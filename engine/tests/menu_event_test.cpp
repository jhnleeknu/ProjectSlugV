#include "ms5/menu_event.h"
#include "ms5/object_restart.h"
#include <cassert>
#include <iostream>
static void put(std::vector<std::uint8_t>& data, unsigned int at, std::uint32_t value) {
    for (unsigned int i=0;i<4;++i) data[at+i]=static_cast<std::uint8_t>(value>>(24-i*8));
}
static void failure(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& data) {
    const std::vector<std::uint8_t> before=ram;
    std::vector<ms5::VideoPortWrite> writes(1);
    writes[0].value=123;
    ms5::MenuEventResult result;
    result.a2=456;result.external_jump=789;
    std::string error;
    std::uint32_t d1=0xabcd1234U, d3=0x98767000U;
    std::uint16_t line=123;
    assert(!ms5::dispatch_menu_event(ram,data,3,0x7000,result,writes,error,
                                     NULL,NULL,&line,&d1,&d3));
    assert(d1==0xabcd1234U && d3==0x98767000U && line==123);
    assert(ram==before && writes.size()==1 && writes[0].value==123);
    assert(result.a2==456 && result.external_jump==789 && !error.empty());
}
int main() {
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0x7f0e,0x107efe);put(ram,0x7f12,0x107efe);put(ram,0x7efe,0x200);
    ram[0x7f04]=1;
    ms5::FixedDataResource data;
    data.source_cpu_address=data.source_rom_offset=0x200;
    data.data.assign(30,0);put(data.data,26,0xffffffffU);
    put(data.data,20,0x9532);
    ms5::MenuEventResult result;
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    const std::vector<std::uint8_t> before=ram;
    assert(ms5::dispatch_menu_event(ram,data,3,0x7000,result,writes,error));
    assert(result.external_jump==0xc00444 && result.a2==0x107efe && writes.empty() && ram==before);
    {
        data.data[24]=0x56;data.data[25]=0x78;
        std::uint32_t d1=0xabcd1234U, d3=0x98767000U;
        std::uint16_t line=123;
        assert(ms5::dispatch_menu_event(ram,data,3,0x7000,result,writes,error,
                                        NULL,NULL,&line,&d1,&d3));
        assert(d1==0xabcd5678U && d3==0x98767000U && line==0x7000);
        assert(result.external_jump==0xc00444 && ram==before && writes.empty());
        put(data.data,20,0);
        d1=0xabcd1234U;
        assert(ms5::dispatch_menu_event(ram,data,3,0x7000,result,writes,error,
                                        NULL,NULL,&line,&d1,&d3));
        assert(d1==0xabcd5678U && d3==0x98767000U && line==0x7000);
        assert(result.external_jump==0 && ram==before && writes.empty());
        result.a2=456;result.external_jump=789;line=123;
        assert(!ms5::dispatch_menu_event(ram,data,3,0x7001,result,writes,error,
                                         NULL,NULL,&line,&d1,&d3));
        assert(ram==before && writes.empty() && result.a2==456 && result.external_jump==789);
        assert(d1==0xabcd5678U && d3==0x98767000U && line==123);
    }
    put(data.data,20,0x949a);
    failure(ram,data); // Missing child resource leaves all state/outputs unchanged.
    put(data.data,20,0x1234);
    failure(ram,data);
    put(data.data,20,0x950c);
    ram[0x8f4]=1; // object+10 trap
    failure(ram,data);
    ram[0x8f4]=0;
    ram[0x950]=8; // object+6c cleanup trap
    failure(ram,data);
    ram[0x950]=0;
    put(ram,0xd4f6,0x12345678); // invalid attached coordinate parent: late failure
    failure(ram,data);
    put(ram,0xd4f6,0);
    std::uint32_t restart_d1=0xabcd1234U, restart_d3=0x98767000U;
    std::uint16_t restart_line=123;
    assert(ms5::dispatch_menu_event(ram,data,3,0x7000,result,writes,error,
                                    NULL,NULL,&restart_line,&restart_d1,&restart_d3));
    assert(restart_d1==0xffffffffU && restart_d3==0U && restart_line==0U);
    assert(ram[0x8e4]==0 && ram[0x8e5]==0 && ram[0x8e6]==0xca && ram[0x8e7]==0x22);
    assert(writes.size()==1 && writes[0].address==0x300001 && writes[0].value==3 && writes[0].size==1);
    assert(ram[0x7dfb]==1 && ram[0x7f1b]==2 && result.external_jump==0);
    {
        std::vector<std::uint8_t> inactive=ram;
        inactive[0x950]=0xff;
        std::uint32_t d1=0xabcd1234U, d3=0x98767000U;
        std::vector<ms5::VideoPortWrite> ports;
        assert(ms5::restart_static_object(inactive,0x1008e4,0xca22,3,ports,error,&d1,&d3));
        assert(d1==0xffffffffU && d3==0x98767000U);
        const std::vector<std::uint8_t> unchanged=inactive;
        d1=0xabcd1234U;
        assert(!ms5::restart_static_object(inactive,0x100001,0xca22,3,ports,error,&d1,&d3));
        assert(inactive==unchanged && d1==0xabcd1234U && d3==0x98767000U && ports.size()==1);
    }
    const std::vector<std::uint8_t> saved=ram;
    assert(!ms5::restart_static_object(ram,0x100001,0xca22,3,writes,error));
    assert(ram==saved && writes.size()==1);
    assert(!ms5::restart_static_object(ram,0x1008e4,0xca23,3,writes,error));
    assert(ram==saved && writes.size()==1);
    ram.resize(5);
    failure(ram,data);
    std::cout << "Menu event BIOS boundary and transactional failures passed\n";
}
