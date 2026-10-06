"""Decrypt C/M/V regions and compare every output byte with pinned MAME.

Requires verified regions, fetched references and clang++. Reference C++ is
generated under artifacts/; Python is the extraction implementation.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from decrypt_cmc_gfx import decrypt_graphics, extract_fixed
from decrypt_sound import decrypt_m1, build_audio_region, decrypt_samples


ROOT = Path(__file__).resolve().parents[1]


def function_text(source, name):
    start = source.index(name + '(')
    start = source.rfind('\n', 0, start) + 1
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


def reference_source(filename):
    manifest = json.loads((ROOT / 'config/mame_sources.json').read_text())
    entry = next(x for x in manifest['files'] if x['path'].endswith('/' + filename))
    data = (ROOT / 'artifacts/reference' / filename).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError('Reference hash mismatch: ' + filename)
    return data.decode()


def build_reference():
    cmc = reference_source('prot_cmc.cpp')
    pcm = reference_source('prot_pcm2.cpp')
    parts = ['''// Generated from MAME BSD-3-Clause source.
// Copyright S. Smith, David Haywood, Fabio Priuli.
#include <cstdint>
#include <cstring>
#include <vector>
#include <fstream>
#include <iterator>
#include <string>
static uint32_t reorder(uint32_t v, const int* bits, int count) {
    uint32_t result=0;
    for(int i=0;i<count;++i) result=(result<<1)|((v>>bits[i])&1);
    return result;
}
static uint16_t sum16(const uint8_t* data, unsigned size) {
    uint16_t sum=0;
    for(unsigned i=0;i<size;++i) sum=static_cast<uint16_t>(sum+data[i]);
    return sum;
}
''']
    for width in (16, 24):
        parameters = ','.join('int b%d' % i for i in range(width))
        values = ','.join('b%d' % i for i in range(width))
        parts.append('static uint32_t swap%d(uint32_t v,%s) { const int b[%d]={%s}; return reorder(v,b,%d); }\n'
                     % (width, parameters, width, values, width))
    parts.extend(re.findall(r'static const uint8_t \w+\[256\]\s*=\s*\{.*?\};', cmc, re.S))
    names = ['type0_t03', 'type0_t12', 'type1_t03', 'type1_t12',
             'address_8_15_xor1', 'address_8_15_xor2', 'address_16_23_xor1',
             'address_16_23_xor2', 'address_0_7_xor']
    parts.append('\n' + ''.join('static const uint8_t* %s;\n' % name for name in names))
    for name in ('decrypt', 'gfx_decrypt', 'cmc50_gfx_decrypt', 'sfix_decrypt',
                 'm1_address_scramble', 'cmc50_m1_decrypt'):
        text = function_text(cmc, 'cmc_prot_device::' + name)
        if name == 'cmc50_m1_decrypt':
            # Drop disabled debug file dumps referencing MAME machine().
            text = text[:text.index('\n\tif (0)')] + '\n}\n'
        text = text.replace('cmc_prot_device::', '').replace('util::sum16_creator::simple', 'sum16')
        parts.append(text)
    parts.append(function_text(pcm, 'pcm2_prot_device::swap').replace('pcm2_prot_device::swap', 'pcm_swap'))
    parts.append('''
static bool save(const char* path,const std::vector<uint8_t>& data) {
    std::ofstream out(path,std::ios::binary);
    out.write(reinterpret_cast<const char*>(data.data()),data.size());
    return static_cast<bool>(out);
}
int main(int argc,char** argv) {
    if(argc!=5) return 2;
    std::ifstream in(argv[2],std::ios::binary);
    if(!in) return 3;
    std::vector<uint8_t> data((std::istreambuf_iterator<char>(in)),std::istreambuf_iterator<char>());
    std::vector<uint8_t> extra;
    std::string mode(argv[1]);
    if(mode=="gfx") {
        if(data.size()!=0x4000000) return 4;
        cmc50_gfx_decrypt(data.data(),data.size(),0x19);
        extra.resize(0x20000);
        sfix_decrypt(data.data(),data.size(),extra.data(),extra.size());
    } else if(mode=="m1") {
        if(data.size()!=0x80000) return 4;
        extra.resize(0x90000);
        cmc50_m1_decrypt(data.data(),data.size(),extra.data(),extra.size());
    } else if(mode=="pcm") {
        if(data.size()!=0x1000000) return 4;
        pcm_swap(data.data(),data.size(),2);
    } else return 5;
    if(!save(argv[3],data)) return 6;
    if(!extra.empty()&&!save(argv[4],extra)) return 7;
    return 0;
}
''')
    generated = '\n'.join(parts).replace('bitswap<16>', 'swap16').replace('bitswap<24>', 'swap24')
    directory = ROOT / 'artifacts/media_reference'
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'reference.cpp'
    source.write_text(generated)
    executable = directory / 'reference'
    subprocess.run(['clang++', '-std=c++11', '-O2', str(source), '-o', str(executable)], check=True)
    return executable


def main():
    executable = build_reference()
    assembly = json.loads((ROOT / 'extracted/regions/manifest.json').read_text())
    regions = {x['name']: x for x in assembly['regions']}
    destination = ROOT / 'extracted/media'
    destination.mkdir(parents=True, exist_ok=True)
    reports = []
    cases = [('m1', 'audiocrypt', decrypt_m1, build_audio_region,
              'm1.decrypted.bin', 'audiocpu.region.bin'),
             ('pcm', 'adpcma', decrypt_samples, None, 'samples.decrypted.bin', None),
             ('gfx', 'sprites', decrypt_graphics, extract_fixed,
              'sprites.decrypted.bin', 'fixed.decrypted.bin')]
    for mode, region_name, decrypt, derive, filename, extra_name in cases:
        item = regions[region_name]
        input_path = ROOT / 'extracted/regions' / item['file']
        data = input_path.read_bytes()
        if len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Assembly manifest mismatch: ' + region_name)
        ref = executable.parent / (mode + '.bin')
        ref_extra = executable.parent / (mode + '.extra.bin')
        subprocess.run([str(executable), mode, str(input_path), str(ref), str(ref_extra)], check=True)
        print('Decrypting ' + region_name + ' in Python...', flush=True)
        output = decrypt(data)
        outputs = [(filename, output, ref)]
        if derive:
            outputs.append((extra_name, derive(output), ref_extra))
        for name, contents, reference_path in outputs:
            expected = reference_path.read_bytes()
            if contents != expected:
                raise ValueError('MAME differential mismatch: ' + name)
            (destination / name).write_bytes(contents)
            reports.append({'file': name, 'size': len(contents),
                            'sha256': hashlib.sha256(contents).hexdigest(),
                            'source_region': region_name, 'input_sha256': item['sha256'],
                            'mame_full_byte_comparison': True})
            print('%s: %d bytes match MAME C++' % (name, len(contents)), flush=True)
    report = {'schema_version': 1, 'set': 'mslug5', 'source': assembly['reference']['source'],
              'outputs': reports, 'scope': 'Algorithm differential checks; no emulator boot, audio synthesis or tile decoding.'}
    (destination / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
