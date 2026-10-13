"""Stage controller F1b (area clear 47da4: first-frame preparation, 30 / 160 / 48 frame callback timers, player survival branch, child allocation, 19db sound,
8c16 exit fade, next-area hand-off to 477ee; helpers 4b6e4 4b6ec 1c5b0 1bee4 ca48 9056) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection.  The frozen native observation (artifacts/animation_machine_area_clear_native) is an immutable input: this verifier
never invokes the observer main and never imports the observer module.  Every frame of every native condition (256 conditions, 37444 frames) is replayed against the
actual C++ `run_animation_machine` (one run = one frame, stop 2ac2 after the 480f0 RTS or 477ee at the F1c boundary):
  * per frame the full 64 KiB RAM / 16 registers / PC / A7 / PVC / bank / ordered ports / external reads / status of the actual C++ output are compared with the native
    record: the native full-state SHA256 (observation frame_state_sha256_definition, recomputed here from the C++ output with the same formula), the RAM / PVC / ports
    SHA256 and, where the observer stored a full dump (boundary frames 0 29 188 189 236, all frames of the 8 dump seeds and of every typed condition), the stored bytes;
  * every frame resumes ONLY from the previous actual C++ output plus the declared host changes of the native step (RAM writes, the declared direct re-entry
    PC redirect / A7 delta, the declared sound / sprite release writes); the native input state is never injected (dumps only assert it);
  * continuous C++ run of each frame vs the split C++ chain that stops at every checkpoint of the native step (first arrival, same order, directly after the transferring
    instruction) and vs the native frame; a wait (3aea / cda4) gives AnimationMachineWaiting at the same PC / A7 and resumes by the declared release write;
  * carry = block classification observed through the actual C++: the three consumers 1c5bc 1c5d8 47e0a take a Known C produced by the callee (289e formula / the native
    branch path), flip controls select the other destination, single-block probes with incoming C 1 / 2 on every distinct F1b start observed in a dumped frame give the
    FLOW_ONLY table (16 blocks) back, Unknown at a consumer gives the exact error `area clear caller requires known carry`; native SR is never read;
  * native guards -> exact checked C++ error strings + full preservation; deliberate differences are classified by explicit rules and counted;
  * API-only negatives: all 149 interior PCs, odd and out-of-range PCs, non-routed neighbours, 477ee without a stop, zero-step at every one of the 39 starts x 3 carries.
Native SR is never read: C is a block classification.
"""
import collections
import concurrent.futures
import gzip
import hashlib
import json
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
OUT = ROOT / 'artifacts/animation_machine_area_clear_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_area_clear_native'
NATIVE_SHA = '88b6b075fb184b37d59cbf454dd4a9cb4eec7f9b4d4dddc2586b993a1e4fc73e'
NATIVE_TOOL_SHA = 'afeb5669e119d6c65776e3c36f58f99443d0c7a41ccfd2e085651ccbb3f20201'
CONTRACT = ROOT / 'docs/analysis/animation-machine-area-clear-f1b-contract.md'
CONTRACT_SHA = '6bd2e96395e73814b7d4308f03d027eb1fb7be3c17ef8019491512340f66d4f2'
CPP_SHA = '30333c627a4fee5babf1fbf32a3400faa1f4819646d032f6c3e444cbd2ff10a7'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY + ('scc',)          # the contract adds Scc: it does not change the condition codes on the M68000
M32 = 0xffffffff
S = 0x1feffc
FRAME_RET = 0x2ac2
END_STOP = 0x477ee
FRAME_RTS = 0x480f0
WAIT_PCS = (0xcda4, 0x3aea)
# Neighbour probes superseded by later F4 units (label -> classification) and their observed new error.
SUPERSEDED_NEIGHBOURS = {'unrouted_neighbour_01c5ea': 'superseded_by_F4_later_unit_routes_1c5ea'}
SUPERSEDED_NEIGHBOUR_ERRORS = {'unrouted_neighbour_01c5ea': 'program bus write requires RAM mirror units'}  # align2 run: observed at HEAD a32885b
F1B_RANGES = ((0x47da4, 0x47eac), (0x4b6e4, 0x4b6f4), (0x1c5b0, 0x1c5ea), (0x1bee4, 0x1bef8), (0xca48, 0xca50), (0x9056, 0x9060))
CONSUMERS = (0x1c5bc, 0x1c5d8, 0x47e0a)
CALLBACKS = (0x47de4, 0x47e22, 0x47e62, 0x47e70, 0x47e92)
BB_ENTRIES = (0x289e, 0x28ae, 0x2a48, 0x3af8, 0x8c16, 0x9060, 0x480bc, 0x49c20)
REG16 = tuple('d%d' % i for i in range(8)) + tuple('a%d' % i for i in range(8))
UNKNOWN_CARRY = 'area clear caller requires known carry'
UNSUPPORTED_AREA = 'unsupported animation area clear PC'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNALIGNED_PC = 'unaligned animation machine PC'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
WRITE_DEVICE = 'unsupported animation machine write device'
TRAP15 = 'animation cleanup original TRAP15: nonzero object type'
BUDGET = 'animation machine block budget exceeded'
STATE_SHA_PREFIX = b'F1B-FRAME-STATE-v1'
VERIFIED_BLOBS = set()
RUN_DIR = None
WORKERS = int(os.environ.get('AREA_CLEAR_WORKERS', '3'))
DEBUG_LABELS = [x for x in os.environ.get('AREA_CLEAR_DEBUG_LABELS', '').split(',') if x]    # development switch only: the reported run is always the full set
API_ONLY = bool(os.environ.get('AREA_CLEAR_API_ONLY'))                                  # development switch only
MODEL_NATIVE_KEYS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')


def localize(name):
    local = str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name
    return local if Path(local).exists() else name           # tools not copied into this worktree are read from the main tree (read only)


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


# Batch harness: the same body as `common.HARNESS` (one run_animation_machine call per request, identical argument vector, identical output files and JSON), but the 8 physical ROM
# resources are loaded once per process and requests are read from stdin.  A one-shot spawn per call costs ~70 ms of ROM loading; equality with the one-shot
# harness is audited at run time (harness_equivalence).
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
    """One run_animation_machine call.  Default: batch harness; oneshot=True uses common.HARNESS through a fresh process (close_fds=False)."""
    paths = [folder / (label + s) for s in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin')]
    paths[0].write_bytes(ram)
    paths[1].write_bytes(pvc)
    if oneshot:
        args = [str(exe)] + request_args(state, bank, stop, external, paths) + list(map(str, resources))
        run = subprocess.run(args, capture_output=True, text=True, timeout=600, close_fds=False)
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


# ----------------------------------------------------------------------------------------------------------------- static audit
class RomInstructions(dict):
    def __init__(self, program):
        dict.__init__(self)
        self.program = program

    def __missing__(self, pc):
        item = disassemble_range(self.program, pc, 10, pc)[0]
        assert item['cpu_address'] == pc and item['classification'] in ('candidate_instruction',), (hex(pc), item['classification'])
        self[pc] = item
        return item


def pcs_in(text):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{4,5})`', text)]


def parse_contract(program):
    lines = CONTRACT.read_text().splitlines()
    table, blocks = [], []
    pat_r = re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| `([0-9a-f]+)` \|$')
    pat_b = re.compile(r'^\| `([0-9a-f]+)` \| `([0-9a-f]+)` \| (.*) \|$')
    for line in lines:
        m = pat_r.match(line)
        if m:
            low, high = int(m.group(1), 16), int(m.group(2), 16)
            assert program[low:high].hex() == m.group(3), hex(low)
            table.append((low, high))
            continue
        m = pat_b.match(line)
        if m:
            blocks.append((int(m.group(1), 16), bytes.fromhex(m.group(2)), m.group(3)))
    assert table == list(F1B_RANGES) and sum(h - l for l, h in table) == 376
    starts = bundled = preserve = None
    for i, line in enumerate(lines):
        if line.startswith('- **Block 시작 PC (39개)**'):
            j = i + 1
            while not lines[j].startswith('`'):
                j += 1
            starts = pcs_in(lines[j])
        if line.startswith('- **묶인 조건분기 PC (6개'):
            bundled = pcs_in(line.split('**:', 1)[1].split('. [F]')[0])
        if line.startswith('- **Carry 보존(FLOW_ONLY) block (16개)**'):
            preserve = pcs_in(line.split('**:', 1)[1])
    assert starts and len(starts) == len(set(starts)) == 39 and bundled and len(bundled) == 6 and preserve and len(preserve) == len(set(preserve)) == 16
    assert len(blocks) == 39 and sorted(b[0] for b in blocks) == sorted(starts)
    return table, starts, bundled, preserve, blocks


def audit_static(program):
    table, starts, bundled, preserve, blocks = parse_contract(program)
    instructions = RomInstructions(program)
    start_set = set(starts)
    inside = []
    for low, high in F1B_RANGES:
        pc = low
        while pc < high:
            inside.append(pc)
            pc += instructions[pc]['size']
        assert pc == high, hex(low)
    assert len(inside) == 81
    names = lambda pc: instructions[pc]['mnemonic'].split('.')[0]
    assert not [pc for pc in inside if names(pc) in ('trap', 'rte') or names(pc) in ('addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')]
    # block table bytes / instruction counts re-derived from the original bytes
    block_len = {}
    for start, raw, text in blocks:
        count, pc = 0, start
        while pc < start + len(raw):
            count += 1
            pc += instructions[pc]['size']
        assert pc == start + len(raw) and program[start:start + len(raw)] == raw, hex(start)
        assert count == len(text.split(';')), (hex(start), count, text)
        block_len[start] = count
    # blocks derived from the instruction stream: from each start up to the first terminator / next start
    derived = {}
    for start in starts:
        pcs, pc = [], start
        while True:
            pcs.append(pc)
            name = names(pc)
            end = name in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'dbra', 'trap') or name in ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
            following = pc + instructions[pc]['size']
            if end or following in start_set or not in_ranges(following, F1B_RANGES):
                break
            pc = following
        derived[start] = pcs
    assert {s: len(p) for s, p in derived.items()} == block_len
    covered = collections.Counter(pc for p in derived.values() for pc in p)
    assert max(covered.values()) == 1 and set(covered) == set(inside), (len(covered),)
    flow = sorted(pc for pc in starts if all(names(p) in FLOW_ONLY for p in derived[pc]))
    assert flow == sorted(preserve), [hex(p) for p in set(flow) ^ set(preserve)]
    even_pcs = [pc for low, high in F1B_RANGES for pc in range(low, high, 2)]
    interior = [pc for pc in even_pcs if pc not in start_set]
    assert len(even_pcs) == 188 and len(interior) == 149 and 0x47e0e in interior
    assert bundled == sorted(bundled) and not set(bundled) & start_set and set(bundled) <= set(interior)
    consumers = sorted(pc for pc in starts if names(pc) in ('bcc', 'bcs'))
    assert consumers == [0x1c5bc, 0x1c5d8] and sorted(CONSUMERS) == [0x1c5bc, 0x1c5d8, 0x47e0a]      # 47e0a is Scc + Bcc in one block (first instruction Scc)
    assert names(0x47e0a) == 'scc' and names(0x47e0e) == 'bcc'
    producers = [pc for pc in inside if names(pc) in ('ori', 'andi', 'eori') and re.search(r'\bccr\b', instructions[pc]['op_str'])]
    assert producers == []
    return dict(table=table, starts=starts, bundled=bundled, preserving=preserve, instructions=instructions, blocks=derived, block_len=block_len, interior=interior,
                inside=inside, even_pcs=even_pcs)


def cpp_static(st):
    """C++ case labels vs the 39 block starts, routing ranges, carry-preserving table in the unit vs the 16 FLOW_ONLY blocks."""
    text = (ROOT / 'engine/src/animation_machine_area_clear.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text))
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    in_unit = set(pc for pc in table if in_ranges(pc, F1B_RANGES))
    start = machine.index('animation_stage_entry_block(c);') + len('animation_stage_entry_block(c);')
    route = machine[start:machine.index('animation_area_clear_block(c);', start)]
    ranges = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', route))
    return cases, in_unit, ranges


# ----------------------------------------------------------------------------------------------------------------- native data
def read_blob(name):
    data = (NATIVE_DIR / 'blobs' / name).read_bytes()
    assert sha(data) == name.split('.')[0], name
    VERIFIED_BLOBS.add(name)
    return data


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_area_clear.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'engine/src/animation_machine_area_clear.cpp') == CPP_SHA
    assert cc.digest(CONTRACT) == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert report['conditions'] == 256 == len(report['results']) == len(report['condition_files'])
    assert report['totals']['frames'] == 37444 and report['totals']['split_phases'] == 117537 and report['totals']['control_phases'] == 37444
    assert report['totals']['fresh_frames_equal'] == 37444 and report['totals']['model_frames'] == report['totals']['model_frames_equal'] == 37330
    assert report['block_starts_not_hit'] == [] and len(report['block_starts']) == 39
    assert sum(r['frames'] for r in report['results']) == sum(1 for _ in report['results']) * 0 + sum(r['frames'] for r in report['results'])
    assert sum(r['control_phases'] for r in report['results']) == 37444 and sum(r['split_phases'] for r in report['results']) == 117537
    assert sum(r['dumped_frames'] for r in report['results']) == report['totals']['dumped_frames'] == 7516
    assert report['boundary_frames'] == [0, 29, 188, 189, 236] and report['dump_seeds'] == [0, 60, 117, 118, 134, 126, 135, 141]
    assert report['groups'] == {'natural': 137, 'release-guard': 5, 'variant': 17, 'callback': 18, 'player': 8, 'direct': 6, 'transition': 5, 'sound': 3, 'zero-step': 39, 'guard': 18}
    assert [c['kind'] for c in report['contract_discrepancies']] == ['contract-contradicted']
    for name, expected in report['inputs'].items():
        assert cc.digest(localize(name)) == expected, name
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    return report


def load_condition(report, result):
    data = (NATIVE_DIR / 'conditions' / result['condition_file']).read_bytes()
    assert sha(data) == result['condition_file_sha256'] == report['condition_files']['conditions/' + result['condition_file']]
    cond = json.loads(gzip.decompress(data))
    assert cond['label'] == result['label'] and len(cond['frames']) == len(cond['steps']) == result['control_phases']
    return cond


def lead_pcs_of(pcs, start_set, initial_last):
    """The observer's leader rule on the executed instruction PCs (entry .. last instruction): a leader is a contract block start, or one of the callee entries reached
    directly from F1b code (the previous executed PC lies in an F1b range)."""
    lead_set = start_set | set(BB_ENTRIES)
    leads, last = [], initial_last
    for index, pc in enumerate(pcs[:-1]):
        if pc in lead_set and (pc in start_set or (last is not None and in_ranges(last, F1B_RANGES))):
            leads.append(index)
        last = pc
    return leads


# ----------------------------------------------------------------------------------------------------------------- state helpers
def state_sha(ram, state, bank_base, ports):
    h = hashlib.sha256()
    h.update(STATE_SHA_PREFIX)
    h.update(ram)
    h.update(struct.pack('>16I', *[state[k] for k in REG16]))
    h.update(struct.pack('>II', state['pc'], bank_base >> 20))
    h.update(struct.pack('>I', len(ports) // 9))
    h.update(ports)
    return h.hexdigest()


def initial_carry(fixture):
    sr = fixture.get('sr')
    if sr is None:
        return 0
    return 2 if sr & 1 else 1


def apply_changes(ram, state, rows):
    ram = bytearray(ram)
    state = dict(state)
    for row in rows:
        if row[0] == 'ram':
            address, size, value = int(row[1], 16), row[2], bytes.fromhex(row[3])
            assert len(value) == size and 0x100000 <= address and address + size <= 0x200000 and (address & 0xffff) + size <= 0x10000
            ram[address & 0xffff:(address & 0xffff) + size] = value
        elif row[0] == 'pc':
            state['pc'] = int(row[1], 16)
        elif row[0] == 'a7_add':
            state['a7'] = (state['a7'] + row[1]) & M32
        else:
            raise AssertionError(row)
    return bytes(ram), state


def out_state(result):
    return {k: result[k] for k in common.STATE_KEYS}


def check_preserved(actual, ram, state, pvc, bank, expected_error=None):
    result, out_ram, out_pvc, ports, error = actual
    assert not result['ok'] and (expected_error is None or error.strip() == expected_error), (expected_error, error.strip())
    assert {k: result[k] for k in common.STATE_KEYS} == {k: state[k] for k in common.STATE_KEYS}
    assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
    assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
    return error.strip()


# Native guard -> expected checked C++ error (explicit, per condition).  Rules below classify the deliberate differences.
GUARD_EXPECTED = {
    'release-guard-136': EVEN, 'release-guard-137': EVEN, 'release-guard-138': EVEN, 'release-guard-139': EVEN, 'release-guard-140': EVEN,   # odd WORD read (U1 3c60 / 3bb2)
    'transition-case77-partial': TRAP15, 'transition-case77-full': TRAP15, 'guard-trap15-cleanup-47da4': TRAP15,                             # 2a48 -> 2a52 TRAP #15
    'transition-case77-full-type0': EVEN,
    'a6-102000-seed0': WRITE_DEVICE,
    'guard-odd-a6-47dd8': EVEN_WRITE, 'guard-odd-a6-47de4': EVEN, 'guard-odd-a6-47e1c': EVEN_WRITE, 'guard-odd-a6-47e56': EVEN_WRITE,
    'observe-odd-a6-byte-47e22': UNSUPPORTED_MACHINE,
    'guard-odd-child-a0-47e12': EVEN_WRITE, 'guard-odd-child-a0-47e40': EVEN_WRITE, 'guard-rom-child-a0-47e12': WRITE_DEVICE, 'guard-rom-a6-47dd8': WRITE_DEVICE,
    'guard-odd-a7-47da4': EVEN, 'guard-a5-zero-47da4': WRITE_DEVICE,
    'guard-stop-not-477ee': UNSUPPORTED_MACHINE, 'guard-no-2ac2-stop-d72fe': 'program bus write requires RAM mirror units', 'guard-no-2ac2-stop-e4234': UNSUPPORTED_MACHINE,
    'guard-bad-return-long': UNSUPPORTED_MACHINE,
    'guard-28ae-pool-null-47e30': WRITE_DEVICE}
SUPERSEDED_GUARDS = {'guard-stop-not-477ee': UNSUPPORTED_MACHINE}     # original expectation kept for the record
# Guards whose native reason and C++ error are not the same check; every one is a rejection at the same split-segment (native_split_phases - 1 == C++ phases before the error).
GUARD_NOTES = {
    'guard-no-2ac2-stop-d72fe': ('superseded_by_F4_U04', 'The frozen observer stops before d72fe. U04 now executes this callback; the combined run later rejects a RAM-mirror write. The original prefix is retained, d72fe LEA is checked separately, and no native suffix or fault rollback equivalence is claimed.'),
    'transition-case77-partial': ('contract_claim_contradicted_by_native', 'contract decision 6 (partial run 47da4 -> 47de4 of the recorded case 77) does not hold: the recorded RAM has WORD 100c04 = f2ee, so 2a48 reaches TRAP #15 at 2a52 (native guard '
                                  'unsupported_TRAP, C++ checked error TRAP15); with the declared WORD 100c04 := 0 (transition-case77-partial-type0) the run completes at 47de4 and is compared normally'),
    'transition-case77-full': ('contract_claim_contradicted_by_native', 'same as transition-case77-partial for the full frame'),
    'transition-case77-full-type0': ('native_32bit_unmapped_write_vs_cpp_checked_odd_access', 'native Unicorn faults on a WORD write to the unmapped 32-bit address 80a902e9 at 1a2c0 (synthetic mostly-zero case 77 RAM, odd '
                                     'effective address); the C++ masks addresses to 24 bits and rejects at the same split segment with the odd WORD/LONG access check (no rollback equivalence claimed)'),
    'a6-102000-seed0': ('native_ROM_write_vs_cpp_write_device', 'the declared A6 = 102000 context: after 29 frames 28ae writes through a node pointer at address 4 (ROM): native unmapped_or_protected, C++ unsupported write device'),
    'guard-28ae-pool-null-47e30': ('native_ROM_write_vs_cpp_write_device', 'observer finding not covered by the contract text: 28ae succeeds by count (D0 14 < count) while the free list head 104c9c is NULL, so the original writes '
                                   'through 0 + c (ROM / vector area, ignored by real hardware); native unmapped_or_protected, C++ rejects with the write-device check.  Conservative deliberate difference, no rollback equivalence claimed'),
    'observe-odd-a6-byte-47e22': ('native_unmapped_fetch_vs_cpp_unrouted_PC', 'odd A6: the native Unicorn tolerates the odd LONG read of (A6) (bytes 047af000) and faults on the fetch at 047af000; the C++ lands on the same '
                                  'non-routed PC (verified with stop = 047af000) and reports unsupported animation machine PC'),
    'guard-odd-a7-47da4': ('native_odd_write_vs_cpp_odd_stack_access', 'odd A7: native odd LONG write (JSR push) address error, C++ odd stack access check (same class, different layer message)')}



# ----------------------------------------------------------------------------------------------------------------- condition replay
class Ctx(object):
    pass


def compile_server(root, folder):
    path = folder / 'harness_batch.cpp'
    path.write_text(HARNESS_SERVER)
    exe = folder / 'animation_machine_area_clear_batch_harness'
    compiler = shutil.which('clang++')
    assert compiler
    command = [compiler, '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(root / 'engine/include')]
    command += [str(root / 'engine/src' / name) for name in common.SOURCES]
    command += [str(path), '-o', str(exe)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=900)
    (folder / 'compile_batch.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stdout and not run.stderr, run.stderr
    return exe, command


def inv(ctx, label, ram, state, pvc, bank, stop, external):
    return invoke(ctx.exe, RUN_DIR, label, ram, state, pvc, bank, ctx.resources, stop, external)


def branch_target(pc, carry):
    """Destination of the three area clear carry consumers for a known C (1 Clear, 2 Set)."""
    assert carry in (1, 2)
    return {0x1c5bc: (0x1c5cc, 0x1c5c0), 0x1c5d8: (0x1c5e8, 0x1c5dc), 0x47e0a: (0x47e1c, 0x47e12)}[pc][0 if carry == 1 else 1]


def hexint(text):
    return int(text, 16)


def load_trace(row):
    dump = row.get('dump')
    if not dump:
        return None
    return json.loads(gzip.decompress(read_blob(dump['trace'])))


def split_chain(ctx, tag, ram, state, pvc, bank, stop, checkpoints, external):
    """The C++ split chain of one native step: stop at the first arrival of every checkpoint in the native order, then at the step stop (or at a wait).  Every phase
    resumes from the previous actual C++ output."""
    phases, seen, cur = [], set(), (ram, dict(state), pvc, bank)
    while True:
        remaining = [c for c in checkpoints if c not in seen]
        target = remaining[0] if remaining else stop
        actual = inv(ctx, '%s_p%02d' % (tag, len(phases)), cur[0], cur[1], cur[2], cur[3], target, external)
        phases.append(dict(target=target, actual=actual, entry=cur))
        result = actual[0]
        if not result['ok']:
            return phases, 'error'
        if result['status'] == 1:
            return phases, 'wait'
        cur = (actual[1], out_state(result), actual[2], result['bank_base'])
        seen.add(target)
        if target == stop and not remaining:
            return phases, 'stop'
        if result['pc'] != target:
            return phases, 'wrong-stop'


def native_leader_regs(row, trace, start_set):
    """Native registers at the leader that is the first arrival of every checkpoint PC (dumped frames): {checkpoint pc: regs} when the first arrival is a recorded leader."""
    if trace is None:
        return {}
    pcs = trace['pcs']
    expected = [hexint(x) for x in row['leaders']]
    for initial_last in (None, 0x47da4):
        idx = lead_pcs_of(pcs, start_set, initial_last)
        if [pcs[i] for i in idx] == expected and len(idx) == len(trace['leaders']):
            first = {}
            for i, entry in zip(idx, trace['leaders']):
                assert entry['pc'] == pcs[i] == entry['regs']['pc']
                first.setdefault(pcs[i], (i, entry['regs']))
            return first
    return None


def replay_condition(ctx, report, result):
    cond = load_condition(report, result)
    fx = result['fixture']
    label = result['label']
    acc = dict(totals=collections.Counter(), carry_stops=collections.Counter(), deliberate=[], guard=None, probes={}, consumer=collections.Counter(), failures=[], starts_seen=set())
    totals = acc['totals']
    ram = read_blob(fx['initial_RAM_sha256'] + '.bin')
    pvc = read_blob(fx['initial_PVC_sha256'] + '.bin')
    assert sha(ram) == fx['initial_RAM_sha256'] and sha(pvc) == fx['initial_PVC_sha256']
    bank = fx['bank_state'][0]
    regs = dict(fx['initial_regs'])
    assert sorted(regs) == sorted(k for k in common.REGS if k != 'a7')
    state = dict(regs, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=initial_carry(fx))
    external = fx['external']
    start_set = ctx.start_set
    chain = hashlib.sha256()
    tag0 = 'c%03d' % result['number']
    expected_phases_total = result['split_phases']
    split_total = 0
    for j, (step, row) in enumerate(zip(cond['steps'], cond['frames'])):
        assert step['label'] == row['label'] and step['changes'] == row['host_changes'] and row['step'] == j
        ram, state_in = apply_changes(ram, state, row['host_changes'])
        assert state_in['pc'] == hexint(row['in_pc']) and state_in['a7'] == hexint(row['in_a7']), (label, j)
        dump = row.get('dump')
        trace = load_trace(row)
        if dump:
            raw = bytearray(read_blob(dump['pvc_before']))
            raw[0x1ff0:0x1ff4] = pvc[0x1ff0:0x1ff4]               # the native PVC image is raw Unicorn memory: the two bank registers keep the last written value
            assert read_blob(dump['ram_before']) == ram and bytes(raw) == pvc, (label, j, 'native input state differs from the C++ chain state')
            totals['dumped_inputs_equal_cpp_chain_state'] += 1
        stop = hexint(step['stop_pc'])
        checkpoints = [hexint(x) for x in step['checkpoints']]
        tag = '%s_s%03d' % (tag0, j)
        guarded = 'guard' in row
        cont = inv(ctx, tag + '_cont', ram, state_in, pvc, bank, stop, external)
        totals['continuous_runs'] += 1
        phases, how = split_chain(ctx, tag, ram, state_in, pvc, bank, stop, checkpoints, external)
        totals['split_phases'] += len(phases)
        split_total += len(phases)
        if guarded:
            assert j == len(cond['steps']) - 1, (label, j)
            guard_row(ctx, acc, result, row, step, ram, state_in, pvc, bank, cont, phases, how, stop, external, trace)
            totals['guard_frames'] += 1
            break
        # ---- the native frame
        res, out_ram, out_pvc, out_ports, error = cont
        assert res['ok'] and not error, (label, j, error)
        waiting = row['waiting']
        assert res['status'] == (1 if waiting else 0), (label, j, 'status')
        assert (how == 'wait') == waiting and how in ('stop', 'wait'), (label, j, how)
        state_out = out_state(res)
        sha_cpp = state_sha(out_ram, state_out, res['bank_base'], out_ports)
        assert sha_cpp == row['state_sha256'], (label, j, 'full-state SHA256 differs from the native frame')
        assert sha(out_ram) == row['ram_sha256'] and sha(out_ports) == row['ports_sha256'] and len(out_ports) // 9 == row['port_count']
        ff8, ff9 = hexint(row['ff8']), hexint(row['ff9'])
        if trace is not None:
            # PVC device image and bank: independent fold of the native ordered PVC writes (the native pvc_after is the raw Unicorn memory, the C++ image is normalized)
            exp_pvc, exp_bank, _ = common.fold_device(pvc, bank, trace['events'])
            assert out_pvc == exp_pvc and res['bank_base'] == exp_bank, (label, j, 'PVC / bank fold of the native events')
            totals['pvc_image_equals_native_event_fold'] += 1
        else:
            exp = bytearray(pvc)
            exp[0x1ff0:0x1ff2] = ff8.to_bytes(2, 'big')
            exp[0x1ff2:0x1ff4] = ff9.to_bytes(2, 'big')
            assert out_pvc == bytes(exp), (label, j, 'PVC image: only the normalized bank registers may change')
            totals['pvc_image_equals_input_with_native_bank_registers'] += 1
        assert res['external_reads'] == row['external_reads'] and res['bank_base'] >> 20 == row['bank']
        assert '%x' % res['pc'] == row['out_pc'] == row['pc'] and '%x' % res['a7'] == row['out_a7']
        assert {k: '%08x' % res[k] for k in REG16} == row['regs16']
        assert '%x' % int.from_bytes(out_pvc[0x1ff0:0x1ff2], 'big') == row['ff8'] and '%x' % int.from_bytes(out_pvc[0x1ff2:0x1ff4], 'big') == row['ff9']
        assert row['fresh_equal'] is True and row['model_equal'] in (True, None)
        kind = step['expect']
        if kind in ('return', 'boundary'):
            assert res['pc'] == stop and res['status'] == 0
        if step['a7'] is not None and not waiting:
            want = (state_in['a7'] + step['a7'][1]) & M32 if step['a7'][0] == 'entry' else step['a7'][1]
            assert res['a7'] == want, (label, j, 'declared A7 at the stop')
        if waiting:
            assert res['pc'] in WAIT_PCS and res['carry'] == 0
            totals['waiting_frames'] += 1
        if dump:
            raw = bytearray(read_blob(dump['pvc_after']))
            raw[0x1ff0:0x1ff4] = out_pvc[0x1ff0:0x1ff4]            # raw Unicorn memory keeps the last written value of the two bank registers; everything else equal
            assert out_ram == read_blob(dump['ram_after']) and out_pvc == bytes(raw) and out_ports == read_blob(dump['ports']), (label, j)
            totals['dumped_outputs_equal_bytes'] += 1
        # ---- split chain vs continuous
        last = phases[-1]['actual']
        assert last[0]['ok'] and last[1] == out_ram and last[2] == out_pvc and out_state(last[0]) == state_out and last[0]['bank_base'] == res['bank_base'] and last[0]['status'] == res['status']
        assert b''.join(p['actual'][3] for p in phases) == out_ports and sum(p['actual'][0]['external_reads'] for p in phases) == res['external_reads']
        totals['split_equals_continuous_frames'] += 1
        # ---- carry / leaders / probes / consumers
        if stop == state_in['pc']:
            assert len(phases) == 1 and state_out == state_in and out_ram == ram and out_pvc == pvc and not out_ports and res['external_reads'] == 0
            totals['zero_step_frames_state_unchanged'] += 1
            acc['starts_seen'].add(state_in['pc'])
        else:
            carry_checks(ctx, acc, result, row, step, j, tag, trace, phases, state_in, ram, pvc, bank, stop, external, start_set)
        chain.update(bytes.fromhex(sha_cpp))
        totals['frames'] += 1
        if j and cond['steps'][j]['label'].find('-release') < 0:
            totals['declared_direct_reentries'] += 1
        ram, pvc, bank, state = out_ram, out_pvc, res['bank_base'], state_out
        totals['ports'] += len(out_ports) // 9
        totals['external_reads'] += res['external_reads']
    totals['split_phases_native_total_declared'] += expected_phases_total
    acc['chain_sha256'] = chain.hexdigest()
    acc['out_row'] = dict(number=result['number'], label=label, group=result['group'], frames=totals['frames'], steps=len(cond['steps']), cpp_split_phases=split_total,
                          native_split_phases=expected_phases_total, guard_frames=totals['guard_frames'], dumped_frames=result['dumped_frames'], C_frame_state_chain_sha256=chain.hexdigest(),
                          final_state_sha256=cond['frames'][-1]['state_sha256'])
    return acc


def guard_row(ctx, acc, result, row, step, ram, state_in, pvc, bank, cont, phases, how, stop, external, trace):
    label = result['label']
    if label in SUPERSEDED_GUARDS:
        # superseded by F1c1 (477ee is now an executable frame start): the frame no longer refuses at 477ee, it runs on to the declared frame return 2ac2 without a checked error
        res, out_ram, out_pvc, out_ports, error = cont
        assert res['ok'] and not error and res['pc'] == stop == FRAME_RET and res['status'] == 0 and how == 'stop', (label, how, error, hex(res['pc']))
        others = {}
        for carry in (0, 1, 2):
            if carry == state_in['carry']:
                continue
            again = inv(ctx, 'c%03d_guard_carry%d' % (result['number'], carry), ram, dict(state_in, carry=carry), pvc, bank, stop, external)
            assert again[0]['ok'] and not again[4] and again[0]['pc'] == FRAME_RET, (label, carry)
            others[CARRY_NAME[carry]] = 'reaches 2ac2 without error'
        acc['guard'] = dict(label=label, group=result['group'], native_guard=row['guard'], native_guard_reason=row['guard'].get('reason'), checked_API_error=None,
                            expected_API_error=SUPERSEDED_GUARDS[label], cpp_error_matches_expected=False, continuous_run_error=None, split_chain_error=None,
                            cpp_phases_before_error=None, native_split_phases=row['split_phases'], all_API_outputs_preserved=False, native_fault_rollback_equivalence_claimed=False,
                            state_with_other_carries=others, same_split_segment_as_native=False, cpp_run_reaches_stop='%x' % res['pc'],
                            classification='superseded_by_F1c1_frame_reaches_2ac2', rule='the native refusal at BRA.W 477ee (47ea8) was recorded before F1c1; 477ee is now a routed '
                            'F1c1 frame start, so the frame run with stop 2ac2 only completes there without error (positive check, native guard record kept)')
        return
    error = check_preserved(cont, ram, state_in, pvc, bank)
    first_failed = None
    for index, p in enumerate(phases):
        if not p['actual'][0]['ok']:
            first_failed = index
            e_ram, e_state, e_pvc, e_bank = p['entry']
            chain_error = check_preserved(p['actual'], e_ram, e_state, e_pvc, e_bank)
            assert chain_error == error, (label, 'split chain error differs from the continuous run', chain_error, error)
    assert how == 'error' and first_failed == len(phases) - 1, (label, how)
    expected = GUARD_EXPECTED.get(label)
    entry = dict(label=label, group=result['group'], native_guard=row['guard'], native_guard_reason=row['guard'].get('reason'), checked_API_error=error, expected_API_error=expected,
                 cpp_error_matches_expected=error == expected, continuous_run_error=error, split_chain_error=error, cpp_phases_before_error=len(phases) - 1,
                 native_split_phases=row['split_phases'], all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False,
                 state_with_other_carries={})
    for carry in (0, 1, 2):
        if carry == state_in['carry']:
            continue
        s2 = dict(state_in, carry=carry)
        again = inv(ctx, 'c%03d_guard_carry%d' % (result['number'], carry), ram, s2, pvc, bank, stop, external)
        entry['state_with_other_carries'][CARRY_NAME[carry]] = check_preserved(again, ram, s2, pvc, bank)
    native = row['guard']
    entry['same_split_segment_as_native'] = len(phases) == row['split_phases']
    if native.get('problem') == 'unsupported_code_target' and native['target'] % 2 == 0 and native['target'] != stop:
        reach = inv(ctx, 'c%03d_guard_reach' % result['number'], ram, state_in, pvc, bank, native['target'], external)
        assert reach[0]['ok'] and not reach[4] and reach[0]['pc'] == native['target'] and reach[0]['status'] == 0, (label, 'C++ does not reach the native transfer target')
        entry['cpp_reaches_native_transfer_target_with_stop'] = '%x' % native['target']
        if label == 'guard-no-2ac2-stop-d72fe':
            assert native['target'] == 0xd72fe
            program, unused_source = load_verified_program(ROOT)
            assert program[0xd72fe:0xd7302] == bytes.fromhex('41faffb6')
            prefix_ram, prefix_state, prefix_pvc, prefix_bank = reach[1], out_state(reach[0]), reach[2], reach[0]['bank_base']
            one = inv(ctx, 'c%03d_U04_LEA_prefix' % result['number'], prefix_ram, prefix_state, prefix_pvc, prefix_bank, 0xd7302, external)
            want = dict(prefix_state, a0=0xd72b6, pc=0xd7302)
            assert one[0]['ok'] and not one[4] and one[0]['status'] == 0
            assert out_state(one[0]) == want and one[1] == prefix_ram and one[2] == prefix_pvc
            assert one[0]['bank_base'] == prefix_bank and one[0]['external_reads'] == 0 and not one[3]
            entry['former_expected_API_error'] = UNSUPPORTED_MACHINE
            entry['new_callback_first_block_verified'] = 'd72fe LEA d72b6(PC),A0 -> d7302'
            entry['native_suffix_equivalence_claimed'] = False
    note = GUARD_NOTES.get(label)
    entry['classification'] = note[0] if note else 'same_check_class'
    entry['rule'] = note[1] if note else None
    acc['guard'] = entry
    if expected is None or error != expected:
        acc['failures'].append(('guard error', label, error, expected))
    if not entry['same_split_segment_as_native']:
        acc['failures'].append(('guard segment', label, len(phases), row['split_phases']))


def block_state(p):
    """State at the stop of a split-chain phase: (RAM, state, PVC, bank)."""
    r = p['actual']
    return r[1], out_state(r[0]), r[2], r[0]['bank_base']


def carry_checks(ctx, acc, result, row, step, j, tag, trace, phases, state_in, ram, pvc, bank, stop, external, start_set):
    totals = acc['totals']
    label = result['label']
    pcs = trace['pcs'] if trace else None
    first = native_leader_regs(row, trace, start_set) if trace else {}
    block_len = ctx.st['block_len']
    preserve = set(ctx.st['preserving'])
    assert row['split_phases'] == len(phases), (label, j, 'split phase count', row['split_phases'], len(phases))
    # candidate block-start states of this frame: (pc, state tuple, index in the native pcs)
    at_start = []
    entry_pc = state_in['pc']
    at_start.append((entry_pc, (ram, state_in, pvc, bank), 0))
    acc['starts_seen'].add(entry_pc)
    for p in phases:
        res = p['actual'][0]
        target = p['target']
        acc['carry_stops']['%x:%s' % (target, CARRY_NAME[res['carry']])] += 1
        if res['status'] == 1:
            continue
        index = None
        if pcs is not None and target != stop:
            index = pcs.index(target, 1)
            if first is None:
                totals['leader_regs_alignment_unavailable_frames'] += 1
            elif target in first and first[target][0] == index:
                native = first[target][1]
                assert {k: res[k] for k in REG16} == {k: native[k] for k in REG16} and res['pc'] == native['pc'] == target, (label, j, hex(target))
                totals['checkpoint_registers_equal_native_leader'] += 1
            else:
                totals['checkpoint_not_a_native_leader'] += 1
        if target in start_set:
            acc['starts_seen'].add(target)
        if target in start_set and target != stop:
            at_start.append((target, block_state(p), index))
    for pc, (s_ram, s_state, s_pvc, s_bank), index in at_start:
        if pc not in start_set:
            continue
        if pc in CONSUMERS:
            if s_state['carry'] not in (1, 2):
                # a consumer reached with Unknown C is an error of the API, never a native path (the native CPU always has a CCR)
                acc['failures'].append(('consumer entered with Unknown C', label, j, hex(pc)))
                continue
            known = s_state['carry']
            if pcs is not None:
                want = branch_target(pc, known)
                assert pcs[index + block_len[pc]] == want, (label, j, hex(pc), known, hex(pcs[index + block_len[pc]]), hex(want))
                totals['consumer_known_carry_equals_native_branch_path'] += 1
            if pc != 0x47e0a:
                # 289e formula: Clear iff LONG (A0) == 270e
                if index != 0:
                    a0 = s_state['a0']
                    node = int.from_bytes(s_ram[(a0 & 0xffff):(a0 & 0xffff) + 4], 'big')
                    assert known == (1 if node == 0x270e else 2), (label, j, hex(pc), hex(node), known)
                    totals['consumer_carry_equals_289e_formula'] += 1
            key = (pc, known)
            if key in acc['consumer'] and acc['consumer'][key] >= 3:
                continue
            acc['consumer'][key] += 1
            flipped = 3 - known
            other = branch_target(pc, flipped)
            again = inv(ctx, '%s_flip%x_%d' % (tag, pc, acc['consumer'][key]), s_ram, dict(s_state, carry=flipped), s_pvc, s_bank, other, external)
            r2 = again[0]
            assert r2['ok'] and not again[4] and r2['pc'] == other and r2['status'] == 0 and r2['carry'] == flipped, (label, j, hex(pc))
            assert {k: r2[k] for k in REG16} == {k: s_state[k] for k in REG16} and again[2] == s_pvc and r2['bank_base'] == s_bank and again[3] == b'' and r2['external_reads'] == 0
            if pc == 0x47e0a:
                want_ram = bytearray(s_ram)
                want_ram[(s_state['a6'] + 0x62) & 0xffff] = 0xff if flipped == 1 else 0
                assert again[1] == bytes(want_ram), (label, j, 'SCC.B 62(A6) byte')
            else:
                assert again[1] == s_ram
            totals['consumer_flip_checks'] += 1
            totals['consumer_flip_%x_incoming_%s' % (pc, CARRY_NAME[known])] += 1
            slot = acc['probes'].setdefault(pc, {1: True, 2: True})
            slot[flipped] = slot[flipped] and r2['carry'] == flipped
            # Unknown C at the consumer: exact checked error, full preservation
            if (pc, 0) not in acc['consumer']:
                acc['consumer'][(pc, 0)] += 1
                s0 = dict(s_state, carry=0)
                bad = inv(ctx, '%s_unk%x' % (tag, pc), s_ram, s0, s_pvc, s_bank, other, external)
                check_preserved(bad, s_ram, s0, s_pvc, s_bank, UNKNOWN_CARRY)
                totals['consumer_unknown_carry_errors'] += 1
            continue
        if pcs is None or pc in acc['probes'] and 'done' in acc['probes'][pc]:
            continue
        # single-block probe with incoming C 1 / 2
        n = block_len[pc]
        nxt = pcs[index + n]
        slot = acc['probes'].setdefault(pc, {1: True, 2: True})
        slot['done'] = True
        outs = {}
        for k in (1, 2):
            a = inv(ctx, '%s_probe%x_%d' % (tag, pc, k), s_ram, dict(s_state, carry=k), s_pvc, s_bank, nxt, external)
            r2 = a[0]
            assert r2['ok'] and not a[4] and r2['pc'] == nxt and r2['status'] == 0, (label, j, hex(pc), a[4])
            want = k if pc in preserve else 0
            assert r2['carry'] == want, (label, j, hex(pc), k, r2['carry'])
            slot[k] = slot[k] and r2['carry'] == k
            outs[k] = a
            totals['carry_probes'] += 1
        a1, a2 = outs[1], outs[2]
        assert {x: y for x, y in a1[0].items() if x != 'carry'} == {x: y for x, y in a2[0].items() if x != 'carry'} and a1[1:4] == a2[1:4], (label, j, hex(pc))
        totals['carry_probe_pairs_equal_except_carry'] += 1




def guarded_replay(ctx, report, result):
    try:
        return replay_condition(ctx, report, result)
    except Exception:
        return dict(error=traceback.format_exc(), label=result['label'])


def replay_all(ctx, report, results):
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(lambda r: guarded_replay(ctx, report, r), results))


# ----------------------------------------------------------------------------------------------------------------- API-only checks
def reject_one(args):
    ctx, label, base, changes, stop, expected = args
    ram, state, pvc, bank = base
    s = dict(state, carry=2)
    s.update(changes)
    actual = inv(ctx, 'neg_' + label, ram, s, pvc, bank, stop, 0)
    assert actual[4].strip() == expected, (label, expected, actual[4].strip())
    check_preserved(actual, ram, s, pvc, bank, expected)
    row = dict(label=label, error=expected, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False)
    if label == 'boundary_477ee_without_stop_from_47e9a':
        row.update(former_expected_API_error=UNSUPPORTED_MACHINE, classification='superseded_by_F4_U04', API_only_control=True)
    if label in SUPERSEDED_NEIGHBOURS:
        # Alignment (align2 run): this neighbour was an unrouted probe; a later F4 unit now routes it.
        row.update(former_expected_API_error=UNSUPPORTED_MACHINE, classification=SUPERSEDED_NEIGHBOURS[label], API_only_control=True)
    return row


def run_parallel(function, items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(function, items))


def negatives(ctx, base, st):
    ram, state, pvc, bank = base
    jobs = []
    for pc in st['interior']:
        jobs.append((ctx, 'interior_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_AREA))
    # neighbours that are not routed to any executor (contract: other routines / data)
    for pc in (0x4b6f4, 0x1c5ea, 0x1bef8, 0xca50, END_STOP):
        label = 'unrouted_neighbour_%06x' % pc
        jobs.append((ctx, label, base, {'pc': pc}, 0xff000, SUPERSEDED_NEIGHBOUR_ERRORS.get(label, UNSUPPORTED_MACHINE)))
    # Declared unrouted control that no F4 unit can route: even work-RAM PCs (code never executes in RAM).
    for pc in (0x10fe00, 0x10fefe):
        jobs.append((ctx, 'unrouted_ram_pc_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    for low, high in F1B_RANGES:
        jobs.append((ctx, 'odd_pc_entry_%06x' % (low + 1), base, {'pc': low + 1}, 0xff000, UNALIGNED_PC))
        jobs.append((ctx, 'odd_pc_entry_%06x' % (high - 1), base, {'pc': high - 1}, 0xff000, UNALIGNED_PC))
    for pc in (0x1, 0xffffff, 0xdeadbeef, 0x47e0b, 0x47e0f):
        jobs.append((ctx, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    for pc in (0x0, 0xffffffe, 0x1000000, 0xdeadbee):
        jobs.append((ctx, 'out_of_range_entry_%x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    # The integrated U04 continuation now reaches a RAM-mirror write rejection.
    # This API-only control pins that exact error and complete output rollback.
    jobs.append((ctx, 'boundary_477ee_without_stop_from_47e9a', base, {'pc': 0x47e9a}, 0xff000, 'program bus write requires RAM mirror units'))
    out = run_parallel(reject_one, jobs)
    for pc in CONSUMERS:
        s0 = dict(state, pc=pc, carry=0)
        actual = inv(ctx, 'unknown_carry_%06x' % pc, ram, s0, pvc, bank, 0xff000, 0)
        check_preserved(actual, ram, s0, pvc, bank, UNKNOWN_CARRY)
        out.append(dict(label='unknown_carry_consumer_%06x' % pc, error=UNKNOWN_CARRY, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    controls = []
    for pc in CONSUMERS:
        for carry in (1, 2):
            want = branch_target(pc, carry)
            s2 = dict(state, pc=pc, carry=carry)
            res, out_ram, out_pvc, ports, error = inv(ctx, 'consumer_%06x_%d' % (pc, carry), ram, s2, pvc, bank, want, 0)
            assert res['ok'] and not error and res['pc'] == want and res['carry'] == carry and out_pvc == pvc and not ports and res['status'] == 0
            assert {k: res[k] for k in common.REGS} == {k: s2[k] for k in common.REGS}
            if pc == 0x47e0a:
                exp = bytearray(ram)
                exp[(state['a6'] + 0x62) & 0xffff] = 0xff if carry == 1 else 0
                assert out_ram == bytes(exp)
            else:
                assert out_ram == ram
            controls.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], next_pc=hex(want), carry_preserved=True, status=0))
    return out, controls


def zero_step_one(args):
    ctx, base, pc, carry = args
    ram, state, pvc, bank = base
    s = dict(state, pc=pc, carry=carry)
    result, out_ram, out_pvc, ports, error = inv(ctx, 'zero_%06x_%d' % (pc, carry), ram, s, pvc, bank, pc, 0)
    assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
    assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc and result['bank_base'] == bank and result['external_reads'] == 0 and not ports
    return (pc, carry)


def harness_equivalence(ctx, base, extra_cases):
    """The batch harness against the one-shot common.HARNESS on the same requests (bytes, JSON and error text)."""
    ram, state, pvc, bank = base
    cases = [('frame0', state, ram, pvc, bank, FRAME_RET), ('partial_47dc0', state, ram, pvc, bank, 0x47dc0), ('zero_step', state, ram, pvc, bank, state['pc']),
             ('interior_error', dict(state, pc=0x47da6), ram, pvc, bank, 0xff000), ('unknown_carry_error', dict(state, pc=0x1c5bc, carry=0), ram, pvc, bank, 0xff000),
             ('odd_pc_error', dict(state, pc=0x47da5), ram, pvc, bank, 0xff000), ('unrouted_error', dict(state, pc=END_STOP), ram, pvc, bank, 0xff000)] + list(extra_cases)
    count = 0
    for label, st, r, p, b, stop in cases:
        a = invoke(ctx.exe, RUN_DIR, 'eq_batch_' + label, r, st, p, b, ctx.resources, stop, 0)
        o = invoke(ctx.exe, RUN_DIR, 'eq_oneshot_' + label, r, st, p, b, ctx.resources, stop, 0, oneshot=True)
        assert a[0] == o[0] and a[1:4] == o[1:4] and a[4].strip() == o[4].strip(), (label, a[0], o[0])
        count += 1
    return count


# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve().name == 'animation_machine_area_clear_execution'
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='area_clear_verify_'))
    try:
        run(report_path)
    finally:
        for srv in SERVERS:
            srv.close()
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def scan_old_expectations(st):
    """Old verifiers / tests that name an even PC of the six F1b ranges as a literal (read only; a PC that was an unrouted probe before F1b is now a block start or an interior PC)."""
    pcs = set(st['even_pcs'])
    files = sorted((Path(MAIN_ROOT) / 'tools').glob('verify_animation_machine*.py')) + sorted((ROOT / 'engine/tests').glob('animation_machine*_test.cpp'))
    rows = []
    for path in files:
        if 'area_clear' in path.name:
            continue
        found = collections.OrderedDict()
        for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            for m in re.finditer(r'0x([0-9a-fA-F]{3,6})\b', line):
                pc = int(m.group(1), 16)
                if pc in pcs:
                    found.setdefault(number, []).append(hex(pc))
        for number, hits in found.items():
            note = 'stop PC (stop is checked before routing): unaffected' if 'transition' in path.name else 'literal PC of an F1b range: check the expectation'
            rows.append(dict(file=('tools/' if path.suffix == '.py' else 'engine/tests/') + path.name, line=number, pcs=sorted(set(hits)), note=note))
    return rows


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_area_clear.py', 'tools/observe_animation_machine_area_clear.py', 'docs/analysis/animation-machine-area-clear-f1b-contract.md',
                 'engine/src/animation_machine_area_clear.cpp', 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h'):
        inputs[name] = cc.digest(ROOT / name)
    test = ROOT / 'engine/tests/animation_machine_area_clear_test.cpp'
    if test.exists():
        inputs['engine/tests/animation_machine_area_clear_test.cpp'] = cc.digest(test)
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
    st = audit_static(program)
    ctx = Ctx()
    ctx.exe, ctx.resources, ctx.st, ctx.start_set = exe, resources, st, set(st['starts'])
    rows = report['results']
    if DEBUG_LABELS:
        rows = [r for r in rows if r['label'] in DEBUG_LABELS or r['group'] in DEBUG_LABELS]
    elif API_ONLY:
        rows = []
    # every native blob is content addressed: hash all of them once
    blob_dir = NATIVE_DIR / 'blobs'
    blob_names = sorted(os.listdir(blob_dir))
    assert len(blob_names) == report['blob_count'] == 8882
    for name in blob_names:
        assert sha((blob_dir / name).read_bytes()) == name.split('.')[0], name
    # base state of the API-only checks: natural seed 0 frame 0
    base_row = [r for r in report['results'] if r['label'] == 'natural-000'][0]
    fx0 = base_row['fixture']
    base = (read_blob(fx0['initial_RAM_sha256'] + '.bin'), dict(fx0['initial_regs'], a7=fx0['initial_a7'], pc=fx0['entry_pc'], carry=2), read_blob(fx0['initial_PVC_sha256'] + '.bin'), fx0['bank_state'][0])
    wait_row = [r for r in report['results'] if r['label'] == 'sound-ring-full-0'][0]
    fxw = wait_row['fixture']
    extra = [('sound_wait_frame0', dict(fxw['initial_regs'], a7=fxw['initial_a7'], pc=fxw['entry_pc'], carry=0), read_blob(fxw['initial_RAM_sha256'] + '.bin'),
              read_blob(fxw['initial_PVC_sha256'] + '.bin'), fxw['bank_state'][0], FRAME_RET)]
    equivalence = harness_equivalence(ctx, base, extra)
    results = replay_all(ctx, report, rows)
    failures = [(r['label'], a['error']) for r, a in zip(rows, results) if 'error' in a]
    if failures:
        for label, text in failures[:30]:
            print('CONDITION FAILED', label, text.strip().splitlines()[-1][:400])
        print(failures[0][1])
        raise AssertionError('%d conditions failed' % len(failures))
    totals, carry_stops, guards, out_rows, probes, consumers_seen = collections.Counter(), collections.Counter(), [], [], {}, collections.Counter()
    starts_seen, problems = set(), []
    for r, a in zip(rows, results):
        totals.update(a['totals'])
        carry_stops.update(a['carry_stops'])
        starts_seen |= a['starts_seen']
        problems.extend(a['failures'])
        out_rows.append(a['out_row'])
        if a['guard']:
            guards.append(a['guard'])
        for pc, slots in a['probes'].items():
            slot = probes.setdefault(pc, {1: True, 2: True})
            for k in (1, 2):
                slot[k] = slot[k] and slots[k]
    assert not problems, problems[:10]
    preserve = set(st['preserving'])
    observed_preserving = sorted(pc for pc, slots in probes.items() if slots[1] and slots[2])
    if not DEBUG_LABELS and not API_ONLY:
        assert starts_seen >= set(st['starts']) - {0x47e0e}, sorted(hex(p) for p in set(st['starts']) - starts_seen)
        assert set(observed_preserving) == preserve and set(probes) >= set(st['starts']), sorted(hex(p) for p in set(st['starts']) - set(probes))
        for pc in CONSUMERS:
            assert any(k.startswith('consumer_flip_%x_incoming_' % pc) for k in totals), hex(pc)
        assert len(out_rows) == 256
        assert totals['frames'] + totals['guard_frames'] == report['totals']['frames'], (totals['frames'], totals['guard_frames'])
        assert totals['split_phases'] == report['totals']['split_phases'], (totals['split_phases'], report['totals']['split_phases'])
        assert totals['continuous_runs'] == report['totals']['control_phases']
        assert len(VERIFIED_BLOBS) > 0
    guard_labels = sorted(g['label'] for g in guards)
    # ------------------------------------------------------------------------------ API-only
    negative, consumer_controls = negatives(ctx, base, st)
    zero = run_parallel(zero_step_one, [(ctx, base, pc, carry) for pc in st['starts'] for carry in (0, 1, 2)])
    cases, cpp_carry, cpp_ranges = cpp_static(st)
    assert cases == set(st['starts']), sorted(hex(p) for p in cases ^ set(st['starts']))
    assert cpp_ranges == sorted(F1B_RANGES), cpp_ranges
    assert cpp_carry == preserve, (sorted(hex(p) for p in cpp_carry ^ preserve))
    for name, expected in inputs.items():
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs = dict(refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log', OUT / 'harness_batch.cpp', OUT / 'compile_batch.log'):
        refs[str(path.resolve())] = cc.digest(path)
    old = scan_old_expectations(st)
    result = dict(
        schema_version=1, source=source, inputs=inputs, artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, cpp_sha256=CPP_SHA, contract_sha256=CONTRACT_SHA,
        native_counts=dict(conditions=report['conditions'], groups=report['groups'], frames=report['totals']['frames'], split_phases=report['totals']['split_phases'],
                           control_phases=report['totals']['control_phases'], dumped_frames=report['totals']['dumped_frames'], blobs=report['blob_count']),
        native_blobs_hash_checked=len(blob_names), native_blobs_read_for_comparison=len(VERIFIED_BLOBS),
        contract_ranges=[dict(range='%x..%x' % r, size=r[1] - r[0]) for r in st['table']], block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']],
        interior_PC_count=len(st['interior']), bundled_branches=[hex(p) for p in st['bundled']], carry_preserving_blocks=[hex(p) for p in st['preserving']],
        carry_consumers=[hex(p) for p in CONSUMERS], cpp_case_labels_equal_contract_block_starts=len(cases), cpp_routing_ranges_equal_6=True, cpp_carry_preserving_table_in_unit_equals_16=True,
        observed_carry_preserving_blocks_through_cpp=[hex(p) for p in observed_preserving],
        carry_probed_blocks={hex(pc): dict(incoming_Clear_preserved=bool(slots[1]), incoming_Set_preserved=bool(slots[2])) for pc, slots in sorted(probes.items())},
        actual_CPP=dict(sorted(totals.items())), conditions=out_rows,
        carry_at_stops={k: v for k, v in sorted(carry_stops.items())},
        native_guards_checked_API=guards, native_guard_count=len(guards),
        deliberate_differences=dict(count=sum(1 for g in guards if g['classification'] != 'same_check_class'), rows=[g for g in guards if g['classification'] != 'same_check_class']),
        negatives=negative, negative_count=len(negative), consumer_controls=consumer_controls, zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2],
        harness_equivalence_cases=equivalence,
        invalidated_expectation_candidates=old,
        carry_check='C is a block classification (native SR is never read): the three consumers 1c5bc 1c5d8 47e0a take a Known C produced by the callee inside the run (289e formula '
                    'checked against the C++ RAM, the native branch path checked from the dumped native PC trace, the full-state SHA equality of every frame), flip controls select the other '
                    'destination (47e0a also the SCC.B 62(A6) byte), Unknown at a consumer gives the exact error; single-block probes with incoming C 1 / 2 on every distinct F1b start observed in a '
                    'dumped frame reproduce the 16 FLOW_ONLY blocks; waits report Unknown (API wait contract)',
        compile_command=command, compile_batch_command=scommand, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (the recorded final RAM of the 137 original stage_entry_body begin runs, declared typed variants), not natural scheduler, IRQ or gameplay reachability; '
                'one machine run is one frame and the next frame is a declared direct re-entry (PC redirect + A7 delta + return LONG 2ac2); children e4234 / d72fe never run.',
                'Native SR is not observed; the initial SR is a declared fixture value (2000 / 2001 only for the direct consumer entries).',
                'Existing executors (U1..U7, cleanup, fade_card, F1a 9060, sound, exit, input) are compared as whole results; their interior is not modelled here.',
                'Native split-phase intermediate RAM is not stored (only the per-frame digests): split intermediate registers are compared with the native leader registers of the dumped trace '
                '(first arrival of each checkpoint when it is a recorded leader), the final split state equals the continuous C++ run equals the native frame.',
                'Checked failures preserve API outputs, not original CPU fault rollback; deliberate differences are listed with counts.',
                'No BIOS execution, no natural scheduler, no natural IRQ is claimed.'])
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(conditions=len(out_rows), frames=totals['frames'], guard_frames=totals['guard_frames'], split_phases=totals['split_phases'], continuous=totals['continuous_runs'],
                          negatives=len(negative), zero_step=len(zero), guards=len(guards), deliberate=result['deliberate_differences']['count'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
