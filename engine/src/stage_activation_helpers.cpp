#include "ms5/stage_activation_helpers.h"
#include <new>
namespace ms5 {
namespace {
void byte(std::uint32_t& value,std::uint32_t input){value=(value&0xffffff00U)|(input&255U);}
void word(std::uint32_t& value,std::uint32_t input){value=(value&0xffff0000U)|(input&65535U);}
std::int32_t signed_word(std::uint32_t value){return value<32768?static_cast<std::int32_t>(value):static_cast<std::int32_t>(value)-65536;}
bool at(std::uint32_t base,int displacement,unsigned int size,std::size_t& result,std::string& error){
    const std::int64_t address=static_cast<std::int64_t>(base)+displacement;
    if(address<0x100000 || address>0x110000-size || (size>1 && (address&1))){
        error="activation helper access requires aligned complete CPU RAM span";return false;
    }
    result=static_cast<std::size_t>(address-0x100000);return true;
}
bool read(const std::vector<std::uint8_t>& ram,std::uint32_t base,int displacement,unsigned int size,std::uint32_t& value,std::string& error){
    std::size_t offset=0;if(!at(base,displacement,size,offset,error))return false;
    value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|ram[offset+i];return true;
}
bool write(std::vector<std::uint8_t>& ram,std::uint32_t base,int displacement,unsigned int size,std::uint32_t value,std::string& error){
    std::size_t offset=0;if(!at(base,displacement,size,offset,error))return false;
    for(unsigned int i=0;i<size;++i)ram[offset+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));return true;
}
void emit(std::vector<VideoPortWrite>& ports,std::uint32_t address,std::uint32_t value){
    VideoPortWrite p;p.size=2;p.address=address;p.value=value;ports.push_back(p);
}
bool run(std::vector<std::uint8_t>& ram,std::uint32_t entry,ObjectRestartState& s,bool& carry,std::vector<VideoPortWrite>& ports,std::string& error){
    std::uint32_t value=0;
    if(entry==0x4e216){
        if(!read(ram,s.a[5],-0x75bc,1,value,error))return false;byte(s.d[0],value);
        if(value!=0 && value!=5){carry=false;return true;}
        if(!read(ram,s.a[5],-0x74f8,1,value,error))return false;byte(s.d[0],value);
        carry=value==0 || value==5;return true;
    }
    if(entry==0xbee){
        if(!read(ram,0x10f004,0,1,value,error))return false;byte(s.d[0],value);
        if(!write(ram,0x10f004,0,1,0,error))return false;s.a[0]=0x10fdb6;
        for(unsigned int i=0;i<2;++i){
            if(!read(ram,s.a[0],0,1,value,error))return false;byte(s.d[1],value);++s.a[0];
            if(value==1 || value==2){
                if(!write(ram,0x10f004,0,1,s.d[0],error))return false;carry=true;return true;
            }
        }
        carry=false;return true;
    }
    if(entry==0x16ed2){
        if(!read(ram,s.a[5],0xd3e,2,value,error))return false;word(s.d[0],value);
        std::uint32_t other=0;if(!read(ram,s.a[5],0xd46,2,other,error))return false;
        const bool less=signed_word(value)<signed_word(other);
        if(!read(ram,s.a[6],0x15,1,value,error))return false;
        return write(ram,s.a[6],0x15,1,less?(value|4U):(value&0xfbU),error);
    }
    const std::uint64_t pointer=static_cast<std::uint64_t>(s.a[6])+0x26;
    if(pointer>0xffffffffU){error="animation initializer A0 addition overflows";return false;}
    s.a[0]=static_cast<std::uint32_t>(pointer);
    if(!write(ram,s.a[6],0x18,1,0,error) || !write(ram,s.a[5],-0x7ff0,2,0,error))return false;
    emit(ports,0x2ffff2,0x1000);emit(ports,0x2ffff0,0);
    if(s.a[5]!=0x108000){error="original49f8c TRAP15: A5 must equal108000";return false;}
    return write(ram,s.a[0],0,4,s.a[1],error) && write(ram,s.a[0],4,2,0,error) && write(ram,s.a[0],6,2,s.d[0],error);
}
}
bool execute_stage_activation_helper(std::vector<std::uint8_t>& ram,std::uint32_t entry,ObjectRestartState& state,bool& carry,std::vector<VideoPortWrite>& ports,std::string& error){
    if(ram.size()!=65536 || (entry!=0x4e216 && entry!=0xbee && entry!=0x16ed2 && entry!=0x49f8c)){
        error="activation helper requires64KiB RAM and supported entry";return false;
    }
    try {
        std::vector<std::uint8_t> candidate=ram;ObjectRestartState next=state;bool result=carry;std::vector<VideoPortWrite> output;
        if(!run(candidate,entry,next,result,output,error))return false;
        ram.swap(candidate);state=next;carry=result;ports.swap(output);error.clear();return true;
    }catch(const std::bad_alloc&){error="cannot allocate activation helper transaction";return false;}
}
}
