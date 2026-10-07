#include "ms5/stage_area_menu.h"
#include "ms5/menu_event.h"
#include "ms5/menu_stack.h"
#include <cassert>
#include <cstring>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& data,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)data[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
std::uint32_t get(const std::vector<std::uint8_t>& data,std::size_t at) {
    return (static_cast<std::uint32_t>(data[at])<<24)|(static_cast<std::uint32_t>(data[at+1])<<16)|
           (static_cast<std::uint32_t>(data[at+2])<<8)|data[at+3];
}
void fail(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& menu,
          const ms5::FixedDataResource* font,const ms5::StageGroupMenuContext* context,
          std::uint16_t event) {
    const std::vector<std::uint8_t> before=ram;
    std::uint16_t line=123;std::uint32_t a2=456;
    std::uint32_t d1=0x1234abcdU,d3=0x5678007bU;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].value=789;
    std::string error;
    assert(!ms5::dispatch_stage_area_menu(ram,menu,font,context,event,line,a2,writes,error,&d1,&d3));
    assert(d1==0x1234abcdU && d3==0x5678007bU);
    assert(ram==before && line==123 && a2==456 && writes.size()==1 && writes[0].value==789);
}
}
int main() {
    ms5::FixedDataResource menu;
    menu.source_cpu_address=menu.source_rom_offset=0x955e;
    menu.data.assign(0xa4,0);
    const char format[]="\\c0%1x:%2x %s";
    std::memcpy(&menu.data[0],format,sizeof(format));
    const char clear[]="                          \\r";
    std::memcpy(&menu.data[0xe],clear,sizeof(clear));
    for(unsigned int i=0;i<10;++i) {
        put(menu.data,0x3cU+i*10U,i==1U?0xfffffffeU:0x956cU);
        put(menu.data,0x40U+i*10U,i>=2U?0x9602U:0U);
    }
    put(menu.data,0xa0,0xffffffffU);
    ms5::StageCatalog catalog;catalog.groups.resize(19);
    for(unsigned int i=0;i<19;++i) {
        ms5::StageGroup& group=catalog.groups[i];group.source_cpu_address=0x40000U+i*0x100U;
        if(i>=8)continue;
        for(unsigned int j=0;j<3;++j) {
            ms5::StageRecord record;record.source_cpu_address=group.source_cpu_address+4U+j*30U;
            record.data.assign(28,0);record.data[18]=92;record.data[19]='c';record.data[20]='h';
            record.data[21]=static_cast<std::uint8_t>('A'+j);group.records.push_back(record);
        }
    }
    ms5::FixedDataResource font;
    font.source_cpu_address=font.source_rom_offset=0xe80c8;font.data.assign(1024,0);
    ms5::FixedDataResource prefix;
    prefix.source_cpu_address=prefix.source_rom_offset=0;
    prefix.data.push_back(0);prefix.data.push_back(0x10);prefix.data.push_back(0xf3);prefix.data.push_back(0);
    ms5::StageGroupMenuContext context;
    context.catalog=&catalog;context.null_name=&prefix;context.callback_stack=0x1feffc;
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0x7f0e,0x107efe);put(ram,0x7f12,0x107efe);put(ram,0x7efe,0x958a);
    put(ram,0x7f16,0x3650);ram[0x7f02]=12;ram[0x7f04]=10;
    ram[0x7f05]=4;ram[0x7f06]=4;ram[0x7f09]=30;
    std::uint16_t line=0;std::uint32_t a2=0;std::string error;
    std::vector<ms5::VideoPortWrite> writes;
    assert(ms5::dispatch_stage_area_menu(ram,menu,&font,&context,0,line,a2,writes,error));
    assert(ram[0x7dfe]==2 && ram[0x7e07]==3 && ram[0x7e08]==1 && a2==0x107efe);
    assert(ms5::dispatch_stage_area_menu(ram,menu,&font,&context,1,line,a2,writes,error));
    assert(ram[0x7e01]==2 && ram[0x7e08]==3);
    assert(ms5::dispatch_stage_area_menu(ram,menu,&font,&context,2,line,a2,writes,error));
    assert(ram[0x7e01]==0 && ram[0x7e08]==1);
    fail(ram,menu,NULL,&context,1);fail(ram,menu,&font,NULL,2);
    font.data.resize(512);fail(ram,menu,&font,&context,1);font.data.resize(1024);
    context.callback_stack=0x10f300;fail(ram,menu,&font,&context,5);context.callback_stack=0x1feffc;
    // Event 3 changes the selection state without altering full D1/D3.
    std::uint32_t d1=0x1234abcdU,d3=0x56787088U;
    line=0x7088U;
    ram[0x7e01]=2;
    assert(ms5::dispatch_stage_area_menu(ram,menu,NULL,NULL,3,line,a2,writes,error,&d1,&d3));
    assert(d1==0x1234abcdU && d3==0x56787088U && line==0x7088U);
    assert(ram[0xd680]==2 && ram[0xd681]==2 && ram[0x7dfb]==1 && ram[0x7f1b]==2);
    ram[0x7dfa]=0xab;ram[0x7dfb]=0xcd;
    assert(ms5::dispatch_stage_area_menu(ram,menu,NULL,NULL,4,line,a2,writes,error));
    assert(ram[0x7dfa]==0xab && ram[0x7dfb]==0xcd);
    // Drawing installs the final script style and preserves the D3 high word.
    assert(ms5::dispatch_stage_area_menu(ram,menu,&font,&context,5,line,a2,writes,error,&d1,&d3));
    assert(d1==0x68U && (d3&0xffff0000U)==0x56780000U &&
           static_cast<std::uint16_t>(d3)==line);
    const std::vector<std::uint8_t> before_mismatch=ram;
    const std::uint32_t before_d1=d1,before_d3=d3;
    line^=1U;
    const std::uint16_t mismatch_line=line;
    assert(!ms5::dispatch_stage_area_menu(ram,menu,&font,&context,5,line,a2,writes,error,&d1,&d3));
    assert(ram==before_mismatch && d1==before_d1 && d3==before_d3 && line==mismatch_line);
    line=static_cast<std::uint16_t>(d3);
    ram[0x7dfe]=6;ram[0x7f05]=0;ram[0x7f06]=4;
    assert(ms5::dispatch_stage_area_menu(ram,menu,&font,&context,6,line,a2,writes,error));
    assert(ram[0x7f05]==8 && ram[0x7f06]==8 && ram[0x7f0c]==0 && ram[0x7e07]==7);
    assert(get(ram,0x4ce4)==context.callback_stack-20U);
    ram[0x7f06]=1;fail(ram,menu,&font,&context,5);
    // Parent drawing mutates formatter RAM before child configuration. A late
    // invalid child must roll back those changes and all prepared video writes.
    put(menu.data,0x2c,0x956c); // Full-menu drawing also needs its header title.
    const std::vector<std::uint8_t> before_push=ram;
    writes.assign(1,ms5::VideoPortWrite());writes[0].value=789;
    assert(!ms5::push_menu(ram,menu,0x200,4,8,0x7000,writes,error,&font,&context));
    assert(ram==before_push && writes.size()==1 && writes[0].value==789);
    assert(!ms5::push_menu(ram,menu,0x958a,4,8,0x7000,writes,error,&font));
    assert(ram==before_push && writes.size()==1 && writes[0].value==789);
    assert(ms5::push_menu(ram,menu,0x958a,4,8,0x7000,writes,error,&font,&context));
    assert(get(ram,0x7f0e)==0x107eee && get(ram,0x7f12)==0x107efe);
    assert(get(ram,0x4ce4)==context.callback_stack && !writes.empty());
    assert(ram[0x7f1b]==1 && ram[0x7ef2]==0);
    std::cout << "Stage area wrap, nested navigation stack and late-error rollback passed\n";
}
