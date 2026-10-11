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
bool am_read(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t& value) {
    if ((address&0xffffffU)==0xd00046U && size==1) {
        ++c.external_reads;value=c.external_status;return true;
    }
    c.bus.bank_base=c.device.bank_base;
    return read_program_bus(c.ram,c.windows,c.bus,address,size,value,c.error);
}
namespace {
bool carry_preserving_pc(std::uint32_t pc) {
    // Entire original blocks must preserve C. Shared bus/stack operations do
    // not imply MOVE flags: MOVEM, PEA, JSR and RTS use those operations too.
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
    case 0x2a16:case 0x2a1a:case 0x2a1c:case 0x2a1e:case 0x2a3c:case 0x2a40:case 0x2a44:case 0x2a46:
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
    case 0x43e34:case 0x4855a:case 0xe9176:case 0xe9194:case 0xe9196:case 0xe91ac:case 0xe91be:case 0xe91e4:case 0xe91e8:case 0xe91ec:case 0xe91f0:
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
    // BTST/BEQ changes only Z; its known memory test is already modeled.
    case 0x3b82:return true;
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
bool run_animation_machine(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows,const ProgramBusState& resources,
    AnimationMachineState& state,AnimationMachineDevice& device,
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
            else return am_error(c,"unsupported animation machine PC");
            if (!ok)return false;
            if (c.waiting) {result=AnimationMachineWaiting;stopped=true;break;}
        }
        if (!stopped)return am_error(c,"animation machine block budget exceeded");
        ram.swap(next_ram);state=next;
        device.pvc.swap(next_device.pvc);device.bank_base=next_device.bank_base;
        ports.swap(next_ports);external_reads=c.external_reads;status=result;error.clear();return true;
    } catch (const std::bad_alloc&) {error="cannot allocate animation machine transaction";return false;}
}
}
