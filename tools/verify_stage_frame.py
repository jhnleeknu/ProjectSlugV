"""Immutable original 480bc versus the actual full-state stage-frame CLI.

Only explicit pre-entry and between-call host writes are used. A pending native
CPU, its stack and CCR are retained; hooks never inspect SR. Pending metadata
comes from the original stack, not from a duplicate helper implementation.
"""
import collections
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_MEM_INVALID, UC_HOOK_INTR, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from observe_scene_frame_execution import seeds, fixture, oracle_provenance
from observe_stage_buffer_frame import BASE, STACK, RETURN, KEYS, REGS, SAVED
from pack_stage_input import SOURCE_SHA256, validate_container

ENTRY, SPRITE_WAIT, SOUND_WAIT, EXTERNAL = 0x480bc, 0xcda4, 0x3aea, 0xd00046
CALLEES = (0x47642, 0x1a73c, 0x49b0c, 0x4aa88, 0xb4a2a, 0x6f1c2, 0x4701e, 0xe8a48, 0x2efa6)
ARGS = ('bank', 'stage', 'buffer_phase', 'saved_a6', 'saved_slot_a4', 'saved_slot_d7', 'saved_d0', 'saved_d1', 'saved_d7', 'saved_a0', 'cue_status', 'sound_kind', 'sound_phase', 'sound_saved')


def sha(data): return hashlib.sha256(data).hexdigest()


def put(ram, offset, size, value):
    raw = value.to_bytes(size, 'big')
    old = ram[offset:offset+size].hex()
    ram[offset:offset+size] = raw
    return dict(address=BASE+offset, previous=old, hex=raw.hex())


def smoke(root, seed=0):
    ram, regs = fixture(root, dict(seed_index=seed))
    changes = []
    for at in (0xcb8, 0xda8): changes.append(put(ram, at, 4, 0x270e))
    for at in (0xd734, 0xd738): changes.append(put(ram, at, 4, 0))
    changes += [put(ram, 0xf001, 1, 0), put(ram, 0xdc88, 4, 0x10db88)]
    for slot in range(8):
        at = 0xd61a-0x2c*slot
        changes += [put(ram, at+0x26, 4, 0x80000000), put(ram, at+0x2a, 2, 0)]
    changes += [put(ram, 0xde2e, 1, 1), put(ram, 0xde2f, 1, 0), put(ram, 0xd490, 1, 0), put(ram, 0xd491, 1, 0)]
    if seed == 0: assert sha(ram) == 'd51aba17d6dba2ff67ce77774f44df8c175c12c3cc52203e8dc34a7c61e266ec'
    return ram, regs, changes


def initial(regs, bank=2, cue_status=0):
    state = dict(zip(KEYS, regs))
    state.update({k: 0 for k in ARGS})
    state.update(bank=bank, cue_status=cue_status)
    return state


class Observer:
    def __init__(self, program):
        self.program = program
        self.cpu = make_cpu(program)
        self.cpu.mem_map(0x200000, 0x100000)
        self.cpu.mem_map(0xd00000, 4096)
        self.baseline = self.cpu.context_save()
        self.bank = 2
        self.section = 0
        self.cue_status = 0
        self.external = 0
        self.pcs, self.writes, self.ports, self.reads, self.bank_reads, self.boundaries = [], [], [], [], [], []
        self.error = None
        self.wait_visits = 0

        def code(cpu, pc, size, user):
            self.pcs.append(pc)
            if pc == RETURN: cpu.emu_stop(); return
            if pc in CALLEES:
                self.section = pc
                self.boundaries.append(dict(pc=pc, a7=cpu.reg_read(m.UC_M68K_REG_A7), a6=cpu.reg_read(m.UC_M68K_REG_A6)))
                assert cpu.reg_read(m.UC_M68K_REG_A7) == STACK-4
            if self.section == 0xe8a48:
                if pc == 0xcd58: self.cue_status = 1
                elif pc == 0xcdaa: self.cue_status = 0
                elif pc == 0xcd82: self.cue_status = 2
            if pc in (SPRITE_WAIT, SOUND_WAIT):
                address, reg = (0x108d34, m.UC_M68K_REG_D4) if pc == SPRITE_WAIT else (0x104d74, m.UC_M68K_REG_D1)
                equal = int.from_bytes(cpu.mem_read(address, 2), 'big') == (cpu.reg_read(reg)&65535)
                blocked = not equal if pc == SPRITE_WAIT else equal
                self.wait_visits = self.wait_visits+1 if blocked else 0
                if blocked and self.wait_visits == 2:
                    if pc == SPRITE_WAIT and self.section == 0xe8a48: self.cue_status = 3
                    cpu.emu_stop(); return
            word = int.from_bytes(cpu.mem_read(pc, 2), 'big')
            if word == 0x4afc or 0x4e40 <= word <= 0x4e4f:
                self.error = ('trap', pc, word); cpu.emu_stop()

        def write(cpu, access, address, size, value, user):
            value &= (1 << (size*8))-1
            if BASE <= address and address+size <= BASE+65536:
                self.writes.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC), address=address, size=size, value=value)); return
            if STACK-4096 <= address and address+size <= STACK+4: return
            if address not in (0x2ffff2, 0x2ffff0) or size != 2:
                self.error = ('unexpected-write', address, size, value); cpu.emu_stop(); return
            self.ports.append((size, address, value))
            if address == 0x2ffff2:
                if value not in (0x1000, 0x2000): self.error = ('bank', value); cpu.emu_stop(); return
                self.bank = 2 if value == 0x1000 else 3
                cpu.mem_write(0x200000, program[self.bank*0x100000:self.bank*0x100000+0xffff0])

        def read(cpu, access, address, size, value, user):
            if address == EXTERNAL:
                assert size == 1
                cpu.mem_write(address, bytes([self.external]))
                self.reads.append(dict(address=address, size=size, value=self.external))
            elif 0x200000 <= address < 0x2ffff0:
                self.bank_reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC), address=address, size=size, bank=self.bank))
            elif address < 0x300000 and address+size > 0x2ffff0:
                self.error = ('unexpected-MMIO-read', address, size); cpu.emu_stop()

        def invalid(cpu, access, address, size, value, user): self.error = ('invalid-memory', access, address, size); return False
        def intr(cpu, number, user): self.error = ('exception', number, cpu.reg_read(m.UC_M68K_REG_PC)); cpu.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE, code)
        self.cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        self.cpu.hook_add(UC_HOOK_MEM_READ, read)
        self.cpu.hook_add(UC_HOOK_MEM_INVALID, invalid)
        self.cpu.hook_add(UC_HOOK_INTR, intr)

    def prepare(self, ram, state):
        cpu = self.cpu
        cpu.context_restore(self.baseline)
        cpu.mem_write(BASE, bytes(ram))
        self.bank, self.cue_status, self.section = state['bank'], state['cue_status'], 0
        cpu.mem_write(0x200000, self.program[self.bank*0x100000:self.bank*0x100000+0xffff0])
        cpu.reg_write(m.UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(m.UC_M68K_REG_A5, 0x108000)
        cpu.reg_write(m.UC_M68K_REG_A7, STACK)
        cpu.mem_write(STACK-128, bytes(128)+RETURN.to_bytes(4, 'big'))
        for key, reg in zip(KEYS, REGS): cpu.reg_write(reg, state[key])
        cpu.reg_write(m.UC_M68K_REG_PC, ENTRY)

    def run(self, incoming, external):
        cpu = self.cpu
        self.external, self.wait_visits, self.error = external, 0, None
        for values in (self.pcs, self.writes, self.ports, self.reads, self.bank_reads, self.boundaries): values.clear()
        cpu.emu_start(cpu.reg_read(m.UC_M68K_REG_PC), 0xffffff, count=2000000)
        pc, sp = cpu.reg_read(m.UC_M68K_REG_PC), cpu.reg_read(m.UC_M68K_REG_A7)
        assert self.error is None and pc in (RETURN, SPRITE_WAIT, SOUND_WAIT), (self.error, hex(pc))
        state = initial([cpu.reg_read(r)&0xffffffff for r in REGS], self.bank, self.cue_status)
        def long(off): return int.from_bytes(cpu.mem_read(sp+off, 4), 'big')
        def word(off): return int.from_bytes(cpu.mem_read(sp+off, 2), 'big')
        if pc == SPRITE_WAIT:
            ret = long(0)
            if ret in (0x4b7da, 0x4b814):
                phase = 1 if ret == 0x4b7da else 2
                state.update(stage=1, buffer_phase=phase,
                    saved_a0=long(4), saved_d0=long(16) if phase == 1 else 0,
                    saved_d1=long(12) if phase == 1 else 0, saved_d7=long(8) if phase == 1 else 0,
                    saved_slot_d7=word(24 if phase == 1 else 12), saved_slot_a4=long(26 if phase == 1 else 14), saved_a6=long(30 if phase == 1 else 18))
                assert long(20 if phase == 1 else 8) == 0x4aad4
                assert long(34 if phase == 1 else 22) == 0x480d2
                assert sp == STACK-(38 if phase == 1 else 26)
            else:
                assert ret == 0xe8b58 and long(4) == 0x480ea, hex(ret)
                assert sp == STACK-8
                state.update(stage=2, cue_status=3)
        elif pc == SOUND_WAIT:
            kind, phase = {0x3c00: (1, 1), 0x2efc8: (1, 2), 0x3c70: (2, 1), 0x3c76: (2, 2), 0x2efda: (2, 3)}[long(0)]
            stacked = kind == 1 and phase == 1 or kind == 2 and phase < 3
            saved = cpu.mem_read(sp+4, 1)[0] if kind == 1 and stacked else word(4) if stacked else state['d0'] & (255 if kind == 1 else 65535)
            assert sp == STACK-(14 if stacked else 8)
            assert int.from_bytes(cpu.mem_read(STACK-8, 4), 'big') == {1: 0x2efc8, 2: 0x2efda}[kind]
            assert int.from_bytes(cpu.mem_read(STACK-4, 4), 'big') == 0x480f0
            state.update(stage=3, sound_kind=kind, sound_phase=phase, sound_saved=saved)
        else:
            assert sp == STACK+4
            assert int.from_bytes(cpu.mem_read(STACK, 4), 'big') == RETURN
        assert cpu.reg_read(m.UC_M68K_REG_A5) == 0x108000
        assert bytes(cpu.mem_read(0, BASE)) == self.program[:BASE]
        assert bytes(cpu.mem_read(0x200000, 0xffff0)) == self.program[self.bank*0x100000:self.bank*0x100000+0xffff0]
        if incoming['stage']:
            assert not any(p in self.pcs for p in CALLEES[:CALLEES.index({1: 0x4aa88, 2: 0xe8a48, 3: 0x2efa6}[incoming['stage']])+1])
            assert not self.reads
        state['external_reads'] = len(self.reads)
        ports = b''.join(struct.pack('>BII', *p) for p in self.ports)
        info = dict(final_pc=pc, final_a7=sp, final_a5=cpu.reg_read(m.UC_M68K_REG_A5), stack_hex=bytes(cpu.mem_read(STACK-64, 68)).hex(), pcs=self.pcs.copy(), boundaries=self.boundaries.copy(), RAM_writes=self.writes.copy(), physical_bank_reads=self.bank_reads.copy(), external_reads=self.reads.copy())
        return bytes(cpu.mem_read(BASE, 65536)), state, ports, info


def main():
    root = Path(__file__).resolve().parents[1]
    verifier_at_entry = sha(Path(__file__).read_bytes())
    program, source = load_verified_program(root)
    assert sha(program) == SOURCE_SHA256
    native_seed, resources, manifests, seed_metadata = seeds(root, program)
    assert len(resources) == 458
    mask = root/'extracted/runtime/stage_input/default_masks.ms5d'
    assert validate_container(mask.read_bytes()) == program[0x49ab0:0x49ab4]
    resources = resources+[dict(file=str(mask.relative_to(root)), sha256=sha(mask.read_bytes()))]
    table = root/'extracted/runtime/scene_debug.ms5d'
    # Additional cue/player windows are audited against canonical original data.
    from observe_stage_cue_frame import resource_audit
    extras = resource_audit(root)
    for name in ('player_record_lookup.ms5d', 'game_records.ms5d'):
        p = root/'extracted/runtime'/name
        data = p.read_bytes(); magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack('<4s7I', data[:32])
        import zlib
        assert magic == b'MS5D' and version == 1 and reserved == 0 and len(data) == size+32 and zlib.crc32(data[32:]) == crc and data[32:] == program[rom:rom+size]
        extras.append(dict(file=str(p.relative_to(root)), sha256=sha(data)))
    known = {r['file'] for r in resources}
    resources += [r for r in extras if r['file'] not in known]
    windows = [root/r['file'] for r in resources if r['file'].endswith('.ms5d') and root/r['file'] != table]
    folder = root/'artifacts/stage_frame'; folder.mkdir(parents=True, exist_ok=True)
    report = folder/'verification.json'; report.unlink(missing_ok=True)
    exe = root/'build/step_stage_frame'
    names = ['tools/verify_stage_frame.py', 'build/step_stage_frame', 'Makefile']
    names += [str(p.relative_to(root)) for directory in ('engine/src', 'engine/include/ms5') for p in (root/directory).glob('*') if p.suffix in ('.cpp', '.h')]
    names += ['engine/tools/step_stage_frame.cpp']
    names += ['tools/'+n+'.py' for n in ('observe_scene_frame_execution', 'observe_scene_general_initialization', 'observe_stage_buffer_frame', 'observe_stage_cue_frame', 'observe_stage_region_frame', 'verify_stage_spatial_frame', 'pack_stage_input', 'pack_stage_cue_frame', 'pack_stage_cue_control', 'verify_object_reset', 'disassemble_program')]
    inputs = {n: sha((root/n).read_bytes()) for n in names}
    assert inputs['tools/verify_stage_frame.py'] == verifier_at_entry
    oracle = oracle_provenance()
    observer = Observer(program)
    rows = []
    inp, out, portsfile = (folder/n for n in ('input.bin', 'cpp.bin', 'cpp.ports.bin'))

    def compare(label, ram, state, host_writes=None, external=0, selected_windows=None):
        if state['stage'] == 0: observer.prepare(ram, state)
        else:
            assert [observer.cpu.reg_read(r)&0xffffffff for r in REGS] == [state[k] for k in KEYS]
            for write in host_writes or []:
                observer.cpu.mem_write(write['address'], bytes.fromhex(write['hex']))
            assert bytes(observer.cpu.mem_read(BASE, 65536)) == ram, 'Resume may change only explicitly listed host bytes'
        expected, result, ports, info = observer.run(state, external)
        if state['stage'] == 0:
            expected_callees = list(CALLEES)
            if result['stage']:
                stopped = {1: 0x4aa88, 2: 0xe8a48, 3: 0x2efa6}[result['stage']]
                expected_callees = expected_callees[:expected_callees.index(stopped)+1]
            assert [b['pc'] for b in info['boundaries']] == expected_callees
        replay = bytearray(ram)
        for w in info['RAM_writes']: replay[w['address']-BASE:w['address']-BASE+w['size']] = w['value'].to_bytes(w['size'], 'big')
        assert bytes(replay) == expected
        inp.write_bytes(ram); out.write_bytes(b'old-output'); portsfile.write_bytes(b'old-ports')
        command = [str(exe)]+[str(state[k]) for k in KEYS+ARGS]+[str(external), str(inp), str(out), str(portsfile), str(table)]+list(map(str, windows if selected_windows is None else selected_windows))
        p = subprocess.run(command, capture_output=True, text=True)
        actual = json.loads(p.stdout) if not p.returncode else None
        assert p.returncode == 0, (label, p.stderr, result)
        expected_json = dict(result)
        assert inp.read_bytes() == ram and out.read_bytes() == expected and portsfile.read_bytes() == ports and actual == expected_json, (label, actual, expected_json, [(hex(i), a, b) for i, (a, b) in enumerate(zip(out.read_bytes(), expected)) if a != b][:20])
        index = len(rows)
        rname, pname = 'native_%04d.bin'%index, 'native_%04d.ports.bin'%index
        (folder/rname).write_bytes(expected); (folder/pname).write_bytes(ports)
        rows.append(dict(label=label, incoming=state, external=external, host_writes=host_writes or [], input_sha256=sha(ram), result=result, ram_file=rname, ram_sha256=sha(expected), ports_file=pname, ports_sha256=sha(ports), port_count=len(ports)//9, **info))
        return bytearray(out.read_bytes()), {k: actual[k] for k in KEYS+ARGS}

    ram, regs, changes = smoke(root)
    ram, state = compare('verified-seed-smoke', ram, initial(regs), changes)
    assert sha(ram) == '8ff378d791dcc354e64b995b82c37979b248272793e21b5e7a069b375fdc8135'
    for frame in range(1, 16): ram, state = compare('actual-CLI-output-carried-smoke-%d'%frame, ram, state)
    for seed in (4, 25, 34):
        for bank in (2, 3):
            ram, regs, changes = smoke(root, seed)
            ram, state = compare('verified-initializer-seed%d-bank%d'%(seed, bank), ram, initial(regs, bank), changes)
            for frame in range(1, 4): ram, state = compare('actual-CLI-carried-seed%d-bank%d-frame%d'%(seed, bank, frame), ram, state)

    from verify_stage_spatial_frame import cases as spatial_cases, fixture as spatial_fixture
    from observe_stage_region_frame import build_cases as region_cases, fixture as region_fixture
    from observe_stage_cue_frame import build_cases as cue_cases, fixture as cue_fixture
    active_coverage = {}
    for kind in ('spatial', 'region', 'cue-allocation'):
        ram, regs, changes = smoke(root)
        if kind == 'spatial':
            c = next(c for c in spatial_cases() if c['entry'] == 0x4701e and c['all_active'] and c['parent'] == 1 and c['timer'] == 1)
            data, _ = spatial_fixture(c, [])
            spans = [(0xd61a-7*0x2c, 8*0x2c), (0x6000, 9), (0x2000, 0x26), (0xd494, 1)]
        elif kind == 'region':
            c = next(c for c in region_cases() if c['entry'] == 0xb4a2a and c['activity'] == 3 and c['active'] == [1, 1] and c['source_null'] == [False, False] and c['coords'] == [[0, 0], [0, 0]])
            data, _ = region_fixture(c, [])
            spans = []
            for player in range(2):
                at, record = 0xcb8+player*0xf0, 0xdcba+player*0x2c
                changes += [put(ram, at, 4, 0), put(ram, at+0x61, 1, ram[at+0x61]&0x7f), put(ram, record+0x27, 1, 0)]
                spans += [(at+0x42, 2), (at+0x46, 2), (at+0x56, 4), (record, 2), (record+6, 6), (0x6000+player*16, 8)]
        else:
            c = next(c for c in cue_cases(root) if c['allocate'] == 1 and c['manual'] == 1 and c['debug'] == 0 and c['tag'] == 0x1c)
            data, _ = cue_fixture(c)
            spans = [(0xde26, 4), (0xde2e, 2), (0x6000, 8), (0x4c9c, 6), (0xbfc, 4), (0xc04, 2), (0xc5e, 1), (0x804, 4)]+[(0x408+0x100*i, 4) for i in range(4)]
        for at, count in spans:
            changes.append(dict(address=BASE+at, previous=ram[at:at+count].hex(), hex=data[at:at+count].hex()))
            ram[at:at+count] = data[at:at+count]
        ram, state = compare('active-'+kind, ram, initial(regs), changes)
        counts = collections.Counter(rows[-1]['pcs'])
        if kind == 'spatial': assert counts[0x46f52] == 8
        elif kind == 'region': assert counts[0xb4a50] and counts[0xb4a84] and ram[0xd68e] == 3
        else: assert counts[0x2986] == 1 and counts[0x2992] == 1 and ram[0xde2f] == 0
        active_coverage[kind] = {hex(pc): counts[pc] for pc in (0x46f52, 0xb4a50, 0xb4a84, 0x2986, 0x2992)}

    from observe_stage_buffer_frame import build_cases as buffer_cases, fixture as buffer_fixture
    from observe_stage_cue_frame import build_cases as cue_cases, fixture as cue_fixture
    buffer_catalog, _ = buffer_cases(root)
    cue_catalog = cue_cases(root)
    pending_sprites = set()
    for kind in ('buffer-first', 'buffer-second', 'cue'):
        ram, regs, changes = smoke(root)
        if kind.startswith('buffer'):
            family = 'actual-first-wait-both-sprites-live-resume' if kind == 'buffer-first' else 'fresh-second-sprite-only-wait'
            c = next(c for c in buffer_catalog if c['family'] == family and c['slot_set'] == [0] and c['bank'] == 2)
            data, _ = buffer_fixture(c, [])
            spans = ((0xf001, 1), (0xdaf8, 128), (0x9152, 4), (0x8b34, 512), (0x8d34, 8), (0x914e, 2), (0x2000, 0x100), (0x6000, 8))
        else:
            c = next(c for c in cue_catalog if c['family'] == 'whole-frame-begin-wait-hold-ready' and c['allocate'] == 0 and c['x'] == 0 and c['y'] == 0x40)
            data, _ = cue_fixture(c)
            spans = ((0xf001, 1), (0xde26, 4), (0xde2e, 2), (0x9152, 4), (0x8b34, 512), (0x8d34, 8), (0x914e, 2), (0x6000, 8))
        for at, count in spans:
            changes.append(dict(address=BASE+at, previous=ram[at:at+count].hex(), hex=data[at:at+count].hex()))
            ram[at:at+count] = data[at:at+count]
        ram, state = compare(kind+'-start', ram, initial(regs), changes)
        assert state['stage'] == (2 if kind == 'cue' else 1)
        assert state['buffer_phase'] == {'buffer-first': 1, 'buffer-second': 2, 'cue': 0}[kind]
        pending_sprites.add((state['stage'], state['buffer_phase']))
        changes = [put(ram, 0x9152, 4, 0x106001), put(ram, 0x8d36, 2, 0xdead), put(ram, 0x8d3a, 2, 0xbeef)]
        ram, held = compare(kind+'-hold-invalidated-callback-live-queue', ram, state, changes)
        assert held == state
        changes = [put(ram, 0x8d34, 2, state['d4']&65535)]
        if kind == 'buffer-first':
            changes += [put(ram, 0x9152, 4, 0xcd50), put(ram, 0x8d36, 2, (state['d4']+2)&65535)]
        ram, state = compare(kind+'-release', ram, held, changes)
        if kind == 'buffer-first':
            assert state['stage'] == 1 and state['buffer_phase'] == 2
            pending_sprites.add((1, 2))
            changes = [put(ram, 0x8d34, 2, state['d4']&65535)]
            ram, state = compare(kind+'-release-second', ram, state, changes)
        assert state['stage'] == 0
    assert pending_sprites == {(1, 1), (1, 2), (2, 0)}

    cue_status_coverage = set()
    for label, x, y, consumer, prepared, wanted in (
            ('clip-Y', 0, 0x7fff, 0x100, 0x80, 1),
            ('clip-X', 0x7fff, 0x40, 0x100, 0x80, 1),
            ('full', 0, 0x40, 2, 2, 2),
            ('accepted', 0, 0x40, 0x100, 0x80, 0)):
        ram, regs, changes = smoke(root)
        for at, size, value in ((0xf001, 1, 2), (0xde26, 4, 0x106000), (0x9152, 4, 0xcd50), (0x8d34, 2, consumer), (0x8d36, 2, prepared), (0x8d38, 2, 0), (0x8d3a, 2, 0), (0x8b36, 2, 12), (0x914e, 2, 0), (0x6000, 2, x), (0x6002, 2, y), (0x6004, 1, 0)):
            changes.append(put(ram, at, size, value))
        ram, state = compare('cue-debug-status-'+label, ram, initial(regs, cue_status=2), changes)
        assert state['stage'] == 0 and state['cue_status'] == wanted
        cue_status_coverage.add(wanted)
    cue_status_coverage.add(3)
    assert cue_status_coverage == {0, 1, 2, 3}

    pending_seen = set()
    for rising in (False, True):
        for target in range(1, 3 if rising else 4):
            for tail in (0, 127):
                ram, regs, changes = smoke(root)
                for at in (0x12, 0xfd82, 0xfe80, 0xfd8d, 0x4d7e, 0x4d7b): changes.append(put(ram, at, 1, 0))
                changes += [put(ram, 0xd490, 1, int(rising)), put(ram, 0xd491, 1, int(not rising))]
                for at, v in ((0x4d82, 0x455), (0x4d84, 0x566), (0x4d86, 0x677), (0x4d88, 0x788), (0x4d8a, 0), (0x4d8c, 6), (0x4d74, (tail+target)&127), (0x4d76, tail)): changes.append(put(ram, at, 2, v))
                label = 'sound-%s-phase%d-tail%d'%('word' if rising else 'cancel', target, tail)
                ram, state = compare(label+'-start', ram, initial(regs), changes)
                assert (state['stage'], state['sound_kind'], state['sound_phase']) == (3, 1 if rising else 2, target)
                pending_seen.add((state['sound_kind'], state['sound_phase']))
                changes = [put(ram, 0xd491, 1, 0x71), put(ram, 0xf001, 1, 0xff), put(ram, 0x4d76, 2, 0x8000), put(ram, 0x4d8a, 2, 0x8001)]
                ram, held = compare(label+'-hold-mutated-prior-stages-no-scene-windows', ram, state, changes, 255, [])
                assert held == state and ram[0xd491] == 0x71
                changes = [put(ram, 0x4d74, 2, 0xffff)]
                ram, state = compare(label+'-release-no-scene-windows', ram, held, changes, 255, [])
                assert state['stage'] == 0 and ram[0xd491] == 0x71
    assert pending_seen == {(1, 1), (1, 2), (2, 1), (2, 2), (2, 3)}

    for rising in (False, True):
        ram, regs, changes = smoke(root)
        for at in (0x12, 0xfd82, 0xfe80, 0xfd8d, 0x4d7e, 0x4d7b): changes.append(put(ram, at, 1, 0))
        changes += [put(ram, 0xd490, 1, int(rising)), put(ram, 0xd491, 1, int(not rising))]
        for at, v in ((0x4d82, 0x455), (0x4d84, 0x566), (0x4d86, 0x677), (0x4d88, 0x788), (0x4d8a, 0), (0x4d8c, 6), (0x4d74, 1), (0x4d76, 0)): changes.append(put(ram, at, 2, v))
        label = 'sound-sequential-'+('word' if rising else 'cancel')
        ram, state = compare(label+'-start', ram, initial(regs), changes)
        count = 2 if rising else 3
        assert state['sound_phase'] == 1
        for phase in range(2, count+2):
            changes = [put(ram, 0x4d74, 2, phase)]
            ram, state = compare(label+'-release-to-phase%d'%phase, ram, state, changes, selected_windows=[])
            assert state['sound_phase'] == (phase if phase <= count else 0)
        assert state['stage'] == 0
    external_coverage = []
    for external in (0, 1):
        ram, regs, changes = smoke(root)
        for at in (0x12, 0xfd82, 0xfe80, 0xfd8d, 0x4d7e, 0x4d7b): changes.append(put(ram, at, 1, 0))
        for at, size, value in ((0x12, 1, 1), (0xfd82, 1, 1), (0xfd8d, 1, 1), (0xf001, 1, 32), (0xd490, 1, 1), (0xd491, 1, 0), (0x4d8a, 2, 0), (0x4d8c, 2, 6), (0x4d82, 2, 0x455), (0x4d74, 2, 0xffff), (0x4d76, 2, 0)):
            changes.append(put(ram, at, size, value))
        ram, state = compare('sound-conditional-external-read-%d'%external, ram, initial(regs), changes, external)
        assert len(rows[-1]['external_reads']) == 1
        external_coverage.append(dict(value=external, reads=rows[-1]['external_reads']))

    import tempfile
    import os
    negatives = []
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work = Path(temporary)
        ni, no, np = (work/n for n in ('input.bin', 'output.bin', 'ports.bin'))
        base, regs, _ = smoke(root)
        base_state = initial(regs)
        sentinel = b'preserved-stage-frame-output\0\xff'
        def reject(label, ram=base, state=base_state, outputs=None, selected=None, external=0):
            destinations = (no, np) if outputs is None else outputs
            files = windows if selected is None else selected
            ni.write_bytes(ram)
            for destination in destinations:
                if destination != ni and destination not in files and destination != table and not (destination.exists() and os.path.samefile(destination, ni)):
                    destination.write_bytes(sentinel)
            watched = {p: p.read_bytes() for p in set([ni, no, np, table]+list(destinations)+list(files)) if p.exists() and p.is_file()}
            command = [str(exe)]+[str(state[k]) for k in KEYS+ARGS]+[str(external), str(ni), str(destinations[0]), str(destinations[1]), str(table)]+list(map(str, files))
            p = subprocess.run(command, capture_output=True, text=True)
            assert p.returncode and not p.stdout and all(p.read_bytes() == raw for p, raw in watched.items()), (label, p.stdout, p.stderr)
            negatives.append(dict(label=label, input_outputs_resources_preserved=True, native_bad_fixture_executed=False, error=p.stderr.strip()))
        for size in (0, 65535, 65537): reject('RAM-size-%d'%size, bytes(size))
        for key in KEYS+ARGS:
            for invalid in ('-1', '4294967296', '1x', ''):
                reject('numeric-parser-'+key, state=dict(base_state, **{key: invalid}))
        for external in ('-1', '256', '1x', ''): reject('external-parser', external=external)
        for bad in (dict(stage=4), dict(bank=1), dict(stage=0, buffer_phase=1), dict(stage=1, buffer_phase=0), dict(stage=2, buffer_phase=1), dict(stage=3, sound_kind=0), dict(stage=0, sound_kind=1, sound_phase=1), dict(stage=2, sound_kind=1, sound_phase=1), dict(stage=3, sound_kind=1, sound_phase=3), dict(stage=3, sound_kind=2, sound_phase=0), dict(cue_status=4)):
            reject('inconsistent-state', state=dict(base_state, **bad))
        for key in SAVED:
            reject('inactive-buffer-metadata-'+key, state=dict(base_state, **{key: 1}))
        reject('missing-required-fresh-scene-windows', selected=[])
        late = bytearray(base); put(late, 0xdc88, 4, 0x110000)
        reject('late-buffer-failure-after-scene-ports', ram=late)
        late = bytearray(base); put(late, 0xde2f, 1, 1); put(late, 0xde26, 4, 0xffffffff)
        reject('late-cue-failure-after-prior-stages', ram=late)
        reject('input-output-alias', outputs=(ni, np))
        reject('input-ports-alias', outputs=(no, ni))
        reject('RAM-output-ports-alias', outputs=(no, no))
        reject('resource-output-collision', outputs=(windows[0], np))
        reject('resource-ports-collision', outputs=(no, windows[0]))
        reject('table-output-collision', outputs=(table, np))
        for kind in ('hardlink', 'symlink'):
            ni.write_bytes(base)
            alias = work/kind
            if kind == 'hardlink': os.link(ni, alias)
            else: alias.symlink_to(ni)
            reject('input-output-'+kind, outputs=(alias, np))
        probe = work/'CaseSensitivity.probe'
        probe.write_bytes(b'case sensitivity probe')
        folded_probe = work/'casesensitivity.probe'
        folds_case = folded_probe.exists() and os.path.samefile(probe, folded_probe)
        case_alias_regression = dict(case_insensitive_filesystem=folds_case, applicable=folds_case)
        if folds_case:
            first, second = work/'NewFrame.bin', work/'newframe.bin'
            assert not first.exists() and not second.exists()
            ni.write_bytes(base)
            command = [str(exe)]+[str(base_state[k]) for k in KEYS+ARGS]+['0', str(ni), str(first), str(second), str(table)]+list(map(str, windows))
            p = subprocess.run(command, capture_output=True, text=True)
            assert p.returncode and not p.stdout and ni.read_bytes() == base
            assert not first.exists() and not second.exists(), 'Rejected reservation must remove newly created alias outputs'
            case_alias_regression.update(rejected=True, input_preserved=True, absent_outputs_preserved=True, error=p.stderr.strip())

    assert inputs == {n: sha((root/n).read_bytes()) for n in names}, 'Source/core/binary changed during verification; rerun the complete verifier'
    assert oracle_provenance() == oracle and sha((root/source['path']).read_bytes()) == SOURCE_SHA256
    for item in resources+manifests: assert sha((root/item['file']).read_bytes()) == item['sha256']
    for label in ('initialization_observation', 'initialization_verification', 'frame_inventory'):
        assert sha((root/seed_metadata[label+'_file']).read_bytes()) == seed_metadata[label+'_sha256']
    report.write_text(json.dumps(dict(source=source, oracle=oracle, inputs=inputs, resources=resources, resource_count=sum(r['file'].endswith('.ms5d') for r in resources), manifests=manifests, seed_metadata=seed_metadata, cases=len(rows), negative_cases=negatives, case_alias_regression=case_alias_regression, active_coverage=active_coverage, cue_status_coverage=sorted(cue_status_coverage), conditional_external_read_coverage=external_coverage, pending_sound_states=sorted(pending_seen), pending_sprite_states=sorted(pending_sprites), full_RAM_14_registers_bank_pending_ordered_ports_equal=True, actual_CLI_output_carry=True, original_program_modified=False, physical_bank_payload_modified=False, in_call_SR_read=False, results=rows, scope='Whole immutable original480bc and all original callees versus actualCLI; full64KiBRAM14regs, physicalbank, orderedports, stack-derived pending. NativeCPU/stack/CCR persist across waits. All hostwrites listed. Controlled fixtures do not claim naturalIRQ/scheduler/player execution, CCR/cycle or audiovisual equivalence.'), indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), negative_cases=len(negatives), pending_sound_states=sorted(pending_seen), sha256=sha(report.read_bytes()))))


if __name__ == '__main__': main()
