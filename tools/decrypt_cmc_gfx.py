"""CMC50 C-region decryption and S-region extraction for Metal Slug 5.

Port of MAME src/devices/bus/neogeo/prot_cmc.cpp: decrypt, gfx_decrypt,
cmc50_gfx_decrypt and sfix_decrypt. BSD-3-Clause, copyright S. Smith,
David Haywood, Fabio Priuli; see tools/licenses/mame-pvc.txt for the same
holders and full license. Lookup tables come from the hash-pinned source.
Only the 64 MiB graphics / 128 KiB fixed layout is supported here.
"""

from cmc_tables import load_tables


GRAPHICS_SIZE = 0x4000000
FIXED_SIZE = 0x20000


def decrypt_graphics(data: bytes, extra_xor: int = 0x19) -> bytes:
    """Return decrypted C bytes without modifying the encrypted input.

    Addresses in both passes are 32-bit word indices, not byte offsets.
    extra_xor is the game's CMC50 graphics key.
    """
    if len(data) != GRAPHICS_SIZE:
        raise ValueError("CMC50 graphics input must be exactly 64 MiB")
    if not isinstance(extra_xor, int) or not 0 <= extra_xor <= 0xff:
        raise ValueError("CMC50 graphics key must be an 8-bit integer")
    tables = load_tables()
    type0_t03 = tables["kof2000_type0_t03"]
    type0_t12 = tables["kof2000_type0_t12"]
    type1_t03 = tables["kof2000_type1_t03"]
    type1_t12 = tables["kof2000_type1_t12"]
    address_8_15_xor1 = tables["kof2000_address_8_15_xor1"]
    address_8_15_xor2 = tables["kof2000_address_8_15_xor2"]
    address_16_23_xor1 = tables["kof2000_address_16_23_xor1"]
    address_16_23_xor2 = tables["kof2000_address_16_23_xor2"]
    address_0_7_xor = tables["kof2000_address_0_7_xor"]
    word_count = GRAPHICS_SIZE // 4
    intermediate = bytearray(GRAPHICS_SIZE)

    # Data XOR: MAME decrypt() for byte pairs (0, 3) and (1, 2).
    for rpos in range(word_count):
        middle = (rpos >> 8) & 0xff
        table_index = (rpos & 0xff) ^ address_0_7_xor[middle]
        tmp03 = type1_t03[table_index]
        tmp12 = type1_t12[table_index]
        xor0 = (type0_t03[middle] & 0xfe) | (tmp03 & 1)
        xor3 = (tmp03 & 0xfe) | (type0_t12[middle] & 1)
        xor1 = (type0_t12[middle] & 0xfe) | (tmp12 & 1)
        xor2 = (tmp12 & 0xfe) | (type0_t03[middle] & 1)
        offset = 4 * rpos
        if (rpos >> 8) & 1:
            intermediate[offset] = data[offset + 3] ^ xor0
            intermediate[offset + 3] = data[offset] ^ xor3
        else:
            intermediate[offset] = data[offset] ^ xor0
            intermediate[offset + 3] = data[offset + 3] ^ xor3
        if ((rpos >> 16) ^ address_16_23_xor2[middle]) & 1:
            intermediate[offset + 1] = data[offset + 2] ^ xor1
            intermediate[offset + 2] = data[offset + 1] ^ xor2
        else:
            intermediate[offset + 1] = data[offset + 1] ^ xor1
            intermediate[offset + 2] = data[offset + 2] ^ xor2

    output = bytearray(GRAPHICS_SIZE)
    # Native-endian word views only copy whole words: no word arithmetic is
    # performed, so their endian interpretation cannot change the byte order.
    source_words = memoryview(intermediate).cast("I")
    output_words = memoryview(output).cast("I")
    for rpos in range(word_count):
        baser = rpos ^ extra_xor
        baser ^= address_8_15_xor1[(baser >> 16) & 0xff] << 8
        baser ^= address_8_15_xor2[baser & 0xff] << 8
        baser ^= address_16_23_xor1[baser & 0xff] << 16
        baser ^= address_16_23_xor2[(baser >> 8) & 0xff] << 16
        baser ^= address_0_7_xor[(baser >> 8) & 0xff]
        baser &= word_count - 1
        output_words[rpos] = source_words[baser]
    return bytes(output)


def extract_fixed(decrypted: bytes) -> bytes:
    """Extract MAME sfix_decrypt's 128 KiB byte permutation from C's tail."""
    if len(decrypted) != GRAPHICS_SIZE:
        raise ValueError("Fixed extraction requires exactly 64 MiB of decrypted C data")
    source = memoryview(decrypted)[GRAPHICS_SIZE - FIXED_SIZE:]
    output = bytearray(FIXED_SIZE)
    for index in range(FIXED_SIZE):
        address = ((index & ~0x1f) + ((index & 7) << 2)
                   + ((~index & 8) >> 2) + ((index & 0x10) >> 4))
        output[index] = source[address]
    return bytes(output)
