"""Compare C++ init/submit/prepare/refresh over consecutive controlled frames."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A6, UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_PC, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D5, UC_M68K_REG_D7
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from analyze_sprite_sort import put


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disabled-pool", action="store_true")
    parser.add_argument("--flips", action="store_true")
    parser.add_argument("--blocks", action="store_true")
    parser.add_argument("--animation", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    directory = root/('artifacts/sprite_pipeline_disabled' if args.disabled_pool else 'artifacts/sprite_pipeline')
    if args.flips:
        directory = directory.with_name(directory.name+'_flips')
    if args.blocks:
        directory = directory.with_name(directory.name+'_blocks')
    if args.animation:
        directory = directory.with_name(directory.name+'_animation')
    directory.mkdir(parents=True, exist_ok=True)
    inp, out, trace = directory/'input.bin', directory/'output.bin', directory/'trace.bin'
    identifiers = (0x2382a, 0x2402a, 0x2482a, 0x122, 0x29802, 0x70002) if args.blocks else (0x2152, 0x2952)
    resources = [str(root/'extracted/runtime'/('composition_%06x.ms5c'%i)) for i in identifiers]
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x400000:0x500000])
    events = []
    def hook(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            if address != 0x3c0000 or size != 4:
                raise ValueError('Unexpected video access')
            events.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE, hook)
    def run(entry):
        cpu.reg_write(UC_M68K_REG_A5, 0x108000)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.mem_write(0x1feffc, struct.pack('>I', 0xff000))
        events.clear()
        cpu.emu_start(entry, 0xff000, count=1000000)
        if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
            raise ValueError('Original did not return')
    records = []
    submissions = 0
    for direction in (0, 128):
        for start in (0, 510):
            cpu.mem_write(0x100000, bytes(65536))
            run(0xccd6)
            inp.write_bytes(bytes(65536))
            subprocess.run([str(root/'build/produce_sprite_queue'), 'init', str(inp), str(out)], check=True)
            state = bytearray(out.read_bytes())
            if state != bytes(cpu.mem_read(0x100000, 65536)):
                raise ValueError('Pipeline init mismatch')
            # Controlled arguments passed through original and C++ pool setters.
            state[0x8d3c] = direction
            for at in (0x8d34, 0x8d36, 0x8d38, 0x8d3a):
                put(state, at, start)
            cpu.mem_write(0x100000, bytes(state))
            for selector, lower, upper in ((0, 0, 190), (1, 190, 380)):
                if selector == 1 and args.disabled_pool:
                    continue
                for reg, value in ((UC_M68K_REG_D0,selector),(UC_M68K_REG_D1,lower),(UC_M68K_REG_D2,upper)):
                    cpu.reg_write(reg,value)
                run(0xcd1c)
                inp.write_bytes(state)
                subprocess.run([str(root/'build/configure_sprite_pool'), str(inp), str(out),
                                str(selector), str(lower), str(upper)], check=True)
                state = out.read_bytes()
                if state != bytes(cpu.mem_read(0x100000,65536)):
                    raise ValueError('Pipeline pool configuration differs')
            for frame, count in enumerate((4, 20, 0, 7)):
                for index in range(count):
                    u, v = (0x2a0 if index%5 == 4 else 160), 384+frame
                    d0 = (u<<16)|v
                    d1 = (0xffff1500 if index%2 == 0 else 0xffff1604) | (64 if index%3 == 0 else 0)
                    if args.flips:
                        d1 |= (index+frame)&3
                    d5 = (count-index)*13
                    d7 = identifiers[index%len(identifiers)]
                    if args.animation:
                        mutable = bytearray(state)
                        obj = 0x2000
                        struct.pack_into('>I',mutable,obj+0x12,d1)
                        struct.pack_into('>H',mutable,obj+0x16,0)
                        mutable[obj+0x19] = (d1>>8)&255
                        struct.pack_into('>H',mutable,obj+0x1e,d5)
                        struct.pack_into('>H',mutable,obj+0x20,0)
                        struct.pack_into('>H',mutable,obj+0x42,u)
                        struct.pack_into('>H',mutable,obj+0x46,v)
                        mutable[obj+0x2a] = mutable[obj+0x53] = mutable[obj+0x61] = 0
                        operand = bytes((0,0,0))+struct.pack('>I',d7)
                        mutable[0x5800:0x5807] = operand
                        state = bytes(mutable)
                        cpu.mem_write(0x100000,state)
                        for reg,value in ((UC_M68K_REG_A0,0x102026),(UC_M68K_REG_A1,0x105800),(UC_M68K_REG_A6,0x102000)):
                            cpu.reg_write(reg,value)
                        run(0x4a10c)
                        inp.write_bytes(state)
                        operand_path = directory/'operand.bin'
                        operand_path.write_bytes(operand)
                        subprocess.run([str(root/'build/decode_animation_draw'),str(inp),str(operand_path),str(trace),str(obj)],check=True)
                        skipped,d0,d1,d5,d7 = struct.unpack('>5I',trace.read_bytes())
                        if skipped:
                            raise ValueError('Unexpected skipped animation fixture')
                    else:
                        for reg, value in ((UC_M68K_REG_D0,d0),(UC_M68K_REG_D1,d1),(UC_M68K_REG_D5,d5),(UC_M68K_REG_D7,d7)):
                            cpu.reg_write(reg,value)
                        run(0xcd58)
                        inp.write_bytes(state)
                    subprocess.run([str(root/'build/produce_sprite_queue'), 'submit', str(inp), str(out), str(trace),
                                    str(d0), str(d1), str(d5), str(d7)], check=True)
                    state = out.read_bytes()
                    expected_status = 1 if u == 0x2a0 else 0
                    if state != bytes(cpu.mem_read(0x100000,65536)) or trace.read_bytes() != struct.pack('>I',expected_status):
                        raise ValueError('Pipeline submit mismatch')
                    submissions += 1
                for stage, entry in (('prepare',0x16bba), ('refresh',0x16cfa)):
                    run(entry)
                    inp.write_bytes(state)
                    subprocess.run([str(root/('build/'+stage+'_sprite_queue')), str(inp), str(out), str(trace)]+resources, check=True)
                    state = out.read_bytes()
                    expected_trace = (struct.pack('>I',1) if stage == 'refresh' else b'')+b''.join(struct.pack('>I',w) for w in events)
                    if state != bytes(cpu.mem_read(0x100000,65536)) or trace.read_bytes() != expected_trace:
                        raise ValueError('Pipeline %s mismatch frame%d direction%d start%d' % (stage,frame,direction,start))
                    records.append({'initial_direction':direction,'initial_start':start,'frame':frame,'stage':stage,
                                    'writes':len(events),'ram_sha256':hashlib.sha256(state).hexdigest(),
                                    'video_sha256':hashlib.sha256(expected_trace).hexdigest()})
    (directory/'verification.json').write_text(json.dumps({'source_program_sha256':source['sha256'],
        'animation':args.animation,'blocks':args.blocks,'flips':args.flips,'disabled_pool':args.disabled_pool,'independent_sequences':4,'frames_per_sequence':4,'submissions':submissions,'stages':len(records),
        'all_ram_and_video_equal':True,'scope':'Controlled four-frame sequences with default callback and selected rectangle resources. No actual vblank, interrupt concurrency, pixel or whole-game timing claim.', 'results':records},indent=2)+'\n')
    print('Producer/prepare/refresh pipeline matches:',submissions,'submissions,',len(records),'stages')


if __name__ == '__main__':
    main()
