#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool read_stage(AnimationMachineContext& c,std::uint32_t offset,unsigned int size,std::uint32_t& value) {
    return am_read(c,c.s.a[5]+offset,size,value);
}
bool write_stage(AnimationMachineContext& c,std::uint32_t offset,unsigned int size,std::uint32_t value) {
    return am_write(c,c.s.a[5]+offset,size,value);
}
bool return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
bool branch_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"transition caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
bool port_or_memory(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t value) {
    const std::uint32_t bus=address&0xffffffU;
    if((bus==0x3c0000U && (size==2 || size==4)) ||
        (bus==0x3c0004U && size==2) || (bus==0x300001U && size==1)) {
        VideoPortWrite port;port.address=bus;port.size=static_cast<std::uint8_t>(size);port.value=value;
        c.ports.push_back(port);return true;
    }
    return am_write(c,address,size,value);
}
}
bool animation_transition_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x47d24:return am_call(c,0x4e216,0x47d2a);
    case 0x47d2a:return branch_carry(c,0x47d3e,0x47d2e);
    case 0x47d2e:return am_call(c,0xbee,0x47d34);
    case 0x47d34:return branch_carry(c,0x47d38,0x47d3e);
    case 0x47d38:r.d[0]=0;r.pc=0x47f4a;return true;
    case 0x47d46:
        if(!read_stage(c,0x5681,1,value))return false;
        if(value&128U) {r.pc=0x47d60;return true;}
        r.d[0]=1;if(!read_stage(c,0x5684,1,value))return false;am_byte(r.d[0],r.d[0]&value);
        r.pc=(r.d[0]&255U)?0x47d58:0x47d5c;return true;
    case 0x47d58:return am_call(c,0x477ac,0x47d5c);
    case 0x47d5c:r.pc=0x477ee;return true;
    case 0x47d60:
        if(!read_stage(c,0x568e,1,value))return false;
        if(!value) {r.pc=0x47d72;return true;}
        if(!read_stage(c,0x5683,1,value))return false;r.pc=(value&1U)?0x47da4:0x47d72;return true;
    case 0x47d72:
        if(!read_stage(c,0x5688,2,value))return false;am_word(r.d[0],value);
        r.pc=value?0x47d7a:0x47da0;return true;
    case 0x47d7a:
        if(!read_stage(c,0x568a,2,value))return false;r.pc=value?0x47d9c:0x47d82;return true;
    case 0x47d82:
        if(!read_stage(c,0x5686,2,value))return false;r.pc=value==(r.d[0]&65535U)?0x47d98:0x47d8a;return true;
    case 0x47d8a:
        if(!write_stage(c,0x5686,2,r.d[0]) || !write_stage(c,0x5688,2,0))return false;
        r.pc=0x47d92;return true;
    case 0x47d92:return am_call(c,0x3af8,0x47d98);
    case 0x47d98:r.pc=0x47da0;return true;
    case 0x47d9c:
        if(!read_stage(c,0x568a,2,value) || !write_stage(c,0x568a,2,value-1U))return false;
        r.pc=0x47da0;return true;
    case 0x47da0:r.pc=0x480bc;return true;
    case 0x4e216:
        if(!am_read(c,r.a[5]-0x75bcU,1,value))return false;am_byte(r.d[0],value);
        if(value!=0U && value!=5U)return return_carry(c,AnimationCarryClear);
        // The first condition controls whether the second BYTE is reached.
    case 0x4e22e:
        if(!am_read(c,r.a[5]-0x74f8U,1,value))return false;am_byte(r.d[0],value);
        return return_carry(c,(value==0U || value==5U)?AnimationCarrySet:AnimationCarryClear);
    case 0x4e242:case 0xc24:return return_carry(c,AnimationCarryClear);
    case 0x4e248:case 0xc30:return return_carry(c,AnimationCarrySet);
    case 0x4e246:case 0x4e24c:case 0xc28:case 0xc34:case 0x35ee:return am_return(c);
    case 0xbee:
        if(!am_read(c,0x10f004,1,value))return false;am_byte(r.d[0],value);
        if(!am_write(c,0x10f004,1,0))return false;r.a[0]=0x10fdb6;
        if(!am_read(c,r.a[0],1,value))return false;++r.a[0];am_byte(r.d[1],value);
        if(value!=1U && value!=2U) {
            if(!am_read(c,r.a[0],1,value))return false;++r.a[0];am_byte(r.d[1],value);
        }
        if(value!=1U && value!=2U)return return_carry(c,AnimationCarryClear);
        // Actual restore precedes the ORI CCR and the live RTS read.
    case 0xc2a:
        if(!am_write(c,0x10f004,1,r.d[0]))return false;return return_carry(c,AnimationCarrySet);
    case 0x477ac:
        am_word(r.d[0],0x7162);am_word(r.d[1],0xff);am_word(r.d[2],0x12);am_word(r.d[3],8);
    case 0x477bc:r.pc=0x35a2;return true;
    case 0x35a2:
        if(!port_or_memory(c,0x300001,1,r.d[0]&255U))return false;
    case 0x35a8:r.a[4]=0x3c0000;r.pc=0x35ae;return true;
    case 0x35ae:r.pc=(r.d[2]&65535U)?0x35b4:0x35e0;return true;
    case 0x35b4:
        am_word(r.d[7],r.d[0]);am_swap(r.d[7]);am_word(r.d[7],r.d[1]);am_word(r.d[6],r.d[3]);
        // The following BEQ consumes this MOVE.W's Z, not arbitrary entry flags.
        r.pc=(r.d[6]&65535U)?0x35c0:0x35d8;return true;
    case 0x35c0:
        if(r.d[7]>=0x75000000U)return am_error(c,"unsupported original fill TRAP15");
        if(!port_or_memory(c,r.a[4],4,r.d[7]))return false;
        r.d[7]+=0x10000U;am_word(r.d[6],r.d[6]-1U);
        // BRA/BEQ at35d6/35bc consumes the actual SUBQ.W result.
        r.pc=(r.d[6]&65535U)?0x35c0:0x35d8;return true;
    case 0x35d8:
        am_word(r.d[0],r.d[0]+0x20U);am_word(r.d[2],r.d[2]-1U);r.pc=0x35ae;return true;
    case 0x35e0:
        if(!port_or_memory(c,0x3c0004,2,0) || !port_or_memory(c,r.a[4],4,0x82000000U))return false;
        return am_return(c);
    default:return am_error(c,"unsupported animation transition PC");
    }
}
}
