"""Metal Slug 5 CMC50 M1 and PCM2 sample decryption.

Adapted from MAME src/devices/bus/neogeo/prot_cmc.cpp and prot_pcm2.cpp
(pinned copies in artifacts/reference).
Copyright S. Smith, David Haywood, Fabio Priuli.
SPDX-License-Identifier: BSD-3-Clause
See tools/licenses/mame-pvc.txt for the full license.

These implement the pinned algorithms, not independently inferred hardware
models. Inputs are byte images; neither function modifies its input.
"""

try:
    from .cmc_tables import load_tables
    from .decrypt_pvc import bitswap
except ImportError:
    from cmc_tables import load_tables
    from decrypt_pvc import bitswap


M1_SIZE = 0x80000
SAMPLES_SIZE = 0x1000000
M1_KEY_BITS = (12, 0, 2, 4, 8, 15, 7, 13, 10, 1, 3, 6, 11, 9, 14, 5)
M1_FINAL_BITS = (7, 15, 14, 6, 5, 13, 12, 4, 11, 3, 10, 2, 9, 1, 8, 0)
# MAME indexes each row from 15 down to 0 in the bitswap call.
M1_P1 = (
    (15, 14, 10, 7, 1, 2, 3, 8, 0, 12, 11, 13, 6, 9, 5, 4),
    (7, 1, 8, 11, 15, 9, 2, 3, 5, 13, 4, 14, 10, 0, 6, 12),
    (8, 6, 14, 3, 10, 7, 15, 1, 4, 0, 2, 5, 13, 11, 12, 9),
    (2, 8, 15, 9, 3, 4, 11, 7, 13, 6, 0, 10, 1, 12, 14, 5),
    (1, 13, 6, 15, 14, 3, 8, 10, 9, 4, 7, 12, 5, 2, 0, 11),
    (11, 15, 3, 4, 7, 0, 9, 2, 6, 14, 12, 1, 8, 5, 10, 13),
    (10, 5, 13, 8, 6, 15, 1, 14, 11, 9, 3, 0, 12, 7, 4, 2),
    (9, 3, 7, 0, 2, 12, 4, 11, 14, 10, 5, 8, 15, 13, 1, 6),
)
SAMPLE_ADD = 0xfe2cf6
SAMPLE_ADDRESS_XOR = 0x4e001
SAMPLE_XOR = (0xc3, 0xfd, 0x81, 0xac, 0x6d, 0xe7, 0xbf, 0x9e)


def m1_address_scramble(address: int, key: int, tables=None) -> int:
    """Return MAME's source address for one M1 destination address."""
    if tables is None:
        tables = load_tables()
    block = (address >> 16) & 7
    aux = address & 0xffff
    aux ^= bitswap(key & 0xffff, *M1_KEY_BITS)
    aux = bitswap(aux, *reversed(M1_P1[block]))
    aux ^= tables["m1_address_0_7_xor"][(aux >> 8) & 0xff]
    aux ^= tables["m1_address_8_15_xor"][aux & 0xff] << 8
    aux = bitswap(aux, *M1_FINAL_BITS)
    return (block << 16) | aux


def decrypt_m1(data: bytes) -> bytes:
    """Decrypt an exactly 512 KiB encrypted M1 image."""
    if len(data) != M1_SIZE:
        raise ValueError("CMC50 M1 image must be exactly 0x80000 bytes (512 KiB)")
    tables = load_tables()
    low_xor = tables["m1_address_0_7_xor"]
    high_xor = tables["m1_address_8_15_xor"]
    key = sum(data[:0x10000]) & 0xffff
    permuted_key = bitswap(key, *M1_KEY_BITS)
    final_low = [bitswap(i, *M1_FINAL_BITS) for i in range(0x100)]
    final_high = [bitswap(i << 8, *M1_FINAL_BITS) for i in range(0x100)]
    result = bytearray(M1_SIZE)
    for block in range(8):
        permutation = tuple(reversed(M1_P1[block]))
        first_low = [bitswap(i, *permutation) for i in range(0x100)]
        first_high = [bitswap(i << 8, *permutation) for i in range(0x100)]
        base = block << 16
        for address in range(0x10000):
            aux = address ^ permuted_key
            aux = first_low[aux & 0xff] | first_high[aux >> 8]
            aux ^= low_xor[aux >> 8]
            aux ^= high_xor[aux & 0xff] << 8
            source = final_low[aux & 0xff] | final_high[aux >> 8]
            result[base | address] = data[base | source]
    return bytes(result)


def build_audio_region(decrypted: bytes) -> bytes:
    """Build MAME's 576 KiB audio region: first 64 KiB, then full M1 image."""
    if len(decrypted) != M1_SIZE:
        raise ValueError("decrypted M1 image must be exactly 0x80000 bytes (512 KiB)")
    return bytes(decrypted[:0x10000]) + bytes(decrypted)


def sample_destination_address(address: int) -> int:
    """PCM2 value=2 destination; its 24-bit permutation swaps bits 0 and 16."""
    swapped = ((address & 0xfefffe) | ((address & 1) << 16)
               | ((address >> 16) & 1))
    return swapped ^ SAMPLE_ADDRESS_XOR


def sample_source_address(address: int) -> int:
    """PCM2 value=2 source, with explicit 24-bit wrapping addition."""
    return (address + SAMPLE_ADD) & 0xffffff


def decrypt_samples(data: bytes) -> bytes:
    """Decrypt an exactly 16 MiB sample image using PCM2 swap(value=2)."""
    if len(data) != SAMPLES_SIZE:
        raise ValueError("PCM2 sample image must be exactly 0x1000000 bytes (16 MiB)")
    result = bytearray(SAMPLES_SIZE)
    for address in range(SAMPLES_SIZE):
        destination = ((address & 0xfefffe) | ((address & 1) << 16)
                       | ((address >> 16) & 1)) ^ SAMPLE_ADDRESS_XOR
        source = (address + SAMPLE_ADD) & 0xffffff
        result[destination] = data[source] ^ SAMPLE_XOR[destination & 7]
    return bytes(result)
