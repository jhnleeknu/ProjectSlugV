#include "ms5/control_finish.h"
#include "ms5/fixed_text.h"
#include <cassert>
#include <iostream>
namespace {
void fail(std::vector<std::uint8_t>& ram,const ms5::FixedDataResource& pause) {
    const std::vector<std::uint8_t> before=ram;
    ms5::MenuFrameResult result;result.status=7;result.external_jump=8;result.line=9;
    std::vector<ms5::VideoPortWrite> writes(1);writes[0].address=1;writes[0].size=2;writes[0].value=3;
    std::string error;
    std::uint32_t d1=0xabcd0603U,d3=0xdead7000U;
    assert(!ms5::finish_control_menu(ram,pause,0xffffffffU,0x0603,0x7000,result,writes,error,&d1,&d3));
    assert(d1==0xabcd0603U && d3==0xdead7000U);
    assert(!error.empty() && ram==before && result.status==7 && result.external_jump==8 && result.line==9);
    assert(writes.size()==1 && writes[0].address==1 && writes[0].size==2 && writes[0].value==3);
}
}
int main() {
    ms5::FixedDataResource pause;
    pause.source_cpu_address=pause.source_rom_offset=0x9079;
    const unsigned char data[]={92,'l',18,26,92,'c',3,' ',' ',' ',' ',' ',0};
    pause.data.assign(data,data+sizeof(data));
    std::vector<std::uint8_t> ram(65536,0);
    ram[0x7dee]=255;ram[0x7df0]=3;ram[0x7dfb]=1;
    ram[0x4caa]=0xaa;ram[0x7dfc]=0x88;ram[0x4cab]=0x10;
    ms5::MenuFrameResult result;std::vector<ms5::VideoPortWrite> writes;std::string error;
    // Continued frame ignores callback and exit flag, and clears only D0 low word.
    ram[0x7df9]=1;
    assert(ms5::finish_control_menu(ram,pause,0xffff1200U,0x0603,0x7123,result,writes,error));
    assert(result.status==-65536 && result.line==0x7123 && writes.empty());
    assert(ram[0x7dee]==255 && ram[0x7df0]==3 && ram[0x7df3]==255 && ram[0x4cab]==0x32);
    fail(ram,pause);ram[0x7df9]=0;
    // A bytewise test would incorrectly treat 0101 as the exit value1.
    ram[0x7dfa]=1;
    assert(ms5::finish_control_menu(ram,pause,0x800012ffU,0x0603,0x7123,result,writes,error));
    assert(result.status==-2147478785 && result.line==0x7123 && writes.empty());
    assert(ram[0x7dee]==0 && ram[0x7df0]==3);
    ram[0x7dee]=255;ram[0x7dfa]=0;
    std::uint32_t d1=0xabcd0668U,d3=0xdead7123U;
    assert(ms5::finish_control_menu(ram,pause,0xffffffffU,0x0668,0x7123,result,writes,error,&d1,&d3));
    assert(d1==0xabcd0603U && d3==0x725aU);
    assert(result.status==1 && result.line==0x725a && writes.size()==10);
    assert(writes[0].value==0x725a6320 && ram[0x7dee]==0 && ram[0x7df0]==0);
    // A terminal style control returns even without a glyph. Without a
    // location control, 3918 overwrites only D3's low word with the cursor.
    const unsigned char terminal[]={92,'c',4,0};
    std::vector<std::uint8_t> script(terminal,terminal+sizeof(terminal));
    std::uint16_t style=0x7777,line=0x8888;
    d3=0xdead1234U;
    assert(ms5::trace_table_fixed_text(script,0x7000,0x0668,pause,writes,error,&line,&style,&d3));
    assert(style==0x0604 && line==0x7000 && d3==0xdead7000U && writes.empty());
    script.pop_back();
    assert(!ms5::trace_table_fixed_text(script,0x7100,0x0568,pause,writes,error,&line,&style,&d3));
    assert(style==0x0604 && line==0x7000 && d3==0xdead7000U && writes.empty());
    // Failure after the candidate menu flag changed must roll back all outputs.
    ram[0x7dee]=255;pause.data.pop_back();fail(ram,pause);
    ram.resize(5);fail(ram,pause);
    std::cout << "Control finish width, palette and transactional error tests passed\n";
}
