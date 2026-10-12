# 객체 callback F4 N07(옛 U24): `9baf2`·`bbb9e` 객체 callback, 설치 callback `9bbf8`·`9bfba`·`bbd3c`·`9bf1e`와 공용 꼬리 `9ad06` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N07 행(`9ad06..9ad34` `9baf2..9bc74` `9bf1e..9c0b6` `bbb9e..bbdc0`, callback `9baf2` `9bbf8` `bbb9e` `bbd3c`, 경계 callee `1aa40` `4970a` `d3802`, bank 2, 새 seed 56 57)과 메인 결정 1·2(이름 `objects-n07`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 원 범위(`animation-machine-object-callbacks-f4-scope.md`, SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U24 행이다. 단위 형식과 규약은 N05 계약(SHA256 `403b0b6ba157097695918182b971b2411e645072f39802a51b5ca5e728104cf3`)과 N04 계약(SHA256 `80e41996735a39feeb7f89ddbb4e3267d993bc4a1431a214f2be4af2e05a31e3`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다(N05 `bdd3e` 선례).
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 실행부 없는 경계다.
- U01~N05 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BSET`/`BTST`)만인 block과 callee C를 소비하는 block은 FLOW_ONLY다. 블록 경계를 건너는 N/Z 재계산은 선행이 유일할 때만 허용한다(N07에는 필요 없음, 아래). checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N07 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 자료(`200128`, `2001d8`)는 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n07`(HEAD `0fecfff` = N05까지 통합, `engine/src/animation_machine.cpp` SHA256 `56ddfb9e81245d22a923117b48358c06f8108585963618d1d9deb7836e568579`, routing 규칙 62개)을 참조했다. N07 범위의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N06(`491b6..491c4` `b9dc6..b9f96` `ba196..ba3b6` `d9bcc..d9c0a` `e90d8..e90f2` `eb774..eb7b6`)과 겹치지 않는다. N06 PC 중 `491b6`만 N07에서 호출한다(아래 경계). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n07/n07.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] N07은 **block 시작 125개**다. 코드 4 범위, 1,386바이트, 296명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx·I/O port 쓰기·bank 변경은 없다. routing 짝수 PC는 693개, 내부 PC는 568개다. 범위 안의 모든 명령이 진입에서 정적으로 도달된다(미도달 명령 0).
  - 재범위 N07 행의 124와 차이 1은 fall-through 설치 대상 `9bfba`(`9bfae`의 `MOVE.L #9bfba,(A6)` 뒤 이어짐)다. 재범위 함수 본문 디코더(`rescope/build.pkl`의 함수 `9baf2` `9bbf8` `9bf1e` `bbb9e` `bbd3c` leader 합집합 124)와 비교하면 차이는 이것뿐이다(결정 1).
  - `9bf1e..9bf6c`(12 block)는 이 단위 진입에서 도달하지 않는다. 유일한 참조는 범위 밖 `9bf18`의 `MOVE.L #9bf1e,(A6)`(설치, `9befa` 사슬 = `9bc74` 사슬 안)이다. 참조가 있는 설치 callback 본문이고 재범위가 함수 `9bf1e`로 이 범위에 넣었으므로 routing한다(결정 2). 400 frame 안에는 실행되지 않는다.
  - 범위에서 빼는 이웃: `9ad04`(RTS, 다른 함수 `9acd8`), `9ad34..`(다른 함수), `9baf0`, `9bc74..9bf1e`(설치 callback `9bc74`의 사슬, 이 단위 밖), `9c0b6`(stage event 표 `e8e20`의 별도 callback `JMP 2a00.L`), `bbb9c`, `bbdc0..`(자료, `d3802`에 A1로 넘김), U16 `bbe12..`.
- [F] 함수:
  - 노드 callback `9baf2`(stage event 표 LONG `e8e24`; 앞 `9c0b6`, 뒤 `9c390`), `bbb9e`(LONG `e8f6c`; 앞 `bb9c4`, 뒤 U16 `bbe12`).
  - `MOVE.L #imm,(A6)` 설치 callback: `9bbf8`(`9bbf2`), `9bfba`(`9bfae`), `bbd3c`(`bbd36`) — 셋 다 fall-through로 바로 이어진다. 범위 밖 `9bf18`이 설치하는 `9bf1e`.
  - 공용 꼬리 `9ad06`: 이 단위의 `9bc70` `9bf68` `9c0b2`와 범위 밖 `BRA.W` 12곳(`9ae52` `9aeec` `9af64` `9b0c8` `9b13a` `9b504` `9b58c` `9b622` `9b6dc` `9b768` `9bd3e` `9bef6`)이 들어온다. 앞 `9ad04`는 RTS다.
- [F] **경계 callee(실행부 없음)**: `4970a`(`9c046` `9c074`, 원 범위 N14), `491b6`(`9c056`, 동시 진행 N06 범위 — N06 병합 뒤 routing됨), `d3802`(`bbd8a`), `1aa40`(`bbda2`). 범위 밖 설치 대상 `9bc74`(`9bc5c`의 `MOVE.L #9bc74,(A6)`, 다음 frame에 실행)와 `28ae` 자식 `9b370`(`9c02a`) `9b164`(`9c05c`)는 노드 LONG에 저장만 하고 이 단위가 제어를 넘기지 않는다. `bba7e` `bbb3e`(`7a(A6)` LONG)는 U09 `4706c`가 쓰는 자료 주소다.
- [F] **나가는 호출(routing됨)**: U05 `c6a96`(`9bafe` `bbbde` `bbc32` `bbc78` `bbcbe` `bbd04`), U14 `4a496`(`9bb08` `bbbae`), cleanup `43e34`(`9bb72` `bbd3c`), U12 `4c0ac`(`9bb88`)·`492c8`(`9bc44` `9bf3e` `9bfda`), interpreter `49f8c`(8곳)·`49fc6`(`9bc4a` `9bf62` `9bffe` `bbd42`), U04 `43ea4`(`9bc3e` `9bf38` `9bfd4`), sound `3af8`(`9bf70` `bbd6e`), U11 `490ba`(`9bfa8` `9c01e`), fade_card `28ae`(`9c034` `9c066`, C 반환)·`2a00`(`JMP`), U05 `1ab02`(`9ad22`, C 반환), U01 `4b54e`(`bbd52`, C 반환), stage area `49a58`(`bbd74`), N05 `1a3ae`(`bbd80`), cleanup `46ef4`(`bbd90`), U09 `4706c`(`bbdb8`).
- [F] **flag**:
  - 블록 경계를 건너는 C 소비 block **4개**: `9ad28`(`BCC`, `1ab02` 반환: U05 `1ab7a` Clear / U01 `1aafc` Set), `9c03a` `9c06c`(`BCC`, `28ae` 반환: `2908` ORI Set / `290e` ANDI Clear), `bbd58`(`BCC`, U01 `4b54e` 반환: `4b6be` Clear / `4b6ca` Set).
  - known carry 생산 block **2개**: `9c04c` `9c07a`(`ORI.B #1,CCR` 한 명령, 경계 `4970a` 복귀점, fall-through로 `9c050`/`9c07e`) → Set. 뒤 block이 `MOVE`로 시작하므로 소비자는 없다.
  - N/Z 재계산 block 없음: 모든 Bcc의 N/Z/V는 같은 block 안의 명령이 만든다.
  - block 안에서 만들고 쓰는 flag: `TST.W 96/92(A6); BEQ`(`9ad06` `9ad12`), `MOVE.W 80(A6),D0; BNE`(`9bb0e`), `TST.W 76(A6); BNE`(`9bb5a`), `CMPI.W #0/#1,78(A6); BNE`(`9bb68` `9bb7e`), `TST.W 78(A6); BEQ/BNE`(`9bb8e` `9bbf8`), `CMP.W 7a(A6),D0; BLE`(부호 WORD, `9bc00`), `TST.L 3a(A6); BMI/BPL`(`9bc1a` `9bc2e`), `CMP.W 7c(A6),D0; BLT`(부호 WORD, `9bc50`), `CMPI.W #2,78(A6); BNE`(`9bc5c`), `MOVE.L D0,D1; BPL`(LONG N, `9bf1e` `9bfba`), `CMP.L 86/82(A6),D1; BGE`(부호 LONG, `9bf2a` `9bfc6`), `CMPI.B #3,D0; BPL`(결과 BYTE bit 7, `9bf44` `9bfe0`), `MOVE.B #3,D0; BLE`(`9bf52` `9bfee`, MOVE 뒤 N=Z=V=0이라 **항상 not taken**), `BTST.B #0,15(A6); BNE`(`9bf76` `9c07e`), `TST.W 90(A6); BEQ`(`9c004`), `SUBQ.W #1,9a(A6); BCC`(borrow, `9c00c`), `MOVE.W 76(A6),D0; BNE`(`bbbb4`), `CMPI.W #1~#4,D0; BNE`(`bbc10` `bbc64` `bbcaa` `bbcf0`), `CMPI.W #1,76(A6); BGT`(부호, `bbd48`), `BTST.B #7,61(A6); BEQ`(`bbd60`), `MOVE.L 7a(A6),D0; BEQ`(`bbdae`).
- [F] 읽는 자료(모두 live bus):
  - bank window LONG `200128`(`9bba0` `9bbcc` → `22(A6)`; 그 LONG + `48`/`10`의 LONG을 A1로), `2001d8`(`bbbee` `bbc42` `bbc88` `bbcce` `bbd14` → `22(A6)`; + `88`/`8c`/`90`/`94`/`98`). 재범위의 bank 2는 이 두 LONG이다.
  - 이 단위가 직접 읽지 않고 주소만 넘기는 fixed ROM 자료: `9ac86`(`1ab02` 사각형 `ffe0 fff0 0040 0040`), `9c0bc`(`49f8c` 목록, A1), `cc22c`(`490ba` 표, A0), `bbdc0`(`d3802`, A1), `bba7e`/`bbb3e`(`7a(A6)`).
  - work RAM: node WORD `1e` `20` `32` `46` `54` `68` `76` `78` `7a` `7c` `7e` `80` `90` `92` `94` `96` `9a`, LONG `(A6)` `22` `36` `3a` `7a` `82` `86`, BYTE `15` `5e` `61` `9e`; 자식 node(`28ae` 반환 A0) WORD `2e` `32` `9a` `a0`; A5 WORD `5418`.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준): RNG 초기화+응답 `80` 400 frame과 base 120 frame 모두 seed 56·57만 N07에 들어오고 TB 시작 54개를 실행한다(`9baf2` `bbb9e` frame 0, `9bbf8` `bbd3c` frame 1부터, `9ad1e` frame 48부터). `9bc5c` `9bc6c` `9bf1e` 계열, `9bf6c`~`9c0b2`, `9bbc2` `9bbea`, `bbd5c`, `bbd6a`~`bbda8` 등은 자연 미도달이며 typed fixture와 실제 ROM 차분으로 덮는다. 자연 경로에서는 경계 `4970a` `491b6` `d3802` `1aa40`과 설치 `9bc74`가 실행되지 않는다.
- [F] seed 56·57의 기준 첫 미연결 callback은 `9baf2`(frame 0, node 5)다. [I] N07로 두 seed가 base·RNG 모두 완주할 것으로 본다(검증에서 확인). N06이 없어도 `491b6`은 자연 경로에 없으므로 영향이 없다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 125(재범위 N07 행 124와 차이 1).** fall-through 설치 대상 `9bfba`를 시작으로 센다(결정 3, N05 `bdd3e` `dcf22` 선례).
2. **`9bf1e..9bf6c`(설치 callback `9bf1e`, 12 block) routing.** N03/N05의 "참조 없는 코드"가 아니다(범위 밖 `9bf18`의 설치 참조). 재범위 함수 목록에도 있다. 넣지 않으면 범위 `9bf1e..9c0b6`을 `9bf6c..9c0b6`으로 줄이고 113 block이 된다. 이 계약은 넣는다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n07.cpp`의 `animation_objects_n07_block`. 오류는 `unsupported animation objects n07 PC`(내부 PC), `objects n07 caller requires known carry`(소비 4 block). 메인 지시와 같다.
4. **N06 경계 `491b6`.** 이 작업 트리에서는 routing 밖이라 `9c050`이 `491b6`로 넘어가면 `unsupported animation machine PC`다. 단위 test는 `491b6`에서 멈춤만 확인한다(F4 test 경계 관례). N06 병합 순서와 무관하다.
5. **bank 자료.** bank LONG(`200128` `2001d8`과 그 + offset LONG)은 live bus로 읽는다(N05 결정 6과 같음). test는 합성 bank 바이트를 쓴다(ROM 자료를 test에 넣지 않음).
6. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`에서 N07 범위 PC를 경계·rollback 기대로 쓰는 곳은 없다(scratch grep).

## 원본 바이트 근거

[F] 코드 4 범위 합계 1,386바이트. 범위 순서로 이어 붙인 SHA256 `c50060169e0108e8a2b4c493b7149ecacf547a7b4e5b2a2137cee15489991737`.

| CPU 범위 | 바이트 | SHA256 | 시작 | 내용 |
| --- | --- | --- | --- | --- |
| `9ad06..9ad34` | 46 | `b081107633c1efbc47781dcee6e66a7ad618caae4a0df5f794c2b0b2c8b5bdd1` | 8 | 공용 꼬리 `9ad06` |
| `9baf2..9bc74` | 386 | `deef296b4c307244d4a50512cbd4c330de3a01a5fa96dcef43aad021949d53f1` | 32 | callback `9baf2`, 설치 `9bbf8` |
| `9bf1e..9c0b6` | 408 | `95ce71525e43d21bdcd0a74f679dc3bea1ffa6b37501a05e8103d299fbddd0ed` | 46 | 설치 `9bf1e`, `9bf6c` 계열, 설치 `9bfba` |
| `bbb9e..bbdc0` | 546 | `13639dd84b25c921f867f77ef9332a51427db46cb0e1d3cebf812b2b6e02d59b` | 39 | callback `bbb9e`, 설치 `bbd3c` |

## block 목록과 실행 의미

[F] 125 block. 각 줄은 block 안 명령 전체다. "(→x)"는 fall-through다. d16(An)은 부호확장한다. `.W`/`.B` 연산은 나머지 bit를 보존한다. `ASR.L #3`은 부호 bit를 채운다. `EXT.L`은 WORD 부호확장이다. 부호 비교는 2의 보수로 명시 계산한다.

**공용 꼬리 `9ad06` 8**
- `9ad06`: `TST.W 96(A6); BEQ.W 9ad12` / `9ad0e`: `SUBQ.W #1,96(A6)` (→`9ad12`)
- `9ad12`: `TST.W 92(A6); BEQ.W 9ad1e` / `9ad1a`: `SUBQ.W #1,92(A6)` (→`9ad1e`)
- `9ad1e`: `LEA 9ac86(PC),A0; JSR 1ab02.L` / `9ad28`: `BCC.W 9ad32`(C 소비) / `9ad2c`: `JMP 2a00.L` / `9ad32`: `RTS`

**callback `9baf2` 32**
- `9baf2`: `MOVE.W #49,D0; MOVE.W #4,D1; MOVE.B #0,D2; JSR c6a96.L` / `9bb04`: `MOVE.W #c7d,D0; JSR 4a496.L`
- `9bb0e`: `MOVE.W #800,68(A6); MOVE.W #800,1e(A6); MOVE.W #a0,54(A6); MOVE.W 7a(A6),94(A6); MOVE.W 7c(A6),92(A6); MOVE.W 7e(A6),90(A6); MOVE.W 80(A6),D0; BNE.W 9bb4e`
- `9bb3a`: `MOVE.L #30000,82(A6); MOVE.L #30000,86(A6); BRA.W 9bb5a` / `9bb4e`: `EXT.L D0; LSL.L #8,D0; MOVE.L D0,86(A6); MOVE.L D0,82(A6)` (→`9bb5a`)
- `9bb5a`: `TST.W 76(A6); BNE.W 9bb68` / `9bb62`: `BSET.B #0,15(A6)` (→`9bb68`)
- `9bb68`: `CMPI.W #0,78(A6); BNE.W 9bb7e` / `9bb72`: `JSR 43e34.L` / `9bb78`: `MOVE.W 46(A6),7a(A6)` (→`9bb7e`)
- `9bb7e`: `CMPI.W #1,78(A6); BNE.W 9bb8e` / `9bb88`: `JSR 4c0ac.L`
- `9bb8e`: `TST.W 78(A6); BEQ.W 9bbc2`
- `9bb96`: `LEA 26(A6),A0; MOVE.W #b3,20(A6); MOVE.L 200128.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 48(A1),A1; JSR 49f8c.L` (bank) / `9bbbe`: `BRA.W 9bbf2`
- `9bbc2`: 같은 꼴, `MOVEA.L 10(A1),A1` (bank) / `9bbea`: `MOVE.L #ffffc000,3a(A6)` (→`9bbf2`)
- `9bbf2`: `MOVE.L #9bbf8,(A6)` (→`9bbf8`)
- `9bbf8`(설치): `TST.W 78(A6); BNE.W 9bc3e`
- `9bc00`: `MOVE.L 3a(A6),D0; ASR.L #3,D0; SUB.L D0,3a(A6); MOVE.W 46(A6),D0; SUBI.W #100,D0; CMP.W 7a(A6),D0; BLE.W 9bc2e` (D0 상위 WORD는 ASR 결과의 상위 WORD로 남는다)
- `9bc1a`: `TST.L 3a(A6); BMI.W 9bc2a` / `9bc22`: `SUBI.L #8000,3a(A6)` (→`9bc2a`) / `9bc2a`: `BRA.W 9bc3e`
- `9bc2e`: `TST.L 3a(A6); BPL.W 9bc3e` / `9bc36`: `ADDI.L #8000,3a(A6)` (→`9bc3e`)
- `9bc3e`: `JSR 43ea4.L` / `9bc44`: `JSR 492c8.L` / `9bc4a`: `JSR 49fc6.L`
- `9bc50`: `MOVE.W 5418(A5),D0; CMP.W 7c(A6),D0; BLT.W 9bc70`
- `9bc5c`: `MOVE.L #9bc74,(A6); CMPI.W #2,78(A6); BNE.W 9bc70` / `9bc6c`: `BRA.W 9bf6c` / `9bc70`: `BRA.W 9ad06`

**설치 callback `9bf1e` 12**
- `9bf1e`: `MOVE.L 3a(A6),D0; MOVE.L D0,D1; BPL.W 9bf2a` / `9bf28`: `NEG.L D1` (→`9bf2a`)
- `9bf2a`: `CMP.L 86(A6),D1; BGE.W 9bf38` / `9bf32`: `ASR.L #3,D0; ADD.L D0,3a(A6)` (→`9bf38`)
- `9bf38`: `JSR 43ea4.L` / `9bf3e`: `JSR 492c8.L`
- `9bf44`: `MOVE.W 3a(A6),D0; CMPI.B #3,D0; BPL.W 9bf52` / `9bf50`: `NEG.W D0` (→`9bf52`)
- `9bf52`: `MOVE.B #3,D0; BLE.W 9bf5e`(항상 not taken) / `9bf5a`: `MOVE.B #3,D0` (→`9bf5e`)
- `9bf5e`: `MOVE.B D0,9e(A6); JSR 49fc6.L` / `9bf68`: `BRA.W 9ad06`

**`9bf6c` 계열 34(`9bc6c`에서 진입, 설치 `9bfba`)**
- `9bf6c`: `MOVE.W #188e,D0; JSR 3af8.L`
- `9bf76`: `MOVE.L #4000,36(A6); BTST.B #0,15(A6); BNE.W 9bf8c` / `9bf88`: `NEG.L 36(A6)` (→`9bf8c`)
- `9bf8c`: `MOVE.W #b3,20(A6); MOVEA.L #9c0bc,A1; MOVE.W #100,D0; JSR 49f8c.L`
- `9bfa2`: `LEA cc22c.L,A0; JSR 490ba.L`
- `9bfae`: `MOVE.W D0,D0; MOVE.W D0,9a(A6); MOVE.L #9bfba,(A6)` (→`9bfba`)
- `9bfba`(설치)~`9bffa`: `9bf1e`~`9bf5e`와 같은 꼴(`36(A6)`, `82(A6)`): `9bfba` `9bfc4` `9bfc6` `9bfce` `9bfd4` `9bfda` `9bfe0` `9bfec` `9bfee` `9bff6` `9bffa`
- `9c004`: `TST.W 90(A6); BEQ.W 9c0b2` / `9c00c`: `SUBQ.W #1,9a(A6); BCC.W 9c0b2`
- `9c014`: `SUBQ.W #1,90(A6); LEA cc22c.L,A0; JSR 490ba.L`
- `9c024`: `MOVE.W D0,D0; MOVE.W D0,9a(A6); MOVEA.L #9b370,A0; MOVE.W #a,D0; JSR 28ae.L` / `9c03a`: `BCC.W 9c050`(C 소비)
- `9c03e`: `MOVE.W #0,D0; MOVE.W #0,D1; JSR 4970a.L`(경계) / `9c04c`: `ORI.B #1,CCR` (→`9c050`, Set 생산)
- `9c050`: `MOVE.W #0,9a(A0); JSR 491b6.L`(경계, N06)
- `9c05c`: `MOVEA.L #9b164,A0; MOVE.W #14,D0; JSR 28ae.L` / `9c06c`: `BCC.W 9c07e`(C 소비)
- `9c070`: `CLR.W D0; CLR.W D1; JSR 4970a.L`(경계) / `9c07a`: `ORI.B #1,CCR` (→`9c07e`, Set 생산)
- `9c07e`: `MOVE.W #1,a0(A0); MOVE.W #0,D0; BTST.B #0,15(A6); BNE.W 9c09e`
- `9c092`: `SUBI.W #40,D0; ADD.W D0,2e(A0); BRA.W 9c0a6` / `9c09e`: `SUBI.W #40,D0; SUB.W D0,2e(A0)` (→`9c0a6`)
- `9c0a6`: `MOVE.W 32(A6),D0; SUB.W 7a(A6),D0; MOVE.W D0,32(A0)` (→`9c0b2`) / `9c0b2`: `BRA.W 9ad06`

**callback `bbb9e` 39**
- `bbb9e`: `MOVE.W 78(A6),68(A6); MOVE.W 78(A6),1e(A6); MOVE.W #e5c,D0; JSR 4a496.L`
- `bbbb4`: `MOVE.L #0,7a(A6); MOVE.W 76(A6),D0; BNE.W bbc10`
- `bbbc4`: `MOVE.L #bba7e,7a(A6); MOVE.W #12c,54(A6); MOVE.W #75,D0; MOVE.W #22,D1; MOVE.B #0,D2; JSR c6a96.L` / `bbbe4`: 2001d8 + `88` 애니메이션 (bank) / `bbc0c`: `BRA.W bbd36`
- `bbc10`: `CMPI.W #1,D0; BNE.W bbc64` / `bbc18`: `MOVE.L #bbb3e,7a(A6); MOVE.W #12c,54(A6)`; `c6a96`(`75`,`23`) / `bbc38`: + `8c` (bank) / `bbc60`: `BRA.W bbd36`
- `bbc64`: `CMPI.W #2,D0; BNE.W bbcaa` / `bbc6c`: `c6a96`(`75`,`24`) / `bbc7e`: + `90` / `bbca6`: `BRA.W bbd36`
- `bbcaa`: `CMPI.W #3,D0; BNE.W bbcf0` / `bbcb2`: `c6a96`(`75`,`25`) / `bbcc4`: + `94` / `bbcec`: `BRA.W bbd36`
- `bbcf0`: `CMPI.W #4,D0; BNE.W bbd36` / `bbcf8`: `c6a96`(`75`,`26`) / `bbd0a`: + `98` / `bbd32`: `BRA.W bbd36`
- 애니메이션 block은 `LEA 26(A6),A0; MOVE.W #213,20(A6); MOVE.L 2001d8.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L k(A1),A1; JSR 49f8c.L`이다.
- `bbd36`: `MOVE.L #bbd3c,(A6)` (→`bbd3c`)
- `bbd3c`(설치): `JSR 43e34.L` / `bbd42`: `JSR 49fc6.L`
- `bbd48`: `CMPI.W #1,76(A6); BGT.W bbdae` / `bbd52`: `JSR 4b54e.L` / `bbd58`: `BCC.W bbd60`(C 소비) / `bbd5c`: `CLR.B 5e(A6)` (→`bbd60`)
- `bbd60`: `BTST.B #7,61(A6); BEQ.W bbdae`
- `bbd6a`: `MOVE.W #1a31,D0; JSR 3af8.L` / `bbd74`: `JSR 49a58.L` / `bbd7a`: `ANDI.W #3,D0; ADDQ.W #2,D0; JSR 1a3ae.L`
- `bbd86`: `LEA bbdc0(PC),A1; JSR d3802.L`(경계) / `bbd90`: `JSR 46ef4.L` / `bbd96`: `MOVE.L #18000,D0; MOVE.L #fffe8000,D1; JSR 1aa40.L`(경계) / `bbda8`: `JMP 2a00.L`
- `bbdae`: `MOVE.L 7a(A6),D0; BEQ.W bbdbe` / `bbdb6`: `MOVEA.L D0,A0; JSR 4706c.L` / `bbdbe`: `RTS`

(수: 8 + 32 + 12 + 34 + 39 = 125.)

## 구현 범위와 규약

- routing 4 범위(위 표). 짝수 PC 693개 중 block 시작 125, 내부 568. 내부 PC 직접 진입은 `unsupported animation objects n07 PC`다.
- **FLOW_ONLY 39개**(C 보존): `9ad1e` `9ad28` `9ad2c` `9ad32` `9bb62` `9bb72` `9bb88` `9bbbe` `9bc2a` `9bc3e` `9bc44` `9bc4a` `9bc6c` `9bc70` `9bf38` `9bf3e` `9bf68` `9bfa2` `9bfd4` `9bfda` `9c03a` `9c06c` `9c0b2` `bbc0c` `bbc60` `bbca6` `bbcec` `bbd32` `bbd3c` `bbd42` `bbd52` `bbd58` `bbd60` `bbd74` `bbd86` `bbd90` `bbda8` `bbdb6` `bbdbe`.
- **known carry 생산 2개**: `9c04c` `9c07a` Set.
- 그 밖 84개는 Unknown(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDI`/`SUB`/`SUBI`/`SUBQ`/`ADDQ`/`NEG`/`ASR`/`LSL`/`EXT`/`ANDI` block, `MOVE.L #imm,(A6)` block, banked 애니메이션 block, `MOVEA`+`MOVE.W`+`JSR 28ae` block).
- **소비자 4개**(`9ad28` `9c03a` `9c06c` `bbd58`). Unknown이면 `objects n07 caller requires known carry`(상태 보존).
- 스택: JSR 복귀 LONG만. I/O port 쓰기·bank 변경 없음. 홀수 주소 WORD/LONG(예: 홀수 A6/A0), work RAM 밖 쓰기, 미해결 ROM/bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] N07 → 기존: 위 "나가는 호출" 목록. 실행부 없는 경계 `4970a` `491b6` `d3802` `1aa40`(멈춤만 test).
- [F] 다른 단위 → N07: stage event 표 LONG `e8e24`(`9baf2`) `e8f6c`(`bbb9e`), 범위 밖 `BRA.W 9ad06` 12곳(아직 routing 없음), `9bf18` 설치(`9bf1e`). 기존 test·도구 중 N07 PC를 경계로 기대하는 곳 없음.

## 자연 시작 상태(읽기 전용 기록)

- [F] 기준 C++ 차분(scratch `ms5-scratch/n07/basetree` = `0fecfff` 원본 사본, 현재 `tools/verify_animation_machine_scheduler_f4.py`·`_rng_f4.py`를 scratch 출력으로 실행): base 일치 pass 12,488·node 97,198, 불일치 0, 자연 완주 115 seed(seed 56·57의 첫 미연결 callback `9baf2`, frame 0). RNG 초기화 400 frame: 일치 pass 39,200·node 285,501, 불일치 0, complete 98(SHA256 `0df67edc57cd2aa2e0adc122f64396f553b9de1355977ea63dc40be6bb1895ae`).

- [F] 작업자 scratch 측정(구현 후, 같은 도구): base 일치 pass 12,728·node 100,052, 불일치 0, 자연 완주 117(새 완주 56 57, 회귀 0; 두 seed 모두 120 frame 끝까지 일치). RNG 초기화 400 frame: 일치 pass 40,000·node 291,715, 불일치 0, complete 100(새 complete 56 57, 잃은 것 0; SHA256 `971417c63b29438f16e54b4ee17c706fa21db7c075be673f3a8d2bdf22edaab5`).
- [F] 실제 ROM 차분(scratch `realrom/real7.py`, 시드 1·2·3 각 1,000 case, bank `200000`/`300000`): 불일치 0, 125/125 시작 도달, 실제 생산자 뒤 소비자 native 분기 비교 `9ad28` 1,562 `9c03a` 333 `9c06c` 11 `bbd58` 411(세 시드 합). 경계 멈춤 `4970a` 251 `491b6` 167 `d3802` 278 `1aa40` 33. native가 깨끗이 멈추지 않은 case(무작위 RAM의 interpreter 경로가 `<400` PC로 가거나 멈추지 않음)는 건너뛰고 셌다(시드별 446~474).
- [F] 단위 test `animation_machine_objects_n07_test`: 378 fixture(checked 오류 12, known C 유지 53), 125 block × 3 carry, 내부 568 PC, UBSan 통과.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 125 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류, zero-step, 내부 568 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 범위 밖 이웃 중 routing 밖이고 다른 F4 단위가 아닌 자료(`bbdc0`)는 `unsupported animation machine PC`, 경계 `4970a` `491b6` `d3802` `1aa40`과 설치 대상 `9bc74`는 멈춤만, 소비자 4개 Unknown 오류, 생산자 `9c04c` `9c07a` Set, 소비자 C는 실제 생산자(`1ab02` `28ae` `4b54e`)를 지나는 실제 ROM 차분의 native 분기로 확인. 자연에 없는 길은 typed fixture(Unicorn, work RAM 입력과 합성 bank 바이트)로 비교한다.
- 실제 ROM 차분: callback과 모든 시작을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다(bank `200000`/`300000`).
- 차분(F2 프레임 패스, 142 seed): 불일치 0, 회귀 0, seed 56·57 완주. RNG 초기화 400 frame 차분: 불일치 0, seed 56·57 complete.

## 미확인·범위 밖

1. [I] `9baf2`는 `7a`/`7c`/`7e`/`80` 인자로 목표 높이(`7a`→`94`), 진행 문턱(`7c`, `5418(A5)`와 비교), 자식 수(`7e`→`90`), 속도 상한(`80`→`82`/`86`)을 받는 비행 객체로 보인다. `78` = 0/1/2가 종류(정리 `43e34`, U12 `4c0ac`, 문턱 뒤 `9bf6c` 분기)를 고른다. `9bf6c` 계열은 `cc22c` 표 간격(`490ba`)마다 `28ae` 자식 `9b370`·`9b164`를 만든다. 게임 의미는 미확인이다.
2. [I] `bbb9e`는 `76`(0~4)으로 팔레트·애니메이션을 고르는 정지 객체로, `76` ≤ 1이면 접촉(`4b54e`, BYTE `61` bit 7)에 소리 `1a31`, 무작위 `1a3ae`, 경계 `d3802`(`bbdc0` 자료)·`1aa40`을 거쳐 사라진다. [U] `d3802` `1aa40` `4970a` `9bc74` `9b370` `9b164`는 이 단위 밖이다.
3. [I] `9bf52`/`9bfee`의 `BLE`는 직전 `MOVE.B #3,D0` 때문에 분기하지 않는다(원본 의도는 상한 3 고정으로 보임). 원본대로 구현한다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n07/`(`n07.py` block·범위·SHA 계산, `cls.py` carry 분류, `n07dis.py` `hroute.py` `refs7.py`, `fp/` 기준·새 프레임 패스 차분; 저장소 밖).
