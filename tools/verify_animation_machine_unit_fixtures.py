"""Reusable native fixture verifier for animation-machine units.

A Fixture declares an entry state (RAM 64 KiB, PVC page, bank, 16 registers, PC, carry tag), the ordered external-read queue, a stop PC, the declared
wait releases and the expectation.  The verifier runs
  (a) the C++ ms5::run_animation_machine (engine/tools/unit_fixture_acceptance.cpp, a copy-and-extend of the F5 packet harness) and
  (b) native Unicorn on the original ROM (observe_animation_machine_pvc_banks.PvcMachine, never modified) with the SAME declared releases,
and compares RAM, D0-D7/A0-A7, PC, bank base, PVC page (ff8/ff9 normalised as in the F5 verifier), ordered ports, ordered waits, consumed external reads,
the unconsumed queue and the external-read count.  Carry has no SR oracle: only a valid tag is checked.  Video is ordered ports, not pixels.

Expectations:  'match'            C++ and native agree on everything above (native must reach the stop PC).
               ('error', text)    C++ must fail with an error containing text AND preserve RAM/state/device/queue of the failing call; native is not run.
               'mismatch'         negative check: the comparison must report a difference (use cpp_state / cpp_queue to feed C++ a corrupted input).
Declared releases (names): ef2, 16bd0, 3aea, cda4 (the D1 head waits), gate (47af0/478de carry gate), card (BIOS card c00468 resume; a failing run is
re-run to c00468 exactly like the frame driver, answer byte written to 10fdc6, resume at c37c with A7+4).  Unlisted wait PCs are errors on both sides.
Wait limit (default 16) counts every release including the card resume; one more Waiting block is an error on both sides.
Palette RAM (F6 scope decision E6, optional):  a state may carry 'palette' = (bank0 8192 bytes, bank1 8192 bytes, selected 0/1).  Then C++ runs
run_animation_machine_with_palette (harness flag bit 6), the native machine class must provide palette_load(palette) / palette_dump() (a spec
subclass maps the device), and both banks and the selection are compared.  States without the key are verified exactly as before.

Library:  Fixture, run_fixtures(fixtures, workers), fixture_from_state(...), with_host_writes(...), advance_native(...), seed_frames(...), seed_h_fixtures(...),
          seed_node_fixture(...).   CLI:  --spec module.py (FIXTURES list or build() -> list) --out dir --workers N
"""
import argparse
import collections
import ctypes
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
HARNESS = ROOT / 'engine/tools/unit_fixture_acceptance.cpp'
BUILD = ROOT / 'build/unit_fixture_acceptance'
KEYS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')
PVC_LO, PVC_HI = 0x2fe000, 0x300000
STATUS_ADDR = 0xd00046
CARD_BIOS, CARD_RET, CARD_BYTE = 0xc00468, 0xc37c, 0x10fdc6
RELEASE_BITS = {'ef2': 1, '16bd0': 2, '3aea': 4, 'cda4': 8, 'gate': 16, 'card': 32}
DEFAULT_RELEASES = ('ef2', '16bd0', '3aea', 'cda4', 'gate', 'card')
WAIT_PCS = {0xef2: 'ef2', 0x16bd0: '16bd0', 0x3aea: '3aea', 0xcda4: 'cda4', 0x47af0: 'gate', 0x478de: 'gate'}
DEFAULT_WAIT_LIMIT = 16
DEFAULT_MAX_INSN = 6000000
REQUEST_WORDS = 24
# Tool files whose bytes are pinned in the report (the historic verifiers are reused, never edited).
PINNED_TOOLS = ('verify_animation_machine_unit_fixtures.py', 'verify_animation_machine_frame_head.py', 'verify_animation_machine_frame_driver.py',
                'observe_animation_machine_pvc_banks.py', 'observe_animation_machine_scheduler.py', 'observe_animation_machine_scheduler_rng.py',
                'observe_animation_machine_frame_head.py', 'address_map.py', 'verify_animation_machine.py')


def require(ok, detail):
    if not ok:
        raise RuntimeError(str(detail))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


# ----------------------------------------------------------------------------------
# Fixture and state helpers (ROM-free)
# ----------------------------------------------------------------------------------
def bank_page(bank, pvc=None):
    """8 KiB PVC page for a (base, ff8, ff9) bank triple; ff8/ff9 live at 1ff0/1ff2.  A given page must agree with the triple there."""
    if pvc is None:
        p = bytearray(8192)
        p[0x1ff0:0x1ff4] = struct.pack('>HH', bank[1] & 0xffff, bank[2] & 0xffff)
        return bytes(p)
    require(len(pvc) == 8192, 'PVC page must be 8192 bytes')
    require(bytes(pvc[0x1ff0:0x1ff4]) == struct.pack('>HH', bank[1] & 0xffff, bank[2] & 0xffff), 'PVC page ff8/ff9 disagree with the bank triple')
    return bytes(pvc)


def make_state(ram, regs, pc, bank, pvc=None, carry=0):
    """Entry/exit state dict.  regs: dict d0..a7; bank: (base, ff8, ff9) with base >= 0x100000; carry: 0 unknown, 1 clear, 2 set."""
    require(len(ram) == 65536, 'RAM must be 65536 bytes')
    require(all(k in regs for k in KEYS), 'registers d0..d7, a0..a7 required')
    require(bank[0] >= 0x100000, 'bank base below 100000 is not a producible PVC state')
    require(carry in (0, 1, 2), 'carry tag')
    return dict(ram=bytes(ram), regs={k: regs[k] & 0xffffffff for k in KEYS}, pc=pc, bank=tuple(bank), pvc=bank_page(bank, pvc), carry=carry)


def with_host_writes(state, writes=(), regs=None, pc=None):
    """Copy of state with declared host writes [(address, size, value)] (work RAM address & 0xffff, big-endian) and register / PC overrides."""
    ram = bytearray(state['ram'])
    for addr, size, value in writes:
        require(size in (1, 2, 4), ('write size', size))
        require(0 <= value < (1 << (8 * size)), ('write value', value))
        for i in range(size):
            ram[(addr + i) & 0xffff] = (value >> (8 * (size - 1 - i))) & 0xff
    out = dict(state, ram=bytes(ram), regs=dict(state['regs']))
    for k, v in (regs or {}).items():
        require(k in KEYS, ('register', k))
        out['regs'][k] = v & 0xffffffff
    if pc is not None:
        out['pc'] = pc
    return out


def flip_ram(state, address, mask=1):
    """Corrupted copy for negative checks: XOR mask into one work RAM byte."""
    ram = bytearray(state['ram'])
    ram[address & 0xffff] ^= mask
    return dict(state, ram=bytes(ram))


class Fixture(object):
    """name; state (see make_state); queue [(address, size, value)]; stop PC; expect ('match' | ('error', text) | 'mismatch'); releases (names); wait_limit;
    external_status (byte read at d00046); card_answer; max_insn (native instruction budget per start); cpp_state / cpp_queue (override the C++ input only,
    for negative checks; also cpp_stop); fail_pc (expected-error fixtures: the PC at which the dispatcher fails; default = the start PC of the C++ input; see check_fail_pc); reference (optional independent end state {ram, regs, pc, pvc} that the NATIVE result must equal); meta (free JSON)."""
    def __init__(self, name, state, queue=(), stop=None, expect='match', releases=DEFAULT_RELEASES, wait_limit=DEFAULT_WAIT_LIMIT, external_status=0,
                 card_answer=0x80, max_insn=DEFAULT_MAX_INSN, cpp_state=None, cpp_queue=None, cpp_stop=None, reference=None, meta=None, fail_pc=None):
        require(stop is not None, 'stop PC required')
        require(expect in ('match', 'mismatch') or (isinstance(expect, tuple) and len(expect) == 2 and expect[0] == 'error'), ('expect', expect))
        require(all(r in RELEASE_BITS for r in releases), ('unknown release', releases))
        self.name, self.state, self.queue, self.stop, self.expect = name, state, [tuple(e) for e in queue], stop, expect
        self.releases, self.wait_limit, self.external_status, self.card_answer, self.max_insn = tuple(releases), wait_limit, external_status, card_answer, max_insn
        self.cpp_stop, self.fail_pc = cpp_stop, fail_pc
        self.cpp_state, self.cpp_queue, self.reference, self.meta = cpp_state, (None if cpp_queue is None else [tuple(e) for e in cpp_queue]), reference, meta or {}

    def digest(self):
        h = hashlib.sha256(b'MS5-UNIT-FIXTURE-1')
        for s in (self.state, self.cpp_state):
            if s is not None:
                h.update(s['ram'] + struct.pack('>16I', *[s['regs'][k] for k in KEYS]) + struct.pack('>IIIII', s['pc'], s['bank'][0], s['bank'][1], s['bank'][2], s['carry']) + s['pvc'])
                if s.get('palette') is not None:
                    h.update(b'palette' + s['palette'][0] + s['palette'][1] + bytes([s['palette'][2]]))
        h.update(json.dumps([self.queue, self.cpp_queue, self.stop, self.cpp_stop, self.expect, self.releases, self.wait_limit, self.external_status, self.card_answer] + ([] if self.fail_pc is None else [self.fail_pc]), sort_keys=True).encode())
        return h.hexdigest()


def release_mask(names, card_answer):
    return sum(RELEASE_BITS[n] for n in names) | ((card_answer & 0xff) << 8)


# ----------------------------------------------------------------------------------
# Packets
# ----------------------------------------------------------------------------------
PALETTE_FLAG = 64


def check_palette(palette):
    require(len(palette) == 3 and len(palette[0]) == 8192 and len(palette[1]) == 8192 and palette[2] in (0, 1), 'palette = (8192 bytes, 8192 bytes, 0/1)')
    return (bytes(palette[0]), bytes(palette[1]), palette[2])


def encode_request(state, queue, stop, releases, wait_limit, external_status, card_answer):
    pal = state.get('palette')
    flags = release_mask(releases, card_answer) | (PALETTE_FLAG if pal is not None else 0)
    v = [state['pc'], state.get('carry', 0), state['bank'][0], stop, flags, wait_limit, external_status, len(queue)]
    v += [state['regs'][k] for k in KEYS]
    out = struct.pack('>24I', *v) + state['ram'] + state['pvc'] + b''.join(struct.pack('>III', *e) for e in queue)
    if pal is not None:
        b0, b1, sel = check_palette(pal)
        out += b0 + b1 + struct.pack('>I', sel)
    return out


def parse_response(payload, palette=False):
    """-> dict(ok=True, ...) | dict(ok=False, preserved, committed, error).  Malformed -> ValueError (a harness fault, never a result).
    palette: the request attached palette RAM (the success packet then ends with bank 0, bank 1, selected)."""
    if len(payload) < 12:
        raise ValueError('short harness packet')
    tag = struct.unpack_from('>I', payload)[0]
    if tag == 2:
        raise ValueError('harness rejected the request: ' + payload[12:].decode('latin-1'))
    if tag == 0:
        preserved, committed = struct.unpack_from('>II', payload, 4)
        return dict(ok=False, preserved=preserved == 1, committed=committed, error=payload[12:].decode('latin-1'))
    if tag != 1 or len(payload) < 36 + 64 + 65536 + 8192:
        raise ValueError('invalid harness packet')
    status, pc, carry, bank, reads, np, nq, nw = struct.unpack_from('>8I', payload, 4)
    if status != 0 or carry not in (0, 1, 2):
        raise ValueError('invalid harness status/carry')
    if len(payload) != 36 + 64 + 65536 + 8192 + 12 * (np + nq) + 20 * nw + (16388 if palette else 0):
        raise ValueError('invalid harness packet length')
    regs = dict(zip(KEYS, struct.unpack_from('>16I', payload, 36)))
    at = 100
    ram = payload[at:at + 65536]
    at += 65536
    pvc = payload[at:at + 8192]
    at += 8192
    ports = [struct.unpack_from('>III', payload, at + 12 * i) for i in range(np)]
    at += 12 * np
    remaining = [struct.unpack_from('>III', payload, at + 12 * i) for i in range(nq)]
    at += 12 * nq
    waits = [struct.unpack_from('>5I', payload, at + 20 * i) for i in range(nw)]
    out = dict(ok=True, ram=ram, pvc=pvc, regs=regs, pc=pc, carry=carry, bank_base=bank, reads=reads, ports=ports, remaining=remaining, waits=waits)
    if palette:
        at += 20 * nw
        sel = struct.unpack_from('>I', payload, at + 16384)[0]
        if sel > 1:
            raise ValueError('invalid harness palette selection')
        out['palette'] = (payload[at:at + 8192], payload[at + 8192:at + 16384], sel)
    return out


class Harness(object):
    def __init__(self, exe, resources, stderr_path):
        self.err = open(stderr_path, 'ab')
        self.proc = subprocess.Popen([str(exe)] + [str(p) for p in resources], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err)

    def exact(self, n):
        data = self.proc.stdout.read(n)
        require(len(data) == n, ('truncated harness response', len(data), n))
        return data

    def call(self, payload, palette=False):
        self.proc.stdin.write(struct.pack('>I', len(payload)) + payload)
        self.proc.stdin.flush()
        size = struct.unpack('>I', self.exact(4))[0]
        require(12 <= size <= 4194304, 'invalid harness packet size')
        return parse_response(self.exact(size), palette)

    def close(self):
        try:
            self.proc.stdin.close()
            return self.proc.wait(timeout=60)
        finally:
            self.err.close()


# ----------------------------------------------------------------------------------
# Native side (Unicorn, original ROM)
# ----------------------------------------------------------------------------------
class Native(object):
    """Lazy per-process native oracle: ROM, fixed-area buffer, observers."""
    def __init__(self):
        import unicorn
        import observe_animation_machine_scheduler as S
        import observe_animation_machine_pvc_banks as PB
        self.unicorn, self.S, self.PB = unicorn, S, PB
        self.program = S.load_rom()
        self.fixed = (ctypes.c_ubyte * 0x100000).from_buffer_copy(self.program[:0x100000])

    def run(self, fx_state, queue, stop, releases=DEFAULT_RELEASES, wait_limit=DEFAULT_WAIT_LIMIT, external_status=0, card_answer=0x80, max_insn=DEFAULT_MAX_INSN):
        """Native run to stop.  -> dict(ok, ...).  ok False carries error; ok True: ram, regs, pc, bank=(base,ff8,ff9), pvc, ports (address,size,value), consumed, remaining,
        status_reads, waits (pc,address,size,before,released)."""
        unicorn, S, PB = self.unicorn, self.S, self.PB
        snap = dict(ram=fx_state['ram'], regs=fx_state['regs'], pc=fx_state['pc'], bank=fx_state['bank'])
        m = PB.PvcMachine(self.program, self.fixed, snap)
        if fx_state.get('palette') is not None:
            require(hasattr(m, 'palette_load') and hasattr(m, 'palette_dump'), 'palette state needs a native machine with palette_load / palette_dump')
            m.palette_load(check_palette(fx_state['palette']))
        m.install_basic_hooks()
        c = m.cpu
        for base in (0x340000, 0x380000):
            c.mem_map(base, 4096, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
        c.mem_write(PVC_LO, fx_state['pvc'])
        c.mem_write(STATUS_ADDR, bytes([external_status & 0xff]))
        rest = list(queue)
        consumed, waits, bad = [], [], []
        status_reads = [0]
        result = {'stop': False}
        enabled = set(releases)

        def read(uc, access, address, size, value, user):
            if 0xd00000 <= address < 0xd01000:
                if address == STATUS_ADDR and size == 1:
                    status_reads[0] += 1
                else:
                    bad.append(('undeclared device read', address, size))
                    uc.emu_stop()
                return
            if not (0x300000 <= address < 0x400000):
                return
            if not rest or rest[0][:2] != (address, size):
                bad.append(('external order', address, size, rest[:1]))
                uc.emu_stop()
                return
            _, n, v = rest.pop(0)
            uc.mem_write(address, v.to_bytes(n, 'big'))
            consumed.append((address, size, v))

        def release(pc):
            """Declared release when the block at pc would spin; None when the wait does not apply."""
            r = m.regs()
            a5 = r['a5']
            if pc == 0xef2 and m.byte(a5 - 0x7fea) < m.byte(a5 - 0x7fe9):
                return a5 - 0x7fea, 1, m.byte(a5 - 0x7fe9)
            if pc == 0x16bd0 and m.word(a5 + 0xd34) != (r['d0'] & 65535):
                return a5 + 0xd34, 2, r['d0'] & 65535
            if pc == 0x3aea and m.word(a5 - 0x328c) == (r['d1'] & 65535):
                return 0x104d74, 2, 65535
            if pc == 0xcda4 and m.word(a5 + 0xd34) != (r['d4'] & 65535):
                return a5 + 0xd34, 2, r['d4'] & 65535
            if pc in (0x47af0, 0x478de) and m.byte(0x107ded) >= 0x80:
                if m.word(0x107dea) != 0:
                    bad.append(('gate wait not released', pc))
                    return None
                return 0x107ded, 1, m.byte(0x107ded) & 0x7f
            return None

        def code(uc, pc, size, user):
            if pc == stop:
                result['stop'] = True
                uc.emu_stop()
                return
            kind = WAIT_PCS.get(pc)
            if kind is None:
                return
            rel = release(pc)
            if rel is None:
                return
            if kind not in enabled:
                bad.append(('undeclared wait PC', pc))
                uc.emu_stop()
                return
            if len(waits) >= wait_limit:
                bad.append(('declared wait limit', pc))
                uc.emu_stop()
                return
            address, wsize, value = rel
            before = int.from_bytes(bytes(uc.mem_read(address, wsize)), 'big')
            waits.append((pc, address, wsize, before, value))
            m.put(address, wsize, value)

        c.hook_add(unicorn.UC_HOOK_MEM_READ, read, begin=0x300000, end=0x3fffff)
        c.hook_add(unicorn.UC_HOOK_MEM_READ, read, begin=0xd00000, end=0xd00fff)
        c.hook_add(unicorn.UC_HOOK_CODE, code, begin=0, end=0xffffff)
        cur = fx_state['pc']
        while True:
            m.fetch_unmapped = None
            try:
                c.emu_start(cur, 0xffffff, count=max_insn)
                uc_error = None
            except unicorn.UcError as e:
                uc_error = str(e)
            if bad or m.odd is not None or m.invalid is not None or m.intr is not None:
                return dict(ok=False, error='native error', detail=[bad, m.odd, m.invalid, m.intr])
            if result['stop']:
                break
            if m.fetch_unmapped is not None:
                if m.fetch_unmapped == stop and c.reg_read(S.UC_REG['pc']) == stop:
                    result['stop'] = True
                    break
                a7 = c.reg_read(S.UC_REG['a7'])
                if m.fetch_unmapped == CARD_BIOS and 'card' in enabled and m.long(a7) == CARD_RET and len(waits) < wait_limit:
                    before = m.byte(CARD_BYTE)
                    waits.append((CARD_BIOS, CARD_BYTE, 1, before, card_answer & 0xff))
                    m.put(CARD_BYTE, 1, card_answer & 0xff)
                    c.reg_write(S.UC_REG['a7'], (a7 + 4) & 0xffffffff)
                    cur = CARD_RET
                    continue
                return dict(ok=False, error='native fetch unmapped', detail=[hex(m.fetch_unmapped), uc_error])
            return dict(ok=False, error='native did not reach the stop PC', detail=[hex(c.reg_read(S.UC_REG['pc'])), uc_error])
        pvc = bytearray(c.mem_read(PVC_LO, 8192))
        pvc[0x1ff0:0x1ff4] = struct.pack('>HH', m.ff8, m.ff9)
        regs = m.regs()
        out = dict(ok=True, ram=m.ram(), regs=regs, pc=stop, bank=(m.bank, m.ff8, m.ff9), pvc=bytes(pvc), ports=[(a, n, v) for _, a, n, v in m.ports],
                   consumed=consumed, remaining=rest, status_reads=status_reads[0], waits=waits)
        if fx_state.get('palette') is not None:
            out['palette'] = check_palette(m.palette_dump())
        return out


NATIVE = [None]


def native():
    if NATIVE[0] is None:
        NATIVE[0] = Native()
    return NATIVE[0]


def native_state(result, carry=0):
    """A native result as a fixture state (for chaining fixtures; a native palette result is carried over)."""
    st = make_state(result['ram'], result['regs'], result['pc'], result['bank'], result['pvc'], carry)
    if result.get('palette') is not None:
        st['palette'] = result['palette']
    return st


def advance_native(state, queue, stop, **kw):
    """Run native from state to stop (a breakpoint PC) and return (new_state, remaining_queue, native_result).  Used to capture a state at a chosen PC."""
    r = native().run(state, queue, stop, **kw)
    require(r['ok'], ('native advance failed', r))
    return native_state(r), r['remaining'], r


# ----------------------------------------------------------------------------------
# Comparison
# ----------------------------------------------------------------------------------
def compare_ports(cpp, nat):
    """Ordered port compare.  Rule: a C++ LONG device write at address a equals two native WORD writes (a, hi) (a+2, lo).  -> (difference or None, splits)."""
    i = j = splits = 0
    while i < len(cpp) and j < len(nat):
        a, n, v = cpp[i]
        if PVC_LO <= a < PVC_HI and n == 2:
            v &= 0xffff
        if (a, n, v) == tuple(nat[j]):
            i += 1
            j += 1
        elif n == 4 and tuple(nat[j:j + 2]) == ((a, 2, v >> 16), (a + 2, 2, v & 0xffff)):
            i += 1
            j += 2
            splits += 1
        else:
            return dict(field='ports', index=i, native_index=j, cpp=tuple(cpp[i]), native=tuple(nat[j])), splits
    if i != len(cpp) or j != len(nat):
        return dict(field='ports', index=i, native_index=j, cpp_len=len(cpp), native_len=len(nat), cpp=tuple(cpp[i]) if i < len(cpp) else None,
                    native=tuple(nat[j]) if j < len(nat) else None), splits
    return None, splits


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def compare(cpp, nat, queue):
    """Ordered list of differences between a C++ success result and a native result (empty = equal)."""
    out = []
    if not cpp['ok']:
        return [dict(field='cpp-error', error=cpp['error'], preserved=cpp['preserved'], committed=cpp['committed'])]
    if cpp['pc'] != nat['pc']:
        out.append(dict(field='pc', cpp=cpp['pc'], native=nat['pc']))
    for k in KEYS:
        if cpp['regs'][k] != nat['regs'][k]:
            out.append(dict(field='reg-' + k, cpp=cpp['regs'][k], native=nat['regs'][k]))
    if cpp['bank_base'] != nat['bank'][0]:
        out.append(dict(field='bank', cpp=cpp['bank_base'], native=nat['bank'][0]))
    if cpp['ram'] != nat['ram']:
        i = first_diff(cpp['ram'], nat['ram'])
        out.append(dict(field='ram', address=0x100000 + i, cpp=cpp['ram'][i], native=nat['ram'][i], count=sum(1 for x, y in zip(cpp['ram'], nat['ram']) if x != y)))
    if cpp['pvc'] != nat['pvc']:
        i = first_diff(cpp['pvc'], nat['pvc'])
        out.append(dict(field='pvc', address=PVC_LO + i, cpp=cpp['pvc'][i], native=nat['pvc'][i]))
    d, _ = compare_ports(cpp['ports'], nat['ports'])
    if d:
        out.append(d)
    if cpp.get('palette') != nat.get('palette'):
        cp, np_ = cpp.get('palette'), nat.get('palette')
        if cp is None or np_ is None:
            out.append(dict(field='palette', cpp=cp is not None, native=np_ is not None))
        elif cp[2] != np_[2]:
            out.append(dict(field='palette-selected', cpp=cp[2], native=np_[2]))
        else:
            b = 0 if cp[0] != np_[0] else 1
            i = first_diff(cp[b], np_[b])
            out.append(dict(field='palette-bank%d' % b, offset=i, cpp=cp[b][i], native=np_[b][i]))
    if [tuple(w) for w in cpp['waits']] != [tuple(w) for w in nat['waits']]:
        i = first_diff(cpp['waits'], nat['waits'])
        out.append(dict(field='waits', index=i, cpp=cpp['waits'][i] if i < len(cpp['waits']) else None, native=nat['waits'][i] if i < len(nat['waits']) else None))
    n = len(nat['consumed'])
    if cpp['remaining'] != nat['remaining'] or list(queue[n:]) != list(nat['remaining']):
        out.append(dict(field='queue-remaining', cpp=cpp['remaining'][:3], native=nat['remaining'][:3]))
    if cpp['reads'] != n + nat['status_reads']:
        out.append(dict(field='external-reads', cpp=cpp['reads'], native=n + nat['status_reads']))
    return out


def compare_reference(nat, ref):
    """Native result against an independent end state (ram, regs, pc, pvc, palette keys, any subset)."""
    out = []
    for k in ('pc', 'regs', 'pvc', 'palette'):
        if k in ref and ref[k] != nat[k]:
            out.append(dict(field='native-vs-reference-' + k))
    if 'ram' in ref and ref['ram'] != nat['ram']:
        i = first_diff(ref['ram'], nat['ram'])
        out.append(dict(field='native-vs-reference-ram', address=0x100000 + i))
    return out


# ----------------------------------------------------------------------------------
# Running fixtures
# ----------------------------------------------------------------------------------
def cpp_call(harness, fx, state=None, queue=None, stop=None):
    st = fx.state if state is None else state
    q = fx.queue if queue is None else queue
    return harness.call(encode_request(st, q, fx.stop if stop is None else stop, fx.releases, fx.wait_limit, fx.external_status, fx.card_answer),
                        st.get('palette') is not None)


UNSUPPORTED_PC = 'unsupported animation machine PC'
UNALIGNED_PC = 'unaligned animation machine PC'
_ROUTING = []
_TRAPS = frozenset([0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788])    # stage_event_ops_trap sites: not routed


def pc_routed(pc):
    """True when the checked-out dispatch chain of engine/src/animation_machine.cpp has an executor for pc (the chain text is parsed once)."""
    if not _ROUTING:
        src = (ROOT / 'engine/src/animation_machine.cpp').read_text()
        body = src[src.index('if ((next.pc>=0x3ac8'):src.index('else return am_error(c,"%s")' % UNSUPPORTED_PC)]
        for m in re.finditer(r'(?:else )?if \((.*?)\)ok=(\w+)\(c\);', body, re.S):
            e = m.group(1).replace('next.pc', 'p').replace('&&', ' and ').replace('||', ' or ')
            e = re.sub(r'!stage_event_ops_trap\(p\)', 'not trap(p)', e).replace('!=', '<>').replace('!', ' not ').replace('<>', '!=')
            _ROUTING.append(compile('(' + e.replace('\n', ' ') + ')', 'routing', 'eval'))
        require(len(_ROUTING) >= 100, ('routing rules', len(_ROUTING)))
    env = dict(p=pc, trap=lambda x: x in _TRAPS)
    return any(eval(r, env) for r in _ROUTING)


def check_fail_pc(harness, fx, state, queue):
    """Failing-PC evidence of an expected-error fixture (L-1 of review 0264).  The C++ error is atomic and carries no PC, so the PC is pinned by three facts:
    (1) the C++ run with stop = P (same state, queue, releases) succeeds and ends exactly at P, so the failing run does reach P through the same path;
    (2) for the shared text 'unsupported animation machine PC', P has no executor in the checked-out dispatch chain (the dispatcher fails there, not later);
    (3) for 'unaligned animation machine PC', P is odd (an odd landing reached from an even start must be declared; it cannot be a stop PC, so its reach is not checked).
    P = fx.fail_pc, default = the start PC of the C++ input.  The PC-carrying texts (1)-(3) need it; executor-specific texts only check it when it is declared.
    -> (ok, note)."""
    text = fx.expect[1]
    shared = text in (UNSUPPORTED_PC, UNALIGNED_PC)
    if fx.fail_pc is None and not shared:
        return True, None
    pc = state['pc'] if fx.fail_pc is None else fx.fail_pc
    if text == UNALIGNED_PC:
        if not pc & 1:
            return False, dict(field='fail-pc-not-odd (the start PC is even: declare the odd landing as fail_pc)', fail_pc=pc)
        if pc != state['pc']:
            return True, dict(fail_pc=pc, reach='odd landing (declared; an odd stop PC is not allowed, so the run to it is not checked)')
        return True, dict(fail_pc=pc)
    if text == UNSUPPORTED_PC:
        if pc & 1 or pc_routed(pc):
            return False, dict(field='fail-pc-routed-or-odd', fail_pc=pc)
    if pc != state['pc']:
        got = cpp_call(harness, fx, state, queue, pc)
        if not got['ok'] or got['pc'] != pc:
            return False, dict(field='fail-pc-not-reached', fail_pc=pc, got=got['error'] if not got['ok'] else hex(got['pc']))
    return True, dict(fail_pc=pc)


def run_one(harness, fx):
    """-> row dict (name, ok, expect, first_difference, stats)."""
    t0 = time.time()
    row = dict(name=fx.name, expect=fx.expect if isinstance(fx.expect, str) else list(fx.expect), digest=fx.digest(), meta=fx.meta)
    cst = fx.state if fx.cpp_state is None else fx.cpp_state
    cq = fx.queue if fx.cpp_queue is None else fx.cpp_queue
    got = cpp_call(harness, fx, cst, cq, fx.cpp_stop)
    if isinstance(fx.expect, tuple):
        text = fx.expect[1]
        ok = (not got['ok']) and text in got['error'] and got['preserved']
        row.update(ok=ok, cpp_error=None if got['ok'] else got['error'], preserved=got.get('preserved'), committed=got.get('committed'))
        if not ok:
            row['first_difference'] = dict(field='expected-error', wanted=text, got=got['error'] if not got['ok'] else 'C++ completed', preserved=got.get('preserved'))
        else:
            ok, note = check_fail_pc(harness, fx, cst, cq)
            row['fail_pc'] = note
            if not ok:
                row['ok'] = False
                row['first_difference'] = note
        row['seconds'] = round(time.time() - t0, 3)
        return row
    nat = native().run(fx.state, fx.queue, fx.stop, fx.releases, fx.wait_limit, fx.external_status, fx.card_answer, fx.max_insn)
    if not nat['ok']:
        row.update(ok=False, first_difference=dict(field='native-failed', error=nat['error'], detail=repr(nat.get('detail'))[:300]), seconds=round(time.time() - t0, 3))
        return row
    diffs = compare(got, nat, cq if fx.cpp_queue is not None else fx.queue)
    if fx.reference is not None:
        diffs = compare_reference(nat, fx.reference) + diffs
    row['stats'] = dict(ports=len(nat['ports']), waits=len(nat['waits']), wait_pcs=[hex(w[0]) for w in nat['waits']], consumed=len(nat['consumed']), status_reads=nat['status_reads'],
                        long_port_splits=compare_ports(got['ports'], nat['ports'])[1] if got['ok'] else 0)
    row['first_difference'] = diffs[0] if diffs else None
    row['difference_count'] = len(diffs)
    row['ok'] = (not diffs) if fx.expect == 'match' else bool(diffs)
    row['seconds'] = round(time.time() - t0, 3)
    return row


CTX = {}


def worker_init(exe, resources, out_dir):
    CTX['harness'] = Harness(exe, resources, Path(out_dir) / ('harness.%d.stderr' % os.getpid()))
    native()


def worker_run(fx):
    try:
        return run_one(CTX['harness'], fx)
    except Exception as e:                                       # a verifier fault is a failed row, never a match
        return dict(name=fx.name, ok=False, expect=str(fx.expect), first_difference=dict(field='verifier-error', error=repr(e)))


def run_fixtures(fixtures, workers=4, exe=None, resources=None, out_dir=None):
    """-> report rows (input order).  exe/resources default to build_harness()/program resources."""
    out_dir = Path(out_dir or BUILD)
    out_dir.mkdir(parents=True, exist_ok=True)
    if exe is None:
        exe = build_harness(workers)['exe']
    if resources is None:
        resources = program_resources()
    names = [f.name for f in fixtures]
    require(len(set(names)) == len(names), 'duplicate fixture names')
    if workers <= 1 or len(fixtures) <= 1:
        worker_init(exe, resources, out_dir)
        try:
            return [worker_run(f) for f in fixtures]
        finally:
            CTX['harness'].close()
    ctx = multiprocessing.get_context('fork')
    with ctx.Pool(min(workers, len(fixtures)), worker_init, (exe, resources, str(out_dir))) as pool:
        return pool.map(worker_run, fixtures, chunksize=1)


# ----------------------------------------------------------------------------------
# Build and inputs
# ----------------------------------------------------------------------------------
def machine_sources():
    line = [l for l in (ROOT / 'Makefile').read_text().splitlines() if l.startswith('ANIMATION_MACHINE_SOURCES =')][0]
    return [ROOT / s for s in line.split('=', 1)[1].split()] + [ROOT / 'engine/src/physical_rom_resource.cpp']


def header_files():
    return sorted(set((ROOT / 'engine/include').rglob('*.h')) | set((ROOT / 'engine/src').rglob('*.h')))


def program_resources():
    import verify_animation_machine as common
    import observe_animation_machine_scheduler as S
    resources, _ = common.resource_audit(ROOT, S.load_rom())
    return resources


def build_harness(jobs=4):
    """Compile all ANIMATION_MACHINE_SOURCES (object cache keyed by source, headers, flags, compiler) and the harness; -> dict(exe, sources, command, ...)."""
    compiler = Path(shutil.which('clang++'))                      # not resolved: the symlink target 'clang' would not link libstdc++
    flags = ['-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(ROOT / 'engine/include')]
    version = subprocess.run([str(compiler), '--version'], stdout=subprocess.PIPE, text=True).stdout
    headers = hashlib.sha256()
    for h in header_files():
        headers.update(str(h.relative_to(ROOT)).encode() + file_sha(h).encode())
    objdir = BUILD / 'obj'
    objdir.mkdir(parents=True, exist_ok=True)
    srcs = machine_sources()
    objs, procs, fresh = [], [], 0
    log = open(BUILD / 'build.stderr', 'ab')
    for s in srcs:
        key = sha((file_sha(s) + headers.hexdigest() + ' '.join(flags) + version).encode())[:16]
        o = objdir / ('%s.%s.o' % (s.stem, key))
        objs.append(o)
        if o.exists():
            continue
        fresh += 1
        while len([p for p, _, _ in procs if p.poll() is None]) >= jobs:
            time.sleep(0.05)
        tmp = o.with_suffix('.tmp')
        procs.append((subprocess.Popen([str(compiler)] + flags + ['-c', str(s), '-o', str(tmp)], stdout=subprocess.DEVNULL, stderr=log), tmp, o))
    for p, tmp, o in procs:
        require(p.wait() == 0, ('compile failed', str(o)))
        tmp.replace(o)
    exe = BUILD / 'unit_fixture_acceptance'
    cmd = [str(compiler)] + flags + [str(HARNESS)] + [str(o) for o in objs] + ['-o', str(exe)]
    require(subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log).returncode == 0, 'link failed')
    log.close()
    live = set(objs)
    for old in objdir.glob('*.o'):                                # drop stale cache entries
        if old not in live:
            old.unlink()
    return dict(exe=exe, sources=srcs, compiler=compiler, compiler_version=version.splitlines()[0], command=' '.join(cmd[:8]) + ' ... -o ' + str(exe), fresh_objects=fresh)


def input_shas(exe, srcs, spec_path, compiler):
    import unicorn
    S = native().S
    libs = sorted(set(Path(unicorn.__file__).parent.rglob('libunicorn*.so*')) | set(Path(unicorn.__file__).parent.rglob('libunicorn*.dylib')))
    res = program_resources()
    out = dict(rom=dict(path='extracted/program/maincpu.decrypted.be.bin', sha256=sha(native().program), expected=S.ROM_SHA),
               program_rom_resources={str(p.relative_to(ROOT)): file_sha(p) for p in res},
               engine_sources={str(p.relative_to(ROOT)): file_sha(p) for p in srcs},
               engine_headers={str(p.relative_to(ROOT)): file_sha(p) for p in header_files()},
               harness={str(HARNESS.relative_to(ROOT)): file_sha(HARNESS)}, harness_binary_sha256=file_sha(exe),
               tools={'tools/' + n: file_sha(TOOLS / n) for n in PINNED_TOOLS if (TOOLS / n).exists()},
               unicorn=dict(version=unicorn.__version__, libraries={str(p): file_sha(p) for p in libs}),
               compiler=dict(path=str(compiler), sha256=file_sha(Path(compiler).resolve())), python=sys.version.split()[0])
    if spec_path:
        out['spec'] = {str(Path(spec_path).resolve().relative_to(ROOT)) if Path(spec_path).resolve().is_relative_to(ROOT) else str(spec_path): file_sha(spec_path)}
    return out


# ----------------------------------------------------------------------------------
# Natural seed machinery (D1 verifier): prepared seeds, native frames, states at chosen PCs
# ----------------------------------------------------------------------------------
def seed_frames(case, frames):
    """Run the D1 native reference (FH HeadRun, 'continuous', base configuration) for `frames` frames of seed `case`; -> list of per-frame records
    (frame, start = H entry state, h = {ext queue, end state, waits...} or None, n = {start, end, dev, waits, cbs} or None).  Reuses the frame driver's setup."""
    import verify_animation_machine_frame_driver as D
    if D.FH is None:
        D.setup_native()
    if 'cls' not in D.CTX:
        D.CTX['cls'] = D.make_verify_class()
        D.CTX['answer'] = D.R.DEFAULT_ANSWER
    sd, snap, meta, rec, carried = D.FH.prepared(case)
    out = []
    snapc = {k: v for k, v in carried.items() if k != 'prep_entry_state'}
    run = D.CTX['cls'](D.R.G['program'], D.R.G['fixed'], D.R.G['levels'], snapc, 'continuous', frames, heavy=False, plan=None, sink=None, extend=False,
                       answer=D.R.DEFAULT_ANSWER, full_dump=False, prep_dump=None, cfg=dict(D.FH.BASE_CFG), case=case, tbset=None, keep_all=False, do_model=False)
    run.on_frame = out.append
    run.run()
    return out


def natural_cases(count=None):
    """Natural D1 seed case numbers (sorted), via the frame driver's declared Linux seed rebase."""
    import verify_animation_machine_frame_driver as D
    if D.FH is None:
        D.setup_native()
    cases = [c for c in sorted(D.S.SEEDS) if D.S.SEEDS[c]['kind'] == 'natural']
    return cases if count is None else cases[:count]


def seed_state(captured, carry=0):
    """FH capture (ram, regs, pc, bank, pvc, status) -> fixture state."""
    return make_state(captured['ram'], captured['regs'], captured['pc'], captured['bank'], captured['pvc'], carry)


def seed_h_fixtures(case, frames, upto=None, name='h', expect='match', **kw):
    """One fixture per frame k >= 1 (k < frames, optionally only frames in `upto`): the H segment from the frame-head entry (e4a/e74) to the controller c52a, with
    FH's declared external queue and the native status byte; the FH end state is attached as an independent `reference` that the native result must equal."""
    out = []
    for fr in seed_frames(case, frames):
        h = fr.get('h')
        if h is None or h['reason']['reason'] != 'controller' or (upto is not None and fr['frame'] not in upto):
            continue
        end = h['end']
        out.append(Fixture('%s-seed%d-f%d' % (name, case, fr['frame']), seed_state(fr['start']), h['ext'], end['pc'], expect, external_status=fr['start']['status'],
                           reference=dict(ram=end['ram'], regs=end['regs'], pc=end['pc']), meta=dict(case=case, frame=fr['frame'], segment='H', start_pc=fr['start']['pc']), **kw))
    return out


def seed_n_fixtures(case, frames, upto=None, name='n', expect='match', **kw):
    """One fixture per frame in `upto` (default all < frames) for the whole N pass (dispatcher 2ac2 to the next frame-head callback), native-declared queue and
    status byte, FH end state as `reference`.  A frame with the BIOS card request (seed natural frame 244) exercises the card release."""
    import verify_animation_machine_frame_driver as D
    out = []
    for fr in seed_frames(case, frames):
        n = fr.get('n')
        if n is None or n['reason']['reason'] != 'frame-head' or (upto is not None and fr['frame'] not in upto):
            continue
        queue, _, other = D.n_queue(n['dev'])
        if other:
            continue
        end = n['end']
        out.append(Fixture('%s-seed%d-f%d' % (name, case, fr['frame']), seed_state(n['start']), queue, end['pc'], expect, external_status=fr['start']['status'],
                           reference=dict(ram=end['ram'], regs=end['regs'], pc=end['pc']), meta=dict(case=case, frame=fr['frame'], segment='N', start_pc=n['start']['pc']), **kw))
    return out


def seed_node_fixture(case, frame, node=0, name='node', **kw):
    """A node of the N pass: native N pass start of `frame` advanced (Unicorn) to the entry of node `node` (breakpoint at its callback), then a fixture from that state to the
    pass dispatcher return PC stored at the shared stack top (the node's RTS target).  -> Fixture, or None when the frame has no such node."""
    frs = [f for f in seed_frames(case, frame + 1) if f['frame'] == frame]
    require(frs, ('no such frame', case, frame))
    fr = frs[0]
    n = fr.get('n')
    if not n or node >= len(n['cbs']):
        return None
    start = seed_state(n['start'])
    queue = [(a, s, v) for _, a, s, v in n['dev'] if a in (0x300000, 0x340000, 0x380000, 0x3c0006)]
    cb = n['cbs'][node]
    st, rest, _ = advance_native(start, queue, cb, external_status=fr['start']['status'])
    ret = int.from_bytes(st['ram'][(st['regs']['a7']) & 0xffff:(st['regs']['a7'] & 0xffff) + 4], 'big')
    return Fixture('%s-seed%d-f%d-n%d-%x' % (name, case, frame, node, cb), st, rest, ret, external_status=fr['start']['status'],
                   meta=dict(case=case, frame=frame, node=node, callback=cb, return_pc=ret), **kw)


# ----------------------------------------------------------------------------------
# Report and CLI
# ----------------------------------------------------------------------------------
def load_spec(path):
    spec = importlib.util.spec_from_file_location('unit_fixture_spec', str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, 'FIXTURES'):
        return list(mod.FIXTURES)
    require(hasattr(mod, 'build'), 'spec must define FIXTURES or build()')
    return list(mod.build())


def make_report(rows, fixtures, inputs, build, started, spec):
    bad = [r for r in rows if not r['ok']]
    kinds = collections.Counter(('error' if isinstance(f.expect, tuple) else f.expect) for f in fixtures)
    totals = dict(fixtures=len(rows), ok=len(rows) - len(bad), failed=len(bad), expect_kinds=dict(kinds),
                  ports=sum(r.get('stats', {}).get('ports', 0) for r in rows), waits=sum(r.get('stats', {}).get('waits', 0) for r in rows),
                  consumed_reads=sum(r.get('stats', {}).get('consumed', 0) for r in rows))
    return dict(tool='tools/verify_animation_machine_unit_fixtures.py', spec=str(spec), ok=not bad, totals=totals,
                first_failure=bad[0] if bad else None, inputs=inputs, build=dict(command=build['command'], compiler_version=build['compiler_version'], fresh_objects=build['fresh_objects']),
                elapsed_seconds=round(time.time() - started, 1), rows=rows,
                limits=['Carry has no SR oracle; only a valid tag is checked.  Video is ordered ports, not pixels.',
                        'C++ LONG device writes equal two native WORD writes at a and a+2 (declared rule).',
                        'An expected-error fixture checks the C++ error text, state preservation and (shared PC texts, or when declared) the failing PC; native is not run for it.'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--spec', required=True, help='python file defining FIXTURES (list) or build() -> list')
    ap.add_argument('--out', required=True, help='output directory (report.json, logs); must be inside the checkout or the scratchpad')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--only', help='comma list of fixture-name substrings')
    args = ap.parse_args(argv)
    require(not sys.flags.optimize, 'optimized Python disables checks')
    started = time.time()
    out = Path(args.out).absolute()
    out.mkdir(parents=True, exist_ok=True)
    build = build_harness(args.workers)
    fixtures = load_spec(args.spec)
    if args.only:
        keys = args.only.split(',')
        fixtures = [f for f in fixtures if any(k in f.name for k in keys)]
    before = input_shas(build['exe'], build['sources'], args.spec, build['compiler'])
    rows = run_fixtures(fixtures, args.workers, build['exe'], program_resources(), out)
    after = input_shas(build['exe'], build['sources'], args.spec, build['compiler'])
    report = make_report(rows, fixtures, before, build, started, args.spec)
    report['inputs_unchanged_after'] = before == after
    report['ok'] = report['ok'] and report['inputs_unchanged_after']
    (out / 'report.json').write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + '\n')
    for r in rows:
        print('%-4s %-44s %s' % ('ok' if r['ok'] else 'FAIL', r['name'], '' if r['ok'] else json.dumps(r.get('first_difference'), default=str)[:200]), file=sys.stderr)
    print(json.dumps(dict(ok=report['ok'], totals=report['totals'], elapsed_seconds=report['elapsed_seconds'], report=str(out / 'report.json')), sort_keys=True))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
