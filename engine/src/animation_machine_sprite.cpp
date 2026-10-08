#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool read_sprite(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool write_sprite(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
}
bool animation_sprite_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x16ea4:
        r.a[5]=0x108000;r.d[3]=0;
        if(!am_read(c,r.a[6]+0x53U,1,value))return false;am_byte(r.d[2],value);
        am_swap(r.d[0]);
        if(!am_read(c,r.a[6]+0x42U,2,value))return false;am_word(r.d[0],r.d[0]+value);
        {const std::uint32_t extend=r.d[2]&1U;am_byte(r.d[2],(r.d[2]&255U)>>1);am_word(r.d[0],r.d[0]-extend);}
        am_swap(r.d[0]);
        if(!am_read(c,r.a[6]+0x46U,2,value))return false;am_word(r.d[0],r.d[0]+value);
        {const std::uint32_t extend=r.d[2]&1U;am_byte(r.d[2],(r.d[2]&255U)>>1);am_word(r.d[0],r.d[0]-extend);}
        if(!am_read(c,r.a[6]+0x12U,4,r.d[1]) || !am_read(c,r.a[6]+0x1eU,2,value))return false;
        am_word(r.d[5],value);r.pc=0xcd58;return true; // Original tail JMP, with no return-slot push.
    case 0x16ed2:
        if(!read_sprite(c,0xd3e,2,value))return false;am_word(r.d[0],value);
        if(!read_sprite(c,0xd46,2,value))return false;
        {const bool less=((r.d[0]&65535U)^0x8000U)<(value^0x8000U);
        if(!am_read(c,r.a[6]+0x15U,1,value))return false;
        if(!am_write(c,r.a[6]+0x15U,1,less?(value|4U):(value&~4U)))return false;}
        return am_return(c);
    case 0xcd50:case 0xcd56:case 0xce00:return am_return(c);
    case 0xcd52:
        if(!write_sprite(c,0x1152,4,r.a[0]))return false;return am_return(c);
    case 0xcd58:
        if(!read_sprite(c,0x1152,4,r.a[0]))return false;
        // Only the original default RTS callback is currently defined here.
        if(r.a[0]!=0xcd50)return am_error(c,"unsupported sprite callback target");
        return am_call(c,r.a[0],0xcd5e);
    case 0xcd5e:
        am_word(r.d[0],r.d[0]-0x40U);
        if((r.d[0]&65535U)>=0x280U)return am_return(c);
        am_word(r.d[0],r.d[0]+0x40U);am_swap(r.d[0]);am_word(r.d[0],r.d[0]+0x160U);
        if((r.d[0]&65535U)>=0x400U)return am_return(c);
        am_word(r.d[0],r.d[0]-0x160U);am_swap(r.d[0]);
        r.a[1]=r.a[5]+0xb34U;
        if(!read_sprite(c,0xd3a,2,value))return false;am_word(r.d[6],value);
        am_word(r.d[6],r.d[6]+2U);am_word(r.d[6],r.d[6]&0x1feU);
        if(!read_sprite(c,0xd34,2,value))return false;
        if((r.d[6]&65535U)!=value) {r.pc=0xcdaa;return true;}
        if(!read_sprite(c,0xd36,2,value))return false;am_word(r.d[4],value);
        if(!read_sprite(c,0xd34,2,value))return false;
        if((r.d[4]&65535U)==value)return am_return(c);
        r.pc=0xcda4;c.waiting=true;return true;
    case 0xcda4:
        if(!read_sprite(c,0xd34,2,value))return false;
        if((r.d[4]&65535U)!=value) {c.waiting=true;return true;}
        r.pc=0xcdaa;return true;
    case 0xcdaa:
        if(!write_sprite(c,0xd3a,2,r.d[6]))return false;
        // BCLR on data register has a32-bit operand; bit6 matches prior API.
        {const bool deferred=(r.d[1]&64U)!=0;r.d[1]&=~64U;
        r.pc=deferred?0xcdd0:0xcdb6;}return true;
    case 0xcdb6:
        if(!read_sprite(c,0xd38,2,value))return false;am_word(r.d[4],value);
        if(!am_read(c,am_index(r.a[1],r.d[6]),2,value))return false;am_word(r.d[3],value);
        if(!am_write(c,am_index(r.a[1],r.d[4]),2,r.d[3]))return false;
        am_word(r.d[4],r.d[4]+2U);am_word(r.d[4],r.d[4]&0x1feU);
        if(!write_sprite(c,0xd38,2,r.d[4]))return false;r.pc=0xcde4;return true;
    case 0xcdd0:
        r.a[0]=r.a[5]+0xf4eU;
        if(!read_sprite(c,0x114e,2,value))return false;am_word(r.d[4],value);
        // The ADDQ reads memory afresh, after D4 captures the preceding WORD.
        if(!read_sprite(c,0x114e,2,value) || !write_sprite(c,0x114e,2,value+2U))return false;
        if(!am_read(c,am_index(r.a[1],r.d[6]),2,value))return false;am_word(r.d[3],value);
        if(!am_write(c,am_index(r.a[0],r.d[4]),2,r.d[3]))return false;r.pc=0xcde4;return true;
    case 0xcde4:
        r.a[0]=am_index(r.a[5],0xff34);r.a[0]=am_index(r.a[0],r.d[3]);
        am_swap(r.d[7]);am_word(r.d[0],r.d[0]<<7);am_word(r.d[7],r.d[7]|r.d[0]);am_swap(r.d[7]);
        am_byte(r.d[1],r.d[1]&7U);am_word(r.d[0],r.d[5]);am_swap(r.d[0]);am_word(r.d[0],r.d[0]<<6);
        // MOVEM.L D0-D1/D7,(A0) writes ascending registers to live bus memory.
        if(!am_write(c,r.a[0],4,r.d[0]) || !am_write(c,r.a[0]+4U,4,r.d[1]) ||
           !am_write(c,r.a[0]+8U,4,r.d[7]))return false;
        return am_return(c);
    default:return am_error(c,"unsupported animation sprite PC");
    }
}
}
