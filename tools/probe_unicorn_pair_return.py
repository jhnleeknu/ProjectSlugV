"""Isolate carry across AND/BNE/RTS/MOVEM using separate synthetic RAM code."""
import hashlib
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from musashi_oracle import MusashiOracle

CODE, STACK, STOP = 0x106000, 0x1feffc, 0xff000
MARKER = bytes.fromhex('65047000600270014e75')


def bytecode(mode):
    # D0=1 -> ASR generates C1. AND must clear C; BNE preserves it.
    body = bytes.fromhex('e280ce4666000006003c0001')
    if mode == 'inline':
        return body+MARKER, CODE+len(body)
    save = bytes.fromhex('48e70300') if mode == 'call-with-movem' else b''
    restore = bytes.fromhex('4cdf00c0') if save else b''
    callee = len(save)+4+len(restore)+len(MARKER)
    branch = bytes.fromhex('6100')+struct.pack('>h',callee-len(save)-2)
    return save+branch+restore+MARKER+body+bytes.fromhex('4e75'), CODE+len(save)+4+len(restore)


def run(program, mode, zero, hook_mode, engine):
    raw, branch_pc = bytecode(mode)
    snapshots = []
    values = dict(d0=1, d6=0xff00, d7=0 if zero else 0xff00,
                  a7=STACK, sr=0x2000, pc=CODE)
    if engine == 'Unicorn':
        cpu = make_cpu(program)
        cpu.mem_write(CODE,raw); cpu.mem_write(STACK,STOP.to_bytes(4,'big'))
        cpu.reg_write(m.UC_M68K_REG_SR,values['sr'])
        for key,value in values.items():
            if key != 'sr': cpu.reg_write(getattr(m,'UC_M68K_REG_'+key.upper()),value)
        if hook_mode != 'none':
            def hook(cpu,pc,size,user):
                snapshots.append(dict(pc=pc,**({'sr':cpu.reg_read(m.UC_M68K_REG_SR)} if hook_mode=='read-SR' else {})))
            cpu.hook_add(UC_HOOK_CODE,hook)
        cpu.emu_start(CODE,STOP,count=100)
        result = dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),a7=cpu.reg_read(m.UC_M68K_REG_A7),
                      d0=cpu.reg_read(m.UC_M68K_REG_D0),sr=cpu.reg_read(m.UC_M68K_REG_SR))
        assert cpu.mem_read(0,0x100000)==program[:0x100000]
    else:
        cpu = MusashiOracle();cpu.load(0,program[:0x100000]);cpu.load(CODE,raw);cpu.load(STACK,STOP.to_bytes(4,'big'))
        cpu.set_reg('sr',values['sr'])
        for key,value in values.items():
            if key!='sr':cpu.set_reg(key,value)
        if hook_mode != 'none':
            def hook(pc):snapshots.append(dict(pc=pc,**({'sr':cpu.get_reg('sr')} if hook_mode=='read-SR' else {})))
            cpu.set_instruction_hook(hook)
        status=cpu.run(100,STOP);assert status['status']=='sentinel'
        result={key:cpu.get_reg(key) for key in ('pc','a7','d0','sr')}
        assert cpu.read(0,0x100000)==program[:0x100000]
        cpu.set_instruction_hook(None)
    assert result['pc']==STOP and result['a7']==STACK+4
    return dict(mode=mode,zero_AND_result=zero,hook_mode=hook_mode,engine=engine,
                synthetic_code_cpu_address=CODE,code_hex=raw.hex(),bcs_pc=branch_pc,
                expected_bcs_taken=zero,bcs_taken=result['d0']==1,result=result,snapshots=snapshots)


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);rows=[]
    for mode in ('inline','call','call-with-movem'):
        for zero in (False,True):
            for engine in ('Unicorn','Musashi'):
                group=[run(program,mode,zero,hook_mode,engine) for hook_mode in ('none','PC-only','read-SR')]
                assert group[0]['result']==group[1]['result']
                if engine=='Musashi':
                    assert group[0]['result']==group[2]['result']
                    assert all(r['bcs_taken']==r['expected_bcs_taken'] for r in group)
                else:
                    assert all(r['bcs_taken']==r['expected_bcs_taken'] for r in group[:2])
                rows.extend(group)
    mismatches=[r for r in rows if r['bcs_taken']!=r['expected_bcs_taken']]
    metadata_path=root/'artifacts/dependencies/musashi_oracle_build/metadata.json'
    metadata=json.loads(metadata_path.read_text())
    assert hashlib.sha256(Path(metadata['library_path']).read_bytes()).hexdigest()==metadata['library_sha256']
    report=dict(source=source,unicorn_version=unicorn.__version__,musashi_revision=metadata['revision'],
                musashi_library_sha256=metadata['library_sha256'],
                musashi_metadata_sha256=hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
                cases=len(rows),results=rows,branch_disagreements=len(mismatches),
                scope='Separate synthetic RAM opcodes only; original ROM unchanged. Actual continuous BCS outcome; no-hook/PC-only hook equality; SR-reading hook interference recorded separately against independent Musashi. No game logic or emulator internal root-cause inference.')
    path=root/'artifacts/scene_motion_pair/unicorn_pair_return_probe.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        disagreements=[{k:r[k] for k in ('mode','zero_AND_result','hook_mode','engine','bcs_taken')} for r in mismatches])))
if __name__=='__main__':main()
