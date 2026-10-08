"""Audit original SBCD against a pinned third-party hardware-tested reference.

Reference sources stay in ignored artifacts with their upstream LICENSE. They
are compiled as an independent test oracle, not included in engine sources.
This is not a local physical 68000 measurement.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from verify_object_reset import make_cpu
from observe_scene_frame_execution import oracle_provenance
from verify_stage_catalog import SOURCE_SHA256
from unicorn import m68k_const as m

REVISION = '39a01be528b0744302bf1dc9b3463fc22a3fc45f'
PINS = {
    'bcd-emul.cc': '8031ed69542475de443aad27c2bc58bd83b426eb5843ec99763fda479bac3424',
    'bcd-emul.hh': '4dfff93573eec1b43e93da8e5512441ed701006cb7c2da177ae7d7064e17076c',
    'bcd-gen.cc': '8f1b52a084cdff6ce24cc3640d3529b8b26fbf8f6f74fd9d4e3c2ccb6489f4fa',
    'README.md': 'e9265215836f9e190c083013e0aa7de001f79ad8adfb60caabc9dbcdbd0769a1',
    'LICENSE': '589ed823e9a84c56feb95ac58e7cf384626b9cbf4fda2a907bc36e103de1bad2',
}
TABLE_SHA = '8432868c9aa93c92574bae48bebd4efb2834e298340eb09530625365b80147e5'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / 'artifacts/stage_counter_bcd'
    output.mkdir(exist_ok=True)
    report_path = output / 'verification.json'
    report_path.unlink(missing_ok=True)
    folder = root / 'artifacts/dependencies/flamewing-bcd'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'data').mkdir(exist_ok=True)
    urls = {}
    for name, digest in PINS.items():
        url = 'https://raw.githubusercontent.com/flamewing/68k-bcd-verifier/' + REVISION + '/' + name
        path = folder / name
        if not path.exists():
            raw = urllib.request.urlopen(url, timeout=30).read()
            assert sha(raw) == digest, name
            path.write_bytes(raw)
        assert sha(path.read_bytes()) == digest, name
        urls[name] = dict(url=url, sha256=digest)
    subprocess.run(['c++', '-std=c++11', 'bcd-gen.cc', 'bcd-emul.cc', '-o', 'bcd-gen'], cwd=folder, check=True)
    subprocess.run(['./bcd-gen'], cwd=folder, check=True)
    table = (folder / 'data/bcd-table.bin').read_bytes()
    assert len(table) == 1050624 and sha(table) == TABLE_SHA
    program, source = load_verified_program(root)
    assert sha(program) == source['sha256'] == SOURCE_SHA256
    unicorn_cpu = make_cpu(program)
    musashi = MusashiOracle()
    musashi.load(0, program[:0x100000])
    rows = []
    for high in range(256):
        for low in (0, 2):
            ram = bytearray(65536)
            ram[0xd683] = 16
            ram[0xfdb6] = 1
            ram[0xd67e], ram[0xd67f] = high, low
            musashi.reset()
            musashi.load(0x100000, ram)
            for reg, value in [('sr', 0x2000), ('a7', 0x1feffc), ('a5', 0x108000),
                               ('d0', 0xaabbccdd), ('d1', 0x8899aaff), ('pc', 0x4843c)]:
                musashi.set_reg(reg, value)
            status = musashi.run(100, 0x4846a)
            assert status['status'] == 'sentinel'
            musashi_result = [musashi.get_reg('d1') & 255, musashi.get_reg('sr') & 17]
            cpu = unicorn_cpu
            cpu.mem_write(0x100000, bytes(ram))
            for reg, value in [(m.UC_M68K_REG_SR, 0x2000), (m.UC_M68K_REG_A7, 0x1feffc),
                               (m.UC_M68K_REG_A5, 0x108000), (m.UC_M68K_REG_D0, 0xaabbccdd),
                               (m.UC_M68K_REG_D1, 0x8899aaff)]:
                cpu.reg_write(reg, value)
            cpu.emu_start(0x4843c, 0x4846a, count=100)
            assert cpu.reg_read(m.UC_M68K_REG_PC) == 0x4846a
            unicorn_result = [cpu.reg_read(m.UC_M68K_REG_D1) & 255, cpu.reg_read(m.UC_M68K_REG_SR) & 17]
            extend = int(low < 2)
            # Upstream generator order: source, destination, X, Z; flags/result.
            offset = 524288 + (high * 4 + extend * 2) * 2
            flags, result = table[offset:offset+2]
            assert [table[offset+2] & 17, table[offset+3]] == [flags & 17, result]
            reference = [result, flags & 17]
            assert unicorn_result == reference
            assert musashi.read(0x100000, 65536) == bytes(ram)
            assert bytes(cpu.mem_read(0x100000, 65536)) == bytes(ram)
            assert musashi.get_reg('a7') == cpu.reg_read(m.UC_M68K_REG_A7) == 0x1feffc
            rows.append(dict(high=high, low=low, extend=extend, reference=reference,
                             musashi=musashi_result, unicorn=unicorn_result))
    assert musashi.read(0, 0x100000) == bytes(unicorn_cpu.mem_read(0, 0x100000)) == program[:0x100000]
    assert sha((root / source['path']).read_bytes()) == source['sha256']
    differences = sum(row['musashi'] != row['reference'] for row in rows)
    assert differences == 301
    report = dict(source=source, reference_revision=REVISION, reference_files=urls,
                  table_sha256=TABLE_SHA, table_size=len(table), cases=len(rows),
                  unicorn_mismatches=0, musashi_mismatches=differences,
                  unicorn_provenance=oracle_provenance(),
                  musashi_library_sha256=sha(musashi.library_path.read_bytes()),
                  tool_sha256=sha(Path(__file__).read_bytes()), rows=rows,
                  scope='Original ROM through SBCD before BCC; source BYTE0, all256 destination BYTEs, both incoming X. Result BYTE and C/X only. Reference author reports Genesis Model1/Model3VA2 hardware tests; not local physical hardware measurement.')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(cases=len(rows), unicorn_mismatches=0, musashi_mismatches=differences, sha256=sha(report_path.read_bytes()))))


if __name__ == '__main__':
    main()
