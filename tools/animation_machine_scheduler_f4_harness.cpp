// Verification harness, adapted from Claude U15b/U15c integration evidence: frame passes of the scheduler shell through run_animation_machine.
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
// One run with the declared wait release loop (sound 3aea: WORD 104d74 = ffff; sprite cda4: WORD 108d34 = D4.W; gate 47af0/478de:
// BYTE 107ded bit 7 cleared unless WORD 107dea <> 0).
static bool run(Machine& m,Bytes& ram,ms5::AnimationMachineState& s,ms5::AnimationMachineDevice& dev,std::uint32_t stop,
    std::vector<ms5::VideoPortWrite>& all,std::string& error,unsigned& waits,std::uint32_t& reads_total){
    for(unsigned k=0;k<17;++k){
        std::vector<ms5::VideoPortWrite> ports;std::uint32_t reads=0;ms5::AnimationMachineStatus st=ms5::AnimationMachineReturned;
        if(!ms5::run_animation_machine(ram,m.w,*m.bus,s,dev,stop,0,reads,st,ports,error))return false;
        all.insert(all.end(),ports.begin(),ports.end());reads_total+=reads;
        if(st==ms5::AnimationMachineReturned)return true;
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
    const Bytes in=load(argv[1]);if(in.size()!=65536+8192+19*4)return 4;
    Bytes ram(in.begin(),in.begin()+65536);ms5::AnimationMachineDevice dev;dev.pvc.assign(in.begin()+65536,in.begin()+65536+8192);
    ms5::AnimationMachineState s;std::size_t o=65536+8192;
    for(unsigned i=0;i<8;++i)s.d[i]=be(in,o+4*i);for(unsigned i=0;i<8;++i)s.a[i]=be(in,o+32+4*i);s.pc=be(in,o+64);dev.bank_base=be(in,o+68);
    const std::uint32_t frames=be(in,o+72);
    std::ofstream out(argv[2]);
    for(std::uint32_t frame=0;frame<frames;++frame){
        if(frame>0){s.pc=0x2ac2;s.a[6]=0x1008e4;s.a[7]=0x1ff000;}
        s.carry=ms5::AnimationCarryUnknown;
        std::ostringstream js;js<<"{\"frame\":"<<frame<<",\"start\":\""<<state_digest(ram,s,0x2ac2,dev,false)<<"\"";
        const std::uint32_t head=ramget(ram,0x100820,4);
        if(head!=0xe4a&&head!=0xe74){js<<",\"host_reject\":"<<head<<"}";out<<js.str()<<"\n";break;}
        // Chained node runs (stop 2abe = node entry, stop 2ac2 = node exit) on copies.
        Bytes cram=ram;ms5::AnimationMachineState cs=s;ms5::AnimationMachineDevice cdev=dev;std::vector<ms5::VideoPortWrite> cports;
        std::string cerr_;bool cok=true;unsigned waits=0;std::uint32_t reads=0;js<<",\"nodes\":[";bool first=true;std::string ctrl;
        for(unsigned n=0;n<400;++n){
            std::vector<ms5::VideoPortWrite> p;
            if(!run(m,cram,cs,cdev,0x2abe,p,cerr_,waits,reads)){cok=false;break;}
            cports.insert(cports.end(),p.begin(),p.end());
            if(cs.a[6]==0x100820){p.clear();if(!run(m,cram,cs,cdev,head,p,cerr_,waits,reads)){cok=false;}cports.insert(cports.end(),p.begin(),p.end());break;}
            if(cs.a[6]==0x1008e4){ctrl="controller-node-visited";break;}
            const std::uint32_t a6=cs.a[6],cb=ramget(cram,a6,4);
            const std::string entry=state_digest(cram,cs,0x2ab8,cdev,true);
            p.clear();std::string nerr;
            const bool ok=run(m,cram,cs,cdev,0x2ac2,p,nerr,waits,reads);
            js<<(first?"":",")<<"{\"a6\":"<<a6<<",\"cb\":"<<cb<<",\"entry\":\""<<entry<<"\"";first=false;
            if(!ok){js<<",\"error\":\""<<nerr<<"\"}";cerr_=nerr;cok=false;break;}
            const bool split=(cb==0x4fcce||cb==0x4fcda);
            js<<",\"exit\":\""<<state_digest(cram,cs,0x2ac2,cdev,false)<<"\",\"ports\":"<<p.size()<<",\"ports_sha\":\""<<ports_digest(p,split)<<"\"}";
            cports.insert(cports.end(),p.begin(),p.end());
        }
        js<<"]";
        // Whole pass: one run with stop = LONG (100820) (plus the declared wait releases).
        Bytes before=ram;ms5::AnimationMachineState sb=s;ms5::AnimationMachineDevice db=dev;std::vector<ms5::VideoPortWrite> wports;
        std::string werr;unsigned wwaits=0;std::uint32_t wreads=0;
        const bool wok=run(m,ram,s,dev,head,wports,werr,wwaits,wreads);
        if(!wok){
            bool preserved=(ram==before)&&(dev.pvc==db.pvc)&&dev.bank_base==db.bank_base&&s.pc==sb.pc;
            for(unsigned i=0;i<8;++i)if(s.d[i]!=sb.d[i]||s.a[i]!=sb.a[i])preserved=false;
            js<<",\"error\":\""<<werr<<"\",\"preserved\":"<<(preserved?"true":"false")<<",\"chain_ok\":"<<(cok?"true":"false")<<",\"chain_error\":\""<<cerr_<<"\"";
            if(!ctrl.empty())js<<",\"ctrl\":true";
            js<<"}";out<<js.str()<<"\n";break;
        }
        bool same=cok&&ctrl.empty()&&cram==ram&&cdev.pvc==dev.pvc&&cdev.bank_base==dev.bank_base&&cs.pc==s.pc&&cports.size()==wports.size();
        for(unsigned i=0;i<8&&same;++i)if(cs.d[i]!=s.d[i]||cs.a[i]!=s.a[i])same=false;
        js<<",\"end\":\""<<state_digest(ram,s,s.pc,dev,false)<<"\",\"pc\":"<<s.pc<<",\"a7\":"<<s.a[7]<<",\"a6\":"<<s.a[6]<<",\"a5\":"<<s.a[5]<<",\"a0\":"<<s.a[0]
          <<",\"stack\":"<<ramget(ram,s.a[7],4)<<",\"waits\":"<<wwaits<<",\"reads\":"<<wreads<<",\"ports\":"<<wports.size()<<",\"chain_equal\":"<<(same?"true":"false")<<"}";
        out<<js.str()<<"\n";
    }
    return 0;
}
