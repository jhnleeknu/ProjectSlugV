#include "animation_machine_internal.h"
namespace ms5 {
namespace {
bool neg(std::uint32_t v) {return (v&0x8000U)!=0;}
bool read_offset(AnimationMachineContext& c,unsigned int reg,std::uint32_t displacement,
    unsigned int size,std::uint32_t& value) {return am_read(c,am_index(c.s.a[reg],displacement),size,value);}
bool write_offset(AnimationMachineContext& c,unsigned int reg,std::uint32_t displacement,
    unsigned int size,std::uint32_t value) {return am_write(c,am_index(c.s.a[reg],displacement),size,value);}
bool save_addresses(AnimationMachineContext& c) {
    // MOVEM.L A0-A1,-(A7): reverse register order on predecrement.
    return am_push(c,4,c.s.a[1]) && am_push(c,4,c.s.a[0]);
}
bool restore_addresses(AnimationMachineContext& c) {
    return am_pop(c,4,c.s.a[0]) && am_pop(c,4,c.s.a[1]);
}
bool restore_bank(AnimationMachineContext& c) {
    std::uint32_t value=0;
    if(!am_pop(c,2,value) || !write_offset(c,5,0x8010,2,value))return false;
    // MOVEM.W D0/D7,-(A7) precedes the live shadow read; it may alias it.
    if(!am_push(c,2,c.s.d[7]) || !am_push(c,2,c.s.d[0]))return false;
    if(!read_offset(c,5,0x8010,2,value))return false;
    am_word(c.s.d[7],value);am_word(c.s.d[0],c.s.d[7]);
    am_word(c.s.d[7],c.s.d[7]+1U);am_word(c.s.d[7],c.s.d[7]<<8);
    am_word(c.s.d[7],c.s.d[7]<<4);
    if(!am_write(c,0x2ffff2,2,c.s.d[7]) || !am_write(c,0x2ffff0,2,0))return false;
    if(!am_pop(c,2,value))return false;c.s.d[0]=am_extend_word(value);
    if(!am_pop(c,2,value))return false;c.s.d[7]=am_extend_word(value);
    return true;
}
bool draw(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t v=0;
    r.d[0]=0;r.d[5]=0;r.d[6]=0;
    if(!am_fetch(c,1,v))return false;am_byte(r.d[5],v);
    if(!am_fetch(c,1,v))return false;am_byte(r.d[0],v);
    if(!am_fetch(c,1,v))return false;am_byte(r.d[6],v);
    if(!am_fetch(c,4,r.d[7]))return false;
    if(r.d[7]==0x7ff800U)return am_return(c);
    if(!read_offset(c,6,0x20,2,v))return false;am_word(r.d[7],r.d[7]|v);
    if(!read_offset(c,0,4,1,v))return false;
    if(v&0x80U)return am_return(c);
    if(!read_offset(c,6,0x61,1,v))return false;
    if(v&8U) {if(!read_offset(c,5,0x800f,1,v))return false;if(v&1U)return am_return(c);}
    if(!read_offset(c,6,0x12,4,r.d[1]))return false;
    am_word(r.d[0],(r.d[0]&0x80U)?r.d[0]|0xff00U:r.d[0]);
    am_word(r.d[6],(r.d[6]&0x80U)?r.d[6]|0xff00U:r.d[6]);
    unsigned int x=r.d[5]&1U;am_byte(r.d[5],(r.d[5]&255U)>>1);am_word(r.d[6],r.d[6]*2U+x);
    x=r.d[5]&1U;am_byte(r.d[5],(r.d[5]&255U)>>1);am_word(r.d[0],r.d[0]*2U+x);
    if(r.d[1]&1U)r.d[0]=0U-r.d[0];
    if(r.d[1]&2U)am_word(r.d[6],0U-r.d[6]);
    if(!read_offset(c,6,0x42,2,v))return false;am_word(r.d[0],r.d[0]+v);
    if(!read_offset(c,6,0x46,2,v))return false;am_word(r.d[6],r.d[6]+v);
    r.d[3]=0;if(!read_offset(c,6,0x53,1,v))return false;am_byte(r.d[2],v);
    x=r.d[2]&1U;am_byte(r.d[2],(r.d[2]&255U)>>1);am_word(r.d[0],r.d[0]-x);
    x=r.d[2]&1U;am_byte(r.d[2],(r.d[2]&255U)>>1);am_word(r.d[6],r.d[6]-x);
    am_swap(r.d[0]);am_word(r.d[0],r.d[6]);am_byte(r.d[4],r.d[5]);
    am_byte(r.d[4],r.d[4]&3U);am_byte(r.d[1],r.d[1]^r.d[4]);
    am_word(r.d[5],(r.d[5]&65535U)>>2);
    if((r.d[5]&65535U)>=10) {am_word(r.d[5],r.d[5]-10U);am_byte(r.d[1],r.d[1]^4U);}
    bool direct=false;
    if((r.d[5]&65535U)>=5)am_word(r.d[5],r.d[5]-5U);
    else {
        if(!read_offset(c,6,0x16,2,v))return false;am_word(r.d[4],v);
        const bool carry=(r.d[4]&1U)!=0;
        am_byte(r.d[4],((r.d[4]&255U)>>1)|(r.d[4]&0x80U));
        if(!(r.d[4]&0x80U) && carry) {am_byte(r.d[4],r.d[1]);am_word(r.d[1],r.d[4]);direct=true;}
    }
    if(!direct && (r.d[5]&65535U)<4) {
        am_byte(r.d[4],r.d[1]);
        if(!am_read(c,am_index(r.a[6]+0x19U,r.d[5]),1,v))return false;
        am_byte(r.d[1],v);am_word(r.d[1],r.d[1]<<8);am_byte(r.d[1],r.d[4]);
    }
    if(!read_offset(c,6,0x1e,2,v))return false;am_word(r.d[5],v);
    if(!save_addresses(c))return false;
    if(!read_offset(c,5,0x8010,2,v) || !am_push(c,2,v) || !am_zero_bank(c))return false;
    return am_call(c,0xcd58,0x4a200);
}
bool wait_command(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t v=0;
    r.d[7]=0;
    if(!read_offset(c,5,0x5742,1,v) || !write_offset(c,5,0x5742,1,v+1U))return false;
    if(!am_fetch(c,1,v))return false;am_byte(r.d[1],v);
    if((r.d[1]&255U)==0) {
        if(!read_offset(c,0,4,1,v))return false;am_byte(r.d[6],v);
        if(v&0x80U) {
            if(!write_offset(c,0,4,2,0) || !am_read(c,r.a[0],4,r.d[7]))return false;
            r.a[1]=r.d[7];r.pc=0x49ffe;return true;
        }
        r.pc=0x4a0ca;return true;
    }
    if(!read_offset(c,0,4,2,v))return false;am_word(r.d[6],v);
    const std::uint32_t original=r.d[6]&65535U;
    if(original==0 || neg(original)) {
        if(!read_offset(c,0,4,1,v) || !write_offset(c,0,4,1,v+r.d[1]))return false;
    }
    if(!neg(original)) {
        if(!read_offset(c,0,6,2,v))return false;am_word(r.d[0],v);
        if(!read_offset(c,0,4,2,v) || !write_offset(c,0,4,2,v-r.d[0]))return false;
    }
    if(!read_offset(c,0,4,2,v))return false;
    if(v!=0 && !neg(v)) {if(!am_read(c,r.a[0],4,r.d[5]))return false;r.a[1]=r.d[5];}
    if(!am_read(c,r.a[1],1,v))return false;
    if(v==0x28) {if(!am_read(c,r.a[0],4,r.d[5]))return false;r.a[1]=r.d[5];r.d[7]=0xffffffffU;}
    if(neg(original)) {r.pc=0x49ffe;return true;}
    r.d[6]=r.a[1];if(!am_write(c,r.a[0],4,r.d[6]))return false;
    r.pc=0x4a0ca;return true;
}
bool field(AnimationMachineContext& c,std::uint32_t pc) {
    AnimationMachineState& r=c.s;std::uint32_t v=0;
    if(pc==0x4a2f2 || pc==0x4a300) {
        r.a[1]+=1U;if(pc==0x4a2f2)r.d[0]=0;
        if(!am_fetch(c,2,v) || !write_offset(c,6,pc==0x4a2f2?0x70:0x20,2,v))return false;
    } else if(pc==0x4a27e) {
        if(!am_fetch(c,1,v))return false;am_byte(r.d[0],v);
        if(!am_fetch(c,2,v))return false;am_word(r.d[1],v);am_word(r.d[1],r.d[1]*2U);
        r.a[2]=0x4a76c;if(!am_read(c,am_index(r.a[2],r.d[1]),2,v))return false;am_word(r.d[1],v);
        if(!am_write(c,am_index(r.a[6],r.d[1]),1,r.d[0]))return false;
    } else {
        r.d[0]=0;if(!am_fetch(c,1,v))return false;am_byte(r.d[0],v);am_word(r.d[0],r.d[0]*2U);
        r.a[2]=0x4a76c;if(!am_read(c,am_index(r.a[2],r.d[0]),2,v))return false;am_word(r.d[0],v);
        const std::uint32_t address=am_index(r.a[6],r.d[0]);
        if(pc==0x4a294 || pc==0x4a2ac) {
            const unsigned int size=pc==0x4a294?2:4;
            if(!am_fetch(c,size,v))return false;
            if(size==2)am_word(r.d[1],v);else r.d[1]=v;
            if(!am_write(c,address,size,r.d[1]))return false;
        } else if(pc==0x4a2c4) {
            if(!am_read(c,address,1,v) || !am_write(c,address,1,v-1U))return false;
        } else {
            if(!am_fetch(c,2,v))return false;am_word(r.d[2],v);
            if(!am_read(c,address,1,v))return false;am_byte(r.d[0],v);am_word(r.d[0],r.d[0]*2U);
            if((r.d[0]&65535U)<(r.d[2]&65535U)) {
                if(!am_read(c,am_index(r.a[1],r.d[0]),2,v))return false;r.a[1]=am_index(r.a[1],v);
            }
            r.a[1]=am_index(r.a[1],r.d[2]);
        }
    }
    r.pc=0x4a276;return true;
}
bool callback(AnimationMachineContext& c,bool wide) {
    AnimationMachineState& r=c.s;std::uint32_t v=0;
    if(!am_push(c,4,r.a[0]))return false;
    if(wide) {r.a[1]+=1U;if(!am_fetch(c,2,v))return false;am_word(r.d[0],v);}
    else {r.d[0]=0;if(!am_fetch(c,1,v))return false;am_byte(r.d[0],v);}
    am_word(r.d[0],r.d[0]*2U);am_word(r.d[0],r.d[0]*2U);r.a[0]=0x4a500;
    if(!am_read(c,am_index(r.a[0],r.d[0]),4,r.d[7]))return false;
    if(wide) {
        if(!am_fetch(c,2,v))return false;am_word(r.d[0],v);am_word(r.d[0],r.d[0]*2U);r.a[0]=0x4a76c;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,v))return false;am_word(r.d[1],v);
    }
    if(!am_fetch(c,4,r.a[0]) || !am_push(c,4,r.a[1]))return false;
    r.a[1]=r.d[7];if(wide)r.d[0]=r.a[0];
    if(!read_offset(c,5,0x8010,2,v) || !am_push(c,2,v) || !am_zero_bank(c))return false;
    // eb752/eb766: the command callback table 4a6dc handlers routed by objects N04; 52e78/53ad0: commands 30/31 (4a5c0/4a5c4), N12.
    if(r.a[1]!=0x3679e && r.a[1]!=0x2b3e8 && r.a[1]!=0x2b3fa && r.a[1]!=0x47672 && r.a[1]!=0xeb752 && r.a[1]!=0xeb766 &&
        r.a[1]!=0x52e78 && r.a[1]!=0x53ad0)
        return am_error(c,"unsupported animation callback target");
    return am_call(c,r.a[1],wide?0x4a354:0x4a43e);
}
}
bool animation_interpreter_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t v=0;
    switch(r.pc) {
    case 0x1dc84:return am_call(c,0x49fc6,0x1dc8a);
    case 0x210ae:return am_call(c,0x49fc6,0x210b4);
    case 0x1dc8a:case 0x210b4:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"animation caller requires known carry");
        if(r.pc==0x1dc8a)r.pc=r.carry==AnimationCarryClear?0x1dccc:0x1dc8e;
        else r.pc=r.carry==AnimationCarrySet?0x21564:0x210b8;
        return true;
    case 0x47cae:
        if(!write_offset(c,6,0x42,2,0xa0) || !write_offset(c,6,0x46,2,0x170) ||
            !write_offset(c,6,0x1e,2,0xffff))return false;
        r.pc=0x47cc0;return true;
    case 0x47cc0:return am_call(c,0x16ed2,0x47cc6);
    case 0x47cc6:return am_call(c,0x47672,0x47cca);
    case 0x47cca:
        if(!write_offset(c,6,0x14,1,0x0b))return false;r.d[0]=0;
        if(!read_offset(c,6,0x7e,1,v))return false;am_byte(r.d[0],v);
        am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
        r.a[0]=0x48a12;
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,r.d[7]))return false;
        r.d[0]=0;r.pc=0x47ce6;return true;
    case 0x47ce6:return am_call(c,0x16ea4,0x47cec);
    case 0x47cec:
        if(!write_offset(c,6,0x42,2,0xa0) || !write_offset(c,6,0x46,2,0x170) ||
            !write_offset(c,6,0x12,1,255) || !write_offset(c,6,0x13,1,255) ||
            !write_offset(c,6,0x14,1,4))return false;
        r.pc=0x47d0a;return true;
    case 0x47d0a:r.a[1]=0x489c2;r.pc=0x47d10;return true;
    case 0x47d10:am_word(r.d[0],0x100);r.pc=0x47d14;return true;
    case 0x47d14:return am_call(c,0x49f8c,0x47d1a);
    case 0x47d1a:return am_call(c,0x49fc6,0x47d20);
    case 0x47f04:return am_call(c,0x49fc6,0x47f0a);
    case 0x49f8c:
        r.a[0]=r.a[6]+0x26U;
        if(!write_offset(c,6,0x18,1,0) || !am_zero_bank(c))return false;
        if(r.a[5]!=0x108000U)return am_error(c,"unsupported original animation initializer TRAP15");
        if(!am_write(c,r.a[0],4,r.a[1]) || !write_offset(c,0,4,2,0) ||
            !write_offset(c,0,6,2,r.d[0]))return false;
        r.carry=AnimationCarryClear;
        return am_return(c);
    case 0x49fc6:
        r.a[0]=r.a[6]+0x26U;if(!am_zero_bank(c) || !am_read(c,r.a[0],4,r.d[7]))return false;
        if(r.d[7]==0) {r.carry=AnimationCarrySet;return am_return(c);}
        r.a[1]=r.d[7];if(!write_offset(c,5,0x5742,1,0) || !read_offset(c,6,0x17,1,v))return false;
        if(v!=0 && v<128)if(!write_offset(c,6,0x17,1,v-1U))return false;
        r.pc=0x49ffe;return true;
    case 0x49ffe:
        r.d[7]=0;if(!am_fetch(c,1,v))return false;am_byte(r.d[7],v);
        switch(v) {
        case 0:r.pc=0x4a066;break;case 4:r.pc=0x4a104;break;case 8:r.pc=0x4a3ac;break;
        case 0x0c:r.pc=0x4a3b8;break;case 0x10:r.pc=0x4a22c;break;case 0x14:r.pc=0x4a408;break;
        case 0x18:r.pc=0x4a27e;break;case 0x1c:r.pc=0x4a294;break;case 0x20:r.pc=0x4a2ac;break;
        case 0x24:r.pc=0x4a2c4;break;case 0x28:r.pc=0x4a0e4;break;case 0x2c:r.pc=0x4a3de;break;
        case 0x30:r.pc=0x4a2da;break;case 0x34:r.pc=0x4a2f2;break;case 0x38:r.pc=0x4a300;break;
        case 0x3c:r.pc=0x4a30c;break;case 0x40:r.pc=0x4a382;break;
        default:return am_error(c,"unsupported animation command or dispatch alignment");
        }return true;
    case 0x4a066:return wait_command(c);
    case 0x4a0ca:
        if(!am_zero_bank(c))return false;
        r.carry=(r.d[7]&1U)?AnimationCarrySet:AnimationCarryClear;
        am_word(r.d[7],((r.d[7]&65535U)>>1)|(r.d[7]&0x8000U));
        return am_return(c);
    case 0x49fea:case 0x4a0e2:case 0x4a124:case 0x4a132:case 0x4a148:case 0x3679e:return am_return(c);
    case 0x4a0e4:
        if(!read_offset(c,0,4,2,v))return false;
        if(neg(v)) {
            if(!write_offset(c,0,4,2,0) || !am_read(c,r.a[0],4,r.d[7]))return false;r.a[1]=r.d[7];r.pc=0x49ffe;
        } else {if(!write_offset(c,0,4,1,0))return false;r.d[7]=0xffffffffU;r.pc=0x4a0ca;}
        return true;
    case 0x4a104:return am_call(c,0x4a10c,0x4a108);
    case 0x4a108:case 0x4a272:r.pc=0x49ffe;return true;
    case 0x4a10c:return draw(c);
    case 0x4a200:
        if(!restore_bank(c) || !restore_addresses(c))return false;return am_return(c);
    case 0x4a22c:
        r.d[0]=0;if(!am_fetch(c,1,v))return false;am_byte(r.d[0],v);am_word(r.d[0],r.d[0]*2U);
        r.a[2]=0x4a76c;if(!am_read(c,am_index(r.a[2],r.d[0]),2,v))return false;am_word(r.d[0],v);
        if(!am_fetch(c,2,v))return false;am_word(r.d[1],v);
        if(!am_push(c,4,am_index(r.a[1],r.d[1])))return false;
        if(!am_read(c,am_index(r.a[6],r.d[0]),1,v))return false;am_byte(r.d[0],v);am_word(r.d[0],r.d[0]<<3);
        if((r.d[0]&65535U)>=(r.d[1]&65535U)) {r.pc=0x4a270;return true;}
        if(!am_read(c,am_index(r.a[1],r.d[0]),1,v))return false;
        if(v!=4)return am_error(c,"indexed animation selected opcode is not04");
        r.a[1]=am_index(r.a[1],r.d[0])+1U;return am_call(c,0x4a10c,0x4a270);
    case 0x4a270:if(!am_pop(c,4,r.a[1]))return false;r.pc=0x49ffe;return true;
    case 0x4a276:r.d[6]=r.a[1];if(!am_write(c,r.a[0],4,r.d[6]))return false;r.pc=0x49ffe;return true;
    case 0x4a27e:case 0x4a294:case 0x4a2ac:case 0x4a2c4:case 0x4a2f2:case 0x4a300:case 0x4a3de:return field(c,r.pc);
    case 0x4a2da:
        r.a[1]+=1U;r.d[0]=0;if(!am_fetch(c,2,v))return false;am_word(r.d[0],v);
        if(!save_addresses(c))return false;return am_call(c,0x3af8,0x4a2ec);
    case 0x4a2ec:if(!restore_addresses(c))return false;r.pc=0x4a276;return true;
    case 0x4a30c:return callback(c,true);
    case 0x4a408:return callback(c,false);
    case 0x4a354:case 0x4a43e:
        if(!restore_bank(c))return false;
        if(!am_pop(c,4,r.a[1]) || !am_pop(c,4,r.a[0]))return false;r.pc=0x4a276;return true;
    case 0x4a382:
        r.d[0]=0;if(!am_fetch(c,1,v))return false;am_byte(r.d[0],v);am_word(r.d[0],r.d[0]*2U);
        r.a[2]=0x4a76c;if(!am_read(c,am_index(r.a[2],r.d[0]),2,v))return false;am_word(r.d[0],v);
        if(!am_fetch(c,2,v))return false;am_word(r.d[7],v);r.a[2]=0x200004;
        if(!am_read(c,am_index(r.a[2],r.d[7]),4,r.a[2]))return false;
        if(!am_fetch(c,2,v))return false;am_word(r.d[7],v);
        if(!am_read(c,am_index(r.a[2],r.d[7]),4,r.d[7]) || !am_write(c,am_index(r.a[6],r.d[0]),4,r.d[7]))return false;
        r.pc=0x4a276;return true;
    case 0x4a3ac:
        r.a[1]+=1U;if(!am_read(c,r.a[1],4,r.d[7]))return false;r.a[1]=r.d[7];r.pc=0x4a276;return true;
    case 0x4a3b8:
        if(!am_fetch(c,1,v))return false;am_byte(r.d[1],v?255U:0U);
        if(!am_fetch(c,2,v))return false;am_word(r.d[0],v);am_word(r.d[0],r.d[0]*2U);r.a[2]=0x4a76c;
        if(!am_read(c,am_index(r.a[2],r.d[0]),2,v))return false;am_word(r.d[0],v);
        if(!am_fetch(c,4,r.d[7]) || !am_read(c,am_index(r.a[6],r.d[0]),1,v))return false;
        am_byte(r.d[0],v?255U:0U);if((r.d[0]&255U)==(r.d[1]&255U))r.a[1]=r.d[7];r.pc=0x4a276;return true;
    case 0x2b3e8:case 0x2b3fa:
        r.d[0]=0;if(!read_offset(c,6,r.pc==0x2b3e8?0x7c:0x7d,1,v))return false;am_byte(r.d[0],v);
        am_word(r.d[0],r.d[0]*2U);am_word(r.d[0],r.d[0]*2U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,v) || !write_offset(c,6,0x78,4,v))return false;
        return am_return(c);
    case 0x2b3f8:case 0x2b40a:return am_return(c);
    default:return am_error(c,"unsupported animation interpreter PC");
    }
}
}
