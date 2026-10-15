#include "animation_machine_internal.h"
#include <new>
namespace ms5 {
void am_byte(std::uint32_t& r,std::uint32_t value) {r=(r&0xffffff00U)|(value&255U);}
void am_word(std::uint32_t& r,std::uint32_t value) {r=(r&0xffff0000U)|(value&65535U);}
void am_swap(std::uint32_t& r) {r=(r<<16)|(r>>16);}
std::uint32_t am_extend_word(std::uint32_t value) {
    return (value&0x8000U)?(value|0xffff0000U):(value&65535U);
}
std::uint32_t am_index(std::uint32_t base,std::uint32_t word) {return base+am_extend_word(word);}
bool am_error(AnimationMachineContext& c,const char* message) {c.error=message;return false;}
namespace {
// Declared external-read devices: WORD raster 3c0006, BYTE inputs 300000 / 340000 / 380000 and the BYTE Z80 reply 320000 (F6 scope
// decision E7; 24-bit address, exact size).
bool external_queue_device(std::uint32_t address,unsigned int size) {
    return (address==0x3c0006U && size==2) ||
        ((address==0x300000U || address==0x320000U || address==0x340000U || address==0x380000U) && size==1);
}
}
bool am_read(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t& value) {
    if ((address&0xffffffU)==0xd00046U && size==1) {
        ++c.external_reads;value=c.external_status;return true;
    }
    if (external_queue_device(address&0xffffffU,size)) {
        // The queue lives in the candidate device, so a failed run never commits the consumption.
        if (c.device.reads.empty())return am_error(c,"animation machine external read queue empty");
        const AnimationMachineExternalRead head=c.device.reads.front();
        if (head.address!=(address&0xffffffU) || head.size!=size)return am_error(c,"animation machine external read queue mismatch");
        value=size==1?(head.value&255U):(head.value&65535U);
        c.device.reads.erase(c.device.reads.begin());++c.external_reads;return true;
    }
    const std::uint32_t at=address&0xffffffU;
    if (c.palette!=0 && (size==1 || size==2 || size==4) && (size==1 || (at&1U)==0U) && at>=0x400000U && at+size<=0x800000U) {
        // Palette RAM mirror (E6): the selected 8 KiB bank at (address & 1fff); only with an attached palette device.
        const std::vector<std::uint8_t>& bank=c.palette->banks[c.palette->selected];
        value=0;for (unsigned int i=0;i<size;++i)value=(value<<8)|bank[(at+i)&0x1fffU];
        return true;
    }
    c.bus.bank_base=c.device.bank_base;
    return read_program_bus(c.ram,c.windows,c.bus,address,size,value,c.error);
}
namespace {
bool carry_preserving_pc(std::uint32_t pc) {
    // Entire original blocks must preserve C. Shared bus/stack operations do
    // not imply MOVE flags: MOVEM, PEA, JSR and RTS use those operations too.
    // F6b palette cells 7326 <= pc < 871a (BCLR (Z only)+BEQ and the MOVEM copy pairs; the even non-start PCs there are interior errors).
    if (pc>=0x7326U && pc<0x871aU)return true;
    switch(pc) {
    case 0x1dc84:case 0x1dc8a:case 0x210ae:case 0x210b4:
    case 0x47d0a:case 0x47d14:case 0x47d1a:case 0x47f04:
    case 0x47cc0:case 0x47cc6:case 0x47ce6:
    case 0x47d20:case 0x47d3e:case 0x47d42:
    case 0x4847e:case 0x48484:case 0x4848a:case 0x48490:case 0x4849c:
    case 0x484ac:case 0x484b2:case 0x1bdee:case 0x1bdf4:case 0x1bdf8:
    case 0x1be02:case 0x1be0c:case 0x1be12:case 0x1be32:case 0x1be38:
    case 0x28ac:case 0x4df0e:case 0x4df18:case 0x4e184:
    case 0x47c7a:case 0x47c88:case 0x47c8c:
    case 0x4e2c8:case 0x4e2ea:case 0x4e30c:
    case 0x4e330:case 0x4847a:case 0x8cf2:case 0x8d32:case 0x3628:case 0x35f0:
    case 0x47d24:case 0x47d2a:case 0x47d2e:case 0x47d34:
    case 0x47d58:case 0x47d5c:case 0x47d92:case 0x47d98:case 0x47da0:
    case 0x477bc:case 0x4e246:case 0x4e24c:case 0xc28:case 0xc34:
    case 0x35a8:case 0x35ee:
    case 0x47eb2:case 0x47ed6:case 0x47ee0:case 0x47ef8:case 0x47f42:case 0x47f46:
    case 0x47f4e:case 0x47f58:case 0x47f62:case 0x47f68:case 0x47f6e:case 0x47f74:
    case 0x47f7c:case 0x47f82:case 0x47f96:case 0x47fb8:case 0x47fbe:case 0x47fc4:case 0x47f3e:
    case 0x1c63c:case 0x1c642:case 0x1c648:case 0x1c658:case 0x1c65e:case 0x1c664:case 0x1c674:
    case 0x48398:case 0x483a8:case 0x3102:case 0x3c88:case 0x3d48:
    case 0x4e252:case 0xca82:case 0x8ca4:case 0x8cc8:
    case 0xca9e:case 0xcab8:case 0xcaee:case 0xcaf0:case 0xcaf2:
    case 0xcb08:case 0xcb1c:case 0xcb30:case 0xcb44:case 0xcb58:case 0xcb62:case 0x47fca:
    case 0x271c:case 0x2722:case 0x2728:case 0x2780:case 0x2782:case 0x2788:case 0x278e:
    case 0x288a:case 0x29a8:case 0x29ba:case 0x29c0:case 0x29c4:case 0x29c8:case 0x29fe:
    case 0x2a16:case 0x2a1a:case 0x2a1c:case 0x2a1e:case 0x2a24:case 0x2a26:case 0x2a3c:case 0x2a40:case 0x2a44:case 0x2a46:
    case 0x2a58:case 0x2a5c:case 0x2a5e:case 0x2a7c:case 0x2a80:case 0x2a82:
    case 0x2aa0:case 0x2aa4:case 0x2aa8:case 0x2aaa:
    case 0x8ebc:case 0x9000:case 0x9028:case 0x9036:case 0x8e80:
    case 0x43dcc:case 0x43dd4:case 0x43dd8:case 0x43e02:case 0x43e90:case 0x43ea2:
    case 0xc3e6:case 0xc3ec:case 0xc3f2:case 0xc3f8:case 0xc3fa:case 0xc400:
    case 0x4aa2e:case 0xe90d6:case 0x46ef2:case 0x46f26:case 0x46f2c:case 0x8bc0:case 0x3de4:
    case 0x477c2:case 0x477c8:case 0x477d6:case 0x477dc:case 0x477e2:case 0x47fe4:
    // Scene blocks contain only flag-preserving LEA/MOVEA/MOVEM/PEA,
    // calls, branches or RTS. Plain MOVE stack stores are intentionally absent.
    case 0x47fe8:case 0x47fec:case 0x43ffc:case 0x44004:case 0x44008:case 0x4402c:case 0x44030:
    case 0x44078:case 0x4407e:case 0x44086:case 0x4408e:case 0x44094:
    case 0x43f5c:case 0x43f60:case 0x43f70:case 0x43f94:case 0x43f9a:case 0x43faa:
    case 0x43fce:case 0x43fd4:case 0x43fda:case 0x43ff8:case 0x43ffa:
    case 0x440ec:case 0x4410a:case 0x4411c:case 0x43f3e:case 0x43f44:case 0x43f4a:case 0x43f5a:
    case 0xccd6:case 0xcd0c:case 0xcd16:case 0xcd1a:case 0xcd46:
    case 0x1adb0:case 0x1adb6:case 0x1adba:case 0x1adc0:case 0x1adc4:case 0x1adca:case 0x1adce:case 0x1add4:
    case 0x1adee:case 0x1adf2:case 0x43f3c:case 0x16f9e:case 0x16fa2:case 0x16fa6:case 0x16faa:
    case 0x182ce:case 0x1724a:case 0x1831a:
    case 0x8da2:case 0x8db8:case 0x8e44:case 0x8e48:case 0x8ea6:case 0x8eb4:
    case 0xe7bf4:case 0xe7bfa:case 0xe7bfe:case 0xe7c10:case 0xe7c36:case 0xe7c3a:case 0xe7c3e:
    case 0x47ff2:case 0x48012:case 0x4801a:case 0x4801e:case 0x48024:case 0x4802a:
    case 0x48030:case 0x48034:case 0x4803c:case 0x16fac:case 0x16fec:case 0x17010:
    case 0x16f5a:case 0x16f5e:case 0x16f6e:case 0x16f98:
    case 0x18424:case 0x18440:case 0x18448:case 0x1844c:case 0x184ce:
    case 0x18530:case 0x18552:case 0x185a2:case 0x185e8:case 0x185f2:case 0x185f8:
    case 0x18650:case 0x18654:case 0x18702:case 0x18720:case 0x1873e:case 0x18742:
    case 0x18746:case 0x1874a:case 0x1874e:case 0x18758:case 0x18760:case 0x18764:
    case 0x18768:case 0x18772:case 0x18778:case 0x1877c:case 0x18780:case 0x18784:
    case 0x18788:case 0x18796:case 0x1879a:case 0x48042:case 0x48048:case 0x17018:
    case 0x49fea:case 0x4a0e2:case 0x4a124:case 0x4a132:case 0x4a148:
    case 0x3679e:case 0x4a104:case 0x4a108:case 0x4a272:case 0x4a270:
    case 0x4a2ec:case 0x2b3f8:case 0x2b40a:
    case 0xcd50:case 0xcd56:case 0xce00:case 0xcd58:
    case 0x3ad8:case 0x3ae0:case 0x3b98:case 0x3ba8:case 0x3bca:
    case 0x3be4:case 0x3bfc:case 0x3c02:case 0xca70:
    case 0x47672:case 0x47688:case 0x4768e:case 0x476a4:
    case 0x3ad6:case 0x3af6:case 0x3b06:case 0x3b14:case 0x3b1e:
    case 0x3b28:case 0x3b3e:case 0x3b5e:case 0x3b6c:case 0x3b80:
    case 0x3b96:case 0x3bc8:case 0x3be2:case 0x3c06:case 0xca74:
    case 0x476ba:
    // Fade/card/child/dispatcher blocks: JSR/JMP/BSR/BRA/RTS/LEA/MOVEA only.
    // 290c/2916 are the RTS after ORI/ANDI CCR, which set known C first.
    case 0x48058:case 0x4807e:case 0x4809a:case 0x480a0:case 0x480b6:
    case 0x48072:case 0x48098:case 0x480b4:case 0xc376:case 0xc37c:case 0xc37e:
    case 0xc39c:case 0xc3b6:case 0xc3be:case 0x28ae:case 0x290c:case 0x2916:
    case 0x2a00:case 0x2a02:case 0x2a06:case 0x2ab8:case 0x2abe:case 0x2ac0:case 0x2ac2:case 0x2ac6:
    // Card child c250/de424/e7c16 blocks: JSR (abs or d16(PC))/JMP/RTS/LEA/MOVEA.W #0 only.
    case 0xc258:case 0xc264:case 0xc266:case 0xc274:case 0xc28e:case 0xc2a2:
    case 0xde424:case 0xde450:case 0xde456:case 0xde45a:case 0xde460:case 0xde466:
    case 0xde46c:case 0xde478:case 0xde47e:case 0xde484:case 0xde48a:
    case 0xe7c16:case 0xe7c1a:case 0xe7c1e:case 0xe7c30:
    // Card menu a0a0/38e8/c2a8 blocks: JSR/RTS/LEA only. ADDA/SUBA blocks stay Unknown.
    case 0xa0c2:case 0xa158:case 0xa17e:case 0x3878:case 0x38a4:case 0xc2a8:case 0xa2bc:case 0xc2ba:
    // Card menu open blocks: BSR/JSR/JMP/BRA/RTS/LEA/MOVEA/MOVEM/BTST and conditional branches only.
    // The a018 caller BCS blocks consume the C set by a06c (ANDI CCR) or a076 (ORI CCR).
    case 0x391a:case 0x3926:case 0x3928:case 0x392a:case 0x9b54:case 0x9b56:case 0x9b64:case 0x9b78:
    case 0x9ba6:case 0x9bc8:case 0x9bcc:case 0x9be6:case 0x9bea:case 0x9c10:case 0x9c32:case 0x9c36:
    case 0x9c50:case 0x9c54:case 0x9c76:case 0x9c98:case 0x9c9c:case 0x9cb6:case 0x9cba:case 0x9cd4:
    case 0x9cd8:case 0x9cf8:case 0x9cfc:case 0x9d1e:case 0x9d22:case 0x9d38:case 0x9d4a:case 0x9d92:
    case 0x9d96:case 0x9dc0:case 0x9dd6:case 0x9dfe:case 0x9e02:case 0x9e14:case 0x9e26:case 0x9e34:
    case 0x9e72:case 0x9e92:case 0xa008:case 0xa00c:case 0xa016:case 0xa040:case 0xa238:case 0xa348:
    case 0xa36e:case 0xa396:case 0xa3a8:case 0xa3b4:case 0xa3c6:case 0xa5e2:case 0xa61c:case 0xa624:
    case 0xbf94:case 0xbfbc:case 0xc1c4:case 0xc1e6:case 0xc1ee:case 0xc1f4:case 0xc1fe:case 0xc202:
    case 0xc208:case 0xc212:case 0xc2c6:case 0xe84d0:
    // Card menu input blocks: BSR/JSR/JMP/BRA/MOVEA/BTST/BSET/BCLR and conditional branches only.
    // SNE blocks, MOVE/MOVEQ/CMP/CMPI/TST/SUBQ/ORI/ANDI/OR blocks stay Unknown.
    case 0xa412:case 0xa41a:case 0xa42a:case 0xa442:case 0xa488:case 0xa562:case 0xa566:
    case 0xa570:case 0xa574:case 0xa57e:case 0xa714:case 0xbf50:case 0xbf8e:
    // Card menu close blocks: JSR/BSR/RTS/BCS only (a344 ADDQ.W #2,A7 stays Unknown like ADDA/SUBA).
    // a324 is the BCS that consumes the C set by a018 (a06c/a076). MOVE/MOVEQ/SWAP/CMPI/SUBQ/ADDI blocks stay Unknown.
    case 0x9ee4:case 0xa320:case 0xa324:case 0xa672:case 0xa67a:case 0xc2f8:
    // Card menu save blocks: BSR/JSR/BRA/RTS/MOVEA (+)/BCC only. c1ea is the BCC that consumes the C
    // set by be2e (ORI CCR) or be34 (ANDI CCR) in the same block as their RTS. bbb8/be0c (MOVE.L An,-(A7)),
    // MOVE/MOVEQ/EXT/ADD/NOT/ADDI/SUBQ/ANDI/MULU/TST blocks stay Unknown.
    case 0xa100:case 0xa71a:case 0xa72a:case 0xbb8c:case 0xbbd0:case 0xbd90:case 0xc1ea:
    // Card menu nested blocks: MOVEA/BSR/RTS only (a6ce, a6f8, a706). a6fc (SUBA.W), a6b2/a6ea (CMPA),
    // a6da/a6f0 (MOVE.L An stores), a698/a6bc (MOVE) and a6d6 (MOVEQ) stay Unknown.
    case 0xa6ce:case 0xa6f8:case 0xa706:
    // Frame helper (480bc U1) blocks: JSR/BSR/BRA/RTS/LEA/MOVEA/BTST/BSET and conditional branches only.
    // 4765c, b4a38 and b4a6c are the BCC blocks consuming the C returned by 289e or 49392; 493aa/493ae/493ba
    // carry the Clear set by the 4939e ANDI.W or the Set of the 493b6 ORI CCR to the RTS. DBRA blocks
    // (46faa 4700a 47016) and MOVE/MOVEQ/CMP/CMPA/TST/SUB/ADD/ANDI/ADDA/ADDQ/CLR/SNE/EXG/NOT blocks stay Unknown.
    case 0x480bc:case 0x480c0:case 0x480c6:case 0x480cc:case 0x480d2:case 0x480d8:case 0x480de:case 0x480e4:
    case 0x480ea:case 0x480f0:case 0x47656:case 0x4765c:case 0x47660:case 0x4766a:case 0x47670:case 0x6f1c2:
    case 0x2efc8:case 0x2efda:case 0x3c68:case 0xb4a38:case 0xb4a6c:case 0xb4aae:case 0x493aa:case 0x493ae:
    case 0x493ba:case 0x1c03a:case 0x1c048:case 0x1c04c:case 0x4d9e0:case 0x4d9ea:case 0x4d9fc:case 0x4da00:
    case 0xb482a:case 0xb4836:case 0xb484e:case 0x4701c:case 0x4705c:case 0x4706a:
    // Scene core (480bc U2) blocks: BSR/JSR/BRA/RTS/LEA/MOVEA/BTST and conditional branches only.
    // 1a756 1a2c6 1a302 1a30e 1a320 1a32c 1a344 1a352 are the BCC/BCS blocks consuming the C returned by
    // 1a2b4, a condition handler, 1a34c or 289e; 1a2d2 1a312 1a330 1a332 return that known C unchanged.
    // EXG/ADDA blocks and MOVE/MOVEQ/CMP/CMPA/TST/SUB/ADD/ASR/SWAP/CLR/ORI/ANDI/EORI blocks stay Unknown
    // (1a2cc 1a2e0 1a356 1a39a 1a3a0 set their known C inside the block).
    case 0x19978:case 0x199d2:case 0x19bda:case 0x19bf0:case 0x19c12:case 0x19c40:case 0x19c5c:case 0x19c68:
    case 0x19c8e:case 0x19ca0:case 0x19cc6:case 0x19d48:case 0x19d5a:case 0x19dec:case 0x1a276:case 0x1a292:
    case 0x1a29c:case 0x1a2c6:case 0x1a2ca:case 0x1a2d2:case 0x1a2d4:case 0x1a2d8:case 0x1a2dc:case 0x1a2fa:
    case 0x1a302:case 0x1a306:case 0x1a30e:case 0x1a312:case 0x1a314:case 0x1a320:case 0x1a324:case 0x1a32c:
    case 0x1a330:case 0x1a332:case 0x1a33c:case 0x1a344:case 0x1a348:case 0x1a34c:case 0x1a352:case 0x1a35c:
    case 0x1a44e:case 0x1a45a:case 0x1a464:case 0x1a466:case 0x1a756:case 0x1a75a:case 0x1a75e:case 0x1a762:
    case 0x1a766:case 0x1a784:case 0x1a788:case 0x1a78c:
    // Motion walk (480bc U3) blocks: BSR/BRA/RTS/LEA/MOVEM and conditional branches only, including the 180
    // indexed-JMP BRA.W slots. 196c0 196e2 19924 19734 198b8 1974e 19874 19894 198d8 are the BCC/BCS blocks
    // consuming the C returned by 18c06, 19710, 1971c or 192c4 (19894/198d8 after MOVEM.L (A7)+); 19398 195a0
    // 1971a 19728 return that known C. EXG blocks (19370 19578) and MOVE/MOVEQ/CMP/CMPA/TST/SUB/ADD/NEG/
    // ASR/LSL/SWAP/EXT/Scc/AND/ORI/ANDI blocks stay Unknown (18c9e 18ca4 19710 19716 1971c 19724 19372 19394
    // 1957a 1959c 196d8 set their known C inside the block).
    case 0x18c0e:case 0x18c12:case 0x18c16:case 0x18c1a:case 0x18c1e:case 0x18c22:case 0x18c26:case 0x18c2a:case 0x18c2e:case 0x18c32:
    case 0x18c36:case 0x18c3a:case 0x18c3e:case 0x18c42:case 0x18c46:case 0x18c4a:case 0x18c4e:case 0x18c52:case 0x18c56:case 0x18c5a:
    case 0x18c5e:case 0x18c62:case 0x18c66:case 0x18c6a:case 0x18c6e:case 0x18c72:case 0x18c76:case 0x18c7a:case 0x18c7e:case 0x18c82:
    case 0x18c86:case 0x18c8a:case 0x18c8e:case 0x18c92:case 0x18c96:case 0x18c9a:case 0x18cb2:case 0x18cb6:case 0x18cba:case 0x18cbe:
    case 0x18cc2:case 0x18cc6:case 0x18cca:case 0x18cce:case 0x18cd2:case 0x18cd6:case 0x18cda:case 0x18cde:case 0x18ce2:case 0x18ce6:
    case 0x18cea:case 0x18cee:case 0x18cf2:case 0x18cf6:case 0x18cfa:case 0x18cfe:case 0x18d02:case 0x18d06:case 0x18d0a:case 0x18d0e:
    case 0x18d12:case 0x18d16:case 0x18d1a:case 0x18d1e:case 0x18d22:case 0x18d26:case 0x18d2a:case 0x18d2e:case 0x18d32:case 0x18d36:
    case 0x18d3a:case 0x18d3e:case 0x18f02:case 0x18f06:case 0x18f0a:case 0x18f0e:case 0x18f12:case 0x18f16:case 0x18f1a:case 0x18f1e:
    case 0x18f22:case 0x18f26:case 0x18f2a:case 0x18f2e:case 0x18f32:case 0x18f36:case 0x18f3a:case 0x18f3e:case 0x18f42:case 0x18f46:
    case 0x18f4a:case 0x18f4e:case 0x18f52:case 0x18f56:case 0x18f5a:case 0x18f5e:case 0x18f62:case 0x18f66:case 0x18f6a:case 0x18f6e:
    case 0x18f72:case 0x18f76:case 0x18f7a:case 0x18f7e:case 0x18f82:case 0x18f86:case 0x18f8a:case 0x18f8e:case 0x18fda:case 0x18fde:
    case 0x18fe2:case 0x18fe6:case 0x18fea:case 0x18fee:case 0x18ff2:case 0x18ff6:case 0x18ffa:case 0x18ffe:case 0x19002:case 0x19006:
    case 0x1900a:case 0x1900e:case 0x19012:case 0x19016:case 0x1901a:case 0x1901e:case 0x19022:case 0x19026:case 0x1902a:case 0x1902e:
    case 0x19032:case 0x19036:case 0x1903a:case 0x1903e:case 0x19042:case 0x19046:case 0x1904a:case 0x1904e:case 0x19052:case 0x19056:
    case 0x1905a:case 0x1905e:case 0x19062:case 0x19066:case 0x192cc:case 0x192d0:case 0x192d4:case 0x192d8:case 0x192dc:case 0x192e0:
    case 0x192e4:case 0x192e8:case 0x192ec:case 0x192f0:case 0x192f4:case 0x192f8:case 0x192fc:case 0x19300:case 0x19304:case 0x19308:
    case 0x1930c:case 0x19310:case 0x19314:case 0x19318:case 0x1931c:case 0x19320:case 0x19324:case 0x19328:case 0x1932c:case 0x19330:
    case 0x19334:case 0x19338:case 0x1933c:case 0x19340:case 0x19344:case 0x19348:case 0x1934c:case 0x19350:case 0x19354:case 0x19358:
    case 0x19398:case 0x195a0:case 0x196ac:case 0x196c0:case 0x196de:case 0x196e2:case 0x196fa:case 0x1971a:case 0x19728:case 0x19732:
    case 0x19734:case 0x19738:case 0x1973a:case 0x1974c:case 0x1974e:case 0x19752:case 0x19756:case 0x1981a:case 0x19830:case 0x19870:
    case 0x19874:case 0x19878:case 0x19894:case 0x1989a:case 0x198b4:case 0x198b8:case 0x198bc:case 0x198d8:case 0x198de:case 0x19910:
    case 0x19924:
    // Scene update (480bc U4) blocks: BSR/JSR/JMP/BRA/RTS/LEA/MOVEA/MOVEM/BTST/BCLR/BSET Dn and conditional
    // branches only, including the eight 19e8a BRA.W slots and the 19e86 indexed JMP. U4 has no carry consumer
    // and no known-carry producer; MOVE/MOVEQ/CLR/ADD/SUB/SUBX/OR/AND/MULU/MULS/ASR/LSL/ROL/NEG/SWAP/TST/CMPI/
    // CMPA blocks and the DBRA blocks (1b0cc 1b0d6) stay Unknown.
    case 0x1728c:case 0x18662:case 0x186b2:case 0x18700:case 0x19e6e:case 0x19e70:case 0x19e7a:case 0x19e84:case 0x19e86:case 0x19e8a:
    case 0x19e8e:case 0x19e92:case 0x19e96:case 0x19e9a:case 0x19e9e:case 0x19ea2:case 0x19ea6:case 0x19edc:case 0x19eee:case 0x19f00:
    case 0x19f12:case 0x19f46:case 0x19f4a:case 0x19f54:case 0x19f74:case 0x19f80:case 0x19f86:case 0x19f8a:case 0x19fc0:case 0x19ff0:
    case 0x1a018:case 0x1a046:case 0x1a060:case 0x1a7f4:case 0x1a808:case 0x1a830:case 0x1a844:case 0x1a86c:case 0x1a880:case 0x1a8a8:
    case 0x1a8bc:case 0x1a8ce:case 0x1a8de:case 0x1a8ee:case 0x1a8fe:case 0x1a90e:case 0x1afec:case 0x1b00e:case 0x1b014:case 0x1b07a:
    case 0x1b0a8:case 0x1b0b8:case 0x1b0c4:case 0x1b0de:case 0x1b126:
    // Script placement (480bc U5) blocks: BSR/JMP/BRA/RTS/LEA/MOVEA/NOP and conditional branches only, including
    // the twenty 1a0bc..1a108 BRA.W slots. 197a2 is the BCC consuming the C returned by 18c06. MOVE.L An,-(A7)
    // blocks and MOVE/MOVEQ/CMP/CMPA/TST/SUB/SUBQ/ADD/AND/OR/ROL/LSL/SWAP/NEG/CLR blocks stay Unknown
    // (3d7e and 1a484 set and consume their C inside the block). U5 has no known-carry producer.
    case 0x197a2:case 0x1a086:case 0x1a09e:case 0x1a0bc:case 0x1a0c0:case 0x1a0c4:case 0x1a0c8:case 0x1a0cc:case 0x1a0d0:
    case 0x1a0d4:case 0x1a0d8:case 0x1a0dc:case 0x1a0e0:case 0x1a0e4:case 0x1a0e8:case 0x1a0ec:case 0x1a0f0:case 0x1a0f4:
    case 0x1a0f8:case 0x1a0fc:case 0x1a100:case 0x1a104:case 0x1a108:case 0x1a10c:case 0x1a116:case 0x1a182:case 0x1a1be:
    case 0x1a1cc:case 0x1a1f6:case 0x1a216:case 0x1a21c:case 0x1a23a:case 0x1a23e:case 0x1a51a:case 0xe8a02:
    // Input (480bc U6) blocks: JSR (abs, (A1) or d16(PC))/BSR/BRA/RTS/LEA/MOVEA/MOVEM/BTST/BSET/BCLR and conditional
    // branches only. 49b28 49b7e 4d7c6 are the BCC blocks consuming the C returned by 289e; 1d5b2 is the BCS
    // consuming the C returned by 4836e (48378 ANDI CCR Clear / 4837e ORI CCR Set set it inside their own block).
    // MOVE/MOVEQ/CLR/CMPI/CMPA/TST/SUB/ADDQ/SUBQ/AND/ANDI/OR/ORI/EOR/NEG/SWAP/LSL/MULU/ADDA/Scc blocks stay Unknown
    // (49ad6 sets and consumes its C inside the block). 4d7f0 (TRAP #f) has no executor.
    case 0x1d8cc:case 0x49ad4:case 0x49aec:case 0x49af4:case 0x49afc:case 0x49b1c:case 0x49b28:case 0x49b2c:case 0x49b2e:
    case 0x49b36:case 0x49b52:case 0x49b56:case 0x49b5a:case 0x49b72:case 0x49b7e:case 0x49b82:case 0x49b84:case 0x49b8c:
    case 0x49ba8:case 0x49bac:case 0x49bb0:
    case 0x1bec0:case 0x1beca:case 0x1bed8:case 0x1d5ac:case 0x1d5b2:case 0x1d5e2:case 0x1d5fa:case 0x1d61a:case 0x1d632:
    case 0x1d638:case 0x1d696:case 0x1d6f8:case 0x1da96:case 0x1dab2:case 0x1dab8:case 0x4836e:case 0x49c32:case 0x49c66:
    case 0x49e28:case 0x49e2e:case 0x49f84:case 0x4d7ac:case 0x4d7b8:case 0x4d7c0:case 0x4d7c6:
    case 0x49dd8:case 0x49de0:case 0x49de4:case 0x49e70:case 0x49e8e:case 0x49e96:case 0x49e9a:case 0x49e9c:case 0x49eb4:
    case 0x49eca:case 0x49ed2:case 0x49eea:case 0x49eee:case 0x49f00:case 0x49f10:case 0x49f26:case 0x49f2a:case 0x49f58:
    case 0x49f60:case 0x49f64:
    // Buffer/cue (480bc U7) blocks: JSR/BSR/RTS/LEA/MOVEA/BTST/BSET/BCHG and conditional branches only. 298e is the
    // 2986 tail that consumes the known C left by 28ae (290c/2916 RTS) for its MOVE SR image and restores it with
    // MOVE (A7)+,SR. EXG (4ab86), ADDA (e8ae8) and MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/ADDQ/SUBI/NEG/SWAP/EORI/OR/ANDI/
    // LSR/LSL blocks stay Unknown (their conditional branches consume flags produced inside the same block).
    case 0x4aa88:case 0x4aafc:case 0x4ab2e:case 0x4ab74:case 0x4b7ae:case 0x4b7f6:case 0xe8ab6:case 0xe8ac2:
    case 0xe8ace:case 0xe8af2:case 0xe8b08:case 0xe8b16:case 0xe8b2a:case 0xe8b46:case 0xe8b58:case 0x298e:
    // Stage entry (F1a) blocks: JSR/JMP/BSR/BRA/RTS/LEA/MOVEA/BSET and conditional branches only, including the eight
    // 47b06 BRA.W slots. 47af6 1a670 1996e 47b86 47b9c 47bd4 are the BCC blocks consuming the C returned by 72f0, 199f6
    // or U3 1971c, U3 18c06 and 28ae; 72f0 (SUBI.B) and 199f6 (ORI CCR) set their known C inside the block. ADDA (e90a6),
    // the 17292 unrolled clear and MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/AND/SUBQ/SWAP blocks stay Unknown.
    case 0x3634:case 0xc3cc:case 0x19956:case 0x1996e:case 0x199fc:case 0x19b94:case 0x19dee:case 0x19dfe:case 0x19e0e:
    case 0x19e1e:case 0x19e2e:case 0x1a420:case 0x1a42c:case 0x1a436:case 0x1a438:case 0x1a62a:case 0x1a62e:case 0x1a632:
    case 0x1a636:case 0x1a63a:case 0x1a642:case 0x1a64e:case 0x1a65a:case 0x1a65e:case 0x1a66c:case 0x1a670:case 0x1a678:
    case 0x1a71c:case 0x1a720:case 0x47aa6:case 0x47ab4:case 0x47ada:case 0x47af0:case 0x47af6:case 0x47b06:case 0x47b0a:
    case 0x47b0e:case 0x47b12:case 0x47b16:case 0x47b1a:case 0x47b1e:case 0x47b22:case 0x47b26:case 0x47b3a:case 0x47b4a:
    case 0x47b50:case 0x47b64:case 0x47b86:case 0x47b88:case 0x47b9c:case 0x47b9e:case 0x47ba2:case 0x47bd4:case 0x47c0c:
    case 0x47c12:case 0x47c18:case 0x47c28:case 0x47c36:case 0x47c3c:case 0x47c54:case 0xddf9a:case 0xe8a24:case 0xe9086:
    // Area clear (F1b) blocks: JSR/JMP/RTS/LEA/BSET/BCLR, conditional branches and Scc only (Scc leaves the CCR unchanged).
    // 1c5bc 1c5d8 are the BCC blocks consuming the C returned by 289e; 47e0a (SCC.B 62(A6); BCC) consumes the C returned
    // by 28ae. F1b has no known-carry producer. MOVE/MOVEQ/TST/SUBQ/ADDQ/CLR blocks stay Unknown.
    case 0x1c5b0:case 0x1c5bc:case 0x1c5c0:case 0x1c5cc:case 0x1c5d8:case 0x1c5dc:case 0x1c5e8:case 0x47da4:
    case 0x47daa:case 0x47db0:case 0x47dba:case 0x47dc0:case 0x47dc6:case 0x47df4:case 0x47e0a:case 0x47e2a:
    // Stage catalog (F1c1) blocks: JSR/JMP/BSR/BRA/RTS/LEA/MOVEA and conditional branches only, including the six 478ac
    // BRA.W slots. 478e4 47944 4795c 47974 are the BCC blocks consuming the C returned by 72f0 and 28ae. F1c1 has no
    // known-carry producer (the 47550 SUBQ borrow reaches no consumer). MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/SUBQ/LSL/BCLR/
    // ADDI/Scc/OR blocks and the 3d58/3d6e BYTE stack blocks stay Unknown.
    case 0x3d6a:case 0x47540:case 0x4754a:case 0x47556:case 0x47558:case 0x4782a:case 0x47830:case 0x47836:case 0x4783c:
    case 0x47886:case 0x4788c:case 0x47890:case 0x478a8:case 0x478ac:case 0x478b0:case 0x478b4:case 0x478b8:case 0x478bc:
    case 0x478c0:case 0x478de:case 0x478e4:case 0x478e6:case 0x478ec:case 0x478fe:case 0x47912:case 0x47918:case 0x4791c:
    case 0x47944:case 0x47948:case 0x4795c:case 0x47960:case 0x47974:
    // Stage area (F1c2) blocks: JSR/JMP/BSR/BRA/RTS/LEA/MOVEA and conditional branches only. 47716 47732 4776c 1bd34 1bd96
    // are the BCS blocks consuming the C returned by 289e; d7648 returns the 28ae C unconsumed. F1c2 has no known-carry
    // producer. MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/AND/ANDI/ADD/ADDQ/SUBQ/SUB/MULU/BSET/BCLR blocks, the SUBA/ADDA blocks
    // (49a6c 49a70 49a7c), the DBRA block 4aa6e and the MOVE stack blocks stay Unknown.
    case 0x3d3a:case 0x3d3e:case 0x3d42:case 0x1bcfe:case 0x1bd08:case 0x1bd24:case 0x1bd2e:case 0x1bd34:case 0x1bd38:
    case 0x1bd5c:case 0x1bd90:case 0x1bd96:case 0x1bd9a:case 0x1be90:case 0x2efe8:case 0x46f2e:case 0x46f50:case 0x4759e:
    case 0x475ae:case 0x475b4:case 0x475d4:case 0x475e0:case 0x475e6:case 0x475ec:case 0x475f2:case 0x475f8:case 0x475fe:
    case 0x47604:case 0x4760a:case 0x47610:case 0x47616:case 0x47716:case 0x47722:case 0x47732:case 0x4773e:case 0x47740:
    case 0x4774e:case 0x4775a:case 0x47760:case 0x4776c:case 0x47792:case 0x477a0:case 0x479b0:case 0x479b6:case 0x479cc:
    case 0x479d8:case 0x479e4:case 0x479ea:case 0x479fa:case 0x47a06:case 0x47a4a:case 0x47a50:case 0x47a64:case 0x47a88:
    case 0x47a8e:case 0x4818c:case 0x481ea:case 0x4aa76:case 0x4aa7e:case 0x4d126:case 0x4d130:case 0x4d13a:case 0x4d13c:
    case 0x4d146:case 0x4d150:case 0x4ddb6:case 0x4ddbe:case 0x4e666:case 0x4e66e:case 0x4e68c:case 0xb4806:case 0xb4812:
    case 0xb4a24:case 0xb4a28:case 0xb7a20:case 0xb7a24:case 0xd7648:
    // Stage event (F3a) blocks: BSR/JSR/BRA/RTS/LEA/MOVEA/BCLR and conditional branches only, including the eight e91e4
    // and the 34 e97e4 BRA.W slots and the 43e34 LEA entry of the cleanup coordinate update 43e38. e9248 e9258 are the BCC
    // blocks consuming the C returned by 49392. F3a has no known-carry producer. MOVE/MOVEQ/CLR/TST/CMP/CMPI/SUB/SUBI/SUBQ/ADD/ADDQ/ORI/LSL/EXT/Scc/LEA+MOVE blocks, the ADDA block e94c4
    // and the BYTE stack blocks (e97d4 e986c e987c..e98ea) stay Unknown.
    case 0x43e04:case 0x43e34:case 0x4855a:case 0xe9176:case 0xe9194:case 0xe9196:case 0xe91ac:case 0xe91be:case 0xe91e4:case 0xe91e8:case 0xe91ec:case 0xe91f0:
    case 0xe91f4:case 0xe91f8:case 0xe91fc:case 0xe9200:case 0xe9236:case 0xe923a:case 0xe9248:case 0xe9258:case 0xe9296:case 0xe932a:
    case 0xe9488:case 0xe9498:case 0xe94a4:case 0xe94b4:case 0xe94b8:case 0xe97e4:case 0xe97e8:case 0xe97ec:case 0xe97f0:case 0xe97f4:
    case 0xe97f8:case 0xe97fc:case 0xe9800:case 0xe9804:case 0xe9808:case 0xe980c:case 0xe9810:case 0xe9814:case 0xe9818:case 0xe981c:
    case 0xe9820:case 0xe9824:case 0xe9828:case 0xe982c:case 0xe9830:case 0xe9834:case 0xe9838:case 0xe983c:case 0xe9840:case 0xe9844:
    case 0xe9848:case 0xe984c:case 0xe9850:case 0xe9854:case 0xe9858:case 0xe985c:case 0xe9860:case 0xe9864:case 0xe9868:case 0xe9878:
    // Stage event ops (F3b) blocks: BSR/JSR/JMP/BRA/RTS/LEA/MOVEA/BTST/BSET/BCLR and conditional branches only, including
    // the three e941c, the eight e9538 and the nine e9790..e97b0 BRA.W blocks. e936e (288c/289e) and e9576 (2986) are the
    // carry consumers; 2898 sets its known C (ORI CCR) inside the block. MOVE/MOVEQ/CMP/CMPI/CMPA/SUBQ/SUBI/ADDQ/ADD/SUB/
    // LSL/LSR/MULU/SWAP/PEA blocks, the ADDA blocks e97b2 e97b8 e97be and the MOVE stack blocks stay Unknown.
    case 0xe9362:case 0xe9368:case 0xe936e:case 0xe9372:case 0xe9390:case 0xe939a:case 0xe93b0:case 0xe93c6:case 0xe93f6:case 0xe941c:
    case 0xe9420:case 0xe9424:case 0xe950a:case 0xe9514:case 0xe9516:case 0xe951a:case 0xe9538:case 0xe953c:case 0xe9540:case 0xe9544:
    case 0xe9548:case 0xe954c:case 0xe9550:case 0xe9554:case 0xe9576:case 0xe961c:case 0xe9626:case 0xe96a4:case 0xe96ac:case 0xe96b4:
    case 0xe96b8:case 0xe96c8:case 0xe96d6:case 0xe9720:case 0xe9722:case 0xe973e:case 0xe9754:case 0xe9790:case 0xe9794:case 0xe9798:
    case 0xe979c:case 0xe97a0:case 0xe97a4:case 0xe97a8:case 0xe97ac:case 0xe97b0:case 0xe97c4:case 0xe97c6:
    // Scheduler shell (F2) blocks: only the RTS blocks 271a and 4fda4 keep C. 2aac (MOVE.L), 270e (TST), 2716 (ADDQ) and the
    // 4fcce MOVE/MOVEA/ADDQ/CMPI/TST/NEG/ADD/ADDA/LSL/ADDI blocks stay Unknown. F2 has no carry consumer.
    case 0x271a:case 0x4fda4:
    // Objects U01 (F4) blocks: JSR/BSR/JMP/BRA/RTS/LEA/BCLR/BSET only, including the consumers 4b55c (4b50c), b4e26 (b4e6c)
    // and b4e60 (1aa7e) and the RTS blocks 4b6e2/b4e6a that return the C set by 4b6be (MOVE.B clears C) or 4b6ca (ORI CCR).
    // 1aaf6 4b548 (ANDI CCR) and 1aafc 4b532 (ORI CCR) set their known C inside the block. MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/
    // ADD/SUB/SUBI/SUBQ/NEG/SWAP/LSR/LSL/ASR/AND/ANDI/NOT/EXT blocks, the ADDQ.W #1,A2 and ADDA blocks and the DBRA blocks
    // stay Unknown.
    case 0x1aaaa:case 0x1aae6:case 0x48296:case 0x482a8:case 0x4b55a:case 0x4b55c:case 0x4b6aa:case 0x4b6e2:case 0xb4dc2:
    case 0xb4dc6:case 0xb4df8:case 0xb4dfe:case 0xb4e12:case 0xb4e1c:case 0xb4e22:case 0xb4e26:case 0xb4e30:case 0xb4e34:
    case 0xb4e5a:case 0xb4e60:case 0xb4e6a:case 0xb4ffe:case 0xc6a90:case 0xdd4d0:case 0xdd4ea:case 0xdd4ec:
    // Objects U02 (F4) blocks: MOVEA/LEA/BSR/JSR/JMP/BRA/RTS/MOVEM/EXG/ST and BTST (Z only) blocks, including the consumers
    // 3a7e and e56ac (C returned by 396e: 398c ORI CCR Set; 3a12/3a4c/3a68 ANDI CCR Clear, set inside those blocks).
    // MOVE/MOVEQ/CLR/TST/CMP/CMPI/ADD/ADDQ/ADDI/SUBQ/SUBI/LSL/LSR/ASR/MULS/ANDI/SEQ blocks, the ADDQ.W An blocks 39ae/8f68
    // and the BSET/BCLR + MOVE blocks stay Unknown.
    case 0x396e:case 0x39f8:case 0x3a70:case 0x3a7a:case 0x3a7e:case 0x3a80:case 0x8ecc:case 0x8efe:case 0x8f6a:
    case 0xe50b4:case 0xe50c0:case 0xe511e:case 0xe5120:case 0xe512a:case 0xe5170:case 0xe519e:case 0xe51b4:case 0xe51d8:
    case 0xe51ee:case 0xe5226:case 0xe5246:case 0xe527a:case 0xe5286:case 0xe528c:case 0xe5670:case 0xe567e:case 0xe56a0:
    case 0xe56ac:case 0xe56b0:case 0xe56be:case 0xe57f0:case 0xe583a:
    // Objects U03 (F4) blocks: BRA/LEA only and e88c0 (MOVEM.L (A7)+ and RTS keep the CCR). U03 has no carry consumer or
    // known-carry producer; every CMPI/MOVE/ADDQ/ADDI/SUBI/ANDI/OR/LSL/SWAP/TST block (the ADDQ.W #6,A1 block e8866 too) stays Unknown.
    case 0xe856a:case 0xe85b2:case 0xe85c2:case 0xe868c:case 0xe869c:case 0xe86da:case 0xe8706:case 0xe8856:case 0xe88c0:
    // Objects U05 (F4) blocks: BRA/JSR/JMP/RTS/LEA+JSR, MOVEM.L D0-D1,-(A7)+BSR (c6a96) and the BCC consumers b9752 (C returned
    // by 1ab02: 1ab7a ANDI CCR Clear set inside that block, U01 1aafc ORI CCR Set) and c6ad6/c6b20/c6b7a (C returned by the 497a6
    // boundary). MOVE/MOVEA/CMP/CMPI/TST/SUBQ/ADD/NEG/SWAP blocks, the ADDA.W block c6bf6 and the ADDQ.L #4,A1 block c6c1a stay Unknown.
    case 0x1ab2e:case 0x1ab6a:case 0xb971a:case 0xb9720:case 0xb9746:case 0xb9752:case 0xb9756:case 0xb975c:case 0xc6a96:
    case 0xc6ad0:case 0xc6ad6:case 0xc6ada:case 0xc6b1a:case 0xc6b20:case 0xc6b24:case 0xc6b74:case 0xc6b7a:case 0xc6b7e:
    case 0xc6bf4:case 0xc6c12:
    // Objects U04 (F4) blocks: BRA/RTS/LEA/JSR/JMP and the BNE d73ca (Z of the 287e CMP, recomputed) only. Every C consumer
    // is a BCC/BCS in the block of its SUBQ/CMPI/CMP; no block produces a known C. MOVE/MOVEQ/CLR/TST/CMP/CMPA/ADD/ADDQ/SUB/
    // SUBQ/SUBI/NEG/NOT/ANDI/ASR/LSL/SWAP/MULS/MULU blocks and the BSET/BCLR + MOVE blocks stay Unknown.
    case 0xce44:case 0xce60:case 0x43ea4:case 0xd72fe:case 0xd730a:case 0xd731a:case 0xd73c4:case 0xd73ca:case 0xd73ce:
    case 0xd7424:case 0xd748c:case 0xd74a2:case 0xd74d6:case 0xd7504:case 0xd75cc:
    // Objects U06 (F4) blocks: LEA/JSR/BSR/BRA/RTS, MOVEA.L (A7)+,A0+RTS, Dn BTST+BEQ (Z only) and the consumers e742c (C returned
    // by the input 4836e) and e7916 (C returned by the interpreter 49fc6). U06 has no known-carry producer. MOVE/MOVEQ/MOVEA+MOVE/
    // CLR/TST/CMP/CMPI/AND/ANDI/OR/ADD/ADDI/ADDQ/SUBQ/LSL/LSR blocks, the ADDQ.L An blocks eb7bc/eba78 and the PVC blocks stay Unknown.
    case 0x49be6:case 0x49bec:case 0xe73f8:case 0xe7426:case 0xe742c:case 0xe743a:case 0xe744e:case 0xe7462:case 0xe7478:
    case 0xe7486:case 0xe74a0:case 0xe74d6:case 0xe74ea:case 0xe74ec:case 0xe755e:case 0xe7792:case 0xe77dc:case 0xe77e2:
    case 0xe786c:case 0xe7888:case 0xe78a8:case 0xe78c0:case 0xe78d6:case 0xe78f4:case 0xe7910:case 0xe7916:case 0xe7944:
    case 0xeb83e:case 0xeb84e:case 0xeb852:case 0xeb862:case 0xeb866:case 0xeb87c:case 0xeb880:case 0xeb896:case 0xeb8ae:
    case 0xeb8ba:case 0xeb8c6:case 0xeb8d2:case 0xeb8f2:case 0xeb910:case 0xeb928:case 0xeb92c:case 0xeb942:case 0xeb96e:
    case 0xeb98e:case 0xeb9b8:
    // Objects U07 (F4) blocks: LEA/BRA/JSR/JMP/RTS only, including the BCC consumer 4e1a2 (C returned by readiness 289e: Clear when
    // the LONG at A0 is 270e, else ORI CCR Set). U07 has no known-carry producer (every 4e186 caller sets its own flags);
    // MOVE/MOVEA+MOVE/MOVEQ/TST/CMP/CMPI/ADDI/SUBI/SUB/ADD/NEG/ASR/ANDI/CLR blocks stay Unknown.
    case 0x4e18c:case 0x4e196:case 0x4e19c:case 0x4e1a2:case 0xe5872:case 0xe5878:case 0xe596c:case 0xe5986:case 0xe5a7a:
    case 0xe5af8:case 0xe5b2c:case 0xe5b48:case 0xe5ba6:case 0xe5bac:case 0xe5bae:
    // Objects U08a (F4) blocks: the 4483a JMP (computed PC), the 96 BRA.W table entries 4483e..449ba, JSR/BRA/RTS blocks and the
    // MOVEM/LEA/MOVEA+JSR/JMP blocks 49274/49284/49290 only. U08a has no carry consumer or known-carry producer. MOVE/MOVEQ/NOT/
    // ANDI/LSR/LSL/OR/ADDI/ADD/SUB/CMPA/CMP/CMPI/TST/SWAP/ROL/EXG/ORI blocks and 449be (MOVE.W #160,D7; RTS) stay Unknown.
    case 0x43ebe:case 0x447da:case 0x447e0:case 0x447e4:case 0x4483a:case 0x4483e:case 0x44842:case 0x44846:case 0x4484a:
    case 0x4484e:case 0x44852:case 0x44856:case 0x4485a:case 0x4485e:case 0x44862:case 0x44866:case 0x4486a:case 0x4486e:
    case 0x44872:case 0x44876:case 0x4487a:case 0x4487e:case 0x44882:case 0x44886:case 0x4488a:case 0x4488e:case 0x44892:
    case 0x44896:case 0x4489a:case 0x4489e:case 0x448a2:case 0x448a6:case 0x448aa:case 0x448ae:case 0x448b2:case 0x448b6:
    case 0x448ba:case 0x448be:case 0x448c2:case 0x448c6:case 0x448ca:case 0x448ce:case 0x448d2:case 0x448d6:case 0x448da:
    case 0x448de:case 0x448e2:case 0x448e6:case 0x448ea:case 0x448ee:case 0x448f2:case 0x448f6:case 0x448fa:case 0x448fe:
    case 0x44902:case 0x44906:case 0x4490a:case 0x4490e:case 0x44912:case 0x44916:case 0x4491a:case 0x4491e:case 0x44922:
    case 0x44926:case 0x4492a:case 0x4492e:case 0x44932:case 0x44936:case 0x4493a:case 0x4493e:case 0x44942:case 0x44946:
    case 0x4494a:case 0x4494e:case 0x44952:case 0x44956:case 0x4495a:case 0x4495e:case 0x44962:case 0x44966:case 0x4496a:
    case 0x4496e:case 0x44972:case 0x44976:case 0x4497a:case 0x4497e:case 0x44982:case 0x44986:case 0x4498a:case 0x4498e:
    case 0x44992:case 0x44996:case 0x4499a:case 0x4499e:case 0x449a2:case 0x449a6:case 0x449aa:case 0x449ae:case 0x449b2:
    case 0x449b6:case 0x449ba:case 0x449c4:case 0x449ca:case 0x449d0:case 0x449d6:case 0x449dc:case 0x449e6:case 0x449f0:
    case 0x449fa:case 0x44a04:case 0x44a0e:case 0x44a18:case 0x44a22:case 0x44a2c:case 0x44a32:case 0x44a3a:case 0x44a44:
    case 0x44a4c:case 0x44a58:case 0x44a64:case 0x44a70:case 0x44a7c:case 0x44a88:case 0x44a94:case 0x44aa0:case 0x44aac:
    case 0x44ab8:case 0x44ac4:case 0x44ad0:case 0x44adc:case 0x49274:case 0x49284:case 0x49290:
    // Objects U09 (F4) blocks: MOVEA/LEA/EXG/BSR/JSR/JMP/BRA/RTS, LEA+DBRA (470a0), MOVEA+BRA (4726a), the BSET.B #0 block 76740
    // (Z only) and the BCC consumer 76a08 (C returned by U05 1ab02: 1ab7a ANDI CCR Clear, U01 1aafc ORI CCR Set). U09 has no
    // known-carry producer (the ADDI.B/ADD.B/CMP/SUBQ carries and the SUBX X are consumed inside their blocks).
    // MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/ADDQ/SUB/SUBQ/SUBX/MULU/ANDI/ORI/OR/AND/EOR/LSR/SWAP/EXT/Scc blocks stay Unknown.
    case 0x469ae:case 0x469d0:case 0x469d2:case 0x46a16:case 0x46a56:case 0x46a74:case 0x46a82:case 0x46abe:case 0x46aca:
    case 0x46b28:case 0x46b2c:case 0x46b78:case 0x46b84:case 0x46baa:case 0x46bda:case 0x46bde:case 0x47078:case 0x470a0:
    case 0x470a8:case 0x470da:case 0x47130:case 0x47182:case 0x4718a:case 0x4726a:case 0x76740:case 0x76746:case 0x76768:
    case 0x7676e:case 0x76786:case 0x767b6:case 0x767bc:case 0x767c2:case 0x767ec:case 0x767f2:case 0x7684a:case 0x7684e:
    case 0x769fc:case 0x76a08:case 0x76a0c:case 0x76a12:
    // Objects U08b (F4) blocks: BSR/JSR/BRA/RTS, MOVEM (+BRA/RTS), BCLR/BTST (Z only) + Bcc, BTST/SNE/RTS and the BEQ 4beec only.
    // U08b has no carry consumer across blocks (463ee 464ce 46572 46428 46506 465aa 4be9a set and consume C inside the block) and no
    // known-carry producer. MOVE/MOVEQ/MOVEA+MOVE/CLR/TST/CMP/CMPI/ADD/ADDI/SUB/SUBI/SUBQ/SUBX/NEG/ASR/LSR/AND/ANDI/OR/ORI/SWAP/EXG blocks stay Unknown.
    case 0x46384:case 0x463b4:case 0x463b8:case 0x46498:case 0x464c6:case 0x464ca:case 0x4688a:case 0x468b6:case 0x468de:
    case 0x46992:case 0x4bb2a:case 0x4bb2c:case 0x4bb3c:case 0x4bc7a:case 0x4bc8a:case 0x4be34:case 0x4be4c:case 0x4be82:
    case 0x4bea0:case 0x4bee2:case 0x4beec:case 0x4bf0a:case 0x4bf10:case 0x4bf80:case 0x4bf8a:case 0x4bf98:case 0x4bf9e:
    // Objects U10 (F4) blocks: JSR/BRA/JMP/RTS/LEA(+BRA/JSR) only and the 15 lone BCC/BCS consumers of the C returned by 1ab02 (bac92
    // bae38 baee2 baf8e: 1ab7a ANDI CCR Clear, U01 1aafc ORI CCR Set), 49fc6 (baecc baf56 bb212 bb2c4 bb3a0 bb410 bb480), 288c
    // (bafda) and the boundaries 497b6/eb774/4c266 (bac6e bac78 badbe). U10 has no known-carry producer. MOVE/MOVEQ/MOVEA+TST/
    // MOVEA+CMPI/CLR/TST/CMP/CMPI/ADDI/SUBI/ANDI/ADD/SUB/SUBQ/NEG/EXT/LSL/ASR blocks, the MOVE.L #imm,(A6) blocks, the banked
    // animation blocks and the ADDA.W block d7842 stay Unknown.
    case 0xbac24:case 0xbac5c:case 0xbac62:case 0xbac6e:case 0xbac72:case 0xbac78:case 0xbac7c:case 0xbac80:case 0xbac86:
    case 0xbac92:case 0xbac96:case 0xbac9c:case 0xbacaa:case 0xbacb2:case 0xbacb6:case 0xbacbc:case 0xbad92:case 0xbada8:
    case 0xbadac:case 0xbadbe:case 0xbadc2:case 0xbae26:case 0xbae2c:case 0xbae38:case 0xbae3c:case 0xbae42:case 0xbae5c:
    case 0xbae64:case 0xbae68:case 0xbae6e:case 0xbae82:case 0xbaec0:case 0xbaec6:case 0xbaecc:case 0xbaed6:case 0xbaee2:
    case 0xbaee6:case 0xbaeec:case 0xbaefa:case 0xbaf02:case 0xbaf06:case 0xbaf0c:case 0xbaf4a:case 0xbaf50:case 0xbaf56:
    case 0xbaf82:case 0xbaf8e:case 0xbaf92:case 0xbaf98:case 0xbafc0:case 0xbafc8:case 0xbafcc:case 0xbafd2:case 0xbafd4:
    case 0xbafda:case 0xbafde:case 0xbafe4:case 0xbb00e:case 0xbb0e4:case 0xbb0ea:case 0xbb0f0:case 0xbb1d8:case 0xbb1fc:
    case 0xbb200:case 0xbb206:case 0xbb20c:case 0xbb212:case 0xbb246:case 0xbb280:case 0xbb2b2:case 0xbb2b8:case 0xbb2be:
    case 0xbb2c4:case 0xbb2ce:case 0xbb30e:case 0xbb31a:case 0xbb328:case 0xbb32c:case 0xbb332:case 0xbb338:case 0xbb33e:
    case 0xbb37e:case 0xbb38a:case 0xbb38e:case 0xbb394:case 0xbb39a:case 0xbb3a0:case 0xbb3cc:case 0xbb3fe:case 0xbb404:
    case 0xbb40a:case 0xbb410:case 0xbb41a:case 0xbb446:case 0xbb46a:case 0xbb46e:case 0xbb474:case 0xbb47a:case 0xbb480:
    case 0xbb4b4:case 0xbb4ee:case 0xbb520:case 0xbb526:case 0xbb52c:case 0xbb532:case 0xbb546:case 0xbb54c:case 0xbb556:
    case 0xdbdc6:case 0xdbdd4:case 0xdbde6:case 0xdbdf4:case 0xdbe06:case 0xdbe14:case 0xdbe16:case 0xdbe1e:
    // Objects U11 (F4) blocks: the 45176 JMP (computed PC), the 96 BRA.W table entries 4517a..452f6, JSR/LEA+JSR/MOVEA+JSR/JMP/
    // BRA/RTS blocks and the six consumers 497ba (C returned by 49370), 497c4/497d8 (49392), 497cc/497e0 (the 4941e boundary) and
    // be892 (1ab02). 49386/497e4 (ORI CCR Set) and 4938c/497ea (ANDI CCR Clear) set their known C inside the block. MOVE/MOVEQ/CLR/
    // TST/CMP/CMPI/CMPA/ADD/ADDI/ADDQ/SUB/SUBI/AND/ANDI/EOR/LSL/ASR/MOVEM+MOVE blocks, beaba (MOVE.L #imm,(A6)) and the ADDA.W
    // block 472a8 stay Unknown.
    case 0x45176:case 0x4517a:case 0x4517e:case 0x45182:case 0x45186:case 0x4518a:case 0x4518e:case 0x45192:case 0x45196:
    case 0x4519a:case 0x4519e:case 0x451a2:case 0x451a6:case 0x451aa:case 0x451ae:case 0x451b2:case 0x451b6:case 0x451ba:
    case 0x451be:case 0x451c2:case 0x451c6:case 0x451ca:case 0x451ce:case 0x451d2:case 0x451d6:case 0x451da:case 0x451de:
    case 0x451e2:case 0x451e6:case 0x451ea:case 0x451ee:case 0x451f2:case 0x451f6:case 0x451fa:case 0x451fe:case 0x45202:
    case 0x45206:case 0x4520a:case 0x4520e:case 0x45212:case 0x45216:case 0x4521a:case 0x4521e:case 0x45222:case 0x45226:
    case 0x4522a:case 0x4522e:case 0x45232:case 0x45236:case 0x4523a:case 0x4523e:case 0x45242:case 0x45246:case 0x4524a:
    case 0x4524e:case 0x45252:case 0x45256:case 0x4525a:case 0x4525e:case 0x45262:case 0x45266:case 0x4526a:case 0x4526e:
    case 0x45272:case 0x45276:case 0x4527a:case 0x4527e:case 0x45282:case 0x45286:case 0x4528a:case 0x4528e:case 0x45292:
    case 0x45296:case 0x4529a:case 0x4529e:case 0x452a2:case 0x452a6:case 0x452aa:case 0x452ae:case 0x452b2:case 0x452b6:
    case 0x452ba:case 0x452be:case 0x452c2:case 0x452c6:case 0x452ca:case 0x452ce:case 0x452d2:case 0x452d6:case 0x452da:
    case 0x452de:case 0x452e2:case 0x452e6:case 0x452ea:case 0x452ee:case 0x452f2:case 0x452f6:case 0x497b6:case 0x497ba:
    case 0x497c4:case 0x497c8:case 0x497cc:case 0x497d8:case 0x497dc:case 0x497e0:case 0x4be06:case 0xbe888:case 0xbe892:
    case 0xbe896:case 0xbe89c:case 0xbe8a2:case 0xbe988:case 0xbe98e:case 0xbeab4:case 0xbeac0:case 0xbeac6:case 0xbead0:
    case 0xbeb52:case 0xbeb78:
    // Objects U12 (F4) blocks: JSR/BSR/BRA/RTS/LEA/MOVEM, BTST/BSET/BCLR (Z only) + Bcc, the BCC consumers 4c0c6 (C returned by
    // 46d72: 46eda MOVE Clear, 46ee6 ORI CCR Set) and 70502 (the 4c2cc boundary), the SCS consumers 490a4 (keeps C) and 490b0 (ADD.B,
    // leaves C Unknown) of the 289e C, the RTS 1abea (C of the 1abda CMPI) and the BPL 70198 (N of 49a58 recomputed). 1abda 1abec
    // 46eda 46ee6 set their known C inside the block. MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/SUB/SUBI/ADDI/ANDI/AND/ORI/EOR/NEG/SWAP/
    // LSL/LSR/ASR/MULU/Scc+MOVE blocks, the SUBQ/ADDQ.W An blocks 46db6 46eba, the ADDA blocks 49140 49176 and the stack MOVE
    // blocks stay Unknown.
    case 0x1abea:case 0x46dac:case 0x46e08:case 0x46e66:case 0x46e6a:case 0x46e80:case 0x46ea8:case 0x46eea:case 0x490a4:
    case 0x490b0:case 0x492c6:case 0x492c8:case 0x4c0ac:case 0x4c0c6:case 0x4c0e8:case 0x70054:case 0x70106:case 0x7011a:
    case 0x70182:case 0x70192:case 0x70198:case 0x7019c:case 0x701ac:case 0x701c6:case 0x70226:case 0x7022c:case 0x70234:
    case 0x7023e:case 0x70246:case 0x7024c:case 0x70254:case 0x7026a:case 0x70270:case 0x70278:case 0x7027e:case 0x70286:
    case 0x7028c:case 0x70418:case 0x7041e:case 0x70476:case 0x70496:case 0x704f0:case 0x704f6:case 0x70502:case 0x70506:
    case 0x70512:case 0x70522:case 0x70548:
    // Objects U13 (F4) blocks: LEA+JSR/JSR/JMP/BRA/RTS blocks, the BTST+Bcc blocks 70a40 b81aa (Z only) and the four consumers b80ce
    // (C returned by 1ab02), b819c (4b54e), b83f2 (49fc6) and ea5f6 (the U12 boundary 1abda). U13 has no known-carry producer.
    // MOVE/MOVEQ/CLR/TST/CMPI/ADDI/ADD/SUBQ/BSET/BCLR+MOVE.L blocks, the MOVE.L #imm,(A6) blocks and the WORD push/pop blocks stay
    // Unknown.
    case 0x709a6:case 0x70a40:case 0xb80c4:case 0xb80ce:case 0xb80d2:case 0xb80d8:case 0xb8110:case 0xb8132:case 0xb8138:
    case 0xb816e:case 0xb8190:case 0xb8196:case 0xb819c:case 0xb81aa:case 0xb81ba:case 0xb83e6:case 0xb83ec:case 0xb83f2:
    case 0xb83fc:case 0xea5f0:case 0xea5f6:case 0xea624:case 0xf1a62:case 0xf1a74:
    // Objects U14 (F4) blocks: BSR/JSR/LEA+JSR/BRA/JMP/RTS blocks, the SUBA.W+RTS block 4926e, the BCLR/BSET (Z only) blocks
    // 16efc 16f06 and the MOVEA+BTST+Bcc blocks 51758 5176e. U14 has no carry consumer across blocks and no known-carry producer.
    // MOVE/MOVEQ/MOVEA+MOVE/CLR/TST/CMP/CMPI/ADD/ADDI/SUBQ/LSR/BSET/BCLR+MOVE blocks, the MOVE.L #imm,(A6) blocks and the BYTE/LONG
    // push/pop blocks stay Unknown.
    case 0x16efc:case 0x16f06:case 0x16f0c:case 0x49260:case 0x4926e:case 0x50cca:case 0x50cce:case 0x50d2c:case 0x50d44:
    case 0x50d58:case 0x50d94:case 0x50dac:case 0x514bc:case 0x51668:case 0x5169a:case 0x51720:case 0x51758:case 0x51766:
    case 0x5176e:case 0x5177a:case 0x51798:case 0x5179e:case 0x51fda:case 0x51ff2:case 0x5205c:case 0x614d4:
    // Objects U15a (F4) blocks: JSR/BSR/BRA/RTS/LEA, LEA+JSR, BSET+JSR, BSET (Z only), BTST+Bcc (Z only), ST/SF (Scc keeps the CCR)
    // and the seven consumers af150 af42a (C returned by the U16 boundary b0106), af452 af4c4 (b0206), af27a (287e), af2e6 (4b54e) and
    // b05ca (1ab02). 49542 4c260 (ANDI CCR Clear) and 49548 4c25a (ORI CCR Set) set their known C inside the block. MOVE/MOVEQ/MOVEA+
    // MOVE/CLR/TST/CMP/CMPI/ADD/ADDI/SUB/SUBI/SUBQ/SUBX/ANDI/ORI/LSL/SWAP/EXT/EXG/MOVEM blocks, the MOVE.L #imm,(A6) blocks and the stack
    // MOVE blocks stay Unknown.
    case 0x46640:case 0x46670:case 0x46674:case 0x4671a:case 0x46748:case 0x4674c:case 0x4950e:case 0x4951a:case 0x49534:
    case 0x4c1ee:case 0x4c244:case 0x4c29a:case 0xaf092:case 0xaf146:case 0xaf150:case 0xaf1e4:case 0xaf1ea:case 0xaf22a:
    case 0xaf274:case 0xaf27a:case 0xaf2b8:case 0xaf2dc:case 0xaf2e0:case 0xaf2e6:case 0xaf2ee:case 0xaf2fe:case 0xaf3de:
    case 0xaf3ea:case 0xaf3f0:case 0xaf3f8:case 0xaf3fe:case 0xaf402:case 0xaf408:case 0xaf41e:case 0xaf422:case 0xaf426:
    case 0xaf42a:case 0xaf452:case 0xaf466:case 0xaf46c:case 0xaf47a:case 0xaf488:case 0xaf48c:case 0xaf492:case 0xaf4c4:
    case 0xaf4e0:case 0xb0062:case 0xb05be:case 0xb05ca:case 0xb05dc:
    // Objects U16 (F4) blocks: JSR/MOVEA+JSR/LEA+JSR/JMP/RTS blocks and the two consumers b020c (C returned by the U15 boundary 4950e)
    // and bbe86 (C returned by U01 4b54e). b011a (ANDI.W Clear), b0144 (ORI CCR Set), b0210 (ORI CCR Set) and b021c (ANDI CCR Clear)
    // set their known C inside the block; the RTS blocks b014e/b0226 return it to the U15 consumers. MOVE/MOVEQ/SUB/ADDI/CLR/TST/LSR/
    // ASR/SUBI/NEG/ADDQ/SUBQ/BTST+MOVE blocks and the MOVE.L #imm,(A6) blocks stay Unknown.
    case 0xb0122:case 0xb014e:case 0xb0206:case 0xb020c:case 0xb0226:case 0xbbe12:case 0xbbe74:case 0xbbe7a:case 0xbbe80:
    case 0xbbe86:case 0xbbef2:case 0xbbefc:case 0xbbf02:case 0xf1a22:case 0xf1a34:
    // Objects U15b (F4) blocks: the 96 BRA.W table entries 4579c..45918 and the RTS blocks 4591c 45930 45b10. U15b has no carry
    // consumer across blocks and no known-carry producer. 45792 (MOVE.W+EXT.L+JMP 4579c(PC,D7.W)) and the MOVE/OR/MOVEQ/TST/CMPI/
    // LSL/ADD/SUB/NOT/ANDI/ASR/NEG blocks stay Unknown.
    case 0x4579c:case 0x457a0:case 0x457a4:case 0x457a8:case 0x457ac:case 0x457b0:case 0x457b4:case 0x457b8:case 0x457bc:
    case 0x457c0:case 0x457c4:case 0x457c8:case 0x457cc:case 0x457d0:case 0x457d4:case 0x457d8:case 0x457dc:case 0x457e0:
    case 0x457e4:case 0x457e8:case 0x457ec:case 0x457f0:case 0x457f4:case 0x457f8:case 0x457fc:case 0x45800:case 0x45804:
    case 0x45808:case 0x4580c:case 0x45810:case 0x45814:case 0x45818:case 0x4581c:case 0x45820:case 0x45824:case 0x45828:
    case 0x4582c:case 0x45830:case 0x45834:case 0x45838:case 0x4583c:case 0x45840:case 0x45844:case 0x45848:case 0x4584c:
    case 0x45850:case 0x45854:case 0x45858:case 0x4585c:case 0x45860:case 0x45864:case 0x45868:case 0x4586c:case 0x45870:
    case 0x45874:case 0x45878:case 0x4587c:case 0x45880:case 0x45884:case 0x45888:case 0x4588c:case 0x45890:case 0x45894:
    case 0x45898:case 0x4589c:case 0x458a0:case 0x458a4:case 0x458a8:case 0x458ac:case 0x458b0:case 0x458b4:case 0x458b8:
    case 0x458bc:case 0x458c0:case 0x458c4:case 0x458c8:case 0x458cc:case 0x458d0:case 0x458d4:case 0x458d8:case 0x458dc:
    case 0x458e0:case 0x458e4:case 0x458e8:case 0x458ec:case 0x458f0:case 0x458f4:case 0x458f8:case 0x458fc:case 0x45900:
    case 0x45904:case 0x45908:case 0x4590c:case 0x45910:case 0x45914:case 0x45918:case 0x4591c:case 0x45930:case 0x45b10:
    // Objects U15c (F4) blocks: the 45b28 JMP (computed PC) and the 96 BRA.W table entries 45b2c..45ca8. U15c has no carry consumer
    // across blocks and no known-carry producer. The CMPI/TST+Bcc entry blocks 45b12 45b1a 45b22 and the ORI.W+MOVE.W+RTS target
    // bodies stay Unknown.
    case 0x45b28:case 0x45b2c:case 0x45b30:case 0x45b34:case 0x45b38:case 0x45b3c:case 0x45b40:case 0x45b44:case 0x45b48:
    case 0x45b4c:case 0x45b50:case 0x45b54:case 0x45b58:case 0x45b5c:case 0x45b60:case 0x45b64:case 0x45b68:case 0x45b6c:
    case 0x45b70:case 0x45b74:case 0x45b78:case 0x45b7c:case 0x45b80:case 0x45b84:case 0x45b88:case 0x45b8c:case 0x45b90:
    case 0x45b94:case 0x45b98:case 0x45b9c:case 0x45ba0:case 0x45ba4:case 0x45ba8:case 0x45bac:case 0x45bb0:case 0x45bb4:
    case 0x45bb8:case 0x45bbc:case 0x45bc0:case 0x45bc4:case 0x45bc8:case 0x45bcc:case 0x45bd0:case 0x45bd4:case 0x45bd8:
    case 0x45bdc:case 0x45be0:case 0x45be4:case 0x45be8:case 0x45bec:case 0x45bf0:case 0x45bf4:case 0x45bf8:case 0x45bfc:
    case 0x45c00:case 0x45c04:case 0x45c08:case 0x45c0c:case 0x45c10:case 0x45c14:case 0x45c18:case 0x45c1c:case 0x45c20:
    case 0x45c24:case 0x45c28:case 0x45c2c:case 0x45c30:case 0x45c34:case 0x45c38:case 0x45c3c:case 0x45c40:case 0x45c44:
    case 0x45c48:case 0x45c4c:case 0x45c50:case 0x45c54:case 0x45c58:case 0x45c5c:case 0x45c60:case 0x45c64:case 0x45c68:
    case 0x45c6c:case 0x45c70:case 0x45c74:case 0x45c78:case 0x45c7c:case 0x45c80:case 0x45c84:case 0x45c88:case 0x45c8c:
    case 0x45c90:case 0x45c94:case 0x45c98:case 0x45c9c:case 0x45ca0:case 0x45ca4:case 0x45ca8:
    // Objects U17 (F4) blocks: JSR/BSR/BRA/JMP/RTS/LEA+JSR, BSET+JSR 482c0, BCLR (Z only) 1c5fa 1c610, BTST+BEQ (Z only) bbfe4,
    // MOVEM+MOVEA+RTS 4c060 and the six consumers 1c5f6 1c60c (C returned by 289e), bc054 c3e88 (49fc6) and c3f86 c3fb6 (288c). U17
    // has no known-carry producer. MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/SUB/SUBI/SUBQ/NEG/ASR/LSR/LSL/ANDI/OR/MULS/ST blocks, the
    // MOVE.L #imm,(A6) blocks and the banked animation blocks stay Unknown.
    case 0x1c5ea:case 0x1c5f6:case 0x1c5fa:case 0x1c600:case 0x1c60c:case 0x1c610:case 0x1c616:case 0x482c0:case 0x482de:
    case 0x482e2:case 0x482e8:case 0x4bfa4:case 0x4bfa8:case 0x4bfac:case 0x4bfb0:case 0x4c060:case 0xbbf7e:case 0xbbfe4:
    case 0xbc018:case 0xbc01e:case 0xbc04e:case 0xbc054:case 0xbc05e:case 0xbc076:case 0xbc084:case 0xbc08a:case 0xc3d60:
    case 0xc3d66:case 0xc3db8:case 0xc3df2:case 0xc3e30:case 0xc3e36:case 0xc3e70:case 0xc3e88:case 0xc3eb8:case 0xc3ebe:
    case 0xc3ec0:case 0xc3edc:case 0xc3f00:case 0xc3f06:case 0xc3f12:case 0xc3f74:case 0xc3f7a:case 0xc3f80:case 0xc3f86:
    case 0xc3f8a:case 0xc3f90:case 0xc3f9e:case 0xc3faa:case 0xc3fb0:case 0xc3fb6:case 0xc3fba:case 0xc3fcc:case 0xc3fd2:
    // Objects U18 (F4) blocks: JSR/BSR/JMP/BRA/RTS/LEA/MOVEA blocks, the BTST/BSET/BCLR (+Bcc/RTS) blocks and the 14 consumers
    // b67a4 (b7e5c), b76ae (49fc6), b76c4 (boundary b7b4c), b7736 (1aa7e), b7e20 (28ae), ea5e6 (1abda), ea650 (MOVEM.W+DBCS, 46c68),
    // ea65c (ea636), ea678 (46c68), ea770 (289e), ea792 (SCS+BCS, ea65a) and ea806/ea830/ea946 (288c). 46d08 (ANDI CCR Clear), 46d12
    // (ORI CCR Set), b7e64 (ANDI CCR Clear) and ea67a (ORI CCR Set) set their known C inside the block. The CCR blocks b7e2e b7e56
    // ea9ea, the MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/SUB/SUBI/SUBQ/ANDI/LSL/NEG/SWAP blocks, the ADDA/MOVEM.L stack blocks and the
    // MOVE.L #imm,(A6) blocks stay Unknown.
    case 0xb6326:case 0xb670c:case 0xb6764:case 0xb6768:case 0xb67a0:case 0xb67a4:case 0xb67ae:case 0xb76a4:case 0xb76a8:
    case 0xb76ae:case 0xb76b8:case 0xb76bc:case 0xb76c4:case 0xb76d2:case 0xb76dc:case 0xb76e0:case 0xb7708:case 0xb772c:
    case 0xb7736:case 0xb7740:case 0xb7bcc:case 0xb7bf4:case 0xb7c0a:case 0xb7c10:case 0xb7c18:case 0xb7c1e:case 0xb7c3c:
    case 0xb7c40:case 0xb7c42:case 0xb7c48:case 0xb7c6a:case 0xb7cfa:case 0xb7d04:case 0xb7d0a:case 0xb7d0e:case 0xb7d14:
    case 0xb7d1a:case 0xb7d2c:case 0xb7e06:case 0xb7e20:case 0xb7e6e:case 0xea5e0:case 0xea5e6:case 0xea650:case 0xea658:
    case 0xea65a:case 0xea65c:case 0xea660:case 0xea678:case 0xea770:case 0xea792:case 0xea7aa:case 0xea7f2:case 0xea806:
    case 0xea82a:case 0xea830:case 0xea83a:case 0xea852:case 0xea908:case 0xea90e:case 0xea940:case 0xea946:case 0xea94a:
    case 0xea99e:case 0xea9a4:case 0xea9ca:case 0xea9f8:case 0xea9fe:case 0xeaa54:
    // Objects U19 (F4) blocks: JSR/BSR/BRA/JMP/RTS/LEA+JSR, MOVEA.L A2,A0 (b7b96), BTST+Bcc (Z only) and the ten consumers b6414
    // (C returned by the U18 boundary b7e5c), b64b2 d83b4 (49fc6), b7b52 (484e2), b7b64 b7b78 (49392), b7b6a b7b7e (the b7b30 boundary),
    // ba7f4 (1ab02) and d8312 (1aa7e). 484ec/b7bb6 (ORI CCR Set) and 484f2/b7bbc (ANDI CCR Clear) set their known C inside the block
    // before RTS. MOVE/MOVEQ/CLR/TST/CMP/CMPI/SUBI/SUBQ/NEG blocks, the MOVE.L #imm,(A6) blocks and the banked animation blocks stay Unknown.
    case 0x484e2:case 0xb630a:case 0xb6342:case 0xb636c:case 0xb63b4:case 0xb6406:case 0xb640a:case 0xb6410:case 0xb6414:case 0xb641e:
    case 0xb6466:case 0xb64a8:case 0xb64ac:case 0xb64b2:case 0xb6502:case 0xb68ba:case 0xb68fa:case 0xb6900:case 0xb694e:case 0xb69b6:
    case 0xb69ba:case 0xb69ce:case 0xb69f4:case 0xb6a12:case 0xb6a20:case 0xb6a26:case 0xb6a76:case 0xb6ac8:case 0xb6ace:case 0xb6ad4:
    case 0xb6ae4:case 0xb6aea:case 0xb6b3a:case 0xb6b7c:case 0xb6b80:case 0xb6b86:case 0xb7b4c:case 0xb7b52:case 0xb7b64:case 0xb7b68:
    case 0xb7b6a:case 0xb7b78:case 0xb7b7c:case 0xb7b7e:case 0xb7b96:case 0xb7c9e:case 0xb7ca4:case 0xb7cc6:case 0xba7d8:case 0xba7de:
    case 0xba7e4:case 0xba7ea:case 0xba7f4:case 0xba7f8:case 0xba7fe:case 0xd8272:case 0xd829e:case 0xd82aa:case 0xd82b4:case 0xd82ba:
    case 0xd82be:case 0xd82c4:case 0xd82ca:case 0xd8302:case 0xd8308:case 0xd8312:case 0xd8316:case 0xd831c:case 0xd831e:case 0xd8354:
    case 0xd8380:case 0xd8388:case 0xd8394:case 0xd839e:case 0xd83a4:case 0xd83a8:case 0xd83ae:case 0xd83b4:case 0xd83b8:case 0xd83be:
    case 0xdbf08:case 0xdbf18:case 0xdbf32:case 0xdbf44:
    // Objects U20a (F4) blocks: the 44ade JMP (computed PC), the 96 BRA.W table entries 44ae2..44c5e, BCHG+RTS 492d0 (Z only) and the
    // RTS 497b4. 497a6 (TST.B: Clear) and 497b0 (ORI CCR: Set) set their known C inside the block. The MOVE/MOVEQ/NOT/AND/ANDI/ADD/SUB/
    // SUBI/ASR/LSL/TST/CMPI height leaves 44c62..45174 stay Unknown (no consumer: both 44ade callers continue with SUBI.L).
    case 0x44ade:case 0x44ae2:case 0x44ae6:case 0x44aea:case 0x44aee:case 0x44af2:case 0x44af6:case 0x44afa:case 0x44afe:
    case 0x44b02:case 0x44b06:case 0x44b0a:case 0x44b0e:case 0x44b12:case 0x44b16:case 0x44b1a:case 0x44b1e:case 0x44b22:
    case 0x44b26:case 0x44b2a:case 0x44b2e:case 0x44b32:case 0x44b36:case 0x44b3a:case 0x44b3e:case 0x44b42:case 0x44b46:
    case 0x44b4a:case 0x44b4e:case 0x44b52:case 0x44b56:case 0x44b5a:case 0x44b5e:case 0x44b62:case 0x44b66:case 0x44b6a:
    case 0x44b6e:case 0x44b72:case 0x44b76:case 0x44b7a:case 0x44b7e:case 0x44b82:case 0x44b86:case 0x44b8a:case 0x44b8e:
    case 0x44b92:case 0x44b96:case 0x44b9a:case 0x44b9e:case 0x44ba2:case 0x44ba6:case 0x44baa:case 0x44bae:case 0x44bb2:
    case 0x44bb6:case 0x44bba:case 0x44bbe:case 0x44bc2:case 0x44bc6:case 0x44bca:case 0x44bce:case 0x44bd2:case 0x44bd6:
    case 0x44bda:case 0x44bde:case 0x44be2:case 0x44be6:case 0x44bea:case 0x44bee:case 0x44bf2:case 0x44bf6:case 0x44bfa:
    case 0x44bfe:case 0x44c02:case 0x44c06:case 0x44c0a:case 0x44c0e:case 0x44c12:case 0x44c16:case 0x44c1a:case 0x44c1e:
    case 0x44c22:case 0x44c26:case 0x44c2a:case 0x44c2e:case 0x44c32:case 0x44c36:case 0x44c3a:case 0x44c3e:case 0x44c42:
    case 0x44c46:case 0x44c4a:case 0x44c4e:case 0x44c52:case 0x44c56:case 0x44c5a:case 0x44c5e:case 0x492d0:case 0x497b4:
    // Objects U20b (F4) blocks: LEA+JSR, JSR, BRA, RTS and BTST+BNE blocks and the 3 consumers 849fe (C returned by
    // 1ab02), 8592c (497a6) and 85bec (49fc6). U20b has no known-carry producer. The MOVE/MOVE.L #imm,(A6)/CLR/BSET+CLR/TST/CMP/CMPI/
    // ADD/ADDI/SUBI/SUBQ/NEG blocks and the banked animation blocks stay Unknown.
    case 0x849f4:case 0x849fe:case 0x84a12:case 0x85926:case 0x8592c:case 0x85978:case 0x85980:case 0x859ec:case 0x85a56:
    case 0x85a86:case 0x85a8c:case 0x85aa0:case 0x85b16:case 0x85b2e:case 0x85b34:case 0x85b3a:case 0x85b6c:case 0x85b76:
    case 0x85b7c:case 0x85b80:case 0x85b86:case 0x85b9a:case 0x85bcc:case 0x85bd6:case 0x85bdc:case 0x85be0:case 0x85be6:
    case 0x85bec:case 0x85bf0:case 0x85c00:case 0x85c48:case 0x85c52:case 0x85c58:case 0x85c5c:case 0x85c62:case 0x85c68:
    // Objects N01 (F4) blocks: JSR/JMP/BRA/RTS blocks, MOVEA+ST+JMP e5f22 e5fae (Scc keeps the CCR) and the two consumers e5c12 e5e06
    // (C returned by 49fc6). N01 has no known-carry producer. MOVE/MOVEQ/MOVEA+TST/CLR/CMP/CMPI/ADD/ADDI/ADDQ/SUBQ/LSL blocks, the
    // MOVE.L #imm,(A6) blocks and the banked animation blocks stay Unknown.
    case 0x52136:case 0x5213c:case 0xe5c06:case 0xe5c0c:case 0xe5c12:case 0xe5c72:case 0xe5cdc:case 0xe5ce2:case 0xe5d70:
    case 0xe5dfa:case 0xe5e00:case 0xe5e06:case 0xe5e7e:case 0xe5eb2:case 0xe5f18:case 0xe5f22:case 0xe5f30:case 0xe5f5c:
    case 0xe5f74:case 0xe5f90:case 0xe5f96:case 0xe5f9e:case 0xe5fae:case 0xe5fbc:
    // Objects N03 (F4) blocks: RTS, JSR, BRA, JMP, LEA+JSR, MOVEA+JSR, MOVEA, BTST+BEQ and BCHG blocks, the pass-through c637c
    // (BCC.W to the next instruction) and the consumer c63aa (C returned by 1ab02). N03 has no known-carry producer; the MOVE/MOVEQ/
    // CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/ADDQ/SUBQ/ANDI/LSL blocks, MOVE.L #imm,(A6), MOVEM+MOVE.B and ADDQ.L #4,A1 stay Unknown.
    case 0x4b878:case 0xc603a:case 0xc6150:case 0xc61f4:case 0xc61fa:case 0xc6230:case 0xc6238:case 0xc6246:case 0xc624e:
    case 0xc6252:case 0xc6268:case 0xc6278:case 0xc6296:case 0xc629a:case 0xc629e:case 0xc62b2:case 0xc62be:case 0xc62ca:
    case 0xc62e2:case 0xc6308:case 0xc6336:case 0xc634e:case 0xc6354:case 0xc637c:case 0xc6380:case 0xc6398:case 0xc63a0:
    case 0xc63aa:case 0xc63ae:case 0xc63b4:case 0xc6428:case 0xc642c:case 0xc647e:
    // Objects N04 (F4) blocks: JSR/BSR/BRA/JMP/RTS/LEA+JSR/MOVEA+JSR blocks, the BTST/BSET/BCLR/BCHG (Z only, +Bcc/BRA) blocks, MOVEA+ST+JMP
    // 72e50 (Scc keeps the CCR) and the ten consumers 72be2 72d04 (C returned by 49fc6),
    // 72bfc 72c08 (boundary 49c38), 72c18 72c30 (289e), 72c46 (boundary 494c0), 72e4c aaa02 (1ab02) and ab06c (288c). 4a48a (ORI CCR
    // Set) and 4a490 (ANDI CCR Clear) set their known C inside the block before RTS. MOVE/MOVEQ/MOVEA+TST/CLR/CMP/CMPI/ADD/ADDI/ADDQ/SUB/
    // SUBI/SUBQ/NEG/ASR/LSR/LSL/ANDI/SWAP blocks, the CMPI+BLT blocks ab19a ab1a2 (BLT ab1a6 folded), the MOVE.L #imm,(A6) blocks and the
    // banked animation blocks stay Unknown.
    case 0x4bc3e:case 0x6fec8:case 0x6ffae:case 0x6fff0:case 0x70052:case 0x71cc8:case 0x71d2e:case 0x71d34:case 0x71d44:
    case 0x72a5e:case 0x72a8a:case 0x72ac6:case 0x72af2:case 0x72b2e:case 0x72b5a:case 0x72b96:case 0x72bc2:case 0x72bcc:
    case 0x72bd6:case 0x72bdc:case 0x72be2:case 0x72bfc:case 0x72c08:case 0x72c0c:case 0x72c18:case 0x72c24:case 0x72c30:
    case 0x72c3c:case 0x72c46:case 0x72c6e:case 0x72ca2:case 0x72cce:case 0x72cd8:case 0x72ce4:case 0x72cee:case 0x72cf4:
    case 0x72cf8:case 0x72cfe:case 0x72d04:case 0x72d3e:case 0x72d42:case 0x72d54:case 0x72dd2:case 0x72dd8:case 0x72e3a:
    case 0x72e3e:case 0x72e42:case 0x72e4c:case 0x72e50:case 0x72e70:case 0x72e7a:case 0x72e8a:case 0xaa986:case 0xaa9bc:
    case 0xaa9ec:case 0xaa9f2:case 0xaa9f8:case 0xaaa02:case 0xaaa16:case 0xab02a:case 0xab066:case 0xab06c:case 0xab070:
    case 0xab076:case 0xab1ba:case 0xab1c0:case 0xab1c6:case 0xab222:case 0xeb752:case 0xeb75a:case 0xeb766:
    case 0xeb772:
    // Objects N05 (F4) blocks: JSR, BRA, JMP, RTS, LEA+JSR, LEA+BRA, MOVEA+JSR, SUBA+RTS (4925a) and BCHG blocks, the BPL bddb4 (N of
    // its only predecessor bdd8a recomputed from D2) and the 7 consumers bdd7e bde44 bdeb8 (C returned by 1ab02), bdf64 (288c), c5ff2
    // (28ae), d23be (49fc6) and d23cc (1ab80). The producer 1abd4 (ANDI.B #fe,CCR; RTS) sets its known Clear inside the block; the
    // MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/SUB/SUBQ/NEG/ASR/LSL/EXT/SWAP/ANDI blocks and MOVE.L #imm,(A6) stay Unknown.
    case 0x4925a:case 0xbdd3e:case 0xbdd44:case 0xbdd72:case 0xbdd7e:case 0xbdd82:case 0xbdd88:case 0xbddb0:case 0xbddb4:
    case 0xbddf2:case 0xbde2c:case 0xbde32:case 0xbde38:case 0xbde44:case 0xbde48:case 0xbde4e:case 0xbdea0:case 0xbdea6:
    case 0xbdeac:case 0xbdeb8:case 0xbdebc:case 0xbdec2:case 0xbded8:case 0xbdef0:case 0xbdf40:case 0xbdf58:case 0xbdf5e:
    case 0xbdf64:case 0xbdf68:case 0xbdf7a:case 0xbdf80:case 0xc5e76:case 0xc5ff2:case 0xc600c:case 0xd1d00:case 0xd1d30:
    case 0xd1d60:case 0xd1dc0:case 0xd1df0:case 0xd1e6a:case 0xd239c:case 0xd23b2:case 0xd23b8:case 0xd23be:case 0xd23c2:
    case 0xd23cc:case 0xd23d0:case 0xd23d2:case 0xd3c2a:case 0xd3c38:case 0xd3c3e:case 0xdcee0:case 0xdcee6:case 0xdceec:
    case 0xdcf02:case 0xdcf04:case 0xdcf0a:case 0xdcf10:case 0xdcf2a:case 0xdcf3c:
    // Objects N06 (F4) blocks: JSR/BRA/JMP/RTS/MOVEA+JSR blocks, LEA+BRA and ST.B(+BRA) blocks (Scc keeps the CCR), BSET ba31e (Z only)
    // and the twelve consumers b9e46 (C returned by 1aa7e), ba1ec (288c), ba23a (eb774), ba282 (boundary 497f0), ba29c (497b6), ba334
    // ba396 (28ae), eb77a (49370), eb786 eb79c (49392) and eb790 eb7a6 (boundary 49416). eb7aa (ORI CCR Set) and eb7b0 (ANDI CCR Clear)
    // set their known C inside the block before RTS. MOVE/MOVEQ/MOVEA+TST/CLR/CMP/CMPI/CMPA/SUBQ/ADD/ANDI/NEG blocks, the MOVE.L #imm,(A6)
    // blocks, the MOVE+JSR blocks and the banked animation blocks stay Unknown.
    case 0xb9dd4:case 0xb9df0:case 0xb9df6:case 0xb9e08:case 0xb9e16:case 0xb9e1c:case 0xb9e2e:case 0xb9e3a:case 0xb9e46:
    case 0xb9e4a:case 0xb9e50:case 0xb9e5c:case 0xb9e62:case 0xb9e70:case 0xb9eb0:case 0xb9f04:case 0xb9f2e:case 0xb9f70:
    case 0xb9f74:case 0xb9f7a:case 0xb9f92:case 0xba196:case 0xba19a:case 0xba1a0:case 0xba1b4:case 0xba1c4:case 0xba1ca:
    case 0xba1e6:case 0xba1ec:case 0xba1f0:case 0xba1f6:case 0xba212:case 0xba234:case 0xba23a:case 0xba250:case 0xba258:
    case 0xba25c:case 0xba268:case 0xba270:case 0xba27c:case 0xba282:case 0xba286:case 0xba28e:case 0xba292:case 0xba296:
    case 0xba29c:case 0xba2a0:case 0xba2a8:case 0xba2ac:case 0xba2b0:case 0xba2b4:case 0xba31e:case 0xba334:case 0xba384:
    case 0xba396:case 0xba3a8:case 0xd9bd8:case 0xd9bf2:case 0xd9c04:case 0xeb774:case 0xeb77a:case 0xeb786:case 0xeb78a:
    case 0xeb790:case 0xeb79c:case 0xeb7a0:case 0xeb7a6:
    // Objects N07 (F4) blocks: JSR, BRA, JMP, RTS, LEA+JSR, MOVEA+JSR, BSET (Z only) 9bb62 and BTST+BEQ (Z only) bbd60 blocks and the 4
    // consumers 9ad28 (C returned by 1ab02), 9c03a 9c06c (28ae) and bbd58 (4b54e). 9c04c and 9c07a (ORI CCR after the boundary 4970a)
    // set their known Set inside the block. The MOVE/MOVEQ/CLR/TST/CMP/CMPI/ADD/ADDI/SUB/SUBI/SUBQ/ADDQ/NEG/ASR/LSL/EXT/ANDI blocks,
    // MOVE.L #imm,(A6) and the banked animation blocks stay Unknown.
    case 0x9ad1e:case 0x9ad28:case 0x9ad2c:case 0x9ad32:case 0x9bb62:case 0x9bb72:case 0x9bb88:case 0x9bbbe:case 0x9bc2a:
    case 0x9bc3e:case 0x9bc44:case 0x9bc4a:case 0x9bc6c:case 0x9bc70:case 0x9bf38:case 0x9bf3e:case 0x9bf68:case 0x9bfa2:
    case 0x9bfd4:case 0x9bfda:case 0x9c03a:case 0x9c06c:case 0x9c0b2:case 0xbbc0c:case 0xbbc60:case 0xbbca6:case 0xbbcec:
    case 0xbbd32:case 0xbbd3c:case 0xbbd42:case 0xbbd52:case 0xbbd58:case 0xbbd60:case 0xbbd74:case 0xbbd86:case 0xbbd90:
    case 0xbbda8:case 0xbbdb6:case 0xbbdbe:
    // Objects N08 (F4) blocks: JSR 4945e, BTST+BEQ (Z only) 49842 4b4da, RTS 49876 (returns the C of 4984e / 49862) and LEA 4b4e6.
    // N08 has no carry consumer. 494a6 494ac (ANDI CCR Clear) and 494b4 (ORI CCR Set) set their known C before RTS; 4984e (CMP.W+BCC:
    // taken Clear, fall-through Set) and 49862 (CMP.W unsigned borrow) set the known C that 49876 returns. MOVE/MOVEQ/MOVEA/TST/CLR/
    // CMP/CMPI/ADD/SUB/SUBI/NEG/ASR/LSR/LSL/AND/OR/SWAP blocks, the DBRA blocks, the MOVEQ+BSR 4ad6c candidate blocks, MOVE.L+JSR 4b4ea
    // and the result MOVE+RTS 4b4fa stay Unknown.
    case 0x4945e:case 0x49842:case 0x49876:case 0x4b4da:case 0x4b4e6:
    // Objects N09 (F4) blocks: JSR/BSR/BRA/JMP/RTS/LEA/MOVEA/MOVEM blocks, the BTST/BSET/BCLR/BCHG (Z only, +Bcc) blocks including the
    // folded af7a0 (BTST+BRA+BNE), SF/ST (Scc keeps the CCR) and the 19 consumers af5b0 (SCC, C returned by b0468), af64a (b0206),
    // af6a4 af938 afc92 (49fc6), af738 (b02ec), af74e (b041c), af764 (b0352), af7f4 (boundary 4941e), af970 (4b54e), afc78 (4c1de),
    // b01ea (boundary 4945e), b0238 (boundary 493bc), b02b0 (b0150), b036c (boundary 4983e), b03f0 (b0406), b044a (b0228), b058a
    // (1ab02) and b05aa (1ab80). Known C inside the block: Clear b01c8 b01fa b0320 b042e (ANDI CCR), b0358 b03d8 b041c b0468 b047e
    // (ANDI/MOVE/TST/CMPI #0), Set b01d6 b01ee b031a b04b6 (ORI CCR), computed b0406 b0412 b0434 b0462 (CMP borrow). The other
    // MOVE/MOVEQ/TST/CMP/CMPI/ADD/ADDI/SUB/SUBI/SUBQ/AND/ANDI/OR/EOR/NEG/ASR/ASL/LSR/LSL/EXT/SWAP/CLR/DIVU blocks, the MOVE.L #imm,(A6)
    // blocks and the animation blocks stay Unknown.
    case 0xaf552:case 0xaf59e:case 0xaf5ac:case 0xaf5b0:case 0xaf5b4:case 0xaf5be:case 0xaf60e:case 0xaf62c:case 0xaf64a:
    case 0xaf672:case 0xaf676:case 0xaf698:case 0xaf69e:case 0xaf6a4:case 0xaf6c2:case 0xaf6da:case 0xaf6de:case 0xaf6ec:
    case 0xaf70c:case 0xaf734:case 0xaf738:case 0xaf74a:case 0xaf74e:case 0xaf760:case 0xaf764:case 0xaf76e:case 0xaf7a0:
    case 0xaf7aa:case 0xaf7ba:case 0xaf7c6:case 0xaf7e6:case 0xaf7f4:case 0xaf806:case 0xaf92c:case 0xaf932:case 0xaf938:
    case 0xaf952:case 0xaf966:case 0xaf96a:case 0xaf970:case 0xaf974:case 0xaf98c:case 0xafc16:case 0xafc28:case 0xafc2e:
    case 0xafc3a:case 0xafc78:case 0xafc7c:case 0xafc82:case 0xafc86:case 0xafc8c:case 0xafc92:case 0xafc96:case 0xafcb0:
    case 0xafcba:case 0xb005e:case 0xb017a:case 0xb01aa:case 0xb01e2:case 0xb01e4:case 0xb01ea:case 0xb0204:case 0xb0230:
    case 0xb0238:case 0xb023c:case 0xb023e:case 0xb0268:case 0xb0292:case 0xb029c:case 0xb02b0:case 0xb02b4:case 0xb02b8:
    case 0xb0326:case 0xb0352:case 0xb0360:case 0xb036c:case 0xb0370:case 0xb0372:case 0xb03e6:case 0xb03f0:case 0xb03f4:
    case 0xb03f6:case 0xb03fe:case 0xb0400:case 0xb041a:case 0xb0424:case 0xb0444:case 0xb0446:case 0xb044a:case 0xb044e:
    case 0xb0470:case 0xb0472:case 0xb0486:case 0xb04ca:case 0xb057e:case 0xb058a:case 0xb059c:case 0xb059e:case 0xb05aa:
    case 0xb05bc:
    // Objects N10 (F4) blocks: JSR/BRA/JMP/RTS/LEA+JSR, BSET c58d4 and BTST+BNE c58f8 (Z only) and the consumer c5932 (C returned by
    // 1ab02). N10 has no known-carry producer; the MOVE/TST/CMPI/ADD blocks and MOVE.L #imm,(A6) stay Unknown.
    case 0xc58d4:case 0xc58e2:case 0xc58f8:case 0xc5902:case 0xc5908:case 0xc590c:case 0xc5912:case 0xc5916:case 0xc5928:
    case 0xc5932:case 0xc5936:case 0xc593c:
    // Objects N11 (F4) blocks: JSR, LEA+JSR, MOVEA+JSR, JMP 2a00, BRA, RTS, BCHG (Z only) aefc8 and the 7 consumers aee9e (C returned
    // by 28ae), aef28 aef8e af060 (1ab02), af03c (49fc6), eb3a0 (eb5e6) and eb3cc (49370). eb60a (ORI CCR Set) and eb610 (ANDI CCR
    // Clear) set their known C before RTS. The MOVE/MOVEQ/MOVEA+MOVE/TST/CMPI/CMP/ADDQ/SUBQ/SUBI/NEG/EXT/LSL/MULS/ASR/ADD/CLR blocks,
    // the MOVE.L #imm,(A6) blocks, the banked animation blocks aefd6 af002 and the table blocks stay Unknown.
    case 0xaee9e:case 0xaeea2:case 0xaef18:case 0xaef1e:case 0xaef28:case 0xaef2c:case 0xaef32:case 0xaef3a:case 0xaef76:
    case 0xaef7c:case 0xaef84:case 0xaef8e:case 0xaef92:case 0xaef98:case 0xaefc8:case 0xaeffe:case 0xaf030:case 0xaf036:
    case 0xaf03c:case 0xaf040:case 0xaf04e:case 0xaf056:case 0xaf060:case 0xaf064:case 0xaf06a:case 0xdbf94:case 0xeb266:
    case 0xeb2ba:case 0xeb2be:case 0xeb2c4:case 0xeb2d0:case 0xeb2ee:case 0xeb2fc:case 0xeb376:case 0xeb37a:case 0xeb380:
    case 0xeb38c:case 0xeb398:case 0xeb3a0:case 0xeb3c6:case 0xeb3cc:case 0xeb3e0:case 0xeb5a8:
    // Objects N12 (F4) blocks: JSR/BSR/BRA/JMP/RTS, LEA+JSR 52ea2, BTST/BSET/BCLR (Z only)+Bcc and ST blocks and the 12 consumers 53130
    // (C returned by 5317c), 53184 5318e (SCS, C returned by 49392; their MOVEQ/OR.B leave an Unknown C), 53232 5328a 53abe 53c2c 53cfe
    // 53e0e 53e50 (49fc6) and 53aee 53b3c (28ae). 53196 (ORI CCR Set) and 5319c (ANDI CCR Clear) set their known C before RTS. The
    // MOVE/MOVEQ/MOVEA+MOVE/CLR/TST/CMP/CMPI/ADD/ADDQ/SUB/SUBQ/NEG/ASR/ANDI/SWAP/OR blocks, MOVE.L #imm,(A6), the 28ae child and
    // animation blocks and ADDQ.W #4,A7+RTS 53b4c stay Unknown.
    case 0x52e62:case 0x52e9a:case 0x52e9c:case 0x52ea2:case 0x52ebe:case 0x52ec4:case 0x52f4a:case 0x52f66:case 0x52f7c:
    case 0x52f88:case 0x52f8e:case 0x52f94:case 0x52f96:case 0x52fa8:case 0x52fb2:case 0x52fb6:case 0x52fc0:case 0x52fd8:
    case 0x52fe2:case 0x53050:case 0x53122:case 0x5312c:case 0x53130:case 0x5316c:case 0x53172:case 0x53178:case 0x53184:
    case 0x5318e:case 0x531c2:case 0x531dc:case 0x531e2:case 0x53208:case 0x53222:case 0x5322c:case 0x53232:case 0x53260:
    case 0x5327a:case 0x53284:case 0x5328a:case 0x539e4:case 0x539ea:case 0x539f0:case 0x539f6:case 0x53a8a:case 0x53ab2:
    case 0x53ab8:case 0x53abe:case 0x53ac8:case 0x53ace:case 0x53aee:case 0x53b3c:case 0x53bf2:case 0x53c06:case 0x53c20:
    case 0x53c26:case 0x53c2c:case 0x53c3a:case 0x53c40:case 0x53cc4:case 0x53cd8:case 0x53cf2:case 0x53cf8:case 0x53cfe:
    case 0x53d0c:case 0x53d12:case 0x53dac:case 0x53db2:case 0x53db8:case 0x53dd4:case 0x53de8:case 0x53e02:case 0x53e08:
    case 0x53e0e:case 0x53e2c:case 0x53e44:case 0x53e4a:case 0x53e50:case 0x53e6e:
    // Objects N13 (F4) blocks: JSR, BSR, LEA+JSR, BRA, JMP 2a00, RTS, ST/SPL (Scc keeps the CCR; 5a802 5b326 5b3ae), BTST/BSET/BCLR
    // (Z only, +Bcc) blocks and the 6 consumers 5a8be (C returned by 5ab5a / 49fc6), 5aa2c (4b54e), 5b2b4 d3608 (288c), 5b3d0 (28ae)
    // and 5b48c (4a46c). N13 has no known-carry producer. The MOVE/MOVEQ/TST/CMP/CMPI/CLR/NOT/NEG/ADD/ADDI/ADDQ/SUB/SUBQ/ANDI/EOR/ASR/
    // LSR/LSL/EXT/SWAP/ADDX/DIVU blocks, the MOVE.L #imm,(A6) blocks and the banked animation blocks 5aa3a 5b220 stay Unknown.
    case 0x59ebe:case 0x59ed6:case 0x59ee0:case 0x59f12:case 0x59f16:case 0x5a7c8:case 0x5a7d2:case 0x5a7fa:case 0x5a7fe:
    case 0x5a802:case 0x5a828:case 0x5a82e:case 0x5a854:case 0x5a880:case 0x5a8ba:case 0x5a8be:case 0x5a8d8:case 0x5a8dc:
    case 0x5a8e8:case 0x5a99c:case 0x5a9a2:case 0x5a9ae:case 0x5a9b4:case 0x5a9b8:case 0x5a9f0:case 0x5aa04:case 0x5aa0e:
    case 0x5aa26:case 0x5aa2c:case 0x5ab22:case 0x5ab58:case 0x5ab64:case 0x5ab6a:case 0x5b2ae:case 0x5b2b4:case 0x5b2b8:
    case 0x5b2c2:case 0x5b326:case 0x5b3ae:case 0x5b3d0:case 0x5b48c:case 0x5b4be:case 0x5b4c0:case 0xd35c2:case 0xd35ce:
    case 0xd35f2:case 0xd3602:case 0xd3608:case 0xd3612:case 0xd3b1a:case 0xd3b3a:case 0xd3b44:case 0xd3b58:case 0xd3b62:
    // Objects N14 (F4) blocks: JSR/JMP/BRA/RTS, LEA+JSR a5d02 a6e02 be126, BTST/BSET (Z only)+Bcc and ST blocks and the 15 consumers
    // a5d0c be130 (C returned by 1ab02), a5d56 a5d8a a5dd6 a5e46 a5f9c (28ae), a5da0 a5dec a5fae (28ae Clear branch or ORI CCR Set),
    // a5ea4 a5ee6 (497a6), a60ce a6a12 (4b54e) and a6e84 (288c). a5d64 a5d9c a5de8 a5e54 a5faa (ORI CCR) set a known C. The
    // MOVE/MOVEQ/CLR/TST/CMP/CMPI/ADD/ADDI/SUBI/SUBQ/NEG/EXT/LSL/ASR/ORI blocks, MOVE.L #imm,(A6), the 28ae child and animation blocks
    // and 4b702 (ORI.B #80,60(A6); RTS) stay Unknown.
    case 0x4970a:case 0x4970e:case 0x4971a:case 0x49726:case 0x4972a:case 0x49746:case 0x4974c:case 0x49756:case 0x4975c:case 0x49766:
    case 0x4976c:case 0xa5d02:case 0xa5d0c:case 0xa5d10:case 0xa5d16:case 0xa5d56:case 0xa5d8a:case 0xa5da0:case 0xa5dc2:case 0xa5dd6:
    case 0xa5dec:case 0xa5e20:case 0xa5e26:case 0xa5e2c:case 0xa5e46:case 0xa5e58:case 0xa5e5e:case 0xa5e9e:case 0xa5ea4:case 0xa5eb6:
    case 0xa5ee0:case 0xa5ee6:case 0xa5ef8:case 0xa5f86:case 0xa5f9c:case 0xa5fae:case 0xa5fb2:case 0xa5fd8:case 0xa602e:case 0xa6062:
    case 0xa60c8:case 0xa60ce:case 0xa60d6:case 0xa60fc:case 0xa610e:case 0xa6114:case 0xa616e:case 0xa6944:case 0xa6978:case 0xa6a0c:
    case 0xa6a12:case 0xa6a1a:case 0xa6a50:case 0xa6a52:case 0xa6a5e:case 0xa6a8c:case 0xa6a9c:case 0xa6ac2:case 0xa6e02:case 0xa6e7e:
    case 0xa6e84:case 0xa6e88:case 0xa6e9a:case 0xa6ea0:case 0xa6ed0:case 0xa6ed6:case 0xa6ee2:case 0xa6ee8:case 0xa7256:case 0xbe110:
    case 0xbe126:case 0xbe130:case 0xbe134:case 0xbe13a:
    // Objects N15 (F4) blocks: JSR, BSR, LEA+JSR, BRA, JMP 2a00/4945e, RTS, BTST/BSET (Z only, +Bcc) blocks and the 16 consumers
    // 71152 (C returned by 7054c), 711a2 (705ca), 711c0 (boundary 70594), 711ce (7028e), 71dc8 76e4a 76eb0 (49fc6), 76daa (4983e),
    // 76dba (76f98), 76ed4 (1ab02), 76f28 (1ab80), 76f3e 76f84 (28ae), 76fbc 76fe2 (49392) and 71c48 (BTST+BEQ+BCS: the BCS reads the
    // C carried through 710e4 when 82 bit 1 is set). Known C inside the block: Clear 493ee 70298 702c6 70588 705fe 76fc0 76fe6 (ANDI
    // CCR) and 710d2 (MOVE.L #710e4,(A6)), Set 493e8 702c0 7058e 705f8 (ORI CCR), computed 493c8 493d4 (CMPA.L borrow) and 7029e
    // (CMPI.W borrow). The other MOVE/MOVEQ/TST/CMP/CMPI/CLR/NEG/ADD/ADDI/SUB/SUBI/SUBQ/AND/ANDI/EOR/ASR/LSL/EXT/SWAP blocks, the
    // MOVE.L #imm,(A6) blocks, the table blocks 7116c 711e6, the banked animation blocks, 71c86 (folded N04 TST.W) and the ORI CCR
    // blocks 76f50 76f92 (no consumer) stay Unknown.
    case 0x493e0:case 0x493ec:case 0x7028e:case 0x702ae:case 0x702b0:case 0x7054c:case 0x70556:case 0x7056a:case 0x70574:
    case 0x7057e:case 0x705ca:case 0x71062:case 0x7108e:case 0x710ba:case 0x710e4:case 0x710ee:case 0x7110e:case 0x7114e:
    case 0x71152:case 0x7115c:case 0x71166:case 0x7117a:case 0x7119e:case 0x711a2:case 0x711ac:case 0x711c0:case 0x711ca:
    case 0x711ce:case 0x711d8:case 0x711e2:case 0x7120a:case 0x71ad2:case 0x71b28:case 0x71b2e:case 0x71b3e:case 0x71bf0:
    case 0x71c48:case 0x71c56:case 0x71c6e:case 0x71d78:case 0x71db2:case 0x71dbc:case 0x71dc2:case 0x71dc8:case 0x71dd2:
    case 0x71e06:case 0x71e72:case 0x71e78:case 0x71e88:case 0x72d66:case 0x72d6c:case 0x72dce:case 0x76d44:case 0x76d4a:
    case 0x76d56:case 0x76daa:case 0x76db6:case 0x76dba:case 0x76dd8:case 0x76de2:case 0x76de8:case 0x76dec:case 0x76df2:
    case 0x76df8:case 0x76e2a:case 0x76e34:case 0x76e3a:case 0x76e3e:case 0x76e44:case 0x76e4a:case 0x76e4e:case 0x76e5e:
    case 0x76e90:case 0x76e9a:case 0x76ea0:case 0x76ea4:case 0x76eaa:case 0x76eb0:case 0x76eba:case 0x76eca:case 0x76ed4:
    case 0x76ed8:case 0x76ede:case 0x76ee4:case 0x76eee:case 0x76f1e:case 0x76f28:case 0x76f2c:case 0x76f3e:case 0x76f84:
    case 0x76f96:case 0x76fbc:case 0x76fe2:case 0x76fec:
    // Objects N16 (F4) blocks: JSR/JMP/BRA/RTS, LEA/MOVEA+JSR 775b2 79584 79592 795a0 79614 7967e, BTST/BSET/BCLR/BCHG (Z only, +Bcc)
    // blocks and the 23 BCC/BCS consumers 775bc 79688 (C returned by 493bc), 775f6 77620 7762e 7925a 7926c 792e0 792f2 792fa 7958e 7959c
    // (boundary helpers 79454 7949c 794e2 79400 79478 79722 7942e 494c0), 77604 77612 77652 77664 77672 77680 77d80 792bc (N16 helpers),
    // 79580 (4945e), 78c6a (1ab02), 78c86 (28ae); and the EORI.B #1,CCR consumers 792ac (4945e) 7961e (494c0), which invert a known C.
    // 79212 792fe 795ac 78c96 (ORI CCR) set and 7921c 792b2 79304 795b2 79624 (ANDI CCR) clear a known C. The MOVE/CLR/TST/CMPI/ADDQ/
    // SUBQ/EOR/ANDI.W/ASR blocks, MOVE.L #imm,(A6), the 28ae child and animation blocks and 79282 79286 7928c stay Unknown.
    case 0x77596:case 0x7759a:case 0x775a0:case 0x775b2:case 0x775bc:case 0x775c0:case 0x775ce:case 0x775f2:case 0x775f6:case 0x77600:
    case 0x77604:case 0x7760e:case 0x77612:case 0x7761c:case 0x77620:case 0x7762a:case 0x7762e:case 0x77638:case 0x7763c:case 0x77646:
    case 0x77652:case 0x7765c:case 0x77660:case 0x77664:case 0x7766e:case 0x77672:case 0x7767c:case 0x77680:case 0x7768a:case 0x77d70:
    case 0x77d76:case 0x77d7c:case 0x77d80:case 0x77d8a:case 0x7839a:case 0x783c0:case 0x783c6:case 0x783d2:case 0x783dc:case 0x783e6:
    case 0x78c22:case 0x78c34:case 0x78c44:case 0x78c4a:case 0x78c54:case 0x78c6a:case 0x78c74:case 0x78c86:case 0x78de6:case 0x7905e:
    case 0x79064:case 0x790a4:case 0x790fa:case 0x79114:case 0x791d0:case 0x791d6:case 0x791e8:case 0x791ea:case 0x791f0:case 0x791f8:
    case 0x791fa:case 0x79256:case 0x7925a:case 0x79268:case 0x7926c:case 0x79270:case 0x7927e:case 0x792a6:case 0x792ac:case 0x792b8:
    case 0x792bc:case 0x792e0:case 0x792e4:case 0x792ee:case 0x792f2:case 0x792f6:case 0x792fa:case 0x7957a:case 0x79580:case 0x79584:
    case 0x7958e:case 0x79592:case 0x7959c:case 0x795a0:case 0x795aa:case 0x7960a:case 0x79614:case 0x7961e:case 0x7967e:case 0x79688:
    case 0x7968c:case 0x79696:case 0x796cc:case 0x796d6:case 0x796de:
    // Objects N17 (F4) blocks: JSR/JMP/BRA/RTS, LEA+JSR 7a3fa 7a476 7b274 7b282 7b7c2, MOVEA/BTST/BSET/BCLR (Z only, +Bcc) blocks, BTST.B #0,D0
    // 7a460 and the 11 BCC/BCS consumers 7a390 (C returned by 7b200), 7a3a6 7a50a (7b7ae), 7a6c0 (7b570), 7a414 (49fc6), 7a4f0 7b0e6
    // (28ae), 7ab5e 7b206 (4b54e), 7abb6 (288c), 7b04a (497a6). 7a502 7b0f4 7b21c 7b22e 7b250 7b588 7b7ce (ORI CCR) set and 7b214 7b25c
    // 7b596 7b59e (ANDI CCR) clear a known C. The MOVE/MOVEQ/CLR/TST/CMP/ADD/SUB/NEG/EXT/LSL/LSR/ANDI.W blocks, the installs, the 28ae
    // child and animation blocks and the DBRA block 7a45a stay Unknown.
    case 0x7a390:case 0x7a398:case 0x7a3a2:case 0x7a3a6:case 0x7a3b0:case 0x7a3b2:case 0x7a3b8:case 0x7a3ce:case 0x7a3fa:case 0x7a40a:
    case 0x7a40e:case 0x7a414:case 0x7a460:case 0x7a476:case 0x7a480:case 0x7a48e:case 0x7a498:case 0x7a49c:case 0x7a4de:case 0x7a4f0:
    case 0x7a506:case 0x7a50a:case 0x7a514:case 0x7a53a:case 0x7a546:case 0x7a54a:case 0x7a554:case 0x7a65a:case 0x7a674:case 0x7a678:
    case 0x7a67c:case 0x7a680:case 0x7a692:case 0x7a6aa:case 0x7a6bc:case 0x7a6c0:case 0x7a6ca:case 0x7aa5e:case 0x7aa66:case 0x7aa96:
    case 0x7aab2:case 0x7ab14:case 0x7ab34:case 0x7ab3e:case 0x7ab44:case 0x7ab4a:case 0x7ab58:case 0x7ab5e:case 0x7ab70:case 0x7ab76:
    case 0x7ab9e:case 0x7abb0:case 0x7abb6:case 0x7abc0:case 0x7afb6:case 0x7afc4:case 0x7afce:case 0x7afe2:case 0x7b018:case 0x7b01e:
    case 0x7b024:case 0x7b034:case 0x7b03a:case 0x7b044:case 0x7b04a:case 0x7b05c:case 0x7b08c:case 0x7b0e6:case 0x7b118:case 0x7b14e:
    case 0x7b158:case 0x7b15e:case 0x7b162:case 0x7b168:case 0x7b17a:case 0x7b17c:case 0x7b182:case 0x7b1a2:case 0x7b200:case 0x7b206:
    case 0x7b20a:case 0x7b22a:case 0x7b238:case 0x7b242:case 0x7b274:case 0x7b27e:case 0x7b282:case 0x7b28c:case 0x7b570:case 0x7b59a:
    case 0x7b5a6:case 0x7b7c2:case 0x7b7cc:
    // Objects N18 (F4) blocks: JSR/BSR/JMP/BRA/RTS, the 27 BRA.W slots of the 862a0 table, LEA+JSR 86352 b78a2, LEA 8689a 868a2,
    // BTST/BSET (Z only, +Bcc) blocks and the 7 BCC/BCS consumers 86260 (C returned by 4b54e), 8635c (1ab02), 871d0 (49fc6), b6536
    // (28ae), b6600 (b7e5c), b7898 (288c), b78ac (1aa7e). b6544 (ORI CCR) sets a known C. The MOVE/MOVEQ/CLR/TST/CMP/CMPI/ADD/SUB/SUBI/
    // SUBQ/ADDQ/NEG/LSL/LSR/ASR/ANDI/EOR blocks, MOVE.L #imm,(A6), the 28ae child block, the animation blocks and 86298 stay Unknown.
    case 0x8625a:case 0x86260:case 0x86274:case 0x8627e:case 0x86282:case 0x862a4:case 0x862a8:case 0x862ac:case 0x862b0:case 0x862b4:
    case 0x862b8:case 0x862bc:case 0x862c0:case 0x862c4:case 0x862c8:case 0x862cc:case 0x862d0:case 0x862d4:case 0x862d8:case 0x862dc:
    case 0x862e0:case 0x862e4:case 0x862e8:case 0x862ec:case 0x862f0:case 0x862f4:case 0x862f8:case 0x862fc:case 0x86300:case 0x86304:
    case 0x86308:case 0x8630c:case 0x8631a:case 0x86352:case 0x8635c:case 0x86370:case 0x864b6:case 0x86584:case 0x865da:case 0x865e0:
    case 0x865e8:case 0x865f2:case 0x865fa:case 0x86600:case 0x86608:case 0x8661e:case 0x86624:case 0x8662c:case 0x86632:case 0x8663a:
    case 0x86640:case 0x866ca:case 0x866d0:case 0x86708:case 0x8684e:case 0x86852:case 0x86858:case 0x86866:case 0x86882:case 0x8689a:
    case 0x868a2:case 0x868bc:case 0x868d6:case 0x868e6:case 0x86f50:case 0x86f88:case 0x86fb0:case 0x86fb6:case 0x86fc6:case 0x87192:
    case 0x871c4:case 0x871ca:case 0x871d0:case 0x871da:case 0x871ea:case 0xb6318:case 0xb6536:case 0xb659e:case 0xb65f0:case 0xb65f6:
    case 0xb65fc:case 0xb6600:case 0xb660a:case 0xb7874:case 0xb787a:case 0xb7892:case 0xb7898:case 0xb78a2:case 0xb78ac:case 0xb78b6:
    case 0xdbea2:case 0xdbea4:case 0xdbee0:case 0xdbeea:
    // Objects N19 (F4) blocks: JSR/JMP/BRA/RTS, LEA+JSR b1b76 b1e02 b1e12, LEA b1c04, MOVEM.W (A7)+ + JSR b1d60, BTST/BSET/BCLR (Z only,
    // +Bcc) blocks and the 14 BCC/BCS consumers b15e6 b1b4e (C returned by 4b54e), b1702 (287e), b173e (28ae), b1760 (497a6), b17e8
    // (49fc6), b1804 (b1fd6), b1898 (b1dfa), b18f2 b1966 b19a0 (b15e0), b194c (b1ee6), b1b80 (1ab02), b1fdc (4945e). b15fe b174c (ORI CCR)
    // set and b1604 b1ffc (ANDI CCR) clear a known C. The MOVE/MOVEQ/CLR/TST/CMP/CMPI/ADDI/SUB/SUBQ/NEG/ANDI blocks, MOVE.L #imm,(A6),
    // the 28ae child blocks and the animation blocks stay Unknown.
    case 0x86742:case 0x86746:case 0x8674c:case 0x8675a:case 0x86776:case 0x8677e:case 0x86798:case 0x867ca:case 0x867d0:case 0x867f0:
    case 0x86800:case 0x86810:case 0xb15e0:case 0xb15e6:case 0xb15f4:case 0xb160a:case 0xb1628:case 0xb1642:case 0xb1654:case 0xb16ea:
    case 0xb16fc:case 0xb1702:case 0xb1706:case 0xb170c:case 0xb173e:case 0xb1750:case 0xb175a:case 0xb1760:case 0xb1772:case 0xb1784:
    case 0xb17dc:case 0xb17e2:case 0xb17e8:case 0xb17ec:case 0xb17f2:case 0xb1804:case 0xb1826:case 0xb182c:case 0xb1884:case 0xb188e:
    case 0xb1894:case 0xb1898:case 0xb18b4:case 0xb18b8:case 0xb18d6:case 0xb18ea:case 0xb18ee:case 0xb18f2:case 0xb1916:case 0xb1918:
    case 0xb1936:case 0xb193a:case 0xb1948:case 0xb194c:case 0xb1950:case 0xb1954:case 0xb195a:case 0xb195e:case 0xb1962:case 0xb1966:
    case 0xb1972:case 0xb1974:case 0xb1998:case 0xb199c:case 0xb19a0:case 0xb19a4:case 0xb19b0:case 0xb19d6:case 0xb1b42:case 0xb1b48:
    case 0xb1b4e:case 0xb1b60:case 0xb1b76:case 0xb1b80:case 0xb1b84:case 0xb1b8a:case 0xb1b8c:case 0xb1bba:case 0xb1bc0:case 0xb1c04:
    case 0xb1c0e:case 0xb1c12:case 0xb1c26:case 0xb1c80:case 0xb1d60:case 0xb1d6a:case 0xb1d8a:case 0xb1db8:case 0xb1de0:case 0xb1e02:
    case 0xb1e12:case 0xb1e1c:case 0xb1e22:case 0xb1e28:case 0xb1fd6:case 0xb1fdc:case 0xb2002:case 0xdbf68:
    // Objects N20 (F4) blocks: JSR/BSR/JMP/BRA/RTS, LEA/MOVEA+JSR 735b0 73936 b99ee b9b44, MOVEA.L #0,A0 7369a, BTST (Z only, +Bcc)
    // blocks and the 11 BCC/BCS consumers 735ba b99fa b9b50 (C returned by 1ab02), 73838 7388c 738e8 73932 (49fc6), b9cfe (288c), 73696
    // (49580) and 73660 736a6 (73690, the C of 49580 through 7369a/736a0). 495d8 (CMPI.W #8000,D0; EORI.B #1,CCR; RTS) sets the
    // computed C = D0.W bit 15. The MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/ADDI/SUB/SUBI/SUBQ/ANDI/NEG/LSL/LSR/MULU/SWAP blocks, the
    // installs, the 28ae child blocks and the animation blocks stay Unknown.
    case 0x49580:case 0x495ac:case 0x735b0:case 0x735ba:case 0x735be:case 0x735c4:case 0x735d2:case 0x735dc:case 0x735e2:
    case 0x7361a:case 0x73620:case 0x7364c:case 0x7365c:case 0x73660:case 0x7368e:case 0x73690:case 0x73696:case 0x7369a:
    case 0x736a0:case 0x736a2:case 0x736a6:case 0x736d0:case 0x7370c:case 0x737ba:case 0x737be:case 0x737c2:case 0x737d4:
    case 0x737d8:case 0x737e8:case 0x737ec:case 0x737f0:case 0x737f4:case 0x737f8:case 0x737fc:case 0x7382e:case 0x73832:
    case 0x73838:case 0x7383c:case 0x7384c:case 0x73850:case 0x73882:case 0x73886:case 0x7388c:case 0x73896:case 0x7389a:
    case 0x738da:case 0x738de:case 0x738e2:case 0x738e8:case 0x738f2:case 0x738f6:case 0x73928:case 0x7392c:case 0x73932:
    case 0x73936:case 0x73946:case 0x7394a:case 0x73970:case 0x73990:case 0x739be:case 0xb9880:case 0xb988c:case 0xb98b8:
    case 0xb990e:case 0xb9948:case 0xb997c:case 0xb99be:case 0xb99c4:case 0xb99ee:case 0xb99fa:case 0xb99fe:case 0xb9a04:
    case 0xb9a0a:case 0xb9a16:case 0xb9a1c:case 0xb9a2e:case 0xb9a34:case 0xb9a6c:case 0xb9ae8:case 0xb9b2c:case 0xb9b30:
    case 0xb9b36:case 0xb9b44:case 0xb9b50:case 0xb9b54:case 0xb9b5a:case 0xb9b60:case 0xb9b6c:case 0xb9b72:case 0xb9b84:
    case 0xb9b8a:case 0xb9bc4:case 0xb9c7c:case 0xb9c8e:case 0xb9cde:case 0xb9cf2:case 0xb9cf8:case 0xb9cfe:case 0xb9d02:
    case 0xb9d08:
    // Objects N21 (F4) blocks: JSR/BSR/JMP/BRA/RTS, MOVEA/LEA+JSR b9c26 c406e and the 3 BCC/BCS consumers b9c32 c4078 (C returned by
    // 1ab02) and b9d9a (288c). N21 produces no known C; the MOVE/CMP/CMPI/CMPA/ADD/ADDI blocks, the installs and the animation blocks
    // stay Unknown.
    case 0xb9c0e:case 0xb9c12:case 0xb9c18:case 0xb9c26:case 0xb9c32:case 0xb9c36:case 0xb9c3c:case 0xb9c42:case 0xb9c4e:
    case 0xb9c54:case 0xb9c66:case 0xb9c6c:case 0xb9d18:case 0xb9d2a:case 0xb9d7a:case 0xb9d8e:case 0xb9d94:case 0xb9d9a:
    case 0xb9d9e:case 0xb9da4:case 0xc404c:case 0xc4052:case 0xc4064:case 0xc406e:case 0xc4078:case 0xc407c:case 0xc4082:
    // Objects N22a (F4) blocks: JSR/BSR/JMP/BRA/RTS, LEA+JSR/BRA (1bf14 1bf1e 1bfbc 1bfc6 3d310 3d32c 3d340 3d3c4 3e1dc 3e222), BTST/BSET/
    // SNE (Z only, +Bcc) blocks, JMP (A0) 3e1b6 and the 16 BCC/BCS/SCS consumers 1bf0a (C returned by 484b4), 1bf2a 1bfd2 (289e), 3d338
    // (1aa7e), 3d34c (4d2d4), 3d358 (3dcac), 3d3ba (3dcf2), 3d3d0 (1ab02), 3dc5e (4d766), 3dd02 (49fc6), 3ddc0 (49fca), 3df92 3dfe2
    // 3e038 (28ae), 3e1d4 3e21a (288c). 1bf5c 3d3ea 3df96 3dfe6 (ORI CCR) set, 3d3de (TST.B) clears and 3dd08 (LSR.B #1) computes a
    // known C. The MOVE/MOVEQ/TST/CMP/CMPI/ADD/ADDI/ANDI/AND/SUBQ/NEG/EXT/LSR blocks, the installs and the animation blocks stay Unknown.
    case 0x1bf0a:case 0x1bf14:case 0x1bf1e:case 0x1bf24:case 0x1bf2a:case 0x1bf2e:case 0x1bf52:case 0x1bfbc:case 0x1bfc6:case 0x1bfcc:
    case 0x1bfd2:case 0x1bfd6:case 0x1c000:case 0x1c008:case 0x3d228:case 0x3d310:case 0x3d32c:case 0x3d338:case 0x3d33c:case 0x3d340:
    case 0x3d34c:case 0x3d358:case 0x3d380:case 0x3d384:case 0x3d3b2:case 0x3d3b6:case 0x3d3ba:case 0x3d3c4:case 0x3d3d0:case 0x3d3da:
    case 0x3d3ee:case 0x3db62:case 0x3dbba:case 0x3dc24:case 0x3dc2a:case 0x3dc58:case 0x3dc5e:case 0x3dc62:case 0x3dc7a:case 0x3dcfc:
    case 0x3dd02:case 0x3ddc0:case 0x3ddc4:case 0x3ddca:case 0x3de06:case 0x3de44:case 0x3de52:case 0x3df92:case 0x3dfe2:case 0x3e038:
    case 0x3e03c:case 0x3e130:case 0x3e178:case 0x3e1b6:case 0x3e1ce:case 0x3e1d4:case 0x3e1d8:case 0x3e1dc:case 0x3e1e2:case 0x3e1e8:
    case 0x3e214:case 0x3e21a:case 0x3e21e:case 0x3e222:case 0x3e238:case 0x3e23e:case 0x3e244:case 0x3e248:case 0x3e24a:
    // Objects N23 (F4) blocks: JSR/BSR/JMP/BRA/RTS, LEA/MOVEA+JSR/BRA (4d376 4d382 4dbac c3b6a 4da4a), BTST/ST (Z only, +Bcc) blocks,
    // JSR (A1) 4d38a, 4219c (MOVEM.W pop + BEQ on the recomputed c3ce Z), 42238 (SPL on the recomputed N) and the 14 BCC/BCS/SCS
    // consumers 420c4 4dbbc (C returned by 288c), 423d6 (4a46c), 4d2e0 4d2f0 (4d36e; SCS then MOVE/TST, so the block ends Unknown),
    // 4d35a (4d344 CMP.W D0,D1), 4d90e 4d934 (289e), 4db9a (484b4), 4dbb2 (the JSR (A1) callee), c3b74 (1ab02), c3b94 (4b54e), c3bc4
    // c3bea (28ae). ORI CCR (484be 4d310 4d320 4d350 4d35e 4d366 4d3a6 4d40c 4d922 4d948 c3bd2 c3bf8) sets, ANDI CCR (484c4 4d2fe
    // 4d412 4d950) clears and 4d344 (CMP.W) / 4d77a (ADD.B D1,D1) compute a known C. The other blocks stay Unknown.
    case 0x420be:case 0x420c4:case 0x420c8:case 0x420e8:case 0x42154:case 0x4219c:case 0x42238:case 0x423d0:case 0x423d6:case 0x42408:
    case 0x42410:case 0x484b4:case 0x4d2e0:case 0x4d2f0:case 0x4d34a:case 0x4d35a:case 0x4d376:case 0x4d382:case 0x4d38a:case 0x4d514:
    case 0x4d51c:case 0x4d766:case 0x4d76c:case 0x4d778:case 0x4d90e:case 0x4d92a:case 0x4d934:case 0x4d95e:case 0x4d966:case 0x4da4a:
    case 0x4db8e:case 0x4db94:case 0x4db9a:case 0x4db9e:case 0x4dbac:case 0x4dbb2:case 0x4dbb6:case 0x4dbbc:case 0x4dbc0:case 0x4dbca:
    case 0x4dbd4:case 0x4dbd6:case 0xc3afe:case 0xc3b3e:case 0xc3b4a:case 0xc3b54:case 0xc3b5a:case 0xc3b5e:case 0xc3b64:case 0xc3b6a:
    case 0xc3b74:case 0xc3b78:case 0xc3b7e:case 0xc3b8e:case 0xc3b94:case 0xc3b9c:case 0xc3ba6:case 0xc3bc4:case 0xc3bd6:case 0xc3bea:
    case 0xc3bfc:case 0xc3c02:case 0xc3c14:case 0xc3c1a:
    // Objects N28 (F4) blocks: JSR/BSR/JMP/BRA/RTS, LEA+BRA/JMP/JSR (2b422 2b434 2b43c 2b688 2b9c2 2ca72 3075e 30778), BTST/BSET/ST/SNE
    // (Z only, +Bcc) blocks (2b418 2b8a0 2b9a4 2c760 307d2 30f8a 30fc2 30fda) and the 10 BCC/BCS consumers 2b82e 2b870 (C returned by
    // 28ae), 2b9cc 3076a (1aa7e), 2ba10 30784 (4d2d4), 2ba1c 2c89e (2b63e), 30790 (319f6), 30fbe (4d766). ORI CCR (2b832 2b874) sets and
    // ANDI CCR (2b6b6) clears a known C. The other blocks stay Unknown.
    case 0x2b418:case 0x2b422:case 0x2b434:case 0x2b43c:case 0x2b688:case 0x2b82e:case 0x2b85c:case 0x2b870:case 0x2b89e:case 0x2b8a0:
    case 0x2b8a6:case 0x2b8aa:case 0x2b8be:case 0x2b9a4:case 0x2b9be:case 0x2b9c2:case 0x2b9cc:case 0x2b9d0:case 0x2ba10:case 0x2ba1c:
    case 0x2c760:case 0x2c76e:case 0x2c89a:case 0x2c89e:case 0x2c8a8:case 0x2c8ac:case 0x2c8b0:case 0x2c8b4:case 0x2c8c6:case 0x2c8f0:
    case 0x2ca72:case 0x2ca9a:case 0x2cb2a:case 0x306a8:case 0x30748:case 0x3075a:case 0x3075e:case 0x3076a:case 0x30774:case 0x30778:
    case 0x30784:case 0x30790:case 0x307bc:case 0x307d2:case 0x307d6:case 0x30ed2:case 0x30f84:case 0x30f8a:case 0x30fb8:case 0x30fbe:
    case 0x30fc2:case 0x30fda:case 0x31000:
    // Objects N24 (F4) blocks: JSR-only blocks (5e050 5e7aa 5e7dc 5e7ea 5e7f0), BRA blocks, BTST.B #7,61(A6)+BEQ (5e7fe), RTS 5e8a4
    // and the consumer 5e7f6 (BCC.W after JSR 4b54e). N24 has no known C producer; every other block stays Unknown.
    case 0x5e050:case 0x5e104:case 0x5e20a:case 0x5e246:case 0x5e27c:case 0x5e2ae:case 0x5e2de:case 0x5e310:case 0x5e340:case 0x5e3ca:
    case 0x5e3ce:case 0x5e414:case 0x5e524:case 0x5e574:case 0x5e57e:case 0x5e5bc:case 0x5e5ec:case 0x5e62a:case 0x5e65a:case 0x5e68e:
    case 0x5e6de:case 0x5e728:case 0x5e7aa:case 0x5e7d8:case 0x5e7dc:case 0x5e7ea:case 0x5e7f0:case 0x5e7f6:case 0x5e7fe:case 0x5e846:
    case 0x5e878:case 0x5e8a0:case 0x5e8a4:
    // Objects N29 (F4) blocks: JSR/JMP/BRA/RTS, LEA/MOVEA+JSR (30ac0 30e70), BTST (Z only, +Bcc) blocks (30902 3090a 30914 30962
    // 3096a 30974 30aa8 30ab2 30f2a), the 9 BRA.W slots of 30a76 and the 15 BCC/BCS/SCS consumers 306fc (C returned by 1aa7e), 3070a
    // 309e4 (3165e = 49fc6), 30dc2 (3164a), 30dea 30e3e 31038 (288c), 30dfa 30e52 (ea680), 30ec0 (49fc6), 30efa (319f6), 3195c 3199a
    // (28ae), 31a04 (4d418), 31676 (49c38; SCS then MOVE, so the block ends Unknown). ANDI.W #8 (31650) clears and ORI CCR (31658 31960
    // 31a08) sets a known C. The other blocks stay Unknown.
    case 0x306ec:case 0x306f0:case 0x306fc:case 0x30706:case 0x3070a:case 0x30714:case 0x308fe:case 0x30902:case 0x3090a:case 0x30914:
    case 0x30926:case 0x3092a:case 0x3092e:case 0x30932:case 0x30936:case 0x3093a:case 0x3093e:case 0x3095e:case 0x30962:case 0x3096a:
    case 0x30974:case 0x30986:case 0x3098a:case 0x309ac:case 0x309b0:case 0x309d0:case 0x309d4:case 0x309d8:case 0x309dc:case 0x309e0:
    case 0x309e4:case 0x309ee:case 0x30a50:case 0x30a54:case 0x30a7a:case 0x30a7e:case 0x30a82:case 0x30a86:case 0x30a8a:case 0x30a8e:
    case 0x30a92:case 0x30a96:case 0x30a9a:case 0x30aa8:case 0x30ab2:case 0x30abc:case 0x30ac0:case 0x30ad6:case 0x30b66:case 0x30dbe:
    case 0x30dc2:case 0x30dc6:case 0x30de4:case 0x30dea:case 0x30dee:case 0x30df4:case 0x30dfa:case 0x30e12:case 0x30e38:case 0x30e3e:
    case 0x30e4c:case 0x30e52:case 0x30e70:case 0x30e7c:case 0x30e82:case 0x30e88:case 0x30eae:case 0x30eb4:case 0x30eba:case 0x30ec0:
    case 0x30eca:case 0x30ecc:case 0x30ed6:case 0x30ef6:case 0x30efa:case 0x30f2a:case 0x31002:case 0x31032:case 0x31038:case 0x3103c:
    case 0x3104a:case 0x310ca:case 0x310d0:case 0x310d6:case 0x310d8:case 0x3164a:case 0x3165c:case 0x3165e:case 0x31664:case 0x3166a:
    case 0x31676:case 0x31694:case 0x31696:case 0x316ac:case 0x3195c:case 0x3199a:case 0x319b4:case 0x31a04:case 0x31a10:case 0x31a22:
    case 0x31a24:case 0x33116:
    // Objects B1c (F4) blocks: the 27 BRA.W slots of 30b84 and the 9 of 335fe, JSR/JMP/BRA-only blocks, LEA+JSR (30cb8 339bc 339d2 339ec),
    // BTST (Z only, +Bcc) blocks and the 6 BCC/BCS consumers 30c7c (C returned by 319f6), 3328e 3352c (49fc6), 33390 335b4 (4c2c4), 33a08
    // (4d418). B1c has no known-C producer; every other block (MOVE/MOVEQ/TST/CMP/SUB/ADD/AND/ASR/LSL/SUBQ) stays Unknown.
    case 0x30b84:case 0x30b88:case 0x30b8c:case 0x30b90:case 0x30b94:case 0x30b98:case 0x30b9c:case 0x30ba0:case 0x30ba4:case 0x30ba8:
    case 0x30bac:case 0x30bb0:case 0x30bb4:case 0x30bb8:case 0x30bbc:case 0x30bc0:case 0x30bc4:case 0x30bc8:case 0x30bcc:case 0x30bd0:
    case 0x30bd4:case 0x30bd8:case 0x30bdc:case 0x30be0:case 0x30be4:case 0x30be8:case 0x30bec:case 0x30c00:case 0x30c64:case 0x30c68:
    case 0x30c78:case 0x30c7c:case 0x30c86:case 0x30c8a:case 0x30c8e:case 0x30c92:case 0x30cb4:case 0x30cb8:case 0x30cd6:case 0x30d66:
    case 0x33248:case 0x3324c:case 0x33274:case 0x33280:case 0x33284:case 0x33288:case 0x3328e:case 0x33298:case 0x332d6:case 0x332f0:
    case 0x33320:case 0x33324:case 0x33328:case 0x3332c:case 0x33332:case 0x33364:case 0x33368:case 0x33370:case 0x3337a:case 0x33390:
    case 0x333ac:case 0x333b4:case 0x333b8:case 0x333bc:case 0x333c0:case 0x333e2:case 0x3341a:case 0x33428:case 0x33430:case 0x3346a:
    case 0x3346e:case 0x33472:case 0x3349e:case 0x334a8:case 0x334ac:case 0x334b4:case 0x334bc:case 0x334c0:case 0x334c4:case 0x334c8:
    case 0x334cc:case 0x33500:case 0x33504:case 0x3350c:case 0x33516:case 0x3351a:case 0x3351e:case 0x33522:case 0x33526:case 0x3352c:
    case 0x33536:case 0x33546:case 0x3354a:case 0x33580:case 0x33584:case 0x33588:case 0x335b4:case 0x335cc:case 0x335d0:case 0x335d4:
    case 0x335d8:case 0x335fe:case 0x33602:case 0x33606:case 0x3360a:case 0x3360e:case 0x33612:case 0x33616:case 0x3361a:case 0x3361e:
    case 0x3362c:case 0x33636:case 0x3363a:case 0x3364e:case 0x336cc:case 0x33990:case 0x339aa:case 0x339bc:case 0x339d2:case 0x339dc:
    case 0x339ec:case 0x339f6:case 0x33a08:case 0x33a50:
    // Objects N25 (F4) blocks: JSR-only blocks, ST.B+JSR 5e9ec, ST.B 5edca, BRA blocks, RTS (5e8be 5e8c6 5e9d4 5ebde 5eeaa 5f182 5f238)
    // and the consumers 5ec9c (BCS.W after JSR 49370), 5ee1c 5f190 (BCC.W after JSR 49fc6). N25 has no known C producer; every other
    // block stays Unknown.
    case 0x5e8b0:case 0x5e8be:case 0x5e8c0:case 0x5e8c6:case 0x5e8dc:case 0x5e95c:case 0x5e97a:case 0x5e97e:case 0x5e9d4:case 0x5e9ec:
    case 0x5ea2e:case 0x5ea34:case 0x5eae2:case 0x5eae8:case 0x5ebc8:case 0x5ebd0:case 0x5ebde:case 0x5ec1e:case 0x5ec88:case 0x5ec96:
    case 0x5ec9c:case 0x5eca0:case 0x5eca6:case 0x5ecf4:case 0x5ecfa:case 0x5ed00:case 0x5ed94:case 0x5edca:case 0x5edce:case 0x5edfa:
    case 0x5ee16:case 0x5ee1c:case 0x5eeaa:case 0x5f006:case 0x5f00c:case 0x5f074:case 0x5f0e8:case 0x5f15a:case 0x5f174:case 0x5f182:
    case 0x5f184:case 0x5f18a:case 0x5f190:case 0x5f1c2:case 0x5f1dc:case 0x5f1fe:case 0x5f218:case 0x5f238:
    // Objects N26 (F4) blocks: JSR-only blocks, MOVEA+JSR 5fa02, LEA(+BRA) blocks 5f308 5f310 5f46c 5f474 5fcc4 5fccc, BRA blocks, RTS
    // and the consumers 5f394 5f876 5fcb4 (BCC.W after JSR 49fc6), 5f3c4 5f3ea 5f414 5f43a (BCC.W after JSR 28ae). 5f3d6 5f3fc 5f426
    // 5f44c (ORI.B #1,CCR) set a known Set that no block consumes; every other block stays Unknown.
    case 0x5f26a:case 0x5f270:case 0x5f308:case 0x5f310:case 0x5f32e:case 0x5f336:case 0x5f354:case 0x5f386:case 0x5f388:case 0x5f38e:
    case 0x5f394:case 0x5f3c4:case 0x5f3ea:case 0x5f400:case 0x5f414:case 0x5f43a:case 0x5f45c:case 0x5f46c:case 0x5f474:case 0x5f4ae:
    case 0x5f774:case 0x5f77a:case 0x5f860:case 0x5f86e:case 0x5f870:case 0x5f876:case 0x5f9a4:case 0x5f9f8:case 0x5fa02:case 0x5fa66:
    case 0x5fab4:case 0x5fb02:case 0x5fb04:case 0x5fb2e:case 0x5fb34:case 0x5fbd8:case 0x5fc48:case 0x5fc62:case 0x5fc70:case 0x5fc8c:
    case 0x5fc8e:case 0x5fc9c:case 0x5fca6:case 0x5fca8:case 0x5fcae:case 0x5fcb4:case 0x5fcc4:case 0x5fccc:case 0x5fd02:
    // Objects N30a (F4) blocks: JSR/JMP/BRA/RTS, LEA+JSR (33184 331e2 331f6), LEA+BRA (34608 3462c 34650 34748), BTST (Z only,
    // +Bcc) blocks (33170 33198 337bc 33c2a 33c54), BTST+SNE+BEQ 33a8e, BSET 33ac6 / 33ade, the 27 BRA.W slots of 336e6, JMP (A1)
    // (346fa 3489a) and the 10 BCC consumers 3318e 331ec (C returned by 1aa7e), 33200 (4d2d4), 33212 (4d418), 33ac2 (4d766), 33b8c
    // 33bda (28ae), 34638 (3465a = 49fc6), 346cc 3487a (288c). ORI CCR (33b90) sets a known C. The other blocks stay Unknown.
    case 0x3316a:case 0x33170:case 0x33180:case 0x33184:case 0x3318e:case 0x33198:case 0x331a2:case 0x331a8:case 0x331c2:case 0x331d8:
    case 0x331dc:case 0x331e2:case 0x331ec:case 0x331f6:case 0x33200:case 0x33212:case 0x3323a:case 0x336ea:case 0x336ee:case 0x336f2:
    case 0x336f6:case 0x336fa:case 0x336fe:case 0x33702:case 0x33706:case 0x3370a:case 0x3370e:case 0x33712:case 0x33716:case 0x3371a:
    case 0x3371e:case 0x33722:case 0x33726:case 0x3372a:case 0x3372e:case 0x33732:case 0x33736:case 0x3373a:case 0x3373e:case 0x33742:
    case 0x33746:case 0x3374a:case 0x3374e:case 0x33752:case 0x3377c:case 0x33782:case 0x337a8:case 0x337b4:case 0x337b8:case 0x337bc:
    case 0x337da:case 0x337de:case 0x337e2:case 0x3380e:case 0x33812:case 0x33816:case 0x33838:case 0x33958:case 0x33a88:case 0x33a8e:
    case 0x33abc:case 0x33ac2:case 0x33ac6:case 0x33ade:case 0x33b0c:case 0x33b8c:case 0x33bda:case 0x33bde:case 0x33c28:case 0x33c2a:
    case 0x33c34:case 0x33c48:case 0x33c4e:case 0x33c54:case 0x33c5e:case 0x33c6c:case 0x33c72:case 0x34608:case 0x34610:case 0x34614:
    case 0x3462c:case 0x34634:case 0x34638:case 0x34642:case 0x34650:case 0x34658:case 0x346a2:case 0x346be:case 0x346c6:case 0x346cc:
    case 0x346fa:case 0x34714:case 0x34748:case 0x34874:case 0x3487a:case 0x3489a:case 0x3489c:
    // Objects N27 (F4) blocks: JSR-only blocks, ST(+JSR) 5ff8a 600f8, LEA(+BRA) blocks 5ff98 5ffa0, BRA / BSR blocks, RTS and the
    // consumers 5ff7e (BCC.W after JSR 49fc6), 6019e 601c8 (BCC.W after JSR 28ae). 601b0 601da (ORI.B #1,CCR) set a known Set that no
    // block consumes; every other block stays Unknown.
    case 0x5fd44:case 0x5fd4a:case 0x5fdee:case 0x5fe40:case 0x5fe4e:case 0x5fe76:case 0x5feae:case 0x5feb2:case 0x5fedc:case 0x5ff06:
    case 0x5ff2a:case 0x5ff4e:case 0x5ff6e:case 0x5ff72:case 0x5ff78:case 0x5ff7e:case 0x5ff8a:case 0x5ff8e:case 0x5ff98:case 0x5ffa0:
    case 0x5ffd6:case 0x6001c:case 0x600dc:case 0x600f8:case 0x60126:case 0x6013c:case 0x60166:case 0x6019e:case 0x601b4:case 0x601c8:
    case 0x601fa:case 0x60242:case 0x60294:case 0x602e6:case 0x60304:case 0x60308:case 0x6030e:case 0x60314:case 0x60332:case 0x603f8:
    case 0x60406:case 0x60408:case 0x6040e:case 0x60414:case 0x60432:case 0x604ee:case 0x604fc:case 0x604fe:case 0x60504:
    // Objects N31 (F4) blocks: JSR/JMP/BRA/RTS, LEA+JSR (38c14 38c36 38c48 38cce 38d18 3a3fc), MOVEA+JSR 38ca2, BSET+MOVEA+JSR
    // 38cc0, BTST (Z only, +Bcc) 3a350 3a3cc, BTST+SNE+BEQ 3a406, BSET 3a43e / 3a456 and the 10 consumers 38c40 38cd8 38d22 (C
    // returned by 1aa7e), 38c52 (4d2d4), 38c5e 3a384 (3a4a4), 38ce4 38d2e (3b334), 3a340 (49fc6), 3a43a (4d766). The code pointer
    // 38d44 (TST.B Clear) / 38d50 (ORI Set) gives a known C to N23 4dbb2. The other blocks stay Unknown.
    case 0x34750:case 0x38ba0:case 0x38bd2:case 0x38c14:case 0x38c1e:case 0x38c36:case 0x38c40:case 0x38c44:case 0x38c48:case 0x38c52:
    case 0x38c5e:case 0x38c86:case 0x38c8a:case 0x38ca2:case 0x38cac:case 0x38cc0:case 0x38cce:case 0x38cd8:case 0x38cdc:case 0x38ce0:
    case 0x38ce4:case 0x38d0a:case 0x38d18:case 0x38d22:case 0x38d26:case 0x38d2a:case 0x38d2e:case 0x38d54:case 0x3a2f4:case 0x3a334:
    case 0x3a33a:case 0x3a340:case 0x3a344:case 0x3a34a:case 0x3a34c:case 0x3a350:case 0x3a380:case 0x3a384:case 0x3a3cc:case 0x3a3e8:
    case 0x3a3fc:case 0x3a406:case 0x3a434:case 0x3a43a:case 0x3a43e:case 0x3a456:case 0x3a4a2:
    // Objects N32a (F4) blocks: JSR-only blocks, MOVEA(+JSR) blocks, BSET/BCLR(+MOVEA+JSR / +BRA) blocks 38dfc 391b2 395ee 3960a,
    // BTST (Z only, +Bcc) blocks, BRA blocks and the 14 consumers 38e12 38e56 39056 39148 391c8 3975c 397c4 398a0 (BCC.W after JSR
    // 3b334) and 39128 396ca 3981a 39900 39952 3998e (MOVEM.L (A7)+,D0; BCS.W after JSR 3a4da). Every other block stays Unknown.
    case 0x38dde:case 0x38de8:case 0x38dfc:case 0x38e0a:case 0x38e0e:case 0x38e12:case 0x38e1c:case 0x38e36:case 0x38e40:case 0x38e4e:
    case 0x38e52:case 0x38e56:case 0x3900e:case 0x39028:case 0x3902c:case 0x39034:case 0x3903c:case 0x39046:case 0x3904e:case 0x39052:
    case 0x39056:case 0x39072:case 0x39086:case 0x39090:case 0x390a2:case 0x390a6:case 0x390ae:case 0x390b6:case 0x390c0:case 0x390d0:
    case 0x390da:case 0x390e2:case 0x390ec:case 0x3910c:case 0x39128:case 0x39130:case 0x39138:case 0x39140:case 0x39144:case 0x39148:
    case 0x39152:case 0x39160:case 0x3917a:case 0x39184:case 0x39188:case 0x39190:case 0x391a0:case 0x391aa:case 0x391b2:case 0x391c0:
    case 0x391c4:case 0x391c8:case 0x391e4:case 0x395dc:case 0x395ee:case 0x395f8:case 0x3960a:case 0x39626:case 0x39630:case 0x39634:
    case 0x39654:case 0x3965e:case 0x39662:case 0x3966a:case 0x39672:case 0x3967c:case 0x39684:case 0x3968e:case 0x396ae:case 0x396ca:
    case 0x396d2:case 0x396da:case 0x396ec:case 0x396f6:case 0x396fa:case 0x39702:case 0x39714:case 0x3971e:case 0x39728:case 0x39730:
    case 0x39734:case 0x39738:case 0x3973c:case 0x39746:case 0x39754:case 0x39758:case 0x3975c:case 0x39766:case 0x3976a:case 0x3979e:
    case 0x397a8:case 0x397ac:case 0x397b4:case 0x397bc:case 0x397c0:case 0x397c4:case 0x397ce:case 0x397dc:case 0x397fa:case 0x397fe:
    case 0x3981a:case 0x39830:case 0x39834:case 0x39838:case 0x39848:case 0x39868:case 0x39882:case 0x39886:case 0x3989c:case 0x398a0:
    case 0x398aa:case 0x398ba:case 0x398d0:case 0x398e0:case 0x398e4:case 0x39900:case 0x39908:case 0x39932:case 0x39936:case 0x39952:
    case 0x3995a:case 0x3995e:case 0x3996e:case 0x39972:case 0x3998e:case 0x39996:case 0x3999a:case 0x399ae:case 0x399ce:case 0x399e8:
    case 0x399ec:case 0x39a02:case 0x39a06:case 0x39a16:
    // Frame head H1 (F5) blocks: JSR/BSR/BRA/RTS/LEA, BTST/BSET/BCLR (Z only, +Bcc) only (b88 ba8 e98 ec4 among them). H1 has no
    // carry consumer and no known-carry producer (every Bcc and the 1879c SUBX read flags made in their own block); the guard blocks
    // f3c f44 f4c f52 and every MOVE/MOVEQ/CLR/CMP/CMPI/CMPA/TST/ADD/ADDQ/SUB/SUBQ/SUBI/SUBX/AND/ANDI/OR/LSR/SNE block stay Unknown.
    case 0xb88:case 0xba8:case 0xe4a:case 0xe8c:case 0xe92:case 0xe98:case 0xec4:case 0xf2a:case 0xf54:case 0xf94:
    case 0xfae:case 0xfb4:case 0xfd6:case 0x1000:case 0x3dc0:case 0x8bc8:case 0x8bde:case 0x8c14:case 0x903a:case 0x9054:
    case 0x955c:case 0x166c8:case 0x16bb8:case 0x16bc8:case 0x16c18:case 0x16c2c:case 0x16c4c:case 0x16c98:case 0x16cae:case 0x16ccc:
    case 0x187d6:case 0x1ae78:case 0x1ae84:case 0x1ae90:
    // Objects N32b (F4) blocks: JSR-only blocks, MOVEA/LEA(+JSR) blocks, BTST (Z only, +Bcc) blocks, BRA blocks (the 18 BRA.W table
    // slots of 39e7a / 39f4e among them) and the 8 consumers 39c58 39d78 (BCC.W after JSR 3b334), 39c90 39d9e (BCC.W after JSR 28ae),
    // 39e40 39f7c (BCC.W after JSR 1ab02) and 39c30 39d50 (MOVEM.L (A7)+,D0; BCS.W after JSR 3a4da). 39c9e / 39dac (ORI.B #1,CCR) set C
    // in the executor; every other block stays Unknown.
    case 0x39b72:case 0x39b7c:case 0x39b80:case 0x39b8a:case 0x39bb2:case 0x39bbc:case 0x39bc8:case 0x39bd0:case 0x39bd8:case 0x39be2:
    case 0x39bea:case 0x39bf4:case 0x39c14:case 0x39c30:case 0x39c38:case 0x39c40:case 0x39c48:case 0x39c50:case 0x39c54:case 0x39c58:
    case 0x39c6a:case 0x39c90:case 0x39ca2:case 0x39cb0:case 0x39cda:case 0x39ce4:case 0x39ce8:case 0x39cf0:case 0x39cf8:case 0x39d02:
    case 0x39d0a:case 0x39d14:case 0x39d34:case 0x39d50:case 0x39d58:case 0x39d60:case 0x39d68:case 0x39d70:case 0x39d74:case 0x39d78:
    case 0x39d9e:case 0x39db0:case 0x39dc6:case 0x39dd0:case 0x39e36:case 0x39e40:case 0x39e5c:case 0x39e60:case 0x39e7a:case 0x39e7e:
    case 0x39e82:case 0x39e86:case 0x39e8a:case 0x39e8e:case 0x39e92:case 0x39e96:case 0x39e9a:case 0x39e9e:case 0x39eae:case 0x39ec4:
    case 0x39ece:case 0x39ef4:case 0x39f1c:case 0x39f20:case 0x39f2a:case 0x39f34:case 0x39f4e:case 0x39f52:case 0x39f56:case 0x39f5a:
    case 0x39f5e:case 0x39f62:case 0x39f66:case 0x39f6a:case 0x39f6e:case 0x39f72:case 0x39f7c:case 0x39f8a:case 0x39f94:case 0x39f98:
    // Objects N33 (F4) blocks: JSR/BSR/JMP/BRA/RTS, MOVEA(+JSR/RTS) 3a1e0 46bfc, LEA+JSR 3a242, MOVEM.L (A7)+ + BRA 4bdfe, BTST/BSET
    // (Z only, +Bcc) blocks and the 8 consumers 3b16c 3b208 (C returned by 288c), 3b21e 3b380 3b38c (49fc6), 3b400 (49fca), 3b5a0
    // (28ae), 4b8ee (482aa). 482b4 (ANDI CCR, Clear) / 482ba (ORI CCR, Set) and 3b392 / 3b410 (LSR.B #1 of a 00/ff BYTE) give a known
    // C. The other blocks stay Unknown.
    case 0x3a1e0:case 0x3a1fe:case 0x3a202:case 0x3a212:case 0x3a216:case 0x3a21a:case 0x3a21e:case 0x3a222:case 0x3a23e:case 0x3a242:
    case 0x3a25e:case 0x3a264:case 0x3a2ee:case 0x3b166:case 0x3b16c:case 0x3b178:case 0x3b17a:case 0x3b19a:case 0x3b1a0:case 0x3b1a6:
    case 0x3b1a8:case 0x3b1f6:case 0x3b202:case 0x3b208:case 0x3b20c:case 0x3b212:case 0x3b218:case 0x3b21e:case 0x3b222:case 0x3b228:
    case 0x3b22a:case 0x3b268:case 0x3b26a:case 0x3b274:case 0x3b282:case 0x3b288:case 0x3b292:case 0x3b2a0:case 0x3b30e:case 0x3b320:
    case 0x3b332:case 0x3b36c:case 0x3b376:case 0x3b37a:case 0x3b380:case 0x3b386:case 0x3b38c:case 0x3b400:case 0x3b404:case 0x3b40a:
    case 0x3b55a:case 0x3b560:case 0x3b5a0:case 0x3b5a4:case 0x46bfc:case 0x482aa:case 0x4b8e8:case 0x4b8ee:case 0x4b8f0:case 0x4b9c8:
    case 0x4babc:case 0x4bd02:case 0x4bd88:case 0x4bdaa:case 0x4bdec:case 0x4bdf4:case 0x4bdfe:case 0x4be50:case 0x4be6c:case 0x4bfb4:
    case 0x4bfb8:case 0x4bfbc:case 0x4c0ea:case 0x4c0ee:case 0x4c38c:
    // F5 H3 FLOW_ONLY blocks: the 256 dirty-mark cell BSET blocks 579c + 26k, the LEA-only last cell block 7188 and the
    // BCLR / BSR / BRA / RTS blocks of the palette rebuild (contract carry section).
    case 0x579c:case 0x57b6:case 0x57d0:case 0x57ea:case 0x5804:case 0x581e:case 0x5838:case 0x5852:case 0x586c:case 0x5886:case 0x58a0:case 0x58ba:
    case 0x58d4:case 0x58ee:case 0x5908:case 0x5922:case 0x593c:case 0x5956:case 0x5970:case 0x598a:case 0x59a4:case 0x59be:case 0x59d8:case 0x59f2:
    case 0x5a0c:case 0x5a26:case 0x5a40:case 0x5a5a:case 0x5a74:case 0x5a8e:case 0x5aa8:case 0x5ac2:case 0x5adc:case 0x5af6:case 0x5b10:case 0x5b2a:
    case 0x5b44:case 0x5b5e:case 0x5b78:case 0x5b92:case 0x5bac:case 0x5bc6:case 0x5be0:case 0x5bfa:case 0x5c14:case 0x5c2e:case 0x5c48:case 0x5c62:
    case 0x5c7c:case 0x5c96:case 0x5cb0:case 0x5cca:case 0x5ce4:case 0x5cfe:case 0x5d18:case 0x5d32:case 0x5d4c:case 0x5d66:case 0x5d80:case 0x5d9a:
    case 0x5db4:case 0x5dce:case 0x5de8:case 0x5e02:case 0x5e1c:case 0x5e36:case 0x5e50:case 0x5e6a:case 0x5e84:case 0x5e9e:case 0x5eb8:case 0x5ed2:
    case 0x5eec:case 0x5f06:case 0x5f20:case 0x5f3a:case 0x5f54:case 0x5f6e:case 0x5f88:case 0x5fa2:case 0x5fbc:case 0x5fd6:case 0x5ff0:case 0x600a:
    case 0x6024:case 0x603e:case 0x6058:case 0x6072:case 0x608c:case 0x60a6:case 0x60c0:case 0x60da:case 0x60f4:case 0x610e:case 0x6128:case 0x6142:
    case 0x615c:case 0x6176:case 0x6190:case 0x61aa:case 0x61c4:case 0x61de:case 0x61f8:case 0x6212:case 0x622c:case 0x6246:case 0x6260:case 0x627a:
    case 0x6294:case 0x62ae:case 0x62c8:case 0x62e2:case 0x62fc:case 0x6316:case 0x6330:case 0x634a:case 0x6364:case 0x637e:case 0x6398:case 0x63b2:
    case 0x63cc:case 0x63e6:case 0x6400:case 0x641a:case 0x6434:case 0x644e:case 0x6468:case 0x6482:case 0x649c:case 0x64b6:case 0x64d0:case 0x64ea:
    case 0x6504:case 0x651e:case 0x6538:case 0x6552:case 0x656c:case 0x6586:case 0x65a0:case 0x65ba:case 0x65d4:case 0x65ee:case 0x6608:case 0x6622:
    case 0x663c:case 0x6656:case 0x6670:case 0x668a:case 0x66a4:case 0x66be:case 0x66d8:case 0x66f2:case 0x670c:case 0x6726:case 0x6740:case 0x675a:
    case 0x6774:case 0x678e:case 0x67a8:case 0x67c2:case 0x67dc:case 0x67f6:case 0x6810:case 0x682a:case 0x6844:case 0x685e:case 0x6878:case 0x6892:
    case 0x68ac:case 0x68c6:case 0x68e0:case 0x68fa:case 0x6914:case 0x692e:case 0x6948:case 0x6962:case 0x697c:case 0x6996:case 0x69b0:case 0x69ca:
    case 0x69e4:case 0x69fe:case 0x6a18:case 0x6a32:case 0x6a4c:case 0x6a66:case 0x6a80:case 0x6a9a:case 0x6ab4:case 0x6ace:case 0x6ae8:case 0x6b02:
    case 0x6b1c:case 0x6b36:case 0x6b50:case 0x6b6a:case 0x6b84:case 0x6b9e:case 0x6bb8:case 0x6bd2:case 0x6bec:case 0x6c06:case 0x6c20:case 0x6c3a:
    case 0x6c54:case 0x6c6e:case 0x6c88:case 0x6ca2:case 0x6cbc:case 0x6cd6:case 0x6cf0:case 0x6d0a:case 0x6d24:case 0x6d3e:case 0x6d58:case 0x6d72:
    case 0x6d8c:case 0x6da6:case 0x6dc0:case 0x6dda:case 0x6df4:case 0x6e0e:case 0x6e28:case 0x6e42:case 0x6e5c:case 0x6e76:case 0x6e90:case 0x6eaa:
    case 0x6ec4:case 0x6ede:case 0x6ef8:case 0x6f12:case 0x6f2c:case 0x6f46:case 0x6f60:case 0x6f7a:case 0x6f94:case 0x6fae:case 0x6fc8:case 0x6fe2:
    case 0x6ffc:case 0x7016:case 0x7030:case 0x704a:case 0x7064:case 0x707e:case 0x7098:case 0x70b2:case 0x70cc:case 0x70e6:case 0x7100:case 0x711a:
    case 0x7134:case 0x714e:case 0x7168:case 0x7182:case 0x7188:case 0x7194:case 0x71d8:case 0x71fe:case 0x7252:case 0x727e:case 0x7282:case 0x7286:
    case 0x728a:case 0x72aa:case 0x72ae:case 0x72b2:
    // Frame head H4 (F5) blocks: the 8 BRA.W slots of the reverse writer table 11792..117ae and the 32 BRA.W cell table entries of
    // each of the 8 reverse writer routines. H4 has no carry consumer and no known-carry producer (every BCS/BCC/BLE/BMI reads flags
    // made in its own block); every other block (MOVE/MOVEQ/SWAP/ADD/SUB/CMP/AND/EOR/NEG/LSL/LSR/ASR/CLR/MULS, MOVE.L Dn,(A6)) stays Unknown.
    case 0x11792:case 0x11796:case 0x1179a:case 0x1179e:case 0x117a2:case 0x117a6:case 0x117aa:case 0x117ae:case 0x118a2:case 0x118a6:
    case 0x118aa:case 0x118ae:case 0x118b2:case 0x118b6:case 0x118ba:case 0x118be:case 0x118c2:case 0x118c6:case 0x118ca:case 0x118ce:
    case 0x118d2:case 0x118d6:case 0x118da:case 0x118de:case 0x118e2:case 0x118e6:case 0x118ea:case 0x118ee:case 0x118f2:case 0x118f6:
    case 0x118fa:case 0x118fe:case 0x11902:case 0x11906:case 0x1190a:case 0x1190e:case 0x11912:case 0x11916:case 0x1191a:case 0x1191e:
    case 0x11c70:case 0x11c74:case 0x11c78:case 0x11c7c:case 0x11c80:case 0x11c84:case 0x11c88:case 0x11c8c:case 0x11c90:case 0x11c94:
    case 0x11c98:case 0x11c9c:case 0x11ca0:case 0x11ca4:case 0x11ca8:case 0x11cac:case 0x11cb0:case 0x11cb4:case 0x11cb8:case 0x11cbc:
    case 0x11cc0:case 0x11cc4:case 0x11cc8:case 0x11ccc:case 0x11cd0:case 0x11cd4:case 0x11cd8:case 0x11cdc:case 0x11ce0:case 0x11ce4:
    case 0x11ce8:case 0x11cec:case 0x12040:case 0x12044:case 0x12048:case 0x1204c:case 0x12050:case 0x12054:case 0x12058:case 0x1205c:
    case 0x12060:case 0x12064:case 0x12068:case 0x1206c:case 0x12070:case 0x12074:case 0x12078:case 0x1207c:case 0x12080:case 0x12084:
    case 0x12088:case 0x1208c:case 0x12090:case 0x12094:case 0x12098:case 0x1209c:case 0x120a0:case 0x120a4:case 0x120a8:case 0x120ac:
    case 0x120b0:case 0x120b4:case 0x120b8:case 0x120bc:case 0x12412:case 0x12416:case 0x1241a:case 0x1241e:case 0x12422:case 0x12426:
    case 0x1242a:case 0x1242e:case 0x12432:case 0x12436:case 0x1243a:case 0x1243e:case 0x12442:case 0x12446:case 0x1244a:case 0x1244e:
    case 0x12452:case 0x12456:case 0x1245a:case 0x1245e:case 0x12462:case 0x12466:case 0x1246a:case 0x1246e:case 0x12472:case 0x12476:
    case 0x1247a:case 0x1247e:case 0x12482:case 0x12486:case 0x1248a:case 0x1248e:case 0x12804:case 0x12808:case 0x1280c:case 0x12810:
    case 0x12814:case 0x12818:case 0x1281c:case 0x12820:case 0x12824:case 0x12828:case 0x1282c:case 0x12830:case 0x12834:case 0x12838:
    case 0x1283c:case 0x12840:case 0x12844:case 0x12848:case 0x1284c:case 0x12850:case 0x12854:case 0x12858:case 0x1285c:case 0x12860:
    case 0x12864:case 0x12868:case 0x1286c:case 0x12870:case 0x12874:case 0x12878:case 0x1287c:case 0x12880:case 0x12d16:case 0x12d1a:
    case 0x12d1e:case 0x12d22:case 0x12d26:case 0x12d2a:case 0x12d2e:case 0x12d32:case 0x12d36:case 0x12d3a:case 0x12d3e:case 0x12d42:
    case 0x12d46:case 0x12d4a:case 0x12d4e:case 0x12d52:case 0x12d56:case 0x12d5a:case 0x12d5e:case 0x12d62:case 0x12d66:case 0x12d6a:
    case 0x12d6e:case 0x12d72:case 0x12d76:case 0x12d7a:case 0x12d7e:case 0x12d82:case 0x12d86:case 0x12d8a:case 0x12d8e:case 0x12d92:
    case 0x13228:case 0x1322c:case 0x13230:case 0x13234:case 0x13238:case 0x1323c:case 0x13240:case 0x13244:case 0x13248:case 0x1324c:
    case 0x13250:case 0x13254:case 0x13258:case 0x1325c:case 0x13260:case 0x13264:case 0x13268:case 0x1326c:case 0x13270:case 0x13274:
    case 0x13278:case 0x1327c:case 0x13280:case 0x13284:case 0x13288:case 0x1328c:case 0x13290:case 0x13294:case 0x13298:case 0x1329c:
    case 0x132a0:case 0x132a4:case 0x13746:case 0x1374a:case 0x1374e:case 0x13752:case 0x13756:case 0x1375a:case 0x1375e:case 0x13762:
    case 0x13766:case 0x1376a:case 0x1376e:case 0x13772:case 0x13776:case 0x1377a:case 0x1377e:case 0x13782:case 0x13786:case 0x1378a:
    case 0x1378e:case 0x13792:case 0x13796:case 0x1379a:case 0x1379e:case 0x137a2:case 0x137a6:case 0x137aa:case 0x137ae:case 0x137b2:
    case 0x137b6:case 0x137ba:case 0x137be:case 0x137c2:
    // Objects N35 (F4) blocks: JSR/JMP/RTS 4c728 4cf52 4cf5c 4cf62 ea680 ea68a and the 2 consumers 4cf58 (C returned by 288c), ea686
    // (1abda). N35 has no known C producer; the other blocks stay Unknown.
    case 0x4c728:case 0x4cf52:case 0x4cf58:case 0x4cf5c:case 0x4cf62:case 0xea680:case 0xea686:case 0xea68a:
    // F5 frame head H2: 46 FLOW_ONLY blocks (only LEA / JSR / BSR / BRA / JMP / RTS / Bcc / DBRA and the Z-only BTST / BSET / BCLR).
    case 0x334c:case 0x3360:case 0x3364:case 0x3368:case 0x3404:case 0x349a:case 0x350e:case 0x3904:case 0x3910:case 0x3912:
    case 0x3916:case 0x90b6:case 0x90ba:case 0x90c4:case 0x90dc:case 0x90ea:case 0x90f8:case 0x9106:case 0x910a:case 0x9122:
    case 0x9126:case 0x9130:case 0x9134:case 0x9154:case 0x9168:case 0x9172:case 0x9184:case 0x91cc:case 0x91d0:case 0x91da:
    case 0x91ea:case 0x91f4:case 0x91fe:case 0x9208:case 0x9218:case 0x9222:case 0x922c:case 0x924c:case 0x9250:case 0x928a:
    case 0x928e:case 0x92ce:case 0x92ec:case 0x92fc:case 0x9326:case 0x933e:
    // Objects N34 (F4) FLOW_ONLY blocks: BSR/JSR/BRA/RTS, LEA+JSR, MOVEM.L -(A7)+LEA+JSR, BTST (Z only)+BEQ and the BMI 4c49c (N of
    // 4c48e SUB.W recomputed from D0.W; unique predecessor). N34 has no consumer of a callee C and no known C producer.
    case 0x4c44a:case 0x4c488:case 0x4c49c:case 0x4c4ac:case 0x4c4ba:case 0x4c576:case 0x4c65e:case 0x4c686:case 0x4c6a2:case 0x4c83c:
    case 0x4c840:case 0x4c844:case 0x4c8ac:case 0x4c90e:case 0x4c9ee:case 0x4c9f8:case 0x4cacc:case 0x4cb3e:case 0x4cc2e:case 0x4cc38:
    case 0x4cd9e:case 0x4cda4:case 0x4cda8:case 0x4cdae:case 0x4ce1e:case 0x4ce70:case 0x4cf30:
    // Frame head H8 (F5) blocks: the 8 BRA.W slots of the forward writer table ce62..ce7e and the 32 BRA.W cell table entries of
    // each of the 8 forward writer routines. H8 has no carry consumer and no known-carry producer (every BCS/BCC/BPL/BMI reads flags
    // made in its own block); every other block (MOVE/MOVEQ/SWAP/ADD/ADDQ/SUB/CMP/AND/EOR/NEG/LSL/LSR/ASR/CLR/MULS, MOVE.L Dn,(A6))
    // stays Unknown.
    case 0xce62:case 0xce66:case 0xce6a:case 0xce6e:case 0xce72:case 0xce76:case 0xce7a:case 0xce7e:case 0xcf72:case 0xcf76:
    case 0xcf7a:case 0xcf7e:case 0xcf82:case 0xcf86:case 0xcf8a:case 0xcf8e:case 0xcf92:case 0xcf96:case 0xcf9a:case 0xcf9e:
    case 0xcfa2:case 0xcfa6:case 0xcfaa:case 0xcfae:case 0xcfb2:case 0xcfb6:case 0xcfba:case 0xcfbe:case 0xcfc2:case 0xcfc6:
    case 0xcfca:case 0xcfce:case 0xcfd2:case 0xcfd6:case 0xcfda:case 0xcfde:case 0xcfe2:case 0xcfe6:case 0xcfea:case 0xcfee:
    case 0xd342:case 0xd346:case 0xd34a:case 0xd34e:case 0xd352:case 0xd356:case 0xd35a:case 0xd35e:case 0xd362:case 0xd366:
    case 0xd36a:case 0xd36e:case 0xd372:case 0xd376:case 0xd37a:case 0xd37e:case 0xd382:case 0xd386:case 0xd38a:case 0xd38e:
    case 0xd392:case 0xd396:case 0xd39a:case 0xd39e:case 0xd3a2:case 0xd3a6:case 0xd3aa:case 0xd3ae:case 0xd3b2:case 0xd3b6:
    case 0xd3ba:case 0xd3be:case 0xd714:case 0xd718:case 0xd71c:case 0xd720:case 0xd724:case 0xd728:case 0xd72c:case 0xd730:
    case 0xd734:case 0xd738:case 0xd73c:case 0xd740:case 0xd744:case 0xd748:case 0xd74c:case 0xd750:case 0xd754:case 0xd758:
    case 0xd75c:case 0xd760:case 0xd764:case 0xd768:case 0xd76c:case 0xd770:case 0xd774:case 0xd778:case 0xd77c:case 0xd780:
    case 0xd784:case 0xd788:case 0xd78c:case 0xd790:case 0xdae8:case 0xdaec:case 0xdaf0:case 0xdaf4:case 0xdaf8:case 0xdafc:
    case 0xdb00:case 0xdb04:case 0xdb08:case 0xdb0c:case 0xdb10:case 0xdb14:case 0xdb18:case 0xdb1c:case 0xdb20:case 0xdb24:
    case 0xdb28:case 0xdb2c:case 0xdb30:case 0xdb34:case 0xdb38:case 0xdb3c:case 0xdb40:case 0xdb44:case 0xdb48:case 0xdb4c:
    case 0xdb50:case 0xdb54:case 0xdb58:case 0xdb5c:case 0xdb60:case 0xdb64:case 0xdedc:case 0xdee0:case 0xdee4:case 0xdee8:
    case 0xdeec:case 0xdef0:case 0xdef4:case 0xdef8:case 0xdefc:case 0xdf00:case 0xdf04:case 0xdf08:case 0xdf0c:case 0xdf10:
    case 0xdf14:case 0xdf18:case 0xdf1c:case 0xdf20:case 0xdf24:case 0xdf28:case 0xdf2c:case 0xdf30:case 0xdf34:case 0xdf38:
    case 0xdf3c:case 0xdf40:case 0xdf44:case 0xdf48:case 0xdf4c:case 0xdf50:case 0xdf54:case 0xdf58:case 0xe3f0:case 0xe3f4:
    case 0xe3f8:case 0xe3fc:case 0xe400:case 0xe404:case 0xe408:case 0xe40c:case 0xe410:case 0xe414:case 0xe418:case 0xe41c:
    case 0xe420:case 0xe424:case 0xe428:case 0xe42c:case 0xe430:case 0xe434:case 0xe438:case 0xe43c:case 0xe440:case 0xe444:
    case 0xe448:case 0xe44c:case 0xe450:case 0xe454:case 0xe458:case 0xe45c:case 0xe460:case 0xe464:case 0xe468:case 0xe46c:
    case 0xe904:case 0xe908:case 0xe90c:case 0xe910:case 0xe914:case 0xe918:case 0xe91c:case 0xe920:case 0xe924:case 0xe928:
    case 0xe92c:case 0xe930:case 0xe934:case 0xe938:case 0xe93c:case 0xe940:case 0xe944:case 0xe948:case 0xe94c:case 0xe950:
    case 0xe954:case 0xe958:case 0xe95c:case 0xe960:case 0xe964:case 0xe968:case 0xe96c:case 0xe970:case 0xe974:case 0xe978:
    case 0xe97c:case 0xe980:case 0xee24:case 0xee28:case 0xee2c:case 0xee30:case 0xee34:case 0xee38:case 0xee3c:case 0xee40:
    case 0xee44:case 0xee48:case 0xee4c:case 0xee50:case 0xee54:case 0xee58:case 0xee5c:case 0xee60:case 0xee64:case 0xee68:
    case 0xee6c:case 0xee70:case 0xee74:case 0xee78:case 0xee7c:case 0xee80:case 0xee84:case 0xee88:case 0xee8c:case 0xee90:
    case 0xee94:case 0xee98:case 0xee9c:case 0xeea0:
    // F6a IRQ shell FLOW_ONLY blocks (contract carry section: JMP/JSR/BSR/BRA/RTS, LEA/MOVEA, BTST/BSET/BCLR (Z only)+Bcc) and the clear run
    // RTS 1669e (n = 0 entry). F6a consumes no incoming C; 16e92 (Set), 16e9e (Clear) and the RTE blocks 248 2b6 2ce (popped SR bit 0)
    // produce a known C inside their block; every other block stays Unknown.
    case 0x21e:case 0x23c:case 0x242:case 0xa4c:case 0xa72:case 0xaba:case 0xacc:case 0xb06:case 0xb0a:case 0xbc8:case 0xbec:
    case 0xc8c:case 0xc96:case 0xcb0:case 0xcbe:case 0xcc4:case 0xcd6:case 0xcdc:case 0xce2:case 0xd2a:case 0xd36:case 0xd48:
    case 0x3cac:case 0x3cde:case 0x3ce0:case 0x3d06:case 0x3dcc:case 0x16cfa:case 0x16d52:case 0x16d66:case 0x16d84:case 0x16e0c:
    case 0x16e22:case 0x16e40:case 0x187d8:case 0x187e2:case 0x18be6:case 0x1ae1a:case 0x1ae26:case 0x1ae32:case 0x4817e:case 0x1669e:
    // Objects B2b blocks: the consumers 4d438 (BCC, C returned by 289e) 3a4ec (BCC, 4d6b4) 3ad26 (BCS, 288c) 3ad3c (BCC, 49fc6) 38d70 (SCC,
    // 28ae) 38dbe (BCC, 3b334) and the blocks that return the C of the path that reached them unchanged: the RTS blocks 33950 3a4ce (Clear set by
    // the TST of 33948 / 3a4c6) 4d506 (Set or Clear from 4d4e0 / 4d4e8 / 4d502), 3b448 (BTST + BEQ) / 3b456 (Clear of 3b42e) and 4eeea (MOVEM + RTS).
    case 0x4d438:case 0x3a4ec:case 0x3ad26:case 0x3ad3c:case 0x38d70:case 0x38dbe:case 0x33950:case 0x3a4ce:case 0x4d506:
    case 0x3b448:case 0x3b456:case 0x4eeea:
    // Controller C1 (F5) FLOW blocks (43): JSR/BSR/JMP/BRA/RTS, LEA/MOVEA/ADDQ.W #1,An/ADDA.W Dn,An, BTST/BSET Dn (Z only) and the
    // conditional branches. c4a0 c674 c67e c806 c996 c9ba are the BCC/BCS consumers of the C returned by ca32, 289e, 314c, 30bc and 30d4;
    // 30c8 30e0 3156 (ORI CCR) and 30ce 30e6 315c (ANDI CCR) set their known C in their own block and ca32 (CMPI) sets it for c4a0.
    // 4a9d0 4a9da (BEQ) read the Z of the TST.B (A0) that ended 4a974 and recompute it from BYTE (A0). MOVE/MOVEQ/CMP/CMPI/TST/SUBQ/
    // SUBI/ADDQ.B/SBCD/CLR/LSR/ANDI/ADD.W blocks and the stack MOVEs stay Unknown.
    case 0x30bc:case 0x30d4:case 0x3680:case 0x36b8:case 0x36ba:case 0x36d2:case 0x36fc:case 0x3706:case 0xc49c:case 0xc4a0:
    case 0xc4a4:case 0xc4b6:case 0xc654:case 0xc66a:case 0xc674:case 0xc678:case 0xc67e:case 0xc682:case 0xc736:case 0xc73a:
    case 0xc748:case 0xc7fc:case 0xc806:case 0xc80a:case 0xc990:case 0xc996:case 0xc9b4:case 0xc9ba:case 0xc9be:case 0xca20:
    case 0x4a896:case 0x4a8ac:case 0x4a8da:case 0x4a94c:case 0x4a962:case 0x4a972:case 0x4a9ae:case 0x4a9c4:case 0x4a9d0:case 0x4a9d4:
    case 0x4a9da:case 0x4a9de:case 0x4a9e0:
    // Objects B2a blocks: the 16 consumers 5ef6c 5f5e6 5f744 (BCC, C returned by the boundary 4b6f4) 5ef80 5efda (BCC, 1ab02) 5efc6 (BCC, 49fc6)
    // 5f6c2 60880 (BCC, 4b54e) 5f702 6062e 606f4 6077e 6085e 60902 (BCC, 28ae) 60828 608cc (MOVEM.W + BCC, 2986) and the five RTS blocks that return
    // the C of the path that reached them unchanged. The ORI.B #1,CCR blocks set a known Set inside the block; every other block stays Unknown.
    case 0x5ef6c:case 0x5f5e6:case 0x5f744:case 0x5ef80:case 0x5efda:case 0x5efc6:case 0x5f6c2:case 0x60880:case 0x5f702:case 0x6062e:
    case 0x606f4:case 0x6077e:case 0x6085e:case 0x60902:case 0x60828:case 0x608cc:case 0x5ef8a:case 0x5efe4:case 0x5f5f0:case 0x5f75e:
    case 0x60938:
    // BTST/BEQ changes only Z; its known memory test is already modeled.
    // F6b palette transfer FLOW blocks outside the cell range: 7302 BCLR+BEQ, 8738 RTS, 8b60 BRA (contract carry section).
    case 0x7302:case 0x8738:case 0x8b60:
    case 0x3b82:return true;
    // Objects B1b (deferred N22b/N19b) blocks: JSR/BSR/JMP/BRA/RTS, LEA/MOVEA+JSR, BTST/BSET/BCLR (Z only, +Bcc), MOVEM, SCC and the 9
    // BCC/BCS/SCC consumers 3d40a (C returned by 28ae), 3d478 (3dcf2), 3dbae 3e2ec (49fc6), 3dbca (3dcac -> 4d418), 3e2dc (288c), b16c2
    // (b15e0), b1cb4 (28ae); 3dac2 (BNE) is recomputed from BYTE a4(A6). b1cc2 (ORI CCR) sets a known C. The other blocks stay Unknown.
    case 0x3d40a:case 0x3d422:case 0x3d426:case 0x3d432:case 0x3d470:case 0x3d474:case 0x3d478:case 0x3d47c:case 0x3d494:case 0x3d4e2:
    case 0x3d4e6:case 0x3d4ea:case 0x3d7e8:case 0x3d7ec:case 0x3d7f4:case 0x3d7fc:case 0x3d812:case 0x3d816:case 0x3d81a:case 0x3d880:
    case 0x3d884:case 0x3d888:case 0x3d88c:case 0x3d8a8:case 0x3d8ac:case 0x3d8b0:case 0x3d8b4:case 0x3d8b8:case 0x3d8bc:case 0x3d8c0:
    case 0x3d8c4:case 0x3d8c8:case 0x3d8da:case 0x3d8de:case 0x3d8f4:case 0x3d97e:case 0x3da72:case 0x3da7e:case 0x3da82:case 0x3da98:
    case 0x3da9c:case 0x3daa0:case 0x3daae:case 0x3dab2:case 0x3dac2:case 0x3dacc:case 0x3dad0:case 0x3daee:case 0x3db5c:case 0x3dba2:
    case 0x3dba8:case 0x3dbae:case 0x3dbb2:case 0x3dbb8:case 0x3dbbe:case 0x3dbc2:case 0x3dbc6:case 0x3dbca:case 0x3dc04:case 0x3dc20:
    case 0x3dcc8:case 0x3dcd4:case 0x3dcea:case 0x3dcec:case 0x3dd0e:case 0x3dd1e:case 0x3dd2e:case 0x3def0:case 0x3e03e:case 0x3e06e:
    case 0x3e0a6:case 0x3e0a8:case 0x3e2d6:case 0x3e2dc:case 0x3e2e0:case 0x3e2e6:case 0x3e2ec:case 0x3e2f0:case 0xb1656:case 0xb165a:
    case 0xb16a4:case 0xb16c2:case 0xb16c6:case 0xb16cc:case 0xb16d0:case 0xb16d4:case 0xb16e6:case 0xb1cb4:case 0xb1cc2:case 0xb1cc6:
    case 0xb1cca:case 0xb1cf6:case 0xb1d8c:return true;
    default:return false;
    }
}
// The eight F3b TRAP #15 sites are boundaries without an executor (F3 main decision 4).
bool stage_event_ops_trap(std::uint32_t pc) {
    return pc==0xe93d8 || pc==0xe9528 || pc==0xe9530 || pc==0xe957a || pc==0xe96d4 || pc==0xe9702 || pc==0xe9780 || pc==0xe9788;
}
std::uint32_t pvc_word(const AnimationMachineDevice& device,unsigned int index) {
    return (static_cast<std::uint32_t>(device.pvc[index*2])<<8)|device.pvc[index*2+1];
}
void pvc_put(AnimationMachineDevice& device,unsigned int index,std::uint32_t value) {
    device.pvc[index*2]=static_cast<std::uint8_t>(value>>8);
    device.pvc[index*2+1]=static_cast<std::uint8_t>(value);
}
// Device equations follow the pinned MAME PVC reference. See
// tools/licenses/mame-pvc.txt (BSD-3-Clause), S. Smith, David Haywood, Fabio Priuli.
void pvc_effects(AnimationMachineDevice& device,unsigned int index) {
    if (index==0xff0) {
        const std::uint32_t pen=pvc_word(device,0xff0);
        const std::uint32_t blue=((pen&15U)<<1)|((pen>>12)&1U);
        const std::uint32_t green=((pen&0xf0U)>>3)|((pen>>13)&1U);
        const std::uint32_t red=((pen&0xf00U)>>7)|((pen>>14)&1U);
        pvc_put(device,0xff1,(green<<8)|blue);
        pvc_put(device,0xff2,((pen>>15)<<8)|red);
    } else if (index==0xff4 || index==0xff5) {
        const std::uint32_t gb=pvc_word(device,0xff4),sr=pvc_word(device,0xff5);
        pvc_put(device,0xff6,((gb&0x1eU)>>1)|((gb&0x1e00U)>>5)|((sr&0x1eU)<<7)|
            ((gb&1U)<<12)|((gb&0x100U)<<5)|((sr&1U)<<14)|((sr&0x100U)<<7));
    }
    if (index>=0xff8) {
        const std::uint32_t ff8=pvc_word(device,0xff8),ff9=pvc_word(device,0xff9);
        device.bank_base=0x100000U+((ff8>>8)|(ff9<<8));
        pvc_put(device,0xff8,(ff8&0xfe00U)|0xa0U);
        pvc_put(device,0xff9,ff9&0x7fffU);
    }
}
}
bool am_write(AnimationMachineContext& c,std::uint32_t logical,unsigned int size,std::uint32_t value) {
    if ((size!=1 && size!=2 && size!=4) || (size>1 && (logical&1U)))
        return am_error(c,"invalid animation machine write size/alignment");
    const unsigned int unit=size==1?1:2;
    // The public invocation owns rollback across all units and device effects.
    for (unsigned int offset=0;offset<size;offset+=unit) {
        const std::uint32_t address=(logical+offset)&0xffffffU;
        const std::uint32_t part=(value>>(8*(size-offset-unit)))&(unit==1?255U:65535U);
        if (address>=0x100000U && address<0x200000U) {
            if (!write_program_bus_ram(c.ram,logical+offset,unit,part,c.error))return false;
        } else if (address>=0x2fe000U && address<0x300000U) {
            const unsigned int at=address-0x2fe000U;
            for (unsigned int i=0;i<unit;++i)c.device.pvc[at+i]=static_cast<std::uint8_t>(part>>(8*(unit-i-1)));
            VideoPortWrite port;port.address=address;port.size=static_cast<std::uint8_t>(unit);port.value=part;
            c.ports.push_back(port);pvc_effects(c.device,at/2);
        } else if (c.palette!=0 && address>=0x400000U && address<0x800000U) {
            // Palette RAM mirror (E6), not a port; without an attached palette device this stays the device error below.
            std::vector<std::uint8_t>& bank=c.palette->banks[c.palette->selected];
            for (unsigned int i=0;i<unit;++i)bank[(address+i)&0x1fffU]=static_cast<std::uint8_t>(part>>(8*(unit-i-1)));
        } else return am_error(c,"unsupported animation machine write device");
    }
    c.bus.bank_base=c.device.bank_base;return true;
}
bool am_fetch(AnimationMachineContext& c,unsigned int size,std::uint32_t& value) {
    if (!am_read(c,c.s.a[1],size,value))return false;
    c.s.a[1]+=size;return true;
}
bool am_push(AnimationMachineContext& c,unsigned int size,std::uint32_t value) {
    return push_program_stack(c.ram,c.s.a[7],size,value,c.error);
}
bool am_pop(AnimationMachineContext& c,unsigned int size,std::uint32_t& value) {
    c.bus.bank_base=c.device.bank_base;
    return pop_program_stack(c.ram,c.windows,c.bus,c.s.a[7],size,value,c.error);
}
bool am_call(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc) {
    if (!am_push(c,4,return_pc))return false;c.s.pc=target;return true;
}
bool am_return(AnimationMachineContext& c) {
    std::uint32_t target=0;if (!am_pop(c,4,target))return false;c.s.pc=target;return true;
}
bool am_zero_bank(AnimationMachineContext& c) {
    return am_write(c,c.s.a[5]-0x7ff0U,2,0) && am_write(c,0x2ffff2,2,0x1000) && am_write(c,0x2ffff0,2,0);
}
namespace {
// Shared implementation of run_animation_machine (palette null) and run_animation_machine_with_palette (validated palette).
bool run_machine(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,const ProgramBusState& resources,
    AnimationMachineState& state,AnimationMachineDevice& device,AnimationMachinePaletteRam* palette,
    std::uint32_t stop_pc,std::uint8_t external_status,std::uint32_t& external_reads,
    AnimationMachineStatus& status,std::vector<VideoPortWrite>& ports,std::string& error) {
    if (ram.size()!=65536 || device.pvc.size()!=8192 || (stop_pc&1U)) {
        error="invalid animation machine RAM/PVC/stop PC";return false;
    }
    if (state.carry!=AnimationCarryUnknown && state.carry!=AnimationCarryClear && state.carry!=AnimationCarrySet) {
        error="invalid animation machine carry state";return false;
    }
    try {
        std::vector<std::uint8_t> next_ram=ram;
        AnimationMachineState next=state;AnimationMachineDevice next_device=device;
        std::vector<VideoPortWrite> next_ports;
        AnimationMachineContext c(next_ram,windows,resources,next,next_device,next_ports,external_status,error);
        AnimationMachinePaletteRam next_palette;
        if (palette!=0) {next_palette=*palette;c.palette=&next_palette;}
        AnimationMachineStatus result=AnimationMachineReturned;bool stopped=false;
        // A legitimate 65536-column WORD loop exceeds the former 100000-block cap.
        // Keep a finite limit; malformed record walks and huge transfers still fail atomically.
        for (unsigned int steps=0;steps<1000000;++steps) {
            if (next.pc==stop_pc) {stopped=true;break;}
            if (next.pc&1U)return am_error(c,"unaligned animation machine PC");
            if (!carry_preserving_pc(next.pc))next.carry=AnimationCarryUnknown;
            bool ok=false;
            if ((next.pc>=0x3ac8 && next.pc<0x3c08) || (next.pc>=0x47672 && next.pc<0x476bc) ||
                (next.pc>=0xca70 && next.pc<0xca76))ok=animation_sound_block(c);
            else if ((next.pc>=0xcd50 && next.pc<0xce02) || next.pc==0x16ea4 || next.pc==0x16ed2)ok=animation_sprite_block(c);
            else if (next.pc==0x47d20 || next.pc==0x47d3e || next.pc==0x47d42 ||
                (next.pc>=0x4847c && next.pc<0x484b4) || (next.pc>=0x1bdde && next.pc<0x1be3a) ||
                (next.pc>=0x289e && next.pc<0x28ae) || (next.pc>=0x4dee2 && next.pc<0x4df1a) ||
                (next.pc>=0x4e166 && next.pc<0x4e186))ok=animation_readiness_block(c);
            else if ((next.pc>=0x47c6c && next.pc<0x47cae) || (next.pc>=0x4843c && next.pc<=0x4847a) ||
                (next.pc>=0x4e286 && next.pc<=0x4e330) || (next.pc>=0x8cda && next.pc<=0x8d32) ||
                (next.pc>=0x35f0 && next.pc<=0x3628))ok=animation_hud_block(c);
            else if ((next.pc>=0x47d24 && next.pc<0x47da4) || next.pc==0x477ac || next.pc==0x477bc ||
                (next.pc>=0x4e216 && next.pc<=0x4e24c) || (next.pc>=0xbee && next.pc<=0xc34) ||
                (next.pc>=0x35a2 && next.pc<=0x35ee))ok=animation_transition_block(c);
            else if ((next.pc>=0x47eac && next.pc<0x47fca && next.pc!=0x47f04) || next.pc==0x47c5a ||
                (next.pc>=0x1c63c && next.pc<0x1c676) || (next.pc>=0x48398 && next.pc<=0x483a8) ||
                (next.pc>=0x30f4 && next.pc<=0x3102) || next.pc==0x3c84 || next.pc==0x3c88 ||
                next.pc==0x3d44 || next.pc==0x3d48 || next.pc==0x3d4c || next.pc==0x4e24e || next.pc==0x4e252 ||
                next.pc==0xca7e || next.pc==0xca82 || next.pc==0x8c16 || next.pc==0x8ca4 || next.pc==0x8cc8)ok=animation_exit_block(c);
            else if ((next.pc>=0x271c && next.pc<=0x278e) || next.pc==0x287e || next.pc==0x288a ||
                (next.pc>=0x299c && next.pc<=0x29fe) || (next.pc>=0x2a0a && next.pc<=0x2aaa) ||
                (next.pc>=0x8ff4 && next.pc<=0x9036) || next.pc==0x8e4a || next.pc==0x8e80 ||
                next.pc==0x8eb6 || next.pc==0x8ebc || (next.pc>=0x43dcc && next.pc<=0x43ea2) ||
                (next.pc>=0xc3dc && next.pc<=0xc400) || next.pc==0x4aa06 || next.pc==0x4aa2e ||
                next.pc==0xe90ca || next.pc==0xe90d6 || next.pc==0x46eec || next.pc==0x46ef2 ||
                next.pc==0x46ef4 || next.pc==0x46f08 || next.pc==0x46f26 || next.pc==0x46f2c ||
                next.pc==0x8bbc || next.pc==0x8bc0 || next.pc==0x3dce || next.pc==0x3de4 ||
                (next.pc>=0x477c2 && next.pc<=0x477e2) || next.pc==0x47fe4)ok=animation_cleanup_block(c);
            else if ((next.pc>=0xca9e && next.pc<=0xcb62) || next.pc==0x47fca || next.pc==0x47fd0 || next.pc==0x47fdc)ok=animation_screen_block(c);
            else if (next.pc==0x47fe8 || next.pc==0x47fec || (next.pc>=0x43efa && next.pc<=0x4411c) ||
                (next.pc>=0xccd6 && next.pc<=0xcd48) || (next.pc>=0x1ad9a && next.pc<=0x1adf2) ||
                (next.pc>=0x16f9a && next.pc<=0x16faa) || (next.pc>=0x1829a && next.pc<=0x1831a) ||
                next.pc==0x1701a || next.pc==0x17028 || next.pc==0x1704a || next.pc==0x1724a)ok=animation_scene_block(c);
            else if ((next.pc>=0x8da2 && next.pc<=0x8e48) || (next.pc>=0x8e82 && next.pc<=0x8eb4) ||
                (next.pc>=0xe7bf4 && next.pc<=0xe7c10) || (next.pc>=0xe7c36 && next.pc<=0xe7c3e) ||
                (next.pc>=0x47ff2 && next.pc<0x48042) || (next.pc>=0x16fac && next.pc<=0x16fec) ||
                (next.pc>=0x16ff8 && next.pc<=0x17010))ok=animation_palette_bind_block(c);
            else if ((next.pc>=0x16f0e && next.pc<=0x16f98) || (next.pc>=0x183c6 && next.pc<=0x184ce) ||
                (next.pc>=0x18530 && next.pc<=0x185f8) || (next.pc>=0x1861a && next.pc<=0x18654) ||
                (next.pc>=0x18702 && next.pc<=0x1879a) || next.pc==0x48042 || next.pc==0x48048 ||
                next.pc==0x17012 || next.pc==0x17018)ok=animation_map_transfer_block(c);
            else if ((next.pc>=0x49f8c && next.pc<0x4a46c) || next.pc==0x3679e ||
                next.pc==0x47cec || next.pc==0x47d0a || next.pc==0x47d10 ||
                next.pc==0x47d14 || next.pc==0x47d1a || next.pc==0x47f04 ||
                next.pc==0x47cae || next.pc==0x47cc0 || next.pc==0x47cc6 || next.pc==0x47cca || next.pc==0x47ce6 ||
                next.pc==0x1dc84 || next.pc==0x1dc8a || next.pc==0x210ae || next.pc==0x210b4 ||
                (next.pc>=0x2b3e8 && next.pc<0x2b40c))ok=animation_interpreter_block(c);
            else if ((next.pc>=0x4804e && next.pc<=0x480b6) || (next.pc>=0xc364 && next.pc<=0xc3be) ||
                (next.pc>=0x28ae && next.pc<=0x2916) || next.pc==0x2a00 || next.pc==0x2a02 || next.pc==0x2a06 ||
                (next.pc>=0x2ab8 && next.pc<=0x2ac6))ok=animation_fade_card_block(c);
            else if ((next.pc>=0xc250 && next.pc<=0xc2a2) || (next.pc>=0xde424 && next.pc<=0xde48a) ||
                (next.pc>=0xe7c16 && next.pc<=0xe7c30))ok=animation_card_child_block(c);
            else if ((next.pc>=0xa0a0 && next.pc<=0xa1e0) || (next.pc>=0xa29c && next.pc<=0xa2bc) ||
                (next.pc>=0x386e && next.pc<=0x38fe && next.pc!=0x38c8 && next.pc!=0x38e2) ||
                (next.pc>=0xc2a8 && next.pc<=0xc2ba))ok=animation_card_menu_block(c);
            else if ((next.pc>=0x3650 && next.pc<=0x366e) || (next.pc>=0x3918 && next.pc<=0x392a) ||
                (next.pc>=0x9b26 && next.pc<=0x9e92) || (next.pc>=0x9f7c && next.pc<=0x9fc2) ||
                (next.pc>=0xa008 && next.pc<=0xa07e) || (next.pc>=0xa216 && next.pc<=0xa27e) ||
                (next.pc>=0xa348 && next.pc<=0xa404) || (next.pc>=0xa5d2 && next.pc<=0xa660 && next.pc!=0xa63c) ||
                (next.pc>=0xa73e && next.pc<=0xa758) || (next.pc>=0xbf94 && next.pc<=0xbfbc) ||
                (next.pc>=0xc1c4 && next.pc<=0xc212) || (next.pc>=0xc2c0 && next.pc<=0xc2c6) ||
                (next.pc>=0xe84c8 && next.pc<=0xe84d0))ok=animation_card_menu_open_block(c);
            else if ((next.pc>=0x9fc4 && next.pc<=0x9fcc) || (next.pc>=0x9ff4 && next.pc<=0x9ffc) ||
                (next.pc>=0xa1ee && next.pc<=0xa1f8) || (next.pc>=0xa406 && next.pc<=0xa5d0) ||
                (next.pc>=0xa70a && next.pc<=0xa718) || (next.pc>=0xbf2c && next.pc<=0xbf92))ok=animation_card_menu_input_block(c);
            else if ((next.pc>=0x9e94 && next.pc<=0x9ee4) || (next.pc>=0xa2be && next.pc<=0xa346) ||
                (next.pc>=0xa662 && next.pc<=0xa696) || (next.pc>=0xc2c8 && next.pc<=0xc2f8))ok=animation_card_menu_close_block(c);
            else if ((next.pc>=0x9f36 && next.pc<=0x9f76) || (next.pc>=0xa71a && next.pc<=0xa72a) ||
                (next.pc>=0xbb74 && next.pc<=0xbb8c) || (next.pc>=0xbbb8 && next.pc<=0xbbd2) ||
                (next.pc>=0xbd26 && next.pc<=0xbd92) || (next.pc>=0xbe0c && next.pc<=0xbe38))ok=animation_card_menu_save_block(c);
            else if (next.pc>=0xa698 && next.pc<=0xa708)ok=animation_card_menu_nested_block(c);
            else if ((next.pc>=0x480bc && next.pc<=0x480f0) || (next.pc>=0x47642 && next.pc<=0x47670) ||
                next.pc==0x6f1c2 || (next.pc>=0x2efa6 && next.pc<=0x2efda) || (next.pc>=0x3c44 && next.pc<=0x3c7a) ||
                (next.pc>=0xb4a2a && next.pc<=0xb4aae) || (next.pc>=0x49392 && next.pc<=0x493ba && next.pc!=0x4939c) ||
                (next.pc>=0x1c028 && next.pc<=0x1c050) || (next.pc>=0x4d9d6 && next.pc<=0x4da06) ||
                (next.pc>=0xb481e && next.pc<=0xb484e) || (next.pc>=0x46f52 && next.pc<=0x4706a))ok=animation_frame_helpers_block(c);
            else if ((next.pc>=0x197da && next.pc<0x19812) || (next.pc>=0x19832 && next.pc<0x19844) ||
                (next.pc>=0x198ee && next.pc<0x19910) || (next.pc>=0x19978 && next.pc<0x199d4) ||
                (next.pc>=0x19a40 && next.pc<0x19b50) || (next.pc>=0x19b96 && next.pc<0x19dee) ||
                (next.pc>=0x1a26a && next.pc<0x1a3a6) || (next.pc>=0x1a3d6 && next.pc<0x1a40e) ||
                (next.pc>=0x1a442 && next.pc<0x1a470) || (next.pc>=0x1a526 && next.pc<0x1a5a4) ||
                (next.pc>=0x1a73c && next.pc<0x1a7a8))ok=animation_scene_core_block(c);
            else if ((next.pc>=0x18c06 && next.pc<0x19768) || (next.pc>=0x19812 && next.pc<0x19832) ||
                (next.pc>=0x19844 && next.pc<0x198ee) || (next.pc>=0x19910 && next.pc<0x19938))ok=animation_motion_walk_block(c);
            else if ((next.pc>=0x1a7a8 && next.pc<0x1a910) || (next.pc>=0x1724c && next.pc<0x17292) ||
                (next.pc>=0x43ea8 && next.pc<0x43eb8) || (next.pc>=0x1afda && next.pc<0x1b128) ||
                (next.pc>=0x19e64 && next.pc<0x1a07a) || (next.pc>=0x18656 && next.pc<0x18702))ok=animation_scene_update_block(c);
            else if ((next.pc>=0x3d7e && next.pc<0x3db2) || next.pc==0x16fee || (next.pc>=0x19772 && next.pc<0x197da) ||
                (next.pc>=0x19e60 && next.pc<0x19e64) || (next.pc>=0x1a086 && next.pc<0x1a26a) ||
                (next.pc>=0x1a40e && next.pc<0x1a414) || (next.pc>=0x1a470 && next.pc<0x1a526) ||
                (next.pc>=0xe89fa && next.pc<0xe8a0c))ok=animation_script_placement_block(c);
            else if ((next.pc>=0x49ab4 && next.pc<0x49bca) || (next.pc>=0x49c20 && next.pc<0x49c38) ||
                (next.pc>=0x49c66 && next.pc<0x49c6c) || (next.pc>=0x49d88 && next.pc<0x49f8c) || next.pc==0x1d8cc ||
                (next.pc>=0xe73f2 && next.pc<0xe73f8) || (next.pc>=0x1bec0 && next.pc<0x1bee4) ||
                (next.pc>=0x1d5ac && next.pc<0x1d5c4) || (next.pc>=0x1d5e2 && next.pc<0x1d5fc) ||
                (next.pc>=0x1d61a && next.pc<0x1d63a) || (next.pc>=0x1d664 && next.pc<0x1d698) ||
                (next.pc>=0x1d6c2 && next.pc<0x1d6fa) || (next.pc>=0x1da60 && next.pc<0x1daba) ||
                (next.pc>=0x4836e && next.pc<0x48384) ||
                (next.pc>=0x4d7a6 && next.pc<0x4d81c && next.pc!=0x4d7f0))ok=animation_input_block(c);
            else if ((next.pc>=0x4aa88 && next.pc<0x4abc0) || (next.pc>=0x4b784 && next.pc<0x4b82e) ||
                (next.pc>=0xe8a48 && next.pc<0xe8b5a) || (next.pc>=0x2986 && next.pc<0x299c))ok=animation_buffer_cue_block(c);
            else if ((next.pc>=0x47a94 && next.pc<0x47c5a) || (next.pc>=0x72f0 && next.pc<0x72fa) ||
                (next.pc>=0x1a5a4 && next.pc<0x1a73c) || (next.pc>=0x17292 && next.pc<0x1829a) ||
                (next.pc>=0x19768 && next.pc<0x19772) || (next.pc>=0x19938 && next.pc<0x19978) ||
                (next.pc>=0x199d4 && next.pc<0x19a00) || (next.pc>=0x19b50 && next.pc<0x19b96) ||
                (next.pc>=0x19dee && next.pc<0x19e60) || (next.pc>=0x1a07a && next.pc<0x1a086) ||
                (next.pc>=0x1a3c8 && next.pc<0x1a3d6) || (next.pc>=0x1a414 && next.pc<0x1a442) ||
                (next.pc>=0xe8a1c && next.pc<0xe8a3a) || (next.pc>=0xe905c && next.pc<0xe90ca && next.pc!=0xe909c) ||
                (next.pc>=0x477a2 && next.pc<0x477ac) || (next.pc>=0xddf9a && next.pc<0xddfa4) ||
                (next.pc>=0x362a && next.pc<0x3650) || (next.pc>=0x9060 && next.pc<0x9068) ||
                (next.pc>=0x4e254 && next.pc<0x4e26c) || (next.pc>=0xca56 && next.pc<0xca5c) ||
                (next.pc>=0xca76 && next.pc<0xca7e) || (next.pc>=0xc3c0 && next.pc<0xc3ce))ok=animation_stage_entry_block(c);
            else if ((next.pc>=0x47da4 && next.pc<0x47eac) || (next.pc>=0x4b6e4 && next.pc<0x4b6f4) ||
                (next.pc>=0x1c5b0 && next.pc<0x1c5ea) || (next.pc>=0x1bee4 && next.pc<0x1bef8) ||
                (next.pc>=0xca48 && next.pc<0xca50) || (next.pc>=0x9056 && next.pc<0x9060))ok=animation_area_clear_block(c);
            else if ((next.pc>=0x477e4 && next.pc<0x479b0 && next.pc!=0x478a6) || (next.pc>=0x474e2 && next.pc<0x474f4) ||
                (next.pc>=0x47540 && next.pc<0x4755e) || (next.pc>=0x3d58 && next.pc<0x3d62) || (next.pc>=0x3d6a && next.pc<0x3d7c) ||
                (next.pc>=0xca8a && next.pc<0xca9e) || (next.pc>=0x4814e && next.pc<0x48156))ok=animation_stage_catalog_block(c);
            else if ((next.pc>=0x479b0 && next.pc<0x47a54) || (next.pc>=0x47a64 && next.pc<0x47a94) ||
                (next.pc>=0x47594 && next.pc<0x47642) || (next.pc>=0x476dc && next.pc<0x477a2) || (next.pc>=0x3d3a && next.pc<0x3d44) ||
                (next.pc>=0x1bcfe && next.pc<0x1bdde) || (next.pc>=0x1be84 && next.pc<0x1be98) || (next.pc>=0x2ef90 && next.pc<0x2efa6) ||
                (next.pc>=0x2efdc && next.pc<0x2eff4) || (next.pc>=0x46f2e && next.pc<0x46f52) || (next.pc>=0x48180 && next.pc<0x481b2) ||
                (next.pc>=0x481de && next.pc<0x48210) || (next.pc>=0x49a58 && next.pc<0x49a84) || (next.pc>=0x49a8e && next.pc<0x49ab0) ||
                (next.pc>=0x4aa30 && next.pc<0x4aa86) || (next.pc>=0x4d126 && next.pc<0x4d196) ||
                (next.pc>=0x4d81c && next.pc<0x4d84e && next.pc!=0x4d824) || (next.pc>=0x4ddb6 && next.pc<0x4ddde) ||
                (next.pc>=0x4e666 && next.pc<0x4e68e) || (next.pc>=0xb4806 && next.pc<0xb481e) || (next.pc>=0xb4a24 && next.pc<0xb4a2a) ||
                (next.pc>=0xb7a20 && next.pc<0xb7a28) || (next.pc>=0xb7a2e && next.pc<0xb7a62) ||
                (next.pc>=0xd760a && next.pc<0xd764a))ok=animation_stage_area_block(c);
            else if ((next.pc>=0xe9150 && next.pc<0xe9350) || (next.pc>=0xe9444 && next.pc<0xe94fe) ||
                (next.pc>=0xe9768 && next.pc<0xe9774) || (next.pc>=0xe97c8 && next.pc<0xe98ee) ||
                (next.pc>=0x48502 && next.pc<0x4855c) || (next.pc>=0x1a910 && next.pc<0x1a91a) ||
                (next.pc>=0x1a93e && next.pc<0x1a952))ok=animation_stage_event_block(c);
            else if (((next.pc>=0x288c && next.pc<0x289e) || (next.pc>=0x1a92c && next.pc<0x1a93e) || (next.pc>=0x49a84 && next.pc<0x49a8e) ||
                (next.pc>=0xe9350 && next.pc<0xe93da) || (next.pc>=0xe93f0 && next.pc<0xe9444) || (next.pc>=0xe94fe && next.pc<0xe957c) ||
                (next.pc>=0xe958e && next.pc<0xe9768) || (next.pc>=0xe9774 && next.pc<0xe97c8)) &&
                !stage_event_ops_trap(next.pc))ok=animation_stage_event_ops_block(c);
            else if ((next.pc>=0x2aac && next.pc<0x2ab8) || (next.pc>=0x270e && next.pc<0x271c) ||
                (next.pc>=0x4fcce && next.pc<0x4fd0a) || (next.pc>=0x4fd58 && next.pc<0x4fda6))ok=animation_scheduler_block(c);
            else if ((next.pc>=0x1aa7e && next.pc<0x1ab02) || (next.pc>=0x48296 && next.pc<0x482aa) || (next.pc>=0x4b50c && next.pc<0x4b6e4) ||
                (next.pc>=0xb4d7e && next.pc<0xb4d88) || (next.pc>=0xb4da6 && next.pc<0xb4db0) || (next.pc>=0xb4dc2 && next.pc<0xb4dca) ||
                (next.pc>=0xb4df2 && next.pc<0xb4e46) || (next.pc>=0xb4e5a && next.pc<0xb4e6c) || (next.pc>=0xb4fd4 && next.pc<0xb503e) ||
                (next.pc>=0xc6a90 && next.pc<0xc6a96) || (next.pc>=0xd6d22 && next.pc<0xd6d36) ||
                (next.pc>=0xdd4d0 && next.pc<0xdd574))ok=animation_objects_u01_block(c);
            else if ((next.pc>=0x3950 && next.pc<0x39c6) || (next.pc>=0x39c8 && next.pc<0x3a0c) || (next.pc>=0x3a0e && next.pc<0x3a82) ||
                (next.pc>=0x8ebe && next.pc<0x8ec8) || (next.pc>=0x8ecc && next.pc<0x8f6c) || (next.pc>=0x8f84 && next.pc<0x8ff4) ||
                (next.pc>=0x443d2 && next.pc<0x443ea) || (next.pc>=0xe5086 && next.pc<0xe5292) || (next.pc>=0xe5614 && next.pc<0xe56c0) ||
                (next.pc>=0xe5724 && next.pc<0xe583c))ok=animation_objects_u02_block(c);
            else if (next.pc>=0xe84d6 && next.pc<0xe88c6)ok=animation_objects_u03_block(c);
            else if ((next.pc>=0x1ab02 && next.pc<0x1ab80) || (next.pc>=0xb96c8 && next.pc<0xb975e) ||
                (next.pc>=0xc6a96 && next.pc<0xc6c24))ok=animation_objects_u05_block(c);
            else if ((next.pc>=0xce02 && next.pc<0xce62) || (next.pc>=0x43ea4 && next.pc<0x43ea8) ||
                (next.pc>=0xd72f2 && next.pc<0xd75ce))ok=animation_objects_u04_block(c);
            else if ((next.pc>=0x49be0 && next.pc<0x49bf2) || (next.pc>=0xe73f8 && next.pc<0xe74f8) || (next.pc>=0xe7546 && next.pc<0xe7562) ||
                (next.pc>=0xe7792 && next.pc<0xe7946) || (next.pc>=0xeb7b6 && next.pc<0xeb9ba) ||
                (next.pc>=0xeba3e && next.pc<0xeba9e))ok=animation_objects_u06_block(c);
            else if ((next.pc>=0x4e186 && next.pc<0x4e1cc) || (next.pc>=0xe585c && next.pc<0xe5bb0))ok=animation_objects_u07_block(c);
            else if ((next.pc>=0x18be8 && next.pc<0x18c06) || (next.pc>=0x1aa3a && next.pc<0x1aa40) || (next.pc>=0x43eb8 && next.pc<0x43efa) ||
                (next.pc>=0x447be && next.pc<0x44ade) || (next.pc>=0x49274 && next.pc<0x4929e))ok=animation_objects_u08_block(c);
            else if ((next.pc>=0x469a0 && next.pc<0x46bfc) || (next.pc>=0x4706c && next.pc<0x470e6) || (next.pc>=0x470e8 && next.pc<0x47288) ||
                (next.pc>=0x7670e && next.pc<0x76852) || (next.pc>=0x769fc && next.pc<0x76a14))ok=animation_objects_u09_block(c);
            else if ((next.pc>=0x461ec && next.pc<0x461f2) || (next.pc>=0x46372 && next.pc<0x4662e) || (next.pc>=0x4683c && next.pc<0x46994) ||
                (next.pc>=0x4bb22 && next.pc<0x4bb52) || (next.pc>=0x4bc44 && next.pc<0x4bca0) || (next.pc>=0x4be34 && next.pc<0x4be50) ||
                (next.pc>=0x4be82 && next.pc<0x4bfa4))ok=animation_objects_u08b_block(c);
            else if ((next.pc>=0xbabb4 && next.pc<0xbb012) || (next.pc>=0xbb0b6 && next.pc<0xbb0f4) || (next.pc>=0xbb188 && next.pc<0xbb55a) ||
                (next.pc>=0xd7828 && next.pc<0xd788c) || (next.pc>=0xdbdb6 && next.pc<0xdbe1c) || next.pc==0xdbe1e)ok=animation_objects_u10_block(c);
            else if ((next.pc>=0x45176 && next.pc<0x4578a) || (next.pc>=0x47288 && next.pc<0x472be) || (next.pc>=0x49370 && next.pc<0x4937c) ||
                (next.pc>=0x4937e && next.pc<0x49392) || (next.pc>=0x496c2 && next.pc<0x496d2) || (next.pc>=0x497b6 && next.pc<0x497f0) ||
                (next.pc>=0x4be06 && next.pc<0x4be2c) || (next.pc>=0xbe888 && next.pc<0xbe992) ||
                (next.pc>=0xbeab4 && next.pc<0xbeb7a))ok=animation_objects_u11_block(c);
            else if ((next.pc>=0x1abda && next.pc<0x1abfa) || (next.pc>=0x46d72 && next.pc<0x46eec) || (next.pc>=0x49098 && next.pc<0x4910c) ||
                (next.pc>=0x4911a && next.pc<0x4913e) || (next.pc>=0x49140 && next.pc<0x49174) || (next.pc>=0x49176 && next.pc<0x491b6) ||
                (next.pc>=0x492ae && next.pc<0x492d0) || (next.pc>=0x4c0ac && next.pc<0x4c0ea) || (next.pc>=0x70054 && next.pc<0x7028e) ||
                (next.pc>=0x70418 && next.pc<0x7054c))ok=animation_objects_u12_block(c);
            else if ((next.pc>=0x7090a && next.pc<0x7091e) || (next.pc>=0x70932 && next.pc<0x70a6c) || (next.pc>=0xb80c4 && next.pc<0xb812c) ||
                (next.pc>=0xb8132 && next.pc<0xb81be) || (next.pc>=0xb83e6 && next.pc<0xb8400) || (next.pc>=0xea5f0 && next.pc<0xea600) ||
                (next.pc>=0xea60c && next.pc<0xea626) || (next.pc>=0xf1a4e && next.pc<0xf1a7a))ok=animation_objects_u13_block(c);
            else if ((next.pc>=0x16ef0 && next.pc<0x16f0e) || (next.pc>=0x49260 && next.pc<0x49274) || (next.pc>=0x4a496 && next.pc<0x4a4b4) ||
                (next.pc>=0x50cca && next.pc<0x50cd2) || (next.pc>=0x50d2c && next.pc<0x50dae) || (next.pc>=0x51482 && next.pc<0x51574) ||
                (next.pc>=0x51634 && next.pc<0x517a0) || (next.pc>=0x51fcc && next.pc<0x51ff4) || (next.pc>=0x51ffa && next.pc<0x5205e) ||
                (next.pc>=0x614d4 && next.pc<0x614da) || (next.pc>=0x7086a && next.pc<0x7087e))ok=animation_objects_u14_block(c);
            else if ((next.pc>=0x4662e && next.pc<0x4683c) || (next.pc>=0x4950e && next.pc<0x4954e) || (next.pc>=0x4c1de && next.pc<0x4c266) ||
                (next.pc>=0x4c29a && next.pc<0x4c2c4) || (next.pc>=0xaf078 && next.pc<0xaf096) || (next.pc>=0xaf146 && next.pc<0xaf302) ||
                (next.pc>=0xaf3de && next.pc<0xaf4ee) || (next.pc>=0xb0062 && next.pc<0xb0106) || (next.pc>=0xb05be && next.pc<0xb05de))ok=animation_objects_u15_block(c);
            else if ((next.pc>=0xb0106 && next.pc<0xb0150) || (next.pc>=0xb0206 && next.pc<0xb0228) || (next.pc>=0xb02c8 && next.pc<0xb02ec) ||
                (next.pc>=0xbbe12 && next.pc<0xbbf04) || (next.pc>=0xf1a0e && next.pc<0xf1a3a))ok=animation_objects_u16_block(c);
            else if (next.pc>=0x4578a && next.pc<0x45b12)ok=animation_objects_u15b_block(c);
            else if (next.pc>=0x45b12 && next.pc<0x461ec)ok=animation_objects_u15c_block(c);
            else if ((next.pc>=0x1c5ea && next.pc<0x1c618) || (next.pc>=0x443ea && next.pc<0x44402) || (next.pc>=0x482c0 && next.pc<0x482ea) ||
                (next.pc>=0x491c4 && next.pc<0x491e0) || (next.pc>=0x4929e && next.pc<0x492ae) || (next.pc>=0x4bfa4 && next.pc<0x4bfb4) ||
                (next.pc>=0x4c020 && next.pc<0x4c06c) || (next.pc>=0xbbf56 && next.pc<0xbc08c) ||
                (next.pc>=0xc3d60 && next.pc<0xc3fd4))ok=animation_objects_u17_block(c);
            else if ((next.pc>=0x46c68 && next.pc<0x46d1c) || (next.pc>=0x4be2c && next.pc<0x4be34) || (next.pc>=0xb631c && next.pc<0xb632a) ||
                (next.pc>=0xb66c8 && next.pc<0xb67b2) || (next.pc>=0xb76a4 && next.pc<0xb7742) || (next.pc>=0xb7bc2 && next.pc<0xb7c9e) ||
                (next.pc>=0xb7cfa && next.pc<0xb7d2e) || (next.pc>=0xb7e06 && next.pc<0xb7e74) || (next.pc>=0xea5e0 && next.pc<0xea5f0) ||
                (next.pc>=0xea636 && next.pc<0xea680) || (next.pc>=0xea762 && next.pc<0xea85a) || (next.pc>=0xea908 && next.pc<0xeaa00) ||
                (next.pc>=0xeaa54 && next.pc<0xeaa5a))ok=animation_objects_u18_block(c);
            else if ((next.pc>=0x484e2 && next.pc<0x484f8) || (next.pc>=0xb6300 && next.pc<0xb630e) || (next.pc>=0xb6338 && next.pc<0xb6346) ||
                (next.pc>=0xb6362 && next.pc<0xb6506) || (next.pc>=0xb68ba && next.pc<0xb6ba0) || (next.pc>=0xb7b4c && next.pc<0xb7bc2) ||
                (next.pc>=0xb7c9e && next.pc<0xb7cfa) || (next.pc>=0xba78c && next.pc<0xba800) || (next.pc>=0xd6d4a && next.pc<0xd6d68) ||
                (next.pc>=0xd81cc && next.pc<0xd83c0) || (next.pc>=0xdbefe && next.pc<0xdbf4a))ok=animation_objects_u19_block(c);
            else if ((next.pc>=0x44ade && next.pc<0x45176) || (next.pc>=0x492d0 && next.pc<0x492d8) ||
                (next.pc>=0x497a6 && next.pc<0x497b6))ok=animation_objects_u20_block(c);
            else if ((next.pc>=0x849f4 && next.pc<0x84a14) || (next.pc>=0x858d8 && next.pc<0x8597c) ||
                (next.pc>=0x85980 && next.pc<0x85c6c))ok=animation_objects_u20b_block(c);
            else if ((next.pc>=0x5208a && next.pc<0x52156) || (next.pc>=0xe5bb0 && next.pc<0xe5e80) ||
                (next.pc>=0xe5ea0 && next.pc<0xe5fbe))ok=animation_objects_n01_block(c);
            else if ((next.pc>=0x4b82e && next.pc<0x4b8a2) || (next.pc>=0xc603a && next.pc<0xc63b6) ||
                (next.pc>=0xc63be && next.pc<0xc644a) || (next.pc>=0xc647e && next.pc<0xc64a0))ok=animation_objects_n03_block(c);
            else if ((next.pc>=0x4a46c && next.pc<0x4a496) || (next.pc>=0x4bc04 && next.pc<0x4bc44) || (next.pc>=0x6feb4 && next.pc<0x70054) ||
                (next.pc>=0x71c90 && next.pc<0x71d48) || (next.pc>=0x72a18 && next.pc<0x72d56) || (next.pc>=0x72dd2 && next.pc<0x72e8e) ||
                (next.pc>=0xaa93e && next.pc<0xaaa18) || (next.pc>=0xab02a && next.pc<0xab078) || (next.pc>=0xab0b8 && next.pc<0xab226) ||
                (next.pc>=0xeb752 && next.pc<0xeb75c) || (next.pc>=0xeb766 && next.pc<0xeb774))ok=animation_objects_n04_block(c);
            else if ((next.pc>=0x1a3ae && next.pc<0x1a3c8) || (next.pc>=0x1ab80 && next.pc<0x1abda) || (next.pc>=0x49214 && next.pc<0x49260) ||
                (next.pc>=0xbdcc6 && next.pc<0xbdf82) || (next.pc>=0xc5e6c && next.pc<0xc5e7c) || (next.pc>=0xc5fd8 && next.pc<0xc6012) ||
                (next.pc>=0xd1cd8 && next.pc<0xd1d68) || (next.pc>=0xd1d98 && next.pc<0xd1df8) || (next.pc>=0xd1e58 && next.pc<0xd1e6e) ||
                (next.pc>=0xd22e6 && next.pc<0xd232c) || (next.pc>=0xd239c && next.pc<0xd23d8) || (next.pc>=0xd3c2a && next.pc<0xd3c40) ||
                (next.pc>=0xdceca && next.pc<0xdcf42))ok=animation_objects_n05_block(c);
            else if ((next.pc>=0x491b6 && next.pc<0x491c4) || (next.pc>=0xb9dc6 && next.pc<0xb9f32) || (next.pc>=0xb9f62 && next.pc<0xb9f96) ||
                (next.pc>=0xba196 && next.pc<0xba214) || (next.pc>=0xba234 && next.pc<0xba2b6) || (next.pc>=0xba2d6 && next.pc<0xba2fa) ||
                (next.pc>=0xba310 && next.pc<0xba338) || (next.pc>=0xba346 && next.pc<0xba364) || (next.pc>=0xba372 && next.pc<0xba39a) ||
                (next.pc>=0xba3a8 && next.pc<0xba3b6) || (next.pc>=0xd9bcc && next.pc<0xd9c0a) || (next.pc>=0xe90d8 && next.pc<0xe90f2) ||
                (next.pc>=0xeb774 && next.pc<0xeb7b6))ok=animation_objects_n06_block(c);
            else if ((next.pc>=0x9ad06 && next.pc<0x9ad34) || (next.pc>=0x9baf2 && next.pc<0x9bc74) || (next.pc>=0x9bf1e && next.pc<0x9c0b6) ||
                (next.pc>=0xbbb9e && next.pc<0xbbdc0))ok=animation_objects_n07_block(c);
            else if ((next.pc>=0x4945e && next.pc<0x494c0) || (next.pc>=0x4983e && next.pc<0x49878) ||
                (next.pc>=0x4ae4a && next.pc<0x4b50c))ok=animation_objects_n08_block(c);
            else if ((next.pc>=0xaf4ee && next.pc<0xaf80a) || (next.pc>=0xaf92c && next.pc<0xaf990) || (next.pc>=0xafc16 && next.pc<0xafcbe) ||
                (next.pc>=0xb005e && next.pc<0xb0062) || (next.pc>=0xb0150 && next.pc<0xb0206) || (next.pc>=0xb0228 && next.pc<0xb0240) ||
                (next.pc>=0xb0260 && next.pc<0xb02c8) || (next.pc>=0xb02ec && next.pc<0xb04cc) ||
                (next.pc>=0xb057e && next.pc<0xb05be))ok=animation_objects_n09_block(c);
            else if (next.pc>=0xc5896 && next.pc<0xc593e)ok=animation_objects_n10_block(c);
            else if ((next.pc>=0xaee30 && next.pc<0xaf06c) || (next.pc>=0xdbf80 && next.pc<0xdbf9a) || (next.pc>=0xeb24e && next.pc<0xeb2fe) ||
                (next.pc>=0xeb352 && next.pc<0xeb3e2) || (next.pc>=0xeb586 && next.pc<0xeb5aa) || (next.pc>=0xeb5e6 && next.pc<0xeb626) ||
                (next.pc>=0xeb74a && next.pc<0xeb752) || (next.pc>=0xeb75c && next.pc<0xeb766))ok=animation_objects_n11_block(c);
            else if ((next.pc>=0x52e4a && next.pc<0x52e64) || (next.pc>=0x52e78 && next.pc<0x531a2) || (next.pc>=0x531c2 && next.pc<0x532a0) ||
                (next.pc>=0x539e4 && next.pc<0x53b50) || (next.pc>=0x53b70 && next.pc<0x53ee0))ok=animation_objects_n12_block(c);
            else if ((next.pc>=0x59ea2 && next.pc<0x59f1a) || (next.pc>=0x5a7c8 && next.pc<0x5a9bc) || (next.pc>=0x5a9c2 && next.pc<0x5ab6c) ||
                (next.pc>=0x5b220 && next.pc<0x5b4c6) || (next.pc>=0xd3580 && next.pc<0xd3614) || (next.pc>=0xd3ab8 && next.pc<0xd3ace) ||
                (next.pc>=0xd3ae8 && next.pc<0xd3b70) || (next.pc>=0xdbfac && next.pc<0xdbfb8))ok=animation_objects_n13_block(c);
            else if ((next.pc>=0x4970a && next.pc<0x4976e) || (next.pc>=0x4b702 && next.pc<0x4b70a) || (next.pc>=0xa5cf6 && next.pc<0xa6172) ||
                (next.pc>=0xa6914 && next.pc<0xa6ac6) || (next.pc>=0xa6dd4 && next.pc<0xa6eea) || (next.pc>=0xa7256 && next.pc<0xa725c) ||
                (next.pc>=0xbe0c4 && next.pc<0xbe13c))ok=animation_objects_n14_block(c);
            else if ((next.pc>=0x493bc && next.pc<0x493c6) || (next.pc>=0x493c8 && next.pc<0x493fc) || (next.pc>=0x7028e && next.pc<0x702cc) ||
                (next.pc>=0x7054c && next.pc<0x70594) || (next.pc>=0x705ca && next.pc<0x70606) || (next.pc>=0x708a6 && next.pc<0x708ba) ||
                (next.pc>=0x71032 && next.pc<0x7117e) || (next.pc>=0x7119e && next.pc<0x7120e) || (next.pc>=0x71a80 && next.pc<0x71b42) ||
                (next.pc>=0x71bc0 && next.pc<0x71c90) || (next.pc>=0x71d48 && next.pc<0x71e8c) || (next.pc>=0x72d66 && next.pc<0x72da6) ||
                (next.pc>=0x72dac && next.pc<0x72dcc) || (next.pc>=0x72dce && next.pc<0x72dd2) || (next.pc>=0x76d18 && next.pc<0x76f14) ||
                (next.pc>=0x76f18 && next.pc<0x76ff2))ok=animation_objects_n15_block(c);
            else if ((next.pc>=0x77556 && next.pc<0x7768e) || (next.pc>=0x77d38 && next.pc<0x77d8e) ||
                (next.pc>=0x7839a && next.pc<0x783ae) || (next.pc>=0x783c0 && next.pc<0x783ea) || (next.pc>=0x78c22 && next.pc<0x78c58) ||
                (next.pc>=0x78c5c && next.pc<0x78cc0) || (next.pc>=0x78de6 && next.pc<0x78dec) || (next.pc>=0x79054 && next.pc<0x790a6) ||
                (next.pc>=0x790be && next.pc<0x790fc) || (next.pc>=0x79114 && next.pc<0x79130) || (next.pc>=0x791c0 && next.pc<0x79222) ||
                (next.pc>=0x79256 && next.pc<0x7930a) || (next.pc>=0x79566 && next.pc<0x795b8) || (next.pc>=0x7960a && next.pc<0x7962a) ||
                (next.pc>=0x7967e && next.pc<0x79698) || (next.pc>=0x796cc && next.pc<0x796e6))ok=animation_objects_n16_block(c);
            else if ((next.pc>=0x7a388 && next.pc<0x7a4dc) || (next.pc>=0x7a4de && next.pc<0x7a558) ||
                (next.pc>=0x7a65a && next.pc<0x7a6ce) || (next.pc>=0x7aa5e && next.pc<0x7aa64) || (next.pc>=0x7aa66 && next.pc<0x7aa6c) ||
                (next.pc>=0x7aa6e && next.pc<0x7abc2) || (next.pc>=0x7afa6 && next.pc<0x7b11a) || (next.pc>=0x7b140 && next.pc<0x7b1da) ||
                (next.pc>=0x7b200 && next.pc<0x7b28e) || (next.pc>=0x7b570 && next.pc<0x7b5a8) || (next.pc>=0x7b740 && next.pc<0x7b75e) ||
                (next.pc>=0x7b786 && next.pc<0x7b79a) || (next.pc>=0x7b7ae && next.pc<0x7b7d4))ok=animation_objects_n17_block(c);
            else if ((next.pc>=0x8625a && next.pc<0x86348) || (next.pc>=0x8634e && next.pc<0x86372) ||
                (next.pc>=0x864b6 && next.pc<0x86560) || (next.pc>=0x86564 && next.pc<0x86742) || (next.pc>=0x86814 && next.pc<0x868ea) ||
                (next.pc>=0x86f1c && next.pc<0x86fca) || (next.pc>=0x8715e && next.pc<0x871ee) || (next.pc>=0xb630e && next.pc<0xb631c) ||
                (next.pc>=0xb6506 && next.pc<0xb660e) || (next.pc>=0xb780c && next.pc<0xb78b8) ||
                (next.pc>=0xdbe98 && next.pc<0xdbeec))ok=animation_objects_n18_block(c);
            else if ((next.pc>=0x86742 && next.pc<0x86814) || (next.pc>=0xb15e0 && next.pc<0xb1656) ||
                (next.pc>=0xb16ea && next.pc<0xb19f2) || (next.pc>=0xb1b24 && next.pc<0xb1c82) ||
                (next.pc>=0xb1cf8 && next.pc<0xb1d8c) || (next.pc>=0xb1dae && next.pc<0xb1e2a) ||
                (next.pc>=0xb1fd6 && next.pc<0xb2004) || (next.pc>=0xdbf5e && next.pc<0xdbf6e))ok=animation_objects_n19_block(c);
            else if ((next.pc>=0x49580 && next.pc<0x495e2) || (next.pc>=0x735b0 && next.pc<0x735e8) ||
                (next.pc>=0x7361a && next.pc<0x7364a) || (next.pc>=0x7364c && next.pc<0x739c0) || (next.pc>=0xb9832 && next.pc<0xb9c0e) ||
                (next.pc>=0xb9c6e && next.pc<0xb9d0a))ok=animation_objects_n20_block(c);
            else if ((next.pc>=0xb9c0e && next.pc<0xb9c6e) || (next.pc>=0xb9d0a && next.pc<0xb9da6) ||
                (next.pc>=0xc3fdc && next.pc<0xc4084))ok=animation_objects_n21_block(c);
            else if ((next.pc>=0x1bf02 && next.pc<0x1bf6c) || (next.pc>=0x1bfb4 && next.pc<0x1c012) ||
                (next.pc>=0x3d228 && next.pc<0x3d234) || (next.pc>=0x3d280 && next.pc<0x3d3f0) ||
                (next.pc>=0x3db62 && next.pc<0x3db68) || (next.pc>=0x3dbba && next.pc<0x3dbbe) ||
                (next.pc>=0x3dc24 && next.pc<0x3dcac) || (next.pc>=0x3dcf2 && next.pc<0x3dd0e) ||
                (next.pc>=0x3dd6a && next.pc<0x3dde4) || (next.pc>=0x3de06 && next.pc<0x3de54) ||
                (next.pc>=0x3df44 && next.pc<0x3e03e) || (next.pc>=0x3e0f6 && next.pc<0x3e1b8) ||
                (next.pc>=0x3e1c2 && next.pc<0x3e250) || (next.pc>=0x41fe6 && next.pc<0x420be))ok=animation_objects_n22_block(c);
            else if ((next.pc>=0x420be && next.pc<0x4240a) || (next.pc>=0x42410 && next.pc<0x42460) ||
                (next.pc>=0x484b4 && next.pc<0x484ca) || (next.pc>=0x4d2d4 && next.pc<0x4d418) ||
                (next.pc>=0x4d508 && next.pc<0x4d55e) || (next.pc>=0x4d766 && next.pc<0x4d77e) ||
                (next.pc>=0x4d900 && next.pc<0x4d970) || (next.pc>=0x4da4a && next.pc<0x4da74) ||
                (next.pc>=0x4db42 && next.pc<0x4dbdc) || (next.pc>=0xc3a7c && next.pc<0xc3c1c))ok=animation_objects_n23_block(c);
            else if ((next.pc>=0x2b418 && next.pc<0x2b532) || (next.pc>=0x2b668 && next.pc<0x2b6c4) ||
                (next.pc>=0x2b7ce && next.pc<0x2b8ae) || (next.pc>=0x2b8b6 && next.pc<0x2b8fc) ||
                (next.pc>=0x2b96c && next.pc<0x2ba50) || (next.pc>=0x2c760 && next.pc<0x2c7a6) ||
                (next.pc>=0x2c7fe && next.pc<0x2c8f2) || (next.pc>=0x2ca68 && next.pc<0x2cb30) ||
                (next.pc>=0x306a8 && next.pc<0x306b4) || (next.pc>=0x30718 && next.pc<0x307da) ||
                (next.pc>=0x30ed2 && next.pc<0x30ed6) || (next.pc>=0x30f84 && next.pc<0x31002))ok=animation_objects_n28_block(c);
            else if (next.pc>=0x5deec && next.pc<0x5e8a6)ok=animation_objects_n24_block(c);
            else if ((next.pc>=0x306b4 && next.pc<0x30718) || (next.pc>=0x308e2 && next.pc<0x30b6c) ||
                (next.pc>=0x30dbe && next.pc<0x30ed2) || (next.pc>=0x30ed6 && next.pc<0x30f84) ||
                (next.pc>=0x31002 && next.pc<0x310de) || (next.pc>=0x3164a && next.pc<0x3169c) ||
                (next.pc>=0x316ac && next.pc<0x316c2) || (next.pc>=0x318d8 && next.pc<0x319b6) ||
                (next.pc>=0x319f6 && next.pc<0x31a54) || (next.pc>=0x3310c && next.pc<0x3312c))ok=animation_objects_n29_block(c);
            else if ((next.pc>=0x30b6c && next.pc<0x30d6c) || (next.pc>=0x3323e && next.pc<0x336d2) ||
                (next.pc>=0x3395c && next.pc<0x33a88))ok=animation_objects_b1c_block(c);
            else if ((next.pc>=0x5e8b0 && next.pc<0x5ea38) || (next.pc>=0x5eac2 && next.pc<0x5eeac) ||
                (next.pc>=0x5efe6 && next.pc<0x5f23a))ok=animation_objects_n25_block(c);
            else if ((next.pc>=0x5f24a && next.pc<0x5f4b0) || (next.pc>=0x5f760 && next.pc<0x5fb06) ||
                (next.pc>=0x5fb0e && next.pc<0x5fd04))ok=animation_objects_n26_block(c);
            else if ((next.pc>=0x33132 && next.pc<0x3323e) || (next.pc>=0x336d2 && next.pc<0x3383c) ||
                (next.pc>=0x33958 && next.pc<0x3395c) || (next.pc>=0x33a88 && next.pc<0x33c78) ||
                (next.pc>=0x33f4c && next.pc<0x33f58) || (next.pc>=0x345c2 && next.pc<0x346c0) ||
                (next.pc>=0x346c6 && next.pc<0x346fc) || (next.pc>=0x34714 && next.pc<0x34750) ||
                (next.pc>=0x34874 && next.pc<0x348a2))ok=animation_objects_n30_block(c);
            else if ((next.pc>=0x5fd24 && next.pc<0x5ffd8) || (next.pc>=0x60008 && next.pc<0x60316) ||
                (next.pc>=0x6031e && next.pc<0x60416) || (next.pc>=0x6041e && next.pc<0x60506) ||
                (next.pc>=0xdcf56 && next.pc<0xdcf6a))ok=animation_objects_n27_block(c);
            else if ((next.pc>=0x34750 && next.pc<0x34752) || (next.pc>=0x38ba0 && next.pc<0x38d56) ||
                (next.pc>=0x3a2f4 && next.pc<0x3a4a4))ok=animation_objects_n31_block(c);
            else if ((next.pc>=0x38dd4 && next.pc<0x38e86) || (next.pc>=0x38ff4 && next.pc<0x391e8) ||
                (next.pc>=0x395dc && next.pc<0x39a1a))ok=animation_objects_n32_block(c);
            else if ((next.pc>=0xb68 && next.pc<0xbb6) || (next.pc>=0xe4a && next.pc<0xfb8) || (next.pc>=0xfbc && next.pc<0xfee) ||
                (next.pc>=0xff0 && next.pc<0x1002) || (next.pc>=0x3c08 && next.pc<0x3c42) || (next.pc>=0x3db2 && next.pc<0x3dcc) ||
                (next.pc>=0x8bc8 && next.pc<0x8c16) || (next.pc>=0x903a && next.pc<0x9056) || (next.pc>=0x9546 && next.pc<0x955e) ||
                (next.pc>=0x166bc && next.pc<0x16cfa) || (next.pc>=0x1879c && next.pc<0x187d8) || (next.pc>=0x1ae56 && next.pc<0x1aeb4) ||
                (next.pc>=0x43dbc && next.pc<0x43dcc))ok=animation_frame_head_h1_block(c);
            else if ((next.pc>=0x39b72 && next.pc<0x39ca6) || (next.pc>=0x39cb0 && next.pc<0x39f9c))ok=animation_objects_n32b_block(c);
            else if ((next.pc>=0x3a1e0 && next.pc<0x3a2f4) || (next.pc>=0x3a5d2 && next.pc<0x3a60a) ||
                (next.pc>=0x3b118 && next.pc<0x3b424) || (next.pc>=0x3b542 && next.pc<0x3b5a6) ||
                (next.pc>=0x46bfc && next.pc<0x46c02) || (next.pc>=0x482aa && next.pc<0x482c0) ||
                (next.pc>=0x4b8e4 && next.pc<0x4bb1a) || (next.pc>=0x4bce0 && next.pc<0x4be06) ||
                (next.pc>=0x4be50 && next.pc<0x4be82) || (next.pc>=0x4bfb4 && next.pc<0x4bfc0) ||
                (next.pc>=0x4c0ea && next.pc<0x4c0f0) || (next.pc>=0x4c37c && next.pc<0x4c390) ||
                (next.pc>=0x4c7a4 && next.pc<0x4c810))ok=animation_objects_n33_block(c);
            else if (next.pc>=0x4718 && next.pc<0x72f0)ok=animation_frame_head_h3_block(c);
            else if (next.pc>=0x11792 && next.pc<0x13b46)ok=animation_frame_head_h4_block(c);
            else if (next.pc>=0xce62 && next.pc<0xf226)ok=animation_frame_head_h8_block(c);
            else if ((next.pc>=0x4c6f0 && next.pc<0x4c72a) || (next.pc>=0x4cf52 && next.pc<0x4cf64) ||
                (next.pc>=0x4d8d8 && next.pc<0x4d900) || (next.pc>=0xea680 && next.pc<0xea69c))ok=animation_objects_n35_block(c);
            else if ((next.pc>=0x313c && next.pc<0x3144) || (next.pc>=0x31d6 && next.pc<0x35a2) ||
                (next.pc>=0x3902 && next.pc<0x3918) || (next.pc>=0x9086 && next.pc<0x9344))ok=animation_frame_head_h2_block(c);
            else if ((next.pc>=0x4c3de && next.pc<0x4c6f0) || (next.pc>=0x4c72a && next.pc<0x4c7a4) ||
                (next.pc>=0x4c810 && next.pc<0x4cf52))ok=animation_objects_n34_block(c);
            else if ((next.pc>=0x20c && next.pc<0x2d8) || next.pc==0x3dcc || (next.pc>=0xa2c && next.pc<0xb0c) ||
                (next.pc>=0xbbe && next.pc<0xbee) || (next.pc>=0xc8c && next.pc<0xd56) || (next.pc>=0x3cac && next.pc<0x3d3a) ||
                (next.pc>=0x48156 && next.pc<0x48180) || (next.pc>=0x1adf8 && next.pc<0x1ae56) || (next.pc>=0x187d8 && next.pc<0x18be8) ||
                (next.pc>=0x16092 && next.pc<0x166bc) || (next.pc>=0x16cfa && next.pc<0x16ea4))ok=animation_irq_f6a_block(c);
            else if ((next.pc>=0x3383c && next.pc<0x338f8) || (next.pc>=0x33940 && next.pc<0x33958) ||
                (next.pc>=0x38d56 && next.pc<0x38dd4) || (next.pc>=0x39f9c && next.pc<0x3a048) ||
                (next.pc>=0x3a0dc && next.pc<0x3a1e0) || (next.pc>=0x3a4a4 && next.pc<0x3a4d6) ||
                (next.pc>=0x3a4da && next.pc<0x3a5d2) || (next.pc>=0x3acd6 && next.pc<0x3ad48) ||
                (next.pc>=0x3b424 && next.pc<0x3b458) || (next.pc>=0x4bfc0 && next.pc<0x4c020) ||
                (next.pc>=0x4c2fa && next.pc<0x4c340) || (next.pc>=0x4c390 && next.pc<0x4c3ba) ||
                (next.pc>=0x4c3cc && next.pc<0x4c3de) || (next.pc>=0x4d418 && next.pc<0x4d508) ||
                (next.pc>=0x4d6b4 && next.pc<0x4d6f2) || (next.pc>=0x4d734 && next.pc<0x4d766) ||
                (next.pc>=0x4d98a && next.pc<0x4d9a2) || (next.pc>=0x4d9ba && next.pc<0x4d9d6) ||
                (next.pc>=0x4eea2 && next.pc<0x4eef4) || (next.pc>=0x4f08a && next.pc<0x4f0c4) ||
                (next.pc>=0x4ff96 && next.pc<0x4ffba) || (next.pc>=0xd3d7c && next.pc<0xd3d9c))ok=animation_objects_b2b_block(c);
            else if ((next.pc>=0x8b64 && next.pc<0x8bbc) || (next.pc>=0xc52a && next.pc<0xc56e))ok=animation_controller_c3_block(c);
            else if ((next.pc>=0x3d3f0 && next.pc<0x3d526) || (next.pc>=0x3d7e8 && next.pc<0x3d982) || (next.pc>=0x3da72 && next.pc<0x3db62) ||
                (next.pc>=0x3db68 && next.pc<0x3dbba) || (next.pc>=0x3dbbe && next.pc<0x3dc24) || (next.pc>=0x3dcac && next.pc<0x3dcf2) ||
                (next.pc>=0x3dd0e && next.pc<0x3dd42) || (next.pc>=0x3dde4 && next.pc<0x3de06) || (next.pc>=0x3de54 && next.pc<0x3def2) ||
                (next.pc>=0x3defa && next.pc<0x3df1a) || (next.pc>=0x3df1e && next.pc<0x3df44) || (next.pc>=0x3e03e && next.pc<0x3e0aa) ||
                (next.pc>=0x3e250 && next.pc<0x3e302) || (next.pc>=0xb1656 && next.pc<0xb16ea) || (next.pc>=0xb1c82 && next.pc<0xb1c90) ||
                (next.pc>=0xb1c9e && next.pc<0xb1cf8) || (next.pc>=0xb1d8c && next.pc<0xb1dae))ok=animation_objects_b1b_block(c);
            else if (next.pc>=0x72fa && next.pc<0x8b64)ok=animation_irq_f6b_block(c);
            else if ((next.pc>=0x30bc && next.pc<0x30ec) || (next.pc>=0x314c && next.pc<0x3162) || (next.pc>=0x3670 && next.pc<0x370c) ||
                (next.pc>=0xc49c && next.pc<0xc4cc) || (next.pc>=0xc4f8 && next.pc<0xc52a) || (next.pc>=0xc654 && next.pc<0xc686) ||
                (next.pc>=0xc724 && next.pc<0xc74c) || (next.pc>=0xc7fc && next.pc<0xc80e) || (next.pc>=0xc988 && next.pc<0xca22) ||
                (next.pc>=0xca32 && next.pc<0xca3a) || (next.pc>=0x4a88e && next.pc<0x4a8f8) ||
                (next.pc>=0x4a944 && next.pc<0x4a9e2))ok=animation_controller_c1_block(c);
            else if ((next.pc>=0x5eed2 && next.pc<0x5efe6) || (next.pc>=0x5f504 && next.pc<0x5f760) || (next.pc>=0x60516 && next.pc<0x6093a))ok=animation_objects_b2a_block(c);
            else return am_error(c,"unsupported animation machine PC");
            if (!ok)return false;
            if (c.waiting) {result=AnimationMachineWaiting;stopped=true;break;}
        }
        if (!stopped)return am_error(c,"animation machine block budget exceeded");
        ram.swap(next_ram);state=next;
        device.pvc.swap(next_device.pvc);device.bank_base=next_device.bank_base;device.reads.swap(next_device.reads);
        if (palette!=0) {
            palette->banks[0].swap(next_palette.banks[0]);palette->banks[1].swap(next_palette.banks[1]);palette->selected=next_palette.selected;
        }
        ports.swap(next_ports);external_reads=c.external_reads;status=result;error.clear();return true;
    } catch (const std::bad_alloc&) {error="cannot allocate animation machine transaction";return false;}
}
}
bool run_animation_machine(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,const ProgramBusState& resources,
    AnimationMachineState& state,AnimationMachineDevice& device,
    std::uint32_t stop_pc,std::uint8_t external_status,std::uint32_t& external_reads,
    AnimationMachineStatus& status,std::vector<VideoPortWrite>& ports,std::string& error) {
    return run_machine(ram,windows,resources,state,device,0,stop_pc,external_status,external_reads,status,ports,error);
}
bool run_animation_machine_with_palette(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,const ProgramBusState& resources,
    AnimationMachineState& state,AnimationMachineDevice& device,AnimationMachinePaletteRam& palette,
    std::uint32_t stop_pc,std::uint8_t external_status,std::uint32_t& external_reads,
    AnimationMachineStatus& status,std::vector<VideoPortWrite>& ports,std::string& error) {
    if (palette.banks[0].size()!=8192 || palette.banks[1].size()!=8192 || palette.selected>1) {
        error="invalid animation machine palette RAM";return false;
    }
    return run_machine(ram,windows,resources,state,device,&palette,stop_pc,external_status,external_reads,status,ports,error);
}
}
