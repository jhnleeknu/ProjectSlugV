#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute and PC relative data operands (read through the live bus).
const std::uint32_t OU5_RANGE_RECORD=0xba3d6;  // b9746 LEA ba3d6.L,A0 (two LONGs for 1ab02, fixed ROM)
const std::uint32_t OU5_BANK_POINTER=0x2001d0; // b96f0 MOVE.L 2001d0.L,22(A6) (bank window, live bank_base)
const std::uint32_t OU5_BASE_TABLE=0xc6e08;    // c6bfa LEA c6e08(PC),A1 (WORD per object kind, fixed ROM)
const std::uint32_t OU5_LIST_TABLE=0xc6c24;    // c6c04 LEA c6c24(PC),A1 (LONG list pointer per object kind, fixed ROM)
bool ou5_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou5_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Signed view of a WORD (explicit two's complement).
std::int32_t ou5_signed_word(std::uint32_t value) {
    value&=65535U;return (value&0x8000U)?static_cast<std::int32_t>(value)-65536:static_cast<std::int32_t>(value);
}
// ADD.W src,Dn (WORD, upper half kept).
void ou5_add_word(std::uint32_t& d,std::uint32_t src) {am_word(d,(d+src)&65535U);}
// ADD.W D1,D0; NEG.W D0.
void ou5_add_negate(AnimationMachineState& r) {ou5_add_word(r.d[0],r.d[1]);am_word(r.d[0],(0U-(r.d[0]&65535U))&65535U);}
// MOVE.L d16(A6),D2; CMP.L d16(A6),D2; BEQ equal_pc; BMI minus_pc (bundled: N = bit 31 of the same CMP.L), else plus_pc.
bool ou5_range_compare(AnimationMachineContext& c,std::uint32_t own,std::uint32_t other,std::uint32_t equal_pc,
    std::uint32_t minus_pc,std::uint32_t plus_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,limit=0;
    if(!ou5_get(c,r.a[6],own,4,value) || !ou5_get(c,r.a[6],other,4,limit))return false;
    r.d[2]=value;const std::uint32_t difference=value-limit;
    r.pc=difference==0?equal_pc:((difference&0x80000000U)?minus_pc:plus_pc);return true;
}
// SWAP D2; ADD.W D0,D2 (plus ADD.W D1,D2 when both); CMPI.W #limit,D2; BGT (greater) / BLT (less) 1aafc, else next_pc.
void ou5_edge(AnimationMachineState& r,bool both,std::int32_t limit,bool greater,std::uint32_t next_pc) {
    am_swap(r.d[2]);ou5_add_word(r.d[2],r.d[0]);if(both)ou5_add_word(r.d[2],r.d[1]);
    const std::int32_t value=ou5_signed_word(r.d[2]);
    r.pc=(greater?value>limit:value<limit)?0x1aafc:next_pc;
}
// Consumers of a known C (BCC clear_pc, else set_pc).
bool ou5_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects u05 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.W #id,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool ou5_palette(AnimationMachineContext& c,std::uint32_t id,std::uint32_t return_pc) {
    am_word(c.s.d[0],id);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.B 19(A6),14(A6); RTS.
bool ou5_finish(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!ou5_get(c,c.s.a[6],0x19,1,value) || !ou5_put(c,c.s.a[6],0x14,1,value))return false;
    return am_return(c);
}
// CMPI.W #kind,D0; BNE other_pc (else equal_pc).
void ou5_kind(AnimationMachineState& r,std::uint32_t kind,std::uint32_t equal_pc,std::uint32_t other_pc) {
    r.pc=(r.d[0]&65535U)==kind?equal_pc:other_pc;
}
}
// Objects F4 U05 (71 block starts): the C2 screen range test 1ab02 with fixed edges 200/100/140/0 (C returned: Clear from 1ab7a,
// Set from the U01 block 1aafc), the node callback b96c8 with its installed callback b971a, the C1 object palette reference c6a96
// (MOVEM.L D0-D1 around the c6bf6 lookup and the U02 8ebe call, then kind dependent extra 8ebe calls) and the lookup c6bf6 (WORD
// table c6e08 and LONG list table c6c24, list of key/addend WORD pairs ended by a negative key). The BMI after the BEQ at 1ab20/
// 1ab5c consumes the N of the same CMP.L and is bundled into 1ab14/1ab50. b9752 consumes the C returned by 1ab02; c6ad6/c6b20/c6b7a
// consume the C returned by the 497a6 boundary. The callee 497a6 and the installed callbacks b975e/b97c0 have no executor.
// Existing executors called: U01 1aafc, U02 8ebe, 8ff4, 49f8c, 49fc6, F3a 43e34, fade_card 2a24. b96e6 reads the LONG at the bank
// window 2001d0 and the LONG at 44 past it through the live bus (live bank_base); fixed data is read through the live bus too.
// The c6c0c list walk has no extra limit (block budget only).
bool animation_objects_u05_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 1ab02: MOVE.L (A0)+,D0; MOVE.L (A0)+,D1; BTST #1,15(A6); BEQ 1ab14.
    case 0x1ab02:
        if(!am_read(c,r.a[0],4,value))return false;r.d[0]=value;r.a[0]+=4U;
        if(!am_read(c,r.a[0],4,value))return false;r.d[1]=value;r.a[0]+=4U;
        if(!ou5_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&2U)?0x1ab10:0x1ab14;return true;
    case 0x1ab10:ou5_add_negate(r);r.pc=0x1ab14;return true;
    case 0x1ab14:return ou5_range_compare(c,0x46,0x4e,0x1ab3e,0x1ab32,0x1ab24);
    case 0x1ab24:ou5_edge(r,false,0x200,true,0x1ab2e);return true;  // SWAP D2; ADD.W D0,D2; CMPI.W #200,D2; BGT 1aafc.
    case 0x1ab2e:r.pc=0x1ab3e;return true;                          // BRA 1ab3e.
    case 0x1ab32:ou5_edge(r,true,0x100,false,0x1ab3e);return true;  // SWAP D2; ADD.W D0,D2; ADD.W D1,D2; CMPI.W #100,D2; BLT 1aafc.
    // SWAP D0; SWAP D1; BTST #0,15(A6); BEQ 1ab50.
    case 0x1ab3e:
        am_swap(r.d[0]);am_swap(r.d[1]);if(!ou5_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&1U)?0x1ab4c:0x1ab50;return true;
    case 0x1ab4c:ou5_add_negate(r);r.pc=0x1ab50;return true;
    case 0x1ab50:return ou5_range_compare(c,0x42,0x4a,0x1ab7a,0x1ab6e,0x1ab60);
    case 0x1ab60:ou5_edge(r,false,0x140,true,0x1ab6a);return true;  // SWAP D2; ADD.W D0,D2; CMPI.W #140,D2; BGT 1aafc.
    case 0x1ab6a:r.pc=0x1ab7a;return true;                          // BRA 1ab7a.
    case 0x1ab6e:ou5_edge(r,true,0,false,0x1ab7a);return true;      // SWAP D2; ADD.W D0,D2; ADD.W D1,D2; CMPI.W #0,D2; BLT 1aafc.
    case 0x1ab7a:r.carry=AnimationCarryClear;return am_return(c);   // ANDI.B #fe,CCR; RTS.

    // ---- b96c8 (callback): MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.W #73,D0; MOVE.W #11,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xb96c8:
        if(!ou5_put(c,r.a[6],0x68,2,0) || !ou5_put(c,r.a[6],0x1e,2,0))return false;
        am_word(r.d[0],0x73);am_word(r.d[1],0x11);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xb96e6);
    // LEA 26(A6),A0; MOVE.W #203,20(A6); MOVE.L 2001d0.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1;
    // MOVEA.L 44(A1),A1; JSR 49f8c.L.
    case 0xb96e6:
        r.a[0]=am_index(r.a[6],0x26);if(!ou5_put(c,r.a[6],0x20,2,0x203))return false;
        if(!am_read(c,OU5_BANK_POINTER,4,value) || !ou5_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
        if(!ou5_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
        if(!ou5_get(c,r.a[1],0x44,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,0xb970e);
    // MOVE.W #78,78(A6); MOVE.L #b971a,(A6) (then the callback b971a).
    case 0xb970e:if(!ou5_put(c,r.a[6],0x78,2,0x78) || !am_write(c,r.a[6],4,0xb971a))return false;r.pc=0xb971a;return true;
    case 0xb971a:return am_call(c,0x43e34,0xb9720); // JSR 43e34.L (callback entry).
    case 0xb9720:return am_call(c,0x49fc6,0xb9726); // JSR 49fc6.L.
    // SUBQ.W #1,78(A6); BNE b9746.
    case 0xb9726:
        if(!ou5_get(c,r.a[6],0x78,2,value))return false;value=(value-1U)&65535U;
        if(!ou5_put(c,r.a[6],0x78,2,value))return false;r.pc=value?0xb9746:0xb972e;return true;
    // TST.W 76(A6); BNE b9740.
    case 0xb972e:if(!ou5_get(c,r.a[6],0x76,2,value))return false;r.pc=(value&65535U)?0xb9740:0xb9736;return true;
    case 0xb9736:if(!am_write(c,r.a[6],4,0xb975e))return false;r.pc=0xb9746;return true; // MOVE.L #b975e,(A6); BRA b9746.
    case 0xb9740:if(!am_write(c,r.a[6],4,0xb97c0))return false;r.pc=0xb9746;return true; // MOVE.L #b97c0,(A6).
    case 0xb9746:r.a[0]=OU5_RANGE_RECORD;return am_call(c,0x1ab02,0xb9752); // LEA ba3d6.L,A0; JSR 1ab02.L.
    case 0xb9752:return ou5_carry(c,0xb975c,0xb9756); // BCC b975c.
    case 0xb9756:r.pc=0x2a24;return true;              // JMP 2a24.L.
    case 0xb975c:case 0xc6bf4:case 0xc6c12:return am_return(c); // RTS.

    // ---- c6a96: MOVEM.L D0-D1,-(A7) (D1 at A7-4, D0 at A7-8); BSR c6bf6.
    case 0xc6a96:
        if(!am_push(c,4,r.d[1]) || !am_push(c,4,r.d[0]))return false;return am_call(c,0xc6bf6,0xc6a9e);
    case 0xc6a9e:am_byte(r.d[1],r.d[2]&255U);return am_call(c,0x8ebe,0xc6aa6); // MOVE.B D2,D1; JSR 8ebe.L.
    // MOVEM.L (A7)+,D0-D1; CMPI.W #33,D0; BNE c6ac8.
    case 0xc6aa6:if(!am_pop(c,4,r.d[0]) || !am_pop(c,4,r.d[1]))return false;ou5_kind(r,0x33,0xc6ab2,0xc6ac8);return true;
    case 0xc6ab2:return ou5_palette(c,0xc4b,0xc6ac0);
    case 0xc6ac0:case 0xc6b0a:case 0xc6b46:case 0xc6b64:case 0xc6b92:case 0xc6bb0:case 0xc6bce:case 0xc6bec:return ou5_finish(c);
    case 0xc6ac8:ou5_kind(r,0x34,0xc6ad0,0xc6b12);return true;
    case 0xc6ad0:return am_call(c,0x497a6,0xc6ad6); // JSR 497a6.L (boundary without an executor).
    case 0xc6ad6:return ou5_carry(c,0xc6aee,0xc6ada); // BCC c6aee.
    case 0xc6ada:return am_call(c,0x8ff4,0xc6ae0);    // JSR 8ff4.L.
    case 0xc6ae0:return ou5_palette(c,0xc54,0xc6aee);
    case 0xc6aee:return ou5_palette(c,0xc50,0xc6afc);
    case 0xc6afc:return ou5_palette(c,0xc52,0xc6b0a);
    case 0xc6b12:ou5_kind(r,0x60,0xc6b1a,0xc6b4e);return true;
    case 0xc6b1a:return am_call(c,0x497a6,0xc6b20); // JSR 497a6.L (boundary).
    case 0xc6b20:return ou5_carry(c,0xc6b38,0xc6b24); // BCC c6b38.
    case 0xc6b24:return am_call(c,0x8ff4,0xc6b2a);
    case 0xc6b2a:return ou5_palette(c,0xc54,0xc6b38);
    case 0xc6b38:return ou5_palette(c,0xc48,0xc6b46);
    case 0xc6b4e:ou5_kind(r,0x47,0xc6b56,0xc6b6c);return true;
    case 0xc6b56:return ou5_palette(c,0xc76,0xc6b64);
    case 0xc6b6c:ou5_kind(r,0x5d,0xc6b74,0xc6b9a);return true;
    case 0xc6b74:return am_call(c,0x497a6,0xc6b7a); // JSR 497a6.L (boundary).
    case 0xc6b7a:return ou5_carry(c,0xc6b92,0xc6b7e); // BCC c6b92.
    case 0xc6b7e:return am_call(c,0x8ff4,0xc6b84);
    case 0xc6b84:return ou5_palette(c,0xc4d,0xc6b92);
    case 0xc6b9a:ou5_kind(r,0x4f,0xc6ba2,0xc6bb8);return true;
    case 0xc6ba2:return ou5_palette(c,0xc88,0xc6bb0);
    case 0xc6bb8:ou5_kind(r,0x59,0xc6bc0,0xc6bd6);return true;
    case 0xc6bc0:return ou5_palette(c,0xc39,0xc6bce);
    case 0xc6bd6:ou5_kind(r,0x5c,0xc6bde,0xc6bf4);return true;
    case 0xc6bde:return ou5_palette(c,0xc3f,0xc6bec);

    // ---- c6bf6: MOVE.W D0,D3; ADD.W D3,D3; LEA c6e08(PC),A1; ADDA.W D3,A1; MOVE.W (A1),D0; ADD.W D3,D3; LEA c6c24(PC),A1;
    // MOVEA.L (A1,D3.W),A1.
    case 0xc6bf6:
        am_word(r.d[3],r.d[0]);ou5_add_word(r.d[3],r.d[3]);r.a[1]=am_index(OU5_BASE_TABLE,r.d[3]);
        if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[0],value);ou5_add_word(r.d[3],r.d[3]);r.a[1]=OU5_LIST_TABLE;
        if(!am_read(c,am_index(r.a[1],r.d[3]),4,value))return false;r.a[1]=value;r.pc=0xc6c0c;return true;
    // MOVE.W (A1),D3; BPL c6c14.
    case 0xc6c0c:if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[3],value);r.pc=(value&0x8000U)?0xc6c12:0xc6c14;return true;
    case 0xc6c14:r.pc=(r.d[1]&65535U)==(r.d[3]&65535U)?0xc6c1e:0xc6c1a;return true; // CMP.W D3,D1; BEQ c6c1e.
    case 0xc6c1a:r.a[1]+=4U;r.pc=0xc6c0c;return true;                                // ADDQ.L #4,A1; BRA c6c0c.
    // ADD.W 2(A1),D0; RTS.
    case 0xc6c1e:if(!ou5_get(c,r.a[1],2,2,value))return false;ou5_add_word(r.d[0],value);return am_return(c);
    default:return am_error(c,"unsupported animation objects u05 PC");
    }
}
}
