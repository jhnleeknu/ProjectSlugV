#include "ms5/object_sound_lookup.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram,unsigned int at,unsigned int size,std::uint32_t value) {
    assert(at<=ram.size() && size<=ram.size()-at);
    for(unsigned int i=0;i<size;++i)ram[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
unsigned int get(const std::vector<std::uint8_t>& ram,unsigned int at,unsigned int size=2) {
    assert(at<=ram.size() && size<=ram.size()-at);unsigned int value=0;
    for(unsigned int i=0;i<size;++i)value=(value<<8)|ram[at+i];return value;
}
ms5::ObjectSoundLookupState initial() {
    ms5::ObjectSoundLookupState s;
    for(unsigned int i=0;i<8;++i)s.sound.byte.registers.d[i]=0xabcd1200U+i;
    for(unsigned int i=0;i<5;++i)s.sound.byte.registers.a[i]=0x76540000U+i;
    s.a6=0x102000;return s;
}
bool same(const ms5::ObjectSoundLookupState& a,const ms5::ObjectSoundLookupState& b) {
    for(unsigned int i=0;i<8;++i)if(a.sound.byte.registers.d[i]!=b.sound.byte.registers.d[i])return false;
    for(unsigned int i=0;i<5;++i)if(a.sound.byte.registers.a[i]!=b.sound.byte.registers.a[i])return false;
    return a.a5==b.a5 && a.a6==b.a6 && a.phase==b.phase && a.saved_a0==b.saved_a0 &&
        a.sound.phase==b.sound.phase && a.sound.saved_low==b.sound.saved_low && a.sound.byte.waiting==b.sound.byte.waiting;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0x95c,2,0x5a01);ram[0x207e]=0x5a;ram[0x2012]=0x99;return ram;
}
std::vector<ms5::FixedDataResource> resources() {
    std::vector<ms5::FixedDataResource> windows(1);
    windows[0].source_cpu_address=windows[0].source_rom_offset=0x4411e;windows[0].data.resize(256);
    for(unsigned int i=0;i<128;++i)put(windows[0].data,i*2,2,i==0?0:0x1234+i);
    return windows;
}
unsigned int index(unsigned int value) {return (value>=0x40 && value<=0xbf)?0x80:(value*2)&255;}
unsigned int result(unsigned int value) {return value==0?0:0x1233+value/2;}
void failure(std::vector<std::uint8_t> ram,const std::vector<ms5::FixedDataResource>& windows,ms5::ObjectSoundLookupState state) {
    const std::vector<std::uint8_t> before=ram;const ms5::ObjectSoundLookupState saved=state;
    std::uint8_t reads=77;std::string error;
    assert(!ms5::execute_object_sound_lookup(ram,windows,state,255,reads,error));
    assert(!error.empty()&&ram==before&&same(state,saved)&&reads==77);
}
void all_low_bytes() {
    const std::uint32_t bases[]={0x108000,0x108002,0x1076a4,0x1176a2};
    const std::vector<ms5::FixedDataResource> windows=resources();
    for(unsigned int low=0;low<256;++low){
        std::vector<std::uint8_t> ram=fixture();ms5::ObjectSoundLookupState state=initial(),want=state;
        state.a5=want.a5=bases[low%4];put(ram,state.a5-0x76a4-0x100000,2,0x5a00|low);
        const unsigned int value=result(index(low));want.sound.byte.registers.a[0]=0x4411e;
        want.sound.byte.registers.d[0]=(want.sound.byte.registers.d[0]&0xffffff00U)|0x5a;
        want.sound.byte.registers.d[1]=value==0?0:(want.sound.byte.registers.d[1]&0xffff0000U)|value;
        std::vector<std::uint8_t> expected=ram;expected[0x2012]=static_cast<std::uint8_t>(value);
        std::uint8_t reads=99;std::string error="old";
        assert(ms5::execute_object_sound_lookup(ram,windows,state,0,reads,error));
        assert(error.empty()&&reads==0&&same(state,want)&&ram==expected);
    }
}
void sound_and_aliases() {
    const std::vector<ms5::FixedDataResource> windows=resources();
    for(unsigned int which=0;which<4;++which){
        std::vector<std::uint8_t> ram=fixture();ms5::ObjectSoundLookupState state=initial();
        put(ram,0x95c,2,0x20c1);ram[0x207e]=0;
        if(which==1)state.a6=0x1008df; // source-low BYTE changes c1 to20 before WORD read.
        if(which==2){put(ram,0x4d8a,2,0xbbda);put(ram,0x4d8c,2,0xbbda);} // queue append aliases source.
        if(which==3){ram[0x12]=1;ram[0xfd82]=1;} // external gate skips actual queue writes.
        std::uint8_t reads=77;std::string error;
        assert(ms5::execute_object_sound_lookup(ram,windows,state,1,reads,error));
        const unsigned int expected_index=which==1?0x40:which==2?0x80:0x82;
        assert(state.phase==0&&state.saved_a0==0&&state.sound.phase==0&&!state.sound.byte.waiting&&state.sound.saved_low==0);
        assert(state.sound.byte.registers.d[0]==0xabcd1ac0&&state.sound.byte.registers.d[1]==(0xabcd0000U|result(expected_index)));
        assert(state.sound.byte.registers.a[0]==0x4411e&&ram[state.a6+0x12-0x100000]==static_cast<std::uint8_t>(result(expected_index)));
        assert(reads==(which==3?1:0));
        if(which==1)assert(get(ram,0x95c)==0x2020);
        if(which==2)assert(get(ram,0x95c)==0x1ac0);
        if(which==3)assert(get(ram,0x4d8c)==0);
        else assert(get(ram,0x4d8c)==(which==2?4:2));
    }
}
ms5::ObjectSoundLookupState begin_wait(std::vector<std::uint8_t>& ram,unsigned int target) {
    ram=fixture();ram[0x207e]=0;
    put(ram,0x4d8a,2,0);put(ram,0x4d8c,2,6);put(ram,0x4d74,2,target);put(ram,0x4d76,2,0);
    put(ram,0x4d82,2,0x0455);put(ram,0x4d84,2,0x0566);put(ram,0x4d86,2,0x0677);
    ms5::ObjectSoundLookupState state=initial();std::uint8_t reads=77;std::string error;
    assert(ms5::execute_object_sound_lookup(ram,std::vector<ms5::FixedDataResource>(),state,0,reads,error));
    assert(reads==0&&state.phase==1&&state.saved_a0==0x10095c&&state.sound.phase==target&&state.sound.byte.waiting&&state.sound.saved_low==0x55);
    return state;
}
void waits() {
    const std::vector<ms5::FixedDataResource> windows=resources();
    for(unsigned int target=1;target<=2;++target){
        std::vector<std::uint8_t> ram;ms5::ObjectSoundLookupState state=begin_wait(ram,target),captured=state;
        put(ram,0x95c,2,0x1234);ram[0x207e]=0x12;ram[0x12]=1;ram[0xfd82]=1;ram[0xfd8d]=0;ram[0x4d7e]=1;
        const std::vector<std::uint8_t> held=ram;std::uint8_t reads=77;std::string error;
        assert(ms5::execute_object_sound_lookup(ram,std::vector<ms5::FixedDataResource>(),state,255,reads,error));
        assert(reads==0&&ram==held&&same(state,captured));
        ms5::ObjectSoundLookupState bad=state;bad.a5=0x108002;failure(ram,windows,bad);
        put(ram,0x4d74,2,0xffff);
        failure(ram,std::vector<ms5::FixedDataResource>(),state); // Sound writes complete, then lookup fails: whole transaction rolls back.
        bad=state;bad.sound.byte.registers.a[0]=0x110000;failure(ram,windows,bad);
        assert(ms5::execute_object_sound_lookup(ram,windows,state,255,reads,error));
        assert(reads==0&&state.phase==0&&state.saved_a0==0&&state.sound.phase==0&&state.sound.saved_low==0&&!state.sound.byte.waiting);
        assert(state.sound.byte.registers.d[0]==0xabcd1a55); // Actual pending low55, not requested commandc0.
        assert(state.sound.byte.registers.d[1]==(0xabcd0000U|result(0x68))&&ram[0x2012]==static_cast<std::uint8_t>(result(0x68)));
    }
    std::vector<std::uint8_t> ram;ms5::ObjectSoundLookupState state=begin_wait(ram,1);
    put(ram,0x4d74,2,2);std::uint8_t reads=77;std::string error;
    assert(ms5::execute_object_sound_lookup(ram,std::vector<ms5::FixedDataResource>(),state,255,reads,error));
    assert(state.phase==1&&state.sound.phase==2&&state.saved_a0==0x10095c&&state.sound.saved_low==0x55&&state.sound.byte.waiting&&reads==0);
    put(ram,0x4d74,2,0xffff);assert(ms5::execute_object_sound_lookup(ram,windows,state,255,reads,error));assert(state.phase==0);
}
void lookup_and_errors() {
    std::vector<std::uint8_t> ram=fixture();ms5::ObjectSoundLookupState state=initial();
    std::vector<ms5::FixedDataResource> windows=resources();
    failure(ram,std::vector<ms5::FixedDataResource>(),state);
    std::vector<ms5::FixedDataResource> bad=windows;bad.push_back(windows[0]);failure(ram,bad,state);
    bad=windows;bad[0].data.resize(3);failure(ram,bad,state); // query1 reads offset2..3, second BYTE missing.
    bad=windows;ms5::FixedDataResource overlap;overlap.source_cpu_address=overlap.source_rom_offset=0x44121;overlap.data.push_back(0);
    bad.push_back(overlap);failure(ram,bad,state); // Complete winner plus partial overlap remains ambiguous.
    bad=windows;bad[0].source_rom_offset++;failure(ram,bad,state);
    bad=windows;bad[0].source_cpu_address=bad[0].source_rom_offset=0xffff0;bad[0].data.resize(32);failure(ram,bad,state);
    // A fixed window may start odd while the actual reached WORD stays aligned.
    windows[0].source_cpu_address=windows[0].source_rom_offset=0x4411d;windows[0].data.insert(windows[0].data.begin(),0xa5);
    std::uint8_t reads=77;std::string error;assert(ms5::execute_object_sound_lookup(ram,windows,state,0,reads,error));assert(reads==0);
    windows=resources();ram=fixture();state=initial();state.a5=0x108001;ram[0x207e]=ram[0x95d];failure(ram,windows,state);
    state=initial();state.a5=0;failure(ram,windows,state);state.a5=0xffffffff;failure(ram,windows,state);
    state=initial();state.a5=0x108002;put(ram,0x95e,2,0x5a01);ram[0x207e]=0;failure(ram,windows,state); // Sound would require canonicalA5.
    ram=fixture();state=initial();state.a6=0xfffa0;ram[0x1e]=0x5a;failure(ram,windows,state); // compare/write at10001e fit, final output belowRAM.
    state=initial();state.a6=0xffffffff;failure(ram,windows,state);
    state=initial();state.phase=2;failure(ram,windows,state);
    state=initial();state.saved_a0=1;failure(ram,windows,state);
    state=initial();state.sound.saved_low=1;failure(ram,windows,state);
    state=initial();state.sound.phase=1;failure(ram,windows,state);
    state=initial();state.sound.byte.waiting=true;failure(ram,windows,state);
    state=initial();state.phase=1;failure(ram,windows,state);
    state.sound.phase=3;state.sound.byte.waiting=true;failure(ram,windows,state);
    ram.resize(65535);failure(ram,windows,initial());
}
}
int main(){all_low_bytes();sound_and_aliases();waits();lookup_and_errors();std::cout<<"object_sound_lookup_test passed\n";return 0;}
