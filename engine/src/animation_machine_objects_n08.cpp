#include "animation_machine_internal.h"
namespace ms5 {
namespace {
std::uint32_t on08_w(std::uint32_t v) {return v&65535U;}
bool on08_get(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t& value) {
    return am_read(c,am_index(base,displacement),size,value);
}
bool on08_put(AnimationMachineContext& c,std::uint32_t base,std::uint32_t displacement,unsigned int size,std::uint32_t value) {
    return am_write(c,am_index(base,displacement),size,value);
}
// WORD subtraction dst - src (SUB.W/CMP.W): result and the N Z V C flags of the 16-bit two's complement operation.
struct On08Flags {bool n,z,v,c;};
std::uint32_t on08_sub(std::uint32_t dst,std::uint32_t src,On08Flags& f) {
    const std::uint32_t a=dst&65535U,b=src&65535U,res=(a-b)&65535U;
    f.n=(res&0x8000U)!=0U;f.z=res==0U;f.v=(((a^b)&(a^res))&0x8000U)!=0U;f.c=b>a;return res;
}
// Signed WORD conditions from N Z V (written out).
bool on08_ge(const On08Flags& f) {return f.n==f.v;}
bool on08_lt(const On08Flags& f) {return f.n!=f.v;}
bool on08_gt(const On08Flags& f) {return !f.z && f.n==f.v;}
bool on08_le(const On08Flags& f) {return f.z || f.n!=f.v;}
// NEG.W Dn / ADD.W Dm,Dn on the low WORD only.
void on08_neg_w(std::uint32_t& r) {am_word(r,(0U-on08_w(r))&65535U);}
void on08_add_w(std::uint32_t& r,std::uint32_t v) {am_word(r,(on08_w(r)+on08_w(v))&65535U);}
// ASR.W #1 / ASR.B #1 on the low WORD / BYTE: returns the shifted-out bit (C); the sign bit is kept.
bool on08_asr_w(std::uint32_t& r) {const std::uint32_t w=on08_w(r);am_word(r,(w>>1)|(w&0x8000U));return (w&1U)!=0U;}
bool on08_asr_b(std::uint32_t& r) {const std::uint32_t b=r&255U;am_byte(r,(b>>1)|(b&0x80U));return (b&1U)!=0U;}
// OR.L d1(A4),Dp; OR.L d2(A4),Dq (reads in this order).
bool on08_or_pair(AnimationMachineContext& c,std::uint32_t d1,unsigned int p,std::uint32_t d2,unsigned int q,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!on08_get(c,r.a[4],d1,4,value))return false;r.d[p]|=value;
    if(!on08_get(c,r.a[4],d2,4,value))return false;r.d[q]|=value;r.pc=next_pc;return true;
}
// ADD.W D1,D0; NEG.W D0 (flip of the box offset).
void on08_flip(AnimationMachineState& r) {on08_add_w(r.d[0],r.d[1]);on08_neg_w(r.d[0]);}
// OR.L (A3)+,D6; OR.L (A3)+,D7; DBRA D1,loop_pc (one iteration per block).
bool on08_rows(AnimationMachineContext& c,std::uint32_t loop_pc,std::uint32_t next_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    if(!am_read(c,r.a[3],4,value))return false;r.d[6]|=value;r.a[3]+=4U;
    if(!am_read(c,r.a[3],4,value))return false;r.d[7]|=value;r.a[3]+=4U;
    const std::uint32_t count=(on08_w(r.d[1])+65535U)&65535U;am_word(r.d[1],count);r.pc=count!=65535U?loop_pc:next_pc;return true;
}
// Bit-scan group head: [SWAP Dn;] TST.size Dn; BEQ.W end_pc; BPL.W plus_pc (else the candidate block hit_pc).
bool on08_head(AnimationMachineContext& c,unsigned int n,unsigned int size,bool swap,std::uint32_t end_pc,std::uint32_t plus_pc,
    std::uint32_t hit_pc) {
    AnimationMachineState& r=c.s;if(swap)am_swap(r.d[n]);
    const std::uint32_t mask=size==1?255U:65535U,sign=size==1?0x80U:0x8000U,value=r.d[n]&mask;
    r.pc=value==0U?end_pc:((value&sign)?hit_pc:plus_pc);return true;
}
// Bit-scan step: ADD.size Dn,Dn; BEQ.W end_pc; BPL.W plus_pc (else the candidate block hit_pc).
bool on08_add(AnimationMachineContext& c,unsigned int n,unsigned int size,std::uint32_t end_pc,std::uint32_t plus_pc,std::uint32_t hit_pc) {
    AnimationMachineState& r=c.s;
    const std::uint32_t mask=size==1?255U:65535U,sign=size==1?0x80U:0x8000U,value=((r.d[n]&mask)<<1)&mask;
    r.d[n]=(r.d[n]&~mask)|value;r.pc=value==0U?end_pc:((value&sign)?hit_pc:plus_pc);return true;
}
// Candidate: MOVEA.L d(A4),A2; MOVEQ #index,D4; BSR.W 4ad6c (boundary without an executor).
bool on08_hit(AnimationMachineContext& c,std::uint32_t displacement,std::uint32_t index,std::uint32_t return_pc) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;if(!on08_get(c,r.a[4],displacement,4,value))return false;
    r.a[2]=value;r.d[4]=index;return am_call(c,0x4ad6c,return_pc);
}
}
// Objects F4 N08 (190 block starts): the shared object core. 4945e (JSR 49370; nearest player node to A0, C returned by ANDI/ORI
// CCR: 494a6 494ac Clear, 494b4 Set), the on-screen test 4983e / second entry 49842 (C returned by CMP.W: 4984e BCC taken Clear /
// fall-through Set, 49862 unsigned borrow; RTS 49876 keeps it) and the hit box grid search 4ae4a (category and column / row masks,
// the 64 bit-scan candidate blocks BSR to the boundary 4ad6c without an executor, the debug walk JSR 4b784 when BYTE 10f000 bit 5).
// FLOW_ONLY: 4945e 49842 49876 4b4da 4b4e6. N08 has no carry consumer.
bool animation_objects_n08_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0,v1=0,v2=0;On08Flags f;
    switch(r.pc) {
    // ---- 4945e: JSR 49370(PC).
    case 0x4945e:return am_call(c,0x49370,0x49462);
    case 0x49462:r.pc=(r.d[0]&255U)==0U?0x494b4:0x49468;return true;                    // TST.B D0; BEQ.W 494b4.
    // LEA 100cb8.L,A0; LEA 100da8.L,A1; CMPI.B #1,D0; BEQ.W 494a6.
    case 0x49468:r.a[0]=0x100cb8;r.a[1]=0x100da8;r.pc=(r.d[0]&255U)==1U?0x494a6:0x4947c;return true;
    case 0x4947c:r.pc=(r.d[0]&255U)==2U?0x494ac:0x49484;return true;                    // CMPI.B #2,D0; BEQ.W 494ac.
    // MOVE.W 42(A6),D0; MOVE.W 42(A0),D1; MOVE.W 42(A1),D2; SUB.W D0,D1; BGE.W 49498.
    case 0x49484:
        if(!on08_get(c,r.a[6],0x42,2,value) || !on08_get(c,r.a[0],0x42,2,v1) || !on08_get(c,r.a[1],0x42,2,v2))return false;
        am_word(r.d[0],value);am_word(r.d[1],v1);am_word(r.d[2],v2);
        am_word(r.d[1],on08_sub(r.d[1],r.d[0],f));r.pc=on08_ge(f)?0x49498:0x49496;return true;
    case 0x49496:on08_neg_w(r.d[1]);r.pc=0x49498;return true;                            // NEG.W D1.
    case 0x49498:am_word(r.d[2],on08_sub(r.d[2],r.d[0],f));r.pc=on08_ge(f)?0x494a0:0x4949e;return true; // SUB.W D0,D2; BGE.W 494a0.
    case 0x4949e:on08_neg_w(r.d[2]);r.pc=0x494a0;return true;                            // NEG.W D2.
    case 0x494a0:on08_sub(r.d[2],r.d[1],f);r.pc=on08_lt(f)?0x494ac:0x494a6;return true;  // CMP.W D1,D2; BLT.W 494ac.
    case 0x494a6:r.carry=AnimationCarryClear;return am_return(c);                        // ANDI.B #fe,CCR; RTS.
    case 0x494ac:r.a[0]=r.a[1];r.carry=AnimationCarryClear;return am_return(c);          // MOVEA.L A1,A0; ANDI.B #fe,CCR; RTS.
    case 0x494b4:r.a[0]=0x100cb8;r.carry=AnimationCarrySet;return am_return(c);         // LEA 100cb8.L,A0; ORI.B #1,CCR; RTS.

    // ---- 4983e: MOVE.W #18,D2 (then the second entry 49842: BTST.B #0,15(A6); BEQ.W 4984e).
    case 0x4983e:am_word(r.d[2],0x18);r.pc=0x49842;return true;
    case 0x49842:if(!on08_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&1U)==0U?0x4984e:0x4984c;return true;
    case 0x4984c:on08_neg_w(r.d[0]);r.pc=0x4984e;return true;                            // NEG.W D0.
    // ADD.W 42(A6),D0; SUB.W D2,D0; MOVE.W #140,D3; SUB.W D2,D3; SUB.W D2,D3; CMP.W D3,D0; BCC.W 49876 (taken: C Clear, else Set).
    case 0x4984e:
        if(!on08_get(c,r.a[6],0x42,2,value))return false;on08_add_w(r.d[0],value);am_word(r.d[0],on08_sub(r.d[0],r.d[2],f));
        am_word(r.d[3],0x140);am_word(r.d[3],on08_sub(r.d[3],r.d[2],f));am_word(r.d[3],on08_sub(r.d[3],r.d[2],f));
        on08_sub(r.d[0],r.d[3],f);r.carry=f.c?AnimationCarrySet:AnimationCarryClear;r.pc=f.c?0x49862:0x49876;return true;
    // ADD.W 46(A6),D1; SUBI.W #100,D1; SUB.W D2,D1; MOVE.W #100,D3; SUB.W D2,D3; SUB.W D2,D3; CMP.W D3,D1 (C = unsigned borrow).
    case 0x49862:
        if(!on08_get(c,r.a[6],0x46,2,value))return false;on08_add_w(r.d[1],value);am_word(r.d[1],on08_sub(r.d[1],0x100,f));
        am_word(r.d[1],on08_sub(r.d[1],r.d[2],f));am_word(r.d[3],0x100);am_word(r.d[3],on08_sub(r.d[3],r.d[2],f));
        am_word(r.d[3],on08_sub(r.d[3],r.d[2],f));on08_sub(r.d[1],r.d[3],f);r.carry=f.c?AnimationCarrySet:AnimationCarryClear;
        r.pc=0x49876;return true;
    case 0x49876:return am_return(c);                                                    // RTS (keeps C).

    // ---- 4ae4a: LEA 5746(A5),A4; TST.B 5744(A5); BMI.W 4ae5a.
    case 0x4ae4a:r.a[4]=am_index(r.a[5],0x5746);if(!on08_get(c,r.a[5],0x5744,1,value))return false;r.pc=(value&0x80U)?0x4ae5a:0x4ae56;return true;
    case 0x4ae56:r.a[4]=am_index(r.a[5],0x5918);r.pc=0x4ae5a;return true;               // LEA 5918(A5),A4.
    // MOVEQ #0,D6; MOVEQ #0,D7; MOVE.W D7,5af2(A5); MOVE.L D7,5af4(A5); MOVE.L D7,5b78(A5); MOVE.W D7,5b7c(A5); MOVE.L D7,5b7e(A5);
    // MOVE.W #ffff,5b82(A5); MOVE.B 3(A0),D0; ASR.W #1,D0; BCC.W 4ae8a.
    case 0x4ae5a:
        r.d[6]=0;r.d[7]=0;
        if(!on08_put(c,r.a[5],0x5af2,2,0) || !on08_put(c,r.a[5],0x5af4,4,0) || !on08_put(c,r.a[5],0x5b78,4,0) ||
            !on08_put(c,r.a[5],0x5b7c,2,0) || !on08_put(c,r.a[5],0x5b7e,4,0) || !on08_put(c,r.a[5],0x5b82,2,0xffff))return false;
        if(!on08_get(c,r.a[0],3,1,value))return false;am_byte(r.d[0],value);r.pc=on08_asr_w(r.d[0])?0x4ae82:0x4ae8a;return true;
    case 0x4ae82:return on08_or_pair(c,0xb8,6,0xbc,7,0x4ae8a);                           // OR.L b8(A4),D6; OR.L bc(A4),D7.
    case 0x4ae8a:r.pc=on08_asr_w(r.d[0])?0x4ae90:0x4ae98;return true;                   // ASR.W #1,D0; BCC.W 4ae98.
    case 0x4ae90:return on08_or_pair(c,0xc0,6,0xc4,7,0x4ae98);
    case 0x4ae98:r.pc=on08_asr_w(r.d[0])?0x4ae9e:0x4aea6;return true;
    case 0x4ae9e:return on08_or_pair(c,0xc8,6,0xcc,7,0x4aea6);
    // MOVE.W (A0),D0; LEA 4a9eb(PC),A1; MOVE.B (A1,D0.W),D0 (fixed ROM BYTE table, live bus); MOVEQ #0,D4; MOVEQ #0,D5; ASR.B #1,D0;
    // BCC.W 4aec2.
    case 0x4aea6:
        if(!am_read(c,r.a[0],2,value))return false;am_word(r.d[0],value);r.a[1]=0x4a9eb;
        if(!am_read(c,am_index(r.a[1],r.d[0]),1,value))return false;am_byte(r.d[0],value);r.d[4]=0;r.d[5]=0;
        r.pc=on08_asr_b(r.d[0])?0x4aeba:0x4aec2;return true;
    case 0x4aeba:return on08_or_pair(c,0xa0,4,0xa4,5,0x4aec2);                           // OR.L a0(A4),D4; OR.L a4(A4),D5.
    case 0x4aec2:r.pc=on08_asr_b(r.d[0])?0x4aec8:0x4aed0;return true;                   // ASR.B #1,D0; BCC.W 4aed0.
    case 0x4aec8:return on08_or_pair(c,0xa8,4,0xac,5,0x4aed0);
    case 0x4aed0:r.pc=on08_asr_b(r.d[0])?0x4aed6:0x4aede;return true;
    case 0x4aed6:return on08_or_pair(c,0xb0,4,0xb4,5,0x4aede);
    // AND.L D4,D6; AND.L D5,D7; MOVE.L D6,5aea(A5); MOVE.L D7,5aee(A5); OR.L D6,D7; BEQ.W 4b4da.
    case 0x4aede:
        r.d[6]&=r.d[4];r.d[7]&=r.d[5];if(!on08_put(c,r.a[5],0x5aea,4,r.d[6]) || !on08_put(c,r.a[5],0x5aee,4,r.d[7]))return false;
        r.d[7]|=r.d[6];r.pc=r.d[7]==0U?0x4b4da:0x4aef0;return true;
    // MOVE.L a(A0),D0; MOVE.L e(A0),D1; BTST.B #1,15(A6); BEQ.W 4af06.
    case 0x4aef0:
        if(!on08_get(c,r.a[0],0xa,4,value) || !on08_get(c,r.a[0],0xe,4,v1))return false;r.d[0]=value;r.d[1]=v1;
        if(!on08_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&2U)==0U?0x4af06:0x4af02;return true;
    case 0x4af02:on08_flip(r);r.pc=0x4af06;return true;                                  // ADD.W D1,D0; NEG.W D0.
    // ADD.W 46(A6),D0; SWAP D0; SWAP D1; BTST.B #0,15(A6); BEQ.W 4af1c.
    case 0x4af06:
        if(!on08_get(c,r.a[6],0x46,2,value))return false;on08_add_w(r.d[0],value);am_swap(r.d[0]);am_swap(r.d[1]);
        if(!on08_get(c,r.a[6],0x15,1,value))return false;r.pc=(value&1U)==0U?0x4af1c:0x4af18;return true;
    case 0x4af18:on08_flip(r);r.pc=0x4af1c;return true;                                  // ADD.W D1,D0; NEG.W D0.
    // ADD.W 42(A6),D0; MOVE.W #ffe0,D6; MOVE.W #15f,D7; ADD.W D0,D1; CMP.W D7,D0; BGT.W 4b4da.
    case 0x4af1c:
        if(!on08_get(c,r.a[6],0x42,2,value))return false;on08_add_w(r.d[0],value);am_word(r.d[6],0xffe0);am_word(r.d[7],0x15f);
        on08_add_w(r.d[1],r.d[0]);on08_sub(r.d[0],r.d[7],f);r.pc=on08_gt(f)?0x4b4da:0x4af30;return true;
    // CMP.W D6,D1; BLT.W 4b4da (both axes).
    case 0x4af30:on08_sub(r.d[1],r.d[6],f);r.pc=on08_lt(f)?0x4b4da:0x4af36;return true;
    case 0x4af5c:on08_sub(r.d[1],r.d[6],f);r.pc=on08_lt(f)?0x4b4da:0x4af62;return true;
    // SUB.W D6,D0; BGE.W (else CLR.W D0).
    case 0x4af36:am_word(r.d[0],on08_sub(r.d[0],r.d[6],f));r.pc=on08_ge(f)?0x4af3e:0x4af3c;return true;
    case 0x4af62:am_word(r.d[0],on08_sub(r.d[0],r.d[6],f));r.pc=on08_ge(f)?0x4af6a:0x4af68;return true;
    case 0x4af3c:am_word(r.d[0],0);r.pc=0x4af3e;return true;                             // CLR.W D0.
    case 0x4af68:am_word(r.d[0],0);r.pc=0x4af6a;return true;
    // CMP.W D7,D1; BLE.W (else MOVE.W D7,D1).
    case 0x4af3e:on08_sub(r.d[1],r.d[7],f);r.pc=on08_le(f)?0x4af46:0x4af44;return true;
    case 0x4af6a:on08_sub(r.d[1],r.d[7],f);r.pc=on08_le(f)?0x4af72:0x4af70;return true;
    case 0x4af44:am_word(r.d[1],r.d[7]);r.pc=0x4af46;return true;
    case 0x4af70:am_word(r.d[1],r.d[7]);r.pc=0x4af72;return true;
    // SUB.W D6,D1; SWAP D0; SWAP D1; MOVE.W #100,D6; MOVE.W #1ff,D7; ADD.W D0,D1; CMP.W D7,D0; BGT.W 4b4da.
    case 0x4af46:
        am_word(r.d[1],on08_sub(r.d[1],r.d[6],f));am_swap(r.d[0]);am_swap(r.d[1]);am_word(r.d[6],0x100);am_word(r.d[7],0x1ff);
        on08_add_w(r.d[1],r.d[0]);on08_sub(r.d[0],r.d[7],f);r.pc=on08_gt(f)?0x4b4da:0x4af5c;return true;
    // SUB.W D6,D1; LSR.L #5,D0; LSR.L #5,D1; MOVE.W #7ff,D6; AND.W D6,D0; AND.W D6,D1; SUB.L D0,D1; LSL.L #3,D0; LEA 60(A4,D0.W),A3;
    // MOVEQ #0,D6; MOVEQ #0,D7.
    case 0x4af72:
        am_word(r.d[1],on08_sub(r.d[1],r.d[6],f));r.d[0]>>=5;r.d[1]>>=5;am_word(r.d[6],0x7ff);
        am_word(r.d[0],on08_w(r.d[0])&on08_w(r.d[6]));am_word(r.d[1],on08_w(r.d[1])&on08_w(r.d[6]));r.d[1]-=r.d[0];r.d[0]<<=3;
        r.a[3]=am_index(r.a[4]+0x60U,r.d[0]);r.d[6]=0;r.d[7]=0;r.pc=0x4af8c;return true;
    case 0x4af8c:return on08_rows(c,0x4af8c,0x4af94);                                    // OR.L (A3)+,D6; OR.L (A3)+,D7; DBRA D1.
    // LEA 5aea(A5),A3; AND.L (A3),D6; MOVE.L D6,(A3)+; AND.L (A3),D7; MOVE.L D7,(A3)+; OR.L D6,D7; BEQ.W 4b4da.
    case 0x4af94:
        r.a[3]=am_index(r.a[5],0x5aea);if(!am_read(c,r.a[3],4,value))return false;r.d[6]&=value;
        if(!am_write(c,r.a[3],4,r.d[6]))return false;r.a[3]+=4U;if(!am_read(c,r.a[3],4,value))return false;r.d[7]&=value;
        if(!am_write(c,r.a[3],4,r.d[7]))return false;r.a[3]+=4U;r.d[7]|=r.d[6];r.pc=r.d[7]==0U?0x4b4da:0x4afa6;return true;
    // SWAP D0; SWAP D1; LEA (A4,D0.W),A3; MOVEQ #0,D7; MOVEQ #0,D6.
    case 0x4afa6:am_swap(r.d[0]);am_swap(r.d[1]);r.a[3]=am_index(r.a[4],r.d[0]);r.d[7]=0;r.d[6]=0;r.pc=0x4afb2;return true;
    case 0x4afb2:return on08_rows(c,0x4afb2,0x4afba);
    // LEA 5aea(A5),A3; AND.L (A3)+,D6; AND.L (A3)+,D7; MOVE.L D6,D3; OR.L D7,D3; BEQ.W 4b4da.
    case 0x4afba:
        r.a[3]=am_index(r.a[5],0x5aea);if(!am_read(c,r.a[3],4,value))return false;r.d[6]&=value;r.a[3]+=4U;
        if(!am_read(c,r.a[3],4,value))return false;r.d[7]&=value;r.a[3]+=4U;r.d[3]=r.d[6]|r.d[7];r.pc=r.d[3]==0U?0x4b4da:0x4afca;return true;
    case 0x4afca:r.pc=r.d[7]==0U?0x4b252:0x4afd0;return true;                            // TST.L D7; BEQ.W 4b252.
    case 0x4b252:r.pc=r.d[6]==0U?0x4b4da:0x4b258;return true;                            // TST.L D6; BEQ.W 4b4da.

    // ---- 4afd0..4b4d0: the 128 bit-scan blocks (8 groups: head, 8 candidates, 7 additions).
    // group 0 (D7.B): head 4afd0, candidates 4afda+14k, additions 4afe4+14k.
    case 0x4afd0:return on08_head(c,7,1,false,0x4b070,0x4afe4,0x4afda);
    case 0x4afda:return on08_hit(c,0xec,0x7,0x4afe4);
    case 0x4afe4:return on08_add(c,7,1,0x4b070,0x4aff8,0x4afee);
    case 0x4afee:return on08_hit(c,0xe8,0x6,0x4aff8);
    case 0x4aff8:return on08_add(c,7,1,0x4b070,0x4b00c,0x4b002);
    case 0x4b002:return on08_hit(c,0xe4,0x5,0x4b00c);
    case 0x4b00c:return on08_add(c,7,1,0x4b070,0x4b020,0x4b016);
    case 0x4b016:return on08_hit(c,0xe0,0x4,0x4b020);
    case 0x4b020:return on08_add(c,7,1,0x4b070,0x4b034,0x4b02a);
    case 0x4b02a:return on08_hit(c,0xdc,0x3,0x4b034);
    case 0x4b034:return on08_add(c,7,1,0x4b070,0x4b048,0x4b03e);
    case 0x4b03e:return on08_hit(c,0xd8,0x2,0x4b048);
    case 0x4b048:return on08_add(c,7,1,0x4b070,0x4b05c,0x4b052);
    case 0x4b052:return on08_hit(c,0xd4,0x1,0x4b05c);
    case 0x4b05c:return on08_add(c,7,1,0x4b070,0x4b070,0x4b066);
    case 0x4b066:return on08_hit(c,0xd0,0x0,0x4b070);
    // group 1 (D7.W): head 4b070, candidates 4b07a+14k, additions 4b084+14k.
    case 0x4b070:return on08_head(c,7,2,false,0x4b110,0x4b084,0x4b07a);
    case 0x4b07a:return on08_hit(c,0x10c,0xf,0x4b084);
    case 0x4b084:return on08_add(c,7,2,0x4b110,0x4b098,0x4b08e);
    case 0x4b08e:return on08_hit(c,0x108,0xe,0x4b098);
    case 0x4b098:return on08_add(c,7,2,0x4b110,0x4b0ac,0x4b0a2);
    case 0x4b0a2:return on08_hit(c,0x104,0xd,0x4b0ac);
    case 0x4b0ac:return on08_add(c,7,2,0x4b110,0x4b0c0,0x4b0b6);
    case 0x4b0b6:return on08_hit(c,0x100,0xc,0x4b0c0);
    case 0x4b0c0:return on08_add(c,7,2,0x4b110,0x4b0d4,0x4b0ca);
    case 0x4b0ca:return on08_hit(c,0xfc,0xb,0x4b0d4);
    case 0x4b0d4:return on08_add(c,7,2,0x4b110,0x4b0e8,0x4b0de);
    case 0x4b0de:return on08_hit(c,0xf8,0xa,0x4b0e8);
    case 0x4b0e8:return on08_add(c,7,2,0x4b110,0x4b0fc,0x4b0f2);
    case 0x4b0f2:return on08_hit(c,0xf4,0x9,0x4b0fc);
    case 0x4b0fc:return on08_add(c,7,2,0x4b110,0x4b110,0x4b106);
    case 0x4b106:return on08_hit(c,0xf0,0x8,0x4b110);
    // group 2 (D7.B): head 4b110, candidates 4b11c+14k, additions 4b126+14k.
    case 0x4b110:return on08_head(c,7,1,true,0x4b1b2,0x4b126,0x4b11c);
    case 0x4b11c:return on08_hit(c,0x12c,0x17,0x4b126);
    case 0x4b126:return on08_add(c,7,1,0x4b1b2,0x4b13a,0x4b130);
    case 0x4b130:return on08_hit(c,0x128,0x16,0x4b13a);
    case 0x4b13a:return on08_add(c,7,1,0x4b1b2,0x4b14e,0x4b144);
    case 0x4b144:return on08_hit(c,0x124,0x15,0x4b14e);
    case 0x4b14e:return on08_add(c,7,1,0x4b1b2,0x4b162,0x4b158);
    case 0x4b158:return on08_hit(c,0x120,0x14,0x4b162);
    case 0x4b162:return on08_add(c,7,1,0x4b1b2,0x4b176,0x4b16c);
    case 0x4b16c:return on08_hit(c,0x11c,0x13,0x4b176);
    case 0x4b176:return on08_add(c,7,1,0x4b1b2,0x4b18a,0x4b180);
    case 0x4b180:return on08_hit(c,0x118,0x12,0x4b18a);
    case 0x4b18a:return on08_add(c,7,1,0x4b1b2,0x4b19e,0x4b194);
    case 0x4b194:return on08_hit(c,0x114,0x11,0x4b19e);
    case 0x4b19e:return on08_add(c,7,1,0x4b1b2,0x4b1b2,0x4b1a8);
    case 0x4b1a8:return on08_hit(c,0x110,0x10,0x4b1b2);
    // group 3 (D7.W): head 4b1b2, candidates 4b1bc+14k, additions 4b1c6+14k.
    case 0x4b1b2:return on08_head(c,7,2,false,0x4b252,0x4b1c6,0x4b1bc);
    case 0x4b1bc:return on08_hit(c,0x14c,0x1f,0x4b1c6);
    case 0x4b1c6:return on08_add(c,7,2,0x4b252,0x4b1da,0x4b1d0);
    case 0x4b1d0:return on08_hit(c,0x148,0x1e,0x4b1da);
    case 0x4b1da:return on08_add(c,7,2,0x4b252,0x4b1ee,0x4b1e4);
    case 0x4b1e4:return on08_hit(c,0x144,0x1d,0x4b1ee);
    case 0x4b1ee:return on08_add(c,7,2,0x4b252,0x4b202,0x4b1f8);
    case 0x4b1f8:return on08_hit(c,0x140,0x1c,0x4b202);
    case 0x4b202:return on08_add(c,7,2,0x4b252,0x4b216,0x4b20c);
    case 0x4b20c:return on08_hit(c,0x13c,0x1b,0x4b216);
    case 0x4b216:return on08_add(c,7,2,0x4b252,0x4b22a,0x4b220);
    case 0x4b220:return on08_hit(c,0x138,0x1a,0x4b22a);
    case 0x4b22a:return on08_add(c,7,2,0x4b252,0x4b23e,0x4b234);
    case 0x4b234:return on08_hit(c,0x134,0x19,0x4b23e);
    case 0x4b23e:return on08_add(c,7,2,0x4b252,0x4b252,0x4b248);
    case 0x4b248:return on08_hit(c,0x130,0x18,0x4b252);
    // group 4 (D6.B): head 4b258, candidates 4b262+14k, additions 4b26c+14k.
    case 0x4b258:return on08_head(c,6,1,false,0x4b2f8,0x4b26c,0x4b262);
    case 0x4b262:return on08_hit(c,0x16c,0x27,0x4b26c);
    case 0x4b26c:return on08_add(c,6,1,0x4b2f8,0x4b280,0x4b276);
    case 0x4b276:return on08_hit(c,0x168,0x26,0x4b280);
    case 0x4b280:return on08_add(c,6,1,0x4b2f8,0x4b294,0x4b28a);
    case 0x4b28a:return on08_hit(c,0x164,0x25,0x4b294);
    case 0x4b294:return on08_add(c,6,1,0x4b2f8,0x4b2a8,0x4b29e);
    case 0x4b29e:return on08_hit(c,0x160,0x24,0x4b2a8);
    case 0x4b2a8:return on08_add(c,6,1,0x4b2f8,0x4b2bc,0x4b2b2);
    case 0x4b2b2:return on08_hit(c,0x15c,0x23,0x4b2bc);
    case 0x4b2bc:return on08_add(c,6,1,0x4b2f8,0x4b2d0,0x4b2c6);
    case 0x4b2c6:return on08_hit(c,0x158,0x22,0x4b2d0);
    case 0x4b2d0:return on08_add(c,6,1,0x4b2f8,0x4b2e4,0x4b2da);
    case 0x4b2da:return on08_hit(c,0x154,0x21,0x4b2e4);
    case 0x4b2e4:return on08_add(c,6,1,0x4b2f8,0x4b2f8,0x4b2ee);
    case 0x4b2ee:return on08_hit(c,0x150,0x20,0x4b2f8);
    // group 5 (D6.W): head 4b2f8, candidates 4b302+14k, additions 4b30c+14k.
    case 0x4b2f8:return on08_head(c,6,2,false,0x4b398,0x4b30c,0x4b302);
    case 0x4b302:return on08_hit(c,0x18c,0x2f,0x4b30c);
    case 0x4b30c:return on08_add(c,6,2,0x4b398,0x4b320,0x4b316);
    case 0x4b316:return on08_hit(c,0x188,0x2e,0x4b320);
    case 0x4b320:return on08_add(c,6,2,0x4b398,0x4b334,0x4b32a);
    case 0x4b32a:return on08_hit(c,0x184,0x2d,0x4b334);
    case 0x4b334:return on08_add(c,6,2,0x4b398,0x4b348,0x4b33e);
    case 0x4b33e:return on08_hit(c,0x180,0x2c,0x4b348);
    case 0x4b348:return on08_add(c,6,2,0x4b398,0x4b35c,0x4b352);
    case 0x4b352:return on08_hit(c,0x17c,0x2b,0x4b35c);
    case 0x4b35c:return on08_add(c,6,2,0x4b398,0x4b370,0x4b366);
    case 0x4b366:return on08_hit(c,0x178,0x2a,0x4b370);
    case 0x4b370:return on08_add(c,6,2,0x4b398,0x4b384,0x4b37a);
    case 0x4b37a:return on08_hit(c,0x174,0x29,0x4b384);
    case 0x4b384:return on08_add(c,6,2,0x4b398,0x4b398,0x4b38e);
    case 0x4b38e:return on08_hit(c,0x170,0x28,0x4b398);
    // group 6 (D6.B): head 4b398, candidates 4b3a4+14k, additions 4b3ae+14k.
    case 0x4b398:return on08_head(c,6,1,true,0x4b43a,0x4b3ae,0x4b3a4);
    case 0x4b3a4:return on08_hit(c,0x1ac,0x37,0x4b3ae);
    case 0x4b3ae:return on08_add(c,6,1,0x4b43a,0x4b3c2,0x4b3b8);
    case 0x4b3b8:return on08_hit(c,0x1a8,0x36,0x4b3c2);
    case 0x4b3c2:return on08_add(c,6,1,0x4b43a,0x4b3d6,0x4b3cc);
    case 0x4b3cc:return on08_hit(c,0x1a4,0x35,0x4b3d6);
    case 0x4b3d6:return on08_add(c,6,1,0x4b43a,0x4b3ea,0x4b3e0);
    case 0x4b3e0:return on08_hit(c,0x1a0,0x34,0x4b3ea);
    case 0x4b3ea:return on08_add(c,6,1,0x4b43a,0x4b3fe,0x4b3f4);
    case 0x4b3f4:return on08_hit(c,0x19c,0x33,0x4b3fe);
    case 0x4b3fe:return on08_add(c,6,1,0x4b43a,0x4b412,0x4b408);
    case 0x4b408:return on08_hit(c,0x198,0x32,0x4b412);
    case 0x4b412:return on08_add(c,6,1,0x4b43a,0x4b426,0x4b41c);
    case 0x4b41c:return on08_hit(c,0x194,0x31,0x4b426);
    case 0x4b426:return on08_add(c,6,1,0x4b43a,0x4b43a,0x4b430);
    case 0x4b430:return on08_hit(c,0x190,0x30,0x4b43a);
    // group 7 (D6.W): head 4b43a, candidates 4b444+14k, additions 4b44e+14k.
    case 0x4b43a:return on08_head(c,6,2,false,0x4b4da,0x4b44e,0x4b444);
    case 0x4b444:return on08_hit(c,0x1cc,0x3f,0x4b44e);
    case 0x4b44e:return on08_add(c,6,2,0x4b4da,0x4b462,0x4b458);
    case 0x4b458:return on08_hit(c,0x1c8,0x3e,0x4b462);
    case 0x4b462:return on08_add(c,6,2,0x4b4da,0x4b476,0x4b46c);
    case 0x4b46c:return on08_hit(c,0x1c4,0x3d,0x4b476);
    case 0x4b476:return on08_add(c,6,2,0x4b4da,0x4b48a,0x4b480);
    case 0x4b480:return on08_hit(c,0x1c0,0x3c,0x4b48a);
    case 0x4b48a:return on08_add(c,6,2,0x4b4da,0x4b49e,0x4b494);
    case 0x4b494:return on08_hit(c,0x1bc,0x3b,0x4b49e);
    case 0x4b49e:return on08_add(c,6,2,0x4b4da,0x4b4b2,0x4b4a8);
    case 0x4b4a8:return on08_hit(c,0x1b8,0x3a,0x4b4b2);
    case 0x4b4b2:return on08_add(c,6,2,0x4b4da,0x4b4c6,0x4b4bc);
    case 0x4b4bc:return on08_hit(c,0x1b4,0x39,0x4b4c6);
    case 0x4b4c6:return on08_add(c,6,2,0x4b4da,0x4b4da,0x4b4d0);
    case 0x4b4d0:return on08_hit(c,0x1b0,0x38,0x4b4da);

    // ---- 4b4da: BTST.B #5,10f000.L; BEQ.W 4b4fa.
    case 0x4b4da:if(!am_read(c,0x10f000,1,value))return false;r.pc=(value&0x20U)==0U?0x4b4fa:0x4b4e6;return true;
    case 0x4b4e6:r.a[0]+=0x12U;r.pc=0x4b4ea;return true;                                  // LEA 12(A0),A0.
    case 0x4b4ea:r.d[7]=0x22b;return am_call(c,0x4b784,0x4b4f4);                          // MOVE.L #22b,D7; JSR 4b784(PC).
    case 0x4b4f4:if(!am_read(c,r.a[0],2,value))return false;r.pc=value!=0x8000U?0x4b4ea:0x4b4fa;return true; // CMPI.W #8000,(A0); BNE.B 4b4ea.
    // MOVE.W 5af2(A5),D0; MOVEA.L 5b78(A5),A0; MOVEA.L 5b7e(A5),A1; MOVEA.L 5af4(A5),A2; RTS.
    case 0x4b4fa:
        if(!on08_get(c,r.a[5],0x5af2,2,value))return false;am_word(r.d[0],value);
        if(!on08_get(c,r.a[5],0x5b78,4,value))return false;r.a[0]=value;if(!on08_get(c,r.a[5],0x5b7e,4,value))return false;r.a[1]=value;
        if(!on08_get(c,r.a[5],0x5af4,4,value))return false;r.a[2]=value;return am_return(c);
    default:return am_error(c,"unsupported animation objects n08 PC");
    }
}
}
