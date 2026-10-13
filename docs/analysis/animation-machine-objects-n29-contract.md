# 객체 callback F4 N29(N29a): stage event `318d8` 계열 객체 — `28ae` 자식 callback `30dbe`·`31008`, 설치 사슬 `306b4` `308e2` `309b4` `309f2`, 공유 꼬리 `30ed6`(N28 결정 1), helper `3164a` `3165e` `3166c` `316ac` `316b2` `319f6` `31a12`, interpreter 표 진입 `31a2a`/`31a44`, stage event callback `3310c` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N29 행(187 block, `306b4..30718` `308e2..30cb8` `30dbe..310de` `3164a..316c2` `318d8..31a54` `3310c..3312c`, callback `30dbe` `30de4` `31008` `31032` `3310c`, 경계 callee 21, 표 `30a76`:9, bank 2, 미실행 설치 11(+8), 새 seed 없음, 옛 U41 187; seed 116 117 사슬의 일부)과 N28 계약(`animation-machine-objects-n28-contract.md`, SHA256 `15494b530a0861644fe9ea2bd46c671a900b21c2cf7e4a3af42fec9a47eb9f99`) 결정 1이 넘긴 공유 꼬리 `30ed6..30f84`(18 block)이다. N28 소유 `30ed2..30ed6` `30f84..31002`는 다시 routing하지 않는다. 단위 형식과 규약은 N28 계약을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 분기를 각 선행에 접어 넣음). N29에는 block 경계를 건너는 N/Z/V 읽기가 없다(결정 5).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다. 범위 밖 코드만 부르는 범위 안 helper는 routing하지 않는다(`3169c` `319b6`, 결정 2).
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- `animation_machine_interpreter.cpp`와 다른 단위 실행부는 고치지 않는다. 기존 실행부의 두 번째 진입이 필요한 곳은 scratch patch와 결정으로 보고한다(N28 `30fa0`, 결정 3). DIV 0 제수는 단위 checked 오류(N29에는 DIV가 없다).
- 계산 점프 표는 정적으로 묶고 전부 전사한다(`30a76`, 9 slot, 결정 4). LONG 포인터 표 + `JMP (An)`은 live bus 읽기 + live target(N29 본문에는 레지스터 간접 제어 이동이 없다; interpreter의 `JSR (A1)`이 표 `4a500`의 `31a2a`/`31a44`로 들어온다).
- ~220 block을 넘으면 나누고 seed 116 117이 쓰는 부분을 먼저 구현한다(정적 closure 246 block → N29a 192 + N29b 54, 결정 1).
- N24(`5deec..5e8c8`)가 동시에 진행된다. N29 routing 범위는 N24와 겹치지 않는다.

- 결정 6(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치, `28ae` 자식 값, 범위 밖에서 참조하는 범위 안 진입, interpreter LONG 표 `4a500` 대상, PC 상대 BRA.W 표 slot)로 정한다. Unicorn TB 분할은 시작이 아니다.
- 결정 7(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N28 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDQ`/`SUB`/`SUBQ`/`ANDI`/`ASR`/`LSL`/`SWAP`/`CLR` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`ST`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `ORI` CCR은 known Set 생산이다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N29 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`200094` `2000ac`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n29`(HEAD `d798961` = N28까지 통합, `engine/src/animation_machine.cpp` SHA256 `f8e19026967f94f32ac3910c5028df7f5aedf7ac36723305c93ec798ad0fa7b0`, routing 규칙 81개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`, `engine/src/animation_machine_objects_n28.cpp` SHA256 `6b78e30430021e4bea1a467f7e2925f23a0e8512150564dde0a925073d73504e`)을 참조했다. N29a routing 10 범위의 짝수 PC는 기존 routing에 없다. 범위 양끝 이웃 중 `306b2` `30718` `30ed2` `30ed4` `30f84` `31000`은 N28 routing이고, `308e0` `30b6c` `30dbc` `310de` `31648` `3169c` `316aa` `316c2` `318d6` `319b6` `319f4` `31a54` `3310a` `3312c`는 routing 밖이다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n29/n29.py`(정적 디코드, `starts.txt` SHA256 `d4cbcff06a94f5bf4e37857f74f93454b484b800883cb2ee75d69fe0c0457b40`)와 `cls29.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N29a = 192 block**(10 routing 범위, 코드 1,872바이트, 짝수 PC 936, 내부 744). 진입 18개(`306b4` `308e2` `30dbe` `30ed6` `31002` `31008` `3164a` `3165e` `3166c` `31696` `316ac` `316b2` `318d8` `319f6` `31a12` `31a2a` `31a44` `3310c`)에서 분기·fall-through·범위 안 설치·`28ae` 자식·BRA.W 표 `30a76`을 끝까지 따라간 정적 closure다. 같은 규칙의 N29 전체 closure는 246 block이고, 설치 `30b6c` 계열 54 block(27 slot 표 `30b80` 포함)을 N29b로 미룬다(결정 1).
- [F] 진입:
  - stage event callback `3310c`(고정 ROM LONG 표 `e8cc0..e8cdc`의 `e8cd0`; 같은 표의 `2b8a6` `2b8a0` `306a8`은 N28, `2b7be` `2b7b8` `304ea` `3fefc`는 범위 밖). 범위 밖 `3312c ST.B 99(A6); BRA.B 3310c`도 들어온다(`3312c`는 routing 밖).
  - `28ae` 자식 값: `30dbe`(`319a4 MOVEA.L #30dbe,A0; JSR 28ae`), `31008`(`3198a`). 둘 다 seed 116 117이 자연 400 frame에서 실행한다.
  - 범위 안 설치: `306ec`(`306e6`, fall-through), `30718`(`3070e`, N28 값), `31002`(`30700`), `308fe`(`308f8`), `3095e`(`30958`), `309d0`(`309ca`), `308e2`(`309e8`), `30a30`(`30a2a`), `309b4`(`30f66`), `30de4`(`30dde`), `30e38`(`30e32`), `30e8a`(`30e6a`), `30eae`(`30ea8`), `30dd4`(`30ec4`), `31032`(`3102c`). `33132`(`33124`)는 N30 범위 값이다.
  - 범위 밖에서 들어오는 범위 안 진입: `308e2`(범위 밖 `306a0 MOVE.L #308e2,(A6)`·`3086e BMI.W`), `30ed6`(범위 밖 `305ae` `30610` `30834` `30866` `308de BRA.W`/`BPL.W`), `31002`(N28 `3076e` 설치·범위 밖 `30510` `30660 BCC.W`), `3164a`(범위 밖 `315e4` `31a90 JSR`), `3165e`(N28 `30774`·범위 밖 `30588` `305cc` `30642` `30830` `30858` `308da`), `31696`(범위 밖 `30584` `3063e` `3082c` `30854` `308d6`), `316b2`(N28 `3075a`), `318d8`(N28 `306a8`·범위 밖 `304ee` `30502` `30652`), `319f6`(N28 `3078c`·범위 밖 `3050c` `3065c`·N29b `30c78`), `31a12`(N29b `30c74` `30cc8`), `31a2a`/`31a44`(interpreter LONG 표 `4a500`의 `4a5a4`/`4a5a8`; `4a352`/`4a43c JSR (A1)` live target).
  - 범위 안에서만 들어오는 진입: `306b4`(`30918` `30978 BNE.W`), `3166c`(`308fe` `3095e` `309d0`, N29b `30c64`), `316ac`(`30a50`, N29b `30c8e`).
- [F] **경계(실행부 없음, 현재 routing 밖) callee 18개**: `316c2`(`30992`), `316f0`(`30926`), `31768`(`30ed6`), `317b8`(`3092a` `30986` `309d4`), `31832`(`3092e` `3098a` `309d8` `30a4c`), `3185a`(`3093a` `309ac`), `33b12`(`33120`), `49c38`(`31670`; C 반환, `31676 SCS` 소비), `4be6c`(`316ac` `316bc JMP`), `4c0ea`(`33116`), `4d418`(`319fe`; C 반환, `31a04` 소비), `4d4b4`(`31a24 JMP`), `4d734`(`30f70`), `4d8d8`(`31a14`), `4d9ba`(`30f7e`), `4ff96`(`30ad0`), `d3d7c`(`30ad6` `30af2` `30b0e` `30b2a`), `ea680`(`30df4` `30e4c`; C·A0·D1 반환, `30dfa`/`30e52` 소비). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다. 재범위의 "경계 21"은 N29b 쪽 `4d8d8` `4db18` 호출과 `30cc4` 등을 포함한 값이다([I]).
- [F] **다른 실행부로 가는 callee·출구**: `28ae` `2a00` `2a24`(fade_card), `2986`(buffer_cue), `288c`(stage_event_ops), `3af8`(sound), `8ebe` `443d2`(U02), `8ff4` `43e22` `43e34`(cleanup), `16ed2`(sprite), `1aa3a` `49290`(U08), `1aa7e`(U01), `1abda` `492c8`(U12), `491c4`(U17), `496c2`(U11), `49be0`(U06), `49f8c` `49fc6`(interpreter), `4ae4a`(N08), `49214`(N05), `4be82`(U08b; `31696 JMP`), `4d7a6`(input), `4d81c`(stage_area), N28 `30ed2`(`30714 BRA`)·`30f84`(`30efe BRA`, `30f7e JSR 4d9ba`의 복귀점)·`30fa0`(`30abc BRA`, 결정 3).
- [F] **범위 밖 설치·자식 값(실행 PC가 아님)**: 설치 `30718`(N28), `33132`(N30); `2986` 자식 `30d6c`(`30b46`); `28ae` 자식 `41fe6`(`3194c`, N22); 자료 포인터 LONG `76` = `31c92`(`30a18`).
- [F] **carry**(아래 "carry" 절): 소비 15 block(FLOW 14, 끝 Unknown 1 = `31676 SCS`), known 생산 4개(`ANDI.W` Clear 1, `ORI` Set 3), FLOW_ONLY 101개(소비 14 포함), Unknown 87개(`31676` 포함). 101 + 4 + 87 = 192.
- [F] X·DIVx/MULx·레지스터 간접 제어 이동·TRAP·I/O port 쓰기·bank 변경이 없다. N/Z 재계산이 없다(결정 5). PC 상대 BRA.W 표 1개(`30a76`, 9 slot).
- [F] 스택: JSR 복귀 LONG, `3098e MOVE.L 3a(A6),-(A7)` / `309a4 MOVE.L (A7)+,3a(A6)`(LONG), `31a12 MOVE.B D1,-(A7)` / `31a1a MOVE.B (A7)+,D1`(BYTE, ±2).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen29.py`): RNG·base 두 기록 모두 seed 116 117만 N29a 범위 PC 43개를 실행한다: `30dbe..30e12`(12) `31008..3104a`(7) `3164a..3166a`(6) `316b2` `318d8..319b4`(11) `31a44` `3310c..33124`(4)와 `33132`(N30). callback 실행 수(seed 116 기준, 117 같음): `30dbe` 1, `30de4` 81, `31008` 1, `31032` 81, `3310c` 1; 그 밖 `318d8`(N28 `306a8`) 1, `316b2`(N28 `3075a`) 80, `3164a`, `3165e`(N28 `30774`), `31a44`(interpreter 표). `306b4..30718` `308e2..30b6c` `30ed6..30f84` `30dd4` `30e14..30ecc` `3104c..310d8` `3166c..31694` `31696` `316ac` `319f6..31a2a` `31a12`는 자연 400 frame에서 실행되지 않는다.
- [F] 기준(`d798961`)에서 seed 116 117은 frame 0 `38ba0`(N31)에서 먼저 멈춘다. [I] N29a만으로는 새 완주 seed가 없다(재범위 N29 행과 같음). 116 117의 N29 자연 경로는 다시 `ea680`(N35 범위, `30df4`)·`4c0ea`(N33, `33116`)·`4be6c`(N33, `316b2`)·`33b12`(N30)에서 멈춘다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **분할: N29a 192 block 구현, N29b 54 block 미룸.** [F] 재범위 N29 범위 + `30ed6..30f84`의 정적 closure(진입 19, BRA.W 표 2개 전부)는 246 block이라 ~220을 넘는다.
   - seed 116 117이 자연 400 frame에 쓰는 부분은 `30dbe..30ed2`(35) `31002..310de`(17) `3164a..316c2`(15) `318d8..31a54`(22) `3310c..3312c`(4) = 93 block 안에 모두 있다(`seen29.py`).
   - **권고(구현함): N29a = 246 − `30b6c..30cb8`(54) = 192 block.** 설치 `30b6c`(N28 `30f96`의 값만; 범위 안 참조 없음)부터 시작하는 함수(`5e` 27 slot 표 `30b80`, `4d8d8` `4db18` `31a12` `319f6` 호출, 설치 `30c4c` `30cb8`)는 자연 400 frame에서 실행되지 않고 N29a 안의 어떤 block도 그 안으로 분기하지 않는다. N29a는 자연 경로 93 block, N28이 넘긴 공유 꼬리 18 block, 그 꼬리가 설치하는 `309b4`, 그리고 꼬리로 돌아오는 `306b4`/`308e2`/`309f2` 사슬(표 `30a76` 포함)을 함께 담는다.
   - **N29b(다음 단위, 54 + α block)** = `30b6c..30cb8`과 범위 밖 이웃 `30cb8..30d6c`(설치 `30cb8`(`30cae`)·27 slot 중 `30be4 BRA.W 30cc4`의 대상; 재범위 N29 범위 밖이라 이번 closure에도 없음, [I] 약 10 block)이다. `30d6c..30dbe`는 `2986` 자식 값(`30b46` `30d46`)이라 N28 `2cb30`처럼 실행 PC가 아니다.
   - 대안: 93 block 자연 경로만 N29a로 하고 나머지 153을 N29b로(꼬리·`30a76` 표가 함께 미뤄짐).
2. **범위 안 미참조·범위 밖 전용 helper는 routing하지 않음.** [F] `3169c..316ac`(`MOVEQ #0,D0; MOVE.L D0,36(A6); MOVE.L D0,3a(A6); JMP 4be82`, 참조는 범위 밖 `305c8 JSR`뿐)와 `319b6..319f6`(`5e` `97` `98` `88` `76` `56`(`31c66`) `90` `14` 초기화 + `JSR 4d98a`, 참조는 범위 밖 `3054c` `3069c`·N28 설치 값 `307da`의 `307da JSR`뿐)는 routing하지 않는다. 범위 밖 `307da..308e2`(N28 `307ae`가 설치하는 `307da`와 그 사슬 `30824` `30854` `3086a` `3089e`, 재범위 어느 단위에도 없음)도 routing하지 않는다. 자연 400 frame에서 셋 다 실행되지 않는다.
3. **N28 실행부의 두 번째 진입 `30fa0`(기존 실행부 수정 필요, 적용하지 않음).** [F] N29a `30abc BRA.W 30fa0`(그리고 N29b `30cb4 BRA.W 30fa0`)는 N28 block `30f9c`(`AND.B D0,5e(A6); BCLR.B #6,61(A6); TST.W 88(A6); BEQ.W 30fb8`)의 두 번째 명령으로 들어간다. N28 routing은 `30fa0`을 받지만 N28 실행부에는 그 case가 없어 `unsupported animation objects n28 PC`(rollback)다.
   - scratch patch `ms5-scratch/n29/patch/n28-30fa0.diff`: `case 0x30f9c`를 `AND.B` 뒤 `r.pc=0x30fa0`로 나누고 `case 0x30fa0:`(BCLR/TST/BEQ)를 더한다(실행 의미 불변; `30fa0`은 `TST.W`로 C를 바꾸므로 carry 보존 목록에 넣지 않음). N28 test는 block 수 151 → 152, 내부 PC 722 → 721, `starts.txt`에 `30fa0` 추가, block 표 한 줄이 필요하다.
   - **권고: 메인이 N28 쪽에 그 patch를 넣는다**(N29a 범위의 `30abc` 경로는 자연 400 frame에서 실행되지 않는다). 이 계약의 N29a 실행부는 `30abc`에서 `PC = 30fa0`만 두고 N28로 넘긴다. N29 test는 `30fa0`을 stop으로만 쓴다(F4 경계 관례).
4. **표 `30a76`: 9 slot, 계산 PC.** [F] `30a64 JSR 4ae4a`(N08) 뒤 `30a6a CMPI.W #9,D0; BCC.W 30a9e`가 무부호 `D0.W < 9`만 `30a72`로 보낸다. `30a72 ADD.W D0,D0; ADD.W D0,D0; JMP 30a7a(PC,D0.W)`이므로 자연 index는 0..8, slot은 `30a7a`+4·k(k = 0..8, `30a7a..30a9a`, 각 `BRA.W` 4바이트)다. 9 slot을 모두 block 시작(FLOW)으로 옮긴다: k = 1 2 3 → `30ac0`, k = 0 4 5 6 7 8 → `30a9e`. F1 메인 결정 3(N18 `86298` 선례)대로 `30a72`는 상한 검사 없이 PC = `30a7a` + sext((4·`D0.W`) & `ffff`)로 옮긴다. `30a72`로 바로 들어온 typed 입력에서 `D0.W ≥ 9`이면 대상은 4의 배수 주소다: `30a9e`(k = 9)는 block 시작, 그 밖 N29a 범위 안 주소는 내부 PC(`unsupported animation objects n29 PC`), routing 밖은 `unsupported animation machine PC`(전체 rollback)다. [I] 원본은 `30a6a`를 거치지 않으면 범위 밖 대상으로 뛴다.
5. **flag 재계산 없음.** [F] 진입에서 flag를 읽는 block은 소비 15개뿐이고 모두 callee가 RTS로 돌려준 C(`1aa7e` `3165e`(=`49fc6`) `3164a` `288c` `ea680` `49fc6` `319f6` `28ae` `4d418` `49c38`)를 읽는다. 나머지 비교·`TST`·`BTST`·산술과 그 Bcc는 같은 block 안에 있다(`30902`/`30962`/`30914`/`30974 BTST D0`, `3091c`/`3097c ANDI.W #f`, `30a6a CMPI.W #9; BCC`, `30a9e CMPI.W #110; BGT`(부호 있음), `30dfe`/`30e56 CMPI.L #300000; BLE`(부호 있음), `30eda`/`30ee8 MOVE.B; BEQ`, `30f12 CMPI.B #9; BNE`, `30f22 TST.B; BEQ`, `31042 TST.B; BPL`, `3104c CMP.W; BEQ`, `31092 CMP.B; BEQ`, `31650 ANDI.W #8; BEQ`, `31684 BTST #6`, `31a1a TST.B; BPL`, `3310c CMPI.W #0; BNE`).
6. **경계 callee C·반환값 소비 4곳.** [F] `30dfa BCC.W`·`30e52 BCC.W`는 `ea680`의 C(그리고 A0·D1), `31a04 BCC.W`는 `4d418`의 C, `31676 SCS.B a0(A6)`는 `49c38`의 C를 읽는다. 세 callee는 실행부가 없으므로 N29 안에서는 typed fixture(진입 C 선언)로만 실행하고, Unknown C면 `objects n29 caller requires known carry`다. [U] 세 callee의 C 생산은 해당 단위가 정한다(`ea680` N35, `4d418`·`49c38` 미배정).
7. **`2986` caller-X 제한 유지.** [F] `30b30`이 `JSR 2986`(buffer_cue, A0 = `30d6c`, `D0.W` = `1e`, A1 = `100bf4`)을 부른다. 실패 경로는 buffer_cue 결정 1 선택 A대로 `cue wrapper failure requires known caller X` checked 오류다. N29는 고치지 않는다(자연 400 frame에서 실행되지 않음).
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n29.cpp`의 `animation_objects_n29_block`. 오류는 `unsupported animation objects n29 PC`(내부 PC), `objects n29 caller requires known carry`(소비 15 block). 메인 지시와 같다.
9. **무효화 탐침 없음.** [F] `engine/tests`·`engine/src`·`tools/*.py`의 16진 토큰 중 N29a routing 범위 짝수 PC와 같은 것은 N28 test·실행부의 경계 stop(`3165e` `316b2` `318d8` `319f6`; stop만), N28 test의 RANGES 끝값(`306b4` `30ed6` `31002`), N04 test·U20 test의 레지스터 값(`30978` `309f4`)뿐이다. routing 탐침이나 rollback 기대로 쓰는 곳은 없다. N28 test의 stop 행(`306a8`→`318d8`, `3075a`→`316b2`, `30774`→`3165e`, `30788`→`319f6`)은 N29a 뒤에도 그 PC에서 멈춘다(stop은 routing 전에 판정).

## 원본 바이트 근거

[F] N29a 코드 10 범위 합계 1,872바이트(짝수 PC 936개, 시작 192, 내부 744). 범위 순서로 이어 붙인 SHA256 `71ee6c89146bb6c34bab38d978e74334b858d2ef0f18a75a3d6d5325eb275097`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `306b4..30718` | 100 | `881c4e29f171f72b31abd5de8e7f2c2979dd135b8380d4fd042487aa454b9624` | 11 |
| `308e2..30b6c` | 650 | `688a24c6b7d52b6ac7043e2afb54b97b46a560cf23e5b0ef170278bc65153a19` | 70 |
| `30dbe..30ed2` | 276 | `9b11a5801a225ac297df634d6ece04a19e47e3b14f28868a6177e44d969ffa21` | 35 |
| `30ed6..30f84` | 174 | `9d0c42d3781811db79aa125ec4434303f32f9cb9fe4c2255fc1c6517b16551aa` | 18 |
| `31002..310de` | 220 | `eb2243bd88ef5f096c0fc55fcb20fa9eda8708411f71afebd2038750e80ffafe` | 17 |
| `3164a..3169c` | 82 | `b6d16062908c8105d16043b8236ca548aa8b9ffaaead9d46cdf160fa0af422cb` | 13 |
| `316ac..316c2` | 22 | `aa61c8ba269adda8d02a7def31dcb430ea6cf09451ecaf83df194a45bcc82722` | 2 |
| `318d8..319b6` | 222 | `e9e6e1949418743242eb86f59b137aec0068a436cdc1bcc3c2df6c57ca7aa838` | 12 |
| `319f6..31a54` | 94 | `f662d9b8a80ba231c10cdafc4d0723016634558cc37e900615f2306077c1f5b6` | 10 |
| `3310c..3312c` | 32 | `1debe47501d3e68b3395be80f270bf619be7050efd06bd3c1c39b481bafd42f1` | 4 |


- [F] 범위 이웃: `306b4` 앞 `306a8..306b4`(N28), `30718..307da`(N28), `307da..308e2`(N28 설치 값 `307da`의 사슬, 결정 2), `30b6c..30cb8`(N29b, 결정 1), `30cb8..30d6c`(N29b 이웃), `30d6c..30dbe`(`2986` 자식 값), `30ed2..30ed6`(N28), `30f84..31002`(N28), `310de..3164a`(설치 `310de`(범위 밖 `3187e`)와 다른 함수), `3169c..316ac`(결정 2), `316c2..318d8`(경계 `316c2` `316f0` `31768` `317b8` `31832` `3185a`, 범위 밖 `318b8`), `319b6..319f6`(결정 2), `31a54..`(interpreter 표 `4a5ac` 대상 `31a54`, `2986` 자식 `31a82`; 재범위 N29 범위 밖), `3312c`(`ST.B 99(A6); BRA.B 3310c`, 참조 없음)·`33132..`(N30).
- [F] 우연 일치(실행 진입 아님): 고정 ROM의 LONG `00030800`(`244a0` 등 14곳), `0003080e` `00030812` `00030814` `0003081a`(`f2048` `db178` 등), `00030a00`(`3d248`), `00030a06`(`f27b8` 등), `00030c40`(`a3772` 등), `00031082`(`990f6` 등 5곳), `00031030`(`53158`)와 명령 바이트 안의 `00030708`(`48696`), `00030900`(`1b64`), `000308a9` `00030c2d` `00030c41` `00030c49` `00030e1f` `00031941`는 명령 중간·홀수이거나 범위 밖 PC다([I] 수치 상수).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "Set/Clear 생산", "FLOW"(C 보존), "끝 Unknown"(`SCS` 소비 뒤 `MOVE`). 태그 없는 block은 Unknown이다. d16(An)·`(An,Dn.W)`는 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. 모든 비교·`TST`·`BTST`·산술과 그 Bcc는 같은 block 안에 있다(결정 5).

**`306b4`(`30918` `30978 BNE`; 애니메이션 `31e3a`, 설치 `306ec`(fall-through), `316b2`·`1aa7e`(사각형 `31ad4`)·`3165e`, 설치 `31002`/`30718`, 끝 `BRA 30ed2`(N28)) 11**
- `306b4`: `MOVEA.L #31e3a, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `306c4`: `MOVE.B 1b(a6), 14(a6); MOVE.L #0, 76(a6); MOVE.L #0, 56(a6); JSR 496c2.l`
- `306e0`: `MOVE.B #ff, 94(a6); MOVE.L #306ec, (a6)` (→`306ec`)
- `306ec`: `JSR 316b2(pc)` — FLOW
- `306f0`: `LEA.L 31ad4.l, a0; JSR 1aa7e.l` — FLOW
- `306fc`: `BCC.W 30706` (→`30700`) — C 소비, FLOW
- `30700`: `MOVE.L #31002, (a6)` (→`30706`)
- `30706`: `JSR 3165e(pc)` — FLOW
- `3070a`: `BCC.W 30714` (→`3070e`) — C 소비, FLOW
- `3070e`: `MOVE.L #30718, (a6)` (→`30714`)
- `30714`: `BRA.W 30ed2` — FLOW

**`308e2`(범위 밖 `3086e BMI`·설치 `306a2`, 범위 안 `30982 BNE`·설치 `309e8`; 설치 `308fe`(fall-through), `3166c` 입력 판정, 끝 `BRA 30ed6`) 14**
- `308e2`: `MOVEA.L #31f0c, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `308f2`: `MOVE.B #1, 94(a6); MOVE.L #308fe, (a6)` (→`308fe`)
- `308fe`: `JSR 3166c(pc)` — FLOW
- `30902`: `BTST.B #7, d0; BNE.W 309f2` (→`3090a`) — FLOW
- `3090a`: `BTST.B #7, 15(a6); BEQ.W 3091c` (→`30914`) — FLOW
- `30914`: `BTST.B #5, d0; BNE.W 306b4` (→`3091c`) — FLOW
- `3091c`: `MOVE.W d0, d1; ANDI.W #f, d1; BEQ.W 30942` (→`30926`)
- `30926`: `JSR 316f0(pc)` — FLOW
- `3092a`: `JSR 317b8(pc)` — FLOW
- `3092e`: `JSR 31832(pc)` — FLOW
- `30932`: `JSR 31696(pc)` — FLOW
- `30936`: `JSR 3165e(pc)` — FLOW
- `3093a`: `JSR 3185a(pc)` — FLOW
- `3093e`: `BRA.W 30ed6` — FLOW

**`30942`(`30922 BEQ`; 설치 `3095e`(fall-through), `316c2` 결과로 LONG `3a` 임시 이동, 끝 `BRA 30ed6`) 14**
- `30942`: `MOVEA.L #31f0c, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `30952`: `MOVE.B #1, 94(a6); MOVE.L #3095e, (a6)` (→`3095e`)
- `3095e`: `JSR 3166c(pc)` — FLOW
- `30962`: `BTST.B #7, d0; BNE.W 309f2` (→`3096a`) — FLOW
- `3096a`: `BTST.B #7, 15(a6); BEQ.W 3097c` (→`30974`) — FLOW
- `30974`: `BTST.B #5, d0; BNE.W 306b4` (→`3097c`) — FLOW
- `3097c`: `MOVE.W d0, d1; ANDI.W #f, d1; BNE.W 308e2` (→`30986`)
- `30986`: `JSR 317b8(pc)` — FLOW
- `3098a`: `JSR 31832(pc)` — FLOW
- `3098e`: `MOVE.L 3a(a6), -(a7); JSR 316c2(pc)`
- `30996`: `SWAP d0; CLR.W d0; ASR.L #6, d0; ADD.L d0, 3a(a6); JSR 31696(pc)`
- `309a4`: `MOVE.L (a7)+, 3a(a6); JSR 3165e(pc)`
- `309ac`: `JSR 3185a(pc)` — FLOW
- `309b0`: `BRA.W 30ed6` — FLOW

**설치 callback `309b4`(`30f66` 설치; 설치 `309d0`(fall-through), `3165e` C로 설치 `308e2`) 10**
- `309b4`: `MOVEA.L #32084, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `309c4`: `MOVE.B #2, 94(a6); MOVE.L #309d0, (a6)` (→`309d0`)
- `309d0`: `JSR 3166c(pc)` — FLOW
- `309d4`: `JSR 317b8(pc)` — FLOW
- `309d8`: `JSR 31832(pc)` — FLOW
- `309dc`: `JSR 31696(pc)` — FLOW
- `309e0`: `JSR 3165e(pc)` — FLOW
- `309e4`: `BCC.W 309ee` (→`309e8`) — C 소비, FLOW
- `309e8`: `MOVE.L #308e2, (a6)` (→`309ee`)
- `309ee`: `BRA.W 30ed6` — FLOW

**`309f2`(`30906` `30966 BNE`; `31a12`, 설치 `30a30`(fall-through), LONG `36`/`3a` 감쇠, `4ae4a`(`31c2a`)) 8**
- `309f2`: `MOVEA.L #31f0c, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `30a02`: `MOVE.B #ff, 94(a6); MOVE.B #1, d1; JSR 31a12(pc)`
- `30a10`: `MOVE.L #0, 56(a6); MOVE.L #31c92, 76(a6); MOVE.W #1ac8, d0; JSR 3af8.l`
- `30a2a`: `MOVE.L #30a30, (a6)` (→`30a30`)
- `30a30`: `MOVE.L #100000, d0; SUB.L 36(a6), d0; ASR.L #3, d0; ADD.L d0, 36(a6); MOVE.L 3a(a6), d0; ASR.L #4, d0; SUB.L d0, 3a(a6); MOVEQ #0, d0; JSR 31832(pc)`
- `30a50`: `JSR 316ac(pc)` — FLOW
- `30a54`: `JSR 3165e(pc)` — FLOW
- `30a58`: `MOVE.W #8000, 8a(a6); LEA.L 31c2a.l, a0; JSR 4ae4a.l`

**`30a6a` 계산 점프(`4ae4a` 반환 `D0.W` < 9, BRA.W 표 `30a7a` 9 slot) / `30a9e` 판정, 끝 `BRA 30fa0`(N28 내부, 결정 3) 15**
- `30a6a`: `CMPI.W #9, d0; BCC.W 30a9e` (→`30a72`)
- `30a72`: `ADD.W d0, d0; ADD.W d0, d0; JMP 30a7a(pc, d0.w)`
- `30a7a`: `BRA.W 30a9e` — FLOW
- `30a7e`: `BRA.W 30ac0` — FLOW
- `30a82`: `BRA.W 30ac0` — FLOW
- `30a86`: `BRA.W 30ac0` — FLOW
- `30a8a`: `BRA.W 30a9e` — FLOW
- `30a8e`: `BRA.W 30a9e` — FLOW
- `30a92`: `BRA.W 30a9e` — FLOW
- `30a96`: `BRA.W 30a9e` — FLOW
- `30a9a`: `BRA.W 30a9e` — FLOW
- `30a9e`: `CMPI.W #110, 42(a6); BGT.W 30ac0` (→`30aa8`)
- `30aa8`: `BTST.B #5, 15(a6); BNE.W 30ac0` (→`30ab2`) — FLOW
- `30ab2`: `BTST.B #0, 61(a6); BNE.W 30ac0` (→`30abc`) — FLOW
- `30abc`: `BRA.W 30fa0` — FLOW

**`30ac0`(파괴: `4ae4a`(`31c48`) `4ff96` `d3d7c` 네 번, `2986` 자식 `30d6c`, `49214`, `JMP 2a00`) 9**
- `30ac0`: `LEA.L 31c48.l, a0; JSR 4ae4a.l` — FLOW
- `30acc`: `MOVEQ #1, d0; MOVEQ #0, d1; JSR 4ff96.l`
- `30ad6`: `JSR d3d7c.l` — FLOW
- `30adc`: `MOVE.L #ffee0000, 36(a0); MOVE.L #240000, 3a(a0); MOVE.W #a, 54(a0); JSR d3d7c.l`
- `30af8`: `MOVE.L #e0000, 36(a0); MOVE.L #200000, 3a(a0); MOVE.W #7, 54(a0); JSR d3d7c.l`
- `30b14`: `MOVE.L #fff40000, 36(a0); MOVE.L #10000, 3a(a0); MOVE.W #7, 54(a0); JSR d3d7c.l`
- `30b30`: `MOVE.L #a0000, 36(a0); MOVE.L #fffc0000, 3a(a0); MOVE.W #5, 54(a0); MOVEA.L #30d6c, a0; MOVE.W #1e, d0; MOVEA.L #100bf4, a1; JSR 2986.l`
- `30b5c`: `MOVEQ #0, d0; MOVEQ #10, d1; JSR 49214.l`
- `30b66`: `JMP 2a00.l` — FLOW

**`28ae` 자식 callback `30dbe`(`319a4`)·설치 `30de4` `30e38` `30e8a` `30eae` `30dd4`(`30ec4`) / 공유 `JMP 2a00` `30ecc` 35**
- `30dbe`: `JSR 3164a(pc)` — FLOW
- `30dc2`: `BCS.W 30ecc` (→`30dc6`) — C 소비, FLOW
- `30dc6`: `JSR 1abda.l` — FLOW
- `30dcc`: `MOVEQ #0, d1; JSR 8ebe.l`
- `30dd4`: `MOVEQ #0, d0; MOVEQ #0, d1; JSR 49290.l`
- `30dde`: `MOVE.L #30de4, (a6)` (→`30de4`)
- `30de4`: `JSR 288c.l` — FLOW
- `30dea`: `BCC.W 30ecc` (→`30dee`) — C 소비, FLOW
- `30dee`: `JSR 43e34.l` — FLOW
- `30df4`: `JSR ea680.l` — FLOW
- `30dfa`: `BCC.W 30e12` (→`30dfe`) — C 소비, FLOW
- `30dfe`: `MOVE.L d1, d3; ADD.L 18(a0), d3; SUB.L 46(a6), d3; CMPI.L #300000, d3; BLE.W 30e14` (→`30e12`)
- `30e12`: `RTS` — FLOW
- `30e14`: `MOVE.W #e2, 20(a6); MOVE.L 200094.l, 22(a6); MOVEA.L #32f16, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `30e32`: `MOVE.L #30e38, (a6)` (→`30e38`)
- `30e38`: `JSR 288c.l` — FLOW
- `30e3e`: `BCC.W 30ecc` (→`30e42`) — C 소비, FLOW
- `30e42`: `MOVEQ #0, d0; MOVEQ #0, d1; JSR 49290.l`
- `30e4c`: `JSR ea680.l` — FLOW
- `30e52`: `BCC.W 30e8a` (→`30e56`) — C 소비, FLOW
- `30e56`: `MOVE.L d1, d3; ADD.L 18(a0), d3; SUB.L 46(a6), d3; CMPI.L #300000, d3; BLE.W 30e70` (→`30e6a`)
- `30e6a`: `MOVE.L #30e8a, (a6)` (→`30e70`)
- `30e70`: `MOVEA.L a0, a1; LEA.L 2e(a6), a0; JSR 43e22.l` — FLOW
- `30e7c`: `JSR 16ed2.l` — FLOW
- `30e82`: `JSR 49fc6.l` — FLOW
- `30e88`: `RTS` — FLOW
- `30e8a`: `MOVE.W #e2, 20(a6); MOVE.L 200094.l, 22(a6); MOVEA.L #32ec4, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `30ea8`: `MOVE.L #30eae, (a6)` (→`30eae`)
- `30eae`: `JSR 43e34.l` — FLOW
- `30eb4`: `JSR 16ed2.l` — FLOW
- `30eba`: `JSR 49fc6.l` — FLOW
- `30ec0`: `BCC.W 30eca` (→`30ec4`) — C 소비, FLOW
- `30ec4`: `MOVE.L #30dd4, (a6)` (→`30eca`)
- `30eca`: `RTS` — FLOW
- `30ecc`: `JMP 2a00.l` — FLOW

**공유 꼬리 `30ed6`(N28 결정 1; 범위 밖 `305ae` `30610` `30834` `30866` `308de`, 범위 안 `3093e` `309b0` `309ee BRA`; 끝 `30f7e JSR 4d9ba` 복귀 `30f84`(N28)) 18**
- `30ed6`: `JSR 31768(pc)` — FLOW
- `30eda`: `MOVE.B 97(a6), d0; BEQ.W 30ee8` (→`30ee2`)
- `30ee2`: `SUBQ.B #1, d0; MOVE.B d0, 97(a6)` (→`30ee8`)
- `30ee8`: `MOVE.B 98(a6), d0; BEQ.W 30ef6` (→`30ef0`)
- `30ef0`: `SUBQ.B #1, d0; MOVE.B d0, 98(a6)` (→`30ef6`)
- `30ef6`: `JSR 319f6(pc)` — FLOW
- `30efa`: `BCS.W 30f08` (→`30efe`) — C 소비, FLOW
- `30efe`: `MOVE.L #30718, (a6); BRA.W 30f84`
- `30f08`: `MOVE.W 84(a6), d0; JSR 4d7a6.l`
- `30f12`: `CMPI.B #9, d0; BNE.W 30f22` (→`30f1a`)
- `30f1a`: `MOVE.B d1, 99(a6); MOVE.B d2, 9a(a6)` (→`30f22`)
- `30f22`: `TST.B 5e(a6); BEQ.W 30f6c` (→`30f2a`)
- `30f2a`: `BTST.B #6, 61(a6); BNE.W 30f6c` (→`30f34`) — FLOW
- `30f34`: `MOVE.W #2d, 88(a6); ST.B 8c(a6); MOVE.B 5f(a6), d1; ANDI.B #f, d1; LSL.B #4, d1; MOVE.L #60000, d0; JSR 443d2.l`
- `30f54`: `ADD.L d0, 36(a6); ADD.L d1, 3a(a6); MOVE.W #1a59, d0; JSR 3af8.l`
- `30f66`: `MOVE.L #309b4, (a6)` (→`30f6c`)
- `30f6c`: `MOVE.W 84(a6), d0; JSR 4d734.l`
- `30f76`: `MOVE.W 84(a6), d0; MOVEA.L 56(a6), a1; JSR 4d9ba.l`

**`31002`(`JMP 2a24`; 설치 `30700`·범위 밖 `3076e` 등, `3199a BCC`) / `28ae` 자식 callback `31008`(`3198a`)·설치 `31032` 17**
- `31002`: `JMP 2a24.l` — FLOW
- `31008`: `MOVE.W #112, 20(a6); MOVE.L 2000ac.l, 22(a6); MOVE.B #ff, 94(a6); MOVE.W #ffff, 86(a6); MOVEQ #0, d0; MOVEQ #0, d1; JSR 49290.l`
- `3102c`: `MOVE.L #31032, (a6)` (→`31032`)
- `31032`: `JSR 288c.l` — FLOW
- `31038`: `BCC.W 310d8` (→`3103c`) — C 소비, FLOW
- `3103c`: `JSR 491c4.l` — FLOW
- `31042`: `TST.B 94(a0); BPL.W 3104c` (→`3104a`)
- `3104a`: `RTS` — FLOW
- `3104c`: `MOVE.W 1e(a0), 1e(a6); MOVE.W 84(a0), 84(a6); MOVE.B 90(a0), 90(a6); MOVEA.L c(a6), a0; MOVE.W 86(a0), d0; CMP.W 86(a6), d0; BEQ.W 31092` (→`3106e`)
- `3106e`: `MOVE.W d0, 86(a6); JSR 8ff4.l`
- `31078`: `MOVE.W 86(a6), d0; LEA.L 31c84.l, a0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; MOVE.B #1, d1; JSR 8ebe.l`
- `31092`: `MOVEA.L c(a6), a0; MOVE.B 94(a0), d0; CMP.B 94(a6), d0; BEQ.W 310ca` (→`310a2`)
- `310a2`: `MOVE.B d0, 94(a6); ANDI.W #ff, d0; ADD.W d0, d0; ADD.W d0, d0; ADD.W 86(a6), d0; ADD.W d0, d0; ADD.W d0, d0; LEA.L 31d3e.l, a0; MOVEA.L (a0, d0.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `310ca`: `JSR 43e34.l` — FLOW
- `310d0`: `JSR 49fc6.l` — FLOW
- `310d6`: `RTS` — FLOW
- `310d8`: `JMP 2a00.l` — FLOW

**helper `3164a`(C 반환) `3165e` `3166c` `31696` `316ac` `316b2`(범위 밖 `3169c` 제외) 15**
- `3164a`: `JSR 1aa3a.l` — FLOW
- `31650`: `ANDI.W #8, d0; BEQ.W 3165c` (→`31658`) — Clear 생산
- `31658`: `ORI.B #1, ccr` (→`3165c`) — Set 생산
- `3165c`: `RTS` — FLOW
- `3165e`: `JSR 492c8.l` — FLOW
- `31664`: `JSR 49fc6.l` — FLOW
- `3166a`: `RTS` — FLOW
- `3166c`: `MOVE.W 84(a6), d0; JSR 49c38.l`
- `31676`: `SCS.B a0(a6); MOVE.W 84(a6), d0; JSR 49be0.l` — C 소비, 끝 Unknown
- `31684`: `MOVE.W (a0), d0; BTST.B #6, d0; BEQ.W 31694` (→`3168e`)
- `3168e`: `MOVE.B #f, 97(a6)` (→`31694`)
- `31694`: `RTS` — FLOW
- `31696`: `JMP 4be82.l` — FLOW
- `316ac`: `JMP 4be6c.l` — FLOW
- `316b2`: `MOVEQ #0, d0; MOVE.L d0, 36(a6); MOVE.L d0, 3a(a6); JMP 4be6c.l`

**`318d8`(N28 `306a8`·범위 밖 `304ee` `30502` `30652` `JSR`; bank LONG `2000ac`, `28ae` 자식 `41fe6` `31008` `30dbe`) 12**
- `318d8`: `MOVE.W #112, 20(a6); MOVE.L 2000ac.l, 22(a6); MOVE.W #1f4, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `318f4`: `MOVE.W #1f4, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `31902`: `MOVE.W #1d9, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `31910`: `MOVE.W #8810, 68(a6); MOVE.W #8810, 1e(a6); MOVEQ #9, d1; JSR 4d81c.l`
- `31924`: `MOVE.B d1, 99(a6); MOVE.B d2, 9a(a6); MOVE.W d3, 54(a6); MOVE.W #ffff, 92(a6); MOVE.W #e80, 90(a6); MOVEQ #0, d0; MOVE.B d0, 97(a6); MOVE.B d0, 98(a6); JSR 496c2.l`
- `3194c`: `MOVEA.L #41fe6, a0; MOVE.W #a, d0; JSR 28ae.l`
- `3195c`: `BCC.W 3198a` (→`31960`) — C 소비, FLOW
- `31960`: `LEA.L 8a(a6), a1; MOVE.L a1, 76(a0); MOVE.B #9, 7a(a0); MOVE.B #4, 7b(a0); MOVE.B #0, 7c(a0); MOVE.B #3, 7d(a0); MOVE.B #0, 7e(a0); ORI.B #1, ccr` (→`3198a`) — Set 생산
- `3198a`: `MOVEA.L #31008, a0; MOVE.W #a, d0; JSR 28ae.l`
- `3199a`: `BCC.W 31002` (→`3199e`) — C 소비, FLOW
- `3199e`: `MOVE.B #ff, 94(a6); MOVEA.L #30dbe, a0; MOVE.W #a, d0; JSR 28ae.l`
- `319b4`: `RTS` — FLOW

**helper `319f6`(C 반환) `31a12`(BYTE push) / interpreter 표 진입 `31a2a`(LONG `4a5a4`)·`31a44`(LONG `4a5a8`) 10**
- `319f6`: `MOVE.W 84(a6), d0; MOVEQ #0, d2; MOVEQ #18, d3; JSR 4d418.l`
- `31a04`: `BCC.W 31a10` (→`31a08`) — C 소비, FLOW
- `31a08`: `MOVE.W d0, 86(a6); ORI.B #1, ccr` (→`31a10`) — Set 생산
- `31a10`: `RTS` — FLOW
- `31a12`: `MOVE.B d1, -(a7); JSR 4d8d8.l`
- `31a1a`: `MOVE.B (a7)+, d1; TST.B d0; BPL.W 31a24` (→`31a22`)
- `31a22`: `RTS` — FLOW
- `31a24`: `JMP 4d4b4.l` — FLOW
- `31a2a`: `MOVE.L (a0), d0; MOVE.B (a0), d1; ANDI.L #ffffff, d0; MOVEA.L d0, a0; ANDI.W #ff, d1; MOVE.B (a6, d1.w), d1; ADD.W d1, d1; ADD.W d1, d1; ADDA.W d1, a0` (→`31a44`)
- `31a44`: `MOVEA.L (a0), a0; MOVE.W (a0)+, 8a(a6); MOVE.W (a0)+, 9c(a6); MOVE.W (a0)+, 9e(a6); RTS`

**stage event callback `3310c`(LONG `e8cd0`; 설치 `33132`(N30 값)) 4**
- `3310c`: `CMPI.W #0, 76(a6); BNE.W 3311c` (→`33116`)
- `33116`: `JSR 4c0ea.l` — FLOW
- `3311c`: `CLR.W 76(a6); JSR 33b12(pc)`
- `33124`: `MOVE.L #33132, (a6); RTS`

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다):
  - `306b4`: `49f8c`(A1 = `31e3a`, `D0.W` = `100`). `306c4`: BYTE `14` = BYTE `1b`, LONG `76` = LONG `56` = 0, `JSR 496c2`(U11). `306e0`: BYTE `94` = `ff`, `(A6)` = `306ec`, fall-through. `306ec`: `JSR 316b2`. `306f0`: A0 = `31ad4`, `JSR 1aa7e`(U01); Set이면 `(A6)` = `31002`(`30700`). `30706`: `JSR 3165e`; Set이면 `(A6)` = `30718`(`3070e`). `30714`: `BRA 30ed2`(N28 → `30f84`).
  - `308e2`/`30942`: `49f8c`(A1 = `31f0c`), BYTE `94` = 1, `(A6)` = `308fe`/`3095e`, fall-through, `JSR 3166c`. `30902`/`30962`: `D0` bit 7 = 1이면 `309f2`. `3090a`/`3096a`: BYTE `15` bit 7 = 1이고(`30914`/`30974`) `D0` bit 5 = 1이면 `306b4`. `3091c`: `D1.W` = `D0.W` & `f`; 0이면 `30942`, 아니면 `JSR 316f0` `317b8` `31832` `31696` `3165e` `3185a`, `BRA 30ed6`. `3097c`: `D1.W` = `D0.W` & `f`; ≠ 0이면 `308e2`, 0이면 `JSR 317b8` `31832`(`30986` `3098a`). `3098e`: push LONG `3a`, `JSR 316c2`. `30996`: `SWAP D0; CLR.W D0`(`D0` = `D0.W`(복귀값) << 16), `D0` = `D0` 산술 >> 6, LONG `3a` += `D0`(32 bit), `JSR 31696`. `309a4`: LONG `3a` = pop LONG(원래 값), `JSR 3165e`. `309ac`: `JSR 3185a`, `BRA 30ed6`.
  - `309b4`(설치): `49f8c`(A1 = `32084`), BYTE `94` = 2, `(A6)` = `309d0`, fall-through, `JSR 3166c` `317b8` `31832` `31696` `3165e`; Set이면 `(A6)` = `308e2`(`309e8`). `BRA 30ed6`.
  - `309f2`: `49f8c`(A1 = `31f0c`). `30a02`: BYTE `94` = `ff`, `D1.B` = 1, `JSR 31a12`. `30a10`: LONG `56` = 0, LONG `76` = `31c92`, `3af8`(`D0.W` = `1ac8`). `30a2a`: `(A6)` = `30a30`, fall-through. `30a30`: `D0` = (`100000` − LONG `36`) 산술 >> 3, LONG `36` += `D0`; `D0` = LONG `3a` 산술 >> 4, LONG `3a` −= `D0`(모두 32 bit), `D0` = 0, `JSR 31832`. `30a50`: `JSR 316ac`. `30a54`: `JSR 3165e`. `30a58`: `8a.W` = `8000`, A0 = `31c2a`, `JSR 4ae4a`(N08). `30a6a`/`30a72`/slot: 결정 4. `30a9e`: 부호 있는 `42.W` > `110`이면 `30ac0`; BYTE `15` bit 5 = 1이면 `30ac0`; BYTE `61` bit 0 = 1이면 `30ac0`; 아니면 `BRA 30fa0`(결정 3).
  - `30ac0`: A0 = `31c48`, `JSR 4ae4a`. `30acc`: `D0` = 1, `D1` = 0, `JSR 4ff96`(경계). `30ad6`: `JSR d3d7c`(경계). `30adc` `30af8` `30b14` `30b30`: 반환 A0 노드에 LONG `36` / LONG `3a` / `54.W` = (`ffee0000`, `240000`, `a`) / (`e0000`, `200000`, 7) / (`fff40000`, `10000`, 7) / (`a0000`, `fffc0000`, 5); 앞 셋은 다시 `JSR d3d7c`, `30b30`은 `2986`(A0 = `30d6c`, `D0.W` = `1e`, A1 = `100bf4`; 결정 7). `30b5c`: `D0` = 0, `D1` = `10`, `JSR 49214`(N05). `30b66`: `JMP 2a00`.
  - `30dbe`: `JSR 3164a`; Set이면 `JMP 2a00`(`30ecc`). `30dc6`: `JSR 1abda`(U12). `30dcc`: `D1` = 0, `JSR 8ebe`(U02). `30dd4`: `D0` = `D1` = 0, `JSR 49290`(U08). `30dde`: `(A6)` = `30de4`, fall-through. `30de4`: `JSR 288c`; Clear면 `JMP 2a00`. `30dee`: `JSR 43e34`. `30df4`: `JSR ea680`(경계); Clear면 RTS(`30e12`). `30dfe`: `D3` = `D1` + LONG `18(A0)` − LONG `46`(32 bit); 부호 있는 `D3` ≤ `300000`이면 `30e14`, 아니면 RTS. `30e14`: `20.W` = `e2`, LONG `22` = bank LONG `200094`, `49f8c`(A1 = `32f16`). `30e32`: `(A6)` = `30e38`, fall-through. `30e38`: `JSR 288c`; Clear면 `JMP 2a00`. `30e42`: `D0` = `D1` = 0, `JSR 49290`. `30e4c`: `JSR ea680`; Clear면 `30e8a`. `30e56`: `30dfe`와 같은 `D3`; ≤ `300000`이면 `30e70`, 아니면 `(A6)` = `30e8a`(`30e6a`). `30e70`: A1 = A0, A0 = A6 + `2e`, `JSR 43e22`(cleanup) → `JSR 16ed2`(sprite) → `JSR 49fc6` → RTS. `30e8a`: `20.W` = `e2`, LONG `22` = bank LONG `200094`, `49f8c`(A1 = `32ec4`), `(A6)` = `30eae`, fall-through. `30eae`: `JSR 43e34` `16ed2` `49fc6`; Set이면 `(A6)` = `30dd4`(`30ec4`). RTS.
  - `30ed6`: `JSR 31768`(경계). `30eda`/`30ee8`: `D0.B` = BYTE `97`/`98`; ≠ 0이면 1 줄여 다시 쓴다(`30ee2`/`30ef0`). `30ef6`: `JSR 319f6`; Clear면 `(A6)` = `30718`, `BRA 30f84`(N28, `30efe`). `30f08`: `D0.W` = `84.W`, `JSR 4d7a6`(input). `30f12`: `D0.B` = 9이면 BYTE `99` = `D1.B`, BYTE `9a` = `D2.B`(`30f1a`). `30f22`: BYTE `5e` ≠ 0이고 BYTE `61` bit 6 = 0이면 `30f34`: `88.W` = `2d`, BYTE `8c` = `ff`, `D1.B` = (BYTE `5f` & `f`) << 4, `D0` = `60000`, `JSR 443d2`(U02). `30f54`: LONG `36` += `D0`, LONG `3a` += `D1`(32 bit), `3af8`(`D0.W` = `1a59`). `30f66`: `(A6)` = `309b4`. `30f6c`: `D0.W` = `84.W`, `JSR 4d734`(경계). `30f76`: `D0.W` = `84.W`, A1 = LONG `56`, `JSR 4d9ba`(경계; 복귀 `30f84` N28).
  - `31002`: `JMP 2a24`. `31008`: `20.W` = `112`, LONG `22` = bank LONG `2000ac`, BYTE `94` = `ff`, `86.W` = `ffff`, `D0` = `D1` = 0, `JSR 49290`. `3102c`: `(A6)` = `31032`, fall-through. `31032`: `JSR 288c`; Clear면 `JMP 2a00`(`310d8`). `3103c`: `JSR 491c4`(U17). `31042`: BYTE `94(A0)` bit 7 = 1이면 RTS(`3104a`). `3104c`: `1e.W` = `1e.W(A0)`, `84.W` = `84.W(A0)`, BYTE `90` = BYTE `90(A0)`, A0 = LONG `c`(부모), `D0.W` = `86.W(부모)`; `86.W`와 같으면 `31092`. `3106e`: `86.W` = `D0.W`, `JSR 8ff4`(cleanup). `31078`: `D0.W` = WORD(`31c84` + sext(2·`86.W`)), `D1.B` = 1, `JSR 8ebe`. `31092`: A0 = LONG `c`, `D0.B` = BYTE `94(부모)`; BYTE `94`와 같으면 `310ca`. `310a2`: BYTE `94` = `D0.B`, `D0.W` = (4·`D0.B` + `86.W`)·4(16 bit), A0 = `31d3e`, A1 = LONG(A0 + sext(`D0.W`)), `49f8c`(`D0.W` = `100`). `310ca`: `JSR 43e34` `49fc6`, RTS.
  - `3164a`: `JSR 1aa3a`(U08: `D0.W` = WORD `543c(A5)`). `31650`: `D0.W` &= 8(C = 0); 0이면 RTS, 아니면 C = 1(`31658`) 뒤 RTS. `3165e`: `JSR 492c8`(U12), `JSR 49fc6`, RTS(C는 `49fc6`의 값). `3166c`: `D0.W` = `84.W`, `JSR 49c38`(경계). `31676`: BYTE `a0` = (C = 1) ? `ff` : 0(`SCS`), `D0.W` = `84.W`, `JSR 49be0`(U06). `31684`: `D0.W` = WORD (A0); bit 6 = 1이면 BYTE `97` = `f`(`3168e`). RTS. `31696`: `JMP 4be82`(U08b). `316ac`: `JMP 4be6c`(경계). `316b2`: `D0` = 0, LONG `36` = LONG `3a` = 0, `JMP 4be6c`.
  - `318d8`: `20.W` = `112`, LONG `22` = bank LONG `2000ac`, `8ebe`(`1f4`, 1) 두 번, `8ebe`(`1d9`, 1). `31910`: `68.W` = `1e.W` = `8810`, `D1` = 9, `JSR 4d81c`(stage_area). `31924`: BYTE `99` = `D1.B`, BYTE `9a` = `D2.B`, `54.W` = `D3.W`, `92.W` = `ffff`, `90.W` = `e80`, `D0` = 0, BYTE `97` = BYTE `98` = 0, `JSR 496c2`. `3194c`: `28ae`(A0 = `41fe6`, `D0.W` = `a`); Set이면 `31960`: A1 = A6 + `8a`, 자식 LONG `76` = A1, BYTE `7a` = 9, `7b` = 4, `7c` = 0, `7d` = 3, `7e` = 0, C = 1. `3198a`: `28ae`(A0 = `31008`); Clear면 `JMP 2a24`(`31002`). `3199e`: BYTE `94` = `ff`, `28ae`(A0 = `30dbe`), RTS(`319b4`).
  - `319f6`: `D0.W` = `84.W`, `D2` = 0, `D3` = `18`, `JSR 4d418`(경계); Set이면 `86.W` = `D0.W`, C = 1(`31a08`). RTS. `31a12`: push BYTE `D1.B`(A7 −= 2), `JSR 4d8d8`(경계). `31a1a`: `D1.B` = pop BYTE(A7 += 2); `D0.B` bit 7 = 1이면 RTS(`31a22`), 아니면 `JMP 4d4b4`(경계).
  - `31a2a`: `D0` = LONG (A0), `D1.B` = BYTE (A0), A0 = `D0` & `ffffff`, `D1.W` &= `ff`, `D1.B` = BYTE(A6 + `D1.W`), `D1.W` = 4·`D1.W`, A0 += sext(`D1.W`), fall-through. `31a44`: A0 = LONG (A0), `8a.W` `9c.W` `9e.W` = WORD (A0)+ 세 번, RTS.
  - `3310c`: `76.W` = 0이면 `JSR 4c0ea`(경계). `3311c`: `76.W` = 0(`CLR.W`), `JSR 33b12`(경계). `33124`: `(A6)` = `33132`, RTS.

## carry

- [F] **소비 15 block**(`31676`만 끝 Unknown, 나머지 FLOW). Unknown C로 들어오면 `objects n29 caller requires known carry`(상태 보존)다. Clear면 BCC는 분기 대상, BCS는 fall-through; Set이면 반대. `SCS`는 Set이면 `ff`, Clear면 0을 쓴다.
  - `306fc BCC.W 30706`: U01 `1aa7e`(`1aaf6 ANDI` Clear, `1aafc ORI` Set).
  - `3070a BCC.W 30714`, `309e4 BCC.W 309ee`: `3165e`의 C = interpreter `49fc6`의 C.
  - `30dc2 BCS.W 30ecc`: `3164a`(N29 생산 `31650`/`31658`).
  - `30dea BCC.W 30ecc`, `30e3e BCC.W 30ecc`, `31038 BCC.W 310d8`: stage_event_ops `288c`(`2898` `28a8 ORI` Set, `289e CMPI.L #270e,(A0)` 같음 = Clear).
  - `30dfa BCC.W 30e12`, `30e52 BCC.W 30e8a`: 경계 `ea680`(결정 6).
  - `30ec0 BCC.W 30eca`: interpreter `49fc6`.
  - `30efa BCS.W 30f08`: `319f6`(N29 생산 `31a08` Set, `31a04` Clear 통과).
  - `3195c BCC.W 3198a`, `3199a BCC.W 31002`: fade_card `28ae`(`2908 ORI` Set, `290e ANDI` Clear).
  - `31a04 BCC.W 31a10`: 경계 `4d418`(결정 6).
  - `31676 SCS.B a0(A6)`: 경계 `49c38`(결정 6).
- [F] **known 생산 4 block**: Clear(`ANDI.W #8,D0`) `31650`; Set(`ORI`) `31658` `31960` `31a08`. RTS 앞 생산의 소비자 확인은 아래 검증 기록(`30dc2`/`30efa`를 복귀 LONG으로 둔 native 분기).
- [F] **FLOW_ONLY 101 block**(C 보존): JSR/JMP/BRA/RTS block, `LEA`/`MOVEA`+`JSR`(`30ac0` `30e70`), `BTST`(+Bcc) block(`30902` `3090a` `30914` `30962` `3096a` `30974` `30aa8` `30ab2` `30f2a`), BRA.W slot 9개, 소비 14개. 목록: `306ec` `306f0` `306fc` `30706` `3070a` `30714` `308fe` `30902` `3090a` `30914` `30926` `3092a` `3092e` `30932` `30936` `3093a` `3093e` `3095e` `30962` `3096a` `30974` `30986` `3098a` `309ac` `309b0` `309d0` `309d4` `309d8` `309dc` `309e0` `309e4` `309ee` `30a50` `30a54` `30a7a` `30a7e` `30a82` `30a86` `30a8a` `30a8e` `30a92` `30a96` `30a9a` `30aa8` `30ab2` `30abc` `30ac0` `30ad6` `30b66` `30dbe` `30dc2` `30dc6` `30de4` `30dea` `30dee` `30df4` `30dfa` `30e12` `30e38` `30e3e` `30e4c` `30e52` `30e70` `30e7c` `30e82` `30e88` `30eae` `30eb4` `30eba` `30ec0` `30eca` `30ecc` `30ed6` `30ef6` `30efa` `30f2a` `31002` `31032` `31038` `3103c` `3104a` `310ca` `310d0` `310d6` `310d8` `3164a` `3165c` `3165e` `31664` `3166a` `31694` `31696` `316ac` `3195c` `3199a` `319b4` `31a04` `31a10` `31a22` `31a24` `33116`.
- [F] **carry 보존 목록 102 PC** = FLOW_ONLY 101 + `31676`(SCS 소비; 실행부가 C를 읽은 뒤 Unknown으로 둔다). 생산 4 block은 보존 목록에 넣지 않고 block 안에서 C를 정한다.
- [F] **Unknown 87 block**: 나머지(`MOVE`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`ADD`/`SUB`/`SUBQ`/`ANDI`/`ASR`/`LSL`/`SWAP`/`CLR` 포함 block, 설치 block, `31676`).
- [F] RTS로 돌려주는 C가 쓰이는 N29 함수는 `3164a`(소비 `30dc2`, 범위 밖 `31a94` `315e4` 근처)와 `319f6`(소비 `30efa`, N28 `30790`, N29b `30c7c`)다. `3165e`는 `49fc6`의 C를 그대로 돌려준다(FLOW). `31a12`의 끝 RTS(`31a22`, 앞 `TST.B`)·`31694`·`31a44`·`3104a`·`30e12` 등의 C는 쓰이지 않는다(호출자가 바로 덮거나 scheduler/interpreter 복귀).

## 구현 범위와 규약

- routing 10 범위(위 표). 짝수 PC 936개 중 block 시작 192, 내부 744. 내부 PC 직접 진입은 `unsupported animation objects n29 PC`다. 범위 이웃(미참조·범위 밖 전용 코드 `3169c..316ac` `319b6..319f6`, 자료, N28·N29b·N30 범위)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)이거나 그 단위 실행부다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`는 LONG 전체). 산술·shift는 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다(`ASR.L #3/#4/#6`은 부호 bit 채움을 직접 계산). 부호 있는 비교(`BGT` WORD, `BLE` LONG)는 값을 부호 있는 정수로 명시 변환해 비교한다. 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다). `CLR.W`는 쓰기만 한다(기존 관례).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 102 PC를 넣는다.
- 제어 이동은 `30a72`(결정 4)를 빼면 모두 정적이다. `30b66` `30ecc` `310d8 JMP 2a00`, `31002 JMP 2a24`, `31696 JMP 4be82`, `316ac`/`316bc JMP 4be6c`, `31a24 JMP 4d4b4`는 복귀 LONG을 push하지 않는다. 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`306e0`→`306ec`, `308f2`→`308fe`, `30952`→`3095e`, `309c4`→`309d0`, `30a2a`→`30a30`, `30dde`→`30de4`, `30e32`→`30e38`, `30ea8`→`30eae`, `3102c`→`31032`). `30e6a`→`30e70`, `30ec4`→`30eca`, `30f66`→`30f6c`, `31960`→`3198a`, `31a2a`→`31a44`도 이어진다. `30714`(`BRA 30ed2`)·`30efe`(`BRA 30f84`)·`30f76`(복귀 `30f84`)는 N28로, `30abc`(`BRA 30fa0`)는 N28 `30fa0`(결정 3)으로 넘긴다.
- 스택: JSR 복귀 LONG, `3098e`/`309a4`의 LONG push/pop, `31a12`/`31a1a`의 BYTE push/pop(A7 ±2, `push_program_stack`/`pop_program_stack` 크기 1). work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `200094`(`30e14` `30e8a`, id `e2` → LONG `22`), LONG `2000ac`(`31008` `318d8`, id `112` → LONG `22`).
- [F] 고정 ROM 자료(live bus 읽기, 원본처럼 색인 검사 없음):
  - `31c84` WORD 표(`31078`, 색인 sext(2·`86.W`) → `8ebe` id). [F] 원본 앞 WORD는 `0376 0377 0004 0005 01d9 ffff fffc …`이다(끝은 정적으로 정해지지 않음; `86.W`는 `3106e`에서 부모 `86.W`를 복사한 값).
  - `31d3e` LONG 표(`310a2`, 색인 sext(4·(4·`94.B` + `86.W`)) → 애니메이션 목록 A1).
  - interpreter 표 진입 `31a2a`/`31a44`가 따라가는 A0 기록(interpreter 인자; live bus).
  - 주소만 넘기는 자료: 사각형 `31ad4`(`1aa7e`), 애니메이션 목록 `31e3a` `31f0c` `32084` `32f16` `32ec4`(`49f8c`), `4ae4a` 인자 `31c2a` `31c48`, LONG `76` 값 `31c92`(`30a10`), `2986` 자식 값 `30d6c`, `8ebe` 인자 WORD `1f4` `1d9`, `3af8` 인자 `1ac8` `1a59`.
- [F] work RAM:
  - 노드 A6: BYTE `14` `15` `1b` `5e` `5f` `61` `8c`(`ST`) `90` `94` `97` `98` `99` `9a` `a0`(`SCS`), (A6 + 0..ff)(`31a2a` 색인); WORD `1e` `20` `42` `54` `68` `76` `84` `86` `88` `8a` `90` `92` `9c` `9e`; LONG `(A6)`(설치) `c`(부모) `22` `36` `3a` `46` `56` `76`.
  - 부모 `c(A6)`: WORD `86`, BYTE `94`. `491c4` 반환 A0: BYTE `94`, WORD `1e` `84`, BYTE `90`. `ea680` 반환 A0: LONG `18`. `49be0` 반환 A0: WORD `0`. `d3d7c` 반환 A0(`30adc`..`30b30`): LONG `36` `3a`, WORD `54`. `28ae` 자식 A0(`31960`): LONG `76`, BYTE `7a`..`7e`.
  - A5 기준: `1aa3a`가 읽는 WORD `543c`(`3164a`의 C).
- [F] 상수 인자: `28ae` `D0.W` = `a`(A0 = `41fe6` `31008` `30dbe`); `2986` `D0.W` = `1e`, A0 = `30d6c`, A1 = `100bf4`; `49f8c` `D0.W` = `100`; `4ff96` `D0`/`D1` = 1/0; `49214` `D0`/`D1` = 0/`10`; `49290` `D0`/`D1` = 0/0; `4d81c` `D1` = 9; `4d418` `D2`/`D3` = 0/`18`; `443d2` `D0` = `60000`; `8ebe` `D1.B` = 0(`30dcc` `MOVEQ`) / 1.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256): `engine/src/animation_machine_objects_n29.cpp` `1d57937b0f481ebfada07969aa253fddb0902e35262802edff701a7439d2fadd`, `engine/tests/animation_machine_objects_n29_test.cpp` `494a59accae72c58e4d55d12b61b47e0a4d394cf37102f9f2183515768db9a96`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나(102 PC); `3c3af2bc…`), `engine/src/animation_machine_internal.h`(선언 하나; `2b04d296…`), `Makefile`(source 목록·test target·실행 줄; `9a154001…`), `tools/verify_animation_machine.py` SOURCES(`ac7efc78…`). `animation_machine_interpreter.cpp`와 다른 단위 실행부(N28 포함)는 바꾸지 않았다.
- [F] 실행부 case 집합 = scratch `starts.txt`(192, SHA256 `d4cbcff0…`). 내부 PC 744개는 모두 `unsupported animation objects n29 PC`, 소비 15 block은 Unknown C에서 `objects n29 caller requires known carry`(상태 보존)다.
- [F] `make -j4 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`). N29 test 출력: `animation machine objects n29: 420 fixtures (39 checked errors, 51 kept C), 192 blocks, 2351 calls`. N28 test(`423 fixtures … 151 blocks`)와 N20~N23 test는 그대로 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N29 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen29.py` Unicorn 생성(표 SHA256 `17ff42f2…`), `gen/assemble29.py` 조립): 420 fixture(성공 381, checked 오류 39), 192 시작 모두 Unicorn fixture로 덮음, block 표(192 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 15는 Unknown에서 거부), zero-step 192 × 3, 내부 PC 744 전수, 홀수 PC(범위 양끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`(8 fixture), 범위 옆 고정 ROM 자료 `31c84` `31c90` `31d3e` `31ad4`(routing 밖), 경계·다른 단위 진입 stop 47개(stop만; N28 `30fa0` 포함). 표 `30a76`: `30a6a`에서 `D0` = 0..9·`ffff0003`·`12340008`·`8000`·`10009`, `30a72` 직접 진입 `D0` = 0 1 8 9 `4000` `12344002`와 checked 오류 3개(`a` → `30aa2` 내부, `3fff` → `30a76` 내부, `1f00` → `3867a` routing 밖). "real" 행은 `1aa7e`(사각형 `31ad4`, 화면 안/밖 → `306fc`), `1aa3a`(WORD `543c(A5)` bit 3 → `31650` → `30dc2`), `288c`(부모 0 / `270e` / 그 밖 → `30dea` `30e3e` `31038`), `28ae`(자리 있음/없음 → `3195c` `3199a`)를 native로 따라가 실제 소비자 분기와 비교했다. 합성 물리 바이트(ROM 자료 아님): `31ad4..31adc`, `31c80..31c98`, `31d3e..31d8e`, bank LONG `200094` `2000ac`.
- [F] RTS 앞 생산 native 확인(실제 ROM 소비자를 복귀 LONG으로, Unicorn SR 미사용): `31650`(`D0` = 0 / `fff7`) → Clear(`30dc2` → `30dc6`), `31650`(`D0` = 8 / `ffff`) → `31658` Set(`30dc2` → `30ecc`); `31a08` → Set(`30efa` → `30f08`); `31a04`(선언 C Clear/Set) → `31a10` → `30efa` → `30efe`/`30f08`(FLOW 통과). 계약과 같다.
- [F] 돌연변이 검사(scratch `mut/mut29.py`, 실행부 한 곳씩 26개: 소비 분기 뒤바꿈 2(`306fc` `30dc2`), 부호 있는 `BGT`/`BLE` 2, `ASR.L` 부호 채움, `30a30` shift 수, `30a72` 색인 배수, slot `30a7a` 대상, `31650` Clear, `31a08` ORI 누락, `SCS` 값, BYTE push 크기, `309a4` pop 대상, `LSL.B` 수, `31078` 색인 배수, `310a2` 더하기 순서, `31a2a` 24 bit 마스크, `3104c` 비교, 타이머 감소, `31042` bit, `3310c` 분기, `30902` bit, bank LONG 주소, `3091c` 마스크, `31960` BYTE `7d`, `31a1a` pop 값): 26/26을 test가 잡았다(`mut/mut.log`).
- [F] 실제 ROM 차분(scratch `realrom/real29.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM, 실제 ROM 표 `31c84` `31d3e`·사각형 `31ad4`·bank LONG `200094` `2000ac`; native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC·N28 `30fa0`(점프로 들어올 때만)·interpreter `49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 190/192/191(합집합 192). 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `306fc` 44 `3070a` 55 `309e4` 4 `30dc2` 46 `30dea` 81 `30e3e` 7 `30ec0` 8 `31038` 83 `3195c` 77 `3199a` 103. interpreter 따라가기(`FOLLOW_ANIM`) 2 × 1,000 case 불일치 0. 의도한 차이: `2986` 실패 경로 caller-X 제한(`cue wrapper failure requires known caller X`, 결정 7) 4/4/3/1/3건(모두 `30b30`). native 홀수 주소·Unknown C 진입 소비 거부 0. clean stop이 없는 native case는 건너뜀(seed별 73/85/77; 주로 `306f0`·`318d8`의 interpreter/`4be82` 경로). 하네스 보정: sprite `16ed2` 내부 분기 PC(`16ede` `16ee4` `16ee8` `16eee`)는 실행부 내부로 보고 멈추지 않는다.
- [F] 결정 3 patch 확인(scratch `patch/n28-30fa0.diff` SHA256 `8ad76321…`를 작업 트리 사본 `patch/tree`에 적용, `realrom/batch_patch`): `30fa0`를 stop에서 빼고(`NO30FA0`) 1,500 case(seed 21) 불일치 0. 같은 seed를 patch 없는 실행부로 돌리면 400 case 중 13건이 `unsupported animation objects n28 PC`(모두 `30abc` → `30fa0` 경로)로 갈린다. [U] patch를 넣으면 N28 test(block 151 → 152, 내부 722 → 721, block 표 `30f9c` 후속)를 다시 생성해야 한다(이 작업에서는 하지 않음).
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `d798961` 일치 pass 14,408·node 122,462, 불일치 0 → N29a 뒤 같음(`diff_results.json` SHA256 `a6c41695…` 기준과 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` SHA256 `cdffa22c…`) → N29a 뒤 같은 수치·불일치 0(`95c4025a…`; 차이는 기록된 `animation_machine.cpp` 원본 SHA(seed 32 33 116 117의 `current_router_sha256` 포함)와 새 원본 목록뿐). **새 완주 seed 없음**(재범위 예상과 같음), 잃은 seed 0. seed 116 117은 그대로 frame 0 `38ba0`(N31)에서 멈춘다.
- [U] 남은 미확인: N29a 범위의 자연 frame pass 비교는 116 117이 `38ba0`에서 먼저 멈춰 아직 없다(실제 ROM 차분·fixture로만 덮음). 경계 `ea680`·`4d418`·`49c38`의 C 생산(소비 `30dfa` `30e52` `31a04` `31676`)은 그 단위가 정한다. 결정 1의 N29b(`30b6c..30d6c`)와 결정 2의 `3169c` `319b6` `307da..308e2`는 routing하지 않았다. 결정 3 patch는 적용하지 않았다.
