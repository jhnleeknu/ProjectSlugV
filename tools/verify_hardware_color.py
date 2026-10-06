"""Exhaustive C++ color comparison with pinned MAME paletteram_w and resistors."""
import hashlib
import json
from pathlib import Path
import subprocess
from extract_media import function_text, reference_source


def main():
    root = Path(__file__).resolve().parents[1]
    net = reference_source('resnet.cpp')
    header = reference_source('resnet.h')
    video = reference_source('neogeo_v.cpp')
    templates = header[header.index('namespace emu::detail {'):header.index('/* this should be moved')]
    cpp = '''// MAME BSD-3-Clause; see tools/licenses/mame-colors.txt.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
using std::uint8_t; using std::uint16_t;
typedef unsigned int offs_t;
#define MAX_NETS 3
#define MAX_RES_PER_NET 18
#define VERBOSE 0
#define BIT(v,b) (((v)>>(b))&1)
#define fatalerror(...) std::abort()
#define osd_printf_info(...) ((void)0)
struct PaletteSink { uint8_t pixels[16384][3];
void set_pen_color(unsigned int offset,uint8_t r,uint8_t g,uint8_t b) {
pixels[offset][0]=r; pixels[offset][1]=g; pixels[offset][2]=b; } };
struct neogeo_base_state { uint8_t m_palette_lookup[32][4];
unsigned int m_palette_bank; uint16_t m_paletteram[8192]; PaletteSink* m_palette;
void create_rgb_lookups(); void paletteram_w(offs_t offset,uint16_t data); };
'''+templates+function_text(net,'compute_resistor_weights')+function_text(video,'neogeo_base_state::create_rgb_lookups')+function_text(video,'neogeo_base_state::paletteram_w')+'''
int main() { neogeo_base_state state; PaletteSink sink; state.m_palette=&sink;
state.create_rgb_lookups();
for(unsigned int bank=0;bank<2;bank++) {
state.m_palette_bank=bank*0x1000;
for(unsigned int shadow=0;shadow<2;shadow++) {
for(unsigned int word=0;word<65536;word++) {
state.paletteram_w(0,static_cast<uint16_t>(word));
if(std::fwrite(sink.pixels[bank*0x1000+shadow*0x2000],1,3,stdout)!=3) return 1;
}}} return 0; }
'''
    directory = root/'artifacts/hardware_color'
    directory.mkdir(parents=True,exist_ok=True)
    source = directory/'reference.cpp'
    source.write_text(cpp)
    binary = directory/'reference'
    subprocess.run(['clang++','-std=c++17','-O2',str(source),'-o',str(binary)],check=True)
    expected = subprocess.check_output([str(binary)])
    if len(expected) != 2*2*65536*3 or expected[:393216] != expected[393216:]:
        raise ValueError('Reference bank output mismatch')
    (directory/'mame.rgb').write_bytes(expected)
    input_path = directory/'all.words.be.bin'
    input_path.write_bytes(b''.join(i.to_bytes(2,'big') for i in range(65536)))
    actual = bytearray()
    for mode in ('normal','shadow'):
        output = directory/(mode+'.rgb')
        subprocess.run([str(root/'build/convert_color_words'),str(input_path),str(output),mode],check=True)
        actual.extend(output.read_bytes())
    if bytes(actual) != expected[:393216]:
        raise ValueError('C++ hardware color mapping differs from pinned MAME')
    report = {'reference_revision':'df09546b783c419889a2386bec9402883574b881',
              'words_per_mode':65536,'modes':['normal','shadow'],'reference_banks_checked':2,
              'all_rgb_bytes_equal':True,'output_sha256':hashlib.sha256(actual).hexdigest(),
              'scope':'All static palette words and screen-shadow states; no CRT analog fidelity, bank switching timing or full frame emulation claim.'}
    (directory/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
