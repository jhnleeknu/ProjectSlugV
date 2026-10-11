"""480bc frame helper bundle U1 (47642/6f1c2/b4a2a/4701e/46f52/2efa6/3c44 and callees) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an immutable
input (this verifier never invokes the observer main). Start states are the stage-frame seeds
declared by the observation: they are reconstructed here from tools/verify_stage_frame.py smoke()
and artifacts/stage_frame (never copied from the observation) and asserted equal to the recorded
seed SHAs, fixture RAM/PVC SHAs, registers and bank state. C++ resumes only from the previous
actual C++ output plus the host changes recorded in the native step (declared PC redirect, return
LONG and RAM fixtures). 1a73c/49b0c/4aa88/e8a48 and 4939c (TRAP #f) have no native instructions in this observation
(boundary stops there; later units execute 1a73c/49b0c/4aa88/e8a48 in the final state, see superseded_negatives); 4939c (TRAP #f) stays a stop boundary. Native SR is never read: C is a source-opcode classification.
"""
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
import verify_stage_frame as vsf
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_frame_helpers_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_frame_helpers_native'
NATIVE_SHA = 'bf7525b04f9735da44958b24fdf9be2f7d67b7f80fd7b53015b0c7645a949916'
NATIVE_TOOL_SHA = '7c6c65e09a2ffea2fc436086a441d7aa158b267df4c1f429a432161acc4a31d2'
CONTRACT_SHA = '785c3fba8bf05bd405ad8c0898738504367ed0c3195ffb9aa80a0a3774c861e0'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
M32 = 0xffffffff
S = 0x1feffc
ENTRY = 0x480bc
A5V = 0x108000
B1A73C, B49B0C, B4AA88, BE8A48, T4939C = 0x1a73c, 0x49b0c, 0x4aa88, 0xe8a48, 0x4939c
BOUNDARY_PCS = (B1A73C, B49B0C, B4AA88, BE8A48, T4939C)
CONSUMERS = {0x4765c: (0x47670, 0x47660), 0xb4a38: (0xb4a5e, 0xb4a3c), 0xb4a6c: (0xb4a92, 0xb4a70)}
NEW_RANGES = ((0x480bc, 0x480f2), (0x47642, 0x47672), (0x6f1c2, 0x6f1c4), (0x2efa6, 0x2efdc), (0x3c44, 0x3c7c),
              (0xb4a2a, 0xb4ab0), (0x49392, 0x4939c), (0x4939e, 0x493bc), (0x1c028, 0x1c052), (0x4d9d6, 0x4da08),
              (0xb481e, 0xb4850), (0x4701e, 0x4706c), (0x46f52, 0x4701e))
EXISTING_RANGES = ((0x289e, 0x28ae), (0x3ac8, 0x3c08), (0x43e38, 0x43ea4))
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_FRAME = 'unsupported animation frame helper PC'
UNKNOWN_CARRY = 'frame helper caller requires known carry'
WRITE_DEVICE = 'unsupported animation machine write device'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
FLOW_ONLY = cc.FLOW_ONLY
CARRY_NAME = cc.CARRY_NAME
sha = cc.sha


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def load_rows(report):
    rows = []
    for row in report['results'] + report['guarded_results']:
        for kind in ('phases', 'continuous_control'):
            for phase in row[kind]:
                data = {}
                for name, expected in phase['artifacts'].items():
                    value = (NATIVE_DIR / name).read_bytes()
                    assert sha(value) == expected, name
                    data[name.rsplit('phase_%03d_' % phase['index'], 1)[1]] = value
                phase['_data'] = data
                phase['_trace'] = json.loads(data['trace.json'])
                for snapshot in phase['snapshots']:
                    snapshot['_ram'] = (NATIVE_DIR / snapshot['artifacts']['ram']).read_bytes()
                    snapshot['_pvc'] = (NATIVE_DIR / snapshot['artifacts']['pvc']).read_bytes()
                    assert sha(snapshot['_ram']) == phase['artifacts'][snapshot['artifacts']['ram']]
                    assert sha(snapshot['_pvc']) == phase['artifacts'][snapshot['artifacts']['pvc']]
        rows.append(row)
    return rows


def static_blocks(instructions, starts):
    """Block extents from the original opcodes: a block ends at RTS/BRA/JMP, a conditional branch, JSR/BSR or the next start."""
    addrs = sorted(instructions)
    nxt = {a: b for a, b in zip(addrs, addrs[1:])}
    blocks = {}
    for start in starts:
        pcs = []
        pc = start
        while True:
            item = instructions[pc]
            pcs.append(pc)
            name = item['mnemonic'].split('.')[0]
            end = (name in ('rts', 'bra', 'jmp', 'jsr', 'bsr') or name.startswith('b') and name not in ('btst', 'bset', 'bclr', 'bchg')
                   or name.startswith('db'))
            following = pc + item['size']
            if end or following in starts or following not in instructions:
                break
            pc = following
        blocks[start] = pcs
    return blocks


def classify_carry(instructions, carry, pcs):
    """Source-opcode C classification (no native SR): ORI/ANDI CCR and ANDI.W #1,D0 at 493a2 only (contract: the 49392 return C; an AND always clears C,
    but every other ANDI.W is conservatively Unknown in the C++)
    are known; the 289e branch-taken equal compare (CMPI.L then BEQ to 28ac) cannot borrow, so C is Clear
    there and Set on the ORI path; flow-only opcodes preserve; anything else makes C Unknown."""
    for index, pc in enumerate(pcs):
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        if name == 'ori' and item['op_str'] == '#$1, ccr':
            carry = 2
        elif name == 'andi' and item['op_str'] == '#$fe, ccr':
            carry = 1
        elif pc == 0x493a2 and item['mnemonic'] == 'andi.w' and item['op_str'] == '#$1, d0':
            carry = 1
        elif pc == 0x289e:
            carry = 0
        elif pc == 0x28a4 and index + 1 < len(pcs) and pcs[index + 1] == 0x28ac and carry == 0:
            carry = 1
        elif name in FLOW_ONLY:
            pass
        else:
            carry = 0
    return carry


def audit_native(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_frame_helpers.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-frame-helpers-u1-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    assert source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin',
                'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['declared_register_changes_at_step_boundaries'] == []
    assert report['rom_stat_start'] == report['rom_stat_end']
    refs = helpers.audit_references(ROOT, NATIVE_DIR, report)
    refs[str(path.resolve())] = NATIVE_SHA
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(report['oracle']['library']) == report['oracle']['library_sha256']
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    assert sorted(tuple(r) for r in static['new_ranges']) == sorted(NEW_RANGES) == sorted(tuple(r) for r in report['new_ranges'])
    assert sorted(tuple(r) for r in static['existing_ranges']) == sorted(EXISTING_RANGES)
    assert sorted(report['boundary_stop_pcs']) == [B1A73C, T4939C]
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        assert at == instruction['cpu_address']          # fixed CPU address == file offset
        instructions[instruction['cpu_address']] = instruction
    for pc in (B1A73C, B49B0C, B4AA88, BE8A48, T4939C):
        assert pc not in instructions
    starts = sorted(b for b in report['block_starts'] if in_ranges(b, NEW_RANGES))
    assert len(starts) == 106 and len(set(starts)) == 106
    all_starts = set(report['block_starts'])
    # independent re-derivation of the leaders from the original opcodes (range starts, branch/call targets, successors)
    derived = set(low for low, _ in NEW_RANGES if low != 0x4939e)
    derived.add(0x4939e)
    for pc, item in instructions.items():
        if not in_ranges(pc, NEW_RANGES):
            continue
        name = item['mnemonic'].split('.')[0]
        target = re.search(r'\$([0-9a-f]+)$', item['op_str'])
        if name in ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble', 'bra',
                    'bsr', 'jsr', 'dbra', 'dbf') and target:
            derived.add(int(target.group(1), 16))
        if name in ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble',
                    'bsr', 'jsr', 'dbra', 'dbf') or item['mnemonic'] == 'jsr.l':
            derived.add(pc + item['size'])
    derived = set(pc for pc in derived if in_ranges(pc, NEW_RANGES))
    missing = sorted(set(starts) - derived)
    extra = sorted(derived - set(starts))
    covered = set(report['covered_PCs'])
    uncovered = sorted(set(starts) - covered)
    assert uncovered == [0x480c6, 0x480cc, 0x480d2, 0x480ea], [hex(p) for p in uncovered]   # shell returns after the boundary calls: never executed natively
    rows = load_rows(report)
    assert len(rows) == report['cases'] + report['guarded_cases'] == 199 and report['cases'] == 182 and report['guarded_cases'] == 17
    split_count = sum(len(r['phases']) for r in rows)
    control_count = sum(len(r['continuous_control']) for r in rows)
    assert (split_count, control_count) == (report['total_split_phases'], report['total_control_phases']) == (3753, 199)
    assert report['fresh_CPU_runs'] == 995
    program_reads = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    for row in rows:
        assert row['reproduced_twice'] and row['continuous_split_equivalent']
        assert bool(row['guarded']) == (row['group'] == 'guard' or row['label'].startswith('guard-'))
        fx = row['fixture']
        for kind in ('phases', 'continuous_control'):
            counts = cc.audit_program_reads(program, fx, row[kind])
            if kind == 'phases':
                for key, value in counts.items():
                    program_reads[key] += value
        cc.audit_split_control(row)
        for phase in row['phases'] + row['continuous_control']:
            assert phase['carry'] is None and not phase['branch_evidence']
            assert phase['counts']['external_reads'] == sum(e['region'] == 'external' for e in phase['_trace']['events'])
            ports = [e for e in phase['_trace']['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
            assert phase['_data']['ports.bin'] == b''.join(
                struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports)
            executed = set(phase['_trace']['pcs'][:-1])
            assert not (executed & set(BOUNDARY_PCS)) and instructions.keys() >= executed
    return report, rows, refs, instructions, program_reads, control_count, starts, missing, extra, all_starts, uncovered


def rebuild_seeds():
    """Seeds from verify_stage_frame.smoke() and artifacts/stage_frame, never from the observation."""
    ver_path = ROOT / 'artifacts/stage_frame/verification.json'
    ver = json.loads(ver_path.read_text())
    by_label = {r['label']: r for r in ver['results']}
    order = [r['label'] for r in ver['results']]
    seeds = {}
    files = {str(ver_path): cc.digest(ver_path)}

    def page(bank):
        data = bytearray(8192)
        data[0x1ff0:0x1ff2] = (0xa0).to_bytes(2, 'big')
        data[0x1ff2:0x1ff4] = (0x1000 if bank == 2 else 0x2000).to_bytes(2, 'big')
        return bytes(data)

    def make(name, ram, regs14, bank, source):
        raw_sha = sha(bytes(ram))
        ram = bytearray(ram)
        ram[S & 0xffff:(S & 0xffff) + 4] = (0x2ac2).to_bytes(4, 'big')        # declared return LONG at the initial A7
        regs = dict((k, v & M32) for k, v in zip(vsf.KEYS, regs14))
        regs['a5'] = A5V
        seeds[name] = dict(ram=bytes(ram), pvc=page(bank), regs=regs, bank_state=((0x200000 if bank == 2 else 0x300000), 0xa0, 0x1000 if bank == 2 else 0x2000),
                           source=source, bank=bank, raw_sha=raw_sha)

    for idx, bank in ((0, 2), (4, 2), (4, 3), (25, 2), (25, 3), (34, 2), (34, 3)):
        ram, regs, _changes = vsf.smoke(ROOT, idx)
        label = 'verified-seed-smoke' if idx == 0 else 'verified-initializer-seed%d-bank%d' % (idx, bank)
        assert sha(bytes(ram)) == by_label[label]['input_sha256']
        assert [regs[i] for i in range(14)] == [by_label[label]['incoming'][k] for k in vsf.KEYS]
        make('seed%d-bank%d' % (idx, bank), ram, regs, bank, 'vsf.smoke(%d)' % idx)
    for label in ('verified-seed-smoke', 'actual-CLI-output-carried-smoke-5', 'actual-CLI-output-carried-smoke-15',
                  'actual-CLI-carried-seed4-bank3-frame3'):
        row = by_label[label]
        path = ROOT / 'artifacts/stage_frame' / row['ram_file']
        data = path.read_bytes()
        assert sha(data) == row['ram_sha256'] and len(data) == 65536
        res = row['result']
        assert res['stage'] == 0 and all(res[x] == 0 for x in ('buffer_phase', 'sound_kind', 'sound_phase'))
        name = 'after-%s' % label.replace('actual-CLI-output-carried-', '').replace('actual-CLI-carried-', '').replace(
            'verified-seed-smoke', 'seed0-smoke-frame0')
        make(name, data, [res[k] for k in vsf.KEYS], res['bank'], str(path))
        files[str(path)] = cc.digest(path)
    return seeds, files


def start_of_row(row, seeds):
    """C++ start: reconstructed seed + the row's declared register/A7/external overrides; every part asserted vs the record."""
    fx = row['fixture']
    matches = [n for n, s in seeds.items() if sha(s['ram']) == fx['initial_RAM_sha256'] and
               sha(s['pvc']) == fx['initial_PVC_sha256'] and tuple(s['bank_state']) == tuple(fx['bank_state'])]
    assert len(matches) == 1, (row['label'], matches)
    name = matches[0]
    seed = seeds[name]
    prov = report_seed_provenance[name]
    assert fx['seed'] == prov, (row['label'], name)
    assert fx['entry_pc'] == ENTRY and fx['stop_pc'] == ENTRY and fx['checkpoints'] == []
    regs = dict(seed['regs'])
    declared = {}
    for key, want in fx['initial_regs'].items():
        if regs[key] != want:
            declared[key] = (regs[key], want)
            regs[key] = want
    assert set(fx['initial_regs']) == set(regs)
    a7 = fx['initial_a7']
    if a7 != S:
        declared['a7'] = (S, a7)
    state = dict(regs, a7=a7, pc=ENTRY, carry=0)
    return name, seed['ram'], state, seed['pvc'], seed['bank_state'][0], declared


report_seed_provenance = {}
PROBES = True            # debug switch of the development harness only; the reported run always has it on


def apply_changes(ram, state, changes, entry):
    ram = bytearray(ram)
    state = dict(state)
    kinds = []
    for change in changes:
        kind = change['kind']
        assert change['pc_before'] == entry['pc'] and change['a7_before'] == entry['a7'], change
        if kind == 'ram':
            at, size = change['address'] & 65535, change['size']
            assert 0 <= at <= 65536 - size
            common.native.put(ram, change['address'], size, change['value'])
        elif kind == 'pc':
            state['pc'] = change['to']
        else:
            raise AssertionError(kind)
        kinds.append(kind)
    return bytes(ram), state, kinds


# The reviewed 289e executor returns C directly from its entry block: the original RTS at 28ac (and the ORI path
# at 28a8) are never a separate C++ block, so the native split stops there are merged into the next phase.
ATOMIC_INTERNAL_STOPS = (0x28a8, 0x28ac)


def merge_phases(phases):
    groups, pending = [], []
    for phase in phases:
        pending.append(phase)
        if phase['stop_pc'] in ATOMIC_INTERNAL_STOPS and phase['guard'] is None:
            continue
        if len(pending) == 1:
            groups.append(phase)
        else:
            first, last = pending[0], pending[-1]
            merged = dict(first, stop_pc=last['stop_pc'], outgoing=last['outgoing'], modeled_bank=last['modeled_bank'],
                          guard=last['guard'], ff8_after=last['ff8_after'], ff9_after=last['ff9_after'])
            pcs, events = [], []
            for part in pending:
                pcs.extend(part['_trace']['pcs'][:-1])
                events.extend(part['_trace']['events'])
            pcs.append(last['_trace']['pcs'][-1])
            merged['_trace'] = dict(last['_trace'], pcs=pcs, events=events)
            merged['_data'] = dict(first['_data'], **{k: last['_data'][k] for k in ('ram_after.bin', 'pvc_after.bin')})
            merged['_data']['ports.bin'] = b''.join(part['_data']['ports.bin'] for part in pending)
            groups.append(merged)
        pending = []
    assert not pending
    return groups


def check_result(actual, n, pvc, bank, portbytes, waiting):
    """common.check_result with the status rule of this unit: the 3aea split stop is a checkpoint, not a wait, unless the native phase recorded waiting."""
    result, ram, device, ports, error = actual
    assert result['ok'] and not error
    assert {k: result[k] for k in common.REGS + ('pc',)} == n['outgoing'], {
        k: (n['outgoing'][k], result[k]) for k in common.REGS + ('pc',) if result[k] != n['outgoing'][k]}
    assert result['status'] == (1 if waiting else 0), (result['status'], waiting)
    if result['status'] == 1:
        assert result['carry'] == 0
    reads = sum(e['access'] == 'read' and e['address'] == 0xd00046 and e['size'] == 1 for e in n['events'])
    assert result['external_reads'] == reads and result['bank_base'] == bank, (reads, result['external_reads'], bank, result['bank_base'])
    assert ram == n['ram_after'], [(i, n['ram_after'][i], ram[i]) for i in range(len(ram)) if ram[i] != n['ram_after'][i]][:20]
    assert device == pvc, 'PVC mismatch'
    assert ports == portbytes, ('ports', ports.hex(), portbytes.hex())


def compare(exe, rows, resources, instructions, seeds, block_starts, carry_preserving):
    out_rows = []
    totals = dict(cases=0, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0,
                  carry_probe_preserved=0, consumer_flip_checks=0, declared_register_rows=0,
                  declared_host_changes=dict(ram=0, pc=0), guard_rows=0,
                  native_phases_merged_into_atomic_callee_returns=0)
    guards = []
    starts_by_label = {}
    carry_hist = {0: 0, 1: 0, 2: 0}
    single_block = {}
    consumer_phases = set()
    for row in rows:
        fx = row['fixture']
        seed_name, ram, state, pvc, bank, declared = start_of_row(row, seeds)
        if declared:
            totals['declared_register_rows'] += 1
        expected_pvc, expected_bank = pvc, bank
        results = []
        step_start = None
        merged = merge_phases(row['phases'])
        totals['native_phases_merged_into_atomic_callee_returns'] += len(row['phases']) - len(merged)
        for j, phase in enumerate(merged):
            data = phase['_data']
            entry = dict(pc=state['pc'], a7=state['a7'])
            ram, state, kinds = apply_changes(ram, state, phase['host_changes'], entry)
            for kind in kinds:
                totals['declared_host_changes'][kind] += 1
            assert kinds == [c['kind'] for c in phase['host_changes']]
            if j == 0:
                step_start = (ram, dict(state), pvc, bank)
                starts_by_label[row['label']] = step_start
            else:
                assert not phase['host_changes']
            if phase['guard'] is not None:
                assert j == len(merged) - 1 and row['guarded']
                assert ram == data['ram_before.bin']
                assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
                guards.append((row, phase, ram, dict(state), pvc, bank, step_start))
                break
            assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
            assert ram == data['ram_before.bin'], (row['label'], j)
            assert bank == phase['bank_before']
            events = phase['_trace']['events']
            expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
            assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
            phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
            actual = common.invoke(exe, OUT, 'c%03d_split_%03d' % (row['index'], j), ram, state, pvc, bank,
                                   resources, stop=phase['stop_pc'], external=fx['external'])
            assert actual[0]['ok'] and not actual[4], (row['label'], j, hex(phase['stop_pc']), actual[4])
            check_result(actual, dict(outgoing=phase['outgoing'], events=events, ram_after=data['ram_after.bin']),
                         expected_pvc, expected_bank, portbytes, phase['waiting'])
            result, ram, pvc, _, _ = actual
            executed = phase['_trace']['pcs'][:-1]
            want_carry = classify_carry(instructions, state['carry'], executed)
            assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']), result['carry'], want_carry)
            carry_hist[result['carry']] += 1
            first = executed[0] if executed else None
            if first in CONSUMERS:
                consumer_phases.add(first)
                # a consumer reads the modeled C: the flipped known C selects the other branch and changes nothing else
                clear_pc, set_pc = CONSUMERS[first]
                assert phase_in['carry'] in (1, 2), (row['label'], j)
                flipped = 3 - phase_in['carry']
                other = clear_pc if flipped == 1 else set_pc
                again = common.invoke(exe, OUT, 'c%03d_flip_%03d' % (row['index'], j), data['ram_before.bin'],
                                      dict(phase_in, carry=flipped), phase_pvc, phase_bank, resources,
                                      stop=other, external=fx['external'])
                assert again[0]['ok'] and not again[4] and again[0]['pc'] == other, (row['label'], j)
                assert again[1] == data['ram_before.bin'] and again[2] == phase_pvc
                assert again[0]['carry'] == flipped
                totals['consumer_flip_checks'] += 1
            elif PROBES:
                for probe in (1, 2):
                    again = common.invoke(exe, OUT, 'c%03d_carry%d_%03d' % (row['index'], probe, j), data['ram_before.bin'],
                                          dict(phase_in, carry=probe), phase_pvc, phase_bank, resources,
                                          stop=phase['stop_pc'], external=fx['external'])
                    assert again[0]['ok'] and not again[4], (row['label'], j, probe)
                    assert again[0]['carry'] == classify_carry(instructions, probe, executed), (row['label'], j, probe, again[0]['carry'])
                    assert ({k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in result.items() if k != 'carry'})
                    assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                    totals['carry_probes'] += 1
                    totals['carry_probe_preserved'] += again[0]['carry'] == probe
                    blocks = [pc for pc in executed if pc in block_starts]
                    if len(blocks) == 1 and blocks[0] == first and not in_ranges(first, EXISTING_RANGES):
                        single_block.setdefault(first, {})[probe] = again[0]['carry'] == probe
            totals['carry_checks'] += 1
            state = {k: result[k] for k in common.STATE_KEYS}
            bank = result['bank_base']
            totals['reads'] += result['external_reads']
            totals['ports'] += len(portbytes) // 9
            totals['resumes'] += 1 if j else 0
            results.append(dict(step=phase['step'], stop_pc=phase['stop_pc'], carry=CARRY_NAME[result['carry']],
                                actual_previous_outputs_used=bool(j), full_RAM_16R_PC_PVC_bank_ports_status_reads_equal=True))
            if j == len(merged) - 1:
                last = (ram, dict(state), pvc, bank)
        # continuous control: one C++ run from the step start must equal the split chain and the native control
        control_rows = 0
        for phase in row['continuous_control']:
            if phase['guard'] is not None:
                continue
            c_ram, c_state, c_pvc, c_bank = step_start
            data = phase['_data']
            assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
            e_pvc, e_bank, portbytes = cc.fold_outputs(c_pvc, c_bank, phase['_trace']['events'])
            assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
            actual = common.invoke(exe, OUT, 'c%03d_control' % row['index'], c_ram, c_state, c_pvc, c_bank, resources,
                                   stop=phase['stop_pc'], external=fx['external'])
            assert actual[0]['ok'] and not actual[4], (row['label'], actual[4])
            check_result(actual, dict(outgoing=phase['outgoing'], events=phase['_trace']['events'],
                                      ram_after=data['ram_after.bin']), e_pvc, e_bank, portbytes, phase['waiting'])
            assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == last
            control_rows += 1
        totals['cases'] += 1
        totals['split'] += len(results)
        totals['control'] += control_rows
        out_rows.append(dict(index=row['index'], label=row['label'], group=row['group'], seed=seed_name,
                             declared_initial_registers=sorted(declared), split_phases=len(results),
                             control_steps=control_rows, phases=results))
    for pc, outcomes in single_block.items():
        # preserving means both known probes (Clear and Set) come out unchanged; a Clear-making block keeps only Clear, a Set-making block only Set
        assert set(outcomes) == {1, 2} and all(outcomes.values()) == (pc in carry_preserving), (hex(pc), outcomes)
    assert consumer_phases == set(CONSUMERS) or not PROBES
    totals['single_block_carry_starts_checked'] = sorted(hex(pc) for pc in single_block)
    totals['carry_preserving_starts_observed'] = sorted(hex(pc) for pc in single_block if pc in carry_preserving)
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in carry_hist.items()}
    totals['guard_rows'] = len(guards)
    return out_rows, totals, guards, starts_by_label


def compare_guards(exe, guards, resources, guard_errors):
    rows = []
    for row, phase, ram, state, pvc, bank, step_start in guards:
        fx = row['fixture']
        label = row['label']
        stop = phase['stop_pc']
        cases = [('phase', ram, state, pvc, bank, stop)]
        if (ram, state, pvc, bank) != (step_start[0], step_start[1], step_start[2], step_start[3]):
            cases.append(('whole_step', step_start[0], step_start[1], step_start[2], step_start[3], phase['step_stop_pc']))
        entry = {}
        for kind, r, s, p, b, stp in cases:
            s = dict(s, carry=2)
            result, outgoing, out_pvc, ports, error = common.invoke(exe, OUT, 'guard_%s_%s' % (label, kind), r, s, p, b,
                                                                    resources, stop=stp, external=fx['external'])
            if label in SUPERSEDED_GUARDS:
                # superseded negative: the stop is now reached (JSR 1a73c is routed by U2); record the observed result, assert nothing about a failure
                entry[kind] = dict(ok=bool(result['ok']), pc=hex(result['pc']), error=error.strip(), observed_final_state_only=True)
                assert result['ok'] and not error.strip() and result['pc'] == stp, (label, kind, error.strip())
                continue
            assert not result['ok'], (label, kind)
            assert error.strip() == guard_errors[label], (label, kind, error.strip())
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert outgoing == r and out_pvc == p and result['bank_base'] == b
            assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
            entry[kind] = error.strip()
        if label in SUPERSEDED_GUARDS:
            SUPERSEDED_RECORDS.append(dict(label=label, native_guard=phase['guard'], former_expected_API_error=SUPERSEDED_GUARDS[label],
                                           observed_final_state=entry, native_fault_rollback_equivalence_claimed=False))
            continue
        rows.append(dict(label=label, native_guard=phase['guard'], checked_API_errors=entry,
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    return rows


def interior_pcs(instructions, block_starts):
    skip = set(block_starts) | set(BOUNDARY_PCS)
    return [pc for pc in sorted(instructions) if in_ranges(pc, NEW_RANGES) and pc not in skip]


def negatives(exe, base, starts, instructions, block_starts, resources, neg_errors):
    out = []
    r0, s0, p0, b0 = base

    def reject(label, start, changes=None, stop=0xff000, external=0, error_expected=None):
        r, s, p, b = start
        s = dict(s, carry=2)
        s.update(changes or {})
        result, outgoing, out_pvc, ports, error = common.invoke(exe, OUT, 'negative_' + label, r, s, p, b, resources,
                                                                stop=stop, external=external)
        assert not result['ok'], label
        want = error_expected if error_expected is not None else neg_errors[label]
        assert error.strip() == want, (label, error.strip())
        assert {k: result[k] for k in common.STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        row = dict(label=label, error=error.strip(), all_API_outputs_preserved=True,
                   native_exception_rollback_equivalence_claimed=False)
        if label == 'outside_range_entry_04706c':
            row.update(former_expected_API_error=UNSUPPORTED_MACHINE, superseded_by='F4 U09',
                       API_only_control=True, native_execution_equivalence_claimed=False,
                       reason='U09 contract routes 4706c (MOVEQ D0/D1, then slot registration); the frozen input now reaches a checked bus alignment error')
        out.append(row)

    interior = interior_pcs(instructions, block_starts)
    for pc in interior:
        reject('interior_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_FRAME)
    for pc in BOUNDARY_PCS:
        reject('boundary_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_MACHINE)
    for pc in (0x480f2, 0x47672, 0x6f1c4, 0x2efdc, 0x3c7c, 0xb4ab0, 0x493bc, 0x1c052, 0x4da08, 0xb4850, 0x4706c, 0x480ba):
        # U09 contract's 4706c..470e6 range supersedes this one outside probe.
        # Keep the old address/label and pin the full-run API error, including rollback.
        expected = EVEN if pc == 0x4706c else UNSUPPORTED_MACHINE
        reject('outside_range_entry_%06x' % pc, base, {'pc': pc}, error_expected=expected)
    # unknown carry at the three BCC consumers
    for pc in sorted(CONSUMERS):
        r, s, p, b = base
        for carry in (0,):
            s2 = dict(s, pc=pc, carry=carry)
            result, outgoing, out_pvc, ports, error = common.invoke(exe, OUT, 'negative_unknown_carry_%06x' % pc, r, s2, p, b,
                                                                    resources, stop=CONSUMERS[pc][0], external=0)
            assert not result['ok'] and error.strip() == UNKNOWN_CARRY, (hex(pc), error)
            assert {k: result[k] for k in common.STATE_KEYS} == s2 and outgoing == r and out_pvc == p and ports == MARKER
            assert result['external_reads'] == 0x12345678 and result['status'] == 1
            out.append(dict(label='unknown_carry_consumer_%06x' % pc, error=error.strip(), all_API_outputs_preserved=True,
                            native_exception_rollback_equivalence_claimed=False))
    # non-boundary stops: full rollback
    reject('natural_480bc_with_stop_ff000', starts['natural-seed0-bank2'], error_expected=UNSUPPORTED_MACHINE)
    # superseded negatives: 49b0c / 4aa88 are executable now (U3..U7). natural 480bc with these stops runs through the post-1a73c shell and stops there without error
    for label, stop in (('natural_480bc_with_stop_49b0c', B49B0C), ('natural_480bc_with_stop_4aa88', B4AA88)):
        r, s, p, b = starts['natural-seed0-bank2']
        result, outgoing, out_pvc, ports, error = common.invoke(exe, OUT, 'superseded_' + label, r, dict(s, carry=2), p, b, resources, stop=stop, external=0)
        assert result['ok'] and not error.strip() and result['pc'] == stop and result['status'] == 0, (label, error.strip())
        SUPERSEDED_RECORDS.append(dict(label=label, former_expected_API_error=UNSUPPORTED_MACHINE, observed_final_state=dict(
            ok=True, pc=hex(result['pc']), a7=hex(result['a7']), error='', RAM_changed=outgoing != r), native_exception_rollback_equivalence_claimed=False))
    reject('natural_480bc_with_stop_4939c', starts['natural-seed0-bank2'], stop=T4939C, error_expected=UNSUPPORTED_MACHINE)
    reject('direct_6f1c2_with_stop_ff000', starts[SIX_F1C2_LABEL], error_expected=UNSUPPORTED_MACHINE)
    reject('a5_not_108000_49392_with_stop_ff000', starts['boundary-a5-not-108000-direct-49392'], error_expected=UNSUPPORTED_MACHINE)
    reject('a5_not_108000_via_b4a2a_with_stop_ff000', starts['boundary-a5-not-108000-via-b4a2a'], error_expected=UNSUPPORTED_MACHINE)
    # API-only positive controls: the post-1a73c shell reaches 49b0c, 4aa88 and e8a48 with matching stops (stop checked at the loop head, nothing executed there by these controls)
    controls = []
    for entry_pc, stop in ((0x480c6, B49B0C), (0x480cc, B4AA88), (0x480e4, BE8A48), (0x480d2, 0xb4a2a), (0x480ea, 0x2efa6)):
        s = dict(s0, pc=entry_pc, carry=2, a7=s0['a7'] - 4)
        r = bytearray(r0)
        r[(s['a7']) & 0xffff:(s['a7'] & 0xffff) + 4] = (0x2ac2).to_bytes(4, 'big')
        result, out_ram, out_pvc, ports, error = common.invoke(exe, OUT, 'control_stop_%06x' % stop, bytes(r), s, p0, b0,
                                                               resources, stop=stop)
        assert result['ok'] and not error and result['pc'] == stop and result['status'] == 0, (hex(stop), error)
        controls.append(dict(entry=entry_pc, stop=stop, ok=True, a7=result['a7']))
    return out, len(interior), controls


def zero_step(exe, base, resources, block_starts):
    ram, state, pvc, bank = base
    rows = []
    for pc in block_starts:
        for carry in (0, 1, 2):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = common.invoke(exe, OUT, 'zero_%06x_%d' % (pc, carry), ram, s, pvc, bank,
                                                                    resources, stop=pc)
            assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
            assert result['external_reads'] == 0 and not ports
            rows.append(dict(pc=pc, carry=carry, all_input_state_preserved=True))
    return rows


def boundary_zero_step(exe, base, resources):
    ram, state, pvc, bank = base
    rows = []
    for pc in BOUNDARY_PCS:
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = common.invoke(exe, OUT, 'zero_boundary_%06x' % pc, ram, s, pvc, bank,
                                                               resources, stop=pc)
        assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
        rows.append(dict(pc=pc, ok=result['ok'], error=error.strip()))
    return rows


BUS_DEVICE = 'unsupported program bus device address'
SIX_F1C2_LABEL = '6f1c2-rts'
GUARD_ERRORS = {
    'guard-hazard-x-bin-overflow-x1-06a0': BUS_DEVICE, 'guard-hazard-x-bin-overflow-x1-1000': BUS_DEVICE,
    'guard-hazard-x-bin-overflow-x1-4000': BUS_DEVICE, 'guard-hazard-x-bin-overflow-x1-7fff': BUS_DEVICE,
    'guard-odd-A0-46f52': EVEN, 'guard-odd-A1-movem': EVEN, 'guard-odd-A1-4d9d6-route': EVEN, 'guard-odd-A4-4d9d6': EVEN,
    'guard-odd-A7-6f1c2-rts': EVEN, 'guard-odd-A7-3c44-push': EVEN, 'guard-odd-A7-jsr-push': EVEN,
    'guard-rom-write-b4a2a-a5-0': WRITE_DEVICE, 'guard-rom-write-4701e-a5-0': WRITE_DEVICE,
    'guard-rom-write-b481e-a5-8000': WRITE_DEVICE, 'guard-odd-A5-b4a2a': EVEN_WRITE,
    'guard-ret-1a73c-boundary-via-direct': UNSUPPORTED_MACHINE}
# Superseded by U2 (JSR 1a73c is executed from here on): the native guard record is unchanged; the C++ now runs to the 2ac2 stop without error.
SUPERSEDED_GUARDS = {'guard-stop-not-boundary-2ac2': UNSUPPORTED_MACHINE}
SUPERSEDED_RECORDS = []
NEG_ERRORS = {}


def main():
    assert OUT.resolve() == (ROOT / 'artifacts/animation_machine_frame_helpers_execution').resolve()
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder: stale debug files must not enter the report
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_frame_helpers.py', 'tools/verify_animation_machine_card_child.py',
                 'tools/verify_stage_frame.py', 'tools/observe_animation_machine_frame_helpers.py',
                 'docs/analysis/animation-machine-frame-helpers-u1-contract.md',
                 'engine/src/animation_machine_frame_helpers.cpp', 'engine/src/animation_machine_internal.h',
                 'engine/tests/animation_machine_frame_helpers_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    cc.NATIVE_DIR = NATIVE_DIR
    (report, rows, native_refs, instructions, program_reads, control_count, block_starts, leader_missing, leader_extra,
     all_starts, uncovered_starts) = audit_native(program, source)
    refs.update(native_refs)
    block_starts = tuple(block_starts)
    report_seed_provenance.update(report['seed_provenance']['seeds'])
    seeds, seed_files = rebuild_seeds()
    assert sorted(seeds) == sorted(report['seed_provenance']['seeds'])
    for name, seed in seeds.items():
        prov = report['seed_provenance']['seeds'][name]
        assert prov['ram_sha256'] == seed['raw_sha'], name
        assert prov['registers'] == [hex(seed['regs'][k]) for k in vsf.KEYS], name
    for path, expected in seed_files.items():
        assert report['seed_provenance']['files'].get(path, expected) == expected
    # blocks and carry-preserving set from the original opcodes
    blocks = static_blocks(instructions, set(block_starts))
    carry_preserving = tuple(sorted(pc for pc in block_starts if all(
        instructions[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc])))
    cpp_cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', (ROOT / 'engine/src/animation_machine_frame_helpers.cpp').read_text()))
    cpp_not_native = sorted(cpp_cases - set(block_starts))
    native_not_cpp = sorted(set(block_starts) - cpp_cases)
    matches, totals, guards, starts = compare(exe, rows, resources, instructions, seeds, set(all_starts), carry_preserving)
    guarded = compare_guards(exe, guards, resources, GUARD_ERRORS)
    base_ram, base_state, base_pvc, base_bank = starts['natural-seed0-bank2']
    base = (base_ram, base_state, base_pvc, base_bank)
    negative, interior_count, controls = negatives(exe, base, starts, instructions, set(block_starts), resources, NEG_ERRORS)
    zero = zero_step(exe, base, resources, block_starts)
    boundary_zero = boundary_zero_step(exe, base, resources)
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert cc.digest(ROOT / name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs.update(seed_files)
    refs.update({str(path.resolve()): cc.digest(path) for path in OUT.rglob('*') if path.is_file() and path != report_path})
    unique = {}
    for name, expected in list(inputs.items()) + list(refs.items()):
        key = str((ROOT / name).resolve())
        assert key not in unique or unique[key] == expected
        unique[key] = expected
    result = dict(schema_version=1, source=source, inputs=inputs, artifacts=refs,
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, contract_sha256=CONTRACT_SHA,
                  seeds_rebuilt={n: dict(ram_sha256=sha(s['ram']), pvc_sha256=sha(s['pvc']), source=s['source'])
                                 for n, s in seeds.items()},
                  block_starts=[hex(p) for p in block_starts], block_start_count=len(block_starts),
                  carry_preserving_blocks=[hex(p) for p in carry_preserving], carry_preserving_count=len(carry_preserving),
                  never_executed_natively=[hex(p) for p in uncovered_starts],
                  opcode_leader_derivation=dict(native_not_derived=[hex(p) for p in leader_missing],
                                                derived_not_native=[hex(p) for p in leader_extra]),
                  cpp_case_labels=dict(cpp_not_in_native_block_starts=[hex(p) for p in cpp_not_native],
                                       native_block_starts_without_cpp_case=[hex(p) for p in native_not_cpp]),
                  actual_CPP=dict(totals, matches=matches),
                  original_program_read_audit=program_reads,
                  superseded_negatives=SUPERSEDED_RECORDS,
                  native_guards_checked_API=guarded, native_continuous_control_phases_replayed=control_count,
                  negatives=negative, negative_count=len(negative) + len(guarded),
                  interior_PCs_rejected=interior_count, API_only_boundary_stop_controls=controls,
                  zero_step=zero, boundary_zero_step=boundary_zero,
                  carry_check='C++ carry equals source-opcode walk over native-executed PCs (ORI/ANDI CCR and ANDI.W #1,D0 known, 289e equal-branch Clear, flow-only preserved, else Unknown); native SR never read',
                  normalized_reference_paths=len(unique), compile_command=command, failure=None, ROM_unchanged=True,
                  limits=['Controlled stage-frame seeds with declared RAM/register/PC/return-LONG fixtures, not natural scheduler, IRQ or gameplay reachability.',
                          'This observation never executed 1a73c/49b0c/4aa88/e8a48 or 4939c (TRAP #f); in the final state later units execute 1a73c/49b0c/4aa88/e8a48 (stop-not-boundary-2ac2 and natural 49b0c/4aa88 stops are recorded as superseded_negatives), 4939c remains a stop boundary; 49b0c/4aa88/e8a48 stops are API-only controls with no native counterpart.',
                          'Carry is a source-opcode classification (native SR is never read).',
                          'Checked failures preserve API outputs, not original CPU fault rollback; interior/boundary direct entries have no native guard (API-only rejection).',
                          'X-bin overflow past 10d665 is observed native behavior (writes reach 10d67c at x1=06a0); hazard cases that fault natively are guards here.',
                          'Native observation artifacts are audited by hash/trace consistency, not re-executed here.'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'],
                         negatives=result['negative_count'], interior=interior_count, zero_step=len(zero),
                         carry=totals['carry_histogram'], preserving=len(carry_preserving), sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
