#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool cleanup_branch(AnimationMachineContext& c,std::uint32_t clear,std::uint32_t set) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"cleanup caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear:set;return true;
}
bool cleanup_coordinate(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[5]=0x108000;
    if(!am_read(c,r.a[0]+0x14U,4,r.d[2]) || !am_read(c,r.a[0]+0x18U,4,r.d[3]) ||
       !am_read(c,r.a[0]+0x10U,4,r.a[1]) || !am_read(c,r.a[0],4,r.d[0]) ||
       !am_read(c,r.a[0]+4U,4,r.d[1]))return false;
    r.d[7]=0;
    if(r.a[1]) {
        if(!am_read(c,r.a[1]+0x14U,4,r.d[4]) || !am_read(c,r.a[1]+0x18U,4,r.d[5]))return false;
        am_word(r.d[6],r.d[1]);
        const std::uint32_t y=(r.d[6]&65535U)+(r.d[5]&65535U);am_word(r.d[6],y);
        r.d[7]=(y>>16)&1U;
        am_word(r.d[6],r.d[0]);
        const std::uint32_t x=(r.d[6]&65535U)+(r.d[4]&65535U);am_word(r.d[6],x);
        am_word(r.d[7],r.d[7]*2U+((x>>16)&1U));
        r.d[0]+=r.d[4];r.d[1]+=r.d[5];
        if(!am_read(c,r.a[1]+0x25U,1,value))return false;am_byte(r.d[7],r.d[7]|value);
    }
    if(!am_write(c,r.a[0]+0x25U,1,r.d[7]) || !am_write(c,r.a[0]+0x14U,4,r.d[0]) ||
       !am_write(c,r.a[0]+0x18U,4,r.d[1]))return false;
    if(!am_read(c,r.a[5]+0x5494U,1,value))return false;am_byte(r.d[5],value);
    if(!am_read(c,r.a[0]+0x24U,1,value))return false;am_byte(r.d[4],value);
    if(!(r.d[4]&255U)) {
        if(!am_write(c,r.a[0]+0x24U,1,r.d[5]) || !am_write(c,r.a[0]+0x1cU,4,r.d[0]) ||
           !am_write(c,r.a[0]+0x20U,4,r.d[1]))return false;
    } else if((r.d[5]&255U)!=(r.d[4]&255U)) {
        if(!am_write(c,r.a[0]+0x24U,1,r.d[5]) || !am_write(c,r.a[0]+0x1cU,4,r.d[2]) ||
           !am_write(c,r.a[0]+0x20U,4,r.d[3]))return false;
    }
    return am_return(c);
}
}
bool animation_cleanup_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x47fe4:return am_call(c,0x477c2,0x47fe8);
    case 0x477c2:return am_call(c,0x2a0a,0x477c8);
    case 0x477c8:r.a[0]=0x100bf4;return am_call(c,0x2a84,0x477d4);
    case 0x477d4:r.d[0]=0;r.pc=0x477d6;return true;
    case 0x477d6:return am_call(c,0x8bbc,0x477dc);
    case 0x477dc:return am_call(c,0x3dce,0x477e2);
    case 0x477e2:return am_return(c);
    case 0x8bbc:
        if(!am_write(c,r.a[5]-0x214U,1,r.d[0]))return false;r.pc=0x8bc0;return true;
    case 0x8bc0:case 0x3de4:return am_return(c);
    case 0x3dce:
        if(!am_read(c,r.a[5]-0x326fU,1,value) || !am_write(c,r.a[5]-0x326fU,1,value&~16U))return false;
        r.a[0]=0x3dcc;
        if(!am_write(c,0x100006,4,r.a[0]) || !am_write(c,0x10000a,4,r.a[0]))return false;
        r.pc=0x3de4;return true;
    case 0x271c:return am_call(c,0x8eb6,0x2722);
    case 0x2722:return am_call(c,0x43dcc,0x2728);
    case 0x2728:return am_call(c,0xc3dc,0x272e);
    case 0x272e:
        r.d[0]=0;r.d[1]=0xffffffffU;
        if(!am_write(c,r.a[0]+0x15U,1,0) || !am_write(c,r.a[0]+0x61U,1,0) ||
           !am_write(c,r.a[0]+0x62U,1,0) || !am_write(c,r.a[0]+0x63U,1,0) ||
           !am_write(c,r.a[0]+0x12U,1,r.d[1]) || !am_write(c,r.a[0]+0x13U,1,r.d[1]) ||
           !am_write(c,r.a[0]+0x1eU,2,r.d[1]))return false;
        r.a[0]+=0x76U;r.d[0]=0;
        for(unsigned int i=0;i<19;++i){if(!am_write(c,r.a[0],4,r.d[0]))return false;r.a[0]+=4U;}
        if(!am_write(c,r.a[0],2,r.d[0]))return false;r.a[0]-=0xc2U;r.pc=0x2780;return true;
    case 0x2780:case 0x278e:return am_return(c);
    case 0x2782:return am_call(c,0x8ff4,0x2788);
    case 0x2788:return am_call(c,0xc3fa,0x278e);
    case 0x287e:
        if(!am_read(c,r.a[6]+8U,4,r.a[0]) || !am_read(c,r.a[6]+0x10U,2,value))return false;
        am_word(r.d[0],value);
        if(!am_read(c,r.a[0]+0x10U,2,value))return false;
        r.carry=(r.d[0]&65535U)<value?AnimationCarrySet:AnimationCarryClear;r.pc=0x288a;return true;
    case 0x288a:return am_return(c);
    case 0x299c: {
        r.a[5]=0x108000;
        VideoPortWrite p;p.size=1;p.address=0x300001;p.value=r.d[0]&255U;c.ports.push_back(p);
        r.pc=0x29a8;return true;
    }
    case 0x29a8:return am_call(c,0x2782,0x29ac);
    case 0x29ac:
        if(!am_write(c,r.a[6],4,0x270e) || !am_read(c,r.a[6]+0x10U,2,value))return false;
        r.pc=value?0x29c0:0x29ba;return true;
    case 0x29ba:r.a[0]=r.a[6];r.pc=0x271c;return true;
    case 0x29c0:return am_call(c,0x287e,0x29c4);
    case 0x29c4:return cleanup_branch(c,0x29c8,0x29fe);
    case 0x29c8:r.a[0]=r.a[6];return am_call(c,0x271c,0x29ce);
    case 0x29ce:
        if(!am_read(c,r.a[6]+4U,4,r.a[0]) || !am_read(c,r.a[6]+8U,4,r.a[1]) ||
           !am_write(c,r.a[1]+4U,4,r.a[0]) || !am_write(c,r.a[0]+8U,4,r.a[1]) ||
           !am_read(c,r.a[5]-0x3364U,4,value) || !am_write(c,r.a[6]+8U,4,value) ||
           !am_write(c,r.a[5]-0x3364U,4,r.a[6]) || !am_read(c,r.a[5]-0x3360U,2,value) ||
           !am_write(c,r.a[5]-0x3360U,2,value+1U))return false;
        r.a[6]=r.a[0];
        if(!am_read(c,r.a[6],4,value))return false;
        if(value!=0x270eU){r.pc=0x29fe;return true;}
        if(!am_read(c,r.a[6]+0x10U,2,value))return false;r.pc=value?0x29c0:0x29fe;return true;
    case 0x29fe:return am_return(c);
    case 0x2a0a:
        if(!am_read(c,r.a[6]+0x10U,2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,r.a[6]+8U,4,r.a[6]))return false;r.pc=0x2a12;return true;
    case 0x2a12:
        if(!am_read(c,r.a[6]+0x10U,2,value))return false;
        r.carry=(r.d[0]&65535U)<value?AnimationCarrySet:AnimationCarryClear;r.pc=0x2a16;return true;
    case 0x2a16:return cleanup_branch(c,0x2a1e,0x2a1a);
    case 0x2a1a:return am_call(c,0x299c,0x2a1c);
    case 0x2a1c:r.pc=0x2a0a;return true;
    case 0x2a1e:
        if(!am_read(c,r.a[6]+4U,4,r.a[6]))return false;return am_return(c);
    case 0x2a28:case 0x2a48:case 0x2a6c:case 0x2a90:
        if(!am_read(c,r.a[0]+0x10U,2,value))return false;
        if(value)return am_error(c,"animation cleanup original TRAP15: nonzero object type");
        r.pc=r.pc==0x2a28?0x2a34:r.pc==0x2a48?0x2a54:r.pc==0x2a6c?0x2a78:0x2a9c;return true;
    case 0x2a60:case 0x2a84:
        if(!am_read(c,r.a[6]+0x10U,2,value))return false;
        if(value)return am_error(c,"animation cleanup original TRAP15: nonzero parent type");
        r.pc=r.pc==0x2a60?0x2a6c:0x2a90;return true;
    case 0x2a34:
        if(!am_push(c,4,r.a[6]) || !am_push(c,4,r.a[1]) || !am_push(c,4,r.a[0]))return false;
        r.a[6]=r.a[0];r.pc=0x2a3c;return true;
    case 0x2a3c:return am_call(c,0x299c,0x2a40);
    case 0x2a40:
        if(!am_pop(c,4,r.a[0]))return false;r.pc=0x2a42;return true;
    case 0x2a42:
        if(!am_pop(c,4,value) || !am_write(c,r.a[0],4,value))return false;
        r.pc=0x2a44;return true;
    case 0x2a44:case 0x2a5c:case 0x2a80:case 0x2aa8:
        if(!am_pop(c,4,r.a[6]))return false;
        r.pc=r.pc==0x2a44?0x2a46:r.pc==0x2a5c?0x2a5e:r.pc==0x2a80?0x2a82:0x2aaa;return true;
    case 0x2a46:case 0x2a5e:case 0x2a82:case 0x2aaa:return am_return(c);
    case 0x2a54:case 0x2a78:case 0x2a9c: {
        const std::uint32_t next=r.pc==0x2a54?0x2a58:r.pc==0x2a78?0x2a7c:0x2aa0;
        if(!am_push(c,4,r.a[6]))return false;r.a[6]=r.a[0];r.pc=next;return true;
    }
    case 0x2a58:return am_call(c,0x299c,0x2a5c);
    case 0x2a7c:return am_call(c,0x2a0a,0x2a80);
    case 0x2aa0:return am_call(c,0x2a0a,0x2aa4);
    case 0x2aa4:return am_call(c,0x299c,0x2aa8);
    case 0x8ff4:
        r.d[7]=0;if(!am_read(c,r.a[6]+0x1dU,1,r.d[7]))return false;
        value=r.d[7]&65535U;am_word(r.d[7],value-1U);r.pc=value?0x9000:0x9030;return true;
    case 0x9000:r.a[1]=r.a[5]-0x326eU;r.pc=0x9004;return true;
    case 0x9004:
        r.d[0]=0;if(!am_read(c,am_index(r.a[6]+0x19U,r.d[7]),1,r.d[0]))return false;
        am_word(r.d[0],r.d[0]<<4);r.a[2]=am_index(r.a[1],r.d[0]);
        if(!am_read(c,r.a[2]+8U,2,value))return false;am_word(r.d[1],value);
        if(value && value!=65535U){
            if(!am_read(c,r.a[2]+8U,2,value))return false;
            value=(value-1U)&65535U;if(!am_write(c,r.a[2]+8U,2,value))return false;
            r.pc=value?0x902c:0x9028;
        }else r.pc=0x902c;
        return true;
    case 0x9028:return am_call(c,0x8e4a,0x902c);
    case 0x902c:
        value=r.d[7]&65535U;am_word(r.d[7],value-1U);r.pc=value?0x9004:0x9030;return true;
    case 0x9030:
        if(!am_write(c,r.a[6]+0x1dU,1,0))return false;r.pc=0x9036;return true;
    case 0x9036:case 0x8e80:case 0x8ebc:return am_return(c);
    case 0x8eb6:
        if(!am_write(c,r.a[0]+0x1dU,1,0))return false;r.pc=0x8ebc;return true;
    case 0x8e4a:
        if(!am_read(c,r.a[2],2,value))return false;am_word(r.d[2],value);
        if(!am_read(c,r.a[2]+2U,2,value))return false;am_word(r.d[3],value);
        if(!am_write(c,am_index(r.a[1],r.d[3]),2,r.d[2]) || !am_write(c,am_index(r.a[1],r.d[2])+2U,2,r.d[3]))return false;
        am_word(r.d[2],0x1000);
        if(!am_read(c,am_index(r.a[1],r.d[2]),2,value))return false;am_word(r.d[3],value);
        if(!am_write(c,r.a[2]+2U,2,r.d[2]) || !am_write(c,r.a[2],2,r.d[3]) ||
           !am_write(c,am_index(r.a[1],r.d[3])+2U,2,r.d[0]) || !am_write(c,am_index(r.a[1],r.d[2]),2,r.d[0]) ||
           !am_write(c,r.a[2]+0xaU,2,65535) || !am_write(c,r.a[2]+0xcU,2,65535) ||
           !am_write(c,r.a[2]+0xfU,1,2))return false;
        r.pc=0x8e80;return true;
    case 0x43dcc:r.a[0]+=0x2eU;return am_call(c,0x43dda,0x43dd4);
    case 0x43dd4:r.a[0]-=0x2eU;return am_return(c);
    case 0x43dd8:case 0x43e02:case 0x43e90:case 0x43ea2:return am_return(c);
    case 0x43dda: {
        r.d[0]=0;
        const unsigned int offsets[]={0x10,0,4,8,0xc,0x14,0x18,0x1c,0x20};
        for(unsigned int i=0;i<9;++i)if(!am_write(c,r.a[0]+offsets[i],4,0))return false;
        if(!am_write(c,r.a[0]+0x24U,2,0))return false;r.pc=0x43e02;return true;
    }
    case 0x43e38:return cleanup_coordinate(c);
    case 0xc3dc:
        if(!am_write(c,r.a[0]+0x64U,4,0) || !am_write(c,r.a[0]+0x6eU,2,0x40))return false;r.pc=0xc3e6;return true;
    case 0xc3e6:return am_call(c,0x4aa06,0xc3ec);
    case 0xc3ec:return am_call(c,0xe90ca,0xc3f2);
    case 0xc3f2:return am_call(c,0x46eec,0xc3f8);
    case 0xc3f8:case 0xc400:case 0x4aa2e:case 0xe90d6:case 0x46ef2:return am_return(c);
    case 0xc3fa:return am_call(c,0x46ef4,0xc400);
    case 0x4aa06:
        r.d[0]=0;
        if(!am_write(c,r.a[0]+0x54U,2,0) || !am_write(c,r.a[0]+0x56U,4,0) || !am_write(c,r.a[0]+0x5eU,1,0) ||
           !am_write(c,r.a[0]+0x5aU,2,65535) || !am_write(c,r.a[0]+0x60U,1,0) ||
           !am_write(c,r.a[0]+0x17U,1,255) || !am_write(c,r.a[0]+0x6dU,1,255) ||
           !am_write(c,r.a[0]+0x72U,4,0))return false;r.pc=0x4aa2e;return true;
    case 0xe90ca:
        if(!am_write(c,r.a[0]+0x6aU,1,0) || !am_write(c,r.a[0]+0x6bU,1,255))return false;r.pc=0xe90d6;return true;
    case 0x46eec:
        if(!am_write(c,r.a[0]+0x6cU,1,255))return false;r.pc=0x46ef2;return true;
    case 0x46ef4:
        r.d[0]=0;if(!am_read(c,r.a[6]+0x6cU,1,r.d[0]))return false;
        if(r.d[0]&128U){r.pc=0x46f2c;return true;}
        if((r.d[0]&65535U)>=8U)return am_error(c,"animation cleanup original TRAP15: coordinate index");
        r.pc=0x46f08;return true;
    case 0x46f08:
        r.d[0]=(r.d[0]&65535U)*0x2cU;r.a[0]=am_index(r.a[5]+0x54e6U,r.d[0]);
        if(!am_write(c,r.a[0]+0x26U,2,65535) || !am_write(c,r.a[0]+0x2aU,2,2) ||
           !am_write(c,r.a[6]+0x6cU,1,255))return false;r.pc=0x46f26;return true;
    case 0x46f26:return am_call(c,0x43e38,0x46f2c);
    case 0x46f2c:return am_return(c);
    default:return am_error(c,"unsupported animation machine PC");
    }
}
}
