#include "ms5/animation_execution.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& data,unsigned int at,unsigned int size,std::uint32_t value) {
    assert(at<=data.size() && size<=data.size()-at);
    for(unsigned int i=0;i<size;++i)data[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& data,unsigned int at,unsigned int size=2) {
    assert(at<=data.size() && size<=data.size()-at);std::uint32_t value=0;
    for(unsigned int i=0;i<size;++i)value=(value<<8)|data[at+i];return value;
}
ms5::AnimationExecutionState initial() {
    ms5::AnimationExecutionState s;s.a6=0x102000;
    for(unsigned int i=0;i<8;++i)s.sprite.registers.d[i]=0xabcd1200U+i;
    for(unsigned int i=0;i<5;++i)s.sprite.registers.a[i]=0x76540000U+i;return s;
}
bool same(const ms5::AnimationExecutionState& a,const ms5::AnimationExecutionState& b) {
    for(unsigned int i=0;i<8;++i)if(a.sprite.registers.d[i]!=b.sprite.registers.d[i])return false;
    for(unsigned int i=0;i<5;++i)if(a.sprite.registers.a[i]!=b.sprite.registers.a[i])return false;
    return a.a5==b.a5 && a.a6==b.a6 && a.phase==b.phase && a.saved_a0==b.saved_a0 &&
        a.saved_a1==b.saved_a1 && a.saved_bank==b.saved_bank && a.saved_list_end==b.saved_list_end && a.sprite.waiting==b.sprite.waiting &&
        a.callback_saved_a0==b.callback_saved_a0 && a.callback_sound_phase==b.callback_sound_phase &&
        a.callback_saved_low==b.callback_saved_low && a.callback_waiting==b.callback_waiting;
}
std::vector<std::uint8_t> fixture(std::uint32_t pointer=0x50000) {
    std::vector<std::uint8_t> ram(65536,0);put(ram,0x2026,4,pointer);put(ram,0x202c,2,0x100);
    put(ram,0x2012,4,0x12340000);put(ram,0x2016,2,0x4502);put(ram,0x201e,2,0x8123);
    put(ram,0x2042,2,0xffff);put(ram,0x2046,2,0x40);put(ram,0x8d34,2,0x100);
    put(ram,0x9152,4,0xcd50);for(unsigned int i=0;i<256;++i)put(ram,0x8b34+i*2,2,i*12);
    return ram;
}
std::vector<ms5::AnimationResource> script(const std::vector<std::uint8_t>& bytes,std::uint32_t address=0x50000) {
    std::vector<ms5::AnimationResource> scripts(1);scripts[0].source_cpu_address=scripts[0].source_rom_offset=address;scripts[0].data=bytes;return scripts;
}
std::vector<std::uint8_t> draw(unsigned int control=0,unsigned int x=0,unsigned int y=0,std::uint32_t id=0x12345) {
    std::vector<std::uint8_t> bytes(8);bytes[0]=4;bytes[1]=control;bytes[2]=x;bytes[3]=y;put(bytes,4,4,id);return bytes;
}
void append(std::vector<std::uint8_t>& a,const std::vector<std::uint8_t>& b) {a.insert(a.end(),b.begin(),b.end());}
std::vector<ms5::VideoPortWrite> old_ports() {
    std::vector<ms5::VideoPortWrite> ports(1);ports[0].size=1;ports[0].address=0x300001;ports[0].value=0x55;return ports;
}
void ports_are(const std::vector<ms5::VideoPortWrite>& ports,unsigned int pairs) {
    if(ports.size()!=pairs*2)std::cerr<<"expected "<<pairs*2<<" port writes, got "<<ports.size()<<"\n";
    assert(ports.size()==pairs*2);
    for(unsigned int i=0;i<pairs;++i){assert(ports[i*2].size==2&&ports[i*2].address==0x2ffff2&&ports[i*2].value==0x1000);
        assert(ports[i*2+1].size==2&&ports[i*2+1].address==0x2ffff0&&ports[i*2+1].value==0);}
}
void failure(std::vector<std::uint8_t> ram,const std::vector<ms5::AnimationResource>& scripts,ms5::AnimationExecutionState state) {
    const std::vector<std::uint8_t> before=ram;const ms5::AnimationExecutionState saved=state;
    for(unsigned int input=0;input<2;++input){bool carry=input!=0;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(!ms5::step_animation_execution(ram,scripts,state,carry,ports,error));
        assert(!error.empty()&&ram==before&&same(state,saved)&&carry==(input!=0));
        assert(ports.size()==1&&ports[0].size==1&&ports[0].address==0x300001&&ports[0].value==0x55);}
}
void data_failure(std::vector<std::uint8_t> ram,const std::vector<ms5::AnimationResource>& scripts,
    const std::vector<ms5::FixedDataResource>& windows,ms5::AnimationExecutionState state) {
    const std::vector<std::uint8_t> before=ram;const ms5::AnimationExecutionState saved=state;
    for(unsigned int input=0;input<2;++input){bool carry=input!=0;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(!ms5::step_animation_execution(ram,scripts,windows,state,carry,ports,error));
        assert(!error.empty()&&ram==before&&same(state,saved)&&carry==(input!=0));
        assert(ports.size()==1&&ports[0].size==1&&ports[0].address==0x300001&&ports[0].value==0x55);}
}
std::vector<ms5::FixedDataResource> control_data() {
    std::vector<ms5::FixedDataResource> windows(1);windows[0].source_cpu_address=windows[0].source_rom_offset=0x4276c;
    windows[0].data.resize(65536,0);
    put(windows[0].data,0,2,0x8000);put(windows[0].data,65534,2,0x7fff);
    put(windows[0].data,0x4a76c - 0x4276c,2,0xfffe);put(windows[0].data,0x4a76e - 0x4276c,2,1);
    put(windows[0].data,0x4a88c - 0x4276c,2,0x8026);put(windows[0].data,0x4a76a - 0x4276c,2,0x7e);
    put(windows[0].data,0x4a574 - 0x4276c,4,0x2b3e8);put(windows[0].data,0x4a578 - 0x4276c,4,0x2b3fa);
    return windows;
}
int signed_word(unsigned int value) {return value<0x8000?static_cast<int>(value):static_cast<int>(value)-65536;}
std::vector<std::uint8_t> control_ram(std::uint32_t pointer=0x50000) {
    std::vector<std::uint8_t> ram=fixture();put(ram,0x8026,4,pointer);put(ram,0x802a,2,0);put(ram,0x802c,2,0x100);ram[0x8017]=0;return ram;
}
void field_branches() {
    const unsigned int selectors[]={0,1,0x90,0x3fff,0x4000,0x7fff,0x8000,0xffff};
    const unsigned int values[]={0,1,0x80,0xff};const std::vector<ms5::FixedDataResource> windows=control_data();
    for(unsigned int n=0;n<8;++n)for(unsigned int d=0;d<4;++d)for(unsigned int f=0;f<4;++f){
        std::vector<std::uint8_t> ram=control_ram();ms5::AnimationExecutionState state=initial(),want=state;state.a6=want.a6=0x108000;
        const unsigned int table=static_cast<unsigned int>(0x4a76c+signed_word((selectors[n]*2)&65535));
        const unsigned int offset=get(windows[0].data,table-0x4276c);const unsigned int field=static_cast<unsigned int>(0x108000+signed_word(offset));
        put(ram,field-0x100000,1,values[f]);std::vector<std::uint8_t> bytes(0x21,0);
        bytes[0]=0x0c;bytes[1]=values[d];put(bytes,2,2,selectors[n]);put(bytes,4,4,0x50020);bytes[0x20]=0x28;
        const bool branch=(values[d]!=0)==(values[f]!=0);
        want.sprite.registers.d[0]=(want.sprite.registers.d[0]&0xffff0000U)|(offset&0xff00U)|(values[f]?255U:0U);
        want.sprite.registers.d[1]=(want.sprite.registers.d[1]&0xffffff00U)|(branch&&values[d]?255U:0U);
        want.sprite.registers.d[6]=branch?0x50020:0x50000;want.sprite.registers.d[7]=branch?0xffffffffU:0;
        want.sprite.registers.a[0]=0x108026;want.sprite.registers.a[1]=branch?0x50021:0x5000a;want.sprite.registers.a[2]=0x4a76c;
        bool carry=!branch;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,script(bytes),windows,state,carry,ports,error));
        assert(carry==branch&&same(state,want)&&get(ram,0x8026,4)==(branch?0x50020:0x50008));ports_are(ports,2);
    }
    // Branch pointer storage changes the RAM bytes fetched as the next opcode.
    std::vector<std::uint8_t> ram=control_ram(0x105000);ms5::AnimationExecutionState state=initial();state.a6=0x108000;
    put(ram,0x5000,1,0x0c);put(ram,0x5001,1,0);put(ram,0x5002,2,1);put(ram,0x5004,4,0x108026);ram[0x8001]=0;
    bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),windows,state,carry,ports,error));
    assert(!carry&&get(ram,0x8026,4)==0x108026&&state.sprite.registers.d[1]==0xabcd1210&&get(ram,0x802a)==0xf00);
}
void control_callbacks() {
    const unsigned int indices[]={0,1,0x7f,0x80,0xff};
    for(unsigned int which=0;which<2;++which)for(unsigned int i=0;i<5;++i)for(unsigned int profile=0;profile<5;++profile){
        std::vector<std::uint8_t> ram=control_ram();ms5::AnimationExecutionState state=initial(),want=state;
        state.a6=want.a6=0x108000;state.a5=want.a5=0x108002;const unsigned int index_at=0x807c+which;
        ram[index_at]=indices[i];unsigned int source=profile>=2?0x108076+(profile-2)*2:0;
        if(profile>=2)put(ram,source-0x100000,4,0xa1b2c3d4);
        const unsigned int live=ram[index_at];const unsigned int operand=profile==0?0x106000:profile==1?0x60000:source-live*4;
        std::vector<ms5::FixedDataResource> windows=control_data();unsigned int value=0;
        if(profile==0){source=operand+live*4;value=0x81230000|(live<<8)|which;put(ram,source-0x100000,4,value);}
        else if(profile==1){ms5::FixedDataResource data;data.source_cpu_address=data.source_rom_offset=operand;data.data.resize(1024,0);
            value=0x76540000|(live<<8)|which;put(data.data,live*4,4,value);windows.push_back(data);}
        else value=get(ram,source-0x100000,4);
        std::vector<std::uint8_t> bytes(8,0);bytes[0]=0x14;bytes[1]=0x1d+which;put(bytes,2,4,operand);
        want.sprite.registers.d[0]=live*4;want.sprite.registers.d[1]&=0xffffff00U;
        want.sprite.registers.d[6]=0x50000;want.sprite.registers.d[7]=0;
        want.sprite.registers.a[0]=0x108026;want.sprite.registers.a[1]=0x50008;
        bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,script(bytes),windows,state,carry,ports,error));
        assert(!carry&&same(state,want)&&get(ram,0x8078,4)==value&&get(ram,0x8026,4)==0x50006);ports_are(ports,4);
    }
    // Callback destination aliases live bank shadow: restore follows the
    // LONG store and overwrites its highWORD, rather than restoring earlier.
    std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial();state.a6=0x101000;state.a5=0x109068;
    put(ram,0x1026,4,0x50000);put(ram,0x102a,2,0);ram[0x1017]=0;ram[0x107c]=0;put(ram,0x6000,4,0xabcd5678);
    std::vector<std::uint8_t> bytes(8,0);bytes[0]=0x14;bytes[1]=0x1d;put(bytes,2,4,0x106000);
    bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,script(bytes),control_data(),state,carry,ports,error));
    assert(!carry&&get(ram,0x1078,4)==0x00005678&&get(ram,0x1026,4)==0x50006);ports_are(ports,4);
}
void control_errors() {
    std::vector<std::uint8_t> ram=control_ram();ms5::AnimationExecutionState state=initial();state.a6=0x108000;
    std::vector<std::uint8_t> bytes(10,0);bytes[0]=0x0c;bytes[1]=1;put(bytes,2,2,0);put(bytes,4,4,0x50008);
    std::vector<ms5::FixedDataResource> windows=control_data(),bad=windows;
    data_failure(ram,script(bytes),std::vector<ms5::FixedDataResource>(),state);
    bad.push_back(windows[0]);data_failure(ram,script(bytes),bad,state);
    bad=windows;bad[0].source_cpu_address=bad[0].source_rom_offset=0x4a76c;bad[0].data.assign(1,0);data_failure(ram,script(bytes),bad,state);
    bad=windows;ms5::FixedDataResource overlap;overlap.source_cpu_address=overlap.source_rom_offset=0x4a76d;overlap.data.assign(1,0);bad.push_back(overlap);data_failure(ram,script(bytes),bad,state);
    bad=windows;bad[0].source_rom_offset++;data_failure(ram,script(bytes),bad,state);
    std::vector<std::uint8_t> truncated=bytes;truncated.resize(7);data_failure(ram,script(truncated),windows,state);
    // Negative raw field offset falls belowRAM only when it is actually read.
    state.a6=0x100000;put(ram,0x26,4,0x50000);put(ram,0x2a,2,0);ram[0x17]=0;
    data_failure(ram,script(bytes),windows,state);
    state=initial();state.a6=0x108000;ram=control_ram();bytes.assign(8,0);bytes[0]=0x14;bytes[1]=0x1d;put(bytes,2,4,0x106000);put(ram,0x6000,4,0x12345678);ram[0x807c]=0;
    // Callback destination/bank/PVC effects roll back when the following opcode is missing.
    truncated=bytes;truncated.resize(6);data_failure(ram,script(truncated),windows,state);
    bad=windows;put(bad[0].data,0x4a574 - 0x4276c,4,0x2b3fa);data_failure(ram,script(bytes),bad,state);
    bytes[1]=0x1f;bad=windows;put(bad[0].data,0x4a57c - 0x4276c,4,0x2b3e8);data_failure(ram,script(bytes),bad,state);
    bytes[1]=0x1d;put(bytes,2,4,0x106001);data_failure(ram,script(bytes),windows,state);
    put(bytes,2,4,0xffffffff);data_failure(ram,script(bytes),windows,state);
    put(bytes,2,4,0x60000);data_failure(ram,script(bytes),windows,state);
    ms5::FixedDataResource partial;partial.source_cpu_address=partial.source_rom_offset=0x60000;partial.data.assign(3,0);bad=windows;bad.push_back(partial);data_failure(ram,script(bytes),bad,state);
    // Odd window base does not invalidate aligned reached table reads.
    bytes.assign(10,0);bytes[0]=0x0c;put(bytes,2,2,0);put(bytes,4,4,0x50008);
    windows[0].source_cpu_address=windows[0].source_rom_offset=0x4276b;windows[0].data.insert(windows[0].data.begin(),0x55);
    bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,script(bytes),windows,state,carry,ports,error));assert(!carry);
}
void early_and_waits() {
    std::vector<std::uint8_t> ram=fixture(0);ms5::AnimationExecutionState s=initial(),want=s;std::string error;
    // Null pointer does not reach the otherwise invalid A5+5742 span.
    s.a5=want.a5=0x10b000;put(ram,0x3010,2,0xffff);ram[0x2017]=0x7f;
    want.sprite.registers.a[0]=0x102026;want.sprite.registers.d[7]=0;
    bool carry=false;std::vector<ms5::VideoPortWrite> ports=old_ports();
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),s,carry,ports,error));
    assert(carry&&same(s,want)&&get(ram,0x3010)==0&&ram[0x2017]==0x7f);ports_are(ports,1);
    const unsigned int timers[]={0,0x7fff,0x8000,0xffff};
    for(unsigned int i=0;i<4;++i){
        ram=fixture();s=initial();want=s;put(ram,0x202a,2,timers[i]);ram[0x2017]=1;
        std::vector<std::uint8_t> bytes(2,0);std::vector<ms5::AnimationResource> scripts=script(bytes);
        want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=0x50002;
        want.sprite.registers.d[7]=0;want.sprite.registers.d[1]&=0xffffff00U;
        want.sprite.registers.d[6]&=0xffffff00U;
        if(i==1)want.sprite.registers.d[6]|=0x7f;
        assert(ms5::step_animation_execution(ram,scripts,s,carry,ports,error));
        assert(!carry&&same(s,want)&&ram[0x2017]==0&&ram[0xd742]==(i>=2?2:1));
        assert(get(ram,0x202a)==(i>=2?0:timers[i])&&get(ram,0x2026,4)==0x50000);ports_are(ports,2);
    }
    // Negative nonzero wait loops with live high-BYTE timer addition.
    ram=fixture();s=initial();put(ram,0x202a,2,0xffff);
    std::vector<std::uint8_t> bytes;bytes.push_back(0);bytes.push_back(1);bytes.push_back(8);bytes.push_back(0);
    bytes.resize(8);put(bytes,4,4,0x50000);
    assert(ms5::step_animation_execution(ram,script(bytes),s,carry,ports,error));
    assert(!carry&&get(ram,0x202a)==0xffff&&get(ram,0x2026,4)==0x50002&&ram[0xd742]==2);
    assert(s.sprite.registers.d[0]==0xabcd0100&&s.sprite.registers.d[6]==0x50002&&s.sprite.registers.d[5]==0x50000);
    // Terminal clears only the timer high BYTE; negative timer is retried.
    for(unsigned int timer=0;timer<2;++timer){ram=fixture();s=initial();put(ram,0x202a,2,timer?0x8001:0x0101);
        assert(ms5::step_animation_execution(ram,script(std::vector<std::uint8_t>(1,0x28)),s,carry,ports,error));
        assert(carry&&s.sprite.registers.d[7]==0xffffffffU&&get(ram,0x202a)==(timer?0:1));}
}
void ram_scripts_and_jumps() {
    std::vector<std::uint8_t> ram=fixture(0x103000);ms5::AnimationExecutionState s=initial();bool carry=true;
    std::vector<ms5::VideoPortWrite> ports;std::string error;
    // The jump writes its target into the object pointer, then executes those
    // current RAM bytes as00 duration10; an immutable host copy would differ.
    const unsigned char jump[]={8,0,0,0x10,0x20,0x26};
    for(unsigned int i=0;i<6;++i)ram[0x3000+i]=jump[i];
    ms5::AnimationResource fake;fake.source_cpu_address=fake.source_rom_offset=0x103000;fake.data.assign(6,0x28);
    std::vector<ms5::AnimationResource> scripts(1,fake);
    assert(ms5::step_animation_execution(ram,scripts,s,carry,ports,error));
    assert(!carry&&get(ram,0x2026,4)==0x102026&&get(ram,0x202a)==0xf00&&s.sprite.registers.d[1]==0xabcd1210&&s.sprite.registers.d[6]==0x102026);
    ram=fixture();s=initial();std::vector<std::uint8_t> bytes(6,0);bytes[0]=8;put(bytes,2,4,0x51000);
    scripts=script(bytes);std::vector<ms5::AnimationResource> target=script(std::vector<std::uint8_t>(2,0),0x51000);scripts.push_back(target[0]);
    assert(ms5::step_animation_execution(ram,scripts,s,carry,ports,error));assert(!carry&&get(ram,0x2026,4)==0x51000&&s.sprite.registers.a[1]==0x51002);
}
void draw_paths() {
    std::vector<std::uint8_t> bytes=draw();bytes.push_back(0);bytes.push_back(0);
    std::vector<ms5::AnimationResource> scripts=script(bytes);std::vector<std::uint8_t> ram=fixture();
    ms5::AnimationExecutionState s=initial();bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,scripts,s,carry,ports,error));
    assert(!carry&&s.phase==0&&!s.sprite.waiting&&s.sprite.registers.a[0]==0x102026&&s.sprite.registers.a[1]==0x5000a);
    assert(s.sprite.registers.d[0]==0xffffffc0U); // MOVEM.W sign-extends saved lowWORD after actual accepted sprite.
    assert(s.sprite.registers.d[1]==0x12344500&&s.sprite.registers.d[2]==0xabcd1200&&s.sprite.registers.d[3]==12);
    assert(s.sprite.registers.d[4]==0xabcd0002&&s.sprite.registers.d[5]==0x8123&&s.sprite.registers.d[6]==0&&s.sprite.registers.d[7]==0);
    assert(get(ram,0x7f40,4)==0x8123ffc0&&get(ram,0x7f44,4)==0x12344500);ports_are(ports,4);
    // Sentinel skip reads all operands but never reaches object+20/+61.
    ram=fixture();s=initial();s.a6=0x10ffd0;put(ram,0xfff6,4,0x50000);put(ram,0xfffa,2,0);
    bytes=draw(0x12,0x34,0x56,0x7ff800);bytes.push_back(0);bytes.push_back(0);
    assert(ms5::step_animation_execution(ram,script(bytes),s,carry,ports,error));
    assert(s.sprite.registers.d[0]==0x34&&s.sprite.registers.d[5]==0x12&&s.sprite.registers.d[6]==0&&s.sprite.registers.d[2]==0xabcd1202);ports_are(ports,2);
    // Flash skip supports checked noncanonical A5 and preserves draw scratch.
    ram=fixture();s=initial();s.a5=0x108002;ram[0x2061]=8;ram[0x11]=1;
    bytes=draw(0x12,0x34,0x56);bytes.push_back(0);bytes.push_back(0);
    assert(ms5::step_animation_execution(ram,script(bytes),s,carry,ports,error));
    assert(s.sprite.registers.d[0]==0x34&&s.sprite.registers.d[5]==0x12&&s.sprite.registers.d[6]==0&&s.a5==0x108002);ports_are(ports,2);
    // Negative timer skips draw once, then terminal restarts and reaches draw.
    ram=fixture();s=initial();put(ram,0x202a,2,0x8000);bytes=draw();bytes.push_back(0x28);
    assert(ms5::step_animation_execution(ram,script(bytes),s,carry,ports,error));assert(carry&&get(ram,0x8d3a)==2);
}
ms5::AnimationExecutionState begin_wait(std::vector<std::uint8_t>& ram,const std::vector<ms5::AnimationResource>& scripts,bool deferred) {
    ram=fixture();put(ram,0x8d34,2,2);put(ram,0x8d36,2,4);if(deferred)put(ram,0x2012,4,0x12340040);
    ms5::AnimationExecutionState s=initial();bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,scripts,s,carry,ports,error));
    assert(carry&&s.phase==1&&s.sprite.waiting&&s.saved_a0==0x102026&&s.saved_a1==0x50008&&s.saved_bank==0);
    ports_are(ports,2);return s;
}
void pending() {
    std::vector<std::uint8_t> bytes=draw();append(bytes,draw());bytes.push_back(0);bytes.push_back(0);
    const std::vector<ms5::AnimationResource> scripts=script(bytes);
    for(unsigned int deferred=0;deferred<2;++deferred){
        std::vector<std::uint8_t> ram;ms5::AnimationExecutionState s=begin_wait(ram,scripts,deferred!=0),captured=s;
        put(ram,0x10,2,0xbeef);put(ram,0x2042,2,0x8000);put(ram,0x2046,2,0);ram[0x2053]=0xfc;put(ram,0x2020,2,0x1234);
        const std::vector<std::uint8_t> held=ram;bool carry=false;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),s,carry,ports,error));
        assert(!carry&&same(s,captured)&&ram==held&&ports.empty());
        ms5::AnimationExecutionState bad=s;bad.a5=0x108002;failure(ram,scripts,bad);
        put(ram,0x8d34,2,4);failure(ram,std::vector<ms5::AnimationResource>(),s); // Callee writes and restore ports roll back before missing next opcode.
        bad=s;bad.sprite.registers.a[1]=0x110000;failure(ram,scripts,bad);
        assert(ms5::step_animation_execution(ram,scripts,s,carry,ports,error));
        assert(!carry&&s.phase==0&&!s.sprite.waiting&&s.saved_a0==0&&s.saved_a1==0&&s.saved_bank==0&&get(ram,0x10)==0);
        assert(get(ram,0x8d3a)==2&&get(ram,0x7f40,4)==0x8123ffc0); // Current draw uses original coordinates.
        assert(s.sprite.registers.d[2]==0xabcd123f); // Later draw legitimately read changed object+53.
        assert(get(ram,0x914e)==(deferred?2:0));ports_are(ports,4);
    }
}
void errors() {
    std::vector<std::uint8_t> bytes=draw();bytes.push_back(0);bytes.push_back(0);std::vector<ms5::AnimationResource> scripts=script(bytes);
    std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState s=initial();
    put(ram,0x8b36,2,1);failure(ram,scripts,s); // Late sprite error restores entry/draw bank writes and ports.
    ram=fixture();put(ram,0x9152,4,0);failure(ram,scripts,s);
    ram=fixture();s.a5=0x108002;failure(ram,scripts,s);
    s=initial();s.a6=0x102001;failure(ram,scripts,s);s.a6=0xffffffff;failure(ram,scripts,s);
    s=initial();failure(ram,std::vector<ms5::AnimationResource>(),s);
    std::vector<ms5::AnimationResource> bad=scripts;bad.push_back(scripts[0]);failure(ram,bad,s);
    bad=scripts;bad[0].data.resize(7);failure(ram,bad,s); // packed LONG is incomplete after preceding operand reads.
    bad=scripts;ms5::AnimationResource overlap;overlap.source_cpu_address=overlap.source_rom_offset=0x50005;overlap.data.push_back(0);bad.push_back(overlap);failure(ram,bad,s);
    bad=scripts;bad[0].source_rom_offset++;failure(ram,bad,s);
    // Odd window base accepted when actual packed LONG remains aligned.
    scripts[0].source_cpu_address=scripts[0].source_rom_offset=0x4ffff;scripts[0].data.insert(scripts[0].data.begin(),0x55);
    bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,scripts,s,carry,ports,error));
    ram=fixture(0x50001);failure(ram,script(bytes,0x50001),initial());
    const unsigned int unsupported_or_missing_data[]={0x0c,0x10,0x14,0x18,0x1c,0x20,0x24,0x2c,0x30,0x34,0x38,0x3c,0x40,1,0x44};
    ram=fixture();for(unsigned int i=0;i<15;++i)failure(ram,script(std::vector<std::uint8_t>(1,unsupported_or_missing_data[i])),initial());
    bytes.assign(6,0);bytes[0]=8;put(bytes,2,4,0x50000);failure(ram,script(bytes),initial()); // cap is an error, never an empty success.
    s=initial();s.phase=2;failure(ram,script(bytes),s);s=initial();s.saved_a0=1;failure(ram,script(bytes),s);
    s=initial();s.saved_a1=1;failure(ram,script(bytes),s);s=initial();s.saved_bank=1;failure(ram,script(bytes),s);
    s=initial();s.sprite.waiting=true;failure(ram,script(bytes),s);s=initial();s.phase=1;failure(ram,script(bytes),s);
    ram.resize(65535);failure(ram,script(bytes),initial());
}
std::vector<ms5::FixedDataResource> sound_data() {
    std::vector<ms5::FixedDataResource> windows=control_data();
    put(windows[0].data,0x4a57c-0x4276c,4,0x47672);
    for(unsigned int i=0;i<128;++i)put(windows[0].data,0x4411e - 0x4276c+i*2,2,i?0x1234+i:0);
    return windows;
}
std::vector<std::uint8_t> sound_script() {
    std::vector<std::uint8_t> bytes(8,0);bytes[0]=0x14;bytes[1]=0x1f;put(bytes,2,4,0x12345678);return bytes;
}
void sound_failure(std::vector<std::uint8_t> ram,const std::vector<ms5::AnimationResource>& scripts,
    const std::vector<ms5::FixedDataResource>& windows,ms5::AnimationExecutionState state) {
    const std::vector<std::uint8_t> before=ram;const ms5::AnimationExecutionState saved=state;
    for(unsigned int input=0;input<2;++input) {
        bool carry=input!=0;std::uint32_t reads=0x12345678;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(!ms5::step_animation_execution(ram,scripts,windows,state,255,reads,carry,ports,error));
        assert(!error.empty()&&ram==before&&same(state,saved)&&carry==(input!=0)&&reads==0x12345678);
        assert(ports.size()==1&&ports[0].size==1&&ports[0].address==0x300001&&ports[0].value==0x55);
    }
}
ms5::AnimationExecutionState sound_wait(std::vector<std::uint8_t>& ram,unsigned int target) {
    ram=fixture(0x106000);const std::vector<std::uint8_t> bytes=sound_script();
    for(unsigned int i=0;i<bytes.size();++i)ram[0x6000+i]=bytes[i];
    put(ram,0x95c,2,0x5a01);ram[0x207e]=0;
    put(ram,0x4d8a,2,0);put(ram,0x4d8c,2,6);put(ram,0x4d74,2,target);put(ram,0x4d76,2,0);
    put(ram,0x4d82,2,0x0455);put(ram,0x4d84,2,0x0566);put(ram,0x4d86,2,0x0677);
    ms5::AnimationExecutionState state=initial();bool carry=true;std::uint32_t reads=77;
    std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),sound_data(),state,0,reads,carry,ports,error));
    assert(carry&&reads==0&&state.phase==2&&!state.sprite.waiting&&state.callback_waiting);
    assert(state.saved_a0==0x102026&&state.saved_a1==0x106006&&state.saved_bank==0);
    assert(state.callback_saved_a0==0x10095c&&state.callback_sound_phase==target&&state.callback_saved_low==0x55);
    ports_are(ports,2);return state;
}
void sound_callbacks() {
    const std::vector<ms5::FixedDataResource> windows=sound_data();
    const std::vector<ms5::AnimationResource> scripts=script(sound_script());
    for(unsigned int kind=0;kind<4;++kind) {
        std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial();
        put(ram,0x95c,2,0x5a01);ram[0x207e]=kind==1?0x5a:0;
        if(kind==2){ram[0x12]=1;ram[0xfd82]=1;}
        if(kind==3){state.a5=0x108002;put(ram,0x95e,2,0x5a01);ram[0x207e]=0x5a;}
        bool carry=true;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,scripts,windows,state,1,reads,carry,ports,error));
        assert(!carry&&state.phase==0&&state.callback_saved_a0==0&&state.callback_sound_phase==0&&
            state.callback_saved_low==0&&!state.callback_waiting&&!state.sprite.waiting);
        assert(reads==(kind==2?1U:0U)&&ram[0x2012]==0x34&&get(ram,0x2026,4)==0x50006);
        assert(state.sprite.registers.a[0]==0x102026&&state.sprite.registers.a[1]==0x50008);
        ms5::AnimationExecutionState want=initial();want.a5=state.a5;
        want.sprite.registers.d[0]=(kind==1||kind==3)?0x5aU:0x1ac0U;
        want.sprite.registers.d[1]=0xabcd1200U;want.sprite.registers.d[6]=0x50000;want.sprite.registers.d[7]=0;
        want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=0x50008;assert(same(state,want));
        ports_are(ports,4);
        if(kind==0)assert(get(ram,0x4d8c)==2&&get(ram,0x4d82)==0x1ac0);
        data_failure(fixture(),scripts,windows,initial()); // Previous overload must still reject reached1f.
    }
    // Two callbacks each conditionally sample external status. The first output
    // aliases the source BYTE, so the second comparison legitimately changes.
    std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial();state.a6=0x10094a;
    put(ram,0x970,4,0x50000);put(ram,0x974,2,0);put(ram,0x976,2,0x100);put(ram,0x95c,2,0x5a01);
    ram[0x9c8]=0;ram[0x12]=1;ram[0xfd82]=1;
    std::vector<std::uint8_t> bytes=sound_script();bytes.resize(6);append(bytes,sound_script());
    bool carry=true;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,script(bytes),windows,state,1,reads,carry,ports,error));
    assert(reads==2&&!carry&&ram[0x95c]==0x34&&ram[0x9c8]==0x34);ports_are(ports,6);
    // Callback output aliases the bank shadow; outer restoration wins afterward.
    ram=fixture();state=initial();state.a6=0xffffe;put(ram,0x24,4,0x50000);put(ram,0x28,2,0);
    put(ram,0x95c,2,0x5a01);ram[0x7c]=0;
    assert(ms5::step_animation_execution(ram,scripts,windows,state,0,reads,carry,ports,error));
    assert(get(ram,0x10)==0&&get(ram,0x24,4)==0x50006&&state.sprite.registers.a[0]==0x100024);ports_are(ports,4);
}
void sound_waits() {
    const std::vector<ms5::FixedDataResource> windows=sound_data();
    for(unsigned int target=1;target<=2;++target)for(unsigned int input=0;input<2;++input) {
        std::vector<std::uint8_t> ram;ms5::AnimationExecutionState state=sound_wait(ram,target);
        put(ram,0x95c,2,0x1234);ram[0x207e]=0x12;ram[0x4d7e]=1;put(ram,0x10,2,0xbeef);put(ram,0x6002,4,0xdeadbeef);
        const ms5::AnimationExecutionState captured=state;const std::vector<std::uint8_t> held=ram;
        bool carry=input!=0;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));
        assert(same(state,captured)&&ram==held&&reads==0&&ports.empty()&&carry==(input!=0));
        ms5::AnimationExecutionState bad=state;bad.a6=0xffffffff;
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad,0,reads,carry,ports,error));
        assert(bad.a6==0xffffffff&&bad.phase==2); // A6 is unreached while held.
        data_failure(ram,std::vector<ms5::AnimationResource>(),windows,state);
        failure(ram,std::vector<ms5::AnimationResource>(),state);
        put(ram,0x4d74,2,0xffff);
        sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state);
        bad=state;bad.saved_a0=0x110000;sound_failure(ram,std::vector<ms5::AnimationResource>(),windows,bad);
        bad=state;bad.saved_a1=0x110000;sound_failure(ram,std::vector<ms5::AnimationResource>(),windows,bad);
        bad=state;bad.callback_saved_a0=0x110000;sound_failure(ram,std::vector<ms5::AnimationResource>(),windows,bad);
        bad=state;bad.a5=0x108002;sound_failure(ram,std::vector<ms5::AnimationResource>(),windows,bad);
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),windows,state,255,reads,carry,ports,error));
        assert(!carry&&reads==0&&state.phase==0&&state.callback_saved_a0==0&&state.callback_sound_phase==0&&
            state.callback_saved_low==0&&!state.callback_waiting&&state.saved_a0==0&&state.saved_a1==0&&state.saved_bank==0);
        ms5::AnimationExecutionState want=initial();want.sprite.registers.d[0]=0x1a55;
        want.sprite.registers.d[1]=0xabcd1200U;want.sprite.registers.d[6]=0x106000;want.sprite.registers.d[7]=0;
        want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=0x106008;assert(same(state,want));
        assert(ram[0x2012]==0x67&&get(ram,0x10)==0&&get(ram,0x2026,4)==0x106006);ports_are(ports,2);
    }
    std::vector<std::uint8_t> ram;ms5::AnimationExecutionState state=sound_wait(ram,1);
    put(ram,0x4d74,2,2);bool carry=false;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));
    assert(!carry&&reads==0&&ports.empty()&&state.phase==2&&state.callback_sound_phase==2&&state.callback_saved_low==0x55);
    // Successful low-byte completion, outer restore and pointer store happen
    // before this missing fixed next-script fetch; all must roll back.
    state.saved_a1=0x50006;put(ram,0x4d74,2,0xffff);
    sound_failure(ram,std::vector<ms5::AnimationResource>(),windows,state);
    state.saved_a1=0x106006;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),windows,state,0,reads,carry,ports,error));
    assert(state.phase==0);
}
void sound_metadata() {
    const std::vector<ms5::FixedDataResource> windows=sound_data();const std::vector<ms5::AnimationResource> scripts=script(sound_script());
    std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState bad=initial();
    // External sampling occurs before the missing inner raw lookup. Its count
    // must roll back together with entry/callback writes and PVC output.
    put(ram,0x95c,2,0x5a01);ram[0x207e]=0;ram[0x12]=1;ram[0xfd82]=1;
    std::vector<ms5::FixedDataResource> dispatch(1);dispatch[0].source_cpu_address=dispatch[0].source_rom_offset=0x4a57c;
    dispatch[0].data.resize(4);put(dispatch[0].data,0,4,0x47672);sound_failure(ram,scripts,dispatch,bad);
    std::vector<ms5::FixedDataResource> wrong=windows;put(wrong[0].data,0x4a57c-0x4276c,4,0x47674);
    sound_failure(ram,scripts,wrong,bad);
    bad.callback_saved_a0=1;sound_failure(ram,scripts,windows,bad);
    bad=initial();bad.callback_sound_phase=1;sound_failure(ram,scripts,windows,bad);
    bad=initial();bad.callback_saved_low=1;sound_failure(ram,scripts,windows,bad);
    bad=initial();bad.callback_waiting=true;sound_failure(ram,scripts,windows,bad);
    bad=initial();bad.phase=1;bad.sprite.waiting=true;bad.callback_saved_low=1;sound_failure(ram,scripts,windows,bad);
    ms5::AnimationExecutionState state=sound_wait(ram,1);
    bad=state;bad.sprite.waiting=true;sound_failure(ram,scripts,windows,bad);
    bad=state;bad.callback_waiting=false;sound_failure(ram,scripts,windows,bad);
    bad=state;bad.callback_sound_phase=0;sound_failure(ram,scripts,windows,bad);
    bad=state;bad.callback_sound_phase=3;sound_failure(ram,scripts,windows,bad);
    bad=state;bad.phase=3;sound_failure(ram,scripts,windows,bad);
}

std::vector<ms5::FixedDataResource> indexed_data(unsigned int field=0x7d) {
    std::vector<ms5::FixedDataResource> windows=control_data();put(windows[0].data,0x4a7a8-0x4276c,2,field);return windows;
}
std::vector<std::uint8_t> indexed_script(unsigned int length=16) {
    std::vector<std::uint8_t> bytes(4);bytes[0]=0x10;bytes[1]=0x1e;put(bytes,2,2,length);
    append(bytes,draw(0,0,0,0x12345));append(bytes,draw(0x40,1,2,0x54321));bytes.push_back(0x28);return bytes;
}
void indexed_selection() {
    const unsigned int fields[]={0x7d,0xfffe,0x017d,0x8004,0x6000};
    const unsigned int indices[]={0,1,2,0xff};
    for(unsigned int f=0;f<5;++f)for(unsigned int i=0;i<4;++i) {
        // Use shifted object for signed field offsets, including high-byte
        // retention and WORD shift wrap. Length0 still reads that live field.
        std::vector<std::uint8_t> ram=control_ram();ms5::AnimationExecutionState state=initial(),want=state;
        state.a6=want.a6=0x108000;const unsigned int at=0x8000+signed_word(fields[f]);ram[at]=indices[i];
        std::vector<std::uint8_t> bytes(5);bytes[0]=0x10;bytes[1]=0x1e;bytes[4]=0x28;
        want.sprite.registers.d[0]=(((fields[f]&0xff00)|indices[i])<<3)&65535;
        want.sprite.registers.d[1]&=0xffff0000U;want.sprite.registers.d[7]=0xffffffffU;
        want.sprite.registers.a[0]=0x108026;want.sprite.registers.a[1]=0x50005;want.sprite.registers.a[2]=0x4a76c;
        bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,script(bytes),indexed_data(fields[f]),state,carry,ports,error));
        assert(carry&&same(state,want)&&get(ram,0x8026,4)==0x50000);ports_are(ports,2);
    }
    // Unsigned boundary skips the selected opcode entirely, even if invalid.
    for(unsigned int index=2;index<256;++index) {
        std::vector<std::uint8_t> ram=fixture();ram[0x207d]=index;ms5::AnimationExecutionState state=initial();
        std::vector<std::uint8_t> bytes=indexed_script();bytes[4]=0x7f;
        bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,script(bytes),indexed_data(),state,carry,ports,error));
        assert(carry&&state.sprite.registers.d[0]==index*8&&state.sprite.registers.d[6]==0xabcd1206U&&get(ram,0x2026,4)==0x50000);
    }
}
void indexed_draws() {
    for(unsigned int index=0;index<2;++index)for(unsigned int profile=0;profile<5;++profile) {
        std::vector<std::uint8_t> ram=fixture();ram[0x207d]=index;
        std::vector<std::uint8_t> bytes=indexed_script();
        if(profile==1)put(ram,0x2012,4,0x12340040);
        if(profile==2)put(ram,0x2042,2,0x8000);
        if(profile==3)put(bytes,4+index*8+4,4,0x7ff800);
        if(profile==4){ram[0x2061]=8;ram[0xf]=1;}
        std::vector<std::uint8_t> direct(bytes.begin()+4+index*8,bytes.begin()+12+index*8);direct.push_back(0x28);
        std::vector<std::uint8_t> reference=ram;ms5::AnimationExecutionState state=initial(),want=state;
        bool carry=false,want_carry=false;std::vector<ms5::VideoPortWrite> ports,expected;std::string error;
        assert(ms5::step_animation_execution(reference,script(direct),want,want_carry,expected,error));
        assert(ms5::step_animation_execution(ram,script(bytes),indexed_data(),state,carry,ports,error));
        want.sprite.registers.a[1]=0x50015;want.sprite.registers.a[2]=0x4a76c;
        if(profile==3||profile==4)want.sprite.registers.d[1]=(want.sprite.registers.d[1]&0xffff0000U)|16U;
        assert(carry&&want_carry&&same(state,want)&&ram==reference&&get(ram,0x2026,4)==0x50000);
        assert(ports.size()==expected.size());
        for(unsigned int n=0;n<ports.size();++n)assert(ports[n].size==expected[n].size&&ports[n].address==expected[n].address&&ports[n].value==expected[n].value);
    }
    // Declared length7 allows a complete8-byte record. Its last ID byte is
    // also the terminal00 byte, so no index+8<=length restriction is valid.
    std::vector<std::uint8_t> ram=fixture();ram[0x207d]=0;std::vector<std::uint8_t> bytes=indexed_script(7);
    bytes.resize(13);bytes[11]=bytes[12]=0;ms5::AnimationExecutionState state=initial();bool carry=true;
    std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,script(bytes),indexed_data(),state,carry,ports,error));
    assert(!carry&&state.sprite.registers.a[1]==0x5000d&&get(ram,0x2026,4)==0x50000);
    // Signed negative list end is separate from the unsigned comparison.
    ram=fixture(0x105800);ram[0x207d]=0;bytes=indexed_script(0xfff0);
    for(unsigned int i=0;i<bytes.size();++i)ram[0x5800+i]=bytes[i];ram[0x57f4]=0x28;state=initial();
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),indexed_data(),state,carry,ports,error));
    assert(carry&&state.sprite.registers.a[1]==0x1057f5&&get(ram,0x2026,4)==0x105800);
    // The selection comparison is unsigned, but the selected address is signed:
    // offset8000 < length8001 selects list_base-8000, not list_base+8000.
    ram=fixture(0x107ffc);put(ram,0x7ffc,1,0x10);put(ram,0x7ffd,1,0x1e);put(ram,0x7ffe,2,0x8001);
    std::vector<std::uint8_t> selected=draw(0,0,0,0x123450);for(unsigned int i=0;i<selected.size();++i)ram[i]=selected[i];
    ram[0x307d]=0;state=initial();
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),indexed_data(0x107d),state,carry,ports,error));
    assert(!carry&&state.sprite.registers.a[1]==0x100003&&get(ram,0x2026,4)==0x107ffc);
}
ms5::AnimationExecutionState indexed_wait(std::vector<std::uint8_t>& ram,bool deferred) {
    ram=fixture(0x105800);ram[0x207d]=0;put(ram,0x8d34,2,2);put(ram,0x8d36,2,4);
    if(deferred)put(ram,0x2012,4,0x12340040);
    const std::vector<std::uint8_t> bytes=indexed_script();for(unsigned int i=0;i<bytes.size();++i)ram[0x5800+i]=bytes[i];
    ms5::AnimationExecutionState state=initial();bool carry=true;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),indexed_data(),state,carry,ports,error));
    assert(carry&&state.phase==3&&state.sprite.waiting&&state.saved_list_end==0x105814&&state.saved_a1==0x10580c);
    assert(state.saved_a0==0x102026&&state.saved_bank==0);ports_are(ports,2);return state;
}
void indexed_waits() {
    for(unsigned int deferred=0;deferred<2;++deferred)for(unsigned int api=0;api<3;++api) {
        std::vector<std::uint8_t> ram;ms5::AnimationExecutionState state=indexed_wait(ram,deferred!=0);
        ram[0x207d]=255;ram[0x5800]=ram[0x5804]=0x7f;put(ram,0x5802,2,0xfff0);
        put(ram,0x2042,2,0x8000);put(ram,0x2046,2,0);ram[0x2053]=0xfc;put(ram,0x10,2,0xbeef);
        const std::vector<std::uint8_t> held=ram;const ms5::AnimationExecutionState captured=state;
        bool carry=api==1;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        if(api==0)assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),state,carry,ports,error));
        if(api==1)assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,carry,ports,error));
        if(api==2)assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));
        assert(ram==held&&same(state,captured)&&carry==(api==1)&&ports.empty());if(api==2)assert(reads==0);
        ms5::AnimationExecutionState bad=state;bad.a6=0xffffffff;
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),bad,carry,ports,error));assert(bad.a6==0xffffffff);
        ms5::AnimationExecutionState unused=captured;unused.a6=0xffffffff;assert(same(bad,unused));
        put(ram,0x8d34,2,4);bad=state;bad.saved_list_end=0x50000;
        failure(ram,std::vector<ms5::AnimationResource>(),bad);data_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
        sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
        bad=state;bad.sprite.registers.a[1]=0x110000;failure(ram,std::vector<ms5::AnimationResource>(),bad);
        bad=state;bad.a5=0x108002;failure(ram,std::vector<ms5::AnimationResource>(),bad);
        if(api==0)assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),state,carry,ports,error));
        if(api==1)assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,carry,ports,error));
        if(api==2)assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,0,reads,carry,ports,error));
        assert(carry&&state.phase==0&&!state.sprite.waiting&&state.saved_list_end==0&&state.saved_a0==0&&state.saved_a1==0);
        assert(state.sprite.registers.a[1]==0x105815&&state.sprite.registers.d[6]==2&&get(ram,0x2026,4)==0x105800);
        assert(get(ram,0x7f40,4)==0x8123ffc0&&get(ram,0x914e)==(deferred?2:0));ports_are(ports,2);if(api==2)assert(reads==0);
    }
}
void indexed_errors() {
    std::vector<std::uint8_t> ram=fixture();ram[0x207d]=0;ms5::AnimationExecutionState state=initial();
    std::vector<std::uint8_t> bytes=indexed_script();std::vector<ms5::FixedDataResource> windows=indexed_data();
    data_failure(ram,script(bytes),std::vector<ms5::FixedDataResource>(),state);
    std::vector<ms5::FixedDataResource> bad=windows;bad.push_back(windows[0]);data_failure(ram,script(bytes),bad,state);
    bytes[4]=0x7f;data_failure(ram,script(bytes),windows,state);bytes=indexed_script();bytes.resize(11);data_failure(ram,script(bytes),windows,state);
    bytes=indexed_script();put(ram,0x8b36,2,1);data_failure(ram,script(bytes),windows,state); // Late callee failure after PVC.
    ram=fixture();state.saved_list_end=1;data_failure(ram,script(bytes),windows,state);
    state=initial();state.phase=1;state.sprite.waiting=true;state.saved_list_end=1;data_failure(ram,script(bytes),windows,state);
    state=sound_wait(ram,1);state.saved_list_end=1;sound_failure(ram,script(bytes),windows,state);
    state=indexed_wait(ram,false);state.sprite.waiting=false;data_failure(ram,script(bytes),windows,state);
    state=indexed_wait(ram,false);state.callback_saved_low=1;data_failure(ram,script(bytes),windows,state);
    state=indexed_wait(ram,false);state.saved_list_end=0;bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),state,carry,ports,error)); // Zero cursor is not prevalidated while held.
    assert(state.phase==3&&state.saved_list_end==0&&!carry&&ports.empty());
}

std::vector<ms5::FixedDataResource> field_data(unsigned int selector,unsigned int offset) {
    std::vector<ms5::FixedDataResource> windows=control_data();
    const unsigned int at=static_cast<unsigned int>(0x4a76c+signed_word((selector*2)&65535));
    put(windows[0].data,at-0x4276c,2,offset);return windows;
}
void field_expected_ram(std::vector<std::uint8_t>& ram,unsigned int cursor) {
    put(ram,0x10,2,0);ram[0xd742]=0;ram[0x2017]=1;put(ram,0x2026,4,cursor);ram[0x202a]=0;
}
void field_writes() {
    const unsigned int selectors[]={0,1,0x90,0x4000,0x7fff,0x8000,0xffff};
    for(unsigned int i=0;i<7;++i) {
        std::vector<std::uint8_t> bytes(5);bytes[0]=0x18;bytes[1]=0x80;put(bytes,2,2,selectors[i]);bytes[4]=0x28;
        std::vector<std::uint8_t> ram=fixture(),expected=ram;expected[0x1ffe]=0x80;field_expected_ram(expected,0x50004);
        ms5::AnimationExecutionState state=initial(),want=state;
        want.sprite.registers.d[0]=0xabcd1280U;want.sprite.registers.d[1]=0xabcdfffeU;want.sprite.registers.d[6]=0x50004;want.sprite.registers.d[7]=0xffffffffU;
        want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=0x50005;want.sprite.registers.a[2]=0x4a76c;
        bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,script(bytes),field_data(selectors[i],0xfffe),state,carry,ports,error));
        assert(carry&&same(state,want)&&ram==expected);ports_are(ports,2);
    }
    const unsigned int opcodes[]={0x1c,0x20,0x24,0x34,0x38};
    for(unsigned int i=0;i<5;++i)for(unsigned int alias=0;alias<(i<2?2U:1U);++alias) {
        const unsigned int opcode=opcodes[i],size=opcode==0x20?4:2;
        const unsigned int offset=opcode==0x34?0x70:opcode==0x38?0x20:alias?0x26:0x78;
        std::vector<std::uint8_t> bytes(opcode==0x24?3:2+size+1);bytes[0]=opcode;bytes[1]=i>=3?0xfe:1;
        if(opcode!=0x24)put(bytes,2,size,opcode==0x20?0x81234567:0x8123);bytes.back()=0x28;
        const unsigned int cursor=0x50000+bytes.size()-1;
        std::vector<std::uint8_t> ram=fixture(),expected=ram;ram[0x2078]=expected[0x2078]=0;
        if(opcode==0x24)expected[0x2078]=255;else put(expected,0x2000+offset,size,opcode==0x20?0x81234567:0x8123);
        field_expected_ram(expected,cursor);ms5::AnimationExecutionState state=initial(),want=state;
        if(opcode!=0x38)want.sprite.registers.d[0]=opcode==0x34?0:offset;
        if(opcode==0x1c)want.sprite.registers.d[1]=0xabcd8123U;
        if(opcode==0x20)want.sprite.registers.d[1]=0x81234567;
        want.sprite.registers.d[6]=cursor;want.sprite.registers.d[7]=0xffffffffU;
        want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=cursor+1;if(i<3)want.sprite.registers.a[2]=0x4a76c;
        bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,script(bytes),field_data(1,offset),state,carry,ports,error));
        assert(carry&&same(state,want)&&ram==expected);ports_are(ports,2);
    }
    // Padding bytes34/38 are never fetched, so their MS5A span can be absent.
    for(unsigned int opcode=0x34;opcode<=0x38;opcode+=4) {
        std::vector<ms5::AnimationResource> scripts=script(std::vector<std::uint8_t>(1,opcode));
        std::vector<std::uint8_t> tail(3);put(tail,0,2,0x1234);tail[2]=0x28;
        scripts.push_back(script(tail,0x50002)[0]);
        std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial();bool carry=false;
        std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,scripts,state,carry,ports,error));
        assert(carry&&get(ram,opcode==0x34?0x2070:0x2020)==0x1234);
    }
    // A LONG field write modifies the next live RAM opcode; fetch sees28.
    std::vector<std::uint8_t> ram=fixture(0x105000);put(ram,0x5000,1,0x20);ram[0x5001]=1;put(ram,0x5002,4,0x28000000);
    ram[0x5006]=0x7f;ms5::AnimationExecutionState state=initial();bool carry=false;
    std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),field_data(1,0x3006),state,carry,ports,error));
    assert(carry&&ram[0x5006]==0x28&&get(ram,0x2026,4)==0x105006&&state.sprite.registers.d[6]==0x105006);
}
void relative_fields() {
    // length1 still reads a full selectedWORD. Zero selected displacement
    // lands on its low00 byte, which is also the following duration0 opcode.
    std::vector<std::uint8_t> bytes(7);bytes[0]=0x2c;bytes[1]=1;put(bytes,2,2,1);
    std::vector<std::uint8_t> ram=fixture();ram[0x207d]=0;ms5::AnimationExecutionState state=initial();bool carry=true;
    std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,script(bytes),field_data(1,0x7d),state,carry,ports,error));
    assert(!carry&&get(ram,0x2026,4)==0x50005&&state.sprite.registers.a[1]==0x50007);
    assert(state.sprite.registers.d[0]==0&&state.sprite.registers.d[2]==0xabcd0001U);
    // Skipped selection performs no selectedWORD fetch, preserving register
    // highWORDs and requiring only the final cursor's opcode.
    const unsigned int fields[]={0x7d,0x017d,0x8004};
    for(unsigned int i=0;i<3;++i) {
        ram=control_ram();state=initial();state.a6=0x108000;ram[0x8000+signed_word(fields[i])]=255;
        bytes.assign(5,0);bytes[0]=0x2c;bytes[1]=1;bytes[4]=0x28;
        assert(ms5::step_animation_execution(ram,script(bytes),field_data(1,fields[i]),state,carry,ports,error));
        assert(carry&&state.sprite.registers.d[0]==((((fields[i]&0xff00)|255)<<1)&65535));
        assert(state.sprite.registers.d[2]==0xabcd0000U&&state.sprite.registers.d[6]==0x50004&&get(ram,0x8026,4)==0x50004);
    }
    // Two sequential signed additions: selected-6 then length8 =>base+2.
    // Put terminal28 inside the list, distinct from base+length.
    ram=fixture();ram[0x207d]=0;bytes.assign(12,0);bytes[0]=0x2c;bytes[1]=1;put(bytes,2,2,8);put(bytes,4,2,0xfffa);bytes[6]=0x28;
    state=initial();assert(ms5::step_animation_execution(ram,script(bytes),field_data(1,0x7d),state,carry,ports,error));
    assert(carry&&get(ram,0x2026,4)==0x50006&&state.sprite.registers.a[1]==0x50007&&state.sprite.registers.d[0]==0);
    // Both selection and final length use signed addresses after an unsigned
    // comparison. offset8000 < length8001 reads a backwardWORD.
    ram=fixture(0x108000);put(ram,0x8000,1,0x2c);ram[0x8001]=1;put(ram,0x8002,2,0x8001);
    ram[0x607d]=0;put(ram,4,2,2);ram[7]=0x28;state=initial();
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),field_data(1,0x407d),state,carry,ports,error));
    assert(carry&&get(ram,0x2026,4)==0x100007&&state.sprite.registers.d[0]==0x8000&&state.sprite.registers.d[2]==0xabcd8001U);
}
void field_errors() {
    std::vector<std::uint8_t> bytes(7);bytes[0]=0x20;bytes[1]=1;put(bytes,2,4,0x12345678);bytes[6]=0x28;
    std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial();
    state.a6=0x108000;
    data_failure(control_ram(),script(bytes),field_data(1,0x7ffe),state); // Aligned LONG at10fffe crosses RAM end after full operand fetch.
    state=initial();
    data_failure(ram,script(bytes),field_data(1,0x7d),state); // Odd LONG target.
    std::vector<ms5::AnimationResource> short_script=script(bytes);short_script[0].data.resize(5);
    data_failure(ram,short_script,field_data(1,0x78),state);
    bytes.resize(6);data_failure(ram,script(bytes),field_data(1,0x78),state); // Field write and pointer store precede missing next fetch.
    bytes.assign(4,0);bytes[0]=0x2c;bytes[1]=1;put(bytes,2,2,1);ram[0x207d]=0;
    data_failure(ram,script(bytes),field_data(1,0x7d),state); // Actually reached selectedWORD absent.
    bytes.assign(5,0);bytes[0]=0x2c;bytes[1]=1;bytes[4]=0x28;
    data_failure(ram,script(bytes),field_data(1,0x8004),state); // length0 must still reach below-RAM field.
    std::vector<ms5::FixedDataResource> duplicate=field_data(1,0x78);duplicate.push_back(duplicate[0]);
    bytes.assign(3,0);bytes[0]=0x24;bytes[1]=1;bytes[2]=0x28;data_failure(ram,script(bytes),duplicate,state);
}

std::vector<std::uint8_t> direct_sound_script(unsigned int command=0x1ac0) {
    std::vector<std::uint8_t> bytes(5);bytes[0]=0x30;bytes[1]=0xff;put(bytes,2,2,command);bytes[4]=0x28;return bytes;
}
void direct_sound_calls() {
    const unsigned int commands[]={0,3,0x20,0x120,0x1ac0,0x8001};
    for(unsigned int i=0;i<6;++i) {
        std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial(),want=state;
        const std::vector<ms5::AnimationResource> scripts=script(direct_sound_script(commands[i]));
        want.sprite.registers.d[0]=commands[i];
        if(commands[i]==0x120)want.sprite.registers.d[1]=0xabcd0100U;
        if(commands[i]==0x20||commands[i]==0x1ac0)want.sprite.registers.d[1]=0xabcd0002U;
        want.sprite.registers.d[6]=0x50004;want.sprite.registers.d[7]=0xffffffffU;
        want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=0x50005;
        bool carry=false;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,scripts,std::vector<ms5::FixedDataResource>(),state,0,reads,carry,ports,error));
        assert(carry&&reads==0&&same(state,want)&&get(ram,0x2026,4)==0x50004);ports_are(ports,2);
        failure(fixture(),scripts,initial());data_failure(fixture(),scripts,std::vector<ms5::FixedDataResource>(),initial());
    }
    // Missing padding MS5A bytes do not prevent the actual WORD fetch.
    std::vector<ms5::AnimationResource> scripts=script(std::vector<std::uint8_t>(1,0x30));
    std::vector<std::uint8_t> tail(3);put(tail,0,2,0x8001);tail[2]=0x28;scripts.push_back(script(tail,0x50002)[0]);
    std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial();bool carry=false;std::uint32_t reads=77;
    std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,scripts,std::vector<ms5::FixedDataResource>(),state,0,reads,carry,ports,error));
    assert(carry&&state.sprite.registers.d[0]==0x8001&&reads==0); // No MOVEM.W signextension.
    // Two direct commands and one1f callback each sample external status.
    std::vector<std::uint8_t> bytes=direct_sound_script();bytes.resize(4);append(bytes,direct_sound_script());bytes.resize(8);append(bytes,sound_script());
    ram=fixture();ram[0x12]=1;ram[0xfd82]=1;put(ram,0x95c,2,0x5a01);ram[0x207e]=0;state=initial();
    assert(ms5::step_animation_execution(ram,script(bytes),sound_data(),state,1,reads,carry,ports,error));
    assert(reads==3&&!carry&&get(ram,0x4d8c)==0);
    // Allthree reads and preceding command effects roll back on missing nextfetch.
    bytes.resize(14);sound_failure(fixture(),script(bytes),sound_data(),initial());
    std::vector<std::uint8_t> sampled=fixture();sampled[0x12]=1;sampled[0xfd82]=1;put(sampled,0x95c,2,0x5a01);sampled[0x207e]=0;
    sound_failure(sampled,script(bytes),sound_data(),initial());
}
ms5::AnimationExecutionState direct_wait(std::vector<std::uint8_t>& ram,unsigned int target) {
    ram=fixture(0x106000);const std::vector<std::uint8_t> bytes=direct_sound_script();
    for(unsigned int i=0;i<bytes.size();++i)ram[0x6000+i]=bytes[i];
    put(ram,0x4d8a,2,0);put(ram,0x4d8c,2,6);put(ram,0x4d74,2,target);put(ram,0x4d76,2,0);
    put(ram,0x4d82,2,0x0455);put(ram,0x4d84,2,0x0566);put(ram,0x4d86,2,0x0677);
    ms5::AnimationExecutionState state=initial();bool carry=true;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,0,reads,carry,ports,error));
    assert(carry&&reads==0&&state.phase==4&&!state.sprite.waiting&&state.callback_waiting&&state.callback_sound_phase==target);
    assert(state.saved_a0==0x102026&&state.saved_a1==0x106004&&state.saved_bank==0&&state.saved_list_end==0&&state.callback_saved_a0==0&&state.callback_saved_low==0x55);
    assert(state.sprite.registers.d[7]==0x30);ports_are(ports,1);return state;
}
void direct_sound_waits() {
    for(unsigned int target=1;target<=2;++target)for(unsigned int input=0;input<2;++input) {
        std::vector<std::uint8_t> ram;ms5::AnimationExecutionState state=direct_wait(ram,target);
        put(ram,0x6002,2,0xffff);ram[0x4d7e]=1;ram[0x12]=1;ram[0xfd82]=1;put(ram,0x10,2,0xbeef);
        const std::vector<std::uint8_t> held=ram;const ms5::AnimationExecutionState captured=state;
        bool carry=input!=0;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports=old_ports();std::string error;
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));
        assert(same(state,captured)&&ram==held&&reads==0&&ports.empty()&&carry==(input!=0));
        ms5::AnimationExecutionState unused=state;unused.a6=0xffffffff;unused.saved_a0=0xffffffff;unused.saved_a1=0;
        const ms5::AnimationExecutionState untouched=unused;
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),unused,0,reads,carry,ports,error));
        assert(same(unused,untouched)&&ram==held&&ports.empty()&&reads==0&&carry==(input!=0));
        failure(ram,std::vector<ms5::AnimationResource>(),state);data_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state);
        put(ram,0x4d74,2,0xffff);
        ms5::AnimationExecutionState bad=state;bad.saved_a0=0x110000;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
        bad=state;bad.saved_a1=0x50000;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
        bad=state;bad.a5=0x108002;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));
        assert(carry&&reads==0&&state.phase==0&&state.saved_a0==0&&state.saved_a1==0&&!state.callback_waiting&&state.callback_sound_phase==0&&state.callback_saved_low==0);
        assert(state.sprite.registers.d[0]==0x1a55&&state.sprite.registers.d[6]==0x106004&&state.sprite.registers.a[0]==0x102026&&state.sprite.registers.a[1]==0x106005);
        assert(get(ram,0x2026,4)==0x106004&&get(ram,0x10)==0);ports_are(ports,1); // Only normal terminal epilogue writes PVC.
    }
    std::vector<std::uint8_t> ram;ms5::AnimationExecutionState state=direct_wait(ram,1);
    put(ram,0x4d74,2,2);bool carry=false;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));
    assert(!carry&&state.phase==4&&state.callback_sound_phase==2&&state.callback_saved_low==0x55&&ports.empty()&&reads==0);
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));assert(state.phase==4&&ports.empty());
    put(ram,0x4d74,2,0xffff);
    assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));assert(state.phase==0);
}
void direct_sound_metadata() {
    std::vector<std::uint8_t> ram;ms5::AnimationExecutionState state=direct_wait(ram,1),bad=state;
    bad.saved_bank=1;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
    bad=state;bad.saved_list_end=1;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
    bad=state;bad.callback_saved_a0=1;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
    bad=state;bad.callback_sound_phase=0;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
    bad=state;bad.callback_sound_phase=3;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
    bad=state;bad.callback_waiting=false;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
    bad=state;bad.sprite.waiting=true;sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),bad);
    ram=fixture();bad=initial();bad.a5=0x108002;sound_failure(ram,script(direct_sound_script(0x8001)),std::vector<ms5::FixedDataResource>(),bad);
    std::vector<ms5::AnimationResource> short_script=script(direct_sound_script());short_script[0].data.resize(3);
    sound_failure(ram,short_script,std::vector<ms5::FixedDataResource>(),initial());
}

std::vector<std::uint8_t> word_callback_script(unsigned int selector,unsigned int lookup=0,std::uint32_t operand=0x106000) {
    std::vector<std::uint8_t> bytes(11);bytes[0]=0x3c;bytes[1]=0xff;put(bytes,2,2,selector);put(bytes,4,2,lookup);put(bytes,6,4,operand);bytes[10]=0x28;return bytes;
}
std::vector<ms5::FixedDataResource> word_callback_data(unsigned int selector,unsigned int lookup,std::uint32_t target,unsigned int value) {
    // Supply only the two actually reached lookup spans. First WORDselector
    // wraps at4x; the second wraps at2x. No ROM payload is embedded here.
    std::vector<ms5::FixedDataResource> windows(2);
    windows[0].source_cpu_address=windows[0].source_rom_offset=static_cast<unsigned int>(0x4a500+signed_word((selector*4)&65535));
    windows[0].data.resize(4);put(windows[0].data,0,4,target);
    windows[1].source_cpu_address=windows[1].source_rom_offset=static_cast<unsigned int>(0x4a76c+signed_word((lookup*2)&65535));
    windows[1].data.resize(2);put(windows[1].data,0,2,value);return windows;
}
void word_callbacks() {
    const unsigned int selectors[]={0,0x1d,0x401d,0x801d,0xc01d,0x1fff,0x2000,0x3fff,0xffff};
    const unsigned int lookups[]={0,0x3fff,0x4000,0x7fff,0x8000,0xffff};
    for(unsigned int s=0;s<9;++s)for(unsigned int k=0;k<6;++k)for(unsigned int callee=0;callee<2;++callee) {
        const unsigned int index=(s+k)%3==0?255:(s+k)%3==1?1:0;
        const unsigned int value=k%3==0?0:k%3==1?0x8001:0xffff;
        const unsigned int target=callee?0x2b3fa:0x2b3e8;
        std::vector<std::uint8_t> ram=fixture();ram[0x207c+callee]=index;put(ram,0x6000+index*4,4,0x81234567);
        std::vector<std::uint8_t> expected=ram;put(expected,0x2078,4,0x81234567);field_expected_ram(expected,0x5000a);
        ms5::AnimationExecutionState state=initial(),want=state;
        want.sprite.registers.d[0]=index*4;want.sprite.registers.d[1]=0xabcd0000U|value;
        want.sprite.registers.d[6]=0x5000a;want.sprite.registers.d[7]=0xffffffffU;
        want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=0x5000b;
        bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,script(word_callback_script(selectors[s],lookups[k])),word_callback_data(selectors[s],lookups[k],target,value),state,carry,ports,error));
        assert(carry&&same(state,want)&&ram==expected);
        assert(state.sprite.registers.a[2]==0x76540002U); // Original3c LEAs both useA0; initial nonzeroA2 survives.
        ports_are(ports,4);
    }
    // Missing padding is allowed: onlyopcode, WORDselectors andLONGoperand
    // are provided. The callback reads a live operand that aliases its output.
    std::vector<std::uint8_t> bytes=word_callback_script(0x801d,0xffff,0x102074);
    std::vector<ms5::AnimationResource> scripts=script(std::vector<std::uint8_t>(1,0x3c));
    scripts.push_back(script(std::vector<std::uint8_t>(bytes.begin()+2,bytes.end()),0x50002)[0]);
    std::vector<std::uint8_t> ram=fixture();ram[0x207c]=1;put(ram,0x2078,4,0xdeadbeef);ms5::AnimationExecutionState state=initial();
    bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,scripts,word_callback_data(0x801d,0xffff,0x2b3e8,0x9234),state,carry,ports,error));
    assert(carry&&get(ram,0x2078,4)==0xdeadbeef&&state.sprite.registers.d[1]==0xabcd9234U);
    // Live fixed operand windows are also consumed at the original address.
    std::vector<ms5::FixedDataResource> windows=word_callback_data(0x2000,0,0x2b3fa,0x55aa);
    ms5::FixedDataResource operand;operand.source_cpu_address=operand.source_rom_offset=0x60000;operand.data.resize(4);put(operand.data,0,4,0xfedcba98);windows.push_back(operand);
    ram=fixture();ram[0x207d]=0;state=initial();
    assert(ms5::step_animation_execution(ram,script(word_callback_script(0x2000,0,0x60000)),windows,state,carry,ports,error));
    assert(carry&&get(ram,0x2078,4)==0xfedcba98&&state.sprite.registers.d[1]==0xabcd55aaU);
}
std::vector<ms5::FixedDataResource> word_sound_data() {
    std::vector<ms5::FixedDataResource> windows=word_callback_data(0x401f,0xffff,0x47672,0x9234);
    ms5::FixedDataResource raw;raw.source_cpu_address=raw.source_rom_offset=0x4411e;raw.data.resize(256);
    for(unsigned int i=0;i<128;++i)put(raw.data,i*2,2,i?0x1234+i:0);windows.push_back(raw);return windows;
}
void word_callback_sound() {
    const std::vector<ms5::FixedDataResource> windows=word_sound_data();
    for(unsigned int target=1;target<=2;++target) {
        std::vector<std::uint8_t> ram=fixture(0x106000);std::vector<std::uint8_t> bytes=word_callback_script(0x401f,0xffff,0x92348000);
        for(unsigned int i=0;i<bytes.size();++i)ram[0x6000+i]=bytes[i];
        put(ram,0x95c,2,0x5a01);ram[0x207e]=0;put(ram,0x4d8c,2,6);put(ram,0x4d74,2,target);
        put(ram,0x4d82,2,0x0455);put(ram,0x4d84,2,0x0566);put(ram,0x4d86,2,0x0677);
        ms5::AnimationExecutionState state=initial();bool carry=target==1;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),windows,state,0,reads,carry,ports,error));
        assert(state.phase==2&&state.saved_a1==0x10600a&&state.callback_saved_a0==0x10095c&&state.callback_saved_low==0x55&&reads==0);
        assert(state.sprite.registers.a[2]==0x76540002U);
        assert((state.sprite.registers.d[0]&0xffff0000U)==0x92340000U); // Full operand→D0 before inner lowWORD command.
        put(ram,0x6002,2,0xffff);put(ram,0x6004,2,0x4000);put(ram,0x6006,4,0xdeadbeef);put(ram,0x95c,2,0x1234);ram[0x4d7e]=1;
        const ms5::AnimationExecutionState captured=state;const std::vector<std::uint8_t> held=ram;
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));
        assert(same(state,captured)&&ram==held&&ports.empty()&&reads==0&&carry==(target==1));
        failure(ram,std::vector<ms5::AnimationResource>(),state);
        if(target==1) {
            put(ram,0x4d74,2,2);
            assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state,255,reads,carry,ports,error));
            assert(state.phase==2&&state.callback_sound_phase==2&&state.callback_saved_low==0x55&&state.saved_a1==0x10600a&&ports.empty()&&reads==0);
        }
        put(ram,0x4d74,2,0xffff);sound_failure(ram,std::vector<ms5::AnimationResource>(),std::vector<ms5::FixedDataResource>(),state);
        assert(ms5::step_animation_execution(ram,std::vector<ms5::AnimationResource>(),windows,state,255,reads,carry,ports,error));
        assert(carry&&reads==0&&state.phase==0&&state.sprite.registers.d[0]==0x1a55&&state.sprite.registers.a[1]==0x10600b);ports_are(ports,2);
    }
    // No-sound47672 retains full operand highWORD until signedWORD restore.
    std::vector<std::uint8_t> ram=fixture();put(ram,0x95c,2,0x8001);ram[0x207e]=0x80;ms5::AnimationExecutionState state=initial();
    bool carry=false;std::uint32_t reads=77;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,script(word_callback_script(0x401f,0xffff,0x9234ff00)),windows,state,0,reads,carry,ports,error));
    assert(carry&&state.sprite.registers.d[0]==0xffffff80U&&reads==0);
    data_failure(fixture(),script(word_callback_script(0x401f,0xffff)),windows,initial());
}
void word_callback_errors() {
    std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial();
    std::vector<ms5::AnimationResource> scripts=script(word_callback_script(0x2000,0xffff));
    std::vector<ms5::FixedDataResource> windows=word_callback_data(0x2000,0xffff,0x2b3e8,0x8001);
    data_failure(ram,scripts,std::vector<ms5::FixedDataResource>(),state);
    std::vector<ms5::FixedDataResource> bad=windows;bad.erase(bad.begin()+1);data_failure(ram,scripts,bad,state);
    bad=windows;bad[0].data.resize(3);data_failure(ram,scripts,bad,state);
    bad=windows;bad[1].data.resize(1);data_failure(ram,scripts,bad,state);
    bad=windows;bad.push_back(windows[0]);data_failure(ram,scripts,bad,state);
    bad=windows;put(bad[0].data,0,4,0x2b3e9);data_failure(ram,scripts,bad,state);
    std::vector<ms5::AnimationResource> short_script=scripts;short_script[0].data.resize(9);data_failure(ram,short_script,windows,state);
    short_script=scripts;short_script[0].data.resize(10);data_failure(ram,short_script,windows,state); // Callback RAMwrite/PVC complete before missing nextfetch.
    ram[0x207c]=0;put(ram,0x2026,4,0x50001);data_failure(ram,script(word_callback_script(0x2000,0xffff),0x50001),windows,state);
    // Even when sound would overwriteD1, the second lookup is mandatory.
    ram=fixture();put(ram,0x95c,2,0x5a01);ram[0x207e]=0;bad=word_sound_data();bad.erase(bad.begin()+1);
    sound_failure(ram,script(word_callback_script(0x401f,0xffff)),bad,state);
    // Existing14 still rejects arbitraryselector aliases of a supportedtarget.
    std::vector<std::uint8_t> old(7);old[0]=0x14;old[1]=0;put(old,2,4,0x106000);old[6]=0x28;
    data_failure(ram,script(old),word_callback_data(0,0,0x2b3e8,0),state);
}

void word_callback_rts() {
    const unsigned int selectors[]={3,0x4003,0x8003,0xc003,0x2000};
    const std::uint32_t operands[]={0,0x92340001U,0x12347fffU,0xabcd8000U,0x9234ffffU};
    for(unsigned int i=0;i<5;++i) {
        std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial(),want=state;
        const unsigned int value=i*0x1234;std::vector<ms5::FixedDataResource> windows=word_callback_data(selectors[i],0xffff,0x3679e,value);
        const unsigned int low=operands[i]&65535;
        want.sprite.registers.d[0]=low<0x8000?low:low|0xffff0000U;want.sprite.registers.d[1]=0xabcd0000U|value;
        want.sprite.registers.d[6]=0x5000a;want.sprite.registers.d[7]=0xffffffffU;
        want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=0x5000b;
        bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
        assert(ms5::step_animation_execution(ram,script(word_callback_script(selectors[i],0xffff,operands[i])),windows,state,carry,ports,error));
        assert(carry&&same(state,want)&&get(ram,0x2026,4)==0x5000a);
        assert(state.sprite.registers.a[2]==0x76540002U);ports_are(ports,4);
    }
    // Actual14 selector03 uses the same real RTS target but has no second
    // lookup and does not MOVE.L operand intoD0. Only its reachedLONG is needed.
    std::vector<std::uint8_t> bytes(7);bytes[0]=0x14;bytes[1]=3;put(bytes,2,4,0xffffffff);bytes[6]=0x28;
    std::vector<ms5::FixedDataResource> windows=word_callback_data(3,0,0x3679e,0);windows.resize(1);
    std::vector<std::uint8_t> ram=fixture();ms5::AnimationExecutionState state=initial(),want=state;
    want.sprite.registers.d[0]=12;want.sprite.registers.d[6]=0x50006;want.sprite.registers.d[7]=0xffffffffU;
    want.sprite.registers.a[0]=0x102026;want.sprite.registers.a[1]=0x50007;
    bool carry=false;std::vector<ms5::VideoPortWrite> ports;std::string error;
    assert(ms5::step_animation_execution(ram,script(bytes),windows,state,carry,ports,error));assert(carry&&same(state,want));ports_are(ports,4);
    bytes[1]=4;data_failure(fixture(),script(bytes),word_callback_data(4,0,0x3679e,0),initial()); //14alias remains unsupported.
    bytes=word_callback_script(3);windows=word_callback_data(3,0,0x3679f,0);data_failure(fixture(),script(bytes),windows,initial()); // Nearbytarget is not the verifiedRTS.
}

}
int main(){early_and_waits();ram_scripts_and_jumps();draw_paths();pending();errors();field_branches();control_callbacks();control_errors();sound_callbacks();sound_waits();sound_metadata();indexed_selection();indexed_draws();indexed_waits();indexed_errors();field_writes();relative_fields();field_errors();direct_sound_calls();direct_sound_waits();direct_sound_metadata();word_callbacks();word_callback_sound();word_callback_errors();word_callback_rts();std::cout<<"animation_execution_test passed\n";return 0;}
