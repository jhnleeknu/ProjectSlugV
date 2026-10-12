#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t ON11_BANK_13C=0x20013c;       // MOVE.L 20013c.L,22(A6) (aefe0 af00c; banked window LONG, live bus).
const std::uint32_t ON11_RANGE=0xaee12;           // LEA aee12(PC),A0 (the 1ab02 range record; not read here).
const std::uint32_t ON11_SCREEN=0x10d256;         // LEA 10d256.L,A1 (fixed work RAM object: WORD 4, LONG c).
std::uint32_t on11_w(std::uint32_t v) {return v&65535U;}
bool on11_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on11_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// MOVE.W/MOVE.L d16(As),d16(Ad) (read, then write).
bool on11_copy(AnimationMachineContext& c,std::uint32_t src,std::uint32_t src_d,std::uint32_t dst,std::uint32_t dst_d,unsigned int size) {
    std::uint32_t value=0;if(!on11_get(c,src,src_d,size,value))return false;return on11_put(c,dst,dst_d,size,value);
}
// MULS.W: sext16(a) * sext16(b) as a 32-bit two's complement product (|product| <= 2^30, no overflow).
std::uint32_t on11_muls(std::uint32_t a,std::uint32_t b) {
    const std::int32_t x=static_cast<std::int32_t>(on11_w(a))-((a&0x8000U)?65536:0);
    const std::int32_t y=static_cast<std::int32_t>(on11_w(b))-((b&0x8000U)?65536:0);
    return static_cast<std::uint32_t>(x*y);
}
// ASR.W #n on the low WORD (the sign bit is copied explicitly).
void on11_asr_w(std::uint32_t& r,unsigned int n) {
    std::uint32_t u=on11_w(r);for(unsigned int i=0;i<n;++i)u=(u>>1)|(u&0x8000U);am_word(r,u);
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool on11_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n11 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.L #callback,(A6), then continue at next_pc.
bool on11_install(AnimationMachineContext& c,std::uint32_t callback,std::uint32_t next_pc) {
    if(!am_write(c,c.s.a[6],4,callback))return false;c.s.pc=next_pc;return true;
}
// TST.W d16(A6); Bcc on zero: zero_pc when the WORD is 0.
bool on11_test(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t zero_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!on11_get(c,c.s.a[6],displacement,2,value))return false;
    c.s.pc=value==0U?zero_pc:next_pc;return true;
}
// CMPI.W #k,D1; BNE.W other_pc (equal -> next_pc).
bool on11_dir(AnimationMachineContext& c,std::uint32_t k,std::uint32_t other_pc,std::uint32_t next_pc) {
    c.s.pc=on11_w(c.s.d[1])==k?next_pc:other_pc;return true;
}
// LEA 26(A6),A0; MOVE.W #db,20(A6); MOVE.L 20013c.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d16(A1),A1;
// JSR 49f8c.L (the bank LONG and the LONG at its value + d16 through the live bus).
bool on11_animation(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=am_index(r.a[6],0x26);
    if(!on11_put(c,r.a[6],0x20,2,0xdb) || !am_read(c,ON11_BANK_13C,4,value) || !on11_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!on11_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
    if(!on11_get(c,r.a[1],displacement,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,return_pc);
}
// LEA table.L,A0; JSR 4ae4a.L.
bool on11_hits(AnimationMachineContext& c,std::uint32_t table,std::uint32_t return_pc) {c.s.a[0]=table;return am_call(c,0x4ae4a,return_pc);}
}
// Objects F4 N11 (95 block starts): the node callback aee30 (28ae child loop, installed aef18), its child aef34 (installed aef3a)
// and grandchild aef9a (banked animation 20013c, installed af030), the node callbacks dbf80 (two sounds) eb24e (A5 5e52..5e56) and
// eb266 (installed eb2ba) with the LONG table install eb352 (installed eb376), the state change eb586 (BYTE table eb5aa, LONG table
// eb5d2 written to (A6)), the movement record eb5e6 (returns C: ORI/ANDI CCR), eb616 and the interpreter command callbacks eb74a
// eb75c. Consumers aee9e (28ae), aef28 aef8e af060 (1ab02), af03c (49fc6), eb3a0 (eb5e6) and eb3cc (49370). Producers eb60a (Set)
// and eb610 (Clear). No boundary without an executor.
bool animation_objects_n11_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- aee30: MOVE.W 80(A6),D0; BNE.W aee3c.
    case 0xaee30:if(!on11_get(c,r.a[6],0x80,2,value))return false;am_word(r.d[0],value);r.pc=value!=0U?0xaee3c:0xaee38;return true;
    case 0xaee38:am_word(r.d[0],0x18);r.pc=0xaee3c;return true;                          // MOVE.W #18,D0.
    // MOVE.W 76(A6),D1; BNE.W aee4e.
    case 0xaee3c:if(!on11_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[1],value);r.pc=value!=0U?0xaee4e:0xaee44;return true;
    // MOVE.W #0,8e(A6); MOVE.W D0,90(A6).
    case 0xaee44:if(!on11_put(c,r.a[6],0x8e,2,0) || !on11_put(c,r.a[6],0x90,2,on11_w(r.d[0])))return false;r.pc=0xaee4e;return true;
    case 0xaee4e:return on11_dir(c,1,0xaee62,0xaee56);                                    // CMPI.W #1,D1; BNE.W aee62.
    // MOVE.W #0,8e(A6); NEG.W D0; MOVE.W D0,90(A6).
    case 0xaee56:
        if(!on11_put(c,r.a[6],0x8e,2,0))return false;am_word(r.d[0],(0U-on11_w(r.d[0]))&65535U);
        if(!on11_put(c,r.a[6],0x90,2,on11_w(r.d[0])))return false;r.pc=0xaee62;return true;
    case 0xaee62:return on11_dir(c,2,0xaee76,0xaee6a);                                    // CMPI.W #2,D1; BNE.W aee76.
    // NEG.W D0; MOVE.W D0,8e(A6); MOVE.W #0,90(A6).
    case 0xaee6a:
        am_word(r.d[0],(0U-on11_w(r.d[0]))&65535U);
        if(!on11_put(c,r.a[6],0x8e,2,on11_w(r.d[0])) || !on11_put(c,r.a[6],0x90,2,0))return false;r.pc=0xaee76;return true;
    case 0xaee76:return on11_dir(c,3,0xaee88,0xaee7e);                                    // CMPI.W #3,D1; BNE.W aee88.
    // MOVE.W D0,8e(A6); MOVE.W #0,90(A6).
    case 0xaee7e:if(!on11_put(c,r.a[6],0x8e,2,on11_w(r.d[0])) || !on11_put(c,r.a[6],0x90,2,0))return false;r.pc=0xaee88;return true;
    case 0xaee88:if(!on11_put(c,r.a[6],0x8c,2,0))return false;r.pc=0xaee8e;return true;   // MOVE.W #0,8c(A6).
    case 0xaee8e:r.a[0]=0xaef34;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xaee9e);     // MOVEA.L #aef34,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xaee9e:return on11_consume(c,true,0xaeea8,0xaeea2);                             // BCS.W aeea8 (C of 28ae).
    // JMP 2a00.L.
    case 0xaeea2:case 0xaef2c:case 0xaef76:case 0xaef92:case 0xaf040:case 0xaf064:r.pc=0x2a00;return true;
    // MOVE.W 8c(A6),D0; MOVE.W 7e(A6),D1; MULS.W D1,D0; MOVE.W D0,88(A0); MOVE.W 7c(A6),8a(A0); MOVE.W 7a(A6),7a(A0);
    // MOVE.W 8c(A6),8c(A0); MOVE.W 82(A6),D0; ADD.W D0,8c(A0); MOVE.W 84(A6),84(A0); MOVE.W 76(A6),76(A0); MOVE.W 86(A6),86(A0);
    // MOVE.W 76(A6),D2; MOVE.W 8e(A6),D0; MOVE.W 90(A6),D1; MULS.W 8c(A6),D0; MULS.W 8c(A6),D1; JSR 49214.L.
    case 0xaeea8:
        if(!on11_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],value);
        if(!on11_get(c,r.a[6],0x7e,2,value))return false;am_word(r.d[1],value);
        r.d[0]=on11_muls(r.d[0],r.d[1]);
        if(!on11_put(c,r.a[0],0x88,2,on11_w(r.d[0])) || !on11_copy(c,r.a[6],0x7c,r.a[0],0x8a,2) || !on11_copy(c,r.a[6],0x7a,r.a[0],0x7a,2) ||
            !on11_copy(c,r.a[6],0x8c,r.a[0],0x8c,2))return false;
        if(!on11_get(c,r.a[6],0x82,2,value))return false;am_word(r.d[0],value);
        if(!on11_get(c,r.a[0],0x8c,2,value) || !on11_put(c,r.a[0],0x8c,2,(value+on11_w(r.d[0]))&65535U))return false;
        if(!on11_copy(c,r.a[6],0x84,r.a[0],0x84,2) || !on11_copy(c,r.a[6],0x76,r.a[0],0x76,2) || !on11_copy(c,r.a[6],0x86,r.a[0],0x86,2))return false;
        if(!on11_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[2],value);
        if(!on11_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],value);
        if(!on11_get(c,r.a[6],0x90,2,value))return false;am_word(r.d[1],value);
        if(!on11_get(c,r.a[6],0x8c,2,value))return false;r.d[0]=on11_muls(r.d[0],value);
        if(!on11_get(c,r.a[6],0x8c,2,value))return false;r.d[1]=on11_muls(r.d[1],value);
        return am_call(c,0x49214,0xaeefc);
    // MOVE.W 8c(A6),D0; ADDQ.W #1,D0; CMP.W 78(A6),D0; BGT.W aef12 (signed WORD: !Z and N == V).
    case 0xaeefc: {
        if(!on11_get(c,r.a[6],0x8c,2,value))return false;am_word(r.d[0],(value+1U)&65535U);
        std::uint32_t limit=0;if(!on11_get(c,r.a[6],0x78,2,limit))return false;
        const std::uint32_t a=on11_w(r.d[0]),res=(a-limit)&65535U;
        const bool n=(res&0x8000U)!=0U,z=res==0U,v=(((a^limit)&(a^res))&0x8000U)!=0U;
        r.pc=(!z && n==v)?0xaef12:0xaef0a;return true;
    }
    case 0xaef0a:if(!on11_put(c,r.a[6],0x8c,2,on11_w(r.d[0])))return false;r.pc=0xaee8e;return true; // MOVE.W D0,8c(A6); BRA.W aee8e.
    case 0xaef12:return on11_install(c,0xaef18,0xaef18);                                  // MOVE.L #aef18,(A6).

    // ---- aef18 (installed): JSR 4be06.L; LEA aee12(PC),A0; JSR 1ab02.L; BCC.W aef32; JMP 2a00.L; RTS.
    case 0xaef18:return am_call(c,0x4be06,0xaef1e);
    case 0xaef1e:r.a[0]=ON11_RANGE;return am_call(c,0x1ab02,0xaef28);
    case 0xaef28:return on11_consume(c,false,0xaef32,0xaef2c);                             // BCC.W aef32 (C of 1ab02).
    // RTS (keeps C).
    case 0xaef32:case 0xaef98:case 0xaf06a:case 0xeb2fc:case 0xeb3e0:case 0xeb5a8:return am_return(c);

    // ---- aef34 (28ae child): MOVE.L #aef3a,(A6); JSR 43e34.L; TST.W 88(A6); BNE.W aef80.
    case 0xaef34:return on11_install(c,0xaef3a,0xaef3a);
    case 0xaef3a:return am_call(c,0x43e34,0xaef40);
    case 0xaef40:return on11_test(c,0x88,0xaef48,0xaef80);
    case 0xaef48:r.a[0]=0xaef9a;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xaef58);     // MOVEA.L #aef9a,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xaef58:r.d[0]=0;r.d[1]=0;return am_call(c,0x49214,0xaef62);                     // MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.L.
    // MOVE.W 8a(A6),88(A6); MOVE.W 86(A6),86(A0); SUBQ.W #1,7a(A6); BCC.W aef7c (C = the WORD was 0).
    case 0xaef62:
        if(!on11_copy(c,r.a[6],0x8a,r.a[6],0x88,2) || !on11_copy(c,r.a[6],0x86,r.a[0],0x86,2))return false;
        if(!on11_get(c,r.a[6],0x7a,2,value) || !on11_put(c,r.a[6],0x7a,2,(value+65535U)&65535U))return false;
        r.pc=value!=0U?0xaef7c:0xaef76;return true;
    case 0xaef7c:r.pc=0xaef84;return true;                                                // BRA.W aef84.
    case 0xaef80:if(!on11_get(c,r.a[6],0x88,2,value) || !on11_put(c,r.a[6],0x88,2,(value+65535U)&65535U))return false;r.pc=0xaef84;return true;
    case 0xaef84:r.a[0]=ON11_RANGE;return am_call(c,0x1ab02,0xaef8e);                     // LEA aee12(PC),A0; JSR 1ab02.L.
    case 0xaef8e:return on11_consume(c,false,0xaef98,0xaef92);                             // BCC.W aef98 (C of 1ab02).

    // ---- aef9a (28ae grandchild): MOVE.W #4e,D0; MOVE.W #2,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xaef9a:am_word(r.d[0],0x4e);am_word(r.d[1],2);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xaefac);
    // MOVEA.L c(A6),A0; MOVE.W #8820,D0; ADD.W 8c(A0),D0; MOVE.W D0,68(A6); MOVE.W D0,1e(A6); TST.W 84(A0); BEQ.W aefce.
    case 0xaefac:
        if(!on11_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;
        if(!on11_get(c,r.a[0],0x8c,2,value))return false;am_word(r.d[0],(0x8820U+value)&65535U);
        if(!on11_put(c,r.a[6],0x68,2,on11_w(r.d[0])) || !on11_put(c,r.a[6],0x1e,2,on11_w(r.d[0])))return false;
        if(!on11_get(c,r.a[0],0x84,2,value))return false;r.pc=value==0U?0xaefce:0xaefc8;return true;
    // BCHG.B #0,15(A6) (Z only).
    case 0xaefc8:if(!on11_get(c,r.a[6],0x15,1,value) || !on11_put(c,r.a[6],0x15,1,(value^1U)&255U))return false;r.pc=0xaefce;return true;
    case 0xaefce:return on11_test(c,0x86,0xaefd6,0xaf002);                                // TST.W 86(A6); BNE.W af002.
    case 0xaefd6:return on11_animation(c,8,0xaeffe);
    case 0xaeffe:r.pc=0xaf02a;return true;                                                // BRA.W af02a.
    case 0xaf002:return on11_animation(c,0xc,0xaf02a);
    case 0xaf02a:return on11_install(c,0xaf030,0xaf030);                                  // MOVE.L #af030,(A6).
    case 0xaf030:return am_call(c,0x4be06,0xaf036);
    case 0xaf036:return am_call(c,0x49fc6,0xaf03c);
    case 0xaf03c:return on11_consume(c,false,0xaf046,0xaf040);                             // BCC.W af046 (C of 49fc6).
    // MOVE.L 72(A6),D0; BEQ.W af056.
    case 0xaf046:if(!on11_get(c,r.a[6],0x72,4,value))return false;r.d[0]=value;r.pc=value==0U?0xaf056:0xaf04e;return true;
    case 0xaf04e:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0xaf056);                         // MOVEA.L D0,A0; JSR 4ae4a.L.
    case 0xaf056:r.a[0]=ON11_RANGE;return am_call(c,0x1ab02,0xaf060);                     // LEA aee12(PC),A0; JSR 1ab02.L.
    case 0xaf060:return on11_consume(c,false,0xaf06a,0xaf064);                             // BCC.W af06a (C of 1ab02).

    // ---- dbf80: MOVE.W #19d7,D0; JSR 3af8.L; MOVE.W #731,D0; JSR 3af8.L; JMP 2a00.L.
    case 0xdbf80:am_word(r.d[0],0x19d7);return am_call(c,0x3af8,0xdbf8a);
    case 0xdbf8a:am_word(r.d[0],0x731);return am_call(c,0x3af8,0xdbf94);
    case 0xdbf94:r.pc=0x2a00;return true;

    // ---- eb24e: MOVE.W 76(A6),5e52(A5); MOVE.W 78(A6),5e54(A5); MOVE.W 7a(A6),5e56(A5); JMP 2a00.L.
    case 0xeb24e:
        if(!on11_copy(c,r.a[6],0x76,r.a[5],0x5e52,2) || !on11_copy(c,r.a[6],0x78,r.a[5],0x5e54,2) ||
            !on11_copy(c,r.a[6],0x7a,r.a[5],0x5e56,2))return false;
        r.pc=0x2a00;return true;

    // ---- eb266: LEA eb6e8.L,A0; JSR 490ba.L.
    case 0xeb266:r.a[0]=0xeb6e8;return am_call(c,0x490ba,0xeb272);
    // EXT.L D0; LSL.L #8,D0; NEG.L D0; MOVE.L D0,7c(A6); LEA 10d256.L,A1; MOVE.W #e0,4(A1); MOVE.W #20,D0; MOVE.W #ec,D1; JSR 43e04.L.
    case 0xeb272:
        r.d[0]=am_extend_word(r.d[0]&65535U);r.d[0]=(r.d[0]<<8)&0xffffffffU;r.d[0]=(0U-r.d[0])&0xffffffffU;
        if(!on11_put(c,r.a[6],0x7c,4,r.d[0]))return false;r.a[1]=ON11_SCREEN;
        if(!on11_put(c,r.a[1],4,2,0xe0))return false;am_word(r.d[0],0x20);am_word(r.d[1],0xec);return am_call(c,0x43e04,0xeb296);
    case 0xeb296:am_word(r.d[0],0x74d);return am_call(c,0x3af8,0xeb2a0);                  // MOVE.W #74d,D0; JSR 3af8.L.
    // MOVE.W #0,84(A6); LEA 10d256.L,A1; MOVE.L #fffe8000,c(A1); MOVE.L #eb2ba,(A6).
    case 0xeb2a0:
        if(!on11_put(c,r.a[6],0x84,2,0))return false;r.a[1]=ON11_SCREEN;
        if(!on11_put(c,r.a[1],0xc,4,0xfffe8000U))return false;return on11_install(c,0xeb2ba,0xeb2ba);
    case 0xeb2ba:return am_call(c,0xeb616,0xeb2be);                                       // JSR eb616(PC).
    case 0xeb2be:return am_call(c,0x43e34,0xeb2c4);
    case 0xeb2c4:return on11_hits(c,0xeb6ac,0xeb2d0);
    case 0xeb2d0:return on11_hits(c,0xeb6ca,0xeb2dc);
    // LEA 10d256.L,A1; MOVE.W 4(A1),D0; CMPI.W #e0,D0; BPL.W eb2fc (N of D0.W - e0).
    case 0xeb2dc:
        r.a[1]=ON11_SCREEN;if(!on11_get(c,r.a[1],4,2,value))return false;am_word(r.d[0],value);
        r.pc=(((value-0xe0U)&0x8000U)==0U)?0xeb2fc:0xeb2ee;return true;
    case 0xeb2ee:return am_call(c,0x3d44,0xeb2f4);
    case 0xeb2f4:am_word(r.d[0],0xc);return am_call(c,0xeb586,0xeb2fc);                   // MOVE.W #c,D0; JSR eb586(PC).

    // ---- eb352 (LONG table eb5d2 index 3): MOVE.W 86(A6),D0; MOVE.W D0,D1; ASR.W #1,D0; MOVE.W eb2fe(PC,D0.W),88(A6);
    // MOVE.L eb308(PC,D1.W),78(A6); LEA 10d256.L,A1; CLR.L c(A1); MOVE.L #eb376,(A6).
    case 0xeb352:
        if(!on11_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],value);on11_asr_w(r.d[0],1);
        if(!am_read(c,am_index(0xeb2fe,r.d[0]),2,value) || !on11_put(c,r.a[6],0x88,2,value))return false;
        if(!am_read(c,am_index(0xeb308,r.d[1]),4,value) || !on11_put(c,r.a[6],0x78,4,value))return false;
        r.a[1]=ON11_SCREEN;if(!on11_put(c,r.a[1],0xc,4,0))return false;return on11_install(c,0xeb376,0xeb376);
    case 0xeb376:return am_call(c,0xeb616,0xeb37a);                                       // JSR eb616(PC).
    case 0xeb37a:return am_call(c,0x43e34,0xeb380);
    case 0xeb380:return on11_hits(c,0xeb6ac,0xeb38c);
    case 0xeb38c:return on11_hits(c,0xeb6ca,0xeb398);
    // MOVEA.L 78(A6),A0; JSR eb5e6(PC).
    case 0xeb398:if(!on11_get(c,r.a[6],0x78,4,value))return false;r.a[0]=value;return am_call(c,0xeb5e6,0xeb3a0);
    case 0xeb3a0:return on11_consume(c,false,0xeb3be,0xeb3a4);                             // BCC.W eb3be (C of eb5e6).
    // MOVE.W 86(A6),D0; ASR.W #1,D0; LEA eb31c(PC),A0; MOVE.W (A0,D0.W),80(A6); BPL.W eb3be.
    case 0xeb3a4:
        if(!on11_get(c,r.a[6],0x86,2,value))return false;am_word(r.d[0],value);on11_asr_w(r.d[0],1);r.a[0]=0xeb31c;
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value) || !on11_put(c,r.a[6],0x80,2,value))return false;
        r.pc=(value&0x8000U)==0U?0xeb3be:0xeb3b8;return true;
    case 0xeb3b8:if(!on11_copy(c,r.a[5],0x5e56,r.a[6],0x80,2))return false;r.pc=0xeb3be;return true; // MOVE.W 5e56(A5),80(A6).
    case 0xeb3be:return on11_test(c,0x80,0xeb3e0,0xeb3c6);                                // TST.W 80(A6); BEQ.W eb3e0.
    case 0xeb3c6:return am_call(c,0x49370,0xeb3cc);
    case 0xeb3cc:return on11_consume(c,true,0xeb3e0,0xeb3d0);                              // BCS.W eb3e0 (C of 49370).
    // SUBQ.W #1,80(A6); BNE.W eb3e0.
    case 0xeb3d0:
        if(!on11_get(c,r.a[6],0x80,2,value))return false;value=(value+65535U)&65535U;
        if(!on11_put(c,r.a[6],0x80,2,value))return false;r.pc=value!=0U?0xeb3e0:0xeb3d8;return true;
    // MOVE.W 88(A6),D0; JSR eb586(PC).
    case 0xeb3d8:if(!on11_get(c,r.a[6],0x88,2,value))return false;am_word(r.d[0],value);return am_call(c,0xeb586,0xeb3e0);

    // ---- eb586: MOVE.W D0,D1; ASR.W #2,D0; MOVE.W 84(A6),D2; ADD.W D2,D2; ADD.W D2,D0; MOVE.B eb5aa(PC,D0.W),D2; BEQ.W eb5a8.
    case 0xeb586:
        am_word(r.d[1],r.d[0]);on11_asr_w(r.d[0],2);
        if(!on11_get(c,r.a[6],0x84,2,value))return false;am_word(r.d[2],(value+value)&65535U);
        am_word(r.d[0],(r.d[0]+r.d[2])&65535U);
        if(!am_read(c,am_index(0xeb5aa,r.d[0]),1,value))return false;am_byte(r.d[2],value);
        r.pc=(value&255U)==0U?0xeb5a8:0xeb59a;return true;
    // MOVE.W 84(A6),86(A6); MOVE.W D1,84(A6); MOVE.L eb5d2(PC,D1.W),(A6) (the table value is only written to the node).
    case 0xeb59a:
        if(!on11_copy(c,r.a[6],0x84,r.a[6],0x86,2) || !on11_put(c,r.a[6],0x84,2,on11_w(r.d[1])))return false;
        if(!am_read(c,am_index(0xeb5d2,r.d[1]),4,value) || !am_write(c,r.a[6],4,value))return false;r.pc=0xeb5a8;return true;

    // ---- eb5e6: CMPI.W #80,(A0); BEQ.W eb610.
    case 0xeb5e6:if(!am_read(c,r.a[0],2,value))return false;r.pc=value==0x80U?0xeb610:0xeb5ee;return true;
    // LEA 10d256.L,A1; MOVE.W 4(A1),D0; ADD.W (A0)+,D0; MOVE.W D0,4(A1); MOVE.L A0,78(A6); CMPI.W #80,(A0); BNE.W eb610.
    case 0xeb5ee:
        r.a[1]=ON11_SCREEN;if(!on11_get(c,r.a[1],4,2,value))return false;am_word(r.d[0],value);
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]+=2U;am_word(r.d[0],(r.d[0]+value)&65535U);
        if(!on11_put(c,r.a[1],4,2,on11_w(r.d[0])) || !on11_put(c,r.a[6],0x78,4,r.a[0]))return false;
        if(!am_read(c,r.a[0],2,value))return false;r.pc=value!=0x80U?0xeb610:0xeb60a;return true;
    case 0xeb60a:r.carry=AnimationCarrySet;return am_return(c);                           // ORI.B #1,CCR; RTS.
    case 0xeb610:r.carry=AnimationCarryClear;return am_return(c);                         // ANDI.B #fe,CCR; RTS.
    // LEA 10d256.L,A1; MOVE.W 4(A1),D1; SUBI.W #28,D1; RTS.
    case 0xeb616:
        r.a[1]=ON11_SCREEN;if(!on11_get(c,r.a[1],4,2,value))return false;am_word(r.d[1],(value-0x28U)&65535U);return am_return(c);

    // ---- eb74a / eb75c (interpreter command callbacks): MOVEA.L (A0),A0; MOVE.L A0,72(A6); RTS / MOVE.L #0,72(A6); RTS.
    case 0xeb74a:
        if(!am_read(c,r.a[0],4,value))return false;r.a[0]=value;if(!on11_put(c,r.a[6],0x72,4,r.a[0]))return false;return am_return(c);
    case 0xeb75c:if(!on11_put(c,r.a[6],0x72,4,0))return false;return am_return(c);
    default:return am_error(c,"unsupported animation objects n11 PC");
    }
}
}
