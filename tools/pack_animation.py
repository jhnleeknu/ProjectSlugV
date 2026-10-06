"""Extract a caller-backed fixed-ROM animation loop and its compositions."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program
from verify_sprite_blocks import resolve_blocks


def extract(program):
    # Verify decoded setup instructions, not an arbitrary byte-pattern candidate.
    if program[0x1e67a:0x1e680]!=bytes.fromhex('3d7c00ca0020'):
        raise ValueError('Unexpected composition group setup')
    if program[0x1e6a6:0x1e6b6]!=bytes.fromhex('227c0006f1e2303c01004eb900049f8c'):
        raise ValueError('Unexpected animation initialization call')
    start=0x6f1e2;cursor=start;commands=[];identifiers=[]
    for step in range(100):
        at=cursor;opcode=program[cursor];cursor+=1
        if opcode==4:
            control,x,y,identifier=struct.unpack('>BBBI',program[cursor:cursor+7]);cursor+=7
            commands.append({'address':at,'opcode':opcode,'control':control,'x_byte':x,'y_byte':y,'identifier_operand':identifier})
            if identifier!=0x7ff800: identifiers.append(identifier|0xca)
        elif opcode==0:
            commands.append({'address':at,'opcode':opcode,'duration':program[cursor]});cursor+=1
        elif opcode==8:
            target=int.from_bytes(program[cursor+1:cursor+5],'big');cursor+=5
            if target!=start: raise ValueError('Expected loop to exact start')
            commands.append({'address':at,'opcode':opcode,'target':target})
            if cursor!=0x6f21a: raise ValueError('Unexpected reviewed script boundary')
            return start,program[start:cursor],commands,identifiers
        else: raise ValueError('Unexpected script opcode')
    raise ValueError('Missing loop terminator')


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f': raise ValueError('Unsupported ROM')
    base,data,commands,ids=extract(program)
    destination=root/'extracted/runtime';destination.mkdir(parents=True,exist_ok=True)
    packed=struct.pack('<4s7I',b'MS5A',1,1,base,base,len(data),zlib.crc32(data),0)+data
    filename='animation_%06x.ms5a'%base;(destination/filename).write_bytes(packed)
    resources=[]
    for identifier in sorted(set(ids)):
        bank,offset,payload,blocks=resolve_blocks(program,identifier)
        composition=struct.pack('<4s7I',b'MS5C',1,2,identifier,offset,len(payload),zlib.crc32(payload),0)+payload
        name='composition_%06x.ms5c'%identifier;(destination/name).write_bytes(composition)
        resources.append({'packed_id':identifier,'file':name,'source_rom_offset':offset,'source_cpu_address':offset-bank+0x200000,
                          'bank_base':bank,'blocks':len(blocks),'sha256':hashlib.sha256(composition).hexdigest()})
    manifest={'schema_version':1,'format':'MS5A','source':source,'file':filename,'source_cpu_address':base,'source_rom_offset':base,
              'payload_size':len(data),'sha256':hashlib.sha256(packed).hexdigest(),'caller':0x1e6b0,'group':0xca,'timer_decrement':256,
              'commands':commands,'compositions':resources,'scope':'One statically referenced loop; caller setup verified, natural gameplay reachability and palette binding not fully verified.'}
    (destination/'animations.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Packed original animation loop:',len(data),'bytes,',len(resources),'composition dependencies')


if __name__=='__main__': main()
