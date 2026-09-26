> **Outcome note (added Path B4, 2026-09-26):** The "4:1 WES:RES ratio" goal mentioned below is
> now resolved — see `re_analysis/ENERGY_SYSTEM_MAP.md`. Short version: no single hardcoded
> ratio exists; the code has two separate subsystem-specific 4x rules (Drive, Shield), and
> weapon energy draw (the actual "WES" side) is still untraced.

# Path B Handoff: Code Analysis Phase
## Reverse Engineer Begin.exe Game Logic

**Status:** Ready to start code tracing  
**Date:** 2026-09-25 (after struct mapping complete)  
**Next Session Focus:** Find and reverse the code that uses the ship stats struct

---

## Quick Summary: What We Know

### Ship Struct is Fully Mapped ✅

**Location:** File offset `0x0008858c` (Heavy Cruiser entry, ~1872 bytes per ship class)

**Key field offsets (all ships):**
```
+0x14 = INT: Crew count
+0x18 = INT: DWT (Dead Weight Tonnage)
+0x54 = INT: Number of reactors
+0x64 = INT: Torpedo load time
+0x68 = INT: Shield power per unit
+0x6c = INT: Phaser/torpedo charge buildup
+0x8c = INT: Number of shield generators
+0xc4 = INT: Number of phaser banks
```

**All 7 ships located in binary:**
| Ship | File Offset | Crew (Binary) | Crew (Manual) |
|------|-------------|---|---|
| Dreadnought Killer | 0x00080fdc | ? | — |
| Destroyer | 0x000843bc | 250 | 200 |
| Dreadnought v1 | 0x000860fc | 750 | 500 |
| Dreadnought v2 | 0x00087344 | 500 | 500 |
| Frigate | 0x00087a94 | 175 | 175 |
| Battle Cruiser | 0x00087e3c | 350 | — |
| Heavy Cruiser | 0x0008858c | 450 | 450 |

---

## Path B Goals (In Priority Order)

### 1. Find Code That Reads Ship Stats ⭐ START HERE
**Objective:** Locate functions that access the ship struct fields

**Approach:**
- Use Ghidra to search for xrefs to the ship table region (0x088000-0x088fff)
- Look for functions that use hardcoded offsets like `0x14`, `0x54`, `0xc4`
- Functions that read crew/reactors/weapons will be in the game loop or ship AI code

**Tools:**
- GhidraMCP: `get_xrefs_to(0x0008858c)` — who references the HC entry?
- Search for functions accessing known offsets: crew at +0x14, reactors at +0x54
- Use Ghidra's "Search → For Scalars" to find references to offset values

**Success criteria:**
- Found at least 1 function that reads crew count
- Found at least 1 function that reads reactor count
- Can trace back to a larger function (probably the game loop or ship AI logic)

---

### 2. Reverse the Energy/Power System
**Objective:** Understand how crew, reactors, weapons are allocated per cycle

**From manual (begin-manual-findings.md):**
- WES (Weapon Energy System) → RES (Reactor Energy System) at 4:1 ratio
- Energy allocation order: Weapons → Life Support → Shields
- Shields regenerate at X% per cycle

**To find:**
- Where is the 4:1 WES:RES ratio hardcoded?
- What code enforces the allocation priority?
- How do shields regenerate?

---

### 3. Reverse Combat Damage Calculation
**Objective:** Find the damage formulas (linear vs. squared distance falloff)

**From manual:**
- Phaser damage: **falls off linearly with range** (best discriminator!)
- Torpedo/probe/antimatter damage: **falls off with SQUARE of distance**

**To find:**
- Phaser damage function: `damage = max_damage - (distance * decay_factor)`
- Torpedo damage function: `damage = max_damage - ((distance ^ 2) * decay_factor)`
- Search for distance calculations and division operations

---

### 4. Locate Personality/AI Struct
**Objective:** Find where bravery, loyalty, aggression, fanaticism values are stored

**From manual:**
- Retreat formula: `if damage_sustained >= captain_bravery: retreat()`
- Fanaticism overrides retreat (suicide run)
- Loyalty affects fleet behavior

**To find:**
- Search for comparison operations with these thresholds
- Look for the retreat decision code
- Find where personality values are initialized per captain/nation

---

### 5. Map the Game Loop
**Objective:** Understand the cycle/sub-cycle structure (10 sub-cycles per cycle)

**From manual:**
- Each cycle has 10 sub-cycles
- Sub-cycle events: movement, fuse checks, targeting, helm adjustments

**To find:**
- Main game loop counter (cycles and sub-cycles)
- Event dispatch system (what happens at each sub-cycle)
- Resource regeneration (shields, crew repair, etc.)

---

## Tools & Files Ready to Use

### Ghidra
- **Location:** `~/tools/ghidra_12.1.4_PUBLIC/ghidraRun`
- **Project:** `re_analysis/begin4-ghidra/begin3_project`
- **MCP Server:** Running on `127.0.0.1:8080`
- **Status:** Ready for querying functions, xrefs, decompilation

### Python Tools
- **Location:** `re_analysis/binary_tools.py`
- **Functions available:**
  - `dump_ship_entry(binary_path, file_offset, size)` — dump hex + interpret values
  - `compare_ship_entries(binary_path, ships)` — side-by-side comparison
  - `find_value_in_binary(binary_path, value)` — search for integer values

### Reference Documentation
- `re_analysis/ship-struct-analysis.md` — detailed struct mapping
- `re_analysis/all-ships-binary-vs-manual.md` — all ships with crew/reactor/weapon counts
- `re_analysis/all-ships-from-manual.md` — complete manual specs (Appendix C)
- `re_analysis/begin-manual-findings.md` — game mechanics extracted from manual
- `re_analysis/RE-TECHNIQUES.md` — methodology and workflow

### External Reference
- `https://hallert.net/misc/begin/empiresandships.html` — ship specs from community docs
- Use to verify expected crew counts, reactor counts (may differ from binary due to version differences)

---

## How to Start Path B (Next Session)

### Step 1: Fire up Ghidra
```bash
cd /home/nathan/claude/begin4
~/tools/ghidra_12.1.4_PUBLIC/ghidraRun &
# Opens the Ghidra project at: re_analysis/begin4-ghidra/begin3_project
```

### Step 2: Load GhidraMCP Tools
When you start the new chat, the GhidraMCP server should auto-load.
Test it with:
```python
# In Claude's next chat, I'll query Ghidra directly
decompile_function_by_address("0x00418660")  # Test: the helm state function
```

### Step 3: Start Code Tracing
**First query:** Find all xrefs to the ship table
```python
get_xrefs_to(0x0008858c)  # Heavy Cruiser entry
get_xrefs_to(0x000843bc)  # Destroyer entry
```

**Second query:** Search for functions using offset 0x14 (crew field)
- Likely pattern: `mov eax, [ebx + 0x14]` or similar
- Look for functions that read multiple offsets from the same base register

### Step 4: Follow the xref chain
Each function that reads ship stats will:
1. Be called FROM another function
2. Return values that are used BY yet another function
3. Eventually trace back to main game logic

Follow the chain upward to find:
- The ship AI decision logic
- The energy allocation system
- The game cycle loop

---

## Key Addresses to Remember

**Ship Table Region:**
```
0x080fdc - Dreadnought Killer (start)
0x0843bc - Destroyer (start)
0x088588 - Heavy Cruiser (start)
0x88590  - Heavy Cruiser crew field (+0x14)
0x885e0  - Heavy Cruiser reactors field (+0x54)
0x885f4  - Heavy Cruiser shield power field (+0x68)
```

**Previous discoveries:**
```
0x004649b4 - "Heavy Cruiser" string
0x004649b0 - "Destroyer" string  (actually pointer, but nearby)
0x0048f044 - Helm mode state table (Manual/Pursuing/Eluding)
0x00418660 - FUN_00418660 (reads helm state, from Session 1)
```

---

## Expected Discoveries (Next Steps)

By the end of Path B, you should have:

1. ✅ List of functions that read crew, reactors, weapons
2. ✅ The energy allocation algorithm (WES:RES ratio, priority order)
3. ✅ Combat damage formulas (linear for phasers, squared for torpedos)
4. ✅ Personality/AI struct location and fields
5. ✅ Main game loop structure (cycle/sub-cycle dispatch)
6. ✅ Rough function call graph showing dependencies

This will give you a **complete understanding of Begin's core game mechanics** — enough to either:
- Document the engine for historical preservation
- Implement the same mechanics in Begin 4 (the modernized rebuild)
- Mod or debug the original game

---

## Notes for Next Session

- **Ghidra will be running** — start the chat with Ghidra already open
- **Have the reference files open** — `all-ships-binary-vs-manual.md`, `ship-struct-analysis.md`
- **Use GhidraMCP for all queries** — no need to take screenshots or manually navigate
- **Stay systematic** — follow one xref chain at a time, don't jump around
- **Commit frequently** — each major discovery gets a commit to `re_analysis/`

---

## Remember the Teaching Goals

From CLAUDE.md:
1. **One step at a time** — map ONE function, understand it fully, then move to the next
2. **Explain the WHY** — not just what the code does, but why the game designed it this way
3. **Check for understanding** — pause and verify before proceeding
4. **Best practices** — commit findings, use clear naming, document discoveries

---

**You're ready for Path B. See you in the next chat!** 🚀

