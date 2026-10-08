"""Immutable ca9e/caf0 native15register/RAM/ordered-port observations only."""
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
from verify_stage_catalog import SOURCE_SHA256

BASE, STACK, RETURN = 0x100000, 0x1feffc, 0xff000
STACK_START, CAP = STACK-4096, 100000
KEYS = tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(7))
REGS = tuple(getattr(m, 'UC_M68K_REG_'+key.upper()) for key in KEYS)
PORTS = (0x300001, 0x3c0000, 0x3c0004)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_cases():
    profiles = ((0,)*15, (0xffffffff,)*15,
        (0xabcd1234, 0xfedcba98, 0x98765432, 0x87654321, 0xbeefabcd, 0x76543210, 0x12345678, 0x81235678,
         0xdeadbeef, 0xcafebabe, 0xface1234, 0xe1e23456, 0xfeedbeef, 0x13579bdf, 0x87654321),
        tuple((0x80000000+i*0x01010101)&0xffffffff for i in range(15)))
    cases = []
    for entry in (0xca9e, 0xcaf0):
        a5s = (0x108000, 0, 0xffffffff, 0x10769a) if entry == 0xca9e else (0x108000, 0x10769a, 0x117699, 0x108001)
        for profile, values in enumerate(profiles):
            for a5 in a5s:
                regs = list(values)
                regs[13] = a5
                cases.append(dict(entry=entry, profile=profile, incoming=dict(zip(KEYS, regs)),
                    clear_address=None if entry == 0xca9e else a5-0x769a))
    return cases


def fixture(case):
    ram = bytearray(hashlib.shake_256(b'screen-reset-full-'+bytes([case['profile']])).digest(65536))
    if case['clear_address'] is not None:
        ram[case['clear_address']-BASE] = 0xa5
    return bytes(ram)


class Observer:
    def __init__(self, program):
        self.program = program
        self.cpu = make_cpu(program)
        # The pinned Musashi wrapper has a two-MiB memory span; Unicorn's mapped
        # ports preserve original writes without changing or substituting code.
        self.cpu.mem_map(0x300000, 0x100000)
        self.baseline = self.cpu.context_save()
        self.events, self.boundaries, self.reads, self.pcs = [], [], [], []
        self.error = None

        def code(cpu, pc, size, user):
            self.pcs.append(pc)
            if pc == RETURN:
                cpu.emu_stop()
                return
            if pc in (0xca9e, 0xcaf0, 0x35a2):
                self.boundaries.append(dict(pc=pc, a7=cpu.reg_read(m.UC_M68K_REG_A7),
                    registers=dict(zip(KEYS, (cpu.reg_read(reg)&0xffffffff for reg in REGS)))))
            opcode = int.from_bytes(cpu.mem_read(pc, 2), 'big')
            if opcode == 0x4afc or 0x4e40 <= opcode <= 0x4e4f:
                self.error = dict(kind='trap-or-illegal', pc=pc, opcode=opcode)
                cpu.emu_stop()

        def write(cpu, access, address, size, value, user):
            kind = 'ports' if address in PORTS else 'ram' if BASE <= address and address+size <= BASE+65536 else 'stack' if STACK_START <= address and address+size <= STACK+4 else None
            event = dict(pc=cpu.reg_read(m.UC_M68K_REG_PC), address=address, size=size,
                value=value&((1 << (size*8))-1), kind=kind)
            self.events.append(event)
            if kind is None:
                self.error = dict(kind='unexpected-write', event=event)
                cpu.emu_stop()

        def read(cpu, access, address, size, value, user):
            if not (address+size <= BASE or BASE <= address and address+size <= BASE+65536 or STACK_START <= address and address+size <= STACK+4):
                self.reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC), address=address, size=size))

        def invalid(cpu, access, address, size, value, user):
            self.error = dict(kind='invalid-memory', access=access, address=address, size=size,
                pc=cpu.reg_read(m.UC_M68K_REG_PC))
            return False

        def intr(cpu, number, user):
            self.error = dict(kind='cpu-exception', number=number, pc=cpu.reg_read(m.UC_M68K_REG_PC))
            cpu.emu_stop()

        self.cpu.hook_add(UC_HOOK_CODE, code)
        self.cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        self.cpu.hook_add(UC_HOOK_MEM_READ, read)
        self.cpu.hook_add(UC_HOOK_MEM_INVALID, invalid)
        self.cpu.hook_add(UC_HOOK_INTR, intr)

    def run(self, case, ram):
        cpu = self.cpu
        cpu.context_restore(self.baseline)
        cpu.mem_write(BASE, ram)
        stack_fill = bytes([0x5a])*4100
        cpu.mem_write(STACK_START, stack_fill)
        cpu.mem_write(STACK, RETURN.to_bytes(4, 'big'))
        # Supervisor selection precedes A7 to avoid switching to a stale SP.
        cpu.reg_write(m.UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(m.UC_M68K_REG_A7, STACK)
        for key, reg in zip(KEYS, REGS):
            cpu.reg_write(reg, case['incoming'][key])
        self.events.clear(); self.boundaries.clear(); self.reads.clear(); self.pcs.clear(); self.error = None
        try:
            cpu.emu_start(case['entry'], 0xffffff, count=CAP)
        except unicorn.UcError as exc:
            if self.error is None:
                self.error = dict(kind='emulator-error', error=str(exc), pc=cpu.reg_read(m.UC_M68K_REG_PC))
        pc = cpu.reg_read(m.UC_M68K_REG_PC)
        if pc != RETURN and self.error is None:
            self.error = dict(kind='instruction-cap', pc=pc, cap=CAP)
        assert self.error is None, self.error
        assert cpu.reg_read(m.UC_M68K_REG_A7) == STACK+4
        assert bytes(cpu.mem_read(STACK, 4)) == RETURN.to_bytes(4, 'big')
        stack_events = [event for event in self.events if event['kind'] == 'stack']
        lowest = min([event['address'] for event in stack_events]+[STACK])
        assert bytes(cpu.mem_read(STACK_START, lowest-STACK_START)) == stack_fill[:lowest-STACK_START]
        assert bytes(cpu.mem_read(0, BASE)) == self.program[:BASE]
        assert not self.reads, self.reads
        output = bytes(cpu.mem_read(BASE, 65536))
        replay = bytearray(ram)
        for event in self.events:
            if event['kind'] == 'ram':
                offset = event['address']-BASE
                replay[offset:offset+event['size']] = event['value'].to_bytes(event['size'], 'big')
        assert bytes(replay) == output
        result = dict(zip(KEYS, (cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        ports = b''.join(struct.pack('>BII', event['size'], event['address'], event['value']) for event in self.events if event['kind'] == 'ports')
        info = dict(returned=True, final_pc=pc, final_a7=cpu.reg_read(m.UC_M68K_REG_A7),
            instructions=len(self.pcs), lowest_stack_write=lowest, stack_write_count=len(stack_events),
            RAM_writes=[event for event in self.events if event['kind'] == 'ram'], boundaries=self.boundaries.copy(),
            calls=dict(collections.Counter(hex(row['pc']) for row in self.boundaries)), unexpected_reads=self.reads.copy())
        return output, result, ports, self.events.copy(), info


def assert_contract(case, ram, output, result, ports, info):
    incoming = case['incoming']
    expected = dict(incoming)
    expected.update(d0=0x7580ff02 if case['entry'] == 0xca9e else 0x75807500,
        d1=0 if case['entry'] == 0xca9e else 0x7000, a4=0x3c0000)
    if case['entry'] == 0xca9e:
        expected['d7'] = (incoming['d7']&0xffff0000)|0xffff
        assert output == ram and info['RAM_writes'] == []
        assert [row['pc'] for row in info['boundaries']] == [0xca9e]
        assert len(ports)//9 == 773
    else:
        expected.update(d2=0, d3=32, d6=incoming['d6']&0xffff0000, d7=0x75007000)
        changed = bytearray(ram)
        changed[case['clear_address']-BASE] = 0
        assert output == changed
        assert len(info['RAM_writes']) == 1 and info['RAM_writes'][0]['address'] == case['clear_address'] and info['RAM_writes'][0]['size'] == 1 and info['RAM_writes'][0]['value'] == 0
        assert [row['pc'] for row in info['boundaries']] == [0xcaf0, 0xca9e]+[0x35a2]*5
        assert len(ports)//9 == 2072
        events = [struct.unpack_from('>BII', ports, i) for i in range(0, len(ports), 9)]
        assert [event for event in events if event[1] == 0x300001] == [(1, 0x300001, value) for value in (0x21, 0x1f, 0, 0, 0xe0)]
        assert [event for event in events if event[1] == 0x3c0004] == [(2, 0x3c0004, 0)]*5
        observed_rectangles = [[row['registers'][key]&65535 for key in ('d0', 'd1', 'd2', 'd3')] for row in info['boundaries'] if row['pc'] == 0x35a2]
        assert observed_rectangles == [[0x7021, 0xff, 38, 30], [0x701f, 0x7000, 40, 1], [0x7000, 0x7000, 40, 1], [0x7000, 0x7000, 1, 32], [0x74e0, 0x7000, 1, 32]]
    assert result == expected, dict(incoming=incoming, expected=expected, actual=result)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert sha(program) == SOURCE_SHA256 == source['sha256']
    folder = root/'artifacts/screen_reset_full'
    folder.mkdir(parents=True, exist_ok=True)
    report = folder/'observation.json'
    report.unlink(missing_ok=True)
    inputs = {name: sha((root/name).read_bytes()) for name in ('tools/observe_screen_reset_full.py', 'tools/verify_object_reset.py', 'tools/observe_scene_frame_execution.py', 'docs/analysis/screen-reset-full-contract.md', 'artifacts/screen_reset_full_static.json')}
    oracle = oracle_provenance()
    observer = Observer(program)
    rows, mismatches = [], []
    for index, case in enumerate(build_cases()):
        ram = fixture(case)
        output, result, ports, events, info = observer.run(case, ram)
        try:
            assert_contract(case, ram, output, result, ports, info)
        except AssertionError as exc:
            mismatches.append(dict(case_index=index, error=repr(exc)))
        files = dict(input_ram_file='input_%02d.bin'%index, ram_file='native_%02d.bin'%index,
            ports_file='native_%02d.ports.bin'%index, writes_file='native_%02d.writes.json'%index)
        for key, data in (('input_ram_file', ram), ('ram_file', output), ('ports_file', ports),
                ('writes_file', (json.dumps(events, indent=2)+'\n').encode())):
            (folder/files[key]).write_bytes(data)
        rows.append(dict(case_index=index, fixture=case, result=result, input_ram_sha256=sha(ram),
            ram_sha256=sha(output), ports_sha256=sha(ports), writes_sha256=sha((folder/files['writes_file']).read_bytes()),
            port_count=len(ports)//9, **files, **info))
    assert inputs == {name: sha((root/name).read_bytes()) for name in inputs}
    assert sha((root/source['path']).read_bytes()) == SOURCE_SHA256
    result = dict(source=source, oracle=oracle, inputs=inputs, cases=len(rows), completed_cases=len(rows),
        contract_mismatches=mismatches, total_native_ports=sum(row['port_count'] for row in rows),
        source_program_modified=False, in_call_SR_read=False, full_RAM_15_registers_ordered_ports_observed=True,
        Cpp_comparison_performed=False, results=rows,
        scope='Original unpatchedca9e/caf0 through all35a2 calls toRTS; full64KiBRAM15regs/all ordered MMIO and RAM/stack writes. Fourfull-register profiles, arbitraryca9e A5 and valid alternatecaf0 A5-relative RAMdestinations. SRset beforeA7; no in-callSRreads, no code/context substitutions. Final register constants are assertions against native observations only. No C++comparison, rendering/physicalmirror/CCR/cycle/scheduler equivalence claim.')
    report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), contract_mismatches=len(mismatches), ports=result['total_native_ports'], sha256=sha(report.read_bytes()))))
    if mismatches:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
