#include "ms5/input_status.h"
#include <new>
namespace ms5 {
bool update_input_status(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& table, std::string& error) {
    if(ram.size()!=65536U) {error="input status requires 64KiB RAM";return false;}
    if(table.source_cpu_address!=0xb58U || table.source_rom_offset!=0xb58U ||
       table.data.size()!=256U) {error="input status requires complete b58 lookup window";return false;}
    ram[0x12]=ram[0xfdaf];
    ram[0xf007]=0;
    unsigned int status=0;
    for(int bit=3;bit>=0;--bit) {
        const unsigned int mask=1U<<bit;
        const bool pending=(ram[0xf006]&mask)!=0;
        ram[0xf006]=static_cast<std::uint8_t>(ram[0xf006]&~mask);
        const std::size_t slot=0xfdb6U+static_cast<unsigned int>(bit);
        if(pending) ram[slot]=1;
        const unsigned int index=(4U+ram[slot])&255U;
        if(table.data[index]!=0) status|=mask;
    }
    ram[0xf007]=static_cast<std::uint8_t>(status);
    error.clear();return true;
}
bool step_input(std::vector<std::uint8_t>& ram,const FixedDataResource& streams,
                const FixedDataResource& table,const InputPortSamples& ports,
                std::uint8_t& read_count,std::string& error) {
    std::vector<std::uint8_t> candidate;
    try {candidate=ram;} catch(const std::bad_alloc&) {error="cannot allocate input status state";return false;}
    std::uint8_t candidate_reads=0;
    if(!sample_input(candidate,streams,ports,candidate_reads,error) ||
       !update_input_status(candidate,table,error)) return false;
    ram.swap(candidate);read_count=candidate_reads;error.clear();return true;
}
}
