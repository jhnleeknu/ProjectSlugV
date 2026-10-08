"""Bounded declared 24-bit bus adapter for three original opcode40 high-address cases.

No original instruction, fixture register or data is replaced. This is explicit host
mapping emulation, not Unicorn automatic masking or a physical hardware measurement.
Two reads at logical01000000 use a read-only alias of actual cart program[0:1000].
The third effectivefffffff0 masks to unsupported busfffff0 and stops before access.
Only isolated4a382..4a3ac is executed; no CCR/full40/natural reachability claim.
"""
import inspect
import json
from pathlib import Path
import unicorn
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_banked_handler as original

LABELS = ('bank3-first7ffc-ptr01000000-high', 'ram8000-ptr01000000-high',
          'ram8000-ptr00000010-secondffe0-negative-32bit')
ALIAS, PAGE = 0x01000000, 0x1000
sha = original.sha


class Observer(original.Observer):
    def prepare(self, fx):
        super().prepare(fx)
        self.effective_addresses = []
        self.cpu.mem_map(ALIAS, PAGE, unicorn.UC_PROT_READ)
        self.cpu.mem_write(ALIAS, self.program[:PAGE])
        return self

    def effective(self, cpu, pc):
        logical = super().effective(cpu, pc)
        bus = logical & 0xffffff
        self.effective_addresses.append(dict(pc=pc, logical=logical, bus=bus))
        return bus  # inherited guard classifies the declared bus address only

    def run(self):
        result = super().run()
        result['effective_addresses'] = self.effective_addresses
        result['alias_unchanged'] = bytes(self.cpu.mem_read(ALIAS, PAGE)) == self.program[:PAGE]
        if result['guard'] is not None:
            raw = self.effective_addresses[-1]
            assert raw['pc'] == result['guard']['pc']
            result['guard']['bus_address'] = result['guard'].pop('address')
            result['guard']['logical_address'] = raw['logical']
        return result


def adapted_bytes(program, fx, logical, size):
    """Independent per-byte wrap32/mask24 source selection, never CPU injection."""
    model = original.BusModel(program, fx['bank_base'], fx['ram'], fx['pvc'])
    return bytes(model.byte(((logical + i) & 0xffffffff) & 0xffffff) for i in range(size))


def run_case(program, case, index):
    fx = original.fixture(case, index, program)
    prefix = original.model(program, fx)
    assert prefix['stop_pc'] == 0x4a3a0
    assert prefix['guard']['problem'] == 'unsupported_high_32bit_effective_address'
    logical = prefix['guard']['address']
    bus = logical & 0xffffff
    obs = Observer(program)
    try:
        native = obs.prepare(fx).run()
    finally:
        obs.close()
    assert native['error'] is None and not native['invalid'] and not native['interrupts']
    assert all(native[k] for k in ('mirrors_coherent', 'mapped_rom_unchanged', 'pvc_unchanged', 'alias_unchanged'))
    assert native['outgoing']['a7'] == original.A7
    assert native['outgoing']['sr'] & 0xff00 == fx['sr'] & 0xff00
    accesses = [dict(pc=x['pc'], access=x['access'], address=x['address'], size=x['size'], bytes=x['bytes'])
                for x in native['reads'] + native['writes']]
    accesses.sort(key=lambda x: native['pcs'].index(x['pc']))
    wanted = [dict(pc=x['pc'], access=x['access'], address=x['address'], size=x['size'], bytes=x['bytes'])
              for x in prefix['accesses']]
    expected_regs = dict(prefix['registers'])
    expected_ram = bytearray(fx['ram'])
    if bus == 0:
        assert logical == ALIAS and native['guard'] is None
        data = adapted_bytes(program, fx, logical, 4)
        assert data == program[:4]
        wanted.append(dict(pc=0x4a3a0, access='read', address=logical, size=4, bytes=data.hex()))
        expected_regs['d7'] = int.from_bytes(data, 'big')
        destination = (expected_regs['a6'] + original.s16(expected_regs['d0'])) & 0xffffffff
        before = adapted_bytes(program, fx, destination, 4)
        wanted.append(dict(pc=0x4a3a4, access='write', address=destination, size=4, bytes=data.hex()))
        for i, value in enumerate(data):
            address = ((destination+i) & 0xffffffff) & 0xffffff
            assert original.RAM <= address < original.BANK
            expected_ram[address & 0xffff] = value
        assert len(native['writes']) == 1 and native['writes'][0]['before'] == before.hex()
        assert native['outgoing']['pc'] == original.STOP
        outcome = 'complete_with_declared_cart_vector_alias'
        assert native['pcs'] == [0x4a382, 0x4a384, 0x4a386, 0x4a388, 0x4a38e, 0x4a392,
            0x4a394, 0x4a39a, 0x4a39e, 0x4a3a0, 0x4a3a4, 0x4a3a8]
    else:
        assert logical == 0xfffffff0 and bus == 0xfffff0
        assert native['outgoing']['pc'] == 0x4a3a0 and not native['writes']
        assert native['guard']['problem'] == 'unsupported_device_region'
        assert native['guard']['logical_address'] == logical and native['guard']['bus_address'] == bus
        outcome = 'guard_unsupported_masked_device'
    assert accesses == wanted
    assert all(x['pc'] == x['hook_pc'] for x in native['reads'] + native['writes'])
    assert {k: native['outgoing'][k] for k in original.REG_NAMES} == expected_regs
    assert native['ram_after'] == bytes(expected_ram)
    assert native['outgoing']['a2'] == prefix['registers']['a2']  # raw high pointer retained
    return fx, native, dict(outcome=outcome, second_read_logical=logical, second_read_bus=bus,
                           expected_source='canonical program[0:4] under declared cart vector view' if bus == 0 else None)


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = original.load_verified_program(root)
    assert sha(program) == original.SOURCE_SHA256
    program = bytes(program)
    folder = root/'artifacts/animation_high_address_native'
    folder.mkdir(parents=True, exist_ok=True)
    report_path = folder/'observation.json'
    report_path.unlink(missing_ok=True)
    inputs_paths = ['tools/observe_animation_high_address.py', 'tools/observe_animation_banked_handler.py',
        'tools/disassemble_program.py', 'extracted/program/manifest.json', source['path'],
        'artifacts/animation_banked_handler_native/observation.json',
        'artifacts/animation_banked_handler_native/source.json',
        'artifacts/reference/neogeo.cpp', 'artifacts/reference/prot_pvc.cpp', 'artifacts/reference/revision.txt']
    inputs = {p: sha((root/p).read_bytes()) for p in inputs_paths}
    # Check the frozen parent report's input/artifact identities before reuse.
    parent = json.loads((root/inputs_paths[5]).read_text())
    assert parent['cases'] == 95 and parent['outcomes']['complete'] == 73
    assert parent['oracle']['library_sha256'] == sha(Path(uclib._name).read_bytes())
    assert parent['oracle']['wrapper_sha256'] == sha(Path(inspect.getfile(unicorn.Uc)).read_bytes())
    for path, digest in parent['inputs'].items():
        assert sha((root/path).read_bytes()) == digest, path
    for path, digest in parent['artifacts'].items():
        assert sha((root/'artifacts/animation_banked_handler_native'/path).read_bytes()) == digest, path
    rows, artifacts = [], {}
    for index, case in enumerate(original.cases()):
        if case['label'] not in LABELS:
            continue
        fx, native, details = run_case(program, case, index)
        frozen = parent['results'][index]
        prefix = original.model(program, fx)
        assert frozen['label'] == case['label']
        assert frozen['outgoing']['registers15'] == prefix['registers']
        assert frozen['stop_pc'] == 0x4a3a0
        assert frozen['guard']['address'] == details['second_read_logical']
        fx2, native2, details2 = run_case(program, case, index)
        assert (fx, native, details) == (fx2, native2, details2)
        stem = 'case_%04d' % index
        trace = {k: native[k] for k in ('pcs', 'reads', 'writes', 'effective_addresses', 'guard', 'invalid', 'interrupts', 'error')}
        payloads = {stem+'_ram_before.bin': fx['ram'], stem+'_ram_after.bin': native['ram_after'],
                    stem+'_pvc_incoming.bin': fx['pvc'], stem+'_trace.json': (json.dumps(trace, indent=2)+'\n').encode()}
        for name, data in payloads.items():
            (folder/name).write_bytes(data)
            artifacts[name] = sha(data)
        rows.append(dict(case_index=index, case=case, details=details, fixture_details=fx['details'],
            incoming=native['incoming'], outgoing=native['outgoing'], reproduced_twice=True,
            ports=[], stack_used=False, prefix_matches_frozen_original_case=True,
            checks={k: native[k] for k in ('mirrors_coherent', 'mapped_rom_unchanged', 'pvc_unchanged', 'alias_unchanged')},
            artifacts={name: sha(data) for name, data in payloads.items()}))
    assert len(rows) == 3
    assert all(sha((root/path).read_bytes()) == digest for path, digest in inputs.items())
    library = Path(uclib._name)
    report = dict(schema_version=1, source=source, inputs=inputs, artifacts=artifacts, cases=3, completed=2, guarded=1,
        fresh_cpu_runs=6, reproduced_twice=True, rows=rows,
        oracle=dict(engine='Unicorn', version=unicorn.__version__, cpu='UC_CPU_M68K_M68000',
            library=str(library), library_sha256=sha(library.read_bytes()),
            wrapper_sha256=sha(Path(inspect.getfile(unicorn.Uc)).read_bytes())),
        adapter=dict(logical_bits=32, bus_bits=24, alias_start=ALIAS, alias_size=PAGE,
            source_physical_start=0, source_sha256=sha(program[:PAGE]), permission='read-only',
            declaration='explicit host map, not automatic backend masking; cart vectors assumed'),
        original_program_modified=False, register_injection_after_begin=False, in_hook_SR_access=False,
        CCR_observed=False, Cpp_comparison_performed=False, whole_opcode40_claim=False,
        limitations=['Isolated4a382..4a3ac only; stop before4a276. Synthetic original fixtures; natural reachability unknown.',
            'Read-only alias models declared24-bit address lines only for these bounded cases; no generic MMIO adapter or physical hardware proof.',
            'Vectors use canonical cart program bytes; BIOS/cart vector selection is not established.',
            'Raw logical hook address01000000 is preserved. Unsupported maskedfffff0 is guarded before access.',
            'Only SR system byte is compared; lazy CCR flags are not observed. Hooks describe logical accesses, not bus cycles or timing.'],
        failure=None)
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(cases=3, completed=2, guarded=1, artifacts=len(artifacts), sha256=sha(report_path.read_bytes()))))


if __name__ == '__main__':
    main()
