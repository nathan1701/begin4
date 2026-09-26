# Path B2 Handoff: Energy System & Combat Analysis

**Status:** Ready to analyze game mechanics  
**Date:** 2026-09-26 (after Path B architecture discovery)  
**Previous:** Path B mapped game loop, ship initialization, and subsystem structure  
**Next Session Focus:** Reverse the energy system (4:1 WES:RES ratio), damage calculations, and AI logic

---

## What Path B Accomplished ✅

### Game Loop Structure
- **10 main cycles per round** (from FUN_0040d330)
- **10 sub-cycles per cycle** (from FUN_0040d1b0)
- **Energy update after all cycles** (from FUN_0040d270 → FUN_004035b0)
- **Top-level entry:** FUN_00419bb0 (game loop runner)

### Ship Object Architecture
- **Two-layer system:** Class definitions (static) + Runtime objects (heap-allocated)
- **Runtime size:** 3200 bytes (0xc80) per ship
- **Class data pointer:** Stored at runtime offset 0xe4
- **Subsystems:** Initialized at specific offsets (0x150, 0x7f8, 0x708, etc.)
- **Linked list:** Ships stored at offset 0xc58 (doubly-linked)

### Initialization Pipeline
- **FUN_0040ccd0:** Main initialization (allocates ships, creates lists)
- **FUN_00404910:** Ship constructor (sets up 16+ subsystems)
- **Subsystem inits:** Each reads count from class data, creates instance array
  - FUN_0040a830 (Reactors @ runtime +0x150)
  - FUN_0040af50 (Shields @ runtime +0x7f8)
  - FUN_00409860 (Warp Drives @ runtime +0x708)
  - [8 more subsystem initializers...]

---

## Path B2 Goals (In Priority Order)

### 1. Find the 4:1 WES:RES Ratio ⭐ START HERE
**Objective:** Locate where weapon energy is limited by reactor energy

**From manual:** Weapon Energy System (WES) uses 4× the power of Reactor Energy System (RES)
- Likely pattern: `if (weapon_energy > reactor_energy * 4) { weapon_energy = reactor_energy * 4; }`

**Approach:**
- Decompile FUN_004035b0 (main energy calculator)
- Decompile sub-functions it calls:
  - FUN_0040ab50 (weapon/phaser energy)
  - FUN_0040bdc0 (torpedo energy)
  - FUN_00409cb0 (shields/life support)
  - FUN_00409600 (possibly reactors)
  - FUN_0040a710, FUN_004090c0, FUN_0040ba00 (other subsystems)
- Look for: Division by 4, multiplication by 4, comparisons with 4×
- Search for: Constants like 0.25 (1/4 ratio), 4.0 (float)

**Success criteria:**
- Found the line/function that enforces 4:1 ratio
- Understand energy allocation priority (weapons → shields → life support)
- Can explain how crew affects energy regeneration

---

### 2. Trace Crew/Reactor/Weapon Data Flow
**Objective:** Understand how subsystem counts feed into energy calculations

**What we know:**
- Crew count: Class data + 0x14 (value 450 for HC)
- Reactor count: Class data + 0x58 (value 7 for HC)
- Weapon counts: Class data offsets TBD (4 phasers, 6 torpedos for HC)

**To find:**
- How crew affects energy regeneration rate
- How reactor count affects max energy
- How weapon counts affect energy draw
- Where these constants are used in FUN_004035b0

**Success criteria:**
- Mapped data flow: subsystem counts → energy calculation
- Found crew/reactor multipliers
- Understand energy formula: `max_energy = reactors * reactor_power * efficiency`

---

### 3. Reverse Combat Damage Formulas
**Objective:** Find and confirm linear vs. squared distance falloff

**From manual:**
- **Phaser damage:** Linear falloff with range
  - Formula: `damage = max_damage - (distance * decay_factor)`
- **Torpedo/Probe damage:** Squared falloff
  - Formula: `damage = max_damage - ((distance ^ 2) * decay_factor)`

**Approach:**
- Search for distance calculations in combat/targeting functions
- Look for multiplication operations (distance * distance)
- Find where damage is reduced by range
- Trace from targeting code (FUN_00401e10 in main cycle?) to damage calc

**Success criteria:**
- Located phaser damage function
- Located torpedo damage function
- Confirmed linear vs. squared patterns
- Found decay factor constants

---

### 4. Locate Personality/AI Struct
**Objective:** Find where captain traits (bravery, loyalty, aggression, fanaticism) are stored

**From manual:**
- Bravery threshold: If `damage_taken >= bravery_value` → retreat
- Fanaticism: Overrides retreat (suicide run)
- Aggression: Affects targeting priority
- Loyalty: Affects fleet behavior

**Approach:**
- Search for comparison operations checking damage vs. threshold
- Look for retreat/surrender decision code
- Search for constants like 0-100 (typical AI stat ranges)
- Trace back to find where these values are loaded

**Success criteria:**
- Found the retreat decision logic
- Located personality stat storage
- Mapped bravery, aggression, loyalty, fanaticism fields
- Understand how fanaticism overrides retreat

---

## Tools & Setup

### Ghidra
- **Location:** `~/tools/ghidra_12.1.4_PUBLIC/ghidraRun`
- **Project:** `re_analysis/begin4-ghidra/begin3_project`
- **MCP Server:** Should auto-connect on startup
- **Status:** Ready to query functions, disassembly, decompilation

### Reference Files Ready
- `PATH-B-FINDINGS.md` — Detailed function analysis from Path B
- `SESSION-SUMMARY-2026-09-25.md` — Architecture overview
- `ship-struct-analysis.md` — Ship class data layout
- `all-ships-binary-vs-manual.md` — Crew/reactor/weapon counts verified
- `begin-manual-findings.md` — Game mechanics from manual

---

## How to Start Path B2 (Next Session)

### Step 1: Fire up Ghidra
```bash
cd /home/nathan/claude/begin4
~/tools/ghidra_12.1.4_PUBLIC/ghidraRun &
# Ghidra MCP should auto-connect
```

### Step 2: Load GhidraMCP Tools
When you start the next chat, tools should already be loaded. Test with:
```
decompile_function("FUN_004035b0")  # Main energy calculator
```

### Step 3: Start Energy System Analysis
**First priority:** Find the 4:1 ratio

Decompile in order:
1. `FUN_004035b0` — Main energy update function
2. `FUN_0040ab50` — Weapon energy (most likely to have ratio)
3. `FUN_0040bdc0` — Torpedo energy
4. `FUN_00409cb0` — Shields/life support

Look for: Comparisons, divisions, multiplications involving 4 or 0.25

### Step 4: Trace Data Flow
Once you find the 4:1 ratio check, trace backwards:
- What ship data feeds into it?
- How are crew/reactor/weapon counts used?
- What are the energy formulas?

### Step 5: Find Combat & AI
After energy system, search for:
- Distance calculations → damage functions
- Damage threshold checks → retreat logic
- Personality stat access → AI struct

---

## Key Addresses to Remember

### Main Functions
```
0x0040ccd0 - Game initialization
0x00404910 - Ship constructor
0x0040d330 - Main cycle (10 cycles)
0x0040d1b0 - Sub-cycle (10 per cycle)
0x00419bb0 - Game loop runner
0x004035b0 - Energy calculator (PRIORITY!)
```

### Energy Sub-functions
```
0x0040ab50 - Weapon/phaser energy
0x0040bdc0 - Torpedo energy
0x00409cb0 - Shields/drain
0x00409600 - Life support/crew
0x0040a710 - Another subsystem
0x004090c0 - Another subsystem
0x0040ba00 - Another subsystem
```

### Subsystem Initialization
```
0x0040a830 - Reactor init (reads class data +0x58)
0x0040af50 - Shield init (reads class data +0x1d0)
0x00409860 - Warp init (reads class data +0x190)
```

### Data Addresses
```
0x0008858c - Class data start (Heavy Cruiser in binary)
0x004649b4 - "Heavy Cruiser" string
0x00464c3c - "reactor" string
PTR_LOOP_0048b33c - Ships linked list (for iteration)
PTR_LOOP_0048b37c - Another ships list
```

---

## Function Call Flow for Energy System

```
FUN_00419bb0 (game loop)
  └─ FUN_0040d330 (main cycle)
     └─ 10 cycles with sub-cycles
     └─ FUN_0040d270 (after all cycles)
        └─ FUN_004035b0 (energy calculator PER SHIP) ⭐
           └─ For each ship:
              ├─ FUN_0040ab50 (weapon energy) ← likely has 4:1 ratio
              ├─ FUN_0040bdc0 (torpedo energy)
              ├─ FUN_00409cb0 (shields/drain)
              ├─ FUN_00409600 (life support)
              ├─ FUN_0040a710, FUN_004090c0, FUN_0040ba00 (others)
              └─ FUN_004182e0 (apply energy calculations)
```

---

## Expected Discoveries

By the end of Path B2, you should have:

1. ✅ Location and exact formula for 4:1 WES:RES ratio
2. ✅ Complete energy allocation algorithm
3. ✅ Crew effects on energy/regeneration
4. ✅ Phaser damage formula (linear falloff)
5. ✅ Torpedo damage formula (squared falloff)
6. ✅ Retreat/surrender decision logic
7. ✅ Personality stat struct location and fields

This will give you **complete understanding of Begin's core combat and energy systems**.

---

## Notes for Next Session

- **Have Ghidra open** — Start with begin3_project ready
- **Reference files ready** — Keep PATH-B-FINDINGS.md visible
- **Focus on FUN_004035b0 first** — It's the energy hub
- **Search systematically** — One function at a time
- **Look for constants** — 4, 0.25, energy multipliers
- **Commit frequently** — Each discovery gets a commit

---

## Remember the Pedagogical Goals

From CLAUDE.md:
1. **Explain the WHY** — Not just what code does, but why the game designed it this way
2. **One step at a time** — Fully understand one function before moving to next
3. **Check understanding** — Verify reasoning at each step
4. **Best practices** — Clear naming, documentation, regular commits

---

**You're ready for Path B2. Let's reverse engineer the game mechanics!** 🚀
