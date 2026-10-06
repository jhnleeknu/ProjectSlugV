"""Verify animation draw operand decoding before the original sprite producer."""
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D5, UC_M68K_REG_D7
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu


def model(control, xbyte, ybyte, identifier, style, palette_word, palettes,
          base_x, base_y, carry, group, depth, delay, hidden, blink):
    if identifier == 0x7ff800 or delay&128 or hidden&8 and blink&1:
        return None
    x = (xbyte if xbyte<128 else xbyte-256)*2+((control>>1)&1)
    y = (ybyte if ybyte<128 else ybyte-256)*2+(control&1)
    if style&1: x=-x
    if style&2: y=-y
    x=(x+base_x-(carry&1))&65535
    y=(y+base_y-((carry>>1)&1))&65535
    style ^= (control>>2)&3
    selection=control>>4
    if selection>=10:
        selection-=10
        style ^= 4
    if selection>=5:
        selection-=5
        use_special=False
    else:
        use_special=bool(palette_word&1) and not palette_word&128
    if use_special:
        style=(style&0xffff00ff)|(palette_word&0xff00)
    elif selection<4:
        style=(style&0xffff00ff)|(palettes[selection]<<8)
    return [(x<<16)|y,style,depth,(identifier|group)]


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000)
    captured=[]
    def hook(cpu,address,size,user):
        if address==0xcd58:
            captured.append([cpu.reg_read(r) for r in (UC_M68K_REG_D0,UC_M68K_REG_D1,UC_M68K_REG_D5,UC_M68K_REG_D7)])
            cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE,hook,begin=0xcd58,end=0xcd58)
    cases=[]
    for control in range(256):
        for flip in range(4):
            for special in (0x3300,0x3301,0x3381):
                # Cover wrapped signed offsets, parent fractional carry and palette modes.
                xbyte=(control*13)&255;ybyte=(control*29+128)&255
                style=0xffff1500|flip
                identifier=0x23800
                ram=bytearray(65536);obj=0x2000
                struct.pack_into('>I',ram,obj+0x12,style)
                struct.pack_into('>H',ram,obj+0x16,special)
                ram[obj+0x19:obj+0x1d]=bytes((0x21,0x22,0x23,0x24))
                struct.pack_into('>H',ram,obj+0x1e,0x5678)
                struct.pack_into('>H',ram,obj+0x20,0x2a)
                struct.pack_into('>H',ram,obj+0x42,160)
                struct.pack_into('>H',ram,obj+0x46,384)
                ram[obj+0x53]=control&3
                ram[0x5800:0x5807]=bytes((control,xbyte,ybyte))+struct.pack('>I',identifier)
                cpu.mem_write(0x100000,bytes(ram))
                for reg,value in ((UC_M68K_REG_A0,0x102026),(UC_M68K_REG_A1,0x105800),(UC_M68K_REG_A5,0x108000),(UC_M68K_REG_A6,0x102000),(UC_M68K_REG_A7,0x1feffc)):
                    cpu.reg_write(reg,value)
                cpu.mem_write(0x1feffc,struct.pack('>I',0xff000));captured.clear()
                cpu.emu_start(0x4a10c,0xff000,count=2000)
                expected=model(control,xbyte,ybyte,identifier,style,special,(0x21,0x22,0x23,0x24),160,384,control&3,0x2a,0x5678,0,0,0)
                if captured!=[expected] or cpu.reg_read(UC_M68K_REG_A1)!=0x105807:
                    raise ValueError('Draw argument mismatch '+repr((control,flip,special,captured,expected)))
                cases.append({'control':control,'flip':flip,'palette_word':special,'arguments':expected})
    destination=root/'artifacts/animation_draw';destination.mkdir(parents=True,exist_ok=True)
    (destination/'verification.json').write_text(json.dumps({'source':source,'cases':len(cases),'all_arguments_equal':True,
        'scope':'Direct draw handler calls with controlled object state, intercepted before producer. No animation timing, skip branch or whole-game claim.','results':cases},indent=2)+'\n')
    print('Animation draw producer arguments match:',len(cases),'cases')


if __name__=='__main__':
    main()
