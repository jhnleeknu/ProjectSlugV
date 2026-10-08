#include "ms5/palette_effect_execution.h"
#include "ms5/palette_control.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& r,unsigned int at,std::uint32_t v) {
    r[at]=static_cast<std::uint8_t>(v>>8); r[at+1]=static_cast<std::uint8_t>(v);
}
std::uint16_t get(const std::vector<std::uint8_t>& r,unsigned int at) {
    return static_cast<std::uint16_t>((static_cast<std::uint32_t>(r[at])<<8)|r[at+1]);
}
ms5::ObjectRestartState initial() {
    ms5::ObjectRestartState s;
    for(unsigned int i=0;i<8;++i) s.d[i]=0xabcd1234U+i*0x10101U;
    for(unsigned int i=0;i<7;++i) s.a[i]=0x98765432U+i*0x10101U;
    return s;
}
bool same(const ms5::ObjectRestartState& a,const ms5::ObjectRestartState& b) {
    for(unsigned int i=0;i<8;++i) if(a.d[i]!=b.d[i]) return false;
    for(unsigned int i=0;i<7;++i) if(a.a[i]!=b.a[i]) return false;
    return true;
}
void preserved(const ms5::ObjectRestartState& s,const ms5::ObjectRestartState& old) {
    assert(s.a[5]==0x108000);
    for(unsigned int i=4;i<8;++i) assert(s.d[i]==old.d[i]);
    for(unsigned int i=0;i<7;++i) if(i!=5) assert(s.a[i]==old.a[i]);
}
void success(std::vector<std::uint8_t>& r,ms5::ObjectRestartState& s) {
    const ms5::ObjectRestartState old=s; std::vector<std::uint8_t> expected=r; std::string error="old";
    assert(ms5::set_palette_effect(expected,static_cast<std::uint16_t>(s.d[0]),static_cast<std::uint16_t>(s.d[1]),
        static_cast<std::uint16_t>(s.d[2]),static_cast<std::uint8_t>(s.d[3]),error));
    assert(ms5::execute_palette_effect(r,s,error)); assert(r==expected && error.empty()); preserved(s,old);
}
void failure(std::vector<std::uint8_t>& r,ms5::ObjectRestartState& s) {
    const std::vector<std::uint8_t> old=r; const ms5::ObjectRestartState saved=s; std::string error;
    assert(!ms5::execute_palette_effect(r,s,error)); assert(r==old && same(s,saved) && !error.empty());
}
}
int main() {
    // Zero deltas preserve steps and in-range high words; clamp MOVEQ replaces
    // the entire register. This branch exposes widths that DIVS would replace.
    const unsigned int channels[]={0,1,31,32,0x7fff,0x8000,0xffe0,0xffe1,0xffff};
    const unsigned int targets[]={0,0x100,0x1f00,0x1f00,0x1f00,0xe100,0xe100,0xe100,0xff00};
    const unsigned int highs[]={0xabcd0000U,0xabcd0000U,0xabcd0000U,0,0,0xffff0000U,0xffff0000U,0xabcd0000U,0xabcd0000U};
    const unsigned int durations[]={0,1,2,3,255};
    std::vector<std::uint8_t> r; ms5::ObjectRestartState s;
    for(unsigned int c=0;c<9;++c) for(unsigned int t=0;t<5;++t) {
        r.assign(65536,0x5a); s=initial();
        for(unsigned int i=0;i<3;++i) { s.d[i]=0xabcd0000U|channels[c]; put(r,0x7dc2+i*2,targets[c]); put(r,0x7dceU+i*2,0x1234+i); }
        s.d[3]=0x9876ff00U|durations[t]; success(r,s);
        for(unsigned int i=0;i<3;++i) assert(s.d[i]==highs[c] && get(r,0x7dceU+i*2)==0x1234+i);
        assert(s.d[3]==0x98760000U && r[0x7dd4]==0);
    }
    // Wrapped signed deltas and DIVS both pack a signed remainder above the
    // signed quotient. Negative division truncates toward zero.
    r.assign(65536,0); s=initial(); s.d[0]=0x1234001f; s.d[1]=0x5678ffe1; s.d[2]=0x9abc0000; s.d[3]=0xffff12ff;
    put(r,0x7dc2,0x8000); put(r,0x7dc4,0x7fff); put(r,0x7dc6,1); success(r,s);
    assert(s.d[0]==0xff9fff9fU && s.d[1]==0x00620061U && s.d[2]==0xffff0000U && s.d[3]==255);
    assert(get(r,0x7dce)==0xff9f && get(r,0x7dd0)==97 && get(r,0x7dd2)==0 && r[0x7dd4]==255);
    // Durations0/1 normalize to1, including -32768 dividend; division cannot
    // overflow because the positive normalized divisor never equals -1.
    for(unsigned int duration=0;duration<=1;++duration) {
        r.assign(65536,0); s=initial(); s.d[0]=0; s.d[1]=0; s.d[2]=0; s.d[3]=0x7654ff00U|duration;
        put(r,0x7dc2,0x8000); put(r,0x7dc4,1); put(r,0x7dc6,0xffff); success(r,s);
        assert(s.d[0]==0x8000 && s.d[1]==0xffff && s.d[2]==1 && s.d[3]==1 && r[0x7dd4]==1);
    }
    // One nonzero channel still runs DIVS for the two zero channels, replacing
    // their old upper words rather than preserving them from the clamp branch.
    r.assign(65536,0); s=initial(); s.d[0]=0x12340000; s.d[1]=0x56780000; s.d[2]=0x9abc0001; s.d[3]=3;
    success(r,s); assert(s.d[0]==0 && s.d[1]==0 && s.d[2]==0x00010055 && s.d[3]==3);
    // Every malformed RAM size preserves all bytes and15registers, including
    // incoming A5 which would otherwise be replaced at the first instruction.
    s=initial(); r.assign(65535,0x77); failure(r,s); r.push_back(0); r.push_back(0); failure(r,s); r.clear(); failure(r,s);
    std::cout<<"palette_effect_execution_test passed\n";
}
