#include "ms5/animation_machine.h"
#include <cassert>
#include <cstdio>
#include <iostream>
#include <string>
// F6a vblank IRQ shell (193 block starts + 381 computed clear-run entries; contract docs/analysis/animation-machine-irq-f6a-contract.md)
// through run_animation_machine only. Inputs are declared work RAM fixtures (no ROM resource: F6a reads no ROM data). Expectations are
// written from the original instructions in this file (independent of the executor); the native Unicorn comparison of the same
// semantics is the V1 spec tools/unit_fixture_specs/f6a.py.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef ms5::AnimationMachineState State;
typedef std::vector<ms5::VideoPortWrite> Ports;
const std::uint32_t SENT=0xc00500;   // return sentinel (stop)
const std::uint32_t SP=0x10f000;     // A7 of every fixture before its own pushes
unsigned int calls=0;
const std::uint32_t STARTS[]={0x20c,0x21e,0x224,0x23c,0x242,0x248,0x29c,0x2a4,0x2b6,0x2ce,0xa2c,0xa36,0xa3c,0xa42,0xa46,0xa4c,0xa4e,0xa56,
 0xa5c,0xa62,0xa6c,0xa72,0xa74,0xa82,0xa8a,0xa92,0xa9c,0xaac,0xaba,0xabc,0xacc,0xad0,0xaf4,0xafc,0xb06,0xb0a,0xbbe,0xbc8,0xbca,0xbd4,
 0xbde,0xbec,0xc8c,0xc96,0xc98,0xca0,0xcaa,0xcb0,0xcb6,0xcbe,0xcc4,0xcd0,0xcd6,0xcdc,0xce2,0xcf0,0xd36,0xd42,0xd48,0xd4e,0x3cac,0x3cb2,
 0x3cc6,0x3cd6,0x3cde,0x3ce0,0x3cea,0x3cfa,0x3d06,0x3d08,0x3d16,0x3d1e,0x3d26,0x3d2e,0x3dcc,0x16092,0x166a0,0x16cfa,0x16d0a,0x16d26,
 0x16d3e,0x16d44,0x16d52,0x16d56,0x16d66,0x16d6a,0x16d84,0x16d86,0x16d98,0x16d9a,0x16da4,0x16db6,0x16db8,0x16dc2,0x16dde,0x16dfa,0x16e00,
 0x16e0c,0x16e10,0x16e22,0x16e26,0x16e40,0x16e42,0x16e54,0x16e56,0x16e5e,0x16e70,0x16e72,0x16e7a,0x16e92,0x16e9e,0x187d8,0x187e2,0x187ec,
 0x187f4,0x18be6,0x1adf8,0x1ae1a,0x1ae26,0x1ae32,0x1ae3e,0x48156,0x4815e,0x48166,0x48170,0x48174,0x4817e,0xd2a,0xce6};
const unsigned int START_COUNT=sizeof(STARTS)/sizeof(STARTS[0]);
// FLOW_ONLY (contract carry section) plus the clear run RTS 1669e.
const std::uint32_t FLOW[]={0x21e,0x23c,0x242,0xa4c,0xa72,0xaba,0xacc,0xb06,0xb0a,0xbc8,0xbec,0xc8c,0xc96,0xcb0,0xcbe,0xcc4,0xcd6,0xcdc,
 0xce2,0xd2a,0xd36,0xd48,0x3cac,0x3cde,0x3ce0,0x3d06,0x3dcc,0x16cfa,0x16d52,0x16d66,0x16d84,0x16e0c,0x16e22,0x16e40,0x187d8,0x187e2,
 0x18be6,0x1ae1a,0x1ae26,0x1ae32,0x4817e,0x1669e};
const unsigned int FLOW_COUNT=sizeof(FLOW)/sizeof(FLOW[0]);
const std::uint32_t RANGES[][2]={{0x20c,0x2d8},{0x3dcc,0x3dce},{0xa2c,0xb0c},{0xbbe,0xbee},{0xc8c,0xd56},{0x3cac,0x3d3a},{0x48156,0x48180},
 {0x1adf8,0x1ae56},{0x187d8,0x18be8},{0x16092,0x166bc},{0x16cfa,0x16ea4}};
const unsigned int RANGE_COUNT=sizeof(RANGES)/sizeof(RANGES[0]);
bool in_list(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
bool is_cell(std::uint32_t pc){return pc>=0x18834&&pc<0x18be6&&((pc-0x18834)%0x1e==0||(pc-0x18834)%0x1e==2);}
bool is_run(std::uint32_t pc){return pc>=0x160ae&&pc<=0x1669e&&((0x1669e -pc)&3U)==0;}
bool is_start(std::uint32_t pc){return in_list(STARTS,START_COUNT,pc)||is_cell(pc)||is_run(pc);}
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
struct Out {
    ms5::AnimationMachineDevice dev;Ports ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
    Out():reads(0),status(ms5::AnimationMachineReturned){}
};
void read_of(Out&o,std::uint32_t address,std::uint8_t size,std::uint32_t value){
    ms5::AnimationMachineExternalRead r;r.address=address;r.size=size;r.value=value;o.dev.reads.push_back(r);}
bool run(Bytes&ram,State&s,std::uint32_t stop,Out&o){
    ++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource> w;o.ports.clear();o.error.clear();
    const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);
    if(!ok)std::cerr<<std::hex<<"run error "<<o.error<<" pc "<<s.pc<<" stop "<<stop<<"\n";return ok;}
bool same(const State&a,const State&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
// Failure preserves RAM, registers, the device (queue included) and every output.
void reject(Bytes ram,State s,std::uint32_t stop,const char*message,const std::vector<ms5::AnimationMachineExternalRead>& queue=
    std::vector<ms5::AnimationMachineExternalRead>()){
    const Bytes before=ram;const State old=s;Out o;o.dev.reads=queue;o.reads=99;o.status=ms5::AnimationMachineWaiting;
    ms5::VideoPortWrite marker;marker.address=0xdeadbeef;marker.value=0x87;marker.size=1;o.ports.push_back(marker);
    const ms5::AnimationMachineDevice dev=o.dev;++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource> w;
    const bool ok=ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);
    if(ok){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
    if(o.error!=message)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
    assert(o.error==message&&ram==before&&same(s,old)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&
        o.dev.reads.size()==queue.size()&&o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef);
}
bool port_is(const ms5::VideoPortWrite&p,std::uint32_t address,unsigned int size,std::uint32_t value){
    return p.address==address&&p.size==size&&p.value==value;}
// The default fixture: zero RAM, A5 = 108000, A7 = SP with the return sentinel pushed, distinct register values.
State fixture(Bytes&ram,std::uint32_t pc){
    ram.assign(65536,0);State s;
    for(unsigned int i=0;i<8;++i){s.d[i]=0x11110000U*(i+1)+i;s.a[i]=0x10a000+0x100*i;}
    s.a[5]=0x108000;s.a[7]=SP-4;put(ram,SP-4,4,SENT);s.pc=pc;return s;}
// E2 exception frame at SP: LONG interrupted PC, WORD SR; A7 = SP - 6.
State irq_fixture(Bytes&ram,std::uint32_t vector_pc,std::uint32_t wait_pc,std::uint32_t sr){
    State s=fixture(ram,vector_pc);put(ram,SP-4,4,wait_pc);put(ram,SP-6,2,sr);s.a[7]=SP-6;return s;}
// P1 prep values (scope decision E5).
void prep(Bytes&ram){put(ram,0x10fd80,1,0x80);put(ram,0x100006,4,0x3dcc);put(ram,0x10000a,4,0x3dcc);put(ram,0x10081c,4,0x10081c);
    put(ram,0x100017,1,2);}

// ---- every start: zero-step at the stop PC with each carry tag; interior and odd PCs -----------------------------------------
void block_table(){
    unsigned int cells=0,runs=0;
    for(std::uint32_t pc=0x18834;pc<0x18be6;pc+=2)if(is_cell(pc))++cells;
    for(std::uint32_t pc=0x160ae;pc<=0x1669e;pc+=2)if(is_run(pc))++runs;
    assert(START_COUNT==129&&cells==64&&runs==381&&FLOW_COUNT==42);   // 129 + 64 = 193 block starts (1669e is run entry n = 0)
    unsigned int count=0;
    for(unsigned int r=0;r<RANGE_COUNT;++r)for(std::uint32_t pc=RANGES[r][0];pc<RANGES[r][1];pc+=2) {
        if(!is_start(pc))continue;
        ++count;
        for(unsigned int carry=0;carry<3;++carry){
            Bytes ram;State s=fixture(ram,pc);s.carry=static_cast<ms5::AnimationCarryState>(carry);
            const Bytes before=ram;const State old=s;Out o;assert(run(ram,s,pc,o));
            assert(ram==before&&same(s,old)&&o.ports.empty()&&o.reads==0&&o.status==ms5::AnimationMachineReturned);
        }
    }
    assert(count==193+381);
    for(unsigned int i=0;i<FLOW_COUNT;++i)assert(is_start(FLOW[i]));
}
void interior(){
    unsigned int inside=0;
    for(unsigned int r=0;r<RANGE_COUNT;++r)for(std::uint32_t pc=RANGES[r][0];pc<RANGES[r][1];pc+=2) {
        if(is_start(pc))continue;Bytes ram;State s=fixture(ram,pc);reject(ram,s,SENT,"unsupported animation irq f6a PC");++inside;
    }
    assert(inside==(0xcc+2+0xe0+0x30+0xca+0x8e +0x2a+0x5e +0x410+0x62a+0x1aa)/2-193-381);
    const std::uint32_t odd[]={0x20d,0x3dcd,0xc8d,0x1669f,0x18835,0x16cfb};
    for(unsigned int i=0;i<6;++i){Bytes ram;State s=fixture(ram,odd[i]);reject(ram,s,SENT,"unaligned animation machine PC");}
}
// ---- carry: FLOW blocks keep the incoming C, the others make it Unknown -----------------------------------------------------------
void carry(){
    for(unsigned int c=1;c<3;++c){
        // 3dcc RTS (FLOW): the C reaches the sentinel unchanged.
        Bytes ram;State s=fixture(ram,0x3dcc);s.carry=static_cast<ms5::AnimationCarryState>(c);Out o;assert(run(ram,s,SENT,o));
        assert(s.pc==SENT&&s.carry==c&&s.a[7]==SP);
        // a8a CLR.B + RTS (not FLOW): Unknown.
        s=fixture(ram,0xa8a);s.carry=static_cast<ms5::AnimationCarryState>(c);assert(run(ram,s,SENT,o));
        assert(s.carry==ms5::AnimationCarryUnknown);
        // run entry n = 0 (1669e RTS) is FLOW, n = 1 is not.
        s=fixture(ram,0x1669e);s.carry=static_cast<ms5::AnimationCarryState>(c);s.a[6]=0x3c0000;assert(run(ram,s,SENT,o));assert(s.carry==c&&o.ports.empty());
        s=fixture(ram,0x1669a);s.carry=static_cast<ms5::AnimationCarryState>(c);s.a[6]=0x3c0000;assert(run(ram,s,SENT,o));
        assert(s.carry==ms5::AnimationCarryUnknown&&o.ports.size()==1);
    }
}
// ---- vblank IRQ: 20c -> c0044a, declared resume, 248 -> RTE ------------------------------------------------------------------------
void vblank(){
    for(unsigned int variant=0;variant<4;++variant){
        Bytes ram;const std::uint32_t sr=variant&1?0x2001:0x2000;State s=irq_fixture(ram,0x20c,0xef2,sr);prep(ram);
        put(ram,0x100010,2,0x0005);put(ram,0x104d8e,2,0x7123);put(ram,0x100016,1,variant==2?0xff:0x00);
        const State entry=s;Out o;read_of(o,0x320000,1,variant==3?3:0);
        assert(run(ram,s,0xc0044a,o));
        assert(s.pc==0xc0044a&&s.a[7]==SP-6-60-4-4&&get(ram,s.a[7],4)==0x248&&o.reads==1&&o.dev.reads.empty());
        // stack: 15 LONGs D0..D7 A0..A6 (D0 lowest), WORD 104d8e, WORD 100010
        for(unsigned int i=0;i<8;++i)assert(get(ram,SP-6-60+4*i,4)==entry.d[i]);
        for(unsigned int i=0;i<7;++i)assert(get(ram,SP-6-60+32+4*i,4)==entry.a[i]);
        assert(get(ram,SP-6-60-2,2)==0x7123&&get(ram,SP-6-60-4,2)==0x0005);
        assert(port_is(o.ports[0],0x3c000c,2,6));
        if(variant==2)assert(get(ram,0x100016,1)==0xff&&o.ports.size()==1);
        else assert(get(ram,0x100016,1)==1&&port_is(o.ports[1],0x300001,1,entry.d[0]&255U));
        assert(get(ram,0x100019,1)==0&&s.a[5]==0x108000);
        if(variant==3)assert(get(ram,0x104d7c,1)==3);
        // declared resume (E4): PC := LONG (A7), A7 += 4
        s.pc=get(ram,s.a[7],4);s.a[7]+=4;assert(s.pc==0x248);
        Out p;read_of(p,0x3c0006,2,variant&2?0x0008:0xfff7);put(ram,0x100010,2,0x0009);   // the bank copy at 100010 is restored from the stack
        assert(run(ram,s,0xef2,p));
        assert(s.pc==0xef2&&s.a[7]==SP&&p.reads==1);
        for(unsigned int i=0;i<8;++i)assert(s.d[i]==entry.d[i]);
        for(unsigned int i=0;i<7;++i)assert(s.a[i]==entry.a[i]);
        assert(s.carry==(sr&1?ms5::AnimationCarrySet:ms5::AnimationCarryClear));
        assert(get(ram,0x100010,2)==5&&get(ram,0x104d8e,2)==0x7123&&get(ram,0x100002,1)==(variant&2?0xff:0));
        assert(p.ports.size()==4&&port_is(p.ports[0],0x3c0004,2,0)&&port_is(p.ports[1],0x2ffff2,2,0x6000)&&port_is(p.ports[2],0x2ffff0,2,0)&&
            port_is(p.ports[3],0x3c0000,2,0x7123));
        // the VRAM WORD slot keeps its value; MOVEM.W D0/D7,-(A7) overwrote the popped bank slot
        assert(get(ram,SP-6-60-2,2)==0x7123U);
    }
    // RTE status: S = 0, T = 1 are checked errors (state and queue preserved)
    const std::uint32_t bad[]={0x0000,0xa000,0x8700};
    for(unsigned int i=0;i<3;++i){Bytes ram;State s=irq_fixture(ram,0x2ce,0xef2,bad[i]);reject(ram,s,0xef2,"unsupported animation irq RTE status");}
    // game mode clear: JMP c00438 (BIOS INT1 boundary, unrouted)
    {Bytes ram;State s=irq_fixture(ram,0x20c,0xef2,0x2000);Out o;assert(run(ram,s,0xc00438,o));assert(o.ports.size()==1&&s.a[7]==SP-6);
     s=irq_fixture(ram,0x20c,0xef2,0x2000);reject(ram,s,0xef2,"unsupported animation machine PC");}
    // live callback: JSR (A0) with A0 = LONG 100006
    {Bytes ram;State s=irq_fixture(ram,0x20c,0xef2,0x2000);prep(ram);put(ram,0x100006,4,0x12346);Out o;assert(run(ram,s,0x12346,o));
     assert(s.a[0]==0x12346&&get(ram,s.a[7],4)==0x23c);
     s=irq_fixture(ram,0x20c,0xef2,0x2000);prep(ram);put(ram,0x100006,4,0x12347);reject(ram,s,0xef2,"unaligned animation machine PC");}
    // re-entry: 100019 bit 7 set -> c96 RTS, no watchdog, no 320000 read
    {Bytes ram;State s=irq_fixture(ram,0x20c,0xef2,0x2000);prep(ram);put(ram,0x100019,1,0x80);Out o;assert(run(ram,s,0xc0044a,o));
     assert(o.ports.size()==1&&o.reads==0&&get(ram,0x100019,1)==0x80);}
    // render path: JSR 72fa (F6b boundary); 10f001 bit 4 ports 3a0011 / 3a0001
    {Bytes ram;State s=irq_fixture(ram,0x20c,0xef2,0x2000);prep(ram);put(ram,0x10001b,1,0x80);Out o;assert(run(ram,s,0x72fa,o));
     assert(get(ram,s.a[7],4)==0xcc4);}
    {Bytes ram;State s=irq_fixture(ram,0x20c,0xef2,0x2000);prep(ram);put(ram,0x10f001,1,0x10);Out o;read_of(o,0x320000,1,1);
     assert(run(ram,s,0xc0044a,o));
     bool seen=false;for(unsigned int i=0;i<o.ports.size();++i)if(o.ports[i].address==0x3a0001)seen=true;assert(seen);}
    // empty 320000 queue
    {Bytes ram;State s=irq_fixture(ram,0x20c,0xef2,0x2000);prep(ram);reject(ram,s,0xc0044a,"animation machine external read queue empty");}
}
void raster(){
    // bit 7 clear: 2ce
    {Bytes ram;State s=irq_fixture(ram,0x29c,0x1234,0x2001);Out o;assert(run(ram,s,0x1234,o));
     assert(s.a[7]==SP&&s.carry==ms5::AnimationCarrySet&&o.ports.size()==1&&port_is(o.ports[0],0x3c000c,2,2));}
    // bit 7 set: 2a4 -> 3dcc -> 2b6
    {Bytes ram;State s=irq_fixture(ram,0x29c,0x1234,0x2000);prep(ram);put(ram,0x104d8e,2,0x4567);const State entry=s;Out o;
     assert(run(ram,s,0x1234,o));
     assert(s.a[7]==SP&&s.a[5]==entry.a[5]&&s.carry==ms5::AnimationCarryClear&&get(ram,0x104d8e,2)==0x4567);
     assert(o.ports.size()==2&&port_is(o.ports[0],0x3c000c,2,2)&&port_is(o.ports[1],0x3c0000,2,0x4567));}
    {Bytes ram;State s=irq_fixture(ram,0x29c,0x1234,0x2000);prep(ram);put(ram,0x10000a,4,0x5554);Out o;assert(run(ram,s,0x5554,o));
     assert(s.a[5]==0x5554&&get(ram,s.a[7],4)==0x2b6&&get(ram,s.a[7]+6,4)==0x108000);}
}
// ---- credit -----------------------------------------------------------------------------------------------------------------------
std::uint32_t bcd_minus_one(std::uint32_t v){   // SBCD #1 (X = 0) by nibbles
    int lo=static_cast<int>(v&15U)-1,hi=static_cast<int>(v>>4);if(lo<0){lo-=6;--hi;}if(hi<0)hi-=6;
    return ((static_cast<std::uint32_t>(hi)&15U)<<4)|(static_cast<std::uint32_t>(lo)&15U);}
void credit(){
    for(std::uint32_t v=0;v<256;++v){
        Bytes ram;State s=fixture(ram,0xa62);s.a[0]=0x100004;s.d[1]=0;s.d[7]=0xabcdef00U|v;Out o;assert(run(ram,s,SENT,o));
        assert((s.d[7]&255U)==bcd_minus_one(v)&&get(ram,0x100004,1)==bcd_minus_one(v)&&(s.d[7]>>8)==0xabcdefU&&(s.d[6]&0xffffU)==1);
    }
    // a2c: D0 bit i requested and the credit byte nonzero -> bit 1 set (two passes, LSR.B)
    {Bytes ram;State s=fixture(ram,0xa2c);put(ram,0x100004,1,1);put(ram,0x100005,1,0);s.d[0]=0x12345603;Out o;assert(run(ram,s,SENT,o));
     assert((s.d[0]&255U)==0x01&&s.a[0]==0x100007&&(s.d[1]&0xffffU)==0xffff);}
    // a4e: LSR.W; requested nonzero credit decremented (BCD)
    {Bytes ram;State s=fixture(ram,0xa4e);put(ram,0x100004,1,0x10);put(ram,0x100005,1,0x01);s.d[0]=0x12340103;Out o;assert(run(ram,s,SENT,o));
     assert(get(ram,0x100004,2)==0x0900&&(s.d[0]&0xffffU)==0x0040&&s.a[0]==0x100006);}
    // bbe with 100014 = 3, 10fdaf = 2 -> abc -> a2c -> ad0 -> af4 -> a4e
    {Bytes ram;State s=fixture(ram,0xbbe);put(ram,0x100014,1,3);put(ram,0x10fdaf,1,2);put(ram,0x10f004,1,0xff);put(ram,0x10f007,1,0x0f);
     put(ram,0x10f006,1,0x0c);put(ram,0x100004,1,0x21);put(ram,0x100005,1,0x00);Out o;assert(run(ram,s,SENT,o));
     // a2c pass 1: bit 0 set, credit 21 -> 20 (no borrow) -> ORI #2; pass 2: bit 0 set, credit 00 borrows -> D0.B = 1;
     // ad0: 1 & ff & 0f = 1 -> 10f006 = 0d, 10fdb4 = 1, 10fdaf = 2; a4e: bit 0 -> credit 21 SBCD -> 20; bde: 100014 &= fe.
     assert(get(ram,0x10fdb4,1)==1&&get(ram,0x10f006,1)==0x0d&&get(ram,0x10fdaf,1)==2&&get(ram,0x100014,1)==2&&
         get(ram,0x100004,1)==0x20&&(s.d[1]&0xffffU)==0xffff);}
    // 10fdaf = 0 / 3 -> a8a clears 10fdb4; 10fd82 nonzero -> bc8
    for(std::uint32_t f=0;f<4;f+=3){Bytes ram;State s=fixture(ram,0xbbe);put(ram,0x100014,1,0x81);put(ram,0x10fdaf,1,f);Out o;assert(run(ram,s,SENT,o));
     assert(get(ram,0x10fdb4,1)==0&&get(ram,0x100014,1)==0x81);}
    {Bytes ram;State s=fixture(ram,0xbbe);put(ram,0x10fd82,1,1);put(ram,0x100014,1,3);Out o;assert(run(ram,s,SENT,o));assert(get(ram,0x100014,1)==3);}
    // 10fdaf = 1: 10fdb4 & 10f004 nonzero -> aac
    {Bytes ram;State s=fixture(ram,0xa74);put(ram,0x10fdaf,1,1);put(ram,0x10fdb4,1,6);put(ram,0x10f004,1,4);Out o;assert(run(ram,s,SENT,o));
     assert(get(ram,0x10fdb4,1)==0&&get(ram,0x10fdaf,1)==2&&(s.d[0]&255U)==4);}
}
// ---- service tail, task restore -------------------------------------------------------------------------------------------------------
void service(){
    // cc4 entry, sprite flush idle (d3d bit 7 clear), task queue empty, sound idle: ports 320000 command from the empty ring path
    {Bytes ram;State s=fixture(ram,0xcc4);put(ram,0x10081c,4,0x10081c);put(ram,0x10f001,1,0x10);put(ram,0x104d74,2,1);put(ram,0x104d76,2,1);
     Out o;read_of(o,0x320000,1,0);assert(run(ram,s,SENT,o));
     assert(o.ports.size()==6&&port_is(o.ports[0],0x3a0011,1,0)&&port_is(o.ports[1],0x2ffff2,2,0x2000)&&
         port_is(o.ports[3],0x2ffff2,2,0x1000)&&port_is(o.ports[5],0x3a0001,1,0)&&o.reads==1);
     assert(s.carry==ms5::AnimationCarryUnknown&&get(ram,0x100019,1)==0&&s.a[6]==0x10081c);}
    // one task frame at 1007dc: registers restored, 10081c advanced, PC -> 3dcc -> d2a -> ce6 -> d36
    {Bytes ram;State s=fixture(ram,0xcc4);const std::uint32_t f=0x1007dc;put(ram,0x10081c,4,f);
     for(unsigned int r=0;r<14;++r)put(ram,f+4*r,4,r==13?0x108000:0x01010101U*(r+1));put(ram,f+56,4,0x10c000);put(ram,f+60,4,0x3dcc);
     Out o;read_of(o,0x320000,1,1);assert(run(ram,s,0xd36,o));
     for(unsigned int i=0;i<8;++i)assert(s.d[i]==0x01010101U*(i+1));
     for(unsigned int i=0;i<5;++i)assert(s.a[i]==0x01010101U*(i+9));
     assert(s.a[5]==0x108000&&s.a[6]==0x10081c&&get(ram,0x10081c,4)==0x10081c&&s.a[7]==SP-4&&get(ram,SP-8,4)==0xd2a&&o.reads==0);
     assert(o.ports.size()==7&&port_is(o.ports[4],0x300001,1,0)&&port_is(o.ports[5],0x2ffff2,2,0x1000));}
    // task PC live (left to the routing)
    {Bytes ram;State s=fixture(ram,0xcf0);s.a[6]=0x1007dc;put(ram,0x1007dc+52,4,0x108000);put(ram,0x1007dc+56,4,0x10c000);put(ram,0x1007dc+60,4,0x22222);
     Out o;assert(run(ram,s,0x22222,o));assert(s.a[6]==0x10c000&&get(ram,s.a[7],4)==0xd2a&&get(ram,0x10081c,4)==0x10081c);
     assert(o.ports.size()==3&&port_is(o.ports[0],0x300001,1,0)&&s.d[0]==0&&s.a[5]==0x108000);}
    // watchdog saturation: 100016 = ff -> caa, = fe -> ca0
    for(std::uint32_t v=0xfe;v<=0xff;++v){Bytes ram;State s=fixture(ram,0xc98);put(ram,0x100016,1,v);Out o;assert(run(ram,s,0xbbe,o));
     assert(get(ram,0x100016,1)==0xff&&o.ports.size()==(v==0xfe?1U:0U));}
}
// ---- Z80 and sound timer --------------------------------------------------------------------------------------------------------------
void z80(){
    // pending (104d7b bit 7) -> 3 ; reply 1 -> nothing ; 10f003 bit 7 -> 7f
    {Bytes ram;State s=fixture(ram,0x3cb2);put(ram,0x104d7b,1,0x80);Out o;read_of(o,0x320000,1,0x42);assert(run(ram,s,SENT,o));
     assert(get(ram,0x104d7c,1)==0x42&&get(ram,0x104d7b,1)==0&&get(ram,0x104d7a,1)==0xff&&o.ports.size()==1&&port_is(o.ports[0],0x320000,1,3));}
    {Bytes ram;State s=fixture(ram,0x3cb2);Out o;read_of(o,0x320000,1,1);assert(run(ram,s,SENT,o));assert(o.ports.empty()&&(s.d[0]&255U)==1);}
    {Bytes ram;State s=fixture(ram,0x3cb2);put(ram,0x10f003,1,0x81);Out o;read_of(o,0x320000,1,0);assert(run(ram,s,SENT,o));
     assert(get(ram,0x10f003,1)==1&&port_is(o.ports[0],0x320000,1,0x7f));}
    // ring: duplicates skipped, wrap at 7f
    {Bytes ram;State s=fixture(ram,0x3cb2);for(unsigned int i=0;i<0x80;++i)put(ram,0x104cf4+i,1,i<0x7d?i:0x55);put(ram,0x104cf4,1,0x55);put(ram,0x104cf5,1,0x66);
     put(ram,0x104d74,2,0x7d);put(ram,0x104d76,2,0x20);Out o;read_of(o,0x320000,1,0);assert(run(ram,s,SENT,o));
     assert(get(ram,0x104d74,2)==1&&port_is(o.ports[0],0x320000,1,0x55)&&(s.d[1]&0xffffU)==1);}
    {Bytes ram;State s=fixture(ram,0x3cb2);put(ram,0x104d74,2,0x10);put(ram,0x104d76,2,0x13);for(unsigned int i=0;i<4;++i)put(ram,0x104d04+i,1,7);
     Out o;read_of(o,0x320000,1,0);assert(run(ram,s,SENT,o));assert(get(ram,0x104d74,2)==0x13&&port_is(o.ports[0],0x320000,1,7));}
    // queue: WORD 320000 is not a queue device; the BYTE needs the matching front entry
    {Bytes ram;State s=fixture(ram,0x3cb2);std::vector<ms5::AnimationMachineExternalRead> q(1);q[0].address=0x320000;q[0].size=2;q[0].value=0;
     reject(ram,s,SENT,"animation machine external read queue mismatch",q);}
    // timer: 0 -> RTS ; 1..f -> +1 ; 10 / negative -> 0 or +1 ; JSR 3af8 with D0.W = 19c0 + old
    const std::uint32_t t[]={1,0xf,0x10,0xffff,0x7fff};
    for(unsigned int i=0;i<5;++i){Bytes ram;State s=fixture(ram,0x48156);put(ram,0x10d68c,2,t[i]);Out o;assert(run(ram,s,0x3af8,o));
     const std::int32_t sv=t[i]>=0x8000?static_cast<std::int32_t>(t[i])-0x10000:static_cast<std::int32_t>(t[i]);
     const std::uint32_t d0=sv<=15?t[i]:0;
     assert(get(ram,0x10d68c,2)==(sv<=15?((t[i]+1)&0xffffU):0U)&&(s.d[0]&0xffffU)==((d0+0x19c0)&0xffffU)&&get(ram,s.a[7],4)==0x4817e);}
    {Bytes ram;State s=fixture(ram,0x48156);Out o;assert(run(ram,s,SENT,o));assert(s.a[7]==SP);}
}
// ---- columns -------------------------------------------------------------------------------------------------------------------------
void columns(){
    Bytes ram;State s=fixture(ram,0x1adf8);const std::uint32_t obj=0x109156;
    put(ram,obj+0x7a,1,0x81);put(ram,obj+0x26,2,0x0123);put(ram,obj+0x7c,2,0x0140);put(ram,obj+0x7e,2,0x0011);
    for(unsigned int k=0;k<32;++k)put(ram,obj+0x3a+2*k,2,0x100+k);
    put(ram,0x10b1d6+0x7a,1,0x80);put(ram,0x10d256+0x7a,1,0x01);put(ram,0x10d2d6+0x7a,1,0x81);put(ram,0x10d2d6+0x26,2,0x8000);
    Out o;assert(run(ram,s,SENT,o));
    assert(o.ports.size()==2+64+2&&get(ram,obj+0x7a,1)==1&&get(ram,0x10d2d6+0x7a,1)==1&&get(ram,0x100010,2)==0);
    std::uint32_t d6=(((0x0123U+0x8401U)&0xffffU)<<16)|((0x0140U<<7)&0xffffU),d7=((0x0123U+0x8201U)&0xffffU)<<16;
    const std::uint32_t d0=(0x0011U<<7)&0xffffU;
    for(unsigned int k=0;k<32;++k){
        d7=(d7&0xffff0000U)|d0;d6=(d6&0xffff0000U)|((d6+0x400U)&0xffffU);
        if(0xa000U>(d6&0xffffU))d7=(d7&0xffff0000U)|((d7+0x100U+k)&0xffffU);
        d6=(d6&0xffff0000U)|((d6-0x400U)&0xffffU);
        assert(port_is(o.ports[2+2*k],0x3c0000,4,d6));d6+=0x10000U;d6=(d6&0xffff0000U)|((d6+0x800U)&0xffffU);
        assert(port_is(o.ports[3+2*k],0x3c0000,4,d7));d7+=0x10000U;
    }
}
// ---- sprite flush and clear runs ------------------------------------------------------------------------------------------------------
void runs(){
    for(unsigned int n=0;n<381;++n){
        Bytes ram;State s=fixture(ram,0x1669e -4*n);s.a[6]=0x3c0000;s.d[0]=0x7e000000U+n;s.d[2]=0x10000;Out o;assert(run(ram,s,SENT,o));
        assert(o.ports.size()==n&&s.d[0]==0x7e000000U+n+0x10000U*n&&s.pc==SENT);
        for(unsigned int i=0;i<n;++i)assert(port_is(o.ports[i],0x3c0000,4,0x7e000000U+n+0x10000U*i));
        // the same entry through 16092 (D1 = n) and 166a0 (D1 = -n)
        s=fixture(ram,0x16092);s.a[6]=0x3c0000;s.d[0]=0x5555abcdU;s.d[1]=0xffff0000U|n;assert(run(ram,s,SENT,o));
        assert(o.ports.size()==n&&s.d[2]==0x10000&&s.a[1]==0x1669e&&(s.d[1]&0xffffU)==((0x10000U-4*n)&0xffffU));
        if(n)assert(port_is(o.ports[0],0x3c0000,4,(((0xabcdU+0x8201U)&0xffffU)<<16)|0x8000U));
        s=fixture(ram,0x166a0);s.a[6]=0x3c0000;s.d[0]=0x5555abcdU;s.d[1]=(0x10000U-n)&0xffffU;assert(run(ram,s,SENT,o));
        assert(o.ports.size()==n&&s.d[2]==0xffff0000U);
        if(n)assert(port_is(o.ports[n-1],0x3c0000,4,(((((0xabcdU+0x8200U)&0xffffU)<<16)|0x8000U)-0x10000U*(n-1))));
    }
    // A6 not the video port: ordinary RAM LONG writes
    {Bytes ram;State s=fixture(ram,0x1669e -8);s.a[6]=0x10a100;s.d[0]=0x01020304;s.d[2]=0x1000;Out o;assert(run(ram,s,SENT,o));
     assert(o.ports.empty()&&get(ram,0x10a100,4)==0x01021304);}
    // targets outside the run: 160aa (n = 381) / 166a2 (D1 = -1) are interior PCs of this unit
    {Bytes ram;State s=fixture(ram,0x16092);s.d[1]=381;reject(ram,s,SENT,"unsupported animation irq f6a PC");
     s=fixture(ram,0x16092);s.d[1]=0xffff;reject(ram,s,SENT,"unsupported animation irq f6a PC");}
}
void sprite(){
    // idle: d3d bit 7 clear -> C clear
    {Bytes ram;State s=fixture(ram,0x16cfa);s.carry=ms5::AnimationCarrySet;Out o;assert(run(ram,s,SENT,o));
     assert(s.carry==ms5::AnimationCarryClear&&o.ports.empty()&&s.a[5]==0x108000);}
    // forward, queue empty: n = 5 - max(0, 3) = 2 and n = 4 - max(1, -1) = 3
    {Bytes ram;State s=fixture(ram,0x16cfa);put(ram,0x108d3d,1,0x80);put(ram,0x108d3c,1,0x80);put(ram,0x108d36,2,0x22);put(ram,0x108d34,2,0x22);
     put(ram,0x108d3e,2,0);put(ram,0x108d40,2,5);put(ram,0x108d44,2,3);put(ram,0x108d46,2,1);put(ram,0x108d48,2,4);put(ram,0x108d4c,2,0xffff);
     const State entry=s;Out o;assert(run(ram,s,SENT,o));
     assert(o.ports.size()==2+3+2&&s.carry==ms5::AnimationCarrySet&&s.a[6]==entry.a[6]&&s.a[7]==SP&&get(ram,0x108d3c,1)==0&&get(ram,0x108d3d,1)==0);
     assert(get(ram,0x108d42,2)==0&&get(ram,0x108d4a,2)==1&&port_is(o.ports[5],0x2ffff2,2,0x1000));}
    // backward, queue empty: n = min(4, 2) - 0 = 2 ... after 16dde copies WORD 2 to WORD 6
    {Bytes ram;State s=fixture(ram,0x16cfa);put(ram,0x108d3d,1,0x80);put(ram,0x108d3e,2,0);put(ram,0x108d40,2,6);put(ram,0x108d42,2,2);
     Out o;assert(run(ram,s,SENT,o));assert(o.ports.size()==2+2&&get(ram,0x108d44,2)==6&&get(ram,0x108d3c,1)==0x80);}
    // queue entry: writer table targets (F6c boundary), forward and backward, ring wraps
    {Bytes ram;State s=fixture(ram,0x16cfa);put(ram,0x108d3d,1,0x80);put(ram,0x108d3c,1,0x80);put(ram,0x108d34,2,0x1fe);put(ram,0x108d36,2,0);
     put(ram,0x108d32,2,0x0100);put(ram,0x108034+4,2,0x1234);put(ram,0x108034+6,2,0x0007);Out o;assert(run(ram,s,0xf226+4*(4|3),o));
     assert(s.a[0]==0x108b34&&s.a[2]==0x108034&&s.a[4]==0x108d46&&(s.d[1]&0xffffU)==3&&get(ram,s.a[7],4)==0x16d84&&s.a[3]==0xf226);}
    {Bytes ram;State s=fixture(ram,0x16cfa);put(ram,0x108d3d,1,0x80);put(ram,0x108d34,2,0x10);put(ram,0x108d36,2,0);
     put(ram,0x108d32,2,0xfff0);put(ram,0x107f24+4,2,0xffff);put(ram,0x107f24+6,2,0x00f2);Out o;assert(run(ram,s,0x13b46+4*0xf2,o));
     assert(s.a[1]==0x108d32&&s.a[2]==0x107f24&&s.a[4]==0x108d3e&&get(ram,s.a[7],4)==0x16e40);}
}
}
int main(){
    block_table();interior();carry();vblank();raster();credit();service();z80();columns();runs();sprite();
    std::printf("animation_machine_irq_f6a_test: %u runs ok\n",calls);
    return 0;
}
