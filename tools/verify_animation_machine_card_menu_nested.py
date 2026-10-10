"""Original card-menu nested return (a698..a706: a698/a6b2/a6bc/a6ce/a6d6/a6da/a6ea/a6f0/a6f8/a6fc/a706) native evidence
vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an immutable input (this
verifier never invokes the observer main). C++ resumes only from the previous actual C++ output plus the host changes
recorded in the native step records (RAM write, PC change, A7 add, register-at-step-boundary), each asserted against
the step-start PC/A7 and against the native RAM/registers the record states. The chain start is the actual C++ output
of the reviewed fade/card chain (c00468 stop); the prefix of the nested chain (steps 0..36: card child, push, open,
input frame 1, YES selection with declared BIOS resumes, result menu push) is re-run in actual C++ from the split
phases of the reviewed open and save observations (the nested observer itself stores only the nested frames of the
chain, steps 37..109, split). Every other condition starts from an actual C++ chain step output selected by native
RAM identity, the source step named in the fixture and register equality; declared initial registers are recorded.
c00468/c0046e (BIOS card stops) are stop boundaries only: never executed. Native files are streamed and hash checked
against the report; per-invocation scratch files are removed after the comparison and only guards/negatives/zero-step
keep their files.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = '/Users/start/Workspce/metalslug/'      # absolute prefix recorded inside the native observation
OUT = ROOT / 'artifacts/animation_machine_card_menu_nested_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_card_menu_nested_native'
NATIVE_SHA = '7b40f4de2da0d11dba79fd098993b3dcc6f3a958be254d2642b456dd874c9959'
NATIVE_TOOL_SHA = 'fb7524ab620f2fbc730844a92293518cdf9016e6340fedc3e38c9a7a417746c8'
CONTRACT_SHA = '1688616ba2f0ea744c0e37505c208bd2d9f0b8ba1ad066b21d1e65384fdbd27f'
REPORTS = {     # name -> (native folder, observation sha256)
    'fade': ('animation_machine_fade_card_native', 'f53387b7122286eca94c55371a34a09f900489eb9ab2766f9c98e086da7f57fc'),
    'child': ('animation_machine_card_child_native', '3e48b69e4827d5a25f7085aee1c81bf6bc0b41a64daa159a3232e690c16f3312'),
    'push': ('animation_machine_card_menu_native', 'da76f4643efafafdc8929a9cd73a24a1e3a434e49275e5babcadd53e5c45bfbc'),
    'open': ('animation_machine_card_menu_open_native', '154b4ed588a1bf7c9615bc7c6c3710492e4c0a711aca710b20f6bd21a7390ab4'),
    'input': ('animation_machine_card_menu_input_native', '49c1ba52f7ec11dc1929022f7dc6b455b434681d472e9a39631c69ea98ce9b46'),
    'close': ('animation_machine_card_menu_close_native', 'b5bd2164ab5badd5067b469d9d6c7d79b3cedeae2efca07d89ff18d4882a39dd'),
    'save': ('animation_machine_card_menu_save_native', 'b0f9e26195f9a31181a6164f4ee15b93497515a7782dccc7f5a0e74ada142c0c')}
OPEN_CHAIN = 'chain-full-bios-resume-to-open'      # steps 0..30
SAVE_CHAIN = 'chain-full-bios-resume-to-save'      # steps 31..36 stored (SAVE OK)
CHAIN_LABEL = 'chain-save-ok-to-nested-removal'
OPEN_LAST, SAVE_FIRST, SAVE_LAST = 30, 31, 36
NESTED_BLOCK_STARTS = (0xa698, 0xa6b2, 0xa6bc, 0xa6ce, 0xa6d6, 0xa6da, 0xa6ea, 0xa6f0, 0xa6f8, 0xa6fc, 0xa706)
NESTED_RANGE = (0xa698, 0xa70a)         # half-open, equal to native new_ranges [[42648, 42762]]
ROUTER_INCLUSIVE = (0xa698, 0xa708)     # animation_machine.cpp router condition
CARRY_PRESERVING = (0xa6ce, 0xa6f8, 0xa706)
BIOS_STOPS = (0xc00468, 0xc0046e)
BRANCH_ROOTS = ('bra', 'bsr', 'beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt',
                'bgt', 'ble', 'rts', 'jmp', 'jsr')
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_NESTED = 'unsupported animation card menu nested PC'
EVEN = 'program bus requires even WORD/LONG address'
MARKER = cc.MARKER
STATE_KEYS = common.STATE_KEYS
CHILD, PARENT = 0x104800, 0x102000
DECLARED_INITIAL_KEYS = ('a2', 'a7')      # fixture initial_regs/initial_a7 that differ from the chain step output (direct entries)


def sha(data):
    return cc.sha(data)


CMP_PRODUCERS = (0x2886, 0x2a12)       # CMP.W $10(A0|A6),D0 inside the cleanup core: its carry is a known compare result


def classify(instructions, carry, pcs):
    """Source-opcode carry classification over the full native PC path (last PC = next/stop PC).

    cc.classify_carry rule (ORI/ANDI CCR known, flow-only preserved, everything else Unknown) plus one extra,
    evidence-based rule: the cleanup compare CMP.W $10(An),D0 (2886, 2a12) makes C a compare result whose value the
    native path itself decides at the consuming BCS/BCC (taken BCS or untaken BCC means C=1, the 68000 definition)."""
    pending = False
    for k in range(len(pcs) - 1):
        pc = pcs[k]
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        if pc in CMP_PRODUCERS:
            pending, carry = True, 0
        elif pending and name in ('bcs', 'bcc'):
            taken = pcs[k + 1] != pc + item['size']
            carry = 2 if (name == 'bcs') == taken else 1
            pending = False
        else:
            carry = cc.classify_carry(instructions, carry, [pc])
    assert not pending, 'cleanup compare without a consuming BCS/BCC inside the phase'
    return carry


def rd(ram, address, size):
    return cc.rd(ram, address, size)


def in_range(pc):
    return NESTED_RANGE[0] <= pc < NESTED_RANGE[1]


def run(exe, label, ram, state, pvc, bank, resources, stop, external=0, keep=False):
    """common.invoke plus removal of the scratch files unless the case is kept as evidence."""
    result = common.invoke(exe, OUT, label, ram, state, pvc, bank, resources, stop=stop, external=external)
    if not keep:
        for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin', '_state.json'):
            (OUT / (label + suffix)).unlink()
    return result


def load_phase(folder, phase, covered, snapshots=False):
    """Read and hash-check every native file of a phase; return payload dict, trace and snapshots."""
    data = {}
    for name, expected in phase['artifacts'].items():
        value = (folder / name).read_bytes()
        assert sha(value) == expected, name
        assert name not in covered, name
        covered.add(name)
        data[name.rsplit('phase_%03d_' % phase['index'], 1)[1]] = value
    trace = json.loads(data['trace.json'])
    snaps = []
    if snapshots:
        for snapshot in phase['snapshots']:
            ram = data[snapshot['artifacts']['ram'].rsplit('phase_%03d_' % phase['index'], 1)[1]]
            pvc = data[snapshot['artifacts']['pvc'].rsplit('phase_%03d_' % phase['index'], 1)[1]]
            snaps.append((snapshot['registers'], ram, pvc))
    return data, trace, snaps


def audit_reads(program, tracker, phase, trace):
    """Reconstruct the live bank from ordered PVC writes, independently of tags, and check ROM reads."""
    assert (phase['bank_before'], phase['ff8_before'], phase['ff9_before']) == (
        tracker['bank'], tracker['ff8'], tracker['ff9'])
    for event in trace['events']:
        address, size = event['address'], event['size']
        raw = bytes.fromhex(event['bytes'])
        assert len(raw) == size
        if event['region'] == 'pvc':
            assert event['access'] == 'write' and size == 2
            if address == 0x2ffff0:
                tracker['ff8'] = int.from_bytes(raw, 'big')
            else:
                assert address == 0x2ffff2
                tracker['ff9'] = int.from_bytes(raw, 'big')
            tracker['bank'], tracker['ff8'], tracker['ff9'] = common.pvc_bank_update(tracker['ff8'], tracker['ff9'])
            assert (event['bank_after'], event['ff8_after'], event['ff9_after']) == (
                tracker['bank'], tracker['ff8'], tracker['ff9'])
            tracker['PVC_writes'] += 1
        elif event['region'] in ('fixed', 'bank'):
            assert event['access'] == 'read'
            if event['region'] == 'fixed':
                assert 0 <= address <= 0x100000 - size
                physical = address
                tracker['fixed_reads'] += 1
            else:
                assert 0x200000 <= address <= 0x2fe000 - size
                physical = tracker['bank'] + address - 0x200000
                assert (event['bank_at_read'], event['physical_rom_offset']) == (tracker['bank'], physical)
                tracker['bank_reads'] += 1
            assert 0 <= physical <= len(program) - size
            assert raw == program[physical:physical + size]
    assert (phase['modeled_bank'], phase['ff8_after'], phase['ff9_after']) == (
        tracker['bank'], tracker['ff8'], tracker['ff9'])


def audit_phase(phase, data, trace, instructions):
    assert phase['carry'] is None and not phase['branch_evidence']
    assert phase['counts']['external_reads'] == sum(e['region'] == 'external' for e in trace['events'])
    ports = [e for e in trace['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
    assert data['ports.bin'] == b''.join(struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16))
                                         for e in ports)
    executed = trace['pcs'][:-1]
    assert not (set(executed) & set(BIOS_STOPS)), 'BIOS boundary executed'
    assert instructions.keys() >= set(executed)
    return executed


def audit_step(parts, whole):
    """Split concatenation equals the continuous control for this step; checkpoints equal snapshots."""
    phase_whole, data_whole, trace_whole, snaps = whole
    assert parts and parts[0][0]['host_changes'] == phase_whole['host_changes']
    assert all(not p['host_changes'] for p, _d, _t in parts[1:])
    assert parts[0][0]['incoming'] == phase_whole['incoming']
    pcs, events = [], []
    for _p, _d, trace in parts:
        pcs.extend(trace['pcs'][:-1])
        events.extend(trace['events'])
    pcs.extend(parts[-1][2]['pcs'][-1:])
    assert pcs == trace_whole['pcs'] and events == trace_whole['events']
    last, last_data, _t = parts[-1]
    for key in ('outgoing', 'modeled_bank', 'guard'):
        assert last[key] == phase_whole[key], (phase_whole['step'], key)
    assert last_data['ram_after.bin'] == data_whole['ram_after.bin']
    assert last_data['pvc_after.bin'] == data_whole['pvc_after.bin']
    checkpoints = {p['outgoing']['pc']: (p['outgoing'], d['ram_after.bin'], d['pvc_after.bin'])
                   for p, d, _t in parts[:-1] if p['guard'] is None}
    seen = set()
    for registers, ram, pvc in snaps:
        assert registers['pc'] not in seen and checkpoints[registers['pc']] == (registers, ram, pvc)
        seen.add(registers['pc'])
    assert seen == set(checkpoints), phase_whole['step']
    return len(snaps)


def apply_changes(ram, state, changes, entry):
    """Declared host changes on top of previous actual C++ outputs only; each must match its record."""
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
        elif kind == 'a7_add':
            state['a7'] = (state['a7'] + change['delta']) & 0xffffffff
        elif kind == 'reg':
            assert change['name'] in common.REGS and change['name'] != 'a7', change
            state[change['name']] = change['value']
        else:
            raise AssertionError(kind)
        kinds.append(kind)
    return bytes(ram), state, kinds


def digest_output(ram, state, pvc, bank, carry):
    h = hashlib.sha256()
    h.update(ram)
    h.update(pvc[:0x1ff0] + pvc[0x1ff4:])
    h.update(json.dumps({k: state[k] for k in sorted(state) if carry or k != 'carry'}, sort_keys=True).encode())
    h.update(struct.pack('>I', bank))
    return h.hexdigest()


def static_blocks(instructions):
    """Source-opcode walk of each nested block (to the branch/jump or the next block start)."""
    starts = set(NESTED_BLOCK_STARTS)
    blocks = {}
    for start in NESTED_BLOCK_STARTS:
        pcs, pc = [], start
        while True:
            item = instructions[pc]
            pcs.append(pc)
            if item['mnemonic'].split('.')[0] in BRANCH_ROOTS:
                break
            pc += item['size']
            if pc in starts:
                break
        blocks[start] = pcs
    return blocks


def static_preserving(instructions, blocks):
    out = set()
    for start, pcs in blocks.items():
        if cc.classify_carry(instructions, 1, pcs) == 1 and cc.classify_carry(instructions, 2, pcs) == 2:
            out.add(start)
    return out


def ranges_of(before, after):
    """Contiguous changed byte ranges between two RAM images (CPU addresses 0x100000+)."""
    out, start = [], None
    for i in range(65536):
        if before[i] != after[i]:
            if start is None:
                start = i
            last = i
        elif start is not None:
            out.append((start, last))
            start = None
    if start is not None:
        out.append((start, last))
    return out


def check_frame(ram, state, frame, ports_sha, ports_count, step_start_ram, base7e=CHILD):
    """The recorded per-frame fields equal the C++ RAM/registers of the frame end (and the step's ordered ports)."""
    a5 = state['a5']
    changed = ranges_of(step_start_ram, ram)
    got = dict(
        outgoing=(state['pc'], state['a6'], state['a7']),
        f2=rd(ram, a5 - 0xf2, 4), ee=rd(ram, a5 - 0xee, 4), e5=rd(ram, a5 - 0xe5, 1), e6=rd(ram, a5 - 0xe6, 1),
        word4_107eee=rd(ram, 0x107eee + 4, 2), word4_107efe=rd(ram, 0x107efe + 4, 2),
        record_107eee=bytes(ram[0x7eee:0x7efe]).hex(), record_107efe=bytes(ram[0x7efe:0x7f0e]).hex(),
        child_7e=rd(ram, base7e + 0x7e, 2), child_80=rd(ram, base7e + 0x80, 1), child_callback=rd(ram, CHILD, 4),
        sound_queue=bytes(ram[0x4d82:0x4d8e]).hex(), ports=(ports_sha, ports_count),
        ram_changed=(len(changed), [(0x100000 + a, 0x100000 + b) for a, b in changed]))
    want = dict(
        outgoing=(int(frame['outgoing_pc'], 16), int(frame['outgoing_a6'], 16), int(frame['outgoing_a7'], 16)),
        f2=int(frame['f2_after'], 16), ee=int(frame['ee_after'], 16), e5=frame['e5_after'], e6=frame['e6_after'],
        word4_107eee=frame['word4_107eee_after'], word4_107efe=frame['word4_107efe_after'],
        record_107eee=frame['record_107eee_after'], record_107efe=frame['record_107efe_after'],
        child_7e=frame['child_7e_after'], child_80=frame['child_80_after'],
        child_callback=int(frame['child_callback_after'], 16), sound_queue=frame['sound_queue_ram_104d82_12_after'],
        ports=(frame['ordered_ports_sha256'], frame['ordered_port_writes']),
        ram_changed=(frame['ram_changed']['count'], [(int(r['first'], 16), int(r['last'], 16))
                                                     for r in frame['ram_changed']['ranges']]))
    bad = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
    assert not bad, (frame['step'], frame['label'], bad)


class Shared(object):
    """State shared by the row workers: chain step outputs other rows start from, guard/start records."""
    def __init__(self):
        self.cv = threading.Condition()
        self.failed = False
        self.ends = {}          # (label, step) -> (ram, state, pvc, bank)
        self.meta = {}          # (label, step) -> (native ram_after sha, modeled_bank, ff8_after, ff9_after)
        self.sources = {}       # native ram_after sha -> [(label, step)]
        self.starts = {}
        self.guards = []


def probe_task(exe, resources, instructions, label, phase_ram, phase_in, phase_pvc, phase_bank, stop, external,
               full, probe, result, ram, pvc, ports):
    """Same phase with a known incoming C: exactly the source classification, all other outputs identical."""
    again = run(exe, label, phase_ram, dict(phase_in, carry=probe), phase_pvc, phase_bank, resources, stop=stop,
                external=external)
    assert again[0]['ok'] and not again[4]
    executed = full[:-1]
    assert again[0]['carry'] == classify(instructions, probe, full)
    assert ({k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in result.items() if k != 'carry'})
    assert again[1] == ram and again[2] == pvc and again[3] == ports
    blocks = [pc for pc in executed if pc in NESTED_BLOCK_STARTS]
    single = blocks[0] if len(blocks) == 1 and blocks[0] == executed[0] else None
    return single, again[0]['carry'] == probe


def control_task(exe, resources, label, c_ram, c_state, c_pvc, c_bank, stop, external, outgoing, events, ram_after,
                 e_pvc, e_bank, portbytes, end):
    actual = run(exe, label, c_ram, c_state, c_pvc, c_bank, resources, stop=stop, external=external)
    assert actual[0]['ok'] and not actual[4], (label, actual[4])
    common.check_result(actual, dict(outgoing=outgoing, events=events, ram_after=ram_after), e_pvc, e_bank, portbytes)
    assert (actual[1], {k: actual[0][k] for k in STATE_KEYS}, actual[2], actual[0]['bank_base']) == end, label
    return 1


def run_row(ctx, row, folder, start, tracker, tag, shared, register=None, frames=None, controls_on=True):
    """Replay one native row (all steps) in actual C++: split phases resumed from the previous C++ output."""
    exe, program, resources, instructions, pool = (ctx[k] for k in ('exe', 'program', 'resources', 'instructions', 'pool'))
    totals = dict(cases=1, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0,
                  carry_probe_preserved=0, snapshots_checked=0, frames_checked=0,
                  declared_host_changes=dict(ram=0, pc=0, a7_add=0, reg=0), reg_changes=[], record_7e_80_read_from_parent=[])
    fx = row['fixture']
    covered = set()
    ram, state, pvc, bank = start
    expected_pvc, expected_bank = pvc, bank
    ctl_tracker = dict(tracker)
    frame_by_step = {f['step']: f for f in (frames or [])}
    steps = []
    for j, phase in enumerate(row['phases']):
        if not steps or steps[-1][0] != phase['step']:
            assert phase['step'] not in [s for s, _ in steps]
            steps.append((phase['step'], []))
        steps[-1][1].append((j, phase))
    controls = {p['step']: p for p in row['continuous_control']}
    assert len(controls) == len(row['continuous_control']) and sorted(controls) == [s for s, _ in steps]
    digests = hashlib.sha256()
    futures = []
    records = []
    guard_item = None
    first_start = None
    guard_start = None
    resumed = row_phases = control_rows = frames_seen = 0
    row_carry = {0: 0, 1: 0, 2: 0}
    for step, items in steps:
        parts = []
        step_start = None
        completed = True
        step_ports = bytearray()
        for j, phase in items:
            data, trace, _s = load_phase(folder, phase, covered)
            executed = audit_phase(phase, data, trace, instructions)
            audit_reads(program, tracker, phase, trace)
            parts.append((phase, data, trace))
            entry = dict(pc=state['pc'], a7=state['a7'])
            if phase['guard'] is not None:
                assert j == len(row['phases']) - 1 and row['guarded']
                ram2, state2, _k = apply_changes(ram, state, phase['host_changes'], entry)
                assert ram2 == data['ram_before.bin']
                assert {k: state2[k] for k in common.REGS + ('pc',)} == phase['incoming']
                guard_item = (row, phase, ram2, state2, pvc, bank)
                completed = False
                break
            ram, state, kinds = apply_changes(ram, state, phase['host_changes'], entry)
            for change in phase['host_changes']:
                totals['declared_host_changes'][change['kind']] += 1
                if change['kind'] == 'reg':
                    assert phase['phase_in_step'] == 0
                    totals['reg_changes'].append((row['label'], phase['label'], change['name'], change['value']))
            assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
            assert ram == data['ram_before.bin'], (row['label'], j)
            assert bank == phase['bank_before'] and kinds == [c['kind'] for c in phase['host_changes']]
            if phase['phase_in_step'] == 0:
                step_start = (ram, dict(state), pvc, bank, expected_pvc, expected_bank)
                if first_start is None:
                    first_start = (ram, dict(state), pvc, bank)
            else:
                assert not phase['host_changes']
            events = trace['events']
            expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
            assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
            step_ports += portbytes
            phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
            label = '%s_s%03d' % (tag, j)
            actual = run(exe, label, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
            assert actual[0]['ok'] and not actual[4], (row['label'], j, phase['stop_pc'], actual[4])
            common.check_result(actual, dict(outgoing=phase['outgoing'], events=events,
                                             ram_after=data['ram_after.bin']), expected_pvc, expected_bank, portbytes)
            assert actual[0]['status'] == 0
            result, ram, pvc, _, _ = actual
            want_carry = classify(instructions, phase_in['carry'], trace['pcs'])
            assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']),
                                                    result['carry'], want_carry)
            row_carry[result['carry']] += 1
            if executed and all(in_range(pc) for pc in executed):
                for probe in (1, 2):
                    futures.append(('probe', pool.submit(
                        probe_task, exe, resources, instructions, label + 'p%d' % probe, data['ram_before.bin'],
                        phase_in, phase_pvc, phase_bank, phase['stop_pc'], fx['external'], trace['pcs'], probe, result,
                        ram, pvc, actual[3])))
            totals['carry_checks'] += 1
            state = {k: result[k] for k in STATE_KEYS}
            bank = result['bank_base']
            totals['reads'] += result['external_reads']
            totals['ports'] += len(portbytes) // 9
            if j:
                resumed += 1
                totals['resumes'] += 1
            row_phases += 1
            out_c = digest_output(ram, state, pvc, bank, True)
            digests.update(out_c.encode())
            records.append(((sha(data['ram_after.bin']), sha(data['pvc_after.bin']),
                             tuple(sorted(phase['outgoing'].items()))),
                            digest_output(ram, state, pvc, bank, False), out_c))
        if completed:
            end = (ram, dict(state), pvc, bank)
            last = parts[-1]
            if register is not None:
                with shared.cv:
                    shared.ends[(register, step)] = end
                    shared.meta[(register, step)] = (sha(last[1]['ram_after.bin']), last[0]['modeled_bank'],
                                                     last[0]['ff8_after'], last[0]['ff9_after'])
                    shared.sources.setdefault(sha(last[1]['ram_after.bin']), []).append((register, step))
                    shared.cv.notify_all()
            if step in frame_by_step:
                # Fact: in the two fresh rows that declare the parent re-entry (A6 = parent) the observer's record
                # fields child_7e/child_80 hold the parent object's 7e/80 (the chain row's record reads the child).
                parent_fields = row['label'] != CHAIN_LABEL and any(
                    c['kind'] == 'reg' for c in parts[0][0]['host_changes'])
                if parent_fields:
                    totals['record_7e_80_read_from_parent'].append(row['label'])
                check_frame(ram, state, frame_by_step[step], sha(bytes(step_ports)), len(step_ports) // 9,
                            step_start[0], base7e=PARENT if parent_fields else CHILD)
                frames_seen += 1
                totals['frames_checked'] += 1
        control = controls[step]
        c_data, c_trace, c_snaps = load_phase(folder, control, covered, snapshots=True)
        audit_phase(control, c_data, c_trace, instructions)
        audit_reads(program, ctl_tracker, control, c_trace)
        totals['snapshots_checked'] += audit_step(parts, (control, c_data, c_trace, c_snaps))
        if control['guard'] is None and controls_on:
            assert completed
            c_ram, c_state, c_pvc, c_bank, e_pvc, e_bank = step_start
            assert {k: c_state[k] for k in common.REGS + ('pc',)} == control['incoming']
            e_pvc, e_bank, portbytes = cc.fold_outputs(e_pvc, e_bank, c_trace['events'])
            assert e_bank == control['modeled_bank'] and portbytes == c_data['ports.bin']
            futures.append(('control', pool.submit(
                control_task, exe, resources, '%s_ctl%03d' % (tag, step), c_ram, c_state, c_pvc, c_bank,
                control['stop_pc'], fx['external'], control['outgoing'], c_trace['events'], c_data['ram_after.bin'],
                e_pvc, e_bank, portbytes, end)))
            control_rows += 1
    assert frames_seen == len(frame_by_step), (row['label'], frames_seen, len(frame_by_step))
    single = {}
    for kind, future in futures:
        value = future.result()
        if kind == 'probe':
            block, preserved = value
            totals['carry_probes'] += 1
            totals['carry_probe_preserved'] += preserved
            if block is not None:
                single.setdefault(block, set()).add(preserved)
    assert ctl_tracker['bank'] == tracker['bank']
    totals['split'] = row_phases
    totals['control'] = control_rows
    summary = dict(index=row['index'], label=row['label'], group=row['group'],
                   split_phases=row_phases, resumed_from_previous_Cpp_output=resumed,
                   control_steps=control_rows, steps=len(steps), guarded=bool(row['guarded']),
                   carry_counts={cc.CARRY_NAME[k]: v for k, v in row_carry.items()},
                   C_output_digest_chain_sha256=digests.hexdigest())
    return dict(summary=summary, totals=totals, covered=covered, records=records, guard=guard_item,
                first_start=first_start, guard_start=guard_start, single=single, row_carry=row_carry,
                end=(ram, dict(state), pvc, bank))


def new_tracker(fx):
    return dict(bank=fx['bank_state'][0], ff8=fx['bank_state'][1], ff9=fx['bank_state'][2],
                fixed_reads=0, bank_reads=0, PVC_writes=0)


def row_start(row, shared, bios_start):
    """C++ start state: previous actual C++ output (BIOS chain stop / chain step end) plus recorded declared registers."""
    fx = row['fixture']
    first = row['phases'][0]
    native_pvc = (NATIVE_DIR / next(n for n in first['artifacts'] if n.endswith('_pvc_before.bin'))).read_bytes()
    assert sha(native_pvc) == fx['initial_PVC_sha256']
    native_masked = sha(cc.masked_pvc(native_pvc))
    want = dict({k: v for k, v in fx['initial_regs'].items() if k != 'a7'}, a7=fx['initial_a7'], pc=fx['entry_pc'])
    role = fx['preparation']['role']
    named = re.search(r'\(step (\d+)', role)
    candidates = [c for c in shared.sources.get(fx['initial_RAM_sha256'], [])
                  if shared.ends[c][1]['pc'] == fx['entry_pc']]
    assert candidates, row['label']
    if named:
        candidates = [c for c in candidates if c[1] == int(named.group(1))]
        assert candidates, (row['label'], 'named source step not among RAM-identical chain steps')

    def diff(candidate):
        s = shared.ends[candidate][1]
        return sorted(k for k in cc.STATE_NO_CARRY if s[k] != want[k])
    best = min(len(diff(c)) for c in candidates)
    found = [c for c in candidates if len(diff(c)) == best]
    label, step = found[0]
    ram, src_state, pvc, bank = shared.ends[found[0]]
    declared = diff(found[0])
    assert all(diff(c) == declared for c in found)
    assert set(declared) <= set(DECLARED_INITIAL_KEYS), (row['label'], declared)
    assert sha(ram) == fx['initial_RAM_sha256'] and sha(cc.masked_pvc(pvc)) == native_masked
    assert bank == fx['bank_state'][0] and shared.meta[found[0]][1:] == tuple(fx['bank_state'])
    state = dict(src_state)
    declared_values = {}
    for key in declared:
        declared_values[key] = (src_state[key], want[key])
        state[key] = want[key]
    origin = 'actual C++ output of %s step %d (%d equal candidates)%s' % (
        label, step, len(found), (' plus declared ' + ','.join('%s %#x->%#x' % (k, v[0], v[1])
                                                                for k, v in declared_values.items())) if declared else '')
    return (ram, state, pvc, bank), origin, declared_values, (label, step)


def chain_prefix(ctx, bios_start, shared, reports, rows_by_name):
    """Re-run steps 0..36 (open chain 0..30, save chain 31..36) in actual C++ from the c00468 stop output."""
    out = []
    key, (ram, src_state, pvc, bank) = bios_start
    start = (ram, dict(src_state, carry=0), pvc, bank)
    tracker = None
    for name, label, first, last in (('open', OPEN_CHAIN, 0, OPEN_LAST), ('save', SAVE_CHAIN, SAVE_FIRST, SAVE_LAST)):
        row = next(r for r in reports[name]['results'] if r['label'] == label)
        folder = ROOT / 'artifacts' / REPORTS[name][0]
        fx = row['fixture']
        if tracker is None:
            first_phase = row['phases'][0]
            native_pvc = (folder / next(n for n in first_phase['artifacts'] if n.endswith('_pvc_before.bin'))).read_bytes()
            assert fx['entry_pc'] == cc.BIOS and sha(cc.masked_pvc(native_pvc)) == sha(cc.masked_pvc(pvc))
            assert sha(ram) == fx['initial_RAM_sha256'] and bank == fx['bank_state'][0]
            assert {k: src_state[k] for k in cc.STATE_NO_CARRY} == dict(
                {k: v for k, v in fx['initial_regs'].items() if k != 'a7'}, a7=fx['initial_a7'], pc=fx['entry_pc'])
            tracker = new_tracker(fx)
        steps = sorted(set(p['step'] for p in row['phases']))
        assert (steps[0], steps[-1]) == ((0 if name == 'open' else SAVE_FIRST), last) and steps == list(range(steps[0], last + 1))
        if name == 'save':
            assert row['fixture']['entry_pc'] == cc.BIOS      # stored from step 31: resumes from the previous C++ output
        result = run_row(ctx, row, folder, start, tracker, name, shared, register=CHAIN_LABEL)
        out.append((name, result))
        start = result['end']
    return out, tracker


def audit_native(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_card_menu_nested.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-card-menu-nested-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert report['model_checks_all_equal'] is True and not report['contract_discrepancies']
    assert all(row['equal'] for row in report['contract_byte_rows'])
    refs = {}
    for name, expected in report['inputs'].items():
        mapped = ROOT / name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT) else Path(name)
        assert cc.digest(mapped) == expected, name
        refs[str(mapped.resolve())] = expected
    refs[str(path.resolve())] = NATIVE_SHA
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    lib = report['oracle']['library']
    lib = str(ROOT / lib[len(MAIN_ROOT):]) if lib.startswith(MAIN_ROOT) else lib
    assert cc.digest(lib) == report['oracle']['library_sha256']
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    assert report['artifacts']['source.json'] == cc.digest(NATIVE_DIR / 'source.json')
    assert tuple(report['nested_block_starts']) == NESTED_BLOCK_STARTS and len(NESTED_BLOCK_STARTS) == 11
    assert tuple(report['boundary_stop_pcs']) == BIOS_STOPS
    assert tuple(tuple(r) for r in report['new_ranges']) == (NESTED_RANGE, )
    contract_text = (ROOT / 'docs/analysis/animation-machine-card-menu-nested-contract.md').read_text()
    line = next(l for l in contract_text.splitlines() if l.startswith('- Block 시작 PC:'))
    listed = tuple(int(x, 16) for x in re.findall(r'`([0-9a-f]{4})`', line.split('그 밖')[0]))
    assert listed == NESTED_BLOCK_STARTS, 'contract block list'
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        instructions[instruction['cpu_address']] = instruction
    covered = set(report['covered_PCs'])
    assert set(NESTED_BLOCK_STARTS) <= covered and set(NESTED_BLOCK_STARTS) <= set(instructions)
    rows = report['results'] + report['guarded_results']
    assert len(rows) == report['cases'] + report['guarded_cases'] == 62
    assert [r['index'] for r in rows] == list(range(62))
    split_count = sum(len(r['phases']) for r in rows)
    control_count = sum(len(r['continuous_control']) for r in rows)
    # the observer counts the unstored split-free prefix (steps 0..36: 111 phase indices, 37 control indices) too
    first_phase, first_control = rows[0]['phases'][0], rows[0]['continuous_control'][0]
    assert (first_phase['index'], first_phase['step'], first_control['index'], first_control['step']) == (111, 37, 37, 37)
    assert (split_count + 111, control_count + 37) == (report['total_split_phases'], report['total_control_phases'])
    assert (split_count, control_count) == (11494, 240) and report['fresh_CPU_runs'] == 307
    assert len(report['artifacts']) == 115421
    for row in rows:
        assert row['reproduced_twice'] and row['continuous_split_equivalent']
        assert bool(row['guarded']) == (row['group'] == 'guard' or row['label'].startswith('guard-'))
    assert rows[0]['group'] == 'chain' and sum(r['group'] == 'chain' for r in rows) == 1
    assert rows[0]['label'] == CHAIN_LABEL and report['nested_summary']['first_step'] == 37
    assert report['nested_summary']['last_step'] == 109 and report['nested_summary']['total_chain_frames_nested'] == 73
    # declared register changes at step boundaries recorded by the observer == the host changes found in the rows
    declared = sorted((d['condition'], d['step'], d['change']['name'], d['change']['value'])
                      for d in report['declared_register_changes_at_step_boundaries'])
    assert declared == sorted([(CHAIN_LABEL, 'nested-f073', 'a6', PARENT),
                               ('fresh-nested-parent-cleanup-480ac', 'nested-f073', 'a6', PARENT),
                               ('connected-bios3-stop-to-no-save-nested', 'nosave-nested-f073', 'a6', PARENT)])
    return report, rows, refs, instructions, static


def load_reports(program):
    """Hash-pinned observation reports of the chain prefix and the instruction tables they bring."""
    reports = {}
    merged = {}
    for name, (folder, pin) in REPORTS.items():
        path = ROOT / 'artifacts' / folder / 'observation.json'
        assert cc.digest(path) == pin, name
        report = json.loads(path.read_text())
        assert report['failure'] is None
        reports[name] = report
        assert report['artifacts']['source.json'] == cc.digest(path.parent / 'source.json')
        for instruction in json.loads((path.parent / 'source.json').read_text())['instructions']:
            at, size = instruction['rom_offset'], instruction['size']
            assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
            known = merged.setdefault(instruction['cpu_address'], instruction)
            assert (known['mnemonic'], known['op_str'], known['size']) == (
                instruction['mnemonic'], instruction['op_str'], size), hex(instruction['cpu_address'])
    return reports, merged


def compare(ctx, report, rows, bios_start, reports):
    shared = Shared()
    pool = ctx['pool']
    row_pool = ThreadPoolExecutor(max_workers=12)
    frames = report['nested_frames']
    results = {}
    try:
        chain_row = rows[0]
        prefix, tracker = chain_prefix(ctx, bios_start, shared, reports, rows)
        results['prefix'] = prefix
        end_prefix = prefix[-1][1]['end']
        fx = chain_row['fixture']
        # the nested chain row continues from the previous actual C++ output (step 36 end)
        assert end_prefix[1]['pc'] == 0x2ac2 and sha(end_prefix[0]) == shared.meta[(CHAIN_LABEL, SAVE_LAST)][0]
        assert fx['entry_pc'] == cc.BIOS
        nested = run_row(ctx, chain_row, NATIVE_DIR, end_prefix, tracker, 'c000', shared, register=CHAIN_LABEL,
                         frames=frames[CHAIN_LABEL])
        results['chain'] = nested
        futures = []
        for row in rows[1:]:
            futures.append(row_pool.submit(run_other, ctx, row, shared, bios_start, frames.get(row['label'])))
        others = []
        for future in futures:
            try:
                others.append(future.result())
            except BaseException:
                with shared.cv:
                    shared.failed = True
                    shared.cv.notify_all()
                raise
        results['others'] = others
    finally:
        row_pool.shutdown(wait=True)
    return shared, results


def run_other(ctx, row, shared, bios_start, frames):
    start, origin, declared, source = row_start(row, shared, bios_start)
    result = run_row(ctx, row, NATIVE_DIR, start, new_tracker(row['fixture']), 'c%03d' % row['index'], shared,
                     frames=frames)
    result['summary'].update(origin=origin, declared_initial_registers={k: [hex(v[0]), hex(v[1])]
                                                                         for k, v in declared.items()},
                             source_step=source[1])
    return result


def compare_guards(exe, guards, resources, guard_errors, native_guards):
    rows = []
    for row, phase, ram, state, pvc, bank in guards:
        result, outgoing, out_pvc, ports, error = run(
            exe, 'guard_%s' % row['label'], ram, dict(state, carry=2), pvc, bank, resources,
            stop=phase['stop_pc'], external=row['fixture']['external'], keep=True)
        assert not result['ok'], row['label']
        assert error.strip() == guard_errors[row['label']], (row['label'], error)
        assert {k: result[k] for k in STATE_KEYS} == dict(state, carry=2)
        assert outgoing == ram and out_pvc == pvc and result['bank_base'] == bank
        assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
        assert phase['guard'] == native_guards[row['label']]
        rows.append(dict(label=row['label'], native_guard=phase['guard'], checked_API_error=error.strip(),
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    return rows


def interior_pcs(instructions):
    # the instruction table tiles the whole nested range without gaps (every PC of a698..a70a is covered)
    pc = NESTED_RANGE[0]
    while pc < NESTED_RANGE[1]:
        pc += instructions[pc]['size']
    assert pc == NESTED_RANGE[1]
    return [pc for pc in sorted(instructions) if in_range(pc) and pc not in NESTED_BLOCK_STARTS]


def negatives(exe, base, starts, instructions, resources, neg_errors):
    out = []

    def reject(label, start, changes=None, stop=0xff000, external=0):
        r, s, p, b = start
        s = dict(s, carry=2)
        s.update(changes or {})
        result, outgoing, out_pvc, ports, error = run(
            exe, 'negative_' + label, r, s, p, b, resources, stop=stop, external=external, keep=True)
        assert not result['ok'], label
        assert error.strip() == neg_errors[label], (label, error.strip())
        assert {k: result[k] for k in STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label=label, error=error.strip(), all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))

    interior = interior_pcs(instructions)
    for pc in interior:
        reject('interior_direct_entry_%06x' % pc, base, {'pc': pc})
    for pc in BIOS_STOPS:
        reject('boundary_direct_entry_%06x' % pc, base, {'pc': pc})
    for pc in (0xa696, 0xa70c):       # first PCs below/above the nested range: owned by the close / input cores
        reject('outside_range_entry_%06x' % pc, base, {'pc': pc})
    # internal entries with a declared stack: run past the intended return with a stop that is never reached
    for label in ('a698-direct-natural', 'a6da-direct-pushed-00107efe', 'a6b2-direct-popped-00107eee'):
        reject('%s_with_unreached_stop' % label, starts[(label, 0)])
    return out, len(interior)


def zero_step(exe, base, resources):
    ram, state, pvc, bank = base
    rows = []
    for pc in NESTED_BLOCK_STARTS:
        for carry in (0, 1, 2):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = run(exe, 'zero_%06x_%d' % (pc, carry), ram, s, pvc, bank,
                                                         resources, stop=pc, keep=True)
            assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
            assert {k: result[k] for k in STATE_KEYS} == s
            assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
            assert result['external_reads'] == 0 and not ports
            rows.append(dict(pc=pc, carry=carry, all_input_state_preserved=True))
    return rows


def boundary_zero_step(exe, base, resources):
    """stop == entry PC at the BIOS boundaries: recorded as observed behavior (not required by the contract)."""
    ram, state, pvc, bank = base
    rows = []
    for pc in BIOS_STOPS:
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = run(exe, 'zero_boundary_%06x' % pc, ram, s, pvc, bank, resources,
                                                      stop=pc, keep=True)
        assert {k: result[k] for k in STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
        rows.append(dict(pc=pc, ok=result['ok'], error=error.strip()))
    return rows


PINNED_GUARD = {
    'guard-odd-A2-a698': EVEN,
    'guard-odd-A7-a698': EVEN,
    'guard-odd-A7-a6da': EVEN,
    'guard-odd-A7-a6b2': EVEN,
    'guard-unsupported-callback': UNSUPPORTED_MACHINE}


ODD_JSR = 'animation fade card odd JSR target'
NEG_ERRORS = {
    'outside_range_entry_00a696': 'unsupported animation card menu close PC',
    'outside_range_entry_00a70c': 'unsupported animation card menu input PC',
    'boundary_direct_entry_c00468': UNSUPPORTED_MACHINE,
    'boundary_direct_entry_c0046e': UNSUPPORTED_MACHINE,
    # the declared return LONG 2ac2 is consumed only when the stop is 2ac2; with an unreached stop the dispatcher
    # runs on into the next object and meets the odd JSR target of the fixture chain: full rollback.
    'a698-direct-natural_with_unreached_stop': ODD_JSR,
    'a6da-direct-pushed-00107efe_with_unreached_stop': ODD_JSR,
    'a6b2-direct-popped-00107eee_with_unreached_stop': ODD_JSR}


class Errors(dict):
    """Pinned exact strings; every interior address of the nested range is rejected by the nested core."""
    def __missing__(self, label):
        if label.startswith('interior_direct_entry_'):
            return UNSUPPORTED_NESTED
        raise KeyError(label)


NEG_ERRORS = Errors(NEG_ERRORS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_card_menu_nested.py', 'tools/verify_animation_machine_card_child.py',
                 'tools/observe_animation_machine_card_menu_nested.py',
                 'docs/analysis/animation-machine-card-menu-nested-contract.md',
                 'engine/src/animation_machine_card_menu_nested.cpp', 'engine/src/animation_machine_card_menu_save.cpp',
                 'engine/src/animation_machine_card_menu_close.cpp', 'engine/src/animation_machine_card_menu_input.cpp',
                 'engine/src/animation_machine_card_menu_open.cpp', 'engine/src/animation_machine_card_menu.cpp',
                 'engine/src/animation_machine_card_child.cpp', 'engine/src/animation_machine.cpp',
                 'engine/src/animation_machine_internal.h', 'engine/tests/animation_machine_card_menu_nested_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    # Reviewed fade/card chain re-run in actual C++ gives the c00468 stop output; the card child, push, open, input,
    # save prefix then continues from it inside this verifier (re-run end to end in C++).
    cc.OUT = OUT / 'card_child_chain'
    cc.OUT.mkdir(parents=True, exist_ok=True)
    bios_start = cc.fade_chain_bios_output(exe, program, source, resources)
    report, rows, native_refs, nested_instructions, static = audit_native(program, source)
    reports, merged = load_reports(program)
    instructions = dict(merged)
    for pc, item in nested_instructions.items():
        known = instructions.setdefault(pc, item)
        assert (known['mnemonic'], known['op_str'], known['size']) == (item['mnemonic'], item['op_str'], item['size'])
    refs.update(native_refs)
    pool = ThreadPoolExecutor(max_workers=10)
    ctx = dict(exe=exe, program=program, resources=resources, instructions=instructions, pool=pool)
    try:
        shared, results = compare(ctx, report, rows, bios_start, reports)
    finally:
        pool.shutdown(wait=True)
    prefix, chain = results['prefix'], results['chain']
    others = results['others']
    every = [r for _n, r in prefix] + [chain] + others
    covered = set(chain['covered'])
    for item in others:
        assert not (covered & item['covered'])
        covered |= item['covered']
    assert covered == set(report['artifacts']) - {'source.json'}, (len(covered), len(report['artifacts']))
    manifest = hashlib.sha256()
    for name in sorted(covered):
        manifest.update(('%s %s\n' % (name, report['artifacts'][name])).encode())
    def blank():
        return dict(cases=0, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0,
                    carry_probe_preserved=0, snapshots_checked=0, frames_checked=0,
                    declared_host_changes=dict(ram=0, pc=0, a7_add=0, reg=0))
    totals, nested_totals = blank(), blank()
    reg_changes = []
    parent_records = []
    carry_histogram = {0: 0, 1: 0, 2: 0}
    single_block = {}
    for item in every:
        targets = [totals] + ([] if any(item is r for _n, r in prefix) else [nested_totals])
        for t in targets:
            for key, value in item['totals'].items():
                if key in ('reg_changes', 'record_7e_80_read_from_parent'):
                    continue
                if isinstance(value, dict):
                    for k2, v2 in value.items():
                        t[key][k2] += v2
                else:
                    t[key] += value
        reg_changes.extend(item['totals']['reg_changes'])
        parent_records.extend(item['totals']['record_7e_80_read_from_parent'])
        for key, value in item['row_carry'].items():
            carry_histogram[key] += value
        for block, outcomes in item['single'].items():
            single_block.setdefault(block, set()).update(outcomes)
    # the nested observation's own rows only (prefix rows belong to the open/save observations)
    guard_phases = sum(1 for r in rows for p in r['phases'] if p['guard'] is not None)
    assert nested_totals['split'] == sum(len(r['phases']) for r in rows) - guard_phases == 11494 - 5
    assert nested_totals['control'] == sum(len(r['continuous_control']) for r in rows) - 5
    assert sorted(parent_records) == ['connected-bios3-stop-to-no-save-nested', 'fresh-nested-parent-cleanup-480ac']
    assert sorted(reg_changes) == sorted([
        (CHAIN_LABEL, 'nested-f073', 'a6', PARENT),
        ('fresh-nested-parent-cleanup-480ac', 'nested-f073', 'a6', PARENT),
        ('connected-bios3-stop-to-no-save-nested', 'nosave-nested-f073', 'a6', PARENT)])
    # fresh frames equal the long-lived chain in actual C++ (matched by native output identity)
    by_identity = {}
    for identity, out_nc, out_c in chain['records']:
        by_identity.setdefault(identity, (out_nc, out_c))
    chain_phase_matches = chain_carry_matches = 0
    for item in others:
        if item['summary']['group'] != 'fresh-frame':
            continue
        for j, (identity, out_nc, out_c) in enumerate(item['records']):
            assert identity in by_identity, (item['summary']['label'], j)
            assert by_identity[identity][0] == out_nc, (item['summary']['label'], j)
            chain_phase_matches += 1
            chain_carry_matches += by_identity[identity][1] == out_c
    assert chain_phase_matches == report['chain_vs_fresh_phases_compared'] == 673, chain_phase_matches
    # prefix and chain steps equal the reviewed save/open native evidence (RAM/outgoing registers of each step)
    ends, starts = shared.ends, {}
    for item in every:
        if item['first_start'] is not None:
            starts[(item['summary']['label'], 0)] = item['first_start']
        if item['guard_start'] is not None:
            starts[(item['summary']['label'], 'guard')] = item['guard_start']
    prefix_equal = {}
    for name, step_range in (('open', range(0, OPEN_LAST + 1)), ('save', range(SAVE_FIRST, SAVE_LAST + 1))):
        folder, _pin = REPORTS[name]
        row = next(r for r in reports[name]['results'] if r['label'] == (OPEN_CHAIN if name == 'open' else SAVE_CHAIN))
        count = 0
        for step in step_range:
            last = [p for p in row['phases'] if p['step'] == step][-1]
            ram_name = next(n for n in last['artifacts'] if n.endswith('_ram_after.bin'))
            assert sha((ROOT / 'artifacts' / folder / ram_name).read_bytes()) == last['artifacts'][ram_name]
            ram, state, _pvc, _bank = ends[(CHAIN_LABEL, step)]
            assert shared.meta[(CHAIN_LABEL, step)][0] == last['artifacts'][ram_name]
            assert sha(ram) == last['artifacts'][ram_name] and {k: state[k] for k in common.REGS + ('pc',)} == last['outgoing'], step
            count += 1
        prefix_equal[name] = dict(condition=row['label'], steps_compared=count, equal=True)
    base = ends[(CHAIN_LABEL, SAVE_LAST)]
    assert base[1]['pc'] == 0x2ac2
    final = ends[(CHAIN_LABEL, 109)]
    assert final[1]['pc'] == 0x2ac2 and final[1]['a7'] == 0x1ff000
    guards = [item['guard'] for item in every if item['guard'] is not None]
    native_guards = {g['label']: g['guard'] for g in report['guard_reports']}
    assert len(guards) == len(native_guards) == 5
    guarded = compare_guards(exe, guards, resources, PINNED_GUARD, native_guards)
    negative, interior_count = negatives(exe, base, starts, instructions, resources, NEG_ERRORS)
    zero = zero_step(exe, base, resources)
    boundary_zero = boundary_zero_step(exe, base, resources)
    blocks = static_blocks(instructions)
    preserving = static_preserving(instructions, blocks)
    assert preserving == set(CARRY_PRESERVING)
    for pc, outcomes in single_block.items():
        assert outcomes == {pc in CARRY_PRESERVING}, (hex(pc), outcomes)
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert cc.digest(ROOT / name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    local = {str(path.resolve()): cc.digest(path) for path in OUT.rglob('*')
             if path.is_file() and path != report_path}
    unique = {}
    for name, expected in list(inputs.items()) + list(refs.items()) + list(local.items()):
        key = str((ROOT / name).resolve())
        assert key not in unique or unique[key] == expected
        unique[key] = expected
    out_rows = [dict(r['summary']) for r in others]
    prefix_rows = [dict(r['summary'], native_report=n) for n, r in prefix]
    chain_row = chain['summary']
    totals['chain_phase_matches'] = chain_phase_matches
    totals['chain_carry_matches'] = chain_carry_matches
    totals['carry_histogram'] = {cc.CARRY_NAME[k]: v for k, v in carry_histogram.items()}
    result = dict(schema_version=1, source=source, inputs=inputs, artifacts=dict(refs, **local),
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA,
                  contract_sha256=CONTRACT_SHA,
                  native_artifacts_hash_checked=dict(count=len(covered), manifest_sha256=manifest.hexdigest()),
                  prefix_equal_to_reference_observations=prefix_equal,
                  actual_CPP=dict(totals, nested_observation_rows_only=nested_totals, prefix_rows=prefix_rows,
                                  chain_row=chain_row, rows=out_rows),
                  declared_register_changes_at_step_boundaries=[list(c) for c in sorted(reg_changes)],
                  declared_initial_registers=dict(
                      allowed_keys=list(DECLARED_INITIAL_KEYS),
                      rows_with_declared_initial=sum(1 for r in out_rows if r['declared_initial_registers']),
                      rows_total=len(out_rows)),
                  observer_record_note=dict(
                      rows=sorted(parent_records),
                      fact='in these two rows the native frame record fields child_7e/child_80 of the parent re-entry frame equal the parent object 7e/80 (A6=102000); the chain row record reads the child; C++ RAM equals native RAM in all three, so only the record naming differs'),
                  native_guards_checked_API=guarded,
                  negatives=negative, negative_count=len(negative) + len(guarded),
                  interior_PCs_rejected=interior_count, zero_step=zero, boundary_zero_step=boundary_zero,
                  carry=dict(
                      contract_preserving_blocks=[hex(pc) for pc in CARRY_PRESERVING],
                      static_source_walk_preserving=sorted(hex(pc) for pc in preserving),
                      observed_single_block_starts=sorted(hex(pc) for pc in single_block),
                      observed_preserving_starts=sorted(hex(pc) for pc in single_block if pc in CARRY_PRESERVING),
                      not_observed_single_block=sorted(hex(pc) for pc in NESTED_BLOCK_STARTS if pc not in single_block)),
                  bios_start=dict(chain_label=bios_start[0][0], step=bios_start[0][1],
                                  ram_sha256=sha(bios_start[1][0])),
                  carry_check='C++ carry equals source-opcode walk over native-executed PCs (ORI/ANDI CCR known, flow-only preserved, else Unknown); native SR never read',
                  normalized_reference_paths=len(unique), compile_command=command, failure=None,
                  ROM_unchanged=True,
                  limits=['Controlled fixtures; frame re-entry (PC=2ab8/2ab8-region), the BIOS resumes of the save chain, the input BYTEs 104cba/104cc0, the cleanup fixture (1d/6c/104ca4) and the parent re-entry A6 are declared host changes, not a natural scheduler, BIOS or input routine.',
                          'The nested observer splits only the nested frames (steps 37..109); the prefix steps 0..36 are replayed here from the split phases of the reviewed open and save observations, not re-observed by the nested observer.',
                          'Carry is a source-opcode classification (native SR is never read), not a native C measurement; ADDA/SUBA are conservatively Unknown.',
                          'c00468/c0046e (BIOS card stops) are stop boundaries only; BIOS card internals, video port screen meaning and everything after the 2a00 child/parent removal are out of scope.',
                          'Native observation artifacts are hash checked (115421 files) and streamed, not re-executed here.',
                          'Checked failures preserve API outputs, not original CPU fault rollback; interior direct entries and the boundary/outside entries have no native guard (API-only rejection).'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'],
                         resumes=totals['resumes'], negatives=result['negative_count'], interior=interior_count,
                         zero_step=len(zero), carry=totals['carry_histogram'],
                         sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
