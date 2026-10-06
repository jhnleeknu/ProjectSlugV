#include "ms5/fixed_text.h"
#include <cassert>
#include <iostream>

int main() {
    ms5::FixedTextMeasure result;
    result.glyph_count = 123;
    result.style = 456;
    result.line = 789;
    result.consumed_bytes = 99;
    std::string error;
    std::vector<std::uint8_t> data(1, 92);
    assert(!ms5::measure_fixed_text(data, 0, 0, result, error));
    assert(result.glyph_count == 123 && result.style == 456 &&
           result.line == 789 && result.consumed_bytes == 99);
    data.push_back('n');
    data.push_back(0);
    assert(!ms5::measure_fixed_text(data, 0, 0x74ff, result, error));
    assert(result.glyph_count == 123 && result.consumed_bytes == 99);
    data.assign(65536, 0xff);
    data.push_back(0);
    assert(ms5::measure_fixed_text(data, 0, 0x7000, result, error));
    assert(result.glyph_count == 0 && result.consumed_bytes == 65537);
    data.assign(1, 0);
    assert(ms5::measure_fixed_text(data, 0xabcd, 0xffff, result, error));
    assert(result.style == 0xabcd && result.line == 0xffff && result.consumed_bytes == 1);
    std::cout << "Text measurement rollback and count width passed\n";
}
