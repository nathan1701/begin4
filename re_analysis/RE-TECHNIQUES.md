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

dump = dump_ship_entry('/path/to/Begin.exe', 0x88588, size=256)  # corrected offset, see below
print_dump(dump, header="Heavy Cruiser Entry")
```

**Output:** Address, hex bytes, type (INT/FLOAT/PTR/ZERO), and interpretation

---

#### `compare_ship_entries(binary_path, ships)`
Compare multiple ship entries side-by-side to verify struct layout consistency.

```python
from binary_tools import compare_ship_entries

ships = [
    ("Heavy Cruiser", 0x00088588),
    ("Destroyer", 0x000843b8),
    ("Frigate", 0x00087a90),
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

**CORRECTED 2026-09-26 (class-data mapping session) — the offsets below were off by 4 bytes for
every ship class. See `ENERGY_SYSTEM_MAP.md` §3.9 for the full story, including a live memory read
that caught it. This is itself a case study for the "known constants → data structure" technique's
main weakness: two 4-byte-int fields (crew, DWT) matched their manual values even under the WRONG
base address, because the search alone can't tell you *which* nearby field it actually landed on —
see "Core Technique 2" below for the fix.**

**Confirmed struct offsets (corrected; verified across HC, Destroyer, Frigate):**

```
+0x00:       Unidentified, 0 for Heavy Cruiser (NOT a vtable pointer)
+0x04-0x14:  5 pointers (string descriptions) - the last two are a ship-name pool and a
             commanding-officer-surname pool, respectively (ENERGY_SYSTEM_MAP.md §3.6/§3.9)
+0x18:       INT - Crew count (code-confirmed AND live-memory-confirmed)
+0x1C:       INT - DWT (Dead Weight Tonnage, in units of ~10)
+0x20-0x40:  FLOATs/DOUBLEs - Power capacities, efficiencies (still mostly unverified - see
             ship-struct-analysis.md TODO item 7)
+0x58:       TypeRecord pointer for Reactor's subsystem array (code-confirmed via disassembly -
             NOT the same thing as the "+0x40 reactor count" guess this table used to have here;
             see ENERGY_SYSTEM_MAP.md §3.8 for the full 13-subsystem TypeRecord table, which
             starts here and runs to +0x380)

+0x618ish+:  A separate, NOT code-verified, set of repeating SUBSYSTEM BLOCKS found by the same
             number-search technique (shields, phasers, torpedos, probes, warp drives, etc.) - may
             or may not be the same table as the +0x58..+0x380 TypeRecords; not confirmed either way
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

## Core Technique 2: Live Memory Verification via `/proc/<pid>/mem`

### The Principle

Static analysis (Ghidra + raw file reads) can produce two equally plausible readings of the same
data that disagree with each other, with no way to tell which is right from the file alone — this
happened in the class-data mapping session (2026-09-26), where a heuristic file-offset table and a
disassembly-confirmed code offset disagreed by exactly 4 bytes, and *both* looked locally plausible
(see `ENERGY_SYSTEM_MAP.md` §3.9). When that happens, reading the **actual live memory** of the
running game settles it in one data point, because there's no ambiguity left — it's the address the
game itself is really using, not a guess about where the game's data table starts in the file.

**Why this doesn't need Cheat Engine or a Windows VM:** the game runs under Wine as an ordinary
Linux process, so its memory is readable the same way any Linux process's memory is — through
`/proc/<pid>/mem` — as long as you already know *which* addresses you want (no GUI memory-scanning
needed, since Ghidra already tells you the addresses in the binary's own address space, and Wine
loads old 32-bit PE binaries like this one at their preferred base unmodified).

### Step-by-step

1. **Find the process.** `ps aux | grep -i <exe name>` (or `grep -i wine`). Note the PID.
2. **Confirm you're reading the right binary**, especially if multiple copies of the file exist on
   disk (e.g. a Downloads copy vs. a project copy) — `md5sum` both and confirm they match before
   trusting that Ghidra's addresses apply to the running process.
3. **Confirm the module's load address matches Ghidra's assumed base**, so no address translation
   is needed: `cat /proc/<pid>/maps | grep -i <exe name>` — for this binary, Ghidra assumes
   `0x00400000`, and Wine loaded it there unmodified (no ASLR rebasing for this old 32-bit PE). If
   the base differs, every Ghidra VA needs `actual_base - 0x00400000` added before use.
4. **Read memory.** Same-user access alone isn't enough by default (`ptrace_scope=1` restricts
   `/proc/<pid>/mem` reads to the process's own parent or root) — so this needs `sudo`, run by the
   developer directly in their own terminal (never by having an AI assistant run `sudo` on your
   behalf, and never by weakening `ptrace_scope` itself — that's a real system security setting).
   A short Python script does the read: open `/proc/<pid>/mem`, `seek()` to the address, `read()`
   the bytes, `struct.unpack()` them. See `read_live_classdata.py` for a working example that reads
   a ship pointer out of a known global, follows it to `class_data`, and dumps a few fields.
5. **Compare against the static file reading.** Any disagreement tells you exactly which static
   assumption was wrong (and often, as with the off-by-4 bug, exactly *how* it was wrong).

### When to reach for this

- A code-confirmed offset (from disassembly) and a heuristic/file-search-based offset disagree.
- A value read from the static file looks impossible (e.g. a count of `0` for something every
  instance must have at least one of).
- You want to confirm a *runtime-only* value that never appears as a fixed constant in the static
  `.exe` at all (e.g. `ship+0xe4`'s class_data pointer, which is written by runtime ship-selection
  code — see `ENERGY_SYSTEM_MAP.md` §3.6).

---

## Next RE Targets

Using these techniques:

1. **Combat damage formulas** (active target, see `NEXT_SESSION_PROMPT.txt`) — decode more of the
   13 confirmed TypeRecord fields (`ENERGY_SYSTEM_MAP.md` §3.8), cross-checking against the manual
   the same way Bank/Drive/Shield were decoded, and reach for a live memory read if anything looks
   off rather than guessing.
2. **Locate personality/AI struct** — search for bravery, aggression, loyalty values
3. **Game loop structure** — locate the 10-subcycle-per-cycle loop and resource allocation code
4. **`class_data+0x00`/`+0xC`** — still unidentified, low priority (see `ship-struct-analysis.md`)

---

## Tools & Commands

### Run a quick comparison (shell):
```bash
cd /home/nathan/claude/begin4/re_analysis
python3 binary_tools.py /home/nathan/claude/begin4/original_game/Begin.exe 0x88588
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
- [Energy System Map](ENERGY_SYSTEM_MAP.md) — Symbol names, function locations, and the
  off-by-4 bug / live-memory-verification case study (§3.9) this doc's "Core Technique 2" is based on

