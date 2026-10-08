#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool scene_long(AnimationMachineContext& c,std::uint32_t address,std::uint32_t value) {
    if((address&0xffffffU)!=0x3c0000U)return am_write(c,address,4,value);
    VideoPortWrite p;p.size=4;p.address=0x3c0000;p.value=value;c.ports.push_back(p);return true;
}
bool scene_watchdog(AnimationMachineContext& c,std::uint32_t value) {
    VideoPortWrite p;p.size=1;p.address=0x300001;p.value=value&255U;c.ports.push_back(p);return true;
}
bool scene_movem(AnimationMachineContext& c) {
    std::uint32_t value=0;
    if(!am_read(c,c.s.a[0],2,value))return false;c.s.d[0]=am_extend_word(value);
    if(!am_read(c,c.s.a[0]+2U,2,value))return false;c.s.d[1]=am_extend_word(value);return true;
}
void scene_dbf(AnimationMachineState& r,unsigned int reg,std::uint32_t again,std::uint32_t end) {
    am_word(r.d[reg],r.d[reg]-1U);r.pc=(r.d[reg]&65535U)==65535U?end:again;
}
}
bool animation_scene_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    // The original unrolled clear has one live WORD access at each boundary.
    if(r.pc>=0x182da && r.pc<=0x18318 && !(r.pc&1U)) {
        if(!am_write(c,r.a[1],2,r.d[0]))return false;r.a[1]+=2U;r.pc+=2U;return true;
    }
    switch(r.pc) {
    case 0x47fe8:r.a[0]=0x48108;r.pc=0x47fec;return true;
    case 0x47fec:return am_call(c,0x43ffc,0x47ff2);
    case 0x43ffc:r.a[5]=0x108000;r.pc=0x44002;return true;
    case 0x44002:if(!am_push(c,4,r.a[0]))return false;r.pc=0x44004;return true;
    case 0x44004:return am_call(c,0x43f3e,0x44008);
    case 0x44008:if(!am_pop(c,4,r.a[0]))return false;r.pc=0x4400a;return true;
    case 0x4400a:r.pc=r.a[0]==0?0x44086:0x44012;return true;
    case 0x44012:
        if(!am_write(c,r.a[5]+0x549aU,1,255) || !am_read(c,r.a[0]+2U,2,value))return false;
        am_word(r.d[0],value);r.pc=value==0?0x44032:value==3?0x44086:0x4402c;return true;
    case 0x4402c:return am_call(c,0x43f5c,0x44030);
    case 0x44030:r.pc=0x44012;return true;
    case 0x44032:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]=am_index(r.a[0],value);r.d[7]=0;
        if(!am_write(c,r.a[5]+0x549aU,1,0) || !scene_movem(c))return false;r.pc=0x44040;return true;
    case 0x44040:r.pc=(r.d[1]&65535U)==3?0x44072:(r.d[1]&65535U)<3?0x44066:0x4404c;return true;
    case 0x4404c:case 0x43f7c:case 0x43fb6:case 0x43fde:return am_error(c,"animation scene TRAP15");
    case 0x44066:
        if(!am_push(c,4,r.a[0]))return false;am_word(r.d[7],r.d[7]+1U);r.a[0]=am_index(r.a[0],r.d[0]);
        if(!scene_movem(c))return false;r.pc=0x44040;return true;
    case 0x44072:r.pc=(r.d[7]&65535U)==0?0x44086:0x44078;return true;
    case 0x44078:if(!am_pop(c,4,r.a[0]))return false;r.pc=0x4407a;return true;
    case 0x4407a:am_word(r.d[7],r.d[7]-1U);r.pc=0x4407c;return true;
    case 0x4407c:if(!am_push(c,2,r.d[7]))return false;r.pc=0x4407e;return true;
    case 0x4407e:return am_call(c,0x43f5c,0x44082);
    case 0x44082:
        if(!am_pop(c,2,value))return false;am_word(r.d[7],value);
        // BRA/BEQ consumes the Z written by this actual MOVE.W, not an incoming Z.
        r.pc=(r.d[7]&65535U)==0?0x44086:0x44078;return true;
    case 0x44086:return am_call(c,0x4410c,0x4408a);
    case 0x4408a:am_word(r.d[0],0);r.pc=0x4408e;return true;
    case 0x4408e:return am_call(c,0xcd1c,0x44094);
    case 0x44094:case 0x43ffa:case 0x440ec:case 0x4410a:case 0x4411c:
    case 0x43f5a:case 0xcd1a:case 0xcd46:case 0x1adee:case 0x43f3c:
    case 0x16faa:case 0x182ce:case 0x1724a:case 0x1831a:return am_return(c);
    case 0x43f5c:if(!scene_movem(c))return false;r.pc=0x43f60;return true;
    case 0x43f60:if(!am_push(c,4,am_index(r.a[0],r.d[0])))return false;r.pc=0x43f64;return true;
    case 0x43f64:r.pc=(r.d[1]&65535U)==1?0x43f6c:0x43f9e;return true;
    case 0x43f6c:if(!am_read(c,r.a[0]+4U,2,value))return false;am_word(r.d[0],value);r.pc=0x43f70;return true;
    case 0x43f70:return am_call(c,0x440c8,0x43f74);
    case 0x43f74:r.pc=(r.d[0]&65535U)==0?0x43f92:0x43f7c;return true;
    case 0x43f92:r.d[0]=1;r.pc=0x43f94;return true;
    case 0x43f94:return am_call(c,0xcd1c,0x43f9a);
    case 0x43f9a:case 0x43fda:r.pc=0x43ff8;return true;
    case 0x43f9e:r.pc=(r.d[1]&65535U)==2?0x43fa6:0x43fde;return true;
    case 0x43fa6:am_word(r.d[0],0x20);r.pc=0x43faa;return true;
    case 0x43faa:return am_call(c,0x440c8,0x43fae);
    case 0x43fae:r.pc=(r.d[0]&65535U)==0?0x43fcc:0x43fb6;return true;
    case 0x43fcc:if(!am_push(c,2,r.d[1]))return false;r.pc=0x43fce;return true;
    case 0x43fce:if(!am_read(c,r.a[0]+4U,4,r.a[0]))return false;r.pc=0x43fd2;return true;
    case 0x43fd2:if(!am_pop(c,2,value))return false;am_word(r.d[0],value);r.pc=0x43fd4;return true;
    case 0x43fd4:return am_call(c,0x16f9a,0x43fda);
    case 0x43ff8:if(!am_pop(c,4,r.a[0]))return false;r.pc=0x43ffa;return true;
    case 0x440c8:
        if(!am_read(c,r.a[5]+0x549aU,1,value))return false;r.pc=value==0?0x440d0:0x440ee;return true;
    case 0x440d0:
        if(!am_read(c,r.a[5]+0x5496U,2,value))return false;am_word(r.d[1],value);
        if(!am_read(c,r.a[5]+0x5498U,2,value))return false;am_word(r.d[3],value);
        am_word(r.d[2],r.d[1]);am_word(r.d[2],r.d[2]+r.d[0]);
        if((r.d[2]&65535U)>=(r.d[3]&65535U))am_word(r.d[2],r.d[3]);
        if(!am_write(c,r.a[5]+0x5496U,2,r.d[2]))return false;
        am_word(r.d[0],r.d[0]-r.d[2]);am_word(r.d[0],r.d[0]+r.d[1]);r.pc=0x440ec;return true;
    case 0x440ee:
        if(!am_read(c,r.a[5]+0x5498U,2,value))return false;am_word(r.d[2],value);
        if(!am_read(c,r.a[5]+0x5496U,2,value))return false;am_word(r.d[3],value);
        am_word(r.d[1],r.d[2]);am_word(r.d[1],r.d[1]-r.d[0]);
        if((r.d[1]&65535U)<(r.d[3]&65535U))am_word(r.d[1],r.d[3]);
        if(!am_write(c,r.a[5]+0x5498U,2,r.d[1]))return false;
        am_word(r.d[0],r.d[0]-r.d[2]);am_word(r.d[0],r.d[0]+r.d[1]);r.pc=0x4410a;return true;
    case 0x4410c:
        if(!am_read(c,r.a[5]+0x5496U,2,value))return false;am_word(r.d[1],value);
        if(!am_read(c,r.a[5]+0x5498U,2,value))return false;am_word(r.d[2],value);
        if(!am_write(c,r.a[5]+0x5496U,2,r.d[2]))return false;
        am_word(r.d[0],r.d[2]);am_word(r.d[0],r.d[0]-r.d[1]);r.pc=0x4411c;return true;
    case 0xcd1c:
        r.a[4]=r.a[5]+((r.d[0]&65535U)==0?0xd3eU:0xd46U);
        if((r.d[1]&65535U)>=0x17cU)r.d[1]=0xffffffffU;
        if((r.d[1]&65535U)>=(r.d[2]&65535U))r.d[2]=0xffffffffU;
        am_swap(r.d[1]);am_word(r.d[1],r.d[2]);
        if(!am_write(c,r.a[4],4,r.d[1]) || !am_write(c,r.a[4]+4U,4,r.d[1]))return false;r.pc=0xcd46;return true;
    case 0x43f3e:return am_call(c,0xccd6,0x43f44);
    case 0x43f44:return am_call(c,0x1ad9a,0x43f4a);
    case 0x43f4a:return am_call(c,0x43efa,0x43f4c);
    case 0x43f4c:
        if(!am_write(c,0x10d496,2,0) || !am_write(c,0x10d498,2,0x17c))return false;r.pc=0x43f5a;return true;
    case 0xccd6:return am_call(c,0xcd48,0xccda);
    case 0xcd48:if(!am_write(c,r.a[5]+0x1152U,4,0xcd50))return false;r.pc=0xcd50;return true;
    case 0xccda:
        r.d[0]=0;
        if(!am_write(c,r.a[5]+0xd3dU,1,0) || !am_write(c,r.a[5]+0xd34U,4,0) ||
           !am_write(c,r.a[5]+0xd38U,2,0) || !am_write(c,r.a[5]+0xd3aU,2,0) ||
           !am_write(c,r.a[5]+0x114eU,2,0) || !am_write(c,r.a[5]+0x1150U,2,0))return false;
        r.a[0]=r.a[5]+0xb34U;am_word(r.d[7],255);r.pc=0xccfc;return true;
    case 0xccfc:
        if(!am_write(c,r.a[0],2,r.d[0]))return false;r.a[0]+=2U;am_word(r.d[0],r.d[0]+12U);
        scene_dbf(r,7,0xccfc,0xcd06);return true;
    case 0xcd06:r.d[0]=0;r.d[1]=r.d[2]=0xffffffffU;r.pc=0xcd0c;return true;
    case 0xcd0c:return am_call(c,0xcd1c,0xcd10);
    case 0xcd10:r.d[0]=1;r.d[1]=r.d[2]=0xffffffffU;r.pc=0xcd16;return true;
    case 0xcd16:return am_call(c,0xcd1c,0xcd1a);
    case 0x1ad9a:
        if(!am_write(c,r.a[5]-0x7ff0U,2,1) || !am_write(c,0x2ffff2,2,0x2000) || !am_write(c,0x2ffff0,2,0))return false;
        r.pc=0x1adb0;return true;
    case 0x1adb0:r.a[0]=0x109156;r.pc=0x1adb6;return true;
    case 0x1adb6:return am_call(c,0x1adf0,0x1adba);
    case 0x1adba:r.a[0]=0x10b1d6;r.pc=0x1adc0;return true;
    case 0x1adc0:return am_call(c,0x1adf0,0x1adc4);
    case 0x1adc4:r.a[0]=0x10d256;r.pc=0x1adca;return true;
    case 0x1adca:return am_call(c,0x1adf0,0x1adce);
    case 0x1adce:r.a[0]=0x10d2d6;r.pc=0x1add4;return true;
    case 0x1add4:return am_call(c,0x1adf0,0x1add8);
    case 0x1add8:
        if(!am_write(c,r.a[5]-0x7ff0U,2,0) || !am_write(c,0x2ffff2,2,0x1000) || !am_write(c,0x2ffff0,2,0))return false;
        r.pc=0x1adee;return true;
    case 0x1adf0:r.d[0]=0xffffffffU;r.pc=0x1adf2;return true;
    case 0x1adf2:r.pc=0x16f9a;return true;
    case 0x43efa:
        r.a[4]=0x3c0000;r.d[7]=0x82010000;r.d[6]=0x8401f000;r.d[5]=0x8001ffff;r.d[4]=0x10000;
        am_word(r.d[0],0x17b);r.pc=0x43f1a;return true;
    case 0x43f1a:
        if(!scene_long(c,r.a[4],r.d[7]))return false;r.d[7]+=r.d[4];
        if(!scene_watchdog(c,r.d[0]) || !scene_long(c,r.a[4],r.d[6]))return false;r.d[6]+=r.d[4];
        if(!scene_watchdog(c,r.d[0]) || !scene_long(c,r.a[4],r.d[5]))return false;r.d[5]+=r.d[4];
        if(!scene_watchdog(c,r.d[0]))return false;scene_dbf(r,0,0x43f1a,0x43f3c);return true;
    case 0x16f9a:if(!am_write(c,r.a[0]+0x26U,2,r.d[0]))return false;r.pc=0x16f9e;return true;
    case 0x16f9e:return am_call(c,0x1829a,0x16fa2);
    case 0x16fa2:return am_call(c,0x1701a,0x16fa6);
    case 0x16fa6:return am_call(c,0x182d0,0x16faa);
    case 0x1829a:
        if(!am_read(c,r.a[0]+0x26U,2,value))return false;am_word(r.d[7],value);
        if(value&0x8000U){r.pc=0x182ce;return true;}
        r.a[1]=0x3c0000;am_word(r.d[6],0x3ff);am_word(r.d[7],(r.d[7]+1U)<<6);am_swap(r.d[7]);am_word(r.d[7],0);
        r.pc=0x182b4;return true;
    case 0x182b4:
        if(!scene_long(c,r.a[1],r.d[7]))return false;r.d[7]+=0x10000U;
        if(!scene_long(c,r.a[1],r.d[7]))return false;r.d[7]+=0x10000U;
        scene_dbf(r,6,0x182b4,0x182c8);return true;
    case 0x182c8:if(!scene_watchdog(c,r.d[0]))return false;r.pc=0x182ce;return true;
    case 0x1701a:
        if(!am_read(c,r.a[0]+0x7aU,1,value) || !am_write(c,r.a[0]+0x7aU,1,value&254U) ||
           !am_read(c,r.a[0]+0x26U,2,value))return false;am_word(r.d[7],value);
        r.pc=(value&0x8000U)?0x1724a:0x17028;return true;
    case 0x17028:
        if(!scene_watchdog(c,r.d[0]))return false;am_word(r.d[6],r.d[7]);
        am_word(r.d[7],r.d[7]+0x8201U);am_word(r.d[6],r.d[6]+0x8001U);am_swap(r.d[7]);am_swap(r.d[6]);
        am_word(r.d[6],0xfff);am_word(r.d[7],0x8000);r.d[5]=0x10000;r.pc=0x1704a;return true;
    case 0x1704a:
        for(unsigned int i=0;i<32;++i){
            if(!scene_long(c,0x3c0000,r.d[7]))return false;r.d[7]+=r.d[5];
            if(!scene_long(c,0x3c0000,r.d[6]))return false;r.d[6]+=r.d[5];
        }
        r.pc=0x1724a;return true;
    case 0x182d0:r.d[0]=0;r.a[1]=r.a[0]+0x3aU;am_word(r.d[0],0);r.pc=0x182da;return true;
    default:return am_error(c,"unsupported animation scene PC");
    }
}
}
