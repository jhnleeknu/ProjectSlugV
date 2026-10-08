#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t relative(std::uint32_t base,std::uint32_t magnitude) {
    return base-magnitude;
}
bool read_word_register(AnimationMachineContext& c,std::uint32_t address,std::uint32_t& reg) {
    std::uint32_t value=0;
    if (!am_read(c,address,2,value)) return false;
    am_word(reg,value);return true;
}
bool read_byte_register(AnimationMachineContext& c,std::uint32_t address,std::uint32_t& reg) {
    std::uint32_t value=0;
    if (!am_read(c,address,1,value)) return false;
    am_byte(reg,value);return true;
}
}
// State has no general CCR. Each condition-producing instruction is grouped
// with its immediately following conditional branch; all memory is read live.
bool animation_sound_block(AnimationMachineContext& c) {
    AnimationMachineState& s=c.s;
    std::uint32_t value=0;
    switch (s.pc) {
    // BYTE queue: A5-relative live head/tail and signed WORD queue index.
    case 0x3ac8:
        s.pc=(s.d[0]&255U)==3U?0x3ad0U:0x3ad8U;return true;
    case 0x3ad0:
        if (!am_write(c,relative(s.a[5],0x3285U),1,255)) return false;
        s.pc=0x3ad6;return true;
    case 0x3ad6:return am_return(c);
    case 0x3ad8:
        s.a[0]=relative(s.a[5],0x330cU);s.pc=0x3adc;return true;
    case 0x3adc:
        if (!read_word_register(c,relative(s.a[5],0x328aU),s.d[1])) return false;
        s.pc=0x3ae0;return true;
    case 0x3ae0:
        s.a[0]=am_index(s.a[0],s.d[1]);s.pc=0x3ae4;return true;
    case 0x3ae4:
        am_word(s.d[1],s.d[1]+1U);s.pc=0x3ae6;return true;
    case 0x3ae6:
        am_word(s.d[1],s.d[1]&127U);s.pc=0x3aea;return true;
    case 0x3aea:
        if (!am_read(c,relative(s.a[5],0x328cU),2,value)) return false;
        if ((s.d[1]&65535U)==value) {c.waiting=true;return true;}
        s.pc=0x3af0;return true;
    case 0x3af0:
        if (!am_write(c,s.a[0],1,s.d[0]&255U)) return false;
        s.pc=0x3af2;return true;
    case 0x3af2:
        if (!am_write(c,relative(s.a[5],0x328aU),2,s.d[1]&65535U)) return false;
        s.pc=0x3af6;return true;
    case 0x3af6:return am_return(c);
    // WORD queue, including every original gate and full ring flush path.
    case 0x3af8:
        s.pc=(s.d[0]&65535U)>=0x2000U?0x3b06U:0x3afeU;return true;
    case 0x3afe:
        s.pc=(s.d[0]&255U)>=0x20U?0x3b08U:0x3b06U;return true;
    case 0x3b06:return am_return(c);
    case 0x3b08:
        am_word(s.d[1],s.d[0]);s.pc=0x3b0a;return true;
    case 0x3b0a:
        am_byte(s.d[1],0);s.pc=0x3b0c;return true;
    case 0x3b0c:
        s.pc=(s.d[1]&65535U)==0x100U?0x3b14U:0x3b16U;return true;
    case 0x3b14:return am_return(c);
    case 0x3b16:
        s.pc=(s.d[1]&65535U)==0x300U?0x3b1eU:0x3b20U;return true;
    case 0x3b1e:return am_return(c);
    case 0x3b20:
        s.pc=(s.d[1]&65535U)==0x200U?0x3b28U:0x3b2aU;return true;
    case 0x3b28:return am_return(c);
    case 0x3b2a:
        if (!am_read(c,0x100012,1,value)) return false;
        s.pc=value!=1U?0x3b6eU:0x3b36U;return true;
    case 0x3b36:
        s.pc=(s.d[1]&65535U)!=0U?0x3b40U:0x3b3eU;return true;
    case 0x3b3e:return am_return(c);
    case 0x3b40:
        if (!am_read(c,0x10fd82,1,value)) return false;
        s.pc=value==0U?0x3b60U:0x3b4aU;return true;
    case 0x3b4a:
        if (!am_read(c,0x10fe80,1,value)) return false;
        s.pc=value!=0U?0x3b60U:0x3b54U;return true;
    case 0x3b54:
        if (!am_read(c,0xd00046,1,value)) return false;
        s.pc=value==0U?0x3b60U:0x3b5eU;return true;
    case 0x3b5e:return am_return(c);
    case 0x3b60:
        if (!am_read(c,0x10fd8d,1,value)) return false;
        s.pc=value!=0U?0x3b6eU:0x3b6cU;return true;
    case 0x3b6c:return am_return(c);
    case 0x3b6e:
        if (!am_read(c,0x104d7e,1,value)) return false;
        s.pc=value==0U?0x3b82U:0x3b78U;return true;
    case 0x3b78:
        s.pc=(s.d[0]&65535U)<0x1000U?0x3b82U:0x3b80U;return true;
    case 0x3b80:return am_return(c);
    case 0x3b82:
        if (!am_read(c,0x10f001,1,value)) return false;
        s.pc=(value&0x20U)==0U?0x3b98U:0x3b8eU;return true;
    case 0x3b8e:
        s.pc=(s.d[1]&65535U)!=0U?0x3b98U:0x3b96U;return true;
    case 0x3b96:return am_return(c);
    case 0x3b98:
        s.a[0]=relative(s.a[5],0x327eU);s.pc=0x3b9c;return true;
    case 0x3b9c:
        if (!read_word_register(c,relative(s.a[5],0x3276U),s.d[1])) return false;
        s.pc=0x3ba0;return true;
    case 0x3ba0:
        if (!am_read(c,relative(s.a[5],0x3274U),2,value)) return false;
        s.pc=(s.d[1]&65535U)==value?0x3bccU:0x3ba8U;return true;
    case 0x3ba8:
        s.a[1]=am_index(s.a[0],s.d[1]);s.pc=0x3bac;return true;
    case 0x3bac:
        am_word(s.d[1],s.d[1]+2U);s.pc=0x3bae;return true;
    case 0x3bae:
        am_word(s.d[1],s.d[1]&6U);s.pc=0x3bb2;return true;
    case 0x3bb2:
        if (!am_read(c,s.a[1],2,value)) return false;
        s.pc=(s.d[0]&65535U)!=value?0x3bcaU:0x3bb8U;return true;
    case 0x3bb8:
        if (!am_read(c,relative(s.a[5],0x3274U),2,value)) return false;
        s.pc=(s.d[1]&65535U)==value?0x3bc8U:0x3bc0U;return true;
    case 0x3bc0:
        if (!am_read(c,am_index(s.a[0],s.d[1]),2,value)) return false;
        if (!am_write(c,s.a[1],2,value)) return false;
        s.pc=0x3bc4;return true;
    case 0x3bc4:
        if (!am_write(c,am_index(s.a[0],s.d[1]),2,s.d[0]&65535U)) return false;
        s.pc=0x3bc8;return true;
    case 0x3bc8:return am_return(c);
    case 0x3bca:s.pc=0x3ba0;return true;
    case 0x3bcc:
        if (!am_write(c,am_index(s.a[0],s.d[1]),2,s.d[0]&65535U)) return false;
        s.pc=0x3bd0;return true;
    case 0x3bd0:
        am_word(s.d[1],s.d[1]+2U);s.pc=0x3bd2;return true;
    case 0x3bd2:
        am_word(s.d[1],s.d[1]&6U);s.pc=0x3bd6;return true;
    case 0x3bd6:
        if (!am_write(c,relative(s.a[5],0x3274U),2,s.d[1]&65535U)) return false;
        s.pc=0x3bda;return true;
    case 0x3bda:
        if (!am_read(c,relative(s.a[5],0x3276U),2,value)) return false;
        s.pc=(s.d[1]&65535U)==value?0x3be4U:0x3be2U;return true;
    case 0x3be2:return am_return(c);
    case 0x3be4:
        s.a[0]=am_index(s.a[0],s.d[1]);s.pc=0x3be8;return true;
    case 0x3be8:
        am_word(s.d[1],s.d[1]+2U);s.pc=0x3bea;return true;
    case 0x3bea:
        am_word(s.d[1],s.d[1]&6U);s.pc=0x3bee;return true;
    case 0x3bee:
        if (!am_write(c,relative(s.a[5],0x3276U),2,s.d[1]&65535U)) return false;
        s.pc=0x3bf2;return true;
    case 0x3bf2:
        if (!am_read(c,s.a[0],2,value)) return false;
        s.pc=value==0U?0x3c06U:0x3bf8U;return true;
    case 0x3bf8:
        if (!read_byte_register(c,s.a[0],s.d[0])) return false;
        s.a[0]+=1U;s.pc=0x3bfa;return true;
    case 0x3bfa:
        if (!am_read(c,s.a[0],1,value)) return false;
        s.a[0]+=1U;
        if (!am_push(c,1,value)) return false;
        s.pc=0x3bfc;return true;
    case 0x3bfc:return am_call(c,0x3ac8,0x3c00);
    case 0x3c00:
        if (!am_pop(c,1,value)) return false;
        am_byte(s.d[0],value);s.pc=0x3c02;return true;
    case 0x3c02:s.pc=0x3ac8;return true;
    case 0x3c06:return am_return(c);
    // Object sound callback and its actual nested helper/callee returns.
    case 0xca70:
        s.a[0]=relative(s.a[5],0x76a4U);s.pc=0xca74;return true;
    case 0xca74:return am_return(c);
    case 0x47672:return am_call(c,0xca70,0x47678);
    case 0x47678:
        if (!read_byte_register(c,s.a[0],s.d[0])) return false;
        s.pc=0x4767a;return true;
    case 0x4767a:
        if (!am_read(c,s.a[6]+0x7eU,1,value)) return false;
        s.pc=(s.d[0]&255U)==value?0x47690U:0x47682U;return true;
    case 0x47682:
        if (!am_push(c,4,s.a[0])) return false;
        s.pc=0x47684;return true;
    case 0x47684:
        am_word(s.d[0],0x1ac0);s.pc=0x47688;return true;
    case 0x47688:return am_call(c,0x3af8,0x4768e);
    case 0x4768e:
        if (!am_pop(c,4,value)) return false;
        s.a[0]=value;s.pc=0x47690;return true;
    case 0x47690:
        if (!am_read(c,s.a[0],1,value)) return false;
        if (!am_write(c,s.a[6]+0x7eU,1,value)) return false;
        s.pc=0x47694;return true;
    case 0x47694:
        if (!read_word_register(c,s.a[0],s.d[1])) return false;
        s.pc=0x47696;return true;
    case 0x47696:
        value=s.d[1]&255U;
        am_byte(s.d[1],value*2U);
        // ADD.B signed overflow is true precisely for original40..bf.
        s.pc=value>=0x40U && value<=0xbfU?0x4769cU:0x476a0U;return true;
    case 0x4769c:
        am_byte(s.d[1],0x80);s.pc=0x476a0;return true;
    case 0x476a0:
        am_word(s.d[1],s.d[1]&0xfeU);s.pc=0x476a4;return true;
    case 0x476a4:
        s.a[0]=0x4411e;s.pc=0x476aa;return true;
    case 0x476aa:
        if (!read_word_register(c,am_index(s.a[0],s.d[1]),s.d[1])) return false;
        s.pc=0x476ae;return true;
    case 0x476ae:
        value=s.d[1]&65535U;am_word(s.d[1],value-1U);
        s.pc=value==0U?0x476b4U:0x476b6U;return true;
    case 0x476b4:s.d[1]=0;s.pc=0x476b6;return true;
    case 0x476b6:
        if (!am_write(c,s.a[6]+0x12U,1,s.d[1]&255U)) return false;
        s.pc=0x476ba;return true;
    case 0x476ba:return am_return(c);
    default:return am_error(c,"unsupported animation sound PC");
    }
}
}
