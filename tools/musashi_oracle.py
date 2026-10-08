"""ctypes interface to the pinned Musashi M68000 single-context oracle.

One live oracle per process; creating another replaces the same native context.
Set SR before A7 when preparing a fixture, as supervisor switching changes SP.
"""
import ctypes
import hashlib
import json
from pathlib import Path
import platform

MEMORY_SIZE = 0x200000
SENTINEL = 0xff000
REGISTERS = {name:index for index, name in enumerate(
    ['d'+str(i) for i in range(8)]+['a'+str(i) for i in range(8)]+['pc', 'sr'])}


class MusashiOracle:
    def __init__(self, library=None):
        root = Path(__file__).resolve().parents[1]
        if library is None:
            name = 'libmusashi_oracle.dylib' if platform.system() == 'Darwin' else 'libmusashi_oracle.so'
            library = root/'artifacts/dependencies/musashi_oracle_build'/name
        self.library_path = Path(library)
        self.lib = ctypes.CDLL(str(self.library_path))
        self._in_hook = False
        self._callback = None
        self._write_callback = None
        self._callback_error = None
        self._observer_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint)
        self.lib.oracle_set_observer.argtypes = [self._observer_type]
        self.lib.oracle_set_observer.restype = None
        self._write_observer_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)
        self.lib.oracle_set_write_observer.argtypes = [self._write_observer_type]
        self.lib.oracle_set_write_observer.restype = None
        byte_pointer = ctypes.POINTER(ctypes.c_ubyte)
        for name in ('oracle_init', 'oracle_reset'):
            getattr(self.lib, name).argtypes = []
            getattr(self.lib, name).restype = None
        for name in ('oracle_load', 'oracle_read'):
            getattr(self.lib, name).argtypes = [ctypes.c_uint, byte_pointer, ctypes.c_uint]
            getattr(self.lib, name).restype = ctypes.c_int
        self.lib.oracle_set_register.argtypes = [ctypes.c_uint, ctypes.c_uint]
        self.lib.oracle_set_register.restype = ctypes.c_int
        self.lib.oracle_get_register.argtypes = [ctypes.c_uint]
        self.lib.oracle_get_register.restype = ctypes.c_uint
        self.lib.oracle_run.argtypes = [ctypes.c_uint, ctypes.c_uint]
        self.lib.oracle_run.restype = ctypes.c_int
        for name in ('oracle_instruction_count', 'oracle_last_fault_address', 'oracle_cpu_write_count'):
            getattr(self.lib, name).argtypes = []
            getattr(self.lib, name).restype = ctypes.c_uint
        self.lib.oracle_init()

    def reset(self, clear_memory=False):
        """Reset vector PC/A7/SR and clear fixture D0..D7/A0..A6 deterministically."""
        self._require_not_hook()
        if clear_memory:
            self.lib.oracle_init()
            if self._callback is not None:
                self.lib.oracle_set_observer(self._callback)
            if self._write_callback is not None:
                self.lib.oracle_set_write_observer(self._write_callback)
        else:
            self.lib.oracle_reset()

    def _span(self, address, size):
        if not isinstance(address, int) or not isinstance(size, int) or address < 0 or size < 0 or address+size > MEMORY_SIZE:
            raise ValueError('Memory span outside two-MiB harness')

    def load(self, address, data):
        self._require_not_hook()
        data = bytes(data)
        self._span(address, len(data))
        buffer = (ctypes.c_ubyte*len(data)).from_buffer_copy(data)
        if not self.lib.oracle_load(address, buffer, len(data)):
            raise ValueError('Native memory load failed')

    def read(self, address, size):
        self._span(address, size)
        buffer = (ctypes.c_ubyte*size)()
        if not self.lib.oracle_read(address, buffer, size):
            raise ValueError('Native memory read failed')
        return bytes(buffer)

    def set_reg(self, name, value):
        self._require_not_hook()
        index = REGISTERS[name.lower()]
        if not isinstance(value, int) or not 0 <= value <= 0xffffffff:
            raise ValueError('Register value must be unsigned32')
        if not self.lib.oracle_set_register(index, value):
            raise ValueError('Native register set failed')

    def get_reg(self, name):
        return int(self.lib.oracle_get_register(REGISTERS[name.lower()]))

    def registers(self):
        return {name:self.get_reg(name) for name in REGISTERS}

    def _require_not_hook(self):
        if self._in_hook:
            raise RuntimeError('Instruction observer permits register/memory reads only')

    def set_instruction_hook(self, callback):
        """Observe before each instruction: callback(pc); register/memory reads allowed."""
        self._require_not_hook()
        if callback is None:
            self._callback = None
            self.lib.oracle_set_observer(self._observer_type())
            return

        def observe(pc):
            self._in_hook = True
            try:
                callback(int(pc))
                return 0
            except BaseException as error:
                self._callback_error = error
                return 1
            finally:
                self._in_hook = False

        self._callback = self._observer_type(observe)
        self.lib.oracle_set_observer(self._callback)

    def set_write_hook(self, callback):
        """Observe CPU writes: callback(instruction_pc,address,size_bytes,value)."""
        self._require_not_hook()
        if callback is None:
            self._write_callback = None
            self.lib.oracle_set_write_observer(self._write_observer_type())
            return

        def observe(pc, address, size, value):
            self._in_hook = True
            try:
                callback(int(pc), int(address), int(size), int(value))
                return 0
            except BaseException as error:
                self._callback_error = error
                return 1
            finally:
                self._in_hook = False

        self._write_callback = self._write_observer_type(observe)
        self.lib.oracle_set_write_observer(self._write_callback)

    def run(self, instruction_budget=100000, sentinel=SENTINEL):
        self._require_not_hook()
        if not isinstance(instruction_budget, int) or not 0 < instruction_budget <= 100000000:
            raise ValueError('Instruction budget outside1..100000000')
        self._span(sentinel, 1)
        self._callback_error = None
        status = int(self.lib.oracle_run(instruction_budget, sentinel))
        if self._callback_error is not None:
            raise RuntimeError('Instruction observer failed; execution result is not accepted') from self._callback_error
        result = dict(status=['sentinel', 'budget_exhausted', 'memory_fault', 'stopped_cpu', 'observer_error'][status],
            instructions=int(self.lib.oracle_instruction_count()), pc=self.get_reg('pc'),
            cpu_writes=int(self.lib.oracle_cpu_write_count()),
            fault_address=int(self.lib.oracle_last_fault_address()))
        return result


def verify_synthetic_flags():
    cpu = MusashiOracle()
    rows = []
    # AND.W D0,D1 and MOVE.L D0,D1, each followed by RTS to a separate sentinel.
    for mnemonic, raw in [('AND.W D0,D1', 'c240'), ('MOVE.L D0,D1', '2200')]:
        for value, expected_ccr in [(0, 0x14), (1, 0x10), (0x80008000, 0x18)]:
            cpu.reset(clear_memory=True)
            cpu.load(0x100, bytes.fromhex(raw+'4e75'))
            cpu.load(0x1ff000, SENTINEL.to_bytes(4, 'big'))
            cpu.set_reg('sr', 0x201f)
            cpu.set_reg('a7', 0x1ff000)
            cpu.set_reg('pc', 0x100)
            cpu.set_reg('d0', value)
            cpu.set_reg('d1', 0xffffffff)
            result = cpu.run(10)
            expected_d1 = (0xffff0000 | (value & 0xffff)) if mnemonic.startswith('AND') else value
            if result['status'] != 'sentinel' or result['instructions'] != 2 or cpu.get_reg('d1') != expected_d1 or cpu.get_reg('sr') & 0x1f != expected_ccr:
                raise AssertionError((mnemonic, value, result, cpu.registers()))
            rows.append(dict(instruction=mnemonic, opcode_hex=raw, input_d0=value,
                output_d1=cpu.get_reg('d1'), output_sr=cpu.get_reg('sr'), result=result))
    cpu.reset(clear_memory=True)
    cpu.load(0x100, bytes.fromhex('003c00014e75'))
    cpu.load(0x1ff000, SENTINEL.to_bytes(4, 'big'))
    cpu.set_reg('sr', 0x2010)
    cpu.set_reg('a7', 0x1ff000)
    cpu.set_reg('pc', 0x100)
    result = cpu.run(10)
    if result['status'] != 'sentinel' or cpu.get_reg('sr') != 0x2011 or result['instructions'] != 2:
        raise AssertionError(('ORI #1,CCR', result, cpu.registers()))
    rows.append(dict(instruction='ORI #1,CCR', opcode_hex='003c0001', output_sr=cpu.get_reg('sr'), result=result))
    return rows


def verify_observers_and_controls():
    cpu = MusashiOracle()
    results = []
    snapshots = []
    writes = []
    for observed in (False, True):
        cpu.reset(clear_memory=True)
        cpu.load(0x100, bytes.fromhex('2080c24022004e75'))
        cpu.load(0x1ff000, SENTINEL.to_bytes(4, 'big'))
        cpu.set_reg('sr', 0x201f)
        cpu.set_reg('a7', 0x1ff000)
        cpu.set_reg('pc', 0x100)
        cpu.set_reg('d0', 0x80008000)
        cpu.set_reg('d1', 0xffffffff)
        cpu.set_reg('a0', 0x100100)
        if observed:
            def observe(pc):
                snapshots.append(dict(pc=pc, registers=cpu.registers(), code_hex=cpu.read(pc, 2).hex()))
            def write(pc, address, size, value):
                writes.append(dict(pc=pc, address=address, size=size, value=value,
                                   previous_hex=cpu.read(address, size).hex()))
            cpu.set_instruction_hook(observe)
            cpu.set_write_hook(write)
        result = cpu.run(10)
        results.append(dict(result=result, registers=cpu.registers(),
            memory_sha256=hashlib.sha256(cpu.read(0, MEMORY_SIZE)).hexdigest()))
    if results[0] != results[1] or results[1]['result']['status'] != 'sentinel' or len(snapshots) != 4 or len(writes) != 1:
        raise AssertionError(('Observer affected state', results, snapshots, writes))
    cpu.set_instruction_hook(None)
    cpu.set_write_hook(None)
    cpu.reset(clear_memory=True)
    cpu.load(0x100, bytes.fromhex('60fe'))
    cpu.set_reg('pc', 0x100)
    budget = cpu.run(5)
    if budget['status'] != 'budget_exhausted' or budget['instructions'] != 5:
        raise AssertionError(('Instruction budget failed', budget))
    cpu.reset(clear_memory=True)
    cpu.load(0x100, bytes.fromhex('23c0002000004e75'))
    cpu.set_reg('pc', 0x100)
    fault = cpu.run(5)
    if fault['status'] != 'memory_fault' or fault['fault_address'] != MEMORY_SIZE or fault['cpu_writes'] != 1:
        raise AssertionError(('Unmapped write was not observed/faulted', fault))
    cpu.reset(clear_memory=True)
    cpu.load(0x100, bytes.fromhex('4e71'))
    cpu.set_reg('pc', 0x100)
    def forbidden(pc):
        cpu.set_reg('d0', 1)
    cpu.set_instruction_hook(forbidden)
    try:
        cpu.run(5)
    except RuntimeError as error:
        propagated = isinstance(error.__cause__, RuntimeError)
    else:
        propagated = False
    if not propagated:
        raise AssertionError('Read-only callback mutation/error was not rejected')
    cpu.set_instruction_hook(None)
    cpu.reset(clear_memory=True)
    cpu.load(0x100, bytes.fromhex('20804e75'))
    cpu.set_reg('pc', 0x100)
    cpu.set_reg('a0', 0x100100)
    cpu.set_reg('d0', 0x12345678)
    def reject_write(pc, address, size, value):
        raise ValueError('Synthetic observer refusal')
    cpu.set_write_hook(reject_write)
    try:
        cpu.run(5)
    except RuntimeError as error:
        write_propagated = isinstance(error.__cause__, ValueError)
    else:
        write_propagated = False
    if not write_propagated or cpu.read(0x100100, 4) != bytes(4):
        raise AssertionError('Write callback error was not propagated/rejected')
    cpu.set_write_hook(None)
    cpu.set_reg('d7', 0xffffffff)
    cpu.reset()
    if cpu.get_reg('d7') != 0:
        raise AssertionError('Fixture reset retained a general register')
    return dict(hook_nohook_state_equal=True, results=results, instruction_observations=snapshots,
        write_observations=writes, instruction_budget=budget, unmapped_write=fault,
        observer_exception_propagated=True, write_observer_exception_propagated=True,
        fixture_register_reset=True)


if __name__ == '__main__':
    rows = verify_synthetic_flags()
    controls = verify_observers_and_controls()
    path = Path(__file__).resolve().parents[1]/'artifacts/dependencies/musashi_oracle_build/synthetic_flags.json'
    path.write_text(json.dumps(dict(cases=len(rows), rows=rows, controls=controls,
        scope='Synthetic opcode flags, read-only observers and harness controls only, no game logic inference'), indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), and_word_clears_c=True, move_long_clears_c=True,
                         ori_ccr_sets_c=True, hook_nohook_state_equal=True, observer_exception_propagated=True)))
