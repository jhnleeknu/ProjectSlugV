"""Observe canonical scene opcode08 on the unmodified M68000 program.

This records native behavior only; it makes no C++ equivalence claim.
"""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID, UC_HOOK_INTR
from unicorn import m68k_const as m
from disassemble_program import load_verified_program
from pack_scene_scripts import command_span
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource

BASE, STACK, RETURN, ENTRY = 0x100000, 0x1feffc, 0xff000, 0x1a0b6
KEYS = tuple('d'+str(index) for index in range(8)) + ('a0', 'a1', 'a2', 'a4')
REGS = tuple(getattr(m, 'UC_M68K_REG_'+key.upper()) for key in KEYS)
CALLS = (0x43f3e, 0xccd6, 0x1ad9a, 0x43efa, 0x440c8, 0x16f9a,
         0x1829a, 0x1701a, 0x182d0, 0x4410c, 0xcd1c)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    scripts = root/'extracted/runtime/scene_scripts'
    manifest = json.loads((scripts/'manifest.json').read_text())
    commands = []
    for item in manifest['scripts']:
        start = item['source_cpu_address']
        end, decoded, terminator = command_span(program, start)
        checked_resource(scripts/item['file'], program, start, end)
        commands.extend((item['file'], command) for command in decoded if command['opcode'] == 8)
    assert len(commands) == 41
    folder = root/'artifacts/scene_setup'
    folder.mkdir(parents=True, exist_ok=True)
    report = folder/'native_observation.json'
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x300000)
    rows, ports, calls, transitions = [], [], [], []
    state = {'bank': 0x200000, 'failure': None, 'instructions': 0}

    def code(cpu, address, size, user):
        state['instructions'] += 1
        if address == RETURN:
            cpu.emu_stop()
            return
        if address in CALLS:
            calls.append(address)
        word = int.from_bytes(cpu.mem_read(address, 2), 'big')
        if 0x4e40 <= word <= 0x4e4f or word == 0x4afc:
            state['failure'] = {'kind': 'trap-or-illegal-instruction', 'pc': address,
                                'word': word}
            cpu.emu_stop()

    def write(cpu, access, address, size, value, user):
        value &= (1 << (size * 8)) - 1
        if BASE <= address and address + size <= BASE + 65536:
            return
        if STACK - 4096 <= address and address + size <= STACK + 4:
            return
        ports.append((size, address, value))
        if address == 0x2ffff2:
            if size != 2 or value not in (0x1000, 0x2000):
                state['failure'] = {'kind': 'unsupported-pvc-bank-write',
                                    'address': address, 'size': size, 'value': value}
                cpu.emu_stop()
                return
            state['bank'] = 0x200000 if value == 0x1000 else 0x300000
            cpu.mem_write(0x200000, program[state['bank']:state['bank'] + 0xffff0])
            transitions.append({'port_index': len(ports)-1, 'source_rom_offset': state['bank']})
        elif not 0x2ffff0 <= address < 0x500000:
            state['failure'] = {'kind': 'unexpected-write-outside-workram-stack-mmio',
                                'address': address, 'size': size, 'value': value}
            cpu.emu_stop()

    def invalid(cpu, access, address, size, value, user):
        state['failure'] = {'kind': 'invalid-memory-access', 'access': access,
                            'address': address, 'size': size, 'value': value}
        return False

    def interrupt(cpu, number, user):
        state['failure'] = {'kind': 'cpu-exception', 'number': number,
                            'pc': cpu.reg_read(m.UC_M68K_REG_PC)}
        cpu.emu_stop()

    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    cpu.hook_add(UC_HOOK_MEM_INVALID, invalid)
    cpu.hook_add(UC_HOOK_INTR, interrupt)
    highs = ((0,)*12, (0xabcd1234,0xfedcba98,0x98765432,0x87654321,
             0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,
             0,0xcafebabe,0xface1234))

    def save():
        result = dict(source=source, emulator='Unicorn '+unicorn.__version__,
            dispatcher_cpu_address=ENTRY, canonical_opcode08_occurrences=41,
            cases=len(rows), completed_cases=sum(row['returned'] for row in rows),
            total_ports=sum(row['port_count'] for row in rows), results=rows,
            failure=state['failure'], cpp_equivalence_claimed=False,
            fixed_rom_immutable=bytes(cpu.mem_read(0,0x100000)) == program[:0x100000],
            physical_bank_immutable=bytes(cpu.mem_read(0x200000,0xffff0)) == program[state['bank']:state['bank']+0xffff0],
            bank_mapping_scope='PVC word1000/2000 selects source ROM2MiB/3MiB at physical200000..2fffef; MMIO register tail excluded. Only these observed bank words modeled.',
            scope='Standalone canonical commands through actual original dispatcher/callees to RTS. Random RAM and high registers are controlled fixtures; A5=108000,A3/A6=0,external stack1feffc. No ROM patch/stub, natural scheduler, full scene playback or C++ comparison.')
        report.write_text(json.dumps(result, indent=2)+'\n')
        return hashlib.sha256(report.read_bytes()).hexdigest()

    for file, command in commands:
        for seed, profile in itertools.product((0,1), range(2)):
            ram = hashlib.shake_256(b'scene-setup-observation'+bytes([seed])).digest(65536)
            cpu.mem_write(BASE, ram)
            state.update(bank=0x200000, failure=None, instructions=0)
            cpu.mem_write(0x200000, program[0x200000:0x2ffff0])
            cpu.reg_write(m.UC_M68K_REG_A5, 0x108000)
            cpu.reg_write(m.UC_M68K_REG_A3, 0)
            cpu.reg_write(m.UC_M68K_REG_A6, 0)
            cpu.reg_write(m.UC_M68K_REG_A7, STACK)
            cpu.reg_write(m.UC_M68K_REG_SR, 0x2000)
            cpu.mem_write(STACK, RETURN.to_bytes(4,'big'))
            values = list(highs[profile]); values[9] = command['source_cpu_address']
            for register, value in zip(REGS, values):
                cpu.reg_write(register, value)
            ports.clear(); calls.clear(); transitions.clear()
            try:
                cpu.emu_start(ENTRY, 0xffffff, count=2000000)
            except unicorn.UcError as error:
                if state['failure'] is None:
                    state['failure'] = {'kind': 'emulator-error', 'message': str(error)}
            returned = cpu.reg_read(m.UC_M68K_REG_PC) == RETURN
            if not returned and state['failure'] is None:
                state['failure'] = {'kind': 'instruction-budget-exhausted'}
            output = bytes(cpu.mem_read(BASE, 65536))
            packed = b''.join(struct.pack('>BII', *event) for event in ports)
            name = 'case-%03d.ports.bin' % len(rows)
            (folder/name).write_bytes(packed)
            rows.append(dict(script_file=file, command=command, ram_seed=seed,
                register_profile=profile, incoming=dict(zip(KEYS,values)),
                final_registers={key:cpu.reg_read(getattr(m,'UC_M68K_REG_'+key.upper()))&0xffffffff
                    for key in tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(8))},
                final_pc=cpu.reg_read(m.UC_M68K_REG_PC), returned=returned,
                native_a7_rts_valid=returned and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4,
                input_ram_sha256=hashlib.sha256(ram).hexdigest(), output_ram_sha256=hashlib.sha256(output).hexdigest(),
                changed_ram_bytes=sum(a!=b for a,b in zip(ram,output)),
                port_count=len(ports), ports_file=name, ports_sha256=hashlib.sha256(packed).hexdigest(),
                representative_ports=ports[:8]+ports[-8:] if len(ports)>16 else ports.copy(),
                call_counts={hex(k):v for k,v in sorted(collections.Counter(calls).items())},
                call_order=calls.copy(), bank_transitions=transitions.copy(), instructions=state['instructions']))
            assert bytes(cpu.mem_read(0,0x100000)) == program[:0x100000]
            assert bytes(cpu.mem_read(0x200000,0xffff0)) == program[state['bank']:state['bank']+0xffff0]
            if state['failure']:
                print(json.dumps(dict(cases=len(rows), failure=state['failure'], report_sha256=save())))
                raise SystemExit(1)
            assert rows[-1]['native_a7_rts_valid']
    print(json.dumps(dict(cases=len(rows), ports=sum(row['port_count'] for row in rows), report_sha256=save())))


if __name__ == '__main__':
    main()
