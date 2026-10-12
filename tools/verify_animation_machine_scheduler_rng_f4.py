"""Whole-frame-pass C++ execution vs the native RNG-initialised scheduler seed record (F4 decision 1 + 2).

Native input (immutable, pinned): artifacts/animation_machine_scheduler_rng_native/ (observation.json and the 142 seed records + 6 answer-00 variants).
The seed-start dump of every record is the declared state after the recorded 49a1a RAM change (registers stay the seed's registers); this verifier never re-runs
the preparation, it only starts from that dump.  For every recorded frame pass the C++ run_animation_machine is driven with the F2 frame-pass protocol
(PC 2ac2, A6 1008e4, A7 1ff000, LONG 104ca4 = 1ff000 already in the dump, stop = LONG (100820), declared wait releases).  Where the native pass shows a bios-card
wait the C++ run is declared to stop at c00468 and is resumed by the recorded declared resume (PC = c37c, A7 += 4, BYTE 10fdc6 = answer, carry Unknown;
the A6 pop is done by the C++ block at c37c, exactly as the native c37c instruction).  Each pass is compared as the chained node runs (entry state at 2ab8 /
exit state at 2ac2 / MS5-SCHED-PORTS-1 digest per node) and as the single whole-pass run (MS5-SCHED-STATE-1 end digest), with the chain-vs-whole equality.
C++ errors are checked errors; the first one is compared with the observer's first unrouted callback.  Run twice by the caller: identical JSON SHA expected.
The ROM is never modified; this is a declared model, not natural execution (no BIOS execution, no natural IRQ, no natural scheduler).
"""
import collections
import concurrent.futures
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NAT = ROOT / 'artifacts/animation_machine_scheduler_rng_native'
OUT = Path(os.environ['OUTDIR']) if os.environ.get('OUTDIR') else ROOT / 'artifacts/animation_machine_scheduler_rng_f4_execution'
OBS_SHA = '413052978cbf85fa1eedbaaa0ca93bc20b9996c131bba032a6e8db22bc27d6d7'
TOOL_SHA = '659f8636fa82311b757bbcd72190b8874906ad6dbe0baddf638eb5a641e7848b'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
KEYS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')
BIOS = 0xc00468
CARD_RET = 0xc37c
UNROUTED_ERROR = 'unsupported animation machine PC'
NATIVE_END_ERROR = {'fetch-unmapped': 'animation fade card odd JSR target', 'odd-pc': 'unaligned animation machine PC'}
DRIVER_CPP = r'''// Scratch differential driver (not a deliverable): frame passes of the scheduler shell through run_animation_machine.
// Input file: RAM 65536, PVC 8192, 16 regs + pc + bank_base + frames (BE u32). Output: JSON lines.
#include "ms5/animation_machine.h"
#include "ms5/physical_rom_resource.h"
#include <CommonCrypto/CommonDigest.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
typedef std::vector<std::uint8_t> Bytes;
static Bytes load(const char* p){std::ifstream f(p,std::ios::binary);return Bytes((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());}
static std::uint32_t be(const Bytes& b,std::size_t o){return (std::uint32_t(b[o])<<24)|(std::uint32_t(b[o+1])<<16)|(std::uint32_t(b[o+2])<<8)|b[o+3];}
static void put32(Bytes& b,std::uint32_t v){for(int i=3;i>=0;--i)b.push_back(static_cast<std::uint8_t>(v>>(8*i)));}
static void put16(Bytes& b,std::uint32_t v){b.push_back(static_cast<std::uint8_t>(v>>8));b.push_back(static_cast<std::uint8_t>(v));}
static std::string hexs(const unsigned char* d,unsigned n){static const char* h="0123456789abcdef";std::string s;for(unsigned i=0;i<n;++i){s+=h[d[i]>>4];s+=h[d[i]&15];}return s;}
static std::uint32_t ramget(const Bytes& r,std::uint32_t a,unsigned n){std::uint32_t v=0;for(unsigned i=0;i<n;++i)v=(v<<8)|r[(a+i)&65535U];return v;}
static std::string state_digest(const Bytes& ram,const ms5::AnimationMachineState& s,std::uint32_t pc,const ms5::AnimationMachineDevice& dev,bool a5_fix){
    Bytes tail;const char* tag="MS5-SCHED-STATE-1";tail.insert(tail.end(),tag,tag+std::strlen(tag));
    Bytes regs;for(unsigned i=0;i<8;++i)put32(regs,s.d[i]);for(unsigned i=0;i<8;++i)put32(regs,(a5_fix&&i==5)?0x108000U:s.a[i]);
    Bytes t2;put32(t2,pc);put32(t2,dev.bank_base);put32(t2,0);put16(t2,(std::uint32_t(dev.pvc[0x1ff0])<<8)|dev.pvc[0x1ff1]);put16(t2,(std::uint32_t(dev.pvc[0x1ff2])<<8)|dev.pvc[0x1ff3]);
    CC_SHA256_CTX c;CC_SHA256_Init(&c);CC_SHA256_Update(&c,&tail[0],tail.size());CC_SHA256_Update(&c,&ram[0],ram.size());
    CC_SHA256_Update(&c,&regs[0],regs.size());CC_SHA256_Update(&c,&t2[0],t2.size());unsigned char d[32];CC_SHA256_Final(d,&c);return hexs(d,32);
}
// Unicorn port tuples: PVC page writes kind 1, other devices kind 2; the 4fcce MOVEM.W pair splits into two WORD events.
static std::string ports_digest(const std::vector<ms5::VideoPortWrite>& p,bool split){
    Bytes b;const char* tag="MS5-SCHED-PORTS-1";b.insert(b.end(),tag,tag+std::strlen(tag));
    for(std::size_t i=0;i<p.size();++i){
        const std::uint32_t a=p[i].address;
        if(a>=0x2fe000U&&a<0x300000U){b.push_back(1);put32(b,a);b.push_back(2);put32(b,p[i].value&65535U);}
        else if(split&&a==0x3c0000U&&p[i].size==4){b.push_back(2);put32(b,a);b.push_back(2);put32(b,p[i].value>>16);b.push_back(2);put32(b,a+2);b.push_back(2);put32(b,p[i].value&65535U);}
        else{b.push_back(2);put32(b,a);b.push_back(p[i].size);put32(b,p[i].value);}
    }
    unsigned char d[32];CC_SHA256(&b[0],static_cast<CC_LONG>(b.size()),d);return hexs(d,32);
}
struct Machine {const ms5::ProgramBusState* bus;std::vector<ms5::FixedDataResource> w;};
// Declared bios-card wait: stop PC c00468 (the JSR at c376 pushed c37c; (A7+4) = saved A6); declared resume PC = c37c, A7 += 4, BYTE 10fdc6 = answer, carry Unknown.
static const std::uint32_t BIOS=0xc00468U;
struct CardRec {std::uint32_t pc,a7,ret,saved_a6,a6;};
struct Card {unsigned remaining;unsigned answer;std::vector<CardRec> recs;bool bad;Card():remaining(0),answer(0x80),bad(false){}};
static bool g_seg_preserved=true;
// One run with the declared wait release loop (sound 3aea: WORD 104d74 = ffff; sprite cda4: WORD 108d34 = D4.W; gate 47af0/478de:
// BYTE 107ded bit 7 cleared unless WORD 107dea <> 0) and the declared bios-card stop/resume.
static bool run(Machine& m,Bytes& ram,ms5::AnimationMachineState& s,ms5::AnimationMachineDevice& dev,std::uint32_t stop,
    std::vector<ms5::VideoPortWrite>& all,std::string& error,unsigned& waits,std::uint32_t& reads_total,Card& card){
    for(unsigned k=0;k<40;++k){
        std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads=0;ms5::AnimationMachineStatus st=ms5::AnimationMachineReturned;
        const std::uint32_t cur_stop=card.remaining?BIOS:stop;
        const Bytes before=ram;const ms5::AnimationMachineState sb=s;const ms5::AnimationMachineDevice db=dev;
        if(!ms5::run_animation_machine(ram,m.w,*m.bus,s,dev,cur_stop,0,reads,st,ports,error)){
            bool pr=(ram==before)&&dev.pvc==db.pvc&&dev.bank_base==db.bank_base&&s.pc==sb.pc;
            for(unsigned i=0;i<8;++i)if(s.d[i]!=sb.d[i]||s.a[i]!=sb.a[i])pr=false;
            g_seg_preserved=pr;return false;}
        all.insert(all.end(),ports.begin(),ports.end());reads_total+=reads;
        if(st==ms5::AnimationMachineReturned){
            if(cur_stop==BIOS){
                CardRec r;r.pc=s.pc;r.a7=s.a[7];r.ret=ramget(ram,s.a[7],4);r.saved_a6=ramget(ram,s.a[7]+4,4);r.a6=s.a[6];card.recs.push_back(r);
                if(s.pc!=BIOS||r.ret!=0xc37cU){card.bad=true;error="card-stop-state";return false;}
                s.pc=0xc37cU;s.a[7]+=4;ram[0xfdc6]=static_cast<std::uint8_t>(card.answer);s.carry=ms5::AnimationCarryUnknown;--card.remaining;continue;
            }
            return true;
        }
        ++waits;
        if(s.pc==0x3aea){ram[0x4d74]=0xff;ram[0x4d75]=0xff;}
        else if(s.pc==0xcda4){ram[0x8d34]=static_cast<std::uint8_t>(s.d[4]>>8);ram[0x8d35]=static_cast<std::uint8_t>(s.d[4]);}
        else if(ramget(ram,0x107dea,2)==0)ram[0x7ded]&=0x7f;
        else {error="wait-not-released";return false;}
    }
    error="wait-limit";return false;
}
int main(int argc,char** argv){
    if(argc<4)return 2;
    std::vector<ms5::PhysicalRomResource> physical;std::string error;
    for(int i=3;i<argc;++i){ms5::PhysicalRomResource r;if(!ms5::load_physical_rom_resource(argv[i],r,error)){std::cerr<<error;return 3;}physical.push_back(r);}
    ms5::ProgramBusState bus;bus.physical_rom=&physical;Bytes vectors;
    for(std::size_t i=0;i<physical.size();++i)if(physical[i].source_rom_offset==0&&physical[i].data.size()>=128)vectors.assign(physical[i].data.begin(),physical[i].data.begin()+128);
    if(!vectors.empty())bus.vectors=&vectors;
    Machine m;m.bus=&bus;
    const Bytes in=load(argv[1]);const std::size_t hdr=65536+8192+19*4;if(in.size()<hdr+4)return 4;
    Bytes ram(in.begin(),in.begin()+65536);ms5::AnimationMachineDevice dev;dev.pvc.assign(in.begin()+65536,in.begin()+65536+8192);
    ms5::AnimationMachineState s;std::size_t o=65536+8192;
    for(unsigned i=0;i<8;++i)s.d[i]=be(in,o+4*i);for(unsigned i=0;i<8;++i)s.a[i]=be(in,o+32+4*i);s.pc=be(in,o+64);dev.bank_base=be(in,o+68);
    const std::uint32_t frames=be(in,o+72);
    // card spec: answer, then per frame: count and the node seqs (A6 order index) of the declared bios-card waits of that native pass
    std::size_t q=hdr;const std::uint32_t answer=be(in,q);q+=4;
    std::vector<std::vector<std::uint32_t> > cardseq(frames);
    for(std::uint32_t f=0;f<frames;++f){const std::uint32_t n=be(in,q);q+=4;for(std::uint32_t i=0;i<n;++i){cardseq[f].push_back(be(in,q));q+=4;}}
    if(q!=in.size())return 5;
    std::ofstream out(argv[2]);
    for(std::uint32_t frame=0;frame<frames;++frame){
        if(frame>0){s.pc=0x2ac2;s.a[6]=0x1008e4;s.a[7]=0x1ff000;}
        s.carry=ms5::AnimationCarryUnknown;
        std::ostringstream js;js<<"{\"frame\":"<<frame<<",\"start\":\""<<state_digest(ram,s,0x2ac2,dev,false)<<"\"";
        const std::uint32_t head=ramget(ram,0x100820,4);
        if(head!=0xe4a&&head!=0xe74){js<<",\"host_reject\":"<<head<<"}";out<<js.str()<<"\n";break;}
        Bytes cram=ram;ms5::AnimationMachineState cs=s;ms5::AnimationMachineDevice cdev=dev;std::vector<ms5::VideoPortWrite> cports;
        std::string cerr_;bool cok=true;unsigned waits=0;std::uint32_t reads=0;js<<",\"nodes\":[";bool first=true;std::string ctrl;
        for(unsigned n=0;n<400;++n){
            std::vector<ms5::VideoPortWrite> p;Card c0;c0.answer=answer;
            if(!run(m,cram,cs,cdev,0x2abe,p,cerr_,waits,reads,c0)){cok=false;break;}
            cports.insert(cports.end(),p.begin(),p.end());
            if(cs.a[6]==0x100820){p.clear();if(!run(m,cram,cs,cdev,head,p,cerr_,waits,reads,c0)){cok=false;}cports.insert(cports.end(),p.begin(),p.end());break;}
            if(cs.a[6]==0x1008e4){ctrl="controller-node-visited";break;}
            const std::uint32_t a6=cs.a[6],cb=ramget(cram,a6,4);
            const std::string entry=state_digest(cram,cs,0x2ab8,cdev,true);
            p.clear();std::string nerr;
            Card nc;nc.answer=answer;for(std::size_t i=0;i<cardseq[frame].size();++i)if(cardseq[frame][i]==n)++nc.remaining;
            const bool ok=run(m,cram,cs,cdev,0x2ac2,p,nerr,waits,reads,nc);
            js<<(first?"":",")<<"{\"a6\":"<<a6<<",\"cb\":"<<cb<<",\"entry\":\""<<entry<<"\"";first=false;
            if(!ok){js<<",\"error\":\""<<nerr<<"\"}";cerr_=nerr;cok=false;break;}
            const bool split=(cb==0x4fcce||cb==0x4fcda);
            js<<",\"exit\":\""<<state_digest(cram,cs,0x2ac2,cdev,false)<<"\",\"ports\":"<<p.size()<<",\"ports_sha\":\""<<ports_digest(p,split)<<"\"";
            if(!nc.recs.empty()){js<<",\"cards\":[";for(std::size_t i=0;i<nc.recs.size();++i)js<<(i?",":"")<<"["<<nc.recs[i].a7<<","<<nc.recs[i].saved_a6<<","<<nc.recs[i].a6<<"]";js<<"]";}
            js<<"}";
            cports.insert(cports.end(),p.begin(),p.end());
        }
        js<<"]";
        std::vector<ms5::VideoPortWrite> wports;
        std::string werr;unsigned wwaits=0;std::uint32_t wreads=0;
        Card wc;wc.answer=answer;wc.remaining=static_cast<unsigned>(cardseq[frame].size());
        g_seg_preserved=true;
        const bool wok=run(m,ram,s,dev,head,wports,werr,wwaits,wreads,wc);
        if(!wok){
            js<<",\"error\":\""<<werr<<"\",\"preserved\":"<<(g_seg_preserved?"true":"false")<<",\"chain_ok\":"<<(cok?"true":"false")<<",\"chain_error\":\""<<cerr_<<"\"";
            if(!ctrl.empty())js<<",\"ctrl\":true";
            js<<"}";out<<js.str()<<"\n";break;
        }
        bool same=cok&&ctrl.empty()&&cram==ram&&cdev.pvc==dev.pvc&&cdev.bank_base==dev.bank_base&&cs.pc==s.pc&&cports.size()==wports.size();
        for(unsigned i=0;i<8&&same;++i)if(cs.d[i]!=s.d[i]||cs.a[i]!=s.a[i])same=false;
        js<<",\"end\":\""<<state_digest(ram,s,s.pc,dev,false)<<"\",\"pc\":"<<s.pc<<",\"a7\":"<<s.a[7]<<",\"a6\":"<<s.a[6]<<",\"a5\":"<<s.a[5]<<",\"a0\":"<<s.a[0]
          <<",\"stack\":"<<ramget(ram,s.a[7],4)<<",\"waits\":"<<wwaits<<",\"reads\":"<<wreads<<",\"ports\":"<<wports.size()<<",\"chain_equal\":"<<(same?"true":"false");
        js<<",\"cards\":[";for(std::size_t i=0;i<wc.recs.size();++i)js<<(i?",":"")<<"["<<wc.recs[i].a7<<","<<wc.recs[i].saved_a6<<","<<wc.recs[i].a6<<"]";
        js<<"]}";
        out<<js.str()<<"\n";
    }
    return 0;
}
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def state_digest(ram, regs, pc, bank):
    h = hashlib.sha256()
    h.update(b'MS5-SCHED-STATE-1')
    h.update(ram)
    h.update(struct.pack('>16I', *[regs[k] for k in KEYS]))
    h.update(struct.pack('>IIIHH', pc, bank[0], 0, bank[1] & 0xffff, bank[2] & 0xffff))
    return h.hexdigest()


def build_driver(work):
    work.mkdir(parents=True, exist_ok=True)
    src = work / 'frame_pass_rng_driver.cpp'
    src.write_text(DRIVER_CPP)
    exe = work / 'frame_pass_rng_driver'
    makefile = (ROOT / 'Makefile').read_text()
    line = [l for l in makefile.splitlines() if l.startswith('ANIMATION_MACHINE_SOURCES =')][0]
    sources = line.split('=', 1)[1].split()
    cmd = ['clang++', '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-Wno-deprecated-declarations', '-Iengine/include'] + sources + \
          ['engine/src/physical_rom_resource.cpp', str(src), '-o', str(exe)]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, close_fds=False)
    assert r.returncode == 0, r.stderr
    # Compiler warnings are diagnostics; successful exit confirms build.
    return exe


def load_doc(directory, case):
    return json.load(gzip.open(directory / ('seed_%04d.json.gz' % case)))


def run_case(exe, work, windows, directory, case, answer):
    doc = load_doc(directory, case)
    assert doc['answer'] == answer, (case, doc['answer'], answer)
    start = [d for d in doc['dumps'] if d['kind'] == 'seed-start']
    assert len(start) == 1
    st = start[0]
    ram = (NAT / 'blobs' / (st['ram'] + '.bin')).read_bytes()
    assert sha(ram) == st['ram'] and state_digest(ram, st['regs'], st['pc'], st['bank']) == st['state']
    assert int.from_bytes(ram[0x4ca4:0x4ca8], 'big') == 0x1ff000
    assert int.from_bytes(ram[0xd722 & 0xffff:(0xd722 & 0xffff) + 4], 'big') == 0x10d720, 'RNG pointer must be the recorded post-preparation value'
    base, ff8, ff9 = st['bank']
    pvc = bytearray(8192)
    pvc[0x1ff0:0x1ff2] = ff8.to_bytes(2, 'big')
    pvc[0x1ff2:0x1ff4] = ff9.to_bytes(2, 'big')
    passes = doc['passes']
    frames = len(passes)
    spec = struct.pack('>I', answer)
    native_cards = {}
    for i, p in enumerate(passes):
        cards = [w for w in p['waits'] if w['kind'] == 'bios-card']
        for w in cards:
            assert w['pc'] == BIOS and w['live'] == CARD_RET and w['released'][:2] == [['pc', CARD_RET], ['a7', 4]] and w['compared'] == answer
            nseq = [n['seq'] for n in p['nodes']]
            assert nseq == list(range(len(nseq))) and 0 <= w['node'] < len(nseq)
        native_cards[i] = cards
        spec += struct.pack('>I', len(cards)) + b''.join(struct.pack('>I', w['node']) for w in cards)
    blob = ram + bytes(pvc) + struct.pack('>16I', *[st['regs'][k] for k in KEYS]) + struct.pack('>III', st['pc'], base, frames) + spec
    tag = '%s_%04d_%02x' % (directory.name, case, answer)
    inp, outp = work / ('in_' + tag + '.bin'), work / ('out_' + tag + '.jsonl')
    inp.write_bytes(blob)
    r = subprocess.run([str(exe), str(inp), str(outp)] + windows, capture_output=True, text=True, close_fds=False, timeout=7200)
    assert r.returncode == 0, (case, r.returncode, r.stderr)
    rows = [json.loads(l) for l in outp.read_text().splitlines()]
    inp.unlink()
    outp.unlink()
    res = dict(case=case, kind=doc['kind'], answer=answer, native_frames=frames, native_stop=doc['stop']['reason'], native_stop_detail=doc['stop'], cpp_passes=len(rows),
               pass_equal=0, node_compared=0, node_equal=0, chain_unequal=0, cards_native=0, cards_cpp=0, cards_equal=0, mismatches=[], cpp_stop=None)
    for i, row in enumerate(rows):
        p = passes[i]
        if row['start'] != p['start']:
            res['mismatches'].append(dict(frame=i, node=None, field='start'))
            break
        nn, cn = p['nodes'], row.get('nodes', [])
        bad = False
        for j, c in enumerate(cn):
            if j >= len(nn):
                res['mismatches'].append(dict(frame=i, node=j, field='extra-node'))
                bad = True
                break
            n = nn[j]
            if 'error' in c:
                for f in ('a6', 'cb', 'entry'):
                    if c[f] != n[f]:
                        res['mismatches'].append(dict(frame=i, node=j, field='error-node-' + f))
                        bad = True
                        break
                break
            res['node_compared'] += 1
            diff = [f for f, nf in (('a6', 'a6'), ('cb', 'cb'), ('entry', 'entry'), ('exit', 'exit'), ('ports_sha', 'ports_sha')) if c[f] != n[nf]]
            if diff:
                res['mismatches'].append(dict(frame=i, node=j, field=diff[0], cpp=c.get(diff[0]), native=n[diff[0]]))
                bad = True
                break
            res['node_equal'] += 1
            ncards = [w for w in native_cards[i] if w['node'] == j]
            ccards = c.get('cards', [])
            res['cards_native'] += len(ncards)
            res['cards_cpp'] += len(ccards)
            if [[w['a7_at_stop'], w['saved_a6'], w['node_a6']] for w in ncards] != ccards:
                res['mismatches'].append(dict(frame=i, node=j, field='card-stop-state'))
                bad = True
                break
            res['cards_equal'] += len(ncards)
        if bad:
            break
        if 'error' in row or 'host_reject' in row:
            fail = next((c for c in cn if 'error' in c), None)
            res['cpp_stop'] = dict(frame=i, error=row.get('error'), preserved=row.get('preserved'), host_reject=row.get('host_reject'), chain_error=row.get('chain_error'),
                                   node_cb=fail['cb'] if fail else None, node_a6=fail['a6'] if fail else None, node_index=cn.index(fail) if fail else None)
            break
        if not row['chain_equal']:
            res['chain_unequal'] += 1
        if p['stop'] != 'frame-head':
            res['mismatches'].append(dict(frame=i, node=None, field='cpp-completed-native-stopped'))
            break
        if row['end'] != p['end'] or len(cn) != len(nn):
            res['mismatches'].append(dict(frame=i, node=None, field='end' if row['end'] != p['end'] else 'node-count'))
            break
        if not (row['a7'] == 0x1ff000 - 4 and row['stack'] == 0x2ac2 and row['a6'] == 0x100820 and row['a5'] == 0x108000 and row['a0'] == row['pc'] and row['pc'] in (0xe4a, 0xe74)):
            res['mismatches'].append(dict(frame=i, node=None, field='head-registers'))
            break
        if row['cards'] != [[w['a7_at_stop'], w['saved_a6'], w['node_a6']] for w in native_cards[i]]:
            res['mismatches'].append(dict(frame=i, node=None, field='whole-pass-card-stop-state'))
            break
        res['pass_equal'] += 1
    # classification
    first = None
    for p in passes:
        for n in p['nodes']:
            if not n['rA']:
                first = dict(frame=p['frame'], seq=n['seq'], a6=n['a6'], cb=n['cb'])
                break
        if first:
            break
    res['first_unrouted'] = first
    s = res['cpp_stop']
    if res['mismatches']:
        cls = 'MISMATCH'
    elif s is None:
        cls = 'complete' if res['pass_equal'] == frames == len(rows) else 'incomplete'
    elif (s['frame'] == frames - 1 and res['pass_equal'] == frames - 1 and native_stop_is_end(doc) and s['preserved'] and
          s['error'] == NATIVE_END_ERROR.get(doc['stop']['reason'])):
        cls = 'cpp-error-at-native-end:' + str(s['error'])
    elif first and s['frame'] == first['frame'] and s['node_cb'] == first['cb'] and s['node_a6'] == first['a6'] and s['error'] == UNROUTED_ERROR and s['preserved'] and res['pass_equal'] == first['frame']:
        cls = 'unrouted-equals-observer-first'
    else:
        cls = 'cpp-error-other'
    res['classification'] = cls
    return res


def native_stop_is_end(doc):
    return doc['stop']['reason'] != 'frame-limit'


def run_all(exe, work, windows, workers):
    obs = json.loads((NAT / 'observation.json').read_text())
    cases = [r['case'] for r in obs['seeds']]
    jobs = [(NAT / 'seeds', c, 0x80) for c in cases]
    variants = [(NAT / 'variants_answer00', r['case'], 0x00) for r in obs['variants_answer00']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        main = list(ex.map(lambda j: run_case(exe, work, windows, *j), jobs))
        var = list(ex.map(lambda j: run_case(exe, work, windows, *j), variants))
    return obs, main, var


def summarize(rows):
    t = collections.Counter()
    cls = collections.Counter()
    for r in rows:
        t['seeds'] += 1
        t['passes_equal'] += r['pass_equal']
        t['native_frames'] += r['native_frames']
        t['nodes_compared'] += r['node_compared']
        t['nodes_equal'] += r['node_equal']
        t['chain_unequal'] += r['chain_unequal']
        t['cards_native'] += r['cards_native']
        t['cards_equal'] += r['cards_equal']
        t['mismatch_seeds'] += bool(r['mismatches'])
        cls[r['classification']] += 1
    t['classification'] = dict(cls)
    return dict(t)



def boundary_native(argument):
    directory, result = argument
    import observe_animation_machine_scheduler_rng as observer
    import observe_animation_machine_objects_g1 as g1
    import unicorn
    doc = load_doc(directory,result['case'])
    frame = result['cpp_stop']['frame']
    # Start from the dump of the immediately preceding pass end (frame-1) when recorded; otherwise (the record dumps only boundary frames)
    # replay from the latest recorded pass-end dump before the stop frame, or from the seed start, requiring every intermediate pass digest to equal
    # the native per-pass MS5-SCHED-STATE-1 end digest.
    exact = [row for row in doc['dumps'] if row['kind']=='pass-end' and row['frame']==frame-1] if frame else [row for row in doc['dumps'] if row['kind']=='seed-start']
    if exact:
        assert len(exact)==1
        initial = exact[0]; replay_from = 'frame-1-dump' if frame else 'seed-start'; first_frame = frame
    else:
        earlier = sorted((row for row in doc['dumps'] if row['kind']=='pass-end' and row['frame']<frame-1), key=lambda row: row['frame'])
        if earlier:
            initial = earlier[-1]; first_frame = initial['frame']+1; replay_from = 'pass-end-dump-%d' % initial['frame']
        else:
            initial = [row for row in doc['dumps'] if row['kind']=='seed-start'][0]; first_frame = 0; replay_from = 'seed-start'
    ram = (NAT/'blobs'/(initial['ram']+'.bin')).read_bytes()
    assert sha(ram)==initial['ram']
    assert state_digest(ram,initial['regs'],initial['pc'],initial['bank'])==initial['state']
    snapshot = dict(ram=ram,regs=dict(initial['regs']),pc=0x2ac2,bank=initial['bank'])
    if first_frame:
        snapshot['regs'].update(a6=0x1008e4,a7=0x1ff000)
    run = observer.RngRun(observer.G['program'],observer.G['fixed'],observer.G['levels'],snapshot,
                          'continuous',1,extend=False,answer=doc['answer'])
    run.frame=first_frame
    machine=run.build(snapshot)
    machine.cpu.reg_write(observer.UC_REG['sr'],0x2000)
    active=[False]
    missing=[]
    atomic_palette=[False]
    def hook(cpu,pc,size,unused):
        if pc==BIOS or not active[0]: return
        # Earlier completed nodes have frozen entry/exit/ports equality; their
        # internal instruction PCs need not be public dispatcher starts.
        cur=run.cur
        stop=result['cpp_stop']
        if cur is None or (cur['seq'],cur['a6'],cur['cb']) != (stop['node_index'],stop['node_a6'],stop['node_cb']): return
        # Exit contract: 8c16 invokes one existing whole-leaf palette adapter.
        # Its original body has no JSR; interior PCs are not public dispatch boundaries.
        if pc==0x8c16: atomic_palette[0]=True
        if atomic_palette[0] and 0x8c16<=pc<0x8ca4: return
        atomic_palette[0]=False
        bitmap=observer.G['bm']
        if pc&1 or pc>=0x100000 or not bitmap[pc>>1]:
            missing.append(pc)
            run.request_stop('current-unrouted-PC',pc=pc)
    machine.cpu.hook_add(unicorn.UC_HOOK_CODE,hook,begin=0,end=0xffffff)
    replayed_equal=0
    for f in range(first_frame,frame+1):
        run.frame=f
        if f>first_frame:
            machine.cpu.reg_write(observer.UC_REG['sr'],0x2000);machine.cpu.reg_write(observer.UC_REG['pc'],0x2ac2)
            machine.cpu.reg_write(observer.UC_REG['a6'],0x1008e4);machine.cpu.reg_write(observer.UC_REG['a7'],0x1ff000)
        active[0]=(f==frame)
        reason,walk,start,waits,ports0=run.run_pass()
        assert start==doc['passes'][f]['start'],('native replay start',f)
        if f<frame:
            es=machine.state();es['pc']=reason['pc']
            assert reason['reason']=='frame-head',(result['case'],f,reason)
            assert state_digest(es['ram'],es['regs'],es['pc'],es['bank'])==doc['passes'][f]['end'],('replayed pass digest',result['case'],f)
            replayed_equal+=1
    native_pass=doc['passes'][frame]
    assert start==native_pass['start'],('native replay start',frame)
    cur=run.cur
    stop=result['cpp_stop']
    same_node=(cur is not None and cur['a6']==stop['node_a6'] and cur['cb']==stop['node_cb'] and cur['seq']==stop['node_index'])
    entry=None
    if cur is not None:
        entry=state_digest(cur['entry_ram'],cur['entry_regs'],0x2ab8,cur['entry_bank'])
        assert entry==native_pass['nodes'][cur['seq']]['entry']
    prefix_equal=True
    for index,node in enumerate(run.pass_nodes):
        record=node['rec'];expected=native_pass['nodes'][index]
        if any(record[key]!=expected[key] for key in ('a6','cb','entry','exit','ports_sha')): prefix_equal=False
    approved=(reason['reason']=='current-unrouted-PC' and bool(missing) and same_node and prefix_equal
              and stop['preserved'] and stop['error']==UNROUTED_ERROR and result['pass_equal']==frame
              and not result['mismatches'] and result['chain_unequal']==0)
    return dict(approved=approved,replay_from=replay_from,replayed_equal_passes=replayed_equal,first_replayed_frame=first_frame,
                observer_first_unrouted=result['first_unrouted'],current_first_missing_PC=missing[0] if missing else None,
                native_reason=reason,frame=frame,callback=cur['cb'] if cur else None,
                node_entry_sha256=entry,node_entry_matches_frozen_native=entry is not None,
                completed_native_node_prefix_equal=prefix_equal,completed_native_nodes=len(run.pass_nodes),
                initial_state_sha256=initial['state'],initial_RAM_sha256=initial['ram'],
                current_router_sha256=sha((ROOT/'engine/src/animation_machine.cpp').read_bytes()),
                atomic_palette_leaf=dict(entry=0x8c16,end_exclusive=0x8ca4,
                  original_bytes_sha256=sha(observer.G['program'][0x8c16:0x8ca4]),
                  contract='docs/analysis/animation-machine-exit-contract.md',
                  contract_sha256=sha((ROOT/'docs/analysis/animation-machine-exit-contract.md').read_bytes())))


def audit_current_boundaries(rows,variants):
    import observe_animation_machine_scheduler_rng as observer
    import observe_animation_machine_objects_g1 as g1
    observer.setup((ROOT/'engine/src/animation_machine.cpp').read_text())
    for directory,results in ((NAT/'seeds',rows),(NAT/'variants_answer00',variants)):
        for result in results:
            if not result['cpp_stop'] or result['cpp_stop']['error']!=UNROUTED_ERROR: continue
            ok,evidence,_=g1.isolated(boundary_native,(directory,result))
            result['current_boundary_evidence']=evidence if ok else dict(approved=False,native_replay_aborted=True)
            if ok and evidence['approved']:
                result['historical_first_unrouted']=result['first_unrouted']
                result['classification']='checked-current-first-unrouted-PC' if evidence['replayed_equal_passes']==0 else 'checked-current-first-unrouted-PC-replayed'
            else:
                result['classification']='cpp-error-other'


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    executed_tool_sha256=sha(Path(__file__).read_bytes())
    source_hashes={str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in (ROOT/'engine/src').glob('*.cpp')}
    work = OUT / 'work'
    workers = int(os.environ.get('W', '3'))
    assert sha((NAT / 'observation.json').read_bytes()) == OBS_SHA, 'native observation changed'
    obs_rom = json.loads((NAT / 'observation.json').read_text())['rom_stat_start']
    observer = ROOT / 'tools/observe_animation_machine_scheduler_rng.py'
    if not observer.exists():                          # the observer is not yet committed into this worktree: pin the copy of the main tree
        observer = Path('/Users/start/Workspce/metalslug/tools/observe_animation_machine_scheduler_rng.py')
    assert sha(observer.read_bytes()) == TOOL_SHA, 'native observer changed'
    rom = ROOT / 'extracted/program/maincpu.decrypted.be.bin'
    rom_start = (sha(rom.read_bytes()), rom.stat().st_mtime_ns, rom.stat().st_size)
    assert rom_start[0] == ROM_SHA and rom_start[1] == obs_rom['mtime_ns'] and rom_start[2] == obs_rom['size'], (rom_start, obs_rom)
    windows = sorted(str(p) for p in (ROOT / 'extracted/runtime/program_rom').glob('*.ms5d'))
    assert len(windows) == 8, windows
    exe = build_driver(work)
    obs, rows, var = run_all(exe, work, windows, workers)
    audit_current_boundaries(rows,var)
    assert (sha(rom.read_bytes()), rom.stat().st_mtime_ns, rom.stat().st_size) == rom_start, 'ROM changed'
    summary = summarize(rows)
    vsummary = summarize(var)
    complete = sorted(r['case'] for r in rows if r['classification'] == 'complete')
    routed = obs['totals']['all_callbacks_routed_seeds']
    natural_routed = [c for c in routed]
    checks = dict(
        routed_all_complete_or_native_end=all(r['classification'] == 'complete' or r['classification'].startswith('cpp-error-at-native-end') for r in rows if r['case'] in set(routed)),
        routed_complete=len([r for r in rows if r['case'] in set(routed) and r['classification'] == 'complete']),
        routed_native_end=sorted(r['case'] for r in rows if r['case'] in set(routed) and r['classification'].startswith('cpp-error-at-native-end')),
        unrouted_equals_observer_first=len([r for r in rows if r['classification'] == 'unrouted-equals-observer-first']),
        other=sorted(r['case'] for r in rows if r['classification'] in ('cpp-error-other', 'incomplete', 'MISMATCH')),
        no_mismatch=all(not r['mismatches'] for r in rows + var),
        chain_equal=summary['chain_unequal'] == 0 and vsummary['chain_unequal'] == 0,
        routed_count=len(routed))
    assert executed_tool_sha256==sha(Path(__file__).read_bytes()), 'executed tool changed'
    assert all(sha((ROOT/path).read_bytes())==digest for path,digest in source_hashes.items()), 'engine sources changed'
    report = dict(schema_version=1, tool='tools/verify_animation_machine_scheduler_rng_f4.py', executed_tool_sha256=executed_tool_sha256, engine_source_sha256=source_hashes, rom=dict(sha256=ROM_SHA, size=rom_start[2], mtime_ns=rom_start[1], unchanged=True),
                  native=dict(observation_sha256=OBS_SHA, observer_sha256=TOOL_SHA, rom_sha256=ROM_SHA),
                  declared=dict(frame_pass=dict(pc=0x2ac2, a6=0x1008e4, a7=0x1ff000, base_long_104ca4=0x1ff000, stop='LONG(100820)'),
                                bios_card=dict(stop_pc=BIOS, resume_pc=CARD_RET, a7_delta=4, answer_byte=0x10fdc6, carry='Unknown'),
                                seed_start='seed-start dump = post-49a1a RAM, seed registers (preparation not re-run)'),
                  totals=summary, variants_answer00=dict(totals=vsummary, seeds=var), checks=checks, complete_seeds=complete, seeds=rows)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'verification.json'
    path.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps(dict(totals=summary, variants=vsummary, checks=checks, sha256=sha(path.read_bytes())), sort_keys=True))
    return 0 if checks['no_mismatch'] and checks['chain_equal'] and checks['routed_all_complete_or_native_end'] and not checks['other'] else 1


if __name__ == '__main__':
    sys.exit(main())
