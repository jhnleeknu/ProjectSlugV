"""Connect native main-frame boundaries and IRQ signals with CLI RAM/full-register carry."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import m68k_const
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256, checked_resource, verify_resources
from verify_frame_gate import zlib_crc

BASE, GATE, PREFIX, CALLBACK, CONTROL, RETURN, LOOP, TRAP, BIOS = (
    0x100000, 0xef2, 0xf12, 0xf3c, 0xf54, 0xff000, 0xec4, 0xfee, 0xc00444)
INPUT_PORTS = (0x380000, 0x300000, 0x340000, 0x300000, 0x340000)
REGS = [getattr(m68k_const, 'UC_M68K_REG_' + kind + str(index)) for kind in ('D', 'A') for index in range(8)]


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    irq_cli, main_cli = root / 'build/step_interrupt', root / 'build/step_input_control'
    streams, status, menu, pause, palettes, font, stages = [root / 'extracted/runtime' / name for name in
        ('input_streams.ms5d', 'input_status.ms5d', 'control_menu_tree.ms5d', 'control_pause.ms5d',
         'palettes.ms5p', 'menu_fonts.ms5d', 'stages')]
    hashes = {'streams': checked_resource(streams, program, 0xf01fe, 0xf1a0e),
        'status': checked_resource(status, program, 0xb58, 0xc58),
        'menu': checked_resource(menu, program, 0x937e, 0x9aa8),
        'pause': checked_resource(pause, program, 0x9068, 0x9086),
        'font': checked_resource(font, program, 0xe80c8, 0xe84c8),
        'null_name': checked_resource(stages / 'stage_null_name.ms5d', program, 0, 4)}
    groups = verify_resources(stages, program, source)
    records, ignored = extract(program)
    payload = b''.join(struct.pack('<I', identifier) + records[identifier][0] + records[identifier][1] for identifier in sorted(records))
    packed = palettes.read_bytes()
    assert packed == struct.pack('<4s7I', b'MS5P', 1, len(records), 68, len(payload), zlib_crc(payload), 0, 0) + payload
    hashes['palettes'] = hashlib.sha256(packed).hexdigest()
    folder = root / 'artifacts/main_frame_flow'
    folder.mkdir(parents=True, exist_ok=True)
    inp, out, ports_out, regs_in, banks_in, banks_out, report = [folder / name for name in
        ('input.bin', 'cpp.bin', 'cpp.ports.bin', 'registers.bin', 'banks.bin', 'cpp.banks.bin', 'verification.json')]
    report.unlink(missing_ok=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.mem_map(0xc00000, 0x1000)
    state = {'stop_pc': None, 'debug_calls': 0, 'cli_d1': None, 'cli_d3': None, 'cli_pc':None, 'entry':None, 'entry_visits':0, 'mode': 'setup', 'visits': 0, 'video': 0, 'video_reads': 0, 'sound_reads': 0}
    ports, reads, trace, rows, sequences, ordered_reads = [], [], [], [], [], []
    samples = []

    def read(cpu, access, address, size, value, user):
        if address == 0x320000:
            assert state['mode'] == 'irq' and size == 1
            state['sound_reads'] += 1
            ordered_reads.append((1,address,0))
            cpu.mem_write(address, b'\0')
        elif address == 0x3c0006:
            assert state['mode'] == 'main' and size == 2
            state['video_reads'] += 1
            ordered_reads.append((2,address,state['video']))
            cpu.mem_write(address, state['video'].to_bytes(2, 'big'))
        elif address in INPUT_PORTS:
            ordinal = len(reads)
            assert state['mode'] == 'main' and ordinal < len(samples) and address == INPUT_PORTS[ordinal] and size == 1
            cpu.mem_write(address, bytes([samples[ordinal]]))
            reads.append((address, samples[ordinal]))
            ordered_reads.append((1,address,samples[ordinal]))

    def write(cpu, access, address, size, value, user):
        if address in (0x300001, 0x320000, 0x2ffff0, 0x2ffff2, 0x3a0001) or 0x3c0000 <= address < 0x3c0010:
            ports.append((size, address, value & ((1 << (size * 8)) - 1)))
        elif not (BASE <= address and address + size <= BASE + 65536) and not (0x1fb000 <= address and address + size <= 0x1ff000):
            raise ValueError('Unexpected native write: ' + repr((hex(address), size, value)))

    def code(cpu, address, size, user):
        if state['mode']=='main':
            if address==LOOP:
                if state['entry']==LOOP and state['entry_visits']==0:
                    state['entry_visits']+=1
                    state['debug_calls']+=1
                else:
                    cpu.emu_stop()
                    return
            elif address in (GATE,0xf4c):
                state['visits']+=1
                if state['visits']==2:
                    cpu.emu_stop()
                    return
            if address==0x3a70 and state['entry']==LOOP and not state['prefix_started']:
                state['debug_formatter_calls']+=1
            if address==PREFIX: state['prefix_started']=True
            if address in (PREFIX,CALLBACK,CONTROL):
                trace.append({'pc':address,'d1':cpu.reg_read(REGS[1]),'d3':cpu.reg_read(REGS[3]),'a1':cpu.reg_read(REGS[9]),'a6':cpu.reg_read(REGS[14]),'a7':cpu.reg_read(REGS[15])})
            if address in (CALLBACK,TRAP,BIOS,RETURN): cpu.emu_stop()
        elif state['mode']=='irq' and address==RETURN:
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_MEM_READ, read, begin=0x300000, end=0x3c0007)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write)
    cpu.hook_add(UC_HOOK_CODE, code)
    cpu.mem_write(BASE, bytes(65536))
    cpu.reg_write(m68k_const.UC_M68K_REG_A5, 0x108000)
    cpu.reg_write(m68k_const.UC_M68K_REG_A7, 0x1feffc)
    cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
    cpu.emu_start(0x3ef2, RETURN, count=10000)
    assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == RETURN
    allocated = bytes(cpu.mem_read(BASE, 65536))

    def fixture(threshold, signal=0, callback=0, guard=0, pointer=0x100001):
        ram = bytearray(allocated)
        for slot in range(256):
            node = 0x4d92 + slot * 16
            struct.pack_into('>HH', ram, node + 10, 0x203, 0x87a if slot & 1 else 0x203)
            ram[node + 14], ram[node + 15] = slot & 31, 0x80 | (slot & 3)
        ram[0x7df0], ram[0xfdaf], ram[0xf000], ram[0xf002] = 0, 2, 2, 1
        ram[0xfdb6:0xfdba] = b'\1\1\1\1'
        ram[0x4cd2], ram[0x4cd3] = 15, 4
        struct.pack_into('>I', ram, 0x4cc4, 0xf01fe)
        struct.pack_into('>H', ram, 0x4cc2, 0x1234)
        struct.pack_into('>HH', ram, 0x4ccc, 0, 0)
        ram[0x4cd0] = 0
        struct.pack_into('>H', ram, 0x4d90, 0xfff7)
        struct.pack_into('>H', ram, 0xe, 0xffff)
        struct.pack_into('>H', ram, 0xf5c + 0x7e, 0xffff)
        ram[0xf5c + 0x84] = 1
        struct.pack_into('>II', ram, 0xf5c + 0x76, callback, 0xdeadbeef)
        ram[0x16], ram[0x17], ram[0x18], ram[0x19], ram[0x1b] = signal, threshold, 0xa5, guard, 0x7f
        struct.pack_into('>I', ram, 0x81c, pointer)
        struct.pack_into('>H', ram, 0xd68c, 0)
        struct.pack_into('>HH', ram, 0x4d74, 0, 0)
        ram[0x4d7b], ram[0xf003], ram[0x14] = 0, 0, 0
        return ram

    def new_main_context(ram, style=0xff6b, line=0x7000, entry=LOOP):
        cpu.mem_write(BASE, bytes(ram))
        for reg, value in ((m68k_const.UC_M68K_REG_SR, 0x2000), (m68k_const.UC_M68K_REG_A5, 0x108000),
                (m68k_const.UC_M68K_REG_A6, 0x100f5c), (m68k_const.UC_M68K_REG_A7, 0x1feffc),
                (m68k_const.UC_M68K_REG_D0, 0x12345678), (m68k_const.UC_M68K_REG_D1, 0xbeef0000 | style),
                (m68k_const.UC_M68K_REG_D3, 0xcafe0000|line), (m68k_const.UC_M68K_REG_A1, 0xdeadbeef)):
            cpu.reg_write(reg, value)
        cpu.mem_write(0x1feffc, RETURN.to_bytes(4, 'big'))
        state['cli_d1'],state['cli_d3'],state['cli_pc']=0xbeef0000|style,0xcafe0000|line,entry
        cpu.reg_write(m68k_const.UC_M68K_REG_PC,entry)
        return cpu.context_save()

    def arguments(incoming,current_samples,entry,video):
        return [str(main_cli),'--main',str(entry),str(debug_resource),str(video),'--registers',str(state['cli_d1']),str(state['cli_d3']),str(inp),str(streams),str(status),str(menu),str(pause),str(palettes),str(out),str(ports_out),str(incoming[14]),str(state['cli_d1']&65535),str(state['cli_d3']&65535),str(incoming[15])]+[str(value) for value in current_samples]+[str(font),str(stages)]

    def main_call(ram,context,video,current_samples,profile):
        cpu.mem_write(BASE,bytes(ram))
        cpu.context_restore(context)
        incoming=[cpu.reg_read(reg)&0xffffffff for reg in REGS]
        assert incoming[1]==state['cli_d1'] and incoming[3]==state['cli_d3']
        entry=state['cli_pc']
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC)==entry
        prior_debug_calls=state['debug_calls']
        state.update(mode='main',entry=entry,entry_visits=0,visits=0,video=video,video_reads=0,sound_reads=0)
        samples[:]=current_samples[:5 if ram[0x4cd4]==0 else 3]
        state['prefix_started'],state['debug_formatter_calls']=False,0
        ports.clear();reads.clear();trace.clear();ordered_reads.clear()
        command=arguments(incoming,current_samples,entry,video)
        cpu.emu_start(entry,RETURN,count=12000000)
        ready=entry==PREFIX or (ram[0x16]!=0 if entry==0xf4c else ram[0x16]>=ram[0x17])
        pc=cpu.reg_read(m68k_const.UC_M68K_REG_PC)
        expected=bytes(cpu.mem_read(BASE,65536))
        assert state['debug_calls']-prior_debug_calls==int(entry==LOOP)
        assert state['debug_formatter_calls']==int(entry==LOOP and bool(ram[0xf000]&1) and bool(ram[0xf5c+0x84]))
        assert state['video_reads']==int(ready and entry in (LOOP,GATE)) and not state['sound_reads']
        prefix=[item for item in trace if item['pc'] in (CALLBACK,CONTROL)]
        if ready:
            assert len(prefix)==1 and prefix[0]['a1']==0xb58 and prefix[0]['a6']==incoming[14] and prefix[0]['a7']==incoming[15]
            assert expected[0x1a]==ram[0x16] and expected[0x16]==0
            callback=struct.unpack_from('>I',expected,0xf5c+0x76)[0] if pc==CALLBACK else 0
            callback_context=struct.unpack_from('>I',expected,0xf5c+0x7a)[0] if callback else 0
            style=prefix[0]['d1']&65535
            assert len(reads)==len(samples)
        else:
            assert pc in (GATE,0xf4c) and not reads and not trace
            callback,callback_context,style=0,0,cpu.reg_read(REGS[1])&65535
            if entry!=LOOP: assert expected==ram and not ports
        if entry==0xf4c: assert expected[0x18]==ram[0x18]
        assert ordered_reads==([(2,0x3c0006,video)] if ready and entry in (LOOP,GATE) else [])+[(1,address,value) for address,value in reads]
        result={'next_pc':0 if pc==RETURN else pc,'callback':callback,'callback_context':callback_context,'style':style,'read_count':len(reads),'d1':cpu.reg_read(REGS[1])&0xffffffff,'d3':cpu.reg_read(REGS[3])&0xffffffff}
        expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        inp.write_bytes(ram)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert not actual.returncode,(profile,actual.stderr)
        parsed=json.loads(actual.stdout)
        if out.read_bytes()!=expected or ports_out.read_bytes()!=expected_ports or parsed!=result:
            differences=[(hex(at),expected[at],out.read_bytes()[at]) for at in range(65536) if expected[at]!=out.read_bytes()[at]]
            raise ValueError(repr((len(rows),profile,entry,differences[:16],result,actual.stdout,actual.stderr)))
        state['cli_d1'],state['cli_d3'],state['cli_pc']=parsed['d1'],parsed['d3'],parsed['next_pc']
        assert [cpu.reg_read(REGS[index])&0xffffffff for index in (1,3)]==[state['cli_d1'],state['cli_d3']]
        rows.append({'kind':'main','profile':profile,'entry':entry,'initial_signal':ram[0x16],'threshold':ram[0x17],'ready':ready,'video':video,'video_reads':state['video_reads'],'input_reads':reads.copy(),'ordered_reads':ordered_reads.copy(),'ports':len(ports),'ec4_entry_count':state['debug_calls']-prior_debug_calls,'debug_formatter_calls':state['debug_formatter_calls'],'incoming_d1':incoming[1],'incoming_d3':incoming[3],'result':parsed,'ram_sha256':hashlib.sha256(expected).hexdigest(),'ports_sha256':hashlib.sha256(expected_ports).hexdigest()})
        # Equality is already proved; explicitly carry the C++ register outputs.
        cpu.reg_write(REGS[1],parsed['d1'])
        cpu.reg_write(REGS[3],parsed['d3'])
        return bytearray(out.read_bytes()),cpu.context_save(),ready

    def interrupt(ram, main_context, profile):
        cpu.mem_write(BASE, bytes(ram))
        cpu.context_restore(main_context)
        main_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        registers = list(struct.unpack('>16I', hashlib.shake_256(b'frame-flow-irq-regs:' + len(rows).to_bytes(4, 'big')).digest(64)))
        registers[0], registers[13], registers[15] = 0xabcd0000 | (len(rows) & 255), 0x108000, 0x1fcffc
        cpu.reg_write(m68k_const.UC_M68K_REG_SR, 0x2000)
        for reg, value in zip(REGS, registers):
            cpu.reg_write(reg, value)
        cpu.mem_write(registers[15], RETURN.to_bytes(4, 'big'))
        state.update(mode='irq', stop_pc=None, video_reads=0, sound_reads=0)
        ports.clear()
        reads.clear()
        trace.clear()
        ordered_reads.clear()
        cpu.emu_start(0xc8c, RETURN, count=100000)
        assert cpu.reg_read(m68k_const.UC_M68K_REG_PC) == RETURN and not reads and not state['video_reads']
        expected = bytes(cpu.mem_read(BASE, 65536))
        reentrant = bool(ram[0x19] & 128)
        assert state['sound_reads'] == int(not reentrant)
        assert expected[0x16] == (ram[0x16] if reentrant else min(255, ram[0x16] + 1))
        expected_ports = b''.join(struct.pack('>BII', *event) for event in ports)
        result = {'service_phase': 1 if reentrant else 0, 'display_bank': 0, 'sound_reads': state['sound_reads'],
            'task_registers': [0] * 16, 'task': {'next_pc': 0, 'restored': False, 'stack_address': [0, 0], 'stack_value': [0, 0]},
            'pending': dict.fromkeys(('kind', 'phase', 'low', 'cursor', 'command', 'tail', 'next'), 0)}
        banks = hashlib.shake_256(b'frame-flow-unused-banks').digest(16384)
        inp.write_bytes(ram)
        banks_in.write_bytes(banks)
        regs_in.write_bytes(struct.pack('>16I', *registers))
        for path in (out, banks_out, ports_out):
            path.unlink(missing_ok=True)
        actual = subprocess.run([str(irq_cli), 'begin', str(inp), str(banks_in), str(regs_in), str(out), str(banks_out), str(ports_out), '0', '0'], capture_output=True, text=True)
        assert not actual.returncode and out.read_bytes() == expected and banks_out.read_bytes() == banks and ports_out.read_bytes() == expected_ports and json.loads(actual.stdout) == result, (profile, actual.stdout, actual.stderr)
        cpu.context_restore(main_context)
        restored_main_registers = [cpu.reg_read(reg) & 0xffffffff for reg in REGS]
        assert restored_main_registers == main_registers
        rows.append({'kind': 'irq', 'profile': profile, 'initial_signal': ram[0x16], 'result_signal': expected[0x16],
            'reentrant': reentrant, 'sound_reads': state['sound_reads'], 'ports': len(ports),
            'main_d1_preserved': main_registers[1], 'main_a6_preserved': main_registers[14],
            'all_main_registers_restored_by_host_context': True, 'result': result,
            'ram_sha256': hashlib.sha256(expected).hexdigest(), 'ports_sha256': hashlib.sha256(expected_ports).hexdigest()})
        return bytearray(out.read_bytes()), cpu.context_save()

    debug_resource = root / 'extracted/runtime/main_debug.ms5d'
    hashes['debug'] = checked_resource(debug_resource, program, 0xd56, 0xe40)

    for debug_flag,status_byte,callback,mode,threshold in ((0,1,0xdeadbeef,0,2),(1,0,0xdeadbeef,2,1),(1,1,0xdeadbeef,1,3),(1,255,0,0,2)):
        ram=fixture(threshold,callback=callback)
        ram[0xf000],ram[0xf5c+0x84],ram[0x4cd4]=debug_flag,status_byte,mode
        if not callback: ram[0x7df1]=1
        context=new_main_context(ram,style=(0xf6b,0x9a17,0xa568,0xf30)[len(sequences)%4],line=0x1234)
        begin=len(rows)
        ram,context,ready=main_call(ram,context,0xffff,[255]*5,'ec4-debug-once-then-wait')
        assert not ready
        ram,context,ready=main_call(ram,context,0x8888,[255]*5,'waiting-does-not-rerun-debug')
        assert not ready
        for tick in range(threshold):
            ram,context=interrupt(ram,context,'actual-irq-main-wait-release')
            ram,context,ready=main_call(ram,context,0x3200+tick*128,[255,254,253,252,251],'irq-count-then-input')
            assert ready==(tick==threshold-1)
        if not callback:
            assert state['cli_pc']==LOOP
            for frame in range(2):
                ram,context,ready=main_call(ram,context,0x4000,[255]*5,'next-ec4-with-cpp-full-register-outputs')
                assert not ready
                for tick in range(threshold):
                    ram,context=interrupt(ram,context,'next-frame-actual-irq')
                    ram,context,ready=main_call(ram,context,0x4000,[255]*5,'next-frame-cpp-context-carry')
                    assert ready==(tick==threshold-1)
                assert state['cli_pc']==LOOP
        sequences.append({'profile':'debug-irq-input-cpp-carry','calls':len(rows)-begin,'callback':bool(callback),'cpp_full_d1_d3_and_ram_carried':True,'no_native_main_register_reset_between_calls':True,'signal_generated_only_by_actual_irq_after_initial_fixture':True})
    for mode,replay in ((0,'live'),(1,'event'),(1,'noevent'),(1,'terminal'),(2,'live')):
        ram=fixture(255,callback=0xdeadbeef)
        ram[0x4cd4]=mode
        struct.pack_into('>HH',ram,0x4ccc,0,0x5ff if replay=='terminal' else 0)
        struct.pack_into('>I',ram,0x4cc4,0xf07fe if replay=='terminal' else 0xf01fe)
        ram[0x4cd0]=255 if replay=='terminal' else 1 if replay=='noevent' else 0
        context=new_main_context(ram,entry=PREFIX)
        ram,context,ready=main_call(ram,context,0xffff,[3,17,29,43,61],'direct-f12-mode-'+str(mode)+'-'+replay)
        assert ready and state['cli_pc']==CALLBACK
    ram=fixture(255,callback=0xdeadbeef)
    context=new_main_context(ram,entry=0xf4c)
    begin=len(rows)
    ram,context,ready=main_call(ram,context,0xffff,[255]*5,'f4c-waits-without-video')
    assert not ready
    ram,context=interrupt(ram,context,'irq-releases-callback-wait-below-threshold')
    ram,context,ready=main_call(ram,context,0xffff,[3,17,29,43,61],'f4c-ignores-threshold-no-video')
    assert ready and state['cli_pc']==CALLBACK
    sequences.append({'profile':'callback-wait-irq-cpp-carry','calls':len(rows)-begin,'cpp_full_d1_d3_and_ram_carried':True,'signal_generated_only_by_actual_irq_after_initial_fixture':True})
    ram=fixture(1,callback=0xdeadbeef,guard=0x80)
    context=new_main_context(ram)
    begin=len(rows)
    ram,context,ready=main_call(ram,context,0xffff,[255]*5,'reentrant-initial-wait')
    ram,context=interrupt(ram,context,'reentrant-does-not-produce-signal')
    ram,context,ready=main_call(ram,context,0xffff,[255]*5,'still-waiting-after-reentrant-service')
    assert not ready
    ram[0x19]=0 # Explicit host release of service guard; no signal injection.
    ram,context=interrupt(ram,context,'released-guard-produces-signal')
    ram,context,ready=main_call(ram,context,0xffff,[255]*5,'ready-after-service-guard-release')
    assert ready
    sequences.append({'profile':'reentrant-service','calls':len(rows)-begin,'host_releases_guard19':True,'cpp_full_d1_d3_and_ram_carried':True})
    ram=fixture(255,signal=254,callback=0xdeadbeef)
    context=new_main_context(ram)
    ram,context,ready=main_call(ram,context,0xffff,[255]*5,'saturation-initial-wait')
    assert not ready
    for _ in range(2): ram,context=interrupt(ram,context,'irq-saturates-count255')
    ram,context,ready=main_call(ram,context,0xffff,[255]*5,'saturated-count-releases-input')
    assert ready and ram[0x1a]==255
    for selected in (4,5):
        ram=fixture(0)
        ram[0x7df0],ram[0x7dee]=3,255
        struct.pack_into('>III',ram,0x7f0e,0x107efe,0x107efe,0x9332)
        struct.pack_into('>I',ram,0x7efe,0x93e0)
        ram[0x7f02:0x7f0e]=bytes((12,0,6,selected,selected,4,8,24,12,3,3,0))
        struct.pack_into('>H',ram,0x8f4,0)
        ram[0x901],ram[0x950]=0,255
        context=new_main_context(ram,entry=PREFIX)
        ram,context,ready=main_call(ram,context,0xffff,[255]*5,'native-static-restart-or-bios')
        assert ready and state['cli_pc']==(LOOP if selected==4 else BIOS)
    ram=fixture(0)
    ram[0x7df0]=1
    ram[0xf]^=1
    context=new_main_context(ram,entry=PREFIX)
    ram,context,ready=main_call(ram,context,0xffff,[254,255,255,255,255],'native-counter-trap-boundary')
    assert ready and state['cli_pc']==TRAP
    negatives=[]
    sentinel=b'previous-main-frame-output\0\xff'
    ram=fixture(0)
    ram[0xf000]=3
    struct.pack_into('>HH',ram,0x4d92+10,0xfffe,0xfffe)
    ram[0x4d92+15]=0x80
    context=new_main_context(ram)
    incoming=[cpu.reg_read(reg)&0xffffffff for reg in REGS]
    command=arguments(incoming,[253,255,255,255,255],LOOP,0xffff)
    inp.write_bytes(ram);out.write_bytes(sentinel);ports_out.write_bytes(sentinel)
    actual=subprocess.run(command,capture_output=True,text=True)
    assert actual.returncode and out.read_bytes()==sentinel and ports_out.read_bytes()==sentinel
    negatives.append({'failure':'late-palette-after-debug-gate-input-controller','outputs_preserved':True,'original_executed':False})
    for invalid in ('0','0xf13','-1','4294967296','0x100000000','0x','1x',''):
        command=arguments(incoming,[255]*5,LOOP,0xffff)
        command[2]=invalid
        inp.write_bytes(fixture(2));out.write_bytes(sentinel);ports_out.write_bytes(sentinel)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and ports_out.read_bytes()==sentinel
        negatives.append({'failure':'invalid-main-entry','outputs_preserved':True,'original_executed':False})
    for label,command in (
            ('missing-register-option',arguments(incoming,[255]*5,LOOP,0xffff)),
            ('exclusive-main-poll',arguments(incoming,[255]*5,LOOP,0xffff)),
            ('duplicate-main-option',arguments(incoming,[255]*5,LOOP,0xffff)),
            ('invalid-video-overflow',arguments(incoming,[255]*5,LOOP,0xffff))):
        if label=='missing-register-option': del command[5:8]
        elif label=='exclusive-main-poll': command[5:5]=['--poll','0']
        elif label=='duplicate-main-option': command[5:5]=['--main',str(LOOP),str(debug_resource),'0']
        else: command[4]='65536'
        inp.write_bytes(fixture(2));out.write_bytes(sentinel);ports_out.write_bytes(sentinel)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and ports_out.read_bytes()==sentinel
        negatives.append({'failure':label,'outputs_preserved':True,'original_executed':False})
    debug_alias=folder/'debug-output-alias.ms5d'
    original_debug=debug_resource.read_bytes()
    debug_alias.write_bytes(original_debug)
    command=arguments(incoming,[255]*5,LOOP,0xffff)
    command[3]=command[14]=str(debug_alias)
    inp.write_bytes(fixture(2));ports_out.write_bytes(sentinel)
    actual=subprocess.run(command,capture_output=True,text=True)
    assert actual.returncode and debug_alias.read_bytes()==original_debug and ports_out.read_bytes()==sentinel
    negatives.append({'failure':'debug-input-output-alias','outputs_preserved':True,'original_executed':False})
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert bytes(cpu.mem_read(0x200000,0xffff0))==program[0x200000:0x2ffff0]
    assert any(row['kind']=='main' and row['result']['next_pc']==CALLBACK for row in rows)
    assert any(row['kind']=='main' and row['result']['next_pc']==LOOP for row in rows)
    assert any(row['kind']=='main' and row['result']['next_pc']==BIOS for row in rows)
    assert any(row['kind']=='main' and row['result']['next_pc']==TRAP for row in rows)
    report.write_text(json.dumps({'source':source,'emulator':'Unicorn '+unicorn.__version__,'program_code_modified':False,'cases':len(rows),'irq_cases':sum(row['kind']=='irq' for row in rows),'main_cases':sum(row['kind']=='main' for row in rows),'main_entry_cases':{hex(entry):sum(row['kind']=='main' and row['entry']==entry for row in rows) for entry in (LOOP,GATE,PREFIX,0xf4c)},'whole_ram_ordered_ports_full_d1_full_d3_results_equal':True,'ordered_ports':sum(row['ports'] for row in rows),'irq_context_is_explicit_host_save_restore':True,'cpp_ram_full_d1_d3_outputs_carried':True,'waiting_does_not_rerun_debug_asserted':True,'initial_signal_fixture_only_afterward_actual_irq_generation':True,'runtime_hashes':hashes,'negative_cases':len(negatives),'negative_results':negatives,'output_carry_sequences':sequences,'results':rows,'scope':'Native ec4 debug→ef2 wait/ready and f12 controller/callback, ef2 resumes, direct f12 and f4c callback wait. Actual c8c produces signal16 after initial fixtures; main context is explicitly saved/restored by host around service execution, without BIOS, SR/RTE, physical interrupt timing or arbitrary callback implementation. Whole C++ RAM and full D1/D3 outputs are carried between main calls and IRQ calls; native scratch context persists independently and is never reset to correct an oracle mismatch. Only D1/D3 and explicit A6/stack boundary context are API inputs; full scratch-register equivalence is not claimed. Host releases reentrant guard19 once. Mode/replay/control/restart/BIOS/TRAP boundaries covered.'},indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'main_cases':sum(row['kind']=='main' for row in rows),'irq_cases':sum(row['kind']=='irq' for row in rows),'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest()}))

if __name__=='__main__':
    main()
