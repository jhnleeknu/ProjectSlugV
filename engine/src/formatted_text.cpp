#include "ms5/formatted_text.h"
#include <cstddef>

namespace ms5 {
namespace {
const std::size_t state = 0x4cd6U;
std::uint16_t word(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return static_cast<std::uint16_t>((static_cast<unsigned int>(ram[at]) << 8) | ram[at+1]);
}
std::uint32_t longword(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(word(ram,at)) << 16) | word(ram,at+2);
}
void putword(std::vector<std::uint8_t>& ram,std::size_t at,std::uint16_t v) {
    ram[at]=static_cast<std::uint8_t>(v>>8);ram[at+1]=static_cast<std::uint8_t>(v);
}
void putlong(std::vector<std::uint8_t>& ram,std::size_t at,std::uint32_t v) {
    putword(ram,at,static_cast<std::uint16_t>(v>>16));
    putword(ram,at+2,static_cast<std::uint16_t>(v));
}
struct Memory {
    const std::vector<std::uint8_t>& ram;
    const std::vector<FixedDataResource>& resources;
    std::uint32_t arguments_address;
    const std::vector<std::uint8_t>& arguments;
    bool slice(std::uint32_t address,std::vector<std::uint8_t>& data,std::string& error) const {
        if(address>=0x100000U && address<0x110000U) {
            data.assign(ram.begin()+(address-0x100000U),ram.end());return true;
        }
        if(address>=arguments_address && address-arguments_address<arguments.size()) {
            data.assign(arguments.begin()+(address-arguments_address),arguments.end());return true;
        }
        for(std::size_t i=0;i<resources.size();++i) {
            const FixedDataResource& r=resources[i];
            if(address>=r.source_cpu_address && address-r.source_cpu_address<r.data.size()) {
                data.assign(r.data.begin()+(address-r.source_cpu_address),r.data.end());return true;
            }
        }
        error="formatted text reads outside supplied memory";return false;
    }
    bool byte(std::uint32_t address,std::uint8_t& value,std::string& error) const {
        if(address>=0x100000U && address<0x110000U) {
            value=ram[address-0x100000U];return true;
        }
        if(address>=arguments_address && address-arguments_address<arguments.size()) {
            value=arguments[address-arguments_address];return true;
        }
        for(std::size_t i=0;i<resources.size();++i) {
            const FixedDataResource& r=resources[i];
            if(address>=r.source_cpu_address && address-r.source_cpu_address<r.data.size()) {
                value=r.data[address-r.source_cpu_address];return true;
            }
        }
        error="formatted text reads outside supplied memory";return false;
    }
    bool pointer(std::uint32_t address,std::uint32_t& value,std::string& error) const {
        if(address&1U) {error="formatted text pointer read is unaligned";return false;}
        value=0;
        for(unsigned int i=0;i<4;++i) {
            std::uint8_t b=0;if(!byte(address+i,b,error))return false;
            value=(value<<8)|b;
        }
        return true;
    }
};
bool parse(const Memory& memory,std::uint32_t& address,std::uint16_t& style,
           std::uint16_t& line,std::uint16_t& cursor,std::uint8_t& glyph,std::string& error) {
    std::vector<std::uint8_t> bytes;
    if(!memory.slice(address,bytes,error))return false;
    std::size_t position=0;
    if(!parse_fixed_text_glyph(bytes,position,style,line,cursor,glyph,error))return false;
    address+=static_cast<std::uint32_t>(position);return true;
}
bool render(const Memory& memory,const FixedDataResource& font,std::uint8_t glyph,
            std::uint32_t& address,std::uint16_t& cursor,std::uint16_t style,
            std::vector<VideoPortWrite>& output,std::string& error,
            std::uint32_t renderer,bool numeric=false) {
    if(renderer==0x3650U) {
        if(output.size()>99998U) {error="formatted text exceeds100000 port events";return false;}
        VideoPortWrite write;write.address=0x3c0000U;write.size=4;
        write.value=(static_cast<std::uint32_t>(cursor)<<16) |
            ((static_cast<std::uint32_t>(style)&0x0f00U)<<4) |
            ((static_cast<std::uint32_t>(style)&15U)<<8) | glyph;
        output.push_back(write);write.size=2;write.value=0x8200U;output.push_back(write);
        cursor=static_cast<std::uint16_t>(static_cast<unsigned int>(cursor)+0x20U);
        return true;
    }
    std::vector<std::uint8_t> bytes;
    if(numeric) {
        // 3a62 supplies3650 for numeric glyph lookahead. Its first byte is48,
        // so no supported numeric hex/space glyph consumes it.
        bytes.push_back(0x48);
    } else if(!memory.slice(address,bytes,error))return false;
    std::size_t position=0;
    std::vector<VideoPortWrite> glyph_writes;
    if(!render_table_text_glyph(glyph,bytes,position,cursor,style,font,glyph_writes,error))return false;
    if(output.size()+glyph_writes.size()>100000U) {
        error="formatted text exceeds100000 port events";return false;
    }
    address+=static_cast<std::uint32_t>(position);
    output.insert(output.end(),glyph_writes.begin(),glyph_writes.end());return true;
}
}

bool format_fixed_text(std::vector<std::uint8_t>& ram,
                       const std::vector<FixedDataResource>& resources,
                       const FixedDataResource& font,std::uint32_t format_address,
                       std::uint32_t arguments_address,const std::vector<std::uint8_t>& argument_bytes,
                       std::uint16_t cursor,std::uint16_t style,
                       std::vector<VideoPortWrite>& writes,std::string& error,std::uint32_t renderer,
                       std::uint16_t* final_style,std::uint16_t* final_line) {
    if(renderer!=0x3650U && renderer!=0xe84c8U) {
        error="formatted text supports renderer3650 or e84c8";return false;
    }
    if(ram.size()!=65536U) {error="formatted text requires64KiB work RAM";return false;}
    if(argument_bytes.size()>0x1000000U || arguments_address>0xffffffU ||
       argument_bytes.size()>0x1000000U-arguments_address) {
        error="formatted text argument table exceeds CPU address space";return false;
    }
    for(std::size_t i=0;i<resources.size();++i) {
        const FixedDataResource& r=resources[i];
        if(r.source_cpu_address>=0x100000U || r.source_cpu_address!=r.source_rom_offset ||
           r.data.empty() || r.data.size()>0x100000U-r.source_cpu_address) {
            error="formatted text requires fixed-ROM resource windows";return false;
        }
        for(std::size_t j=0;j<i;++j) {
            if(r.source_cpu_address<resources[j].source_cpu_address+resources[j].data.size() &&
               resources[j].source_cpu_address<r.source_cpu_address+r.data.size()) {
                error="formatted text ROM windows overlap";return false;
            }
        }
    }
    std::vector<std::uint8_t> pending_ram=ram;
    std::vector<VideoPortWrite> pending;
    const Memory memory={pending_ram,resources,arguments_address,argument_bytes};
    putword(pending_ram,state,cursor);putword(pending_ram,state+2,cursor);
    putword(pending_ram,state+4,style);putlong(pending_ram,state+6,format_address);
    putlong(pending_ram,state+10,renderer);putlong(pending_ram,state+14,arguments_address);
    putword(pending_ram,state+22,0);
    for(unsigned int step=0;step<100000U;++step) {
        std::uint32_t at=longword(pending_ram,state+6);
        cursor=word(pending_ram,state);style=word(pending_ram,state+4);
        std::uint16_t line=word(pending_ram,state+2);
        std::uint8_t glyph=0;
        if(!parse(memory,at,style,line,cursor,glyph,error))return false;
        if(glyph==0) {
            ram.swap(pending_ram);writes.swap(pending);
            if(final_style!=NULL) *final_style=style;
            if(final_line!=NULL) *final_line=line;
            error.clear();return true;
        }
        putword(pending_ram,state,cursor);putword(pending_ram,state+2,line);
        putword(pending_ram,state+4,style);
        if(glyph=='%') {
            std::uint8_t next=0;
            if(!memory.byte(at,next,error))return false;
            if(next=='%') {++at;glyph='%';}
            else {
                const bool zero_pad=next=='0';
                line=static_cast<std::uint16_t>((line&0xff00U)|(zero_pad?0xffU:0U));
                std::uint16_t width=65535U;
                if(next>='0' && next<='9') {
                    width=0;
                    do {
                        width=static_cast<std::uint16_t>(static_cast<unsigned int>(width)*10U+next-'0');
                        ++at;
                        if(!memory.byte(at,next,error))return false;
                    } while(next>='0' && next<='9');
                }
                if(width==0) {error="formatted text zero width triggers original trap";return false;}
                const std::uint8_t kind=next;++at;
                const std::uint16_t count=word(pending_ram,state+22);
                if(width==count) {
                    putword(pending_ram,state+22,0);putlong(pending_ram,state+6,at);continue;
                }
                std::uint32_t argument=longword(pending_ram,state+18);
                if((count&0xffU)==0) {
                    const std::uint32_t table=longword(pending_ram,state+14);
                    if(!memory.pointer(table,argument,error))return false;
                    putlong(pending_ram,state+14,table+4);putlong(pending_ram,state+18,argument);
                }
                const std::uint16_t digit=static_cast<std::uint16_t>(static_cast<unsigned int>(count)+1U);
                putword(pending_ram,state+22,digit);
                if(kind=='s') {
                    if(!parse(memory,argument,style,line,cursor,glyph,error))return false;
                    putword(pending_ram,state+4,style);putword(pending_ram,state+2,line);
                    if(!render(memory,font,glyph,argument,cursor,style,pending,error,renderer))return false;
                    putlong(pending_ram,state+18,argument);putword(pending_ram,state,cursor);
                    if(!memory.byte(argument,next,error))return false;
                    if(next==0)putword(pending_ram,state+22,width);
                } else if(kind=='x') {
                    if(digit>width) {error="formatted text hex digit exceeds width";return false;}
                    bool visible=zero_pad;
                    unsigned int nibble=0;
                    for(unsigned int index=0;index<digit;++index) {
                        std::uint8_t value=0;if(!memory.byte(argument,value,error))return false;
                        if(((index^width)&1U)==0)nibble=value>>4;
                        else {nibble=value&15U;++argument;}
                        if(nibble!=0 || digit==width)visible=true;
                    }
                    static const char hex[]="0123456789ABCDEF ";
                    glyph=static_cast<std::uint8_t>(hex[visible?nibble:16U]);
                    std::uint32_t lookahead=0x3650U;
                    if(!render(memory,font,glyph,lookahead,cursor,style,pending,error,renderer,true))return false;
                    putword(pending_ram,state,cursor);
                } else {error="formatted text unsupported conversion triggers original trap";return false;}
                continue;
            }
        }
        cursor=word(pending_ram,state);
        if(!render(memory,font,glyph,at,cursor,style,pending,error,renderer))return false;
        putword(pending_ram,state,cursor);putlong(pending_ram,state+6,at);
    }
    error="formatted text exceeds100000 execution steps";return false;
}
bool step_main_debug(std::vector<std::uint8_t>& ram,
                     const FixedDataResource& debug,std::uint32_t object_address,
                     std::uint32_t& d1,std::vector<VideoPortWrite>& writes,
                     std::string& error,std::uint16_t* line) {
    if(ram.size()!=65536U) {error="main debug requires 64KiB RAM";return false;}
    if((ram[0xf000]&1U)==0) {writes.clear();error.clear();return true;}
    if(object_address<0x100000U || object_address>0x10ff7bU) {
        error="main debug status field must lie in RAM";return false;
    }
    if(ram[object_address-0x100000U+0x84U]==0) {
        writes.clear();error.clear();return true;
    }
    if(debug.source_cpu_address!=0xd56U || debug.source_rom_offset!=0xd56U ||
       debug.data.size()!=0xe40U-0xd56U) {
        error="main debug requires exact native format and argument table window";return false;
    }
    const std::vector<FixedDataResource> resources(1,debug);
    const FixedDataResource unused_font;
    const std::vector<std::uint8_t> arguments;
    std::uint16_t style=static_cast<std::uint16_t>(d1);
    if(!format_fixed_text(ram,resources,unused_font,0xd56,0xdf0,arguments,
                          0x7066,style,writes,error,0x3650,&style,line)) return false;
    d1=(d1&0xffff0000U)|style;
    return true;
}

}
