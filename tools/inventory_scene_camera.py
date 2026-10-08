"""Bounded original camera instruction candidates and literal asymmetries.

No camera behavior, callee effects or native reachability are inferred.
"""
import hashlib
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program, disassemble_range
from inventory_game_initialization import asm
from inventory_scene_frame import motion_inventory
from pack_scene_scripts import SOURCE_SHA256

WINDOWS = ((0x19a40, 0x19b50), (0x19b96, 0x19d08))
LITERAL_INSTRUCTIONS = (
    (0x19b38, 'move.l', 'd7, $53e2(a5)', 'Y literal store before subtraction'),
    (0x19b3c, 'sub.l', '$53e2(a5), d7', 'Y literal read of same encoded A5 displacement'),
    (0x19c9a, 'add.w', 'd1, d0', 'X literal ADD.W D1,D0'),
    (0x19c9c, 'bpl.w', '$19ce6', 'X literal BPL immediately after ADD.W'),
    (0x19cce, 'subi.w', '#$b8, d0', 'Y literal SUBI.W'),
    (0x19cd2, 'bpl.w', '$19ce6', 'Y literal BPL immediately after SUBI.W'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical original source')
    windows = []
    indexed = {}
    for start, end in WINDOWS:
        rows = disassemble_range(program, start, end-start, start)
        cursor = start
        for row in rows:
            require(row['cpu_address'] == cursor and row['rom_offset'] == cursor
                    and row['size'] > 0 and cursor+row['size'] <= end,
                    'Window gap, overlap or out-of-range row')
            require(bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']],
                    'Instruction raw bytes/source mismatch')
            require(cursor not in indexed, 'Overlapping explicit instruction windows')
            indexed[cursor] = row
            cursor += row['size']
        require(cursor == end, 'Incomplete exact instruction window coverage')
        undecoded = [r for r in rows if r['classification'] != 'candidate_instruction']
        require(not undecoded, 'Canonical camera window has unexpected undecoded rows')
        windows.append(dict(start_cpu_address=start, start_rom_offset=start,
            end_cpu_address_exclusive=end, end_rom_offset_exclusive=end,
            byte_count=end-start, raw_sha256=sha(program[start:end]),
            instruction_row_count=len(rows), undecoded_row_count=len(undecoded),
            gap_count=0, gaps=[], instructions=rows, undecoded_rows=undecoded))
    evidence = []
    for address, mnemonic, operand, note in LITERAL_INSTRUCTIONS:
        require(address in indexed, 'Literal evidence address is not a decoded row boundary')
        row = indexed[address]
        require(row['mnemonic'] == mnemonic and row['op_str'] == operand,
                'Literal camera instruction evidence changed')
        evidence.append(dict(cpu_address=address, rom_offset=address, note=note,
            instruction=dict(row), raw_sha256=sha(bytes.fromhex(row['raw']))))
    for previous, following in ((0x19b38, 0x19b3c), (0x19c9a, 0x19c9c), (0x19cce, 0x19cd2)):
        require(previous+indexed[previous]['size'] == following,
                'Literal evidence instruction pair is no longer adjacent')
    motion = motion_inventory(root, program, source)
    require(sha(program) == SOURCE_SHA256, 'Original source changed during inventory')
    return dict(schema_version=1, source=source, program_code_modified=False,
        provenance='Pinned original decrypted source checked before/after; padded disassembly bytes and exact source-verified existing motion manifests/containers retained.',
        decoder='Capstone '+capstone.__version__,
        mapping='Fixed first1MiB CPU addresses equal ROM file offsets; encoded A5 displacement remains an operand, RAM/MMIO distinct.',
        window_count=len(windows), instruction_row_count=sum(w['instruction_row_count'] for w in windows),
        undecoded_row_count=sum(w['undecoded_row_count'] for w in windows), gap_count=0,
        windows=windows, literal_asymmetric_evidence=evidence,
        motion_word_at_4_inventory=motion,
        scope='Two main-confirmed complete assigned windows, including bytes after RTS; window endpoints are evidence bounds rather than routine completion. '
              'Literal MOVE.L D7,$53e2(A5) then SUB.L $53e2(A5),D7 and X ADD.W D1,D0 versus Y direct BPL after SUBI retain original bytes without semantic correction. '
              'Existing37 motion resources have raw records and literal signed WORD+4 counts only. No camera/motion semantics, native/C++ execution equivalence, callee effects or natural reachability claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    path = root/'artifacts/scene_camera_disassembly.json'
    listing_path = root/'artifacts/scene_camera_disassembly.asm'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    listing = ['; Original source SHA256 '+SOURCE_SHA256,
               '; Fixed CPU=ROM; full bounded instruction candidates, no semantic correction or execution proof.']
    for window in report['windows']:
        listing.append('; [%06x,%06x) SHA256 %s; firstRTS does not truncate.' % (
            window['start_cpu_address'], window['end_cpu_address_exclusive'], window['raw_sha256']))
        listing.append(asm(window['instructions']))
    listing.append('; Literal asymmetric instruction evidence only.')
    for row in report['literal_asymmetric_evidence']:
        listing.append('; '+row['note'])
        listing.append(asm([row['instruction']]))
    listing_path.write_text('\n'.join(listing)+'\n')
    motion = report['motion_word_at_4_inventory']
    print(json.dumps(dict(windows=report['window_count'], rows=report['instruction_row_count'],
        undecoded=report['undecoded_row_count'], gaps=report['gap_count'],
        per_window=[dict(start_cpu_address=w['start_cpu_address'], rows=w['instruction_row_count'],
            raw_sha256=w['raw_sha256']) for w in report['windows']],
        literal_evidence_instructions=len(report['literal_asymmetric_evidence']),
        motion_resources=motion['resource_count'], motion_records=motion['ordinary_record_count'],
        report_sha256=sha(path.read_bytes()), asm_sha256=sha(listing_path.read_bytes()))))


if __name__ == '__main__':
    main()
