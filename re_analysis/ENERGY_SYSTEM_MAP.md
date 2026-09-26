# Begin 3 Energy System Map

**Status:** Path B5 complete (weapon power draw traced, `FUN_0040b510` identified). This document
supersedes the energy-system claims in `PATH_B3_FINDINGS.md` and `B3_PROGRESS.txt` (kept for
historical record — see the banners added to those files). It also supersedes the "4:1 WES:RES
ratio" framing in `docs/handoff-PATH-B2-energy-analysis.md`.

**Binary:** `original_game/Begin.exe` — **Date:** 2026-09-26 — **Tooling:** Ghidra (live MCP
connection), `energy_system_analysis.py`

---

## 0. Headline correction

Path B2 hypothesized a single **4:1 WES:RES ratio** — Weapon Energy Storage vs. Reactor Energy
Storage — living at address `0x00464688`. That hypothesis does not survive contact with the
binary:

1. `0x00464688` contains **100.0**, not 4.0. It is a generic percent→fraction constant used in
   **35+ functions** across the entire codebase — collision math, RNG, UI display, several
   subsystems' charge cycles. It has nothing to do with energy balance specifically.
2. The real `4.0` literal (`0x00464ad8`) exists, but it is **not one unified ratio**. It's reused
   by the compiler's constant pool for at least two distinct, real game-balance rules (Drive
   charge/drain rate; Shield reinforcement-tier power cost) **and** several unrelated formulas
   (a collision-detection quadratic, a UI threshold, a physics coefficient).
3. **Weapons** (Phaser Banks, confirmed Path B5 — see §3.3b) **do not use the 4.0 constant, or
   any reactor-relative ratio, at all.** Their cost is a flat reactor-rate deduction plus a
   separate type-specific per-tick charge cap. This was the last open piece of the "WES:RES"
   hypothesis, and it does not hold up.

The line in the manual/game text — *"Reinforced shields require 4x power"* (`0x004662f0`) — is
not a metaphor for a weapon/reactor exchange rate. It's a literal description of one confirmed
mechanism: **reinforced shields cost 4× the power of regular shields**, implemented in
`FUN_0040b320` (§3.2 below). **Path B5 confirmed no analogous relationship exists for weapons** —
see §3.3b.

---

## 1. Three separate "ship" structures — do not conflate them

This was the single biggest source of confusion in Path B3. The binary has **three structurally
unrelated layouts** that all get called "the ship struct" in earlier notes:

| Structure | Where | Size | Purpose |
|---|---|---|---|
| **Class Data** (static) | e.g. file offset `0x0008858c` for Heavy Cruiser | ~1872 bytes/class | Per-ship-*type* template (crew, base counts, stats). See `ship-struct-analysis.md`. |
| **Runtime Object** (live) | heap-allocated, one per ship instance | `0xc80` (3200 bytes) | The actual simulation state each frame. See `PATH-B-FINDINGS.md`; confirmed further in §2. |
| **Display/Summary struct** | built fresh for `FUN_0040f4b0` (status-report text) | smaller, different field order | A flattened snapshot assembled just for printing the status screen. Offsets here (§2.2) do **not** match the Runtime Object's offsets, despite both being "the ship" conceptually. |

**Lesson for future sessions:** matching field offsets between two functions is not evidence
they read the same struct. Confirm via the object's actual size, its allocator, or (most
reliably) a string/label the code prints while touching that offset.

---

## 2. Structure layouts

### 2.1 Runtime Ship Object (`0xc80` bytes) — confirmed subsystem offsets

From `PATH-B-FINDINGS.md`, and **confirmed/extended this session** by tracing real per-frame
update code in `FUN_00404250`:

| Offset | Subsystem | Constructor | Confirmed by |
|---|---|---|---|
| `0xe4` | → pointer to Class Data | — | Path B |
| `0xe8` | Crew count | — | Path B |
| `0xec` | Unidentified subsystem | `FUN_00418080` | **Not resolved** — several charge functions chase a pointer near here (`+0xe8`/`+0xec`) to reach a rate double at `+0x38` in the target; unclear if this offset itself is that target or a link to it. Open question. |
| `0x150` | **Reactor** array | `FUN_0040a830` | Path B (class-data read at class+0x58) |
| `0x708` | **Drive** (Warp) array | `FUN_00409860` | **This session** — `FUN_00418de0` (Drive's fire-event notifier) passes the literal string `"Drive"` |
| `0x7f8` | **Shield** array | `FUN_0040af50` | **This session** — `FUN_0040b4a0` (Shield::UpdatePower) operates on this exact offset from `FUN_00404250` |
| `0xb88`/`~0xbb8` | **Tractor beam** | `FUN_004094f0` | **This session** — tied to the `"Our tractor beam has failed due to lack of power.\n"` string in `FUN_00404250` |
| `0xc20` | **Cloak** | `FUN_0040a5e0` | **This session** — `FUN_0040a690` (Cloak::UpdatePower) operates on this offset; matches `"We have uncloaked due to lack of power.\n"` |
| `0xc58`/`0xc5c` | Ship linked-list next/prev | — | Path B |

Other subsystem slots (`0x2a0`, `0x438`, `0x454`, `0x470`, `0x9c0`, `0xc00`, `0xbf0`) are
constructed (per `PATH-B-FINDINGS.md`) but not yet identified by name.

### 2.2 Display/Summary struct (fed to `FUN_0040f4b0`, the status-report printer)

Walked the **entire** function in address order this session (not just isolated snippets) and
matched every section against its actual printed format string. This is what corrects Path B3's
per-field guesses:

| Offset | Field | Confirmed via |
|---|---|---|
| `0x58` | Reactor type 1 count | printed with `"%d Reactor%s providing %.0lfeu each.\n"` (`0x466550`) |
| `0x88` | Reactor type 1 value | same section |
| `0x90` | Reactor type 2 count | same format string, second call |
| `0xc0` | Reactor type 2 value | same section |
| `0xc8` | **Phaser Bank count** | `"%d Phaser bank%s with %.0lf maximum range. %s "` (`0x4664c8`) |
| `0xf8`,`0x100`,`0x108` | Phaser Bank stats (range + 2 more) | same section |
| `0x110` | **Torpedo Tube count** | `"%d Torpedo tube%s of "%s" class. %s requires "` (`0x46644c`) |
| `0x150` | ptr → tube name/class data | same section |
| `0x158` | **Probe Launcher count** | `"%d Probe launcher%s of "%s" class.\n"` (`0x4663f0`) |
| `0x188` | ptr → launcher name/class data | same section |
| `0x1d0` | Shield type/flag (section gate) | precedes the shield block |
| `0x200` | Shield capacity/count | `"%d Shield generators each supplying %.0lfeu of "` (`0x466384`) |
| **`0x208`** | **Shield charge fraction** (×100 for display = **FMUL #1**, `0x0040f871`) | printed immediately before `"is %.0lfeu per shield with a regeneration of %.2lf%%.\n"` and the `"Reinforced shields require 4x power.\n"` line |
| `0x210`,`0x218` | More shield stats | same section |
| `0x190` | Drive count | `"%d Warp drive%s providing %.0lfeu%s with an "` (`0x466270`) |
| `0x1c0` | Drive base rate | shared with `FUN_00409740`'s live rate chase |
| **`0x1c8`** | **Drive charge fraction** (×100 for display = **FMUL #2**, `0x0040f997`) | same section; matches the fields `FUN_00409740` updates |
| `0x38` | Divisor used in the drive ratio display | same section |
| `0x20` | Drive current/cap value | same section |
| `0x384`,`0x388` | Cloak-adjacent gate fields | precede the section containing FMUL #3 |
| **`0x390`** | **Cloak(?) charge fraction** (×100 for display = **FMUL #3**, `0x0040fc87`) | positional match — printed in the section right after the Drive block, pattern-consistent with Cloak's status readout; not confirmed by a literal string the way #1/#2 are |

**Path B3's original field guesses were wrong on all three FMUL operands:**

| FMUL | Path B3 guessed | Actually |
|---|---|---|
| `0x0040f871` (`+0x208`) | "unknown field" | **Shield** charge/regen percentage |
| `0x0040f997` (`+0x1c8`) | "reactor power level" | **Drive** charge percentage |
| `0x0040fc87` (`+0x390`) | "shield capacity" | Likely **Cloak** charge percentage (unconfirmed) |

---

## 3. The two real "4×" mechanisms

### 3.1 Drive charge/drain (`FUN_00409740`, called from `FUN_00409a70`, called from `FUN_00404250` on the `+0x708` array)

Per-slot record is **`0x38` (56) bytes** — confirmed via raw disassembly
(`ADD dword ptr [ESP+0x10], 0x38`), *not* `0x1c` as first read off the decompiler (a `ushort*`
pointer-arithmetic trap — Ghidra scales `p += 0x1c` by `sizeof(ushort)`, i.e. by 2, giving the
true 0x38-byte stride. Always verify a stride against the raw `ADD`, not the decompiler's typed
pointer arithmetic.)

| Slot offset | Field |
|---|---|
| `+0x14` | Phase counter, 0–100. `<100` = charging, `>=100` = ready/depleting |
| `+0x20` | Stored energy accumulator |
| `+0x28` | This-tick delta/output |
| `+0x30` | Back-pointer to ship → chases `+0xe8` → `+0x38` (reactor rate double) |

```c
// charging phase (phase < 100):
frac  = (100 - phase) / 100.0;                  // 0x464688 — generic percent→fraction
delta = (ratio_in - frac * reactor_rate) * 4.0; // 0x464ad8 — the real constant
energy += delta;
if (energy >= 12.0) {                            // 0x465088 — "ready" threshold
    if (energy > 40.0 && ratio_in > 0.0) {        // 0x465488 — "fire" threshold
        // percent-chance roll (see FUN_004013e0, uses the SAME 100.0 constant again)
        // success -> phase = 100 (switch to depleting)
    }
}
// depleting phase (phase >= 100):
energy -= reactor_rate * 4.0;                    // same 4.0, same rate, opposite direction
```

End of the per-frame driver (`FUN_00409a70`) also applies `× 0.5` (`0x00464bd0`) to the leftover
reactor pool value it returns.

**Interpretation:** Drive both charges and drains at `reactor_rate × 4`. The 4.0 here scales
Drive's energy exchange rate relative to the reactor's raw output — symmetric in both
directions.

### 3.2 Shield reinforcement cost (`FUN_0040b320`, called from `FUN_0040b4a0`, called from `FUN_00404250` on the `+0x7f8` array)

```c
// summing power draw across all shield units, array stride 0x48 bytes:
for each shield unit:
    weight = (unit.type == 10) ? 4.0     // 0x464ad8 — REINFORCED shield
           : 1.0;                        // type == 8 = regular shield, or default
    total_draw += unit.value * weight;
reactor_pool -= total_draw;
```

This **is** "Reinforced shields require 4x power," literally. A companion function
(`FUN_0040aea0`) handles each shield unit's individual charge/regen using the generic `100.0`
percent constant — same pattern as everywhere else, no special ratio there.

### 3.3 What does NOT use either mechanism

**Cloak** (`FUN_0040a690`, ship `+0xc20`) is architecturally unrelated to both of the above:

```c
draw = crew_count * per_crew_cost + base_cost;   // flat formula — no 4.0, no percent-cycle
pool -= draw;
if (pool < 0) fail;
```

Matches the flat `"requiring %.0lfeu"` cloak cost text. No charge/discharge cycle, no
type-weighted sum.

**Weapons** (Phaser Banks / Torpedo Tubes / Probe Launchers) — not yet traced. Their
power-draw functions are unknown at time of writing. See Open Questions.

### 3.3b Weapon (Bank) power draw — resolved in Path B5

Traced `"Charging %d bank%s!\n"` (`0x00467b64`) all the way to the real per-unit energy function.
Two things worth flagging about *how* this was found: neither the UI-command function
(`0x00412bb0`) nor the state-setter it calls (`0x00408b80`) had a Ghidra-defined function at their
address, even though `0x00408b80` is a direct `call` target — Ghidra's auto-analysis simply never
reached this region. Both were decoded by hand from raw bytes (see `binary_tools.py` /
`energy_system_analysis.py`'s `file_offset_to_va()`, added this session as the inverse of
`va_to_file_offset()`).

**The command chain** (`Bank::ChargeCommand` at `0x00412bb0`, called when the player issues the
charge command): parses which banks were selected, then calls a shared state-setter
(`Bank::MarkUnitsState`, `0x00408b80`) with a numeric code (`7` = charge) that just writes that
code into each selected unit's `+0x28` state byte — after checking the unit is available and not
already maxed. `"Charging %d bank%s!\n"` prints when that returns 0 failures. **None of this is
energy math** — it's a UI acknowledgment that a state flag got set.

**The real energy draw** is per-frame, exactly parallel to Drive/Shield/Cloak, called from
`FUN_00404250` on `ship+0x438` (confirming this as the Bank slot):

```c
// FUN_004087b0 - called once per bank unit, per frame, from FUN_00408b40 (array driver)
// this = one Bank unit; pool = shared per-frame accumulator (local_88 in FUN_00404250)
if (unit.state != 8 && unit.linkRec[0] > 0 &&
    unit.currentLevel <= unit.linkRec->max && unit.flag_0x30 == 0)
{
    double reactorRate = /* chased via unit+0x20 -> +0x14 -> +0x28 */;
    pool -= reactorRate;

    if (pool >= 0.0) {
        TypeRec *t = unit.typeRecord;                          // +0x24
        double remaining = t->maxCharge - unit.accumulated;    // +0x38 - +0x40
        if (remaining <= 0.0) { unit.ready = 1; return 1; }    // already fully charged
        double perTickCap = t->maxCharge / t->chargeRate;      // +0x38 / +0x30
        if (perTickCap < remaining) remaining = perTickCap + 0.001;  // 0x00465440 epsilon
        unit.accumulated += min(remaining, pool);
        pool -= remaining;
        unit.ready = 1;
    } else {
        unit.ready = 0;
        unit.accumulated = 0.0;   // reactor undersupplied -> charge progress resets to ZERO
    }
}
```

**No `0x00464ad8` (4.0), no `0x00478798`, no ratio at all.** Weapon power cost is a flat
reactor-rate deduction plus a *separate*, type-specific per-tick charge cap (`maxCharge /
chargeRate`) — nothing scales relative to the reactor the way Drive and Shield do. Bank's failure
mode is also harsher than Drive/Shield's: if the reactor can't even cover its own rate for a
single tick, the bank's accumulated charge progress is wiped to zero rather than just pausing.

**Conclusion: there was never a real "WES:RES 4:1" mechanic.** The manual's "4x power" line was
always Shield-specific, exactly as suspected. This closes Open Question #1 from Path B4.

One loose thread for a future session: the reactor-rate chase here (`unit+0x20 → +0x14 → +0x28`)
uses a different offset path than Drive/Shield's (`ship+0xe8/0xec → +0x38`) — worth keeping in
mind for Open Question about `ship+0xec`'s identity (§7).

### 3.5 `FUN_0040b510` — NOT an energy function (resolved in Path B5)

Path B4 flagged `FUN_0040b510` as suspicious because it uses both the 4.0 and 0.5 constants in a
Drive-like phase-cycle shape. Path B5 traced its three callers (`FUN_00409530`, `FUN_0040a630`,
`FUN_0040b740` — all thin per-unit wrappers differing only in which offset holds a "link" pointer)
up one more level, to a single shared driver: `FUN_004035b0`.

**`FUN_004035b0` is a completely separate per-frame system from `FUN_00404250`'s reactor pool.**
It computes a ship-wide "power-to-weight ratio":

```c
void FUN_004035b0(Ship *ship) {
    double ratio = ship->cachedReactorOutput(+0xf0) / ship->classData->deadWeightTonnage(+0x18);
    if (ship->linkedShip(+0x148) != NULL) {
        double linkedRatio = linkedShip->cachedReactorOutput(+0xf0)
                            / linkedShip->classData->deadWeightTonnage(+0x18) * linkedShip->+0x390;
        ratio = max(ratio, linkedRatio);
    }
    if (ratio <= 0.1 /* 0x00464b08 */) return;    // "brownout" floor - skip the whole pass

    // roll + report a phase-cycle event for 13 subsystem slots; only 5 of them route through
    // FUN_0040b510: ship+0xb50, Tractor(+0xb88), +0xbb8, +0xbf0, Cloak(+0xc20)
    ...
}
```

`class+0x18` is documented in `PATH-B-FINDINGS.md` as **Dead Weight Tonnage**, and
`FUN_004035b0` is independently flagged there as referencing the string `"reactor"` — both support
reading `ship+0xf0` as a cached total reactor-output value (its writer wasn't tracked down this
session — open thread). `FUN_0040b510` itself is a generic phase/percent-chance cycle (reusing
`FUN_004013e0`'s percent-roll helper, same as Drive), and its results are reported through
`FUN_004182e0`, a generic `"%d %s%s %s!\n"` notifier gated on "is this the player's own ship."

**This is a probabilistic subsystem-malfunction/event system, not an energy drain.** It reuses the
same 4.0 and 0.5 literals as Drive/Shield purely coincidentally — the same "narrow xref count
doesn't guarantee purpose-built" lesson from §8, now confirmed a second time. It also reclassifies
`ship+0xb50`, `+0xbb8`, and `+0xbf0`: they're not Drive/Shield/Bank-style continuous chargers:
they belong to this probabilistic-event family alongside Tractor and Cloak (which each *also* have
their own, separate, real continuous energy-draw functions from `FUN_00404250` — this is purely an
*additional* system layered on top).

---

## 4. Full constant catalogue (all values read directly from the binary, VA→file-offset fixed for Ghidra's `0x00400000` base)

| VA | Value | Confirmed role |
|---|---|---|
| `0x00464688` | **100.0** | Generic percent(0–100)→fraction(0.0–1.0). 35+ xrefs across the codebase — display formatting, `FUN_00409740` (Drive), `FUN_004013e0` (generic RNG percent-chance helper), `FUN_0040aea0` (Shield per-unit charge). **Not** energy-specific. |
| `0x00464680` | 1/32768 ≈ 3.0517578125e-05 | `rand()` normalizer (`RAND_MAX`=32767 assumption) — paired with 100.0 inside `FUN_004013e0`'s `rand()/32768.0 < percent/100.0` percent-chance roll. |
| `0x00464ad8` | **4.0** | The real "4×" literal. Confirmed purposeful uses: Drive charge/drain (§3.1), Shield reinforcement cost (§3.2). Confirmed *coincidental* (non-energy) reuses: quadratic-formula `b²−4ac` coefficient in collision detection (`FUN_004018b0`), a proximity threshold in a generic charge-status text picker (`FUN_004185e0`), an unrelated physics/repair coefficient (`FUN_00407220`). |
| `0x00478798` | 4.0 | A **second**, separate 4.0 literal in `.data`. **Zero direct-addressing xrefs found** — likely reached only via indexed/array-relative addressing Ghidra can't statically resolve. Unresolved — flagged for next session. |
| `0x00464bd0` | 0.5 | Used at the end of Drive's per-frame update (final pool scaling) and inside `FUN_0040b510` (unidentified, charge-cycle-shaped function). Shared "50%" factor; exact purpose not confirmed beyond Drive. |
| `0x00465088` | 12.0 | Drive's "ready" charge threshold. |
| `0x00465488` | 40.0 | Drive's "fire" charge threshold; also reused as a baseline distance in `FUN_004185e0`'s status-text picker. |
| `0x00464ad0` | (not yet decoded) | Seen used in `FUN_004018b0` as a minimum-distance-squared cutoff. Open. |
| `0x00464ac8` | (not yet decoded) | Seen used in `FUN_00407220`. Open. |
| `0x00464b08` | (not yet decoded) | Seen used in `FUN_0040aea0` as a minimum regen floor. Open. |

All of the above are readable with the fixed `energy_system_analysis.py` (see §6) —
`read_constant_at_address()` now uses Ghidra's normalized `0x00400000` base instead of the PE
header's own declared (and irrelevant) `0x00062e00` image base.

---

## 5. Confirmed function map

| Address | Name (informal) | Role |
|---|---|---|
| `FUN_0040f4b0` (`0x0040f4b0`) | Ship status display | Prints the whole status report; contains all 3 FMULs (§2.2) |
| `FUN_00404250` (`0x00404250`) | Ship per-frame subsystem update | The real driver — calls each subsystem's `UpdatePower`-style function on the Runtime Object |
| `FUN_00409740` (`0x00409740`) | Drive::ChargeCycle (per-unit) | §3.1 |
| `FUN_00409a70` (`0x00409a70`) | Drive::UpdateArray (per-frame driver) | Iterates the `+0x708` array, calls `FUN_00409740` per slot |
| `FUN_00418de0` (`0x00418de0`) | Drive fire-event notifier | Passes literal `"Drive"` — the string that identified this subsystem |
| `FUN_004013e0` (`0x004013e0`) | Generic percent-chance RNG helper | `rand()/32768.0 < percent/100.0` |
| `FUN_0044c1c0` (`0x0044c1c0`) | Generic round-to-int64 | FPU rounding helper, not game-specific |
| `FUN_0040b4a0` (`0x0040b4a0`) | Shield::UpdatePower | §3.2, operates on `+0x7f8` |
| `FUN_0040b320` (`0x0040b320`) | Shield power-budget summation | The literal 4× reinforced-shield weighting |
| `FUN_0040aea0` (`0x0040aea0`) | Shield::ChargeCycle (per-unit) | Uses generic 100.0, no 4.0 |
| `FUN_0040a690` (`0x0040a690`) | Cloak::UpdatePower | §3.3, flat-cost formula, operates on `+0xc20` |
| `FUN_004018b0` (`0x004018b0`) | Collision detection | Quadratic-formula intersection test; incidental 4.0 use only |
| `FUN_00412bb0` (`0x00412bb0`) | Bank::ChargeCommand | §3.3b. UI command handler, not energy math. **Not in Ghidra's function database** — hand-decoded from raw bytes; Ghidra's auto-analysis never reached this region. |
| `FUN_00408b80` (`0x00408b80`) | Bank::MarkUnitsState | §3.3b. Sets a per-unit state byte from a numeric command code. **Also not in Ghidra's function database**, despite being a direct `call` target. |
| `FUN_00408b40` (`0x00408b40`) | Bank::UpdateArray (per-frame driver) | §3.3b. Iterates `ship+0x438`'s unit array, calls `FUN_004087b0` per slot. Ghidra has this one defined normally. |
| `FUN_004087b0` (`0x004087b0`) | Bank::ChargeCycle (per-unit) | §3.3b. The real weapon energy-draw function. No 4.0, no ratio. |
| `FUN_004035b0` (`0x004035b0`) | Ship-wide power-to-weight ratio + malfunction-event driver | §3.5. Separate per-frame system from `FUN_00404250`. Already flagged (but not analyzed) in `PATH-B-FINDINGS.md` as "Energy Processing." |
| `FUN_0040b510` (`0x0040b510`) | Subsystem malfunction/event phase-cycle | §3.5. Uses 4.0 and 0.5, but NOT energy-related — driven by `FUN_004035b0`'s power-to-weight ratio, not the reactor pool. Callers: `FUN_00409530` (`+0xb88` Tractor, `+0xbf0`), `FUN_0040a630` (`+0xc20` Cloak), `FUN_0040b740` (`+0xb50`, `+0xbb8`). |
| `FUN_004182e0` (`0x004182e0`) | Generic malfunction/event notifier | §3.5. `"%d %s%s %s!\n"`, gated on `this ship == player's own ship`. |

---

## 6. Tooling notes

`energy_system_analysis.py` had a real bug fixed this session: `va_to_file_offset()` was
computing RVAs against the **PE header's own declared `image_base`** (`0x00062e00` — an unusual
value for this binary), instead of the **`0x00400000`** address Ghidra actually normalizes
everything to. This silently broke lookups for any address outside `.text` (e.g. `0x00465088`,
`0x00465488`, `0x00464bd0` all raised "not found in any PE section" before the fix, even though
they're valid `.rdata` addresses) — that's exactly how the 12.0/40.0/0.5 constants stayed hidden
until this session. Fixed by introducing a `GHIDRA_IMAGE_BASE = 0x00400000` constant and using it
for the RVA conversion instead of the header's field. See `PYTHON_TOOLS.md` for the full changelog.

---

## 7. Open questions

**Closed in Path B5:**

1. ~~Trace actual weapon power-draw.~~ **Done — §3.3b.** No 4.0, no ratio; flat reactor-rate
   deduction + type-specific per-tick charge cap. The "WES:RES 4:1" hypothesis does not hold for
   weapons, closing this out for good.
2. ~~Identify `FUN_0040b510`.~~ **Done — §3.5.** Not an energy function at all — a
   subsystem-malfunction/event system driven by a ship-wide power-to-weight ratio
   (`FUN_004035b0`), coincidentally reusing the 4.0/0.5 literals.

**Still open for Path B6:**

3. **Resolve the second `4.0` at `0x00478798`.** No direct-addressing xrefs were found; it's
   probably reached through computed/indexed addressing (an array of doubles, accessed via a
   register-relative index) rather than a literal `FMUL [addr]`. Would need a broader
   instruction-pattern search, or finding the array's base and stride.
4. **Confirm `ship+0xec`'s identity.** `FUN_00418080` constructs it; several charge functions
   chase a pointer near this offset to reach a reactor-rate double at `+0x38` in whatever it
   points to. Is `0xec` itself the Reactor link, or a distinct "power distribution" object? Path
   B5 adds a wrinkle: Bank's charge function (§3.3b) reaches its own reactor-rate double via a
   *different* chase (`unit+0x20 → +0x14 → +0x28`) — is this the same underlying Reactor object
   reached a different way, or a genuinely separate link?
5. **Explain how the Display/Summary struct (§2.2) gets built.** It is clearly assembled fresh
   for `FUN_0040f4b0` and does not share the Runtime Object's field layout. Finding its
   construction site would let us map it back to Runtime Object offsets directly, rather than
   via string-format inference.
6. **Decode the two still-open adjacent constants** (`0x464ad0`, `0x464ac8`) — values are known
   (`1e-08`, `1.0`) but their functional role within `FUN_004018b0`/`FUN_00407220` isn't confirmed.
7. **New from Path B5 — confirm `ship+0xf0`.** Used in `FUN_004035b0` as a "cached reactor output"
   value (divided by class-data Dead Weight Tonnage at `+0x18` to get a power-to-weight ratio).
   Strongly implied by the `"reactor"` string xref already noted in `PATH-B-FINDINGS.md` for this
   same function, but its *writer* wasn't tracked down this session.
8. **New from Path B5 — what event does `FUN_0040b510`'s cycle actually represent?** We know
   *that* it fires a generic `"%d %s%s %s!\n"` notification (via `FUN_004182e0`) for 5 subsystem
   slots (`+0xb50`, Tractor `+0xb88`, `+0xbb8`, `+0xbf0`, Cloak `+0xc20`) when a power-to-weight
   floor is cleared, but not the specific noun/verb substituted in (would need to trace
   `FUN_00401490`/`FUN_00401560`, the two calls made just before the notify, which likely set
   global "current message" state).
9. **New from Path B5 — name the remaining unlabeled subsystem slots.** `+0xb50`, `+0xbb8`,
   `+0xbf0`, `+0x2a0`, `+0x454`, `+0x470`, `+0x9c0`, `+0xc00` still have no confirmed subsystem
   name (Torpedo Tube / Probe Launcher / Battery / Scanner / etc. remain candidates). The RTTI
   class-name strings found this session (`.?AVTube@@`, `.?AVLauncher@@`, `.?AVBattery@@`,
   `.?AVScanner@@`, `.?AVLifeSupport@@`, `.?AVTransporter@@`, `.?AVImpulse@@` at `0x0048b3xx`-
   `0x0048b5xx`) are a promising new lead — each RTTI type-descriptor string is likely referenced
   from that class's vtable, which would let these slots be matched to concrete class names rather
   than guessed from position.

---

## 8. Methodology lessons (for the learner, not just the record)

- **A widely-referenced constant is usually generic, not game-specific.** `0x00464688`'s 35+
  xrefs was itself the tell that it wasn't a balance constant — narrowly-used constants (like
  the real 4.0's ~7 xrefs) are more likely purpose-built, though not guaranteed (see next point).
- **Even a narrow xref list can include coincidental reuse.** Don't assume every hit on a
  constant's address shares its "meaning" — check the actual formula shape. A `b² − 4ac`
  discriminant and a charge multiplier can legitimately share the same memory address for the
  literal `4.0`.
- **Decompiler pointer arithmetic scales by the pointee's type.** `ushort *p; p += 0x1c;` moves
  `p` by `0x38` bytes, not `0x1c`. When a stride matters, verify it against the raw disassembly's
  `ADD reg, imm`, not the decompiled C.
- **Ghidra's normalized load address can differ from the PE header's declared image base.** This
  binary's header claims `0x00062e00`; Ghidra (correctly, for analysis purposes) uses
  `0x00400000`. Any VA→file-offset conversion must use Ghidra's base.
- **A notify/logging call's string-literal argument is often the fastest way to identify a
  subsystem** — faster than reasoning about field offsets alone. Finding the literal `"Drive"`
  passed to a notifier settled an entire subsystem's identity in one step.
- **Matching offsets across two functions doesn't mean matching structs.** This binary has (at
  least) three differently-shaped "ship" structures. Confirm structural identity via
  size/allocator/label, not just "this offset looks similar to that one."
- **Zero xrefs to a string doesn't mean it's unreachable — it might mean Ghidra never analyzed the
  code that reaches it.** (Path B5.) `"Charging %d bank%s!\n"` had zero xrefs not because it lives
  in an indexed table (the working theory going in, by analogy with `0x00478798`), but because the
  `push offset str` instruction referencing it sits in a region Ghidra's auto-analysis never
  disassembled into a function at all — confirmed by finding the raw pointer via a byte-level
  search (`find_value_in_binary` + the new `file_offset_to_va()`) and discovering it decoded to a
  perfectly ordinary `push`/`call` pair. Even a direct `call` target (`0x00408b80`) can be missing
  from Ghidra's function database. When `get_function_by_address` / `decompile_function_by_address`
  both say "no function found," that's a statement about Ghidra's analysis coverage, not about
  whether real code exists there — check with a raw byte dump before concluding a dead end.
- **A charge-cycle-shaped function isn't automatically part of the energy system.** `FUN_0040b510`
  looked exactly like Drive's charge cycle (phase counter, percent-chance roll, 4.0 and 0.5
  literals) and was a reasonable person's first guess for a missing weapon subsystem. It turned out
  to belong to an entirely different mechanic (ship-wide power-to-weight-driven malfunction events)
  that just happens to share the same *shape* and the same *constants* as the real energy system.
  Structural similarity is a lead worth chasing, not a conclusion — the only thing that confirms
  "this is energy math" is whether the value being consumed is actually the shared reactor pool
  (`local_88` from `FUN_00404250`), which `FUN_0040b510` never touches.
