#include "ms5/stage_hud_counter.h"
#include "ms5/stage_block_draw.h"
#include <cassert>
#include <iostream>
namespace {
ms5::StageHudCounterState initial(std::uint16_t value=0x1200) {
    ms5::StageHudCounterState s;
    for(unsigned int i=0;i<8;++i)s.sound.byte.registers.d[i]=0xabcd1234U+i*0x10001U;
    for(unsigned int i=0;i<5;++i)s.sound.byte.registers.a[i]=0x87654320U+i*2;
    s.sound.byte.registers.d[0]=0xabcd0000U|value;s.a6=0x87654321;return s;
}
bool same(const ms5::StageHudCounterState& a,const ms5::StageHudCounterState& b) {
    if(a.a5!=b.a5||a.a6!=b.a6||a.phase!=b.phase||a.saved_d0!=b.saved_d0||a.sound.phase!=b.sound.phase||
       a.sound.saved_low!=b.sound.saved_low||a.sound.byte.waiting!=b.sound.byte.waiting)return false;
    for(unsigned int i=0;i<8;++i)if(a.sound.byte.registers.d[i]!=b.sound.byte.registers.d[i])return false;
    for(unsigned int i=0;i<5;++i)if(a.sound.byte.registers.a[i]!=b.sound.byte.registers.a[i])return false;
    return true;
}
bool same_ports(const std::vector<ms5::VideoPortWrite>& a,const std::vector<ms5::VideoPortWrite>& b) {
    if(a.size()!=b.size())return false;
    for(std::size_t i=0;i<a.size();++i)if(a[i].size!=b[i].size||a[i].address!=b[i].address||a[i].value!=b[i].value)return false;
    return true;
}
void put(std::vector<std::uint8_t>& ram,std::size_t at,std::uint16_t value) {
    assert(at+1<ram.size());ram[at]=static_cast<std::uint8_t>(value>>8);ram[at+1]=static_cast<std::uint8_t>(value);
}
std::vector<ms5::VideoPortWrite> old_ports() {
    std::vector<ms5::VideoPortWrite> p(1);p[0].size=1;p[0].address=0x300001;p[0].value=0x12;return p;
}
std::vector<ms5::FixedDataResource> table() {
    std::vector<ms5::FixedDataResource> w(1);w[0].source_cpu_address=w[0].source_rom_offset=0x4e272;
    for(unsigned int i=0;i<16;++i){w[0].data.push_back(0x30);w[0].data.push_back(static_cast<std::uint8_t>(i*16));}
    return w;
}
void failure(std::vector<std::uint8_t> ram,ms5::StageHudCounterState s,const std::vector<ms5::FixedDataResource>& windows) {
    const std::vector<std::uint8_t> before=ram;const ms5::StageHudCounterState saved=s;
    std::uint8_t reads=98;std::vector<ms5::VideoPortWrite> ports=old_ports(),saved_ports=ports;std::string error;
    assert(!ms5::step_stage_hud_counter(ram,windows,s,0,reads,ports,error));
    assert(!error.empty()&&ram==before&&same(s,saved)&&reads==98&&same_ports(ports,saved_ports));
}
void blank_and_high() {
    std::vector<std::uint8_t> ram(65536,0);ms5::StageHudCounterState s=initial(),before=s;
    std::vector<ms5::VideoPortWrite> ports=old_ports();std::uint8_t reads=99;std::string error="old";
    assert(ms5::step_stage_hud_counter(ram,std::vector<ms5::FixedDataResource>(),s,0,reads,ports,error));
    assert(same(s,before)&&ports.empty()&&reads==0&&error.empty());
    s=initial(0x9a00);ram[0xdd1f]=1;const std::vector<std::uint8_t> saved=ram;
    ms5::ObjectRestartState full;for(unsigned int i=0;i<8;++i)full.d[i]=s.sound.byte.registers.d[i];
    for(unsigned int i=0;i<5;++i)full.a[i]=s.sound.byte.registers.a[i];full.a[5]=s.a5;full.a[6]=s.a6;
    full.d[0]=(full.d[0]&0xffff0000U)|0x7243;full.d[1]=(full.d[1]&0xffff0000U)|0xc904;full.d[2]=4;full.d[3]=2;
    std::vector<ms5::VideoPortWrite> want;
    assert(ms5::execute_stage_block_draw(ram,0x35f0,std::vector<ms5::FixedDataResource>(),full,want,error));
    assert(ms5::step_stage_hud_counter(ram,std::vector<ms5::FixedDataResource>(),s,0,reads,ports,error));
    for(unsigned int i=0;i<8;++i)assert(full.d[i]==s.sound.byte.registers.d[i]);
    for(unsigned int i=0;i<5;++i)assert(full.a[i]==s.sound.byte.registers.a[i]);
    assert(same_ports(ports,want)&&ports.size()==9&&ram==saved&&reads==0);
}
void normal_and_shape() {
    const unsigned int values[]={0x1200,0x0f00,0x09ff,0x0020,0x001f};
    for(unsigned int i=0;i<5;++i) {
        std::vector<std::uint8_t> ram(65536,0);ram[0xdd1f]=1;ram[0xdd20]=1;put(ram,0x4e52+8,1);
        ms5::StageHudCounterState s=initial(static_cast<std::uint16_t>(values[i]));
        const std::uint32_t a3=s.sound.byte.registers.a[3],a6=s.a6;
        std::vector<ms5::VideoPortWrite> ports;std::uint8_t reads=99;std::string error;
        assert(ms5::step_stage_hud_counter(ram,table(),s,0,reads,ports,error));
        assert(ports.size()==10&&s.phase==0&&s.saved_d0==0&&reads==0);
        assert(s.sound.byte.registers.d[0]==((values[i]>>12)*2U<<16|0x72c3U));
        unsigned int weight=0;
        if(values[i]<0xa00){unsigned int shifted=(values[i]&255U)<<3;weight=((values[i]&32U)?~shifted:shifted)&255U;weight>>=3;}
        assert(ram[0x4e52+0xe]==weight&&ram[0x4e52+0xc]==0x0a&&ram[0x4e52+0xd]==0x0d);
        assert(s.sound.byte.registers.a[3]==a3&&s.a6==a6&&s.a5==0x108000);
    }
    // Odd fixed-window base is valid when the actual WORD reads are aligned.
    std::vector<ms5::FixedDataResource> windows=table();windows[0].source_cpu_address--;windows[0].source_rom_offset--;
    windows[0].data.insert(windows[0].data.begin(),0x55);
    std::vector<std::uint8_t> ram(65536,0);ram[0xdd1f]=1;ms5::StageHudCounterState s=initial();
    s.a5=0x108001;ram[0xdd20]=1;ram[0xdd21]=1;std::uint8_t reads=0;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_stage_hud_counter(ram,windows,s,0,reads,ports,error));assert(s.a5==0x108001&&ports.size()==10);
}
ms5::StageHudCounterState capture(std::vector<std::uint8_t>& ram) {
    ram.assign(65536,0);ram[0xdd1f]=1;put(ram,0x4d8a,0);put(ram,0x4d8c,6);
    put(ram,0x4d82,0x1020);put(ram,0x4d84,0x1040);put(ram,0x4d86,0x1060);
    put(ram,0x4d74,1);put(ram,0x4d76,0);
    ms5::StageHudCounterState s=initial(0x05ff);std::uint8_t reads=99;
    std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
    assert(ms5::step_stage_hud_counter(ram,table(),s,0,reads,ports,error));
    assert(s.phase==1&&s.sound.phase==1&&s.sound.byte.waiting&&s.saved_d0==0x05ff);
    assert(ram[0xdd20]==255&&ports.empty()&&reads==0);return s;
}
void pending() {
    std::vector<std::uint8_t> ram;ms5::StageHudCounterState s=capture(ram);
    // Hold/resume must not reread the now blank flag or decrement this counter.
    ram[0xdd1f]=0;ram[0xdd20]=0x77;const std::vector<std::uint8_t> held=ram;const ms5::StageHudCounterState saved=s;
    std::uint8_t reads=98;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
    assert(ms5::step_stage_hud_counter(ram,std::vector<ms5::FixedDataResource>(),s,255,reads,ports,error));
    assert(ram==held&&same(s,saved)&&reads==0&&ports.empty());
    // Resume reaches post-sound failure only after actual byte writes; all roll back.
    put(ram,0x4d74,3);failure(ram,s,std::vector<ms5::FixedDataResource>());
    assert(ms5::step_stage_hud_counter(ram,table(),s,255,reads,ports,error));
    assert(s.phase==0&&s.sound.phase==0&&!s.sound.byte.waiting&&s.saved_d0==0&&s.sound.saved_low==0);
    assert(ram[0xdd20]==31&&ram[0x4cf4]==0x10&&ram[0x4cf5]==0x20&&ports.size()==10&&reads==0);
    assert(s.sound.byte.registers.d[0]==0x72c3);
    // Release only the high byte: second byte captures a distinct phase2 wait.
    s=capture(ram);ram[0xdd1f]=0;ram[0xdd20]=0x66;put(ram,0x4d74,2);
    assert(ms5::step_stage_hud_counter(ram,table(),s,0,reads,ports,error));
    assert(s.phase==1&&s.sound.phase==2&&s.sound.byte.waiting&&ram[0x4cf4]==0x10&&ram[0xdd20]==0x66);
    ram[0x4cf4]=0xaa;const ms5::StageHudCounterState low_saved=s;
    assert(ms5::step_stage_hud_counter(ram,table(),s,0,reads,ports,error));assert(same(s,low_saved)&&ram[0x4cf4]==0xaa);
    put(ram,0x4d74,3);
    // Phase2 can write the pending second byte, publish its tail/counter and
    // finish sound before lookup fails. Every effect and pending field rolls back.
    assert(s.sound.phase==2 && ram[0x4cf5]!=0x20);
    failure(ram,s,std::vector<ms5::FixedDataResource>());
    assert(ms5::step_stage_hud_counter(ram,table(),s,0,reads,ports,error));
    assert(s.phase==0&&ram[0x4cf4]==0xaa&&ram[0x4cf5]==0x20&&ram[0xdd20]==31&&ports.size()==10);
    s=capture(ram);s.a5=0x108001;failure(ram,s,table());
}
void aliases_and_reads() {
    std::vector<std::uint8_t> ram(65536,0);ms5::StageHudCounterState s=initial(0x20);
    // Counter/flag alias slot12 weight/target lowBYTE; accesses remain live.
    s.a5=0xff140;put(ram,0x4e52+8,1);ram[0x4e5f]=1;ram[0x4e60]=1;
    std::uint8_t reads=99;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_stage_hud_counter(ram,table(),s,0,reads,ports,error));
    assert(s.a5==0xff140&&ram[0x4e60]==31&&ram[0x4e5f]==0x0d&&reads==0);
    // Actual conditional external sample is reported even when sound is filtered.
    ram.assign(65536,0);s=initial(1);ram[0xdd1f]=1;ram[0x12]=1;ram[0xfd82]=1;
    assert(ms5::step_stage_hud_counter(ram,table(),s,255,reads,ports,error));
    assert(reads==1&&ram[0xdd20]==31&&ram[0x4d8c]==0&&ram[0x4d8d]==0&&ports.size()==10);
    s=initial(1);ram[0xdd20]=0;failure(ram,s,std::vector<ms5::FixedDataResource>());
}
void errors() {
    std::vector<std::uint8_t> ram(65536,0);ram[0xdd1f]=1;put(ram,0x4e52+8,1);
    ms5::StageHudCounterState s=initial();std::vector<ms5::FixedDataResource> windows(1);
    // First digit succeeds and emits ports, second WORD is absent.
    windows[0].source_cpu_address=windows[0].source_rom_offset=0x4e274;windows[0].data.push_back(0x30);windows[0].data.push_back(0x10);
    failure(ram,s,windows);windows=table();windows.push_back(windows[0]);failure(ram,s,windows);
    windows=table();windows[0].data.resize(3);failure(ram,s,windows);
    windows=table();windows[0].source_rom_offset++;failure(ram,s,windows);
    s=initial();s.saved_d0=1;failure(ram,s,table());s=initial();s.sound.saved_low=1;failure(ram,s,table());
    s=initial();s.sound.phase=1;failure(ram,s,table());s=initial();s.sound.byte.waiting=true;failure(ram,s,table());
    s=initial();s.phase=2;failure(ram,s,table());s=initial();s.phase=1;failure(ram,s,table());
    s=initial();s.a5=0xffffffff;failure(ram,s,table());s=initial(1);s.a5=0x108001;
    ram[0xdd20]=1;ram[0xdd21]=0;failure(ram,s,table());
    ram.resize(65535);failure(ram,initial(),table());
}
}
int main(){blank_and_high();normal_and_shape();pending();aliases_and_reads();errors();std::cout<<"stage_hud_counter_test: passed\n";return 0;}
