"""Inventory fixed-ROM direct task-helper calls without claiming execution."""
import hashlib
import json
from pathlib import Path
import re

import capstone
from disassemble_program import disassemble_range, load_verified_program

PROGRAM_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
FIXED_END = 0x100000
TARGETS = {0xc64: 'task-registration', 0xc42: 'task-initialization', 0xc8c: 'task-service'}
# These anchors were already inspected as contiguous instruction streams in
# the repository analysis. They establish local alignment, not execution.
KNOWN_WINDOWS = {
    0x23c: (0x224, 0x256, 'docs/analysis/input-status.md; vector20c path'),
    0xa08: (0x9de, 0xa0e, 'docs/analysis/object-dispatch.md; initialization calls'),
}


def direct_target(instruction):
    if instruction.mnemonic.split('.')[0] not in ('jsr', 'bsr'):
        return None
    operand = re.fullmatch(r'\$([0-9a-f]+)(?:\.l|\.w|\(pc\))?', instruction.op_str)
    if operand is None:
        return None
    target = int(operand.group(1), 16) & 0xffffff
    return target if target in TARGETS else None


def candidate_window(program, instruction):
    address = instruction.address
    known = KNOWN_WINDOWS.get(address)
    if known is not None:
        start, end, basis = known
    else:
        start, end, basis = address, min(FIXED_END, address + instruction.size + 24), None
        # Pick a surrounding contiguous decode that reaches this exact call.
        # This is local decoding consistency only; its start is not a proven
        # routine boundary and a data stream can also satisfy this condition.
        for trial in range(max(0, address - 24), address + 1, 2):
            trial_rows = disassemble_range(program, trial, end - trial, trial)
            if any(row['cpu_address'] == address and row['raw'] == instruction.bytes.hex()
                   for row in trial_rows) and all(row['classification'] == 'candidate_instruction'
                   for row in trial_rows if row['cpu_address'] <= address):
                start = trial
                break
    rows = disassemble_range(program, start, end - start, start)
    matching = [row for row in rows if row['cpu_address'] == address and
                row['raw'] == instruction.bytes.hex()]
    if len(matching) != 1:
        raise ValueError('Window does not preserve the candidate call at %06x' % address)
    return {'start_cpu_address': start, 'start_rom_offset': start,
            'end_cpu_address': end, 'anchor_basis': basis,
            'classification': 'previously_inspected_contiguous_code_window' if basis else
                              'locally_consistent_candidate_decode_window',
            'instructions': rows}


def literal_hits(program, target):
    pattern = target.to_bytes(4, 'big')
    result, at = [], 0
    while True:
        at = program.find(pattern, at, FIXED_END)
        if at < 0:
            return result
        result.append({'rom_offset': at, 'cpu_address': at,
            'raw': pattern.hex(), 'word_aligned': at % 2 == 0,
            'classification': 'raw_value_match_only',
            'limitation': 'Not a decoded call, pointer classification, or execution evidence.'})
        at += 1


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != PROGRAM_SHA256:
        raise ValueError('Unsupported program')
    decoder = capstone.Cs(capstone.CS_ARCH_M68K,
                          capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    candidates, decoded_starts = [], 0
    for address in range(0, FIXED_END, 2):
        available = min(24, FIXED_END - address)
        window = program[address:address + available] + bytes(24 - available)
        instruction = next(decoder.disasm(window, address, count=1), None)
        if instruction is None or instruction.size > available or instruction.mnemonic == 'dc.w':
            continue
        decoded_starts += 1
        target = direct_target(instruction)
        if target is None:
            continue
        candidates.append({'cpu_address': address, 'rom_offset': address,
            'raw': instruction.bytes.hex(), 'mnemonic': instruction.mnemonic,
            'operands': instruction.op_str, 'target_cpu_address': target,
            'target_id': TARGETS[target], 'classification': 'decoded_direct_call_candidate',
            'execution_observed': False, 'window': candidate_window(program, instruction)})
    counts = {hex(target): sum(row['target_cpu_address'] == target for row in candidates)
              for target in TARGETS}
    folder = root / 'artifacts/task_queue_callers'
    folder.mkdir(parents=True, exist_ok=True)
    report = {'source': source, 'decoder': 'Capstone ' + capstone.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'scan_rom_offset': 0, 'scan_size': FIXED_END,
        'mapping': 'Fixed ROM CPU address equals canonical decrypted program offset.',
        'aligned_starts_checked': FIXED_END // 2,
        'non_data_word_decodes': decoded_starts,
        'target_counts': counts, 'candidates': candidates,
        'raw_long_value_matches': {hex(target): literal_hits(program, target) for target in TARGETS},
        'method': 'Decode one instruction at every even fixed-ROM address with a padded24-byte '
            'window and reject truncation. Retain direct JSR/BSR targets after24-bit address '
            'normalization; inspect contiguous context and known local anchors separately. '
            'Inventory literal long values separately without treating them as calls.',
        'finding': 'No direct JSR/BSR candidate to c64 in the fixed first MiB. '
            'c42 and c8c have one candidate each in previously inspected code windows.',
        'limitations': 'Every aligned-start scanning includes data and mid-instruction starts. '
            'Contiguous decode and known local alignment do not prove natural reachability. '
            'Indirect calls, references through jump stubs, transformed RAM code, banked code '
            'outside the fixed first MiB, interrupt arrival, and actual deferred handler '
            'identities are not established. No original execution was performed.'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    if hashlib.sha256(program).hexdigest() != PROGRAM_SHA256:
        raise ValueError('Canonical program bytes changed in memory')
    print('Fixed-ROM task helper call candidates:', counts)


if __name__ == '__main__':
    main()
