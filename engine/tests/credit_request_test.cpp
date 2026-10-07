#include "ms5/credit_request.h"
#include <cassert>
#include <iostream>
int main() {
    std::vector<std::uint8_t> ram(65536,0);std::string error;std::uint32_t d0=0xabcdab00;
    ram[0xfdaf]=2;ram[0x14]=3;ram[0xf004]=ram[0xf007]=255;ram[4]=0x10;ram[5]=0xa0;
    assert(ms5::process_credit_request(ram,d0,error));
    assert(ram[4]==9 && ram[5]==0x99 && ram[0x14]==0 && ram[0xfdb4]==3 && ram[0xf006]==3);
    assert(d0==0xabcd2afc);
    ram[0xfd82]=1;const std::vector<std::uint8_t> before=ram;
    assert(ms5::process_credit_request(ram,d0,error));assert(ram==before && d0==0xabcd2afc);
    ram.assign(65536,0);ram[0xfdaf]=1;ram[0x14]=1;ram[0xf004]=1;ram[4]=0x10;d0=0x1234abcd;
    assert(ms5::process_credit_request(ram,d0,error));
    assert(ram[0xfdaf]==2 && ram[0xfdb4]==0 && ram[0x14]==1 && ram[4]==0x10 && d0==0x1234abff);
    assert(ms5::process_credit_request(ram,d0,error));
    assert(ram[0x14]==1 && ram[4]==0x10); // No active f007 slot accepts the request.
    ram.resize(1);d0=42;assert(!ms5::process_credit_request(ram,d0,error));assert(d0==42 && ram.size()==1);
    std::cout<<"Credit request byte/word widths, BCD borrow and mode transition passed\n";
}
