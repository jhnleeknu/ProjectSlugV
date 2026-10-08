#include "ms5/object_sound_lookup.h"
#include <new>
namespace ms5 {
namespace {
void byte(std::uint32_t& reg,std::uint32_t value) { reg=(reg&0xffffff00U)|(value&255U); }
void word(std::uint32_t& reg,std::uint32_t value) { reg=(reg&0xffff0000U)|(value&65535U); }
bool valid(const ObjectSoundLookupState& s) {
    if (s.phase==0) return s.saved_a0==0 && s.sound.phase==0 && s.sound.saved_low==0 && !s.sound.byte.waiting;
    return s.phase==1 && (s.sound.phase==1 || s.sound.phase==2) && s.sound.byte.waiting;
}
bool ram_span(std::uint32_t base,int displacement,unsigned int size,
    std::size_t& at,std::string& error) {
    const std::int64_t address=static_cast<std::int64_t>(base)+displacement;
    if (address<0x100000 || address+size>0x110000 || (size>1 && (address&1))) {
        error="object sound lookup requires aligned complete reached RAM spans";return false;
    }
    at=static_cast<std::size_t>(address-0x100000);return true;
}
bool lookup(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::uint32_t address,std::uint32_t& value,std::string& error) {
    if ((address&1U) || address>0xfffffeU) {error="unaligned or overflowing object lookup WORD";return false;}
    const std::vector<std::uint8_t>* data=NULL;std::size_t at=0;
    if (address>=0x100000 && address<=0x10fffe) {data=&ram;at=address-0x100000;}
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
        if (matches!=1 || data==NULL) {error="missing, ambiguous or partial fixed object lookup WORD";return false;}
    }
    value=(static_cast<unsigned int>((*data)[at])<<8)|(*data)[at+1];return true;
}
bool finish(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    ObjectSoundLookupState& s,std::string& error) {
    SceneMapTransferState& r=s.sound.byte.registers;std::size_t source=0,destination=0;
    if (!ram_span(r.a[0],0,1,source,error)) return false;
    if (!ram_span(s.a6,0x7e,1,destination,error)) return false;
    ram[destination]=ram[source];
    // This WORD read is deliberately live after the BYTE write above.
    if (!ram_span(r.a[0],0,2,source,error)) return false;
    word(r.d[1],(static_cast<unsigned int>(ram[source])<<8)|ram[source+1]);
    const unsigned int original=r.d[1]&255U;
    byte(r.d[1],original>=0x40U && original<=0xbfU ? 0x80U : original*2U);
    word(r.d[1],r.d[1]&0xfeU);r.a[0]=0x4411e;
    std::uint32_t value=0;
    if (!lookup(ram,windows,r.a[0]+(r.d[1]&65535U),value,error)) return false;
    word(r.d[1],value-1U);
    if (value==0) r.d[1]=0;
    if (!ram_span(s.a6,0x12,1,destination,error)) return false;
    ram[destination]=static_cast<std::uint8_t>(r.d[1]);return true;
}
bool run(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    ObjectSoundLookupState& s,std::uint8_t external_status,std::uint8_t& reads,std::string& error) {
    SceneMapTransferState& r=s.sound.byte.registers;
    if (s.phase==1) {
        if (s.a5!=0x108000) {error="object sound resume requires canonical A5=108000";return false;}
        if (!execute_sound_word(ram,s.sound,external_status,reads,error)) return false;
        if (s.sound.phase!=0) return true;
        r.a[0]=s.saved_a0;s.saved_a0=0;s.phase=0;
        return finish(ram,windows,s,error);
    }
    std::size_t source=0,destination=0;
    if (!ram_span(s.a5,-0x76a4,1,source,error)) return false;
    r.a[0]=static_cast<std::uint32_t>(0x100000U+source);
    byte(r.d[0],ram[source]);
    if (!ram_span(s.a6,0x7e,1,destination,error)) return false;
    if ((r.d[0]&255U)!=ram[destination]) {
        if (s.a5!=0x108000) {error="object sound call requires canonical A5=108000";return false;}
        s.saved_a0=r.a[0];word(r.d[0],0x1ac0);
        if (!execute_sound_word(ram,s.sound,external_status,reads,error)) return false;
        if (s.sound.phase!=0) {s.phase=1;return true;}
        r.a[0]=s.saved_a0;s.saved_a0=0;
    }
    return finish(ram,windows,s,error);
}
}
bool execute_object_sound_lookup(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,ObjectSoundLookupState& state,
    std::uint8_t external_status,std::uint8_t& external_reads,std::string& error) {
    if (ram.size()!=65536 || !valid(state)) {error="invalid object sound lookup RAM or continuation";return false;}
    try {
        std::vector<std::uint8_t> candidate=ram;ObjectSoundLookupState next=state;std::uint8_t reads=0;
        if (!run(candidate,windows,next,external_status,reads,error)) return false;
        ram.swap(candidate);state=next;external_reads=reads;error.clear();return true;
    } catch (const std::bad_alloc&) {error="cannot allocate object sound lookup transaction";return false;}
}
}
