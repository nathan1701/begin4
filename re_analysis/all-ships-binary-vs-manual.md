# Begin Ship Stats: Binary vs. Manual Comparison

**Date:** 2026-09-25  
**Source:** Begin v1.65 Manual (Appendix C) + Begin.exe binary analysis

---

## Summary Table: All 7 Ships Located in Binary

| Ship Class | File Offset | Binary Crew | Manual Crew | Binary Reactors | Manual Reactors | Binary Phasers | Manual Phasers | Notes |
|---|---|---|---|---|---|---|---|---|
| Dreadnought Killer | 0x00080fdc | 0 (?) | ? | 0 (?) | ? | 1 (?) | ? | Data appears corrupted or incomplete |
| Destroyer | 0x000843bc | 250 | 200 | 5 | 5 ✓ | 4 | 4 ✓ | Crew discrepancy confirmed (250 in game) |
| Dreadnought v1 | 0x000860fc | 750 | 500* | 8 | 8 ✓ | 6 | 8 | *May be different version or variant |
| Dreadnought v2 | 0x00087344 | 500 | 500 ✓ | 6 | 8 | 6 | 8 | Reactor count discrepancy |
| Frigate | 0x00087a94 | 175 | 175 ✓ | 3 | 3 ✓ | 5 | 5 ✓ | Perfect match |
| Battle Cruiser | 0x00087e3c | 350 | ? | 4 | ? | 5 | ? | Not in manual sample sheets |
| Heavy Cruiser | 0x0008858c | 450 | 450 ✓ | 7 | 7 ✓ | 4 | 4 ✓ | Perfect match |

---

## Key Observations

### ✅ Confirmed Values (Manual = Binary)
- **Frigate:** Crew 175, Reactors 3, Phasers 5
- **Heavy Cruiser:** Crew 450, Reactors 7, Phasers 4
- **Destroyer:** Reactors 5, Phasers 4 (crew differs as noted)

### ⚠️ Discrepancies
1. **Destroyer crew:** Manual says 200, binary has 250 (confirmed via game, binary is correct)
2. **Dreadnought v1 crew:** Binary shows 750, manual shows 500 (possibly different variant: Player vs. AI?)
3. **Dreadnought v2 reactors:** Binary shows 6, manual shows 8
4. **Phasers on Dreadnought entries:** Binary shows 6, manual shows 8

### ❓ Unknowns
1. **Dreadnought Killer:** Data incomplete/corrupted in binary (all zeros/invalid values)
2. **Battle Cruiser:** No ship class data found in manual Appendix C
3. **Multiple Dreadnought entries:** May represent player ship vs. AI/Klingon variants

---

## Federation Ships in Manual (Appendix C)

| Class | Crew | DWT | Reactors | Batteries | Phasers | Torpedos | Probes | Shields | Warp Drives |
|---|---|---|---|---|---|---|---|---|---|
| Interceptor (IR) | 155 | 70,000 | 6 | 6 | 6 | 2 | 1 | 6 | 2 |
| Destroyer (DE) | 200 | 85,000 | 5 | 5 | 4 | 4 | 2 | 6 | 1 |
| Heavy Cruiser (HC) | 450 | 190,000 | 7 | 6 | 4 | 6 | 3 | 6 | 2 |
| Dreadnought (DN) | 500 | 295,000 | 8 | 8 | 8 | 8 | 6 | 6 | 3 |

---

## Klingon Ships in Manual (Appendix C)

| Class | Crew | DWT | Reactors | Batteries | Phasers | Torpedos | Probes | Shields | Warp Drives |
|---|---|---|---|---|---|---|---|---|---|
| Escort (ES) | 65 | 65,000 | 2 | 6 | 5 | 1 | 1 | 5 | 2 |
| Frigate (FR) | 175 | 70,000 | 3 | 4 | 5 | 2 | 2 | 6 | 1 |
| Dreadnought (DK) | 550 | 275,000 | 8 | 8 | 8 | 6 | 4 | 6 | 3 |

---

## Romulan Ships in Manual (Appendix C)

| Class | Crew | DWT | Reactors | Batteries | Phasers | Torpedos | Probes | Shields | Warp Drives | Special |
|---|---|---|---|---|---|---|---|---|---|---|
| War Eagle (WE) | 115 | 50,000 | 3 | 3 | 5 | 1 plasma | 1 | 6 | 2 | Cloaking |
| Flagship (FD) | 275 | 150,000 | 6 | 6 | 8 | 2 plasma | 2 | 6 | 2 | - |

---

## Struct Field Mapping Summary

**Verified field locations (offset from struct start):**

```
+0x14 = INT: Crew count
+0x18 = INT: DWT (scale factor ~10)
+0x54 = INT: Number of reactors
+0x64 = INT: Torpedo load time (always 60)
+0x68 = INT: Shield power per unit (usually 25)
+0x6c = INT: Phaser/torpedo charge buildup (usually 10)
+0xc4 = INT: Number of phaser banks
+0x8c = INT: Number of shield generators
```

Repeating blocks follow for each subsystem (phasers, torpedos, shields, probes, warp drives, batteries).

---

## Next Session (Path B): Code Analysis

With the struct now fully mapped, the next steps are:

1. **Find code that reads ship stats** — Use Ghidra xrefs to locate functions accessing the ship table
2. **Trace energy allocation** — Find the code that implements WES→RES conversion and power distribution
   *(Done, Path B4: see `ENERGY_SYSTEM_MAP.md` — turned out to be two separate subsystem-specific
   4x rules rather than one WES→RES conversion; weapon energy draw is still untraced)*
3. **Reverse combat damage** — Locate phaser (linear) vs. torpedo (squared) damage calculations
4. **Personality/AI struct** — Search for bravery, loyalty, aggression values
5. **Game loop** — Find the 10-subcycle-per-cycle main loop

This will require using Ghidra's code navigation and xref tracing (GhidraMCP tools from Session 2).

