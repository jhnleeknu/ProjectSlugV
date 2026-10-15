// Dedicated read-only F6-D frame driver acceptance harness for IRQ execution (AnimationFrameOptions.irq_execution, the palette RAM
// overloads of run_animation_machine_pass / step_animation_machine_frame). Copy-and-extend of frame_controller_acceptance.cpp (that
// harness and its packet format are unchanged). Length-prefixed BE packets on stdin/stdout; no files written.
// Request (BE u32 unless noted):
//   mode (0 = run_animation_machine_pass, 1 = step_animation_machine_frame), d0..d7, a0..a7, pc, carry, bank_base, external_status,
//   options (bits 0..7 = card_answer, bit 8 = card_resume, bit 9 = controller_mode Execute, bit 10 = credit_resume, bit 11 = irq_execution,
//   bit 12 = palette RAM attached (the palette overloads; otherwise the plain functions)), credit_answer, irq_z80_reply, irq_video_status,
//   palette selected bank, queue count NQ, then RAM 65536 bytes, PVC 8192 bytes, palette bank 0 and bank 1 (8192 bytes each),
//   NQ x (address, size, value).
// Success response: 1, pc, carry, bank_base, head_pc, controller_pc, pass_stop_pc, controller_exit_pc, head_external_reads,
//   node_external_reads, controller_external_reads, NH, NN, NC, NW, NR, NI (irqs), NP (irq ports), palette selected, d0..d7, a0..a7,
//   RAM 65536, PVC 8192, palette banks 16384, NH x (address, size, value), NN x (...), NC x (...), NW x (segment, pc, address, size,
//   before, released), NI x (segment, wait_pc, sequence, ports_begin, ports_end, external_reads, bios_resumes, rte_sr), NP x (address,
//   size, value), NR x (address, size, value).
// Failure response: 0, preserved (1 when RAM, state, device, palette and result are unchanged), error text bytes.
#include "ms5/animation_machine.h"
#include "ms5/animation_machine_frame.h"
#include "ms5/physical_rom_resource.h"
#include <iostream>
#include <string>
#include <vector>

typedef std::vector<std::uint8_t> Bytes;
static const std::uint32_t REQUEST_WORDS=27;
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
// Returns false only for a malformed request; a driver failure is a valid failure response.
static bool run(const Bytes& input,const ms5::ProgramBusState& bus,Bytes& output,std::string& error) {
    std::size_t at=0;
    std::uint32_t v[REQUEST_WORDS];
    for(unsigned int i=0;i<REQUEST_WORDS;++i)if(!take(input,at,v[i])) {error="short request";return false;}
    const std::uint32_t mode=v[0],nq=v[26];
    if((mode!=0U&&mode!=1U)||v[18]>2U||v[20]>255U||v[21]>0x1fffU||v[23]>255U||v[24]>65535U||v[25]>1U||nq>65536U||
        input.size()!=4U*REQUEST_WORDS+65536U+8192U+16384U+12U*nq) {error="invalid request";return false;}
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
    ms5::AnimationMachinePaletteRam pal;
    pal.banks[0].assign(input.begin()+at,input.begin()+at+8192);
    at+=8192;
    pal.banks[1].assign(input.begin()+at,input.begin()+at+8192);
    at+=8192;
    pal.selected=static_cast<std::uint8_t>(v[25]);
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
    const ms5::AnimationMachinePaletteRam pal0(pal);
    std::vector<ms5::FixedDataResource> windows;
    ms5::AnimationFrameOptions options;
    options.card_resume=(v[21]&0x100U)!=0;
    options.card_answer=static_cast<std::uint8_t>(v[21]&0xffU);
    options.controller_mode=(v[21]&0x200U)!=0?ms5::AnimationFrameControllerExecute:ms5::AnimationFrameControllerSkip;
    options.credit_resume=(v[21]&0x400U)!=0;
    options.credit_answer=v[22];
    options.irq_execution=(v[21]&0x800U)!=0;
    options.irq_z80_reply=static_cast<std::uint8_t>(v[23]);
    options.irq_video_status=static_cast<std::uint16_t>(v[24]);
    const bool palette=(v[21]&0x1000U)!=0;
    ms5::AnimationFrameResult result;
    std::string failure;
    bool ok=false;
    const std::uint8_t status=static_cast<std::uint8_t>(v[20]);
    if(mode==0U)ok=palette?ms5::run_animation_machine_pass(ram,windows,bus,s,dev,pal,status,options,result,failure):
        ms5::run_animation_machine_pass(ram,windows,bus,s,dev,status,options,result,failure);
    else ok=palette?ms5::step_animation_machine_frame(ram,windows,bus,s,dev,pal,status,options,result,failure):
        ms5::step_animation_machine_frame(ram,windows,bus,s,dev,status,options,result,failure);
    if(!ok) {
        const bool preserved=ram==ram0&&same_state(s,s0)&&dev.bank_base==dev0.bank_base&&dev.pvc==dev0.pvc&&same_reads(dev.reads,dev0.reads)&&
            result.head_ports.empty()&&result.node_ports.empty()&&result.controller_ports.empty()&&result.waits.empty()&&result.head_pc==0&&
            result.controller_pc==0&&result.pass_stop_pc==0&&result.controller_exit_pc==0&&result.head_external_reads==0&&result.node_external_reads==0&&
            result.controller_external_reads==0&&result.irqs.empty()&&result.irq_ports.empty()&&pal.banks[0]==pal0.banks[0]&&
            pal.banks[1]==pal0.banks[1]&&pal.selected==pal0.selected;
        add(output,0);
        add(output,preserved?1U:0U);
        output.insert(output.end(),failure.begin(),failure.end());
        return true;
    }
    add(output,1);
    add(output,s.pc);add(output,static_cast<std::uint32_t>(s.carry));add(output,dev.bank_base);
    add(output,result.head_pc);add(output,result.controller_pc);add(output,result.pass_stop_pc);add(output,result.controller_exit_pc);
    add(output,result.head_external_reads);add(output,result.node_external_reads);add(output,result.controller_external_reads);
    add(output,static_cast<std::uint32_t>(result.head_ports.size()));add(output,static_cast<std::uint32_t>(result.node_ports.size()));
    add(output,static_cast<std::uint32_t>(result.controller_ports.size()));
    add(output,static_cast<std::uint32_t>(result.waits.size()));add(output,static_cast<std::uint32_t>(dev.reads.size()));
    add(output,static_cast<std::uint32_t>(result.irqs.size()));add(output,static_cast<std::uint32_t>(result.irq_ports.size()));add(output,pal.selected);
    for(unsigned int i=0;i<8;++i)add(output,s.d[i]);
    for(unsigned int i=0;i<8;++i)add(output,s.a[i]);
    output.insert(output.end(),ram.begin(),ram.end());
    output.insert(output.end(),dev.pvc.begin(),dev.pvc.end());
    output.insert(output.end(),pal.banks[0].begin(),pal.banks[0].end());
    output.insert(output.end(),pal.banks[1].begin(),pal.banks[1].end());
    add_ports(output,result.head_ports);
    add_ports(output,result.node_ports);
    add_ports(output,result.controller_ports);
    for(std::size_t i=0;i<result.waits.size();++i) {
        const ms5::AnimationFrameWait& w=result.waits[i];
        add(output,static_cast<std::uint32_t>(w.segment));add(output,w.pc);add(output,w.address);add(output,w.size);
        add(output,w.before);add(output,w.released);
    }
    for(std::size_t i=0;i<result.irqs.size();++i) {
        const ms5::AnimationFrameIrq& q=result.irqs[i];
        add(output,static_cast<std::uint32_t>(q.segment));add(output,q.wait_pc);add(output,q.sequence);add(output,q.ports_begin);add(output,q.ports_end);
        add(output,q.external_reads);add(output,q.bios_resumes);add(output,q.rte_sr);
    }
    add_ports(output,result.irq_ports);
    for(std::size_t i=0;i<dev.reads.size();++i) {add(output,dev.reads[i].address);add(output,dev.reads[i].size);add(output,dev.reads[i].value);}
    return true;
}
int main(int argc,char** argv) {
    if(argc!=9) {std::cerr<<"usage: frame_irq_acceptance PROGRAM_ROM_0.ms5d ... PROGRAM_ROM_7.ms5d\n";return 2;}
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
