# 객체 callback F4 N28: stage event callback `2b8a0`/`2b8a6`(설치 `2b96c` `2b99c`, `2c7fe`/`2c838`, `2ca68`), 방향 helper `2b418`, `4da50` 자식 생성 `2b668`과 code pointer `2b692`, `2c760`, stage event callback `306a8`(설치 `30718` `3075a`)과 꼬리 `30f84` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N28 행(150 block, `2b418..2b532` `2b668..2b6c4` `2b7ce..2ba50` `2c760..2c8f2` `2ca68..2cb30` `306a8..307da` `30ed2..31002`, callback `2b8a6` `2b96c` `2b99c` `306a8` `30718` `3075a`, 경계 callee 17, bank 1, 새 seed 없음; seed 116 117 사슬 N28→N35의 시작, 그 seed는 `38ba0`(N31)에서 멈춤)이다. 단위 형식과 규약은 N23 계약(`animation-machine-objects-n23-contract.md`, SHA256 `ad189087b33086de823cebdade045281fe057ebb7b8beb45ec0b51920d06e40b`)을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 분기를 각 선행에 접어 넣음). N28에는 block 경계를 건너는 N/Z/V 읽기가 없다(결정 4).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다. 범위 밖 코드만 부르는 범위 안 helper는 routing하지 않는다(N22/N23 선례).
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- `animation_machine_interpreter.cpp`와 다른 단위 실행부는 고치지 않는다(N28에는 기존 실행부의 두 번째 진입이 필요 없다). DIV 0 제수는 단위 checked 오류(N28에는 DIV가 없다).
- 계산 점프 표는 정적으로 묶고 전부 전사한다(N28에는 PC 상대 BRA.W 점프 표가 없다). LONG 포인터 표 + `JMP (An)`은 live bus 읽기 + live target(N28에는 레지스터 간접 제어 이동이 없다).
- ~220 block을 넘으면 나눈다(N28은 151 block이라 나누지 않는다).
- N24(`5deec..5e8c8`)가 동시에 진행된다. N28 routing 범위는 N24와 겹치지 않는다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치, 범위 밖에서 참조하는 범위 안 진입, LEA로 넘기는 code pointer)로 정한다. Unicorn TB 분할은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N23 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDI`/`ADDQ`/`SUB`/`SUBQ`/`AND`/`ANDI`/`OR`/`NEG`/`NOT`/`ASR`/`LSR`/`CLR` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`BSET`/`BCLR`/`ST`/`SNE`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `ORI`/`ANDI` CCR은 known Set/Clear 생산이다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N28 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`20009c`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n28`(HEAD `0da8cec` = N23까지 통합, `engine/src/animation_machine.cpp` SHA256 `4635c41ba8aa782891ec41a22f6e332c9bb6c11507e76761672d2b859750efc3`, routing 규칙 80개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`)을 참조했다. N28 routing 12 범위의 짝수 PC는 기존 routing에 없고, 범위 양끝 이웃(`2b416` `2b532` `2b666` `2b6c4` `2b7cc` `2b8ae` `2b8b4` `2b8fc` `2b96a` `2ba50` `2c75e` `2c7a6` `2c7fc` `2c8f2` `2ca66` `2cb30` `306a6` `306b4` `30716` `307da` `30ed0` `30ed6` `30f82` `31002`)도 routing 밖이다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n28/n28.py`(정적 디코드, `starts.txt` SHA256 `cb86f81e79f9fa4b60bf7f638f4cc5bfccb7e11123d305de842e368f0292897e`)와 `cls28.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N28 = 151 block**(12 routing 범위, 코드 1,746바이트, 짝수 PC 873, 내부 722). 진입 10개(`2b8a0` `2b8a6` `2b96c` `2b99c` `306a8` `30718` `3075a` `2b692` `2c7fe` `2ca68`)에서 분기·fall-through·범위 안 설치를 끝까지 따라간 정적 closure다. 재범위 150은 400 frame 안에 실행되는 함수 본문 span(동적 TB 소유 포함)이고, 차이는 결정 1이다.
- [F] 진입:
  - stage event callback(고정 ROM LONG 표 `e8cc0..e8cdc`의 `e8cc4` = `2b8a6`, `e8ccc` = `2b8a0`, `e8cd4` = `306a8`). `2b8a0`은 `BSET.B #0,15(A6)` 뒤 `2b8a6`으로 fall-through한다. 같은 표의 `2b7be` `2b7b8`(형제 callback, 함수 `2b6e6`)과 `3310c`(N29) `304ea` `3fefc`는 범위 밖이다.
  - 범위 안 설치: `2b96c`(`2b8f4`; 범위 밖 `2c638`도 설치), `2b99c`(`2b996`, fall-through), `2c838`(`2c832`, fall-through), `2ca68`(`2c8c0`; 범위 밖 `2c68a` 설치·`2ca60 BRA`), `30718`(`306ac`; 범위 밖 `304f6` `30710` `30efe`), `3075a`(`30754`, fall-through).
  - 범위 밖에서 들어오는 범위 안 진입: `2c7fe`(범위 밖 `2c456 MOVE.L #2c7fe,(A6)`; 범위 안 `2b9a0 BEQ.W`), `2c8ca`(범위 밖 `2c6c8` `2ca64` `2cc5a` `2cca0` `2ccc4` `2d29c BRA.W`; 범위 안 `2ba4c` `2c8c6`), `2b418`(범위 밖 `2ba8a` `2bac4` `2bb76` 등 `JSR`/`BSR`), `2b668`(범위 밖 `2ce5a BSR`), `2b8b6`(범위 밖 형제 `2b7c2 BRA.W`), `2c760`(범위 밖 `2c9f2 BSR`), `30ed2`(범위 밖 `30614` `30646` `30714 BRA.W`).
  - code pointer: `2b692`(`2b688 LEA 2b692(PC),A0; JMP 4da50` → N23 `4da66`이 자식 LONG `7a`에 저장 → N23 `4dbb0 JSR (A1)`).
  - 범위 안 내부 callee: `2b7ce`(`2b8a6 BSR`), `2b418`(`2b9be` `2c8b4`), `2b668`(`2b992`), `2c760`(`2b9ba` `2c8b0`).
- [F] **경계(실행부 없음, 현재 routing 밖) callee 15개**: `2b63e`(`2ba18` `2c89a BSR`; C 반환), `2c71a`(`2c8a8 BSR`), `3165e`(`30774`), `316b2`(`3075a`), `318b8`(`30fd6`), `318d8`(`306a8`), `319f6`(`3078c`; C 반환), `4c37c`(`2b8d6`), `4c3a2`(`2c79a`), `4c3de`(`2c76e`), `4d4b4`(`2c894` `2ca8a`), `4db18`(`2c826`), `4ff96`(`2ca94`), `8d34`(`2c860`), `d3d7c`(`2ca9a` `2cab6` `2cad2` `2caee`). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **다른 실행부로 가는 callee**: `28ae` `2a00`(fade_card), `2986`(buffer_cue), `3af8`(sound), `8ebe`(U02), `1aa7e` `48296` `4b54e`(U01), `496c2`(U11), `49be0`(U06), `4c0ac`(U12), `49c66`(input), `49f8c` `49fc6`(interpreter; `2b52c JMP 49fc6`), `49214`(N05), `4ae4a`(N08), `4d81c`(stage_area), `4d2d4` `4d508` `4d766` `4da4a` `4da50`(N23; `2b68c JMP 4da50`). 레지스터 간접 제어 이동은 없다.
- [F] **범위 밖 설치·자식 값(실행 PC가 아님)**: 설치 `2ba50`(`2ba3e`), `307da`(`307ae`), `31002`(`3076e`), `30b6c`(`30f96`, N29 범위); `28ae` 자식 `41fe6`(`2b81e` `2b860`, N22); `2986` 자식 `2cb30`(`2caf4`); 자료 포인터 `2b3d0`(LONG `9e`), `2c7a6`(LONG `98`).
- [F] **carry**(아래 "carry" 절): 소비 block 10개(모두 FLOW), known 생산 3개(`ORI` Set 2, `ANDI` Clear 1), FLOW_ONLY 53개(소비 10 포함), Unknown 95개. 53 + 3 + 95 = 151.
- [F] N/Z 재계산·X·DIVx/MULx·PC 상대 점프 표·레지스터 간접 제어 이동·TRAP·I/O port 쓰기·bank 변경이 없다.
- [F] 스택: JSR/BSR 복귀 LONG, `2b9fa MOVE.W 42(A6),-(A7); MOVE.W 46(A6),-(A7)` / `2ba44 MOVE.W (A7)+,46(A6); MOVE.W (A7)+,42(A6)`(WORD, ±2).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen28.py`): RNG·base 두 기록 모두 seed 116 117만 N28 범위 PC 77개를 실행한다. callback 실행 수(seed 116 기준, 117 같음): `2b8a6` 1, `2b96c` 1, `2b99c` 80, `306a8` 1, `30718` 1, `3075a` 80, 그리고 N23 `4db8e`의 `JSR (A1)` = `2b692` 80. `2b8a0` `2c7fe..2c8c6` `2ca68..2cb2a` `2b85c..2b874` `2b9d0` `2ba14..2ba3e` `2c77a` `3076e` `30788..307d2` `30f96` `30fae` `30fc2` `30fd0` `30fda` `30ff6`은 자연 400 frame에서 실행되지 않는다.
- [F] 기준(`0da8cec`)에서 seed 116 117은 frame 0 `38ba0`(N31)에서 먼저 멈춘다. [I] N28만으로는 새 완주 seed가 없다(재범위 N28 행과 같음). 116 117은 N28 뒤에도 `38ba0`·`4c37c`(N33)·`4c3de`(N34)·`318d8`(N29) 등에서 멈춘다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 151 block(재범위 150과 차이).** [F] 재범위 N28 행은 실행 함수 본문 span이고 동적 TB를 가장 가까운 앞 진입에 귀속했다.
   - 넣은 것: `2b8a0`(stage event LONG `e8ccc`가 참조하는 범위 안 진입, 1 block, `2b8a6`으로 fall-through), `2b692`(LEA로 넘기는 code pointer, 4 block), `2c7fe..2c8f2`(`2b99c BEQ`·범위 밖 설치 `2c456`; 자료 `2c7a6..2c7fe` 제외), `2ca68..2cb30`(`2b9a4 BNE`). 뒤 두 묶음은 자연 400 frame에서 실행되지 않지만 N28 진입에서 정적으로 닿는다.
   - 뺀 것(routing하지 않음):
     - 미참조 `2b8ae`(`BSR 2b7ce; BRA 2b8fc`, 참조 0).
     - 범위 밖에서만 들어오는 `2b8fc..2b96c`(7 block: `2b8fc` `2b916` `2b926` `2b92a` `2b930` `2b93e` `2b964`). 참조는 범위 밖 형제 callback `2b7c6`(고정 ROM LONG `1d46c`)의 `2b7ca BRA.W 2b8fc`와 미참조 `2b8b2`뿐이다. 설치 `2baf4`(범위 밖)를 쓴다.
     - 범위 밖에서만 들어오는 공유 꼬리 `30ed6..30f84`(18 block). 참조는 범위 밖 `305ae` `30610` `30834` `30866` `308de` `3093e` `309b0` `309ee`(N29 `308e2..30cb8` 등)의 `BRA.W`/`BPL.W`뿐이고 N28 `30ed2`는 `BRA.W 30f84`로 건너뛴다. 재범위 N28 행에는 동적 TB 소유 규칙으로 들어 있었다. **권고: N29가 `30ed6..30f84`를 넣는다**(N22/N23 결정 1 선례).
     - N29 행과 겹치는 `306b4..30718`(N29 진입 `306b4`). N28 `306a8`은 `306a8..306b4`만이다.
     - 범위 안 자료 `2c7a6..2c7fe`(LONG `98` 목록, `ffff fff4` 되감기 WORD 포함)와 `2b6c4` 뒤 자료(`2b6ce` `2b6d6` 사각형).
   - 둘을 넣으면 176 block이다. 뺀 부분은 자연 400 frame에서 실행되지 않는다(`seen28.py`).
2. **경계 callee 15개의 소속.** [F] `2b63e`(`2b532..2b668` 사이, `JMP 4d418`로 끝남), `2c71a`, `318b8`은 어느 N 단위 범위에도 없다. `3165e` `316b2` `318d8` `319f6`은 N29 범위(`3164a..316c2` `318d8..31a54`), `4c37c`는 N33, `4c3de`는 N34 범위다. `4c3a2` `4d4b4` `4ff96` `8d34` `d3d7c`은 범위 밖이다. `4db18`은 N23 결정 1이 "N28~N33에서 함께 정한다"고 남긴 helper(`28ae` 자식 `4dbdc` 생성)다. N28 진입에서 `2c826 JSR 4db18`로 닿지만 자연 400 frame에서 실행되지 않으므로 **권고: 경계로 둔다**(넣으면 4 block + 자식 `4dbdc` 사슬이 따라온다). [F] 자연 경로(116 117)가 실제로 부르는 경계는 `4c37c`(`2b8c4`) `4c3de`(`2c76e`) `318d8`(`306a8`) `316b2`(`3075a`) `3165e`(`30774`)다. `2b63e` `319f6` `2c71a` `318b8` `4c3a2` `4d4b4` `4db18` `4ff96` `8d34` `d3d7c`은 자연 400 frame에서 불리지 않는다(`4d2d4`가 Clear를 돌려 `2ba10`/`30784`가 `2ba44`/`307d6`으로 간다).
3. **known C 생산과 실제 소비자.** [F] `2b6b6 ANDI.B #fe,CCR; RTS`(Clear) → N23 `4dbb2 BCS.W 4dbd6`(code pointer `2b692`의 호출자 `4dbb0 JSR (A1)`). `2b832` `2b874 ORI.B #1,CCR`(Set; `2b85c BRA` → `2b89e RTS`) → ROM 안 소비자 없음(`2b7ce` 호출자 `2b8a6`의 복귀점 `2b8aa BRA.W 2b8b6` 뒤 `TST.W`, 범위 밖 `2b8ae`도 `BRA`), `ORI` 관례로 known. [F] 세 생산은 실제 ROM 소비자 `4dbb2`를 복귀 LONG으로 두고 native 분기로 C를 확인했다(검증 기록). `2b7ce`의 `28ae` Clear 경로(`2b82e`/`2b870 BCC` → `2b85c`/`2b89e`)는 FLOW로 Clear를 그대로 돌려준다.
4. **flag 재계산 없음.** [F] 진입에서 flag를 읽는 block은 소비 10개뿐이고 모두 callee가 RTS로 돌려준 C(`28ae` `1aa7e` `4d2d4` `2b63e` `319f6` `4d766`)를 읽는다. 나머지 비교·`TST`·`BTST`·산술과 그 Bcc/`Scc`는 같은 block 안에 있다(`2b468 ASR.W; BMI`, `2b46e SUBQ.W; BCS`, `2b4a0..2b4d6 CMPI.W; BGE/BGT`(부호 있음), `2b4f8 CMPI.W; SEQ` 다섯 번, `2c838 CMPA.W #0,A0; BEQ`, `2c8b8 SUBQ.W; BPL`, `30f8a BTST; SNE; BEQ`).
5. **경계 callee C 소비 3곳.** [F] `2ba1c BCC.W`·`2c89e BCS.W`는 `2b63e`(→ `JMP 4d418`)의 C, `30790 BCC.W`는 `319f6`의 C를 읽는다. 두 callee는 실행부가 없으므로 N28 안에서는 typed fixture(진입 C 선언)로만 실행하고, Unknown C면 `objects n28 caller requires known carry`다. [U] 두 callee의 C 생산은 해당 단위가 정한다.
6. **`2986` caller-X 제한 유지.** [F] `2caf4`가 `JSR 2986`(buffer_cue, A0 = `2cb30`, `D0.W` = `1e`, A1 = `100bf4`)을 부른다. 실패 경로는 buffer_cue 결정 1 선택 A대로 `cue wrapper failure requires known caller X` checked 오류다. N28은 고치지 않는다(자연 400 frame에서 실행되지 않음).
7. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n28.cpp`의 `animation_objects_n28_block`. 오류는 `unsupported animation objects n28 PC`(내부 PC), `objects n28 caller requires known carry`(소비 10 block). 메인 지시와 같다.
8. **무효화 탐침 없음.** [F] `engine/tests`·`engine/src`·`tools/*.py`의 16진 토큰 중 N28 routing 범위 짝수 PC와 같은 것은 자료 추출 도구의 ROM 주소(`tools/pack_palettes.py` `2b7e4` `2b7f2` `2b800`, `tools/analyze_branch_object_setup.py` `2b7ce` `2b80e`, `tools/pack_animation_branch.py` `2b7ce`, `tools/observe_animation_machine_scene_core.py`의 검색 끝 `31000`)와 N04 test의 레지스터 값 `2ca78`뿐이다. routing 탐침이나 rollback 기대로 쓰는 곳은 없다.

## 원본 바이트 근거

[F] N28 코드 12 범위 합계 1,746바이트(짝수 PC 873개, 시작 151, 내부 722). 범위 순서로 이어 붙인 SHA256 `1fd3bf81cfaf5ea49dad71e579a727634a67e1e70fc898c36b6d3c5a7c29a03e`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `2b418..2b532` | 282 | `15c7adb1e9903a034034df06e2a159cfa87f699321b1d1e33d7533a0be8e8ed2` | 26 |
| `2b668..2b6c4` | 92 | `31c0813491d4e4622817b926183865f9633b912b25911207a3a5ea3e0cf93fe6` | 6 |
| `2b7ce..2b8ae` | 224 | `e4286ed06917eec8656ed4a34d85b0f9540f419cba0716d88e463ddb47dc6e78` | 15 |
| `2b8b6..2b8fc` | 70 | `e364435f05b7e794687ea1e90968cce3f8f378734fb6906b8316d7931b96839b` | 5 |
| `2b96c..2ba50` | 228 | `99e4e58e9c0ce5148b160cc23cf1c2894d23519c6ebe2f37a27929df3e3597b4` | 19 |
| `2c760..2c7a6` | 70 | `53c9d65112dc58a4252c1006c1460a536a30931161e63a1cc0b15f56850adf51` | 5 |
| `2c7fe..2c8f2` | 244 | `a663bc3bd4ba24bf9cc6b1e59c0b1e5fef183c681e5e7eae0dba036caf65b312` | 27 |
| `2ca68..2cb30` | 200 | `ee48f051f3304680c2765dd6464afcb9f2539da4dcac9c496dc7985fc768b6be` | 11 |
| `306a8..306b4` | 12 | `592bebd1cbe9bb62ec4741e069a1d1664bd4678de3d0bf8c486e6018404b89e4` | 2 |
| `30718..307da` | 194 | `e54f18ce6f96a17f3300f152d6c933b8dd3b18b6bbf7f5016ae65d7a9e50a630` | 20 |
| `30ed2..30ed6` | 4 | `13304458ad071da9bd4afcd66531086a23f12ac8a93cca585681f5d231206bb7` | 1 |
| `30f84..31002` | 126 | `58acb273032ef791d52331b0dbe9fa775f6d7646027e0b706011eaa4383bd8e8` | 14 |

- [F] 범위 이웃: `2b418` 앞 `..2b418`(LONG 표 `2b2ec` `2b330` `2b374`, 자료 `2b3d0`), `2b532..2b668`(함수 `2b532` `2b608`, 경계 `2b63e`), `2b6c4..2b6e6`(자료 `2b6c4`, 사각형 `2b6ce` `2b6d6`), `2b6e6..2b7ce`(형제 설정 함수 `2b6e6`, 형제 callback `2b7b8`/`2b7be`/`2b7c6`), `2b8ae..2b8b6`(미참조), `2b8fc..2b96c`(범위 밖에서만), `2ba50..2c71a`(설치 `2ba50`, 다른 함수 `2ba86..`), `2c71a..2c760`(경계 `2c71a`), `2c7a6..2c7fe`(자료), `2c8f2..2ca68`(자료 `2c8f2..2c94c`, 함수 `2c94c..`), `2cb30..`(`2986` 자식 값), `306a8` 앞 `..306a8`(다른 함수), `306b4..30718`(N29 `306b4`), `307da..30ed2`(N29 범위의 설치 `307da`·`308e2..`), `30ed6..30f84`(결정 1), `31002..`(설치 `31002`, N29 `30dbe..310de`).
- [F] 우연 일치(실행 진입 아님): 고정 ROM에 `0002b800`(`2475c` 등 12곳), `0002c800`(`2474c` 등 12곳), `00031000`(`244aa` 등 12곳)인 LONG과 명령 바이트 안의 `0002b42c`(`1ca5e` `1ce1c`), `00030744`(`f35aa`)가 있다. `2b800` `2c800` `31000` `2b42c` `30744`는 명령 중간이거나 수치 상수다([I]).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "Set/Clear 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)·d16(A5)·`(An,Dn.W)`는 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`는 LONG 전체). 모든 비교·`TST`·산술과 그 Bcc는 같은 block 안에 있다(결정 4).

**`2b418`(내부 `2b9be JSR`·`2c8b4 BSR`, 범위 밖 `2ba8a` `2bac4` 등 11곳; 표 `2b374`/`2b2ec`/`2b330` → LONG `56`, 방향 BYTE `7c` `7d` `7e`; 끝 `JMP 49fc6`) 26**
- `2b418`: `BTST.B #7, 15(a6); BNE.W 2b42a` (→`2b422`) — FLOW
- `2b422`: `LEA.L 2b374(pc), a0; BRA.W 2b440` — FLOW
- `2b42a`: `CMPI.B #1, 7f(a6); BCC.W 2b43c` (→`2b434`)
- `2b434`: `LEA.L 2b2ec(pc), a0; BRA.W 2b440` — FLOW
- `2b43c`: `LEA.L 2b330(pc), a0` (→`2b440`) — FLOW
- `2b440`: `MOVEQ #0, d0; MOVE.B 7c(a6), d0; ADD.W d0, d0; ADD.W d0, d0; MOVE.L (a0, d0.w), 56(a6); TST.L 36(a6); SNE.B 80(a6); MOVE.W 8c(a6), d0; BTST.B #0, 15(a6); BEQ.W 2b468` (→`2b466`)
- `2b466`: `NEG.W d0` (→`2b468`)
- `2b468`: `ASR.W #5, d0; BMI.W 2b47e` (→`2b46e`)
- `2b46e`: `SUBQ.W #1, d0; BCS.W 2b478` (→`2b474`)
- `2b474`: `ANDI.W #ff, d0` (→`2b478`)
- `2b478`: `ADDQ.W #1, d0; BRA.W 2b486`
- `2b47e`: `NOT.W d0; ANDI.W #e0, d0; NOT.W d0` (→`2b486`)
- `2b486`: `ADDI.W #100, d0; LSR.W #5, d0; MOVE.B d0, 7c(a6); MOVE.W 8c(a6), d1; BTST.B #0, 15(a6); BEQ.W 2b4a0` (→`2b49e`)
- `2b49e`: `NEG.W d1` (→`2b4a0`)
- `2b4a0`: `CMPI.W #eb00, d1; BGE.W 2b4b2` (→`2b4a8`)
- `2b4a8`: `MOVE.B #0, 7d(a6); BRA.W 2b4ee`
- `2b4b2`: `CMPI.W #fb00, d1; BGE.W 2b4c4` (→`2b4ba`)
- `2b4ba`: `MOVE.B #1, 7d(a6); BRA.W 2b4ee`
- `2b4c4`: `CMPI.W #500, d1; BGT.W 2b4d6` (→`2b4cc`)
- `2b4cc`: `MOVE.B #2, 7d(a6); BRA.W 2b4ee`
- `2b4d6`: `CMPI.W #1500, d1; BGT.W 2b4e8` (→`2b4de`)
- `2b4de`: `MOVE.B #3, 7d(a6); BRA.W 2b4ee`
- `2b4e8`: `MOVE.B #4, 7d(a6)` (→`2b4ee`)
- `2b4ee`: `TST.W d1; BPL.W 2b4f8` (→`2b4f4`)
- `2b4f4`: `ADDI.W #1ff, d1` (→`2b4f8`)
- `2b4f8`: `ASR.W #1, d1; ANDI.W #ff00, d1; MOVEQ #0, d7; CMPI.W #1000, d1; SEQ.B d0; OR.B d0, d7; CMPI.W #500, d1; SEQ.B d0; OR.B d0, d7; CMPI.W #0, d1; SEQ.B d0; OR.B d0, d7; CMPI.W #fb00, d1; SEQ.B d0; OR.B d0, d7; CMPI.W #f000, d1; SEQ.B d0; OR.B d0, d7; MOVE.B d7, 7e(a6); JMP 49fc6.l`

**`2b668`(`2b992 BSR`·범위 밖 `2ce5a`; `28ae` 자식 `4db42` 생성 `JMP 4da50`, code pointer `2b692`) / `2b692`(`4dbb0 JSR (A1)` live target, `ANDI` Clear) 6**
- `2b668`: `MOVEQ #0, d1; MOVE.B 7c(a6), d1; ADD.W d1, d1; ADD.W d1, d1; LEA.L 2d8b8(pc), a4; ADDA.W d1, a4; MOVE.W (a4)+, d0; MOVE.W (a4)+, d1; BTST.B #0, 15(a6); BEQ.W 2b688` (→`2b686`)
- `2b686`: `NEG.W d0` (→`2b688`)
- `2b688`: `LEA.L 2b692(pc), a0; JMP 4da50.l` — FLOW
- `2b692`: `MOVEA.L c(a6), a0; MOVEQ #0, d1; MOVE.B 7c(a0), d1; ADD.W d1, d1; ADD.W d1, d1; LEA.L 2d8b8(pc), a4; ADDA.W d1, a4; MOVE.W (a4)+, d0; MOVE.W (a4)+, d1; BTST.B #0, 15(a0); BEQ.W 2b6b6` (→`2b6b4`)
- `2b6b4`: `NEG.W d0` (→`2b6b6`)
- `2b6b6`: `MOVE.W d0, 2e(a6); MOVE.W d1, 32(a6); ANDI.B #fe, ccr; RTS` — Clear 생산

**`2b7ce`(`2b8a6 BSR`; bank LONG `20009c`, `8ebe` 세 번, `28ae` 자식 `41fe6`) / stage event callback `2b8a0`(LONG `e8ccc`)·`2b8a6`(LONG `e8cc4`) 15**
- `2b7ce`: `MOVE.W #f2, 20(a6); MOVE.L 20009c.l, 22(a6); MOVE.L #2b3d0, 9e(a6); MOVE.W #87d, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `2b7f2`: `MOVE.W #39d, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `2b800`: `MOVE.W #87a, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `2b80e`: `MOVE.W #8080, 8e(a6); BTST.B #0, 15(a6); BNE.W 2b860` (→`2b81e`)
- `2b81e`: `MOVEA.L #41fe6, a0; MOVE.W #a, d0; JSR 28ae.l`
- `2b82e`: `BCC.W 2b85c` (→`2b832`) — C 소비, FLOW
- `2b832`: `LEA.L 8e(a6), a1; MOVE.L a1, 76(a0); MOVE.B #6, 7a(a0); MOVE.B #0, 7b(a0); MOVE.B #0, 7c(a0); MOVE.B #0, 7d(a0); MOVE.B #0, 7e(a0); ORI.B #1, ccr` (→`2b85c`) — Set 생산
- `2b85c`: `BRA.W 2b89e` — FLOW
- `2b860`: `MOVEA.L #41fe6, a0; MOVE.W #a, d0; JSR 28ae.l`
- `2b870`: `BCC.W 2b89e` (→`2b874`) — C 소비, FLOW
- `2b874`: `LEA.L 8e(a6), a1; MOVE.L a1, 76(a0); MOVE.B #6, 7a(a0); MOVE.B #0, 7b(a0); MOVE.B #0, 7c(a0); MOVE.B #0, 7d(a0); MOVE.B #4, 7e(a0); ORI.B #1, ccr` (→`2b89e`) — Set 생산
- `2b89e`: `RTS` — FLOW
- `2b8a0`: `BSET.B #0, 15(a6)` (→`2b8a6`) — FLOW
- `2b8a6`: `BSR.W 2b7ce` — FLOW
- `2b8aa`: `BRA.W 2b8b6` — FLOW

**`2b8b6`(`2b8aa BRA`·범위 밖 `2b7c2 BRA`; 설치 `2b96c`) 5**
- `2b8b6`: `TST.W 76(a6); BNE.W 2b8c4` (→`2b8be`)
- `2b8be`: `JSR 4c0ac.l` — FLOW
- `2b8c4`: `MOVE.W #8810, 68(a6); MOVE.W #8810, 1e(a6); MOVE.W #0, 8c(a6); JSR 4c37c.l`
- `2b8dc`: `MOVE.L a0, 94(a6); MOVEQ #1, d1; JSR 4d81c.l`
- `2b8e8`: `MOVE.B d1, 83(a6); MOVE.B d2, 84(a6); MOVE.W d3, 54(a6); MOVE.L #2b96c, (a6); RTS`

**설치 callback `2b96c`(`2b8f4`·범위 밖 `2c638`) / `2b99c`(`2b996` 설치, fall-through) 19**
- `2b96c`: `MOVE.B 1b(a6), 14(a6); MOVE.L #0, 98(a6); MOVEA.L #645da, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `2b98a`: `MOVE.L #0, 64(a6); BSR.W 2b668`
- `2b996`: `MOVE.L #2b99c, (a6)` (→`2b99c`)
- `2b99c`: `TST.W 54(a6); BEQ.W 2c7fe` (→`2b9a4`)
- `2b9a4`: `BTST.B #7, 61(a6); BNE.W 2ca68` (→`2b9ae`) — FLOW
- `2b9ae`: `MOVE.B #0, 5e(a6); MOVE.B #8, 86(a6); BSR.W 2c760`
- `2b9be`: `JSR 2b418(pc)` — FLOW
- `2b9c2`: `LEA.L 2b6ce(pc), a0; JSR 1aa7e.l` — FLOW
- `2b9cc`: `BCC.W 2b9d6` (→`2b9d0`) — C 소비, FLOW
- `2b9d0`: `JMP 2a00.l` — FLOW
- `2b9d6`: `LEA.L 2b6d6(pc), a0; MOVEQ #0, d0; MOVE.B 7c(a6), d0; ADD.W d0, d0; ADD.W d0, d0; LEA.L 2d8b8(pc), a4; ADDA.W d0, a4; MOVE.W (a4)+, d0; MOVE.W (a4)+, d1; BTST.B #0, 15(a6); BEQ.W 2b9fa` (→`2b9f8`)
- `2b9f8`: `NEG.W d0` (→`2b9fa`)
- `2b9fa`: `MOVE.W 42(a6), -(a7); MOVE.W 46(a6), -(a7); ADD.W d0, 42(a6); ADD.W d1, 46(a6); JSR 4d2d4.l`
- `2ba10`: `BCC.W 2ba44` (→`2ba14`) — C 소비, FLOW
- `2ba14`: `MOVE.W d0, 88(a6); BSR.W 2b63e`
- `2ba1c`: `BCC.W 2ba44` (→`2ba20`) — C 소비, FLOW
- `2ba20`: `MOVE.W d0, 8a(a6); MOVE.W 88(a6), d0; MOVE.B #1, d1; MOVE.B 83(a6), d2; MOVE.B 84(a6), d3; MOVE.W 54(a6), d4; JSR 4d508.l`
- `2ba3e`: `MOVE.L #2ba50, (a6)` (→`2ba44`)
- `2ba44`: `MOVE.W (a7)+, 46(a6); MOVE.W (a7)+, 42(a6); BRA.W 2c8ca`

**`2c760`(`2b9ba` `2c8b0 BSR`·범위 밖 `2c9f2`) 5**
- `2c760`: `MOVEA.L 94(a6), a0; BTST.B #7, 15(a6); BEQ.W 2c77a` (→`2c76e`) — FLOW
- `2c76e`: `JSR 4c3de.l` — FLOW
- `2c774`: `MOVE.W d0, 8c(a6); RTS`
- `2c77a`: `MOVE.L 64(a6), 36(a6); MOVEA.L 9e(a6), a4; MOVE.L 10(a4), d0; SUB.L 3a(a6), d0; MOVEA.L 9e(a6), a4; MOVE.W 6(a4), d1; ASR.L d1, d0; ADD.L d0, 3a(a6); JSR 4c3a2.l`
- `2c7a0`: `MOVE.W d0, 8c(a6); RTS`

**`2c7fe`(`2b9a0 BEQ`·범위 밖 설치 `2c456`; 설치 `2c838`) / 공유 꼬리 `2c8ca`(`2ba4c`·범위 밖 `2c6c8` `2ca64` `2cc5a` 등) 27**
- `2c7fe`: `MOVE.W #1ac8, d0; JSR 3af8.l`
- `2c808`: `MOVEA.L #65f56, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `2c818`: `MOVE.L #2c7a6, 98(a6); MOVEQ #0, d0; MOVE.W #38, d1; JSR 4db18.l`
- `2c82c`: `MOVE.W #60, 92(a6); MOVE.L #2c838, (a6)` (→`2c838`)
- `2c838`: `MOVEA.L 98(a6), a0; CMPA.W #0, a0; BEQ.W 2c866` (→`2c844`)
- `2c844`: `MOVE.B 1a(a6), 14(a6); MOVE.W (a0)+, d1; CMPI.W #ffff, d1; BNE.W 2c858` (→`2c854`)
- `2c854`: `ADDA.W (a0), a0; MOVE.W (a0)+, d1` (→`2c858`)
- `2c858`: `MOVE.L a0, 98(a6); MOVE.B 14(a6), d0; JSR 8d34.l`
- `2c866`: `CLR.L 64(a6); MOVE.B #ff, 86(a6); MOVE.W 88(a6), d0; BMI.W 2c8b0` (→`2c878`)
- `2c878`: `MOVE.W 88(a6), d0; JSR 49be0.l`
- `2c882`: `MOVE.W (a0), d0; BTST.B #5, d0; BEQ.W 2c89a` (→`2c88c`)
- `2c88c`: `MOVE.B #1, d1; MOVE.W 88(a6), d0; JSR 4d4b4.l`
- `2c89a`: `BSR.W 2b63e` — FLOW
- `2c89e`: `BCS.W 2c8a8` (→`2c8a2`) — C 소비, FLOW
- `2c8a2`: `MOVE.W #ffff, 88(a6)` (→`2c8a8`)
- `2c8a8`: `BSR.W 2c71a` — FLOW
- `2c8ac`: `BRA.W 2c8b4` — FLOW
- `2c8b0`: `BSR.W 2c760` — FLOW
- `2c8b4`: `BSR.W 2b418` — FLOW
- `2c8b8`: `SUBQ.W #1, 92(a6); BPL.W 2c8c6` (→`2c8c0`)
- `2c8c0`: `MOVE.L #2ca68, (a6)` (→`2c8c6`)
- `2c8c6`: `BRA.W 2c8ca` — FLOW
- `2c8ca`: `CMPI.W #8000, 8e(a6); BEQ.W 2c8f0` (→`2c8d4`)
- `2c8d4`: `MOVEA.L 78(a6), a0; MOVE.B (a0)+, d0; MOVE.B (a0)+, d1; BTST.B #0, 15(a6); BEQ.W 2c8e8` (→`2c8e6`)
- `2c8e6`: `NEG.B d0` (→`2c8e8`)
- `2c8e8`: `MOVE.B d0, 8e(a6); MOVE.B d1, 8f(a6)` (→`2c8f0`)
- `2c8f0`: `RTS` — FLOW

**`2ca68`(`2b9aa BNE`·`2c8c0` 설치·범위 밖 `2c68a` 설치·`2ca60 BRA`; 끝 `JMP 2a00`) 11**
- `2ca68`: `MOVE.W #18de, d0; JSR 3af8.l`
- `2ca72`: `LEA.L 2c94c(pc), a0; JSR 4ae4a.l` — FLOW
- `2ca7c`: `MOVE.B #0, d1; MOVE.W 88(a6), d0; MOVE.B #7, 5e(a6); JSR 4d4b4.l`
- `2ca90`: `MOVEQ #1, d0; MOVEQ #0, d1; JSR 4ff96.l`
- `2ca9a`: `JSR d3d7c.l` — FLOW
- `2caa0`: `MOVE.L #fff20000, 36(a0); MOVE.L #280000, 3a(a0); MOVE.W #a, 54(a0); JSR d3d7c.l`
- `2cabc`: `MOVE.L #a0000, 36(a0); MOVE.L #250000, 3a(a0); MOVE.W #7, 54(a0); JSR d3d7c.l`
- `2cad8`: `MOVE.L #fff70000, 36(a0); MOVE.L #10000, 3a(a0); MOVE.W #7, 54(a0); JSR d3d7c.l`
- `2caf4`: `MOVE.L #70000, 36(a0); MOVE.L #fffc0000, 3a(a0); MOVE.W #5, 54(a0); MOVEA.L #2cb30, a0; MOVE.W #1e, d0; MOVEA.L #100bf4, a1; JSR 2986.l`
- `2cb20`: `MOVEQ #0, d0; MOVEQ #10, d1; JSR 49214.l`
- `2cb2a`: `JMP 2a00.l` — FLOW

**stage event callback `306a8`(LONG `e8cd4`; 설치 `30718`) 2**
- `306a8`: `JSR 318d8(pc)` — FLOW
- `306ac`: `MOVE.L #30718, (a6); RTS`

**설치 callback `30718`(`306ac`·범위 밖 `304f6` `30710` `30efe`) / `3075a`(`30754` 설치, fall-through) 20**
- `30718`: `MOVEA.L #31d6e, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `30728`: `MOVE.B 1b(a6), 14(a6); MOVE.L #0, 76(a6); MOVE.L #0, 56(a6); MOVEQ #8, d0; MOVEQ #28, d1; JSR 4da4a.l`
- `30748`: `JSR 496c2.l` — FLOW
- `3074e`: `MOVE.B #ff, 94(a6); MOVE.L #3075a, (a6)` (→`3075a`)
- `3075a`: `JSR 316b2(pc)` — FLOW
- `3075e`: `LEA.L 31ad4.l, a0; JSR 1aa7e.l` — FLOW
- `3076a`: `BCC.W 30774` (→`3076e`) — C 소비, FLOW
- `3076e`: `MOVE.L #31002, (a6)` (→`30774`)
- `30774`: `JSR 3165e(pc)` — FLOW
- `30778`: `LEA.L 31ae4.l, a0; JSR 4d2d4.l` — FLOW
- `30784`: `BCC.W 307d6` (→`30788`) — C 소비, FLOW
- `30788`: `MOVE.W d0, 84(a6); JSR 319f6(pc)`
- `30790`: `BCC.W 307d6` (→`30794`) — C 소비, FLOW
- `30794`: `MOVE.W 84(a6), d0; MOVE.B #9, d1; MOVE.B 99(a6), d2; MOVE.B 9a(a6), d3; MOVE.W 54(a6), d4; JSR 4d508.l`
- `307ae`: `MOVE.L #307da, (a6); TST.W 92(a6); BMI.W 307d6` (→`307bc`)
- `307bc`: `JSR 48296.l` — FLOW
- `307c2`: `MOVEQ #0, d0; JSR 49c66.l`
- `307ca`: `MOVEQ #1, d0; JSR 49c66.l`
- `307d2`: `ST.B 5c8d(a5)` (→`307d6`) — FLOW
- `307d6`: `BRA.W 30ed2` — FLOW

**`30ed2`(`307d6 BRA`·범위 밖 `30614` `30646` `30714 BRA`) 1**
- `30ed2`: `BRA.W 30f84` — FLOW

**`30f84`(`30ed2 BRA`; 범위 밖 `30f04 BRA`(`30ed6` 꼬리)) 14**
- `30f84`: `JSR 4b54e.l` — FLOW
- `30f8a`: `BTST.B #7, 61(a6); SNE.B d0; BEQ.W 30f9c` (→`30f96`) — FLOW
- `30f96`: `MOVE.L #30b6c, (a6)` (→`30f9c`)
- `30f9c`: `AND.B d0, 5e(a6); BCLR.B #6, 61(a6); TST.W 88(a6); BEQ.W 30fb8` (→`30fae`)
- `30fae`: `SUBQ.W #1, 88(a6); BSET.B #6, 61(a6)` (→`30fb8`)
- `30fb8`: `JSR 4d766.l` — FLOW
- `30fbe`: `BCC.W 30fc8` (→`30fc2`) — C 소비, FLOW
- `30fc2`: `BSET.B #6, 61(a6)` (→`30fc8`) — FLOW
- `30fc8`: `TST.L 76(a6); BEQ.W 30fe4` (→`30fd0`)
- `30fd0`: `MOVE.B 1a(a6), 14(a6); JSR 318b8(pc)`
- `30fda`: `BSET.B #6, 61(a6); BRA.W 31000` — FLOW
- `30fe4`: `MOVE.B 1b(a6), 14(a6); MOVE.W 88(a6), d0; ANDI.W #1, d0; BEQ.W 31000` (→`30ff6`)
- `30ff6`: `MOVE.B 19(a6), 14(a6); ST.B 8c(a6)` (→`31000`)
- `31000`: `RTS` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다):
  - `2b418`: BYTE `15` bit 7 = 0이면 A0 = `2b374`(`2b422`); 아니면 BYTE `7f` ≥ 1(부호 없음)이면 A0 = `2b330`(`2b43c`), 0이면 `2b2ec`(`2b434`). `2b440`: `D0` = BYTE `7c`(0 확장), `D0.W` = 4·`D0.W`(16 bit), LONG `56` = LONG(A0 + sext(`D0.W`)), BYTE `80` = (LONG `36` ≠ 0) ? `ff` : 0(`SNE`), `D0.W` = `8c.W`; BYTE `15` bit 0 = 1이면 `D0.W` = −`D0.W`(`2b466`). `2b468`: `D0.W` = `D0.W` 산술 >> 5; 음수면 `2b47e`: `D0.W` = `D0.W` | `ff1f`(`NOT`/`ANDI #e0`/`NOT`). 아니면 `2b46e`: `D0.W` −= 1; 빌림(원래 0)이면 `2b478`, 아니면 `D0.W` &= `ff`(`2b474`); `2b478`: `D0.W` += 1, `BRA 2b486`. `2b486`: `D0.W` = ((`D0.W` + `100`) & `ffff`) >> 5(논리), BYTE `7c` = `D0.B`, `D1.W` = `8c.W`; BYTE `15` bit 0 = 1이면 `D1.W` = −`D1.W`(`2b49e`).
  - `2b4a0`: 부호 있는 `D1.W` < −`1500`(`eb00`)이면 BYTE `7d` = 0; < −`500`(`fb00`)이면 1; ≤ `500`이면 2; ≤ `1500`이면 3; 아니면 4(`2b4a8`..`2b4e8`, 모두 `BRA 2b4ee`). `2b4ee`: `D1.W` < 0이면 `D1.W` += `1ff`(`2b4f4`). `2b4f8`: `D1.W` = `D1.W` 산술 >> 1, `D1.W` &= `ff00`, `D7` = 0; `D1.W`가 `1000` `500` `0` `fb00` `f000` 중 하나와 같을 때마다 `D0.B` = `ff`(아니면 0)를 `D7.B`에 OR(`SEQ.B D0`: `D0.B`만 바뀌고 마지막 값은 `D1.W` = `f000` 여부), BYTE `7e` = `D7.B`, `JMP 49fc6`(interpreter, 호출자에게 복귀).
  - `2b668`: `D1` = 4·BYTE `7c`(LONG, 16 bit 덧셈 두 번), A4 = `2d8b8` + sext(`D1.W`), `D0.W` = WORD (A4)+, `D1.W` = WORD (A4)+; BYTE `15` bit 0 = 1이면 `D0.W` = −`D0.W`(`2b686`). `2b688`: A0 = `2b692`, `JMP 4da50`(N23: `28ae` 자식 `4db42`, WORD `76`/`78` = `D0.W`/`D1.W`, LONG `7a` = `2b692`; 호출자에게 복귀).
  - `2b692`(code pointer, A6 = `4db42` 자식): A0 = LONG `c`(부모), `D1` = 4·BYTE `7c(A0)`, A4 = `2d8b8` + sext(`D1.W`), `D0.W` = WORD (A4)+, `D1.W` = WORD (A4)+; BYTE `15(A0)` bit 0 = 1이면 `D0.W` = −`D0.W`(`2b6b4`). `2b6b6`: `2e.W` = `D0.W`, `32.W` = `D1.W`, C = 0, RTS.
  - `2b7ce`: `20.W` = `f2`, LONG `22` = bank LONG `20009c`, LONG `9e` = `2b3d0`, `8ebe`(`D0.W` = `87d`, `D1.B` = 1); `2b7f2`: `8ebe`(`39d`, 1); `2b800`: `8ebe`(`87a`, 1). `2b80e`: `8e.W` = `8080`; BYTE `15` bit 0 = 1이면 `2b860`. `2b81e`/`2b860`: `28ae`(A0 = `41fe6`, `D0.W` = `a`); Clear면 `2b85c`/`2b89e`(C = 0 그대로 RTS). `2b832`/`2b874`: A1 = A6 + `8e`, LONG `76(A0)` = A1, BYTE `7a(A0)` = 6, `7b(A0)` = `7c(A0)` = `7d(A0)` = 0, `7e(A0)` = 0(`2b832`) / 4(`2b874`), C = 1; RTS(`2b85c BRA 2b89e`).
  - `2b8a0`: BYTE `15` |= 1(`BSET.B #0`). `2b8a6`: `BSR 2b7ce`; `2b8aa`: `BRA 2b8b6`. `2b8b6`: `76.W` = 0이면 `JSR 4c0ac`(U12, `2b8be`). `2b8c4`: `68.W` = `1e.W` = `8810`, `8c.W` = 0, `JSR 4c37c`(경계). `2b8dc`: LONG `94` = A0, `D1` = 1, `JSR 4d81c`(stage_area). `2b8e8`: BYTE `83` = `D1.B`, BYTE `84` = `D2.B`, `54.W` = `D3.W`, `(A6)` = `2b96c`, RTS.
  - `2b96c`(설치): BYTE `14` = BYTE `1b`, LONG `98` = 0, `49f8c`(A1 = `645da`, `D0.W` = `100`). `2b98a`: LONG `64` = 0, `BSR 2b668`. `2b996`: `(A6)` = `2b99c`, fall-through. `2b99c`(설치): `54.W` = 0이면 `2c7fe`. `2b9a4`: BYTE `61` bit 7 = 1이면 `2ca68`. `2b9ae`: BYTE `5e` = 0, BYTE `86` = 8, `BSR 2c760`. `2b9be`: `JSR 2b418`. `2b9c2`: A0 = `2b6ce`, `JSR 1aa7e`(U01); Set이면 `JMP 2a00`(`2b9d0`). `2b9d6`: A0 = `2b6d6`, `2b668`과 같은 `2d8b8` 읽기(BYTE `7c`)와 `NEG`(`2b9f8`). `2b9fa`: push WORD `42.W`, push WORD `46.W`, `42.W` += `D0.W`, `46.W` += `D1.W`(16 bit), `JSR 4d2d4`(N23). `2ba10`: Clear면 `2ba44`. `2ba14`: `88.W` = `D0.W`, `BSR 2b63e`(경계). `2ba1c`: Clear면 `2ba44`. `2ba20`: `8a.W` = `D0.W`, `D0.W` = `88.W`, `D1.B` = 1, `D2.B` = BYTE `83`, `D3.B` = BYTE `84`, `D4.W` = `54.W`, `JSR 4d508`(N23). `2ba3e`: `(A6)` = `2ba50`. `2ba44`: `46.W` = pop WORD, `42.W` = pop WORD, `BRA 2c8ca`.
  - `2c760`: A0 = LONG `94`; BYTE `15` bit 7 = 1이면 `JSR 4c3de`(경계, `2c76e`), `2c774`: `8c.W` = `D0.W`, RTS. `2c77a`: LONG `36` = LONG `64`, A4 = LONG `9e`, `D0` = LONG `10(A4)` − LONG `3a`(32 bit), A4 = LONG `9e`, `D1.W` = WORD `6(A4)`, `D0` = `D0` 산술 >> (`D1` & 63)(32 이상이면 부호 bit로 채움), LONG `3a` += `D0`(32 bit), `JSR 4c3a2`(경계); `2c7a0`: `8c.W` = `D0.W`, RTS.
  - `2c7fe`: `3af8`(`D0.W` = `1ac8`). `2c808`: `49f8c`(A1 = `65f56`, `D0.W` = `100`). `2c818`: LONG `98` = `2c7a6`, `D0` = 0, `D1.W` = `38`, `JSR 4db18`(경계). `2c82c`: `92.W` = `60`, `(A6)` = `2c838`, fall-through. `2c838`(설치): A0 = LONG `98`; 0이면 `2c866`. `2c844`: BYTE `14` = BYTE `1a`, `D1.W` = WORD (A0)+; `ffff`가 아니면 `2c858`; 맞으면 A0 += sext(WORD (A0)), `D1.W` = WORD (A0)+(`2c854`). `2c858`: LONG `98` = A0, `D0.B` = BYTE `14`, `JSR 8d34`(경계). `2c866`: LONG `64` = 0, BYTE `86` = `ff`, `D0.W` = `88.W`; 음수면 `2c8b0`. `2c878`: `D0.W` = `88.W`, `JSR 49be0`(U06). `2c882`: `D0.W` = WORD (A0); bit 5 = 1이면 `2c88c`: `D1.B` = 1, `D0.W` = `88.W`, `JSR 4d4b4`(경계). `2c89a`: `BSR 2b63e`(경계). `2c89e`: Clear면 `88.W` = `ffff`(`2c8a2`). `2c8a8`: `BSR 2c71a`(경계), `BRA 2c8b4`. `2c8b0`: `BSR 2c760`. `2c8b4`: `BSR 2b418`. `2c8b8`: `92.W` −= 1; 결과 bit 15 = 1이면 `(A6)` = `2ca68`(`2c8c0`). `2c8c6`: `BRA 2c8ca`. `2c8ca`: `8e.W` = `8000`이면 RTS(`2c8f0`). `2c8d4`: A0 = LONG `78`, `D0.B` = BYTE (A0)+, `D1.B` = BYTE (A0)+; BYTE `15` bit 0 = 1이면 `D0.B` = −`D0.B`(`2c8e6`). `2c8e8`: BYTE `8e` = `D0.B`, BYTE `8f` = `D1.B`. RTS.
  - `2ca68`: `3af8`(`D0.W` = `18de`). `2ca72`: A0 = `2c94c`, `JSR 4ae4a`(N08). `2ca7c`: `D1.B` = 0, `D0.W` = `88.W`, BYTE `5e` = 7, `JSR 4d4b4`(경계). `2ca90`: `D0` = 1, `D1` = 0, `JSR 4ff96`(경계). `2ca9a`: `JSR d3d7c`(경계). `2caa0` `2cabc` `2cad8` `2caf4`: 반환 A0 노드에 LONG `36` / LONG `3a` / `54.W` = (`fff20000`, `280000`, `a`) / (`a0000`, `250000`, 7) / (`fff70000`, `10000`, 7) / (`70000`, `fffc0000`, 5); 앞 셋은 다시 `JSR d3d7c`, `2caf4`는 `2986`(A0 = `2cb30`, `D0.W` = `1e`, A1 = `100bf4`; 결정 6). `2cb20`: `D0` = 0, `D1` = `10`, `JSR 49214`(N05). `2cb2a`: `JMP 2a00`.
  - `306a8`: `JSR 318d8`(경계). `306ac`: `(A6)` = `30718`, RTS.
  - `30718`(설치): `49f8c`(A1 = `31d6e`, `D0.W` = `100`). `30728`: BYTE `14` = BYTE `1b`, LONG `76` = 0, LONG `56` = 0, `D0` = 8, `D1` = `28`, `JSR 4da4a`(N23: `28ae` 자식 `4db42`, LONG `7a` = 0). `30748`: `JSR 496c2`(U11). `3074e`: BYTE `94` = `ff`, `(A6)` = `3075a`, fall-through. `3075a`(설치): `JSR 316b2`(경계). `3075e`: A0 = `31ad4`, `JSR 1aa7e`(U01); Set이면 `(A6)` = `31002`(`3076e`). `30774`: `JSR 3165e`(경계). `30778`: A0 = `31ae4`, `JSR 4d2d4`(N23); Clear면 `307d6`. `30788`: `84.W` = `D0.W`, `JSR 319f6`(경계); Clear면 `307d6`(`30790`). `30794`: `D0.W` = `84.W`, `D1.B` = 9, `D2.B` = BYTE `99`, `D3.B` = BYTE `9a`, `D4.W` = `54.W`, `JSR 4d508`(N23). `307ae`: `(A6)` = `307da`; `92.W` < 0이면 `307d6`. `307bc`: `JSR 48296`(U01). `307c2`/`307ca`: `JSR 49c66`(input; `D0` = 0 / 1). `307d2`: BYTE `5c8d(A5)` = `ff`. `307d6`: `BRA 30ed2`; `30ed2`: `BRA 30f84`.
  - `30f84`: `JSR 4b54e`(U01; C는 소비되지 않음). `30f8a`: `D0.B` = (BYTE `61` bit 7 = 1) ? `ff` : 0; bit 7 = 1이면 `(A6)` = `30b6c`(`30f96`). `30f9c`: BYTE `5e` &= `D0.B`, BYTE `61` bit 6 = 0; `88.W` ≠ 0이면 `88.W` −= 1, BYTE `61` bit 6 = 1(`30fae`). `30fb8`: `JSR 4d766`(N23); Set이면 BYTE `61` bit 6 = 1(`30fc2`). `30fc8`: LONG `76` ≠ 0이면 BYTE `14` = BYTE `1a`, `JSR 318b8`(경계, `30fd0`), BYTE `61` bit 6 = 1, `BRA 31000`(`30fda`). `30fe4`: BYTE `14` = BYTE `1b`, `D0.W` = `88.W` & 1; ≠ 0이면 BYTE `14` = BYTE `19`, BYTE `8c` = `ff`(`30ff6`). RTS(`31000`).

## carry

- [F] **소비 10 block**(모두 FLOW). Unknown C로 들어오면 `objects n28 caller requires known carry`(상태 보존)다. Clear면 BCC는 분기 대상, BCS는 fall-through; Set이면 반대.
  - `2b82e BCC.W 2b85c`, `2b870 BCC.W 2b89e`: fade_card `28ae`(`2908 ORI` Set = 자식 생성, `290e ANDI` Clear = 자리 없음).
  - `2b9cc BCC.W 2b9d6`, `3076a BCC.W 30774`: U01 `1aa7e`(`1aaf6 ANDI` Clear, `1aafc ORI` Set).
  - `2ba10 BCC.W 2ba44`, `30784 BCC.W 307d6`: N23 `4d2d4`(`4d2fe ANDI` Clear, `4d310` `4d320` `4d350` `4d35e` `4d366 ORI` Set).
  - `2ba1c BCC.W 2ba44`, `2c89e BCS.W 2c8a8`: 경계 `2b63e`(결정 5).
  - `30790 BCC.W 307d6`: 경계 `319f6`(결정 5).
  - `30fbe BCC.W 30fc8`: N23 `4d766`(`4d77a ADD.B D1,D1`: C = `D1.B` bit 7).
- [F] **known 생산 3 block**: Set(`ORI`) `2b832` `2b874`; Clear(`ANDI`) `2b6b6`. 소비자 확인은 결정 3.
- [F] **FLOW_ONLY 53 block**(C 보존): JSR/BSR/JMP/BRA/RTS block, `LEA`+`BRA`/`JMP`/`JSR`(`2b422` `2b434` `2b43c` `2b688` `2b9c2` `2ca72` `3075e` `30778`), `BTST`(+Bcc)·`BSET`·`ST`·`SNE` block(`2b418` `2b8a0` `2b9a4` `2c760`(`MOVEA`+`BTST`) `307d2` `30f8a` `30fc2` `30fda`), 소비 10개. 목록: `2b418` `2b422` `2b434` `2b43c` `2b688` `2b82e` `2b85c` `2b870` `2b89e` `2b8a0` `2b8a6` `2b8aa` `2b8be` `2b9a4` `2b9be` `2b9c2` `2b9cc` `2b9d0` `2ba10` `2ba1c` `2c760` `2c76e` `2c89a` `2c89e` `2c8a8` `2c8ac` `2c8b0` `2c8b4` `2c8c6` `2c8f0` `2ca72` `2ca9a` `2cb2a` `306a8` `30748` `3075a` `3075e` `3076a` `30774` `30778` `30784` `30790` `307bc` `307d2` `307d6` `30ed2` `30f84` `30f8a` `30fb8` `30fbe` `30fc2` `30fda` `31000`.
- [F] **carry 보존 목록 53 PC** = FLOW_ONLY 53. 생산 3 block은 보존 목록에 넣지 않고 block 안에서 C를 정한다.
- [F] **Unknown 95 block**: 나머지(`MOVE`/`MOVEQ`/`TST`/`CMPI`/`CMPA`/`ADD`/`ADDI`/`ADDQ`/`SUB`/`SUBQ`/`AND`/`ANDI`/`OR`/`NEG`/`NOT`/`ASR`/`LSR`/`CLR` 포함 block, 설치 block, 애니메이션 block).
- [F] `2b7ce`가 RTS로 돌려주는 C(`28ae` Clear 그대로 / `2b832` `2b874` Set)는 N28 안에서 소비되지 않는다(`2b8aa BRA` → `2b8b6 TST.W`). callback 끝 RTS(`2b8e8` `2c8f0` `306ac` `31000` 등)의 C는 scheduler가 쓰지 않는다.

## 구현 범위와 규약

- routing 12 범위(위 표). 짝수 PC 873개 중 block 시작 151, 내부 722. 내부 PC 직접 진입은 `unsupported animation objects n28 PC`다. 범위 이웃(미참조 코드·범위 밖에서만 들어오는 경로·자료·다른 단위 범위)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술·shift는 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다(`ASR.W #5` `ASR.W #1` `ASR.L Dn`은 부호 bit 채움을 직접 계산, `ASR.L`의 레지스터 shift 수는 `D1` & 63). 부호 있는 비교(`BGE`/`BGT`)는 WORD를 부호 있는 값으로 명시 변환해 비교한다. 결과 flag는 같은 block 안의 Bcc/`Scc`만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 53 PC를 넣는다.
- 제어 이동은 모두 정적이다. `2b52c JMP 49fc6`·`2b68c JMP 4da50`·`2b9d0` `2cb2a JMP 2a00`은 복귀 LONG을 push하지 않는다. 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`2b996`→`2b99c`, `2c82c`→`2c838`, `3074e`→`3075a`). `2b8a0`은 `2b8a6`으로, `2ba3e`는 `2ba44`로, `2b832`는 `2b85c`로 이어진다.
- 스택: JSR/BSR 복귀 LONG과 `2b9fa`/`2ba44`의 WORD push/pop만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `20009c`(`2b7ce` id `f2` → LONG `22`).
- [F] 고정 ROM 자료(live bus 읽기, 원본처럼 색인 검사 없음):
  - `2b2ec` `2b330` `2b374` LONG 표(색인 4·BYTE `7c`; BYTE `7c`는 `2b486`이 0..`10`으로 만든다) → LONG `56`.
  - `2d8b8` WORD 쌍 표(색인 4·BYTE `7c`(`2b668` `2b9d6`) 또는 4·BYTE `7c(부모)`(`2b692`)).
  - LONG `9e`(= `2b3d0`, `2b7ce`)가 가리키는 기록의 LONG `10`·WORD `6`(`2c77a`).
  - LONG `98` 목록(`2c818`이 `2c7a6`을 넣음; WORD `ffff` 다음 WORD는 되감기 변위, `2c844`/`2c854`).
  - 주소만 넘기는 자료: 사각형 `2b6ce`(`1aa7e`) `2b6d6`(`4d2d4`) `31ad4`(`1aa7e`) `31ae4`(`4d2d4`), 애니메이션 목록 `645da` `65f56` `31d6e`(`49f8c`), `4ae4a` 인자 `2c94c`, `2986` 자식 값 `2cb30`, `8ebe` 인자 WORD `87d` `39d` `87a`, `3af8` 인자 `1ac8` `18de`.
- [F] work RAM:
  - 노드 A6: BYTE `14` `15` `19` `1a` `1b` `5e` `61` `7c` `7d` `7e` `7f` `80` `83` `84` `86` `8c`(BYTE `ST`) `8e` `8f` `94` `99` `9a`; WORD `1e` `20` `2e` `32` `42` `46` `54` `68` `76` `84` `88` `8a` `8c` `8e` `92`; LONG `(A6)`(설치) `c`(부모, `2b692`) `22` `36` `3a` `56` `64` `76` `78`(BYTE 쌍 포인터) `94` `98` `9e`.
  - 부모 `c(A6)`(`2b692`): BYTE `7c` `15`.
  - `28ae` 자식 A0(`2b832` `2b874`): LONG `76` = A6 + `8e`, BYTE `7a`..`7e`. `d3d7c` 반환 A0(`2caa0`..`2caf4`): LONG `36` `3a`, WORD `54`.
  - `49be0` 반환 A0의 WORD `0`(`2c882`). A5 기준 BYTE `5c8d`(`307d2`).
- [F] 상수 인자: `28ae` `D0.W` = `a`(A0 = `41fe6`); `2986` `D0.W` = `1e`, A0 = `2cb30`, A1 = `100bf4`; `49f8c` `D0.W` = `100`; `4d508` `D1.B` = 1(`2ba20`) / 9(`30794`); `4da4a` `D0`/`D1` = 8/`28`; `4d81c` `D1` = 1; `4db18` `D0`/`D1.W` = 0/`38`; `4d4b4` `D1.B` = 1(`2c88c`) / 0(`2ca7c`); `4ff96` `D0`/`D1` = 1/0; `49214` `D0`/`D1` = 0/`10`; `49c66` `D0` = 0, 1.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256): `engine/src/animation_machine_objects_n28.cpp` `6b78e30430021e4bea1a467f7e2925f23a0e8512150564dde0a925073d73504e`, `engine/tests/animation_machine_objects_n28_test.cpp` `91083b58dc95486d44e9efb40e2f63d5cab8b4fce06c0b80501cf2021a679a0d`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나(53 PC); `f8e19026…`), `engine/src/animation_machine_internal.h`(선언 하나; `79ad5994…`), `Makefile`(source 목록·test target·실행 줄; `7327cd24…`), `tools/verify_animation_machine.py` SOURCES(`985cd43a…`). `animation_machine_interpreter.cpp`와 다른 단위 실행부는 바꾸지 않았다.
- [F] 실행부 case 집합 = scratch `starts.txt`(151, SHA256 `cb86f81e…`). 내부 PC 722개는 모두 `unsupported animation objects n28 PC`, 소비 10 block은 Unknown C에서 `objects n28 caller requires known carry`(상태 보존)다.
- [F] `make -j4 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`). N28 test 출력: `animation machine objects n28: 423 fixtures (30 checked errors, 48 kept C), 151 blocks, 2092 calls`. N20~N23 test는 그대로 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N28 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen28.py` Unicorn 생성, `gen/assemble28.py` 조립): 423 fixture(성공 393, checked 오류 30), 151 시작 모두 Unicorn fixture로 덮음, block 표(151 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 10은 Unknown에서 거부), zero-step 151 × 3, 내부 PC 722 전수, 홀수 PC(범위 양끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`(9 fixture), 범위 안·옆 자료 `2c7a6` `2c7d0` `2c7fc` `2b6c4` `2b6ce`, 경계·다른 단위 진입 stop 38개(stop만). "real" 행은 `28ae`(`2b80e`), `1aa7e`(`2b9c2` `3075e`), N23 `4d2d4`(N22 `1bf02` 경유; `2b9fa` `30778`), N23 `4d766`(N22 `1bfb4` 경유; `30fb8`)를 native로 따라가 실제 소비자 분기와 비교했다. 합성 물리 바이트(ROM 자료 아님): `1bef8`, `2b2ec..2b3b8`, `2b6ce..2b6de`, `2d8b8..2d8fc`, `31ad4`, `31ae4`, bank LONG `20009c`.
- [F] RTS 앞 생산 native 확인(실제 ROM 소비자 `4dbb2 BCS.W 4dbd6`를 복귀 LONG으로, Unicorn SR 미사용): `2b6b6` → Clear(`4dbb6`), `2b832` `2b874` → Set(`4dbd6`). 계약과 같다.
- [F] 돌연변이 검사(scratch `mut/mut28.py`, 실행부 한 줄씩 20개: 소비 분기 뒤바꿈 2, `ASR.W` 부호 채움, 부호 있는 `BGE`/`BGT` 2, `2b47e` 마스크, `2b46e` 빌림, `SEQ` 값, `ASR.L` shift 수 mod 64, `ADDA.W` 부호 확장, `2c8b8` N, `2b6b6` C, `2ba44` pop 순서, `SNE` 값, `AND.B`, `NEG.B`, `2b874` BYTE `7e`, `30fe4` bit, pair 색인 배수, `2b42a` 비교): 20/20을 test가 잡았다.
- [F] 실제 ROM 차분(scratch `realrom/real28.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM, 실제 ROM 표 `2b2ec` `2b330` `2b374` `2d8b8`·기록 `2b3d0`·목록 `2c7a6`·bank LONG `20009c`, native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC·interpreter `49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 150/151/150(합집합 151). 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `2b82e` 40 `2b870` 54 `2b9cc` 69 `2ba10` 119 `3076a` 42 `30784` 62 `30fbe` 159. interpreter 따라가기(`FOLLOW_ANIM`) 2 × 1,000 case 불일치 0. 의도한 차이: `2986` 실패 경로 caller-X 제한(`cue wrapper failure requires known caller X`, 결정 6) 0/1/2/3/0건(모두 `2caf4`). native 홀수 주소·Unknown C 진입 소비 거부 0. clean stop이 없는 native case는 건너뜀(seed별 136/117/122; 주로 `4b54e`·interpreter 경로).
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `0da8cec` 일치 pass 14,408·node 122,462, 불일치 0 → N28 뒤 같음(`diff_results.json` SHA256 `a6c41695…` 기준과 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` SHA256 `5656685f…`) → N28 뒤 같은 수치·불일치 0(`cdffa22c…`; 차이는 기록된 `animation_machine.cpp` 원본 SHA와 새 원본 목록뿐). **새 완주 seed 없음**(재범위 예상과 같음), 잃은 seed 0. seed 116 117은 그대로 frame 0 `38ba0`(N31)에서 멈춘다.
- [U] 남은 미확인: N28 범위의 자연 frame pass 비교는 116 117이 `38ba0`에서 먼저 멈춰 아직 없다(실제 ROM 차분·fixture로만 덮음). 경계 `2b63e`·`319f6`의 C 생산(소비 `2ba1c` `2c89e` `30790`)은 그 단위가 정한다. 결정 1의 `2b8fc..2b96c`·`30ed6..30f84`와 결정 2의 `4db18`은 routing하지 않았다.
