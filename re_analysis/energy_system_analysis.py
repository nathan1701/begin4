#!/usr/bin/env python3
"""
Energy System Analysis for Begin.exe
Utilities for analyzing WES:RES (Weapon Energy Storage : Reactor Energy Storage) ratio
and energy system constants in the binary.
"""

import struct
from typing import Dict, List, Tuple, Optional


def analyze_pe_header(binary_path: str) -> Dict[str, any]:
    """
    Read PE header information from a Windows executable, including section table.

    Args:
        binary_path: Path to Begin.exe

    Returns:
        Dictionary with 'image_base', 'num_sections', 'sections' info
    """
    with open(binary_path, 'rb') as f:
        # Read DOS header
        f.seek(0x3c)
        pe_offset = struct.unpack('<I', f.read(4))[0]

        # Read PE signature
        f.seek(pe_offset)
        pe_sig = f.read(4)

        if pe_sig != b'PE\0\0':
            raise ValueError("Not a valid PE executable")

        # Read COFF header (machine, num_sections)
        f.seek(pe_offset + 4)
        machine = struct.unpack('<H', f.read(2))[0]
        num_sections = struct.unpack('<H', f.read(2))[0]

        # Skip to optional header size field
        f.seek(pe_offset + 20)
        opt_header_size = struct.unpack('<H', f.read(2))[0]

        # Read image base from optional header
        f.seek(pe_offset + 28)
        image_base = struct.unpack('<I', f.read(4))[0]

        # Read section headers (start after COFF and optional headers)
        sections = []
        section_offset = pe_offset + 24 + opt_header_size
        for i in range(num_sections):
            f.seek(section_offset + i * 40)
            name = f.read(8).rstrip(b'\0').decode('ascii', errors='ignore')
            virtual_size = struct.unpack('<I', f.read(4))[0]
            virtual_addr = struct.unpack('<I', f.read(4))[0]
            size_of_raw = struct.unpack('<I', f.read(4))[0]
            ptr_to_raw = struct.unpack('<I', f.read(4))[0]

            sections.append({
                'name': name,
                'virtual_size': virtual_size,
                'virtual_addr': virtual_addr,
                'size_of_raw': size_of_raw,
                'ptr_to_raw': ptr_to_raw
            })

        return {
            'image_base': image_base,
            'num_sections': num_sections,
            'machine': machine,
            'opt_header_size': opt_header_size,
            'pe_offset': pe_offset,
            'sections': sections
        }


GHIDRA_IMAGE_BASE = 0x00400000
# Ghidra normalizes this binary's load address to 0x00400000 regardless of what
# the PE header's own OptionalHeader.ImageBase field says (that field is an oddball
# 0x00062e00 for this executable). All VAs copied from Ghidra assume the 0x00400000
# base, so conversions MUST use this constant, not header_info['image_base'].
# Using the PE header's image_base here silently produces wrong (but plausible-looking)
# file offsets for addresses outside .text, which is why 0x00465088 etc. previously
# raised "not found in any PE section" even though they're valid .rdata addresses.


def va_to_file_offset(va: int, binary_path: str) -> Optional[int]:
    """
    Convert a Virtual Address (VA) in memory to a file offset in the binary.
    Uses section headers to properly map RVA to file offset.

    Args:
        va: Virtual address (e.g., 0x00464688)
        binary_path: Path to Begin.exe

    Returns:
        File offset for seeking in the binary, or None if VA is not in any section
    """
    header_info = analyze_pe_header(binary_path)

    # Convert VA to RVA (Relative Virtual Address) using Ghidra's normalized base,
    # NOT header_info['image_base'] (see GHIDRA_IMAGE_BASE note above).
    rva = va - GHIDRA_IMAGE_BASE

    # Find which section contains this RVA
    for section in header_info['sections']:
        section_va = section['virtual_addr']
        section_size = section['virtual_size']

        if section_va <= rva < section_va + section_size:
            # Calculate offset within section
            offset_in_section = rva - section_va
            # Map to file offset
            file_offset = section['ptr_to_raw'] + offset_in_section
            return file_offset

    # Not found in any section
    return None


def read_constant_at_address(binary_path: str, va: int, size: int = 8) -> bytes:
    """
    Read raw bytes at a virtual address.

    Args:
        binary_path: Path to Begin.exe
        va: Virtual address
        size: Number of bytes to read (default 8 for double)

    Returns:
        Raw bytes at that address

    Raises:
        ValueError: If VA is not found in any section
    """
    file_offset = va_to_file_offset(va, binary_path)

    if file_offset is None:
        raise ValueError(f"Virtual address 0x{va:08x} not found in any PE section")

    with open(binary_path, 'rb') as f:
        f.seek(file_offset)
        return f.read(size)


def interpret_as_double(data: bytes) -> float:
    """Interpret 8 bytes as IEEE 754 double-precision float."""
    if len(data) != 8:
        raise ValueError(f"Expected 8 bytes, got {len(data)}")
    return struct.unpack('<d', data)[0]


def interpret_as_float(data: bytes) -> float:
    """Interpret 4 bytes as IEEE 754 single-precision float."""
    if len(data) != 4:
        raise ValueError(f"Expected 4 bytes, got {len(data)}")
    return struct.unpack('<f', data)[0]


def interpret_as_int32(data: bytes) -> int:
    """Interpret 4 bytes as little-endian 32-bit signed integer."""
    if len(data) != 4:
        raise ValueError(f"Expected 4 bytes, got {len(data)}")
    return struct.unpack('<i', data)[0]


# --- Path B4 findings (2026-09-26) ---------------------------------------------------------
# Full writeup: ENERGY_SYSTEM_MAP.md. Short version: there is NO single "4:1 WES:RES ratio"
# constant. 0x00464688 (100.0) is a generic percent-to-fraction helper used everywhere in the
# codebase; the real 4.0 literal (0x00464ad8) is reused by the compiler for two DIFFERENT real
# game-balance rules (Drive charge/drain rate, and reinforced-vs-regular Shield power cost) plus
# several unrelated formulas (a collision quadratic, a UI threshold, a physics coefficient).
# KNOWN_CONSTANTS below replaces the old single-constant model.

KNOWN_CONSTANTS: Dict[int, Dict[str, any]] = {
    0x00464688: {
        'value': 100.0,
        'role': 'Generic percent(0-100) -> fraction(0.0-1.0) conversion',
        'confirmed_uses': [
            'FUN_0040f4b0 - all 3 display FMULs (percent formatting only)',
            'FUN_00409740 - Drive charge cycle',
            'FUN_004013e0 - generic rand()-based percent-chance helper',
            'FUN_0040aea0 - Shield per-unit charge cycle',
        ],
        'note': '35+ xrefs total. NOT energy-specific despite Path B2/B3 assuming otherwise.',
    },
    0x00464680: {
        'value': 1.0 / 32768.0,
        'role': 'rand() normalizer (RAND_MAX=32767 assumption)',
        'confirmed_uses': ['FUN_004013e0 - rand()/32768.0 < percent/100.0'],
    },
    0x00464ad8: {
        'value': 4.0,
        'role': 'The real "4x" literal - reused for multiple unrelated purposes',
        'confirmed_uses': [
            'FUN_00409740 - Drive charge/drain multiplier (energy)',
            'FUN_0040b320 - Shield reinforcement power-cost weight (energy, "4x power" text)',
            'FUN_004018b0 - quadratic formula b^2-4ac coefficient (collision detection, NOT energy)',
            'FUN_004185e0 - proximity threshold in a generic status-text picker (NOT energy)',
            'FUN_00407220 - unrelated physics/repair coefficient (NOT energy)',
        ],
        'note': 'Two distinct energy-balance rules share this literal. See ENERGY_SYSTEM_MAP.md section 3.',
    },
    0x00478798: {
        'value': 4.0,
        'role': 'Second, separate 4.0 literal in .data',
        'confirmed_uses': [],
        'note': 'UNRESOLVED - zero direct-addressing xrefs found. Likely reached via indexed/array '
                'addressing, not a literal FMUL [addr]. Open question for Path B5.',
    },
    0x00464bd0: {
        'value': 0.5,
        'role': 'Shared 0.5 scaling factor',
        'confirmed_uses': [
            'FUN_00409a70 - end-of-frame Drive reactor pool scaling',
            'FUN_0040b510 - unidentified charge-cycle-shaped function',
        ],
        'note': 'Purpose beyond Drive not confirmed. FUN_0040b510 subsystem unidentified.',
    },
    0x00465088: {'value': 12.0, 'role': "Drive 'ready' charge threshold", 'confirmed_uses': ['FUN_00409740']},
    0x00465488: {
        'value': 40.0,
        'role': "Drive 'fire' charge threshold",
        'confirmed_uses': ['FUN_00409740', 'FUN_004185e0 (reused as a baseline distance)'],
    },
    0x00464ad0: {
        'value': 1e-08,
        'role': 'Min distance-squared cutoff (collision detection)',
        'confirmed_uses': ['FUN_004018b0'],
        'note': 'Value confirmed; not energy-related (geometry epsilon).',
    },
    0x00464ac8: {
        'value': 1.0,
        'role': 'Coefficient in FUN_00407220 (unrelated physics/repair formula)',
        'confirmed_uses': ['FUN_00407220'],
        'note': 'Value confirmed; functional meaning within that formula still open.',
    },
    0x00464b08: {
        'value': 0.1,
        'role': 'Minimum regen floor',
        'confirmed_uses': ['FUN_0040aea0 - Shield per-unit charge cycle'],
        'note': 'Value confirmed; clamps the regen delta to a minimum of 0.1 per tick.',
    },
}


def find_double_in_binary(binary_path: str, target: float, tolerance: float = 1e-9,
                           section_filter: Optional[str] = None) -> List[Dict[str, any]]:
    """
    Scan the whole binary for 8-byte-aligned IEEE 754 doubles matching `target`.

    Complements binary_tools.find_value_in_binary (which searches for 32-bit ints).
    Useful for locating literals like the constants in KNOWN_CONSTANTS, or checking
    whether a suspected ratio appears anywhere else un-cross-referenced (e.g. inside
    an array Ghidra can't see as a scalar reference).

    Args:
        binary_path: Path to Begin.exe
        target: The double value to search for (e.g. 4.0)
        tolerance: Absolute tolerance for the match
        section_filter: If given (e.g. '.rdata'), only report hits in that PE section

    Returns:
        List of {'va': int, 'file_offset': int, 'section': str} for each match
    """
    header_info = analyze_pe_header(binary_path)
    matches = []

    with open(binary_path, 'rb') as f:
        data = f.read()

    for offset in range(0, len(data) - 8, 8):
        chunk = data[offset:offset + 8]
        try:
            value = struct.unpack('<d', chunk)[0]
        except struct.error:
            continue
        if abs(value - target) > tolerance:
            continue

        # Map file offset back to a VA + section name for reporting
        section_name = None
        va = None
        for section in header_info['sections']:
            if section['ptr_to_raw'] <= offset < section['ptr_to_raw'] + section['size_of_raw']:
                section_name = section['name']
                va = GHIDRA_IMAGE_BASE + section['virtual_addr'] + (offset - section['ptr_to_raw'])
                break

        if section_filter and section_name != section_filter:
            continue

        matches.append({'va': va, 'file_offset': offset, 'section': section_name})

    return matches


def search_energy_constants(binary_path: str) -> Dict[int, Dict[str, any]]:
    """
    Read and verify every constant in KNOWN_CONSTANTS against the live binary.

    Superseded the old single-address (0x00464688) version once Path B4 established
    there isn't one energy constant, there are several with different roles.

    Returns:
        Dictionary mapping VA -> {expected, actual, matches, role, confirmed_uses, note}
    """
    results = {}

    for va, info in KNOWN_CONSTANTS.items():
        entry = dict(info)
        try:
            raw_bytes = read_constant_at_address(binary_path, va, size=8)
            actual = interpret_as_double(raw_bytes)
            entry['actual_value'] = actual
            entry['raw_hex'] = raw_bytes.hex()
            expected = info.get('value')
            entry['matches_expected'] = (expected is None) or abs(actual - expected) < 1e-9
        except Exception as e:
            entry['error'] = str(e)
        results[va] = entry

    return results


def analyze_wes_res_ratio(binary_path: str) -> Dict[str, any]:
    """
    Full energy-system report. Despite the name (kept for backward compatibility with
    earlier sessions' scripts/notes), there is no single WES:RES ratio - see
    ENERGY_SYSTEM_MAP.md for the full corrected picture. This returns the two confirmed
    "4x" mechanisms plus the full constant catalogue.

    Returns:
        Dictionary with analysis results
    """
    constants = search_energy_constants(binary_path)

    analysis = {
        'headline': (
            "No single WES:RES ratio exists. Two separate energy-balance rules both reuse "
            "the same 4.0 literal (0x00464ad8): Drive charge/drain rate, and Shield "
            "reinforcement power cost. Weapon (Bank/Tube/Launcher) power draw has not been "
            "traced yet - open question for Path B5."
        ),
        'constants': constants,
        'confirmed_mechanisms': {
            'drive_charge_drain': {
                'function': 'FUN_00409740',
                'formula': 'delta = (ratio_in - (100-phase)/100.0 * reactor_rate) * 4.0',
                'array': 'ship_runtime+0x708, 0x38-byte records',
            },
            'shield_reinforcement_cost': {
                'function': 'FUN_0040b320',
                'formula': 'total_draw += unit.value * (unit.type == 10 ? 4.0 : 1.0)',
                'array': 'ship_runtime+0x7f8, 0x48-byte records',
                'note': 'This is the literal "Reinforced shields require 4x power" mechanism.',
            },
        },
        'not_using_4x': {
            'cloak': 'FUN_0040a690 - flat crew_count*per_crew_cost + base_cost formula, no 4.0',
            'weapons': 'Not yet traced - see ENERGY_SYSTEM_MAP.md Open Questions #1',
        },
        'critical_addresses': {
            '0x00464688': '100.0 - generic percent-to-fraction (NOT energy-specific)',
            '0x00464ad8': 'The real 4.0 - reused for Drive AND Shield (different rules)',
            '0x00478798': 'Second 4.0 - unresolved, no direct xrefs found',
            '0x0040f871': 'Display FMUL #1 - Shield charge percentage (not "unknown field")',
            '0x0040f997': 'Display FMUL #2 - Drive charge percentage (not "reactor power")',
            '0x0040fc87': 'Display FMUL #3 - likely Cloak charge percentage (not "shield capacity")',
            '0x0040f4b0': 'Ship status display function (contains all 3 FMULs)',
            '0x00404250': 'Ship per-frame subsystem update (the real UpdatePower driver)',
        },
        'see_also': 'ENERGY_SYSTEM_MAP.md for full structure maps, function tables, and open questions.',
    }

    return analysis


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        binary_path = sys.argv[1]
        print(f"\nAnalyzing: {binary_path}")

        try:
            analysis = analyze_wes_res_ratio(binary_path)
            # Constants are keyed by int VA internally; render as hex for readability.
            analysis['constants'] = {
                f'0x{va:08x}': info for va, info in analysis['constants'].items()
            }
            print(json.dumps(analysis, indent=2, default=str))
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Usage: python energy_system_analysis.py <path_to_begin.exe>")
        print("\nExample:")
        print("  python energy_system_analysis.py /home/nathan/claude/begin4/original_game/Begin.exe")
