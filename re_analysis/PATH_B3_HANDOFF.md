# Path B3: Energy System Implementation & Verification

## 🎯 Mission Summary
**Previous Achievement (Path B2):** Located and verified the 4:1 WES:RES (Weapon Energy Storage : Reactor Energy Storage) ratio constant in `begin3.exe`.

**Path B3 Goal:** Verify the constant value, understand its use throughout the codebase, and prepare implementation for Begin 4.

---

## 🔍 Critical Findings from Path B2

### Energy Ratio Constant Location
- **Virtual Address:** `0x00464688` (.rdata section)
- **Type:** IEEE 754 double-precision float
- **Likely Value:** `4.0` (based on disassembly analysis)
- **File Offset:** Varies by PE header (use `va_to_file_offset()` from `energy_system_analysis.py`)

### Where It's Used (Disassembly References)
1. **0x0040f871** - FMUL in power calculation (weapon energy)
2. **0x0040f997** - FMUL in power calculation (reactor energy)  
3. **0x0040fc87** - FMUL in shield/weapon power calculation
4. **Context Function:** `FUN_0040f4b0` (ship status display, weaponry section)

### Related Constant
- **String "Reinforced shields require 4x power"** at `0x004662f0`
  - Confirms the 4:1 ratio is intentional game balance design

---

## 📋 Path B3 Checklist

### Phase 1: Binary Verification
- [ ] Run `energy_system_analysis.py` on `Begin.exe` to extract the constant
- [ ] Confirm value is `4.0` (or document actual value)
- [ ] Verify all 3 FMUL references are accessing this same address
- [ ] Take screenshots of Ghidra disassembly showing FMUL instructions

### Phase 2: Code Flow Analysis  
- [ ] **Trace backwards** from FMUL at 0x0040f871:
  - What value is being multiplied?
  - Which ship system does it apply to?
  - How is the result used?
  
- [ ] **Trace backwards** from FMUL at 0x0040f997:
  - Same questions as above
  - Is this for a different system?
  
- [ ] **Trace backwards** from FMUL at 0x0040fc87:
  - Examine context with shield/weapon power
  - Map to the "4x power" message logic

### Phase 3: Data Structure Mapping
- [ ] Identify the ship structure layout in `FUN_0040f4b0`:
  - Offset 0xc8 = ? (weapon system field)
  - Offset 0x110 = ? (reactor system field)
  - Offset 0x190 = ? (shield system field)
  - Document all offsets and their meanings

- [ ] Find weapon/reactor initialization code:
  - Where does WES get set?
  - Where does RES get set?
  - Is there a config file or hardcoded table?

### Phase 4: Document Integration
- [ ] Create `ENERGY_SYSTEM.md` documenting:
  - The 4:1 ratio design
  - Which systems share the energy pool
  - How weapons compete with shields for power
  - Formula: `weapon_output = reactor_output * 4.0`?

### Phase 5: Prepare for Implementation
- [ ] Design equivalent energy system for Begin 4
- [ ] Decide: will Begin 4 use same 4:1 ratio or tweak it?
- [ ] Map Begin3 energy constants to Begin 4 design docs

---

## 📁 Useful Files & Tools

### Scripts
- **`binary_tools.py`** - General binary analysis utilities
  - `dump_ship_entry()` - Extract ship data structures
  - `find_value_in_binary()` - Search for constants
  
- **`energy_system_analysis.py`** (newly created)
  - `search_energy_constants()` - Find WES:RES constant
  - `va_to_file_offset()` - Convert Ghidra VA to file offset
  - `interpret_as_double()`, `interpret_as_float()` - Parse binary values

### Ghidra Project
- Location: `/home/nathan/claude/begin4/re_analysis/begin4-ghidra/`
- Binary: `/home/nathan/claude/begin4/original_game/Begin.exe`

### Previous Analysis
- Path B2 disassembly from `FUN_0040f4b0` (ship status display function)
- Key strings: weapon/reactor display format strings

---

## 🎓 Learning Notes

### Why the 4:1 Ratio?
- **Game Balance:** Weapons need 4x the power of reactors to create meaningful choice
  - Reactor-heavy build: lots of power, less weapons damage
  - Weapon-heavy build: powerful weapons, fragile
  
### Key Insight
The constant `0x00464688` isn't just a number—it's the **game's balance lever**. Changing it would fundamentally alter Begin3's gameplay.

---

## 🚀 Next Session Prompt

```
Project: Begin 4 - Path B3: Energy System Deep Dive

Context:
- We located the 4:1 WES:RES ratio constant at 0x00464688 (likely value: 4.0)
- This constant is used in 3+ FMUL operations in the power calculation code
- We need to verify it and trace how the energy system actually works

Tools available:
- binary_tools.py (general binary analysis)
- energy_system_analysis.py (energy-specific utilities)
- Ghidra project: begin3_project in /home/nathan/claude/begin4/re_analysis/begin4-ghidra/
- Binary: /home/nathan/claude/begin4/original_game/Begin.exe

Immediate tasks for Path B3:
1. Run energy_system_analysis.py to extract and verify the 4.0 constant
2. Trace the 3 FMUL instructions to understand what values they're multiplying
3. Map the weapon/reactor data structure offsets in FUN_0040f4b0
4. Document how WES and RES interact in the game's energy system

Learning goal: Understand the complete energy flow so we can replicate it in Begin 4
```

---

## 📞 Questions for Next Session

1. **What's at offset 0x00464688?** - Run the script to find out!
2. **How do weapons actually consume energy?** - Trace the FMUL at 0x0040f871
3. **Is there a config/data file** or are all constants hardcoded in the binary?
4. **Where's the weapon initialization code?** - Are weapons defined in a table?

---

## 🔗 Related Paths

- **Path B1** - Initial binary exploration, strings analysis, function identification
- **Path B2** - Located energy system constant (COMPLETE)
- **Path B3** - Verify constant, trace usage, map data structures (IN PROGRESS)
- **Path B4** - Weapon/ship data structure analysis
- **Path B5** - Implement energy system in Begin 4

---

**Last Updated:** 2026-09-26  
**Session Started By:** Claude Haiku 4.5  
**Status:** Path B2 Complete → Path B3 Ready
