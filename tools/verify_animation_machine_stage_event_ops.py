"""Stage event F3b (opcodes 08..0f e94fe..e9768, the skip routine e9774 with the e9790 table, the child thread callbacks e9350 / e9362 with the e941c child opcode table, the 288c / 2898,
1a92c and 49a84 / 49a88 helpers; TRAP #15 stop boundaries) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection.  The frozen native observation (artifacts/animation_machine_stage_event_ops_native) is an immutable input; this verifier never invokes the
observer main and never imports the observer module.  It reads the F3b observation, the typed condition files, the natural node rows and the entry probes, and compares them with the actual C++
`run_animation_machine` (one run = one node execution: PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd; stop 2ac2 after the dispatcher RTS or the 2a00 delete; typed direct entries stop at the
declared stop PC, the TRAP #15 sites are declared stop boundaries):
  * typed conditions (284, 38 of them native guards): every split phase (stop at the first arrival of every checkpoint of the native step, same order, directly after the transferring
    instruction) is compared with the native phase record (16 registers, PC, SHA256 of the 64 KiB RAM, PVC image modulo the two normalized bank words + their native values, ordered ports SHA256,
    external reads); every phase resumes ONLY from the previous actual C++ output plus the declared host changes of the step; the native input state is asserted, never injected; continuous C++ run
    vs the split chain vs the native record; native guards -> exact checked C++ error strings (listed per label), state preserved, the same split segment where the native guard is a refusal;
    deliberate differences (op 08 failure path, high-byte RNG pointer, native bus errors, stack-overwriting op 08 copy) are classified with counts;
  * natural nodes (471 e9150 / e9176 / e9350 / e9362 node executions of the natural seeds that touch F3b): the entry states are regenerated from the pinned scheduler seeds (the scheduler observer is
    imported ONLY as the seed state generator: its SeedRun, with the F3 replay hook replaced by this verifier's C++ run; nothing of it is edited), each regenerated entry digest must equal the recorded
    one before the C++ run, the C++ exit digest must equal the recorded exit digest and the recorded ordered port digest; every node is dumped natively and compared byte by byte (RAM, PVC, ports)
    and with the full split chain of the native executed path;
  * carry = block classification observed through the actual C++: the two consumers e936e (288c / 289e / 2898) and e9576 (2986) take a Known C (native branch path), flip controls select the other
    destination, single-block probes with incoming C 1 / 2 on every distinct F3b start observed in a traced condition give the 48 FLOW_ONLY blocks back, Unknown at a consumer gives the exact
    error `stage event ops caller requires known carry`; native SR is never read;
  * API-only negatives: all 359 interior PCs, 476 odd PCs, the 8 TRAP sites (direct entry = unrouted, declared zero-step = ok), the 20 string-area PCs, the neighbours of the 8 routed ranges,
    zero-step at every one of the 109 starts x 3 carries.
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
OUT = Path(os.environ['OUTDIR']) if os.environ.get('OUTDIR') else ROOT / 'artifacts/animation_machine_stage_event_ops_execution'   # OUTDIR: scratch output override (final component must keep this name)
NATIVE_DIR = ROOT / 'artifacts/animation_machine_stage_event_ops_native'
SEED_DIR = ROOT / 'artifacts/animation_machine_scheduler_native'
NATIVE_SHA = 'e8a81643f5b62af0f4c570cd1173c7bf7262601fe20e212a711ff9cf5c61239b'
NATIVE_TOOL_SHA = 'c27b2d1cbd01ad02590357589413d3982d0d5c3b8d855a10b64ce3638a738605'
F3A_TOOL_SHA = 'ae0840bbd1eb22a4aaa1de78a274ef924c22b6b2ea87ae0125eefd33cd3ed9c6'
SCHED_TOOL_SHA = '62bb23ff6d2f61a5e47af71b8e1308d50c99b85d95f3278b8d825b7ee327c01c'
SEED_OBS_SHA = 'c330e597f9585c2595006239be49ab0bcb029f4b5fed5c70ebf872fe91a2b4ff'
SEED_FILE_SHA = '86af9f05a3f127aabd96c7755f091e4a450bb8d5d70978ddb0a503f1b7fcff0f'
CONTRACT = ROOT / 'docs/analysis/animation-machine-stage-event-f3-contract.md'
CONTRACT_SHA = 'bba912176899ab0c21a0b9d54800c5f987f8fdcad9c592b714b8a713d5376c95'
# FR7 refresh: animation_machine.cpp was 989b7951f8613fcb3643603292b94b3a61fbb97b5ca16ad7e66cc31bef1adcfe, animation_machine_internal.h was cef94f5cbabb5b89a0cdaf27c53f86cec9bf32abeaecedf6fdde8f3778b284c1
# FR9 refresh: animation_machine.cpp was 9592e227f3a4cfe478dafa4fcf3842dae50072fd7adbb828fd5108f0fe4a270b, animation_machine_internal.h was a7d92b011f252b522dc8ac0e7f2c0b9bb3c0f72e2bb1a97bd9803f0e0deb400d
# player C1 refresh: animation_machine.cpp was 7233eefce1281ff3fdda6f44f97948290b350786f895b2734fa6b2a18d7a534d, animation_machine_internal.h was b870dcc5f415fc18b92fa0b2e7c97b469c2302ee3d5d2bf61d773643b44ed25e
# select E1 refresh: animation_machine.cpp was 15b827242abca6434147ab3a63a827b5d4d613cbdbbba051c438a57ea001dea2, animation_machine_internal.h was 5e2ad9ef19d159ba9907b2a9683034ad754b6734177ee8e73f84e235c4337a0e
# player C2 refresh: animation_machine.cpp was 565880ca271b7cff4fabe49c3d386553f46ec9d18b1965e30f02318cabec22c5, animation_machine_internal.h was 9a80738e3a1b1fbc8dc9782331426daf2406f2706d8cc86af2a2bed1b0c58a32
# player C3 refresh: animation_machine.cpp was 003b4d86868d11dce31dd6732b5c79f9c1d76e523a75110628d7d11f87c389f5, animation_machine_internal.h was 9bb14a08b8beafda059409ccf886f4ed1a83827b3144c6ff2234fb6fb5b92ec6
# player C4 refresh: animation_machine.cpp was 0a8379cacc854d593b262cbb4989dc68a17dfacb3e58b06e0d3e833d87474b26, animation_machine_internal.h was dee2f94720c4f7abd38131660b83a741fa36ada560a56357fafd8cb3f2a0e112
CPP_PINS = {'engine/src/animation_machine_stage_event_ops.cpp': '5369d279877922f015249c3d4173cccd46beabdf6c3a50d9c220c175b982f61c', 'engine/src/animation_machine_stage_event.cpp': 'e074f25f82b8e1bd7d84068bfe773db6b9f435cb35d22e95a59e24ead6952d9c', 'engine/src/animation_machine_cleanup.cpp': 'b6aed30bbea37f5ab02f85ffc8e62ecd6c68e5f6f34cdc0a2b6e9487716aaf5c', 'engine/src/animation_machine_buffer_cue.cpp': '5360f1fcad2e125782bd36a3c3dc7f253407b9d78f260a13b6ac9279f9cc32cd', 'engine/src/animation_machine_fade_card.cpp': '73a0ac85fbba29fcbb2e48890b0cfded80300dc9f71ac586e97c70523ee42550', 'engine/src/animation_machine_readiness.cpp': 'da3893ef551d93b3f11375fac5ad224cb7ca5615084d5a782971cbb6373eb668', 'engine/src/animation_machine_stage_area.cpp': 'dd273339b0a98d71bdf4f1b492e9354079c399f99eea0c7ad4ad078e43eb8d10', 'engine/src/animation_machine.cpp': '9747100c960fa54879c998635c250ae06e790155df4ae1c5a5a4e2ec2c03915d', 'engine/src/animation_machine_internal.h': '6f22404a6c4422178f812a7ad193ee9e8a1b36bfde4f0da1c7740d2875923c0d'}  # FR8 refresh: animation_machine.cpp was 298c64da5f6ab9483acc7b1e39c0b733ea0908cb685c058621faa500ffbec51f and animation_machine_internal.h was 69b45dcd7444ae6411e238106b33c3f2f5098d10525e0ed93f78f21f237813fd (FR8 routing else-if, carry group of 6 and declaration after FR7). Earlier FR7 refresh: animation_machine.cpp was 989b7951f8613fcb3643603292b94b3a61fbb97b5ca16ad7e66cc31bef1adcfe and animation_machine_internal.h was cef94f5cbabb5b89a0cdaf27c53f86cec9bf32abeaecedf6fdde8f3778b284c1 (FR7 routing else-if, carry group of 8 and declaration after FR6). Earlier FR6 refresh: animation_machine.cpp was 7641c2d9f54068ee2c4308c516bea495bc4392fd0107b3f85b584de5fedcf337 and animation_machine_internal.h was fcef64db27191d5aa06fd75a83d3cf1fd9a989aaeddcc9870ae9f803a223009f (FR6 routing else-if, carry group of 12 and declaration after FR5). Earlier FR5 refresh: animation_machine.cpp was 31a1b033911fd15cfed40998c1072f32db29a85d7605848e1049b1bbf86735c8 and animation_machine_internal.h was 8570d1e86121aa5ad8432c716d2787cdc69ef5cb26bbc9cb3a78742edd7625e0 (FR5 routing else-if, carry group of 6 and declaration after FR4). Earlier FR4 refresh: animation_machine.cpp was 869a9dc12b14ba47ed65642ab937cb1bbaa5a49775241e3a325ce47fc1d1a446 and animation_machine_internal.h was f7953e9a0a117d13b4f4b8966df5402838e579a4a4efb36c325affd18daf1f3b (FR4 routing else-if, carry group of 7 and declaration after FR3). Earlier FR3 refresh: animation_machine.cpp was 4fc41a76a8ef697a93dd339af64a7deff8c62620c680d27015aad6bf2b2a3b40 and animation_machine_internal.h was 142f253e7e8caa020620d97ea91eeac57907506c7323af4c9d006a8186c43d24 (FR3 routing else-if, carry group of 17 and declaration after FR2b). Earlier FR2b refresh: animation_machine.cpp was eadc97b080cbeacbf16524ca1626fb4013b07acdc0042340743ab34509201923 and animation_machine_internal.h was 522199f979904a60033719cccfa965edb2890a16744b267375436ede12875b14 (FR2b routing else-if, carry group of 11 and declaration after b4a7e21). Earlier FR2a refresh: animation_machine.cpp was 00ff3a1b8bfb89d7682bb48506ef39809ddd9062853335707385457b2cbd9fb4 and animation_machine_internal.h was caad91c124ca03fb7dd4d77d972f577e4736fe58e30aad5054bfb957d527a04e (FR2a routing else-if, carry group of 9 and declaration after 11be2b6). Earlier FR1 refresh: animation_machine.cpp was 8ce8eb93c21465dd5e9355d4518ab1ca853df4549305fec98c7854caa1a82db6 and animation_machine_internal.h was 74d9c9ab7c60ffc9e7c8d3f523f7e769fb2f836fbafadfcad56ee34dcbebb71d (FR1 routing/declarations changes after 062bfd7). Earlier 062bfd7 refresh (0267): animation_machine.cpp was 1e7625c722bca323152a57d6cd81f2237a5fdff51c13a1563b6e430c26ccbf76 and animation_machine_internal.h was 874fceb112699346f95c12ee5212bbc997137eef22de17b8fe18b38bb5a079f8 (d66442f); d66442f..062bfd7 adds B4a/B4b child callback routing and private declarations. Earlier d66442f refresh (0266): animation_machine.cpp was aba5bec0b6450b00b0259478ccdbe6c0fa133ec9e481145117b3a2631aa68cc9 and animation_machine_internal.h was 706f6a5bcd3ce44c91dfa74928b5a155050af087ce1c643631c11d8a513a0e78 (de0e5be); de0e5be..d66442f adds U06b (e7562/48250) and B3c (N28 chain children, 1c114, 2291a tail) routing and private declarations. Earlier de0e5be refresh (0264-legacy rerun): animation_machine.cpp was 7e76e64bad3037cc22c6597b3c8746b05f7540dee4703c4dc18853179cf951a6 and animation_machine_internal.h was 4585a260ec43cf41c5c9fb8a8c23532505000c9dd9ea1161f659a2d6a6d6cfbd (e5bfb73); e5bfb73..de0e5be adds B2c-a/B2d/B2e/B3a/B3b routing and private declarations. Earlier e5bfb73 refresh (0264-legacy): animation_machine.cpp was c7318132fcdfd288c12a58ab7e51c03e2920b46d7e939103bd917d72ca8caad2 and animation_machine_internal.h was 6406329a911fd50c13b9765bf59b032f5afa322e1237a8a9b1dea6b1a5fa6e34 (709a706); 709a706..e5bfb73 adds the ten-unit routing (C1-C3, F6a-c, B1a-c, B2a/b), private declarations, the palette device context and the Z80 reply 320000 external-read device (the old line was replaced, not deleted). Earlier note, b8502bf: 0c89a1f..HEAD adds routing for N33/N34/N35 and H2/H3/H4/H8 plus private declarations; no existing shared lines removed. Other pinned unit sources unchanged.
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
SPD = 0x1ff000
FRAME_RET = 0x2ac2
NODE_PC = 0x2ab8
F3A_RANGES = ((0x1a910, 0x1a91a), (0x1a93e, 0x1a952), (0x48502, 0x4855c), (0xe9150, 0xe9350), (0xe9444, 0xe94fe), (0xe9768, 0xe9774), (0xe97c8, 0xe98ee))
F3B_RANGES = ((0x288c, 0x289e), (0x1a92c, 0x1a93e), (0x49a84, 0x49a8e), (0xe9350, 0xe93da), (0xe93f0, 0xe9444), (0xe94fe, 0xe957c), (0xe958e, 0xe9768), (0xe9774, 0xe97c8))
STRING_RANGES = ((0xe93da, 0xe93f0), (0xe957c, 0xe958e))     # data (ASCII error strings), not code: unrouted
RET_F3A = 0xe91b0                                              # the F3a block after BSR e94fe (e91ac)
TRAP_SITES = (0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788)
CONSUMERS = (0xe936e, 0xe9576)
SET_PRODUCER = 0x2898                                         # ORI.B #1,CCR inside the block: Known Set at the RTS
CALLBACKS = (0xe9150, 0xe9176, 0xe9350, 0xe9362)
BLACK_BOXES = (0x43e34, 0x49392, 0x4d7a6)
REG16 = tuple('d%d' % i for i in range(8)) + tuple('a%d' % i for i in range(8))
UNKNOWN_CARRY = 'stage event ops caller requires known carry'
UNSUPPORTED_EVENT = 'unsupported animation stage event PC'
UNSUPPORTED_OPS = 'unsupported animation stage event ops PC'
CUE_FAILURE = 'cue wrapper failure requires known caller X'
RNG_OUTSIDE = 'stage area RNG pointer outside work RAM'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNALIGNED_PC = 'unaligned animation machine PC'
EVEN = 'program bus requires even WORD/LONG address'
BUDGET = 'animation machine block budget exceeded'
WORKERS = int(os.environ.get('STAGE_EVENT_OPS_WORKERS', '3'))
API_ONLY = bool(os.environ.get('STAGE_EVENT_OPS_API_ONLY'))                 # development switch only
DEBUG_LABELS = [x for x in os.environ.get('STAGE_EVENT_OPS_DEBUG_LABELS', '').split(',') if x]      # development switch only
NO_NATURAL = bool(os.environ.get('STAGE_EVENT_OPS_NO_NATURAL'))             # development switch only
NATURAL_SEEDS = [int(x) for x in os.environ.get('STAGE_EVENT_OPS_SEEDS', '').split(',') if x]      # development switch only
STATE_SHA_PREFIX = b'F3B-STATE-v1'
VERIFIED_BLOBS = set()
RUN_DIR = None


def localize(name):
    local = str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name
    return local if Path(local).exists() else name


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def in_f3a(pc):
    return in_ranges(pc, F3A_RANGES)


def in_f3b(pc):
    return in_ranges(pc, F3B_RANGES)


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
    """Fresh server registry (a forked natural worker must never share the parent's pipes)."""
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
    exe = folder / 'animation_machine_stage_event_ops_batch_harness'
    compiler = shutil.which('clang++')
    assert compiler
    command = [compiler, '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(root / 'engine/include')]
    command += [str(root / 'engine/src' / name) for name in common.SOURCES]
    command += [str(path), '-o', str(exe)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    (folder / 'compile_batch.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stdout and not run.stderr, run.stderr
    return exe, command


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


def expand_pcs(text):
    """PC tokens of a contract line; `a`..`b`(n slot) expands to the 4-byte table slots."""
    out = []
    for m in re.finditer(r'`([0-9a-f]{4,6})`(?:\.\.`([0-9a-f]{4,6})`\((\d+)[^)]*\))?', text):
        a = int(m.group(1), 16)
        if m.group(2):
            b = int(m.group(2), 16)
            n = int(m.group(3))
            assert (b - a) // 4 + 1 == n, (m.group(0), n)
            out.extend(range(a, b + 1, 4))
        else:
            out.append(a)
    return out


def parse_contract(program):
    lines = CONTRACT.read_text().splitlines()
    pat = re.compile(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| (.*) \|$')
    code, sect = [], None
    for line in lines:
        if line == '**F3a**':
            sect = 'a'
            continue
        if line == '**F3b**':
            sect = 'b'
            continue
        if sect != 'b':
            continue
        m = pat.match(line)
        if not m:
            continue
        low, high = int(m.group(1), 16), int(m.group(2), 16)
        ticks = re.findall(r'`([0-9a-f]+)`', m.group(3))
        digest = re.search(r'SHA256 `([0-9a-f]{64})`', m.group(3))
        assert ticks and ticks[-1] == program[low:high].hex(), (hex(low), 'byte table row')
        if digest:
            assert sha(program[low:high]) == digest.group(1)
        code.append((low, high))
    assert code == list(F3B_RANGES) and sum(h - l for l, h in code) == 952
    starts = bundled = preserve = consumers = None
    seen_b = False
    for line in lines:
        if line.startswith('**F3b (109 block 시작'):
            starts = expand_pcs(line.split(':', 1)[1])
            seen_b = True
        elif line.startswith('**공통**'):
            seen_b = False
        elif seen_b and line.startswith('- 묶인 PC 31개:'):
            bundled = expand_pcs(line.split(':', 1)[1].split('결정 3의')[0])
        elif seen_b and line.startswith('- FLOW_ONLY 48개:'):
            preserve = expand_pcs(line.split(':', 1)[1])
        elif seen_b and line.startswith('- carry 소비 block 2개:'):
            consumers = [int(x, 16) for x in re.findall(r'`(e[0-9a-f]{4})`', line.split(':', 1)[1].split('known carry')[0])]
    assert starts and len(starts) == len(set(starts)) == 109
    assert bundled and len(bundled) == len(set(bundled)) == 31
    assert preserve and len(preserve) == len(set(preserve)) == 48
    assert consumers == list(CONSUMERS)
    return starts, bundled, preserve


BRANCHES = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
TERMINATORS = ('rts', 'bra', 'jmp', 'jsr', 'bsr') + BRANCHES


def audit_static(program):
    starts, bundled, preserve = parse_contract(program)
    instructions = RomInstructions(program)
    start_set = set(starts)
    names = lambda pc: instructions[pc]['mnemonic'].split('.')[0]
    inside = []
    for low, high in F3B_RANGES:
        pc = low
        while pc < high:
            inside.append(pc)
            pc += instructions[pc]['size']
        assert pc == high, hex(low)
    assert len(inside) == 271
    traps = sorted(pc for pc in inside if names(pc) == 'trap')
    assert traps == sorted(TRAP_SITES) and all(instructions[pc]['size'] == 2 for pc in traps)
    assert not [pc for pc in inside if names(pc) in ('rte', 'addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')]
    # blocks: from a start to the next start (or a TRAP site / the range end), the contiguous instruction run; bundled continuation instructions stay in the block they follow
    blocks = collections.OrderedDict()
    for low, high in F3B_RANGES:
        pc, cur = low, None
        while pc < high:
            if pc in TRAP_SITES:
                cur = None
                pc += instructions[pc]['size']
                continue
            if pc in start_set or cur is None:
                cur = pc
                blocks[cur] = []
            blocks[cur].append(pc)
            pc += instructions[pc]['size']
        assert pc == high
    assert sorted(blocks) == sorted(starts) and sum(len(v) for v in blocks.values()) == 263
    fallthrough = sorted(s for s, b in blocks.items() if names(b[-1]) not in TERMINATORS)
    leaving = sorted(s for s in fallthrough if not in_f3b(blocks[s][-1] + instructions[blocks[s][-1]]['size']))
    assert leaving == [0xe9762] and blocks[0xe9762][-1] + instructions[blocks[0xe9762][-1]]['size'] == 0xe9768          # MOVE.B #ff,80(A6) falls into the F3a block e9768
    assert all(b[-1] + instructions[b[-1]]['size'] in start_set for s, b in blocks.items() if s in fallthrough and s not in leaving), [hex(s) for s in fallthrough]
    # a conditional branch that ends a block may fall through into a TRAP site (the boundary)
    trap_fallthrough = sorted(s for s, b in blocks.items() if b[-1] + instructions[b[-1]]['size'] in TRAP_SITES)
    assert all(names(blocks[s][-1]) in BRANCHES for s in trap_fallthrough)
    derived_bundled = sorted(pc for b in blocks.values() for pc in b[1:] if names(pc) in BRANCHES)
    assert derived_bundled == sorted(bundled), [hex(p) for p in set(derived_bundled) ^ set(bundled)]
    assert not set(bundled) & start_set and not set(TRAP_SITES) & start_set
    flow = sorted(s for s, b in blocks.items() if all(names(p) in FLOW_ONLY for p in b))
    assert flow == sorted(preserve), [hex(p) for p in set(flow) ^ set(preserve)]
    assert [names(p) for p in CONSUMERS] == ['bcc', 'bcs'] and all(len(blocks[p]) == 1 for p in CONSUMERS)
    assert names(SET_PRODUCER) == 'ori' and names(blocks[SET_PRODUCER][-1]) == 'rts'
    even_pcs = [pc for low, high in F3B_RANGES for pc in range(low, high, 2)]
    odd_pcs = [pc for low, high in F3B_RANGES for pc in range(low + 1, high, 2)]
    interior = [pc for pc in even_pcs if pc not in start_set and pc not in TRAP_SITES]
    string_even = [pc for low, high in STRING_RANGES for pc in range(low, high, 2)]
    string_odd = [pc for low, high in STRING_RANGES for pc in range(low + 1, high, 2)]
    assert len(even_pcs) == 476 and len(interior) == 359 and len(odd_pcs) == 476 and len(string_even) == 20 and len(string_odd) == 20
    assert program[0xe93da:0xe93f0].startswith(b'HOJU TABLE CODE ERROR\0') and program[0xe957c:0xe958e] == b'ESET MAKE FAIL!!\0\0'      # [F] the contract text says `SET MAKE FAIL!!\0\0`: the ROM bytes begin with an extra 'E' (data, never executed)
    return dict(starts=starts, bundled=sorted(bundled), preserving=sorted(preserve), instructions=instructions, blocks=blocks, fallthrough_blocks=fallthrough, interior=interior, even_pcs=even_pcs,
                odd_pcs=odd_pcs, string_even=string_even, string_odd=string_odd, traps=traps, trap_fallthrough_blocks=trap_fallthrough)


def routed_ranges():
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    return sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', machine))


def cpp_static(st):
    text = (ROOT / 'engine/src/animation_machine_stage_event_ops.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text))
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    in_unit = set(pc for pc in table if in_ranges(pc, F3B_RANGES))
    start = machine.index('animation_stage_event_block(c);') + len('animation_stage_event_block(c);')
    end = machine.index('animation_stage_event_ops_block(c);', start)
    route = machine[start:end]
    ranges = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', route))
    assert '!stage_event_ops_trap(next.pc)' in route
    trap_fn = machine[machine.index('bool stage_event_ops_trap'):]
    trap_fn = trap_fn[:trap_fn.index('}')]
    traps = sorted(int(x, 16) for x in re.findall(r'pc==0x([0-9a-f]+)', trap_fn))
    return cases, in_unit, ranges, traps


# ----------------------------------------------------------------------------------------------------------------- native data
def read_blob(name, base=None):
    data = (base or NATIVE_DIR / 'blobs').joinpath(name).read_bytes()
    assert sha(data) == name.split('.')[0], name
    VERIFIED_BLOBS.add(name)
    return data


def blob_bytes(h):
    return read_blob(h + '.bin')


def blob_json(h):
    return json.loads(gzip.decompress(read_blob(h + '.json.gz')))


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_stage_event_ops.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_stage_event.py') == F3A_TOOL_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_scheduler.py') == SCHED_TOOL_SHA
    assert cc.digest(SEED_DIR / 'observation.json') == SEED_OBS_SHA and cc.digest(SEED_DIR / 'f3_node_seeds.json.gz') == SEED_FILE_SHA
    for name, expected in CPP_PINS.items():
        assert cc.digest(ROOT / name) == expected, name
    assert cc.digest(CONTRACT) == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and all(x['bytes_equal_to_rom'] for x in report['contract']['byte_table_check'])
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert report['condition_count'] == 284 == len(report['conditions']) == report['control_steps']
    assert report['natural']['nodes'] == 471 and sum(report['natural']['by_callback'].values()) == 471 and report['natural']['self_delete_nodes'] == 6
    assert report['block_starts_covered'] == 109 and report['block_starts_uncovered'] == [] and len(report['block_starts_need_typed_fixture']) == 109 - 54
    assert report['entry_probes']['addresses'] == 992 and report['entry_probes']['rows'] == 1000 and report['model']['natural_equal'] == 471 and report['model']['typed_equal'] == 246
    assert report['seed_inputs']['f3_node_seeds_sha256'] == SEED_FILE_SHA and report['seed_inputs']['scheduler_observation_sha256'] == SEED_OBS_SHA
    sc = report['static_checks']
    assert sc['block_starts'] == 109 and sc['blocks_total_instructions'] == 271 and sc['bundled_pcs'] == 31 and sc['flow_only_equal_contract'] is True
    assert sc['carry_consumers_contract'] == ['0xe936e', '0xe9576'] and sc['trap_instructions_in_blocks'] == [hex(p) for p in TRAP_SITES]
    changed = []
    for name, expected in report['inputs'].items():
        actual = cc.digest(localize(name))
        if actual != expected:
            # C++ sources / verifiers edited after the observation (the native observer never reads the C++); recorded, not asserted
            changed.append(dict(path=name, native_observation_sha256=expected, current_sha256=actual))
    report['_changed_inputs'] = changed
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    return report


def load_condition(result):
    file = result['file']
    data = (NATIVE_DIR / file['file']).read_bytes()
    assert sha(data) == file['sha256']
    cond = json.loads(gzip.decompress(data))
    assert cond['result']['label'] == result['label'] and cond['result']['index'] == result['number']
    return cond


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


def sched_state_digest(ram, regs, pc, bank):
    """The scheduler observer's state digest (state_blob_digest) recomputed from the C++ output: 64 KiB RAM, 16 registers, PC, bank base, PVC words ff8 / ff9."""
    h = hashlib.sha256()
    h.update(b'MS5-SCHED-STATE-1')
    h.update(ram)
    h.update(struct.pack('>16I', *[regs[k] for k in REG16]))
    h.update(struct.pack('>IIIHH', pc, bank[0], 0, bank[1] & 0xffff, bank[2] & 0xffff))
    return h.hexdigest()


def sched_ports_digest(ports):
    """The scheduler observer's ordered port digest from the C++ ordered ports (kind 1 = PVC bank words, kind 2 = other device writes)."""
    h = hashlib.sha256()
    h.update(b'MS5-SCHED-PORTS-1')
    for i in range(0, len(ports), 9):
        size, address, value = struct.unpack('>BII', ports[i:i + 9])
        h.update(struct.pack('>BIBI', 1 if 0x2fe000 <= address < 0x300000 else 2, address, size, value))
    return h.hexdigest()


def bank_words(pvc):
    return int.from_bytes(pvc[0x1ff0:0x1ff2], 'big'), int.from_bytes(pvc[0x1ff2:0x1ff4], 'big')


def pvc_page_for(bank):
    page = bytearray(8192)
    page[0x1ff0:0x1ff2] = bank[1].to_bytes(2, 'big')
    page[0x1ff2:0x1ff4] = bank[2].to_bytes(2, 'big')
    return bytes(page)


def initial_carry(sr):
    if sr is None:
        return 0
    return 2 if sr & 1 else 1


def apply_changes(ram, state, rows):
    ram = bytearray(ram)
    for row in rows:
        assert row['kind'] == 'ram'
        address, size, value = row['address'], row['size'], row['value']
        assert 0x100000 <= address and address + size <= 0x200000 and (address & 0xffff) + size <= 0x10000
        ram[address & 0xffff:(address & 0xffff) + size] = value.to_bytes(size, 'big')
    return bytes(ram), dict(state)


def out_state(result):
    return {k: result[k] for k in common.STATE_KEYS}


def check_preserved(actual, ram, state, pvc, bank, expected_error=None):
    result, out_ram, out_pvc, ports, error = actual
    assert not result['ok'] and (expected_error is None or error.strip() == expected_error), (expected_error, error.strip())
    assert {k: result[k] for k in common.STATE_KEYS} == {k: state[k] for k in common.STATE_KEYS}
    assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
    assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
    return error.strip()


def inv(ctx, label, ram, state, pvc, bank, stop, external):
    return invoke(ctx.exe, RUN_DIR, label, ram, state, pvc, bank, ctx.resources, stop, external)


def split_chain(ctx, tag, ram, state, pvc, bank, stop, checkpoints, external):
    """The C++ split chain of one native step: stop at the first arrival of every checkpoint in the native order, then at the step stop.  Every phase resumes from the previous actual C++ output."""
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


def branch_target(pc, carry):
    """Destination of the two stage event ops carry consumers (BCC clear_pc, otherwise set_pc; e9576 is BCS: the Clear destination is the TRAP boundary e957a) for a known C (1 Clear, 2 Set)."""
    assert carry in (1, 2)
    return {0xe936e: (0xe9428, 0xe9372), 0xe9576: (0xe957a, 0xe958e)}[pc][0 if carry == 1 else 1]


def native_succ(pcs, index, block, instructions, start_set):
    """Native successor PC of a block started at pcs[index]: the first discontinuity of the executed path (a transfer), a fall-through into the next start or into a TRAP boundary, or a bundled branch
    whose destination is a taken branch.  A not-taken bundled branch continues sequentially inside the same C++ block."""
    i = index
    while True:
        pc = pcs[i]
        nxt = pcs[i + 1]
        if nxt != pc + instructions[pc]['size']:
            return nxt, i + 1
        if nxt in start_set or nxt in TRAP_SITES:
            return nxt, i + 1
        i += 1


# ----------------------------------------------------------------------------------------------------------------- guard expectations
# Native guard label -> expected checked C++ error string (explicit per label; the code-target kind is classified by the original ranges).
WRITE_DEVICE = 'unsupported animation machine write device'
DEVICE_ADDR = 'unsupported program bus device address'
GUARD_KIND_EXPECTED = {
    'unsupported_odd_data_access': EVEN,
    'step_limit': BUDGET,
    'rng_pointer_outside_ram': RNG_OUTSIDE,
    'unsupported_TRAP': UNSUPPORTED_MACHINE,
    'unsupported_data_device': DEVICE_ADDR,
}
# Per-label expectations that refine a kind (the unmapped / protected kind splits into a write to ROM or the banked window and a read of an unmapped address) or differ from it (op 08 failure).
GUARD_EXPECTED = {
    'op08-oddlen-0b-top': WRITE_DEVICE, 'op08-oddlen-09-top': WRITE_DEVICE, 'op08-pool-count-nohead': WRITE_DEVICE, 'op09-pool-nohead': WRITE_DEVICE, 'direct-e975a-a6-rom': WRITE_DEVICE,
    'child-stream-null': DEVICE_ADDR, 'direct-e9774-a0-unmapped': DEVICE_ADDR,
    'op08-fail-undeclared': CUE_FAILURE, 'trap-e957a-op08-fail-undeclared': CUE_FAILURE,
}
# The two op 08 failure guards: the native observer reaches the TRAP boundary e957a (one more split segment) where the C++ already fails inside the 2986 failure return.
SEGMENT_DIFFERENCE = ('op08-fail-undeclared', 'trap-e957a-op08-fail-undeclared')
KIND_NOTES = {
    'unsupported_TRAP': ('native_TRAP_boundary_vs_cpp_unrouted_PC', 'native: the TRAP #15 boundary is reached without a declared stop and the TRAP is never executed (guard unsupported_TRAP); C++: the transfer lands on the same non-routed TRAP '
                         'PC (the 8 sites are excluded from routing) and reports unsupported animation machine PC at the same split segment'),
    'unmapped_or_protected': ('native_bus_error_vs_cpp_device_check', 'native: write to the program ROM / banked window or a data access to an unmapped address (bus error); C++: checked write-device / device-address error, state preserved'),
    'unsupported_data_device': ('native_unsupported_data_device_vs_cpp_device_address_check', 'native: data access to the video device region 3c0000 refused; C++: unsupported program bus device address'),
    'step_limit': ('native_watchdog_vs_cpp_block_budget', 'native: the declared instruction watchdog expired (the original code has no bound); C++: the block budget error (loops have no extra limit, F3 main decision 7)'),
    'rng_pointer_outside_ram': ('same_policy_F1c2_RNG_guard', 'the native observer declares the F1c2 policy as a guard row (nothing executed at the entry of 49a58); the C++ reports the same policy as a checked error'),
    'unsupported_odd_data_access': ('same_check_class', 'native: odd WORD/LONG access (address error on the original CPU); C++: the program bus requires an even WORD/LONG address (checked error)'),
    'unsupported_code_target': ('native_code_target_guard_vs_cpp_unrouted_PC', 'native: control transfer to an address outside every routed range; C++: the same transfer is reached (verified with a stop at that PC) and is unrouted'),
}
GUARD_NOTES = {
    'op08-fail-undeclared': ('native_TRAP_e957a_vs_cpp_cue_failure', 'native: op 08 object creation failed, BCS.W e9576 not taken, TRAP e957a reached undeclared (guard); C++: the U7 2986 failure return has no known caller '
                             '(`cue wrapper failure requires known caller X`) one split segment earlier (deliberate difference, main decision U7 option A)'),
    'trap-e957a-op08-fail-undeclared': ('native_TRAP_e957a_vs_cpp_cue_failure', 'same as op08-fail-undeclared (the trap group fixture)'),
}
CODE_TARGET_NOTE = {
    'odd': UNALIGNED_PC,
    'f3b_interior': UNSUPPORTED_OPS,
    'f3a_interior': UNSUPPORTED_EVENT,
    'outside': UNSUPPORTED_MACHINE,
}


def classify_code_target(g):
    if g.get('odd_pc'):
        return 'odd'
    if g['target'] in TRAP_SITES:
        return 'outside'
    if in_f3b(g['target']):
        return 'f3b_interior'
    return 'f3a_interior' if in_f3a(g['target']) else 'outside'


def expected_for(label, g):
    if g['problem'] == 'unsupported_code_target':
        return CODE_TARGET_NOTE[classify_code_target(g)]
    return GUARD_EXPECTED.get(label) or GUARD_KIND_EXPECTED.get(g['problem'])


# ----------------------------------------------------------------------------------------------------------------- typed condition replay
class Ctx(object):
    pass


def initial_state(res, base_blob):
    fx = res['fixture']
    name = fx['initial_RAM_sha256']
    try:
        ram = blob_bytes(name)
        rebuilt = False
    except FileNotFoundError:
        ram = bytearray(blob_bytes(fx['seed']['base_ram_sha256']))
        for w in fx['initial_host_writes']:
            data = bytes.fromhex(w['hex'])
            assert len(data) == w['size'] and 0x100000 <= w['address'] and w['address'] + len(data) <= 0x200000
            ram[w['address'] & 0xffff:(w['address'] & 0xffff) + len(data)] = data
        ram = bytes(ram)
        assert sha(ram) == name
        rebuilt = True
    pvc = blob_bytes(fx['initial_PVC_sha256'])
    regs = dict(fx['initial_regs'])
    assert sorted(regs) == sorted(k for k in common.REGS if k != 'a7')
    state = dict(regs, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=initial_carry(fx['seed']['declared_sr']))
    return ram, pvc, fx['bank_state'][0], state, rebuilt


def compare_phase(totals, label, k, np_, actual, entry, last_pcs_known=True):
    """One C++ split phase vs the native phase record (no state injection: the entry is the previous actual C++ output)."""
    res, out_ram, out_pvc, ports, error = actual
    e_ram, e_state, e_pvc, e_bank = entry
    assert res['ok'] and not error and res['status'] == 0, (label, k, error)
    inc = np_['incoming']
    assert {x: inc[x] for x in REG16} == {x: e_state[x] for x in REG16} and inc['pc'] == e_state['pc'], (label, k, 'native incoming differs from the chain state')
    assert sha(e_ram) == np_['artifacts']['ram_before'] and e_bank == np_['bank_before'], (label, k, 'native input RAM / bank differ from the chain state')
    out = np_['outgoing']
    assert {x: res[x] for x in REG16} == {x: out[x] for x in REG16} and res['pc'] == out['pc'], (label, k, {x: (res[x], out[x]) for x in REG16 if res[x] != out[x]})
    assert sha(out_ram) == np_['artifacts']['ram_after'], (label, k, 'RAM')
    assert sha(ports) == np_['artifacts']['ports'] and len(ports) // 9 == np_['counts']['pvc'] + np_['counts']['video'] + np_['counts']['watchdog'], (label, k, 'ports')
    nat_pvc = blob_bytes(np_['artifacts']['pvc_after'])
    assert out_pvc[:0x1ff0] == nat_pvc[:0x1ff0] and out_pvc[0x1ff4:] == nat_pvc[0x1ff4:], (label, k, 'PVC image')
    assert bank_words(out_pvc) == (np_['ff8_after'], np_['ff9_after']) and res['bank_base'] == np_['modeled_bank'], (label, k, 'bank words')
    assert res['external_reads'] == np_['counts']['external_reads'], (label, k, 'external reads')
    totals['phases_equal_native'] += 1


def typed_row(res):
    return dict(number=res['index'], label=res['label'], group=res['group'], guarded=res['guarded'])


def replay_typed(ctx, row):
    cond = load_condition(row)
    res = cond['result']
    label = res['label']
    fx = res['fixture']
    step = res['steps'][0]
    acc = dict(totals=collections.Counter(), guard=None, deliberate=None, failures=[], starts_seen=set(), consumer=collections.Counter(), probes={}, carry_stops=collections.Counter())
    totals = acc['totals']
    ram, pvc, bank, state, rebuilt = initial_state(res, None)
    totals['initial_RAM_rebuilt_from_base_plus_writes'] += int(rebuilt)
    ram, state_in = apply_changes(ram, state, step['declared_changes'])
    external = fx['external']
    stop = step['stop_pc']
    if step['observed_end'] is not None and step['observed_end'] != stop:
        # the native step declares the dispatcher return plus alternative boundary stops (e94fe and the bundled-branch targets); the native run ended at the first one reached
        assert step['observed_end'] in step['boundary_stop_pcs'], (label, step['observed_end'])
        stop = step['observed_end']
        totals['steps_ending_at_boundary_stop'] += 1
    checkpoints = step['checkpoints']
    tag = 't%03d' % row['number']
    cont = inv(ctx, tag + '_cont', ram, state_in, pvc, bank, stop, external)
    totals['continuous_runs'] += 1
    phases, how = split_chain(ctx, tag, ram, state_in, pvc, bank, stop, checkpoints, external)
    totals['split_phases'] += len(phases)
    nat = res['phases']
    cc0 = res['continuous_control'][0]
    trace = blob_json(cc0['artifacts']['trace']) if cc0['artifacts']['trace'] else None
    chain = hashlib.sha256()
    if not res['guarded'] and not cont[0]['ok']:
        deliberate_failure(ctx, acc, res, row, ram, state_in, pvc, bank, cont, phases, how, stop, external, nat)
        totals['deliberate_failure_conditions'] += 1
        acc['out_row'] = dict(number=row['number'], label=label, group=res['group'], guarded=False, deliberate_failure=True, cpp_phases=len(phases), native_phases=len(nat))
        return acc
    if res['guarded']:
        guard_row(ctx, acc, res, row, ram, state_in, pvc, bank, cont, phases, how, stop, external, nat, trace)
        totals['guard_conditions'] += 1
        out = dict(number=row['number'], label=label, group=res['group'], guarded=True, cpp_phases=len(phases), native_phases=len(nat))
        acc['out_row'] = out
        return acc
    assert how == 'stop' and len(phases) == len(nat) == len(checkpoints) + 1 or how == 'wait', (label, how, len(phases), len(nat))
    for k, (p, np_) in enumerate(zip(phases, nat)):
        assert p['target'] == (np_['stop_pc'] if k < len(nat) - 1 else np_['outgoing']['pc']), (label, k, hex(p['target']), hex(np_['stop_pc']))
        compare_phase(totals, label, k, np_, p['actual'], p['entry'])
        res_k = p['actual'][0]
        chain.update(bytes.fromhex(state_sha(p['actual'][1], out_state(res_k), res_k['bank_base'], p['actual'][3])))
    # continuous C++ run vs split chain vs native continuous record
    r, out_ram, out_pvc, ports, error = cont
    assert r['ok'] and not error and r['status'] == 0
    last = phases[-1]['actual']
    assert last[1] == out_ram and last[2] == out_pvc and out_state(last[0]) == out_state(r) and last[0]['bank_base'] == r['bank_base']
    assert b''.join(p['actual'][3] for p in phases) == ports and sum(p['actual'][0]['external_reads'] for p in phases) == r['external_reads']
    totals['split_equals_continuous'] += 1
    assert {x: r[x] for x in REG16} == {x: cc0['outgoing'][x] for x in REG16} and r['pc'] == cc0['outgoing']['pc'] == stop
    assert sha(out_ram) == cc0['artifacts']['ram_after'] and sha(ports) == cc0['artifacts']['ports'] and bank_words(out_pvc) == (cc0['ff8_after'], cc0['ff9_after'])
    nat_pvc = blob_bytes(cc0['artifacts']['pvc_after'])
    assert out_pvc[:0x1ff0] == nat_pvc[:0x1ff0] and out_pvc[0x1ff4:] == nat_pvc[0x1ff4:]
    if step['a7_expectation'] and cc0['stop_reason'] in ('return-dispatcher', 'return'):
        assert r['a7'] == step['a7_expectation'][1], (label, 'declared A7 at the stop')
        totals['declared_A7_equal'] += 1
    totals['continuous_equals_native'] += 1
    totals['conditions'] += 1
    totals['ports'] += len(ports) // 9
    totals['bank_writes_to_2ffff0_2ffff2'] += sum(1 for i in range(0, len(ports), 9) if 0x2fe000 <= struct.unpack('>I', ports[i + 1:i + 5])[0] < 0x300000)
    if stop != state_in['pc']:
        carry_checks(ctx, acc, res, cc0, step, tag, trace, phases, state_in, ram, pvc, bank, stop, external)
    else:
        totals['zero_step_conditions_state_unchanged'] += int(out_state(r) == state_in and out_ram == ram and out_pvc == pvc and not ports)
    acc['out_row'] = dict(number=row['number'], label=label, group=res['group'], guarded=False, stop_reason=cc0['stop_reason'], cpp_phases=len(phases), native_phases=len(nat),
                          C_phase_state_chain_sha256=chain.hexdigest(), final_pc=hex(r['pc']))
    return acc


def guard_row(ctx, acc, res, row, ram, state_in, pvc, bank, cont, phases, how, stop, external, nat, trace):
    label = res['label']
    ng = nat[-1]['guard']
    assert ng and res['continuous_control'][0]['guard'] == ng, label
    if cont[0]['ok']:
        deliberate_accept(ctx, acc, res, row, ram, state_in, pvc, bank, cont, phases, how, stop, external, nat, ng)
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
    # the successful phases before the failing one are compared with the native phase records
    for k, p in enumerate(phases[:-1]):
        compare_phase(acc['totals'], label, k, nat[k], p['actual'], p['entry'])
    expected = expected_for(label, ng)
    entry = dict(label=label, group=res['group'], native_problem=ng['problem'], native_reason=ng.get('reason'), native_target=hex(ng['target']) if ng.get('target') is not None else None,
                 native_refused_before_jump=bool(ng.get('refused_before_jump')), native_odd_pc=bool(ng.get('odd_pc')), checked_API_error=error, expected_API_error=expected,
                 cpp_error_matches_expected=error == expected, cpp_phases_before_error=len(phases) - 1, native_split_phases=len(nat),
                 same_split_segment_as_native=len(phases) == len(nat), all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False, state_with_other_carries={})
    for carry in (0, 1, 2):
        if carry == state_in['carry']:
            continue
        s2 = dict(state_in, carry=carry)
        again = inv(ctx, 'g%03d_carry%d' % (row['number'], carry), ram, s2, pvc, bank, stop, external)
        entry['state_with_other_carries'][CARRY_NAME[carry]] = check_preserved(again, ram, s2, pvc, bank)
    if ng['problem'] == 'unsupported_code_target' and not ng.get('odd_pc') and ng['target'] != stop and ng['target'] % 2 == 0 and not ng.get('refused_before_jump') and not ng.get('refused_before_execution'):
        # the native transfer target is reachable in C++ with that stop (transfer then unrouted)
        reach = inv(ctx, 'g%03d_reach' % row['number'], ram, state_in, pvc, bank, ng['target'], external)
        assert reach[0]['ok'] and not reach[4] and reach[0]['pc'] == ng['target'] and reach[0]['status'] == 0, (label, 'C++ does not reach the native transfer target')
        entry['cpp_reaches_native_transfer_target_with_stop'] = '%x' % ng['target']
    note = GUARD_NOTES.get(label) or KIND_NOTES.get(ng['problem'])
    entry['classification'] = note[0] if note else 'same_check_class'
    entry['rule'] = note[1] if note else None
    acc['guard'] = entry
    if expected is None or error != expected:
        acc['failures'].append(('guard error', label, error, expected))
    if not entry['same_split_segment_as_native'] and label not in SEGMENT_DIFFERENCE:
        acc['failures'].append(('guard segment', label, len(phases), len(nat)))
    if label in SEGMENT_DIFFERENCE:
        entry['failing_phase_stop'] = hex(phases[-1]['target'])
        entry['native_reaches_trap_after_phases'] = len(nat)
        if not (len(phases) + 1 == len(nat) and phases[-1]['target'] == 0xe9576):
            acc['failures'].append(('op08 failure segment', label, len(phases), len(nat), hex(phases[-1]['target'])))


# Native NON-guard conditions whose C++ run fails by a deliberate difference: the original op 08 failure path (2986 returns C = 0 -> BCS not taken -> TRAP #15 at e957a, a declared native stop) is
# an unknown-caller failure of the U7 cue wrapper in the C++ (main decision, U7 option A): the C++ reports a checked error and preserves the API state.
OP08_FAIL_RULE = ('native: op 08 object creation fails (28ae / 2986 return C = 0), BCS.W e9576 is not taken and the declared stop is the TRAP #15 boundary e957a; C++: the U7 2986 failure return has no known '
                  'caller (main decision, U7 option A) and reports the checked error `cue wrapper failure requires known caller X`; the API state is preserved (no rollback equivalence claimed)')
DELIBERATE_FAIL_CLASS = {'op0c-rng-original-completes': 'deliberate_difference_RNG_policy_vs_original_completes'}
DELIBERATE_FAIL = {
    'op08-fail': (CUE_FAILURE, OP08_FAIL_RULE),
    'op08-null-callback': (CUE_FAILURE, OP08_FAIL_RULE),
    'trap-e957a-op08-fail-declared': (CUE_FAILURE, OP08_FAIL_RULE),
    'op0c-rng-original-completes': (RNG_OUTSIDE, 'native fixture with the F1c2 RNG policy disabled documents the ORIGINAL behaviour for the ring pointer fffd0 (reads the program ROM mirror, writes +2e into the work RAM and completes); '
                                    'the C++ keeps the F1c2 policy and refuses a ring pointer outside work RAM before any access (checked error, state preserved)'),
}


def deliberate_failure(ctx, acc, res, row, ram, state_in, pvc, bank, cont, phases, how, stop, external, nat):
    label = res['label']
    assert label in DELIBERATE_FAIL, (label, 'C++ failed a non-guard native condition without a declared reason', cont[4])
    expected, rule = DELIBERATE_FAIL[label]
    error = check_preserved(cont, ram, state_in, pvc, bank, expected)
    first_failed = None
    for index, p in enumerate(phases):
        if not p['actual'][0]['ok']:
            first_failed = index
            e_ram, e_state, e_pvc, e_bank = p['entry']
            chain_error = check_preserved(p['actual'], e_ram, e_state, e_pvc, e_bank, expected)
            assert chain_error == error
    assert how == 'error' and first_failed == len(phases) - 1, (label, how)
    for k, p in enumerate(phases[:-1]):
        compare_phase(acc['totals'], label, k, nat[k], p['actual'], p['entry'])
    others = {}
    for carry in (0, 1, 2):
        if carry == state_in['carry']:
            continue
        s2 = dict(state_in, carry=carry)
        again = inv(ctx, 'f%03d_carry%d' % (row['number'], carry), ram, s2, pvc, bank, stop, external)
        others[CARRY_NAME[carry]] = check_preserved(again, ram, s2, pvc, bank, expected)
    acc['deliberate'] = dict(label=label, group=res['group'], native_problem=None, native_reason='native condition reached the declared stop %x without a guard' % stop, native_target=hex(stop), checked_API_error=error,
                        expected_API_error=expected, cpp_error_matches_expected=True, cpp_phases_before_error=len(phases) - 1, native_split_phases=len(nat), native_final_pc=hex(nat[-1]['outgoing']['pc']),
                        failing_phase_stop=hex(phases[-1]['target']), failing_phase_native_stop=hex(nat[len(phases) - 1]['stop_pc']), same_split_segment_as_native=len(phases) == len(nat),
                        all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False, state_with_other_carries=others, classification=DELIBERATE_FAIL_CLASS.get(label, 'deliberate_difference_op08_failure_path'), rule=rule)


# Native guards the C++ executor deliberately does NOT refuse (the C++ bus models the access; the native observer refuses it as an unmodeled device access).
ACCEPT_CLASS = {'op0c-rng-high-byte': 'native_cannot_follow_24bit_masked_RNG_pointer_cpp_masks_it'}
DELIBERATE_ACCEPT = {
    'op0c-rng-high-byte': 'the stage area RNG ring pointer LONG 10d722 has a nonzero top byte (0110d6b4) over a work RAM 24 bit address: the native observer cannot follow it (Unicorn M68000 24 bit address space: guard '
                          'row rng_pointer_high_byte); the C++ masks the 24 bit address like the other program bus accesses and runs on (F1c2 policy)',
    'guard-stream-pvc': 'the event stream pointer addresses the PVC register page (2ffff0): the native observer refuses a data access to 2ffff0 of size 1 (unsupported_PVC_read_or_write: only the three bank writes '
                        'are permitted PVC accesses); the C++ bus reads the PVC register image byte (device image modeled by the machine, like every other unit) and runs on',
}


def deliberate_accept(ctx, acc, res, row, ram, state_in, pvc, bank, cont, phases, how, stop, external, nat, ng):
    label = res['label']
    assert label in DELIBERATE_ACCEPT, (label, 'C++ accepted a native guard without a declared reason')
    r, out_ram, out_pvc, ports, error = cont
    assert r['ok'] and not error and r['pc'] == stop and r['status'] == 0
    assert how == 'stop'
    last = phases[-1]['actual']
    assert last[1] == out_ram and last[2] == out_pvc and out_state(last[0]) == out_state(r) and b''.join(p['actual'][3] for p in phases) == ports
    entry = dict(label=label, group=res['group'], native_problem=ng['problem'], native_reason=ng.get('reason'), native_target=None, native_refused_before_jump=False, native_odd_pc=False,
                 checked_API_error=None, expected_API_error=None, cpp_error_matches_expected=None, cpp_phases_before_error=None, native_split_phases=len(nat), cpp_split_phases=len(phases),
                 same_split_segment_as_native=None, all_API_outputs_preserved=None, native_fault_rollback_equivalence_claimed=False, state_with_other_carries={},
                 classification=ACCEPT_CLASS.get(label, 'native_refuses_device_access_cpp_models_it'), rule=DELIBERATE_ACCEPT[label], cpp_continuous_equals_split=True, cpp_final_pc=hex(r['pc']),
                 cpp_RAM_sha256=sha(out_ram), cpp_state_sha256=state_sha(out_ram, out_state(r), r['bank_base'], ports))
    acc['guard'] = entry
    acc['totals']['guard_conditions_accepted_by_cpp'] += 1


def carry_checks(ctx, acc, res, cc0, step, tag, trace, phases, state_in, ram, pvc, bank, stop, external):
    """Carry as block classification: consumer e9248 / e9258 Known C vs the native executed path, flip controls, Unknown error; single-block probes of the FLOW_ONLY table."""
    totals = acc['totals']
    label = res['label']
    st = ctx.st
    start_set = ctx.start_set
    instructions = st['instructions']
    pcs = trace['pcs'] if trace else None
    at_start = [(state_in['pc'], (ram, state_in, pvc, bank), 0 if pcs else None)]
    acc['starts_seen'].add(state_in['pc'])
    for p in phases:
        target = p['target']
        r = p['actual'][0]
        acc['carry_stops']['%x:%s' % (target, CARRY_NAME[r['carry']])] += 1
        if r['status'] == 1:
            continue
        if target in start_set:
            acc['starts_seen'].add(target)
        if target in start_set and target != stop:
            index = pcs.index(target, 1) if pcs and target in pcs[1:] else None
            at_start.append((target, (p['actual'][1], out_state(r), p['actual'][2], r['bank_base']), index))
    for pc, (s_ram, s_state, s_pvc, s_bank), index in at_start:
        if pc not in start_set or index is None or pcs is None:
            continue
        if pc in CONSUMERS:
            if s_state['carry'] not in (1, 2):
                acc['failures'].append(('consumer entered with Unknown C', label, hex(pc)))
                continue
            known = s_state['carry']
            want = branch_target(pc, known)
            assert pcs[index + 1] == want, (label, hex(pc), known, hex(pcs[index + 1]), hex(want))
            totals['consumer_known_carry_equals_native_branch_path'] += 1
            key = (pc, known)
            if acc['consumer'][key] >= 2:
                continue
            acc['consumer'][key] += 1
            flipped = 3 - known
            other = branch_target(pc, flipped)
            again = inv(ctx, '%s_flip%x_%d' % (tag, pc, acc['consumer'][key]), s_ram, dict(s_state, carry=flipped), s_pvc, s_bank, other, external)
            r2 = again[0]
            assert r2['ok'] and not again[4] and r2['pc'] == other and r2['status'] == 0 and r2['carry'] == flipped, (label, hex(pc))
            assert {k: r2[k] for k in REG16} == {k: s_state[k] for k in REG16} and again[1] == s_ram and again[2] == s_pvc and r2['bank_base'] == s_bank and again[3] == b'' and r2['external_reads'] == 0
            totals['consumer_flip_checks'] += 1
            totals['consumer_flip_%x_incoming_%s' % (pc, CARRY_NAME[known])] += 1
            if (pc, 0) not in acc['consumer']:
                acc['consumer'][(pc, 0)] += 1
                s0 = dict(s_state, carry=0)
                bad = inv(ctx, '%s_unk%x' % (tag, pc), s_ram, s0, s_pvc, s_bank, other, external)
                check_preserved(bad, s_ram, s0, s_pvc, s_bank, UNKNOWN_CARRY)
                totals['consumer_unknown_carry_errors'] += 1
            continue
        if pc in acc['probes'] or pc in ctx.probed_done:
            continue
        nxt, _ = native_succ(pcs, index, st['blocks'], instructions, start_set)
        if nxt == pc:
            totals['carry_probe_skipped_self_loop_occurrence'] += 1       # stop == entry PC is a zero step: another occurrence / condition supplies the exit
            continue
        probe_block(ctx, acc, label, '%s_probe%x' % (tag, pc), pc, (s_ram, s_state, s_pvc, s_bank), nxt, external)


def probe_block(ctx, acc, label, tag, pc, entry, nxt, external):
    """Single-block probe: the block at `pc` run from incoming C Clear and Set to its native successor; the output C is the incoming one for a FLOW_ONLY block, Unknown otherwise (2898: Known Set)."""
    totals = acc['totals']
    s_ram, s_state, s_pvc, s_bank = entry
    slot = acc['probes'].setdefault(pc, {1: True, 2: True})
    outs = {}
    for k in (1, 2):
        a = inv(ctx, '%s_%d' % (tag, k), s_ram, dict(s_state, carry=k), s_pvc, s_bank, nxt, external)
        r2 = a[0]
        assert r2['ok'] and not a[4] and r2['pc'] == nxt and r2['status'] == 0, (label, hex(pc), hex(nxt), a[4])
        want = 2 if pc == SET_PRODUCER else (k if pc in ctx.preserve else 0)
        assert r2['carry'] == want, (label, hex(pc), k, r2['carry'])
        slot[k] = slot[k] and r2['carry'] == k
        outs[k] = a
        totals['carry_probes'] += 1
    a1, a2 = outs[1], outs[2]
    assert {x: y for x, y in a1[0].items() if x != 'carry'} == {x: y for x, y in a2[0].items() if x != 'carry'} and a1[1:4] == a2[1:4], (label, hex(pc))
    totals['carry_probe_pairs_equal_except_carry'] += 1


def guarded_typed(ctx, row):
    try:
        return replay_typed(ctx, row)
    except Exception:
        return dict(error=traceback.format_exc(), label=row['label'])


def run_parallel(function, items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(function, items))


# ----------------------------------------------------------------------------------------------------------------- natural nodes
NAT = {}


def nat_node(ctx, acc, case, frame, node):
    key = (case, frame, node['seq'])
    row = NAT['rows'][key]
    rec = NAT['recs'][key]
    totals = acc['totals']
    ram = bytes(node['entry_ram'])
    regs = dict(node['entry_regs'])
    bank = tuple(node['entry_bank'])
    ed = sched_state_digest(ram, regs, NODE_PC, bank)
    assert ed == rec['entry'] == row['entry'], (key, 'regenerated entry state differs from the recorded one')
    totals['entry_digest_equal_recorded'] += 1
    pvc = pvc_page_for(bank)
    state = dict({k: regs[k] for k in REG16}, pc=NODE_PC, carry=0)
    assert row['end'] == FRAME_RET and row['a6'] == node['a6'] == regs['a6'] and row['cb'] == node['cb'], key
    stop = FRAME_RET
    tag = 'n%03d_%03d_%02d' % key
    cont = inv(ctx, tag + '_cont', ram, state, pvc, bank[0], stop, 0)
    r, out_ram, out_pvc, ports, error = cont
    assert r['ok'] and not error and r['status'] == 0 and r['pc'] == stop, (key, error)
    ff8, ff9 = bank_words(out_pvc)
    ex = sched_state_digest(out_ram, {k: r[k] for k in REG16}, r['pc'], (r['bank_base'], ff8, ff9))
    assert ex == row['state'] == rec['exit'], (key, 'C++ exit state digest differs from the recorded one')
    assert r['a7'] == row['a7'] and len(ports) // 9 == rec['ports'] == row['ports'], (key, 'a7 / port count')
    assert sched_ports_digest(ports) == rec['ports_sha'], (key, 'ordered port digest')
    totals['ordered_port_digest_equal_recorded'] += 1
    totals['nodes_end_2ac2'] += 1
    totals['exit_digest_equal_recorded'] += 1
    totals['nodes'] += 1
    totals['cb_%x' % row['cb']] += 1
    totals['self_delete_nodes'] += int(bool(row['self_delete']))
    totals['ports'] += len(ports) // 9
    acc['chain'].update(bytes.fromhex(ex))
    leads = set(row['lead_set'])
    for pc in CONSUMERS:
        if pc in leads:
            totals['nodes_with_consumer_%x' % pc] += 1
    for pc in leads & ctx.start_set:
        acc['starts_seen'].add(pc)
    b = row['blobs']
    assert read_blob(b['ram_before'] + '.bin') == ram and read_blob(b['ram_after'] + '.bin') == out_ram
    nat_pvc = read_blob(b['pvc_after'] + '.bin')
    assert out_pvc[:0x1ff0] == nat_pvc[:0x1ff0] and out_pvc[0x1ff4:] == nat_pvc[0x1ff4:]
    assert read_blob(b['ports'] + '.bin') == ports
    trace = blob_json(b['trace'])
    pcs = trace['pcs']
    assert pcs[0] == NODE_PC and pcs[-1] == stop
    order = []
    seen = set()
    for pc in pcs[1:]:
        if pc in ctx.checkpoint_set and pc not in seen and pc != stop and pc != NODE_PC:
            seen.add(pc)
            order.append(pc)
    assert len(order) + 1 == row['phases'], (key, len(order) + 1, row['phases'])
    phases, how = split_chain(ctx, tag, ram, state, pvc, bank[0], stop, order, 0)
    assert how == 'stop' and len(phases) == row['phases'], (key, how)
    last = phases[-1]['actual']
    assert last[1] == out_ram and last[2] == out_pvc and out_state(last[0]) == out_state(r) and b''.join(p['actual'][3] for p in phases) == ports
    totals['dumped_nodes_byte_equal'] += 1
    totals['dumped_split_phases'] += len(phases)
    totals['dumped_split_equals_continuous'] += 1
    acc['cpp_phases'] += len(phases)
    nat_carry(ctx, acc, key, tag, trace, phases, state, ram, pvc, bank[0], stop)
    acc['cpp_runs'] += 1


def nat_carry(ctx, acc, key, tag, trace, phases, state_in, ram, pvc, bank, stop):
    totals = acc['totals']
    pcs = trace['pcs']
    start_set = ctx.start_set
    instructions = ctx.st['instructions']
    cur = [(state_in['pc'], (ram, state_in, pvc, bank), 0)]
    for p in phases:
        target = p['target']
        r = p['actual'][0]
        acc['carry_stops']['%x:%s' % (target, CARRY_NAME[r['carry']])] += 1
        if target in start_set and target != stop:
            cur.append((target, (p['actual'][1], out_state(r), p['actual'][2], r['bank_base']), pcs.index(target, 1)))
    for pc, (s_ram, s_state, s_pvc, s_bank), index in cur:
        if pc in CONSUMERS:
            assert s_state['carry'] in (1, 2), (key, hex(pc))
            want = branch_target(pc, s_state['carry'])
            assert pcs[index + 1] == want, (key, hex(pc))
            totals['consumer_known_carry_equals_native_branch_path'] += 1
        elif pc in ctx.need_probe and pc not in acc['probes']:
            nxt, _ = native_succ(pcs, index, ctx.st['blocks'], instructions, start_set)
            if nxt == pc:
                totals['carry_probe_skipped_self_loop_occurrence'] += 1
                continue
            probe_block(ctx, acc, '%s' % (key,), '%s_probe%x' % (tag, pc), pc, (s_ram, s_state, s_pvc, s_bank), nxt, 0)


def natural_seed(case):
    """One natural seed in a forked worker: the scheduler's SeedRun regenerates every e9150 / e9176 node entry state; each node runs in the actual C++."""
    import observe_animation_machine_scheduler as sched
    ctx = NAT['ctx']
    acc = dict(totals=collections.Counter(), probes={}, carry_stops=collections.Counter(), starts_seen=set(), chain=hashlib.sha256(), cpp_phases=0, cpp_runs=0, split_targets=collections.Counter())
    try:
        sd = sched.SEEDS[case]
        snap, meta = sched.seed_snap(sd)
        seen = []

        def hook(self, node):
            if node['cb'] not in CALLBACKS or (case, self.frame, node['seq']) not in NAT['rows']:
                return
            seen.append((self.frame, node['seq']))
            nat_node(ctx, acc, case, self.frame, node)

        def noop(self, node):
            pass
        sched.SeedRun.f3_replay = hook
        sched.SeedRun.model_node = noop
        # Pin the original observation scope independently of finaltree rA/rB
        # coverage, which otherwise extends newly supported seeds to 400 frames.
        published = NAT['seed_scope'][case]
        run = sched.SeedRun(sched.G['program'], sched.G['fixed'], sched.G['levels'], snap, 'continuous', published['frames_done'], heavy=True, sink=None, extend=False).run()
        assert run.frames_done == published['frames_done'] and run.stop['reason'] == published['stop']['reason'], (case, run.frames_done, run.stop, published)
        expected_keys = sorted((r['frame'], r['seq']) for r in NAT['rows'].values() if r['case'] == case)
        assert sorted(seen) == expected_keys and len(set(seen)) == len(seen), (case, len(seen), len(expected_keys))
        stop = run.stop
        acc['out_row'] = dict(case=case, family=sd['family'], bank=sd['bank'], nodes=len(seen), frames_done=run.frames_done, scheduler_stop_reason=stop['reason'], cpp_runs=acc['cpp_runs'],
                              cpp_split_phases=acc['cpp_phases'], C_exit_state_chain_sha256=acc['chain'].hexdigest())
        acc['starts_seen'] = sorted(acc['starts_seen'])
        acc['totals'] = dict(acc['totals'])
        acc['carry_stops'] = dict(acc['carry_stops'])
        acc['split_targets'] = dict(acc['split_targets'])
        acc['chain'] = None
        return acc
    except Exception:
        return dict(error=traceback.format_exc(), case=case)
    finally:
        for srv in SERVERS:
            srv.close()
        reset_servers()


def natural_init():
    reset_servers()


# ----------------------------------------------------------------------------------------------------------------- API-only checks
def reject_one(args):
    ctx, label, base, changes, stop, expected = args
    ram, state, pvc, bank = base
    s = dict(state, carry=2)
    s.update(changes)
    actual = inv(ctx, 'neg_' + label, ram, s, pvc, bank, stop, 0)
    check_preserved(actual, ram, s, pvc, bank, expected)
    return dict(label=label, pc=changes.get('pc'), error=expected, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False)


def negatives(ctx, base, st):
    ram, state, pvc, bank = base
    jobs = []
    for pc in st['interior']:
        jobs.append((ctx, 'interior_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_OPS))
    for pc in st['odd_pcs']:
        jobs.append((ctx, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    # the eight TRAP #15 sites are boundaries without an executor: reached by a direct entry with a stop elsewhere they are unrouted (the zero-step with stop == PC is checked in zero_step_one)
    for pc in st['traps']:
        jobs.append((ctx, 'trap_site_without_stop_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    # data (ASCII error strings) between the code ranges
    for pc in st['string_even']:
        jobs.append((ctx, 'string_area_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    for pc in st['string_odd']:
        jobs.append((ctx, 'string_area_odd_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    # neighbours of the 8 routed ranges: the first address after each end (and the one before each start) that no other executor routes
    other = [r for r in routed_ranges() if r not in F3B_RANGES]
    neighbours = []
    for low, high in F3B_RANGES:
        for pc, name in ((high, 'after'), (low - 2, 'before')):
            if in_ranges(pc, F3B_RANGES) or in_ranges(pc, STRING_RANGES) or in_ranges(pc, other):
                continue
            neighbours.append(pc)
            jobs.append((ctx, 'unrouted_%s_%06x' % (name, pc), base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    for pc in (0x1, 0xffffff, 0xdeadbeef):
        jobs.append((ctx, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    for pc in (0x0, 0xffffffe, 0x1000000, 0xdeadbee):
        jobs.append((ctx, 'out_of_range_entry_%x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
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
            assert {k: res[k] for k in common.REGS} == {k: s2[k] for k in common.REGS} and out_ram == ram
            controls.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], next_pc=hex(want), carry_preserved=True, status=0))
    return out, controls, neighbours


def zero_step_one(args):
    ctx, base, pc, carry = args
    ram, state, pvc, bank = base
    s = dict(state, pc=pc, carry=carry)
    result, out_ram, out_pvc, ports, error = inv(ctx, 'zero_%06x_%d' % (pc, carry), ram, s, pvc, bank, pc, 0)
    assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
    assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc and result['bank_base'] == bank and result['external_reads'] == 0 and not ports
    return (pc, carry)


def harness_equivalence(ctx, base, extra_cases):
    ram, state, pvc, bank = base
    cases = [('node_frame', state, ram, pvc, bank, FRAME_RET), ('zero_step', state, ram, pvc, bank, state['pc']),
             ('interior_error', dict(state, pc=0xe9560), ram, pvc, bank, 0xff000), ('unknown_carry_error', dict(state, pc=0xe936e, carry=0), ram, pvc, bank, 0xff000),
             ('odd_pc_error', dict(state, pc=0xe9559), ram, pvc, bank, 0xff000), ('trap_unrouted_error', dict(state, pc=0xe957a), ram, pvc, bank, 0xff000),
             ('trap_zero_step', dict(state, pc=0xe957a), ram, pvc, bank, 0xe957a)] + list(extra_cases)
    count = 0
    for label, st, r, p, b, stop in cases:
        a = invoke(ctx.exe, RUN_DIR, 'eq_batch_' + label, r, st, p, b, ctx.resources, stop, 0)
        o = invoke(ctx.exe, RUN_DIR, 'eq_oneshot_' + label, r, st, p, b, ctx.resources, stop, 0, oneshot=True)
        assert a[0] == o[0] and a[1:4] == o[1:4] and a[4].strip() == o[4].strip(), (label, a[0], o[0])
        count += 1
    return count


def entry_probe_map(report, negative, st, zero):
    """The native entry probes (992 addresses, 1000 rows) vs the C++ results: start -> zero-step state unchanged (3 carries), declared TRAP site -> zero-step ok, undeclared TRAP site -> unsupported
    animation machine PC, interior even PC -> unsupported animation stage event ops PC, odd address -> unaligned PC, string area -> unsupported animation machine PC / unaligned PC."""
    path = NATIVE_DIR / 'entry_probes.json.gz'
    data = path.read_bytes()
    assert sha(data) == report['entry_probes']['file_sha256']
    rows = json.loads(gzip.decompress(data))['rows']
    assert len(rows) == 1000
    cpp = {}
    for n in negative:
        if n.get('pc') is not None and n['label'].startswith(('interior_direct_entry_', 'odd_pc_entry_', 'trap_site_without_stop_', 'string_area_entry_', 'string_area_odd_entry_')):
            cpp[(n['label'].rsplit('_', 1)[0], n['pc'])] = n['error']
    zero_done = set(pc for pc, carry in zero)
    counts = collections.OrderedDict()
    for r in rows:
        pc, kind = r['pc'], r['kind']
        if kind == 'start-zero-step':
            assert pc in zero_done and r['state_unchanged'] is True and r['instructions'] == 0
            got, native = 'zero-step ok (3 carries)', 'zero-step (stop = entry PC, state unchanged)'
        elif kind == 'trap-site' and r['guard'] is None:
            assert pc in TRAP_SITES and pc in zero_done and r['state_unchanged'] is True
            got, native = 'zero-step ok (3 carries)', 'declared TRAP stop: zero-step (state unchanged)'
        elif kind == 'trap-site':
            assert cpp[('trap_site_without_stop', pc)] == UNSUPPORTED_MACHINE and r['guard'] == 'unsupported_TRAP'
            got, native = UNSUPPORTED_MACHINE, 'unsupported_TRAP (undeclared; the TRAP is never executed)'
        elif kind == 'interior-even':
            assert cpp[('interior_direct_entry', pc)] == UNSUPPORTED_OPS and r['guard'] == 'unsupported_code_target'
            got, native = UNSUPPORTED_OPS, r['guard'] + (' refused_before_execution' if r['refused_before_execution'] else '')
        elif kind == 'string-even':
            assert cpp[('string_area_entry', pc)] == UNSUPPORTED_MACHINE and r['guard'] == 'unsupported_code_target'
            got, native = UNSUPPORTED_MACHINE, r['guard']
        elif kind == 'string-odd':
            assert cpp[('string_area_odd_entry', pc)] == UNALIGNED_PC and r['guard'] == 'unsupported_code_target'
            got, native = UNALIGNED_PC, r['guard'] + (' (harness refusal, odd entry PC)' if r['refused_before_execution'] else '')
        else:
            assert kind == 'odd' and cpp[('odd_pc_entry', pc)] == UNALIGNED_PC and r['guard'] == 'unsupported_code_target' and r['refused_before_execution'] is True
            got, native = UNALIGNED_PC, r['guard'] + ' (harness refusal, odd entry PC)'
        key = (kind, native, got)
        counts[key] = counts.get(key, 0) + 1
    return [dict(kind=k[0], native=k[1], cpp=k[2], count=v) for k, v in counts.items()]


def scan_old_expectations(st):
    """Literal PCs of the F3b ranges in the older verifiers / C++ tests (read only, never edited): the candidates for boundary expectations that F3b routing invalidates."""
    pcs = set(st['even_pcs']) | set(st['string_even'])
    files = sorted((Path(MAIN_ROOT) / 'tools').glob('verify_animation_machine*.py')) + [ROOT / 'tools/verify_animation_machine_stage_event.py'] + sorted((ROOT / 'engine/tests').glob('animation_machine*_test.cpp'))      # older verifiers: main tree + the F3a verifier of this chain, read only
    rows = []
    for path in files:
        if path.name in ('verify_animation_machine_stage_event_ops.py', 'animation_machine_stage_event_ops_test.cpp'):
            continue
        found = collections.OrderedDict()
        for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            for m in re.finditer(r'0x([0-9a-fA-F]{3,6})\b', line):
                pc = int(m.group(1), 16)
                if pc in pcs:
                    found.setdefault(number, []).append(hex(pc))
        for number, hits in found.items():
            rows.append(dict(file=('tools/' if path.suffix == '.py' else 'engine/tests/') + path.name, line=number, pcs=sorted(set(hits)), note=OLD_NOTES.get((path.name, number), 'literal PC of a F3b range: classify')))
    return rows


OLD_UNAFFECTED_STOP = 'unaffected: the literal PC is a stop / expected PC or a fixture value; a stop is checked before routing, and the run arrives at it without executing it'
OLD_NOTES = {
    ('verify_animation_machine_stage_area.py', 64): 'unaffected: 49a84 is the exclusive end of the F1c2 range (49a58..49a84)',
    ('verify_animation_machine_stage_area.py', 1035): 'INVALIDATED: UNROUTED_NEIGHBOURS expects unsupported animation machine PC at 49a84 / 49a86 / 49a8c; 49a84 is now an F3b block start (runs) and 49a86 / 49a8c are F3b interior PCs '
                                                      '(unsupported animation stage event ops PC); see old_expectation_checks',
    ('animation_machine_stage_area_test.cpp', 653): 'unaffected: 49a84 is the exclusive end of the F1c2 range (49a58..49a84)',
    ('verify_animation_machine_stage_event.py', 68): 'unaffected: F3B_ENTRY (e94fe) as the stop boundary of the F3a node runs (stop is checked before routing)',
    ('verify_animation_machine_stage_event.py', 69): 'unaffected: range bounds of the F3a ranges (e9350 / e94fe / e9774 are exclusive ends)',
    ('verify_animation_machine_stage_event.py', 72): 'unaffected: native decision-3 data (bundled return PCs of the F3a e98ea block)',
    ('verify_animation_machine_stage_event.py', 1046): 'INVALIDATED: the F3a verifier expects unsupported animation machine PC for these 21 F3b PCs (f3b_pc_without_stop): the 8 TRAP sites keep it, the 9 block starts + e94fe now run, '
                                                       'the bundled e9396 e939e e96b0 give unsupported animation stage event ops PC; see old_expectation_checks',
    ('verify_animation_machine_stage_event.py', 1301): 'INVALIDATED: harness_equivalence unrouted_error enters e94fe with stop ff000 and expects unsupported animation machine PC; e94fe is now an F3b block start',
}
for _n in (85, 87, 89, 91, 244, 409):
    OLD_NOTES[('animation_machine_stage_event_test.cpp', _n)] = OLD_UNAFFECTED_STOP + ' (e94fe boundary fixtures)'
for _n in (207, 209, 211, 213, 219, 221, 423, 424, 425):
    OLD_NOTES[('animation_machine_stage_event_test.cpp', _n)] = OLD_UNAFFECTED_STOP + ' (e98ea bundled-return destinations e9428 e939a e93a2 e96b8 e96b4 are now routed F3b starts but the runs stop on arrival)'
OLD_NOTES[('animation_machine_stage_event_test.cpp', 315)] = 'list data (the five Z-consuming F3b PCs): the expectation was already updated by the F3b commit to unsupported animation stage event ops PC'
OLD_NOTES[('animation_machine_stage_event_test.cpp', 316)] = 'unaffected: the seven F3a routed ranges'
OLD_NOTES[('animation_machine_stage_event_test.cpp', 493)] = 'already updated by the F3b commit: 1a93c is an F3b interior PC (unsupported animation stage event ops PC)'
OLD_NOTES[('animation_machine_stage_event_test.cpp', 507)] = 'already updated by the F3b commit: F3b target ranges of the F3a computed-PC test (e9350 runs, other F3b targets give the ops error)'
OLD_NOTES[('animation_machine_stage_event_test.cpp', 510)] = 'already updated by the F3b commit: the computed target e9350 now runs'


def old_expectation_checks(ctx, base, st):
    """Actual C++ results at the PCs where the older verifiers expect `unsupported animation machine PC` (never edited): run from the base state with stop ff000 and carry Set."""
    ram, state, pvc, bank = base
    # Historical address sets are immutable evidence; final verifier source is
    # migrated and no longer contains the old unsupported tuple/line positions.
    f3a_negatives = sorted(set((0xe9350, 0xe9362, 0xe96cc, 0xe96f8, 0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788, 0xe9428, 0xe939a, 0xe93a2, 0xe96b4, 0xe96b8, 0xe9396, 0xe939e, 0xe96b0, 0xe94fe)))
    f3a_neighbours = sorted(set(pc for low, high in F3A_RANGES for pc in (high, low - 2) if in_f3b(pc) or pc in TRAP_SITES))
    stage_area_neighbours = [0x49a84, 0x49a86, 0x49a8c]
    groups = (('F3a verifier f3b_pc_without_stop (expected unsupported animation machine PC)', f3a_negatives), ('F3a verifier neighbours of the 7 F3a ranges (expected unsupported animation machine PC)', f3a_neighbours),
              ('F1c2 stage area verifier UNROUTED_NEIGHBOURS in F3b ranges (expected unsupported animation machine PC)', stage_area_neighbours))
    out = []
    for name, pcs in groups:
        rows = []
        for pc in pcs:
            s = dict(state, pc=pc, carry=2)
            res, out_ram, out_pvc, ports, error = inv(ctx, 'old_%06x' % pc, ram, s, pvc, bank, 0xff000, 0)
            kind = 'block start' if pc in ctx.start_set else ('TRAP site' if pc in TRAP_SITES else ('F3b interior' if in_f3b(pc) else 'outside F3b'))
            # only a TRAP site (or an address outside every F3b range) can still fail AT the entry PC with the machine error; a block start now executes (the error text, if any, comes from a later PC)
            still = kind in ('TRAP site', 'outside F3b') and error.strip() == UNSUPPORTED_MACHINE
            rows.append(dict(pc=hex(pc), kind=kind, ok=res['ok'], error=error.strip() or None, final_pc=hex(res['pc']) if res['ok'] else None, old_expectation_still_true=still))
        out.append(dict(group=name, count=len(rows), still_expected=sum(1 for r in rows if r['old_expectation_still_true']), changed=[r for r in rows if not r['old_expectation_still_true']]))
    # the F3a native computed-PC policy rows (e97e0 out of table): targets inside the F3b ranges
    f3a_obs = json.loads((ROOT / 'artifacts/animation_machine_stage_event_native/observation.json').read_text())
    rows = f3a_obs['computed_pc']['e97e0_out_of_table']
    inside = [r for r in rows if in_f3b(r['target'])]
    out.append(dict(group='F3a computed-PC policy rows (e97e0 out of table) with a target inside the F3b ranges', count=len(rows), still_expected=len(rows) - len(inside), changed=[hex(r['target']) for r in inside]))
    return out


def pin_audit():
    """Hard-coded digest pins of engine/src files in the older verifiers vs the digests of this unit (which changes animation_machine.cpp, animation_machine_internal.h and animation_machine_stage_event.cpp)."""
    rows = []
    changed = ('engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h', 'engine/src/animation_machine_stage_event.cpp')
    for path in sorted((Path(MAIN_ROOT) / 'tools').glob('verify_animation_machine*.py')) + [ROOT / 'tools/verify_animation_machine_stage_event.py']:
        if path.name == 'verify_animation_machine_stage_event_ops.py':
            continue
        pins = dict(re.findall(r"'(engine/src/[\w./]+)'\s*:\s*'([0-9a-f]{64})'", path.read_text()))
        hit = sorted(n for n in pins if n in changed)
        if hit:
            rows.append(dict(file='tools/' + path.name, pinned_changed_files=hit))
    return rows





# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve().name == 'animation_machine_stage_event_ops_execution'
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    RUN_DIR = Path(tempfile.mkdtemp(prefix='stage_event_ops_verify_'))
    try:
        run(OUT / 'verification.json')
    finally:
        for srv in SERVERS:
            srv.close()
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ['tools/verify_animation_machine_stage_event_ops.py', 'tools/observe_animation_machine_stage_event_ops.py', 'tools/observe_animation_machine_stage_event.py',
                 'tools/observe_animation_machine_scheduler.py', 'docs/analysis/animation-machine-stage-event-f3-contract.md', 'engine/tests/animation_machine_stage_event_ops_test.cpp'] + list(CPP_PINS):
        inputs[name] = cc.digest(ROOT / name)
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
    ctx.preserve = set(st['preserving'])
    ctx.probed_done = set()
    ctx.need_probe = set()
    # the native split stops at the first arrival of every F3b block start, every black box entry outside the unit (the callee executors) and the F3a block after BSR e94fe (e91b0)
    ctx.black_box_entries = sorted(int(x, 16) for x in report['static_checks']['black_box_entries'])
    ctx.checkpoint_set = set(st['starts']) | set(ctx.black_box_entries) | {RET_F3A}
    # every native blob is content addressed: hash all of them once
    blob_dir = NATIVE_DIR / 'blobs'
    blob_names = sorted(os.listdir(blob_dir))
    assert len(blob_names) == report['blobs'] == 1383
    for name in blob_names:
        assert sha((blob_dir / name).read_bytes()) == name.split('.')[0], name
    rows = [dict(r) for r in report['conditions']]
    first = [r for r in rows if r['number'] == 0][0]
    base_cond = load_condition(first)['result']
    bram, bpvc, bbank, bstate, _ = initial_state(base_cond, None)
    base_cond_changed_ram, _ = apply_changes(bram, bstate, base_cond['steps'][0]['declared_changes'])
    base = (base_cond_changed_ram, dict(bstate, carry=2), bpvc, bbank)
    equivalence = harness_equivalence(ctx, base, [])
    sel = rows
    if DEBUG_LABELS:
        sel = [r for r in rows if r['label'] in DEBUG_LABELS or r['group'] in DEBUG_LABELS]
    elif API_ONLY:
        sel = []
    typed = run_parallel(lambda r: guarded_typed(ctx, r), sel)
    failures = [(r['label'], a['error']) for r, a in zip(sel, typed) if 'error' in a]
    if failures:
        for label, text in failures[:60]:
            print('CONDITION FAILED', label, text.strip().splitlines()[-1][:600])
        print(failures[0][1])
        raise AssertionError('%d conditions failed' % len(failures))
    totals, carry_stops, guards, deliberate, out_rows, probes, starts_seen, problems = collections.Counter(), collections.Counter(), [], [], [], {}, set(), []
    typed_by_label = {}
    for r, a in zip(sel, typed):
        totals.update(a['totals'])
        carry_stops.update(a['carry_stops'])
        starts_seen |= a['starts_seen']
        problems.extend(a['failures'])
        out_rows.append(a['out_row'])
        typed_by_label[r['label']] = dict(guard=a['guard'])
        if a['guard']:
            guards.append(a['guard'])
        if a['deliberate']:
            deliberate.append(a['deliberate'])
        for pc, slots in a['probes'].items():
            slot = probes.setdefault(pc, {1: True, 2: True})
            for k in (1, 2):
                slot[k] = slot[k] and slots[k]
    for p in problems:
        print('PROBLEM', p)
    assert not problems, problems[:10]
    # ---- natural nodes
    nat_totals, nat_rows, nat_carry_stops, nat_starts, nat_targets = collections.Counter(), [], collections.Counter(), set(), collections.Counter()
    if NATURAL_SEEDS or not (DEBUG_LABELS or API_ONLY or NO_NATURAL):
        ctx.probed_done = set(probes)
        ctx.need_probe = set(st['starts']) - set(probes) - set(CONSUMERS)
        nat_json = json.loads(gzip.decompress((NATIVE_DIR / 'natural_nodes.json.gz').read_bytes()))
        assert sha((NATIVE_DIR / 'natural_nodes.json.gz').read_bytes()) == report['natural']['file_sha256']
        NAT['rows'] = {(r['case'], r['frame'], r['seq']): r for r in nat_json['rows']}
        assert len(NAT['rows']) == 471
        recs = json.loads(gzip.decompress((SEED_DIR / 'f3_node_seeds.json.gz').read_bytes()))['records']
        NAT['recs'] = {(r['case'], r['frame'], r['seq']): r for r in recs if r['cb'] in CALLBACKS}
        NAT['seed_cases'] = sorted(set(r['case'] for r in nat_json['rows']))
        NAT['seed_scope'] = {r['case']: r for r in json.loads((SEED_DIR / 'observation.json').read_text())['seeds']}
        NAT['ctx'] = ctx
        import observe_animation_machine_scheduler as sched
        # The scheduler observer parses the routing source of engine/src/animation_machine.cpp only for its rA / rB coverage flags (executor levels); it cannot parse the F3b `!stage_event_ops_trap(...)` atom.
        # The seed state generator is given the routing source without the F3b `else if` rule (a derived copy in the scratch run directory; nothing is edited); the flags do not choose the replay frame scope (pinned below).
        src = (ROOT / 'engine/src/animation_machine.cpp').read_text()
        lo = src.index('            else if (((next.pc>=0x288c')
        hi = src.index('ok=animation_stage_event_ops_block(c);\n', lo) + len('ok=animation_stage_event_ops_block(c);\n')
        derived = RUN_DIR / 'animation_machine_routing_without_f3b.cpp'
        derived.write_text(src[:lo] + src[hi:])
        sched.ROUTING_SRC = derived
        sched.setup()
        sched.load_seeds()
        naturals = sorted(c for c in sched.SEEDS if sched.SEEDS[c]['kind'] == 'natural')
        assert len(naturals) == 137 and set(NAT['seed_cases']) <= set(naturals) and len(NAT['seed_cases']) == 95
        naturals = NAT['seed_cases']
        if NATURAL_SEEDS:
            naturals = NATURAL_SEEDS
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
        for r in results:
            nat_totals.update(r['totals'])
            nat_rows.append(r['out_row'])
            nat_carry_stops.update(r['carry_stops'])
            nat_starts |= set(r['starts_seen'])
            nat_targets.update(r['split_targets'])
            for pc, slots in r['probes'].items():
                slot = probes.setdefault(pc, {1: True, 2: True})
                for k in (1, 2):
                    slot[k] = slot[k] and slots[k]
        if not NATURAL_SEEDS:
            assert nat_totals['nodes'] == 471 and nat_totals['entry_digest_equal_recorded'] == 471 and nat_totals['exit_digest_equal_recorded'] == 471
            assert nat_totals['dumped_nodes_byte_equal'] == 471 and nat_totals['self_delete_nodes'] == 6 and nat_totals['ordered_port_digest_equal_recorded'] == 471
            for cb, n in report['natural']['by_callback'].items():
                assert nat_totals['cb_%x' % int(cb, 16)] == n, cb
    preserve = set(st['preserving'])
    observed_preserving = sorted(pc for pc, slots in probes.items() if slots[1] and slots[2])
    if not (DEBUG_LABELS or API_ONLY):
        assert starts_seen | nat_starts >= set(st['starts']), sorted(hex(p) for p in set(st['starts']) - starts_seen - nat_starts)
        assert set(observed_preserving) == preserve - set(CONSUMERS) and set(probes) >= set(st['starts']) - set(CONSUMERS), \
            (sorted(hex(p) for p in set(st['starts']) - set(probes) - set(CONSUMERS)), sorted(hex(p) for p in set(observed_preserving) ^ (preserve - set(CONSUMERS))))
        for pc in CONSUMERS:
            for known in ('Clear', 'Set'):
                assert totals['consumer_flip_%x_incoming_%s' % (pc, known)] + nat_totals['consumer_flip_%x_incoming_%s' % (pc, known)] > 0, (hex(pc), known)
        assert len(out_rows) == 284 and totals['conditions'] + totals['guard_conditions'] + totals['deliberate_failure_conditions'] == 284
    # ---- guard/native consistency
    if not (DEBUG_LABELS or API_ONLY):
        native_guards = {g['label']: g for g in report['guards']}
        assert sorted(g['label'] for g in guards) == sorted(native_guards) and len(guards) == 38
        for g in guards:
            assert native_guards[g['label']]['problem'] == g['native_problem'], g['label']
        kinds = collections.Counter(g['native_problem'] for g in guards)
        assert dict(kinds) == {'unsupported_TRAP': 9, 'unmapped_or_protected': 7, 'unsupported_odd_data_access': 7, 'rng_pointer_outside_ram': 6, 'step_limit': 5, 'unsupported_code_target': 2,
                               'rng_pointer_high_byte': 1, 'unsupported_data_device': 1}, dict(kinds)
    negative, consumer_controls, neighbours = negatives(ctx, base, st)
    zero_pcs = list(st['starts']) + list(st['traps'])
    zero = run_parallel(zero_step_one, [(ctx, base, pc, carry) for pc in zero_pcs for carry in (0, 1, 2)])
    cases, cpp_carry, cpp_ranges, cpp_traps = cpp_static(st)
    assert cases == set(st['starts']), sorted(hex(p) for p in cases ^ set(st['starts']))
    assert cpp_ranges == sorted(F3B_RANGES), cpp_ranges
    assert cpp_carry == preserve, sorted(hex(p) for p in cpp_carry ^ preserve)
    assert cpp_traps == sorted(TRAP_SITES)
    for name, expected in inputs.items():
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs = dict(refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log', OUT / 'harness_batch.cpp', OUT / 'compile_batch.log'):
        refs[str(path.resolve())] = cc.digest(path)
    probe_map = entry_probe_map(report, negative, st, zero) if not (DEBUG_LABELS or API_ONLY) else []
    old = scan_old_expectations(st)
    old_checks = old_expectation_checks(ctx, base, st)
    pins_audit = pin_audit()
    by_kind = collections.OrderedDict()
    for g in sorted(guards, key=lambda x: (x['native_problem'], x['label'])):
        by_kind.setdefault(g['native_problem'], collections.Counter())[g['checked_API_error'] or '(accepted by the C++ executor, deliberate difference)'] += 1
    classes = collections.Counter(g['classification'] for g in guards)
    classes.update(g['classification'] for g in deliberate)
    result = dict(
        schema_version=1, source=source, inputs=inputs, artifacts=refs, changed_inputs_since_native_observation=report['_changed_inputs'],
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, f3a_tool_sha256=F3A_TOOL_SHA, scheduler_tool_sha256=SCHED_TOOL_SHA, contract_sha256=CONTRACT_SHA, cpp_pins=CPP_PINS,
        native_counts=dict(conditions=report['condition_count'], groups=report['group_counts'], natural_nodes=report['natural']['nodes'], natural_by_callback=report['natural']['by_callback'],
                           entry_probe_addresses=report['entry_probes']['addresses'], entry_probe_rows=report['entry_probes']['rows'], blobs=report['blobs'], guards=len(report['guards'])),
        native_blobs_hash_checked=len(blob_names), native_blobs_read_for_comparison=len(VERIFIED_BLOBS),
        block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']], interior_PC_count=len(st['interior']), odd_PC_count=len(st['odd_pcs']), trap_sites=[hex(p) for p in st['traps']],
        string_even_PC_count=len(st['string_even']), string_odd_PC_count=len(st['string_odd']), neighbour_pcs=[hex(p) for p in neighbours],
        bundled_branches=[hex(p) for p in st['bundled']], carry_preserving_blocks=[hex(p) for p in st['preserving']], carry_consumers=[hex(p) for p in CONSUMERS], known_carry_producer=hex(SET_PRODUCER),
        cpp_case_labels_equal_contract_block_starts=len(cases), cpp_routing_ranges_equal_8=True, cpp_trap_sites_equal_8=True, cpp_carry_preserving_table_in_unit_equals_48=True,
        observed_carry_preserving_blocks_through_cpp=[hex(p) for p in sorted(set(observed_preserving) | set(CONSUMERS))], carry_preserving_consumers_checked_by_flip_controls=[hex(p) for p in CONSUMERS],
        carry_probed_blocks={hex(pc): dict(incoming_Clear_preserved=bool(slots[1]), incoming_Set_preserved=bool(slots[2])) for pc, slots in sorted(probes.items())},
        typed_actual_CPP=dict(sorted(totals.items())), typed_conditions=out_rows, natural_actual_CPP=dict(sorted(nat_totals.items())), natural_seeds=nat_rows,
        carry_at_stops_typed={k: v for k, v in sorted(carry_stops.items())}, carry_at_stops_natural={k: v for k, v in sorted(nat_carry_stops.items())},
        native_guards_checked_API=guards, native_guard_count=len(guards), guard_kind_to_cpp_error={k: dict(sorted(v.items())) for k, v in by_kind.items()},
        deliberate_failure_conditions=deliberate, difference_classification_counts=dict(sorted(classes.items())),
        entry_probe_map=probe_map, typed_final_pc_counts=dict(sorted(collections.Counter(r['final_pc'] for r in out_rows if r.get('final_pc')).items())),
        block_starts_seen_by_typed=sorted(hex(p) for p in starts_seen), block_starts_in_natural_lead_sets=sorted(hex(p) for p in nat_starts),
        block_starts_only_typed_fixture=sorted(hex(p) for p in set(st['starts']) - nat_starts) if nat_starts else [],
        negatives=negative, negative_count=len(negative), consumer_controls=consumer_controls, zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_trap_sites=len(st['traps']),
        zero_step_carries=[0, 1, 2], harness_equivalence_cases=equivalence, invalidated_expectation_candidates=old, old_expectation_checks=old_checks, old_verifier_pin_audit=pins_audit,
        carry_check='C is a block classification (native SR is never read): the two consumers e936e (288c / 289e / 2898) and e9576 (2986) take a Known C produced inside the run (checked against the native '
                    'executed branch path of the trace), flip controls select the other destination, Unknown at a consumer gives the exact error; single-block probes with incoming C 1 / 2 '
                    'on every F3b start observed in a traced condition reproduce the 48 FLOW_ONLY blocks (2898 produces a Known Set in the block)',
        compile_command=command, compile_batch_command=scommand, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (declared node entry states of the scheduler observer DECLARED frame pass model, typed fixtures on recorded dump states), not natural scheduler, IRQ or gameplay reachability; '
                'the scheduler observer is imported only to regenerate the natural node entry states (each regenerated entry digest must equal the recorded one before the C++ run).',
                'Native SR is not observed; the initial SR is a declared fixture value (2000 / 2001 only for the direct consumer entries).',
                'Existing executors (cleanup 43e08/43e22/43e34, fade_card 28ae/2a00, buffer_cue 2986, input 289e, stage area 49a58, F3a blocks) are compared as whole results; their interior is not modelled here.',
                'Checked failures preserve API outputs, not original CPU fault rollback; deliberate differences are listed with counts.',
                'No BIOS execution, no natural scheduler, no natural IRQ is claimed.'])
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(typed_conditions=len(out_rows), typed_phases=totals['phases_equal_native'], guard_conditions=totals['guard_conditions'], deliberate_failures=len(deliberate), natural_nodes=nat_totals['nodes'],
                          negatives=len(negative), zero_step=len(zero), guards=len(guards), sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
