"""Stage controller F1c2 (area and player initialisation 479b0..47a94 with the helpers 3d3a 1bcfe/1bd12/1bd2e/1bd90 1be84 2ef90/2efdc 46f2e 48180/481de 4d81c 49a58 49a8e
4aa30 4d126/4d13c 4ddb6 4e666 b4806/b4a24 b7a20 d760a, player placement 476dc, first-area initialisation 47594/475ca) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection.  The frozen native observation (artifacts/animation_machine_stage_area_native) is an immutable input: this verifier
never invokes the observer main and never imports the observer module.  Every frame of every native condition (753 conditions, 3735 frames) is replayed against the
actual C++ `run_animation_machine` (one run = one frame, stop 2ac2 after the dispatcher RTS, or the F1a body 47a94 / the 4d824 and 4d7f0 boundaries):
  * per frame the full 64 KiB RAM / 16 registers / PC / A7 / PVC / bank / ordered ports / external reads / status of the actual C++ output are compared with the native
    record: the native full-state SHA256 (observation frame_state_sha256_definition, recomputed here from the C++ output with the same formula), the RAM / PVC / ports
    SHA256 and the stored dump bytes (every frame of the observation is dumped);
  * every frame resumes ONLY from the previous actual C++ output plus the declared host changes of the native step (RAM writes, the declared direct re-entry
    PC redirect / A7 delta, the declared sound / sprite release writes); the native input state is never injected (dumps only assert it);
  * continuous C++ run of each frame vs the split C++ chain that stops at every checkpoint of the native step (first arrival, same order, directly after the transferring
    instruction) vs the native frame; a wait (3aea / cda4) gives AnimationMachineWaiting at the same PC / A7 and resumes by the declared release write;
  * carry = block classification observed through the actual C++: the five consumers 47716 47732 4776c 1bd34 1bd96 take a Known C produced by the 289e callee (289e formula /
    native branch path), flip controls select the other destination, single-block probes with incoming C 1 / 2 on every distinct F1c2 start observed in a dumped frame give the
    FLOW_ONLY table (77 blocks) back, Unknown at a consumer gives the exact error `stage area caller requires known carry`; native SR is never read;
  * native guards -> exact checked C++ error strings + full preservation; the RNG pointer policy rows (rng_pointer_outside_ram / rng_pointer_high_byte) and the deliberate
    differences are classified by explicit rules and counted;
  * API-only negatives: all 636 interior PCs, odd and out-of-range PCs, non-routed neighbours, 4d824 / 4d7f0 without a stop, zero-step at every one of the 153 starts x 3 carries.
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
OUT = ROOT / 'artifacts/animation_machine_stage_area_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_stage_area_native'
NATIVE_SHA = '851281ab5037a7daac6d1831d814406057245839271ed3591df225e4ce2b44ca'
NATIVE_TOOL_SHA = '80f890edced7d875607f9dfbd924ce302e3db12703db1df4e03f1c41bb4bb82a'
CONTRACT = ROOT / 'docs/analysis/animation-machine-stage-catalog-f1c-contract.md'
CONTRACT_SHA = 'f374c80f3528d5200aaa870bd66e8a58d09b400db7a84c8ee3a89fddd474a575'
CPP_SHA = 'dd273339b0a98d71bdf4f1b492e9354079c399f99eea0c7ad4ad078e43eb8d10'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
S = 0x1feffc
FRAME_RET = 0x2ac2
FINAL_STOP = 0x47a94
TRAP_STOP = 0x4d824                       # TRAP #15 boundary of 4d81c (D1.W >= 14): stop only, never routed
U6_TRAP_STOP = 0x4d7f0                    # U6 boundary (stop only)
WAIT_PCS = (0xcda4, 0x3aea)
F1C2_RANGES = ((0x3d3a, 0x3d44), (0x1bcfe, 0x1bdde), (0x1be84, 0x1be98), (0x2ef90, 0x2efa6), (0x2efdc, 0x2eff4), (0x46f2e, 0x46f52), (0x47594, 0x47642), (0x476dc, 0x477a2),
               (0x479b0, 0x47a54), (0x47a64, 0x47a94), (0x48180, 0x481b2), (0x481de, 0x48210), (0x49a58, 0x49a84), (0x49a8e, 0x49ab0), (0x4aa30, 0x4aa86), (0x4d126, 0x4d196),
               (0x4d81c, 0x4d84e), (0x4ddb6, 0x4ddde), (0x4e666, 0x4e68e), (0xb4806, 0xb481e), (0xb4a24, 0xb4a2a), (0xb7a20, 0xb7a28), (0xb7a2e, 0xb7a62), (0xd760a, 0xd764a))
CONSUMERS = (0x1bd34, 0x1bd96, 0x47716, 0x47732, 0x4776c)
CONSUMER_TARGETS = {0x47716: (0x4771a, 0x47724), 0x47732: (0x47736, 0x47740), 0x4776c: (0x47770, 0x47788), 0x1bd34: (0x1bd38, 0x1bd3a), 0x1bd96: (0x1bd9a, 0x1bd9c)}   # (C Clear, C Set)
BB_ENTRIES = (0x289e, 0x28ae, 0x2a28, 0x2a48, 0x3af8, 0x3c84, 0x3d44, 0x3dce, 0x43dda, 0x477c2, 0x49c32, 0x4ab88, 0x4d7a6, 0x6f1c2, 0xb483e, 0xe7c36, 0xe89fa)
REG16 = tuple('d%d' % i for i in range(8)) + tuple('a%d' % i for i in range(8))
UNKNOWN_CARRY = 'stage area caller requires known carry'
UNSUPPORTED_AREA = 'unsupported animation stage area PC'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNALIGNED_PC = 'unaligned animation machine PC'
RNG_ERROR = 'stage area RNG pointer outside work RAM'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
WRITE_DEVICE = 'unsupported animation machine write device'
TRAP15 = 'animation cleanup original TRAP15: nonzero object type'
BUDGET = 'animation machine block budget exceeded'
STATE_SHA_PREFIX = b'F1C2-FRAME-STATE-v1'
VERIFIED_BLOBS = set()
RUN_DIR = None
WORKERS = int(os.environ.get('STAGE_AREA_WORKERS', '3'))
DEBUG_LABELS = [x for x in os.environ.get('STAGE_AREA_DEBUG_LABELS', '').split(',') if x]    # development switch only: the reported run is always the full set
API_ONLY = bool(os.environ.get('STAGE_AREA_API_ONLY'))                                  # development switch only
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
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{3,6})`', text)]


def parse_contract(program):
    """F1c2 ranges (bytes equal to the original), block starts, bundled branches, carry consumers and FLOW_ONLY blocks from the contract text."""
    lines = CONTRACT.read_text().splitlines()
    table = []
    pat_r = re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| `([0-9a-f]+)` \|$')
    for line in lines:
        m = pat_r.match(line)
        if m:
            low, high = int(m.group(1), 16), int(m.group(2), 16)
            assert program[low:high].hex() == m.group(3), hex(low)
            if (low, high) in F1C2_RANGES:
                table.append((low, high))
    assert table == list(F1C2_RANGES), 'the 24 contract ranges of F1c2'
    assert sum(h - l for l, h in table) == 1580, sum(h - l for l, h in table)
    sections = {}
    current = None
    for line in lines:
        if line.startswith('- **Block 시작 PC.**'):
            current = 'starts'
        elif line.startswith('- **묶인 조건분기 PC'):
            current = 'bundled'
        elif line.startswith('- **Carry 소비 block'):
            current = 'consumers'
        elif line.startswith('- **Carry 보존(FLOW_ONLY) block.**'):
            current = 'preserve'
        elif line.startswith('- **'):
            current = None
        if current and line.startswith('  - F1c2'):
            sections[current] = pcs_in(line)
    starts, bundled, consumers, preserve = sections['starts'], sections['bundled'], sections['consumers'], sections['preserve']
    assert len(starts) == len(set(starts)) == 153 and len(bundled) == len(set(bundled)) == 24 and len(preserve) == len(set(preserve)) == 77
    consumers = [x for x in consumers if x in set(starts)]          # the line also names the producer 289e and the constant 270e
    assert sorted(consumers) == sorted(CONSUMERS), [hex(x) for x in consumers]
    return table, starts, bundled, preserve


def audit_static(program):
    table, starts, bundled, preserve = parse_contract(program)
    instructions = RomInstructions(program)
    start_set = set(starts)
    inside = []
    for low, high in F1C2_RANGES:
        pc = low
        while pc < high:
            inside.append(pc)
            pc += instructions[pc]['size']
        assert pc == high, hex(low)
    assert len(inside) == 382, len(inside)       # 381 decoded instructions of the observer + the TRAP #15 at 4d824 (a boundary, not routed)
    names = lambda pc: instructions[pc]['mnemonic'].split('.')[0]
    traps = [pc for pc in inside if names(pc) == 'trap']
    assert traps == [TRAP_STOP]
    assert not [pc for pc in inside if names(pc) == 'rte' or names(pc) in ('addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')]
    # blocks derived from the instruction stream: from each start up to the first terminator / next start / end of the range
    derived = {}
    for start in starts:
        pcs, pc = [], start
        while True:
            pcs.append(pc)
            name = names(pc)
            end = name in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'trap') or name in ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
            end = end or (name == 'dbra' or name == 'dbf')
            following = pc + instructions[pc]['size']
            if end or following in start_set or not in_ranges(following, F1C2_RANGES):
                break
            pc = following
        derived[start] = pcs
    block_len = dict((start, len(pcs)) for start, pcs in derived.items())
    covered = collections.Counter(pc for p in derived.values() for pc in p)
    assert max(covered.values()) == 1 and set(covered) == set(inside) - {TRAP_STOP}, (len(covered), sorted(hex(x) for x in set(inside) ^ set(covered)))
    assert sum(block_len.values()) == 381
    flow = sorted(pc for pc in starts if all(names(p) in FLOW_ONLY for p in derived[pc]))
    assert flow == sorted(preserve), [hex(p) for p in set(flow) ^ set(preserve)]
    even_pcs = [pc for low, high in F1C2_RANGES for pc in range(low, high, 2)]
    interior = [pc for pc in even_pcs if pc not in start_set and pc != TRAP_STOP]
    assert len(even_pcs) == 790 and len(interior) == 636 and TRAP_STOP in even_pcs
    assert not set(bundled) & start_set and set(bundled) <= set(interior) and 0x4aa72 in bundled
    consumers = sorted(pc for pc in starts if names(pc) in ('bcc', 'bcs'))
    assert consumers == sorted(CONSUMERS) and all(block_len[pc] == 1 for pc in CONSUMERS)
    producers = [pc for pc in inside if names(pc) in ('ori', 'andi', 'eori') and re.search(r'\bccr\b', instructions[pc]['op_str'])]
    assert producers == []
    return dict(table=table, starts=starts, bundled=bundled, preserving=preserve, instructions=instructions, blocks=derived, block_len=block_len, interior=interior,
                inside=inside, even_pcs=even_pcs)


def cpp_static(st):
    """C++ case labels vs the 153 block starts, routing ranges, carry-preserving table in the unit vs the 77 FLOW_ONLY blocks."""
    text = (ROOT / 'engine/src/animation_machine_stage_area.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text))
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    in_unit = set(pc for pc in table if in_ranges(pc, F1C2_RANGES))
    start = machine.index('animation_stage_catalog_block(c);') + len('animation_stage_catalog_block(c);')
    route = machine[start:machine.index('animation_stage_area_block(c);', start)]
    ranges = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', route))
    assert 'next.pc!=0x4d824' in route and route.count('!=') == 1
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
    assert cc.digest(ROOT / 'tools/observe_animation_machine_stage_area.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'engine/src/animation_machine_stage_area.cpp') == CPP_SHA
    assert cc.digest(CONTRACT) == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert report['conditions'] == 753 == len(report['results']) == len(report['condition_files'])
    t = report['totals']
    assert t['frames'] == 3735 and t['split_phases'] == 63558 and t['control_phases'] == 3735 and t['fresh_frames_equal'] == 3735
    assert t['model_frames'] == t['model_frames_equal'] == 728 and t['dumped_frames'] == 3735
    assert sum(r['split_phases'] for r in report['results']) == 63558 and sum(r['steps'] for r in report['results']) == 3735
    assert sum(r['control_phases'] for r in report['results']) == 3735 and sum(r['dumped_frames'] for r in report['results']) == 3735
    assert report['block_starts_not_hit'] == [] and len(report['block_starts']) == 153
    assert report['block_starts_needing_typed_fixtures'] == ['0x476ec', '0x49a7c']
    assert report['boundary_frames'] == [0, 29, 188, 189, 235, 236, 237] and report['dump_seeds'] == [0, 60, 117, 118, 134, 126, 135, 141]
    assert report['groups'] == {'natural': 137, 'release-guard': 5, 'runtime': 236, 'area': 18, 'music': 16, 'players': 20, 'players-direct': 48, 'rng': 10, 'rng-guard': 14,
                                'rng-difference': 10, 'effect': 15, 'trap-boundary': 6, 'trap-guard': 2, 'lookup': 10, 'alloc': 4, 'area-direct': 26, 'sound': 16, 'guard': 7,
                                'zero-step': 153}
    assert [c['kind'] for c in report['contract_discrepancies']] == ['contract-contradicted']
    assert report['frame_state_sha256_definition'].startswith('sha256(b"F1C2-FRAME-STATE-v1"')
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
    directly from F1c2 code (the previous executed PC lies in an F1c2 range)."""
    lead_set = start_set | set(BB_ENTRIES)
    leads, last = [], initial_last
    for index, pc in enumerate(pcs[:-1]):
        if pc in lead_set and (pc in start_set or (last is not None and in_ranges(last, F1C2_RANGES))):
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


# Native guard -> expected checked C++ error (explicit, per condition, derived from reading the C++ unit and the bus rules, not from running it).
RNG_POLICY_LABELS = ['rng-outside-zero', 'rng-outside-rom-30', 'rng-outside-rom-fffc0', 'rng-outside-io-200000', 'rng-outside-bank-2fffff', 'rng-outside-ffffffff'] + \
    ['rng-policy-rejects-' + x for x in ('fffd0', 'fffd2', 'fffe0', 'ffff0', 'ffffc', 'ffffe')]
RNG_ORIGINAL_OUTSIDE = ['rng-original-outside-zero', 'rng-original-outside-rom-30', 'rng-original-outside-rom-fffc0', 'rng-original-outside-rom-fffce']
RNG_ORIGINAL_COMPLETES = ['rng-original-completes-' + x for x in ('fffd0', 'fffd2', 'fffe0', 'ffff0', 'ffffc', 'ffffe')]
RNG_HIGH_BYTE = 'rng-outside-high-ff10d720'
GUARD_EXPECTED = {
    'release-guard-136': EVEN, 'release-guard-137': EVEN, 'release-guard-138': EVEN, 'release-guard-139': EVEN, 'release-guard-140': EVEN,   # odd WORD read (U1 3c60 / 3bb2)
    'rng-odd': EVEN,                                                         # 49a58: odd pointer inside the work RAM, odd WORD read
    '481de-trap-no-stop': UNSUPPORTED_MACHINE,                                # 4d824 is a stop only
    '48180-u6-trap-undeclared': UNSUPPORTED_MACHINE,                          # 4d7f0 is a stop only (U6)
    'd760a-28ae-empty-list': WRITE_DEVICE,                                    # 28ae writes through a NULL free-list head (address 0xc)
    '475ca-players-alive-null-8c': WRITE_DEVICE,                              # 1bdcc CLR.B 2(A4) with A4 = 0 (ROM address 2)
    'guard-odd-a7-476dc': EVEN,                                               # odd A7: LONG push of the JSR / BSR return PC
    'guard-odd-a6-479b0': EVEN,                                               # TST.B 7d(A6) is BYTE; the WORD read 7c(A6) at 476dc sees the odd address 100b41
    'guard-odd-record-47a1c': EVEN,
    'guard-odd-a5-1bd12': EVEN_WRITE,                                         # CLR.W 5478(A5) through an odd A5
    'guard-odd-a0-1bd2e': EVEN,
    'guard-node-depth-47770': TRAP15,                                         # 2a28 nonzero object type -> TRAP #15 of the cleanup unit
    'guard-odd-a1-pointer-47724': EVEN}
for _label in RNG_POLICY_LABELS + RNG_ORIGINAL_OUTSIDE:
    GUARD_EXPECTED[_label] = RNG_ERROR
# Guards whose native reason and C++ error are not the same check; every one is a rejection at the same split-segment unless the note says otherwise.
GUARD_NOTES = {
    'd760a-28ae-empty-list': ('native_ROM_write_vs_cpp_write_device', 'the 28ae free list is empty: the original writes through 0 + c (ROM / vector area, ignored by real hardware); native '
                              'unmapped_or_protected, C++ rejects with the write-device check; no rollback equivalence claimed'),
    '475ca-players-alive-null-8c': ('native_ROM_write_vs_cpp_write_device', 'NULL child pointer 8c(A0): native unmapped_or_protected write of a BYTE to address 2 (ROM), C++ write-device check'),
    'guard-node-depth-47770': ('native_unsupported_TRAP_vs_cpp_cleanup_TRAP15_check', 'the native cleanup path reaches the original TRAP #15; the C++ cleanup unit reports its checked TRAP15 error'),
    'guard-odd-a7-476dc': ('native_odd_write_vs_cpp_odd_stack_access', 'odd A7: native odd LONG write (JSR push) address error, C++ odd stack access check (same class, different layer message)'),
    '481de-trap-no-stop': ('native_unsupported_code_target_vs_cpp_unrouted_PC', 'TRAP #15 at 4d824 reached without its declared stop: native unsupported_code_target, C++ unsupported animation machine PC (4d824 is not routed)'),
    '48180-u6-trap-undeclared': ('native_unsupported_TRAP_vs_cpp_unrouted_PC', 'U6 TRAP #15 at 4d7f0 reached without its declared stop: native unsupported_TRAP, C++ unsupported animation machine PC (4d7f0 is a stop only)'),
    'rng-original-outside-zero': ('native_original_ROM_write_vs_cpp_RNG_policy', 'policy disabled: the original SUB.W writes into ROM (unmapped_or_protected at 49a80, address 0x30); the C++ rejects at the entry of 49a58 with the RNG pointer check'),
    'rng-original-outside-rom-30': ('native_original_ROM_write_vs_cpp_RNG_policy', 'policy disabled: native write to ROM address 0x60; C++ RNG pointer check at the entry of 49a58'),
    'rng-original-outside-rom-fffc0': ('native_original_ROM_write_vs_cpp_RNG_policy', 'policy disabled: native write to address ffff0 (below the work RAM); C++ RNG pointer check at the entry of 49a58'),
    'rng-original-outside-rom-fffce': ('native_original_ROM_write_vs_cpp_RNG_policy', 'policy disabled: native write to address ffffe; C++ RNG pointer check at the entry of 49a58')}
RNG_SEGMENT_DIFFERS = set(RNG_ORIGINAL_OUTSIDE)         # the native fault happens in a later split phase (49a80) than the C++ rejection (entry of 49a58)


# ----------------------------------------------------------------------------------------------------------------- condition replay
class Ctx(object):
    pass


def compile_server(root, folder):
    path = folder / 'harness_batch.cpp'
    path.write_text(HARNESS_SERVER)
    exe = folder / 'animation_machine_stage_area_batch_harness'
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
    """Destination of the five stage area carry consumers for a known C (1 Clear, 2 Set)."""
    assert carry in (1, 2)
    return CONSUMER_TARGETS[pc][0 if carry == 1 else 1]


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
    for initial_last in (None,):
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
    prev_ff = ('%x' % fx['bank_state'][1], '%x' % fx['bank_state'][2])
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
        if label in RNG_ORIGINAL_COMPLETES:
            assert not guarded and j == len(cond['steps']) - 1 and len(cond['steps']) == 1, (label, j)
            difference_complete_row(ctx, acc, result, row, step, ram, state_in, pvc, bank, cont, phases, how, stop, external, trace, start_set)
            totals['difference_frames'] += 1
            break
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
        pvc_written = trace is not None and any(e['access'] == 'write' and 0x2fe000 <= e['address'] < 0x300000 for e in trace['events'])
        if pvc_written:
            assert '%x' % int.from_bytes(out_pvc[0x1ff0:0x1ff2], 'big') == row['ff8'] and '%x' % int.from_bytes(out_pvc[0x1ff2:0x1ff4], 'big') == row['ff9'], (label, j)
            totals['bank_registers_equal_native_after_pvc_writes'] += 1
        else:
            # no PVC write in the frame: the native raw bank registers are the declared input values; the C++ image only carries the normalized registers
            assert (row['ff8'], row['ff9']) == prev_ff, (label, j, row['ff8'], row['ff9'], prev_ff)
            totals['frames_without_pvc_write_bank_registers_not_in_cpp_image'] += 1
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
        prev_ff = (row['ff8'], row['ff9'])
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
    if label == RNG_HIGH_BYTE:
        return high_byte_row(ctx, acc, result, row, step, ram, state_in, pvc, bank, cont, phases, how, stop, external)
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
    note = GUARD_NOTES.get(label)
    entry['classification'] = note[0] if note else 'same_check_class'
    entry['rule'] = note[1] if note else None
    acc['guard'] = entry
    if expected is None or error != expected:
        acc['failures'].append(('guard error', label, error, expected))
    if not entry['same_split_segment_as_native'] and label not in RNG_SEGMENT_DIFFERS:
        acc['failures'].append(('guard segment', label, len(phases), row['split_phases']))


def model_rng(ram, a5=0x108000):
    """Independent Python model of the 49a58 block (and the RTS is not part of it): returns (new RAM bytes, D0 low WORD, final A3, final A4) or an error text.  Addresses are the 24 bit
    bus addresses, the compares and the pointer arithmetic are 32 bit unsigned like the CPU registers."""
    a4 = (a5 + 0x5722) & M32
    buf = bytearray(ram)

    def at(address, size):
        a = address & 0xffffff
        if a & 1:
            return None
        if not (0x100000 <= a and a + size <= 0x200000):
            return None
        return a & 0xffff
    off = at(a4, 4)
    a3 = int.from_bytes(buf[off:off + 4], 'big')
    if not (0x100000 <= (a3 & 0xffffff) < 0x200000):
        return RNG_ERROR
    off = at(a3, 2)
    if off is None:
        return EVEN
    w = int.from_bytes(buf[off:off + 2], 'big')
    a3 = (a3 + 2) & M32
    if not a3 < a4:
        a3 = (a3 - 0x6e) & M32
    buf[at(a4, 4):at(a4, 4) + 4] = a3.to_bytes(4, 'big')
    a3 = (a3 + 0x2e) & M32
    if not a3 < a4:
        a3 = (a3 - 0x6e) & M32
    off = at(a3, 2)
    if off is None:
        return 'model: second access outside the work RAM / odd'
    v = int.from_bytes(buf[off:off + 2], 'big')
    buf[off:off + 2] = ((v - w) & 0xffff).to_bytes(2, 'big')
    return bytes(buf), w, a3, a4


def high_byte_row(ctx, acc, result, row, step, ram, state_in, pvc, bank, cont, phases, how, stop, external):
    """rng-outside-high-ff10d720: the native observation is impossible (Unicorn does not mask the top byte), the observer classifies it as rng_pointer_high_byte.  The C++ masks the
    24 bit address for the work RAM check and for the bus access; this row reports what the C++ actually does and checks it against the independent model."""
    label = result['label']
    res, out_ram, out_pvc, out_ports, error = cont
    entry = dict(label=label, group=result['group'], native_guard=row['guard'], native_guard_reason=row['guard'].get('reason'), native_split_phases=row['split_phases'],
                 pointer='%08x' % row['guard']['pointer'], pointer24='%06x' % row['guard']['pointer24'], cpp_ok=bool(res['ok']), cpp_error=error.strip(),
                 native_fault_rollback_equivalence_claimed=False)
    model = model_rng(ram)
    if res['ok']:
        assert not error and res['status'] == 0 and res['pc'] == stop, (label, error)
        last = phases[-1]['actual']
        assert how == 'stop' and last[0]['ok'] and last[1] == out_ram and last[2] == out_pvc and out_state(last[0]) == out_state(res)
        assert b''.join(p['actual'][3] for p in phases) == out_ports
        entry['outcome'] = 'cpp_completes'
        entry['split_chain_equals_continuous'] = True
        entry['ram_bytes_changed_vs_input'] = sum(1 for x, y in zip(ram, out_ram) if x != y)
        entry['changed_ranges'] = changed_ranges(ram, out_ram)
        entry['model_ok'] = not isinstance(model, str)
        if not isinstance(model, str):
            m_ram, w, a3, a4 = model
            # the full frame is 49a58 + RTS: the model RAM equals the C++ RAM except the RTS pops (no RAM change)
            entry['model_ram_equals_cpp'] = m_ram == out_ram
            entry['model_d0_low_word_equals_cpp'] = (res['d0'] & 0xffff) == w
            entry['model_a3_a4_equal_cpp'] = res['a3'] == a3 and res['a4'] == a4
            assert entry['model_ram_equals_cpp'] and entry['model_d0_low_word_equals_cpp'] and entry['model_a3_a4_equal_cpp'], label
        entry['final_a3'] = '%08x' % res['a3']
        entry['final_a4'] = '%08x' % res['a4']
        entry['note'] = ('native: no observation (Unicorn does not mask the top byte).  C++: the work RAM check and the bus access use the 24 bit address 10d720, the register compares '
                         'stay 32 bit (A3 = ff10d722 is not below A4 = 10d722, so both wrap subtractions apply): the run completes and agrees with the independent model.  '
                         '[I] this equals the M68000 bus behaviour (24 address lines) and is NOT a rejection; it is not backed by a native observation.')
    else:
        entry['outcome'] = 'cpp_rejects'
        check_preserved(cont, ram, state_in, pvc, bank)
        entry['note'] = 'C++ rejects the high byte pointer'
    entry['classification'] = 'rng_high_byte_cpp_masks_24bit_completes' if res['ok'] else 'rng_high_byte_cpp_rejects'
    acc['guard'] = dict(entry, checked_API_error=error.strip(), expected_API_error=None, cpp_error_matches_expected=None, same_split_segment_as_native=None, rule=entry['note'],
                        cpp_phases_before_error=None, all_API_outputs_preserved=not res['ok'], state_with_other_carries={})
    acc['high_byte'] = entry


def changed_ranges(a, b):
    out, start = [], None
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y and start is None:
            start = i
        if x == y and start is not None:
            out.append('%x..%x' % (0x100000 + start, 0x100000 + i))
            start = None
    if start is not None:
        out.append('%x..%x' % (0x100000 + start, 0x100000 + len(a)))
    return out


def difference_complete_row(ctx, acc, result, row, step, ram, state_in, pvc, bank, cont, phases, how, stop, external, trace, start_set):
    """rng-original-completes-*: native Unicorn (original behaviour, policy disabled) completes the frame with a pointer below the work RAM; the C++ deliberately rejects at the entry of
    49a58 with the RNG pointer check.  Everything before the rejected block is compared (checkpoint registers), the rejection must be exactly the declared error with full preservation."""
    label = result['label']
    error = check_preserved(cont, ram, state_in, pvc, bank, RNG_ERROR)
    first_failed = None
    for index, p in enumerate(phases):
        if not p['actual'][0]['ok']:
            first_failed = index
            e_ram, e_state, e_pvc, e_bank = p['entry']
            assert check_preserved(p['actual'], e_ram, e_state, e_pvc, e_bank, RNG_ERROR) == error
    assert how == 'error' and first_failed == len(phases) - 1, (label, how)
    # the pointer the rule talks about
    pointer = int.from_bytes(ram[0xd722:0xd726], 'big')
    assert pointer < 0x100000 and state_in['pc'] == 0x49a58
    first = native_leader_regs(row, trace, start_set) if trace else {}
    compared = 0
    for p in phases[:-1]:
        res = p['actual'][0]
        native = (first or {}).get(p['target'])
        if native is not None and native[0] == 0:
            assert {k: res[k] for k in REG16} == {k: native[1][k] for k in REG16} and res['pc'] == p['target']
            compared += 1
    # the native frame completed normally: it is compared as a native observation only (state SHA of the declared frame is recorded, not reproduced by the C++)
    assert row['stop_kind'] == 'return' and row['out_pc'] == '2ac2' and 'guard' not in row
    entry = dict(label=label, group=result['group'], native_guard=None, native_guard_reason='none: the original completes the frame (policy disabled)', checked_API_error=error,
                 expected_API_error=RNG_ERROR, cpp_error_matches_expected=True, continuous_run_error=error, split_chain_error=error, cpp_phases_before_error=len(phases) - 1,
                 native_split_phases=row['split_phases'], same_split_segment_as_native=False, all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False,
                 state_with_other_carries={}, pointer='%08x' % pointer, native_completes_final_pc=row['out_pc'], native_final_state_sha256=row['state_sha256'],
                 classification='native_original_completes_vs_cpp_RNG_policy_rejects', checkpoint_registers_compared_before_rejection=compared,
                 rule='policy disabled in the native observation (the original SUB.W writes into ROM / below the work RAM address range and the frame completes); the C++ rejects the pointer %08x '
                      'at the entry of 49a58 (F1c contract decision 9, checked error, state preserved).  Deliberate difference, no rollback equivalence claimed' % pointer)
    for carry in (0, 1, 2):
        if carry == state_in['carry']:
            continue
        s2 = dict(state_in, carry=carry)
        again = inv(ctx, 'c%03d_diff_carry%d' % (result['number'], carry), ram, s2, pvc, bank, stop, external)
        entry['state_with_other_carries'][CARRY_NAME[carry]] = check_preserved(again, ram, s2, pvc, bank, RNG_ERROR)
    acc['guard'] = entry
    acc['difference_complete'] = entry


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
            if index != 0:
                # 289e formula: Clear iff LONG (A0) == 270e
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
            assert again[1] == s_ram          # the consumers are Bcc only: no RAM write
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
        if nxt == pc:
            # self-loop block (4aa50 16x, 4aa6e 256x): probe the whole loop up to its exit (the carry of a non-FLOW_ONLY block is Unknown at the exit either way)
            members = set(ctx.st['blocks'][pc])
            nxt = next(x for x in pcs[index + n:] if x not in members)
            totals['self_loop_probe_to_exit'] += 1
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
def superseded_stage_area_neighbour_prefix(ctx, label, ram, state, pvc, bank):
    """Original prefix to H1 raster block; empty queue remains a checked boundary."""
    import ctypes
    import unicorn
    # The shared native classes are imported only for these four controls. Bind
    # their exact immutable sources before import and again after execution.
    oracle_sources = {
        'observe_animation_machine_scheduler.py': '62bb23ff6d2f61a5e47af71b8e1308d50c99b85d95f3278b8d825b7ee327c01c',
        'observe_animation_machine_pvc_banks.py': '86ebf962e3b83eef6882c1f96845c117edfa735c3137960b1cbda6623768d3a0'}
    for name, expected in oracle_sources.items():
        assert cc.digest(ROOT / 'tools' / name) == expected
    import observe_animation_machine_scheduler as scheduler
    import observe_animation_machine_pvc_banks as pvc_native
    library = Path(scheduler.uclib._name).resolve()
    library_before = cc.digest(library)
    manifest = ROOT / 'extracted/program/manifest.json'
    manifest_before = cc.digest(manifest)
    wrapper_files = sorted(Path(unicorn.__file__).resolve().parent.rglob('*.py'))
    oracle_wrappers = {str(path): cc.digest(path) for path in wrapper_files}
    program, source = load_verified_program(ROOT)
    assert sha(program) == ROM_SHA
    # Native BSET #7,d16(A5); MOVE.W 3c0006.l,D0 inside public block ea4.
    assert program[0xea4:0xeb0].hex() == '08ed0007801b3039003c0006'
    fixed = (ctypes.c_ubyte * 0x100000).from_buffer_copy(program[:0x100000])
    snap = dict(ram=ram, regs={key: state[key] for key in REG16}, pc=state['pc'],
                bank=(bank, int.from_bytes(pvc[0x1ff0:0x1ff2], 'big'),
                      int.from_bytes(pvc[0x1ff2:0x1ff4], 'big')))
    machine = pvc_native.PvcMachine(program, fixed, snap)
    machine.install_basic_hooks()
    machine.cpu.mem_write(0x2fe000, pvc)
    machine.cpu.reg_write(scheduler.UC_REG['sr'], 0x2001)
    trace, reached = [], []
    def code(cpu, pc, size, unused):
        trace.append(pc)
        if pc == 0xea4:
            reached.append(pc)
            cpu.emu_stop()
    hook = machine.cpu.hook_add(unicorn.UC_HOOK_CODE, code)
    machine.cpu.emu_start(state['pc'], 0xffffff, count=1000000)
    assert reached and not machine.odd and not machine.invalid and not machine.intr
    assert not machine.dev_reads
    expected_regs = machine.regs()
    expected_ram = machine.ram()
    expected_pvc = bytearray(machine.cpu.mem_read(0x2fe000, 8192))
    expected_pvc[0x1ff0:0x1ff4] = struct.pack('>HH', machine.ff8, machine.ff9)
    expected_ports = b''.join(struct.pack('>BII', size, address, value)
                              for kind, address, size, value in machine.ports)
    expected_bank = machine.bank
    actual = inv(ctx, 'superseded_prefix_' + label, ram, state, pvc, bank, 0xea4, 0)
    result, out_ram, out_pvc, ports, error = actual
    assert result['ok'] and not error and result['pc'] == 0xea4 and result['status'] == 0
    assert {key: result[key] for key in REG16} == expected_regs
    assert out_ram == expected_ram and out_pvc == bytes(expected_pvc)
    assert ports == expected_ports and result['bank_base'] == expected_bank and result['external_reads'] == 0
    # Reached instruction eaa is the first external read. Do not provide input
    # or claim its state equals a completed instruction with an empty queue.
    machine.cpu.hook_del(hook)
    external = []
    def read(cpu, access, address, size, value, unused):
        external.append((address, size, cpu.reg_read(scheduler.UC_REG['pc'])))
        cpu.emu_stop()
    machine.cpu.hook_add(unicorn.UC_HOOK_MEM_READ, read, begin=0x300000, end=0x3fffff)
    machine.cpu.emu_start(0xea4, 0xffffff, count=20)
    assert external == [(0x3c0006, 2, 0xeaa)]
    assert not machine.odd and not machine.invalid and not machine.intr
    for name, expected in oracle_sources.items():
        assert cc.digest(ROOT / 'tools' / name) == expected
    assert cc.digest(library) == library_before
    assert cc.digest(manifest) == manifest_before
    assert oracle_wrappers == {str(path): cc.digest(path) for path in wrapper_files}
    return dict(stop_pc='0xea4', first_external_address='0x3c0006', first_external_size=2,
                first_external_CPU_pc='0xeaa', source_ROM_sha256=ROM_SHA,
                original_file_offset='0xeaa', fixed_ROM_bank=None,
                original_block_bytes=program[0xea4:0xeb0].hex(), incoming_RAM_sha256=sha(ram),
                prefix_RAM_sha256=sha(out_ram), prefix_PVC_sha256=sha(out_pvc),
                ordered_ports=len(ports) // 9, trace_PC_sha256=sha(struct.pack('>%dI' % len(trace), *trace)),
                native_PC_hook_count=len(trace), stopped_PC_included=True, full_prefix_state_ports_reads_equal=True,
                native_SR_read=False, oracle_sources=oracle_sources,
                program_manifest_sha256=manifest_before, oracle_wrapper_sha256=oracle_wrappers,
                oracle_library=dict(path=str(library), sha256=library_before, version=unicorn.__version__),
                limitation='Declared direct entry; later empty external queue is API checked boundary, not native CPU fault rollback.')


def reject_one(args):
    ctx, label, base, changes, stop, expected = args
    ram, state, pvc, bank = base
    s = dict(state, carry=2)
    s.update(changes)
    proof = None
    former = expected
    if label in ('unrouted_neighbour_0b481e', 'unrouted_neighbour_0b4a2a',
                 'unrouted_neighbour_046f52', 'unrouted_neighbour_01bdde'):
        assert expected == UNSUPPORTED_MACHINE
        assert int(label.removeprefix('unrouted_neighbour_'), 16) == s['pc']
        proof = superseded_stage_area_neighbour_prefix(ctx, label, ram, s, pvc, bank)
        expected = 'animation machine external read queue empty'
    actual = inv(ctx, 'neg_' + label, ram, s, pvc, bank, stop, 0)
    check_preserved(actual, ram, s, pvc, bank, expected)
    row = dict(label=label, error=expected, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False)
    if proof is not None:
        row.update(former_expected_error=former, superseded_by='F5 H1 continuation into the declared empty raster-read queue',
                   original_prefix=proof, API_only=False, boundary_rollback_API_only=True)
    return row


def run_parallel(function, items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(function, items))


def negatives(ctx, base, st):
    ram, state, pvc, bank = base
    jobs = []
    for pc in st['interior']:
        jobs.append((ctx, 'interior_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_AREA))
    # Historical neighbours include three PCs routed by F3b; keep each old label and full rollback check.
    for pc in UNROUTED_NEIGHBOURS:
        expected = SUPERSEDED_NEIGHBOUR_ERRORS.get(pc, UNSUPPORTED_MACHINE)
        jobs.append((ctx, 'unrouted_neighbour_%06x' % pc, base, {'pc': pc}, 0xff000, expected))
    jobs.append((ctx, 'trap_4d824_direct_entry_without_stop', base, {'pc': TRAP_STOP}, 0xff000, UNSUPPORTED_MACHINE))
    jobs.append((ctx, 'u6_4d7f0_direct_entry_without_stop', base, {'pc': U6_TRAP_STOP}, 0xff000, UNSUPPORTED_MACHINE))
    for low, high in F1C2_RANGES:
        jobs.append((ctx, 'odd_pc_entry_%06x' % (low + 1), base, {'pc': low + 1}, 0xff000, UNALIGNED_PC))
        jobs.append((ctx, 'odd_pc_entry_%06x' % (high - 1), base, {'pc': high - 1}, 0xff000, UNALIGNED_PC))
    for pc in (0x1, 0xffffff, 0xdeadbeef, 0x479b1, 0x49a59):
        jobs.append((ctx, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    for pc in (0x0, 0xffffffe, 0x1000000, 0xdeadbee):
        jobs.append((ctx, 'out_of_range_entry_%x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    # the boundary 4d824 is reachable only as a declared stop: 481de with D1.W = 14 without that stop rolls back
    out = run_parallel(reject_one, jobs)
    for row in out:
        pc = int(row['label'].removeprefix('unrouted_neighbour_'), 16) if row['label'].startswith('unrouted_neighbour_') else None
        if pc in SUPERSEDED_NEIGHBOUR_ERRORS:
            row.update(pc=hex(pc), former_expected_error=UNSUPPORTED_MACHINE, API_only=True,
                       superseded_by='F3b routing: block start executes; interior PCs use the ops executor error')
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
            assert out_ram == ram
            controls.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], next_pc=hex(want), carry_preserved=True, status=0))
    return out, controls


# Historical outside-PC inventory is retained; exactly three expectations changed when F3b routed 49a84..49a8e.
SUPERSEDED_NEIGHBOUR_ERRORS = {0x49a84: RNG_ERROR, 0x49a86: 'unsupported animation stage event ops PC',
                               0x49a8c: 'unsupported animation stage event ops PC'}
UNROUTED_NEIGHBOURS = (0x47a54, 0x47a56, 0x47a5c, 0x47a62, 0x49a84, 0x49a86, 0x49a8c, 0xb7a28, 0xb7a2a, 0xb7a2c, 0x4d84e, 0x4ddde, 0x4e68e, 0xb481e, 0xb4a2a, 0x46f52, 0x1bdde, 0x2eff4, 0x4aa86)


def f3b_neighbour_prefix(ctx, base, program):
    """Bounded API control: original MOVE.W D0,D7; BSR.S 49a58, before the RNG body."""
    pc, stop, ret = 0x49a84, 0x49a58, 0x49a88
    assert program[pc:ret].hex() == '3e0061d0'  # ROM word move; signed -48 displacement from 49a88.
    assert ret + struct.unpack('b', program[pc + 3:ret])[0] == stop
    ram, state, pvc, bank = base
    incoming = dict(state, pc=pc, carry=2)
    result, out_ram, out_pvc, ports, error = inv(ctx, 'f3b_neighbour_prefix_049a84', ram, incoming, pvc, bank, stop, 0)
    expected = dict(incoming, pc=stop, a7=(incoming['a7'] - 4) & M32, carry=0)
    expected['d7'] = (incoming['d7'] & 0xffff0000) | (incoming['d0'] & 0xffff)
    expected_ram = bytearray(ram)
    offset = expected['a7'] & 0xffff
    assert offset + 4 <= len(expected_ram)
    expected_ram[offset:offset + 4] = ret.to_bytes(4, 'big')
    assert result['ok'] and not error and result['status'] == 0
    assert out_state(result) == expected and out_ram == bytes(expected_ram)
    assert out_pvc == pvc and result['bank_base'] == bank and result['external_reads'] == 0 and not ports
    return dict(pc=hex(pc), stop=hex(stop), ROM_bytes=program[pc:ret].hex(), return_LONG=hex(ret),
                incoming_RAM_sha256=sha(ram), incoming_PVC_sha256=sha(pvc), incoming_state=incoming,
                expected_state=expected, all_state_RAM_PVC_ports_bank_status_external_reads_checked=True,
                API_only=True, native_continuation_equivalence_claimed=False,
                original_evidence='MOVE.W D0,D7; BSR.S 49a58; stop before RNG entry checks',
                carry_note='MOVE sets flags: the public block classification is Unknown')


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
    cases = [('frame0', state, ram, pvc, bank, FINAL_STOP), ('partial_479b6', state, ram, pvc, bank, 0x479b6), ('zero_step', state, ram, pvc, bank, state['pc']),
             ('interior_error', dict(state, pc=0x479b2), ram, pvc, bank, 0xff000), ('unknown_carry_error', dict(state, pc=0x47716, carry=0), ram, pvc, bank, 0xff000),
             ('odd_pc_error', dict(state, pc=0x479b1), ram, pvc, bank, 0xff000), ('unrouted_error', dict(state, pc=0x47a54), ram, pvc, bank, 0xff000),
             ('trap_stop_zero_step', dict(state, pc=TRAP_STOP), ram, pvc, bank, TRAP_STOP)] + list(extra_cases)
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
    assert OUT.resolve().name == 'animation_machine_stage_area_execution'
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='stage_area_verify_'))
    try:
        run(report_path)
    finally:
        for srv in SERVERS:
            srv.close()
        shutil.rmtree(RUN_DIR, ignore_errors=True)


BREAKING_EXPECTATIONS = {
    ('tools/verify_animation_machine_frame_helpers.py', 541): '`reject` loop of unrouted PCs names 2efdc, now an F1c2 block start (2efdc LEA 10d480.L,A1 ...): the direct entry executes, the expectation `unsupported animation machine PC` breaks; move to an unconnected PC such as 2eff4',
    ('tools/verify_animation_machine_input.py', 861): '`outside_entry` loop names 4d81c, now an F1c2 block start (CMPI.W #14,D1): the direct entry executes, the expectation `unsupported animation machine PC` breaks; move to 4d84e'}


def scan_old_expectations(st):
    """Old verifiers / tests that name an even PC of the 24 F1c2 ranges as a literal (read only; a PC that was an unrouted probe before F1c2 is now a block start or an interior PC)."""
    pcs = set(st['even_pcs'])
    files = sorted((Path(MAIN_ROOT) / 'tools').glob('verify_animation_machine*.py')) + sorted((ROOT / 'engine/tests').glob('animation_machine*_test.cpp'))
    rows = []
    for path in files:
        if 'stage_area' in path.name:
            continue
        found = collections.OrderedDict()
        for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            for m in re.finditer(r'0x([0-9a-fA-F]{3,6})\b', line):
                pc = int(m.group(1), 16)
                if pc in pcs:
                    found.setdefault(number, []).append(hex(pc))
        for number, hits in found.items():
            tag = ('tools/' if path.suffix == '.py' else 'engine/tests/') + path.name
            if (tag, number) in BREAKING_EXPECTATIONS:
                note = BREAKING_EXPECTATIONS[(tag, number)]
            else:
                note = ('literal PC of an F1c2 range, read as data / a declared stop / an exclusive range end by manual review: the unsupported-PC expectation is not touched '
                        '(stop PCs are checked before routing)')
            rows.append(dict(file=tag, line=number, pcs=sorted(set(hits)), note=note, expectation_breaks=(tag, number) in BREAKING_EXPECTATIONS))
    return rows


RNG_API_POINTERS = (0x100000, 0x10d6b4, 0x10d6b6, 0x10d71e, 0x10d720, 0x10d722, 0x1ffffe, 0x01100000 | 0x10d6b4, 0xff10d720, 0x0fffff, 0xfffffe, 0x200000, 0x1fffff, 0x0)


def rng_api_checks(ctx, base):
    """API-only checks of the 49a58 RNG pointer policy against the independent model (no native comparator: the policy rows of the observation cover the rejected pointers)."""
    ram, state, pvc, bank = base
    rows = []
    for pointer in RNG_API_POINTERS:
        r2 = bytearray(ram)
        r2[0xd722:0xd726] = pointer.to_bytes(4, 'big')
        r2 = bytes(r2)
        s2 = dict(state, pc=0x49a58, carry=2, a7=S)
        assert r2[S & 0xffff:(S & 0xffff) + 4] == FRAME_RET.to_bytes(4, 'big')
        actual = inv(ctx, 'rngapi_%08x' % pointer, r2, s2, pvc, bank, FRAME_RET, 0)
        res, out_ram, out_pvc, ports, error = actual
        model = model_rng(r2)
        row = dict(pointer='%08x' % pointer, pointer24='%06x' % (pointer & 0xffffff))
        if isinstance(model, str):
            assert model != 'model: second access outside the work RAM / odd', hex(pointer)
            check_preserved(actual, r2, s2, pvc, bank, model)
            row.update(outcome='rejected', error=model, state_preserved=True)
        else:
            m_ram, w, a3, a4 = model
            assert res['ok'] and not error and res['status'] == 0 and res['pc'] == FRAME_RET, (hex(pointer), error)
            assert out_ram == m_ram and (res['d0'] & 0xffff) == w and res['a3'] == a3 and res['a4'] == a4 and res['a5'] == 0x108000 and not ports and out_pvc == pvc
            row.update(outcome='completes', model_equal=True, final_a3='%08x' % a3)
        rows.append(row)
    return rows


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_stage_area.py', 'tools/observe_animation_machine_stage_area.py', 'docs/analysis/animation-machine-stage-catalog-f1c-contract.md',
                 'engine/src/animation_machine_stage_area.cpp', 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h'):
        inputs[name] = cc.digest(ROOT / name)
    test = ROOT / 'engine/tests/animation_machine_stage_area_test.cpp'
    if test.exists():
        inputs['engine/tests/animation_machine_stage_area_test.cpp'] = cc.digest(test)
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
    assert len(blob_names) == report['blob_count'] == 5928
    for name in blob_names:
        assert sha((blob_dir / name).read_bytes()) == name.split('.')[0], name
    # base state of the API-only checks: natural seed 1 (recorded frame-236 state), after the declared host changes of its frame 0 (dispatcher re-entry at 478de)
    base_row = [r for r in report['results'] if r['label'] == 'natural-001'][0]
    fx0 = base_row['fixture']
    cond0 = load_condition(report, base_row)
    base_ram = read_blob(fx0['initial_RAM_sha256'] + '.bin')
    base_state = dict(fx0['initial_regs'], a7=fx0['initial_a7'], pc=fx0['entry_pc'], carry=2)
    base_ram, base_state = apply_changes(base_ram, base_state, cond0['steps'][0]['changes'])
    base = (base_ram, base_state, read_blob(fx0['initial_PVC_sha256'] + '.bin'), fx0['bank_state'][0])
    wait_row = [r for r in report['results'] if r['group'] == 'sound' and r['steps'] == 2][0]
    fxw = wait_row['fixture']
    condw = load_condition(report, wait_row)
    assert condw['steps'][0]['expect'] == 'wait'
    wram, wstate = apply_changes(read_blob(fxw['initial_RAM_sha256'] + '.bin'), dict(fxw['initial_regs'], a7=fxw['initial_a7'], pc=fxw['entry_pc'], carry=0), condw['steps'][0]['changes'])
    extra = [('sound_wait_frame0', wstate, wram, read_blob(fxw['initial_PVC_sha256'] + '.bin'), fxw['bank_state'][0], hexint(condw['steps'][0]['stop_pc']))]
    equivalence = harness_equivalence(ctx, base, extra)
    results = replay_all(ctx, report, rows)
    failures = [(r['label'], a['error']) for r, a in zip(rows, results) if 'error' in a]
    if failures:
        for label, text in failures[:30]:
            print('CONDITION FAILED', label, text.strip().splitlines()[-1][:400])
        print(failures[0][1])
        raise AssertionError('%d conditions failed' % len(failures))
    totals, carry_stops, guards, out_rows, probes = collections.Counter(), collections.Counter(), [], [], {}
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
    full = not DEBUG_LABELS and not API_ONLY
    if full:
        interior_seen = set(st['starts']) - starts_seen
        assert not interior_seen, sorted(hex(p) for p in interior_seen)
        assert set(observed_preserving) == preserve and set(probes) >= set(st['starts']), (sorted(hex(p) for p in set(st['starts']) - set(probes)), sorted(hex(p) for p in preserve ^ set(observed_preserving)))
        for pc in CONSUMERS:
            assert any(k.startswith('consumer_flip_%x_incoming_' % pc) for k in totals), hex(pc)
        assert len(out_rows) == 753
        assert totals['frames'] + totals['guard_frames'] + totals['difference_frames'] == report['totals']['frames'], (totals['frames'], totals['guard_frames'], totals['difference_frames'])
        assert totals['continuous_runs'] == report['totals']['control_phases']
        assert len(VERIFIED_BLOBS) > 0
        # split phases: equal to the native count except the declared deliberate-difference rows
        for row in out_rows:
            if row['label'] in RNG_ORIGINAL_COMPLETES or row['label'] in RNG_SEGMENT_DIFFERS or row['label'] == RNG_HIGH_BYTE:
                continue
            assert row['cpp_split_phases'] == row['native_split_phases'], row['label']
        assert totals['split_phases'] + sum(r['native_split_phases'] - r['cpp_split_phases'] for r in out_rows) == report['totals']['split_phases']
    guard_labels = sorted(g['label'] for g in guards)
    # ------------------------------------------------------------------------------ API-only
    negative, consumer_controls = negatives(ctx, base, st)
    f3b_prefix = f3b_neighbour_prefix(ctx, base, program)
    zero = run_parallel(zero_step_one, [(ctx, base, pc, carry) for pc in st['starts'] + [TRAP_STOP] for carry in (0, 1, 2)])
    rng_api = rng_api_checks(ctx, base)
    cases, cpp_carry, cpp_ranges = cpp_static(st)
    assert cases == set(st['starts']), sorted(hex(p) for p in cases ^ set(st['starts']))
    assert cpp_ranges == sorted(F1C2_RANGES), cpp_ranges
    assert cpp_carry == preserve, (sorted(hex(p) for p in cpp_carry ^ preserve))
    for name, expected in inputs.items():
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs = dict(refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log', OUT / 'harness_batch.cpp', OUT / 'compile_batch.log'):
        refs[str(path.resolve())] = cc.digest(path)
    old = scan_old_expectations(st)
    differences = [g for g in guards if g.get('classification') not in (None, 'same_check_class')]
    rng_policy_rows = [g for g in guards if g['label'] in RNG_POLICY_LABELS]
    result = dict(
        schema_version=1, source=source, inputs=inputs, artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, cpp_sha256=CPP_SHA, contract_sha256=CONTRACT_SHA,
        native_counts=dict(conditions=report['conditions'], groups=report['groups'], frames=report['totals']['frames'], split_phases=report['totals']['split_phases'],
                           control_phases=report['totals']['control_phases'], dumped_frames=report['totals']['dumped_frames'], blobs=report['blob_count']),
        native_blobs_hash_checked=len(blob_names), native_blobs_read_for_comparison=len(VERIFIED_BLOBS),
        contract_ranges=[dict(range='%x..%x' % r, size=r[1] - r[0]) for r in st['table']], block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']],
        interior_PC_count=len(st['interior']), bundled_branches=[hex(p) for p in st['bundled']], carry_preserving_blocks=[hex(p) for p in st['preserving']],
        carry_consumers=[hex(p) for p in CONSUMERS], cpp_case_labels_equal_contract_block_starts=len(cases), cpp_routing_ranges_equal_24=True, cpp_carry_preserving_table_in_unit_equals_77=True,
        observed_carry_preserving_blocks_through_cpp=[hex(p) for p in observed_preserving],
        carry_probed_blocks={hex(pc): dict(incoming_Clear_preserved=bool(slots[1]), incoming_Set_preserved=bool(slots[2])) for pc, slots in sorted(probes.items())},
        actual_CPP=dict(sorted(totals.items())), conditions=out_rows,
        carry_at_stops={k: v for k, v in sorted(carry_stops.items())},
        native_guards_checked_API=guards, native_guard_count=len(guards),
        deliberate_differences=dict(count=len(differences), rows=differences),
        rng_policy=dict(policy_rows_rejected_with_exact_error=len(rng_policy_rows), policy_row_labels=[g['label'] for g in rng_policy_rows],
                        native_completes_cpp_rejects_rows=[g['label'] for g in guards if g['label'] in RNG_ORIGINAL_COMPLETES], native_completes_cpp_rejects_count=len([g for g in guards if g['label'] in RNG_ORIGINAL_COMPLETES]),
                        native_ROM_write_cpp_policy_rejects_rows=[g['label'] for g in guards if g['label'] in RNG_ORIGINAL_OUTSIDE],
                        high_byte_row=[g for g in guards if g['label'] == RNG_HIGH_BYTE], api_pointer_checks=rng_api),
        superseded_F3b_neighbour_prefix=f3b_prefix,
        negatives=negative, negative_count=len(negative), consumer_controls=consumer_controls, zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2],
        zero_step_extra_stop_only_PCs=[hex(TRAP_STOP)],
        harness_equivalence_cases=equivalence,
        invalidated_expectation_candidates=old,
        carry_check='C is a block classification (native SR is never read): the five consumers 47716 47732 4776c 1bd34 1bd96 take a Known C produced by the 289e callee inside the run '
                    '(289e formula checked against the C++ RAM, the native branch path checked from the dumped native PC trace, the full-state SHA equality of every frame), flip controls select '
                    'the other destination, Unknown at a consumer gives the exact error; single-block probes with incoming C 1 / 2 on every distinct F1c2 start observed in a dumped frame '
                    'reproduce the 77 FLOW_ONLY blocks; waits report Unknown (API wait contract)',
        compile_command=command, compile_batch_command=scommand, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (the recorded frame-236 state of the F1c1 observation of 129 natural seeds, the recorded complete chain of 8 seeds, runtime fixtures built by the original code, '
                'declared typed variants), not natural scheduler, IRQ or gameplay reachability; one machine run is one frame and the next frame is a declared direct re-entry '
                '(PC redirect + A7 delta + return LONG 2ac2).',
                'Native SR is not observed; the initial SR of every fixture is declared (Unknown carry in the C++ for all fixtures).',
                'Existing executors (U1..U7, cleanup, fade_card, F1a, F1b, F1c1, sound, exit, input, readiness) are compared as whole results; their interior is not modelled here.',
                'Native split-phase intermediate RAM is not stored (only the per-frame digests and the full dumps of whole frames): split intermediate registers are compared with the native '
                'leader registers of the dumped trace (first arrival of each checkpoint when it is a recorded leader); the final split state equals the continuous C++ run equals the native frame.',
                'Checked failures preserve API outputs, not original CPU fault rollback; deliberate differences are listed with counts.',
                'No BIOS execution, no natural scheduler, no natural IRQ is claimed.'])
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(conditions=len(out_rows), frames=totals['frames'], guard_frames=totals['guard_frames'], difference_frames=totals['difference_frames'], split_phases=totals['split_phases'],
                          continuous=totals['continuous_runs'], negatives=len(negative), zero_step=len(zero), guards=len(guards), deliberate=result['deliberate_differences']['count'],
                          sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
