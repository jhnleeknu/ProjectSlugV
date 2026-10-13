# 객체 callback F4 N23: `420be` 자식 이동 callback, `4db42` 화면 판정 자식(`4da4a`/`4da50` 생성), player 판정 `4d2d4`/`4d36e`, `484b4` `4d508` `4d766` `4d900`, stage event callback `c3a7c` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N23 행(185 block, `420be..42460` `484b4..484ca` `4d2d4..4d418` `4d766..4d77e` `4d900..4dbdc` `c3a7c..c3c1c`, callback `420be` `4db42` `4db8e` `c3a7c` `c3b4a`, 경계 `c3ce` `4c2fa` `4d958` `e9112`, 간접 `4d38a` `4dbb0`, X `42370 ADDX.B`, bank 2, 새 seed RNG 38 39)과 N22 계약(`animation-machine-objects-n22-contract.md`, SHA256 `f23ddd7fa4d7aba26604366bdaf26ff982d532a55ce70badb9efcea15870d4aa`)의 메인 결정 4(`4da4a..4da74`를 N35에서 N23으로 옮김)다. 단위 형식과 규약은 N22 계약을 따른다. N 재계산은 N13 계약(SHA256 `e93eeddb8701c3e90216ae1f1c55a047726e3242b3e82959c0d21edc9e29d632`)의 `5b326` 선례(같은 `CMPI.W #8000,D1; BNE; SPL` 꼴)를 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 분기를 각 선행에 접어 넣음).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다. N22a의 경계 `484b4` `4d2d4` `4d508` `4d766`을 넣는다.
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. DIV 0 제수는 단위 checked 오류(N23에는 DIV가 없다).
- 계산 점프 표는 정적으로 묶고 전부 전사한다(N23에는 PC 상대 BRA.W 점프 표가 없다). LONG 포인터 표 + `JMP (An)`은 live bus 읽기 + live target(N22 결정 3).
- 설치·표 포함 뒤 ~220 block을 넘으면 나누고, seed 38 39가 쓰는 부분을 먼저 구현한다(N23은 198 block이라 나누지 않는다).

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치·`MOVEA.L #imm,A0`+`JSR 28ae` 자식, 범위 밖에서 참조하는 범위 안 진입)로 정한다. Unicorn TB 분할은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N22 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDI`/`ADDQ`/`SUB`/`SUBI`/`SUBQ`/`ANDI`/`EOR`/`NEG`/`NOT`/`EXT`/`SWAP`/`LSL`/`LSR`/`ASR`/`ADDX`/`CLR` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`ST`/`SCS`/`SPL`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `ORI`/`ANDI` CCR은 known Set/Clear 생산이다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N23 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`200098` `200088`과 그 표)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n23`(HEAD `22dd4ef` = N22a까지 통합 + interpreter `49fca`, `engine/src/animation_machine.cpp` SHA256 `a8ff43d8aad886e0a99714aa5f3813dca7ff7c598fe579804f6927724f84df1f`, routing 규칙 79개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`)을 참조했다. N23 routing 10 범위의 짝수 PC는 기존 routing에 없다(범위 앞 `420bc`(N22)·`484b2`, `4d9d6..4da08`(frame helpers)는 이웃이다). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n23/n23.py`(정적 디코드, `starts.txt`)와 `cls23.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N23 = 198 block**(10 routing 범위, 코드 2,104바이트, 짝수 PC 1,052, 내부 854). 진입 14개에서 분기·fall-through·범위 안 설치·`28ae` 자식을 끝까지 따라간 정적 closure다. 재범위 185는 400 frame 안에 실행되는 함수 본문만 센 값이고, `4d958`(재범위 "경계")·`4d508`(메인 지시)·`4da4a..4da74`(N22 결정 4)를 더하고 미참조 `4240a`를 뺀 값이다(결정 1).
- [F] 진입:
  - node callback: `420be`(N22 `420b6 MOVE.L #420be,(A6)`가 `41fe6` 자식에 설치), `4db42`(`4da56 MOVEA.L #4db42,A0; JSR 28ae` 자식), `c3a7c`(고정 ROM stage event LONG `e8ff0`).
  - 범위 안 설치: `4db8e`(`4db88`, fall-through), `c3b4a`(`c3b44`, fall-through).
  - 다른 단위가 부르는 함수: `484b4`(N22 `1bf02`; 범위 밖 `1fd30` `1ff24` `4d0e2`), `4d2d4`(N22 `3d340`; 범위 밖 `2ba0c` `2ceae` `30780` `331fc` `38c4e` `3fff4`), `4d508`(N22 `3d374`; 범위 밖 `2b960` `2ba3a` 등 11곳), `4d50e`(범위 밖 `481d8 JMP 4d50e`), `4d766`(N22 `3dc5a`; 범위 밖 `2c614` `30fba` `33abe` `3a436` `40848` 등), `4d900`(범위 밖 `3431c`), `4da4a`(범위 밖 `30744` `331ce`), `4da50`(N22 `3d316`; 범위 밖 `2b68e JMP` `38c1a`), `c3a9c`(범위 밖 `c3a58` 형제 callback의 `c3a78 BRA.W c3a9c`).
  - 범위 안 내부 callee: `4d36e`(`4d2dc`/`4d2ec BSR`), `4d900`(`4210c` `42410` `4dbca`), `4d958`(`4214e` `4241e`).
- [F] **경계(실행부 없음, 현재 routing 밖)**: `c3ce`(`42196`), `4c2fa`(`42314`), `e9112`(`c3ba6`). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **다른 실행부로 가는 callee**: `288c`(stage_event_ops), `289e`(readiness), `28ae` `2a00`(fade_card), `2986`(buffer_cue), `8ebe` `443d2`(U02), `1ab02` `c6a96`(U05), `1bf02` `1bfb4`(N22), `43e08` `43e34` `46ef4`(cleanup), `4706c`(U09), `49290`(U08), `4970a`(N14), `49a58`(stage_area), `49be0`(U06), `49f8c` `49fc6`(interpreter), `4a46c`(N04), `4a496`(U14), `4b54e`(U01), `4be06`(U11), `4be2c`(U18), `4c0ac`(U12). 레지스터 간접 `4d38a JSR (A1)`·`4dbb0 JSR (A1)`은 live target이다.
- [F] **범위 밖 설치·자식 값(실행 PC가 아님)**: `28ae` 자식 `42600`(`42332`), `d1d08`(`c3bb4`)·`d1d38`(`c3bda`)(N05 범위), `2986` 자식 LONG 표 `41f1e`(`24bf4` `24c0e` `24c58` `24de0`)·`42460`(`424b4` `424e6` `4251e`) 값, 자료 포인터 `c3a38` `c3a50`(`80`/`7c(A6)`).
- [F] **carry**(아래 "carry" 절): 소비 block 14개(FLOW 12 + `4d2e0`/`4d2f0` SCS 뒤 Unknown 2), known 생산 18개(`ORI` Set 12, `ANDI` Clear 4, 계산 2), FLOW_ONLY 62개(소비 12, 재계산 2 포함), Unknown 116개. 62 + 2 + 18 + 116 = 198.
- [F] **N/Z 재계산 2 block**(유일 선행): `4219c`(callee `c3ce`의 `TST.B (A0,D0.W)` Z, 결정 2), `42238`(`42228 CMPI.W #8000,D1`의 N, 결정 3).
- [F] X: `4236e ASR.B #3,D0; ADDX.B D1,D0`(같은 block 안에서 X 생산·소비). DIVx/MULx·PC 상대 BRA.W 점프 표·TRAP·I/O port 쓰기·bank 변경은 없다.
- [F] 스택: JSR/BSR 복귀 LONG, `4218e MOVEM.W D0,-(A7)`/`4219c MOVEM.W (A7)+,D0`(부호 확장 LONG), `422ee MOVE.L A0,-(A7)`/`42308 MOVEA.L (A7)+,A0`, `4232e MOVEM.L D0-D1/A1,-(A7)`/`42342 MOVEM.L (A7)+,D0-D1/A1`, `4d2e2 MOVE.W D7,-(A7)`/`4d2f2 MOVE.W (A7)+,D7`, `4da50 MOVE.L A0,-(A7); MOVEM.W D0-D1,-(A7)`/`4da66 MOVE.W (A7)+,76(A0); MOVE.W (A7)+,78(A0); MOVE.L (A7)+,7a(A0)`.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen23.py`): RNG 기록에서 seed 38 39(78 시작) 116 117(60 시작), base 기록에서 116 117만 N23 범위 PC를 실행한다. callback 실행 수(RNG, seed 38): `c3a7c` 2, `c3b4a` 170, `420be` 170, `4db42` 1, `4db8e` 84(116 117: `420be` 405, `4db42` 5, `4db8e` 400). `422bc`/`4243c`(`2986`)와 `4219c`(`c3ce` 뒤)·`4231a`(`4c2fa` 뒤)·`c3bac`(`e9112` 뒤)는 자연 400 frame에서 실행되지 않는다.
- [F] 기준(`22dd4ef`)에서 seed 38 39는 frame 0 callback `7086a` 안의 `c3a7c`에서 멈춘다(RNG 완주 130). [I] N23 뒤 38 39는 `c3a7c`→`c3b4a`·N22 `3d228`→`4da50`→`4db42`·`420be`를 지나 완주할 것으로 본다(검증 기록에서 확인). 116 117은 `38ba0`(N31)에서 먼저 멈춘다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 198 block(재범위 185와 차이).** [F] 재범위 N23 행의 `4d900..4dbdc`는 실행 함수 본문의 span이고, 그 안에 N23 진입에서 닿지 않는 함수가 있다.
   - 넣은 것: `4d958`(내부 `JSR` 대상, 4 block; 재범위는 실행되지 않는 경계로 셌다), `4d508..4d55e`(메인 지시, 7 block; 범위 밖 `481d8 JMP 4d50e`가 참조하는 `4d50e`도 시작), `4da4a..4da74`(N22 결정 4, 3 block), `c3a9c`(범위 밖 `c3a78 BRA.W c3a9c`가 참조하는 함수 중간 진입, 1 block).
   - 뺀 것(routing하지 않음): `4240a JMP 2a00`(앞 `42408 RTS` 뒤, 참조 0), `4d970..4d98a`(함수 `4d970`, 참조 0), `4da2a..4da4a`(`4da2a`, 참조 0), `4da74..4db18`(`4da74`·자식 `4da9e`, 참조 0).
   - **범위 밖 코드만 부르는 범위 안 helper**(N23 진입에서 닿지 않음): `4d98a`(`2c57e` `2d128` `319f0` `339ac` `3b624` `3e0a2` `40b46`), `4d9a2`(`1c09e`), `4d9ba`(`2c6c4` `2d1f4` `30f80` `33a44` `3a3c0` `4080e`), `4da08`(`1c054`, `1c058 BCC` 소비), `4db18`(`2c828` `3da62` `30c38`, 자식 `4dbdc`). 합계 18 block. N22 결정 8(`1bf6c..1bfb4`, "다른 단위 몫") 선례대로 **뺐다**. 넣으면 216 block이 되고, frame helpers test의 바깥 탐침 `4d9d4`·`4da08`(`animation_machine_frame_helpers_test.cpp` outside 목록)과 `tools/verify_animation_machine_frame_helpers.py`의 `outside_range_entry_04da08`이 무효가 된다(RAM 탐침으로 바꿔야 함). 권고: 지금은 빼고, 이 helper들을 부르는 단위(N22b `3da62`, N28~N33)에서 함께 정한다.
2. **`4219c` Z 재계산(callee Z, 유일 선행).** [F] `4218e`가 `MOVEM.W D0,-(A7); MOVE.W 90(A6),D0; JSR c3ce`로 부르고, `c3ce`(경계, 실행부 없음)는 `LEA 7024(A5),A0; ANDI.W #1,D0; TST.B (A0,D0.W); RTS`다. 복귀점 `4219c MOVEM.W (A7)+,D0; BEQ.W 421bc`는 `c3ce`의 Z를 읽는다(`MOVEM`은 CCR을 바꾸지 않는다). `4219c`의 선행은 `c3ce`의 `RTS` 하나다(`4219c` 참조는 `42196 JSR`의 복귀 LONG뿐). `TST`와 `4219c` 사이 `A0`·`D0`·메모리는 바뀌지 않으므로, `4219c` 진입의 `A0`·`D0.W`로 BYTE(`A0` + sext(`D0.W`))를 다시 읽어 Z = (BYTE = 0)로 정확히 재계산한다(그 뒤 `D0` = sext(pop WORD)). C 상태는 Z를 나타내지 않으므로 다른 방법이 없다. 이 읽기는 원본 `TST`와 같은 주소다(work RAM 밖이면 기존 checked 오류). Unicorn typed fixture에서 `4219c`를 직접 진입할 때는 SR Z를 이 식과 같게 둔다.
3. **`42238` N 재계산(유일 선행, N13 `5b326` 선례).** [F] `42238 SPL.B 82(A6)`는 `4222c BNE.W 42238`(block `42228 CMPI.W #8000,D1; BNE.W 42238`)의 분기 대상이고 다른 참조가 없다(`42230 BRA.W`는 `4223c`로 간다). N = bit 15 of (`D1.W` − `8000`) = NOT bit 15 of `D1.W`. `SPL`은 N = 0(곧 `D1.W` bit 15 = 1)이면 BYTE `ff`, 아니면 `00`을 쓴다. FLOW_ONLY다.
4. **`4d344` 계산 C 생산 + `4d35a` 소비.** [F] `4d35a BCC.W 4d366`은 `4d344 CMP.W D0,D1; BNE.W 4d35a`의 C를 읽는다(선행 유일). 재계산 대신 관례("CMP는 소비자가 있을 때 known 생산")대로 `4d344`를 계산 C 생산(C = `D1.W` < `D0.W`, 부호 없는 빌림; 두 출구 모두)으로, `4d35a`를 C 소비(FLOW, Unknown이면 checked 오류)로 둔다. native 분기(`4d35e`/`4d366`)로 확인한다.
5. **known C 생산과 실제 소비자.** [F] `484be`(Set)/`484c4`(Clear) → N22 `1bf0a`, N23 `4db9a`. `4d2fe`(Clear)/`4d310` `4d320` `4d350` `4d35e` `4d366`(Set) → N22 `3d34c`와 범위 밖 6곳(`2ba10` `2ceb2` `30784` `33200` `38c52` `3fff8`) `BCC`. `4d3a6` `4d40c`(Set)/`4d412`(Clear) → `4d2e0`/`4d2f0 SCS`. `4d77a`(계산: `ADD.B D1,D1`의 C = `D1.B` bit 7) → N22 `3dc5e`와 범위 밖 `2c618` `30fbe` `33ac2` `3a43a` `4084c` 등 `BCC`. `4d922` `4d948`(Set)/`4d950`(Clear) → ROM 안 소비자 없음(`42112` `42416` `4dbce` `34320`은 `TST.B D0`), `ORI`/`ANDI` 관례로 known. `c3bd2` `c3bf8`(Set) → 소비자 없음(`46ef4` 뒤 `JMP 2a00`), `ORI` 관례로 known. [F] RTS 앞 생산은 실제 ROM 소비자(`4dbb2 BCS.W 4dbd6`, `3d34c BCC.W 3d380`, `3dc5e BCC.W 3dc68`)를 복귀 LONG으로 두고 native 분기로 C를 확인했다(검증 기록). `4da66`(`MOVE.L`)·`4d544`·`4d96a`의 C는 소비자가 없어 Unknown이다.
6. **레지스터 간접 `JSR (A1)` 두 곳(live target).** [F] `4d38a JSR (A1)`: N23 안의 호출자 `4d2d4`/`4d2e4`는 `LEA 1bf02.l,A1`(N22)만 넘긴다. `4dbb0 JSR (A1)`: A1 = LONG `7a(A6)`(`4da66`이 `4da50` 호출자의 A0를 자식 LONG `7a`에 저장; N22 `3d310`은 `3d3de`, `4da4a`는 0 → `4dba4 TST.L; BEQ`로 건너뜀). 둘 다 PC = A1(홀수면 `unaligned animation machine PC`, routing 밖이면 `unsupported animation machine PC`)이고 복귀 LONG을 push한다. 대상 집합은 정적으로 닫지 않는다(N22 결정 3 관례).
7. **`2986` caller-X 제한 유지.** [F] `4228c`(`41f1e` 표 자식)와 `42424`(`42460` 표 자식)가 `JSR 2986`(buffer_cue)을 부른다. `2986` 실패 경로(자리 없음)는 buffer_cue 결정 1 선택 A대로 `cue wrapper failure requires known caller X` checked 오류다. N23은 고치지 않는다. 자연 400 frame에서 두 호출은 실행되지 않는다(위 자연 도달).
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n23.cpp`의 `animation_objects_n23_block`. 오류는 `unsupported animation objects n23 PC`(내부 PC), `objects n23 caller requires known carry`(소비 14 block). 메인 지시와 같다.
9. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`의 16진 토큰 중 N23 routing 범위 짝수 PC와 같은 것은 N22 실행부·test의 경계 stop(`484b4` `4d2d4` `4d508` `4d766` `4da50`, `420be` 설치 값, `4dbb2` 복귀 LONG)과 readiness 도구의 범위 끝 `484b4`(배타적 끝)뿐이다. stop은 routing 전에 멈추므로 그대로 성립한다. rollback 탐침으로 쓰는 곳은 없다(결정 1의 helper를 넣으면 frame helpers 탐침 2개가 무효).

## 원본 바이트 근거

[F] N23 코드 10 범위 합계 2,104바이트(짝수 PC 1,052개, 시작 198, 내부 854). 범위 순서로 이어 붙인 SHA256 `834551b6f707b0fe8302de33ccf3c5e3202c1e1698512447703db2eceace0478`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `420be..4240a` | 844 | `99d5f634aaa8667b90a80ab84bc380e118b66797fb2b90feecd605f4be6d3b23` | 63 |
| `42410..42460` | 80 | `163046ffe2c672c84dab4a5b2513db40bf3068188cf84801311f09965ae6d248` | 6 |
| `484b4..484ca` | 22 | `7739c5c483126c0b2dcf2179a0275c51d9140f01ffbe5fdc331402d56304d18d` | 3 |
| `4d2d4..4d418` | 324 | `154d129a617fb0c5aaf1155e9c3e9423bda2c625a37692f118abc51e8486128e` | 35 |
| `4d508..4d55e` | 86 | `bddbc0bc7e861383ddb78f2fdaec660283bd5cff54359b74c66f6b2d6a2ea533` | 7 |
| `4d766..4d77e` | 24 | `4fa468910323ac1fdc8521cfff161a3cfffae1105a4513162ca99d1957e60137` | 4 |
| `4d900..4d970` | 112 | `6c629b378842b35082bd159c2444de3df0c3be2e7d211e24bcf22bfc04517495` | 15 |
| `4da4a..4da74` | 42 | `68f353e4dede149147ffaca890e4eb96fb22d3775cab95e769db2e4e3e43d3f2` | 3 |
| `4db42..4dbdc` | 154 | `6bb48844c66ecde89f5db7f3650b670fe12e46098bd8daad5fc32643211e3369` | 18 |
| `c3a7c..c3c1c` | 416 | `90b46005b0cc2d9cbe8907d5b2190186a8ed93f10a82a0ffd3da9e77476324dd` | 44 |

- [F] 범위 이웃: `420be` 앞 `41fe6..420be`(N22), `4240a JMP 2a00`(미참조), `42460..`(LONG 표 `42460` 23 entry, 그 뒤 `424b4`(범위 밖 `2986` 자식)), `484b4` 앞 `4847c..484b4`(readiness), `484ca..`(다른 함수), `4d2d4` 앞 `..4d2d4`(다른 함수), `4d418..4d508`(`4d418` `4d4b4`, 다른 단위 경계), `4d55e..4d766`(`4d55e` `4d5fe` `4d628` `4d6b4` `4d6f2` `4d734`), `4d77e..4d7a6`(`4d77e`), `4d970..4d9d6`(미참조 `4d970`, 범위 밖에서만 부르는 `4d98a` `4d9a2` `4d9ba`, 결정 1), `4d9d6..4da08`(frame helpers), `4da08..4da4a`(`4da08`, 미참조 `4da2a`), `4da74..4db42`(미참조 `4da74` `4da9e`, 범위 밖에서만 부르는 `4db18`), `4dbdc..`(`4db18`의 자식 `4dbdc`), `c3a38..c3a7c`(자료 `c3a38` `c3a50`, 형제 callback `c3a58`), `c3c1c..`(다른 함수).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "Set/Clear 생산", "계산 C 생산", "Z/N 재계산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)·d16(A5)·`(An,Dn.W)`·d8(PC,Dn.W)는 부호 확장한다(`-7348(A5)` = A5 + sext(`8cb8`) 등). `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`MOVEM.W`→레지스터(부호 확장)는 LONG 전체). 모든 비교·`TST`·산술과 그 Bcc는 같은 block 안에 있다(예외: 결정 2·3·4).

**`420be`(N22 `420b6`이 `41fe6` 자식에 설치하는 callback; `JSR 288c` 부모 확인, `4d900` player 선택, 표 `41dfc`/`41e76`/`41f1e` 이동·`2986` 자식, `ADDX` 방향, `4a46c`/`49fc6` 애니메이션; 끝 `42410` `JMP 2a00`) 69**
- `420be`: `JSR 288c.l` — FLOW
- `420c4`: `BCC.W 42410` (→`420c8`) — C 소비, FLOW
- `420c8`: `BTST.B #7, 61(a0); BNE.W 42410` (→`420d2`) — FLOW
- `420d2`: `MOVEA.L 76(a6), a0; MOVE.W (a0), d0; CMPI.W #8000, d0; BEQ.W 42410` (→`420e0`)
- `420e0`: `CMPI.W #8080, d0; BNE.W 420ea` (→`420e8`)
- `420e8`: `RTS` — FLOW
- `420ea`: `MOVEA.L 76(a6), a0; MOVE.B 3(a0), d0; BMI.W 42108` (→`420f6`)
- `420f6`: `MOVE.B #ff, 3(a0); LSL.B #4, d0; LSL.W #8, d0; MOVE.W d0, 86(a6); MOVE.W d0, 8c(a6)` (→`42108`)
- `42108`: `LSR.W 8e(a6); JSR 4d900.l`
- `42112`: `TST.B d0; BPL.W 42134` (→`42118`)
- `42118`: `MOVE.B #0, 81(a6); MOVE.B #0, 7f(a6); MOVE.B #0, 80(a6); MOVE.B #0, 93(a6); BRA.W 42354`
- `42134`: `ANDI.W #ff, d0; ANDI.W #ff, d0; MOVE.W d0, 90(a6); MOVEQ #0, d1; BSET.B d0, d1; MOVE.B d1, 60(a6); MOVEQ #0, d1; MOVE.B 86(a6), d1; JSR 4d958.l`
- `42154`: `JSR 49be0.l` — FLOW
- `4215a`: `MOVE.W (a0), d0; BTST.B #4, d0; BEQ.W 42182` (→`42164`)
- `42164`: `TST.B 80(a6); BNE.W 42172` (→`4216c`)
- `4216c`: `MOVE.B 7c(a6), 7f(a6)` (→`42172`)
- `42172`: `MOVE.B 7d(a6), 80(a6); MOVE.B #8, 93(a6); BRA.W 421bc`
- `42182`: `MOVE.W 2(a0), d0; BTST.B #4, d0; BEQ.W 421bc` (→`4218e`)
- `4218e`: `MOVEM.W d0, -(a7); MOVE.W 90(a6), d0; JSR c3ce.l`
- `4219c`: `MOVEM.W (a7)+, d0; BEQ.W 421bc` (→`421a4`) — Z 재계산, FLOW
- `421a4`: `SUBQ.B #1, 93(a6); BCC.W 421bc` (→`421ac`)
- `421ac`: `MOVE.B #0, 93(a6); MOVE.B 7d(a6), 80(a6); BRA.W 421f4`
- `421bc`: `MOVE.W 8c(a6), d2; ANDI.W #f, d0; MOVEQ #0, d1; MOVE.B 7e(a6), d1; LEA.L 41dfc(pc), a1; MOVEA.L (a1, d1.w), a1; MOVE.B (a1, d0.w), d0; ADD.W d0, d0; ADD.W d0, d0; LEA.L 41e76(pc), a1; MOVEQ #0, d1; MOVE.B 7a(a6), d1; ADD.W d1, d1; ADD.W d1, d1; MOVEA.L (a1, d1.w), a1; MOVE.L (a1, d0.w), d1; BPL.W 421fc` (→`421f4`)
- `421f4`: `MOVE.W 86(a6), d1; MOVE.W d1, 8c(a6)` (→`421fc`)
- `421fc`: `MOVE.W 8c(a6), d2; MOVE.W d1, 8c(a6); CMP.W d2, d1; BEQ.W 42216` (→`4220a`)
- `4220a`: `MOVE.W #800, 88(a6); MOVE.W #0, 8a(a6)` (→`42216`)
- `42216`: `MOVE.W 88(a6), d7; ADD.W 8a(a6), d7; MOVE.W 86(a6), d2; SUB.W d2, d1; BEQ.W 42272` (→`42228`)
- `42228`: `CMPI.W #8000, d1; BNE.W 42238` (→`42230`)
- `42230`: `NOT.B 82(a6); BRA.W 4223c`
- `42238`: `SPL.B 82(a6)` (→`4223c`) — N 재계산, FLOW
- `4223c`: `TST.B 82(a6); BEQ.W 42246` (→`42244`)
- `42244`: `NEG.W d7` (→`42246`)
- `42246`: `ADD.W d7, d2; SUB.W d7, d1; EOR.W d1, d7; BPL.W 42252` (→`42250`)
- `42250`: `ADD.W d1, d2` (→`42252`)
- `42252`: `MOVE.W d2, 86(a6); MOVE.W #fa00, d7; SUB.W 88(a6), d7; ASR.W #2, d7; ADD.W d7, 88(a6); MOVE.W #3000, d7; SUB.W 8a(a6), d7; ASR.W #4, d7; ADD.W d7, 8a(a6)` (→`42272`)
- `42272`: `MOVE.B 80(a6), d0; BNE.W 42284` (→`4227a`)
- `4227a`: `MOVE.B #0, 81(a6); BRA.W 42354`
- `42284`: `SUBQ.B #1, 7f(a6); BCC.W 42354` (→`4228c`)
- `4228c`: `SUBQ.B #1, d0; MOVE.B d0, 80(a6); MOVE.B #ff, 81(a6); MOVE.B 7b(a6), d0; ADD.B d0, 7f(a6); MOVEQ #0, d0; MOVE.B 7a(a6), d0; ADD.W d0, d0; ADD.W d0, d0; LEA.L 41f1e(pc), a0; MOVEA.L (a0, d0.w), a0; MOVE.W #a, d0; MOVEA.L #100bf4, a1; JSR 2986.l`
- `422c2`: `MOVE.B 60(a6), 60(a0); MOVEQ #0, d2; MOVE.B 86(a6), d1; CMP.B 84(a6), d1; BNE.W 422ee` (→`422d6`)
- `422d6`: `MOVE.B 83(a6), d2; ADDQ.B #1, d2; CMPI.B #3, d2; BCS.W 422e6` (→`422e4`)
- `422e4`: `MOVEQ #0, d2` (→`422e6`)
- `422e6`: `MOVE.B d2, 83(a6); SUBQ.B #1, d2; ADD.W d2, d2` (→`422ee`)
- `422ee`: `MOVE.B d1, 84(a6); ADD.B d2, d1; MOVE.B d1, 76(a0); SUB.B d2, d1; MOVE.L #1c0000, d0; MOVE.L a0, -(a7); JSR 443d2.l`
- `42308`: `MOVEA.L (a7)+, a0; SWAP d0; SWAP d1; MOVE.W d0, d2; MOVE.W d1, d3; MOVEQ #ff, d0; JSR 4c2fa.l`
- `4231a`: `TST.B d6; BEQ.W 42354` (→`42320`)
- `42320`: `TST.W 8e(a6); BNE.W 42354` (→`42328`)
- `42328`: `MOVE.W #ff, 8e(a6); MOVEM.L d0-d1/a1, -(a7); MOVEA.L #42600, a0; MOVE.W #1e, d0; JSR 28ae.l`
- `42342`: `MOVEM.L (a7)+, d0-d1/a1; LEA.L 2e(a0), a0; SWAP d0; SWAP d1; JSR 43e08.l`
- `42354`: `MOVEQ #0, d1; MOVE.B 86(a6), d0; BTST.B #0, 15(a6); BEQ.W 4236e` (→`42364`)
- `42364`: `SUBI.B #40, d0; NEG.B d0; ADDI.B #40, d0` (→`4236e`)
- `4236e`: `ASR.B #3, d0; ADDX.B d1, d0; ANDI.B #1f, d0; MOVE.B d0, 92(a6); MOVEA.L c(a6), a0; MOVE.W 68(a0), 68(a6); MOVE.W 94(a6), 1e(a6); BNE.W 42394` (→`4238e`)
- `4238e`: `MOVE.W 1e(a0), 1e(a6)` (→`42394`)
- `42394`: `MOVE.L 96(a6), d0; BEQ.W 423b2` (→`4239c`)
- `4239c`: `MOVEA.L d0, a0; MOVE.B 86(a6), d0; ADDQ.B #8, d0; LSR.B #4, d0; ANDI.W #f, d0; MOVE.B (a0, d0.w), d0; ADD.W d0, 1e(a6)` (→`423b2`)
- `423b2`: `LEA.L 2e(a0), a1; MOVEA.L 76(a6), a0; MOVE.B (a0)+, d0; MOVE.B (a0), d1; EXT.W d0; EXT.W d1; MOVE.W d0, 2e(a6); MOVE.W d1, 32(a6); JSR 43e34.l`
- `423d0`: `JSR 4a46c.l` — FLOW
- `423d6`: `BCC.W 423e0` (→`423da`) — C 소비, FLOW
- `423da`: `MOVE.B 1a(a6), 14(a6)` (→`423e0`)
- `423e0`: `MOVE.B #ff, 17(a6); JSR 49fc6.l`
- `423ec`: `MOVE.B 19(a6), 14(a6); MOVEA.L 76(a6), a0; TST.B 2(a0); BEQ.W 42408` (→`423fe`)
- `423fe`: `CLR.B 2(a0); MOVE.B 1a(a6), 14(a6)` (→`42408`)
- `42408`: `RTS` — FLOW
- `42410`: `JSR 4d900.l` — FLOW
- `42416`: `TST.B d0; BMI.W 42424` (→`4241c`)
- `4241c`: `MOVEQ #ff, d1; JSR 4d958.l`
- `42424`: `MOVEQ #0, d0; MOVE.B 7a(a6), d0; ADD.W d0, d0; ADD.W d0, d0; MOVEA.L 42460(pc, d0.w), a0; MOVE.W #a, d0; MOVEA.L #100bf4, a1; JSR 2986.l`
- `42442`: `MOVE.B 7a(a6), 7a(a0); MOVEQ #0, d0; MOVEQ #0, d1; JSR 4970a.l`
- `42452`: `ADDQ.W #1, 68(a0); ADDQ.W #1, 1e(a0); JMP 2a00.l`

**`484b4`(N22 `1bf02`·N23 `4db94` `JSR`; BYTE `5683(A5)` bit 3 → C) 3**
- `484b4`: `BTST.B #3, 5683(a5); BEQ.W 484c4` (→`484be`) — FLOW
- `484be`: `ORI.B #1, ccr; RTS` — Set 생산
- `484c4`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**`4d2d4`(N22 `3d340` 등 `JSR`; 내부 `4d36e`(`BSR` 두 번, `4d38a JSR (A1)` = `1bf02`), C·`D0` 반환) 35**
- `4d2d4`: `LEA.L 1bf02.l, a1; MOVEQ #0, d0; BSR.W 4d36e`
- `4d2e0`: `SCS.B d7; MOVE.W d7, -(a7); LEA.L 1bf02.l, a1; MOVEQ #1, d0; BSR.W 4d36e` — C 소비
- `4d2f0`: `SCS.B d6; MOVE.W (a7)+, d7; EXT.W d7; MOVE.B d6, d7; TST.W d7; BNE.W 4d308` (→`4d2fe`) — C 소비
- `4d2fe`: `MOVEQ #ff, d0; MOVEQ #0, d1; ANDI.B #fe, ccr; RTS` — Clear 생산
- `4d308`: `CMPI.W #ff, d7; BNE.W 4d318` (→`4d310`)
- `4d310`: `MOVEQ #1, d0; ORI.B #1, ccr; RTS` — Set 생산
- `4d318`: `CMPI.W #ff00, d7; BNE.W 4d328` (→`4d320`)
- `4d320`: `MOVEQ #0, d0; ORI.B #1, ccr; RTS` — Set 생산
- `4d328`: `MOVE.W -731a(a5), d0; SUB.W 2e(a6), d0; BPL.W 4d336` (→`4d334`)
- `4d334`: `NEG.W d0` (→`4d336`)
- `4d336`: `MOVE.W -722a(a5), d1; SUB.W 2e(a6), d1; BPL.W 4d344` (→`4d342`)
- `4d342`: `NEG.W d1` (→`4d344`)
- `4d344`: `CMP.W d0, d1; BNE.W 4d35a` (→`4d34a`) — 계산 C 생산
- `4d34a`: `JSR 49a58.l` — FLOW
- `4d350`: `ANDI.W #1, d0; ORI.B #1, ccr; RTS` — Set 생산
- `4d35a`: `BCC.W 4d366` (→`4d35e`) — C 소비, FLOW
- `4d35e`: `MOVEQ #1, d0; ORI.B #1, ccr; RTS` — Set 생산
- `4d366`: `MOVEQ #0, d0; ORI.B #1, ccr; RTS` — Set 생산
- `4d36e`: `ANDI.W #1, d0; BNE.W 4d382` (→`4d376`)
- `4d376`: `LEA.L -7348(a5), a3; LEA.L 5cba(a5), a4; BRA.W 4d38a` — FLOW
- `4d382`: `LEA.L -7258(a5), a3; LEA.L 5ce6(a5), a4` (→`4d38a`) — FLOW
- `4d38a`: `JSR (a1)` — FLOW
- `4d38c`: `TST.B d0; BMI.W 4d412` (→`4d392`)
- `4d392`: `TST.W (a4); BNE.W 4d412` (→`4d398`)
- `4d398`: `TST.B 22(a4); BNE.W 4d412` (→`4d3a0`)
- `4d3a0`: `TST.B d0; BEQ.W 4d3ac` (→`4d3a6`)
- `4d3a6`: `ORI.B #1, ccr; RTS` — Set 생산
- `4d3ac`: `MOVE.W 42(a3), d0; SUB.W 42(a6), d0; MOVE.W 4a(a3), d1; SUB.W 4a(a6), d1; BTST.B #0, 15(a6); BEQ.W 4d3ca` (→`4d3c6`)
- `4d3c6`: `NEG.W d0; NEG.W d1` (→`4d3ca`)
- `4d3ca`: `MOVE.W (a0), d2; SUB.W d2, d0; SUB.W d2, d1; MOVE.W 4(a0), d2; SUB.W d2, d0; BCS.W 4d3e2` (→`4d3da`)
- `4d3da`: `SUB.W d2, d1; EOR.W d1, d0; BPL.W 4d412` (→`4d3e2`)
- `4d3e2`: `MOVE.W 46(a3), d0; SUB.W 46(a6), d0; MOVE.W 4e(a3), d1; SUB.W 4e(a6), d1; MOVE.W 2(a0), d2; SUB.W d2, d0; SUB.W d2, d1; MOVE.W 6(a0), d2; SUB.W d2, d0; BCS.W 4d40c` (→`4d404`)
- `4d404`: `SUB.W d2, d1; EOR.W d1, d0; BPL.W 4d412` (→`4d40c`)
- `4d40c`: `ORI.B #1, ccr; RTS` — Set 생산
- `4d412`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**`4d508`/`4d50e`(N22 `3d35c` 등 `JSR 4d508`; 범위 밖 `481d8 JMP 4d50e`) 7**
- `4d508`: `MOVEQ #ff, d5; MOVE.B #0, d6` (→`4d50e`)
- `4d50e`: `TST.B d0; BNE.W 4d51c` (→`4d514`)
- `4d514`: `LEA.L 5cba(a5), a4; BRA.W 4d520` — FLOW
- `4d51c`: `LEA.L 5ce6(a5), a4` (→`4d520`) — FLOW
- `4d520`: `MOVE.W 54(a6), 1c(a4); MOVE.W #0, 1a(a4); MOVE.B #0, 2b(a4); MOVE.W #0, 6(a4); CMPI.B #64, d2; BCS.W 4d544` (→`4d540`)
- `4d540`: `MOVE.B #63, d2` (→`4d544`)
- `4d544`: `MOVE.B d1, 27(a4); MOVE.B d2, 25(a4); MOVE.B d3, 26(a4); MOVE.W d4, 1c(a4); MOVE.W d5, 20(a4); MOVE.B d6, 2a(a4); RTS`

**`4d766`(N22 `3dc58` 등 `JSR`; `JSR 1bfb4`, BYTE `10f000` bit 7, `ADD.B D1,D1` → C) 4**
- `4d766`: `JSR 1bfb4.l` — FLOW
- `4d76c`: `BTST.B #7, 10f000.l; BEQ.W 4d77a` (→`4d778`) — FLOW
- `4d778`: `ST.B d1` (→`4d77a`) — FLOW
- `4d77a`: `ADD.B d1, d1; RTS` — 계산 C 생산

**`4d900`(`4210c` `42410` `4dbca`·범위 밖 `3431c`) / `4d958`(`4214e` `4241e`) 15**
- `4d900`: `MOVE.W e(a6), d0; LEA.L -7348(a5), a0; JSR 289e.l`
- `4d90e`: `BCC.W 4d92a` (→`4d912`) — C 소비, FLOW
- `4d912`: `CMP.W 5cba(a5), d0; BNE.W 4d92a` (→`4d91a`)
- `4d91a`: `TST.B 5cdc(a5); BEQ.W 4d92a` (→`4d922`)
- `4d922`: `MOVEQ #0, d0; ORI.B #1, ccr; RTS` — Set 생산
- `4d92a`: `LEA.L -7258(a5), a0; JSR 289e.l` — FLOW
- `4d934`: `BCC.W 4d950` (→`4d938`) — C 소비, FLOW
- `4d938`: `CMP.W 5ce6(a5), d0; BNE.W 4d950` (→`4d940`)
- `4d940`: `TST.B 5d08(a5); BEQ.W 4d950` (→`4d948`)
- `4d948`: `MOVEQ #1, d0; ORI.B #1, ccr; RTS` — Set 생산
- `4d950`: `MOVEQ #ff, d0; ANDI.B #fe, ccr; RTS` — Clear 생산
- `4d958`: `TST.B d0; BNE.W 4d966` (→`4d95e`)
- `4d95e`: `LEA.L 5cba(a5), a4; BRA.W 4d96a` — FLOW
- `4d966`: `LEA.L 5ce6(a5), a4` (→`4d96a`) — FLOW
- `4d96a`: `MOVE.W d1, 1e(a4); RTS`

**`4da4a`/`4da50`(`28ae` 자식 `4db42` 생성; N22 `3d310`·범위 밖 `30744` `331ce` `2b68e` `38c1a`) 3**
- `4da4a`: `MOVEA.L #0, a0` (→`4da50`) — FLOW
- `4da50`: `MOVE.L a0, -(a7); MOVEM.W d0-d1, -(a7); MOVEA.L #4db42, a0; MOVE.W #a, d0; JSR 28ae.l`
- `4da66`: `MOVE.W (a7)+, 76(a0); MOVE.W (a7)+, 78(a0); MOVE.L (a7)+, 7a(a0); RTS`

**`28ae` 자식 callback `4db42`(설치 `4db8e`; `4dbb0 JSR (A1)` live target) 18**
- `4db42`: `MOVE.W #ea, 20(a6); MOVE.L 200098.l, 22(a6); MOVEA.L #4dc66, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `4db60`: `MOVE.W #3ad, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `4db6e`: `MOVE.W #fff1, 68(a6); MOVE.W #fff1, 1e(a6); MOVE.W 76(a6), d0; MOVE.W 78(a6), d1; JSR 49290.l`
- `4db88`: `MOVE.L #4db8e, (a6)` (→`4db8e`)
- `4db8e`: `JSR 43e34.l` — FLOW
- `4db94`: `JSR 484b4.l` — FLOW
- `4db9a`: `BCC.W 4dba4` (→`4db9e`) — C 소비, FLOW
- `4db9e`: `JSR 49fc6.l` — FLOW
- `4dba4`: `TST.L 7a(a6); BEQ.W 4dbb6` (→`4dbac`)
- `4dbac`: `MOVEA.L 7a(a6), a1; JSR (a1)` — FLOW
- `4dbb2`: `BCS.W 4dbd6` (→`4dbb6`) — C 소비, FLOW
- `4dbb6`: `JSR 288c.l` — FLOW
- `4dbbc`: `BCC.W 4dbd6` (→`4dbc0`) — C 소비, FLOW
- `4dbc0`: `BTST.B #7, 61(a0); BNE.W 4dbd6` (→`4dbca`) — FLOW
- `4dbca`: `JSR 4d900(pc)` — FLOW
- `4dbce`: `TST.B d0; BPL.W 4dbd6` (→`4dbd4`)
- `4dbd4`: `RTS` — FLOW
- `4dbd6`: `JMP 2a00.l` — FLOW

**stage event callback `c3a7c`(고정 ROM LONG `e8ff0`; 범위 밖 `c3a58`의 `BRA c3a9c`; 설치 `c3b4a`) 44**
- `c3a7c`: `MOVE.W #1, 7a(a6); MOVE.L #c3a38, 80(a6); MOVE.L #c3a50, 7c(a6); MOVE.W #82, 54(a6); MOVE.W #10, d0` (→`c3a9c`)
- `c3a9c`: `MOVE.W 76(a6), d1; BEQ.W c3aa6` (→`c3aa4`)
- `c3aa4`: `SUBQ.W #1, d1` (→`c3aa6`)
- `c3aa6`: `MOVE.W d1, d2; MOVEA.L 80(a6), a0; ADD.W d2, d2; ADD.W d2, d2; MOVE.L (a0, d2.w), 80(a6); ADD.W d1, d0; LEA.L 26(a6), a0; MOVE.W #ca, 20(a6); MOVE.L 200088.l, 22(a6); LEA.L 26(a6), a0; MOVE.W d0, d1; ADD.W d1, d1; ADD.W d1, d1; MOVEA.L 200088.l, a1; MOVEA.L (a1, d1.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `c3ae8`: `TST.W 76(a6); BNE.W c3b02` (→`c3af0`)
- `c3af0`: `MOVE.W #ce5, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `c3afe`: `BRA.W c3b14` — FLOW
- `c3b02`: `MOVE.W #21, d0; MOVE.W #b, d1; MOVE.B #0, d2; JSR c6a96.l`
- `c3b14`: `MOVE.W #ce6, d0; JSR 4a496.l`
- `c3b1e`: `MOVE.W 78(a6), d0; BNE.W c3b36` (→`c3b26`)
- `c3b26`: `MOVE.W #0, 68(a6); MOVE.W #0, 1e(a6); BRA.W c3b3e`
- `c3b36`: `MOVE.W d0, 68(a6); MOVE.W d0, 1e(a6)` (→`c3b3e`)
- `c3b3e`: `JSR 4c0ac.l` — FLOW
- `c3b44`: `MOVE.L #c3b4a, (a6)` (→`c3b4a`)
- `c3b4a`: `BTST.B #7, 15(a6); BNE.W c3b5e` (→`c3b54`) — FLOW
- `c3b54`: `JSR 4be2c.l` — FLOW
- `c3b5a`: `BRA.W c3b64` — FLOW
- `c3b5e`: `JSR 4be06.l` — FLOW
- `c3b64`: `JSR 49fc6.l` — FLOW
- `c3b6a`: `MOVEA.L 7c(a6), a0; JSR 1ab02.l` — FLOW
- `c3b74`: `BCC.W c3b84` (→`c3b78`) — C 소비, FLOW
- `c3b78`: `JSR 46ef4.l` — FLOW
- `c3b7e`: `JMP 2a00.l` — FLOW
- `c3b84`: `CMPI.W #1, 76(a6); BNE.W c3c08` (→`c3b8e`)
- `c3b8e`: `JSR 4b54e.l` — FLOW
- `c3b94`: `BCC.W c3b9c` (→`c3b98`) — C 소비, FLOW
- `c3b98`: `CLR.B 5e(a6)` (→`c3b9c`)
- `c3b9c`: `BTST.B #7, 61(a6); BEQ.W c3c08` (→`c3ba6`) — FLOW
- `c3ba6`: `JSR e9112.l` — FLOW
- `c3bac`: `TST.W 7a(a6); BNE.W c3bda` (→`c3bb4`)
- `c3bb4`: `MOVEA.L #d1d08, a0; MOVE.W #14, d0; JSR 28ae.l`
- `c3bc4`: `BCC.W c3bd6` (→`c3bc8`) — C 소비, FLOW
- `c3bc8`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `c3bd2`: `ORI.B #1, ccr` (→`c3bd6`) — Set 생산
- `c3bd6`: `BRA.W c3bfc` — FLOW
- `c3bda`: `MOVEA.L #d1d38, a0; MOVE.W #14, d0; JSR 28ae.l`
- `c3bea`: `BCC.W c3bfc` (→`c3bee`) — C 소비, FLOW
- `c3bee`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `c3bf8`: `ORI.B #1, ccr` (→`c3bfc`) — Set 생산
- `c3bfc`: `JSR 46ef4.l` — FLOW
- `c3c02`: `JMP 2a00.l` — FLOW
- `c3c08`: `MOVEA.L 80(a6), a0; CMPA.W #0, a0; BEQ.W c3c1a` (→`c3c14`)
- `c3c14`: `JSR 4706c.l` — FLOW
- `c3c1a`: `RTS` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다):
  - `420be`(설치 callback): `JSR 288c`(stage_event_ops: 부모 없음 → Set, 부모 LONG = `270e` → Clear, 아니면 Set; A0 = 부모); Clear → `42410`. `420c8`: BYTE `61(A0)` bit 7 = 1 → `42410`. `420d2`: A0 = LONG `76`, `D0.W` = WORD (A0); `8000`이면 `42410`; `420e0`: `8080`이면 RTS(`420e8`). `420ea`: A0 = LONG `76`, `D0.B` = BYTE `3(A0)`; 음수면 `42108`; 아니면 `420f6`: BYTE `3(A0)` = `ff`, `D0.B` = (`D0.B` << 4) & `ff`, `D0.W` = (`D0.W` << 8) & `ffff`, `86.W` = `8c.W` = `D0.W`. `42108`: `8e.W` = `8e.W` >> 1(논리), `JSR 4d900`. `42112`: `D0.B` ≥ 0이면 `42134`; 아니면 BYTE `81` `7f` `80` `93` = 0, `BRA 42354`.
  - `42134`: `D0.W` &= `ff`(두 번), `90.W` = `D0.W`, `D1` = 1 << (`D0` & 31)(`BSET.B D0,D1`은 레지스터 대상이라 LONG), BYTE `60` = `D1.B`, `D1` = BYTE `86`(0 확장), `JSR 4d958`; `JSR 49be0`(U06: A0 = A5 + `5726`/`572c`). `4215a`: `D0.W` = WORD (A0); bit 4 = 0이면 `42182`. `42164`: BYTE `80` = 0이면 BYTE `7f` = BYTE `7c`(`4216c`); `42172`: BYTE `80` = BYTE `7d`, BYTE `93` = 8, `BRA 421bc`. `42182`: `D0.W` = WORD `2(A0)`; bit 4 = 0이면 `421bc`. `4218e`: push WORD `D0.W`(A7 −2), `D0.W` = `90.W`, `JSR c3ce`(경계). `4219c`: Z = (BYTE(A0 + sext(`D0.W`)) = 0)(결정 2), `D0` = sext(pop WORD); Z면 `421bc`. `421a4`: BYTE `93` −= 1; 빌림 없음(원래 ≠ 0)이면 `421bc`; `421ac`: BYTE `93` = 0, BYTE `80` = BYTE `7d`, `BRA 421f4`.
  - `421bc`: `D2.W` = `8c.W`, `D0.W` &= `f`, `D1` = BYTE `7e`(0 확장), A1 = LONG(`41dfc` + `D1.W`), `D0.B` = BYTE(A1 + `D0.W`), `D0.W` = 4·`D0.W`(16 bit), A1 = LONG(`41e76` + 4·BYTE `7a`)(16 bit 색인), `D1` = LONG(A1 + `D0.W`); `D1` ≥ 0이면 `421fc`. `421f4`: `D1.W` = `86.W`, `8c.W` = `D1.W`. `421fc`: `D2.W` = `8c.W`, `8c.W` = `D1.W`; `D1.W` = `D2.W`이면 `42216`; `4220a`: `88.W` = `800`, `8a.W` = 0. `42216`: `D7.W` = `88.W` + `8a.W`(16 bit), `D2.W` = `86.W`, `D1.W` −= `D2.W`; 0이면 `42272`. `42228`: `D1.W` ≠ `8000`이면 `42238`(결정 3: BYTE `82` = `D1.W` bit 15 ? `ff` : 0); 같으면 BYTE `82` = NOT BYTE `82`(`42230`). `4223c`: BYTE `82` ≠ 0이면 `D7.W` = −`D7.W`(`42244`). `42246`: `D2.W` += `D7.W`, `D1.W` −= `D7.W`, `D7.W` ^= `D1.W`; 결과 bit 15 = 1이면 `D2.W` += `D1.W`(`42250`). `42252`: `86.W` = `D2.W`; `D7.W` = (`fa00` − `88.W`) 산술 >> 2, `88.W` += `D7.W`; `D7.W` = (`3000` − `8a.W`) 산술 >> 4, `8a.W` += `D7.W`(모두 16 bit).
  - `42272`: `D0.B` = BYTE `80`; 0이면 BYTE `81` = 0(`4227a`), `BRA 42354`. `42284`: BYTE `7f` −= 1; 빌림 없음이면 `42354`. `4228c`: `D0.B` −= 1, BYTE `80` = `D0.B`, BYTE `81` = `ff`, BYTE `7f` += BYTE `7b`(8 bit), `D0` = 4·BYTE `7a`, A0 = LONG(`41f1e` + `D0.W`), `D0.W` = `a`, A1 = `100bf4`, `JSR 2986`(buffer_cue; 결정 7). `422c2`: BYTE `60(A0)` = BYTE `60`, `D2` = 0, `D1.B` = BYTE `86`; BYTE `84`와 같으면 `422d6`: `D2.B` = BYTE `83` + 1, 3 이상이면 `D2` = 0(`422e4`), BYTE `83` = `D2.B`, `D2.B` −= 1, `D2.W` = 2·`D2.W`. `422ee`: BYTE `84` = `D1.B`, BYTE `76(A0)` = `D1.B` + `D2.B`, (`D1.B` 복원), `D0` = `1c0000`, push A0, `JSR 443d2`(U02). `42308`: A0 = pop, `SWAP D0`, `SWAP D1`, `D2.W` = `D0.W`, `D3.W` = `D1.W`, `D0` = `ffffffff`, `JSR 4c2fa`(경계). `4231a`: `D6.B` = 0이면 `42354`; `42320`: `8e.W` ≠ 0이면 `42354`; `42328`: `8e.W` = `ff`, push A1 D1 D0(LONG, `MOVEM.L` 순서), `28ae`(A0 = `42600`, `D0.W` = `1e`). `42342`: pop D0 D1 A1, A0 += `2e`, `SWAP D0`, `SWAP D1`, `JSR 43e08`(cleanup).
  - `42354`: `D1` = 0, `D0.B` = BYTE `86`; BYTE `15` bit 0 = 1이면 `D0.B` = `40` − (`D0.B` − `40`)(`42364`: `SUBI.B`, `NEG.B`, `ADDI.B`, 8 bit). `4236e`: `ASR.B #3,D0`(X = 밀려난 마지막 bit = 원래 bit 2), `D0.B` = `D0.B` + `D1.B` + X(`ADDX.B`), `D0.B` &= `1f`, BYTE `92` = `D0.B`, A0 = LONG `c`(부모), `68.W` = `68.W(A0)`, `1e.W` = `94.W`; `94.W` = 0이면 `1e.W` = `1e.W(A0)`(`4238e`). `42394`: `D0` = LONG `96`; 0이면 `423b2`; `4239c`: A0 = `D0`, `D0.B` = ((BYTE `86` + 8) & `ff`) >> 4, `D0.W` &= `f`, `D0.B` = BYTE(A0 + `D0.W`), `1e.W` += `D0.W`. `423b2`: A1 = A0 + `2e`, A0 = LONG `76`, `D0.B` = BYTE (A0)+, `D1.B` = BYTE (A0), `D0.W` = sext(`D0.B`), `D1.W` = sext(`D1.B`), `2e.W` = `D0.W`, `32.W` = `D1.W`, `JSR 43e34`; `JSR 4a46c`(N04, C 반환); Set이면 BYTE `14` = BYTE `1a`(`423da`). `423e0`: BYTE `17` = `ff`, `JSR 49fc6`. `423ec`: BYTE `14` = BYTE `19`, A0 = LONG `76`; BYTE `2(A0)` ≠ 0이면 BYTE `2(A0)` = 0, BYTE `14` = BYTE `1a`(`423fe`). RTS.
  - `42410`: `JSR 4d900`; `D0.B` ≥ 0이면 `D1` = `ffffffff`, `JSR 4d958`(`4241c`). `42424`: `D0` = 4·BYTE `7a`, A0 = LONG(`42460` + `D0.W`), `D0.W` = `a`, A1 = `100bf4`, `JSR 2986`. `42442`: BYTE `7a(A0)` = BYTE `7a`, `D0` = `D1` = 0, `JSR 4970a`(N14). `42452`: `68.W(A0)` += 1, `1e.W(A0)` += 1(A0 = `4970a`가 남긴 값), `JMP 2a00`.
  - `484b4`: BYTE `5683(A5)` bit 3 = 1이면 C = 1(`484be`), 아니면 C = 0(`484c4`), RTS.
  - `4d2d4`: A1 = `1bf02`, `D0` = 0, `BSR 4d36e`; `4d2e0`: `D7.B` = C ? `ff` : 0, push WORD `D7.W`, A1 = `1bf02`, `D0` = 1, `BSR 4d36e`; `4d2f0`: `D6.B` = C ? `ff` : 0, `D7.W` = pop WORD, `D7.W` = sext(`D7.B`), `D7.B` = `D6.B`; `D7.W` = 0이면 `D0` = `ffffffff`, `D1` = 0, C = 0(`4d2fe`); `00ff`이면 `D0` = 1, C = 1; `ff00`이면 `D0` = 0, C = 1; 둘 다(`ffff`)면 `4d328`: `D0.W` = |WORD `-731a(A5)` − `2e.W`|, `D1.W` = |WORD `-722a(A5)` − `2e.W`|(16 bit, `BPL` 아니면 `NEG.W`); `4d344`: C = `D1.W` < `D0.W`(부호 없음); 같으면 `JSR 49a58`, `D0.W` &= 1, C = 1(`4d350`); 다르면 `4d35a`: C = 0이면 `D0` = 0, 아니면 `D0` = 1, C = 1. RTS.
  - `4d36e`: `D0.W` &= 1; ≠ 0이면 A3 = A5 − `7258`, A4 = A5 + `5ce6`, 아니면 A3 = A5 − `7348`, A4 = A5 + `5cba`. `4d38a`: `JSR (A1)`(live target). `4d38c`: `D0.B` < 0 → C = 0(`4d412`). WORD (A4) ≠ 0 → C = 0. BYTE `22(A4)` ≠ 0 → C = 0. `D0.B` ≠ 0 → C = 1(`4d3a6`). `4d3ac`: `D0.W` = `42.W(A3)` − `42.W`, `D1.W` = `4a.W(A3)` − `4a.W`; BYTE `15` bit 0 = 1이면 둘 다 부호 반전(`4d3c6`). `4d3ca`: `D2.W` = WORD (A0), `D0.W` −= `D2.W`, `D1.W` −= `D2.W`, `D2.W` = WORD `4(A0)`, `D0.W` −= `D2.W`; 빌림이면 `4d3e2`; `4d3da`: `D1.W` −= `D2.W`, `D0.W` ^= `D1.W`; bit 15 = 0이면 C = 0. `4d3e2`: 같은 꼴로 `46`/`4e`와 WORD `2(A0)`/`6(A0)`; 빌림이면 C = 1(`4d40c`); `4d404`: bit 15 = 0이면 C = 0, 아니면 C = 1. RTS.
  - `4d508`: `D5` = `ffffffff`, `D6.B` = 0. `4d50e`: `D0.B` ≠ 0이면 A4 = A5 + `5ce6`, 아니면 A5 + `5cba`. `4d520`: `1c.W(A4)` = `54.W`, `1a.W(A4)` = 0, BYTE `2b(A4)` = 0, `6.W(A4)` = 0; `D2.B` ≥ `64`(부호 없음)이면 `D2.B` = `63`(`4d540`). `4d544`: BYTE `27(A4)` = `D1.B`, BYTE `25(A4)` = `D2.B`, BYTE `26(A4)` = `D3.B`, `1c.W(A4)` = `D4.W`, `20.W(A4)` = `D5.W`, BYTE `2a(A4)` = `D6.B`, RTS.
  - `4d766`: `JSR 1bfb4`(N22). `4d76c`: BYTE `10f000` bit 7 = 1이면 `D1.B` = `ff`(`4d778`). `4d77a`: C = `D1.B` bit 7, `D1.B` = (`D1.B` << 1) & `ff`, RTS.
  - `4d900`: `D0.W` = `e.W`, A0 = A5 − `7348`, `JSR 289e`; Clear → `4d92a`; `D0.W` = WORD `5cba(A5)`이고 BYTE `5cdc(A5)` ≠ 0이면 `D0` = 0, C = 1(`4d922`). `4d92a`: A0 = A5 − `7258`, `JSR 289e`; Clear → `4d950`; `D0.W` = WORD `5ce6(A5)`이고 BYTE `5d08(A5)` ≠ 0이면 `D0` = 1, C = 1(`4d948`). `4d950`: `D0` = `ffffffff`, C = 0. RTS.
  - `4d958`: `D0.B` ≠ 0이면 A4 = A5 + `5ce6`, 아니면 A5 + `5cba`; `1e.W(A4)` = `D1.W`, RTS.
  - `4da4a`: A0 = 0. `4da50`: push LONG A0, push WORD `D1.W` 뒤 `D0.W`(`MOVEM.W D0-D1,-(A7)`), `28ae`(A0 = `4db42`, `D0.W` = `a`; 자리 없음이면 A0 = 더미 노드). `4da66`: `76.W(A0)` = pop WORD(호출자 `D0.W`), `78.W(A0)` = pop WORD(`D1.W`), LONG `7a(A0)` = pop LONG(호출자 A0), RTS.
  - `4db42`(`28ae` 자식): `20.W` = `ea`, LONG `22` = bank LONG `200098`, A1 = `4dc66`, `D0.W` = `100`, `JSR 49f8c`; `4db60`: `D0.W` = `3ad`, `D1.B` = 0, `JSR 8ebe`; `4db6e`: `68.W` = `1e.W` = `fff1`, `D0.W` = `76.W`, `D1.W` = `78.W`, `JSR 49290`; `4db88`: `(A6)` = `4db8e`, fall-through. `4db8e`(설치): `JSR 43e34`, `JSR 484b4`; Set이면 `JSR 49fc6`(`4db9e`). `4dba4`: LONG `7a` = 0이면 `4dbb6`; 아니면 A1 = LONG `7a`, `JSR (A1)`(live target; N22 `3d3de` 등); `4dbb2`: Set이면 `4dbd6`. `4dbb6`: `JSR 288c`; Clear → `4dbd6`; BYTE `61(A0)` bit 7 = 1 → `4dbd6`; `JSR 4d900`; `D0.B` ≥ 0이면 `4dbd6`; 아니면 RTS(`4dbd4`). `4dbd6`: `JMP 2a00`.
  - `c3a7c`(stage event callback): `7a.W` = 1, LONG `80` = `c3a38`, LONG `7c` = `c3a50`, `54.W` = `82`, `D0.W` = `10`. `c3a9c`: `D1.W` = `76.W`; ≠ 0이면 `D1.W` −= 1(`c3aa4`). `c3aa6`: `D2.W` = 4·`D1.W`, A0 = LONG `80`, LONG `80` = LONG(A0 + sext(`D2.W`)), `D0.W` += `D1.W`, A0 = A6 + `26`, `20.W` = `ca`, LONG `22` = bank LONG `200088`, A0 = A6 + `26`, `D1.W` = 4·`D0.W`, A1 = bank LONG `200088`(다시 읽음), A1 = LONG(A1 + sext(`D1.W`)), `D0.W` = `100`, `JSR 49f8c`. `c3ae8`: `76.W` = 0이면 `8ebe`(`D0.W` = `ce5`, `D1.B` = 0; `c3af0`), 아니면 `c6a96`(`D0.W` = `21`, `D1.W` = `b`, `D2.B` = 0; `c3b02`). `c3b14`: `D0.W` = `ce6`, `JSR 4a496`. `c3b1e`: `D0.W` = `78.W`; `68.W` = `1e.W` = `D0.W`(0이면 0). `c3b3e`: `JSR 4c0ac`; `c3b44`: `(A6)` = `c3b4a`, fall-through. `c3b4a`(설치): BYTE `15` bit 7 = 1이면 `JSR 4be06`, 아니면 `JSR 4be2c`; `JSR 49fc6`; A0 = LONG `7c`, `JSR 1ab02`; Set → `JSR 46ef4`, `JMP 2a00`. `c3b84`: `76.W` ≠ 1이면 `c3c08`. `c3b8e`: `JSR 4b54e`; Set이면 BYTE `5e` = 0(`c3b98`). `c3b9c`: BYTE `61` bit 7 = 0이면 `c3c08`. `c3ba6`: `JSR e9112`(경계). `c3bac`: `7a.W` = 0이면 `28ae`(A0 = `d1d08`, `D0.W` = `14`), 아니면 `28ae`(A0 = `d1d38`); Set이면 `D0.W` = `D1.W` = 0, `JSR 4970a`, C = 1(`c3bd2`/`c3bf8`). `c3bfc`: `JSR 46ef4`, `JMP 2a00`. `c3c08`: A0 = LONG `80`; 0이 아니면 `JSR 4706c`(U09). RTS.

## carry

- [F] **소비 14 block**. Unknown C로 들어오면 `objects n23 caller requires known carry`(상태 보존)다. Clear면 BCC는 분기 대상, BCS·SCS는 fall-through/0; Set이면 반대.
  - `420c4 BCC.W 42410`, `4dbbc BCC.W 4dbd6`: stage_event_ops `288c`(`2898 ORI` Set, `289e` 계산, `28a8 ORI` Set).
  - `423d6 BCC.W 423e0`: N04 `4a46c`(`4a48a ORI` Set, `4a490 ANDI` Clear).
  - `4d2e0 SCS.B D7`, `4d2f0 SCS.B D6`: N23 `4d36e`(`4d3a6` `4d40c` Set, `4d412` Clear). 두 block은 `MOVE`/`MOVEQ`/`TST`가 뒤따라 끝 C는 Unknown이다(FLOW 아님, carry 보존 목록에는 넣음).
  - `4d35a BCC.W 4d366`: N23 `4d344 CMP.W D0,D1`(결정 4).
  - `4d90e BCC.W 4d92a`, `4d934 BCC.W 4d950`: readiness `289e`(`CMPI.L #270e,(A0)` 같음 → Clear, `28a8 ORI` → Set).
  - `4db9a BCC.W 4dba4`: N23 `484b4`.
  - `4dbb2 BCS.W 4dbd6`: `4dbb0 JSR (A1)`의 live callee(N22 `3d3de`: `TST.B` Clear / `ORI` Set).
  - `c3b74 BCC.W c3b84`: U05 `1ab02`(`1ab7a ANDI` Clear, `1aafc ORI` Set).
  - `c3b94 BCC.W c3b9c`: U01 `4b54e`(`4b548 ANDI` Clear 등).
  - `c3bc4 BCC.W c3bd6`, `c3bea BCC.W c3bfc`: fade_card `28ae`(`2908 ORI` Set = 자식 생성, `290e ANDI` Clear = 자리 없음).
- [F] **known 생산 18 block**: Set(`ORI`) `484be` `4d310` `4d320` `4d350` `4d35e` `4d366` `4d3a6` `4d40c` `4d922` `4d948` `c3bd2` `c3bf8`; Clear(`ANDI`) `484c4` `4d2fe` `4d412` `4d950`; 계산 `4d344`(`CMP.W D0,D1`: C = `D1.W` < `D0.W`), `4d77a`(`ADD.B D1,D1`: C = `D1.B` bit 7). 소비자 확인은 결정 5.
- [F] **FLOW_ONLY 62 block**(C 보존): JSR/BSR/JMP/BRA/RTS block, `LEA`/`MOVEA`+`JSR`/`BRA`(`4d376` `4d382` `4dbac` `c3b6a` `4da4a`), `BTST`(+Bcc)·`ST` block(`420c8` `4d76c` `4d778` `4dbc0` `c3b4a` `c3b9c`), `MOVEM`+`BEQ`(`4219c`), `SPL`(`42238`), 소비 12개. 목록: `420be` `420c4` `420c8` `420e8` `42154` `4219c` `42238` `423d0` `423d6` `42408` `42410` `484b4` `4d34a` `4d35a` `4d376` `4d382` `4d38a` `4d514` `4d51c` `4d766` `4d76c` `4d778` `4d90e` `4d92a` `4d934` `4d95e` `4d966` `4da4a` `4db8e` `4db94` `4db9a` `4db9e` `4dbac` `4dbb2` `4dbb6` `4dbbc` `4dbc0` `4dbca` `4dbd4` `4dbd6` `c3afe` `c3b3e` `c3b4a` `c3b54` `c3b5a` `c3b5e` `c3b64` `c3b6a` `c3b74` `c3b78` `c3b7e` `c3b8e` `c3b94` `c3b9c` `c3ba6` `c3bc4` `c3bd6` `c3bea` `c3bfc` `c3c02` `c3c14` `c3c1a`.
- [F] **carry 보존 목록 64 PC** = FLOW_ONLY 62 + `4d2e0` `4d2f0`(SCS 소비 뒤 block 안에서 Unknown으로 둠). 생산 18 block은 보존 목록에 넣지 않고 block 안에서 C를 정한다.
- [F] **Unknown 116 block**: 나머지(`MOVE`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDQ`/`ADDX`/`SUB`/`SUBQ`/`ANDI`/`EOR`/`NEG`/`NOT`/`EXT`/`SWAP`/`LSL`/`LSR`/`ASR`/`CLR` 포함 block, 설치 block, 애니메이션 block).
- [F] X: `4236e`만 X를 쓴다(같은 block의 `ASR.B #3`이 만든다). block 경계를 건너는 X는 없다.

## 구현 범위와 규약

- routing 10 범위(위 표). 짝수 PC 1,052개 중 block 시작 198, 내부 854. 내부 PC 직접 진입은 `unsupported animation objects n23 PC`다. 범위 이웃(미참조 코드·범위 밖에서만 부르는 helper·자료)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술·shift는 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다(`ASR.W` `ASR.B`는 부호 bit 채움을 직접 계산). 결과 flag는 같은 block 안의 Bcc만 쓴다(결정 2·3·4 예외). 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 64 PC를 넣는다.
- 제어 이동: `4d38a`·`4dbb0 JSR (A1)`만 live target이다(복귀 LONG push 뒤 PC = A1). 나머지는 정적이다. 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`4db88`→`4db8e`, `c3b44`→`c3b4a`).
- 스택: 요약의 push/pop만. `MOVEM.W`→레지스터는 부호 확장 LONG, `MOVE.W (A7)+,D7`은 하위 WORD만. `MOVEM.L D0-D1/A1,-(A7)`은 A1, D1, D0 순서로 쓰고 `(A7)+`는 D0, D1, A1 순서로 읽는다. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `200098`(`4db42` id `ea` → LONG `22`), LONG `200088`(`c3aa6` id `ca` → LONG `22`, 그리고 같은 LONG을 다시 읽어 표 기준; 표 LONG(기준 + 4·(`10` + `76.W`−1 또는 0))).
- [F] 고정 ROM 자료(live bus 읽기, 원본처럼 색인 검사 없음):
  - `41dfc` LONG 4개(`41e0c` `41e1c` `41e2c` `41e3c`, BYTE 색인 `7e`; 표 BYTE 16개씩), `41e76` LONG 표(색인 4·BYTE `7a`) → LONG 표(색인 4·BYTE), `41f1e` LONG 표(색인 4·BYTE `7a`; `2986` 자식 값), `42460` LONG 표(색인 4·BYTE `7a`; `424b4` `424e6` `4251e`), `c3a38` LONG 표(`c36dc` `c3736` `c37e0` `c38da`; 색인 4·(`76.W` − 1)).
  - 주소만 넘기는 자료: 사각형 `c3a50`(`1ab02`, LONG `7c`), 애니메이션 목록 `4dc66`(`49f8c`), `8ebe` 인자 WORD `3ad` `ce5`, `4a496` 인자 `ce6`.
- [F] work RAM:
  - 노드 A6: BYTE `14` `15` `17` `19` `1a` `5e` `60` `61` `7a` `7b` `7c` `7d` `7e` `7f` `80` `81` `82` `83` `84` `86`(BYTE 읽기) `92` `93`; WORD `1e` `20` `2e` `32` `54` `68` `76` `78` `7a` `86` `88` `8a` `8c` `8e` `90` `94`; LONG `(A6)`(설치) `c`(부모) `22` `76`(`420be`: 3 BYTE 기록 포인터) `7a`(`4db42`: code pointer) `7c` `80` `96`.
  - 부모 `c(A6)`: WORD `68` `1e`(`4236e`/`4238e`), `288c`가 돌려준 A0의 BYTE `61`.
  - A5 기준: BYTE `5683`(`484b4`), player 기록 `-7348`(`100cb8`) `-7258`(`100da8`)의 WORD `42` `46` `4a` `4e`(`4d3ac`/`4d3e2`), WORD `-731a` `-722a`(`4d328`/`4d336`), 슬롯 `5cba`/`5ce6`(WORD `0` `6` `1a` `1c` `1e` `20`, BYTE `22` `25` `26` `27` `2a` `2b`), WORD `5cba`/`5ce6`·BYTE `5cdc`/`5d08`(`4d900`), BYTE `7024`+(0/1)(`c3ce`, 결정 2).
  - BYTE `10f000` bit 7(`4d76c`, 디버그 BYTE).
  - `28ae`/`2986` 자식 A0: BYTE `60` `76` `7a`, WORD `68` `1e`(`42452`), WORD `76` `78`·LONG `7a`(`4da66`).
- [F] 상수 인자: `28ae` `D0.W` = `a`(`4da50`) / `1e`(`42328`) / `14`(`c3bb4` `c3bda`); `2986` `D0.W` = `a`, A1 = `100bf4`; `49f8c` `D0.W` = `100`; `49290` `D0`/`D1` = `76.W`/`78.W`; `4970a` `D0`/`D1` = 0; `443d2` `D0` = `1c0000`; `4c2fa` `D0` = `ffffffff`; `c6a96` `D0.W`/`D1.W`/`D2.B` = `21`/`b`/0.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256): `engine/src/animation_machine_objects_n23.cpp` `c5a148eb271bc3defc3ea62b4d52d4104c8ed2da16d29be61a9f542fbacefa00`, `engine/tests/animation_machine_objects_n23_test.cpp` `3b0b0d97156cb46a46fc41e01b5e913abe9095e6cf09a330f3556fbf59d11c50`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나(64 PC); `4635c41b…`), `engine/src/animation_machine_internal.h`(선언 하나; `862621dc…`), `Makefile`(source 목록·test target·실행 줄; `7c848050…`), `tools/verify_animation_machine.py` SOURCES(`a3270581…`).
- [F] 실행부 case 집합 = scratch `starts.txt`(198, SHA256 `23b4ba37…`). 내부 PC 854개는 모두 `unsupported animation objects n23 PC`, 소비 14 block은 Unknown C에서 `objects n23 caller requires known carry`(상태 보존)다.
- [F] `make -j4 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all2.log`). N23 test 출력: `animation machine objects n23: 579 fixtures (41 checked errors, 201 kept C), 198 blocks, 2659 calls`. N22 test는 그대로 통과(`460 fixtures`).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N23 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen23.py` Unicorn 생성): 579 fixture(성공 538, checked 오류 41), 198 시작 모두 Unicorn fixture로 덮음, block 표(198 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 14는 Unknown에서 거부), zero-step 198 × 3, 내부 PC 854 전수, 홀수 PC(범위 양끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`(11 fixture), 범위 옆 자료 `42460` `42464` `c3a38` `c3a50`, 경계 stop 31개(다른 단위 진입·`c3ce` `4c2fa` `e9112`·live target `3d3de`는 stop만). "real" 행은 `288c` `289e` `28ae` `1ab02` `4a46c`와 N22 `1bf02`(→ N23 `484b4`) `1bfb4` `3d3de`를 native로 따라가 실제 소비자 분기와 비교했다. 재계산 block은 native SR N/Z를 같은 값으로 두고 진입했다. 바뀐 오류 행: 부모 없는 `420be`(`288c` Set, A0 = 0 → `420c8`가 vector page BYTE `61`을 읽음)는 C++ `reached program vectors require exact128BYTE view`(bus에 vector view가 없는 test 조건) checked 오류다.
- [F] RTS 앞 생산 native 확인(실제 ROM 소비자를 복귀 LONG으로, Unicorn SR 미사용; 26건 모두 계약과 같음): `484b4`(BYTE `5683` = 0/8/f7/ff) → `4db9a` Clear/Set/Clear/Set, `4d2fe` → `3d34c` Clear, `4d310` `4d320` `4d350` `4d35e` `4d366` → `3d34c` Set, `4d3a6` `4d40c` `4d922` `4d948` → `4dbb2` Set, `4d412` `4d950` → `4dbb2` Clear, `4d77a`(`D1` = 0/7f/80/ff/40/12345681) → `3dc5e` Clear/Clear/Set/Set/Clear/Set, `4d344`(4쌍) → `4d35a` 분기가 `D1.W` < `D0.W`와 같음.
- [F] 돌연변이 검사(scratch `mut/mut23.py`, 실행부 한 줄씩 16개: 소비 분기 뒤바꿈, `4d77a` bit, `4d344` 부호, `ADDX` X bit, `ASR.W`, `4219c` 부호 확장, `42238` N, `BSET` mod 32, `4d2f0` `EXT.W`, `4d520` 비교, `4d3ca` 빌림, `4da50` push 순서, `c3aa6` 색인 배수, `484b4` bit, `421a4` 빌림, `4239c` 반올림): 16/16을 test가 잡았다(`4219c` 부호 확장을 잡으려고 `421bc`/`421a4`에서 멈추는 fixture 3개를 더했다).
- [F] 실제 ROM 차분(scratch `realrom/real23.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM, native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC·interpreter `49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 198/198. 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `420c4` 150 `423d6` 234 `4d2e0` 98 `4d2f0` 101 `4d35a` 17 `4d90e` 294 `4d934` 299 `4db9a` 82 `4dbb2` 40 `4dbbc` 107 `c3b74` 139 `c3b94` 28 `c3bc4` 22 `c3bea` 23. interpreter 따라가기(`FOLLOW_ANIM`) 2 × 1,000 case 불일치 0. 의도한 차이: `2986` 실패 경로 caller-X 제한(`cue wrapper failure requires known caller X`, 결정 7) 84/73/61건(대부분 `420be`·`42410`·`4228c`에서 자리 없는 `28ae`). native 홀수 주소·Unknown C 진입 소비 거부 0. clean stop이 없는 native case는 건너뜀(seed별 165/187/181).
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `22dd4ef` 일치 pass 14,408·node 122,462, 불일치 0 → N23 뒤 같음(불일치 0, `diff_results.json` SHA256 `a6c41695…` 기준과 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 130·pass 52,000·node 389,711·불일치 0(`verification.json` SHA256 `985b9efc…`) → N23 뒤 complete **132**·pass 52,800·node 396,091·불일치 0(`5656685f…`). **새 완주 seed 38 39**(400 frame), 잃은 seed 0. 남은 미완: 32 33(`dcf56`), 116 117(`38ba0`, N31), guard 136~140, 141.
- [U] 남은 미확인: 116 117의 자연 경로는 N31 `38ba0`에서 먼저 멈춰 N23 범위의 frame pass 비교가 아직 없다(실제 ROM 차분·fixture로만 덮음). `4219c`·`4231a`·`c3bac` 뒤 경로와 `2986` 호출은 자연 400 frame에서 실행되지 않는다. 결정 1의 helper 18 block은 routing하지 않았다.
