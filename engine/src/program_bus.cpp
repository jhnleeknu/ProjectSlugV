#include "ms5/program_bus.h"
namespace ms5 {
namespace {
bool fail(std::string& error,const char* message) {error=message;return false;}
bool request(const std::vector<std::uint8_t>& ram,std::uint32_t logical,unsigned int size,std::string& error) {
    if(ram.size()!=65536)return fail(error,"program bus requires exact64KiB RAM");
    if(size!=1 && size!=2 && size!=4)return fail(error,"program bus size must be1/2/4");
    if(size>1 && (logical&1U))return fail(error,"program bus requires even WORD/LONG address");
    return true;
}
unsigned int kind(const FixedDataResource& w) {
    const std::uint32_t cpu=w.source_cpu_address,rom=w.source_rom_offset;
    const std::size_t n=w.data.size();
    if(n==0)return 0;
    if(cpu<0x100000U)return cpu==rom && n<=0x100000U-cpu?1:0;
    if(cpu<0x200000U || cpu>=0x2ffff0U || n>0x2ffff0U-cpu ||
        rom>=0x800000U || n>0x800000U-rom || rom<cpu-0x200000U)return 0;
    const std::uint32_t bank=rom-(cpu-0x200000U);
    return bank>=0x100000U && bank%0x100000U==0?2:0;
}
bool rom_unit(const std::vector<FixedDataResource>& windows,unsigned int wanted,
    std::uint64_t physical,unsigned int size,std::uint32_t& value,std::string& error) {
    const FixedDataResource* selected=NULL;std::size_t at=0;unsigned int matches=0;
    for(std::size_t i=0;i<windows.size();++i) {
        const FixedDataResource& w=windows[i];if(kind(w)!=wanted)continue;
        const std::uint64_t start=w.source_rom_offset,end=start+w.data.size();
        if(physical<end && physical+size>start) {
            ++matches;
            if(physical>=start && physical+size<=end) {selected=&w;at=static_cast<std::size_t>(physical-start);}
        }
    }
    if(matches!=1 || selected==NULL)return fail(error,"missing, partial or ambiguous program bus ROM unit");
    value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|selected->data[at+i];return true;
}
bool read_unit(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    const ProgramBusState& bus,std::uint32_t address,unsigned int size,std::uint32_t& value,std::string& error) {
    const std::vector<std::uint8_t>* bytes=NULL;std::size_t at=0;
    if(address<0x80U) {
        if(bus.vectors==NULL || bus.vectors->size()!=128)return fail(error,"reached program vectors require exact128BYTE view");
        bytes=bus.vectors;at=address;
    } else if(address<0x100000U)return rom_unit(windows,1,address,size,value,error);
    else if(address<0x200000U) {
        value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|ram[(address+i)&65535U];return true;
    } else if(address<0x2fe000U) {
        const std::uint64_t physical=static_cast<std::uint64_t>(bus.bank_base)+(address-0x200000U);
        if(bus.bank_base<0x100000U || physical+size>0x800000U)return fail(error,"reached program bank physical span outside ROM");
        return rom_unit(windows,2,physical,size,value,error);
    } else if(address<0x300000U) {
        if(bus.pvc==NULL || bus.pvc->size()!=8192)return fail(error,"reached PVC requires exact8192BYTE view");
        bytes=bus.pvc;at=address-0x2fe000U;
    } else return fail(error,"unsupported program bus device address");
    value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|(*bytes)[at+i];return true;
}
}
bool read_program_bus(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    const ProgramBusState& bus,std::uint32_t logical,unsigned int size,std::uint32_t& value,std::string& error) {
    if(!request(ram,logical,size,error))return false;
    const unsigned int unit=size==1?1:2;std::uint32_t candidate=0;
    for(unsigned int offset=0;offset<size;offset+=unit) {
        const std::uint32_t address=static_cast<std::uint32_t>(logical+offset)&0xffffffU;
        std::uint32_t part=0;if(!read_unit(ram,windows,bus,address,unit,part,error))return false;
        candidate=(candidate<<(unit*8))|part;
    }
    value=candidate;error.clear();return true;
}
bool write_program_bus_ram(std::vector<std::uint8_t>& ram,std::uint32_t logical,
    unsigned int size,std::uint32_t value,std::string& error) {
    if(!request(ram,logical,size,error))return false;
    const unsigned int unit=size==1?1:2;
    for(unsigned int offset=0;offset<size;offset+=unit) {
        const std::uint32_t address=static_cast<std::uint32_t>(logical+offset)&0xffffffU;
        if(address<0x100000U || address>=0x200000U)return fail(error,"program bus write requires RAM mirror units");
    }
    for(unsigned int i=0;i<size;++i)ram[static_cast<std::uint32_t>(logical+i)&65535U]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));
    error.clear();return true;
}
}
