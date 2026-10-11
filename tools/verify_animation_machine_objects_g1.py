"""F4 U01..U16 original-ROM differential verification through the public C++ API.

Typed test inputs are reused, never their expected outputs or synthetic ROM bytes.
G1 frozen native fixtures are independently replayed without rerunning their search.
Unknown C is a public abstraction; native branch results verify consumer behavior.
The inherited G1 MOVE SR probe is diagnostic only, never a carry equality oracle.
Checked errors preserve all public outputs and are reported apart from execution passes.
"""
import argparse
import collections
import ctypes
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import struct
import subprocess
import time
import verify_animation_machine as common
import observe_animation_machine_objects_g1 as native
import pack_physical_program as physical
import unicorn

ROOT = Path(__file__).resolve().parents[1]
ROM_SHA = physical.SOURCE_SHA256
ENV = None
ROUTED = None
DIAGNOSTIC_EXE = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture_inputs(path):
    text = path.read_text()
    section = text.split('const Fixture FIXTURES[]={', 1)[1].split('\n};', 1)[0]
    # Parse only input fields. In particular no expected register/digest is read.
    pattern = r'\{"([^"\\]*)",(0x[0-9a-f]+),(0x[0-9a-f]+),(\d+),\{([^}]*)\},"([^"\\]*)",(NULL|"[^"\\]*")'
    matches = list(re.finditer(pattern, section))
    assert len(matches) == len(re.findall(r'^\s*\{"', section, re.M)), path
    for match in matches:
        name, entry, stop, carry, values, edits, error = match.groups()
        if error != 'NULL':
            continue  # synthetic checked-negative expectations are not an original oracle
        regs = [int(v.strip(), 0) for v in values.split(',')]
        assert len(regs) == 16
        ram = bytearray(65536)
        ram[0xf000:0xf004] = bytes.fromhex('000ff000')
        for item in edits.split(','):
            if not item:
                continue
            address, data = item.split(':')
            address = int(address, 16)
            for offset, value in enumerate(bytes.fromhex(data)):
                ram[(address + offset) & 65535] = value
        ccr = 1 if int(carry) == 2 else 0
        flag_precondition = None
        if int(entry, 16) == 0xd73ca:
            address = (regs[8] + 0x10) & 65535
            word = (ram[address] << 8) | ram[(address + 1) & 65535]
            if (regs[0] & 65535) == word:
                ccr |= 4
            flag_precondition = 'U04 contract decision 2: incoming Z = (D0.W == WORD 10(A0)); test lines 17 and 357'
        if int(entry, 16) == 0x4beec:
            if (regs[7] & 255) == 0:
                ccr |= 4
            flag_precondition = 'U08b contract decision 3: incoming Z = (D7.B == 0), unique ADD.B D7,D7 predecessor'
        if int(entry, 16) in (0x70198, 0x701cc):
            address = regs[11] & 65535
            word = (ram[address] << 8) | ram[(address + 1) & 65535]
            if word & 0x8000:
                ccr |= 8
            flag_precondition = 'U12 contract decision 4 and test header: incoming N = WORD (A3) bit 15, 49a80 SUB.W D0,(A3); RTS'
        yield dict(name=name, pc=int(entry, 16), stop=int(stop, 16),
                   carry=int(carry), regs=dict(zip(common.REGS, regs)), ram=bytes(ram),
                   bank=(0x200000, 0xa0, 0x1000), ccr=ccr,
                   provenance=dict(test=str(path.relative_to(ROOT)), test_sha256=sha(path.read_bytes()),
                                   ram_edits=edits, initial_CCR=ccr, flag_precondition=flag_precondition, expected_outputs_used=False, synthetic_ROM_used=False))


def g1_inputs(folder):
    doc = json.load(gzip.open(folder / 'fixtures.json.gz', 'rt'))
    for row in doc['fixtures']:
        if row['final'] != 'stop':
            continue  # guards recorded separately by the original observer
        start = row['start']
        ram = (folder / 'blobs' / (start['ram'] + '.bin')).read_bytes()
        assert sha(ram) == start['ram']
        yield dict(name=row['name'], pc=start['pc'], stop=row['final_detail']['pc'],
                   carry=2 if (start['ccr'] or 0) & 1 else 1, regs=start['regs'], ram=ram,
                   bank=tuple(start['bank']), ccr=start['ccr'],
                   provenance=dict(native_fixture=row['name'], source_ram_sha256=start['ram'],
                                   source_state_sha256=start['state'], edits=row['edits'],
                                   declared_state=True, expected_outputs_used=False))


def native_one(fixture):
    st = dict(ram=fixture['ram'], regs=fixture['regs'], pc=fixture['pc'],
              bank=fixture['bank'], ccr=fixture['ccr'])
    machine = native.make_machine(ENV, st)
    pcs = []
    stopped = [False]
    trap = [None]
    def code(cpu, pc, size, unused):
        if pc == fixture['stop']:
            stopped[0] = True
            cpu.emu_stop()
            return
        if ENV.program[pc:pc + 2] == bytes.fromhex('4e4f'):
            trap[0] = pc
            cpu.emu_stop()
            return
        pcs.append(pc)
    execution_hook = machine.cpu.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
    error = None
    try:
        machine.cpu.emu_start(st['pc'], 0xffffff, count=10000)
    except unicorn.UcError as exception:
        error = str(exception)
    guard = native.guard_of(machine)
    machine.cpu.hook_del(execution_hook)  # post-stop diagnostic CCR probe is not an execution PC
    final = native.capture(machine)
    kind = 'stop' if stopped[0] else ('trap' if trap[0] is not None else ('guard' if guard or error else 'step-limit'))
    return dict(kind=kind, guard=guard, error=error, state=final, ports=list(machine.ports),
                pcs=pcs, trap=trap[0], device_reads=list(machine.dev_reads))


def pvc_of(bank):
    pvc = bytearray(8192)
    pvc[0x1ff0:0x1ff2] = bank[1].to_bytes(2, 'big')
    pvc[0x1ff2:0x1ff4] = bank[2].to_bytes(2, 'big')
    return bytes(pvc)



def router_bitmap():
    """Independent inventory of the public dispatch conditions, adapted from reviewed Claude hroute."""
    source = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = source[source.index('bool ok=false;'):source.index('else return am_error(c,"unsupported animation machine PC")')]
    trap_body = source[source.index('bool stage_event_ops_trap('):source.index('std::uint32_t pvc_word(')]
    traps = set(int(value,16) for value in re.findall(r'pc==0x([0-9a-f]+)',trap_body))
    rules = re.findall(r'if \((.*?)\)ok=(animation_\w+)\(c\);',body,re.S)
    assert len(rules) >= 40
    expressions = []
    for condition, function in rules:
        expression = condition.replace('next.pc','pc').replace('&&',' and ').replace('||',' or ').replace('\n',' ')
        expression = expression.replace('!stage_event_ops_trap(pc)','(pc not in traps)')
        expressions.append(compile(expression,'<dispatch inventory>','eval'))
    numbers = set(int(value,16) for value in re.findall(r'0x([0-9a-f]+)',body)) | traps
    points = sorted({0,0x100000} | {number & ~1 for number in numbers} | {(number+2) & ~1 for number in numbers})
    bitmap = bytearray(0x80000)
    for low, high in zip(points,points[1:]):
        if low >= 0x100000: continue
        for pc in ([low,low+2] if high-low>2 else [low]):
            if any(eval(expression,{'__builtins__':{},'pc':pc,'traps':traps}) for expression in expressions):
                end = high if pc != low else low+2
                bitmap[pc>>1:end>>1] = bytes([1]) * ((end-pc)//2)
    return bitmap


def checked_error_evidence(fixture, observation, error):
    global ROUTED
    if ROUTED is None: ROUTED = router_bitmap()
    unsupported = [pc for pc in observation['pcs'] if pc & 1 or pc >= 0x100000 or not ROUTED[pc>>1]]
    match = re.fullmatch(r'unsupported animation objects u(02|06) PC', error)
    if match:
        unit = int(match.group(1))
        entry = fixture['pc']
        approved = entry < 0x100000 and entry % 2 == 0 and ENV.unit[entry >> 1] == unit and entry not in ENV.starts
        return approved, dict(declared_direct_entry_interior_PC=entry, unit=unit,
                              contract_sha256=ENV.contracts[unit]['sha'], public_block_entry_supported=False)
    if error == 'unsupported animation machine PC':
        pc = observation.get('diagnostic_error_PC')
        reached = pc in observation['pcs'] or pc == observation['trap']
        missing = pc is not None and (pc & 1 or pc >= 0x100000 or not ROUTED[pc >> 1])
        approved = reached and missing and observation.get('diagnostic_public_outputs_equal', False)
        return approved, dict(actual_CPP_missing_PC=pc, native_reaches_actual_missing_PC=reached,
                              current_dispatch_missing=missing,
                              diagnostic_public_outputs_equal=observation.get('diagnostic_public_outputs_equal', False))
    if error == 'program bus requires even WORD/LONG address':
        guard = observation['guard']
        return bool(guard and guard[0] in ('odd-read','odd-write')), dict(native_guard=guard)
    if error == 'unaligned animation machine PC' or error == 'animation fade card odd JSR target':
        guard = observation['guard']
        return bool(guard and guard[0] in ('odd-pc','fetch-unmapped','fetch-protected')), dict(native_guard=guard)
    if error == 'stage area RNG pointer outside work RAM':
        return 0x49a80 in observation['pcs'] and observation['kind']=='guard', dict(native_rng_write_PC=0x49a80)
    if error in ('program bus write requires RAM mirror units','unsupported animation machine write device'):
        guard = observation['guard']
        return bool(guard and guard[0] in ('rom-write','write-unmapped','pvc-page','write-protected')), dict(native_guard=guard)
    if error == 'objects u09 caller requires known carry':
        address = fixture['regs']['a7'] & 65535
        initial_return = int.from_bytes(fixture['ram'][address:address + 4], 'big')
        pcs = observation['pcs']
        absent_producers = all(pc not in pcs for pc in (0x1ab02, 0x1ab7a, 0x1aafc))
        approved = initial_return == 0x76a08 and 0x76a08 in pcs and absent_producers
        return approved, dict(boundary_kind='declared-artificial-return-without-known-carry-producer',
                              initial_return_PC=initial_return, native_consumer_PC=0x76a08,
                              legitimate_producer_absent=absent_producers,
                              contract='docs/analysis/animation-machine-objects-u09-contract.md')
    if error == 'cue wrapper failure requires known caller X':
        pcs = observation['pcs']
        node = fixture['regs']['a6'] & 65535
        callback = int.from_bytes(fixture['ram'][node:node + 4], 'big')
        approved = (callback == 0xe585c and all(pc in pcs for pc in (0xe586c, 0x2986, 0x28ae, 0x290e, 0xe5872))
                    and 0xe8a48 not in pcs and ENV.program[0xe586c:0xe5872] == bytes.fromhex('4eb900002986'))
        return approved, dict(boundary_kind='documented-cue-caller-X-limitation', callback=callback,
                              actual_saved_return_PC=0xe5872, supported_saved_return_PC=0xe8a8a,
                              native_failure_PC=0x290e, contract='docs/analysis/animation-machine-objects-u07-contract.md',
                              contract_sha256=sha((ROOT/'docs/analysis/animation-machine-objects-u07-contract.md').read_bytes()))
    if error.endswith('requires known carry') and fixture['carry'] == 0:
        unit = fixture.get('unit','')
        path = ROOT / ('docs/analysis/animation-machine-objects-u%s-contract.md' % unit)
        documented = path.exists() and error in path.read_text()
        return documented, dict(declared_unknown_C=True, contract=str(path.relative_to(ROOT)) if path.exists() else None)
    return False, dict(unapproved_error=error)


def contract_coverage(coverage):
    result = {}
    for path in sorted((ROOT/'docs/analysis').glob('animation-machine-objects-u*-contract.md')):
        text = path.read_text()
        section = text[text.index('## block 목록'):]
        end = section.find('\n## ',5)
        if end != -1: section = section[:end]
        starts = []
        for line in section.splitlines():
            match = re.match(r'^- ((?:`[0-9a-f]{3,6}`[ ,]*)+):',line)
            if match: starts.extend(int(value,16) for value in re.findall(r'`([0-9a-f]+)`',match.group(1)))
        assert starts and len(starts)==len(set(starts)),path
        denominator = int(re.search(r'\[F\] (\d+) block',section).group(1))
        unit = path.stem.split('-u')[1].split('-')[0]
        if len(starts) != denominator:
            # Contracts compress tables/formula families; the bounded test enumerates input PCs only.
            test = ROOT / ('engine/tests/animation_machine_objects_u%s_test.cpp' % unit)
            table = test.read_text().split('const Block BLOCKS[]={',1)[1].split('\n};',1)[0]
            expanded = set(int(value,16) for value in re.findall(r'\{(0x[0-9a-f]+),',table))
            assert set(starts) <= expanded and len(expanded)==denominator,(unit,len(expanded),denominator)
            starts = sorted(expanded)
        observed = set(coverage.get(unit,()))
        if int(unit[:2]) <= 7: observed.update(coverage.get('g1',()))
        result[unit] = dict(contract_sha256=sha(path.read_bytes()), block_denominator=len(starts),
                            native_observed_starts=len(set(starts)&observed),
                            missing_native_starts=sorted(set(starts)-observed),
                            claim='native observation only; checked errors are not C++ execution coverage')
    return result


def audit_row(fixture, observation, actual):
    result, ram, pvc, ports, error = actual
    initial = dict(fixture['regs'], pc=fixture['pc'], carry=fixture['carry'])
    row = dict(name=fixture['name'], entry=fixture['pc'], declared_stop=fixture['stop'],
               provenance=fixture['provenance'], native_kind=observation['kind'],
               native_pc=observation['state']['pc'], native_guard=observation['guard'],
               native_instructions=len(observation['pcs']), cpp_ok=result['ok'], cpp_error=error,
               cpp_pc=result['pc'], differences=[])
    if not result['ok']:
        marker = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
        preserved = (ram == fixture['ram'] and pvc == pvc_of(fixture['bank']) and ports == marker
                     and all(result[k] == initial[k] for k in common.STATE_KEYS)
                     and result['bank_base'] == fixture['bank'][0]
                     and result['external_reads'] == 0x12345678 and result['status'] == 1)
        approved, evidence = checked_error_evidence(fixture, observation, error)
        row.update(verdict='checked-boundary' if approved else 'mismatch', rollback_verified=preserved, checked_error_evidence=evidence)
        if not approved: row['differences'].append('unapproved or unsupported-error without native evidence')
        if not preserved or not error:
            row['differences'].append('failure must preserve every public output')
        return row
    if result['status'] == 1:
        row['verdict'] = 'wait-control-only-boundary'
        if result['pc'] not in observation['pcs']:
            row['differences'].append('wait PC absent from native path')
        return row
    row['verdict'] = 'execution-equal'
    final = observation['state']
    if observation['kind'] != 'stop':
        row['differences'].append('C++ succeeded but native did not reach declared stop')
    for key in common.REGS + ('pc',):
        if result[key] != (final['pc'] if key == 'pc' else final['regs'][key]):
            row['differences'].append(key)
    if ram != final['ram']:
        row['differences'].append('RAM')
    if pvc != pvc_of(final['bank']) or result['bank_base'] != final['bank'][0]:
        row['differences'].append('PVC/bank')
    expected_ports = b''.join(struct.pack('>BII', size, address, value) for _, address, size, value in observation['ports'])
    if ports != expected_ports:
        row['differences'].append('ordered ports')
    row['cpp_carry_class'] = result['carry']
    row['native_probe_C_diagnostic'] = None if final['ccr'] is None else final['ccr'] & 1
    row['native_C_probe_used_as_oracle'] = False
    row['native_RAM_sha256'] = sha(final['ram'])
    row['cpp_RAM_sha256'] = sha(ram)
    if row['differences']:
        row['verdict'] = 'mismatch'
    return row


def execute_fixture(argument):
    index, fixture, scratch, executable, resources = argument
    observed_pcs = []
    ok, observation, _ = native.isolated(native_one, fixture)
    label = 'row_%05d' % index
    if not ok:
        row = dict(name=fixture['name'], unit=fixture['unit'], verdict='native-translator-abort',
                   entry=fixture['pc'], provenance=fixture['provenance'])
    elif observation['kind'] == 'step-limit':
        row = dict(name=fixture['name'], unit=fixture['unit'], verdict='native-step-limit',
                   entry=fixture['pc'], native_instructions=len(observation['pcs']), provenance=fixture['provenance'])
    elif fixture['unit'] == 'g1' and fixture['pc'] == 0xd73ca and bool(fixture['ccr'] & 4) != ((fixture['regs']['d0'] & 65535) == int.from_bytes(bytes(fixture['ram'][((fixture['regs']['a0'] + 0x10 + i) & 65535)] for i in range(2)), 'big')):
        address = (fixture['regs']['a0'] + 0x10) & 65535
        row = dict(name=fixture['name'], unit=fixture['unit'], verdict='invalid-declared-flag-precondition',
                   entry=fixture['pc'], provenance=fixture['provenance'], native_kind=observation['kind'],
                   input_D0_WORD=fixture['regs']['d0'] & 65535,
                   input_RAM_WORD=int.from_bytes(bytes(fixture['ram'][(address + i) & 65535] for i in range(2)), 'big'),
                   input_CCR=fixture['ccr'], original_G1_input_preserved=True,
                   required_precondition='U04 contract decision 2: Z = (D0.W == WORD 10(A0))',
                   contract_sha256=sha((ROOT/'docs/analysis/animation-machine-objects-u04-contract.md').read_bytes()),
                   execution_equality_claimed=False, checked_CPP_boundary_claimed=False)
        observed_pcs = observation['pcs']
    else:
        observed_pcs = observation['pcs']
        state = dict(fixture['regs'], pc=fixture['pc'], carry=fixture['carry'])
        actual = common.invoke(executable, scratch, label, fixture['ram'], state,
                               pvc_of(fixture['bank']), fixture['bank'][0], resources, stop=fixture['stop'])
        if actual[4] == 'unsupported animation machine PC':
            diagnostic = common.invoke(DIAGNOSTIC_EXE, scratch, label + '_diagnostic', fixture['ram'], state,
                                       pvc_of(fixture['bank']), fixture['bank'][0], resources, stop=fixture['stop'])
            match = re.fullmatch(r'F4_DIAGNOSTIC_PC=([0-9a-f]{8})\nunsupported animation machine PC', diagnostic[4])
            observation['diagnostic_error_PC'] = int(match.group(1), 16) if match else None
            observation['diagnostic_public_outputs_equal'] = diagnostic[:4] == actual[:4]
            for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin', '_state.json'):
                (scratch / (label + '_diagnostic' + suffix)).unlink()
        row = audit_row(fixture, observation, actual)
        row['unit'] = fixture['unit']
        row['native_trace_sha256'] = sha(struct.pack('>%dI' % len(observation['pcs']), *observation['pcs']))
        for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin', '_state.json'):
            (scratch / (label + suffix)).unlink()
    return row, observed_pcs


def main():
    global ENV, ROUTED, DIAGNOSTIC_EXE
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'artifacts/animation_machine_objects_integration_execution')
    parser.add_argument('--g1-native', type=Path, default=ROOT / 'artifacts/animation_machine_objects_g1_native')
    parser.add_argument('--units', default='01,02,03,04,05,06,07,08,08b,09,10,11,12,13,14,15,15b,15c,16')
    parser.add_argument('--limit', type=int, default=0, help='Development subset, explicitly marked incomplete')
    parser.add_argument('--skip-g1', action='store_true')
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    started = time.time()
    executed_tool_sha = sha(Path(__file__).read_bytes())
    ROUTED = router_bitmap()
    args.out.mkdir(parents=True, exist_ok=False)
    scratch = args.out / 'work'
    scratch.mkdir()
    ENV = native.Env()
    assert sha(ENV.program) == ROM_SHA
    original_stat = native.ROM_PATH.stat()
    resources = []
    for offset in range(0, len(ENV.program), 0x100000):
        path = scratch / ('program_%06x.ms5d' % offset)
        path.write_bytes(physical.wrap(ENV.program[offset:offset + 0x100000], offset))
        resources.append(path)
    harness = scratch / 'machine.cpp'
    harness.write_text(common.HARNESS)
    executable = scratch / 'machine'
    sources = [ROOT / 'engine/src' / source for source in common.SOURCES]
    for source in sorted((ROOT / 'engine/src').glob('animation_machine_objects_u*.cpp')):
        if source not in sources:
            sources.append(source)
    for name in ('animation_machine_scheduler.cpp', 'animation_machine_stage_event.cpp', 'animation_machine_stage_event_ops.cpp'):
        source = ROOT / 'engine/src' / name
        if source.exists() and source not in sources:
            sources.append(source)
    command = ['clang++', '-std=c++11', '-O2', '-I' + str(ROOT / 'engine/include')] + list(map(str, sources)) + [str(harness), '-o', str(executable)]
    input_hashes = {str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in sources}
    subprocess.run(command, check=True, capture_output=True)
    # A separate read-only diagnostic copy reports the failing dispatcher PC.
    # Production outputs are still the oracle and must match this copy exactly.
    diagnostic_source = scratch / 'animation_machine_diagnostic.cpp'
    original_source = (ROOT/'engine/src/animation_machine.cpp').read_text()
    original_error = 'bool am_error(AnimationMachineContext& c,const char* message) {c.error=message;return false;}'
    assert original_source.count(original_error) == 1
    diagnostic_source.write_text('#include <cstdio>\n' + original_source.replace(original_error,
        'bool am_error(AnimationMachineContext& c,const char* message) {std::fprintf(stderr,"F4_DIAGNOSTIC_PC=%08x\\n",static_cast<unsigned>(c.s.pc));c.error=message;return false;}'))
    DIAGNOSTIC_EXE = scratch / 'machine_diagnostic'
    diagnostic_command = ['clang++', '-std=c++11', '-O2', '-I' + str(ROOT/'engine/include'), '-I' + str(ROOT/'engine/src')]
    diagnostic_command += [str(diagnostic_source if source.name == 'animation_machine.cpp' else source) for source in sources]
    diagnostic_command += [str(harness), '-o', str(DIAGNOSTIC_EXE)]
    subprocess.run(diagnostic_command, check=True, capture_output=True)
    fixtures = []
    for unit in args.units.split(','):
        path = ROOT / ('engine/tests/animation_machine_objects_u%s_test.cpp' % unit)
        assert path.exists(), path
        fixtures.extend(dict(fixture, unit=unit, name='u%s-%s' % (unit, fixture['name'])) for fixture in fixture_inputs(path))
    if not args.skip_g1:
        fixtures.extend(dict(fixture, unit='g1') for fixture in g1_inputs(args.g1_native))
    total = len(fixtures)
    if args.limit:
        fixtures = fixtures[:args.limit]
    rows = []
    covered = collections.defaultdict(set)
    arguments = [(index,fixture,scratch,executable,resources) for index,fixture in enumerate(fixtures)]
    with multiprocessing.get_context('fork').Pool(args.workers) as pool:
      for index, (row, observed_pcs) in enumerate(pool.imap(execute_fixture, arguments, chunksize=1)):
        covered[row['unit']].update(observed_pcs)
        rows.append(row)
        if row.get('differences'):
            print('MISMATCH', json.dumps(row, sort_keys=True), flush=True)
        if index % 100 == 0:
            print('rows', index + 1, 'of', len(fixtures), dict(collections.Counter(r['verdict'] for r in rows)), flush=True)
    report = dict(schema_version=1, ROM_sha256=ROM_SHA, complete_requested_matrix=not args.limit,
                  total_available_inputs=total, rows=len(rows), verdicts=dict(collections.Counter(r['verdict'] for r in rows)),
                  mismatches=[row for row in rows if row.get('differences')], results=rows,
                  instruction_PC_coverage={unit:sorted(pcs) for unit, pcs in covered.items()},
                  contract_coverage=contract_coverage(covered),
                  executed_tool_sha256=executed_tool_sha, workers=args.workers,
                  inputs=input_hashes,
                  build_command=command, diagnostic_build_command=diagnostic_command,
                  diagnostic_source_sha256=sha(diagnostic_source.read_bytes()), elapsed_seconds=time.time() - started,
                  limitations=['Declared typed states; no natural boot/IRQ claim.',
                               'Synthetic ROM overlays and expected test outputs are excluded.',
                               'Checked errors and waits are boundaries, not successful original execution.',
                               'Unknown public carry is not native full CCR.',
                               'U17+ and new RNG game units are outside scope.'])
    assert executed_tool_sha == sha(Path(__file__).read_bytes()), 'verifier changed during execution'
    assert all(sha((ROOT/path).read_bytes())==digest for path,digest in input_hashes.items()), 'C++ sources changed during execution'
    assert native.ROM_PATH.stat().st_mtime_ns == original_stat.st_mtime_ns
    assert sha(native.ROM_PATH.read_bytes()) == ROM_SHA
    (args.out / 'execution.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({key:report[key] for key in ('rows','verdicts','elapsed_seconds')}, sort_keys=True))
    return 1 if report['mismatches'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
