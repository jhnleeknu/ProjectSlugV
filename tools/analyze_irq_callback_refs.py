"""Inventory fixed-ROM references to IRQ callback slots; no execution claims."""
import hashlib
import json
from pathlib import Path
import re

import capstone
from disassemble_program import disassemble_range, load_verified_program

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
FIXED_END = 0x100000
SLOTS = {0x100006: '-$7ffa(a5)', 0x10000a: '-$7ff6(a5)'}
KNOWN_WINDOWS = {
    0x236: (0x20c, 0x250, 'Previously inspected vector20c conditional instruction path.'),
    0x2b0: (0x29c, 0x2d8, 'Previously inspected vector29c conditional instruction path.'),
    0x3dd8: (0x3dcc, 0x3de6, 'Contiguous helper beginning3dce; preceding RTS at3dcc.'),
    0x3dde: (0x3dcc, 0x3de6, 'Contiguous helper beginning3dce; preceding RTS at3dcc.'),
}


def referenced_slots(instruction):
    matches = []
    for slot, relative in SLOTS.items():
        if relative in instruction.op_str:
            matches.append((slot, 'a5_relative', 'Conditional on A5=108000 unless context establishes it.'))
        for operand in instruction.op_str.split(', '):
            absolute = re.fullmatch(r'\$([0-9a-f]+)\.l', operand)
            if absolute and int(absolute.group(1), 16) & 0xffffff == slot:
                matches.append((slot, 'absolute_long', 'Explicit24-bit CPU address.'))
    return matches


def context(program, instruction):
    address = instruction.address
    known = KNOWN_WINDOWS.get(address)
    if known:
        start, end, basis = known
    else:
        start, end, basis = address, min(FIXED_END, address + instruction.size + 24), None
        for trial in range(max(0, address - 24), address + 1, 2):
            rows = disassemble_range(program, trial, end - trial, trial)
            if any(row['cpu_address'] == address and row['raw'] == instruction.bytes.hex()
                   for row in rows) and all(row['classification'] == 'candidate_instruction'
                   for row in rows if row['cpu_address'] <= address):
                start = trial
                break
    rows = disassemble_range(program, start, end - start, start)
    if not any(row['cpu_address'] == address and row['raw'] == instruction.bytes.hex() for row in rows):
        raise ValueError('Context failed to preserve instruction at %06x' % address)
    return {'start_cpu_address': start, 'start_rom_offset': start, 'end_cpu_address': end,
            'alignment_basis': basis, 'classification': 'known_local_instruction_alignment' if basis
            else 'locally_consistent_candidate_window', 'instructions': rows}


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256:
        raise ValueError('Unsupported program')
    decoder = capstone.Cs(capstone.CS_ARCH_M68K,
                          capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    candidates, initializer_refs = [], []
    for address in range(0, FIXED_END, 2):
        available = min(24, FIXED_END - address)
        window = program[address:address + available] + bytes(24 - available)
        instruction = next(decoder.disasm(window, address, count=1), None)
        if instruction is None or instruction.size > available or instruction.mnemonic == 'dc.w':
            continue
        for slot, kind, limitation in referenced_slots(instruction):
            row = {'cpu_address': address, 'rom_offset': address,
                'raw': instruction.bytes.hex(), 'mnemonic': instruction.mnemonic,
                'operands': instruction.op_str, 'slot_cpu_address': slot,
                'reference_kind': kind, 'classification': 'decoded_instruction_reference_candidate',
                'execution_observed': False, 'address_context': limitation,
                'window': context(program, instruction)}
            if address == 0x236 and kind == 'a5_relative':
                row['a5_context'] = {'value': 0x108000, 'establishing_instruction_cpu_address': 0x228,
                                     'basis': 'Preceding LEA with no intervening A5 write in local path.'}
            elif address == 0x2b0 and kind == 'a5_relative':
                row['a5_context'] = {'value_before_reference': 0x108000,
                    'establishing_instruction_cpu_address': 0x2a6,
                    'basis': 'Preceding LEA; MOVEA uses old A5 for effective address then replaces A5.'}
            else:
                row['a5_context'] = 'Unknown or unnecessary for absolute reference.'
            if address in (0x3dd8, 0x3dde):
                row['locally_derived_callback_constant'] = {
                    'value': 0x3dcc, 'register': 'a0', 'producer_cpu_address': 0x3dd4,
                    'producer_raw': program[0x3dd4:0x3dd8].hex(),
                    'producer_instruction': 'lea.l $3dcc(pc),a0',
                    'target_instruction_raw': program[0x3dcc:0x3dce].hex(),
                    'target_instruction': 'rts',
                    'classification': 'Local dataflow evidence; write execution not observed.'}
            candidates.append(row)
        if instruction.mnemonic.split('.')[0] in ('jsr', 'bsr', 'jmp', 'bra'):
            match = re.fullmatch(r'\$([0-9a-f]+)(?:\.l|\.w|\(pc\))?', instruction.op_str)
            if match and int(match.group(1), 16) & 0xffffff == 0x3dce:
                initializer_refs.append({'cpu_address': address, 'rom_offset': address,
                    'raw': instruction.bytes.hex(), 'mnemonic': instruction.mnemonic,
                    'operands': instruction.op_str, 'classification': 'decoded_direct_reference_candidate',
                    'execution_observed': False,
                    'surrounding_instructions': disassemble_range(program, 0x9de, 0x30, 0x9de)
                        if address == 0x9e4 else context(program, instruction)['instructions']})
    counts = {hex(slot): sum(row['slot_cpu_address'] == slot for row in candidates) for slot in SLOTS}
    report = {'source': source, 'decoder': 'Capstone ' + capstone.__version__, 'cpu_model': 'M68000',
        'program_code_modified': False, 'scan_rom_offset': 0, 'scan_size': FIXED_END,
        'mapping': 'Fixed ROM CPU address equals canonical decrypted program offset.',
        'aligned_starts_checked': FIXED_END // 2, 'slot_reference_counts': counts,
        'candidates': candidates, 'initializer_direct_reference_candidates': initializer_refs,
        'method': 'Decode every even fixed-ROM start with padded24-byte windows, rejecting '
            'truncated instructions. Match explicit absolute-long slot operands or A5-relative '
            'displacements. Record local alignment and register-value evidence separately.',
        'limitations': 'An aligned-start scan also decodes data and mid-instruction starts. '
            'Known local instruction alignment does not establish natural execution. Only the '
            'shown paths establish A5=108000. Dynamically calculated addresses, indirect slot '
            'writes, transformed RAM code and banked program outside the first MiB are excluded. '
            'The locally installed3dcc RTS value does not establish every runtime callback value. '
            'No original execution, IRQ timing or full handler equivalence was verified.'}
    folder = root / 'artifacts/irq_callback_refs'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    if hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Canonical program bytes changed in memory')
    print('IRQ callback slot references:', counts, '; initializer refs:', len(initializer_refs))


if __name__ == '__main__':
    main()
