"""Immutable original8cda throughRTS in pinnedMusashi; no C++ comparison."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program, disassemble_range
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from verify_stage_catalog import SOURCE_SHA256

BASE, STACK, RETURN, ENTRY, END = 0x100000, 0x1feffc, 0xff000, 0x8cda, 0x8d34
KEYS = tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(7))
BRANCHES = (0x8cee, 0x8cf8, 0x8d02, 0x8d1c, 0x8d28)
A5_VALUES = (0, 1, 0x108000, 0x100000, 0x7fffffff, 0x80000000, 0xffffffff)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_cases():
    cases = []
    for reference, slot, weight, same_target, same_weight, same_base in itertools.product(
            (0, 1, 0xffff), (0, 1, 12, 255), (0, 31, 32, 33, 255),
            (False, True), (False, True), (False, True)):
        index = len(cases)
        cases.append(dict(reference=reference, slot=slot, incoming_weight=weight,
            target_same=same_target, weight_same=same_weight, base_id_same=same_base,
            profile=index % 3, a5=A5_VALUES[index % len(A5_VALUES)],
            # Do not correlate preexisting dirty bit with base_id_same.
            initial_flag=(0x35, 0xb5)[(index // 8) % 2]))
    assert len(cases) == 480
    return cases


def fixture(case):
    ram = bytearray(hashlib.shake_256(b'palette-blend-full-'+bytes([case['profile']])).digest(65536))
    high = (0, 0xabcd0000, 0xffff0000)[case['profile']]
    regs = [(high+(i+1)*0x10203) & 0xffffffff for i in range(15)]
    regs[0] = high | 0xa500 | case['slot']
    regs[1] = high | 0x0a0d
    regs[2] = high | 0xa500 | case['incoming_weight']
    regs[13] = case['a5']
    at = 0x4d92 + case['slot']*16
    effective = min(case['incoming_weight'], 32)
    previous_weight = effective if case['weight_same'] else (effective+1) & 255
    target = regs[1] & 65535
    struct.pack_into('>HHHBB', ram, at+8, case['reference'],
        target if case['base_id_same'] else target ^ 0xffff,
        target if case['target_same'] else target ^ 0xffff,
        previous_weight, case['initial_flag'])
    return bytes(ram), regs


class Observer:
    def __init__(self, program):
        self.program = program
        self.cpu = MusashiOracle()
        self.cpu.load(0, program[:BASE])
        self.pcs, self.writes = [], []
        self.slot = 0

        def code(pc):
            assert ENTRY <= pc < END, (hex(pc), 'unexpected execution')
            self.pcs.append(pc)

        def write(pc, address, size, value):
            assert (address == self.slot+12 and size == 2) or (
                address in (self.slot+14, self.slot+15) and size == 1), (hex(pc), hex(address), size, value)
            self.writes.append(dict(pc=pc, address=address, size=size, value=value))

        self.cpu.set_instruction_hook(code)
        self.cpu.set_write_hook(write)

    def run(self, case, ram, regs):
        cpu = self.cpu
        cpu.reset()
        cpu.load(BASE, ram)
        # Supervisor switching changes SP, so SR must be set before A7.
        cpu.set_reg('sr', 0x2000)
        cpu.set_reg('a7', STACK)
        cpu.load(STACK, RETURN.to_bytes(4, 'big'))
        for key, value in zip(KEYS, regs):
            cpu.set_reg(key, value)
        cpu.set_reg('pc', ENTRY)
        self.slot = 0x104d92 + case['slot']*16
        self.pcs.clear()
        self.writes.clear()
        guards = ((0, BASE), (BASE+65536, STACK-BASE-65536), (STACK+4, 0x200000-STACK-4))
        before = [cpu.read(address, size) for address, size in guards]
        status = cpu.run(100, RETURN)
        assert status['status'] == 'sentinel' and status['pc'] == RETURN, status
        assert cpu.get_reg('a7') == STACK+4
        assert cpu.read(STACK, 4) == RETURN.to_bytes(4, 'big')
        assert before == [cpu.read(address, size) for address, size in guards]
        assert cpu.read(0, BASE) == self.program[:BASE]
        output = cpu.read(BASE, 65536)
        result = {key:cpu.get_reg(key) for key in KEYS}
        # These are the approved register contract assertions, not a RAM oracle.
        predicted = dict(zip(KEYS, regs))
        predicted['d0'] = (regs[0] & 0xffff0000) | ((regs[0] & 255) << 4)
        predicted['a1'] = 0x104d92
        predicted['a2'] = self.slot
        if case['reference'] and case['incoming_weight'] >= 32:
            predicted['d2'] = 32
        assert result == predicted, (case, result, predicted)
        # All final RAM differences must be explained by actual CPU writes.
        replay = bytearray(ram)
        for item in self.writes:
            at = item['address']-BASE
            replay[at:at+item['size']] = item['value'].to_bytes(item['size'], 'big')
        assert bytes(replay) == output
        assert status['cpu_writes'] == len(self.writes), status
        if not case['reference']:
            assert output == ram and not self.writes
        return output, result, dict(status=status, final_pc=RETURN,
            final_a7=cpu.get_reg('a7'), pcs=self.pcs.copy(), RAM_writes=self.writes.copy())


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root/'artifacts/palette_blend_full'
    folder.mkdir(parents=True, exist_ok=True)
    report = folder/'observation.json'
    report.unlink(missing_ok=True)
    names = ('tools/observe_palette_blend_full.py', 'tools/musashi_oracle.py',
        'tools/observe_scene_motion_pair.py', 'tools/disassemble_program.py',
        'tools/verify_stage_catalog.py', 'docs/analysis/stage-activation-prefix-contract.md')
    inputs = {name:sha((root/name).read_bytes()) for name in names}
    program, source = load_verified_program(root)
    assert sha(program) == SOURCE_SHA256
    instructions = disassemble_range(program, ENTRY, END-ENTRY, ENTRY)
    assert all(row['classification'] == 'candidate_instruction' for row in instructions)
    assert instructions[-1]['cpu_address'] == 0x8d32 and instructions[-1]['raw'] == '4e75'
    oracle = oracle_provenance(root)
    observer = Observer(program)
    rows, branches = [], collections.defaultdict(set)
    total_writes = 0
    for index, case in enumerate(build_cases()):
        ram, regs = fixture(case)
        output, result, info = observer.run(case, ram, regs)
        for pc, next_pc in zip(info['pcs'], info['pcs'][1:]):
            if pc in BRANCHES:
                branches[pc].add(next_pc)
        total_writes += len(info['RAM_writes'])
        input_name, output_name = 'input_%03d.bin'%index, 'native_%03d.bin'%index
        (folder/input_name).write_bytes(ram)
        (folder/output_name).write_bytes(output)
        rows.append(dict(case_index=index, fixture=case, incoming=dict(zip(KEYS, regs)),
            input_ram_file=input_name, input_ram_sha256=sha(ram),
            native_ram_file=output_name, native_ram_sha256=sha(output), result=result, **info))
    assert all(len(branches[pc]) == 2 for pc in BRANCHES), dict(branches)
    assert inputs == {name:sha((root/name).read_bytes()) for name in names}
    assert oracle_provenance(root) == oracle
    assert sha((root/source['path']).read_bytes()) == SOURCE_SHA256
    report.write_text(json.dumps(dict(source=source, oracle=oracle, inputs=inputs,
        entry=ENTRY, return_instruction=0x8d32, cases=len(rows), RAM_write_count=total_writes,
        instructions=instructions, branches={hex(pc):sorted(branches[pc]) for pc in BRANCHES},
        Cpp_comparison_performed=False, native_register_contract_assertions_passed=True,
        full_RAM_captured=True, exact_CPU_write_replay_passed=True,
        program_code_modified=False, in_call_SR_read=False, SR_set_before_A7=True,
        results=rows, scope='Immutable original8cda throughRTS, pinnedMusashiM68000; controlled480case matrix. Full64KiB RAM,15regs and exact ordered CPU writes captured. No ROMpatch/stub/MMIO/resource/CPP comparison. A5 arbitrary and unchanged. Isolatedstack1feffc with sentinelff000; A7/stack native-only, no CCR/cycle/hardwaremirror/rendering/naturalgameclaim.'), indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), RAM_write_count=total_writes,
        branches={hex(pc):sorted(branches[pc]) for pc in BRANCHES},
        sha256=sha(report.read_bytes()))))


if __name__ == '__main__':
    main()
