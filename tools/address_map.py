"""Explicit Metal Slug 5 cartridge ROM address mapping.

Rules follow MAME revision df09546b783c419889a2386bec9402883574b881:
src/mame/snk/neogeo.cpp (banked_vectors_r, cartridge ROM installation,
NEOGEO_MSLUG5 PVC overlay) and src/devices/bus/neogeo/prot_pvc.cpp
(pvc_prot_device::get_bank_base). Pinned copies live in artifacts/reference.
This resolver requires caller-supplied bank/vector state; it infers no state
and does not wrap addresses or out-of-range ROM offsets.

PVC formula adapted from MAME; Copyright S. Smith, David Haywood, Fabio Priuli.
SPDX-License-Identifier: BSD-3-Clause
See tools/licenses/mame-pvc.txt for the full license.
"""

from typing import Optional, Tuple


def _nonnegative_integer(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(name + " must be a nonnegative integer")


def cpu_to_rom_offset(cpu_address: int, bank_base: Optional[int] = None,
                      cart_vectors: bool = False,
                      rom_size: int = 0x800000) -> Optional[int]:
    """Resolve one CPU byte address to a cartridge program ROM byte offset.

    None means the address is not cartridge ROM, the bank is unknown, or the
    resolved byte falls outside rom_size. The 0x000000..0x00007f vector window
    resolves only when cart_vectors explicitly selects cartridge vectors.
    bank_base is a byte offset, not a bank number or a 1 MiB aligned value.
    Odd bank bases and odd CPU byte addresses are both valid.
    """
    _nonnegative_integer(cpu_address, "cpu_address")
    if cpu_address > 0xffffff:
        raise ValueError("cpu_address must fit in 24 bits")
    if bank_base is not None:
        _nonnegative_integer(bank_base, "bank_base")
    _nonnegative_integer(rom_size, "rom_size")
    if not isinstance(cart_vectors, bool):
        raise ValueError("cart_vectors must be a boolean")

    if cpu_address < 0x80:
        if not cart_vectors:
            return None
        offset = cpu_address
    elif cpu_address <= 0x0fffff:
        offset = cpu_address
    elif 0x200000 <= cpu_address <= 0x2fdfff:
        if bank_base is None:
            return None
        offset = bank_base + cpu_address - 0x200000
    else:
        # This includes the PVC RAM overlay at 0x2fe000..0x2fffff.
        return None

    return offset if offset < rom_size else None


def pvc_bank_update(word_ff8: int, word_ff9: int) -> Tuple[int, int, int]:
    """Return (ROM bank byte base, updated ff8, updated ff9) from uint16 words.

    Inputs are the merged PVC RAM words before get_bank_base runs. The bank
    formula uses those original words, before the two register side effects.
    There is no ROM-size check here: the hardware formula can exceed the ROM,
    and cpu_to_rom_offset rejects out-of-range offsets independently.
    """
    for value, name in ((word_ff8, "word_ff8"), (word_ff9, "word_ff9")):
        _nonnegative_integer(value, name)
        if value > 0xffff:
            raise ValueError(name + " must fit in 16 bits")

    bank_base = ((word_ff8 >> 8) | (word_ff9 << 8)) + 0x100000
    new_ff8 = (word_ff8 & 0xfe00) | 0x00a0
    new_ff9 = word_ff9 & 0x7fff
    return bank_base, new_ff8, new_ff9
