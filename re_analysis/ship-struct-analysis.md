# Begin 3 Ship Class Structure
## Reverse-Engineered from Begin.exe

**Date:** 2026-09-25 (offsets corrected 2026-09-26, class-data mapping session)  
**Status:** In-progress, Heavy Cruiser mostly complete  

**CORRECTION (class-data mapping session, see `ENERGY_SYSTEM_MAP.md` §3.9 for the full story):**
every file offset and "MAIN STATS SECTION" offset below was originally found by searching the
binary for known manual numbers (crew=450, etc.), and that search was **off by 4 bytes** for every
ship class — confirmed by a live memory read of the running game (`read_live_classdata.py`). The
struct actually starts 4 bytes earlier than recorded here; crew is at `+0x18` (not `+0x14`), DWT at
`+0x1C` (not `+0x18`), and so on. All offsets below are corrected in place; anywhere a `~` or `?`
was already present it remains a genuine open question, not something this correction resolved.

---

## DISCOVERY PROCESS

Using the **Heavy Cruiser stats from the manual** (crew: 450, reactors: 7, shields: 6, etc.) as known numeric constants, we searched the Begin.exe binary for these values and traced them back to the underlying data structure.

**Key technique:** Search for unique numeric constants → find their location in binary → examine surrounding data → identify struct boundaries and layout.

---

## STRUCTURE LOCATION

**File offset:** `0x00088588` (Heavy Cruiser entry) — **corrected from `0x0008858c`, off by 4
bytes; see the correction banner at the top of this doc**  
**Memory address:** `0x00489988` — **corrected from `0x0048998c`**; confirmed live via
`/proc/<pid>/mem` against a running copy of the game (Heavy Cruiser, class-data mapping session)  
**Struct size:** ~1872 bytes (0x750) per ship class (unaffected by the offset correction — this was
always a gap-to-next-entry measurement, not tied to the internal offset labeling)  

**All ship class entries in Begin.exe (corrected, -4 from the original values):**
| Ship Class | File Offset | Size |
|---|---|---|
| Dreadnought Killer (dink) | 0x00080fd8 | 13,280 bytes |
| Destroyer | 0x000843b8 | 7,488 bytes |
| Dreadnought (v1) | 0x000860f8 | 4,680 bytes |
| Dreadnought (v2) | 0x00087340 | 2,808 bytes |
| Battle Cruiser | 0x00087e38 | 1,872 bytes |
| Heavy Cruiser | 0x00088588 | (unknown, last entry) |

*(Note: Varying sizes suggest different subsystem block counts per class, or separate arrays for player vs. AI ships. Only Heavy Cruiser/Destroyer/Frigate's corrected offsets were independently re-verified this session against the manual — the Dreadnought/Battle Cruiser rows above just have the same -4 arithmetic applied and haven't been re-checked field-by-field.)*

---

## STRUCTURE LAYOUT: Heavy Cruiser

### HEADER (bytes 0x00-0x17, corrected — an extra field at the true +0x00 was missing before)
```
Offset  Value           Purpose
------  -----           --------
0x00    0                  Unidentified. Zero for Heavy Cruiser. NOT a vtable pointer (would be
                           a non-zero address if it were) - open question, low priority.
0x04    0x004649b4      PTR → "Heavy Cruiser" string
0x08    0x004649b0      PTR → ??? (unknown, adjacent to the name string, maybe a short code/class tag string)
0x0C    0x00481308      PTR → class_data+0xC's table - NOT a name pool (confirmed class-data
                           mapping session): a mix of doubles and a text fragment ("We have
                           examined your simulation results."). Real structure unresolved.
0x10    0x00482f80      PTR → ship-name pool ("Enterprise, Hornet, Trenton, Lexington, Defiant,
                           Independence, Republic" for Heavy Cruiser) - this is what `ship+0xe8`
                           is built from (code-relative class_data+0x10; see
                           `ENERGY_SYSTEM_MAP.md` §3.6/§3.9)
0x14    0x00482e80      PTR → commanding-officer surname pool ("Webster, Bronson, Eastwood, Stone,
                           Pike, Austin, Montgomery") - this is what `ship+0xec+0x8` is built from
                           (code-relative class_data+0x14; see `ENERGY_SYSTEM_MAP.md` §3.7/§3.9)
```

### MAIN STATS SECTION (bytes 0x18-0x70ish, corrected +4 from original) — confirmed fields only;
everything past DWT below is still an open hypothesis, not a finding (see TODO item 7)
```
Offset  Type    Value   Unit        Field Name
------  ----    -----   ----        ----------
0x18    INT     450     crew        Crew count — **confirmed** by code (disassembly of
                                     `FUN_00418080` and `FUN_004035b0`, both use this offset
                                     directly on the runtime class_data pointer) AND by a live
                                     memory read of a running game (class-data mapping session).
                                     Corrected from the old (wrong) `+0x14` label.
0x1C    INT     20000   kt          Dead Weight Tonnage (DWT) — corrected from the old `+0x18` label
0x20    FLOAT   2.531   ?           Power conversion/efficiency? — **unverified**, and possibly
                                     wrong data type: the ship constructor reads *doubles* (not
                                     4-byte floats) from this general region via `FUN_00401de0`
                                     (see `ENERGY_SYSTEM_MAP.md` §7 item 10) — needs re-deriving
                                     from code, not re-labeled by number-matching
0x24    FLOAT   2.125   ?           Battery efficiency? — unverified, same caveat as above
0x28    FLOAT   2.125   ?           Warp efficiency? — unverified, same caveat as above
...     FLOAT   ...     ?           (several more power/efficiency floats) — unverified
0x38    INT     7       count       Number of reactors — unverified at this specific offset (the
                                     code-confirmed Reactor TypeRecord count lives at the very
                                     different, verified offset `class_data+0x58`, see
                                     `ENERGY_SYSTEM_MAP.md` §3.8 — don't conflate the two)
0x40    INT     60      cycles?     Torpedo load time? — unverified
0x44    INT     25      EU          Shield power consumption per shield — unverified
0x48    INT     10      EU          Phaser/Torpedo charge buildup amount — unverified
0x4C    INT     25      EU          Shield power usage? — unverified
0x50    INT     99      count?      Probe capacity? — unverified
...     (padding and alignment)
```

### SUBSYSTEM BLOCKS: Repeating (each ~40-60 bytes)

**Pattern for each subsystem (shields, phasers, torpedos, probes, warp drives, etc.):**

```
+0x00   PTR     Subsystem description pointer 1
+0x04   PTR     Subsystem description pointer 2
+0x08   INT     count (# of this subsystem type)
+0x0C   INT     flags/padding (usually 0)
+0x10   FLOAT   efficiency / regeneration / reload rate
+0x14   INT     damage / power / range value
+0x18   INT     padding (usually 0)
+0x1C   INT     capacity or secondary count
+0x20   INT     power usage / cost per unit
+0x24-  ...     additional fields (variable)
```

**Confirmed subsystem blocks in Heavy Cruiser** (offsets shown with the same +4 correction applied
as everywhere else in this doc; per TODO item 1, this may be a *second*, separate table from the
code-confirmed TypeRecords in `ENERGY_SYSTEM_MAP.md` §3.8 — not re-verified by code this session):

| Subsystem | Offset | Count | Notes |
|-----------|--------|-------|-------|
| Shields | 0x61C | 6 | 6 shield generators, 225 EU each, 0.90% regen |
| Phasers | 0x654 | 4 | 4 phaser banks, 2000 range, 10 EU charge |
| Torpedos | 0x66C-... | 6 | 6 torpedo tubes, 10 EU buildup, 3 cycle load |
| Probes | 0x75C | 3 | 3 probe launchers |
| Warp | 0x714 | 2 | 2 warp drives, 285 EU each |
| Batteries | (TBD) | ? | ? battery units |
| Life Support | (TBD) | ? | ? life support modules |

---

## VERIFIED CONSTANTS vs. MANUAL

All values confirmed match the Heavy Cruiser specs from *Begin v1.65 Advanced Strategy Manual, Appendix C*:

✅ Crew: 450  
✅ Reactors: 7 @ 35 EU each  
✅ Shield Generators: 6 @ 225 EU protection each  
✅ Shield Regen Rate: 0.90% → appears as 1.9000 float (0.9 × 2 + offset?)  
✅ Phaser Banks: 4 @ 2000 range max  
✅ Phaser Charge: 10 EU  
✅ Torpedo Tubes: 6 @ 10 EU buildup  
✅ Probe Launchers: 3  
✅ Warp Drives: 2 @ 285 EU each  
✅ Shield Power Usage: 25 EU per shield generator  

---

## DATA TYPE PATTERNS

The struct mixes integer and floating-point data, likely to represent:
- **Integers:** Equipment counts, crew, charge amounts, power values, damage
- **Floats:** Efficiency percentages, regeneration rates, reload times (in some encoded form)
- **Pointers:** To string descriptions and subsystem info blocks

Alignment appears to be 4-byte boundaries (word-aligned on x86).

---

## UNKNOWNS / TODO

1. ~~**Exact subsystem block boundaries**~~ **Superseded — see `ENERGY_SYSTEM_MAP.md` §3.8.** The
   "subsystem blocks" described below (Shields at `+0x618`, Phasers at `+0x650`, etc.) were found by
   scanning raw bytes for known manual numbers, without knowing the real struct shape. Code-tracing
   every subsystem's constructor (the class-data mapping session) found a **different, earlier, and
   complete** set of 13 per-subsystem "TypeRecord" pointers at `+0x58` through `+0x380` — Reactor,
   Battery, Bank, Tube, Launcher, Drive, Shield, Transporter, Scanner, Cloak, Impulse, Tractor,
   LifeSupport, in that order, each confirmed by finding the actual `class_data+offset` constant in
   its `ConstructArray` function. The `+0x618`-region blocks below may be a second, different table
   (unconfirmed) rather than the same one — don't assume they're the same data restated.
2. **Pointer interpretation** — what do the 2-3 subsystem description pointers point to? Are they weapon stats, flavor text, etc.?
3. **Float encoding** — the regen rate 1.9000 = 0.90% from manual, but relationship unclear
4. **Struct size variance** — why are earlier ship entries larger? Multiple subsystems? Separate player/AI tables?
5. ~~**Missing subsystems**~~ **Resolved — see `ENERGY_SYSTEM_MAP.md` §3.8.** Batteries and Life
   Support (and all other subsystems) are not missing or in a separate table — they're TypeRecords
   at `class_data+0x90` (Battery) and `class_data+0x348` (LifeSupport), found the same way as the
   others.
6. **NEW — decode the 13 TypeRecords' contents** (`ENERGY_SYSTEM_MAP.md` §3.8/§7 item 9b, in
   progress). Offsets are known; internal field meanings (cost, charge rate, capacity, range,
   damage...) mostly aren't yet, except Bank's `+0x38`=`maxCharge`.
7. **RESOLVED, then corrected again — see `ENERGY_SYSTEM_MAP.md` §3.9.** This item originally
   flagged that `ENERGY_SYSTEM_MAP.md` §7 item 10 found three **doubles** read from
   `class_data+0x28/+0x30/+0x40`, contradicting this doc's old guess of three 4-byte floats at
   (uncorrected) `+0x1C/+0x20/+0x24`. It turned out the deeper problem was that this doc's entire
   file-offset table was off by 4 bytes (§3.9) — now fixed throughout this document. Crew (`+0x18`)
   and DWT (`+0x1C`) are confirmed by code AND a live memory read; everything past DWT in the "MAIN
   STATS SECTION" table remains an open hypothesis, not a finding, including whether the
   `class_data+0x28/+0x30/+0x40` doubles even correspond to any of the guessed float fields there.
8. **NEW — `class_data+0x00` and `class_data+0xC` are still unidentified** (class-data mapping
   session). `+0x00` is `0` for Heavy Cruiser and isn't a vtable pointer. `+0xC` points to a mixed
   table of doubles and a text fragment ("We have examined your simulation results.") that doesn't
   match the 17-byte-record-stride name-pool pattern used by `+0x10`/`+0x14`. Neither was resolved
   this session.
9. **RESOLVED — `class_data+0x380`/`+0x390`/`+0x3a0` (`COMBAT_DAMAGE` session, live-verified via
   `/proc/<pid>/mem`, see `COMBAT_DAMAGE_MAP.md` §4.1/§7 and `ENERGY_SYSTEM_MAP.md` §7 item 10).**
   `+0x380` is genuinely `0` for every class tested (HC/Destroyer/Frigate) — it's copied into
   `ship+0x110` at construction, which turns out to be scratch space in the damage-application
   function, not a stored "max hull" stat; Begin 3 has no accumulating hull-HP pool at all. `+0x390`
   is `1.0` (live-confirmed, HC) — a linked-ship malfunction-risk scaling factor. `+0x3a0` is the
   field that actually matters here: a per-class **instant-destruction damage threshold** —
   `75.0`/`60.0`/`50.0` EU for HC/Destroyer/Frigate (live-confirmed for HC). Worth adding a row for
   `+0x3a0` to a future revision of the "MAIN STATS SECTION" table above once more of the struct's
   tail region gets mapped — not done here since this doc's table stops well before `+0x380`.

---

## NEXT STEPS IN RE

1. **Dump other ship classes** (Destroyer, Battle Cruiser) to compare struct layout and identify repeating patterns
2. **Cross-reference with code** — find Ghidra functions that read this table (search for hardcoded offsets like 0x40 or 0x44)
3. **Locate personality/AI struct** — search for bravery, aggression values
4. **Find game loop** — 10 subcycles per cycle, resource allocation, AI decision tree
5. ~~**Reverse combat damage model** — linear vs. squared distance falloff for different weapon
   types.~~ **Done for phasers/Bank — see `COMBAT_DAMAGE_MAP.md`.** Confirmed **linear** falloff
   (`1 − distance/maxRange`, not squared) for the phaser/Bank weapon path specifically. **Torpedo/Tube
   fire chain now traced through launch (`TORPEDO_DAMAGE` session, see `TORPEDO_DAMAGE_MAP.md`)** —
   confirmed torpedoes really are physical projectile objects (`FUN_0043d97e(0x118)` allocation),
   genuinely different from Bank's instant hit-scan, not just a near-twin with a different range
   formula. **Still open: everything after launch** — the projectile's own travel/arming-timer/
   collision/impact code, where any damage falloff for torpedoes specifically would live
   (`TORPEDO_DAMAGE_MAP.md` §5 item 5) — completely untraced.

---

## RELATED DOCUMENTATION

- [Manual Findings](begin-manual-findings.md) — Original game mechanics, formulas, and tables
- [Energy System Map](ENERGY_SYSTEM_MAP.md) — Symbol names, function locations, and xref chains
  for the energy system specifically (this replaces a planned but never-written "Ghidra Notes"
  doc — as of Path B4 there's no single general symbol-notes file; findings live in the
  topic-specific docs like this one and `ENERGY_SYSTEM_MAP.md`)
- [`PATH-B-FINDINGS.md`](../PATH-B-FINDINGS.md) — Runtime ship object layout, game loop structure

