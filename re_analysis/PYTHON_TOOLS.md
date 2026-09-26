# Python Tools Manifest

**Purpose:** Index of all working Python analysis scripts created for Begin 4 reverse engineering. This prevents duplicating code across sessions and builds a reusable toolkit.

**Location:** `/home/nathan/claude/begin4/re_analysis/`

**Rule:** Before writing new Python code, check this list. If a similar tool exists, use or improve it rather than rewriting.

---

## 📋 Available Scripts

### 1. `binary_tools.py` 
**Status:** ✅ Active (created in earlier session)  
**Size:** 5.0K  
**Purpose:** General binary file analysis utilities

**Functions:**
- `dump_ship_entry(binary_path, file_offset, size=256)` - Extract and parse 32-bit values from binary at given offset
- `print_dump(entries, header="")` - Pretty-print binary dumps with type inference
- `compare_ship_entries(binary_path, ships)` - Compare multiple ship data structures side-by-side
- `find_value_in_binary(binary_path, value, show_context=True)` - Search for 32-bit integer values in binary

**Usage Example:**
```python
from binary_tools import dump_ship_entry, print_dump
entries = dump_ship_entry('/path/to/Begin.exe', 0x12345)
print_dump(entries, "Ship struct")
```

**When to Use:**
- Extracting and comparing ship/weapon data structures
- Searching for numeric constants in the binary
- Dumping raw binary sections for analysis

---

### 2. `energy_system_analysis.py`
**Status:** ✅ Active (created in Path B2, bug-fixed and extended in Path B4)
**Size:** ~10K
**Purpose:** Energy system-specific analysis (constant catalogue, power formulas)

**⚠️ Path B4 bug fix:** `va_to_file_offset()` was converting VA→RVA using the PE header's own
declared `image_base` (`0x00062e00`, an oddball value for this binary), instead of the
`0x00400000` address **Ghidra actually normalizes to**. This silently broke any lookup outside
`.text` — e.g. `0x00465088`, `0x00465488`, `0x00464bd0` all raised "not found in any PE section"
even though they're valid `.rdata` addresses. Fixed with a `GHIDRA_IMAGE_BASE = 0x00400000`
constant used for the RVA conversion. **If you ever see "VA not found in any PE section" for an
address you can see in Ghidra, this is the first thing to check.**

**Functions:**
- `analyze_pe_header(binary_path)` - Read PE header to get image base and section info
- `va_to_file_offset(va, binary_path)` - Convert Ghidra Virtual Address to file offset (uses `GHIDRA_IMAGE_BASE`, not the PE header's image_base — see fix above)
- `read_constant_at_address(binary_path, va, size=8)` - Read raw bytes at virtual address
- `interpret_as_double(data)` - Parse 8 bytes as IEEE 754 double
- `interpret_as_float(data)` - Parse 4 bytes as IEEE 754 float
- `interpret_as_int32(data)` - Parse 4 bytes as 32-bit signed int
- `find_double_in_binary(binary_path, target, tolerance=1e-9, section_filter=None)` - **New in Path B4.** Scans the whole binary for 8-byte-aligned doubles matching a value; complements `binary_tools.find_value_in_binary` (which only searches 32-bit ints)
- `search_energy_constants(binary_path)` - Reads and verifies every entry in `KNOWN_CONSTANTS` against the live binary (rewritten in Path B4 — used to check only one address)
- `analyze_wes_res_ratio(binary_path)` - Full report: confirmed mechanisms, constant catalogue, open questions (name kept for backward compatibility; **there is no single WES:RES ratio** — see below)

**`KNOWN_CONSTANTS` dict (new in Path B4):** catalogues every energy-adjacent constant found so
far — value, role, confirmed call sites, and whether it's actually energy-related or a
coincidental reuse of the same literal. This is the canonical machine-readable version of
`ENERGY_SYSTEM_MAP.md` §4.

**Usage Example:**
```python
from energy_system_analysis import analyze_wes_res_ratio, find_double_in_binary
import json

analysis = analyze_wes_res_ratio('/path/to/Begin.exe')
print(json.dumps(analysis, indent=2))

# Find every 4.0 literal in .rdata (useful for checking coverage of xref-based analysis)
hits = find_double_in_binary('/path/to/Begin.exe', 4.0, section_filter='.rdata')
```

**When to Use:**
- Verifying any of the constants in `KNOWN_CONSTANTS` against the binary
- Converting Ghidra addresses to file offsets for reading binary data
- Parsing floating-point constants from the binary
- Cross-checking whether a suspected constant appears anywhere Ghidra's xref list missed

**Corrected understanding (Path B4) — full details in `ENERGY_SYSTEM_MAP.md`:**
There is **no single "4:1 WES:RES ratio" constant**. `0x00464688` = 100.0, a generic
percent-to-fraction helper used in 35+ unrelated functions. The real `4.0` (`0x00464ad8`) is
reused by the compiler for two distinct real mechanisms (Drive charge/drain rate; Shield
reinforcement power cost) plus several unrelated formulas. Weapon power draw hasn't been traced
yet — that's the open item for the next session.

---

## 📝 Script Usage Guidelines

### Before Writing New Code
1. **Check This Manifest** - Is there an existing tool for what you need?
2. **Improve, Don't Rewrite** - If a tool is close, modify it or add a new function
3. **Document Well** - Add docstrings explaining parameters, return values, and examples
4. **Test Before Committing** - Make sure your changes work with the target binary

### When to Create a New Script
- The task is fundamentally different from existing tools
- Trying to keep a single file under ~300 lines for readability
- Multiple sessions will benefit from this specialized tool

### Commit Procedure
```bash
cd /home/nathan/claude/begin4
git add re_analysis/new_tool.py
git commit -m "Add new_tool.py: Brief description of what it does"
# Update this manifest
git add re_analysis/PYTHON_TOOLS.md
git commit -m "Update PYTHON_TOOLS.md: Add new_tool.py entry"
```

---

## 🔗 Related Sessions & Paths

| Path | Session | Scripts Created | Purpose |
|------|---------|-----------------|---------|
| B1 | Initial exploration | — | Binary strings, function discovery |
| B2 | Energy system | `energy_system_analysis.py` | Hypothesized a 4:1 WES:RES ratio constant (later corrected) |
| B3 | Deep dive | — | Verified the constant, found it was 100.0 not 4.0; found real 4.0 elsewhere |
| B4 | Energy system, complete | `energy_system_analysis.py` (bug-fixed + extended) | Fixed VA→offset bug; mapped Drive & Shield's real 4x mechanisms; corrected 3 mis-identified display fields; wrote `ENERGY_SYSTEM_MAP.md` |
| B5+ | Future | TBD | Trace weapon (Bank/Tube/Launcher) power draw; identify `FUN_0040b510`; resolve second 4.0 at `0x00478798` |

---

## ✅ Checklist for Future Sessions

When starting a new session:
- [ ] Review this manifest for existing tools
- [ ] Check `/re_analysis/` for recent scripts
- [ ] Read `NEXT_SESSION_PROMPT.txt` if continuing a path
- [ ] Before writing Python code, search for similar existing functions
- [ ] After creating a working script, commit it AND update this manifest

---

## 🎓 Learning Value

Over time, this toolkit becomes a **reusable reverse-engineering library** for Begin 3's binary format. It documents:
- **How to read PE binaries** (not game-specific, useful for any Windows .exe)
- **How to parse floating-point constants** (IEEE 754 handling)
- **How to structure analysis tools** (clean separation of concerns)
- **Git workflow for tool development** (version control good practices)

Each script is a learning milestone. Keep them, improve them, learn from them.

---

**Last Updated:** 2026-09-26 (Path B4)
**Maintained By:** Claude (AI Assistant)
**For:** Begin 4 Project
