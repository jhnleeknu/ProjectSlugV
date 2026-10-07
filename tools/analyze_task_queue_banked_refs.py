"""Inventory task-registration references beyond fixed ROM; mapping unconfirmed."""
import hashlib
import json
from pathlib import Path
import re

import capstone
from disassemble_program import disassemble_range, load_verified_program

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
START, END, TARGET = 0x100000, 0x800000, 0xc64


def bounded_context(program, offset, candidate_raw=None):
    start = max(START, (offset - 24) & ~1)
    end = min(END, (offset + 32 + 1) & ~1)
    if candidate_raw is not None:
        # Search for a contiguous candidate decode that retains this exact
        # instruction start. None of these trial starts proves code alignment.
        for trial in range(start, offset + 1, 2):
            rows = disassemble_range(program, trial, end-trial, 0)
            if any(row['rom_offset'] == offset and row['raw'] == candidate_raw for row in rows):
                start = trial
                break
    rows = disassemble_range(program, start, end-start, 0)
    for row in rows:
        row['decode_coordinate_relative_to_window'] = row.pop('cpu_address')
        row['operand_coordinate_basis'] = 'PC-relative displayed addresses use synthetic window origin zero; source CPU address is unknown.'
    return {'start_rom_offset': start, 'end_rom_offset_exclusive': end,
            'raw': program[start:end].hex(), 'alignment_verified': False,
            'classification': 'bounded_candidate_decode_only', 'instructions': rows}


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256 or len(program) != END:
        raise ValueError('Unsupported canonical program revision or size')
    decoder = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    absolute, relative, literal = [], [], []
    decoded_starts, bsr_count = 0, 0
    pc_relative_counts = {'bsr': 0, 'jsr': 0, 'jmp': 0}
    bsr_ranges = {'flat_rom_offset': [0xffffff, 0], 'hypothetical_1m_window': [0xffffff, 0]}
    for offset in range(START, END, 2):
        available = min(24, END-offset)
        instruction = next(decoder.disasm(program[offset:offset+available] + bytes(24-available), offset, count=1), None)
        if instruction is None or instruction.size > available or instruction.mnemonic == 'dc.w':
            continue
        decoded_starts += 1
        mnemonic = instruction.mnemonic.split('.')[0]
        if mnemonic not in ('jsr', 'jmp', 'bsr'):
            continue
        raw = instruction.bytes.hex()
        if mnemonic == 'bsr' or instruction.bytes[:2] in (b'\x4e\xba', b'\x4e\xfa'):
            # Only the 68000 signed byte/word displacement encodings are in
            # this inventory. A synthetic CPU coordinate is never execution.
            if mnemonic != 'bsr' and instruction.size == 4:
                displacement = int.from_bytes(instruction.bytes[2:4], 'big', signed=True)
            elif instruction.size == 2:
                displacement = int.from_bytes(instruction.bytes[1:2], 'big', signed=True)
            elif instruction.size == 4 and instruction.bytes[1] == 0:
                displacement = int.from_bytes(instruction.bytes[2:4], 'big', signed=True)
            else:
                continue
            bsr_count += int(mnemonic == 'bsr')
            pc_relative_counts[mnemonic] += 1
            mappings = {'flat_rom_offset': offset,
                        'hypothetical_1m_window': 0x200000 + (offset & 0xfffff)}
            for name, hypothetical_pc in mappings.items():
                target = (hypothetical_pc+2+displacement) & 0xffffff
                bsr_ranges[name][0] = min(bsr_ranges[name][0], target)
                bsr_ranges[name][1] = max(bsr_ranges[name][1], target)
                if target == TARGET:
                    relative.append({'rom_offset': offset, 'raw': raw,
                        'mnemonic': instruction.mnemonic, 'signed_displacement': displacement,
                        'hypothetical_mapping': name, 'hypothetical_instruction_coordinate': hypothetical_pc,
                        'target_cpu_address_if_mapping_held': TARGET,
                        'classification': 'mapping_dependent_pc_relative_candidate', 'execution_observed': False,
                        'window': bounded_context(program, offset, raw)})
            continue
        match = re.fullmatch(r'\$([0-9a-f]+)\.(l|w)', instruction.op_str)
        if match is None or int(match.group(1), 16) & 0xffffff != TARGET:
            continue
        absolute.append({'rom_offset': offset, 'raw': raw,
            'mnemonic': instruction.mnemonic, 'operands': instruction.op_str,
            'target_cpu_address_encoded': TARGET, 'source_cpu_address': None,
            'classification': 'aligned_start_absolute_instruction_candidate',
            'code_alignment_verified': False, 'execution_observed': False,
            'window': bounded_context(program, offset, raw)})
    pattern, at = TARGET.to_bytes(4, 'big'), START
    while True:
        at = program.find(pattern, at, END)
        if at < 0:
            break
        literal.append({'rom_offset': at, 'raw': pattern.hex(), 'word_aligned': at % 2 == 0,
            'classification': 'exact_be32_value_candidate_only', 'source_cpu_address': None,
            'pointer_verified': False, 'execution_observed': False,
            'window': bounded_context(program, at)})
        at += 1
    folder = root / 'artifacts/task_queue_banked_refs'
    folder.mkdir(parents=True, exist_ok=True)
    report = {'source': source, 'decoder': 'Capstone '+capstone.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'scan_start_rom_offset': START, 'scan_end_rom_offset_exclusive': END,
        'scan_size': END-START, 'aligned_starts_checked': (END-START)//2,
        'non_data_word_decodes': decoded_starts, 'target_fixed_cpu_address': TARGET,
        'source_cpu_mapping': 'Unknown; every candidate source location is a ROM offset only.',
        'absolute_jsr_count': sum(row['mnemonic'].split('.')[0]=='jsr' for row in absolute),
        'absolute_jmp_count': sum(row['mnemonic'].split('.')[0]=='jmp' for row in absolute),
        'mapping_dependent_bsr_count': sum(row['mnemonic'].split('.')[0]=='bsr' for row in relative),
        'mapping_dependent_pc_relative_count': len(relative), 'decoded_pc_relative_starts_checked': pc_relative_counts, 'decoded_bsr_starts_checked': bsr_count,
        'exact_be32_value_count': len(literal),
        'absolute_instruction_candidates': absolute, 'mapping_dependent_pc_relative_candidates': relative,
        'exact_be32_value_candidates': literal,
        'hypothetical_pc_relative_target_ranges': bsr_ranges,
        'mapping_hypotheses': {
            'flat_rom_offset': 'Synthetic CPU coordinate equal to ROM offset; not a bank mapping.',
            'hypothetical_1m_window': 'Each successive 1 MiB ROM chunk independently placed at CPU 200000..2fffff only for arithmetic screening; no chunk mapping established.'},
        'bsr_distance_bound': {'source_window': [0x200000, 0x2fffff],
            'signed_word_displacement': [-32768, 32767], 'pc_displacement_base_delta': 2,
            'possible_unwrapped_target_range': [0x1f8002, 0x308000],
            'fixed_c64_outside_range': True,
            'basis': '68000 BSR signed16 cannot reach fixed c64 from CPU200000..2fffff; signed8 is narrower.'},
        'existing_document_checked': {'path': 'docs/analysis/branch-object-resources.md',
            'limitation': 'Its ROM400000 to CPU200000 statement concerns graphics-data bank interpretation; it does not establish source mapping for this program scan.'},
        'method': 'One bounded padded Capstone decode at every even ROM offset. Absolute JSR/JMP operands to fixed c64 are retained. '
            'BSR signed8/signed16 and direct PC-relative JSR/JMP signed16 targets are screened under two explicit hypothetical coordinate systems. '
            'Exact 00000c64 BE32 byte values are scanned at every byte alignment separately. Each hit retains bounded raw context and candidate disassembly.',
        'limitations': 'Even starts include data and instruction middles; plausible decoded windows are not proof of code. '
            'Absolute operands encode a target but do not prove instruction execution. Raw BE32 matches are not established pointers. '
            'Unknown bank mappings prevent confirmed BSR callsites and source CPU addresses. Indirect calls, register-computed targets, '
            'RAM-transformed code, actual task handler identities and execution are not established.'}
    path = folder / 'report.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    assert hashlib.sha256(program).hexdigest() == PROGRAM_SHA256
    print(json.dumps({'absolute_jsr': report['absolute_jsr_count'], 'absolute_jmp': report['absolute_jmp_count'],
        'hypothetical_pc_relative': len(relative), 'raw_be32': len(literal),
        'report_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
