#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t ofr6_w(std::uint32_t value) {return value&65535U;}
std::uint32_t ofr6_b(std::uint32_t value) {return value&255U;}
// Signed value of the low WORD (CMP.W + BGE / BLE).
int ofr6_sw(std::uint32_t value) {const int v=static_cast<int>(value&65535U);return v>=32768?v-65536:v;}
bool ofr6_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ofr6_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    const std::uint32_t mask=size==1?0xffU:(size==2?0xffffU:0xffffffffU);
    return am_write(c,am_index(base,displacement),size,value&mask);
}
// BCLR.B / BSET.B #bit,d(An): read-modify-write of one BYTE.
bool ofr6_bit(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int bit,bool set) {
    std::uint32_t value=0;if(!ofr6_get(c,base,displacement,1,value))return false;
    const std::uint32_t mask=1U<<bit;return ofr6_put(c,base,displacement,1,set?(value|mask):(value&~mask));
}
// SUBQ.B #1,d(An) / ADDQ.B: the new BYTE (wraps in the BYTE).
bool ofr6_add_byte(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,std::uint32_t addend,std::uint32_t& result) {
    std::uint32_t value=0;if(!ofr6_get(c,base,displacement,1,value))return false;
    result=ofr6_b(value+addend);return ofr6_put(c,base,displacement,1,result);
}
// BCC / BCS / SCC / SCS on a known C (returned by a callee or set by the predecessor block): clear -> clear_pc, set -> set_pc.
bool ofr6_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"objects fr6 caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// ANDI.B #fe,CCR; RTS (Clear) / ORI.B #1,CCR; RTS (Set): the block sets its own C for the caller's consumer.
bool ofr6_return_carry(AnimationMachineContext& c,AnimationCarryState carry) {c.s.carry=carry;return am_return(c);}
// ASR.W #4: arithmetic shift of the low WORD (the sign bit is replicated; no signed shift in C++).
std::uint32_t ofr6_asr4(std::uint32_t value) {const std::uint32_t w=ofr6_w(value);return (w>>4)|((w&0x8000U)!=0U?0xf000U:0U);}
// ABCD as the project's original-CPU oracle (Unicorn M68000) computes it (FR2 contract decision 3, the same formula as FR2a e62a8):
// t = src + 66, s = t + dst + X, c = s ^ (t ^ dst), result = s - ((~c & 110) >> 2 | (~c & 110) >> 3); X = C = bit 8.
std::uint32_t ofr6_abcd(std::uint32_t source,std::uint32_t destination,bool& extend) {
    const std::uint32_t t=(source&0xffU)+0x66U;const std::uint32_t s=t+(destination&0xffU)+(extend?1U:0U);
    const std::uint32_t carries=s^(t^(destination&0xffU));const std::uint32_t none=(~carries)&0x110U;
    const std::uint32_t result=s-((none>>2)|(none>>3));extend=((result>>8)&1U)!=0U;return result&0xffU;
}
// ABCD -(Ay),-(Ax): Ay -= 1, source BYTE; Ax -= 1, destination BYTE; destination := BCD sum (Ay / Ax are never A7 here).
bool ofr6_abcd_step(AnimationMachineContext& c,std::uint32_t& ay,std::uint32_t& ax,bool& extend) {
    std::uint32_t source=0;std::uint32_t destination=0;ay=ay-1U;
    if(!am_read(c,ay,1,source))return false;ax=ax-1U;
    if(!am_read(c,ax,1,destination))return false;return am_write(c,ax,1,ofr6_abcd(source,destination,extend));
}
// A1 := the LONG at d75ce + sext(4 * WORD) (the LONG table d75ce, any index through the live bus): LEA d75ce(PC),A1; MOVE.W ..,D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1.
bool ofr6_table_d75ce(AnimationMachineContext& c,std::uint32_t index) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[1]=0xd75ce;am_word(r.d[0],index);am_word(r.d[0],r.d[0]+r.d[0]);am_word(r.d[0],r.d[0]+r.d[0]);
    if(!am_read(c,am_index(r.a[1],r.d[0]),4,value))return false;r.a[1]=value;return true;
}
// MOVE.W 8e(A6),D0; ADD.W D0,8c(A6); BMI.W negative_pc (the N of the WORD sum) / positive_pc.
bool ofr6_grow(AnimationMachineContext& c,std::uint32_t negative_pc,std::uint32_t positive_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!ofr6_get(c,r.a[6],0x8e,2,value))return false;am_word(r.d[0],value);
    if(!ofr6_get(c,r.a[6],0x8c,2,value))return false;value=ofr6_w(value+r.d[0]);if(!ofr6_put(c,r.a[6],0x8c,2,value))return false;
    r.pc=(value&0x8000U)!=0U?negative_pc:positive_pc;return true;
}
// MOVEQ #0,D2; MOVE.B 8c(A6),D2; BSR.W 51608.
bool ofr6_step_51608(AnimationMachineContext& c,std::uint32_t return_pc) {
    std::uint32_t value=0;if(!ofr6_get(c,c.s.a[6],0x8c,1,value))return false;c.s.d[2]=value;return am_call(c,0x51608,return_pc);
}
// 72980 / 729ac: LEA 26(A6),A0; MOVE.W #kind,20(A6); MOVE.L window.l,22(A6) (the bank-window LONG through the live bus); MOVE.W #100,D0;
// LEA 26(A6),A0; MOVEA.L 22(A6),A1 (read back); MOVEA.L field(A1),A1; JSR 49f8c.l.
bool ofr6_bank_anim(AnimationMachineContext& c,std::uint32_t kind,std::uint32_t window,std::uint32_t field,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;r.a[0]=am_index(r.a[6],0x26);
    if(!ofr6_put(c,r.a[6],0x20,2,kind) || !am_read(c,window,4,value) || !ofr6_put(c,r.a[6],0x22,4,value))return false;
    am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
    if(!ofr6_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;if(!ofr6_get(c,r.a[1],field,4,value))return false;r.a[1]=value;
    return am_call(c,0x49f8c,return_pc);
}
// 19a06 / 19a12 / 19a26 / 19a32: CMP.W field(A5),Dn; BGE (ge = true) / BLE (ge = false) skip_pc (signed WORD), otherwise write_pc.
bool ofr6_bound(AnimationMachineContext& c,std::uint32_t field,std::uint32_t reg,bool ge,std::uint32_t skip_pc,std::uint32_t write_pc) {
    std::uint32_t value=0;if(!ofr6_get(c,c.s.a[5],field,2,value))return false;
    const bool skip=ge?ofr6_sw(reg)>=ofr6_sw(value):ofr6_sw(reg)<=ofr6_sw(value);c.s.pc=skip?skip_pc:write_pc;return true;
}
}
// Objects FR6 (220 block starts, contract docs/analysis/animation-machine-frontier-fr6-contract.md): the last C-independent area-D IO frontier of the
// FR5 IO rerun, the object 50dae (the install value of U14 50d82) with its installs 50dd2 50e42 50cf6 50d08 50f1a 50f80 50f9c 50ffe 51076 and its
// helpers 51608 51590 515a2 51178 51574 491fe, and the front of FR7 (C-gated D): the condition test 4855c, the bound helper 19a00, the object d764a
// (the 28ae child of stage_area d760a, installs d7692 d76a6 d76b2 d7700 d7766 d77ba), the object 36292, the helpers 1aa66 1a988 e9148 49c38 48210,
// the object 72978 (install 729e2) with 703f6, the 28ae child 4fcb8 (install 4fcc4) and the BCD add e625e / e6284.  No computed jump, no TRAP; every
// exit is routed.  MOVE.L #v,(A6) enters v only when v is the next PC, otherwise it only writes the callback LONG (50cf6 d7766 d76a6 510d0 511ae
// 70c0c 71c90).  The 12 consumers 362cc (482aa), 4858e (289e), 48598 (1aa66), 50d0e (4945e), 50f62 (SCC, 28ae; MOVE.W then clears C), 51054
// (51044 AND.B Clear / 51050 ORI Set), 729ee d77da (49fc6), d7802 (49fca), d7698 d76b8 d770e (4855c) read a known C or fail; 1aa72 485a2 49c4a
// (ANDI; RTS) / 1aa78 4859c 49c50 (ORI; RTS) set their own C.  X stays inside e6284.  Data through the live bus (no limit test).
bool animation_objects_fr6_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    case 0x19a3e:case 0x362d0:case 0x362d8:case 0x50d2a:case 0x50e6c:case 0x50f50:case 0x50f8e:case 0x50fb0:case 0x51062:case 0x511ac:
    case 0x515a0:case 0x70416:case 0xd76a4:case 0xd76f2:case 0xd7712:case 0xd7826:case 0xe6282:case 0xe62a6:
        return am_return(c);                                                                              // RTS.
    case 0x1aa72:case 0x485a2:case 0x49c4a:return ofr6_return_carry(c,AnimationCarryClear);               // ANDI.B #fe,CCR; RTS.
    case 0x1aa78:case 0x4859c:case 0x49c50:return ofr6_return_carry(c,AnimationCarrySet);                 // ORI.B #1,CCR; RTS.
    case 0x362da:r.pc=0x2a00;return true;                                                                 // JMP 2a00.l.
    // ---- 19a00: TST.B D7; BEQ.W 19a1e / CMP.W 53d0(A5),D1; BGE.W 19a12 / MOVE.W D1,53d0(A5) / CMP.W 53d4(A5),D1; BLE.W 19a1e / MOVE.W D1,53d4(A5)
    // / ANDI.W #ff00,D7; BEQ.W 19a3e / the same for D0 with 53ce / 53d2.
    case 0x19a00:r.pc=ofr6_b(r.d[7])==0U?0x19a1eU:0x19a06U;return true;
    case 0x19a06:return ofr6_bound(c,0x53d0,r.d[1],true,0x19a12,0x19a0e);
    case 0x19a0e:if(!ofr6_put(c,r.a[5],0x53d0,2,r.d[1]))return false;r.pc=0x19a12;return true;
    case 0x19a12:return ofr6_bound(c,0x53d4,r.d[1],false,0x19a1e,0x19a1a);
    case 0x19a1a:if(!ofr6_put(c,r.a[5],0x53d4,2,r.d[1]))return false;r.pc=0x19a1e;return true;
    case 0x19a1e:am_word(r.d[7],r.d[7]&0xff00U);r.pc=ofr6_w(r.d[7])==0U?0x19a3eU:0x19a26U;return true;
    case 0x19a26:return ofr6_bound(c,0x53ce,r.d[0],true,0x19a32,0x19a2e);
    case 0x19a2e:if(!ofr6_put(c,r.a[5],0x53ce,2,r.d[0]))return false;r.pc=0x19a32;return true;
    case 0x19a32:return ofr6_bound(c,0x53d2,r.d[0],false,0x19a3e,0x19a3a);
    case 0x19a3a:if(!ofr6_put(c,r.a[5],0x53d2,2,r.d[0]))return false;r.pc=0x19a3e;return true;
    // ---- 1a988: MOVE.W 5432(A5),D0; ADD.W 53c0(A5),D0; ADD.W 53a6(A5),D0; RTS.
    case 0x1a988:
        if(!ofr6_get(c,r.a[5],0x5432,2,value))return false;am_word(r.d[0],value);
        if(!ofr6_get(c,r.a[5],0x53c0,2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!ofr6_get(c,r.a[5],0x53a6,2,value))return false;am_word(r.d[0],r.d[0]+value);return am_return(c);
    // ---- 1aa66: MOVE.W 5418(A5),D0; CMP.W 53ee(A5),D0; BCC.W 1aa78 (unsigned D0.W >= WORD 53ee).
    case 0x1aa66:
        if(!ofr6_get(c,r.a[5],0x5418,2,value))return false;am_word(r.d[0],value);if(!ofr6_get(c,r.a[5],0x53ee,2,value))return false;
        r.pc=ofr6_w(r.d[0])>=value?0x1aa78U:0x1aa72U;return true;
    // ---- 36292: MOVEA.L c(A6),A0; MOVE.W 78(A0),D0; JSR 1bfb4.l.
    case 0x36292:
        if(!ofr6_get(c,r.a[6],0xc,4,value))return false;r.a[0]=value;if(!ofr6_get(c,r.a[0],0x78,2,value))return false;am_word(r.d[0],value);
        return am_call(c,0x1bfb4,0x362a0);
    case 0x362a0:r.pc=ofr6_b(r.d[1])==0U?0x362daU:0x362a6U;return true;                                   // TST.B D1; BEQ.W 362da.
    case 0x362a6:return am_call(c,0x16ed2,0x362ac);                                                       // JSR 16ed2.l.
    case 0x362ac:return am_call(c,0x43e34,0x362b2);                                                       // JSR 43e34.l.
    case 0x362b2:if(!ofr6_get(c,r.a[6],0x76,1,value))return false;r.pc=value==0U?0x362c6U:0x362baU;return true;   // TST.B 76(A6); BEQ.W 362c6.
    case 0x362ba:if(!ofr6_add_byte(c,r.a[6],0x76,0xff,value))return false;r.pc=value==0U?0x362daU:0x362c2U;return true;   // SUBQ.B #1,76(A6); BEQ.W.
    case 0x362c2:r.pc=0x362d2;return true;                                                                // BRA.W 362d2.
    case 0x362c6:return am_call(c,0x482aa,0x362cc);                                                       // JSR 482aa.l.
    case 0x362cc:return ofr6_carry(c,0x362d2,0x362d0);                                                    // BCC.W 362d2 (C of 482aa).
    case 0x362d2:return am_call(c,0x49fc6,0x362d8);                                                       // JSR 49fc6.l.
    // ---- 48210: LEA 5694(A5),A0; ANDI.W #1,D0; BEQ.W 48220 / LEA 569c(A5),A0 / MOVEQ #0,D1; MOVE.B (A0),D1; RTS.
    case 0x48210:r.a[0]=am_index(r.a[5],0x5694);am_word(r.d[0],r.d[0]&1U);r.pc=ofr6_w(r.d[0])==0U?0x48220U:0x4821cU;return true;
    case 0x4821c:r.a[0]=am_index(r.a[5],0x569c);r.pc=0x48220;return true;
    case 0x48220:if(!am_read(c,r.a[0],1,value))return false;r.d[1]=value;return am_return(c);
    // ---- 4855c: TST.B 568e(A5); BEQ.W 485a2 / BTST.B #2 / #1,5683(A5); BEQ.W 485a2 / BTST.B #0,5683(A5); BNE.W 485a2.
    case 0x4855c:if(!ofr6_get(c,r.a[5],0x568e,1,value))return false;r.pc=value==0U?0x485a2U:0x48564U;return true;
    case 0x48564:if(!ofr6_get(c,r.a[5],0x5683,1,value))return false;r.pc=(value&4U)==0U?0x485a2U:0x4856eU;return true;
    case 0x4856e:if(!ofr6_get(c,r.a[5],0x5683,1,value))return false;r.pc=(value&2U)==0U?0x485a2U:0x48578U;return true;
    case 0x48578:if(!ofr6_get(c,r.a[5],0x5683,1,value))return false;r.pc=(value&1U)!=0U?0x485a2U:0x48582U;return true;
    case 0x48582:r.a[0]=0x100bf4;return am_call(c,0x289e,0x4858e);                                        // LEA 100bf4.l,A0; JSR 289e.l.
    case 0x4858e:return ofr6_carry(c,0x485a2,0x48592);                                                    // BCC.W 485a2 (C of 289e).
    case 0x48592:return am_call(c,0x1aa66,0x48598);                                                       // JSR 1aa66.l.
    case 0x48598:return ofr6_carry(c,0x4859c,0x485a2);                                                    // BCS.W 485a2 (C of 1aa66).
    // ---- 491fe: LEA 2e(A0),A0; MOVEA.L #0,A1; JSR 43e08.l / SUBA.W #2e,A0; RTS.
    case 0x491fe:r.a[0]=r.a[0]+0x2eU;r.a[1]=0;return am_call(c,0x43e08,0x4920e);
    case 0x4920e:r.a[0]=r.a[0]-0x2eU;return am_return(c);
    // ---- 49c38: LEA 5734(A5),A0; ANDI.W #1,D0; LSL.W #2,D0; TST.L (A0,D0.W); BNE.W 49c50.
    case 0x49c38:
        r.a[0]=am_index(r.a[5],0x5734);am_word(r.d[0],r.d[0]&1U);am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.pc=value!=0U?0x49c50U:0x49c4aU;return true;
    // ---- 4fcb8 (28ae child value of stage_catalog 47934): MOVE.W #ffe2,7a(A6); MOVE.L #4fcc4,(A6) (next PC) / MOVEA.L #50030,A0; BRA.W 4fce0.
    case 0x4fcb8:if(!ofr6_put(c,r.a[6],0x7a,2,0xffe2) || !ofr6_put(c,r.a[6],0,4,0x4fcc4))return false;r.pc=0x4fcc4;return true;
    case 0x4fcc4:r.a[0]=0x50030;r.pc=0x4fce0;return true;
    // ---- 50cf6 (installed value): BCLR.B #0,15(A6); JSR 496c2.l / MOVE.L #50d08,(A6) (next PC) / JSR 4945e.l / BCS.W 50d24.
    case 0x50cf6:if(!ofr6_bit(c,r.a[6],0x15,0,false))return false;return am_call(c,0x496c2,0x50d02);
    case 0x50d02:if(!ofr6_put(c,r.a[6],0,4,0x50d08))return false;r.pc=0x50d08;return true;
    case 0x50d08:return am_call(c,0x4945e,0x50d0e);
    case 0x50d0e:return ofr6_carry(c,0x50d12,0x50d24);                                                    // BCS.W 50d24 (C of 4945e).
    // ADDQ.B #1,a1(A6); ANDI.B #1,a1(A6); BNE.W 50fb2 / BRA.W 50e94.
    case 0x50d12:
        if(!ofr6_add_byte(c,r.a[6],0xa1,1,value) || !ofr6_get(c,r.a[6],0xa1,1,value))return false;value&=1U;
        if(!ofr6_put(c,r.a[6],0xa1,1,value))return false;r.pc=value!=0U?0x50fb2U:0x50d20U;return true;
    case 0x50d20:r.pc=0x50e94;return true;
    case 0x50d24:return am_call(c,0x43ea4,0x50d2a);
    // ---- 50dae (installed value of U14 50d82): MOVE.B 1a(A6),14(A6); BCLR.B #2,7e(A6); CLR.W 8c(A6); MOVE.L #50e80,80(A6); JSR 496c2.l.
    case 0x50dae:
        if(!ofr6_get(c,r.a[6],0x1a,1,value) || !ofr6_put(c,r.a[6],0x14,1,value) || !ofr6_bit(c,r.a[6],0x7e,2,false) ||
           !ofr6_put(c,r.a[6],0x8c,2,0) || !ofr6_put(c,r.a[6],0x80,4,0x50e80))return false;
        return am_call(c,0x496c2,0x50dcc);
    case 0x50dcc:if(!ofr6_put(c,r.a[6],0,4,0x50dd2))return false;r.pc=0x50dd2;return true;               // MOVE.L #50dd2,(A6) (next PC).
    case 0x50dd2:if(!ofr6_get(c,r.a[6],0x8c,2,value))return false;r.pc=value==0U?0x50de0U:0x50ddaU;return true;   // TST.W 8c(A6); BEQ.W 50de0.
    case 0x50dda:if(!ofr6_get(c,r.a[6],0x8c,2,value) || !ofr6_put(c,r.a[6],0x8c,2,value-1U))return false;return am_return(c);   // SUBQ.W; RTS.
    // MOVEA.L 80(A6),A0; MOVE.W (A0)+,D0; CMPI.W #ffff,D0; BEQ.W 50dfc.
    case 0x50de0:
        if(!ofr6_get(c,r.a[6],0x80,4,value))return false;r.a[0]=value;if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);
        r.a[0]=r.a[0]+2U;r.pc=ofr6_w(r.d[0])==0xffffU?0x50dfcU:0x50deeU;return true;
    // MOVE.W (A0)+,8c(A6); MOVE.L A0,80(A6); JMP 3af8.l.
    case 0x50dee:
        if(!am_read(c,r.a[0],2,value))return false;r.a[0]=r.a[0]+2U;
        if(!ofr6_put(c,r.a[6],0x8c,2,value) || !ofr6_put(c,r.a[6],0x80,4,r.a[0]))return false;r.pc=0x3af8;return true;
    case 0x50dfc:am_word(r.d[0],0x189f);return am_call(c,0x3af8,0x50e06);                                // MOVE.W #189f,D0; JSR 3af8.l.
    // MOVE.W #2000,8c(A6); MOVE.W 52486(PC),8e(A6); MOVEA.L #521ec,A1; MOVE.W #100,D0; JSR 49f8c.l.
    case 0x50e06:
        if(!ofr6_put(c,r.a[6],0x8c,2,0x2000) || !am_read(c,0x52486,2,value) || !ofr6_put(c,r.a[6],0x8e,2,value))return false;
        r.a[1]=0x521ec;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x50e22);
    // LEA 538e(A5),A1; MOVE.W #120,D0; MOVE.W #b4 | a0 | ff80,D1; JSR 43e04.l.
    case 0x50e22:r.a[1]=am_index(r.a[5],0x538e);am_word(r.d[0],0x120);am_word(r.d[1],0xb4);return am_call(c,0x43e04,0x50e34);
    // MOVE.L #ffff0000,3a(A6); MOVE.L #50e42,(A6) (next PC).
    case 0x50e34:if(!ofr6_put(c,r.a[6],0x3a,4,0xffff0000U) || !ofr6_put(c,r.a[6],0,4,0x50e42))return false;r.pc=0x50e42;return true;
    case 0x50e42:return ofr6_step_51608(c,0x50e4c);
    case 0x50e4c:return am_call(c,0x43ea4,0x50e52);
    // ADDI.L #800,3a(A6); JSR 49fc6.l.
    case 0x50e52:if(!ofr6_get(c,r.a[6],0x3a,4,value) || !ofr6_put(c,r.a[6],0x3a,4,value+0x800U))return false;return am_call(c,0x49fc6,0x50e60);
    case 0x50e60:return ofr6_grow(c,0x50e6e,0x50e6c);
    case 0x50e6e:am_word(r.d[0],0x19d6);return am_call(c,0x3af8,0x50e78);                                // MOVE.W #19d6,D0; JSR 3af8.l.
    case 0x50e78:if(!ofr6_put(c,r.a[6],0,4,0x50cf6))return false;return am_return(c);                   // MOVE.L #50cf6,(A6) (write only); RTS.
    // ---- 50e94: MOVEA.L #526e4,A1; MOVE.W #100,D0; JSR 49f8c.l / MOVEA.L #52792,A1; MOVE.W #100,D0; LEA 76(A6),A0; JSR 49f96.l.
    case 0x50e94:r.a[1]=0x526e4;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x50ea4);
    case 0x50ea4:r.a[1]=0x52792;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x76);return am_call(c,0x49f96,0x50eb8);
    // BCLR.B #2,7e(A6); MOVE.B 1a(A6),14(A6); BCLR.B #0,15(A6); JSR 49a58.l.
    case 0x50eb8:
        if(!ofr6_bit(c,r.a[6],0x7e,2,false) || !ofr6_get(c,r.a[6],0x1a,1,value) || !ofr6_put(c,r.a[6],0x14,1,value) ||
           !ofr6_bit(c,r.a[6],0x15,0,false))return false;
        return am_call(c,0x49a58,0x50ed0);
    case 0x50ed0:am_byte(r.d[0],r.d[0]&1U);r.pc=ofr6_b(r.d[0])==0U?0x50edeU:0x50ed8U;return true;       // ANDI.B #1,D0; BEQ.W 50ede.
    case 0x50ed8:if(!ofr6_bit(c,r.a[6],0x15,0,true))return false;r.pc=0x50ede;return true;               // BSET.B #0,15(A6).
    case 0x50ede:return am_call(c,0x496c2,0x50ee4);
    // MOVE.L #2000,3a(A6); MOVE.W #189f,D0; JSR 3af8.l.
    case 0x50ee4:if(!ofr6_put(c,r.a[6],0x3a,4,0x2000))return false;am_word(r.d[0],0x189f);return am_call(c,0x3af8,0x50ef6);
    // MOVE.W #2000,8c(A6); MOVE.W 52790(PC),8e(A6); LEA 538e(A5),A1; MOVE.W #120,D0; MOVE.W #a0,D1; JSR 43e04.l.
    case 0x50ef6:
        if(!ofr6_put(c,r.a[6],0x8c,2,0x2000) || !am_read(c,0x52790,2,value) || !ofr6_put(c,r.a[6],0x8e,2,value))return false;
        r.a[1]=am_index(r.a[5],0x538e);am_word(r.d[0],0x120);am_word(r.d[1],0xa0);return am_call(c,0x43e04,0x50f14);
    case 0x50f14:if(!ofr6_put(c,r.a[6],0,4,0x50f1a))return false;r.pc=0x50f1a;return true;               // MOVE.L #50f1a,(A6) (next PC).
    case 0x50f1a:return ofr6_step_51608(c,0x50f24);
    case 0x50f24:return am_call(c,0x43ea4,0x50f2a);
    case 0x50f2a:if(!ofr6_get(c,r.a[6],0x1e,2,value))return false;am_word(r.d[0],value);return am_call(c,0xce02,0x50f34);   // MOVE.W 1e(A6),D0; JSR ce02.
    case 0x50f34:r.a[0]=am_index(r.a[6],0x76);return am_call(c,0x49fca,0x50f3e);                          // LEA 76(A6),A0; JSR 49fca.l.
    case 0x50f3e:return am_call(c,0x49fc6,0x50f44);
    case 0x50f44:return ofr6_grow(c,0x50f52,0x50f50);
    case 0x50f52:r.a[0]=0x5193c;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x50f62);                     // MOVEA.L #5193c,A0; MOVE.W #a,D0; JSR 28ae.l.
    // SCC.B 62(A6) (C of 28ae: Clear -> ff, Set -> 00); MOVE.W #0,D0 (clears C); MOVE.W #0,D1; JSR 49214.l.
    case 0x50f62:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects fr6 caller requires known carry");
        if(!ofr6_put(c,r.a[6],0x62,1,r.carry==AnimationCarryClear?0xffU:0U))return false;
        am_word(r.d[0],0);am_word(r.d[1],0);r.carry=AnimationCarryClear;return am_call(c,0x49214,0x50f74);
    case 0x50f74:return am_call(c,0x491b6,0x50f7a);
    case 0x50f7a:if(!ofr6_put(c,r.a[6],0,4,0x50f80))return false;r.pc=0x50f80;return true;               // MOVE.L #50f80,(A6) (next PC).
    case 0x50f80:return am_call(c,0x43ea4,0x50f86);
    case 0x50f86:if(!ofr6_get(c,r.a[6],0x62,1,value))return false;r.pc=value!=0U?0x50f90U:0x50f8eU;return true;   // TST.B 62(A6); BNE.W 50f90.
    // MOVE.B #30,8c(A6); MOVE.L #50f9c,(A6) (next PC).
    case 0x50f90:if(!ofr6_put(c,r.a[6],0x8c,1,0x30) || !ofr6_put(c,r.a[6],0,4,0x50f9c))return false;r.pc=0x50f9c;return true;
    case 0x50f9c:return am_call(c,0x43ea4,0x50fa2);
    case 0x50fa2:if(!ofr6_add_byte(c,r.a[6],0x8c,0xff,value))return false;r.pc=value!=0U?0x50fb0U:0x50faaU;return true;   // SUBQ.B #1; BNE.W.
    case 0x50faa:if(!ofr6_put(c,r.a[6],0,4,0x50cf6))return false;r.pc=0x50fb0;return true;               // MOVE.L #50cf6,(A6) (write only).
    case 0x50fb2:am_word(r.d[0],0x749);return am_call(c,0x3af8,0x50fbc);                                  // MOVE.W #749,D0; JSR 3af8.l.
    case 0x50fbc:r.a[1]=0x52860;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0x50fcc);
    // BSET.B #2,7e(A6); MOVE.B 19(A6),14(A6); JSR 496c2.l.
    case 0x50fcc:
        if(!ofr6_bit(c,r.a[6],0x7e,2,true) || !ofr6_get(c,r.a[6],0x19,1,value) || !ofr6_put(c,r.a[6],0x14,1,value))return false;
        return am_call(c,0x496c2,0x50fde);
    case 0x50fde:r.a[1]=am_index(r.a[5],0x538e);am_word(r.d[0],0x120);am_word(r.d[1],0xff80);return am_call(c,0x43e04,0x50ff0);
    // MOVE.L #20000,3a(A6); MOVE.L #50ffe,(A6) (next PC).
    case 0x50ff0:if(!ofr6_put(c,r.a[6],0x3a,4,0x20000) || !ofr6_put(c,r.a[6],0,4,0x50ffe))return false;r.pc=0x50ffe;return true;
    // MOVE.W 2e(A6),D0; MOVE.W #b0,D1; SUB.W 2e(A6),D0; SEQ.B D2; BMI.W 51014 / ADDI.W #f,D0.
    case 0x50ffe:
        if(!ofr6_get(c,r.a[6],0x2e,2,value))return false;am_word(r.d[0],value);am_word(r.d[1],0xb0);
        if(!ofr6_get(c,r.a[6],0x2e,2,value))return false;am_word(r.d[0],r.d[0]-value);am_byte(r.d[2],ofr6_w(r.d[0])==0U?0xffU:0U);
        r.pc=(r.d[0]&0x8000U)!=0U?0x51014U:0x51010U;return true;
    case 0x51010:case 0x5102e:am_word(r.d[0],r.d[0]+0xfU);r.pc=r.pc+4U;return true;                      // ADDI.W #f,D0.
    case 0x51020:case 0x51040:am_word(r.d[1],r.d[1]+0xfU);r.pc=r.pc+4U;return true;                      // ADDI.W #f,D1.
    // ASR.W #4,D0; SUB.W 32(A6),D1; SEQ.B D3; BMI.W 51024 / ADDI.W #f,D1.
    case 0x51014:
        am_word(r.d[0],ofr6_asr4(r.d[0]));if(!ofr6_get(c,r.a[6],0x32,2,value))return false;am_word(r.d[1],r.d[1]-value);
        am_byte(r.d[3],ofr6_w(r.d[1])==0U?0xffU:0U);r.pc=(r.d[1]&0x8000U)!=0U?0x51024U:0x51020U;return true;
    // ASR.W #4,D1; SUB.W 36(A6),D0; BMI.W 51032 / ADDI.W #f,D0.
    case 0x51024:
        am_word(r.d[1],ofr6_asr4(r.d[1]));if(!ofr6_get(c,r.a[6],0x36,2,value))return false;am_word(r.d[0],r.d[0]-value);
        r.pc=(r.d[0]&0x8000U)!=0U?0x51032U:0x5102eU;return true;
    // ASR.W #4,D0; ADD.W D0,36(A6); SUB.W 3a(A6),D1; BMI.W 51044 / ADDI.W #f,D1.
    case 0x51032:
        am_word(r.d[0],ofr6_asr4(r.d[0]));if(!ofr6_get(c,r.a[6],0x36,2,value) || !ofr6_put(c,r.a[6],0x36,2,value+r.d[0]))return false;
        if(!ofr6_get(c,r.a[6],0x3a,2,value))return false;am_word(r.d[1],r.d[1]-value);r.pc=(r.d[1]&0x8000U)!=0U?0x51044U:0x51040U;return true;
    // ASR.W #4,D1; ADD.W D1,3a(A6); AND.B D3,D2 (C := 0); BEQ.W 51054 / 51050: ORI.B #1,CCR (C := 1).
    case 0x51044:
        am_word(r.d[1],ofr6_asr4(r.d[1]));if(!ofr6_get(c,r.a[6],0x3a,2,value) || !ofr6_put(c,r.a[6],0x3a,2,value+r.d[1]))return false;
        am_byte(r.d[2],r.d[2]&r.d[3]);r.carry=AnimationCarryClear;r.pc=ofr6_b(r.d[2])==0U?0x51054U:0x51050U;return true;
    case 0x51050:r.carry=AnimationCarrySet;r.pc=0x51054;return true;
    case 0x51054:return ofr6_carry(c,0x51058,0x51064);                                                    // BCS.W 51064 (C of 51044 / 51050).
    case 0x51058:return am_call(c,0x43ea4,0x5105e);
    case 0x5105e:return am_call(c,0x51590,0x51062);                                                       // BSR.W 51590.
    case 0x51064:return am_call(c,0x496c2,0x5106a);
    // MOVE.B #10,a4(A6); MOVE.L #51076,(A6) (next PC).
    case 0x5106a:if(!ofr6_put(c,r.a[6],0xa4,1,0x10) || !ofr6_put(c,r.a[6],0,4,0x51076))return false;r.pc=0x51076;return true;
    case 0x51076:return am_call(c,0x515a2,0x5107a);                                                       // JSR 515a2(PC).
    case 0x5107a:return am_call(c,0x51590,0x5107e);                                                       // BSR.W 51590.
    case 0x5107e:if(!ofr6_get(c,r.a[6],0xa3,1,value))return false;r.pc=value!=0U?0x510c8U:0x51086U;return true;   // TST.B a3(A6); BNE.W 510c8.
    case 0x51086:if(!ofr6_get(c,r.a[6],0x9c,1,value))return false;r.pc=value!=0U?0x510a2U:0x5108eU;return true;   // TST.B 9c(A6); BNE.W 510a2.
    case 0x5108e:r.a[0]=0x52c16;return am_call(c,0x490ba,0x5109a);                                        // LEA 52c16.l,A0; JSR 490ba.l.
    case 0x510a2:r.a[0]=0x52c30;return am_call(c,0x490ba,0x510ae);                                        // LEA 52c30.l,A0; JSR 490ba.l.
    // MOVE.B D0,a3(A6); BRA.W 510b2 (5109a) / fall-through (510ae).
    case 0x5109a:case 0x510ae:if(!ofr6_put(c,r.a[6],0xa3,1,r.d[0]))return false;r.pc=0x510b2;return true;
    case 0x510b2:return am_call(c,0x51178,0x510b6);                                                       // BSR.W 51178.
    case 0x510b6:if(!ofr6_add_byte(c,r.a[6],0xa4,0xff,value))return false;r.pc=value!=0U?0x510c4U:0x510beU;return true;   // SUBQ.B #1; BNE.W.
    case 0x510be:if(!ofr6_put(c,r.a[6],0,4,0x510d0))return false;r.pc=0x510c4;return true;               // MOVE.L #510d0,(A6) (write only).
    case 0x510c4:r.pc=0x510cc;return true;                                                                // BRA.W 510cc.
    case 0x510c8:if(!ofr6_add_byte(c,r.a[6],0xa3,0xff,value))return false;r.pc=0x510cc;return true;      // SUBQ.B #1,a3(A6).
    case 0x510cc:r.pc=0x51574;return true;                                                                // BRA.W 51574.
    // ---- 51178: MOVEA.L #51c36,A0; MOVE.W #a,D0; JSR 28ae.l / MOVE.W #55,D0; JSR 49a84.l / ADDI.W #19a,D0; MOVE.W D0,D1; MOVE.W #120,D0;
    // JSR 49a84.l / ADDI.W #10,D0; JSR 491fe.l / RTS.
    case 0x51178:r.a[0]=0x51c36;am_word(r.d[0],0xa);return am_call(c,0x28ae,0x51188);
    case 0x51188:am_word(r.d[0],0x55);return am_call(c,0x49a84,0x51192);
    case 0x51192:am_word(r.d[0],r.d[0]+0x19aU);am_word(r.d[1],r.d[0]);am_word(r.d[0],0x120);return am_call(c,0x49a84,0x511a2);
    case 0x511a2:am_word(r.d[0],r.d[0]+0x10U);return am_call(c,0x491fe,0x511ac);
    // ---- 51574: JSR 4b54e.l / BTST.B #7,61(A6); BEQ.W 5158a / MOVE.L #511ae,(A6) (write only) / CLR.B 5e(A6); RTS.
    case 0x51574:return am_call(c,0x4b54e,0x5157a);
    case 0x5157a:if(!ofr6_get(c,r.a[6],0x61,1,value))return false;r.pc=(value&0x80U)==0U?0x5158aU:0x51584U;return true;
    case 0x51584:if(!ofr6_put(c,r.a[6],0,4,0x511ae))return false;r.pc=0x5158a;return true;
    case 0x5158a:if(!ofr6_put(c,r.a[6],0x5e,1,0))return false;return am_return(c);
    // ---- 51590: MOVE.W 1e(A6),D0; JSR ce02.l / JSR 49fc6.l / RTS.
    case 0x51590:if(!ofr6_get(c,r.a[6],0x1e,2,value))return false;am_word(r.d[0],value);return am_call(c,0xce02,0x5159a);
    case 0x5159a:return am_call(c,0x49fc6,0x515a0);
    // ---- 515a2: MOVE.L 3a(A6),-(A7); LEA 4411e.l,A0; MOVEQ #0,D0; MOVE.B a2(A6),D0; ADD.W D0,D0; MOVE.W (A0,D0.W),D1; ADDQ.B #8,a2(A6);
    // MOVEQ #0,D0; MOVE.B a2(A6),D0; ADD.W D0,D0; SUB.W (A0,D0.W),D1; NEG.W D1; ADD.W D1,D1; EXT.L D1; LSL.L #8,D1; MOVE.L D1,3a(A6);
    // JSR 43ea4.l.
    case 0x515a2:
        if(!ofr6_get(c,r.a[6],0x3a,4,value) || !am_push(c,4,value))return false;r.a[0]=0x4411e;
        if(!ofr6_get(c,r.a[6],0xa2,1,value))return false;r.d[0]=value;am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[1],value);
        if(!ofr6_add_byte(c,r.a[6],0xa2,8,value))return false;
        if(!ofr6_get(c,r.a[6],0xa2,1,value))return false;r.d[0]=value;am_word(r.d[0],r.d[0]+r.d[0]);
        if(!am_read(c,am_index(r.a[0],r.d[0]),2,value))return false;am_word(r.d[1],r.d[1]-value);
        am_word(r.d[1],0U-r.d[1]);am_word(r.d[1],r.d[1]+r.d[1]);r.d[1]=am_extend_word(r.d[1])<<8;
        if(!ofr6_put(c,r.a[6],0x3a,4,r.d[1]))return false;return am_call(c,0x43ea4,0x515da);
    case 0x515da:if(!am_pop(c,4,value) || !ofr6_put(c,r.a[6],0x3a,4,value))return false;return am_return(c);   // MOVE.L (A7)+,3a(A6); RTS.
    case 0x51608:r.a[0]=0x51626;r.pc=0x515e0;return true;                                                 // LEA 51626(PC),A0; BRA.B 515e0.
    // ---- 703f6: MOVE.L 72(A6),D0; BEQ.W 70406 / MOVEA.L D0,A0; JSR 4ae4a.l / TST.B D0; BEQ.W 70416 / MOVE.W #1a6a,D0; JSR 3af8.l / RTS.
    case 0x703f6:if(!ofr6_get(c,r.a[6],0x72,4,value))return false;r.d[0]=value;r.pc=value==0U?0x70406U:0x703feU;return true;
    case 0x703fe:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0x70406);
    case 0x70406:r.pc=ofr6_b(r.d[0])==0U?0x70416U:0x7040cU;return true;
    case 0x7040c:am_word(r.d[0],0x1a6a);return am_call(c,0x3af8,0x70416);
    // ---- 72978: TST.W 9c(A6); BNE.W 729ac / the bank-window anim (2000d0, LONG 6c) / BRA.W 729d4 / (2000d4, LONG 58).
    case 0x72978:if(!ofr6_get(c,r.a[6],0x9c,2,value))return false;r.pc=value!=0U?0x729acU:0x72980U;return true;
    case 0x72980:return ofr6_bank_anim(c,3,0x2000d0,0x6c,0x729a8);
    case 0x729a8:r.pc=0x729d4;return true;
    case 0x729ac:return ofr6_bank_anim(c,0xb,0x2000d4,0x58,0x729d4);
    // MOVE.L #0,64(A6); MOVE.L #729e2,(A6) (next PC) / JSR 4bfa4.l / JSR 49fc6.l / BCC.W 729f8 / MOVE.L #70c0c,(A6) (write only).
    case 0x729d4:if(!ofr6_put(c,r.a[6],0x64,4,0) || !ofr6_put(c,r.a[6],0,4,0x729e2))return false;r.pc=0x729e2;return true;
    case 0x729e2:return am_call(c,0x4bfa4,0x729e8);
    case 0x729e8:return am_call(c,0x49fc6,0x729ee);
    case 0x729ee:return ofr6_carry(c,0x729f8,0x729f2);                                                    // BCC.W 729f8 (C of 49fc6).
    case 0x729f2:if(!ofr6_put(c,r.a[6],0,4,0x70c0c))return false;r.pc=0x729f8;return true;
    case 0x729f8:return am_call(c,0x703f6,0x729fc);                                                       // JSR 703f6(PC).
    // BTST.B #7,15(A6); BNE.W 72a0c / MOVE.L #71c90,(A6) (write only) / BRA.W 72dd2.
    case 0x729fc:if(!ofr6_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&0x80U)!=0U?0x72a0cU:0x72a06U;return true;
    case 0x72a06:if(!ofr6_put(c,r.a[6],0,4,0x71c90))return false;r.pc=0x72a0c;return true;
    case 0x72a0c:r.pc=0x72dd2;return true;
    // ---- d764a (28ae child value of stage_area d760a): MOVE.W #ea,20(A6); then MOVE.W #d19 | d23 | d24,D0; MOVE.B #0,D1; JSR 8ebe.l.
    case 0xd764a:if(!ofr6_put(c,r.a[6],0x20,2,0xea))return false;am_word(r.d[0],0xd19);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xd765e);
    case 0xd765e:am_word(r.d[0],0xd23);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xd766c);
    case 0xd766c:am_word(r.d[0],0xd24);am_byte(r.d[1],0);return am_call(c,0x8ebe,0xd767a);
    // MOVE.B 19(A6),14(A6); MOVE.W #ffff,68(A6); MOVE.W #ffff,1e(A6); MOVE.L #d7692,(A6) (next PC).
    case 0xd767a:
        if(!ofr6_get(c,r.a[6],0x19,1,value) || !ofr6_put(c,r.a[6],0x14,1,value) || !ofr6_put(c,r.a[6],0x68,2,0xffff) ||
           !ofr6_put(c,r.a[6],0x1e,2,0xffff) || !ofr6_put(c,r.a[6],0,4,0xd7692))return false;
        r.pc=0xd7692;return true;
    case 0xd7692:return am_call(c,0x4855c,0xd7698);
    case 0xd7698:return ofr6_carry(c,0xd769c,0xd76a6);                                                    // BCS.W d76a6 (C of 4855c).
    case 0xd769c:case 0xd76bc:case 0xd7700:                                                               // TST.W 5df8(A5); BEQ.W d7714.
        if(!ofr6_get(c,r.a[5],0x5df8,2,value))return false;
        r.pc=value==0U?0xd7714U:(r.pc==0xd769cU?0xd76a4U:(r.pc==0xd76bcU?0xd76c4U:0xd7708U));return true;
    // MOVE.L 5418(A5),76(A6); MOVE.L #d76b2,(A6) (next PC).
    case 0xd76a6:
        if(!ofr6_get(c,r.a[5],0x5418,4,value) || !ofr6_put(c,r.a[6],0x76,4,value) || !ofr6_put(c,r.a[6],0,4,0xd76b2))return false;
        r.pc=0xd76b2;return true;
    case 0xd76b2:return am_call(c,0x4855c,0xd76b8);
    case 0xd76b8:return ofr6_carry(c,0xd76f4,0xd76bc);                                                    // BCC.W d76f4 (C of 4855c).
    // SUBQ.W #1,5df8(A5); MOVE.W 5418(A5),D0; MOVE.W 76(A6),D1; MOVE.W D0,76(A6); CMP.W D0,D1; BEQ.W d76e0 / MOVE.W #96,5df8(A5).
    case 0xd76c4:
        if(!ofr6_get(c,r.a[5],0x5df8,2,value) || !ofr6_put(c,r.a[5],0x5df8,2,value-1U) || !ofr6_get(c,r.a[5],0x5418,2,value))return false;
        am_word(r.d[0],value);if(!ofr6_get(c,r.a[6],0x76,2,value))return false;am_word(r.d[1],value);
        if(!ofr6_put(c,r.a[6],0x76,2,r.d[0]))return false;r.pc=ofr6_w(r.d[1])==ofr6_w(r.d[0])?0xd76e0U:0xd76daU;return true;
    case 0xd76da:case 0xd76ec:if(!ofr6_put(c,r.a[5],0x5df8,2,0x96))return false;r.pc=r.pc+6U;return true;   // MOVE.W #96,5df8(A5).
    case 0xd76e0:return am_call(c,0xe9148,0xd76e6);
    case 0xd76e6:r.pc=ofr6_w(r.d[0])==0U?0xd76f2U:0xd76ecU;return true;                                   // TST.W D0; BEQ.W d76f2.
    // MOVE.W #1,5df8(A5); MOVE.L #d7700,(A6) (next PC).
    case 0xd76f4:if(!ofr6_put(c,r.a[5],0x5df8,2,1) || !ofr6_put(c,r.a[6],0,4,0xd7700))return false;r.pc=0xd7700;return true;
    case 0xd7708:return am_call(c,0x4855c,0xd770e);
    case 0xd770e:return ofr6_carry(c,0xd7712,0xd7714);                                                    // BCS.W d7714 (C of 4855c).
    // MOVE.W #4b,5df8(A5); MOVE.B #2,8c(A6); LEA 10ddec.l,A0; WORDs 78 7a 7c := (A0) 2(A0) 4(A0); LEA 6(A0),A0; WORDs 7e 80 82 := (A0) 2(A0)
    // 4(A0); A1 := LONG d75ce + 4 * WORD (A0); MOVE.W #100,D0; LEA 84(A6),A0; JSR 49f96.l.
    case 0xd7714:
        if(!ofr6_put(c,r.a[5],0x5df8,2,0x4b) || !ofr6_put(c,r.a[6],0x8c,1,2))return false;r.a[0]=0x10ddec;
        for(unsigned int k=0;k<2;++k){
            for(unsigned int i=0;i<3;++i){if(!am_read(c,r.a[0]+2U*i,2,value) || !ofr6_put(c,r.a[6],0x78U+6U*k+2U*i,2,value))return false;}
            if(k==0U)r.a[0]=r.a[0]+6U;}
        if(!am_read(c,r.a[0],2,value) || !ofr6_table_d75ce(c,value))return false;
        am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x84);return am_call(c,0x49f96,0xd7766);
    // d7766 (installed value / return PC): A1 := LONG d75ce + 4 * WORD 78; MOVE.W #100,D0; JSR 49f8c.l (A0 kept).
    case 0xd7766:if(!ofr6_get(c,r.a[6],0x78,2,value) || !ofr6_table_d75ce(c,value))return false;am_word(r.d[0],0x100);return am_call(c,0x49f8c,0xd7780);
    case 0xd7780:
        if(!ofr6_get(c,r.a[6],0x7e,2,value) || !ofr6_table_d75ce(c,value))return false;am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x84);
        return am_call(c,0x49f96,0xd779e);
    // MOVE.W 78(A6),D0; OR.W 7e(A6),D0; BEQ.W d77b4 / MOVE.W #1ac1,D0; JSR 3af8.l.
    case 0xd779e:
        if(!ofr6_get(c,r.a[6],0x78,2,value))return false;am_word(r.d[0],value);if(!ofr6_get(c,r.a[6],0x7e,2,value))return false;
        am_word(r.d[0],r.d[0]|value);r.pc=ofr6_w(r.d[0])==0U?0xd77b4U:0xd77aaU;return true;
    case 0xd77aa:am_word(r.d[0],0x1ac1);return am_call(c,0x3af8,0xd77b4);
    case 0xd77b4:if(!ofr6_put(c,r.a[6],0,4,0xd77ba))return false;r.pc=0xd77ba;return true;               // MOVE.L #d77ba,(A6) (next PC).
    case 0xd77ba:return am_call(c,0x16ed2,0xd77c0);
    case 0xd77c0:if(!ofr6_get(c,r.a[6],0x78,2,value))return false;r.pc=value==0U?0xd77e0U:0xd77c8U;return true;   // TST.W 78(A6); BEQ.W d77e0.
    // MOVE.W 7a(A6),42(A6); MOVE.W 7c(A6),46(A6); JSR 49fc6.l.
    case 0xd77c8:
        if(!ofr6_get(c,r.a[6],0x7a,2,value) || !ofr6_put(c,r.a[6],0x42,2,value) || !ofr6_get(c,r.a[6],0x7c,2,value) ||
           !ofr6_put(c,r.a[6],0x46,2,value))return false;
        return am_call(c,0x49fc6,0xd77da);
    // SCS.B -(A7) (C of 49fc6: Set -> ff, Clear -> 00; A7 -= 2); BRA.W d77e4 (C kept).
    case 0xd77da:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects fr6 caller requires known carry");
        if(!am_push(c,1,r.carry==AnimationCarrySet?0xffU:0U))return false;r.pc=0xd77e4;return true;
    case 0xd77e0:if(!am_push(c,1,0xff))return false;r.pc=0xd77e4;return true;                            // MOVE.B #ff,-(A7).
    case 0xd77e4:if(!ofr6_get(c,r.a[6],0x7e,2,value))return false;r.pc=value==0U?0xd7808U:0xd77ecU;return true;   // TST.W 7e(A6); BEQ.W d7808.
    // MOVE.W 80(A6),42(A6); MOVE.W 82(A6),46(A6); LEA 84(A6),A0; JSR 49fca.l.
    case 0xd77ec:
        if(!ofr6_get(c,r.a[6],0x80,2,value) || !ofr6_put(c,r.a[6],0x42,2,value) || !ofr6_get(c,r.a[6],0x82,2,value) ||
           !ofr6_put(c,r.a[6],0x46,2,value))return false;
        r.a[0]=am_index(r.a[6],0x84);return am_call(c,0x49fca,0xd7802);
    // SCS.B D0 (C of 49fca); BRA.W d780c (C kept).
    case 0xd7802:
        if(r.carry==AnimationCarryUnknown)return am_error(c,"objects fr6 caller requires known carry");
        am_byte(r.d[0],r.carry==AnimationCarrySet?0xffU:0U);r.pc=0xd780c;return true;
    case 0xd7808:am_byte(r.d[0],0xff);r.pc=0xd780c;return true;                                          // MOVE.B #ff,D0.
    case 0xd780c:if(!am_pop(c,1,value))return false;am_byte(r.d[0],r.d[0]&value);r.pc=ofr6_b(r.d[0])==0U?0xd7826U:0xd7812U;return true;   // AND.B (A7)+,D0.
    // MOVE.L #d7766,(A6) (write only); SUBQ.B #1,8c(A6); BNE.W d7826 / MOVE.L #d76a6,(A6) (write only).
    case 0xd7812:
        if(!ofr6_put(c,r.a[6],0,4,0xd7766) || !ofr6_add_byte(c,r.a[6],0x8c,0xff,value))return false;r.pc=value!=0U?0xd7826U:0xd7820U;return true;
    case 0xd7820:if(!ofr6_put(c,r.a[6],0,4,0xd76a6))return false;r.pc=0xd7826;return true;
    // ---- e625e: BTST.B #0,D0; BEQ.W e6270 / LEA 10de18.l,A1; BSR.W e6284 / BTST.B #1,D0; BEQ.W e6282 / LEA 10de20.l,A1; BSR.W e6284 / RTS.
    case 0xe625e:r.pc=(r.d[0]&1U)==0U?0xe6270U:0xe6266U;return true;
    case 0xe6266:r.a[1]=0x10de18;return am_call(c,0xe6284,0xe6270);
    case 0xe6270:r.pc=(r.d[0]&2U)==0U?0xe6282U:0xe6278U;return true;
    case 0xe6278:r.a[1]=0x10de20;return am_call(c,0xe6284,0xe6282);
    // e6284: LEA e625e(PC),A2; LEA 2(A0),A0; ADDI.B #0,D0 (X := 0); ABCD -(A0),-(A1) twice; ABCD -(A2),-(A1) twice; BCC.W e62a6.
    case 0xe6284:{
        bool extend=false;r.a[2]=0xe625e;r.a[0]=r.a[0]+2U;
        for(unsigned int k=0;k<4;++k){if(!ofr6_abcd_step(c,k<2U?r.a[0]:r.a[2],r.a[1],extend))return false;}
        r.pc=extend?0xe629cU:0xe62a6U;return true;}
    // MOVE.W #9999,(A1); MOVE.B #99,2(A1).
    case 0xe629c:if(!am_write(c,r.a[1],2,0x9999) || !am_write(c,r.a[1]+2U,1,0x99))return false;r.pc=0xe62a6;return true;
    // ---- e9148: MOVEQ #0,D0; MOVE.B 5e3c(A5),D0; RTS.
    case 0xe9148:if(!ofr6_get(c,r.a[5],0x5e3c,1,value))return false;r.d[0]=value;return am_return(c);
    default:break;
    }
    return am_error(c,"unsupported animation objects fr6 PC");
}
}
