#include "ms5/stage_readiness.h"
#include <cassert>
#include <iostream>
namespace {
ms5::ObjectRestartState initial(std::uint32_t a5=0x108000){
    ms5::ObjectRestartState s;for(unsigned int i=0;i<8;++i)s.d[i]=0xabcd1234U+i*0x10001U;
    for(unsigned int i=0;i<7;++i)s.a[i]=0x87654321U+i*2;s.a[5]=a5;return s;
}
bool same(const ms5::ObjectRestartState& a,const ms5::ObjectRestartState& b){
    for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i])return false;
    for(unsigned int i=0;i<7;++i)if(a.a[i]!=b.a[i])return false;return true;
}
void put(std::vector<std::uint8_t>& ram,std::uint32_t address,unsigned int size,std::uint32_t value){
    assert(address>=0x100000 && address<=0x110000-size);const std::size_t at=address-0x100000;
    for(unsigned int i=0;i<size;++i)ram[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
void object(std::vector<std::uint8_t>& ram,std::uint32_t a5,unsigned int index,std::uint32_t marker,
    unsigned int flag61=0,unsigned int a8=0){
    const std::uint32_t at=a5-(index?0x7258:0x7348);put(ram,at,4,marker);put(ram,at+0x61,1,flag61);put(ram,at+0xa8,1,a8);
}
void descriptor(std::vector<std::uint8_t>& ram,std::uint32_t a5,unsigned int index,unsigned int type,unsigned int status,unsigned int flags=0){
    const std::uint32_t at=a5+(index?0x5d18:0x5d12);put(ram,at,1,type);put(ram,at+2,1,status);put(ram,at+4,2,flags);
}
void failure(const std::vector<std::uint8_t>& ram,ms5::ObjectRestartState s){
    const ms5::ObjectRestartState saved=s;const std::vector<std::uint8_t> before=ram;bool carry=true;std::string error;
    assert(!ms5::execute_stage_readiness(ram,s,carry,error));assert(!error.empty()&&same(s,saved)&&carry&&ram==before);
}
void masks(){
    const std::uint32_t bases[]={0x108000,0x108002,0x107ffe};
    for(unsigned int b=0;b<3;++b)for(unsigned int mask=0;mask<4;++mask)for(unsigned int flag=0;flag<2;++flag){
        ms5::ObjectRestartState s=initial(bases[b]),want=s;std::vector<std::uint8_t> ram(65536,0x53);
        object(ram,s.a[5],0,0x270e);object(ram,s.a[5],1,0x270e);
        put(ram,s.a[5]+0x5684,1,flag);put(ram,s.a[5]-0x75bc,1,mask&1?2:0);put(ram,s.a[5]-0x74f8,1,mask&2?2:255);
        want.d[0]=flag?1:mask;want.a[0]=s.a[5]-0x7258;
        const std::vector<std::uint8_t> before=ram;bool carry=false;std::string error="old";
        assert(ms5::execute_stage_readiness(ram,s,carry,error));assert(error.empty()&&carry==(flag||mask)&&same(s,want)&&ram==before);
    }
}
void record_paths(){
    struct Case{unsigned int type,status,flags;bool ready,loads;};
    const Case cases[]={{1,3,0,false,true},{1,4,0,false,true},{2,5,0,false,true},
        {1,2,0,true,true},{2,6,0,true,true},{2,255,0,true,true},{1,0,0,true,true},
        {0,3,0,true,false},{3,4,0,true,false},{1,3,0x8000,true,false},{2,5,0xffff,true,false}};
    for(unsigned int player=0;player<2;++player)for(unsigned int i=0;i<sizeof(cases)/sizeof(cases[0]);++i){
        ms5::ObjectRestartState s=initial(),want=s;std::vector<std::uint8_t> ram(65536,0);
        object(ram,s.a[5],0,player?0x270e:0x123456);object(ram,s.a[5],1,player?0x123456:0x270e);
        descriptor(ram,s.a[5],player,cases[i].type,cases[i].status,cases[i].flags);ram[0xd684]=1;
        want.d[0]=(!cases[i].ready && player==0)?0:1;
        want.a[0]=(!cases[i].ready && player==0)?0x100cb8:0x100da8;want.a[4]=player?0x10dd18:0x10dd12;
        if(cases[i].loads)want.d[1]=(want.d[1]&0xffffff00U)|cases[i].status;
        bool carry=false;std::string error;assert(ms5::execute_stage_readiness(ram,s,carry,error));
        assert(carry==cases[i].ready&&same(s,want));
    }
    // a8 bit4 takes priority over flag61 bit7 and skips descriptor access.
    std::vector<std::uint8_t> ram(65536,0);ms5::ObjectRestartState s=initial(),want=s;
    object(ram,s.a[5],0,1,128,16);object(ram,s.a[5],1,0x270e);ram[0xd684]=1;
    want.d[0]=1;want.a[0]=0x100da8;bool carry=false;std::string error;
    assert(ms5::execute_stage_readiness(ram,s,carry,error));assert(carry&&same(s,want));
}
void bounds(){
    std::vector<std::uint8_t> ram(65536,0);ms5::ObjectRestartState s=initial(0x117258),want=s;
    object(ram,s.a[5],0,1,128,0);want.d[0]=0;want.a[0]=0x10ff10;
    bool carry=true;std::string error;assert(ms5::execute_stage_readiness(ram,s,carry,error));assert(!carry&&same(s,want));
    // First player passes, but the second player's LONG is outside RAM.
    object(ram,s.a[5],0,0x270e);failure(ram,initial(0x117258));
    // Both inactive skip descriptors whose WORD addresses are outside RAM.
    ram.assign(65536,0);s=initial(0x10a2ee);object(ram,s.a[5],0,0x270e);object(ram,s.a[5],1,0x270e);
    put(ram,s.a[5]+0x5684,1,1);assert(ms5::execute_stage_readiness(ram,s,carry,error));assert(carry);
    // Actual record WORD fails after both first-player gates and scratch changes.
    object(ram,s.a[5],0,1);failure(ram,initial(0x10a2ee));
    failure(ram,initial(0x108001));failure(ram,initial(0));failure(ram,initial(0xffffffff));
    ram.resize(65535);failure(ram,initial());ram.resize(65537);failure(ram,initial());
    // 4e166 first BYTE below RAM is reached only with final flag0.
    ram.assign(65536,0);s=initial(0x107348);object(ram,s.a[5],0,0x270e);object(ram,s.a[5],1,0x270e);
    put(ram,s.a[5]+0x5684,1,1);assert(ms5::execute_stage_readiness(ram,s,carry,error));assert(carry);
    put(ram,s.a[5]+0x5684,1,0);failure(ram,initial(0x107348));
}
}
int main(){masks();record_paths();bounds();std::cout<<"stage_readiness_test: passed\n";return 0;}
