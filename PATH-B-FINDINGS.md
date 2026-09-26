# Path B: Code Analysis Findings

## Game Loop Structure Discovered ✅

### Main Cycle Function: FUN_0040d330
**Location:** 0x0040d330  
**Called from:** FUN_00419bb0 (0x00419dc6)

Structure:
```
FUN_0040d330():
  └─ 10 main cycles (iVar4 = 10..0)
     ├─ Pre-processing per cycle:
     │  ├─ FUN_00401e10(ship) - movement/targeting?
     │  ├─ FUN_00402510(ship)
     │  └─ FUN_00403f70(ship)
     │
     ├─ 10 sub-cycles (iVar3 = 10..0)
     │  └─ FUN_0040d1b0()  [Sub-cycle handler]
     │
     └─ After all cycles:
        └─ FUN_0040d270()  [Energy/Reactor Update]
```

### Sub-Cycle Function: FUN_0040d1b0
**Location:** 0x0040d1b0  
Each sub-cycle performs:
```
1. Virtual method 0x2c() on all ships  [AI/Decision making]
2. FUN_0040d050()  [Global update]
3. FUN_00402b60(ship)
4. FUN_00402460(ship)
5. Virtual method 0x30() on all ships
6. FUN_0040d050()  [Global update]
7. FUN_00402b60(ship)
```

### Energy/Reactor Update: FUN_0040d270
**Location:** 0x0040d270  
Processes energy systems on all ships:
```
1. Virtual method 0x2c() on all ships
2. FUN_00402b60(ship)
3. FUN_004035b0(ship)  ← Processes "reactor" string & energy allocation
4. FUN_00403be0(ship)
5. FUN_00404020(ship)
```

---

## Ship Object Construction (CRITICAL DISCOVERY)

### Ship Constructor: FUN_00404910
**Location:** 0x00404910  
**Allocates:** 0xc80 bytes (3200 bytes per ship object)  
**Called from:** FUN_0040ccd0 (game initialization)

**Runtime Ship Object Layout:**
```
Offset  Purpose
------  -------
0x00    Virtual function table (vftable)
0xe0    Pointer to some status/tracking struct
0xe4    ⭐ POINTER TO SHIP CLASS DATA ⭐
0xe8    Crew count? (result from FUN_004011b0)
0xec    Subsystem struct (initialized by FUN_00418080)
0x110   Value from class data at offset 0x380
0x150   Subsystem struct (initialized by FUN_0040a830)
0x2a0   Subsystem struct (initialized by FUN_00409270)
0x438   Subsystem struct (initialized by FUN_00408e60)
0x454   Subsystem struct (initialized by FUN_0040cae0)
0x470   Subsystem struct (initialized by FUN_00409e40)
0x708   Subsystem struct (initialized by FUN_00409860)
0x7f8   Subsystem struct (initialized by FUN_0040af50)
0x9c0   Subsystem struct (initialized by FUN_0040bac0)
0xb50   Subsystem struct (initialized by FUN_0040aaa0)
0xb88   Subsystem struct (initialized by FUN_004094f0)
0xc00   Subsystem struct (initialized by FUN_0040b6f0)
0xbf0   Subsystem struct (initialized by FUN_00409b90)
0xc20   Subsystem struct (initialized by FUN_0040a5e0)
0xc58   Next ship pointer (linked list)
0xc5c   Previous ship pointer (linked list)
0xc60   Owner reference
```

**KEY INSIGHT:** 
- Runtime object at 0xe4 stores a **pointer to class data**
- Class data (at file offset 0x0008858c) contains:
  - Crew: offset 0x14
  - Reactors: offset 0x34 (**not 0x54**)
  - Individual subsystems at various offsets
- To read crew, code does: `*(int *)((ship_object_ptr + 0xe4)[0x14])`

### Game Initialization: FUN_0040ccd0
**Location:** 0x0040ccd0  
Allocates 0xc80 bytes for each ship and calls FUN_00404910 to initialize.
Iterates through ship lists from PTR_LOOP_00481000 and PTR_LOOP_0048100c.

### Top-Level Entry: FUN_00419e40
- **Location:** 0x00419e40  
- **Callers:** Calls FUN_0040ccd0 (init), then FUN_00419bb0 (game loop)
- Shows complete game startup sequence

## Energy Processing: FUN_004035b0
- **Accesses ship struct fields at many offsets**
- Uses param_1 (runtime ship object) to get class data pointer at 0xe4
- Then accesses fields from class data
- Calls subsystem energy calculation functions

---

## String References Found

- 0x004649b4: "Heavy Cruiser" → referenced from 0x0048998c [DATA] and FUN_0040f190
- 0x004649a4: "Destroyer" → referenced from 0x0040f1b3 and 0x004857bc
- 0x00464c3c: "reactor" → referenced from FUN_004035b0
- 0x00465368: "Transported %d crew member%s..." → crew transport messages
- 0x004660d8: "%d Transporter%s..." → crew capacity

---

## Data Structure Model: TWO-LAYER ARCHITECTURE

The game uses **two separate data structures**:

### Layer 1: Class Definition (Static, in binary)
**Location:** File offset 0x0008858c (Heavy Cruiser example)  
**Properties:** Shared template data, loaded once at startup

```
Offset  Field
------  -----
0x00    Pointers to class name strings
0x14    Crew count (INT) - e.g., 450 for HC
0x18    Dead Weight Tonnage (INT)
0x34    Number of reactors (INT) - e.g., 7 for HC
0x40    Shield power per unit
0x44    Phaser charge buildup
0x618   Shields subsystem block
0x650   Phasers subsystem block
0x668   Torpedos subsystem block
...     More subsystems
```

### Layer 2: Runtime Object (Instance-specific, heap-allocated)
**Size:** 0xc80 bytes (3200 bytes)  
**Created by:** FUN_00404910 (constructor)  
**Properties:** One per ship in game, stores current game state

```
Offset  Field
------  -----
0x00    Virtual function table
0xe4    ⭐ POINTER TO CLASS DATA (Layer 1)
0xe8    Crew count (cached/current)
0xec-0xc78  Subsystem instances (initialized from class)
0xc58   Linked list pointers
```

**Code Access Pattern:**
```
To read crew from runtime object:
  ship_runtime = ...  // runtime object at 0xe4
  ship_class = *(int*)(ship_runtime + 0xe4)  // get class pointer
  crew = *(int*)(ship_class + 0x14)  // read crew from class
```

---

## Next Steps

### Tier 1 (Immediate)
1. Decompile crew-reading functions called from energy update
2. Decompile reactor-reading functions
3. Decompile weapon-counting functions
4. Find the 4:1 WES:RES ratio constant

### Tier 2 (Understand)
1. Trace FUN_00419bb0 upward to find game entry point
2. Map all virtual method callers (0x2c, 0x30)
3. Understand the linked list iteration structure

### Tier 3 (Refinement)
1. Cross-reference ship data memory with struct analysis
2. Find damage calculation code
3. Locate personality/bravery struct

---

## Key Insights

✅ **The game uses a 10x10 cycle/sub-cycle structure** (confirmed in code!)
✅ **Energy updates happen AFTER all movement/combat cycles**
✅ **Ships are in a linked list** (FUN_0040d1b0 iterates PTR_LOOP_0048b33c)
✅ **Ship classes use virtual methods** (vtable at offset 0 of ship object)

---

Generated: 2026-09-25  
Status: **Active tracing in progress**
