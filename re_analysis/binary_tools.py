#!/usr/bin/env python3
"""
Binary analysis utilities for Begin.exe reverse engineering.
Reusable functions for dumping, comparing, and analyzing ship structs.
"""

import struct
from typing import List, Tuple, Optional


def dump_ship_entry(binary_path: str, file_offset: int, size: int = 256) -> List[Tuple[int, int, str, str, str]]:
    """
    Dump a ship struct entry from the binary as 32-bit little-endian values.

    Args:
        binary_path: Path to Begin.exe
        file_offset: File offset where the ship entry starts
        size: Number of bytes to read (default 256)

    Returns:
        List of (address, value, hex_str, type_name, interpretation)
    """
    with open(binary_path, 'rb') as f:
        f.seek(file_offset)
        data = f.read(size)

    results = []
    for i in range(0, len(data), 4):
        val_bytes = data[i:i+4]
        if len(val_bytes) == 4:
            as_int = struct.unpack('<I', val_bytes)[0]
            as_float = struct.unpack('<f', val_bytes)[0]
            hex_str = ' '.join(f'{b:02x}' for b in val_bytes)

            address = file_offset + i

            # Interpret the value
            if as_int > 0x00400000 and as_int < 0x004a0000:
                type_name = "PTR"
                interp = f"0x{as_int:08x}"
            elif as_int == 0:
                type_name = "ZERO"
                interp = "0"
            elif as_int < 10000:
                type_name = "INT"
                interp = str(as_int)
            elif 0.001 < as_float < 1000:
                type_name = "FLOAT"
                interp = f"{as_float:.4f}"
            else:
                type_name = "???"
                interp = f"int={as_int}, float={as_float:.2f}"

            results.append((address, as_int, hex_str, type_name, interp))

    return results


def dump_doubles(binary_path: str, file_offset: int, count: int = 8) -> List[Tuple[int, float]]:
    """
    Dump a run of consecutive 8-byte IEEE 754 doubles from the binary.

    Added for the class-data TypeRecord mapping session: dump_ship_entry() only
    interprets 4-byte ints/floats, but the per-subsystem TypeRecord fields found
    in that session (reactor rate, charge rate, capacity, etc.) are doubles.

    Args:
        binary_path: Path to Begin.exe
        file_offset: File offset to start reading from
        count: Number of consecutive doubles to read (default 8, i.e. 64 bytes)

    Returns:
        List of (address, value) tuples, one per double.
    """
    with open(binary_path, 'rb') as f:
        f.seek(file_offset)
        data = f.read(count * 8)

    results = []
    for i in range(0, len(data) - 7, 8):
        value = struct.unpack('<d', data[i:i+8])[0]
        results.append((file_offset + i, value))
    return results


def print_doubles(entries: List[Tuple[int, float]], header: str = "") -> None:
    """Pretty-print a dump_doubles() result."""
    if header:
        print(f"\n{header}")
        print("=" * 60)
    for address, value in entries:
        print(f"0x{address:08x}: {value}")


def print_dump(entries: List[Tuple[int, int, str, str, str]], header: str = "") -> None:
    """Pretty-print a ship struct dump."""
    if header:
        print(f"\n{header}")
        print("=" * 100)

    for address, value, hex_str, type_name, interp in entries:
        print(f"0x{address:08x}: {hex_str:25s} {type_name:7s} {interp}")


def compare_ship_entries(binary_path: str, ships: List[Tuple[str, int]]) -> None:
    """
    Compare multiple ship entries and highlight differences.

    Args:
        binary_path: Path to Begin.exe
        ships: List of (ship_name, file_offset) tuples
    """
    print("\n" + "=" * 120)
    print("SHIP STRUCT COMPARISON")
    print("=" * 120)

    # Dump all ships
    dumps = {}
    for ship_name, offset in ships:
        dumps[ship_name] = dump_ship_entry(binary_path, offset, size=256)

    # Print side-by-side comparison of offsets
    print("\n{:<20s}".format("Offset"), end="")
    for ship_name, _ in ships:
        print(f" | {ship_name:35s}", end="")
    print()
    print("-" * 120)

    # Get max entries
    max_entries = max(len(entries) for entries in dumps.values())

    for i in range(min(max_entries, 60)):  # Limit to first 60 dwords
        offset = f"0x{i*4:04x}"
        print(f"{offset:<20s}", end="")

        for ship_name, _ in ships:
            entries = dumps[ship_name]
            if i < len(entries):
                addr, value, hex_str, type_name, interp = entries[i]
                # Highlight key values (non-zero, non-pointer, reasonable integers)
                if type_name == "INT" and 0 < value < 10000:
                    print(f" | {interp:>5s} ({type_name})", end="")
                elif type_name == "FLOAT":
                    print(f" | {interp:>8s}", end="")
                elif type_name == "PTR":
                    print(f" | PTR", end="")
                else:
                    print(f" | {interp:>10s}", end="")
            else:
                print(f" | {'—':>10s}", end="")
        print()


def find_value_in_binary(binary_path: str, value: int, show_context: bool = True) -> List[int]:
    """
    Find all occurrences of a 32-bit little-endian integer in the binary.

    Args:
        binary_path: Path to Begin.exe
        value: Integer value to search for
        show_context: If True, print context around each match

    Returns:
        List of file offsets where the value was found
    """
    target = struct.pack('<I', value)

    with open(binary_path, 'rb') as f:
        data = f.read()

    matches = []
    pos = 0
    while True:
        pos = data.find(target, pos)
        if pos == -1:
            break

        matches.append(pos)

        if show_context:
            context_start = max(0, pos - 16)
            context_end = min(len(data), pos + 20)
            context_hex = data[context_start:context_end].hex()
            print(f"  Found at 0x{pos:08x}: {context_hex}")

        pos += 1

    return matches


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        binary_path = sys.argv[1]
        if len(sys.argv) > 2:
            offset = int(sys.argv[2], 16)
            dump = dump_ship_entry(binary_path, offset, size=256)
            print_dump(dump, f"Ship entry at 0x{offset:08x}")
