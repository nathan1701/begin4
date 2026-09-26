# Path B3 Findings - Energy System Investigation

## Summary
Investigated the energy system constants in Begin3.exe through binary analysis and Ghidra disassembly. Discovered a discrepancy between the addresses reported in Path B2 and actual constant locations in the binary.

## Key Discoveries

### 1. Address Space Understanding
- **Ghidra uses 0x00400000 as the image base** (NOT the PE header's 0x00062e00)
- This is standard for x86 Windows executables when loaded in an analysis tool
- Requires proper VA-to-file-offset conversion using PE section headers

### 2. The Three FMUL Instructions

#### Instruction 1: 0x0040f871
```assembly
0040f868: FLD double ptr [EAX + 0x208]      // Load value from ship structure offset 0x208
0040f871: FMUL double ptr [0x00464688]      // Multiply by constant at 0x00464688
0040f877: FSTP double ptr [ESP]              // Store result for display
```
**Context**: EAX points to ship structure (passed as parameter)
**Purpose**: Appears to calculate a display value using a multiplier

#### Instruction 2: 0x0040f997
```assembly
0040f990: FLD double ptr [ECX + 0x1c8]      // Load reactor power (probably)
0040f996: PUSH EAX
0040f997: FMUL double ptr [0x00464688]      // Multiply by constant at 0x00464688
0040f99d: SUB ESP,0x8
0040f9a0: FSTP double ptr [ESP]              // Store result for display
```
**Context**: ECX points to ship structure, offset 0x1c8 is likely reactor power
**Purpose**: Calculate reactor power display with multiplier

#### Instruction 3: 0x0040fc87
```assembly
0040fc7d: CMP ESI,0x1
0040fc81: FLD double ptr [ECX + 0x390]      // Load shield-related value
0040fc87: FMUL double ptr [0x00464688]      // Multiply by constant at 0x00464688
0040fc8d: FSTP double ptr [ESP]              // Store result for display
```
**Context**: ECX points to ship structure, offset 0x390 is likely shield field
**Purpose**: Calculate shield power display with multiplier

### 3. Constant Locations Found

#### Address 0x00464688 (Referenced in FMUL instructions)
- **Value**: 100.0 (IEEE 754 double)
- **File offset**: 0x00063888
- **Section**: .rdata
- **Status**: Confirmed via binary read, but contains 100.0, NOT 4.0

#### Address 0x00464ad8 (First 4.0 constant)
- **Value**: 4.0 (IEEE 754 double)
- **File offset**: 0x00063cd8
- **Section**: .rdata
- **Context**: 
  - Previous: 1.0, 1e-08
  - Current: 4.0
  - Next: 0.01745329252 (π/180, degrees-to-radians), 10.0
- **Interpretation**: Part of a lookup table or constants array

#### Address 0x00478798 (Second 4.0 constant)
- **Value**: 4.0 (IEEE 754 double)
- **File offset**: 0x00077998
- **Section**: .data
- **Context**:
  - Previous: 1.325817659497261, 4.170771417695958e-09
  - Current: 4.0
  - Next: 1.3276424705982208, 8.562541371162474e-09
- **Interpretation**: Part of another lookup table or ship data structure

## Discrepancies & Questions

1. **Why does 0x00464688 contain 100.0 instead of 4.0?**
   - Possible explanations:
     - The address was recorded incorrectly in Path B2
     - There are multiple energy constants serving different purposes
     - The value 100.0 might be shield maximum capacity or another scaling factor

2. **What is the relationship between the three locations?**
   - All three FMUL instructions reference the same address (0x00464688)
   - But the actual 4.0 constant appears at different addresses (0x00464ad8, 0x00478798)
   - This suggests either:
     - Register-relative addressing that modifies the base address at runtime
     - Multiple ship types with different constants
     - A pattern table lookup

3. **What do these offsets represent?**
   - 0x208, 0x1c8, 0x390 are offsets within the ship structure
   - Need to map these to understand what fields are being multiplied

## Ship Structure Offsets (From Disassembly)

Based on the decompilation and disassembly analysis:
- **0x208**: Unknown (first FMUL operand)
- **0x1c8**: Likely reactor power level (second FMUL operand)
- **0x390**: Likely shield capacity (third FMUL operand)

Other observed offsets:
- **0x58**: Weapon type 1 count
- **0x90**: Weapon type 2 count
- **0x200, 0x110, 0x158**: Different reactor types
- **0x1c0**: Reactor output/power
- **0x1d0**: Shield type
- **0x2d0**: Unknown type (possibly armor/defense)
- **0x38**: Likely divisor for power calculations
- **0x20**: Another power-related field

## Recommendations for Path B3 Continuation

1. **Use the actual 4.0 locations** (0x00464ad8 and 0x00478798) rather than 0x00464688
2. **Map the ship structure completely** by:
   - Looking at initialization code to see which offsets are set
   - Finding string references ("WEAPONRY:", "Reactors", etc.) to trace data usage
   - Understanding the pattern of constants around the 4.0 values
3. **Investigate the 100.0 constant** at 0x00464688:
   - Is it a display scaling factor?
   - Is it shield max capacity?
   - Is it related to a different game mechanic?
4. **Check if these are lookup tables** by examining addresses before/after

## Tools Updated

Enhanced `energy_system_analysis.py` to:
- Properly parse PE section headers
- Correctly convert Ghidra VAs to file offsets using section mapping
- Find all 4.0 constants in the binary
- Support both traditional PE image_base and Ghidra's normalized 0x00400000 base address

## Next Steps

1. Navigate to the 4.0 constants in Ghidra and examine surrounding data
2. Trace backwards from FMUL instructions to understand addressing modes
3. Look for initialization code that populates these constants
4. Map the complete ship structure layout
5. Document the energy calculation formulas with correct constants
