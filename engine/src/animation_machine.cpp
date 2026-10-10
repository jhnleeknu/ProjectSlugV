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
    case 0x47eb2:case 0x47ed6:case 0x47ee0:case 0x47ef8:case 0x47f42:case 0x47f46:
    case 0x47f4e:case 0x47f58:case 0x47f62:case 0x47f68:case 0x47f6e:case 0x47f74:
    case 0x47f7c:case 0x47f82:case 0x47f96:case 0x47fb8:case 0x47fbe:case 0x47fc4:case 0x47f3e:
    case 0x1c63c:case 0x1c642:case 0x1c648:case 0x1c658:case 0x1c65e:case 0x1c664:case 0x1c674:
    case 0x48398:case 0x483a8:case 0x3102:case 0x3c88:case 0x3d48:
    case 0x4e252:case 0xca82:case 0x8ca4:case 0x8cc8:
    case 0xca9e:case 0xcab8:case 0xcaee:case 0xcaf0:case 0xcaf2:
    case 0xcb08:case 0xcb1c:case 0xcb30:case 0xcb44:case 0xcb58:case 0xcb62:case 0x47fca:
    case 0x271c:case 0x2722:case 0x2728:case 0x2780:case 0x2782:case 0x2788:case 0x278e:
    case 0x288a:case 0x29a8:case 0x29ba:case 0x29c0:case 0x29c4:case 0x29c8:case 0x29fe:
    case 0x2a16:case 0x2a1a:case 0x2a1c:case 0x2a1e:case 0x2a3c:case 0x2a40:case 0x2a44:case 0x2a46:
    case 0x2a58:case 0x2a5c:case 0x2a5e:case 0x2a7c:case 0x2a80:case 0x2a82:
    case 0x2aa0:case 0x2aa4:case 0x2aa8:case 0x2aaa:
    case 0x8ebc:case 0x9000:case 0x9028:case 0x9036:case 0x8e80:
    case 0x43dcc:case 0x43dd4:case 0x43dd8:case 0x43e02:case 0x43e90:case 0x43ea2:
    case 0xc3e6:case 0xc3ec:case 0xc3f2:case 0xc3f8:case 0xc3fa:case 0xc400:
    case 0x4aa2e:case 0xe90d6:case 0x46ef2:case 0x46f26:case 0x46f2c:case 0x8bc0:case 0x3de4:
    case 0x477c2:case 0x477c8:case 0x477d6:case 0x477dc:case 0x477e2:case 0x47fe4:
    // Scene blocks contain only flag-preserving LEA/MOVEA/MOVEM/PEA,
    // calls, branches or RTS. Plain MOVE stack stores are intentionally absent.
    case 0x47fe8:case 0x47fec:case 0x43ffc:case 0x44004:case 0x44008:case 0x4402c:case 0x44030:
    case 0x44078:case 0x4407e:case 0x44086:case 0x4408e:case 0x44094:
    case 0x43f5c:case 0x43f60:case 0x43f70:case 0x43f94:case 0x43f9a:case 0x43faa:
    case 0x43fce:case 0x43fd4:case 0x43fda:case 0x43ff8:case 0x43ffa:
    case 0x440ec:case 0x4410a:case 0x4411c:case 0x43f3e:case 0x43f44:case 0x43f4a:case 0x43f5a:
    case 0xccd6:case 0xcd0c:case 0xcd16:case 0xcd1a:case 0xcd46:
    case 0x1adb0:case 0x1adb6:case 0x1adba:case 0x1adc0:case 0x1adc4:case 0x1adca:case 0x1adce:case 0x1add4:
    case 0x1adee:case 0x1adf2:case 0x43f3c:case 0x16f9e:case 0x16fa2:case 0x16fa6:case 0x16faa:
    case 0x182ce:case 0x1724a:case 0x1831a:
    case 0x8da2:case 0x8db8:case 0x8e44:case 0x8e48:case 0x8ea6:case 0x8eb4:
    case 0xe7bf4:case 0xe7bfa:case 0xe7bfe:case 0xe7c10:case 0xe7c36:case 0xe7c3a:case 0xe7c3e:
    case 0x47ff2:case 0x48012:case 0x4801a:case 0x4801e:case 0x48024:case 0x4802a:
    case 0x48030:case 0x48034:case 0x4803c:case 0x16fac:case 0x16fec:case 0x17010:
    case 0x16f5a:case 0x16f5e:case 0x16f6e:case 0x16f98:
    case 0x18424:case 0x18440:case 0x18448:case 0x1844c:case 0x184ce:
    case 0x18530:case 0x18552:case 0x185a2:case 0x185e8:case 0x185f2:case 0x185f8:
    case 0x18650:case 0x18654:case 0x18702:case 0x18720:case 0x1873e:case 0x18742:
    case 0x18746:case 0x1874a:case 0x1874e:case 0x18758:case 0x18760:case 0x18764:
    case 0x18768:case 0x18772:case 0x18778:case 0x1877c:case 0x18780:case 0x18784:
    case 0x18788:case 0x18796:case 0x1879a:case 0x48042:case 0x48048:case 0x17018:
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
    // Fade/card/child/dispatcher blocks: JSR/JMP/BSR/BRA/RTS/LEA/MOVEA only.
    // 290c/2916 are the RTS after ORI/ANDI CCR, which set known C first.
    case 0x48058:case 0x4807e:case 0x4809a:case 0x480a0:case 0x480b6:
    case 0x48072:case 0x48098:case 0x480b4:case 0xc376:case 0xc37c:case 0xc37e:
    case 0xc39c:case 0xc3b6:case 0xc3be:case 0x28ae:case 0x290c:case 0x2916:
    case 0x2a00:case 0x2a02:case 0x2a06:case 0x2ab8:case 0x2abe:case 0x2ac0:case 0x2ac2:case 0x2ac6:
    // Card child c250/de424/e7c16 blocks: JSR (abs or d16(PC))/JMP/RTS/LEA/MOVEA.W #0 only.
    case 0xc258:case 0xc264:case 0xc266:case 0xc274:case 0xc28e:case 0xc2a2:
    case 0xde424:case 0xde450:case 0xde456:case 0xde45a:case 0xde460:case 0xde466:
    case 0xde46c:case 0xde478:case 0xde47e:case 0xde484:case 0xde48a:
    case 0xe7c16:case 0xe7c1a:case 0xe7c1e:case 0xe7c30:
    // Card menu a0a0/38e8/c2a8 blocks: JSR/RTS/LEA only. ADDA/SUBA blocks stay Unknown.
    case 0xa0c2:case 0xa158:case 0xa17e:case 0x3878:case 0x38a4:case 0xc2a8:case 0xa2bc:case 0xc2ba:
    // Card menu open blocks: BSR/JSR/JMP/BRA/RTS/LEA/MOVEA/MOVEM/BTST and conditional branches only.
    // The a018 caller BCS blocks consume the C set by a06c (ANDI CCR) or a076 (ORI CCR).
    case 0x391a:case 0x3926:case 0x3928:case 0x392a:case 0x9b54:case 0x9b56:case 0x9b64:case 0x9b78:
    case 0x9ba6:case 0x9bc8:case 0x9bcc:case 0x9be6:case 0x9bea:case 0x9c10:case 0x9c32:case 0x9c36:
    case 0x9c50:case 0x9c54:case 0x9c76:case 0x9c98:case 0x9c9c:case 0x9cb6:case 0x9cba:case 0x9cd4:
    case 0x9cd8:case 0x9cf8:case 0x9cfc:case 0x9d1e:case 0x9d22:case 0x9d38:case 0x9d4a:case 0x9d92:
    case 0x9d96:case 0x9dc0:case 0x9dd6:case 0x9dfe:case 0x9e02:case 0x9e14:case 0x9e26:case 0x9e34:
    case 0x9e72:case 0x9e92:case 0xa008:case 0xa00c:case 0xa016:case 0xa040:case 0xa238:case 0xa348:
    case 0xa36e:case 0xa396:case 0xa3a8:case 0xa3b4:case 0xa3c6:case 0xa5e2:case 0xa61c:case 0xa624:
    case 0xbf94:case 0xbfbc:case 0xc1c4:case 0xc1e6:case 0xc1ee:case 0xc1f4:case 0xc1fe:case 0xc202:
    case 0xc208:case 0xc212:case 0xc2c6:case 0xe84d0:
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
        // A legitimate 65536-column WORD loop exceeds the former 100000-block cap.
        // Keep a finite limit; malformed record walks and huge transfers still fail atomically.
        for (unsigned int steps=0;steps<1000000;++steps) {
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
            else if ((next.pc>=0x47eac && next.pc<0x47fca && next.pc!=0x47f04) || next.pc==0x47c5a ||
                (next.pc>=0x1c63c && next.pc<0x1c676) || (next.pc>=0x48398 && next.pc<=0x483a8) ||
                (next.pc>=0x30f4 && next.pc<=0x3102) || next.pc==0x3c84 || next.pc==0x3c88 ||
                next.pc==0x3d44 || next.pc==0x3d48 || next.pc==0x3d4c || next.pc==0x4e24e || next.pc==0x4e252 ||
                next.pc==0xca7e || next.pc==0xca82 || next.pc==0x8c16 || next.pc==0x8ca4 || next.pc==0x8cc8)ok=animation_exit_block(c);
            else if ((next.pc>=0x271c && next.pc<=0x278e) || next.pc==0x287e || next.pc==0x288a ||
                (next.pc>=0x299c && next.pc<=0x29fe) || (next.pc>=0x2a0a && next.pc<=0x2aaa) ||
                (next.pc>=0x8ff4 && next.pc<=0x9036) || next.pc==0x8e4a || next.pc==0x8e80 ||
                next.pc==0x8eb6 || next.pc==0x8ebc || (next.pc>=0x43dcc && next.pc<=0x43ea2) ||
                (next.pc>=0xc3dc && next.pc<=0xc400) || next.pc==0x4aa06 || next.pc==0x4aa2e ||
                next.pc==0xe90ca || next.pc==0xe90d6 || next.pc==0x46eec || next.pc==0x46ef2 ||
                next.pc==0x46ef4 || next.pc==0x46f08 || next.pc==0x46f26 || next.pc==0x46f2c ||
                next.pc==0x8bbc || next.pc==0x8bc0 || next.pc==0x3dce || next.pc==0x3de4 ||
                (next.pc>=0x477c2 && next.pc<=0x477e2) || next.pc==0x47fe4)ok=animation_cleanup_block(c);
            else if ((next.pc>=0xca9e && next.pc<=0xcb62) || next.pc==0x47fca || next.pc==0x47fd0 || next.pc==0x47fdc)ok=animation_screen_block(c);
            else if (next.pc==0x47fe8 || next.pc==0x47fec || (next.pc>=0x43efa && next.pc<=0x4411c) ||
                (next.pc>=0xccd6 && next.pc<=0xcd48) || (next.pc>=0x1ad9a && next.pc<=0x1adf2) ||
                (next.pc>=0x16f9a && next.pc<=0x16faa) || (next.pc>=0x1829a && next.pc<=0x1831a) ||
                next.pc==0x1701a || next.pc==0x17028 || next.pc==0x1704a || next.pc==0x1724a)ok=animation_scene_block(c);
            else if ((next.pc>=0x8da2 && next.pc<=0x8e48) || (next.pc>=0x8e82 && next.pc<=0x8eb4) ||
                (next.pc>=0xe7bf4 && next.pc<=0xe7c10) || (next.pc>=0xe7c36 && next.pc<=0xe7c3e) ||
                (next.pc>=0x47ff2 && next.pc<0x48042) || (next.pc>=0x16fac && next.pc<=0x16fec) ||
                (next.pc>=0x16ff8 && next.pc<=0x17010))ok=animation_palette_bind_block(c);
            else if ((next.pc>=0x16f0e && next.pc<=0x16f98) || (next.pc>=0x183c6 && next.pc<=0x184ce) ||
                (next.pc>=0x18530 && next.pc<=0x185f8) || (next.pc>=0x1861a && next.pc<=0x18654) ||
                (next.pc>=0x18702 && next.pc<=0x1879a) || next.pc==0x48042 || next.pc==0x48048 ||
                next.pc==0x17012 || next.pc==0x17018)ok=animation_map_transfer_block(c);
            else if ((next.pc>=0x49f8c && next.pc<0x4a46c) || next.pc==0x3679e ||
                next.pc==0x47cec || next.pc==0x47d0a || next.pc==0x47d10 ||
                next.pc==0x47d14 || next.pc==0x47d1a || next.pc==0x47f04 ||
                next.pc==0x47cae || next.pc==0x47cc0 || next.pc==0x47cc6 || next.pc==0x47cca || next.pc==0x47ce6 ||
                next.pc==0x1dc84 || next.pc==0x1dc8a || next.pc==0x210ae || next.pc==0x210b4 ||
                (next.pc>=0x2b3e8 && next.pc<0x2b40c))ok=animation_interpreter_block(c);
            else if ((next.pc>=0x4804e && next.pc<=0x480b6) || (next.pc>=0xc364 && next.pc<=0xc3be) ||
                (next.pc>=0x28ae && next.pc<=0x2916) || next.pc==0x2a00 || next.pc==0x2a02 || next.pc==0x2a06 ||
                (next.pc>=0x2ab8 && next.pc<=0x2ac6))ok=animation_fade_card_block(c);
            else if ((next.pc>=0xc250 && next.pc<=0xc2a2) || (next.pc>=0xde424 && next.pc<=0xde48a) ||
                (next.pc>=0xe7c16 && next.pc<=0xe7c30))ok=animation_card_child_block(c);
            else if ((next.pc>=0xa0a0 && next.pc<=0xa1e0) || (next.pc>=0xa29c && next.pc<=0xa2bc) ||
                (next.pc>=0x386e && next.pc<=0x38fe && next.pc!=0x38c8 && next.pc!=0x38e2) ||
                (next.pc>=0xc2a8 && next.pc<=0xc2ba))ok=animation_card_menu_block(c);
            else if ((next.pc>=0x3650 && next.pc<=0x366e) || (next.pc>=0x3918 && next.pc<=0x392a) ||
                (next.pc>=0x9b26 && next.pc<=0x9e92) || (next.pc>=0x9f7c && next.pc<=0x9fc2) ||
                (next.pc>=0xa008 && next.pc<=0xa07e) || (next.pc>=0xa216 && next.pc<=0xa27e) ||
                (next.pc>=0xa348 && next.pc<=0xa404) || (next.pc>=0xa5d2 && next.pc<=0xa660 && next.pc!=0xa63c) ||
                (next.pc>=0xa73e && next.pc<=0xa758) || (next.pc>=0xbf94 && next.pc<=0xbfbc) ||
                (next.pc>=0xc1c4 && next.pc<=0xc212) || (next.pc>=0xc2c0 && next.pc<=0xc2c6) ||
                (next.pc>=0xe84c8 && next.pc<=0xe84d0))ok=animation_card_menu_open_block(c);
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
