#include "ms5/stage_group_menu.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& data,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)data[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
void expect_failure(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& menu,
                    const ms5::FixedDataResource* font,const ms5::StageGroupMenuContext* context) {
    const std::vector<std::uint8_t> before=ram;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].value=123;
    std::uint32_t a2=456;std::string error;
    assert(!ms5::dispatch_stage_group_menu(ram,menu,font,context,5,a2,writes,error));
    assert(ram==before && a2==456 && writes.size()==1 && writes[0].value==123 && !error.empty());
}
}
int main() {
    ms5::FixedDataResource menu;
    menu.source_cpu_address=menu.source_rom_offset=0x9780;
    menu.data.assign(0x82,0);
    const char format[]="FOR %s ";
    for(unsigned int i=0;i<sizeof(format);++i)menu.data[1+i]=format[i];
    for(unsigned int i=0;i<10;++i)put(menu.data,0x1eU + i*10,0x9802);
    put(menu.data,0x7e,0xffffffffU);
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0x7f0e,0x107efe);put(ram,0x7f12,0x107efe);put(ram,0x7efe,0x978a);
    ram[0x7f04]=10;ram[0x7f05]=0;ram[0x7f06]=0;
    ms5::StageCatalog catalog;catalog.groups.resize(19);
    for(unsigned int i=0;i<19;++i)catalog.groups[i].source_cpu_address=0x40000+i*4;
    ms5::FixedDataResource prefix;
    prefix.source_cpu_address=prefix.source_rom_offset=0;
    prefix.data.push_back(0);prefix.data.push_back(0x10);prefix.data.push_back(0xf3);prefix.data.push_back(0);
    ms5::FixedDataResource font;
    font.source_cpu_address=font.source_rom_offset=0xe80c8;font.data.assign(1024,0);
    ms5::StageGroupMenuContext context;
    context.catalog=&catalog;context.null_name=&prefix;context.callback_stack=0x1feffc;
    expect_failure(ram,menu,NULL,&context);
    expect_failure(ram,menu,&font,NULL);
    context.null_name=NULL;expect_failure(ram,menu,&font,&context);context.null_name=&prefix;
    const std::uint32_t bad_stacks[]={0,0x9784,0x10f300,0x110000,0x1feffd,0xffffff};
    for(unsigned int i=0;i<6;++i) {
        context.callback_stack=bad_stacks[i];expect_failure(ram,menu,&font,&context);
    }
    context.callback_stack=0x1feffc;
    std::uint32_t a2=0;std::vector<ms5::VideoPortWrite> writes;std::string error;
    assert(ms5::dispatch_stage_group_menu(ram,menu,&font,&context,5,a2,writes,error));
    assert(a2==context.callback_stack && writes.size()==16);
    assert((writes[8].value&65535U)==0x300U && (writes[10].value&65535U)==0x310U &&
           (writes[12].value&65535U)==0x3f3U);
    assert(ram[0x7e07]==1 && ram[0x7e0a]==0 && ram[0x7e0d]==0);
    ram[0x7f06]=9;
    assert(ms5::dispatch_stage_group_menu(ram,menu,NULL,NULL,3,a2,writes,error));
    assert(a2==0x107efe && ram[0xd680]==18 && ram[0xd681]==0 && ram[0x7dfb]==1 && ram[0x7f1b]==2);
    ram[0x7dfa]=0xab;ram[0x7dfb]=0xcd;
    assert(ms5::dispatch_stage_group_menu(ram,menu,NULL,NULL,4,a2,writes,error));
    assert(ram[0x7dfa]==0xab && ram[0x7dfb]==0xcd);
    ram[0x7f06]=10;expect_failure(ram,menu,&font,&context);
    std::cout << "Stage group menu selection, null-name bytes and transactional failures passed\n";
}
