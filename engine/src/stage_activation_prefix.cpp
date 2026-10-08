#include "ms5/stage_activation_prefix.h"
#include <new>
namespace ms5 {
namespace {
bool address(std::uint32_t base, int displacement, unsigned int size,
    std::size_t& at, std::string& error) {
    const std::int64_t cpu=static_cast<std::int64_t>(base)+displacement;
    if (cpu<0x100000 || cpu>0x110000-size || (size>1 && (cpu&1))) {
        error="stage activation prefix access requires aligned complete CPU RAM span";
        return false;
    }
    at=static_cast<std::size_t>(cpu-0x100000); return true;
}
bool read_byte(const std::vector<std::uint8_t>& ram, std::uint32_t base,
    int displacement, std::uint8_t& value, std::string& error) {
    std::size_t at=0; if (!address(base,displacement,1,at,error)) return false;
    value=ram[at]; return true;
}
bool write(std::vector<std::uint8_t>& ram, std::uint32_t base,
    int displacement, unsigned int size, std::uint32_t value, std::string& error) {
    std::size_t at=0; if (!address(base,displacement,size,at,error)) return false;
    for (unsigned int i=0;i<size;++i) ram[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
    return true;
}
bool set_bit(std::vector<std::uint8_t>& ram, std::uint32_t base,
    int displacement, unsigned int mask, std::string& error) {
    std::uint8_t value=0;
    return read_byte(ram,base,displacement,value,error) &&
        write(ram,base,displacement,1,value|mask,error);
}
int signed_byte(std::uint8_t value) { return value<128 ? value : static_cast<int>(value)-256; }
bool run(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    ObjectRestartState& s, std::vector<VideoPortWrite>& ports, std::string& error) {
    std::uint8_t value=0;
    if (!read_byte(ram,s.a[5],0x5684,value,error)) return false;
    if (value==0) {
        if (!write(ram,0x107def,0,1,0,error) ||
            !write(ram,s.a[5],0x5d1f,1,255,error) ||
            !write(ram,s.a[5],0x5d20,1,0,error) ||
            !write(ram,s.a[5],-0x75be,1,0,error) ||
            !write(ram,s.a[5],-0x74fa,1,0,error) ||
            !set_bit(ram,s.a[5],0x5683,0x10,error)) return false;
    }
    s.d[0]=1;
    if (!read_byte(ram,s.a[5],0x5684,value,error)) return false;
    s.d[0]&=value;
    if (s.d[0]!=0 && !execute_stage_block_draw(ram,0x477a2,windows,s,ports,error)) return false;
    s.d[0]=4;
    if (!read_byte(ram,s.a[5],0x5684,value,error)) return false;
    s.d[0]&=value;
    if (s.d[0]==0 && !write(ram,s.a[5],-0x769b,1,255,error)) return false;
    if (!write(ram,s.a[5],-0x7699,1,0,error) ||
        !set_bit(ram,s.a[5],0x5683,4,error) ||
        !read_byte(ram,s.a[6],0x7c,value,error)) return false;
    s.d[0]=value;
    if (value<6) {
        std::uint8_t current=0;
        if (!read_byte(ram,s.a[5],-0xcf,current,error)) return false;
        if (signed_byte(value)>signed_byte(current) &&
            !write(ram,s.a[5],-0xcf,1,value,error)) return false;
    }
    return write(ram,s.a[6],0x7e,1,255,error) &&
        write(ram,s.a[6],0x20,2,0xea,error) &&
        write(ram,s.a[6],0,4,0x47c6c,error);
}
}
bool initialize_stage_activation_prefix(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, ObjectRestartState& state,
    std::vector<VideoPortWrite>& ports, std::string& error) {
    if (ram.size()!=65536) { error="stage activation prefix requires64KiB RAM"; return false; }
    try {
        std::vector<std::uint8_t> candidate=ram; ObjectRestartState next=state;
        std::vector<VideoPortWrite> output;
        if (!run(candidate,windows,next,output,error)) return false;
        ram.swap(candidate); state=next; ports.swap(output); error.clear(); return true;
    } catch (const std::bad_alloc&) { error="cannot allocate stage activation prefix transaction"; return false; }
}
}
