#include "ms5/object_sprite_wrapper.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& ram, unsigned int at, std::uint32_t value, unsigned int size = 2) {
    assert(at <= ram.size() && size <= ram.size()-at);
    for (unsigned int i=0;i<size;++i) ram[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
}
std::uint32_t get(const std::vector<std::uint8_t>& ram, unsigned int at, unsigned int size=4) {
    assert(at <= ram.size() && size <= ram.size()-at); std::uint32_t result=0;
    for (unsigned int i=0;i<size;++i) result=(result<<8)|ram[at+i]; return result;
}
ms5::ObjectSpriteWrapperState initial() {
    ms5::ObjectSpriteWrapperState s;
    for (unsigned int i=0;i<8;++i) s.sprite.registers.d[i]=0xabcd1200U+i;
    for (unsigned int i=0;i<5;++i) s.sprite.registers.a[i]=0x76540000U+i;
    s.a5=0xffffffff;s.a6=0x102000;s.sprite.registers.d[0]=0x00030040;
    s.sprite.registers.d[7]=0x00110022;return s;
}
bool same(const ms5::ObjectSpriteWrapperState& a,const ms5::ObjectSpriteWrapperState& b) {
    for(unsigned int i=0;i<8;++i)if(a.sprite.registers.d[i]!=b.sprite.registers.d[i])return false;
    for(unsigned int i=0;i<5;++i)if(a.sprite.registers.a[i]!=b.sprite.registers.a[i])return false;
    return a.sprite.waiting==b.sprite.waiting&&a.a5==b.a5&&a.a6==b.a6;
}
std::vector<std::uint8_t> fixture() {
    std::vector<std::uint8_t> ram(65536,0);
    put(ram,0x9152,0xcd50,4);put(ram,0x8b36,12);put(ram,0x8d34,0x100);
    put(ram,0x2012,0xfedcba07,4);put(ram,0x201e,0x4567);
    return ram;
}
void failure(std::vector<std::uint8_t> ram,ms5::ObjectSpriteWrapperState s) {
    const std::vector<std::uint8_t> before=ram;const ms5::ObjectSpriteWrapperState saved=s;
    ms5::SpriteSubmitStatus status=ms5::SpriteFull;std::string error;
    assert(!ms5::execute_object_sprite_wrapper(ram,s,status,error));
    assert(!error.empty()&&ram==before&&same(s,saved)&&status==ms5::SpriteFull);
}
void accepted() {
    std::vector<std::uint8_t> ram=fixture();ms5::ObjectSpriteWrapperState s=initial(),want=s;
    want.a5=0x108000;want.sprite.registers.d[0]=0x456700c0;
    want.sprite.registers.d[1]=0xfedcba07;want.sprite.registers.d[2]=0xabcd1200;
    want.sprite.registers.d[3]=12;want.sprite.registers.d[4]=0xabcd0002;
    want.sprite.registers.d[5]=0xabcd4567;want.sprite.registers.d[6]=0xabcd0002;
    want.sprite.registers.d[7]=0x20110022;want.sprite.registers.a[0]=0x107f40;want.sprite.registers.a[1]=0x108b34;
    ms5::SpriteSubmitStatus status=ms5::SpriteClipped;std::string error="old";
    assert(ms5::execute_object_sprite_wrapper(ram,s,status,error));
    assert(error.empty()&&status==ms5::SpriteAccepted&&same(s,want));
    assert(get(ram,0x7f40)==want.sprite.registers.d[0]&&get(ram,0x7f44)==want.sprite.registers.d[1]&&get(ram,0x7f48)==want.sprite.registers.d[7]);
    assert(get(ram,0x8d3a,2)==2&&get(ram,0x8d38,2)==2&&get(ram,0x8b34,2)==12);
}
void conversion_clips() {
    const unsigned int flags[]={0,1,2,3,0x7c,0x81,0xfe,0xff};
    const std::uint32_t inputs[]={0x00000000,0xffff0000,0x7fff0000,0x80000000};
    const unsigned int offsets[]={0,1,0xffff,0x8000};
    for(unsigned int f=0;f<8;++f)for(unsigned int i=0;i<4;++i){
        std::vector<std::uint8_t> ram=fixture();ms5::ObjectSpriteWrapperState s=initial(),want=s;
        s.sprite.registers.d[0]=want.sprite.registers.d[0]=inputs[i];ram[0x2053]=flags[f];
        put(ram,0x2042,offsets[i]);put(ram,0x2046,0);
        const unsigned int x=((inputs[i]>>16)+offsets[i]-(flags[f]&1U))&65535U;
        const unsigned int y=(0U-((flags[f]>>1)&1U))&65535U;
        want.a5=0x108000;want.sprite.registers.d[0]=(x<<16)|((y-0x40U)&65535U);
        want.sprite.registers.d[1]=0xfedcba07;want.sprite.registers.d[2]=0xabcd1200U|(flags[f]>>2);
        want.sprite.registers.d[3]=0;want.sprite.registers.d[5]=0xabcd4567;want.sprite.registers.a[0]=0xcd50;
        const std::vector<std::uint8_t> before=ram;ms5::SpriteSubmitStatus status=ms5::SpriteFull;std::string error;
        assert(ms5::execute_object_sprite_wrapper(ram,s,status,error));assert(status==ms5::SpriteClipped&&ram==before&&same(s,want));
    }
    // ADD wraps before SUBX: bit0 takes its X from LSR, not ADD carry.
    std::vector<std::uint8_t> ram=fixture();ms5::ObjectSpriteWrapperState s=initial();
    s.sprite.registers.d[0]=0xffff003f;put(ram,0x2042,1);put(ram,0x2046,1);ram[0x2053]=1;
    ms5::SpriteSubmitStatus status=ms5::SpriteFull;std::string error;
    assert(ms5::execute_object_sprite_wrapper(ram,s,status,error));assert(status==ms5::SpriteAccepted&&s.sprite.registers.d[2]==0xabcd1200);
    assert(s.sprite.registers.d[0]==0x4567ffc0&&s.sprite.registers.d[7]==0x20110022);
}
void waits() {
    std::vector<std::uint8_t> ram=fixture();put(ram,0x8d34,2);put(ram,0x8d36,4);
    ms5::ObjectSpriteWrapperState s=initial();ms5::SpriteSubmitStatus status=ms5::SpriteFull;std::string error;
    assert(ms5::execute_object_sprite_wrapper(ram,s,status,error));assert(status==ms5::SpriteWaiting&&s.sprite.waiting&&s.a5==0x108000);
    const ms5::ObjectSpriteWrapperState captured=s;
    put(ram,0x9152,0xdeadbeef,4);put(ram,0x8d36,0xffff);put(ram,0x8d3a,0x1234);
    put(ram,0x2012,0xffffffff,4);put(ram,0x201e,1);put(ram,0x2042,0x8000);put(ram,0x2046,0xffff);ram[0x2053]=0xff;
    const std::vector<std::uint8_t> poisoned=ram;
    assert(ms5::execute_object_sprite_wrapper(ram,s,status,error));assert(status==ms5::SpriteWaiting&&same(s,captured)&&ram==poisoned);
    ms5::ObjectSpriteWrapperState bad=s;bad.a5=0x108002;failure(ram,bad);
    put(ram,0x8d34,4);put(ram,0x8d38,1);failure(ram,s); // Fails after publishing producer on resume.
    put(ram,0x8d38,0);std::vector<std::uint8_t> expected=ram;
    ms5::ObjectSpriteWrapperState want=captured;ms5::SpriteSubmitStatus direct=ms5::SpriteWaiting;
    assert(ms5::execute_sprite_submit(expected,want.sprite,direct,error));
    assert(ms5::execute_object_sprite_wrapper(ram,s,status,error));assert(status==ms5::SpriteAccepted&&same(s,want)&&ram==expected);
    assert(get(ram,0x8d3a,2)==2&&s.sprite.registers.d[2]==captured.sprite.registers.d[2]&&s.a6==captured.a6);
    // A6 is not dereferenced by a captured hold, even outside CPU RAM.
    s=captured;s.a6=0xffffffff;put(ram,0x8d34,6);const ms5::ObjectSpriteWrapperState untouched=s;
    assert(ms5::execute_object_sprite_wrapper(ram,s,status,error));assert(status==ms5::SpriteWaiting&&same(s,untouched));
}
void errors() {
    std::vector<std::uint8_t> ram=fixture();ms5::ObjectSpriteWrapperState s=initial();
    put(ram,0x8b36,1);failure(ram,s); // Callee mutates producer/list before odd record fails.
    ram=fixture();put(ram,0x9152,0,4);s.sprite.registers.d[0]=0;failure(ram,s); // Callback checked before clip.
    ram=fixture();s=initial();s.a6=0x102001;failure(ram,s); // BYTE fits; reached WORD is odd.
    s=initial();s.a6=0x10ffad;failure(ram,s);s.a6=0xffffffff;failure(ram,s);
    // Only actual fields must fit: lowest and highest supported even bases.
    const std::uint32_t bases[]={0xfffee,0x10ffac};
    for(unsigned int i=0;i<2;++i){ram=fixture();s=initial();s.a6=bases[i];s.sprite.registers.d[0]=0;
        const unsigned int at=static_cast<unsigned int>(s.a6+0x12-0x100000);
        put(ram,at,0,4);put(ram,at+0xc,0);put(ram,at+0x30,0);put(ram,at+0x34,0);ram[at+0x41]=0;
        ms5::SpriteSubmitStatus status=ms5::SpriteAccepted;std::string error;
        assert(ms5::execute_object_sprite_wrapper(ram,s,status,error));assert(status==ms5::SpriteClipped&&s.a6==bases[i]);}
    ram.resize(65535);failure(ram,initial());
}
}
int main(){accepted();conversion_clips();waits();errors();std::cout<<"object_sprite_wrapper_test passed\n";return 0;}
