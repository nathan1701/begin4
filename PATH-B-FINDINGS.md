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

## Subsystem Initialization & Data Flow

### How Subsystem Counts Are Read

Each subsystem initializer reads the COUNT from class data at a specific offset, then creates an array of subsystem instances:

**Reactor Initializer (FUN_0040a830, at ship runtime +0x150):**
```c
psVar3 = (short *)(*(int *)(ship + 0xe4) + 0x58);  // Read reactor count from class
*(short *)this = *psVar3;  // Store count at subsystem +0x0
// Then iterate and initialize each reactor
```

**Shield Initializer (FUN_0040af50, at ship runtime +0x7f8):**
```c
puVar4 = (undefined2 *)(*(int *)(ship + 0xe4) + 0x1d0);  // Read shield count
*(undefined2 *)this = *puVar4;  // Store at subsystem +0x0
```

**Warp Drive Initializer (FUN_00409860, at ship runtime +0x708):**
```c
psVar4 = (short *)(*(int *)(ship + 0xe4) + 400);  // 0x190 in hex
*(short *)this = sVar1;  // Store count
```

### Subsystem Array Pattern

Each subsystem creates an array where offset +0x0 stores the COUNT, then individual instances follow:
```
Subsystem instance array:
+0x0: Count of this subsystem (e.g., 7 for reactors)
+0x x: Individual instance 1 data
+0x xx: Individual instance 2 data
...
```

This explains why energy calculations iterate through these arrays - each subsystem instance calculates its own energy cost/generation.

### Offset Mapping Notes

⚠️ **Offset confusion:** Reference docs mention 0x54 for reactors, 0xc4 for phasers in class data, but initializers read from different offsets (0x58 for reactors, etc.). This suggests either:
1. File format ≠ Runtime format (data is reformatted when loaded)
2. Multiple data tables with different layouts
3. Offset calculations applied during loading

**Next investigation:** Trace class data loading to understand offset mapping.

## Next Steps

### Tier 1 (Immediate) ✅ IN PROGRESS
- ✅ Found game loop structure (10 cycles × 10 subcycles)
- ✅ Found ship initialization and subsystem creation
- ✅ Found subsystem initializers reading from class data
- ⏳ **Need:** Map exact class data offsets for crew, reactors, weapons
- ⏳ **Need:** Find where class data is loaded/reformatted

### Tier 2 (Energy System)
1. Decompile crew/reactor/weapon functions called from energy update (FUN_004035b0)
2. Trace how these subsystem counts flow into energy allocation
3. Find the 4:1 WES:RES ratio constant

### Tier 3 (Combat & AI)
1. Find damage calculation code (linear for phasers, squared for torpedos)
2. Locate personality/bravery struct
3. Find retreat decision logic

---

## Key Insights

✅ **The game uses a 10x10 cycle/sub-cycle structure** (confirmed in code!)
✅ **Energy updates happen AFTER all movement/combat cycles**
✅ **Ships are in a linked list** (FUN_0040d1b0 iterates PTR_LOOP_0048b33c)
✅ **Ship classes use virtual methods** (vtable at offset 0 of ship object)

---

## Addendum (Path B4, 2026-09-26): Runtime subsystem offsets confirmed

The runtime object layout above held up well under further tracing. Path B4 independently
confirmed several of these subsystem offsets by finding the actual per-frame update code
(`FUN_00404250`) and matching it against notification strings and behavior:

- **`0x150` (Reactor)** and **`0x708` (Warp/Drive)** — confirmed as listed here
- **`0x7f8` (Shields)** — confirmed; this is where the real "Reinforced shields require 4x
  power" mechanism lives (see `re_analysis/ENERGY_SYSTEM_MAP.md` §3.2)
- **`0xc20` (Cloak)** — confirmed via `"We have uncloaked due to lack of power.\n"`
- **`0xb88`/`~0xbb8` (Tractor Beam)** — confirmed via `"Our tractor beam has failed due to lack
  of power.\n"`

One important correction: **the ship struct read by `FUN_0040f4b0` (the status-display
function) is NOT this runtime object.** It's a separate, flattened summary struct built fresh
for display, with a completely different field layout. Don't assume an offset found via
`FUN_0040f4b0` applies to the `0xc80`-byte runtime object mapped here, or vice versa — see
`ENERGY_SYSTEM_MAP.md` §1 for the full three-structure breakdown (Class Data / Runtime Object /
Display struct).

Full energy-system writeup, including the two confirmed "4x" mechanisms and the corrected
constant map: **[`re_analysis/ENERGY_SYSTEM_MAP.md`](re_analysis/ENERGY_SYSTEM_MAP.md)**.

---

Generated: 2026-09-25
Status: **Active tracing in progress** (energy system: complete as of Path B4, 2026-09-26 — see addendum above)
