#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands (MOVE.L #, d(PC,Xn) tables).
const std::uint32_t SV_EVENT_BASE=0x10d38e;                         // e9150 MOVE.L #10d38e,3e(A6)
const std::uint32_t SV_CALLBACK=0xe9176;                            // e9170 MOVE.L #e9176,(A6)
const std::uint32_t SV_OPCODES=0xe91e4;                             // e91ba JSR e91e4(PC,D7.W)
const std::uint32_t SV_OPERATORS=0xe97e4;                           // e97e0 JMP e97e4(PC,D1.W)
// Evaluator return PCs whose first instruction branches on the Z left by e98ea MOVE.B (A7)+,D0 (F3 main decision 3).
const std::uint32_t SV_EVAL_CHILD1=0xe9396,SV_EVAL_CHILD2=0xe939e,SV_EVAL_OP05=0xe94c0,SV_EVAL_OP0B=0xe96b0;
// d16(A5) operands use the live A5 (negative displacements are written as their 16-bit two's complement).
bool sv_read(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[5],displacement),size,value);
}
bool sv_write(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[5],displacement),size,value);
}
// MOVE/CLR/Scc to d16(An) (CLR and Scc are modeled as a write like the other units).
bool sv_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
bool sv_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
// ADDQ.B #1,<ea>: BYTE read-modify-write, carry out discarded.
bool sv_increment(AnimationMachineContext& c,std::uint32_t address) {
    std::uint32_t value=0;if(!am_read(c,address,1,value))return false;
    return am_write(c,address,1,(value+1U)&255U);
}
// Signed comparisons through the sign-flipped unsigned value (no signed overflow).
bool sv_less_word(std::uint32_t a,std::uint32_t b) {return ((a^0x8000U)&65535U)<((b^0x8000U)&65535U);}
bool sv_less_byte(std::uint32_t a,std::uint32_t b) {return ((a^0x80U)&255U)<((b^0x80U)&255U);}
// Consumers of a C returned by 49392: BCC clear_pc, otherwise set_pc.
bool sv_carry(AnimationMachineContext& c,std::uint32_t clear_pc,std::uint32_t set_pc) {
    if(c.s.carry==AnimationCarryUnknown)return am_error(c,"stage event caller requires known carry");
    c.s.pc=c.s.carry==AnimationCarryClear?clear_pc:set_pc;return true;
}
// MOVE.B #ff,81(A6); RTS.
bool sv_frame_end(AnimationMachineContext& c) {
    if(!sv_put(c,c.s.a[6],0x81,1,0xff))return false;return am_return(c);
}
// MOVE.B Dn/#imm/<ea>,-(A7): A7-2, one BYTE (F1c rule).
bool sv_push(AnimationMachineContext& c,std::uint32_t value) {
    if(!am_push(c,1,value&255U))return false;c.s.pc=0xe97c8;return true;
}
// MOVE.B (A7)+,D0: one BYTE, A7+2 (only the low BYTE of D0 is written).
bool sv_pop(AnimationMachineContext& c) {
    std::uint32_t value=0;if(!am_pop(c,1,value))return false;am_byte(c.s.d[0],value);return true;
}
// e989c..e98c4: MOVE.B (A7)+,D0; CMP.B (A7),D0; Scc.B (A7) (D0-(A7), signed for GT/GE/LT/LE); BRA e97c8.
bool sv_compare(AnimationMachineContext& c,unsigned int kind) {
    AnimationMachineState& r=c.s;std::uint32_t top=0;
    if(!sv_pop(c) || !am_read(c,r.a[7],1,top))return false;
    const std::uint32_t a=r.d[0]&255U,b=top&255U;bool set=false;
    if(kind==0)set=a==b;
    else if(kind==1)set=sv_less_byte(b,a);
    else if(kind==2)set=!sv_less_byte(a,b);
    else if(kind==3)set=sv_less_byte(a,b);
    else set=!sv_less_byte(b,a);
    if(!am_write(c,r.a[7],1,set?0xffU:0U))return false;r.pc=0xe97c8;return true;
}
// e98ce/e98d8: MOVE.B (A7)+,D0; SNE.B D0; AND.B/OR.B D0,(A7); BRA e97c8.
bool sv_logic(AnimationMachineContext& c,bool use_or) {
    AnimationMachineState& r=c.s;std::uint32_t top=0;
    if(!sv_pop(c))return false;am_byte(r.d[0],(r.d[0]&255U)?0xffU:0U);
    if(!am_read(c,r.a[7],1,top))return false;
    const std::uint32_t value=use_or?(top|r.d[0]):(top&r.d[0]);
    if(!am_write(c,r.a[7],1,value&255U))return false;r.pc=0xe97c8;return true;
}
// 4851e/4853a and the 48546..48556 tail: MOVE.W 42(A0),Dx; MOVE.W 46(A0),Dy.
bool sv_position(AnimationMachineContext& c,std::uint32_t& x,std::uint32_t& y) {
    std::uint32_t value=0;
    if(!sv_get(c,c.s.a[0],0x42,2,value))return false;am_word(x,value);
    if(!sv_get(c,c.s.a[0],0x46,2,value))return false;am_word(y,value);return true;
}
// e930c/e9320: ADDQ.W #1,Dn; SCS.B low(A5); SCC.B high(A5) (C = carry out of the WORD).
bool sv_edge(AnimationMachineContext& c,std::uint32_t& d,std::uint32_t low,std::uint32_t high) {
    const bool carry=(d&65535U)==65535U;am_word(d,(d&65535U)+1U);
    return sv_write(c,low,1,carry?0xffU:0U) && sv_write(c,high,1,carry?0U:0xffU);
}
}
// Stage event F3a: the event node callbacks e9150 (initialisation, falls into e9176) and e9176 (every frame) with the
// e9204 class count and screen flags (e932c, e9298 with 48502), the main stream loop e9198..e91e2 with the e91e4 opcode
// table (eight BRA.W slots), the opcode 00..07 handlers e9444..e94fe, the length advance e9768 and the expression
// evaluator e97c8..e98ee with its e97e4 operator table (34 BRA.W slots), and the helpers 1a910 and 1a93e. Existing
// executors called: cleanup 43e38 (through its 43e34 LEA entry), frame_helpers 49392 (known C, consumed by e9248/e9258) and input 4d7a6. e94fe (opcodes 08..0f, F3b) is a
// boundary without an executor (e91ac BSR e94fe). The e91ba index is bounded by the original (e919c/e91a4) and followed
// as the computed PC e91e4+D7.W; the e97e0 index has no upper bound and is followed as the computed PC e97e4+D1.W (F1
// main decision 3: a target that is not a block start is unsupported; D1.W is a multiple of 4). The evaluator stack is a
// BYTE stack on A7 (MOVE.B -(A7)/(A7)+ move A7 by 2 and touch one BYTE). e98ea pops the result BYTE into D0 and the
// return LONG; the Z of that MOVE is consumed by the first instruction of the four known return PCs, so their branch is
// evaluated in the e98ea block (e9396/e939e BEQ e9428, e94c0 BNE e9768, e96b0 BEQ e96b8) and those PCs are bundled (no
// direct entry); any other return LONG is followed as is (F3 main decision 3). ROM data (event streams and expressions)
// is read through the live bus; all d16(A5) operands use the live A5. The e9204 list walk and the stream loop have no
// extra limit (block budget only). Writes outside work RAM are checked errors.
bool animation_stage_event_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // 1a910: MOVE.W D0,5442(A5); MOVE.W D1,5440(A5); RTS.
    case 0x1a910:
        if(!sv_write(c,0x5442,2,r.d[0]&65535U) || !sv_write(c,0x5440,2,r.d[1]&65535U))return false;return am_return(c);
    case 0x1a93e:r.pc=(r.d[0]&255U)?0x1a944:0x1a94c;return true;              // TST.B D0; BEQ 1a94c.
    case 0x1a944:if(!sv_write(c,0x544c,2,0x200))return false;return am_return(c); // MOVE.W #200,544c(A5); RTS.
    case 0x1a94c:if(!sv_write(c,0x544c,2,0))return false;return am_return(c);     // CLR.W 544c(A5); RTS.

    // 48502: MOVE.W #a0,D0; MOVE.W #180,D1; MOVE.W D0,D2; MOVE.W D1,D3; MOVEQ #0,D7; LEA -7348(A5),A0;
    // BTST #0,568e(A5); BEQ 4852a.
    case 0x48502:
        am_word(r.d[0],0xa0);am_word(r.d[1],0x180);am_word(r.d[2],0xa0);am_word(r.d[3],0x180);r.d[7]=0;
        r.a[0]=am_index(r.a[5],0x8cb8);if(!sv_read(c,0x568e,1,value))return false;
        r.pc=(value&1U)?0x4851e:0x4852a;return true;
    // MOVE.W #ffff,D7; MOVE.W 42(A0),D0; MOVE.W 46(A0),D1.
    case 0x4851e:am_word(r.d[7],0xffff);if(!sv_position(c,r.d[0],r.d[1]))return false;r.pc=0x4852a;return true;
    // CLR.B D7; LEA -7258(A5),A0; BTST #1,568e(A5); BEQ 48546.
    case 0x4852a:
        am_byte(r.d[7],0);r.a[0]=am_index(r.a[5],0x8da8);if(!sv_read(c,0x568e,1,value))return false;
        r.pc=(value&2U)?0x4853a:0x48546;return true;
    // MOVE.B #ff,D7; MOVE.W 42(A0),D2; MOVE.W 46(A0),D3.
    case 0x4853a:am_byte(r.d[7],0xff);if(!sv_position(c,r.d[2],r.d[3]))return false;r.pc=0x48546;return true;
    case 0x48546:r.pc=(r.d[7]&0x80U)?0x48550:0x4854c;return true;                 // TST.B D7; BMI 48550.
    case 0x4854c:am_word(r.d[2],r.d[0]);am_word(r.d[3],r.d[1]);r.pc=0x48550;return true; // MOVE.W D0,D2; MOVE.W D1,D3.
    case 0x48550:r.pc=(r.d[7]&0x8000U)?0x4855a:0x48556;return true;               // TST.W D7; BMI 4855a.
    case 0x48556:am_word(r.d[0],r.d[2]);am_word(r.d[1],r.d[3]);r.pc=0x4855a;return true; // MOVE.W D2,D0; MOVE.W D3,D1.
    case 0x4855a:return am_return(c); // RTS.

    // e9150 (node callback): MOVE.L #10d38e,3e(A6); CLR.W 7e(A6); CLR.B 80(A6); CLR.B 81(A6); MOVE.W #a0,5e46(A5);
    // MOVE.W #80,5e48(A5); MOVE.L #e9176,(A6) (then e9176).
    case 0xe9150:
        if(!sv_put(c,r.a[6],0x3e,4,SV_EVENT_BASE) || !sv_put(c,r.a[6],0x7e,2,0) || !sv_put(c,r.a[6],0x80,1,0) ||
           !sv_put(c,r.a[6],0x81,1,0) || !sv_write(c,0x5e46,2,0xa0) || !sv_write(c,0x5e48,2,0x80) ||
           !am_write(c,r.a[6],4,SV_CALLBACK))return false;
        r.pc=0xe9176;return true;
    case 0xe9176:return am_call(c,0xe9204,0xe917a); // BSR e9204.
    // MOVE.L 53bc(A5),2e(A6); MOVE.L 53c0(A5),32(A6); JSR 43e34.L.
    case 0xe917a:
        if(!sv_read(c,0x53bc,4,value) || !sv_put(c,r.a[6],0x2e,4,value))return false;
        if(!sv_read(c,0x53c0,4,value) || !sv_put(c,r.a[6],0x32,4,value))return false;
        return am_call(c,0x43e34,0xe918c);
    // MOVE.L 76(A6),D7; BNE e9196.
    case 0xe918c:if(!sv_get(c,r.a[6],0x76,4,value))return false;r.d[7]=value;r.pc=value?0xe9196:0xe9194;return true;
    case 0xe9194:return am_return(c);               // RTS (stream null: the bank is not restored).
    case 0xe9196:r.a[0]=r.d[7];r.pc=0xe9198;return true; // MOVEA.L D7,A0.
    // MOVEQ #0,D7; MOVE.B (A0),D7; CMPI.B #10,D7; BCC e91c6.
    case 0xe9198:r.d[7]=0;if(!am_read(c,r.a[0],1,value))return false;am_byte(r.d[7],value);r.pc=(value&255U)>=0x10U?0xe91c6:0xe91a4;return true;
    case 0xe91a4:r.pc=(r.d[7]&255U)<8U?0xe91b8:0xe91ac;return true; // CMPI.B #8,D7; BCS e91b8.
    case 0xe91ac:return am_call(c,0xe94fe,0xe91b0);                   // BSR e94fe (F3b boundary).
    case 0xe91b0:r.d[7]=r.a[0];if(!sv_put(c,r.a[6],0x76,4,r.d[7]))return false;r.pc=0xe9198;return true; // MOVE.L A0,D7; MOVE.L D7,76(A6); BRA e9198.
    // LSL.W #2,D7; JSR e91e4(PC,D7.W) (computed PC; the index is bounded by e919c/e91a4).
    case 0xe91b8:am_word(r.d[7],(r.d[7]&65535U)<<2);return am_call(c,am_index(SV_OPCODES,r.d[7]),0xe91be);
    // BCLR #0,81(A6); BEQ e9198 (the previous bit 0 was clear).
    case 0xe91be:
        if(!sv_get(c,r.a[6],0x81,1,value) || !sv_put(c,r.a[6],0x81,1,value&0xfeU))return false;
        r.pc=(value&1U)?0xe91c6:0xe9198;return true;
    // MOVE.L A0,D7; MOVE.L D7,76(A6); MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; RTS.
    case 0xe91c6:
        r.d[7]=r.a[0];if(!sv_put(c,r.a[6],0x76,4,r.d[7]) || !am_zero_bank(c))return false;return am_return(c);
    // e91e4 opcode table: eight BRA.W slots (opcodes 00..07).
    case 0xe91e4:r.pc=0xe9444;return true;
    case 0xe91e8:r.pc=0xe9458;return true;
    case 0xe91ec:r.pc=0xe948c;return true;
    case 0xe91f0:r.pc=0xe949c;return true;
    case 0xe91f4:r.pc=0xe94a8;return true;
    case 0xe91f8:r.pc=0xe94b8;return true;
    case 0xe91fc:r.pc=0xe94d0;return true;
    case 0xe9200:r.pc=0xe94f6;return true;

    // e9204: MOVEQ #0,D0; LEA 5e30(A5),A0; MOVE.L D0,(A0)+ (three times); LEA 5e30(A5),A0; LEA -740c(A5),A1; BRA e922c.
    case 0xe9204:
        r.d[0]=0;r.a[0]=am_index(r.a[5],0x5e30);
        for(unsigned int i=0;i<3;++i){if(!am_write(c,r.a[0],4,0))return false;r.a[0]+=4U;}
        r.a[0]=am_index(r.a[5],0x5e30);r.a[1]=am_index(r.a[5],0x8bf4);r.pc=0xe922c;return true;
    // MOVE.B 6b(A1),D0; CMPI.W #c,D0; BCC e922c (unsigned WORD).
    case 0xe921c:
        if(!sv_get(c,r.a[1],0x6b,1,value))return false;am_byte(r.d[0],value);r.pc=(r.d[0]&65535U)>=0xcU?0xe922c:0xe9228;return true;
    case 0xe9228:if(!sv_increment(c,am_index(r.a[0],r.d[0])))return false;r.pc=0xe922c;return true; // ADDQ.B #1,(A0,D0.W).
    // MOVEA.L 8(A1),A1; TST.W 10(A1); BNE e921c.
    case 0xe922c:
        if(!sv_get(c,r.a[1],8,4,value))return false;r.a[1]=value;
        if(!sv_get(c,r.a[1],0x10,2,value))return false;r.pc=(value&65535U)?0xe921c:0xe9236;return true;
    case 0xe9236:return am_call(c,0xe932c,0xe923a); // BSR e932c.
    case 0xe923a:return am_call(c,0xe9298,0xe923e); // BSR e9298.
    case 0xe923e:r.d[1]=0;r.d[0]=0;return am_call(c,0x49392,0xe9248); // MOVEQ #0,D1; MOVEQ #0,D0; JSR 49392.L.
    case 0xe9248:return sv_carry(c,0xe9250,0xe924c);                    // BCC e9250.
    case 0xe924c:am_byte(r.d[1],(r.d[1]|1U)&255U);r.pc=0xe9250;return true; // ORI.B #1,D1.
    case 0xe9250:r.d[0]=1;return am_call(c,0x49392,0xe9258);           // MOVEQ #1,D0; JSR 49392.L.
    case 0xe9258:return sv_carry(c,0xe9260,0xe925c);                    // BCC e9260.
    case 0xe925c:am_byte(r.d[1],(r.d[1]|2U)&255U);r.pc=0xe9260;return true; // ORI.B #2,D1.
    // MOVE.B D1,D0; CMPI.B #3,D0; SEQ.B 5e3e(A5); SNE.B 5e3d(A5); CLR.B 5e3f(A5); MOVEQ #0,D0; JSR 4d7a6.L.
    case 0xe9260:{
        am_byte(r.d[0],r.d[1]);const bool both=(r.d[0]&255U)==3U;
        if(!sv_write(c,0x5e3e,1,both?0xffU:0U) || !sv_write(c,0x5e3d,1,both?0U:0xffU) || !sv_write(c,0x5e3f,1,0))return false;
        r.d[0]=0;return am_call(c,0x4d7a6,0xe927a);}
    case 0xe927a:r.pc=(r.d[0]&255U)?0xe9280:0xe9284;return true; // TST.B D0; BEQ e9284.
    case 0xe9280:if(!sv_increment(c,am_index(r.a[5],0x5e3f)))return false;r.pc=0xe9284;return true; // ADDQ.B #1,5e3f(A5).
    case 0xe9284:r.d[0]=1;return am_call(c,0x4d7a6,0xe928c); // MOVEQ #1,D0; JSR 4d7a6.L.
    case 0xe928c:r.pc=(r.d[0]&255U)?0xe9292:0xe9296;return true; // TST.B D0; BEQ e9296.
    case 0xe9292:if(!sv_increment(c,am_index(r.a[5],0x5e3f)))return false;r.pc=0xe9296;return true; // ADDQ.B #1,5e3f(A5).
    case 0xe9296:return am_return(c); // RTS.
    // e9298: CLR.B 5e40(A5) (twice); CLR.B 5e41/5e42/5e44/5e43/5e45(A5); JSR 48502.L.
    case 0xe9298:
        if(!sv_write(c,0x5e40,1,0) || !sv_write(c,0x5e40,1,0) || !sv_write(c,0x5e41,1,0) || !sv_write(c,0x5e42,1,0) ||
           !sv_write(c,0x5e44,1,0) || !sv_write(c,0x5e43,1,0) || !sv_write(c,0x5e45,1,0))return false;
        return am_call(c,0x48502,0xe92ba);
    case 0xe92ba:r.d[6]=0;r.pc=(r.d[7]&65535U)?0xe92c2:0xe932a;return true; // MOVEQ #0,D6; TST.W D7; BEQ e932a.
    // MOVE.W 53a2/53a6(A5),D4/D5 and SUB.W from D0..D3; MOVE.W 53bc/53c0(A5),D4/D5 and SUB.W again; MOVEQ #0,D4/D5;
    // CMP.W 5e46/5e48(A5),D0/D1 with SLT.B D4/D5; EXT.W D4/D5; CMP.W 5e46/5e48(A5),D2/D3 with SLT.B D4/D5;
    // TST.W D4; SEQ.B 5e41(A5); BEQ e9316.
    case 0xe92c2:{
        std::uint32_t width=0,height=0;
        for(unsigned int pass=0;pass<2;++pass){
            if(!sv_read(c,pass?0x53bc:0x53a2,2,value) || !sv_read(c,pass?0x53c0:0x53a6,2,other))return false;
            am_word(r.d[4],value);am_word(r.d[5],other);
            am_word(r.d[0],(r.d[0]&65535U)-(r.d[4]&65535U));am_word(r.d[1],(r.d[1]&65535U)-(r.d[5]&65535U));
            am_word(r.d[2],(r.d[2]&65535U)-(r.d[4]&65535U));am_word(r.d[3],(r.d[3]&65535U)-(r.d[5]&65535U));}
        r.d[4]=0;r.d[5]=0;
        if(!sv_read(c,0x5e46,2,width))return false;
        am_byte(r.d[4],sv_less_word(r.d[0],width)?0xffU:0U);
        if(!sv_read(c,0x5e48,2,height))return false;
        am_byte(r.d[5],sv_less_word(r.d[1],height)?0xffU:0U);
        am_word(r.d[4],(r.d[4]&0x80U)?0xffffU:0U);am_word(r.d[5],(r.d[5]&0x80U)?0xffffU:0U);
        if(!sv_read(c,0x5e46,2,width))return false;
        am_byte(r.d[4],sv_less_word(r.d[2],width)?0xffU:0U);
        if(!sv_read(c,0x5e48,2,height))return false;
        am_byte(r.d[5],sv_less_word(r.d[3],height)?0xffU:0U);
        if(!sv_write(c,0x5e41,1,(r.d[4]&65535U)?0U:0xffU))return false;
        r.pc=(r.d[4]&65535U)?0xe930c:0xe9316;return true;}
    case 0xe930c:if(!sv_edge(c,r.d[4],0x5e40,0x5e42))return false;r.pc=0xe9316;return true; // ADDQ.W #1,D4; SCS.B 5e40; SCC.B 5e42.
    // TST.W D5; SEQ.B 5e44(A5); BEQ e932a.
    case 0xe9316:if(!sv_write(c,0x5e44,1,(r.d[5]&65535U)?0U:0xffU))return false;r.pc=(r.d[5]&65535U)?0xe9320:0xe932a;return true;
    case 0xe9320:if(!sv_edge(c,r.d[5],0x5e43,0x5e45))return false;r.pc=0xe932a;return true; // ADDQ.W #1,D5; SCS.B 5e43; SCC.B 5e45.
    case 0xe932a:return am_return(c); // RTS.
    // e932c: MOVE.L A0,-(A7); MOVE.W D0,-(A7); LEA 5e30(A5),A0; MOVEQ #0,D0; ADD.B (A0)+,D0 (eight times);
    // MOVE.B D0,5e3c(A5); MOVE.W (A7)+,D0; MOVEA.L (A7)+,A0; RTS (the MOVEQ leaves the upper WORD of D0 zero).
    case 0xe932c:{
        if(!am_push(c,4,r.a[0]) || !am_push(c,2,r.d[0]&65535U))return false;
        r.a[0]=am_index(r.a[5],0x5e30);r.d[0]=0;
        for(unsigned int i=0;i<8;++i){if(!am_read(c,r.a[0],1,value))return false;r.a[0]+=1U;am_byte(r.d[0],(r.d[0]+value)&255U);}
        if(!sv_write(c,0x5e3c,1,r.d[0]&255U))return false;
        if(!am_pop(c,2,value))return false;am_word(r.d[0],value);
        if(!am_pop(c,4,value))return false;r.a[0]=value;return am_return(c);}

    // e9444 (opcode 00): MOVE.W 5418(A5),D0; CMP.W 2(A0),D0; BCC e9768 (unsigned).
    case 0xe9444:
        if(!sv_read(c,0x5418,2,value))return false;am_word(r.d[0],value);if(!sv_get(c,r.a[0],2,2,other))return false;
        r.pc=(value&65535U)>=(other&65535U)?0xe9768:0xe9450;return true;
    case 0xe9450:return sv_frame_end(c); // MOVE.B #ff,81(A6); RTS.
    // e9458 (opcode 01): the same wait, then e946c.
    case 0xe9458:
        if(!sv_read(c,0x5418,2,value))return false;am_word(r.d[0],value);if(!sv_get(c,r.a[0],2,2,other))return false;
        r.pc=(value&65535U)>=(other&65535U)?0xe946c:0xe9464;return true;
    case 0xe9464:return sv_frame_end(c);
    case 0xe946c:if(!sv_put(c,r.a[6],0x80,1,0))return false;r.d[0]=0;return am_call(c,0x1a93e,0xe9478); // CLR.B 80(A6); MOVEQ #0,D0; JSR 1a93e.L.
    // MOVE.W 2(A0),D1; MOVE.W D1,D0; SUB.W 4(A0),D0; JSR 1a910.L.
    case 0xe9478:
        if(!sv_get(c,r.a[0],2,2,value))return false;am_word(r.d[1],value);am_word(r.d[0],value);
        if(!sv_get(c,r.a[0],4,2,other))return false;am_word(r.d[0],(r.d[0]&65535U)-(other&65535U));
        return am_call(c,0x1a910,0xe9488);
    case 0xe9488:r.pc=0xe9768;return true; // BRA e9768.
    // e948c (opcode 02): MOVE.W 2(A0),D1; MOVE.W D1,D0; JSR 1a910.L.
    case 0xe948c:
        if(!sv_get(c,r.a[0],2,2,value))return false;am_word(r.d[1],value);am_word(r.d[0],value);return am_call(c,0x1a910,0xe9498);
    case 0xe9498:r.pc=0xe9768;return true; // BRA e9768.
    case 0xe949c:r.d[0]=0xffffffffU;return am_call(c,0x1a93e,0xe94a4); // (opcode 03) MOVEQ #ff,D0; JSR 1a93e.L.
    case 0xe94a4:r.pc=0xe9768;return true; // BRA e9768.
    // e94a8 (opcode 04): MOVE.W 2(A0),D0; MOVEQ #ff,D1; JSR 1a910.L.
    case 0xe94a8:if(!sv_get(c,r.a[0],2,2,value))return false;am_word(r.d[0],value);r.d[1]=0xffffffffU;return am_call(c,0x1a910,0xe94b4);
    case 0xe94b4:r.pc=0xe9768;return true; // BRA e9768.
    case 0xe94b8:r.a[1]=am_index(r.a[0],4);return am_call(c,0xe97c8,SV_EVAL_OP05); // (opcode 05) LEA 4(A0),A1; BSR e97c8.
    // ADDA.W 2(A0),A0; MOVE.B #ff,81(A6); RTS.
    case 0xe94c4:if(!sv_get(c,r.a[0],2,2,value))return false;r.a[0]=am_index(r.a[0],value);return sv_frame_end(c);
    // e94d0 (opcode 06): TST.W 7e(A6); BNE e94e6.
    case 0xe94d0:if(!sv_get(c,r.a[6],0x7e,2,value))return false;r.pc=(value&65535U)?0xe94e6:0xe94d8;return true;
    // MOVE.W 2(A0),7e(A6); MOVE.B #ff,81(A6); RTS.
    case 0xe94d8:if(!sv_get(c,r.a[0],2,2,value) || !sv_put(c,r.a[6],0x7e,2,value&65535U))return false;return sv_frame_end(c);
    // SUBQ.W #1,7e(A6); BEQ e9768.
    case 0xe94e6:
        if(!sv_get(c,r.a[6],0x7e,2,value))return false;value=(value-1U)&65535U;if(!sv_put(c,r.a[6],0x7e,2,value))return false;
        r.pc=value?0xe94ee:0xe9768;return true;
    case 0xe94ee:return sv_frame_end(c);
    case 0xe94f6:if(!sv_put(c,r.a[6],0x80,1,0))return false;r.pc=0xe9768;return true; // (opcode 07) CLR.B 80(A6); BRA e9768.

    // e9768: MOVEQ #0,D0; MOVE.B 1(A0),D0; LEA (A0,D0.W),A0; RTS.
    case 0xe9768:r.d[0]=0;if(!sv_get(c,r.a[0],1,1,value))return false;am_byte(r.d[0],value);r.a[0]=am_index(r.a[0],r.d[0]);return am_return(c);

    // e97c8 (evaluator): MOVEQ #0,D0; MOVE.B (A1)+,D0; CMPI.B #80,D0; BCC e97d8.
    case 0xe97c8:r.d[0]=0;if(!am_read(c,r.a[1],1,value))return false;r.a[1]+=1U;am_byte(r.d[0],value);r.pc=(value&255U)>=0x80U?0xe97d8:0xe97d4;return true;
    case 0xe97d4:return sv_push(c,r.d[0]); // MOVE.B D0,-(A7); BRA e97c8.
    // SUBI.W #80,D0; MOVE.W D0,D1; LSL.W #2,D1; JMP e97e4(PC,D1.W) (computed PC, no upper bound).
    case 0xe97d8:
        am_word(r.d[0],(r.d[0]&65535U)-0x80U);am_word(r.d[1],r.d[0]);am_word(r.d[1],(r.d[1]&65535U)<<2);
        r.pc=am_index(SV_OPERATORS,r.d[1]);return true;
    // e97e4 operator table: 34 BRA.W slots (operators 80..a1).
    case 0xe97e4:case 0xe97e8:case 0xe97ec:case 0xe97f0:case 0xe97f4:case 0xe97f8:case 0xe97fc:case 0xe9800:case 0xe9804:
    case 0xe9808:case 0xe980c:case 0xe9810:case 0xe9818:case 0xe981c:case 0xe9820:case 0xe9824:case 0xe9828:case 0xe982c:
    case 0xe9830:case 0xe9834:case 0xe9838:r.pc=0xe986c;return true;
    case 0xe9814:r.pc=0xe9878;return true;
    case 0xe983c:r.pc=0xe9884;return true;
    case 0xe9840:r.pc=0xe988c;return true;
    case 0xe9844:r.pc=0xe9894;return true;
    case 0xe9848:r.pc=0xe989c;return true;
    case 0xe984c:r.pc=0xe98a6;return true;
    case 0xe9850:r.pc=0xe98b0;return true;
    case 0xe9854:r.pc=0xe98ba;return true;
    case 0xe9858:r.pc=0xe98c4;return true;
    case 0xe985c:r.pc=0xe98ce;return true;
    case 0xe9860:r.pc=0xe98d8;return true;
    case 0xe9864:r.pc=0xe98ea;return true;
    case 0xe9868:r.pc=0xe98e2;return true;
    // LEA 5e30(A5),A2; MOVE.B (A2,D0.W),-(A7); BRA e97c8.
    case 0xe986c:r.a[2]=am_index(r.a[5],0x5e30);if(!am_read(c,am_index(r.a[2],r.d[0]),1,value))return false;return sv_push(c,value);
    case 0xe9878:return am_call(c,0xe932c,0xe987c); // BSR e932c.
    case 0xe987c:if(!sv_read(c,0x5e3c,1,value))return false;return sv_push(c,value); // MOVE.B 5e3c(A5),-(A7); BRA e97c8.
    case 0xe9884:return sv_push(c,0xff); // MOVE.B #ff,-(A7); BRA e97c8.
    case 0xe988c:return sv_push(c,0);    // MOVE.B #0,-(A7); BRA e97c8.
    case 0xe9894:if(!sv_get(c,r.a[6],0x80,1,value))return false;return sv_push(c,value); // MOVE.B 80(A6),-(A7); BRA e97c8.
    case 0xe989c:return sv_compare(c,0); // SEQ.
    case 0xe98a6:return sv_compare(c,1); // SGT.
    case 0xe98b0:return sv_compare(c,2); // SGE.
    case 0xe98ba:return sv_compare(c,3); // SLT.
    case 0xe98c4:return sv_compare(c,4); // SLE.
    case 0xe98ce:return sv_logic(c,false); // AND.B.
    case 0xe98d8:return sv_logic(c,true);  // OR.B.
    // MOVE.B (A7)+,D0; ADD.B D0,(A7); BRA e97c8.
    case 0xe98e2:
        if(!sv_pop(c) || !am_read(c,r.a[7],1,value) || !am_write(c,r.a[7],1,(value+r.d[0])&255U))return false;r.pc=0xe97c8;return true;
    // MOVE.B (A7)+,D0; RTS. The Z of the MOVE is consumed by the known return PCs (F3 main decision 3).
    case 0xe98ea:{
        if(!sv_pop(c))return false;const bool zero=(r.d[0]&255U)==0U;
        if(!am_pop(c,4,value))return false;
        if(value==SV_EVAL_CHILD1)r.pc=zero?0xe9428:0xe939a;      // e9396 BEQ.W e9428.
        else if(value==SV_EVAL_CHILD2)r.pc=zero?0xe9428:0xe93a2; // e939e BEQ.W e9428.
        else if(value==SV_EVAL_OP05)r.pc=zero?0xe94c4:0xe9768;   // e94c0 BNE.W e9768.
        else if(value==SV_EVAL_OP0B)r.pc=zero?0xe96b8:0xe96b4;   // e96b0 BEQ.W e96b8.
        else r.pc=value;
        return true;}
    default:return am_error(c,"unsupported animation stage event PC");
    }
}
}
