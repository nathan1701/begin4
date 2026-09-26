# Reverse Engineering Techniques for Begin.exe
## A Learning Guide with Reusable Tools

**Document Purpose:** Record the RE techniques and tools we've developed, so they can be reused and built upon in future sessions.

---

## Core Technique: Known Constants → Data Structure

### The Principle

When reversing a game, **use documented mechanics as anchors into the binary**:

1. Read the game manual/docs → extract numeric constants (crew counts, power values, weapon counts)
2. Search the binary for these values → they're distinctive enough to be unique markers
3. Examine surrounding data → identify struct boundaries and field layout
4. Verify with multiple examples → confirm the pattern with 2-3 different data points

**Why it works:** Game designers hardcode stats into data tables. These stats are mathematically distinctive (e.g., "crew: 450" is unlikely to appear by accident).

---

## Implementation: The `binary_tools.py` Module

Located at: `re_analysis/binary_tools.py`

### Functions

#### `dump_ship_entry(binary_path, file_offset, size=256)`
Dump a ship struct from the binary as 32-bit little-endian values with type inference.

```python
from binary_tools import dump_ship_entry, print_dump

dump = dump_ship_entry('/path/to/Begin.exe', 0x88590, size=256)
print_dump(dump, header="Heavy Cruiser Entry")
```

**Output:** Address, hex bytes, type (INT/FLOAT/PTR/ZERO), and interpretation

---

#### `compare_ship_entries(binary_path, ships)`
Compare multiple ship entries side-by-side to verify struct layout consistency.

```python
from binary_tools import compare_ship_entries

ships = [
    ("Heavy Cruiser", 0x0008858c),
    ("Destroyer", 0x000843bc),
    ("Frigate", 0x00081234),  # example offset
]
compare_ship_entries('/path/to/Begin.exe', ships)
```

**Output:** Table showing all ships' values at each offset. Same offsets = consistent struct.

---

#### `find_value_in_binary(binary_path, value, show_context=True)`
Search the binary for a specific integer value (useful for locating unknown ships or constants).

```python
from binary_tools import find_value_in_binary

matches = find_value_in_binary('/path/to/Begin.exe', 175)  # Frigate crew
```

---

## Workflow: Analyzing a New Ship

### Step 1: Gather Stats from Manual
Collect numeric constants:
- CREW count (most distinctive)
- Number of reactors, shields, weapons
- Power values, charge amounts

### Step 2: Locate Ship in Binary
If you know the pointer location (from Ghidra string search), use `dump_ship_entry()`.  
Otherwise, use `find_value_in_binary()` to search for the crew count.

### Step 3: Extract and Verify
Dump the entry with `dump_ship_entry()` and cross-reference known values against the manual.

### Step 4: Compare Against Known Ships
Use `compare_ship_entries()` to verify:
- Offsets are consistent across ships
- Values differ per ship, but positions match

---

## Current Findings: Ship Struct Layout

**Confirmed struct offsets (verified across HC, Destroyer, others):**

```
+0x00-0x10:  5 pointers (string descriptions)
+0x14:       INT - Crew count
+0x18:       INT - DWT (Dead Weight Tonnage, in units of ~10)
+0x1C-0x3C:  FLOATs - Power capacities, efficiencies
+0x40:       INT - Number of reactors
+0x50:       INT - Torpedo load time
+0x54:       INT - Shield power per unit
+0x58:       INT - Phaser/torpedo charge buildup
+0x5C:       INT - Shield regeneration power
+0x60:       INT - Probe capacity

+0x70+:      Repeating SUBSYSTEM BLOCKS
             (shields, phasers, torpedos, probes, warp drives, etc.)
```

---

## Known Discrepancies: Manual vs. Binary

**Destroyer Crew:**
- Manual: 200
- Binary: 250
- **Conclusion:** The manual is outdated; the binary is the source of truth.

**DWT Units:**
- Manual: 190,000 kilotons (HC), 85,000 kilotons (Destroyer)
- Binary: 20,000 (HC), 8,500 (Destroyer)
- **Hypothesis:** Binary stores DWT in units of ~10 (or similar scale factor)

---

## Next RE Targets

Using this same technique:

1. **Map subsystem block structure** — dump all the shields/phasers/torpedo blocks to understand their layout
2. **Find code that reads this struct** — use Ghidra to locate functions accessing these offsets
3. **Locate personality/AI struct** — search for bravery, aggression, loyalty values
4. **Reverse combat calculations** — find code for damage falloff (linear vs. squared distance)
5. **Game loop structure** — locate the 10-subcycle-per-cycle loop and resource allocation code

---

## Tools & Commands

### Run a quick comparison (shell):
```bash
cd /home/nathan/claude/begin4/re_analysis
python3 binary_tools.py /home/nathan/claude/begin4/original_game/Begin.exe 0x88590
```

### Import in Python scripts:
```python
import sys
sys.path.insert(0, '/home/nathan/claude/begin4/re_analysis')
from binary_tools import dump_ship_entry, compare_ship_entries

# ... use functions ...
```

---

## Learning Takeaways

✅ **Patience + structure** — Break down binary analysis into small, verifiable steps  
✅ **Reusability** — Write tools once, use them many times  
✅ **Cross-check everything** — Compare multiple examples to confirm patterns  
✅ **Trust the code** — The binary is more reliable than outdated documentation  

---

## References

- [Ship Struct Analysis](ship-struct-analysis.md) — Detailed struct mapping
- [Manual Findings](begin-manual-findings.md) — Game mechanics extracted from manual
- [Ghidra Notes](ghidra-notes.md) — Ghidra discoveries and symbol locations

