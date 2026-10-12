#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// Absolute operands of the original code.
const std::uint32_t ON03_TABLE=0xc64a0;        // LEA c64a0(PC),A0: fixed ROM 16-byte records ending at WORD ffff (live bus).
const std::uint32_t ON03_BANK_BASE=0x200004;   // MOVE.L/MOVEA.L #200004: banked window LONG base (live bus).
const std::uint32_t ON03_BANK_RECORD=0x2002b8; // MOVEA.L 2002b8.L,A0: banked window LONG (live bus).
const std::uint32_t ON03_RECT=0xc63b6;         // LEA c63b6(PC),A0: rectangle read by 1ab02.
const std::uint32_t ON03_SLOTS_END=0x10db78;   // CMPA.L #10db78,A4: end of the slot table 5af8(A5).
const std::uint32_t ON03_CALLBACK=0xc6218;     // MOVE.L #c6218,(A6).
// A5 displacements (sign-extended WORDs).
const std::uint32_t ON03_SLOTS=0x5af8;         // LEA 5af8(A5),A4 (16 slots of 8 bytes).
const std::uint32_t ON03_INPUT_MODE=0xccac;    // -3354(A5): input BYTE (mode, record, animation).
const std::uint32_t ON03_INPUT_MOVE=0xccb0;    // -3350(A5): input BYTE (position).
const std::uint32_t ON03_INPUT_COLOR=0xccb2;   // -334e(A5): input BYTE (palette, 12/13).
bool on03_get(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(c.s.a[6],displacement),size,value);
}
bool on03_put(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(c.s.a[6],displacement),size,value);
}
// ADDQ/SUBQ #1 on a node WORD or BYTE (delta 1 or 0xffffffff).
bool on03_step(AnimationMachineContext& c,std::uint32_t displacement,unsigned int size,std::uint32_t delta,std::uint32_t next_pc) {
    std::uint32_t value=0;const std::uint32_t mask=size==1?255U:65535U;
    if(!on03_get(c,displacement,size,value) || !on03_put(c,displacement,size,(value+delta)&mask))return false;c.s.pc=next_pc;return true;
}
// MOVE.W d16(A6),d16(A6).
bool on03_copy(AnimationMachineContext& c,std::uint32_t from,std::uint32_t to) {
    std::uint32_t value=0;return on03_get(c,from,2,value) && on03_put(c,to,2,value);
}
// Bcc consuming the C returned by a callee: BCC taken when C is clear.
bool on03_bcc(AnimationMachineContext& c,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects n03 caller requires known carry");
    r.pc=r.carry==AnimationCarryClear?taken_pc:next_pc;return true;
}
// BTST.B #bit,D0; BNE (bit set) -> set_pc, BEQ -> clear_pc.
bool on03_bit(AnimationMachineContext& c,unsigned int bit,std::uint32_t set_pc,std::uint32_t clear_pc) {
    c.s.pc=((c.s.d[0]>>bit)&1U)!=0U?set_pc:clear_pc;return true;
}
// MOVE.B d16(A5),D0 (input BYTE into the low byte of D0).
bool on03_input(AnimationMachineContext& c,std::uint32_t displacement) {
    std::uint32_t value=0;if(!am_read(c,am_index(c.s.a[5],displacement),1,value))return false;am_byte(c.s.d[0],value);return true;
}
// MOVE.W #value,D0; MOVE.B #0,D1; JSR 8ebe.L.
bool on03_palette(AnimationMachineContext& c,std::uint32_t value,std::uint32_t return_pc) {
    am_word(c.s.d[0],value);am_byte(c.s.d[1],0);return am_call(c,0x8ebe,return_pc);
}
// MOVE.W #1,82(A6); ADDQ.W #1,7e(A6) (next record, first animation).
bool on03_next_record(AnimationMachineContext& c,std::uint32_t next_pc) {
    if(!on03_put(c,0x82,2,1))return false;return on03_step(c,0x7e,2,1U,next_pc);
}
// SUBQ.W #1,7e(A6); BCC.W no_borrow_pc (otherwise next_pc: the record index wrapped below 0).
bool on03_previous_record(AnimationMachineContext& c,std::uint32_t no_borrow_pc,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!on03_get(c,0x7e,2,value) || !on03_put(c,0x7e,2,(value-1U)&65535U))return false;
    c.s.pc=value==0U?next_pc:no_borrow_pc;return true;
}
// MOVE.W 2e(A6),42(A6); MOVE.W 32(A6),46(A6); ADDI.W #100,46(A6).
bool on03_place(AnimationMachineContext& c,std::uint32_t next_pc) {
    std::uint32_t value=0;
    if(!on03_copy(c,0x2e,0x42) || !on03_copy(c,0x32,0x46) || !on03_get(c,0x46,2,value) || !on03_put(c,0x46,2,(value+0x100U)&65535U))return false;
    c.s.pc=next_pc;return true;
}
// LEA c64a0(PC),A0; MOVE.W 7e(A6),D0; LSL.W #4,D0; MOVEA.L #200004,A1; ADDA.W 2(A0,D0.W),A1; MOVEA.L (A1),A0.
bool on03_list(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    r.a[0]=ON03_TABLE;if(!on03_get(c,0x7e,2,value))return false;am_word(r.d[0],(value<<4)&65535U);
    r.a[1]=ON03_BANK_BASE;if(!am_read(c,am_index(r.a[0],r.d[0])+2U,2,value))return false;r.a[1]=am_index(r.a[1],value);
    if(!am_read(c,r.a[1],4,value))return false;r.a[0]=value;return true;
}
// MOVEM.L D0-D7/A0-A6,-(A7) (D0 at the lowest address).
bool on03_save(AnimationMachineContext& c) {
    for(unsigned int i=7;i>0;--i)if(!am_push(c,4,c.s.a[i-1]))return false;
    for(unsigned int i=8;i>0;--i)if(!am_push(c,4,c.s.d[i-1]))return false;
    return true;
}
// MOVEM.L (A7)+,D0-D7/A0-A6.
bool on03_restore(AnimationMachineContext& c) {
    std::uint32_t value=0;
    for(unsigned int i=0;i<8;++i){if(!am_pop(c,4,value))return false;c.s.d[i]=value;}
    for(unsigned int i=0;i<7;++i){if(!am_pop(c,4,value))return false;c.s.a[i]=value;}
    return true;
}
}
// Objects F4 N03 (old U22; 113 block starts): the shared slot registration 4b82e (node BYTE 6d, slot table 5af8(A5) of 16 x 8 bytes
// up to 10db78), the node callback c603a (record table c64a0 and the banked animation list 200004+WORD, MOVEM around cleanup 8ff4,
// helper c647e and U02 8ebe, interpreter 49f8c, cleanup 43e34) with its installed callback c6218 (input BYTEs -3354/-3350/-334e(A5),
// helpers c63be/c63fa, banked LONG 2002b8 for interpreter 49fc6, U01 4b54e, boundary 4ae4a when LONG 72 is not 0, U05 1ab02 with the
// fixed rectangle c63b6; C set: fade_card 2a00). N03 writes no port and changes no bank; the data c63b6..c63be and the unreferenced
// c644a..c647e stay outside the routing.
bool animation_objects_n03_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,other=0;
    switch(r.pc) {
    // ---- 4b82e (shared): MOVEQ #0,D0; MOVE.B 6d(A6),D0; BPL.W 4b87a.
    case 0x4b82e:if(!on03_get(c,0x6d,1,value))return false;r.d[0]=value&255U;r.pc=(value&0x80U)==0U?0x4b87a:0x4b838;return true;
    case 0x4b838:r.pc=r.a[0]==0U?0x4b878:0x4b840;return true;                 // CMPA.W #0,A0; BEQ.W 4b878.
    case 0x4b840:r.a[4]=am_index(r.a[5],ON03_SLOTS);r.d[7]=0;r.pc=0x4b846;return true; // LEA 5af8(A5),A4; MOVEQ #0,D7.
    // MOVEA.L (A4),A3; CMPA.W #0,A3; BEQ.W 4b85e.
    case 0x4b846:if(!am_read(c,r.a[4],4,value))return false;r.a[3]=value;r.pc=value==0U?0x4b85e:0x4b850;return true;
    // MOVE.B 6d(A3),D6; ANDI.W #f,D6; CMP.B D6,D7; BEQ.W 4b86a.
    case 0x4b850:
        if(!am_read(c,am_index(r.a[3],0x6d),1,value))return false;am_word(r.d[6],value&15U);
        r.pc=(r.d[7]&255U)==(r.d[6]&255U)?0x4b86a:0x4b85e;return true;
    // MOVE.B D7,6d(A6); MOVE.L A6,(A4); MOVE.L A0,4(A4); RTS.
    case 0x4b85e:
        if(!on03_put(c,0x6d,1,r.d[7]&255U) || !am_write(c,r.a[4],4,r.a[6]) || !am_write(c,am_index(r.a[4],4),4,r.a[0]))return false;
        return am_return(c);
    // ADDQ.W #1,D7; LEA 8(A4),A4; CMPA.L #10db78,A4; BCS.B 4b846.
    case 0x4b86a:am_word(r.d[7],r.d[7]+1U);r.a[4]=am_index(r.a[4],8);r.pc=r.a[4]<ON03_SLOTS_END?0x4b846:0x4b878;return true;
    case 0x4b878:case 0xc63b4:return am_return(c);                            // RTS.
    // ANDI.W #f,D0; LSL.W #3,D0; LEA 5af8(A5),A4; ADDA.W D0,A4; CMPA.W #0,A0; BNE.W 4b89c.
    case 0x4b87a:
        am_word(r.d[0],(r.d[0]&15U)<<3);r.a[4]=am_index(am_index(r.a[5],ON03_SLOTS),r.d[0]);r.pc=r.a[0]!=0U?0x4b89c:0x4b88e;return true;
    // MOVE.L A0,(A4); MOVE.L A0,4(A4); MOVE.B #ff,6d(A6); RTS.
    case 0x4b88e:
        if(!am_write(c,r.a[4],4,r.a[0]) || !am_write(c,am_index(r.a[4],4),4,r.a[0]) || !on03_put(c,0x6d,1,0xff))return false;return am_return(c);
    case 0x4b89c:if(!am_write(c,am_index(r.a[4],4),4,r.a[0]))return false;return am_return(c); // MOVE.L A0,4(A4); RTS.

    // ---- c603a (callback): JSR 8ff4.L.
    case 0xc603a:return am_call(c,0x8ff4,0xc6040);
    case 0xc6040:return on03_palette(c,0xc49,0xc604e);                        // MOVE.W #c49,D0; MOVE.B #0,D1; JSR 8ebe.L.
    // MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVE.W #0,7e(A6); MOVE.W #1,82(A6); MOVE.W 76(A6),78(A6); LEA c64a0(PC),A0;
    // MOVE.W 7e(A6),D0.
    case 0xc604e:
        if(!on03_put(c,0x68,2,0x8820) || !on03_put(c,0x1e,2,0x8820) || !on03_put(c,0x7e,2,0) || !on03_put(c,0x82,2,1) || !on03_copy(c,0x76,0x78))
            return false;
        r.a[0]=ON03_TABLE;if(!on03_get(c,0x7e,2,value))return false;am_word(r.d[0],value);r.pc=0xc6074;return true;
    // MOVE.W D0,D1; LSL.W #4,D1; CMPI.W #ffff,(A0,D1.W); BNE.W c608c.
    case 0xc6074:
        am_word(r.d[1],(r.d[0]<<4)&65535U);if(!am_read(c,am_index(r.a[0],r.d[1]),2,value))return false;
        r.pc=value!=0xffffU?0xc608c:0xc6082;return true;
    // SUBQ.W #1,D0; MOVE.W D0,80(A6); BRA.W c6090.
    case 0xc6082:am_word(r.d[0],r.d[0]-1U);if(!on03_put(c,0x80,2,r.d[0]&65535U))return false;r.pc=0xc6090;return true;
    case 0xc608c:am_word(r.d[0],r.d[0]+1U);r.pc=0xc6074;return true;          // ADDQ.W #1,D0; BRA.B c6074.
    // MOVE.L #0,72(A6); CLR.L 56(A6); LEA 0.W,A0; JSR 4b82e.L.
    case 0xc6090:if(!on03_put(c,0x72,4,0) || !on03_put(c,0x56,4,0))return false;r.a[0]=0;return am_call(c,0x4b82e,0xc60a6);
    // LEA c64a0(PC),A0; MOVE.W 7e(A6),D0; LSL.W #4,D0; ADDA.W D0,A0; MOVE.W (A0),D1; CMPI.W #ffff,D1; BNE.W c60c4.
    case 0xc60a6:
        r.a[0]=ON03_TABLE;if(!on03_get(c,0x7e,2,value))return false;am_word(r.d[0],(value<<4)&65535U);r.a[0]=am_index(r.a[0],r.d[0]);
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[1],value);r.pc=value!=0xffffU?0xc60c4:0xc60bc;return true;
    case 0xc60bc:if(!on03_put(c,0x7e,2,0))return false;r.pc=0xc60a6;return true; // MOVE.W #0,7e(A6); BRA.B c60a6.
    // MOVE.W D1,7a(A6); MOVE.L #200004,D2; ADD.W 2(A0),D2; MOVE.L D2,7a(A6); MOVE.W 4(A0),D0; MOVE.W D0,7a(A6); MOVE.W D1,20(A6);
    // MOVEA.L D2,A1; MOVE.L (A1),22(A6); MOVEA.L 22(A6),A3; MOVE.W 82(A6),D0; MOVE.W 82(A6),7a(A6).
    case 0xc60c4:
        if(!on03_put(c,0x7a,2,r.d[1]&65535U))return false;
        r.d[2]=ON03_BANK_BASE;if(!am_read(c,am_index(r.a[0],2),2,value))return false;am_word(r.d[2],r.d[2]+value);
        if(!on03_put(c,0x7a,4,r.d[2]) || !am_read(c,am_index(r.a[0],4),2,value))return false;am_word(r.d[0],value);
        if(!on03_put(c,0x7a,2,r.d[0]&65535U) || !on03_put(c,0x20,2,r.d[1]&65535U))return false;
        r.a[1]=r.d[2];if(!am_read(c,r.a[1],4,value) || !on03_put(c,0x22,4,value) || !on03_get(c,0x22,4,value))return false;r.a[3]=value;
        if(!on03_get(c,0x82,2,value))return false;am_word(r.d[0],value);if(!on03_copy(c,0x82,0x7a))return false;
        r.pc=0xc60f6;return true;
    // MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L (A3,D1.W),A1; CMPA.L #0,A1; BNE.W c6116.
    case 0xc60f6:
        am_word(r.d[1],(r.d[0]<<2)&65535U);if(!am_read(c,am_index(r.a[3],r.d[1]),4,value))return false;r.a[1]=value;
        r.pc=value!=0U?0xc6116:0xc610a;return true;
    // MOVE.W #1,82(A6); ADDQ.W #1,7e(A6); BRA c60a6.
    case 0xc610a:case 0xc6124:return on03_next_record(c,0xc60a6);
    // MOVEA.L 4(A3,D1.W),A2; CMPA.L #0,A2; BNE.W c6132.
    case 0xc6116:if(!am_read(c,am_index(r.a[3],r.d[1])+4U,4,value))return false;r.a[2]=value;r.pc=value!=0U?0xc6132:0xc6124;return true;
    case 0xc6132:r.pc=r.a[1]!=r.a[2]?0xc613c:0xc6138;return true;            // CMPA.L A2,A1; BNE.W c613c.
    case 0xc6138:am_word(r.d[0],r.d[0]+1U);r.pc=0xc60f6;return true;          // ADDQ.W #1,D0; BRA.B c60f6.
    // MOVE.W D0,82(A6); MOVE.W 82(A6),7a(A6); MOVEM.L D0-D7/A0-A6,-(A7); JSR 8ff4.L.
    case 0xc613c:
        if(!on03_put(c,0x82,2,r.d[0]&65535U) || !on03_copy(c,0x82,0x7a) || !on03_save(c))return false;return am_call(c,0x8ff4,0xc6150);
    case 0xc6150:return am_call(c,0xc647e,0xc6154);                           // JSR c647e(PC).
    // ADD.W 6(A0),D0; MOVE.W D0,86(A6); MOVE.B #0,D1; JSR 8ebe.L.
    case 0xc6154:
        if(!am_read(c,am_index(r.a[0],6),2,value))return false;am_word(r.d[0],r.d[0]+value);
        if(!on03_put(c,0x86,2,r.d[0]&65535U))return false;am_byte(r.d[1],0);return am_call(c,0x8ebe,0xc6166);
    // MOVE.W 6(A0),D0; CMPI.W #75,D0; BNE.W c6180.
    case 0xc6166:if(!am_read(c,am_index(r.a[0],6),2,value))return false;am_word(r.d[0],value);r.pc=value!=0x75U?0xc6180:0xc6172;return true;
    case 0xc6172:return on03_palette(c,0xc76,0xc6180);
    case 0xc6180:r.pc=(r.d[0]&65535U)!=0x87U?0xc6196:0xc6188;return true;     // CMPI.W #87,D0; BNE.W c6196.
    case 0xc6188:return on03_palette(c,0xc88,0xc6196);
    case 0xc6196:r.pc=(r.d[0]&65535U)!=0x36U?0xc61ac:0xc619e;return true;     // CMPI.W #36,D0; BNE.W c61ac.
    case 0xc619e:return on03_palette(c,0xc39,0xc61ac);
    case 0xc61ac:r.pc=(r.d[0]&65535U)!=0x3eU?0xc61c2:0xc61b4;return true;     // CMPI.W #3e,D0; BNE.W c61c2.
    case 0xc61b4:return on03_palette(c,0xc3f,0xc61c2);
    case 0xc61c2:r.pc=(r.d[0]&65535U)!=0xd6U?0xc61d8:0xc61ca;return true;     // CMPI.W #d6,D0; BNE.W c61d8.
    case 0xc61ca:return on03_palette(c,0xce4,0xc61d8);
    // MOVEM.L (A7)+,D0-D7/A0-A6; MOVE.B 19(A6),14(A6); MOVE.W #100,D0; JSR 49f8c.L.
    case 0xc61d8:
        if(!on03_restore(c) || !on03_get(c,0x19,1,value) || !on03_put(c,0x14,1,value))return false;am_word(r.d[0],0x100);
        return am_call(c,0x49f8c,0xc61ec);
    // TST.W 76(A6); BNE.W c61fe / c6358.
    case 0xc61ec:if(!on03_get(c,0x76,2,value))return false;r.pc=value!=0U?0xc61fe:0xc61f4;return true;
    case 0xc6346:if(!on03_get(c,0x76,2,value))return false;r.pc=value!=0U?0xc6358:0xc634e;return true;
    case 0xc61f4:return am_call(c,0x43e34,0xc61fa);                           // JSR 43e34.L.
    case 0xc634e:return am_call(c,0x43e34,0xc6354);
    case 0xc61fa:r.pc=0xc6210;return true;                                    // BRA.W c6210.
    case 0xc6354:r.pc=0xc636a;return true;                                    // BRA.W c636a.
    case 0xc61fe:return on03_place(c,0xc6210);
    case 0xc6358:return on03_place(c,0xc636a);
    case 0xc6210:if(!am_write(c,r.a[6],4,ON03_CALLBACK))return false;return am_return(c); // MOVE.L #c6218,(A6); RTS.

    // ---- c6218 (installed callback): MOVE.B #90,567e(A5); MOVE.B #ff,567f(A5); MOVE.B -3354(A5),D0; BTST.B #4,D0; BEQ.W c623e.
    case 0xc6218:
        if(!am_write(c,am_index(r.a[5],0x567e),1,0x90) || !am_write(c,am_index(r.a[5],0x567f),1,0xff) || !on03_input(c,ON03_INPUT_MODE))
            return false;
        return on03_bit(c,4,0xc6230,0xc623e);
    case 0xc6230:return on03_bit(c,5,0xc6238,0xc623e);                        // BTST.B #5,D0; BEQ.W c623e.
    case 0xc6238:if(!on03_get(c,0x84,1,value) || !on03_put(c,0x84,1,value^1U))return false;r.pc=0xc623e;return true; // BCHG.B #0,84(A6).
    case 0xc623e:if(!on03_get(c,0x84,1,value))return false;r.pc=value!=0U?0xc62a2:0xc6246;return true; // TST.B 84(A6); BNE.W c62a2.
    case 0xc6246:return on03_bit(c,7,0xc624e,0xc6252);                        // BTST.B #7,D0; BEQ.W c6252.
    case 0xc624e:case 0xc629e:r.pc=0xc6090;return true;                       // BRA.W c6090.
    case 0xc6252:return on03_bit(c,6,0xc625a,0xc6268);                        // BTST.B #6,D0; BEQ.W c6268.
    case 0xc625a:return on03_next_record(c,0xc6090);                          // MOVE.W #1,82(A6); ADDQ.W #1,7e(A6); BRA.W c6090.
    case 0xc6268:return on03_bit(c,4,0xc6270,0xc6278);                        // BTST.B #4,D0; BEQ.W c6278.
    case 0xc6270:return on03_step(c,0x82,2,1U,0xc6090);                       // ADDQ.W #1,82(A6); BRA.W c6090.
    case 0xc6278:return on03_bit(c,5,0xc6280,0xc62a2);                        // BTST.B #5,D0; BEQ.W c62a2.
    // SUBQ.W #1,82(A6); BNE.W c629a.
    case 0xc6280:
        if(!on03_get(c,0x82,2,value))return false;value=(value-1U)&65535U;if(!on03_put(c,0x82,2,value))return false;
        r.pc=value!=0U?0xc629a:0xc6288;return true;
    case 0xc6288:return on03_previous_record(c,0xc6296,0xc6290);              // SUBQ.W #1,7e(A6); BCC.W c6296.
    case 0xc6290:if(!on03_copy(c,0x80,0x7e))return false;r.pc=0xc6296;return true; // MOVE.W 80(A6),7e(A6).
    case 0xc6296:return am_call(c,0xc63be,0xc629a);                           // JSR c63be(PC).
    case 0xc629a:return am_call(c,0xc63fa,0xc629e);                           // JSR c63fa(PC).
    case 0xc62a2:if(!on03_input(c,ON03_INPUT_MOVE))return false;return on03_bit(c,0,0xc62ae,0xc62b2); // MOVE.B -3350(A5),D0; BTST #0.
    case 0xc62ae:return on03_step(c,0x32,2,1U,0xc62b2);                       // ADDQ.W #1,32(A6).
    case 0xc62b2:return on03_bit(c,1,0xc62ba,0xc62be);                        // BTST.B #1,D0; BEQ.W c62be.
    case 0xc62ba:return on03_step(c,0x32,2,0xffffffffU,0xc62be);              // SUBQ.W #1,32(A6).
    case 0xc62be:return on03_bit(c,3,0xc62c6,0xc62ca);                        // BTST.B #3,D0; BEQ.W c62ca.
    case 0xc62c6:return on03_step(c,0x2e,2,1U,0xc62ca);                       // ADDQ.W #1,2e(A6).
    case 0xc62ca:return on03_bit(c,2,0xc62d2,0xc62d6);                        // BTST.B #2,D0; BEQ.W c62d6.
    case 0xc62d2:return on03_step(c,0x2e,2,0xffffffffU,0xc62d6);              // SUBQ.W #1,2e(A6).
    // MOVE.B -334e(A5),D0; BTST.B #4/#5/#6,D0; BEQ.W.
    case 0xc62d6:if(!on03_input(c,ON03_INPUT_COLOR))return false;return on03_bit(c,4,0xc62e2,0xc62fc);
    case 0xc62fc:if(!on03_input(c,ON03_INPUT_COLOR))return false;return on03_bit(c,5,0xc6308,0xc6322);
    case 0xc6322:if(!on03_input(c,ON03_INPUT_COLOR))return false;return on03_bit(c,6,0xc632e,0xc6336);
    case 0xc62e2:return am_call(c,0x8ff4,0xc62e8);                            // JSR 8ff4.L.
    case 0xc6308:return am_call(c,0x8ff4,0xc630e);
    // MOVE.W 86(A6),D0; SUBQ.W/ADDQ.W #1,D0; MOVE.W D0,86(A6); MOVE.B #0,D1; JSR 8ebe.L.
    case 0xc62e8:case 0xc630e:
        if(!on03_get(c,0x86,2,value))return false;am_word(r.d[0],r.pc==0xc62e8?value-1U:value+1U);
        if(!on03_put(c,0x86,2,r.d[0]&65535U))return false;am_byte(r.d[1],0);return am_call(c,0x8ebe,r.pc==0xc62e8?0xc62fc:0xc6322);
    // SUBQ.B #1,12(A6); SUBQ.B #1,13(A6) / ADDQ.B #1,12(A6); ADDQ.B #1,13(A6).
    case 0xc632e:if(!on03_step(c,0x12,1,0xffffffffU,0xc6336))return false;return on03_step(c,0x13,1,0xffffffffU,0xc6336);
    case 0xc6336:return on03_bit(c,7,0xc633e,0xc6346);                        // BTST.B #7,D0; BEQ.W c6346.
    case 0xc633e:if(!on03_step(c,0x12,1,1U,0xc6346))return false;return on03_step(c,0x13,1,1U,0xc6346);
    // MOVEA.L 2002b8.L,A0; MOVE.L 14(A0),7a(A6); JSR 49fc6.L.
    case 0xc636a:
        if(!am_read(c,ON03_BANK_RECORD,4,value))return false;r.a[0]=value;
        if(!am_read(c,am_index(r.a[0],0x14),4,value) || !on03_put(c,0x7a,4,value))return false;return am_call(c,0x49fc6,0xc637c);
    case 0xc637c:r.pc=0xc6380;return true;                                    // BCC.W c6380 (target = next instruction; C not used).
    case 0xc6380:return am_call(c,0x4b54e,0xc6386);                           // JSR 4b54e.L.
    // CLR.B 5e(A6); BCLR.B #7,61(A6); MOVE.L 72(A6),D0; BEQ.W c63a0.
    case 0xc6386:
        if(!on03_put(c,0x5e,1,0) || !on03_get(c,0x61,1,value) || !on03_put(c,0x61,1,value&0x7fU) || !on03_get(c,0x72,4,value))return false;
        r.d[0]=value;r.pc=value==0U?0xc63a0:0xc6398;return true;
    case 0xc6398:r.a[0]=r.d[0];return am_call(c,0x4ae4a,0xc63a0);              // MOVEA.L D0,A0; JSR 4ae4a.L (boundary).
    case 0xc63a0:r.a[0]=ON03_RECT;return am_call(c,0x1ab02,0xc63aa);           // LEA c63b6(PC),A0; JSR 1ab02.L.
    case 0xc63aa:return on03_bcc(c,0xc63b4,0xc63ae);                          // BCC.W c63b4 (C returned by 1ab02).
    case 0xc63ae:r.pc=0x2a00;return true;                                     // JMP 2a00.L.

    // ---- c63be (helper): list of record 7e, then MOVE.W #1,D0.
    case 0xc63be:if(!on03_list(c))return false;am_word(r.d[0],1);r.pc=0xc63d8;return true;
    // MOVE.W D0,D1; ADD.W D1,D1; ADD.W D1,D1; MOVEA.L (A0,D1.W),A1; CMPA.L #0,A1; BEQ.W c63f0.
    case 0xc63d8:
        am_word(r.d[1],(r.d[0]<<2)&65535U);if(!am_read(c,am_index(r.a[0],r.d[1]),4,value))return false;r.a[1]=value;
        r.pc=value==0U?0xc63f0:0xc63ec;return true;
    case 0xc63ec:am_word(r.d[0],r.d[0]+1U);r.pc=0xc63d8;return true;          // ADDQ.W #1,D0; BRA.B c63d8.
    // SUBQ.W #1,D0; SUBQ.W #1,D0; MOVE.W D0,82(A6); RTS.
    case 0xc63f0:am_word(r.d[0],r.d[0]-2U);if(!on03_put(c,0x82,2,r.d[0]&65535U))return false;return am_return(c);
    // ---- c63fa (helper): list of record 7e, then MOVE.W 82(A6),D0.
    case 0xc63fa:if(!on03_list(c) || !on03_get(c,0x82,2,value))return false;am_word(r.d[0],value);r.pc=0xc6414;return true;
    case 0xc6414:am_word(r.d[1],r.d[0]);r.pc=(r.d[1]&65535U)!=0U?0xc642e:0xc641a;return true; // MOVE.W D0,D1; BNE.W c642e.
    case 0xc641a:return on03_previous_record(c,0xc6428,0xc6422);              // SUBQ.W #1,7e(A6); BCC.W c6428.
    case 0xc6422:if(!on03_copy(c,0x80,0x7e))return false;r.pc=0xc6428;return true; // MOVE.W 80(A6),7e(A6).
    case 0xc6428:return am_call(c,0xc63be,0xc642c);                           // JSR c63be(PC).
    case 0xc642c:r.pc=0xc63fa;return true;                                    // BRA.B c63fa.
    // ADD.W D1,D1; ADD.W D1,D1; MOVEA.L (A0,D1.W),A1; MOVEA.L 4(A0,D1.W),A2; CMPA.L A2,A1; BNE.W c6444.
    case 0xc642e:
        am_word(r.d[1],(r.d[1]<<2)&65535U);
        if(!am_read(c,am_index(r.a[0],r.d[1]),4,value) || !am_read(c,am_index(r.a[0],r.d[1])+4U,4,other))return false;
        r.a[1]=value;r.a[2]=other;r.pc=value!=other?0xc6444:0xc6440;return true;
    case 0xc6440:am_word(r.d[0],r.d[0]-1U);r.pc=0xc6414;return true;          // SUBQ.W #1,D0; BRA.B c6414.
    case 0xc6444:if(!on03_put(c,0x82,2,r.d[0]&65535U))return false;return am_return(c); // MOVE.W D0,82(A6); RTS.
    // ---- c647e (helper): MOVEA.L 8(A0),A1.
    case 0xc647e:if(!am_read(c,am_index(r.a[0],8),4,value))return false;r.a[1]=value;r.pc=0xc6482;return true;
    case 0xc6482:if(!am_read(c,r.a[1],2,value))return false;am_word(r.d[2],value);r.pc=(value&0x8000U)==0U?0xc648c:0xc6488;return true;
    case 0xc6488:r.d[0]=0;return am_return(c);                                // MOVEQ #0,D0; RTS.
    // MOVE.W 82(A6),D1; CMP.W D1,D2; BEQ.W c649a.
    case 0xc648c:if(!on03_get(c,0x82,2,value))return false;am_word(r.d[1],value);r.pc=(r.d[2]&65535U)==value?0xc649a:0xc6496;return true;
    case 0xc6496:r.a[1]+=4U;r.pc=0xc6482;return true;                         // ADDQ.L #4,A1; BRA.B c6482.
    case 0xc649a:if(!am_read(c,r.a[1]+2U,2,value))return false;am_word(r.d[0],value);return am_return(c); // MOVE.W 2(A1),D0; RTS.
    default:return am_error(c,"unsupported animation objects n03 PC");
    }
}
}
