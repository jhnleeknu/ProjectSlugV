#include "animation_machine_internal.h"
namespace ms5 {
namespace {
void watchdog(AnimationMachineContext& c) {
    VideoPortWrite p;p.address=0x300001;p.size=1;p.value=c.s.d[0]&255U;c.ports.push_back(p);
}
std::uint32_t signed12(std::uint32_t value) {
    value&=0xfffU;return (value&0x800U)?value|0xf000U:value;
}
}
bool animation_palette_bind_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x8da2:r.a[5]=0x108000;r.pc=0x8da8;return true;
    case 0x8da8:watchdog(c);r.pc=0x8dae;return true;
    case 0x8dae:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);
        r.pc=value==65535U?0x8e44:0x8db8;return true;
    case 0x8db8:r.a[1]=0x104d92;r.pc=0x8dbe;return true;
    case 0x8dbe:
        am_word(r.d[0],r.d[0]<<4);r.a[2]=am_index(r.a[1],r.d[0]);r.pc=0x8dc4;return true;
    case 0x8dc4:
        if(!am_read(c,r.a[0]+2U,2,value))return false;am_word(r.d[1],value);
        am_word(r.d[4],((value&255U)<<4)+4U);r.a[4]=am_index(r.a[1],r.d[4]);
        if(!am_read(c,r.a[4]+2U,2,value))return false;
        r.pc=value==(r.d[0]&65535U)?0x8dfe:0x8dde;return true;
    case 0x8dde:
        if(!am_read(c,r.a[2],2,value))return false;am_word(r.d[2],value);
        if(!am_read(c,r.a[2]+2U,2,value))return false;am_word(r.d[3],value);r.pc=0x8de4;return true;
    case 0x8de4:
        if(!am_write(c,am_index(r.a[1],r.d[3]),2,r.d[2]))return false;r.pc=0x8de8;return true;
    case 0x8de8:
        if(!am_write(c,am_index(r.a[1],r.d[2])+2U,2,r.d[3]))return false;r.pc=0x8dec;return true;
    case 0x8dec:
        if(!am_read(c,r.a[4]+2U,2,value))return false;am_word(r.d[3],value);r.pc=0x8df0;return true;
    case 0x8df0:
        if(!am_write(c,am_index(r.a[1],r.d[3]),2,r.d[0]))return false;r.pc=0x8df4;return true;
    case 0x8df4:
        if(!am_write(c,r.a[2]+2U,2,r.d[3]))return false;r.pc=0x8df8;return true;
    case 0x8df8:
        if(!am_write(c,r.a[2],2,r.d[4]))return false;r.pc=0x8dfa;return true;
    case 0x8dfa:
        if(!am_write(c,r.a[4]+2U,2,r.d[0]))return false;r.pc=0x8dfe;return true;
    case 0x8dfe:
        if(!am_write(c,r.a[2]+8U,2,65535))return false;
        r.pc=(r.d[1]&65535U)==65535U?0x8e0c:0x8e22;return true;
    case 0x8e0c:
        if(!am_write(c,r.a[2]+10U,2,65535))return false;r.pc=0x8e12;return true;
    case 0x8e12:
        if(!am_write(c,r.a[2]+12U,2,65535))return false;r.pc=0x8e18;return true;
    case 0x8e18:
        if(!am_write(c,r.a[2]+15U,1,2))return false;r.pc=0x8e36;return true;
    case 0x8e22:
        if(!am_write(c,r.a[2]+10U,2,r.d[1]))return false;r.pc=0x8e26;return true;
    case 0x8e26:
        if(!am_write(c,r.a[2]+12U,2,r.d[1]))return false;r.pc=0x8e2a;return true;
    case 0x8e2a:
        if(!am_read(c,r.a[0]+4U,1,value))return false;am_byte(r.d[0],value);r.d[0]|=128U;r.pc=0x8e32;return true;
    case 0x8e32:
        if(!am_write(c,r.a[2]+15U,1,r.d[0]))return false;r.pc=0x8e36;return true;
    case 0x8e36:
        r.a[0]+=6U;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);
        r.pc=value==65535U?0x8e44:0x8dbe;return true;
    case 0x8e44:r.a[0]+=2U;r.pc=0x8e48;return true;
    case 0x8e48:case 0x8eb4:case 0x16fec:case 0x17010:return am_return(c);
    case 0x8e82:watchdog(c);r.pc=0x8e88;return true;
    case 0x8e88:r.a[1]=0x104d92;r.a[2]=r.a[1];r.d[0]=0;am_word(r.d[7],255);r.pc=0x8e96;return true;
    case 0x8e96:
        if(!am_read(c,r.a[2]+8U,2,value))return false;r.pc=value==65535U?0x8ea0:0x8ea8;return true;
    case 0x8ea0:
        if(!am_write(c,r.a[2]+8U,2,0))return false;r.pc=0x8ea6;return true;
    case 0x8ea6:return am_call(c,0x8e4a,0x8ea8);
    case 0x8ea8:
        r.a[2]+=16U;am_word(r.d[0],r.d[0]+16U);value=r.d[7]&65535U;am_word(r.d[7],value-1U);
        r.pc=value?0x8e96:0x8eb4;return true;
    case 0xe7bf4:return am_call(c,0x8e82,0xe7bfa);
    case 0xe7bfa:r.a[0]=0xe7b58;r.pc=0xe7bfe;return true;
    case 0xe7bfe:return am_call(c,0x8da2,0xe7c04);
    case 0xe7c04:am_word(r.d[0],6);am_word(r.d[1],1);am_word(r.d[2],12);r.pc=0xe7c10;return true;
    case 0xe7c10:r.pc=0x8cda;return true;
    case 0xe7c36:return am_call(c,0xe7bf4,0xe7c3a);
    case 0xe7c3a:r.a[0]=0xe7bda;r.pc=0xe7c3e;return true;
    case 0xe7c3e:r.pc=0x8da2;return true;
    case 0x47ff2:return am_call(c,0xe7c36,0x47ff8);
    case 0x47ff8:am_word(r.d[0],0x3c);r.pc=0x47ffc;return true;
    case 0x47ffc:
        if(!am_write(c,r.a[5]-0x7ff0U,2,0))return false;r.pc=0x48002;return true;
    case 0x48002:
        if(!am_write(c,0x2ffff2,2,0x1000))return false;r.pc=0x4800a;return true;
    case 0x4800a:
        if(!am_write(c,0x2ffff0,2,0))return false;r.pc=0x48012;return true;
    case 0x48012:
        if(!am_read(c,0x20000c,4,r.a[0]))return false;r.pc=0x48018;return true;
    case 0x48018:am_word(r.d[0],r.d[0]<<2);r.pc=0x4801a;return true;
    case 0x4801a:
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;r.pc=0x4801e;return true;
    case 0x4801e:return am_call(c,0x8da2,0x48024);
    case 0x48024:r.a[0]=0x10d256;r.pc=0x4802a;return true;
    case 0x4802a:return am_call(c,0x16fac,0x48030);
    case 0x48030:r.a[1]=0x480f2;r.pc=0x48034;return true;
    case 0x48034:r.a[2]=0;r.pc=0x48038;return true;
    case 0x48038:r.d[0]=0;r.pc=0x4803a;return true;
    case 0x4803a:r.d[1]=31;r.pc=0x4803c;return true;
    case 0x4803c:return am_call(c,0x16ff8,0x48042);
    case 0x16fac:return am_call(c,0x43dda,0x16fb2);
    case 0x16fb2:case 0x16fb8:
        if(!am_write(c,r.a[0]+(r.pc==0x16fb2?0x2cU:0x2dU),1,0))return false;
        r.pc=r.pc==0x16fb2?0x16fb8:0x16fbe;return true;
    case 0x16fbe:
        if(!am_write(c,r.a[0]+0x2eU,4,0))return false;r.pc=0x16fc6;return true;
    case 0x16fc6:case 0x16fcc:
        if(!am_write(c,r.a[0]+(r.pc==0x16fc6?0x32U:0x34U),2,0))return false;
        r.pc=r.pc==0x16fc6?0x16fcc:0x16fd2;return true;
    case 0x16fd2:
        if(!am_write(c,r.a[0]+0x36U,4,0xffffffffU))return false;r.pc=0x16fda;return true;
    case 0x16fda:case 0x16fe0:
        if(!am_write(c,r.a[0]+(r.pc==0x16fda?0x28U:0x2aU),2,0x100))return false;
        r.pc=r.pc==0x16fda?0x16fe0:0x16fe6;return true;
    case 0x16fe6:
        if(!am_write(c,r.a[0]+0x7aU,1,6))return false;r.pc=0x16fec;return true;
    case 0x16ff8:
        if(!am_write(c,r.a[0]+0x2eU,4,r.a[1]))return false;r.pc=0x16ffc;return true;
    case 0x16ffc:
        if(!am_write(c,r.a[0]+0x36U,4,r.a[2]))return false;r.pc=0x17000;return true;
    case 0x17000:
        am_word(r.d[0],signed12(r.d[0]));am_word(r.d[1],signed12(r.d[1]));r.pc=0x17008;return true;
    case 0x17008:
        if(!am_write(c,r.a[0]+0x32U,2,r.d[0]))return false;r.pc=0x1700c;return true;
    case 0x1700c:
        if(!am_write(c,r.a[0]+0x34U,2,r.d[1]))return false;r.pc=0x17010;return true;
    default:return am_error(c,"unsupported animation palette bind PC");
    }
}
}
