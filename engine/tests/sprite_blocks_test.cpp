#include "ms5/sprite_composition.h"
#include <cstdlib>
#include <iostream>

void require(bool value, const char* message) {
    if (!value) { std::cerr << message << '\n'; std::exit(1); }
}

int main() {
    // Two one-tile blocks at x=0 and x=16. The second has a different Y offset.
    const std::uint8_t raw[] = {2,0, 0,0,0,0,1,1,0,0,0,11,
                             0,16,0,16,1,1,0,0,0,12};
    std::vector<std::uint8_t> data(raw, raw+sizeof(raw));
    std::vector<ms5::SpriteWrite> writes;
    std::uint16_t next = 99;
    std::string error;
    require(ms5::emit_sprite_blocks(data,0,0,0,0,380,true,false,0,
                                    writes,next,error), "emit failed");
    require(next == 2 && writes.size() == 10, "wrong block allocation");
    require(writes[0].address == 0x8201 && writes[0].value == 1 &&
            writes[5].address == 0x8202 && writes[5].value == 0xf801 &&
            writes[6].address == 0x8402 && writes[6].value == 2048 &&
            writes[9].address == 128 && writes[9].value == 12, "wrong block placement");
    // Exhaustion must not suppress validation of a malformed later block.
    data[17] = 0;
    const std::vector<ms5::SpriteWrite> before = writes;
    require(!ms5::emit_sprite_blocks(data,0,0,0,0,1,true,false,0,
                                     writes,next,error), "bad later block accepted");
    require(next == 2 && writes.size() == before.size(), "failure changed outputs");
    for (std::size_t i=0; i<writes.size(); ++i) {
        require(writes[i].address == before[i].address && writes[i].value == before[i].value,
                "failure changed writes");
    }
    // Full 8-bit count, including a zero-slot call; parsing still reaches the end.
    data.assign(2,0); data[0]=255;
    for (unsigned int i=0; i<255; ++i) { data.insert(data.end(),raw+2,raw+12); }
    require(ms5::emit_sprite_blocks(data,0,0,0,0,0,false,false,0,
                                    writes,next,error) && writes.empty() && next==0,
            "maximum count failed");
    data.push_back(0);
    require(!ms5::emit_sprite_blocks(data,0,0,0,0,0,false,false,0,
                                     writes,next,error), "trailing byte accepted");
    std::cout << "sprite_blocks_test: passed\n";
}
