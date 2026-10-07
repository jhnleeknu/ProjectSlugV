#include "ms5/game_initialization.h"
#include "ms5/game_reset.h"
#include "ms5/game_objects.h"
#include "ms5/game_records.h"
#include <new>
namespace ms5 {
namespace {
void word(std::vector<std::uint8_t>& ram,std::size_t at,std::uint16_t value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
void longword(std::vector<std::uint8_t>& ram,std::size_t at,std::uint32_t value) {
    word(ram,at,static_cast<std::uint16_t>(value>>16));word(ram,at+2,static_cast<std::uint16_t>(value));
}
bool empty(const SoundBytePending& byte) {
    return !byte.waiting&&byte.command==0&&byte.tail==0&&byte.next==0;
}
bool suffix_state(const GamePreludeState& state) {
    return state.next_pc==0x475a4&&state.word.kind==0&&state.word.phase==0&&state.word.low==0&&
        state.word.cursor==0&&empty(state.word.byte)&&empty(state.byte);
}
bool area_suffix(std::vector<std::uint8_t>& ram, std::uint32_t& d0, std::uint32_t& d1,
                 std::uint32_t& d3, std::string& error) {
    ram[0xd682]=0;
    if(!reset_game_objects(ram,0x1bd12,d0,error))return false;
    longword(ram,0xde2a,0xe89ec);
    //3d42 is RTS.3dce installs the two default callback addresses.
    ram[0x4d91]&=0xef;longword(ram,6,0x3dcc);longword(ram,10,0x3dcc);
    const std::uint32_t entries[]={0x49a8e,0x4aa30,0xb4a24,0x2ef90,0x46f2e,0x4d13c,0x4ddb6};
    //6f1c2 between2ef90 and46f2e is RTS.
    for(unsigned int index=0;index<7;++index)
        if(!reset_game_subsystem(ram,entries[index],d0,d1,d3,error))return false;
    ram[0xdc8c]=0;ram[0xdc8d]=0;word(ram,0xd690,0xa0);word(ram,0xd692,0x180);
    ram[0xd68e]=0;word(ram,0xd688,0);word(ram,0xd68a,0);word(ram,0xd68c,0);
    return true;
}
bool suffix(std::vector<std::uint8_t>& ram,const FixedDataResource& records,
            std::uint32_t& d0,std::uint32_t& d1,std::uint32_t& d3,std::string& error) {
    word(ram,0xd686,0);
    if(!reset_game_subsystem(ram,0xb7a20,d0,d1,d3,error)||
       !reset_game_subsystem(ram,0x4d126,d0,d1,d3,error)||
       !reset_game_objects(ram,0x1bcfe,d0,error))return false;
    d0=0;d1=0;
    if(!configure_game_record(ram,records,d0,d1,d3,error))return false;
    d0=1;d1=0;
    if(!configure_game_record(ram,records,d0,d1,d3,error))return false;
    return area_suffix(ram,d0,d1,d3,error);
}
}
bool reset_stage_area(std::vector<std::uint8_t>& ram, std::uint32_t& d0,
                      std::uint32_t& d1, std::uint32_t& d3, std::string& error) {
    if (ram.size() != 65536) { error = "stage area reset requires64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate = ram;
        std::uint32_t next0 = d0, next1 = d1, next3 = d3;
        if (!area_suffix(candidate,next0,next1,next3,error)) return false;
        ram.swap(candidate); d0 = next0; d1 = next1; d3 = next3; error.clear(); return true;
    } catch (const std::bad_alloc&) { error = "cannot allocate stage area reset transaction"; return false; }
}
bool finish_game_initialization(std::vector<std::uint8_t>& ram,const FixedDataResource& records,
    std::uint32_t& d0,std::uint32_t& d1,std::uint32_t& d3,std::string& error) {
    if(ram.size()!=65536){error="game initialization requires64KiB RAM";return false;}
    try {
        std::vector<std::uint8_t> candidate=ram;
        std::uint32_t next0=d0,next1=d1,next3=d3;
        if(!suffix(candidate,records,next0,next1,next3,error))return false;
        ram.swap(candidate);d0=next0;d1=next1;d3=next3;error.clear();return true;
    } catch(const std::bad_alloc&) {error="cannot allocate game initialization transaction";return false;}
}
bool initialize_game(std::vector<std::uint8_t>& ram,const FixedDataResource& records,
    std::uint8_t external,GameInitializationState& state,std::uint8_t& reads,std::string& error) {
    if(ram.size()!=65536||state.returned||state.prelude.phase>4||
       (state.prelude.phase==4&&!suffix_state(state.prelude))) {
        error="invalid game initialization RAM or continuation";return false;
    }
    try {
        std::vector<std::uint8_t> candidate=ram;GameInitializationState next=state;std::uint8_t next_reads=0;
        if(next.prelude.phase!=4&&!prepare_game_prelude(candidate,external,next.prelude,next_reads,error))return false;
        if(next.prelude.phase==4) {
            if(!suffix(candidate,records,next.prelude.d0,next.prelude.d1,next.prelude.d3,error))return false;
            next.returned=true;
        }
        ram.swap(candidate);state=next;reads=next_reads;error.clear();return true;
    } catch(const std::bad_alloc&) {error="cannot allocate game initialization transaction";return false;}
}
}
