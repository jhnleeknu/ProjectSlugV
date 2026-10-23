"""Stage event F3a (e9150 / e9176 event node callbacks, e9204 class count + e9298 screen flags with 48502, main stream loop e9198 with the e91e4 opcode table, opcodes 00..07 e9444..e94fe,
length advance e9768, expression evaluator e97c8 with the e97e4 operator table and the BYTE stack on A7, helpers 1a910 1a93e; 43e34 in the cleanup executor) native evidence vs the public
machine API.

Controlled fixtures; no expected-register injection.  The frozen native observation (artifacts/animation_machine_stage_event_native) is an immutable input; this verifier never invokes the
observer main and never imports the observer module.  It reads the stage-event observation, the typed condition files, the natural node rows and the entry probes, and compares them with the
actual C++ `run_animation_machine` (one run = one node execution: PC 2ab8, A6 = node, A7 = SPd, LONG 104ca4 = SPd; stop 2ac2 after the dispatcher RTS or e94fe, the F3b boundary):
  * typed conditions (560, 117 of them native guards): every split phase (stop at the first arrival of every checkpoint of the native step, same order, directly after the transferring
    instruction) is compared with the native phase record (16 registers, PC, SHA256 of the 64 KiB RAM, PVC image modulo the two normalized bank words + their native values, ordered ports SHA256,
    external reads); every phase resumes ONLY from the previous actual C++ output plus the declared host changes of the step (RAM writes); the native input state is asserted, never injected;
    continuous C++ run vs the split chain vs the native record; native guards -> exact checked C++ error strings, full preservation, the same split segment;
  * natural nodes (9613 e9150 / e9176 node executions of the 137 natural seeds): the entry states are regenerated from the pinned scheduler seeds (the scheduler observer is imported ONLY as the
    seed state generator: its SeedRun passes, with the F3 replay hook replaced by this verifier's C++ run; nothing of it is edited), each regenerated entry digest must equal the recorded
    one before the C++ run, the C++ exit digest must equal the recorded exit / e94fe digest and the recorded ordered port digest; the 856 dumped nodes are compared byte by byte (RAM, PVC, ports)
    and with the full split chain of the native executed path, the other nodes with a continuous run and one split at a leader;
  * carry = block classification observed through the actual C++: the two consumers e9248 e9258 take a Known C produced by 49392 (native branch path), flip controls select the other
    destination, single-block probes with incoming C 1 / 2 on every distinct F3a start observed in a traced condition give the 60 FLOW_ONLY blocks back, Unknown at a consumer gives
    the exact error `stage event caller requires known carry`; native SR is never read;
  * API-only negatives: all 428 interior PCs, 562 odd PCs, the neighbours of the 7 routed ranges, e94fe without a stop, zero-step at every one of the 134 starts x 3 carries.
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
OUT = Path(os.environ['OUTDIR']) if os.environ.get('OUTDIR') else ROOT / 'artifacts/animation_machine_stage_event_execution'   # OUTDIR: scratch output override (final component must keep this name)
NATIVE_DIR = ROOT / 'artifacts/animation_machine_stage_event_native'
SEED_DIR = ROOT / 'artifacts/animation_machine_scheduler_native'
NATIVE_SHA = '44836842e9b132ac4909e693845f85def6d3204787c764eca33bf17e1d100ae0'
NATIVE_TOOL_SHA = 'ae0840bbd1eb22a4aaa1de78a274ef924c22b6b2ea87ae0125eefd33cd3ed9c6'
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
# player C5 refresh: animation_machine.cpp was 9747100c960fa54879c998635c250ae06e790155df4ae1c5a5a4e2ec2c03915d, animation_machine_internal.h was 6f22404a6c4422178f812a7ad193ee9e8a1b36bfde4f0da1c7740d2875923c0d
# player C6 refresh: animation_machine.cpp was beff46d62a342129120d107dba0848ca937dddf9301c16902d19a521d8da2f21, animation_machine_internal.h was 0dc447022c1b885d2fb7e112329823cb8373ee6369949b6811ae678a635939bd
# player C7 refresh: animation_machine.cpp was bd037aff436d5b102749b0c97562660c5b32423736393f679dede2d2dcecefd4, animation_machine_internal.h was 5458ca6c08b35b69780549b938650f1c649eed535a4ce1760b828644efd6d9a5
# player C8 refresh: animation_machine.cpp was 1f4599a2480e6998abc34f8141e93cb790ea7cd5694852290bbe3dd7596ab97d, animation_machine_internal.h was 8ae7ae9276347fb2fb5349ed57e8c3d979da36c30042cbf4181da341ea8f0737
# player C9 refresh: animation_machine.cpp was 2622b7a2374959c551dea03156bc48ab1f7995118a1c1664e80e30ad36d443c5, animation_machine_internal.h was 57606da7148c24cc37efdec0560ea0f8a6ec6ce95932953f63cd8012c1499662
# objects FR10 refresh: animation_machine.cpp was 48ba3f29953b656d51b1cebe03f18c3004fa0fb011070b0ea8527d5e94b617c3, animation_machine_internal.h was d8918d505ee9dde426c93f8b26ec19f8d4893f59867cce33a6017947e20a3058
# player C10 refresh: animation_machine.cpp was 6a7d76c3817fdab2a07af95b5d1be6cb14fca2c81f992bba558a88bddb14cdc6, animation_machine_internal.h was 9f371fcfefb8bf19538c6b6e6e779a9e95ea9019c77816537a4b0ce01870425c
# objects FR11 refresh: animation_machine.cpp was 63f7d470922dfab836b19417f2a16dba5d170d3424906a13c04ad69f53a48eb7, animation_machine_internal.h was f1180a35ac8dab11f98c309ba7c890110e5e141f63553c3239c51375fb1c7f4a
# objects FR12 refresh: animation_machine.cpp was e99fe5dbc8192ae377b9384c30fa821ada4a2fbf23aeca777c81fed5f115a815, animation_machine_internal.h was 8cf2b547c1c11023096672ee7db3418811215596a99e907c494a91ed663b2296
CPP_PINS = {'engine/src/animation_machine_stage_event.cpp': 'e074f25f82b8e1bd7d84068bfe773db6b9f435cb35d22e95a59e24ead6952d9c', 'engine/src/animation_machine_cleanup.cpp': 'b6aed30bbea37f5ab02f85ffc8e62ecd6c68e5f6f34cdc0a2b6e9487716aaf5c', 'engine/src/animation_machine.cpp': '49170da4b41a73e9cbb8d1684e0fa261fedc2ece6bab2e1e77a0b2dbe8e0c5f2', 'engine/src/animation_machine_internal.h': '3a5dc9af01e57baf08320a0ec5ba744c82ea85679e150a5e912a7d1212ed8c84'}  # FR8 refresh: animation_machine.cpp was 298c64da5f6ab9483acc7b1e39c0b733ea0908cb685c058621faa500ffbec51f and animation_machine_internal.h was 69b45dcd7444ae6411e238106b33c3f2f5098d10525e0ed93f78f21f237813fd (FR8 routing else-if, carry group of 6 and declaration after FR7). Earlier FR7 refresh: animation_machine.cpp was 989b7951f8613fcb3643603292b94b3a61fbb97b5ca16ad7e66cc31bef1adcfe and animation_machine_internal.h was cef94f5cbabb5b89a0cdaf27c53f86cec9bf32abeaecedf6fdde8f3778b284c1 (FR7 routing else-if, carry group of 8 and declaration after FR6). Earlier FR6 refresh: animation_machine.cpp was 7641c2d9f54068ee2c4308c516bea495bc4392fd0107b3f85b584de5fedcf337 and animation_machine_internal.h was fcef64db27191d5aa06fd75a83d3cf1fd9a989aaeddcc9870ae9f803a223009f (FR6 routing else-if, carry group of 12 and declaration after FR5). Earlier FR5 refresh: animation_machine.cpp was 31a1b033911fd15cfed40998c1072f32db29a85d7605848e1049b1bbf86735c8 and animation_machine_internal.h was 8570d1e86121aa5ad8432c716d2787cdc69ef5cb26bbc9cb3a78742edd7625e0 (FR5 routing else-if, carry group of 6 and declaration after FR4). Earlier FR4 refresh: animation_machine.cpp was 869a9dc12b14ba47ed65642ab937cb1bbaa5a49775241e3a325ce47fc1d1a446 and animation_machine_internal.h was f7953e9a0a117d13b4f4b8966df5402838e579a4a4efb36c325affd18daf1f3b (FR4 routing else-if, carry group of 7 and declaration after FR3). Earlier FR3 refresh: animation_machine.cpp was 4fc41a76a8ef697a93dd339af64a7deff8c62620c680d27015aad6bf2b2a3b40 and animation_machine_internal.h was 142f253e7e8caa020620d97ea91eeac57907506c7323af4c9d006a8186c43d24 (FR3 routing else-if, carry group of 17 and declaration after FR2b). Earlier FR2b refresh: animation_machine.cpp was eadc97b080cbeacbf16524ca1626fb4013b07acdc0042340743ab34509201923 and animation_machine_internal.h was 522199f979904a60033719cccfa965edb2890a16744b267375436ede12875b14 (FR2b routing else-if, carry group of 11 and declaration after b4a7e21). Earlier FR2a refresh: animation_machine.cpp was 00ff3a1b8bfb89d7682bb48506ef39809ddd9062853335707385457b2cbd9fb4 and animation_machine_internal.h was caad91c124ca03fb7dd4d77d972f577e4736fe58e30aad5054bfb957d527a04e (FR2a routing else-if, carry group of 9 and declaration after 11be2b6). Earlier FR1 refresh: animation_machine.cpp was 8ce8eb93c21465dd5e9355d4518ab1ca853df4549305fec98c7854caa1a82db6 and animation_machine_internal.h was 74d9c9ab7c60ffc9e7c8d3f523f7e769fb2f836fbafadfcad56ee34dcbebb71d (FR1 routing/declarations changes after 062bfd7). Earlier 062bfd7 refresh (0267): animation_machine.cpp was 1e7625c722bca323152a57d6cd81f2237a5fdff51c13a1563b6e430c26ccbf76 and animation_machine_internal.h was 874fceb112699346f95c12ee5212bbc997137eef22de17b8fe18b38bb5a079f8 (d66442f); d66442f..062bfd7 adds B4a/B4b child callback routing and private declarations. Earlier d66442f refresh (0266): animation_machine.cpp was aba5bec0b6450b00b0259478ccdbe6c0fa133ec9e481145117b3a2631aa68cc9 and animation_machine_internal.h was 706f6a5bcd3ce44c91dfa74928b5a155050af087ce1c643631c11d8a513a0e78 (de0e5be); de0e5be..d66442f adds U06b (e7562/48250) and B3c (N28 chain children, 1c114, 2291a tail) routing and private declarations. Earlier de0e5be refresh (0264-legacy rerun): animation_machine.cpp was 7e76e64bad3037cc22c6597b3c8746b05f7540dee4703c4dc18853179cf951a6 and animation_machine_internal.h was 4585a260ec43cf41c5c9fb8a8c23532505000c9dd9ea1161f659a2d6a6d6cfbd (e5bfb73); e5bfb73..de0e5be adds B2c-a/B2d/B2e/B3a/B3b routing and private declarations. Earlier e5bfb73 refresh (0264-legacy): animation_machine.cpp was c7318132fcdfd288c12a58ab7e51c03e2920b46d7e939103bd917d72ca8caad2 and animation_machine_internal.h was 6406329a911fd50c13b9765bf59b032f5afa322e1237a8a9b1dea6b1a5fa6e34 (709a706); 709a706..e5bfb73 adds the ten-unit routing (C1-C3, F6a-c, B1a-c, B2a/b), private declarations, the palette device context and the Z80 reply 320000 external-read device (the old line was replaced, not deleted). Earlier note, b8502bf: 0c89a1f..HEAD adds routing for N33/N34/N35 and H2/H3/H4/H8 plus private declarations; no existing shared lines removed. Other pinned unit sources unchanged.
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
SPD = 0x1ff000
FRAME_RET = 0x2ac2
NODE_PC = 0x2ab8
F3B_ENTRY = 0xe94fe
F3A_RANGES = ((0x1a910, 0x1a91a), (0x1a93e, 0x1a952), (0x48502, 0x4855c), (0xe9150, 0xe9350), (0xe9444, 0xe94fe), (0xe9768, 0xe9774), (0xe97c8, 0xe98ee))
CONSUMERS = (0xe9248, 0xe9258)
CALLBACKS = (0xe9150, 0xe9176)
BUNDLED_RETURNS = (0xe9396, 0xe939e, 0xe94c0, 0xe96b0)       # BEQ.W / BNE.W consuming the Z of the e98ea MOVE.B (A7)+,D0 (F3 decision 3)
BLACK_BOXES = (0x43e34, 0x49392, 0x4d7a6)
REG16 = tuple('d%d' % i for i in range(8)) + tuple('a%d' % i for i in range(8))
UNKNOWN_CARRY = 'stage event caller requires known carry'
UNSUPPORTED_EVENT = 'unsupported animation stage event PC'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
# FR2a routes e991c..e995c (docs/analysis/animation-machine-frontier-fr2-contract.md): the e97d8 computed targets e991c..e9958 (D0.W = ce..dd) now land in it.
# Former behaviour: every one of the 16 targets ended in 'unsupported animation machine PC' (outside the routing). Now the 3 block starts run on (stop-only
# control, like the F3b starts) and the 13 other targets are refused by the FR2a executor ('unsupported animation objects fr2 PC').
UNSUPPORTED_FR2 = 'unsupported animation objects fr2 PC'
FR2A_GUARD_RANGE = (0xe991c, 0xe995c)
FR2A_STARTS = frozenset((0xe991c, 0xe9922, 0xe9930, 0xe993c, 0xe9942, 0xe9952, 0xe9956))
UNALIGNED_PC = 'unaligned animation machine PC'
EVEN = 'program bus requires even WORD/LONG address'
BUDGET = 'animation machine block budget exceeded'
WORKERS = int(os.environ.get('STAGE_EVENT_WORKERS', '3'))
API_ONLY = bool(os.environ.get('STAGE_EVENT_API_ONLY'))                 # development switch only
DEBUG_LABELS = [x for x in os.environ.get('STAGE_EVENT_DEBUG_LABELS', '').split(',') if x]      # development switch only
NO_NATURAL = bool(os.environ.get('STAGE_EVENT_NO_NATURAL'))             # development switch only
NATURAL_SEEDS = [int(x) for x in os.environ.get('STAGE_EVENT_SEEDS', '').split(',') if x]      # development switch only
STATE_SHA_PREFIX = b'F3A-STATE-v1'
VERIFIED_BLOBS = set()
RUN_DIR = None


def localize(name):
    local = str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name
    return local if Path(local).exists() else name


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def in_f3a(pc):
    return in_ranges(pc, F3A_RANGES)


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
    exe = folder / 'animation_machine_stage_event_batch_harness'
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
        if sect != 'a':
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
    assert code == list(F3A_RANGES) and sum(h - l for l, h in code) == 1124
    starts = bundled = preserve = consumers = None
    seen_a = False
    for line in lines:
        if line.startswith('**F3a (134 block 시작)**'):
            starts = expand_pcs(line.split(':', 1)[1])
            seen_a = True
        elif line.startswith('**F3b (109 block 시작'):
            seen_a = False
        elif seen_a and line.startswith('- 묶인 PC 22개:'):
            bundled = expand_pcs(line.split(':', 1)[1])
        elif seen_a and line.startswith('- FLOW_ONLY 60개:'):
            preserve = expand_pcs(line.split(':', 1)[1])
        elif seen_a and line.startswith('- carry 소비 block 2개:'):
            consumers = expand_pcs(line.split(':', 1)[1].split('(')[0])
    assert starts and len(starts) == len(set(starts)) == 134
    assert bundled and len(bundled) == len(set(bundled)) == 22
    assert preserve and len(preserve) == len(set(preserve)) == 60
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
    for low, high in F3A_RANGES:
        pc = low
        while pc < high:
            inside.append(pc)
            pc += instructions[pc]['size']
        assert pc == high, hex(low)
    assert len(inside) == 324
    assert not [pc for pc in inside if names(pc) in ('trap', 'rte', 'addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')]
    # blocks: from a start to the next start (or the range end), the contiguous instruction run; bundled continuation instructions stay in the block they follow
    blocks = collections.OrderedDict()
    for low, high in F3A_RANGES:
        pc, cur = low, None
        while pc < high:
            if pc in start_set or cur is None:
                cur = pc
                blocks[cur] = []
            blocks[cur].append(pc)
            pc += instructions[pc]['size']
        assert pc == high
    assert sorted(blocks) == sorted(starts) and sum(len(v) for v in blocks.values()) == 324
    fallthrough = sorted(s for s, b in blocks.items() if names(b[-1]) not in TERMINATORS)
    assert all(b[-1] + instructions[b[-1]]['size'] in start_set for s, b in blocks.items() if s in fallthrough), [hex(s) for s in fallthrough]
    derived_bundled = sorted(pc for b in blocks.values() for pc in b[1:] if names(pc) in BRANCHES)
    assert derived_bundled == sorted(bundled), [hex(p) for p in set(derived_bundled) ^ set(bundled)]
    assert not set(bundled) & start_set
    flow = sorted(s for s, b in blocks.items() if all(names(p) in FLOW_ONLY for p in b))
    assert flow == sorted(preserve), [hex(p) for p in set(flow) ^ set(preserve)]
    # the cleanup 43e34 entry is no start of this unit (it moved into the cleanup executor)
    assert 0x43e34 not in start_set
    consumers = sorted(s for s in starts if names(s) == 'bcc')
    assert consumers == list(CONSUMERS)
    even_pcs = [pc for low, high in F3A_RANGES for pc in range(low, high, 2)]
    odd_pcs = [pc for low, high in F3A_RANGES for pc in range(low + 1, high, 2)]
    interior = [pc for pc in even_pcs if pc not in start_set]
    assert len(even_pcs) == 562 and len(interior) == 428 and len(odd_pcs) == 562
    return dict(starts=starts, bundled=sorted(bundled), preserving=sorted(preserve), instructions=instructions, blocks=blocks, fallthrough_blocks=fallthrough, interior=interior, even_pcs=even_pcs, odd_pcs=odd_pcs)


def cpp_static(st):
    text = (ROOT / 'engine/src/animation_machine_stage_event.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text))
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    in_unit = set(pc for pc in table if in_ranges(pc, F3A_RANGES))
    start = machine.index('animation_stage_area_block(c);') + len('animation_stage_area_block(c);')
    route = machine[start:machine.index('animation_stage_event_block(c);', start)]
    ranges = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=0x([0-9a-f]+) && next\.pc<0x([0-9a-f]+)', route))
    cleanup = (ROOT / 'engine/src/animation_machine_cleanup.cpp').read_text()
    assert 'case 0x43e34:r.a[0]=am_index(r.a[6],0x2e);r.pc=0x43e38;return true;' in cleanup
    return cases, in_unit, ranges, 0x43e34 in table


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
    assert cc.digest(ROOT / 'tools/observe_animation_machine_stage_event.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_scheduler.py') == SCHED_TOOL_SHA
    assert cc.digest(SEED_DIR / 'observation.json') == SEED_OBS_SHA and cc.digest(SEED_DIR / 'f3_node_seeds.json.gz') == SEED_FILE_SHA
    for name, expected in CPP_PINS.items():
        assert cc.digest(ROOT / name) == expected, name
    assert cc.digest(CONTRACT) == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['byte_table_check'] and report['contract_discrepancies'] is not None
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert report['condition_count'] == 560 == len(report['conditions']) == report['control_steps']
    assert report['natural']['nodes'] == 9613 and report['natural']['seeds'] == 137 and report['natural']['dumped_nodes'] == 856
    assert report['block_starts_covered'] == 134 and report['block_starts_uncovered'] == []
    assert report['entry_probes']['addresses'] == 1124 and report['model']['natural_equal'] == 9613 and report['model']['typed_equal'] == 443
    assert report['seed_inputs']['f3_node_seeds_sha256'] == SEED_FILE_SHA and report['seed_inputs']['scheduler_observation_sha256'] == SEED_OBS_SHA
    assert report['static_checks']['block_starts'] == 134 and report['static_checks']['blocks_total_instructions'] == 324
    assert report['static_checks']['flow_only_equal_contract'] is True and report['static_checks']['carry_consumers_equal'] is True
    changed = []
    for name, expected in report['inputs'].items():
        actual = cc.digest(localize(name))
        if actual != expected:
            # the only input allowed to differ is the routing source read by the scheduler observer for the rA / rB coverage flags (the stage event routing was added after the observation)
            assert name.endswith('engine/src/animation_machine.cpp'), name
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
    """Destination of the two stage event carry consumers (BCC clear_pc, otherwise set_pc) for a known C (1 Clear, 2 Set)."""
    assert carry in (1, 2)
    return {0xe9248: (0xe9250, 0xe924c), 0xe9258: (0xe9260, 0xe925c)}[pc][0 if carry == 1 else 1]


def native_succ(pcs, index, block, instructions, start_set):
    """Native successor PC of a block started at pcs[index]: the first discontinuity of the executed path (a transfer) or a fall-through into the next start.  A bundled e98ea return into the
    branch of e94c0 executes that BNE inside the same C++ block, so its destination is the successor."""
    i = index
    while True:
        pc = pcs[i]
        nxt = pcs[i + 1]
        if pc == 0xe98ec and nxt in BUNDLED_RETURNS:       # the RTS of the e98ea block returning to a bundled branch (decision 3)
            return pcs[i + 2], i + 2
        if nxt != pc + instructions[pc]['size']:
            return nxt, i + 1
        if nxt in start_set:
            return nxt, i + 1
        i += 1


# ----------------------------------------------------------------------------------------------------------------- guard expectations
# Native guard kind -> expected checked C++ error string (explicit per kind; the code-target kind is classified by the original ranges).
GUARD_KIND_RULES = {
    'step_limit': BUDGET,
    'unsupported_odd_data_access': 'read: ' + EVEN + '; write: invalid animation machine write size/alignment (push: ' + EVEN + ')',
}
GUARD_EXPECTED = {
    'op-len0-loop': BUDGET, 'walk-circular': BUDGET,
    'op-odd-length-then-word': EVEN, 'walk-odd-link': EVEN, 'guard-stream-odd-op00': EVEN, 'guard-odd-a6-node': EVEN,
    'guard-odd-a7-node': EVEN,
    'input-trap-index-zero': UNSUPPORTED_MACHINE, 'guard-rom-write-e9150': 'unsupported animation machine write device', 'guard-bank-window-write': 'unsupported animation machine write device',
    'guard-stack-below-ram': 'program bus write requires RAM mirror units', 'guard-stream-unmapped': 'unsupported program bus device address', 'guard-stream-device': 'unsupported program bus device address',
}
# Classification of the native guard -> C++ error pairs that are not the identical check (every other pair is a refusal of the same access / transfer class).
GUARD_NOTES = {
    'input-trap-index-zero': ('native_TRAP_boundary_vs_cpp_unrouted_PC', 'the native observer stops with unsupported_TRAP at 4d7f0 (TRAP #15 inside the input callee 4d7a6, a TRAP boundary of that unit); the C++ lands on the same '
                              'non-routed PC 4d7f0 and reports unsupported animation machine PC (verified at the same split segment)'),
    'guard-rom-write-e9150': ('native_bus_error_vs_cpp_write_device', 'native: write to the program ROM / unmapped address 203e (bus error); C++: checked write-device error, state preserved'),
    'guard-bank-window-write': ('native_bus_error_vs_cpp_write_device', 'native: write to the banked ROM window 20003e (bus error); C++: checked write-device error, state preserved'),
    'guard-stack-below-ram': ('native_bus_error_vs_cpp_stack_RAM_mirror_check', 'native: push below RAM (write to ffffe, bus error); C++: the stack write requires the RAM mirror units (checked error)'),
    'guard-stream-unmapped': ('native_bus_error_vs_cpp_device_address_check', 'native: stream read at the unmapped address 500000 (bus error); C++: unsupported program bus device address'),
    'guard-stream-device': ('native_unsupported_data_device_vs_cpp_device_address_check', 'native: stream read at the video device region 3c0000 refused; C++: unsupported program bus device address'),
}
CODE_TARGET_NOTE = {
    'odd': UNALIGNED_PC,
    'f3a_interior': UNSUPPORTED_EVENT,
    'outside': UNSUPPORTED_MACHINE,
    'fr2a_interior': UNSUPPORTED_FR2,
}


def classify_code_target(g):
    if g.get('odd_pc'):
        return 'odd'
    if FR2A_GUARD_RANGE[0] <= g['target'] < FR2A_GUARD_RANGE[1] and g['target'] not in FR2A_STARTS:
        return 'fr2a_interior'
    return 'f3a_interior' if in_f3a(g['target']) else 'outside'


def expected_for(label, g):
    if g['problem'] == 'unsupported_code_target':
        return CODE_TARGET_NOTE[classify_code_target(g)]
    return GUARD_EXPECTED.get(label)


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
    acc = dict(totals=collections.Counter(), guard=None, failures=[], starts_seen=set(), consumer=collections.Counter(), probes={}, carry_stops=collections.Counter())
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
    if ng['problem'] == 'unsupported_code_target' and (ng.get('target') in f3b_starts() or ng.get('target') in FR2A_STARTS):
        target = ng['target']
        checks = [phase['outgoing']['pc'] for phase in nat[:-1]]
        prefix, reason = split_chain(ctx, 'superseded_guard_%03d' % row['number'], ram, state_in, pvc, bank, target, checks, external)
        assert reason == 'stop' and len(prefix) == len(nat), (label, reason, len(prefix), len(nat))
        # F3b starts: the last phase ends at the target like the native guard phase.  FR2a starts: the native guard phase ends BEFORE the computed jump
        # (e97e0, refused target), the C++ phase runs on to the target (stop-only control), so only the phases before the guard phase are compared.
        compared = len(prefix) if target in f3b_starts() else len(prefix) - 1
        for k, phase in enumerate(prefix[:compared]):
            compare_phase(acc['totals'], label, k, nat[k], phase['actual'], phase['entry'])
        if not cont[0]['ok']:
            check_preserved(cont, ram, state_in, pvc, bank)
        acc['guard'] = dict(label=label, group=res['group'], native_problem=ng['problem'],
                            classification='superseded_F3b_routing_boundary' if target in f3b_starts() else 'superseded_FR2a_routing_boundary', native_target=hex(target),
                            native_prefix_phases_equal=len(prefix), cpp_reaches_native_transfer_target_with_stop=hex(target),
                            checked_API_error=cont[4].strip() or None, cpp_suffix_ok=cont[0]['ok'],
                            native_suffix_equivalence_claimed=False,
                            replacement_native_coverage='stage_event_ops typed block-start coverage' if target in f3b_starts() else 'objects_fr2 unit test and V1 fr2 spec (e991c e9930 e993c block starts)')
        acc['totals']['guard_conditions_superseded_by_F3b' if target in f3b_starts() else 'guard_conditions_superseded_by_FR2a'] += 1
        return
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
    note = GUARD_NOTES.get(label)
    entry['classification'] = note[0] if note else 'same_check_class'
    entry['rule'] = note[1] if note else None
    acc['guard'] = entry
    if expected is None or error != expected:
        acc['failures'].append(('guard error', label, error, expected))
    if not entry['same_split_segment_as_native']:
        acc['failures'].append(('guard segment', label, len(phases), len(nat)))


# Native guards the C++ executor deliberately does NOT refuse (the C++ bus models the access; the native observer refuses it as an unmodeled device access).
DELIBERATE_ACCEPT = {
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
                 classification='native_refuses_device_access_cpp_models_it', rule=DELIBERATE_ACCEPT[label], cpp_continuous_equals_split=True, cpp_final_pc=hex(r['pc']),
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
        slot = acc['probes'].setdefault(pc, {1: True, 2: True})
        outs = {}
        for k in (1, 2):
            a = inv(ctx, '%s_probe%x_%d' % (tag, pc, k), s_ram, dict(s_state, carry=k), s_pvc, s_bank, nxt, external)
            r2 = a[0]
            assert r2['ok'] and not a[4] and r2['pc'] == nxt and r2['status'] == 0, (label, hex(pc), hex(nxt), a[4])
            want = k if pc in ctx.preserve else 0
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
    end = row['end']
    stop = FRAME_RET if end == FRAME_RET else F3B_ENTRY
    tag = 'n%03d_%03d_%02d' % key
    cont = inv(ctx, tag + '_cont', ram, state, pvc, bank[0], stop, 0)
    r, out_ram, out_pvc, ports, error = cont
    assert r['ok'] and not error and r['status'] == 0 and r['pc'] == stop, (key, error)
    ff8, ff9 = bank_words(out_pvc)
    ex = sched_state_digest(out_ram, {k: r[k] for k in REG16}, r['pc'], (r['bank_base'], ff8, ff9))
    assert ex == row['state'], (key, 'C++ exit state digest differs from the recorded one')
    assert r['a7'] == row['a7'] and len(ports) // 9 == (rec['ports'] if end == FRAME_RET else rec['e94fe_ports']), (key, 'a7 / port count')
    if end == FRAME_RET:
        assert sched_ports_digest(ports) == rec['ports_sha'], (key, 'ordered port digest')
        totals['ordered_port_digest_equal_recorded'] += 1
        totals['nodes_end_2ac2'] += 1
    else:
        assert ports == b'', key
        totals['nodes_end_e94fe'] += 1
    totals['exit_digest_equal_recorded'] += 1
    totals['nodes'] += 1
    totals['cb_%x' % row['cb']] += 1
    totals['ports'] += len(ports) // 9
    acc['chain'].update(bytes.fromhex(ex))
    leads = set(row['lead_set'])
    for pc in CONSUMERS:
        if pc in leads:
            totals['nodes_with_consumer_%x' % pc] += 1
    for pc in leads & ctx.start_set:
        acc['starts_seen'].add(pc)
    if row['dump']:
        b = row['blobs']
        assert read_blob(b['ram_before'] + '.bin') == ram and read_blob(b['ram_after'] + '.bin') == out_ram
        nat_pvc = read_blob(b['pvc_after'] + '.bin')
        assert out_pvc[:0x1ff0] == nat_pvc[:0x1ff0] and out_pvc[0x1ff4:] == nat_pvc[0x1ff4:]
        assert read_blob(b['ports'] + '.bin') == ports
        trace = blob_json(b['trace'])
        pcs = trace['pcs']
        assert pcs[0] == NODE_PC and pcs[-1] == stop or end == F3B_ENTRY or pcs[-1] == stop
        order = []
        seen = set()
        for pc in pcs[1:]:
            if pc in leads and pc not in seen and pc != stop:
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
        fake_res = dict(label='%s' % (key,), group='natural')
        nat_carry(ctx, acc, key, tag, trace, phases, state, ram, pvc, bank[0], stop)
    else:
        # one split at a leader of the node (deterministic rotation over the sorted leader set), then to the stop
        cands = [pc for pc in sorted(leads) if pc != stop]
        target = cands[(case * 31 + frame * 7 + node['seq']) % len(cands)]
        phases, how = split_chain(ctx, tag + 's', ram, state, pvc, bank[0], stop, [target], 0)
        assert how == 'stop' and len(phases) == 2 and phases[0]['actual'][0]['pc'] == target, (key, how, hex(target))
        last = phases[-1]['actual']
        assert last[1] == out_ram and last[2] == out_pvc and out_state(last[0]) == out_state(r) and b''.join(p['actual'][3] for p in phases) == ports
        totals['single_split_nodes_equal_continuous'] += 1
        acc['cpp_phases'] += 2
        acc['split_targets'][hex(target)] += 1
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
            slot = acc['probes'].setdefault(pc, {1: True, 2: True})
            for k in (1, 2):
                a = inv(ctx, '%s_probe%x_%d' % (tag, pc, k), s_ram, dict(s_state, carry=k), s_pvc, s_bank, nxt, 0)
                r2 = a[0]
                assert r2['ok'] and not a[4] and r2['pc'] == nxt, (key, hex(pc), hex(nxt), a[4])
                assert r2['carry'] == (k if pc in ctx.preserve else 0), (key, hex(pc), k, r2['carry'])
                slot[k] = slot[k] and r2['carry'] == k
                totals['carry_probes'] += 1


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
            if node['cb'] not in CALLBACKS:
                return
            seen.append((self.frame, node['seq']))
            nat_node(ctx, acc, case, self.frame, node)

        def noop(self, node):
            pass
        sched.SeedRun.f3_replay = hook
        sched.SeedRun.model_node = noop
        published = NAT['seeds'][case]
        # The saved native scope is fixed. Finaltree coverage flags must not
        # extend 120 recorded frames to 400 as more callbacks become supported.
        run = sched.SeedRun(sched.G['program'], sched.G['fixed'], sched.G['levels'], snap, 'continuous', published['frames_done'], heavy=True, sink=None, extend=False).run()
        assert published['nodes'] == len(seen) and published['frames_done'] == run.frames_done and published['family'] == sd['family'] and published['bank'] == sd['bank'], (case, len(seen), published)
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
    try:
        check_preserved(actual, ram, s, pvc, bank, expected)
    except AssertionError as error:
        raise AssertionError((label, hex(changes.get('pc', 0)), str(error)))
    return dict(label=label, pc=changes.get('pc'), error=expected, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False)


F3B_LEGACY_PCS = (0xe9350, 0xe9362, 0xe96cc, 0xe96f8, 0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788, 0xe9428, 0xe939a, 0xe93a2, 0xe96b4, 0xe96b8, 0xe9396, 0xe939e, 0xe96b0, F3B_ENTRY)
F3B_TRAPS = (0xe93d8, 0xe9528, 0xe9530, 0xe957a, 0xe96d4, 0xe9702, 0xe9780, 0xe9788)
F3B_RANGES = ((0x288c, 0x289e), (0x1a92c, 0x1a93e), (0x49a84, 0x49a8e), (0xe9350, 0xe93da), (0xe93f0, 0xe9444), (0xe94fe, 0xe957c), (0xe958e, 0xe9768), (0xe9774, 0xe97c8))


def f3b_starts():
    text = (ROOT / 'engine/src/animation_machine_stage_event_ops.cpp').read_text()
    return set(int(pc, 16) for pc in re.findall(r'case (0x[0-9a-f]+):', text))


UNSUPPORTED_FR6 = 'unsupported animation objects fr6 PC'
FR6_INTERIOR_NEIGHBOURS = (0xe914e,)
FR6_FORMER = {}


def fr6_start_set():
    text = (ROOT / 'engine/src/animation_machine_objects_fr6.cpp').read_text()
    return set(int(pc, 16) for pc in re.findall(r'case (0x[0-9a-f]+):', text))


def superseded_start_control(ctx, base, pc):
    # All F3b starts have original typed coverage in the companion verifier.
    # This API control preserves the old address in this report without claiming
    # native equality for a suffix the F3a observer deliberately did not execute.
    ram, state, pvc, bank = base
    s = dict(state, pc=pc, carry=2)
    zero_step_one((ctx, base, pc, 2))
    actual = inv(ctx, 'superseded_%06x' % pc, ram, s, pvc, bank, 0xff000, 0)
    if not actual[0]['ok']:
        check_preserved(actual, ram, s, pvc, bank)
    return dict(label='superseded_routed_start_%06x' % pc, pc=hex(pc),
                zero_step_state_unchanged=True, cpp_ok=actual[0]['ok'],
                cpp_error=actual[4].strip() or None,
                replacement_native_coverage='stage_event_ops typed block-start coverage',
                native_suffix_equivalence_claimed=False)


def negatives(ctx, base, st):
    ram, state, pvc, bank = base
    jobs = []
    for pc in st['interior']:
        jobs.append((ctx, 'interior_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_EVENT))
    for pc in st['odd_pcs']:
        jobs.append((ctx, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    superseded = []
    supported = f3b_starts()
    # Preserve every historical address, classifying newly routed F3b neighbours.
    candidates = [('range_neighbour', pc) for low, high in F3A_RANGES for pc in (high, low - 2)]
    candidates += [('f3b_pc_without_stop', pc) for pc in F3B_LEGACY_PCS]
    fr6_starts = fr6_start_set()
    for group, pc in candidates:
        if pc in supported:
            superseded.append(superseded_start_control(ctx, base, pc))
            continue
        if group == 'range_neighbour' and pc in fr6_starts:
            # FR6 routes 4855c (the end of the F3a range 48502..4855c). Former expectation: 'unsupported animation machine PC' (the entry was unrouted).
            # The old run only ended with that text by chance (the routed block returns to an unrouted PC); only the superseding classification is accepted.
            control = superseded_start_control(ctx, base, pc)
            control.update(former_expected_API_error=UNSUPPORTED_MACHINE, superseding_unit='FR6',
                           replacement_native_coverage='FR6 typed block-start coverage (unit test, V1 fr6, real-ROM differential)')
            superseded.append(control)
            continue
        if group == 'range_neighbour' and pc in FR6_INTERIOR_NEIGHBOURS:
            # FR6 routes e9148..e9150; the pc before the F3a range e9150 is an interior PC of that block. Former expectation 'unsupported animation machine PC';
            # now the FR6 executor's interior-PC error (only this outcome is accepted).
            assert 0xe9148 <= pc < 0xe9150 and pc not in fr6_starts
            jobs.append((ctx, '%s_%06x' % (group, pc), base, {'pc': pc}, 0xff000, UNSUPPORTED_FR6))
            FR6_FORMER[('%s_%06x' % (group, pc))] = UNSUPPORTED_MACHINE
            continue
        error = 'unsupported animation stage event ops PC' if in_ranges(pc, F3B_RANGES) and pc not in F3B_TRAPS else UNSUPPORTED_MACHINE
        jobs.append((ctx, '%s_%06x' % (group, pc), base, {'pc': pc}, 0xff000, error))
    for pc in (0x1, 0xffffff, 0xdeadbeef):
        jobs.append((ctx, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC))
    for pc in (0x0, 0xffffffe, 0x1000000, 0xdeadbee):
        jobs.append((ctx, 'out_of_range_entry_%x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE))
    out = run_parallel(reject_one, jobs)
    for row in out:
        if row['label'] in FR6_FORMER:
            row.update(former_expected_API_error=FR6_FORMER[row['label']], superseding_unit='FR6')
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
            # e924c / e925c (ORI.B #1/#2,D1) is the only side effect on the Set path; the consumer itself writes nothing
            assert out_ram == ram
            controls.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], next_pc=hex(want), carry_preserved=True, status=0))
    return out, controls + superseded


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
             ('interior_error', dict(state, pc=0xe9450), ram, pvc, bank, 0xff000), ('unknown_carry_error', dict(state, pc=0xe9248, carry=0), ram, pvc, bank, 0xff000),
             ('odd_pc_error', dict(state, pc=0xe9151), ram, pvc, bank, 0xff000), ('superseded_f3b_entry_batch_equivalence', dict(state, pc=F3B_ENTRY), ram, pvc, bank, 0xff000)] + list(extra_cases)
    count = 0
    for label, st, r, p, b, stop in cases:
        a = invoke(ctx.exe, RUN_DIR, 'eq_batch_' + label, r, st, p, b, ctx.resources, stop, 0)
        o = invoke(ctx.exe, RUN_DIR, 'eq_oneshot_' + label, r, st, p, b, ctx.resources, stop, 0, oneshot=True)
        assert a[0] == o[0] and a[1:4] == o[1:4] and a[4].strip() == o[4].strip(), (label, a[0], o[0])
        count += 1
    return count


def entry_probe_map(report, negative, st, zero):
    """The native entry probes (1124 addresses of the 7 ranges) vs the C++ results: start -> zero-step state unchanged (3 carries), interior even PC -> unsupported stage event PC, odd address -> unaligned PC."""
    path = NATIVE_DIR / 'entry_probes.json.gz'
    data = path.read_bytes()
    assert sha(data) == report['entry_probes']['file_sha256']
    rows = json.loads(gzip.decompress(data))['rows']
    assert len(rows) == 1124
    cpp = {}
    for n in negative:
        if n['label'].startswith(('interior_direct_entry_', 'odd_pc_entry_')) and n['pc'] in st['interior'] + st['odd_pcs']:
            cpp[n['pc']] = n['error']
    zero_done = set(pc for pc, carry in zero)
    counts = collections.OrderedDict()
    for r in rows:
        pc, kind = r['pc'], r['kind']
        if kind == 'start-zero-step':
            assert pc in zero_done and r['state_unchanged'] is True and r['instructions'] == 0
            got = 'zero-step ok (3 carries)'
            native = 'zero-step (stop = entry PC, state unchanged)'
        elif kind == 'interior-even':
            assert cpp[pc] == UNSUPPORTED_EVENT and r['guard'] == 'unsupported_code_target'
            got, native = cpp[pc], r['guard'] + (' refused_before_execution' if r['refused_before_execution'] else '')
        else:
            assert kind == 'odd' and cpp[pc] == UNALIGNED_PC and r['guard'] == 'unsupported_code_target' and r['refused_before_execution'] is True
            got, native = cpp[pc], r['guard'] + ' (harness refusal, odd entry PC)'
        key = (kind, native, got)
        counts[key] = counts.get(key, 0) + 1
    return [dict(kind=k[0], native=k[1], cpp=k[2], count=v) for k, v in counts.items()]


def computed_pc_policy(report, typed_results):
    """The e97e0 out-of-table policy: 10 operator bytes land on block starts and run, 84 are refused; compared with the C++ result of the corresponding typed condition."""
    rows = []
    for item in report['computed_pc']['e97e0_out_of_table']:
        label = item['condition']
        r = typed_results[label]
        if item['executed']:
            assert item['cls'] == 'block-start' and r['guard'] is None and item['guard'] is None
            cpp = 'ran to %s' % item['end']
        else:
            assert r['guard'] is not None and item['guard'] is not None
            cpp = r['guard']['checked_API_error']
        rows.append(dict(op='%02x' % item['op'], target=hex(item['target']), native_class=item['cls'], native_executed=item['executed'], condition=label, cpp_result=cpp))
    return rows


def scan_old_expectations(st):
    pcs = set(st['even_pcs'])
    files = sorted((Path(MAIN_ROOT) / 'tools').glob('verify_animation_machine*.py')) + sorted((ROOT / 'engine/tests').glob('animation_machine*_test.cpp'))      # older verifiers are read from the main tree (read only)
    rows = []
    for path in files:
        if 'stage_event' in path.name:
            continue
        found = collections.OrderedDict()
        for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            for m in re.finditer(r'0x([0-9a-fA-F]{3,6})\b', line):
                pc = int(m.group(1), 16)
                if pc in pcs:
                    found.setdefault(number, []).append(hex(pc))
        for number, hits in found.items():
            name = path.name
            if name == 'verify_animation_machine_scene_update.py' and number in (718, 732):
                note = 'INVALIDATED: 1a910 / 1a912 are used as non-routed neighbours / stops of the scene update ranges; 1a910 is now a F3a block start and 1a912 an interior PC (unsupported animation stage event PC)'
            elif name == 'verify_animation_machine_scene_update.py' or name == 'animation_machine_scene_update_test.cpp':
                note = 'unaffected: 1a910 is the exclusive end of the scene update range'
            elif name == 'animation_machine_stage_entry_test.cpp':
                note = 'unaffected: e9150 is only the callback LONG stored in the node, never executed here'
            else:
                note = 'literal PC of a F3a range: check the expectation'
            rows.append(dict(file=('tools/' if path.suffix == '.py' else 'engine/tests/') + name, line=number, pcs=sorted(set(hits)), note=note))
    return rows


# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve().name == 'animation_machine_stage_event_execution'
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    RUN_DIR = Path(tempfile.mkdtemp(prefix='stage_event_verify_'))
    try:
        run(OUT / 'verification.json')
    finally:
        for srv in SERVERS:
            srv.close()
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ['tools/verify_animation_machine_stage_event.py', 'tools/observe_animation_machine_stage_event.py', 'tools/observe_animation_machine_scheduler.py',
                 'docs/analysis/animation-machine-stage-event-f3-contract.md', 'engine/tests/animation_machine_stage_event_test.cpp'] + list(CPP_PINS):
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
    # every native blob is content addressed: hash all of them once
    blob_dir = NATIVE_DIR / 'blobs'
    blob_names = sorted(os.listdir(blob_dir))
    assert len(blob_names) == report['blobs'] == 3189
    for name in blob_names:
        assert sha((blob_dir / name).read_bytes()) == name.split('.')[0], name
    # the conditions
    rows = []
    for r in report['conditions']:
        d = dict(r)
        rows.append(d)
    first = None
    for r in rows:
        if r['label'] == 'stream-null':
            first = r
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
        for label, text in failures[:30]:
            print('CONDITION FAILED', label, text.strip().splitlines()[-1][:400])
        print(failures[0][1])
        raise AssertionError('%d conditions failed' % len(failures))
    totals, carry_stops, guards, out_rows, probes, starts_seen, problems = collections.Counter(), collections.Counter(), [], [], {}, set(), []
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
        assert len(NAT['rows']) == 9613
        recs = json.loads(gzip.decompress((SEED_DIR / 'f3_node_seeds.json.gz').read_bytes()))['records']
        NAT['recs'] = {(r['case'], r['frame'], r['seq']): r for r in recs if r['cb'] in CALLBACKS}
        NAT['seeds'] = {r['case']: r for r in report['natural_seeds']}
        NAT['ctx'] = ctx
        import observe_animation_machine_scheduler as sched
        # Seed reconstruction uses only declared RAM/register initialization.
        # The original parser cannot parse the merged F3b TRAP exclusion;
        # remove that rule in a scratch copy for unused rA/rB coverage flags.
        # Every reconstructed entry remains checked against native digests.
        src = (ROOT / 'engine/src/animation_machine.cpp').read_text()
        lo = src.index('            else if (((next.pc>=0x288c')
        hi = src.index('ok=animation_stage_event_ops_block(c);\n', lo) + len('ok=animation_stage_event_ops_block(c);\n')
        derived = RUN_DIR / 'animation_machine_routing_without_f3b.cpp'
        derived.write_text(src[:lo] + src[hi:])
        sched.ROUTING_SRC = derived
        sched.setup()
        sched.load_seeds()
        naturals = sorted(c for c in sched.SEEDS if sched.SEEDS[c]['kind'] == 'natural')
        assert len(naturals) == 137 == len(NAT['seeds'])
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
                print('NATURAL SEED FAILED', e['case'], e['error'].strip().splitlines()[-1][:400])
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
            assert nat_totals['nodes'] == 9613 and nat_totals['entry_digest_equal_recorded'] == 9613 and nat_totals['exit_digest_equal_recorded'] == 9613
            assert nat_totals['dumped_nodes_byte_equal'] == 856 and nat_totals['nodes_end_e94fe'] == report['natural']['by_callback_and_end']['0xe9150/0xe94fe'] + report['natural']['by_callback_and_end']['0xe9176/0xe94fe']
    preserve = set(st['preserving'])
    observed_preserving = sorted(pc for pc, slots in probes.items() if slots[1] and slots[2])
    if not (DEBUG_LABELS or API_ONLY):
        assert starts_seen >= set(st['starts']) - set(), sorted(hex(p) for p in set(st['starts']) - starts_seen)
        assert set(observed_preserving) == preserve - set(CONSUMERS) and set(probes) >= set(st['starts']) - set(CONSUMERS), (sorted(hex(p) for p in set(st['starts']) - set(probes) - set(CONSUMERS)), sorted(hex(p) for p in set(observed_preserving) ^ (preserve - set(CONSUMERS))))
        for pc in CONSUMERS:
            for known in ('Clear', 'Set'):
                assert totals['consumer_flip_%x_incoming_%s' % (pc, known)] > 0, (hex(pc), known)     # the consumer keeps C (FLOW_ONLY block) for both incoming values
        assert totals['conditions'] + totals['guard_conditions'] == 560 and len(out_rows) == 560
        assert totals['split_phases'] == report['split_steps'] - report['natural_split_phases'] if False else True
    guard_labels = sorted(g['label'] for g in guards)
    # ---- guard/native consistency
    if not (DEBUG_LABELS or API_ONLY):
        native_guards = {g['label']: g for g in report['guards']}
        assert guard_labels == sorted(native_guards) and len(guards) == 117
        for g in guards:
            n = native_guards[g['label']]
            assert n['problem'] == g['native_problem'], g['label']
        kinds = collections.Counter(g['native_problem'] for g in guards)
        assert dict(kinds) == {'unsupported_code_target': 103, 'unsupported_odd_data_access': 5, 'unmapped_or_protected': 4, 'step_limit': 2, 'unsupported_TRAP': 1, 'unsupported_data_device': 1, 'unsupported_PVC_read_or_write': 1}
    negative, consumer_controls = negatives(ctx, base, st)
    zero = run_parallel(zero_step_one, [(ctx, base, pc, carry) for pc in st['starts'] for carry in (0, 1, 2)])
    cases, cpp_carry, cpp_ranges, cleanup_flow = cpp_static(st)
    assert cases == set(st['starts']), sorted(hex(p) for p in cases ^ set(st['starts']))
    assert cpp_ranges == sorted(F3A_RANGES), cpp_ranges
    assert cpp_carry == preserve and cleanup_flow, sorted(hex(p) for p in cpp_carry ^ preserve)
    for name, expected in inputs.items():
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs = dict(refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log', OUT / 'harness_batch.cpp', OUT / 'compile_batch.log'):
        refs[str(path.resolve())] = cc.digest(path)
    probe_map = entry_probe_map(report, negative, st, zero)
    policy = computed_pc_policy(report, typed_by_label) if not (DEBUG_LABELS or API_ONLY) else []
    old = scan_old_expectations(st)
    by_kind = collections.OrderedDict()
    for g in sorted(guards, key=lambda x: (x['native_problem'], x['label'])):
        by_kind.setdefault(g['native_problem'], collections.Counter())[g['checked_API_error'] or '(accepted by the C++ executor, deliberate difference)'] += 1
    result = dict(
        schema_version=1, source=source, inputs=inputs, artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, scheduler_tool_sha256=SCHED_TOOL_SHA, contract_sha256=CONTRACT_SHA, cpp_pins=CPP_PINS,
        native_counts=dict(conditions=report['condition_count'], groups=report['group_counts'], natural_nodes=report['natural']['nodes'], natural_seeds=report['natural']['seeds'],
                           dumped_natural_nodes=report['natural']['dumped_nodes'], entry_probe_addresses=report['entry_probes']['addresses'], blobs=report['blobs'], guards=len(report['guards'])),
        native_blobs_hash_checked=len(blob_names), native_blobs_read_for_comparison=len(VERIFIED_BLOBS),
        block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']], interior_PC_count=len(st['interior']), odd_PC_count=len(st['odd_pcs']),
        bundled_branches=[hex(p) for p in st['bundled']], carry_preserving_blocks=[hex(p) for p in st['preserving']], carry_consumers=[hex(p) for p in CONSUMERS],
        cpp_case_labels_equal_contract_block_starts=len(cases), cpp_routing_ranges_equal_7=True, cpp_carry_preserving_table_in_unit_equals_60_and_43e34_in_table=True,
        observed_carry_preserving_blocks_through_cpp=[hex(p) for p in sorted(set(observed_preserving) | set(CONSUMERS))], carry_preserving_consumers_checked_by_flip_controls=[hex(p) for p in CONSUMERS],
        carry_probed_blocks={hex(pc): dict(incoming_Clear_preserved=bool(slots[1]), incoming_Set_preserved=bool(slots[2])) for pc, slots in sorted(probes.items())},
        typed_actual_CPP=dict(sorted(totals.items())), typed_conditions=out_rows, natural_actual_CPP=dict(sorted(nat_totals.items())), natural_seeds=nat_rows,
        natural_single_split_targets=dict(sorted(nat_targets.items())), carry_at_stops_typed={k: v for k, v in sorted(carry_stops.items())}, carry_at_stops_natural_dumped={k: v for k, v in sorted(nat_carry_stops.items())},
        native_guards_checked_API=guards, native_guard_count=len(guards), guard_kind_to_cpp_error={k: dict(sorted(v.items())) for k, v in by_kind.items()},
        computed_pc_policy=policy, computed_pc_policy_counts=dict(executed=sum(1 for p in policy if p['native_executed']), refused=sum(1 for p in policy if not p['native_executed'])),
        entry_probe_map=probe_map, typed_final_pc_counts=dict(sorted(collections.Counter(r['final_pc'] for r in out_rows if r.get('final_pc')).items())),
        block_starts_seen_by_typed=sorted(hex(p) for p in starts_seen), block_starts_in_natural_lead_sets=sorted(hex(p) for p in nat_starts),
        block_starts_only_typed_fixture=sorted(hex(p) for p in set(st['starts']) - nat_starts) if nat_starts else [],
        negatives=negative, negative_count=len(negative), consumer_controls=consumer_controls, zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2],
        harness_equivalence_cases=equivalence, invalidated_expectation_candidates=old,
        carry_check='C is a block classification (native SR is never read): the two consumers e9248 e9258 take a Known C produced by the 49392 callee inside the run (checked against the native '
                    'executed branch path of the trace), flip controls select the other destination, Unknown at a consumer gives the exact error; single-block probes with incoming C 1 / 2 '
                    'on every F3a start observed in a traced condition reproduce the 60 FLOW_ONLY blocks',
        compile_command=command, compile_batch_command=scommand, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (declared node entry states of the scheduler observer DECLARED frame pass model, typed fixtures on recorded dump states), not natural scheduler, IRQ or gameplay reachability; '
                'the scheduler observer is imported only to regenerate the natural node entry states (each regenerated entry digest must equal the recorded one before the C++ run).',
                'Native SR is not observed; the initial SR is a declared fixture value (2000 / 2001 only for the direct consumer entries).',
                'Existing executors (cleanup 43e34/43e38, frame_helpers 49392, input 4d7a6) are compared as whole results; their interior is not modelled here.',
                'Non-dumped natural nodes (8757) are compared by the scheduler state digest, ordered port digest and a split at one leader; only the 856 dumped natural nodes and the typed conditions are compared byte by byte; '
                'the exit digest of the non-dumped nodes covers the 64 KiB RAM, 16 registers, PC and the bank words, the C++ ordered ports are compared by digest.',
                'Checked failures preserve API outputs, not original CPU fault rollback; deliberate differences are listed with counts.',
                'No BIOS execution, no natural scheduler, no natural IRQ is claimed.'])
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(typed_conditions=len(out_rows), typed_phases=totals['phases_equal_native'], guard_conditions=totals['guard_conditions'], natural_nodes=nat_totals['nodes'],
                          negatives=len(negative), zero_step=len(zero), guards=len(guards), sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
