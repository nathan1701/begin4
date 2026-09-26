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


def read_mem(pid, addr, size):
    with open(f'/proc/{pid}/mem', 'rb') as f:
        f.seek(addr)
        return f.read(size)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: sudo python3 {sys.argv[0]} <PID>")
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


if __name__ == "__main__":
    main()
