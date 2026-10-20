"""F6-D frame driver acceptance, IRQ execution: C++ step_animation_machine_frame / run_animation_machine_pass with AnimationFrameOptions.irq_execution and the
palette RAM overloads versus native Unicorn execution of the original ROM in which the IRQ-effect waits are released by a delivered vblank IRQ.

Native reference: the D1 verifier's FH HeadRun subclass (tools/verify_animation_machine_frame_driver.py make_verify_class, imported, not edited; same declared
platform rebase of the stage_entry_body seeds, same routing text, base configuration, card answer, D1 frame protocol H + declared controller skip + N), changed only
at the IRQ-effect waits (scope decision E1 A): at ef2 / 16bd0 (H) and cda4 / 3aea / 47af0 / 478de (N) one IRQ is delivered instead of the declared release:
  push LONG wait PC, WORD SR 2000 (declared), SR := 2100, PC := LONG ROM[64] (= 20c); IRQ phase reads: BYTE 320000 := --z80 (default 0), WORD 3c0006 := --video
  (default 0) (E7, written into the device page by a read hook); the BIOS SYSTEM_IO fetch c0044a with LONG (A7) = 248 is the declared resume (PC := 248,
  A7 += 4; E4); the RTE at 29a / 2cc / 2d6 is emulated (Unicorn 2.1.4 cannot execute RTE: pop SR WORD, PC LONG, A7 += 6; E3); the IRQ must return to the wait
  PC with D0-D7 / A0-A7 unchanged and SR 2000; then the wait block runs again (re-delivery while it still waits, at most 16 waits per segment as in D1).
Palette RAM (E6 as decided): 400000..7fffff is the 512-fold mirror of one 8 KiB view of the selected bank; BYTE writes to 3a000f / 3a001f select bank 0 / 1
(the view is swapped with the stored bank).  Seed preparation P1 (E5, declared, applied to the RNG-prepared seed RAM): the original 3dce and c42 run natively
(to their RTS at 3de4 / c62, registers discarded) and BYTE 10fd80 |= 80 (a1e BSET), cross-checked against the P2 + c42 values.

Per seed and frame:
  frame 0  native N0                       vs C++ run_animation_machine_pass (mode 0, irq_execution, palette attached);
  frame k  native H_k + skip + N_k         vs C++ step_animation_machine_frame (mode 1) from the native H start, plus mode 0 from the native N start.
Compared: everything of D1 (RAM, D0-D7/A0-A7, PC, bank base, PVC page, ordered head / node ports without the IRQ ports, waits (card only: IRQ waits are not
AnimationFrameWait records), external reads per segment, stop PCs, carry Unknown, queue fully consumed) plus the palette banks and selection, the ordered IRQ
records (segment, wait PC, sequence, port range, reads, BIOS resumes, popped SR) and the ordered IRQ ports.  The C++ queue is the D1 queue (H declared reads,
N device reads); the IRQ reads come from the options.  Native non-completions must make C++ fail with the declared checked error and preserved state.
Full pure-C++ chain for every seed; determinism: two chain runs for the first natural seeds.  Negatives on one seed.
"""
import argparse
import collections
import ctypes
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import verify_animation_machine_frame_driver as D  # noqa: E402  (imported, never edited)

OUT = ROOT / 'artifacts/animation_machine_frame_irq'
BUILD = ROOT / 'build/frame_irq_acceptance'
HARNESS = ROOT / 'engine/tools/frame_irq_acceptance.cpp'
KEYS = D.KEYS
MODE_PASS, MODE_STEP = 0, 1
OPT_IRQ, OPT_PALETTE = 0x800, 0x1000
IRQ_WAIT_PCS = (0xef2, 0x16bd0, 0xcda4, 0x3aea, 0x47af0, 0x478de)
BIOS_IO, BIOS_INT1, IRQ_RESUME, RTE_PCS = 0xc0044a, 0xc00438, 0x248, (0x29a, 0x2cc, 0x2d6)
PAL_LO, PAL_SIZE, PAL_SELECT = 0x400000, 0x2000, {0x3a000f: 0, 0x3a001f: 1}
IRQ_DEVICE_READS = {(0x320000, 1), (0x3c0006, 2), (D.STATUS_ADDR, 1)}
CHAIN_SEEDS = 4
NATIVE_END_ERROR = dict(D.NATIVE_END_ERROR)
NATIVE_END_ERROR.update({'wait-not-released': 'animation irq wait not released', 'irq:bios-int1': 'animation irq bios int1 boundary',
                         'irq:internal-wait': 'animation irq internal wait'})
EXPECTED = dict(natural_seeds=137, natural_complete_400=136, p1_irqs=108528)   # scope doc 6 (probe P1 + mirror); D1 complete frames 54,400
CTX = {}


# ----------------------------------------------------------------------------------
# Packets (ROM-free)
# ----------------------------------------------------------------------------------
def encode_request(mode, st, queue, irq=True, palette=True, z80=0, video=0, card_resume=True, card_answer=0x80):
    ram, pvc = st['ram'], st['pvc']
    b0, b1, sel = st['palette']
    assert len(ram) == 65536 and len(pvc) == 8192 and len(b0) == 8192 and len(b1) == 8192
    options = (0x100 if card_resume else 0) | (card_answer & 0xff) | (OPT_IRQ if irq else 0) | (OPT_PALETTE if palette else 0)
    values = [mode] + [st['regs'][k] & 0xffffffff for k in KEYS] + [st['pc'], 0, st['bank'][0], st['status'], options, 0x01010000, z80 & 0xff, video & 0xffff,
                                                                     sel, len(queue)]
    return struct.pack('>27I', *values) + bytes(ram) + bytes(pvc) + bytes(b0) + bytes(b1) + b''.join(struct.pack('>III', *e) for e in queue)


def parse_response(payload):
    if len(payload) < 8:
        raise ValueError('short harness packet')
    ok = struct.unpack_from('>I', payload)[0]
    if ok == 0:
        return dict(ok=False, preserved=struct.unpack_from('>I', payload, 4)[0] == 1, error=payload[8:].decode('latin-1'))
    n0 = 35
    if ok != 1 or len(payload) < 4 * n0 + 65536 + 8192 + 16384:
        raise ValueError('invalid harness packet')
    v = struct.unpack_from('>%dI' % n0, payload)
    pc, carry, bank, head_pc, ctrl_pc, stop_pc, exit_pc, hreads, nreads, creads, nh, nn, nc, nw, nr, ni, np_, sel = v[1:19]
    regs = dict(zip(KEYS, v[19:35]))
    at = 4 * n0
    if len(payload) != at + 65536 + 8192 + 16384 + 12 * (nh + nn + nc + np_ + nr) + 24 * nw + 32 * ni:
        raise ValueError('invalid harness packet length')
    ram = payload[at:at + 65536]
    at += 65536
    pvc = payload[at:at + 8192]
    at += 8192
    pal = (payload[at:at + 8192], payload[at + 8192:at + 16384], sel)
    at += 16384

    def triples(n):
        nonlocal at
        out = [struct.unpack_from('>III', payload, at + 12 * i) for i in range(n)]
        at += 12 * n
        return out
    head_ports, node_ports, ctrl_ports = triples(nh), triples(nn), triples(nc)
    waits = [struct.unpack_from('>6I', payload, at + 24 * i) for i in range(nw)]
    at += 24 * nw
    irqs = [struct.unpack_from('>8I', payload, at + 32 * i) for i in range(ni)]
    at += 32 * ni
    irq_ports = triples(np_)
    remaining = triples(nr)
    return dict(ok=True, pc=pc, carry=carry, bank_base=bank, head_pc=head_pc, controller_pc=ctrl_pc, pass_stop_pc=stop_pc, controller_exit_pc=exit_pc,
                head_reads=hreads, node_reads=nreads, controller_reads=creads, regs=regs, ram=ram, pvc=pvc, palette=pal, head_ports=head_ports,
                node_ports=node_ports, controller_ports=ctrl_ports, waits=waits, irqs=irqs, irq_ports=irq_ports, remaining=remaining)


def compare(got, exp):
    """D1 comparison plus palette, IRQ records and IRQ ports (empty = equal)."""
    bad = D.compare(got, exp)
    if not got['ok']:
        return bad
    if got['palette'] != exp['palette']:
        g, e = got['palette'], exp['palette']
        bank = 0 if g[0] != e[0] else 1
        i = D.first_diff(g[bank], e[bank]) if g[bank] != e[bank] else None
        bad.append(dict(field='palette', selected=(g[2], e[2]), bank=bank, first=i))
    irqs = [tuple(q) for q in got['irqs']]
    if irqs != exp['irqs']:
        i = D.first_diff(irqs, exp['irqs'])
        bad.append(dict(field='irqs', index=i, cpp=irqs[i] if i is not None and i < len(irqs) else None,
                        native=exp['irqs'][i] if i is not None and i < len(exp['irqs']) else None, cpp_len=len(irqs), native_len=len(exp['irqs'])))
    conv, _ = D.cpp_ports_native_form(got['irq_ports'], exp['irq_ports'])
    if conv != exp['irq_ports']:
        i = D.first_diff(conv, exp['irq_ports'])
        bad.append(dict(field='irq_ports', index=i, cpp=conv[i] if i is not None and i < len(conv) else None,
                        native=exp['irq_ports'][i] if i is not None and i < len(exp['irq_ports']) else None, cpp_len=len(conv), native_len=len(exp['irq_ports'])))
    if got['controller_ports'] or got['controller_reads'] or got['controller_exit_pc']:
        bad.append(dict(field='controller', why='controller output in Skip mode'))
    return bad


def check_expected_failure(got, label, kind):
    if got['ok']:
        return dict(check=label, ok=False, native_kind=kind, why='C++ completed where native did not complete the frame')
    expected = NATIVE_END_ERROR.get(kind)
    ok = bool(got['preserved']) and expected is not None and got['error'] == expected
    r = dict(check=label, ok=ok, native_kind=kind, expected_error=expected, error=got['error'], preserved=got['preserved'])
    if not ok:
        r['why'] = 'native stop kind without a declared C++ error' if expected is None else 'C++ error or preservation differs'
    return r


def state_digest(st):
    h = hashlib.sha256(b'MS5-F6D-FRAME-STATE-1')
    h.update(bytes(st['ram']))
    h.update(struct.pack('>16I', *[st['regs'][k] & 0xffffffff for k in KEYS]))
    h.update(struct.pack('>II', st['pc'], st['bank'][0]))
    h.update(bytes(st['pvc']))
    h.update(bytes(st['palette'][0]) + bytes(st['palette'][1]) + bytes([st['palette'][2]]))
    return h.hexdigest()


class Harness(D.Harness):
    def call(self, payload):
        self.proc.stdin.write(struct.pack('>I', len(payload)) + payload)
        self.proc.stdin.flush()
        head = self.proc.stdout.read(4)
        if len(head) != 4:
            raise RuntimeError('harness died (exit %r)' % self.proc.poll())
        n = struct.unpack('>I', head)[0]
        data = self.proc.stdout.read(n)
        if len(data) != n:
            raise RuntimeError('truncated harness response')
        self.calls += 1
        return parse_response(data)


def request_for(mode, st, queue, **kw):
    kw.setdefault('card_answer', CTX.get('answer', 0x80))
    kw.setdefault('z80', CTX.get('z80', 0))
    kw.setdefault('video', CTX.get('video', 0))
    return encode_request(mode, st, queue, **kw)


# ----------------------------------------------------------------------------------
# Native: P1 preparation and the D1 VerifyRun with IRQ delivery
# ----------------------------------------------------------------------------------
P1_EXPECT = ((0x100006, 4, 0x3dcc), (0x10000a, 4, 0x3dcc), (0x10081c, 4, 0x10081c), (0x100016, 1, 0), (0x100017, 1, 2), (0x10001a, 1, 0),
             (0x100019, 1, 0), (0x10001b, 1, 0))


def p1_prep(snap):
    """Declared P1: original 3dce (to its RTS 3de4) and c42 (to its RTS c62) natively on the seed RAM, registers discarded; then BYTE 10fd80 |= 80."""
    S, R = D.S, D.R
    ps = dict(snap, regs=dict(snap['regs']), pc=0x3dce)
    assert ps['regs']['a5'] == 0x108000, hex(ps['regs']['a5'])
    mach = S.Machine(R.G['program'], R.G['fixed'], ps)
    mach.install_basic_hooks()
    c = mach.cpu
    for entry, stop in ((0x3dce, 0x3de4), (0xc42, 0xc62)):
        c.emu_start(entry, stop, count=100)
        assert mach.pc() == stop and mach.odd is None and mach.invalid is None and mach.intr is None and mach.fetch_unmapped is None, (hex(entry), mach.pc())
    ram = bytearray(mach.ram())
    ram[0xfd80] |= 0x80
    before = snap['ram']
    diff = [0x100000 + i for i in range(65536) if before[i] != ram[i]]
    for a, n, v in P1_EXPECT:
        assert int.from_bytes(ram[a & 0xffff:(a & 0xffff) + n], 'big') == v, hex(a)
    assert ram[0x4d91] & 0x10 == 0 and ram[0xfd80] & 0x80
    return bytes(ram), dict(changed_bytes=len(diff), changed=[hex(a) for a in diff], ports=len(mach.ports))


def make_irq_class():
    FH, S = D.FH, D.S
    UC_REG = S.UC_REG
    import unicorn
    Verify = D.make_verify_class()
    M32 = 0xffffffff

    class IrqRun(Verify):
        def __init__(self, *a, **kw):
            self.z80 = kw.pop('z80')
            self.video = kw.pop('video')
            Verify.__init__(self, *a, **kw)
            self.irq_total = collections.Counter()
            self.frame_irqs = []
            self.irq_fail = None
            self.pal_reads = collections.Counter()
            self.h_p0 = self.n_p0 = 0

        def build(self, snap):
            mach = Verify.build(self, snap)
            c = mach.cpu
            for base in (0x320000, 0x3a0000):
                c.mem_map(base, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
            self.pal_view = (ctypes.c_ubyte * PAL_SIZE)()
            c._keep.append(self.pal_view)
            for i in range(0x200):
                c.mem_map_ptr(PAL_LO + i * PAL_SIZE, PAL_SIZE, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE, ctypes.addressof(self.pal_view))
            self.pal_banks = [bytearray(PAL_SIZE), bytearray(PAL_SIZE)]
            self.pal_sel = 0
            c.hook_add(FH.UC_HOOK_MEM_WRITE, self.h_palsel, begin=0x3a000f, end=0x3a001f)
            c.hook_add(FH.UC_HOOK_MEM_READ, self.h_irqread, begin=0x320000, end=0x320000)
            c.hook_add(FH.UC_HOOK_MEM_READ, self.h_irqread, begin=0x3c0006, end=0x3c0007)
            c.hook_add(FH.UC_HOOK_MEM_READ, self.h_palread, begin=PAL_LO, end=0x7fffff)
            return mach

        def h_palsel(self, uc, access, address, size, value, user):
            if size != 1 or address not in PAL_SELECT:
                return
            new = PAL_SELECT[address]
            if new != self.pal_sel:
                self.pal_banks[self.pal_sel][:] = bytes(self.pal_view)
                ctypes.memmove(self.pal_view, bytes(self.pal_banks[new]), PAL_SIZE)
                self.pal_sel = new
                self.irq_total['palette-bank-switch'] += 1

        def h_irqread(self, uc, access, address, size, value, user):
            if self.phase != 'I':
                return
            if address == 0x320000 and size == 1:
                uc.mem_write(0x320000, bytes([self.z80 & 0xff]))
            elif address == 0x3c0006 and size == 2:
                uc.mem_write(0x3c0006, (self.video & 0xffff).to_bytes(2, 'big'))

        def h_palread(self, uc, access, address, size, value, user):
            self.pal_reads[self.phase] += 1

        def palette_state(self):
            b = [bytes(x) for x in self.pal_banks]
            b[self.pal_sel] = bytes(self.pal_view)
            return (b[0], b[1], self.pal_sel)

        def capture(self):
            st = Verify.capture(self)
            st['palette'] = self.palette_state()
            return st

        def run_head(self, frame):
            self.frame_irqs = []
            self.irq_fail = None
            self.h_p0 = len(self.m.ports)
            return Verify.run_head(self, frame)

        def run_pass(self):
            if self.frame == 0:
                self.frame_irqs = []
                self.irq_fail = None
            self.n_p0 = len(self.m.ports)
            return Verify.run_pass(self)

        def deliver(self, ret_pc):
            mach = self.m
            c = mach.cpu
            old = self.phase
            pre = mach.regs()
            a7 = (pre['a7'] - 4) & M32
            mach.put(a7, 4, ret_pc)
            a7 = (a7 - 2) & M32
            mach.put(a7, 2, 0x2000)
            c.reg_write(UC_REG['sr'], 0x2100)
            c.reg_write(UC_REG['a7'], a7)
            pc = int.from_bytes(bytes(D.R.G['program'][0x64:0x68]), 'big')
            self.phase = 'I'
            p0 = len(mach.ports)
            d0 = len(self.devlog)
            res, bios, sr = 'ok', 0, None
            for _ in range(8):
                mach.fetch_unmapped = mach.odd = mach.invalid = mach.intr = None
                try:
                    c.emu_start(pc, ret_pc, count=2000000)
                    err = None
                except unicorn.UcError as e:
                    err = str(e)
                if self.stop is not None:
                    res = 'stop:%s' % self.stop.get('reason')
                    break
                if self.waiting is not None:
                    res = 'internal-wait'
                    self.waiting = None
                    break
                sp = c.reg_read(UC_REG['a7'])
                if mach.fetch_unmapped == BIOS_IO and mach.long(sp) == IRQ_RESUME:
                    c.reg_write(UC_REG['a7'], (sp + 4) & M32)
                    pc = IRQ_RESUME
                    bios += 1
                    continue
                if mach.fetch_unmapped == BIOS_INT1:
                    res = 'bios-int1'
                    break
                if mach.intr and mach.intr['number'] == 256 and mach.intr['pc'] in RTE_PCS:
                    sr = mach.word(sp)
                    pc = mach.long(sp + 2)
                    c.reg_write(UC_REG['sr'], sr)
                    c.reg_write(UC_REG['a7'], (sp + 6) & M32)
                    c.reg_write(UC_REG['pc'], pc)
                    mach.intr = None
                    if pc == ret_pc:
                        break
                    continue
                if mach.fetch_unmapped is not None:
                    res = 'fetch-unmapped:%x' % mach.fetch_unmapped
                elif mach.odd or mach.invalid or mach.intr or err:
                    res = 'error:%s' % (mach.odd or mach.invalid or mach.intr or err)
                else:
                    res = 'no-rte'
                break
            post = mach.regs()
            if res == 'ok':
                if any(pre[k] != post[k] for k in pre) or mach.pc() != ret_pc:
                    res = 'regs-differ'
                elif c.reg_read(UC_REG['sr']) & 0xffff != 0x2000:
                    res = 'sr:%x' % c.reg_read(UC_REG['sr'])
            reads = [(a, n) for ph, a, n, v in self.devlog[d0:] if ph == 'I']
            if res == 'ok' and any(r not in IRQ_DEVICE_READS for r in reads):
                res = 'undeclared-read'
            self.phase = old
            rec = dict(segment=0 if old == 'H' else 1, pc=ret_pc, ports=list(mach.ports[p0:]), p0=p0, p1=len(mach.ports), reads=len(reads), bios=bios,
                       sr=sr, res=res)
            self.irq_total['delivered'] += 1
            self.irq_total['at:%x' % ret_pc] += 1
            self.irq_total['res:' + res.split(':')[0]] += 1
            self.irq_total['bios'] += bios
            return rec

        def release_wait(self, w):
            if w['pc'] not in IRQ_WAIT_PCS:
                return Verify.release_wait(self, w)
            rec = self.deliver(w['pc'])
            self.frame_irqs.append(rec)
            if rec['res'] != 'ok':
                if self.irq_fail is None:
                    self.irq_fail = rec['res']
                return []
            return [('irq', len(self.frame_irqs) - 1, 0)]
    return IrqRun


# ----------------------------------------------------------------------------------
# Expectations from one native frame
# ----------------------------------------------------------------------------------
def drop_ranges(ports, base, ranges):
    """Native port list starting at absolute index base without the IRQ port ranges -> (list, mapper of relative positions)."""
    keep = []
    cut = []
    for j, p in enumerate(ports):
        a = base + j
        if any(lo <= a < hi for lo, hi in ranges):
            cut.append(j)
            continue
        keep.append(p)

    def mapper(j):
        return j - sum(1 for x in cut if x < j)
    return keep, mapper


def irq_tuples(irqs, first_seq=0):
    out, ports, at = [], [], 0
    for k, q in enumerate(irqs):
        out.append((q['segment'], q['pc'], first_seq + k, at, at + len(q['ports']), q['reads'], q['bios'], q['sr'] if q['sr'] is not None else 0))
        at += len(q['ports'])
        ports.extend(tuple(p) for p in q['ports'])
    return out, ports


def irq_frame(run, fr):
    """-> (category, expectations) for one native frame with IRQs (D.frame_expectation on the frame with the IRQ ports and IRQ waits removed)."""
    irqs = list(run.frame_irqs)
    ranges = [(q['p0'], q['p1']) for q in irqs]
    fr2 = dict(fr)
    if fr.get('h') is not None:
        h = dict(fr['h'])
        h['ports'], _ = drop_ranges(fr['h']['ports'], run.h_p0, ranges)
        h['rec'] = dict(h['rec'], waits=[w for w in h['rec']['waits'] if w['pc'] not in IRQ_WAIT_PCS])
        fr2['h'] = h
    if fr.get('n') is not None:
        n = dict(fr['n'])
        n['ports'], mapper = drop_ranges(fr['n']['ports'], run.n_p0, ranges)
        n['split'] = [(mapper(lo), mapper(hi)) for lo, hi in fr['n']['split']]
        n['waits'] = [w for w in fr['n']['waits'] if w['pc'] not in IRQ_WAIT_PCS]
        fr2['n'] = n
    if run.irq_fail is not None:
        kind = 'irq:' + run.irq_fail.split(':')[0]
        return 'native-irq-stop:' + run.irq_fail, None, kind, irqs
    if fr.get('h') is not None and fr['h']['reason']['reason'] != 'controller':
        return 'native-H-stop:' + fr['h']['reason']['reason'], None, fr['h']['reason']['reason'], irqs
    cat, ex = D.frame_expectation(fr2)
    kind = D.native_kind(cat, fr2) if cat != 'complete' else None
    all_t, all_p = irq_tuples(irqs)
    n_irqs = [q for q in irqs if q['segment'] == 1]
    n_t, n_p = irq_tuples(n_irqs)
    ex['exp_n'] = dict(ex['exp_n'], palette=fr['n']['end']['palette'], irqs=n_t, irq_ports=n_p)
    if 'exp_step' in ex:
        ex['exp_step'] = dict(ex['exp_step'], palette=fr['n']['end']['palette'], irqs=all_t, irq_ports=all_p)
    return cat, ex, kind, irqs


def compare_frame(harness, run, fr):
    cat, ex, kind, irqs = irq_frame(run, fr)
    frame = fr['frame']
    row = dict(frame=frame, category=cat, checks={}, irqs=len(irqs))
    queue_h = list(fr['h']['ext']) if fr.get('h') else []
    if ex is None:
        q = queue_h + (D.n_queue(fr['n']['dev'])[0] if fr.get('n') else [])
        got = harness.call(request_for(MODE_PASS if frame == 0 else MODE_STEP, fr['start'], q))
        row['checks']['step'] = check_expected_failure(got, 'step', kind)
        row['match'] = False
        return row, dict(fail=True, kind=kind, queue=q)
    info = ex['info']
    if frame == 0:
        got = harness.call(request_for(MODE_PASS, fr['start'], info['n_queue']))
        if cat == 'complete':
            bad = compare(got, ex['exp_n'])
            row['checks']['pass'] = dict(ok=not bad, mismatch=bad[:4])
            row['match'] = not bad
            chain = dict(queue=info['n_queue'], exp=ex['exp_n'])
        else:
            row['checks']['pass'] = check_expected_failure(got, 'pass', kind)
            row['match'] = False
            chain = dict(fail=True, kind=kind, queue=info['n_queue'])
        return row, chain
    queue = info['h_queue'] + info['n_queue']
    got = harness.call(request_for(MODE_STEP, fr['start'], queue))
    ngot = harness.call(request_for(MODE_PASS, fr['n']['start'], info['n_queue']))
    if cat == 'complete':
        bad = compare(got, ex['exp_step'])
        nbad = compare(ngot, ex['exp_n'])
        row['checks']['step'] = dict(ok=not bad, mismatch=bad[:4])
        row['checks']['pass'] = dict(ok=not nbad, mismatch=nbad[:4])
        row['match'] = not bad and not nbad
        row['counts'] = dict(irqs=len(ex['exp_step']['irqs']), irq_ports=len(ex['exp_step']['irq_ports']), head_ports=len(ex['exp_step']['head_ports']),
                             node_ports=len(ex['exp_step']['node_ports']), card=sum(1 for w in ex['exp_step']['waits'] if w[1] == D.CARD_BIOS))
        chain = dict(queue=queue, exp=ex['exp_step'])
    else:
        row['checks']['step'] = check_expected_failure(got, 'step', kind)
        row['match'] = False
        chain = dict(fail=True, kind=kind, queue=queue)
    return row, chain


# ----------------------------------------------------------------------------------
# Worker
# ----------------------------------------------------------------------------------
def harness_for_worker():
    h = CTX.get('harness')
    if h is None:
        h = Harness(CTX['exe'], CTX['resources'], OUT / ('harness.%d.stderr' % os.getpid()))
        CTX['harness'] = h
    return h


def chain_state(got, status):
    return dict(ram=got['ram'], regs=got['regs'], pc=got['pc'], bank=(got['bank_base'],), pvc=got['pvc'], palette=got['palette'], status=status)


def full_chain_step(harness, fr, c, fc):
    """Pure C++ chain: frame 0 pass from the prepared seed state, then step from the previous C++ output with the native queue; full comparison per frame."""
    if not fc['alive'] or c is None:
        fc['alive'] = False
        return
    st = fr['start'] if fr['frame'] == 0 else fc['state']
    fc['frames'] += 1
    got = harness.call(request_for(MODE_PASS if fr['frame'] == 0 else MODE_STEP, st, c['queue']))
    if c.get('fail'):
        r = check_expected_failure(got, 'chain', c['kind'])
        if r['ok']:
            fc['expected_failures'] += 1
        else:
            fc['first_divergence'] = dict(frame=fr['frame'], detail=r)
        fc['alive'] = False
        return
    bad = compare(got, c['exp'])
    if bad:
        fc['first_divergence'] = dict(frame=fr['frame'], mismatch=bad[:4])
        fc['alive'] = False
        return
    fc['matched'] += 1
    fc['state'] = chain_state(got, st['status'])
    fc['digests'].append(state_digest(fc['state']))


def run_chain(harness, seed_start, chain_rows):
    st = dict(seed_start)
    digests = []
    for i, c in enumerate(chain_rows):
        if c is None or c.get('fail'):
            break
        got = harness.call(request_for(MODE_PASS if i == 0 else MODE_STEP, st, c['queue']))
        if not got['ok'] or got['remaining']:
            digests.append('error:' + (got.get('error') or 'queue'))
            break
        st = chain_state(got, st['status'])
        digests.append(state_digest(st))
    return digests


def make_run(case, frames, on_frame):
    FH, R = D.FH, D.R
    sd, snap, meta, rec, carried = FH.prepared(case)
    snapc = {k: v for k, v in carried.items() if k != 'prep_entry_state'}
    snapc['ram'], prep = p1_prep(snapc)
    run = CTX['cls'](R.G['program'], R.G['fixed'], R.G['levels'], snapc, 'continuous', frames, heavy=False, plan=None, sink=None, extend=False,
                     answer=R.DEFAULT_ANSWER, full_dump=False, prep_dump=None, cfg=dict(FH.BASE_CFG), case=case, tbset=None, keep_all=False, do_model=False,
                     z80=CTX.get('z80', 0), video=CTX.get('video', 0))
    run.on_frame = on_frame
    return sd, run, prep


def work(arg):
    case, frames, chain = arg
    t0 = time.time()
    harness = harness_for_worker()
    calls0 = harness.calls
    rows, chain_rows, state0 = [], [], {}
    fchain = dict(state=None, alive=True, matched=0, expected_failures=0, first_divergence=None, frames=0, digests=[])
    holder = {}

    def on_frame(fr):
        run = holder['run']
        if fr['frame'] == 0:
            state0.update(fr['start'])
        try:
            row, c = compare_frame(harness, run, fr)
        except Exception as e:                                  # a verifier failure is recorded, never a match
            import traceback
            row, c = dict(frame=fr['frame'], category='verifier-error', error=repr(e), tb=traceback.format_exc()[-800:], match=False, checks={}), None
        rows.append(row)
        full_chain_step(harness, fr, c, fchain)
        if c is not None:
            c.pop('exp', None)
        chain_rows.append(c)
    sd, run, prep = make_run(case, frames, on_frame)
    holder['run'] = run
    run.run()
    out = dict(case=case, kind=sd['kind'], stop=run.stop, frames_done=run.frames_done, prep=dict(changed_bytes=prep['changed_bytes']), rows=rows,
               irq_total=dict(run.irq_total), palette_reads=dict(run.pal_reads), card=len(run.card_waits))
    if chain:
        d1 = run_chain(harness, state0, chain_rows)
        d2 = run_chain(harness, state0, chain_rows)
        out['chain'] = dict(frames=len(d1), deterministic=d1 == d2, digest=D.sha(json.dumps(d1).encode()), equal_full_chain=d1 == fchain['digests'][:len(d1)])
    fchain.pop('state', None)
    fchain['digest'] = D.sha(json.dumps(fchain.pop('digests')).encode())
    out['full_chain'] = fchain
    out['harness_calls'] = harness.calls - calls0
    out['seconds'] = time.time() - t0
    return out


# ----------------------------------------------------------------------------------
# Negatives (one seed, frame 2) and the native IRQ boundary fixture
# ----------------------------------------------------------------------------------
def negatives(case):
    harness = harness_for_worker()
    keep = {}

    def on_frame(fr):
        if fr['frame'] == 2 and 'fr' not in keep:
            keep['fr'] = fr
            keep['cmp'] = irq_frame(keep['run'], fr)
    sd, run, prep = make_run(case, 3, on_frame)
    keep['run'] = run
    run.run()
    fr = keep['fr']
    cat, ex, kind, irqs = keep['cmp']
    assert cat == 'complete', cat
    queue = ex['info']['h_queue'] + ex['info']['n_queue']
    exp = ex['exp_step']
    tests = {}
    base = harness.call(request_for(MODE_STEP, fr['start'], queue))
    tests['baseline-equal'] = not compare(base, exp)
    tests['baseline-irqs'] = dict(detected=len(exp['irqs']) > 0, irqs=len(exp['irqs']))

    def detected(label, st=None, q=None, **kw):
        got = harness.call(request_for(MODE_STEP, st or fr['start'], queue if q is None else q, **kw))
        bad = compare(got, exp)
        tests[label] = dict(detected=bool(bad), first=bad[0] if bad else None)
        return got
    flipped = dict(fr['start'])
    ram = bytearray(flipped['ram'])
    ram[0x0100] ^= 0x01
    flipped['ram'] = bytes(ram)
    detected('ram-byte-flipped', st=flipped)
    detected('irq-execution-off', irq=False)
    detected('z80-reply-changed', z80=(CTX.get('z80', 0) ^ 0x5a) & 0xff)
    detected('video-status-changed', video=(CTX.get('video', 0) ^ 8) & 0xffff)
    nopal = detected('palette-not-attached', palette=False)
    tests['palette-not-attached']['error'] = nopal.get('error')
    detected('queue-short', q=queue[:-1])
    detected('queue-extra-entry', q=queue + [(0x300000, 1, 0x5a)])
    pal_swap = dict(fr['start'])
    b0, b1, sel = pal_swap['palette']
    pal_swap['palette'] = (b1, b0, sel)
    tests['palette-input-nonzero'] = dict(detected=any(b0), bank0_nonzero=sum(1 for x in b0 if x))
    detected('palette-banks-swapped', st=pal_swap)
    # BYTE 10fd80 bit 7 = 0: the IRQ takes 21e JMP c00438 (BIOS INT1): a checked, preserving error.
    int1 = dict(fr['start'])
    ram = bytearray(int1['ram'])
    ram[0xfd80] &= 0x7f
    int1['ram'] = bytes(ram)
    got = harness.call(request_for(MODE_STEP, int1, queue))
    tests['bios-int1'] = dict(detected=(not got['ok']) and got.get('error') == 'animation irq bios int1 boundary' and bool(got.get('preserved')), error=got.get('error'))
    for label, mutate in (('result-irq-dropped', lambda g: g['irqs'].pop()),
                          ('result-irq-sr', lambda g: g['irqs'].__setitem__(0, tuple(g['irqs'][0][:7]) + (0x2001,))),
                          ('result-irq-port-value', lambda g: g['irq_ports'].__setitem__(0, (g['irq_ports'][0][0], g['irq_ports'][0][1], g['irq_ports'][0][2] ^ 1))),
                          ('result-palette-byte', lambda g: g.update(palette=(bytes([g['palette'][0][0] ^ 1]) + g['palette'][0][1:], g['palette'][1], g['palette'][2]))),
                          ('result-ram', lambda g: g.update(ram=bytes([g['ram'][0] ^ 1]) + g['ram'][1:]))):
        g = dict(base, irqs=list(base['irqs']), irq_ports=list(base['irq_ports']))
        mutate(g)
        tests[label] = dict(detected=bool(compare(g, exp)))
    broken = subprocess.run([str(CTX['exe'])] + [str(p) for p in CTX['resources']], input=struct.pack('>I', 11) + b'bad request', stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    tests['malformed-request-nonzero-exit'] = dict(detected=broken.returncode != 0, returncode=broken.returncode)
    try:
        parse_response(b'\0\0\0\x01' + b'\0' * 20)
        tests['malformed-response-rejected'] = dict(detected=False)
    except ValueError:
        tests['malformed-response-rejected'] = dict(detected=True)
    ok = tests['baseline-equal'] and all(v['detected'] for k, v in tests.items() if k != 'baseline-equal')
    return dict(case=case, frame=2, ok=ok, tests=tests)


# ----------------------------------------------------------------------------------
# Build, aggregate, main
# ----------------------------------------------------------------------------------
def build(jobs):
    compiler = Path(shutil.which('clang++'))
    flags = ['-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(ROOT / 'engine/include')]
    objdir = BUILD / 'obj'
    if objdir.exists():
        shutil.rmtree(objdir)
    objdir.mkdir(parents=True)
    srcs = D.machine_sources()
    log = open(OUT / 'build.stderr', 'wb')
    procs, objs = [], []
    for s in srcs:
        o = objdir / (s.stem + '.o')
        objs.append(o)
        while len([p for p in procs if p.poll() is None]) >= jobs:
            time.sleep(0.05)
        procs.append(subprocess.Popen([str(compiler)] + flags + ['-c', str(s), '-o', str(o)], stdout=subprocess.DEVNULL, stderr=log))
    for p in procs:
        assert p.wait() == 0, 'compile failed (see build.stderr)'
    exe = BUILD / 'frame_irq_acceptance'
    subprocess.run([str(compiler)] + flags + [str(o) for o in objs] + [str(HARNESS), '-o', str(exe)], check=True, stdout=subprocess.DEVNULL, stderr=log)
    log.close()
    return exe, compiler, srcs


def aggregate(results):
    tot = collections.Counter()
    cats = collections.Counter()
    errs = collections.Counter()
    irq = collections.Counter()
    compared = collections.Counter()
    per_seed = []
    for r in results:
        rows = r['rows']
        nat = r['kind'] == 'natural'
        comp = [x for x in rows if x['category'] == 'complete']
        nonc = [x for x in rows if x['category'] != 'complete']
        bad_fail = [x for x in nonc if x['category'] == 'verifier-error' or not all(c.get('ok') for c in x['checks'].values())]   # a verifier exception (empty checks) is an acceptance failure (review 0264 L-2)
        for x in rows:
            cats[x['category']] += 1
            for c in x['checks'].values():
                if c.get('error'):
                    errs['%s|%s' % (x['category'], c['error'])] += 1
            if x.get('match') and nat:
                for k, v in x.get('counts', {}).items():
                    compared[k] += v
        irq.update(r['irq_total'])
        first = next((x for x in comp if not x['match']), None)
        fc = r['full_chain']
        per_seed.append(dict(case=r['case'], kind=r['kind'], native_stop=r['stop'], frames=len(rows), complete=len(comp), matches=sum(1 for x in comp if x['match']),
                             first_mismatch=first, non_completions=[dict(frame=x['frame'], category=x['category'], checks=x['checks']) for x in nonc][:3],
                             irqs=r['irq_total'].get('delivered', 0), full_chain=fc, chain=r.get('chain'), palette_reads=r['palette_reads'],
                             seconds=round(r['seconds'], 1)))
        pre = 'natural_' if nat else 'guard_'
        tot[pre + 'frames'] += len(rows)
        tot[pre + 'complete_frames'] += len(comp)
        tot[pre + 'matches'] += sum(1 for x in comp if x['match'])
        tot[pre + 'mismatches'] += sum(1 for x in comp if not x['match'])
        tot[pre + 'non_completions'] += len(nonc)
        tot[pre + 'expected_failure_bad'] += len(bad_fail)
        tot[pre + 'irqs_delivered'] += r['irq_total'].get('delivered', 0)
        if nat:
            tot['natural_complete_400'] += int(r['stop']['reason'] == 'frame-limit' and r['frames_done'] == 400)
            tot['natural_chain_frames_matched'] += fc['matched']
            tot['natural_chain_expected_failures'] += fc['expected_failures']
            tot['natural_chain_divergent_seeds'] += int(fc['first_divergence'] is not None)
            tot['natural_card_seeds'] += int(r['card'] > 0)
    return dict(totals=dict(tot), categories=dict(cats), cpp_errors_on_non_completions=dict(errs), irq_native=dict(irq), natural_matched_frame_tallies=dict(compared),
                stop_categories=dict(collections.Counter(r['stop']['reason'] for r in results)), per_seed=per_seed)


def main(argv=None):
    global OUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', help='comma list (default: all 142 seeds)')
    ap.add_argument('--frames', type=int, default=400)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--z80', type=lambda x: int(x, 0), default=0, help='declared Z80 reply BYTE 320000 per IRQ (default 0)')
    ap.add_argument('--video', type=lambda x: int(x, 0), default=0, help='declared video status WORD 3c0006 per IRQ (default 0)')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--out', default=str(OUT))
    D.add_seed_option(ap)
    args = ap.parse_args(argv)
    D.apply_seed_option(args)
    assert not sys.flags.optimize
    OUT = Path(args.out).absolute()
    D.OUT = OUT
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob('harness.*.stderr'):
        p.unlink()
    report_path = OUT / 'verification.json'
    if report_path.exists():
        report_path.unlink()
    rebase, routing_info, pins = D.setup_native()
    import verify_animation_machine as common
    program = D.R.G['program']
    rom_sha = D.sha(program)
    assert rom_sha == D.S.ROM_SHA
    resources, resource_refs = common.resource_audit(ROOT, program)
    if args.no_build and (BUILD / 'frame_irq_acceptance').exists():
        exe, compiler, srcs = BUILD / 'frame_irq_acceptance', Path(shutil.which('clang++')), D.machine_sources()
    else:
        exe, compiler, srcs = build(args.workers)
    CTX.update(exe=exe, resources=resources, cls=make_irq_class(), answer=D.R.DEFAULT_ANSWER, z80=args.z80, video=args.video)
    import unicorn
    headers = sorted(set((ROOT / 'engine/include').rglob('*.h')) | set((ROOT / 'engine/src').rglob('*.h')))
    inputs = dict(rom=dict(path='extracted/program/maincpu.decrypted.be.bin', sha256=rom_sha),
                  seed_observation=dict(path=str(D.S.SEED_OBS.relative_to(ROOT)), sha256=D.file_sha(D.S.SEED_OBS)), program_rom_resources=resource_refs,
                  engine_sources={str(p.relative_to(ROOT)): D.file_sha(p) for p in srcs}, engine_headers={str(p.relative_to(ROOT)): D.file_sha(p) for p in headers},
                  harness={str(HARNESS.relative_to(ROOT)): D.file_sha(HARNESS)}, harness_binary_sha256=D.file_sha(exe),
                  tools={str(p.relative_to(ROOT)): D.file_sha(p) for p in (TOOLS / 'verify_animation_machine_frame_irq.py', TOOLS / 'verify_animation_machine_frame_driver.py',
                                                                           TOOLS / 'observe_animation_machine_frame_head.py')},
                  unicorn=unicorn.__version__, compiler=subprocess.run([str(compiler), '--version'], stdout=subprocess.PIPE, text=True).stdout.splitlines()[0],
                  python=sys.version.split()[0], routing=routing_info)
    cases = sorted(D.S.SEEDS) if not args.cases else [int(x) for x in args.cases.split(',')]
    naturals = [c for c in cases if D.S.SEEDS[c]['kind'] == 'natural']
    chain_cases = set(naturals[:CHAIN_SEEDS])
    ctx = multiprocessing.get_context('fork')
    results = []
    with ctx.Pool(args.workers) as pool:
        neg_async = pool.apply_async(negatives, (naturals[0],)) if naturals and args.frames >= 3 else None
        jobs = sorted(((c, args.frames, c in chain_cases) for c in cases), key=lambda j: (D.S.SEEDS[j[0]]['kind'] != 'natural', j[0]))
        for r in pool.imap_unordered(work, jobs, chunksize=1):
            results.append(r)
            nonmatch = sum(1 for x in r['rows'] if x['category'] == 'complete' and not x['match'])
            print('[%6.0fs] case %3d %-13s frames %3d irqs %5d complete-mismatch %d stop %s' % (time.time() - t0, r['case'], r['kind'], len(r['rows']),
                  r['irq_total'].get('delivered', 0), nonmatch, r['stop']['reason']), file=sys.stderr, flush=True)
        neg = neg_async.get() if neg_async else None
    results.sort(key=lambda r: r['case'])
    agg = aggregate(results)
    chains = [r['chain'] for r in results if r.get('chain')]
    determinism = dict(seeds=sorted(chain_cases), all_deterministic=all(c['deterministic'] and c['equal_full_chain'] for c in chains), chains=chains)
    full = args.cases is None and args.frames == 400
    t = agg['totals']
    expected = dict(natural_seeds=len(naturals), natural_complete_400=t.get('natural_complete_400'), p1_irqs=t.get('natural_irqs_delivered', 0) + t.get('guard_irqs_delivered', 0))
    acceptance = dict(all_complete_match=t.get('natural_mismatches', 0) == 0 and t.get('guard_mismatches', 0) == 0,
                      non_completions_checked=t.get('natural_expected_failure_bad', 0) == 0 and t.get('guard_expected_failure_bad', 0) == 0,
                      chain_no_divergence=t.get('natural_chain_divergent_seeds', 0) == 0, deterministic=determinism['all_deterministic'],
                      negatives_ok=bool(neg and neg['ok']), expected_from_scope_probe=EXPECTED if full else None,
                      equal_scope_probe=(expected == EXPECTED) if full else None)
    report = dict(tool='tools/verify_animation_machine_frame_irq.py', full_run=full, cases=len(cases), frames_limit=args.frames, z80_reply=args.z80,
                  video_status=args.video, declared_platform_rebase=rebase, observer_pins=pins, inputs=inputs, negative_checks=neg, determinism=determinism,
                  acceptance=acceptance, elapsed_seconds=round(time.time() - t0, 1), **agg, protocol=__doc__.strip().splitlines(),
                  limits=['IRQ delivery points are the declared E1 A points (wait blocks), not a vblank time axis.',
                          'BIOS c0044a is a declared resume (no BIOS ROM); RTE is emulated natively (Unicorn 2.1.4).',
                          'Z80 reply and video status are declared constants per IRQ; palette RAM is a two-bank model without display/CPU bank distinction.',
                          'Controller c52a is not executed (declared skip, D1).'])
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + '\n')
    print(json.dumps({k: report[k] for k in ('full_run', 'totals', 'categories', 'stop_categories', 'acceptance', 'elapsed_seconds')}, indent=1, sort_keys=True,
                     default=str))
    print(json.dumps(dict(negative_ok=neg['ok'] if neg else None, report_sha256=D.file_sha(report_path)), sort_keys=True))


if __name__ == '__main__':
    main()
