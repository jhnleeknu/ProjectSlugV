#include "ms5/palette_effect_execution.h"
#include <new>
namespace ms5 {
namespace {
std::uint16_t low(std::uint32_t value) { return static_cast<std::uint16_t>(value); }
std::int32_t signed_word(std::uint32_t value) {
    const std::uint32_t word=low(value);
    return word<0x8000U?static_cast<std::int32_t>(word):static_cast<std::int32_t>(word)-65536;
}
void word(std::uint32_t& value,std::uint32_t input) { value=(value&0xffff0000U)|low(input); }
std::uint16_t read(const std::vector<std::uint8_t>& ram,unsigned int offset) {
    return static_cast<std::uint16_t>((static_cast<std::uint32_t>(ram[offset])<<8)|ram[offset+1]);
}
void write(std::vector<std::uint8_t>& ram,unsigned int offset,std::uint32_t value) {
    ram[offset]=static_cast<std::uint8_t>(value>>8); ram[offset+1]=static_cast<std::uint8_t>(value);
}
void run(std::vector<std::uint8_t>& ram,ObjectRestartState& s) {
    s.a[5]=0x108000;
    for (unsigned int i=0;i<3;++i) {
        const std::int32_t channel=signed_word(s.d[i]);
        if (channel>31) s.d[i]=31;
        else if (channel< -31) s.d[i]=0xffffffe1U;
    }
    for (unsigned int i=0;i<3;++i) {
        word(s.d[i],static_cast<std::uint32_t>(low(s.d[i]))<<8);
        write(ram,0x7dc8+i*2,s.d[i]);
    }
    word(s.d[3],s.d[3]&255U);
    if (low(s.d[3])<2) s.d[3]=(s.d[3]&0xffffff00U)|1U;
    ram[0x7dd4]=static_cast<std::uint8_t>(s.d[3]);
    for (unsigned int i=0;i<3;++i) word(s.d[i],s.d[i]-read(ram,0x7dc2+i*2));
    word(s.d[3],s.d[0]); word(s.d[3],s.d[3]|s.d[1]); word(s.d[3],s.d[3]|s.d[2]);
    if (low(s.d[3])==0) { ram[0x7dd4]=0; return; }
    s.d[3]=ram[0x7dd4];
    // Duration is normalized1..255. Sign-extended WORD dividends therefore
    // have no divide-by-zero or quotient-overflow case. C++11 signed division
    // truncates toward zero; unsigned WORD packing avoids signed shifts.
    for (unsigned int i=0;i<3;++i) {
        const std::int32_t dividend=signed_word(s.d[i]);
        const std::int32_t divisor=static_cast<std::int32_t>(s.d[3]);
        const std::int32_t quotient=dividend/divisor;
        const std::int32_t remainder=dividend%divisor;
        s.d[i]=(static_cast<std::uint32_t>(static_cast<std::uint16_t>(remainder))<<16)|
            static_cast<std::uint16_t>(quotient);
        write(ram,0x7dceU+i*2,s.d[i]);
    }
}
}
bool execute_palette_effect(std::vector<std::uint8_t>& ram,ObjectRestartState& state,std::string& error) {
    if (ram.size()!=65536) { error="palette effect execution requires64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate=ram; ObjectRestartState next=state;
        run(candidate,next); ram.swap(candidate); state=next; error.clear(); return true;
    } catch (const std::bad_alloc&) { error="cannot allocate palette effect execution transaction"; return false; }
}
}
