"""Reproducible synthetic CCR.C probes; source ROM bytes are never modified."""
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE,m68k_const as m
from verify_object_reset import make_cpu
from disassemble_program import load_verified_program
from observe_scene_motion_bounds import sha,BASE,STACK,RETURN,SCRATCH

OPS=(('AND.W D6,D7',bytes.fromhex('ce46')),('MOVE.L A1,53b4(A5)',bytes.fromhex('2b4953b4')),('TST.W (A1)',bytes.fromhex('4a51')),('MOVEQ #0,D7',bytes.fromhex('7e00')),('SUBQ.L #1,D7',bytes.fromhex('5387')))
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);rows=[]
    for name,op in OPS:
        for carry_source in ('initial-SR-C1','ORI-CCR-C1','ASR-C1'):
            for hooked in (False,True):
                cpu=make_cpu(program);initial_sr=0x2001 if carry_source=='initial-SR-C1' else 0x2000
                prefix=b'' if carry_source=='initial-SR-C1' else bytes.fromhex('003c0001') if carry_source=='ORI-CCR-C1' else bytes.fromhex('e280') # ASR.L #1,D0 withD0=1.
                # One continuous execution: opcode; BCS marksD0=1, fallthrough marksD0=0; RTS.
                code=prefix+op+bytes.fromhex('65047000600270014e75');cpu.mem_write(SCRATCH,code);cpu.mem_write(BASE+0x7000,struct.pack('>H',10));cpu.reg_write(m.UC_M68K_REG_SR,initial_sr);cpu.reg_write(m.UC_M68K_REG_D0,1);cpu.reg_write(m.UC_M68K_REG_D6,0xff00);cpu.reg_write(m.UC_M68K_REG_D7,0xff00);cpu.reg_write(m.UC_M68K_REG_A1,BASE+0x7000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));snapshots=[]
                if hooked:
                    def hook(cpu,address,size,user):
                        if address==SCRATCH+len(prefix)+len(op):snapshots.append(dict(pc=address,sr=cpu.reg_read(m.UC_M68K_REG_SR),d7=cpu.reg_read(m.UC_M68K_REG_D7)))
                    cpu.hook_add(UC_HOOK_CODE,hook)
                cpu.emu_start(SCRATCH,RETURN,count=100)
                assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
                assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
                assert cpu.reg_read(m.UC_M68K_REG_D0)==0 # Every tested instruction clears C for these operands.
                rows.append(dict(expected_carry_after_operation=False,pre_BCS_SR_C_disagrees=bool(snapshots and snapshots[0]['sr']&1),operation=name,opcode_hex=op.hex(),full_synthetic_code_hex=code.hex(),synthetic_code_cpu_address=SCRATCH,carry_source=carry_source,start_sr=initial_sr,hooked=hooked,pre_BCS_snapshots=snapshots,bcs_taken=cpu.reg_read(m.UC_M68K_REG_D0)==1,end_sr=cpu.reg_read(m.UC_M68K_REG_SR),end_d7=cpu.reg_read(m.UC_M68K_REG_D7),original_ROM_unchanged=True))
    for index in range(0,len(rows),2):assert rows[index]['bcs_taken']==rows[index+1]['bcs_taken']
    folder=root/'artifacts/scene_motion_pair';folder.mkdir(parents=True,exist_ok=True);path=folder/'unicorn_flag_probe.json';report=dict(source=source,emulator='Unicorn '+unicorn.__version__,cpu_model='M68000',cases=len(rows),results=rows,scope='Independent synthetic opcodes in RAM106000, original source ROM unmodified. Continuous instruction plus BCS before stopping; separate no-hook/readonly-hook observations. Raw SR and actual in-call branch result are retained independently. This is emulator diagnostic evidence, not original ROM oracle equivalence.')
    path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),sha256=sha(path.read_bytes()),results=[dict(operation=r['operation'],carry_source=r['carry_source'],hooked=r['hooked'],bcs_taken=r['bcs_taken'],pre_BCS_snapshots=r['pre_BCS_snapshots'],end_sr=r['end_sr']) for r in rows])))
if __name__=='__main__':main()
