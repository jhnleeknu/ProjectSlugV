# 객체 callback F4 U16: 지형 보조 `b0106` `b0206` `b02c8`, 객체 callback `bbe12`(설치 `bbe74`), 대기 callback `f1a0e`(설치 `f1a1a`) 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U16 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`, `4b54e` 반환 C), U13 계약(SHA256 `20af72d0d12a571f1d36590bc9e36348b596de54d948320364c7721f71e2c53e`, 같은 형식의 `f1a4e`), U14 계약(SHA256 `22952574c990f88d5da5d9104286d505a09ce424b2cfbd35ed17d340fd34b9db`), U15 계약(U15a, SHA256 `7ca5ae307416e101d30291c9406ff267769fee8c2109d33f4f51ac4c44740400`, `b0106`/`b0206`의 C 소비자)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee와 다른 단위의 PC는 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U15 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U16에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BTST`)만인 block과 callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. `ADDQ`/`SUBQ` block은 Unknown이다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U16의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. banked window 자료(`2001d8`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u16`(HEAD `e670b53` = U01~U14 WIP, `engine/src/animation_machine.cpp` SHA256 `d9910f04678efa514e3a33eb98a382da03a6fbb0b798fe72902a03ac67285e21`, routing 규칙 49개)을 참조했다. U15(작업 트리 `metalslug-u15`, U15a 계약 위 SHA)는 이 작업 트리에 없으므로 U15 소유 PC(`4c29a` `4950e`, 범위 `b0062..b0106` 등)는 경계로 둔다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u16/u16.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U16은 **block 시작 39개**다. 범위 문서 U16 행의 39와 같다. 범위 문서 `units.pkl`의 함수 7개(`b0106` `b0206` `b02c8` `bbe12` `bbe74` `f1a0e` `f1a1a`)의 본문이다.
  - 지형 보조 `b0106` 6, `b0206` 5, `b02c8` 5(이 셋은 U15 `af078` 계열과 범위 밖 `af0c6`~`af646`·`b02b8`이 부른다).
  - 객체 callback `bbe12` 18(설치 callback `bbe74` 포함), 대기 callback `f1a0e` 5(설치 callback `f1a1a` 포함).
  - 코드 5 범위, 430바이트, 97명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx는 없다. routing 짝수 PC는 215개, 내부 PC는 176개다.
  - 범위 문서의 TB 기준 시작과 정적 시작이 같다(F4 범위 재생의 범위 안 TB 시작 중 정적 시작이 아닌 것 0개).
- [F] **경계 callee(실행부 없음) 2개**: `49214`(`bbeb8` `bbee6` `JSR`, U21 범위), `d3802`(`bbef2 JSR`). 범위 문서 "경계 callee 2"(`bound=2:49214 d3802`)와 같다. 이와 별도로 **U15 소유 PC 2개**: `4c29a`(`b0106 JSR`), `4950e`(`b0206 JSR`)는 U15 병합 전 경계다.
- [F] 기존 실행부로 나가는 호출: U12 `4c0ac`(`bbe12`), U05 `c6a96`(`bbe18`), interpreter `49f8c`(`bbe3c`)·`49fc6`(`bbe7a`), U14 `4a496`(`bbe64`), cleanup `43e34`(`bbe74`), U01 `4b54e`(`bbe80`), sound `3af8`(`bbe98`), buffer_cue `2986`(`bbea2` `bbec4`), fade_card `2a00`(`bbefc JMP`, `f1a34 JMP`)·`28ae`(`f1a24`), U08 `43eb8`(`b0122`), U08b `4be34`(`b012c`). U16 안 호출은 없다(`b0218 BRA.W b0226`만).
- [F] **flag**:
  - 블록 경계를 건너는 C 소비 block 2개: `b020c BCS`(U15 경계 `4950e`가 돌려준 C), `bbe86 BCC`(U01 `4b54e`가 돌려준 C, U13 `b819c`와 같은 생산자).
  - known carry 생산 block 4개: `b011a`(`ANDI.W #8,D6`: C=0), `b0144`(`ORI.B #1,CCR`: C=1), `b0210`(`ORI.B #1,CCR`: C=1), `b021c`(`ANDI.B #fe,CCR`: C=0). 이어지는 RTS `b014e` `b0226`은 C를 보존한다. [F] 소비자는 호출자 바로 뒤 명령이다: `b0106` 호출 2곳(`af14c`→`af150 BCS`, `af426`→`af42a BCS`, 둘 다 U15a 범위), `b0206` 호출 4곳 중 3곳(`af44e`→`af452 BCC`, `af4c0`→`af4c4 BCC`(U15a), `af646`→`af64a BCC`(범위 밖)); `af0d2`의 다음 명령은 `JSR`(소비 없음).
  - `b02c8`의 마지막 C(`b02e6 LSR.B`)는 호출자 5곳(`af0c6` `af442` `af4b4` `af63a` `b02b8`) 다음 명령이 모두 `MOVE.B`라 소비되지 않는다. Unknown으로 둔다.
  - block 안에서 만들고 쓰는 flag: `b011a`(`ANDI` 뒤 `BEQ`), `b02c8`(`BTST` 뒤 `BEQ`), `b02de`(`TST.B` 뒤 `BPL`), `bbe8a`(`BTST` 뒤 `BEQ`), `f1a1a`(`SUBQ.W` 뒤 `BCS`, borrow = WORD가 0).
- [F] 읽는 자료: banked window LONG `2001d8`(→ `22(A6)`, `bbe3c`), 이어 그 값 + `80`의 LONG(→ A1, `49f8c` 인자). 주소만 넘기는 상수: `d1d38` `38ba0`(→`2986` A0, 자식 callback), `100bf4`(→`2986` A1), `bbf04`(→`d3802` A1), `4841a`(→`28ae` A0). U16이 직접 읽는 fixed ROM 자료는 없다. I/O port 쓰기와 bank 변경은 U16 자체에 없다.
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base(`f4scope/dyn`) 25 block, RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`) 27 block. seed 18 19 96 97 102 103은 U15 `af078` 계열을 통해 `b0106` `b0206` `b02c8`과 `bbe12`에, 96 97 102 103은 `f1a0e`에도 닿는다. seed 56 57은 `bbe12` 계열에만 닿는다(먼저 U24 `9baf2`에서 멈춤).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **U15 의존.** `b0106`은 `JSR 4c29a`로, `b0206`은 `JSR 4950e`로 시작한다. 둘 다 U15a 범위다. U15 병합 전에는 두 진입이 첫 명령 뒤에 곧바로 경계에서 멈추고, `b020c`의 C 소비는 U15 실행부가 돌려준 known C로만 확인할 수 있다. 또 `b0106`/`b0206`/`b02c8`을 부르는 자연 경로는 모두 U15 `af078` 계열을 지난다. [F] 범위 문서의 새 자연 seed 18 19 96 97 102 103은 frame 0에서 U16 `bbe12`보다 먼저 `af078` 노드를 지나고, 그 노드는 U15 범위 `4578a..45c94`·`46198`(scratch `f4scope/dyn`의 미연결 시작 `4578a 45792 45904 45922 45afe 45b1a 45b28 45c94 46198`)을 쓴다. 이 부분은 U15a(작업 트리 `metalslug-u15` `1eea746`)에 없다. 따라서 U16 단독이나 U15a+U16 조합으로는 이 여섯 seed가 완주하지 않는다(96 97 102 103은 `f1a0e`를 지나 `af078` 노드에서 멈춘다). 권고: U16은 `4c29a` `4950e`를 경계로 두고, 새 자연 완주는 U15 나머지(`4578a` 계열) 병합 뒤 다시 잰다.
2. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u16.cpp`의 `animation_objects_u16_block`. 오류는 `unsupported animation objects u16 PC`(내부 PC), `objects u16 caller requires known carry`(`b020c` `bbe86`에 C가 Unknown으로 들어올 때). 메인 지시와 같다.
3. **bank 자료와 파생 읽기.** `MOVE.L 2001d8.L,22(A6)`는 live bus로 읽는다. 이어 `MOVEA.L 22(A6),A1; MOVEA.L 80(A1),A1`은 노드에 방금 쓴 LONG을 다시 읽고 그 값 + `80`의 LONG을 live bus로 읽는다(bank window 또는 fixed ROM; 그 밖은 기존 checked 오류). [F] bank `200000`에서 `2001d8`=`002d4b72`, 그 + `80`(`2d4bf2`)=`002d5076`; bank `300000`이면 `01000000`(+`80`은 bus 밖: checked 오류); bank `400000`이면 `00223c88`(+`80` → `00000100`). test에는 합성 bank 바이트를 쓴다(ROM 자료를 test에 넣지 않음).
4. **`bbec4`의 A0.** `bbec4 MOVE.W #e0ed,68(A0)`의 A0는 경계 `49214`가 돌려준 값이다. U16만으로는 `bbeb8`이 `49214`에서 멈추므로 `bbec4`는 typed fixture(선언 A0)로만 실행한다.
5. **무효화 탐침.** [F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`(이 작업 트리와 메인 트리)에서 U16 범위 안 PC를 rollback·outside 탐침으로 쓰는 곳은 없다(`probes.py`: `animation-machine-caller-inventory.md` 232행의 caller 나열 `0bbe7a`, 입력 stream 자원 `f01fe..f1a0e`의 배타 끝 `f1a0e`(`tools/pack_input_streams.py` 등 13곳, `input-sampler.md`)뿐, 탐침 아님). 교체 탐침(`5ff00` 이후)은 필요 없다.

## 원본 바이트 근거

[F] 코드 5 범위 합계 430바이트. 범위 순서로 이어 붙인 SHA256 `245eefd71011342c80cd7671d2d74fbcab885fe7502b653c34b447fabffb58a7`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `b0106..b0150` | 74 | `0faf846794c0ef27439a03b2a3f40735c1b890f25644bc2c8df5efccd5cb0574` | 지형 보조 `b0106` |
| `b0206..b0228` | 34 | `1cbc052707eaf5a77fbfc32c17468dc76b12d88b5bad6da95a9331968d555751` | 지형 보조 `b0206` |
| `b02c8..b02ec` | 36 | `ecc77bf4ceb9422e99e5e6ee0fd0a17202102b2673c67a332a6de54b8c006b33` | 방향 보조 `b02c8` |
| `bbe12..bbf04` | 242 | `19047d611c47f78520b13868e17b56d0c9433ba428010079a7b142d493ed8996` | callback `bbe12`, 설치 callback `bbe74` |
| `f1a0e..f1a3a` | 44 | `b579d21d344e037aec342fefd2a426e9abf75b1b05a96d3203defee5ee9233bc` | callback `f1a0e`, 설치 callback `f1a1a` |

- [F] 범위 밖 이웃(routing 밖): `b0062..b0106`(U15a 범위, `b0104 RTS`로 끝남), `b0150..`(다른 함수 `MOVE.L 3e(A6),-(A7)`), `b01fa..b0206`(앞 함수 꼬리), `b0228..`(다른 함수), `b02b6..b02c8`(호출자 `b02b8 BSR.W b02c8`가 있는 앞 함수), `b02ec..`(다른 함수), `bbb9e..bbdbe`(U24 범위), `bbdbe..bbe12`(앞 함수와 자료; `bbe12` 앞 바이트는 명령 경계와 맞지 않는다), `bbf04..`(자료: `d3802` 인자 표), `f1a00..f1a0e`(입력 stream 자원 끝), `f1a3a`(`JMP` 뒤 도달하지 않는 `RTS`, 범위 밖), `f1a3c..f1a4e`(자료: LONG `f1a48`=`000f1a0e`), `f1a4e..`(U13).
- [F] 참조: `bbe12`는 LONG 상수 `e8f70`(stage event 표, 앞 칸 `e8f6c`=`bbb9e`), `f1a0e`는 LONG 상수 `f1a48`, `bbe74`·`f1a1a`는 범위 안 `MOVE.L #imm,(A6)`(`bbe6e` `f1a14`)가 설치한다. `b0106` 호출 2곳(`af14c` `af426` `JSR d16(PC)`), `b0206` 호출 4곳(`af0d2` `af44e` `af4c0` `af646`), `b02c8` 호출 5곳(`af0c6` `af442` `af4b4` `af63a` `b02b8` `BSR.W`).
- [F] 자료(모두 live bus):
  - banked window: LONG `2001d8`(결정 3), 그 값 + `80`의 LONG.
  - work RAM 노드 d16(A6): WORD `46`(읽기), LONG `3e`(→A1) `32`(읽기) `3a`(쓰기) `36`(CLR.L), BYTE `9e`(쓰기), LONG `76`(쓰기, `b0210` `b021c`), BYTE `15`(BTST bit 0, `b02c8`), WORD `68` `1e` `54` `20`(쓰기), LONG `22`(쓰기·읽기), BYTE `5e`(CLR) `61`(BTST bit 7), WORD `76`(`f1a0e` 쓰기, `f1a1a` SUBQ). LONG `(A6)`(callback 설치 `bbe74` `f1a1a`).
  - 다른 노드 d16(A0): WORD `68` `1e`(`bbec4`, A0는 `49214` 반환 값).
- [F] 스택: JSR 복귀 LONG만. push/pop 없음.

## block 목록과 실행 의미

[F] 39 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.B`·`.W` 연산은 나머지 bit를 보존하고 `MOVEQ`는 LONG 전체를 쓴다.

**지형 보조 `b0106` 6**
- `b0106`: `MOVEQ #0,D0; MOVEQ #0,D1; MOVEQ #0,D2; MOVE.W #200,D3; SUB.W 46(A6),D3; JSR 4c29a.L` (U15 경계)
- `b011a`: `ANDI.W #8,D6; BEQ.W b014e` (C=0 생산; D6.W & 8 = 0이면 `b014e`)
- `b0122`: `MOVEA.L 3e(A6),A1; JSR 43eb8.L` (U08; FLOW_ONLY)
- `b012c`: `SUB.L 32(A6),D1; ADDI.L #80000,D1; MOVE.L D1,3a(A6); CLR.L 36(A6); JSR 4be34.L` (U08b)
- `b0144`: `LSR.W #8,D4; MOVE.B D4,9e(A6); ORI.B #1,CCR` (C=1 생산, →`b014e`)
- `b014e`: `RTS` (C 보존)

**지형 보조 `b0206` 5**
- `b0206`: `JSR 4950e.L` (U15 경계; FLOW_ONLY)
- `b020c`: `BCS.W b021c` (`4950e` 반환 C 소비; C=1이면 `b021c`)
- `b0210`: `MOVE.L A0,76(A6); ORI.B #1,CCR; BRA.W b0226` (C=1 생산)
- `b021c`: `MOVEQ #0,D0; MOVE.L D0,76(A6); ANDI.B #fe,CCR` (C=0 생산, →`b0226`)
- `b0226`: `RTS` (C 보존)

**방향 보조 `b02c8` 5**
- `b02c8`: `ASR.W #8,D0; BTST.B #0,15(A6); BEQ.W b02de` (D0.W 산술 8 bit 오른쪽; BYTE `15` bit 0이 0이면 `b02de`)
- `b02d4`: `SUBI.B #40,D0; NEG.B D0; ADDI.B #40,D0` (→`b02de`; D0.B = `80` − D0.B mod 256)
- `b02de`: `TST.B D0; BPL.W b02e6` (D0.B bit 7이 0이면 `b02e6`)
- `b02e4`: `NEG.B D0` (→`b02e6`)
- `b02e6`: `ADDQ.B #8,D0; LSR.B #4,D0; RTS` (D0.B = (D0.B + 8 mod 256) >> 4)

**객체 callback `bbe12` 18**
- `bbe12`: `JSR 4c0ac.L` (callback 진입; U12; FLOW_ONLY)
- `bbe18`: `MOVE.W #1,68(A6); MOVE.W #1,1e(A6); MOVE.W #c8,54(A6); MOVE.W #75,D0; MOVE.W #20,D1; MOVE.B #0,D2; JSR c6a96.L` (U05)
- `bbe3c`: `LEA 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 80(A1),A1; JSR 49f8c.L` (bank 자료; interpreter)
- `bbe64`: `MOVE.W #e5d,D0; JSR 4a496.L` (U14)
- `bbe6e`: `MOVE.L #bbe74,(A6)` (→`bbe74`)
- `bbe74`: `JSR 43e34.L` (설치 callback 진입; cleanup; FLOW_ONLY)
- `bbe7a`: `JSR 49fc6.L` (interpreter; FLOW_ONLY)
- `bbe80`: `JSR 4b54e.L` (U01; FLOW_ONLY)
- `bbe86`: `BCC.W bbf02` (`4b54e` 반환 C 소비; C=0이면 `bbf02`)
- `bbe8a`: `CLR.B 5e(A6); BTST.B #7,61(A6); BEQ.W bbf02` (BYTE `61` bit 7이 0이면 `bbf02`)
- `bbe98`: `MOVE.W #1a2a,D0; JSR 3af8.L` (sound)
- `bbea2`: `MOVEA.L #d1d38,A0; MOVE.W #14,D0; MOVEA.L #100bf4,A1; JSR 2986.L` (buffer_cue 자식 생성)
- `bbeb8`: `MOVE.W #0,D0; MOVEQ #10,D1; JSR 49214.L` (경계)
- `bbec4`: `MOVE.W #e0ed,68(A0); MOVE.W #e0ed,1e(A0); MOVEA.L #38ba0,A0; MOVE.W #0,D0; MOVEA.L #100bf4,A1; JSR 2986.L`
- `bbee6`: `MOVE.W #0,D0; MOVEQ #40,D1; JSR 49214.L` (경계)
- `bbef2`: `LEA bbf04(PC),A1; JSR d3802.L` (경계; FLOW_ONLY)
- `bbefc`: `JMP 2a00.L` (fade_card 자기 삭제; FLOW_ONLY)
- `bbf02`: `RTS` (FLOW_ONLY)

**대기 callback `f1a0e` 5**
- `f1a0e`: `MOVE.W #294,76(A6); MOVE.L #f1a1a,(A6)` (callback 진입, →`f1a1a`)
- `f1a1a`: `SUBQ.W #1,76(A6); BCS.W f1a24` (설치 callback 진입; 감소 전 WORD가 0이면 `f1a24`)
- `f1a22`: `RTS` (FLOW_ONLY)
- `f1a24`: `MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L` (fade_card 자식 생성)
- `f1a34`: `JMP 2a00.L` (FLOW_ONLY)

(수: 6 + 5 + 5 + 18 + 5 = 39.)

## 구현 범위와 규약

- routing 5 범위(위 표). 짝수 PC 215개 중 block 시작 39, 내부 176. 내부 PC 직접 진입은 `unsupported animation objects u16 PC`다. 경계 callee `49214` `d3802`, U15 PC `4c29a` `4950e`와 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **FLOW_ONLY 15개**(C 보존): `b0122`(MOVEA+JSR), `b014e` `b0226` `bbf02` `f1a22`(RTS), `b0206` `bbe12` `bbe74` `bbe7a` `bbe80`(JSR), `bbef2`(LEA+JSR), `bbefc` `f1a34`(JMP), 소비자 `b020c` `bbe86`(단독 Bcc).
- **known carry 생산 4개**: `b011a` Clear(`ANDI.W`), `b0144` Set, `b0210` Set, `b021c` Clear. 그 밖 20개(MOVE/MOVEQ/SUB/ADDI/CLR/LSR/ASR/BTST+MOVE 결과/SUBI/NEG/TST/ADDQ/SUBQ, `MOVE.L #imm,(A6)` block)는 Unknown이다.
- **소비자 2개**: `b020c`, `bbe86`. 들어오는 C가 Unknown이면 `objects u16 caller requires known carry`(상태 보존).
- 루프 없음. I/O port 쓰기 없음. bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM 읽기, physical span 밖 bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U16 → 기존: U12 `4c0ac`, U05 `c6a96`, interpreter `49f8c` `49fc6`, U14 `4a496`, cleanup `43e34`, U01 `4b54e`, sound `3af8`, buffer_cue `2986`, fade_card `28ae` `2a00`, U08 `43eb8`, U08b `4be34`.
- [F] U16 → 경계: `49214`(U21), `d3802`, U15 `4c29a` `4950e`. 자식 callback `d1d38` `38ba0`(`2986`), `4841a`(`28ae`)는 쓰기만 하고 실행하지 않는다.
- [F] 다른 단위 → U16: U15a `af146`/`af3de` 계열(`af14c` `af426` `af442` `af44e` `af4b4` `af4c0`), 범위 밖 `af0c6` `af0d2` `af63a` `af646` `b02b8`; stage event 표 `e8f70`(`bbe12`), LONG `f1a48`(`f1a0e`).

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed, TB 기준)에서 U16 block에 닿는 seed:
- `bbe12` 계열: base seed 18 19 56 57 96 97 102 103(`bbe74`는 56 57만), RNG+`80` 변형에서 같은 seed(`bbe74`는 모두).
- `b0106` `b0206` `b02c8`: seed 18 19 96 97 102 103(U15 `af078` 계열이 부름). `b0210`은 어느 변형에서도 닿지 않는다(`4950e`가 늘 C=1을 돌려줌). `b0226`은 TB 기준으로 `b021c`와 한 TB여서 따로 세지 않았다(fall-through로 실행됨). `b02d4`는 RNG+`80` 변형에서만.
- `f1a0e`: seed 96 97 102 103, `f1a1a`는 RNG+`80` 변형에서만. `f1a24` `f1a34`는 400 frame 안에 닿지 않는다(`76`=`294`=660 frame).
- 39 block 중 TB 기준 base 25개, RNG+`80` 변형 27개가 자연 도달한다. RNG+`80` 변형의 미도달 12개(`b0210` `b0226` `bbe8a` `bbe98` `bbea2` `bbeb8` `bbec4` `bbee6` `bbef2` `bbefc` `f1a24` `f1a34`)는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(작업 트리 `e670b53`, F2 프레임 패스 142 seed): 일치 pass 10,498개·node 79,624개, 불일치 0, 자연 완주 89 seed. 첫 미연결 callback `f1a0e` 4(seed 96 97 102 103), U15 `af078` 2(18 19), U24 `9baf2` 2(56 57). RNG 초기화 400 frame 차분: 일치 pass 23,688개·node 159,409개, 불일치 0, complete 59.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 39 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산자 known, 그 밖 Unknown; 소비자는 Unknown이면 오류), zero-step, 내부 176 PC 정확한 오류, 홀수 PC, 경계 `49214` `d3802`·U15 `4c29a` `4950e` stop(U15·U21 PC는 stop만), rollback 탐침은 `5f6xx..5ffxx`만. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 bank 바이트)로 비교한다.
- 실제 ROM 차분: `bbe12` 전체(실제 `4c0ac` `c6a96` `49f8c` `4a496`, bank `200000`), `bbe74`→`bbe86`(실제 `43e34` `49fc6` `4b54e` 반환 C로 소비 분기 확인)→`bbe8a`~`bbefc`(실제 `3af8` `2986`), `b011a`~`b014e`(실제 `43eb8` `4be34`, 반환 C와 native C 비교), `b020c`~`b0226`(선언 C), `b02c8` 전체, `f1a0e`/`f1a1a`/`f1a24`를 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 기준 이상, 불일치 0, complete 59 이상. U15+U16 조합은 scratch로 따로 잰다(결정 1).

## 미확인·범위 밖

1. [I] `b0106`은 U15 `4c29a`(지형 탐색으로 보임)의 D6 bit 3이 서면 `43eb8`/`4be34`로 노드 위치(`3a` = D1 − `32` + `80000`)를 다시 잡고 D4 상위 BYTE를 `9e`에 둔 뒤 C=1, 아니면 C=0을 돌려주는 착지 판정으로 보인다. 게임 의미는 미확인이다.
2. [I] `b0206`은 U15 `4950e`의 결과가 C=0이면 A0(찾은 대상)를 `76`에 두고 C=1, 아니면 `76`=0과 C=0을 돌려준다.
3. [I] `b02c8`은 D0.W 상위 BYTE(각도)를 좌우 반전 bit(`15` bit 0)로 접고 절댓값을 16단계(`(x+8)>>4`)로 바꾸는 방향 index로 보인다.
4. [I] `bbe12`는 등장 연출 객체(animation `213`, bank 표 `2001d8`+`80`, palette `e5d`)를 만들고, 매 frame cleanup·animation·`4b54e` 판정 뒤 BYTE `61` bit 7이 서면 효과음 `1a2a`와 자식 `d1d38` `38ba0`, `49214`/`d3802` 연출을 일으키고 스스로 지워진다(`2a00`).
5. [U] 경계 `49214` `d3802`와 U15 `4c29a` `4950e`의 본문과 실행 결과는 U16 밖이다.

작업자 scratch: 세션 scratchpad `f4u16/`(`u16.py` block·범위·SHA 계산, `scope.py` `trav.py` `hroute_u16.py` `dis_u16.py`, `refs.py` `nextins.py` `probes.py` `reach.py`; 저장소 밖).
