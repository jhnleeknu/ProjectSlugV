#include "ms5/stage_hud_counter.h"
#include "ms5/palette_blend_execution.h"
#include "ms5/stage_block_draw.h"
#include <new>
namespace ms5 {
namespace {
void word(std::uint32_t& value,std::uint32_t input) { value=(value&0xffff0000U)|(input&65535U); }
void byte(std::uint32_t& value,std::uint32_t input) { value=(value&0xffffff00U)|(input&255U); }
bool valid(const StageHudCounterState& s) {
    if (s.phase==0) return s.saved_d0==0 && s.sound.phase==0 && s.sound.saved_low==0 && !s.sound.byte.waiting;
    return s.phase==1 && (s.sound.phase==1 || s.sound.phase==2) && s.sound.byte.waiting;
}
bool ram_byte(std::uint32_t base,int displacement,std::size_t& at,std::string& error) {
    const std::int64_t address=static_cast<std::int64_t>(base)+displacement;
    if (address<0x100000 || address>=0x110000) { error="HUD counter BYTE access outside CPU RAM"; return false; }
    at=static_cast<std::size_t>(address-0x100000);return true;
}
bool lookup(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::uint32_t address,std::uint32_t& value,std::string& error) {
    if ((address&1U) || address>0xfffffeU) { error="unaligned or overflowing HUD lookup WORD"; return false; }
    const std::vector<std::uint8_t>* data=NULL;std::size_t at=0;
    if (address>=0x100000 && address<=0x10fffe) { data=&ram;at=address-0x100000; }
    else {
        unsigned int matches=0;
        for (std::size_t i=0;i<windows.size();++i) {
            const FixedDataResource& w=windows[i];const std::uint32_t start=w.source_cpu_address;
            if (start>=0x100000 || w.source_rom_offset!=start || w.data.empty() || w.data.size()>0x100000-start) continue;
            const std::uint64_t end=static_cast<std::uint64_t>(start)+w.data.size();
            if (address<end && static_cast<std::uint64_t>(address)+2>start) {
                ++matches;
                if (address>=start && static_cast<std::uint64_t>(address)+2<=end) {data=&w.data;at=address-start;}
            }
        }
        if (matches!=1 || data==NULL) {error="missing, ambiguous or partial fixed HUD lookup WORD";return false;}
    }
    value=(static_cast<unsigned int>((*data)[at])<<8)|(*data)[at+1];return true;
}
void export_registers(const StageHudCounterState& s,ObjectRestartState& full) {
    for (unsigned int i=0;i<8;++i) full.d[i]=s.sound.byte.registers.d[i];
    for (unsigned int i=0;i<5;++i) full.a[i]=s.sound.byte.registers.a[i];
    full.a[5]=s.a5;full.a[6]=s.a6;
}
void import_registers(StageHudCounterState& s,const ObjectRestartState& full) {
    for (unsigned int i=0;i<8;++i) s.sound.byte.registers.d[i]=full.d[i];
    for (unsigned int i=0;i<5;++i) s.sound.byte.registers.a[i]=full.a[i];
    s.a5=full.a[5];s.a6=full.a[6];
}
bool draw(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    StageHudCounterState& s,std::vector<VideoPortWrite>& ports,std::string& error) {
    ObjectRestartState full;export_registers(s,full);std::vector<VideoPortWrite> output;
    if (!execute_stage_block_draw(ram,0x35f0,windows,full,output,error)) return false;
    import_registers(s,full);ports.insert(ports.end(),output.begin(),output.end());return true;
}
bool after_sound(std::vector<std::uint8_t>& ram,StageHudCounterState& s,std::string& error) {
    std::size_t at=0;if (!ram_byte(s.a5,0x5d20,at,error)) return false;
    ram[at]=0x1f;word(s.sound.byte.registers.d[0],s.saved_d0);
    s.saved_d0=0;s.phase=0;return true;
}
void shape(StageHudCounterState& s) {
    SceneMapTransferState& r=s.sound.byte.registers;
    byte(r.d[2],r.d[0]);const bool carry=(r.d[2]&0x20U)!=0;
    byte(r.d[2],r.d[2]<<3);
    if (carry) byte(r.d[2],~r.d[2]);
    byte(r.d[2],(r.d[2]&255U)>>3);
}
bool post(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    StageHudCounterState& s,std::vector<VideoPortWrite>& ports,std::string& error) {
    SceneMapTransferState& r=s.sound.byte.registers;
    const std::uint16_t saved=static_cast<std::uint16_t>(r.d[0]);
    r.d[0]=12;word(r.d[1],0x0a0d);
    ObjectRestartState blend;export_registers(s,blend);
    if (!execute_palette_blend(ram,blend,error)) return false;
    import_registers(s,blend);word(r.d[0],saved);
    word(r.d[0],(r.d[0]&65535U)>>8);const std::uint16_t digits=static_cast<std::uint16_t>(r.d[0]);
    word(r.d[0],(r.d[0]&65535U)>>4);word(r.d[0],r.d[0]*2U);
    r.a[0]=0x4e272;std::uint32_t value=0;
    if (!lookup(ram,windows,r.a[0]+(r.d[0]&65535U),value,error)) return false;
    word(r.d[1],value);r.d[0]=(r.d[0]<<16)|(r.d[0]>>16);
    r.d[2]=2;r.d[3]=2;word(r.d[0],0x7243);
    if (!draw(ram,windows,s,ports,error)) return false;
    word(r.d[0],digits);word(r.d[0],r.d[0]&15U);r.a[0]=0x4e272;word(r.d[0],r.d[0]*2U);
    if (!lookup(ram,windows,r.a[0]+(r.d[0]&65535U),value,error)) return false;
    word(r.d[1],value);r.d[2]=2;r.d[3]=2;word(r.d[0],0x7283);
    return draw(ram,windows,s,ports,error);
}
bool run(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    StageHudCounterState& s,std::uint8_t external_status,std::uint8_t& reads,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    SceneMapTransferState& r=s.sound.byte.registers;
    if (s.phase==1) {
        if (s.a5!=0x108000) {error="HUD sound resume requires canonical A5=108000";return false;}
        if (!execute_sound_word(ram,s.sound,external_status,reads,error)) return false;
        if (s.sound.phase!=0) return true;
        if (!after_sound(ram,s,error)) return false;
        shape(s);return post(ram,windows,s,ports,error);
    }
    std::size_t at=0;if (!ram_byte(s.a5,0x5d1f,at,error)) return false;
    if (ram[at]==0) return true;
    if ((r.d[0]&65535U)>0x99ffU) {
        word(r.d[0],0x7243);word(r.d[1],0xc904);r.d[2]=4;r.d[3]=2;
        return draw(ram,windows,s,ports,error);
    }
    r.d[2]=0;
    if (!ram_byte(s.a5,0x5d20,at,error)) return false;
    if ((r.d[0]&65535U)>=0x0a00U) ram[at]=0;
    else {
        const std::uint8_t previous=ram[at];ram[at]=static_cast<std::uint8_t>(previous-1U);
        if (previous==0) {
            if (s.a5!=0x108000) {error="HUD sound call requires canonical A5=108000";return false;}
            s.saved_d0=static_cast<std::uint16_t>(r.d[0]);word(r.d[0],0x1ac3);
            if (!execute_sound_word(ram,s.sound,external_status,reads,error)) return false;
            if (s.sound.phase!=0) {s.phase=1;return true;}
            if (!after_sound(ram,s,error)) return false;
        }
        shape(s);
    }
    return post(ram,windows,s,ports,error);
}
}
bool step_stage_hud_counter(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,StageHudCounterState& state,
    std::uint8_t external_status,std::uint8_t& external_reads,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if (ram.size()!=65536 || !valid(state)) {error="invalid HUD counter RAM or continuation";return false;}
    try {
        std::vector<std::uint8_t> candidate=ram;StageHudCounterState next=state;
        std::uint8_t reads=0;std::vector<VideoPortWrite> output;
        if (!run(candidate,windows,next,external_status,reads,output,error)) return false;
        ram.swap(candidate);state=next;external_reads=reads;ports.swap(output);error.clear();return true;
    } catch (const std::bad_alloc&) {error="cannot allocate HUD counter transaction";return false;}
}
}
