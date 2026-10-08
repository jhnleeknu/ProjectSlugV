#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool branch_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"readiness caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
bool return_carry(AnimationMachineContext& c,AnimationCarryState carry) {
    c.s.carry=carry;return am_return(c);
}
}
bool animation_readiness_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x47d20:r.pc=0x47d3e;return true;
    case 0x47d3e:return am_call(c,0x4847c,0x47d42);
    case 0x47d42:return branch_carry(c,0x47d72,0x47d46);
    case 0x4847c:r.d[0]=0;r.pc=0x4847e;return true;
    case 0x4847e:return am_call(c,0x1bdde,0x48484);
    case 0x48484:return branch_carry(c,0x484ae,0x48488);
    case 0x48488:r.d[0]=1;r.pc=0x4848a;return true;
    case 0x4848a:return am_call(c,0x1bdde,0x48490);
    case 0x48490:return branch_carry(c,0x484ae,0x48494);
    case 0x48494:
        if(!am_read(c,r.a[5]+0x5684U,1,value))return false;
        r.pc=value?0x484a8:0x4849c;return true;
    case 0x4849c:return am_call(c,0x4e166,0x484a2);
    case 0x484a2:r.pc=(r.d[0]&255U)?0x484a8:0x484ae;return true;
    case 0x484a8:case 0x1be2e:case 0x28a8:return return_carry(c,AnimationCarrySet);
    case 0x484ae:case 0x1be34:case 0x4df0a:return return_carry(c,AnimationCarryClear);
    case 0x484ac:case 0x484b2:case 0x1be32:case 0x1be38:
    case 0x28ac:case 0x4df0e:case 0x4df18:case 0x4e184:return am_return(c);
    case 0x1bdde:
        r.a[0]=r.a[5]-0x7348U;am_word(r.d[0],r.d[0]&1U);
        if(r.d[0]&65535U)r.a[0]=r.a[5]-0x7258U;
        r.pc=0x1bdee;return true;
    case 0x1bdee:return am_call(c,0x289e,0x1bdf4);
    case 0x1bdf4:return branch_carry(c,0x1be2e,0x1bdf8);
    case 0x1bdf8:
        if(!am_read(c,r.a[0]+0xa8U,1,value))return false;
        r.pc=(value&16U)?0x1be2e:0x1be02;return true; // BTST changes Z, preserving C.
    case 0x1be02:
        if(!am_read(c,r.a[0]+0x61U,1,value))return false;
        r.pc=(value&128U)?0x1be34:0x1be0c;return true;
    case 0x1be0c:return am_call(c,0x4dee2,0x1be12);
    case 0x1be12:return branch_carry(c,0x1be2e,0x1be16);
    case 0x1be16:
        value=r.d[1]&255U;r.pc=(value==3U||value==4U||value==5U)?0x1be34:0x1be2e;return true;
    case 0x289e:
        if(!am_read(c,r.a[0],4,value))return false;
        // Equal CMP.L clears C; every non-equal path executes original ORI CCR.
        return return_carry(c,value==0x270eU?AnimationCarryClear:AnimationCarrySet);
    case 0x4dee2:
        r.a[4]=r.a[5]+0x5d12U;am_word(r.d[0],r.d[0]&1U);
        if(r.d[0]&65535U)r.a[4]=r.a[5]+0x5d18U;
        if(!am_read(c,r.a[4]+4U,2,value))return false;
        if(value&0x8000U)return return_carry(c,AnimationCarryClear);
        if(!am_read(c,r.a[4],1,value))return false;
        if(value!=1U&&value!=2U)return return_carry(c,AnimationCarryClear);
        // Actual MOVE.B and ORI sequence is shared with the direct entry below.
    case 0x4df10:
        if(!am_read(c,r.a[4]+2U,1,value))return false;am_byte(r.d[1],value);
        return return_carry(c,AnimationCarrySet);
    case 0x4e166:
        r.d[0]=0;
        if(!am_read(c,r.a[5]-0x75bcU,1,value))return false;
        if(value==2U)am_word(r.d[0],r.d[0]|1U);
        if(!am_read(c,r.a[5]-0x74f8U,1,value))return false;
        if(value==2U)am_word(r.d[0],r.d[0]|2U);
        return am_return(c); // C intentionally Unknown; parent consumes TST.B, not C.
    default:return am_error(c,"unsupported animation readiness PC");
    }
}
}
