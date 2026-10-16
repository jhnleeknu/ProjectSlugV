#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OB3B_PATH=0x2c7a6;         // 2c974: MOVE.L #2c7a6,98(A6) (the N28 path list, fixed ROM WORDs read through the live bus).
std::uint32_t ob3b_b(std::uint32_t value) {return value&255U;}
std::uint32_t ob3b_w(std::uint32_t value) {return value&65535U;}
bool ob3b_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ob3b_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG); the fall-through enters the installed callback.
bool ob3b_install(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next) {
    if(!ob3b_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next;return true;
}
// BTST.B #bit,d16(A6): true when the bit is 1.
bool ob3b_bit(AnimationMachineContext& c,std::uint32_t displacement,unsigned int bit,bool& set) {
    std::uint32_t value=0;if(!ob3b_get(c,c.s.a[6],displacement,1,value))return false;set=((value>>bit)&1U)!=0U;return true;
}
// BSET.B / BCLR.B #bit,61(A6); then PC := next.
bool ob3b_flag61(AnimationMachineContext& c,unsigned int bit,bool on,std::uint32_t next) {
    std::uint32_t value=0;if(!ob3b_get(c,c.s.a[6],0x61,1,value))return false;
    if(!ob3b_put(c,c.s.a[6],0x61,1,on?(value|(1U<<bit)):(value&~(1U<<bit))))return false;c.s.pc=next;return true;
}
// Bcc on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ob3b_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects b3b caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W #n,D0; JSR 3af8.l (sound request).
bool ob3b_sound(AnimationMachineContext& c,std::uint32_t n,std::uint32_t return_pc) {am_word(c.s.d[0],n);return am_call(c,0x3af8,return_pc);}
// MOVEA.L #list,A1 / LEA list.l,A1 (list != 0; 0 keeps A1); MOVE.W #100,D0; JSR 49f8c.l (animation list start).
bool ob3b_anim(AnimationMachineContext& c,std::uint32_t list,std::uint32_t return_pc) {
    if(list!=0U)c.s.a[1]=list;am_word(c.s.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// MOVE.W 88(A6),D0; JSR 49be0.l (input WORD pointer in A0).
bool ob3b_input(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!ob3b_get(c,c.s.a[6],0x88,2,value))return false;am_word(c.s.d[0],value);return am_call(c,0x49be0,return_pc);
}
// MOVE.W (A0),D0 (the input WORD).
bool ob3b_input_word(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_read(c,c.s.a[0],2,value))return false;am_word(c.s.d[0],value);return true;
}
// BTST.B #n,D0; Bcc (Z of one bit of D0): taken_when_set selects BNE (true) or BEQ (false).
void ob3b_d0bit(AnimationMachineState& r,unsigned int bit,bool taken_when_set,std::uint32_t fall,std::uint32_t taken) {
    const bool set=((r.d[0]>>bit)&1U)!=0U;r.pc=set==taken_when_set?taken:fall;
}
// BTST.B #7,15(A6); BEQ.W taken.
bool ob3b_live(AnimationMachineContext& c,std::uint32_t fall,std::uint32_t taken) {
    bool bit=false;if(!ob3b_bit(c,0x15,7,bit))return false;c.s.pc=bit?fall:taken;return true;
}
// BTST.B #0,15(A6); BEQ.W (taken_when_set false) / BNE.W (true).
bool ob3b_face(AnimationMachineContext& c,bool taken_when_set,std::uint32_t fall,std::uint32_t taken) {
    bool bit=false;if(!ob3b_bit(c,0x15,0,bit))return false;c.s.pc=bit==taken_when_set?taken:fall;return true;
}
// LEA first.l,A1; CMPI.B #7,7f(A6); BCS.W below (unsigned BYTE 7f < 7) / fall: LEA second.l,A1.
bool ob3b_pick7(AnimationMachineContext& c,std::uint32_t first,std::uint32_t below,std::uint32_t fall) {
    std::uint32_t value=0;c.s.a[1]=first;if(!ob3b_get(c,c.s.a[6],0x7f,1,value))return false;c.s.pc=value<7U?below:fall;return true;
}
// CMPI.B #limit,7f(A6); BCC.W taken (unsigned BYTE 7f >= limit).
bool ob3b_7f_at_least(AnimationMachineContext& c,std::uint32_t limit,std::uint32_t fall,std::uint32_t taken) {
    std::uint32_t value=0;if(!ob3b_get(c,c.s.a[6],0x7f,1,value))return false;c.s.pc=value>=limit?taken:fall;return true;
}
// MOVE.B #n,9d(A6) (n != 0); MOVEA.L 9e(A6),A4; MOVE.L (A4),D0 / 64(A6) (negated: NEG.L D0; MOVE.L D0,64(A6)); BTST.B #0,15(A6); Bcc.
bool ob3b_walk(AnimationMachineContext& c,std::uint32_t n,bool negate,bool taken_when_set,std::uint32_t fall,std::uint32_t taken) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(n!=0U && !ob3b_put(c,r.a[6],0x9d,1,n))return false;
    if(!ob3b_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;if(!am_read(c,r.a[4],4,value))return false;
    if(negate){r.d[0]=0U-value;value=r.d[0];}
    if(!ob3b_put(c,r.a[6],0x64,4,value))return false;return ob3b_face(c,taken_when_set,fall,taken);
}
// MOVEQ #0,D7; MOVEA.L 9e(A6),A4; MOVE.L (A4),D6; BTST.B #3,D0; BEQ.W taken (input speed head).
bool ob3b_speed_head(AnimationMachineContext& c,std::uint32_t fall,std::uint32_t taken) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.d[7]=0;
    if(!ob3b_get(c,r.a[6],0x9e,4,value))return false;r.a[4]=value;if(!am_read(c,r.a[4],4,value))return false;r.d[6]=value;
    ob3b_d0bit(r,3,false,fall,taken);return true;
}
// MOVE.B 7e(A6),D0; MOVE.B 82(A6),D1; MOVE.B D0,82(A6); EOR.B D0,D1; BPL/BMI (bit 7 of the EOR BYTE).
bool ob3b_turn(AnimationMachineContext& c,bool taken_when_negative,std::uint32_t fall,std::uint32_t taken) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ob3b_get(c,r.a[6],0x7e,1,value))return false;am_byte(r.d[0],value);
    if(!ob3b_get(c,r.a[6],0x82,1,value))return false;am_byte(r.d[1],value);
    if(!ob3b_put(c,r.a[6],0x82,1,r.d[0]))return false;am_byte(r.d[1],ob3b_b(r.d[0])^ob3b_b(r.d[1]));
    r.pc=((r.d[1]&0x80U)!=0U)==taken_when_negative?taken:fall;return true;
}
// MOVE.B 7e(A6),82(A6) (the moved BYTE is returned).
bool ob3b_keep7e(AnimationMachineContext& c,std::uint32_t& value) {
    return ob3b_get(c,c.s.a[6],0x7e,1,value) && ob3b_put(c,c.s.a[6],0x82,1,value);
}
}
// Objects B3b (206 block starts): the middle states of the N28 range-outside installation chain 2ba50 (2baf4..2c0fc, 177: stand 2baf4, walk starts
// 2bb7e / 2bb9a / 2bbb6 / 2bbd6, walk 2bc70, stop 2bdd6 / 2be36, aim 2bef6 / 2bf1e, crouch 2bfcc / 2bff2, second stand 2c088 / 2c09e) and the
// branch exit state 2c96a..2ca68 (30, with the 9-slot table 2ca24..2ca44 behind CMPI.W #9 / BCC). Every exit is routed (B3a, N28, routed
// callees); the only unrouted value is the 28ae child 2db06 (data). Known C: none produced; the 8 consumers 2bb66 2bd06 2bea2 2bf9c (BCS, 2b532),
// 2bee8 2bfa8 2c074 (BCC, 2b418) and 2ca52 (BCC, 1ab02) read a known C or fail. 2bd58 (BMI) has two predecessors (2bd48 MOVE.L + BTST,
// 2bd56 NEG.L), so it is folded into each (N04 ab1a6 / N09 af7b0 / N15 71c86 convention) and is an interior PC. Data reads through the live bus: the record LONG (LONG 9e(A6)), the path list of LONG 98(A6)
// and the input WORD of the 49be0 return. No X / MUL / DIV / TRAP / port / bank write.
bool animation_objects_b3b_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;bool bit=false;
    switch(r.pc) {
    // ---- 2baf4 (installed value): MOVE.L #0,98(A6); CMPI.B #7,7f(A6); BCC.W 2c088.
    case 0x2baf4:if(!ob3b_put(c,r.a[6],0x98,4,0))return false;return ob3b_7f_at_least(c,7,0x2bb06,0x2c088);
    case 0x2bb06:return ob3b_anim(c,0x65f56,0x2bb16);                        // MOVEA.L #65f56,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2bb16:return ob3b_install(c,0x2bb1c,0x2bb1c);                     // MOVE.L #2bb1c,(A6).
    case 0x2bb1c:case 0x2be36:case 0x2bf1e:case 0x2c012:case 0x2c09e:return ob3b_live(c,r.pc+0xaU,0x2c212);   // BTST.B #7,15(A6); BEQ.W 2c212.
    case 0x2bb26:case 0x2bc70:case 0x2be40:case 0x2bf28:case 0x2c01c:case 0x2c0a8:return ob3b_input(c,r.pc+0xaU);   // MOVE.W 88(A6),D0; JSR 49be0.l.
    case 0x2bb30:if(!ob3b_input_word(c))return false;ob3b_d0bit(r,3,true,0x2bb3a,0x2bb7e);return true;   // MOVE.W (A0),D0; BTST.B #3,D0; BNE.W 2bb7e.
    case 0x2bb3a:ob3b_d0bit(r,2,true,0x2bb42,0x2bbb6);return true;           // BTST.B #2,D0; BNE.W 2bbb6.
    case 0x2bb42:ob3b_d0bit(r,7,true,0x2bb4a,0x2c96a);return true;           // BTST.B #7,D0; BNE.W 2c96a.
    case 0x2bb4a:ob3b_d0bit(r,5,true,0x2bb52,0x2c1ae);return true;           // BTST.B #5,D0; BNE.W 2c1ae (B3a).
    case 0x2bb52:ob3b_d0bit(r,1,true,0x2bb5a,0x2bfcc);return true;           // BTST.B #1,D0; BNE.W 2bfcc.
    case 0x2bb5a:ob3b_d0bit(r,6,false,0x2bb62,0x2bb6a);return true;          // BTST.B #6,D0; BEQ.W 2bb6a.
    case 0x2bb62:case 0x2bd02:case 0x2be9e:case 0x2bf98:return am_call(c,0x2b532,r.pc+4U);   // BSR.W 2b532 (B3a; its C is read next).
    case 0x2bb66:return ob3b_carry(c,0x2bb6a,0x2bef6);                       // BCS.W 2bef6 (C returned by 2b532).
    case 0x2bd06:return ob3b_carry(c,0x2bd0a,0x2bef6);
    case 0x2bea2:return ob3b_carry(c,0x2bea6,0x2bef6);
    case 0x2bf9c:return ob3b_carry(c,0x2bfa0,0x2bef6);
    // MOVE.L #0,64(A6); BSR.W 2c71a.
    case 0x2bb6a:case 0x2c0e8:if(!ob3b_put(c,r.a[6],0x64,4,0))return false;return am_call(c,0x2c71a,r.pc+0xcU);
    case 0x2bb76:case 0x2bd96:case 0x2bee4:case 0x2bfa4:case 0x2c070:case 0x2c0f4:case 0x2c9f6:return am_call(c,0x2b418,r.pc+4U);   // BSR.W 2b418 (N28).
    case 0x2bb7a:case 0x2bdd2:case 0x2bef2:case 0x2bfc8:case 0x2c084:case 0x2c0f8:r.pc=0x2c562;return true;   // BRA.W 2c562 (B3a shared tail).
    // ---- walk starts: MOVE.B #5/#3,9d(A6); LONG 64 := +/- LONG (LONG 9e(A6)); BTST.B #0,15(A6); BEQ / BNE.
    case 0x2bb7e:return ob3b_walk(c,5,false,false,0x2bb96,0x2bbf6);
    case 0x2bb9a:if(!ob3b_put(c,r.a[6],0x9d,1,3))return false;r.pc=0x2bba0;return true;   // MOVE.B #3,9d(A6).
    case 0x2bba0:return ob3b_walk(c,0,false,false,0x2bbb2,0x2bc2a);
    case 0x2bbb6:return ob3b_walk(c,5,true,true,0x2bbd2,0x2bbf6);
    case 0x2bbd6:if(!ob3b_put(c,r.a[6],0x9d,1,3))return false;r.pc=0x2bbdc;return true;   // MOVE.B #3,9d(A6).
    case 0x2bbdc:return ob3b_walk(c,0,true,true,0x2bbf2,0x2bc2a);
    case 0x2bb96:case 0x2bbd2:r.pc=0x2bc10;return true;                      // BRA.W 2bc10.
    case 0x2bbb2:case 0x2bbf2:r.pc=0x2bc44;return true;                      // BRA.W 2bc44.
    // ---- animation pick by BYTE 7f < 7.
    case 0x2bbf6:return ob3b_pick7(c,0x6795e,0x2bc5a,0x2bc06);
    case 0x2bc10:return ob3b_pick7(c,0x68230,0x2bc5a,0x2bc20);
    case 0x2bc2a:return ob3b_pick7(c,0x67e12,0x2bc5a,0x2bc3a);
    case 0x2bc44:return ob3b_pick7(c,0x686e4,0x2bc5a,0x2bc54);
    case 0x2bd5c:return ob3b_pick7(c,0x67e12,0x2bd72,0x2bd6c);
    case 0x2bd76:return ob3b_pick7(c,0x686e4,0x2bd8c,0x2bd86);
    case 0x2bc06:r.a[1]=0x68c30;r.pc=0x2bc5a;return true;                    // LEA 68c30.l,A1; BRA.W 2bc5a.
    case 0x2bc20:r.a[1]=0x69502;r.pc=0x2bc5a;return true;                    // LEA 69502.l,A1; BRA.W 2bc5a.
    case 0x2bc3a:r.a[1]=0x690e4;r.pc=0x2bc5a;return true;                    // LEA 690e4.l,A1; BRA.W 2bc5a.
    case 0x2bc54:r.a[1]=0x699b6;r.pc=0x2bc5a;return true;                    // LEA 699b6.l,A1.
    case 0x2bd6c:r.a[1]=0x690e4;r.pc=0x2bd72;return true;                    // LEA 690e4.l,A1.
    case 0x2bd72:r.pc=0x2bd8c;return true;                                    // BRA.W 2bd8c.
    case 0x2bd86:r.a[1]=0x699b6;r.pc=0x2bd8c;return true;                    // LEA 699b6.l,A1.
    case 0x2bc5a:case 0x2bd8c:case 0x2be1e:return ob3b_anim(c,0,r.pc+0xaU);  // MOVE.W #100,D0; JSR 49f8c.l (A1 as picked).
    // MOVE.B 7e(A6),82(A6); MOVE.L #2bc70,(A6).
    case 0x2bc64:if(!ob3b_keep7e(c,value))return false;return ob3b_install(c,0x2bc70,0x2bc70);
    // ---- 2bc70 walk: MOVE.W (A0),D0; BTST.B #0,D0; BEQ.W 2bc8e.
    case 0x2bc7a:if(!ob3b_input_word(c))return false;ob3b_d0bit(r,0,false,0x2bc84,0x2bc8e);return true;
    case 0x2bc84:return ob3b_flag61(c,5,true,0x2bc94);                       // BSET.B #5,61(A6); BRA.W 2bc94.
    case 0x2bc8e:return ob3b_flag61(c,5,false,0x2bc94);                      // BCLR.B #5,61(A6).
    case 0x2bc94:ob3b_d0bit(r,1,false,0x2bc9c,0x2bca6);return true;          // BTST.B #1,D0; BEQ.W 2bca6.
    case 0x2bc9c:return ob3b_flag61(c,4,true,0x2bcac);                       // BSET.B #4,61(A6); BRA.W 2bcac.
    case 0x2bca6:return ob3b_flag61(c,4,false,0x2bcac);                      // BCLR.B #4,61(A6).
    case 0x2bcac:ob3b_d0bit(r,3,false,0x2bcb4,0x2bcc0);return true;          // BTST.B #3,D0; BEQ.W 2bcc0.
    // TST.L 64(A6); BLE.W 2bb9a (signed LONG <= 0; TST clears V).
    case 0x2bcb4:if(!ob3b_get(c,r.a[6],0x64,4,value))return false;r.pc=(value==0U || (value&0x80000000U)!=0U)?0x2bb9a:0x2bcbc;return true;
    case 0x2bcbc:case 0x2bcd0:r.pc=0x2bcd8;return true;                      // BRA.W 2bcd8.
    case 0x2bcc0:ob3b_d0bit(r,2,false,0x2bcc8,0x2bcd4);return true;          // BTST.B #2,D0; BEQ.W 2bcd4.
    // TST.L 64(A6); BGE.W 2bbd6 (signed LONG >= 0).
    case 0x2bcc8:if(!ob3b_get(c,r.a[6],0x64,4,value))return false;r.pc=(value&0x80000000U)==0U?0x2bbd6:0x2bcd0;return true;
    case 0x2bcd4:r.pc=0x2bdd6;return true;                                    // BRA.W 2bdd6.
    case 0x2bcd8:return ob3b_7f_at_least(c,5,0x2bce2,0x2bd0e);               // CMPI.B #5,7f(A6); BCC.W 2bd0e.
    case 0x2bce2:ob3b_d0bit(r,7,true,0x2bcea,0x2c96a);return true;           // BTST.B #7,D0; BNE.W 2c96a.
    case 0x2bcea:ob3b_d0bit(r,1,true,0x2bcf2,0x2bfcc);return true;           // BTST.B #1,D0; BNE.W 2bfcc.
    case 0x2bcf2:ob3b_d0bit(r,5,true,0x2bcfa,0x2c1ae);return true;           // BTST.B #5,D0; BNE.W 2c1ae.
    case 0x2bcfa:ob3b_d0bit(r,6,false,0x2bd02,0x2bd0a);return true;          // BTST.B #6,D0; BEQ.W 2bd0a.
    case 0x2bd0a:r.pc=0x2bd32;return true;                                    // BRA.W 2bd32.
    case 0x2bd0e:ob3b_d0bit(r,1,false,0x2bd16,0x2c0fc);return true;          // BTST.B #1,D0; BEQ.W 2c0fc (B3a).
    case 0x2bd16:ob3b_d0bit(r,7,true,0x2bd1e,0x2c96a);return true;           // BTST.B #7,D0; BNE.W 2c96a.
    case 0x2bd1e:ob3b_d0bit(r,5,true,0x2bd26,0x2c6cc);return true;           // BTST.B #5,D0; BNE.W 2c6cc (B3a).
    case 0x2bd26:ob3b_d0bit(r,6,false,0x2bd2e,0x2bd32);return true;          // BTST.B #6,D0; BEQ.W 2bd32.
    case 0x2bd2e:case 0x2beca:case 0x2c068:case 0x2c0e4:return am_call(c,0x2b608,r.pc+4U);   // BSR.W 2b608 (B3a).
    case 0x2bd32:case 0x2bee0:case 0x2bfa0:case 0x2c06c:return am_call(c,0x2c71a,r.pc+4U);   // BSR.W 2c71a (B3a).
    case 0x2bd36:return ob3b_turn(c,false,0x2bd48,0x2bd96);                  // BYTE 82 := BYTE 7e; EOR bit 7 clear: BPL.W 2bd96.
    // MOVE.L 64(A6),D0; BTST.B #0,15(A6); BEQ.W 2bd58 (folded: the BMI.W 2bd76 at 2bd58 has two predecessors, so each one evaluates it with its own N
    // = D0 bit 31 of the MOVE.L; 2bd58 is an interior PC, not a block start).
    case 0x2bd48:
        if(!ob3b_get(c,r.a[6],0x64,4,value))return false;r.d[0]=value;
        if(!ob3b_face(c,false,0x2bd56,0x2bd58))return false;
        if(r.pc==0x2bd58U)r.pc=(r.d[0]&0x80000000U)!=0U?0x2bd76:0x2bd5c;return true;
    // NEG.L D0; BMI.W 2bd76 (folded 2bd58, N of the NEG result) else 2bd5c.
    case 0x2bd56:r.d[0]=0U-r.d[0];r.pc=(r.d[0]&0x80000000U)!=0U?0x2bd76:0x2bd5c;return true;
    case 0x2c9e6:r.d[0]=0U-r.d[0];r.pc=r.pc+2U;return true;                 // NEG.L D0.
    // BTST.B #7,15(A6); BNE.W 2bdaa.
    case 0x2bd9a:if(!ob3b_bit(c,0x15,7,bit))return false;r.pc=bit?0x2bdaa:0x2bda4;return true;
    case 0x2bda4:return ob3b_install(c,0x2c212,0x2bdaa);                     // MOVE.L #2c212,(A6) (B3a value).
    // MOVEQ #0,D0; MOVE.B 9d(A6),D0; BEQ.W 2bdd2.
    case 0x2bdaa:if(!ob3b_get(c,r.a[6],0x9d,1,value))return false;r.d[0]=value;r.pc=value==0U?0x2bdd2:0x2bdb4;return true;
    // LSL.B #4,D0; SUB.B D0,9c(A6); BCC.W 2bdd2 (C = borrow of the BYTE subtraction).
    case 0x2bdb4:
        am_byte(r.d[0],(r.d[0]<<4)&0xffU);if(!ob3b_get(c,r.a[6],0x9c,1,value))return false;
        if(!ob3b_put(c,r.a[6],0x9c,1,value-ob3b_b(r.d[0])))return false;r.pc=value<ob3b_b(r.d[0])?0x2bdbe:0x2bdd2;return true;
    // SUBQ.B #1,9d(A6); MOVEA.L #2db06,A0; MOVE.W #1e,D0; JSR 28ae.l (the child value 2db06 is data for 28ae).
    case 0x2bdbe:
        if(!ob3b_get(c,r.a[6],0x9d,1,value) || !ob3b_put(c,r.a[6],0x9d,1,value-1U))return false;
        r.a[0]=0x2db06;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0x2bdd2);
    // ---- 2bdd6 stop: MOVE.B 7e(A6),82(A6); BEQ.W 2baf4 (Z of the moved BYTE).
    case 0x2bdd6:if(!ob3b_keep7e(c,value))return false;r.pc=value==0U?0x2baf4:0x2bde0;return true;
    // TST.L 64(A6); SMI.B 85(A6); LEA 69f02.l,A1; LEA 6a210.l,A2; CMPI.B #7,7f(A6); BCS.W 2be0a.
    case 0x2bde0:
        if(!ob3b_get(c,r.a[6],0x64,4,value) || !ob3b_put(c,r.a[6],0x85,1,(value&0x80000000U)!=0U?0xffU:0U))return false;
        r.a[2]=0x6a210;return ob3b_pick7(c,0x69f02,0x2be0a,0x2bdfe);
    case 0x2bdfe:r.a[1]=0x6a51e;r.a[2]=0x6a82c;r.pc=0x2be0a;return true;   // LEA 6a51e.l,A1; LEA 6a82c.l,A2.
    // BTST.B #0,15(A6); SNE.B D0; MOVE.B 85(A6),D1; EOR.B D0,D1; BEQ.W 2be1e.
    case 0x2be0a:
        if(!ob3b_bit(c,0x15,0,bit) || !ob3b_get(c,r.a[6],0x85,1,value))return false;
        am_byte(r.d[0],bit?0xffU:0U);am_byte(r.d[1],value);am_byte(r.d[1],ob3b_b(r.d[1])^ob3b_b(r.d[0]));
        r.pc=ob3b_b(r.d[1])==0U?0x2be1e:0x2be1c;return true;
    case 0x2be1c:r.a[1]=r.a[2];r.pc=0x2be1e;return true;                    // MOVEA.L A2,A1.
    // MOVE.L #0,64(A6); MOVE.L #2be36,(A6).
    case 0x2be28:if(!ob3b_put(c,r.a[6],0x64,4,0))return false;return ob3b_install(c,0x2be36,0x2be36);
    // ---- 2be36: MOVE.W (A0),D0; BTST.B #2,D0; BEQ.W 2be60.
    case 0x2be4a:if(!ob3b_input_word(c))return false;ob3b_d0bit(r,2,false,0x2be54,0x2be60);return true;
    case 0x2be54:if(!ob3b_get(c,r.a[6],0x85,1,value))return false;r.pc=(value&0x80U)==0U?0x2bbb6:0x2be5c;return true;   // TST.B 85(A6); BPL.W 2bbb6.
    case 0x2be5c:r.pc=0x2bbdc;return true;                                    // BRA.W 2bbdc.
    case 0x2be60:ob3b_d0bit(r,3,false,0x2be68,0x2be74);return true;          // BTST.B #3,D0; BEQ.W 2be74.
    case 0x2be68:if(!ob3b_get(c,r.a[6],0x85,1,value))return false;r.pc=(value&0x80U)!=0U?0x2bb7e:0x2be70;return true;   // TST.B 85(A6); BMI.W 2bb7e.
    case 0x2be70:r.pc=0x2bba0;return true;                                    // BRA.W 2bba0.
    case 0x2be74:return ob3b_7f_at_least(c,5,0x2be7e,0x2beaa);               // CMPI.B #5,7f(A6); BCC.W 2beaa.
    case 0x2be7e:ob3b_d0bit(r,7,true,0x2be86,0x2c96a);return true;           // BTST.B #7,D0; BNE.W 2c96a.
    case 0x2be86:ob3b_d0bit(r,1,true,0x2be8e,0x2bfcc);return true;           // BTST.B #1,D0; BNE.W 2bfcc.
    case 0x2be8e:ob3b_d0bit(r,5,true,0x2be96,0x2c1ae);return true;           // BTST.B #5,D0; BNE.W 2c1ae.
    case 0x2be96:ob3b_d0bit(r,6,false,0x2be9e,0x2bea6);return true;          // BTST.B #6,D0; BEQ.W 2bea6.
    case 0x2bea6:r.pc=0x2bece;return true;                                    // BRA.W 2bece.
    case 0x2beaa:ob3b_d0bit(r,1,false,0x2beb2,0x2c0fc);return true;          // BTST.B #1,D0; BEQ.W 2c0fc.
    case 0x2beb2:ob3b_d0bit(r,7,true,0x2beba,0x2c96a);return true;           // BTST.B #7,D0; BNE.W 2c96a.
    case 0x2beba:ob3b_d0bit(r,5,true,0x2bec2,0x2c6cc);return true;           // BTST.B #5,D0; BNE.W 2c6cc.
    case 0x2bec2:ob3b_d0bit(r,6,false,0x2beca,0x2bece);return true;          // BTST.B #6,D0; BEQ.W 2bece.
    case 0x2bece:return ob3b_turn(c,true,0x2bee0,0x2baf4);                   // BYTE 82 := BYTE 7e; EOR bit 7 set: BMI.W 2baf4.
    case 0x2bee8:return ob3b_carry(c,0x2bef2,0x2beec);                       // BCC.W 2bef2 (C returned by 2b418).
    case 0x2bfa8:return ob3b_carry(c,0x2bfb2,0x2bfac);                       // BCC.W 2bfb2 (C returned by 2b418).
    case 0x2c074:return ob3b_carry(c,0x2c084,0x2c078);                       // BCC.W 2c084 (C returned by 2b418).
    case 0x2beec:return ob3b_install(c,0x2baf4,0x2bef2);                     // MOVE.L #2baf4,(A6).
    case 0x2bfac:return ob3b_install(c,0x2baf4,0x2bfb2);                     // MOVE.L #2baf4,(A6).
    case 0x2bfc2:return ob3b_install(c,0x2baf4,0x2bfc8);                     // MOVE.L #2baf4,(A6).
    // ---- 2bef6 aim: MOVE.B #0,7f(A6); MOVE.B 7e(A6),82(A6); MOVE.B #ff,81(A6); MOVEA.L #6c906,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2bef6:
        if(!ob3b_put(c,r.a[6],0x7f,1,0) || !ob3b_keep7e(c,value) || !ob3b_put(c,r.a[6],0x81,1,0xff))return false;return ob3b_anim(c,0x6c906,0x2bf18);
    case 0x2bf18:return ob3b_install(c,0x2bf1e,0x2bf1e);                     // MOVE.L #2bf1e,(A6).
    // MOVE.W (A0),D0; TST.B 81(A6); BEQ.W 2bf60.
    case 0x2bf32:if(!ob3b_input_word(c) || !ob3b_get(c,r.a[6],0x81,1,value))return false;r.pc=value==0U?0x2bf60:0x2bf3c;return true;
    case 0x2bf3c:return ob3b_speed_head(c,0x2bf4c,0x2bf4e);                  // MOVEQ #0,D7; D6 := LONG (LONG 9e); BTST.B #3,D0; BEQ.W 2bf4e.
    case 0x2bf4c:case 0x2c038:r.d[7]+=r.d[6];r.pc=r.pc+2U;return true;      // ADD.L D6,D7.
    case 0x2bf4e:ob3b_d0bit(r,2,false,0x2bf56,0x2bf58);return true;          // BTST.B #2,D0; BEQ.W 2bf58.
    case 0x2bf56:case 0x2c042:r.d[7]-=r.d[6];r.pc=r.pc+2U;return true;      // SUB.L D6,D7.
    case 0x2bf58:if(!ob3b_put(c,r.a[6],0x64,4,r.d[7]))return false;r.pc=0x2bf80;return true;   // MOVE.L D7,64(A6); BRA.W 2bf80.
    case 0x2bf60:ob3b_d0bit(r,1,true,0x2bf68,0x2bfcc);return true;           // BTST.B #1,D0; BNE.W 2bfcc.
    case 0x2bf68:ob3b_d0bit(r,3,true,0x2bf70,0x2bba0);return true;           // BTST.B #3,D0; BNE.W 2bba0.
    case 0x2bf70:ob3b_d0bit(r,2,true,0x2bf78,0x2bbdc);return true;           // BTST.B #2,D0; BNE.W 2bbdc.
    case 0x2bf78:if(!ob3b_put(c,r.a[6],0x64,4,0))return false;r.pc=0x2bf80;return true;   // MOVE.L #0,64(A6).
    case 0x2bf80:ob3b_d0bit(r,7,true,0x2bf88,0x2c96a);return true;           // BTST.B #7,D0; BNE.W 2c96a.
    case 0x2bf88:ob3b_d0bit(r,5,true,0x2bf90,0x2c1ae);return true;           // BTST.B #5,D0; BNE.W 2c1ae.
    case 0x2bf90:ob3b_d0bit(r,6,false,0x2bf98,0x2bfa0);return true;          // BTST.B #6,D0; BEQ.W 2bfa0.
    case 0x2bfb2:if(!ob3b_get(c,r.a[6],0x82,1,value))return false;r.pc=value==0U?0x2bfc8:0x2bfba;return true;   // TST.B 82(A6); BEQ.W 2bfc8.
    case 0x2bfba:if(!ob3b_get(c,r.a[6],0x7e,1,value))return false;r.pc=value!=0U?0x2bfc8:0x2bfc2;return true;   // TST.B 7e(A6); BNE.W 2bfc8.
    // ---- 2bfcc crouch: MOVE.W #1a5f,D0; JSR 3af8.l.
    case 0x2bfcc:return ob3b_sound(c,0x1a5f,0x2bfd6);
    case 0x2bfd6:if(!ob3b_keep7e(c,value))return false;return ob3b_anim(c,0x6556a,0x2bfec);   // MOVE.B 7e(A6),82(A6); MOVEA.L #6556a,A1; ... JSR 49f8c.l.
    case 0x2bfec:return ob3b_install(c,0x2bff2,0x2bff2);                     // MOVE.L #2bff2,(A6).
    // MOVE.B 7e(A6),D0; CMP.B 82(A6),D0; BEQ.W 2c012.
    case 0x2bff2:if(!ob3b_get(c,r.a[6],0x7e,1,value) || !ob3b_get(c,r.a[6],0x82,1,other))return false;am_byte(r.d[0],value);r.pc=value==other?0x2c012:0x2bffe;return true;
    // MOVE.B D0,82(A6); MOVEA.L #6556a,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2bffe:if(!ob3b_put(c,r.a[6],0x82,1,r.d[0]))return false;return ob3b_anim(c,0x6556a,0x2c012);
    // MOVE.W (A0),D0; MOVEQ #0,D7; MOVEA.L 9e(A6),A4; MOVE.L (A4),D6; BTST.B #3,D0; BEQ.W 2c03a.
    case 0x2c026:if(!ob3b_input_word(c))return false;return ob3b_speed_head(c,0x2c038,0x2c03a);
    case 0x2c03a:ob3b_d0bit(r,2,false,0x2c042,0x2c044);return true;          // BTST.B #2,D0; BEQ.W 2c044.
    // MOVE.L D7,64(A6); BTST.B #7,D0; BNE.W 2c96a.
    case 0x2c044:if(!ob3b_put(c,r.a[6],0x64,4,r.d[7]))return false;ob3b_d0bit(r,7,true,0x2c050,0x2c96a);return true;
    case 0x2c050:ob3b_d0bit(r,5,true,0x2c058,0x2c6cc);return true;           // BTST.B #5,D0; BNE.W 2c6cc.
    case 0x2c058:ob3b_d0bit(r,1,false,0x2c060,0x2c0fc);return true;          // BTST.B #1,D0; BEQ.W 2c0fc.
    case 0x2c060:ob3b_d0bit(r,6,false,0x2c068,0x2c06c);return true;          // BTST.B #6,D0; BEQ.W 2c06c.
    // MOVE.W #0,92(A6); MOVE.L #2c088,(A6).
    case 0x2c078:if(!ob3b_put(c,r.a[6],0x92,2,0))return false;return ob3b_install(c,0x2c088,0x2c084);
    // ---- 2c088 second stand: MOVEA.L #662c2,A1; MOVE.W #100,D0; JSR 49f8c.l / MOVE.L #2c09e,(A6).
    case 0x2c088:return ob3b_anim(c,0x662c2,0x2c098);
    case 0x2c098:return ob3b_install(c,0x2c09e,0x2c09e);
    case 0x2c0b2:if(!ob3b_input_word(c))return false;ob3b_d0bit(r,3,true,0x2c0bc,0x2bb7e);return true;   // MOVE.W (A0),D0; BTST.B #3,D0; BNE.W 2bb7e.
    case 0x2c0bc:ob3b_d0bit(r,2,true,0x2c0c4,0x2bbb6);return true;           // BTST.B #2,D0; BNE.W 2bbb6.
    case 0x2c0c4:ob3b_d0bit(r,1,false,0x2c0cc,0x2c0fc);return true;          // BTST.B #1,D0; BEQ.W 2c0fc.
    case 0x2c0cc:ob3b_d0bit(r,7,true,0x2c0d4,0x2c96a);return true;           // BTST.B #7,D0; BNE.W 2c96a.
    case 0x2c0d4:ob3b_d0bit(r,5,true,0x2c0dc,0x2c6cc);return true;           // BTST.B #5,D0; BNE.W 2c6cc.
    case 0x2c0dc:ob3b_d0bit(r,6,false,0x2c0e4,0x2c0e8);return true;          // BTST.B #6,D0; BEQ.W 2c0e8.
    // ---- 2c96a branch exit state: MOVE.W #1ac8,D0; JSR 3af8.l.
    case 0x2c96a:return ob3b_sound(c,0x1ac8,0x2c974);
    // MOVE.L #2c7a6,98(A6); MOVEA.L #68b02,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x2c974:if(!ob3b_put(c,r.a[6],0x98,4,OB3B_PATH))return false;return ob3b_anim(c,0x68b02,0x2c98c);
    // MOVE.W 88(A6),D0; MOVE.B #1,D1; JSR 4d4b4.l.
    case 0x2c98c:if(!ob3b_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],1);return am_call(c,0x4d4b4,0x2c99a);
    // MOVE.L #0,64(A6); MOVE.L #2c9a8,(A6).
    case 0x2c99a:if(!ob3b_put(c,r.a[6],0x64,4,0))return false;return ob3b_install(c,0x2c9a8,0x2c9a8);
    // MOVEA.L 98(A6),A0; CMPA.W #0,A0; BEQ.W 2c9d6 (32-bit compare with the extended WORD 0).
    case 0x2c9a8:if(!ob3b_get(c,r.a[6],0x98,4,value))return false;r.a[0]=value;r.pc=value==0U?0x2c9d6:0x2c9b4;return true;
    // MOVE.B 1a(A6),14(A6); MOVE.W (A0)+,D1; CMPI.W #ffff,D1; BNE.W 2c9c8.
    case 0x2c9b4:
        if(!ob3b_get(c,r.a[6],0x1a,1,value) || !ob3b_put(c,r.a[6],0x14,1,value) || !am_read(c,r.a[0],2,value))return false;
        am_word(r.d[1],value);r.a[0]+=2U;r.pc=ob3b_w(r.d[1])!=0xffffU?0x2c9c8:0x2c9c4;return true;
    // ADDA.W (A0),A0; MOVE.W (A0)+,D1.
    case 0x2c9c4:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=am_extend_word(value);if(!am_read(c,r.a[0],2,value))return false;
        am_word(r.d[1],value);r.a[0]+=2U;r.pc=0x2c9c8;return true;
    // MOVE.L A0,98(A6); MOVE.B 14(A6),D0; JSR 8d34.l (B3a).
    case 0x2c9c8:if(!ob3b_put(c,r.a[6],0x98,4,r.a[0]) || !ob3b_get(c,r.a[6],0x14,1,value))return false;am_byte(r.d[0],value);return am_call(c,0x8d34,0x2c9d6);
    // MOVE.L #c0000,D0; BTST.B #0,15(A6); BEQ.W 2c9e8.
    case 0x2c9d6:r.d[0]=0xc0000U;return ob3b_face(c,false,0x2c9e6,0x2c9e8);
    // SUB.L 64(A6),D0; ASR.L #5,D0 (explicit sign refill); ADD.L D0,64(A6); BSR.W 2c760 (N28).
    case 0x2c9e8:
        if(!ob3b_get(c,r.a[6],0x64,4,value))return false;r.d[0]-=value;
        r.d[0]=(r.d[0]>>5)|((r.d[0]&0x80000000U)!=0U?0xf8000000U:0U);
        if(!ob3b_get(c,r.a[6],0x64,4,value) || !ob3b_put(c,r.a[6],0x64,4,value+r.d[0]))return false;return am_call(c,0x2c760,0x2c9f6);
    // MOVE.W #8000,8e(A6); BTST.B #0,61(A6); BNE.W 2ca56.
    case 0x2c9fa:if(!ob3b_put(c,r.a[6],0x8e,2,0x8000) || !ob3b_bit(c,0x61,0,bit))return false;r.pc=bit?0x2ca56:0x2ca0a;return true;
    case 0x2ca0a:r.a[0]=0x2c8f2;return am_call(c,0x4ae4a,0x2ca14);          // LEA 2c8f2(PC),A0; JSR 4ae4a.l.
    case 0x2ca14:r.pc=ob3b_w(r.d[0])>=9U?0x2ca48:0x2ca1c;return true;      // CMPI.W #9,D0; BCC.W 2ca48 (unsigned).
    // ADD.W D0,D0; ADD.W D0,D0; JMP 2ca24(PC,D0.W) (no limit test here: the original target computation, F1 decision 3).
    case 0x2ca1c:am_word(r.d[0],r.d[0]*2U);am_word(r.d[0],r.d[0]*2U);r.pc=0x2ca24U+am_extend_word(r.d[0]);return true;
    // the 9 slots: BRA.W 2ca48 (0, 3..8) / BRA.W 2ca56 (1, 2).
    case 0x2ca24:case 0x2ca30:case 0x2ca34:case 0x2ca38:case 0x2ca3c:case 0x2ca40:case 0x2ca44:r.pc=0x2ca48;return true;
    case 0x2ca28:case 0x2ca2c:r.pc=0x2ca56;return true;
    case 0x2ca48:r.a[0]=0x2b6de;return am_call(c,0x1ab02,0x2ca52);          // LEA 2b6de(PC),A0; JSR 1ab02.l.
    case 0x2ca52:return ob3b_carry(c,0x2ca64,0x2ca56);                       // BCC.W 2ca64 (C returned by 1ab02).
    case 0x2ca56:r.a[0]=0x2c910;return am_call(c,0x4ae4a,0x2ca60);          // LEA 2c910(PC),A0; JSR 4ae4a.l.
    case 0x2ca60:r.pc=0x2ca68;return true;                                    // BRA.W 2ca68 (N28).
    case 0x2ca64:r.pc=0x2c8ca;return true;                                    // BRA.W 2c8ca (N28 shared tail).
    default:return am_error(c,"unsupported animation objects b3b PC");
    }
}
}
