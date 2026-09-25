# original_game

Contains the original `Begin` game binaries and documentation, used as reference
material for reverse engineering. **These files are not committed to Git** — they
are copyrighted third-party binaries, kept local-only (see `.gitignore`).

## Inventory (local machine only)

- `Begin.exe` — Begin 3.0.1 (build 151), Windows port. Copyright Tom Nelson
  (1984-2010) and Mike Higgins (1984-1996). Per its own version string, this is
  "a quick port to Windows of the DOS version of Begin" — i.e. a port of Begin 2.
- `Skin/` — UI/graphics assets used by the Begin 3 Windows client.
- `begin2/BEGIN2.EXE` — Begin 2, the original DOS version.
- `begin2/BEGIN.MAN` — Begin 2's manual/documentation.
- `begin2/WHATS.NEW` — Begin 2's changelog (documents commands/mechanics added
  going from Begin 1 to Begin 2 — useful as a command-syntax reference).

Begin 2 is kept alongside Begin 3 because some mechanics/commands are reportedly
broken in Begin 2 relative to other versions — cross-referencing both helps
distinguish real game logic from version-specific bugs during reverse engineering.
