#include "ms5/random_state.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sys/stat.h>
namespace {
bool parse(const std::string& text,std::uint32_t& result) {
    unsigned int base=10;std::size_t start=0;
    if(text.size()>1 && text[0]=='0' && (text[1]=='x'||text[1]=='X')) {base=16;start=2;}
    if(start==text.size())return false;
    std::uint32_t value=0;
    for(std::size_t i=start;i<text.size();++i) {
        const char c=text[i];unsigned int digit;
        if(c>='0'&&c<='9')digit=static_cast<unsigned int>(c-'0');
        else if(base==16&&c>='a'&&c<='f')digit=static_cast<unsigned int>(c-'a')+10U;
        else if(base==16&&c>='A'&&c<='F')digit=static_cast<unsigned int>(c-'A')+10U;
        else return false;
        if(digit>=base||value>(0xffffffffU-digit)/base)return false;
        value=value*base+digit;
    }
    result=value;return true;
}
bool same_file(const char* first,const char* second) {
    struct stat a,b;
    return std::string(first)==second || (stat(first,&a)==0&&stat(second,&b)==0&&
           a.st_dev==b.st_dev&&a.st_ino==b.st_ino);
}
}
int main(int argc,char** argv) {
    if(argc!=6) {std::cerr<<"usage: step_random seed|next|scale D0 D1 INPUT_RAM OUTPUT_RAM\n";return 2;}
    const std::string mode(argv[1]);std::uint32_t d0=0,d1=0;
    if((mode!="seed"&&mode!="next"&&mode!="scale")||!parse(argv[2],d0)||!parse(argv[3],d1)) {
        std::cerr<<"mode or uint32 register input is invalid\n";return 1;
    }
    if(same_file(argv[4],argv[5])) {std::cerr<<"input and output must be distinct\n";return 1;}
    std::ifstream input(argv[4],std::ios::binary|std::ios::ate);
    if(!input||input.tellg()!=65536) {std::cerr<<"input must contain exactly 64 KiB RAM\n";return 1;}
    input.seekg(0,std::ios::beg);std::vector<std::uint8_t> ram(65536);
    if(!input.read(reinterpret_cast<char*>(&ram[0]),65536))return 1;
    std::string error;bool success=false;
    if(mode=="seed")success=ms5::seed_random(ram,d0,d1,error);
    else if(mode=="next")success=ms5::next_random(ram,d0,error);
    else success=ms5::scale_random(ram,d0,error);
    if(!success) {std::cerr<<error<<'\n';return 1;}
    std::ofstream output(argv[5],std::ios::binary|std::ios::trunc);
    if(!output)return 1;
    output.write(reinterpret_cast<const char*>(&ram[0]),65536);output.close();
    if(!output)return 1;
    std::cout<<"{\"d0\":"<<d0<<",\"d1\":"<<d1<<"}\n";return 0;
}
