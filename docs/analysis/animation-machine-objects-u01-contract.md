# 객체 callback F4 U01: `b4d7e` 계열·C2 `1aa7e`·C4 `4b50c`/`4b54e`·stub 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U01 행과 그 "메인 결정"이다. 적용하는 메인 결정은 다음과 같다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기·DBcc fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- 결정 6: `TRAP #f`는 실행부 없는 checked 경계다(stop이면 직전 상태로 멈춤, 아니면 rollback).

구조와 규약(묶인 분기, carry 보존 목록, 소비 block, 내부 PC 거부, ROM window)은 F1a·F1b·F1c·F3 계약을 따른다. 실행 규약(프레임 패스)은 F2 계약(`animation-machine-scheduler-shell-f2-contract.md`)과 같다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U01의 코드와 자료는 모두 fixed `<100000`에 있으므로 CPU 주소와 file offset이 같다. 기존 실행부와 routing은 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `55261ac`, F2 WIP)을 참조했다. [F]=원본 바이트, 기록 산출물 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u01/u01.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U01은 **block 시작 105개 + TRAP 경계 2개(`b4db0`, `b4e46`)**다. 코드 12 범위, 1,050바이트, 279명령이며 미해독은 없다. routing 짝수 PC는 525개, 내부 PC는 420개다.
- [F] **범위 문서 114와의 차이(−9)**:
  - −7: `b4fe0` `b4fe4` `b4fe8` `b4fec` `b4ff0` `b4ff4` `b4ffa`는 `b4fd4` 직선 block 안의 Unicorn TB 분할 인공물이다(결정 3).
  - −2: TRAP 자리 `b4db0`·`b4e46`은 block이 아니라 경계다(F3b 관례).
  - −2: `1aa9c BMI`·`1aad8 BMI`는 앞 `BEQ`의 fall-through이며 같은 `CMP.W`의 N을 소비한다. 앞 block에 묶는다(F3 결정 3 선택 A).
  - +2: `b4e34`(`b4e2a`·`b4e64`가 `MOVE.L #b4e34,(A6)`로 설치)와 `dd512`(`dd506`이 설치)는 callback 진입이다. 범위 스크립트는 본문 안 fall-through라 leader로 세지 않았다.
- [F] 함수 9개: `1aa7e`(C2), `48296`, `4b50c`·`4b54e`(C4), node callback `b4d7e`(설치 callback `b4df8` `b4e1c` `b4e34`), `b4fd4`, `c6a90`, `d6d22`, `dd4d0`(설치 callback `dd4e2` `dd512`).
- [F] 경계(실행부 없음): callee `b4e6c`(`b4e22 JSR`), `482c0`(`dd4ec JSR`), callback `dd574`(`dd546` 설치), TRAP `b4db0` `b4e46`. 같은 영역의 다른 진입 `b4d88` `b4d92` `b4d9c`와 `b4dca..b4df0`(그 경로)는 U01 밖이다.
- [F] 기존 실행부로 나가는 출구: `43e34`(F3a), `49a84`(F3b, 안에서 `49a58` F1c2), `4b784`(U7), `1c5b0`(F1b), `3af8`(sound), `2a00`(fade_card).
- 자연 seed(F2 프레임 패스, 기본 120 frame): 52·53·74·75·112~115가 `b4d7e`/`b4df8`, 54·55가 `c6a90`, 72·73이 `dd4d0`/`dd4e2`/`d6d22`, 2·3이 `b4d7e`→`b500c`→`49a84`→RNG 경계로 끝난다. U01 뒤 완주 seed는 25→39가 되어야 한다(아래 "최소 검증").

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(114→105).** 위 요약의 −7/−2/−2/+2를 채택한다(권고). 범위 문서는 고치지 않는다.
2. **`4b6be`의 known carry.** [F] `4b54e`의 모든 길은 `4b6be`(`MOVEQ`; `MOVEQ`; `MOVE.B 5e(A6),D0`; `BEQ 4b6e2`)를 지난다. M68000 `MOVE`는 C를 지운다. 그래서 `4b54e`의 반환 C는 BYTE `5e(A6)`=0이면 Clear(`4b6e2 RTS`), 아니면 `4b6ca ... ORI #1,CCR`로 Set이다. [F] fixed ROM의 `JSR 4b54e` 호출자 중 다수(`54382 BCC`, `7f3fa BCS` 등 50곳 이상)가 이 C를 소비한다. 권고: `4b6be`를 known Clear 생산 block으로 둔다(F1a `72f0` SUBI.B와 같은 "block 안에서 C를 정함" 유형). U01 안에서는 `b4dfe`→`b4e04 CLR.B`가 C를 소비하지 않는다.
   - [F] scratch Unicorn 확인(`f4u01/gen/carry_probe.py`): ROM 소비자 `56a38 JSR 4b54e; 56a3e BCC 56a46`을 `56(A6)`=0으로 실행하면 들어오는 C가 0이든 1이든 `5e`=0이면 `56a46`, `5e`=`19`이면 `56a42`로 간다. [F] 같은 재생에서 code hook 시점의 SR 읽기는 MOVE 계열의 지연 flag를 반영하지 않으므로(`4b6be` 뒤 C=1로 읽힘) C 검증에는 쓰지 않는다. ANDI/ORI CCR 뒤 값만 믿는다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u01.cpp`의 `animation_objects_u01_block`. 오류는 `unsupported animation objects u01 PC`, `objects u01 caller requires known carry`(권고, 메인 지시와 같음).
4. **RNG seed(2·3).** [F] `b500c`→`49a84`→`49a58`에서 seed RAM의 RNG 포인터 0 때문에 native는 frame 0에 ROM `30` 쓰기로 멈추고, C++ F1c2는 `stage area RNG pointer outside work RAM` checked 오류다(F1c 결정 9, 의도된 차이). 권고: 정지 frame이 같으면 "완주(guard)"로 센다(F4 범위 문서와 같음).

## 원본 바이트 근거

[F] 코드 12 범위 합계 1,050바이트. 이어 붙인 SHA256 `76c9d42437c0dd384f79ebbbb3fc018ddfa0634dad6e453999ef9ed13e1e0f31`.

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `1aa7e..1ab02` | `20182218082e0001001567000006d0414440342e0046b46e004e670000206b000010d440b46d53f86e0000546000000ed440d441b46d53f66d00004448404841082e0000001567000006d0414440342e0042b46e004a670000206b000010d440b46d53f46e0000186000000ed440d441b46d53f26d000008023c00fe4e75003c00014e75` |
| `48296..482aa` | `08ad0005568308ad000456834eb90001c5b04e75` |
| `4b50c..4b6e4` | `0c6b0001000a670000344a2d5b846700002c286b000cb8fc00006700000a4a6c003267000018426e005408ee000700611d7c0019005e003c00014e75023c00fe4e75266e0056b6fc00006700016661b06500016045ee005a49ed57464a2d57446a000008524a49ed591814bc00ff382c01d00c4400406400013a1a04e64d464502450007201b221b082e0001001567000006d0414440d06e004648404841082e0000001567000006d0414440d06e00423c3cffe03e3c015fd240b0476e0000f4b2466d0000ee90466c0000044240b2476f00000432079246484048413c3c01003e3c01ffd240b0476e0000c8b2466d0000c290466c0000044240b2476f00000432079246ea88ea893c3c07ffc046c2469280e788d04543f4006009d143e9000851c9fff848404841d04543f4000009d143e9000851c9fff8301b43faf39a10310000e748d04543ec00a009f10000301be2406400000a43ec00b809f15000e2406400000a43ec00c009f15000e2406400000a43ec00c809f15000302c01d014803e00e54f45ec00d0258e70005240394001d0083900060010f0006700001641eb00062e3c00000a2b4eba00ce0c50800066f074007600102e005e6700001a142e005cd442162e005dd643946e0042966e0046003c00014e75` |
| `b4d7e..b4d88` | `3d7c0000008c60000020` |
| `b4da6..b4db0` | `0c6e0004007665000014` |
| `b4dc2..b4dca` | `4eba02106000002a` |
| `b4df2..b4e46` | `2cbc000b4df84eb900043e344eb90004b54e422e005e082e0007006166000006600000262cbc000b4e1c4eb900043e344eba0048640000082cbc000b4e34600000084ef900002a00206e0056b0fc000066000016` |
| `b4e5a..b4e6c` | `4eb90001aa7e640000082cbc000b4e344e75` |
| `b4fd4..b503e` | `302e0076d040d04041fa018e207000002d480056d0fc00122d58008e2d5800923d6e007a00546600000808ee000700614a6e007866000012303c00034eb900049a8452403d400078422e009c302e0082122e0084142e008548c0e1882d4000881d41009a1d42009b4e75` |
| `c6a90..c6a96` | `4ef900002a00` |
| `d6d22..d6d36` | `206e00c0d1fc0000000a2b485e2a4ef900002a00` |
| `dd4d0..dd574` | `4eb9000482961d7c005a00182cbc000dd4e2532e00186b0000044e754eb9000482c0303c19d54eb900003af8303c07384eb900003af83b7c000154182cbc000dd51243f90010b1d60ca9fffa000000086f00000a04a9000040000008237c00000000000c202e007690a900080c8007b00000650000082cbc000dd5742d40007643f90010d2560ca9ffffa00000086f00000a04a9000004000008237c00000000000c4e75` |

- [F] 범위에서 뺀 바이트: TRAP `b4db0`(`4e4f`)+문자열 `b4db2..b4dc2` `NULL ITEM ERROR\0`; TRAP `b4e46`(`4e4f`)+문자열 `b4e48..b4e5a` `NULL ITEM ERROR2\0\0`; `b4d88..b4da6`(다른 진입 3개), `b4dca..b4df2`(그 경로).
- [F] 자료: `b516c` LONG 8개(`000b507c 000b50b8 000b50f4 000b5130 000b509a 000b50d6 000b5112 000b514e`, item record 포인터), `4a9e2` BYTE 표(`4b646 LEA 4a9e2(PC)`), record(`b507c..`)의 `+0..+7`(`1aa7e`/`4b586`의 두 LONG), `+a` WORD(`4b50c`), `+c` LONG(`4b51e`), `+12..+19`(`b4fec`/`b4ff0`), `+8`/`+a` WORD(`4b644`/`4b65a`). 모두 physical window로만 읽는다(F1 결정 6).

## block 목록과 실행 의미

[F] 105 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 live 레지스터를 쓰고 index `(An,Dn.W)`·`ADDA.W`는 부호확장한다. MOVE.B/MOVE.W Dn·ADD.W·SUB.W·SWAP·LSR.W 등은 나머지 bit를 보존한다.

**C2 `1aa7e`(화면 범위 판정, C 반환) 14**
- `1aa7e`: `MOVE.L (A0)+,D0; MOVE.L (A0)+,D1; BTST #1,15(A6); BEQ 1aa90`
- `1aa8c`: `ADD.W D1,D0; NEG.W D0` (→`1aa90`)
- `1aa90`: `MOVE.W 46(A6),D2; CMP.W 4e(A6),D2; BEQ 1aaba; BMI 1aaae` (묶음: `1aa9c`. BMI는 (D2−M).W의 bit15)
- `1aaa0`: `ADD.W D0,D2; CMP.W 53f8(A5),D2; BGT 1aafc` (부호)
- `1aaaa`: `BRA 1aaba`
- `1aaae`: `ADD.W D0,D2; ADD.W D1,D2; CMP.W 53f6(A5),D2; BLT 1aafc` (→`1aaba`)
- `1aaba`: `SWAP D0; SWAP D1; BTST #0,15(A6); BEQ 1aacc`
- `1aac8`: `ADD.W D1,D0; NEG.W D0` (→`1aacc`)
- `1aacc`: `MOVE.W 42(A6),D2; CMP.W 4a(A6),D2; BEQ 1aaf6; BMI 1aaea` (묶음: `1aad8`)
- `1aadc`: `ADD.W D0,D2; CMP.W 53f4(A5),D2; BGT 1aafc`
- `1aae6`: `BRA 1aaf6`
- `1aaea`: `ADD.W D0,D2; ADD.W D1,D2; CMP.W 53f2(A5),D2; BLT 1aafc` (→`1aaf6`)
- `1aaf6`: `ANDI.B #fe,CCR; RTS` (C=Clear 생산)
- `1aafc`: `ORI.B #1,CCR; RTS` (C=Set 생산)

**`48296` 2**
- `48296`: `BCLR #5,5683(A5); BCLR #4,5683(A5); JSR 1c5b0`
- `482a8`: `RTS`

**C4 `4b50c`(C 반환) 6**
- `4b50c`: `CMPI.W #1,a(A3); BEQ 4b548`
- `4b516`: `TST.B 5b84(A5); BEQ 4b548`
- `4b51e`: `MOVEA.L c(A3),A4; CMPA.W #0,A4; BEQ 4b532` (CMPA.W는 부호확장: 32비트 비교)
- `4b52a`: `TST.W 32(A4); BEQ 4b548` (→`4b532`)
- `4b532`: `CLR.W 54(A6); BSET #7,61(A6); MOVE.B #19,5e(A6); ORI.B #1,CCR; RTS` (Set 생산)
- `4b548`: `ANDI.B #fe,CCR; RTS` (Clear 생산)

**C4 `4b54e`(접촉 bitmap 등록, C 반환) 39**
- `4b54e`: `MOVEA.L 56(A6),A3; CMPA.W #0,A3; BEQ 4b6be`
- `4b55a`: `BSR 4b50c`
- `4b55c`: `BCS 4b6be` (carry 소비)
- `4b560`: `LEA 5a(A6),A2; LEA 5746(A5),A4; TST.B 5744(A5); BPL 4b576`
- `4b570`: `ADDQ.W #1,A2; LEA 5918(A5),A4` (→`4b576`)
- `4b576`: `MOVE.B #ff,(A2); MOVE.W 1d0(A4),D4; CMPI.W #40,D4; BCC 4b6be` (무부호)
- `4b586`: `MOVE.B D4,D5; LSR.W #3,D5; NOT.W D5; ANDI.W #7,D5; MOVE.L (A3)+,D0; MOVE.L (A3)+,D1; BTST #1,15(A6); BEQ 4b5a2`
- `4b59e`: `ADD.W D1,D0; NEG.W D0` (→`4b5a2`)
- `4b5a2`: `ADD.W 46(A6),D0; SWAP D0; SWAP D1; BTST #0,15(A6); BEQ 4b5b8`
- `4b5b4`: `ADD.W D1,D0; NEG.W D0` (→`4b5b8`)
- `4b5b8`: `ADD.W 42(A6),D0; MOVE.W #ffe0,D6; MOVE.W #15f,D7; ADD.W D0,D1; CMP.W D7,D0; BGT 4b6be`
- `4b5cc`: `CMP.W D6,D1; BLT 4b6be`
- `4b5d2`: `SUB.W D6,D0; BGE 4b5da` (GE ⇔ 부호 D0.W(이전)≥D6.W)
- `4b5d8`: `CLR.W D0` (→`4b5da`)
- `4b5da`: `CMP.W D7,D1; BLE 4b5e2`
- `4b5e0`: `MOVE.W D7,D1` (→`4b5e2`)
- `4b5e2`: `SUB.W D6,D1; SWAP D0; SWAP D1; MOVE.W #100,D6; MOVE.W #1ff,D7; ADD.W D0,D1; CMP.W D7,D0; BGT 4b6be`
- `4b5f8`: `CMP.W D6,D1; BLT 4b6be`
- `4b5fe`: `SUB.W D6,D0; BGE 4b606`
- `4b604`: `CLR.W D0` (→`4b606`)
- `4b606`: `CMP.W D7,D1; BLE 4b60e`
- `4b60c`: `MOVE.W D7,D1` (→`4b60e`)
- `4b60e`: `SUB.W D6,D1; LSR.L #5,D0; LSR.L #5,D1; MOVE.W #7ff,D6; AND.W D6,D0; AND.W D6,D1; SUB.L D0,D1; LSL.L #3,D0; ADD.W D5,D0; LEA 60(A4,D0.W),A1` (→`4b626`)
- `4b626`: `BSET D4,(A1); LEA 8(A1),A1; DBRA D1,4b626` (BSET 메모리는 bit D4 mod 8, BYTE 읽고 씀)
- `4b630`: `SWAP D0; SWAP D1; ADD.W D5,D0; LEA (A4,D0.W),A1` (→`4b63a`)
- `4b63a`: `BSET D4,(A1); LEA 8(A1),A1; DBRA D1,4b63a`
- `4b644`: `MOVE.W (A3)+,D0; LEA 4a9e2(PC),A1; MOVE.B (A1,D0.W),D0; LSL.W #3,D0; ADD.W D5,D0; LEA a0(A4),A1; BSET D4,(A1,D0.W); MOVE.W (A3)+,D0; ASR.W #1,D0; BCC 4b66a` (C=ASR로 밀려난 bit0, 같은 block에서 소비)
- `4b662`: `LEA b8(A4),A1; BSET D4,(A1,D5.W)` (→`4b66a`)
- `4b66a`: `ASR.W #1,D0; BCC 4b678`
- `4b670`: `LEA c0(A4),A1; BSET D4,(A1,D5.W)` (→`4b678`)
- `4b678`: `ASR.W #1,D0; BCC 4b686`
- `4b67e`: `LEA c8(A4),A1; BSET D4,(A1,D5.W)` (→`4b686`)
- `4b686`: `MOVE.W 1d0(A4),D0; MOVE.B D0,(A2); MOVE.W D0,D7; LSL.W #2,D7; LEA d0(A4),A2; MOVE.L A6,(A2,D7.W); ADDQ.W #1,D0; MOVE.W D0,1d0(A4); BTST #6,10f000.L; BEQ 4b6be`
- `4b6aa`: `LEA 6(A3),A0` (→`4b6ae`)
- `4b6ae`: `MOVE.L #a2b,D7; JSR 4b784(PC)` (U7 실행부)
- `4b6b8`: `CMPI.W #8000,(A0); BNE 4b6ae`
- `4b6be`: `MOVEQ #0,D2; MOVEQ #0,D3; MOVE.B 5e(A6),D0; BEQ 4b6e2` (C=Clear 생산, 결정 2)
- `4b6ca`: `MOVE.B 5c(A6),D2; ADD.W D2,D2; MOVE.B 5d(A6),D3; ADD.W D3,D3; SUB.W 42(A6),D2; SUB.W 46(A6),D3; ORI.B #1,CCR` (Set 생산, →`4b6e2`)
- `4b6e2`: `RTS`

**node callback `b4d7e`(+`b4df8` `b4e1c` `b4e34`) 21**
- `b4d7e`: `MOVE.W #0,8c(A6); BRA b4da6`
- `b4da6`: `CMPI.W #4,76(A6); BCS b4dc2` (무부호. 실패 시 TRAP `b4db0`)
- `b4dc2`: `JSR b4fd4(PC)`
- `b4dc6`: `BRA b4df2`
- `b4df2`: `MOVE.L #b4df8,(A6)` (→`b4df8`)
- `b4df8`: `JSR 43e34` (callback 진입)
- `b4dfe`: `JSR 4b54e`
- `b4e04`: `CLR.B 5e(A6); BTST #7,61(A6); BNE b4e16`
- `b4e12`: `BRA b4e3a`
- `b4e16`: `MOVE.L #b4e1c,(A6)` (→`b4e1c`)
- `b4e1c`: `JSR 43e34` (callback 진입)
- `b4e22`: `JSR b4e6c(PC)` (경계 callee)
- `b4e26`: `BCC b4e30` (carry 소비; `b4e6c` 반환 C)
- `b4e2a`: `MOVE.L #b4e34,(A6)` (→`b4e30`)
- `b4e30`: `BRA b4e3a`
- `b4e34`: `JMP 2a00` (callback 진입, 자기 삭제)
- `b4e3a`: `MOVEA.L 56(A6),A0; CMPA.W #0,A0; BNE b4e5a` (0이면 TRAP `b4e46`)
- `b4e5a`: `JSR 1aa7e`
- `b4e60`: `BCC b4e6a` (carry 소비; `1aa7e` 반환 C)
- `b4e64`: `MOVE.L #b4e34,(A6)` (→`b4e6a`)
- `b4e6a`: `RTS`

**`b4fd4`(item 초기화) 6**
- `b4fd4`: `MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; LEA b516c(PC),A0; MOVEA.L (A0,D0.W),A0; MOVE.L A0,56(A6); ADDA.W #12,A0; MOVE.L (A0)+,8e(A6); MOVE.L (A0)+,92(A6); MOVE.W 7a(A6),54(A6); BNE b5004` (Z=옮긴 WORD)
- `b4ffe`: `BSET #7,61(A6)` (→`b5004`)
- `b5004`: `TST.W 78(A6); BNE b501c`
- `b500c`: `MOVE.W #3,D0; JSR 49a84` (F3b → `49a58` RNG)
- `b5016`: `ADDQ.W #1,D0; MOVE.W D0,78(A6)` (→`b501c`)
- `b501c`: `CLR.B 9c(A6); MOVE.W 82(A6),D0; MOVE.B 84(A6),D1; MOVE.B 85(A6),D2; EXT.L D0; LSL.L #8,D0; MOVE.L D0,88(A6); MOVE.B D1,9a(A6); MOVE.B D2,9b(A6); RTS`

**stub 2**
- `c6a90`: `JMP 2a00`
- `d6d22`: `MOVEA.L c0(A6),A0; ADDA.L #a,A0; MOVE.L A0,5e2a(A5); JMP 2a00`

**node callback `dd4d0`(+`dd4e2` `dd512`) 15**
- `dd4d0`: `JSR 48296`
- `dd4d6`: `MOVE.B #5a,18(A6); MOVE.L #dd4e2,(A6)` (→`dd4e2`)
- `dd4e2`: `SUBQ.B #1,18(A6); BMI dd4ec` (callback 진입. N=결과 BYTE bit7)
- `dd4ea`: `RTS`
- `dd4ec`: `JSR 482c0` (경계 callee)
- `dd4f2`: `MOVE.W #19d5,D0; JSR 3af8`
- `dd4fc`: `MOVE.W #738,D0; JSR 3af8`
- `dd506`: `MOVE.W #1,5418(A5); MOVE.L #dd512,(A6)` (→`dd512`)
- `dd512`: `LEA 10b1d6,A1; CMPI.L #fffa0000,8(A1); BLE dd52c` (callback 진입. 부호 LONG)
- `dd524`: `SUBI.L #4000,8(A1)` (→`dd52c`)
- `dd52c`: `MOVE.L #0,c(A1); MOVE.L 76(A6),D0; SUB.L 8(A1),D0; CMPI.L #7b00000,D0; BCS dd54c` (무부호)
- `dd546`: `MOVE.L #dd574,(A6)` (→`dd54c`. `dd574`는 경계 callback)
- `dd54c`: `MOVE.L D0,76(A6); LEA 10d256,A1; CMPI.L #ffffa000,8(A1); BLE dd56a`
- `dd562`: `SUBI.L #400,8(A1)` (→`dd56a`)
- `dd56a`: `MOVE.L #0,c(A1); RTS`

## 구현 범위와 규약

- routing 12 범위(위 표). 짝수 PC 525개 중 block 시작 105, 내부 420(묶인 PC `1aa9c` `1aad8` 포함). 내부 PC 직접 진입은 `unsupported animation objects u01 PC`다. TRAP·문자열 바이트는 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤)다.
- **carry 소비 block 3개**: `4b55c`(`4b50c`), `b4e26`(`b4e6c`, 경계), `b4e60`(`1aa7e`). Unknown이면 `objects u01 caller requires known carry`.
- **known carry 생산 block 6개**: Clear `1aaf6` `4b548` `4b6be`, Set `1aafc` `4b532` `4b6ca`(앞 둘은 RTS까지 같은 block, `4b6ca`·`4b6be`는 `4b6e2 RTS`로 넘김).
- **FLOW_ONLY 26개**(C 보존): `1aaaa` `1aae6`(BRA), `48296`(BCLR+JSR), `482a8`, `4b55a`(BSR), `4b55c`, `4b6aa`(LEA), `4b6e2`, `b4dc2` `b4dc6` `b4df8` `b4dfe` `b4e12` `b4e1c` `b4e22` `b4e26` `b4e30` `b4e34` `b4e5a` `b4e60` `b4e6a`, `b4ffe`(BSET), `c6a90`, `dd4d0` `dd4ea` `dd4ec`. 그 밖(MOVE/MOVEQ/CLR/TST/CMP/CMPI/CMPA/ADD/SUB/SUBI/SUBQ/NEG/SWAP/LSR/LSL/ASR/AND/ANDI/NOT/EXT, `ADDQ.W #1,A2`·`ADDA` block, DBRA block)은 Unknown이다(기존 관례).
- 부호 비교: `BGT`/`BLT`/`BLE`(CMP.W·CMPI.L)는 부호 정수 비교, `BCS`/`BCC`(CMPI)는 무부호, `BMI`(`1aa90`·`1aacc`의 묶음, `dd4e2`)는 결과 bit15/bit7이다. `BGE` after `SUB.W`는 부호 비교다(N⊕V).
- 반복: `4b626`/`4b63a` DBRA는 D1.W+1회(최대 65,536). `4b6ae..4b6b8`은 `(A0)`=`8000` WORD까지 `4b784`를 반복한다. 원본대로 두고 block budget(1,000,000)만 한계다.
- 홀수 주소 WORD/LONG 접근과 work RAM 밖 쓰기는 기존 checked 오류(원본은 주소 오류·ROM 쓰기)다. port 쓰기는 U01 자체에 없다(callee 몫).
- I/O: RAM 절대 주소 `10f000`(BTST bit6, [I] debug flag), `10b1d6`·`10d256`(+8 LONG, +c LONG), d16(A5) `5683` `5b84` `5744` `5746+1d0..` `5918+1d0..` `53f2..53f8` `5418` `5e2a`.
- 회귀 탐침: [F] `engine/tests/animation_machine_area_clear_test.cpp`의 outside 탐침 `0x4b6e2`는 U01 block 시작이 된다. 아무 문서에도 없는 미연결 `0x5f03e`로 바꾼다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, F2 프레임 패스 Unicorn, 142 seed 120/400 frame)에서 U01 callback node 실행: `b4d7e` 62, `b4df8` 4,696, `c6a90` 2, `d6d22` 22, `dd4d0` 2, `dd4e2` 170. TB 포함 기준으로 105 block 중 67개가 자연 도달한다. 미도달 38개(fixture 필요): `1aa8c` `1aaa0` `1aaaa` `1aadc` `1aae6` `4b51e` `4b52a` `4b532` `4b59e` `4b604` `4b662` `4b678` `4b67e` `4b6aa` `4b6ae` `4b6b8` `4b6ca` `b4e16` `b4e1c` `b4e22` `b4e26` `b4e2a` `b4e30` `b4e34` `b4e64` `b4ffe` `b5016` `dd4ec` `dd4f2` `dd4fc` `dd506` `dd512` `dd524` `dd52c` `dd546` `dd54c` `dd562` `dd56a`.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 105 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 block 값, 그 밖 Unknown), 소비 block의 Unknown 오류, zero-step, 내부 420 PC 정확한 오류, TRAP 2개 stop·rollback, 홀수 PC, 경계 callee/callback(`b4e6c` `482c0` `dd574`) 오류. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, 합성 ROM 자료)로 비교한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`): 이전에 일치하던 pass가 모두 그대로 일치하고, 완주 seed가 25→39(새 14: 2 3 52 53 54 55 72 73 74 75 112 113 114 115)여야 한다. 2·3은 frame 0 RNG guard 정지(결정 4).

## 미확인·범위 밖

1. [I] `b4d7e`는 item 객체(문자열 `NULL ITEM ERROR`), `4b54e`는 접촉 bitmap(64 slot, `1d0` count), `1aa7e`는 화면 범위 판정이다. 게임 의미는 미확인이다.
2. [U] `b4e6c`(`b4ed0 JSR d(PC,D0.W)` 표 `b4f1e`)와 `482c0`, callback `dd574`는 U01 밖이다.
3. [U] `4a9e2` 표 길이(record `+8` WORD index의 상한)는 정적으로 정하지 않았다. 읽기는 bus가 막는다.

작업자 scratch: 세션 scratchpad `f4u01/`(`u01.py` block·범위·SHA 계산, `dis_u01.py`, `callers.py`, `reach.py`; 저장소 밖).
