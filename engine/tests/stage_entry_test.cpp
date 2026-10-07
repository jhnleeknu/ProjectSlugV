#include "ms5/stage_entry.h"
#include <cstdlib>
#include <iostream>
namespace {
void require(bool ok, const char* message) { if (!ok) { std::cerr << message << '\n'; std::exit(1); } }
void word(std::vector<std::uint8_t>& ram, unsigned int at, unsigned int value) {
    ram[at]=static_cast<std::uint8_t>(value>>8); ram[at+1]=static_cast<std::uint8_t>(value);
}
void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value) { word(ram,at,value>>16); word(ram,at+2,value); }
std::uint32_t get(const std::vector<std::uint8_t>& ram, unsigned int at) {
    return (static_cast<std::uint32_t>(ram[at])<<24)|(static_cast<std::uint32_t>(ram[at+1])<<16)|
        (static_cast<std::uint32_t>(ram[at+2])<<8)|ram[at+3];
}
ms5::StageCatalog catalog_fixture() {
    ms5::StageCatalog catalog; catalog.groups.resize(19);
    for (unsigned int group=0; group<19; ++group) {
        ms5::StageGroup& target=catalog.groups[group]; target.source_cpu_address=0x50000+group*0x1000;
        target.header=0x1234;
        const unsigned int count=group == 0 ? 41 : 1;
        for (unsigned int area=0; area<count; ++area) {
            ms5::StageRecord record; record.source_cpu_address=target.source_cpu_address+4+area*22;
            record.data.assign(20,0); record.data[0]=static_cast<std::uint8_t>((area%6)*4);
            word(record.data,0x10,0x19c1); target.records.push_back(record);
        }
    }
    return catalog;
}
ms5::FixedDataResource tables_fixture() {
    ms5::FixedDataResource tables; tables.source_cpu_address=tables.source_rom_offset=0x1af12; tables.data.assign(512,0); return tables;
}
bool same(const ms5::StageEntryState& a, const ms5::StageEntryState& b) {
    return a.next_pc==b.next_pc && a.phase==b.phase && a.d0==b.d0 && a.d1==b.d1 && a.d3==b.d3 && a.a6==b.a6 &&
        a.sound.entry==b.sound.entry && a.sound.next_pc==b.sound.next_pc && a.sound.phase==b.sound.phase && a.sound.saved==b.sound.saved &&
        a.sound.d0==b.sound.d0 && a.sound.d1==b.sound.d1 && a.sound.d3==b.sound.d3 && a.sound.byte.waiting==b.sound.byte.waiting &&
        a.sound.byte.command==b.sound.byte.command && a.sound.byte.tail==b.sound.byte.tail && a.sound.byte.next==b.sound.byte.next;
}
void fails(std::vector<std::uint8_t>& ram, const ms5::StageCatalog& catalog, const ms5::FixedDataResource& tables, ms5::StageEntryState& state) {
    const std::vector<std::uint8_t> before=ram; const ms5::StageEntryState old=state;
    std::vector<ms5::VideoPortWrite> ports(1); ports[0].value=0xabcdef; std::string error;
    require(!ms5::step_stage_entry(ram,catalog,tables,state,ports,error) && !error.empty() && ram==before && same(state,old) &&
        ports.size()==1 && ports[0].value==0xabcdef,"stage entry error preserves all outputs");
}
}
int main() {
    ms5::StageCatalog catalog=catalog_fixture(); ms5::FixedDataResource tables=tables_fixture();
    std::vector<std::uint8_t> ram(65536,0); std::vector<ms5::VideoPortWrite> ports; std::string error;
    const std::uint32_t targets[6]={0x478c4,0x478f0,0x4791c,0x47934,0x4794c,0x47964};
    for (unsigned int area=0; area<41; ++area) {
        ram.assign(65536,0); ram[0xd681]=static_cast<std::uint8_t>(area); word(ram,0xd686,0x19c1);
        put(ram,0xcb8,0x270e); put(ram,0xda8,0); ram[0xd683]=255;
        ms5::StageEntryState state; state.next_pc=0x477ee; state.d0=0xffffffff; state.d1=0xffffffff; state.d3=0xabcdef01;
        require(ms5::step_stage_entry(ram,catalog,tables,state,ports,error),"selector successful");
        require(state.phase==2 && state.next_pc==targets[area%6] && state.d0==(area%6)*4 && state.d1==0 &&
            state.d3==0xabcdef01 && ports.size()==773 && get(ram,0xba6)==catalog.groups[0].records[area].source_cpu_address,
            "selector actual target and full regs; no body");
        require(ram[0xd684]==0x12 && ram[0xd683]==0xc8 && ram[0xd19]==0 && ram[0xe09]==0x40 && ram[0xe50]==1 &&
            ram[0x967]==255 && ram[0x965]==0 && ram[0x7def]==255 && ram[0xd68d]==0,"helper flags and skipped music timer");
        fails(ram,catalog,tables,state);
    }
    // Stage fallback and invalid area retry select group zero/area zero.
    ram.assign(65536,0); ram[0xd680]=255; ram[0xd681]=255; word(ram,0xd686,0x19c1);
    ms5::StageEntryState state; state.next_pc=0x477ee;
    require(ms5::step_stage_entry(ram,catalog,tables,state,ports,error) && ram[0xbad]==0 && state.next_pc==0x478c4,"stage/area fallback");
    // First and second captured queue waits; preserve changes without replaying the prefix.
    ram.assign(65536,0); word(ram,0x4d74,1); state=ms5::StageEntryState(); state.next_pc=0x477ee; state.d3=0xabcdef12;
    require(ms5::step_stage_entry(ram,catalog,tables,state,ports,error) && state.phase==1 && state.sound.phase==1 && ports.empty(),"first sound wait");
    const ms5::StageEntryState first=state; const std::vector<std::uint8_t> waiting_ram=ram;
    require(ms5::step_stage_entry(ram,catalog,tables,state,ports,error) && same(first,state) && ram==waiting_ram,"stable wait");
    ram[0x967]=0x22; ram[0xd683]=0xff; ram[0xd680]=18;
    word(ram,0x4d74,2);
    require(ms5::step_stage_entry(ram,catalog,tables,state,ports,error) && state.sound.phase==2 && state.phase==1 &&
        ram[0x4cf4]==10 && ram[0x4d77]==1 && ports.empty(),"second wait carries first byte");
    // Live record pointer changes after the query, so dispatch must reread it.
    put(ram,0xba6,catalog.groups[0].records[5].source_cpu_address); word(ram,0x4d74,3);
    require(ms5::step_stage_entry(ram,catalog,tables,state,ports,error) && state.phase==2 && state.next_pc==0x47964 &&
        state.sound.phase==3 && state.d0==20 && state.d1==0 && state.d3==0xabcdef12 && ram[0x4cf5]==0x58 &&
        ram[0x4d77]==2 && ram[0xd68d]==1 && ram[0x967]==0x22 && ram[0xd683]==255 && ports.size()==773,"live pointer/sound finish no prefix replay");
    // Late selector failure rolls back an already resumed sound write and screen output.
    ram=waiting_ram; state=first; word(ram,0x4d74,4); catalog.groups[0].records[0].data[0]=1;
    fails(ram,catalog,tables,state); catalog.groups[0].records[0].data[0]=0;
    // Empty-group original loop and failure after initialization remain transactional.
    ms5::StageCatalog empty=catalog; empty.groups[9].records.clear(); ram.assign(65536,0); ram[0xd680]=9;
    state=ms5::StageEntryState(); fails(ram,empty,tables,state);
    ram.assign(65536,0); state=ms5::StageEntryState();
    require(ms5::step_stage_entry(ram,catalog,tables,state,ports,error) && state.phase==2 && ports.size()==777 &&
        state.d3==0x01000000 && ports[0].address==0x2ffff2 && ports[0].value==0x2000 && ports[3].value==0,
        "fresh initialization ordered PVC then screen");
    state=ms5::StageEntryState(); state.next_pc=0x477ee; state.a6=0x100001; fails(ram,catalog,tables,state);
    state.a6=0x10ff3e; fails(ram,catalog,tables,state);
    state=first; state.sound.d3^=1; fails(ram,catalog,tables,state);
    state=first; state.sound.byte.command=9; fails(ram,catalog,tables,state);
    state=ms5::StageEntryState(); state.sound.d0=1; fails(ram,catalog,tables,state);
    state=ms5::StageEntryState(); ram.resize(65535); fails(ram,catalog,tables,state);
    std::cout << "stage_entry_test: passed\n";
}
