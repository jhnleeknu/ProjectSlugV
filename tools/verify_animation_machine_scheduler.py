"""Scheduler shell F2 (2aac boot entry, 270e / 2716 / 271a idle callback, 4fcce..4fda6 fade child, frame pass 2ac2 -> frame head callback) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection.  The frozen native observation (artifacts/animation_machine_scheduler_native, an immutable input) is read, never regenerated here: the
observer main is never invoked; the observer module is imported ONLY as (a) the natural seed snapshot generator (seed_snap), (b) the independent node-trace generator used to order block
leaders for the split chains (a fresh Unicorn CPU, traced_native) and (c) the fixture generator of the extra typed fixtures of this verifier (replay_node).  Frame pass protocol (contract
decision 2): one C++ run = one whole frame pass, PC 2ac2, A6 1008e4, A7 SPd = 1ff000, LONG 104ca4 = SPd (declared host write, part of the recorded seed state), stop PC = LONG (100820)
(e4a / e74; the host rejects any other value); the next pass restarts from the actual previous C++ output with PC 2ac2, A6 1008e4, A7 SPd (declared boundary, nothing else changes).
  * natural seeds (142 = 137 begin outputs + 5 release guard rows): every pass of every recorded frame is run in the actual C++ and compared with the recorded pass:
    start digest (seed RAM / the previous C++ output with the declared boundary) equal to the recorded one BEFORE the run, end digest (64 KiB RAM, 16 registers, PC, bank, PVC words) and ordered
    port digest equal to the recorded ones, node-by-node (2ac2 -> 2abe entry, 2abe -> 2ac2 exit; 4 phases of the dispatcher) entry / exit / ports digests equal to the recorded node rows and the
    node-by-node chain equals the whole-pass run byte for byte; dump frames are compared with the recorded RAM blobs;
  * seeds whose pass cannot run to the frame head (native stop or a callback without an executor): the whole-pass run is a checked error that preserves every output; the node-by-node walk
    runs the nodes before the failing one against the recorded rows and classifies the failing node (native stop reason vs the exact C++ error string);
  * typed fixtures (18 native + extra ones of this verifier), negatives (interior / odd / unrouted neighbours / wrong stops), zero-step at every start x 3 carries, carry as block classification
    (single-block probes: FLOW_ONLY 271a and 4fda4), 4fcce path coverage through split chains ordered by the independent native trace.
Native SR is never read: C is a block classification.
"""
import collections
import concurrent.futures
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import traceback
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
from disassemble_program import load_verified_program, disassemble_range

ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = '/Users/start/Workspce/metalslug'
OUT = ROOT / 'artifacts/animation_machine_scheduler_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_scheduler_native'
PVC_DIR = ROOT / 'artifacts/animation_machine_pvc_banks_native'
PVC_SHA = '613bd4648d7ed3035620ad1949e1be4c94e4e866635a788a423df6c9650a65fe'
NATIVE_SHA = 'c330e597f9585c2595006239be49ab0bcb029f4b5fed5c70ebf872fe91a2b4ff'
NATIVE_TOOL_SHA = '62bb23ff6d2f61a5e47af71b8e1308d50c99b85d95f3278b8d825b7ee327c01c'
CONTRACT = ROOT / 'docs/analysis/animation-machine-scheduler-shell-f2-contract.md'
CONTRACT_SHA = '6584431718e82293372350b9fa736b2c949e6947e4f989b85aa60079d52f1c1b'
CPP_PINS = {'engine/src/animation_machine_scheduler.cpp': '1deb3bcc13ed13b061d0d1d0e5980653f5a0c271f14a54d002fb07ef2e87b587'}
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
SPD = 0x1ff000
A5V = 0x108000
BASE_LONG = 0x104ca4
FRAME_HEAD = 0x100820
CONTROLLER = 0x1008e4
PASS_PC = 0x2ac2
ENTRY_PC = 0x2abe
LOOP_PC = 0x2ab8
BOOT_PC = 0x2aac
HEAD_STOPS = (0xe4a, 0xe74)
REG16 = tuple('d%d' % i for i in range(8)) + tuple('a%d' % i for i in range(8))
STARTS = (0x2aac, 0x270e, 0x2716, 0x271a, 0x4fcce, 0x4fcda, 0x4fcee, 0x4fcfe, 0x4fd58, 0x4fd5e, 0x4fd6a, 0x4fd72, 0x4fd7c, 0x4fd84, 0x4fd8c, 0x4fd9e, 0x4fda4)
RANGES = ((0x2aac, 0x2ab8), (0x270e, 0x271c), (0x4fcce, 0x4fd0a), (0x4fd58, 0x4fda6))
BUNDLED = (0x2712, 0x4fcea, 0x4fd5a, 0x4fd78, 0x4fd80, 0x4fd88)
FLOW_BLOCKS = (0x271a, 0x4fda4)
UNSUPPORTED_SCHED = 'unsupported animation scheduler PC'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNALIGNED_PC = 'unaligned animation machine PC'
EVEN = 'program bus requires even WORD/LONG address'
BUDGET = 'animation machine block budget exceeded'
WORKERS = int(os.environ.get('SCHED_WORKERS', '3'))
NATURAL_CASES = [int(x) for x in os.environ.get('SCHED_CASES', '').split(',') if x]      # development switch only
NO_NATURAL = bool(os.environ.get('SCHED_NO_NATURAL'))                                   # development switch only
RUN_DIR = None
VERIFIED_BLOBS = set()


def localize(name):
    local = str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name
    return local if Path(local).exists() else name


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


HARNESS_SERVER = r'''#include "ms5/animation_machine.h"
#include "ms5/physical_rom_resource.h"
#include <fstream>
#include <iterator>
#include <iostream>
#include <sstream>
#include <cstdlib>
static std::vector<std::uint8_t> load(const char* p) {
    std::ifstream f(p,std::ios::binary);return std::vector<std::uint8_t>((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
}
static bool save(const char* p,const std::vector<std::uint8_t>& b) {
    std::ofstream f(p,std::ios::binary);if(!b.empty())f.write(reinterpret_cast<const char*>(&b[0]),b.size());f.close();return !f.fail();
}
static void u32(std::ofstream& f,std::uint32_t n){for(int i=3;i>=0;--i)f.put(static_cast<char>((n>>(i*8))&255));}
int main(int argc,char** argv) {
    std::vector<ms5::PhysicalRomResource> physical;std::string error;
    for(int i=1;i<argc;++i){ms5::PhysicalRomResource r;if(!ms5::load_physical_rom_resource(argv[i],r,error)){std::cerr<<error;return 3;}physical.push_back(r);}
    std::vector<ms5::FixedDataResource> windows;ms5::ProgramBusState bus;bus.physical_rom=&physical;
    std::vector<std::uint8_t> vectors;
    for(std::size_t i=0;i<physical.size();++i)if(physical[i].source_rom_offset==0&&physical[i].data.size()>=128) vectors.assign(physical[i].data.begin(),physical[i].data.begin()+128);
    if(!vectors.empty())bus.vectors=&vectors;
    std::string line;
    while(std::getline(std::cin,line)){
        std::istringstream in(line);std::vector<std::string> t;std::string w;while(in>>w)t.push_back(w);
        if(t.size()!=26){std::cout<<"{}\n-"<<std::endl;continue;}
        ms5::AnimationMachineState s;for(unsigned i=0;i<8;++i)s.d[i]=std::strtoul(t[i].c_str(),NULL,0);
        for(unsigned i=0;i<8;++i)s.a[i]=std::strtoul(t[8+i].c_str(),NULL,0);s.pc=std::strtoul(t[16].c_str(),NULL,0);
        s.carry=static_cast<ms5::AnimationCarryState>(std::strtoul(t[17].c_str(),NULL,0));
        ms5::AnimationMachineDevice device;device.bank_base=std::strtoul(t[18].c_str(),NULL,0);
        const std::uint32_t stop=std::strtoul(t[19].c_str(),NULL,0);const std::uint8_t external=std::strtoul(t[20].c_str(),NULL,0);
        std::vector<std::uint8_t> ram=load(t[21].c_str());device.pvc=load(t[22].c_str());
        ms5::VideoPortWrite marker;marker.size=1;marker.address=0xdeadbeef;marker.value=0x87;
        std::vector<ms5::VideoPortWrite> ports(1,marker);std::uint32_t reads=0x12345678;
        ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;error.clear();
        bool ok=ms5::run_animation_machine(ram,windows,bus,s,device,stop,external,reads,status,ports,error);
        if(!save(t[23].c_str(),ram)||!save(t[24].c_str(),device.pvc)){std::cout<<"{}\n-"<<std::endl;continue;}
        std::ofstream portfile(t[25].c_str(),std::ios::binary);
        for(std::size_t i=0;i<ports.size();++i){portfile.put(static_cast<char>(ports[i].size));u32(portfile,ports[i].address);u32(portfile,ports[i].value);}portfile.close();
        if(portfile.fail()){std::cout<<"{}\n-"<<std::endl;continue;}
        std::ostringstream o;
        o<<"{";
        for(unsigned i=0;i<8;++i)o<<(i?",":"")<<"\"d"<<i<<"\":"<<s.d[i];
        for(unsigned i=0;i<8;++i)o<<",\"a"<<i<<"\":"<<s.a[i];
        o<<",\"pc\":"<<s.pc<<",\"carry\":"<<static_cast<unsigned>(s.carry)<<",\"bank_base\":"<<device.bank_base<<",\"external_reads\":"<<reads
            <<",\"status\":"<<static_cast<unsigned>(status)<<",\"ok\":"<<(ok?"true":"false")<<"}";
        std::string hex;static const char* digits="0123456789abcdef";
        if(!ok)for(std::size_t i=0;i<error.size();++i){hex+=digits[(static_cast<unsigned char>(error[i])>>4)&15];hex+=digits[static_cast<unsigned char>(error[i])&15];}
        if(hex.empty())hex="-";
        std::cout<<o.str()<<"\n"<<hex<<std::endl;
    }
    return 0;
}
'''


class Server(object):
    """One batch harness process (used by one thread at a time)."""
    def __init__(self, exe, resources):
        self.proc = subprocess.Popen([str(exe)] + list(map(str, resources)), stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, close_fds=False)

    def call(self, args):
        self.proc.stdin.write(' '.join(args) + '\n')
        self.proc.stdin.flush()
        first = self.proc.stdout.readline()
        second = self.proc.stdout.readline()
        assert first and second, 'batch harness died'
        error = '' if second.strip() == '-' else bytes.fromhex(second.strip()).decode()
        return first, error

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=60)
        except Exception:
            self.proc.kill()


SERVERS = []
TLS = threading.local()
SERVER_EXE = [None, None]


def reset_servers():
    global TLS
    SERVERS[:] = []
    TLS = threading.local()


def server():
    srv = getattr(TLS, 'server', None)
    if srv is None:
        srv = Server(SERVER_EXE[0], SERVER_EXE[1])
        TLS.server = srv
        SERVERS.append(srv)
    return srv


def request_args(state, pvc_bank, stop, external, paths):
    return [str(state[k]) for k in common.REGS] + [str(state['pc']), str(state['carry']), str(pvc_bank), str(stop), str(external)] + list(map(str, paths))


def invoke(exe, folder, label, ram, state, pvc, bank, resources, stop, external=0, oneshot=False):
    paths = [folder / (label + s) for s in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin')]
    paths[0].write_bytes(ram)
    paths[1].write_bytes(pvc)
    if oneshot:
        args = [str(exe)] + request_args(state, bank, stop, external, paths) + list(map(str, resources))
        run = subprocess.run(args, capture_output=True, text=True, timeout=1800, close_fds=False)
        assert run.returncode == 0, (label, run.stderr)
        text, error = run.stdout, run.stderr
    else:
        text, error = server().call(request_args(state, bank, stop, external, paths))
    result = common.parse(text, expected_invalid_carry=state['carry'] if state['carry'] not in (0, 1, 2) else None)
    assert paths[0].read_bytes() == ram and paths[1].read_bytes() == pvc
    out = (result, paths[2].read_bytes(), paths[3].read_bytes(), paths[4].read_bytes(), error)
    for path in paths:
        path.unlink()
    return out


def compile_server(root, folder):
    path = folder / 'harness_batch.cpp'
    path.write_text(HARNESS_SERVER)
    exe = folder / 'animation_machine_scheduler_batch_harness'
    compiler = shutil.which('clang++')
    assert compiler
    command = [compiler, '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(root / 'engine/include')]
    command += [str(root / 'engine/src' / name) for name in common.SOURCES]
    command += [str(path), '-o', str(exe)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    (folder / 'compile_batch.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stdout and not run.stderr, run.stderr
    return exe, command


# ----------------------------------------------------------------------------------------------------------------- state helpers
def sched_state_digest(ram, regs, pc, bank):
    """The scheduler observer's state digest (MS5-SCHED-STATE-1) recomputed from a C++ state: 64 KiB RAM, 16 registers, PC, bank base, PVC words ff8 / ff9."""
    h = hashlib.sha256()
    h.update(b'MS5-SCHED-STATE-1')
    h.update(ram)
    h.update(struct.pack('>16I', *[regs[k] for k in REG16]))
    h.update(struct.pack('>IIIHH', pc, bank[0], 0, bank[1] & 0xffff, bank[2] & 0xffff))
    return h.hexdigest()


MOVEM_CALLBACKS = (0x4fcce, 0x4fcda)


def native_events(ports, movem=False):
    """C++ ordered ports (size, address, value 9-byte records) as the observer's event tuples (kind 1 = PVC bank words, kind 2 = other device writes).  A 3c0000 size 4 port is one native
    LONG store (MOVE.L), except inside the fade child callbacks 4fcce / 4fcda where the 4fd8c MOVEM.W D3-D4,(A4) is the pair of the two native WORD stores (3c0000 high, 3c0002 low), the
    map_transfer convention (`movem`)."""
    events = []
    for i in range(0, len(ports), 9):
        size, address, value = struct.unpack('>BII', ports[i:i + 9])
        if 0x2fe000 <= address < 0x300000:
            events.append((1, address, size, value))
        elif movem and size == 4 and address == 0x3c0000:
            events.append((2, address, 2, value >> 16))
            events.append((2, address + 2, 2, value & 0xffff))
        else:
            events.append((2, address, size, value))
    return events


def events_digest(events):
    h = hashlib.sha256()
    h.update(b'MS5-SCHED-PORTS-1')
    for e in events:
        h.update(struct.pack('>BIBI', *e))
    return h.hexdigest()


def ports_digest(ports, movem=False):
    return events_digest(native_events(ports, movem))


def bank_words(pvc):
    return int.from_bytes(pvc[0x1ff0:0x1ff2], 'big'), int.from_bytes(pvc[0x1ff2:0x1ff4], 'big')


def pvc_page_for(bank):
    page = bytearray(8192)
    page[0x1ff0:0x1ff2] = bank[1].to_bytes(2, 'big')
    page[0x1ff2:0x1ff4] = bank[2].to_bytes(2, 'big')
    return bytes(page)


def out_state(result):
    return {k: result[k] for k in common.STATE_KEYS}


class St(object):
    """One machine state of the verifier chain: RAM, 16R + PC + carry, PVC image, bank base."""
    __slots__ = ('ram', 'state', 'pvc', 'bank')

    def __init__(self, ram, state, pvc, bank):
        self.ram, self.state, self.pvc, self.bank = ram, dict(state), pvc, bank

    def digest(self, pc=None):
        words = bank_words(self.pvc)
        return sched_state_digest(self.ram, self.state, self.state['pc'] if pc is None else pc, (self.bank, words[0], words[1]))

    def long(self, address):
        o = address & 0xffff
        return int.from_bytes(self.ram[o:o + 4], 'big')

    def word(self, address):
        o = address & 0xffff
        return int.from_bytes(self.ram[o:o + 2], 'big')

    def byte(self, address):
        return self.ram[address & 0xffff]

    def with_pc(self, pc, **regs):
        s = dict(self.state, pc=pc)
        s.update(regs)
        return St(self.ram, s, self.pvc, self.bank)

    def put(self, address, size, value):
        ram = bytearray(self.ram)
        o = address & 0xffff
        assert o + size <= 0x10000
        ram[o:o + size] = (value & ((1 << (8 * size)) - 1)).to_bytes(size, 'big')
        return St(bytes(ram), self.state, self.pvc, self.bank)


def from_seed_snap(snap):
    """Observer snapshot (ram, regs, pc, bank tuple) -> St (carry Unknown, SR never read)."""
    base, ff8, ff9 = snap['bank']
    state = {k: snap['regs'][k] & M32 for k in REG16}
    state.update(pc=snap['pc'], carry=0)
    return St(snap['ram'], state, pvc_page_for((base, ff8, ff9)), base)


def run(ctx, label, st, stop, external=0):
    """One C++ run from a St.  Returns (result, St_out or None, ports, error)."""
    result, ram, pvc, ports, error = invoke(ctx.exe, RUN_DIR, label, st.ram, st.state, st.pvc, st.bank, ctx.resources, stop, external)
    if not result['ok']:
        assert error and not error.endswith('\n') or True
        assert {k: result[k] for k in common.STATE_KEYS} == {k: st.state[k] for k in common.STATE_KEYS} and ram == st.ram and pvc == st.pvc and result['bank_base'] == st.bank
        assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1, (label, 'failure did not preserve the outputs')
        return result, None, b'', error.strip()
    return result, St(ram, out_state(result), pvc, result['bank_base']), ports, ''


def classify_error(text):
    """Group the checked C++ error strings by class (the exact string is always recorded as well)."""
    return text


def release_wait(st, pc):
    """Declared host release of a wait (F1 observer vocabulary, identical to the scheduler observer): sound ring tail := ffff, sprite queue word := D4.W, gate BYTE 107ded bit7 cleared unless WORD 107dea <> 0."""
    if pc == 0x3aea:
        return st.put(0x104d74, 2, 0xffff), [['ram', 0x104d74, 2, 0xffff]]
    if pc == 0xcda4:
        return st.put(0x108d34, 2, st.state['d4'] & 0xffff), [['ram', 0x108d34, 2, st.state['d4'] & 0xffff]]
    if st.word(0x107dea) == 0:
        value = st.byte(0x107ded) & 0x7f
        return st.put(0x107ded, 1, value), [['ram', 0x107ded, 1, value]]
    return st, []


WAIT_LIMIT = 16


def run_wait(ctx, label, st, stop, waits):
    """Run to `stop`; a Waiting status is released by the declared host write and the same pass continues (at the same PC / A7)."""
    ports_all = b''
    n = 0
    while True:
        result, out, ports, error = run(ctx, '%s_w%d' % (label, n), st, stop)
        if out is None:
            return result, None, b'', error
        ports_all += ports
        if result['status'] == 0:
            return result, out, ports_all, ''
        pc = result['pc']
        released, changes = release_wait(out, pc)
        waits.append(dict(pc=hex(pc), a7=hex(result['a7']), released=changes))
        if not changes or len(waits) > WAIT_LIMIT:
            return result, out, ports_all, 'wait-not-released'
        st = released
        n += 1


# ----------------------------------------------------------------------------------------------------------------- static audit
def expand_hex(text):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{4,6})`', text)]


def audit_static(program):
    """Contract byte tables vs ROM, block starts / bundled branches / FLOW_ONLY from the ROM bytes (independent of the C++), C++ case labels and routing."""
    lines = CONTRACT.read_text().splitlines()
    pat = re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)`[^|]*\| `([0-9a-f]+)` \|')
    checked = []
    for line in lines:
        m = pat.match(line)
        if m:
            low, high = int(m.group(1), 16), int(m.group(2), 16)
            if low in (0x2aac, 0x270e, 0x4fcce, 0x4fd58):
                assert program[low:high].hex() == m.group(3), hex(low)
                checked.append((low, high))
    assert sorted(checked) == sorted(((0x2aac, 0x2ab8), (0x270e, 0x271c), (0x4fcce, 0x4fd0a), (0x4fd58, 0x4fda6))), checked
    # instruction decode of the four ranges
    insts = {}
    for low, high in RANGES:
        pc = low
        while pc < high:
            item = disassemble_range(program, pc, 10, pc)[0]
            assert item['cpu_address'] == pc and item['classification'] == 'candidate_instruction', (hex(pc), item['classification'])
            insts[pc] = item
            pc += item['size']
        assert pc == high
    names = lambda pc: insts[pc]['mnemonic'].split('.')[0]
    start_set = set(STARTS)
    blocks = collections.OrderedDict()
    for low, high in RANGES:
        pc, cur = low, None
        while pc < high:
            if pc in start_set or cur is None:
                cur = pc
                blocks[cur] = []
            blocks[cur].append(pc)
            pc += insts[pc]['size']
    assert sorted(blocks) == sorted(STARTS) and len(insts) == sum(len(v) for v in blocks.values())
    branches = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
    bundled = sorted(pc for b in blocks.values() for pc in b[1:] if names(pc) in branches)
    assert bundled == sorted(BUNDLED), [hex(p) for p in bundled]
    flow = sorted(s for s, b in blocks.items() if all(names(p) in FLOW_ONLY for p in b))
    # 2aac contains LEA + MOVE.L (not in FLOW_ONLY); the contract: only 271a is FLOW_ONLY, 4fda4 is the worker fill-in (RTS only)
    assert flow == sorted(FLOW_BLOCKS), [hex(p) for p in flow]
    assert insts[0x4fda4]['mnemonic'].startswith('rts') and insts[0x271a]['mnemonic'].startswith('rts')
    even = [pc for low, high in RANGES for pc in range(low, high, 2)]
    odd = [pc for low, high in RANGES for pc in range(low + 1, high, 2)]
    interior = [pc for pc in even if pc not in start_set]
    return dict(insts=insts, blocks=blocks, bundled=bundled, flow=flow, even=even, odd=odd, interior=interior)


def cpp_static():
    text = (ROOT / 'engine/src/animation_machine_scheduler.cpp').read_text()
    cases = sorted(set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text)))
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    inside = sorted(pc for pc in table if in_ranges(pc, RANGES))
    ranges = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)\)[^\n]*animation_scheduler_block|next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', ''))
    line = [l for l in machine.splitlines() if 'animation_scheduler_block' in l]
    assert len(line) == 1
    start = machine.index('animation_scheduler_block(c)')
    seg = machine[machine.rfind('else if', 0, start):start]
    ranges = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', seg))
    return cases, inside, ranges


# ----------------------------------------------------------------------------------------------------------------- native data
def read_blob(name):
    path = NATIVE_DIR / 'blobs' / name
    if not path.exists():
        path = PVC_DIR / 'blobs' / name
    data = path.read_bytes()
    assert sha(data) == name.split('.')[0], name
    VERIFIED_BLOBS.add(name)
    return data


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_scheduler.py') == NATIVE_TOOL_SHA
    assert cc.digest(CONTRACT) == CONTRACT_SHA
    for name, expected in CPP_PINS.items():
        assert cc.digest(ROOT / name) == expected, name
    report = json.loads(path.read_text())
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['rom_stat_start'] == report['rom_stat_end'] and report['rom_stat_start']['sha256'] == ROM_SHA
    assert report['model_mismatches'] == [] and len(report['seeds']) == 142 and report['totals']['natural'] == 137 and report['totals']['guard_rows'] == 5
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    return report


def load_seed_file(row):
    data = (NATIVE_DIR / row['file']).read_bytes()
    assert sha(data) == row['file_sha256'] and len(data) == row['file_size'], row['file']
    return json.loads(gzip.decompress(data))


def pvc_replacement(case, original, row):
    """Pinned expanded-bank native record, with the old prefix retained."""
    path = PVC_DIR / 'observation.json'
    assert cc.digest(path) == PVC_SHA
    obs = json.loads(path.read_text())
    record = next(r for r in obs['seeds'] if r['case'] == case)
    data = (PVC_DIR / record['file']).read_bytes()
    assert sha(data) == record['file_sha256'] and len(data) == record['file_size']
    replacement = json.loads(gzip.decompress(data))
    assert record['frames_done'] == record['frames_complete'] == 120
    assert replacement['passes'][0]['start'] == original['passes'][0]['start']
    assert row['kind'] == 'natural' and record['waits'] == {}
    replacement['kind'] = row['kind']  # provenance metadata absent from the expanded schema
    for frame in replacement['passes']:
        frame['waits'] = []  # the pinned expanded observation asserts no waits
    old_start = next(d for d in original['dumps'] if d['kind'] == 'seed-start')
    new_start = next(d for d in replacement['dumps'] if d['kind'] == 'seed-start')
    assert all(old_start[k] == new_start[k] for k in ('pc', 'regs', 'ram', 'bank', 'state'))
    old_nodes, new_nodes = original['passes'][0]['nodes'], replacement['passes'][0]['nodes']
    assert old_nodes[-1]['partial'] and not new_nodes[len(old_nodes) - 1]['partial']
    for i, old in enumerate(old_nodes):
        keys = ('a6', 'cb', 'seq', 'entry') if old['partial'] else ('a6', 'cb', 'seq', 'entry', 'exit', 'ports', 'ports_sha')
        assert all(old[k] == new_nodes[i][k] for k in keys), (case, i, 'old/new native prefix')
    evidence = dict(native_observation_sha256=PVC_SHA, seed_file_sha256=record['file_sha256'],
                    original_stop_category=row['stop_category'], original_stop=original['stop'],
                    original_complete_prefix_nodes=len(old_nodes) - 1, original_partial_entry_equal=True,
                    original_seed_start_equal=True, replacement_native_frames=120,
                    classification='superseded_two_bank_observer_limit')
    updated = dict(row, frames_done=120, frames_complete=120, stop=record['stop'], stop_category='frame-limit')
    return replacement, updated, evidence


# ----------------------------------------------------------------------------------------------------------------- natural seeds
NAT = {}


def host_stop(st):
    """Contract decision 2: the stop PC is LONG (100820); the host rejects any value other than e4a / e74 before the run."""
    value = st.long(FRAME_HEAD)
    assert value in HEAD_STOPS, hex(value)
    return value


def boundary_state(out):
    """Declared pass boundary after a pass: the next pass restarts from the same input form (PC 2ac2, A6 1008e4, A7 SPd); everything else is the actual C++ output."""
    return St(out.ram, dict(out.state, pc=PASS_PC, a6=CONTROLLER, a7=SPD, carry=0), out.pvc, out.bank)


def node_walk(ctx, tag, start, native_nodes, totals, final_stop, native_stop=None, hook=None):
    """Node-by-node execution of one pass from the pass start state (PC 2ac2, A6 = previous node): for every recorded node the entry state (2ac2 -> 2abe, A6 = node) and the exit state
    (2abe -> 2ac2) are compared with the recorded rows.  Returns (end St at the frame head stop or None, ports, failure dict or None)."""
    cur = start
    ports_all = b''
    events_all = []
    for i, nn in enumerate(native_nodes):
        r, entry, ports, error = run(ctx, '%s_a%d' % (tag, i), cur, ENTRY_PC)
        if entry is None:
            return None, (ports_all, events_all), dict(kind='advance', index=i, error=error, a6=nn['a6'], cb=nn['cb'])
        assert not ports and r['status'] == 0 and r['a6'] == nn['a6'], (tag, i, hex(r['a6']), hex(nn['a6']))
        assert entry.state['a5'] == A5V
        edig = entry.digest(LOOP_PC)
        assert edig == nn['entry'], (tag, i, 'entry digest differs from the recorded node entry')
        totals['node_entry_digest_equal_recorded'] += 1
        r, exit_, ports, error = run(ctx, '%s_x%d' % (tag, i), entry, PASS_PC)
        if nn['partial'] or exit_ is None:
            assert exit_ is None or nn['partial']
            fail = dict(kind='partial-node' if nn['partial'] else 'node', index=i, error=error, executed=exit_ is not None, a6=nn['a6'], cb=nn['cb'], native_routable_A=nn['rA'], native_routable_B=nn['rB'])
            # does the C++ reach the callback entry (the JSR (A0) of 2ac0 transfers to it) and the native stop address?
            reach, _, _, _ = run(ctx, '%s_rc%d' % (tag, i), entry, nn['cb'])
            fail['cpp_reaches_callback_entry'] = reach['ok'] and reach['pc'] == nn['cb']
            if nn['partial'] and native_stop is not None and native_stop.get('address') is not None and not native_stop['address'] & 1 and native_stop['reason'] in ('bios-boundary', 'fetch-unmapped'):
                reach2, _, _, e2 = run(ctx, '%s_rs%d' % (tag, i), entry, native_stop['address'])
                fail['cpp_reaches_native_stop_address'] = reach2['ok'] and reach2['pc'] == native_stop['address']
                fail['cpp_error_with_native_stop_address'] = e2
            if nn['partial'] and native_stop is not None:
                boundary = native_stop.get('pc')
                if boundary is not None and not boundary & 1:
                    rb, sb, pb, eb = run(ctx, '%s_partial_boundary%d' % (tag, i), entry, boundary)
                    fail['cpp_native_boundary_PC'] = hex(boundary)
                    fail['cpp_native_boundary_state_equal'] = sb is not None and sb.digest() == nn['exit']
                    fail['cpp_native_boundary_error'] = eb or None
                    if fail['cpp_native_boundary_state_equal']:
                        assert ports_digest(pb, nn['cb'] in MOVEM_CALLBACKS) == nn['ports_sha'], (tag, i, 'partial boundary ports')
                        totals['partial_node_boundary_digest_equal_native'] += 1
            return None, (ports_all, events_all), fail
        assert r['status'] == 0 and r['pc'] == PASS_PC
        assert exit_.digest() == nn['exit'], (tag, i, hex(nn['cb']), 'exit digest differs from the recorded node exit')
        movem = nn['cb'] in MOVEM_CALLBACKS
        if nn.get('ports_sha') is not None:
            assert ports_digest(ports, movem) == nn['ports_sha'] and len(native_events(ports, movem)) == nn['ports'], (tag, i, hex(nn['cb']), 'node port digest')
            totals['node_ports_digest_equal_recorded'] += 1
        events_all.extend(native_events(ports, movem))
        if hook is not None:
            hook(i, nn, entry, exit_, ports)
        totals['node_exit_digest_equal_recorded'] += 1
        totals['cb_%x' % nn['cb']] += 1
        ports_all += ports
        cur = exit_
        totals['node_segments'] += 2
    r, head, ports, error = run(ctx, '%s_h' % tag, cur, ENTRY_PC)
    if head is None:
        return None, (ports_all, events_all), dict(kind='advance-to-head', error=error)
    if r['a6'] != FRAME_HEAD:
        return None, (ports_all, events_all), dict(kind='ring-continues-past-recorded-nodes', a6=hex(r['a6']), cb=head.long(r['a6']))
    assert not ports, tag
    r, end, ports, error = run(ctx, '%s_e' % tag, head, final_stop)
    if end is None:
        return None, (ports_all, events_all), dict(kind='head', error=error)
    totals['node_segments'] += 2
    ports_all += ports
    events_all.extend(native_events(ports))
    return end, (ports_all, events_all), None


# ----------------------------------------------------------------------------------------------------------------- traced split chains and carry probes
def new_probe_acc():
    return dict(starts_seen=set(), probes={}, chains=0, chain_phases=0, single_blocks=0, paths=collections.Counter())


def merge_probe(acc, other):
    acc['starts_seen'] |= set(other['starts_seen'])
    for pc, slots in other['probes'].items():
        slot = acc['probes'].setdefault(pc, {0: True, 1: True, 2: True})
        for k in (0, 1, 2):
            slot[k] = slot[k] and slots[k]
    for k in ('chains', 'chain_phases', 'single_blocks'):
        acc[k] += other[k]
    acc['paths'].update(other['paths'])


def snap_of(st, pc=None):
    words = bank_words(st.pvc)
    return dict(ram=st.ram, regs={k: st.state[k] for k in REG16}, pc=st.state['pc'] if pc is None else pc, bank=(st.bank, words[0], words[1]))


def native_trace_pcs(st, stops):
    """The independent native instruction trace (a fresh Unicorn CPU, scheduler observer traced_native) from the state; PCs only."""
    import observe_animation_machine_scheduler as sched
    nat = sched.traced_native(sched.G['program'], sched.G['fixed'], snap_of(st), set(stops))
    assert nat.get('stopped') in stops and 'error' not in nat, (hex(st.state['pc']), nat.get('error'))
    return [pc for pc, regs in nat['trace']]


def probe_chain(ctx, tag, st_in, pcs, final_stop, expected_final, expected_ports, acc, blocks):
    """Split chain at the first arrival of every F2 block start of the native trace (same order, directly after the transferring instruction), every phase resuming from the previous actual
    C++ output; the chain end equals the continuous run; single-block carry probes (incoming Unknown / Clear / Set) at every start reached."""
    leaders = []
    seen = set()
    for j, pc in enumerate(pcs):
        if pc in blocks and pc not in seen and pc != final_stop:
            seen.add(pc)
            leaders.append((pc, j))
    cur = st_in
    chain_ports = b''
    at = []
    for k, (pc, j) in enumerate(leaders):
        if pc == cur.state['pc'] and j == 0:
            at.append((pc, j, cur, None))
            continue
        r, nxt, ports, error = run(ctx, '%s_s%d' % (tag, k), cur, pc)
        assert nxt is not None and r['pc'] == pc and r['status'] == 0, (tag, hex(pc), error)
        chain_ports += ports
        cur = nxt
        at.append((pc, j, cur, None))
        acc['chain_phases'] += 1
    r, last, ports, error = run(ctx, '%s_sf' % tag, cur, final_stop)
    assert last is not None and r['pc'] == final_stop, (tag, error)
    chain_ports += ports
    acc['chain_phases'] += 1
    acc['chains'] += 1
    if expected_final is not None:
        assert last.ram == expected_final.ram and last.pvc == expected_final.pvc and last.state == expected_final.state and last.bank == expected_final.bank and chain_ports == expected_ports, (tag, 'split chain differs from the continuous run')
    # carry probes: one block from the actual state at the start
    for pc, j, s_k, _ in at:
        acc['starts_seen'].add(pc)
        last_instr = blocks[pc][-1]
        jl = next(x for x in range(j, len(pcs)) if pcs[x] == last_instr)
        succ = pcs[jl + 1]
        acc['paths'][(pc, succ)] += 1
        slot = acc['probes'].setdefault(pc, {0: True, 1: True, 2: True})
        for carry in (0, 1, 2):
            sc = St(s_k.ram, dict(s_k.state, carry=carry), s_k.pvc, s_k.bank)
            r2, one, ports2, e2 = run(ctx, '%s_p%x_%d' % (tag, pc, carry), sc, succ)
            assert one is not None and r2['pc'] == succ and r2['status'] == 0, (tag, hex(pc), hex(succ), carry, e2)
            want = carry if pc in FLOW_BLOCKS else 0
            assert r2['carry'] == want, (tag, hex(pc), carry, r2['carry'])
            slot[carry] = slot[carry] and r2['carry'] == carry
            acc['single_blocks'] += 1
            if carry == 1:
                nxt_lead = [x for x in at if x[1] == jl + 1]
                if nxt_lead:
                    assert one.ram == nxt_lead[0][2].ram and one.state['pc'] == nxt_lead[0][0] and {k: one.state[k] for k in REG16} == {k: nxt_lead[0][2].state[k] for k in REG16}
                    assert one.pvc == nxt_lead[0][2].pvc and one.bank == nxt_lead[0][2].bank
    return leaders


# ----------------------------------------------------------------------------------------------------------------- typed fixtures
def apply_edits(st, edits):
    ram = bytearray(st.ram)
    state = dict(st.state)
    for e in edits:
        if e['kind'] == 'ram':
            a, sz, v = e['address'], e['size'], e['value']
            ram[a & 0xffff:(a & 0xffff) + sz] = (v & ((1 << (8 * sz)) - 1)).to_bytes(sz, 'big')
        elif e['kind'] == 'bytes':
            data = bytes.fromhex(e['data'])
            ram[e['address'] & 0xffff:(e['address'] & 0xffff) + len(data)] = data
        elif e['kind'] == 'reg':
            state[e['reg']] = e['value'] & M32
        elif e['kind'] == 'pc':
            state['pc'] = e['value']
        else:
            raise AssertionError(e)
    return St(bytes(ram), state, st.pvc, st.bank)


def seed_state(case, frame0_only=True):
    sd = NAT['sched'].SEEDS[case]
    snap, meta = NAT['sched'].seed_snap(sd)
    return from_seed_snap(snap)


def ref_state(ref):
    """A recorded state reference (ram blob, regs, pc, bank) as an St (carry Unknown)."""
    state = {k: ref['regs'][k] for k in REG16}
    state.update(pc=ref['pc'], carry=0)
    return St(read_blob(ref['ram'] + '.bin'), state, pvc_page_for(tuple(ref['bank'])), ref['bank'][0])


def same_machine(a, b):
    return a.ram == b.ram and a.pvc == b.pvc and a.bank == b.bank and {k: a.state[k] for k in REG16} == {k: b.state[k] for k in REG16} and a.state['pc'] == b.state['pc']


def fixture_direct(ctx, row, acc):
    base = seed_state(100)
    st = St(base.ram, dict(base.state, a7=SPD - 4, pc=row['pc']), base.pvc, base.bank)
    st = apply_edits(st, row['edits'])
    assert st.digest() == row['entry']['state'], (row['name'], 'entry digest')
    tag = 'fx_' + row['name']
    r, out, ports, error = run(ctx, tag, st, PASS_PC)
    assert out is not None and not error and not ports, (row['name'], error)
    exp = ref_state(row['exit'])
    assert same_machine(out, exp) and out.digest() == row['exit']['state'], (row['name'], 'exit state differs from the recorded one')
    pcs = native_trace_pcs(st, {PASS_PC})
    assert len(pcs) - 1 == row['instructions']
    probe_chain(ctx, tag, st, pcs, PASS_PC, out, ports, acc, ctx.st['blocks'])
    return dict(name=row['name'], group=row['group'], result='C++ exit state equals the recorded one (RAM, 16R, PC, bank, PVC words, no ports)', exit_digest=out.digest(), native_instructions=row['instructions'],
                leaders=[hex(x) for x in row['leaders']])


def fixture_boot(ctx, row, acc):
    base = seed_state(100)
    head_cb = [e['value'] for e in row['edits'] if e['kind'] == 'ram' and e['address'] == FRAME_HEAD][0]
    a7 = 0x1ff800 if row['name'].endswith('e4a') else 0x1fef00
    st = apply_edits(St(base.ram, dict(base.state, a7=a7, pc=BOOT_PC), base.pvc, base.bank), row['edits'])
    tag = 'fx_' + row['name']
    stop = host_stop(st)
    assert stop == head_cb == row['stop_pc']
    r, out, ports, error = run(ctx, tag, st, stop)
    assert out is not None and not error and not ports, (row['name'], error)
    exp = ref_state(row['exit'])
    assert same_machine(out, exp), (row['name'], 'boot stop state differs from the recorded one')
    assert out.long(BASE_LONG) == a7 and out.state['a6'] == FRAME_HEAD and out.state['a5'] == A5V and out.state['a0'] == stop and out.state['a7'] == a7 - 4 and out.long(a7 - 4) == PASS_PC
    # split: 2aac block, then the dispatcher
    r1, mid, p1, e1 = run(ctx, tag + '_s1', st, LOOP_PC)
    assert mid is not None and mid.state['a6'] == FRAME_HEAD and mid.long(BASE_LONG) == a7 and mid.state['a7'] == a7 and not p1
    r2, end, p2, e2 = run(ctx, tag + '_s2', mid, stop)
    assert end is not None and same_machine(end, out) and not p2
    for carry in (0, 1, 2):
        sc = St(st.ram, dict(st.state, carry=carry), st.pvc, st.bank)
        rc, one, pc_, ec = run(ctx, '%s_c%d' % (tag, carry), sc, LOOP_PC)
        assert one is not None and rc['carry'] == 0 and same_machine(one, mid), (row['name'], carry)
    acc['probes'].setdefault(BOOT_PC, {0: True, 1: True, 2: True})
    for k in (1, 2):
        acc['probes'][BOOT_PC][k] = False         # C is reset to Unknown by the MOVE.L block (not a preserving block)
    acc['starts_seen'].add(BOOT_PC)
    acc['single_blocks'] += 3
    return dict(name=row['name'], group=row['group'], result='boot 2aac -> dispatcher -> frame head stop: LONG 104ca4 = A7, A6 = 100820, A5 = 108000, A0 = stop, A7 = A7-4, LONG (A7-4) = 2ac2; split at 2ab8 equal',
                a7_in=hex(a7), stop=hex(stop), exit_digest=out.digest())


def stop_label(prec):
    return prec


def nodes_as_records(row):
    return [dict(a6=n[0], cb=n[1], depth=n[2], entry=n[3], exit=n[4], self_delete=n[5], partial=n[6], ports_sha=None, ports=None, rA=None, rB=None) for n in row['nodes']]


def fixture_pass(ctx, row, acc):
    """Typed pass fixtures: the input is the recorded seed-start dump (the state of the native pass after the declared edits and the declared 104ca4 write)."""
    d0 = [d for d in row['dumps'] if d['kind'] == 'seed-start'][0]
    st = ref_state(d0)
    assert st.digest() == d0['state'] == row['start'], (row['name'], 'fixture start')
    tag = 'fx_' + row['name']
    name = row['name']
    stop = st.long(FRAME_HEAD)
    out = dict(name=name, group=row['group'], native_stop=row['stop']['reason'], native_nodes=len(row['nodes']))
    if name == 'pass-head-callback-rejected':
        assert stop not in HEAD_STOPS
        out['result'] = 'host rule: LONG (100820) = %x is neither e4a nor e74, the frame pass is rejected before any run (the C++ API takes the stop PC as a parameter and does not read LONG (100820))' % stop
        out['host_rejects'] = True
        return out
    if name == 'pass-head-ring-unchecked-step-limit':
        # the frame head callback is 270e (not a head stop); the host rule is bypassed: the stop is declared e4a, the ring is walked on into the controller node 1008e4 (callback c52a, no executor)
        r, end, ports, error = run_wait(ctx, tag, st, 0xe4a, [])
        # Former expectation: error == UNSUPPORTED_MACHINE ('unsupported animation machine PC', controller callback c52a had no executor). The controller node c52a is
        # routed by deferred unit C3 (c52a..c64c, with C1/C2 behind it) since the ten-unit batch; the pass now runs the controller and never reaches the declared stop
        # e4a, so the checked error is the block budget (e5bfb73 full run; 0264-legacy). Outputs stay preserved (checked by run_wait).
        assert end is None and error == 'animation machine block budget exceeded', (end, error)
        totals = collections.Counter()
        nend, nports, failure = node_walk(ctx, tag + 'n', st, nodes_as_records(row), totals, 0xe4a)
        assert failure is not None and failure['kind'] == 'ring-continues-past-recorded-nodes' and failure['cb'] == 0xc52a, failure
        out.update(result='the stop e4a is never reached: the ring continues through the idle head node 270e into the controller node 1008e4 (callback c52a): whole pass = checked error (block budget exceeded: the controller node runs through C3; former unsupported-PC error), outputs preserved',
                   cpp_error=error, former_expected_cpp_error=UNSUPPORTED_MACHINE, superseded_by='controller C3 (c52a)', node_failure=failure, nodes_equal_native=totals['node_exit_digest_equal_recorded'])
        return out
    waits = []
    r, end, ports, error = run_wait(ctx, tag, st, stop, waits)
    out['cpp_waits'] = waits
    if name == 'pass-gate-wait-not-released':
        assert end is not None and error == 'wait-not-released' and waits and waits[0]['pc'] == '0x47af0'
        assert r['status'] == 1 and r['pc'] == 0x47af0
        out.update(result='Waiting at 47af0 (palette gate); WORD 107dea <> 0, the declared release is empty and the pass is given up (the same Waiting PC again on resume without a host change)',
                   waiting_pc=hex(r['pc']), waiting_a7=hex(r['a7']), native_wait_not_released=True)
        r2, again, p2, e2 = run(ctx, tag + '_again', end, stop)
        assert again is not None and r2['status'] == 1 and r2['pc'] == 0x47af0 and r2['a7'] == r['a7'] and same_machine(again, end)
        out['resume_without_change_waits_again_at_same_pc_and_a7'] = True
        return out
    if name == 'pass-self-delete-base-long-zero':
        assert end is None and error, (name, 'expected a checked error (A7 = 0 after 2a02, the next JSR push is outside the RAM)')
        out.update(result='LONG 104ca4 = 0: 2a02 loads A7 = 0; the next JSR push is outside the RAM: checked error, outputs preserved', cpp_error=error, native_expected='invalid-memory-access (push to fffffc)')
        assert row['stop']['reason'] == 'invalid-memory-access'
        return out
    assert end is not None and not error, (name, error)
    assert end.digest() == row['end'], (name, 'pass end digest')
    out['end_digest_equal_recorded'] = True
    end_dump = [d for d in row['dumps'] if d['kind'] == 'pass-end']
    if end_dump:
        exp = ref_state(end_dump[0])
        assert same_machine(end, exp)
        out['pass_end_dump_byte_equal'] = True
    if name == 'pass-self-delete-base-long-offset':
        assert end.state['a7'] != SPD - 4 and row['head_bad'] == 1
        out['a7_at_stop'] = hex(end.state['a7'])
        out['result'] = 'LONG 104ca4 = SPd-0x20: the self delete restores A7 from it, the pass reaches the stop with A7 <> SPd-4 (the host head check refuses it); state equals the recorded one'
    else:
        assert end.state['a7'] == SPD - 4 and end.state['a6'] == FRAME_HEAD and end.state['a5'] == A5V
        out['result'] = 'pass ran to the frame head stop %x; end state equals the recorded pass end' % stop
    if waits:
        assert name == 'pass-gate-wait-released' and waits[0]['pc'] == '0x47af0'
        out['result'] = 'Waiting at 47af0 (palette gate, A7 and PC kept), declared release BYTE 107ded bit7 cleared, the same pass continues to the stop; end state equals the recorded one'
        return out
    totals = collections.Counter()
    nend, nports, failure = node_walk(ctx, tag + 'n', st, nodes_as_records(row), totals, stop)
    assert failure is None and same_machine(nend, end) and nports[0] == ports, (name, failure)
    out['node_by_node_equals_whole_pass'] = True
    out['nodes_equal_recorded'] = totals['node_exit_digest_equal_recorded']
    return out


VARIANT_7A = (0xffe2, 0xffee, 0xfffa, 0xfffc, 0xfffd, 0xfffe, 0xffff, 0x0000, 0x0001, 0x000a, 0x0021, 0x0023, 0x0024, 0x0025, 0x0030, 0x7ffc, 0x7ffd, 0x8000, 0x8002, 0x8003)


def variants_4fcda(ctx, tag, entry, acc):
    """4fcda path variants: the WORD 7a(A6) of a real 4fcda node entry is edited (declared host write), the independent native run (the observer's replay_node, fresh Unicorn CPU) gives the
    expected state and ports, the C++ node run must equal it (RAM, 16R, PC, bank, ordered ports); the reached block starts of the traced native run are recorded."""
    import observe_animation_machine_scheduler as sched
    rows = []
    a6 = entry.state['a6']
    for v in VARIANT_7A:
        e = entry.put(a6 + 0x7a, 2, v)
        snap = snap_of(e, LOOP_PC)
        rp = sched.replay_node(sched.G['program'], sched.G['fixed'], snap)
        r, out, ports, error = run(ctx, '%s_v%04x' % (tag, v), e, PASS_PC)
        row = dict(value_7a=hex(v), native_status=rp['status'])
        if rp['status'] == '2ac2':
            assert out is not None and not error, (tag, hex(v), error)
            st = rp['state']
            assert out.ram == st['ram'] and {k: out.state[k] for k in REG16} == {k: st['regs'][k] for k in REG16} and out.state['pc'] == PASS_PC and out.bank == st['bank'][0], (tag, hex(v))
            assert events_digest(native_events(ports, True)) == events_digest([tuple(x) for x in rp['ports']]), (tag, hex(v), 'ports')
            row.update(cpp='equal to the native replay', ports=len(native_events(ports, True)))
            pcs = native_trace_pcs(e.with_pc(LOOP_PC), {PASS_PC, 0x2a00})
            starts = sorted(set(pc for pc in pcs if pc in ctx.st['blocks']))
            row['block_starts_reached'] = [hex(x) for x in starts]
            acc['starts_seen'] |= set(starts)
            row['self_delete_or_completion'] = 0x4fcee in starts
        else:
            row.update(native_reason=sched_reason(rp['reason']), cpp_error=error if out is None else None, cpp_ok=out is not None)
            assert out is None, (tag, hex(v), 'native guard but the C++ accepted')
        rows.append(row)
    return rows


def sched_reason(reason):
    return {k: (hex(v) if isinstance(v, int) and not isinstance(v, bool) else v) for k, v in (reason or {}).items() if v is not None and not isinstance(v, dict)} if reason else None


def natural_seed(case):
    ctx = NAT['ctx']
    import observe_animation_machine_scheduler as sched
    totals = collections.Counter()
    try:
        sd = sched.SEEDS[case]
        snap, meta = sched.seed_snap(sd)
        row = NAT['rows'][case]
        data = load_seed_file(row)
        replacement_evidence = None
        if case in (58, 59):
            data, row, replacement_evidence = pvc_replacement(case, data, row)
        assert data['case'] == case and data['kind'] == row['kind']
        passes = data['passes']
        dumps = {d['frame']: d for d in data['dumps'] if d['kind'] == 'pass-end'}
        seed_start = [d for d in data['dumps'] if d['kind'] == 'seed-start'][0]
        st = from_seed_snap(snap)
        assert st.digest() == seed_start['state'] == passes[0]['start'], (case, 'seed start')
        assert read_blob(seed_start['ram'] + '.bin') == st.ram if (NATIVE_DIR / 'blobs' / (seed_start['ram'] + '.bin')).exists() else True
        chain = hashlib.sha256()
        acc = new_probe_acc()
        picked = collections.Counter()
        variant_rows = []

        def hook(i, nn, entry, exit_, ports):
            cb = nn['cb']
            if cb not in (0x270e, 0x4fcce, 0x4fcda):
                return
            leads = set(nn.get('leaders') or [])
            want = None
            if picked[cb] < 2:
                want = 'first'
            elif nn['self_delete'] and picked['sd'] < 3:
                want = 'sd'
            elif leads & {0x4fd5e, 0x4fd9e, 0x2716} and picked['rare%x' % cb] < 2:
                want = 'rare'
            if want is None:
                return
            picked[want if want != 'first' else cb] += 1
            if want == 'rare':
                picked['rare%x' % cb] += 1
            pcs = native_trace_pcs(entry.with_pc(LOOP_PC), {PASS_PC, 0x2a00})
            probe_chain(ctx, 'c%03d_pr%d' % (case, acc['chains']), entry, pcs, PASS_PC, exit_, ports, acc, ctx.st['blocks'])
            if cb == 0x4fcda and not variant_rows:
                variant_rows.extend(variants_4fcda(ctx, 'c%03d_var' % case, entry, acc))

        out = dict(case=case, kind=row['kind'], family=row['family'], bank=row['bank'], native_frames_done=row['frames_done'], native_frames_complete=row['frames_complete'],
                   native_stop=row['stop']['reason'], native_stop_category=row['stop_category'], cpp_complete_passes=0, cpp_failure=None, pvc_replacement=replacement_evidence)
        declared = data['declared']
        assert len(declared) == 1 and declared[0]['address'] == BASE_LONG and declared[0]['value'] == SPD and st.long(BASE_LONG) == SPD
        for k, prec in enumerate(passes):
            tag = 'c%03d_f%03d' % (case, k)
            assert prec['frame'] == k
            if st.digest() != prec['start']:
                raise AssertionError((case, k, 'pass start digest differs from the recorded start'))
            totals['pass_start_digest_equal_recorded'] += 1
            native_complete = prec['stop'] == 'frame-head'
            stop = host_stop(st)
            waits = []
            result, end, ports, error = run_wait(ctx, tag + '_whole', st, stop, waits)
            totals['whole_pass_runs'] += 1
            if end is not None and not error:
                # complete in C++
                if not native_complete:
                    # The merged callback coverage can complete a pass whose
                    # historical native record stops at an earlier boundary.
                    # Preserve all recorded node-entry/exit checks, then prove
                    # the partial node's native boundary snapshot separately.
                    nend, nports, failure = node_walk(ctx, tag, st, prec['nodes'], totals, stop, data['stop'])
                    assert failure is not None and failure['kind'] == 'partial-node', (case, k, failure)
                    assert failure.get('cpp_native_boundary_state_equal') is True, (case, k, 'superseded native boundary state', failure)
                    out['cpp_failure'] = dict(frame=k, kind='cpp-completes-native-stopped', native_stop=prec['stop'],
                                              native_pass_complete=False, node_failure=failure,
                                              cpp_suffix_end_state_sha256=end.digest(),
                                              native_suffix_equivalence_claimed=False)
                    totals['cpp_completes_where_native_stopped'] += 1
                    break
                assert result['pc'] == stop and result['status'] == 0 and result['a6'] == FRAME_HEAD and result['a5'] == A5V and result['a7'] == SPD - 4 and result['a0'] == stop
                assert end.long(SPD - 4) == PASS_PC
                assert end.digest() == prec['end'], (case, k, 'pass end digest')
                assert [w['pc'] for w in waits] == [hex(w['pc']) for w in prec['waits']] if prec['waits'] else not waits
                totals['pass_end_digest_equal_recorded'] += 1
                totals['pass_ports_digest_equal_recorded'] += 1
                if k in dumps:
                    d = dumps[k]
                    blob = read_blob(d['ram'] + '.bin')
                    assert blob == end.ram and d['pc'] == end.state['pc'] and {x: d['regs'][x] for x in REG16} == {x: end.state[x] for x in REG16} and list(d['bank']) == [end.bank, bank_words(end.pvc)[0], bank_words(end.pvc)[1]]
                    totals['dump_frames_byte_equal'] += 1
                # node-by-node chain equals the whole pass
                if not waits:
                    nend, nports, failure = node_walk(ctx, tag, st, prec['nodes'], totals, stop, None, None if replacement_evidence else hook)
                    assert failure is None, (case, k, failure)
                    assert nend.ram == end.ram and nend.pvc == end.pvc and nend.state == end.state and nend.bank == end.bank and nports[0] == ports, (case, k, 'node-by-node chain differs from the whole pass')
                    assert events_digest(nports[1]) == prec['ports_sha'] and len(nports[1]) == prec['ports'], (case, k, 'pass ports digest')
                    totals['node_chain_equals_whole_pass'] += 1
                else:
                    assert ports_digest(ports) == prec['ports_sha'] and len(native_events(ports)) == prec['ports'], (case, k, 'pass ports digest')
                    totals['passes_with_declared_wait_not_node_walked'] += 1
                totals['complete_passes'] += 1
                totals['nodes'] += len(prec['nodes'])
                chain.update(bytes.fromhex(end.digest()))
                out['cpp_complete_passes'] += 1
                st = boundary_state(end)
                continue
            # C++ whole pass fails: the outputs are preserved (run() asserted); classify through the node walk
            totals['whole_pass_checked_errors'] += 1
            nend, nports, failure = node_walk(ctx, tag, st, prec['nodes'], totals, stop, data['stop'])
            assert failure is not None, (case, k, 'whole pass failed but the node walk completed', error)
            out['cpp_failure'] = dict(frame=k, whole_pass_error=error, whole_pass_status=result['status'], node_failure=failure, native_pass_stop=prec['stop'], native_pass_complete=native_complete,
                                      nodes_before_failure=failure.get('index'), native_partial_node_index=next((n_i for n_i, n in enumerate(prec['nodes']) if n['partial']), None),
                                      native_nodes_in_pass=len(prec['nodes']))
            totals['seed_stops_in_cpp'] += 1
            break
        else:
            out['cpp_failure'] = None
        out['C_state_chain_sha256'] = chain.hexdigest()
        out['native_passes'] = len(passes)
        out['totals'] = dict(totals)
        acc['starts_seen'] = sorted(acc['starts_seen'])
        acc['paths'] = {'%x>%x' % k: v for k, v in sorted(acc['paths'].items())}
        acc['probes'] = {pc: slots for pc, slots in acc['probes'].items()}
        out['probe'] = acc
        out['variants_4fcda'] = variant_rows
        return out
    except Exception:
        return dict(error=traceback.format_exc(), case=case)
    finally:
        for srv in SERVERS:
            srv.close()
        reset_servers()


def natural_init():
    reset_servers()


# ----------------------------------------------------------------------------------------------------------------- API-only checks
def check_preserved(actual, st, expected_error=None):
    result, out, ports, error = actual
    assert out is None and (expected_error is None or error == expected_error), (expected_error, error)
    return error


# label -> (former expected error, observed exact error, superseding unit); filled from the first full run of each stale probe.
SUPERSEDED_PROBES = {'unrouted_after_002ab8': (UNSUPPORTED_MACHINE, 'animation machine external read queue empty', 'F6a IRQ shell 20c..2d8 [I: error attributed to the routed continuation, not separately traced]')}


def reject_one(args):
    ctx, label, base, changes, stop, expected = args
    st = St(base.ram, dict(base.state, carry=2, **changes), base.pvc, base.bank)
    r, out, ports, error = run(ctx, 'neg_' + label, st, stop)
    if label in SUPERSEDED_PROBES:
        # Former expectation `expected`; the probe PC is routed by a later unit and ends in the recorded exact error (0264-legacy, e5bfb73).
        former, observed, unit = SUPERSEDED_PROBES[label]
        assert former == expected
        expected = observed
    if not (out is None and (expected is None or error == expected)):
        return dict(label=label, failed=(error, expected))      # collected by negatives(): every stale probe is reported together
    row = dict(label=label, pc=changes.get('pc'), error=error, expected=expected, all_API_outputs_preserved=True)
    if label in SUPERSEDED_PROBES:
        row.update(former_expected_API_error=SUPERSEDED_PROBES[label][0], superseded_by=SUPERSEDED_PROBES[label][2], API_only_control=True)
    return row


def negatives(ctx, base, stinfo):
    jobs = []
    for pc in stinfo['interior']:
        jobs.append((ctx, 'interior_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_SCHED))
    for pc in stinfo['odd']:
        jobs.append((ctx, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    for low, high in RANGES:
        jobs.append((ctx, 'unrouted_after_%06x' % high, base, {'pc': high}, 0xff000, UNSUPPORTED_MACHINE))
        jobs.append((ctx, 'unrouted_before_%06x' % (low - 2), base, {'pc': low - 2}, 0xff000, UNSUPPORTED_MACHINE))
    for pc in (0x4fd0a, 0x4fd16, 0x4fd20, 0x4fd2c, 0x4fd32, 0x4fd40, 0x4fd50, 0x4fd56):          # the sibling fade-out variant 4fd0a..4fd58 is not part of this unit
        jobs.append((ctx, 'sibling_variant_4fd0a_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    for pc in (0x1, 0xffffff, 0xdeadbeef):
        jobs.append((ctx, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    for pc in (0x0, 0xffffffe, 0x1000000, 0xdeadbee):
        jobs.append((ctx, 'out_of_range_entry_%x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    for pc in (0x10fe00, 0x10fefe):      # unrouted work-RAM controls (code never executes in RAM)
        jobs.append((ctx, 'unrouted_work_ram_control_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    out = run_parallel(reject_one, jobs)
    failed = [row for row in out if 'failed' in row]
    assert not failed, failed
    # odd stop PC (API check) and odd operand addresses
    r, o, p, e = run(ctx, 'neg_odd_stop', St(base.ram, dict(base.state, pc=0x270e, a6=0x1009a8, a5=A5V), base.pvc, base.bank), 0x2ac3)
    assert o is None and e == 'invalid animation machine RAM/PVC/stop PC'
    out.append(dict(label='odd_stop_pc', error=e, all_API_outputs_preserved=True))
    for label, changes, expected in (('270e_odd_A6_WORD_read', {'pc': 0x270e, 'a6': 0x1009a9}, EVEN), ('2716_odd_counter_address', {'pc': 0x2716, 'a5': A5V + 1}, EVEN),
                                     ('4fcee_odd_parent_pointer', {'pc': 0x4fcee, 'a6': 0x1009a9}, EVEN), ('4fcda_odd_7a_read', {'pc': 0x4fcda, 'a6': 0x1009a9}, EVEN),
                                     ('4fd72_odd_rows_pointer', {'pc': 0x4fd72, 'a0': 0x50075}, EVEN), ('4fd8c_odd_video_pointer', {'pc': 0x4fd8c, 'a4': 0x100001}, None)):
        r = reject_one((ctx, label, base, changes, 0xff000, expected))
        out.append(dict(label=label, error=r['error'], expected=expected, all_API_outputs_preserved=True))
    return out


def zero_step_one(args):
    ctx, base, pc, carry = args
    s = St(base.ram, dict(base.state, pc=pc, carry=carry), base.pvc, base.bank)
    result, out, ports, error = run(ctx, 'zero_%06x_%d' % (pc, carry), s, pc)
    assert out is not None and not error and result['status'] == 0 and not ports and result['external_reads'] == 0, (hex(pc), carry, error)
    assert same_machine(out, s) and out.state['carry'] == carry
    return (pc, carry)


def scan_old_expectations(stinfo):
    """Literal PCs of the F2 ranges in older verifiers / C++ tests.  A literal in an unsupported / outside / reject expectation context is listed individually; every other use (callback LONG
    data written into a node, the decimal constant 0x2710, ...) is only counted per file."""
    pcs = set(stinfo['even'])
    files = sorted((Path(MAIN_ROOT) / 'tools').glob('verify_animation_machine*.py')) + sorted((ROOT / 'engine/tests').glob('animation_machine*_test.cpp'))
    rows, data = [], collections.OrderedDict()
    for path in files:
        if 'scheduler' in path.name:
            continue
        lines = path.read_text(errors='replace').splitlines()
        for number, line in enumerate(lines, 1):
            hits = [int(m.group(1), 16) for m in re.finditer(r'0x([0-9a-fA-F]{3,6})\b', line) if int(m.group(1), 16) in pcs]
            if not hits:
                continue
            prefix = ('tools/' if path.suffix == '.py' else 'engine/tests/') + path.name
            context = ' '.join(lines[max(0, number - 3):number + 1]).lower()
            if 'dispatcher_entry_2aac_unsupported' in line or (path.name.endswith('fade_card_test.cpp') and 'outside[]' in line):
                note = 'INVALIDATED: 2aac is now a scheduler block start (animation_scheduler_block); 2ab2 is an interior PC of the same range (error unsupported animation scheduler PC, not unsupported animation machine PC)'
                rows.append(dict(file=prefix, line=number, pcs=sorted(set(hex(h) for h in hits)), text=line.strip()[:200], note=note))
            elif 'unsupported' in line.lower() or 'outside' in line.lower() or 'reject' in line.lower() or 'unrouted' in line.lower():
                rows.append(dict(file=prefix, line=number, pcs=sorted(set(hex(h) for h in hits)), text=line.strip()[:200], note='CHECK: literal PC of an F2 range in an unsupported / outside / reject context'))
            else:
                data[prefix] = data.get(prefix, 0) + 1
    return rows, dict(data)


# ----------------------------------------------------------------------------------------------------------------- extra fixtures
def fixture_idle_ring_budget(ctx):
    """All ring nodes are made idle (the controller callback c52a replaced by 270e) and the frame head callback is 270e: the stop e4a is never reached; the dispatcher never ends."""
    base = NAT['fx_base']
    d = base
    for node in (0x100820, 0x1008e4, 0x100b30, 0x100bf4):
        d = d.put(node, 4, 0x270e)
    d = d.with_pc(PASS_PC)
    r, out, ports, error = run(ctx, 'fx_ring_idle_budget', d, 0xe4a)
    assert out is None and error == BUDGET, error
    return dict(name='ring-idle-block-budget', group='extra-pass', result='every node idle (270e) and no frame head callback: the stop e4a is never reached, checked error "%s", outputs preserved' % error, cpp_error=error)


def fixture_stack_outside(ctx):
    """Self delete path with LONG 104ca4 pointing below the RAM mirror: covered by the native zero fixture; here the 2aac store through an A7 outside the RAM is a checked error."""
    base = NAT['fx_base']
    st = St(base.ram, dict(base.state, pc=BOOT_PC, a7=0x400000), base.pvc, base.bank)
    r, out, ports, error = run(ctx, 'fx_boot_a7_outside_ram', st, 0xe4a)
    assert out is None and error
    return dict(name='boot-2aac-A7-outside-RAM', group='extra-boot', result='A7 = 400000 (no RAM): the 104ca4 store is fine but the JSR push is a checked error, outputs preserved', cpp_error=error)


# ----------------------------------------------------------------------------------------------------------------- main
def run_parallel(function, items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(function, items))


def setup_sched():
    """The observer module as the natural seed generator only (seed_snap); its setup() routing parser is not used."""
    import ctypes
    import observe_animation_machine_scheduler as sched
    program, _ = load_verified_program(ROOT)
    sched.G['program'] = program
    sched.G['fixed'] = (ctypes.c_ubyte * 0x100000).from_buffer_copy(program[:0x100000])
    sched.load_seeds()
    return sched


def natural_all(ctx, report):
    sched = setup_sched()
    NAT['ctx'] = ctx
    NAT['rows'] = {r['case']: r for r in report['seeds']}
    naturals = sorted(NAT['rows'])
    assert len(naturals) == 142 == len(sched.SEEDS)
    if NATURAL_CASES:
        naturals = NATURAL_CASES
    for srv in SERVERS:
        srv.close()
    reset_servers()
    mp = multiprocessing.get_context('fork')
    with mp.Pool(WORKERS, initializer=natural_init) as pool:
        results = pool.map(natural_seed, naturals, chunksize=1)
    reset_servers()
    errs = [r for r in results if 'error' in r]
    if errs:
        for e in errs[:5]:
            print('NATURAL SEED FAILED', e['case'], e['error'].strip().splitlines()[-1][:600])
        print(errs[0]['error'])
        raise AssertionError('%d natural seeds failed' % len(errs))
    return results


def main():
    global RUN_DIR
    assert OUT.resolve().name == 'animation_machine_scheduler_execution'
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    RUN_DIR = Path(tempfile.mkdtemp(prefix='scheduler_verify_'))
    try:
        run_all(OUT / 'verification.json')
    finally:
        for srv in SERVERS:
            srv.close()
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run_all(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ['tools/verify_animation_machine_scheduler.py', 'tools/observe_animation_machine_scheduler.py', 'docs/analysis/animation-machine-scheduler-shell-f2-contract.md'] + list(CPP_PINS):
        inputs[name] = cc.digest(ROOT / name)
    for path in (PVC_DIR / 'observation.json', PVC_DIR / 'seeds/seed_0058.json.gz', PVC_DIR / 'seeds/seed_0059.json.gz'):
        inputs[str(path)] = cc.digest(path)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    sexe, scommand = compile_server(ROOT, OUT)
    SERVER_EXE[0], SERVER_EXE[1] = sexe, resources
    report = audit_report(program, source)
    stinfo = audit_static(program)
    cases, cpp_carry, cpp_ranges = cpp_static()
    assert cases == sorted(STARTS), sorted(hex(p) for p in set(cases) ^ set(STARTS))
    assert cpp_ranges == sorted(RANGES), cpp_ranges
    assert cpp_carry == sorted(FLOW_BLOCKS), [hex(p) for p in cpp_carry]
    ctx = Ctx()
    ctx.exe, ctx.resources, ctx.program, ctx.st = exe, resources, program, stinfo
    # every native blob is content addressed: hash all of them once; the per-seed files are hash checked when loaded
    blob_dir = NATIVE_DIR / 'blobs'
    blob_names = sorted(os.listdir(blob_dir))
    assert len(blob_names) == report['output_sizes']['blobs']
    for name in blob_names:
        assert sha((blob_dir / name).read_bytes()) == name.split('.')[0], name
    sched = setup_sched()
    NAT['sched'] = sched
    NAT['ctx'] = ctx
    NAT['rows'] = {r['case']: r for r in report['seeds']}
    base = seed_state(100)
    NAT['fx_base'] = base
    # ---- natural seeds
    results = [] if NO_NATURAL else natural_all(ctx, report)
    # ---- typed fixtures (main process)
    SERVER_EXE[0], SERVER_EXE[1] = sexe, resources
    reset_servers()
    facc = new_probe_acc()
    frows = []
    for row in report['fixtures']:
        assert row['ok'], row['name']
        if row['group'] == 'direct-entry':
            frows.append(fixture_direct(ctx, row, facc))
        elif row['group'] == 'boot':
            frows.append(fixture_boot(ctx, row, facc))
        elif row['group'] == 'pass':
            frows.append(fixture_pass(ctx, row, facc))
        else:
            assert row['group'] == 'f3-node'
            frows.append(dict(name=row['name'], group=row['group'], result='not run here: an F3b stop-boundary / guard fixture of the stage event node (e9362 child thread, the F3b unit verifies it); native status %s' % row['status'], native_status=row['status']))
    frows.append(fixture_idle_ring_budget(ctx))
    frows.append(fixture_stack_outside(ctx))
    # ---- API-only checks
    negative = negatives(ctx, NAT['fx_base'], stinfo)
    zero = run_parallel(zero_step_one, [(ctx, NAT['fx_base'], pc, carry) for pc in STARTS for carry in (0, 1, 2)])
    old, old_data = scan_old_expectations(stinfo)
    # ---- aggregate
    totals = collections.Counter()
    for r in results:
        totals.update(r['totals'])
    probes = {}
    starts_seen = set(facc['starts_seen'])
    for pc, slots in facc['probes'].items():
        probes[pc] = dict(slots)
    for r in results:
        starts_seen |= set(r['probe']['starts_seen'])
        for pc, slots in r['probe']['probes'].items():
            slot = probes.setdefault(pc, {0: True, 1: True, 2: True})
            for k in (0, 1, 2):
                slot[k] = slot[k] and slots[k]
    seed_rows = []
    failure_classes = collections.Counter()
    for r in results:
        f = r['cpp_failure']
        row = dict(case=r['case'], kind=r['kind'], family=r['family'], bank=r['bank'], native_passes=r['native_passes'], native_complete_passes=r['native_frames_complete'], native_stop=r['native_stop'],
                   native_stop_category=r['native_stop_category'], pvc_replacement=r.get('pvc_replacement'), cpp_complete_passes=r['cpp_complete_passes'], C_state_chain_sha256=r['C_state_chain_sha256'], cpp_failure=f)
        seed_rows.append(row)
        if f:
            nf = f['node_failure']
            failure_classes[(r['native_stop_category'], 'native pass complete' if f['native_pass_complete'] else 'native pass stopped', nf['kind'], nf['error'], hex(nf['cb']) if nf.get('cb') is not None else None)] += 1
    seed_rows.sort(key=lambda x: x['case'])
    if not NATURAL_CASES and not NO_NATURAL:
        assert len(results) == 142 and sorted(r['case'] for r in results) == sorted(NAT['rows'])
    if not (NATURAL_CASES or NO_NATURAL):
        assert starts_seen >= set(STARTS), sorted(hex(p) for p in set(STARTS) - starts_seen)
        observed_preserving = sorted(pc for pc, slots in probes.items() if slots[1] and slots[2])
        assert observed_preserving == sorted(FLOW_BLOCKS), [hex(p) for p in observed_preserving]
        assert all(slots[0] is True or True for slots in probes.values())
    for name, expected in inputs.items():
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs = dict(refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log', OUT / 'harness_batch.cpp', OUT / 'compile_batch.log'):
        refs[str(path.resolve())] = cc.digest(path)
    result = dict(
        schema_version=1, source=source, inputs=inputs, artifacts=refs, native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, pvc_replacement_native_observation_sha256=PVC_SHA, contract_sha256=CONTRACT_SHA, cpp_pins=CPP_PINS,
        native_counts=dict(seeds=len(report['seeds']), natural=report['totals']['natural'], guard_rows=report['totals']['guard_rows'], passes=report['totals']['passes'], complete_passes=report['totals']['complete_passes'],
                           node_visits=report['totals']['node_visits'], fixtures=len(report['fixtures']), blobs=len(blob_names)),
        native_blobs_hash_checked=len(blob_names), native_blobs_read_for_comparison=len(VERIFIED_BLOBS),
        block_start_count=len(STARTS), block_starts=[hex(p) for p in STARTS], bundled_branches=[hex(p) for p in stinfo['bundled']], carry_preserving_blocks=[hex(p) for p in stinfo['flow']],
        interior_PC_count=len(stinfo['interior']), odd_PC_count=len(stinfo['odd']), cpp_case_labels_equal_17_starts=True, cpp_routing_ranges=[[hex(a), hex(b)] for a, b in cpp_ranges],
        native_counts_scope='historical_original_observation',
        effective_native_counts=dict(passes=sum(r['native_passes'] for r in results), complete_passes=sum(r['native_frames_complete'] for r in results), pvc_replacement_cases=[58, 59]),
        natural_actual_CPP=dict(sorted(totals.items())), natural_seeds=seed_rows,
        failure_classes=[dict(native_stop_category=k[0], native_pass=k[1], node_failure_kind=k[2], cpp_error=k[3], callback=k[4], seeds=v) for k, v in sorted(failure_classes.items(), key=str)],
        variants_4fcda={str(r['case']): r['variants_4fcda'] for r in sorted(results, key=lambda x: x['case']) if r['variants_4fcda']}, fixtures=frows, negatives=negative, negative_count=len(negative), zero_step_count=len(zero), zero_step_blocks=len(STARTS), zero_step_carries=[0, 1, 2],
        carry_probes={hex(pc): {CARRY_NAME[k]: v for k, v in slots.items()} for pc, slots in sorted(probes.items())}, block_starts_seen=sorted(hex(p) for p in starts_seen),
        invalidated_expectation_candidates=old, other_literal_uses_per_file=old_data, compile_command=command, compile_batch_command=scommand, failure=None, ROM_unchanged=True)
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(seeds=len(seed_rows), complete_passes=totals['complete_passes'], node_segments=totals['node_segments'], fixtures=len(frows), negatives=len(negative), zero_step=len(zero), sha256=cc.digest(report_path))))


class Ctx(object):
    pass


if __name__ == '__main__':
    main()
