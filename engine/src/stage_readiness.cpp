#include "ms5/stage_readiness.h"
namespace ms5 {
namespace {
void word(std::uint32_t& value,std::uint32_t input){value=(value&0xffff0000U)|(input&65535U);}
void byte(std::uint32_t& value,std::uint32_t input){value=(value&0xffffff00U)|(input&255U);}
bool pointer(std::uint32_t base,int displacement,std::uint32_t& result,std::string& error){
    const std::int64_t address=static_cast<std::int64_t>(base)+displacement;
    if(address<0 || address>0xffffffffLL){error="stage readiness address addition overflows";return false;}
    result=static_cast<std::uint32_t>(address);return true;
}
bool read(const std::vector<std::uint8_t>& ram,std::uint32_t base,int displacement,
    unsigned int size,std::uint32_t& value,std::string& error){
    const std::int64_t address=static_cast<std::int64_t>(base)+displacement;
    if(address<0x100000 || address>0x110000-size || (size>1 && (address&1))){
        error="stage readiness read requires aligned complete CPU RAM span";return false;
    }
    const std::size_t at=static_cast<std::size_t>(address-0x100000);value=0;
    for(unsigned int i=0;i<size;++i)value=(value<<8)|ram[at+i];return true;
}
bool record(const std::vector<std::uint8_t>& ram,ObjectRestartState& s,bool& carry,std::string& error){
    if(!pointer(s.a[5],0x5d12,s.a[4],error))return false;
    word(s.d[0],s.d[0]&1U);
    if((s.d[0]&65535U)!=0 && !pointer(s.a[5],0x5d18,s.a[4],error))return false;
    std::uint32_t value=0;
    if(!read(ram,s.a[4],4,2,value,error))return false;
    if(value&0x8000U){carry=false;return true;}
    if(!read(ram,s.a[4],0,1,value,error))return false;
    if(value!=1 && value!=2){carry=false;return true;}
    if(!read(ram,s.a[4],2,1,value,error))return false;
    byte(s.d[1],value);carry=true;return true;
}
bool player(const std::vector<std::uint8_t>& ram,ObjectRestartState& s,bool& carry,std::string& error){
    if(!pointer(s.a[5],-0x7348,s.a[0],error))return false;
    word(s.d[0],s.d[0]&1U);
    if((s.d[0]&65535U)!=0 && !pointer(s.a[5],-0x7258,s.a[0],error))return false;
    std::uint32_t value=0;
    if(!read(ram,s.a[0],0,4,value,error))return false;
    if(value==0x270e){carry=true;return true;}
    if(!read(ram,s.a[0],0xa8,1,value,error))return false;
    if(value&16U){carry=true;return true;}
    if(!read(ram,s.a[0],0x61,1,value,error))return false;
    if(value&128U){carry=false;return true;}
    bool record_carry=false;if(!record(ram,s,record_carry,error))return false;
    const std::uint32_t status=s.d[1]&255U;
    carry=!record_carry || (status!=3 && status!=4 && status!=5);return true;
}
bool run(const std::vector<std::uint8_t>& ram,ObjectRestartState& s,bool& carry,std::string& error){
    s.d[0]=0;bool ready=false;if(!player(ram,s,ready,error))return false;
    if(!ready){carry=false;return true;}
    s.d[0]=1;if(!player(ram,s,ready,error))return false;
    if(!ready){carry=false;return true;}
    std::uint32_t value=0;if(!read(ram,s.a[5],0x5684,1,value,error))return false;
    if(value!=0){carry=true;return true;}
    s.d[0]=0;
    if(!read(ram,s.a[5],-0x75bc,1,value,error))return false;
    if(value==2)word(s.d[0],s.d[0]|1U);
    if(!read(ram,s.a[5],-0x74f8,1,value,error))return false;
    if(value==2)word(s.d[0],s.d[0]|2U);
    carry=(s.d[0]&255U)!=0;return true;
}
}
bool execute_stage_readiness(const std::vector<std::uint8_t>& ram,ObjectRestartState& state,bool& carry,std::string& error){
    if(ram.size()!=65536){error="stage readiness requires64KiB RAM";return false;}
    ObjectRestartState next=state;bool result=false;
    if(!run(ram,next,result,error))return false;
    state=next;carry=result;error.clear();return true;
}
}
