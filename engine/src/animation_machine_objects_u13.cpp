#include "animation_machine_internal.h"
namespace ms5 {
namespace {
const std::uint32_t OU13_DISPATCH=0x70932;      // MOVE.W 7e(A6),D0 (the shared dispatcher of the 7086a family).
const std::uint32_t OU13_OBJECT_TAIL=0xb80c4;   // LEA b7fd4(PC),A0; JSR 1ab02.L (the shared tail of the b8122 family).
const std::uint32_t OU13_BANK_ANIMATION=0x200084; // MOVE.L 200084.L,22(A6) (banked window LONG, live bus).
bool ou13_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool ou13_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// MOVE.L #callback,(A6); RTS (the dispatcher's next-frame callback).
bool ou13_install_return(AnimationMachineContext& c,std::uint32_t callback) {
    if(!am_write(c,c.s.a[6],4,callback))return false;return am_return(c);
}
// BSET.B/BCLR.B #0,15(A6) (Z only, not modeled further); MOVE.L #callback,(A6); RTS.
bool ou13_side_install_return(AnimationMachineContext& c,bool set,std::uint32_t callback) {
    std::uint32_t value=0;if(!ou13_get(c,c.s.a[6],0x15,1,value))return false;
    value=set?(value|1U):(value&0xfeU);if(!ou13_put(c,c.s.a[6],0x15,1,value))return false;
    return ou13_install_return(c,callback);
}
// CMPI.W #k,D0; BNE.W next (Z of the low WORD of D0).
bool ou13_case(AnimationMachineContext& c,std::uint32_t k,std::uint32_t next_pc,std::uint32_t equal_pc) {
    c.s.pc=(c.s.d[0]&65535U)!=k?next_pc:equal_pc;return true;
}
// Bcc consuming the C returned by a callee: taken when C equals taken_when_set.
bool ou13_consume(AnimationMachineContext& c,bool taken_when_set,std::uint32_t taken_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;
    if(r.carry==AnimationCarryUnknown)return am_error(c,"objects u13 caller requires known carry");
    r.pc=((r.carry==AnimationCarrySet)==taken_when_set)?taken_pc:next_pc;return true;
}
// MOVE.W #v,68(A6); MOVE.W #v,1e(A6).
bool ou13_height(AnimationMachineContext& c,std::uint32_t v) {
    return ou13_put(c,c.s.a[6],0x68,2,v) && ou13_put(c,c.s.a[6],0x1e,2,v);
}
}
// Objects F4 U13 (76 block starts): the callback 7090a (U12 70418 is a boundary) and the shared dispatcher 70932 that installs the
// next-frame callback by WORD 7e(A6); the object family b8122 (U12 4c0ac and 490ba are boundaries) with the installed callbacks b813c
// b816e b83e6, the shared tail b80c4 and the palette/height helper b80da; ea5f0 (U12 1abda is a boundary; child ea7f4) with the shared
// tail ea60c; f1a4e with the installed countdown callback f1a5a (child 4841a). Calls into existing executors: U05 1ab02/c6a96,
// fade_card 28ae/2a00, U09 47070, interpreter 49f8c/49fc6, U01 4b54e, U11 4be06. b80ce b819c b83f2 ea5f6 consume a callee C (1ab02,
// 4b54e, 49fc6, 1abda). U13 reads work RAM, the fixed ROM LONG table b80ac and the banked window LONG 200084 (and the LONG at its
// value + 16c) and writes no port.
bool animation_objects_u13_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 7090a (callback): MOVE.W #1,9c(A6); JSR 70418(PC) (boundary).
    case 0x7090a:if(!ou13_put(c,r.a[6],0x9c,2,1))return false;return am_call(c,0x70418,0x70914);
    case 0x70914:if(!ou13_put(c,r.a[6],0x87,1,0x10))return false;r.pc=OU13_DISPATCH;return true; // MOVE.B #10,87(A6); BRA.W 70932.
    // ---- 70932: MOVE.W 7e(A6),D0; CMPI.W #2,D0; BNE.W 70946.
    case 0x70932:if(!ou13_get(c,r.a[6],0x7e,2,value))return false;am_word(r.d[0],value);return ou13_case(c,2,0x70946,0x7093e);
    case 0x7093e:return ou13_install_return(c,0x72040);
    case 0x70946:return ou13_case(c,0xc,0x7095c,0x7094e);
    case 0x7094e:return ou13_side_install_return(c,false,0x72a18);
    case 0x7095c:return ou13_case(c,0xd,0x70972,0x70964);
    case 0x70964:return ou13_side_install_return(c,true,0x72a18);
    case 0x70972:r.pc=(r.d[0]&65535U)==0xeU?0x70980:0x70978;return true;     // CMPI.W #e,D0; BEQ.B 70980.
    case 0x70978:return ou13_case(c,0xf,0x709a8,0x70980);
    case 0x70980:r.pc=(r.d[0]&0x8000U)?0x709a6:0x70986;return true;          // TST.W D0; BMI.W 709a6.
    // ADDI.W #18,32(A6); CMPI.W #e,7e(A6); BNE.W 709a0.
    case 0x70986:
        if(!ou13_get(c,r.a[6],0x32,2,value) || !ou13_put(c,r.a[6],0x32,2,(value+0x18U)&65535U) || !ou13_get(c,r.a[6],0x7e,2,value))
            return false;
        r.pc=value!=0xeU?0x709a0:0x70996;return true;
    case 0x70996:if(!am_write(c,r.a[6],4,0x7241a))return false;r.pc=0x709a6;return true; // MOVE.L #7241a,(A6); BRA.W 709a6.
    case 0x709a0:if(!am_write(c,r.a[6],4,0x725d4))return false;r.pc=0x709a6;return true; // MOVE.L #725d4,(A6).
    case 0x709a6:return am_return(c);                                        // RTS.
    case 0x709a8:return ou13_case(c,3,0x709b8,0x709b0);
    case 0x709b0:return ou13_install_return(c,0x72714);
    case 0x709b8:return ou13_case(c,4,0x709c8,0x709c0);
    case 0x709c0:return ou13_install_return(c,0x7277a);
    case 0x709c8:return ou13_case(c,5,0x709d8,0x709d0);
    case 0x709d0:return ou13_install_return(c,0x727e0);
    case 0x709d8:return ou13_case(c,6,0x709e8,0x709e0);
    case 0x709e0:return ou13_install_return(c,0x72846);
    case 0x709e8:return ou13_case(c,8,0x709fe,0x709f0);
    case 0x709f0:return ou13_side_install_return(c,true,0x728ac);
    case 0x709fe:return ou13_case(c,9,0x70a14,0x70a06);
    case 0x70a06:return ou13_side_install_return(c,true,0x72912);
    case 0x70a14:return ou13_case(c,0xa,0x70a2a,0x70a1c);
    case 0x70a1c:return ou13_side_install_return(c,false,0x728ac);
    case 0x70a2a:return ou13_case(c,0xb,0x70a40,0x70a32);
    case 0x70a32:return ou13_side_install_return(c,false,0x72912);
    // BTST.B #7,15(A6); BNE.W 70a52.
    case 0x70a40:if(!ou13_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&0x80U)?0x70a52:0x70a4a;return true;
    case 0x70a4a:return ou13_install_return(c,0x71c90);
    // CMPI.B #3,6e(A6); BNE.W 70a64.
    case 0x70a52:if(!ou13_get(c,r.a[6],0x6e,1,value))return false;r.pc=value!=3U?0x70a64:0x70a5c;return true;
    case 0x70a5c:return ou13_install_return(c,0x70c0c);
    case 0x70a64:return ou13_install_return(c,0x71032);

    // ---- b80c4: LEA b7fd4(PC),A0; JSR 1ab02.L.
    case 0xb80c4:r.a[0]=0xb7fd4;return am_call(c,0x1ab02,0xb80ce);
    case 0xb80ce:return ou13_consume(c,false,0xb80d8,0xb80d2);               // BCC.W b80d8 (C returned by 1ab02).
    case 0xb80d2:r.pc=0x2a00;return true;                                    // JMP 2a00.L.
    case 0xb80d8:return am_return(c);                                        // RTS.
    // b80da: MOVE.W #20,D0; MOVE.W #5b,D1; MOVE.B #0,D2; JSR c6a96.L.
    case 0xb80da:am_word(r.d[0],0x20);am_word(r.d[1],0x5b);am_byte(r.d[2],0);return am_call(c,0xc6a96,0xb80ec);
    // TST.W 76(A6); BNE.W b8104.
    case 0xb80ec:if(!ou13_get(c,r.a[6],0x76,2,value))return false;r.pc=value?0xb8104:0xb80f4;return true;
    case 0xb80f4:if(!ou13_height(c,0x8838))return false;r.pc=0xb8110;return true; // MOVE.W #8838 x2; BRA.W b8110.
    case 0xb8104:if(!ou13_height(c,0xfff2))return false;r.pc=0xb8110;return true; // MOVE.W #fff2 x2.
    case 0xb8110:r.a[0]=0xc84c2;return am_call(c,0x490ba,0xb811c);          // LEA c84c2.L,A0; JSR 490ba.L (boundary).
    case 0xb811c:if(!ou13_put(c,r.a[6],0x54,2,r.d[0]&65535U))return false;return am_return(c); // MOVE.W D0,54(A6); RTS.
    // b8122 (callback): MOVE.B #0,79(A6); BRA.W b8132.
    case 0xb8122:if(!ou13_put(c,r.a[6],0x79,1,0))return false;r.pc=0xb8132;return true;
    case 0xb8132:return am_call(c,0x4c0ac,0xb8138);                          // JSR 4c0ac.L (boundary).
    case 0xb8138:return am_call(c,0xb80da,0xb813c);                          // JSR b80da(PC).
    // b813c: LEA 26(A6),A0; MOVE.W #c2,20(A6); MOVE.L 200084.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1;
    // MOVEA.L 16c(A1),A1; JSR 49f8c.L.
    case 0xb813c:
        r.a[0]=am_index(r.a[6],0x26);
        if(!ou13_put(c,r.a[6],0x20,2,0xc2) || !am_read(c,OU13_BANK_ANIMATION,4,value) || !ou13_put(c,r.a[6],0x22,4,value))return false;
        am_word(r.d[0],0x100);r.a[0]=am_index(r.a[6],0x26);
        if(!ou13_get(c,r.a[6],0x22,4,value))return false;r.a[1]=value;
        if(!ou13_get(c,r.a[1],0x16c,4,value))return false;r.a[1]=value;return am_call(c,0x49f8c,0xb8164);
    // CLR.B 5e(A6); MOVE.L #b816e,(A6).
    case 0xb8164:if(!ou13_put(c,r.a[6],0x5e,1,0) || !am_write(c,r.a[6],4,0xb816e))return false;r.pc=0xb816e;return true;
    case 0xb816e:case 0xb83e6:return am_call(c,0x4be06,r.pc+6U);           // (callback) JSR 4be06.L.
    // LEA b80ac(PC),A0; MOVEQ #0,D0; MOVE.B 79(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A0,D0.W),A0; MOVEQ #0,D0; MOVEQ #0,D1;
    // JSR 47070.L.
    case 0xb8174:
        r.a[0]=0xb80ac;r.d[0]=0;if(!ou13_get(c,r.a[6],0x79,1,value))return false;am_byte(r.d[0],value);am_word(r.d[0],r.d[0]<<2);
        if(!am_read(c,am_index(r.a[0],r.d[0]),4,value))return false;r.a[0]=value;r.d[0]=0;r.d[1]=0;return am_call(c,0x47070,0xb8190);
    case 0xb8190:case 0xb83ec:return am_call(c,0x49fc6,r.pc+6U);           // JSR 49fc6.L.
    case 0xb8196:return am_call(c,0x4b54e,0xb819c);                          // JSR 4b54e.L.
    case 0xb819c:return ou13_consume(c,false,0xb81aa,0xb81a0);               // BCC.W b81aa (C returned by 4b54e).
    // CLR.B 5e(A6); MOVE.L #b81be,(A6).
    case 0xb81a0:if(!ou13_put(c,r.a[6],0x5e,1,0) || !am_write(c,r.a[6],4,0xb81be))return false;r.pc=0xb81aa;return true;
    // BTST.B #7,61(A6); BEQ.W b81ba.
    case 0xb81aa:if(!ou13_get(c,r.a[6],0x61,1,value))return false;r.pc=(value&0x80U)?0xb81b4:0xb81ba;return true;
    case 0xb81b4:if(!am_write(c,r.a[6],4,0xb8232))return false;r.pc=0xb81ba;return true; // MOVE.L #b8232,(A6).
    case 0xb81ba:case 0xb83fc:r.pc=OU13_OBJECT_TAIL;return true;            // BRA.W b80c4.
    case 0xb83f2:return ou13_consume(c,false,0xb83fc,0xb83f6);               // BCC.W b83fc (C returned by 49fc6).
    case 0xb83f6:if(!am_write(c,r.a[6],4,0xb8400))return false;r.pc=0xb83fc;return true; // MOVE.L #b8400,(A6).

    // ---- ea5f0: JSR 1abda.L (boundary).
    case 0xea5f0:return am_call(c,0x1abda,0xea5f6);
    case 0xea5f6:return ou13_consume(c,false,0xea624,0xea5fa);               // BCC.W ea624 (C returned by 1abda).
    case 0xea5fa:r.d[2]=2;r.pc=0xea60c;return true;                          // MOVEQ #2,D2; BRA.W ea60c.
    // MOVE.W D2,-(A7); MOVEA.L #ea7f4,A0; MOVE.W #1e,D0; JSR 28ae.L.
    case 0xea60c:if(!am_push(c,2,r.d[2]&65535U))return false;r.a[0]=0xea7f4;am_word(r.d[0],0x1e);return am_call(c,0x28ae,0xea61e);
    // MOVE.W (A7)+,76(A0); RTS.
    case 0xea61e:if(!am_pop(c,2,value) || !ou13_put(c,r.a[0],0x76,2,value))return false;return am_return(c);
    case 0xea624:return am_return(c);                                        // RTS.

    // ---- f1a4e (callback): MOVE.W #294,76(A6); MOVE.L #f1a5a,(A6).
    case 0xf1a4e:if(!ou13_put(c,r.a[6],0x76,2,0x294) || !am_write(c,r.a[6],4,0xf1a5a))return false;r.pc=0xf1a5a;return true;
    // f1a5a (callback): SUBQ.W #1,76(A6); BCS.W f1a64 (borrow: the WORD was 0).
    case 0xf1a5a:
        if(!ou13_get(c,r.a[6],0x76,2,value) || !ou13_put(c,r.a[6],0x76,2,(value-1U)&65535U))return false;
        r.pc=value==0?0xf1a64:0xf1a62;return true;
    case 0xf1a62:return am_return(c);                                        // RTS.
    // MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L.
    case 0xf1a64:r.a[0]=0x4841a;am_word(r.d[0],0xa);return am_call(c,0x28ae,0xf1a74);
    case 0xf1a74:r.pc=0x2a00;return true;                                    // JMP 2a00.L.
    default:return am_error(c,"unsupported animation objects u13 PC");
    }
}
}
