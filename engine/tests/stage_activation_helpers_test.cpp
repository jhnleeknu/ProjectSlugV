#include "ms5/stage_activation_helpers.h"
#include <cassert>
#include <iostream>
namespace {
ms5::ObjectRestartState initial(){ms5::ObjectRestartState s;for(unsigned int i=0;i<8;++i)s.d[i]=0xabcd1234U+i*0x10001U;
    for(unsigned int i=0;i<7;++i)s.a[i]=0x87654321U+i*2;s.a[5]=0x108000;s.a[6]=0x100b30;return s;}
bool same(const ms5::ObjectRestartState& a,const ms5::ObjectRestartState& b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i])return false;
    for(unsigned int i=0;i<7;++i)if(a.a[i]!=b.a[i])return false;return true;}
std::vector<ms5::VideoPortWrite> old_ports(){std::vector<ms5::VideoPortWrite> p(1);p[0].size=1;p[0].address=0x300001;p[0].value=0x55;return p;}
void put(std::vector<std::uint8_t>& ram,std::uint32_t address,unsigned int size,std::uint32_t value){assert(address>=0x100000 && address<=0x110000-size);
    for(unsigned int i=0;i<size;++i)ram[address-0x100000+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));}
void failure(std::vector<std::uint8_t> ram,std::uint32_t entry,ms5::ObjectRestartState s){const std::vector<std::uint8_t> before=ram;const ms5::ObjectRestartState saved=s;
    for(unsigned int input=0;input<2;++input){bool carry=input!=0;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(!ms5::execute_stage_activation_helper(ram,entry,s,carry,ports,error));assert(!error.empty()&&ram==before&&same(s,saved)&&carry==(input!=0));
        assert(ports.size()==1&&ports[0].size==1&&ports[0].address==0x300001&&ports[0].value==0x55);}}
void status_helpers(){const unsigned int values[]={0,1,2,5,255};
    for(unsigned int i=0;i<5;++i)for(unsigned int j=0;j<5;++j)for(unsigned int which=0;which<2;++which){
        std::vector<std::uint8_t> ram(65536,0x53),expected;ms5::ObjectRestartState s=initial(),want=s;std::string error="old";
        const std::uint32_t entry=which?0xbee:0x4e216;
        if(which){s.a[5]=want.a[5]=0xffffffff;ram[0xf004]=0xa5;ram[0xfdb6]=values[i];ram[0xfdb7]=values[j];}
        else{++s.a[5];want.a[5]=s.a[5];ram[0xa45]=values[i];ram[0xb09]=values[j];}
        expected=ram;bool first=which?(values[i]==1||values[i]==2):(values[i]==0||values[i]==5);
        bool success=which?(first||values[j]==1||values[j]==2):(first&&(values[j]==0||values[j]==5));
        if(which){want.d[0]=(want.d[0]&0xffffff00U)|0xa5;want.d[1]=(want.d[1]&0xffffff00U)|(first?values[i]:values[j]);want.a[0]=first?0x10fdb7:0x10fdb8;expected[0xf004]=success?0xa5:0;}
        else want.d[0]=(want.d[0]&0xffffff00U)|(first?values[j]:values[i]);
        bool carry=!success;std::vector<ms5::VideoPortWrite> ports=old_ports();assert(ms5::execute_stage_activation_helper(ram,entry,s,carry,ports,error));
        assert(error.empty()&&carry==success&&same(s,want)&&ram==expected&&ports.empty());
    }
    std::vector<std::uint8_t> ram(65536,0);ms5::ObjectRestartState s=initial();s.a[5]=0x1175bb;ram[0xffff]=2;
    bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;assert(ms5::execute_stage_activation_helper(ram,0x4e216,s,carry,ports,error));assert(!carry);
    ram[0xffff]=0;failure(ram,0x4e216,s);
}
void signed_alias(){const int values[]={-32768,-1,0,1,32767};
    for(unsigned int i=0;i<5;++i)for(unsigned int j=0;j<5;++j)for(unsigned int alias=0;alias<2;++alias){
        std::vector<std::uint8_t> ram(65536,0x53);ms5::ObjectRestartState s=initial(),want=s;
        put(ram,0x108d3e,2,static_cast<std::uint16_t>(values[i]));put(ram,0x108d46,2,static_cast<std::uint16_t>(values[j]));
        s.a[6]=alias?0x108d29:0xfffeb;want.a[6]=s.a[6];std::vector<std::uint8_t> expected=ram;const std::size_t at=s.a[6]+0x15-0x100000;
        expected[at]=values[i]<values[j]?(expected[at]|4U):(expected[at]&0xfbU);want.d[0]=(want.d[0]&0xffff0000U)|static_cast<std::uint16_t>(values[i]);
        bool carry=alias!=0;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(ms5::execute_stage_activation_helper(ram,0x16ed2,s,carry,ports,error));assert(carry==(alias!=0)&&same(s,want)&&ram==expected&&ports.empty());
    }
}
void animation(){const std::uint32_t bases[]={0x100b30,0x10ffd2,0xfffea,0xfffe8};
    for(unsigned int i=0;i<4;++i){std::vector<std::uint8_t> ram(65536,0x53);ms5::ObjectRestartState s=initial(),want=s;s.a[6]=want.a[6]=bases[i];s.a[1]=want.a[1]=0x81234567;
        const std::uint32_t pointer=s.a[6]+0x26;want.a[0]=pointer;std::vector<std::uint8_t> expected=ram;
        put(expected,s.a[6]+0x18,1,0);put(expected,0x100010,2,0);put(expected,pointer,4,s.a[1]);put(expected,pointer+4,2,0);put(expected,pointer+6,2,s.d[0]);
        bool carry=i%2;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(ms5::execute_stage_activation_helper(ram,0x49f8c,s,carry,ports,error));assert(carry==bool(i%2)&&same(s,want)&&ram==expected);
        assert(ports.size()==2&&ports[0].size==2&&ports[0].address==0x2ffff2&&ports[0].value==0x1000&&ports[1].size==2&&ports[1].address==0x2ffff0&&ports[1].value==0);
        if(i==2)assert(ram[0x10]==0x81&&ram[0x11]==0x23);if(i==3)assert(ram[0x10]==0x45&&ram[0x11]==0x67);
    }
}
void errors(){std::vector<std::uint8_t> ram(65536,0x53);ms5::ObjectRestartState s=initial();
    // LONG at 10fffa and WORD at 10fffe fit; the final WORD at 110000
    // fails after earlier RAM writes and both candidate PVC port writes.
    s.a[6]=0x10ffd4;failure(ram,0x49f8c,s);s=initial();
    s.a[6]=0x10ffda;failure(ram,0x49f8c,s);s=initial();s.a[5]=0x108002;failure(ram,0x49f8c,s);
    s=initial();s.a[6]=0x100b31;failure(ram,0x49f8c,s);s=initial();s.a[6]=0xffffffff;failure(ram,0x49f8c,s);
    s=initial();s.a[6]=0x110000;failure(ram,0x16ed2,s);s=initial();s.a[5]=0x108001;failure(ram,0x16ed2,s);
    failure(ram,0,initial());s=initial();s.a[5]=0;failure(ram,0x4e216,s);
    ram.resize(65535);failure(ram,0xbee,initial());}
}
int main(){status_helpers();signed_alias();animation();errors();std::cout<<"stage_activation_helpers_test: passed\n";return 0;}
