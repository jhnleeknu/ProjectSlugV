#include "../src/animation_machine_internal.h"
#include <cassert>
#include <iostream>
// Pinned MAME model evidence, not physical-hardware observation. Independent
// expected fields follow prot_pvc.cpp unpack/pack_color and get_bank_base, with
// neogeo.cpp write_bankprot_pvc applying effects after each merged WORD write.
namespace {
typedef std::vector<std::uint8_t> Bytes;
struct Fixture {
    Bytes ram;
    std::vector<ms5::FixedDataResource> windows;
    ms5::ProgramBusState bus;
    ms5::AnimationMachineState state;
    ms5::AnimationMachineDevice device;
    std::vector<ms5::VideoPortWrite> ports;
    std::string error;
    ms5::AnimationMachineContext c;
    Fixture() : ram(65536,0x5a),c(ram,windows,bus,state,device,ports,0x7b,error) {}
};
std::uint32_t get(const Bytes& bytes,unsigned int word) {
    return (static_cast<std::uint32_t>(bytes[2*word])<<8)|bytes[2*word+1];
}
void put(Bytes& bytes,unsigned int word,std::uint32_t value) {
    bytes[2*word]=static_cast<std::uint8_t>(value>>8);bytes[2*word+1]=static_cast<std::uint8_t>(value);
}
std::uint32_t packed(std::uint32_t gb,std::uint32_t sr) {
    // Independent per-channel bit placement: four high color bits become the
    // original low nibbles; each fifth color bit and shade occupy bits12..15.
    const std::uint32_t blue=gb&31U,green=(gb>>8)&31U,red=sr&31U,shade=(sr>>8)&1U;
    return (blue>>1)|((green>>1)<<4)|((red>>1)<<8)|((blue&1U)<<12)|
        ((green&1U)<<13)|((red&1U)<<14)|(shade<<15);
}
void unpacked(std::uint32_t pen,std::uint32_t& gb,std::uint32_t& sr) {
    const std::uint32_t b=2U*(pen&15U)+((pen>>12)&1U);
    const std::uint32_t g=2U*((pen>>4)&15U)+((pen>>13)&1U);
    const std::uint32_t r=2U*((pen>>8)&15U)+((pen>>14)&1U);
    gb=256U*g+b;sr=256U*((pen>>15)&1U)+r;
}
void port(const Fixture& f,unsigned int index,unsigned int size,std::uint32_t address,std::uint32_t value) {
    assert(index<f.ports.size());assert(f.ports[index].size==size);
    assert(f.ports[index].address==address&&f.ports[index].value==value);
}
void colors_exhaustive() {
    Fixture f;
    for(std::uint32_t pen=0;pen<=65535U;++pen) {
        f.ports.clear();std::uint32_t gb=0,sr=0;unpacked(pen,gb,sr);
        assert(ms5::am_write(f.c,0x2fffe0,2,pen));
        assert(get(f.device.pvc,0xff0)==pen);
        assert(get(f.device.pvc,0xff1)==gb&&get(f.device.pvc,0xff2)==sr);
        const std::uint32_t prior_sr=get(f.device.pvc,0xff5);
        assert(ms5::am_write(f.c,0x2fffe8,2,gb));
        assert(get(f.device.pvc,0xff6)==packed(gb,prior_sr));
        assert(ms5::am_write(f.c,0x2fffea,2,sr));
        assert(get(f.device.pvc,0xff6)==pen&&packed(gb,sr)==pen);
        assert(f.device.bank_base==0x200000&&f.ports.size()==3);
        port(f,0,2,0x2fffe0,pen);port(f,1,2,0x2fffe8,gb);port(f,2,2,0x2fffea,sr);
    }
}
void color_lanes_and_triggers() {
    Fixture f;put(f.device.pvc,0xff0,0x1234);
    assert(ms5::am_write(f.c,0xab2fffe0U,1,0xab));
    assert(get(f.device.pvc,0xff0)==0xab34);std::uint32_t gb=0,sr=0;unpacked(0xab34,gb,sr);
    assert(get(f.device.pvc,0xff1)==gb&&get(f.device.pvc,0xff2)==sr);port(f,0,1,0x2fffe0,0xab);
    assert(ms5::am_write(f.c,0x2fffe1,1,0xcd));unpacked(0xabcd,gb,sr);
    assert(get(f.device.pvc,0xff0)==0xabcd&&get(f.device.pvc,0xff1)==gb&&get(f.device.pvc,0xff2)==sr);
    port(f,1,1,0x2fffe1,0xcd);
    put(f.device.pvc,0xff4,0x1234);put(f.device.pvc,0xff5,0x5678);
    const std::uint32_t addresses[]={0x2fffe8,0x2fffe9,0x2fffea,0x2fffeb};
    const std::uint32_t values[]={0xab,0xcd,0xef,0x12};
    std::uint32_t expected_gb=0x1234,expected_sr=0x5678;
    for(unsigned int i=0;i<4;++i) {
        f.ports.clear();
        if(i==0)expected_gb=(expected_gb&255U)|0xab00U;
        if(i==1)expected_gb=(expected_gb&0xff00U)|0xcdU;
        if(i==2)expected_sr=(expected_sr&255U)|0xef00U;
        if(i==3)expected_sr=(expected_sr&0xff00U)|0x12U;
        assert(ms5::am_write(f.c,addresses[i],1,values[i]));
        assert(get(f.device.pvc,0xff4)==expected_gb&&get(f.device.pvc,0xff5)==expected_sr);
        assert(get(f.device.pvc,0xff6)==packed(expected_gb,expected_sr));port(f,0,1,addresses[i],values[i]);
    }
    // Output/register writes do not themselves cause recursive color effects.
    const unsigned int no_trigger[]={0xff1,0xff2,0xff3,0xff6,0xff7};
    for(unsigned int i=0;i<5;++i) {
        Bytes expected=f.device.pvc;put(expected,no_trigger[i],0x9876);
        assert(ms5::am_write(f.c,0x2fe000U+2U*no_trigger[i],2,0x9876));
        assert(f.device.pvc==expected&&f.device.bank_base==0x200000);
    }
    // LONG applies unpack first, then its second WORD overwrites ff1.
    f.ports.clear();assert(ms5::am_write(f.c,0xab2fffe0U,4,0xface1234));unpacked(0xface,gb,sr);
    assert(f.ports.size()==2);port(f,0,2,0x2fffe0,0xface);port(f,1,2,0x2fffe2,0x1234);
    assert(get(f.device.pvc,0xff0)==0xface&&get(f.device.pvc,0xff1)==0x1234&&get(f.device.pvc,0xff2)==sr);
}
struct ModelBank {
    std::uint32_t ff8,ff9,bank;
    ModelBank() : ff8(0x12ff),ff9(0x8001),bank(0x345678) {}
};
void bank_write(ModelBank& model,std::uint32_t address,unsigned int size,std::uint32_t value) {
    const unsigned int word=(address-0x2fe000U)/2U;
    if(word==0xff8 || word==0xff9) {
        std::uint32_t& merged=word==0xff8?model.ff8:model.ff9;
        if(size==2)merged=value&65535U;
        else if(address&1U)merged=(merged&0xff00U)|(value&255U);
        else merged=(merged&255U)|((value&255U)<<8);
    }
    // Primary get_bank_base consumes merged words before its two side effects.
    model.bank=0x100000U+(model.ff8>>8)+(model.ff9*256U);
    model.ff8=(model.ff8&0xfe00U)|0x00a0U;model.ff9=model.ff9&0x7fffU;
}
void write_and_check(Fixture& f,ModelBank& model,std::uint32_t address,unsigned int size,std::uint32_t value) {
    bank_write(model,address,size,value);f.ports.clear();
    assert(ms5::am_write(f.c,address,size,value));
    assert(f.device.bank_base==model.bank&&get(f.device.pvc,0xff8)==model.ff8&&get(f.device.pvc,0xff9)==model.ff9);
    assert(f.ports.size()==1);port(f,0,size,address&0xffffffU,value&(size==1?255U:65535U));
    std::uint32_t live=0;
    assert(ms5::am_read(f.c,0x2ffff0,2,live)&&live==model.ff8);
    assert(ms5::am_read(f.c,0x2ffff2,2,live)&&live==model.ff9);
}
void bank_matrix_and_partial_order() {
    const std::uint32_t values[]={0,1,0x7f,0x80,0xff,0x100,0x7fff,0x8000,0xffff};
    for(unsigned int i=0;i<9;++i)for(unsigned int j=0;j<9;++j)for(unsigned int order=0;order<2;++order) {
        Fixture f;ModelBank model;put(f.device.pvc,0xff8,model.ff8);put(f.device.pvc,0xff9,model.ff9);
        f.device.bank_base=model.bank;
        if(order==0) {
            write_and_check(f,model,0x2ffff0,2,values[i]);write_and_check(f,model,0x2ffff2,2,values[j]);
        } else {
            write_and_check(f,model,0x2ffff2,2,values[j]);write_and_check(f,model,0x2ffff0,2,values[i]);
        }
    }
    Fixture f;ModelBank model;put(f.device.pvc,0xff8,model.ff8);put(f.device.pvc,0xff9,model.ff9);
    write_and_check(f,model,0x2ffff2,1,0xff);
    assert(get(f.device.pvc,0xff9)==0x7f01); // High mask precedes following low-lane merge.
    write_and_check(f,model,0x2ffff3,1,0xab);assert(get(f.device.pvc,0xff9)==0x7fab);
    write_and_check(f,model,0x2ffff0,1,1);assert((f.device.bank_base&1U)==1U);
    write_and_check(f,model,0x2ffff1,1,0x21);assert((get(f.device.pvc,0xff8)&255U)==0xa0U);
    // A LONG crossing ff8/ff9 observes the first WORD's masks before second.
    f.ports.clear();bank_write(model,0x2ffff0,2,1);bank_write(model,0x2ffff2,2,0xffff);
    assert(ms5::am_write(f.c,0x2ffff0,4,0x0001ffff));
    assert(f.device.bank_base==model.bank&&get(f.device.pvc,0xff8)==model.ff8&&get(f.device.pvc,0xff9)==model.ff9);
    assert(f.ports.size()==2);port(f,0,2,0x2ffff0,1);port(f,1,2,0x2ffff2,0xffff);
    // Every ff8..fff WORD triggers bank update, including final odd BYTE.
    put(f.device.pvc,0xff8,0x03fe);put(f.device.pvc,0xff9,0x8123);model.ff8=0x03fe;model.ff9=0x8123;
    write_and_check(f,model,0x2ffffe,2,0x4567);assert(get(f.device.pvc,0xfff)==0x4567);
    write_and_check(f,model,0x2fffff,1,0x89);assert(get(f.device.pvc,0xfff)==0x4589);
}
void live_bus_and_non_device() {
    Fixture f;std::vector<ms5::PhysicalRomResource> physical(2);
    physical[0].source_rom_offset=0x200001;
    const unsigned char one[]={0x12,0x34,0x56,0x78};physical[0].data.assign(one,one+4);
    physical[1].source_rom_offset=0x300000;
    const unsigned char two[]={0xde,0xad,0xbe,0xef};physical[1].data.assign(two,two+4);
    f.c.bus.physical_rom=&physical;put(f.device.pvc,0xff8,0);put(f.device.pvc,0xff9,0x1000);
    assert(ms5::am_write(f.c,0x2ffff0,1,1)&&f.device.bank_base==0x200001);
    std::uint32_t result=0;
    assert(ms5::am_read(f.c,0x200000,4,result)&&result==0x12345678);
    assert(ms5::am_write(f.c,0x2ffff2,2,0x2000)&&f.device.bank_base==0x300000);
    assert(ms5::am_read(f.c,0x200000,4,result)&&result==0xdeadbeef);
    assert(ms5::am_write(f.c,0x2ffff2,2,0xffff));
    result=0x12345678;assert(!ms5::am_read(f.c,0x200000,1,result)&&result==0x12345678);
    const Bytes before_pvc=f.device.pvc;const std::uint32_t before_bank=f.device.bank_base;
    f.ports.clear();assert(ms5::am_write(f.c,0xab1ffffeU,2,0x1234));
    assert(f.ram[65534]==0x12&&f.ram[65535]==0x34);
    assert(f.device.pvc==before_pvc&&f.device.bank_base==before_bank&&f.ports.empty());
    assert(ms5::am_read(f.c,0x10fffe,2,result)&&result==0x1234);
    const Bytes before_ram=f.ram;
    assert(!ms5::am_write(f.c,0x300000,1,9));assert(!f.error.empty());
    assert(!ms5::am_write(f.c,0x2ffff1,2,9));assert(!ms5::am_write(f.c,0x2ffff0,3,9));
    assert(f.ram==before_ram&&f.device.pvc==before_pvc&&f.device.bank_base==before_bank&&f.ports.empty());
    assert(f.c.external_reads==0);
    assert(ms5::am_read(f.c,0xd00046,1,result)&&result==0x7b&&f.c.external_reads==1);
    assert(ms5::am_read(f.c,0xabd00046U,1,result)&&result==0x7b&&f.c.external_reads==2);
    result=0x12345678;assert(!ms5::am_read(f.c,0xd00046,2,result));
    assert(result==0x12345678&&f.c.external_reads==2);
}
ms5::AnimationMachineExternalRead ext(std::uint32_t address,std::uint8_t size,std::uint32_t value) {
    ms5::AnimationMachineExternalRead r;r.address=address;r.size=size;r.value=value;return r;
}
// Declared external-read queue: WORD 3c0006 and BYTE 300000 / 340000 / 380000 consume the front entry only when address and size match.
void external_read_queue() {
    Fixture f;std::uint32_t result=0x55555555U;const char* const empty="animation machine external read queue empty";
    const char* const mismatch="animation machine external read queue mismatch";
    // Default: empty queue, every queue device read is the checked error and leaves the result and counters alone.
    assert(f.device.reads.empty());
    assert(!ms5::am_read(f.c,0x3c0006,2,result)&&f.error==empty&&result==0x55555555U&&f.c.external_reads==0);
    assert(!ms5::am_read(f.c,0x300000,1,result)&&f.error==empty);assert(!ms5::am_read(f.c,0x340000,1,result)&&f.error==empty);
    assert(!ms5::am_read(f.c,0x380000,1,result)&&f.error==empty);
    // Other sizes at those addresses are not queue reads (the previous unsupported-device behaviour).
    f.device.reads.push_back(ext(0x3c0006,2,0x1234));
    assert(!ms5::am_read(f.c,0x3c0006,1,result)&&f.error!=empty&&f.error!=mismatch&&f.device.reads.size()==1);
    assert(!ms5::am_read(f.c,0x300000,2,result)&&f.error!=empty&&f.error!=mismatch&&f.device.reads.size()==1&&f.c.external_reads==0);
    // Mismatch: wrong address, wrong size in the entry, the entry stays at the front and nothing is counted.
    assert(!ms5::am_read(f.c,0x300000,1,result)&&f.error==mismatch&&f.device.reads.size()==1&&f.c.external_reads==0&&result==0x55555555U);
    f.device.reads.clear();f.device.reads.push_back(ext(0x3c0006,1,0x12));
    assert(!ms5::am_read(f.c,0x3c0006,2,result)&&f.error==mismatch&&f.device.reads.size()==1);
    f.device.reads.clear();
    // Ordered consumption across all four devices; values are masked to the access size; the 24-bit address is used.
    f.device.reads.push_back(ext(0x300000,1,0x1234));f.device.reads.push_back(ext(0x340000,1,0xa5));
    f.device.reads.push_back(ext(0x380000,1,0xffffff7fU));f.device.reads.push_back(ext(0x3c0006,2,0xabcd1234U));
    f.device.reads.push_back(ext(0x3c0006,2,0x8000));f.device.reads.push_back(ext(0x300000,1,0xff));
    assert(ms5::am_read(f.c,0xab300000U,1,result)&&result==0x34&&f.c.external_reads==1&&f.device.reads.size()==5);
    assert(!ms5::am_read(f.c,0x380000,1,result)&&f.error==mismatch&&f.device.reads.size()==5&&f.c.external_reads==1);
    assert(ms5::am_read(f.c,0x340000,1,result)&&result==0xa5&&f.c.external_reads==2);
    assert(ms5::am_read(f.c,0x380000,1,result)&&result==0x7f&&f.c.external_reads==3);
    assert(ms5::am_read(f.c,0x3c0006,2,result)&&result==0x1234&&f.c.external_reads==4);
    assert(ms5::am_read(f.c,0x3c0006,2,result)&&result==0x8000&&f.c.external_reads==5&&f.device.reads.size()==1);
    assert(ms5::am_read(f.c,0x300000,1,result)&&result==0xff&&f.c.external_reads==6&&f.device.reads.empty());
    assert(!ms5::am_read(f.c,0x300000,1,result)&&f.error==empty&&f.c.external_reads==6);
    // The d00046 external status is unaffected by the queue and keeps its own count.
    f.device.reads.push_back(ext(0x3c0006,2,7));
    assert(ms5::am_read(f.c,0xd00046,1,result)&&result==0x7b&&f.c.external_reads==7&&f.device.reads.size()==1);
}
}
int main() {
    colors_exhaustive();color_lanes_and_triggers();bank_matrix_and_partial_order();live_bus_and_non_device();external_read_queue();
    std::cout<<"animation_machine_device_test PASS (pinned model;65536pens)\n";
}
