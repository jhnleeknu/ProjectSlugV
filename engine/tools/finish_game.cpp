#include "ms5/game_initialization.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {

// Canonicalize an existing path, or its existing parent for a new output.
bool canonical_path(const std::string& path, std::string& canonical) {
    char* resolved = realpath(path.c_str(), 0);
    if (resolved != 0) {
        canonical.assign(resolved);
        std::free(resolved);
        return true;
    }
    const std::size_t slash = path.find_last_of('/');
    const std::string parent = slash == std::string::npos ? "."
        : (slash == 0 ? "/" : path.substr(0, slash));
    const std::string basename = slash == std::string::npos ? path : path.substr(slash + 1);
    if (basename.empty() || basename == "." || basename == "..") {
        return false;
    }
    resolved = realpath(parent.c_str(), 0);
    if (resolved == 0) {
        return false;
    }
    canonical.assign(resolved);
    std::free(resolved);
    canonical += "/" + basename;
    return true;
}

bool same_inode(const std::string& left, const std::string& right) {
    struct stat left_stat;
    struct stat right_stat;
    return stat(left.c_str(), &left_stat) == 0 &&
        stat(right.c_str(), &right_stat) == 0 &&
        left_stat.st_dev == right_stat.st_dev &&
        left_stat.st_ino == right_stat.st_ino;
}

bool save_bytes(const std::string& path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream output(path.c_str(), std::ios::binary | std::ios::trunc);
    if (!output) {
        return false;
    }
    if (!bytes.empty()) {
        output.write(reinterpret_cast<const char*>(&bytes[0]),
                     static_cast<std::streamsize>(bytes.size()));
    }
    output.close();
    return static_cast<bool>(output);
}

bool parse_integer(const std::string& text, std::uint32_t maximum, std::uint32_t& result) {
    unsigned int base = 10U;
    std::size_t start = 0U;
    if (text.size() >= 2U && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) {
        base = 16U; start = 2U;
    }
    if (start == text.size()) return false;
    unsigned int value = 0U;
    for (std::size_t index = start; index < text.size(); ++index) {
        const char c = text[index];
        unsigned int digit;
        if (c >= '0' && c <= '9') digit = static_cast<unsigned int>(c - '0');
        else if (base == 16U && c >= 'a' && c <= 'f') digit = static_cast<unsigned int>(c - 'a') + 10U;
        else if (base == 16U && c >= 'A' && c <= 'F') digit = static_cast<unsigned int>(c - 'A') + 10U;
        else return false;
        if (digit >= base || digit > maximum || value > (maximum - digit) / base) return false;
        value = value * base + digit;
    }
    result = value;
    return true;
}

} // namespace

int main(int argc,char** argv) {
    if(argc!=7) {std::cerr<<"usage: finish_game D0 D1 D3 INPUT_RAM OUTPUT_RAM RECORDS.ms5d\n";return 2;}
    std::uint32_t d0=0,d1=0,d3=0;
    if(!parse_integer(argv[1],0xffffffffU,d0)||!parse_integer(argv[2],0xffffffffU,d1)||!parse_integer(argv[3],0xffffffffU,d3))return 1;
    const std::string input_path=argv[4],output_path=argv[5],records_path=argv[6];
    std::string input_canonical,output_canonical,records_canonical;
    if(!canonical_path(input_path,input_canonical)||!canonical_path(output_path,output_canonical)||
       !canonical_path(records_path,records_canonical)||input_canonical==output_canonical||
       records_canonical==output_canonical||same_inode(input_path,output_path)||same_inode(records_path,output_path)) {
        std::cerr<<"output must be distinct from inputs\n";return 1;
    }
    std::ifstream input(input_path.c_str(),std::ios::binary|std::ios::ate);
    if(!input||input.tellg()!=65536)return 1;
    input.seekg(0);std::vector<std::uint8_t> ram(65536);
    if(!input.read(reinterpret_cast<char*>(&ram[0]),65536))return 1;
    ms5::FixedDataResource records;std::string error;
    if(!ms5::load_fixed_data_resource(records_path,records,error)||
       !ms5::finish_game_initialization(ram,records,d0,d1,d3,error)) {std::cerr<<error<<'\n';return 1;}
    if(!save_bytes(output_path,ram))return 1;
    std::cout<<"{\"d0\":"<<d0<<",\"d1\":"<<d1<<",\"d3\":"<<d3<<"}\n";return 0;
}
