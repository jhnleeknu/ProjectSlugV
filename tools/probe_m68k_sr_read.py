"""Synthetic M68000 backend SR-read experiments; no original ROM or game oracle.

The CPU itself executes MOVE SR,D2. Host SR reads occur only at declared stop
boundaries, never in hooks. Each experiment owns a fresh CPU. No registers are
explicitly injected after execution starts; context restore uses only its immediately
saved state, and split calls resume from the next instruction.
"""
import hashlib
import inspect
import json
from pathlib import Path
import sys

import capstone
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib

ROOT = Path(__file__).resolve().parents[1]
CODE = 0x1000
READOUT = bytes.fromhex('40c2')  # MOVE SR,D2 (does not modify CCR)
GROUPS = (
    ('asr-odd-carry-set', '7effe247'),
    ('asr-even-carry-clear', '7e02e247'),
    ('ori-ccr-carry-set', '003c0001'),
    ('andi-ccr-carry-clear', '003c0001023c00fe'),
    ('cmp-word-zero-less-than-one', '70007201b041'),
    ('moveq-zero', '7000'),
    ('addq-long-overflow', '70ff5280'),
)
STRATEGIES = ('same-start', 'split-no-host-SR', 'split-with-host-SR', 'split-context-restore')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def registers(cpu):
    return {name: cpu.reg_read(getattr(m, 'UC_M68K_REG_' + name.upper()))
        for name in ('d0', 'd1', 'd2', 'd7', 'a7', 'pc')}


def experiment(group, hex_code, strategy):
    raw = bytes.fromhex(hex_code) + READOUT
    split = CODE + len(raw) - len(READOUT)
    cpu = unicorn.Uc(unicorn.UC_ARCH_M68K, unicorn.UC_MODE_BIG_ENDIAN)
    cpu.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
    assert cpu.ctl_get_cpu_model() == m.UC_CPU_M68K_M68000
    cpu.mem_map(0x1000, 4096)
    cpu.mem_write(CODE, raw)
    cpu.reg_write(m.UC_M68K_REG_SR, 0x2000)
    cpu.reg_write(m.UC_M68K_REG_A7, 0x8000)
    trace = []
    def code_hook(c, address, size, user):
        # No SR or other register access inside hooks.
        trace.append(dict(pc=address, backend_size=size))
    cpu.hook_add(unicorn.UC_HOOK_CODE, code_hook)
    before = registers(cpu)
    mid_sr = None
    calls = []
    if strategy == 'same-start':
        calls.append(dict(begin=CODE, until=CODE + len(raw)))
        cpu.emu_start(CODE, CODE + len(raw))
    else:
        calls.append(dict(begin=CODE, until=split))
        cpu.emu_start(CODE, split)
        if strategy == 'split-with-host-SR':
            mid_sr = cpu.reg_read(m.UC_M68K_REG_SR)
        if strategy == 'split-context-restore':
            cpu.context_restore(cpu.context_save())
        calls.append(dict(begin=split, until=CODE + len(raw)))
        cpu.emu_start(split, CODE + len(raw))
    # Read CPU capture first; a subsequent host SR read cannot change captured D2.
    cpu_sr = cpu.reg_read(m.UC_M68K_REG_D2) & 65535
    after = registers(cpu)
    host_sr = cpu.reg_read(m.UC_M68K_REG_SR)
    observed = bytes(cpu.mem_read(CODE, len(raw)))
    assert observed == raw and after['pc'] == CODE + len(raw)
    decoder = capstone.Cs(capstone.CS_ARCH_M68K,
        capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    decoded = [dict(pc=i.address, size=i.size, raw=bytes(i.bytes).hex(),
        mnemonic=i.mnemonic, operands=i.op_str) for i in decoder.disasm(raw, CODE)]
    assert sum(i['size'] for i in decoded) == len(raw)
    assert [i['pc'] for i in decoded] == [i['pc'] for i in trace]
    return dict(group=group, strategy=strategy, initial_sr=0x2000,
        code_address=CODE, requested_code=raw.hex(), observed_code=observed.hex(),
        instructions=decoded, instruction_trace=trace, emu_start_calls=calls,
        before=before, after=after, intermediate_host_sr=mid_sr,
        cpu_move_sr_d2=cpu_sr, final_host_sr=host_sr,
        cpu_carry=bool(cpu_sr & 1), host_carry=bool(host_sr & 1),
        final_host_equals_cpu=(host_sr == cpu_sr))


def main():
    folder = ROOT / 'artifacts/m68k_sr_read_probe'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'observation.json'
    path.unlink(missing_ok=True)
    tool = Path(__file__).resolve()
    tool_sha = sha(tool.read_bytes())
    rows = [experiment(group, code, strategy) for group, code in GROUPS for strategy in STRATEGIES]
    # Independently reset CPUs and require full observed traces/registers to reproduce.
    again = [experiment(group, code, strategy) for group, code in GROUPS for strategy in STRATEGIES]
    assert again == rows
    comparisons = []
    for group, _ in GROUPS:
        by_strategy = {r['strategy']: r for r in rows if r['group'] == group}
        comparisons.append(dict(group=group,
            cpu_sr_by_strategy={s: by_strategy[s]['cpu_move_sr_d2'] for s in STRATEGIES},
            host_sr_by_strategy={s: by_strategy[s]['final_host_sr'] for s in STRATEGIES},
            mid_host_read_changes_later_cpu_sr=(by_strategy['split-with-host-SR']['cpu_move_sr_d2'] !=
                by_strategy['split-no-host-SR']['cpu_move_sr_d2']),
            split_without_host_preserves_cpu_sr=(by_strategy['split-no-host-SR']['cpu_move_sr_d2'] ==
                by_strategy['same-start']['cpu_move_sr_d2'])))
    # Assert the stated pinned-backend observations after execution; never inject them.
    expected_carry = {'asr-odd-carry-set': True, 'asr-even-carry-clear': False,
        'ori-ccr-carry-set': True, 'andi-ccr-carry-clear': False}
    for group, _ in GROUPS:
        by_strategy = {r['strategy']: r for r in rows if r['group'] == group}
        if group in expected_carry:
            assert all(r['final_host_equals_cpu'] and r['cpu_carry'] == expected_carry[group]
                for r in by_strategy.values()), (group, by_strategy)
        else:
            same = by_strategy['same-start']
            assert not same['final_host_equals_cpu'], (group, 'lazy host/CPU difference disappeared')
            for strategy in ('split-no-host-SR', 'split-context-restore'):
                assert by_strategy[strategy]['cpu_move_sr_d2'] == same['cpu_move_sr_d2'], (group, strategy)
            interrupted = by_strategy['split-with-host-SR']
            assert interrupted['cpu_move_sr_d2'] != same['cpu_move_sr_d2'], (group, 'host-read effect disappeared')
            assert interrupted['cpu_move_sr_d2'] == interrupted['intermediate_host_sr'], group
    api = inspect.getfile(unicorn.Uc)
    assert sha(tool.read_bytes()) == tool_sha
    report = dict(synthetic_only=True, original_ROM_used=False,
        expected_register_or_flag_injection_after_start=False, in_hook_SR_access=False,
        model='UC_CPU_M68K_M68000', model_id=m.UC_CPU_M68K_M68000,
        unicorn_version=unicorn.__version__, python=sys.version,
        api_source_path=api, api_file_sha256=sha(Path(api).read_bytes()),
        native_library_path=uclib._name, native_library_sha256=sha(Path(uclib._name).read_bytes()),
        capstone_version=capstone.__version__, tool_sha256=tool_sha,
        cases=len(rows), reproduced_twice=True, groups=[g for g, _ in GROUPS],
        strategies=list(STRATEGIES), results=rows, comparisons=comparisons,
        conclusion='For these pinned backend sequences, ASR and explicit ORI/ANDI produce matching host/CPU SR. '
            'CMP/MOVEQ/ADDQ CPU-visible lazy flags differ from final host SR. A host SR read between split calls '
            'changes the subsequent CPU MOVE SR capture for those lazy cases; splitting or saving/restoring context '
            'without the host read preserves the tested CPU flags.',
        limitations='Synthetic primitives only. No original game execution, physical68000 CCR measurement, '
            'timing, arbitrary instruction/flag or pending continuation proof. Backend code-hook size is not '
            'instruction length; exact bytes and lengths are independently decoded by Capstone. Initial SR is '
            'prepared before execution; no explicit reg_write or expected-result injection occurs after start; '
            'context-restore strategy restores only its immediately saved state.')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(cases=len(rows), groups=len(GROUPS), strategies=len(STRATEGIES),
        reproduced_twice=True, source_sha256=tool_sha, report_sha256=sha(path.read_bytes()))))


if __name__ == '__main__':
    main()
