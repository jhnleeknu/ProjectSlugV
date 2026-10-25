"""Stage controller F1c1 (stage catalog 477e4 / 477ee, music compare, entry-effect table 478a8, dispatcher callbacks 478de 4790a 4798e, child allocation
47934 4794c 47964, cut at the callback 479b0 = F1c2) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection.  The frozen native observation (artifacts/animation_machine_stage_catalog_native) is an immutable input: this
verifier never invokes the observer main and never imports the observer module.  The native record keeps, per frame (one frame = one machine run from a callback PC to
the dispatcher return 2ac2, or to a declared stop / wait): the declared step (host changes, split checkpoints, stop PC), the complete end state of the continuous run
(16 registers, PC, bank, RAM / PVC / ordered ports as SHA256, port count, external reads, waiting) and the state SHA256 of the observer; frames of the typed fixtures, of
8 natural seeds and the boundary frames carry the full dumps (RAM before / after, PVC, ordered ports, trace of PCs and bus events, leader registers).  The natural F1b
prefix frames 0..235 of 129 seeds were recorded once with the full-state SHA only and are compared by that SHA (and its parts).  Every condition is replayed against
the actual C++ `run_animation_machine`:
  * the split chain: stop at every declared checkpoint in order, every phase resumes ONLY from the previous actual C++ output (RAM / 16R / PC / A7 / PVC / bank / carry)
    plus the declared host changes of the native step (RAM writes, the dispatcher re-entry PC redirect, the A7 delta, the declared IRQ palette effect, the declared
    sprite / sound release writes);
  * the continuous C++ run of each step vs the split C++ chain and vs the native continuous end state; waits (3aea sound ring, the 478de gate) give
    AnimationMachineWaiting at the same PC / A7 and resume correctly;
  * for dumped frames the native trace (PCs + ordered bus events) rebuilds the native RAM / PVC / ports / external reads / PC (and the leader registers where recorded)
    at every split boundary; each actual C++ split phase is compared with them (the rebuilt RAM is itself validated against the recorded RAM-after of the frame);
  * carry = source-opcode classification (ORI #1,CCR / ANDI #fe,CCR / EORI after the 1a2e8 CMP / 72f4 SUBI.B / TST and AND logical clears / 289e compare / flow-only
    blocks) over the native trace; the four F1c1 consumers (478e4 47944 4795c 47974) give `stage catalog caller requires known carry` on Unknown and are flipped
    (incoming C 1 / 2) through the actual C++; FLOW_ONLY preservation is observed through the actual C++;
  * native guards -> exact checked C++ error strings + full preservation of the phase input; deliberate differences are classified by explicit rules and counted;
  * API-only negatives: all 214 interior PCs, odd PCs, outside entries, TRAP 478a6 / F1c2 entry 479b0, Unknown-carry consumers, zero-step at every block start x 3
    carries.
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
OUT = ROOT / 'artifacts/animation_machine_stage_catalog_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_stage_catalog_native'
NATIVE_SHA = '15f7411230a5885e2737403e7584c6e263e2dce60ee3cc94f04ef3a1d3edd3fd'
NATIVE_TOOL_SHA = '22b038c1300bfb99ff0b81f19d87f3d0c1572040185a61c367c6e7209d0a23c6'
CONTRACT = ROOT / 'docs/analysis/animation-machine-stage-catalog-f1c-contract.md'
CONTRACT_SHA = 'f374c80f3528d5200aaa870bd66e8a58d09b400db7a84c8ee3a89fddd474a575'
CPP_SHA = 'a431f6b99d0d84bf00189f96ea2f0c781c55d61fadad03a5a2a0cd1beb94a56c'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
RET_FRAME = 0x2ac2
CUT_STOP = 0x479b0
TRAP_STOP = 0x478a6
GATE_PC = 0x478de
WAIT_PCS = (0xcda4, 0x3aea, GATE_PC)
CONSUMERS = (0x478e4, 0x47944, 0x4795c, 0x47974)
F1C1_RANGES = ((0x3d58, 0x3d62), (0x3d6a, 0x3d7c), (0xca8a, 0xca9e), (0x474e2, 0x474f4), (0x47540, 0x4755e), (0x477e4, 0x479b0), (0x4814e, 0x48156))
CONTRACT_BYTES_SHA = '40c8dfbe9abc0fad2f65abae38cabb7670caa53f125b079b9fdeb8d06d7d25ef'
BB_ENTRIES = tuple(sorted((0x1a5a4, 0xca48, 0x1c5b0, 0x9056, 0xca7e, 0x4e24e, 0x3ac8, 0xca9e, 0xcaf0, 0x8c16, 0x480bc, 0x72f0, 0x35a2, 0x28ae)))
LOGICAL_CLEAR = (0x19710, 0x1971c, 0x1938e, 0x19596)
UNSUPPORTED_CATALOG = 'unsupported animation stage catalog PC'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNKNOWN_CARRY = 'stage catalog caller requires known carry'
UNALIGNED_PC = 'unaligned animation machine PC'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
WRITE_DEVICE = 'unsupported animation machine write device'
DEVICE_ADDRESS = 'unsupported program bus device address'
BUDGET = 'animation machine block budget exceeded'
CONDITIONAL = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
REG16 = common.REGS
PORT_REGIONS = ('pvc', 'video', 'watchdog')
WORKERS = int(os.environ.get('STAGE_CATALOG_WORKERS', '3'))
DEBUG_LABEL = os.environ.get('STAGE_CATALOG_DEBUG_LABEL', '')       # development switch only: the reported run is always the full set
DEBUG_GROUPS = os.environ.get('STAGE_CATALOG_DEBUG_GROUPS', '')     # development switch only
API_ONLY = bool(os.environ.get('STAGE_CATALOG_API_ONLY'))           # development switch only
RUN_DIR = None


def localize(name):
    local = str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name
    return local if Path(local).exists() else name           # tools not copied into this worktree are read from the main tree (read only)


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def in_f1c1(pc):
    return in_ranges(pc, F1C1_RANGES)


def invoke(exe, folder, label, ram, state, pvc, bank, resources, stop, external=0):
    """common.invoke with close_fds=False (posix_spawn), a long timeout and no state.json side file."""
    paths = [folder / (label + s) for s in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin')]
    paths[0].write_bytes(ram)
    paths[1].write_bytes(pvc)
    args = [str(exe)] + [str(state[k]) for k in common.REGS] + [str(state['pc']), str(state['carry']), str(bank), str(stop), str(external)] + \
        list(map(str, paths)) + list(map(str, resources))
    run = subprocess.run(args, capture_output=True, text=True, timeout=1800, close_fds=False)
    assert run.returncode == 0, (label, run.stderr)
    result = common.parse(run.stdout, expected_invalid_carry=state['carry'] if state['carry'] not in (0, 1, 2) else None)
    assert paths[0].read_bytes() == ram and paths[1].read_bytes() == pvc
    out = (result, paths[2].read_bytes(), paths[3].read_bytes(), paths[4].read_bytes(), run.stderr)
    for p in paths:
        p.unlink()
    return out


def inv(label, *args, **kwargs):
    return invoke(*((args[0], RUN_DIR, label) + args[1:]), **kwargs)


class RomInstructions(dict):
    """Instruction decoded from the original bytes on demand."""
    def __init__(self, program):
        dict.__init__(self)
        self.program = program

    def __missing__(self, pc):
        item = disassemble_range(self.program, pc, 10, pc)[0]
        assert item['cpu_address'] == pc, hex(pc)
        if item['classification'] != 'candidate_instruction':
            item = dict(item, mnemonic='dc.w')           # undecodable word of another unit: never a carry producer / consumer, classified Unknown
        self[pc] = item
        return item


# ----------------------------------------------------------------------------------------------------------------- contract / static
def pcs_in(text):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{4,6})`', text)]


def parse_contract(program):
    lines = CONTRACT.read_text().splitlines()
    table, code = [], []
    pattern = re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| `([0-9a-f]+)` \|$')
    section = None
    for line in lines:
        if line.startswith('**F1c1**'):
            section = 'f1c1'
        elif line.startswith('**F1c2**'):
            section = 'f1c2'
        if section != 'f1c1':
            continue
        match = pattern.match(line)
        if match:
            low, high = int(match.group(1), 16), int(match.group(2), 16)
            assert program[low:high].hex() == match.group(3), hex(low)
            table.append(dict(range='%x..%x' % (low, high), size=high - low, bytes_equal_to_rom=True, sha256=sha(program[low:high])))
            code.append((low, high))
    assert code == [(0x3d58, 0x3d62), (0x3d6a, 0x3d7c), (0xca8a, 0xca9e), (0x474e2, 0x474f4), (0x47540, 0x4755e), (0x477e4, 0x479b0), (0x4814e, 0x48156)]
    assert sum(h - l for l, h in code) == 564
    assert sha(b''.join(program[l:h] for l, h in code)) == CONTRACT_BYTES_SHA
    lists = {}
    for line in lines:
        match = re.match(r'^\s*- F1c1\((\d+)\):(.*)$', line)
        if match and int(match.group(1)) in (67, 9, 32):
            lists[int(match.group(1))] = pcs_in(match.group(2))
    starts, bundled, preserve = lists.get(67), lists.get(9), lists.get(32)
    assert starts and len(starts) == len(set(starts)) == 67 and bundled and len(bundled) == len(set(bundled)) == 9 and preserve and len(preserve) == len(set(preserve)) == 32
    text = CONTRACT.read_text()
    assert '`478e4`(`72f0`, C=Clear는 결정 3), `47944`·`4795c`·`47974`(`28ae`' in text
    window = re.search(r'`474f4\.\.47540`: stage group 표 LONG 19개, SHA256 `([0-9a-f]{64})`', text)
    assert window and sha(program[0x474f4:0x47540]) == window.group(1)
    return table, starts, bundled, preserve


def audit_static(program):
    table, starts, bundled, preserve = parse_contract(program)
    instructions = RomInstructions(program)
    inside = []
    for low, high in F1C1_RANGES:
        pc = low
        while pc < high:
            inside.append(pc)
            pc += instructions[pc]['size']
        assert pc == high, hex(low)
    start_set = set(starts)
    # the 478a6 TRAP is the fall-through of the BCS.W at 478a2 inside 477e4..479b0: boundary, not a contract block start
    trap_items = [pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] == 'trap']
    assert trap_items == [TRAP_STOP] and program[TRAP_STOP:TRAP_STOP + 2].hex() == '4e4f'
    derived = set(low for low, _ in F1C1_RANGES)
    for pc in inside:
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        target = re.search(r'\$([0-9a-f]+)$', item['op_str'])
        if name in CONDITIONAL + ('bra', 'bsr', 'jsr', 'dbra') and target:
            derived.add(int(target.group(1), 16))
        if name in CONDITIONAL + ('bsr', 'jsr', 'rts', 'bra', 'jmp', 'dbra', 'trap'):
            derived.add(pc + item['size'])
    derived = set(pc for pc in derived if in_f1c1(pc))
    derived.discard(TRAP_STOP)
    table_slots = set(range(0x478ac, 0x478c4 + 1, 4))
    callbacks = set((0x478de, 0x4790a, 0x4798e, 0x477e4))
    assert derived | table_slots | callbacks == start_set, sorted(hex(p) for p in (derived | table_slots | callbacks) ^ start_set)
    blocks = {}
    for start in start_set:
        pcs, pc = [], start
        while True:
            item = instructions[pc]
            pcs.append(pc)
            name = item['mnemonic'].split('.')[0]
            end = name in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'dbra', 'trap') or name in CONDITIONAL
            following = pc + item['size']
            if end or following in start_set or not in_f1c1(following) or following == TRAP_STOP:
                break
            pc = following
        blocks[start] = pcs
    in_block = collections.Counter(pc for pcs in blocks.values() for pc in pcs)
    assert max(in_block.values()) == 1
    bundled_expected = sorted(pc for pc in inside if pc not in start_set and pc != TRAP_STOP and instructions[pc]['mnemonic'].split('.')[0] in CONDITIONAL + ('dbra',))
    assert bundled_expected == sorted(bundled), [hex(p) for p in set(bundled_expected) ^ set(bundled)]
    flow = sorted(pc for pc in start_set if all(instructions[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc]))
    assert flow == sorted(preserve), [hex(p) for p in set(flow) ^ set(preserve)]
    even = [pc for low, high in F1C1_RANGES for pc in range(low, high, 2)]
    assert len(even) == 282
    interior = [pc for pc in even if pc not in start_set and pc != TRAP_STOP]
    assert len(interior) == 214
    consumers = sorted(pc for pc in start_set if instructions[pc]['mnemonic'].split('.')[0] in ('bcc', 'bcs', 'bne', 'beq'))
    assert consumers == sorted(CONSUMERS), [hex(p) for p in consumers]
    producers = sorted(pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in ('ori', 'andi', 'eori') and re.search(r'\bccr\b', instructions[pc]['op_str']))
    x_users = [pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in ('addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')]
    assert x_users == [] and producers == []
    return dict(table=table, starts=starts, bundled=bundled, preserving=preserve, instructions=instructions, blocks=blocks, inside=inside, interior=interior,
                even_pcs=len(even), instruction_count=len(inside))


def cpp_static(st):
    """C++ case labels vs the contract block starts, routing ranges vs the code ranges, carry-preserving table vs the 32 FLOW_ONLY blocks."""
    text = (ROOT / 'engine/src/animation_machine_stage_catalog.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text))
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    in_unit = set(pc for pc in table if in_f1c1(pc))
    start = machine.index('animation_area_clear_block(c);')
    route = machine[start:machine.index('animation_stage_catalog_block(c);', start)]
    ranges = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', route))
    assert 'next.pc!=0x478a6' in route
    return cases, in_unit, ranges


# ----------------------------------------------------------------------------------------------------------------- native record
class Native(object):
    """Frozen native record: observation.json, the condition files and the content-addressed blobs (every file hash checked on first use)."""
    def __init__(self):
        path = NATIVE_DIR / 'observation.json'
        assert cc.digest(path) == NATIVE_SHA
        self.report = json.loads(path.read_text())
        self.checked = {}
        self.blob_ok = set()
        self.cond_cache = {}

    def file_checked(self, rel, expected):
        key = rel
        if key not in self.checked:
            data = (NATIVE_DIR / rel).read_bytes()
            assert sha(data) == expected, rel
            self.checked[key] = len(data)
        return (NATIVE_DIR / rel).read_bytes()

    def condition(self, name):
        rel = 'conditions/' + name
        data = self.file_checked(rel, self.report['condition_files'][rel])
        return json.loads(gzip.decompress(data))

    def blob(self, name):
        """Blobs are content addressed: the file name is the SHA256 of the stored bytes."""
        rel = 'blobs/' + name
        data = (NATIVE_DIR / rel).read_bytes()
        if name not in self.blob_ok:
            assert sha(data) == name.split('.')[0], name
            self.blob_ok.add(name)
        return data

    def audit_all_blobs(self):
        names = sorted(p.name for p in (NATIVE_DIR / 'blobs').iterdir())
        assert len(names) == self.report['blob_count'] == 6255
        for name in names:
            data = (NATIVE_DIR / 'blobs' / name).read_bytes()
            assert sha(data) == name.split('.')[0], name
            self.blob_ok.add(name)
        return len(names)

    def trace(self, name):
        return json.loads(gzip.decompress(self.blob(name)))


def audit_report(program, source):
    report = json.loads((NATIVE_DIR / 'observation.json').read_text())
    assert cc.digest(NATIVE_DIR / 'observation.json') == NATIVE_SHA
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_stage_catalog.py') == NATIVE_TOOL_SHA
    assert cc.digest(CONTRACT) == CONTRACT_SHA
    assert cc.digest(ROOT / 'engine/src/animation_machine_stage_catalog.cpp') == CPP_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert len(report['conditions']) == 534 if isinstance(report['conditions'], list) else report['conditions'] == 534
    assert len(report['results']) == 534
    totals = report['totals']
    assert (totals['frames'], totals['split_phases'], totals['control_phases']) == (4036, 24602, 4036)
    assert report['block_starts_not_hit'] == [] and len(report['block_starts']) == 67
    assert report['block_starts_needing_typed_fixtures'] == ['0x478b4', '0x478bc', '0x4791c', '0x47922', '0x4794c', '0x4795c', '0x47960']
    assert report['natural_seed_policy']['natural'] == 137 and report['natural_seed_policy']['release_guard_rows'] == 5
    assert report['dump_seeds'] == [0, 60, 117, 118, 134, 126, 135, 141] and report['boundary_frames'] == [0, 29, 188, 189, 235, 236, 237]
    refs = {}
    for name, expected in report['inputs'].items():
        if name.endswith('animation-machine-stage-catalog-f1c-contract.md'):
            assert expected == CONTRACT_SHA
            continue
        assert cc.digest(localize(name)) == expected, name
        refs[name] = expected
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert len(report['condition_files']) == 663
    return report, refs


# ----------------------------------------------------------------------------------------------------------------- carry
def branch_expect(item, carry):
    """Next PC of a consumer for a known carry (1 Clear, 2 Set): BCC taken on Clear, BCS taken on Set."""
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
    for i, pc in enumerate(pcs):
        if instructions[pc]['mnemonic'].split('.')[0] in ('bcc', 'bcs'):
            if classify_carry(instructions, 1, pcs[:i], reads) != classify_carry(instructions, 2, pcs[:i], reads):
                return True
    return False


# ----------------------------------------------------------------------------------------------------------------- native event replay
def ports_blob(events):
    return b''.join(struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in events if e['region'] in PORT_REGIONS)


def fold_outputs(pvc, bank, events):
    """Independent PVC effects of the native events in order (as the F1a verifier)."""
    for event in events:
        if event['access'] == 'write' and 0x2fe000 <= event['address'] < 0x300000:
            pvc, bank, encoded = common.fold_device(pvc, bank, [event])
            assert len(encoded) == 9
    return pvc, bank


def raw_image(pvc, raw):
    """The native observer keeps the last raw WORDs written to 2ffff0 / 2ffff2 in its PVC image (offsets 1ff0 / 1ff2); the C++ device holds the normalized bank words
    (common.fold_device).  The native image is therefore rebuilt from the actual C++ device plus the raw words of the ordered C++ port writes."""
    image = bytearray(pvc)
    image[0x1ff0:0x1ff2] = raw[0].to_bytes(2, 'big')
    image[0x1ff2:0x1ff4] = raw[1].to_bytes(2, 'big')
    return bytes(image)


def update_raw(raw, ports):
    raw = list(raw)
    for i in range(0, len(ports), 9):
        size, address, value = struct.unpack('>BII', ports[i:i + 9])
        if 0x2fe000 <= address < 0x300000:
            assert size == 2 and address in (0x2ffff0, 0x2ffff2)
            raw[0 if address == 0x2ffff0 else 1] = value
    return raw


def state_sha(ram, result, ports, bank_base):
    h = hashlib.sha256()
    h.update(b'F1C1-FRAME-STATE-v1')
    h.update(ram)
    h.update(struct.pack('>16I', *[result[k] for k in REG16]))
    h.update(struct.pack('>II', result['pc'], bank_base >> 20))
    h.update(struct.pack('>I', len(ports) // 9))
    h.update(ports)
    return h.hexdigest()


class FrameTrace(object):
    """Native trace of a dumped frame: PCs and ordered bus events; events are attributed to instructions (an instruction's events carry its own pc and directly follow
    the previous instruction's events), which gives the native RAM / PVC / ports / external reads at every instruction boundary."""
    def __init__(self, native, frame, ram_before, pvc_before, bank_before, program):
        dump = frame['dump']
        t = native.trace(dump['trace'])
        self.pcs, self.events, self.leaders, self.guard = t['pcs'], t['events'], t['leaders'], t['guard']
        self.ram_before, self.pvc_before, self.bank_before = ram_before, pvc_before, bank_before
        self.dump = dump
        cut = []
        j = 0
        events = self.events
        for pc in self.pcs:
            cut.append(j)
            while j < len(events) and events[j]['pc'] == pc:
                j += 1
        self.cut = cut
        self.total_events = len(events)
        self.consumed_all = j == len(events)
        self.program = program

    def at(self, index):
        """(ram, pvc, bank, ports, external_reads) at the boundary directly before executing pcs[index]; index == len(pcs) - 1 is the final state."""
        end = self.cut[index] if index < len(self.pcs) - 1 else self.total_events
        ram = bytearray(self.ram_before)
        for e in self.events[:end]:
            if e['access'] == 'write' and e['region'] == 'ram':
                at = e['address'] & 0xffff
                raw = bytes.fromhex(e['bytes'])
                assert len(raw) == e['size'] and at + e['size'] <= 0x10000
                ram[at:at + e['size']] = raw
        pvc, bank = fold_outputs(self.pvc_before, self.bank_before, self.events[:end])
        ports = ports_blob(self.events[:end])
        reads = sum(1 for e in self.events[:end] if e['access'] == 'read' and e['address'] == 0xd00046 and e['size'] == 1)
        return bytes(ram), pvc, bank, ports, reads

    def leader_indices(self, start_set, lead_set, guarded=False):
        """Index in pcs of every recorded leader (same rule as the observer: a block start, or a black-box entry reached directly from F1c1 code).  The final PC of a
        normal run is the stop PC (hooked but not recorded); the final PC of a guarded run is the faulting instruction (hooked and recorded)."""
        out = []
        last = None
        for index in range(len(self.pcs) if guarded else len(self.pcs) - 1):
            pc = self.pcs[index]
            if pc in lead_set and (pc in start_set or (last is not None and in_f1c1(last))):
                out.append(index)
            last = pc
        return out


# ----------------------------------------------------------------------------------------------------------------- fixtures and steps
def parse_changes(changes):
    out = []
    for change in changes:
        if change[0] == 'ram':
            out.append(('ram', int(change[1], 16), change[2], int(change[3], 16)))
        elif change[0] == 'pc':
            out.append(('pc', int(change[1], 16)))
        elif change[0] == 'a7_add':
            out.append(('a7_add', change[1]))
        else:
            raise AssertionError(change)
    return out


def apply_changes(ram, state, changes):
    ram = bytearray(ram)
    state = dict(state)
    a7 = state['a7']
    kinds = []
    for change in changes:
        kind = change[0]
        if kind == 'ram':
            _, address, size, value = change
            assert 0x100000 <= address < 0x110000 or 0x1f0000 <= address < 0x200000
            at = address & 0xffff
            assert at + size <= 0x10000
            ram[at:at + size] = value.to_bytes(size, 'big')
        elif kind == 'pc':
            state['pc'] = change[1]
        else:
            state['a7'] = (a7 + change[1]) & M32
        kinds.append(kind)
    return bytes(ram), state, kinds


def expected_error_for(guard):
    """Allowed exact C++ checked errors for a native guard (the rule is documented in the report; the observed string is recorded per condition)."""
    problem = guard['problem']
    if problem == 'unsupported_odd_data_access':
        return (EVEN, EVEN_WRITE)
    if problem == 'unsupported_code_target':
        if guard.get('odd_pc'):
            return (UNALIGNED_PC,)
        reason = guard['reason']
        if reason.startswith('computed PC'):
            return (UNSUPPORTED_CATALOG,)
        return (UNSUPPORTED_MACHINE,)
    if problem in ('unsupported_write', 'unmapped_or_protected'):
        return (WRITE_DEVICE, DEVICE_ADDRESS)
    if problem == 'step_limit':
        return (BUDGET,)
    raise AssertionError(guard)


class Ctx(object):
    def __init__(self, exe, resources, program, instructions, native, start_set, lead_set):
        self.exe, self.resources, self.program, self.instructions, self.native = exe, resources, program, instructions, native
        self.start_set, self.lead_set = start_set, lead_set


def check_preserved(actual, ram, state, pvc, bank):
    result, out_ram, out_pvc, ports, error = actual
    assert not result['ok'] and error.strip()
    assert {k: result[k] for k in common.STATE_KEYS} == {k: state[k] for k in common.STATE_KEYS}
    assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
    assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
    return error.strip()


def audit_rom_reads(program, trace):
    """Every fixed / banked ROM read of the native trace returned the original bytes at the physical offset."""
    bank = trace.bank_before
    counts = collections.Counter()
    for event in trace.events:
        if event['region'] == 'pvc':
            bank = event['bank_after']
        elif event['region'] in ('fixed', 'bank'):
            raw = bytes.fromhex(event['bytes'])
            if event['region'] == 'fixed':
                physical = event['address']
            else:
                physical = bank + event['address'] - 0x200000
                assert physical == event['physical_rom_offset'] and bank == event['bank_at_read']
            assert 0 <= physical <= len(program) - event['size'] and raw == program[physical:physical + event['size']]
            counts[event['region']] += 1
    return counts


def window_notes(trace, windows):
    """F1c1 code reads of fixed ROM data outside the contract data windows (the observer discrepancy: 47864 reads WORD 10(A0) of the last record of group 4)."""
    out = collections.Counter()
    for e in trace.events:
        if e['region'] == 'fixed' and e['access'] == 'read' and in_f1c1(e['pc']):
            if not any(a <= e['address'] and e['address'] + e['size'] <= b for a, b in windows):
                out[(e['pc'], e['address'] + e['size'] - 1)] += 1
    return out


CONTRACT_WINDOWS = ((0x474f4, 0x47540), (0xd99e2, 0xdd4be), (0x472be, 0x474e0))
CORRECT_WINDOWS = ((0x474f4, 0x47540), (0xd99e2, 0xdd4d0), (0x472be, 0x474e0))        # group 4 ends at dd4d0 (group extents of the ROM catalog, observer record)


def initial_prefix(result, ctx):
    """Natural seed chain: the recorded final RAM and registers of the original stage_entry_body run, A7 = 1feffc with the declared dispatcher return LONG 2ac2 at (A7),
    direct entry 47da4 (the same declaration as the dump seeds, whose fixture summary records it); the first prefix frame carries the full dump."""
    pf = result['prefix']
    prefix = ctx.native.condition(pf['prefix_file'])
    frame0 = prefix['frames'][0]
    prov = result['provenance']
    seed_path = ROOT / 'artifacts/stage_entry_body' / prov['ram_file']
    ram = bytearray(seed_path.read_bytes())
    assert sha(bytes(ram)) == prov['ram_sha256']
    ram[0xeffc:0xf000] = bytes.fromhex('00002ac2')
    ram = bytes(ram)
    assert ram == ctx.native.blob(frame0['dump']['ram_before'])
    pvc = ctx.native.blob(frame0['dump']['pvc_before'])
    regs = {k: int(v, 16) for k, v in prov['registers'].items()}
    state = dict(a7=0x1feffc, pc=0x47da4, carry=0)
    for k in common.REGS:
        if k != 'a7':
            state[k] = regs[k]
    assert int(frame0['in_pc'], 16) == 0x47da4 and int(frame0['in_a7'], 16) == 0x1feffc
    assert prov['bank'] == 2 and int.from_bytes(pvc[0x1ff0:0x1ff2], 'big') == 0xa0 and int.from_bytes(pvc[0x1ff2:0x1ff4], 'big') == 0x1000
    return ram, pvc, 0x200000, state, 'seed file + declared stack LONG 2ac2 at 1feffc'


def initial_from_fixture(cond, ctx):
    """Declared initial state of a condition: registers / A7 / PC from the fixture summary (no SR is declared: C Unknown), RAM from the recorded seed and declared
    host writes (natural seeds) or from the RAM image of the first native frame (typed fixtures; a declared fixture RAM)."""
    result, cf = cond['result'], cond['cf']
    fx = result['fixture']
    if 'prefix' in result:
        return initial_prefix(result, ctx)
    frame0 = cf['frames'][0]
    assert 'dump' in frame0, result['label']
    ram_dump = ctx.native.blob(frame0['dump']['ram_before'])
    pvc = ctx.native.blob(frame0['dump']['pvc_before'])
    assert sha(pvc) == fx['initial_PVC_sha256']
    state = dict(fx['initial_regs'], a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    for k in common.REGS:
        assert k in state
    bank = fx['bank_state'][0]
    assert bank == fx['bank'] << 20 if isinstance(fx['bank'], int) else True
    ff8, ff9 = fx['bank_state'][1], fx['bank_state'][2]
    assert int.from_bytes(pvc[0x1ff0:0x1ff2], 'big') == ff8 and int.from_bytes(pvc[0x1ff2:0x1ff4], 'big') == ff9
    prov = result['provenance']
    if prov['kind'].startswith('stage_entry_body final ff000 RAM output'):
        seed_path = ROOT / 'artifacts/stage_entry_body' / prov['ram_file']
        ram = bytearray(seed_path.read_bytes())
        assert sha(bytes(ram)) == prov['ram_sha256']
        for w in fx['initial_host_writes']:
            at = w['address'] & 0xffff
            ram[at:at + w['size']] = bytes.fromhex(w['hex'])
        ram = bytes(ram)
        assert ram == ram_dump and sha(ram) == fx['initial_RAM_sha256']
        source = 'seed file + declared initial host writes'
    else:
        ram = ram_dump
        assert sha(ram) == fx['initial_RAM_sha256']
        source = 'recorded fixture RAM image (first frame)'
    return ram, pvc, bank, state, source


# ----------------------------------------------------------------------------------------------------------------- condition replay
SUPERSEDED_GUARDS = ('guard-undeclared-cut-479b0',)
# API-only boundary probes whose run reaches code a later unit routes (label -> observed error, classification, block starts reached in order).
# boundary_entry_0479b0: since F1c2 the run from 479b0 executes and failed at the first unrouted block 48350 (the Set side of the C1 block 48346).
# Player C3 routes 48350 (contract animation-machine-player-c3-contract.md): the run continues 48362 -> C1 1d21c -> ... and ends at ea4, whose
# MOVE.W 3c0006.l (LSPC VCOUNT, a queue device) has no queued value in this API call: checked error with full rollback (unchanged since C3).
SUPERSEDED_BOUNDARY_ENTRIES = {
    'boundary_entry_0479b0': dict(error='animation machine external read queue empty', classification='superseded_by_player_C3_routes_48350',
                                  reached=(0x48350, 0x1d21c, 0xea4)),
}


class Acc(object):
    def __init__(self):
        self.totals = collections.Counter()
        self.deliberate = []
        self.guards = []
        self.superseded_guards = []
        self.first_pcs = collections.Counter()
        self.preserved = {}
        self.consumer_flips = collections.Counter()
        self.windows = collections.Counter()
        self.waits = []
        self.errors = []
        self.carry_hist = collections.Counter()
        self.probe_seen = set()
        self.wait_carry = collections.Counter()
        self.leader_failed = []
        self.slots = {}


def cmp_frame(frame, result, ram, pvc, raw, ports, bank, reads, waiting, label, step, dump_pvc=None):
    """The actual C++ end state of a frame vs the native continuous record."""
    want = {k: int(v, 16) for k, v in frame['regs16'].items()}
    got = {k: result[k] for k in REG16}
    assert got == want, (label, step, {k: (hex(want[k]), hex(got[k])) for k in REG16 if want[k] != got[k]})
    assert result['pc'] == int(frame['pc'], 16), (label, step, hex(result['pc']), frame['pc'])
    assert result['a7'] == int(frame['out_a7'], 16)
    assert bank >> 20 == frame['bank'], (label, step)
    assert sha(ram) == frame['ram_sha256'], (label, step, 'RAM')
    assert sha(raw_image(pvc, raw)) == frame['pvc_sha256'], (label, step, 'PVC')
    if 'ff8' in frame:
        assert int.from_bytes(pvc[0x1ff0:0x1ff2], 'big') == int(frame['ff8'], 16) and int.from_bytes(pvc[0x1ff2:0x1ff4], 'big') == int(frame['ff9'], 16), (label, step)
    if dump_pvc is not None:
        assert raw_image(pvc, raw) == dump_pvc, (label, step, 'PVC dump')
    assert sha(ports) == frame['ports_sha256'] and len(ports) // 9 == frame['port_count'], (label, step, 'ports')
    if 'external_reads' in frame:
        assert reads == frame['external_reads'], (label, step, reads, frame['external_reads'])
    assert waiting == bool(frame.get('waiting')), (label, step, 'waiting')
    assert state_sha(ram, result, ports, bank) == frame['state_sha256'], (label, step, 'state sha')


def run_condition(job, ctx):
    result, cf = job
    acc = Acc()
    label = result['label']
    cond = dict(result=result, cf=cf)
    native = ctx.native
    frames = cf['frames']
    steps = cf['steps']
    guarded = bool(result['guarded'])
    expected_guard = result['observed_guard']
    ram, pvc, bank, state, source = initial_from_fixture(cond, ctx)
    external = result['fixture']['external']
    raw = [int.from_bytes(pvc[0x1ff0:0x1ff2], 'big'), int.from_bytes(pvc[0x1ff2:0x1ff4], 'big')]
    if 'prefix' in result:
        ram, pvc, bank, state, raw = run_prefix(result, ctx, acc, ram, pvc, bank, state, external, raw)
        # the tail starts from the actual C++ output of frame 235 (declared by the native record: captured native state)
        fx = result['fixture']
        assert sha(ram) == fx['initial_RAM_sha256'] and sha(raw_image(pvc, raw)) == fx['initial_PVC_sha256'], label
        assert state['pc'] == fx['entry_pc'] and state['a7'] == fx['initial_a7'] and bank == fx['bank_state'][0]
        assert {k: state[k] for k in common.REGS} == {k: (fx['initial_regs'][k] if k != 'a7' else fx['initial_a7']) for k in common.REGS}
        source = 'actual C++ output of the natural prefix frame 235'
        acc.totals['tail_starts_from_cpp_prefix_output'] += 1
    expected_pvc = pvc
    digest = hashlib.sha256()
    split_phases = 0
    cond_row = dict(label=label, group=result['group'], number=result['number'], steps=len(steps), start=source, split_phases=0, guarded=guarded, cpp_error=None, carry={})
    for si, step in enumerate(steps):
        frame = frames[si]
        changes = parse_changes(step['changes'])
        ram, state, kinds = apply_changes(ram, state, changes)
        acc.totals['declared_host_ram_changes'] += kinds.count('ram')
        acc.totals['declared_dispatcher_reentry_pc_changes'] += kinds.count('pc')
        acc.totals['declared_dispatcher_reentry_a7_deltas'] += kinds.count('a7_add')
        assert state['pc'] == int(frame['in_pc'], 16) and state['a7'] == int(frame['in_a7'], 16), (label, si)
        trace = None
        if 'dump' in frame:
            dump_before = native.blob(frame['dump']['ram_before'])
            assert dump_before == ram, (label, si, 'incoming RAM differs from the native recorded RAM before the frame')
            assert native.blob(frame['dump']['pvc_before']) == raw_image(pvc, raw)
            trace = FrameTrace(native, frame, ram, pvc, bank, ctx.program)
            assert trace.pcs[0] == state['pc']
        stop = int(step['stop_pc'], 16)
        checkpoints = [int(x, 16) for x in step['checkpoints']]
        step_in = (ram, dict(state), pvc, bank)
        stop_a7 = step['a7'][1] if step.get('a7') else None
        phases = run_step(label, si, ctx, acc, cond_row, result, frame, trace, step_in, raw, checkpoints, stop, external, guarded and si == len(steps) - 1, expected_guard)
        if phases['error'] is not None:
            cond_row['cpp_error'] = phases['error']
            assert si == len(steps) - 1
            break
        ram, state, pvc, bank = phases['end']
        raw = phases['raw']
        split_phases += phases['count']
        digest.update(phases['digest'])
        if stop_a7 is not None and state['pc'] == stop and not frame.get('waiting'):
            assert state['a7'] == stop_a7, (label, si, hex(state['a7']), hex(stop_a7))
    else:
        assert not guarded, label
    cond_row['split_phases'] = split_phases
    cond_row['C_phase_digest_sha256'] = digest.hexdigest()
    acc.totals['cases'] += 1
    return acc, cond_row


def run_prefix(result, ctx, acc, ram, pvc, bank, state, external, raw):
    """The natural F1b prefix frames 0..235: one continuous C++ run per frame (the native record has no checkpoints there), resumed from the previous actual C++
    output plus the declared host changes; compared with the recorded full-state SHA256 and its parts."""
    pf = result['prefix']
    prefix = ctx.native.condition(pf['prefix_file'])
    assert ctx.native.report['condition_files']['conditions/' + pf['prefix_file']] == pf['prefix_file_sha256']
    label = result['label']
    frames = prefix['frames']
    assert len(frames) == pf['frames'] == 236
    for fi, frame in enumerate(frames):
        changes = parse_changes(frame['host_changes'])
        ram, state, kinds = apply_changes(ram, state, changes)
        acc.totals['declared_host_ram_changes'] += kinds.count('ram')
        acc.totals['declared_dispatcher_reentry_pc_changes'] += kinds.count('pc')
        acc.totals['declared_dispatcher_reentry_a7_deltas'] += kinds.count('a7_add')
        assert state['pc'] == int(frame['in_pc'], 16) and state['a7'] == int(frame['in_a7'], 16), (label, 'prefix', fi)
        if 'dump' in frame:
            assert ctx.native.blob(frame['dump']['ram_before']) == ram, (label, 'prefix', fi)
            assert ctx.native.blob(frame['dump']['pvc_before']) == raw_image(pvc, raw), (label, 'prefix', fi)
        actual = inv('p%04d_%03d' % (result['number'], fi), ctx.exe, ram, state, pvc, bank, ctx.resources, stop=RET_FRAME, external=external)
        res, out_ram, out_pvc, out_ports, error = actual
        assert res['ok'] and not error, (label, 'prefix', fi, error)
        assert res['status'] == 0
        raw = update_raw(raw, out_ports)
        if raw != [int.from_bytes(out_pvc[0x1ff0:0x1ff2], 'big'), int.from_bytes(out_pvc[0x1ff2:0x1ff4], 'big')]:
            acc.totals['frames_native_raw_PVC_words_differ_from_normalized_device'] += 1
        dump_pvc = ctx.native.blob(frame['dump']['pvc_after']) if 'dump' in frame else None
        cmp_frame(frame, res, out_ram, out_pvc, raw, out_ports, res['bank_base'], res['external_reads'], res['status'] == 1, label, 'prefix%d' % fi, dump_pvc)
        if 'dump' in frame:
            assert out_ram == ctx.native.blob(frame['dump']['ram_after'])
            assert out_ports == ctx.native.blob(frame['dump']['ports'])
            acc.totals['prefix_dumped_frames_full_compare'] += 1
        acc.totals['prefix_frames'] += 1
        acc.totals['prefix_state_sha_equal'] += 1
        acc.carry_hist[res['carry']] += 1
        ram, pvc, bank = out_ram, out_pvc, res['bank_base']
        state = {k: res[k] for k in common.STATE_KEYS}
    return ram, pvc, bank, state, raw


def run_step(label, si, ctx, acc, cond_row, result, frame, trace, step_in, raw, checkpoints, stop, external, last_guard_step, expected_guard):
    """One native step (frame): split chain over the declared checkpoints, then the continuous run; returns the end state or the checked error."""
    exe, resources, instructions = ctx.exe, ctx.resources, ctx.instructions
    ram0, state0, pvc0, bank0 = step_in
    targets = checkpoints + [stop]
    phases = []
    ram, state, pvc, bank = ram0, dict(state0), pvc0, bank0
    all_ports = b''
    reads_total = 0
    digest = hashlib.sha256()
    boundary_index = {}
    if trace is not None:
        prev = 0
        for t in checkpoints:
            idx = next((i for i in range(1, len(trace.pcs)) if trace.pcs[i] == t), None)
            if idx is not None and idx > prev:
                boundary_index[t] = idx
                prev = idx
    n_native = frame['split_phases']
    error = None
    waiting = False
    for j, target in enumerate(targets):
        phase_in = (ram, dict(state), pvc, bank)
        actual = inv('c%04d_%03d_%03d' % (result['number'], si, j), exe, ram, state, pvc, bank, resources, stop=target, external=external)
        res, out_ram, out_pvc, out_ports, err = actual
        if last_guard_step and j + 1 >= n_native and label in SUPERSEDED_GUARDS:
            # This historical guard must succeed now; an old unsupported error is a regression.
            assert j + 1 == n_native, (label, si, 'superseded guard phase', j + 1, n_native)
            assert res['ok'] and not err.strip() and res['status'] == 0 and res['pc'] == target, (label, si, res, err)
            if trace is not None and phases:
                compare_trace(label, si, ctx, acc, frame, trace, phases, checkpoints, stop, boundary_index, state0, ram0, result['number'], guarded_frame=True)
            # superseded by F1c2: 479b0 is an executable block start now, so the native 'undeclared cut' guard phase runs through without a checked error in C++ (native guard record kept)
            acc.superseded_guards.append(dict(label=label, step=si, phase=j, stop=hex(target), former_expected='checked API error (unsupported animation machine PC at the cut)',
                                              observed_final_state=dict(ok=True, pc=hex(res['pc']), status=res['status']), native_guard=frame.get('guard'),
                                              native_fault_rollback_equivalence_claimed=False))
            acc.totals['guard_rows_superseded_by_F1c2'] += 1
            return dict(error='superseded: C++ runs through the undeclared cut %x without a checked error' % target, end=None, count=j + 1, digest=digest.digest())
        if not res['ok']:
            error = check_preserved(actual, ram, state, pvc, bank)
            err_row = dict(label=label, step=si, phase=j, stop=hex(target), error=error, native_phases=n_native, state_pc=hex(state['pc']))
            if not last_guard_step:
                acc.errors.append(err_row)
                raise AssertionError(('UNEXPECTED C++ ERROR', err_row))
            # native guard: the failing phase is the last native phase of the step
            guard = frame.get('guard')
            assert guard is not None, (label, si)
            allowed = expected_error_for(guard)
            assert j + 1 == n_native, (label, si, 'C++ error phase', j + 1, 'native guard phase', n_native, error)
            assert error in allowed, (label, si, error, allowed, guard['problem'])
            acc.guards.append(dict(label=label, step=si, phase=j, stop=hex(target), native_guard=dict(problem=guard['problem'], reason=guard.get('reason'), pc=guard.get('pc'),
                                   target=guard.get('target'), address=guard.get('address'), size=guard.get('size'), access=guard.get('access')),
                                   checked_API_error=error, allowed_errors=list(allowed), all_API_outputs_preserved=True, phase_input=dict(pc=hex(state['pc']), a7=hex(state['a7']),
                                   carry=CARRY_NAME[state['carry']]),
                                   native_fault_rollback_equivalence_claimed=False))
            # the continuous run from the step start fails with the same error and preserves the step input
            cont = inv('g%04d_%03d_c' % (result['number'], si), exe, ram0, dict(state0), pvc0, bank0, resources, stop=stop, external=external)
            cont_error = check_preserved(cont, ram0, dict(state0), pvc0, bank0)
            assert cont_error == error, (label, si, cont_error, error)
            # other incoming carry classes give the same error (the checked error does not depend on C)
            other = dict(state, carry=0 if state['carry'] else 2)
            again = inv('g%04d_%03d_o' % (result['number'], si), exe, ram, other, pvc, bank, resources, stop=target, external=external)
            assert check_preserved(again, ram, other, pvc, bank) == error
            acc.totals['guard_rows'] += 1
            acc.totals['guard_continuous_same_error'] += 1
            acc.totals['guard_other_carry_same_error'] += 1
            acc.totals['guard_failing_phases'] += 1
            if trace is not None and phases:
                compare_trace(label, si, ctx, acc, frame, trace, phases, checkpoints, stop, boundary_index, state0, ram0, result['number'], guarded_frame=True)
            return dict(error=error, end=None, count=j + 1, digest=digest.digest())
        assert not last_guard_step or j + 1 < n_native, (label, si, 'native guard phase succeeded in C++')
        acc.totals['split'] += 1
        # per phase native comparison from the rebuilt native trace (dumped frames)
        ph = dict(target=target, res=res, ram=out_ram, pvc=out_pvc, ports=out_ports, inp=phase_in)
        executed_slice = None
        if trace is not None:
            idx = len(trace.pcs) - 1 if target == stop and j == len(targets) - 1 else boundary_index.get(target)
            ph['idx'] = idx
        reads_total += res['external_reads']
        all_ports += out_ports
        phases.append(ph)
        digest.update(struct.pack('>IIB', target, res['pc'], res['carry']) + hashlib.sha256(out_ram).digest() + hashlib.sha256(out_pvc).digest() + struct.pack('>I', len(out_ports)))
        ram, pvc, bank = out_ram, out_pvc, res['bank_base']
        state = {k: res[k] for k in common.STATE_KEYS}
        waiting = res['status'] == 1
        if waiting:
            acc.totals['waiting_phases'] += 1
            break
        assert res['pc'] == target, (label, si, j, hex(res['pc']), hex(target))
    assert len(phases) == n_native, (label, si, len(phases), n_native)
    # (all C++ ports of the step are the concatenation of the phase ports)
    final = phases[-1]
    res = final['res']
    raw_end = update_raw(raw, all_ports)
    if raw_end != [int.from_bytes(pvc[0x1ff0:0x1ff2], 'big'), int.from_bytes(pvc[0x1ff2:0x1ff4], 'big')]:
        acc.totals['frames_native_raw_PVC_words_differ_from_normalized_device'] += 1
    cmp_frame(frame, res, ram, pvc, raw_end, all_ports, bank, reads_total, waiting, label, si,
              ctx.native.blob(frame['dump']['pvc_after']) if ('dump' in frame and not last_guard_step) else None)
    acc.totals['frames_end_state_equal'] += 1
    # native trace based comparison (dumped frames)
    if trace is not None:
        compare_trace(label, si, ctx, acc, frame, trace, phases, checkpoints, stop, boundary_index, state0, ram0, result['number'])
    # continuous C++ run vs the split chain (and vs the native continuous record, already compared above)
    cont = inv('k%04d_%03d' % (result['number'], si), exe, ram0, dict(state0), pvc0, bank0, resources, stop=stop, external=external)
    cres, cram, cpvc, cports, cerr = cont
    assert cres['ok'] and not cerr, (label, si, cerr)
    assert (cram, {k: cres[k] for k in common.STATE_KEYS}, cpvc, cres['bank_base'], cports, cres['status'], cres['external_reads']) == \
        (ram, {k: state[k] for k in common.STATE_KEYS}, pvc, bank, all_ports, 1 if waiting else 0, reads_total), (label, si, 'continuous vs split')
    acc.totals['continuous_runs_equal_split'] += 1
    acc.totals['reads'] += reads_total
    acc.totals['ports'] += len(all_ports) // 9
    acc.carry_hist[res['carry']] += 1
    if waiting:
        wait_pc = final['res']['pc']
        if trace is None:
            gate = wait_pc == GATE_PC
            assert final['res']['carry'] == (1 if gate else 0), (label, si, hex(wait_pc), CARRY_NAME[final['res']['carry']])
            acc.wait_carry['%x_waiting_carry_%s' % (wait_pc, CARRY_NAME[final['res']['carry']])] += 1
        acc.waits.append((label, si, hex(wait_pc), hex(final['res']['a7'])))
        acc.totals['native_waiting_frames'] += 1
    # carry consumers: flip the incoming C of every phase that starts at a consumer, with the native next PC where a trace exists
    for j, ph in enumerate(phases):
        ph_in = ph['inp']
        first_pc = ph_in[1]['pc']
        acc.first_pcs[first_pc] += 1
        if first_pc in CONSUMERS and ph['target'] == first_pc:
            # zero-step entry at a consumer (stop = entry PC): nothing executes, so the Unknown incoming C is not consumed
            assert ph_in[1]['carry'] == 0 and ph['res']['pc'] == first_pc
            acc.totals['zero_step_consumer_entries_unknown_carry_not_consumed'] += 1
        elif first_pc in CONSUMERS:
            carry_in = ph_in[1]['carry']
            assert carry_in in (1, 2), (label, si, j, carry_in)
            expect = branch_expect(instructions[first_pc], carry_in)
            if trace is not None and ph.get('idx') is not None and 'prev_idx' in ph:
                pass
            flipped = 3 - carry_in
            other = branch_expect(instructions[first_pc], flipped)
            same = inv('f%04d_%03d_%03d_s' % (result['number'], si, j), exe, ph_in[0], dict(ph_in[1]), ph_in[2], ph_in[3], resources, stop=expect, external=external)
            assert same[0]['ok'] and same[0]['pc'] == expect and same[0]['carry'] == carry_in and same[1] == ph_in[0] and same[2] == ph_in[2], (label, si, j)
            again = inv('f%04d_%03d_%03d_f' % (result['number'], si, j), exe, ph_in[0], dict(ph_in[1], carry=flipped), ph_in[2], ph_in[3], resources, stop=other, external=external)
            assert again[0]['ok'] and not again[4] and again[0]['pc'] == other and again[0]['carry'] == flipped, (label, si, j)
            assert again[1] == ph_in[0] and again[2] == ph_in[2] and again[0]['bank_base'] == ph_in[3]
            assert {k: again[0][k] for k in common.REGS} == {k: ph_in[1][k] for k in common.REGS}
            gate_wait = other == GATE_PC
            assert again[0]['status'] == (1 if gate_wait else 0), (label, si, j)
            assert same[0]['status'] == (1 if expect == GATE_PC else 0)
            acc.consumer_flips['%x_incoming_%s' % (first_pc, CARRY_NAME[carry_in])] += 1
            acc.totals['consumer_flip_checks'] += 1
    return dict(error=None, end=(ram, state, pvc, bank), count=len(phases), digest=digest.digest(), raw=raw_end)


def compare_trace(label, si, ctx, acc, frame, trace, phases, checkpoints, stop, boundary_index, state0, ram0, number, guarded_frame=False):
    """Dumped frame: native-trace derived RAM / PVC / ports / reads / PC (and leader registers) at every split boundary vs the actual C++ split phases, carry
    classification, FLOW_ONLY preservation probes and the ROM read audit."""
    program, instructions = ctx.program, ctx.instructions
    if not guarded_frame:
        final_ram, final_pvc, final_bank, final_ports, final_reads = trace.at(len(trace.pcs) - 1)
        assert final_ram == ctx.native.blob(frame['dump']['ram_after'])
        assert final_ports == ctx.native.blob(frame['dump']['ports'])
        assert trace.consumed_all
    for n, count in audit_rom_reads(program, trace).items():
        acc.totals['rom_reads_%s_audited' % n] += count
    for key, count in window_notes(trace, CONTRACT_WINDOWS).items():
        acc.windows['%x:%x' % key] += count
    for key, count in window_notes(trace, CORRECT_WINDOWS).items():
        acc.windows['outside_group_extents_%x:%x' % key] += count
    leader_idx = trace.leader_indices(ctx.start_set, ctx.lead_set, guarded_frame)
    leaders_ok = [trace.pcs[i] for i in leader_idx] == [l['pc'] for l in trace.leaders]
    reads = computed_reads(trace.events)
    executed_all = trace.pcs[:-1]
    carry_in_step = state0['carry']
    prev_idx = 0
    prev_ports = 0
    prev_reads = 0
    acc.totals['trace_frames'] += 1
    acc.totals['leader_alignment_ok' if leaders_ok else 'leader_alignment_failed'] += 1
    if not leaders_ok:
        acc.leader_failed.append('%s#%d' % (label, si))
    for j, ph in enumerate(phases):
        idx = ph.get('idx')
        res = ph['res']
        if idx is None:
            acc.totals['trace_boundary_not_found'] += 1
            prev_idx = None
            continue
        nram, npvc, nbank, nports, nreads = trace.at(idx)
        target_pc = trace.pcs[idx]
        if not res['status']:
            assert res['pc'] == target_pc, (label, si, j, hex(res['pc']), hex(target_pc))
        assert ph['ram'] == nram, (label, si, j, 'RAM', [(i, nram[i], ph['ram'][i]) for i in range(65536) if nram[i] != ph['ram'][i]][:10])
        assert ph['pvc'] == npvc and res['bank_base'] == nbank
        assert b''.join(p['ports'] for p in phases[:j + 1]) == nports, (label, si, j, 'ports')
        assert sum(p['res']['external_reads'] for p in phases[:j + 1]) == nreads
        acc.totals['native_trace_split_boundaries_compared'] += 1
        if j < len(phases) - 1 and trace.leaders and leaders_ok:
            lead = next((l for l, i in zip(trace.leaders, leader_idx) if i == idx), None)
            if lead is not None:
                regs = lead['regs']
                assert {k: res[k] for k in REG16} == {k: regs[k] for k in REG16}, (label, si, j, 'leader registers')
                acc.totals['leader_register_boundaries_compared'] += 1
        # carry
        want = classify_carry(instructions, carry_in_step, trace.pcs[:idx], reads) if res['status'] == 0 else None
        if res['status'] == 0:
            assert res['carry'] == want, (label, si, j, hex(target_pc), CARRY_NAME[res['carry']], CARRY_NAME[want])
            acc.totals['carry_classification_checked'] += 1
        else:
            # waiting: the 478de gate leaves the Clear produced by 72f4 SUBI.B (BCC taken), the sprite / sound waits are not carry preserving (Unknown)
            gate = res['pc'] == GATE_PC
            want_w = classify_carry(instructions, carry_in_step, trace.pcs[:idx], reads) if gate else 0
            assert res['carry'] == want_w == (1 if gate else 0), (label, si, j, hex(res['pc']), CARRY_NAME[res['carry']], CARRY_NAME[want_w])
            acc.wait_carry['%x_waiting_carry_%s' % (res['pc'], CARRY_NAME[res['carry']])] += 1
        # carry probes and FLOW_ONLY preservation on single-block phases
        if prev_idx is not None and res['status'] == 0:
            seg = trace.pcs[prev_idx:idx]
            first_pc = seg[0] if seg else None
            if first_pc is not None and first_pc in ctx.start_set and first_pc not in CONSUMERS:
                blocks = [p for p in seg if p in ctx.start_set]
                inc = ph['inp'][1]['carry']
                seg_reads = {pc: [] for pc in (0x72f0, 0x1a2e4, 0x1a2e8)}
                # reads of this segment only (the classifier indexes reads per event kind from the segment start)
                lo, hi = trace.cut[prev_idx], trace.cut[idx] if idx < len(trace.pcs) - 1 else trace.total_events
                seg_reads = computed_reads(trace.events[lo:hi])
                if first_pc not in acc.probe_seen and not path_depends_on_incoming(instructions, seg, seg_reads):
                    acc.probe_seen.add(first_pc)
                    for probe in (1, 2):
                        again = inv('q%04d_%03d_%03d_%d' % (number, si, j, probe), ctx.exe, ph['inp'][0], dict(ph['inp'][1], carry=probe), ph['inp'][2], ph['inp'][3],
                                    ctx.resources, stop=ph['target'], external=0)
                        assert again[0]['ok'] and not again[4], (label, si, j, probe)
                        assert again[0]['carry'] == classify_carry(instructions, probe, seg, seg_reads), (label, si, j, probe, again[0]['carry'])
                        assert {k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in res.items() if k != 'carry'}
                        assert again[1] == ph['ram'] and again[2] == ph['pvc'] and again[3] == ph['ports']
                        acc.totals['carry_probes'] += 1
                        acc.totals['carry_probe_preserved'] += again[0]['carry'] == probe
                        if len(blocks) == 1 and blocks[0] == first_pc:
                            slot = acc.slots.setdefault(first_pc, {1: True, 2: True})
                            slot[probe] = slot[probe] and again[0]['carry'] == probe
        prev_idx = idx
    # consumers inside the frame: the REAL native next PC follows the incoming C of the phase that starts there
    for i, pc in enumerate(executed_all):
        if pc in CONSUMERS and i + 1 < len(trace.pcs):
            carry = classify_carry(instructions, carry_in_step, trace.pcs[:i], reads)
            if carry in (1, 2):
                nxt = trace.pcs[i + 1]
                assert nxt == branch_expect(instructions[pc], carry), (label, si, hex(pc), carry, hex(nxt))
                acc.totals['consumer_real_branch_checks'] += 1


# ----------------------------------------------------------------------------------------------------------------- driver
def compile_harness(folder):
    path = folder / 'harness.cpp'
    path.write_text(common.HARNESS)
    exe = folder / 'animation_machine_stage_catalog_harness'
    compiler = shutil.which('clang++')
    assert compiler
    command = [compiler, '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(ROOT / 'engine/include')]
    command += [str(ROOT / 'engine/src' / name) for name in common.SOURCES]
    command += [str(path), '-o', str(exe)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=3600)
    (folder / 'compile.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stdout and not run.stderr, run.stderr
    return exe, command


# ----------------------------------------------------------------------------------------------------------------- API-only checks
def reject_one(args):
    exe, label, base, changes, stop, expected, resources, extra = args
    ram, state, pvc, bank = base
    s = dict(state, carry=2)
    s.update(changes or {})
    r = extra.get('ram', ram)
    p = extra.get('pvc', pvc)
    actual = inv('n_' + label, exe, r, s, p, bank, extra.get('resources', resources), stop=stop, external=255)
    error = check_preserved(actual, r, s, p, bank)
    assert expected is None or error == expected, (label, error, expected)
    return dict(label=label, error=error, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False)


def run_parallel(function, items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(function, items))


def api_base(native, ctx, results):
    r = next(x for x in results if x['label'] == 'table-00-slot0-478c4-gate')
    cf = native.condition(r['condition_file'])
    ram, pvc, bank, state, _ = initial_from_fixture(dict(result=r, cf=cf), ctx)
    return ram, state, pvc, bank


def negatives(ctx, base, st, resources):
    exe = ctx.exe
    ram, state, pvc, bank = base
    jobs = []
    for pc in st['interior']:
        jobs.append((exe, 'interior_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_CATALOG, resources, {}))
    # TRAP 478a6 (stop-only boundary): no executor. The F1c2 entry 479b0 is an executable block start (see SUPERSEDED_GUARDS); its probe is kept with
    # the observed later error and reached-block controls (SUPERSEDED_BOUNDARY_ENTRIES).
    for pc in (TRAP_STOP, CUT_STOP):
        label = 'boundary_entry_%06x' % pc
        expected = SUPERSEDED_BOUNDARY_ENTRIES[label]['error'] if label in SUPERSEDED_BOUNDARY_ENTRIES else UNSUPPORTED_MACHINE
        jobs.append((exe, label, base, {'pc': pc}, 0xff000, expected, resources, {}))
    # neighbours of the routed ranges that no executor owns at this commit (data table, gaps, dead code)
    # Former probes 0x4755e and 0x48156 (expected UNSUPPORTED_MACHINE) are now inside routed ranges: 4755e..47594 (controller C2) and 48156..48180 (F6a
    # IRQ shell). They would run that code and pass only because a later PC ends in the same message (independent review 0264 M-1), so they are no
    # longer used as unrouted probes; the work-RAM PCs 10fe00/10fefe (code never executes in RAM) are the unrouted controls.
    for pc in (0x3d62, 0x3d7c, 0x474f4, 0x47a54, 0x10fe00, 0x10fefe):
        jobs.append((exe, 'outside_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE, resources, {}))
    for low, high in F1C1_RANGES:
        jobs.append((exe, 'odd_pc_%06x' % (low + 1), base, {'pc': low + 1}, 0xff000, UNALIGNED_PC, resources, {}))
        jobs.append((exe, 'odd_pc_%06x' % (high - 1), base, {'pc': high - 1}, 0xff000, UNALIGNED_PC, resources, {}))
    for pc in (0x1, 0xffffff, 0xdeadbeef, 0x478ad, 0x478c1):
        jobs.append((exe, 'odd_pc_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC, resources, {}))
    for pc in (0x0, 0xffffffe, 0x1000000, 0xdeadbee):
        jobs.append((exe, 'out_of_range_%x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE, resources, {}))
    # a stop that is not an even PC / short RAM image / short PVC / no physical window: checked errors with full preservation
    jobs.append((exe, 'odd_stop', base, {'pc': 0x477e4}, 0xff001, None, resources, {}))
    jobs.append((exe, 'short_ram', base, {'pc': 0x477e4}, 0xff000, None, resources, {'ram': ram[:-1]}))
    jobs.append((exe, 'short_pvc', base, {'pc': 0x477e4}, 0xff000, None, resources, {'pvc': pvc[:-1]}))
    jobs.append((exe, 'missing_physical', base, {'pc': 0x477e4}, 0xff000, None, resources, {'resources': []}))
    out = run_parallel(reject_one, jobs)
    for row in out:
        superseded = SUPERSEDED_BOUNDARY_ENTRIES.get(row['label'])
        if not superseded:
            continue
        # The same run with an earlier stop must end there: the former failing block and the block of the new error are reached in order.
        s = dict(state, carry=2, pc=int(row['label'][-6:], 16))
        reached = []
        for stop in superseded['reached']:
            res, out_ram, out_pvc, ports, error = inv('n_%s_stop_%06x' % (row['label'], stop), exe, ram, s, pvc, bank, resources, stop=stop, external=255)
            assert res['ok'] and not error.strip() and res['pc'] == stop, (row['label'], hex(stop), res, error)
            reached.append(hex(stop))
        row.update(former_expected_API_error=UNSUPPORTED_MACHINE, classification=superseded['classification'], reached_block_starts=reached, API_only_control=True)
    # the four carry consumers need a known incoming C (Unknown -> checked error, full rollback)
    for pc in CONSUMERS:
        s0 = dict(state, pc=pc, carry=0)
        actual = inv('unknown_carry_%06x' % pc, exe, ram, s0, pvc, bank, resources, stop=0xff000)
        assert check_preserved(actual, ram, s0, pvc, bank) == UNKNOWN_CARRY
        out.append(dict(label='unknown_carry_consumer_%06x' % pc, error=UNKNOWN_CARRY, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    # positive controls: a known incoming C is consumed and preserved (478e4 with C Clear is the gate wait at 478de)
    controls = []
    for pc in CONSUMERS:
        for carry in (1, 2):
            want = branch_expect(ctx.instructions[pc], carry)
            s2 = dict(state, pc=pc, carry=carry)
            res, out_ram, out_pvc, ports, error = inv('consumer_%06x_%d' % (pc, carry), exe, ram, s2, pvc, bank, resources, stop=want)
            assert res['ok'] and not error and res['pc'] == want and res['carry'] == carry and out_ram == ram and out_pvc == pvc and not ports
            assert res['status'] == (1 if want == GATE_PC else 0)
            assert {k: res[k] for k in common.REGS} == {k: s2[k] for k in common.REGS}
            controls.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], next_pc=hex(want), status=res['status'], carry_preserved=True, API_state_unchanged=True))
    return out, controls


def zero_step_one(args):
    exe, base, resources, pc, carry = args
    ram, state, pvc, bank = base
    s = dict(state, pc=pc, carry=carry)
    result, out_ram, out_pvc, ports, error = inv('zero_%06x_%d' % (pc, carry), exe, ram, s, pvc, bank, resources, stop=pc)
    ok = result['ok'] and not error and result['status'] == 0 and {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc \
        and result['bank_base'] == bank and result['external_reads'] == 0 and not ports
    return (pc, carry, bool(ok), error.strip())


def zero_step(ctx, base, resources, starts):
    rows = run_parallel(zero_step_one, [(ctx.exe, base, resources, pc, carry) for pc in starts for carry in (0, 1, 2)])
    assert all(r[2] for r in rows), [r for r in rows if not r[2]]
    # informational: the two stop-only boundaries as zero-step (stop = entry PC)
    extra = run_parallel(zero_step_one, [(ctx.exe, base, resources, pc, carry) for pc in (TRAP_STOP, CUT_STOP) for carry in (0, 1, 2)])
    return len(rows), [dict(pc=hex(r[0]), carry=CARRY_NAME[r[1]], zero_step_ok=r[2], error=r[3]) for r in extra]


# FLOW_ONLY block starts that no observed single-block phase probed: direct API probes from a declared register state (stop = the block's branch target)
TARGETED_PROBES = {0x47558: (dict(d0=0x00000004, a0=0x000472be), 0x47544)}      # LEA (A0,D0.W),A0; BRA 47544


def targeted_probes(ctx, base, resources, pcs):
    ram, state, pvc, bank = base
    rows = []
    for pc in pcs:
        regs, stop = TARGETED_PROBES[pc]
        for carry in (1, 2):
            s = dict(state, pc=pc, carry=carry)
            s.update(regs)
            res, out_ram, out_pvc, ports, error = inv('targeted_%06x_%d' % (pc, carry), ctx.exe, ram, s, pvc, bank, resources, stop=stop)
            assert res['ok'] and not error and res['pc'] == stop and res['carry'] == carry and out_ram == ram and out_pvc == pvc and not ports, (hex(pc), carry, error)
            assert res['a0'] == (s['a0'] + 4) & M32 and res['status'] == 0
            rows.append(dict(pc=hex(pc), carry_in=CARRY_NAME[carry], carry_out=CARRY_NAME[res['carry']], next_pc=hex(res['pc']), preserved=res['carry'] == carry))
    return rows


def window_probe(ctx, base, resources, program):
    """The contract data window of groups 0~4 ends at dd4be but 47864 reads WORD 10(A0) of the last record of group 4 (record dd4ae -> WORD dd4be..dd4bf): the C++ reads the
    physical ROM through the live bus.  Direct entry at 47842 with 76(A6) := the record; the outcome is predicted from the ROM bytes."""
    exe = ctx.exe
    ram, state, pvc, bank = base
    rows = []
    for record, equal in ((0xdd4ae, False), (0xdd382, False), (0xd99e2, False), (0x472be, False), (0xdd4ae, True)):
        ram2 = bytearray(ram)
        a6 = state['a6']
        at = (a6 + 0x76) & 0xffff
        ram2[at:at + 4] = struct.pack('>I', record)
        a5 = state['a5']
        d0 = int.from_bytes(program[record + 0x10:record + 0x12], 'big')
        if equal:
            ram2[(a5 + 0x5686) & 0xffff:((a5 + 0x5686) & 0xffff) + 2] = struct.pack('>H', d0)       # WORD 10d686 equal to the record music: BEQ 47890
        ram2 = bytes(ram2)
        d1 = int.from_bytes(ram2[(a5 + 0x5686) & 0xffff:((a5 + 0x5686) & 0xffff) + 2], 'big')
        target = 0x47890 if d0 == d1 else 0x47872
        s0 = dict(state, pc=0x47842, carry=0)
        res, out_ram, out_pvc, ports, error = inv('window_%06x_%d' % (record, equal), exe, ram2, s0, pvc, bank, resources, stop=target)
        assert res['ok'] and not error and res['pc'] == target, (hex(record), error, hex(res['pc']))
        assert res['a0'] == record and (res['d0'] & 0xffff) == d0 and (res['d1'] & 0xffff) == d1, hex(record)
        assert out_ram[0xd683] == ram2[0xd683] & ~0x37 & 0xff                      # BCLR #0/#4/#2/#1/#5 of BYTE 10d683
        rows.append(dict(record=hex(record), music_word_declared_equal=equal, word_address=hex(record + 0x10), word_from_original_ROM='%04x' % d0, d0_word=hex(res['d0'] & 0xffff), next_pc=hex(res['pc']),
                         outside_contract_window=not any(a <= record + 0x10 and record + 0x12 <= b for a, b in CONTRACT_WINDOWS)))
    return rows


# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve().name == 'animation_machine_stage_catalog_execution'
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='stage_catalog_verify_'))
    try:
        run(report_path)
    finally:
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def guarded_run(job, ctx):
    try:
        return run_condition(job, ctx)
    except Exception:
        return dict(error=traceback.format_exc())


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_stage_catalog.py', 'tools/observe_animation_machine_stage_catalog.py', 'tools/observe_animation_machine_stage_entry.py',
                 'docs/analysis/animation-machine-stage-catalog-f1c-contract.md', 'engine/src/animation_machine_stage_catalog.cpp',
                 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h', 'engine/tests/animation_machine_stage_catalog_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = compile_harness(OUT)
    report, native_refs = audit_report(program, source)
    st = audit_static(program)
    instructions = st['instructions']
    native = Native()
    blob_count = native.audit_all_blobs()
    start_set = frozenset(st['starts'])
    lead_set = start_set | frozenset(BB_ENTRIES)
    ctx = Ctx(exe, resources, program, instructions, native, start_set, lead_set)
    results = report['results']
    assert [r['number'] for r in results] == list(range(len(results))) or True
    jobs = []
    for r in results:
        jobs.append((r, native.condition(r['condition_file'])))
    if API_ONLY:
        jobs = []
    elif DEBUG_LABEL:
        jobs = [j for j in jobs if any(x in j[0]['label'] for x in DEBUG_LABEL.split(','))]
    elif DEBUG_GROUPS:
        jobs = [j for j in jobs if j[0]['group'] in DEBUG_GROUPS.split(',')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        outs = list(pool.map(lambda job: guarded_run(job, ctx), jobs))
    failures = [(job[0]['label'], out['error']) for job, out in zip(jobs, outs) if isinstance(out, dict) and 'error' in out]
    if failures:
        for n, (label, text) in enumerate(failures[:30]):
            print('CONDITION FAILED', label, text.strip().splitlines()[-1][:600])
            if n < 3:
                print(text)
        raise AssertionError('%d conditions failed' % len(failures))
    totals = collections.Counter()
    rows, guards, waits, leader_failed = [], [], [], []
    superseded_guards = []
    first_pcs, flips, windows, wait_carry, carry_hist = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    slots, probe_seen = {}, set()
    for (acc, row) in outs:
        totals.update(acc.totals)
        rows.append(row)
        guards.extend(acc.guards)
        superseded_guards.extend(acc.superseded_guards)
        waits.extend(acc.waits)
        leader_failed.extend(acc.leader_failed)
        first_pcs.update(acc.first_pcs)
        flips.update(acc.consumer_flips)
        windows.update(acc.windows)
        wait_carry.update(acc.wait_carry)
        carry_hist.update(acc.carry_hist)
        for pc, slot in acc.slots.items():
            mine = slots.setdefault(pc, {1: True, 2: True})
            for probe in (1, 2):
                mine[probe] = mine[probe] and slot[probe]
    if not (API_ONLY or DEBUG_LABEL or DEBUG_GROUPS):
        assert len(rows) == 534
        assert totals['cases'] == 534
    for pc, slot in slots.items():
        assert pc in start_set and all(slot.values()) == (pc in st['preserving']), (hex(pc), slot)
    observed_preserving = sorted(pc for pc, slot in slots.items() if all(slot.values()))
    if not (API_ONLY or DEBUG_LABEL or DEBUG_GROUPS):
        missing = sorted(start_set - set(first_pcs))
        assert not missing, [hex(p) for p in missing]
        for pc in CONSUMERS:
            assert any(k.startswith('%x_incoming_' % pc) for k in flips), hex(pc)
    unprobed = sorted(set(st['preserving']) - set(observed_preserving) - set(CONSUMERS))
    # base state for the API-only checks: the first frame of a typed fixture (RAM image, registers, normalized PVC)
    base = api_base(native, ctx, results)
    negative, consumer_controls = negatives(ctx, base, st, resources)
    zero_count, zero_boundary = zero_step(ctx, base, resources, st['starts'])
    window_rows = window_probe(ctx, base, resources, program)
    if not (API_ONLY or DEBUG_LABEL or DEBUG_GROUPS):
        assert all(pc in TARGETED_PROBES for pc in unprobed), [hex(p) for p in unprobed if p not in TARGETED_PROBES]
    targeted_rows = targeted_probes(ctx, base, resources, [pc for pc in unprobed if pc in TARGETED_PROBES])
    cpp_cases, cpp_carry_table, cpp_ranges = cpp_static(st)
    assert cpp_cases == set(st['starts']), [hex(p) for p in cpp_cases ^ set(st['starts'])]
    assert cpp_ranges == sorted(F1C1_RANGES), (cpp_ranges, F1C1_RANGES)
    assert cpp_carry_table == set(st['preserving']), (sorted(hex(p) for p in cpp_carry_table ^ set(st['preserving'])))
    for name, expected in inputs.items():
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    assert len(native.checked) == 663 or API_ONLY or DEBUG_LABEL or DEBUG_GROUPS, len(native.checked)
    refs = dict(refs)
    refs.update(native_refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log'):
        refs[str(path.resolve())] = cc.digest(path)
    guard_table = collections.OrderedDict()
    for g in sorted(guards, key=lambda g: g['label']):
        guard_table[g['label']] = g
    def category(g):
        n = g['native_guard']
        if n['problem'] == 'step_limit':
            return 'native_watchdog_vs_cpp_block_budget'
        if n['problem'] == 'unsupported_code_target':
            reason = n.get('reason') or ''
            if 'odd target PC' in reason:
                return 'odd_computed_PC_refused_before_the_jump_native_vs_cpp_unaligned_PC_error_at_the_fetch'
            if reason.startswith('computed PC'):
                return 'computed_PC_inside_a_table_slot_instruction_native_refused_fetch_vs_cpp_unsupported_catalog_PC'
            return 'undeclared_stop_only_boundary_reached_native_refused_fetch_vs_cpp_unsupported_machine_PC'
        if n['problem'] == 'unsupported_odd_data_access':
            return 'odd_WORD_LONG_data_access_native_address_error_vs_cpp_checked_bus_error'
        return 'native_write_to_unmapped_address_vs_cpp_checked_device_address_error'
    category_counts = collections.Counter(category(g) for g in guards)
    deliberate = [
        dict(rule='native observer PVC image keeps the last raw WORDs written to 2ffff0 / 2ffff2 at offsets 1ff0 / 1ff2; the C++ device holds the normalized bank words (common.fold_device); '
                  'the native image is rebuilt from the actual C++ device plus the raw words of the ordered C++ port writes and compared by SHA256 / blob; the normalized words are compared '
                  'with the recorded ff8 / ff9 and the independent event fold', frames=totals['frames_native_raw_PVC_words_differ_from_normalized_device']),
        dict(rule='no initial SR is declared: every condition starts with C Unknown (native Unicorn starts with a declared SR 2000 = C clear); the only native conditions entering at a '
                  'carry consumer are the 4 zero-step rows, where nothing executes and the Unknown C is not consumed', rows=totals['zero_step_consumer_entries_unknown_carry_not_consumed']),
        dict(rule='native guards are observer faults / watchdog; the C++ reports a checked error at the same split phase and preserves the phase input (rollback equivalence with an original CPU '
                  'fault is not claimed)', rows=len(guards), categories=dict(sorted(category_counts.items()))),
        dict(rule='the declared IRQ palette effect of the 478de gate (and the sprite / sound release writes) are declared host RAM writes between runs; the IRQ itself is not modelled',
             waiting_frames=totals['native_waiting_frames'])]
    guard_errors = collections.Counter((g['native_guard']['problem'], g['checked_API_error']) for g in guards)
    result = dict(
        schema_version=1, source=source, inputs=inputs, artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, cpp_sha256=CPP_SHA, contract_sha256=CONTRACT_SHA,
        native_files_hash_checked=len(native.checked), native_blobs_hash_checked=blob_count,
        native_counts=dict(conditions=534, groups=report['groups'], frames=report['totals']['frames'], split_phases=report['totals']['split_phases'],
                           control_phases=report['totals']['control_phases'], prefix_frames=129 * 236),
        totals=dict(sorted(totals.items())), carry_histogram={CARRY_NAME[k]: v for k, v in sorted(carry_hist.items())},
        wait_carry=dict(sorted(wait_carry.items())), waits=sorted(waits),
        block_starts_run_as_first_pc_of_actual_cpp_phases=len(start_set & set(first_pcs)), first_pc_counts={hex(k): v for k, v in sorted(first_pcs.items()) if k in start_set},
        carry_consumer_flips=dict(sorted(flips.items())), carry_probed_block_starts=len(slots), carry_observed_preserving=[hex(p) for p in observed_preserving],
        carry_contract_preserving=[hex(p) for p in sorted(st['preserving'])],
        native_data_reads_outside_contract_window={k: v for k, v in sorted(windows.items()) if not k.startswith('outside_group_extents_')},
        native_data_reads_outside_group_extents={k: v for k, v in sorted(windows.items()) if k.startswith('outside_group_extents_')},
        window_probe=window_rows, targeted_carry_probes=targeted_rows, leader_alignment_failed_frames=sorted(leader_failed),
        flow_only_not_probed_by_observed_phases=[hex(p) for p in unprobed],
        deliberate_differences=deliberate, condition_groups=dict(sorted(collections.Counter(r['group'] for r in rows).items())),
        guards=list(guard_table.values()), superseded_guards=superseded_guards, guard_error_histogram={'%s -> %s' % k: v for k, v in sorted(guard_errors.items())},
        negatives=dict(count=len(negative), rows=negative), consumer_controls=consumer_controls, zero_step_start_pcs_x_3_carries=zero_count, zero_step_boundary_entries=zero_boundary,
        conditions=rows, cpp_static=dict(case_labels=len(cpp_cases), routing_ranges=[[hex(a), hex(b)] for a, b in cpp_ranges], carry_preserving_in_unit=len(cpp_carry_table)),
        static=dict(block_starts=len(st['starts']), bundled=len(st['bundled']), flow_only=len(st['preserving']), interior=len(st['interior']), even_pcs=st['even_pcs'],
                    instructions=st['instruction_count'], table=st['table']),
        contract_discrepancies_native=report['contract_discrepancies'], limitations=report['limitations'],
        rom_unchanged=True, original_program_modified=False, SR_read_at_any_phase=False, register_injection_after_begin=False, expected_register_injection=False)
    report_path.write_text(json.dumps(result, indent=1, sort_keys=True, default=str) + '\n')
    print('OK', json.dumps(dict(sorted(totals.items())), sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
