#include "animation_machine_internal.h"
namespace ms5 {
namespace {
// 44ade JMP 44ae2(PC,D7.W): the 96 BRA.W entries 44ae2+4k (k = 0..5f) transcribed from the original code (decision 4). The callers
// (U08b 46384/46498) pass D7.W = 4k (k < 60, 160 filtered out before the call); the jump itself moves to the computed PC (F1
// decision 3).
const std::uint32_t OU20_TABLE=0x44ae2;
const unsigned int OU20_TABLE_ENTRIES=96;
const std::uint32_t OU20_TARGETS[OU20_TABLE_ENTRIES]={
    0x44f5c,0x45154,0x45066,0x45044,0x44f78,0x45132,0x45088,0x45022,0x44f9a,0x45110,0x450aa,0x45000,0x44fbc,0x450ee,0x450cc,0x44fde,
    0x44fde,0x450cc,0x450ee,0x44fbc,0x45000,0x450aa,0x45110,0x44f9a,0x45022,0x45088,0x45132,0x44f78,0x45044,0x45066,0x45154,0x44f5c,
    0x44c70,0x44c80,0x44c80,0x44c70,0x44cde,0x44d38,0x44cf0,0x44c96,0x44cc6,0x44d20,0x44d08,0x44cae,0x44cae,0x44d08,0x44d20,0x44cc6,
    0x44c96,0x44cf0,0x44d38,0x44cde,0x44d68,0x44d92,0x44d7a,0x44d50,0x44d50,0x44d7a,0x44d92,0x44d68,0x44daa,0x44dba,0x44dba,0x44daa,
    0x44dd0,0x44e30,0x44e0e,0x44dec,0x44dec,0x44e0e,0x44e30,0x44dd0,0x44e52,0x44f3a,0x44ed4,0x44eb2,0x44e6e,0x44f18,0x44ef6,0x44e90,
    0x44e90,0x44ef6,0x44f18,0x44e6e,0x44eb2,0x44ed4,0x44f3a,0x44e52,0x44c62,0x44c62,0x44c62,0x44c62,0x44c62,0x44c6a,0x44c62,0x44c62};
const std::uint32_t OU20_NO_HEIGHT=0x44c62;  // MOVE.L #80000000,D6; RTS (the out-of-range branch of every checked leaf).
const std::uint32_t OU20_FLAG=0x10fd92;      // TST.B 10fd92.L (497a6; absolute work RAM BYTE).
// MOVE.L #7ffff,D6; MOVE.L D6,D4; AND.L D1,D4; SUBI.L #k,D4 (k = 0: no SUBI; the result is the same).
void ou20_mask(AnimationMachineState& r,std::uint32_t k) {r.d[6]=0x7ffffU;r.d[4]=((r.d[6]&r.d[1])-k)&0xffffffffU;}
// ASR.L #n,D4 (n = 0..2): arithmetic shift that copies the sign bit.
std::uint32_t ou20_asr(std::uint32_t value,unsigned int n) {
    const std::uint32_t fill=(value&0x80000000U)!=0U?~(0xffffffffU>>n):0U;return ((value>>n)|fill)&0xffffffffU;
}
// AND.L D0,D6; ADD.L D4,D6 (add) or SUB.L D4,D6; RTS.
bool ou20_combine(AnimationMachineContext& c,bool add) {
    AnimationMachineState& r=c.s;const std::uint32_t d6=r.d[6]&r.d[0];
    r.d[6]=(add?(d6+r.d[4]):(d6-r.d[4]))&0xffffffffU;return am_return(c);
}
// Slope leaf without a range check: mask, ASR.L #shift,D4 (shift 0: no ASR), combine.
bool ou20_slope(AnimationMachineContext& c,std::uint32_t k,unsigned int shift,bool add) {
    ou20_mask(c.s,k);c.s.d[4]=ou20_asr(c.s.d[4],shift);return ou20_combine(c,add);
}
// Range-checked head: mask; CMPI.L #limit,D4; BCC.W 44c62 (taken when D4 >= limit unsigned, high_fails) or BCS.W 44c62 (taken when
// D4 < limit unsigned).
void ou20_check(AnimationMachineState& r,std::uint32_t k,std::uint32_t limit,bool high_fails,std::uint32_t tail_pc) {
    ou20_mask(r,k);const bool below=r.d[4]<limit;r.pc=(high_fails?!below:below)?OU20_NO_HEIGHT:tail_pc;
}
// Range-checked tail: LSL.L #shift,D4; AND.L D0,D6; SUB.L/ADD.L D4,D6; RTS.
bool ou20_scale(AnimationMachineContext& c,unsigned int shift,bool add) {
    c.s.d[4]=(c.s.d[4]<<shift)&0xffffffffU;return ou20_combine(c,add);
}
// TST.B 549e(A5); BNE.B 44c62 (otherwise next_pc).
bool ou20_flag(AnimationMachineContext& c,std::uint32_t next_pc) {
    std::uint32_t value=0;if(!am_read(c,am_index(c.s.a[5],0x549e),1,value))return false;c.s.pc=value!=0U?OU20_NO_HEIGHT:next_pc;return true;
}
}
// Objects F4 U20a (177 block starts, the first part of the proposed U20 split): the terrain jump table function 44ade (all 96
// BRA.W entries 44ae2..44c5e) with its height leaves 44c62..45174 (D6 from D0/D1 with the 19-bit fraction mask 7ffff, D4 kept as
// scratch, 44c62 = no height 80000000), and C3 492d0 (BCHG #0,15(A6)) / 497a6 (TST.B 10fd92: C clear when the BYTE is not 0,
// otherwise 497b0 sets C). 44ade moves to the computed PC 44ae2+D7.W through the routing (entries are block starts; other values
// reach the routing like the original jump). U20a calls no other executor, has no carry consumer and produces known C only in
// 497a6 (Clear) and 497b0 (Set).
bool animation_objects_u20_block(AnimationMachineContext& c) {
    AnimationMachineState& r=c.s;std::uint32_t value=0;
    switch(r.pc) {
    // ---- 44ade: JMP 44ae2(PC,D7.W) (computed PC through the routing).
    case 0x44ade:r.pc=am_index(OU20_TABLE,r.d[7]);return true;

    // ---- Shared and special targets.
    case 0x44c62:r.d[6]=0x80000000U;return am_return(c);                     // MOVE.L #80000000,D6; RTS.
    case 0x44c6a:r.pc=(r.d[2]&0x80000000U)!=0U?0x44c80:0x44c70;return true;  // TST.L D2; BLT.W 44c80.
    case 0x44c70:return ou20_flag(c,0x44c76);                                 // TST.B 549e(A5); BNE.B 44c62.
    case 0x44c76:r.d[6]=r.d[0]&0x7ffffU;return am_return(c);                 // MOVE.L D0,D6; ANDI.L #7ffff,D6; RTS.
    case 0x44c80:return ou20_flag(c,0x44c86);                                 // TST.B 549e(A5); BNE.B 44c62.
    // MOVE.L #7ffff,D4; MOVE.L D0,D6; AND.L D4,D6; NOT.L D4; ADD.L D4,D6; RTS.
    case 0x44c86:r.d[4]=0x7ffffU;r.d[6]=r.d[0]&r.d[4];r.d[4]=~r.d[4]&0xffffffffU;r.d[6]=(r.d[6]+r.d[4])&0xffffffffU;return am_return(c);
    // ---- Slope leaves without a range check: MOVE.L #7ffff,D6; MOVE.L D6,D4; AND.L D1,D4; [SUBI.L #k,D4;] [ASR.L #s,D4;]
    // AND.L D0,D6; ADD.L/SUB.L D4,D6; RTS.
    case 0x44c96:return ou20_slope(c,0xffe80000U,2,false);
    case 0x44cae:return ou20_slope(c,0xfff00000U,2,false);
    case 0x44cc6:return ou20_slope(c,0xfff80000U,2,false);
    case 0x44cde:return ou20_slope(c,0x0U,2,false);
    case 0x44cf0:return ou20_slope(c,0x80000U,2,true);
    case 0x44d08:return ou20_slope(c,0x100000U,2,true);
    case 0x44d20:return ou20_slope(c,0x180000U,2,true);
    case 0x44d38:return ou20_slope(c,0x200000U,2,true);
    case 0x44d50:return ou20_slope(c,0xfff80000U,1,false);
    case 0x44d68:return ou20_slope(c,0x0U,1,false);
    case 0x44d7a:return ou20_slope(c,0x80000U,1,true);
    case 0x44d92:return ou20_slope(c,0x100000U,1,true);
    case 0x44daa:return ou20_slope(c,0x0U,0,false);
    case 0x44dba:return ou20_slope(c,0x80000U,0,true);
    // ---- Range-checked leaves: MOVE.L #7ffff,D6; MOVE.L D6,D4; AND.L D1,D4; [SUBI.L #k,D4;] CMPI.L #lim,D4; BCC.W/BCS.W 44c62,
    // then LSL.L #s,D4; AND.L D0,D6; SUB.L/ADD.L D4,D6; RTS (BCC heads have SUB tails, BCS heads ADD tails).
    case 0x44dd0:ou20_check(r,0x0U,0x40000U,true,0x44de4);return true;
    case 0x44de4:return ou20_scale(c,1,false);
    case 0x44dec:ou20_check(r,0x40000U,0x40000U,true,0x44e06);return true;
    case 0x44e06:return ou20_scale(c,1,false);
    case 0x44e0e:ou20_check(r,0x80000U,0xfffc0000U,false,0x44e28);return true;
    case 0x44e28:return ou20_scale(c,1,true);
    case 0x44e30:ou20_check(r,0x40000U,0xfffc0000U,false,0x44e4a);return true;
    case 0x44e4a:return ou20_scale(c,1,true);
    case 0x44e52:ou20_check(r,0x0U,0x20000U,true,0x44e66);return true;
    case 0x44e66:return ou20_scale(c,2,false);
    case 0x44e6e:ou20_check(r,0x20000U,0x20000U,true,0x44e88);return true;
    case 0x44e88:return ou20_scale(c,2,false);
    case 0x44e90:ou20_check(r,0x40000U,0x20000U,true,0x44eaa);return true;
    case 0x44eaa:return ou20_scale(c,2,false);
    case 0x44eb2:ou20_check(r,0x60000U,0x20000U,true,0x44ecc);return true;
    case 0x44ecc:return ou20_scale(c,2,false);
    case 0x44ed4:ou20_check(r,0x80000U,0xfffe0000U,false,0x44eee);return true;
    case 0x44eee:return ou20_scale(c,2,true);
    case 0x44ef6:ou20_check(r,0x60000U,0xfffe0000U,false,0x44f10);return true;
    case 0x44f10:return ou20_scale(c,2,true);
    case 0x44f18:ou20_check(r,0x40000U,0xfffe0000U,false,0x44f32);return true;
    case 0x44f32:return ou20_scale(c,2,true);
    case 0x44f3a:ou20_check(r,0x20000U,0xfffe0000U,false,0x44f54);return true;
    case 0x44f54:return ou20_scale(c,2,true);
    case 0x44f5c:ou20_check(r,0x0U,0x10000U,true,0x44f70);return true;
    case 0x44f70:return ou20_scale(c,3,false);
    case 0x44f78:ou20_check(r,0x10000U,0x10000U,true,0x44f92);return true;
    case 0x44f92:return ou20_scale(c,3,false);
    case 0x44f9a:ou20_check(r,0x20000U,0x10000U,true,0x44fb4);return true;
    case 0x44fb4:return ou20_scale(c,3,false);
    case 0x44fbc:ou20_check(r,0x30000U,0x10000U,true,0x44fd6);return true;
    case 0x44fd6:return ou20_scale(c,3,false);
    case 0x44fde:ou20_check(r,0x40000U,0x10000U,true,0x44ff8);return true;
    case 0x44ff8:return ou20_scale(c,3,false);
    case 0x45000:ou20_check(r,0x50000U,0x10000U,true,0x4501a);return true;
    case 0x4501a:return ou20_scale(c,3,false);
    case 0x45022:ou20_check(r,0x60000U,0x10000U,true,0x4503c);return true;
    case 0x4503c:return ou20_scale(c,3,false);
    case 0x45044:ou20_check(r,0x70000U,0x10000U,true,0x4505e);return true;
    case 0x4505e:return ou20_scale(c,3,false);
    case 0x45066:ou20_check(r,0x80000U,0xffff0000U,false,0x45080);return true;
    case 0x45080:return ou20_scale(c,3,true);
    case 0x45088:ou20_check(r,0x70000U,0xffff0000U,false,0x450a2);return true;
    case 0x450a2:return ou20_scale(c,3,true);
    case 0x450aa:ou20_check(r,0x60000U,0xffff0000U,false,0x450c4);return true;
    case 0x450c4:return ou20_scale(c,3,true);
    case 0x450cc:ou20_check(r,0x50000U,0xffff0000U,false,0x450e6);return true;
    case 0x450e6:return ou20_scale(c,3,true);
    case 0x450ee:ou20_check(r,0x40000U,0xffff0000U,false,0x45108);return true;
    case 0x45108:return ou20_scale(c,3,true);
    case 0x45110:ou20_check(r,0x30000U,0xffff0000U,false,0x4512a);return true;
    case 0x4512a:return ou20_scale(c,3,true);
    case 0x45132:ou20_check(r,0x20000U,0xffff0000U,false,0x4514c);return true;
    case 0x4514c:return ou20_scale(c,3,true);
    case 0x45154:ou20_check(r,0x10000U,0xffff0000U,false,0x4516e);return true;
    case 0x4516e:return ou20_scale(c,3,true);

    // ---- 492d0: BCHG.B #0,15(A6); RTS (Z only).
    case 0x492d0:
        if(!am_read(c,am_index(r.a[6],0x15),1,value) || !am_write(c,am_index(r.a[6],0x15),1,(value^1U)&255U))return false;return am_return(c);
    // ---- 497a6: TST.B 10fd92.L (C clear); BNE.W 497b4.
    case 0x497a6:if(!am_read(c,OU20_FLAG,1,value))return false;r.carry=AnimationCarryClear;r.pc=value!=0U?0x497b4:0x497b0;return true;
    case 0x497b0:r.carry=AnimationCarrySet;r.pc=0x497b4;return true;          // ORI.B #1,CCR.
    case 0x497b4:return am_return(c);                                         // RTS.
    default:
        // Table entries 44ae2+4k: BRA.W to the transcribed target. The displacement WORDs are interior PCs.
        if(r.pc>=OU20_TABLE && r.pc<OU20_TABLE+4U*OU20_TABLE_ENTRIES && ((r.pc-OU20_TABLE)&3U)==0){
            r.pc=OU20_TARGETS[(r.pc-OU20_TABLE)>>2];return true;
        }
        return am_error(c,"unsupported animation objects u20 PC");
    }
}
}
