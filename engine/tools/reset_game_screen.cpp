#include "ms5/game_screen_reset.h"

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
    if(argc!=8) {std::cerr<<"usage: reset_game_screen ENTRY D0 D1 D3 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS\n";return 2;}
    std::uint32_t entry=0,d0=0,d1=0,d3=0;
    if(!parse_integer(argv[1],0xffffffffU,entry)||!parse_integer(argv[2],0xffffffffU,d0)||
       !parse_integer(argv[3],0xffffffffU,d1)||!parse_integer(argv[4],0xffffffffU,d3))return 1;
    const std::string input_path=argv[5],output_path=argv[6],ports_path=argv[7];
    std::string paths[3];const std::string originals[3]={input_path,output_path,ports_path};
    for(unsigned int index=0;index<3;++index)if(!canonical_path(originals[index],paths[index]))return 1;
    for(unsigned int first=0;first<3;++first)for(unsigned int second=first+1;second<3;++second)
        if(paths[first]==paths[second]||same_inode(originals[first],originals[second])) {std::cerr<<"paths must be distinct\n";return 1;}
    std::ifstream input(input_path.c_str(),std::ios::binary|std::ios::ate);
    if(!input||input.tellg()!=65536)return 1;
    input.seekg(0);std::vector<std::uint8_t> ram(65536);
    if(!input.read(reinterpret_cast<char*>(&ram[0]),65536))return 1;
    std::vector<ms5::VideoPortWrite> writes;std::string error;
    if(!ms5::reset_game_screen(ram,entry,d0,d1,d3,writes,error)) {std::cerr<<error<<'\n';return 1;}
    std::vector<std::uint8_t> bytes;bytes.reserve(writes.size()*9U);
    for(std::size_t index=0;index<writes.size();++index) {
        bytes.push_back(writes[index].size);
        for(int shift=24;shift>=0;shift-=8)bytes.push_back(static_cast<std::uint8_t>(writes[index].address>>shift));
        for(int shift=24;shift>=0;shift-=8)bytes.push_back(static_cast<std::uint8_t>(writes[index].value>>shift));
    }
    if(!save_bytes(output_path,ram)||!save_bytes(ports_path,bytes))return 1;
    std::cout<<"{\"d0\":"<<d0<<",\"d1\":"<<d1<<",\"d3\":"<<d3<<",\"writes\":"<<writes.size()<<"}\n";return 0;
}
