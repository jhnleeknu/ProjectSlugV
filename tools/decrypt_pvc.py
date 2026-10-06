"""Metal Slug 5 PVC program decryption with explicit MAME byte layout.

Adapted from MAME src/devices/bus/neogeo/prot_pvc.cpp,
pvc_prot_device::mslug5_decrypt_68k (pinned copy in artifacts/reference).
Copyright S. Smith, David Haywood, Fabio Priuli.
SPDX-License-Identifier: BSD-3-Clause
See tools/licenses/mame-pvc.txt for the full license.

This implements the pinned algorithm, not an independently inferred hardware
model. It does not read archives or modify its input.
"""


PROGRAM_SIZE = 0x800000
XOR1 = (
    0xc2, 0x4b, 0x74, 0xfd, 0x0b, 0x34, 0xeb, 0xd7,
    0x10, 0x6d, 0xf9, 0xce, 0x5d, 0xd5, 0x61, 0x29,
    0xf5, 0xbe, 0x0d, 0x82, 0x72, 0x45, 0x0f, 0x24,
    0xb3, 0x34, 0x1b, 0x99, 0xea, 0x09, 0xf3, 0x03,
)
XOR2 = (
    0x36, 0x09, 0xb0, 0x64, 0x95, 0x0f, 0x90, 0x42,
    0x6e, 0x0f, 0x30, 0xf6, 0xe5, 0x08, 0x30, 0x64,
    0x08, 0x04, 0x00, 0x2f, 0x72, 0x09, 0xa0, 0x13,
    0xc9, 0x0b, 0xa0, 0x3e, 0xc2, 0x00, 0x40, 0x2b,
)
WORD_BITS = (15, 14, 13, 12, 10, 11, 8, 9, 6, 7, 4, 5, 3, 2, 1, 0)
FIRST_BLOCK_BITS = (7, 6, 5, 4, 1, 0, 3, 2)
LATER_BLOCK_BITS = (5, 4, 7, 6, 1, 0, 3, 2)


def bitswap(value: int, *source_bits: int) -> int:
    """Build output from source bits listed most significant first, as in MAME."""
    result = 0
    for source_bit in source_bits:
        result = (result << 1) | ((value >> source_bit) & 1)
    return result


def decrypt_program(data: bytes, byte_xor: int = 0) -> bytes:
    """Return decrypted bytes for an exactly 8 MiB program image.

    byte_xor=0 selects MAME little-endian host word storage. byte_xor=1 selects
    canonical 68000 big-endian bytes. This is the pinned BYTE_XOR_LE mapping:
    native little endian uses identity; native big endian uses xor 1.
    The returned image retains the input byte layout.
    """
    if len(data) != PROGRAM_SIZE:
        raise ValueError("PVC program image must be exactly 0x800000 bytes (8 MiB)")
    if byte_xor not in (0, 1):
        raise ValueError("byte_xor must be 0 (little-endian storage) or 1 (canonical BE)")

    rom = bytearray(data)
    for i in range(0x100000):
        rom[i] ^= XOR1[(i ^ byte_xor) % 0x20]
    for i in range(0x100000, PROGRAM_SIZE):
        rom[i] ^= XOR2[(i ^ byte_xor) % 0x20]

    # Precompute the exact 16-bit permutation to avoid repeated Python bit
    # loops across the 1,835,008 cross-word pairs.
    word_swap = [bitswap(value, *WORD_BITS) for value in range(0x10000)]
    for i in range(0x100000, PROGRAM_SIZE, 4):
        low_index = (i + 1) ^ byte_xor
        high_index = (i + 2) ^ byte_xor
        rom16 = rom[low_index] | (rom[high_index] << 8)
        rom16 = word_swap[rom16]
        rom[low_index] = rom16 & 0xff
        rom[high_index] = rom16 >> 8

    buf = bytes(rom)
    for i in range(0x100000 // 0x10000):
        offset = (i & 0xf0) + bitswap(i & 0x0f, *FIRST_BLOCK_BITS)
        rom[i * 0x10000:(i + 1) * 0x10000] = buf[offset * 0x10000:(offset + 1) * 0x10000]
    for i in range(0x100000, PROGRAM_SIZE, 0x100):
        offset = ((i & 0xf000ff) + ((i & 0x000f00) ^ 0x00700)
                  + (bitswap((i & 0x0ff000) >> 12, *LATER_BLOCK_BITS) << 12))
        rom[i:i + 0x100] = buf[offset:offset + 0x100]

    buf = bytes(rom)
    rom[0x100000:0x200000] = buf[0x700000:0x800000]
    rom[0x200000:0x800000] = buf[0x100000:0x700000]
    return bytes(rom)
