#!/usr/bin/env python3
"""
One-off diagnostic: read the live class_data struct out of a running Begin.exe
(under Wine) via /proc/<pid>/mem, to check it against the static-file offsets
assumed in ship-struct-analysis.md.

Needs root (or CAP_SYS_PTRACE) to read another process's memory even as the
same user, because of the default Yama ptrace_scope=1 restriction - hence
running this with sudo rather than changing that system-wide security setting.

Usage: sudo python3 read_live_classdata.py <PID>
"""
import struct
import sys
import time


def read_mem(pid, addr, size):
    with open(f'/proc/{pid}/mem', 'rb') as f:
        f.seek(addr)
        return f.read(size)


def main():
    if len(sys.argv) >= 3 and sys.argv[2] == '--watch':
        pid = int(sys.argv[1])
        duration = float(sys.argv[3]) if len(sys.argv) >= 4 else 10.0
        watch_tubes(pid, duration=duration)
        return

    if len(sys.argv) != 2:
        print(f"Usage: sudo python3 {sys.argv[0]} <PID>")
        print(f"       sudo python3 {sys.argv[0]} <PID> --watch   "
              f"(poll the Tube array ~7x/sec for 10s under one sudo prompt,")
        print("        printing only tubes whose fields changed since the last poll -"
              " fire while it's running)")
        sys.exit(1)
    pid = int(sys.argv[1])

    ship_ptr = struct.unpack('<I', read_mem(pid, 0x004941c4, 4))[0]
    print(f"ship pointer (DAT_004941c4)      = 0x{ship_ptr:08x}")

    if ship_ptr == 0:
        print("Ship pointer is NULL - is a battle actually running with your own ship active?")
        return

    class_data = struct.unpack('<I', read_mem(pid, ship_ptr + 0xe4, 4))[0]
    print(f"class_data (ship+0xe4)           = 0x{class_data:08x}")

    crew = struct.unpack('<i', read_mem(pid, class_data + 0x14, 4))[0]
    dwt = struct.unpack('<i', read_mem(pid, class_data + 0x18, 4))[0]
    print(f"class_data+0x14 (expected crew)  = {crew}")
    print(f"class_data+0x18 (expected DWT)   = {dwt}")

    val_54 = struct.unpack('<i', read_mem(pid, class_data + 0x54, 4))[0]
    val_58_word = struct.unpack('<H', read_mem(pid, class_data + 0x58, 2))[0]
    print(f"class_data+0x54 (old guess: reactor count) = {val_54}")
    print(f"class_data+0x58 (code-confirmed Reactor TypeRecord count) = {val_58_word}")

    # COMBAT_DAMAGE session: class_data+0x380 is code-confirmed (ship constructor,
    # FUN_00404910) as the source ship+0x110 gets copied from at construction, and
    # FUN_00404d90 (damage application) treats ship+0x110 as a live, decreasing hull-HP
    # pool. But the static file reads 0 at class_data+0x380 for Heavy Cruiser/Destroyer/
    # Frigate - suspicious, since a ship starting with 0 hull would hit the "critically
    # low hull" branch on its very first point of hull damage, every time. Reading these
    # live checks whether the static file's 0 is real or a stale/pre-init template value.
    hull_max = struct.unpack('<i', read_mem(pid, class_data + 0x380, 4))[0]
    link_scale = struct.unpack('<d', read_mem(pid, class_data + 0x390, 8))[0]
    destruct_threshold = struct.unpack('<d', read_mem(pid, class_data + 0x3a0, 8))[0]
    ship_hull_current = struct.unpack('<i', read_mem(pid, ship_ptr + 0x110, 4))[0]
    print(f"class_data+0x380 (hypothesis: max hull, static file reads 0) = {hull_max}")
    print(f"class_data+0x390 (hypothesis: linked-ship risk scaling) = {link_scale}")
    print(f"class_data+0x3a0 (hypothesis: destruction threshold, static file reads 75.0 for HC) = {destruct_threshold}")
    print(f"ship+0x110 (hypothesis: current hull HP, copied from class_data+0x380 at construction) = {ship_hull_current}")

    print()
    read_tube_array(pid, ship_ptr)


def read_tube_array(pid, ship_ptr):
    """TORPEDO_DAMAGE session: dump the live Tube array (ship+0x454) to watch a
    tube's state transition around an actual in-game torpedo launch.

    Container layout (from FUN_0040beb0/FUN_0040c0a0 disassembly, TORPEDO_DAMAGE
    session): ship+0x454 IS the container (embedded, not a separate heap alloc) -
    +0x0 is a ushort tube count, +0x10 is a pointer to a packed array of Tube*
    pointers (4 bytes each).

    Per-tube fields read here, all from FUN_0040beb0/FUN_0040bf70:
    - +0x30 (byte): ready flag - live-confirmed (TORPEDO_DAMAGE session) as a
      genuine single-instant flag: caught it flip to 1 for exactly one ~0.15s
      poll several times, always immediately followed by 0 + target(+0x6c)
      cleared. This is the literal launch instant inside FUN_0040bf70.
    - +0x34 (int): NOT tied to firing - live-tested across 138s and 8+ fire
      events in one battle, always identical across all 6 tubes and never
      changed once, despite repeated fires. A fixed/shared reference (possibly
      selected-ammo-type or a fire-control back-pointer), same role-shape as
      Bank's own fixed +0x24 (COMBAT_DAMAGE_MAP.md §1). (Earlier hypothesis -
      a per-fire "queued order" cleared alongside +0x6c on launch - was based
      on a single ambiguous observation right before the ship was destroyed in
      that test and is now believed wrong; see TORPEDO_DAMAGE_MAP.md §3.)
    - +0x58 (byte): salvo count - incremented once per duplicate tube merged
      into the same firing solution (see FUN_0040c0a0's dedup pass); expect
      this to reset/increment around a fire event.
    - +0x6c (int, pointer): the live firing-solution lock ("target" from here
      on) - live-confirmed as the standing lock set by "lock all tubes X"
      (applies to every eligible tube at once, even ones without a fresh
      round), cleared by FUN_0040bf70 the instant a tube fires, and reacquired
      automatically - no re-issued lock command needed - once that tube's
      reload cycle completes (observed at a fairly consistent ~20-28s cadence
      at this game's turn-taking pace, matching "3 turns wait, ready on the
      4th"). See TORPEDO_DAMAGE_MAP.md §3 for the full session transcript this
      is based on.
    """
    tube_container = ship_ptr + 0x454
    count = struct.unpack('<H', read_mem(pid, tube_container, 2))[0]
    units_ptr = struct.unpack('<I', read_mem(pid, tube_container + 0x10, 4))[0]
    print(f"Tube array (ship+0x454): count = {count}, units_ptr (container+0x10) = 0x{units_ptr:08x}")

    if count == 0 or units_ptr == 0:
        print("  (no tubes, or units_ptr is NULL - nothing more to read)")
        return

    for i in range(count):
        unit_ptr = struct.unpack('<I', read_mem(pid, units_ptr + i * 4, 4))[0]
        ready = struct.unpack('<B', read_mem(pid, unit_ptr + 0x30, 1))[0]
        field_34 = struct.unpack('<i', read_mem(pid, unit_ptr + 0x34, 4))[0]
        salvo = struct.unpack('<B', read_mem(pid, unit_ptr + 0x58, 1))[0]
        target_ptr = struct.unpack('<I', read_mem(pid, unit_ptr + 0x6c, 4))[0]
        print(f"  tube[{i}] @ 0x{unit_ptr:08x}: ready(+0x30)={ready}  field_34(+0x34)={field_34}  "
              f"salvo(+0x58)={salvo}  target(+0x6c)=0x{target_ptr:08x}")


def _snapshot_tubes(mem_file, ship_ptr):
    """Single-poll variant of read_tube_array() that reuses an already-open mem
    file handle (for tight polling in watch_tubes()) and returns the per-tube
    tuples instead of printing, so the caller can diff between polls.

    Returns None (not []) if the container/array can't be read right now - the
    ship pointer can go stale mid-watch (ship destroyed, battle ends, game
    reloads a save), which showed up as a real crash the first time a
    long-duration watch ran long enough to cross one of those transitions.
    """
    def rd(addr, size):
        mem_file.seek(addr)
        data = mem_file.read(size)
        return data if len(data) == size else None

    tube_container = ship_ptr + 0x454
    raw_count = rd(tube_container, 2)
    raw_units_ptr = rd(tube_container + 0x10, 4)
    if raw_count is None or raw_units_ptr is None:
        return None
    count = struct.unpack('<H', raw_count)[0]
    units_ptr = struct.unpack('<I', raw_units_ptr)[0]
    if count == 0 or units_ptr == 0:
        return []

    rows = []
    for i in range(count):
        raw_unit_ptr = rd(units_ptr + i * 4, 4)
        if raw_unit_ptr is None:
            return None
        unit_ptr = struct.unpack('<I', raw_unit_ptr)[0]
        raw = [rd(unit_ptr + 0x30, 1), rd(unit_ptr + 0x34, 4), rd(unit_ptr + 0x58, 1), rd(unit_ptr + 0x6c, 4)]
        if any(r is None for r in raw):
            return None
        ready = struct.unpack('<B', raw[0])[0]
        field_34 = struct.unpack('<i', raw[1])[0]
        salvo = struct.unpack('<B', raw[2])[0]
        target_ptr = struct.unpack('<I', raw[3])[0]
        rows.append((i, unit_ptr, ready, field_34, salvo, target_ptr))
    return rows


def watch_tubes(pid, duration=10.0, interval=0.15):
    """TORPEDO_DAMAGE session: poll the Tube array repeatedly under one sudo
    prompt, printing a line only when a tube's watched fields change since the
    last poll. Meant to be started right before firing, to catch the
    ready(+0x30) flag's same-frame flip that a single before/after snapshot
    (read_tube_array()) can miss entirely.

    Re-reads the ship pointer (DAT_004941c4) every poll rather than once at
    the start, and tolerates it (or the tube array) going temporarily
    unreadable - e.g. combat ending, the ship being destroyed, or a save
    reloading mid-watch - by reporting the transition once and continuing to
    poll for it to come back, instead of crashing (see git history for the
    struct.error this used to throw when a long watch crossed one of these).
    """
    with open(f'/proc/{pid}/mem', 'rb') as mem_file:
        print(f"Watching Tube array (ship+0x454) for {duration}s, every {interval}s - fire now.")
        start = time.time()
        last = {}
        was_readable = None
        while time.time() - start < duration:
            t = time.time() - start
            ship_ptr = struct.unpack('<I', read_mem(pid, 0x004941c4, 4))[0]
            rows = _snapshot_tubes(mem_file, ship_ptr) if ship_ptr != 0 else None
            if rows is None:
                if was_readable is not False:
                    print(f"  [{t:5.2f}s] ship pointer/Tube array unreadable "
                          f"(ship_ptr=0x{ship_ptr:08x}) - battle ended? ship destroyed? waiting...")
                was_readable = False
                last = {}
            else:
                if was_readable is False:
                    print(f"  [{t:5.2f}s] readable again (ship_ptr=0x{ship_ptr:08x})")
                was_readable = True
                for (i, unit_ptr, ready, field_34, salvo, target_ptr) in rows:
                    row = (ready, field_34, salvo, target_ptr)
                    if last.get(i) != row:
                        print(f"  [{t:5.2f}s] tube[{i}] @ 0x{unit_ptr:08x}: ready(+0x30)={ready}  "
                              f"field_34(+0x34)={field_34}  salvo(+0x58)={salvo}  target(+0x6c)=0x{target_ptr:08x}")
                        last[i] = row
            time.sleep(interval)
        print("Done watching.")


if __name__ == "__main__":
    main()
