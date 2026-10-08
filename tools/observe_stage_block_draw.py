"""Unpatched477a2/ddf9a/362a/35f0 native observations; no C++ comparison."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_MEM_INVALID, UC_HOOK_INTR, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from observe_scene_frame_execution import oracle_provenance
from observe_screen_reset_full import KEYS, REGS, BASE, STACK, RETURN, STACK_START
from verify_stage_catalog import SOURCE_SHA256

TABLE_START, TABLE_END, STREAM, CAP = 0xddfa4, 0xddfdc, 0x106000, 100000
ENTRIES = (0x477a2, 0xddf9a, 0x362a, 0x35f0)
STEP_PCS = (0x360c, 0x3612, 0x3616, 0x361a, 0x361c, 0x3620, 0x3628)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_cases(program):
    profiles = ((0,)*15, (0xffffffff,)*15,
        tuple((0x81231234+i*0x01010101)&0xffffffff for i in range(15)),
        tuple((0xabcdffff-i*0x01010203)&0xffffffff for i in range(15)))
    cases = []
    for profile, values in enumerate(profiles):
        def add(entry, family, base=0x7162, payload=None, **updates):
            regs = dict(zip(KEYS, values)); regs['d0'] = (regs['d0']&0xffff0000)|base
            regs.update(updates)
            cases.append(dict(entry=entry, family=family, profile=profile, incoming=regs,
                stream_hex=None if payload is None else payload.hex()))
        add(0x477a2, 'canonical-tail-477a2')
        for base in (0, 0x7000, 0x7162):
            add(0xddf9a, 'canonical-tail-ddf9a', base=base)
        add(0x362a, 'live-RAM-empty-sentinel', payload=b'\xff\xff', a0=STREAM)
        add(0x362a, 'live-RAM-canonical-copy', payload=program[TABLE_START:TABLE_END], a0=STREAM)
        add(0x362a, 'live-RAM-BYTE-wrap-WORD-offset-wrap', base=0xffff,
            payload=struct.pack('>HHBBH', 1, 0x12f8, 2, 3, 0xffff), a0=STREAM)
        add(0x362a, 'live-RAM-two-record-BYTE-wrap', base=0x7000,
            payload=struct.pack('>HHBBHHBBH', 0x10, 0xfffe, 1, 2, 0x40, 0x12ff, 2, 1, 0xffff), a0=STREAM)
        for coord, width, height in ((0x7000, 2, 3), (0x74fc, 1, 4)):
            add(0x35f0, 'direct-valid-rectangle', base=coord,
                d1=(values[1]&0xffff0000)|0xfff8,
                d2=(values[2]&0xffff0000)|width,
                d3=(values[3]&0xffff0000)|height)
    assert len(cases) == 40
    return cases


def fixture(case):
    ram = bytearray(hashlib.shake_256(b'stage-block-draw-'+bytes([case['profile']])).digest(65536))
    if case['stream_hex'] is not None:
        payload = bytes.fromhex(case['stream_hex'])
        ram[STREAM-BASE:STREAM-BASE+len(payload)] = payload
    return bytes(ram)


class Observer:
    def __init__(self, program):
        self.program = program; self.cpu = make_cpu(program)
        self.cpu.mem_map(0x300000, 0x100000)
        self.baseline = self.cpu.context_save()
        self.events, self.boundaries, self.steps, self.reads = [], [], [], []
        self.error = None; self.instructions = 0

        def registers(cpu):
            return dict(zip(KEYS, (cpu.reg_read(reg)&0xffffffff for reg in REGS)))

        def code(cpu, pc, size, user):
            self.instructions += 1
            if pc == RETURN:
                cpu.emu_stop(); return
            if pc in ENTRIES:
                self.boundaries.append(dict(pc=pc, a7=cpu.reg_read(m.UC_M68K_REG_A7), registers=registers(cpu)))
            if pc in STEP_PCS:
                self.steps.append(dict(pc=pc, registers=registers(cpu)))
            opcode = int.from_bytes(cpu.mem_read(pc, 2), 'big')
            if opcode == 0x4afc or 0x4e40 <= opcode <= 0x4e4f:
                self.error = dict(kind='trap-or-illegal', pc=pc, opcode=opcode); cpu.emu_stop()

        def write(cpu, access, address, size, value, user):
            kind = 'ports' if address == 0x3c0000 else 'ram' if BASE <= address and address+size <= BASE+65536 else 'stack' if STACK_START <= address and address+size <= STACK+4 else None
            event = dict(pc=cpu.reg_read(m.UC_M68K_REG_PC), address=address, size=size, value=value&((1 << (size*8))-1), kind=kind)
            self.events.append(event)
            if kind is None:
                self.error = dict(kind='unexpected-write', event=event); cpu.emu_stop()

        def read(cpu, access, address, size, value, user):
            if not (address+size <= BASE or BASE <= address and address+size <= BASE+65536 or STACK_START <= address and address+size <= STACK+4):
                self.reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC), address=address, size=size))

        def invalid(cpu, access, address, size, value, user):
            self.error = dict(kind='invalid-memory', access=access, address=address, size=size, pc=cpu.reg_read(m.UC_M68K_REG_PC)); return False

        def intr(cpu, number, user):
            self.error = dict(kind='cpu-exception', number=number, pc=cpu.reg_read(m.UC_M68K_REG_PC)); cpu.emu_stop()

        self.cpu.hook_add(UC_HOOK_CODE, code); self.cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        self.cpu.hook_add(UC_HOOK_MEM_READ, read); self.cpu.hook_add(UC_HOOK_MEM_INVALID, invalid); self.cpu.hook_add(UC_HOOK_INTR, intr)

    def run(self, case, ram):
        cpu = self.cpu; cpu.context_restore(self.baseline); cpu.mem_write(BASE, ram)
        cpu.mem_write(STACK_START, bytes([0x5a])*4100); cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        cpu.reg_write(m.UC_M68K_REG_SR, 0x2000); cpu.reg_write(m.UC_M68K_REG_A7, STACK)
        for key, reg in zip(KEYS, REGS): cpu.reg_write(reg, case['incoming'][key])
        self.events.clear(); self.boundaries.clear(); self.steps.clear(); self.reads.clear(); self.error = None; self.instructions = 0
        try:
            cpu.emu_start(case['entry'], 0xffffff, count=CAP)
        except unicorn.UcError as exc:
            if self.error is None: self.error = dict(kind='emulator-error', error=str(exc), pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc = cpu.reg_read(m.UC_M68K_REG_PC)
        if pc != RETURN and self.error is None: self.error = dict(kind='instruction-cap', pc=pc, cap=CAP)
        assert self.error is None, self.error
        assert cpu.reg_read(m.UC_M68K_REG_A7) == STACK+4 and bytes(cpu.mem_read(STACK, 4)) == RETURN.to_bytes(4, 'big')
        stack_events = [event for event in self.events if event['kind'] == 'stack']
        lowest = min([event['address'] for event in stack_events]+[STACK])
        assert bytes(cpu.mem_read(STACK_START, lowest-STACK_START)) == bytes([0x5a])*(lowest-STACK_START)
        assert bytes(cpu.mem_read(0, BASE)) == self.program[:BASE] and not self.reads
        output = bytes(cpu.mem_read(BASE, 65536)); replay = bytearray(ram)
        for event in self.events:
            if event['kind'] == 'ram':
                at = event['address']-BASE; replay[at:at+event['size']] = event['value'].to_bytes(event['size'], 'big')
        assert output == bytes(replay)
        result = dict(zip(KEYS, (cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        ports = b''.join(struct.pack('>BII', event['size'], event['address'], event['value']) for event in self.events if event['kind'] == 'ports')
        info = dict(returned=True, final_pc=pc, final_a7=cpu.reg_read(m.UC_M68K_REG_A7), instructions=self.instructions,
            lowest_stack_write=lowest, stack_write_count=len(stack_events), RAM_writes=[e for e in self.events if e['kind'] == 'ram'],
            boundaries=self.boundaries.copy(), calls=dict(collections.Counter(hex(row['pc']) for row in self.boundaries)),
            unexpected_reads=self.reads.copy())
        return output, result, ports, dict(writes=self.events.copy(), steps=self.steps.copy()), info


def assert_contract(case, ram, output, result, ports, trace, info):
    incoming = case['incoming']; assert output == ram and not info['RAM_writes']
    events = [struct.unpack_from('>BII', ports, i) for i in range(0, len(ports), 9)]
    assert all(address == 0x3c0000 and (size == 4 or size == 2 and value == 0x8200) for size, address, value in events)
    for key in ('d4', 'd5', 'a1', 'a2', 'a3', 'a5', 'a6'): assert result[key] == incoming[key], key
    for key in ('d0', 'd1', 'd6'): assert result[key]&0xffff0000 == incoming[key]&0xffff0000, key
    if case['family'] == 'live-RAM-empty-sentinel':
        expected = dict(incoming); expected.update(a0=STREAM+2, d1=(incoming['d1']&0xffff0000)|0xffff)
        assert result == expected and not ports and not trace['steps']; return
    assert result['a4'] == 0x3c0000 and result['d6']&65535 == 0
    if case['entry'] != 0x35f0:
        assert result['d2'] == 0 and result['d0']&65535 == (0x7162 if case['entry'] == 0x477a2 else incoming['d0']&65535)
        assert result['d1']&65535 == 0xffff
        assert result['a0'] == (TABLE_END if case['stream_hex'] is None else STREAM+len(bytes.fromhex(case['stream_hex'])))
    else:
        assert result['a0'] == incoming['a0'] and result['d2'] == incoming['d2']&0xffff0000 and result['d3'] == incoming['d3']
    if case['entry'] == 0x477a2:
        assert len(events) == 137 and result['a0'] == 0xddfdc and result['d0']&65535 == 0x7162 and result['d1']&65535 == 0xffff
        assert result['d2'] == 0 and result['d3'] == 4 and result['d6']&65535 == 0 and result['d7'] == 0x72caff0b and result['a4'] == 0x3c0000
    if case['family'] == 'live-RAM-BYTE-wrap-WORD-offset-wrap':
        rectangle_entry = next(row for row in info['boundaries'] if row['pc'] == 0x35f0)
        assert incoming['d0']&65535 == 0xffff and rectangle_entry['registers']['d0']&65535 == 0
        assert rectangle_entry['registers']['d0']&0xffff0000 == incoming['d0']&0xffff0000
        assert events[0] == (4, 0x3c0000, 0x000012f8)
    # Before/after observations bracket individual original instructions.
    # These width assertions do not generate the observed tile/port sequence.
    steps = trace['steps']; widths = collections.Counter()
    for before, after in zip(steps, steps[1:]):
        pc, next_pc = before['pc'], after['pc']; a, b = before['registers'], after['registers']
        if (pc, next_pc) == (0x360c, 0x3612):
            assert b['d7'] == (a['d7']+0x10000)&0xffffffff; widths['row_LONG_increment'] += 1
        elif (pc, next_pc) == (0x3612, 0x3616):
            assert b['d7'] == (a['d7']&0xffffff00)|((a['d7']+16)&255); widths['tile_BYTE_increment'] += 1
            if a['d7']&255 >= 240: widths['tile_BYTE_wrap'] += 1
        elif (pc, next_pc) == (0x361a, 0x361c):
            assert b['d1'] == (a['d1']&0xffffff00)|((a['d1']+1)&255); widths['column_tile_BYTE_increment'] += 1
        elif (pc, next_pc) == (0x361c, 0x3620):
            assert b['d0'] == (a['d0']&0xffff0000)|((a['d0']+32)&65535); widths['coordinate_WORD_increment'] += 1
    info['observed_width_checks'] = dict(widths)


def main():
    root = Path(__file__).resolve().parents[1]; program, source = load_verified_program(root)
    assert sha(program) == SOURCE_SHA256 == source['sha256']
    static_path = root/'artifacts/stage_activation_block_table.json'; static = json.loads(static_path.read_bytes())
    assert static['source']['sha256'] == SOURCE_SHA256 and static['start_cpu'] == TABLE_START and static['end_cpu'] == TABLE_END
    raw = program[TABLE_START:TABLE_END]; assert len(raw) == 56 and raw[-2:] == b'\xff\xff' and len(static['records']) == 9
    for index, record in enumerate(static['records']):
        assert record['cpu'] == record['rom'] == TABLE_START+index*6
        assert tuple(record[key] for key in ('offset', 'tile', 'width', 'height')) == struct.unpack_from('>HHBB', raw, index*6)
    folder = root/'artifacts/stage_block_draw'; folder.mkdir(parents=True, exist_ok=True)
    report = folder/'observation.json'; report.unlink(missing_ok=True)
    names = ('tools/disassemble_program.py', 'tools/verify_stage_catalog.py', 'tools/observe_stage_block_draw.py', 'tools/observe_screen_reset_full.py', 'tools/verify_object_reset.py', 'tools/observe_scene_frame_execution.py', 'docs/analysis/stage-block-draw-contract.md', 'artifacts/stage_activation_block_table.json')
    inputs = {name: sha((root/name).read_bytes()) for name in names}; oracle = oracle_provenance(); observer = Observer(program)
    rows, mismatches, native_pairs = [], [], {}
    for index, case in enumerate(build_cases(program)):
        ram = fixture(case); output, result, ports, trace, info = observer.run(case, ram)
        try:
            assert_contract(case, ram, output, result, ports, trace, info)
        except AssertionError as exc:
            mismatches.append(dict(case_index=index, fixture=case, error=repr(exc), result=result))
        if case['entry'] == 0xddf9a and case['incoming']['d0']&65535 == 0x7162:
            native_pairs[case['profile']] = (result, ports)
        if case['family'] == 'live-RAM-canonical-copy':
            fixed_result, fixed_ports = native_pairs[case['profile']]; normalized = dict(result); normalized['a0'] = TABLE_END
            assert normalized == fixed_result and ports == fixed_ports
        files = dict(input_ram_file='input_%02d.bin'%index, ram_file='native_%02d.bin'%index, ports_file='native_%02d.ports.bin'%index, trace_file='native_%02d.trace.json'%index)
        payloads = dict(input_ram_file=ram, ram_file=output, ports_file=ports, trace_file=(json.dumps(trace, indent=2)+'\n').encode())
        for key, data in payloads.items(): (folder/files[key]).write_bytes(data)
        rows.append(dict(case_index=index, fixture=case, result=result, input_ram_sha256=sha(ram), ram_sha256=sha(output),
            ports_sha256=sha(ports), trace_sha256=sha(payloads['trace_file']), port_count=len(ports)//9, **files, **info))
    assert inputs == {name: sha((root/name).read_bytes()) for name in inputs} and sha((root/source['path']).read_bytes()) == SOURCE_SHA256
    width_totals = collections.Counter()
    for row in rows: width_totals.update(row.get('observed_width_checks', {}))
    assert width_totals['tile_BYTE_wrap'] > 0
    result = dict(source=source, oracle=oracle, inputs=inputs, table_cpu_start=TABLE_START, table_rom_start=TABLE_START,
        table_length=len(raw), table_payload_sha256=sha(raw), cases=len(rows), completed_cases=len(rows), contract_mismatches=mismatches,
        total_native_ports=sum(row['port_count'] for row in rows), observed_width_checks=dict(width_totals),
        original_program_modified=False, in_call_SR_read=False, full_RAM_15_registers_ordered_ports_observed=True,
        Cpp_comparison_performed=False, native_fixed_RAM_copy_equal_profiles=len(native_pairs), results=rows,
        scope='Original477a2/ddf9a/362a/35f0 toRTS with immutablecanonical9recordtable and explicitliveRAM6bytestreams/empty sentinel. Full64KiBRAM15regs/allorderedvideoports and completeRAM/stack/portwrites; native before/after instruction snapshots verifyBYTEtile/WORDcoordinate widths. SRbeforeA7/nohookSR; isolatedboundedstack; assertionsonlyforstaticpredictions. NoC++comparison, genericzero-width/height/TRAP fuzz, renderedpixels, CCR/cycle/scheduler equivalence claim.')
    report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), mismatches=len(mismatches), ports=result['total_native_ports'], width_checks=dict(width_totals), sha256=sha(report.read_bytes()))))
    if mismatches: raise SystemExit(1)


if __name__ == '__main__':
    main()
