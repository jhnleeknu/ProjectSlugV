#include "ms5/input_sampler.h"
#include <new>
namespace ms5 {
namespace {
unsigned int word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<unsigned int>(ram[at])<<8)|ram[at+1];
}
void put_word(std::vector<std::uint8_t>& ram, std::size_t at, unsigned int value) {
    ram[at]=static_cast<std::uint8_t>(value>>8);
    ram[at+1]=static_cast<std::uint8_t>(value);
}
void update(std::vector<std::uint8_t>& ram, std::size_t at, std::uint8_t input) {
    ram[at+1]=ram[at+2];
    ram[at+2]=input;
    ram[at+3]=static_cast<std::uint8_t>((ram[at+1]^input)&input);
    if(ram[at+3]!=0) {
        ram[at+4]=ram[at+3]; ram[at+5]=ram[0x4cd2];
    } else {
        ram[at+5]=static_cast<std::uint8_t>(ram[at+5]-1U);
        ram[at+4]=0;
        if(ram[at+5]==0) {ram[at+4]=input;ram[at+5]=ram[0x4cd3];}
    }
}
bool read_stream(const FixedDataResource& streams, std::uint32_t base,
                 unsigned int index, std::uint8_t& value, std::string& error) {
    const std::int64_t displacement=index<0x8000U ? index : static_cast<std::int64_t>(index)-65536;
    const std::int64_t offset=static_cast<std::int64_t>(base)+displacement-streams.source_cpu_address;
    if(offset<0 || static_cast<std::uint64_t>(offset)>=streams.data.size()) {
        error="input replay read falls outside fixed resource";return false;
    }
    value=streams.data[static_cast<std::size_t>(offset)];return true;
}
bool replay(std::vector<std::uint8_t>& ram,const FixedDataResource& streams,std::string& error) {
    unsigned int cursor=word(ram,0x4cce);
    // Original exits before accessing the resource when the cursor is exhausted.
    if(cursor>=0x600U) {ram[0x4cd4]=2;return true;}
    if(streams.source_cpu_address!=0xf01feU || streams.source_rom_offset!=0xf01feU ||
       streams.data.size()!=0x1810U) {error="input replay requires complete native input window";return false;}
    const std::uint32_t base=(static_cast<std::uint32_t>(word(ram,0x4cc4))<<16)|word(ram,0x4cc6);
    while(cursor<0x600U) {
        std::uint8_t duration=0;
        if(!read_stream(streams,base,cursor,duration,error)) return false;
        const unsigned int previous=word(ram,0x4ccc);
        const unsigned int limit=cursor==previous ? 15U : 255U;
        if(cursor==previous) duration&=15U;
        if(duration!=ram[0x4cd0]) {
            put_word(ram,0x4cce,cursor);
            ram[0x4cd0]=static_cast<std::uint8_t>(ram[0x4cd0]+1U);return true;
        }
        ram[0x4cd0]=0;
        ++cursor;
        if(duration==limit) {
            std::uint8_t following=0;
            if(!read_stream(streams,base,cursor,following,error)) return false;
            if(following!=0) {
                put_word(ram,0x4cce,cursor);ram[0x4cd0]=1;return true;
            }
            ++cursor;
        }
        put_word(ram,0x4ccc,cursor);
        std::uint8_t event=0;
        if(!read_stream(streams,base,previous,event,error)) return false;
        put_word(ram,0x4cc2,word(ram,0x4cc2)^(1U<<(event>>4)));
    }
    ram[0x4cd4]=2;return true;
}
}
bool initialize_input(std::vector<std::uint8_t>& ram, const FixedDataResource& streams,
                      std::uint16_t selector, std::string& error) {
    if(ram.size()!=65536U) {error="input initializer requires 64KiB RAM";return false;}
    if(selector<2U && (streams.source_cpu_address!=0xf01feU ||
        streams.source_rom_offset!=0xf01feU || streams.data.size()!=0x1810U)) {
        error="input initializer requires complete native input window";return false;
    }
    // Validate before mutation. Copy native BE32 pointer bytes without host pointers.
    for(std::size_t at=0x4ca8;at<0x4cb4;++at) ram[at]=0;
    ram[0x4cd4]=selector<2U ? 1 : 0;
    if(selector<2U) {
        const std::size_t entry=static_cast<std::size_t>(selector)*4U;
        for(std::size_t byte=0;byte<4;++byte) {
            ram[0x4cc4+byte]=streams.data[0xc00U+entry+byte];
            ram[0x4cc8+byte]=streams.data[0x1808U+entry+byte];
        }
        put_word(ram,0x4ccc,0);put_word(ram,0x4cce,0);
        put_word(ram,0x4cc2,0);ram[0x4cd0]=0;
    }
    error.clear();return true;
}
bool sample_input(std::vector<std::uint8_t>& ram,const FixedDataResource& streams,
                  const InputPortSamples& ports,std::uint8_t& read_count,std::string& error) {
    if(ram.size()!=65536U) {error="input sampler requires 64KiB RAM";return false;}
    std::vector<std::uint8_t> candidate;
    try {candidate=ram;} catch(const std::bad_alloc&) {error="cannot allocate input state";return false;}
    const std::uint8_t system=static_cast<std::uint8_t>((~ports.system)&15U);
    candidate[0x4cb5]=static_cast<std::uint8_t>((candidate[0x4cb4]^system)&system);
    candidate[0x4cb4]=system;
    update(candidate,0x4cb6,static_cast<std::uint8_t>(~ports.player1_raw));
    update(candidate,0x4cbc,static_cast<std::uint8_t>(~ports.player2_raw));
    const unsigned int mode=candidate[0x4cd4];
    if(mode==0) {
        candidate[0x4ca8]=candidate[0xfd94];
        update(candidate,0x4ca8,static_cast<std::uint8_t>(~ports.player1_game));
        candidate[0x4cae]=candidate[0xfd9a];
        update(candidate,0x4cae,static_cast<std::uint8_t>(~ports.player2_game));
    } else if(mode==1) {
        if(!replay(candidate,streams,error)) return false;
        update(candidate,0x4ca8,candidate[0x4cc2]);
        update(candidate,0x4cae,candidate[0x4cc3]);
    } else {
        update(candidate,0x4ca8,0);update(candidate,0x4cae,0);
    }
    ram.swap(candidate);read_count=mode==0 ? 5 : 3;error.clear();return true;
}
}
