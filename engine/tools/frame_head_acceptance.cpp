// Dedicated read-only F5 acceptance harness. Length-prefixed BE packets on stdin/stdout;
// no game/controller implementation and no files written by this process.
#include "ms5/animation_machine.h"
#include "ms5/physical_rom_resource.h"
#include <iostream>
#include <string>
#include <vector>

typedef std::vector<std::uint8_t> Bytes;
static void add(Bytes& b,std::uint32_t v) {
    for(unsigned int i=0;i<4;++i)b.push_back(static_cast<std::uint8_t>(v>>(24-8*i)));
}
static bool take(const Bytes& b,std::size_t& at,std::uint32_t& v) {
    if(at+4>b.size())return false;
    v=0;for(unsigned int i=0;i<4;++i)v=(v<<8)|b[at++];return true;
}
static std::uint32_t ram_value(const Bytes& b,std::uint32_t a,unsigned int n) {
    std::uint32_t v=0;for(unsigned int i=0;i<n;++i)v=(v<<8)|b[(a+i)&65535U];return v;
}
static void ram_put(Bytes& b,std::uint32_t a,unsigned int n,std::uint32_t v) {
    for(unsigned int i=0;i<n;++i)b[(a+i)&65535U]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));
}
static bool read_packet(Bytes& b,bool& eof) {
    char h[4];std::cin.read(h,4);eof=std::cin.gcount()==0&&std::cin.eof();
    if(eof)return true;if(std::cin.gcount()!=4)return false;
    std::uint32_t n=0;for(unsigned int i=0;i<4;++i)n=(n<<8)|static_cast<unsigned char>(h[i]);
    if(n>1048576U)return false;b.resize(n);
    if(n)std::cin.read(reinterpret_cast<char*>(&b[0]),n);
    return static_cast<std::uint32_t>(std::cin.gcount())==n;
}
static bool write_packet(const Bytes& b) {
    Bytes h;add(h,static_cast<std::uint32_t>(b.size()));
    std::cout.write(reinterpret_cast<const char*>(&h[0]),4);
    if(!b.empty())std::cout.write(reinterpret_cast<const char*>(&b[0]),b.size());
    std::cout.flush();return static_cast<bool>(std::cout);
}
static bool run(const Bytes& input,const ms5::ProgramBusState& bus,Bytes& output,std::string& error) {
    std::size_t at=0;std::uint32_t values[22];
    for(unsigned int i=0;i<22;++i)if(!take(input,at,values[i])) {error="short request";return false;}
    const std::uint32_t nq=values[20];
    if(nq>4096U||input.size()!=88U+65536U+8192U+12U*nq||values[21]>255U) {error="invalid request length/status";return false;}
    ms5::AnimationMachineState s;for(unsigned int i=0;i<8;++i){s.d[i]=values[i];s.a[i]=values[i+8];}
    s.pc=values[16];s.carry=static_cast<ms5::AnimationCarryState>(values[17]);
    const std::uint32_t stop=values[19];
    Bytes ram(input.begin()+at,input.begin()+at+65536);at+=65536;
    ms5::AnimationMachineDevice dev;dev.bank_base=values[18];dev.pvc.assign(input.begin()+at,input.begin()+at+8192);at+=8192;
    for(std::uint32_t i=0;i<nq;++i) {
        ms5::AnimationMachineExternalRead e;std::uint32_t size=0;
        if(!take(input,at,e.address)||!take(input,at,size)||!take(input,at,e.value)||size>255U) {error="bad queue entry";return false;}
        e.size=static_cast<std::uint8_t>(size);dev.reads.push_back(e);
    }
    std::vector<ms5::VideoPortWrite> ports;Bytes waits;std::uint32_t reads=0,nwaits=0;
    ms5::AnimationMachineStatus status=ms5::AnimationMachineReturned;
    for(;;) {
        std::vector<ms5::FixedDataResource> windows;std::vector<ms5::VideoPortWrite> phase;
        std::uint32_t consumed=0;
        if(!ms5::run_animation_machine(ram,windows,bus,s,dev,stop,static_cast<std::uint8_t>(values[21]),consumed,status,phase,error))return false;
        reads+=consumed;ports.insert(ports.end(),phase.begin(),phase.end());
        if(status!=ms5::AnimationMachineWaiting)break;
        if(++nwaits>64U) {error="declared wait limit";return false;}
        std::uint32_t address=0,size=2,value=0;
        if(s.pc==0xef2U) {address=s.a[5]-0x7feaU;size=1;value=ram_value(ram,s.a[5]-0x7fe9U,1);}
        else if(s.pc==0x16bd0U) {address=s.a[5]+0xd34U;value=s.d[0]&65535U;}
        else if(s.pc==0x3aeaU) {address=0x104d74U;value=65535U;}
        else if(s.pc==0xcda4U) {address=0x108d34U;value=s.d[4]&65535U;}
        else {error="undeclared wait PC";return false;}
        add(waits,s.pc);add(waits,address);add(waits,size);add(waits,ram_value(ram,address,size));add(waits,value);
        ram_put(ram,address,size,value);
    }
    add(output,1);add(output,static_cast<std::uint32_t>(status));add(output,s.pc);add(output,static_cast<std::uint32_t>(s.carry));
    add(output,dev.bank_base);add(output,reads);add(output,static_cast<std::uint32_t>(ports.size()));
    add(output,static_cast<std::uint32_t>(dev.reads.size()));add(output,nwaits);
    for(unsigned int i=0;i<8;++i)add(output,s.d[i]);for(unsigned int i=0;i<8;++i)add(output,s.a[i]);
    output.insert(output.end(),ram.begin(),ram.end());output.insert(output.end(),dev.pvc.begin(),dev.pvc.end());
    for(std::size_t i=0;i<ports.size();++i) {add(output,ports[i].address);add(output,ports[i].size);add(output,ports[i].value);}
    for(std::size_t i=0;i<dev.reads.size();++i) {add(output,dev.reads[i].address);add(output,dev.reads[i].size);add(output,dev.reads[i].value);}
    output.insert(output.end(),waits.begin(),waits.end());return true;
}
int main(int argc,char** argv) {
    if(argc!=9) {std::cerr<<"usage: frame_head_acceptance PROGRAM_ROM_0.ms5d ... PROGRAM_ROM_7.ms5d\n";return 2;}
    std::vector<ms5::PhysicalRomResource> physical;Bytes vectors;std::string error;
    for(int i=1;i<argc;++i) {
        ms5::PhysicalRomResource r;if(!ms5::load_physical_rom_resource(argv[i],r,error)) {std::cerr<<error<<"\n";return 2;}
        if(r.source_rom_offset==0&&r.data.size()>=128)vectors.assign(r.data.begin(),r.data.begin()+128);
        physical.push_back(r);
    }
    if(vectors.size()!=128) {std::cerr<<"missing original vectors\n";return 2;}
    ms5::ProgramBusState bus;bus.physical_rom=&physical;bus.vectors=&vectors;
    for(;;) {
        Bytes input,output;bool eof=false;
        if(!read_packet(input,eof)) {std::cerr<<"invalid packet\n";return 2;}if(eof)break;
        if(!run(input,bus,output,error)) {output.clear();add(output,0);output.insert(output.end(),error.begin(),error.end());}
        if(!write_packet(output))return 2;
    }
    return 0;
}
