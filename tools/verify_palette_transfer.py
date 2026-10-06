"""Verify normal transfer gates and consecutive effect/prepare/upload frames."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':raise ValueError('Unsupported ROM')
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);cpu.mem_write(0x200000,program[0x200000:0x300000]);cpu.reg_write(UC_M68K_REG_A5,0x108000)
    selections=[]
    def hook(cpu,access,address,size,value,user):
        if address in (0x3a000f,0x3a001f):selections.append(0 if address==0x3a000f else 1)
    cpu.hook_add(UC_HOOK_MEM_WRITE,hook)
    folder=root/'artifacts/palette_transfer';folder.mkdir(parents=True,exist_ok=True)
    inp,pal,out,outpal,bank=[folder/name for name in ('input.bin','palette.bin','output.bin','output_palette.bin','bank.bin')]
    rows=[]
    def transfer(state,palette):
        cpu.mem_write(0x100000,bytes(state));cpu.mem_write(0x400000,palette);selections.clear();call(cpu,0x72fa)
        expected=bytes(cpu.mem_read(0x100000,65536));expected_palette=bytes(cpu.mem_read(0x400000,8192))
        inp.write_bytes(state);pal.write_bytes(palette)
        subprocess.run([str(root/'build/transfer_palette'),str(inp),str(pal),str(out),str(outpal),str(bank)],check=True)
        if out.read_bytes()!=expected or outpal.read_bytes()!=expected_palette or bank.read_bytes()!=bytes([selections[-1]]):raise ValueError('Normal palette transfer mismatch')
        rows.append({'ram_sha256':hashlib.sha256(expected).hexdigest(),'palette_sha256':hashlib.sha256(expected_palette).hexdigest(),'bank_sequence':list(selections)})
        return bytearray(expected),expected_palette
    for first in (0,0x1234,0x9234,0xffff):
        for pending in (0,1,128,255):
            for display in (0,255):
                state=bytearray(65536);state[0x7ded]=pending;state[0x7dec]=display
                state[0x5da2:0x7da2]=hashlib.shake_256(struct.pack('>HBB',first,pending,display)).digest(8192)
                struct.pack_into('>H',state,0x5da2,first)
                transfer(state,bytes([0x5a])*8192)
    for target in ((65532,65532,65532,4),(31,65505,0,5)):
        cpu.mem_write(0x100000,bytes(65536));call(cpu,0x3ef2)
        state=bytearray(cpu.mem_read(0x100000,65536));palette=bytes(8192)
        for slot,identifier in enumerate((0x203,0x39d,0x3d3)):
            node=0x4d92+slot*16;struct.pack_into('>HH',state,node+10,identifier,identifier);state[node+15]=128
        cpu.mem_write(0x100000,bytes(state))
        for reg,value in zip((UC_M68K_REG_D0,UC_M68K_REG_D1,UC_M68K_REG_D2,UC_M68K_REG_D3),target):cpu.reg_write(reg,value)
        call(cpu,0x8c16);expected=bytes(cpu.mem_read(0x100000,65536));inp.write_bytes(state)
        subprocess.run([str(root/'build/control_palette'),'effect',str(inp),str(out)]+[str(v) for v in target],check=True)
        state=bytearray(out.read_bytes())
        if state!=expected:raise ValueError('Effect setup mismatch')
        for frame in range(12):
            cpu.mem_write(0x100000,bytes(state));call(cpu,0x5728);expected=bytes(cpu.mem_read(0x100000,65536));inp.write_bytes(state)
            subprocess.run([str(root/'build/step_palette_frame'),str(inp),str(root/'extracted/runtime/palettes.ms5p'),str(out)],check=True)
            state=bytearray(out.read_bytes())
            if state!=expected:raise ValueError('Consecutive effect frame mismatch')
            if frame!=1:state,palette=transfer(state,palette) # intentionally defer one upload
    (folder/'verification.json').write_text(json.dumps({'source':source,'transfer_cases':len(rows),'consecutive_frames':24,'all_ram_palette_bank_equal':True,
        'scope':'Normal72fa RAM/palette0 bytes and final bank selector; boundary fixtures plus controlled setter/frame/transfer sequences with one delayed upload. Logical mapped bank0, not device timing, bank1 contents or special fill mode.', 'results':rows},indent=2)+'\n')
    print('Palette transfer matches:',len(rows),'transfers and24 consecutive effect frames')


if __name__=='__main__':main()
