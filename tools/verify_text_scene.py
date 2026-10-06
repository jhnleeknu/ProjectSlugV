"""Fresh original-CPU scene trace vs resource-only native C++ scene output."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from unicorn import UC_HOOK_MEM_WRITE
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    directory = root/'artifacts/text_scene'
    directory.mkdir(parents=True,exist_ok=True)
    output = directory/'warning.ppm'
    subprocess.run([str(root/'build/render_text_scene'),str(root/'extracted/runtime/warning.ms5x'),
                    str(root/'extracted/runtime/fixed.ms5t'),str(root/'extracted/runtime/palettes.ms5p'),str(output)],check=True)
    cpu = make_cpu(program)
    cpu.mem_map(0x200000,0x300000)
    cpu.mem_write(0x200000,program[0x200000:0x300000])
    call(cpu,0x3ef2)
    vram = [0]*1280
    writes = []
    def on_write(cpu, access, address, size, value, user):
        if 0x3c0000 <= address < 0x3c0010:
            if address != 0x3c0000 or size != 4 or not 0x7000 <= value>>16 < 0x7500:
                raise ValueError('Unexpected original video port write')
            vram[(value>>16)-0x7000] = value&0xffff
            writes.append(value)
    cpu.hook_add(UC_HOOK_MEM_WRITE,on_write)
    call(cpu,0xcb64)
    call(cpu,0x7196)
    call(cpu,0x72fa)
    palette = struct.unpack('>256H',bytes(cpu.mem_read(0x400000,512)))
    raw = (root/'extracted/media/fixed.decrypted.bin').read_bytes()
    if hashlib.sha256(raw).hexdigest() != '8cbbe34735a51a71fdce50566323a23c4afd41be5a11c94afdfcb23c2f6a7981':
        raise ValueError('Unverified fixed tile image')
    subprocess.run([sys.executable,str(root/'tools/inspect_color_reference.py')],check=True)
    lookup = (root/'artifacts/color_reference/channel_lookup.bin').read_bytes()
    frame = [0]*(320*256)
    for y in range(256):
        for column in range(40):
            value = vram[column*32+y//8]
            tile, slot = value&0xfff,value>>12
            for pair, offset in enumerate((16,24,0,8)):
                byte = raw[tile*32+(y&7)+offset]
                for half,pixel in enumerate((byte&15,byte>>4)):
                    if pixel:
                        frame[y*320+column*8+pair*2+half] = palette[slot*16+pixel]
    rgb = bytearray()
    for word in frame:
        column = word>>15
        channels = (((word>>14)&1)|((word>>7)&30),((word>>13)&1)|((word>>3)&30),((word>>12)&1)|((word<<1)&30))
        rgb.extend(lookup[channel*4+column] for channel in channels)
    expected = b'P6\n320 256\n255\n'+rgb
    if output.read_bytes() != expected:
        raise ValueError('Resource-only C++ scene differs from fresh original reference')
    (directory/'reference.ppm').write_bytes(expected)
    report = {'source_program_sha256':source['sha256'],'original_entries':[0x3ef2,0xcb64,0x7196,0x72fa],
              'cpp_inputs':['warning.ms5x','fixed.ms5t','palettes.ms5p'],
              'original_video_writes':len(writes),'frame_size':[320,256],
              'rgb_bytes_compared':len(rgb),'all_pixels_equal':True,
              'ppm_sha256':hashlib.sha256(expected).hexdigest(),
              'scope':'Controlled zero initial VRAM/background, cartridge fixed layer and normal screen; no actual boot/display timing claim.'}
    (directory/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
