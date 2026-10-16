"""480bc frame helper bundle U7 (buffer 4aa88 / 4b784, cue e8a48 / e8ad0 / e8af4 and the cue wrapper 2986 / 298e) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation (artifacts/animation_machine_buffer_cue_native) is an immutable input: this
verifier never invokes the observer main and never imports the observer module. Every native split phase (22607) and every continuous control phase (1943) is
replayed against the actual C++ `run_animation_machine`:
  * per split phase the full 64 KiB RAM / 16 registers / PC / A7 / PVC / bank / ordered ports / external reads / status of the actual C++ output; each phase resumes ONLY
    from the previous actual C++ output plus the declared host changes of the native step (RAM writes, the frame re-entry PC redirect, the A7 delta);
  * continuous C++ run of each step vs the split C++ chain and vs the native continuous control;
  * carry = source-opcode classification (ORI #1,CCR / ANDI #fe,CCR / MOVE (A7)+,SR at 2998 from the popped WORD / flow-only blocks) cross-checked at the 298e consumer
    against the REAL native image WORD; incoming C probes (1 / 2) per distinct first block of a row; unknown-carry consumer rejection;
  * native guards -> exact checked C++ error strings + full preservation; deliberate differences are classified by explicit rules and counted;
  * API-only negatives: interior / bundled / operand-word direct entries, outside entries, odd PCs, zero-step at every block start x 3 carries.
Native SR is never read: the only CCR dependent value, the WORD pushed at 2990, is a native ordered RAM write that the C++ RAM image must reproduce.
"""
import collections
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import traceback
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
from disassemble_program import load_verified_program, disassemble_range

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_buffer_cue_verify'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_buffer_cue_native'
NATIVE_SHA = '06327d8cc34c58f43e8c74504816881dec250d095dbef597398e11a05705c630'
NATIVE_TOOL_SHA = '64d363d7ca6a0201bb5b73544fd60f267f4cf419ddf3e7d46d6df41743e57ff1'
CONTRACT = ROOT / 'docs/analysis/animation-machine-buffer-cue-u7-contract.md'
CONTRACT_SHA = '75e76e8cfb9ed6c9e18d70b9b5a153f0b54104c0d98f118756c7c67f6955ae09'
CPP_SHA_PREFIX = '5360f1fc'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
S = 0x1feffc
RET_FRAME = 0x2ac2
WRAPPER = 0x298e
U7_RANGES = ((0x4aa88, 0x4abc0), (0x4b784, 0x4b82e), (0xe8a48, 0xe8b5a), (0x2986, 0x299c))
CONSUMER = 0x298e
CALLER_RET = 0xe8a8a
UNSUPPORTED_UNIT = 'unsupported animation buffer cue PC'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNALIGNED_PC = 'unaligned animation machine PC'
UNKNOWN_CARRY = 'cue wrapper requires known carry'
UNKNOWN_CALLER_X = 'cue wrapper failure requires known caller X'
ALIAS_X = 'cue wrapper caller X source overlaps the stack'
WORD_OVERWRITTEN = 'cue wrapper status WORD overwritten'
A5_REQUIRED = 'cue requires A5 108000'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
WRITE_DEVICE = 'unsupported animation machine write device'
RAM_MIRROR = 'program bus write requires RAM mirror units'
BUDGET = 'animation machine block budget exceeded'
DEVICE_ADDRESS = 'unsupported program bus device address'
SPRITE_CALLBACK = 'unsupported sprite callback target'
VERIFIED_ARTIFACTS = set()
RUN_DIR = None
WORKERS = 8
EXTERNAL_QUEUE_EMPTY = 'animation machine external read queue empty'
# e5bfb73 (0264-legacy): e8a1c (F1a stage_entry range e8a1c..e8a3a) and 4b82e (N03 4b82e..4b8a2) now run on into blocks routed by the ten-unit batch and end with a
# BYTE read of a non-physical address, which takes the F5 external-read queue path (empty in this harness): the checked error is 'external read queue empty'. Former
# expectation UNSUPPORTED_MACHINE; the superseding unit of the continuation is not traced [U]. This is not evidence of device behaviour.
SUPERSEDED_OUTSIDE = {0x4b830: 'unsupported animation objects n03 PC', 0xe8a1c: EXTERNAL_QUEUE_EMPTY, 0x4b82e: EXTERNAL_QUEUE_EMPTY}
DEBUG_ROWS = int(os.environ.get('BUFCUE_DEBUG_ROWS', '0'))     # development switch only: the reported run is always the full set


def localize(name):
    main = '/Users/start/Workspce/metalslug'
    local = str(ROOT) + name[len(main):] if name.startswith(main + '/') else name
    return local if Path(local).exists() else name           # tools not copied into this worktree are read from the main tree (read only)


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def invoke(exe, folder, label, ram, state, pvc, bank, resources, stop, external=0):
    """common.invoke with close_fds=False (posix_spawn) and no state.json side file."""
    paths = [folder / (label + s) for s in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin')]
    paths[0].write_bytes(ram)
    paths[1].write_bytes(pvc)
    args = [str(exe)] + [str(state[k]) for k in common.REGS] + [str(state['pc']), str(state['carry']), str(bank), str(stop), str(external)] + \
        list(map(str, paths)) + list(map(str, resources))
    run = subprocess.run(args, capture_output=True, text=True, timeout=300, close_fds=False)
    assert run.returncode == 0, (label, run.stderr)
    result = common.parse(run.stdout, expected_invalid_carry=state['carry'] if state['carry'] not in (0, 1, 2) else None)
    assert paths[0].read_bytes() == ram and paths[1].read_bytes() == pvc
    return result, paths[2].read_bytes(), paths[3].read_bytes(), paths[4].read_bytes(), run.stderr


def inv(label, *args, **kwargs):
    result = invoke(*((args[0], RUN_DIR, label) + args[1:]), **kwargs)
    for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin'):
        (RUN_DIR / (label + suffix)).unlink()
    return result


class RomInstructions(dict):
    """Instruction decoded from the original bytes on demand."""
    def __init__(self, program):
        dict.__init__(self)
        self.program = program

    def __missing__(self, pc):
        item = disassemble_range(self.program, pc, 10, pc)[0]
        assert item['classification'] == 'candidate_instruction' and item['cpu_address'] == pc, hex(pc)
        self[pc] = item
        return item


# ----------------------------------------------------------------------------------------------------------------- contract
def contract_lists():
    """Block starts (60 = 17 + 13 + 28 + 2), bundled branch PCs (24), carry-preserving block starts (15) of the contract text."""
    lines = CONTRACT.read_text().splitlines()
    pcs = lambda text: [int(x, 16) for x in re.findall(r'`([0-9a-f]{4,5})`', text)]
    starts, bundled, preserve = [], [], []
    for i, line in enumerate(lines):
        if line.startswith('- **Block 시작 PC (60개)**'):
            j = i + 1
            while lines[j].startswith('  - '):
                starts += pcs(lines[j].split(':', 1)[1])
                j += 1
        if line.startswith('- **묶인 분기 PC (24개'):
            bundled = pcs(lines[i + 1])
        if line.startswith('- **Carry 보존(FLOW_ONLY) block (15개)**'):
            preserve = pcs(lines[i + 1])
    assert len(starts) == len(set(starts)) == 60 and len(bundled) == len(set(bundled)) == 24 and len(preserve) == len(set(preserve)) == 15
    return starts, bundled, preserve


def parse_table(program):
    rows, code = [], []
    pattern = re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| (\d+) \| `([0-9a-f]+)…([0-9a-f]+)` \| `([0-9a-f]+)` \|')
    for line in CONTRACT.read_text().splitlines():
        match = pattern.match(line)
        if not match:
            continue
        low, high = int(match.group(1), 16), int(match.group(2), 16)
        data = program[low:high]
        assert data.hex() == match.group(6) and high - low == int(match.group(3))
        digest = sha(data)
        assert digest.startswith(match.group(4)) and digest.endswith(match.group(5))
        rows.append(dict(range='%x..%x' % (low, high), size=high - low, bytes_equal_to_rom=True, sha256=digest))
        code.append((low, high))
    assert code == list(U7_RANGES) and sum(h - l for l, h in code) == 778
    assert sha(b''.join(program[l:h] for l, h in code)) == 'aa13f52b624d8da72825a6afb522510763c1bacaf6c75cb448cc523e8653c574'
    return rows


def static_blocks(instructions, starts):
    blocks = {}
    conditional = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
    for start in starts:
        pcs, pc = [], start
        while True:
            item = instructions[pc]
            pcs.append(pc)
            name = item['mnemonic'].split('.')[0]
            end = name in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'dbra') or name in conditional
            following = pc + item['size']
            if end or following in starts:
                break
            pc = following
        blocks[start] = pcs
    return blocks


def audit_static(program):
    table = parse_table(program)
    starts, bundled, preserve = contract_lists()
    instructions = RomInstructions(program)
    inside = []
    for low, high in U7_RANGES:
        pc = low
        while pc < high:
            inside.append(pc)
            pc += instructions[pc]['size']
        assert pc == high
    assert len(inside) == 219
    start_set = set(starts)
    conditional = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
    # leaders derived from the original opcodes (range starts, branch / call targets, instructions after conditional branches, calls, rts, bra)
    derived = set(low for low, _ in U7_RANGES)
    for pc in inside:
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        target = re.search(r'\$([0-9a-f]+)$', item['op_str'])
        if name in conditional + ('bra', 'bsr', 'jsr') and target:
            derived.add(int(target.group(1), 16))
        if name in conditional + ('bsr', 'jsr', 'rts', 'bra', 'jmp'):
            derived.add(pc + item['size'])
    derived = set(pc for pc in derived if in_ranges(pc, U7_RANGES))
    assert derived == start_set, (sorted(hex(p) for p in derived ^ start_set))
    blocks = static_blocks(instructions, start_set)
    in_block = collections.Counter(pc for pcs in blocks.values() for pc in pcs)
    assert max(in_block.values()) == 1
    bundled_expected = sorted(pc for pc in inside if pc not in start_set and instructions[pc]['mnemonic'].split('.')[0] in conditional)
    assert bundled_expected == sorted(bundled), [hex(p) for p in set(bundled_expected) ^ set(bundled)]
    flow_only = sorted(pc for pc in starts if all(instructions[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc]))
    assert flow_only == sorted(preserve), [hex(p) for p in set(flow_only) ^ set(preserve)]
    producers = sorted(pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in ('ori', 'andi', 'eori', 'move') and re.search(r'\b(ccr|sr)\b', instructions[pc]['op_str']))
    assert producers == [0x2990, 0x2998], [hex(p) for p in producers]
    x_users = [pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in ('addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')]
    assert x_users == []
    return dict(table=table, starts=starts, bundled=bundled, preserving=preserve, instructions=instructions, blocks=blocks, inside=inside)


def cpp_static(st):
    """C++ case labels of the unit vs the 60 contract block starts, routing ranges and the carry-preserving table."""
    text = (ROOT / 'engine/src/animation_machine_buffer_cue.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text))
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    in_unit = set(pc for pc in table if in_ranges(pc, U7_RANGES))
    routing = re.search(r'\(next\.pc>=0x4aa88 && next\.pc<0x4abc0\) \|\| \(next\.pc>=0x4b784 && next\.pc<0x4b82e\) \|\|\s*'
                        r'\(next\.pc>=0xe8a48 && next\.pc<0xe8b5a\) \|\| \(next\.pc>=0x2986 && next\.pc<0x299c\)\)ok=animation_buffer_cue_block', machine)
    assert routing, 'routing ranges not found'
    return cases, in_unit, True


# ----------------------------------------------------------------------------------------------------------------- native rows
def read_checked(name, expected):
    value = (NATIVE_DIR / name).read_bytes()
    assert sha(value) == expected, name
    VERIFIED_ARTIFACTS.add(name)
    return value


def load_phase(phase):
    data = {}
    for name, expected in phase['artifacts'].items():
        data[re.search(r'_phase_\d+_(.*)$', name).group(1)] = read_checked(name, expected)
    phase['_data'] = data
    phase['_trace'] = json.loads(data['trace.json'])
    for snapshot in phase['snapshots']:
        snapshot['_ram'] = read_checked(snapshot['artifacts']['ram'], phase['artifacts'][snapshot['artifacts']['ram']])
        snapshot['_pvc'] = read_checked(snapshot['artifacts']['pvc'], phase['artifacts'][snapshot['artifacts']['pvc']])


def trace_text(pcs, events, guard):
    """The exact trace.json text the observer wrote (json.dumps(indent=2) + newline), to re-derive the recorded SHA of a sliced split-phase trace."""
    return (json.dumps({'pcs': pcs, 'events': events, 'guard': guard}, indent=2) + '\n').encode()


def ports_blob(events):
    return b''.join(struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in events if e['region'] in ('pvc', 'video', 'watchdog'))


def load_row(row):
    """The continuous control payloads and checkpoint snapshots exist for every row (hash checked). The split-phase payloads exist only for the 31 stage-frame rows;
    for all other rows the split phases are rebuilt from the control payload of their step (checkpoint snapshots = full RAM / PVC after every non-final phase, PC and
    event slices from the recorded pc_count / event counts) and every rebuilt payload (RAM before / after, PVC before / after, ports, the exact trace.json text) is
    checked against the SHA256 recorded for that split phase. Where the split files exist they are additionally compared with the rebuilt payloads."""
    for phase in row['continuous_control']:
        load_phase(phase)
    real = 0
    for phase in row['phases']:
        step = [c for c in row['continuous_control'] if c['step'] == phase['step']]
        assert len(step) == 1
        phase['_control'] = step[0]
        if all((NATIVE_DIR / n).exists() for n in phase['artifacts']):
            load_phase(phase)
            phase['_real'] = dict(data=phase.pop('_data'), trace=phase.pop('_trace'))
            real += 1
    row['_real_split'] = real
    for step in sorted({p['step'] for p in row['phases']}):
        parts = [p for p in row['phases'] if p['step'] == step]
        ctrl = parts[0]['_control']
        pcs, events = ctrl['_trace']['pcs'], ctrl['_trace']['events']
        snaps = {sn['registers']['pc']: sn for sn in ctrl['snapshots']}
        ci = ei = 0
        ram, pvc = ctrl['_data']['ram_before.bin'], ctrl['_data']['pvc_before.bin']
        for k, p in enumerate(parts):
            final = k == len(parts) - 1
            n, ne = p['pc_count'], sum(p['counts'].values())
            ppcs, pev = pcs[ci:ci + n], events[ei:ei + ne]
            assert len(ppcs) == n and len(pev) == ne
            assert ppcs[0] == p['incoming']['pc'] and ppcs[-1] == p['outgoing']['pc'], (row['label'], step, k)
            ci += n - 1
            ei += ne
            if final:
                assert ci == len(pcs) - 1 and ei == len(events), (row['label'], step, ci, len(pcs), ei, len(events))
                after_ram, after_pvc = ctrl['_data']['ram_after.bin'], ctrl['_data']['pvc_after.bin']
                assert p['outgoing'] == ctrl['outgoing'] and p['guard'] == ctrl['guard'] and p['waiting'] == ctrl['waiting']
            else:
                sn = snaps[p['outgoing']['pc']]
                assert sn['registers'] == p['outgoing']
                after_ram, after_pvc = sn['_ram'], sn['_pvc']
            guard = p['guard']
            data = {'ram_before.bin': ram, 'ram_after.bin': after_ram, 'pvc_before.bin': pvc, 'pvc_after.bin': after_pvc, 'ports.bin': ports_blob(pev)}
            text = trace_text(ppcs, pev, guard)
            for name, value in list(data.items()) + [('trace.json', text)]:
                recorded = [h for n_, h in p['artifacts'].items() if n_.endswith('_' + name)]
                assert len(recorded) == 1 and sha(value) == recorded[0], (row['label'], step, k, name)
            p['_data'] = data
            p['_trace'] = {'pcs': ppcs, 'events': pev, 'guard': guard}
            if '_real' in p:
                assert p['_real']['data'] == dict(data, **{'trace.json': text}) or all(p['_real']['data'][x] == data[x] for x in data)
                assert p['_real']['data']['trace.json'] == text and p['_real']['trace'] == p['_trace']
                for sn in p['snapshots']:
                    assert sn['_ram'] == snaps[sn['registers']['pc']]['_ram']
            ram, pvc = after_ram, after_pvc


def unload_row(row):
    for kind in ('phases', 'continuous_control'):
        for phase in row[kind]:
            for key in ('_data', '_trace', '_real', '_control'):
                phase.pop(key, None)
            for snapshot in phase['snapshots']:
                snapshot.pop('_ram', None)
                snapshot.pop('_pvc', None)


def audit_row(row, program):
    assert row['reproduced_twice'] and row['continuous_split_equivalent']
    assert bool(row['guarded']) == row['label'].startswith('guard-')
    fx = row['fixture']
    counts_split = None
    for kind in ('phases', 'continuous_control'):
        counts = cc.audit_program_reads(program, fx, row[kind])
        if kind == 'phases':
            counts_split = counts
    for step in sorted({p['step'] for p in row['phases']}):
        parts = [p for p in row['phases'] if p['step'] == step]
        whole = parts[0]['_control']
        assert parts[0]['host_changes'] == whole['host_changes'] and all(not p['host_changes'] for p in parts[1:])
        assert parts[0]['incoming'] == whole['incoming']
        pcs, events = [], []
        for p in parts:
            pcs.extend(p['_trace']['pcs'][:-1])
            events.extend(p['_trace']['events'])
        pcs.extend(parts[-1]['_trace']['pcs'][-1:])
        assert pcs == whole['_trace']['pcs'] and events == whole['_trace']['events']
        for key in ('outgoing', 'modeled_bank', 'guard'):
            assert parts[-1][key] == whole[key], (row['label'], step, key)
    for phase in row['phases'] + row['continuous_control']:
        assert phase['carry'] is None and not phase['branch_evidence'] and phase['carry_in'] is None
        assert phase['counts']['external_reads'] == sum(e['region'] == 'external' for e in phase['_trace']['events'])
        assert phase['_data']['ports.bin'] == ports_blob(phase['_trace']['events'])
        assert phase['waiting'] == (phase['wait'] is not None)
        assert phase['waiting'] == (phase['outgoing']['pc'] in (0xcda4, 0x3aea) and phase['guard'] is None and phase['stop_pc'] != phase['outgoing']['pc'])
    return counts_split


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_buffer_cue.py') == NATIVE_TOOL_SHA
    assert cc.digest(CONTRACT) == CONTRACT_SHA
    assert cc.digest(ROOT / 'engine/src/animation_machine_buffer_cue.cpp').startswith(CPP_SHA_PREFIX)
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['declared_register_changes_at_step_boundaries'] == [] and report['contract_discrepancies'] == []
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert (report['cases'], report['guarded_cases'], report['split_steps'], report['control_steps']) == (1779, 22, 22439, 1921)
    assert (report['guard_split_steps'], report['guard_control_steps'], report['total_split_phases'], report['total_control_phases']) == (168, 22, 22607, 1943)
    assert report['block_starts_covered'] == 60 and report['block_starts_uncovered'] == []
    assert report['boundary_stop_pcs'] == [295122, 295146, RET_FRAME]
    for name, expected in report['inputs'].items():
        assert cc.digest(localize(name)) == expected, name
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    return report


# ----------------------------------------------------------------------------------------------------------------- carry / images
def popped_bit(events):
    """C from the popped WORD of MOVE (A7)+,SR at 2998 (the native ordered RAM read); None when the phase did not execute it."""
    reads = [e for e in events if e['pc'] == 0x2998 and e['access'] == 'read' and e['size'] == 2]
    if not reads:
        return None
    assert len(reads) == 1
    return int(reads[0]['bytes'], 16) & 1


def classify_carry(instructions, carry, pcs, events):
    """Source-opcode classification of C (no native SR): ORI #1,CCR Set, ANDI #fe,CCR Clear, MOVE (A7)+,SR at 2998 = bit0 of the native popped WORD,
    flow-only opcodes preserve, anything else makes C Unknown."""
    for pc in pcs:
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        if name == 'ori' and item['op_str'] == '#$1, ccr':
            carry = 2
        elif name == 'andi' and item['op_str'] == '#$fe, ccr':
            carry = 1
        elif pc == 0x2998:
            carry = 2 if popped_bit(events) else 1
        elif name in FLOW_ONLY:
            pass
        else:
            carry = 0
    return carry


def patched(ram, overrides, skip=()):
    if not overrides:
        return ram
    out = bytearray(ram)
    for offset, value in overrides.items():
        if offset not in skip:
            out[offset] = value
    return bytes(out)


def written_offsets(events):
    """RAM mirror offsets written by the ordered native events of a phase."""
    out = set()
    for e in events:
        if e['access'] == 'write' and e['region'] == 'ram':
            out.update((e['address'] + i) & 0xffff for i in range(e['size']))
    return out


def check_result(actual, phase, pvc, bank, portbytes, events, overrides=None, fresh=()):
    result, ram, device, ports, error = actual
    assert result['ok'] and not error, error
    outgoing = phase['outgoing']
    assert {k: result[k] for k in common.REGS + ('pc',)} == outgoing, {
        k: (outgoing[k], result[k]) for k in common.REGS + ('pc',) if result[k] != outgoing[k]}
    assert result['status'] == (1 if phase['waiting'] else 0), (result['status'], phase['waiting'])
    if result['status'] == 1:
        assert result['carry'] == 0
    reads = sum(e['access'] == 'read' and e['address'] == 0xd00046 and e['size'] == 1 for e in events)
    assert result['external_reads'] == reads and result['bank_base'] == bank, (reads, result['external_reads'], bank, result['bank_base'])
    expected_ram = patched(phase['_data']['ram_after.bin'], overrides, written_offsets(events) - set(fresh))
    assert ram == expected_ram, [(i, expected_ram[i], ram[i]) for i in range(len(ram)) if ram[i] != expected_ram[i]][:20]
    assert device == pvc, 'PVC mismatch'
    assert ports == portbytes, ('ports', ports.hex(), portbytes.hex())


def check_preserved(actual, ram, state, pvc, bank, expected_error=None):
    result, out_ram, out_pvc, ports, error = actual
    assert not result['ok'] and (expected_error is None or error.strip() == expected_error), (expected_error, error.strip())
    assert {k: result[k] for k in common.STATE_KEYS} == {k: state[k] for k in common.STATE_KEYS}
    assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
    assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
    return error.strip()


def word(ram, address):
    at = address & 0xffff
    return int.from_bytes(ram[at:at + 2], 'big')


def long(ram, address):
    at = address & 0xffff
    return int.from_bytes(ram[at:at + 4], 'big')


def image_model(ram, regs, carry_set):
    """Independent contract model (docs table) of the WORD pushed at 2990 for a phase that starts at 298e with A7 pointing at the saved A6 LONG.
    Success: X = (D0.W == 0), N/Z of BYTE 6a(A0), V = 0, C = 1. Failure: C = 0, CMP.W D0-M flags (M = WORD 104ca0) or (28c2) Z only, X of the e8a48 caller
    (flags BYTE 4(cue): bit0 -> carry of WORD 2(cue)+WORD 10d3c0, bit1 -> carry of WORD (cue)+WORD 10d3bc, else 0). Returns (word, caller_x_known)."""
    d0 = regs['d0'] & 0xffff
    if carry_set:
        value = ram[(regs['a0'] + 0x6a) & 0xffff]
        ccr = 1 | (8 if value & 0x80 else 0) | (4 if value == 0 else 0) | (0x10 if d0 == 0 else 0)
        return 0x2000 | ccr, True
    m = word(ram, 0x104ca0)
    if d0 >= m:
        result = (d0 - m) & 0xffff
        ccr = (8 if result & 0x8000 else 0) | (4 if result == 0 else 0) | (2 if ((d0 ^ m) & (d0 ^ result)) & 0x8000 else 0)
    else:
        ccr = 4
    ret = long(ram, regs['a7'] + 4)
    if ret != CALLER_RET:
        return 0x2000 | ccr, False
    cue = long(ram, 0x10de26)
    flags = ram[(cue + 4) & 0xffff]
    x = 0
    if flags & 1:
        x = (word(ram, cue + 2) + word(ram, 0x10d3c0)) >> 16
    elif flags & 2:
        x = (word(ram, cue) + word(ram, 0x10d3bc)) >> 16
    return 0x2000 | ccr | (0x10 if x else 0), True


# ----------------------------------------------------------------------------------------------------------------- deliberate differences
def deliberate_error(label, error):
    """Classify a C++ checked error that occurs before the native outcome (a native success, or a native guard that fires later). Returns (category, rule) or None."""
    if label.startswith('guard-'):
        if label.startswith('guard-cue-overlap-6aA0-over-SR-word') and error == WORD_OVERWRITTEN:
            return ('overlap_6aA0_over_SR_word', 'decision 1: the popped WORD differs from the pushed one -> checked error at 298e (native: RTS to 00000002 later)')
        if label == 'guard-cue-a5-zero' and error == A5_REQUIRED:
            return ('a5_not_108000_at_e8a48', 'decision 1: A5 = 108000 is required at e8a48 (native: write fault at e8a50)')
        return None
    if error == UNKNOWN_CALLER_X:
        return ('wrapper_failure_requires_known_caller_X', 'decision 1 option A: failure-path X is computed only for the e8a8a caller; other return LONGs are checked errors')
    if error == ALIAS_X:
        return ('widened_alias_guard', 'decision 1: the caller-X re-read range overlapping [S-8,S+8) (mirror aliasing included) is a checked error')
    if error == WORD_OVERWRITTEN:
        return ('status_word_overwritten', 'decision 1: popped WORD differs from the pushed one (2992 write overlapping the stack WORD)')
    if error == A5_REQUIRED:
        return ('a5_not_108000_at_e8a48', 'decision 1: A5 = 108000 is required at e8a48')
    return None


GUARD_EXPECTED = {
    'guard-buf-callback-cd52': SPRITE_CALLBACK, 'guard-buf-callback-ram': SPRITE_CALLBACK,
    'guard-buf-odd-a7-no-debug': EVEN, 'guard-buf-odd-a7-debug-push': EVEN, 'guard-buf-odd-object': EVEN, 'guard-buf-odd-record': EVEN,
    'guard-buf-odd-cursor': EVEN, 'guard-buf-rom-cursor': WRITE_DEVICE, 'guard-buf-a5-zero': EVEN,
    'guard-cue-walk-alloc0-phase-ffff-no-terminator': DEVICE_ADDRESS, 'guard-cue-walk-alloc1-phase-ffff-no-terminator': DEVICE_ADDRESS,
    'guard-cue-walk-rom-default-phase-ffff-no-terminator': DEVICE_ADDRESS, 'guard-cue-walk-unterminated-reaches-PVC': DEVICE_ADDRESS,
    'guard-cue-overlap-6aA0-over-SR-word-high-byte-20': WORD_OVERWRITTEN, 'guard-cue-overlap-6aA0-over-SR-word-high-byte-27': WORD_OVERWRITTEN,
    'guard-direct-e8ad0-phase-ffff-no-terminator': DEVICE_ADDRESS, 'guard-cue-odd-a7-push': EVEN, 'guard-cue-odd-cue': EVEN, 'guard-cue-odd-stream': EVEN,
    'guard-cue-a5-zero': A5_REQUIRED, 'guard-cue-bad-stop-outside-ranges': UNSUPPORTED_MACHINE, 'guard-buf-bad-stop-outside-ranges': UNSUPPORTED_MACHINE}


# ----------------------------------------------------------------------------------------------------------------- row replay
def apply_changes(ram, state, changes):
    ram = bytearray(ram)
    state = dict(state)
    kinds = []
    for change in changes:
        kind = change['kind']
        if kind == 'ram':
            at, size = change['address'] & 0xffff, change['size']
            assert 0 <= at <= 0x10000 - size
            common.native.put(ram, change['address'], size, change['value'])
        elif kind == 'pc':
            state['pc'] = change['to']
        elif kind == 'a7_add':
            state['a7'] = (state['a7'] + change['delta']) & M32
        else:
            raise AssertionError(kind)
        kinds.append(kind)
    return bytes(ram), state, kinds


def initial_carry(row, entry_pc):
    """Declared initial C: only the 298e direct entries consume C; their declared SR gives it (SR 2000 / 2010 -> Clear, 2001 -> Set). Others Unknown."""
    if entry_pc != WRAPPER:
        return 0
    sr = row['provenance'].get('declared_sr') or row['fixture'].get('sr')
    sr = 0x2000 if sr is None else (int(sr, 16) if isinstance(sr, str) else sr)
    return 2 if sr & 1 else 1


def run_row(row, ctx):
    exe, resources, st, program, instructions = ctx
    start_set = set(st['starts'])
    acc = dict(totals=collections.Counter(), program_reads=collections.Counter(), carry_hist=collections.Counter(), first_pcs=collections.Counter(),
               preserved={}, guards=[], deliberate=[], images=[], declared_ccr=[], carry_classes=collections.Counter())
    totals = acc['totals']
    load_row(row)
    counts = audit_row(row, program)
    acc['program_reads'].update(counts)
    fx = row['fixture']
    label = row['label']
    phases = row['phases']
    first = phases[0]
    pvc = first['_data']['pvc_before.bin']
    totals['rows_with_real_split_payload_files_compared_with_rebuilt'] += bool(row['_real_split'])
    bank = first['bank_before']
    ram = first['_data']['ram_before.bin']
    state = dict(first['incoming'], carry=initial_carry(row, first['incoming']['pc']))
    expected_pvc, expected_bank = pvc, bank
    digest = hashlib.sha256()
    step_starts, step_ends = {}, {}
    carry_row = collections.Counter()
    seen_first = set()
    stops = 0
    error_row = None
    overrides = {}
    overrides_end = {}
    for j, phase in enumerate(phases):
        data = phase['_data']
        step = phase['step']
        if phase['phase_in_step'] == 0:
            if step == 0:
                assert not any(c['kind'] != 'ram' for c in phase['host_changes'])
            ram, state, kinds = apply_changes(ram, state, phase['host_changes'])
            totals['declared_host_ram_changes'] += kinds.count('ram')
            totals['declared_frame_reentry_pc_changes'] += kinds.count('pc')
            totals['declared_frame_reentry_a7_deltas'] += kinds.count('a7_add')
            step_starts[step] = (ram, dict(state), pvc, bank)
        else:
            assert not phase['host_changes']
        assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (label, j)
        assert ram == patched(data['ram_before.bin'], overrides), (label, j)
        assert bank == phase['bank_before']
        events = phase['_trace']['events']
        executed = phase['_trace']['pcs'][:-1]
        if phase['guard'] is not None:
            assert j == len(phases) - 1 and row['guarded']
            acc['guards'].append((row, phase, ram, dict(state), pvc, bank))
            break
        expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
        actual = inv('c%04d_split_%03d' % (row['index'], j), exe, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        if not actual[0]['ok']:
            error = check_preserved(actual, ram, state, pvc, bank)
            category = deliberate_error(label, error)
            assert category is not None, ('UNEXPECTED C++ ERROR', label, j, hex(phase['stop_pc']), error)
            acc['deliberate'].append(dict(label=label, step=step, phase=j, stop=hex(phase['stop_pc']), category=category[0], rule=category[1], error=error,
                                          native_continued_to=hex(phase['outgoing']['pc']), all_API_outputs_preserved=True))
            error_row = (j, error)
            break
        first_pc = executed[0] if executed else None
        image = model = None
        if first_pc == WRAPPER:
            writes = [e for e in events if e['pc'] == 0x2990 and e['access'] == 'write']
            assert len(writes) == 1 and writes[0]['size'] == 2
            image = int(writes[0]['bytes'], 16)
            model, known = image_model(data['ram_before.bin'], phase_in, phase_in['carry'] == 2)
        fresh = set()
        try:
            check_result(actual, phase, expected_pvc, expected_bank, portbytes, events, overrides)
        except AssertionError:
            # a direct 2986 / 298e fixture whose declared SR gives X/N/Z/V that the original path would not produce: the C++ computes the CCR image from the
            # path (contract table); accepted only when the single differing RAM byte is the low byte of the pushed WORD, differs only in X/N/Z/V and equals the
            # independent contract model
            if not (first_pc == WRAPPER and row['group'] == 'custom-wrapper' and known):
                raise
            at = (writes[0]['address'] + 1) & 0xffff
            cpp_ram = actual[1]
            expected = patched(data['ram_after.bin'], overrides, written_offsets(events))
            diff = [i for i in range(len(cpp_ram)) if cpp_ram[i] != expected[i]]
            assert diff == [at], (label, j, diff[:8])
            native_byte, cpp_byte = expected[at], cpp_ram[at]
            assert cpp_byte == (model & 0xff) and (native_byte ^ cpp_byte) & ~0x1e & 0xff == 0, (label, j, hex(native_byte), hex(cpp_byte), hex(model))
            overrides[at] = cpp_byte
            fresh = {at}
            check_result(actual, phase, expected_pvc, expected_bank, portbytes, events, overrides, fresh)
            acc['declared_ccr'].append(dict(label=label, native_low_byte=hex(native_byte), cpp_low_byte=hex(cpp_byte), differing_bits=hex(native_byte ^ cpp_byte),
                                            contract_model_low_byte=hex(model & 0xff)))
        for offset in written_offsets(events) - fresh:
            overrides.pop(offset, None)
        result, ram, pvc, _, _ = actual
        want = classify_carry(instructions, state['carry'], executed, events)
        if phase['waiting']:
            want = 0
        assert result['carry'] == want, (label, j, hex(phase['outgoing']['pc']), result['carry'], want)
        acc['carry_hist'][result['carry']] += 1
        carry_row[CARRY_NAME[result['carry']]] += 1
        if first_pc in start_set:
            acc['first_pcs'][first_pc] += 1
        # 298e: the C consumer. The incoming C (from the previous ACTUAL C++ output) must equal the REAL native image bit0, the image WORD is
        # an ordered native RAM write that the C++ RAM image reproduces (already compared as part of the RAM image).
        if first_pc == WRAPPER:
            assert phase_in['carry'] in (1, 2), (label, j, phase_in['carry'])
            assert (image & 1) == (1 if phase_in['carry'] == 2 else 0), (label, j, hex(image), phase_in['carry'])
            popped = popped_bit(events)
            assert (image >> 8) == 0x20 or label.startswith('guard-'), hex(image)
            acc['images'].append((label, j, image, model, known, popped))
            totals['consumer_298e_phases'] += 1
            if known:
                if image == model:
                    totals['image_words_equal_independent_contract_model'] += 1
                else:
                    assert row['group'] == 'custom-wrapper', (label, j, hex(image), hex(model))
                    totals['image_words_declared_SR_fixture_differs_from_path_model'] += 1
        # incoming C probes: once per distinct first block of the row, phases that do not execute the 298e consumer (the probe would change the path)
        if not phase['waiting'] and first_pc not in seen_first and WRAPPER not in executed:
            seen_first.add(first_pc)
            for probe in (1, 2):
                again = inv('c%04d_carry%d_%03d' % (row['index'], probe, j), exe, data['ram_before.bin'], dict(phase_in, carry=probe), phase_pvc,
                            phase_bank, resources, stop=phase['stop_pc'], external=fx['external'])
                assert again[0]['ok'] and not again[4], (label, j, probe)
                assert again[0]['carry'] == classify_carry(instructions, probe, executed, events), (label, j, probe, again[0]['carry'])
                assert {k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in result.items() if k != 'carry'}
                assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                totals['carry_probes'] += 1
                totals['carry_probe_preserved'] += again[0]['carry'] == probe
                blocks = [pc for pc in executed if pc in start_set]
                if len(blocks) == 1 and blocks[0] == first_pc:
                    slot = acc['preserved'].setdefault(first_pc, {1: True, 2: True})
                    slot[probe] = slot[probe] and again[0]['carry'] == probe
        totals['carry_checks'] += 1
        totals['native_waiting_phases_C_status_1'] += bool(phase['waiting'])
        state = {k: result[k] for k in common.STATE_KEYS}
        bank = result['bank_base']
        totals['reads'] += result['external_reads']
        totals['ports'] += len(portbytes) // 9
        totals['resumes'] += 1 if phase['phase_in_step'] else 0
        digest.update(struct.pack('>IIB', phase['stop_pc'], state['pc'], result['carry']) + hashlib.sha256(ram).digest() + hashlib.sha256(pvc).digest() +
                      struct.pack('>I', len(portbytes)))
        stops += 1
        last_of_step = j + 1 == len(phases) or phases[j + 1]['step'] != step
        if last_of_step:
            step_ends[step] = (ram, dict(state), pvc, bank)
            overrides_end[step] = dict(overrides)
    control_rows = 0
    for phase in row['continuous_control']:
        step = phase['step']
        if phase['guard'] is not None or step not in step_starts:
            continue
        c_ram, c_state, c_pvc, c_bank = step_starts[step]
        data = phase['_data']
        assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
        e_pvc, e_bank, portbytes = cc.fold_outputs(c_pvc, c_bank, phase['_trace']['events'])
        assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        actual = inv('c%04d_control_%d' % (row['index'], step), exe, c_ram, c_state, c_pvc, c_bank, resources, stop=phase['stop_pc'], external=fx['external'])
        if error_row is not None and step == phases[error_row[0]]['step']:
            assert check_preserved(actual, c_ram, c_state, c_pvc, c_bank, error_row[1]) == error_row[1]
            totals['continuous_runs_agree_with_split_error'] += 1
            continue
        assert actual[0]['ok'] and not actual[4], (label, step, actual[4])
        check_result(actual, phase, e_pvc, e_bank, portbytes, phase['_trace']['events'], overrides_end.get(step), set(overrides_end.get(step, ())))
        assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == step_ends[step], (label, step)
        control_rows += 1
    totals['cases'] += 1
    totals['split'] += stops
    totals['control'] += control_rows
    acc['out_row'] = dict(index=row['index'], label=label, group=row['group'], entry_pc=hex(fx['entry_pc']), steps=len(row['steps']),
                          step_stop_pcs=[hex(s['stop_pc']) for s in row['steps']], split_phases=stops, control_steps=control_rows,
                          carry=dict(sorted(carry_row.items())), guarded=bool(row['guarded']),
                          cpp_error=error_row[1] if error_row else None, C_phase_digest_sha256=digest.hexdigest())
    unload_row(row)
    return acc


def compare(exe, rows, resources, st, program, instructions):
    totals = collections.Counter()
    program_reads = collections.Counter(fixed_reads=0, bank_reads=0, PVC_writes=0)
    carry_hist = collections.Counter({0: 0, 1: 0, 2: 0})
    preserved, first_pcs = {}, collections.Counter()
    out_rows, guards, deliberate, images, declared_ccr = [], [], [], [], []
    start_set = set(st['starts'])
    ctx = (exe, resources, st, program, instructions)

    def guarded_run(r):
        try:
            return run_row(r, ctx)
        except Exception:
            return dict(error=traceback.format_exc())
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(guarded_run, rows))
    failures = [(row['label'], acc['error']) for row, acc in zip(rows, results) if 'error' in acc]
    if failures:
        for n, (label, text) in enumerate(failures[:30]):
            print('ROW FAILED', label, text.strip().splitlines()[-1][:300])
            if n < 3:
                print(text)
        raise AssertionError('%d rows failed' % len(failures))
    for row, acc in zip(rows, results):
        totals.update(acc['totals'])
        program_reads.update(acc['program_reads'])
        carry_hist.update(acc['carry_hist'])
        first_pcs.update(acc['first_pcs'])
        for pc, slots in acc['preserved'].items():
            slot = preserved.setdefault(pc, {1: True, 2: True})
            for probe in (1, 2):
                slot[probe] = slot[probe] and slots[probe]
        guards.extend(acc['guards'])
        deliberate.extend(acc['deliberate'])
        images.extend(acc['images'])
        declared_ccr.extend(acc['declared_ccr'])
        out_rows.append(acc['out_row'])
    # carry preservation observed through the actual C++ (single-block phases probed with an incoming known C): equal to the contract's 15 FLOW_ONLY blocks
    # (298e is the consumer / restorer and is checked through the image bit0 instead)
    for pc, slots in preserved.items():
        assert pc in start_set and all(slots.values()) == (pc in st['preserving']), (hex(pc), slots)
    observed_preserving = sorted(pc for pc, slots in preserved.items() if all(slots.values()))
    if not DEBUG_ROWS:
        assert start_set <= set(first_pcs), sorted(hex(p) for p in start_set - set(first_pcs))
        assert set(observed_preserving) == set(st['preserving']), (sorted(hex(p) for p in set(observed_preserving) ^ set(st['preserving'])))
    totals = dict(sorted(totals.items()))
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in sorted(carry_hist.items())}
    totals['guard_rows'] = len(guards)
    totals['block_starts_run_as_first_pc_of_actual_cpp_phases'] = len(start_set & set(first_pcs))
    totals['block_starts_probed_for_carry_preservation'] = len(preserved)
    totals['block_starts_observed_carry_preserving'] = len(observed_preserving)
    return out_rows, totals, guards, dict(program_reads), deliberate, images, declared_ccr


def compare_guards(exe, guards, resources):
    rows, mismatches = [], []
    for row, phase, ram, state, pvc, bank in guards:
        fx = row['fixture']
        label = row['label']
        s = dict(state)
        actual = inv('guard_%s' % label, exe, ram, s, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        error = check_preserved(actual, ram, s, pvc, bank)
        want = GUARD_EXPECTED[label]
        if want is not None and error != want:
            mismatches.append((label, error, want))
        # same error with the other carry classes (no carry dependence of the failure unless the consumer 298e is the first block)
        s0 = dict(s, carry=0 if s['pc'] != WRAPPER else 2)
        again = inv('guard0_%s' % label, exe, ram, s0, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        again_error = check_preserved(again, ram, s0, pvc, bank)
        rows.append(dict(label=label, native_guard=phase['guard'], checked_API_error=error, expected_API_error=want, error_with_other_carry=again_error,
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    assert not mismatches, mismatches
    return rows


# ----------------------------------------------------------------------------------------------------------------- API-only checks
def reject(exe, label, start, changes, stop, error_expected, out, resources, external=0):
    r, s, p, b = start
    s = dict(s, carry=2)
    s.update(changes or {})
    actual = inv('negative_' + label, exe, r, s, p, b, resources, stop=stop, external=external)
    check_preserved(actual, r, s, p, b, error_expected)
    out.append(dict(label=label, error=error_expected, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))


def negatives(exe, base, st, resources, entry_buffer, entry_cue, wrapper_fail, wrapper_ok):
    out = []
    start_set = set(st['starts'])
    interior = [pc for pc in st['inside'] if pc not in start_set]
    for pc in interior:
        reject(exe, 'interior_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_UNIT, out, resources)
    operand = [pc for low, high in U7_RANGES for pc in range(low, high, 2) if pc not in st['instructions'] and pc not in start_set]
    assert not (set(operand) & set(interior))
    for pc in operand:
        reject(exe, 'operand_word_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_UNIT, out, resources)
    for pc in st['bundled']:
        assert pc in interior
    # outside the four routing ranges (data window e8a0c.., unit edges): no executor
    outside_mismatches = []
    for pc in (0xe8a0c, 0xe8a1c, 0xe8a46, 0xe8b5a, 0xe8b5c, 0x4abc0, 0x4abc2, 0x4b782, 0x4b82e, 0x4b830, 0x2984):
        if in_ranges(pc, U7_RANGES):
            continue
        # align2 run (HEAD dd61e61): 4b830 is now routed by F4 N03 ('unsupported animation objects n03 PC'); former expectation UNSUPPORTED_MACHINE.
        try:
            reject(exe, 'outside_entry_%06x' % pc, base, {'pc': pc}, 0xff000, SUPERSEDED_OUTSIDE.get(pc, UNSUPPORTED_MACHINE), out, resources)
        except AssertionError as error:      # collected: every stale probe of the loop is reported together
            outside_mismatches.append((hex(pc), error.args))
            continue
        if pc in SUPERSEDED_OUTSIDE:
            out[-1].update(former_expected_API_error=UNSUPPORTED_MACHINE, classification='superseded_by_F4_N03' if pc == 0x4b830 else 'superseded_by_routed_continuation_unit_not_traced', API_only_control=True)
    assert not outside_mismatches, outside_mismatches
    # Unrouted controls that no F4 unit can route: even work-RAM PCs.
    for pc in (0x10fe00, 0x10fefe):
        reject(exe, 'unrouted_ram_pc_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE, out, resources)
    for pc in (0x4aa89, 0x4b785, 0xe8a49, 0x2987, 0x298f, 0xe8ad1):
        reject(exe, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC, out, resources)
    # unknown-carry consumer: 298e with C Unknown
    r, s, p, b = base
    s2 = dict(wrapper_ok[1], carry=0)
    actual = inv('unknown_carry_298e', exe, wrapper_ok[0], s2, p, b, resources, stop=0xff000)
    check_preserved(actual, wrapper_ok[0], s2, p, b, UNKNOWN_CARRY)
    out.append(dict(label='unknown_carry_consumer_298e', error=UNKNOWN_CARRY, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    # e8a48 with A5 != 108000
    s3 = dict(entry_cue[1], a5=0x108002)
    actual = inv('e8a48_a5', exe, entry_cue[0], s3, p, b, resources, stop=0xff000)
    check_preserved(actual, entry_cue[0], s3, p, b, A5_REQUIRED)
    out.append(dict(label='e8a48_A5_not_108000', error=A5_REQUIRED, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    # unreached stop: runs on until the first PC without an executor
    for entry, stop in ((entry_buffer, 0xff000), (entry_cue, 0xff000)):
        s4 = dict(entry[1])
        actual = inv('unreached_stop_%06x' % stop, exe, entry[0], s4, p, b, resources, stop=stop)
        assert not actual[0]['ok']
        check_preserved(actual, entry[0], s4, p, b, None)
        out.append(dict(label='unreached_stop_%06x_from_%06x' % (stop, entry[1]['pc']), error=actual[4].strip(), all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))
    # widened alias guard: failure path with the e8a8a caller, the cue pointer chosen so that cue+4 (flags BYTE) lies inside the stack range [S-8, S+8),
    # directly and through the 64 KiB RAM mirror; and the control without aliasing succeeds
    fr, fs, fp, fb = wrapper_fail
    ctrl = inv('alias_control', exe, fr, dict(fs), fp, fb, resources, stop=0xe8a8a)
    assert ctrl[0]['ok'], ctrl[4]
    for shift in (0, 0x10000, 0x30000):
        cue = (fs['a7'] - 8 - shift) & M32
        assert 0x100000 <= cue < 0x200000
        ram2 = bytearray(fr)
        ram2[0xde26:0xde2a] = cue.to_bytes(4, 'big')
        actual = inv('alias_%x' % shift, exe, bytes(ram2), dict(fs), fp, fb, resources, stop=0xe8a8a)
        check_preserved(actual, bytes(ram2), dict(fs), fp, fb, ALIAS_X)
        out.append(dict(label='alias_guard_cue_%06x' % cue, error=ALIAS_X, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    return out, len(interior), len(operand)


def zero_step(exe, base, resources, starts):
    ram, state, pvc, bank = base
    rows = []
    for pc in starts:
        for carry in (0, 1, 2):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = inv('zero_%06x_%d' % (pc, carry), exe, ram, s, pvc, bank, resources, stop=pc)
            assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
            assert result['external_reads'] == 0 and not ports
            rows.append((pc, carry))
    return rows


# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve() == (ROOT / 'artifacts/animation_machine_buffer_cue_verify').resolve()
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='bufcue_verify_'))
    try:
        run(report_path)
    finally:
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_buffer_cue.py', 'tools/observe_animation_machine_buffer_cue.py',
                 'docs/analysis/animation-machine-buffer-cue-u7-contract.md', 'engine/src/animation_machine_buffer_cue.cpp',
                 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h', 'engine/tests/animation_machine_buffer_cue_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    report = audit_report(program, source)
    st = audit_static(program)
    instructions = st['instructions']
    rows = report['results'] + report['guarded_results']
    assert len(rows) == 1801
    if DEBUG_ROWS:
        rows = report['results'][:DEBUG_ROWS] + [r for r in report['results'] if r['group'] in ('custom-wrapper', 'custom-direct')] + report['guarded_results']
    matches, totals, guards, program_reads, deliberate, images, declared_ccr = compare(exe, rows, resources, st, program, instructions)
    assert DEBUG_ROWS or VERIFIED_ARTIFACTS <= set(report['artifacts']), len(VERIFIED_ARTIFACTS - set(report['artifacts']))
    guarded = compare_guards(exe, guards, resources)
    early = [d for d in deliberate if d['label'].startswith('guard-')]
    for d in early:
        guarded.append(dict(label=d['label'], native_guard='fires later in the native row', checked_API_error=d['error'], expected_API_error=GUARD_EXPECTED.get(d['label']),
                            error_with_other_carry=None, all_API_outputs_preserved=True, early_checked_error_phase=d['phase'], stop=d['stop'],
                            native_fault_rollback_equivalence_claimed=False))
    guarded.sort(key=lambda g: g['label'])
    assert DEBUG_ROWS or len(guarded) == 22, len(guarded)
    deliberate = [d for d in deliberate if not d['label'].startswith('guard-')]
    # API-only bases: natural stage-frame entry for the buffer, an entry of the cue frame, a 298e wrapper entry
    by_label = {r['label']: r for r in report['results']}

    def start_of(label):
        row = by_label[label]
        load_row(row)
        p0 = row['phases'][0]
        out = (p0['_data']['ram_before.bin'], dict(p0['incoming'], carry=initial_carry(row, p0['incoming']['pc'])), p0['_data']['pvc_before.bin'], p0['bank_before'])
        unload_row(row)
        return out
    first_label = report['results'][0]['label']
    base_ram, base_state, base_pvc, base_bank = start_of(first_label)
    base = (base_ram, dict(base_state), base_pvc, base_bank)
    cue_label = next(r['label'] for r in report['results'] if r['group'] == 'typed-cue' and r['fixture']['entry_pc'] == 0xe8a48)
    buf_label = next(r['label'] for r in report['results'] if r['group'] == 'typed-buffer' and r['fixture']['entry_pc'] == 0x4aa88)
    wrap_label = next(r['label'] for r in report['results'] if r['label'].startswith('wrapper-298e'))
    entry_cue, entry_buf, wrap = start_of(cue_label), start_of(buf_label), start_of(wrap_label)
    negative, interior_count, operand_count = negatives(exe, base, st, resources, entry_buf, entry_cue, start_of('wrapper-2986-fail-bcc-rete8a8a-sr2000'), wrap)
    zero = zero_step(exe, base, resources, st['starts'])
    cpp_cases, cpp_carry_table, routing_ok = cpp_static(st)
    assert cpp_cases == set(st['starts']), ([hex(p) for p in cpp_cases ^ set(st['starts'])])
    carry_table_extra = sorted(cpp_carry_table - set(st['preserving']) - {WRAPPER})
    carry_table_missing = sorted((set(st['preserving']) | {WRAPPER}) - cpp_carry_table)
    assert carry_table_missing == [] and carry_table_extra == [], ([hex(p) for p in carry_table_missing], [hex(p) for p in carry_table_extra])
    for name, expected in inputs.items():
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs = dict(refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log'):
        refs[str(path.resolve())] = cc.digest(path)
    categories = collections.Counter(d['category'] for d in deliberate)
    image_summary = collections.Counter()
    for label, j, image, model, known, popped in images:
        image_summary['phases'] += 1
        image_summary['independent_model_applicable'] += known
        image_summary['independent_model_equal'] += known and image == model
        image_summary['popped_bit_differs_from_pushed_bit(overlap)'] += popped is not None and popped != (image & 1)
    result = dict(
        schema_version=1, source=source, inputs=inputs, artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, contract_sha256=CONTRACT_SHA,
        native_artifacts_read_and_hash_checked=len(VERIFIED_ARTIFACTS) if not DEBUG_ROWS else None,
        native_manifest_entries=len(report['artifacts']),
        native_counts=dict(conditions=report['cases'], guarded=report['guarded_cases'], split_phases=report['total_split_phases'],
                           control_phases=report['total_control_phases'], group_counts=report['group_counts']),
        contract_ranges=st['table'], block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']],
        bundled_branch_count=len(st['bundled']), bundled_branches=[hex(p) for p in st['bundled']],
        carry_preserving_blocks=[hex(p) for p in st['preserving']], carry_consumer_producer_block=hex(WRAPPER),
        cpp_case_labels_equal_contract_block_starts=len(cpp_cases), cpp_carry_preserving_table_equal=True, cpp_routing_ranges_found=routing_ok,
        actual_CPP=dict(totals, matches=matches), original_program_read_audit=program_reads,
        wrapper_image_word_checks=dict(sorted(image_summary.items())),
        native_guards_checked_API=guarded, deliberate_differences=dict(count=len(deliberate), by_category=dict(sorted(categories.items())), rows=deliberate,
                                    guard_rows_with_earlier_checked_error=[g['label'] for g in early],
                                    declared_SR_fixture_ccr_differs_from_path_model=dict(count=len(declared_ccr), rows=declared_ccr)),
        negatives=negative, negative_count=len(negative) + len(guarded), interior_PCs_rejected=interior_count, operand_word_PCs_rejected=operand_count,
        zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2],
        carry_check='C++ carry equals the source-opcode walk over native-executed PCs (ORI #1,CCR Set / ANDI #fe,CCR Clear / MOVE (A7)+,SR at 2998 = bit0 of the '
                    'native popped WORD / flow-only preserved / else Unknown; a waiting status reports Unknown); at every 298e phase the incoming C from the previous '
                    'ACTUAL C++ output equals bit0 of the REAL native pushed image; incoming C probes 1 / 2 on one phase per distinct first block of a row',
        compile_command=command, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (stage-frame seeds, stage-entry 480bc entry states, typed corpora and declared variants), not natural scheduler, IRQ or gameplay reachability.',
                'Native SR is not observed; initial SR 2000 is the declared fixture value (the only declared C is the 298e direct entry from its declared SR).',
                'Existing executors cd58 / 28ae / 43e08 / sound 3aea are compared as whole results; their interior is not modelled here.',
                'Checked failures preserve API outputs, not original CPU fault rollback; deliberate differences are listed with counts.'],
        normalized_reference_paths=len(refs))
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'],
                          negatives=result['negative_count'], interior=interior_count, operand=operand_count, zero_step=len(zero),
                          deliberate=len(deliberate), carry=totals['carry_histogram'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
