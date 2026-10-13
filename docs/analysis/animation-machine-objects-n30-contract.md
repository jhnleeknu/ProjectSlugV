# 객체 callback F4 N30(N30a): stage event `33132` 계열 객체 — callback `33132`·`331d8`, 설치 callback `336d2`(27 slot 표 `336e6`)·`337a8`, 공유 꼬리 `33958`/`33a88`, 설정 `33b12`, helper `33be0` `33c0e` `33c2a` `33c54`, interpreter 표 진입 `33f4c`, `28ae` 자식 callback `345c2`·`3471a`와 `JMP (A1)` 선택기 `346c6`·`34874` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N30 행(220 block, `33132..3383c` `33958..33c78` `33f4c..33f58` `345c2..34750` `34874..348a2`, 진입 `33132` `331d8` `345c2` `34650` `3471a` `34748`, 경계 callee 25, 간접 `346fa` `3489a`, 표 `335fa`:9, bank 1, 미실행 설치 9(+87), 옛 U42 198 + U43 22; seed 116 117 사슬의 일부)이다. 단위 형식과 규약은 N29 계약(`animation-machine-objects-n29-contract.md`, SHA256 `78b63ea277b5f727cb44f652c25cea6a74c11dc5ea5b5663347008329a7b0190`)과 N22 계약(LONG 표 + `JMP (A0)` live target, 결정 3)을 따른다. 메인 작업 지시:
- block 시작은 `MOVE.L #imm,(A6)` 설치 callback, DBRA 대상, JSR 복귀점을 포함한 정적 디코드로 정하고 재범위 수치와 다르면 보고한다(결정 2).
- 간접 점프 `346fa` `3489a`는 live target routing이다(allow list 없음). 계산 점프 표는 정적으로 묶이면 전부 전사하고, 아니면 F1 결정 3이다.
- 약 230 block을 넘으면 a/b 분할을 제안하고 a만 구현한다(정적 closure 326 block → N30a 166 + N30b 160, 결정 1).
- 범위 안 PC를 "routing 밖" 탐침으로 쓰는 기존 test는 RAM `10fe00..10fefe`(`10fe60` 이상 권장)로 옮긴다(해당 없음, 결정 9).
- 다른 단위 실행부의 두 번째 진입이 필요하면 고치지 않고 scratch patch와 결정으로 보고한다(N30a에는 해당 없음).

- 결정 관례(N29와 같음): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치, `28ae` 자식 값, 범위 밖에서 참조하는 범위 안 진입, interpreter LONG 표 `4a500` 대상, `LEA x(PC),A1` 계속 주소, 범위 안 LONG 표 대상, PC 상대 BRA.W 표 slot)로 정한다. Unicorn TB 분할은 시작이 아니다. 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N29 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDI`/`ADDQ`/`SUBQ`/`AND`/`ANDI`/`EXT`/`NEG` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`BSET`/`BCLR`/`SNE`/`ST`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `ORI` CCR은 known Set 생산이다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N30 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`2000a4`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n30`(HEAD `3535981` = N01~N25, N28(두 번째 진입 `30fa0` 포함), N29a 통합, `engine/src/animation_machine.cpp` SHA256 `2f16bea5ed3b4c88b96bd90c009e232f3f16b50f5c9154c4e9cd445cf870d6d8`, routing 규칙 84개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`, `engine/src/animation_machine_objects_n29.cpp` SHA256 `1d57937b0f481ebfada07969aa253fddb0902e35262802edff701a7439d2fadd`)을 참조했다. 재범위 N30 행 5 범위의 짝수 PC는 모두 기존 routing에 없다. N30a routing 9 범위의 양끝 이웃 `33130` `3323e` `336d0` `3383c` `33956` `3395c` `33a86` `33c78` `33f4a` `33f58` `345c0` `346c0` `346c4` `346fc` `34712` `34750` `34872` `348a2`도 routing 밖이다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n30/n30.py`(정적 디코드, SHA256 `b338673967131a3ff608d0fb0b58301c9a48699e7e16fdfa9b704327c70e84d8`; 전체 closure `starts.txt` SHA256 `e62f3a78bdb45b71a5644fae509585c25eb55b7e67779f4dbdd557e3af07a032`, N30a `startsA.txt` SHA256 `0f328d3fbc601f6a39a52b0b8f363ad2f380b5f0ec395d078b9a10b557e62167`)와 `cls30.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N30 전체 정적 closure = 326 block**(재범위 행 5 범위에서 자료 `346c0..346c6` `346fc..34714`를 뺀 코드 658 명령 전부 도달). 진입 13개(`33132` `331d8` `33336` `33b12` `33be0` `33f4c` `345c2` `3471a` `34650` `34748` `34874`와 LONG 표 `34708` 대상 `345f2` `34616` `34644`)에서 분기·fall-through·범위 안 설치·`28ae` 자식·`LEA x(PC),A1` 계속 주소·BRA.W 표 2개(`335fa` 9 slot, `336e6` 27 slot)를 끝까지 따라갔다. ~230을 넘으므로 나눈다(결정 1).
- [F] **N30a = 166 block**(9 routing 범위, 코드 1,556바이트, 짝수 PC 778, 내부 612). = 전체 closure − 설치 `3323e` 사슬(N30b 160: `3323e..336d2` 130 + `3395c..33a88` 30). seed 116 117이 자연 400 frame에 실행하는 N30 PC(TB 시작 57개 중 56개; 나머지 `34750`은 N31)는 모두 N30a 안에 있다.
- [F] 진입:
  - stage event 사슬의 callback `33132`(N29 `33124 MOVE.L #33132,(A6)`, N30b `33a0c` 설치, N30b `33546 BRA.W`). 범위 안 설치 `33180`(`3317a`, fall-through), `331d8`(`331d2`, fall-through), `33b0c`(`33192` `331f0`), `336d2`(`33a9a`), `337a8`(`3379c`, fall-through), `34608`(`34602`), `3462c`(`34626`), `34644`(`3463c`), `34650`(`3464a`, fall-through), `34748`(`34742`, fall-through).
  - 설정 `33b12`(N29 `3311c JSR 33b12(PC)`, 범위 밖 `330ac JSR`).
  - `28ae` 자식 값: `345c2`(`33bba MOVEA.L #345c2,A0`), `3471a`(`33bca`). `41fe6`(`33b7c`)은 N22다.
  - interpreter 표 진입 `33f4c`(LONG 표 `4a500`의 `4a5b4` = `00033f4c`; interpreter `JSR (A1)` live target).
  - helper `33be0`(N30b `33248`, 범위 밖 `33100 JSR`), `33c0e`(`337b8`, N30b 6곳), `33c2a`(`337b4`, N30b `33284`), `33c54`(`33180` `331d8` `337de`), `33c48`(N30b `33320` 등 5곳 JSR; N30a에서는 `33c3a` fall-through), `33c6c`(N30b `335cc` JSR; N30a에서는 `33c64` fall-through), `3465a`(`34610` `34634`).
  - 선택기 `346c6`(`34608` `3462c` `34650 BRA.W`, A1 = 계속 주소 `34610` `34634` `34658`), `34874`(`34748 BRA.W`, A1 = `34750`(N31); 범위 밖 `3477e` `347a4` `347ca` `347e6 BRA.W`, A1 = `34782` `347a8` `347ce` `347ea`).
  - LONG 표 `34708` 대상 `345f2`(k=0) `34616`(k=1) `34644`(k=2), LONG 표 `348a2` k=0 대상 `34742`.
  - 공유 꼬리 `33958`(`331a8` `3323a BRA.W`) → `33a88`, `33aa4`(`33838 BRA.W`, N30b `33636`).
- [F] **경계(실행부 없음, 현재 routing 밖) callee·출구 11개**: `33846`(`3374a` slot `BRA.W`; 범위 밖 함수 `3383c`의 `JSR 4ae4a` 복귀점), `33940`(`337c4`; 범위 밖 BYTE push helper), `33f1a`(`33ad4`), `34490`(`3380e`), `3453a`(`33812`), `4be6c`(`33c6c`), `4bfb4`(`33c5e JMP`), `4bfc0`(`33c34 JMP`), `4d418`(`33204` `337cc`; C 반환, `33212` 소비), `4d8d8`(`337a8` `337e2`), `4db18`(`33788`). live target `34750`(N31, `34748`의 계속 주소)도 routing 밖이다. `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **다른 실행부로 가는 callee·출구**: `288c`(stage_event_ops), `28ae` `2a00`(fade_card), `3af8`(sound), `8ebe`(U02), `43e34` `46ef4`(cleanup), `1aa7e` `4b54e`(U01), `49290`(U08), `492c8`(U12; `33c4e` `33c72 JMP`), `496c2`(U11), `49be0`(U06), `49f8c` `49fc6`(interpreter), `4be82`(U08b), `4d2d4` `4d508` `4d766` `4da4a`(N23), `4d81c`(stage_area), `41fe6`(N22, `28ae` 자식 값).
- [F] **범위 밖 설치·자식 값(실행 PC가 아님)**: 설치 `3323e`(N30b, `33234`), `3383c`(`33832`; 재범위 어느 단위에도 없음), `28ae` 자식 `41fe6`(N22); 자료 포인터 LONG `76` = `34906`(`33788`), LONG `56` = `34b66`(`33be0`).
- [F] **carry**(아래 "carry" 절): 소비 10 block(모두 FLOW), known 생산 1개(`33b90 ORI` Set), FLOW_ONLY 97개(소비 10 포함), Unknown 68개. 97 + 1 + 68 = 166.
- [F] X·DIVx/MULx·TRAP·I/O port 쓰기·bank 변경이 없다. N/Z 재계산이 없다(`3382e` BNE는 두 선행에 접어 넣음, 결정 3). PC 상대 BRA.W 표 1개(`336e6`, 27 slot; 결정 4). 레지스터 간접 제어 이동 2곳(`346fa` `3489a JMP (A1)`, live target; 결정 5).
- [F] 스택: JSR 복귀 LONG, `3467e MOVE.W D0,-(A7)` / `346a8 MOVE.W (A7)+,D0`(WORD, A7 ±2, 사이에 `JSR 49fc6` `JSR 43e34`).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen30.py`): RNG·base 두 기록 모두 seed 116 117만 N30 범위 PC 57개(TB 시작)를 실행한다: `33132..331a8`의 `33132` `3315e` `3316a` `33170`, `331ac..3323a`의 13개, `33958`, `33a88..33b04`의 9개, `33b12..33bde`의 10개, `33c54` `33c5e`, `33f4c`, `345c2` `345de` `345e8` `34644` `34650` `34658` `346c6` `346cc` `346d0` `346fa`, `3471a` `34732` `34742` `34748` `34874` `3487a` `3487e` `3488a` `3489a`, 그리고 N31 `34750`. callback 실행 수(seed 116, 117 같음): `33132` 1, `331d8` 80, `345c2` 1, `34650` 81, `3471a` 1, `34748` 81. N30b 범위와 `336d2..3383c` `33c0e..33c4e` `33be0` `345f2..34642` `3465a..346be` `34714` `3489c`는 자연 400 frame에서 실행되지 않는다.
- [F] 기준(`3535981`)에서 seed 116 117은 frame 0 `38ba0`(N31)에서 먼저 멈춘다. [I] N30a만으로는 새 완주 seed가 없다(재범위 N30 행과 같음). 116 117의 N30 자연 경로는 다시 `4bfb4`(N33, `33c5e JMP`)와 `34750`(N31, `3489a JMP (A1)`)에서 멈춘다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **분할: N30a 166 block 구현, N30b 160 block 미룸.** [F] 재범위 N30 5 범위의 정적 closure는 326 block이라 ~230을 넘는다.
   - seed 116 117이 자연 400 frame에 실행하는 N30 PC는 모두 `33132..3323e` `33958` `33a88..33c78` `33f4c` `345c2..34750` `34874..348a2` 안에 있다(`seen30.py`).
   - **권고(구현함): N30a = 326 − 설치 `3323e` 사슬 160 = 166 block.** N30b = `3323e..336d2`(130: 설치 `3323e`(N30a `33234`의 값)부터 `33250` 상태기계, 설치 `33280` `3329c` `332d6` `33364` `333f2` `3341a` `3349e` `33500` `3353a` `3359c`, 범위 밖 설치 `33336`(`33104`, 범위 밖 함수 `330a4`), 9 slot 표 `335fa`, 파괴 `3363a`(`2986` 자식 `338f8`)) + `3395c..33a88`(30: N30b 안에서만 `BRA.W 3395c`로 들어오는 꼬리 앞부분, `4d418` C → 설치 `33132`)이다. N30a 안의 어떤 block도 N30b 범위로 분기하지 않는다(N30a는 `3323e`를 값으로만 쓴다). N30b가 N30a로 들어오는 곳은 이미 N30a block 시작이다(`33132` `33a88` `33aa4` `33be0` `33c0e` `33c2a` `33c48` `33c6c`; `33c48` `33c6c`는 N30b의 JSR 대상이라 전체 closure 기준으로 N30a에 시작으로 둔다). 따라서 N30b는 N30a 실행부의 두 번째 진입을 요구하지 않는다.
   - N30b의 경계 callee: `33940` `33c78` `33d2c` `33dce` `33e48` `343e0` `34470` `34490` `3453a` `4c2c4`(C 반환, `33390 BCC`·`335b4 BCS` 소비) `4d418` `4d734` `4d98a` `4d9ba` `4ff96` `d3d7c`; 다른 실행부 `2986`(buffer_cue, `2986` caller-X 제한) `3af8` `443d2` `46ef4` `49214` `496c2` `49f8c` `49fc6` `4ae4a` `4d7a6` `2a00`.
   - 대안: 자연 경로 함수만(`336d2..3383c` 55 block도 N30b로) N30a = 111로 하고 N30b = 215로 둔다. `336d2`는 N30a 공유 꼬리 `33a9a`가 설치하는 값이라 N30a에 두는 편이 단위 경계가 깔끔하다(권고안).
2. **재범위 수치와 다른 점.** [F] 재범위 N30 행은 220 block(함수 13개: `33180` `345c2` `331d8` `34748` `337a8` `33f4c` `34650` `33132` `33b12` `33c54` `34658` `3353a` `3471a`; scratch `rescope/units.pkl`·`build.pkl`)이다. 이 계약의 전체 closure 326과의 차이:
   - 재범위에만 있는 시작: `3382e`(이 계약은 flag 접기로 시작에서 뺌, 결정 3).
   - 이 계약에만 있는 시작 107개: 미실행 설치 본문 `3323e` 사슬(`3323e..33332` 30개, `33364` `333f2` `33408..33478` `3349e` `33500` `3359c`), 미실행 설치 `336d2` 본문(`336d2` `336de` 27 slot `336ea..33752`, `33756..3379c`), LONG 표 `34708` 대상과 그 사슬(`345f2..34642`), helper `33be0` `33c0e..33c28` `33c2a..33c4e` `33c6c` `3465a..346be`. 재범위는 함수 본문을 실행된 진입에서 설치를 따르지 않고 셌다([I] "미실행 설치 9(+87)"가 이 차이의 일부).
   - **표**: 재범위의 "표 `335fa`:9"는 N30b에 있다. 재범위에 없는 **27 slot 표 `336e6`**(설치 `336d2`의 `CMPI.B #1b,D0; BCC`)이 N30a에 있다(결정 4).
   - **간접**: `346fa` `3489a`(둘 다 `JMP (A1)`)는 같다.
   - **경계 callee**: 전체 closure에서 현재 routing 밖 callee는 23개(`33940` `33c78` `33d2c` `33dce` `33e48` `33f1a` `343e0` `34470` `34490` `3453a` `4be6c` `4bfb4` `4bfc0` `4c2c4` `4d418` `4d734` `4d8d8` `4d98a` `4d9ba` `4db18` `4ff96` `d3d7c`, 출구 `33846`)와 live target `34750`이다. 재범위 25와의 차이는 재범위 기준 routing(N23 이전, `4d2d4` `4d508` `4d766` `4da4a`가 routing 밖)과 집계 방식 차이로 본다([I]). N30a만은 10 callee + 출구 `33846` + live target `34750`이다.
   - **bank**: `2000a4` 한 주소(읽기 3곳 `33b12` `345c2` `3471a`)로 같다. **기타 9(+87)**: 이 계약에서 따로 세지 않았다([U]).
   - **새 완주 seed**: 재범위와 같이 없다(아래 검증 기록).
3. **`3382e BNE.W 33838` flag 접기.** [F] `3382e`는 `33826 BEQ.W 3382e`(앞 `33822 TST.B 92(A6)`, 분기하면 Z = 1)와 `3382a SUBQ.B #1,92(A6)`의 fall-through 두 곳에서 들어오고 Z를 읽는다. 선행이 둘이므로 재계산하지 않고 각 선행에 접는다: `3381c`는 BYTE `92` = 0이면 바로 `33832`(Z = 1이라 `BNE` 불성립), 아니면 `3382a`; `3382a`는 감소 결과 ≠ 0이면 `33838`, 아니면 `33832`. `3382e`는 block 시작이 아니고 내부 PC다(다른 참조 없음, scratch `xref30.py`).
4. **표 `336e6`: 27 slot, 정적 상한, 전부 전사.** [F] `336d2 MOVE.B 5e(A6),D0; CMPI.B #1b,D0; BCC.W 33756`이 무부호 `D0.B` < `1b`만 `336de`로 보낸다. `336de ANDI.W #ff,D0; ADD.W D0,D0; ADD.W D0,D0; JMP 336ea(PC,D0.W)`이므로 자연 index는 0..26, slot은 `336ea`+4·k(`336ea..33752`, 각 `BRA.W` 4바이트)다. 27 slot을 모두 block 시작(FLOW)으로 옮긴다: k = 24(`3374a`) → `33846`(routing 밖 출구), 그 밖 26개 → `33756`. F1 메인 결정 3(N18 `86298`, N29 `30a72` 선례)대로 `336de`는 상한 검사 없이 PC = `336ea` + sext((4·(`D0.W` & `ff`)) & `ffff`)로 옮긴다. `336de`로 바로 들어온 typed 입력에서 `D0.B` ≥ `1b`이면 대상은 `33756`(k = 27, block 시작), N30a 내부 PC(`unsupported animation objects n30 PC`, 예: k = 28 → `3375a`), N30b 범위·범위 밖(`unsupported animation machine PC`)이다. [I] 원본은 `336d2`를 거치지 않으면 표 밖으로 뛴다.
5. **LONG 표 + `JMP (A1)` live target 두 곳(전사하지 않음).** [F] N22 결정 3과 같은 꼴이다.
   - 선택기 `346c6`: `JSR 288c`(Clear → `34714 JMP 2a00`), `346d0`: `D0.B` = BYTE `9a(A0)`(A0 = 288c가 돌려준 부모), `D7.B` = (4·BYTE `9a(A6)` + `D0.B`) & `ff`, `D7.W` &= `ff`, `D7.B` = BYTE(`346fc` + `D7.W`)(BYTE 표 `346fc..34708` = `00 01 01 00 01 00 01 00 01 00 00 00`; 행 = 자기 `9a`, 열 = 부모 `9a`); 0이면 `346fa JMP (A1)`(A1 = 호출자의 `LEA x(PC),A1` 계속 주소 `34610` `34634` `34658`), 아니면 `346ea`: BYTE `9a(A6)` = `D0.B`, A1 = LONG(`34708` + 4·(`D0.W` & `ff`))(LONG 표 `34708..34714` = `345f2` `34616` `34644`), `346fa JMP (A1)`. 
   - 선택기 `34874`: `JSR 288c`(Clear → `3489c JMP 2a00`), `3487e`: `D0.B` = BYTE `9b(A0)`; BYTE `9b(A6)`와 같으면 `3489a JMP (A1)`(계속 주소 `34750` 등), 아니면 `3488a`: BYTE `9b(A6)` = `D0.B`, A1 = LONG(`348a2` + 4·(`D0.W` & `ff`))(범위 밖 LONG 표 `348a2..`: `34742` `34752` `34792` `347b8` `347d4` `356fe` `3598a` `35c16` `35ea2` `35734` `359c0` `35c4c` …; 끝은 정적으로 정해지지 않음), `3489a JMP (A1)`.
   - 색인은 BYTE(0..`ff`)라 정적 상한은 256 LONG이지만 표 자료는 짧고 그 뒤는 코드 바이트다. BRA.W 점프 표가 아니라 자료 LONG 읽기 + 레지스터 간접 점프이므로 live bus 읽기와 live target routing(`PC` = A1; 홀수면 `unaligned animation machine PC`, routing 밖이면 `unsupported animation machine PC`)으로 둔다. 범위 안 LONG 대상(`345f2` `34616` `34644` `34742`)과 계속 주소(`34610` `34634` `34658`)만 block 시작이다. [I] 원본은 `9a` ≤ 2, `9b`가 표 길이 안이라는 자료 전제를 둔다. 메인이 "전사"를 요구하면 F1 결정 3 대상이다.
6. **경계 callee C·반환값 소비.** [F] `33212 BCC.W 3323a`는 경계 `4d418`의 C를 읽는다. 실행부가 없으므로 N30a 안에서는 typed fixture(진입 C 선언)로만 실행하고, Unknown C면 `objects n30 caller requires known carry`다. [U] `4d418`의 C 생산은 그 단위가 정한다(N29 결정 6과 같음, 미배정). `33200`(N23 `4d2d4`)·`33ac2`(N23 `4d766`)·`3318e` `331ec`(U01 `1aa7e`)·`33b8c` `33bda`(`28ae`)·`346cc` `3487a`(`288c`)는 실제 생산자를 native로 따라가 확인한다. `34638 BCC.W 34642`는 `3465a`가 `346be RTS`(FLOW)로 돌려주는 interpreter `49fc6`의 C다.
7. **범위 밖 설치 값·출구.** [F] `33832 MOVE.L #3383c,(A6)`의 `3383c`(함수 `3383c..3393e`: `4ae4a` `33940` `4ff96` `d3d7c` 네 번 `2986` 자식 `338f8`, `49214`, `JMP 2a00`; 설치 `33928`)와 slot `3374a BRA.W 33846`(같은 함수의 `JSR 4ae4a` 복귀점), `337c4 JSR 33940`(`33940..33958` BYTE push + `JSR 4d8d8` helper)은 재범위 어느 단위에도 없다(N29 결정 2의 `3169c` `319b6`와 같은 꼴). routing하지 않는다. [I] 고아 정리 단계 몫이다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n30.cpp`의 `animation_objects_n30_block`. 오류는 `unsupported animation objects n30 PC`(내부 PC), `objects n30 caller requires known carry`(소비 10 block). N29와 같은 꼴이다.
9. **무효화 탐침 없음(탐침 이동 없음).** [F] `engine/tests`·`engine/src`·`tools/*.py`의 16진 토큰(`0x` 접두 5~6자리)과 맨 16진 문자열 중 재범위 N30 5 범위의 값은 N29 실행부·test의 경계 stop `33b12`(`3310c-*` `3311c` fixture와 block 표 `3311c` 행; stop만)와 설치 값 `33132`(`33124`), N04 test 출력 레지스터 값 `0x33b18`, U11 test 레지스터 값 `0x3320f` `0x3468b`(홀수)뿐이다. "routing 밖" 탐침이나 rollback 기대로 쓰는 곳은 없으므로 `10fe60..` 이동 대상이 없다. N29 test의 stop 행은 N30a 뒤에도 그 PC에서 멈춘다(stop은 routing 전에 판정).
10. **`2986` caller-X 제한 해당 없음.** [F] N30a는 `2986`을 부르지 않는다(N30b `336b2`, 범위 밖 `338d8`만 부른다).

## 원본 바이트 근거

[F] N30a 코드 9 범위 합계 1,556바이트(짝수 PC 778개, 시작 166, 내부 612). 범위 순서로 이어 붙인 SHA256 `0d709526d7fae98b0af60685944294bbf60438483facda8b6c4c2959b5a7426c`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `33132..3323e` | 268 | `f75c02d23ac075aae6b3df64f5d893a9d7e93d044d1ee1a6f38daf75bca8ea7a` | 28 |
| `336d2..3383c` | 362 | `2864a789612366a24c6ff2823ad6d1e7c6c92062f5738cc085fa91868da74c37` | 55 |
| `33958..3395c` | 4 | `dec8c1489c63ac769d84f191cfff0990c14c705226abf968bc818d02838b5590` | 1 |
| `33a88..33c78` | 496 | `28483092b30abb04d61c54b3673ff1f5f15d2d903179fad13c0e619c3a26a564` | 42 |
| `33f4c..33f58` | 12 | `d402ad22540a552edd122bb83c9ed2491a974b450f1edf60297923c8881fc5e0` | 1 |
| `345c2..346c0` | 254 | `18728e95f224cb45808e8295e9e3d25a1e9cedfd007e59b05a9483728e5608b4` | 23 |
| `346c6..346fc` | 54 | `3c197edc0a829be7fc01bb3b3104a5ee1ffed7e3a688833e07ea5e908d42061b` | 5 |
| `34714..34750` | 60 | `412fd5bc56b8b7301a4f722db4df601cd87234eed4c807ae5086d3608fa88592` | 5 |
| `34874..348a2` | 46 | `53e6ab299228a6f04c162006b91bf4397fa464cb7d5ee4943e2b79999c649d96` | 6 |

- [F] 범위 이웃: `33132` 앞 `330a4..3310c`(범위 밖 함수: `33b12` `33be0` 호출, 설치 `33336`)·`3310c..3312c`(N29), `3323e..336d2`·`3395c..33a88`(N30b, 결정 1), `3383c..33958`(범위 밖 함수 `3383c`와 helper `33940`, 결정 7), `33c78..33f4c`(범위 밖 `33c78` `33d2c` `33dce` `33e48` `33f1a` 등; 재범위 어느 단위에도 없음), `33f58..345c2`(범위 밖 `343e0` `34470` `34490` `3453a` 등), 자료 `346c0..346c6`(BYTE 표 `02 01 00 ff fe 00`, `3467e`가 읽음)·`346fc..34714`(BYTE 표 12 + LONG 표 3), `34750..34752`(N31 `RTS`), `34752..34874`(범위 밖 `34752` `34792` `347b8` `347d4` 등; 표 `348a2` 대상), `348a2..`(LONG 표, 자료).
- [F] 우연 일치(실행 진입 아님): 고정 ROM의 LONG `00033140`(`4779a` `60b88`), `0003317c`(`43e16` `43e28`), `00033333`(홀수), `0003343c`(`6f83a` 등 14곳), `00033800`(`244dc` 등 14곳), `00033960`(`e635a`), `00033a2e`(`d661e`, 명령 중간), `00033b40`(`48112`), `00033c20`(`1500`, 명령 중간), `00034882`(`2b624`)와 `JSR 46ef4`의 확장어 `6ef4`(`33168` `3358c` `33786`)는 명령 중간·홀수이거나 수치 상수다([I]).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "Set 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)·`(An,Dn.W)`·`d8(PC,Dn.W)`는 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. 비교·`TST`·`BTST`·산술과 그 Bcc는 같은 block 안에 있다. `3381c`의 `BEQ.W 3382e`는 결정 3대로 `33832`로 접는다(`3382e`는 내부 PC).

**callback `33132`(N29 `33124` 설치·N30b `33a0c` 설치·`33546 BRA`; 애니메이션 `34c80`, `46ef4` `496c2`, `BTST 15` bit 7, 설치 `33180`(fall-through), `33c54`·`1aa7e`(사각형 `349ce`), 설치 `33b0c`, `49fc6`, 끝 `BRA 33958`) 12**
- `33132`: `MOVE.B #1, 9a(a6); MOVE.B #0, 9b(a6); MOVE.L #0, 76(a6); MOVE.L #0, 56(a6); MOVEA.L #34c80, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3315e`: `MOVE.B 1b(a6), 14(a6); JSR 46ef4.l`
- `3316a`: `JSR 496c2.l` — FLOW
- `33170`: `BTST.B #7, 15(a6); BNE.W 331ac` (→`3317a`) — FLOW
- `3317a`: `MOVE.L #33180, (a6)` (→`33180`)
- `33180`: `JSR 33c54(pc)` — FLOW
- `33184`: `LEA.L 349ce(pc), a0; JSR 1aa7e.l` — FLOW
- `3318e`: `BCC.W 33198` (→`33192`) — C 소비, FLOW
- `33192`: `MOVE.L #33b0c, (a6)` (→`33198`)
- `33198`: `BTST.B #7, 15(a6); BNE.W 331ac` (→`331a2`) — FLOW
- `331a2`: `JSR 49fc6.l` — FLOW
- `331a8`: `BRA.W 33958` — FLOW

**`331ac`(`33176` `3319e BNE`; 애니메이션 `34c80`, `496c2`, `4da4a`, 설치 callback `331d8`(fall-through): `33c54` `49fc6`, `1aa7e`(사각형 `349ce`), 설치 `33b0c`, `4d2d4`(`349e6`), `4d418`, `4d508`, 설치 `3323e`(N30b 값), 끝 `BRA 33958`) 16**
- `331ac`: `MOVE.B #0, 9b(a6); MOVEA.L #34c80, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `331c2`: `JSR 496c2.l` — FLOW
- `331c8`: `MOVEQ #10, d0; MOVEQ #30, d1; JSR 4da4a.l`
- `331d2`: `MOVE.L #331d8, (a6)` (→`331d8`)
- `331d8`: `JSR 33c54(pc)` — FLOW
- `331dc`: `JSR 49fc6.l` — FLOW
- `331e2`: `LEA.L 349ce(pc), a0; JSR 1aa7e.l` — FLOW
- `331ec`: `BCC.W 331f6` (→`331f0`) — C 소비, FLOW
- `331f0`: `MOVE.L #33b0c, (a6)` (→`331f6`)
- `331f6`: `LEA.L 349e6(pc), a0; JSR 4d2d4.l` — FLOW
- `33200`: `BCC.W 3323a` (→`33204`) — C 소비, FLOW
- `33204`: `MOVE.W d0, 7a(a6); MOVEQ #c, d2; MOVEQ #18, d3; JSR 4d418.l`
- `33212`: `BCC.W 3323a` (→`33216`) — C 소비, FLOW
- `33216`: `MOVE.W d0, 7c(a6); MOVE.W 7a(a6), d0; MOVE.B #4, d1; MOVE.B 93(a6), d2; MOVE.B 94(a6), d3; MOVE.W 54(a6), d4; JSR 4d508.l`
- `33234`: `MOVE.L #3323e, (a6)` (→`3323a`)
- `3323a`: `BRA.W 33958` — FLOW

**설치 callback `336d2`(`33a9a`; BYTE `5e` 27 slot BRA.W 표 `336e6`, 애니메이션 `34bec`, 설치 callback `337a8`(fall-through): `4d8d8` 두 번, `33c2a` `33c0e` `33940`, `4d418` / `33c54`, 애니메이션 `34cf6`·`34490` `3453a`, BYTE `92` 타이머, 설치 `3383c`(범위 밖 값), 끝 `BRA 33aa4`) 55**
- `336d2`: `MOVE.B 5e(a6), d0; CMPI.B #1b, d0; BCC.W 33756` (→`336de`)
- `336de`: `ANDI.W #ff, d0; ADD.W d0, d0; ADD.W d0, d0; JMP 336ea(pc, d0.w)`
- `336ea`: `BRA.W 33756` — FLOW
- `336ee`: `BRA.W 33756` — FLOW
- `336f2`: `BRA.W 33756` — FLOW
- `336f6`: `BRA.W 33756` — FLOW
- `336fa`: `BRA.W 33756` — FLOW
- `336fe`: `BRA.W 33756` — FLOW
- `33702`: `BRA.W 33756` — FLOW
- `33706`: `BRA.W 33756` — FLOW
- `3370a`: `BRA.W 33756` — FLOW
- `3370e`: `BRA.W 33756` — FLOW
- `33712`: `BRA.W 33756` — FLOW
- `33716`: `BRA.W 33756` — FLOW
- `3371a`: `BRA.W 33756` — FLOW
- `3371e`: `BRA.W 33756` — FLOW
- `33722`: `BRA.W 33756` — FLOW
- `33726`: `BRA.W 33756` — FLOW
- `3372a`: `BRA.W 33756` — FLOW
- `3372e`: `BRA.W 33756` — FLOW
- `33732`: `BRA.W 33756` — FLOW
- `33736`: `BRA.W 33756` — FLOW
- `3373a`: `BRA.W 33756` — FLOW
- `3373e`: `BRA.W 33756` — FLOW
- `33742`: `BRA.W 33756` — FLOW
- `33746`: `BRA.W 33756` — FLOW
- `3374a`: `BRA.W 33846` — FLOW
- `3374e`: `BRA.W 33756` — FLOW
- `33752`: `BRA.W 33756` — FLOW
- `33756`: `MOVEA.L #34bec, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `33766`: `MOVE.B #4, 9b(a6); MOVE.B #1, 9a(a6); MOVE.W #1ac8, d0; JSR 3af8.l`
- `3377c`: `JSR 496c2.l` — FLOW
- `33782`: `JSR 46ef4.l` — FLOW
- `33788`: `MOVE.L #34906, 76(a6); MOVEQ #10, d0; MOVE.W #2c, d1; JSR 4db18.l`
- `3379c`: `MOVE.B #60, 92(a6); MOVE.L #337a8, (a6)` (→`337a8`)
- `337a8`: `JSR 4d8d8.l` — FLOW
- `337ae`: `TST.B d0; BMI.W 337de` (→`337b4`)
- `337b4`: `JSR 33c2a(pc)` — FLOW
- `337b8`: `JSR 33c0e(pc)` — FLOW
- `337bc`: `BTST.B #5, d0; BEQ.W 337cc` (→`337c4`) — FLOW
- `337c4`: `MOVE.B #4, d1; JSR 33940(pc)`
- `337cc`: `MOVE.W 7a(a6), d0; MOVEQ #c, d2; MOVEQ #18, d3; JSR 4d418.l`
- `337da`: `BRA.W 337e2` — FLOW
- `337de`: `JSR 33c54(pc)` — FLOW
- `337e2`: `JSR 4d8d8.l` — FLOW
- `337e8`: `TST.B d0; BPL.W 33816` (→`337ee`)
- `337ee`: `CMPI.B #0, 9b(a6); BEQ.W 33816` (→`337f8`)
- `337f8`: `MOVE.B #0, 9b(a6); MOVEA.L #34cf6, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3380e`: `JSR 34490(pc)` — FLOW
- `33812`: `JSR 3453a(pc)` — FLOW
- `33816`: `JSR 49fc6.l` — FLOW
- `3381c`: `MOVE.W #8000, 8a(a6); TST.B 92(a6); BEQ.W 3382e` (→`3382a`)
- `3382a`: `SUBQ.B #1, 92(a6); BNE.W 33838` (→`33832`)
- `33832`: `MOVE.L #3383c, (a6)` (→`33838`)
- `33838`: `BRA.W 33aa4` — FLOW

**공유 꼬리 `33958`(`BRA 33a88`) / `33a88`(`4b54e`, BYTE `61` bit 7 → 설치 `336d2`, `4d766`, BYTE `14` 선택, RTS) / `33b0c JMP 2a00`(설치 값) 17**
- `33958`: `BRA.W 33a88` — FLOW
- `33a88`: `JSR 4b54e.l` — FLOW
- `33a8e`: `BTST.B #7, 61(a6); SNE.B d0; BEQ.W 33aa0` (→`33a9a`) — FLOW
- `33a9a`: `MOVE.L #336d2, (a6)` (→`33aa0`)
- `33aa0`: `AND.B d0, 5e(a6)` (→`33aa4`)
- `33aa4`: `BCLR.B #6, 61(a6); TST.W 7e(a6); BEQ.W 33abc` (→`33ab2`)
- `33ab2`: `SUBQ.W #1, 7e(a6); BSET.B #6, 61(a6)` (→`33abc`)
- `33abc`: `JSR 4d766.l` — FLOW
- `33ac2`: `BCC.W 33acc` (→`33ac6`) — C 소비, FLOW
- `33ac6`: `BSET.B #6, 61(a6)` (→`33acc`) — FLOW
- `33acc`: `TST.L 76(a6); BEQ.W 33ae8` (→`33ad4`)
- `33ad4`: `MOVE.B 1a(a6), 14(a6); JSR 33f1a(pc)`
- `33ade`: `BSET.B #6, 61(a6); BRA.W 33b04` — FLOW
- `33ae8`: `MOVE.B 1b(a6), 14(a6); MOVE.W 7e(a6), d0; ANDI.W #1, d0; BEQ.W 33b04` (→`33afa`)
- `33afa`: `MOVE.B 19(a6), 14(a6); ST.B 8c(a6)` (→`33b04`)
- `33b04`: `MOVE.B #2, 95(a6); RTS`
- `33b0c`: `JMP 2a00.l` — FLOW

**설정 `33b12`(N29 `3311c`·범위 밖 `330ac JSR`; bank LONG `2000a4`, `8ebe` 세 번, `4d81c`, `28ae` 자식 `41fe6` `345c2` `3471a`) 11**
- `33b12`: `MOVE.W #102, 20(a6); MOVE.L 2000a4.l, 22(a6); MOVE.W #ce, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `33b2e`: `MOVE.W #ce, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `33b3c`: `MOVE.W #d, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `33b4a`: `MOVE.W #8810, 68(a6); MOVE.W #8810, 1e(a6); MOVEQ #4, d1; JSR 4d81c.l`
- `33b5e`: `MOVE.B d1, 93(a6); MOVE.B d2, 94(a6); MOVE.W d3, 54(a6); MOVE.B #2, 9a(a6); MOVE.B #0, 9b(a6); MOVE.B #5, 8e(a6); MOVEA.L #41fe6, a0; MOVE.W #a, d0; JSR 28ae.l`
- `33b8c`: `BCC.W 33bba` (→`33b90`) — C 소비, FLOW
- `33b90`: `LEA.L 8a(a6), a1; MOVE.L a1, 76(a0); MOVE.B #1, 7a(a0); MOVE.B #0, 7b(a0); MOVE.B #0, 7c(a0); MOVE.B #0, 7d(a0); MOVE.B #0, 7e(a0); ORI.B #1, ccr` (→`33bba`) — Set 생산
- `33bba`: `MOVEA.L #345c2, a0; MOVE.W #a, d0; JSR 28ae.l`
- `33bca`: `MOVEA.L #3471a, a0; MOVE.W #a, d0; JSR 28ae.l`
- `33bda`: `BCC.W 33b0c` (→`33bde`) — C 소비, FLOW
- `33bde`: `RTS` — FLOW

**helper `33be0`(N30b `33248`·범위 밖 `33100 JSR`), `33c0e`, `33c2a`(+`33c48` `33c4e`), `33c54`(+`33c6c` `33c72`) 15**
- `33be0`: `MOVEQ #0, d0; MOVE.B d0, 5e(a6); MOVE.B d0, 90(a6); MOVE.B d0, 91(a6); MOVE.W #1e, 7e(a6); MOVE.L d0, 76(a6); MOVE.B #2, 95(a6); MOVE.B #ff, 96(a6); MOVE.L #34b66, 56(a6); RTS`
- `33c0e`: `MOVE.W 7a(a6), d0; JSR 49be0.l`
- `33c18`: `MOVE.W (a0), d0; BTST.B #6, d0; BEQ.W 33c28` (→`33c22`)
- `33c22`: `MOVE.B #f, 90(a6)` (→`33c28`)
- `33c28`: `RTS` — FLOW
- `33c2a`: `BTST.B #7, 15(a6); BEQ.W 33c3a` (→`33c34`) — FLOW
- `33c34`: `JMP 4bfc0.l` — FLOW
- `33c3a`: `MOVE.L 64(a6), 36(a6); ADDI.L #ffffb000, 3a(a6)` (→`33c48`)
- `33c48`: `JSR 4be82.l` — FLOW
- `33c4e`: `JMP 492c8.l` — FLOW
- `33c54`: `BTST.B #7, 15(a6); BEQ.W 33c64` (→`33c5e`) — FLOW
- `33c5e`: `JMP 4bfb4.l` — FLOW
- `33c64`: `ADDI.L #ffffb000, 3a(a6)` (→`33c6c`)
- `33c6c`: `JSR 4be6c.l` — FLOW
- `33c72`: `JMP 492c8.l` — FLOW

**interpreter 표 진입 `33f4c`(LONG `4a5b4`) 1**
- `33f4c`: `MOVEA.L (a0), a0; MOVE.W (a0), 8a(a6); MOVE.W (a0), 88(a6); RTS`

**`28ae` 자식 callback `345c2`(`33bbc`), LONG 표 `34708` 대상 `345f2` `34616` `34644`, 설치 `34608` `3462c` `34650`, 계속 주소 `34610` `34634` `34658`, helper `3465a`, 선택기 `346c6`(BYTE 표 `346fc`, LONG 표 `34708`, `JMP (A1)` live target) 28**
- `345c2`: `MOVE.W #102, 20(a6); MOVE.L 2000a4.l, 22(a6); MOVE.W #f, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `345de`: `MOVEQ #0, d0; MOVEQ #0, d1; JSR 49290.l`
- `345e8`: `MOVE.B #2, 9a(a6); BRA.W 34644`
- `345f2`: `MOVEA.L #354f2, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `34602`: `MOVE.L #34608, (a6)` (→`34608`)
- `34608`: `LEA.L 34610(pc), a1; BRA.W 346c6` — FLOW
- `34610`: `JSR 3465a(pc)` — FLOW
- `34614`: `RTS` — FLOW
- `34616`: `MOVEA.L #35650, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `34626`: `MOVE.L #3462c, (a6)` (→`3462c`)
- `3462c`: `LEA.L 34634(pc), a1; BRA.W 346c6` — FLOW
- `34634`: `JSR 3465a(pc)` — FLOW
- `34638`: `BCC.W 34642` (→`3463c`) — C 소비, FLOW
- `3463c`: `MOVE.L #34644, (a6)` (→`34642`)
- `34642`: `RTS` — FLOW
- `34644`: `MOVE.B #2, 9a(a6); MOVE.L #34650, (a6)` (→`34650`)
- `34650`: `LEA.L 34658(pc), a1; BRA.W 346c6` — FLOW
- `34658`: `RTS` — FLOW
- `3465a`: `MOVEA.L c(a6), a0; MOVE.W 1e(a0), 1e(a6); MOVE.B 88(a0), d0; MOVE.B 89(a0), d1; EXT.W d0; EXT.W d1; MOVE.W d0, 2e(a6); MOVE.W d1, 32(a6); JSR 43e34.l`
- `3467e`: `MOVEA.L c(a6), a0; MOVE.B 84(a0), 8f(a6); MOVE.B 85(a0), d0; ANDI.W #ff, d0; MOVE.B 346c0(pc, d0.w), d0; EXT.W d0; MOVE.W d0, -(a7); ADD.W d0, 46(a6); JSR 49fc6.l`
- `346a2`: `JSR 43e34.l` — FLOW
- `346a8`: `MOVE.W (a7)+, d0; NEG.W d0; ADD.W d0, 46(a6); ADDQ.W #6, 42(a6); SUBQ.W #1, 1e(a6); JSR 49fc6.l`
- `346be`: `RTS` — FLOW
- `346c6`: `JSR 288c.l` — FLOW
- `346cc`: `BCC.W 34714` (→`346d0`) — C 소비, FLOW
- `346d0`: `MOVE.B 9a(a0), d0; MOVE.B 9a(a6), d7; ADD.B d7, d7; ADD.B d7, d7; ADD.B d0, d7; ANDI.W #ff, d7; MOVE.B 346fc(pc, d7.w), d7; BEQ.W 346fa` (→`346ea`)
- `346ea`: `MOVE.B d0, 9a(a6); ANDI.W #ff, d0; ADD.W d0, d0; ADD.W d0, d0; MOVEA.L 34708(pc, d0.w), a1` (→`346fa`)
- `346fa`: `JMP (a1)` — FLOW

**`34714 JMP 2a00` / `28ae` 자식 callback `3471a`(`33bcc`), 설치 `34748`, 선택기 `34874`(LONG 표 `348a2`, `JMP (A1)` live target; 범위 밖 `3477e` `347a4` `347ca` `347e6 BRA`) / `3489c JMP 2a00` 11**
- `34714`: `JMP 2a00.l` — FLOW
- `3471a`: `MOVE.W #102, 20(a6); MOVE.L 2000a4.l, 22(a6); MOVEQ #0, d0; MOVEQ #0, d1; JSR 49290.l`
- `34732`: `MOVE.W #ffff, 7c(a6); MOVE.B #ff, 9b(a6); BRA.W 34742`
- `34742`: `MOVE.L #34748, (a6)` (→`34748`)
- `34748`: `LEA.L 34750(pc), a1; BRA.W 34874` — FLOW
- `34874`: `JSR 288c.l` — FLOW
- `3487a`: `BCC.W 3489c` (→`3487e`) — C 소비, FLOW
- `3487e`: `MOVE.B 9b(a0), d0; CMP.B 9b(a6), d0; BEQ.W 3489a` (→`3488a`)
- `3488a`: `MOVE.B d0, 9b(a6); ANDI.W #ff, d0; ADD.W d0, d0; ADD.W d0, d0; MOVEA.L 348a2(pc, d0.w), a1` (→`3489a`)
- `3489a`: `JMP (a1)` — FLOW
- `3489c`: `JMP 2a00.l` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다):
  - `33132`: BYTE `9a` = 1, BYTE `9b` = 0, LONG `76` = LONG `56` = 0, `49f8c`(A1 = `34c80`, `D0.W` = `100`). `3315e`: BYTE `14` = BYTE `1b`, `JSR 46ef4`(cleanup). `3316a`: `JSR 496c2`(U11). `33170`: BYTE `15` bit 7 = 1이면 `331ac`. `3317a`: `(A6)` = `33180`, fall-through. `33180`: `JSR 33c54`. `33184`: A0 = `349ce`, `JSR 1aa7e`(U01); Set이면 `(A6)` = `33b0c`(`33192`). `33198`: BYTE `15` bit 7 = 1이면 `331ac`, 아니면 `JSR 49fc6`(`331a2`), `BRA 33958`(`331a8`).
  - `331ac`: BYTE `9b` = 0, `49f8c`(A1 = `34c80`). `331c2`: `JSR 496c2`. `331c8`: `D0` = `10`, `D1` = `30`(`MOVEQ`), `JSR 4da4a`(N23). `331d2`: `(A6)` = `331d8`, fall-through. `331d8`: `JSR 33c54`. `331dc`: `JSR 49fc6`. `331e2`: A0 = `349ce`, `JSR 1aa7e`; Set이면 `(A6)` = `33b0c`(`331f0`). `331f6`: A0 = `349e6`, `JSR 4d2d4`(N23); Clear면 `3323a`. `33204`: `7a.W` = `D0.W`, `D2` = `c`, `D3` = `18`, `JSR 4d418`(경계); Clear면 `3323a`. `33216`: `7c.W` = `D0.W`, `D0.W` = `7a.W`, `D1.B` = 4, `D2.B` = BYTE `93`, `D3.B` = BYTE `94`, `D4.W` = `54.W`, `JSR 4d508`(N23). `33234`: `(A6)` = `3323e`(N30b 값), `3323a`: `BRA 33958`.
  - `336d2`(설치): `D0.B` = BYTE `5e`; 무부호 `D0.B` ≥ `1b`이면 `33756`. `336de`: `D0.W` &= `ff`, `D0.W` = 4·`D0.W`(16 bit), PC = `336ea` + sext(`D0.W`)(결정 4). slot: k = 24 → `33846`(경계 출구), 그 밖 → `33756`. `33756`: `49f8c`(A1 = `34bec`). `33766`: BYTE `9b` = 4, BYTE `9a` = 1, `3af8`(`D0.W` = `1ac8`). `3377c`: `JSR 496c2`. `33782`: `JSR 46ef4`. `33788`: LONG `76` = `34906`, `D0` = `10`, `D1.W` = `2c`, `JSR 4db18`(경계). `3379c`: BYTE `92` = `60`, `(A6)` = `337a8`, fall-through. `337a8`: `JSR 4d8d8`(경계). `337ae`: `D0.B` 음수면 `337de`(`JSR 33c54`) → `337e2`. `337b4`: `JSR 33c2a`. `337b8`: `JSR 33c0e`. `337bc`: `D0` bit 5 = 1이면 `337c4`: `D1.B` = 4, `JSR 33940`(경계). `337cc`: `D0.W` = `7a.W`, `D2` = `c`, `D3` = `18`, `JSR 4d418`(경계; C는 쓰지 않음), `BRA 337e2`(`337da`). `337e2`: `JSR 4d8d8`. `337e8`: `D0.B` ≥ 0(`BPL`)이면 `33816`. `337ee`: BYTE `9b` = 0이면 `33816`. `337f8`: BYTE `9b` = 0, `49f8c`(A1 = `34cf6`), `JSR 34490`(`3380e`, 경계), `JSR 3453a`(`33812`, 경계). `33816`: `JSR 49fc6`. `3381c`: `8a.W` = `8000`; BYTE `92` = 0이면 `33832`, 아니면 `3382a`: BYTE `92` −= 1; 결과 ≠ 0이면 `33838`, 0이면 `33832`(결정 3). `33832`: `(A6)` = `3383c`(범위 밖 값). `33838`: `BRA 33aa4`.
  - `33958`: `BRA 33a88`. `33a88`: `JSR 4b54e`(U01). `33a8e`: `D0.B` = (BYTE `61` bit 7 = 1) ? `ff` : 0(`SNE`); bit 7 = 1이면 `(A6)` = `336d2`(`33a9a`). `33aa0`: BYTE `5e` &= `D0.B`. `33aa4`: BYTE `61` bit 6 = 0(`BCLR`); `7e.W` ≠ 0이면 `33ab2`: `7e.W` −= 1, BYTE `61` bit 6 = 1. `33abc`: `JSR 4d766`(N23); Set이면 BYTE `61` bit 6 = 1(`33ac6`). `33acc`: LONG `76` ≠ 0이면 `33ad4`: BYTE `14` = BYTE `1a`, `JSR 33f1a`(경계); `33ade`: BYTE `61` bit 6 = 1, `BRA 33b04`. `33ae8`: BYTE `14` = BYTE `1b`, `D0.W` = `7e.W` & 1; ≠ 0이면 `33afa`: BYTE `14` = BYTE `19`, BYTE `8c` = `ff`(`ST`). `33b04`: BYTE `95` = 2, RTS. `33b0c`: `JMP 2a00`.
  - `33b12`: `20.W` = `102`, LONG `22` = bank LONG `2000a4`, `8ebe`(`ce`, 1) 두 번(`33b12` `33b2e`), `8ebe`(`d`, 1)(`33b3c`). `33b4a`: `68.W` = `1e.W` = `8810`, `D1` = 4, `JSR 4d81c`(stage_area). `33b5e`: BYTE `93` = `D1.B`, BYTE `94` = `D2.B`, `54.W` = `D3.W`, BYTE `9a` = 2, BYTE `9b` = 0, BYTE `8e` = 5, `28ae`(A0 = `41fe6`, `D0.W` = `a`); Set이면 `33b90`: A1 = A6 + `8a`, 자식 LONG `76` = A1, BYTE `7a` = 1, `7b` = `7c` = `7d` = `7e` = 0, C = 1. `33bba`: `28ae`(A0 = `345c2`). `33bca`: `28ae`(A0 = `3471a`); Clear면 `JMP 2a00`(`33b0c`), 아니면 RTS(`33bde`).
  - `33be0`: `D0` = 0, BYTE `5e` = `90` = `91` = 0, `7e.W` = `1e`, LONG `76` = 0, BYTE `95` = 2, BYTE `96` = `ff`, LONG `56` = `34b66`, RTS. `33c0e`: `D0.W` = `7a.W`, `JSR 49be0`(U06). `33c18`: `D0.W` = WORD (A0); bit 6 = 1이면 BYTE `90` = `f`(`33c22`). RTS(`33c28`). `33c2a`: BYTE `15` bit 7 = 1이면 `JMP 4bfc0`(`33c34`, 경계). `33c3a`: LONG `36` = LONG `64`, LONG `3a` += `ffffb000`(32 bit), fall-through `33c48`: `JSR 4be82`(U08b), `33c4e`: `JMP 492c8`(U12). `33c54`: BYTE `15` bit 7 = 1이면 `JMP 4bfb4`(`33c5e`, 경계). `33c64`: LONG `3a` += `ffffb000`, fall-through `33c6c`: `JSR 4be6c`(경계), `33c72`: `JMP 492c8`.
  - `33f4c`: A0 = LONG (A0), `8a.W` = WORD (A0), `88.W` = WORD (A0)(같은 주소 두 번), RTS.
  - `345c2`: `20.W` = `102`, LONG `22` = bank LONG `2000a4`, `8ebe`(`D0.W` = `f`, `D1.B` = 0). `345de`: `D0` = `D1` = 0, `JSR 49290`(U08). `345e8`: BYTE `9a` = 2, `BRA 34644`. `34644`: BYTE `9a` = 2, `(A6)` = `34650`, fall-through. `34650`: A1 = `34658`, `BRA 346c6`. `34658`: RTS.
  - `345f2`(LONG 표 k=0): `49f8c`(A1 = `354f2`). `34602`: `(A6)` = `34608`, fall-through. `34608`: A1 = `34610`, `BRA 346c6`. `34610`: `JSR 3465a`. `34614`: RTS. `34616`(k=1): `49f8c`(A1 = `35650`). `34626`: `(A6)` = `3462c`, fall-through. `3462c`: A1 = `34634`, `BRA 346c6`. `34634`: `JSR 3465a`; Set이면 `(A6)` = `34644`(`3463c`). RTS(`34642`).
  - `3465a`: A0 = LONG `c`(부모), `1e.W` = `1e.W(A0)`, `D0.B` = BYTE `88(A0)`, `D1.B` = BYTE `89(A0)`, `D0.W` = sext(`D0.B`), `D1.W` = sext(`D1.B`)(`EXT.W`), `2e.W` = `D0.W`, `32.W` = `D1.W`, `JSR 43e34`(cleanup). `3467e`: A0 = LONG `c`, BYTE `8f` = BYTE `84(A0)`, `D0.B` = BYTE `85(A0)`, `D0.W` &= `ff`, `D0.B` = BYTE(`346c0` + `D0.W`)(고정 ROM 자료), `D0.W` = sext(`D0.B`), push WORD `D0.W`(A7 −= 2), `46.W` += `D0.W`(16 bit), `JSR 49fc6`. `346a2`: `JSR 43e34`. `346a8`: `D0.W` = pop WORD(A7 += 2), `D0.W` = −`D0.W`(`NEG.W`, 16 bit), `46.W` += `D0.W`, `42.W` += 6, `1e.W` −= 1, `JSR 49fc6`. `346be`: RTS(C = `49fc6`의 C, FLOW).
  - `346c6`/`346cc`/`346d0`/`346ea`/`346fa`: 결정 5. `34714`: `JMP 2a00`.
  - `3471a`: `20.W` = `102`, LONG `22` = bank LONG `2000a4`, `D0` = `D1` = 0, `JSR 49290`. `34732`: `7c.W` = `ffff`, BYTE `9b` = `ff`, `BRA 34742`. `34742`: `(A6)` = `34748`, fall-through. `34748`: A1 = `34750`, `BRA 34874`. `34874`/`3487a`/`3487e`/`3488a`/`3489a`: 결정 5. `3489c`: `JMP 2a00`.

## carry

- [F] **소비 10 block**(모두 FLOW). Unknown C로 들어오면 `objects n30 caller requires known carry`(상태 보존)다. 모두 `BCC`다: Clear면 분기 대상, Set이면 fall-through.
  - `3318e BCC.W 33198`, `331ec BCC.W 331f6`: U01 `1aa7e`(`1aaf6 ANDI` Clear, `1aafc ORI` Set).
  - `33200 BCC.W 3323a`: N23 `4d2d4`(N23 생산 `4d3a6` `4d40c` ORI / `4d412` ANDI, `4d2e0` `4d2f0` SCS 뒤 등; N28 `2ba10` `30784`와 같은 소비).
  - `33212 BCC.W 3323a`: 경계 `4d418`(결정 6).
  - `33ac2 BCC.W 33acc`: N23 `4d766`(`4d77a ADD.B D1,D1` 계산 C; N28 `30fbe`와 같은 소비).
  - `33b8c BCC.W 33bba`, `33bda BCC.W 33b0c`: fade_card `28ae`(`2908 ORI` Set, `290e ANDI` Clear).
  - `34638 BCC.W 34642`: `3465a`의 C = `346b8 JSR 49fc6`의 C(`346be RTS` FLOW로 통과).
  - `346cc BCC.W 34714`, `3487a BCC.W 3489c`: stage_event_ops `288c`(`2898` `28a8 ORI` Set, `289e CMPI.L #270e,(A0)` 같음 = Clear).
- [F] **known 생산 1 block**: Set(`ORI`) `33b90`. [I] 바로 뒤 `33bba MOVE.W #a,D0`이 C를 지우므로 소비자는 없다(N29 `31960`과 같은 관례로 생산으로 둔다).
- [F] **FLOW_ONLY 97 block**(C 보존): JSR/JMP/BRA/RTS block, `LEA`+`JSR`(`33184` `331e2` `331f6`), `LEA`+`BRA`(`34608` `3462c` `34650` `34748`), `BTST`(+Bcc) block(`33170` `33198` `337bc` `33c2a` `33c54`), `BTST`+`SNE`+`BEQ`(`33a8e`), `BSET`(`33ac6`, `33ade`+`BRA`), BRA.W slot 27개, `JMP (A1)`(`346fa` `3489a`), 소비 10개. 목록: `3316a` `33170` `33180` `33184` `3318e` `33198` `331a2` `331a8` `331c2` `331d8` `331dc` `331e2` `331ec` `331f6` `33200` `33212` `3323a` `336ea` `336ee` `336f2` `336f6` `336fa` `336fe` `33702` `33706` `3370a` `3370e` `33712` `33716` `3371a` `3371e` `33722` `33726` `3372a` `3372e` `33732` `33736` `3373a` `3373e` `33742` `33746` `3374a` `3374e` `33752` `3377c` `33782` `337a8` `337b4` `337b8` `337bc` `337da` `337de` `337e2` `3380e` `33812` `33816` `33838` `33958` `33a88` `33a8e` `33abc` `33ac2` `33ac6` `33ade` `33b0c` `33b8c` `33bda` `33bde` `33c28` `33c2a` `33c34` `33c48` `33c4e` `33c54` `33c5e` `33c6c` `33c72` `34608` `34610` `34614` `3462c` `34634` `34638` `34642` `34650` `34658` `346a2` `346be` `346c6` `346cc` `346fa` `34714` `34748` `34874` `3487a` `3489a` `3489c`.
- [F] **carry 보존 목록 97 PC** = FLOW_ONLY 97. 생산 1 block은 보존 목록에 넣지 않고 block 안에서 C를 정한다.
- [F] **Unknown 68 block**: 나머지(`MOVE`/`MOVEQ`/`TST`/`CMPI`/`CMP`/`ADD`/`ADDI`/`ADDQ`/`SUBQ`/`AND`/`ANDI`/`EXT`/`NEG` 포함 block, 설치 block).
- [F] RTS로 돌려주는 C가 쓰이는 N30a 함수는 `3465a`(소비 `34638`, FLOW 통과)뿐이다. `33b04`(scheduler 복귀)·`33bde`(N29 `33124`·범위 밖 `330b0`은 C를 쓰지 않음)·`33be0`·`33c28`(`337bc BTST`가 덮음)·`33f4c`·`34614` `34642` `34658`(callback 끝)의 C는 쓰이지 않는다.

## 구현 범위와 규약

- routing 9 범위(위 표). 짝수 PC 778개 중 block 시작 166, 내부 612. 내부 PC 직접 진입은 `unsupported animation objects n30 PC`다(`3382e` 포함, 결정 3). 범위 이웃(N30b, 범위 밖 함수 `3383c` `33940` `33c78..`, 자료 `346c0..346c6` `346fc..34714` `348a2..`, N29·N31 범위)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)이거나 그 단위 실행부다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`는 LONG 전체). 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow에 기대지 않는다(`EXT.W`·`NEG.W`·`ADDI.L #ffffb000`·`ADDQ.W`·`SUBQ.W`/`SUBQ.B`). 결과 flag는 같은 block 안의 Bcc만 쓴다(`3382e`는 결정 3). 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다). `BTST.B #n,Dn`은 `Dn` bit n(32 bit 중 n < 8)을 본다.
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 97 PC를 넣는다.
- 제어 이동: `336de`(결정 4)와 `346fa` `3489a`(PC = A1, live target; 결정 5)를 빼면 모두 정적이다. `33b0c` `34714` `3489c JMP 2a00`, `33c34 JMP 4bfc0`, `33c5e JMP 4bfb4`, `33c4e` `33c72 JMP 492c8`는 복귀 LONG을 push하지 않는다. 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`3317a`→`33180`, `331d2`→`331d8`, `3379c`→`337a8`, `34602`→`34608`, `34626`→`3462c`, `34644`→`34650`, `34742`→`34748`). `33192`→`33198`, `331f0`→`331f6`, `33234`→`3323a`, `33832`→`33838`, `33a9a`→`33aa0`→`33aa4`, `33ab2`→`33abc`, `33ac6`→`33acc`, `33afa`→`33b04`, `33b90`→`33bba`, `33c22`→`33c28`, `33c3a`→`33c48`, `33c64`→`33c6c`, `3463c`→`34642`, `346ea`→`346fa`, `3488a`→`3489a`도 이어진다.
- 스택: JSR 복귀 LONG, `3467e`/`346a8`의 WORD push/pop(A7 ±2, `push_program_stack`/`pop_program_stack` 크기 2). work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `2000a4`(`33b12` `345c2` `3471a`, id `102` → LONG `22`).
- [F] 고정 ROM 자료(live bus 읽기, 원본처럼 색인 검사 없음):
  - BYTE 표 `346c0`(`02 01 00 ff fe 00`; `3467e`, 색인 BYTE `85(부모)` 0..`ff`).
  - BYTE 표 `346fc`(12 BYTE `00 01 01 00 01 00 01 00 01 00 00 00`; `346d0`, 색인 (4·BYTE `9a(A6)` + BYTE `9a(부모)`) & `ff`).
  - LONG 표 `34708`(`345f2` `34616` `34644`; `346ea`, 색인 4·BYTE `9a(부모)`).
  - LONG 표 `348a2`(`34742` `34752` `34792` …; `3488a`, 색인 4·BYTE `9b(부모)`).
  - `33f4c`가 따라가는 A0 기록(interpreter 인자; live bus).
  - 주소만 넘기는 자료: 사각형 `349ce`(`1aa7e`), `349e6`(`4d2d4`), 애니메이션 목록 `34c80` `34bec` `34cf6` `354f2` `35650`(`49f8c`), LONG `76` 값 `34906`(`33788`), LONG `56` 값 `34b66`(`33be0`), `8ebe` 인자 WORD `ce` `d` `f`, `3af8` 인자 `1ac8`.
- [F] work RAM:
  - 노드 A6: BYTE `14` `15` `19` `1a` `1b` `5e` `61` `8c`(`ST`) `8e` `8f` `90` `91` `92` `93` `94` `95` `96` `9a` `9b`; WORD `1e` `20` `2e` `32` `42` `46` `54` `68` `7a` `7c` `7e` `88` `8a`; LONG `(A6)`(설치) `c`(부모) `22` `36` `3a` `56` `64` `76`.
  - 부모 `c(A6)`: WORD `1e`, BYTE `84` `85` `88` `89`(`3465a`), BYTE `9a`(`346d0`), BYTE `9b`(`3487e`); `288c`는 부모 LONG `0`(callback)을 본다. `49be0` 반환 A0: WORD `0`. `28ae` 자식 A0(`33b90`): LONG `76`, BYTE `7a`..`7e`. `33f4c` 인자 A0: LONG (A0) → WORD.
- [F] 상수 인자: `28ae` `D0.W` = `a`(A0 = `41fe6` `345c2` `3471a`); `49f8c` `D0.W` = `100`; `49290` `D0`/`D1` = 0/0; `4d81c` `D1` = 4; `4d418` `D2`/`D3` = `c`/`18`; `4d508` `D1.B` = 4; `4da4a` `D0`/`D1` = `10`/`30`; `4db18` `D0` = `10`, `D1.W` = `2c`; `8ebe` `D1.B` = 1(`33b12` `33b2e` `33b3c`) / 0(`345c2`).

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_objects_n30.cpp` `aeed39270b8f25b4`, `engine/tests/animation_machine_objects_n30_test.cpp` `7d886092ba44552b`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나(9 범위), carry 보존 case group 하나(97 PC); `fadcc623acdf386d`), `engine/src/animation_machine_internal.h`(선언 하나; `f588967d9100772c`), `Makefile`(source 목록·test target·실행 줄; `5e5cf9b0d2e7c727`), `tools/verify_animation_machine.py` SOURCES(`f100467e1df0aa23`). `animation_machine_interpreter.cpp`와 다른 단위 실행부는 바꾸지 않았다. 다른 단위의 두 번째 진입 patch는 필요 없다.
- [F] 실행부 case 집합 = scratch `startsA.txt`(166). 내부 PC 612개(`3382e` 포함)는 모두 `unsupported animation objects n30 PC`, 소비 10 block은 Unknown C에서 `objects n30 caller requires known carry`(상태 보존)다.
- [F] `make -j4 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`). N30 test 출력: `animation machine objects n30: 411 fixtures (35 checked errors, 46 kept C), 166 blocks, 2056 calls`. N28(152 block)·N29(192 block) test는 그대로 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N30 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen30.py` Unicorn 생성(표 SHA256 앞 16자리 `67d7c4738383c656`), `gen/assemble30.py` 조립): 411 fixture(성공 376, checked 오류 35), 166 시작 모두 Unicorn fixture로 덮음, block 표(166 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 10은 Unknown에서 거부), zero-step 166 × 3, 내부 PC 612 전수, 홀수 PC(범위 양끝 18), RAM rollback 탐침 `10fe60` `10fe70` `10fe80`·RTS 복귀 `10fe90`(10 fixture), 범위 안팎 자료 `346c0` `346c4` `346fc` `34708` `34710` `348a2`(routing 밖), 경계·다른 단위 진입 stop 33개(stop만; N31 `34750` 포함). 표 `336e6`: `336d2`에서 BYTE `5e` = 0..`1b`·`80`·`ff`, `336de` 직접 진입 `D0` = 0 1 24 26 27 `12341818` `ff00`와 checked 오류 2개(28 → `3375a`, `1234ff1d` → `3375e` 내부). live target: `346fa`/`3489a` A1 = `34658` `34610` `34750` `2a00` STOP, checked 오류(홀수 `34611` → `unaligned animation machine PC`, `34612` → N30 내부 PC, 표 `348a2` k=3 홀수 LONG → unaligned, k=5 RAM `10fe60` → `unsupported animation machine PC`). "real" 행은 `1aa7e`(사각형 `349ce`, 화면 안/밖 → `3318e` `331ec`), N23 `4d2d4`(N22 `1bf02`, 사각형 `349e6` → `33200`), N23 `4d766`(N22 `1bfb4` → `33ac2`), `28ae`(자리 있음/없음/하나만 → `33b8c` `33bda`), `288c`(부모 `270e` / 살아 있음 → `346cc` `3487a`)를 native로 따라가 실제 소비자 분기와 비교했다. 합성 물리 바이트(ROM 자료 아님): `1bef8..1bf02`, `346c0..346c6`, `346fc..34714`, `348a2..348ba`, `349ce..349d6`, `349e6..349ee`, bank LONG `2000a4`.
- [F] RTS 통과 native 확인(Unicorn SR을 C 판정에 쓰지 않음): `346be`(선언 C Clear/Set, 복귀 LONG = 실제 소비자 `34638`) → `34638 BCC` native 분기 `34642`(Clear)/`3463c`(Set). 계약과 같다.
- [F] 돌연변이 검사(scratch `mut/mut30.py`, 실행부 한 곳씩 29개): 28/29를 test가 잡았다(`mut/mut.log`). 살아남은 `m3`(`336d2` `>= 1b` → `> 1b`)는 `5e` = `1b`일 때 slot k = 27이 `33756`(BCC 대상과 같은 block)이고 `336de`가 바꾸는 `D0.W`를 `33756 MOVE.W #100,D0`이 덮으므로 관찰 결과가 같은 동치 돌연변이다. 경계를 k = 24로 옮긴 `m3b`(`>= 18`)는 잡혔다.
- [F] 실제 ROM 차분(scratch `realrom/real30.py` SHA256 앞 16자리 `8af5a3daddf7abd5`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM, 실제 ROM 표 `346c0` `346fc` `34708` `348a2`·사각형 `349ce` `349e6`·bank LONG `2000a4`; native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC(N30a 경계, N30b `3323e` `3395c`, `3383c`, N31 `34750`; N28b 하네스처럼 나중 단위가 routing해도 선언 stop으로 유지)·interpreter `49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 165/166/165(합집합 166). 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `3318e` 24 `331ec` 26 `33200` 92 `33ac2` 192 `33b8c` 93 `33bda` 121 `34638` 23 `346cc` 242 `3487a` 109. interpreter 따라가기(`FOLLOW_ANIM`) 1,000 case 불일치 0. 의도한 차이: `336de` 직접 진입에서 `D0.B` ≥ `1b`로 block 시작이 아닌 명령(`337fe`)에 닿은 1건(seed 1; 결정 4, F1 결정 3 checked 오류). native 홀수 주소·Unknown C 진입 소비 거부·`2986` 0건. clean stop이 없는 native case는 건너뜀(seed별 174/165/163; 주로 `331f6` `33b12` `33958` `33a88` 경로의 다른 단위 반복).
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `3535981` 일치 pass 14,408·node 122,462, 불일치 0 → N30a 뒤 같음(`diff_results.json` SHA256 앞 16자리 `a6c41695e17a74bd`, 기준과 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` `89cef5d6…`) → N30a 뒤 같은 수치·불일치 0(`93e5b3fd…`; 차이는 기록된 `animation_machine.cpp` SHA(seed 32 33 116 117의 `current_router_sha256` 포함)와 새 원본 목록뿐). **새 완주 seed 없음**(재범위 예상과 같음), 잃은 seed 0. seed 116 117은 그대로 frame 0 `38ba0`(N31)에서 멈춘다.
- [F] 탐침 이동: 없음(결정 9). 이 test의 새 RAM 탐침은 `10fe60` `10fe70` `10fe80` `10fe90`이다.
- [U] 남은 미확인: N30a 범위의 자연 frame pass 비교는 116 117이 `38ba0`에서 먼저 멈춰 아직 없다(실제 ROM 차분·fixture로만 덮음). 경계 `4d418`의 C 생산(소비 `33212`)은 그 단위가 정한다. 결정 1의 N30b(`3323e..336d2` `3395c..33a88`)와 결정 7의 `3383c..33958`은 routing하지 않았다. 재범위 "기타 9(+87)"의 정확한 대응은 확인하지 않았다.
