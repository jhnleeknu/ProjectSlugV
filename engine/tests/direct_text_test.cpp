#include "ms5/fixed_text.h"
#include <cassert>
#include <iostream>

int main() {
    std::vector<std::uint8_t> text;
    text.push_back(255);
    text.push_back(0);
    std::vector<ms5::VideoPortWrite> writes;
    std::string error;
    assert(ms5::trace_direct_fixed_text(text, 0xffff, 0xabcd, writes, error));
    assert(writes.size() == 2);
    assert(writes[0].address == 0x3c0000 && writes[0].size == 4 && writes[0].value == 0xffffbdffU);
    assert(writes[1].address == 0x3c0000 && writes[1].size == 2 && writes[1].value == 0x8200);
    text.pop_back();
    assert(!ms5::trace_direct_fixed_text(text, 0, 0, writes, error));
    assert(writes.size() == 2 && writes[0].value == 0xffffbdffU);
    text.assign(100001, 'A');
    text.push_back(0);
    assert(!ms5::trace_direct_fixed_text(text, 0, 0, writes, error));
    assert(writes.size() == 2 && writes[1].value == 0x8200);
    text.assign(1, 0);
    assert(ms5::trace_direct_fixed_text(text, 0, 0, writes, error) && writes.empty());
    std::cout << "Direct text port ordering and output preservation passed\n";
}
