"""Compare Python PVC decryption with the hash-pinned MAME C++ function.

The generated C++ stays in artifacts/. It uses the original function body,
with minimal standalone byte/bitswap support and little-endian byte storage.
This is an algorithm differential check, not an emulator execution test.
"""
import hashlib
import json
from pathlib import Path
import subprocess

from decrypt_pvc import decrypt_program
from assemble_regions import swap_words


def build_reference(root):
    manifest = json.loads((root / 'config/mame_sources.json').read_text())
    entry = next(x for x in manifest['files'] if x['path'].endswith('/prot_pvc.cpp'))
    source = (root / 'artifacts/reference/prot_pvc.cpp').read_bytes()
    if hashlib.sha256(source).hexdigest() != entry['sha256']:
        raise ValueError('Pinned MAME source does not match')
    text = source.decode()
    start = text.index('void pvc_prot_device::mslug5_decrypt_68k(')
    end = text.index('\nvoid pvc_prot_device::svc_px_decrypt(', start)
    function = text[start:end].replace('pvc_prot_device::', '')
    function = function.replace('bitswap<8>', 'swap8').replace('bitswap<16>', 'swap16')
    header = '''// MAME BSD-3-Clause function: S. Smith, David Haywood, Fabio Priuli.
#include <cstdint>
#include <cstring>
#include <vector>
#include <fstream>
#include <iterator>
#define BYTE_XOR_LE(a) (a)
static uint32_t reorder(uint32_t value, const int* bits, int count) {
    uint32_t result = 0;
    for (int i = 0; i < count; ++i) result = (result << 1) | ((value >> bits[i]) & 1);
    return result;
}
static uint32_t swap8(uint32_t v, int a,int b,int c,int d,int e,int f,int g,int h) {
    const int bits[8] = {a,b,c,d,e,f,g,h}; return reorder(v,bits,8);
}
static uint32_t swap16(uint32_t v, int a,int b,int c,int d,int e,int f,int g,int h,
    int i,int j,int k,int l,int m,int n,int o,int p) {
    const int bits[16] = {a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p}; return reorder(v,bits,16);
}
'''
    footer = '''
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    std::ifstream input(argv[1], std::ios::binary);
    if (!input) return 3;
    std::vector<uint8_t> rom((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    if (rom.size() != 0x800000) return 4;
    mslug5_decrypt_68k(rom.data(), static_cast<uint32_t>(rom.size()));
    std::ofstream output(argv[2], std::ios::binary);
    output.write(reinterpret_cast<const char*>(rom.data()), rom.size());
    return output ? 0 : 5;
}
'''
    directory = root / 'artifacts/pvc_reference'
    directory.mkdir(parents=True, exist_ok=True)
    cpp = directory / 'reference.cpp'
    executable = directory / 'reference'
    cpp.write_text(header + function + footer)
    subprocess.run(['clang++', '-std=c++11', '-O2', str(cpp), '-o', str(executable)], check=True)
    return executable, manifest['revision']


def main():
    root = Path(__file__).resolve().parents[1]
    executable, revision = build_reference(root)
    directory = executable.parent
    real = root / 'extracted/regions/maincpu.encrypted.le.bin'
    synthetic = directory / 'synthetic.le.bin'
    synthetic.write_bytes(hashlib.shake_256(b'mslug5 PVC differential fixture v1').digest(0x800000))
    reports = []
    for name, input_path in [('synthetic', synthetic), ('mslug5', real)]:
        output_path = directory / (name + '.reference.le.bin')
        subprocess.run([str(executable), str(input_path), str(output_path)], check=True)
        source = input_path.read_bytes()
        expected = output_path.read_bytes()
        actual = decrypt_program(source)
        if actual != expected:
            index = next(i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1])
            raise ValueError('Differential mismatch in %s at 0x%x' % (name, index))
        if decrypt_program(swap_words(source), byte_xor=1) != swap_words(expected):
            raise ValueError('Big-endian layout covariance failed: ' + name)
        reports.append({'case': name, 'bytes_compared': len(actual),
                        'input_sha256': hashlib.sha256(source).hexdigest(),
                        'output_sha256': hashlib.sha256(actual).hexdigest(), 'match': True,
                        'big_endian_layout_match': True})
        print(name + ': all %d bytes match MAME C++' % len(actual))
    (directory / 'verification.json').write_text(json.dumps({
        'source_revision': revision, 'storage_byte_order': 'little', 'cases': reports,
        'scope': 'Algorithm only; not a full MAME boot or execution comparison.'
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
