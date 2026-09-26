# Begin 3 Combat Damage Map

**Date:** 2026-09-26, `COMBAT_DAMAGE` session
**Status:** Phaser (Bank) fire → hit → shield-absorb → hull/destruction chain fully traced and
code-confirmed. Torpedo (Tube) equivalent **not yet traced** — everything below comes from the
phaser/Bank path specifically; see §6 item 10.

**Prerequisite:** the `class_data` TypeRecord table (`ENERGY_SYSTEM_MAP.md` §3.8) and the corrected
ship-class file offsets (§3.9) — this session reads and depends on both.

---

## 0. Headline correction (read this before trusting anything about `ship+0x110`)

Mid-session, this doc's own working draft claimed `ship+0x110` was "current hull HP, starts at max,
decreases toward zero." **That's wrong**, caught by a live `/proc/<pid>/mem` read of the developer's
own running game (same technique as last session's off-by-4 fix): `class_data+0x380` — the value
`ship+0x110` is copied from at construction — is **`0` for every ship class**, confirmed both
statically and live. Begin 3 does not appear to have a traditional accumulating hull-HP pool at all.
See §4 for what `ship+0x110` actually does (it's scratch space inside a single function call, always
reset to `0`).

---

## 1. Weapon fire chain (Bank / Phaser)

```
ship+0x438 (Bank array, §3.8)
  → FUN_00403330            per-frame "should we fire?" check for this ship
      → FUN_004086a0          selects which banks are ready to fire (NOT decoded — §6 item 1)
      → FUN_004183e0          announces "%s firing %d phaser%s.\n" (3rd person; ship+0xec is the
                               commanding-officer/name sub-object, §3.7)
      → FUN_00408fa0          loops the selected bank indices
          → FUN_00408cf0        the REAL per-bank fire function — hit resolution lives here
```

`FUN_00408cf0(bank_unit)` — traced from **raw disassembly**, not the decompiler's pseudocode (see
§5 for why that mattered here):

```c
// one-time-ish setup per call:
maxRange      = *(double*)(*(int*)(bank_unit+0x24) + 0x40);   // class_data-chain: engagement range cap
halfRange     = *(double*)(bank_unit+0x48) * 0.5;              // "close enough to hit" gate
falloffTerm   = 45.0 / *(double*)(bank_unit+0x48);             // 0x00465060 = 45.0

for each ship in the global ship list (skip self):
    if (target.vtable[8]() == 1 && target+0x148 != 0) continue;   // skip condition, enum unclear (§6.3)

    distance = FUN_00401800(ownerShip, targetShip);                // confirmed: ship-to-ship distance
    if (distance >= maxRange) continue;

    // angle of the incoming shot relative to the TARGET's own heading (§3):
    bearingAtTarget = FUN_00402140(ownerShip, targetShip);
    targetHeading   = FUN_00401fe0(ownerShip, targetShip);
    relativeAngle   = FUN_00401430(bearingAtTarget - targetHeading);

    if (distance >= halfRange) continue;                            // hard inner-range cutoff

    rangeFraction = 1.0 - (distance / maxRange);                    // LINEAR falloff, not squared
    rangeFraction = validate_not_nan_or_inf(rangeFraction);         // FUN_0044c380 — guard only, §5
    damage = rangeFraction * bank_unit+0x40 * falloffTerm * 0.5;    // bank_unit+0x40 = charge being fired

    target.vtable[0x34](relativeAngle, damage, /*weaponType=*/3);   // FUN_00404d90, §4
```

**Confirmed, ground-truth formula** (no RNG term, no `4.0` anywhere in this function — see §5's
correction):

```
damage = (1 − distance/maxEngagementRange) × chargeBeingFired × (45.0 / weaponRangeStat) × 0.5
```

Two distinct "range" quantities feed this, easy to conflate:
- `class_data+0x40` (via `bank_unit+0x24`'s chain) = **max engagement range** — a hard cutoff, used
  for the smooth linear falloff's denominator.
- `bank_unit+0x48` = a **static per-weapon range stat** — used for the tighter "half of this" inner
  cutoff *and* the `45.0/range` term. Never independently confirmed as a class_data snapshot (like
  Battery/Scanner's one-time-copy pattern, §3.8) vs. something computed per-frame — see §6 item 11.

---

## 2. Shield absorption

`FUN_00404d90` (damage application, §4) calls into the Shield array (`ship+0x7f8`) **before**
touching hull at all:

```
FUN_0040b230(shieldArray, relativeAngle, damage, weaponType)
  → FUN_0040b180(shieldArray, relativeAngle)      picks WHICH shield unit takes the hit
  → FUN_0040ae00(shieldUnit, weaponType, &damage)  mutates damage in place → leftover
```

### 2.1 Facing selection (`FUN_0040b180`) — directional shields

The relative angle gets bucketed into one of **6 facings**, each a distinct bitmask:

| Angle range (degrees) | Bitmask |
|---|---|
| `[330, 360) ∪ [0, 30)` (wrap) | `0x01` |
| `[30, 90)` | `0x02` |
| `[90, 150)` | `0x08` |
| `[150, 210)` | `0x20` |
| `[210, 270)` | `0x04` |
| `[270, 330)` | `0x10` |

Each shield unit has its own facing-coverage bitmask (word field at `unit+0xb`... within the array's
per-unit stride — see §7 struct table). The first live unit (`hitCounter < 100` and `state != 8`)
whose coverage overlaps the hit's bucket absorbs it; if none match, the full, un-reduced damage
returns (no shield available at that facing).

### 2.2 Absorption math (`FUN_0040ae00`)

```c
shieldUnit+0x28 += 1;                                        // hits-this-frame counter (§7)
capacityEU   = classData[Shield].TypeRecord + 0x30;          // confirmed per-class EU, §3.9
availableEU  = round((shieldUnit+0x30 / 100.0) * capacityEU); // +0x30 = live charge %
absorbed     = min(availableEU, damage);

rateFraction = classData[Shield].TypeRecord + 0x38;           // confirmed per-class efficiency, §3.9
cost = (1 - rateFraction) * absorbed + 1;
if (shieldUnit+0x20 == 10) cost *= 0.5;   // state 10 = REINFORCED (confirmed, §3.2 — same 10 also
                                          // gates the "4x power cost" reinforcement mechanic)

shieldUnit+0x38 -= cost;                  // shield "integrity" — separate from charge %
shieldUnit+0x38 = max(shieldUnit+0x38, 0);
if (shieldUnit+0x38 < shieldUnit+0x30) shieldUnit+0x30 = shieldUnit+0x38;  // charge% syncs down

if (weaponType != 1) damage -= absorbed;  // <-- weapon type 1 still drains the shield, but the
                                          //     leftover damage is NOT reduced — bypasses shields
```

**Weapon-type 1 is a real, distinct mechanic**: whatever fires with type 1 (not phasers — those use
type 3) punches through shields for full damage while still draining them. Candidate: torpedoes,
unconfirmed (§6 item 10).

---

## 3. The angle-of-attack / position-fidelity mechanic

The `relativeAngle` argument threading through all of the above comes from a small cluster of
mirrored geometry helpers, all taking `(shipA, shipB)`:

| Function | Role |
|---|---|
| `FUN_00401800` | Distance between two ships (confirmed) |
| `FUN_00402090` | Bearing **from** A **to** B |
| `FUN_00402140` | Mirrored/reciprocal bearing (used for "angle of impact at the target") |
| `FUN_00401fe0` | B's heading (true or estimated, same fidelity rule as below) |
| `FUN_0044c27a` / `FUN_0044c480` | Generic `atan`-family core (plausibly the 257-row lookup table from Path B6, `ENERGY_SYSTEM_MAP.md` §4) |

**Position fidelity is gated by team + detection, not always the true position:**

```c
if (shipA.team == shipB.team || shipB+0xa8 != 0)   // same side, OR "detected" flag set
    use shipB's TRUE position (+0x38/+0x40) / heading (+0x88);
else
    use shipB's ESTIMATED position (+0xb0/+0xb8) / heading (+0xC8, =200 decimal);
```

This is a real, nameable feature: **an undetected enemy ship's apparent position can be stale or
wrong**, and combat geometry (bearing, and therefore which shield facing takes a hit) is computed
against whatever the firing ship *believes* is true, not necessarily reality. Ties naturally to the
Scanner subsystem. Not fully explored this session (§6 item 8).

---

## 4. Damage application / destruction (`FUN_00404d90`, `Ship::vftable+0x34`)

Confirmed as the vtable target by reading the ship vtable directly: base `0x00464f04` (cross-checked
— its `+0x2c` entry is `0x00403460`, the already-known energy-system vtable function), `+0x34` entry
is `0x00404d90`.

```c
void ApplyDamage(Ship *this, double angleOfAttack, double damage, int weaponType) {
    this->officerObj(+0xe0)+0xa8 -= 5;  clamp >= 0;      // some alert/readiness stat, not pinned down

    leftover = ApplyShieldAbsorption(this+0x7f8, angleOfAttack, damage, weaponType);  // §2

    this+0x134 += 1;      // total-hits-taken counter (every call, shielded or not)
    this+0x12C  = 1;      // "took damage this frame" flag

    if (leftover != 0) {
        this+0x128 += 1;                 // hull-hits-this-frame counter (reporting, already known)
        this+0x110 -= leftover;          // ALWAYS goes to <1 — see §0's correction
        if (this+0x110 < 1) {
            this+0x110 = 0;
            if (classData+0x3a0 <= leftover) {     // per-class destruction threshold (§3.9, confirmed)
                this+0x1c = 3;            // destroyed state
                return;
            }
            // --- everything below runs on EVERY hull-penetrating hit, not just "critical" ones ---
            crewCasualties = randomRoll(crew=this+0xf0);   // resolves the §7 item 7 mystery (below)
            this+0xf0 -= crewCasualties;
            if (this+0xf0 < 6) FUN_00403210(this);          // presumed derelict/abandon-ship (§6.9)

            if (this+0x138 != 0) {
                this+0x138 -= randomRoll();
                if (this+0x138 < 6) this+0x138 = 0;          // unidentified 2nd pool (§6.4)
            }

            if (leftover > 9) {
                for each entry in linked list at this+0xc70:  // NOT the same as +0x148 (§6.5)
                    entry.vtable[0x34](angleOfAttack, leftover, /*weaponType=*/1);  // recursive!
            }

            rolls = leftover / 10;
            repeat rolls times:
                malfunction-roll against ALL 13 subsystems, in class_data TypeRecord order (§3.8)
            // + two conditional event-queue pushes near Scanner/Cloak fields (§6.6)
        }
    }
}
```

### 4.1 The hull-HP correction, explained

`ship+0x110` starts at `0` (copied from `class_data+0x380`, confirmed `0` for Heavy
Cruiser/Destroyer/Frigate, both statically **and live** via `/proc/<pid>/mem` on the developer's
running game — see `read_live_classdata.py`). Since `leftover` is always positive when this branch
runs, `this+0x110 -= leftover` is always negative, so `if (this+0x110 < 1)` **always fires** — it's
not a rare "critical" case, it's unconditional. `ship+0x110` itself is reset to exactly `0`
immediately after, every time, so it never persists anything across hits.

**Conclusion: Begin 3 has no accumulating hull-HP pool.** Instead, *every single hit that gets past
shields* is independently checked against a flat per-class **destruction threshold**
(`class_data+0x3a0`, confirmed `75.0`/`60.0`/`50.0` EU for Heavy Cruiser/Destroyer/Frigate, live-
verified for Heavy Cruiser) — big enough in *one hit*, instant destruction; otherwise, that hit's
damage proportionally rolls for crew casualties and a subsystem-malfunction chance. There is no
"ship health bar" being tracked between hits, as far as this function shows.

This also **fully resolves `ENERGY_SYSTEM_MAP.md` §7 item 7** (the long-open "no per-frame writer
found for `ship+0xf0`" question): there isn't one, because it was never a per-frame field. Crew
(`ship+0xf0`) only decreases here, on a hull-penetrating hit, proportional to that hit's damage —
exactly the "working theory" §7 item 7 already guessed, now confirmed with the actual formula shape
(and the added detail that this runs on *every* penetrating hit, not a rare critical one).

---

## 5. Methodology note: the FPU-hidden-argument decompiler trap

This session hit the **same decompiler failure mode three separate times**, always around calls to
small CRT/math-internal helper functions that take their real argument on the x87 FPU stack rather
than as a normal register/stack argument Ghidra can track:

- `FUN_0044c1c0` — a double→int64 round helper (MSVC `_ftol`-style). Ghidra's decompiled pseudocode
  showed it being called with two unrelated integer-looking parameters; the *actual* input was
  whatever double the caller had just `FLD`'d, one instruction earlier, invisible in the pseudocode.
- `FUN_0044c380` — a NaN/Infinity domain-check guard (`_matherr`-style, error code `5`). Ghidra's
  pseudocode implied it returned a *new*, transformed value multiplied into the phaser damage
  formula; reading the raw disassembly showed it just validates and returns its input unchanged.
- **The phaser damage formula's final multiplier**: Ghidra's decompiled pseudocode confidently
  labeled it `_DAT_00464ad8` (**4.0**, the same constant from Drive/Shield's energy mechanics) — this
  was **wrong**. The actual instruction is `FMUL double ptr [0x00464bd0]` (**0.5**). The `4.0`
  literal does not appear anywhere in this function's real instructions.

**The pattern to watch for:** a decompiled call with suspiciously few/opaque arguments (`extraout_*`
registers, a function seemingly "called with nothing"), especially right after floating-point
comparisons or divisions. When you see it, disassemble the actual function (`disassemble_function`,
not `decompile_function`) and read the `FLD`/`FST`/`FSTP` sequence directly — don't trust the
high-level pseudocode's variable names or constant references in this specific situation. This is
the same "trust code over derived labels" discipline as last session's off-by-4 bug, just applied to
decompiler output instead of a heuristic file-offset table. (Cross-referenced into
`ENERGY_SYSTEM_MAP.md` §8's methodology list too.)

---

## 6. Open questions / TODOs

**Weapon firing:**
1. `FUN_004086a0` (which banks are selected to fire each frame) — not decoded.
2. `bank_unit+0x34`/`+0x38`'s "locked target" lookup (`FUN_004021f0`) — what it caches, and where
   `+0x34` itself gets set (never saw the write site this session).
3. The vtable`+8` status-query enum used in the target-skip condition (`result==1 && ship+0x148!=0`
   → can't be targeted). `ship+0x148` itself is already known (tractor/linked-ship pointer).
11. Confirm `bank_unit+0x48` is really a static per-class weapon-range snapshot (like Battery/
    Scanner's one-time TypeRecord copy, §3.8) rather than something recomputed per-frame — assumed
    by pattern, not independently re-verified the way Shield's chain was.

**Damage application / hull:**
4. `ship+0x138` — second pool that loses a random amount on critical hits, clamped to 0 below 6.
   Marines/boarding party? Unconfirmed.
5. `ship+0xc70`'s linked list — damage propagates here on big hits (`leftover > 9`), with
   `weaponType` forced to `1`. Distinct from the already-known `ship+0x148` single tractor-link
   pointer. Escort/fleet/docked-ship list? Unconfirmed.
6. The two conditional event-queue pushes near Scanner (`+0xb94/+0xb9c`) and Cloak (`+0xbc4/+0xbcc`)
   fields inside the critical-hit branch — plausibly "enemy detected you" / "cloak blown" as a side
   effect of taking damage. Unconfirmed.
7. Cross-reference the 13-subsystem malfunction roll here against `FUN_0040b510`'s existing
   malfunction/event system (`ENERGY_SYSTEM_MAP.md` §3.5/§7 item 8) — same event queue feeding the
   same flavor text, or two independent systems that happen to both roll against all 13 subsystems?
9. **CONFIRMED (`TORPEDO_IMPACT` session)** — `FUN_00403210` (called when crew drops under 6) zeroes
   `ship+0xf0` (crew count) plus seven adjacent fields (`+0xf4` through `+0x10c`), a full crew-wipe.
   Matches the developer's own live account of a "blue," hull-intact, crewless ship encountered in
   play, boardable and reactivatable — real derelict/capture mechanic, not just a code-shape guess
   anymore. See `TORPEDO_IMPACT_MAP.md` §5. What actually triggers/handles a successful boarding is
   still unknown — good next-session candidate.

**Position/geometry:**
8. Pin down exact roles of `ship+0x20/+0x28/+0x58/+0x60/+0x80/+0x88/+0xa8/+0xb0/+0xb8/+0xC8` —
   current read is a well-supported *hypothesis* (position/heading/velocity model, gated by a
   detection-fidelity flag at `+0xa8`), built from `FUN_00402390`'s construction-time writes and the
   bearing helpers' reads, but not independently confirmed field-by-field the way the combat
   formulas above were.

**Next session, structurally different path:**
10. **Substantially traced (`TORPEDO_DAMAGE` + `TORPEDO_IMPACT` sessions)** — see
    `TORPEDO_DAMAGE_MAP.md` (fire chain through launch) and `TORPEDO_IMPACT_MAP.md` (post-launch:
    global in-flight list, per-ship-per-turn hit resolution, live-confirmed immediate damage
    application). Confirmed genuinely different from Bank's instant hit-scan, as this item
    predicted. Still open: the exact array `FUN_004089b0` writes damage into isn't confirmed to be
    this document's Shield array (`TORPEDO_IMPACT_MAP.md` §2.4/§6 item 3), so weapon-type `1`
    (shield-bypass) still hasn't been confirmed as what torpedoes pass.

---

## 7. New struct fields confirmed this session

**Ship runtime object** (extends `ENERGY_SYSTEM_MAP.md` §2.1 — full table stays there; this is the
combat-specific delta):

| Offset | Field | Confirmed by |
|---|---|---|
| `+0x110` | Scratch value inside `ApplyDamage`, always reset to `0`; **not** a persistent hull-HP pool (§0, §4.1) | `FUN_00404910` (ctor) + `FUN_00404d90`, live memory read |
| `+0x128` | Hull-hits-this-frame counter (already known from reporting code; now confirmed it only increments on shield-penetrating hits) | `FUN_00404d90` |
| `+0x12C` (300) | "Took damage this frame" flag | `FUN_00404d90` |
| `+0x130` | "Fired weapons this frame" flag | `FUN_00403330` |
| `+0x134` | Total-hits-taken counter (every `ApplyDamage` call) | `FUN_00404d90` |
| `+0x138` | Second casualty-style pool, unidentified (§6 item 4) | `FUN_00404d90` |
| `+0x1c` | Ship status byte; `3` = destroyed | `FUN_00404d90` |
| `+0xc70`/`+0xc74`/`+0xc78` | Head of a third embedded circular linked list (distinct from the ship-list node at `+0xc58`/`+0xc5c`); damage-propagation target (§6 item 5) | `FUN_00404910` (ctor init), `FUN_00404d90` |
| `+0x38`/`+0x40` | True position (x, y doubles) | `FUN_00402090` et al. |
| `+0xb0`/`+0xb8` | Estimated/apparent position (x, y doubles), used when undetected by an enemy observer | `FUN_00402090` et al. |
| `+0x88` | True heading (double) | `FUN_00401fe0` |
| `+0xC8` (200) | Estimated/apparent heading (double) | `FUN_00401fe0` |
| `+0xa8` | Detection/visibility flag (exact semantics unconfirmed, §6 item 8) | `FUN_00402090`/`FUN_00401fe0` |
| `+0xc` | Team/faction id | `FUN_00402090` et al. |

**Bank (Phaser) unit** (per-unit fields, array at `ship+0x438`):

| Offset | Field |
|---|---|
| `+0x20` | Back-pointer to array container (established pattern, §3.6) |
| `+0x24` | Back-pointer feeding a class-data chain (`+0x40` off the dereferenced pointer = max engagement range) |
| `+0x34` | Locked-target id/handle, unconfirmed (§6 item 2) |
| `+0x38` | Cached double from the locked-target lookup, unconfirmed |
| `+0x40` | Charge/power being fired this shot |
| `+0x48` | Static per-weapon range stat (§6 item 11) |

**Shield unit** (per-unit fields, array at `ship+0x7f8`; extends what §3.6/§3.9 already had):

**Container layout correction (`TORPEDO_IMPACT` session):** unlike Tube (`ship+0x454`) and Bank
(`ship+0x438`), which are containers holding a *pointer* to a packed array of separately-allocated
unit pointers, Shield's array is **embedded in-place**: count (ushort) at `container+0x0`, then
units packed directly starting at `container+0x8`, stride `0x48` bytes, no pointer indirection at
all. Confirmed by decompiling the facing-selection function (`FUN_0040b180`) directly rather than
assuming the same shape as Tube/Bank — that assumption caused a real live-testing crash (an
`OSError` reading through a garbage pointer) before being caught. **Don't assume every subsystem
array shares one container shape without checking** — see `TORPEDO_IMPACT_MAP.md` §7 for the full
story.

| Offset | Field |
|---|---|
| `+0x20` | State/type enum; `10` = REINFORCED |
| `+0x28` | Hits-this-frame counter (ushort) |
| `+0x30` | Live charge percentage (double, 0–100ish) |
| `+0x38` | Live shield integrity (double) — degrades on absorption, floors at 0, syncs `+0x30` downward |
| `+0x40` | Pointer to array container → `+0x1bc` → Shield TypeRecord (`class_data+0x1d0`) |
| `+0xb` (word, within array stride) | Facing-coverage bitmask (§2.1) |

**`class_data` tail fields** (extends `ENERGY_SYSTEM_MAP.md` §3.9's "still unresolved" list):

| Offset | Value (HC / Destroyer / Frigate) | Role |
|---|---|---|
| `+0x380` | `0` / `0` / `0` (confirmed live for HC too) | Copied into `ship+0x110`; not meaningfully used (§0, §4.1) |
| `+0x390` | `1.0` (live-confirmed for HC) | Linked-ship malfunction-risk scaling factor (already suspected §3.9, now confirmed) |
| `+0x3a0` | `75.0` / `60.0` / `50.0` (live-confirmed for HC) | Per-class instant-destruction threshold (§4.1) |

---

## 8. Constants used in this chain

| VA | Value | Role |
|---|---|---|
| `0x00465060` | **45.0** | New. Numerator of the phaser damage falloff term, `45.0 / weaponRangeStat` |
| `0x00464bd0` | 0.5 | Reused (already known from Drive/§3.1) — the *real* final multiplier in the phaser damage formula. **Not** `4.0` — see §5. |
| `0x00464688` | 100.0 | Reused (generic percent→fraction) — shield charge-percentage-to-EU conversion |
