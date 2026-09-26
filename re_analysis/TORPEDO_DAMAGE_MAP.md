# Begin 3 Torpedo (Tube) Weapon Map

**Date:** 2026-09-26, `TORPEDO_DAMAGE` session
**Status:** Fire chain traced from raw disassembly down to the moment a torpedo projectile object
gets allocated. The live lock/reload/fire cycle (which tube fields do what) is now thoroughly
confirmed against two real play sessions with live `/proc/<pid>/mem` reads. **Not yet found:** the
projectile object's own per-frame update/collision pass — everything below is the *launch*, not the
*flight or impact*. See §5 for the full open-questions list.

**Prerequisite:** `COMBAT_DAMAGE_MAP.md` (the phaser/Bank equivalent — read first, this doc leans on
its established conventions: array-container back-pointers, the FPU-hidden-argument decompiler trap,
etc.) and `ENERGY_SYSTEM_MAP.md` §3.8/§3.9 (`class_data` TypeRecord table, corrected ship offsets).

---

## 0. Headline: torpedoes are NOT a near-twin of Bank, and there's no auto-fire

Two assumptions going into this session both turned out wrong, in opposite directions:

- **`PYTHON_TOOLS.md`'s note that "Tube's per-unit charge code is a near-exact structural twin of
  Bank's"** was true for *power draw* (Path B6) but does **not** extend to hit resolution — the two
  weapon types work completely differently. Bank is an instant same-frame hit-scan across the whole
  ship list (`COMBAT_DAMAGE_MAP.md` §1); Tube launches a genuine separate projectile object
  (`FUN_0043d97e(0x118)`, §1 below) with its own position/trajectory, matching the manual's own
  "arms after N cycles," "travels at a velocity of," and per-class flavor text.
- Conversely, this session initially suspected torpedoes might **auto-fire** each turn the way Bank's
  `FUN_00403330` appears to (an unconditional per-frame "should we fire" check with no explicit
  command). **Live testing disproved this directly** — a 30-second window with zero commands typed
  produced zero state changes (§2.2); a "no-op" turn (pressing Enter with nothing typed) *did* still
  advance reload/lock state, but only ever in a way traceable to a standing order the player had
  already issued (`"lock all tubes X"`), never to a bare unrequested launch.

---

## 1. Weapon fire chain (Tube / Torpedo), from disassembly

```
ship+0x454 (Tube array — count at +0x0, unit-pointer array at +0x10)
  → FUN_0040c0a0         per-"turn" handler for this ship's tubes
      → FUN_0040beb0        selects eligible tubes (ready(+0x30)!=0 && target(+0x6c)!=0)
      → [inline dedup pass]  merges simultaneous same-target tubes into one announcement,
                              incrementing the merged tube's salvo count (+0x58)
      → FUN_00418430        announces "%s firing %d torpedo%s!\n" (VA 0x004691c0)
      → FUN_0040bf70         the REAL per-tube launch function, once per selected tube
```

Found the same way `COMBAT_DAMAGE_MAP.md` found Bank's chain: `get_xrefs_to` on the announce string
→ `FUN_00418430` → `get_function_xrefs` → `FUN_0040c0a0`.

### 1.1 `FUN_0040c0a0` — per-turn handler and dedup pass

Calls `FUN_0040beb0(this, out_indices)` to get a count and an index list of eligible tubes, then
(if any) walks **every pair** of eligible tubes checking:

```c
if (tubeA.target(+0x6c) != 0 && tubeA.target == tubeB.target) {
    // same target - now check the firing SOLUTION also matches:
    if (tubeA.field_34 == 0) {
        if (tubeB.field_34 == 0 && tubeB.solution(+0x48+0x38) == tubeA.solution(+0x48+0x38))
            merge(tubeA, tubeB);   // tubeA.salvo(+0x58) += 1; tubeB dropped (target zeroed)
    } else if (tubeA.field_34 == tubeB.field_34 && tubeB.field_48 == tubeA.field_48) {
        merge(tubeA, tubeB);
    }
}
```

This is why the string is `"%s firing %d torpedo%s!"` (plural-capable) — several tubes firing at the
same target in the same turn get folded into **one** announcement with a combined count, rather than
one line per tube. (Never observed live — every fire in this session's tests was a single tube; see
§5 item 4.)

### 1.2 `FUN_0040beb0` — tube eligibility

```c
void FUN_0040beb0(TubeArray *this, ushort *out_indices) {
    for each tube in this->units:
        if (tube+0x30 != 0 && tube+0x6c != 0)   // ready AND has a target lock
            *out_indices++ = tube_index;
}
```

Simple two-condition gate. Note **`field_34` (+0x34) plays no role here** — confirmed both statically
(absent from this function entirely) and live (§2, it never changes with firing).

### 1.3 `FUN_0040bf70` — the launch

Traced from decompiled pseudocode (no FPU-hidden-argument issues hit here, unlike Bank's damage
formula in `COMBAT_DAMAGE_MAP.md` §5):

```c
void FUN_0040bf70(Tube *tube) {
    if (tube+0x30 == 0) return;      // not ready - shouldn't happen, caller already filtered
    tube+0x30 = 0;                    // consume readiness
    FUN_0040bf10(tube);                // UNDECODED - some pre-launch prep (§5 item 1)

    ownHeading = FUN_00401430(*(double*)(*(int*)(tube+0x20) + 0x18));  // owning ship's heading, normalized

    target = tube+0x6c;               // the locked-target Ship* - SAVE...
    tube+0x6c = 0;                    // ...then immediately clear the lock (consumed)

    torpedo = FUN_0043d97e(0x118);    // allocate a NEW 0x118-byte object - THE PROJECTILE
    if (torpedo != NULL) {
        torpedo = FUN_00405830(torpedo, ownShip+0xc /*team/faction, confirmed COMBAT_DAMAGE_MAP.md §7*/,
                                target, (ushort)tube+0x58 /*salvo count*/);   // projectile ctor
    }
    torpedo+0xf0 (8 bytes) = tube+0x50;              // charge/damage value copied in
    torpedo+0xe8 (8 bytes) = target+0x28 (8 bytes);  // target's velocity(?) snapshot copied in
    leadTerm = FUN_00401460(0.0, target+0x40 + target+0x40);   // UNCLEAR - not fully decoded (§5 item 3)
    FUN_00405630(torpedo, *(int*)(tube+0x20)+0x18,   // owning ship's Ship*
                 ownHeading, (leadTerm + target+0x40) - target+0x40);  // trajectory/intercept setter

    if (target+0x38 (byte, low byte of a field) != 0)
        FUN_00401c10(torpedo, 1, tube+0x34, torpedo+8);  // conditional - UNCLEAR trigger (§5 item 3)
}
```

**This confirms the projectile-object model directly**: `FUN_0043d97e(0x118)` is the exact
small-object-allocation pattern the session prompt flagged (seen before for various event objects) —
a fresh 280-byte object gets built per torpedo launch, seeded with the firing ship's team id, the
target pointer, the salvo count, a copy of the target's position-adjacent data, and a
trajectory/intercept calculation. This is the code-level confirmation of what the user independently
described from gameplay (§3.3): *"the tube lock calculates the ship direction and speed, then fires
ahead — if the target changes course after that, the torpedo misses (unless it's a
tracking/homing type like Romulan Plasma)."* A one-time lead calculation at launch, not continuous
homing, is exactly a "fire dumb, hope they don't turn" model — matches perfectly.

**Not decoded yet:** the projectile's own per-frame/per-turn update (travel, collision detection,
arming-distance check, the actual hit) — this function only *creates* the object and hands it a
trajectory. See §5 item 5.

---

## 2. Live-tested lock/reload/fire model

Confirmed across two real play sessions (PID 117796, then a fresh PID 124275 after the first ship
was destroyed) using `read_live_classdata.py`'s new `--watch` mode (`watch_tubes()`), which polls
`ship+0x454`'s Tube array every ~0.15s under one `sudo` prompt and prints only the tubes whose
watched fields changed since the last poll — built specifically because a single before/after
snapshot missed the transient `ready` flag entirely (§2.1).

### 2.1 The three per-tube fields, confirmed live

| Field | Confirmed role | Evidence |
|---|---|---|
| `+0x30` `ready` | Single-**instant** flag, true for the exact moment of launch inside `FUN_0040bf70`, then immediately cleared | Caught flipping 0→1→0 across a single ~0.15s poll gap **5 separate times** in one battle, every single time paired with `target` clearing in the same or next poll |
| `+0x6c` `target` | The live firing-solution lock. Set for **every eligible tube at once** by `"lock all tubes X"`. Cleared the instant that specific tube fires. **Reacquired automatically** (no re-issued lock command) once that tube's reload finishes | See §2.3/§2.4 tables below |
| `+0x34` `field_34` | **Not tied to firing at all.** Identical across all 6 tubes, unchanged across 138+ seconds and 8+ fire events in one battle | See §2.4 |

`+0x58` (salvo count) stayed at its baseline value of `1` throughout every test — never observed
incrementing, because no test happened to have two tubes fire at the same target in the same turn
(the dedup pass in §1.1 is still unconfirmed live — see §5 item 4).

### 2.2 Control test: nothing happens with zero input

Before trusting any of the above, ran a 30-second window with the player **not touching the keyboard
at all**. Result: **zero state changes** — not even the earlier-suspected "auto-fire" or a
background timer. This directly disproved an early hypothesis (that `FUN_0040c0a0` might
unconditionally auto-fire torpedoes the way Bank's per-frame check appears to) and confirmed the game
only advances any state on a processed command — this is a turn-based game, not continuously
real-time, something the user flagged mid-session and that reframed the rest of the analysis
correctly.

A follow-up test (pressing blank Enter — no command at all — several times) **did** still produce
tube-state changes, which at first looked like a contradiction. It wasn't: the player had a **standing
`"lock all tubes X"` order** already in effect from before that test started, and tubes coming off
their reload cycle auto-reacquire that standing lock — so blank turns still "do something" to tube
state, just never a launch, only lock bookkeeping.

### 2.3 First confirmation: firing two tubes clears exactly those two tubes' locks

Player fired tube 5 then tube 6 (1-indexed → array index 4, 5) a few seconds apart. Live reads showed
**exactly** tube[4] and tube[5] (and no others) losing their `target` value at the corresponding
times, each immediately followed by some other previously-unlocked tube (tube[0], then tube[1])
picking up the exact same target pointer:

| Time | Event |
|---|---|
| 8.72s | tube[4]: target cleared. tube[0]: target set (same value tube[4] just lost) |
| 12.78s | tube[5]: target cleared. tube[1]: target set (same value tube[5] just lost) |

(A second, less clean run in the same session showed the correlation break down when the player's
"fire tube 1"/"fire tube 2" commands failed silently due to a display/typo issue they'd flagged
independently — turns still advanced from the failed commands, ticking reload state forward with no
successful fire attached. Worth remembering: **a rejected/typo'd command can still consume a turn.**)

### 2.4 Second, cleaner confirmation: full reload-cycle timing table

Second play session (fresh ship, "tubes locked and loaded on the Bismarck," PID 124275), watched for
138+ seconds of normal play with no gaps:

| Tube | Fired at | Regained lock at | Reload gap |
|---|---|---|---|
| 1 | 20.32s | 42.30s | 22.0s |
| 2 | 25.14s | 50.13s | 25.0s |
| 3 | 35.23s (`ready=1` caught at 35.08s) | 56.00s | 20.8s |
| 4 | 38.69s | 66.54s | 27.9s |
| 5 | 42.30s (`ready=1` caught at 42.15s) | 68.65s | 26.4s |
| 0 | 56.00s (delayed — player's first attempt was rejected, tube wasn't loaded yet) | 101.76s | 45.8s (includes the failed early attempt) |

Every successfully-fired tube took **~20-28 seconds** (this game's turn-processing pace) to cycle
back to locked — consistent with the player's own recollection of "3 turns wait, ready on the 4th."
A second full cycle for several tubes (fire again ~80-140s in) reproduced the same ~20-27s gap,
confirming this isn't a one-off. `field_34` was read at every single one of these events and never
changed from its baseline value, across either tube or time — the strongest evidence that it's
unrelated to the fire/reload cycle (see the table in §2.1).

### 2.5 Crash → useful data point: ship destruction invalidates the read cleanly

An earlier, less careful long-running watch **crashed** (`struct.error: unpack requires a buffer of 2
bytes`) partway through a session — turned out the player's ship had just been destroyed
("i died. HA HA."), and the next poll's read of `ship+0x454` came back short because the ship
pointer/object had gone stale. `watch_tubes()` was fixed to re-read the ship pointer every poll and
treat a short read as "unreadable, waiting" rather than crashing — useful going forward for any test
that might run long enough to cross a destruction/battle-end boundary.

---

## 3. Comparison with Bank (Phaser)

| | Bank (Phaser) | Tube (Torpedo) |
|---|---|---|
| Hit resolution | Same-frame hit-scan across the whole ship list (`COMBAT_DAMAGE_MAP.md` §1) | Allocates a real projectile object (`FUN_0043d97e(0x118)`); flight/impact happens later, elsewhere (undecoded, §5 item 5) |
| Fire trigger | Appears to be an unconditional per-frame check (never disproved, but never live-tested either) | **Confirmed NOT automatic** — only ever changes state in response to a processed command, including a no-op blank Enter, never with zero input at all (§2.2) |
| Targeting | Per-shot, computed fresh each firing pass | A **standing lock** (`"lock all tubes X"`) that persists and auto-reapplies to tubes as they come off reload, until that tube actually fires |
| Damage | Instant, linear range falloff formula fully decoded | Charge value (`tube+0x50`) copied into the projectile at launch; the actual damage-on-impact formula is wherever the projectile's collision code lives — **not found yet** |
| Range/falloff | Explicit `1 − distance/maxRange` term in the fire function | A one-time lead/intercept calculation at launch (`FUN_00401460`/`FUN_00405630`), no fresh range check found in the launch function itself — falloff (if any) would have to live in the projectile's own update, not here |

---

## 4. New struct fields confirmed this session

**Tube container** (`ship+0x454`, embedded — not a separate heap allocation):

| Offset | Field |
|---|---|
| `+0x0` (ushort) | Tube count |
| `+0x10` | Pointer to a packed array of `Tube*` (4 bytes each) |

**Tube unit** (per-unit fields, pointed to by the container's `+0x10` array):

| Offset | Field | Confirmed by |
|---|---|---|
| `+0x20` | Back-pointer to array container (established Bank/Tube pattern, `ENERGY_SYSTEM_MAP.md` §3.6) | disassembly |
| `+0x30` | Ready flag — single-instant, true only at the moment of launch | live (§2.1, §2.4) |
| `+0x34` | Fixed/shared reference, NOT firing-related — role unconfirmed (§5 item 2) | live (§2.4), disassembly (absent from `FUN_0040beb0`'s eligibility check) |
| `+0x38`, `+0x48` | Firing-solution doubles, used only to detect duplicate simultaneous shots at the same target (§1.1) | disassembly |
| `+0x50` | Charge/damage value, copied into the new projectile object at `torpedo+0xf0` | disassembly |
| `+0x58` (byte) | Salvo count — starts at `1`, would increment on a dedup-merge (never observed live) | disassembly + live (stayed at 1 throughout) |
| `+0x6c` | Live target lock — set by `"lock all tubes"`, cleared on that tube's own launch, auto-reacquired after reload | live (§2.3, §2.4) + disassembly |

**New projectile object** (`FUN_0043d97e(0x118)`-allocated, constructed by `FUN_00405830`):

| Offset | Field | Confirmed by |
|---|---|---|
| `+0xe8` (8 bytes) | Copy of target `+0x28` (8 bytes) at launch time — likely target velocity/course snapshot, unconfirmed | disassembly |
| `+0xf0` (8 bytes) | Copy of firing tube's `+0x50` charge value | disassembly |

---

## 5. Open questions / TODOs

1. `FUN_0040bf10` — called at the very start of the launch, before the readiness flag is even
   checked further; not decoded at all this session.
2. `field_34`'s real role — confirmed NOT firing-related (§2.1, §2.4), but what it actually *is*
   remains unconfirmed. Candidates: selected-ammo-type pointer (shared across tubes loaded with the
   same torpedo class, e.g. "Mk7"), or a fixed fire-control/launcher-group back-pointer analogous to
   Bank's own fixed `+0x24` field. A clean test: load two different torpedo classes into different
   tubes (if the game allows it) and see whether `field_34` then *differs* between them — this would
   confirm the "selected ammo type" theory directly.
3. The trajectory/intercept math in `FUN_0040bf70` (`FUN_00401460`, `FUN_00405630`, and the
   conditional `FUN_00401c10` call gated on a byte read from the target object) — decompiled but not
   hand-verified against raw disassembly the way Bank's damage formula was in
   `COMBAT_DAMAGE_MAP.md` §5. Given that session's experience, don't fully trust the decompiler's
   constant/argument attribution here without double-checking.
4. The same-target dedup/salvo-merge pass (§1.1) has never been observed live — every fire in this
   session was a single tube at a time. Worth testing directly: fire two or more tubes at the exact
   same locked target in the same turn (if the game's command interface allows a true simultaneous
   multi-tube fire) and watch for `+0x58` incrementing above 1 and a merged announcement string.
5. **The big one, structurally different from anything in `COMBAT_DAMAGE_MAP.md`:** the projectile
   object's own per-frame/per-turn update — travel, the "arms after N cycles" timer, the
   collision/hit check, and wherever the actual damage-on-impact call to `Ship::vftable+0x34`
   (`FUN_00404d90`, already known) happens for torpedoes. `FUN_0040bf70` only *creates and launches*
   the object; nothing in this session traced what runs on it afterward. Likely candidates for a next
   pass: search for other callers of `FUN_00405830`/other methods on the same vtable as the
   projectile object, or look for a second, separate list/array (distinct from the ship list Bank
   scans) that per-frame code iterates to update in-flight projectiles.
6. Confirm whether weapon type `1` (the shield-bypassing type found in `COMBAT_DAMAGE_MAP.md` §2.2)
   is actually passed by the torpedo's eventual damage-application call — requires finding the code
   from item 5 first.
7. Where the homing-vs-dumb-fire distinction (Romulan Plasma tracks continuously; other torpedo
   classes apparently don't, per the user's own gameplay description in §1.3) is actually encoded —
   presumably a per-class-of-ammo flag somewhere in the Tube TypeRecord (`class_data+0x110`,
   `ENERGY_SYSTEM_MAP.md` §3.8) or on the projectile object itself, not found this session.
8. Multi-target split-locking (`"lock tubes 1-3 on ship A, tubes 4-6 on ship B"`, per the user's
   description) was never tested live — every test this session had exactly one enemy ship present,
   so every locked tube showed the identical target pointer. A scenario with two live enemies would
   directly confirm that `target` really is per-tube (not per-ship-wide) and let different tubes show
   different pointers simultaneously.

---

## 6. Constants / addresses reference

| VA | Role |
|---|---|
| `0x004691c0` | String: `"%s firing %d torpedo%s!\n"` (3rd-person announce) |
| `0x00418430` | `FUN_00418430` — announce-string handler (torpedo's analog to Bank's `FUN_004183e0`) |
| `0x0040c0a0` | `FUN_0040c0a0` — per-turn Tube handler (torpedo's analog to Bank's `FUN_00403330`) |
| `0x0040beb0` | `FUN_0040beb0` — tube eligibility selector (torpedo's analog to Bank's still-undecoded `FUN_004086a0`) |
| `0x0040bf70` | `FUN_0040bf70` — the real per-tube launch function (torpedo's analog to Bank's `FUN_00408cf0`) |
| `0x0043d97e` | `FUN_0043d97e(size)` — small-object allocator, called here with `0x118` (280 bytes) for the projectile |
| `0x00405830` | Projectile object constructor |
| `0x0040bf10` | Pre-launch prep, undecoded (§5 item 1) |
| `0x00401460` / `0x00405630` / `0x00401c10` | Trajectory/intercept math, not fully verified (§5 item 3) |
