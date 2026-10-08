#include "ms5/stage_counter.h"
#include <cassert>
#include <iostream>
namespace {
ms5::ObjectRestartState initial(std::uint32_t a5=0x108000) {
    ms5::ObjectRestartState s;
    for(unsigned int i=0;i<8;++i)s.d[i]=0xabcd1234U+i*0x10001U;
    for(unsigned int i=0;i<7;++i)s.a[i]=0x87654321U+i*2;
    s.a[5]=a5;return s;
}
bool same(const ms5::ObjectRestartState& a,const ms5::ObjectRestartState& b) {
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i])return false;
    for(unsigned int i=0;i<7;++i)if(a.a[i]!=b.a[i])return false;
    return true;
}
std::size_t offset(std::uint32_t base,int displacement) {
    const std::int64_t at=static_cast<std::int64_t>(base)+displacement-0x100000;
    assert(at>=0 && at<65536);return static_cast<std::size_t>(at);
}
void failure(std::vector<std::uint8_t> ram,ms5::ObjectRestartState s) {
    const std::vector<std::uint8_t> saved=ram;const ms5::ObjectRestartState saved_state=s;std::string error;
    assert(!ms5::execute_stage_counter(ram,s,error));assert(!error.empty()&&ram==saved&&same(s,saved_state));
}
void gates() {
    const unsigned int values[]={0,1,2,255};
    for(unsigned int i=0;i<4;++i)for(unsigned int j=0;j<4;++j) {
        std::vector<std::uint8_t> ram(65536,0x53),saved;
        ram[0xd683]=0x10;ram[0xfdb6]=static_cast<std::uint8_t>(values[i]);ram[0xfdb7]=static_cast<std::uint8_t>(values[j]);
        ms5::ObjectRestartState s=initial(),want=s;std::string error;
        if(values[i]!=1 && values[j]!=1) {
            saved=ram;want.d[0]&=0xffffff00U;want.d[1]&=0xffffff00U;
            assert(ms5::execute_stage_counter(ram,s,error));assert(ram==saved&&same(s,want));
        } else {
            ram[0xd67e]=0x10;ram[0xd67f]=2;saved=ram;saved[0xd67f]=0;
            want.d[0]&=0xffffff00U;want.d[1]=(want.d[1]&0xffffff00U)|0x10;want.d[2]=0;
            assert(ms5::execute_stage_counter(ram,s,error));assert(ram==saved&&same(s,want));
        }
    }
    // Disabled first gate must skip invalid status addresses.
    ms5::ObjectRestartState s=initial(0x108249),want=s;std::vector<std::uint8_t> ram(65536,0);
    const std::vector<std::uint8_t> saved=ram;std::string error="old";
    assert(ms5::execute_stage_counter(ram,s,error));assert(error.empty()&&ram==saved&&same(s,want));
}
void counter_vectors() {
    struct Case {std::uint16_t input,output;bool clear;};
    const Case cases[]={{0x1002,0x1000,false},{0x1000,0x09fe,false},{0x0000,0,true},
        {0xa000,0x99fe,false},{0xa002,0xa000,false},{0x9f02,0x9f00,false},{0xff01,0xfeff,false},
        {0x0a00,0x09fe,false},{0x0b00,0x0afe,false},{0x0a02,0x0a00,false},
        {0x0002,0,false},{0x0100,0x00fe,false},{0x1010,0x100e,false},
        {0x9999,0x9997,false},{0xffff,0xfffd,false},{0x0001,0,true}};
    const std::uint32_t bases[]={0x108000,0x108001,0x108002};
    for(unsigned int b=0;b<3;++b)for(unsigned int i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        ms5::ObjectRestartState s=initial(bases[b]),want=s;std::vector<std::uint8_t> ram(65536,0x35);
        ram[offset(s.a[5],0x5683)]=0x10;ram[offset(s.a[5],0x7db6)]=1;ram[offset(s.a[5],0x7db7)]=0;
        ram[offset(s.a[5],0x567e)]=static_cast<std::uint8_t>(cases[i].input>>8);
        ram[offset(s.a[5],0x567f)]=static_cast<std::uint8_t>(cases[i].input);
        std::vector<std::uint8_t> expected=ram;
        expected[offset(s.a[5],0x567e)]=static_cast<std::uint8_t>(cases[i].output>>8);
        expected[offset(s.a[5],0x567f)]=static_cast<std::uint8_t>(cases[i].output);
        want.d[0]=cases[i].clear?0:(want.d[0]&0xffffff00U)|(cases[i].output&255U);
        want.d[1]=cases[i].clear?0:(want.d[1]&0xffffff00U)|(cases[i].output>>8);want.d[2]=0;
        std::string error;assert(ms5::execute_stage_counter(ram,s,error));assert(error.empty()&&ram==expected&&same(s,want));
    }
}
void errors() {
    std::vector<std::uint8_t> ram(65536,0);ms5::ObjectRestartState s=initial(0x108249);
    ram[offset(s.a[5],0x5683)]=16;ram[offset(s.a[5],0x7db6)]=1;
    // Even true first status cannot short-circuit the failing second read.
    failure(ram,s);
    s=initial(0xfa97d);ram.assign(65536,0);ram[offset(s.a[5],0x5683)]=16;
    ram[offset(s.a[5],0x7db6)]=1;ram[offset(s.a[5],0x7db7)]=0;
    // Both SEQ effects occur before the reached counter address fails below RAM.
    failure(ram,s);failure(ram,initial(0xffffffff));failure(ram,initial(0));
    ram.resize(65535);failure(ram,initial());ram.resize(65537);failure(ram,initial());
}
}
int main(){gates();counter_vectors();errors();std::cout<<"stage_counter_test: passed\n";return 0;}
