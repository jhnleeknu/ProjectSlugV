"""Decode an explicitly mapped 68000 range; code/data status remains unknown."""

import argparse
import hashlib
import json
from pathlib import Path

import capstone

ROOT = Path(__file__).resolve().parents[1]
MAX_REGION_SIZE = 8 * 1024 * 1024
CPU_ADDRESS_LIMIT = 1 << 24
# More than the longest 68000 instruction. Capstone fabricates operands and
# shortens instruction sizes for truncated buffers, so supply a padded window
# and accept a decode only when its entire size fits the real requested bytes.
DECODE_WINDOW = 24


def validate_range(data, offset, length, cpu_base):
    if len(data) > MAX_REGION_SIZE:
        raise ValueError('Program region exceeds 8 MiB')
    for name, value in (('offset', offset), ('length', length), ('cpu_base', cpu_base)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError('%s must be a nonnegative integer' % name)
        if value % 2:
            raise ValueError('%s must be even' % name)
    if length == 0:
        raise ValueError('length must be positive')
    if offset + length > len(data):
        raise ValueError('Requested ROM range exceeds the program region')
    if cpu_base >= CPU_ADDRESS_LIMIT or cpu_base + length > CPU_ADDRESS_LIMIT:
        raise ValueError('Requested CPU range exceeds the 24-bit address space')


def disassemble_range(data, offset, length, cpu_base):
    """Return candidate instructions covering every byte in the supplied range."""
    validate_range(data, offset, length, cpu_base)
    decoder = capstone.Cs(capstone.CS_ARCH_M68K,
                          capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    rows = []
    consumed = 0
    while consumed < length:
        rom_offset = offset + consumed
        address = cpu_base + consumed
        available = min(DECODE_WINDOW, length - consumed)
        window = bytes(data[rom_offset:rom_offset + available])
        padded = window + bytes(DECODE_WINDOW - available)
        instruction = next(decoder.disasm(padded, address, count=1), None)
        if (instruction is not None and instruction.mnemonic != 'dc.w'
                and instruction.size >= 2 and instruction.size % 2 == 0
                and instruction.size <= available):
            size = instruction.size
            mnemonic = instruction.mnemonic
            operands = instruction.op_str
            classification = 'candidate_instruction'
        else:
            size = 2
            mnemonic = 'dc.w'
            operands = '$%04x' % int.from_bytes(window[:2], 'big')
            classification = 'undecoded_word'
        rows.append({'rom_offset': rom_offset, 'cpu_address': address,
                     'raw': bytes(data[rom_offset:rom_offset + size]).hex(),
                     'size': size, 'mnemonic': mnemonic, 'op_str': operands,
                     'classification': classification})
        consumed += size
    return rows


def load_verified_program(root):
    manifest = json.loads((root / 'extracted/program/manifest.json').read_text())
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported program manifest schema version')
    source = manifest['output']
    path = root / 'extracted/program/maincpu.decrypted.be.bin'
    if source['path'] != str(path.relative_to(root)) or source['byte_order'] != 'big':
        raise ValueError('Program manifest must identify the canonical big-endian image')
    data = path.read_bytes()
    if len(data) > MAX_REGION_SIZE or len(data) != source['size']:
        raise ValueError('Program size does not match manifest or exceeds 8 MiB')
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise ValueError('Program hash does not match manifest')
    return data, source


def write_disassembly(offset, length, cpu_base, output, root=None):
    root = ROOT if root is None else Path(root)
    data, source = load_verified_program(root)
    rows = disassemble_range(data, offset, length, cpu_base)
    report = {
        'schema_version': 1,
        'format': 'mslug5-explicit-range-disassembly',
        'source': dict(source),
        'decoder': {'name': 'capstone', 'version': capstone.__version__,
                    'architecture': 'M68K', 'cpu': '68000', 'byte_order': 'big'},
        'mapping': {'basis': 'explicitly_supplied_by_caller', 'rom_offset': offset,
                    'length': length, 'cpu_base': cpu_base,
                    'formula': 'cpu_address = cpu_base + (rom_offset - range_rom_offset)',
                    'bank': 'not determined; caller must justify mapping'},
        'limitation': 'Code/data classification and runtime behavior are not determined. '
                      'Decoded instructions are candidates only; this is not completed analysis.',
        'rows': rows,
    }
    output = Path(output)
    if not output.is_absolute():
        output = root / output
    if output.suffix != '.json':
        raise ValueError('Output must use the .json suffix')
    # Protect canonical source data and repository files from CLI output mistakes.
    artifact_root = (root / 'artifacts').resolve()
    if artifact_root not in output.resolve().parents:
        raise ValueError('Output must be inside the artifacts directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    listing = ['; Explicit caller mapping; code/data and runtime behavior unverified.',
               '; Source SHA256: ' + source['sha256'],
               '; ROM offset  CPU address  raw bytes               instruction [classification]']
    for row in rows:
        listing.append('%08x    %06x       %-22s  %s %s [%s]' % (
            row['rom_offset'], row['cpu_address'], row['raw'], row['mnemonic'],
            row['op_str'], row['classification']))
    output.write_text(json.dumps(report, indent=2) + '\n')
    output.with_suffix('.asm').write_text('\n'.join(listing) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offset', type=lambda value: int(value, 0), required=True,
                        help='ROM region byte offset (decimal or 0x hexadecimal)')
    parser.add_argument('--length', type=lambda value: int(value, 0), required=True)
    parser.add_argument('--cpu-base', type=lambda value: int(value, 0), required=True,
                        help='CPU address assigned explicitly to the first byte')
    parser.add_argument('--output', default='artifacts/disassembly/range.json')
    args = parser.parse_args()
    try:
        report = write_disassembly(args.offset, args.length, args.cpu_base, args.output)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))
    print('Decoded %d rows; code/data status remains unknown.' % len(report['rows']))


if __name__ == '__main__':
    main()
