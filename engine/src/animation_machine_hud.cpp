#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool read_hud(AnimationMachineContext& c,std::uint32_t offset,unsigned int size,std::uint32_t& value) {
    return am_read(c,c.s.a[5]+offset,size,value);
}
bool write_hud(AnimationMachineContext& c,std::uint32_t offset,unsigned int size,std::uint32_t value) {
    return am_write(c,c.s.a[5]+offset,size,value);
}
bool video(AnimationMachineContext& c,unsigned int size,std::uint32_t value) {
    if((c.s.a[4]&0xffffffU)!=0x3c0000U)return am_write(c,c.s.a[4],size,value);
    // One original MOVE.L is one observed video event, unlike PVC bus WORD units.
    VideoPortWrite port;port.address=0x3c0000;port.size=static_cast<std::uint8_t>(size);port.value=value;
    c.ports.push_back(port);return true;
}
bool dirty(AnimationMachineContext& c) {
    std::uint32_t value=0;return am_read(c,c.s.a[2]+15U,1,value) && am_write(c,c.s.a[2]+15U,1,value|128U);
}
}
bool animation_hud_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    case 0x47c6c:
        if(!read_hud(c,0x5684,1,value))return false;
        if(value) {r.pc=0x47d3e;return true;}
        r.d[0]=0;if(!read_hud(c,0x567e,2,value))return false;am_word(r.d[0],value);
        r.pc=0x47c7a;return true;
    case 0x47c7a:return am_call(c,0x4e286,0x47c80);
    case 0x47c80:
        if(!read_hud(c,0x567e,2,value))return false;r.pc=value?0x47c88:0x47eac;return true;
    case 0x47c88:return am_call(c,0x4843c,0x47c8c);
    case 0x47c8c:return am_call(c,0xca70,0x47c92);
    case 0x47c92:
        if(!am_read(c,r.a[0],2,value))return false;
        if(!value) {r.pc=0x47d24;return true;}
        if(!read_hud(c,0x7db6,1,value))return false;am_byte(r.d[0],value==1U?255U:0U);
        if(!read_hud(c,0x7db7,1,value))return false;am_byte(r.d[1],value==1U?255U:0U);
        am_byte(r.d[1],r.d[1]|r.d[0]);r.pc=(r.d[1]&255U)?0x47d24:0x47cae;return true;
    case 0x4843c: {
        if(!read_hud(c,0x5683,1,value))return false;
        if(!(value&16U))return am_return(c);
        if(!read_hud(c,0x7db6,1,value))return false;am_byte(r.d[0],value==1U?255U:0U);
        if(!read_hud(c,0x7db7,1,value))return false;am_byte(r.d[1],value==1U?255U:0U);
        am_byte(r.d[1],r.d[1]|r.d[0]);if(!(r.d[1]&255U))return am_return(c);
        if(!read_hud(c,0x567f,1,value))return false;am_byte(r.d[0],value);const unsigned int low=value;
        if(!read_hud(c,0x567e,1,other))return false;am_byte(r.d[1],other);r.d[2]=0;
        am_byte(r.d[0],low-2U);
        // Source0 rule follows the pinned independent raw-BCD reference (stage-counter contract).
        if(low<2U) {
            if(!other) {r.d[0]=0;r.d[1]=0;}
            else am_byte(r.d[1],other-((other&15U)?1U:7U));
        }
        if(!write_hud(c,0x567e,1,r.d[1]) || !write_hud(c,0x567f,1,r.d[0]))return false;
        return am_return(c);
    }
    case 0x4e286:
        if(!read_hud(c,0x5d1f,1,value))return false;
        if(!value)return am_return(c);
        if((r.d[0]&65535U)>0x99ffU) {
            am_word(r.d[0],0x7243);am_word(r.d[1],0xc904);r.d[2]=4;r.d[3]=2;r.pc=0x35f0;return true;
        }
        r.d[2]=0;
        if((r.d[0]&65535U)>=0xa00U) {
            if(!write_hud(c,0x5d20,1,0))return false;r.pc=0x4e2e2;return true;
        }
        if(!read_hud(c,0x5d20,1,value) || !write_hud(c,0x5d20,1,value-1U))return false;
        if(value) {r.pc=0x4e2d6;return true;}
        if(!am_push(c,2,r.d[0]))return false;am_word(r.d[0],0x1ac3);r.pc=0x4e2c8;return true;
    case 0x4e2c8:return am_call(c,0x3af8,0x4e2ce);
    case 0x4e2ce:
        if(!write_hud(c,0x5d20,1,0x1f) || !am_pop(c,2,value))return false;
        am_word(r.d[0],value);r.pc=0x4e2d6;return true;
    case 0x4e2d6:
        am_byte(r.d[2],r.d[0]);other=r.d[2]&0x20U;am_byte(r.d[2],r.d[2]<<3);
        if(other)am_byte(r.d[2],~r.d[2]);am_byte(r.d[2],(r.d[2]&255U)>>3);
        r.pc=0x4e2e2;return true;
    case 0x4e2e2:
        if(!am_push(c,2,r.d[0]))return false;r.d[0]=12;am_word(r.d[1],0xa0d);r.pc=0x4e2ea;return true;
    case 0x4e2ea:return am_call(c,0x8cda,0x4e2f0);
    case 0x4e2f0:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],(r.d[0]&65535U)>>8);
        if(!am_push(c,2,r.d[0]))return false;am_word(r.d[0],(r.d[0]&65535U)>>4);am_word(r.d[0],r.d[0]*2U);
        r.a[0]=0x4e272;if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[1],value);
        am_swap(r.d[0]);r.d[2]=2;r.d[3]=2;am_word(r.d[0],0x7243);r.pc=0x4e30c;return true;
    case 0x4e30c:return am_call(c,0x35f0,0x4e312);
    case 0x4e312:
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);am_word(r.d[0],r.d[0]&15U);r.a[0]=0x4e272;
        am_word(r.d[0],r.d[0]*2U);if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[1],value);
        r.d[2]=2;r.d[3]=2;am_word(r.d[0],0x7283);r.pc=0x35f0;return true;
    case 0x8cda:
        am_word(r.d[0],(r.d[0]&255U)<<4);r.a[1]=0x104d92;r.a[2]=am_index(r.a[1],r.d[0]);
        if(!am_read(c,r.a[2]+8U,2,value))return false;if(!value)return am_return(c);
        if((r.d[2]&255U)>=32U)r.d[2]=32;
        if(!am_read(c,r.a[2]+12U,2,value))return false;
        if((r.d[1]&65535U)!=value) {
            if(!am_write(c,r.a[2]+12U,2,r.d[1]) || !am_write(c,r.a[2]+14U,1,r.d[2]) || !dirty(c))return false;
            return am_return(c);
        }
        if(!am_read(c,r.a[2]+14U,1,value))return false;
        if((r.d[2]&255U)!=value) {
            if(!am_write(c,r.a[2]+14U,1,r.d[2]) || !am_read(c,r.a[2]+10U,2,value))return false;
            if((r.d[1]&65535U)!=value && !dirty(c))return false;
        }
        return am_return(c);
    case 0x35f0:r.a[4]=0x3c0000;r.pc=0x35f6;return true;
    case 0x35f6:
        am_word(r.d[7],r.d[0]);am_swap(r.d[7]);am_word(r.d[7],r.d[1]);am_word(r.d[6],r.d[3]);r.pc=0x35fe;return true;
    case 0x35fe:
        if(r.d[7]>=0x75000000U)return am_error(c,"unsupported original rectangle TRAP15");
        if(!video(c,4,r.d[7]))return false;r.d[7]+=0x10000U;am_byte(r.d[7],r.d[7]+0x10U);am_word(r.d[6],r.d[6]-1U);
        r.pc=(r.d[6]&65535U)?0x35fe:0x361a;return true;
    case 0x361a:
        am_byte(r.d[1],r.d[1]+1U);am_word(r.d[0],r.d[0]+0x20U);am_word(r.d[2],r.d[2]-1U);
        r.pc=(r.d[2]&65535U)?0x35f6:0x3624;return true;
    case 0x3624:
        if(!video(c,2,0x8200))return false;return am_return(c);
    case 0x4e330:case 0x4847a:case 0x8cf2:case 0x8d32:case 0x3628:return am_return(c);
    default:return am_error(c,"unsupported animation HUD PC");
    }
}
}
