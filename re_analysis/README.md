# re_analysis

Notes, Ghidra project files, memory maps, and extracted logic from reverse-engineering
`Begin.exe` (Begin 3). See the top-level `CLAUDE.md` for the project's mission and pedagogical
ground rules.

## Start here

- **[`NEXT_SESSION_PROMPT.txt`](NEXT_SESSION_PROMPT.txt)** — what to work on next (currently Path B5)
- **[`ENERGY_SYSTEM_MAP.md`](ENERGY_SYSTEM_MAP.md)** — current, corrected picture of the energy
  system (constants, structures, confirmed mechanisms, open questions). Read this before any
  other energy-related doc in this folder.
- **[`PYTHON_TOOLS.md`](PYTHON_TOOLS.md)** — manifest of reusable analysis scripts; check before
  writing new Python code

## Document status

Several energy-system docs below are **historical** — kept for the record of how the
investigation unfolded, but superseded by `ENERGY_SYSTEM_MAP.md` for actual facts:

| Doc | Status |
|---|---|
| `ENERGY_SYSTEM_MAP.md` | ✅ Current — the corrected energy-system reference |
| `PATH_B3_FINDINGS.md` | ⚠️ Superseded — early hypothesis, later corrected |
| `PATH_B3_HANDOFF.md` | ⚠️ Historical — planning doc, checklist now complete |
| `B3_PROGRESS.txt` | ⚠️ Historical — phase tracker, all phases now complete |
| `ship-struct-analysis.md` | ✅ Current — but describes a **different** structure (the static per-ship-class data table), not the runtime object or display struct in `ENERGY_SYSTEM_MAP.md` |
| `all-ships-from-manual.md`, `all-ships-binary-vs-manual.md` | ✅ Current — ship stat cross-references |
| `begin-manual-findings.md` | ✅ Current — paraphrased manual notes (mechanics, formulas) |
| `RE-TECHNIQUES.md` | ✅ Current — general RE methodology notes |

## Tools

- `binary_tools.py` — general binary analysis (struct dumping, integer search)
- `energy_system_analysis.py` — energy-specific analysis (PE header parsing, VA→file-offset,
  constant catalogue, double-value search)

Both are documented in `PYTHON_TOOLS.md`; check there before writing a new script, per
`CLAUDE.md`'s "reuse and improve" rule.

## Ghidra project

Located at `begin4-ghidra/begin3_project.gpr` (gitignored — binary/machine-specific). Analyzes
`../original_game/Begin.exe`. A live Ghidra MCP connection (tools named `mcp__ghidra__*`) is
what made the Path B4 findings possible — direct decompilation, disassembly, and cross-reference
queries instead of manual byte-searching.
