# Begin — Manual Analysis & Reverse-Engineering Notes

Source material reviewed (kept local-only in `original_game/`, not in this repo):
- `Microsoft Word - BEGIN.DOC - BeginMan165.pdf` — Begin v1.65 "Advanced Strategy Manual" (62pp), includes Appendix D previewing v2.0
- `begin2/BEGIN.MAN` — Begin v1.65 "Basic Simulations Manual" (plain text)
- `begin2/WHATS.NEW` — Begin v2.0 changelog

Everything below is paraphrased/synthesized from those documents for our own RE reference —
not a copy of the manual text.

## Version lineage

| Version | Binary | Platform | Notes |
|---|---|---|---|
| 1.65 | (not in our set) | DOS | Fully documented baseline — both manuals above describe this version |
| 2.0 | `begin2/BEGIN2.EXE` | DOS, 16-bit MZ | Feature/command additions over 1.65 (see Appendix D / WHATS.NEW) |
| 3.0.1 build 151 | `Begin.exe` | Windows, 32-bit PE | Per its own version string: "a quick port to Windows of the DOS version" |

**Open question from the user's research:** some mechanics/commands are rumored to be broken
in Begin 2. Nothing in the v2.0 changelog or the v1.65 manual's v2.0 preview reads as a
regression — it's all framed as additive. This needs empirical verification by actually running
`BEGIN2.EXE` (e.g. under DOSBox) and testing it against the documented v1.65 command set, not
something we can confirm from the docs alone.

## Core game loop / time model

- Turn-based command phase, then a real-time movement phase. One full pass is called a **cycle**
  (sometimes referred to as a "second" in-fiction).
- Each cycle subdivides into **10 sub-cycles** for movement, proximity checks, and fuse
  resolution — this is what allows fast-moving torpedoes to be evaluated at finer granularity
  than once per full cycle.
- Rough order of operations per cycle (per the manual's own simplified outline, not the actual
  code structure): tally available energy → deduct life support → deduct shields → charge
  weapons with leftover energy → aim locked weapons → fire phasers → launch torpedoes → launch
  probes → run the 10 sub-cycles (move everything, check fuses, resolve explosions) → check
  engine heat → run repairs → bank/overflow battery charge → prompt for next command.

## Physics & units

- **Distance** — the "Unit." Defined operationally as 1/100 of the distance a ship moving at
  warp 1 covers in one cycle. Not tied to a real-world distance; only relative values matter.
- **Speed** — "Warp," and critically it's a **linear** scale in this game (warp 2 = 2× warp 1,
  warp 4 = 2× warp 2) — not the logarithmic scale sci-fi usually implies. Ships can reverse down
  to warp -1.
- **Energy** — the "eu" (energy unit). Produced by reactors and warp engines, stored in
  batteries, consumed by every subsystem.
- **Temperature** — tracked only for warp engines, drives the overheat mechanic. Manual gives a
  threshold around 40 "M" degrees per engine; the exact meaning/scaling of "M" isn't spelled out
  and should be confirmed from the binary.

## Ship subsystems

- **Reactors / Batteries** — power generation and storage.
- **Phaser banks** — instant-hit, damage falls off **linearly** with range, configurable spread
  (10°–45°), can be locked to a target or fixed to a relative angle ("mark").
- **Torpedo tubes** — fixed velocity per torpedo class, auto-lead a locked target based on its
  course/speed, configurable proximity-fuse detonation range; most classes can't change course
  once fired.
- **Probe launchers** — slow, large warhead, retargetable in flight, must be loaded manually
  (unlike auto-reloading banks/tubes), some classes have homing guidance.
- **Shields** — exactly 6 fixed 60°-wide arcs ("fields") around the hull. Absorb damage up to a
  functional-strength ceiling, regenerate over time, can be individually raised/lowered to save
  power.
- **Damage control crew** — auto-repairs damaged subsystems; repair speed scales with remaining
  crew count; different subsystems have different repair times (warp drives slower than
  phasers, for example).
- **Life support** — costs `crew / 10` eu per cycle continuously; total crew death after 3
  cycles without power to it.

## Energy allocation order

1. Warp Energy System (WES) powers propulsion first; any WES surplus converts to Reactor Energy
   System (RES) at a lossy **4:1** ratio.
2. RES funds, in order: life support → shields → weapon charging. Any leftover RES beyond
   battery capacity is simply lost (not banked).

## Combat damage model

- **Phasers**: 100% energy-efficient at the bank, but damage decays **linearly** with range —
  nearly worthless at max range.
- **Torpedoes / probes / any "antimatter" detonation**: damage decays with the **square** of
  distance from the blast — a very different falloff curve from phasers.
- Shields absorb first; anything exceeding the shield's current capacity carries through to the
  hull/subsystems.
- Subsystem damage is either a hard **destroyed** state (binary — e.g. torpedo tubes, phaser
  banks) or a **degraded** partial-effectiveness state (e.g. reactors, engines, shields).
- All weapons have a short arming delay after launch, so ships can't kill themselves with their
  own just-fired torpedo.

## Enemy/ally AI ("strategy" routines)

Every ship — including allies you haven't given explicit orders to — is assigned 4 hidden
personality stats at creation: **bravery, loyalty, aggression, fanaticism**. Nation determines
the baseline distribution:

- **Federation** — brave, very loyal, low fanaticism (rarely self-destructs), fights to the
  last weapon.
- **Klingon** — less brave than Federation/Romulan but extremely aggressive, somewhat
  fanatical, loyal.
- **Romulan** — avoids close combat, favors plasma torpedoes, every ship carries a suicide bomb
  and isn't shy about using it, slow-moving.
- **Orion (pirates)** — randomized per-captain, explicitly no consistent generalization across
  the faction.

Key documented AI logic:
- **Targeting**: computes a per-enemy "threat level" (a function of range, weapons carried, and
  how many ships are already engaging that target) and attacks the highest-threat target absent
  explicit orders.
- **Weapon selection**: compares relative offense/defense between own ship and the target to
  pick the "best" weapon; also checks whether a probe could finish off an already-weakened
  target as a special case.
- **Retreat rule (given explicitly in the manual)**: `if damage_sustained >= captain_bravery: retreat`
  — with a fanaticism override where a highly fanatical captain may choose a suicide/ramming run
  instead if their ship can still deal damage.
- Also: zig-zag maneuvering to dodge torpedoes, phasering down incoming torpedoes opportunistically,
  maneuvering around (not through) enemy probes when possible, letting a healthy engine run hot
  while sparing a damaged one, and shutting down the weakest shields first when short on power.

## Command set (paraphrased reference — not manual text)

| Category | Commands | Purpose |
|---|---|---|
| Setup only | configure, flagship, begin | Fleet composition and starting the sim |
| Helm | helm, pursue, elude | Course/speed control |
| Sensors/display | chart, report, status damage, scan, range/display | Situational awareness |
| Weapons | fire/lock/turn/status for phasers, torpedoes (tubes), probes (launchers); load/unload/disable/enable tubes/launchers | Combat |
| Shields | raise, lower/drop, status shields | Defense |
| Fleet/allies | tell/order \<ally> \<suborder>, status fleet, transport/beam | Commanding ally ships |
| Self | self destruct/destruct, abort | Emergency |
| Info | library computer, help | Reference lookups |
| Session | quit | End simulation |
| **v2.0 additions** | repair \<system>\|all, tractor, board, dock, cloak (Romulan only), reenforce \<shield>, group, chart by name/distance/nation, text-mode toggle, key \<bindings> | New in Begin 2 |

Ally sub-orders (v1.65): attack, target, disengage, escort, cancel, course, hold fire, open fire,
retreat, report, probe, phaser, torpedo, withdraw.

## Ship/weapon data tables (Appendix C)

Exact per-class numeric stats (crew, displacement, reactor/battery counts and output, weapon
bank/tube/launcher counts with range/charge/load specs, shield generator count/absorption/regen,
warp drive count/efficiency/turn rate) are documented for all four nations: **Federation**
(Interceptor, Destroyer, Heavy Cruiser, Dreadnought), **Klingon** (Escort, Frigate, Dreadnought),
**Romulan** (War Eagle, Bird of Prey), **Orion** (Assassin, Raider, Anarchist). Torpedo/probe
class specs (velocity in warp, destructive force in "antimatter pods," arm delay, stable window)
are also fully tabulated per nation. These exact numbers are kept in the manual PDF locally —
see "RE targets" below for how to use them.

## Open questions / to verify empirically

- Is there an actual documented regression between v1.65 and v2.0, or is "some commands got
  broken in Begin 2" folklore? Nothing we've read supports it directly — needs live testing.
- Exact warp-temperature overheat formula (the "40M degrees" threshold — meaning of "M" unclear).
- Exact threat-level formula for AI targeting (manual is deliberately vague here).
- Exact scoring/odds formula (manual explicitly declines to document it).
- Whether Begin.exe (v3, Windows port) changed any simulation constants from v2.0, or purely
  swapped out the UI/rendering layer.

## RE targets — what to look for when decompiling

1. **String table search** — command keywords (`helm`, `fire`, `phaser`, `torp`, `probe`,
   `tell`, `chart`, ...) and ship/nation/class names are a fast way to locate the command parser
   and ship-class name tables in Ghidra.
2. **Known numeric constants from Appendix C** — e.g. specific crew counts, reactor eu output,
   battery capacity values — search for these as immediate values to find the ship-class
   definition struct/array (likely a fixed-size record repeated per class).
3. **Personality struct** — look for a small 4-field struct (bravery/loyalty/aggression/fanaticism)
   attached to each ship instance, probably byte- or word-sized, seeded per nation at creation.
4. **Main loop shape** — an outer "cycle" loop (input + strategy resolution) wrapping an inner
   loop that runs exactly **10** times (sub-cycles). That constant is a good anchor to search for.
5. **Retreat check** — should be a short, easy-to-spot comparison once the personality struct is
   located: `damage >= bravery`.
6. **Damage falloff functions** — one linear-with-range function (phasers) and one
   inverse-square function (torpedo/probe/antimatter blasts) — look for a divide-by-range vs.
   divide-by-range-squared distinction.
7. **Energy pipeline order** — WES→RES at a 4:1 lossy conversion, then life support (`crew/10`),
   then shields, then weapon charging — a good sequence to confirm against decompiled code order.
   *(Outcome, Path B4: no single unified WES→RES conversion function was found in code. Instead
   there are two separate, subsystem-specific 4x rules — Drive's charge/drain rate and Shield's
   reinforcement power cost — see `ENERGY_SYSTEM_MAP.md`. Weapon energy draw is still untraced,
   so it remains possible the manual's "4:1" description maps onto a weapon-specific mechanism
   not yet found — see Path B5 priority 1.)*
8. **Cross-version diffing** — since `Begin.exe` is stated to be "a quick port to Windows of the
   DOS version," diffing decompiled routines between `BEGIN2.EXE` (DOS) and `Begin.exe` (Win32)
   may show the core simulation logic (combat/physics/AI) is nearly identical in algorithm, with
   differences concentrated in I/O and rendering — useful both for isolating "the actual game"
   from "the UI shell," and for tracking down whatever's claimed to be broken in Begin 2.
9. **Tooling note** — `BEGIN2.EXE` is a 16-bit real-mode DOS MZ executable; Ghidra's 16-bit x86
   support is limited, so behavioral verification is probably easier live under DOSBox (with its
   built-in debugger). `Begin.exe` is a standard 32-bit PE and should get much better mileage out
   of Ghidra's normal decompiler.
