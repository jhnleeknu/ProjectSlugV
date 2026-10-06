"""Compare preserved stage resources and C++ queries/state with original M68000."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib

import unicorn
from unicorn.m68k_const import (UC_M68K_REG_A0, UC_M68K_REG_A5,
                               UC_M68K_REG_A7, UC_M68K_REG_D0,
                               UC_M68K_REG_D1, UC_M68K_REG_PC)
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
COUNTS = [11, 6, 14, 5, 9, 3, 3, 3, 2, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1]
INDEX = 0x474f4


def checked_resource(path, program, address, end):
    packed = path.read_bytes()
    header = struct.unpack_from('<4s7I', packed)
    payload = packed[32:]
    expected = (b'MS5D', 1, 1, address, address, end - address,
                zlib.crc32(payload), 0)
    if header != expected or payload != program[address:end]:
        raise ValueError('Packed resource differs from original: ' + str(path))
    return hashlib.sha256(packed).hexdigest()


def verify_resources(folder, program, source):
    manifest = json.loads((folder / 'manifest.json').read_text())
    if (manifest['schema_version'], manifest['id'], manifest['format'],
            manifest['version'], manifest['source'], manifest['index_file'],
            manifest['index_cpu_address']) != (
            1, 'stage-catalog:000474f4', 'MS5D', 1, source,
            'stage_index.ms5d', INDEX):
        raise ValueError('Stage manifest identity/source mismatch')
    index_hash = checked_resource(folder / manifest['index_file'], program,
                                  INDEX, INDEX + 19 * 4)
    if index_hash != manifest['index_sha256'] or len(manifest['groups']) != 19:
        raise ValueError('Stage index metadata mismatch')
    groups = []
    for number, address in enumerate(struct.unpack_from('>19I', program, INDEX)):
        cursor = address + 2
        records = []
        while True:
            length = struct.unpack_from('>h', program, cursor)[0]
            cursor += 2
            if length == 0:
                break
            if length < 20 or length & 1 or cursor + length > 0x100000:
                raise ValueError('Original stage record length outside verified constraints')
            payload = program[cursor:cursor + length]
            if 0 not in payload[18:]:
                raise ValueError('Original stage name lacks terminator')
            records.append({'id': 'stage-record:%08x' % cursor,
                            'source_cpu_address': cursor, 'source_rom_offset': cursor,
                            'size': length, 'opaque_header_hex': payload[:18].hex(),
                            'name_cpu_address': cursor + 18,
                            'name_and_padding_hex': payload[18:].hex()})
            cursor += length
        filename = 'stage_group_%02d.ms5d' % number
        resource_hash = checked_resource(folder / filename, program, address, cursor)
        group = {'source_cpu_address': address,
                 'header': struct.unpack_from('>H', program, address)[0],
                 'end_cpu_address': cursor, 'records': records,
                 'id': 'stage-group:%02d' % number, 'index': number, 'file': filename,
                 'size': 32 + cursor - address, 'sha256': resource_hash}
        if manifest['groups'][number] != group:
            raise ValueError('Stage group manifest differs from original: ' + str(number))
        groups.append(group)
    if [len(group['records']) for group in groups] != COUNTS:
        raise ValueError('Original stage record counts changed')
    return groups


def call(cpu, entry, d0, d1):
    # The return stack is outside the entire 64 KiB RAM compared below.
    for reg, value in ((UC_M68K_REG_D0, d0), (UC_M68K_REG_D1, d1),
                       (UC_M68K_REG_A5, 0x108000), (UC_M68K_REG_A7, 0x1feffc)):
        cpu.reg_write(reg, value)
    cpu.mem_write(0x1feffc, (0xff000).to_bytes(4, 'big'))
    cpu.emu_start(entry, 0xff000, count=10000)
    if cpu.reg_read(UC_M68K_REG_PC) != 0xff000:
        raise ValueError('Original stage routine did not return: ' + hex(entry))


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported program revision')
    resources = root / 'extracted/runtime/stages'
    groups = verify_resources(resources, program, source)
    folder = root / 'artifacts/stage_catalog'
    folder.mkdir(parents=True, exist_ok=True)
    report_path = folder / 'verification.json'
    report_path.unlink(missing_ok=True)
    cpu = make_cpu(program)
    queries, state_rows = [], []
    stages = list(range(21)) + [255, 256, 32768, 65535]
    areas = list(range(16)) + [255, 65535]
    for stage, area in itertools.product(stages, areas):
        call(cpu, 0x48262, stage, 0)
        count = cpu.reg_read(UC_M68K_REG_D1) & 65535
        call(cpu, 0x474e2, stage, area)
        call(cpu, 0x47540, stage, area)
        record = cpu.reg_read(UC_M68K_REG_A0)
        call(cpu, 0x4827e, stage, area)
        name = cpu.reg_read(UC_M68K_REG_A0)
        expected = {'count': count, 'record': record, 'name': name}
        result = subprocess.run([str(root / 'build/query_stage'), str(resources),
                                 str(stage), str(area)], capture_output=True, text=True)
        if result.returncode or json.loads(result.stdout) != expected:
            raise ValueError('Stage query mismatch: ' + repr((stage, area, expected,
                                                           result.stdout, result.stderr)))
        queries.append(dict(stage=stage, area=area, **expected))

    inp, out = folder / 'input.bin', folder / 'cpp.bin'
    state_cases = [(action, value, None) for action, value in itertools.product(
        (0, 1), (0, 1, 18, 19, 255, 256, 0x7fff, 0xffff))]
    state_cases += [(2, 0xffff - old, old) for old in range(256)]
    for index, (action, value, old) in enumerate(state_cases):
        ram = bytearray(hashlib.shake_256(
            b'ms5-stage-state-v1' + index.to_bytes(4, 'big')).digest(65536))
        if old is not None:
            ram[0xbad] = old
        cpu.mem_write(0x100000, bytes(ram))
        call(cpu, (0x4823a, 0x48250, 0x48256)[action], value, 0)
        expected = bytes(cpu.mem_read(0x100000, 65536))
        inp.write_bytes(ram)
        out.unlink(missing_ok=True)
        result = subprocess.run([str(root / 'build/stage_state'), str(inp), str(out),
                                 str(action), str(value)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('C++ stage state rejected input: ' + result.stderr)
        actual = out.read_bytes()
        if actual != expected:
            differences = [(hex(i), expected[i], actual[i]) for i in range(
                min(len(actual), len(expected))) if expected[i] != actual[i]]
            raise ValueError('Stage state mismatch: ' + repr((action, value, old,
                                                             len(actual), differences[:12])))
        state_rows.append({'action': action, 'value': value, 'old_step_byte': old,
                           'input_sha256': hashlib.sha256(ram).hexdigest(),
                           'ram_sha256': hashlib.sha256(expected).hexdigest()})
    report = {
        'source': source, 'emulator': 'Unicorn ' + unicorn.__version__,
        'cpu_model': 'M68000', 'program_code_modified': False,
        'address_mapping': 'Verified fixed ROM: CPU address equals decrypted file offset below 0x100000.',
        'entries_cpu_address': {'group': 0x474e2, 'record': 0x47540,
                               'count': 0x48262, 'name': 0x4827e,
                               'set_stage': 0x4823a, 'set_area': 0x48250,
                               'next_area': 0x48256},
        'group_count': len(groups), 'record_count': sum(COUNTS),
        'record_counts': COUNTS, 'packed_payloads_and_manifest_equal': True,
        'query_cases': len(queries), 'query_outputs_equal': True,
        'state_cases': len(state_rows), 'state_whole_65536_byte_ram_equal': True,
        'query_results': queries, 'state_results': state_rows,
        'scope': 'Original unmodified fixed-ROM routines versus C++ stage query/state CLIs. '
                 'All 19 groups, 59 opaque record payloads, names/control/padding, source addresses, '
                 'index and canonical manifest checked against original. Queries cover stages 0..20, '
                 '255/256/32768/65535 and areas 0..15/255/65535. State actions 0/1 cover eight word '
                 'boundaries; action 2 covers all 256 source bytes and varying ignored values. '
                 'Entire RAM compared with deterministic unrelated random bytes. '
                 'Gameplay meaning, referenced maps/scripts, natural reachability, CPU flags/other '
                 'register equivalence, hardware timing and full boot are outside scope.'}
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print('Stage catalog original/C++ match:', len(queries), 'queries;',
          len(state_rows), 'whole-RAM state cases;', len(groups), 'groups;', sum(COUNTS), 'records')


if __name__ == '__main__':
    main()
