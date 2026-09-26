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

## Key Functions to Analyze

### Energy Processing: FUN_004035b0
- **Accesses ship struct fields at many offsets**
- Reads from offset 0xf0, 0xe4, 0x148, 0x390...
- Calls:
  - FUN_0040ab50, FUN_0040bdc0, FUN_004088c0, FUN_00409cb0
  - FUN_00409600, FUN_0040a710, FUN_004090c0, FUN_0040ba00
  - FUN_0040b740, FUN_00409530, FUN_0040a630
- **NEXT:** Decompile these to find crew, reactor, weapon access patterns

### Top-Level Caller: FUN_00419bb0
- **Location:** 0x00419bb0  
- Calls FUN_0040d330 at 0x00419dc6
- **NEXT:** Find who calls this - likely main() or game entry point

---

## String References Found

- 0x004649b4: "Heavy Cruiser" → referenced from 0x0048998c [DATA] and FUN_0040f190
- 0x004649a4: "Destroyer" → referenced from 0x0040f1b3 and 0x004857bc
- 0x00464c3c: "reactor" → referenced from FUN_004035b0
- 0x00465368: "Transported %d crew member%s..." → crew transport messages
- 0x004660d8: "%d Transporter%s..." → crew capacity

---

## Data Structures Identified

### Ship Object Layout (from code)
- Offset 0x2c: Virtual method pointer (AI decision)
- Offset 0x30: Virtual method pointer (combat/weapons?)
- Offset 0x34: Next ship pointer (linked list)
- Offset 0xc: Some comparison field (used in FUN_0040f190)
- Offset 0xc58: ?
- Offset 0xd0: ?
- Offset 0x316: ?

### Energy/Reactor Calculation (from FUN_004035b0)
- Offset 0xf0: Primary energy value
- Offset 0xe4: Pointer to ship class/template data
- Offset 0x148: Target ship reference (?)
- Offset 0x390: Some multiplier (energy efficiency?)

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
