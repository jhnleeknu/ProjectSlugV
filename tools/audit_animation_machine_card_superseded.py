"""Strict API-only acceptance of five frozen card guard observations.

Reads the pinned completed reports. --run-save executes only the previously
unretained save guard into a new external directory; --save-receipt verifies
that saved supplemental call. No native continuation equality is claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

PINS = {
    'input': ('f4ee5eaef2db5ec4a29e2045d51404ff5641d03139242fc6ce93574b1e050bca', '49c1ba52f7ec11dc1929022f7dc6b455b434681d472e9a39631c69ea98ce9b46', 'native_guards_superseded_by_later_card_menu_cores', 119, 114, 5),
    'close': ('a2ee3906de92c27c10988425e04d4c68178a18bf54981b28c68abcdc643a289d', 'b5bd2164ab5badd5067b469d9d6c7d79b3cedeae2efca07d89ff18d4882a39dd', 'native_guards_superseded_by_nested_core', 83, 74, 9),
    'save': ('0e790b227f6c814e9d750517f5f9da36ec2d43a2eb8ffd3820644f71a5998471', 'b0f9e26195f9a31181a6164f4ee15b93497515a7782dccc7f5a0e74ada142c0c', 'native_guards_superseded', 95, 83, 12)}
# Frame-return stop is 2ac2. The save contract's BIOS stop policy (line 41)
# requires machine-error rollback for bd26 with a different stop.
SPECS = (
    ('input', 'guard-bd26-without-stop', False, 'unsupported animation machine PC', 0xc1e6, 1, 100),
    ('input', 'guard-a662-without-stop', True, '', 0x2ac2, 0, 8),
    ('close', 'guard-a698-without-stop', True, '', 0x2ac2, 0, 15),
    ('close', 'guard-a6da-lower-reaches-zero', True, '', 0x2ac2, 0, 28),
    ('save', 'guard-desc-flags-0001-9e94', True, '', 0x2ac2, 0, 10))
SUFFIXES = ('input.bin', 'pvc_input.bin', 'ram.bin', 'pvc.bin', 'ports.bin', 'state.json')


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned_json(path, expected):
    require(digest(path) == expected, ('JSON SHA', str(path)))
    return json.loads(path.read_text())


def reports(root, kind):
    pin = PINS[kind]
    out = root / ('artifacts/animation_machine_card_menu_%s_execution' % kind)
    native_dir = root / ('artifacts/animation_machine_card_menu_%s_native' % kind)
    report = pinned_json(out / 'verification.json', pin[0])
    verify_hashes({str(root / n): h for n, h in report['inputs'].items()})
    return out, report, native_dir, pinned_json(native_dir / 'observation.json', pin[1])


def phase_blob(folder, phase, suffix):
    name = next(n for n in phase['artifacts'] if n.endswith(suffix))
    path = folder / name
    require(digest(path) == phase['artifacts'][name], ('native blob SHA', name))
    return path.read_bytes()


def save_input(root):
    out, report, folder, native = reports(root, 'save')
    row = next(r for r in native['guarded_results'] if r['label'] == SPECS[-1][1])
    phase = row['phases'][-1]
    require(len(row['phases']) - 1 == 10 and phase['stop_pc'] == 0x2ac2, 'save frozen phase')
    ram = phase_blob(folder, phase, 'ram_before.bin')
    raw_pvc = phase_blob(folder, phase, 'pvc_before.bin')
    pvc = bytearray(raw_pvc)
    # The native raw PVC words differ from the normalized device held by C++.
    pvc[0x1ff0:0x1ff4] = struct.pack('>HH', phase['ff8_before'], phase['ff9_before'])
    return out, report, phase, ram, dict(phase['incoming'], carry=2), bytes(pvc), raw_pvc


def verify_hashes(hashes):
    for path, expected in hashes.items():
        require(digest(path) == expected, ('file SHA', path))


def run_save(root, output):
    require(not output.exists(), 'supplemental output directory must be new')
    require(not output.is_relative_to(root), 'supplemental outputs must be outside repository')
    import verify_animation_machine as common
    from disassemble_program import load_verified_program
    out, report, phase, ram, state, pvc, raw_pvc = save_input(root)
    exe = out / 'animation_machine_callers_harness'
    binary_sha = report['artifacts'][str(exe)]
    source_hashes = {str(root / n): s for n, s in report['inputs'].items() if n.startswith('engine/')}
    # Pin invocation/ROM/resource-generation source too; these are read-only helpers.
    for name in ('tools/verify_animation_machine.py', 'tools/disassemble_program.py', 'tools/pack_physical_program.py'):
        source_hashes[str(root / name)] = report['inputs'][name]
    source_hashes[str(out / 'harness.cpp')] = report['artifacts'][str(out / 'harness.cpp')]
    verify_hashes(source_hashes)
    require(digest(exe) == binary_sha, 'production harness SHA')
    program, source = load_verified_program(root)
    resources, resource_refs = common.resource_audit(root, program)
    resource_hashes = {str(root / n): s for n, s in resource_refs.items()}
    source_hashes[str(root / source['path'])] = source['sha256']
    output.mkdir(parents=True)
    actual = common.invoke(exe, output, 'save_guard', ram, state, pvc, phase['bank_before'], resources, stop=0x2ac2, external=0)
    result, unused_ram, unused_pvc, unused_ports, error = actual
    require(result['ok'] and result['pc'] == 0x2ac2 and result['status'] == 0 and error.strip() == '', 'save exact API endpoint')
    (output / 'save_guard_error.txt').write_text(error)
    payloads = {str(output / ('save_guard_' + s)): digest(output / ('save_guard_' + s)) for s in SUFFIXES}
    payloads[str(output / 'save_guard_error.txt')] = digest(output / 'save_guard_error.txt')
    verify_hashes(source_hashes)
    verify_hashes(resource_hashes)
    require(digest(exe) == binary_sha, 'production harness changed')
    receipt = dict(schema_version=1, label=SPECS[-1][1], report_sha256=PINS['save'][0], native_report_sha256=PINS['save'][1],
                   state=state, bank=phase['bank_before'], stop=0x2ac2, external=0, raw_native_PVC_sha256=hashlib.sha256(raw_pvc).hexdigest(),
                   binary={str(exe): binary_sha}, sources=source_hashes, resources=resource_hashes, payloads=payloads,
                   API_only=True, native_equal_prefix_phases_from_full_report=10, native_continuation_equivalence_claimed=False)
    path = output / 'receipt.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    return path


def audit(root, receipt_path):
    receipt = json.loads(receipt_path.read_text())
    require(receipt['label'] == SPECS[-1][1] and receipt['report_sha256'] == PINS['save'][0] and receipt['native_report_sha256'] == PINS['save'][1], 'save receipt provenance')
    require(receipt['API_only'] and not receipt['native_continuation_equivalence_claimed'], 'save receipt scope')
    for field in ('binary', 'sources', 'resources', 'payloads'):
        verify_hashes(receipt[field])
    save_out, save_report, phase, ram, state, pvc, raw_pvc = save_input(root)
    exe = save_out / 'animation_machine_callers_harness'
    require(receipt['binary'] == {str(exe): save_report['artifacts'][str(exe)]}, 'receipt production binary pin')
    expected_sources = {str(root / n): h for n, h in save_report['inputs'].items() if n.startswith('engine/')}
    for name in ('tools/verify_animation_machine.py', 'tools/disassemble_program.py', 'tools/pack_physical_program.py'):
        expected_sources[str(root / name)] = save_report['inputs'][name]
    expected_sources[str(save_out / 'harness.cpp')] = save_report['artifacts'][str(save_out / 'harness.cpp')]
    expected_sources[str(root / save_report['source']['path'])] = save_report['source']['sha256']
    require(receipt['sources'] == expected_sources, 'receipt complete source pins')
    expected_resources = {str(root / n): h for n, h in save_report['artifacts'].items() if n.startswith('extracted/runtime/program_rom/')}
    require(len(expected_resources) == 9 and receipt['resources'] == expected_resources, 'receipt eight resources and manifest pins')
    import verify_animation_machine as common
    from disassemble_program import load_verified_program
    program, source = load_verified_program(root)
    require(source == save_report['source'], 'current ROM provenance')
    unused_resources, resource_refs = common.resource_audit(root, program)
    require({str(root / n): h for n, h in resource_refs.items()} == expected_resources, 'current resource audit')
    require(len(receipt['payloads']) == 7, 'receipt complete six outputs plus stderr')
    require(receipt['state'] == state and receipt['bank'] == phase['bank_before'] and receipt['stop'] == 0x2ac2 and receipt['external'] == 0, 'save fixed invocation')
    require(receipt['raw_native_PVC_sha256'] == hashlib.sha256(raw_pvc).hexdigest(), 'save native PVC provenance')
    paths = {Path(n).name: Path(n) for n in receipt['payloads']}
    require(paths['save_guard_input.bin'].read_bytes() == ram and paths['save_guard_pvc_input.bin'].read_bytes() == pvc, 'save exact frozen inputs')
    saved_result = json.loads(paths['save_guard_state.json'].read_text())
    require(saved_result['ok'] and saved_result['pc'] == 0x2ac2 and saved_result['status'] == 0 and paths['save_guard_error.txt'].read_text().strip() == '', 'save receipt exact endpoint')
    results = []
    for kind, label, ok, error, pc, status, prefix in SPECS:
        out, report, folder, native = reports(root, kind)
        pin = PINS[kind]
        require(report['negative_count'] == pin[3] == len(report['negatives']) + len(report['native_guards_checked_API']), ('negative count', kind))
        require(len(report['negatives']) == pin[4] and len(report['native_guards_checked_API']) == pin[5], ('guard separation', kind))
        require(not any(r['label'] == label for r in report['negatives'] + report['native_guards_checked_API']), ('superseded counted negative', label))
        nrow = next(r for r in native['guarded_results'] if r['label'] == label)
        phase = nrow['phases'][-1]
        require(len(nrow['phases']) - 1 == prefix and phase['stop_pc'] == 0x2ac2, ('native prefix', label))
        cases = report['actual_CPP'].get('rows', report['actual_CPP'].get('matches'))
        case = next(r for r in cases if r['label'] == label)
        require(case['split_phases'] == prefix, ('continuation counted native equal', label))
        record = next(r for r in report[pin[2]] if r['label'] == label)
        require(record.get('CPP_now_ok', record.get('C_plus_plus_ok')) == ok and record.get('CPP_now_error', record.get('C_plus_plus_error')) == error and int(record.get('CPP_now_pc', record.get('C_plus_plus_pc')), 16) == pc, ('fixed recorded API outcome', label))
        rollback = False
        if kind != 'save':
            payloads = {}
            for suffix in SUFFIXES:
                path = out / ('guard_%s_%s' % (label, suffix))
                require(digest(path) == report['artifacts'][str(path)], ('saved artifact SHA', str(path)))
                payloads[suffix] = path.read_bytes()
            result = json.loads(payloads['state.json'])
            require(result['ok'] == ok and result['pc'] == pc and result['status'] == status, ('fixed saved API outcome', label))
            require(payloads['input.bin'] == phase_blob(folder, phase, 'ram_before.bin'), ('frozen RAM input', label))
            native_pvc = bytearray(phase_blob(folder, phase, 'pvc_before.bin'))
            native_pvc[0x1ff0:0x1ff4] = struct.pack('>HH', phase['ff8_before'], phase['ff9_before'])
            require(payloads['pvc_input.bin'] == bytes(native_pvc), ('frozen normalized PVC input', label))
            if not ok:
                incoming = dict(phase['incoming'], carry=2)
                require(all(result[k] == value for k, value in incoming.items()), 'bd26 registers/PC/carry rollback')
                require(payloads['ram.bin'] == payloads['input.bin'] and payloads['pvc.bin'] == payloads['pvc_input.bin'], 'bd26 RAM/PVC rollback')
                require(result['bank_base'] == phase['bank_before'] and result['external_reads'] == 0x12345678 and result['status'] == 1 and payloads['ports.bin'] == struct.pack('>BII', 1, 0xdeadbeef, 0x87), 'bd26 bank/ports/status/reads rollback')
                rollback = True
        else:
            require(record['C_plus_plus_status'] == status, 'save report status')
        results.append(dict(unit=kind, label=label, ok=ok, error=error, pc=hex(pc), status=status, full_rollback_checked=rollback,
                            native_equal_prefix_phases=prefix, continuation_in_native_equal_count=False, continuation_in_negative_count=False,
                            API_only=True, native_continuation_equivalence_claimed=False))
    return dict(schema_version=1, audit_tool_sha256=digest(__file__), save_receipt_sha256=digest(receipt_path), report_SHA_pins={k: v[0] for k, v in PINS.items()},
                rows=results, API_only=True, case_count_includes_guard_prefix_rows=True, failure=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--save-receipt', type=Path)
    mode.add_argument('--run-save', type=Path, metavar='NEW_EXTERNAL_DIRECTORY')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    require(not output.is_relative_to(root) and not output.exists(), 'audit output must be new and outside repository')
    receipt = run_save(root, args.run_save.resolve()) if args.run_save else args.save_receipt.resolve()
    result = audit(root, receipt)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(rows=len(result['rows']), failure=result['failure'], output=str(output))))


if __name__ == '__main__':
    main()
