#include "ms5/stage_catalog.h"
#include <iostream>
namespace {
bool parse_integer(const std::string& text, std::uint32_t maximum,
                   std::uint32_t& result) {
    unsigned int base = 10;
    std::size_t start = 0;
    if (text.size() >= 2U && text[0] == '0' &&
        (text[1] == 'x' || text[1] == 'X')) {
        base = 16;
        start = 2;
    }
    if (start == text.size()) {
        return false;
    }
    std::uint32_t value = 0;
    for (std::size_t index = start; index < text.size(); ++index) {
        const char c = text[index];
        unsigned int digit;
        if (c >= '0' && c <= '9') {
            digit = static_cast<unsigned int>(c - '0');
        } else if (base == 16 && c >= 'a' && c <= 'f') {
            digit = static_cast<unsigned int>(c - 'a') + 10U;
        } else if (base == 16 && c >= 'A' && c <= 'F') {
            digit = static_cast<unsigned int>(c - 'A') + 10U;
        } else {
            return false;
        }
        if (digit >= base || digit > maximum || value > (maximum - digit) / base) {
            return false;
        }
        value = value * base + digit;
    }
    result = value;
    return true;
}

}
int main(int argc,char** argv) {
    if(argc!=4) {std::cerr << "usage: query_stage DIRECTORY STAGE AREA\n";return 2;}
    std::uint32_t stage,area;
    if(!parse_integer(argv[2],0xffff,stage) || !parse_integer(argv[3],0xffff,area)) return 1;
    ms5::StageCatalog catalog;
    std::string error;
    std::uint16_t count=0;
    std::uint32_t record=0,name=0;
    if(!ms5::load_stage_catalog(argv[1],catalog,error) ||
       !ms5::query_stage(catalog,static_cast<std::uint16_t>(stage),static_cast<std::uint16_t>(area),
                        count,record,name,error)) {std::cerr << error << '\n';return 1;}
    std::cout << "{\"count\":" << count << ",\"record\":" << record << ",\"name\":" << name << "}\n";
    return 0;
}
