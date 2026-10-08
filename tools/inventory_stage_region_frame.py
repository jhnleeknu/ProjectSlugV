"""Exact bounded original stage-region instructions, without behavior inference."""
import collections
import json
from pathlib import Path

import capstone

from disassemble_program import load_verified_program
from inventory_game_initialization import asm
from inventory_object_removal import CONTROL, target
from inventory_stage_buffer_frame import resource_fixtures
from inventory_stage_input_callbacks import bounded, require, sha
from pack_stage_input import SOURCE_SHA256

WINDOWS = ((0xb4a2a, 0xb4ab0), (0x49392, 0x493bc),
           (0x1c028, 0x1c052), (0xb481e, 0xb4850), (0x4d9d6, 0x4da08))
CONTRACT = 'docs/analysis/stage-region-frame.md'
# Opcode bytes and decoder operands only. MOVEM.W and MOVEA.W retain their
# original size suffix; CPU effects are described by the main contract.
LITERALS = (
    (0xb4a2a, '3b7c80005d48', 'move.w', '#$8000, $5d48(a5)'),
    (0xb4a4c, '4c91000f', 'movem.w', '(a1), d0-d3'),
    (0xb4a50, 'd0680042', 'add.w', '$42(a0), d0'),
    (0xb4a54, 'd2680046', 'add.w', '$46(a0), d1'),
    (0xb4a58, '48ad000f5d48', 'movem.w', 'd0-d3, $5d48(a5)'),
    (0xb4a5e, '3b7c80005d50', 'move.w', '#$8000, $5d50(a5)'),
    (0xb4a80, '4c91000f', 'movem.w', '(a1), d0-d3'),
    (0xb4a84, 'd0680042', 'add.w', '$42(a0), d0'),
    (0xb4a88, 'd2680046', 'add.w', '$46(a0), d1'),
    (0xb4a8c, '48ad000f5d50', 'movem.w', 'd0-d3, $5d50(a5)'),
    (0xb4a9c, '5310', 'subq.b', '#$1, (a0)'),
    (0xb4a9e, '5448', 'addq.w', '#$2, a0'),
    (0xb4aa6, '5310', 'subq.b', '#$1, (a0)'),
    (0xb4aa8, '5448', 'addq.w', '#$2, a0'),
    (0x49392, 'bbfc00108000', 'cmpa.l', '#$108000, a5'),
    (0x4939c, '4e4f', 'trap', '#$f'),
    (0x493a2, '02400001', 'andi.w', '#$1, d0'),
    (0x493ae, '012d568e', 'btst.l', 'd0, $568e(a5)'),
    (0x493b6, '003c0001', 'ori.b', '#$1, ccr'),
    (0x1c028, '3f00', 'move.w', 'd0, -(a7)'),
    (0x1c030, '301f', 'move.w', '(a7)+, d0'),
    (0x1c04c, '22680056', 'movea.l', '$56(a0), a1'),
    (0xb481e, '302d800e', 'move.w', '-$7ff2(a5), d0'),
    (0xb482a, '43ed5d5c', 'lea.l', '$5d5c(a5), a1'),
    (0xb482e, '45ed5d98', 'lea.l', '$5d98(a5), a2'),
    (0xb4836, '43ed5d98', 'lea.l', '$5d98(a5), a1'),
    (0xb483a, '45ed5dd4', 'lea.l', '$5dd4(a5), a2'),
    (0xb483e, '7000', 'moveq', '#$0, d0'),
    (0xb4840, 'b5c9', 'cmpa.l', 'a1, a2'),
    (0xb4846, '3280', 'move.w', 'd0, (a1)'),
    (0xb4848, 'd2fc000a', 'adda.w', '#$a, a1'),
    (0x4d9ea, '207c00000000', 'movea.l', '#$0, a0'),
    (0x4d9f2, '200e', 'move.l', 'a6, d0'),
    (0x4d9f4, '302c0006', 'move.w', '$6(a4), d0'),
    (0x4d9fc, '3040', 'movea.w', 'd0, a0'),
    (0x4da00, '2040', 'movea.l', 'd0, a0'),
    (0x4da02, '226c0008', 'movea.l', '$8(a4), a1'))


def inventory(root):
    root = Path(root).resolve()
    program, source = load_verified_program(root)
    require(source['sha256'] == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported pinned original source')
    paths = ('tools/inventory_stage_region_frame.py', 'tools/disassemble_program.py',
             'tools/inventory_stage_input_callbacks.py', 'tools/inventory_object_removal.py',
             'tools/inventory_game_initialization.py', 'tools/inventory_stage_buffer_frame.py',
             'tools/observe_scene_general_initialization.py', 'tools/pack_stage_input.py')
    provenance = [dict(file=p, sha256=sha((root/p).read_bytes())) for p in paths]
    windows = [bounded(program, a, b) for a, b in WINDOWS]
    rows = [r for w in windows for r in w['instructions']]
    require(len(rows) == 89 and sum(w['byte_count'] for w in windows) == 318
            and all(w['undecoded_row_count'] == 0 for w in windows), 'Exact five windows changed')
    indexed = {r['cpu_address']: r for r in rows}
    literals = []
    for at, raw, mnemonic, operand in LITERALS:
        row = indexed[at]
        require((row['raw'], row['mnemonic'], row['op_str']) == (raw, mnemonic, operand),
                'Literal original instruction changed at %06x' % at)
        literals.append(row)
    calls, branches = [], []
    for window in windows:
        local_addresses = {r['cpu_address'] for r in window['instructions']}
        window['rts_cpu_addresses'] = [r['cpu_address'] for r in window['instructions'] if r['mnemonic'] == 'rts']
        for row in window['instructions']:
            mnemonic = row['mnemonic'].split('.')[0]
            if mnemonic not in CONTROL:
                continue
            destination = target(row)
            require(destination is not None, 'Unexpected indirect control operand')
            item = dict(instruction=row, target_cpu_address=destination, target_rom_offset=destination)
            if mnemonic in ('jsr', 'bsr'):
                calls.append(item)
            else:
                require(destination in local_addresses, 'Branch leaves assigned window or instruction boundary')
                branches.append(item)
    require([(c['instruction']['cpu_address'], c['target_cpu_address']) for c in calls] == [
        (0xb4a32, 0x49392), (0xb4a3e, 0x1c028), (0xb4a66, 0x49392),
        (0xb4a72, 0x1c028), (0xb4aaa, 0xb481e), (0x1c02a, 0x4d9d6)], 'Direct call list changed')
    require(len(branches) == 18, 'Direct branch count changed')
    audit = resource_fixtures(root, program)
    for item in provenance:
        require(sha((root/item['file']).read_bytes()) == item['sha256'], 'Inventory dependency changed')
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Original source changed during inventory')
    return dict(schema_version=1, source=source, decoder='Capstone '+capstone.__version__,
        mapping='All five assigned instruction windows: fixed first1MiB CPU=ROM offset.',
        contract=CONTRACT, provenance=provenance, window_count=5, byte_count=318,
        row_count=89, instruction_row_count=89, undecoded_row_count=0, gap_count=0,
        windows=windows, direct_call_count=len(calls), direct_calls=calls,
        direct_branch_count=len(branches), direct_branches=branches, indirect_control_count=0,
        direct_call_target_counts=[dict(cpu_address=at, rom_offset=at, count=n)
            for at, n in sorted(collections.Counter(c['target_cpu_address'] for c in calls).items())],
        literal_opcode_evidence=literals,
        literal_list_stride=dict(first_displacement=0x5d5c, middle_displacement=0x5d98,
            end_displacement=0x5dd4, stride_bytes=10, word_store_bytes=2,
            first_span_stride_quotient=(0x5d98-0x5d5c)//10,
            second_span_stride_quotient=(0x5dd4-0x5d98)//10,
            scope='Arithmetic of checked literal LEA/ADDA.W/MOVE.W operands only; runtime effects belong to the main contract.'),
        resource_audit=audit, source_modified=False,
        scope='Bounded candidate instruction evidence and source-verified raw8 resource provenance only. '
              'First RTS does not truncate; all literal branch destinations lie at listed local instruction boundaries. '
              'TRAP15 handler is outside scope. Size suffixes and source bytes are retained without correcting decoder text. '
              'No new behavior, natural record, gameplay use, reachability, execution equivalence or complete callee closure claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    output = root/'artifacts/stage_region_frame_inventory.json'
    listing = root/'artifacts/stage_region_frame_inventory.asm'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    lines = ['; Original SHA256 '+SOURCE_SHA256, '; CPU=fixed ROM offset; bounded instruction evidence only.',
             '; Contract: '+CONTRACT+'; first RTS does not truncate; TRAP handler outside scope.']
    for window in report['windows']:
        lines.append('; [%06x,%06x) bytes=%d rows=%d SHA256=%s' % (
            window['start_cpu_address'], window['end_cpu_address_exclusive'], window['byte_count'],
            window['row_count'], window['raw_sha256']))
        lines.append(asm(window['instructions']))
    listing.write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(windows=5, bytes=318, instructions=89, gaps=0, undecoded=0,
        direct_calls=report['direct_call_count'], direct_branches=report['direct_branch_count'],
        literal_checks=len(LITERALS), resource_fixtures=3,
        json_sha256=sha(output.read_bytes()), asm_sha256=sha(listing.read_bytes()))))


if __name__ == '__main__':
    main()
