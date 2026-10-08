#include "ms5/animation_banked_lookup.h"
#include <cassert>
#include <iostream>
namespace {
typedef std::vector<std::uint8_t> Bytes;
typedef std::vector<ms5::FixedDataResource> Windows;
void put(Bytes& b,unsigned int at,unsigned int size,std::uint32_t value) {
    assert(at<=b.size() && size<=b.size()-at);
    for(unsigned int i=0;i<size;++i)b[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
ms5::FixedDataResource window(std::uint32_t cpu,std::uint32_t physical,unsigned int size,std::uint32_t value=0) {
    ms5::FixedDataResource w;w.source_cpu_address=cpu;w.source_rom_offset=physical;w.data.resize(size);
    if(size<=4)put(w.data,0,size,value);return w;
}
std::uint32_t read(const Bytes& ram,const Windows& windows,const ms5::ProgramBusState& bus,std::uint32_t address,unsigned int size) {
    std::uint32_t value=0xdeadbeef;std::string error="dirty";
    const bool ok=ms5::read_program_bus(ram,windows,bus,address,size,value,error);
    if(!ok)std::cerr<<"read failed address="<<std::hex<<address<<" size="<<size<<": "<<error<<"\n";
    assert(ok&&error.empty());return value;
}
void reject(const Bytes& ram,const Windows& windows,const ms5::ProgramBusState& bus,std::uint32_t address,unsigned int size) {
    std::uint32_t value=0xdeadbeef;std::string error;
    assert(!ms5::read_program_bus(ram,windows,bus,address,size,value,error));assert(value==0xdeadbeef&&!error.empty());
}
bool same(const ms5::SceneMapTransferState& a,const ms5::SceneMapTransferState& b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i])return false;
    for(unsigned int i=0;i<5;++i)if(a.a[i]!=b.a[i])return false;return true;
}
void bus_regions() {
    Bytes ram(65536);Windows w;ms5::ProgramBusState bus;
    assert(bus.bank_base==0x200000&&bus.vectors==NULL&&bus.pvc==NULL);
    put(ram,0xfffe,2,0xaabb);put(ram,0,2,0xccdd);
    assert(read(ram,w,bus,0x10fffe,4)==0xaabbccdd);
    assert(read(ram,w,bus,0x1afffe,4)==0xaabbccdd);
    assert(read(ram,w,bus,0x1110fffe,4)==0xaabbccdd);
    w.push_back(window(0x200000,0x300000,2,0x1234));bus.bank_base=0x300000;
    assert(read(ram,w,bus,0x1ffffe,4)==0xaabb1234);
    w.push_back(window(0xffffe,0xffffe,2,0x5678));
    assert(read(ram,w,bus,0xffffe,4)==0x5678ccdd);
    Bytes pvc(8192);put(pvc,0,2,0x9abc);bus.pvc=&pvc;
    w.push_back(window(0x2fdffe,0x3fdffe,2,0xdef0));
    assert(read(ram,w,bus,0x2fdffe,4)==0xdef09abc);
    // Structurally accepted legacy ROM bytes behind overlay never replace PVC.
    w.push_back(window(0x2fe000,0x3fe000,4,0x11112222));
    assert(read(ram,w,bus,0x2fe000,2)==0x9abc);bus.pvc=NULL;reject(ram,w,bus,0x2fe000,2);
    Bytes vectors(128);put(vectors,0x7e,2,0x1357);bus.vectors=&vectors;
    w.push_back(window(0x7f,0x7f,3));put(w.back().data,1,2,0x2468);
    assert(read(ram,w,bus,0x7e,4)==0x13572468);
    vectors.resize(127);reject(ram,w,bus,0x7e,2);
    assert(read(ram,w,bus,0x80,2)==0x2468); // Invalid unused vectors are ignored.
    bus.pvc=&vectors;assert(read(ram,w,bus,0x100000,2)==0xccdd);
    reject(ram,w,bus,0x2fe000,1);reject(ram,w,bus,0x300000,1);
    reject(ram,w,bus,0x100001,2);reject(ram,w,bus,0x100000,3);
    reject(Bytes(65535),w,bus,0x100000,1);
}
void resource_units() {
    Bytes ram(65536);Windows w;ms5::ProgramBusState bus;
    w.push_back(window(0x100,0x100,2,0x1234));w.push_back(window(0x102,0x102,2,0x5678));
    assert(read(ram,w,bus,0x100,4)==0x12345678); // Independent WORD windows.
    Windows first_only(1,w[0]);reject(ram,first_only,bus,0x100,4); // Failure after first WORD preserves output.
    Windows split;split.push_back(window(0x100,0x100,1,0x12));split.push_back(window(0x101,0x101,1,0x34));
    reject(ram,split,bus,0x100,2); // Never merge partial BYTE pieces.
    w.push_back(window(0x101,0x101,1,0xff));reject(ram,w,bus,0x100,2);w.pop_back();
    w.push_back(w[0]);reject(ram,w,bus,0x100,2);w.pop_back();
    ms5::FixedDataResource bad=window(0x100,0x101,2,0xffff);w.push_back(bad);
    assert(read(ram,w,bus,0x100,2)==0x1234); // Invalid metadata ignored.
    w.push_back(window(0x200004,0x300004,4,0xaabbccdd));
    w.push_back(window(0x200004,0x200004,4,0x11223344));bus.bank_base=0x300000;
    assert(read(ram,w,bus,0x1200004,4)==0xaabbccdd);
    bus.bank_base=0x300001;w.push_back(window(0x200005,0x300005,4,0x89abcdef));
    // Remove overlapping earlier bank3 bytes; selection follows physical span.
    w.erase(w.begin()+3);assert(read(ram,w,bus,0x200004,4)==0x89abcdef);
    bus.bank_base=0x800000;reject(ram,w,bus,0x200000,2);
    bus.bank_base=0xffffffff;reject(ram,w,bus,0x200000,1);
    bus.bank_base=0xfffff;reject(ram,w,bus,0x200000,1);
    assert(read(ram,w,bus,0x100000,2)==0); // Invalid unused bank accepted.
    Windows end;end.push_back(window(0x2fffec,0x7fffec,2,0xabcd));bus.bank_base=0x702000;
    assert(read(ram,end,bus,0x2fdfec,2)==0xabcd);
    reject(ram,end,bus,0x2fdffe,2); // v1kind2 cannot represent last16 physical bytes.
    bus.bank_base=0x702004;reject(ram,end,bus,0x2fdffe,2); // Physical span beyond8MiB.
}
void writes() {
    Bytes ram(65536);std::string error="dirty";
    assert(ms5::write_program_bus_ram(ram,0x1110fffe,4,0x12345678,error)&&error.empty());
    assert(ram[0xfffe]==0x12&&ram[0xffff]==0x34&&ram[0]==0x56&&ram[1]==0x78);
    const Bytes before=ram;
    assert(!ms5::write_program_bus_ram(ram,0x1ffffe,4,0xffffffff,error)&&ram==before);
    assert(!ms5::write_program_bus_ram(ram,0x100001,2,0,error)&&ram==before);
    assert(!ms5::write_program_bus_ram(ram,0xfffffffE,4,0,error)&&ram==before);
    assert(!ms5::write_program_bus_ram(ram,0x100000,0,0,error)&&ram==before);
    assert(ms5::write_program_bus_ram(ram,0x1f0123,1,0xab,error));assert(ram[0x123]==0xab);
}
ms5::SceneMapTransferState regs() {
    ms5::SceneMapTransferState r;for(unsigned int i=0;i<8;++i)r.d[i]=0xabcd8000U+i;
    for(unsigned int i=0;i<5;++i)r.a[i]=0x12340000U+i;r.a[1]=0x106001;return r;
}
void lookup_failure(Bytes ram,const Windows& w,const ms5::ProgramBusState& bus,ms5::SceneMapTransferState r,std::uint32_t a6) {
    const Bytes before=ram;const ms5::SceneMapTransferState saved=r;std::string error;
    assert(!ms5::execute_animation_banked_lookup(ram,w,bus,r,a6,error));assert(!error.empty()&&ram==before&&same(r,saved));
}
void lookups() {
    Bytes ram(65536);ram[0x6001]=0;put(ram,0x6002,2,0);put(ram,0x6004,2,2);put(ram,0x4002,4,0x89abcdef);
    Windows w;w.push_back(window(0x4a76c,0x4a76c,2,0x56));
    w.push_back(window(0x200004,0x300004,2,0x0010));w.push_back(window(0x200006,0x300006,2,0x4000));
    ms5::ProgramBusState bus;bus.bank_base=0x300000;
    ms5::SceneMapTransferState r=regs(),want=r;want.d[0]=0x56;want.d[7]=0x89abcdef;want.a[1]=0x106006;want.a[2]=0x104000;
    std::string error="dirty";assert(ms5::execute_animation_banked_lookup(ram,w,bus,r,0x100400,error));
    assert(error.empty()&&same(r,want)&&read(ram,Windows(),bus,0x100456,4)==0x89abcdef);
    // Store aliases the second source, command operands, or first pointer RAM.
    for(unsigned int alias=0;alias<3;++alias) {
        Bytes data(65536);data[0x6001]=0;put(data,0x6002,2,0x8000);put(data,0x6004,2,0xfffe);
        put(data,0x8004,4,0x104002);put(data,0x4000,4,0x76543210);
        const std::uint32_t dest=alias==0?0x104000:alias==1?0x106002:0x108004;
        r=regs();r.a[1]=0x11106001;want=r;want.d[0]=0x56;want.d[7]=0x76543210;want.a[1]=0x11106006;want.a[2]=0x104002;
        assert(ms5::execute_animation_banked_lookup(data,w,bus,r,dest-0x56,error));
        assert(same(r,want)&&read(data,Windows(),bus,dest,4)==0x76543210);
    }
    // First RAM pointer wraps32-bit indexed addition to declared vector view.
    Bytes v(128);put(v,0,4,0x11223344);bus.vectors=&v;
    ram[0x6001]=0;put(ram,0x6002,2,0x8000);put(ram,0x6004,2,0x20);put(ram,0x8004,4,0xffffffe0);
    r=regs();assert(ms5::execute_animation_banked_lookup(ram,w,bus,r,0x100400,error));assert(r.d[7]==0x11223344&&r.a[2]==0xffffffe0);
    // High bits stay in registers while24-bit address lines select PVC.
    Bytes pvc(8192);put(pvc,0,4,0xfedcba98);bus.pvc=&pvc;put(ram,0x8004,4,0x112fe000);put(ram,0x6004,2,0);
    r=regs();assert(ms5::execute_animation_banked_lookup(ram,w,bus,r,0x100400,error));assert(r.a[2]==0x112fe000&&r.d[7]==0xfedcba98);
    // BYTE selector ff doubles to01fe; signed field fffe subtracts2.
    // First LONG is a mixed RAM-mirror WORD and bank WORD, not a root read.
    Bytes mixed(65536);mixed[0x6001]=0xff;put(mixed,0x6002,2,0xfffa);put(mixed,0x6004,2,0);
    put(mixed,0xfffe,2,0x0010);put(mixed,0x4000,4,0xabcdef01);
    Windows mixed_windows;mixed_windows.push_back(window(0x4a96a,0x4a96a,2,0xfffe));
    mixed_windows.push_back(window(0x200000,0x300000,2,0x4000));
    r=regs();want=r;want.d[0]=0xfffe;want.d[7]=0xabcdef01;want.a[1]=0x106006;want.a[2]=0x104000;
    assert(ms5::execute_animation_banked_lookup(mixed,mixed_windows,bus,r,0x100002,error));
    assert(same(r,want)&&read(mixed,Windows(),bus,0x100000,4)==0xabcdef01);
    mixed_windows[0].data.resize(1);lookup_failure(mixed,mixed_windows,bus,regs(),0x100002);
    lookup_failure(ram,w,bus,regs(),0x1fffa8); // Last LONG partially outsideRAM; no partialstore.
    lookup_failure(ram,w,bus,regs(),0x100401); // Odd destination after all reads.
    Windows missing=w;missing.clear();lookup_failure(ram,missing,bus,regs(),0x100400);
    missing=w;missing.push_back(w[0]);lookup_failure(ram,missing,bus,regs(),0x100400);
    bus.pvc=NULL;lookup_failure(ram,w,bus,regs(),0x100400); // Late secondLONG device failure.
    put(ram,0x6002,2,0);bus.bank_base=0x800000;lookup_failure(ram,w,bus,regs(),0x100400);
}

ms5::PhysicalRomResource physical(std::uint32_t at,unsigned int size,std::uint32_t value=0) {
    ms5::PhysicalRomResource w;w.source_rom_offset=at;w.data.resize(size);if(size<=4)put(w.data,0,size,value);return w;
}
void physical_storage() {
    Bytes ram(65536);Windows legacy;ms5::ProgramBusState bus;assert(bus.physical_rom==NULL);
    std::vector<ms5::PhysicalRomResource> raw;
    // Eight maximum-size chunks include every physical byte, even tails not
    // expressible by legacykind2 windows. Values here are synthetic, not ROM.
    for(unsigned int bank=0;bank<8;++bank) {
        raw.push_back(physical(bank*0x100000,0x100000));
        for(unsigned int i=0;i<16;++i)raw.back().data[0xffff0+i]=static_cast<std::uint8_t>(bank*16+i);
    }
    bus.physical_rom=&raw;
    for(unsigned int bank=1;bank<8;++bank) {
        bus.bank_base=bank*0x100000+0x2000;
        for(unsigned int i=0;i<16;++i)assert(read(ram,legacy,bus,0x2fdff0+i,1)==bank*16+i);
    }
    // An even busWORD can have odd physical start and straddle chunk boundary.
    raw[1].data[0xfffff]=0xab;raw[2].data[0]=0xcd;bus.bank_base=0x1fffff;
    assert(read(ram,legacy,bus,0x200000,2)==0xabcd);
    bus.bank_base=0x7fffff;reject(ram,legacy,bus,0x200000,2);
    assert(read(ram,legacy,bus,0x200000,1)==127); // Last physical byte, no ROM wrap.
    bus.bank_base=0x800000;reject(ram,legacy,bus,0x200000,1);
    raw.clear();raw.push_back(physical(0x100,1,0x12));raw.push_back(physical(0x101,1,0x34));
    assert(read(ram,legacy,bus,0x100,2)==0x1234); // Typedkind3 may join individual bytes.
    raw.push_back(raw[1]);reject(ram,legacy,bus,0x100,2);raw.pop_back();
    raw[1].source_rom_offset=0x102;reject(ram,legacy,bus,0x100,2);raw[1].source_rom_offset=0x101;
    raw.push_back(physical(0x101,2,0x3456));reject(ram,legacy,bus,0x100,2);raw.pop_back();
    raw.push_back(physical(0x800000,1,0xff));raw.push_back(physical(0,0));
    raw.push_back(physical(0x100,0x100001)); // Invalid metadata ignored despite reached overlap.
    assert(read(ram,legacy,bus,0x100,2)==0x1234);
    legacy.push_back(window(0x100,0x100,2,0x1234));reject(ram,legacy,bus,0x100,2); // Equal bytes still ambiguous.
    legacy[0].data.resize(1);reject(ram,legacy,bus,0x100,2); // No legacy/kind3 stitching.
    raw[0].source_rom_offset=0x104;reject(ram,legacy,bus,0x100,2); // Partial legacy + physical secondBYTE is not allowed.
    legacy.clear();raw.clear();raw.push_back(physical(0x100,2,0x5678));
    legacy.push_back(window(0x100,0x101,2,0xffff)); // Invalid legacy is ignored.
    assert(read(ram,legacy,bus,0x100,2)==0x5678);
    // A LONG failure on its second WORD still preserves the public output.
    reject(ram,legacy,bus,0x100,4);
    // Device windows win over physical storage, including missing views.
    raw.clear();raw.push_back(physical(0,128));raw.push_back(physical(0x2fe000,2,0xaaaa));
    reject(ram,legacy,bus,0,2);reject(ram,legacy,bus,0x2fe000,2);
    Bytes vectors(128);put(vectors,0,2,0xbbbb);bus.vectors=&vectors;
    Bytes pvc(8192);put(pvc,0,2,0xcccc);bus.pvc=&pvc;
    assert(read(ram,legacy,bus,0,2)==0xbbbb&&read(ram,legacy,bus,0x2fe000,2)==0xcccc);
    // Isolated lookup consumes onlykind3: first physicalWORD starts odd and
    // crosses an adjacent storage boundary; register publication stays exact.
    raw.clear();legacy.clear();raw.push_back(physical(0x4a76c,2,0xfffe));
    raw.push_back(physical(0x1fffff,1,0));raw.push_back(physical(0x200000,3,0x104000));
    bus.bank_base=0x1ffffb;ram[0x6001]=0;put(ram,0x6002,2,0);put(ram,0x6004,2,0);put(ram,0x4000,4,0x89abcdef);
    ms5::SceneMapTransferState state=regs(),want=state;want.d[0]=0xfffe;want.d[7]=0x89abcdef;want.a[1]=0x106006;want.a[2]=0x104000;
    std::string error;assert(ms5::execute_animation_banked_lookup(ram,legacy,bus,state,0x100402,error));
    assert(same(state,want)&&read(ram,Windows(),bus,0x100400,4)==0x89abcdef);
    raw[2].data.resize(2);lookup_failure(ram,legacy,bus,regs(),0x100402); // Gap after first physicalWORD.
    bus.physical_rom=NULL;assert(read(ram,legacy,bus,0x100000,2)==0);
    assert(read(ram,legacy,bus,0,2)==0xbbbb);reject(ram,legacy,bus,0x100,2);
}

}
int main() {bus_regions();resource_units();writes();lookups();physical_storage();std::cout<<"program_bus_test passed\n";}
