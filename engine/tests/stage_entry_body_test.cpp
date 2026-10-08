#include "ms5/stage_entry_body.h"
#include "ms5/stage_sound_frame.h"
#include "ms5/stage_cue_frame.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& r,unsigned int at,std::uint32_t v,unsigned int n=2) {
    for(unsigned int i=0;i<n;++i) r[at+i]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& r,unsigned int at,unsigned int n=4) {
    std::uint32_t v=0; for(unsigned int i=0;i<n;++i) v=(v<<8)|r[at+i]; return v;
}
bool same(const ms5::StageEntryBodyState& a,const ms5::StageEntryBodyState& b) {
    const ms5::StageBufferFrameState& x=a.frame.buffer; const ms5::StageBufferFrameState& y=b.frame.buffer;
    for(unsigned int i=0;i<8;++i) if(x.registers.d[i]!=y.registers.d[i]) return false;
    for(unsigned int i=0;i<5;++i) if(x.registers.a[i]!=y.registers.a[i]) return false;
    return a.a5==b.a5 && a.phase==b.phase && a.frame.stage==b.frame.stage && a.frame.cue_status==b.frame.cue_status &&
        a.frame.sound_kind==b.frame.sound_kind && a.frame.sound_phase==b.frame.sound_phase && a.frame.sound_saved==b.frame.sound_saved &&
        x.a6==y.a6 && x.bank==y.bank && x.phase==y.phase && x.saved_a6==y.saved_a6 && x.saved_slot_a4==y.saved_slot_a4 &&
        x.saved_slot_d7==y.saved_slot_d7 && x.saved_d0==y.saved_d0 && x.saved_d1==y.saved_d1 && x.saved_d7==y.saved_d7 && x.saved_a0==y.saved_a0;
}
ms5::FixedDataResource tables() {
    ms5::FixedDataResource t; t.source_cpu_address=t.source_rom_offset=0x1af12; t.data.assign(512,0);
    for(unsigned int i=0;i<256;++i) put(t.data,i*2,0x320); return t;
}
ms5::FixedDataResource lookup() {
    ms5::FixedDataResource w; w.source_cpu_address=w.source_rom_offset=0x30ec;
    const std::uint8_t raw[]={0x60,0x70,0x80,0x90,0x90,0x90,0x90,0x90}; w.data.assign(raw,raw+8); return w;
}
void fixture(std::vector<std::uint8_t>& r,ms5::StageEntryBodyState& s) {
    r.assign(65536,0); s=ms5::StageEntryBodyState(); s.frame.buffer.a6=0x103000; s.frame.buffer.bank=3;
    s.frame.buffer.registers.a[3]=0xabcdef01; put(r,0x3076,0x106000,4);
    put(r,0xcb8,0x270e,4); put(r,0xda8,0x270e,4); put(r,0xdc88,0x10db88,4); r[0xc60]=255; r[0x12]=2;
    for(unsigned int i=0;i<8;++i) put(r,0xd61a-i*0x2c+0x26,0x8000);
}
void failure(std::vector<std::uint8_t>& r,ms5::StageEntryBodyState& s,const ms5::FixedDataResource& t,
    const std::vector<ms5::FixedDataResource>& windows) {
    const std::vector<std::uint8_t> before=r; const ms5::StageEntryBodyState old=s;
    std::vector<ms5::VideoPortWrite> ports(1); ports[0].size=1; ports[0].address=7; ports[0].value=9;
    std::uint8_t reads=99; std::string error;
    assert(!ms5::step_stage_entry_body(r,t,windows,s,255,reads,ports,error));
    assert(r==before && same(s,old) && reads==99 && ports.size()==1 && ports[0].size==1 && ports[0].address==7 && ports[0].value==9 && !error.empty());
}
void resume(std::vector<std::uint8_t>& r,ms5::StageEntryBodyState& s,std::vector<ms5::VideoPortWrite>& ports) {
    ms5::FixedDataResource absent; std::vector<ms5::FixedDataResource> empty; std::uint8_t reads=99; std::string error;
    assert(ms5::step_stage_entry_body(r,absent,empty,s,255,reads,ports,error)); assert(reads==0 && ports.empty() && error.empty());
}
}
int main() {
    std::vector<std::uint8_t> r; ms5::StageEntryBodyState s; ms5::FixedDataResource t=tables();
    std::vector<ms5::FixedDataResource> windows(1,lookup()),empty; std::vector<ms5::VideoPortWrite> ports; std::string error; std::uint8_t reads=99;
    assert(s.phase==0 && s.a5==0x108000);
    // Controlled null-scene/event fixture verifies composition, not original ROM equivalence.
    for(unsigned int index=0;index<8;++index) {
        fixture(r,s); r[0xfd8c]=static_cast<std::uint8_t>(0xf8|index); r[0xd683]=0x80;
        assert(ms5::step_stage_entry_body(r,t,windows,s,0,reads,ports,error));
        assert(s.phase==2 && s.frame.stage==0 && s.a5==0x108000 && s.frame.buffer.a6==0x103000 && s.frame.buffer.bank==2);
        assert(s.frame.buffer.registers.a[3]!=0); assert(get(r,0x3000)==0x47af0 && get(r,0xbf4)==0xe9150);
        assert(r[0xd683]==0xaa && r[0xd67e]==windows[0].data[index] && r[0xd67f]==255 && reads==0);
        assert(ports.size()==9 && ports[0].address==0x2ffff2 && ports[0].value==0x2000 && ports[4].address==0x300001 && ports[5].address==0x2ffff2 && ports[5].value==0x2000);
        failure(r,s,t,windows); // Completed entry cannot initialize a second time.
    }
    // RAM indirection is read before event initialization; nonnull stream adds
    // its PVC pair between watchdog and the frame's scene entry ports.
    fixture(r,s); put(r,0x600a,0x106100,4); put(r,0x6100,0x106200,4); put(r,0x6200,0);
    assert(ms5::step_stage_entry_body(r,t,windows,s,0,reads,ports,error));
    assert(s.phase==2 && get(r,0xc6a)==0x106202 && ports.size()==11 && ports[4].address==0x300001 &&
        ports[5].address==0x2ffff2 && ports[5].value==0x1000 && ports[7].address==0x2ffff2 && ports[7].value==0x2000);
    // The record aliases scene metadata. Initialization changes the later
    // event pointer and target, so caching the original values would differ.
    fixture(r,s); put(r,0x3076,0x10d41a,4);
    ms5::FixedDataResource indirect; indirect.source_cpu_address=indirect.source_rom_offset=0xa0; indirect.data.assign(4,0);
    windows.push_back(indirect);
    assert(ms5::step_stage_entry_body(r,t,windows,s,0,reads,ports,error));
    assert(s.phase==2 && ports[4].address==0x300001 && ports[4].value==0x80 && get(r,0xde26)==0x7fff0000);
    windows.pop_back();
    // A fresh body can finish initialization at a frame sound wait. Subsequent
    // resource-free resumes preserve host changes to callback and entry flags.
    fixture(r,s); r[0xd491]=255; put(r,0x4d74,1);
    assert(ms5::step_stage_entry_body(r,t,windows,s,0,reads,ports,error));
    assert(s.phase==1 && s.frame.stage==3 && get(r,0x3000)==0x47af0 && ports.size()==9);
    put(r,0x3000,0x12345678,4); r[0xd683]=0x55;
    for(unsigned int phase=1;phase<=3;++phase) {
        resume(r,s,ports); assert(s.phase==1 && get(r,0x3000)==0x12345678 && r[0xd683]==0x55);
        put(r,0x4d74,phase+1); resume(r,s,ports);
    }
    assert(s.phase==2 && get(r,0x3000)==0x12345678 && r[0xd683]==0x55);
    // Missing lookup and invalid event pointer fail after scene/cue publication.
    fixture(r,s); failure(r,s,t,empty);
    std::vector<ms5::FixedDataResource> duplicate=windows; duplicate.push_back(windows[0]); fixture(r,s); failure(r,s,t,duplicate);
    fixture(r,s); put(r,0x600a,0x10ffff,4); failure(r,s,t,windows);
    // A late frame failure also rolls back event restart and callback publication.
    fixture(r,s); put(r,0xdc88,0x10fff0,4); failure(r,s,t,windows);
    // Record input supports unique fixed windows and rejects overlap/partial reads.
    fixture(r,s); ms5::FixedDataResource record; record.source_cpu_address=record.source_rom_offset=0x40000; record.data.assign(16,0);
    windows.push_back(record); put(r,0x3076,0x40000,4);
    assert(ms5::step_stage_entry_body(r,t,windows,s,0,reads,ports,error) && s.phase==2);
    fixture(r,s); put(r,0x3076,0x40000,4); windows.push_back(record); failure(r,s,t,windows); windows.pop_back();
    windows.back().data.resize(14); fixture(r,s); put(r,0x3076,0x40000,4); failure(r,s,t,windows); windows.pop_back();
    for(unsigned int pointer=0;pointer<3;++pointer) {
        fixture(r,s); put(r,0x3076,pointer==0?0xffffffffU:(pointer==1?0x106001U:0x200000U),4); failure(r,s,t,windows);
    }
    // Helper-captured sound continuation resumes without record/resource reads
    // or flag/callback publication; frame outputs alone determine completion.
    r.assign(65536,0); r[0xd491]=255; put(r,0x4d74,1);
    ms5::StageSoundFrameState sound; assert(ms5::step_stage_sound_frame(r,sound,0,reads,error) && sound.byte.waiting);
    s=ms5::StageEntryBodyState(); s.phase=1; s.frame.stage=3; s.frame.buffer.a6=0xffffffffU;
    s.frame.buffer.registers=sound.byte.registers; s.frame.sound_kind=sound.kind; s.frame.sound_phase=sound.phase; s.frame.sound_saved=sound.saved;
    r[0xd683]=0x55; r[0xd67e]=0x66; r[0xd67f]=0x77; r[0xd491]=0x78;
    for(unsigned int phase=1;phase<=3;++phase) {
        const std::vector<std::uint8_t> before=r; const ms5::StageEntryBodyState held=s; ports.resize(1); resume(r,s,ports); assert(r==before && same(s,held));
        put(r,0x4d74,phase+1); resume(r,s,ports); assert(r[0xd683]==0x55 && r[0xd67e]==0x66 && r[0xd67f]==0x77 && r[0xd491]==0x78);
        assert(s.phase==(phase==3?2U:1U));
    }
    failure(r,s,t,windows);
    // Captured cue resume cannot reload an invalid record pointer or callback.
    r.assign(65536,0); r[0xde2e]=1; r[0xf001]=2; put(r,0xde26,0x101200,4); put(r,0x1202,64);
    put(r,0x9152,0xcd50,4); put(r,0x8d34,2); put(r,0x8d36,4);
    ms5::StageCueFrameState cue; ms5::SpriteSubmitStatus status=ms5::SpriteAccepted;
    assert(ms5::step_stage_cue_frame(r,empty,cue,0,status,error) && cue.waiting_for_sprite);
    s=ms5::StageEntryBodyState(); s.phase=1; s.frame.stage=2; s.frame.buffer.registers=cue.registers; s.frame.cue_status=status;
    s.frame.buffer.a6=0xffffffffU; resume(r,s,ports); assert(s.phase==1);
    put(r,0x8d34,4); put(r,0x8d38,1); failure(r,s,t,windows); put(r,0x8d38,0); resume(r,s,ports); assert(s.phase==2 && s.frame.cue_status==ms5::SpriteAccepted);
    // Invalid phase, A5, enum and inactive metadata preserve every caller output.
    fixture(r,s); s.phase=3; failure(r,s,t,windows);
    fixture(r,s); s.phase=1; failure(r,s,t,windows);
    fixture(r,s); s.frame.stage=1; failure(r,s,t,windows);
    fixture(r,s); s.a5=0x108001; failure(r,s,t,windows);
    fixture(r,s); s.frame.buffer.bank=1; failure(r,s,t,windows);
    fixture(r,s); s.frame.cue_status=static_cast<ms5::SpriteSubmitStatus>(4); failure(r,s,t,windows);
    for(unsigned int field=0;field<11;++field) {
        fixture(r,s);
        switch(field) {
        case 0:s.frame.buffer.phase=1;break; case 1:s.frame.buffer.saved_a6=1;break; case 2:s.frame.buffer.saved_slot_a4=1;break;
        case 3:s.frame.buffer.saved_slot_d7=1;break; case 4:s.frame.buffer.saved_d0=1;break; case 5:s.frame.buffer.saved_d1=1;break;
        case 6:s.frame.buffer.saved_d7=1;break; case 7:s.frame.buffer.saved_a0=1;break; case 8:s.frame.sound_kind=1;break; case 9:s.frame.sound_saved=1;break; case 10:s.frame.sound_phase=1;break;
        }
        failure(r,s,t,windows);
    }
    fixture(r,s); r.resize(65535); failure(r,s,t,windows);
    std::cout<<"stage_entry_body_test passed\n";
}
