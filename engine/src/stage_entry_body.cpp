#include "ms5/stage_entry_body.h"
#include "ms5/scene_general_initialization.h"
#include "ms5/stage_cue_control.h"
#include "ms5/stage_event_initialization.h"
#include <new>
namespace ms5 {
namespace {
bool inactive(const StageFrameState& frame) {
    const StageBufferFrameState& b=frame.buffer;
    return frame.stage==0 && b.phase==0 && b.saved_a6==0 && b.saved_slot_a4==0 && b.saved_slot_d7==0 &&
        b.saved_d0==0 && b.saved_d1==0 && b.saved_d7==0 && b.saved_a0==0 &&
        frame.sound_kind==0 && frame.sound_phase==0 && frame.sound_saved==0;
}
bool read(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::uint32_t address,unsigned int size,std::uint32_t& result,std::string& error) {
    if ((size>1 && (address&1U)) || address>0x1000000U-size) {
        error="unaligned or overflowing stage entry body read"; return false;
    }
    const std::vector<std::uint8_t>* bytes=NULL; std::size_t at=0;
    if (address>=0x100000 && address+size<=0x110000) { bytes=&ram; at=address-0x100000; }
    else {
        unsigned int matches=0;
        for (std::size_t i=0;i<windows.size();++i) {
            const FixedDataResource& w=windows[i]; const std::uint32_t start=w.source_cpu_address;
            if ((start&1U) || start>=0x100000 || w.source_rom_offset!=start || w.data.empty() || w.data.size()>0x100000-start) continue;
            const std::uint64_t end=static_cast<std::uint64_t>(start)+w.data.size();
            if (address<end && static_cast<std::uint64_t>(address)+size>start) {
                ++matches;
                if (address>=start && static_cast<std::uint64_t>(address)+size<=end) { bytes=&w.data; at=address-start; }
            }
        }
        if (matches!=1 || bytes==NULL) { error="missing, ambiguous or partial fixed stage entry body read"; return false; }
    }
    std::uint32_t value=0;
    for (unsigned int i=0;i<size;++i) value=(value<<8)|(*bytes)[at+i];
    result=value; return true;
}
bool offset_read(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::uint32_t address,unsigned int offset,unsigned int size,std::uint32_t& result,std::string& error) {
    if (address>0xffffffffU-offset) { error="stage entry body address addition overflows"; return false; }
    return read(ram,windows,address+offset,size,result,error);
}
bool write(std::vector<std::uint8_t>& ram,std::uint32_t address,unsigned int size,std::uint32_t value,std::string& error) {
    if ((size>1 && (address&1U)) || address<0x100000 || address>0x110000-size) {
        error="stage entry body write requires aligned complete RAM span"; return false;
    }
    for (unsigned int i=0;i<size;++i) ram[address-0x100000+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
    return true;
}
void word(std::uint32_t& value,std::uint32_t input) { value=(value&0xffff0000U)|(input&0xffffU); }
void byte(std::uint32_t& value,std::uint32_t input) { value=(value&0xffffff00U)|(input&255U); }
bool initialize(std::vector<std::uint8_t>& ram,const FixedDataResource& tables,
    const std::vector<FixedDataResource>& windows,StageEntryBodyState& state,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    StageBufferFrameState& buffer=state.frame.buffer; SceneMapTransferState& s=buffer.registers;
    std::uint32_t value=0;
    if (!offset_read(ram,windows,buffer.a6,0x76,4,s.a[4],error) ||
        !offset_read(ram,windows,s.a[4],2,4,s.a[0],error) ||
        !offset_read(ram,windows,s.a[4],0xe,2,value,error)) return false;
    word(s.d[0],value); std::vector<VideoPortWrite> scene_ports;
    if (!initialize_scene(ram,tables,windows,s,buffer.a6,scene_ports,error)) return false;
    ports.insert(ports.end(),scene_ports.begin(),scene_ports.end()); buffer.bank=2;
    if (!offset_read(ram,windows,buffer.a6,0x76,4,s.a[4],error) ||
        !offset_read(ram,windows,s.a[4],6,4,s.a[0],error)) return false;
    bool carry=false;
    if (!step_stage_cue_control(ram,0xe8a1c,windows,s,buffer.a6,carry,error)) return false;
    ram[0xd683]|=2U; ram[0xd683]|=8U; ram[0xd683]|=32U;
    byte(s.d[0],ram[0xfd8c]); word(s.d[0],s.d[0]&7U);
    if (!read(ram,windows,0x30ec+(s.d[0]&0xffffU),1,value,error)) return false;
    byte(s.d[0],value); ram[0xd67e]=static_cast<std::uint8_t>(s.d[0]); ram[0xd67f]=255;
    if (!offset_read(ram,windows,buffer.a6,0x76,4,s.a[4],error) ||
        !offset_read(ram,windows,s.a[4],0xa,4,s.a[0],error)) return false;
    if (s.a[0]!=0 && !read(ram,windows,s.a[0],4,s.a[0],error)) return false;
    if (!offset_read(ram,windows,s.a[4],0xe,2,value,error)) return false;
    word(s.d[0],value);
    ObjectRestartState events;
    for (unsigned int i=0;i<8;++i) events.d[i]=s.d[i];
    for (unsigned int i=0;i<5;++i) events.a[i]=s.a[i];
    events.a[5]=state.a5; events.a[6]=buffer.a6; std::vector<VideoPortWrite> event_ports;
    if (!initialize_stage_events(ram,windows,events,event_ports,error)) return false;
    for (unsigned int i=0;i<8;++i) s.d[i]=events.d[i];
    for (unsigned int i=0;i<5;++i) s.a[i]=events.a[i];
    state.a5=events.a[5]; buffer.a6=events.a[6];
    if (state.a5!=0x108000) { error="stage entry body event helper returned unsupported A5"; return false; }
    ports.insert(ports.end(),event_ports.begin(),event_ports.end()); buffer.bank=2;
    return write(ram,buffer.a6,4,0x47af0,error);
}
}
bool step_stage_entry_body(std::vector<std::uint8_t>& ram,
    const FixedDataResource& tables,const std::vector<FixedDataResource>& windows,
    StageEntryBodyState& state,std::uint8_t external_status,std::uint8_t& external_reads,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if (ram.size()!=65536 || state.a5!=0x108000 || state.phase>1 ||
        (state.frame.buffer.bank!=2 && state.frame.buffer.bank!=3) ||
        state.frame.cue_status<SpriteAccepted || state.frame.cue_status>SpriteWaiting ||
        (state.phase==0 && !inactive(state.frame)) ||
        (state.phase==1 && (state.frame.stage<1 || state.frame.stage>3))) {
        error="stage entry body requires64KiB RAM, A5=108000 and valid fresh or pending state"; return false;
    }
    try {
        std::vector<std::uint8_t> candidate=ram; StageEntryBodyState next=state;
        std::vector<VideoPortWrite> output; std::uint8_t reads=0;
        if (next.phase==0 && !initialize(candidate,tables,windows,next,output,error)) return false;
        std::vector<VideoPortWrite> frame_ports;
        if (!step_stage_frame(candidate,tables,windows,next.frame,external_status,reads,frame_ports,error)) return false;
        output.insert(output.end(),frame_ports.begin(),frame_ports.end()); next.phase=next.frame.stage==0?2:1;
        ram.swap(candidate); state=next; external_reads=reads; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error="cannot allocate stage entry body transaction"; return false; }
}
}
