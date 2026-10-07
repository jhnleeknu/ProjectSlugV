"""Check packaged scene bytes, C++ decoding and original dispatch targets."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from pack_scene_scripts import SOURCE_SHA256, wrap
from pack_stage_catalog import decode_group, INDEX, COUNT


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert source['sha256'] == SOURCE_SHA256
    folder = root / 'extracted/runtime/scene_scripts'
    manifest = json.loads((folder / 'manifest.json').read_text())
    output = root / 'artifacts/scene_script_resources'
    output.mkdir(parents=True, exist_ok=True)
    report = output / 'verification.json'
    report.unlink(missing_ok=True)
    executable = root / 'build/inspect_scene_script'
    binary = hashlib.sha256(executable.read_bytes()).hexdigest()
    references = []
    for group, address in enumerate(struct.unpack_from('>%dI' % COUNT, program, INDEX)):
        for area, record in enumerate(decode_group(program, address)['records']):
            at = record['source_cpu_address']
            pointer = struct.unpack_from('>I', program, at + 2)[0]
            references.append(dict(group=group, area=area, record_cpu_address=at,
                                   script_cpu_address=pointer,
                                   resource_id='scene-script:%08x' % pointer if pointer else None))
    assert manifest['references'] == references
    assert {s['source_cpu_address'] for s in manifest['scripts']} == {r['script_cpu_address'] for r in references} - {0}
    cpu = make_cpu(program)
    # The first20 dispatch entries are BRA.W to handlers; stop before handlers.
    targets = {}
    for opcode in range(0, 0x50, 4):
        entry = 0x1a0bc + opcode
        assert program[entry:entry + 2] == b'\x60\x00'
        targets[opcode] = entry + 2 + struct.unpack_from('>h', program, entry + 2)[0]
    reached = []
    def hook(cpu, address, size, user):
        if address in targets.values():
            reached.append(address)
            cpu.emu_stop()
    cpu.hook_add(unicorn.UC_HOOK_CODE, hook)
    rows = []
    command_count = inline_count = 0
    for item in manifest['scripts']:
        path = folder / item['file']
        raw = path.read_bytes()
        address, end = item['source_cpu_address'], item['end_exclusive']
        payload = program[address:end]
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        assert raw == wrap(payload, address)
        result = subprocess.run([str(executable), str(path)], capture_output=True, text=True, check=True)
        decoded = json.loads(result.stdout)
        assert decoded['source_cpu_address'] == address
        reconstructed = bytearray()
        cursor = address
        for command in decoded['commands']:
            assert command['address'] == cursor
            operands, inline = bytes.fromhex(command['operandhex']), bytes.fromhex(command['inlinehex'])
            encoded = struct.pack('>H', command['opcode']) + operands + inline
            assert program[cursor:cursor + len(encoded)] == encoded
            reached.clear()
            cpu.reg_write(m.UC_M68K_REG_A1, cursor)
            cpu.reg_write(m.UC_M68K_REG_D7, 0xabcd1234)
            cpu.reg_write(m.UC_M68K_REG_SR, 0x2000)
            cpu.emu_start(0x1a0b6, 0xffffff, count=4)
            assert reached == [targets[command['opcode']]]
            assert cpu.reg_read(m.UC_M68K_REG_A1) == cursor + 2
            assert cpu.reg_read(m.UC_M68K_REG_D7) == 0xabcd0000 | command['opcode']
            reconstructed.extend(encoded)
            cursor += len(encoded)
            assert command['next'] == cursor
            command_count += 1
            inline_count += bool(inline)
        assert cursor == decoded['terminator_address'] == item['terminator_cpu_address']
        assert decoded['terminator_opcode'] & 0x8000
        reconstructed.extend(struct.pack('>H', decoded['terminator_opcode']))
        assert bytes(reconstructed) == payload and cursor + 2 == end
        rows.append(dict(source_cpu_address=address, commands=len(decoded['commands']),
                         payload_bytes=len(payload), payload_sha256=hashlib.sha256(payload).hexdigest()))
    negatives = []
    path = output / 'bad.ms5d'
    cases = {
        'unknown-opcode': wrap(bytes.fromhex('0050ffff'), 2),
        'truncated-operands': wrap(bytes.fromhex('00000000'), 2),
        'missing-terminator': wrap(bytes.fromhex('00480001'), 2),
        'negative-inline-skip': wrap(bytes.fromhex('002c00000000ffff'), 2),
        'odd-inline-skip': wrap(bytes.fromhex('002c00000000000100ffff'), 2),
        'trailing-after-terminator': wrap(bytes.fromhex('ffff0000'), 2),
        'zero-source': wrap(bytes.fromhex('ffff'), 0),
        'odd-source': wrap(bytes.fromhex('ffff'), 3),
        'truncated-header': b'MS5D',
    }
    corrupt = bytearray(wrap(bytes.fromhex('ffff'), 2)); corrupt[-1] ^= 1
    cases['bad-crc'] = corrupt
    for label, data in cases.items():
        path.write_bytes(data)
        result = subprocess.run([str(executable), str(path)], capture_output=True, text=True)
        assert result.returncode and not result.stdout and path.read_bytes() == data, label
        negatives.append(label)
    assert bytes(cpu.mem_read(0, 0x100000)) == program[:0x100000]
    assert hashlib.sha256(executable.read_bytes()).hexdigest() == binary
    data = dict(source=source, binary_sha256=binary, scripts=len(rows), references=len(references),
                payload_bytes=sum(r['payload_bytes'] for r in rows), commands=command_count,
                opaque_inline_blocks=inline_count, negative_cases=negatives, results=rows,
                native_dispatch_targets=targets,
                scope='All resource bytes and C++ command boundaries reconstruct the original spans. '
                      'Original1a0b6 dispatch executes MOVE.W/JMP/BRA only and stops before handlers. '
                      'No handler effects, complete scene initialization, external map/path resources, '
                      'natural reachability or rendered gameplay are proven.')
    report.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(dict(scripts=len(rows), commands=command_count, negatives=len(negatives),
                         sha256=hashlib.sha256(report.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
