#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool screen_long(AnimationMachineContext& c,std::uint32_t value) {
    if((c.s.a[4]&0xffffffU)!=0x3c0000U)return am_write(c,c.s.a[4],4,value);
    VideoPortWrite port;port.address=0x3c0000;port.size=4;port.value=value;c.ports.push_back(port);return true;
}
void screen_dbf(AnimationMachineState& r) {
    am_word(r.d[7],r.d[7]-1U);r.pc=(r.d[7]&65535U)==65535U?0xcabc:0xcab0;
}
}
bool animation_screen_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x47fca:return am_call(c,0xcaf0,0x47fd0);
    case 0x47fd0:
        if(!am_write(c,r.a[6]+0x7aU,2,32) || !am_write(c,r.a[6],4,0x47fdc))return false;
        r.pc=0x47fdc;return true;
    case 0x47fdc:
        if(!am_read(c,r.a[6]+0x7aU,2,value) || !am_write(c,r.a[6]+0x7aU,2,value-1U))return false;
        r.pc=((value-1U)&65535U)?0x480bc:0x47fe4;return true;
    case 0xca9e:r.a[4]=0x3c0000;r.pc=0xcaa4;return true;
    case 0xcaa4:r.d[0]=0;am_word(r.d[0],0x7500);am_swap(r.d[0]);am_word(r.d[7],0x2ff);r.pc=0xcab0;return true;
    case 0xcab0:
        if(!screen_long(c,r.d[0]))return false;r.d[0]+=0x10000U;screen_dbf(r);return true;
    case 0xcab8:screen_dbf(r);return true; // DBRA itself preserves CCR.
    case 0xcabc:
        r.d[1]=0;am_word(r.d[0],0x7500);am_swap(r.d[0]);am_word(r.d[0],0x200);r.pc=0xcac8;return true;
    case 0xcac8:case 0xcad0:case 0xcad8:case 0xcae0: {
        const std::uint32_t next=r.pc==0xcac8?0xcad0:r.pc==0xcad0?0xcad8:r.pc==0xcad8?0xcae0:0xcae8;
        if(!screen_long(c,r.d[0]))return false;r.d[0]+=0x200000U;r.pc=next;return true;
    }
    case 0xcae8:
        am_word(r.d[0],0xff02);if(!screen_long(c,r.d[0]))return false;r.pc=0xcaee;return true;
    case 0xcaee:case 0xcb62:return am_return(c);
    case 0xcaf0:return am_call(c,0xca9e,0xcaf2);
    case 0xcaf2:r.a[4]=0x3c0000;r.pc=0xcaf8;return true;
    case 0xcaf8:
        am_word(r.d[0],0x7021);am_word(r.d[1],0xff);am_word(r.d[2],0x26);am_word(r.d[3],0x1e);r.pc=0xcb08;return true;
    case 0xcb08:return am_call(c,0x35a2,0xcb0e);
    case 0xcb0e:
        am_word(r.d[0],0x701f);am_word(r.d[1],0x7000);am_word(r.d[2],0x28);r.d[3]=1;r.pc=0xcb1c;return true;
    case 0xcb1c:return am_call(c,0x35a2,0xcb22);
    case 0xcb22:
        am_word(r.d[0],0x7000);am_word(r.d[1],0x7000);am_word(r.d[2],0x28);r.d[3]=1;r.pc=0xcb30;return true;
    case 0xcb30:return am_call(c,0x35a2,0xcb36);
    case 0xcb36:
        am_word(r.d[0],0x7000);am_word(r.d[1],0x7000);r.d[2]=1;am_word(r.d[3],0x20);r.pc=0xcb44;return true;
    case 0xcb44:return am_call(c,0x35a2,0xcb4a);
    case 0xcb4a:
        am_word(r.d[0],0x74e0);am_word(r.d[1],0x7000);r.d[2]=1;am_word(r.d[3],0x20);r.pc=0xcb58;return true;
    case 0xcb58:return am_call(c,0x35a2,0xcb5e);
    case 0xcb5e:
        if(!am_write(c,r.a[5]-0x769aU,1,0))return false;r.pc=0xcb62;return true;
    default:return am_error(c,"unsupported animation screen PC");
    }
}
}
