#include "ms5/physical_rom_resource.h"
#include <fstream>
#include <new>
namespace ms5 {
namespace {
std::uint32_t read_u32(const unsigned char* bytes) {
    return static_cast<std::uint32_t>(bytes[0])|(static_cast<std::uint32_t>(bytes[1])<<8)|
        (static_cast<std::uint32_t>(bytes[2])<<16)|(static_cast<std::uint32_t>(bytes[3])<<24);
}
std::uint32_t crc32(const std::vector<std::uint8_t>& bytes) {
    std::uint32_t crc=0xffffffffU;
    for(std::size_t i=0;i<bytes.size();++i) {
        crc^=bytes[i];
        for(unsigned int bit=0;bit<8;++bit)crc=(crc>>1)^((crc&1U)?0xedb88320U:0U);
    }
    return crc^0xffffffffU;
}
bool fail(std::string& error,const char* message) {error=message;return false;}
}
bool load_physical_rom_resource(const std::string& path,PhysicalRomResource& resource,std::string& error) {
    std::ifstream input(path.c_str(),std::ios::binary|std::ios::ate);
    if(!input)return fail(error,"cannot open physical ROM resource");
    const std::streamoff file_size=input.tellg();
    if(file_size<32)return fail(error,"physical ROM resource header is truncated");
    if(file_size>32+1048576)return fail(error,"physical ROM resource exceeds maximum size");
    input.seekg(0,std::ios::beg);unsigned char header[32];
    if(!input.read(reinterpret_cast<char*>(header),32))return fail(error,"cannot read physical ROM header");
    if(header[0]!='M' || header[1]!='S' || header[2]!='5' || header[3]!='D')return fail(error,"invalid physical ROM magic");
    if(read_u32(header+4)!=1 || read_u32(header+8)!=3 || read_u32(header+12)!=0xffffffffU || read_u32(header+28)!=0)
        return fail(error,"invalid physical ROM version/kind/sentinel/reserved field");
    const std::uint32_t rom=read_u32(header+16),size=read_u32(header+20);
    if(size==0 || size>0x100000U || rom>=0x800000U || size>0x800000U-rom)
        return fail(error,"invalid physical ROM payload span");
    if(file_size!=static_cast<std::streamoff>(32U+size))return fail(error,"physical ROM size differs from header");
    PhysicalRomResource candidate;
    try {candidate.data.resize(size);}catch(const std::bad_alloc&) {return fail(error,"cannot allocate physical ROM payload");}
    if(!input.read(reinterpret_cast<char*>(&candidate.data[0]),size))return fail(error,"cannot read physical ROM payload");
    char extra;if(input.get(extra) || input.bad() || !input.eof())return fail(error,"physical ROM size changed or read failed");
    if(crc32(candidate.data)!=read_u32(header+24))return fail(error,"physical ROM payload CRC32 mismatch");
    resource.data.swap(candidate.data);resource.source_rom_offset=rom;error.clear();return true;
}
}
