#include "ms5/sound_byte_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& r,unsigned int at,unsigned int v) {r[at]=static_cast<std::uint8_t>(v>>8);r[at+1]=static_cast<std::uint8_t>(v);}
bool same(const ms5::SoundByteExecutionState& a,const ms5::SoundByteExecutionState& b) {
    if(a.waiting!=b.waiting)return false;
    for(unsigned int i=0;i<8;++i)if(a.registers.d[i]!=b.registers.d[i])return false;
    for(unsigned int i=0;i<5;++i)if(a.registers.a[i]!=b.registers.a[i])return false;
    return true;
}
}
int main() {
    std::vector<std::uint8_t> r(65536,0);ms5::SoundByteExecutionState s;std::string e;
    s.registers.d[0]=0xabcd0003;s.registers.d[1]=0x87654321;s.registers.a[0]=0xffffffff;
    put(r,0x4d76,0x8000);put(r,0x4d74,0xffff);
    assert(ms5::execute_sound_byte(r,s,e));assert(r[0x4d7b]==255 && s.registers.d[1]==0x87654321 && s.registers.a[0]==0xffffffff);
    // Invalid destination remains opaque until a waiting producer is released.
    s.registers.d[0]=0x55;put(r,0x4d74,1);
    assert(ms5::execute_sound_byte(r,s,e));assert(s.waiting && s.registers.a[0]==0x0fccf4 && s.registers.d[1]==0x87650001);
    put(r,0x4d74,0);std::vector<std::uint8_t> old=r;ms5::SoundByteExecutionState saved=s;
    assert(!ms5::execute_sound_byte(r,s,e));assert(r==old && same(s,saved));
    s.waiting=false;put(r,0x4d76,127);put(r,0x4d74,0);
    assert(ms5::execute_sound_byte(r,s,e));assert(s.waiting && s.registers.a[0]==0x104d73);
    put(r,0x4d76,0x8000);assert(ms5::execute_sound_byte(r,s,e));assert(s.waiting && s.registers.a[0]==0x104d73);
    put(r,0x4d74,1);assert(ms5::execute_sound_byte(r,s,e));assert(!s.waiting && r[0x4d73]==0x55 && r[0x4d76]==0 && r[0x4d77]==0);
    s.waiting=false;put(r,0x4d76,0);put(r,0x4d74,0x0101);
    assert(ms5::execute_sound_byte(r,s,e));assert(!s.waiting);
    put(r,0x4d76,0);put(r,0x4d74,1);
    assert(ms5::execute_sound_byte(r,s,e));assert(s.waiting);
    put(r,0x4d74,0x8001);
    assert(ms5::execute_sound_byte(r,s,e));assert(!s.waiting);
    r.resize(65535);old=r;saved=s;assert(!ms5::execute_sound_byte(r,s,e));assert(r==old && same(s,saved));
    std::cout<<"sound_byte_execution_test passed\n";
}
