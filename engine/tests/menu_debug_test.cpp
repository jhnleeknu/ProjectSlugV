#include "ms5/menu_debug.h"
#include "ms5/menu_text.h"
#include "ms5/fixed_text.h"
#include <cassert>
#include <iostream>
static void put(std::vector<std::uint8_t>& data,unsigned int at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)data[at+i]=static_cast<std::uint8_t>(value>>(24-i*8));
}
int main() {
    ms5::FixedDataResource font;
    font.source_cpu_address=font.source_rom_offset=0xe80c8;
    font.data.assign(512,0);
    for(unsigned int i=0;i<256;++i) {font.data[i*2]=3;font.data[i*2+1]=static_cast<std::uint8_t>(i);}
    std::vector<ms5::VideoPortWrite> writes(1);
    writes[0].value=123;
    std::uint16_t line=456;
    std::string error;
    std::vector<std::uint8_t> script;
    script.push_back('@');script.push_back('.');
    assert(!ms5::trace_table_fixed_text(script,0x7000,0x6b,font,writes,error,&line));
    assert(writes.size()==1 && writes[0].value==123 && line==456);
    script.push_back('a');script.push_back(0);
    assert(ms5::trace_table_fixed_text(script,0xffff,0xf6b,font,writes,error,&line));
    assert(writes.size()==1 && writes[0].size==4 && writes[0].value==0xfffff380U && line==0xffff);
    // A resource containing only font68 is valid for streams using only 68.
    ms5::FixedDataResource kana_font = font;
    kana_font.source_cpu_address = kana_font.source_rom_offset = 0xe82c8;
    script.assign(1, 'A');script.push_back(0);
    assert(ms5::trace_table_fixed_text(script,0x7000,0x268,kana_font,writes,error));
    assert(writes.size()==1 && writes[0].value==0x70002341U);
    // A late switch to an absent table must roll back earlier writes and line.
    script.clear();
    script.push_back('A');script.push_back(92);script.push_back('c');
    script.push_back(0x6b);script.push_back('B');script.push_back(0);
    line=456;
    assert(!ms5::trace_table_fixed_text(script,0x7000,0x68,kana_font,writes,error,&line));
    assert(writes.size()==1 && writes[0].value==0x70002341U && line==456);
    // Direct font3 emits '@' literally and does not combine the following mark.
    script.clear();script.push_back('@');script.push_back(0xb3);
    script.push_back(0xde);script.push_back(0);
    assert(ms5::trace_table_fixed_text(script,0xffe0,0xf03,font,writes,error));
    assert(writes.size()==6 && writes[0].value==0xffe0f340U);
    assert(writes[1].size==2 && writes[1].value==0x8200U);
    assert(writes[2].value==0x0000f3b3U && writes[4].value==0x0020f3deU);
    // Font30 uses the same direct tiles, but consumes a combining mark first.
    assert(ms5::trace_table_fixed_text(script,0xffe0,0xf30,font,writes,error));
    assert(writes.size()==4 && writes[0].value==0xffe0f340U && writes[2].value==0x0000f3e0U);
    script.assign(1,'A');script.push_back(0);
    line=456;
    assert(!ms5::trace_table_fixed_text(script,0x7000,0x69,font,writes,error,&line));
    assert(writes.size()==4 && line==456);
    ms5::FixedDataResource data;
    data.source_cpu_address=data.source_rom_offset=0x99e0;
    data.data.assign(0xc8,0);
    data.data[3]='O';data.data[4]='N';data.data[5]=' ';
    data.data[7]='O';data.data[8]='F';data.data[9]='F';
    put(data.data,0xe,0x99e3);
    put(data.data,0x1e,0x99e3);put(data.data,0x22,0x9aa8);
    put(data.data,0x28,0xffffffffU);
    data.data[0xb8]=15;
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0x7f0e,0x107efe);put(ram,0x7f12,0x107efe);put(ram,0x7efe,0x99ee);
    ram[0x7f04]=1;
    std::uint32_t a2=789;
    line=456;
    const std::vector<std::uint8_t> before=ram;
    const std::vector<ms5::VideoPortWrite> saved=writes;
    std::uint32_t d1=0xabcdef12U,d3=0xdead01c8U;
    assert(!ms5::dispatch_debug_menu(ram,data,NULL,3,line,a2,writes,error,&d1,&d3));
    assert(d1==0xabcdef12U && d3==0xdead01c8U);
    assert(ram==before && a2==789 && line==456 && writes[0].value==saved[0].value);
    assert(ms5::dispatch_debug_menu(ram,data,&font,3,line,a2,writes,error,&d1,&d3));
    assert(d1==0x6bU && (d3>>16)==0xdeadU && (d3&0xffffU)==line);
    assert(ram[0xf000]==0x80 && ram[0xf001]==0 && writes.size()==3 && a2==0x107efe);
    assert(ms5::dispatch_debug_menu(ram,data,&font,1,line,a2,writes,error));
    assert(ram[0xf000]==0 && ram[0xf001]==0 && writes.size()==3);
    d1=0xabcdef12U;d3=0xdead0000U|line;
    assert(ms5::dispatch_debug_menu(ram,data,NULL,4,line,a2,writes,error,&d1,&d3));
    assert(d1==0xabcdef12U && d3==(0xdead0000U|line));
    assert(ram[0x7f1b]==2 && writes.empty());
    ram[0x7f02]=3;
    put(ram,0x7f16,0x3650);
    assert(ms5::draw_menu_text(ram,data,true,0x7000,writes,error,&line,&font));
    assert(line==0x72a1);
    line=456;
    assert(!ms5::draw_menu_text(ram,data,true,0x7000,writes,error,&line));
    assert(line==456);
    data.data[0xb8]=16;
    const std::vector<std::uint8_t> before_bad_map=ram;
    assert(!ms5::dispatch_debug_menu(ram,data,&font,1,line,a2,writes,error));
    assert(ram==before_bad_map && line==456);
    data.data[0xb8]=15;
    writes.clear();
    font.data.resize(511);
    const std::vector<std::uint8_t> before_bad_font=ram;
    assert(!ms5::dispatch_debug_menu(ram,data,&font,2,line,a2,writes,error));
    assert(ram==before_bad_font && writes.empty());
    std::cout << "Debug menu font requirement, bit15 and output rollback passed\n";
}
