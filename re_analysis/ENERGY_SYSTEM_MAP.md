# Begin 3 Energy System Map

**Status:** Path B7 energy-system work complete. All 13 runtime subsystem slots are named, the
reactor-rate chase for every draw-based subsystem (Bank/Tube, Drive, Shield) is fully resolved to
one unified mechanism, and `ship+0xf0`'s construction-time value and zeroing condition are
confirmed. **A later class-data mapping session (§3.8/§3.9) found and fixed a session-crossing
off-by-4 file-offset bug that had mislabeled several class_data fields since Path B4/B7 — read the
correction banner below before trusting any pre-§3.9 claim about `ship+0xe8`, `ship+0xec`, `ship+0xf0`,
crew, or DWT offsets.** This document supersedes the energy-system claims in `PATH_B3_FINDINGS.md`
and `B3_PROGRESS.txt` (kept for historical record — see the banners added to those files). It also
supersedes the "4:1 WES:RES ratio" framing in `docs/handoff-PATH-B2-energy-analysis.md`.

**Path B6 correction — read this before trusting any Path B5 claim about `ship+0xb88`,
`ship+0xbb8`, or `ship+0xc20`:** Path B5's decompiler-based reading mis-attributed a failure
message to the wrong call site. `ship+0xc20` (`FUN_0040a690`) is **Life Support**, not Cloak.
`ship+0xb88` is **Cloak**; `ship+0xbb8` is **Tractor**. See §2.1 and §3.5b for the corrected table
and exactly how this was caught.

**Path B7 correction — read this before trusting Path B5/B6's `ship+0xe8` = "Crew count" claim,
or the "+0xe8/+0xec" hedge for the reactor-rate chase:** Both were wrong. `ship+0xe8` is a
**shuffled commanding-officer name pointer** (cosmetic flavor text), completely unrelated to
energy math. The real reactor-rate chase for Drive/Shield never touches `ship+0xe8` at all — it
goes through each unit's own array container, exactly like Bank/Tube. See §3.6 for the full
unified picture and §8 for how the mix-up happened (a second instance of the "matching offsets
across different structs" trap).

**Class-data mapping session correction — SUPERSEDES the Path B7 correction above and part of
§3.7. Read this before trusting anything about `ship+0xe8`, `ship+0xec`, or `ship+0xf0`:** Path
B7's own re-identification was itself wrong, caused by a newly-discovered **off-by-4 error in
`ship-struct-analysis.md`'s static file-offset table** (every ship class's `class_data` file
offset in that doc was 4 bytes too high — confirmed by a live memory read of a running game
process, see §3.9). The corrected facts:
- `ship+0xe8` is a shuffled **ship name** (`"Enterprise, Hornet, Trenton, Lexington, Defiant,
  Independence, Republic"` for the Heavy Cruiser class) — not a commanding-officer surname.
- `ship+0xec`'s inner `+0x8` field (built by `FUN_00418080`) is the shuffled **commanding-officer
  surname** (`"Webster, Bronson, Eastwood, Stone, Pike, Austin, Montgomery"`) — and reading it is
  **not a bug**. `class_data+0x14` is a genuine pointer field (confirmed by both the corrected
  static data and by disassembly), not the crew integer Path B7 thought it was.
- `ship+0xf0` is a **crew**-derived value (`*(ushort*)(class_data+0x18)`, and `class_data+0x18` is
  crew, not DWT). The "ratio starts at 1.0" observation in §7 item 7 still holds, but the
  "power-to-weight" label does not — see §3.9 and the revised §7 item 7.

Full writeup: §3.9.

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
| `0xe8` | **Shuffled ship-name pointer** | `FUN_004011b0` (via ship ctor directly, not `FUN_00418080`) | **Path B7, corrected in the class-data mapping session (§3.9)** — a pointer to one of several NUL-terminated ship-name strings (`class_data+0x10`'s table: `Enterprise, Hornet, Trenton, Lexington, Defiant, Independence, Republic` for Heavy Cruiser — Path B7 originally misattributed this table as commanding-officer surnames; the actual surname pool is a separate table at `class_data+0x14`, used by `ship+0xec+0x8` instead, not `ship+0xe8`), assigned once at construction by a genuine Fisher-Yates shuffle + round-robin dispenser (`FUN_00401030`/`FUN_004011b0`). **Corrects Path B's "Crew count?" guess** — that guess was already hedged with a `?` and never verified; the real crew count is `class_data+0x18` (confirmed by code and by a live memory read — see §3.9). `ship+0xe8` plays no role in any reactor-rate/energy formula — see §3.6. |
| `0xec` / `0xf0` | Small inline record: `+0xec+0x8` = shuffled commanding-officer surname; `+0xf0` = crew-copy int | `FUN_00418080` | **Corrected in the class-data mapping session (§3.9)** — `ship+0xec` is a self-contained ~0x24-byte inline object (self-pointer to the ship at `+0`, then several fields — see §3.7). **It has nothing to do with the reactor-rate chase**; that was a hedge in Path B5/B6 that didn't survive disassembly (§3.6). Its own `+0x8` field is a legitimate shuffled surname pointer, not a bug (§3.7/§3.9). Its `+4` field is `ship+0xf0` — confirmed set at construction to a raw `uint` copy of `class_data+0x18`, which is **crew**, not DWT as previously documented (§3.9) — and confirmed (§3.7/§7) to be read as a plain **integer** (`FILD`, not `FLD`) by `FUN_004035b0`, where it's divided by crew to get a ratio that starts at `1.0` (not a "power-to-weight" ratio). No per-frame writer was found for it during normal play — see §7 item 7. |
| `0x150` | **Reactor** array | `FUN_0040a830` | Path B (class-data read at class+0x58); malfunction noun `"reactor"` (Path B6) |
| `0x2a0` | **Battery** array | — | **Path B6** — malfunction noun `"battery cell"` in `FUN_004035b0`; its per-frame function `FUN_004091e0` sums the array and *feeds power into* the shared pool in `FUN_00404250`, rather than drawing from it |
| `0x438` | **Bank** (Phaser) array | `FUN_00408e60` (**corrects** `PATH-B-FINDINGS.md`'s stale `FUN_00408920`, an address with no defined function boundary — Path B7, §3.6) | Path B5 (§3.3b); malfunction noun `"bank"` (Path B6) |
| `0x454` | **Tube** (Torpedo) array | — | **Path B6** — malfunction noun `"tube"`; per-unit charge function `FUN_0040c460` is a near-exact structural twin of Bank's `FUN_004087b0` (same offsets, same `0x00465440` epsilon) |
| `0x470` | **Launcher** (Probe) array | — | **Path B6** — malfunction noun `"probe launcher"`; ordinary per-unit pool draw, `FUN_0040a560` |
| `0x708` | **Drive** (Warp) array | `FUN_00409860` | Path B5 — `FUN_00418de0` (Drive's fire-event notifier) passes the literal string `"Drive"`; malfunction noun `"warp drive"` (Path B6) |
| `0x7f8` | **Shield** array | `FUN_0040af50` | Path B5 — `FUN_0040b4a0` (Shield::UpdatePower) operates on this exact offset from `FUN_00404250`; malfunction noun `"shield generator"` (Path B6) |
| `0x9c0` | **Transporter** array | — | **Path B6** — malfunction noun `"transporter"`; draw gated on a `state==7` ("beaming") flag, `FUN_0040bcd0` |
| `0xb50` | **Scanner** array | — | **Path B6** — malfunction noun `"scanner"`; draw with a "linked" bypass condition, `FUN_0040aaf0` |
| `0xb88` | **Cloak** | `FUN_0040a5e0` | **Path B6, corrects Path B5** — malfunction noun `"cloak"`; `FUN_004095b0` is the function whose failure is followed by `"We have uncloaked due to lack of power.\n"` in `FUN_00404250`'s raw disassembly. Path B5 attached this message to `0xc20` instead — a decompiler variable-reuse misread, see §3.5b. |
| `0xbb8` | **Tractor beam** | `FUN_004094f0` | **Path B6, corrects Path B5's hedge** — malfunction noun `"tractor"`; `FUN_0040b990` is the function whose failure is followed by `"Our tractor beam has failed due to lack of power.\n"` |
| `0xbf0` | **Impulse** (engine) array | — | **Path B6** — malfunction noun `"impulse engire"` [sic — the game's own string has this typo]; its per-frame function `FUN_00409bd0` *feeds power into* the shared pool, like Battery, rather than drawing from it |
| `0xc00` | *(no confirmed subsystem)* | — | **Path B6** — the one slot left over after matching all 7 previously-unnamed RTTI classes (Tube/Launcher/Battery/Scanner/LifeSupport/Transporter/Impulse) to 7 of the 8 previously-unnamed offsets. Not touched by `FUN_00404250` or `FUN_004035b0`. Likely unused, reserved, or a class with zero live instances — not investigated further. |
| `0xc20` | **Life Support** | — | **Path B6, corrects Path B5** — malfunction noun `"life support"`; `FUN_0040a690`'s dead-weight-scaled cost formula plus an incrementing fail-counter matches Life Support's escalating "failing → failed → environment failure in N seconds" message chain far better than Cloak's instant on/off. Path B5 called this Cloak; see §3.5b for why that was wrong. |
| `0xc58`/`0xc5c` | Ship linked-list next/prev | — | Path B |

All 13 subsystem slots are now named. `0xc00` remains the one unexplained offset (see above).

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

**Life Support** (`FUN_0040a690`, ship `+0xc20` — misidentified as Cloak in Path B5, corrected in
Path B6, see §3.5b) is architecturally unrelated to both of the above:

```c
draw = dwt_scaled_rate + base_cost;   // flat-ish formula — no 4.0, no percent-cycle
pool -= draw;
if (pool < 0) fail_counter++;         // escalating failure, not instant on/off
```

No charge/discharge cycle, no type-weighted sum. Cloak itself lives at `ship+0xb88`
(`FUN_004095b0`, §3.5b) and uses a simpler flag-clear-on-shortfall formula.

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
// CORRECTED (§3.9): classData+0x18 is crew, not DWT - see the note just below this block.
void FUN_004035b0(Ship *ship) {
    double ratio = ship->cachedReactorOutput(+0xf0) / ship->classData->crew(+0x18);
    if (ship->linkedShip(+0x148) != NULL) {
        double linkedRatio = linkedShip->cachedReactorOutput(+0xf0)
                            / linkedShip->classData->crew(+0x18) * linkedShip->classData->+0x390;
        ratio = max(ratio, linkedRatio);
    }
    if (ratio <= 0.1 /* 0x00464b08 */) return;    // "brownout" floor - skip the whole pass

    // roll + report a phase-cycle event for 13 subsystem slots; only 5 of them route through
    // FUN_0040b510: ship+0xb50, Tractor(+0xb88), +0xbb8, +0xbf0, Cloak(+0xc20)
    ...
}
```

**Correction (class-data mapping session, §3.9): `class_data+0x18` is not DWT — it's crew.** This
was believed to be DWT since Path B4/`PATH-B-FINDINGS.md`, but that was built on the same off-by-4
file-offset bug §3.9 found and fixed. The pseudocode above should read `ship->crew(+0x18)` in place
of `deadWeightTonnage(+0x18)` in both places it appears. The ratio still starts at `1.0` for a
fresh ship (§3.9), but it's a crew-based ratio, not power-to-weight; `ship+0xf0`'s writer (aside
from construction) is still an open thread either way. `FUN_0040b510` itself is a generic
phase/percent-chance cycle (reusing
`FUN_004013e0`'s percent-roll helper, same as Drive), and its results are reported through
`FUN_004182e0`, a generic `"%d %s%s %s!\n"` notifier gated on "is this the player's own ship."

**This is a probabilistic subsystem-malfunction/event system, not an energy drain.** It reuses the
same 4.0 and 0.5 literals as Drive/Shield purely coincidentally — the same "narrow xref count
doesn't guarantee purpose-built" lesson from §8, now confirmed a second time.

**Path B6 correction:** Path B5 stated `FUN_0040b510` is called for only 5 subsystem slots
(`ship+0xb50`, Tractor `+0xb88`, `+0xbb8`, `+0xbf0`, Cloak `+0xc20`), reached from three wrapper
functions. Path B6 fully disassembled `FUN_004035b0` (not just its callers) and found it actually
processes **all 13 subsystem slots**, one call each, every one preceded by a `PUSH` of a
type-specific noun string later consumed by `FUN_004182e0`'s generic `"%d %s%s %s!\n"` notifier
(see §3.5b for the full table and how it also fixed two wrong slot identities). Every slot
ultimately dispatches into `FUN_0040b510`'s shared logic either directly (confirmed independently
via RTTI vtables — see §3.5b) or through one of the thin wrapper functions Path B5 found.

### 3.5b Full `FUN_004035b0` slot table, and a correction to Path B5 (Path B6)

Path B6's Priority 1 task (name the remaining subsystem slots via RTTI) started from Ghidra's
recovered C++ namespaces for `Tube`, `Launcher`, `Battery`, `Scanner`, `LifeSupport`,
`Transporter`, and `Impulse`. Chasing each class's RTTI Complete Object Locator to its vtable
showed every one of these classes' vtable slot 0 and slot 1 point at the exact same two functions
— `FUN_0040b510` and `FUN_0040b5c0` — confirming these are the shared base class's (`System`)
default virtual implementations, inherited unmodified. That was a dead end for naming (vtable
slot 2 turned out to be a trivial per-unit reset stub, not an energy function), so naming instead
came from directly disassembling `FUN_004035b0` (§3.5) and reading off, for each of its 13 calls,
the exact string address `PUSH`ed immediately before it:

| Ship offset | Pushed noun string | Real subsystem | Per-frame draw function (from `FUN_00404250`) |
|---|---|---|---|
| `0x7f8`  | `"shield generator"` | Shield | `FUN_0040b4a0` (known) |
| `0x454`  | `"tube"`             | **Tube** | `FUN_0040caa0` → `FUN_0040c460` (Bank-twin) |
| `0x438`  | `"bank"`             | Bank (known) | `FUN_00408b40` |
| `0x470`  | `"probe launcher"`   | **Launcher** | `FUN_0040a560` |
| `0x708`  | `"warp drive"`       | Drive (known) | `FUN_00409a70` |
| `0x150`  | `"reactor"`          | Reactor (known) | `FUN_0040a9a0` |
| `0x2a0`  | `"battery cell"`     | **Battery** | `FUN_004091e0` (feeds pool, doesn't draw) |
| `0x9c0`  | `"transporter"`      | **Transporter** | `FUN_0040bcd0` |
| `0xb50`  | `"scanner"`          | **Scanner** | `FUN_0040aaf0` |
| `0xb88`  | `"cloak"`            | **Cloak** | `FUN_004095b0` |
| `0xbb8`  | `"tractor"`          | **Tractor** | `FUN_0040b990` |
| `0xbf0`  | `"impulse engire"`   | **Impulse** | `FUN_00409bd0` (feeds pool, doesn't draw) |
| `0xc20`  | `"life support"`     | **Life Support** | `FUN_0040a690` |

This directly caught a mistake in Path B5: Path B5's decompiled read of `FUN_00404250` attached
`"We have uncloaked due to lack of power.\n"` to the call on `ship+0xc20` (`FUN_0040a690`),
because Ghidra's pseudocode put the message inside the `if (iVar3 == 0) {...}` block that
*visually* followed that call. Disassembling `FUN_00404250` directly shows the actual `PUSH` of
that string sits in the **next** call block down — the one for `ship+0xb88` (`FUN_004095b0`) — not
the `0xc20` block, which has no message at all. The same raw-disassembly check confirmed
`"Our tractor beam has failed due to lack of power.\n"` belongs to `ship+0xbb8`
(`FUN_0040b990`), not `0xb88`.

The corrected identities also make more sense functionally: `FUN_0040a690` (`0xc20`) computes a
dead-weight-scaled cost and increments a fail counter on shortfall — a good match for Life
Support's escalating "failing → failed → total environment failure in N seconds" message chain —
while `FUN_004095b0` (`0xb88`) just clears a boolean flag to 0 on shortfall, matching Cloak's
instant on/off behavior exactly.

**Lesson:** a decompiled `if (cond == 0) { ...notify... }` block can visually "contain" a message
that actually belongs to a different call, when the decompiler reuses one variable name
(`iVar3`) across several unrelated checks in the same function. This is the same family of bug as
the `p += 0x1c` pointer-scaling trap from Path B4/B5 (§8) — when a string literal is doing the
identifying work, confirm its call site against raw disassembly, not decompiled pseudocode.

### 3.6 The real reactor-rate chase (Path B7) — resolves the `ship+0xe8`/`+0xec` hedge for good

Path B5/B6 left an open hedge: several charge functions chase "a pointer near `ship+0xe8`/`+0xec`"
to reach a rate double at `+0x38`. Path B7 disassembled the actual chase byte-by-byte for all three
draw-based subsystem categories and found **all of them share one mechanism, and none of them
touch `ship+0xe8` or `ship+0xec` at all**:

| Subsystem | unit's own field | → array's own fixed field | → final double |
|---|---|---|---|
| Bank/Tube | `+0x20` = back-pointer to unit's array container (`ship+0x438`/`+0x454`) | `array+0x14 = class_data+0xC8` (fixed, set once in the array ctor, **no shuffling**) | `+0x28` |
| Drive | `+0x30` = back-pointer to unit's array container (`ship+0x708`) | `array+0xe8 = class_data+0x190` (fixed, set once in `FUN_00409860`) | `+0x38` |
| Shield | `+0x34` = back-pointer to unit's array container (`ship+0x7f8`) | `array+0x1bc = class_data+0x1d0` (fixed, set once in `FUN_0040af50`) | `+0x48` |

Every subsystem's per-unit "reactor rate" is a **static, per-class constant** read through its own
array container — never the live Reactor runtime object at `ship+0x150`, and never `ship+0xe8`.
The `+0x30` field Drive's charge cycle (`FUN_00409740`) reads (`MOV EAX,[unit+0x30]` then
`MOV ECX,[EAX+0xe8]`) is the Drive array object, not the ship — confirmed by disassembling Drive's
array constructor (`FUN_00409860`) and finding the exact instruction that writes it:
`MOV [EDX+0x24],EAX` where `EDX = unit_k+0xc` and `EAX` is the array's own `this` pointer, landing
at `unit_k+0x30`. Shield's `FUN_0040af50` does the analogous write at `unit_k+0x34`. This is now
confirmed the same way Bank/Tube's `unit+0x20` was confirmed in Path B5/B6 — by finding the actual
constructor write, not by assuming offsets line up across different object types.

The final-offset values (`+0x28`, `+0x38`, `+0x48`) climbing by exactly `0x10` per category is a
strong hint that `class_data+0xC8`/`+0x190`/`+0x1d0` are all the same shape of per-subsystem-type
"TypeRecord" block (plausibly `+0x28`=cost, `+0x30`=charge rate, `+0x38`=capacity, matching Bank's
already-confirmed `t->maxCharge` at `+0x38` — see §3.3b), with each category reading whichever
field its own formula needs. The exact numeric values at `class_data+0xC8`/`+0x190`/`+0x1d0`
weren't verified this session — the class-data *pointer itself* (`ship+0xe4`, ultimately sourced
from globals like `DAT_00492fc8`) is written by runtime ship-selection code
(`FUN_00411b80`/`FUN_00415950`), not present as a fixed value in the static `.exe`, so it can't be
read from the file at rest. Confirming the actual numbers would need a live/dynamic read.

**What `ship+0xe8` actually is — CORRECTED in the class-data mapping session, see §3.9 for the full
story:** the ship constructor calls `FUN_004011b0(*(class_data+0x10))` directly (not through
`FUN_00418080`) and stores the result at `ship+0xe8`. Dumping the table `class_data+0x10` points to
(Heavy Cruiser) shows a packed sequence of NUL-terminated 17-byte-stride records: `Enterprise,
Hornet, Trenton, Lexington, Defiant, Independence, Republic` — a pool of **ship names**, not
commanding-officer surnames as Path B7 concluded (that conclusion was itself an artifact of the
off-by-4 file-offset bug §3.9 found — it was reading the *neighboring* table one field over).
`FUN_00401030` (called once, lazily, the first time `FUN_004011b0` runs on a given table) builds a
pointer array to each name and then runs a genuine Fisher-Yates shuffle on it (calling a
`rand()`-based helper, `FUN_00401490`, to pick swap indices); `FUN_004011b0` then hands out "the
next pointer in the shuffled array" on every call, advancing a cursor with wraparound. So
`ship+0xe8` is a **per-ship, shuffled, non-repeating cosmetic ship-name pointer** assigned once at
construction — nothing to do with energy.

### 3.7 `ship+0xec`'s own object — CORRECTED, there is no bug (see §3.9)

`FUN_00418080` builds a small (~0x24-byte) inline object at `ship+0xec`:

```c
this[0x0]  = ship;                                       // self back-pointer to the ship
this[0x4]  = (uint)*(ushort*)(class_data+0x18);          // crew-derived int -- this IS ship+0xf0
this[0x8]  = FUN_004011b0(*(ushort**)(class_data+0x14)); // shuffled surname pointer -- see below
this[0xc..0x20] = six pointers into class_data+0xC's table, at strides 0x00/0x11/0x22/0x33/0x44/0x55
```

**Path B7 called this a "likely genuine bug." It wasn't — the class-data mapping session found
Path B7's own base offset was wrong (§3.9).** `class_data+0x14` is a genuine pointer field —
confirmed by both the corrected static data and by raw disassembly (`MOV EDX,[EAX+0x14]` /
`PUSH EDX` / `CALL FUN_004011b0`, no dereference beforehand) — pointing to a pool of
commanding-officer surnames (`Webster, Bronson, Eastwood, Stone, Pike, Austin, Montgomery`) that is
structurally identical to `ship+0xe8`'s ship-name pool, just at a different `class_data` offset and
not shared with it. So `ship+0xec+0x8` is a **second, independent shuffled name pointer** (the
actual commanding-officer surname, misattributed to `ship+0xe8` by Path B7) — a real, working
cosmetic field, not scaffolding. `crew` (not DWT) is what `class_data+0x18` holds — see §3.9 for
why that matters beyond just this function.

The `this[0xc..0x20]` block (six pointers at fixed strides `0x00/0x11/0x22/0x33/0x44/0x55` into
whatever `class_data+0xC` points to) uses the exact same 17-byte-record-stride convention as the
two name pools, but isn't a name pool itself — see §3.9's note on `class_data+0xC` for what little
is known about it (not resolved this session).

`this[0x4]` (= `ship+0xf0`) is the one field of this object that's definitely alive — see §7 item 7
for its role in `FUN_004035b0`'s power-to-weight ratio.

### 3.8 The full class-data TypeRecord table — all 13 subsystems (class-data mapping session)

Path B7 confirmed the mechanism for 3 subsystem categories (§3.6): `unit → own array container →
array's own fixed field = a class_data+offset pointer`. This session (done as a prerequisite to
combat-damage work, since combat almost certainly reads these same per-class stat blocks) traced
**all 13 subsystem `ConstructArray`/constructor functions** called from the ship constructor
(`FUN_00404910`) and found every single one follows the same shape — confirming this is a general,
uniform mechanism across the entire class-data structure, not something special to Bank/Drive/Shield:

| Subsystem | Ctor function | Runtime array offset | `class_data` TypeRecord offset |
|---|---|---|---|
| Reactor | `FUN_0040a830` | `ship+0x150` | `+0x58` |
| Battery | `FUN_00409270` | `ship+0x2a0` | `+0x90` |
| Bank | `FUN_00408e60` | `ship+0x438` | `+0xC8` |
| Tube | `FUN_0040cae0` | `ship+0x454` | `+0x110` |
| Launcher | `FUN_00409e40` | `ship+0x470` | `+0x158` |
| Drive | `FUN_00409860` | `ship+0x708` | `+0x190` |
| Shield | `FUN_0040af50` | `ship+0x7f8` | `+0x1d0` |
| Transporter | `FUN_0040bac0` | `ship+0x9c0` | `+0x220` |
| Scanner | `FUN_0040aaa0` | `ship+0xb50` | `+0x260` |
| Cloak | `FUN_004094f0` | `ship+0xb88` | `+0x298` |
| Impulse | `FUN_00409b90` | `ship+0xbf0` | `+0x2d0` |
| Tractor | `FUN_0040b6f0` | `ship+0xbb8` | `+0x308` |
| LifeSupport | `FUN_0040a5e0` | `ship+0xc20` | `+0x348` |

That's **13 records**, running from `class_data+0x58` to `class_data+0x380` with gaps of
`0x38`/`0x40`/`0x48`/`0x50` (not a fixed stride — each subsystem type's record is a different size,
plausibly reflecting how many stat fields that subsystem type needs). 13 is not a coincidental
count: it exactly matches Path B6's independent finding that `FUN_004035b0` walks 13 subsystem
slots per frame. Two unrelated investigations (a per-frame malfunction driver, and per-class static
data) landing on the same number 13 is a strong cross-check that this is the complete, real list of
subsystem types — not an artifact of how far either investigation happened to look.

**Two distinct access mechanisms found, not one:**
- **Live pointer (most subsystems):** the array/unit stores the `class_data+offset` address itself
  and re-reads through it on demand every time it needs a stat (Bank/Tube/Launcher/Drive/Shield/
  Transporter/Cloak/Impulse/Tractor/LifeSupport/Reactor all do this).
- **One-time value snapshot (Battery, Scanner only):** the constructor reads an 8-byte **double**
  out of the TypeRecord (`class_data+0x90+0x30` for Battery, `class_data+0x260+0x30` for Scanner —
  both at TypeRecord-relative `+0x30`) and copies the *value* into the unit's own memory once, at
  construction. Later per-frame code for these two subsystems never touches `class_data` again for
  that field. Worth remembering when decoding TypeRecord internals (§ next steps) — a field read
  this way won't show up by searching for who dereferences the TypeRecord pointer at runtime, since
  after construction nothing does.

Every one of the 13 constructors was confirmed by decompiling the actual function and finding the
literal `class_data + constant` computation, not by pattern-matching offsets across functions (the
same discipline Path B7 called out in §8's "matching offsets across different structs" lesson) —
each one was checked individually rather than assumed from the first few.

**Next step, done later this same session (§3.9):** decode what's actually *inside* each
TypeRecord by dumping raw bytes across multiple ship classes and cross-referencing the manual's
per-class subsystem stats — which is exactly what surfaced the off-by-4 bug in §3.9 below.

### 3.9 The off-by-4 file-offset bug — corrects Path B7's `ship+0xe8`/`ship+0xec`/`ship+0xf0`
claims, and the earlier crew/DWT offsets throughout this document and `ship-struct-analysis.md`

Attempting step 2 (decode TypeRecord contents) by reading the Bank TypeRecord's raw bytes across
3 ship classes at the file offsets `ship-struct-analysis.md` had on record produced identical
garbage-looking doubles for every class — a red flag, since Bank stats being *literally identical*
seemed too strange to trust blindly. The smoking gun: Reactor's TypeRecord count field
(`class_data+0x58`, confirmed correct by disassembly — `ADD EDX,0x58` / `MOVZX EDX,word ptr [EDX]`
in `FUN_0040a830`) read as `0` for every ship class tested, which cannot be right — every ship has
reactors. A different field 4 bytes earlier (`+0x54`) held the *correct* reactor count instead.

**Root cause, confirmed with a live memory read:** `ship-struct-analysis.md`'s ship-class file
offsets (found in an earlier session by searching the binary for known manual numbers like
crew=450) were **all 4 bytes too high**. The developer ran the actual game under Wine
(`/home/nathan/Downloads/Begin301b151/Begin.exe`, confirmed byte-identical to
`original_game/Begin.exe` via `md5sum`), loaded a Heavy Cruiser, and — since the project's own
Linux user account can't `ptrace` another process's memory by default (`ptrace_scope=1`), so this
needed `sudo` run by the developer directly rather than any project-side permission change — we
read `/proc/<pid>/mem` at `DAT_004941c4` (a global the ship constructor's caller, `FUN_0040ccd0`,
stores the player's own ship pointer into), followed it to `ship+0xe4` (`class_data`), and compared
against the file. Confirmed module load address matched Ghidra's assumed `0x00400000` base exactly
(checked via `/proc/<pid>/maps`), so no ASLR/rebasing complication. Live `class_data` was **4 bytes
lower** than every file offset `ship-struct-analysis.md` had recorded. Re-reading the static file
with a `-4` correction on all 3 test classes fixed the reactor count for all of them (Heavy
Cruiser/Destroyer/Frigate: 7/5/3, matching the manual exactly) — see `read_live_classdata.py`.

**Critically, this bug never affected any offset confirmed by disassembly against the live runtime
pointer** — e.g. every TypeRecord offset in §3.8's table, and immediates like the `0x10`/`0x14`
used inside the ship constructor and `FUN_00418080`, all operate on `ship+0xe4`'s actual runtime
value and were always correct. What broke was cross-referencing one such code-confirmed offset
(`class_data+0x14`) against `ship-struct-analysis.md`'s mislabeled *file* offsets to guess what it
meant — Path B7 did exactly this and concluded `class_data+0x14` was "the crew integer." Corrected:

| Field | Old (wrong) label | Corrected |
|---|---|---|
| `class_data+0x00` | (not examined) | Unidentified, `0` for Heavy Cruiser. Not a vtable pointer (would be non-zero if it were) — open question, low priority. |
| `class_data+0x14` (code-relative, e.g. read by `FUN_00418080`) | "crew integer" (Path B7) | Pointer to a **ship-name** pool (`Enterprise, Hornet, Trenton, Lexington, Defiant, Independence, Republic` for Heavy Cruiser) — the same pool `ship+0xe8` uses (§3.6) |
| `class_data+0x18` (code-relative) | "DWT" (assumed in §7 item 7 and §3.7) | **Crew** (confirmed twice over: corrected static file AND the live memory read both give `450`/`250`/`175` for Heavy Cruiser/Destroyer/Frigate) |
| `class_data+0x1C` (code-relative) | "crew" (`ship-struct-analysis.md`'s old `+0x18`) | **DWT** (`20000`/`8500`/`6500`, matching manual ÷10 scaling) |

This means `class_data+0x10` (used by the ship ctor to build `ship+0xe8`) and `class_data+0x14`
(used by `FUN_00418080` to build `ship+0xec+0x8`) are **two separate, adjacent name-pool
pointers** — ship names and commanding-officer surnames respectively — not one pointer
misidentified as an integer. §3.6 and §3.7 above are corrected accordingly. `ship+0xf0` (a copy of
`class_data+0x18`, i.e. crew) is therefore crew-derived, not DWT-derived — which changes how to
read `FUN_004035b0`'s ratio (§7 item 7, revised): `local_48 = ship+0xf0 / *(ushort*)(class_data+0x18)`
is `(current copy of crew) / (crew)`, starting at exactly `1.0` for a fresh ship — the "starts at
1.0" observation survives, but this is **not** a power-to-weight ratio. What causes the numerator
to change over time is still unconfirmed (same open question as before, just retargeted from
"weight" to "crew" — plausibly a casualty count deducted from an initial crew-sized pool).

**Bonus finding from the same dive into `FUN_004035b0`:** when a ship is linked to another one
(`ship+0x148`, the same "linked ship" pointer already known from Scanner's power draw, §3.5b), the
function takes the *greater* of the ship's own ratio and `(linked ship's ratio) *
*(double*)(linked_ship_class_data+0x390)` — a cross-ship malfunction-risk propagation, presumably
for tractor-beam-linked ships. This is likely related to the still-unidentified `class_data+0x380`
field found earlier this session (§7 item 10) — both sit in the same tail region just past the last
TypeRecord (`+0x348`, LifeSupport) — but the connection wasn't confirmed further this session.

**TypeRecord contents, now decodable with the corrected offsets** (dumped across Heavy
Cruiser/Destroyer/Frigate — see the manual's per-class EU numbers in `all-ships-from-manual.md`):

| TypeRecord | `+0x00` | `+0x08` | `+0x30` | `+0x38` |
|---|---|---|---|---|
| Bank (`class_data+0xC8`) | count | `0.6` (universal) | `5.0` = reactorRate | `10.0` = maxCharge (matches §3.3b's confirmed `t->maxCharge`; chargeRate is at `+0x30`... see note) |
| Drive (`class_data+0x190`) | count | `0.2` (universal) | `285.0`/`285.0`/`268.0` — **exact match to the manual's per-class Warp EU** | `0.67`/`0.67`/`0.64` — a per-class rate/efficiency fraction |
| Shield (`class_data+0x1d0`) | count | `0.4` (universal) | `225.0`/`200.0`/`175.0` — **exact match to the manual's per-class Shield EU** | `0.72`/`0.63`/`0.5` — a per-class rate/efficiency fraction |

(Note: for Bank, §3.3b's already-confirmed field names are reactorRate=`+0x28`, chargeRate=`+0x30`,
maxCharge=`+0x38` — so the `+0x30` column above is Bank's chargeRate (`3.0`), not the same field
Drive/Shield have at `+0x30`. Bank's own values, dumped fresh: reactorRate=`5.0`, chargeRate=`3.0`,
maxCharge=`10.0`, and **identical across all 3 ship classes tested** — Phaser Banks apparently have
universal charge mechanics regardless of hull, with only the *count* of banks varying per class.
Drive and Shield, by contrast, clearly do vary their `+0x30`/`+0x38` fields per class.)

**Still unresolved:** `class_data+0xC` (the third pointer `FUN_00418080` touches, feeding
`ship+0xec+0xc..0x20`'s six fixed-stride pointers) is **not** a name pool — dumping it shows a mix
of doubles and a text fragment ("`We have examined your simulation results.`"), not repeating
NUL-terminated short strings. Left open rather than guessed at further.

**Methodology lesson (added to §8's list too):** a file-offset table built by *searching for known
numbers* can be off by a constant amount and still "confirm" several fields correctly — crew and
DWT both matched their manual values under the wrong base, because both were 4-byte-int-sized
fields sitting in a run of similar fields, so an off-by-4 read grabbed a plausible number one field
over. The bug only became visible when a *code-confirmed* field (Reactor's count, disassembly-
verified) was checked against that same table and came back nonsensical (`0` for a ship that must
have reactors). When a heuristic-derived offset and a code-derived offset disagree, trust the
code-derived one and go find out why the heuristic one is wrong — don't average them or assume the
heuristic was "close enough."

---

## 4. Full constant catalogue (all values read directly from the binary, VA→file-offset fixed for Ghidra's `0x00400000` base)

| VA | Value | Confirmed role |
|---|---|---|
| `0x00464688` | **100.0** | Generic percent(0–100)→fraction(0.0–1.0). 35+ xrefs across the codebase — display formatting, `FUN_00409740` (Drive), `FUN_004013e0` (generic RNG percent-chance helper), `FUN_0040aea0` (Shield per-unit charge). **Not** energy-specific. |
| `0x00464680` | 1/32768 ≈ 3.0517578125e-05 | `rand()` normalizer (`RAND_MAX`=32767 assumption) — paired with 100.0 inside `FUN_004013e0`'s `rand()/32768.0 < percent/100.0` percent-chance roll. |
| `0x00464ad8` | **4.0** | The real "4×" literal. Confirmed purposeful uses: Drive charge/drain (§3.1), Shield reinforcement cost (§3.2). Confirmed *coincidental* (non-energy) reuses: quadratic-formula `b²−4ac` coefficient in collision detection (`FUN_004018b0`), a proximity threshold in a generic charge-status text picker (`FUN_004185e0`), an unrelated physics/repair coefficient (`FUN_00407220`). |
| `0x00478798` | 4.0 | **RESOLVED (Path B6).** Row 128 of a 257-row **arctangent lookup table** running from VA `0x477ba8` to `0x479390` (24 bytes/row: three doubles `A, B, C`). `B` steps by exactly `1/32` from `0.03125` to `8.0`; `C(B)` equals `atan()` of the *next* step up, verified to full double precision (e.g. `C` at `B=0.0625` equals `atan(0.09375)` exactly), and the final row hard-codes `C = π/2` as the asymptotic clamp instead of computing `atan(8.0)`. `0x00478798` is simply the `B`-column cell holding `4.0` partway through this table — addressed by computed index elsewhere, which is why it has zero direct-addressing xrefs. Column `A` (~`1e-9`–`1e-8`) is a small per-row correction term whose exact interpolation role wasn't pinned down; not needed to confirm this table has nothing to do with energy. |
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
| `FUN_004018b0` (`0x004018b0`) | Collision detection | Quadratic-formula intersection test; incidental 4.0 use only |
| `FUN_00412bb0` (`0x00412bb0`) | Bank::ChargeCommand | §3.3b. UI command handler, not energy math. **Not in Ghidra's function database** — hand-decoded from raw bytes; Ghidra's auto-analysis never reached this region. |
| `FUN_00408b80` (`0x00408b80`) | Bank::MarkUnitsState | §3.3b. Sets a per-unit state byte from a numeric command code. **Also not in Ghidra's function database**, despite being a direct `call` target. |
| `FUN_00408b40` (`0x00408b40`) | Bank::UpdateArray (per-frame driver) | §3.3b. Iterates `ship+0x438`'s unit array, calls `FUN_004087b0` per slot. Ghidra has this one defined normally. |
| `FUN_004087b0` (`0x004087b0`) | Bank::ChargeCycle (per-unit) | §3.3b. The real weapon energy-draw function. No 4.0, no ratio. |
| `FUN_004035b0` (`0x004035b0`) | Ship-wide power-to-weight ratio + malfunction-event driver | §3.5. Separate per-frame system from `FUN_00404250`. Already flagged (but not analyzed) in `PATH-B-FINDINGS.md` as "Energy Processing." |
| `FUN_0040b510` (`0x0040b510`) | Subsystem malfunction/event phase-cycle | §3.5. Uses 4.0 and 0.5, but NOT energy-related — driven by `FUN_004035b0`'s power-to-weight ratio, not the reactor pool. Also confirmed (Path B6) as vtable slot 0 for Tube/Launcher/Battery/Scanner/LifeSupport/Transporter/Impulse — the shared `System` base class's default virtual, inherited unmodified by these 7 classes. |
| `FUN_004182e0` (`0x004182e0`) | Generic malfunction/event notifier | §3.5/§3.5b. `"%d %s%s %s!\n"`, gated on `this ship == player's own ship`. Noun comes from the per-slot string table in §3.5b; `FUN_00401560` picks the plural-vs-singular `"s"` suffix; `FUN_00401490` is a `rand()`-based call whose result feeds the verb selection (exact verb table not traced — Path B6 Priority 6, lowest priority, left open). |
| `FUN_004035b0` (`0x004035b0`) | Ship-wide power-to-weight ratio + malfunction-event driver | §3.5/§3.5b. Fully disassembled in Path B6 — confirmed to cover all 13 subsystem slots, not 5. |
| `FUN_004091e0` (`0x004091e0`) | Battery::SumArray (per-frame) | §3.5b. Ship `+0x2a0`. Sums a value across the Battery array; feeds the shared reactor pool as an extra source in `FUN_00404250` rather than drawing from it. |
| `FUN_0040caa0` (`0x0040caa0`) | Tube::UpdateArray (per-frame driver) | §3.5b. Ship `+0x454`. Iterates the Tube array, calls `FUN_0040c460` per slot. |
| `FUN_0040c460` (`0x0040c460`) | Tube::ChargeCycle (per-unit) | §3.5b. Structurally a near-exact twin of Bank's `FUN_004087b0` — same field offsets, same `0x00465440` epsilon constant. |
| `FUN_0040a560` (`0x0040a560`) | Launcher::UpdateArray+ChargeCycle | §3.5b. Ship `+0x470`. Ordinary per-unit reactor-pool draw. |
| `FUN_0040bcd0` (`0x0040bcd0`) | Transporter::UpdateArray+ChargeCycle | §3.5b. Ship `+0x9c0`. Draw gated on a per-unit `state==7` ("beaming active") flag. |
| `FUN_00409bd0` (`0x00409bd0`) | Impulse::GetOutput (per-frame) | §3.5b. Ship `+0xbf0`. Feeds the shared reactor pool as an extra source, like Battery, rather than drawing from it. |
| `FUN_0040aaf0` (`0x0040aaf0`) | Scanner::UpdateArray+ChargeCycle | §3.5b. Ship `+0xb50`. Draw with a "linked" bypass condition (skips the draw if linked to something at `+0x148`). |
| `FUN_004095b0` (`0x004095b0`) | Cloak::UpdatePower | §3.5b. Ship `+0xb88`. **Corrects Path B5**, which called this offset Tractor. Clears a boolean flag to 0 on shortfall; its failure is followed directly by `"We have uncloaked due to lack of power.\n"` in `FUN_00404250`'s raw disassembly. |
| `FUN_0040b990` (`0x0040b990`) | Tractor::UpdatePower | §3.5b. Ship `+0xbb8`. **Corrects Path B5's `"0xb88/~0xbb8"` hedge** — this is the real Tractor slot; its failure is followed by `"Our tractor beam has failed due to lack of power.\n"`. |
| `FUN_0040a690` (`0x0040a690`) | LifeSupport::UpdatePower | §3.3/§3.5b. Ship `+0xc20`. **Corrects Path B5**, which called this offset Cloak. Dead-weight-scaled cost formula (`crew/DWT-scaled rate + base`) plus an incrementing fail counter — matches Life Support's escalating failure-message chain, not Cloak's instant on/off. |
| `FUN_00418080` (`0x00418080`) | ship+0xec's inline-object constructor | §3.7/§3.9. Builds a self-contained ~0x24-byte record with a self-pointer to the ship, a crew-derived int (`ship+0xf0`, corrected from "DWT" in §3.9), and a legitimate shuffled-surname call into `FUN_004011b0` (§3.7/§3.9 — no bug, Path B7's "likely-buggy" claim was itself a mislabeling caused by the off-by-4 file-offset bug). Not part of the reactor-rate chase. |
| `FUN_004011b0` (`0x004011b0`) | Shuffled-record dispenser | §3.6/§3.9. Lazily shuffles (Fisher-Yates, via `FUN_00401030`) a table of NUL-terminated 17-byte-stride records, then hands out the next shuffled pointer each call, cursor wraps. Used twice, on two separate tables: `ship+0xe8` (ship names, `class_data+0x10`) via the ship ctor directly, and `ship+0xec+0x8` (commanding-officer surnames, `class_data+0x14`) inside `FUN_00418080` — both legitimate uses, no bug (§3.9 corrects Path B7's "likely genuine bug" claim about the second one). |
| `FUN_00401030` (`0x00401030`) | Record-pointer array builder + shuffle | §3.6. First pass fills an array with sequential record pointers (stride `0x11`); second pass runs a real Fisher-Yates shuffle using `FUN_00401490` (`rand()`-based) for swap indices. |
| `FUN_00409860` (`0x00409860`) | Drive::ConstructArray | §3.6. Builds 4 inline `0x38`-byte Drive unit slots at `ship+0x708`; sets each unit's `+0x30` to the array object's own `this` pointer, and the array's own `+0xe8` to `class_data+0x190` (fixed, no shuffling). |
| `FUN_0040af50` (`0x0040af50`) | Shield::ConstructArray | §3.6. Builds 5 inline `0x48`-byte Shield unit slots at `ship+0x7f8`; sets each unit's `+0x34` to the array object's own `this` pointer, and the array's own `+0x1bc` to `class_data+0x1d0` (fixed, no shuffling). |
| `FUN_00408e60` (`0x00408e60`) | Bank::ConstructArray | §3.6. The *actual* Bank array constructor called from the ship ctor — corrects `PATH-B-FINDINGS.md`'s stale reference to `FUN_00408920` (an address that isn't a defined function boundary at all; it falls inside `FUN_004088c0`). Sets each Bank unit's `+0x20` to the array object's own `this` pointer, and the array's own `+0x14` to `class_data+0xC8`. |
| `FUN_0040a9a0` (`0x0040a9a0`) | Reactor::SumOutput | §7 item 7. Fastcall, sums `(100 - damage%) / 100.0 * per-unit-rate` across the Reactor array (`ship+0x150`), returns a `float10` in the FPU register — does **not** write to memory. Neither of its two callers stores the result to `ship+0xf0`. |
| `FUN_00415ca0` (`0x00415ca0`) | Ship status-icon UI pass | §7 item 7. One of `FUN_0040a9a0`'s two callers; turned out to be a UI/status-icon-coloring function (the `FUN_004174a0(0xa8)`/`FUN_004174d0()`/`FUN_004174a0(0x22)` pattern wrapping every subsystem block looks like "select healthy/damaged icon color"), not an energy writer. |
| `FUN_00403460` (`0x00403460`) | `Ship::vftable+0x2c` | §7 item 7. The first per-ship virtual call in `FUN_0040d270`'s per-frame pass. Just a generic countdown timer on `ship+0x118`; unrelated to `+0xf0`. |
| `FUN_00402b60` (`0x00402b60`) | Per-ship state-transition handler | §7 item 7. Runs early in `FUN_0040d270`'s per-frame pass (destruction/state-change bookkeeping on offsets `+0x38`–`+0xc8`); does not touch `+0xf0`. |
| `FUN_00404910` (`0x00404910`) | Ship constructor | §3.8. Calls all 13 subsystem `ConstructArray` functions in order, plus `FUN_00418080` (§3.7) and the `FUN_004011b0` name-pool call (§3.6). Also the source of two new open leads: `ship+0x110 = *(class_data+0x380)` (a plain int copy, subsystem/purpose unknown) and a call to `FUN_00401de0(this, *(double*)(class_data+0x40), *(double*)(class_data+0x28), *(double*)(class_data+0x30))` — three doubles from class_data's header region, contradicting `ship-struct-analysis.md`'s guess of three 4-byte floats at `+0x1C/+0x20/+0x24`. See §7 item 10. |
| `FUN_0040a830` (`0x0040a830`) | Reactor::ConstructArray | §3.8. `ship+0x150`; TypeRecord at `class_data+0x58`. |
| `FUN_00409270` (`0x00409270`) | Battery::ConstructArray | §3.8. `ship+0x2a0`; TypeRecord at `class_data+0x90`. Per-unit **value snapshot** of a double at TypeRecord`+0x30`, not a live pointer. |
| `FUN_0040cae0` (`0x0040cae0`) | Tube::ConstructArray | §3.8. `ship+0x454`; TypeRecord at `class_data+0x110`. Array's own field `+0x14` holds the pointer — same array-offset as Bank's, consistent with Tube's code being a near-twin of Bank's (§5 note on `FUN_0040c460`). |
| `FUN_00409e40` (`0x00409e40`) | Launcher::ConstructArray | §3.8. `ship+0x470`; TypeRecord at `class_data+0x158`. Array's own field `+0x28c` holds the pointer. |
| `FUN_0040bac0` (`0x0040bac0`) | Transporter::ConstructArray | §3.8. `ship+0x9c0`; TypeRecord at `class_data+0x220`. Array's own field `+0x188` holds the pointer. |
| `FUN_0040aaa0` (`0x0040aaa0`) | Scanner::ConstructArray | §3.8. `ship+0xb50`; TypeRecord at `class_data+0x260`. Single-instance object, not a multi-unit array; stores the pointer at its own `+0xc`/`+0x30`, plus a one-time **value snapshot** of a double from TypeRecord`+0x30` into its own `+0x28`. |
| `FUN_004094f0` (`0x004094f0`) | Cloak::ConstructArray | §3.8. `ship+0xb88`; TypeRecord at `class_data+0x298`. Single-instance; pointer at its own `+0xc`/`+0x24`. |
| `FUN_00409b90` (`0x00409b90`) | Impulse::ConstructArray | §3.8. `ship+0xbf0`; TypeRecord at `class_data+0x2d0`. Single-instance; pointer at its own `+0xc`/`+0x24`. |
| `FUN_0040b6f0` (`0x0040b6f0`) | Tractor::ConstructArray | §3.8. `ship+0xbb8`; TypeRecord at `class_data+0x308`. Single-instance; pointer at its own `+0xc`/`+0x30`. |
| `FUN_0040a5e0` (`0x0040a5e0`) | LifeSupport::ConstructArray | §3.8. `ship+0xc20`; TypeRecord at `class_data+0x348`. Single-instance; pointer at its own `+0xc`/`+0x2c`. |

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

**Closed in Path B6:**

3. ~~Resolve the second `4.0` at `0x00478798`.~~ **Done — §4.** It's row 128 of a 257-row
   `atan()` lookup table, addressed by computed index. Nothing to do with energy.
9. ~~Name the remaining unlabeled subsystem slots.~~ **Done — §2.1/§3.5b.** All 13 runtime
   subsystem slots now have confirmed names, including two corrections to Path B5
   (`0xb88`=Cloak not Tractor, `0xc20`=Life Support not Cloak, `0xbb8`=Tractor). Only `0xc00`
   remains an unexplained leftover offset (see §2.1).
8. **Mostly closed — what event does `FUN_0040b510`'s cycle represent?** The noun half is fully
   resolved (§3.5b's string table — every one of the 13 slots gets its own noun, not just 5).
   The verb half is still open: `FUN_004182e0` calls `FUN_00401560` (confirmed: picks a
   singular/plural `"s"` suffix) and `FUN_00401490` (a `rand()`-based call whose return value is
   used somewhere for verb variety, but the actual verb string table wasn't located). Low
   priority — cosmetic flavor text, not game logic.

**Closed in Path B7:**

4. ~~Confirm `ship+0xec`'s identity, and reconcile the reactor-rate chases.~~ **Done — §3.6/§3.7.**
   Resolved in the opposite direction from how it was framed: `ship+0xec` and `ship+0xe8` are
   *both* unrelated to the reactor-rate chase. `ship+0xe8` is a shuffled commanding-officer name
   pointer; `ship+0xec` is a mostly-inert inline record with a likely genuine construction-time bug
   (§3.7). The real chase for Drive/Shield never went through either — it's `unit → own array
   container → array's fixed class-data pointer → final double`, the exact same shape Bank/Tube
   already used. All three subsystem categories (Bank/Tube, Drive, Shield) now confirmed to share
   one mechanism (§3.6) — closing the "same object or different?" question definitively: **all
   three read static, per-class constants through their own array container; none reach the live
   Reactor object, and none share a single common pointer.**
7. **CLOSED — `COMBAT_DAMAGE` session.** Confirmed via disassembly: it's a plain **integer**
   (`FILD`, not `FLD`), set at construction to a raw copy of `class_data+0x18`, which the class-data
   mapping session (§3.9) corrected from "DWT" to **crew** — so a fresh ship starts with
   `ship+0xf0 == crew`, giving `FUN_004035b0`'s ratio an initial value of exactly `1.0` (this part
   of the original claim survives; the "power-to-weight" label doesn't — it's crew-based). Confirmed
   zeroed under `ship+0xc48 == 10` ("reactor destroyed"). **There is no per-frame writer, and there
   never was one to find**: `COMBAT_DAMAGE_MAP.md` §4 traced the real writer to
   `FUN_00404d90` (`Ship::vftable+0x34`, the damage-application function) — `ship+0xf0` (crew) only
   decreases on a hull-penetrating combat hit, via a random casualty roll proportional to that hit's
   damage. This was exactly the "working theory" below, now confirmed with the actual formula shape,
   plus the added detail that it runs on *every* hull-penetrating hit (Begin 3 has no accumulating
   hull-HP pool — see `COMBAT_DAMAGE_MAP.md` §0/§4.1, a correction to what a much older, since-fixed
   assumption about `ship+0x110` would have implied).

**Still open, low priority:**

5. **Explain how the Display/Summary struct (§2.2) gets built.** It is clearly assembled fresh
   for `FUN_0040f4b0` and does not share the Runtime Object's field layout. Finding its
   construction site would let us map it back to Runtime Object offsets directly, rather than
   via string-format inference.
6. **Decode the two still-open adjacent constants** (`0x464ad0`, `0x464ac8`) — values are known
   (`1e-08`, `1.0`) but their functional role within `FUN_004018b0`/`FUN_00407220` isn't confirmed.
8b. **Find `FUN_0040b510`'s verb text** (§7 item 8 in earlier sessions) — cosmetic flavor text
   only, not game logic. See `NEXT_SESSION_PROMPT.txt` history if picked back up.
9b. **Decode the 13 TypeRecords' internal fields** (§3.8) — offsets are now known, contents mostly
   aren't (only Bank's `+0x38`=`maxCharge` is pinned down, §3.3b). This is step 2 of the class-data
   mapping session, in progress.
10. **CLOSED (`class_data+0x380`/`+0x390`) — `COMBAT_DAMAGE` session, live-verified.**
    `class_data+0x380` is confirmed `0` for every ship class tested (Heavy Cruiser/Destroyer/
    Frigate), both statically and via a live `/proc/<pid>/mem` read — it's copied into `ship+0x110`,
    which turns out to be scratch space inside the damage-application function, not a meaningful
    stat; see `COMBAT_DAMAGE_MAP.md` §0/§4.1 for the full story (this reverses a "max hull" guess
    that `COMBAT_DAMAGE`'s own working notes briefly held mid-session, before the live read).
    `class_data+0x390` is confirmed `1.0` live for Heavy Cruiser, matching the already-suspected
    "linked ship malfunction-risk scaling factor, default/identity value" role this item originally
    proposed. A related field, `class_data+0x3a0`, turned out to be the actually-important one
    nearby: a per-class instant-destruction damage threshold (`75.0`/`60.0`/`50.0` EU for HC/
    Destroyer/Frigate, live-verified for HC) — see `COMBAT_DAMAGE_MAP.md` §4.1/§7.
    Separately, still open: `FUN_00401de0(this, *(double*)(class_data+0x40),
   *(double*)(class_data+0x28), *(double*)(class_data+0x30))` — three doubles read from
   class_data's header region and passed to an uninspected function — remains open; note the
   corrected offsets (§3.9) put crew at `+0x18` and DWT at `+0x1C`, so these three doubles
   (`+0x28/+0x30/+0x40`) sit just past DWT, not overlapping it. `ship-struct-analysis.md`'s old
   guess of three 4-byte floats at (uncorrected) `+0x1C/+0x20/+0x24` is superseded both by this
   double-vs-float mismatch and by the general offset correction in §3.9.

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
- **A decompiled `if (cond == 0) { ...message... }` block can attach a message to the wrong call.**
  (Path B6, §3.5b.) Ghidra reused the variable name `iVar3` across several unrelated
  success/failure checks in `FUN_00404250`. Reading the pseudocode top-to-bottom, it looked like
  `"We have uncloaked due to lack of power.\n"` belonged to the call on `ship+0xc20` — it actually
  belongs to the *next* call down, on `ship+0xb88`. This flipped two subsystem identities that
  Path B5 had marked "confirmed." When a string literal is the thing doing the identifying work,
  check its exact call site against raw disassembly (`disassemble_function`), not decompiled C —
  the same discipline as the `p += 0x1c` pointer-scaling lesson above, applied to control flow
  instead of pointer arithmetic.
- **RTTI vtables are a good lead for finding class names, a bad one for finding per-class logic.**
  (Path B6.) Chasing each unnamed class's RTTI Complete Object Locator to its vtable correctly
  confirmed the classes' identities exist and share a base class, but the vtable slots themselves
  were all either the shared base's default implementation or a trivial per-unit reset stub — not
  the real per-frame energy function. The real names came from a completely different angle:
  disassembling the one function that already iterates every subsystem by ship offset
  (`FUN_004035b0`) and reading off the noun string pushed before each call. When a structural
  approach (vtables) stalls, look for a driver function that already enumerates everything you're
  trying to name.
- **The "matching offsets across different structs" trap struck a second time, at the field level
  this time.** (Path B7, §3.6.) Path B5/B6 assumed Drive's `unit+0x30` was a back-pointer to the
  ship, because chasing `[unit+0x30]+0xe8` happened to land on `ship+0xe8` — a field that already
  had a plausible-enough label ("crew count") sitting right there. It never was: `unit+0x30` is a
  back-pointer to Drive's own array container, which *coincidentally* also has a meaningful field
  at `+0xe8` (a completely different value, set by a completely different constructor). Two
  unrelated objects sharing a "used" offset is exactly the same trap as §8's three differently-shaped
  "ship" structs, just one level of indirection deeper — the fix was the same both times: find the
  actual constructor write for the field in question, and confirm it against raw disassembly,
  rather than trusting that a plausible-sounding label at the target offset is the right object.
- **A field's initial value can look exactly like a different, better-established field — verify by
  units, not just by value.** (Path B7, §3.7; the specific field `class_data+0x18` was later
  corrected from "DWT" to **crew** in §3.9, but the methodology point stands.) `ship+0xf0` and
  `class_data+0x18` start out numerically identical for a fresh ship, which could easily be
  mistaken for "these are the same field" or "this is a copy-paste artifact." Checking the *load
  instruction* (`FILD`, integer, in both places) rather than just the value confirmed they're
  genuinely the same kind of quantity used the same way (a ratio numerator/denominator pair), not a
  coincidence or a decompiler misread — the opposite failure mode from the `unit+0x30` trap above,
  where a coincidental offset match was wrongly trusted. Both cases needed the same discipline:
  check the actual bytes/type, don't reason from a plausible-looking coincidence either direction.
- **A heuristic file-offset table (built by searching for known numbers) can be systematically
  wrong by a constant amount and still "confirm" several fields.** (Class-data mapping session,
  §3.9.) `ship-struct-analysis.md`'s ship-class file offsets were all 4 bytes too high, yet crew and
  DWT both still matched their manual values — because both are 4-byte ints sitting in a run of
  similar-sized fields, so reading 4 bytes early just grabbed a different, coincidentally
  plausible-looking field. The bug only became visible when a *disassembly-confirmed* offset
  (Reactor's unit count, `class_data+0x58`) was checked against that same table and came back
  impossible (`0`, for a ship that must have reactors) — a value with no plausible reading at all,
  unlike crew/DWT's silent coincidence. **When a code-derived offset and a heuristic-derived offset
  disagree, trust the code-derived one and go find out why the heuristic failed** — and prefer a
  live/dynamic check (here, `/proc/<pid>/mem` on the running game) over more static guessing when
  two independently-plausible static readings contradict each other, since static analysis alone
  can't tell you *which* plausible reading is real.
- **A decompiled call with suspiciously few or opaque arguments (`extraout_*` registers, a function
  seemingly "called with nothing") is a sign the real argument arrives on the x87 FPU stack, not as
  a normal parameter — and Ghidra's pseudocode can badly misattribute it.** (`COMBAT_DAMAGE` session,
  see `COMBAT_DAMAGE_MAP.md` §5 for the full writeup.) This happened three times in one session, all
  around small CRT/math-internal helpers (`FUN_0044c1c0`'s round-to-int64, `FUN_0044c380`'s NaN/Inf
  domain guard). The most costly instance: Ghidra's decompiled pseudocode for the phaser damage
  formula confidently attributed its final multiplier to `_DAT_00464ad8` (**4.0**, reused from
  Drive/Shield) — the raw disassembly showed the actual instruction was `FMUL [0x00464bd0]`
  (**0.5**); `4.0` doesn't appear anywhere in that function's real instructions. **When a call looks
  like this, disassemble the function and read the `FLD`/`FST`/`FSTP` sequence directly — don't
  trust the pseudocode's variable names or constant references.** Same underlying discipline as the
  off-by-4 lesson above (trust code over a derived label), just applied to decompiler output instead
  of a heuristic file-offset table.
- **A field's value being flatly `0` isn't automatically a bug — it can also overturn a hypothesis
  you already halfway believed.** (`COMBAT_DAMAGE` session, see `COMBAT_DAMAGE_MAP.md` §0/§4.1.)
  `class_data+0x380` reading `0` for every ship class looked exactly like last session's off-by-4
  symptom (a code-confirmed offset giving an "impossible" value) and briefly got framed as "probably
  a stale template value, needs a live check to find the real number." The live check confirmed the
  *file* was right all along — `0` is the real, permanent value, and the mid-session "max hull"
  hypothesis for that field was simply wrong. A live read settles *whether* a surprising value is
  real; it doesn't presuppose the surprising value must be a bug.

---

## 9. Status and what's next

The energy system investigation is now essentially complete. Every subsystem's power-draw
mechanism is traced to real code (§3.1–§3.6), every runtime offset is named (§2.1), and the one
remaining loose end (`ship+0xf0`'s hypothetical per-frame writer, §7 item 7) turned out to most
likely not exist as a per-frame thing at all — it's a combat-damage question, not an energy-system
one. Two small, genuinely low-priority items are left if anyone wants to close them out later:
the Display/Summary struct's construction site (§7 item 5) and `FUN_0040b510`'s verb-text table
(§7 item 8b) — both cosmetic/display, not game logic.

**A concrete lead for a future session, from the developer's own memory of playing the original
game:** transporting crew back to their original ship reportedly scrambled the *ship names* shown
somewhere in the UI. This session confirmed (§3.9, correcting §3.6) that `ship+0xe8` is a per-ship
pointer into a **shuffled pool of ship names** (not commanding-officer surnames as first thought —
that pool is a separate one, at `ship+0xec+0x8`), assigned **once, at construction**, which lines
up with the remembered bug even better than before: it's the *ship-name* pointer specifically that
would need to be involved for the bug to show scrambled ship names. Nothing downstream was checked
for whether transporter code (`FUN_0040bcd0`, ship `+0x9c0`) — or anything that moves crew/state
between two ship objects — ever swaps or re-derives that pointer incorrectly. This is a plausible,
checkable lead for whichever path picks up ship naming or the transporter subsystem, and it's the
kind of bug a live-game repro (the developer can run the actual game and describe exactly what
breaks) would make much faster to pin down than static analysis alone.

**Update (class-data mapping session, chosen as a prerequisite to combat-damage work):** step 1
(§3.8) found the complete 13-subsystem TypeRecord table in `class_data`. Step 2 (decoding TypeRecord
contents) confirmed Bank's fields fully and Drive's/Shield's `+0x30`/`+0x38` fields against manual
data, and — along the way — found and fixed a session-crossing off-by-4 file-offset bug that had
mislabeled several fields since Path B4/B7 (§3.9, with corrections to §3.6/§3.7/§7 item 7 above).
Step 3 (the remaining class-data header fields — the three-doubles call, `class_data+0x00`'s
unidentified field, `class_data+0xC`'s non-name-pool table) is still open, lower priority than
combat-damage work now that crew/DWT/the 13 TypeRecords are solid.

**Update (`COMBAT_DAMAGE` session):** the phaser/Bank weapon-fire → hit → shield-absorption →
hull/destruction chain is now fully traced and code-confirmed — see the new `COMBAT_DAMAGE_MAP.md`
for the complete writeup. This closed out §7 items 7 and 10 above for good (both cross-referenced
into that doc), found that Begin 3 has no accumulating hull-HP pool (a genuine surprise, corrected
mid-session via a live memory read — see `COMBAT_DAMAGE_MAP.md` §0), and left a full open-questions
list of its own (`COMBAT_DAMAGE_MAP.md` §6), headlined by the Tube/torpedo equivalent of this whole
chain being completely untraced.

**Update (`TORPEDO_DAMAGE` session):** that Tube/torpedo equivalent is now traced through the launch
moment — see the new `TORPEDO_DAMAGE_MAP.md`. Confirmed torpedoes really are separate projectile
objects (not a Bank near-twin), and extensively live-tested the tube lock/reload/fire cycle across
two real play sessions (one ending in the player's own ship being destroyed mid-test, which usefully
crashed an early version of the watch script and got fixed). The projectile's own flight/collision/
impact code — where torpedo damage actually gets applied — is still completely untraced
(`TORPEDO_DAMAGE_MAP.md` §5 item 5), the natural next session's target.
