"""Stage controller F1a (entry body 47a94, palette gate 47af0/72f0, dispatcher table 47b06..47b22, activation 47c04, scene initializer 1a5a4 and helpers)
native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation (artifacts/animation_machine_stage_entry_native) is an immutable input: this
verifier never invokes the observer main and never imports the observer module. Every native split phase (23893) and every continuous control phase (1427) is
replayed against the actual C++ `run_animation_machine`:
  * per split phase the full 64 KiB RAM / 16 registers / PC / A7 / PVC / bank / ordered ports / external reads / status of the actual C++ output; each phase resumes
    ONLY from the previous actual C++ output plus the declared host changes of the native step (RAM writes, the dispatcher re-entry PC redirect, the A7 delta, the
    declared 72f0 gate IRQ palette effect and the declared sprite / sound release writes); native split payloads are rebuilt from the stored continuous payload +
    checkpoint snapshots and every rebuilt payload is checked against the SHA256 recorded for the split phase;
  * continuous C++ run of each step vs the split C++ chain and vs the native continuous control; waits (cda4, 3aea, the 47af0 gate) give AnimationMachineWaiting at
    the same PC / A7 and resume correctly;
  * carry = source-opcode classification (ORI #1,CCR / ANDI #fe,CCR / EORI after the 1a2e8 CMP / 72f4 SUBI.B / TST and AND logical clears of the U3 return-C routines /
    289e equal compare / flow-only blocks) cross-checked at every executed BCC / BCS with a known classified C against the REAL native next PC (Unicorn SR is never
    read); the six F1a consumers give `stage entry caller requires known carry` on Unknown; incoming C probes (1 / 2) per distinct first block, flip checks at the
    consumers, FLOW_ONLY preservation observed through the actual C++;
  * native guards -> exact checked C++ error strings + full preservation; deliberate differences are classified by explicit rules and counted;
  * API-only negatives: all interior / operand-word PCs, odd PCs, outside entries, TRAP e909c, Unknown-carry consumers, zero-step at every block start x 3 carries.
Native SR is never read: C is a source-opcode classification.
"""
import collections
import concurrent.futures
import gzip
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
MAIN_ROOT = '/Users/start/Workspce/metalslug'
OUT = ROOT / 'artifacts/animation_machine_stage_entry_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_stage_entry_native'
NATIVE_SHA = 'c35d0baae047784a3ed3ea7da4d5a758e5a984b5e1c29e461fe594088ced6395'
NATIVE_TOOL_SHA = '9735595c447619285e052f003efcf76ceca823c9bfef8799579b3a33a5ef8c90'
CONTRACT = ROOT / 'docs/analysis/animation-machine-stage-controller-f1-contract.md'
CONTRACT_SHA = '82c6d30fdfe9e9f973e98663f4fc678c63f0f184c26b210eee9dc0a413b5791c'         # amended copy of the worktree
CONTRACT_OBSERVER_SHA = 'e66e9a2127167e332f8595941f90b456696380cd4bdd4b06fda3ab60bea5d12f'  # version pinned by the native observer
CONTRACT_OBSERVER_COMMIT = 'cc28e6f'
CPP_SHA = '3e0d3fd26cba985708bc2f75dfcb3c404b867b5c0001e4f3d9d6fa3c6e37862d'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
S = 0x1feffc
RET_FRAME = 0x2ac2
TRAP_PC = 0xe909c
WAIT_PCS = (0xcda4, 0x3aea, 0x47af0)
CONSUMERS = (0x47af6, 0x47b86, 0x47b9c, 0x47bd4, 0x1a670, 0x1996e)
F1A_RANGES = ((0x47a94, 0x47c5a), (0x72f0, 0x72fa), (0x1a5a4, 0x1a73c), (0x17292, 0x1829a), (0x19768, 0x19772), (0x19938, 0x19978), (0x199d4, 0x19a00),
              (0x19b50, 0x19b96), (0x19dee, 0x19e60), (0x1a07a, 0x1a086), (0x1a3c8, 0x1a3d6), (0x1a414, 0x1a442), (0xe8a1c, 0xe8a3a), (0xe905c, 0xe90ca),
              (0x477a2, 0x477ac), (0xddf9a, 0xddfa4), (0x362a, 0x3650), (0x9060, 0x9068), (0x4e254, 0x4e26c), (0xca56, 0xca5c), (0xca76, 0xca7e), (0xc3c0, 0xc3ce))
TABLE_SLOTS = tuple(range(0x47b06, 0x47b26, 4))
CALLBACK_STARTS = (0x47b5c, 0x47bfc)
LOGICAL_CLEAR = (0x19710, 0x1971c, 0x1938e, 0x19596)     # TST.W (A1) / TST.W c(A1) / AND.W D6,D7 : the logical op clears C ahead of the BNE / BPL that guards ORI #1,CCR
ADDED_SENTENCE_MARK = '(F1a native 관측 보정)'
UNSUPPORTED_STAGE = 'unsupported animation stage entry PC'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNKNOWN_CARRY = 'stage entry caller requires known carry'
UNSUPPORTED_SCRIPT = 'unsupported animation script placement PC'
UNALIGNED_PC = 'unaligned animation machine PC'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
WRITE_DEVICE = 'unsupported animation machine write device'
DEVICE_ADDRESS = 'unsupported program bus device address'
BUDGET = 'animation machine block budget exceeded'
CONDITIONAL = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
VERIFIED_ARTIFACTS = set()
RUN_DIR = None
WORKERS = 8
DEBUG_ROWS = int(os.environ.get('STAGE_ENTRY_DEBUG_ROWS', '0'))     # development switch only: the reported run is always the full set
API_ONLY = bool(os.environ.get('STAGE_ENTRY_API_ONLY'))        # development switch only
DEBUG_LABEL = os.environ.get('STAGE_ENTRY_DEBUG_LABEL', '')


def localize(name):
    local = str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name
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
    run = subprocess.run(args, capture_output=True, text=True, timeout=600, close_fds=False)
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
        assert item['cpu_address'] == pc and item['classification'] in ('candidate_instruction',), (hex(pc), item['classification'])
        self[pc] = item
        return item


# ----------------------------------------------------------------------------------------------------------------- contract
def git_show_old_contract():
    run = subprocess.run(['git', '-C', str(ROOT), 'show', '%s:docs/analysis/animation-machine-stage-controller-f1-contract.md' % CONTRACT_OBSERVER_COMMIT],
                         capture_output=True, timeout=60)
    assert run.returncode == 0, run.stderr
    return run.stdout


def audit_contract_amendment():
    """The worktree contract differs from the version pinned by the observer in exactly one appended sentence (decision 7(c) re-entry declaration)."""
    old = git_show_old_contract()
    assert sha(old) == CONTRACT_OBSERVER_SHA
    new = CONTRACT.read_bytes()
    assert sha(new) == CONTRACT_SHA
    old_lines, new_lines = old.decode().split('\n'), new.decode().split('\n')
    assert len(old_lines) == len(new_lines)
    diff = [(i, a, b) for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
    assert len(diff) == 1, [d[0] for d in diff]
    i, a, b = diff[0]
    assert b.startswith(a) and a.startswith('- (c) dispatcher 재진입 선언'), (i,)
    added = b[len(a):]
    assert added.startswith(' ' + ADDED_SENTENCE_MARK) and '104ca4' in added and '1ff000' in added and '\n' not in added
    return dict(old_sha256=CONTRACT_OBSERVER_SHA, new_sha256=CONTRACT_SHA, changed_line_number=i + 1, only_difference_appended_sentence=added,
                old_version_source='git show %s:docs/analysis/animation-machine-stage-controller-f1-contract.md' % CONTRACT_OBSERVER_COMMIT)


def pcs_in(text):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{4,6})`', text)]


def parse_contract(program):
    lines = CONTRACT.read_text().splitlines()
    table, code = [], []
    pattern = re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| (.*) \|$')
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        low, high = int(match.group(1), 16), int(match.group(2), 16)
        cell = match.group(3).strip()
        data = program[low:high]
        if re.fullmatch(r'`[0-9a-f]+`', cell):
            assert data.hex() == cell.strip('`'), hex(low)
            note = None
        else:
            digest = re.search(r'SHA256 `([0-9a-f]{64})`', cell)
            size = re.search(r'([\d,]+)바이트', cell)
            assert digest and sha(data) == digest.group(1) and int(size.group(1).replace(',', '')) == high - low
            note = 'digest row'
        table.append(dict(range='%x..%x' % (low, high), size=high - low, bytes_equal_to_rom=True, sha256=sha(data), note=note))
        code.append((low, high))
    assert code == list(F1A_RANGES) and sum(h - l for l, h in code) == 5608
    # the 17292 row structure is re-derived independently of the digest
    assert program[0x17292:0x1829a] == bytes.fromhex('43e800807000') + bytes.fromhex('22c0') * 2048 + bytes.fromhex('4e75')
    starts = bundled = preserve = None
    for line in lines:
        if line.startswith('`362a` `3634`'):
            starts = pcs_in(line)
        if line.startswith('- **묶인 조건분기 PC (25개'):
            bundled = pcs_in(line.split(':', 1)[1])
        if line.startswith('- **Carry 보존(FLOW_ONLY) block (63개)**'):
            tail = line.split('**:', 1)[1]
            preserve = pcs_in(tail.split('. ')[0] if '. ' in tail else tail)
    assert starts and len(starts) == len(set(starts)) == 145 and bundled and len(bundled) == len(set(bundled)) == 25
    assert preserve and len(preserve) == len(set(preserve)) == 63
    hud = re.search(r'자료 `ddfa4\.\.ddfdc`\(SHA256 `([0-9a-f]{64})`\)', CONTRACT.read_text())
    assert hud and sha(program[0xddfa4:0xddfdc]) == hud.group(1)
    return table, starts, bundled, preserve


def audit_static(program):
    table, starts, bundled, preserve = parse_contract(program)
    instructions = RomInstructions(program)
    inside = []
    for low, high in F1A_RANGES:
        pc = low
        while pc < high:
            inside.append(pc)
            pc += instructions[pc]['size']
        assert pc == high, hex(low)
    trap_items = [pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] == 'trap']
    assert trap_items == [TRAP_PC] and program[TRAP_PC:TRAP_PC + 2].hex() == '4e4f' and len(inside) == 2428
    start_set = set(starts)
    derived = set(low for low, _ in F1A_RANGES)
    for pc in inside:
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        target = re.search(r'\$([0-9a-f]+)$', item['op_str'])
        if name in CONDITIONAL + ('bra', 'bsr', 'jsr', 'dbra') and target:
            derived.add(int(target.group(1), 16))
        if name in CONDITIONAL + ('bsr', 'jsr', 'rts', 'bra', 'jmp', 'dbra', 'trap'):
            derived.add(pc + item['size'])
    derived = set(pc for pc in derived if in_ranges(pc, F1A_RANGES))
    extra = set(TABLE_SLOTS) | set(CALLBACK_STARTS)
    # TRAP e909c is the fall-through of the BEQ before e909e: a leader of the decoded stream, but a stop-only boundary and not one of the 145 contract starts
    assert TRAP_PC in derived and TRAP_PC not in start_set
    derived.discard(TRAP_PC)
    assert derived | extra == start_set, (sorted(hex(p) for p in (derived | extra) ^ start_set))
    # blocks: from each start to the next terminator / start
    blocks = {}
    for start in start_set:
        pcs, pc = [], start
        while True:
            item = instructions[pc]
            pcs.append(pc)
            name = item['mnemonic'].split('.')[0]
            end = name in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'dbra', 'trap') or name in CONDITIONAL
            following = pc + item['size']
            if end or following in start_set:
                break
            pc = following
        blocks[start] = pcs
    in_block = collections.Counter(pc for pcs in blocks.values() for pc in pcs)
    assert max(in_block.values()) == 1
    bundled_expected = sorted(pc for pc in inside if pc not in start_set and instructions[pc]['mnemonic'].split('.')[0] in CONDITIONAL + ('dbra',))
    assert bundled_expected == sorted(bundled), [hex(p) for p in set(bundled_expected) ^ set(bundled)]
    assert not (set(bundled) & start_set)
    flow = sorted(pc for pc in start_set if all(instructions[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc]))
    assert flow == sorted(preserve), [hex(p) for p in set(flow) ^ set(preserve)]
    interior = [pc for pc in inside if pc not in start_set and pc != TRAP_PC]
    inside_set = frozenset(inside)
    operand = [pc for low, high in F1A_RANGES for pc in range(low, high, 2) if pc not in inside_set]
    even_pcs = sum((high - low) // 2 for low, high in F1A_RANGES)
    assert even_pcs == 2804 and len(interior) + len(operand) == even_pcs - len(start_set) - 1 == 2658, (len(interior), len(operand))
    consumers = sorted(pc for pc in start_set if instructions[pc]['mnemonic'].split('.')[0] in ('bcc', 'bcs'))
    assert consumers == sorted(CONSUMERS), [hex(p) for p in set(consumers) ^ set(CONSUMERS)]
    producers = sorted(pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in ('ori', 'andi', 'eori') and re.search(r'\bccr\b', instructions[pc]['op_str']))
    x_users = [pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in ('addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')]
    assert x_users == []
    return dict(table=table, starts=starts, bundled=bundled, preserving=preserve, instructions=instructions, blocks=blocks, inside=inside,
                interior=interior, operand=operand, producers=producers, even_pcs=even_pcs)


def cpp_static(st):
    """C++ case labels vs the contract block starts, routing ranges vs the 22 code ranges, carry-preserving table vs the 63 FLOW_ONLY blocks."""
    text = (ROOT / 'engine/src/animation_machine_stage_entry.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text))
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    in_unit = set(pc for pc in table if in_ranges(pc, F1A_RANGES))
    start = machine.index('animation_buffer_cue_block(c);') + len('animation_buffer_cue_block(c);')
    route = machine[start:machine.index('animation_stage_entry_block(c);', start)]
    ranges = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', route))
    assert 'next.pc!=0xe909c' in route
    return cases, in_unit, ranges


# ----------------------------------------------------------------------------------------------------------------- native rows
def read_checked(name, expected):
    value = (NATIVE_DIR / name).read_bytes()
    assert sha(value) == expected, name
    VERIFIED_ARTIFACTS.add(name)
    return value


def trace_gz(pcs, events, guard):
    """The exact trace.json.gz bytes the observer wrote (compact json + newline, gzip level 9, mtime 0)."""
    return gzip.compress((json.dumps({'pcs': pcs, 'events': events, 'guard': guard}) + '\n').encode(), 9, mtime=0)


def fold_outputs(pvc, bank, events):
    """Independent PVC effects plus native video/watchdog writes in total order (as the card-child fold, plus the WORD port write at 3c0006 that the U5 contract
    records as one video port event)."""
    ports = []
    for event in events:
        if event['access'] != 'write':
            continue
        address, size = event['address'], event['size']
        if 0x2fe000 <= address < 0x300000:
            pvc, bank, encoded = common.fold_device(pvc, bank, [event])
            assert len(encoded) == 9
            ports.append(encoded)
        elif event['region'] in ('video', 'watchdog'):
            assert ((address == 0x3c0000 and size in (2, 4)) or (address == 0x3c0004 and size == 2) or (address == 0x300001 and size == 1) or
                    (address == 0x3c0006 and size == 2)), (hex(address), size)
            raw = bytes.fromhex(event['bytes'])
            assert len(raw) == size
            ports.append(struct.pack('>BII', size, address, int.from_bytes(raw, 'big')))
    return pvc, bank, b''.join(ports)


def ports_blob(events):
    return b''.join(struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in events if e['region'] in ('pvc', 'video', 'watchdog'))


def load_control(phase):
    data = {}
    for name, expected in phase['artifacts'].items():
        data[re.search(r'_phase_\d+_(.*)$', name).group(1)] = read_checked(name, expected)
    phase['_data'] = data
    phase['_trace'] = json.loads(gzip.decompress(data['trace.json.gz']))
    for snapshot in phase['snapshots']:
        snapshot['_ram'] = read_checked(snapshot['artifacts']['ram'], phase['artifacts'][snapshot['artifacts']['ram']])
        snapshot['_pvc'] = read_checked(snapshot['artifacts']['pvc'], phase['artifacts'][snapshot['artifacts']['pvc']])


def load_row(row):
    """The continuous control payloads and checkpoint snapshots exist for every row (hash checked). No split-phase payload file exists: the split phases are rebuilt
    from the control payload of their step (checkpoint snapshots = full RAM / PVC after every non-final phase, PC and event slices from the recorded pc_count / event
    counts) and every rebuilt payload (RAM before / after, PVC before / after, ports, the exact trace.json.gz bytes) is checked against the SHA256 recorded for that
    split phase."""
    for phase in row['continuous_control']:
        load_control(phase)
    rebuilt = 0
    for phase in row['phases']:
        step = [c for c in row['continuous_control'] if c['step'] == phase['step']]
        assert len(step) == 1
        phase['_control'] = step[0]
        assert not any((NATIVE_DIR / n).exists() for n in phase['artifacts'])
    for step in sorted({p['step'] for p in row['phases']}):
        parts = [p for p in row['phases'] if p['step'] == step]
        ctrl = parts[0]['_control']
        pcs, events = ctrl['_trace']['pcs'], ctrl['_trace']['events']
        snaps = {}
        for sn in ctrl['snapshots']:
            assert sn['registers']['pc'] not in snaps
            snaps[sn['registers']['pc']] = sn
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
            data = {'ram_before.bin': ram, 'ram_after.bin': after_ram, 'pvc_before.bin': pvc, 'pvc_after.bin': after_pvc, 'ports.bin': ports_blob(pev),
                    'trace.json.gz': trace_gz(ppcs, pev, guard)}
            for name, value in data.items():
                recorded = [h for n_, h in p['artifacts'].items() if n_.endswith('_' + name)]
                assert len(recorded) == 1 and sha(value) == recorded[0], (row['label'], step, k, name)
            p['_data'] = data
            p['_trace'] = {'pcs': ppcs, 'events': pev, 'guard': guard}
            rebuilt += 1
            ram, pvc = after_ram, after_pvc
    row['_rebuilt'] = rebuilt


def unload_row(row):
    for kind in ('phases', 'continuous_control'):
        for phase in row[kind]:
            for key in ('_data', '_trace', '_control'):
                phase.pop(key, None)
            for snapshot in phase['snapshots']:
                snapshot.pop('_ram', None)
                snapshot.pop('_pvc', None)


def audit_row(row, program):
    assert row['reproduced_twice'] and row['continuous_split_equivalent']
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
        assert phase['waiting'] == (phase['outgoing']['pc'] in WAIT_PCS and phase['guard'] is None and phase['stop_pc'] != phase['outgoing']['pc'])
    return counts_split


def audit_source_json(report, program, source, st):
    """The native static record (source.json): hash, ROM bytes of every recorded instruction and its decode equal the independent decode of this verifier."""
    static = json.loads(read_checked('source.json', report['artifacts']['source.json']))
    assert static['source'] == source
    assert [tuple(r) for r in static['ranges']] == list(F1A_RANGES)
    routing = sorted(tuple(r) for r in static['routing_ranges'])
    assert len(routing) == 23 and set(routing) == (set(F1A_RANGES) - {(0xe905c, 0xe90ca)}) | {(0xe905c, 0xe909c), (0xe909e, 0xe90ca)}
    assert list(static['wait_pcs']) == [0xcda4, 0x3aea, 0x47af0] and static['boundary_stop_pcs'] == report['boundary_stop_pcs']
    count = 0
    for item in static['instructions']:
        at, size = item['rom_offset'], item['size']
        assert at == item['cpu_address'] and bytes.fromhex(item['raw']) == program[at:at + size]
        mine = st['instructions'][at]
        assert (mine['mnemonic'], mine['op_str'], mine['size']) == (item['mnemonic'], item['op_str'], size), hex(at)
        count += 1
    assert count == 2427 and TRAP_PC not in [i['cpu_address'] for i in static['instructions']]
    return count


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_stage_entry.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'engine/src/animation_machine_stage_entry.cpp') == CPP_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_OBSERVER_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['declared_register_changes_at_step_boundaries'] == []
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert (report['cases'], report['guarded_cases'], report['split_steps'], report['control_steps']) == (310, 25, 23661, 1401)
    assert (report['guard_split_steps'], report['guard_control_steps'], report['total_split_phases'], report['total_control_phases']) == (232, 26, 23893, 1427)
    assert report['block_starts_covered'] == 145 and report['block_starts_uncovered'] == []
    assert report['boundary_stop_pcs'] == [RET_FRAME, 293996, 954524, 12584040]
    assert [c['kind'] for c in report['contract_discrepancies']] == ['contract-understated']
    for name, expected in report['inputs'].items():
        if name.endswith('docs/analysis/animation-machine-stage-controller-f1-contract.md'):
            assert expected == CONTRACT_OBSERVER_SHA          # the observer-pinned version: re-derived from git (audit_contract_amendment), the worktree copy is the amended one
            continue
        assert cc.digest(localize(name)) == expected, name
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    return report


# ----------------------------------------------------------------------------------------------------------------- carry
def branch_expect(item, carry):
    """Next PC of a consumer (BCC / BCS) for a known carry (1 Clear, 2 Set)."""
    name = item['mnemonic'].split('.')[0]
    target = int(re.search(r'\$([0-9a-f]+)$', item['op_str']).group(1), 16)
    fall = item['cpu_address'] + item['size']
    taken = (name == 'bcc' and carry == 1) or (name == 'bcs' and carry == 2)
    assert name in ('bcc', 'bcs') and carry in (1, 2)
    return target if taken else fall


def computed_reads(events):
    reads = collections.defaultdict(list)
    for e in events:
        if e['access'] == 'read' and e['pc'] in (0x72f0, 0x1a2e4, 0x1a2e8):
            reads[e['pc']].append(int(e['bytes'], 16))
    return reads


def classify_carry(instructions, carry, pcs, reads):
    """Source-opcode C classification (no native SR): ORI #1,CCR Set, ANDI #fe,CCR Clear, `EORI #1,CCR` after `CMP.W 541e(A5),D0` (1a2e8) = inverted borrow of the
    native read WORDs, `SUBI.B #80,D0` (72f4) = borrow of the native read BYTE, the logical clears (TST / AND) of the U3 return-C routines, the 289e equal compare
    branch Clear, flow-only opcodes preserve, anything else makes C Unknown."""
    counters = collections.Counter()
    for index, pc in enumerate(pcs):
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        if name == 'ori' and item['op_str'] == '#$1, ccr':
            carry = 2
        elif name == 'andi' and item['op_str'] == '#$fe, ccr':
            carry = 1
        elif name == 'eori' and item['op_str'] == '#$1, ccr':
            assert pc == 0x1a2ec, hex(pc)
            k = counters['eori']
            counters['eori'] += 1
            carry = 1 if reads[0x1a2e4][k] < reads[0x1a2e8][k] else 2
        elif pc == 0x72f4:
            k = counters['subi']
            counters['subi'] += 1
            carry = 2 if reads[0x72f0][k] < 0x80 else 1
        elif pc in LOGICAL_CLEAR:
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


def path_depends_on_incoming(instructions, pcs, reads):
    """True when a BCC / BCS executed in the phase sees a classified C that depends on the incoming C (probing another incoming C would change the path)."""
    for i, pc in enumerate(pcs):
        if instructions[pc]['mnemonic'].split('.')[0] in ('bcc', 'bcs'):
            if classify_carry(instructions, 1, pcs[:i], reads) != classify_carry(instructions, 2, pcs[:i], reads):
                return True
    return False


def consumer_checks(instructions, carry_in, executed, nexts, reads, totals):
    """At every executed BCC / BCS with a classified known C (produced inside the phase): the REAL native next PC equals the branch outcome of that C."""
    for index, pc in enumerate(executed):
        if instructions[pc]['mnemonic'].split('.')[0] in ('bcc', 'bcs'):
            carry = classify_carry(instructions, carry_in, executed[:index], reads)
            if carry == 0 or classify_carry(instructions, 1, executed[:index], reads) != classify_carry(instructions, 2, executed[:index], reads):
                continue
            assert nexts[index] == branch_expect(instructions[pc], carry), (hex(pc), carry, hex(nexts[index]))
            totals['consumer_real_branch_checks_C_produced_in_phase'] += 1


# ----------------------------------------------------------------------------------------------------------------- row replay
def apply_changes(ram, state, changes):
    ram = bytearray(ram)
    state = dict(state)
    entry_pc, entry_a7 = state['pc'], state['a7']
    kinds = []
    for change in changes:
        kind = change['kind']
        assert change['pc_before'] == entry_pc and change['a7_before'] == entry_a7, change
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


def initial_carry(row):
    """Declared initial C: only the carry-consumer direct entries carry a declared SR (2000 -> Clear, 2001 -> Set); every other entry starts Unknown."""
    sr = row['fixture'].get('sr')
    if sr is None:
        return 0
    return 2 if sr & 1 else 1


def check_result(actual, phase, pvc, bank, portbytes, events, status_override=None):
    result, ram, device, ports, error = actual
    assert result['ok'] and not error, error
    outgoing = phase['outgoing']
    assert {k: result[k] for k in common.REGS + ('pc',)} == outgoing, {
        k: (outgoing[k], result[k]) for k in common.REGS + ('pc',) if result[k] != outgoing[k]}
    assert result['status'] == (1 if phase['waiting'] else 0 if status_override is None else status_override), (result['status'], phase['waiting'])
    reads = sum(e['access'] == 'read' and e['address'] == 0xd00046 and e['size'] == 1 for e in events)
    assert result['external_reads'] == reads and result['bank_base'] == bank, (reads, result['external_reads'], bank, result['bank_base'])
    expected = phase['_data']['ram_after.bin']
    assert ram == expected, [(i, expected[i], ram[i]) for i in range(len(ram)) if ram[i] != expected[i]][:20]
    assert device == pvc, 'PVC mismatch'
    assert ports == portbytes, ('ports', ports.hex(), portbytes.hex())


def check_preserved(actual, ram, state, pvc, bank, expected_error=None):
    result, out_ram, out_pvc, ports, error = actual
    assert not result['ok'] and (expected_error is None or error.strip() == expected_error), (expected_error, error.strip())
    assert {k: result[k] for k in common.STATE_KEYS} == {k: state[k] for k in common.STATE_KEYS}
    assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
    assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
    return error.strip()


def computed_jump_target(executed, pcs):
    """Target of the executed `JMP 47b06(PC,D0.W)` at 47b02 of the phase (the next native PC), or None."""
    for i, pc in enumerate(executed):
        if pc == 0x47b02:
            return pcs[i]
    return None


def deliberate_error(label, error, first_pc, incoming_carry, start_set, jump_target=None):
    """Classify a C++ checked error that occurs where the native row continued. Returns (category, rule) or None."""
    if error == UNKNOWN_CARRY and first_pc in CONSUMERS and incoming_carry == 0:
        return ('consumer_with_unknown_carry',
                'decision 1/3: the BCC consumer reached through a computed JMP target (47b06+index) or with a non-tracked C has Unknown carry -> checked error '
                '(native: C = 0 from the MOVEQ / MOVE logical clear of the 47af8 block, BCC taken)')
    if error == UNSUPPORTED_STAGE and jump_target is not None and jump_target not in start_set and in_ranges(jump_target, F1A_RANGES):
        return ('native_executes_non_block_start',
                'the computed JMP target is a bundled branch / internal instruction (not a contract block start): the C++ rejects it (native executes the instruction)')
    return None


# guard rows whose C++ error is a deliberate difference to the native guard (category, rule)
GUARD_DELIBERATE = {
    'event-loop-forever-00-limit0-step0': ('native_watchdog_vs_cpp_block_cap', 'native: observer watchdog expired at 60000 instructions (the original loop has no bound); C++: finite 1,000,000-block cap'),
    'guard-banked-script-b3-zero-f788c': ('native_watchdog_vs_cpp_checked_script_PC', 'native: observer watchdog (60000 instructions) in the banked script walk; C++: the U5 script walk rejects the PC with a checked error'),
    'guard-banked-script-b3-nonzero-3c96a': ('native_32bit_address_fault_vs_cpp_24bit_mask', 'native Unicorn faults on the read of 6(A1) at 01000006 (unmapped 32-bit address); the C++ bus masks to 24 bits (000006, ROM vector area), reads it and later fails at a non-block-start F1a PC')}

GUARD_EXPECTED = {
    'body-141-live-RAM-record-reread': UNALIGNED_PC,                        # index ff -> 47b06+ff = 47c05 (odd)
    'table-index-01-odd-pc': UNALIGNED_PC, 'table-index-ff-odd-pc': UNALIGNED_PC, 'table-index-03-odd-pc': UNALIGNED_PC,
    'table-index-22-internal-pc': UNSUPPORTED_STAGE, 'table-index-24-internal-pc': UNSUPPORTED_STAGE,       # 47b28 / 47b2a lie in 47a94..47c5a, no block start
    'table-index-30-internal-pc': UNSUPPORTED_STAGE, 'table-index-32-internal-pc': UNSUPPORTED_STAGE,
    'event-tag-55-trap-undeclared': UNSUPPORTED_MACHINE,                    # e909c is excluded from the routing: no executor
    'event-loop-forever-00-limit0-step0': BUDGET,                           # native: observer watchdog (60000); C++: 1,000,000-block cap
    'event-odd-table-pointer': EVEN,                                        # WORD read at an odd address (am_read -> read_program_bus)
    'guard-clear-17292-rom': WRITE_DEVICE,                                  # write at 0x1080 (not RAM / PVC)
    'guard-clear-17292-past-ram': WRITE_DEVICE,                             # write at 0x200000
    'guard-clear-17292-odd': EVEN_WRITE,                                    # am_write LONG at an odd address
    'guard-odd-a7-gate-entry': EVEN,                                        # JSR 72f0 pushes a LONG at the odd A7 (write_program_bus_ram)
    'guard-odd-a6-record-pointer': EVEN, 'guard-odd-record-pointer': EVEN, 'guard-odd-a4-at-47aca': EVEN, 'guard-odd-a0-1a422': EVEN, 'guard-odd-a1-199e4': EVEN,
    'guard-banked-script-b3-zero-f788c': UNSUPPORTED_SCRIPT,                # native: observer watchdog (60000 steps) inside the banked script walk; C++: U5 rejects the script PC
    'guard-banked-script-b3-nonzero-3c96a': UNSUPPORTED_STAGE,              # native: Unicorn faults on the 32-bit address 01000006 (read of 6(A1)); C++ masks to 24 bits (ROM read) and runs on to a non-start F1a PC
    'guard-rom-write-a5': WRITE_DEVICE,                                     # WORD write at 0x2000 (A5 declared 0)
    'guard-bad-stop-return-4939c': UNSUPPORTED_MACHINE,                     # 4939c is excluded from the frame-helper routing
    'guard-odd-return-long': UNALIGNED_PC}                                  # RTS to 47af1 (odd)


def run_row(row, ctx):
    exe, resources, st, program, instructions = ctx
    start_set = set(st['starts'])
    acc = dict(totals=collections.Counter(), program_reads=collections.Counter(), carry_hist=collections.Counter(), first_pcs=collections.Counter(),
               preserved={}, guards=[], deliberate=[], skipped=collections.Counter(), waits=[], wait_carry=collections.Counter())
    totals = acc['totals']
    load_row(row)
    counts = audit_row(row, program)
    acc['program_reads'].update(counts)
    fx = row['fixture']
    label = row['label']
    phases = row['phases']
    first = phases[0]
    pvc = first['_data']['pvc_before.bin']
    bank = first['bank_before']
    ram = first['_data']['ram_before.bin']
    state = dict(first['incoming'], carry=initial_carry(row))
    expected_pvc, expected_bank = pvc, bank
    digest = hashlib.sha256()
    step_starts, step_ends = {}, {}
    gate_steps = {}
    carry_row = collections.Counter()
    seen_first = set()
    stops = 0
    error_row = None
    for j, phase in enumerate(phases):
        data = phase['_data']
        step = phase['step']
        if phase['phase_in_step'] == 0:
            ram, state, kinds = apply_changes(ram, state, phase['host_changes'])
            totals['declared_host_ram_changes'] += kinds.count('ram')
            totals['declared_dispatcher_reentry_pc_changes'] += kinds.count('pc')
            totals['declared_dispatcher_reentry_a7_deltas'] += kinds.count('a7_add')
            step_starts[step] = (ram, dict(state), pvc, bank)
        else:
            assert not phase['host_changes']
        assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (label, j)
        assert ram == data['ram_before.bin'], (label, j)
        assert bank == phase['bank_before']
        events = phase['_trace']['events']
        executed = phase['_trace']['pcs'][:-1]
        if phase['guard'] is not None:
            assert j == len(phases) - 1 and row['guarded']
            acc['guards'].append((row, phase, ram, dict(state), pvc, bank, step_starts[step]))
            break
        expected_pvc, expected_bank, portbytes = fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
        actual = inv('c%04d_split_%03d' % (row['index'], j), exe, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        first_pc = executed[0] if executed else None
        if not actual[0]['ok']:
            error = check_preserved(actual, ram, state, pvc, bank)
            category = deliberate_error(label, error, first_pc, phase_in['carry'], start_set, computed_jump_target(executed, phase['_trace']['pcs'][1:]))
            assert category is not None, ('UNEXPECTED C++ ERROR', label, j, hex(phase['stop_pc']), error)
            acc['deliberate'].append(dict(label=label, step=step, phase=j, stop=hex(phase['stop_pc']), first_pc=hex(first_pc), category=category[0], rule=category[1],
                                          error=error, computed_jump_target=hex(computed_jump_target(executed, phase['_trace']['pcs'][1:]) or 0), native_continued_to=hex(phase['outgoing']['pc']), all_API_outputs_preserved=True,
                                          native_phases_unreplayed_after_error=len(phases) - j - 1))
            acc['skipped'][category[0]] += len(phases) - j - 1
            error_row = (j, error)
            break
        # deliberate: 47af6 BCC.B 47af0 taken (C Clear) lands on 47af0 which is also the requested stop; the native split treats it as an ordinary stop (no spin
        # iteration finished), the C++ declares the gate wait (Waiting) as soon as the BCC is taken
        gate_at_stop = (first_pc == 0x47af6 and phase_in['carry'] == 1 and phase['outgoing']['pc'] == 0x47af0 == phase['stop_pc'] and not phase['waiting'])
        check_result(actual, phase, expected_pvc, expected_bank, portbytes, events, status_override=1 if gate_at_stop else None)
        if gate_at_stop:
            acc['deliberate'].append(dict(label=label, step=step, phase=j, stop='0x47af0', first_pc='0x47af6', category='gate_wait_reported_when_47af0_is_the_stop',
                                          rule='47af6 with declared C Clear: the native split stops at 47af0 as an ordinary checkpoint (status Returned semantics); the C++ reports Waiting at 47af0 (same PC, registers, RAM)',
                                          error=None, all_API_outputs_preserved=None, native_phases_unreplayed_after_error=0))
            totals['deliberate_status_waiting_at_requested_stop'] += 1
            gate_steps[step] = (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base'])
        result, ram, pvc, _, _ = actual
        reads = computed_reads(events)
        want = classify_carry(instructions, state['carry'], executed, reads)
        if phase['waiting']:
            if phase['outgoing']['pc'] == 0x47af0:
                # the 47af6 BCC (C Clear) leaves PC 47af0 and returns Waiting; the Clear produced by 72f4 is still the known C of the output
                assert want == 1
                acc['wait_carry']['gate_47af0_waiting_carry_' + CARRY_NAME[result['carry']]] += 1
            else:
                want = 0                         # sprite / sound executor blocks are not carry-preserving: C Unknown at the wait (API wait contract)
                acc['wait_carry']['%x_waiting_carry_%s' % (phase['outgoing']['pc'], CARRY_NAME[result['carry']])] += 1
            acc['waits'].append((label, j, phase['outgoing']['pc'], result['a7'], phase['outgoing']['a7']))
        assert result['carry'] == want, (label, j, hex(phase['outgoing']['pc']), result['carry'], want)
        acc['carry_hist'][result['carry']] += 1
        carry_row[CARRY_NAME[result['carry']]] += 1
        if first_pc in start_set:
            acc['first_pcs'][first_pc] += 1
        if first_pc in CONSUMERS:
            # the consumer starts the phase: the incoming C (previous ACTUAL C++ output / declared SR) is known and the REAL native next PC follows it;
            # the flipped C must select the other destination without changing anything else
            assert phase_in['carry'] in (1, 2), (label, j, phase_in['carry'])
            assert phase['_trace']['pcs'][1] == branch_expect(instructions[first_pc], phase_in['carry']), (label, j)
            flipped = 3 - phase_in['carry']
            other = branch_expect(instructions[first_pc], flipped)
            again = inv('c%04d_flip_%03d' % (row['index'], j), exe, data['ram_before.bin'], dict(phase_in, carry=flipped), phase_pvc, phase_bank, resources,
                        stop=other, external=fx['external'])
            if first_pc == 0x47af6 and flipped == 1:
                # BCC.B 47af0 with C Clear: PC 47af0 is the declared wait of the gate (Waiting, same PC)
                assert again[0]['ok'] and again[0]['status'] == 1 and again[0]['pc'] == other, (label, j)
            else:
                assert again[0]['ok'] and not again[4] and again[0]['pc'] == other, (label, j)
            assert again[0]['carry'] == flipped and again[1] == data['ram_before.bin'] and again[2] == phase_pvc and again[0]['bank_base'] == phase_bank
            assert {k: again[0][k] for k in common.REGS} == {k: phase_in[k] for k in common.REGS}
            totals['consumer_first_pc_checks'] += 1
            totals['consumer_flip_checks'] += 1
            totals['consumer_flip_%06x_incoming_%s' % (first_pc, CARRY_NAME[phase_in['carry']])] += 1
        else:
            consumer_checks(instructions, phase_in['carry'], executed, phase['_trace']['pcs'][1:], reads, totals)
        # incoming C probes: once per distinct first block of the row, only when the path of the phase does not depend on the incoming C
        if not phase['waiting'] and first_pc not in seen_first and first_pc not in CONSUMERS:
            seen_first.add(first_pc)
            if path_depends_on_incoming(instructions, executed, reads):
                totals['carry_probe_phases_skipped_path_depends_on_incoming_C'] += 1
            else:
                for probe in (1, 2):
                    again = inv('c%04d_carry%d_%03d' % (row['index'], probe, j), exe, data['ram_before.bin'], dict(phase_in, carry=probe), phase_pvc,
                                phase_bank, resources, stop=phase['stop_pc'], external=fx['external'])
                    assert again[0]['ok'] and not again[4], (label, j, probe)
                    assert again[0]['carry'] == classify_carry(instructions, probe, executed, reads), (label, j, probe, again[0]['carry'])
                    assert {k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in result.items() if k != 'carry'}
                    assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                    totals['carry_probes'] += 1
                    totals['carry_probe_preserved'] += again[0]['carry'] == probe
                    blocks = [pc for pc in executed if pc in start_set]
                    if len(blocks) == 1 and blocks[0] == first_pc:
                        slot = acc['preserved'].setdefault(first_pc, {1: True, 2: True})
                        slot[probe] = slot[probe] and again[0]['carry'] == probe
        totals['carry_checks'] += 1
        totals['native_waiting_phases'] += bool(phase['waiting'])
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
    control_rows = 0
    for phase in row['continuous_control']:
        step = phase['step']
        if phase['guard'] is not None or step not in step_starts:
            continue
        c_ram, c_state, c_pvc, c_bank = step_starts[step]
        data = phase['_data']
        assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
        e_pvc, e_bank, portbytes = fold_outputs(c_pvc, c_bank, phase['_trace']['events'])
        assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        actual = inv('c%04d_control_%d' % (row['index'], step), exe, c_ram, c_state, c_pvc, c_bank, resources, stop=phase['stop_pc'], external=fx['external'])
        if error_row is not None and step == phases[error_row[0]]['step']:
            assert check_preserved(actual, c_ram, c_state, c_pvc, c_bank, error_row[1]) == error_row[1]
            totals['continuous_runs_agree_with_split_error'] += 1
            continue
        if step in gate_steps:
            # the continuous C++ run passes the same 47af0 gate wait as the split chain: Waiting at 47af0, state equal to the split phase output
            assert actual[0]['ok'] and actual[0]['status'] == 1 and actual[0]['pc'] == 0x47af0
            assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == gate_steps[step]
            totals['continuous_runs_waiting_at_47af0_equal_split_gate_phase'] += 1
            continue
        assert actual[0]['ok'] and not actual[4], (label, step, actual[4])
        check_result(actual, phase, e_pvc, e_bank, portbytes, phase['_trace']['events'])
        assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == step_ends[step], (label, step)
        control_rows += 1
    totals['cases'] += 1
    totals['split'] += stops
    totals['control'] += control_rows
    totals['split_phases_rebuilt_from_control_and_hash_checked'] += row['_rebuilt']
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
    out_rows, guards, deliberate, waits = [], [], [], []
    skipped, wait_carry = collections.Counter(), collections.Counter()
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
            print('ROW FAILED', label, text.strip().splitlines()[-1][:400])
            if n < 3:
                print(text)
        raise AssertionError('%d rows failed' % len(failures))
    for row, acc in zip(rows, results):
        totals.update(acc['totals'])
        program_reads.update(acc['program_reads'])
        carry_hist.update(acc['carry_hist'])
        first_pcs.update(acc['first_pcs'])
        skipped.update(acc['skipped'])
        wait_carry.update(acc['wait_carry'])
        waits.extend(acc['waits'])
        for pc, slots in acc['preserved'].items():
            slot = preserved.setdefault(pc, {1: True, 2: True})
            for probe in (1, 2):
                slot[probe] = slot[probe] and slots[probe]
        guards.extend(acc['guards'])
        deliberate.extend(acc['deliberate'])
        out_rows.append(acc['out_row'])
    # carry preservation observed through the actual C++ (single-block phases probed with an incoming known C)
    for pc, slots in preserved.items():
        assert pc in start_set and all(slots.values()) == (pc in st['preserving']), (hex(pc), slots)
    observed_preserving = sorted(pc for pc, slots in preserved.items() if all(slots.values()))
    if not DEBUG_ROWS:
        assert start_set <= set(first_pcs), sorted(hex(p) for p in start_set - set(first_pcs))
        for pc in CONSUMERS:
            assert any(k.startswith('consumer_flip_%06x_incoming_' % pc) for k in totals), hex(pc)
    totals = dict(sorted(totals.items()))
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in sorted(carry_hist.items())}
    totals['guard_rows'] = len(guards)
    totals['block_starts_run_as_first_pc_of_actual_cpp_phases'] = len(start_set & set(first_pcs))
    totals['block_starts_probed_for_carry_preservation'] = len(preserved)
    totals['block_starts_observed_carry_preserving'] = len(observed_preserving)
    totals['carry_consumers_checked_by_flip'] = len([pc for pc in CONSUMERS if any(k.startswith('consumer_flip_%06x_incoming_' % pc) for k in totals)])
    return out_rows, totals, guards, dict(program_reads), deliberate, dict(skipped), dict(wait_carry), waits, observed_preserving, set(first_pcs)


def compare_guards(exe, guards, resources):
    rows, mismatches = [], []
    for row, phase, ram, state, pvc, bank, step_start in guards:
        fx = row['fixture']
        label = row['label']
        s = dict(state)
        actual = inv('guard_%s' % label, exe, ram, s, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        error = check_preserved(actual, ram, s, pvc, bank)
        want = GUARD_EXPECTED[label]
        if error != want:
            mismatches.append((label, error, want))
        # the same error from the start of the native step (continuous run), and with another incoming C class
        c_ram, c_state, c_pvc, c_bank = step_start
        cont = inv('guardc_%s' % label, exe, c_ram, dict(c_state), c_pvc, c_bank, resources, stop=phase['stop_pc'] if phase['phase_in_step'] == 0 else phase['step_stop_pc'],
                   external=fx['external'])
        cont_error = check_preserved(cont, c_ram, dict(c_state), c_pvc, c_bank)
        s0 = dict(s, carry=0 if s['carry'] else 2)
        again = inv('guard0_%s' % label, exe, ram, s0, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        again_error = check_preserved(again, ram, s0, pvc, bank)
        note = GUARD_DELIBERATE.get(label)
        rows.append(dict(label=label, native_guard=phase['guard'], deliberate_difference=note[0] if note and note[1] else None, deliberate_rule=note[1] if note else None,
                         checked_API_error=error, expected_API_error=want, continuous_step_error=cont_error,
                         error_with_other_carry=again_error, all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    assert not mismatches, mismatches
    return rows


# ----------------------------------------------------------------------------------------------------------------- API-only checks
SUPERSEDED_OUTSIDE = {0x72fa: 'animation machine external read queue empty', 0x7300: 'unsupported animation irq f6b PC',
                      # FR1b routes ddfdc (contract animation-machine-frontier-fr1b-contract.md, decision 7; former expectation 'unsupported animation
                      # machine PC'): ddfdc..de00a run, the RTS de00a returns to the base state's natural return LONG and the frame code there reads an
                      # external device (empty queue in this harness; not device evidence). Observed with this verifier's invoke() on base 958d66a + FR1b.
                      0xddfdc: 'animation machine external read queue empty'}
SUPERSEDED_BY = {0x72fa: 'F6b (72f0..7326)', 0x7300: 'F6b (72f0..7326)', 0xddfdc: 'FR1b (ddfdc..de00c)'}


def reject_one(args):
    exe, label, start, changes, stop, error_expected, resources = args
    r, s, p, b = start
    s = dict(s, carry=2)
    s.update(changes or {})
    actual = inv('negative_' + label, exe, r, s, p, b, resources, stop=stop)
    try:
        check_preserved(actual, r, s, p, b, error_expected)
    except AssertionError as error:      # collected by negatives(): every stale probe is reported together with its label
        return dict(label=label, failed=error.args)
    return dict(label=label, error=error_expected, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False)


def run_parallel(function, items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(function, items))


def negatives(exe, base, st, resources):
    start_set = set(st['starts'])
    instructions = st['instructions']
    jobs = []
    # every interior instruction PC and operand-word PC of the 22 ranges (2658 = 2804 even PCs - 145 starts - the TRAP boundary)
    for pc in st['interior']:
        jobs.append((exe, 'interior_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_STAGE, resources))
    for pc in st['operand']:
        jobs.append((exe, 'operand_word_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_STAGE, resources))
    # TRAP e909c (stop-only boundary): direct entry has no executor; reaching it without the declared stop is the guard row
    jobs.append((exe, 'trap_e909c_direct_entry', base, {'pc': TRAP_PC}, 0xff000, UNSUPPORTED_MACHINE, resources))
    jobs.append((exe, 'trap_e909c_direct_entry_stop_e909e', base, {'pc': TRAP_PC}, 0xe909e, UNSUPPORTED_MACHINE, resources))
    # data window and gaps between the executors: no executor of the machine
    # 72fa / 7300 (former expectation UNSUPPORTED_MACHINE) lie in the F6b range 72f0..7326 (palette transfer, ten-unit batch): 72fa now ends with the external-read queue
    # error (non-physical read, empty queue in this harness; not device evidence), 7300 is an F6b interior PC. Former values are recorded in the report row; the
    # work-RAM PCs 10fe00/10fefe are the unrouted controls.
    for pc in (0xddf98, 0xddfa4, 0xddfdc, 0x72fa, 0x7300, 0xe8a3a, 0xe8a46, 0x9068, 0x4e26c, 0xca5c, 0xddf90, 0x10fe00, 0x10fefe):
        if in_ranges(pc, F1A_RANGES):
            continue
        jobs.append((exe, 'outside_entry_%06x' % pc, base, {'pc': pc}, 0xff000, SUPERSEDED_OUTSIDE.get(pc, UNSUPPORTED_MACHINE), resources))
    # odd PCs: alignment is checked before routing
    for low, high in F1A_RANGES:
        jobs.append((exe, 'odd_pc_entry_%06x' % (low + 1), base, {'pc': low + 1}, 0xff000, UNALIGNED_PC, resources))
        jobs.append((exe, 'odd_pc_entry_%06x' % (high - 1), base, {'pc': high - 1}, 0xff000, UNALIGNED_PC, resources))
    for pc in (0x1, 0xffffff, 0xdeadbeef, 0x47b07, 0x47c05):
        jobs.append((exe, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC, resources))
    # even PC outside every range
    for pc in (0x0, 0xffffffe, 0x1000000, 0xdeadbee):
        jobs.append((exe, 'out_of_range_entry_%x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE, resources))
    out = run_parallel(reject_one, jobs)
    failed = [row for row in out if 'failed' in row]
    assert not failed, failed
    for row in out:
        if row['label'].startswith('outside_entry_') and int(row['label'][14:], 16) in SUPERSEDED_OUTSIDE:
            row.update(former_expected_API_error=UNSUPPORTED_MACHINE, superseded_by=SUPERSEDED_BY[int(row['label'][14:], 16)], API_only_control=True)
    # the six carry consumers need a known incoming C (Unknown -> checked error, full rollback)
    r, s, p, b = base
    for pc in CONSUMERS:
        s0 = dict(s, pc=pc, carry=0)
        actual = inv('unknown_carry_%06x' % pc, exe, r, s0, p, b, resources, stop=0xff000)
        check_preserved(actual, r, s0, p, b, UNKNOWN_CARRY)
        out.append(dict(label='unknown_carry_consumer_%06x' % pc, error=UNKNOWN_CARRY, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    # positive controls: a known incoming C is consumed and preserved (47af6 with C Clear is the gate wait at 47af0)
    controls = []
    for pc in CONSUMERS:
        for carry in (1, 2):
            want = branch_expect(instructions[pc], carry)
            s2 = dict(s, pc=pc, carry=carry)
            res, out_ram, out_pvc, ports, error = inv('consumer_%06x_%d' % (pc, carry), exe, r, s2, p, b, resources, stop=want)
            assert res['ok'] and not error and res['pc'] == want and res['carry'] == carry and out_ram == r and out_pvc == p and not ports
            assert res['status'] == (1 if (pc == 0x47af6 and carry == 1) else 0)
            assert {k: res[k] for k in common.REGS} == {k: s2[k] for k in common.REGS}
            controls.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], next_pc=hex(want), status=res['status'], carry_preserved=True, API_state_unchanged=True))
    return out, controls


def zero_step_one(args):
    exe, base, resources, pc, carry = args
    ram, state, pvc, bank = base
    s = dict(state, pc=pc, carry=carry)
    result, out_ram, out_pvc, ports, error = inv('zero_%06x_%d' % (pc, carry), exe, ram, s, pvc, bank, resources, stop=pc)
    assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
    assert {k: result[k] for k in common.STATE_KEYS} == s
    assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
    assert result['external_reads'] == 0 and not ports
    return (pc, carry)


def zero_step(exe, base, resources, starts):
    return run_parallel(zero_step_one, [(exe, base, resources, pc, carry) for pc in starts for carry in (0, 1, 2)])


# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve().name == 'animation_machine_stage_entry_execution'
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='stage_entry_verify_'))
    try:
        run(report_path)
    finally:
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_stage_entry.py', 'tools/observe_animation_machine_stage_entry.py',
                 'docs/analysis/animation-machine-stage-controller-f1-contract.md', 'engine/src/animation_machine_stage_entry.cpp',
                 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h', 'engine/tests/animation_machine_stage_entry_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    amendment = audit_contract_amendment()
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    report = audit_report(program, source)
    st = audit_static(program)
    static_instructions = audit_source_json(report, program, source, st)
    instructions = st['instructions']
    rows = report['results'] + report['guarded_results']
    assert len(rows) == 335
    if API_ONLY:
        rows = []
    elif DEBUG_ROWS:
        rows = [r for r in report['results'] if any(x in r['label'] for x in DEBUG_LABEL.split(','))][:DEBUG_ROWS] if DEBUG_LABEL else report['results'][:DEBUG_ROWS] + report['guarded_results']
    matches, totals, guards, program_reads, deliberate, skipped, wait_carry, waits, observed_preserving, first_pcs = compare(exe, rows, resources, st, program, instructions)
    control_names = set(n for n in report['artifacts'] if '_split_phase_' not in n)
    assert DEBUG_ROWS or API_ONLY or VERIFIED_ARTIFACTS == control_names, (len(VERIFIED_ARTIFACTS), len(control_names))
    if DEBUG_ROWS and not API_ONLY:
        print(json.dumps(dict(debug_totals=totals, deliberate=[(d['label'], d['category']) for d in deliberate], waits=len(waits), wait_carry=wait_carry), default=str))
        guarded = compare_guards(exe, guards, resources)
        print('guards ok', [g['label'] + ':' + g['checked_API_error'] for g in guarded])
        return
    guarded = compare_guards(exe, guards, resources)
    guard_labels = sorted(r['label'] for r in report['guarded_results'])
    if not DEBUG_ROWS and not API_ONLY:
        assert sorted(g['label'] for g in guarded) == guard_labels and len(guarded) == 25
    by_label = {r['label']: r for r in report['results']}
    base_row = by_label['body-000-actual59-catalog-records']
    load_row(base_row)
    p0 = base_row['phases'][0]
    base = (p0['_data']['ram_before.bin'], dict(p0['incoming'], carry=initial_carry(base_row)), p0['_data']['pvc_before.bin'], p0['bank_before'])
    unload_row(base_row)
    negative, consumer_controls = negatives(exe, base, st, resources)
    zero = zero_step(exe, base, resources, st['starts'])
    cpp_cases, cpp_carry_table, cpp_ranges = cpp_static(st)
    expected_cases = set(st['starts'])
    assert cpp_cases == expected_cases, ([hex(p) for p in cpp_cases ^ expected_cases])
    routing_expected = sorted(r for r in F1A_RANGES if r != (0xe905c, 0xe90ca)) + [(0xe905c, 0xe90ca)]
    assert cpp_ranges == sorted(routing_expected), (cpp_ranges, routing_expected)
    carry_table_extra = sorted(cpp_carry_table - set(st['preserving']))
    carry_table_missing = sorted(set(st['preserving']) - cpp_carry_table)
    assert carry_table_missing == [], [hex(p) for p in carry_table_missing]
    assert carry_table_extra == [], [hex(p) for p in carry_table_extra]
    for name, expected in inputs.items():
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs = dict(refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log'):
        refs[str(path.resolve())] = cc.digest(path)
    categories = collections.Counter(d['category'] for d in deliberate)
    result = dict(
        schema_version=1, source=source, inputs=inputs, artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, cpp_sha256=CPP_SHA, contract_sha256=CONTRACT_SHA,
        contract_amendment=amendment,
        native_artifacts_read_and_hash_checked=len(VERIFIED_ARTIFACTS) if not DEBUG_ROWS else None, native_manifest_entries=len(report['artifacts']),
        native_counts=dict(conditions=report['cases'], guarded=report['guarded_cases'], split_phases=report['total_split_phases'],
                           control_phases=report['total_control_phases'], group_counts=report['group_counts']),
        native_static_record_instructions_checked=static_instructions,
        contract_ranges=st['table'], block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']],
        executable_block_start_count=len(st['starts']), bundled_branch_count=len(st['bundled']), bundled_branches=[hex(p) for p in st['bundled']],
        carry_preserving_blocks=[hex(p) for p in st['preserving']], carry_consumers=[hex(p) for p in CONSUMERS],
        carry_producers_decoded=[hex(p) for p in st['producers']],
        cpp_case_labels_equal_contract_block_starts=len(cpp_cases), cpp_routing_ranges_equal_22_code_ranges_minus_e909c=True,
        cpp_carry_preserving_table_in_unit_equals_63=True,
        actual_CPP=dict(totals, matches=matches), original_program_read_audit=program_reads,
        waits=dict(count=len(waits), carry_at_wait=wait_carry, a7_equal_native=all(w[3] == w[4] for w in waits)),
        native_guards_checked_API=guarded,
        deliberate_differences=dict(count=len(deliberate), by_category=dict(sorted(categories.items())), rows=deliberate,
                                    native_phases_not_replayed_after_a_checked_error=skipped),
        negatives=negative, negative_count=len(negative) + len(guarded), interior_PCs_rejected=len(st['interior']), operand_word_PCs_rejected=len(st['operand']),
        consumer_controls=consumer_controls, zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2],
        carry_check='C++ carry equals the source-opcode walk over native-executed PCs (ORI #1,CCR Set / ANDI #fe,CCR Clear / EORI after the 1a2e8 CMP.W from the native read '
                    'WORDs / 72f4 SUBI.B from the native read BYTE / TST and AND logical clears at 19710 1971c 1938e 19596 / 289e equal compare / flow-only preserved / else Unknown; '
                    'sprite and sound waits report Unknown, the 47af0 gate wait keeps the Clear of 72f4); at every executed BCC / BCS with a C produced inside the phase the '
                    'classified C is checked against the REAL native next PC; consumer-first phases take the incoming C from the previous ACTUAL C++ output and are '
                    'checked against the real native branch plus a flipped-C control; incoming C probes 1 / 2 on one phase per distinct first block of a row',
        compile_command=command, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (stage_entry_body begin states, declared dispatcher re-entries, recorded stage_activation_prefix states and declared fixtures on captured '
                'native states), not natural scheduler, IRQ or gameplay reachability. A dispatcher re-entry is a declared PC redirect + A7 delta + return LONG 2ac2 at A7 + '
                'dispatcher base LONG 104ca4; the gate IRQ is the declared minimal palette effect (107ded bit7).',
                'Native SR is not observed; the initial SR 2000 is a declared fixture value (SR 2000 / 2001 only for the six consumer direct entries).',
                'Existing executors (U1..U7, cleanup, palette_bind, exit, screen, fade_card, hud, sprite, sound) are compared as whole results; their interior is not modelled here.',
                'Checked failures preserve API outputs, not original CPU fault rollback; deliberate differences are listed with counts.',
                'No BIOS execution, no natural scheduler, no natural IRQ is claimed.'],
        normalized_reference_paths=len(refs))
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'],
                          negatives=result['negative_count'], interior=len(st['interior']), operand=len(st['operand']), zero_step=len(zero),
                          deliberate=len(deliberate), carry=totals['carry_histogram'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
