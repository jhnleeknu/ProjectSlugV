"""Compare all decoded C tiles with pinned MAME optimize_helper."""
import hashlib
import json
from pathlib import Path
import subprocess

from extract_media import function_text, reference_source


def main():
    root = Path(__file__).resolve().parents[1]
    source = reference_source('neogeo_spr.cpp')
    function = function_text(source, 'neosprite_optimized_device::optimize_helper')
    function = function.replace('neosprite_optimized_device::', '')
    support = '''// MAME BSD-3-Clause; see tools/licenses/mame-sprites.txt.
#include <cstdint>
#include <vector>
#include <fstream>
#include <iterator>
typedef uint8_t u8;
typedef uint32_t u32;
#define BIT(value,bit) (((value)>>(bit))&1)
static u32 get_region_mask(u8*, u32 size) { return size*2-1; }
'''
    driver = '''
int main(int argc,char**argv) {
    if(argc!=3) return 2;
    std::ifstream in(argv[1],std::ios::binary);
    if(!in) return 3;
    std::vector<u8> raw((std::istreambuf_iterator<char>(in)),std::istreambuf_iterator<char>());
    if(raw.size()!=0x4000000) return 4;
    std::vector<u8> decoded;
    optimize_helper(decoded,raw.data(),raw.size());
    std::ofstream out(argv[2],std::ios::binary);
    out.write(reinterpret_cast<const char*>(decoded.data()),decoded.size());
    return out ? 0:5;
}
'''
    directory = root / 'artifacts/tile_reference'
    directory.mkdir(parents=True, exist_ok=True)
    cpp = directory / 'reference.cpp'
    cpp.write_text(support + function + driver)
    executable = directory / 'reference'
    subprocess.run(['clang++', '-std=c++11', '-O2', str(cpp), '-o', str(executable)], check=True)
    expected_path = directory / 'sprites.idx8'
    subprocess.run([str(executable), str(root / 'extracted/media/sprites.decrypted.bin'),
                    str(expected_path)], check=True)
    actual = (root / 'extracted/tiles/sprites.idx8').read_bytes()
    expected = expected_path.read_bytes()
    if actual != expected:
        raise ValueError('Decoded sprite indices differ from MAME optimize_helper')
    # Fixed layer reference follows the renderer's low/high nibble sequence,
    # independently walking pairs rather than sharing the Python decoder.
    fixed = (root / 'extracted/media/fixed.decrypted.bin').read_bytes()
    decoded = (root / 'extracted/tiles/fixed.idx8').read_bytes()
    for tile in range(4096):
        for row in range(8):
            for pair, offset in enumerate((16,24,0,8)):
                byte = fixed[tile*32 + row + offset]
                start = tile*64 + row*8 + pair*2
                if decoded[start:start+2] != bytes((byte & 15, byte >> 4)):
                    raise ValueError('Fixed renderer mapping mismatch')
    report = {'sprites': {'bytes_compared': len(actual),
                          'sha256': hashlib.sha256(actual).hexdigest(),
                          'mame_optimize_helper_match': True},
              'fixed': {'pixels_compared': len(decoded),
                        'sha256': hashlib.sha256(decoded).hexdigest(),
                        'renderer_mapping_match': True},
              'scope': 'Raw indices only; palettes, object composition and animation unresolved.'}
    (directory / 'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
