// Dedicated read-only unit fixture harness for run_animation_machine (no game/controller implementation, no files written).
// Length-prefixed BE packets on stdin/stdout. Request (BE u32):
//   pc, carry, bank_base, stop_pc, flags, wait_limit, external_status, NQ, d0..d7, a0..a7, then RAM 65536 bytes, PVC 8192 bytes, NQ x (address, size, value).
//   flags: bits 0..5 = declared releases enabled (0 ef2, 1 16bd0, 2 3aea, 3 cda4, 4 gate 47af0/478de, 5 BIOS card c00468 resume),
//          bit 6 = palette RAM attached (F6 scope decision E6): the request ends with bank 0 (8192 bytes), bank 1 (8192 bytes) and the
//          selected bank (u32 0/1), the run uses run_animation_machine_with_palette and a success response ends with the same three fields;
//          without bit 6 the run is run_animation_machine and the packets are unchanged.
//          bits 8..15 = BIOS card answer byte.
// Run: run_animation_machine to stop_pc; at every Waiting block the declared release of the current PC is applied (undeclared = error);
// when a run fails and the card release is enabled, the same state is re-run to c00468 and, when the BIOS card request is there
// (return address c37c on the stack), the answer is written to BYTE 10fdc6 and execution resumes at c37c (same protocol as the frame driver).
// Success response: 1, status, pc, carry, bank_base, external_reads, NP, NQleft, NW, d0..d7, a0..a7, RAM, PVC, NP x (address,size,value),
//   NQleft x (address,size,value), NW x (pc,address,size,before,released).
// Malformed request response: 2, 0, 0, error text. Failure response: 0, preserved (1 = the failing run call left RAM/state/device/queue exactly as before it), committed waits, error text.
#include "ms5/animation_machine.h"
#include "ms5/animation_machine_irq.h"
#include "ms5/physical_rom_resource.h"
#include <iostream>
#include <string>
#include <vector>

typedef std::vector<std::uint8_t> Bytes;
static const std::uint32_t CARD_BIOS=0xc00468U,CARD_RETURN=0xc37cU,CARD_ANSWER=0x10fdc6U;
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
    if(n>4194304U)return false;b.resize(n);
    if(n)std::cin.read(reinterpret_cast<char*>(&b[0]),n);
    return static_cast<std::uint32_t>(std::cin.gcount())==n;
}
static bool write_packet(const Bytes& b) {
    Bytes h;add(h,static_cast<std::uint32_t>(b.size()));
    std::cout.write(reinterpret_cast<const char*>(&h[0]),4);
    if(!b.empty())std::cout.write(reinterpret_cast<const char*>(&b[0]),b.size());
    std::cout.flush();return static_cast<bool>(std::cout);
}
static bool same_state(const ms5::AnimationMachineState& a,const ms5::AnimationMachineState& b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i]||a.a[i]!=b.a[i])return false;
    return a.pc==b.pc&&a.carry==b.carry;
}
static bool same_device(const ms5::AnimationMachineDevice& a,const ms5::AnimationMachineDevice& b) {
    if(a.bank_base!=b.bank_base||a.pvc!=b.pvc||a.reads.size()!=b.reads.size())return false;
    for(std::size_t i=0;i<a.reads.size();++i)
        if(a.reads[i].address!=b.reads[i].address||a.reads[i].size!=b.reads[i].size||a.reads[i].value!=b.reads[i].value)return false;
    return true;
}
static bool same_palette(const ms5::AnimationMachinePaletteRam& a,const ms5::AnimationMachinePaletteRam& b) {
    return a.banks[0]==b.banks[0]&&a.banks[1]==b.banks[1]&&a.selected==b.selected;
}
// One run_animation_machine call, or run_animation_machine_with_palette when palette is attached.
static bool machine(Bytes& ram,const std::vector<ms5::FixedDataResource>& windows,const ms5::ProgramBusState& bus,ms5::AnimationMachineState& s,
    ms5::AnimationMachineDevice& dev,ms5::AnimationMachinePaletteRam* palette,std::uint32_t stop,std::uint8_t status_byte,std::uint32_t& reads,
    ms5::AnimationMachineStatus& status,std::vector<ms5::VideoPortWrite>& ports,std::string& error) {
    if(palette!=NULL)return ms5::run_animation_machine_with_palette(ram,windows,bus,s,dev,*palette,stop,status_byte,reads,status,ports,error);
    return ms5::run_animation_machine(ram,windows,bus,s,dev,stop,status_byte,reads,status,ports,error);
}
struct Wait {std::uint32_t pc,address,size,before,released;};
static const unsigned int REQUEST_WORDS=24;
// Applies the declared release of the Waiting PC; returns false (error set) when it is undeclared or not releasable.
static bool release_wait(Bytes& ram,const ms5::AnimationMachineState& s,std::uint32_t flags,std::vector<Wait>& waits,std::string& error) {
    Wait w;w.pc=s.pc;w.address=0;w.size=2;w.released=0;w.before=0;
    const std::uint32_t a5=s.a[5];
    if(s.pc==0xef2U&&(flags&1U)) {w.address=(a5-0x7feaU)&0xffffffU;w.size=1;w.released=ram_value(ram,(a5-0x7fe9U)&0xffffffU,1);}
    else if(s.pc==0x16bd0U&&(flags&2U)) {w.address=(a5+0xd34U)&0xffffffU;w.released=s.d[0]&0xffffU;}
    else if(s.pc==0x3aeaU&&(flags&4U)) {w.address=0x104d74U;w.released=0xffffU;}
    else if(s.pc==0xcda4U&&(flags&8U)) {w.address=0x108d34U;w.released=s.d[4]&0xffffU;}
    else if((s.pc==0x47af0U||s.pc==0x478deU)&&(flags&16U)) {
        if(ram_value(ram,0x107dea,2)!=0) {error="gate wait not released";return false;}
        w.address=0x107dedU;w.size=1;w.released=ram_value(ram,0x107ded,1)&0x7fU;
    } else {error="undeclared wait PC";return false;}
    w.before=ram_value(ram,w.address,w.size);
    ram_put(ram,w.address,w.size,w.released);
    waits.push_back(w);return true;
}
static bool run(const Bytes& input,const ms5::ProgramBusState& bus,Bytes& output,std::string& error) {
    std::size_t at=0;std::uint32_t v[REQUEST_WORDS];
    for(unsigned int i=0;i<REQUEST_WORDS;++i)if(!take(input,at,v[i])) {error="short request";return false;}
    const std::uint32_t nq=v[7],flags=v[4]&0xffU,answer=(v[4]>>8)&0xffU,limit=v[5],stop=v[3];
    const bool with_palette=(flags&64U)!=0U;
    if(nq>65536U||input.size()!=4U*REQUEST_WORDS+65536U+8192U+12U*nq+(with_palette?16388U:0U)||v[6]>255U||v[4]>0xffffU||v[1]>2U||limit>4096U) {
        error="invalid request";return false;}
    ms5::AnimationMachineState s;for(unsigned int i=0;i<8;++i){s.d[i]=v[8+i];s.a[i]=v[16+i];}
    s.pc=v[0];s.carry=static_cast<ms5::AnimationCarryState>(v[1]);
    Bytes ram(input.begin()+at,input.begin()+at+65536);at+=65536;
    ms5::AnimationMachineDevice dev;dev.bank_base=v[2];dev.pvc.assign(input.begin()+at,input.begin()+at+8192);at+=8192;
    for(std::uint32_t i=0;i<nq;++i) {
        ms5::AnimationMachineExternalRead e;std::uint32_t size=0;
        if(!take(input,at,e.address)||!take(input,at,size)||!take(input,at,e.value)||size>255U) {error="bad queue entry";return false;}
        e.size=static_cast<std::uint8_t>(size);dev.reads.push_back(e);
    }
    ms5::AnimationMachinePaletteRam pal;
    if(with_palette) {
        pal.banks[0].assign(input.begin()+at,input.begin()+at+8192);at+=8192;
        pal.banks[1].assign(input.begin()+at,input.begin()+at+8192);at+=8192;
        std::uint32_t selected=0;if(!take(input,at,selected)||selected>1U) {error="bad palette selection";return false;}
        pal.selected=static_cast<std::uint8_t>(selected);
    }
    ms5::AnimationMachinePaletteRam* palette=with_palette?&pal:NULL;
    const std::uint8_t status_byte=static_cast<std::uint8_t>(v[6]);
    std::vector<ms5::FixedDataResource> windows;
    std::vector<ms5::VideoPortWrite> ports;std::vector<Wait> waits;std::uint32_t reads=0;
    ms5::AnimationMachineStatus status=ms5::AnimationMachineReturned;
    unsigned int count=0;
    for(;;) {
        const Bytes saved_ram(ram);const ms5::AnimationMachineState saved_state(s);const ms5::AnimationMachineDevice saved_dev(dev);
        const ms5::AnimationMachinePaletteRam saved_pal(pal);
        std::vector<ms5::VideoPortWrite> phase;std::uint32_t consumed=0;std::string e1;
        if(!machine(ram,windows,bus,s,dev,palette,stop,status_byte,consumed,status,phase,e1)) {
            const bool preserved=ram==saved_ram&&same_state(s,saved_state)&&same_device(dev,saved_dev)&&same_palette(pal,saved_pal);
            bool resumed=false;
            if(flags&32U) {
                Bytes cram(saved_ram);ms5::AnimationMachineState cs(saved_state);ms5::AnimationMachineDevice cd(saved_dev);
                ms5::AnimationMachinePaletteRam cpal(saved_pal);
                std::vector<ms5::VideoPortWrite> cp;std::uint32_t cr=0;std::string ce;
                ms5::AnimationMachineStatus st=ms5::AnimationMachineWaiting;
                if(machine(cram,windows,bus,cs,cd,with_palette?&cpal:NULL,CARD_BIOS,status_byte,cr,st,cp,ce)&&st==ms5::AnimationMachineReturned&&
                    cs.pc==CARD_BIOS&&ram_value(cram,cs.a[7],4)==CARD_RETURN&&count<limit) {
                    ++count;Wait w;w.pc=CARD_BIOS;w.address=CARD_ANSWER;w.size=1;w.before=ram_value(cram,CARD_ANSWER,1);w.released=answer;
                    ram_put(cram,CARD_ANSWER,1,answer);waits.push_back(w);
                    cs.pc=CARD_RETURN;cs.a[7]+=4;cs.carry=ms5::AnimationCarryUnknown;
                    ram.swap(cram);s=cs;dev=cd;pal=cpal;ports.insert(ports.end(),cp.begin(),cp.end());reads+=cr;resumed=true;
                }
            }
            if(resumed)continue;
            // The caller's state must be what the failing call left: report preservation of that call.
            output.clear();add(output,0);add(output,preserved?1U:0U);add(output,static_cast<std::uint32_t>(waits.size()));
            output.insert(output.end(),e1.begin(),e1.end());
            return true;
        }
        reads+=consumed;ports.insert(ports.end(),phase.begin(),phase.end());
        if(status!=ms5::AnimationMachineWaiting)break;
        if(count>=limit) {output.clear();add(output,0);add(output,1);add(output,static_cast<std::uint32_t>(waits.size()));
            const std::string m("declared wait limit");output.insert(output.end(),m.begin(),m.end());return true;}
        ++count;
        std::string we;
        if(!release_wait(ram,s,flags,waits,we)) {output.clear();add(output,0);add(output,1);add(output,static_cast<std::uint32_t>(waits.size()));
            output.insert(output.end(),we.begin(),we.end());return true;}
    }
    add(output,1);add(output,static_cast<std::uint32_t>(status));add(output,s.pc);add(output,static_cast<std::uint32_t>(s.carry));
    add(output,dev.bank_base);add(output,reads);add(output,static_cast<std::uint32_t>(ports.size()));
    add(output,static_cast<std::uint32_t>(dev.reads.size()));add(output,static_cast<std::uint32_t>(waits.size()));
    for(unsigned int i=0;i<8;++i)add(output,s.d[i]);for(unsigned int i=0;i<8;++i)add(output,s.a[i]);
    output.insert(output.end(),ram.begin(),ram.end());output.insert(output.end(),dev.pvc.begin(),dev.pvc.end());
    for(std::size_t i=0;i<ports.size();++i) {add(output,ports[i].address);add(output,ports[i].size);add(output,ports[i].value);}
    for(std::size_t i=0;i<dev.reads.size();++i) {add(output,dev.reads[i].address);add(output,dev.reads[i].size);add(output,dev.reads[i].value);}
    for(std::size_t i=0;i<waits.size();++i) {add(output,waits[i].pc);add(output,waits[i].address);add(output,waits[i].size);add(output,waits[i].before);add(output,waits[i].released);}
    if(with_palette) {
        output.insert(output.end(),pal.banks[0].begin(),pal.banks[0].end());output.insert(output.end(),pal.banks[1].begin(),pal.banks[1].end());
        add(output,pal.selected);
    }
    return true;
}
int main(int argc,char** argv) {
    if(argc!=9) {std::cerr<<"usage: unit_fixture_acceptance PROGRAM_ROM_0.ms5d ... PROGRAM_ROM_7.ms5d\n";return 2;}
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
        if(!run(input,bus,output,error)) {output.clear();add(output,2);add(output,0);add(output,0);output.insert(output.end(),error.begin(),error.end());}
        if(!write_packet(output))return 2;
    }
    return 0;
}
