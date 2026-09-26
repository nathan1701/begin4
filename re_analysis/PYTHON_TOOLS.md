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
**Status:** ✅ Active (created in Path B2)  
**Size:** 6.0K  
**Purpose:** Energy system-specific analysis (WES:RES ratio, power constants)

**Functions:**
- `analyze_pe_header(binary_path)` - Read PE header to get image base and section info
- `va_to_file_offset(va, binary_path)` - Convert Ghidra Virtual Address to file offset
- `read_constant_at_address(binary_path, va, size=8)` - Read raw bytes at virtual address
- `interpret_as_double(data)` - Parse 8 bytes as IEEE 754 double
- `interpret_as_float(data)` - Parse 4 bytes as IEEE 754 float
- `interpret_as_int32(data)` - Parse 4 bytes as 32-bit signed int
- `search_energy_constants(binary_path)` - Find WES:RES constant at 0x00464688
- `analyze_wes_res_ratio(binary_path)` - Full energy system analysis with interpretations

**Usage Example:**
```python
from energy_system_analysis import analyze_wes_res_ratio
import json

analysis = analyze_wes_res_ratio('/path/to/Begin.exe')
print(json.dumps(analysis, indent=2))
```

**When to Use:**
- Verifying the 4:1 WES:RES ratio constant (0x00464688)
- Converting Ghidra addresses to file offsets for reading binary data
- Parsing floating-point constants from the binary
- Understanding energy allocation system

**Critical Constants:**
- `0x00464688` - WES:RES ratio multiplier (value: 4.0)

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
| B2 | Energy system | `energy_system_analysis.py` | Found 4:1 WES:RES ratio constant |
| B3 | Deep dive | (in progress) | Verify constant, trace usage |
| B4+ | Future | TBD | Weapon structs, ship configs, etc. |

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

**Last Updated:** 2026-09-26  
**Maintained By:** Claude (AI Assistant)  
**For:** Begin 4 Project
