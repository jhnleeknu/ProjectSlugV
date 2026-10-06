"""Reproduce pinned MAME's 32x4 channel lookup without changing the source functions."""
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
#define MAX_NETS 3
#define MAX_RES_PER_NET 18
#define VERBOSE 0
#define BIT(v,b) (((v)>>(b))&1)
#define fatalerror(...) std::abort()
#define osd_printf_info(...) ((void)0)
struct neogeo_base_state { unsigned char m_palette_lookup[32][4]; void create_rgb_lookups(); };
'''+templates+function_text(net, 'compute_resistor_weights')+function_text(video, 'neogeo_base_state::create_rgb_lookups')+'''
int main() { neogeo_base_state state; state.create_rgb_lookups();
return std::fwrite(state.m_palette_lookup,1,128,stdout)==128 ? 0 : 1; }
'''
    directory = root/'artifacts/color_reference'
    directory.mkdir(parents=True, exist_ok=True)
    source = directory/'reference.cpp'
    source.write_text(cpp)
    binary = directory/'reference'
    # Only the unchanged upstream reference needs C++17 (std::clamp/template syntax).
    subprocess.run(['clang++','-std=c++17','-O2',str(source),'-o',str(binary)],check=True)
    data = subprocess.check_output([str(binary)])
    if len(data) != 128:
        raise ValueError('Reference channel lookup length mismatch')
    (directory/'channel_lookup.bin').write_bytes(data)
    (directory/'channel_lookup.json').write_text(json.dumps({'index':'5-bit channel value',
        'columns':['normal','dark','shadow','dark_shadow'],
        'rows':[list(data[i:i+4]) for i in range(0,128,4)],
        'sha256':hashlib.sha256(data).hexdigest()},indent=2)+'\n')
    print('Verified source lookup:',hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
