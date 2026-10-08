#include "ms5/stage_frame.h"
#include "ms5/stage_cue_frame.h"
#include "ms5/stage_region_frame.h"
#include "ms5/stage_spatial_frame.h"
#include "ms5/stage_sound_frame.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& r,unsigned int at,std::uint32_t value,unsigned int size=2) {
    for(unsigned int i=0;i<size;++i) r[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
bool registers_equal(const ms5::SceneMapTransferState& a,const ms5::SceneMapTransferState& b) {
    for(unsigned int i=0;i<8;++i) if(a.d[i]!=b.d[i]) return false;
    for(unsigned int i=0;i<5;++i) if(a.a[i]!=b.a[i]) return false;
    return true;
}
bool same(const ms5::StageFrameState& a,const ms5::StageFrameState& b) {
    const ms5::StageBufferFrameState& x=a.buffer; const ms5::StageBufferFrameState& y=b.buffer;
    return registers_equal(x.registers,y.registers) && x.a6==y.a6 && x.bank==y.bank && x.phase==y.phase &&
        x.saved_a6==y.saved_a6 && x.saved_slot_a4==y.saved_slot_a4 && x.saved_slot_d7==y.saved_slot_d7 &&
        x.saved_d0==y.saved_d0 && x.saved_d1==y.saved_d1 && x.saved_d7==y.saved_d7 && x.saved_a0==y.saved_a0 &&
        a.stage==b.stage && a.cue_status==b.cue_status && a.sound_kind==b.sound_kind && a.sound_phase==b.sound_phase && a.sound_saved==b.sound_saved;
}
bool same_ports(const std::vector<ms5::VideoPortWrite>& a,const std::vector<ms5::VideoPortWrite>& b) {
    if(a.size()!=b.size()) return false;
    for(std::size_t i=0;i<a.size();++i) if(a[i].size!=b[i].size || a[i].address!=b[i].address || a[i].value!=b[i].value) return false;
    return true;
}
void failure(std::vector<std::uint8_t>& r,ms5::StageFrameState& s) {
    const std::vector<std::uint8_t> before=r; const ms5::StageFrameState saved=s;
    std::vector<ms5::VideoPortWrite> ports(1); ports[0].size=1; ports[0].address=7; ports[0].value=9;
    const std::vector<ms5::VideoPortWrite> old_ports=ports;
    ms5::FixedDataResource tables; std::vector<ms5::FixedDataResource> windows;
    std::uint8_t reads=99; std::string error;
    assert(!ms5::step_stage_frame(r,tables,windows,s,255,reads,ports,error));
    assert(r==before && same(s,saved) && same_ports(ports,old_ports) && reads==99 && !error.empty());
}
void success(std::vector<std::uint8_t>& r,ms5::StageFrameState& s,std::vector<ms5::VideoPortWrite>& ports) {
    ms5::FixedDataResource tables; std::vector<ms5::FixedDataResource> windows;
    // Deliberately absent scene inputs: continuations must not revisit scene validation.
    std::uint8_t reads=99; std::string error="old";
    assert(ms5::step_stage_frame(r,tables,windows,s,255,reads,ports,error));
    assert(reads==0 && error.empty());
}
void sound_state(ms5::StageFrameState& s,const ms5::StageSoundFrameState& sound) {
    s.buffer.registers=sound.byte.registers; s.sound_kind=sound.kind; s.sound_phase=sound.phase; s.sound_saved=sound.saved;
    s.stage=sound.byte.waiting?3:0;
}
void buffer_fixture(std::vector<std::uint8_t>& r) {
    r.assign(65536,0); put(r,0xdc88,0x10db88,4); put(r,0x9152,0xcd50,4); r[0xf001]=0x80;
    put(r,0xdaf8,0x100cb8,4); put(r,0xdafc,0x101200,4); put(r,0x1204,64,4); put(r,0x120a,1);
    put(r,0x8b38,12); put(r,0x8d34,2); put(r,0x8d36,4);
    for(unsigned int i=0;i<8;++i) put(r,0xd61a-i*0x2c+0x26,0x8000);
}
}
int main() {
    ms5::StageFrameState s; assert(s.stage==0 && s.buffer.phase==0 && s.buffer.bank==2 && s.cue_status==ms5::SpriteAccepted);
    std::vector<std::uint8_t> r(65536,0); std::vector<ms5::FixedDataResource> windows; std::vector<ms5::VideoPortWrite> ports;
    std::string error;
    // These are helper-generated continuation fixtures, not full original-frame evidence.
    // Capture first buffer wait and prove holding it does not execute earlier stages.
    buffer_fixture(r); s.buffer.a6=0xabcdef01; s.buffer.bank=3; s.cue_status=ms5::SpriteFull;
    assert(ms5::step_stage_buffer_frame(r,windows,s.buffer,ports,error) && s.buffer.phase==1); s.stage=1;
    ms5::StageFrameState held=s; std::vector<std::uint8_t> held_ram=r;
    ports.resize(1); success(r,s,ports); assert(same(s,held) && r==held_ram && ports.empty());
    // Release first wait, capture the second, then complete the remaining helpers.
    put(r,0x8d34,4); put(r,0x8d36,6); success(r,s,ports); assert(s.stage==1 && s.buffer.phase==2);
    held=s; held_ram=r; success(r,s,ports); assert(same(s,held) && r==held_ram && ports.empty());
    // A late sound failure rolls back completed sprite, bank, region and spatial effects.
    put(r,0x8d34,6); r[0xd491]=255; put(r,0x4d8a,1); failure(r,s);
    r[0xd491]=0; put(r,0x4d8a,0);
    std::vector<std::uint8_t> expected=r; ms5::StageFrameState next=s; std::vector<ms5::VideoPortWrite> expected_ports;
    assert(ms5::step_stage_buffer_frame(expected,windows,next.buffer,expected_ports,error));
    bool carry=false;
    assert(ms5::step_stage_region_frame(expected,0xb4a2a,windows,next.buffer.registers,next.buffer.a6,next.buffer.bank,carry,error));
    assert(ms5::step_stage_spatial_frame(expected,0x4701e,windows,next.buffer.registers,next.buffer.bank,error));
    ms5::StageCueFrameState cue; cue.registers=next.buffer.registers;
    assert(ms5::step_stage_cue_frame(expected,windows,cue,next.buffer.a6,next.cue_status,error)); next.buffer.registers=cue.registers;
    ms5::StageSoundFrameState sound; sound.byte.registers=next.buffer.registers; std::uint8_t reads=99;
    assert(ms5::step_stage_sound_frame(expected,sound,255,reads,error)); sound_state(next,sound);
    success(r,s,ports); assert(r==expected && same(s,next) && same_ports(ports,expected_ports));
    assert(s.stage==0 && s.buffer.bank==2 && s.buffer.a6==0xabcdef01 && s.cue_status==ms5::SpriteFull && ports.size()==4);
    // Capture cue wait. Poison earlier helper inputs: only captured sprite and sound may run.
    r.assign(65536,0); r[0xde2e]=1; r[0xde2f]=1; r[0xf001]=2; put(r,0xde26,0x101200,4);
    put(r,0x1202,64); put(r,0x9152,0xcd50,4); put(r,0x8d34,2); put(r,0x8d36,4); put(r,0x8b36,12);
    s=ms5::StageFrameState(); cue=ms5::StageCueFrameState();
    assert(ms5::step_stage_cue_frame(r,windows,cue,0,s.cue_status,error) && cue.waiting_for_sprite);
    s.buffer.registers=cue.registers; s.stage=2; put(r,0xdc88,0xffffffffU,4); put(r,0xde26,0xffffffffU,4); r[0xde2f]=77;
    held=s; held_ram=r; success(r,s,ports); assert(same(s,held) && r==held_ram && ports.empty());
    put(r,0x8d34,4); put(r,0x8d38,1); failure(r,s); put(r,0x8d38,0);
    success(r,s,ports); assert(s.stage==0 && s.cue_status==ms5::SpriteAccepted && r[0xde2f]==77 && ports.empty());
    // Capture cancel's three byte waits. Changed dispatch bytes remain unpublished on resume.
    r.assign(65536,0); r[0xd491]=255; put(r,0x4d74,1); sound=ms5::StageSoundFrameState();
    assert(ms5::step_stage_sound_frame(r,sound,0,reads,error) && sound.kind==2 && sound.phase==1);
    s=ms5::StageFrameState(); sound_state(s,sound); s.buffer.a6=0x12345678; s.buffer.bank=3; s.cue_status=ms5::SpriteClipped;
    r[0xd490]=1; r[0xd491]=0x74;
    for(unsigned int phase=1;phase<=3;++phase) {
        held=s; held_ram=r; ports.resize(1); success(r,s,ports); assert(same(s,held) && r==held_ram && ports.empty());
        put(r,0x4d74,phase+1); success(r,s,ports);
        assert(r[0xd491]==0x74 && s.buffer.bank==3 && s.buffer.a6==0x12345678 && s.cue_status==ms5::SpriteClipped);
        if(phase<3) assert(s.stage==3 && s.sound_kind==2 && s.sound_phase==phase+1);
    }
    assert(s.stage==0 && s.sound_kind==0 && s.sound_phase==0 && s.sound_saved==0);
    // Rising edge through a released cue samples the external gate once and
    // retains the word helper's two waits; their resumes never sample it again.
    r.assign(65536,0); r[0xde2e]=1; r[0xf001]=2; put(r,0xde26,0x101200,4);
    put(r,0x1202,64); put(r,0x9152,0xcd50,4); put(r,0x8d34,2); put(r,0x8d36,4);
    s=ms5::StageFrameState(); cue=ms5::StageCueFrameState();
    assert(ms5::step_stage_cue_frame(r,windows,cue,0,s.cue_status,error) && cue.waiting_for_sprite);
    s.buffer.registers=cue.registers; s.stage=2; put(r,0x8d34,4);
    r[0xd490]=1; r[0x12]=1; r[0xfd82]=1; r[0xfd8d]=1;
    put(r,0x4d8a,2); put(r,0x4d8c,0); put(r,0x4d84,0x082b); put(r,0x4d86,0x0629); put(r,0x4d88,0x072a); put(r,0x4d74,1);
    ms5::FixedDataResource tables; reads=99; ports.resize(1);
    assert(ms5::step_stage_frame(r,tables,windows,s,0,reads,ports,error));
    assert(reads==1 && s.stage==3 && s.sound_kind==1 && s.sound_phase==1 && s.sound_saved==0x2b && ports.empty());
    r[0xd490]=0; r[0xd491]=0x75; put(r,0xdc88,0xffffffffU,4); put(r,0xde26,0xffffffffU,4);
    for(unsigned int phase=1;phase<=2;++phase) {
        held=s; held_ram=r; success(r,s,ports); assert(same(s,held) && r==held_ram && ports.empty());
        put(r,0x4d74,phase+1); success(r,s,ports); assert(r[0xd491]==0x75);
        if(phase==1) assert(s.stage==3 && s.sound_kind==1 && s.sound_phase==2);
    }
    assert(s.stage==0 && s.sound_kind==0 && s.sound_phase==0 && s.sound_saved==0 && r[0x4cf4]==8 && r[0x4cf5]==0x2b);
    // Each inactive buffer field must be rejected before an otherwise valid
    // captured sound resume. The baseline can finish with opaque Waiting cue
    // status: status is not required to correlate with the current stage.
    const std::vector<std::uint8_t> resume_ram=r;
    held.cue_status=ms5::SpriteWaiting; s=held; success(r,s,ports);
    assert(s.stage==0 && s.cue_status==ms5::SpriteWaiting);
    for(unsigned int field=0;field<7;++field) {
        r=resume_ram; s=held;
        switch(field) {
        case 0: s.buffer.saved_a6=1; break;
        case 1: s.buffer.saved_slot_a4=1; break;
        case 2: s.buffer.saved_slot_d7=1; break;
        case 3: s.buffer.saved_d0=1; break;
        case 4: s.buffer.saved_d1=1; break;
        case 5: s.buffer.saved_d7=1; break;
        case 6: s.buffer.saved_a0=1; break;
        }
        failure(r,s);
    }
    r=resume_ram; s=held; s.cue_status=static_cast<ms5::SpriteSubmitStatus>(4); failure(r,s);
    // Invalid combinations and captured byte address errors preserve every caller output.
    s=held; s.buffer.registers.a[0]=0; failure(r,s);
    s=ms5::StageFrameState(); s.buffer.bank=1; failure(r,s);
    s=ms5::StageFrameState(); s.stage=4; failure(r,s);
    for(unsigned int stage=0;stage<=3;++stage) {
        s=ms5::StageFrameState(); s.stage=stage; s.buffer.phase=stage==1?0:1; failure(r,s);
    }
    for(unsigned int stage=0;stage<3;++stage) {
        s=ms5::StageFrameState(); s.stage=stage; if(stage==1) s.buffer.phase=1;
        s.sound_saved=1; failure(r,s); s.sound_saved=0; s.sound_kind=1; failure(r,s);
        s.sound_kind=0; s.sound_phase=1; failure(r,s);
    }
    s=ms5::StageFrameState(); s.stage=1; s.buffer.phase=1; s.buffer.saved_slot_a4=7; failure(r,s);
    for(unsigned int kind=0;kind<=3;++kind) {
        s=ms5::StageFrameState(); s.stage=3; s.sound_kind=kind; failure(r,s);
        s.sound_phase=kind==1?3:4; failure(r,s);
    }
    s=ms5::StageFrameState(); s.stage=3; s.sound_kind=1; s.sound_phase=1; s.sound_saved=256; failure(r,s);
    s=ms5::StageFrameState(); failure(r,s); r.resize(65535); failure(r,s);
    std::cout << "stage_frame_test passed\n";
}
