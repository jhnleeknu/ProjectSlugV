#include "ms5/animation_machine_irq.h"
#include "ms5/palette_transfer.h"
#include <cassert>
#include <cstdio>
#include <iostream>
#include <string>
// F6b IRQ palette transfer 72fa..8b64 (522 block starts = 10 unique + 512 cell blocks; contract
// docs/analysis/animation-machine-irq-f6b-contract.md, scope decision E6 as decided) through run_animation_machine_with_palette and
// run_animation_machine (no palette device). Inputs are declared work RAM fixtures (F6b reads no ROM data). Expectations are written
// from the original instructions in this file; the host-level transfer_palette_banks is an independent oracle (scope decision E8) and
// the native Unicorn comparison is the V1 spec tools/unit_fixture_specs/f6b.py.
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef ms5::AnimationMachineState State;
typedef ms5::AnimationMachinePaletteRam Palette;
typedef std::vector<ms5::VideoPortWrite> Ports;
const std::uint32_t SENT=0xc00500;   // return sentinel (stop)
const std::uint32_t SP=0x10f000;     // A7 of every fixture before its own pushes
const std::uint32_t STAGING=0x105da2,FILL=0x107da2,COUNTER=0x107dea,DISPLAY=0x107dec,PENDING=0x107ded;
unsigned int calls=0;
const std::uint32_t UNIQUE[]={0x72fa,0x7302,0x730c,0x7326,0x871a,0x8720,0x8728,0x8732,0x8738,0x873a,0x8b5c,0x8b60};
const unsigned int UNIQUE_COUNT=sizeof(UNIQUE)/sizeof(UNIQUE[0]);
// FLOW (contract carry section): 7302, 7326, every cell test / copy block, 8738, 8b60.
bool in_list(const std::uint32_t*list,unsigned int n,std::uint32_t pc){for(unsigned int i=0;i<n;++i)if(list[i]==pc)return true;return false;}
std::uint32_t cell_test(std::uint32_t k){return 0x732e + 0x14*(k-1);}          // k = 1..255
std::uint32_t cell_copy(std::uint32_t k){return k==0?0x7326:cell_test(k)+8;}  // k = 0..255
bool is_cell(std::uint32_t pc){return pc>=0x732e&&pc<0x871a&&((pc-0x732e)%0x14==0||(pc-0x732e)%0x14==8);}
bool is_start(std::uint32_t pc){return in_list(UNIQUE,UNIQUE_COUNT,pc)||is_cell(pc);}
bool is_flow(std::uint32_t pc){return pc==0x7302||pc==0x8738||pc==0x8b60||(pc>=0x7326&&pc<0x871a);}
void put(Bytes&b,std::uint32_t a,unsigned int n,std::uint32_t v){for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
std::uint32_t get(const Bytes&b,std::uint32_t a,unsigned int n){std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;}
std::uint32_t lcg(std::uint32_t& x){x=x*1103515245U+12345U;return x>>8;}
struct Out {
    ms5::AnimationMachineDevice dev;Ports ports;std::uint32_t reads;ms5::AnimationMachineStatus status;std::string error;
    Out():reads(0),status(ms5::AnimationMachineReturned){}
};
bool run(Bytes&ram,State&s,Palette&p,std::uint32_t stop,Out&o){
    ++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource> w;o.ports.clear();o.error.clear();
    const bool ok=ms5::run_animation_machine_with_palette(ram,w,bus,s,o.dev,p,stop,0,o.reads,o.status,o.ports,o.error);
    if(!ok){std::cerr<<std::hex<<"run error "<<o.error<<" pc "<<s.pc<<" stop "<<stop<<"\n";}
    return ok;}
bool run_plain(Bytes&ram,State&s,std::uint32_t stop,Out&o){
    ++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource> w;o.ports.clear();o.error.clear();
    return ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);}
bool same(const State&a,const State&b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;return a.pc==b.pc&&a.carry==b.carry;}
bool same_palette(const Palette&a,const Palette&b){return a.banks[0]==b.banks[0]&&a.banks[1]==b.banks[1]&&a.selected==b.selected;}
// Failure preserves RAM, registers, the device, the palette and every output. with_palette false: run_animation_machine.
void reject(Bytes ram,State s,Palette p,std::uint32_t stop,const char*message,bool with_palette=true){
    const Bytes before=ram;const State old=s;const Palette old_p=p;Out o;o.reads=99;o.status=ms5::AnimationMachineWaiting;
    ms5::VideoPortWrite marker;marker.address=0xdeadbeef;marker.value=0x87;marker.size=1;o.ports.push_back(marker);
    const ms5::AnimationMachineDevice dev=o.dev;++calls;ms5::ProgramBusState bus;std::vector<ms5::FixedDataResource> w;
    const bool ok=with_palette?ms5::run_animation_machine_with_palette(ram,w,bus,s,o.dev,p,stop,0,o.reads,o.status,o.ports,o.error):
        ms5::run_animation_machine(ram,w,bus,s,o.dev,stop,0,o.reads,o.status,o.ports,o.error);
    if(ok){std::cerr<<std::hex<<"unexpected success "<<old.pc<<" stop "<<stop<<"\n";assert(false);}
    if(o.error!=message)std::cerr<<std::hex<<old.pc<<": "<<o.error<<" expected "<<message<<"\n";
    assert(o.error==message&&ram==before&&same(s,old)&&same_palette(p,old_p)&&dev.pvc==o.dev.pvc&&dev.bank_base==o.dev.bank_base&&o.reads==99&&
        o.status==ms5::AnimationMachineWaiting&&o.ports.size()==1&&o.ports[0].address==0xdeadbeef);
}
bool port_is(const ms5::VideoPortWrite&p,std::uint32_t address,unsigned int size,std::uint32_t value){
    return p.address==address&&p.size==size&&p.value==value;}
// The default fixture: zero RAM, A5 = 108000, A7 = SP with the return sentinel pushed, distinct register values.
State fixture(Bytes&ram,std::uint32_t pc){
    ram.assign(65536,0);State s;
    for(unsigned int i=0;i<8;++i){s.d[i]=0x11110000U*(i+1)+i;s.a[i]=0x10a000+0x100*i;}
    s.a[5]=0x108000;s.a[7]=SP-4;put(ram,SP-4,4,SENT);s.pc=pc;return s;}
// Distinct palette / staging / fill pattern contents.
void fill_palette(Palette&p,std::uint32_t seed){for(unsigned int b=0;b<2;++b)for(unsigned int i=0;i<8192;++i)p.banks[b][i]=static_cast<std::uint8_t>(lcg(seed));}
void fill_staging(Bytes&ram,std::uint32_t seed,bool clear_marks){
    for(unsigned int i=0;i<8192;++i)ram[(STAGING+i)&65535U]=static_cast<std::uint8_t>(lcg(seed));
    if(clear_marks)for(unsigned int k=0;k<256;++k)ram[(STAGING+0x20*k)&65535U]&=0x7fU;
    for(unsigned int i=0;i<32;++i)ram[(FILL+i)&65535U]=static_cast<std::uint8_t>(lcg(seed));
}

// ---- every start: zero-step at the stop PC with each carry tag (both entry points); interior and odd PCs --------------------------
void block_table(){
    unsigned int cells=0,count=0,flow=0;
    for(std::uint32_t pc=0x72fa;pc<0x8b64;pc+=2)if(is_cell(pc))++cells;
    assert(UNIQUE_COUNT==12&&cells==510);   // 12 named starts (7326 and 871a are the cell-rule ends) + 510 = 522
    for(std::uint32_t pc=0x72fa;pc<0x8b64;pc+=2) {
        if(!is_start(pc))continue;
        ++count;if(is_flow(pc))++flow;
        for(unsigned int carry=0;carry<3;++carry){
            Bytes ram;State s=fixture(ram,pc);s.carry=static_cast<ms5::AnimationCarryState>(carry);Palette p;fill_palette(p,pc);
            const Bytes before=ram;const State old=s;const Palette old_p=p;Out o;assert(run(ram,s,p,pc,o));
            assert(ram==before&&same(s,old)&&same_palette(p,old_p)&&o.ports.empty()&&o.reads==0&&o.status==ms5::AnimationMachineReturned);
            assert(run_plain(ram,s,pc,o)&&ram==before&&same(s,old)&&o.ports.empty());
        }
    }
    assert(count==522&&flow==514);
}
void interior(){
    unsigned int inside=0;
    for(std::uint32_t pc=0x72fa;pc<0x8b64;pc+=2) {
        if(is_start(pc))continue;
        Bytes ram;State s=fixture(ram,pc);Palette p;
        reject(ram,s,p,SENT,"unsupported animation irq f6b PC");reject(ram,s,p,SENT,"unsupported animation irq f6b PC",false);++inside;
    }
    assert(inside==(0x8b64-0x72fa)/2-522);
    // 873a block interior: the 256 MOVEM.L D0-D7,-(A0) PCs 8752..8b4e (plus the four set-up PCs) are inside it.
    for(std::uint32_t pc=0x8752;pc<0x8b52;pc+=4)assert(!is_start(pc));
    const std::uint32_t odd[]={0x72fb,0x7327,0x732f,0x871b,0x873b,0x8b61};
    for(unsigned int i=0;i<6;++i){Bytes ram;State s=fixture(ram,odd[i]);Palette p;reject(ram,s,p,SENT,"unaligned animation machine PC");}
    // The neighbours stay outside: 72f0 is stage entry (routed); 8b64 is routed by controller C3a since the merge, so the unrouted
    // probe is the work-RAM PC 10fe00 (repository convention for boundary probes).
    {Bytes ram;State s=fixture(ram,0x10fe00);Palette p;reject(ram,s,p,SENT,"unsupported animation machine PC");}
}
// ---- carry: FLOW blocks keep the incoming C, the others make it Unknown -----------------------------------------------------------
void carry(){
    for(unsigned int cv=1;cv<3;++cv){
        const ms5::AnimationCarryState in=static_cast<ms5::AnimationCarryState>(cv);
        // 7302 (pending clear -> 871a), 8738 RTS, 8b60 BRA: FLOW.
        {Bytes ram;State s=fixture(ram,0x7302);s.carry=in;Palette p;Out o;assert(run(ram,s,p,0x871a,o)&&s.carry==in);}
        {Bytes ram;State s=fixture(ram,0x7302);s.carry=in;put(ram,PENDING,1,0x80);Palette p;Out o;assert(run(ram,s,p,0x730c,o)&&s.carry==in);}
        {Bytes ram;State s=fixture(ram,0x8738);s.carry=in;Palette p;Out o;assert(run(ram,s,p,SENT,o)&&s.carry==in&&s.a[7]==SP);}
        {Bytes ram;State s=fixture(ram,0x8b60);s.carry=in;Palette p;Out o;assert(run(ram,s,p,0x8720,o)&&s.carry==in);}
        // cell 0 copy, cell 7 test (both outcomes) and copy: FLOW across the whole cell chain.
        {Bytes ram;State s=fixture(ram,0x7326);s.carry=in;s.a[0]=STAGING;s.a[1]=0x400000;put(ram,STAGING+0x20*7,1,0x80);Palette p;Out o;
         assert(run(ram,s,p,cell_test(9),o)&&s.carry==in);}
        // 72fa / 730c / 871a / 8720 / 8728 / 8732 / 873a / 8b5c: Unknown.
        const std::uint32_t unknown[]={0x72fa,0x730c,0x871a,0x8720,0x8728,0x8732,0x873a,0x8b5c};
        const std::uint32_t stop[]={0x7302,0x732e,0x8720,0x8728,0x8738,0x8738,0x8b5c,0x8b60};
        for(unsigned int i=0;i<8;++i){
            Bytes ram;State s=fixture(ram,unknown[i]);s.carry=in;Palette p;
            if(unknown[i]==0x8732)put(ram,DISPLAY,1,1);
            if(unknown[i]==0x873a)put(ram,COUNTER,2,0x2000);
            if(unknown[i]==0x8b5c)s.a[0]=0x400000;
            Out o;assert(run(ram,s,p,stop[i],o)&&s.carry==ms5::AnimationCarryUnknown);
        }
    }
}
// ---- every cell entry: staging block k dirty only, entered at its test block (k >= 1; k = 0 via 730c) and at its copy block ------
void cells(){
    for(std::uint32_t k=0;k<256;++k){
        Bytes ram;State s=fixture(ram,k==0?0x730c:cell_test(k));fill_staging(ram,0x1234+k,true);s.a[0]=STAGING;s.a[1]=0x400000;
        put(ram,STAGING+0x20*k,1,get(ram,STAGING+0x20*k,1)|0x80U);
        Palette p;fill_palette(p,0x55+k);p.selected=k&1U;const Palette before=p;const Bytes ram0=ram;
        Out o;assert(run(ram,s,p,0x871a,o));
        const unsigned int bank=k==0?0:(k&1U);
        assert(p.selected==bank&&s.pc==0x871a&&s.a[0]==STAGING&&s.a[1]==0x400000);
        if(k==0){assert(o.ports.size()==1&&port_is(o.ports[0],0x3a000f,1,0x11110000U&255U));}else assert(o.ports.empty());
        for(unsigned int b=0;b<2;++b)for(unsigned int i=0;i<8192;++i){
            const bool target=b==bank&&i/32==k;
            std::uint32_t want=before.banks[b][i];
            if(target)want=ram0[(STAGING+i)&65535U]&(i%32==0?0x7fU:0xffU);
            if(target&&k==0&&i<2)want=0;           // 730c ANDI.W #8000,(A0) then BCLR #7,(A0)
            assert(p.banks[b][i]==want);
        }
        assert(get(ram,STAGING+0x20*k,1)==(k==0?0U:(ram0[(STAGING+0x20*k)&65535U]&0x7fU)));
        for(unsigned int r=0;r<8;++r)assert(s.d[r]==get(ram,STAGING+0x20*k+4*r,4));
        // the copy block itself, entered directly (bit 7 not consulted)
        Bytes ram2=ram0;State t=fixture(ram2,cell_copy(k));fill_staging(ram2,0x777+k,false);t.a[0]=STAGING;t.a[1]=0x400000;Palette q;q.selected=1;
        const Bytes ram2_0=ram2;
        assert(run(ram2,t,q,k==255?0x871a:cell_test(k+1),o));
        for(unsigned int i=0;i<32;++i)assert(q.banks[1][0x20*k+i]==ram2_0[(STAGING+0x20*k+i)&65535U]&&q.banks[0][0x20*k+i]==0);
        assert(ram2==ram2_0&&t.pc==(k==255?0x871aU:cell_test(k+1)));
    }
}
// ---- full transfer 72fa -> RTS: oracle transfer_palette_banks (counter 0 / 2000), dirty patterns, display bank, palette bank --------
void oracle_case(std::uint32_t seed,std::uint32_t counter,std::uint8_t pending,std::uint8_t display,std::uint8_t start_bank,int pattern){
    Bytes ram;State s=fixture(ram,0x72fa);fill_staging(ram,seed,true);
    for(unsigned int k=0;k<256;++k){
        bool dirty=false;
        if(pattern==-1)dirty=true;else if(pattern==-2)dirty=(k&1U)!=0;else if(pattern==-3)dirty=false;else if(pattern==-4)dirty=(lcg(seed)&1U)!=0;
        else dirty=static_cast<int>(k)==pattern;
        if(dirty)ram[(STAGING+0x20*k)&65535U]|=0x80U;
    }
    put(ram,COUNTER,2,counter);put(ram,PENDING,1,pending);put(ram,DISPLAY,1,display);
    Palette p;fill_palette(p,seed^0xabcdef);p.selected=start_bank;
    Bytes oram=ram;std::vector<std::uint8_t> p0=p.banks[0],p1=p.banks[1];std::uint8_t disp=0xff;std::string e;
    assert(ms5::transfer_palette_banks(oram,p0,p1,disp,e));
    const State entry=s;Out o;assert(run(ram,s,p,SENT,o));
    assert(ram==oram&&p.banks[0]==p0&&p.banks[1]==p1&&p.selected==disp&&s.pc==SENT&&s.a[7]==SP&&s.a[5]==entry.a[5]);
    // ports: [3a000f (pending) | 3a001f (fill)], 300001 (normal path only), display select
    std::size_t at=0;
    if(counter!=0){assert(port_is(o.ports[at++],0x3a001f,1,entry.d[0]&255U));}
    else {
        if(pending&0x80U)assert(port_is(o.ports[at++],0x3a000f,1,entry.d[0]&255U));
        assert(port_is(o.ports[at++],0x300001,1,s.d[0]&255U));
    }
    assert(port_is(o.ports[at++],display?0x3a001f:0x3a000f,1,s.d[0]&255U)&&at==o.ports.size());
}
void transfers(){
    std::uint32_t seed=0x2468ace0;
    for(int pattern=-4;pattern<256;++pattern)oracle_case(lcg(seed),0,0x80|static_cast<std::uint8_t>(pattern&0x7f),static_cast<std::uint8_t>(pattern&2),
        static_cast<std::uint8_t>(pattern&1),pattern);
    for(unsigned int i=0;i<16;++i){
        oracle_case(lcg(seed),0,static_cast<std::uint8_t>(i&0x7f),static_cast<std::uint8_t>(i*17),static_cast<std::uint8_t>(i&1),-1);   // not pending
        oracle_case(lcg(seed),0x2000,static_cast<std::uint8_t>(0x80|i),static_cast<std::uint8_t>(i&2),static_cast<std::uint8_t>(i&1),-4); // special fill
    }
    // last-copied D0 reaches the watchdog: only cell 255 dirty
    {Bytes ram;State s=fixture(ram,0x72fa);fill_staging(ram,9,true);put(ram,STAGING+0x20*255,1,0x80);put(ram,PENDING,1,0x80);Palette p;Out o;
     assert(run(ram,s,p,SENT,o)&&o.ports.size()==3&&port_is(o.ports[1],0x300001,1,get(ram,STAGING+0x20*255,4)&255U));}
    // counter 4000: one fill of 402000..403fff (bank 1 mirror), counter -> 2000, no 8b5c; the next IRQ fills again and clears 400000
    {Bytes ram;State s=fixture(ram,0x72fa);fill_staging(ram,77,true);put(ram,COUNTER,2,0x4000);put(ram,PENDING,1,0x80);Palette p;fill_palette(p,5);
     const Palette before=p;const Bytes ram0=ram;Out o;assert(run(ram,s,p,SENT,o));
     assert(get(ram,COUNTER,2)==0x2000&&get(ram,PENDING,1)==0x80&&s.a[0]==0x402000&&p.selected==0&&p.banks[0]==before.banks[0]);
     for(unsigned int i=0;i<8192;++i)assert(p.banks[1][i]==ram0[(FILL+(i&31U))&65535U]);
     State t=s;t.pc=0x72fa;t.a[7]=SP-4;put(ram,SP-4,4,SENT);assert(run(ram,t,p,SENT,o));
     assert(get(ram,COUNTER,2)==0&&t.a[0]==0x400000&&p.banks[1][0]==0&&p.banks[1][1]==0&&p.banks[1][2]==ram0[(FILL+2)&65535U]);}
    // counter 6000: 404000..405fff (mirror of the whole bank 1)
    {Bytes ram;State s=fixture(ram,0x873a);fill_staging(ram,78,true);put(ram,COUNTER,2,0x6000);Palette p;Out o;assert(run(ram,s,p,0x8b60,o));
     assert(get(ram,COUNTER,2)==0x4000&&s.a[0]==0x404000&&p.selected==1);
     for(unsigned int i=0;i<8192;++i)assert(p.banks[1][i]==get(ram,FILL+(i&31U),1));}
}
// ---- palette device: mirror reads/writes, run_animation_machine without palette unchanged, checked errors and rollback ------------
void device(){
    // 72fa TST.W -216(A5) with A5 = 400216 + mirror offsets reads the selected bank (mirror 400000 / 402000 / 7fe000 / 401ffe)
    // (A5 - 216 = the mirror address; the word is nonzero only in bank `nonzero`; the BNE goes to 873a iff that bank is selected)
    const std::uint32_t mirror[]={0x400000,0x402000,0x7fe000,0x401ffe,0x7ffffe};
    for(unsigned int i=0;i<5;++i)for(unsigned int nonzero=0;nonzero<2;++nonzero)for(unsigned int sel=0;sel<2;++sel){
        Bytes ram;State s=fixture(ram,0x72fa);s.a[5]=mirror[i]+0x216;Palette p;p.selected=static_cast<std::uint8_t>(sel);
        p.banks[nonzero][(mirror[i]+1)&0x1fffU]=0x5a;const Palette before=p;Out o;
        assert(run(ram,s,p,sel==nonzero?0x873a:0x7302,o)&&same_palette(p,before)&&o.ports.empty());
    }
    // the same read without a palette device is the pre-existing bus error
    {Bytes ram;State s=fixture(ram,0x72fa);s.a[5]=0x400216;Palette p;reject(ram,s,p,0x7302,"unsupported program bus device address",false);
     s.a[5]=0x7ffffe + 0x216;reject(ram,s,p,0x7302,"unsupported program bus device address",false);}
    // run_animation_machine: palette writes keep the device error; the bank selects stay ports
    {Bytes ram;State s=fixture(ram,0x72fa);put(ram,PENDING,1,0x80);put(ram,STAGING+0x40,1,0x80);Palette p;
     reject(ram,s,p,SENT,"unsupported animation machine write device",false);}
    {Bytes ram;State s=fixture(ram,0x72fa);put(ram,COUNTER,2,0x2000);Palette p;reject(ram,s,p,SENT,"unsupported animation machine write device",false);}
    // without dirty cells the plain run is the same as the palette run (ports, RAM, registers)
    for(unsigned int display=0;display<2;++display){
        Bytes ram;State s=fixture(ram,0x72fa);put(ram,PENDING,1,0x80);put(ram,DISPLAY,1,display);Bytes ram2=ram;State s2=s;
        Palette p;fill_palette(p,3);p.selected=1;Out o,o2;assert(run_plain(ram,s,SENT,o)&&run(ram2,s2,p,SENT,o2));
        assert(ram==ram2&&same(s,s2)&&o.ports.size()==3&&o2.ports.size()==3);
        for(unsigned int i=0;i<3;++i)assert(port_is(o.ports[i],o2.ports[i].address,o2.ports[i].size,o2.ports[i].value));
        assert(port_is(o.ports[0],0x3a000f,1,s.d[0]&255U)&&port_is(o.ports[1],0x300001,1,s.d[0]&255U)&&
            port_is(o.ports[2],display?0x3a001f:0x3a000f,1,s.d[0]&255U)&&p.selected==display);
    }
    // invalid palette device
    {Bytes ram;State s=fixture(ram,0x72fa);Palette p;p.banks[1].resize(8191);reject(ram,s,p,SENT,"invalid animation machine palette RAM");
     Palette q;q.selected=2;reject(ram,s,q,SENT,"invalid animation machine palette RAM");}
    // special fill counters that leave the palette mirror: 1000 (128 stores, then 3ff000: rollback of the written bank), ffe0, 8000;
    // odd counter: LONG store at an odd address
    const std::uint32_t bad[]={0x1000,0xffe0,0x8000,0x0020};
    for(unsigned int i=0;i<4;++i){Bytes ram;State s=fixture(ram,0x72fa);fill_staging(ram,i,true);put(ram,COUNTER,2,bad[i]);Palette p;fill_palette(p,i);
        reject(ram,s,p,SENT,"unsupported animation machine write device");}
    {Bytes ram;State s=fixture(ram,0x72fa);put(ram,COUNTER,2,0x2001);Palette p;reject(ram,s,p,SENT,"invalid animation machine write size/alignment");}
    // a failing later block rolls back palette and bank selection: transfer then RTS to an unrouted PC
    {Bytes ram;State s=fixture(ram,0x72fa);fill_staging(ram,4,true);put(ram,STAGING,1,0x80);put(ram,PENDING,1,0x80);put(ram,DISPLAY,1,1);
     put(ram,SP-4,4,0x10fe00);Palette p;reject(ram,s,p,SENT,"unsupported animation machine PC");}
}
}
int main(){
    block_table();interior();carry();cells();transfers();device();
    std::printf("animation_machine_irq_f6b_test: %u runs ok\n",calls);
    return 0;
}
