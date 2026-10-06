"""Compare C++ sprite selection against unchanged pinned MAME functions."""
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
from extract_media import reference_source, function_text

WORDS = 0x8800


def reference(root, directory):
    source = reference_source('neogeo_spr.cpp')
    cpp = '''// MAME BSD-3-Clause; see tools/licenses/mame-sprites.txt.
#include <cstdint>
#include <cstdio>
#include <cstring>
using u16 = std::uint16_t;
using u32 = std::uint32_t;
#define BIT(v,b) (((v)>>(b))&1)
static constexpr u32 MAX_SPRITES_PER_SCREEN = 381;
static constexpr u32 MAX_SPRITES_PER_LINE = 96;
struct neosprite_base_device {
    u16 m_videoram_drawsource[0x8800];
    bool sprite_on_scanline(int scanline, int y, int rows);
    void parse_sprites(int scanline);
};
'''+function_text(source, 'neosprite_base_device::sprite_on_scanline')+function_text(source, 'neosprite_base_device::parse_sprites')+'''
int main() {
    neosprite_base_device device;
    unsigned char input[0x11002];
    unsigned char output[0x11000];
    while (std::fread(input,1,sizeof(input),stdin)==sizeof(input)) {
        for (unsigned i=0;i<0x8800;++i)
            device.m_videoram_drawsource[i]=(input[2+i*2]<<8)|input[3+i*2];
        device.parse_sprites((input[0]<<8)|input[1]);
        for (unsigned i=0;i<0x8800;++i) {
            output[i*2]=device.m_videoram_drawsource[i]>>8;
            output[i*2+1]=device.m_videoram_drawsource[i];
        }
        if(std::fwrite(output,1,sizeof(output),stdout)!=sizeof(output)) return 1;
    }
    return std::ferror(stdin)?1:0;
}
'''
    path = directory/'reference.cpp'
    path.write_text(cpp)
    binary = directory/'reference'
    subprocess.run(['clang++', '-std=c++11', '-O2', str(path), '-o', str(binary)], check=True)
    return binary


def main():
    root = Path(__file__).resolve().parents[1]
    directory = root/'artifacts/sprite_scanline'
    directory.mkdir(parents=True, exist_ok=True)
    binary = reference(root, directory)
    rng = random.Random(0x268)
    # Nonzero sentinels make clearing and writes outside the selected list observable.
    base = [rng.randrange(65536) for _ in range(WORDS)]
    cases = []
    for pattern in ('empty', 'saturated', 'chained', 'random'):
        vram = base.copy()
        for sprite in range(381):
            if pattern == 'empty':
                control = 0
            elif pattern == 'saturated':
                control = (sprite << 7) | 32
            elif pattern == 'chained':
                control = 64 if sprite % 5 else (((sprite*7)&511)<<7)|(sprite % 64)
            else:
                control = rng.randrange(65536)
            vram[0x8200+sprite] = control
        data = struct.pack('>%dH' % WORDS, *vram)
        for line in range(512):
            cases.append((pattern, line, data))
    # Real C++ resource command output feeds the hardware selector.
    for identifier, style in ((0x2152, 0x1500), (0x2952, 0x1600)):
        output = directory/'composition.bin'
        subprocess.run([str(root/'build/emit_sprite_resource'),
                        str(root/'extracted/runtime'/('composition_%06x.ms5c' % identifier)),
                        str(output), '160', '384', str(style), '0', '380', '0'], check=True)
        data = output.read_bytes()
        vram = [0]*WORDS
        for address, value in struct.iter_unpack('>HH', data[4:]):
            vram[address] = value
        data = struct.pack('>%dH' % WORDS, *vram)
        for line in range(512):
            cases.append(('resource_%06x' % identifier, line, data))
    report = []
    input_path, output_path = directory/'input.bin', directory/'cpp.bin'
    # Reference batching avoids thousands of extra compiler/runtime launches.
    for start in range(0, len(cases), 128):
        batch = cases[start:start+128]
        expected = subprocess.check_output([str(binary)], input=b''.join(struct.pack('>H', line)+data for _, line, data in batch))
        if len(expected) != len(batch)*WORDS*2:
            raise ValueError('Reference output length mismatch')
        for index, (pattern, line, data) in enumerate(batch):
            input_path.write_bytes(data)
            subprocess.run([str(root/'build/parse_sprite_scanline'), str(input_path), str(output_path), str(line)], check=True)
            actual = output_path.read_bytes()
            reference_bytes = expected[index*WORDS*2:(index+1)*WORDS*2]
            if actual != reference_bytes:
                raise ValueError('Scanline mismatch %s line%d' % (pattern, line))
            report.append({'pattern': pattern, 'scanline': line, 'sha256': hashlib.sha256(actual).hexdigest()})
    manifest = json.loads((root/'config/mame_sources.json').read_text())
    result = {'reference_revision': manifest['revision'], 'reference_file': next(x for x in manifest['files'] if x['path'].endswith('/neogeo_spr.cpp')),
              'cases': len(cases), 'vram_bytes_per_case': WORDS*2, 'all_vram_equal': True,
              'scope': 'Scanline sprite selection only. Synthetic states and two real composition command streams; no zoom table, pixel rasterization, hardware timing or whole-game equivalence claim.', 'results': report}
    (directory/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print('All scanline VRAM matches pinned MAME:', len(cases), 'cases')


if __name__ == '__main__':
    main()
