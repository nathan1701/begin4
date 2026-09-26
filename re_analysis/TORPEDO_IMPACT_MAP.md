# Begin 3 Torpedo Post-Launch / Impact Map

**Date:** 2026-09-26, `TORPEDO_IMPACT` session
**Status:** The projectile's self-registration into a global "in-flight" list is traced from raw
disassembly, as is the per-ship-per-turn function that checks that list for hits and rolls
damage. The single biggest open question this session was aimed at — does torpedo damage apply
immediately or is it deferred a turn, given the damage-dispatch function doesn't call the already-known
`Ship::vftable+0x34` directly — is **answered by live testing: immediate, not deferred.** Also
live-confirmed this session, unprompted: shield regen rate, multi-facing salvo hits, the
lost-detection/stale-position mechanic, and the derelict-ship (crew wipeout) handler.

**Prerequisite:** `TORPEDO_DAMAGE_MAP.md` (the fire chain through launch — this doc picks up exactly
where that one's §5 item 5 left off) and `COMBAT_DAMAGE_MAP.md` (the phaser/Bank equivalent chain,
whose confirmed struct fields — Shield array, hit counters, damage-application function — this
session reuses and, in one case, corrects).

---

## 0. Headline: the static read looked like deferred damage; live testing showed it isn't

Tracing the projectile's post-launch code from `Torp::vftable+0x20` down to its final dispatch call
(§2 below) landed on a function, `FUN_004089b0`, that — unlike Bank's phaser chain — does **not**
call the confirmed `Ship::vftable+0x34` (`FUN_00404d90`, damage application) directly. Instead it
writes a damage value into an array element and sets a flag byte, then returns. The natural reading
of that shape is "mark this hit as pending, apply it later" — a genuinely different mechanic from
phasers' immediate hit-and-resolve.

**Live testing across two real fights (§3) disproved the "later" part.** Every one of 6+ confirmed
hit events — spanning both a torpedo exchange and a phaser exchange, in two separate battles —
showed the target's `totalHits`/`hullHits` counters and the struck shield facing's `charge%`/
`integrity` change in the *same poll* the hit registered, never a turn afterward. The flag being
written is much more likely a same-turn "processing in progress, cleared by end of this turn's
dispatch pass" signal than a real deferred-damage queue. This is the same live-testing-overturns-a
-reasonable-static-guess pattern `TORPEDO_DAMAGE_MAP.md` §0 hit twice last session — worth
remembering as a standing lesson for this project, not just this one function.

---

## 1. The projectile's self-registration into a global "in-flight" list

`TORPEDO_DAMAGE_MAP.md` §1.3 traced the launch chain down to `FUN_0040bf70` allocating a ~280-byte
`Torp` object (`FUN_0043d97e(0x118)`) and calling `FUN_00405830` to construct it, then
`FUN_00405630` to seed its trajectory. This session picked up from there.

### 1.1 The constructor's embedded list node

`FUN_00405830` (the `Torp` constructor, confirmed via Ghidra's own RTTI-recovered symbol
`Torp::vftable`, disassembled at `0x00405830`):

```
*(undefined ***)this = Torp::vftable;       // 0x00464f84
this->0x114 = this;                          // owner back-pointer
node = &this->0x10c;
*node = node;  node->0x4 = node;             // self-pointing circular-list init (empty state)
```

`this+0x10c`/`this+0x110` are a classic two-field intrusive doubly-linked-list node (next/prev,
using the "pointer to neighbor's link field" style rather than "pointer to neighbor node"), and
`this+0x114` is a back-pointer from the node to its owning `Torp` object — the same "node embedded
in the object it tracks" shape used elsewhere in this codebase (e.g. the ship-list node at
`ship+0xc58`/`+0xc5c` noted in `COMBAT_DAMAGE_MAP.md` §7).

### 1.2 The registration call

`FUN_00405630` (trajectory-seeding, called right after construction):
```
FUN_004027f0(this_00 /*torpedo*/, ship_class_ptr, chargeArg, ...)
  → FUN_004022f0(...)          seeds position/velocity fields
  → FUN_00402390(...)          seeds more trajectory fields
  → (*this_00->vtable[0x20])() ← virtual call through the projectile's OWN vtable, no other args
FUN_00421b70(...)               separately posts a UI/sound notification event (see below)
```

The vtable`+0x20` call was the key lead — same shape (`this`-only virtual call, minimal visible
args) that led to `Ship::vftable+0x34` in `COMBAT_DAMAGE_MAP.md` §4. Reading `Torp::vftable`'s raw
bytes directly (Ghidra's MCP tools have no memory-read primitive, so this used
`energy_system_analysis.py`'s `read_constant_at_address` against the binary file instead — see
§7 workflow note) gives `Torp::vftable+0x20 = 0x00405980`:

```c
void FUN_00405980(Torp *this) {   // = Torp::vftable+0x20
    FUN_004027b0(this);
    // classic circular doubly-linked-list tail-insert:
    oldTail = PTR_LOOP_0048b3ac;
    *oldTail = &this->0x10c;          // old tail's "next" -> new node
    this->0x110 = oldTail;            // new node's "prev" -> old tail
    this->0x10c = &PTR_LOOP_0048b3a8; // new node's "next" -> sentinel (wraps)
    PTR_LOOP_0048b3ac = &this->0x10c; // global tail -> new node
}
```

`PTR_LOOP_0048b3a8`/`PTR_LOOP_0048b3ac` (Ghidra's own auto-naming — it recognized the circular-list
shape independently) is a **global sentinel**, confirmed by:
- `get_xrefs_to` on both addresses: only `FUN_00405980` (insert, above) and `FUN_00463b20` (a
  trivial list-init function, sets both globals to self-point — the empty-list state) touch them.
- `FUN_004027f0`'s virtual call is the **only call site** of `FUN_00405830`'s vtable slot; every
  torpedo that's ever launched goes through this exact insert.

**This is the "list of things in flight" the previous session's `NEXT_SESSION_PROMPT.txt` predicted
would need to be found.** Every launched torpedo lives in exactly one place, independent of any
specific ship, until something removes it.

### 1.3 Open: no removal function found

Only two functions touch the sentinel globals directly (insert, init). A node removed from the
*middle* of a doubly-linked list only touches its own two neighbors' link fields — it would **not**
need to reference the sentinel at all unless removing the head or tail specifically — so
`get_xrefs_to` on the sentinel addresses cannot rule out a generic, shared-across-many-list-types
unlink helper existing elsewhere. **Not found this session.** Whatever removes an expired/impacted
torpedo from this list (letting it eventually get freed) is still unknown. See §6 item 1.

---

## 2. The per-ship-per-turn collision/hit-resolution chain

Only one function reads the global list after insertion: `FUN_00406f10`.

### 2.1 Caller: a per-ship "did anything happen" dispatcher

`FUN_00406f10`'s single caller is `FUN_004084b0`, which tries a sequence of per-ship turn-event
checks in order, short-circuiting on the first that returns 1 ("something happened"):
```c
FUN_004059f0(...) || FUN_00405ee0(...) || FUN_00406e60(...) || FUN_00406f10(...) ||
FUN_004078d0(...) || FUN_00405fd0(...) || FUN_00406050(...)
```
This confirms `FUN_00406f10` runs **once per ship, per turn** — not once globally, not per-torpedo.
Each call walks the *entire* torpedo list and checks every live torpedo against *this* ship.

### 2.2 `FUN_00406f10`'s body, per torpedo in the list

```c
for (torp in global_torp_list) {
    if (RNG() >= ship.chanceThreshold) continue;              // FUN_00402040, per-ship gate
    angle = normalize(bearing(torp, ship_context));            // FUN_00402090 + FUN_004014c0 —
                                                                 // same bearing/facing-fold shape
                                                                 // as COMBAT_DAMAGE_MAP.md §2.1/§3
    if (!findFacingWithinCone(ship_context, torp, &facingIdx, &foldedAngle))  // FUN_00406db0
        continue;
    if (torp has no valid ammo class) damage = DEFAULT; 
    else {
        damage = FUN_00405b50(shipSubObj, torp, foldedAngle*2);  // hit-chance + damage roll, §2.3
        if (damage == 0) return 0;                              // missed
        casualties = clamp(FUN_0044c1c0(...), 0, ship.crewCap); // crew-casualty-style count
    }
    FUN_00408c00(shipTargetArray, casualties_or_1, damage);      // dispatch, §2.4
    return 1;
}
```

### 2.3 `FUN_00405b50` — the hit-chance + damage formula

```c
hitChanceStat = *(double*)(torp->classDataPtr + 0x40);
baseDamage    = *(double*)(torp->classDataPtr + 0x38);
if (RNG() > hitChanceStat) return 0;                   // miss
return (45.0 / distanceParam) * RNG() * baseDamage * 0.5;
```
`torp->classDataPtr` (`this+0x44c`) is presumed to be the torpedo class's TypeRecord, by direct
analogy with every other weapon's "class-data chain" pattern in this codebase (Bank's `+0x24` →
`+0x40` = max range, `ENERGY_SYSTEM_MAP.md` §3.8/`COMBAT_DAMAGE_MAP.md` §7) — **not independently
verified against a specific torpedo class's known stats this session** (see §6 item 2). The overall
shape (`const / distanceOrAngle * RNG * baseDamage * const`) directly mirrors the phaser falloff
formula in `COMBAT_DAMAGE_MAP.md` §1, reusing the same `45.0`/`0.5` constants.

### 2.4 `FUN_00408c00` → `FUN_004089b0` — the dispatch that looked deferred

```c
FUN_00408c00(targetArray, maxCount, damage):
    for each eligible slot in targetArray (not already flagged, some threshold check):
        collect index
    FUN_004089b0(targetArray, collectedIndices, count, damage)

FUN_004089b0(this, indices, count, damage):
    for each index:
        slot = this->array[index]
        if slot is "eligible" (a different, narrower condition):
            slot->0x48 = damage     // write pending damage value
            slot->0x30 = 1          // flag byte, set to 1
        else:
            (slot skipped, left in the "still eligible" output list)
```

**This is the write that looked like deferred damage** — `slot+0x30 = 1` / `slot+0x48 = damage`,
with no further code in this call chain reading them back. **Important correction:** the array
walked here (rooted at `shipContext+0xb8` → `+0x43c`) is **not confirmed to be the Shield array**
(`ship+0x7f8`) — its field offsets (`+0xc`, `+0x14`, `+0x24`→`+0x38`, `+0x40`) don't cleanly match
the confirmed Shield-unit layout from `COMBAT_DAMAGE_MAP.md` §7. What `shipContext` (`ship+0xb8`,
dereferenced) and this `+0x43c` array actually are is **unresolved** — see §6 item 3. The live
testing in §3 answers the *timing* question (immediate, not deferred) without needing to resolve
this array's identity first.

---

## 3. Live confirmation: damage is applied immediately, not deferred

**Method:** extended `read_live_classdata.py` with a new `--watch-combat [duration]` mode
(`watch_combat()`/`_snapshot_combat()`) polling the *target* ship's `+0x134` (total-hits counter),
`+0x128` (hull-hits-this-frame counter), `+0x12C` (took-damage-this-frame flag), and the Shield
array (`ship+0x7f8`)'s per-unit `+0x28`/`+0x30`/`+0x38` (hits/charge%/integrity) — all fields
already confirmed in `COMBAT_DAMAGE_MAP.md` §7, here live-watched turn-by-turn for the first time.
Deliberately does **not** watch `ship+0x110` ("hull") — already known to be scratch space reset
within the same function call, not a persistent value (`COMBAT_DAMAGE_MAP.md` §0/§4.1) — a live
read confirmed it sitting at `0` at rest before the watcher was even built out, avoiding a wasted
test.

**Result, across two separate battles (one ending in the player's ship being destroyed, a second
fight after restarting):**

```
[47.66s] totalHits=5   tookDamageFlag=1  <-- shield[3] charge% 100.00 -> 46.00   (same poll)
[66.60s] totalHits=10  tookDamageFlag=1  <-- shield[3] charge%  49.42 ->  1.58   (same poll)
[74.26s] totalHits=15  tookDamageFlag=1  <-- shield[5] charge% 100.00 -> 46.00   (same poll)
[82.38s] totalHits=20  tookDamageFlag=1  <-- shield[5] charge%  47.25 -> 34.28   (same poll)
[204.04s] totalHits=25 tookDamageFlag=1  <-- shield[5] charge%   7.03 ->  6.73   (same poll)
[211.70s] totalHits=30 tookDamageFlag=1  <-- shield[5] charge%   7.03 ->  0.00, three other
                                              facings also freshly damaged in the SAME poll (salvo)
[  6.77s] totalHits=32 hullHits=0->2 tookDamageFlag=1  <-- shield[0]->0.00%, shield[5]->0.00%,
                                              hits(+0x28) on shield[5] 0->2, ALL in the same poll
```
(Timestamps are wall-clock seconds since each watch started, not comparable across the two runs.)

Every single hit event shows the counter change and the shield-field change **in the same 0.15s
poll** — never a poll or a turn later. The first battle's hits were confirmed by the developer to be
torpedoes fired from standoff range (gaps of ~8–19s between hits, matching the ~20-28s tube reload
cadence from `TORPEDO_DAMAGE_MAP.md` §2.4, not phasers' tighter cadence); the second battle mixed
torpedo hits (standoff range) and phaser hits (after the enemy closed to short range) and showed
identical same-poll timing for both weapon types.

**`hullHits(+0x128)` also confirmed as a real, working, correctly-named counter** — it sat at 0
through 30 shield-absorbed hits across two fights (nothing had penetrated yet), then jumped from
`0` to `2` in one poll once two different shield facings were simultaneously at 0% charge, and reset
to `0` the very next poll — consistent with `COMBAT_DAMAGE_MAP.md` §7's "hull-hits-**this-frame**"
description (resets every turn, doesn't accumulate). This had never actually been *seen* to fire
live before this session.

**One caveat, honestly reported rather than smoothed over:** the developer's ship was destroyed
shortly after that `hullHits=2` spike, but the watch script's own log went quiet for the remainder
of the fight (no further changes to print — consistent with combat continuing without further
hits to *this* polled set of fields, not necessarily a script failure), and a direct one-shot
read afterward of `ship+0x1c` (status byte, `3` = destroyed per `COMBAT_DAMAGE_MAP.md` §7) came
back `0`, not `3`. The most likely explanation is that `DAT_004941c4` (the global "current ship"
pointer) goes stale after destruction rather than tracking a fresh state — `TORPEDO_DAMAGE_MAP.md`
§2.5 already documented this exact stale-pointer behavior last session. The literal killing blow's
data was not captured. This doesn't weaken the immediate-vs-deferred conclusion (which rests on the
six clean same-poll hit events above), but the destruction moment itself remains unobserved.

---

## 4. Bonus live findings (unprompted, surfaced during the watch)

### 4.1 Shield regen is real and has a visible rate

Between hits, a facing's `charge%`/`integrity` climbs steadily — e.g. one facing: `46.41 → 46.83 →
47.25 → 47.68 → 48.11 → 48.54 → 48.98 → 49.42` over roughly 18 seconds of real time (several turns).
First live confirmation that shield regen is a real, continuously-running mechanic, not just a
value that resets between battles. Exact per-turn rate not computed (would need turn-count, not
wall-clock, correlation — see §6 item 4).

### 4.2 Multi-facing salvos happen

At the `211.70s` mark in the first battle, one single `totalHits` jump of 5 corresponded to **four
different shield facings** all showing fresh damage in the same poll — several weapons (or several
torpedoes) landing on different facings in the same turn, not just repeated hits on one facing.

### 4.3 Lost-detection / stale-position mechanic, live-confirmed

The developer reported the enemy ship appearing "grey" on the tactical display, frozen at a "last
known position" despite continuing to move in reality. This is exactly the behavior
`COMBAT_DAMAGE_MAP.md` §3 predicted from static analysis alone but flagged as unexplored (its own
§6 item 8): an undetected ship's apparent position is read from the stale estimated fields
(`+0xb0`/`+0xb8`) rather than the continuously-updated true position (`+0x38`/`+0x40`). No new code
was traced for this — it's a live gameplay confirmation of an existing static hypothesis, not a new
finding — but it's the first time this project has actually observed the effect rather than just
inferred it from the constructor/bearing-helper code.

---

## 5. Derelict-ship / crew-wipeout handler, confirmed (both statically and live)

`COMBAT_DAMAGE_MAP.md` §6 item 9 flagged `FUN_00403210` (called when `ship+0xf0`, crew count, drops
under 6) as a "presumed derelict/abandon-ship handler, not decoded." Decompiled this session:

```c
void FUN_00403210(Ship *this) {
    this->0xf0 = 0;   // crew count
    this->0xf4 = 0;
    this->0xf8 = 0;
    this->0xfc = 0;
    this->0x100 = 0;
    this->0x104 = 0;
    this->0x108 = 0;
    this->0x10c = 0;
}
```

A full wipe of crew count plus seven adjacent fields (presumably officer/crew sub-structures) — not
a partial casualty tick, a complete zeroing. The developer independently reported, in the same
session and before this function was checked, a live account matching this exactly: a ship turning
a distinct color on their tactical display, hull intact but apparently crewless, capturable by
sending a boarding party and reactivating it. **This upgrades the item-9 "presumed" label to
confirmed**, both by the code shape and by matching real gameplay. The boarding/capture mechanic
itself — what triggers it, what code handles a successful boarding, how "derelict" is signaled to
the UI (the "blue ship" color) — was not traced this session; see §6 item 5, and note this may
tie into the already-flagged "transporter/ship-naming bug" lead from `ENERGY_SYSTEM_MAP.md` §9.

---

## 6. Open questions / TODOs

1. **No removal-from-list function found** (§1.3) — how an expired, impacted, or dodged torpedo
   gets taken out of the global in-flight list (and presumably freed) is unknown. A generic
   node-unlink helper wouldn't show up under `get_xrefs_to` on the sentinel globals the way insert
   did, so this needs a different search strategy — e.g. other callers of whatever frees a `0x118`
   -byte block (mirror of `FUN_0043d97e`'s allocator), or stepping through `Torp::vftable`'s other
   slots (only `+0x20` was checked this session; the vtable dump in §1.2 lists 10 entries total).
2. **`torp->classDataPtr+0x38`/`+0x40` (base damage / hit-chance) not cross-checked against a known
   torpedo class's actual stats** — the formula shape (§2.3) is confirmed by live testing producing
   sane hit/miss/damage behavior, but the specific field identification is by pattern-analogy only,
   the same caveat `COMBAT_DAMAGE_MAP.md` §6 item 11 already carries for Bank's own range field.
3. **The array `FUN_004089b0` writes into (§2.4) is not confirmed to be the Shield array** — its
   field offsets don't cleanly match Shield's known layout. What `shipContext+0xb8+0x43c` actually
   is remains open. Possible approach: set a Ghidra breakpoint equivalent (not available via this
   MCP toolset) or trace `shipContext` itself back to its own constructor to identify the type.
4. **Shield regen's exact per-turn rate** — observed live (§4.1) but only correlated against
   wall-clock time, not turn count, so no precise rate is documented yet.
5. **The boarding/capture mechanic itself** (§5) — what code handles a successful boarding of a
   derelict ship, and where the "blue ship" UI color comes from. Promising next-session candidate;
   also may connect to the transporter/ship-naming bug already flagged in `ENERGY_SYSTEM_MAP.md` §9.
6. **The literal ship-destruction moment was not captured live** (§3 caveat) — `DAT_004941c4` going
   stale after death prevented confirming `ship+0x1c=3` on the actual kill. A cleaner capture would
   need either a faster poll right at the moment of death, or reading the ship pointer through a
   path that survives the transition (not investigated).
7. **Weapon type `1` (shield-bypass, `COMBAT_DAMAGE_MAP.md` §2.2) not confirmed as what torpedoes
   pass** — still open from `TORPEDO_DAMAGE_MAP.md` §5 item 6; this session's chain (§2) never
   surfaced an explicit `weaponType` argument the way Bank's does.
8. **`FUN_0040bf10`** (torpedo launch's pre-launch prep call, `TORPEDO_DAMAGE_MAP.md` §5 item 1) —
   still not decoded.
9. Everything still open from `TORPEDO_DAMAGE_MAP.md` §5 items 2/4/7/8 (field_34's role, salvo
   dedup, homing-vs-dumb-fire, multi-target split-locking) and `COMBAT_DAMAGE_MAP.md` §6 items 1-8 —
   untouched this session, still valid.

---

## 7. Workflow / methodology notes

- **Ghidra's MCP tools have no raw memory/data-read primitive** — `get_xrefs_to`/`decompile_function`
  work on code, but reading a vtable's actual pointer *values* (as opposed to xrefs to the vtable's
  address) isn't directly supported. Worked around by disassembling the constructor to find the
  vtable's address as a literal (`MOV dword ptr [ESI],0x464f84`), then using
  `energy_system_analysis.py`'s existing `read_constant_at_address()` against the binary file on
  disk to dump the vtable's 10 entries as raw 4-byte pointers. Reusable pattern for any future
  vtable-slot lookup.
- **`read_live_classdata.py` gained `--watch-combat [duration]`** (`watch_combat()`/
  `_snapshot_combat()`), same shape as last session's `--watch`/`watch_tubes()`. Two real bugs
  found and fixed while building it, both instructive:
  - **Wrong container-layout assumption:** copy-pasted the Tube array's shape (count + pointer to a
    packed array of unit *pointers*) onto the Shield array without checking — Shield's array is
    actually **embedded in-place** (count, then units packed directly starting 8 bytes into the
    container, stride `0x48` bytes, no pointer indirection at all). Caught immediately by an
    `OSError` reading through the resulting garbage pointer, then fixed by decompiling the real
    facing-selection function (`FUN_0040b180`) instead of assuming uniformity across subsystems.
    **Lesson: "established pattern" from one subsystem (`COMBAT_DAMAGE_MAP.md` §3.6) doesn't
    automatically transfer to another — check.**
  - **Process-exit crash:** the watch loops re-read the ship pointer every poll via a fresh
    `open('/proc/<pid>/mem')` each time; if the whole game process exits (not just the ship
    pointer going stale), that raises `FileNotFoundError` uncaught. Fixed with a new
    `read_mem_or_none()` helper and applied to both `watch_tubes()` and `watch_combat()`.
  - Also picked and discarded a wrong assumption about *which* hull-related field to watch: an
    early version watched `ship+0x110` ("hull") before remembering `COMBAT_DAMAGE_MAP.md` had
    already established it's scratch space, not persistent — caught by a one-shot sanity check
    (reading `0` at rest) before wasting a full 5-minute watch window on a field that could never
    show a meaningful change.
- **Two Begin.exe processes can be running under Wine at once** (a wrapper + the real instance) —
  confirmed by reading `DAT_004941c4` from each PID and using whichever returns a non-null pointer,
  rather than assuming the first PID `ps aux` lists is the live one.

---

## 8. Constants / addresses reference

| VA | Role |
|---|---|
| `0x00464f84` | `Torp::vftable` base |
| `0x00405980` | `Torp::vftable+0x20` — global in-flight-list insert |
| `0x0048b3a8` / `0x0048b3ac` | Global torpedo-list sentinel (next/prev), init by `FUN_00463b20` |
| `0x00406f10` | Per-ship-per-turn torpedo collision/hit check (walks the global list) |
| `0x004084b0` | Per-ship per-turn "did anything happen" dispatcher (single caller of `FUN_00406f10`) |
| `0x00405b50` | Torpedo hit-chance + damage formula |
| `0x00408c00` / `0x004089b0` | Damage dispatch — writes into an unresolved array (§2.4, §6 item 3) |
| `0x00403210` | Derelict/crew-wipeout handler, confirmed §5 |
| `0x00465060` | `45.0` — reused numerator in the torpedo damage formula (same constant as phaser's, `COMBAT_DAMAGE_MAP.md` §8) |
