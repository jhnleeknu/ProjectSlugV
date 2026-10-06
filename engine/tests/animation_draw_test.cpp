#include "ms5/animation_draw.h"
#include <cstdlib>
#include <iostream>
#include <limits>

void check(bool ok) { if (!ok) { std::cerr << "animation draw test failed\n"; std::exit(1); } }
int main() {
    std::vector<std::uint8_t> ram(65536,0), operand(7,0);
    ms5::AnimationDraw result = {false,1,2,3,4};
    std::string error;
    check(!ms5::decode_animation_draw(ram,std::numeric_limits<std::size_t>::max(),operand,result,error));
    check(!result.skipped && result.d0==1 && result.d1==2 && result.d5==3 && result.d7==4);
    check(ms5::decode_animation_draw(ram,65536-0x62,operand,result,error));
    result.d0=123;
    check(!ms5::decode_animation_draw(ram,65536-0x61,operand,result,error) && result.d0==123);
    operand.push_back(0);
    check(!ms5::decode_animation_draw(ram,0,operand,result,error) && result.d0==123);
    operand.resize(6);
    check(!ms5::decode_animation_draw(ram,0,operand,result,error) && result.d0==123);
    operand.resize(7); ram.pop_back();
    check(!ms5::decode_animation_draw(ram,0,operand,result,error) && result.d0==123);
    std::cout << "animation_draw_test: passed\n";
}
