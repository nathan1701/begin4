# Begin v1.65 Manual Ship Stats - Appendix C

Extracted from the Advanced Strategy Manual, Appendix C.

## THE UNITED FEDERATION

| Class | Code | Crew | DWT (Kilotons) | Reactors | Batteries | Phasers | Torpedos | Probes | Shields | Warp | Notes |
|-------|------|------|--------|----------|-----------|---------|----------|--------|---------|------|-------|
| Interceptor | IR | 155 | 70,000 | 6 | 6 @ 60eu | 6 @ 2000 range | 2 | 1 | 6 @ 150eu | 2 @ 150eu | - |
| Destroyer | DE | 200 | 85,000 | 5 | 5 @ 90eu | 4 @ 2000 range | 4 | 2 | 6 @ 200eu | 1 @ 285eu | - |
| Heavy Cruiser | HC | 450 | 190,000 | 7 | 6 @ 90eu | 4 @ 2000 range | 6 | 3 | 6 @ 225eu | 2 @ 285eu | - |
| Dreadnought | DN | 500 | 295,000 | 8 | 8 @ 90eu | 8 @ 2000 range | 8 | 6 | 6 @ 250eu | 3 @ 285eu | - |

## THE KLINGON EMPIRE

| Class | Code | Crew | DWT (Kilotons) | Reactors | Batteries | Phasers | Torpedos | Probes | Shields | Warp | Notes |
|-------|------|------|--------|----------|-----------|---------|----------|--------|---------|------|-------|
| Escort | ES | 65 | 65,000 | 2 | 6 @ 75eu | 5 @ 2200 range | 1 | 1 | 5 @ 100eu | 2 @ 125eu | - |
| Frigate | FR | 175 | 70,000 | 3 | 4 @ 75eu | 5 @ 2200 range | 2 | 2 | 6 @ 175eu | 1 @ 268eu | - |
| Dreadnought | DK | 550 | 275,000 | 8 | 8 @ 75eu | 8 @ 2200 range | 6 | 4 | 6 @ 225eu | 3 @ 285eu | - |

## THE ROMULAN EMPIRE

| Class | Code | Crew | DWT (Kilotons) | Reactors | Batteries | Phasers | Torpedos | Probes | Shields | Warp | Notes |
|-------|------|------|--------|----------|-----------|---------|----------|--------|---------|------|-------|
| War Eagle | WE | 115 | 50,000 | 3 | 3 @ 225eu | 5 @ 2500 range | 1 plasma | 1 | 6 @ 400eu | 2 @ 70eu | Cloaking |
| Flagship | FD | 275 | 150,000 | 6 | 6 @ 225eu | 8 @ 2500 range | 2 plasma | 2 | 6 @ 325eu | 2 @ 176eu | - |

## THE ORION PIRATES

| Class | Code | Crew | DWT (Kilotons) | Reactors | Batteries | Phasers | Torpedos | Probes | Shields | Warp | Notes |
|-------|------|------|--------|----------|-----------|---------|----------|--------|---------|------|-------|
| Assassin | AS | 45 | 20,000 | 2 | 4 @ 45eu | 3 @ 1800 range | 1 | 1 | 5 @ 100eu | 1 @ 200eu | - |
| Raider | RA | 80 | 35,000 | 2 | 6 @ 45eu | 4 @ 1800 range | 1 | 1 | 6 @ 125eu | 1 @ 200eu | - |
| Raider | RA | 145 | 60,000 | 4 | 6 @ 45eu | 5 @ 2000 range | 3 | 3 | 6 @ 350eu | 2 @ 200eu | (larger variant) |

## NOTES ON MANUAL DISCREPANCIES

- **Destroyer crew:** Manual lists 200, but binary has 250 (binary is correct per game testing)
- **Interceptor not found in binary yet** — may be in separate table
- **DWT units:** Appear to be scaled by ~10 in the binary
- **Some Klingon/Romulan ships:** May have different variants or not all are in Begin 3.0.1

## Next: Fill Binary Values

**CORRECTED (class-data mapping session, 2026-09-26) — see `ENERGY_SYSTEM_MAP.md` §3.9:** these
file offsets were originally off by 4 bytes (found by searching for crew/DWT numbers under the
wrong struct base — confirmed via a live memory read of the running game). Also, crew lives at
`class_data+0x18` now, not `+0x14` — see `ship-struct-analysis.md`'s corrected header table.

The following ships have been located in the binary (file offsets, corrected -4 from the original):
- Heavy Cruiser: 0x00088588 (crew=450 ✓, re-verified this session)
- Destroyer: 0x000843b8 (crew=250, manual says 200; re-verified this session)
- Frigate: 0x00087a90 (crew=175 ✓, re-verified this session)
- Battle Cruiser: 0x00087e38 (need to dump - offset corrected but not re-checked)
- Dreadnought: 0x000860f8, 0x00087340 (need to verify - offsets corrected but not re-checked)
- Dreadnought Killer: 0x00080fd8 (need to dump - offset corrected but not re-checked)

