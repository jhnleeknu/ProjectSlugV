#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr1_b(std::uint32_t value) {return value&255U;}
std::uint32_t ofr1_w(std::uint32_t value) {return value&65535U;}
// The low WORD as a signed value (CMP.W / BGE / BLT on WORDs).
std::int32_t ofr1_signed_word(std::uint32_t value) {
    const std::uint32_t w=value&65535U;return (w&0x8000U)!=0U?static_cast<std::int32_t>(w)-65536:static_cast<std::int32_t>(w);
}
bool ofr1_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr1_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// MOVE.L #value,(A6) (installed callback LONG); the fall-through enters the installed callback.
bool ofr1_install(AnimationMachineContext& c,std::uint32_t value) {
    if(!ofr1_put(c,c.s.a[6],0,4,value))return false;c.s.pc=value;return true;
}
// MOVE.L #value,(A6) followed by the next block (not the installed value).
bool ofr1_callback(AnimationMachineContext& c,std::uint32_t value,std::uint32_t next) {
    if(!ofr1_put(c,c.s.a[6],0,4,value))return false;c.s.pc=next;return true;
}
// MOVE.W #value,d(A6) then MOVE.L #install,(A6) (the fall-through enters the installed value).
bool ofr1_set_install(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t value,std::uint32_t install) {
    if(!ofr1_put(c,c.s.a[6],displacement,2,value))return false;return ofr1_install(c,install);
}
// SUBQ.W #1,d(A6); BEQ.W zero_pc (Z of the WORD result); otherwise other_pc.
bool ofr1_tick(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr1_get(c,c.s.a[6],displacement,2,value))return false;value=ofr1_w(value-1U);
    if(!ofr1_put(c,c.s.a[6],displacement,2,value))return false;c.s.pc=value==0U?zero_pc:other_pc;return true;
}
// TST.W d(A6); BEQ.W zero_pc; otherwise other_pc.
bool ofr1_test_word(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr1_get(c,c.s.a[6],displacement,2,value))return false;c.s.pc=ofr1_w(value)==0U?zero_pc:other_pc;return true;
}
// BCC on a C returned by a callee: clear -> clear_pc, set -> set_pc. Unknown C is never consumed.
bool ofr1_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr1 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVEA.L #child,A0; MOVE.W #n,D0; JSR 28ae.l (28ae child).
bool ofr1_28ae(AnimationMachineContext& c,std::uint32_t child,std::uint32_t n,std::uint32_t return_pc) {
    c.s.a[0]=child;am_word(c.s.d[0],n);return am_call(c,0x28ae,return_pc);
}
// MOVE.W #k,7a(A0) (the 28ae child or the dummy node), then the next 28ae child.
bool ofr1_child(AnimationMachineContext& c,std::uint32_t k,std::uint32_t child,std::uint32_t return_pc) {
    if(!ofr1_put(c,c.s.a[0],0x7a,2,k))return false;return ofr1_28ae(c,child,0x1e,return_pc);
}
// MOVEQ #d0,D0; MOVEQ #d1,D1; MOVEQ #d2,D2; MOVEQ #d3,D3 (sign-extended LONGs); JSR 8c16.l.
bool ofr1_8c16(AnimationMachineContext& c,std::uint32_t d012,std::uint32_t d3,std::uint32_t return_pc) {
    c.s.d[0]=d012;c.s.d[1]=d012;c.s.d[2]=d012;c.s.d[3]=d3;return am_call(c,0x8c16,return_pc);
}
// MOVE.W #n,D0; JSR 3af8.l.
bool ofr1_3af8(AnimationMachineContext& c,std::uint32_t n,std::uint32_t return_pc) {
    am_word(c.s.d[0],n);return am_call(c,0x3af8,return_pc);
}
// LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L bank.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l
// (the bank-window LONG and the LONG it points to are read through the live bus).
bool ofr1_bank_anim(AnimationMachineContext& c,std::uint32_t n,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    std::uint32_t value=0;c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr1_put(c,c.s.a[6],0x20,2,n) || !am_read(c,bank,4,value) || !ofr1_put(c,c.s.a[6],0x22,4,value))return false;
    am_word(c.s.d[0],0x100);c.s.a[0]=c.s.a[6]+0x26U;
    if(!ofr1_get(c,c.s.a[6],0x22,4,value))return false;c.s.a[1]=value;
    if(!ofr1_get(c,c.s.a[1],displacement,4,value))return false;c.s.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MULU.W #k,D0: unsigned 16 x 16 -> 32 (k <= c: the product fits 32 bits), the whole D0.
void ofr1_mulu(std::uint32_t& d,std::uint32_t k) {d=ofr1_w(d)*k;}
// DIVU.W D2,D0 (68000): zero divisor -> checked error (the original takes the vector 5 exception, not modeled); quotient > ffff sets V and
// leaves D0 unchanged; otherwise D0 = remainder:quotient. The C of DIVU is not read (the next instruction is SWAP).
bool ofr1_divu(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t divisor) {
    const std::uint32_t v=ofr1_w(divisor);
    if(v==0U)return am_error(c,"objects fr1 DIVU zero divisor");
    const std::uint32_t quotient=d/v,remainder=d%v;
    if(quotient>65535U)return true;
    d=(remainder<<16)|quotient;return true;
}
// DIVU.W D2,D0; SWAP D0; ANDI.W #f,D0 (the decimal digit in the low WORD; the quotient in the upper WORD).
bool ofr1_digit(AnimationMachineContext& c) {
    if(!ofr1_divu(c,c.s.d[0],c.s.d[2]))return false;am_swap(c.s.d[0]);am_word(c.s.d[0],c.s.d[0]&0xfU);return true;
}
// SWAP D0; ANDI.L #ffff,D0 (the quotient back in D0).
void ofr1_quotient(std::uint32_t& d) {am_swap(d);d&=0xffffU;}
// MOVE.W d(A6),D1; BPL.W plus_pc (N of the WORD); otherwise minus_pc.
bool ofr1_index_sign(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t plus_pc,std::uint32_t minus_pc) {
    std::uint32_t value=0;if(!ofr1_get(c,c.s.a[6],displacement,2,value))return false;am_word(c.s.d[1],value);
    c.s.pc=(value&0x8000U)==0U?plus_pc:minus_pc;return true;
}
// CMP.W d(A6),D1; BLT.W less_pc (signed D1.W < WORD); otherwise other_pc.
bool ofr1_index_less(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t less_pc,std::uint32_t other_pc) {
    std::uint32_t value=0;if(!ofr1_get(c,c.s.a[6],displacement,2,value))return false;
    c.s.pc=ofr1_signed_word(c.s.d[1])<ofr1_signed_word(value)?less_pc:other_pc;return true;
}
// MOVE.W s(A6),d(A6).
bool ofr1_copy_word(AnimationMachineContext& c,std::uint32_t from,std::uint32_t to) {
    std::uint32_t value=0;if(!ofr1_get(c,c.s.a[6],from,2,value))return false;return ofr1_put(c,c.s.a[6],to,2,value);
}
// MOVE.W d(A6),D0; ANDI.W #7,D0; BNE.W nonzero_pc; otherwise zero_pc.
bool ofr1_every8(AnimationMachineContext& c,std::uint32_t nonzero_pc,std::uint32_t zero_pc) {
    std::uint32_t value=0;if(!ofr1_get(c,c.s.a[6],0x7a,2,value))return false;am_word(c.s.d[0],value&7U);
    c.s.pc=(value&7U)!=0U?nonzero_pc:zero_pc;return true;
}
// MOVE.L #install,(A6); MOVE.W 7c(A6),D0; JSR 4e0de.l.
bool ofr1_pair(AnimationMachineContext& c,std::uint32_t install,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!ofr1_put(c,c.s.a[6],0,4,install) || !ofr1_get(c,c.s.a[6],0x7c,2,value))return false;
    am_word(c.s.d[0],value);return am_call(c,0x4e0de,return_pc);
}
// MOVE.W Dn,D0; CMPI.W #3e7,D0; BLS.W le_pc (unsigned D0.W <= 3e7); otherwise the clamp block.
void ofr1_clamp(AnimationMachineContext& c,std::uint32_t source,std::uint32_t le_pc,std::uint32_t clamp_pc) {
    am_word(c.s.d[0],source);c.s.pc=ofr1_w(c.s.d[0])<=0x3e7U?le_pc:clamp_pc;
}
// MOVE.W D0,76(A6); MOVE.W #text,D0; TST.W 7c(A6); BEQ.W zero_pc; otherwise other_pc.
bool ofr1_value(AnimationMachineContext& c,std::uint32_t text,std::uint32_t zero_pc,std::uint32_t other_pc) {
    if(!ofr1_put(c,c.s.a[6],0x76,2,c.s.d[0]))return false;am_word(c.s.d[0],text);return ofr1_test_word(c,0x7c,zero_pc,other_pc);
}
// LEA 76(A6),A0; LEA e84c8.l,A1; MOVEQ #0,D3; MOVEQ #3,D4; MOVE.W #461,D1; JMP 3670.l.
void ofr1_draw_value(AnimationMachineContext& c) {
    c.s.a[0]=c.s.a[6]+0x76U;c.s.a[1]=0xe84c8;c.s.d[3]=0;c.s.d[4]=3;am_word(c.s.d[1],0x461);c.s.pc=0x3670;
}
// MOVEA.L 6(Ax),A0; JMP (A0): the handler LONG of a kind record (live target through the routing).
bool ofr1_handler(AnimationMachineContext& c,std::uint32_t record) {
    std::uint32_t value=0;if(!ofr1_get(c,record,6,4,value))return false;c.s.a[0]=value;c.s.pc=value;return true;
}
}
// Objects FR1a (214 block starts, contract docs/analysis/animation-machine-frontier-fr1-contract.md): the first IO-frontier objects de660 (C2 28ae
// child; de660..de8bc, installs de686 de754 de778 de814 de84c de880) with the helpers ca42 (ca42..ca48) and 4e146 (4e146..4e166), e5324 (U02 28ae
// child; e5292..e5580, installs e5364 e537e e539e e5418 e5424 e543e e545e e54d8 e54e4 e5538 e5568) with the helpers 4e0de (4e0de..4e0f6) and the
// BCD helper e56c0 (e56c0..e5724, DIVU), the item object b3dbc (2986 child; b3dbc..b3dfc, b3ea2..b3eac, b3ec4..b3f40, b3f4c..b3f8c, b3fa4..b402a,
// installs b4012 b3fa4; the jump tables b3dcc / b3fce and the JMP (A0) handlers of the kind records b3484 go through the routing; TRAP #15 b3eac
// stays a boundary), the C helper 4b6f4 (4b6f4..4b702), d131a (d131a..d1348), the U06 neighbours eb9ba / eb9e4 (eb9ba..eba3e), the HUD list 51602
// (515e0..515fc, 51602..51608), the delete callback b7742 (b7742..b7748) and the U05 end state b975e (b975e..b97c0, installs b978c). Every other
// exit is routed. Known C: 4b6f4 (TST.B clears C) and 4b6fc (ORI.B #1,CCR) produce the C that 4b700 (RTS, carry preserving) passes to the 20
// callers; the 3 consumers b401e b9798 (BCC, 49fc6) and b97b4 (BCC, 1ab02) read a known C or fail. Data through the live bus (no limit test, as in
// the original): the bank LONGs 2001c0 / 2001d0 and c / 48 of LONG 22(A6), the item records b3894 + 12k, the kind records b3484 + 10k, the LONG
// table b3f8c, the WORD list (A0)+ (51620), the menu records eba9e + 8k. No X / port / bank write.
bool animation_objects_fr1_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;std::uint32_t other=0;
    switch(r.pc) {
    case 0xb3ed8:case 0xb7742:r.pc=0x2a00;return true;                                       // JMP 2a00.l.
    case 0xb97b8:r.pc=0x2a24;return true;                                                     // JMP 2a24.l.
    case 0x4b700:case 0x4e164:case 0xb4028:case 0xb97be:case 0xde68e:case 0xde75c:case 0xde782:case 0xde838:case 0xde854:case 0xde8a0:
    case 0xe536c:case 0xe5386:case 0xe542c:case 0xe5446:case 0xe54ec:case 0xe5540:case 0xe5570:case 0xeb9e2:case 0xeba3c:
        return am_return(c);                                                                  // RTS (4b700 keeps the incoming C).
    // ---- ca42: LEA -76a2(A5),A0; RTS.
    case 0xca42:r.a[0]=am_index(r.a[5],0x895e);return am_return(c);
    // ---- 4b6f4: TST.B 5b86(A5); BEQ.W 4b700 (TST clears C on both outcomes) / 4b6fc ORI.B #1,CCR (C Set).
    case 0x4b6f4:
        if(!ofr1_get(c,r.a[5],0x5b86,1,value))return false;r.carry=AnimationCarryClear;r.pc=ofr1_b(value)==0U?0x4b700:0x4b6fc;return true;
    case 0x4b6fc:r.carry=AnimationCarrySet;r.pc=0x4b700;return true;
    // ---- 4e0de: ANDI.W #1,D0; ADD.W D0,D0; LEA 5d22(A5),A0; MOVE.W (A0,D0.W),D1; LEA 5d26(A5),A0; MOVE.W (A0,D0.W),D2; RTS.
    case 0x4e0de:
        am_word(r.d[0],(r.d[0]&1U)*2U);r.a[0]=r.a[5]+0x5d22U;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[1],value);r.a[0]=r.a[5]+0x5d26U;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[2],value);return am_return(c);
    // ---- 4e146: MOVEQ #0,D0; LEA 1009a8.l,A0; BSR.W 4e158 / 4e152: LEA 100a6c.l,A0 / 4e158: CMPI.B #1,9c(A0); BNE.W 4e164 / 4e162: ADDQ.W #1,D0.
    case 0x4e146:r.d[0]=0;r.a[0]=0x1009a8;return am_call(c,0x4e158,0x4e152);
    case 0x4e152:r.a[0]=0x100a6c;r.pc=0x4e158;return true;
    case 0x4e158:if(!ofr1_get(c,r.a[0],0x9c,1,value))return false;r.pc=ofr1_b(value)==1U?0x4e162:0x4e164;return true;
    case 0x4e162:am_word(r.d[0],r.d[0]+1U);r.pc=0x4e164;return true;
    // ---- 51602 / 515e0: the WORD pair list (A0)+ (D0 then D1) until a negative D0, each pair with the pushed D2 to 8cda.
    case 0x51602:r.a[0]=0x51620;r.pc=0x515e0;return true;                                    // LEA 51620(PC),A0; BRA.B 515e0.
    case 0x515e0:if(!am_push(c,2,ofr1_w(r.d[2])))return false;r.pc=0x515e2;return true;      // MOVE.W D2,-(A7).
    case 0x515e2:                                                                             // MOVE.W (A0)+,D0; BPL.W 515ec.
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.a[0]+=2U;r.pc=(value&0x8000U)==0U?0x515ec:0x515e8;return true;
    case 0x515e8:r.a[7]+=2U;return am_return(c);                                             // ADDQ.W #2,A7; RTS.
    case 0x515ec:                                                                             // MOVE.W (A0)+,D1; MOVE.W (A7),D2; MOVE.L A0,-(A7); JSR 8cda.l.
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);r.a[0]+=2U;
        if(!am_read(c,r.a[7],2,value))return false;am_word(r.d[2],value);
        if(!am_push(c,4,r.a[0]))return false;return am_call(c,0x8cda,0x515f8);
    case 0x515f8:if(!am_pop(c,4,value))return false;r.a[0]=value;r.pc=0x515e2;return true;   // MOVEA.L (A7)+,A0; BRA.B 515e2.
    // ---- b3dbc (2986 child): MOVE.W 7e(A6),D0; CLR.W 7e(A6); ADD.W D0,D0; ADD.W D0,D0; JMP b3dcc(PC,D0.W) (the live target goes through the routing).
    case 0xb3dbc:
        if(!ofr1_get(c,r.a[6],0x7e,2,value) || !ofr1_put(c,r.a[6],0x7e,2,0))return false;am_word(r.d[0],value*4U);
        r.pc=am_index(0xb3dcc,r.d[0]);return true;
    case 0xb3dcc:r.pc=0xb3ddc;return true;                                                    // BRA.W b3ddc (jump table entry 0).
    case 0xb3dd0:r.pc=0xb3de4;return true;                                                    // BRA.W b3de4 (entry 1).
    case 0xb3dd4:r.pc=0xb3dec;return true;                                                    // BRA.W b3dec (entry 2).
    case 0xb3dd8:r.pc=0xb3df4;return true;                                                    // BRA.W b3df4 (entry 3).
    case 0xb3ddc:r.a[0]=0xb41be;r.pc=0xb3ea2;return true;                                    // LEA b41be(PC),A0; BRA.W b3ea2.
    case 0xb3de4:r.a[0]=0xb4036;r.pc=0xb3ea2;return true;
    case 0xb3dec:r.a[0]=0xb42a2;r.pc=0xb3ea2;return true;
    case 0xb3df4:r.a[0]=0xb403e;r.pc=0xb3ea2;return true;
    // CMPI.W #6e,76(A6); BCS.W b3ec4 (unsigned WORD < 6e); otherwise b3eac (TRAP #15, a boundary outside the unit).
    case 0xb3ea2:if(!ofr1_get(c,r.a[6],0x76,2,value))return false;r.pc=ofr1_w(value)<0x6eU?0xb3ec4:0xb3eac;return true;
    // MOVE.W #8838,68(A6); MOVE.W #8838,1e(A6); MOVE.W 76(A6),D0; BNE.W b3ede.
    case 0xb3ec4:
        if(!ofr1_put(c,r.a[6],0x68,2,0x8838) || !ofr1_put(c,r.a[6],0x1e,2,0x8838) || !ofr1_get(c,r.a[6],0x76,2,value))return false;
        am_word(r.d[0],value);r.pc=ofr1_w(value)!=0U?0xb3ede:0xb3ed8;return true;
    case 0xb3ede:if(!ofr1_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[1],value);r.pc=ofr1_w(value)!=0U?0xb3eea:0xb3ee6;return true;
    case 0xb3ee6:am_word(r.d[1],0x258);r.pc=0xb3eea;return true;                             // MOVE.W #258,D1.
    // MOVE.W 7a(A6),D2; MOVE.W 7c(A6),D3; BTST.B #2,95(A6); BNE.W b3f02.
    case 0xb3eea:
        if(!ofr1_get(c,r.a[6],0x7a,2,value))return false;am_word(r.d[2],value);
        if(!ofr1_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[3],value);
        if(!ofr1_get(c,r.a[6],0x95,1,value))return false;r.pc=(value&4U)!=0U?0xb3f02:0xb3efc;return true;
    case 0xb3efc:if(!ofr1_put(c,r.a[6],0x94,1,5))return false;r.pc=0xb3f02;return true;      // MOVE.B #5,94(A6).
    // MOVE.L A0,76(A6); MOVE.L A0,7a(A6); MOVE.W D1,8c(A6); MOVE.B D2,95(A6); ANDI.B #3,D2; EOR.B D2,15(A6); MOVE.W D0,8a(A6); JSR b3f4c(PC).
    case 0xb3f02:
        if(!ofr1_put(c,r.a[6],0x76,4,r.a[0]) || !ofr1_put(c,r.a[6],0x7a,4,r.a[0]) || !ofr1_put(c,r.a[6],0x8c,2,r.d[1]) ||
           !ofr1_put(c,r.a[6],0x95,1,r.d[2]))return false;
        am_byte(r.d[2],r.d[2]&3U);
        if(!ofr1_get(c,r.a[6],0x15,1,value) || !ofr1_put(c,r.a[6],0x15,1,value^ofr1_b(r.d[2])) || !ofr1_put(c,r.a[6],0x8a,2,r.d[0]))return false;
        return am_call(c,0xb3f4c,0xb3f22);
    case 0xb3f22:return am_call(c,0xb3f68,0xb3f26);                                           // JSR b3f68(PC).
    case 0xb3f26:return am_call(c,0x49a58,0xb3f2c);                                           // JSR 49a58.l.
    // ANDI.W #8000,D0; MOVE.W D0,98(A6); TST.W D3; BNE.W b3fc6.
    case 0xb3f2c:am_word(r.d[0],r.d[0]&0x8000U);if(!ofr1_put(c,r.a[6],0x98,2,r.d[0]))return false;r.pc=ofr1_w(r.d[3])!=0U?0xb3fc6:0xb3f3a;return true;
    case 0xb3f3a:return ofr1_handler(c,r.a[1]);                                               // MOVEA.L 6(A1),A0; JMP (A0).
    case 0xb3f4c:return am_call(c,0xb3f5c,0xb3f50);                                           // JSR b3f5c(PC).
    // MOVE.B (A0),D0; ANDI.W #ff,D0; MOVE.W D0,90(A6); RTS.
    case 0xb3f50:if(!am_read(c,r.a[0],1,value))return false;am_word(r.d[0],ofr1_b(value));if(!ofr1_put(c,r.a[6],0x90,2,r.d[0]))return false;return am_return(c);
    // MULU.W #c,D0; LEA b3894(PC),A0; ADDA.W D0,A0; RTS.
    case 0xb3f5c:ofr1_mulu(r.d[0],12U);r.a[0]=am_index(0xb3894,r.d[0]);return am_return(c);
    // MOVE.W 2(A0),D0; MULU.W #a,D0; LEA b3484(PC),A1; ADDA.W D0,A1; MOVE.W 2(A1),8e(A6); MOVE.B (A1),97(A6); MOVE.W 4(A1),D0;
    // MOVE.L b3f8c(PC,D0.W),7e(A6); RTS.
    case 0xb3f68:
        if(!ofr1_get(c,r.a[0],2,2,value))return false;am_word(r.d[0],value);ofr1_mulu(r.d[0],10U);r.a[1]=am_index(0xb3484,r.d[0]);
        if(!ofr1_get(c,r.a[1],2,2,value) || !ofr1_put(c,r.a[6],0x8e,2,value) || !am_read(c,r.a[1],1,value) || !ofr1_put(c,r.a[6],0x97,1,value) ||
           !ofr1_get(c,r.a[1],4,2,value))return false;
        am_word(r.d[0],value);if(!am_read(c,am_index(0xb3f8c,r.d[0]),4,value) || !ofr1_put(c,r.a[6],0x7e,4,value))return false;return am_return(c);
    case 0xb3fa4:return am_call(c,0x8ff4,0xb3faa);                                            // JSR 8ff4.l (installed value / table target).
    case 0xb3faa:if(!ofr1_get(c,r.a[6],0x8a,2,value))return false;am_word(r.d[0],value);return am_call(c,0xb3f5c,0xb3fb2);   // MOVE.W 8a(A6),D0; JSR b3f5c(PC).
    // MOVE.W 2(A0),D0; MULU.W #a,D0; LEA b3484(PC),A0; ADDA.W D0,A0; MOVEA.L 6(A0),A0; JMP (A0).
    case 0xb3fb2:
        if(!ofr1_get(c,r.a[0],2,2,value))return false;am_word(r.d[0],value);ofr1_mulu(r.d[0],10U);r.a[0]=am_index(0xb3484,r.d[0]);
        return ofr1_handler(c,r.a[0]);
    // ADD.W D3,D3; ADD.W D3,D3; JMP b3fce(PC,D3.W) (the live target goes through the routing).
    case 0xb3fc6:am_word(r.d[3],r.d[3]*4U);r.pc=am_index(0xb3fce,r.d[3]);return true;
    case 0xb3fce:r.pc=0xb3fa4;return true;                                                    // BRA.W b3fa4 (jump table entry 0).
    case 0xb3fd2:r.pc=0xb3fd6;return true;                                                    // BRA.W b3fd6 (entry 1).
    case 0xb3fd6:return ofr1_bank_anim(c,0x1e3,0x2001c0,0xc,0xb3ffe);                        // ...; MOVEA.L c(A1),A1; JSR 49f8c.l.
    case 0xb3ffe:am_word(r.d[0],0x380);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xb400c);    // MOVE.W #380,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0xb400c:return ofr1_install(c,0xb4012);
    case 0xb4012:case 0xb978c:return am_call(c,0x43e34,r.pc+6U);                              // JSR 43e34.l (installed values).
    case 0xb4018:case 0xb9792:return am_call(c,0x49fc6,r.pc+6U);                              // JSR 49fc6.l.
    case 0xb401e:return ofr1_carry(c,0xb4028,0xb4022);                                        // BCC.W b4028 (C of 49fc6).
    case 0xb4022:return ofr1_callback(c,0xb3fa4,0xb4028);                                     // MOVE.L #b3fa4,(A6).
    // ---- b975e (U05 installed value): bank animation 2001d0 / 48; MOVE.L #b978c,(A6).
    case 0xb975e:return ofr1_bank_anim(c,0x203,0x2001d0,0x48,0xb9786);
    case 0xb9786:return ofr1_install(c,0xb978c);
    case 0xb9798:return ofr1_carry(c,0xb97a8,0xb979c);                                        // BCC.W b97a8 (C of 49fc6).
    case 0xb979c:if(!ofr1_put(c,r.a[6],0x76,2,1))return false;return ofr1_callback(c,0xb970e,0xb97a8);   // MOVE.W #1,76(A6); MOVE.L #b970e,(A6).
    case 0xb97a8:r.a[0]=0xba3d6;return am_call(c,0x1ab02,0xb97b4);                           // LEA ba3d6.l,A0; JSR 1ab02.l.
    case 0xb97b4:return ofr1_carry(c,0xb97be,0xb97b8);                                        // BCC.W b97be (C of 1ab02).
    // ---- d131a: MOVEA.L #d13b4,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.l / MOVE.W #0,76(A0); MOVEQ #0,D0; MOVE.W #20,D1; JSR 49214.l.
    case 0xd131a:r.a[0]=0xd13b4;am_word(r.d[0],0x14);r.a[1]=0x100bf4;return am_call(c,0x2986,0xd1330);
    case 0xd1330:if(!ofr1_put(c,r.a[0],0x76,2,0))return false;r.d[0]=0;am_word(r.d[1],0x20);return am_call(c,0x49214,0xd1342);
    case 0xd1342:r.pc=0x491b6;return true;                                                    // JMP 491b6.l.
    // ---- de660 (C2 28ae child).
    case 0xde660:case 0xde856:return ofr1_8c16(c,0xffffffe1U,0xf,r.pc+0xeU);                 // MOVEQ #e1,D0/D1/D2; MOVEQ #f,D3; JSR 8c16.l.
    case 0xde66e:case 0xde83a:return am_call(c,0xca48,r.pc+6U);                               // JSR ca48.l.
    case 0xde674:return am_call(c,0xca8a,0xde67a);                                            // JSR ca8a.l.
    case 0xde67a:return ofr1_set_install(c,0x76,4,0xde686);                                   // MOVE.W #4,76(A6); MOVE.L #de686,(A6).
    case 0xde686:return ofr1_tick(c,0x76,0xde690,0xde68e);                                    // SUBQ.W #1,76(A6); BEQ.W de690 (installed value).
    case 0xde690:r.a[0]=0xde526;return am_call(c,0x1a5a4,0xde69a);                           // LEA de526(PC),A0; JSR 1a5a4.l.
    case 0xde69a:return ofr1_28ae(c,0xde97e,0x1e,0xde6aa);
    case 0xde6aa:return ofr1_28ae(c,0xde8ca,0x1e,0xde6ba);
    case 0xde6ba:return ofr1_child(c,0,0xde8ca,0xde6d0);                                      // MOVE.W #0,7a(A0); next 28ae child.
    case 0xde6d0:return ofr1_child(c,1,0xdeba4,0xde6e6);
    case 0xde6e6:return ofr1_child(c,0,0xdeba4,0xde6fc);
    case 0xde6fc:return ofr1_child(c,1,0xdeba4,0xde712);
    case 0xde712:return ofr1_child(c,2,0xdeba4,0xde728);
    case 0xde728:if(!ofr1_put(c,r.a[0],0x7a,2,3))return false;return ofr1_3af8(c,0x19da,0xde738);   // MOVE.W #3,7a(A0); MOVE.W #19da,D0; JSR 3af8.l.
    case 0xde738:return ofr1_3af8(c,0x73c,0xde742);
    case 0xde742:if(!ofr1_put(c,r.a[6],0x62,1,0))return false;return ofr1_set_install(c,0x76,4,0xde754);   // MOVE.B #0,62(A6); MOVE.W #4,76(A6); install.
    case 0xde754:return ofr1_tick(c,0x76,0xde75e,0xde75c);
    case 0xde75e:return am_call(c,0xcaf0,0xde764);                                            // JSR caf0.l.
    case 0xde764:return ofr1_8c16(c,0,8,0xde772);                                             // MOVEQ #0,D0/D1/D2; MOVEQ #8,D3; JSR 8c16.l.
    case 0xde772:return ofr1_install(c,0xde778);
    case 0xde778:if(!ofr1_get(c,r.a[6],0x62,1,value))return false;r.pc=ofr1_b(value)==4U?0xde784:0xde782;return true;   // CMPI.B #4,62(A6); BEQ.W.
    case 0xde784:return am_call(c,0xca56,0xde78a);                                            // JSR ca56.l.
    case 0xde78a:return ofr1_28ae(c,0xdeb1a,0x1e,0xde79a);
    case 0xde79a:return ofr1_child(c,0,0xdeb1a,0xde7b0);
    case 0xde7b0:return ofr1_child(c,1,0xdeb1a,0xde7c6);
    case 0xde7c6:return ofr1_child(c,2,0xdeb1a,0xde7dc);
    case 0xde7dc:return ofr1_child(c,3,0xde9e8,0xde7f2);
    case 0xde7f2:return ofr1_child(c,0,0xde9e8,0xde808);
    case 0xde808:if(!ofr1_put(c,r.a[0],0x7a,2,1))return false;return ofr1_install(c,0xde814);   // MOVE.W #1,7a(A0); MOVE.L #de814,(A6).
    case 0xde814:return am_call(c,0xca42,0xde81a);                                            // JSR ca42.l (installed value).
    case 0xde81a:am_word(r.d[0],0x727b);am_word(r.d[1],3);r.d[3]=0;r.d[4]=2;return am_call(c,0x36ba,0xde82c);   // ...; JSR 36ba.l.
    case 0xde82c:return am_call(c,0x4e146,0xde832);                                           // JSR 4e146.l.
    case 0xde832:r.pc=ofr1_b(r.d[0])==0U?0xde83a:0xde838;return true;                        // TST.B D0; BEQ.W de83a.
    case 0xde840:return ofr1_set_install(c,0x76,0x4b,0xde84c);
    case 0xde84c:return ofr1_tick(c,0x76,0xde856,0xde854);
    case 0xde864:if(!ofr1_put(c,r.a[6],0x76,2,0x14))return false;am_word(r.d[0],0x73c);return am_call(c,0x3c44,0xde874);   // ...; JSR 3c44.l.
    case 0xde874:return ofr1_set_install(c,0x82,0x19c0,0xde880);
    // CMPI.W #19cf,82(A6); BGE.W de898 (signed WORD >= 19cf).
    case 0xde880:if(!ofr1_get(c,r.a[6],0x82,2,value))return false;r.pc=ofr1_signed_word(value)>=0x19cf?0xde898:0xde88a;return true;
    // ADDQ.W #1,82(A6); MOVE.W 82(A6),D0; JSR 3af8.l.
    case 0xde88a:
        if(!ofr1_get(c,r.a[6],0x82,2,value) || !ofr1_put(c,r.a[6],0x82,2,value+1U) || !ofr1_get(c,r.a[6],0x82,2,value))return false;
        am_word(r.d[0],value);return am_call(c,0x3af8,0xde898);
    case 0xde898:return ofr1_tick(c,0x76,0xde8a2,0xde8a0);
    case 0xde8a2:return ofr1_3af8(c,0x19c0,0xde8ac);
    // MOVEA.L c(A6),A0; MOVE.B #ff,62(A0); JMP 2a24.l.
    case 0xde8ac:if(!ofr1_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr1_put(c,r.a[0],0x62,1,0xff))return false;r.pc=0x2a24;return true;
    // ---- e5292 e52b2 e52d6 e52f6: text of the results object (D0 text id, A0 text, A1 = e84c8; JMP 3a70.l).
    case 0xe5292:am_word(r.d[0],0x706d);return ofr1_test_word(c,0x7c,0xe52a2,0xe529e);       // MOVE.W #706d,D0; TST.W 7c(A6); BEQ.W e52a2.
    case 0xe529e:am_word(r.d[0],0x72ad);r.pc=0xe52a2;return true;
    case 0xe52a2:r.a[0]=0xe503c;r.a[1]=0xe84c8;r.pc=0x3a70;return true;                     // LEA e503c(PC),A0; LEA e84c8.l,A1; JMP 3a70.l.
    case 0xe52b2:am_word(r.d[0],0x706a);r.a[0]=0xe5014;return ofr1_test_word(c,0x7c,0xe52ca,0xe52c2);
    case 0xe52c2:am_word(r.d[0],0x72aa);r.a[0]=0xe5028;r.pc=0xe52ca;return true;
    case 0xe52ca:case 0xe52ea:case 0xe5318:r.a[1]=0xe84c8;r.pc=0x3a70;return true;           // LEA e84c8.l,A1; JMP 3a70.l.
    case 0xe52d6:am_word(r.d[0],0x7074);r.a[0]=0xe507a;return ofr1_test_word(c,0x7c,0xe52ea,0xe52e6);
    case 0xe52e6:am_word(r.d[0],0x72b4);r.pc=0xe52ea;return true;
    // LEA e504c(PC),A0; CMPI.B #3,-8000(A5); BEQ.W e5308.
    case 0xe52f6:r.a[0]=0xe504c;if(!ofr1_get(c,r.a[5],0x8000,1,value))return false;r.pc=ofr1_b(value)==3U?0xe5308:0xe5304;return true;
    case 0xe5304:r.a[0]=0xe505e;r.pc=0xe5308;return true;
    case 0xe5308:am_word(r.d[0],0x7070);return ofr1_test_word(c,0x7c,0xe5318,0xe5314);
    case 0xe5314:am_word(r.d[0],0x72b0);r.pc=0xe5318;return true;
    // ---- e5324 (U02 28ae child): LEA 10fdb6.l,A0; MOVE.W 7c(A6),D0; ANDI.W #1,D0; CMPI.B #1,(A0,D0.W); BNE.W e5572.
    case 0xe5324:
        r.a[0]=0x10fdb6;if(!ofr1_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[0],value&1U);
        if(!am_read(c,am_index(r.a[0],r.d[0]),1,value))return false;r.pc=ofr1_b(value)!=1U?0xe5572:0xe533c;return true;
    // MOVEA.L c(A6),A0; MOVE.W 82(A0),D0; TST.W 7c(A6); BEQ.W e5350.
    case 0xe533c:
        if(!ofr1_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr1_get(c,r.a[0],0x82,2,value))return false;am_word(r.d[0],value);
        return ofr1_test_word(c,0x7c,0xe5350,0xe534c);
    case 0xe534c:if(!ofr1_get(c,r.a[0],0x84,2,value))return false;am_word(r.d[0],value);r.pc=0xe5350;return true;   // MOVE.W 84(A0),D0.
    case 0xe5350:if(!ofr1_put(c,r.a[6],0x80,2,r.d[0]))return false;return am_call(c,0xe52b2,0xe5358);   // MOVE.W D0,80(A6); BSR.W e52b2.
    case 0xe5358:case 0xe5418:case 0xe54d8:                                                   // MOVE.W #f,7a(A6); MOVE.L #next,(A6).
        return ofr1_set_install(c,0x7a,0xf,r.pc==0xe5358U?0xe5364U:(r.pc==0xe5418U?0xe5424U:0xe54e4U));
    case 0xe5364:return ofr1_tick(c,0x7a,0xe536e,0xe536c);                                    // SUBQ.W #1,7a(A6); BEQ.W (installed values).
    case 0xe537e:return ofr1_tick(c,0x7a,0xe5388,0xe5386);
    case 0xe5424:return ofr1_tick(c,0x7a,0xe542e,0xe542c);
    case 0xe543e:return ofr1_tick(c,0x7a,0xe5448,0xe5446);
    case 0xe54e4:return ofr1_tick(c,0x7a,0xe54ee,0xe54ec);
    case 0xe5538:return ofr1_tick(c,0x7a,0xe5542,0xe5540);
    case 0xe536e:return am_call(c,0xe5292,0xe5372);                                           // BSR.W e5292.
    case 0xe5372:return ofr1_set_install(c,0x7a,8,0xe537e);
    case 0xe542e:return am_call(c,0xe52f6,0xe5432);                                           // BSR.W e52f6.
    case 0xe5432:return ofr1_set_install(c,0x7a,8,0xe543e);
    case 0xe5388:case 0xe5448:return ofr1_3af8(c,0x1ac4,r.pc+0xaU);                           // MOVE.W #1ac4,D0; JSR 3af8.l.
    case 0xe5392:return ofr1_set_install(c,0x7a,0x1e,0xe539e);
    case 0xe5452:return ofr1_set_install(c,0x7a,0x1e,0xe545e);
    // SUBQ.W #1,7a(A6); BEQ.W e53ca / e548a (installed values); the fall-through e53a6 / e5466 tests every 8th tick.
    case 0xe539e:return ofr1_tick(c,0x7a,0xe53ca,0xe53a6);
    case 0xe545e:return ofr1_tick(c,0x7a,0xe548a,0xe5466);
    case 0xe53a6:return ofr1_every8(c,0xe53bc,0xe53b2);                                       // MOVE.W 7a(A6),D0; ANDI.W #7,D0; BNE.W e53bc.
    case 0xe5466:return ofr1_every8(c,0xe547c,0xe5472);
    case 0xe53b2:case 0xe5472:return ofr1_3af8(c,0x1ac4,r.pc+0xaU);
    case 0xe53bc:case 0xe547c:am_word(r.d[0],0x3e8);return am_call(c,0x49a84,r.pc+0xaU);     // MOVE.W #3e8,D0; JSR 49a84.l.
    case 0xe53c6:r.pc=0xe53e8;return true;                                                    // BRA.W e53e8.
    case 0xe5486:r.pc=0xe54a8;return true;                                                    // BRA.W e54a8.
    case 0xe53ca:return ofr1_pair(c,0xe5418,0xe53da);                                         // MOVE.L #e5418,(A6); MOVE.W 7c(A6),D0; JSR 4e0de.l.
    case 0xe548a:return ofr1_pair(c,0xe54d8,0xe549a);
    case 0xe53da:ofr1_clamp(c,r.d[1],0xe53e8,0xe53e4);return true;                           // MOVE.W D1,D0; CMPI.W #3e7,D0; BLS.W e53e8.
    case 0xe549a:ofr1_clamp(c,r.d[2],0xe54a8,0xe54a4);return true;                           // MOVE.W D2,D0; ...
    case 0xe53e4:am_word(r.d[0],0x3e7);r.pc=0xe53e8;return true;                             // MOVE.W #3e7,D0.
    case 0xe54a4:am_word(r.d[0],0x3e7);r.pc=0xe54a8;return true;
    case 0xe53e8:case 0xe54a8:return am_call(c,0xe56c0,r.pc+4U);                              // BSR.W e56c0.
    case 0xe53ec:return ofr1_value(c,0x71ed,0xe5400,0xe53fc);                                 // MOVE.W D0,76(A6); MOVE.W #71ed,D0; TST.W 7c(A6); BEQ.W e5400.
    case 0xe54ac:return ofr1_value(c,0x71f0,0xe54c0,0xe54bc);
    case 0xe53fc:am_word(r.d[0],0x742d);r.pc=0xe5400;return true;
    case 0xe54bc:am_word(r.d[0],0x7430);r.pc=0xe54c0;return true;
    case 0xe5400:case 0xe54c0:ofr1_draw_value(c);return true;                                // ...; JMP 3670.l.
    case 0xe54ee:return ofr1_3af8(c,0x1acf,0xe54f8);
    case 0xe54f8:return am_call(c,0xe52d6,0xe54fc);                                           // BSR.W e52d6.
    case 0xe54fc:r.a[0]=0x10de14;am_word(r.d[0],0x7154);return ofr1_test_word(c,0x7c,0xe5518,0xe550e);   // LEA 10de14.l,A0; MOVE.W #7154,D0; TST.W 7c(A6).
    case 0xe550e:r.a[0]=0x10de1c;am_word(r.d[0],0x7394);r.pc=0xe5518;return true;
    // LEA e84c8.l,A1; MOVEQ #0,D3; MOVEQ #8,D4; MOVE.W #461,D1; JSR 3670.l.
    case 0xe5518:r.a[1]=0xe84c8;r.d[3]=0;r.d[4]=8;am_word(r.d[1],0x461);return am_call(c,0x3670,0xe552c);
    case 0xe552c:return ofr1_set_install(c,0x7a,0x1e,0xe5538);
    case 0xe5542:return ofr1_28ae(c,0xe5580,0,0xe5552);                                       // MOVEA.L #e5580,A0; MOVE.W #0,D0; JSR 28ae.l.
    // MOVE.W 7c(A6),7c(A0); MOVE.W 80(A6),80(A0); CLR.B 62(A6); MOVE.L #e5568,(A6).
    case 0xe5552:
        if(!ofr1_get(c,r.a[6],0x7c,2,value) || !ofr1_put(c,r.a[0],0x7c,2,value) || !ofr1_get(c,r.a[6],0x80,2,value) || !ofr1_put(c,r.a[0],0x80,2,value) ||
           !ofr1_put(c,r.a[6],0x62,1,0))return false;
        return ofr1_install(c,0xe5568);
    case 0xe5568:if(!ofr1_get(c,r.a[6],0x62,1,value))return false;r.pc=ofr1_b(value)!=0U?0xe5572:0xe5570;return true;   // TST.B 62(A6); BNE.W e5572.
    // MOVEA.L c(A6),A0; ADDQ.B #1,62(A0); JMP 2a00.l.
    case 0xe5572:
        if(!ofr1_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!ofr1_get(c,r.a[0],0x62,1,value) || !ofr1_put(c,r.a[0],0x62,1,value+1U))return false;r.pc=0x2a00;return true;
    // ---- e56c0: the decimal BCD of D0.W (MOVEQ #0,D3; MOVE.W #a,D2; ANDI.L #ffff,D0; BEQ.W e5720).
    case 0xe56c0:r.d[3]=0;am_word(r.d[2],0xa);r.d[0]&=0xffffU;r.pc=r.d[0]==0U?0xe5720:0xe56d0;return true;
    // DIVU.W D2,D0; SWAP D0; ANDI.W #f,D0; MOVE.W D0,D3; SWAP D0; ANDI.L #ffff,D0; BEQ.W e5720.
    case 0xe56d0:if(!ofr1_digit(c))return false;am_word(r.d[3],r.d[0]);ofr1_quotient(r.d[0]);r.pc=r.d[0]==0U?0xe5720:0xe56e6;return true;
    // DIVU.W D2,D0; SWAP D0; ANDI.W #f,D0; LSL.W #4,D0; OR.W D0,D3; SWAP D0; ANDI.L #ffff,D0; BEQ.W e5720.
    case 0xe56e6:
        if(!ofr1_digit(c))return false;am_word(r.d[0],r.d[0]<<4);am_word(r.d[3],r.d[3]|ofr1_w(r.d[0]));ofr1_quotient(r.d[0]);
        r.pc=r.d[0]==0U?0xe5720:0xe56fe;return true;
    // DIVU; SWAP; ANDI.W #f; LSL.W #8; OR.W D0,D3; SWAP; ANDI.L #ffff; DIVU; SWAP; ANDI.W #f; LSL.W #8; LSL.W #4; OR.W D0,D3.
    case 0xe56fe:
        if(!ofr1_digit(c))return false;am_word(r.d[0],r.d[0]<<8);am_word(r.d[3],r.d[3]|ofr1_w(r.d[0]));ofr1_quotient(r.d[0]);
        if(!ofr1_digit(c))return false;am_word(r.d[0],r.d[0]<<8);am_word(r.d[0],r.d[0]<<4);am_word(r.d[3],r.d[3]|ofr1_w(r.d[0]));
        r.pc=0xe5720;return true;
    case 0xe5720:am_word(r.d[0],r.d[3]);return am_return(c);                                  // MOVE.W D3,D0; RTS.
    // ---- eb9ba / eb9e4 (U06 neighbours): the menu index wrap of WORD 7e (limit WORD 7a) and of WORD 7c (limit WORD 78).
    case 0xeb9ba:r.d[3]=0;return ofr1_index_sign(c,0x7e,0xeb9ce,0xeb9c4);                    // MOVEQ #0,D3; MOVE.W 7e(A6),D1; BPL.W eb9ce.
    case 0xeb9c4:if(!ofr1_copy_word(c,0x7a,0x7e))return false;r.pc=0xeb9dc;return true;      // MOVE.W 7a(A6),7e(A6); BRA.W eb9dc.
    case 0xeb9ce:return ofr1_index_less(c,0x7a,0xeb9dc,0xeb9d6);                              // CMP.W 7a(A6),D1; BLT.W eb9dc.
    case 0xeb9d6:if(!ofr1_put(c,r.a[6],0x7e,2,0))return false;r.pc=0xeb9dc;return true;      // MOVE.W #0,7e(A6).
    case 0xeb9dc:r.pc=ofr1_w(r.d[3])!=0U?0xeb9e4:0xeb9e2;return true;                        // TST.W D3; BNE.W eb9e4.
    case 0xeb9e4:return ofr1_index_sign(c,0x7c,0xeb9fa,0xeb9ec);                              // MOVE.W 7c(A6),D1; BPL.W eb9fa.
    // MOVE.W 78(A6),7c(A6); SUBQ.W #1,7c(A6); BRA.W eba08.
    case 0xeb9ec:
        if(!ofr1_copy_word(c,0x78,0x7c) || !ofr1_get(c,r.a[6],0x7c,2,value) || !ofr1_put(c,r.a[6],0x7c,2,value-1U))return false;r.pc=0xeba08;return true;
    case 0xeb9fa:return ofr1_index_less(c,0x78,0xeba08,0xeba02);                              // CMP.W 78(A6),D1; BLT.W eba08.
    case 0xeba02:if(!ofr1_put(c,r.a[6],0x7c,2,0))return false;r.pc=0xeba08;return true;      // MOVE.W #0,7c(A6).
    // LEA eba9e(PC),A0; MOVE.W 7c(A6),D0; LSL.W #3,D0; MOVE.L (A0,D0.W),80(A6); MOVE.W 4(A0,D0.W),84(A6); MOVE.W 6(A0,D0.W),86(A6); JSR eba3e(PC).
    case 0xeba08:
        r.a[0]=0xeba9e;if(!ofr1_get(c,r.a[6],0x7c,2,value))return false;am_word(r.d[0],value<<3);other=am_index(r.a[0],r.d[0]);
        if(!am_read(c,other,4,value) || !ofr1_put(c,r.a[6],0x80,4,value) || !am_read(c,other+4U,2,value) || !ofr1_put(c,r.a[6],0x84,2,value) ||
           !am_read(c,other+6U,2,value) || !ofr1_put(c,r.a[6],0x86,2,value))return false;
        return am_call(c,0xeba3e,0xeba28);
    case 0xeba28:return am_call(c,0x8ff4,0xeba2e);                                            // JSR 8ff4.l.
    case 0xeba2e:if(!ofr1_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xeba3c);   // ...; JSR 8ebe.l.
    default:return am_error(c,"unsupported animation objects fr1 PC");
    }
}
}
