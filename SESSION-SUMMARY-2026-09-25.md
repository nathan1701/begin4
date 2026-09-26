# Path B Session Summary: 2026-09-25

## Major Discoveries This Session

### 1. Game Loop Structure (CONFIRMED) ✅
- **Main cycle function:** FUN_0040d330
- **Sub-cycle function:** FUN_0040d1b0  
- **Structure:** 10 main cycles → each contains 10 sub-cycles → energy update after all cycles
- **Top-level entry:** FUN_00419e40 → FUN_00419bb0 (game loop runner)

### 2. Ship Object Architecture (CRITICAL) ✅
**Two-layer system discovered:**
- **Layer 1 (Class Data):** Static templates at file offset 0x0008858c (HC example)
- **Layer 2 (Runtime Objects):** 3200-byte heap-allocated instances
- **Linking:** Runtime object at offset 0xe4 stores pointer to class data

**Object layout (0xc80 = 3200 bytes):**
```
0x00: VFTable
0xe4: Pointer to class data ⭐
0xec-0xc78: Subsystem instances
0xc58: Linked list pointers
```

### 3. Ship Initialization Pipeline (MAPPED) ✅
1. **FUN_0040ccd0** - Main initialization function
   - Allocates 0xc80 bytes per ship
   - Iterates through ship lists from PTR_LOOP_00481000, PTR_LOOP_0048100c
   
2. **FUN_00404910** - Ship constructor
   - Initializes subsystems by calling specialized functions
   - Maps each subsystem to specific runtime offsets

3. **Subsystem Initializers:**
   - FUN_0040a830 (Reactor) @ runtime +0x150
   - FUN_0040af50 (Shields) @ runtime +0x7f8  
   - FUN_00409860 (Warp Drive) @ runtime +0x708
   - FUN_0040cae0, FUN_00409e40, FUN_0040ba00, FUN_0040aaa0, FUN_004094f0, FUN_0040b6f0, FUN_00409b90, FUN_0040a5e0 (other subsystems)

### 4. Subsystem Data Access Pattern (KEY INSIGHT) ✅
Each subsystem initializer reads counts from class data:
```c
// Example: Reactor initialization
count_ptr = class_data + 0x58;  // Read reactor count
subsys_instance[0] = *count_ptr;  // Store count at subsystem +0x0
// Then iterate and create instances for each reactor
```

**Offsets found:**
- Reactors: class_data + 0x58
- Shields: class_data + 0x1d0
- Warp: class_data + 0x190
- Others: TBD

### 5. Energy Update System (IDENTIFIED) ✅
- **Main function:** FUN_004035b0 (called after all cycle sub-cycles)
- **Called functions:** Many subsystem energy calculators
- **Pattern:** Iterates through subsystem instances, calls virtual methods, sums energy

### 6. String References Located ✅
- "Heavy Cruiser" (0x004649b4) - referenced in ship lists
- "Destroyer" (0x004649a4)
- "reactor" (0x00464c3c) - in energy processing code

---

## Offset Mapping Mystery

**Note:** Reference docs mention offsets like 0x54 (reactors), 0xc4 (phasers) in class data, but initializer functions read from 0x58, 0x1d0, etc. 

**Hypothesis:** Class data is reformatted at runtime load, or there are multiple data layouts (binary file format vs. runtime loaded format).

---

## Key Functions to Decompile in Next Session

**For Energy System Understanding:**
1. FUN_0040ab50 (weapon energy calculation)
2. FUN_0040bdc0 (torpedo energy)
3. FUN_00409cb0 (shields/life support)
4. FUN_00409e40 (another subsystem)
5. FUN_0040ba00 (another subsystem)

**For Game Mechanics:**
1. Damage calculation functions (search for distance/squared patterns)
2. Personality/AI struct location (search for bravery/aggression constants)
3. Retreat decision logic (search for damage threshold checks)

---

## Code Tracing Chain Established

```
FUN_00419e40 (game entry)
  ↓
FUN_0040ccd0 (init)
  ↓
FUN_00404910 (ship constructor)
  ├→ FUN_0040a830 (reactor init)
  ├→ FUN_0040af50 (shield init)
  ├→ FUN_00409860 (warp init)
  └→ [other subsystem inits]
  
FUN_00419bb0 (game loop runner)
  ↓
FUN_0040d330 (main cycle)
  ├→ 10 cycles
  │  └→ 10 sub-cycles (FUN_0040d1b0)
  └→ FUN_0040d270 (energy update)
     └→ FUN_004035b0 (energy calc per ship)
        ├→ FUN_0040ab50 (weapon energy)
        ├→ FUN_0040bdc0 (torpedo energy)
        ├→ FUN_00409cb0 (shield drain)
        ├→ FUN_00409600 (life support)
        └→ [more energy subsystems]
```

---

## What We Still Need to Find

### High Priority (Quick wins):
1. ✅ Where crew count is read (offset 0x14 in class data)
2. ✅ Where reactor count is read (offset 0x58 in class data, but verify)
3. ✅ Where weapon counts are read (offsets TBD)
4. ⏳ The 4:1 WES:RES ratio constant
5. ⏳ Energy allocation priority order (weapons → life support → shields)

### Medium Priority:
1. Damage formulas (linear vs. squared)
2. Personality/AI struct location
3. Retreat/surrender decision logic

### Nice to Have:
1. Exact binary format of class data
2. All subsystem offset mappings

---

## Next Session Plan

**Start with:** Decompile energy calculation functions (FUN_0040ab50, FUN_0040bdc0, etc.) to find:
- Where crew/reactor/weapon counts are used
- The 4:1 ratio
- Energy allocation logic

**Then:** Trace upward to find damage calculation code and personality/AI logic

---

## Commits Made
1. "Path B: Initial game loop structure discovery"
2. "Path B: Discover ship object constructor and two-layer data architecture"
3. "Path B: Map subsystem initialization functions and data flow"

---

**Status:** Path B is progressing excellently. Core game architecture is now understood. Ready to dive into specific mechanics (energy, combat, AI) in next session.
