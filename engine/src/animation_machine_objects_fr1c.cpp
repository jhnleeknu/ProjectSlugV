#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr1c_w(std::uint32_t value) {return value&65535U;}
// The low WORD as a signed value (CMPI.W / BLE / BLT / BGE on WORDs).
std::int32_t ofr1c_signed_word(std::uint32_t value) {
    const std::uint32_t w=value&65535U;return (w&0x8000U)!=0U?static_cast<std::int32_t>(w)-65536:static_cast<std::int32_t>(w);
}
// ASR.L #count (1..8) of a 32-bit value: arithmetic, the sign bit is replicated (no signed shift in C++).
std::uint32_t ofr1c_asr_long(std::uint32_t value,unsigned int count) {
    const std::uint32_t fill=(value&0x80000000U)!=0U?~(0xffffffffU>>count):0U;return (value>>count)|fill;
}
// ASR.W #1 of the low WORD (the WORD sign bit is kept).
std::uint32_t ofr1c_asr_word1(std::uint32_t value) {
    const std::uint32_t w=value&65535U;return (w>>1)|(w&0x8000U);
}
bool ofr1c_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr1c_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG); the fall-through enters the installed callback.
bool ofr1c_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ofr1c_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #value,(A6) followed by the next block (not the installed value).
bool ofr1c_callback(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next) {
    if(!ofr1c_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next;return true;
}
// MOVE.W #value,d(A6) then MOVE.L #install,(A6) (the fall-through enters the installed value).
bool ofr1c_set_install(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,std::uint32_t install) {
    if(!ofr1c_put(c,c.s.a[6],displacement,2,value))return false;return ofr1c_install(c,install);
}
// MOVE.W #value,68(A6); MOVE.W #value,1e(A6).
bool ofr1c_68_1e(AnimationMachineContext& c,std::uint32_t value) {
    return ofr1c_put(c,c.s.a[6],0x68,2,value) && ofr1c_put(c,c.s.a[6],0x1e,2,value);
}
// SUBQ.W #1,76(A6); BCC.W borrow_clear_pc (the old WORD was not 0: no borrow); otherwise (old WORD 0, C set) next_pc.
bool ofr1c_decrement(AnimationMachineContext& c,std::uint32_t borrow_clear_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ofr1c_get(c,c.s.a[6],0x76,2,value))return false;
    if(!ofr1c_put(c,c.s.a[6],0x76,2,value-1U))return false;c.s.pc=ofr1c_w(value)!=0U?borrow_clear_pc:next_pc;return true;
}
// BTST.B #bit,d(A6); BEQ.W zero_pc (bit clear); otherwise set_pc.
bool ofr1c_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;if(!ofr1c_get(c,c.s.a[6],displacement,1,value))return false;c.s.pc=((value>>bit)&1U)==0U?zero_pc:set_pc;return true;
}
// BSET.B / BCHG.B #bit,d(A6) (only Z changes; Z is not read).
bool ofr1c_bset(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;if(!ofr1c_get(c,c.s.a[6],displacement,1,value))return false;return ofr1c_put(c,c.s.a[6],displacement,1,value|(1U<<bit));
}
bool ofr1c_bchg(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit) {
    std::uint32_t value=0;if(!ofr1c_get(c,c.s.a[6],displacement,1,value))return false;return ofr1c_put(c,c.s.a[6],displacement,1,value^(1U<<bit));
}
// BCC / BCS on a known C (returned by a callee, or the CMP C of 49432 / 49452): clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ofr1c_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr1c caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #n,D0; JSR 28ae.l (28ae child).
bool ofr1c_28ae(AnimationMachineContext& c,std::uint32_t child,std::uint32_t n,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],n);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #d0,D0; MOVE.B #0,D1; JSR 8ebe.l (sound).
bool ofr1c_8ebe(AnimationMachineContext& c,std::uint32_t d0,std::uint32_t return_pc) {
    am_word(c.s.d[0],d0);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #e3,20(A6); MOVEA.L #a1,A1; MOVE.W #100,D0; JSR 49f8c.l (A0 as left by the previous block).
bool ofr1c_fixed_anim(AnimationMachineContext& c,std::uint32_t a1,std::uint32_t return_pc) {
    if(!ofr1c_put(c,c.s.a[6],0x20,2,0xe3))return false;c.s.a[1]=a1;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L bank.l,22(A6); MOVE.W #d0,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus).
bool ofr1c_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t bank,std::uint32_t displacement,std::uint32_t d0,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr1c_put(c,c.s.a[6],0x20,2,n) || !am_read(c,bank,4,value) || !ofr1c_put(c,c.s.a[6],0x22,4,value))return false;
    am_word(c.s.d[0],d0);c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr1c_get(c,c.s.a[6],0x22,4,value))return false;c.s.a[1]=value;
    if(!ofr1c_get(c,c.s.a[1],displacement,4,value))return false;c.s.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// bc0da ... bc5e8: the bank animation of the bc08c object (MOVE.W #e3,20(A6); bank window 200140).
bool ofr1c_anim(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    return ofr1c_bank_anim(c,0xe3,0x200140,displacement,0x100,return_pc);
}
// MOVE.L 64(A6),D0; SUB.L 36(A6),D0; ASR.L #5,D0; ADD.L D0,36(A6); MOVE.L #fff00000,D0; SUB.L 3a(A6),D0; ASR.L #5,D0; ADD.L D0,3a(A6);
// JSR 4be34.l (bc246 / bc2be).
bool ofr1c_ease(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;std::uint32_t other=0;AnimationMachineState& r=c.s;
    if(!ofr1c_get(c,r.a[6],0x64,4,value) || !ofr1c_get(c,r.a[6],0x36,4,other))return false;r.d[0]=ofr1c_asr_long(value-other,5);
    if(!ofr1c_get(c,r.a[6],0x36,4,value) || !ofr1c_put(c,r.a[6],0x36,4,value+r.d[0]))return false;
    if(!ofr1c_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ofr1c_asr_long(0xfff00000U-value,5);
    if(!ofr1c_get(c,r.a[6],0x3a,4,value) || !ofr1c_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;
    return am_call(c,0x4be34,return_pc);
}
// MOVE.L #v,36(A6); MOVE.L #v,64(A6); MOVE.L #0,3a(A6); MOVE.L #install,(A6) (bc548 / bc5ac; bc102 adds the WORDs below).
bool ofr1c_speed(AnimationMachineContext& c,std::uint32_t v) {
    return ofr1c_put(c,c.s.a[6],0x36,4,v) && ofr1c_put(c,c.s.a[6],0x64,4,v) && ofr1c_put(c,c.s.a[6],0x3a,4,0);
}
// MOVE.W d(A0),D7; SUB.W d(A6),D7; BTST.B #bit,15(A6); BEQ.W zero_pc (4941e / 4943e).
bool ofr1c_distance(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t set_pc) {
    std::uint32_t value=0;std::uint32_t other=0;
    if(!ofr1c_get(c,c.s.a[0],displacement,2,value))return false;am_word(c.s.d[7],value);
    if(!ofr1c_get(c,c.s.a[6],displacement,2,other))return false;am_word(c.s.d[7],value-other);return ofr1c_bit(c,0x15,bit,zero_pc,set_pc);
}
// SUB.W low(A1),D7; CMP.W size(A1),D7: C = the unsigned borrow of D7.W - WORD size(A1) (49432 / 49452).
bool ofr1c_box(AnimationMachineContext& c,std::uint32_t low,std::uint32_t size,bool& borrow) {
    std::uint32_t value=0;if(!ofr1c_get(c,c.s.a[1],low,2,value))return false;am_word(c.s.d[7],c.s.d[7]-value);
    if(!ofr1c_get(c,c.s.a[1],size,2,value))return false;borrow=ofr1c_w(c.s.d[7])<ofr1c_w(value);
    c.s.carry=borrow?AnimationCarrySet:AnimationCarryClear;return true;
}
}
// Objects FR1c (215 block starts, contract docs/analysis/animation-machine-frontier-fr1c-contract.md): the IO-frontier object bc08c (U17 28ae
// child; bc08c..bc404, bc47c..bc7d6; 34 installed values) and the FR1a 2986 child d13b4 (d13b4..d159e, d2206..d224c; installs d14de d1576 d1586;
// d2206 is also the c6012 table entry) with its shared helpers 4941e (4941e..4945e: the rectangle test of A0 against A6) and 494c0 (494c0..4950e:
// the player choice that ends in N08 49462). Every exit is routed. Known C: 49432 / 49452 leave the unsigned borrow of their CMP.W, 49458
// (EORI.B #1,CCR; RTS) returns the inverted C (Unknown -> checked error), bc7b0 (ORI) Set without a reader. The 15 consumers bc1f6 bc338
// bc394 bc6a2 bc6de bc74e bc78a (49fc6) bc79e (28ae) 494c6 (BCS, 49370) 494e6 494fc (4941e) 49458 d143c (494c0) d153a (4b6f4) d156a (1ab80)
// read a known C or fail. bc3aa recomputes the Z of its only predecessor bc398 (SUBQ.W #1,76(A6)) from WORD 76(A6). Data through the live bus
// (no limit test, as in the original): the bank-window LONGs 200140 / 200090 / 20008c and the LONGs behind them, the rectangle WORDs (A1).
bool animation_objects_fr1c_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool borrow=false;
    switch(r.pc) {
    case 0xbc0c0:case 0xbc1b6:case 0xbc200:case 0xbc28e:case 0xbc2fc:case 0xbc342:case 0xbc402:case 0xbc4ca:case 0xbc51e:case 0xbc582:case 0xbc5e6:
    case 0xbc63e:case 0xbc6ac:case 0xbc6e8:case 0xbc714:case 0xbc758:case 0xbc7c0:case 0xbc7d4:case 0xd1574:
        return am_return(c);                                                                  // RTS.
    // ---- 4941e (JSR entry): MOVE.W 46(A0),D7; SUB.W 46(A6),D7; BTST.B #1,15(A6); BEQ.W 49432 / 49430: NEG.W D7.
    case 0x4941e:return ofr1c_distance(c,0x46,1,0x49432,0x49430);
    case 0x49430:case 0x49450:am_word(r.d[7],0U-r.d[7]);r.pc=r.pc+2U;return true;           // NEG.W D7.
    // SUB.W 2(A1),D7; CMP.W 6(A1),D7; BCC.W 49458 (C clear: taken, C stays Clear; C set: 4943e, C Set).
    case 0x49432:if(!ofr1c_box(c,2,6,borrow))return false;r.pc=borrow?0x4943e:0x49458;return true;
    case 0x4943e:return ofr1c_distance(c,0x42,0,0x49452,0x49450);                            // MOVE.W 42(A0),D7; SUB.W 42(A6),D7; BTST.B #0,15(A6).
    case 0x49452:if(!ofr1c_box(c,0,4,borrow))return false;r.pc=0x49458;return true;          // SUB.W (A1),D7; CMP.W 4(A1),D7.
    // EORI.B #1,CCR; RTS: the known C of 49432 / 49452 inverted (consumer and producer).
    case 0x49458:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects fr1c caller requires known carry");
        r.carry=r.carry==AnimationCarryClear?AnimationCarrySet:AnimationCarryClear;return am_return(c);
    // ---- 494c0 (JSR entry): MOVE.L A0,-(A7); JSR 49370(PC).
    case 0x494c0:if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x49370,0x494c6);
    case 0x494c6:return ofr1c_carry(c,0x494ca,0x49508);                                       // BCS.W 49508 (C of 49370).
    // LEA 100cb8.l,A2; LEA 100da8.l,A3; MOVEA.L (A7)+,A1; BTST #0,D0; BEQ.W 494ee.
    case 0x494ca:r.a[2]=0x100cb8;r.a[3]=0x100da8;if(!am_pop(c,4,value))return false;r.a[1]=value;r.pc=(r.d[0]&1U)==0U?0x494ee:0x494e0;return true;
    case 0x494e0:r.a[0]=r.a[2];return am_call(c,0x4941e,0x494e6);                           // MOVEA.L A2,A0; JSR 4941e(PC).
    case 0x494e6:return ofr1c_carry(c,0x494ee,0x494ea);                                       // BCC.W 494ee (C of 4941e).
    case 0x494ea:am_byte(r.d[0],r.d[0]^1U);r.pc=0x494ee;return true;                         // EORI.B #1,D0.
    case 0x494ee:r.pc=(r.d[0]&2U)==0U?0x49504:0x494f6;return true;                           // BTST #1,D0; BEQ.W 49504.
    case 0x494f6:r.a[0]=r.a[3];return am_call(c,0x4941e,0x494fc);                           // MOVEA.L A3,A0; JSR 4941e(PC).
    case 0x494fc:return ofr1c_carry(c,0x49504,0x49500);                                       // BCC.W 49504 (C of 4941e).
    case 0x49500:am_byte(r.d[0],r.d[0]^2U);r.pc=0x49504;return true;                         // EORI.B #2,D0.
    case 0x49504:r.pc=0x49462;return true;                                                    // BRA.W 49462 (N08).
    case 0x49508:if(!am_pop(c,4,value))return false;r.a[1]=value;r.pc=0x49462;return true;   // MOVEA.L (A7)+,A1; BRA.W 49462.
    // ---- bc08c (U17 28ae child): MOVE.W #ff60,D0; MOVE.W #0,D1; JSR 49290.l.
    case 0xbc08c:am_word(r.d[0],0xff60);am_word(r.d[1],0);return am_call(c,0x49290,0xbc09a);
    // MOVE.W #8834,68(A6); MOVE.W #8834,1e(A6); MOVE.W #2d,76(A6); MOVE.L #bc0b2,(A6).
    case 0xbc09a:if(!ofr1c_68_1e(c,0x8834))return false;return ofr1c_set_install(c,0x76,0x2d,0xbc0b2);
    case 0xbc0b2:return ofr1c_decrement(c,0xbc0c0,0xbc0ba);                                   // SUBQ.W #1,76(A6); BCC.W bc0c0 (installed value).
    case 0xbc0ba:return ofr1c_callback(c,0xbc0c2,0xbc0c0);                                    // MOVE.L #bc0c2,(A6).
    // BSET.B #0,15(A6); MOVE.W #4f,D0; MOVE.W #7,D1; MOVE.B #0,D2; JSR c6a96.l.
    case 0xbc0c2:if(!ofr1c_bset(c,0x15,0))return false;am_word(r.d[0],0x4f);am_word(r.d[1],7);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xbc0da);
    case 0xbc0da:return ofr1c_anim(c,0x1c,0xbc102);
    // MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVE.L #30000,36(A6); MOVE.L #30000,64(A6); MOVE.L #0,3a(A6); MOVE.W #8,76(A6); MOVE.L #bc132,(A6).
    case 0xbc102:if(!ofr1c_68_1e(c,0x8820) || !ofr1c_speed(c,0x30000))return false;return ofr1c_set_install(c,0x76,8,0xbc132);
    case 0xbc132:return ofr1c_bit(c,0x15,7,0xbc146,0xbc13c);                                  // BTST.B #7,15(A6); BEQ.W bc146 (installed value).
    case 0xbc13c:return am_call(c,0x4be2c,0xbc142);                                           // JSR 4be2c.l.
    case 0xbc142:r.pc=0xbc14c;return true;                                                    // BRA.W bc14c.
    case 0xbc146:return am_call(c,0x4bfa4,0xbc14c);                                           // JSR 4bfa4.l.
    // MOVE.W 76(A6),D0; BEQ.W bc1a0.
    case 0xbc14c:if(!ofr1c_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.pc=ofr1c_w(value)==0U?0xbc1a0:0xbc154;return true;
    case 0xbc154:r.pc=ofr1c_w(r.d[0])!=4U?0xbc17a:0xbc15c;return true;                       // CMPI.W #4,D0; BNE.W bc17a.
    case 0xbc15c:return ofr1c_28ae(c,0xbc844,0x14,0xbc16c);                                   // MOVEA.L #bc844,A0; MOVE.W #14,D0; JSR 28ae.l.
    case 0xbc182:return ofr1c_28ae(c,0xbc844,0x14,0xbc192);
    case 0xbc16c:am_word(r.d[0],0xffc0);am_word(r.d[1],0);return am_call(c,0x49214,0xbc17a);// MOVE.W #ffc0,D0; MOVE.W #0,D1; JSR 49214.l.
    case 0xbc192:am_word(r.d[0],0xff90);am_word(r.d[1],0);return am_call(c,0x49214,0xbc1a0);
    // SUBQ.W #1,76(A6); BNE.W bc1a0 (Z of the WORD result).
    case 0xbc17a:
        if(!ofr1c_get(c,r.a[6],0x76,2,value))return false;value=ofr1c_w(value-1U);
        if(!ofr1c_put(c,r.a[6],0x76,2,value))return false;r.pc=value!=0U?0xbc1a0:0xbc182;return true;
    // CMPI.W #78,42(A6); BLE.W bc1b0 (signed WORD <= 78).
    case 0xbc1a0:if(!ofr1c_get(c,r.a[6],0x42,2,value))return false;r.pc=ofr1c_signed_word(value)<=0x78?0xbc1b0:0xbc1aa;return true;
    case 0xbc1aa:return ofr1c_callback(c,0xbc1b8,0xbc1b0);                                    // MOVE.L #bc1b8,(A6).
    case 0xbc1b0:case 0xbc1f0:case 0xbc278:case 0xbc332:case 0xbc38e:case 0xbc4b6:case 0xbc50a:case 0xbc57c:case 0xbc5e0:case 0xbc62a:case 0xbc69c:
    case 0xbc6d8:case 0xbc700:case 0xbc748:case 0xbc784:case 0xbc7ce:case 0xd14fe:
        return am_call(c,0x49fc6,r.pc+6U);                                                    // JSR 49fc6.l.
    case 0xbc1ea:case 0xbc32c:case 0xbc388:case 0xbc4b0:case 0xbc504:case 0xbc696:case 0xbc6d2:case 0xbc6fa:case 0xbc742:case 0xbc77e:case 0xbc7c8:
        return am_call(c,0x43e34,r.pc+6U);                                                    // JSR 43e34.l (installed values).
    case 0xbc1b8:return ofr1c_anim(c,0x8c,0xbc1e0);                                           // (installed value)
    case 0xbc1e0:if(!ofr1c_put(c,r.a[6],0x62,1,0xff))return false;return ofr1c_install(c,0xbc1ea);   // ST.B 62(A6); MOVE.L #bc1ea,(A6).
    // BCC.W (C of 49fc6): clear -> the RTS block, set -> MOVE.L #next,(A6) and the same RTS.
    case 0xbc1f6:return ofr1c_carry(c,0xbc200,0xbc1fa);
    case 0xbc338:return ofr1c_carry(c,0xbc342,0xbc33c);
    case 0xbc6a2:return ofr1c_carry(c,0xbc6ac,0xbc6a6);
    case 0xbc6de:return ofr1c_carry(c,0xbc6e8,0xbc6e2);
    case 0xbc74e:return ofr1c_carry(c,0xbc758,0xbc752);
    case 0xbc394:return ofr1c_carry(c,0xbc402,0xbc398);
    case 0xbc78a:return ofr1c_carry(c,0xbc7c0,0xbc78e);
    case 0xbc1fa:return ofr1c_callback(c,0xbc202,0xbc200);
    case 0xbc33c:return ofr1c_callback(c,0xbc344,0xbc342);
    case 0xbc6a6:return ofr1c_callback(c,0xbc6ae,0xbc6ac);
    case 0xbc6e2:return ofr1c_callback(c,0xbc6ea,0xbc6e8);
    case 0xbc752:return ofr1c_callback(c,0xbc75a,0xbc758);
    case 0xbc202:return ofr1c_anim(c,0xc,0xbc22a);
    // MOVE.L #8a000,3a(A6); MOVE.L #fffd8000,D0; MOVE.L D0,64(A6); MOVE.L D0,36(A6); MOVE.L #bc246,(A6).
    case 0xbc22a:
        if(!ofr1c_put(c,r.a[6],0x3a,4,0x8a000))return false;r.d[0]=0xfffd8000U;
        if(!ofr1c_put(c,r.a[6],0x64,4,r.d[0]) || !ofr1c_put(c,r.a[6],0x36,4,r.d[0]))return false;return ofr1c_install(c,0xbc246);
    case 0xbc246:return ofr1c_ease(c,0xbc26a);                                                // (installed values)
    case 0xbc2be:return ofr1c_ease(c,0xbc2e2);
    // TST.L 3a(A6); BPL.W bc278 (N of the LONG).
    case 0xbc26a:if(!ofr1c_get(c,r.a[6],0x3a,4,value))return false;r.pc=(value&0x80000000U)==0U?0xbc278:0xbc272;return true;
    case 0xbc272:return ofr1c_callback(c,0xbc290,0xbc278);                                    // MOVE.L #bc290,(A6).
    case 0xbc27e:return ofr1c_bit(c,0x15,7,0xbc28e,0xbc288);                                  // BTST.B #7,15(A6); BEQ.W bc28e.
    case 0xbc2ec:return ofr1c_bit(c,0x15,7,0xbc2fc,0xbc2f6);
    case 0xbc288:return ofr1c_callback(c,0xbc2fe,0xbc28e);                                    // MOVE.L #bc2fe,(A6).
    case 0xbc2f6:return ofr1c_callback(c,0xbc2fe,0xbc2fc);
    case 0xbc290:return ofr1c_anim(c,0x10,0xbc2b8);
    case 0xbc2b8:return ofr1c_install(c,0xbc2be);                                             // MOVE.L #bc2be,(A6).
    case 0xbc2e2:if(!ofr1c_get(c,r.a[6],0x3a,4,value))return false;return am_call(c,0x49fc6,0xbc2ec);   // TST.L 3a(A6) (flags unread); JSR 49fc6.l.
    case 0xbc2fe:return ofr1c_anim(c,0x14,0xbc326);
    case 0xbc326:return ofr1c_install(c,0xbc32c);
    case 0xbc344:return ofr1c_anim(c,0x50,0xbc36c);
    case 0xbc36c:return ofr1c_28ae(c,0xbc404,0xa,0xbc37c);                                    // MOVEA.L #bc404,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0xbc37c:return ofr1c_set_install(c,0x76,3,0xbc388);                                  // MOVE.W #3,76(A6); MOVE.L #bc388,(A6).
    case 0xbc398:return ofr1c_decrement(c,0xbc3aa,0xbc3a0);                                   // SUBQ.W #1,76(A6); BCC.W bc3aa.
    case 0xbc3a0:return ofr1c_callback(c,0xbc47c,0xbc402);                                    // MOVE.L #bc47c,(A6); BRA.W bc402.
    // BNE.W bc3da: the Z of the only predecessor bc398 (SUBQ.W #1,76(A6)) recomputed from the WORD it left in 76(A6).
    case 0xbc3aa:if(!ofr1c_get(c,r.a[6],0x76,2,value))return false;r.pc=ofr1c_w(value)!=0U?0xbc3da:0xbc3ae;return true;
    case 0xbc3ae:return ofr1c_anim(c,0x58,0xbc3d6);
    case 0xbc3d6:r.pc=0xbc402;return true;                                                    // BRA.W bc402.
    case 0xbc3da:return ofr1c_anim(c,0x54,0xbc402);
    case 0xbc47c:return ofr1c_anim(c,0x4,0xbc4a4);                                            // (installed value)
    case 0xbc4a4:return ofr1c_set_install(c,0x76,0xf,0xbc4b0);                                // MOVE.W #f,76(A6); MOVE.L #bc4b0,(A6).
    case 0xbc4bc:return ofr1c_decrement(c,0xbc4ca,0xbc4c4);                                   // SUBQ.W #1,76(A6); BCC.W (RTS block).
    case 0xbc510:return ofr1c_decrement(c,0xbc51e,0xbc518);
    case 0xbc630:return ofr1c_decrement(c,0xbc63e,0xbc638);
    case 0xbc706:return ofr1c_decrement(c,0xbc714,0xbc70e);
    case 0xbc4c4:return ofr1c_callback(c,0xbc4cc,0xbc4ca);                                    // MOVE.L #next,(A6).
    case 0xbc518:return ofr1c_callback(c,0xbc520,0xbc51e);
    case 0xbc638:return ofr1c_callback(c,0xbc640,0xbc63e);
    case 0xbc70e:return ofr1c_callback(c,0xbc716,0xbc714);
    case 0xbc4cc:return ofr1c_anim(c,0x90,0xbc4f4);
    // MOVE.W #24,76(A6); CLR.B 62(A6); MOVE.L #bc504,(A6).
    case 0xbc4f4:if(!ofr1c_put(c,r.a[6],0x76,2,0x24) || !ofr1c_put(c,r.a[6],0x62,1,0))return false;return ofr1c_install(c,0xbc504);
    case 0xbc520:return ofr1c_anim(c,0x1c,0xbc548);
    case 0xbc548:if(!ofr1c_speed(c,0x30000))return false;return ofr1c_install(c,0xbc566);    // speed 30000; MOVE.L #bc566,(A6).
    case 0xbc566:return am_call(c,0x4bfa4,0xbc56c);                                           // JSR 4bfa4.l (installed values).
    case 0xbc5ca:return am_call(c,0x4bfa4,0xbc5d0);
    // CMPI.W #80 / #9d,42(A6); BLT.W (signed WORD).
    case 0xbc56c:if(!ofr1c_get(c,r.a[6],0x42,2,value))return false;r.pc=ofr1c_signed_word(value)<0x80?0xbc57c:0xbc576;return true;
    case 0xbc5d0:if(!ofr1c_get(c,r.a[6],0x42,2,value))return false;r.pc=ofr1c_signed_word(value)<0x9d?0xbc5e0:0xbc5da;return true;
    case 0xbc576:return ofr1c_callback(c,0xbc584,0xbc57c);
    case 0xbc5da:return ofr1c_callback(c,0xbc5e8,0xbc5e0);
    case 0xbc584:return ofr1c_bank_anim(c,0xe3,0x200140,0x1c,0x80,0xbc5ac);                  // MOVE.W #80,D0 (not 100).
    case 0xbc5ac:if(!ofr1c_speed(c,0x18000))return false;return ofr1c_install(c,0xbc5ca);
    case 0xbc5e8:if(!ofr1c_put(c,r.a[6],0x2e,4,0xa00000))return false;return ofr1c_anim(c,0x4,0xbc618);   // MOVE.L #a00000,2e(A6); ...
    case 0xbc618:return ofr1c_set_install(c,0x76,0x1e,0xbc624);
    case 0xbc624:return am_call(c,0x4be06,0xbc62a);                                           // JSR 4be06.l (installed value).
    case 0xbc640:if(!ofr1c_put(c,r.a[6],0x62,1,0xff))return false;return am_call(c,0x8ff4,0xbc64a);      // ST.B 62(A6); JSR 8ff4.l.
    case 0xbc64a:return ofr1c_8ebe(c,0xc87,0xbc658);
    case 0xbc658:return ofr1c_8ebe(c,0xc8c,0xbc666);
    case 0xbc666:return ofr1c_8ebe(c,0xc8d,0xbc674);
    // MOVE.B 19(A6),14(A6); MOVE.W #e3,20(A6); MOVEA.L #bcbd4,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xbc674:if(!ofr1c_get(c,r.a[6],0x19,1,value) || !ofr1c_put(c,r.a[6],0x14,1,value))return false;return ofr1c_fixed_anim(c,0xbcbd4,0xbc690);
    case 0xbc690:return ofr1c_install(c,0xbc696);
    // MOVEA.L c(A6),A0; ST.B 62(A0); MOVE.W #e3,20(A6); MOVEA.L #bcc44,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xbc6ae:
        if(!ofr1c_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr1c_put(c,r.a[0],0x62,1,0xff))return false;
        return ofr1c_fixed_anim(c,0xbcc44,0xbc6cc);
    case 0xbc6cc:return ofr1c_install(c,0xbc6d2);
    // CLR.B 62(A6); MOVE.W #1e,76(A6); MOVE.L #bc6fa,(A6).
    case 0xbc6ea:if(!ofr1c_put(c,r.a[6],0x62,1,0))return false;return ofr1c_set_install(c,0x76,0x1e,0xbc6fa);
    case 0xbc716:return ofr1c_28ae(c,0xbc7d6,0xa,0xbc726);
    case 0xbc726:return ofr1c_fixed_anim(c,0xbce74,0xbc73c);                                 // MOVE.W #e3,20(A6); MOVEA.L #bce74,A1; ... (A0 of 28ae).
    case 0xbc73c:return ofr1c_install(c,0xbc742);
    // ST.B 62(A6); ST.B 63(A6); MOVE.W #e3,20(A6); MOVEA.L #bcee2,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0xbc75a:if(!ofr1c_put(c,r.a[6],0x62,1,0xff) || !ofr1c_put(c,r.a[6],0x63,1,0xff))return false;return ofr1c_fixed_anim(c,0xbcee2,0xbc778);
    case 0xbc778:return ofr1c_install(c,0xbc77e);
    case 0xbc78e:return ofr1c_28ae(c,0xd6c78,0xa,0xbc79e);                                    // MOVEA.L #d6c78,A0; MOVE.W #a,D0; JSR 28ae.l.
    case 0xbc79e:return ofr1c_carry(c,0xbc7b4,0xbc7a2);                                       // BCC.W bc7b4 (C of 28ae).
    case 0xbc7a2:am_word(r.d[0],0xfff4);am_word(r.d[1],0xc);return am_call(c,0x4970a,0xbc7b0);   // MOVE.W #fff4,D0; MOVE.W #c,D1; JSR 4970a.l.
    case 0xbc7b0:r.carry=AnimationCarrySet;r.pc=0xbc7b4;return true;                         // ORI.B #1,CCR (no reader).
    case 0xbc7b4:if(!ofr1c_put(c,r.a[0],0x76,2,2))return false;return ofr1c_callback(c,0xbc7c2,0xbc7c0);  // MOVE.W #2,76(A0); MOVE.L #bc7c2,(A6).
    case 0xbc7c2:return ofr1c_install(c,0xbc7c8);                                             // MOVE.L #bc7c8,(A6) (installed value).
    // ---- d13b4 (FR1a 2986 child): three sounds 35d / 364 / 365.
    case 0xd13b4:return ofr1c_8ebe(c,0x35d,0xd13c2);
    case 0xd13c2:return ofr1c_8ebe(c,0x364,0xd13d0);
    case 0xd13d0:return ofr1c_8ebe(c,0x365,0xd13de);
    // BSET.B #4,15(A6); MOVE.W #e0ef,68(A6); MOVE.W #e0ef,1e(A6); bank animation da / 200090 / 14.
    case 0xd13de:if(!ofr1c_bset(c,0x15,4) || !ofr1c_68_1e(c,0xe0ef))return false;return ofr1c_bank_anim(c,0xda,0x200090,0x14,0x100,0xd1418);
    // MOVE.W 76(A6),D0; BEQ.W d1432 / CMPI.W #1,D0; BEQ.W d1432 / BCHG.B #0,15(A6); BRA.W d1432.
    case 0xd1418:if(!ofr1c_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[0],value);r.pc=ofr1c_w(value)==0U?0xd1432:0xd1420;return true;
    case 0xd1420:r.pc=ofr1c_w(r.d[0])==1U?0xd1432:0xd1428;return true;
    case 0xd1428:if(!ofr1c_bchg(c,0x15,0))return false;r.pc=0xd1432;return true;
    case 0xd1432:r.a[0]=0xd13ac;return am_call(c,0x494c0,0xd143c);                          // LEA d13ac(PC),A0; JSR 494c0.l.
    case 0xd143c:return ofr1c_carry(c,0xd144c,0xd1440);                                       // BCC.W d144c (C of 494c0).
    case 0xd1440:am_word(r.d[1],0x40);am_word(r.d[0],0x20);r.pc=0xd14b8;return true;        // MOVE.W #40,D1; MOVE.W #20,D0; BRA.W d14b8.
    // MOVE.W 46(A0),D0; SUB.W 46(A6),D0; CMPI.W #1a0,46(A6); BLE.W d1466 (signed WORD).
    case 0xd144c:
        if(!ofr1c_get(c,r.a[0],0x46,2,value))return false;am_word(r.d[0],value);
        if(!ofr1c_get(c,r.a[6],0x46,2,other))return false;am_word(r.d[0],value-other);
        if(!ofr1c_get(c,r.a[6],0x46,2,other))return false;r.pc=ofr1c_signed_word(other)<=0x1a0?0xd1466:0xd145e;return true;
    case 0xd145e:am_word(r.d[1],0x40);r.pc=0xd1486;return true;                              // MOVE.W #40,D1; BRA.W d1486.
    case 0xd1466:am_word(r.d[1],0x50);r.pc=ofr1c_signed_word(r.d[0])<=0x60?0xd147a:0xd1472;return true;   // MOVE.W #50,D1; CMPI.W #60,D0; BLE.W.
    case 0xd1472:am_word(r.d[1],0x70);r.pc=0xd1486;return true;                              // MOVE.W #70,D1; BRA.W d1486.
    case 0xd147a:r.pc=ofr1c_signed_word(r.d[0])>=-0x40?0xd1486:0xd1482;return true;          // CMPI.W #ffc0,D0; BGE.W d1486.
    case 0xd1482:am_word(r.d[1],0x50);r.pc=0xd1486;return true;                              // MOVE.W #50,D1.
    // NEG.W D0; ASR.W #1,D0; MOVE.W 42(A0),D7; SUB.W 42(A6),D7; BPL.W d1498 (N of the WORD).
    case 0xd1486:
        am_word(r.d[0],0U-r.d[0]);am_word(r.d[0],ofr1c_asr_word1(r.d[0]));
        if(!ofr1c_get(c,r.a[0],0x42,2,value))return false;am_word(r.d[7],value);
        if(!ofr1c_get(c,r.a[6],0x42,2,other))return false;am_word(r.d[7],value-other);r.pc=(r.d[7]&0x8000U)==0U?0xd1498:0xd1496;return true;
    case 0xd1496:am_word(r.d[7],0U-r.d[7]);r.pc=0xd1498;return true;                         // NEG.W D7.
    // ADD.W D7,D0; MOVE.W D1,D7; ASR.L #1,D7; ADD.W D1,D7; CMP.W D7,D0; BCS.W d14a8 (unsigned D0.W < D7.W).
    case 0xd1498:
        am_word(r.d[0],r.d[0]+r.d[7]);am_word(r.d[7],r.d[1]);r.d[7]=ofr1c_asr_long(r.d[7],1);am_word(r.d[7],r.d[7]+r.d[1]);
        r.pc=ofr1c_w(r.d[0])<ofr1c_w(r.d[7])?0xd14a8:0xd14a6;return true;
    case 0xd14a6:am_word(r.d[0],r.d[7]);r.pc=0xd14a8;return true;                            // MOVE.W D7,D0.
    // ADDI.W #20,D0; ANDI.W #ffc0,D0; SUBI.W #20,D0; ADDI.W #40,D0.
    case 0xd14a8:
        am_word(r.d[0],r.d[0]+0x20U);am_word(r.d[0],r.d[0]&0xffc0U);am_word(r.d[0],r.d[0]-0x20U);am_word(r.d[0],r.d[0]+0x40U);r.pc=0xd14b8;return true;
    // MOVE.W D1,D7; MULU.W #1b33,D7; MOVE.L D7,3a(A6); SWAP D0; CLR.W D0; ASR.L #5,D0; BTST.B #0,15(A6); BNE.W d14d4.
    case 0xd14b8:
        am_word(r.d[7],r.d[1]);r.d[7]=ofr1c_w(r.d[7])*0x1b33U;if(!ofr1c_put(c,r.a[6],0x3a,4,r.d[7]))return false;
        am_swap(r.d[0]);am_word(r.d[0],0);r.d[0]=ofr1c_asr_long(r.d[0],5);return ofr1c_bit(c,0x15,0,0xd14d2,0xd14d4);
    case 0xd14d2:r.d[0]=0U-r.d[0];r.pc=0xd14d4;return true;                                   // NEG.L D0.
    case 0xd14d4:if(!ofr1c_put(c,r.a[6],0x36,4,r.d[0]))return false;return ofr1c_install(c,0xd14de);  // MOVE.L D0,36(A6); MOVE.L #d14de,(A6).
    // MOVE.L #fff40000,D0; SUB.L 3a(A6),D0; ASR.L #5,D0; ADD.L D0,3a(A6); MOVE.L 36(A6),D0; ASR.L #5,D0; SUB.L D0,36(A6); JSR 4be34.l.
    case 0xd14de:
        if(!ofr1c_get(c,r.a[6],0x3a,4,value))return false;r.d[0]=ofr1c_asr_long(0xfff40000U-value,5);
        if(!ofr1c_get(c,r.a[6],0x3a,4,value) || !ofr1c_put(c,r.a[6],0x3a,4,value+r.d[0]))return false;
        if(!ofr1c_get(c,r.a[6],0x36,4,value))return false;r.d[0]=ofr1c_asr_long(value,5);
        if(!ofr1c_get(c,r.a[6],0x36,4,value) || !ofr1c_put(c,r.a[6],0x36,4,value-r.d[0]))return false;
        return am_call(c,0x4be34,0xd14fe);
    case 0xd1504:return ofr1c_bit(c,0x15,5,0xd1514,0xd150e);                                  // BTST.B #5,15(A6); BEQ.W d1514.
    case 0xd150e:return ofr1c_callback(c,0xd1576,0xd1514);                                    // MOVE.L #d1576,(A6).
    case 0xd1514:r.a[0]=0xd1c9c;r.d[0]=r.a[0];r.pc=r.d[0]==0U?0xd1528:0xd1520;return true;  // LEA d1c9c.l,A0; MOVE.L A0,D0; BEQ.W d1528.
    case 0xd1520:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0xd1528);                            // MOVEA.L D0,A0; JSR 4ae4a.l.
    case 0xd1528:r.pc=ofr1c_w(r.d[0])==0U?0xd1534:0xd152e;return true;                       // TST.W D0; BEQ.W d1534.
    case 0xd152e:return ofr1c_callback(c,0xd1586,0xd1534);                                    // MOVE.L #d1586,(A6).
    case 0xd1534:return am_call(c,0x4b6f4,0xd153a);                                           // JSR 4b6f4.l.
    case 0xd153a:return ofr1c_carry(c,0xd1544,0xd153e);                                       // BCC.W d1544 (C of 4b6f4).
    case 0xd153e:return ofr1c_callback(c,0xd1586,0xd1544);
    // MOVE.W 10000e.l,D0; ANDI.W #3,D0; CMPI.W #3,D0; BCS.W d155a.
    case 0xd1544:if(!am_read(c,0x10000e,2,value))return false;am_word(r.d[0],value&3U);r.pc=ofr1c_w(r.d[0])<3U?0xd155a:0xd1556;return true;
    case 0xd1556:am_word(r.d[0],1);r.pc=0xd155a;return true;                                 // MOVE.W #1,D0.
    // MOVE.B 19(A6,D0.W),14(A6); LEA d13a4(PC),A0; JSR 1ab80.l.
    case 0xd155a:
        if(!am_read(c,am_index(r.a[6]+0x19U,r.d[0]),1,value) || !ofr1c_put(c,r.a[6],0x14,1,value))return false;r.a[0]=0xd13a4;
        return am_call(c,0x1ab80,0xd156a);
    case 0xd156a:return ofr1c_carry(c,0xd1574,0xd156e);                                       // BCC.W d1574 (C of 1ab80).
    case 0xd156e:r.pc=0x2a00;return true;                                                     // JMP 2a00.l.
    case 0xd1576:if(!ofr1c_68_1e(c,0x1001))return false;r.pc=0xd1592;return true;            // (installed value) ...; BRA.W d1592.
    case 0xd1586:if(!ofr1c_68_1e(c,0x8820))return false;r.pc=0xd1592;return true;            // (installed value)
    case 0xd1592:return am_call(c,0x8ff4,0xd1598);                                            // JSR 8ff4.l.
    case 0xd1598:r.pc=0xd2206;return true;                                                    // JMP d2206.l.
    // ---- d2206 (c6012 table LONG c6032 / d1598): bank animation d2 / 20008c / 14.
    case 0xd2206:return ofr1c_bank_anim(c,0xd2,0x20008c,0x14,0x100,0xd222e);
    case 0xd222e:am_word(r.d[0],0x22);am_word(r.d[1],5);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xd2240);   // MOVE.W #22,D0; ...; JSR c6a96.l.
    case 0xd2240:r.a[0]=0xd3e5c;if(!ofr1c_put(c,r.a[6],0x92,4,r.a[0]))return false;r.pc=0xd23a0;return true;  // LEA d3e5c(PC),A0; MOVE.L A0,92(A6); BRA.W d23a0.
    default:return am_error(c,"unsupported animation objects fr1c PC");
    }
}
}
