"""Original card-menu input frame (a406), bf2c hook, a70a/a1ee and 9fc4/9ff4 native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an immutable
input (this verifier never invokes the observer main). C++ resumes only from the previous actual C++
output plus the host changes recorded in the native fixture (RAM write, PC change, A7 add), each
asserted against the step-start PC/A7. The chain starts from the actual C++ output of the reviewed
fade/card chain (c00468 stop) and is re-run end to end in C++ (push, open, input frames). Every other
condition starts from an actual C++ chain step output selected by native RAM identity and register
equality. a662 (close), bd26 (BIOS card save) and non-bf2c hook targets are stop boundaries only:
never executed. Native files are streamed and hash checked against the report (memory stays bounded);
per-invocation scratch files are removed after the comparison and only negatives/zero-step/guards
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
OUT = ROOT / 'artifacts/animation_machine_card_menu_input_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_card_menu_input_native'
NATIVE_SHA = '49c1ba52f7ec11dc1929022f7dc6b455b434681d472e9a39631c69ea98ce9b46'
NATIVE_TOOL_SHA = 'cbd6fdf19fcc4c5ccec8126be1ab9f98501df5a393dd9805da3f1b7802e66104'
CONTRACT_SHA = '78fe3d1a0c855e1e491d60c66afca710077585edaf8516076bb89386c72ca604'
REFERENCES = {   # name -> (observation path, observation sha256, chain condition, chain step)
    'child': ('artifacts/animation_machine_card_child_native/observation.json',
              '3e48b69e4827d5a25f7085aee1c81bf6bc0b41a64daa159a3232e690c16f3312',
              'chain-full-bios-resume-to-a29c', 24),
    'push': ('artifacts/animation_machine_card_menu_native/observation.json',
             'da76f4643efafafdc8929a9cd73a24a1e3a434e49275e5babcadd53e5c45bfbc',
             'chain-full-bios-resume-to-a370', 25),
    'open': ('artifacts/animation_machine_card_menu_open_native/observation.json',
             '154b4ed588a1bf7c9615bc7c6c3710492e4c0a711aca710b20f6bd21a7390ab4',
             'chain-full-bios-resume-to-open', 30)}
FADE_NATIVE = ('artifacts/animation_machine_fade_card_native/observation.json',
               'f53387b7122286eca94c55371a34a09f900489eb9ab2766f9c98e086da7f57fc')
OPEN_CHAIN_LAST_STEP = 30
DECLARED_INITIAL = {'guard-odd-A7-a43e': ('a7',), 'guard-odd-A7-2ac0': ('a7',)}   # odd A7 is the declared guard fixture
A662, BD26, H9000, HC2C0, HFFF00 = 0xa662, 0xbd26, 0x9000, 0xc2c0, 0xfff00
BOUNDARY_PCS = (A662, BD26)
HOOK_STOP_PCS = (H9000, HC2C0, HFFF00)
INPUT_BLOCK_STARTS = (
    0x9fc4, 0x9ff4, 0xa1ee, 0xa406, 0xa412, 0xa416, 0xa41a, 0xa424, 0xa42a, 0xa42c, 0xa43e, 0xa442, 0xa444, 0xa44e,
    0xa458, 0xa46a, 0xa472, 0xa484, 0xa488, 0xa492, 0xa496, 0xa4b0, 0xa4b8, 0xa4d2, 0xa4da, 0xa4f4, 0xa4fc, 0xa516,
    0xa51e, 0xa538, 0xa540, 0xa55a, 0xa562, 0xa566, 0xa570, 0xa574, 0xa57e, 0xa582, 0xa58c, 0xa596, 0xa5a0, 0xa5aa,
    0xa5b4, 0xa5c6, 0xa5ce, 0xa70a, 0xa714, 0xbf2c, 0xbf34, 0xbf3e, 0xbf48, 0xbf50, 0xbf56, 0xbf5c, 0xbf6a, 0xbf72,
    0xbf76, 0xbf82, 0xbf8a, 0xbf8e)
INPUT_RANGES = ((0x9fc4, 0x9fce), (0x9ff4, 0x9ffe), (0xa1ee, 0xa1fa), (0xa406, 0xa5d2), (0xa70a, 0xa71a),
                (0xbf2c, 0xbf94))      # half-open, equal to native new_ranges
# Inclusive router ranges of animation_machine.cpp that reach animation_card_menu_input_block.
ROUTER_RANGES = ((0x9fc4, 0x9fcc), (0x9ff4, 0x9ffc), (0xa1ee, 0xa1f8), (0xa406, 0xa5d0), (0xa70a, 0xa718),
                 (0xbf2c, 0xbf92))
CARRY_PRESERVING = (0xa412, 0xa41a, 0xa42a, 0xa442, 0xa488, 0xa562, 0xa566, 0xa570, 0xa574, 0xa57e, 0xa714,
                    0xbf50, 0xbf8e)
BRANCH_ROOTS = ('bra', 'bsr', 'beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt',
                'bgt', 'ble', 'rts', 'jmp', 'jsr')
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_INPUT = 'unsupported animation card menu input PC'
ODD_JUMP = 'animation card menu input odd jump target'
EVEN = 'program bus requires even WORD/LONG address'
MARKER = cc.MARKER
STATE_KEYS = common.STATE_KEYS


def sha(data):
    return cc.sha(data)


def rd(ram, address, size):
    return cc.rd(ram, address, size)


def in_ranges(pc, ranges, inclusive=False):
    return any(low <= pc <= high if inclusive else low <= pc < high for low, high in ranges)


def run(exe, label, ram, state, pvc, bank, resources, stop, external=0, keep=False):
    """common.invoke plus removal of the scratch files unless the case is kept as evidence."""
    result = common.invoke(exe, OUT, label, ram, state, pvc, bank, resources, stop=stop, external=external)
    if not keep:
        for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin', '_state.json'):
            (OUT / (label + suffix)).unlink()
    return result


def load_phase(phase, covered, snapshots=False):
    """Read and hash-check every native file of a phase; return payload dict, trace and snapshots."""
    data = {}
    for name, expected in phase['artifacts'].items():
        value = (NATIVE_DIR / name).read_bytes()
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
    assert not (set(executed) & (set(BOUNDARY_PCS) | {H9000, HFFF00})), 'boundary executed'
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
    """Source-opcode walk of each input block (to the branch/jump or the next block start)."""
    starts = set(INPUT_BLOCK_STARTS)
    blocks = {}
    for start in INPUT_BLOCK_STARTS:
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
        results = {cc.classify_carry(instructions, carry, pcs) for carry in (1, 2)}
        if cc.classify_carry(instructions, 1, pcs) == 1 and cc.classify_carry(instructions, 2, pcs) == 2:
            out.add(start)
        assert results <= {0, 1, 2}
    return out


def reference_step(name, step_expected=None):
    """Last phase ram_after sha of the reference chain step, re-hashed from the reference artifacts."""
    path, pin, condition, step = REFERENCES[name]
    assert cc.digest(ROOT / path) == pin, name
    report = json.loads((ROOT / path).read_text())
    row = next(r for r in report['results'] if r['label'] == condition)
    phases = [p for p in row['phases'] if p['step'] == step]
    last = phases[-1]
    ram_name = next(n for n in last['artifacts'] if n.endswith('_ram_after.bin'))
    folder = (ROOT / path).parent
    value = (folder / ram_name).read_bytes()
    assert sha(value) == last['artifacts'][ram_name]
    return value, last['outgoing']


def merged_instructions(program, instructions):
    """Instruction tables of every observation the chain passes through (each hash checked via its report)."""
    merged = dict(instructions)
    sources = [FADE_NATIVE] + [(v[0], v[1]) for v in REFERENCES.values()]
    for path, pin in sources:
        assert cc.digest(ROOT / path) == pin, path
        report = json.loads((ROOT / path).read_text())
        folder = (ROOT / path).parent
        assert report['artifacts']['source.json'] == cc.digest(folder / 'source.json')
        for instruction in json.loads((folder / 'source.json').read_text())['instructions']:
            at, size = instruction['rom_offset'], instruction['size']
            assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
            known = merged.setdefault(instruction['cpu_address'], instruction)
            assert (known['mnemonic'], known['op_str'], known['size']) == (
                instruction['mnemonic'], instruction['op_str'], size), hex(instruction['cpu_address'])
    return merged


def audit_native(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_card_menu_input.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-card-menu-input-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    refs = {}
    for name, expected in report['inputs'].items():
        path_in = helpers.resolve_ref(ROOT, NATIVE_DIR, name)
        assert cc.digest(path_in) == expected, name
        refs[str(path_in.resolve())] = expected
    refs[str(path.resolve())] = NATIVE_SHA
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(report['oracle']['library']) == report['oracle']['library_sha256']
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    assert report['artifacts']['source.json'] == cc.digest(NATIVE_DIR / 'source.json')
    assert tuple(report['input_block_starts']) == INPUT_BLOCK_STARTS and len(INPUT_BLOCK_STARTS) == 60
    assert tuple(report['boundary_stop_pcs']) == (A662, BD26) and tuple(report['hook_stop_pcs']) == HOOK_STOP_PCS
    assert tuple(tuple(r) for r in report['new_ranges']) == INPUT_RANGES
    contract_text = (ROOT / 'docs/analysis/animation-machine-card-menu-input-contract.md').read_text()
    line = next(l for l in contract_text.splitlines() if l.startswith('- Block 시작 PC:'))
    listed = tuple(int(x, 16) for x in re.findall(r'`([0-9a-f]{4})`', line.split('(60개)')[0]))
    assert listed == INPUT_BLOCK_STARTS, 'contract block list'
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        instructions[instruction['cpu_address']] = instruction
    assert not (set(BOUNDARY_PCS) & set(instructions))
    covered = set(report['covered_PCs'])
    assert set(INPUT_BLOCK_STARTS) <= covered and set(INPUT_BLOCK_STARTS) <= set(instructions)
    rows = report['results'] + report['guarded_results']
    assert len(rows) == report['cases'] + report['guarded_cases'] == 99
    assert [r['index'] for r in rows] == list(range(99))
    split_count = sum(len(r['phases']) for r in rows)
    control_count = sum(len(r['continuous_control']) for r in rows)
    assert (split_count, control_count) == (report['total_split_phases'], report['total_control_phases'])
    assert report['fresh_CPU_runs'] == 495
    assert len(report['artifacts']) == 359545
    for row in rows:
        assert row['reproduced_twice'] and row['continuous_split_equivalent']
        assert bool(row['guarded']) == (row['group'] == 'guard' or row['label'].startswith('guard-'))
    assert rows[0]['group'] == 'chain' and sum(r['group'] == 'chain' for r in rows) == 1
    return report, rows, refs, instructions, static


def start_of_row(row, shared, bios_start, first_data):
    """C++ start state: previous actual C++ output (BIOS chain stop / chain step end)."""
    fx = row['fixture']
    native_pvc = first_data['pvc_before.bin']
    assert sha(native_pvc) == fx['initial_PVC_sha256']
    native_masked = sha(cc.masked_pvc(native_pvc))
    want = dict({k: v for k, v in fx['initial_regs'].items() if k != 'a7'}, a7=fx['initial_a7'], pc=fx['entry_pc'])
    if fx['entry_pc'] == cc.BIOS:
        key, (ram, src_state, pvc, bank) = bios_start
        origin = 'actual C++ output of the fade/card chain %s step %d (stop c00468)' % (key[0], key[1])
        assert sha(ram) == fx['initial_RAM_sha256'] and sha(cc.masked_pvc(pvc)) == native_masked
        assert bank == fx['bank_state'][0]
        assert {k: src_state[k] for k in cc.STATE_NO_CARRY} == want
        return ram, dict(want, carry=0), pvc, bank, origin

    declared = DECLARED_INITIAL.get(row['label'], ())

    def candidates():
        return [c for c in shared.sources.get(fx['initial_RAM_sha256'], [])
                if {k: shared.ends[c][1][k] for k in cc.STATE_NO_CARRY if k not in declared} ==
                {k: want[k] for k in want if k not in declared}]

    with shared.cv:
        assert shared.cv.wait_for(lambda: shared.failed or candidates(), timeout=7200) and not shared.failed, \
            row['label']
        found = candidates()
        label, step = found[0]
        ram, src_state, pvc, bank = shared.ends[found[0]]
    assert sha(ram) == fx['initial_RAM_sha256'] and sha(cc.masked_pvc(pvc)) == native_masked
    assert bank == fx['bank_state'][0]
    origin = 'actual C++ output of %s step %d (%d equal candidates)%s' % (
        label, step, len(found), (' plus declared ' + ','.join(declared)) if declared else '')
    state = dict(src_state)
    for key in declared:
        state[key] = want[key]
    return ram, state, pvc, bank, origin


def check_frame(ram, state, frame):
    """The recorded per-frame fields equal the C++ RAM/registers (A5/A6 are the live C++ registers)."""
    a5, a6 = state['a5'], state['a6']
    assert rd(ram, a6 + 0x7e, 2) == frame['child_7e_after'] and rd(ram, a6 + 0x80, 1) == frame['child_80_after']
    assert rd(ram, a5 - 0xe5, 1) == frame['e5_after'] and rd(ram, a5 - 0xe6, 1) == frame['e6_after']
    record = rd(ram, a5 - 0xee, 4)
    assert rd(ram, record + 4, 2) == frame['word4_after']
    assert rd(ram, record + 7, 1) == frame['field_7_after'] and rd(ram, record + 8, 1) == frame['field_8_after']
    assert rd(ram, record + 0xe, 1) == frame['e_after'] == frame['field_e_after']
    assert rd(ram, record + 0xf, 1) == frame['f_after'] and rd(ram, record + 0xd, 1) == frame['d_after']
    assert state['pc'] == int(frame['outgoing_pc'], 16) and state['a7'] == int(frame['outgoing_a7'], 16)
    return rd(ram, a6 + 0x7e, 2)


class Shared(object):
    """State shared by the row workers: chain step outputs other rows start from, guard/start records."""
    def __init__(self):
        self.cv = threading.Condition()
        self.failed = False
        self.ends = {}
        self.sources = {}
        self.starts = {}
        self.guards = []


def probe_task(exe, resources, instructions, label, phase_ram, phase_in, phase_pvc, phase_bank, stop, external,
               executed, probe, result, ram, pvc, ports):
    """Same phase with a known incoming C: exactly the source classification, all other outputs identical."""
    again = run(exe, label, phase_ram, dict(phase_in, carry=probe), phase_pvc, phase_bank, resources, stop=stop,
                external=external)
    assert again[0]['ok'] and not again[4]
    assert again[0]['carry'] == cc.classify_carry(instructions, probe, executed)
    assert ({k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in result.items() if k != 'carry'})
    assert again[1] == ram and again[2] == pvc and again[3] == ports
    blocks = [pc for pc in executed if pc in INPUT_BLOCK_STARTS]
    single = blocks[0] if len(blocks) == 1 and blocks[0] == executed[0] else None
    return single, again[0]['carry'] == probe


def control_task(exe, resources, label, c_ram, c_state, c_pvc, c_bank, stop, external, outgoing, events, ram_after,
                 e_pvc, e_bank, portbytes, end):
    actual = run(exe, label, c_ram, c_state, c_pvc, c_bank, resources, stop=stop, external=external)
    assert actual[0]['ok'] and not actual[4], (label, actual[4])
    common.check_result(actual, dict(outgoing=outgoing, events=events, ram_after=ram_after), e_pvc, e_bank, portbytes)
    assert (actual[1], {k: actual[0][k] for k in STATE_KEYS}, actual[2], actual[0]['bank_base']) == end, label
    return 1


def run_row(exe, program, report, row, resources, instructions, bios_start, shared, pool):
    totals = dict(cases=1, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0,
                  carry_probe_preserved=0, snapshots_checked=0, frames_checked=0,
                  declared_host_changes=dict(ram=0, pc=0, a7_add=0),
                  native_program_reads=dict(fixed_reads=0, bank_reads=0, PVC_writes=0))
    fx = row['fixture']
    covered = set()
    first_data = load_phase(row['phases'][0], set())[0]
    ram, state, pvc, bank, origin = start_of_row(row, shared, bios_start, first_data)
    chain = row['group'] == 'chain'
    expected_pvc, expected_bank = pvc, bank
    tracker = dict(bank=fx['bank_state'][0], ff8=fx['bank_state'][1], ff9=fx['bank_state'][2],
                   fixed_reads=0, bank_reads=0, PVC_writes=0)
    ctl_tracker = dict(tracker)
    frames = {f['step']: f for f in report['input_frames'].get(row['label'], [])}
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
    resumed = row_phases = control_rows = frames_seen = 0
    row_carry = {0: 0, 1: 0, 2: 0}
    w7e = []
    for step, items in steps:
        parts = []
        step_start = None
        completed = True
        for j, phase in items:
            data, trace, _s = load_phase(phase, covered)
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
            for kind in kinds:
                totals['declared_host_changes'][kind] += 1
            assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
            assert ram == data['ram_before.bin'], (row['label'], j)
            assert bank == phase['bank_before'] and kinds == [c['kind'] for c in phase['host_changes']]
            if phase['phase_in_step'] == 0:
                step_start = (ram, dict(state), pvc, bank, expected_pvc, expected_bank)
                if step == 0:
                    first_start = (ram, dict(state), pvc, bank)
            events = trace['events']
            expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
            assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
            phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
            label = 'c%03d_s%03d' % (row['index'], j)
            actual = run(exe, label, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
            assert actual[0]['ok'] and not actual[4], (row['label'], j, phase['stop_pc'], actual[4])
            common.check_result(actual, dict(outgoing=phase['outgoing'], events=events,
                                             ram_after=data['ram_after.bin']), expected_pvc, expected_bank, portbytes)
            assert actual[0]['status'] == 0
            result, ram, pvc, _, _ = actual
            want_carry = cc.classify_carry(instructions, phase_in['carry'], executed)
            assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']),
                                                    result['carry'], want_carry)
            row_carry[result['carry']] += 1
            if executed and all(in_ranges(pc, INPUT_RANGES) for pc in executed):
                for probe in (1, 2):
                    futures.append(('probe', pool.submit(
                        probe_task, exe, resources, instructions, label + 'p%d' % probe, data['ram_before.bin'],
                        phase_in, phase_pvc, phase_bank, phase['stop_pc'], fx['external'], executed, probe, result,
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
            if chain:
                with shared.cv:
                    shared.ends[(row['label'], step)] = end
                    shared.sources.setdefault(sha(parts[-1][1]['ram_after.bin']), []).append((row['label'], step))
                    shared.cv.notify_all()
            if step in frames:
                w7e.append(check_frame(ram, state, frames[step]))
                frames_seen += 1
                totals['frames_checked'] += 1
        control = controls[step]
        c_data, c_trace, c_snaps = load_phase(control, covered, snapshots=True)
        audit_phase(control, c_data, c_trace, instructions)
        audit_reads(program, ctl_tracker, control, c_trace)
        totals['snapshots_checked'] += audit_step(parts, (control, c_data, c_trace, c_snaps))
        if control['guard'] is None:
            assert completed
            c_ram, c_state, c_pvc, c_bank, e_pvc, e_bank = step_start
            assert {k: c_state[k] for k in common.REGS + ('pc',)} == control['incoming']
            e_pvc, e_bank, portbytes = cc.fold_outputs(e_pvc, e_bank, c_trace['events'])
            assert e_bank == control['modeled_bank'] and portbytes == c_data['ports.bin']
            futures.append(('control', pool.submit(
                control_task, exe, resources, 'c%03d_ctl%03d' % (row['index'], step), c_ram, c_state, c_pvc, c_bank,
                control['stop_pc'], fx['external'], control['outgoing'], c_trace['events'], c_data['ram_after.bin'],
                e_pvc, e_bank, portbytes, end)))
            control_rows += 1
    assert frames_seen == len(frames), (row['label'], frames_seen, len(frames))
    single = {}
    for kind, future in futures:
        value = future.result()
        if kind == 'probe':
            block, preserved = value
            totals['carry_probes'] += 1
            totals['carry_probe_preserved'] += preserved
            if block is not None:
                single.setdefault(block, set()).add(preserved)
    for key in ('fixed_reads', 'bank_reads', 'PVC_writes'):
        totals['native_program_reads'][key] += tracker[key]
    assert ctl_tracker['bank'] == tracker['bank']
    totals['split'] = row_phases
    totals['control'] = control_rows
    summary = dict(index=row['index'], label=row['label'], group=row['group'], origin=origin,
                   split_phases=row_phases, resumed_from_previous_Cpp_output=resumed,
                   control_steps=control_rows, steps=len(steps), guarded=bool(row['guarded']),
                   carry_counts={cc.CARRY_NAME[k]: v for k, v in row_carry.items()},
                   C_output_digest_chain_sha256=digests.hexdigest())
    guard_start = None
    if guard_item is not None and step_start is not None:
        guard_start = (step_start[0], step_start[1], step_start[2], step_start[3])
    return dict(summary=summary, totals=totals, covered=covered, records=records, guard=guard_item,
                first_start=first_start, guard_start=guard_start, single=single, w7e=w7e, row_carry=row_carry)


def compare(exe, program, report, rows, resources, instructions, bios_start):
    shared = Shared()
    pool = ThreadPoolExecutor(max_workers=10)
    row_pool = ThreadPoolExecutor(max_workers=14)
    futures = []
    try:
        for row in rows:
            futures.append(row_pool.submit(run_row, exe, program, report, row, resources, instructions,
                                           bios_start, shared, pool))
        results = []
        for future in futures:
            try:
                results.append(future.result())
            except BaseException:
                with shared.cv:
                    shared.failed = True
                    shared.cv.notify_all()
                raise
    finally:
        with shared.cv:
            shared.failed = True      # releases any waiter if we are unwinding on an error
            shared.cv.notify_all()
        row_pool.shutdown(wait=True)
        pool.shutdown(wait=True)
    covered = set()
    totals = dict(cases=0, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0,
                  carry_probe_preserved=0, snapshots_checked=0, frames_checked=0,
                  declared_host_changes=dict(ram=0, pc=0, a7_add=0),
                  native_program_reads=dict(fixed_reads=0, bank_reads=0, PVC_writes=0))
    carry_histogram = {0: 0, 1: 0, 2: 0}
    single_block = {}
    out_rows = []
    for item in results:
        for key, value in item['totals'].items():
            if isinstance(value, dict):
                for k2, v2 in value.items():
                    totals[key][k2] += v2
            else:
                totals[key] += value
        assert not (covered & item['covered'])
        covered |= item['covered']
        for key, value in item['row_carry'].items():
            carry_histogram[key] += value
        for block, outcomes in item['single'].items():
            single_block.setdefault(block, set()).update(outcomes)
        out_rows.append(item['summary'])
        if item['first_start'] is not None:
            shared.starts[(item['summary']['label'], 0)] = item['first_start']
        if item['guard_start'] is not None:
            shared.starts[(item['summary']['label'], 'guard')] = item['guard_start']
    # connected/fresh frames equal the long-lived chain tail in actual C++ (matched by native output identity)
    chain = next(r for r in results if r['summary']['group'] == 'chain')
    by_identity = {}
    for identity, out_nc, out_c in chain['records']:
        by_identity.setdefault(identity, (out_nc, out_c))
    totals['chain_phase_matches'] = totals['chain_carry_matches'] = 0
    for item in results:
        if item['summary']['group'] not in ('connected', 'fresh-frame'):
            continue
        for j, (identity, out_nc, out_c) in enumerate(item['records']):
            assert identity in by_identity, (item['summary']['label'], j)
            assert by_identity[identity][0] == out_nc, (item['summary']['label'], j)
            totals['chain_phase_matches'] += 1
            totals['chain_carry_matches'] += by_identity[identity][1] == out_c
    totals['carry_histogram'] = {cc.CARRY_NAME[k]: v for k, v in carry_histogram.items()}
    guards = [item['guard'] for item in results if item['guard'] is not None]
    return out_rows, totals, shared, guards, single_block, chain['w7e'], covered


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
    skip = set(INPUT_BLOCK_STARTS) | set(BOUNDARY_PCS)
    return [pc for pc in sorted(instructions) if in_ranges(pc, INPUT_RANGES) and pc not in skip]


def negatives(exe, base, starts, instructions, resources, neg_errors):
    out = []

    def reject(label, start, changes=None, stop=0xff000, external=0, ram_patch=None):
        r, s, p, b = start
        if ram_patch:
            r = bytearray(r)
            for address, size, value in ram_patch:
                common.native.put(r, address, size, value)
            r = bytes(r)
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
    for pc in BOUNDARY_PCS + (HFFF00, ):
        reject('boundary_direct_entry_%06x' % pc, base, {'pc': pc})
    a662 = starts[('guard-a662-without-stop', 'guard')]
    bd26 = starts[('guard-bd26-without-stop', 'guard')]
    hook = starts[('guard-hook-target-without-stop', 'guard')]
    for stop in (0x2ac2, BD26, HFFF00, HC2C0):
        reject('a662_reached_with_stop_%06x' % stop, a662, stop=stop)
    for stop in (0x2ac2, A662, HFFF00, HC2C0):
        reject('bd26_reached_with_stop_%06x' % stop, bd26, stop=stop)
    for stop in (0x2ac2, A662, BD26, HC2C0):
        reject('hook_fff00_reached_with_stop_%06x' % stop, hook, stop=stop)
    # Positive controls: the same inputs succeed when the matching boundary is the stop.
    controls = []
    for label, stop in (('guard-a662-without-stop', A662), ('guard-bd26-without-stop', BD26),
                        ('guard-hook-target-without-stop', HFFF00)):
        r, s, p, b = starts[(label, 'guard')]
        result, _, _, _, error = run(exe, 'control_' + label, r, dict(s, carry=2), p, b, resources, stop=stop, keep=True)
        assert result['ok'] and not error and result['pc'] == stop and result['status'] == 0, label
        controls.append(dict(label=label, stop=hex(stop), ok=True))
    return out, controls, len(interior)


def odd_jump_negative(exe, starts, program_rows, resources, neg_errors, covered):
    """API-only: an odd descriptor hook target is a checked error (no native guard)."""
    row = next(r for r in program_rows if r['label'] == 'hook-target-fff00')
    phase = row['phases'][0]
    write = next(c for c in phase['host_changes'] if c['kind'] == 'ram' and c['size'] == 4 and c['value'] == HFFF00)
    start = starts[('hook-target-fff00', 0)]
    r, s, p, b = start
    r = bytearray(r)
    assert rd(r, write['address'], 4) == HFFF00
    common.native.put(r, write['address'], 4, HFFF00 + 1)
    r = bytes(r)
    s = dict(s, carry=2)
    label = 'odd_hook_target_fff01'
    result, outgoing, out_pvc, ports, error = run(exe, 'negative_' + label, r, s, p, b, resources, stop=HFFF00,
                                                   keep=True)
    assert not result['ok'] and error.strip() == neg_errors[label], error
    assert {k: result[k] for k in STATE_KEYS} == s and outgoing == r and out_pvc == p and ports == MARKER
    return dict(label=label, error=error.strip(), all_API_outputs_preserved=True,
                native_exception_rollback_equivalence_claimed=False)


def zero_step(exe, base, resources):
    ram, state, pvc, bank = base
    rows = []
    for pc in INPUT_BLOCK_STARTS:
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


def boundary_zero_step(exe, base, resources, expected):
    """stop == entry PC at the boundaries: recorded as observed behavior (not required by the contract)."""
    ram, state, pvc, bank = base
    rows = []
    for pc in BOUNDARY_PCS + (HFFF00, ):
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = run(exe, 'zero_boundary_%06x' % pc, ram, s, pvc, bank, resources,
                                                      stop=pc, keep=True)
        assert result['ok'] == expected[pc], (hex(pc), error)
        assert {k: result[k] for k in STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
        rows.append(dict(pc=pc, ok=result['ok'], error=error.strip()))
    return rows


# Pinned exact strings. Guards: odd data reads/writes use the program bus check; unreachable
# boundaries are rejected by the router before any execution of the target.
GUARD_ERRORS = {
    'guard-odd-ee-A2': EVEN,
    'guard-odd-descriptor-A3-a42c': EVEN,
    'guard-odd-A7-a43e': EVEN,
    'guard-odd-A7-2ac0': EVEN,
    'guard-hook-target-without-stop': UNSUPPORTED_MACHINE,
    'guard-bd26-without-stop': UNSUPPORTED_MACHINE,
    'guard-a662-without-stop': UNSUPPORTED_MACHINE}


class Errors(dict):
    """Exact pinned error strings; interior entries follow the router ranges of animation_machine.cpp."""
    def __missing__(self, label):
        if label.startswith('interior_direct_entry_'):
            pc = int(label.rsplit('_', 1)[1], 16)
            return UNSUPPORTED_INPUT if in_ranges(pc, ROUTER_RANGES, inclusive=True) else UNSUPPORTED_MACHINE
        for prefix in ('boundary_direct_entry_', 'a662_reached_', 'bd26_reached_', 'hook_fff00_reached_'):
            if label.startswith(prefix):
                return UNSUPPORTED_MACHINE
        raise KeyError(label)


NEG_ERRORS = Errors({'odd_hook_target_fff01': ODD_JUMP})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_card_menu_input.py', 'tools/verify_animation_machine_card_child.py',
                 'tools/observe_animation_machine_card_menu_input.py', 'tools/observe_animation_machine_card_child.py',
                 'docs/analysis/animation-machine-card-menu-input-contract.md',
                 'engine/src/animation_machine_card_menu_input.cpp', 'engine/src/animation_machine_card_menu_open.cpp',
                 'engine/src/animation_machine_card_menu.cpp', 'engine/src/animation_machine_card_child.cpp',
                 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h',
                 'engine/tests/animation_machine_card_menu_input_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    # Reviewed fade/card chain re-run in actual C++ gives the c00468 stop output; the push/open/input
    # chain then continues from it inside the native chain row (re-run end to end in C++).
    cc.OUT = OUT / 'card_child_chain'
    cc.OUT.mkdir(parents=True, exist_ok=True)
    bios_start = cc.fade_chain_bios_output(exe, program, source, resources)
    report, rows, native_refs, input_instructions, static = audit_native(program, source)
    instructions = merged_instructions(program, input_instructions)
    refs.update(native_refs)
    out_rows, totals, shared, guards, single_block, chain_w7e, covered = compare(
        exe, program, report, rows, resources, instructions, bios_start)
    ends, starts = shared.ends, shared.starts
    chain_label = rows[0]['label']
    assert covered == set(report['artifacts']) - {'source.json'}, len(covered)
    manifest = hashlib.sha256()
    for name in sorted(covered):
        manifest.update(('%s %s\n' % (name, report['artifacts'][name])).encode())
    # Prefix of the chain equals the reviewed child/push/open native evidence (hash-identical RAM, registers).
    reference_rows = {}
    for name, (_p, _s, condition, step) in REFERENCES.items():
        value, outgoing = reference_step(name)
        ram, state, pvc, bank = ends[(chain_label, step)]
        assert ram == value and {k: state[k] for k in common.REGS + ('pc',)} == outgoing, name
        reference_rows[name] = dict(condition=condition, step=step, ram_sha256=sha(ram), equal=True)
    open_path, _op, open_condition, _os = REFERENCES['open']
    open_report = json.loads((ROOT / open_path).read_text())
    open_row = next(r for r in open_report['results'] if r['label'] == open_condition)
    open_steps = 0
    for step in range(OPEN_CHAIN_LAST_STEP + 1):
        last = [p for p in open_row['phases'] if p['step'] == step][-1]
        ram_name = next(n for n in last['artifacts'] if n.endswith('_ram_after.bin'))
        value = ((ROOT / open_path).parent / ram_name).read_bytes()
        assert sha(value) == last['artifacts'][ram_name]
        ram, state, pvc, bank = ends[(chain_label, step)]
        assert ram == value and {k: state[k] for k in common.REGS + ('pc',)} == last['outgoing'], step
        open_steps += 1
    # 300-frame countdown chain.
    countdown = report['countdown']
    assert chain_w7e == countdown['w7e_after_each_frame'] and len(chain_w7e) == countdown['frames'] == 301
    final = ends[(chain_label, max(s for lbl, s in ends if lbl == chain_label))]
    assert final[1]['pc'] == A662
    base = ends[(chain_label, OPEN_CHAIN_LAST_STEP)]
    assert base[1]['pc'] == 0x2ac2
    native_guards = {g['label']: g['guard'] for g in report['guard_reports']}
    guarded = compare_guards(exe, guards, resources, GUARD_ERRORS, native_guards)
    negative, controls, interior_count = negatives(exe, base, starts, instructions, resources, NEG_ERRORS)
    negative.append(odd_jump_negative(exe, starts, rows, resources, NEG_ERRORS, covered))
    zero = zero_step(exe, base, resources)
    boundary_zero = boundary_zero_step(exe, base, resources, {pc: True for pc in BOUNDARY_PCS + (HFFF00, )})
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
    result = dict(schema_version=1, source=source, inputs=inputs, artifacts=dict(refs, **local),
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA,
                  contract_sha256=CONTRACT_SHA,
                  native_artifacts_hash_checked=dict(count=len(covered), manifest_sha256=manifest.hexdigest()),
                  prefix_equal_to_reference_observations=reference_rows,
                  open_chain_steps_equal_to_open_native=open_steps,
                  actual_CPP=dict(totals, rows=out_rows),
                  countdown=dict(frames=len(chain_w7e), first=chain_w7e[0], last=chain_w7e[-1],
                                 equals_native_w7e_after_each_frame=True),
                  native_guards_checked_API=guarded,
                  negatives=negative, positive_controls=controls, negative_count=len(negative) + len(guarded),
                  interior_PCs_rejected=interior_count, zero_step=zero, boundary_zero_step=boundary_zero,
                  carry=dict(
                      contract_preserving_blocks=[hex(pc) for pc in CARRY_PRESERVING],
                      static_source_walk_preserving=sorted(hex(pc) for pc in preserving),
                      observed_single_block_starts=sorted(hex(pc) for pc in single_block),
                      observed_preserving_starts=sorted(hex(pc) for pc in single_block if pc in CARRY_PRESERVING),
                      not_observed_single_block=sorted(hex(pc) for pc in INPUT_BLOCK_STARTS if pc not in single_block)),
                  bios_start=dict(chain_label=bios_start[0][0], step=bios_start[0][1],
                                  ram_sha256=sha(bios_start[1][0])),
                  carry_check='C++ carry equals source-opcode walk over native-executed PCs (ORI/ANDI CCR known, flow-only preserved, else Unknown); native SR never read',
                  normalized_reference_paths=len(unique), compile_command=command, failure=None,
                  ROM_unchanged=True,
                  limits=['Controlled fixtures; frame re-entry (PC=2ab8) and the 104cba/104cc0/10fdb6/10fdb7 bytes are declared host changes, not a natural scheduler, input routine or BIOS.',
                          'Carry is a source-opcode classification (native SR is never read), not a native C measurement; ADDA/SUBA are conservatively Unknown.',
                          'a662 (close), bd26 (BIOS card save) and non-bf2c hook targets (9000, c2c0, fff00 fixtures) are stop boundaries only; a662 and later are out of scope.',
                          'Native observation artifacts are hash checked (359544 files) and streamed, not re-executed here.',
                          'Checked failures preserve API outputs, not original CPU fault rollback; interior direct entries and the odd hook target have no native guard (API-only rejection).'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'],
                         resumes=totals['resumes'], negatives=result['negative_count'], interior=interior_count,
                         zero_step=len(zero), carry=totals['carry_histogram'],
                         sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
