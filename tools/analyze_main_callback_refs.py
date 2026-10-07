"""Inventory candidate fixed-ROM object+0x76(A6) references, without execution claims."""
import hashlib
import json
from pathlib import Path
import re

import capstone
from disassemble_program import disassemble_range, load_verified_program

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
FIXED_END = 0x100000
SLOT_OPERAND = '$76(a6)'


def bounded_context(program, instruction):
    address = instruction.address
    end = min(FIXED_END, address + instruction.size + 24)
    if address == 0xf30:
        start = 0xf24
        basis = 'Known f30 callback-slot read anchor; contiguous local f24..f44 instructions.'
    else:
        start = address
        basis = 'Locally consistent decode only; predecessor execution/alignment unknown.'
        for trial in range(max(0, address - 24), address + 1, 2):
            rows = disassemble_range(program, trial, end - trial, trial)
            if any(row['cpu_address'] == address and row['raw'] == instruction.bytes.hex()
                   for row in rows) and all(row['classification'] == 'candidate_instruction'
                   for row in rows if row['cpu_address'] <= address):
                start = trial
                break
    rows = disassemble_range(program, start, end - start, start)
    if not any(row['cpu_address'] == address and row['raw'] == instruction.bytes.hex()
               for row in rows):
        raise ValueError('Context lost candidate at %06x' % address)
    return {'start_cpu_address': start, 'start_rom_offset': start,
            'end_cpu_address_exclusive': end, 'alignment_basis': basis, 'instructions': rows}


def instruction_record(instruction):
    return {'cpu_address': instruction.address, 'rom_offset': instruction.address,
            'raw': instruction.bytes.hex(), 'size': instruction.size,
            'mnemonic': instruction.mnemonic, 'operands': instruction.op_str,
            'classification': 'decoded_instruction_candidate', 'execution_observed': False,
            'false_positive_possible': True}


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256 or len(program) < FIXED_END:
        raise ValueError('Unsupported canonical program')
    decoder = capstone.Cs(capstone.CS_ARCH_M68K,
                          capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    candidates, direct_references, immediate_values = [], [], set()
    decoded_count = 0
    for address in range(0, FIXED_END, 2):
        available = min(24, FIXED_END - address)
        window = program[address:address + available] + bytes(24 - available)
        instruction = next(decoder.disasm(window, address, count=1), None)
        if instruction is None or instruction.mnemonic == 'dc.w' or instruction.size > available:
            continue
        decoded_count += 1
        operands = [operand.strip() for operand in instruction.op_str.split(',')]
        mnemonic = instruction.mnemonic.split('.')[0]
        if SLOT_OPERAND in operands:
            row = instruction_record(instruction)
            row['slot_displacement'] = 0x76
            row['base_register'] = 'a6'
            row['absolute_slot_address'] = None
            row['address_context'] = 'A6 object address is unknown unless established by separate analysis.'
            row['window'] = bounded_context(program, instruction)
            if mnemonic == 'lea':
                row['access_candidate'] = 'effective_address_only'
            elif mnemonic in ('move', 'movea'):
                row['access_candidate'] = 'write' if operands[-1] == SLOT_OPERAND else 'read'
            elif mnemonic in ('cmp', 'cmpa', 'tst', 'btst'):
                row['access_candidate'] = 'read'
            elif mnemonic == 'clr':
                row['access_candidate'] = 'write'
            else:
                row['access_candidate'] = 'other_or_read_modify_write'
            if instruction.mnemonic == 'move.l' and operands[-1] == SLOT_OPERAND:
                immediate = re.fullmatch(r'#\$([0-9a-f]+)', operands[0])
                if immediate:
                    value = int(immediate.group(1), 16)
                    row['immediate_callback_constant_candidate'] = value
                    immediate_values.add(value)
                else:
                    row['callback_source_operand'] = operands[0]
                    row['callback_source_value'] = 'Unknown; no register dataflow inferred.'
            candidates.append(row)
        # Operand rendering gives the computed CPU target for direct branches/calls.
        if mnemonic in ('jsr', 'jmp') or mnemonic.startswith('b') or mnemonic.startswith('db'):
            target = re.fullmatch(r'\$([0-9a-f]+)(?:\.l|\.w|\(pc\))?', operands[-1])
            if target and (mnemonic in ('jsr', 'jmp', 'bra', 'bsr') or
                           mnemonic.startswith('db') or mnemonic in
                           ('bhi', 'bls', 'bcc', 'bcs', 'bne', 'beq', 'bvc', 'bvs',
                            'bpl', 'bmi', 'bge', 'blt', 'bgt', 'ble')):
                direct_references.append((int(target.group(1), 16) & 0xffffff, instruction))
    anchor = [row for row in candidates if row['cpu_address'] == 0xf30]
    if len(anchor) != 1 or anchor[0]['raw'] != '206e0076' or anchor[0]['access_candidate'] != 'read':
        raise ValueError('Known f30 read anchor missing')
    users = []
    for value in sorted(immediate_values):
        matches = []
        for target, instruction in direct_references:
            if target == (value & 0xffffff):
                row = instruction_record(instruction)
                row['window'] = bounded_context(program, instruction)
                matches.append(row)
        users.append({'callback_constant_candidate': value,
                      'target_cpu_address_24bit': value & 0xffffff,
                      'direct_target_users': matches,
                      'meaning_confirmed': False})
    counts = {}
    for row in candidates:
        kind = row['access_candidate']
        counts[kind] = counts.get(kind, 0) + 1
    report = {'schema_version': 1, 'source': source,
        'decoder': {'name': 'Capstone', 'version': capstone.__version__, 'cpu_model': 'M68000'},
        'program_code_modified': False, 'scan_rom_offset': 0, 'scan_size': FIXED_END,
        'mapping': 'First1MiB fixed ROM CPU address equals canonical decrypted file offset; no bank remapping.',
        'aligned_starts_checked': FIXED_END // 2, 'decoded_candidate_count': decoded_count,
        'slot_reference_count': len(candidates), 'access_candidate_counts': counts,
        'known_read_anchor_cpu_address': 0xf30, 'candidates': candidates,
        'immediate_callback_constants_and_direct_target_users': users,
        'method': 'Independently decode every even start with padded24-byte windows, reject truncated '
                  'instructions, match exact $76(a6) operand; enumerate immediate MOVE.L constants '
                  'and direct branch/call references to their24-bit targets.',
        'limitations': 'Data and starts inside instructions can decode as false positives. Local '
                      'alignment does not prove execution. Access types and immediate callback values '
                      'are candidates only; object identity, register-source values, indirect target '
                      'users, banked code, RAM-transformed code and alias-based writes are not resolved. '
                      'No runtime execution was observed and no callback meaning is confirmed.'}
    folder = root / 'artifacts/main_callback_refs'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / 'report.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    if hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Canonical program bytes changed in memory')
    print(json.dumps({'source_sha256': source['sha256'], 'slot_reference_count': len(candidates),
                      'access_candidate_counts': counts, 'immediate_constant_count': len(users),
                      'direct_target_user_count': sum(len(row['direct_target_users']) for row in users),
                      'report_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
