#include "ms5/formatted_text.h"
#include <cassert>
#include <iostream>
#include <cstring>
namespace {
void put(std::vector<std::uint8_t>& bytes,std::size_t at,std::uint32_t value) {
    for(unsigned int i=0;i<4;++i)bytes[at+i]=static_cast<std::uint8_t>(value>>(24U-i*8U));
}
void text(ms5::FixedDataResource& resource,std::size_t at,const char* value) {
    const std::size_t count=std::strlen(value)+1;
    for(std::size_t i=0;i<count;++i)resource.data[at+i]=static_cast<std::uint8_t>(value[i]);
}
}
int main() {
    std::vector<ms5::FixedDataResource> resources(1);
    resources[0].source_cpu_address=resources[0].source_rom_offset=0x60000;
    resources[0].data.assign(8192,0);
    ms5::FixedDataResource font;
    font.source_cpu_address=font.source_rom_offset=0xe80c8;
    font.data.assign(1024,0);
    for(unsigned int i=0;i<512;++i) {
        font.data[2*i]=3;font.data[2*i+1]=static_cast<std::uint8_t>(i);
    }
    std::vector<std::uint8_t> ram(65536,0xa5);
    put(ram,0x7000,0x61000);
    std::vector<std::uint8_t> arguments;
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    text(resources[0],0,"X%s!");text(resources[0],0x1000,"AB");
    assert(ms5::format_fixed_text(ram,resources,font,0x60000,0x107000,arguments,0x7234,3,writes,error));
    assert(writes.size()==8 && writes[0].value==0x72340358U);
    assert(writes[2].value==0x72540341U && writes[4].value==0x72740342U);
    assert(writes[6].value==0x72940321U);
    assert(ram[0x4cd8]==0x72 && ram[0x4cd9]==0); // SEQ.B D3 quirk.
    text(resources[0],0,"%02x");resources[0].data[0x1000]=1;
    assert(ms5::format_fixed_text(ram,resources,font,0x60000,0x107000,arguments,0x7000,3,writes,error));
    assert(writes.size()==4 && writes[0].value==0x70000330U && writes[2].value==0x70200331U);
    text(resources[0],0,"%2x");
    assert(ms5::format_fixed_text(ram,resources,font,0x60000,0x107000,arguments,0x7000,3,writes,error));
    assert(writes[0].value==0x70000320U && writes[2].value==0x70200331U);
    // Caller-provided external stack argument table retains original CPU pointers.
    arguments.assign(4,0);put(arguments,0,0x61000);
    assert(ms5::format_fixed_text(ram,resources,font,0x60000,0x1fefe0,arguments,0x7000,3,writes,error));
    assert(ram[0x4ce4]==0 && ram[0x4ce5]==0x1f && ram[0x4ce6]==0xef && ram[0x4ce7]==0xe4);
    const std::vector<std::uint8_t> saved=ram;
    const std::uint32_t first=writes[0].value;
    const char* invalid[]={"A%0x","A%65536s","A%q","A%9x","A\\cQZ"};
    for(unsigned int i=0;i<5;++i) {
        text(resources[0],0,invalid[i]);
        if(i==3)put(arguments,0,0x61fff); // Width9 exhausts mapped data.
        assert(!ms5::format_fixed_text(ram,resources,font,0x60000,0x1fefe0,arguments,0x7000,3,writes,error));
        assert(ram==saved && writes.size()==4 && writes[0].value==first);
    }
    text(resources[0],0,"A%s");put(arguments,0,0x900000);
    assert(!ms5::format_fixed_text(ram,resources,font,0x60000,0x1fefe0,arguments,0x7000,3,writes,error));
    assert(ram==saved && writes[0].value==first);
    resources.push_back(resources[0]);
    assert(!ms5::format_fixed_text(ram,resources,font,0x60000,0x107000,arguments,0x7000,3,writes,error));
    assert(ram==saved);
    // Renderer3650 consumes one byte per glyph, without a font or lookahead.
    resources.resize(1); arguments.clear();
    ms5::FixedDataResource empty_font;
    resources[0].data[0]='@'; resources[0].data[1]=0x80;
    resources[0].data[2]=0xff; resources[0].data[3]='A'; resources[0].data[4]=0;
    assert(ms5::format_fixed_text(ram,resources,empty_font,0x60000,0x1fefe0,arguments,
                                 0xfff0,0xffff,writes,error,0x3650));
    assert(writes.size()==8);
    const std::uint32_t glyph_values[4]={0xfff0ff40U,0x0010ff80U,0x0030ffffU,0x0050ff41U};
    for(unsigned int i=0;i<4;++i) {
        assert(writes[2*i].size==4 && writes[2*i].address==0x3c0000U &&
               writes[2*i].value==glyph_values[i]);
        assert(writes[2*i+1].size==2 && writes[2*i+1].address==0x3c0000U &&
               writes[2*i+1].value==0x8200U);
    }
    assert(ram[0x4ce0]==0 && ram[0x4ce1]==0 && ram[0x4ce2]==0x36 && ram[0x4ce3]==0x50);
    const std::vector<std::uint8_t> renderer_ram=ram;
    const std::vector<ms5::VideoPortWrite> renderer_writes=writes;
    assert(!ms5::format_fixed_text(ram,resources,empty_font,0x60000,0x1fefe0,arguments,
                                  0x7000,0xffff,writes,error,0x123456));
    assert(ram==renderer_ram && writes.size()==renderer_writes.size());
    for(std::size_t i=0;i<writes.size();++i) {
        assert(writes[i].size==renderer_writes[i].size &&
               writes[i].address==renderer_writes[i].address &&
               writes[i].value==renderer_writes[i].value);
    }
    text(resources[0],0,"A%q"); // Fails after a valid glyph was emitted internally.
    assert(!ms5::format_fixed_text(ram,resources,empty_font,0x60000,0x1fefe0,arguments,
                                  0x7000,0xffff,writes,error,0x3650));
    assert(ram==renderer_ram && writes.size()==renderer_writes.size());
    for(std::size_t i=0;i<writes.size();++i) {
        assert(writes[i].size==renderer_writes[i].size &&
               writes[i].address==renderer_writes[i].address &&
               writes[i].value==renderer_writes[i].value);
    }
    // Terminal controls affect returned D1.style but are not stored on NUL.
    text(resources[0],0,"A\\c7");
    std::uint16_t final_style=0,final_line=0;
    assert(ms5::format_fixed_text(ram,resources,empty_font,0x60000,0x1fefe0,arguments,
                                  0x7000,3,writes,error,0x3650,&final_style,&final_line));
    assert(final_style=='7' && ram[0x4cdb]==3 && final_line==0x7000);
    text(resources[0],0,"A\\n");
    std::uint32_t d3=0xdead1234U;
    assert(ms5::format_fixed_text(ram,resources,empty_font,0x60000,0x1fefe0,arguments,
                                  0x7000,3,writes,error,0x3650,&final_style,&final_line,&d3));
    assert(d3==0xdead7001U);
    assert(final_line==0x7001 && ram[0x4cd8]==0x70 && ram[0x4cd9]==0);
    text(resources[0],0,"A\\l\2\3");
    assert(ms5::format_fixed_text(ram,resources,empty_font,0x60000,0x1fefe0,arguments,
                                  0x7000,3,writes,error,0x3650,&final_style,&final_line,&d3));
    assert(d3==0x7043U && final_line==0x7043);
    d3=0xdead1234U;
    text(resources[0],0,"A\\l\2\3%q");
    final_line=0xabcd;
    assert(!ms5::format_fixed_text(ram,resources,empty_font,0x60000,0x1fefe0,arguments,
                                  0x7000,3,writes,error,0x3650,&final_style,&final_line,&d3));
    assert(final_line==0xabcd && d3==0xdead1234U);
    ms5::FixedDataResource debug;
    std::uint32_t d1=0x12345678U;
    ram[0xf000]=0;
    const std::vector<std::uint8_t> debug_before=ram;
    assert(ms5::step_main_debug(ram,debug,0xffffffffU,d1,writes,error,&final_line));
    assert(ram==debug_before && d1==0x12345678U && writes.empty() && final_line==0xabcd);
    d3=0xdeadabcdU;
    assert(ms5::step_main_debug(ram,debug,0xffffffffU,d1,writes,error,&final_line,&d3));
    assert(ram==debug_before && d1==0x12345678U && d3==0xdeadabcdU && final_line==0xabcd);
    final_line=0x1234U;
    writes.assign(1,ms5::VideoPortWrite());writes[0].value=789U;
    assert(!ms5::step_main_debug(ram,debug,0xffffffffU,d1,writes,error,&final_line,&d3));
    assert(ram==debug_before && d1==0x12345678U && d3==0xdeadabcdU &&
           final_line==0x1234U && writes.size()==1 && writes[0].value==789U);
    final_line=0xabcdU;
    ram[0xf000]=1;ram[0x185]=0;
    assert(ms5::step_main_debug(ram,debug,0x100101,d1,writes,error,&final_line,&d3));
    assert(d3==0xdeadabcdU && final_line==0xabcdU && writes.empty());
    ram[0x185]=1;
    const std::vector<std::uint8_t> active_before=ram;
    assert(!ms5::step_main_debug(ram,debug,0x100101,d1,writes,error,&final_line,&d3));
    assert(ram==active_before && d1==0x12345678U && writes.empty() && final_line==0xabcd);
    assert(d3==0xdeadabcdU);
    debug.source_cpu_address=debug.source_rom_offset=0xd56U;
    debug.data.assign(0xe40U-0xd56U,0);
    text(debug,0,"A\\l\2\3");
    assert(ms5::step_main_debug(ram,debug,0x100101,d1,writes,error,&final_line,&d3));
    assert(d1==0x12345678U && d3==0x7043U && final_line==0x7043U);
    const std::vector<std::uint8_t> before_late_debug=ram;
    d3=0xdeadabcdU;final_line=0xabcdU;
    text(debug,0,"A\\l\2\3%q");
    writes.assign(1,ms5::VideoPortWrite());writes[0].value=789U;
    assert(!ms5::step_main_debug(ram,debug,0x100101,d1,writes,error,&final_line,&d3));
    assert(ram==before_late_debug && d1==0x12345678U && d3==0xdeadabcdU &&
           final_line==0xabcdU && writes.size()==1 && writes[0].value==789U);
    std::cout << "Formatted text state, padding, external arguments and rollback passed\n";
}
