#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OU19_BANK_A=0x2001a8;         // MOVE.L 2001a8.L,22(A6) / MOVEA.L 2001a8.L,A1 (8e(A6) = 0; banked window LONG, live bus).
const std::uint32_t OU19_BANK_B=0x2001ac;         // MOVE.L 2001ac.L,22(A6) / MOVEA.L 2001ac.L,A1 (8e(A6) != 0).
const std::uint32_t OU19_BANK_C0=0x2001c0;        // d824a d832c (80(A6) = 0).
const std::uint32_t OU19_BANK_CC=0x2001cc;        // d8276 d8358 (80(A6) != 0).
const std::uint32_t OU19_BANK_D4=0x2001d4;        // ba7aa.
const std::uint32_t OU19_PALETTE=0xb7f18;         // LEA b7f18(PC),A0 (b7cae; fixed ROM WORD table).
const std::uint32_t OU19_D8_PALETTE=0xd841a;      // LEA d841a(PC),A0 (d8204; fixed ROM WORD table).
bool ou19_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou19_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool ou19_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u19 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6) then continue at next_pc.
bool ou19_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// BSET/BCLR.B #bit,d16(An) (read-modify-write BYTE; Z only).
bool ou19_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!ou19_get(c,base,displacement,1,value))return false;
    value=set?(value|(1U<<bit)):(value&~(1U<<bit));return ou19_put(c,base,displacement,1,value&255U);
}
// BTST.B #bit,d16(An); branch to zero_pc when the bit is 0.
bool ou19_test(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,std::uint32_t zero_pc,std::uint32_t one_pc) {
    std::uint32_t value=0;if(!ou19_get(c,base,displacement,1,value))return false;
    c.s.pc=(value&(1U<<bit))==0U?zero_pc:one_pc;return true;
}
// MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W other_pc.
bool ou19_variant(AnimationMachineContext& c,std::uint32_t other_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!ou19_get(c,c.s.a[6],0x8e,2,value))return false;
    am_word(c.s.d[0],value);c.s.pc=(value&65535U)!=0U?other_pc:next_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVEA.L #table,A1; ADD.W D0,D0 (twice); MOVE.L (A1,D0.W),D0;
// MOVEA.L bank.L,A1; ADD.W D0,D0 (twice); MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c.L (live bus; WORD index sign-extended).
bool ou19_table_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t bank,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!ou19_put(c,r.a[6],0x20,2,k) || !am_read(c,bank,4,value) || !ou19_put(c,r.a[6],0x22,4,value))return false;
    r.a[1]=table;am_word(r.d[0],(r.d[0]<<2)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.d[0]=value;
    if(!am_read(c,bank,4,value))return false;r.a[1]=value;am_word(r.d[0],(r.d[0]<<2)&65535U);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;
    am_word(r.d[0],0x100);return am_call(c,0x49f8c,return_pc);
}
// LEA 26(A6),A0; MOVE.W #k,20(A6); MOVE.L bank.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1;
// JSR 49f8c.L (the bank LONG and the LONG at its value + d16 through the live bus).
bool ou19_animation(AnimationMachineContext& c,std::uint32_t k,std::uint32_t bank,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!ou19_put(c,r.a[6],0x20,2,k) || !am_read(c,bank,4,value) || !ou19_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!ou19_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!ou19_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// MOVE.L #a,96(A6); MOVE.L #b,98(A6).
bool ou19_offsets(AnimationMachineContext& c,std::uint32_t a,std::uint32_t b) {
    return ou19_put(c,c.s.a[6],0x96,4,a) && ou19_put(c,c.s.a[6],0x98,4,b);
}
// MOVE.W #k,D0; MOVE.B #b,D1; JSR 8ebe.L.
bool ou19_palette(AnimationMachineContext& c,std::uint32_t k,std::uint32_t b,std::uint32_t return_pc) {
    am_word(c.s.d[0],k);am_byte(c.s.d[1],b);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W d16a(A6),D0 (or D0 as is); LEA table(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L.
bool ou19_table_palette(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=table;am_word(r.d[0],(r.d[0]<<1)&65535U);
    if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[0],value);am_byte(r.d[1],0);
    return am_call(c,0x8ebe,return_pc);
}
// SUBQ.W #1,d16(A6): returns whether a borrow happened (the WORD was 0).
bool ou19_count(AnimationMachineContext& c,std::uint32_t displacement,bool& borrow) {
    std::uint32_t value=0;if(!ou19_get(c,c.s.a[6],displacement,2,value) || !ou19_put(c,c.s.a[6],displacement,2,(value-1U)&65535U))return false;
    borrow=(value&65535U)==0U;return true;
}
// MOVE.W #v,68(A6); MOVE.W #v,1e(A6).
bool ou19_height(AnimationMachineContext& c,std::uint32_t v) {
    return ou19_put(c,c.s.a[6],0x68,2,v) && ou19_put(c,c.s.a[6],0x1e,2,v);
}
}
// Objects F4 U19 (174 block starts): 484e2 (C = BYTE 5683 bit 0), the object table entries b6300/b6338/b6362 (8e = 0/1, U18 b7bc2)
// with the state body b6370 and its installed callbacks b6406 b6422 b64a8, the state b68ba with its installed callbacks b68be b690a
// b69b6 b6a2a b6ac8 b6aee b6b7c (banked LONGs 2001a8/2001ac and the LONG at their value + 4 * fixed ROM table LONG, U18 boundaries
// b7cfa b7e06 b7e5c b76bc b76d2 4be2c, U20 boundary 492d0, U19b installs b7100/b749c written only), the target pick b7b4c (49392,
// boundary b7b30, one stack LONG; C produced by b7bb6/b7bbc), the palette helper b7c9e (WORD table b7f18), the objects ba78c (bank
// 2001d4 + 38, 1ab02 C), d6d4a, d81cc/d81e8 (WORD table d841a, banks 2001c0/2001cc, 1aa7e and 49fc6 C, boundaries e9112 d83c0) and
// dbefe (BYTE 100012, 76 countdown, child 4841a). Known carry producers: 484ec b7bb6 (Set), 484f2 b7bbc (Clear). No port write.
bool animation_objects_u19_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;bool borrow=false;
    switch(r.pc) {
    // ---- 484e2: BTST.B #0,5683(A5); BEQ.W 484f2; ORI.B #1,CCR; RTS / ANDI.B #fe,CCR; RTS.
    case 0x484e2:return ou19_test(c,r.a[5],0x5683,0,0x484f2,0x484ec);
    case 0x484ec:case 0xb7bb6:r.carry=AnimationCarrySet;return am_return(c);
    case 0x484f2:case 0xb7bbc:r.carry=AnimationCarryClear;return am_return(c);

    // ---- object table entries: MOVE.W #v,8e(A6); BSR.W b7bc2 (U18); BRA.W body.
    case 0xb6300:if(!ou19_put(c,r.a[6],0x8e,2,0))return false;return am_call(c,0xb7bc2,0xb630a);
    case 0xb6338:if(!ou19_put(c,r.a[6],0x8e,2,1))return false;return am_call(c,0xb7bc2,0xb6342);
    case 0xb6362:if(!ou19_put(c,r.a[6],0x8e,2,1))return false;return am_call(c,0xb7bc2,0xb636c);
    case 0xb630a:case 0xb6342:r.pc=0xb6370;return true;
    case 0xb636c:r.pc=0xb68ba;return true;

    // ---- state b6370.
    case 0xb6370:return ou19_variant(c,0xb63b8,0xb637c);
    case 0xb637c:return ou19_table_animation(c,0x1b3,OU19_BANK_A,0xb7f1c,0xb63b4);
    case 0xb63b4:r.pc=0xb63f0;return true;                                  // BRA.W b63f0.
    case 0xb63b8:return ou19_table_animation(c,0x1bb,OU19_BANK_B,0xb7f1c,0xb63f0);
    // MOVE.L #fffffff6,96(A6); MOVE.L #10,98(A6); MOVE.L #b6406,(A6).
    case 0xb63f0:if(!ou19_offsets(c,0xfffffff6U,0x10))return false;return ou19_install(c,0xb6406,0xb6406);
    case 0xb6406:return am_call(c,0xb7cfa,0xb640a);                         // (installed callback) JSR b7cfa(PC) (U18).
    case 0xb640a:return am_call(c,0x49fc6,0xb6410);                         // JSR 49fc6.L.
    case 0xb6410:return am_call(c,0xb7e5c,0xb6414);                         // JSR b7e5c(PC) (U18, C returned).
    case 0xb6414:return ou19_consume(c,false,0xb641e,0xb6418);              // BCC.W b641e (C returned by b7e5c).
    case 0xb6418:return ou19_install(c,0xb6422,0xb641e);                    // MOVE.L #b6422,(A6).
    case 0xb641e:case 0xb6502:r.pc=0xb76d2;return true;                     // BRA.W b76d2 (U18).
    case 0xb6422:return ou19_variant(c,0xb646a,0xb642e);                    // (installed callback)
    case 0xb642e:return ou19_table_animation(c,0x1b3,OU19_BANK_A,0xb7f24,0xb6466);
    case 0xb6466:r.pc=0xb64a2;return true;                                  // BRA.W b64a2.
    case 0xb646a:return ou19_table_animation(c,0x1bb,OU19_BANK_B,0xb7f24,0xb64a2);
    case 0xb64a2:return ou19_install(c,0xb64a8,0xb64a8);                    // MOVE.L #b64a8,(A6).
    case 0xb64a8:return am_call(c,0xb7cfa,0xb64ac);                         // (installed callback) JSR b7cfa(PC).
    case 0xb64ac:return am_call(c,0x49fc6,0xb64b2);                         // JSR 49fc6.L.
    case 0xb64b2:return ou19_consume(c,false,0xb6502,0xb64b6);              // BCC.W b6502 (C returned by 49fc6).
    // MOVE.L #a,96(A6); MOVE.L #b,98(A6); LEA 26(A6),A0; JSR b7e06(PC) (U18).
    case 0xb64b6:if(!ou19_offsets(c,0xfffffff4U,0x8))return false;r.a[0]=am_index(r.a[6],0x26);return am_call(c,0xb7e06,0xb64ce);
    case 0xb64ce:if(!ou19_offsets(c,0xc,0x10))return false;r.a[0]=am_index(r.a[6],0x26);return am_call(c,0xb7e06,0xb64e6);
    case 0xb64e6:if(!ou19_offsets(c,0xfffffff6U,0x10))return false;return am_call(c,0x496c2,0xb64fc); // ...; JSR 496c2.L.
    case 0xb64fc:return ou19_install(c,0xb68ba,0xb6502);                    // MOVE.L #b68ba,(A6).

    // ---- state b68ba.
    case 0xb68ba:return am_call(c,0xb7c9e,0xb68be);                         // JSR b7c9e(PC).
    // b68be (installed callback): CLR.B 5e(A6); BCLR.B #7,61(A6); MOVE.W #f,84(A6); CMPI.W #1,76(A6); BNE.W b68e4.
    case 0xb68be:
        if(!ou19_put(c,r.a[6],0x5e,1,0) || !ou19_bit(c,r.a[6],0x61,7,false) || !ou19_put(c,r.a[6],0x84,2,0xf) ||
           !ou19_get(c,r.a[6],0x76,2,value))return false;
        r.pc=(value&65535U)!=1U?0xb68e4:0xb68d8;return true;
    // BCLR/BSET.B #0,15(A6); MOVE.W #7fff,84(A6).
    case 0xb68d8:if(!ou19_bit(c,r.a[6],0x15,0,false) || !ou19_put(c,r.a[6],0x84,2,0x7fff))return false;r.pc=0xb68e4;return true;
    case 0xb68e4:if(!ou19_get(c,r.a[6],0x76,2,value))return false;r.pc=(value&65535U)!=2U?0xb68fa:0xb68ee;return true; // CMPI.W #2,76(A6); BNE.W b68fa.
    case 0xb68ee:if(!ou19_bit(c,r.a[6],0x15,0,true) || !ou19_put(c,r.a[6],0x84,2,0x7fff))return false;r.pc=0xb68fa;return true;
    case 0xb68fa:return am_call(c,0x4be06,0xb6900);                         // JSR 4be06.L.
    case 0xb6900:return ou19_test(c,r.a[6],0x15,7,0xb6a32,0xb690a);         // BTST.B #7,15(A6); BEQ.W b6a32.
    case 0xb690a:return ou19_variant(c,0xb6952,0xb6916);                    // (installed callback)
    case 0xb6916:return ou19_table_animation(c,0x1b3,OU19_BANK_A,0xb7f6c,0xb694e);
    case 0xb694e:r.pc=0xb698a;return true;                                  // BRA.W b698a.
    case 0xb6952:return ou19_table_animation(c,0x1bb,OU19_BANK_B,0xb7f6c,0xb698a);
    // MOVE.L #fffffffc,96(A6); MOVE.L #1a,98(A6); MOVE.L #18000,D0; BTST.B #0,15(A6); BNE.W b69ac.
    case 0xb698a:if(!ou19_offsets(c,0xfffffffcU,0x1a))return false;r.d[0]=0x18000;return ou19_test(c,r.a[6],0x15,0,0xb69aa,0xb69ac);
    case 0xb69aa:r.d[0]=(0U-r.d[0])&0xffffffffU;r.pc=0xb69ac;return true;    // NEG.L D0.
    case 0xb69ac:if(!ou19_put(c,r.a[6],0x64,4,r.d[0]))return false;return ou19_install(c,0xb69b6,0xb69b6); // MOVE.L D0,64(A6); MOVE.L #b69b6,(A6).
    case 0xb69b6:return am_call(c,0xb7cfa,0xb69ba);                         // (installed callback) BSR.W b7cfa (U18).
    case 0xb69ba:return ou19_test(c,r.a[6],0x15,7,0xb69c4,0xb69ce);         // BTST.B #7,15(A6); BNE.W b69ce.
    case 0xb69c4:return ou19_install(c,0xb6a2a,0xb69f4);                    // MOVE.L #b6a2a,(A6); BRA.W b69f4.
    case 0xb69ce:return ou19_test(c,r.a[6],0x61,0,0xb69de,0xb69d8);         // BTST.B #0,61(A6); BEQ.W b69de.
    case 0xb69d8:return ou19_install(c,0xb6aee,0xb69de);                    // MOVE.L #b6aee,(A6).
    case 0xb69de:if(!ou19_get(c,r.a[6],0x76,1,value))return false;r.pc=(value&255U)!=0U?0xb69f4:0xb69e6;return true; // TST.B 76(A6); BNE.W b69f4.
    case 0xb69e6:if(!ou19_count(c,0x84,borrow))return false;r.pc=borrow?0xb69ee:0xb69f4;return true; // SUBQ.W #1,84(A6); BCC.W b69f4.
    case 0xb69ee:return ou19_install(c,0xb6aee,0xb69f4);                    // MOVE.L #b6aee,(A6).
    case 0xb69f4:return am_call(c,0x6f1c2,0xb69fa);                         // JSR 6f1c2.L.
    case 0xb69fa:r.pc=(r.d[0]&0x8000U)?0xb6a20:0xb6a00;return true;          // TST.W D0; BMI.W b6a20.
    // MOVE.B D0,9e(A6); BTST.B #0,D1; BEQ.W b6a12.
    case 0xb6a00:if(!ou19_put(c,r.a[6],0x9e,1,r.d[0]&255U))return false;r.pc=(r.d[1]&1U)==0U?0xb6a12:0xb6a0c;return true;
    case 0xb6a0c:return ou19_install(c,0xb7100,0xb6a12);                    // MOVE.L #b7100,(A6) (U19b, written only).
    case 0xb6a12:r.pc=(r.d[1]&2U)==0U?0xb6a20:0xb6a1a;return true;           // BTST.B #1,D1; BEQ.W b6a20.
    case 0xb6a1a:return ou19_install(c,0xb749c,0xb6a20);                    // MOVE.L #b749c,(A6) (U19b, written only).
    case 0xb6a20:return am_call(c,0x49fc6,0xb6a26);                         // JSR 49fc6.L.
    case 0xb6a26:case 0xb6aea:r.pc=0xb76bc;return true;                     // BRA.W b76bc (U18).
    // b6a2a (installed callback): CLR.L 36(A6); CLR.L 3a(A6).
    case 0xb6a2a:if(!ou19_put(c,r.a[6],0x36,4,0) || !ou19_put(c,r.a[6],0x3a,4,0))return false;r.pc=0xb6a32;return true;
    case 0xb6a32:return ou19_variant(c,0xb6a7a,0xb6a3e);
    case 0xb6a3e:return ou19_table_animation(c,0x1b3,OU19_BANK_A,0xb7f3c,0xb6a76);
    case 0xb6a76:r.pc=0xb6ab2;return true;                                  // BRA.W b6ab2.
    case 0xb6a7a:return ou19_table_animation(c,0x1bb,OU19_BANK_B,0xb7f3c,0xb6ab2);
    // MOVE.L #fffffff6,96(A6); MOVE.L #18,98(A6); MOVE.L #b6ac8,(A6).
    case 0xb6ab2:if(!ou19_offsets(c,0xfffffff6U,0x18))return false;return ou19_install(c,0xb6ac8,0xb6ac8);
    case 0xb6ac8:return am_call(c,0x4be2c,0xb6ace);                         // (installed callback) JSR 4be2c.L (U18).
    case 0xb6ace:return am_call(c,0x492c8,0xb6ad4);                         // JSR 492c8.L.
    case 0xb6ad4:return ou19_test(c,r.a[6],0x15,7,0xb6ae4,0xb6ade);         // BTST.B #7,15(A6); BEQ.W b6ae4.
    case 0xb6ade:return ou19_install(c,0xb690a,0xb6ae4);                    // MOVE.L #b690a,(A6).
    case 0xb6ae4:return am_call(c,0x49fc6,0xb6aea);                         // JSR 49fc6.L.
    // b6aee (installed callback): CLR.L 64(A6); CLR.L 36(A6); MOVE.W 8e(A6),D0; CMPI.W #0,D0; BNE.W b6b3e.
    case 0xb6aee:if(!ou19_put(c,r.a[6],0x64,4,0) || !ou19_put(c,r.a[6],0x36,4,0))return false;return ou19_variant(c,0xb6b3e,0xb6b02);
    case 0xb6b02:return ou19_table_animation(c,0x1b3,OU19_BANK_A,0xb7f74,0xb6b3a);
    case 0xb6b3a:r.pc=0xb6b76;return true;                                  // BRA.W b6b76.
    case 0xb6b3e:return ou19_table_animation(c,0x1bb,OU19_BANK_B,0xb7f74,0xb6b76);
    case 0xb6b76:return ou19_install(c,0xb6b7c,0xb6b7c);                    // MOVE.L #b6b7c,(A6).
    case 0xb6b7c:return am_call(c,0xb7cfa,0xb6b80);                         // (installed callback) JSR b7cfa(PC).
    case 0xb6b80:return am_call(c,0x49fc6,0xb6b86);                         // JSR 49fc6.L.
    case 0xb6b86:r.a[0]=am_index(r.a[6],0x26);return am_call(c,0x492d0,0xb6b90); // LEA 26(A6),A0; JSR 492d0.L (U20 boundary).
    // MOVE.W #1e,84(A6); MOVE.L #b690a,(A6); BRA.W b76bc.
    case 0xb6b90:if(!ou19_put(c,r.a[6],0x84,2,0x1e))return false;return ou19_install(c,0xb690a,0xb76bc);

    // ---- b7b4c: target pick.
    case 0xb7b4c:return am_call(c,0x484e2,0xb7b52);                         // JSR 484e2.L.
    case 0xb7b52:return ou19_consume(c,true,0xb7bbc,0xb7b56);               // BCS.W b7bbc (C returned by 484e2).
    // MOVE.L #ffffffff,-(A7); MOVEQ #0,D0; JSR 49392.L.
    case 0xb7b56:if(!am_push(c,4,0xffffffffU))return false;r.d[0]=0;return am_call(c,0x49392,0xb7b64);
    case 0xb7b64:return ou19_consume(c,false,0xb7b70,0xb7b68);              // BCC.W b7b70 (C returned by 49392).
    case 0xb7b68:return am_call(c,0xb7b30,0xb7b6a);                         // BSR.B b7b30 (boundary).
    case 0xb7b6a:return ou19_consume(c,false,0xb7b70,0xb7b6e);              // BCC.W b7b70 (C returned by b7b30).
    case 0xb7b6e:if(!am_write(c,r.a[7],4,r.a[0]))return false;r.pc=0xb7b70;return true; // MOVE.L A0,(A7).
    case 0xb7b70:r.d[0]=1;return am_call(c,0x49392,0xb7b78);                 // MOVEQ #1,D0; JSR 49392.L.
    case 0xb7b78:return ou19_consume(c,false,0xb7b9a,0xb7b7c);              // BCC.W b7b9a.
    case 0xb7b7c:return am_call(c,0xb7b30,0xb7b7e);                         // BSR.B b7b30.
    case 0xb7b7e:return ou19_consume(c,false,0xb7b9a,0xb7b82);              // BCC.W b7b9a.
    case 0xb7b82:if(!am_read(c,r.a[7],4,value))return false;r.d[0]=value;r.pc=(value&0x80000000U)?0xb7b98:0xb7b88;return true; // MOVE.L (A7),D0; BMI.W b7b98.
    // MOVEA.L D0,A2; MOVE.W 42(A0),D0; CMP.W 42(A2),D0; BCC.W b7b98 (unsigned WORD >=).
    case 0xb7b88:
        r.a[2]=r.d[0];if(!ou19_get(c,r.a[0],0x42,2,value) || !ou19_get(c,r.a[2],0x42,2,other))return false;am_word(r.d[0],value);
        r.pc=(value&65535U)>=(other&65535U)?0xb7b98:0xb7b96;return true;
    case 0xb7b96:r.a[0]=r.a[2];r.pc=0xb7b98;return true;                    // MOVEA.L A2,A0.
    case 0xb7b98:if(!am_write(c,r.a[7],4,r.a[0]))return false;r.pc=0xb7b9a;return true; // MOVE.L A0,(A7).
    // MOVEQ #0,D0; MOVE.B #1,D2; MOVE.L (A7)+,D1; BMI.W b7bbc.
    case 0xb7b9a:r.d[0]=0;am_byte(r.d[2],1);if(!am_pop(c,4,value))return false;r.d[1]=value;r.pc=(value&0x80000000U)?0xb7bbc:0xb7ba6;return true;
    case 0xb7ba6:r.pc=r.d[1]==0x100cb8U?0xb7bb6:0xb7bb0;return true;          // CMPI.L #100cb8,D1; BEQ.W b7bb6.
    case 0xb7bb0:r.d[0]=1;am_byte(r.d[2],2);r.pc=0xb7bb6;return true;         // MOVEQ #1,D0; MOVE.B #2,D2.

    // ---- b7c9e: palette helper.
    case 0xb7c9e:return am_call(c,0x8ff4,0xb7ca4);                          // JSR 8ff4.L.
    case 0xb7ca4:return ou19_test(c,r.a[6],0x9f,1,0xb7cae,0xb7cca);         // BTST.B #1,9f(A6); BNE.W b7cca.
    // MOVE.W 8e(A6),D0; LEA b7f18(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xb7cae:if(!ou19_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],value);return ou19_table_palette(c,OU19_PALETTE,0xb7cc6);
    case 0xb7cc6:r.pc=0xb7ce4;return true;                                  // BRA.W b7ce4.
    case 0xb7cca:return ou19_palette(c,0xac1,1,0xb7cd8);                    // MOVE.W #ac1,D0; MOVE.B #1,D1; JSR 8ebe.L.
    case 0xb7cd8:if(!ou19_put(c,r.a[6],0x90,2,0xac2) || !ou19_bit(c,r.a[6],0x9f,0,true))return false;r.pc=0xb7ce4;return true; // MOVE.W #ac2,90(A6); BSET.B #0,9f(A6).
    case 0xb7ce4:return ou19_palette(c,0xd88,0,0xb7cf2);                    // MOVE.W #d88,D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xb7cf2:if(!ou19_get(c,r.a[6],0x19,1,value) || !ou19_put(c,r.a[6],0x14,1,value))return false;return am_return(c); // MOVE.B 19(A6),14(A6); RTS.

    // ---- ba78c (callback): MOVE.W #8835,68(A6); MOVE.W #8835,1e(A6); MOVE.W #74,D0; MOVE.W #e,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xba78c:if(!ou19_height(c,0x8835))return false;am_word(r.d[0],0x74);am_word(r.d[1],0xe);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xba7aa);
    case 0xba7aa:return ou19_animation(c,0x20b,OU19_BANK_D4,0x38,0xba7d2);    // animation 20b, bank LONG 2001d4, + 38.
    case 0xba7d2:return ou19_install(c,0xba7d8,0xba7d8);                    // MOVE.L #ba7d8,(A6).
    case 0xba7d8:return am_call(c,0x43e34,0xba7de);                         // (installed callback) JSR 43e34.L.
    case 0xba7de:return am_call(c,0x492c8,0xba7e4);                         // JSR 492c8.L.
    case 0xba7e4:return am_call(c,0x49fc6,0xba7ea);                         // JSR 49fc6.L.
    case 0xba7ea:r.a[0]=0xba784;return am_call(c,0x1ab02,0xba7f4);           // LEA ba784(PC),A0; JSR 1ab02.L.
    case 0xba7f4:return ou19_consume(c,false,0xba7fe,0xba7f8);              // BCC.W ba7fe (C returned by 1ab02).
    case 0xba7f8:case 0xd8316:case 0xd83b8:case 0xdbf18:case 0xdbf44:r.pc=0x2a00;return true; // JMP 2a00.L.
    // RTS (keeps C).
    case 0xba7fe:case 0xd831c:case 0xd83be:case 0xdbf32:return am_return(c);

    // ---- d6d4a (callback): MOVE.W 76/78/7a/7c(A6),5426/5428/542a/542c(A5); JMP 2a00.L.
    case 0xd6d4a:
        for(std::uint32_t k=0;k<8U;k+=2U){if(!ou19_get(c,r.a[6],0x76U+k,2,value) || !ou19_put(c,r.a[5],0x5426U+k,2,value))return false;}
        r.pc=0x2a00;return true;

    // ---- d81cc / d81e8 (callbacks): MOVE.W #0,82(A6); MOVE.W #4/#6,84(A6); MOVE.L #d841e,86(A6); MOVE.W #0/#1,D0; BRA.W d8204.
    case 0xd81cc:case 0xd81e8:
        if(!ou19_put(c,r.a[6],0x82,2,0) || !ou19_put(c,r.a[6],0x84,2,r.pc==0xd81ccU?4U:6U) || !ou19_put(c,r.a[6],0x86,4,0xd841e))return false;
        am_word(r.d[0],r.pc==0xd81ccU?0U:1U);r.pc=0xd8204;return true;
    // MOVE.W D0,80(A6); MOVE.W 80(A6),D0; LEA d841a(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L.
    case 0xd8204:
        if(!ou19_put(c,r.a[6],0x80,2,r.d[0]&65535U) || !ou19_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);
        return ou19_table_palette(c,OU19_D8_PALETTE,0xd8220);
    // MOVE.W #880c,68(A6); MOVE.W #880c,1e(A6); LEA cbce8.L,A0; JSR 490ba.L.
    case 0xd8220:if(!ou19_height(c,0x880c))return false;r.a[0]=0xcbce8;return am_call(c,0x490ba,0xd8238);
    case 0xd8238:if(!ou19_put(c,r.a[6],0x54,2,r.d[0]&65535U))return false;return am_call(c,0x4c0ac,0xd8242); // MOVE.W D0,54(A6); JSR 4c0ac.L.
    case 0xd8242:if(!ou19_get(c,r.a[6],0x80,2,value))return false;r.pc=(value&65535U)!=0U?0xd8276:0xd824a;return true; // TST.W 80(A6); BNE.W d8276.
    case 0xd824a:return ou19_animation(c,0x1e3,OU19_BANK_C0,0x4,0xd8272);     // animation 1e3, bank LONG 2001c0, + 4.
    case 0xd8272:r.pc=0xd829e;return true;                                  // BRA.W d829e.
    case 0xd8276:return ou19_animation(c,0x1fb,OU19_BANK_CC,0x7c,0xd829e);    // animation 1fb, bank LONG 2001cc, + 7c.
    case 0xd829e:return am_call(c,0x496c2,0xd82a4);                         // JSR 496c2.L.
    case 0xd82a4:return ou19_install(c,0xd82aa,0xd82aa);                    // MOVE.L #d82aa,(A6).
    case 0xd82aa:return ou19_test(c,r.a[6],0x15,7,0xd82be,0xd82b4);         // (installed callback) BTST.B #7,15(A6); BEQ.W d82be.
    case 0xd82b4:return am_call(c,0x4be06,0xd82ba);                         // JSR 4be06.L.
    case 0xd82ba:r.pc=0xd82c4;return true;                                  // BRA.W d82c4.
    case 0xd82be:return am_call(c,0x4be2c,0xd82c4);                         // JSR 4be2c.L (U18).
    case 0xd82c4:return am_call(c,0x49fc6,0xd82ca);                         // JSR 49fc6.L.
    case 0xd82ca:return am_call(c,0x4b54e,0xd82d0);                         // JSR 4b54e.L.
    // CLR.B 5e(A6); BTST.B #7,61(A6); BEQ.W d82e4.
    case 0xd82d0:if(!ou19_put(c,r.a[6],0x5e,1,0))return false;return ou19_test(c,r.a[6],0x61,7,0xd82e4,0xd82de);
    case 0xd82de:return ou19_install(c,0xd831e,0xd82e4);                    // MOVE.L #d831e,(A6).
    // MOVEA.L 86(A6),A0; MOVE.W 82(A6),D0; MOVE.W 84(A6),D1; MOVE.W 42(A6),D7; SUBI.W #60,D7; CMPI.W #80,D7; BCS.W d8302.
    case 0xd82e4:
        if(!ou19_get(c,r.a[6],0x86,4,value))return false;r.a[0]=value;
        if(!ou19_get(c,r.a[6],0x82,2,value))return false;am_word(r.d[0],value);
        if(!ou19_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[1],value);
        if(!ou19_get(c,r.a[6],0x42,2,value))return false;am_word(r.d[7],(value-0x60U)&65535U);
        r.pc=(r.d[7]&65535U)<0x80U?0xd8302:0xd8300;return true;
    case 0xd8300:r.d[0]=0;r.pc=0xd8302;return true;                         // MOVEQ #0,D0.
    case 0xd8302:return am_call(c,0x47070,0xd8308);                         // JSR 47070.L.
    case 0xd8308:r.a[0]=0xd8440;return am_call(c,0x1aa7e,0xd8312);           // LEA d8440(PC),A0; JSR 1aa7e.L.
    case 0xd8312:return ou19_consume(c,false,0xd831c,0xd8316);              // BCC.W d831c (C returned by 1aa7e).
    case 0xd831e:return am_call(c,0xe9112,0xd8324);                         // (installed callback) JSR e9112.L (boundary).
    case 0xd8324:if(!ou19_get(c,r.a[6],0x80,2,value))return false;r.pc=(value&65535U)!=0U?0xd8358:0xd832c;return true; // TST.W 80(A6); BNE.W d8358.
    case 0xd832c:return ou19_animation(c,0x1e3,OU19_BANK_C0,0x8,0xd8354);     // animation 1e3, bank LONG 2001c0, + 8.
    case 0xd8354:r.pc=0xd8380;return true;                                  // BRA.W d8380.
    case 0xd8358:return ou19_animation(c,0x1fb,OU19_BANK_CC,0x80,0xd8380);    // animation 1fb, bank LONG 2001cc, + 80.
    case 0xd8380:r.a[0]=am_index(r.a[6],0x26);return am_call(c,0xd83c0,0xd8388); // LEA 26(A6),A0; JSR d83c0(PC) (boundary).
    case 0xd8388:return am_call(c,0x46ef4,0xd838e);                         // JSR 46ef4.L.
    case 0xd838e:return ou19_install(c,0xd8394,0xd8394);                    // MOVE.L #d8394,(A6).
    case 0xd8394:return ou19_test(c,r.a[6],0x15,7,0xd83a8,0xd839e);         // (installed callback) BTST.B #7,15(A6); BEQ.W d83a8.
    case 0xd839e:return am_call(c,0x4be06,0xd83a4);                         // JSR 4be06.L.
    case 0xd83a4:r.pc=0xd83ae;return true;                                  // BRA.W d83ae.
    case 0xd83a8:return am_call(c,0x4be2c,0xd83ae);                         // JSR 4be2c.L (U18).
    case 0xd83ae:return am_call(c,0x49fc6,0xd83b4);                         // JSR 49fc6.L.
    case 0xd83b4:return ou19_consume(c,false,0xd83be,0xd83b8);              // BCC.W d83be (C returned by 49fc6).

    // ---- dbefe (callback): MOVE.W #731,D0; JSR 3af8.L.
    case 0xdbefe:am_word(r.d[0],0x731);return am_call(c,0x3af8,0xdbf08);
    case 0xdbf08:r.pc=0xdbf0c;return true;                                  // BRA.W dbf0c.
    case 0xdbf0c:if(!am_read(c,0x100012,1,value))return false;r.pc=(value&255U)==1U?0xdbf1e:0xdbf18;return true; // CMPI.B #1,100012.L; BEQ.W dbf1e.
    case 0xdbf1e:if(!ou19_put(c,r.a[6],0x76,2,0x294))return false;return ou19_install(c,0xdbf2a,0xdbf2a); // MOVE.W #294,76(A6); MOVE.L #dbf2a,(A6).
    case 0xdbf2a:if(!ou19_count(c,0x76,borrow))return false;r.pc=borrow?0xdbf34:0xdbf32;return true; // (installed callback) SUBQ.W #1,76(A6); BCS.W dbf34.
    case 0xdbf34:r.a[0]=0x4841a;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xdbf44); // MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L.
    default:return am_error(c,"unsupported animation objects u19 PC");
    }
}
}
