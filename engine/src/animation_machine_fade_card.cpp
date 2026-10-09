#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// SUBQ.W #1,7a(A6) and the following BEQ.W: Z is the WORD result only.
bool fade_timer(AnimationMachineContext& c,std::uint32_t zero_pc,std::uint32_t rts_pc) {
    std::uint32_t value=0;
    if(!am_read(c,c.s.a[6]+0x7aU,2,value))return false;value=(value-1U)&65535U;
    if(!am_write(c,c.s.a[6]+0x7aU,2,value))return false;c.s.pc=value?rts_pc:zero_pc;return true;
}
// MOVE.W #timer,7a(A6); MOVE.L #callback,(A6); execution falls into callback.
bool fade_arm(AnimationMachineContext& c,std::uint32_t timer,std::uint32_t callback) {
    if(!am_write(c,c.s.a[6]+0x7aU,2,timer) || !am_write(c,c.s.a[6],4,callback))return false;
    c.s.pc=callback;return true;
}
}
bool animation_fade_card_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x4804e:r.d[0]=0;r.d[1]=0;r.d[2]=0;am_word(r.d[3],0x40);r.pc=0x48058;return true;
    case 0x48058:return am_call(c,0x8c16,0x4805e);
    case 0x4805e:return fade_arm(c,0x80,0x4806a);
    case 0x4806a:return fade_timer(c,0x48074,0x48072);
    case 0x48074:r.d[0]=0xffffffe1U;r.d[1]=0xffffffe1U;r.d[2]=0xffffffe1U;am_word(r.d[3],0x20);r.pc=0x4807e;return true;
    case 0x4807e:return am_call(c,0x8c16,0x48084);
    case 0x48084:return fade_arm(c,0x20,0x48090);
    case 0x48090:return fade_timer(c,0x4809a,0x48098);
    case 0x4809a:return am_call(c,0xcaf0,0x480a0);
    case 0x480a0:return am_call(c,0xc364,0x480a6);
    case 0x480a6:
        if(!am_write(c,r.a[6],4,0x480ac))return false;r.pc=0x480ac;return true;
    case 0x480ac:
        if(!am_read(c,r.a[6]+0x62U,1,value))return false;r.pc=value?0x480b6:0x480b4;return true;
    case 0x480b6:r.pc=0x2a00;return true;
    case 0x48072:case 0x48098:case 0x480b4:case 0xc3b6:case 0xc3be:case 0x290c:case 0x2916:return am_return(c);
    case 0xc364:
        if(!am_push(c,4,r.a[6]) || !am_write(c,0x10fdc4,1,1) || !am_write(c,0x10fdce,2,0x268))return false;
        r.pc=0xc376;return true;
    // BIOS c00468 has no executor: only a caller stop there succeeds.
    case 0xc376:return am_call(c,0xc00468,0xc37c);
    case 0xc37c:
        if(!am_pop(c,4,value))return false;r.a[6]=value;r.pc=0xc37e;return true;
    case 0xc37e:r.a[5]=0x108000;r.pc=0xc384;return true;
    case 0xc384:
        if(!am_read(c,am_index(r.a[5],0x7dc6),1,value))return false;r.pc=value==0x80U?0xc3b8:0xc38e;return true;
    case 0xc38e:
        if(!am_write(c,r.a[6]+0x62U,1,0))return false; // CLR.B: one BYTE write at this layer.
        r.a[0]=0xc250;am_word(r.d[0],0);r.pc=0xc39c;return true;
    case 0xc39c:return am_call(c,0x28ae,0xc3a2);
    case 0xc3a2:
        if(!am_write(c,r.a[0]+0x76U,4,0xc188) || !am_write(c,r.a[0]+0x7aU,2,4) ||
           !am_write(c,r.a[0]+0x7cU,2,4))return false;
        r.pc=0xc3b6;return true;
    case 0xc3b8:
        if(!am_write(c,r.a[6]+0x62U,1,255))return false;r.pc=0xc3be;return true;
    case 0x28ae:r.a[5]=0x108000;r.pc=0x28b4;return true;
    case 0x28b4:
        if(!am_read(c,0x104ca0,2,value))return false;r.pc=(r.d[0]&65535U)>=value?0x290e:0x28be;return true;
    case 0x28be:r.pc=r.a[0]?0x28c6:0x290e;return true; // CMPA.W #0 sign-extends: full32-bit test.
    case 0x28c6:
        if(!am_push(c,4,r.a[0]) || !am_read(c,am_index(r.a[5],0xcc9c),4,value))return false;r.a[0]=value;
        if(!am_read(c,r.a[0]+8U,4,value) || !am_write(c,am_index(r.a[5],0xcc9c),4,value))return false;
        r.pc=0x28d2;return true;
    case 0x28d2:r.pc=r.a[0]?0x28da:0x28de;return true;
    case 0x28da:
        if(!am_read(c,am_index(r.a[5],0xcca0),2,value) ||
           !am_write(c,am_index(r.a[5],0xcca0),2,value-1U))return false;
        r.pc=0x28de;return true;
    case 0x28de:
        // Every operand is read at its own original instruction, after prior writes.
        if(!am_write(c,r.a[0]+0xcU,4,r.a[6]) || !am_read(c,r.a[6]+0x10U,2,value))return false;
        am_word(r.d[0],value+1U);
        if(!am_write(c,r.a[0]+0x10U,2,r.d[0]) || !am_read(c,r.a[6]+8U,4,value))return false;r.a[1]=value;
        if(!am_write(c,r.a[0]+4U,4,r.a[6]) || !am_write(c,r.a[0]+8U,4,r.a[1]) ||
           !am_write(c,r.a[1]+4U,4,r.a[0]) || !am_write(c,r.a[6]+8U,4,r.a[0]) ||
           !am_pop(c,4,value) || !am_write(c,r.a[0],4,value) ||
           !am_read(c,r.a[6]+0x6aU,1,value) || !am_write(c,r.a[0]+0x6aU,1,value))return false;
        r.pc=0x2908;return true;
    case 0x2908:r.carry=AnimationCarrySet;r.pc=0x290c;return true; // ORI #1,CCR
    case 0x290e:r.a[0]=am_index(r.a[5],0x8e98);r.carry=AnimationCarryClear;r.pc=0x2916;return true; // ANDI #fe,CCR
    case 0x2a00:return am_call(c,0x299c,0x2a02);
    case 0x2a02:
        if(!am_read(c,am_index(r.a[5],0xcca4),4,value))return false;r.a[7]=value;r.pc=0x2a06;return true;
    case 0x2a06:r.pc=0x2ac2;return true;
    case 0x2ab8:r.a[5]=0x108000;r.pc=0x2abe;return true;
    case 0x2abe:
        if(!am_read(c,r.a[6],4,value))return false;r.a[0]=value;r.pc=0x2ac0;return true;
    case 0x2ac0:
        if(r.a[0]&1U)return am_error(c,"animation fade card odd JSR target");
        return am_call(c,r.a[0],0x2ac2);
    case 0x2ac2:
        if(!am_read(c,r.a[6]+8U,4,value))return false;r.a[6]=value;r.pc=0x2ac6;return true;
    case 0x2ac6:r.pc=0x2ab8;return true;
    default:return am_error(c,"unsupported animation fade card PC");
    }
}
}
