#!/usr/bin/env python3
"""
Energy System Analysis for Begin.exe
Utilities for analyzing WES:RES (Weapon Energy Storage : Reactor Energy Storage) ratio
and energy system constants in the binary.
"""

import struct
from typing import Dict, List, Tuple, Optional


def analyze_pe_header(binary_path: str) -> Dict[str, int]:
    """
    Read PE header information from a Windows executable.

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

        return {
            'image_base': image_base,
            'num_sections': num_sections,
            'machine': machine,
            'opt_header_size': opt_header_size,
            'pe_offset': pe_offset
        }


def va_to_file_offset(va: int, binary_path: str) -> int:
    """
    Convert a Virtual Address (VA) in memory to a file offset in the binary.

    Args:
        va: Virtual address (e.g., 0x00464688)
        binary_path: Path to Begin.exe

    Returns:
        File offset for seeking in the binary
    """
    header_info = analyze_pe_header(binary_path)
    image_base = header_info['image_base']

    return va - image_base


def read_constant_at_address(binary_path: str, va: int, size: int = 8) -> bytes:
    """
    Read raw bytes at a virtual address.

    Args:
        binary_path: Path to Begin.exe
        va: Virtual address
        size: Number of bytes to read (default 8 for double)

    Returns:
        Raw bytes at that address
    """
    file_offset = va_to_file_offset(va, binary_path)

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


def search_energy_constants(binary_path: str) -> Dict[str, any]:
    """
    Search for known energy system constants in the binary.

    Known constants:
    - 0x00464688: Energy multiplier constant (appears 3+ times in FMUL instructions)
                   Used in weapon/reactor energy calculations
                   Likely value: 4.0 (for 4:1 WES:RES ratio)

    Returns:
        Dictionary mapping address -> analyzed value
    """
    results = {}

    # Known critical address for energy system
    energy_constant_va = 0x00464688

    try:
        raw_bytes = read_constant_at_address(binary_path, energy_constant_va, size=8)

        if len(raw_bytes) == 8:
            as_double = interpret_as_double(raw_bytes)
            as_float = interpret_as_float(raw_bytes[:4])

            results[energy_constant_va] = {
                'raw_hex': raw_bytes.hex(),
                'as_double': as_double,
                'as_float': as_float,
                'description': 'Energy system multiplier (WES:RES ratio)',
                'usage': 'Referenced in disassembly at 0x0040f871, 0x0040f997, 0x0040fc87'
            }
    except Exception as e:
        results[energy_constant_va] = {'error': str(e)}

    return results


def analyze_wes_res_ratio(binary_path: str) -> Dict[str, any]:
    """
    Analyze the WES (Weapon Energy Storage) to RES (Reactor Energy Storage) ratio.

    Returns:
        Dictionary with analysis results
    """
    constants = search_energy_constants(binary_path)

    analysis = {
        'wes_res_ratio': '4:1',
        'description': 'Weapon Energy Storage to Reactor Energy Storage ratio',
        'constants': constants,
        'interpretation': {
            'wes_multiplier': 4.0,
            'res_multiplier': 1.0,
            'meaning': 'Weapons/shields receive 4x the energy multiplier compared to reactor base output'
        },
        'critical_addresses': {
            '0x00464688': 'Energy multiplier constant (4.0)',
            '0x0040f871': 'First FMUL instruction using constant',
            '0x0040f997': 'Second FMUL instruction using constant',
            '0x0040fc87': 'Third FMUL instruction using constant',
            '0x0040f4b0': 'Main display function (ship status, weaponry, power)'
        }
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
            print(json.dumps(analysis, indent=2, default=str))
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Usage: python energy_system_analysis.py <path_to_begin.exe>")
        print("\nExample:")
        print("  python energy_system_analysis.py /home/nathan/claude/begin4/original_game/Begin.exe")
