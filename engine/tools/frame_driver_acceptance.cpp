// Dedicated read-only D1 frame driver acceptance harness (run_animation_machine_pass / step_animation_machine_frame).
// Length-prefixed BE packets on stdin/stdout; no files written by this process.
// Request (BE u32 unless noted):
//   mode (0 = run_animation_machine_pass, 1 = step_animation_machine_frame, 2 = H segment only, see head_only), d0..d7, a0..a7, pc, carry, bank_base,
//   external_status, queue count NQ, then RAM 65536 bytes, PVC 8192 bytes, NQ x (address, size, value).
// Success response: 1, pc, carry, bank_base, head_pc, controller_pc, pass_stop_pc, head_external_reads,
//   node_external_reads, NH (head ports), NN (node ports), NW (waits), NR (queue entries left), d0..d7, a0..a7,
//   RAM 65536, PVC 8192, NH x (address, size, value), NN x (address, size, value),
//   NW x (segment, pc, address, size, before, released), NR x (address, size, value).
// Failure response: 0, preserved (1 when RAM, state, device and result are unchanged), error text bytes.
#include "ms5/animation_machine.h"
#include "ms5/animation_machine_frame.h"
#include "ms5/physical_rom_resource.h"
#include <iostream>
#include <string>
#include <vector>

typedef std::vector<std::uint8_t> Bytes;
static const std::uint32_t REQUEST_WORDS=22;
static void add(Bytes& b,std::uint32_t v) {
    for(unsigned int i=0;i<4;++i)b.push_back(static_cast<std::uint8_t>(v>>(24-8*i)));
}
static bool take(const Bytes& b,std::size_t& at,std::uint32_t& v) {
    if(at+4>b.size())return false;
    v=0;
    for(unsigned int i=0;i<4;++i)v=(v<<8)|b[at++];
    return true;
}
static bool read_packet(Bytes& b,bool& eof) {
    char h[4];
    std::cin.read(h,4);
    eof=std::cin.gcount()==0&&std::cin.eof();
    if(eof)return true;
    if(std::cin.gcount()!=4)return false;
    std::uint32_t n=0;
    for(unsigned int i=0;i<4;++i)n=(n<<8)|static_cast<unsigned char>(h[i]);
    if(n>4194304U)return false;
    b.resize(n);
    if(n)std::cin.read(reinterpret_cast<char*>(&b[0]),n);
    return static_cast<std::uint32_t>(std::cin.gcount())==n;
}
static bool write_packet(const Bytes& b) {
    Bytes h;
    add(h,static_cast<std::uint32_t>(b.size()));
    std::cout.write(reinterpret_cast<const char*>(&h[0]),4);
    if(!b.empty())std::cout.write(reinterpret_cast<const char*>(&b[0]),b.size());
    std::cout.flush();
    return static_cast<bool>(std::cout);
}
static bool same_state(const ms5::AnimationMachineState& x,const ms5::AnimationMachineState& y) {
    for(unsigned int i=0;i<8;++i)if(x.d[i]!=y.d[i]||x.a[i]!=y.a[i])return false;
    return x.pc==y.pc&&x.carry==y.carry;
}
static bool same_reads(const std::vector<ms5::AnimationMachineExternalRead>& x,const std::vector<ms5::AnimationMachineExternalRead>& y) {
    if(x.size()!=y.size())return false;
    for(std::size_t i=0;i<x.size();++i)if(x[i].address!=y[i].address||x[i].size!=y[i].size||x[i].value!=y[i].value)return false;
    return true;
}
static void add_ports(Bytes& out,const std::vector<ms5::VideoPortWrite>& ports) {
    for(std::size_t i=0;i<ports.size();++i) {add(out,ports[i].address);add(out,ports[i].size);add(out,ports[i].value);}
}
static std::uint32_t ram_get(const Bytes& ram,std::uint32_t address,unsigned int size) {
    std::uint32_t v=0;
    for(unsigned int i=0;i<size;++i)v=(v<<8)|ram[((address&0xffffffU)+i)&0xffffU];
    return v;
}
static void ram_set(Bytes& ram,std::uint32_t address,unsigned int size,std::uint32_t value) {
    for(unsigned int i=0;i<size;++i)ram[((address&0xffffffU)+i)&0xffffU]=static_cast<std::uint8_t>(value>>(8*(size-1-i)));
}
// Localisation aid, not the driver: the H segment alone (run_animation_machine from the H start to LONG (1008e4)) with the
// declared release table of animation_machine_frame.h restated here, so that the state after H can be compared with the
// native state at the controller transfer. The driver API does not expose its intermediate H state. Works on copies.
static bool head_only(Bytes& ram,const ms5::ProgramBusState& bus,ms5::AnimationMachineState& s,ms5::AnimationMachineDevice& dev,
    std::uint8_t external_status,ms5::AnimationFrameResult& r,std::string& error) {
    Bytes wram(ram);
    ms5::AnimationMachineState ws(s);
    ms5::AnimationMachineDevice wdev(dev);
    ms5::AnimationFrameResult wr;
    std::vector<ms5::FixedDataResource> windows;
    const std::uint32_t head=ram_get(wram,0x100820,4),stop=ram_get(wram,0x1008e4,4);
    if((head!=0xe4aU&&head!=0xe74U)||ws.pc!=head||ws.a[6]!=0x100820U||ws.a[7]!=0x1feffcU||ram_get(wram,0x1feffc,4)!=0x2ac2U) {
        error="head-only entry mismatch";return false;
    }
    ws.carry=ms5::AnimationCarryUnknown;
    for(unsigned int count=0;;++count) {
        std::vector<ms5::VideoPortWrite> phase;
        std::uint32_t reads=0;
        ms5::AnimationMachineStatus status=ms5::AnimationMachineReturned;
        if(!ms5::run_animation_machine(wram,windows,bus,ws,wdev,stop,external_status,reads,status,phase,error))return false;
        wr.head_ports.insert(wr.head_ports.end(),phase.begin(),phase.end());
        wr.head_external_reads+=reads;
        if(status==ms5::AnimationMachineReturned)break;
        if(count>=64U) {error="head-only wait limit";return false;}
        ms5::AnimationFrameWait w;
        w.segment=ms5::AnimationFrameHead;w.pc=ws.pc;w.size=2;w.address=0;w.released=0;
        const std::uint32_t a5=ws.a[5];
        if(ws.pc==0xef2U) {w.address=(a5-0x7feaU)&0xffffffU;w.size=1;w.released=ram_get(wram,(a5-0x7fe9U)&0xffffffU,1);}
        else if(ws.pc==0x16bd0U) {w.address=(a5+0xd34U)&0xffffffU;w.released=ws.d[0]&0xffffU;}
        else if(ws.pc==0x3aeaU) {w.address=0x104d74U;w.released=0xffffU;}
        else if(ws.pc==0xcda4U) {w.address=0x108d34U;w.released=ws.d[4]&0xffffU;}
        else if(ws.pc==0x47af0U||ws.pc==0x478deU) {
            if(ram_get(wram,0x107dea,2)!=0) {error="head-only gate wait not released";return false;}
            w.address=0x107ded;w.size=1;w.released=ram_get(wram,0x107ded,1)&0x7fU;
        } else {error="head-only undeclared wait";return false;}
        w.before=ram_get(wram,w.address,w.size);
        ram_set(wram,w.address,w.size,w.released);
        wr.waits.push_back(w);
    }
    if(ws.pc!=stop||ws.a[6]!=0x1008e4U||ws.a[7]!=0x1feffcU||ram_get(wram,0x1feffc,4)!=0x2ac2U) {error="head-only boundary mismatch";return false;}
    wr.head_pc=head;wr.controller_pc=stop;
    ram.swap(wram);s=ws;dev=wdev;r=wr;
    return true;
}
// Returns false only for a malformed request; a driver failure is a valid failure response.
static bool run(const Bytes& input,const ms5::ProgramBusState& bus,Bytes& output,std::string& error) {
    std::size_t at=0;
    std::uint32_t v[REQUEST_WORDS];
    for(unsigned int i=0;i<REQUEST_WORDS;++i)if(!take(input,at,v[i])) {error="short request";return false;}
    const std::uint32_t mode=v[0],nq=v[21];
    if(mode>2U||v[18]>2U||v[20]>255U||nq>65536U||input.size()!=4U*REQUEST_WORDS+65536U+8192U+12U*nq) {error="invalid request";return false;}
    ms5::AnimationMachineState s;
    for(unsigned int i=0;i<8;++i) {s.d[i]=v[1+i];s.a[i]=v[9+i];}
    s.pc=v[17];
    s.carry=static_cast<ms5::AnimationCarryState>(v[18]);
    Bytes ram(input.begin()+at,input.begin()+at+65536);
    at+=65536;
    ms5::AnimationMachineDevice dev;
    dev.bank_base=v[19];
    dev.pvc.assign(input.begin()+at,input.begin()+at+8192);
    at+=8192;
    for(std::uint32_t i=0;i<nq;++i) {
        ms5::AnimationMachineExternalRead e;
        std::uint32_t size=0;
        if(!take(input,at,e.address)||!take(input,at,size)||!take(input,at,e.value)||size>255U) {error="bad queue entry";return false;}
        e.size=static_cast<std::uint8_t>(size);
        dev.reads.push_back(e);
    }
    const Bytes ram0(ram);
    const ms5::AnimationMachineState s0(s);
    const ms5::AnimationMachineDevice dev0(dev);
    std::vector<ms5::FixedDataResource> windows;
    ms5::AnimationFrameResult result;
    std::string failure;
    bool ok=false;
    if(mode==0U)ok=ms5::run_animation_machine_pass(ram,windows,bus,s,dev,static_cast<std::uint8_t>(v[20]),result,failure);
    else if(mode==1U)ok=ms5::step_animation_machine_frame(ram,windows,bus,s,dev,static_cast<std::uint8_t>(v[20]),result,failure);
    else ok=head_only(ram,bus,s,dev,static_cast<std::uint8_t>(v[20]),result,failure);
    if(!ok) {
        const bool preserved=ram==ram0&&same_state(s,s0)&&dev.bank_base==dev0.bank_base&&dev.pvc==dev0.pvc&&same_reads(dev.reads,dev0.reads)&&
            result.head_ports.empty()&&result.node_ports.empty()&&result.waits.empty()&&result.head_pc==0&&result.controller_pc==0&&
            result.pass_stop_pc==0&&result.head_external_reads==0&&result.node_external_reads==0;
        add(output,0);
        add(output,preserved?1U:0U);
        output.insert(output.end(),failure.begin(),failure.end());
        return true;
    }
    add(output,1);
    add(output,s.pc);add(output,static_cast<std::uint32_t>(s.carry));add(output,dev.bank_base);
    add(output,result.head_pc);add(output,result.controller_pc);add(output,result.pass_stop_pc);
    add(output,result.head_external_reads);add(output,result.node_external_reads);
    add(output,static_cast<std::uint32_t>(result.head_ports.size()));add(output,static_cast<std::uint32_t>(result.node_ports.size()));
    add(output,static_cast<std::uint32_t>(result.waits.size()));add(output,static_cast<std::uint32_t>(dev.reads.size()));
    for(unsigned int i=0;i<8;++i)add(output,s.d[i]);
    for(unsigned int i=0;i<8;++i)add(output,s.a[i]);
    output.insert(output.end(),ram.begin(),ram.end());
    output.insert(output.end(),dev.pvc.begin(),dev.pvc.end());
    add_ports(output,result.head_ports);
    add_ports(output,result.node_ports);
    for(std::size_t i=0;i<result.waits.size();++i) {
        const ms5::AnimationFrameWait& w=result.waits[i];
        add(output,static_cast<std::uint32_t>(w.segment));add(output,w.pc);add(output,w.address);add(output,w.size);
        add(output,w.before);add(output,w.released);
    }
    for(std::size_t i=0;i<dev.reads.size();++i) {add(output,dev.reads[i].address);add(output,dev.reads[i].size);add(output,dev.reads[i].value);}
    return true;
}
int main(int argc,char** argv) {
    if(argc!=9) {std::cerr<<"usage: frame_driver_acceptance PROGRAM_ROM_0.ms5d ... PROGRAM_ROM_7.ms5d\n";return 2;}
    std::vector<ms5::PhysicalRomResource> physical;
    Bytes vectors;
    std::string error;
    for(int i=1;i<argc;++i) {
        ms5::PhysicalRomResource r;
        if(!ms5::load_physical_rom_resource(argv[i],r,error)) {std::cerr<<error<<"\n";return 2;}
        if(r.source_rom_offset==0&&r.data.size()>=128)vectors.assign(r.data.begin(),r.data.begin()+128);
        physical.push_back(r);
    }
    if(vectors.size()!=128) {std::cerr<<"missing original vectors\n";return 2;}
    ms5::ProgramBusState bus;
    bus.physical_rom=&physical;
    bus.vectors=&vectors;
    for(;;) {
        Bytes input,output;
        bool eof=false;
        if(!read_packet(input,eof)) {std::cerr<<"invalid packet\n";return 2;}
        if(eof)break;
        if(!run(input,bus,output,error)) {std::cerr<<error<<"\n";return 2;}
        if(!write_packet(output))return 2;
    }
    return 0;
}
