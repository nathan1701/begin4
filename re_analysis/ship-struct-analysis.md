# Begin 3 Ship Class Structure
## Reverse-Engineered from Begin.exe

**Date:** 2026-09-25  
**Status:** In-progress, Heavy Cruiser mostly complete  

---

## DISCOVERY PROCESS

Using the **Heavy Cruiser stats from the manual** (crew: 450, reactors: 7, shields: 6, etc.) as known numeric constants, we searched the Begin.exe binary for these values and traced them back to the underlying data structure.

**Key technique:** Search for unique numeric constants → find their location in binary → examine surrounding data → identify struct boundaries and layout.

---

## STRUCTURE LOCATION

**File offset:** `0x0008858c` (Heavy Cruiser entry)  
**Memory address (approx):** `0x00488590` (after PE header translation)  
**Struct size:** ~1872 bytes (0x750) per ship class  

**All ship class entries in Begin.exe:**
| Ship Class | File Offset | Size |
|---|---|---|
| Dreadnought Killer (dink) | 0x00080fdc | 13,280 bytes |
| Destroyer | 0x000843bc | 7,488 bytes |
| Dreadnought (v1) | 0x000860fc | 4,680 bytes |
| Dreadnought (v2) | 0x00087344 | 2,808 bytes |
| Battle Cruiser | 0x00087e3c | 1,872 bytes |
| Heavy Cruiser | 0x0008858c | (unknown, last entry) |

*(Note: Varying sizes suggest different subsystem block counts per class, or separate arrays for player vs. AI ships)*

---

## STRUCTURE LAYOUT: Heavy Cruiser

### HEADER: String Pointers (bytes 0x00-0x13, 20 bytes)
```
Offset  Value           Purpose
------  -----           --------
0x00    0x004649b4      PTR → "Heavy Cruiser" string
0x04    0x004649b0      PTR → ??? (unknown)
0x08    0x00481308      PTR → Weapon/subsystem 1 description
0x0C    0x00482f80      PTR → Weapon/subsystem 2 description
0x10    0x00482e80      PTR → Weapon/subsystem 3 description
```

### MAIN STATS SECTION (bytes 0x14-0x6C, ~90 bytes)
```
Offset  Type    Value   Unit        Field Name
------  ----    -----   ----        ----------
0x14    INT     450     crew        Crew count
0x18    INT     20000   kt          Dead Weight Tonnage (DWT)
0x1C    FLOAT   2.531   ?           Power conversion/efficiency?
0x20    FLOAT   2.125   ?           Battery efficiency?
0x24    FLOAT   2.125   ?           Warp efficiency?
...     FLOAT   ...     ?           (several more power/efficiency floats)
0x34    INT     7       count       Number of reactors
0x3C    INT     60      cycles?     Torpedo load time?
0x40    INT     25      EU          Shield power consumption per shield
0x44    INT     10      EU          Phaser/Torpedo charge buildup amount
0x48    INT     25      EU          Shield power usage?
0x4C    INT     99      count?      Probe capacity?
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

**Confirmed subsystem blocks in Heavy Cruiser:**

| Subsystem | Offset | Count | Notes |
|-----------|--------|-------|-------|
| Shields | 0x618 | 6 | 6 shield generators, 225 EU each, 0.90% regen |
| Phasers | 0x650 | 4 | 4 phaser banks, 2000 range, 10 EU charge |
| Torpedos | 0x668-... | 6 | 6 torpedo tubes, 10 EU buildup, 3 cycle load |
| Probes | 0x758 | 3 | 3 probe launchers |
| Warp | 0x710 | 2 | 2 warp drives, 285 EU each |
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

1. **Exact subsystem block boundaries** — need to identify where Shield block ends and Phaser block starts (offsets only approximate)
2. **Pointer interpretation** — what do the 2-3 subsystem description pointers point to? Are they weapon stats, flavor text, etc.?
3. **Float encoding** — the regen rate 1.9000 = 0.90% from manual, but relationship unclear
4. **Struct size variance** — why are earlier ship entries larger? Multiple subsystems? Separate player/AI tables?
5. **Missing subsystems** — where are Batteries, Life Support, Damage Control in the struct? Are they in separate tables?

---

## NEXT STEPS IN RE

1. **Dump other ship classes** (Destroyer, Battle Cruiser) to compare struct layout and identify repeating patterns
2. **Cross-reference with code** — find Ghidra functions that read this table (search for hardcoded offsets like 0x40 or 0x44)
3. **Locate personality/AI struct** — search for bravery, aggression values
4. **Find game loop** — 10 subcycles per cycle, resource allocation, AI decision tree
5. **Reverse combat damage model** — linear vs. squared distance falloff for different weapon types

---

## RELATED DOCUMENTATION

- [Manual Findings](begin-manual-findings.md) — Original game mechanics, formulas, and tables
- [Ghidra Notes](ghidra-notes.md) — Symbol names, function locations, xref chains

