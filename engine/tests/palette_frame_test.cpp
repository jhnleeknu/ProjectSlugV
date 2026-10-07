#include "ms5/palette_frame.h"
#include <cstdlib>
#include <iostream>
void check(bool value) { if (!value) { std::cerr << "palette frame test failed\n"; std::exit(1); } }
int main() {
    std::vector<std::uint8_t> ram(65536, 0);
    std::vector<ms5::PaletteRecord> records;
    std::string error;
    std::vector<ms5::VideoPortWrite> writes;
    ram[0x7dd4]=2; ram[0x7dc3]=255; ram[0x7dcf]=1; ram[0x7ded]=128;
    ram[0x4db1]=2;
    check(ms5::step_palette_frame(ram,records,error,&writes));
    check(writes.size()==256);
    for(std::size_t i=0;i<writes.size();++i)
        check(writes[i].address==0x300001 && writes[i].size==1 && writes[i].value==255);
    check(ram[0x7dd4]==1 && ram[0x7dc2]==1 && ram[0x7dc3]==0);
    check(ram[0x4da1]==128 && ram[0x4db1]==2); // exemption retained
    ram[0x7ded]=0;
    const std::vector<std::uint8_t> before=ram;
    check(!ms5::step_palette_frame(ram,records,error,&writes) && ram==before);
    check(writes.size()==256 && writes[0].address==0x300001 && writes[0].size==1 && writes[0].value==255);
    ram.assign(65536,0); ram[0x7ded]=128;
    ram[0x7dd4]=2; ram[0x7dcf]=1;
    check(ms5::step_palette_frame(ram,records,error,&writes));
    check(writes.empty());
    check(ram[0x7dc3]==1 && ram[0x4da1]==0); // fractional change only
    ram[0x7dc8]=0x12; ram[0x7dc9]=0x34;
    check(ms5::step_palette_frame(ram,records,error));
    check(ram[0x7dd4]==0 && ram[0x7dc2]==0x12 && ram[0x7dc3]==0x34);
    // Pending preparation leaves the timer's byte-sized D1 result visible.
    ram.assign(65536,0); records.clear(); writes.clear();
    ram[0x7ded]=128; ram[0x7dd4]=2;
    ram[0x7dc4]=2; ram[0x7dd0]=1;
    std::uint32_t d1=0x89abcdefU;
    check(ms5::step_palette_frame(ram,records,error,&writes,&d1));
    check(d1==0x89abcdffU && ram[0x7dd4]==1 && ram[0x7dc4]==3);
    check(writes.size()==256);

    // A zero timer plus pending gate never overwrites any D1 bits.
    ram.assign(65536,0); ram[0x7ded]=128;
    d1=0x1234fedcU;
    check(ms5::step_palette_frame(ram,records,error,&writes,&d1));
    check(d1==0x1234fedcU && writes.empty());

    // Effect preparation exposes the adjusted middle channel in D1.word.
    ram.assign(65536,0); ram[0x7dc4]=2; ram[0x4da1]=128;
    ms5::PaletteRecord record={}; record.id=0;
    record.source_words[15]=static_cast<std::uint16_t>(3U<<5);
    records.assign(1,record); d1=0xa5c3beefU;
    check(ms5::step_palette_frame(ram,records,error,&writes,&d1));
    check(d1==0xa5c30005U && ram[0x7ded]==255);
    check(writes.size()==4);

    // Missing resources after timer arithmetic must roll back every output.
    ram.assign(65536,0); records.clear();
    ram[0x7dd4]=2; ram[0x7dc4]=2; ram[0x7dd0]=1;
    d1=0x76543210U;
    ms5::VideoPortWrite sentinel;
    sentinel.size=2; sentinel.address=0x3c0006U; sentinel.value=0x4567U;
    writes.assign(1,sentinel);
    const std::vector<std::uint8_t> rollback_ram=ram;
    check(!ms5::step_palette_frame(ram,records,error,&writes,&d1));
    check(!error.empty() && ram==rollback_ram && d1==0x76543210U);
    check(writes.size()==1 && writes[0].size==2 &&
          writes[0].address==0x3c0006U && writes[0].value==0x4567U);
    std::cout << "palette_frame_test: passed\n";
}
