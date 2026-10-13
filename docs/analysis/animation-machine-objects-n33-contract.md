# 객체 callback F4 N33: `38ba0` 계열 helper — `3b542`·`28ae` 자식 `3b118`/`3b1ae`, 설치 `3a1e0`, helper `3a5d2` `3b22a`~`3b3b4`, C 생산 `482aa`, 충돌 판정 `4b8e8`, 입력 판정 `4bce0`과 조각 `46bfc` `4be50` `4be6c` `4bfb4` `4c0ea` `4c37c`/`4c7a4` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N33 행(162 block, 누적 5,139, 13 범위 `3a1e0..3a2fa` `3a41c..3a4a4` `3a5d2..3a60a` `3b118..3b424` `3b542..3b5a6` `46bfc..46c02` `482aa..482c0` `4b8e4..4bb1a` `4bce0..4be82` `4bfb4..4bfc0` `4c0ea..4c0f0` `4c37c..4c390` `4c7a4..4c810`, 진입 `3b118` `3b166`, 경계 callee 8, bank 1, 미실행 설치 1(+1), 옛 U38 81 + U45 79)과 N31 계약 결정 1(SHA256 `afe778f95178a0f1e3a0f3d468f23a33c5eae9ec6133c69c1e8a5a3f5ad15fe2`; N31이 `3a2f4..3a4a4` 전체를 가짐)이다. 단위 형식과 규약은 N31 계약과 N32a 계약(`animation-machine-objects-n32-contract.md`, SHA256 `372504afc664b44d6f563f941ac297216483af78ef69d03309e3f20cf4ada61d`)을 따른다. 메인 작업 지시:
- N31 결정 1(구속): N33 = `3a1e0..3a2f4`(`..3a2fa` 아님)이고 `3a41c..3a4a4`는 뺀다. 다른 단위의 기존 routing 범위 안을 다시 routing하지 않는다.
- block 시작은 `MOVE.L #imm,(A6)` 설치 callback, DBRA 대상, JSR 복귀점을 포함한 정적 디코드로 정하고 자료 표는 routing하지 않는다. 재범위 수치와 다르면 보고한다(결정 2).
- 작은 조각 범위(`46bfc` `482aa` `4bfb4` `4c0ea` `4c37c`)가 N33 코드에서만 닿는지, 이미 소유된 곳이 아닌지 확인한다(결정 3).
- 소유자 없는 `3a4a4..3a5d2`(`3a4a4 JMP 4d418`, `3a4be`, `3a4da`, `3a5be`)는 `3b118`/`3b542` 호출 그래프에 속하거나 seed 116/117이 자연 실행하면 N33에 넣고, 아니면 보고한다(결정 1).
- seed 116 117은 기준(`c5181b6`)에서 frame 0 `3b542`(`38ba0 JSR 3b542`)에서 멈춘다. N33 뒤 멈춤 위치(PC, frame, 소유 단위)와 새 완주 seed를 보고한다.
- C 생산: N31은 `3b334`·`3a4a4` 뒤, N32a는 `3b334`·`3a4da` 뒤 C를 소비한다. N33이 소유하면 그 C를 분류하고 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR을 쓰지 않음).
- 탐침 이동·두 번째 진입 patch는 scratch patch 파일과 결정으로 보고한다(결정 4·5).

- 결정 관례(N31·N32a와 같음): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치, 범위 밖에서 참조하는 범위 안 진입(설치 값·`28ae` 자식 값·BRA/JMP/JSR 대상))로 정한다. Unicorn TB 분할은 시작이 아니다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N32a 수용 관례: `MOVE.x`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDQ`/`SUB`/`SUBQ`/`AND`/`ANDI`/`OR`/`ORI`/`NEG`/`EXT`/`SWAP`/`LSR` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`BSET`/`BCLR`/`Scc`)만인 block과 callee C를 소비하는 block은 FLOW_ONLY다. `ORI #1,CCR`은 known Set, `ANDI #fe,CCR`은 known Clear 생산이다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N33 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기는 LONG `2000b4` 하나(`3b11e` `3b1b4` `3b548`, 결정 8)다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n33`(HEAD `c5181b6` = N01~N31, N32a, F5 H1 통합, `engine/src/animation_machine.cpp` SHA256 `4337007826e7d6dc41dd3381162124ca0ca028f7b7eb04fc85e4dc36454e94d3`, routing 규칙 90개, `engine/src/animation_machine_objects_u08b.cpp` SHA256 `2eaa138c170340b55b81f0b1e9635b011a9ebe1d28a15d158e44edcecd8f1afc`, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`, `engine/src/animation_machine_stage_event_ops.cpp` SHA256 `5369d279877922f015249c3d4173cccd46beabdf6c3a50d9c220c175b982f61c`)을 참조했다. N33 13 범위의 짝수 PC는 모두 기존 routing에 없다(scratch `n33.py`가 범위마다 확인). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n33/n33.py`(정적 디코드)와 `cls33.py`(분류)가 원본 opcode에서 독립 계산했다(`starts.txt` SHA256 `07bc18e3dcc48902f404fa75c69bae323e3b07a49a225e0ad11ad38983b3bc51`).

## 요약

- [F] **N33 = 201 block**(13 routing 범위, 코드 2,296바이트, 548 명령 중 547 도달(`3b2d8 BRA.W`는 `3b2d6 RTS` 뒤 죽은 코드, 내부 PC), 자료 없음, 짝수 PC 1,148, 내부 947). 진입 28개에서 분기·fall-through·JSR/BSR 복귀점·범위 안 설치(`3a242` `3b166` `3b202`)·범위 안 `28ae` 자식(`3b118`)을 끝까지 따라간 정적 closure다. 230 미만이라 나누지 않는다.
- [F] 진입(범위 밖에서 들어옴):
  - `3b542`(N31 `38ba0 JSR`, 범위 밖 `38b40 JSR`): `20.W` = `122`, LONG `22` = banked LONG `2000b4`, BYTE `79` = 1이면 BYTE `15` bit 0 set, `3b22a`, `14` ← `1b`, BYTE `15` bit 6 set, `68.W` = `1e.W` = `8810`, `4d81c`(D1 = `11`) 결과 D1/D2/D3 → BYTE `ad`/`ae`/`54.W`, `28ae` 자식 `3b118`(D0 = `a`), C(`28ae`) Clear → `JMP 2a00`(`3a2f4`, N31), Set → RTS.
  - `28ae` 자식 callback `3b118`(`3b590`): `20`·`22`, BYTE `15` bit 6, `68.W` = `1e.W` = 0, `49290`(D0 = D1 = 0), `8ebe`(`1e1`, 0), `49f8c`(`3ceb8`), 설치 `3b166`(fall-through): `288c`(부모 확인; Clear → `JMP 2a00`), 부모 BYTE `a4` = 0이면 RTS, 아니면 `491c4`, `1e.W` ← 부모 `1e.W` − 1, BYTE `a2` ← 부모 `a2`, `a2` < `10`이면 `43e34`, `49fc6`, RTS.
  - `28ae` 자식 callback `3b1ae`(N32b `39c80`): `20`·`22`, `3af8`(`1a4b`), BYTE `15` bit 6, `68.W` = `1e.W` = `e000`, `49f8c`(`3ce70`), `8ebe`(`8cd`, 0), `49274`, 설치 `3b202`(fall-through): `288c` Clear → `JMP 2a00`, Set → `43e34`, `49fc6`(Clear → RTS, Set → `JMP 2a00`).
  - 설치 callback `3a1e0`(범위 밖 `3a1da MOVE.L #3a1e0,(A6)`): `3a5be`(A0 = LONG `82`), `64.L` = 0, BYTE `8a` = `ff`, `4d8d8`(D0.B 음수면 `3b26a`, 아니면 `3b424`; D0 bit 5면 `3a4be`(D1 = 1); `3a4a4`, `3b288`), `3b334`, BYTE `a7` 감소(0이면 설치 `3a242`), `BRA.W 3a41c`(N31). 설치 `3a242`(N32b `39f94 BRA.W`도 들어옴): `4ae4a`(`3b846`), `3a24c`(범위 밖 `3a154 BRA.W`도 들어옴): `3a4be`(D1 = 0), `4ff96`, `49274`, `d3d7c` 네 번(자식 `36`/`3a`/`54` 기록), `28ae` 자식 `3a2fa`(N31), `49214`, `JMP 2a00`.
  - helper(N31·N32a·N32b·범위 밖이 `JSR`/`BRA`/`JMP`): `3a5d2`(LONG `82` = `3a60a`, BYTE `96` `95` = `ff`, `99` `9a` = 0, A1 = 0, `3b398`, BYTE `9d` `9e` bit 4 clear), `3b22a`(`8ff4`, `8ebe` 네 번), `3b26a`/`3b288`(BYTE `15` bit 7이면 `JMP 4bfb4`/`JMP 4bfc0`, 아니면 `3a.L` += `ffff6000` 뒤 `JMP 4be6c`/`JMP 4be82`), `3b282`/`3b2a0`(N32b `39e58` `39f18`/`39898` `399fe` `3a0c6`의 직접 진입), `3b2a6`(`64.L` 보존 + `3b288`), `3b2b8`(LONG `7e` 애니메이션 WORD 표: 음수 −1..−3은 `14` ← `19+n`, 그 밖 음수는 상대 점프, 양수는 `JMP 8d34`), `3b2ee`(`8a.W` bit 0 보존 합성), `3b302`(BYTE 2개로 `94` bit 4/1, `49f8c`(LONG)), `3b334`(LONG `56` 선택, BYTE `b1` = `36.L` ≠ 0, `ce02`, `3b3b4`·`49fc6` 순서는 BYTE `94` bit 1, C = `49fc6`의 C), `3b398`(BYTE `a9` `aa` = 0, `94` bit 0 clear, A0 = A6+`8c`, `JMP 49f96`).
  - C 생산 `482aa`(N33 `4b8e8`, 범위 밖 `3627c` `362c6` `b51e6` `b53e4` `b8a6e` `b8ed4` `JSR`): BYTE `5683(A5)` bit 4가 0이면 C = 1, 아니면 C = 0, RTS.
  - 충돌 판정 `4b8e8`(u08b `4be86`, 범위 밖 `4bfc8`, N34 `4cd9e`): `482aa` Set 또는 BYTE `61` bit 7 → `4b8e4`(D7 = 0, RTS); 아니면 D2/D3 += D0/D1(A0 ≠ 0이면 A0 기준 보정), RAM 표 `10daf8..10db78`(LONG 쌍 16개)을 돌며 사각형 겹침을 판정해 D7·BYTE `6d(A3)`·D2/D3을 고치고 끝 보정, RTS.
  - `4bce0`(N33 `4be6c` `4bfb4` `4c0ea`, u08b `4be82`, 범위 밖 `4bfc0` `4c0fe` `4c2c4` `4c344` `4c394` `4c3d0`): BYTE `549f(A5)` = `ff`, `54a0` = 0, `MOVEM.L D0-D7,-(A7)`; A6가 player(`100cb8`/`100da8`)면 `19a00`·`1aa3a`로, 아니면 `4d8d8`(D0.B 음수면 `54a2` `54a3` = `ff`) 또는 `19a00`으로 LONG `54a6(A5)` 표 값을 고르고 `1aa3a` bit 6이면 `54a0` = 1, `MOVEM.L (A7)+,D0-D7`, `BRA.W 4bc58`(u08b 블록 `4bc44`의 중간, 결정 5).
  - 조각: `46bfc`(N34 `4c8ac` 등 6곳 `JSR`): `MOVEA.L 54c2(A5),A1; RTS`. `4be50`(범위 밖 `71326` `cc9fa`): `4bc44`, BYTE `549e` = `ff`, `10d49d` = 0, `MOVEM.L 2e(A6),D0-D3/A0`, `BRA.W 4bf0a`. `4be6c`(N33 `3b282`, N29 `316ac` `316bc`, N30 `33c6c`, 범위 밖 `40984`): `BSR 4bce0`, 같은 꼬리 → `4bf0a`. `4bfb4`(N33 `3b274`, N30 `33c5e`, 범위 밖 `40972`): `BSR 4bce0`, `BSR 4c020`, `BRA 4bf0a`. `4c0ea`(N29 `33116`, 범위 밖 `1d928` `1d940` `1dbe8`): `JSR 4bce0`, `BRA 4c0b0`(U12). `4c37c`(N28 `2b8d6`, 범위 밖 `2b910`): `28ae` 자식 `4cf52`(N35, D0 = 0), `BRA.W 4c7a4`: 자식 A0의 WORD/BYTE 필드 초기화, `86`/`8a`/`8e`/`92` = 부모 `2e`/`32`(LONG `3e` 기준 보정) − `538e(A5)` 기준, LONG `3e` = A5+`538e`, RTS.
- [F] **경계(실행부 없음, 현재 routing 밖) callee·출구 10개**: `19a00`(`4bd2a` `4bd82`) `3a4a4` `3a4be` `3a5be`(결정 1) `3b424`(`3a1fe`; 결정 1) `4bfc0`(`3b292 JMP`; 결정 1) `4d8d8`(`3a1f2` `4bd02`; N35) `4ff96`(`3a258`) `8d34`(`3b2e8 JMP`) `d3d7c`(`3a264` 등 4곳). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **다른 실행부로 가는 callee·출구**: `2a00` `28ae`(fade_card), `288c`(stage_event_ops), `3a2f4` `3a41c`(N31), `3af8`(sound), `43e34` `8ff4`(cleanup), `491c4` `4c020`(U17), `49214`(N05), `49274` `49290` `1aa3a`(U08), `49f8c` `49f96` `49fc6` `49fca`(interpreter), `4ae4a`(N08), `4bc44` `4be82` `4bf0a`(U08b), `4bc58`(U08b 블록 내부, 결정 5), `4c0b0`(U12), `4d81c`(stage_area), `8ebe`(U02), `ce02`(U04).
- [F] **범위 밖 값(실행 PC가 아님)**: `3a60a`(`3a5d2`가 LONG `82`에 기록; 뒤의 `3a5be JSR (A0)` live target, 결정 1), `28ae` 자식 값 `3a2fa`(N31) `4cf52`(N35). 주소만 넘기는 자료: `3b846`(`4ae4a`), `3ceb8` `3ce70`(`49f8c`), `3b864` `3b882`(LONG `56` 값), `4bca0` `4bca8` `4bcb0` `4bcb8` `4bcc0` `4bcc8` `4bcd0` `4bcd8`(LONG `54a6(A5)` 값; 표 `4bca0..4bce0`은 routing하지 않음).
- [F] **carry**(아래 "carry" 절): 소비 8 block(모두 FLOW), known 생산 4개(`482b4` ANDI Clear, `482ba` ORI Set, `3b392` `3b410` 계산), FLOW_ONLY 75개(소비 8 포함), Unknown 122개. 75 + 4 + 122 = 201.
- [F] X·DIVx/MULx·TRAP·I/O port 쓰기·bank 변경·계산 점프 표·레지스터 간접 제어 이동이 없다. bank 읽기는 LONG `2000b4` 하나다. N/Z 재계산이 없다(flag를 읽는 Bcc·`Scc`는 소비 8 block 말고는 모두 같은 block 안의 생산자를 읽는다). 스택: JSR/BSR 복귀 LONG, BYTE push `SCS.B -(A7)`(`3b380` `3b38c`, A7 −2)·`MOVE.B 14(A6),-(A7)`(`3b3b4`, A7 −2)와 pop(`3b392` `3b410`, A7 +2), WORD push/pop(`3b3b4`/`3b410`, `4b91e`/`4baee`, `4bd1e`/`4bd30`), LONG `3b2a6`/`3b2b2`, `MOVEM.L D0-D7`(`4bce0`/`4bdfe`).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`, TB 시작 기준): seed 116 117만 N33 PC를 실행한다. `3a5d2` `3a5fc`, `3b118..3b178`(8), `3b22a..3b27a`(8), `3b302..3b332`(4), `3b334..3b410`(13), `3b542..3b5a4`(6), `46bfc`, `482aa` `482b4` `482ba`, `4b8e4..4bb04`(10), `4bce0..4bd0e` `4bdfe`(6), `4be6c` `4be70`, `4bfb4..4bfbc`(3), `4c0ea` `4c0ee`, `4c37c` `4c38c`, `4c7a4` `4c7e6`. `3a1e0` 함수, `3b1ae` 사슬, `3b288` `3b2a6` `3b2b8` `3b2ee`, `4be50`, `4bd1e..4bdf8`은 자연 400 frame에서 실행되지 않는다.
- [F] 기준(`c5181b6`)에서 seed 116 117은 frame 0 `38ba0 JSR 3b542`에서 멈춘다. N33 뒤 멈춤 위치는 아래 "작업자 검증 기록"이다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **`3a4a4..3a5d2`·`3b424..3b446`·`4bfc0..4c020`(소유자 없음)를 넣지 않는다.** [F] 셋 다 N33 범위 코드(`3a1e0` 본문의 `3a1fe JSR 3b424`, `3a20a`/`3a24c JSR 3a4be`, `3a212 JSR 3a4a4`, `3a1e0 JSR 3a5be`; `3b288`의 `3b292 JMP 4bfc0`)가 부르지만 `3b118`/`3b542` 호출 그래프 밖이고 seed 116 117이 자연 400 frame에서 실행하지 않는다(`rescope/dyn_rng` TB 시작에 없음). 메인 규칙대로 routing하지 않고 경계로 둔다. 내용:
   - `3a4a4`(5 명령, block 3: `D0.W` = `86.W`, `D2` = 2(BYTE `15` bit 0이면 −2), `D3` = `1e`, `JMP 4d418`(routing 밖)) — C는 `4d418`이 정한다(N31 `38c5e` `3a384` 소비, N29 결정 4의 `4d418` C 미확인과 같은 문제).
   - `3a4be`(block 4: BYTE push D1, `4d8d8`, pop, D0.B 양수면 `JMP 4d4b4`(routing 밖), 아니면 RTS(C = TST Clear)).
   - `3a4da`(N32a 13곳 `JSR`만 부름, N33 코드는 부르지 않음; `4d6b4`, `28ae` 자식 `3ae84` `2d57a`/`2d3ae`, `4c2fa`, ORI/ANDI C 생산; BYTE 쌍 자료 `3a4d6..3a4da`는 `LEA x(PC),A4`로 읽음).
   - `3a5be`(`ST.B 97`, `99`→`9a` 복사 대칭, `JSR (A0)` live target(대개 `3a60a`), RTS).
   - `3b424..3b446`(`49be0`, LONG 마스크, `9d` OR; N32b도 부름), `4bfc0..4c020`(`4bce0`, `4c020`, `4b8e8`, `ADD.B D7,D7`, `469d8`, `MOVEM.L D0-D3/A0,2e(A6)`, `BRA 4bf16`; 재범위 규칙 (b)로 진입이 됐지만 어느 행에도 없음).
   - [I] 권고: `4d418`·`4d4b4`·`4d6b4`를 맡는 단위(N23b 또는 N35 뒤 정리 단위) 또는 N32b와 함께 묶는다. `3a1e0` 본문과 `3b288`은 지금 그 경계에서 멈춘다(자연 seed 영향 없음).
   - [F] N32b가 stop 전용으로 나가는 N33 쪽 PC `3a242` `3a5d2` `3b282` `3b288` `3b302` `3b334`는 모두 N33 block 시작이다(두 번째 진입 patch 불필요). `3b424`는 위 이유로 routing 밖 경계로 남는다. 고아 `39f9c..3a1e0`(설치 `3a1e0`의 설치자 `3a1da` 포함)과 자식 `3acd6`은 N33 호출 그래프 밖이라 routing하지 않는다.
2. **재범위 수치와 다른 점(162 → 201).** [F] 재범위 N33 행 162 block은 `3a41c..3a4a4`(N31 몫)를 포함하고, 설치 직후 fall-through·JSR 복귀점·범위 안 helper 직접 진입(`3b282` `3b2a0`)을 시작으로 나누지 않은 수다([I] N32 결정 3과 같은 차이; 재범위 leader 집합 `rescope/build.pkl`과의 집합 비교는 하지 않았다, [U]). 재범위 "경계 callee 8"은 이 계약의 routing 밖 경계 10개(`19a00` `3a4a4` `3a4be` `3a5be` `3b424` `4bfc0` `4d8d8` `4ff96` `8d34` `d3d7c`)와 수가 다르다([U] 재범위가 세는 방식 차이). bank 1(`2000b4`)은 같다.
3. **조각 범위의 도달.** [F] 조각은 모두 기존 routing 밖이고(`n33.py`가 짝수 PC마다 확인), N33 코드에서만 닿는 것은 `4c7a4`(`4c38c BRA.W`) 하나다. 나머지는 다른 단위에서도 부르는 공유 callee다: `46bfc`(N33 코드에서는 부르지 않음; N34 `4c8ac` `4c90e` `4c9f8` `4cacc` `4cb3e` `4cc38`), `482aa`(N33 `4b8e8`, 범위 밖 6곳), `4b8e8`(u08b `4be86`, `4bfc8`, N34 `4cd9e`), `4bce0`(위 진입 목록), `4bfb4`(N33 `3b274`, N30 `33c5e`, 범위 밖 `40972`), `4c0ea`(N29 `33116`, 범위 밖 3곳), `4c37c`(N28 `2b8d6`, 범위 밖 `2b910`), `4be50` `4be6c`(위). 재범위 행대로 N33에 둔다. `46bfc` 다음 `46c00 RTS`를 가리키는 LONG `ef800`은 `ef7fe CMPI.W #4,D0`의 확장어(우연 일치)다. `4bce0..4be06` 뒤 `4be06..4be50`은 U17·u08b가 이미 routing해 N33 범위를 `4bce0..4be06`·`4be50..4be82`로 나눴다.
4. **무효화 탐침 3 test 이동(적용함, 검토 요청).** [F] 기존 test의 "routing 밖" 탐침·경계 rollback 기대 중 N33 PC인 것: U01 `outside` `0x482aa`(→ `0x10fe30`), U08b `BOUNDARIES` `0x4b8e8` `0x4bce0`(→ 어떤 stop과도 맞지 않는 `0x10fe50` `0x10fe52`, 기존 `469d8` 등과 같은 처리), U08b `outside` `0x4b8e8` `0x4bce0` `0x4be50` `0x4be68` `0x4be80`(→ `0x10fe50` `0x10fe52` `0x10fe54` `0x10fe56` `0x10fe58`), U09 `outside` `0x46bfc` `0x46bfe`(→ `0x10fe5a` `0x10fe5c`). F4 경계 관례대로 RAM `10fe00..10fefe` 탐침으로 바꿨다(N25 선례). 나머지 N33 PC 등장은 stop 또는 자료 값이다(N31·N32 test의 경계 stop `3a5d2` `3b22a` `3b26a` `3b288` `3b2a0` `3b2a6` `3b2b8` `3b2ee` `3b302` `3b334` `3b542`, N28 `4c37c`, N29/N30 `4be6c` `4bfb4` `4c0ea`, U08b fixture stop `4bce0` `4b8e8`, U12 `4c0ea`, U17 `4bfb4`; 자료 값 N08 `3b346`, N20 `3a2be`, N25 `3b5a4`). scratch 기록 `ms5-scratch/n33/patch-probes-u01-u08b-u09.diff`(작업 트리에 적용한 diff). 242개 test 실행으로 확인했다.
5. **U08b 블록 `4bc44`의 두 번째 진입 `4bc58`(적용하지 않음).** [F] N33 `4bdfe MOVEM.L (A7)+,D0-D7; BRA.W 4bc58`은 u08b block `4bc44`(`CLR.B 549f; CLR.B 54a0; MOVE.B #ff,54a2; MOVE.B #ff,54a3; MOVE.B #0,549d; MOVE.B #0,549e; MOVE.B #2,549c; BTST #4,15(A6); BEQ 4bc7a`)의 다섯 번째 명령으로 들어간다. u08b routing은 `4bc58`을 받지만 case가 없어 `unsupported animation objects u08b PC`(rollback)다. N33 test는 `4bdfe`를 stop `4bc58`로만 쓴다. [F] 지금은 자연 seed가 `4bdfe`에 닿지 못한다(`4bd02 JSR 4d8d8`·`4bd82 JSR 19a00`이 먼저 routing 밖 경계). N35(`4d8d8`) 뒤에는 seed 116 117이 `4bdfe → 4bc58`로 간다(자연 TB `4bdfe`). [I] 권고: u08b `4bc44`를 `4bc44`(앞 4 명령, 후속 `4bc58`)와 `4bc58`(뒤 4 명령 + BEQ)로 나눈다(실행 의미 불변, N28 결정 9와 같은 꼴). scratch patch `ms5-scratch/n33/patch-u08b-4bc58.diff`(실행부 + u08b test 기대 수) — 결정 뒤 적용. **해소(F4 N35):** patch를 적용해 u08b `4bc44`/`4bc58`로 나눴다(u08b 계약 "두 번째 진입 `4bc58`", N35 계약 결정 4).
6. **`3b334`의 C(N31·N32a 소비).** [F] `3b334`는 `3b36c BTST #1,94(A6)`에 따라 `3b376 JSR 3b3b4; 3b37a JSR 49fc6; 3b380 SCS.B -(A7)` 또는 `3b386 JSR 49fc6; 3b38c SCS.B -(A7); JSR 3b3b4`를 거쳐 `3b392 MOVE.B (A7)+,D0; LSR.B #1,D0; RTS`로 끝난다. 반환 C = 꺼낸 BYTE의 bit 0 = `49fc6`이 돌려준 C다. `3b392`를 계산 생산으로 둔다(꺼낸 BYTE bit 0). `SCS` 두 곳은 `49fc6` C의 소비자(Unknown이면 checked 오류)다. 실제 소비자 N31 `38ce4 BCC.W 38cee`·N32a `38e12`를 복귀 LONG으로 둔 native 분기로 확인한다.
7. **`3b3b4`의 C.** [F] `3b410 ...; BTST #0,94(A6); SNE.B D0; LSR.B #1,D0; RTS` → C = BYTE `94` bit 0(`3b3ea` `49fca` C로 정해짐). 소비자는 없다(`3b37a JSR 49fc6`, `3b392 MOVE.B`가 덮음). 정확히 계산되므로 계산 생산으로 둔다(미사용). 실제 ROM 소비자(N31 `38ce4`)를 복귀 LONG으로 둔 native 분기로 확인한다.
8. **bank LONG `2000b4`.** [F] `3b118` `3b1ae` `3b542`의 `MOVE.L 2000b4.l,22(A6)`은 PVC bank window를 live bus(`am_read`, 현재 bank base)로 읽는다. bank 변경은 없다. test는 합성 물리 바이트(`0x2000b4`)를, 실제 ROM 차등은 8개 `program_rom_*.ms5d`를 쓴다.
9. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n33.cpp`의 `animation_objects_n33_block`. 오류는 `unsupported animation objects n33 PC`(내부 PC), `objects n33 caller requires known carry`(소비 8 block).
10. **`2986` caller-X 제한 해당 없음.** [F] N33은 `2986`을 부르지 않는다.

## 원본 바이트 근거

[F] N33 코드 13 범위 합계 2,296바이트(짝수 PC 1,148개, 시작 201, 내부 947). 범위 순서로 이어 붙인 SHA256 `2263056f514fee3865700d8952e3f71e2da55e50bdaaec10f4af503a3ecc07b5`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `3a1e0..3a2f4` | 276 | `e70a90cf4adf202c67d7f7bf5111f419fb1b3448f090897822dac709c580dcc8` | 26 |
| `3a5d2..3a60a` | 56 | `fd7d12af470630f1ca355bfd3c971ec8a52a25adce18594e11688982c26be5ed` | 2 |
| `3b118..3b424` | 780 | `bfbbd1b5a1401a402f4bc7c25056f76e4b3c0a113a670fa3b8909b8032a6daff` | 76 |
| `3b542..3b5a6` | 100 | `cd7e709fbe072fd52fff888ed96c431c8412b71481f8b27a4996583285c3d0fe` | 7 |
| `46bfc..46c02` | 6 | `f59d52b5cd72987ff048d676d4838c1282589b94803c1700d77e63da5829c599` | 1 |
| `482aa..482c0` | 22 | `32af3c9f882bf97490a208722686a0e034fe69d9efa0f9b393995cacd80e7214` | 3 |
| `4b8e4..4bb1a` | 566 | `2cce70e2aae4ffd6e56b3ae7b98c00197b320ae32553ef72be769357be87c4fc` | 48 |
| `4bce0..4be06` | 294 | `544cf547f9f7b4e15ed58963cef4ba92da885d1504b26c0d80debfdae819fc28` | 24 |
| `4be50..4be82` | 50 | `eedfd228ed2ee5604962227d1be1ddc63df15197ccb7bfcfc9594038e78c2335` | 4 |
| `4bfb4..4bfc0` | 12 | `55435ffbd7f9e91aa913644d4ce6da02af3933071b9a34c716407f641b432326` | 3 |
| `4c0ea..4c0f0` | 6 | `7dd8b3185bb615cd19dd61a1cd954c746cf58f17f3e57d2fe5ca3407af051254` | 2 |
| `4c37c..4c390` | 20 | `ded3f591f108b581972bc54536b8793e8c7760db326043859b316b4254be63aa` | 2 |
| `4c7a4..4c810` | 108 | `c72f74bbe3f4ff0879904eea70edbbf755f44459920f1c78387f341cf0e84d57` | 3 |

- [F] 범위 이웃(앞/뒤 PC의 routing): `3a1de`(routing 밖, 함수 `3a0dc..3a1e0`의 끝) / `3a2f4`(N31); `3a5d0`(`3a5be` 결정 1) / `3a60a`(routing 밖, `3a5d2`가 쓰는 code pointer 값); `3b116`·`3b424`(routing 밖, `3b424` 결정 1); `3b540`·`3b5a6`(routing 밖, `3b5a6 JSR 3b22a`로 시작하는 다른 함수); `46bfa`(U09 `469a0..46bfc`) / `46c02`(routing 밖); `482a8`(U01 `48296..482aa`) / `482c0`(U19 `482c0..482ea`); `4b8e2`·`4bb1a`(routing 밖); `4bcde`(routing 밖 LONG 표 `4bca0..4bce0`) / `4be06`(U17 `4be06..4be2c`); `4be4e`(u08b `4be34..4be50`) / `4be82`(u08b); `4bfb2`(U17 `4bfa4..4bfb4`) / `4bfc0`(결정 1); `4c0e8`(U12 `4c0ac..4c0ea`) / `4c0f0`(routing 밖); `4c37a`·`4c390`(routing 밖); `4c7a2`·`4c810`(routing 밖, `4c810..`은 N34).
- [F] 우연 일치(실행 진입 아님; scratch `xref33.py`): `3b3c8`(LONG `b2e4`, 명령 중간), `4bcfc`(LONG `4aaa2`, `4aaa0 MOVEA.L $4bcfc` 자료 주소; 명령 중간), `4bdf6`(`4be1c`의 확장어), `4be00`(LONG 3곳, 명령 중간), `4be7e`(`4bea4`의 확장어), `4c800`(LONG 20곳, 명령 중간), `46c00`(LONG `ef800`, 확장어).
- [F] 자료 표: `4bca0..4bce0`(LONG 쌍 8개, `54a6(A5)` 값의 대상)은 routing 범위 밖이다. N33 범위 안에는 자료가 없다.

## carry

- [F] **FLOW_ONLY 75**(진입 C를 그대로 둔다; `carry_preserving_pc` 목록에 넣음): CCR을 바꾸지 않는 명령만인 block 67과 소비 8.
- [F] **소비 8**(Unknown이면 `objects n33 caller requires known carry`, 상태 보존): `3b16c BCC.W 3b1a8`·`3b208 BCS.W 3b212`(stage_event_ops `288c`의 C: 부모 없음·`270e` 아님이면 Set), `3b21e BCC.W 3b228`(interpreter `49fc6`), `3b380 SCS.B -(A7); BRA.W 3b392`·`3b38c SCS.B -(A7); JSR 3b3b4`(`49fc6`), `3b400 BCC.W 3b40a`(interpreter `49fca`), `3b5a0 BCC.W 3a2f4`(fade_card `28ae`: 빈 슬롯 없음 Set), `4b8ee BCS.B 4b8e4`(N33 `482aa`).
- [F] **known 생산 4**: `482b4 ANDI.B #fe,CCR; RTS`(Clear), `482ba ORI.B #1,CCR; RTS`(Set), `3b392 MOVE.B (A7)+,D0; LSR.B #1,D0; RTS`(C = 꺼낸 BYTE bit 0), `3b410 MOVE.B (A7)+,14(A6); MOVE.W (A7)+,1e(A6); BTST #0,94(A6); SNE.B D0; LSR.B #1,D0; RTS`(C = BYTE `94` bit 0). 확인: 실제 소비자(U01 `4b8ee`·범위 밖 `36282`, N31 `38ce4`, N32a `38e12`)를 복귀 LONG으로 둔 native 분기(scratch 생성기 `confirm`).
- [F] **Unknown 122**: 나머지(`MOVE`/`CLR`/`TST`/`CMP`/산술/`SWAP`/`EXT` 등이 C를 바꾸는 block; 소비자가 없거나 같은 block 안에서만 읽음). 예: `3a5fc ANDI.B ...; RTS`(실제 C = Clear지만 소비자 없음), `4b8e4 MOVEQ #0,D7; RTS`(Clear, 소비자 없음: u08b `4be9a`·`4bfce`·N34 `4cda4`가 덮음), `4bb14 SUB.L; SUB.L; RTS`(빌림, 소비자 없음).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "Clear/Set 생산", "C 계산 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. `CMP`/`CMPA`/`TST`와 그 Bcc는 같은 block 안에 있다. `BMI`/`BPL`은 결과 bit 31(N)만, `BCC`/`BCS`는 무부호 빌림, `BGE`/`BLE`(`TST.L` 뒤, V = 0)는 N/Z를 본다. `BTST #n,Dn`은 bit n mod 32(`4bda2 #e`는 bit 14). `CMPA.W #0,An`은 부호 확장 0과 LONG 비교(A = 0). `MOVEM.L D0-D7,-(A7)`은 D0이 가장 낮은 주소, `MOVEM.L (A7)+`는 D0부터 읽는다. BYTE push/pop은 A7 ±2(BYTE는 새 A7 주소, 즉 WORD의 상위 BYTE).

**설치 callback `3a1e0`(범위 밖 `3a1da` 설치)·설치 `3a242`(`3a238`, N32b `39f94 BRA.W`)·`3a24c`(범위 밖 `3a154 BRA.W`) 26**
- `3a1e0`: `MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `3a1e8`: `CLR.L 64(a6); MOVE.B #ff, 8a(a6); JSR 4d8d8.l`
- `3a1f8`: `TST.B d0; BMI.W 3a21e` (→`3a1fe`)
- `3a1fe`: `JSR 3b424(pc)` — FLOW
- `3a202`: `BTST.B #5, d0; BEQ.W 3a212` (→`3a20a`) — FLOW
- `3a20a`: `MOVE.B #1, d1; JSR 3a4be(pc)`
- `3a212`: `JSR 3a4a4(pc)` — FLOW
- `3a216`: `JSR 3b288(pc)` — FLOW
- `3a21a`: `BRA.W 3a222` — FLOW
- `3a21e`: `JSR 3b26a(pc)` — FLOW
- `3a222`: `JSR 3b334(pc)` — FLOW
- `3a226`: `MOVE.B a7(a6), d0; BEQ.W 3a238` (→`3a22e`)
- `3a22e`: `SUBQ.B #1, d0; MOVE.B d0, a7(a6); BRA.W 3a23e`
- `3a238`: `MOVE.L #3a242, (a6)` (→`3a23e`)
- `3a23e`: `BRA.W 3a41c` — FLOW
- `3a242`: `LEA.L 3b846(pc), a0; JSR 4ae4a.l` — FLOW
- `3a24c`: `MOVE.B #0, d1; JSR 3a4be(pc)`
- `3a254`: `MOVEQ #1, d0; MOVEQ #0, d1; JSR 4ff96.l`
- `3a25e`: `JSR 49274.l` — FLOW
- `3a264`: `JSR d3d7c.l` — FLOW
- `3a26a`: `MOVE.L #fff20000, 36(a0); MOVE.L #280000, 3a(a0); MOVE.W #a, 54(a0); JSR d3d7c.l`
- `3a286`: `MOVE.L #a0000, 36(a0); MOVE.L #fff00000, 3a(a0); MOVE.W #7, 54(a0); JSR d3d7c.l`
- `3a2a2`: `MOVE.L #90000, 36(a0); MOVE.L #250000, 3a(a0); MOVE.W #7, 54(a0); JSR d3d7c.l`
- `3a2be`: `MOVE.L #fff90000, 36(a0); MOVE.L #fffc0000, 3a(a0); MOVE.W #5, 54(a0); MOVEA.L #3a2fa, a0; MOVE.W #1e, d0; JSR 28ae.l`
- `3a2e4`: `MOVEQ #0, d0; MOVEQ #8, d1; JSR 49214.l`
- `3a2ee`: `JMP 2a00.l` — FLOW

**`3a5d2`(N31·N32a·범위 밖 15곳 `JSR`) 2**
- `3a5d2`: `MOVE.L #3a60a, 82(a6); MOVE.B #ff, 96(a6); MOVE.B #ff, 95(a6); MOVE.B #0, 99(a6); MOVE.B #0, 9a(a6); MOVEA.L #0, a1; JSR 3b398(pc)`
- `3a5fc`: `ANDI.B #ef, 9d(a6); ANDI.B #ef, 9e(a6); RTS `

**`28ae` 자식 callback `3b118`(`3b590`)·설치 `3b166` 14**
- `3b118`: `MOVE.W #122, 20(a6); MOVE.L 2000b4.l, 22(a6); BSET.B #6, 15(a6); MOVE.W #0, 68(a6); MOVE.W #0, 1e(a6); MOVEQ #0, d0; MOVEQ #0, d1; JSR 49290.l`
- `3b142`: `MOVE.W #1e1, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `3b150`: `MOVEA.L #3ceb8, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3b160`: `MOVE.L #3b166, (a6)` (→`3b166`)
- `3b166`: `JSR 288c.l` — FLOW
- `3b16c`: `BCC.W 3b1a8` (→`3b170`) — C 소비, FLOW
- `3b170`: `TST.B a4(a0); BNE.W 3b17a` (→`3b178`)
- `3b178`: `RTS ` — FLOW
- `3b17a`: `JSR 491c4.l` — FLOW
- `3b180`: `MOVE.W 1e(a0), 1e(a6); SUBQ.W #1, 1e(a6); MOVE.B a2(a0), a2(a6); CMPI.B #10, a2(a6); BCC.W 3b1a6` (→`3b19a`)
- `3b19a`: `JSR 43e34.l` — FLOW
- `3b1a0`: `JSR 49fc6.l` — FLOW
- `3b1a6`: `RTS ` — FLOW
- `3b1a8`: `JMP 2a00.l` — FLOW

**`28ae` 자식 callback `3b1ae`(N32b `39c80`)·설치 `3b202` 13**
- `3b1ae`: `MOVE.W #122, 20(a6); MOVE.L 2000b4.l, 22(a6); MOVE.W #1a4b, d0; JSR 3af8.l`
- `3b1c6`: `BSET.B #6, 15(a6); MOVE.W #e000, 68(a6); MOVE.W #e000, 1e(a6); MOVEA.L #3ce70, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3b1e8`: `MOVE.W #8cd, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `3b1f6`: `JSR 49274.l` — FLOW
- `3b1fc`: `MOVE.L #3b202, (a6)` (→`3b202`)
- `3b202`: `JSR 288c.l` — FLOW
- `3b208`: `BCS.W 3b212` (→`3b20c`) — C 소비, FLOW
- `3b20c`: `JMP 2a00.l` — FLOW
- `3b212`: `JSR 43e34.l` — FLOW
- `3b218`: `JSR 49fc6.l` — FLOW
- `3b21e`: `BCC.W 3b228` (→`3b222`) — C 소비, FLOW
- `3b222`: `JMP 2a00.l` — FLOW
- `3b228`: `RTS ` — FLOW

**helper `3b22a` `3b26a` `3b282` `3b288` `3b2a0` `3b2a6` 16**
- `3b22a`: `JSR 8ff4.l` — FLOW
- `3b230`: `MOVE.W #8ce, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `3b23e`: `MOVE.W #db2, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `3b24c`: `MOVE.W #db2, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `3b25a`: `MOVE.W #db2, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `3b268`: `RTS ` — FLOW
- `3b26a`: `BTST.B #7, 15(a6); BEQ.W 3b27a` (→`3b274`) — FLOW
- `3b274`: `JMP 4bfb4.l` — FLOW
- `3b27a`: `ADDI.L #ffff6000, 3a(a6)` (→`3b282`)
- `3b282`: `JMP 4be6c.l` — FLOW
- `3b288`: `BTST.B #7, 15(a6); BEQ.W 3b298` (→`3b292`) — FLOW
- `3b292`: `JMP 4bfc0.l` — FLOW
- `3b298`: `ADDI.L #ffff6000, 3a(a6)` (→`3b2a0`)
- `3b2a0`: `JMP 4be82.l` — FLOW
- `3b2a6`: `MOVE.L 64(a6), -(a7); CLR.L 64(a6); JSR 3b288(pc)`
- `3b2b2`: `MOVE.L (a7)+, 64(a6); RTS `

**helper `3b2b8` `3b2ee` `3b302` 12**
- `3b2b8`: `MOVEA.L 7e(a6), a0; MOVE.W (a0)+, d1; BPL.W 3b2e0` (→`3b2c2`)
- `3b2c2`: `NEG.W d1; CMPI.W #4, d1; BCC.W 3b2dc` (→`3b2cc`)
- `3b2cc`: `MOVE.B 19(a6, d1.w), 14(a6); MOVE.L a0, 7e(a6); RTS `
- `3b2dc`: `ADDA.W (a0), a0; MOVE.W (a0)+, d1` (→`3b2e0`)
- `3b2e0`: `MOVE.L a0, 7e(a6); MOVE.B 14(a6), d0; JMP 8d34.l`
- `3b2ee`: `ANDI.W #fffe, d0; MOVE.W 8a(a6), d1; ANDI.W #1, d1; OR.W d1, d0; MOVE.W d0, 8a(a6); RTS `
- `3b302`: `BCLR.B #4, 94(a6); MOVE.B (a0)+, d0; BEQ.W 3b314` (→`3b30e`)
- `3b30e`: `BSET.B #4, 94(a6)` (→`3b314`) — FLOW
- `3b314`: `BCLR.B #1, 94(a6); MOVE.B (a0)+, d0; BEQ.W 3b326` (→`3b320`)
- `3b320`: `BSET.B #1, 94(a6)` (→`3b326`) — FLOW
- `3b326`: `MOVEA.L (a0), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3b332`: `RTS ` — FLOW

**helper `3b334`(C 생산) `3b398` `3b3b4` 21**
- `3b334`: `TST.L 56(a6); BEQ.W 3b35a` (→`3b33c`)
- `3b33c`: `CMPI.B #8, 9f(a6); BCC.W 3b350` (→`3b346`)
- `3b346`: `MOVE.L #3b864, d0; BRA.W 3b356`
- `3b350`: `MOVE.L #3b882, d0` (→`3b356`)
- `3b356`: `MOVE.L d0, 56(a6)` (→`3b35a`)
- `3b35a`: `TST.L 36(a6); SNE.B b1(a6); MOVE.W 1e(a6), d0; JSR ce02.l`
- `3b36c`: `BTST.B #1, 94(a6); BNE.W 3b386` (→`3b376`) — FLOW
- `3b376`: `JSR 3b3b4(pc)` — FLOW
- `3b37a`: `JSR 49fc6.l` — FLOW
- `3b380`: `SCS.B -(a7); BRA.W 3b392` — C 소비, FLOW
- `3b386`: `JSR 49fc6.l` — FLOW
- `3b38c`: `SCS.B -(a7); JSR 3b3b4(pc)` — C 소비, FLOW
- `3b392`: `MOVE.B (a7)+, d0; LSR.B #1, d0; RTS ` — C 계산 생산
- `3b398`: `CLR.B a9(a6); CLR.B aa(a6); BCLR.B #0, 94(a6); LEA.L 8c(a6), a0; MOVE.W #100, d0; JMP 49f96.l`
- `3b3b4`: `MOVE.W 1e(a6), -(a7); MOVE.B 14(a6), -(a7); MOVE.B a9(a6), d1; EXT.W d1; ADD.W d1, 42(a6); CLR.B a9(a6); MOVE.B aa(a6), d1; EXT.W d1; ADD.W d1, 46(a6); CLR.B aa(a6); MOVE.B 14(a6), d0; CMP.B 1b(a6), d0; BNE.W 3b3ea` (→`3b3e4`)
- `3b3e4`: `MOVE.B 1c(a6), 14(a6)` (→`3b3ea`)
- `3b3ea`: `MOVE.W #1, 1e(a6); BCLR.B #0, 94(a6); LEA.L 8c(a6), a0; JSR 49fca.l`
- `3b400`: `BCC.W 3b40a` (→`3b404`) — C 소비, FLOW
- `3b404`: `BSET.B #0, 94(a6)` (→`3b40a`) — FLOW
- `3b40a`: `JSR 43e34.l` — FLOW
- `3b410`: `MOVE.B (a7)+, 14(a6); MOVE.W (a7)+, 1e(a6); BTST.B #0, 94(a6); SNE.B d0; LSR.B #1, d0; RTS ` — C 계산 생산

**`3b542`(N31 `38ba0`, 범위 밖 `38b40`) 7**
- `3b542`: `MOVE.W #122, 20(a6); MOVE.L 2000b4.l, 22(a6); CMPI.B #1, 79(a6); BNE.W 3b560` (→`3b55a`)
- `3b55a`: `BSET.B #0, 15(a6)` (→`3b560`) — FLOW
- `3b560`: `JSR 3b22a(pc)` — FLOW
- `3b564`: `MOVE.B 1b(a6), 14(a6); BSET.B #6, 15(a6); MOVE.W #8810, 68(a6); MOVE.W #8810, 1e(a6); MOVEQ #11, d1; JSR 4d81c.l`
- `3b584`: `MOVE.B d1, ad(a6); MOVE.B d2, ae(a6); MOVE.W d3, 54(a6); MOVEA.L #3b118, a0; MOVE.W #a, d0; JSR 28ae.l`
- `3b5a0`: `BCC.W 3a2f4` (→`3b5a4`) — C 소비, FLOW
- `3b5a4`: `RTS ` — FLOW

**leaf `46bfc` 1**
- `46bfc`: `MOVEA.L 54c2(a5), a1; RTS ` — FLOW

**C 생산 `482aa` 3**
- `482aa`: `BTST.B #4, 5683(a5); BEQ.W 482ba` (→`482b4`) — FLOW
- `482b4`: `ANDI.B #fe, ccr; RTS ` — Clear 생산
- `482ba`: `ORI.B #1, ccr; RTS ` — Set 생산

**충돌 판정 `4b8e8`(u08b `4be86`, 범위 밖 `4bfc8`, N34 `4cd9e`)·`4b8e4` 48**
- `4b8e4`: `MOVEQ #0, d7; RTS `
- `4b8e8`: `JSR 482aa.l` — FLOW
- `4b8ee`: `BCS.B 4b8e4` (→`4b8f0`) — C 소비, FLOW
- `4b8f0`: `BTST.B #7, 61(a6); BNE.B 4b8e4` (→`4b8f8`) — FLOW
- `4b8f8`: `ADD.L d0, d2; ADD.L d1, d3; CMPA.W #0, a0; BEQ.W 4b914` (→`4b904`)
- `4b904`: `ADD.L 1c(a0), d0; ADD.L 20(a0), d1; ADD.L 14(a0), d2; ADD.L 18(a0), d3` (→`4b914`)
- `4b914`: `LEA.L 10daf8.l, a4; MOVEQ #0, d6; MOVEQ #0, d7` (→`4b91e`)
- `4b91e`: `MOVE.W d6, -(a7); MOVEA.L (a4)+, a3; MOVEA.L (a4)+, a2; CMPA.W #0, a2; BEQ.W 4baee` (→`4b92c`)
- `4b92c`: `MOVE.B 6d(a3), d4; ANDI.B #f, d4; CMP.B d6, d4; BNE.W 4baee` (→`4b93a`)
- `4b93a`: `MOVEQ #0, d4; MOVE.W 4(a2), d4; MOVE.W 8(a2), d5; BTST.B #0, 15(a3); BEQ.W 4b952` (→`4b94e`)
- `4b94e`: `ADD.W d5, d4; NEG.W d4` (→`4b952`)
- `4b952`: `SWAP d4; ADD.L 42(a3), d4; CMP.L d4, d2; BMI.W 4baee` (→`4b95e`)
- `4b95e`: `SWAP d4; ADD.W d5, d4; SWAP d4; CMP.L d4, d2; BPL.W 4baee` (→`4b96a`)
- `4b96a`: `MOVEQ #0, d5; MOVE.W 6(a2), d5; SWAP d5; ADD.L 46(a3), d5; CMP.L d5, d3; BPL.W 4b992` (→`4b97c`)
- `4b97c`: `SUB.L 46(a3), d5; ADD.L 4e(a3), d5; CMP.L d5, d1; BMI.W 4baee` (→`4b98a`)
- `4b98a`: `SUB.L 4e(a3), d5; ADD.L 46(a3), d5` (→`4b992`)
- `4b992`: `SWAP d5; ADD.W a(a2), d5; SWAP d5; CMP.L d5, d3; BMI.W 4b9b6` (→`4b9a0`)
- `4b9a0`: `SUB.L 46(a3), d5; ADD.L 4e(a3), d5; CMP.L d5, d1; BPL.W 4baee` (→`4b9ae`)
- `4b9ae`: `SUB.L 4e(a3), d5; ADD.L 46(a3), d5` (→`4b9b6`)
- `4b9b6`: `MOVE.W (a2), d6; CMPI.W #2, d6; BEQ.W 4b9fc` (→`4b9c0`)
- `4b9c0`: `CMPI.W #1, d6; BEQ.W 4b9cc` (→`4b9c8`)
- `4b9c8`: `BRA.W 4ba38` — FLOW
- `4b9cc`: `MOVE.L d5, d6; SUB.L 46(a3), d6; ADD.L 4e(a3), d6; CMP.L d6, d1; BMI.W 4ba38` (→`4b9dc`)
- `4b9dc`: `MOVE.L d4, d6; SWAP d6; SUB.W 2(a2), d6; SWAP d6; CMP.L d6, d2; BMI.W 4b9f4` (→`4b9ec`)
- `4b9ec`: `ORI.B #40, d7; BRA.W 4baee`
- `4b9f4`: `ORI.B #20, d7; BRA.W 4baee`
- `4b9fc`: `MOVE.L d5, d6; SUB.L 46(a3), d6; ADD.L 4e(a3), d6; CMP.L d6, d1; BMI.W 4ba16` (→`4ba0c`)
- `4ba0c`: `MOVE.L d5, d3; ORI.B #80, d7; BRA.W 4baee`
- `4ba16`: `SWAP d6; SUB.W a(a2), d6; SWAP d6; CMP.L d6, d1; BPL.W 4ba38` (→`4ba24`)
- `4ba24`: `SWAP d5; SUB.W a(a2), d5; SWAP d5; SUBQ.L #1, d5; MOVE.L d5, d3; ORI.B #80, d7; BRA.W 4baee`
- `4ba38`: `MOVE.L d4, d6; SUB.L 42(a3), d6; ADD.L 4a(a3), d6; CMP.L d6, d0; BMI.W 4ba58` (→`4ba48`)
- `4ba48`: `ORI.B #20, 6d(a3); MOVE.L d4, d2; ORI.B #80, d7; BRA.W 4baee`
- `4ba58`: `SWAP d6; SUB.W 8(a2), d6; SWAP d6; CMP.L d6, d0; BPL.W 4ba80` (→`4ba66`)
- `4ba66`: `ORI.B #10, 6d(a3); SWAP d4; SUB.W 8(a2), d4; SWAP d4; SUBQ.L #1, d4; MOVE.L d4, d2; ORI.B #80, d7; BRA.W 4baee`
- `4ba80`: `SWAP d6; ADD.W 2(a2), d6; SWAP d6; CMP.L d6, d0; BMI.W 4bac0` (→`4ba8e`)
- `4ba8e`: `ORI.B #20, 6d(a3); MOVE.L d2, d6; SUB.L d0, d6; SUB.L 42(a3), d6; ADD.L 4a(a3), d6; TST.L d6; BGE.W 4babc` (→`4baa6`)
- `4baa6`: `MOVE.L d0, d2; CMPA.W #0, a0; BEQ.W 4bab8` (→`4bab0`)
- `4bab0`: `SUB.L 1c(a0), d2; ADD.L 14(a0), d2` (→`4bab8`)
- `4bab8`: `ORI.B #80, d7` (→`4babc`)
- `4babc`: `BRA.W 4baee` — FLOW
- `4bac0`: `ORI.B #10, 6d(a3); MOVE.L d2, d6; SUB.L d0, d6; SUB.L 42(a3), d6; ADD.L 4a(a3), d6; TST.L d6; BLE.W 4baee` (→`4bad8`)
- `4bad8`: `MOVE.L d0, d2; CMPA.W #0, a0; BEQ.W 4baea` (→`4bae2`)
- `4bae2`: `SUB.L 1c(a0), d2; ADD.L 14(a0), d2` (→`4baea`)
- `4baea`: `ORI.B #80, d7` (→`4baee`)
- `4baee`: `MOVE.W (a7)+, d6; ADDQ.W #1, d6; CMPA.L #10db78, a4; BCS.W 4b91e` (→`4bafc`)
- `4bafc`: `CMPA.W #0, a0; BEQ.W 4bb14` (→`4bb04`)
- `4bb04`: `SUB.L 1c(a0), d0; SUB.L 20(a0), d1; SUB.L 14(a0), d2; SUB.L 18(a0), d3` (→`4bb14`)
- `4bb14`: `SUB.L d0, d2; SUB.L d1, d3; RTS `

**`4bce0`(입력·지형 판정, `BRA.W 4bc58` → u08b) 24**
- `4bce0`: `MOVE.B #ff, 549f(a5); CLR.B 54a0(a5); MOVEM.L d0-d7, -(a7); CMPA.L #100cb8, a6; BEQ.W 4bd6e` (→`4bcf8`)
- `4bcf8`: `CMPA.L #100da8, a6; BEQ.W 4bd6e` (→`4bd02`)
- `4bd02`: `JSR 4d8d8.l` — FLOW
- `4bd08`: `TST.B d0; BPL.W 4bd1e` (→`4bd0e`)
- `4bd0e`: `MOVE.B #ff, 54a2(a5); MOVE.B #ff, 54a3(a5); BRA.W 4bdfe`
- `4bd1e`: `MOVE.W d1, -(a7); MOVE.W 42(a6), d0; MOVE.W 46(a6), d1; MOVEQ #ff, d7; JSR 19a00.l`
- `4bd30`: `MOVE.W (a7)+, d1; MOVE.L #4bca8, d7; CMPI.B #4, d1; BEQ.W 4bdd6` (→`4bd40`)
- `4bd40`: `CMPI.B #8, d1; BEQ.W 4bdd6` (→`4bd48`)
- `4bd48`: `MOVE.L #4bcb0, d7; CMPI.B #9, d1; BEQ.W 4bdd6` (→`4bd56`)
- `4bd56`: `MOVE.L #4bcb8, d7; CMPI.B #5, d1; BEQ.W 4bdd6` (→`4bd64`)
- `4bd64`: `MOVE.L #4bca0, d7; BRA.W 4bdd6`
- `4bd6e`: `MOVE.B 81(a6), d7; SNE.B d7; EXT.W d7; MOVE.B 82(a6), d7; MOVE.W 42(a6), d0; MOVE.W 46(a6), d1; JSR 19a00.l`
- `4bd88`: `JSR 1aa3a.l` — FLOW
- `4bd8e`: `MOVE.L #4bcc0, d7; BTST.B #3, d0; BNE.W 4bdd6` (→`4bd9c`)
- `4bd9c`: `MOVE.L #4bcc8, d7; BTST.B #e, d0; BNE.W 4bdd6` (→`4bdaa`)
- `4bdaa`: `BTST.B #7, 61(a6); BNE.W 4bdd0` (→`4bdb4`) — FLOW
- `4bdb4`: `MOVE.L #4bcd0, d7; BTST.B #6, d0; BNE.W 4bdd6` (→`4bdc2`)
- `4bdc2`: `MOVE.L #4bcd8, d7; BTST.B #7, d0; BNE.W 4bdd6` (→`4bdd0`)
- `4bdd0`: `MOVE.L #4bca0, d7` (→`4bdd6`)
- `4bdd6`: `MOVE.L d7, 54a6(a5); MOVE.B 5c8c(a5), 54a2(a5); MOVE.B 5c8d(a5), 54a3(a5); JSR 1aa3a.l`
- `4bdec`: `BTST.B #6, d0; BNE.W 4bdf8` (→`4bdf4`) — FLOW
- `4bdf4`: `BRA.W 4bdfe` — FLOW
- `4bdf8`: `MOVE.B #1, 54a0(a5)` (→`4bdfe`)
- `4bdfe`: `MOVEM.L (a7)+, d0-d7; BRA.W 4bc58` — FLOW

**`4be50` `4be6c` 4**
- `4be50`: `JSR 4bc44(pc)` — FLOW
- `4be54`: `MOVE.B #ff, 549e(a5); MOVE.B #0, 10d49d.l; MOVEM.L 2e(a6), d0-d3/a0; BRA.W 4bf0a`
- `4be6c`: `BSR.W 4bce0` — FLOW
- `4be70`: `MOVE.B #0, 10d49d.l; MOVEM.L 2e(a6), d0-d3/a0; BRA.W 4bf0a`

**`4bfb4` 3**
- `4bfb4`: `BSR.W 4bce0` — FLOW
- `4bfb8`: `BSR.W 4c020` — FLOW
- `4bfbc`: `BRA.W 4bf0a` — FLOW

**`4c0ea` 2**
- `4c0ea`: `JSR 4bce0(pc)` — FLOW
- `4c0ee`: `BRA.B 4c0b0` — FLOW

**`4c37c` 2**
- `4c37c`: `MOVEA.L #4cf52, a0; MOVE.W #0, d0; JSR 28ae.l`
- `4c38c`: `BRA.W 4c7a4` — FLOW

**`4c7a4` 3**
- `4c7a4`: `CLR.W 76(a0); MOVE.W #80, 78(a0); CLR.W 7c(a0); CLR.W 7a(a0); CLR.W 7e(a0); CLR.W 80(a0); CLR.W 82(a0); CLR.W 96(a0); CLR.B 9b(a0); CLR.B 98(a0); CLR.B 99(a0); MOVEA.L 3e(a6), a1; MOVE.L 2e(a6), d0; MOVE.L 32(a6), d1; CMPA.W #0, a1; BEQ.W 4c7ee` (→`4c7e6`)
- `4c7e6`: `ADD.L 14(a1), d0; ADD.L 18(a1), d1` (→`4c7ee`)
- `4c7ee`: `LEA.L 538e(a5), a1; SUB.L 14(a1), d0; SUB.L 18(a1), d1; MOVE.L d0, 86(a0); MOVE.L d1, 8a(a0); MOVE.L d0, 8e(a0); MOVE.L d1, 92(a0); MOVE.L a1, 3e(a0); RTS `

## 작업자 검증 기록 (scratch, 커밋하지 않음)

Claude Opus 5.5 / high 작업자, 작업 트리 `/Users/start/Workspce/metalslug-n33`(기준 `c5181b6`), scratch `/Users/start/Workspce/ms5-scratch/n33/`. ROM SHA256 `29112a94…860f`·mtime `1791291625`·크기 8,388,608 불변.

- 산출(SHA256 앞 16자리): `engine/src/animation_machine_objects_n33.cpp` `5f3763afa464e2ce`, `engine/tests/animation_machine_objects_n33_test.cpp` `0569417507f78ed8`, `engine/src/animation_machine.cpp` `50f0b62639005979`(routing `else if` 1개 + carry 목록 group 1개), `engine/src/animation_machine_internal.h` `66e3b375cb81e395`(선언 1줄), `Makefile` `f2b42b21c038147a`(source·test target·run 줄), `tools/verify_animation_machine.py` `f11e6e74e5dfa2b7`(SOURCES), 탐침 이동(결정 4) `engine/tests/animation_machine_objects_u01_test.cpp` `f4bdd14714cfa584`, `..._u08b_test.cpp` `d940254207160c7b`, `..._u09_test.cpp` `2fb23b8188bed532`.
- scratch: `n33.py` `cf7f99eb04e105c1`, `cls33.py` `c878e119d0cc365f`, `unitdef_final.py` `824e465843df8e1f`, 생성기 `gen/gen33.py` `0768687c3590786d`(= `fw_head.py` + `build33.py` + `fw_tail.py`), `gen/tables_n33.inc` `56228f110317dd21`, `gen/facts33.txt` `e02c9c893fa3428a`, `gen/assemble33.py` `fc671b01ebd938cc`, 실제 ROM 차등 `realrom/real33.py` `f3c5b52cdcb0d530`, 돌연변이 `mut/mut33.py` `970cb819fee13973`, 두 번째 진입 patch `patch-u08b-4bc58.diff` `33f5d5dc6d144b32`.
- [F] `make -j3 all test`: exit 0, warning 0, `Assert` 줄 0(`make_all.log`). 242개 test 실행 파일을 개별로도 모두 통과(`testrun.log` 실패 0).
- [F] N33 test(run_animation_machine만): fixture 403(checked 오류 21, kept C 33), block 201 × C 3(소비 8은 Unknown에서 정확한 오류), zero-step 201 × 3, 내부 PC 947 전부 `unsupported animation objects n33 PC`, 홀수 PC 26, RAM 탐침 rollback, 경계 stop 37 PC(routing 밖 10 + 다른 실행부 27, `4bc58` 포함), RTS rollback 11. 생성기: Unicorn 고정 ROM + 합성 `2000b4`, 모든 data 읽기 검사, fixture가 201 시작 전부를 덮음. known C 확인 20건(`3b392` × 실제 소비자 N31 `38ce4`·N32a `38e12`, `3b410` × `38ce4`, `482aa` × `36282`·`4b8ee`; native 분기 = 모델, Unicorn SR 미사용).
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`): N33 test 통과, runtime error 0(`ubsan.log`).
- [F] 돌연변이 46개 전부 검출(`mut/mut.log`, 46/46). 첫 실행에서 `4bac0 BLE`→`BMI`(D6 = 0)가 살아남아 `4ba8e`/`4bac0` D6 = 0·±1 fixture 6개를 추가한 뒤 46/46.
- [F] 실제 ROM 차등(8개 `program_rom_*.ms5d`, bank 200000/300000, Unicorn vs C++): seed 1·2·3 각 6,000 case(cb ≈ 3,950, any ≈ 2,050), 불일치 0, 201 시작 전부 도달, 소비자 실제 생산자 뒤 native 분기 비교(seed 1: `3b16c` 236, `3b208` 158, `3b21e` 162, `3b380` 75, `3b38c` 187, `3b400` 156, `3b5a0` 248, `4b8ee` 384, `38ce4` 66, `38e12` 82). 의도된 차이 5건(seed 1: 2, seed 2: 3): 무작위 RAM의 animation 명령 BYTE가 interpreter 계산 분기 표 밖이라 C++ `unsupported animation command or dispatch alignment`(interpreter의 정적 경계, N33 밖). native 미정지 skip은 seed마다 약 1,060(대부분 interpreter·무작위 포인터). `4bc58`은 N33 `BRA.W`로 들어올 때만 선언 stop이다(u08b `4bc44` 안 직선 통과는 stop 아님).
- [F] 기준 frame pass(`verify_animation_machine_scheduler_f4.py` 복사본, OUT scratch): 기준 `c5181b6` 14,648 pass / 126,688 node 일치 → N33 14,648 / 126,694, 불일치 0. 첫 미routing 목록에서 `38ba0` 2가 `4cf52` 2로 바뀜.
- [F] RNG 400 frame(`verify_animation_machine_scheduler_rng_f4.py` 복사본): 기준 134 완주 / 53,600 pass / 403,677 node / 불일치 0 → N33 134 완주 / 53,600 pass / 403,683 node / 불일치 0, checks 모두 참(`other` 빈 목록), JSON SHA256 `21c76ea0f2d84cf8…`. 새 완주 seed 없음.
- [F] **seed 116 117 멈춤 위치**: 기준 frame 0 node 4(callback `38ba0`, A6 `10126c`) → N33 뒤 frame 0 node 7(callback `4cf52`, A6 `1014b8`, 첫 미routing PC `4cf52`, N35 범위 `4cf52..4cf64`). node 4~6이 N33으로 끝까지 실행되고(node 6개 추가 일치), frame 0 안에서 N35 `4cf52`([I] 자연 TB에 있는 `4c37c`가 만든 `28ae` 자식 callback)에서 멈춘다. [I] N35 뒤에는 N34 `4c3de..`·`4d8d8`(N35)와 결정 5의 `4bc58`이 다음 경계다.
