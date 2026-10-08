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
        a.saved_a1==b.saved_a1 && a.saved_bank==b.saved_bank && a.sprite.waiting==b.sprite.waiting;
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
    const unsigned int unsupported[]={0x0c,0x10,0x14,0x18,0x1c,0x20,0x24,0x2c,0x30,0x34,0x38,0x3c,0x40,1,0x44};
    ram=fixture();for(unsigned int i=0;i<15;++i)failure(ram,script(std::vector<std::uint8_t>(1,unsupported[i])),initial());
    bytes.assign(6,0);bytes[0]=8;put(bytes,2,4,0x50000);failure(ram,script(bytes),initial()); // cap is an error, never an empty success.
    s=initial();s.phase=2;failure(ram,script(bytes),s);s=initial();s.saved_a0=1;failure(ram,script(bytes),s);
    s=initial();s.saved_a1=1;failure(ram,script(bytes),s);s=initial();s.saved_bank=1;failure(ram,script(bytes),s);
    s=initial();s.sprite.waiting=true;failure(ram,script(bytes),s);s=initial();s.phase=1;failure(ram,script(bytes),s);
    ram.resize(65535);failure(ram,script(bytes),initial());
}
}
int main(){early_and_waits();ram_scripts_and_jumps();draw_paths();pending();errors();field_branches();control_callbacks();control_errors();std::cout<<"animation_execution_test passed\n";return 0;}
