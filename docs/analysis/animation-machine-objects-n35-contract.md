# 객체 callback F4 N35: `28ae` 자식 callback `4cf52`, 슬롯 판정 `4d8d8`, 속도 최대값 `4c6f0`, 지형 호출 `ea680` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N35 행(27 block, 누적 5,379, 5 범위 `4c6f0..4c72a` `4cf52..4cf64` `4d8d8..4d900` `4da4a..4da74` `ea680..ea69c`, 진입 `4cf52`, 새 완주 seed 116 117, 예상 완주 RNG 136 / base 137, 옛 U47 27)과 N33 계약(`animation-machine-objects-n33-contract.md`, SHA256 `9b15f2e9a117e2aedc1789dfb8cddd6fc2b60158864a4cc27c946fde28b8318c`)의 결정 5(u08b `4bc44`의 두 번째 진입 `4bc58`)다. 단위 형식과 규약은 N33 계약을 따른다. 메인 작업 지시:
- block 시작은 `MOVE.L #imm,(A6)` 설치 callback, DBRA 대상, JSR 복귀점을 포함한 정적 디코드로 정하고 자료는 routing하지 않는다. 다른 단위의 기존 routing 범위 안을 다시 routing하지 않는다(N23은 `4d2d4..4d418` `4d766..4d77e` `4d900..4dbdc` 등). N34(`4c3de..4c6f0` `4c810..4cf52`)는 다른 작업자 몫이라 stop 전용이다.
- seed 116 117은 기준(`e7c6972`)에서 frame 0 node 7 callback `4cf52`(A6 `1014b8`)에서 멈춘다. N35(필요하면 `4bc58` 진입) 뒤 멈춤 위치(PC, frame, node, 소유 단위)와 새 완주 seed를 보고한다.
- 두 번째 진입 `4bc58`: N33 scratch patch(`ms5-scratch/n33/patch-u08b-4bc58.diff`)를 검토해 적용하고 u08b test(BLOCKS 행, 수, `4bc58` fixture)와 u08b 계약을 고친다.

- 결정 관례(N33과 같음): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 설치, 범위 밖에서 참조하는 범위 안 진입)로 정한다. Unicorn TB 분할은 시작이 아니다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- carry 관례(U01~N33 수용): `MOVE`/`MOVEQ`/`CMP`/`NEG` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`JSR`/`JMP`/`BRA`/`RTS`/Bcc)만인 block과 callee C를 소비하는 block은 FLOW_ONLY다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N35 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. bank 읽기는 없다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n35`(HEAD `e7c6972` = N01~N33(N32a/b), F5 H1·H3, 외부 읽기 큐 통합, `engine/src/animation_machine.cpp` SHA256 `6043293e064d770ef7538371620c6e77765718476f00917a8f538683a4fddfcd`, `engine/src/animation_machine_objects_u08b.cpp` SHA256 `2eaa138c170340b55b81f0b1e9635b011a9ebe1d28a15d158e44edcecd8f1afc`, `..._u12.cpp` SHA256 `6e253200a738959be131965923c934074012069e79740fabd648f8af0835b84c`, `..._u18.cpp` SHA256 `2cde406861882eead5cdc74f16dd5fb91118305ef05b8205ff095ea290f8dae0`, `animation_machine_stage_event_ops.cpp` SHA256 `5369d279877922f015249c3d4173cccd46beabdf6c3a50d9c220c175b982f61c`)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n35/n35.py`(정적 디코드, `starts.txt` SHA256 `00fa86d43f441319f54987078ba4a513f22091bb3401d640d25bd35f475d5601`)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N35 = 26 block**(4 routing 범위 `4c6f0..4c72a` `4cf52..4cf64` `4d8d8..4d900` `ea680..ea69c`, 코드 144바이트, 45 명령 전부 도달, 자료 없음, 짝수 PC 72, 내부 46). 진입 4개에서 분기·fall-through·JSR 복귀점을 끝까지 따라간 정적 closure다. 범위 안 설치·`28ae` 자식·DBRA·간접 제어 이동·묶인 Bcc는 없다.
- [F] 진입(범위 밖에서 들어옴):
  - `28ae` 자식 callback `4cf52`(N33 `4c37c MOVEA.L #4cf52,A0`): `288c`(부모 확인), C Set → RTS, Clear → `JMP 2a00`(자기 삭제).
  - `4d8d8`(N33 `4bd02` `3a1e8`, 범위 밖 `30bfe` `30c56` `31a12` `337a6` `337e0` `33940` `3a15e` `3a4be` `3da70` `3dcda` `40b7c` `JSR`): `D0` ← A6, `D0.W`가 WORD `5cba(A5)`와 같으면 `D0` = 0, `D1.B` ← BYTE `5ce1(A5)`; 아니면 WORD `5ce6(A5)`와 같으면 `D0` = 1, `D1.B` ← BYTE `5d0d(A5)`; 둘 다 아니면 `D0` = `ffffffff`, `D1` = 0. RTS. 호출자는 모두 `TST.B/W D0` 뒤 N을 본다(C 소비 없음).
  - `4c6f0`(N34 `4ca68` `4ccb8 BSR.W`): LONG `5c92(A5)`의 절댓값이 `|D0|`보다 무부호로 작으면 `5c92` ← D0, LONG `5c96(A5)`와 `D1`도 같은 방식. D6/D7을 덮는다. RTS. `NEG.L 80000000` = `80000000`(32bit wrap), 비교는 `CMP.L D7,D6; BCC`(무부호).
  - `ea680`(N29 `30df4` `30e4c`, 범위 밖 `208fa` `20a4a` `20bcc` `3058c` `37202` `959ee` `JSR`): `1abda`(U12), C Clear → RTS(C Clear 그대로), Set → `D0` ← LONG `42(A6)`, `D1` ← LONG `46(A6)`, `A0` = 0(`MOVEA.W #0`), `D7` = 8, `BRA.B ea65a`(U18 block 시작). 호출자 8곳은 모두 `BCC`로 반환 C를 소비한다.
- [F] **다른 실행부로 가는 callee·출구 4개**: `288c`(stage_event_ops), `2a00`(fade_card), `1abda`(U12), `ea65a`(U18). routing 밖 경계 callee는 없다.
- [F] **carry**: 소비 2 block(FLOW), known 생산 0, FLOW_ONLY 8(소비 2 포함), Unknown 18. 8 + 18 = 26.
- [F] X·DIVx/MULx·TRAP·I/O port 쓰기·bank 읽기/변경·계산 점프 표·레지스터 간접 제어 이동이 없다. N/Z 재계산 없음(모든 Bcc가 같은 block 안의 생산자를 읽는다; 소비 2 block만 callee C). 스택: JSR 복귀 LONG만.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준): seed 116 117만 N35 PC를 실행한다. `4cf52` `4cf58` `4cf62`(frame 0 node 7, callback `4cf52`), `4d8d8` `4d8ea` `4d8fa`(frame 0 node 9, callback `3310c`), `ea680` `ea686` `ea68a`(frame 0 node 14, callback `30dbe`), `4c6f0` `4c6f8` `4c702` `4c70c` `4c714` `4c71e` `4c728`(frame 1 node 7, callback `2b96c`). 같은 재생에서 `4bdfe`와 `4bc58`도 frame 0 node 9에 TB로 나온다(아래 결정 4).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **`4da4a..4da74`는 N35에 넣지 않는다.** [F] N22 계약 결정 4로 N23에 옮겨졌고 이미 `animation_objects_n23_block`이 routing한다(N23 계약 SHA256 `ad189087b33086de823cebdade045281fe057ebb7b8beb45ec0b51920d06e40b`, "넣은 것" `4da4a..4da74` 3 block). 다른 단위 범위 안을 다시 routing하지 않는다.
2. **재범위 수치와 다른 점(27 → 26).** [F] 재범위 N35 행 27 block은 `4da4a..4da74`를 포함한 수다. 이 계약은 그 범위를 빼고 조건분기 fall-through(`NEG.L` 4개, `MOVE.L` 저장 2개)를 시작으로 나눈 26 block이다([U] 재범위 leader 집합과의 집합 비교는 하지 않았다).
3. **`4c72a..4c7a4`(소유자 없음)는 N35 범위 밖이다.** [F] 재범위 N34 행의 경계 `4c72a`는 N34 `4ca9c` `4ccf0 BSR.W`가 부르는 다음 함수(`LSL.L #2,D0; BPL; ADDI.L #ffff,D0; ...`)이고 어느 행에도 없다. N35는 `4c6f0..4c72a`만 가진다. [I] N34 또는 N35 뒤 정리 단계에서 정한다.
4. **u08b 두 번째 진입 `4bc58`(적용함, N33 결정 5의 해소).** [F] N33 `4bdfe MOVEM.L (A7)+,D0-D7; BRA.W 4bc58`은 u08b block `4bc44`의 다섯 번째 명령으로 들어간다(ROM 참조는 `4be02` 하나). N35(`4d8d8`) 뒤 seed 116 117이 `4bdfe`에 닿으므로 u08b `4bc44`를 `4bc44`(`CLR.B 549f; CLR.B 54a0; MOVE.B #ff,54a2; MOVE.B #ff,54a3`, 후속 `4bc58`)와 `4bc58`(`MOVE.B #0,549d; MOVE.B #0,549e; MOVE.B #2,549c; BTST #4,15(A6); BEQ 4bc7a`)로 나눈다. 실행 의미는 같고 둘 다 Unknown(MOVE)이다. u08b 수: block 165 → 166, 내부 589 → 588, FLOW 27 그대로. N33 scratch patch를 검토해 그대로 적용했다(`4bc44` 쓰기 순서·값, `4bc58` 분기 대상 `4bc74`/`4bc7a` 일치).
5. **`4cf58`·`ea686`의 C.** [F] `4cf58 BCS.W 4cf62`는 `288c`(stage_event_ops; ORI Set `2898` `28a8`, 계산 `289e`)의 C, `ea686 BCS.W ea68c`는 U12 `1abda`(계산 C)의 C를 소비한다. Unknown이면 `objects n35 caller requires known carry`(상태 보존). `ea68a RTS`는 FLOW라 `1abda`의 Clear가 호출자(`BCC`)로 그대로 간다. `ea68c`의 C는 Unknown이다(`ea65a BSR.B ea636`의 `SUBI.L`이 소비 전에 덮음).
6. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n35.cpp`의 `animation_objects_n35_block`. 오류는 `unsupported animation objects n35 PC`(내부 PC), `objects n35 caller requires known carry`(소비 2 block).
7. **`2986` caller-X 제한 해당 없음.** [F] N35는 `2986`을 부르지 않는다.

## 원본 바이트 근거

[F] N35 코드 4 범위 합계 144바이트(짝수 PC 72개, 시작 26, 내부 46). 범위 순서로 이어 붙인 SHA256 `39c47c070e80ed8e3f8cf263c0be746d6b5a3b7cd9866fcee7fc9a29bc271bba`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `4c6f0..4c72a` | 58 | `0e3187f961ddd404cdda3293520c3535e5f88d637a214d2bc98f1ac0b68a0d00` | 13 |
| `4cf52..4cf64` | 18 | `0c1f27c8574a73214e1956a00bc11b6a79e48c1de9a4bba2ab338aa7e8fb9562` | 4 |
| `4d8d8..4d900` | 40 | `1e07253807a40743e02d6fcc00142b77e2b585db15181e821b3a12ddc3d40c43` | 5 |
| `ea680..ea69c` | 28 | `bc0ccaa177ab1297dc688a490120419f8721e416f187353d31cf3ae63419dd9d` | 4 |

- [F] 범위 이웃(앞/뒤 PC의 routing): `4c6ee`(routing 밖, N34 범위 `..4c6f0`의 끝 `RTS`) / `4c72a`(routing 밖, 결정 3); `4cf50`(routing 밖, N34 범위 끝) / `4cf64`(routing 밖, 0 자료); `4d8d6`(routing 밖, `4d8ca` 조각의 `RTS`) / `4d900`(N23); `ea67e`(U18) / `ea69c`(routing 밖, 다른 함수 `MOVEQ #0,D2; BRA.W ea6b0`).
- [F] 범위 안 참조(scratch `xref35.py`): 분기 대상과 진입만 있다(`4c6f0` ← `4ca68` `4ccb8`; `4cf52` ← LONG `4c37e`; `4d8d8` ← LONG 13곳; `ea680` ← LONG 8곳). 명령 중간을 가리키는 값은 없다.
- [F] 자료: `4cf64..`(0 WORD)는 `4cf62 RTS` 뒤 자료라 routing하지 않는다.

## carry

- [F] **FLOW_ONLY 8**(진입 C를 그대로 둔다; `carry_preserving_pc` 목록에 넣음): `4c728`(RTS), `4cf52`(JSR), `4cf58`(소비), `4cf5c`(JMP), `4cf62`(RTS), `ea680`(JSR), `ea686`(소비), `ea68a`(RTS).
- [F] **소비 2**(Unknown이면 `objects n35 caller requires known carry`, 상태 보존): `4cf58 BCS.W 4cf62`(`288c`), `ea686 BCS.W ea68c`(`1abda`).
- [F] **known 생산 0.** 
- [F] **Unknown 18**: `4c6f0` 함수 12 block(`MOVE.L`/`NEG.L`/`CMP.L`; 실제 반환 C는 항상 Clear지만 소비자가 없다: N34 `4ca6c` `4ccbc MOVE.L D0,D7`이 덮음), `4d8d8` 5 block(`CMP.W`/`MOVEQ`/`MOVE.B`; 호출자는 `TST` 뒤 N만 봄), `ea68c`(결정 5).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. `BPL`은 직전 `MOVE.L` 결과 bit 31(N)만, `BCC`는 `CMP.L D7,D6`의 무부호 빌림(D6 ≥ D7이면 분기), `BNE`는 `CMP.W`의 Z(D0 하위 WORD)를 본다.

**속도 최대값 `4c6f0`(N34 `4ca68` `4ccb8`) 13**
- `4c6f0`: `MOVE.L d0, d7; BPL.W 4c6f8` (→`4c6f6`)
- `4c6f6`: `NEG.L d7` (→`4c6f8`)
- `4c6f8`: `MOVE.L 5c92(a5), d6; BPL.W 4c702` (→`4c700`)
- `4c700`: `NEG.L d6` (→`4c702`)
- `4c702`: `CMP.L d7, d6; BCC.W 4c70c` (→`4c708`)
- `4c708`: `MOVE.L d0, 5c92(a5)` (→`4c70c`)
- `4c70c`: `MOVE.L d1, d7; BPL.W 4c714` (→`4c712`)
- `4c712`: `NEG.L d7` (→`4c714`)
- `4c714`: `MOVE.L 5c96(a5), d6; BPL.W 4c71e` (→`4c71c`)
- `4c71c`: `NEG.L d6` (→`4c71e`)
- `4c71e`: `CMP.L d7, d6; BCC.W 4c728` (→`4c724`)
- `4c724`: `MOVE.L d1, 5c96(a5)` (→`4c728`)
- `4c728`: `RTS ` — FLOW

**`28ae` 자식 callback `4cf52`(N33 `4c37c`) 4**
- `4cf52`: `JSR 288c.l` — FLOW
- `4cf58`: `BCS.W 4cf62` (→`4cf5c`) — C 소비, FLOW
- `4cf5c`: `JMP 2a00.l` — FLOW
- `4cf62`: `RTS ` — FLOW

**슬롯 판정 `4d8d8` 5**
- `4d8d8`: `MOVE.L a6, d0; CMP.W 5cba(a5), d0; BNE.W 4d8ea` (→`4d8e2`)
- `4d8e2`: `MOVEQ #0, d0; MOVE.B 5ce1(a5), d1; RTS `
- `4d8ea`: `CMP.W 5ce6(a5), d0; BNE.W 4d8fa` (→`4d8f2`)
- `4d8f2`: `MOVEQ #1, d0; MOVE.B 5d0d(a5), d1; RTS `
- `4d8fa`: `MOVEQ #ff, d0; MOVEQ #0, d1; RTS `

**지형 호출 `ea680` 4**
- `ea680`: `JSR 1abda.l` — FLOW
- `ea686`: `BCS.W ea68c` (→`ea68a`) — C 소비, FLOW
- `ea68a`: `RTS ` — FLOW
- `ea68c`: `MOVE.L 42(a6), d0; MOVE.L 46(a6), d1; MOVEA.W #0, a0; MOVEQ #8, d7; BRA.B ea65a`

**u08b 두 번째 진입(결정 4; u08b 실행부 안에서 나눔)**
- `4bc44`: `CLR.B 549f(a5); CLR.B 54a0(a5); MOVE.B #ff, 54a2(a5); MOVE.B #ff, 54a3(a5)` (→`4bc58`)
- `4bc58`: `MOVE.B #0, 549d(a5); MOVE.B #0, 549e(a5); MOVE.B #2, 549c(a5); BTST.B #4, 15(a6); BEQ.W 4bc7a` (→`4bc74`)

## 작업자 검증 기록 (scratch, 커밋하지 않음)

Claude Opus 5.5 / high 작업자, 작업 트리 `/Users/start/Workspce/metalslug-n35`(기준 `e7c6972`), scratch `/Users/start/Workspce/ms5-scratch/n35/`. ROM SHA256 `29112a94…860f`·mtime `1791291625`·크기 8,388,608 불변.

- 산출: `engine/src/animation_machine_objects_n35.cpp`, `engine/tests/animation_machine_objects_n35_test.cpp`, `engine/src/animation_machine.cpp`(routing `else if` 1개 + carry 목록 group 1개), `engine/src/animation_machine_internal.h`(선언 1줄), `Makefile`(source·test target·run 줄), `tools/verify_animation_machine.py`(SOURCES). 결정 4: `engine/src/animation_machine_objects_u08b.cpp`(`4bc44`/`4bc58` 분리), `engine/tests/animation_machine_objects_u08b_test.cpp`(BLOCKS `4bc44` 행 갱신 + `4bc58` 행, fixture `4bc58-*` 4개, 수 166/588, key fact), u08b 계약.
- [F] `make -j3 all test`: exit 0, warning 0, `Assert` 줄 0.
- [F] N35 test(run_animation_machine만): fixture 170(checked 오류 13, kept C 24), block 26 × C 3(소비 2는 Unknown에서 정확한 오류), zero-step 26 × 3, 내부 PC 46 전부 `unsupported animation objects n35 PC`, 범위 끝 홀수 PC, RAM 탐침 rollback, 경계 stop 4(`288c` `2a00` `1abda` `ea65a`), RTS rollback 9. 생성기: Unicorn 고정 ROM(합성 바이트 없음, 모든 data 읽기 검사), fixture가 26 시작 전부를 덮음. known C 확인 3건(`ea680` → `1abda` Clear → `ea68a`를 N29 `30dfa BCC.W` 복귀 LONG으로 둔 native 분기 = 모델; Unicorn SR 미사용).
- [F] u08b test: 같은 scratch 생성기(`u08b/gen_u08b.py`)가 기존 BLOCKS 165행과 성공 fixture 231개를 바이트 단위로 재현한 뒤 새 시작 집합에서 바뀌는 행이 `4bc44` 하나임을 확인했다. 242 fixture, 166 block 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`): N35·u08b·N33 test 통과, runtime error 0.
- [F] 돌연변이 31개 전부 검출(N35 24, u08b 분리 7: `4bc44` 후속, `4bc58` 쓰기 값·누락·분기, 분리 되돌림, `4bc58` case 없음). 첫 test 생성에서 `NEG.L`을 절댓값으로 잘못 구현한 것이 직접 진입 fixture(`4c6f6` 양수 D7)로 검출되어 고쳤다.
- [F] 실제 ROM 차등(8개 `program_rom_*.ms5d`, bank 200000/300000, Unicorn vs C++; N35 26 + u08b 166 시작): seed 1·2·3 각 4,000 case, 불일치 0, 192 시작 전부 도달(`4bc58` 포함), 소비자 실제 생산자 뒤 native 분기 비교(seed 1: `4cf58` 321, `ea686` 346, `30dfa` 185). 의도된 차이(seed 1/2/3: 21/20/13, 모두 u08b `46372` 계열 진입): 무작위 D7으로 계산 점프 `44ade`(U20)·`45176`(U11)·`45798`(U15b)·`4483a`(U08a)가 표 entry 밖에 착지해 C++가 checked 오류(F1 결정 3)를 낸다. seed 2의 1건은 Unknown C 진입이 U11 소비자에 닿은 기존 의도된 차이다. Unicorn 내부 abort 시도는 skip(12/12/21, 같은 seed 재생에서 고정 목록).
- [F] 기준 frame pass(`verify_animation_machine_scheduler_f4.py` 복사본, OUT scratch): 기준 `e7c6972` 14,648 pass / 126,694 node 일치 → N35 14,650 / 126,740, 불일치 0. 첫 미routing 목록에서 `4cf52` 2가 `2b96c` 2로 바뀜.
- [F] RNG 400 frame(`verify_animation_machine_scheduler_rng_f4.py` 복사본): 기준 134 완주 / 53,600 pass / 403,683 node / 불일치 0 → N35 134 완주 / 53,602 pass / 403,729 node / 불일치 0, checks 모두 참. 새 완주 seed 없음.
- [F] **seed 116 117 멈춤 위치**: 기준 frame 0 node 7(callback `4cf52`, A6 `1014b8`) → N35 + `4bc58` 뒤 frame 0 전체 일치(node 23개 추가, 자연 TB `4bdfe`→`4bc58` 경로 포함), frame 1 node 7(callback `2b96c`, A6 `1011a8`, 첫 미routing PC `4c3de` = N34 범위 `4c3de..4c6f0`)에서 멈춘다. [I] 완주는 N34 이후에야 가능하다(재범위 예측 136은 N34까지 전제).
