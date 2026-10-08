#include "animation_machine_internal.h"
#include <new>
namespace ms5 {
void am_byte(std::uint32_t& r,std::uint32_t value) {r=(r&0xffffff00U)|(value&255U);}
void am_word(std::uint32_t& r,std::uint32_t value) {r=(r&0xffff0000U)|(value&65535U);}
void am_swap(std::uint32_t& r) {r=(r<<16)|(r>>16);}
std::uint32_t am_extend_word(std::uint32_t value) {
    return (value&0x8000U)?(value|0xffff0000U):(value&65535U);
}
std::uint32_t am_index(std::uint32_t base,std::uint32_t word) {return base+am_extend_word(word);}
bool am_error(AnimationMachineContext& c,const char* message) {c.error=message;return false;}
bool am_read(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t& value) {
    if ((address&0xffffffU)==0xd00046U && size==1) {
        ++c.external_reads;value=c.external_status;return true;
    }
    c.bus.bank_base=c.device.bank_base;
    return read_program_bus(c.ram,c.windows,c.bus,address,size,value,c.error);
}
namespace {
bool carry_preserving_pc(std::uint32_t pc) {
    // Entire original blocks must preserve C. Shared bus/stack operations do
    // not imply MOVE flags: MOVEM, PEA, JSR and RTS use those operations too.
    switch(pc) {
    case 0x1dc84:case 0x1dc8a:case 0x210ae:case 0x210b4:
    case 0x47d0a:case 0x47d14:case 0x47d1a:case 0x47f04:
    case 0x47cc0:case 0x47cc6:case 0x47ce6:
    case 0x47d20:case 0x47d3e:case 0x47d42:
    case 0x4847e:case 0x48484:case 0x4848a:case 0x48490:case 0x4849c:
    case 0x484ac:case 0x484b2:case 0x1bdee:case 0x1bdf4:case 0x1bdf8:
    case 0x1be02:case 0x1be0c:case 0x1be12:case 0x1be32:case 0x1be38:
    case 0x28ac:case 0x4df0e:case 0x4df18:case 0x4e184:
    case 0x47c7a:case 0x47c88:case 0x47c8c:
    case 0x4e2c8:case 0x4e2ea:case 0x4e30c:
    case 0x4e330:case 0x4847a:case 0x8cf2:case 0x8d32:case 0x3628:case 0x35f0:
    case 0x47d24:case 0x47d2a:case 0x47d2e:case 0x47d34:
    case 0x47d58:case 0x47d5c:case 0x47d92:case 0x47d98:case 0x47da0:
    case 0x477bc:case 0x4e246:case 0x4e24c:case 0xc28:case 0xc34:
    case 0x35a8:case 0x35ee:
    case 0x49fea:case 0x4a0e2:case 0x4a124:case 0x4a132:case 0x4a148:
    case 0x3679e:case 0x4a104:case 0x4a108:case 0x4a272:case 0x4a270:
    case 0x4a2ec:case 0x2b3f8:case 0x2b40a:
    case 0xcd50:case 0xcd56:case 0xce00:case 0xcd58:
    case 0x3ad8:case 0x3ae0:case 0x3b98:case 0x3ba8:case 0x3bca:
    case 0x3be4:case 0x3bfc:case 0x3c02:case 0xca70:
    case 0x47672:case 0x47688:case 0x4768e:case 0x476a4:
    case 0x3ad6:case 0x3af6:case 0x3b06:case 0x3b14:case 0x3b1e:
    case 0x3b28:case 0x3b3e:case 0x3b5e:case 0x3b6c:case 0x3b80:
    case 0x3b96:case 0x3bc8:case 0x3be2:case 0x3c06:case 0xca74:
    case 0x476ba:
    // BTST/BEQ changes only Z; its known memory test is already modeled.
    case 0x3b82:return true;
    default:return false;
    }
}
std::uint32_t pvc_word(const AnimationMachineDevice& device,unsigned int index) {
    return (static_cast<std::uint32_t>(device.pvc[index*2])<<8)|device.pvc[index*2+1];
}
void pvc_put(AnimationMachineDevice& device,unsigned int index,std::uint32_t value) {
    device.pvc[index*2]=static_cast<std::uint8_t>(value>>8);
    device.pvc[index*2+1]=static_cast<std::uint8_t>(value);
}
// Device equations follow the pinned MAME PVC reference. See
// tools/licenses/mame-pvc.txt (BSD-3-Clause), S. Smith, David Haywood, Fabio Priuli.
void pvc_effects(AnimationMachineDevice& device,unsigned int index) {
    if (index==0xff0) {
        const std::uint32_t pen=pvc_word(device,0xff0);
        const std::uint32_t blue=((pen&15U)<<1)|((pen>>12)&1U);
        const std::uint32_t green=((pen&0xf0U)>>3)|((pen>>13)&1U);
        const std::uint32_t red=((pen&0xf00U)>>7)|((pen>>14)&1U);
        pvc_put(device,0xff1,(green<<8)|blue);
        pvc_put(device,0xff2,((pen>>15)<<8)|red);
    } else if (index==0xff4 || index==0xff5) {
        const std::uint32_t gb=pvc_word(device,0xff4),sr=pvc_word(device,0xff5);
        pvc_put(device,0xff6,((gb&0x1eU)>>1)|((gb&0x1e00U)>>5)|((sr&0x1eU)<<7)|
            ((gb&1U)<<12)|((gb&0x100U)<<5)|((sr&1U)<<14)|((sr&0x100U)<<7));
    }
    if (index>=0xff8) {
        const std::uint32_t ff8=pvc_word(device,0xff8),ff9=pvc_word(device,0xff9);
        device.bank_base=0x100000U+((ff8>>8)|(ff9<<8));
        pvc_put(device,0xff8,(ff8&0xfe00U)|0xa0U);
        pvc_put(device,0xff9,ff9&0x7fffU);
    }
}
}
bool am_write(AnimationMachineContext& c,std::uint32_t logical,unsigned int size,std::uint32_t value) {
    if ((size!=1 && size!=2 && size!=4) || (size>1 && (logical&1U)))
        return am_error(c,"invalid animation machine write size/alignment");
    const unsigned int unit=size==1?1:2;
    // The public invocation owns rollback across all units and device effects.
    for (unsigned int offset=0;offset<size;offset+=unit) {
        const std::uint32_t address=(logical+offset)&0xffffffU;
        const std::uint32_t part=(value>>(8*(size-offset-unit)))&(unit==1?255U:65535U);
        if (address>=0x100000U && address<0x200000U) {
            if (!write_program_bus_ram(c.ram,logical+offset,unit,part,c.error))return false;
        } else if (address>=0x2fe000U && address<0x300000U) {
            const unsigned int at=address-0x2fe000U;
            for (unsigned int i=0;i<unit;++i)c.device.pvc[at+i]=static_cast<std::uint8_t>(part>>(8*(unit-i-1)));
            VideoPortWrite port;port.address=address;port.size=static_cast<std::uint8_t>(unit);port.value=part;
            c.ports.push_back(port);pvc_effects(c.device,at/2);
        } else return am_error(c,"unsupported animation machine write device");
    }
    c.bus.bank_base=c.device.bank_base;return true;
}
bool am_fetch(AnimationMachineContext& c,unsigned int size,std::uint32_t& value) {
    if (!am_read(c,c.s.a[1],size,value))return false;
    c.s.a[1]+=size;return true;
}
bool am_push(AnimationMachineContext& c,unsigned int size,std::uint32_t value) {
    return push_program_stack(c.ram,c.s.a[7],size,value,c.error);
}
bool am_pop(AnimationMachineContext& c,unsigned int size,std::uint32_t& value) {
    c.bus.bank_base=c.device.bank_base;
    return pop_program_stack(c.ram,c.windows,c.bus,c.s.a[7],size,value,c.error);
}
bool am_call(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    if (!am_push(c,4,return_pc))return false;c.s.pc=target;return true;
}
bool am_return(AnimationMachineContext& c) {
    std::uint32_t target=0;if (!am_pop(c,4,target))return false;c.s.pc=target;return true;
}
bool am_zero_bank(AnimationMachineContext& c) {
    return am_write(c,c.s.a[5]-0x7ff0U,2,0) && am_write(c,0x2ffff2,2,0x1000) && am_write(c,0x2ffff0,2,0);
}
bool run_animation_machine(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,const ProgramBusState& resources,
    AnimationMachineState& state,AnimationMachineDevice& device,
    std::uint32_t stop_pc,std::uint8_t external_status,std::uint32_t& external_reads,
    AnimationMachineStatus& status,std::vector<VideoPortWrite>& ports,std::string& error) {
    if (ram.size()!=65536 || device.pvc.size()!=8192 || (stop_pc&1U)) {
        error="invalid animation machine RAM/PVC/stop PC";return false;
    }
    if (state.carry!=AnimationCarryUnknown && state.carry!=AnimationCarryClear && state.carry!=AnimationCarrySet) {
        error="invalid animation machine carry state";return false;
    }
    try {
        std::vector<std::uint8_t> next_ram=ram;
        AnimationMachineState next=state;AnimationMachineDevice next_device=device;
        std::vector<VideoPortWrite> next_ports;
        AnimationMachineContext c(next_ram,windows,resources,next,next_device,next_ports,external_status,error);
        AnimationMachineStatus result=AnimationMachineReturned;bool stopped=false;
        for (unsigned int steps=0;steps<100000;++steps) {
            if (next.pc==stop_pc) {stopped=true;break;}
            if (next.pc&1U)return am_error(c,"unaligned animation machine PC");
            if (!carry_preserving_pc(next.pc))next.carry=AnimationCarryUnknown;
            bool ok=false;
            if ((next.pc>=0x3ac8 && next.pc<0x3c08) || (next.pc>=0x47672 && next.pc<0x476bc) ||
                (next.pc>=0xca70 && next.pc<0xca76))ok=animation_sound_block(c);
            else if ((next.pc>=0xcd50 && next.pc<0xce02) || next.pc==0x16ea4 || next.pc==0x16ed2)ok=animation_sprite_block(c);
            else if (next.pc==0x47d20 || next.pc==0x47d3e || next.pc==0x47d42 ||
                (next.pc>=0x4847c && next.pc<0x484b4) || (next.pc>=0x1bdde && next.pc<0x1be3a) ||
                (next.pc>=0x289e && next.pc<0x28ae) || (next.pc>=0x4dee2 && next.pc<0x4df1a) ||
                (next.pc>=0x4e166 && next.pc<0x4e186))ok=animation_readiness_block(c);
            else if ((next.pc>=0x47c6c && next.pc<0x47cae) || (next.pc>=0x4843c && next.pc<=0x4847a) ||
                (next.pc>=0x4e286 && next.pc<=0x4e330) || (next.pc>=0x8cda && next.pc<=0x8d32) ||
                (next.pc>=0x35f0 && next.pc<=0x3628))ok=animation_hud_block(c);
            else if ((next.pc>=0x47d24 && next.pc<0x47da4) || next.pc==0x477ac || next.pc==0x477bc ||
                (next.pc>=0x4e216 && next.pc<=0x4e24c) || (next.pc>=0xbee && next.pc<=0xc34) ||
                (next.pc>=0x35a2 && next.pc<=0x35ee))ok=animation_transition_block(c);
            else if ((next.pc>=0x49f8c && next.pc<0x4a46c) || next.pc==0x3679e ||
                next.pc==0x47cec || next.pc==0x47d0a || next.pc==0x47d10 ||
                next.pc==0x47d14 || next.pc==0x47d1a || next.pc==0x47f04 ||
                next.pc==0x47cae || next.pc==0x47cc0 || next.pc==0x47cc6 || next.pc==0x47cca || next.pc==0x47ce6 ||
                next.pc==0x1dc84 || next.pc==0x1dc8a || next.pc==0x210ae || next.pc==0x210b4 ||
                (next.pc>=0x2b3e8 && next.pc<0x2b40c))ok=animation_interpreter_block(c);
            else return am_error(c,"unsupported animation machine PC");
            if (!ok)return false;
            if (c.waiting) {result=AnimationMachineWaiting;stopped=true;break;}
        }
        if (!stopped)return am_error(c,"animation machine block budget exceeded");
        ram.swap(next_ram);state=next;
        device.pvc.swap(next_device.pvc);device.bank_base=next_device.bank_base;
        ports.swap(next_ports);external_reads=c.external_reads;status=result;error.clear();return true;
    } catch (const std::bad_alloc&) {error="cannot allocate animation machine transaction";return false;}
}
}
