#include "ms5/credit_request.h"
namespace ms5 {
namespace {
void low(std::uint32_t& d0,unsigned int value) {
    d0=(d0&0xffffff00U)|(value&255U);
}
void apply(std::vector<std::uint8_t>& ram,std::uint32_t& d0) {
    low(d0,ram[0xfdaf]);
    if(ram[0xfdaf]==1) {
        low(d0,ram[0xfdb4]&ram[0xf004]);
        if((d0&255U)!=0) {ram[0xfdb4]=0;ram[0xfdaf]=2;}
        return;
    }
    if(ram[0xfdaf]!=2) {ram[0xfdb4]=0;return;}
    low(d0,ram[0xfdb4]);
    // a2c shifts the byte twice, inserting availability into bit1 each time.
    for(unsigned int i=0;i<2;++i) {
        const bool requested=(d0&1U)!=0;
        low(d0,(d0&255U)>>1);
        if(requested && ram[4+i]!=0) low(d0,(d0&255U)|2U);
    }
    low(d0,(d0&255U)&ram[0xf004]&ram[0xf007]);
    ram[0xf006]|=static_cast<std::uint8_t>(d0);
    ram[0xfdb4]=static_cast<std::uint8_t>(d0);
    if((d0&255U)!=0) ram[0xfdaf]=2;
    // a4e shifts a WORD, including the incoming high byte of D0.word.
    for(unsigned int i=0;i<2;++i) {
        const bool requested=(d0&1U)!=0;
        d0=(d0&0xffff0000U)|((d0&65535U)>>1);
        if(requested && ram[4+i]!=0) {
            const unsigned int credit=ram[4+i];
            // SUB.W D6,D6 clears X before SBCD #1. Low-nibble borrow adjusts by6.
            ram[4+i]=static_cast<std::uint8_t>(credit-((credit&15U)==0 ? 7U : 1U));
        }
    }
}
}
bool process_credit_request(std::vector<std::uint8_t>& ram,std::uint32_t& d0,std::string& error) {
    if(ram.size()!=65536U) {error="credit request requires 64KiB RAM";return false;}
    if(ram[0xfd82]==0) {
        low(d0,ram[0x14]);
        if((d0&255U)!=0) {
            ram[0xfdb4]|=static_cast<std::uint8_t>(d0);
            apply(ram,d0);
            low(d0,static_cast<unsigned int>(ram[0xfdb4])^255U);
            ram[0x14]&=static_cast<std::uint8_t>(d0);
        }
    }
    error.clear();return true;
}
}
