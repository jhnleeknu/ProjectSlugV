#include "animation_machine_internal.h"
#include "ms5/palette_effect_execution.h"
namespace ms5 {
namespace {
bool branch_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"exit helper requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
bool object_write(AnimationMachineContext& c,std::uint32_t offset,unsigned int size,std::uint32_t value) {
    return am_write(c,c.s.a[6]+offset,size,value);
}
}
bool animation_exit_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x47c5a:
        if(!object_write(c,0x7e,1,255) || !object_write(c,0x20,2,0xea) || !object_write(c,0,4,0x47c6c))return false;
        r.pc=0x47c6c;return true;
    case 0x47eac:
        if(!object_write(c,0x1e,2,0xffff))return false;r.pc=0x47eb2;return true;
    case 0x47eb2:return am_call(c,0x16ed2,0x47eb8);
    case 0x47eb8:
        if(!object_write(c,0x12,1,255) || !object_write(c,0x14,1,4) || !object_write(c,0x42,2,0xa0) ||
            !object_write(c,0x46,2,0x180) || !object_write(c,0x20,2,0xea))return false;
        r.pc=0x47ed6;return true;
    case 0x47ed6:r.a[1]=0x48980;r.pc=0x47edc;return true;
    case 0x47edc:am_word(r.d[0],0x100);r.pc=0x47ee0;return true;
    case 0x47ee0:return am_call(c,0x49f8c,0x47ee6);
    case 0x47ee6:
        if(!object_write(c,0x42,2,0xa0) || !object_write(c,0x46,2,0x180) || !object_write(c,0x7a,2,0x5a))return false;
        r.pc=0x47ef8;return true;
    case 0x47ef8:return am_call(c,0x1c63c,0x47efe);
    case 0x47efe:
        if(!object_write(c,0,4,0x47f04))return false;r.pc=0x47f04;return true;
    case 0x47f0a:
        if(!am_read(c,r.a[6]+0x7aU,2,value))return false;
        if(!value) {r.pc=0x47f1a;return true;}
        if(!am_read(c,r.a[6]+0x7aU,2,value) || !object_write(c,0x7a,2,value-1U))return false;
        r.pc=0x47f3e;return true;
    case 0x47f1a:
        r.d[7]=0;r.a[0]=r.a[5]-0x7348U;
        if(!am_read(c,r.a[0]+0x61U,1,value))return false;am_byte(r.d[0],(value&128U)?255U:0U);am_byte(r.d[7],r.d[7]|r.d[0]);
        r.a[0]=r.a[5]-0x7258U;
        if(!am_read(c,r.a[0]+0x61U,1,value))return false;am_byte(r.d[0],(value&128U)?255U:0U);am_byte(r.d[7],r.d[7]|r.d[0]);
        r.pc=(r.d[7]&255U)?0x47f3e:0x47f42;return true;
    case 0x47f3e:r.pc=0x480bc;return true;
    case 0x47f42:return am_call(c,0x48398,0x47f46);
    case 0x47f46:r.pc=0x47c5a;return true;
    case 0x47f4a:am_word(r.d[0],0x1890);r.pc=0x47f4e;return true;
    case 0x47f4e:return am_call(c,0x3af8,0x47f54);
    case 0x47f54:am_word(r.d[0],0x1891);r.pc=0x47f58;return true;
    case 0x47f58:return am_call(c,0x3af8,0x47f5e);
    case 0x47f5e:am_word(r.d[0],0x1892);r.pc=0x47f62;return true;
    case 0x47f62:return am_call(c,0x3af8,0x47f68);
    case 0x47f68:return am_call(c,0x3c84,0x47f6e);
    case 0x47f6e:return am_call(c,0x3d44,0x47f74);
    case 0x47f74:
        if(!am_push(c,4,r.d[0]))return false;r.pc=0x47f78;return true;
    case 0x47f78:am_word(r.d[0],0x19dc);r.pc=0x47f7c;return true;
    case 0x47f7c:return am_call(c,0x3af8,0x47f82);
    case 0x47f82:
        if(!am_pop(c,4,value))return false;r.d[0]=value;r.pc=0x47f86;return true;
    case 0x47f86:r.pc=(r.d[0]&255U)?0x47f9c:0x47f8e;return true;
    case 0x47f8e:r.d[0]=0;r.d[1]=r.d[2]=0xffffffe1U;r.d[3]=32;r.pc=0x47f96;return true;
    case 0x47f96:return am_call(c,0x8c16,0x47f9c);
    case 0x47f9c:
        if(!object_write(c,0x7a,2,32) || !object_write(c,0,4,0x47fa8))return false;r.pc=0x47fa8;return true;
    case 0x47fa8:
        if(!am_read(c,r.a[6]+0x7aU,2,value) || !object_write(c,0x7a,2,value-1U))return false;
        r.pc=((value-1U)&65535U)?0x480bc:0x47fb0;return true;
    case 0x47fb0:r.d[0]=r.d[1]=r.d[2]=0xffffffe1U;r.d[3]=32;r.pc=0x47fb8;return true;
    case 0x47fb8:return am_call(c,0x8c16,0x47fbe);
    case 0x47fbe:return am_call(c,0x4e24e,0x47fc4);
    case 0x47fc4:return am_call(c,0xca7e,0x47fca);
    case 0x1c63c:r.a[0]=0x100cb8;r.pc=0x1c642;return true;
    case 0x1c642:return am_call(c,0x289e,0x1c648);
    case 0x1c648:return branch_carry(c,0x1c658,0x1c64c);
    case 0x1c64c:
        if(!am_read(c,r.a[0]+0xa8U,1,value) || !am_write(c,r.a[0]+0xa8U,1,value|2U) ||
            !am_write(c,r.a[0]+0x5eU,1,6))return false;
        r.pc=0x1c658;return true;
    case 0x1c658:r.a[0]=0x100da8;r.pc=0x1c65e;return true;
    case 0x1c65e:return am_call(c,0x289e,0x1c664);
    case 0x1c664:return branch_carry(c,0x1c674,0x1c668);
    case 0x1c668:
        if(!am_read(c,r.a[0]+0xa8U,1,value) || !am_write(c,r.a[0]+0xa8U,1,value|2U) ||
            !am_write(c,r.a[0]+0x5eU,1,6))return false;
        r.pc=0x1c674;return true;
    case 0x48398:return am_call(c,0x30f4,0x4839e);
    case 0x4839e:
        if(!am_write(c,r.a[5]+0x567eU,1,r.d[0]) || !am_write(c,r.a[5]+0x567fU,1,255))return false;
        return am_return(c);
    case 0x30f4:
        if(!am_read(c,0x10fd8c,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]&7U);
        if(!am_read(c,am_index(0x30ec,r.d[0]),1,value))return false;am_byte(r.d[0],value);return am_return(c);
    case 0x3c84:
        if(!am_write(c,r.a[5]-0x3282U,1,0))return false;return am_return(c);
    case 0x3d44:am_byte(r.d[0],8);r.pc=0x3d48;return true;
    case 0x3d48:return am_call(c,0x3ac8,0x3d4c);
    case 0x3d4c:am_byte(r.d[0],0x20);r.pc=0x3ac8;return true;
    case 0x4e24e:
        if(!am_write(c,r.a[5]+0x5d1fU,1,0))return false;return am_return(c);
    case 0xca7e:
        if(!am_write(c,r.a[5]-0x769bU,1,0))return false;return am_return(c);
    case 0x8c16: {
        ObjectRestartState leaf;
        for(unsigned int i=0;i<8;++i)leaf.d[i]=r.d[i];
        for(unsigned int i=0;i<7;++i)leaf.a[i]=r.a[i];
        if(!execute_palette_effect(c.ram,leaf,c.error))return false;
        for(unsigned int i=0;i<8;++i)r.d[i]=leaf.d[i];
        for(unsigned int i=0;i<7;++i)r.a[i]=leaf.a[i];
        return am_return(c);
    }
    case 0x1c674:case 0x483a8:case 0x3102:case 0x3c88:case 0x4e252:case 0xca82:
    case 0x8ca4:case 0x8cc8:return am_return(c);
    default:return am_error(c,"unsupported animation exit PC");
    }
}
}
