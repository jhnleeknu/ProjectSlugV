#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool save_words(AnimationMachineContext& c) {
    for(unsigned int i=6;i>0;--i)if(!am_push(c,2,c.s.d[i-1]))return false;return true;
}
bool restore_words(AnimationMachineContext& c) {
    std::uint32_t value=0;for(unsigned int i=0;i<6;++i){if(!am_pop(c,2,value))return false;c.s.d[i]=am_extend_word(value);}return true;
}
void video(AnimationMachineContext& c,std::uint32_t value) {
    VideoPortWrite p;p.address=0x3c0000;p.size=4;p.value=value;c.ports.push_back(p);
}
std::uint32_t asr4(std::uint32_t value) {value&=65535U;return (value>>4)|((value&0x8000U)?0xf000U:0U);}
bool bit(AnimationMachineContext& c,unsigned int mask,bool& set) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0]+0x7aU,1,value))return false;set=(value&mask)!=0;return true;
}
}
bool animation_map_transfer_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool flag=false,borrow=false;
    switch(r.pc) {
    case 0x48042:return am_call(c,0x1861a,0x48048);
    case 0x48048:return am_call(c,0x17012,0x4804e);
    case 0x17012:
        if(!am_read(c,r.a[0]+0x7aU,1,value)||!am_write(c,r.a[0]+0x7aU,1,value|0x81U))return false;r.pc=0x17018;return true;
    case 0x17018:case 0x16f98:case 0x18654:case 0x18772:case 0x1879a:case 0x185f2:case 0x185f8:return am_return(c);
    case 0x16f0e:
        if(!am_read(c,r.a[0]+0x36U,4,r.a[2])||!am_read(c,r.a[0]+0x2eU,4,r.a[1]))return false;
        am_word(r.d[6],r.d[2]-1U);r.pc=0x16f1a;return true;
    case 0x16f1a:
        if(!am_read(c,r.a[1]+4U,2,value))return false;r.pc=(r.d[0]&65535U)>=value?0x16f88:0x16f22;return true;
    case 0x16f22:
        am_word(r.d[7],(r.d[4]&31U)*2U);r.a[3]=am_index(r.a[0]+0x3aU,r.d[7]);r.pc=0x16f2e;return true;
    case 0x16f2e:r.pc=r.a[2]?0x16f3e:0x16f36;return true;
    case 0x16f36:
        if(!am_write(c,r.a[3],2,0x21))return false;r.pc=0x16f88;return true;
    case 0x16f3e:r.pc=r.a[2]==0xffffffffU?0x16f46:0x16f4e;return true;
    case 0x16f46:
        if(!am_write(c,r.a[3],1,0))return false;r.pc=0x16f88;return true;
    case 0x16f4e:
        if(!am_read(c,r.a[2],2,value))return false;am_word(r.d[7],value);
        r.pc=!value||(r.d[0]&65535U)>=value?0x16f5e:0x16f5a;return true;
    case 0x16f5a:r.a[2]-=4U;r.pc=0x16f4e;return true;
    case 0x16f5e:r.a[4]=r.a[2]+4U;r.pc=0x16f62;return true;
    case 0x16f62:
        if(!am_read(c,r.a[4],2,value))return false;am_word(r.d[7],value);
        r.pc=(value&0x8000U)||(r.d[0]&65535U)<value?0x16f72:0x16f6e;return true;
    case 0x16f6e:r.a[2]=r.a[4];r.pc=0x16f5e;return true;
    case 0x16f72:
        if(!am_read(c,r.a[2]+3U,1,value))return false;am_byte(r.d[7],value);r.pc=0x16f76;return true;
    case 0x16f76:
        if(!am_write(c,r.a[3]+1U,1,r.d[7]))return false;r.pc=0x16f7a;return true;
    case 0x16f7a:
        if(!am_read(c,r.a[0]+0x35U,1,value))return false;am_byte(r.d[7],value);
        if(!am_read(c,r.a[2]+2U,1,value))return false;am_byte(r.d[7],r.d[7]-value+1U);am_byte(r.d[7],r.d[7]<<3);r.pc=0x16f86;return true;
    case 0x16f86:
        if(!am_write(c,r.a[3],1,r.d[7]))return false;r.pc=0x16f88;return true;
    case 0x16f88:
        am_word(r.d[0],r.d[0]+1U);am_word(r.d[4],r.d[4]+1U);value=r.d[6]&65535U;am_word(r.d[6],value-1U);r.pc=value?0x16f1a:0x16f90;return true;
    case 0x16f90:am_word(r.d[0],r.d[0]-r.d[2]);am_word(r.d[4],r.d[4]-r.d[2]);r.pc=0x16f94;return true;
    case 0x16f94:
        if(!am_write(c,r.a[0]+0x36U,4,r.a[2]))return false;r.pc=0x16f98;return true;
    case 0x183c6:
        if(!am_read(c,r.a[1]+4U,2,value))return false;am_word(r.d[7],value);am_word(r.d[2],r.d[2]-1U);
        am_word(r.d[7],r.d[7]+r.d[2]);am_word(r.d[0],r.d[0]+r.d[2]);r.pc=(r.d[0]&65535U)>=(r.d[7]&65535U)?0x185f4:0x183d6;return true;
    case 0x183d6:
        am_word(r.d[7],r.d[7]-r.d[2]);borrow=(r.d[0]&65535U)<(r.d[2]&65535U);am_word(r.d[0],r.d[0]-r.d[2]);r.pc=borrow?0x183de:0x183e4;return true;
    case 0x183de:am_word(r.d[4],r.d[4]-r.d[0]);am_word(r.d[2],r.d[2]+r.d[0]);r.d[0]=0;r.pc=0x183e4;return true;
    case 0x183e4:
        am_word(r.d[2],r.d[2]+1U);am_word(r.d[7],r.d[7]-r.d[0]);borrow=(r.d[7]&65535U)<(r.d[2]&65535U);am_word(r.d[7],r.d[7]-r.d[2]);r.pc=borrow?0x183ee:0x183f0;return true;
    case 0x183ee:am_word(r.d[2],r.d[2]+r.d[7]);r.pc=0x183f0;return true;
    case 0x183f0:
        if(!am_read(c,r.a[1]+6U,2,value))return false;am_word(r.d[7],value);am_word(r.d[3],r.d[3]-1U);
        am_word(r.d[7],r.d[7]+r.d[3]);am_word(r.d[1],r.d[1]+r.d[3]);r.pc=(r.d[1]&65535U)>=(r.d[7]&65535U)?0x185f4:0x18400;return true;
    case 0x18400:
        am_word(r.d[7],r.d[7]-r.d[3]);borrow=(r.d[1]&65535U)<(r.d[3]&65535U);am_word(r.d[1],r.d[1]-r.d[3]);r.pc=borrow?0x18408:0x1840e;return true;
    case 0x18408:am_word(r.d[5],r.d[5]+r.d[1]);am_word(r.d[3],r.d[3]+r.d[1]);r.d[1]=0;r.pc=0x1840e;return true;
    case 0x1840e:
        am_word(r.d[3],r.d[3]+1U);am_word(r.d[7],r.d[7]-r.d[1]);borrow=(r.d[7]&65535U)<(r.d[3]&65535U);am_word(r.d[7],r.d[7]-r.d[3]);r.pc=borrow?0x18418:0x1841a;return true;
    case 0x18418:am_word(r.d[3],r.d[3]+r.d[7]);r.pc=0x1841a;return true;
    case 0x1841a:am_word(r.d[4],r.d[4]&31U);am_word(r.d[5],(~r.d[5])&31U);r.pc=0x18424;return true;
    case 0x18424:if(!save_words(c))return false;r.pc=0x18428;return true;
    case 0x18428:if(!am_write(c,r.a[5]-0x7ff0U,2,1))return false;r.pc=0x1842e;return true;
    case 0x1842e:if(!am_write(c,0x2ffff2,2,0x2000))return false;r.pc=0x18436;return true;
    case 0x18436:if(!am_write(c,0x2ffff0,2,0))return false;r.pc=0x1843e;return true;
    case 0x1843e:if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[7],value);r.pc=0x18440;return true;
    case 0x18440:if(!am_read(c,0x200004,4,r.a[2]))return false;r.pc=0x18446;return true;
    case 0x18446:am_word(r.d[7],r.d[7]<<2);r.pc=0x18448;return true;
    case 0x18448:if(!am_read(c,am_index(r.a[2],r.d[7]),4,value))return false;r.a[2]=value;r.pc=0x1844c;return true;
    case 0x1844c:r.a[2]+=4U;r.pc=0x1844e;return true;
    case 0x1844e:
        if(!am_read(c,r.a[1]+6U,2,value))return false;am_word(r.d[6],value);
        if(!am_read(c,r.a[0]+0x26U,2,value))return false;am_word(r.d[7],value);r.pc=(value&0x8000U)?0x18530:0x1845a;return true;
    case 0x1845a:
        r.d[0]=(r.d[0]&65535U)*(r.d[6]&65535U);r.d[1]&=65535U;r.d[0]=(r.d[0]+r.d[1])<<2;r.a[2]+=r.d[0];am_word(r.d[6],r.d[6]<<2);r.pc=0x1846a;return true;
    case 0x1846a:
        if(!am_read(c,r.a[0]+0x26U,2,value))return false;am_word(r.d[0],(value+1U)*2U);am_word(r.d[4],r.d[4]*2U);am_word(r.d[5],r.d[5]*2U);r.a[3]=r.a[0]+0x3aU;r.pc=0x1847a;return true;
    case 0x1847a:
        if(!am_read(c,am_index(r.a[3],r.d[4]),1,value))return false;am_byte(r.d[1],(value>>3)|((value&128U)?0xe0U:0U));
        am_byte(r.d[1],r.d[1]*2U);am_byte(r.d[1],r.d[1]+r.d[5]);am_word(r.d[1],r.d[1]&0x3eU);
        am_word(r.d[7],r.d[0]+r.d[4]);am_word(r.d[7],r.d[7]<<5);am_word(r.d[7],r.d[7]+r.d[1]);r.a[4]=r.a[2];am_swap(r.d[6]);am_word(r.d[6],r.d[3]);r.pc=0x18496;return true;
    case 0x18496:
        am_swap(r.d[7]);if(!am_read(c,r.a[4],2,value))return false;r.a[4]+=2U;am_word(r.d[7],value);video(c,r.d[7]);r.d[7]+=0x10000U;
        if(!am_read(c,r.a[4],2,value))return false;r.a[4]+=2U;am_word(r.d[7],value);video(c,r.d[7]);am_swap(r.d[7]);
        am_word(r.d[7],r.d[7]-1U);am_word(r.d[7],r.d[7]-r.d[1]);am_byte(r.d[1],(r.d[1]+2U)&0x3eU);am_byte(r.d[7],r.d[7]+r.d[1]);am_word(r.d[6],r.d[6]-1U);
        r.pc=(r.d[6]&65535U)?0x18496:0x184c0;return true;
    case 0x184c0:
        am_swap(r.d[6]);r.a[2]=am_index(r.a[2],r.d[6]);am_word(r.d[4],(r.d[4]+2U)&0x3eU);am_word(r.d[2],r.d[2]-1U);r.pc=(r.d[2]&65535U)?0x1847a:0x184ce;return true;
    case 0x184ce:r.pc=0x18530;return true;
    case 0x18530:if(!restore_words(c))return false;r.pc=0x18534;return true;
    case 0x18534:if(!am_write(c,r.a[5]-0x7ff0U,2,0))return false;r.pc=0x1853a;return true;
    case 0x1853a:if(!am_write(c,0x2ffff2,2,0x1000))return false;r.pc=0x18542;return true;
    case 0x18542:if(!am_write(c,0x2ffff0,2,0))return false;r.pc=0x1854a;return true;
    case 0x1854a:
        if(!am_read(c,r.a[1]+2U,2,value))return false;am_word(r.d[7],value);r.pc=value?0x18552:0x185d2;return true;
    case 0x18552:if(!am_read(c,0x200010,4,r.a[2]))return false;r.pc=0x18558;return true;
    case 0x18558:
        am_word(r.d[7],r.d[7]<<2);if(!am_read(c,am_index(r.a[2],r.d[7]),4,value))return false;r.d[7]=value;r.pc=value==0xffffffffU?0x185a6:0x18568;return true;
    case 0x18568:r.a[2]=r.d[7];am_word(r.d[0],r.d[0]<<2);r.a[2]=am_index(r.a[2],r.d[0]);am_word(r.d[1],r.d[1]<<2);r.pc=0x18570;return true;
    case 0x18570:am_word(r.d[4],r.d[4]<<8);am_word(r.d[5],r.d[5]<<2);am_word(r.d[2],r.d[2]*2U);r.pc=0x18576;return true;
    case 0x18576:
        am_word(r.d[4],r.d[4]&0x1f80U);r.a[4]=r.a[2];if(!am_read(c,r.a[2],2,value))return false;r.a[2]+=2U;r.a[4]=am_index(r.a[4],value);r.a[4]=am_index(r.a[4],r.d[1]);
        r.a[3]=am_index(r.a[0]+0x80U,r.d[4]);am_word(r.d[0],r.d[5]);am_word(r.d[6],r.d[3]);r.pc=0x1858a;return true;
    case 0x1858a:
        am_word(r.d[0],r.d[0]&0x7eU);if(!am_read(c,r.a[4],4,value))return false;r.a[4]+=4U;
        if(!am_write(c,am_index(r.a[3],r.d[0]),4,value))return false;am_word(r.d[0],r.d[0]+4U);am_word(r.d[6],r.d[6]-1U);r.pc=(r.d[6]&65535U)?0x1858a:0x18598;return true;
    case 0x18598:
        r.a[2]=am_index(r.a[2],r.d[6]);am_word(r.d[4],r.d[4]+0x80U);am_word(r.d[2],r.d[2]-1U);r.pc=(r.d[2]&65535U)?0x18576:0x185a2;return true;
    case 0x185a2:r.pc=0x185d2;return true;
    case 0x185a6:am_word(r.d[4],r.d[4]<<8);am_word(r.d[5],r.d[5]<<2);am_word(r.d[2],r.d[2]<<1);r.d[0]=0;r.pc=0x185ae;return true;
    case 0x185ae:
        am_word(r.d[4],r.d[4]&0x1f80U);r.a[3]=am_index(r.a[0]+0x80U,r.d[4]);am_word(r.d[6],r.d[3]);am_word(r.d[7],r.d[5]);r.pc=0x185bc;return true;
    case 0x185bc:
        am_word(r.d[7],r.d[7]&0x7cU);if(!am_write(c,am_index(r.a[3],r.d[7]),4,r.d[0]))return false;am_word(r.d[7],r.d[7]+4U);am_word(r.d[6],r.d[6]-1U);r.pc=(r.d[6]&65535U)?0x185bc:0x185ca;return true;
    case 0x185ca:am_word(r.d[4],r.d[4]+0x80U);am_word(r.d[2],r.d[2]-1U);r.pc=(r.d[2]&65535U)?0x185ae:0x185d2;return true;
    case 0x185d2:if(!am_write(c,r.a[5]-0x7ff0U,2,0))return false;r.pc=0x185d8;return true;
    case 0x185d8:if(!am_write(c,0x2ffff2,2,0x1000))return false;r.pc=0x185e0;return true;
    case 0x185e0:if(!am_write(c,0x2ffff0,2,0))return false;r.pc=0x185e8;return true;
    case 0x185e8:if(!am_read(c,r.a[0]+0x7aU,1,value)||!am_write(c,r.a[0]+0x7aU,1,value|128U))return false;r.pc=0x185ee;return true;
    case 0x185ee:r.carry=AnimationCarrySet;r.pc=0x185f2;return true;
    case 0x185f4:r.carry=AnimationCarryClear;r.pc=0x185f8;return true;
    case 0x1861a:
        if(!am_read(c,r.a[0]+0x2eU,4,r.a[1]))return false;r.pc=r.a[1]?0x18626:0x18654;return true;
    case 0x18626:
        am_word(r.d[4],0xffa0);if(!am_read(c,r.a[0]+0x14U,2,value))return false;am_word(r.d[4],r.d[4]-value);am_word(r.d[4],asr4(r.d[4]));
        am_word(r.d[5],0x27f);if(!am_read(c,r.a[0]+0x18U,2,value))return false;am_word(r.d[5],r.d[5]-value);am_word(r.d[5],asr4(r.d[5]));
        am_word(r.d[0],r.d[4]);am_word(r.d[1],r.d[5]);if(!am_read(c,r.a[0]+0x32U,2,value))return false;am_word(r.d[0],r.d[0]-value);
        if(!am_read(c,r.a[0]+0x34U,2,value))return false;am_word(r.d[1],0U-(r.d[1]-value));am_word(r.d[2],32);am_word(r.d[3],32);r.pc=0x18650;return true;
    case 0x18650:return am_call(c,0x18702,0x18654);
    case 0x18702:if(!bit(c,8,flag))return false;r.pc=flag?0x1870c:0x18720;return true;
    case 0x1870c:if(!am_read(c,r.a[1]+4U,2,value))return false;r.pc=(r.d[0]&65535U)<value?0x18720:0x18714;return true;
    case 0x18714:case 0x18732: {
        const unsigned int index=r.pc==0x18714?0:1,offset=index?6:4;r.d[index]&=65535U;
        if(!am_read(c,r.a[1]+offset,2,value))return false;if(!value)return am_error(c,"animation map DIVU zero divisor");
        other=r.d[index];r.d[index]=((other%value)<<16)|(other/value);am_swap(r.d[index]);r.pc=index?0x1873e:0x18720;return true;
    }
    case 0x18720:if(!bit(c,16,flag))return false;r.pc=flag?0x1872a:0x1873e;return true;
    case 0x1872a:if(!am_read(c,r.a[1]+6U,2,value))return false;r.pc=(r.d[1]&65535U)<value?0x1873e:0x18732;return true;
    case 0x1873e:return am_call(c,0x16f0e,0x18742);
    case 0x18742:if(!save_words(c))return false;r.pc=0x18746;return true;
    case 0x18746:return am_call(c,0x183c6,0x1874a);
    case 0x1874a:if(!restore_words(c))return false;r.pc=0x1874e;return true;
    case 0x1874e:if(!bit(c,16,flag))return false;r.pc=flag?0x18758:0x18768;return true;
    case 0x18758:if(!save_words(c))return false;r.pc=0x1875c;return true;
    case 0x1875c:if(!am_read(c,r.a[1]+6U,2,value))return false;am_word(r.d[1],r.d[1]-value);r.pc=0x18760;return true;
    case 0x18760:return am_call(c,0x183c6,0x18764);
    case 0x18764:if(!restore_words(c))return false;r.pc=0x18768;return true;
    case 0x18768:if(!bit(c,8,flag))return false;r.pc=flag?0x18774:0x18772;return true;
    case 0x18774:if(!am_read(c,r.a[1]+4U,2,value))return false;am_word(r.d[0],r.d[0]-value);r.pc=0x18778;return true;
    case 0x18778:return am_call(c,0x16f0e,0x1877c);
    case 0x1877c:if(!save_words(c))return false;r.pc=0x18780;return true;
    case 0x18780:return am_call(c,0x183c6,0x18784);
    case 0x18784:if(!restore_words(c))return false;r.pc=0x18788;return true;
    case 0x18788:if(!bit(c,16,flag))return false;r.pc=flag?0x18792:0x1879a;return true;
    case 0x18792:if(!am_read(c,r.a[1]+6U,2,value))return false;am_word(r.d[1],r.d[1]-value);r.pc=0x18796;return true;
    case 0x18796:return am_call(c,0x183c6,0x1879a);
    default:return am_error(c,"unsupported animation map transfer PC");
    }
}
}
