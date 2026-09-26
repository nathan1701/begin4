# Python Tools Manifest

**Purpose:** Index of all working Python analysis scripts created for Begin 4 reverse engineering. This prevents duplicating code across sessions and builds a reusable toolkit.

**Location:** `/home/nathan/claude/begin4/re_analysis/`

**Rule:** Before writing new Python code, check this list. If a similar tool exists, use or improve it rather than rewriting.

---

## 📋 Available Scripts

### 1. `binary_tools.py` 
**Status:** ✅ Active (created in earlier session, extended in the class-data mapping session)  
**Size:** 5.0K  
**Purpose:** General binary file analysis utilities

**Functions:**
- `dump_ship_entry(binary_path, file_offset, size=256)` - Extract and parse 32-bit values from binary at given offset
- `print_dump(entries, header="")` - Pretty-print binary dumps with type inference
- `compare_ship_entries(binary_path, ships)` - Compare multiple ship data structures side-by-side
- `find_value_in_binary(binary_path, value, show_context=True)` - Search for 32-bit integer values in binary
- `dump_doubles(binary_path, file_offset, count=8)` - **New in the class-data mapping session.**
  Reads a run of consecutive 8-byte IEEE 754 doubles — `dump_ship_entry` only interprets 4-byte
  ints/floats, but the class-data TypeRecord fields (reactor rate, charge rate, capacity) turned
  out to be doubles.
- `print_doubles(entries, header="")` - Pretty-print a `dump_doubles()` result.

**Also in this directory:** `read_live_classdata.py` (new in the class-data mapping session,
extended in `COMBAT_DAMAGE`, extended again in `TORPEDO_DAMAGE`, **extended again in
`TORPEDO_IMPACT`**) - a one-off diagnostic (not part of the general toolkit, kept for reference)
that reads a running Begin.exe's live `class_data` struct via `/proc/<pid>/mem`, needed to catch and
confirm the off-by-4 file-offset bug described below. `COMBAT_DAMAGE` added reads for
`class_data+0x380/+0x390/+0x3a0` and the live ship's own `+0x110`, used to confirm Begin 3 has no
accumulating hull-HP pool (see `COMBAT_DAMAGE_MAP.md` §0). `TORPEDO_DAMAGE` added a `--watch
[duration]` mode (`watch_tubes()`) that polls `ship+0x454`'s Tube array repeatedly under one `sudo`
prompt, printing only tubes whose fields changed since the last poll — needed because a single
before/after snapshot completely missed the transient `ready(+0x30)` flag, and a real live play
session is long enough that repeated `sudo` prompts would otherwise be disruptive. Also hardened
against the ship pointer going stale mid-watch (battle ending, ship destroyed) after this happened
for real and crashed an earlier version — see `TORPEDO_DAMAGE_MAP.md` §2.5.

`TORPEDO_IMPACT` added a `--watch-combat [duration]` mode (`watch_combat()`/`_snapshot_combat()`)
that polls a ship's hit-counters (`+0x134`/`+0x128`/`+0x12C`) and the Shield array (`ship+0x7f8`)'s
per-unit hits/charge%/integrity, used to live-confirm torpedo damage applies immediately rather than
being deferred a turn (see `TORPEDO_IMPACT_MAP.md` §3). Building it surfaced two real bugs, both
fixed and both worth remembering: (1) a wrong container-layout assumption — copy-pasted Tube's
"pointer to a packed array of unit pointers" shape onto Shield without checking, when Shield's array
is actually embedded in-place with no pointer indirection; caught by an `OSError` reading through
the resulting garbage pointer, fixed by decompiling the real facing-selection function instead of
assuming uniformity across subsystems (`TORPEDO_IMPACT_MAP.md` §7); (2) the watch loops' per-poll
ship-pointer re-read used a bare `read_mem()` that raised `FileNotFoundError` if the whole game
*process* exited (not just the ship pointer going stale) — fixed with a new `read_mem_or_none()`
helper, applied to both `watch_tubes()` and `watch_combat()`. Usage: `sudo python3
read_live_classdata.py <PID>` for a single snapshot (now including the Tube array), `sudo python3
read_live_classdata.py <PID> --watch [duration_seconds]`, or `sudo python3 read_live_classdata.py
<PID> --watch-combat [duration_seconds]` (all need root because of `ptrace_scope=1` — same-user
access alone isn't enough to read another process's memory).

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
- `file_offset_to_va(file_offset, binary_path)` - **New in Path B5.** Inverse of `va_to_file_offset()` — turns a raw file offset (e.g. a hit from `binary_tools.find_value_in_binary()`) back into a Ghidra-normalized VA. Needed when hand-verifying whether a string/constant is really referenced by code Ghidra hasn't analyzed — see the Path B5 workflow note below.
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
- Converting Ghidra addresses to file offsets for reading binary data (and back, with `file_offset_to_va`)
- Parsing floating-point constants from the binary
- Cross-checking whether a suspected constant appears anywhere Ghidra's xref list missed
- **Path B5 workflow:** when Ghidra's `get_xrefs_to` returns nothing for a string/constant, don't
  assume it's an indexed table — it might mean Ghidra never analyzed the referencing code as a
  function at all (this happened for `"Charging %d bank%s!\n"` and its containing function,
  `0x00412bb0`/`0x00408b80` — both real code, neither in Ghidra's function database). Workflow:
  `binary_tools.find_value_in_binary(binary, target_va)` to find the raw pointer's file offset,
  `file_offset_to_va(offset, binary)` to see where the reference itself lives, then dump raw bytes
  around that VA with `binary_tools.dump_ship_entry()` (or a plain contiguous hex dump — see this
  session's transcript) and hand-disassemble. Once you find a function's real start (look for a
  repeated `sub esp, N` prologue after `cc cc` padding), check `get_function_by_address` /
  `decompile_function_by_address` again — if Ghidra still says "no function found," it has to be
  decoded by hand.
- **Path B6 workflow:** when a suspected constant turns out to have zero direct xrefs *and* isn't
  a missing-function case (the code reading it really is indexed/computed addressing), dump a wide
  contiguous range of raw doubles around it with `struct.unpack('<d', ...)` in a loop (see this
  session's transcript) rather than guessing at neighbors one at a time. This is how the second
  `4.0` at `0x00478798` turned out to be one row of a 257-row `atan()` lookup table (step size
  `1/32` from `0` to `8`) — a pattern only visible once ~30+ consecutive rows were dumped and
  compared against `math.atan()` in Python.

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

**Naming convention change (decided 2026-09-26):** the `B1`-`B7` letter/number scheme is retired
going forward. It broke down once work stopped being one single linear investigation ("energy
system") — this session didn't fit any of `NEXT_SESSION_PROMPT.txt`'s own lettered options (A-F),
and needed an ad hoc label ("class-data mapping session") instead. From here on, sessions are
named with a short descriptive slug (e.g. `COMBAT_DAMAGE`, `TRANSPORTER_BUG`), optionally with a
date prefix if a session's focus might shift partway through and the topic label alone wouldn't
capture it. Existing `B1`-`B7` labels in this table and elsewhere are left as-is — not renamed
retroactively.

| Path / Session | Session | Scripts Created | Purpose |
|------|---------|-----------------|---------|
| B1 | Initial exploration | — | Binary strings, function discovery |
| B2 | Energy system | `energy_system_analysis.py` | Hypothesized a 4:1 WES:RES ratio constant (later corrected) |
| B3 | Deep dive | — | Verified the constant, found it was 100.0 not 4.0; found real 4.0 elsewhere |
| B4 | Energy system, complete | `energy_system_analysis.py` (bug-fixed + extended) | Fixed VA→offset bug; mapped Drive & Shield's real 4x mechanisms; corrected 3 mis-identified display fields; wrote `ENERGY_SYSTEM_MAP.md` |
| B5 | Weapon power draw + `FUN_0040b510` | `energy_system_analysis.py` (added `file_offset_to_va`) | Traced Bank's real energy function (no 4.0, no ratio — closes the WES:RES question for good); identified `FUN_0040b510` as an unrelated malfunction/event system; hand-disassembled 2 functions Ghidra never analyzed |
| B6 | Name remaining subsystem slots, resolve 2nd 4.0 | none new | Named all 13 runtime subsystem slots via `FUN_004035b0`'s per-slot noun strings; corrected 2 mis-identified slots (`0xb88`/`0xc20`); resolved `0x00478798` as a row of an `atan()` lookup table |
| B7 | Reactor-rate chase unification, `ship+0xe8`/`0xec`/`0xf0` | none new (used existing `va_to_file_offset`/`file_offset_to_va`) | Found `unit+0x30`(Drive)/`+0x34`(Shield) are array-container back-pointers, not ship back-pointers — same shape as Bank/Tube's `+0x20`; unified all three into one "unit → array → fixed class-data pointer → static double" mechanism; found `ship+0xe8` is a shuffled commanding-officer-name pointer, not "crew count"; found a likely genuine construction-time bug in `FUN_00418080`; confirmed `ship+0xf0` is an int (DWT-copy) with no per-frame writer found. Full writeup: `ENERGY_SYSTEM_MAP.md` §3.6/§3.7/§7. |
| `CLASS_DATA_MAPPING` (2026-09-26) | Full class_data TypeRecord table + off-by-4 fix | `binary_tools.py` (added `dump_doubles`/`print_doubles`), `read_live_classdata.py` (new) | Traced all 13 subsystem `ConstructArray` functions to find the complete TypeRecord offset table in `class_data` (§3.8); found and fixed a session-crossing off-by-4 bug in `ship-struct-analysis.md`'s static file offsets via a live `/proc/<pid>/mem` read of the running game, which reversed two of Path B7's headline findings (`ship+0xe8` is a ship name not a surname; `ship+0xec`'s field is a legitimate surname pointer, not a bug) and corrected `ship+0xf0`/`FUN_004035b0`'s ratio from "power-to-weight" to crew-based (§3.9). Done as a prerequisite to combat-damage work. First session named under the new descriptive-naming convention (see note above the table). |
| `COMBAT_DAMAGE` (2026-09-26) | Phaser/Bank weapon-fire → hit → shield-absorb → hull/destruction chain, fully traced | `read_live_classdata.py` (extended, not rewritten — added reads for `class_data+0x380/+0x390/+0x3a0` and live `ship+0x110`) | Traced the entire phaser fire chain (`FUN_00403330`→`FUN_00408fa0`→`FUN_00408cf0`) including the damage formula (linear range falloff, no `4.0` despite decompiler pseudocode claiming otherwise — see `COMBAT_DAMAGE_MAP.md` §5), fully decoded shield absorption (directional facings, per-class capacity/efficiency from the TypeRecord table, a shield-bypassing "weapon type 1"), found and confirmed `Ship::vftable+0x34` = `FUN_00404d90` (damage application), and — via a live memory read — **overturned Begin 3 having any accumulating hull-HP pool**: every hull-penetrating hit is independently checked against a flat per-class destruction threshold. This closed `ENERGY_SYSTEM_MAP.md` §7 items 7 and 10 for good. Full writeup: `COMBAT_DAMAGE_MAP.md`. Torpedo/Tube path left for a future session. |
| `TORPEDO_DAMAGE` (2026-09-26) | Torpedo/Tube fire chain traced through launch (projectile allocation); full live-tested lock/reload/fire model | `read_live_classdata.py` (extended — added `--watch` mode / `watch_tubes()`, and hardened it against the ship pointer going stale mid-watch) | Traced Tube's fire chain (`FUN_0040c0a0`→`FUN_0040beb0`→`FUN_0040bf70`) from raw disassembly, confirming torpedoes allocate a real projectile object (`FUN_0043d97e(0x118)`) rather than Bank's instant hit-scan — genuinely different mechanics, not "a near-twin of Bank" as an earlier session's power-draw note had implied. Then, via extensive live testing across two real play sessions (including one that ended in the player's ship being destroyed mid-test), fully confirmed the tube-state model: `ready(+0x30)` is a single-instant launch flag, `target(+0x6c)` is a standing lock from `"lock all tubes X"` that auto-reacquires after each ~20-28s reload cycle, and `field_34` is NOT firing-related at all (overturning a mid-session hypothesis) — a live-testing methodology parallel to `COMBAT_DAMAGE`'s `class_data+0x380` correction. Also disproved an "auto-fire" hypothesis for torpedoes via a clean zero-input control test. Full writeup: `TORPEDO_DAMAGE_MAP.md`. Projectile flight/collision/impact still completely untraced (`TORPEDO_DAMAGE_MAP.md` §5 item 5) — the natural next session. |
| `TORPEDO_IMPACT` (2026-09-26) | Torpedo post-launch: global in-flight list, per-ship-per-turn hit resolution, live-confirmed immediate (non-deferred) damage | `read_live_classdata.py` (extended — added `--watch-combat` mode / `watch_combat()`; fixed a Shield-array container-layout bug and a process-exit crash found while building it) | Traced the projectile's self-registration into a global doubly-linked list via a virtual call through its own vtable (`Torp::vftable+0x20`→`FUN_00405980`), and the per-ship-per-turn function (`FUN_00406f10`) that walks that list rolling hit-chance/damage against each ship. That function's damage dispatch doesn't call the known `Ship::vftable+0x34` directly, which looked like deferred damage — **live testing across two real fights disproved that: damage lands the same turn as the hit, every time (6+ confirmed events)**. Also live-confirmed, unprompted: shield regen rate, multi-facing salvo hits, the lost-detection/stale-position mechanic (`COMBAT_DAMAGE_MAP.md` §3, previously only a static hypothesis), and — the session's other headline result — the derelict/crew-wipeout handler (`FUN_00403210`, previously just "presumed" in `COMBAT_DAMAGE_MAP.md` §6 item 9), matching the developer's own account of boarding and reactivating a crewless enemy ship. Full writeup: `TORPEDO_IMPACT_MAP.md`. |

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

**Last Updated:** 2026-09-26 (`TORPEDO_IMPACT` session)
**Maintained By:** Claude (AI Assistant)
**For:** Begin 4 Project
