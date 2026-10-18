"""Unit IO native observer: input and stage-progress observation of the original ROM (native Unicorn M68000), original ROM never modified.

Scope and decisions: docs/analysis/input-stage-progress-observation-scope.md (main decisions at its top are binding).  Protocol, configurations, results and unconfirmed
items: docs/analysis/animation-machine-io-observation.md.  Declared input scripts and host writes: docs/analysis/data/io-input-scripts.json.

This is an observation, not natural game execution: no BIOS execution, no natural IRQ timing and no natural scheduler is claimed.  Every host write, device value, IRQ
delivery, BIOS return and re-entry is a DECLARED step recorded in the observation (observation.json "declared").

Two seed families share one frame protocol:
  S  the 137 natural stage_entry_body seeds (case 141 stops at frame 0) + game-mode declaration (D9 (ii)) + seed preparation P1 + a declared input script
     (configurations P0 control, P1 main, P1b second player on the 14 class representatives);
  B  BIOS-less boot snapshots: the cartridge USER entry 852 is executed natively from 0 RAM with declared device answers and BIOS returns until the scheduler dispatcher
     2ab8, then the declared frame-0 shift (PC := 2ac2, A6 := 1008e4, A7 := 1ff000, LONG 104ca4 := 1ff000) hands over to the D1 frames
     (boot-demo-0, boot-title-start, boot-title-idle).
Frame protocol (scope 5.1): frame 0 = N0; frame k >= 1: declared host writes -> H (frame head up to the controller transfer) -> C (the controller is EXECUTED up to the
dispatcher return 2ac2) -> N (F2 node pass).  Waits in H, C and N (ef2, 16bd0, cda4, 3aea, 47af0, 478de) are released by one delivered IRQ (F6-D convention: declared
resume of the BIOS SYSTEM_IO call, RTE emulated, registers checked, 16 per segment); the card request c00468 is the declared card resume.  The external reads of H
come from the per-frame queue built from the declared input script; every read in N, C or IRQ outside the declared device reads is a guard.

The native machinery is imported in-process from the existing D1 / controller / IRQ tools and is never edited.  The SHA256 of every imported tool, the routing file and the
ROM are asserted.  observation.json carries the compared fields only (compared_sha256); platform.json carries Unicorn / library / OS data and is excluded from every
comparison.
"""
import argparse
import collections
import copy
import ctypes
import gzip
import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import platform as platform_module
import struct
import sys
import time

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

OUT_DEFAULT = ROOT / 'artifacts/animation_machine_io_native'
SCRIPTS_FILE = ROOT / 'docs/analysis/data/io-input-scripts.json'
SCOPE_DOC = ROOT / 'docs/analysis/input-stage-progress-observation-scope.md'
ROM_PATH = ROOT / 'extracted/program/maincpu.decrypted.be.bin'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
ROUTING_FILE = ROOT / 'engine/src/animation_machine.cpp'
ROUTING_SHA = '8ce8eb93c21465dd5e9355d4518ab1ca853df4549305fec98c7854caa1a82db6'
SEED_DIR_DEFAULT = ROOT / 'artifacts/stage_entry_body'
HISTORIC_SEED_SHA = '1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207'
TOOL_PINS = collections.OrderedDict([
    ('observe_animation_machine_frame_head.py', '1b6cd5bddbd55ce685ce96c888b0facc74070c09ab42cdfff1e7ebe644c4df59'),
    ('observe_animation_machine_scheduler.py', '62bb23ff6d2f61a5e47af71b8e1308d50c99b85d95f3278b8d825b7ee327c01c'),
    ('observe_animation_machine_scheduler_rng.py', '659f8636fa82311b757bbcd72190b8874906ad6dbe0baddf638eb5a641e7848b'),
    ('observe_animation_machine_pvc_banks.py', '86ebf962e3b83eef6882c1f96845c117edfa735c3137960b1cbda6623768d3a0'),
    ('address_map.py', '5e11a86662c4dd84f2e75606161ba3196f8ff527e62b2913515127c1abfd234e'),
    ('measure_code_coverage.py', '637d2cc8a2520a383865057e4e3f2f6f8c02c4323abc449be2a67ced34a459a3'),
    ('verify_animation_machine_frame_driver.py', '55bdc6cee56cbc00d17ff18ee8df8491d6cb7aa6f672bea006ae63cf8f5c7760'),
    ('verify_animation_machine_frame_controller.py', '45d163c4f6dc747a1d3d77fb35daa25ec6cb3e602489870d32b665454d2b9fe2'),
    ('verify_animation_machine_frame_irq.py', '4f327616df45a5dc0203c7acd3c74d3e05cc06d18283221650dfdc88f903abef'),
])
FORMAT = 'ms5-io-observation'
VERSION = 1
KEYS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')
SPD = 0x1ff000
PAGE = 256
RAM_PAGES, PVC_PAGES, PAL_PAGES = 256, 32, 32
NPAGES = RAM_PAGES + PVC_PAGES + 2 * PAL_PAGES
HDR = struct.Struct('>16IIIHHBB')
PACK_MAGIC = b'MS5IOST1'
RUN_FORMAT = 'ms5-io-run'
INPUT_PORTS = (0x300000, 0x340000, 0x380000)
RASTER = 0x3c0006
EXPAND_FRAMES = 2048
FIELDS = (('stagecb', 0x100b30, 4), ('p1cb', 0x100cb8, 4), ('p2cb', 0x100da8, 4), ('ctrlcb', 0x1008e4, 4), ('cam_d3a2', 0x10d3a2, 2), ('cam_d3bc', 0x10d3bc, 4),
          ('cam_d3c0', 0x10d3c0, 4), ('mission', 0x10d680, 1), ('area', 0x10d681, 1), ('aid', 0x10d686, 2), ('d684', 0x10d684, 1), ('mod1', 0x10fdb6, 1),
          ('mod2', 0x10fdb7, 1), ('inmode', 0x104cd4, 1), ('replay_cur', 0x104cce, 2), ('replay_ptr', 0x104cc4, 4), ('fdae', 0x10fdae, 1), ('fdaf', 0x10fdaf, 1),
          ('f004', 0x10f004, 1), ('f006', 0x10f006, 1), ('f007', 0x10f007, 1), ('mode12', 0x100012, 1), ('fd82', 0x10fd82, 1))
INBLOCK = (0x104ca8, 22)          # 104ca8..104cbd: gameplay blocks, system, P1 / P2 device blocks
IDLE_CB = 0x270e
BOOT_DEVICE_ANSWERS = {(0x320000, 1): 1, (0x3c0002, 2): 0}
BOOT_RTS_CALLS = {0xc0045c: 'calendar call (1302)', 0xc004c2: 'FIX_CLEAR call (1100)'}
BOOT_READS_ALLOWED = ('380000/1@1322', '3c0002/2@10c8', '320000/1@10ea', '3c0006/2@9a4', '300000/1@2634')
BOOT_LIMIT = 20000000
CTX = {}


# ----------------------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------------------
def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def canon_sha(obj):
    return sha(canon(obj).encode())


def gz(data):
    return gzip.compress(data, compresslevel=6, mtime=0)


def hx(v):
    return '%x' % v


def be(ram, a, n):
    o = a & 0xffff
    return int.from_bytes(bytes(ram[o:o + n]), 'big')


def state_pages(st):
    """-> 90,112 byte image: RAM 64 KiB + PVC page 8 KiB + palette bank 0 + bank 1 (8 KiB each)."""
    pal = st['palette']
    assert len(st['ram']) == 65536 and len(st['pvc']) == 8192 and len(pal[0]) == 8192 and len(pal[1]) == 8192
    return bytes(st['ram']) + bytes(st['pvc']) + bytes(pal[0]) + bytes(pal[1])


def state_header(st):
    return HDR.pack(*([st['regs'][k] & 0xffffffff for k in KEYS] + [st['pc'] & 0xffffffff, st['bank'][0], st['bank'][1] & 0xffff, st['bank'][2] & 0xffff,
                                                                  st['status'] & 0xff, st['palette'][2] & 0xff]))


def state_digest(st):
    h = hashlib.sha256(b'MS5-IO-STATE-1')
    h.update(state_header(st))
    h.update(state_pages(st))
    return h.hexdigest()


def state_from_image(header, image):
    v = HDR.unpack(header)
    regs = dict(zip(KEYS, v[:16]))
    return dict(regs=regs, pc=v[16], bank=(v[17], v[18], v[19]), status=v[20], ram=image[:65536], pvc=image[65536:73728],
                palette=(image[73728:81920], image[81920:90112], v[21]))


class StatePack(object):
    """Page-delta pack of selected frame-start states (all pages of a state: 352 x 256 bytes).  Records are sequential; a delta is relative to the previous record."""
    def __init__(self):
        self.buf = io.BytesIO()
        self.buf.write(PACK_MAGIC)
        self.prev = None
        self.frames = []

    def add(self, frame, st):
        header = state_header(st)
        image = state_pages(st)
        if self.prev is None:
            ids = list(range(NPAGES))
            kind = 0
        else:
            kind = 1
            ids = [i for i in range(NPAGES) if image[i * PAGE:(i + 1) * PAGE] != self.prev[i * PAGE:(i + 1) * PAGE]]
        self.buf.write(struct.pack('>IBH', frame, kind, len(ids)))
        self.buf.write(header)
        for i in ids:
            self.buf.write(struct.pack('>H', i))
            self.buf.write(image[i * PAGE:(i + 1) * PAGE])
        self.prev = image
        self.frames.append(frame)

    def data(self):
        return self.buf.getvalue()


def read_pack(data):
    """Pack bytes -> list of (frame, state dict, digest); raises ValueError on a malformed pack."""
    if data[:8] != PACK_MAGIC:
        raise ValueError('bad state pack magic')
    at = 8
    image = None
    out = []
    while at < len(data):
        frame, kind, n = struct.unpack_from('>IBH', data, at)
        at += 7
        header = data[at:at + HDR.size]
        at += HDR.size
        if kind == 0:
            image = bytearray(NPAGES * PAGE)
        elif image is None:
            raise ValueError('delta without base')
        for _ in range(n):
            pid = struct.unpack_from('>H', data, at)[0]
            at += 2
            image[pid * PAGE:(pid + 1) * PAGE] = data[at:at + PAGE]
            at += PAGE
        st = state_from_image(header, bytes(image))
        h = hashlib.sha256(b'MS5-IO-STATE-1')
        h.update(header)
        h.update(bytes(image))
        out.append((frame, st, h.hexdigest()))
    return out


# ----------------------------------------------------------------------------------
# Input scripts (docs/analysis/data/io-input-scripts.json)
# ----------------------------------------------------------------------------------
def load_scripts():
    data = json.loads(SCRIPTS_FILE.read_text())
    assert data['format'] == 'ms5-io-input-script' and data['version'] == 1
    return data


def expand_script(sdef, nframes=EXPAND_FRAMES):
    """-> list over frames of {port: value}.  BYTE ports 380000 / 300000 / 340000, WORD 3c0006."""
    defaults = dict((int(k, 16), int(v, 16)) for k, v in sdef['defaults'].items())
    table = []
    for f in range(nframes):
        vals = dict(defaults)
        for seg in sdef['segments']:
            if f < seg['from'] or (seg['to'] is not None and f > seg['to']):
                continue
            if 'every' in seg:
                lo, hi = seg['phase']
                if not lo <= f % seg['every'] <= hi:
                    continue
            port = int(seg['port'], 16)
            mask = 0xffff if port == RASTER else 0xff
            if 'value' in seg:
                vals[port] = int(seg['value'], 16) & mask
            if 'clear' in seg:
                vals[port] = vals[port] & ~int(seg['clear'], 16) & mask
            if 'set' in seg:
                vals[port] = (vals[port] | int(seg['set'], 16)) & mask
        table.append(vals)
    return table


def expanded_sha(table):
    h = hashlib.sha256(b'MS5-IO-EXPANDED-1')
    for vals in table:
        h.update(struct.pack('>BBBH', vals[0x380000], vals[0x300000], vals[0x340000], vals[RASTER]))
    return h.hexdigest()


def host_writes_of(cfg, scripts):
    """Config -> (list of (lo, hi, address, size, value, mode) as FH cfg['writes'], list of declaration rows, crosscheck frame)."""
    writes, rows, cross = [], [], {}
    for name in cfg['host_write_sets']:
        for w in scripts['host_write_sets'][name]:
            a, v = int(w['address'], 16), int(w['value'], 16)
            writes.append((w['frames'][0], w['frames'][1], a, w['size'], v, w['mode']))
            rows.append(dict(set=name, frames=w['frames'], address=a, size=w['size'], value=v, mode=w['mode'], why=w['why'], evidence=w['evidence']))
            if w.get('crosscheck'):
                cross[w['frames'][0]] = w['crosscheck']
    return writes, rows, cross


# ----------------------------------------------------------------------------------
# Native machinery
# ----------------------------------------------------------------------------------
def rom_guard():
    st = ROM_PATH.stat()
    return dict(sha256=file_sha(ROM_PATH), size=st.st_size, mtime_ns=st.st_mtime_ns)


def native_setup(seed_dir):
    """Import the existing tools in-process and assert every SHA pin.  Returns the context dict (also stored in CTX)."""
    for name, expect in TOOL_PINS.items():
        got = file_sha(TOOLS / name)
        if got != expect:
            raise SystemExit('imported tool %s changed: %s != pinned %s' % (name, got, expect))
    if file_sha(ROUTING_FILE) != ROUTING_SHA:
        raise SystemExit('routing file %s changed: %s != pinned %s' % (ROUTING_FILE, file_sha(ROUTING_FILE), ROUTING_SHA))
    rg = rom_guard()
    if rg['sha256'] != ROM_SHA:
        raise SystemExit('ROM SHA256 mismatch %s' % rg['sha256'])
    import verify_animation_machine_frame_driver as D
    import verify_animation_machine_frame_controller as VC
    import verify_animation_machine_frame_irq as VI
    import measure_code_coverage as MC

    class Opt(object):
        pass
    opt = Opt()
    opt.seed_dir = str(seed_dir)
    D.apply_seed_option(opt)
    rebase, routing_info, pins = D.setup_native()
    if rebase['seed_sha256'] != HISTORIC_SEED_SHA:
        raise SystemExit('unexpected seed observation %s (this observer pins the historic stage_entry_body %s)' % (rebase['seed_sha256'], HISTORIC_SEED_SHA))
    CTX.update(D=D, VC=VC, VI=VI, MC=MC, FH=D.FH, S=D.S, R=D.R, rebase=rebase, rom=rg, routing_info=routing_info)
    # routing at the observed commit: HEAD animation_machine.cpp (scope section 3 convention; single-PC executors cover their intra-function closure [I])
    text = ROUTING_FILE.read_text()
    atoms, _ = MC.parse_routed_atoms(text)
    routed = bytearray(0x100000)
    for a in atoms:
        for p in range(a['start'], min(a['end'], 0x100000)):
            routed[p] = 1
    disc = MC.Discovery(bytes(D.R.G['program'][:0x100000]))
    routed2 = bytearray(routed)

    def intra(root, limit=4000):
        seen, todo, out = set(), [root], []
        while todo and len(seen) < limit:
            pc = todo.pop()
            if pc in seen or not 0 <= pc < 0x100000:
                continue
            d = disc.decode(pc)
            if d is None:
                continue
            seen.add(pc)
            out.append((pc, d[0]))
            fl = disc.classify(pc, d[0])
            for t, kind in fl.targets:
                if kind == 'branch' and not (disc.word(pc) & 0xffc0) == 0x4ec0:
                    todo.append(t)
            if fl.fall:
                todo.append(pc + d[0])
        return out
    for a in atoms:
        if a['kind'] == 'single':
            for pc, n in intra(a['start']):
                for p in range(pc, pc + n):
                    routed2[p] = 1
    CTX.update(atoms=len(atoms), routed2=routed2, disc=disc, unr_cache={})
    CTX['routing'] = dict(file=str(ROUTING_FILE.relative_to(ROOT)), sha256=ROUTING_SHA, atoms=len(atoms),
                          single_atoms=sum(1 for a in atoms if a['kind'] == 'single'), range_atoms=sum(1 for a in atoms if a['kind'] == 'range'),
                          routed_bytes=sum(routed2), method='MC.parse_routed_atoms; single-PC executors cover their intra-function branch closure [I]')
    return CTX


def tb_first_unrouted(addr, size):
    """First instruction start inside the TB [addr, addr+size) outside the routing bitmap (fixed ROM only), else None (IO-1 definition)."""
    cache = CTX['unr_cache']
    k = (addr, size)
    if k in cache:
        return cache[k]
    res = None
    if addr < 0x100000:
        routed2, disc = CTX['routed2'], CTX['disc']
        pc = addr
        while pc < addr + size:
            if not routed2[pc]:
                res = pc
                break
            d = disc.decode(pc)
            if d is None:
                break
            pc += d[0]
    cache[k] = res
    return res


def make_io_class():
    FH, S, R, D, VC, VI = CTX['FH'], CTX['S'], CTX['R'], CTX['D'], CTX['VC'], CTX['VI']
    import unicorn
    UC_REG = S.UC_REG
    CR = VC.make_controller_class()
    IR = VI.make_irq_class()
    IRQ_WAIT_PCS = VI.IRQ_WAIT_PCS
    M32 = 0xffffffff

    class IoRun(CR):
        """Controller-Execute + IRQ native run with scripted external reads, per-frame records, guards and optional state packs (nothing imported is edited)."""
        def __init__(self, *a, **kw):
            self.io = kw.pop('io')
            self.irq_on = True
            self.z80 = 0
            self.video = 0
            self._q = {}
            self.fx = None
            self.records = []
            self.pack = None
            self.keep_all = False
            CR.__init__(self, *a, **kw)
            self.irq_total = collections.Counter()
            self.frame_irqs = []
            self.irq_fail = None
            self.pal_reads = collections.Counter()
            self.h_p0 = self.n_p0 = 0
            self.keep_all_states = bool(self.io.get('keep_all_states'))
            self.prev_fields = {}
            self.prev_start = None
            self.pending_start = None
            self.written = set()
            self.unr_total = collections.Counter()
            self.unr_first_seen = {}
            self.unr_first = None
            self.unr_frames = 0
            self.banked = set()
            self.ram_exec = 0
            self.summary = dict(ctrl_exits=collections.Counter(), p1cbs=collections.Counter(), p2cbs=collections.Counter(), stagecbs=collections.Counter(),
                                modes=collections.Counter(), qviol=0, qok=0, first_qviol=None, p1_first=None, p1_frames=0, p2_first=None, p2_frames=0,
                                cam0=None, cam1=None, areas=set(), missions=set(), mod1=set(), irq_phase=collections.Counter(), waits=collections.Counter(),
                                ctrl_paths=collections.Counter(), enter_cb=collections.Counter(), cbset=collections.Counter())
            self.xchk = []
            self.crossframes = self.io.get('crosscheck', {})
            self.guard_rec = None
            self.prev_ctrl_exit = None

        # ---- scripted external reads (no module monkeypatch: FH.run_head assigns self.queue, the setter substitutes the scripted queue)
        @property
        def queue(self):
            return self._q

        @queue.setter
        def queue(self, value):
            self._q = self.scripted_queue(getattr(self, 'frame', 0)) if value else {}

        def scripted_queue(self, frame):
            table = self.io['table']
            vals = table[frame] if frame < len(table) else table[-1]
            lim = self.io.get('queue_limit', {})
            q = {}
            for port in (RASTER,) + INPUT_PORTS:
                n = lim.get(port, FH.QLEN)
                q[port] = [vals[port]] * n
            return q

        # ---- machine
        def build(self, snap):
            mach = CR.build(self, snap)
            c = mach.cpu
            for base in (0x320000, 0x3a0000):
                c.mem_map(base, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
            self.pal_view = (ctypes.c_ubyte * VI.PAL_SIZE)()
            c._keep.append(self.pal_view)
            for i in range(0x200):
                c.mem_map_ptr(VI.PAL_LO + i * VI.PAL_SIZE, VI.PAL_SIZE, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE, ctypes.addressof(self.pal_view))
            self.pal_banks = [bytearray(VI.PAL_SIZE), bytearray(VI.PAL_SIZE)]
            self.pal_sel = 0
            pal = snap.get('palette')
            if pal is not None:                                  # fresh-CPU (split) rebuild: restore the palette banks of the captured state
                self.pal_banks = [bytearray(pal[0]), bytearray(pal[1])]
                self.pal_sel = pal[2]
                ctypes.memmove(self.pal_view, bytes(self.pal_banks[self.pal_sel]), VI.PAL_SIZE)
            c.hook_add(FH.UC_HOOK_MEM_WRITE, self.h_palsel, begin=0x3a000f, end=0x3a001f)
            c.hook_add(FH.UC_HOOK_MEM_READ, self.h_irqread, begin=0x320000, end=0x320000)
            c.hook_add(FH.UC_HOOK_MEM_READ, self.h_irqread, begin=0x3c0006, end=0x3c0007)
            c.hook_add(FH.UC_HOOK_MEM_READ, self.h_palread, begin=VI.PAL_LO, end=0x7fffff)
            c.hook_add(FH.UC_HOOK_MEM_READ, self.h_inguard, begin=0x300000, end=0x3c0007)
            c.hook_add(unicorn.UC_HOOK_BLOCK, self.h_tb, begin=0, end=0xffffff)
            orig = mach.state

            def state_with_palette():
                st = orig()
                st['palette'] = self.palette_state()
                return st
            mach.state = state_with_palette
            return mach

        h_palsel = IR.h_palsel
        h_irqread = IR.h_irqread
        h_palread = IR.h_palread
        palette_state = IR.palette_state

        def h_inguard(self, uc, access, address, size, value, user):
            """Direct input / raster port read inside N or C (the logic must read the RAM image made by the H sampler): checked stop."""
            if self.phase not in ('N', 'C') or self.stop is not None or self.m.invalid is not None:
                return
            if (address in INPUT_PORTS and size == 1) or (address == RASTER and size == 2):
                self.request_stop('undeclared-device-read', address=address, size=size, phase=self.phase, pc=uc.reg_read(UC_REG['pc']))

        def h_tb(self, uc, addr, size, user):
            fx = self.fx
            if fx is None:
                return
            fx['tb'][(self.phase, addr, size)] += 1
            if addr < 0x100000:
                u = tb_first_unrouted(addr, size)
                if u is not None:
                    n = fx['unr'].get(u)
                    fx['unr'][u] = (n[0] + 1, n[1]) if n else (1, self.phase)
                    if fx['first_unr'] is None:
                        fx['first_unr'] = (self.phase, u)
            elif 0x200000 <= addr < 0x2fe000:
                fx['banked'].add((self.phase, addr))
            elif 0x100000 <= addr < 0x200000:
                fx['ramexec'] += 1

        def capture(self):
            return CR.capture(self)                              # m.state() already carries the palette banks

        def release_wait(self, w):
            ph = self.phase
            ch = IR.release_wait(self, w)
            if ph == 'C' and ch and ch[0][0] == 'irq':
                return [(ch[0][1], 0, 0)]                        # keep the C-segment wait tuple arithmetic valid; the IRQ record carries the facts
            return ch

        def deliver(self, ret_pc):
            ph = self.phase
            pre = self.capture()
            rec = IR.deliver(self, ret_pc)
            post = self.capture()
            rec['ph'] = ph
            rec['pre'] = state_digest(pre)
            rec['post'] = state_digest(post)
            return rec

        # ---- per frame
        def new_fx(self, frame):
            return dict(frame=frame, tb=collections.Counter(), unr={}, first_unr=None, banked=set(), ramexec=0)

        def run_head(self, frame):
            self.frame_irqs = []
            self.irq_fail = None
            self.fx = self.new_fx(frame)
            self.fx['hp0'] = len(self.m.ports)
            self.h_p0 = self.fx['hp0']
            if frame in self.crossframes:
                self.xchk.append(self.crosscheck(frame))
            out = CR.run_head(self, frame)
            if self.mode == 'split' and out[0]['reason'] == 'controller':
                st = self.m.state()                              # the executed controller state (a7 = SPd - 4 written by the controller phase), for the fresh-CPU rebuild
                out = (out[0], out[1], st) + tuple(out[3:])
            return out

        def run_controller(self):
            self.fx['cp0'] = len(self.m.ports)
            return CR.run_controller(self)

        def run_pass(self):
            if self.frame == 0:
                self.frame_irqs = []
                self.irq_fail = None
                self.fx = self.new_fx(0)
            self.fx['np0'] = len(self.m.ports)
            self.n_p0 = self.fx['np0']
            return CR.run_pass(self)

        def crosscheck(self, frame):
            """Declared PLAYER_START effect versus the original a74 run natively on the pre-state (BYTE 10fdb4 := 1, to its RTS at b0a, registers discarded)."""
            cfgw = [w for w in self.cfg.get('writes', ()) if w[0] <= frame <= w[1] and not (w[2] == 0x10f006)]
            base = bytearray(self.m.ram())
            for lo, hi, a, s, v, mode in cfgw:
                base[a & 0xffff:(a & 0xffff) + s] = v.to_bytes(s, 'big')
            rows = []
            for name, edits in (('seed-pre-state', {}), ('bios-enabled(f004=3,f007=ff,fd82=1)', {0x10f004: 3, 0x10f007: 0xff, 0x10fd82: 1})):
                ram = bytearray(base)
                ram[0xfdb4] = 1
                for a, v in edits.items():
                    ram[a & 0xffff] = v
                regs = self.m.regs()
                ps = dict(ram=bytes(ram), regs=dict(regs), pc=0xa74, bank=(self.m.bank, self.m.ff8, self.m.ff9))
                mach = S.Machine(R.G['program'], R.G['fixed'], ps)
                mach.install_basic_hooks()
                mach.cpu.emu_start(0xa74, 0xb0a, count=2000)
                ok = mach.pc() == 0xb0a and mach.odd is None and mach.invalid is None and mach.fetch_unmapped is None
                new = mach.ram()
                a7 = regs['a7'] & 0xffff
                diff = [(0x100000 + i, ram[i], new[i]) for i in range(65536) if ram[i] != new[i] and not (a7 - 32 <= i < a7)]
                f006_before = ram[0xf006]
                f006_after = new[0xf006]
                rows.append(dict(variant=name, reached_rts=ok, f006_before=f006_before, f006_after=f006_after, ram_diff=[[a, b, c] for a, b, c in diff],
                                 matches_declared_p1=f006_after == (f006_before | 1)))
            return dict(frame=frame, check='a74', pre_state=state_digest(self.capture()), variants=rows)

        def on_frame(self, fr):
            rec = self.build_record(fr)
            self.records.append(rec)

        # ---- the frame record
        def seg_ports(self, ports, base, irqs, phase):
            keep, cut = [], 0
            ranges = [(q['p0'] - base, q['p1'] - base) for q in irqs if q['ph'] == phase]
            for j, p in enumerate(ports):
                if any(lo <= j < hi for lo, hi in ranges):
                    continue
                keep.append(p)
            return keep

        def build_record(self, fr):
            fx = self.fx
            frame = fr['frame']
            h, c, n = fr.get('h'), fr.get('c'), fr.get('n')
            irqs = list(self.frame_irqs)
            st0 = fr['start']
            rec = dict(f=frame, start=state_digest(st0), mode=st0['ram'][0x4cd4])
            hw = h['rec']['host_writes'] if h else []
            rec['hw'] = [[a, s, o, nv, md] for a, s, o, nv, md in hw]
            if h:
                hp = self.seg_ports(h['ports'], fx['hp0'], irqs, 'H')
                rec['H'] = dict(stop=h['reason']['reason'], end=state_digest(h['end']), ports=[len(hp), S.ports_digest(hp)], head_cb=h['rec']['head_cb'],
                                ctrl_cb=h['rec']['ctrl_cb'], waits=[[w['pc'], w['kind']] for w in h['rec']['waits'] if w['pc'] not in IRQ_WAIT_PCS],
                                status=len(h['status_reads']))
            if c:
                cp = self.seg_ports(c['ports'], fx['cp0'], irqs, 'C')
                cq, cstat, cother = D.n_queue(c['dev'])
                rec['C'] = dict(res=c['reason']['reason'], entry=c['entry'], exit=c['exit_cb'], start=state_digest(c['start']), end=state_digest(c['end']),
                                ports=[len(cp), S.ports_digest(cp)], waits=[[w[1], w[2]] for w in c['waits'] if w[1] not in IRQ_WAIT_PCS], status=cstat,
                                path=list(c['path'][:32]))
            else:
                cq, cother = [], []
            if n:
                npts = self.seg_ports(n['ports'], fx['np0'], irqs, 'N')
                nq, nstat, nother = D.n_queue(n['dev'])
                rec['N'] = dict(stop=n['reason']['reason'], start=state_digest(n['start']), end=state_digest(n['end']), ports=[len(npts), S.ports_digest(npts)],
                                cbs=list(n['cbs']), waits=[[w['pc'], w['kind']] for w in n['waits'] if w['pc'] not in IRQ_WAIT_PCS], status=nstat)
            else:
                nq, nother = [], []
            rec['irq'] = [dict(seg=q['ph'], pc=q['pc'], res=q['res'], reads=q['reads'], bios=q['bios'], sr=q['sr'], pre=q['pre'], post=q['post'],
                               ports=[len(q['ports']), S.ports_digest(q['ports'])]) for q in irqs]
            hq = [list(e) for e in h['ext']] if h else []
            queue = hq + [list(e) for e in cq] + [list(e) for e in nq]
            rec['q'] = queue
            rec['qchk'] = self.check_queue(rec['mode'], frame, queue, fx)
            end = (n['end'] if n else (c['end'] if c else (h['end'] if h else st0)))
            rec['fields'] = self.progress_fields(end['ram'])
            guard = self.classify_guard(fr, cother, nother)
            rec['guard'] = guard
            # coverage against the routing at the observed commit
            unr_new = []
            for pc in sorted(fx['unr']):
                cnt, ph = fx['unr'][pc]
                self.unr_total[pc] += cnt
                if pc not in self.unr_first_seen:
                    self.unr_first_seen[pc] = (frame, ph)
                    unr_new.append([pc, cnt, ph])
            rec['unr_new'] = unr_new
            rec['unr_n'] = len(fx['unr'])
            rec['unr_first'] = list(fx['first_unr']) if fx['first_unr'] else None
            if fx['first_unr'] and self.unr_first is None:
                self.unr_first = (frame, fx['first_unr'][0], fx['first_unr'][1])
            if fx['unr']:
                self.unr_frames += 1
            tbk = sorted(fx['tb'].items())
            rec['tb'] = [len(tbk), sha(repr(tbk).encode())[:32]]
            rec['banked'] = len(fx['banked'])
            self.banked |= fx['banked']
            self.ram_exec += fx['ramexec']
            self.account(rec, fr, fx)
            f = self.cur_fields
            last = frame + 1 >= self.limit
            first_unr_frame = bool(fx['unr']) and self.unr_frames == 1
            p1_spawn = f['p1cb'] != IDLE_CB and self.summary['p1_first'] == frame
            ctrl_change = bool(rec.get('C')) and rec['C']['exit'] != self.prev_ctrl_exit
            if rec.get('C'):
                self.prev_ctrl_exit = rec['C']['exit']
            tb_key = frame in (0, 1, 2) or guard is not None or last or first_unr_frame
            state_key = tb_key or p1_spawn or ctrl_change or bool(rec['hw'])
            if tb_key:
                rec['tbs'] = [[ph, a, s, cnt] for (ph, a, s), cnt in tbk]
            self.save_start(fr, rec, state_key, first_unr_frame)
            return rec

        def check_queue(self, mode, frame, queue, fx):
            """Consumption log versus the H2 contract order and the declared script values (frame 0 has no head)."""
            if frame == 0:
                return 'none'
            seq = [e[0] for e in queue]
            pre = [RASTER, RASTER]
            first3 = [0x380000, 0x300000, 0x340000]
            # H2 contract (animation-machine-frame-head-h2-contract.md): mode 0 five input reads, mode >= 2 the first three; mode 1 (replay) the first three
            # (observed; the replay branch 352a itself reads nothing) or, with the recorder 349c, five.
            tails = {0: [first3 + [0x300000, 0x340000]], 1: [first3, first3 + [0x300000, 0x340000]]}.get(mode, [first3])
            ok = False
            for tail in tails:
                if seq[:2] == pre:
                    rest = seq[2:]
                    if rest and len(rest) % len(tail) == 0 and rest == tail * (len(rest) // len(tail)):
                        ok = True
                if not ok and seq and len(seq) % (2 + len(tail)) == 0 and seq == (pre + tail) * (len(seq) // (2 + len(tail))):
                    ok = True                                      # a pause loop that repeats the whole sampler
            if not ok:
                return 'order:mode%d:%s' % (mode, ','.join(hx(a) for a in seq))
            table = self.io['table']
            vals = table[frame] if frame < len(table) else table[-1]
            for a, s, v in queue:
                if v != vals[a]:
                    return 'value:%x=%x!=%x' % (a, v, vals[a])
            return 'ok'

        def progress_fields(self, ram):
            cur = dict((name, be(ram, a, s)) for name, a, s in FIELDS)
            cur['inblk'] = bytes(ram[INBLOCK[0] & 0xffff:(INBLOCK[0] & 0xffff) + INBLOCK[1]]).hex()
            delta = dict((k, v) for k, v in cur.items() if self.prev_fields.get(k) != v)
            self.prev_fields = cur
            self.cur_fields = cur
            return delta

        def classify_guard(self, fr, cother, nother):
            """Frame outcome other than a completed D1/C/N frame -> guard record (kind, segment, detail); None for a completed frame."""
            h, c, n = fr.get('h'), fr.get('c'), fr.get('n')
            seg, reason = None, None
            if h and h['reason']['reason'] != 'controller':
                seg, reason = 'H', h['reason']
            elif c and c['reason']['reason'] != 'returned':
                seg, reason = 'C', c['reason']
            elif n and n['reason']['reason'] != 'frame-head':
                seg, reason = 'N', n['reason']
            elif cother or nother:
                return dict(kind='undeclared-device-read', seg='C' if cother else 'N', reason='device-read', detail=[list(x) for x in (cother or nother)][:4])
            if reason is None:
                return None
            r = reason['reason']
            detail = dict((k, v) for k, v in reason.items() if k != 'reason' and isinstance(v, (int, str, bool)))
            kind = r
            if r == 'stop' and 'detail' in reason:                 # C phase request_stop
                inner = reason['detail']
                kind = inner.get('reason', 'stop')
                detail = dict((k, v) for k, v in inner.items() if k != 'reason' and isinstance(v, (int, str, bool)))
            elif r == 'wait-not-released' and self.irq_fail is not None:
                kind = 'irq:' + self.irq_fail.split(':')[0]
                detail = dict(res=self.irq_fail)
            elif r == 'system-return':
                kind = 'system-return'
            elif r in ('invalid-memory-access', 'invalid'):
                acc, addr = reason.get('access'), reason.get('address')
                if acc in ('write-protected', 'write-unmapped') and addr is not None and (addr < 0x100000 or 0x200000 <= addr < 0x2fe000):
                    kind = 'rom-write'
                elif acc == 'read-unmapped' and addr in INPUT_PORTS:
                    kind = 'undeclared-device-read'
                else:
                    kind = 'unmapped-access'
            elif r in ('odd-pc',):
                kind = 'odd-pc'
            elif r in ('odd-data-access', 'odd'):
                kind = 'odd-data'
            elif r in ('frame-head-aux-callback', 'frame-head-menu-callback'):
                kind = 'head-callback'
            elif r == 'bios-boundary':
                kind = 'bios-boundary'
            return dict(kind=kind, seg=seg, reason=r, detail=detail)

        def account(self, rec, fr, fx):
            s = self.summary
            f = self.cur_fields
            frame = rec['f']
            if rec.get('C'):
                s['ctrl_exits'][rec['C']['exit']] += 1
                s['enter_cb'][rec['C']['entry']] += 1
            s['modes'][rec['mode']] += 1
            if rec['qchk'] == 'ok':
                s['qok'] += 1
            elif rec['qchk'] != 'none':
                s['qviol'] += 1
                if s['first_qviol'] is None:
                    s['first_qviol'] = [frame, rec['qchk']]
            if f['p1cb'] != IDLE_CB:
                s['p1_frames'] += 1
                s['p1cbs'][f['p1cb']] += 1
                if s['p1_first'] is None:
                    s['p1_first'] = frame
            if f['p2cb'] != IDLE_CB:
                s['p2_frames'] += 1
                s['p2cbs'][f['p2cb']] += 1
                if s['p2_first'] is None:
                    s['p2_first'] = frame
            s['stagecbs'][f['stagecb']] += 1
            if s['cam0'] is None:
                s['cam0'] = f['cam_d3bc']
            s['cam1'] = f['cam_d3bc']
            s['areas'].add(f['area'])
            s['missions'].add(f['mission'])
            s['mod1'].add(f['mod1'])
            for q in rec['irq']:
                s['irq_phase'][q['seg'] + ':' + hx(q['pc'])] += 1
            if rec.get('N'):
                for cb in set(rec['N']['cbs']):
                    s['cbset'][cb] += 1
            if rec.get('C') and rec['C']['path']:
                s['ctrl_paths'][tuple(rec['C']['path'][:6])] += 1

        # ---- state packs (frame-start states after the declared host writes; key frames, or every frame)
        def save_start(self, fr, rec, key, first_unr_frame):
            st = fr['start']
            frame = rec['f']
            if self.pack is not None and (key or self.keep_all_states):
                if first_unr_frame and self.prev_start is not None and self.prev_start[0] not in self.written:
                    self.pack.add(self.prev_start[0], self.prev_start[1])          # the frame before the first unrouted frame
                    self.written.add(self.prev_start[0])
                if frame not in self.written:
                    self.pack.add(frame, st)
                    self.written.add(frame)
            self.prev_start = (frame, st)

    return IoRun


# ----------------------------------------------------------------------------------
# B family: BIOS-less boot (scope 3.3), formalised from the IO-1 probe p3_boot.py / p4_bootframes.py
# ----------------------------------------------------------------------------------
BOOT_DECLARATIONS = [
    dict(kind='request', address=0x10fdae, size=1, why='BIOS request byte: 2 = demo (950), 3 = title (964); 0 / 1 return to the BIOS (c00444)', evidence='8a4 branch'),
    dict(kind='device-read', address=0x320000, size=1, value=1, why='Z80 answer for the handshake loop 10d6..10f4 (8000 tries)', evidence='10ea; without it 7cee := ff and 11b4 M1-ROM ERROR screen'),
    dict(kind='device-read', address=0x3c0002, size=2, value=0, why='read-back that must differ from 8b55 (1336 writes 7fff8b55, 10c8 reads again; 8b55 + 74ab = 0 gives 7cef = 0)',
         evidence='1336 / 10c8; without it the SNK cartridge warning loop 1260 [I: original hardware]'),
    dict(kind='device-read', address=0x3c0006, size=2, value=0, why='raster read at 9a4', evidence='9a4'),
    dict(kind='device-read', address=0x300000, size=1, value=0xff, why='released P1 port read at 2634', evidence='2634'),
    dict(kind='device-read', address=0x380000, size=1, value=0xff, why='released system port read at 1322', evidence='1322'),
    dict(kind='bios-call', address=0xc0045c, why='BIOS calendar call (1302): RTS (PC := (A7), A7 += 4), no output', evidence='1302 JSR c0045c'),
    dict(kind='bios-call', address=0xc004c2, why='BIOS FIX_CLEAR call (1100): RTS, no output', evidence='1100 JSR c004c2'),
    dict(kind='write-ignored', address=0x25fff0, size=2, value=0xa, why='bank window WORD write of 874 is ignored and recorded (the window is read-only in this model)', evidence='866..87c'),
    dict(kind='entry', pc=0x852, a7=0x10f300, sr=0x2700, why='cartridge USER entry; A7 = ROM LONG 0 (10f300); SR 2700 assumes the BIOS calls USER with interrupts masked [I]', evidence='ROM vectors'),
    dict(kind='ram', why='all RAM zero except the request byte (BIOS RAM initialisation unknown [U])', evidence='scope 3.3'),
    dict(kind='frame0-shift', pc=0x2ac2, a6=0x1008e4, a7=SPD, a5=0x108000, long104ca4=SPD,
         why='the boot state is at the dispatcher 2ab8 with A6 = 100820, A7 = 10f300: PC := 2ac2, A6 := 1008e4 (N0 visits the remaining nodes), A7 := 1ff000 and LONG 104ca4 := 1ff000 '
             '(the D1 driver fixes SPd = 1ff000; scope decision 1: a declaration, the stack bytes sit at a different place)', evidence='scope 3.3 / decision 1'),
]


def boot_native(fdae):
    """BIOS-less boot to the first fetch of 2ab8, then the declared frame-0 shift.  -> (snapshot dict, boot record)."""
    S, R = CTX['S'], CTX['R']
    import unicorn
    from unicorn import UC_HOOK_CODE, UC_HOOK_BLOCK, UC_HOOK_MEM_READ
    UC_REG = S.UC_REG
    ram = bytearray(0x10000)
    ram[0xfdae] = fdae
    regs = dict((k, 0) for k in S.KEYS)
    regs['a7'] = 0x10f300
    snap = dict(ram=bytes(ram), regs=regs, pc=0x852, bank=(0x200000, 0, 0))
    m = S.Machine(R.G['program'], R.G['fixed'], snap)
    m.install_basic_hooks()
    c = m.cpu
    c.reg_write(UC_REG['sr'], 0x2700)
    for base in (0x320000, 0x340000, 0x380000, 0x3a0000):
        c.mem_map(base, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    c.mem_map(0x400000, 0x400000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    for a in INPUT_PORTS:
        c.mem_write(a, b'\xff')
    devr = collections.Counter()

    def h_dev(uc, access, address, size, value, user):
        devr['%x/%d@%x' % (address, size, uc.reg_read(UC_REG['pc']))] += 1
        if (address, size) in BOOT_DEVICE_ANSWERS:
            uc.mem_write(address, BOOT_DEVICE_ANSWERS[(address, size)].to_bytes(size, 'big'))
    c.hook_add(UC_HOOK_MEM_READ, h_dev, begin=0x300000, end=0x3fffff)
    tbs = collections.Counter()

    def h_blk(uc, addr, size, user):
        tbs[addr] += 1
    c.hook_add(UC_HOOK_BLOCK, h_blk, begin=0, end=0xffffff)
    hit = dict(n=0)

    def h_stop(uc, pc, size, user):
        hit['n'] += 1
        uc.emu_stop()
    c.hook_add(UC_HOOK_CODE, h_stop, begin=0x2ab8, end=0x2ab8)
    bios = collections.Counter()
    ignored = []
    pc0 = 0x852
    err = None
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
    while True:
        err = None
        m.fetch_unmapped = None
        try:
            c.emu_start(pc0, 0xffffff, count=BOOT_LIMIT)
        except unicorn.UcError as e:
            err = str(e)
        fu = m.fetch_unmapped
        if m.invalid and m.invalid.get('access') == 'write-protected' and 0x200000 <= m.invalid['address'] < 0x300000:
            pcx = m.invalid['pc']
            ins = next(md.disasm(bytes(R.G['program'][pcx:pcx + 16]), pcx))
            ignored.append([m.invalid['address'], m.invalid['size'], pcx])
            m.invalid = None
            pc0 = pcx + ins.size
            continue
        if fu in BOOT_RTS_CALLS and hit['n'] == 0:
            a7 = m.regs()['a7']
            ret = m.long(a7)
            bios['%x<-%x' % (fu, ret)] += 1
            if sum(bios.values()) > 8:
                break
            c.reg_write(UC_REG['a7'], (a7 + 4) & 0xffffffff)
            pc0 = ret
            continue
        break
    reached = hit['n'] > 0 and m.pc() == 0x2ab8
    undeclared = sorted(k for k in devr if k not in BOOT_READS_ALLOWED)
    rec = dict(fdae=fdae, reached=reached, error=err, stop_pc=m.pc(), fetch_unmapped=m.fetch_unmapped, tb_unique=len(tbs), tb_total=sum(tbs.values()), ports=len(m.ports),
               ports_sha=S.ports_digest(m.ports), dev_reads=dict(sorted(devr.items())), undeclared_reads=undeclared, bios_calls=dict(sorted(bios.items())),
               ignored_writes=ignored, boot_ram_sha=sha(m.ram()),
               nodes=dict((hx(a), hx(m.long(a))) for a in (0x100820, 0x1008e4, 0x100b30, 0x100bf4, 0x100cb8, 0x100da8)),
               fields=dict((hx(a), hx(m.byte(a))) for a in (0x10fd80, 0x10fdae, 0x10fdaf, 0x10f004, 0x10f007, 0x104cd4, 0x100016, 0x100017)),
               long_104ca4=m.long(0x104ca4), a6_at_stop=m.regs()['a6'], a7_at_stop=m.regs()['a7'], a5_at_stop=m.regs()['a5'],
               palette_nonzero=sum(1 for b in bytes(c.mem_read(0x400000, 0x400000)) if b))
    if not reached or undeclared or err is not None or m.invalid or m.odd or any(k not in ('%x<-%x' % (a, 0)) and False for k in ()):
        raise SystemExit('boot of 10fdae=%d failed: %s' % (fdae, canon(rec)))
    st = m.state()
    regs = dict(st['regs'])
    assert regs['a6'] == 0x100820 and regs['a7'] == 0x10f300, regs
    rec['a5_before_shift'] = regs['a5']
    ram = bytearray(st['ram'])
    regs['a6'] = 0x1008e4
    regs['a7'] = SPD
    regs['a5'] = 0x108000
    ram[0x4ca4:0x4ca8] = SPD.to_bytes(4, 'big')
    shifted = dict(ram=bytes(ram), regs=regs, pc=0x2ac2, bank=st['bank'])
    rec['frame0_ram_sha'] = sha(bytes(ram))
    rec['frame0_regs'] = dict((k, regs[k]) for k in KEYS)
    rec['frame0_bank'] = list(st['bank'])
    return shifted, rec


# ----------------------------------------------------------------------------------
# One run (continuous or fresh-CPU split) of one configuration and seed
# ----------------------------------------------------------------------------------
def build_run(cfgname, case, mode, frames, keep_all_states, with_pack):
    FH, S, R, VI = CTX['FH'], CTX['S'], CTX['R'], CTX['VI']
    scripts = CTX['scripts']
    cfg = scripts['configs'][cfgname]
    writes, wrows, cross = host_writes_of(cfg, scripts)
    table = CTX['tables'][cfg['input']]
    sdef = scripts['scripts'][cfg['input']]
    io = dict(table=table, queue_limit=dict((int(k, 16), v) for k, v in sdef.get('queue_limit', {}).items()), crosscheck=cross, keep_all_states=keep_all_states)
    declared_seed = {}
    if cfg['family'] == 'stage':
        sd, snap, meta, rec, carried = FH.prepared(case)
        snapc = dict((k, v) for k, v in carried.items() if k != 'prep_entry_state')
        if cfg.get('seed_prep') == 'p1':
            snapc['ram'], prep = VI.p1_prep(snapc)
            declared_seed['p1_prep'] = dict(changed_bytes=prep['changed_bytes'], changed=prep['changed'], ports=prep['ports'])
        declared_seed['kind'] = sd['kind']
        caseid = case
    else:
        snapc = CTX['boot'][cfg['boot_fdae']][0]
        declared_seed['boot'] = CTX['boot'][cfg['boot_fdae']][1]
        caseid = -1
    runcfg = dict(FH.BASE_CFG)
    runcfg['writes'] = list(writes)
    IoRun = CTX['IoRun']
    run = IoRun(R.G['program'], R.G['fixed'], R.G['levels'], snapc, mode, frames, heavy=False, plan=None, sink=None, extend=False, answer=R.DEFAULT_ANSWER,
                full_dump=False, prep_dump=None, cfg=runcfg, case=caseid, tbset=None, keep_all=False, do_model=False, io=io)
    run.limit = frames
    run.pack = StatePack() if with_pack else None
    run.cfgname = cfgname
    return run, declared_seed, wrows


def stop_record(run):
    st = run.stop or {}
    out = dict((k, v) for k, v in st.items() if isinstance(v, (int, str, bool)))
    if 'wait' in st:
        out['wait_pc'] = st['wait']['pc']
    return out


def rec_compare_view(rec):
    """The fields of one frame record that must be equal between a continuous and a fresh-CPU split run."""
    keys = ('f', 'start', 'mode', 'hw', 'H', 'C', 'N', 'irq', 'q', 'qchk', 'fields', 'guard')
    return dict((k, rec.get(k)) for k in keys)


def run_one(task):
    cfgname, case, mode_list, frames, keep_all_states, out_dir = task['config'], task['case'], task['modes'], task['frames'], task['keep_all'], Path(task['out'])
    t0 = time.time()
    result = dict(config=cfgname, case=case)
    cont = None
    split = None
    for mode in mode_list:
        run, declared_seed, wrows = build_run(cfgname, case, mode, frames, keep_all_states if mode == 'continuous' else False, mode == 'continuous')
        run.run()
        if mode == 'continuous':
            cont = (run, declared_seed, wrows)
        else:
            split = run
    run, declared_seed, wrows = cont
    recs = run.records
    unr = dict((hx(pc), n) for pc, n in sorted(run.unr_total.items()))
    s = run.summary
    first_unr = run.unr_first
    guard = None
    for r in recs:
        if r['guard'] is not None:
            guard = dict(frame=r['f'], **r['guard'])
    summary = dict(
        frames_done=len(recs), stop=stop_record(run), guard=guard,
        ctrl_exits=dict((hx(k), v) for k, v in sorted(s['ctrl_exits'].items())), ctrl_entries=dict((hx(k), v) for k, v in sorted(s['enter_cb'].items())),
        input_modes=dict((str(k), v) for k, v in sorted(s['modes'].items())), queue_ok=s['qok'], queue_violations=s['qviol'], first_queue_violation=s['first_qviol'],
        p1_first=s['p1_first'], p1_frames=s['p1_frames'], p1_cbs=dict((hx(k), v) for k, v in sorted(s['p1cbs'].items(), key=lambda kv: (-kv[1], kv[0]))[:8]),
        p2_first=s['p2_first'], p2_frames=s['p2_frames'], stage_cbs=dict((hx(k), v) for k, v in sorted(s['stagecbs'].items(), key=lambda kv: (-kv[1], kv[0]))[:8]),
        cam_delta=(s['cam1'] - s['cam0']) if s['cam0'] is not None else None, areas=sorted(s['areas']), missions=sorted(s['missions']), mod1=sorted(s['mod1']),
        irq_total=dict(sorted(run.irq_total.items())), irq_at=dict(sorted(s['irq_phase'].items())), unr_unique=len(unr), unr_execs=sum(run.unr_total.values()),
        unr_first=[first_unr[0], first_unr[1], hx(first_unr[2])] if first_unr else None, unr_frames=run.unr_frames, banked_tbs=len(run.banked), ram_exec_tbs=run.ram_exec,
        crosscheck=run.xchk, final=dict((k, v) for k, v in run.cur_fields.items()) if recs else None, declared_seed=declared_seed)
    body = dict(format=RUN_FORMAT, version=VERSION, config=cfgname, case=case, mode='continuous', frames=recs, summary=summary, unr_pcs=unr)
    raw = canon(body).encode()
    rdir = out_dir / 'runs' / cfgname
    rdir.mkdir(parents=True, exist_ok=True)
    rpath = rdir / ('%03d.json.gz' % case if case >= 0 else 'boot.json.gz')
    rpath.write_bytes(gz(raw))
    entry = dict(config=cfgname, case=case, mode='continuous', records=dict(path=str(rpath.relative_to(out_dir)), sha256=sha(raw), bytes=len(raw)), frames=len(recs),
                 summary=dict((k, v) for k, v in summary.items() if k not in ('declared_seed', 'crosscheck', 'final')),
                 digest_chain=canon_sha([rec_compare_view(r) for r in recs]), host_writes=wrows)
    entry['summary']['final'] = summary['final']
    entry['summary']['crosscheck'] = summary['crosscheck']
    entry['summary']['declared_seed'] = summary['declared_seed']
    if run.pack is not None and run.pack.frames:
        pdata = run.pack.data()
        spath = out_dir / 'states' / cfgname / ('%03d.pack.gz' % case if case >= 0 else 'boot.pack.gz')
        spath.parent.mkdir(parents=True, exist_ok=True)
        spath.write_bytes(gz(pdata))
        back = read_pack(pdata)
        by_frame = dict((r['f'], r['start']) for r in recs)
        ok = all(d == by_frame[fr] for fr, st, d in back)
        entry['states'] = dict(path=str(spath.relative_to(out_dir)), sha256=sha(pdata), bytes=len(pdata), frames=[fr for fr, st, d in back], roundtrip_ok=ok,
                               all_frames=bool(keep_all_states))
    if split is not None:
        srecs = split.records
        first = None
        n = min(len(recs), len(srecs))
        for i in range(n):
            if rec_compare_view(recs[i]) != rec_compare_view(srecs[i]):
                a, b = rec_compare_view(recs[i]), rec_compare_view(srecs[i])
                first = dict(frame=recs[i]['f'], keys=[k for k in a if a[k] != b[k]])
                break
        same_len = len(recs) == len(srecs)
        unr_equal = canon(dict((hx(pc), n) for pc, n in sorted(split.unr_total.items()))) == canon(unr)
        tb_equal = all(a['tb'] == b['tb'] for a, b in zip(recs, srecs))
        entry['split'] = dict(frames=len(srecs), equal=bool(first is None and same_len), first_difference=first, same_length=same_len, split_chain=canon_sha([rec_compare_view(r) for r in srecs]),
                              unrouted_equal=unr_equal, tb_equal=tb_equal, stop_equal=canon(stop_record(run)) == canon(stop_record(split)))
    result['entry'] = entry
    result['elapsed'] = round(time.time() - t0, 1)
    return result


# ----------------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------------
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description='Unit IO native observer (scope: docs/analysis/input-stage-progress-observation-scope.md)')
    ap.add_argument('--family', choices=('stage', 'boot', 'all'), default='all')
    ap.add_argument('--config', default=None, help='comma list of configurations (default: all of the family); see docs/analysis/data/io-input-scripts.json')
    ap.add_argument('--frames', type=int, default=600, help='frames of the stage configurations (boot configurations use their own limit, capped by --boot-frames)')
    ap.add_argument('--boot-frames', type=int, default=2000)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--out', default=str(OUT_DEFAULT), help='output directory (must be new or empty; never deleted by this tool)')
    ap.add_argument('--seed-dir', default=None, help='stage_entry_body seed directory (historic pin %s); env MS5_SEED_DIR; default artifacts/stage_entry_body' % HISTORIC_SEED_SHA[:8])
    ap.add_argument('--split-cases', default=None, help='comma list of cases run also as fresh-CPU split (default: first 8 class representatives)')
    ap.add_argument('--cases', default=None, help='comma list restricting the stage seeds (default: the 137 natural seeds)')
    ap.add_argument('--p1b-cases', default=None, help='cases of P1b (default: the class representatives of this run)')
    ap.add_argument('--keep-all-states', default='all', choices=('none', 'representatives', 'all'),
                    help='state packs of the frame-start states: key frames only (none), every frame of the class representatives, P1b and boot runs (representatives), every frame of every run (all, default; '
                         'about 0.2 MB per 600-frame run)')
    ap.add_argument('--no-split', action='store_true')
    ap.add_argument('--no-fixtures', action='store_true')
    ap.add_argument('--compare', nargs=2, metavar=('DIR_A', 'DIR_B'), help='compare two output directories (compared_sha256, files except platform.json)')
    ap.add_argument('--selftest', action='store_true', help='short self test (no output directory)')
    return ap.parse_args(argv)


def compare_dirs(a, b):
    a, b = Path(a), Path(b)
    oa, ob = json.loads((a / 'observation.json').read_text()), json.loads((b / 'observation.json').read_text())

    def files(root):
        out = {}
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            for fn in filenames:
                p = Path(dirpath) / fn
                rel = str(p.relative_to(root))
                if rel == 'platform.json':
                    continue
                out[rel] = sha(p.read_bytes())
        return out
    fa, fb = files(a), files(b)
    only_a = sorted(set(fa) - set(fb))
    only_b = sorted(set(fb) - set(fa))
    differ = sorted(k for k in fa if k in fb and fa[k] != fb[k])
    res = dict(compared_sha256_a=oa['compared_sha256'], compared_sha256_b=ob['compared_sha256'], equal=oa['compared_sha256'] == ob['compared_sha256'], files_a=len(fa), files_b=len(fb),
               only_a=only_a[:10], only_b=only_b[:10], differ=differ[:10], clean=not (only_a or only_b or differ))
    print(json.dumps(res, indent=1))
    return 0 if res['equal'] and res['clean'] else 1


def run_phase(ctx, args, tlist, label, t_start):
    out = []
    if not tlist:
        return out
    with ctx.Pool(args.workers, maxtasksperchild=6) as pool:
        for r in pool.imap_unordered(run_one, tlist, chunksize=1):
            e = r['entry']
            print('[%6.0fs] %s %-16s case %4d frames %4d stop %-22s unr %5d p1 %4d el %5.1fs%s' % (
                time.time() - t_start, label, e['config'], e['case'], e['frames'], (e['summary']['stop'] or {}).get('reason'), e['summary']['unr_unique'],
                e['summary']['p1_frames'], r['elapsed'], '' if 'split' not in e else ' split=%s' % e['split']['equal']), file=sys.stderr, flush=True)
            out.append(r)
    return out


def main(argv=None):
    args = parse_args(argv)
    if args.compare:
        return compare_dirs(*args.compare)
    t_start = time.time()
    seed_dir = Path(args.seed_dir or os.environ.get('MS5_SEED_DIR') or SEED_DIR_DEFAULT)
    if not seed_dir.is_absolute():
        seed_dir = ROOT / seed_dir
    out_dir = Path(args.out)
    if not args.selftest:
        if out_dir.exists() and any(out_dir.iterdir()):
            raise SystemExit('output directory %s exists and is not empty (this tool never deletes; choose a new one)' % out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    rom0 = rom_guard()
    native_setup(seed_dir)
    scripts = load_scripts()
    CTX['scripts'] = scripts
    CTX['tables'] = dict((name, expand_script(sd)) for name, sd in scripts['scripts'].items())
    CTX['IoRun'] = make_io_class()
    S = CTX['S']
    all_cfgs = scripts['configs']
    fam = args.family
    wanted = args.config.split(',') if args.config else [n for n, c in all_cfgs.items() if not c.get('fixture') and (fam == 'all' or c['family'] == fam)]
    for n in wanted:
        if n not in all_cfgs:
            raise SystemExit('unknown configuration %s' % n)
    if args.config:
        fixtures = [n for n in wanted if all_cfgs[n].get('fixture')]
    else:
        fixtures = [] if args.no_fixtures or args.selftest else [n for n, c in all_cfgs.items() if c.get('fixture') and (fam == 'all' or c['family'] == fam)]
    wanted = [n for n in wanted if not all_cfgs[n].get('fixture')]
    stage_cfgs = [n for n in wanted if all_cfgs[n]['family'] == 'stage']
    boot_cfgs = [n for n in wanted if all_cfgs[n]['family'] == 'boot']
    cases = [int(x) for x in args.cases.split(',')] if args.cases else [c for c in sorted(S.SEEDS) if S.SEEDS[c]['kind'] == 'natural']
    CTX['boot'] = {}
    for fdae in sorted(set(all_cfgs[n]['boot_fdae'] for n in boot_cfgs)):
        snap1, rec1 = boot_native(fdae)
        snap2, rec2 = boot_native(fdae)
        assert snap1['ram'] == snap2['ram'] and canon(rec1) == canon(rec2), 'boot not deterministic'
        CTX['boot'][fdae] = (snap1, rec1)
        if not args.selftest:
            bdir = out_dir / 'boot'
            bdir.mkdir(exist_ok=True)
            (bdir / ('boot_fdae%d.json' % fdae)).write_text(json.dumps(dict(declarations=BOOT_DECLARATIONS, record=rec1), indent=1, sort_keys=True))
            (bdir / ('boot_fdae%d.frame0.ram.gz' % fdae)).write_bytes(gz(snap1['ram']))
    if args.selftest:
        return selftest(all_cfgs)
    ctx = multiprocessing.get_context('fork')

    def mk(cfg, case, modes, frames, keep):
        return dict(config=cfg, case=case, modes=modes, frames=frames, keep_all=keep, out=str(out_dir))

    def order(tl):
        return sorted(tl, key=lambda t: (-t['frames'] * (2 if len(t['modes']) > 1 else 1), t['config'], t['case']))
    keepmode = args.keep_all_states
    explicit_split = set(int(x) for x in args.split_cases.split(',')) if args.split_cases else None
    tasks = []
    for cfg in boot_cfgs:
        fr = min(all_cfgs[cfg]['frames'], args.boot_frames)
        tasks.append(mk(cfg, -1, ['continuous'] + ([] if args.no_split else ['split']), fr, keepmode != 'none'))
    for cfg in [n for n in stage_cfgs if n in ('P0', 'P1')]:
        fr = min(all_cfgs[cfg]['frames'], args.frames)
        for case in cases:
            sp = explicit_split is not None and case in explicit_split and not args.no_split
            tasks.append(mk(cfg, case, ['continuous'] + (['split'] if sp else []), fr, keepmode == 'all' or sp))
    for cfg in fixtures:
        c = all_cfgs[cfg]
        tasks.append(mk(cfg, c['case'], ['continuous'], min(c['frames'], args.frames), True))
    results = run_phase(ctx, args, order(tasks), 'phase1', t_start)
    entries = dict(((r['entry']['config'], r['entry']['case']), r['entry']) for r in results)
    # class representatives (scope 3.1): result signature = (first new unrouted, player frames, number of new unrouted PCs); new = outside the union of the P0 runs
    classes = None
    p0 = dict((k[1], e) for k, e in entries.items() if k[0] == 'P0')
    p1 = dict((k[1], e) for k, e in entries.items() if k[0] == 'P1')
    if p0 and p1:
        p0_union = set()
        for case, e in p0.items():
            p0_union |= set(load_run_unr(out_dir, e).keys())
        sigs = {}
        for case, e in sorted(p1.items()):
            unr = load_run_unr(out_dir, e)
            new = sorted(k for k in unr if k not in p0_union)
            body = load_run_body(out_dir, e)
            first_new = None
            for rec in body['frames']:
                hit = [u for u in rec['unr_new'] if hx(u[0]) not in p0_union]
                if hit:
                    first_new = [rec['f'], hit[0][2], hx(hit[0][0])]
                    break
            e['summary']['new_unr_unique'] = len(new)
            e['summary']['new_unr_execs'] = sum(unr[k] for k in new)
            e['summary']['first_new_unr'] = first_new
            sigs[case] = canon([first_new, e['summary']['p1_frames'], len(new)])
        groups = collections.OrderedDict()
        for case in sorted(sigs):
            groups.setdefault(sigs[case], []).append(case)
        glist = sorted(groups.values(), key=lambda g: (-len(g), g[0]))
        classes = [dict(rep=g[0], size=len(g), cases=g, signature=json.loads(sigs[g[0]])) for g in glist]
        CTX['p0_union_size'] = len(p0_union)
    reps = [c['rep'] for c in classes] if classes else []
    tasks2 = []
    if classes:
        split_set = explicit_split if explicit_split is not None else set(reps[:8])
        for cfg in ('P0', 'P1'):
            if cfg not in stage_cfgs:
                continue
            fr = min(all_cfgs[cfg]['frames'], args.frames)
            for case in reps:
                sp = (not args.no_split) and case in split_set
                e = entries.get((cfg, case))
                if e is not None and ('split' in e or not sp) and e.get('states', {}).get('all_frames'):
                    continue
                tasks2.append(mk(cfg, case, ['continuous'] + (['split'] if sp else []), fr, keepmode != 'none'))
    if 'P1b' in stage_cfgs:
        p1b = [int(x) for x in args.p1b_cases.split(',')] if args.p1b_cases else reps
        for case in p1b:
            tasks2.append(mk('P1b', case, ['continuous'], min(all_cfgs['P1b']['frames'], args.frames), keepmode != 'none'))
    results2 = run_phase(ctx, args, order(tasks2), 'phase2', t_start)
    rerun = []
    for r in results2:
        e = r['entry']
        k = (e['config'], e['case'])
        if k in entries:                                         # rerun of a phase-1 run: identical records required (an extra determinism check), richer states / split kept
            old = entries[k]
            if old['digest_chain'] != e['digest_chain'] or old['records']['sha256'] != e['records']['sha256']:
                raise SystemExit('rerun of %s case %d differs from phase 1' % k)
            for key in ('first_new_unr', 'new_unr_unique', 'new_unr_execs'):
                if key in old['summary']:
                    e['summary'][key] = old['summary'][key]
            rerun.append(k)
        entries[k] = e
    for k in sorted(rerun):
        entries[k]['rerun_identical'] = True
    elapsed = time.time() - t_start
    write_outputs(args, out_dir, list(entries.values()), classes, scripts, rom0, elapsed, fixtures)
    return 0


def selftest(all_cfgs):
    """Short in-process check: continuous versus fresh-CPU split of a stage seed and a boot run, the guard fixtures and a state pack round trip."""
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        jobs = [('P1', 94, 24), ('P0', 0, 16)] + [('boot-demo-0', -1, 12)]
        for cfg, case, frames in jobs:
            if all_cfgs[cfg]['family'] == 'boot' and all_cfgs[cfg]['boot_fdae'] not in CTX['boot']:
                CTX['boot'][all_cfgs[cfg]['boot_fdae']] = boot_native(all_cfgs[cfg]['boot_fdae'])
            r = run_one(dict(config=cfg, case=case, modes=['continuous', 'split'], frames=frames, keep_all=True, out=tmp))
            e = r['entry']
            good = e['split']['equal'] and e['states']['roundtrip_ok'] and e['summary']['queue_violations'] == 0
            print('selftest %-12s case %4d frames %3d split_equal=%s pack_roundtrip=%s queue_violations=%d -> %s' % (
                cfg, case, e['frames'], e['split']['equal'], e['states']['roundtrip_ok'], e['summary']['queue_violations'], 'ok' if good else 'FAIL'))
            ok = ok and good
        for cfg in ('fx-queue-short', 'fx-bios-call', 'fx-n-input-read', 'fx-c-input-read'):
            c = all_cfgs[cfg]
            r = run_one(dict(config=cfg, case=c['case'], modes=['continuous'], frames=min(c['frames'], 6), keep_all=False, out=tmp))
            g = r['entry']['summary']['guard']
            good = bool(g and g['kind'] == c['expect_guard'] and g['frame'] == c['expect_frame'])
            print('selftest %-16s guard %s frame %s -> %s' % (cfg, g and g['kind'], g and g['frame'], 'ok' if good else 'FAIL'))
            ok = ok and good
    print('selftest', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


def load_run_body(out_dir, entry):
    raw = gzip.decompress((Path(out_dir) / entry['records']['path']).read_bytes())
    return json.loads(raw)


def load_run_unr(out_dir, entry):
    return load_run_body(out_dir, entry)['unr_pcs']


def write_outputs(args, out_dir, entries, classes, scripts, rom0, elapsed, fixtures):
    if args.selftest:
        return
    S = CTX['S']
    rom1 = rom_guard()
    assert rom1 == rom0, 'ROM changed during the run'
    entries = sorted(entries, key=lambda e: (e['config'], e['case'], e['mode']))
    cfg_defs = {}
    for name, c in scripts['configs'].items():
        if any(e['config'] == name for e in entries):
            cfg_defs[name] = dict(c)
    pins = dict(
        rom=dict(sha256=ROM_SHA, size=rom0['size']), seed=dict(observation_sha256=CTX['rebase']['seed_sha256'], kind=CTX['rebase']['seed_kind']),
        tools=dict((k, v) for k, v in TOOL_PINS.items()), observer=dict(path='tools/observe_animation_machine_io.py', sha256=file_sha(Path(__file__))),
        routing=CTX['routing'], input_scripts=dict(path=str(SCRIPTS_FILE.relative_to(ROOT)), sha256=file_sha(SCRIPTS_FILE),
                                                    expanded=dict((n, expanded_sha(t)) for n, t in sorted(CTX['tables'].items())), expanded_frames=EXPAND_FRAMES),
        scope_doc=dict(path=str(SCOPE_DOC.relative_to(ROOT)), sha256=file_sha(SCOPE_DOC)))
    declared = [
        dict(kind='protocol', why='D1 frame protocol with the controller EXECUTED (C) and delivered IRQs: H -> C -> N; frame 0 = N0', evidence='scope 5.1; verify_animation_machine_frame_controller.py; verify_animation_machine_frame_irq.py'),
        dict(kind='irq', why='every wait in H, C and N (ef2 16bd0 cda4 3aea 47af0 478de) is released by one delivered IRQ (SR 2000 pushed, SR := 2100, PC := LONG ROM[64], BIOS SYSTEM_IO resume c0044a with LONG (A7) = 248, RTE emulated, registers checked, at most 16 per segment); '
                                    'device values BYTE 320000 = 0, WORD 3c0006 = 0 (raster / z80 values and the IRQ timing are [U])', evidence='verify_animation_machine_frame_irq.py'),
        dict(kind='card', why='BIOS card request c00468 (return c37c / c316) is the declared card resume with answer 0x80 (BYTE 10fdc6)', evidence='verify_animation_machine_frame_driver.py CARD_*'),
        dict(kind='palette', why='palette RAM 400000..7fffff = 512-fold mirror of one 8 KiB view of the selected bank; BYTE writes to 3a000f / 3a001f select bank 0 / 1', evidence='verify_animation_machine_frame_irq.py (E6)'),
        dict(kind='controller-return', why='after C the dispatcher return is the observer skip (PC := 2ac2, A7 += 4, SR := 2000, carry Unknown) and the device pages are zeroed before N', evidence='observe_animation_machine_frame_head.py run()'),
        dict(kind='seed-prep-p1', why='S seeds: original 3dce and c42 run natively (registers discarded) and BYTE 10fd80 |= 80 before frame 0 (F6-D preparation P1)', evidence='verify_animation_machine_frame_irq.py p1_prep'),
        dict(kind='stack', why='A7 = SPd = 1ff000 at every dispatcher level; B frame 0 shift declared (scope decision 1)', evidence='scope decision 1'),
        dict(kind='guards', why='rom-write is a checked stop (scope decision 2); BIOS fetch c00444 in C = system-return (normal end); any other BIOS fetch = bios-boundary; direct input / raster port reads in N or C = undeclared-device-read; '
                                'queue empty / size, odd pc / data, unmapped, head / menu callbacks, wait not released, IRQ failure and step limits as in the D1 / controller / IRQ tools', evidence='scope 5.6'),
        dict(kind='boot', declarations=BOOT_DECLARATIONS, evidence='scope 3.3'),
    ]
    agg = aggregate(entries, classes)
    agg['stage'] = stage_aggregates(out_dir, entries)
    obs = dict(format=FORMAT, version=VERSION, pins=pins, protocol=dict(frames=args.frames, boot_frames=args.boot_frames, tb_unrouted='first instruction start per TB outside the routing bitmap (IO-1 definition)',
                                                                       state_digest='sha256(MS5-IO-STATE-1 + header(16 regs, pc, bank base, ff8, ff9, status, palette select) + RAM 64KiB + PVC page 8KiB + palette bank 0 + bank 1)',
                                                                       pack='page-delta pack of frame-start states (256-byte pages: RAM 256, PVC 32, palette 2 x 32)'),
               declared=declared, configs=cfg_defs, classes=classes, class_baseline=dict(p0_union_unrouted_pcs=CTX.get('p0_union_size')), runs=entries, aggregates=agg,
               fixtures=check_fixtures(entries))
    obs['compared_sha256'] = canon_sha(obs)
    (out_dir / 'observation.json').write_text(json.dumps(obs, indent=1, sort_keys=True))
    inv = {}
    for dirpath, dirnames, filenames in os.walk(out_dir, followlinks=False):
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            rel = str(p.relative_to(out_dir))
            if rel in ('platform.json', 'observation.json'):
                continue
            inv[rel] = dict(sha256=file_sha(p), bytes=p.stat().st_size)
    import unicorn
    import capstone
    lib = [dict(path=str(cand), sha256=file_sha(cand)) for cand in sorted((Path(unicorn.__file__).parent / 'lib').glob('*unicorn*')) if cand.is_file()]
    import subprocess
    try:
        head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True, close_fds=False).stdout.strip()
    except OSError:
        head = None
    plat = dict(git_head=head, unicorn=unicorn.__version__, capstone=capstone.__version__ if hasattr(capstone, '__version__') else None, unicorn_library=lib, python=sys.version, os=platform_module.platform(),
                machine=platform_module.machine(), workers=args.workers, elapsed_seconds=round(elapsed, 1), generated=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                compared_sha256=obs['compared_sha256'], rom_mtime_ns=rom0['mtime_ns'], rom_unchanged=True, output_bytes=sum(v['bytes'] for v in inv.values()), file_inventory=inv, argv=sys.argv[1:])
    (out_dir / 'platform.json').write_text(json.dumps(plat, indent=1, sort_keys=True))
    print('observation.json compared_sha256 %s output %d bytes in %d files' % (obs['compared_sha256'], plat['output_bytes'], len(inv)), file=sys.stderr)


def aggregate(entries, classes):
    agg = {}
    for cfg in sorted(set(e['config'] for e in entries)):
        es = [e for e in entries if e['config'] == cfg]
        stops = collections.Counter((e['summary']['stop'] or {}).get('reason') for e in es)
        guards = collections.Counter((e['summary']['guard'] or {}).get('kind') for e in es)
        agg[cfg] = dict(runs=len(es), frames=sum(e['frames'] for e in es), stops=dict(sorted(stops.items())), guards=dict((str(k), v) for k, v in sorted(guards.items(), key=lambda kv: str(kv[0]))),
                        players=sum(1 for e in es if e['summary']['p1_frames']), player_frames=sum(e['summary']['p1_frames'] for e in es),
                        seeds_with_unrouted=sum(1 for e in es if e['summary']['unr_unique']), queue_violations=sum(e['summary']['queue_violations'] for e in es),
                        irq=dict(sorted(sum((collections.Counter(e['summary']['irq_total']) for e in es), collections.Counter()).items())))
    return agg


def stage_aggregates(out_dir, entries):
    """Cross-seed numbers of the stage family (compared fields): baseline P0 union, new unrouted PCs of P1, players, controller exits, first-new frames."""
    out = {}
    p0 = [e for e in entries if e['config'] == 'P0']
    p1 = [e for e in entries if e['config'] == 'P1']
    if not (p0 and p1):
        return out
    base = set()
    for e in p0:
        base |= set(load_run_unr(out_dir, e).keys())
    new_union = collections.Counter()
    seeds_per_pc = collections.Counter()
    firsts = []
    first_pc = collections.Counter()
    for e in sorted(p1, key=lambda x: x['case']):
        unr = load_run_unr(out_dir, e)
        for k, n in unr.items():
            if k not in base:
                new_union[k] += n
                seeds_per_pc[k] += 1
        fn = e['summary'].get('first_new_unr')
        if fn:
            firsts.append(fn[0])
            first_pc[fn[2]] += 1
    firsts.sort()

    def exits(es):
        c = collections.Counter()
        for e in es:
            for k in e['summary']['ctrl_exits']:
                c[k] += 1
        return dict(sorted(c.items()))
    out['baseline_p0_unrouted_pcs'] = sorted(base)
    out['p1_new_unrouted_pcs'] = len(new_union)
    out['p1_new_unrouted_execs'] = sum(new_union.values())
    out['p1_new_unrouted_pcs_seen_by_seeds'] = dict(sorted(collections.Counter(seeds_per_pc.values()).items()))
    out['p1_seeds_with_new_unrouted'] = len(firsts)
    out['p1_first_new_frame'] = dict(min=firsts[0], median=firsts[len(firsts) // 2], max=firsts[-1]) if firsts else None
    out['p1_first_new_pc'] = dict(sorted(first_pc.items(), key=lambda kv: (-kv[1], kv[0])))
    out['p1_seeds_with_player'] = sum(1 for e in p1 if e['summary']['p1_frames'])
    out['p1_player_frames'] = sum(e['summary']['p1_frames'] for e in p1)
    out['p1_seeds_with_p2'] = sum(1 for e in entries if e['config'] == 'P1b' and e['summary']['p2_frames'])
    out['p0_seeds_by_controller_exit'] = exits(p0)
    out['p1_seeds_by_controller_exit'] = exits(p1)
    out['p0_complete_seeds'] = sum(1 for e in p0 if e['summary']['stop'].get('reason') == 'frame-limit')
    out['p1_complete_seeds'] = sum(1 for e in p1 if e['summary']['stop'].get('reason') == 'frame-limit')
    out['p1_non_complete'] = sorted((e['case'], e['summary']['stop'].get('reason')) for e in p1 if e['summary']['stop'].get('reason') != 'frame-limit')
    out['p0_non_complete'] = sorted((e['case'], e['summary']['stop'].get('reason')) for e in p0 if e['summary']['stop'].get('reason') != 'frame-limit')
    return out


def check_fixtures(entries):
    out = []
    for e in entries:
        c = CTX['scripts']['configs'][e['config']]
        if 'expect_guard' not in c:
            continue
        g = e['summary']['guard']
        out.append(dict(config=e['config'], case=e['case'], natural=not c.get('fixture'), expect=c['expect_guard'], expect_frame=c['expect_frame'], observed=g, ok=bool(g and g['kind'] == c['expect_guard'] and g['frame'] == c['expect_frame'])))
    return out


if __name__ == '__main__':
    sys.exit(main())
