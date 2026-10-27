# 영역 C 단위 C2(플레이어 객체 `1d1f4` 본체 앞부분: `1d222` 상태와 `1ed78`/`1edb0` 상태 머리, 196 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §4.2의 C2 행과 아래 "C2 상세 명세"(계획 §8과 같은 꼴, 이 계약에서 새로 씀)를 기준으로 삼고, 구조·공통 규칙은 C1 계약(`animation-machine-player-c1-contract.md`)과 FR9 계약을 따르며 다른 점만 적는다. 단위 이름은 C2, 파일 접두어는 `player_c2`(C++) / `pc2`(V1 spec)다(계획 메인 결정 7). 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기는 없다(`22(A6)`가 bank 창 주소를 담으면 그 LONG 표 읽기가 bank를 읽는다: live bus). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `6308f75`(branch `claude/c2-core`; C1 `ff2e284`, E1 `6308f75` routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `565880ca271b7cff4fabe49c3d386553f46ec9d18b1965e30f02318cabec22c5`, `animation_machine_internal.h` `9a80738e3a1b1fbc8dc9782331426daf2406f2706d8cc86af2a2bed1b0c58a32`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/P1/068.pack.gz` `094.pack.gz` `106.pack.gz`, `boot-title-start/boot.pack.gz`, `boot-demo-0/boot.pack.gz`)와 계획의 보정 관측 `ms5-scratch/c1/reobs/`(실행 집합 측정용, 계획 메인 결정 1; 읽기만).
- [F] 시작 목록: 계획 scratch `ms5-scratch/c2/starts_C2.txt`(196개, SHA256 `c8e7313e2d71813c55be336edb79969d6c3ebc81d82b6abc012861026ef005a3`, 계획 §6 표의 `c8e7313e2d71813c`와 같음). 실행부의 `case` label 196개와 집합이 같다(작업자 확인).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c2/`
  - `remeasure/`(재측정: `keydump_old.py`, `remeasure2.py`, `r2.json`, `r2_C2.txt`), `plan/udetail_C2.txt` `plan/C2.dis.txt`(범위·출구·역어셈블), `work/callers_c2.py`(진입 호출자와 호출 뒤 명령), `work/natsearch.py`(IO pack 자연 node 검색), `work/v1_*`(V1), `mut/`(변이), `realrom/`(실제 ROM 차분).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정 전**(`MS5_REOBS=…/c1/reobs dleft.py`, routing `565880ca…` = C1+E1 routing): 실행된 routing 밖 PC C **757** / E **12** / D 0, 예측 일치 frame **169,144**, 첫 정지 영역 C 14. 계획 §4.2의 E1 뒤 값과 같다.
- [F] **closure 재측정(C1+E1 routing 상태)**: 계획 spec `plan/plan_final.json`을 그대로 쓰고, 단위 key(각 run의 첫 C·E frame 기준 상대 frame)는 계획 당시 routing(`7233eefc…`, git `04ec345`의 `animation_machine.cpp`)에서 뽑은 값으로 고정했다(`remeasure/keydump_old.py`). 그 key로 현재 routing에서 `cplan3`을 돌린 결과(`remeasure2.py`): **C2 = 196 block, 468 명령, 1,968 byte, 시작 목록 SHA `c8e7313e…`(계획과 같음)**, 예측 169,144(+0), 남은 C 659 / E 12. 전체 검사 `starts_equal true, insns_equal true, missing_exec []`. C3~C13의 시작 목록 SHA도 계획 §6 표와 같다.
  - [F] 주의: key를 현재 routing에서 다시 계산하면(`remeasure.py`, E1 때 쓴 방식) 각 run의 "첫 C·E frame"이 C1·E1 routing 때문에 +190 근처로 밀려 창 `[C, 0, 99]`(C1)이 C2·C3 실행 PC를 잡는다(C1 652 block으로 나옴). 단위 소속은 계획 key로 정해진 것이므로 계획 key를 고정해 재측정했다. 차이는 없다.
- [F] **정적 범위**: 28 범위, 1,968 byte(이어 붙인 SHA256 `cb9b521c539a4c3ef5661b71cf4474a43224e28e55023f11b32eb9e6b27df97e`), 짝수 PC 984(내부 788), 시작 196. 범위 안에 기존 routing된 PC는 없다(closure가 routing된 PC에서 멈춤; `make test`의 내부 PC 788개 검사가 모두 C2 오류로 거부됨을 확인).
- [F] **예측**(계획 §4.2): C2 뒤 C 남은 실행 PC 757 → 659(−98: 실행된 C2 PC 98개, 그중 block 시작 94개), 예측 일치 frame **169,144 그대로**(+0), 첫 정지 C 14.

## C2 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **196 block, 468 명령, 1,968 byte, 28 범위.** 시작 목록 SHA256 `c8e7313e2d71813c55be336edb79969d6c3ebc81d82b6abc012861026ef005a3`. 범위 byte를 이어 붙인 SHA256 `cb9b521c539a4c3ef5661b71cf4474a43224e28e55023f11b32eb9e6b27df97e`.

| 범위(CPU = 파일 오프셋) | byte | SHA256(앞 16자) | 시작 | 내용 [I] |
| --- | --- | --- | --- | --- |
| `1a9e8..1aa3a` | 82 | `e9fa965191708ab3` | 8 | helper `1a9e8`: `6e` = 6, LONG `5434(A5)` ≠ 0, LONG `3e(A6)` ∈ map 4개면 `JMP (A1)` |
| `1c1e2..1c1f4` | 18 | `f1c64e2541a94a83` | 1 | BYTE `9f` := BYTE `a0`, BYTE `9e` := 표 `1c1d8[a0]` |
| `1cab6..1cafe` | 72 | `c27bb75a09070c7c` | 7 | 기록 WORD 표(A0) → LONG 표 `22(A6)` → 해석기 `49f96`(A0 = `26(A6)`/`94(A6)`) |
| `1cb08..1cb1a` | 18 | `22b3c67d3a30572e` | 2 | 기록 WORD 표(A0)의 `9f` 칸 = 0이면 RTS(C Clear) |
| `1cd12..1cd94` | 130 | `d7cf99dd5dca8e67` | 13 | 상자 판정(`5474(A5)`, `53a2/53a6/5470/5472(A5)`) → D0 bit |
| `1cd98..1cde0` `1cdea..1cdf0` | 72 + 6 | `b540f552c2c86c40` `ad944108ef2dbf2b` | 8 | 입력 요약 `1cd98`(`49be0` 입력 WORD) 앞부분 |
| `1cdfe..1ce98` `1cea8..1ceb0` `1cec0..1cec2` `1cef8..1cefa` | 154 + 8 + 2 + 2 | `727fe9793bb6dfad` `8d1ef187c427733d` `1ceeabf0c6a5a30b` `1ceeabf0c6a5a30b` | 18 | 입력 요약 뒷부분(표 `22642`, `1cd94`), RTS 2개 |
| `1d0c2..1d112` | 80 | `2be53a280cfa0c07` | 5 | 표시 ID 2개(`8ebe`)·`8cda` |
| `1d15a..1d182` | 40 | `6b7e7afef0a1286d` | 4 | `1aa3a` 뒤 LONG 표 `1d112`/`1d136` 선택 → `1d0c2` |
| `1d1d0..1d1f4` | 36 | `3c3b15812dd335d9` | 5 | `48384`(C3)의 C, `28ae` 자식 `361e4` |
| `1d222..1d398` | 374 | `2b2ca943194eb1be` | 22 | 플레이어 상태 시작(node 초기화, 자세 D0, `e8b5a`/`ea5f0`/`2986` 자식 `6f1c4`) |
| `1d45a..1d468` | 14 | `a828b393d550b212` | 2 | 설치 `1d466`(RTS) |
| `1d582..1d5ac` | 42 | `30c7a281f654e035` | 7 | `43e34`, `4836e`·`49c38`의 C, `49c20` |
| `1dbd8..1dbf0` | 24 | `001ce2c054f1cf97` | 4 | `1aa3a` 뒤 D0 & `c8` |
| `1ddd0..1ddd8` `1ddfc..1de3c` | 8 + 64 | `305e254670941543` `fae5011a8f7252ca` | 9 | 상태 `1ddd0`(→ `1ed78`, 또는 C10 `1e21c`/`1e8de`) |
| `1dfe6..1e01a` | 52 | `5674db79d25f09f5` | 6 | BYTE `a2` 포화 증가, `49a58`, SUB.W의 borrow를 C로 돌려줌 |
| `1ed34..1ed70` | 60 | `70489f480ea89dc9` | 9 | C를 넘기는 판정(호출자 `1ee00`(C3)/`1efb0`(C11)), LONG `1ed70`/`1ed74` → `1cb08` |
| `1ed78..1ee00` | 136 | `c04a1d3026726195` | 15 | 상태 머리 `1ed78`/설치 `1edb0`(IO run의 자연 callback) |
| `1eee0..1eeea` | 10 | `673b82cf54b5fc2b` | 1 | `1ebbe`(C6)로 |
| `1f1d8..1f2a4` | 204 | `aeb1283e26a1593b` | 21 | 상태 `1f1d8`/설치 `1f224`(속도 감쇠 ASR.L #5) |
| `1f7a4..1f810` | 108 | `01d51faecb401eb9` | 11 | 상태 `1f7a4`/설치 `1f7da` |
| `1fa3c..1fa68` `1fa90..1fafc` | 44 + 108 | `441e61c366f7c29d` `9e5f514c5903ecef` | 18 | 상태 `1fa3c`/설치 `1faaa`, `1fae8` 쓰기 |
| 합계 C2 | 1968 | 이어 붙인 바이트 `cb9b521c…` | **196** | 짝수 PC 984(내부 788) |

- [F] **진입(실행된 PC를 줄인 closure 진입, `udetail.py C2`)**: `1a9e8` `1c1e2` `1cab6` `1cabe` `1cb08` `1cd12` `1cd98` `1cdfe` `1cef8` `1d0c2` `1d15a` `1d1d0` `1d222` `1ed34` `1dfe6`. 실행된 시작 94개, 실행되지 않은 시작 102개(`1edb4..1edf6`의 분기 쪽, `1f1d8..`, `1f7a4..`, `1fa3c..` 상태 대부분).
- [F] **호출자**(ROM 전체 직접 분기 검색, `work/callers_c2.py`): `1a9e8` ← `201a8 JSR`(C3); `1d222` ← C1 `1d21c BCS`, `1eb94 BRA`(C6); `1cdfe` ← `1cdf6 BCS`(C7); `1cb08` ← 15곳(이 단위 `1ed7c` `1fa40` `1ed6c BRA`); `1cab6` 29곳·`1cabe` 19곳; `1cd98` 60곳; `1ed34` ← `1ee00`(C3) `1efb0`(C11); `1dfe6` ← `1e27a`(C10) `1ee12`(C3). 이 단위 밖의 호출은 모두 뒤 단위 코드다.
- [F] **설치 값**(MOVE.L `#v,(A6)`): 곧바로 들어감 `1d466`(`1d460`) `1edb0`(`1edaa`) `1f224`(`1f21e`) `1f7da`(`1f7d4`) `1faaa`(`1faa4`). **쓰기만**: `1f29a` → `1ed78`, `1f806` → `1f810`(C8 범위 밖, 미실행), `1fac8` → `1fae8`. 그 뒤는 `BRA 201a2`(C3).
- [F] **둘째 callback 칸 `84(A6)`**(계획 결정 2·8): `1d246` `1d26a` `1f206` `1f7ac`가 LONG `84(A6)` := `21602`(C3 시작)를 쓴다. 이 단위는 쓰기만 하고 `201a6 JSR (A4)`(C3)가 그 값으로 들어간다.
- [F] **자식**: `1d1e2 MOVEA.L #361e4,A0; JSR 28ae`(`28ae` 자식 `361e4`, C3에서 routing), `1d352 MOVEA.L D7,A0`(= `6f1c4`)`; MOVEA.L #100bf4,A1; JSR 2986`(`2986` 자식 `6f1c4`, 이 단위는 넘기기만 함).

### 계산 점프와 표

- [F] **BRA.W 계산 점프 표: 없음**(계획 §4.1 표의 다섯 표는 모두 C3·C5·C7).
- [F] **live `JMP (A1)` `1aa38`**(유일한 간접 분기). A1 = LONG `5434(A5)`(`1a9f2 MOVEA.L 5434(A5),A1`; 0이면 `1aa2a RTS`). 들어가는 조건: BYTE `6e(A6)` = 6, A1 ≠ 0, LONG `3e(A6)` ∈ {`109156`, `10b1d6`, `10d256`, `10d2d6`}. D4.W := WORD `2e` ASR 4, D5.W := WORD `32` ASR 4를 넘긴다 [I: 좌표 ÷ 16].
  - [F] `5434(A5)`에 쓰는 명령은 ROM 전체에서 두 개뿐이다(`MOVE.L/CLR.L …,5434(A5)` 바이트 검색): `1a610 CLR.L 5434(A5)`(stage 초기화, `stage-startup.md`)와 stage script opcode `4c`의 처리기 `1a16e MOVE.L (A1)+,5434(A5)`(script placement U5). `scene-command.md`는 opcode `4c`의 canonical script 출현이 0이라고 기록한다. [I] 따라서 ROM 자료로는 A1이 늘 0이고 `1aa2c`/`1aa38`은 ROM이 만드는 상태에서 실행되지 않는다. 보정 관측에서도 `1a9f2` 이후는 실행되지 않았다(`1a9e8`·`1aa2a`만 실행 TB 시작).
  - **결정 2**(아래): PC := A1(32 bit, live 대상; FR1 결정 4의 `JMP (An)` 관례). 문서화된 대상 집합은 "routing된 block 시작"이다. 그 밖의 대상은 모두 checked 오류다: routing 밖(RAM·C3 `1ee00`·24 bit 밖 `1001c1e2` 등) → 다음 dispatch의 `unsupported animation machine PC`, 다른 실행부 block의 내부 PC → 그 실행부의 PC 오류(C2 내부면 `unsupported animation player c2 PC`), 홀수 → `unaligned animation machine PC`. 실행 전체가 rollback된다.
- [F] 읽는 고정 ROM 자료(live bus, 상한 검사 없음; 원본도 표 뒤의 바이트를 읽는다): BYTE 표 `1c1d8 + D0.W`(D0 = BYTE `a0`, 0..ff), `22642 + D1.W`(D1 = BYTE `4(A4)`), `1cd94 + D1.W`(D1 = BYTE `9e`), LONG 표 `1d112`/`1d136 + 4 × BYTE 9f`, LONG `1ed70`/`1ed74`, 그리고 호출자가 A0로 넘기는 기록 WORD 표(`1b230` `1b6c4` `1b34a` `1b716` `1b72e`, `1bcc2`/`1bcc4`는 C5 `1cb38`로 넘기기만). `1caea`의 `1cafe`는 해석기에 넘기는 기본 script 포인터다.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `28ae` `2986` `8cda` `8ebe` `8ff4` `ce02` `1aa3a` `1c1f4` `1d198` `43e08` `43e34` `4836e` `49a58` `49be0` `49c20` `49c38` `49f96`(`1caf8 JMP`) `49fc6` `4be82` `4bfc0` `4c0ea` `ea5f0`.
- [F] **뒤 단위 정지**(실행되지만 뒤 단위가 가짐, routing 밖; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`):
  - C3: `1ee00`(`1edf6` fall-through), `201a2`(`1f2a0`/`1f80c`/`1face BRA`), `48384`(`1d1d0 JSR`), `e8b5a`(`1d314 JSR`).
  - C4: `1ceb0`(`1cea8` fall-through), `1cec2`(`1f7de BSR`), `1eeea`(`1edf6 BNE`).
  - C5: `1cb1a`(`1cb08 BNE`), `1cb38`(`1f1f8 BSR`).
  - C6: `1d398`(`1d390` fall-through), `1ebbe`(`1eee0 BRA`).
  - C7: `1cde0`(`1cdd8` fall-through), `1cdf0`(`1cdea` fall-through), `1f2a4`(`1ede6 BNE`).
  - C8: `1ce98`(`1ce80` fall-through), `1cfde`(`1fa4c`/`1fac4 BSR`), `1fa68`(`1edd8 BNE`), `1fafc`(`1fa64 BRA`, `1faf8 BSR`의 복귀 PC).
  - 미룬 입구(나머지 단위): `1de3c`(C9, `1d38c BEQ`), `1e21c` `1e8de`(C10, `1de2c`/`1de34 BNE`).
  - [I] 이 가운데 fall-through(직선 다음 PC)는 `1cde0` `1cdf0` `1ce98` `1ceb0` `1d398` `1ee00`이다. V1 `first_unrouted`는 직선 다음 routing 밖 PC를 다른 실행부 block의 내부로 보고 지나가므로 선언 정지가 필요하다(C1 결정 6과 같음).
- [F] TRAP 없음. ROM·RAM 실행 없음.

### block 경계를 넘는 flag(결정 3·4)

scratch `cscan.py starts_C2.txt`와 호출자 검색(`callers_c2.py`)으로 정했다. Z/N을 block 경계 너머에서 읽는 C2 block은 없다(`BEQ`/`BNE`는 모두 같은 block의 `BTST`/`BSET`/`BCLR`/`TST`/`CMPI`/`AND` 뒤). X 소비(ADDX/SUBX/ROX) 없음.

- [F] **C 소비 block 8개**(Clear 쪽 / Set 쪽; Unknown C면 `player c2 caller requires known carry`):
  - `1d1d6 BCS.W 1d1f2`: `1d1d0 JSR 48384`(C3)의 C. Clear → `1d1da`, Set → `1d1f2`. **routing된 생산자가 없다**(C3 뒤에 실제 사슬).
  - `1d58e BCC.W 1d5aa`: `1d588 JSR 4836e`(input 실행부: BTST #2,`5683(A5)`; bit set → `48378` ANDI(Clear), clear → `4837e` ORI(Set)). Clear → `1d5aa`, Set → `1d592`.
  - `1d59c BCS.W 1d5aa`: `1d592 JSR 49c38`(FR6). Clear → `1d5a0`, Set → `1d5aa`.
  - `1ed80 BCC.W 1ed8e` / `1fa44 BCS.W 1fa90`: `BSR 1cb08`(이 단위)의 C. `1cb08`은 `MOVE.W (A0,D7.W),D7`로 C를 지우고 `BNE`(C 불변)로 `1cb1a`(C5) 또는 `1cb18 RTS`로 간다. 이 단위 안에서는 Clear 쪽만 실제 사슬이다(Set 쪽은 C5 `1cb1a` 경로가 정함).
  - `1f296` `1f802` `1fac0 BCC.W`: `JSR 49fc6`(해석기, known C). Clear → `1f2a0`/`1f80c`/`1face`(BRA `201a2`), Set → `1f29a`/`1f806`/`1fac4`.
- [F] **C 생산 block**(자기 block에서 C를 정함, `carry_preserving_pc`에 넣지 않음): `1cb08`(MOVE.W → Clear), `1dff0`·`1ed54`(`ANDI.B #fe,CCR; RTS` → Clear), `1edf6`(`AND.W D0,D1` → Clear; C3 `1ee00 BSR 1ed34` → `1ed3c RTS` → `1ee04 BCS`가 읽는 C), `1e016`(`SUB.W D1,D0; RTS` → borrow = 무부호 D0.W < D1.W; 호출자 `1ee16 BCC`(C3), `1e27e BCS`(C10)).
- [F] **C 통과 block 5개**(들어온 C를 그대로 둠, `carry_preserving_pc`에 넣음, Unknown도 그대로 통과): `1cb18 RTS`(`1cb08`의 Clear를 `1ed80`/`1fa44`에 넘김), `1ed34`(`BTST #4,D0; BNE`), `1ed3c RTS`, `1ed3e`(`BTST #0,a7(A6); BNE`), `1ed48 RTS`. `BTST`는 Z만 바꾸므로 `1ee00`/`1efb0`(뒤 단위)이 호출 전에 가진 C가 그대로 돌아간다.
- [I] 다음 단위로의 전달(이 단위가 하는 일): `1ee56 BNE`(C3)는 `1cb08`이 `1cb18 RTS`로 돌아올 때의 Z를 읽는다. 그 경로의 Z는 늘 1(`MOVE.W`의 결과 0이라 `BNE`가 안 갔음)이다. C3가 C1 결정 3(RAM에서 다시 계산, 아니면 checked 오류) 또는 정적 상수로 정한다. 이 단위는 Z를 운반하지 않는다.

### IO 실행 run과 frame

- [F] 보정 관측(계획 당시 routing으로 셈, `remeasure/tools_old`): C2 PC를 실행하는 run 14개(P1 12, boot-title-start, boot-demo-0), 실행된 C2 PC 98개(시작 94), 실행 78,634회.
  - P1 94 95 100 101 106 107 110 111: frame **192~193**(각 5,861회). P1 68~71: frame **408~409**(5,628회). boot-title-start: **312~313**(5,861회). boot-demo-0: **381~382**(3,373회, PC 95개).
  - node: 플레이어 기록 `100cb8`(C1의 `4e91c`가 `2a28`로 만든 node). frame 192에 C1 callback `1d20c` → `49bca` → `48346` → `48350`(C3, Set) → `1d21c BCS` → `1d222`(C2) → … → `1de38 BRA 1ed78` → `1ed96`이 `1edb0`을 설치하고 바로 들어간다. 그 뒤 frame(193~218, 409~434, 313~338, 382~383)에는 `1edb0`이 node `100cb8`의 callback이다(`work/natsearch.py`).
- [F] **IO 예측(C2만 연결)**: 169,144 → **169,144**(+0). C2 연결 뒤 첫 정지 frame은 그대로(192/408/312/381)이고, 그 frame의 첫 routing 밖 PC 후보에 `48350`(C3, `1d21c`보다 먼저 실행), `48384` `e8b5a` `1ee00` `201a2`(C3)가 있다(`dstate`). [I] 실행 순서상 `48346`의 Set 쪽 `48350`(C3)이 `1d222`보다 먼저 오므로 IO 비교에서 C2 코드는 C3 연결 전에는 실행되지 않는다. C2와 C3을 한 묶음으로 IO 확인한다(계획 결정 9).
- [F] D1 자연 seed 137개와 P0 run은 C2 코드를 실행하지 않는다.

### 영향받는 기존 시험·검증기

아래 "영향받는 기존 시험·검증기" 절에 이전 값·새 값·이유를 적었다.

## 공통 규칙·native 검증 계획

FR2..FR9, C1 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c2.cpp`, 함수 `animation_player_c2_block`. 오류 문자열은 `unsupported animation player c2 PC`(범위 안 내부 PC 직접 진입)와 `player c2 caller requires known carry`(C 소비 block에 Unknown C; 소비자 8개) 두 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다(`JMP (A1)`의 대상 오류 포함, 결정 2).
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(28 범위, E1 줄 뒤), `carry_preserving_pc`의 E1 주석 뒤에 주석 달린 case 묶음 하나(소비자 8 + 통과 5), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **routing 원자 `1dc84`/`1dc8a`/`210ae`/`210b4`(계획 §2).** C2 범위에 들어가지 않고, C2 block이 그 PC로 가지도 않는다(출구 목록에 없음). **바꾸지 않는다.** 옛 동작 = 새 동작: `1dc84`/`210ae`는 `JSR 49fc6`(복귀 `1dc8a`/`210b4`), `1dc8a`/`210b4`는 해석기의 C로 `1dccc`/`1dc8e`, `21564`/`210b8`를 고르는 interpreter 실행부의 단일 PC stub이다(`animation_machine_interpreter.cpp` 160~164, carry 목록 첫 줄). [F] 재측정 계획에서 `1dc84`의 바로 앞 `1dc70..1dc84`는 C6, `21564`는 C6 시작이다. [I] 그 원자를 둘러싼 함수 closure(계획 §2의 가려진 1,911 명령)는 C2~C13이 나눠 가지며, 원자 자체는 interpreter 실행부에 남겨도 단위 실행부와 경계가 맞는다(C2 시험 `interior()`가 원자 4개가 C2 범위 밖임을 확인).
- **설치 값.** `MOVE.L #v,(A6)` 뒤가 곧 v인 곳(`1d460` `1edaa` `1f21e` `1f7d4` `1faa4`)은 v로 들어간다. `1f29a` `1f806` `1fac8`은 LONG만 쓰고 `BRA 201a2`(C3)로 간다.
- **자료 읽기**(live bus): node field(A6), LONG `8c(A6)`(A4; 기록 [I])의 BYTE `2` `3` `4` `7`, WORD `8` `a`, LONG `22(A6)`(1cad4의 LONG 표; bank 창이면 bank 읽기), LONG `3e(A6)`(map buffer 비교만), A5 기준 LONG `5434` `5474`, WORD `53a2` `53a6` `5470` `5472`, 절대 BYTE `10f001`(`1f1d8`), 스택 LONG `(A7)`(`1d0ca` 읽기만, `1d0e0` pop), 그리고 고정 ROM 표(위 "계산 점프와 표"). 단위 시험은 고정 ROM 표 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름: 기록 WORD 표 `1b230` `0000 0004 0000 0006`, `1b34a`, `1b6c4` `0008 0000 000a 000c | 0001 0002 0000 0003`, `1b716`, `1b72e`, BYTE 표 `1c1d8` `05 01 03 07 02 06 04 00 09 08`, `1cd94` `7f bd 0f f0`, `22642` 16 byte, LONG 표 `1d112`/`1d136`(work RAM `10e800 + 20 i` / `10e900 + 20 i`), `1ed70`/`1ed74`(`10e840` `10e860`)). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W/.B`, `ADD.W`, `ANDI.W`, `ORI.W`, `SUB.W`, `SUBI.W`, `AND.B`, `EOR.B`, `SEQ/SMI/SCS.B`). `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`SUB.L`·`ADDI.L`·`ASR.L`은 LONG 전체. `ADDQ.W #4,A0`는 주소 레지스터라 LONG 전체. `MOVEA.W #0,A1` = 0(부호 확장). `CMPA.W #0,An`은 An 전체를 0과 비교. `LEA (A0,D7.W)`·`(A0,D7.W)`·`(d,PC,D0.W)`·`(A3,D1.W)`의 색인은 부호 확장 WORD. 비교: `CMP.W (A0)+,D2/D3` + `BCS`(무부호 WORD), `CMP.B 3(A4),D2` + `BCS`(무부호 BYTE), `CMPI.B #78,92(A6)` + `BCC`(무부호 BYTE ≥ 78), `SUBI.W #1e,D1` + `BCC`(빌림 없음 = BYTE ≥ 1e), `SUB.L 36(A6),D2` + `BMI`(LONG 부호), `CMPI.W #0/#1/#4,D7`(WORD). bit: `BTST/BSET/BCLR #n,d(An)`·`10f001.l`(memory BYTE, n mod 8), `BTST #n,Dn`(LONG bit n: `1d2fc`의 `#a`는 bit 10), `BSET Dn,60(A6)`(bit = D0 mod 8). `ASR.W #4`(부호 복사, 상위 WORD 유지), `ASR.L #5`. `ADDQ.B #1` + `SCS.B D0` + `OR.B D0,a2(A6)` = `ff`에서 포화(OR는 메모리를 다시 읽는다). `EXG A0,A1`.
- **스택.** `1d0c2`가 LONG A0를 push하고 `1d0ca`는 `(A7)`를 읽기만, `1d0e0`은 pop한다(사이에 `JSR 8ff4`/`8ebe`). `1d326`이 WORD D7을 push하고 `1d380`이 pop한다(사이에 `JSR ea5f0` 등).

## carry(결정 3·4)

- [F] 소비자 8개·통과 5개·생산자 5개는 위 명세와 같다. dispatcher는 `carry_preserving_pc`에 없는 PC로 갈 때 C를 Unknown으로 만든다. 따라서 이 단위의 C 의미는 (1) 소비자가 known C를 읽고 그대로 둔다, (2) 통과 block이 들어온 C를 그대로 둔다, (3) 생산자가 자기 block에서 C를 정한다, (4) 나머지 block 뒤 C는 Unknown이다.
- [F] `1edf6`의 Clear는 이 단위의 소비자가 읽지 않는다. 원본 C와 같고(V1 carry oracle이 known tag를 native C와 대조), C3가 `1ee00`을 통과 목록에 넣으면 그대로 쓰인다.
- [F] `1e016`의 C(borrow)는 데이터에 따른다. 단위 시험은 native 출력 레지스터에서 다시 계산한 값(D0.W(후) + D1.W ≥ 10000)으로 행의 기대 C를 정한다.

## 경계·routing 밖 출구

- [F] 이 단위 안의 간접 분기는 `JMP (A1)` `1aa38` 하나(결정 2). `RTS`로 끝나는 block 14개(+ `1dff0` `1ed54` `1e016` `1d10a` `1c1e2` `1cd7c`의 RTS).
- [F] **native 정지 규칙**(V1): FR9·C1 spec의 `first_unrouted`에 C2 뒤 단위·미룬 입구 21곳(`EXIT_STOPS`)을 선언 정지로 더하고, `JMP (A1)` 직후 PC가 C2 시작이 아니면 그 PC에서 멈춘다(C++의 dispatch가 그 PC에서 checked 오류이므로 같은 stop에서 양쪽이 멈춘다). 실제 ROM 차분은 같은 21곳을 `UNR`로 두고, `1aa38` 착지를 trace 전체에서 추적해 분류한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR9·C1 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: 그 node(A6)에 선언 편집(레지스터; LONG `c(A6)` `8c(A6)` `22(A6)` := 자연 node, LONG `3e(A6)` := map buffer 4개 또는 node; LONG `5434(A5)` := 0 / `1c1e2` / `1ee00` / `1ce0e`(ROM만: native는 work RAM에서 명령을 가져오지 않는다), LONG `5474(A5)` := 0 / node; A1 := ROM 대상).
- **IO pack 자연 node 상태(family `natural`)**: node `100cb8`의 callback이 `1edb0`인 frame-start 상태 14개(P1 094 193 194 200 218, P1 068 409 410 434, P1 106 193 205, boot-title-start 313 314 338, boot-demo-0 382 383), 레지스터만 선언(A5 := `108000`, A6 := `100cb8`, A7 := `10ef00`(복귀 LONG = sentinel), PC := `1edb0`). [F] 자연 실행은 `1cd98` → `49be0` → `1cdba` → `1cdea` → `1cdf0`(C7) 등 뒤 단위 정지에서 멈춘다.
- **재설치 world(family `reinstall`, 11개)**: `1d222`는 C1 `1d21c BCS`의 연속이라 callback으로 남지 않는다. `1d21c BCS 1d222`가 실제로 실행된 frame의 시작 상태(P1 094 192, P1 068 408, boot-title-start 312)와 boot-demo-0 382에서 node `100cb8`에 callback LONG `1d222`를 쓰고 들어간다. 같은 방식으로 `1ed78`(192/408/312), `1f224` `1f7da` `1faaa` `1fae8`(P1 094 193). [I] boot-demo-0 381의 frame-start 상태는 `100cb8`이 아직 빈 node(callback `270e`, LONG `8c` 미설정)라 쓰지 않았다. 이미 진행된 node를 다시 시작하는 world이며 native와 C++가 같은 상태를 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `1d588` → `4836e` → `1d58e`, `1d592` → `49c38` → `1d59c`(두 C 모두), `1ed78`/`1fa3c` → `1cb08` → `1cb18` → `1ed80`/`1fa44`(Clear만; Set은 C5 뒤), `1f290`/`1f7fc`/`1faba` → `49fc6` → `1f296`/`1f802`/`1fac0`(V1에서 두 C 모두). `1d1d6`은 routing된 생산자가 없어(C3 `48384`) V1의 native 실행으로 들어가지 않는다(`GATED_CONSUMERS`; 단위 시험의 선언 C 행·실제 ROM 차분의 선언 C 진입·오류 fixture가 덮는다).
- node fixture: callback·설치 값(`1d222` `1ed78` `1edb0` `1f224` `1f7da` `1faaa` `1fae8` `1d466`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. callee fixture: `1a9e8` `1c1e2` `1cab6` `1cabe` `1cb08` `1cd12` `1cd98` `1cdfe` `1cef8` `1d0c2` `1d15a` `1d1d0` `1d582` `1dbd8` `1dfe6` `1ed34`를 subroutine으로 들어간다.
- 단위 시험(Unicorn 생성기, C1 꼴): 시작 196개(소비자 8개 제외) × 들어오는 C 3가지, zero-step, 내부 PC 788개 정확한 오류, 경계 stop(출구·뒤 단위 정지·JMP 대상 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC. 손으로 계산한 규칙(rules_a..d):
  - 부호·영 확장: `LEA (A0,D7.W)`(`fffe` → A0 − 2), `3fff × 4` = `fffc`(부호 확장 색인), `MOVE.W (A0,D0.W)`(WORD 76 = `ffff` → A0 − 2), `MOVEQ #0` + `MOVE.B`(`1c1e2` `1cda6` `1ce08` `1ce6e` `1d0f6` `1d170` `1e006` `1e014`), WORD/BYTE 대상의 상위 유지, `MOVEA.W #0,A1`, `ADDQ.W #4,A0`(LONG).
  - 비교·경계: `CMPI.B #6/#7/#5/#1/#0`, `CMPI.B #78`(77/78/ff, BYTE 92만), `CMP.W` 동점(1cd2a/1cd50), `CMP.B` 무부호(7f/80)·동점, `SUBI.W #1e`(1d/1e/ff), `CMPI.W #0,D7`(10000은 0), popped WORD 1/4/10/8001/8004, `CMPI.B #10/#11`(BYTE: `111` → `11`), map buffer 32 bit 비교(bit 24).
  - bit: BTST/BSET/BCLR의 bit 번호(BYTE 하나만), `BTST #a,D1`(bit 10), `BSET D0,60(A6)`(11 → bit 3), `BTST #2,10f001`(BYTE 10f000은 무관).
  - 산술: `ASR.W #4`(`8010` `7ff0` `fff0` `000f`), `ASR.L #5` 감쇠 5행(`36`/`3a`, BMI, `+1f`), `SUB.W` borrow 4행, `ADDQ.B` 포화(0/7f/fe/ff), `SMI`/`SEQ`/`EOR.B`, `ANDI.W #3/#ff7f/#ffef/#ffdf/#fffd/#ffbf`, `ORI.W #2/#4/#8/#40`, `AND.B` 표.
  - 기록·쓰기: node 초기화 23칸과 이웃 BYTE 유지(ff node), 설치 5개와 쓰기만 3개, slot `84` 묶음, `CLR.W 8(A4)`, `MOVE.W 78,76(A0)`, `LEA 2e(A0)`, 스택 push/pop(`1d0c2` `1d0ca` `1d0e0` `1d326` `1d380`).
  - carry: 소비자 8개 선언 C 두 값, `1cb08`·`1edf6`·`1dff0`·`1ed54` Clear, `1e016` borrow, 통과 5개가 C 0/1/2를 유지, `1d588` 사슬 두 쪽(Clear 쪽의 `1d5aa RTS` 뒤는 Unknown).
  - `JMP (A1)`: `1c1e2`(routing된 시작, RTS까지 실행), RAM `10fe40`/C3 `1ee00`/`1001c1e2` → `unsupported animation machine PC`, `1aa30` → C2 PC 오류, 홀수 → unaligned.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `565880ca271b7cff4fabe49c3d386553f46ec9d18b1965e30f02318cabec22c5` → `003b4d86868d11dce31dd6732b5c79f9c1d76e523a75110628d7d11f87c389f5`, `animation_machine_internal.h` `9a80738e3a1b1fbc8dc9782331426daf2406f2706d8cc86af2a2bed1b0c58a32` → `9bb14a08b8beafda059409ccf886f4ed1a83827b3144c6ff2234fb6fb5b92ec6`(이 단위의 공유 수정; 옛 값은 `# player C2 refresh:` 주석). 마지막 편집 뒤의 파일 SHA다.
- [F] `tools/unit_fixture_specs/pc1.py`(C1 V1 spec): `build()`의 "TRAP 자리·뒤 단위 정지는 routing 밖이어야 한다" 검사가 `1d222`(C1 `EXIT_STOPS`, 이제 C2 시작)에서 실패한다. 이전: 12곳 모두 `unit_of(t) is None`. 새: `ROUTED_LATER = (0x1d222,)`를 더해 그 PC는 routing돼도 허용하고, `1d222`는 C1 실행의 선언 정지로 그대로 둔다(native와 C++가 같은 stop에서 멈춤). 이유: C1 fixture 집합(과 C1 생성기 `ALLOWED_STOPS`)을 바꾸지 않기 위해서다. V1 pc1 1,264/1,264.
- [F] `engine/tests/animation_machine_objects_u08_test.cpp` `rom_outside`의 `1aa38`: 이 assert는 "U08 범위 밖"만 확인하므로 C2 뒤에도 참이다(`1aa38`은 이제 C2 block `1aa2c`의 내부 PC). 값은 바꾸지 않고 주석만 더했다.
- [F] 검색(`tools/*.py`, `tools/unit_fixture_specs/*.py`, `engine/tests/*.cpp`, `engine/src/*.cpp`의 16진 상수 중 C2 범위 안의 값): 위 두 곳 말고는 C1의 `1d222`(C1 시험·생성기의 출구 목록; 바뀌지 않음, `make test` 통과)와 다른 시험 자료 안의 우연한 값(`motion_walk` `select_e1` `u11` `b4b` `n04` `u15b`의 레지스터·RAM 값, `b2c` 생성기 주석의 `1d1d0` = LONG 행 범위 끝)뿐이다. `UNROUTED_NEIGHBOURS`·"no executor" 탐침에 C2 PC는 없다.
- [F] 경계가 맞닿은 범위(C1 `1d1f4..1d222` 뒤 `1d222..`, input `1d5ac..`(C2 `..1d5ac`), FR6 `1c1f4`, `1aa3a`): `make -j4 all test` 통과(경고 0), V1 회귀 pc1·se1·fr1 통과.
- [I] native 사슬이 이 단위의 PC(`1d222` `1edb0` `1a9e8` 등)를 첫 routing 밖 PC로 멈추던 V1 spec·검증기는 더 진행한다(정지는 routing에서 계산된다). 메인 runner의 회귀·legacy 단계가 확인한다.

## 결정

1. **범위.** C2 = 계획 §4.2 그대로 196 block, 28 범위(C1+E1 routing 상태에서 계획 key로 재측정해 같음). 계획 메인 결정 2·9(미룬 입구, `1ee00` 분할)를 따른다.
2. **live `JMP (A1)` `1aa38`.** PC := A1(32 bit, FR1 결정 4 관례). 허용 대상은 routing된 block 시작뿐이고 나머지는 checked 오류(routing 밖 → `unsupported animation machine PC`, 다른 block 내부 → 그 실행부의 PC 오류, 홀수 → `unaligned animation machine PC`; 실행 전체 rollback). ROM이 쓰는 A1 값은 0뿐이라([F] 쓰는 명령 `1a610 CLR.L`과 opcode `4c` 처리기 `1a16e`, opcode `4c`의 canonical 출현 0) 대상 표를 전사하지 않는다. [I] 68000은 주소 bit 24..31을 버리지만 C++는 32 bit PC로 비교하므로 상위 byte가 0이 아닌 A1은 원본과 달리 checked 오류다(ROM 자료로는 생기지 않음).
3. **RTS·통과를 넘는 flag.** Z/N을 넘겨 읽는 C2 소비자는 없다(새 Z 규약 불필요). C는 위 "carry"절대로: 소비자 8개와 통과 5개를 `carry_preserving_pc`에 넣는다. 통과 5개(`1cb18` `1ed34` `1ed3c` `1ed3e` `1ed48`)는 원본 `RTS`/`BTST`가 C를 바꾸지 않으므로 들어온 tag를 그대로 둔다(Unknown 포함; 소비자에서만 checked 오류).
4. **생산자.** `1cb08` `1dff0` `1ed54` `1edf6`은 자기 block에서 Clear, `1e016`은 borrow를 정한다(통과 목록 밖; FR 관례). `1edf6`의 Clear는 C3가 쓸 값이며 이 단위에서는 V1 oracle로만 확인한다.
5. **표 읽기.** 고정 ROM 표는 live bus로 읽고 상한을 검사하지 않는다(원본과 같음). 단위 시험은 합성 byte만 선언하므로 그 밖 색인은 `missing or ambiguous physical program bus ROM byte`로 확인하고, 원본 값은 V1·실제 ROM 차분이 비교한다.
6. **뒤 단위 정지.** C2 block이 직선·분기·호출·복귀로 닿는 뒤 단위 시작 18곳과 미룬 입구 3곳을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다.
7. **routing 원자 `1dc84` `1dc8a` `210ae` `210b4`.** C2는 바꾸지도 넓히지도 않는다(위 "공통 규칙"). 원자는 C2 범위 밖이고 C2에서 닿지 않으며, 그 원자를 쓰는 기존 시험(`animation_machine_carry_test.cpp`, `verify_animation_machine_carry.py`, `observe_animation_machine_carry.py`)은 그대로다.
8. **실행부 파일·오류 문자열.** 위 "공통 규칙". 오류 문자열 2개.
9. **다음.** 계획 순서대로 C3(`20128` `21688` `1edb0`(뒤) `361e4` …, `48350`/`48384` 포함). C2와 C3을 함께 연결한 뒤 IO 비교로 +338(169,482)을 확인한다.

## 미확인

- [U] node field·전역 값의 의미(`6e` `9e` `9f` `a0` `a2` `a5..a8` `ab` `ad` `61` `15` `7e` `92` `90` `36`/`3a`, LONG `8c` 기록, `22` LONG 표, `5434`/`5474(A5)`, `10f001`, 표 `22642` `1cd94` `1c1d8` `1d112` `1b230..`). 이름은 동작에서 붙인 [I]이다.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 102개(`1edb4..1edf6` 분기 쪽, `1f1d8..1f2a0`, `1f7a4..1f80c`, `1fa3c..1fafc` 대부분, `1aa2c` 등)는 closure로 들어왔다(V1 선언 상태·실제 ROM 차분으로만 확인).
- [U] `1d1d6`(C3 `48384`의 C)과 `1ed80`/`1fa44`의 Set 쪽(C5 `1cb1a`)은 C3·C5가 연결되기 전에는 실제 사슬로 닿지 않는다. 선언 C 행(단위 시험)과 실제 ROM 차분의 선언 C 진입만 있다.
- [U] 재설치 world와 IO pack 자연 node 상태의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1 결정·FR9 결정 5의 [I]와 같음).
- [U] C2 연결 뒤 IO 첫 정지 PC(같은 frame 안의 실행 순서). 예측은 `48350`(C3)이다. IO 비교로 확인한다.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c2.cpp`(case label 196 = `starts_C2.txt`와 집합 일치; 공용 함수 `pc2_get` `pc2_put` `pc2_bit`(BTST/BSET/BCLR memory BYTE, 옛 bit) `pc2_byte_is`(CMPI.B/TST.B) `pc2_carry` `pc2_install` `pc2_state_word`(1cac2/1cb08) `pc2_mask`(MOVE.W #m,D1; AND.W D0,D1) `pc2_shape`(MOVE.W 1e; JSR ce02) `pc2_asr4` `pc2_asr5` `pc2_add_long` `pc2_slot84` `pc2_reset`), `engine/tests/animation_machine_player_c2_test.cpp`(생성 구역 + 수작성 규칙 4묶음), `tools/generate_animation_machine_player_c2_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; 약 80초), `tools/unit_fixture_specs/pc2.py`(V1 spec; C1 spec의 공용 부분 그대로, 단위 부분 교체, `EXIT_STOPS`, `PASS_SET`, `DATA_SET`, `LATER_GATED`, `GATED_CONSUMERS`, `JUMP_PCS`, family `reinstall`). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- [F] `make -j4 all test`(작업자): 종료 0, 경고 0, Python 310 OK. C2 시험 줄: `animation machine player pc2: 999 fixtures (715 single-block, 219 path, 18 producer chain, 16 declared C, 31 checked error (11 with a later failing PC), 99 kept C), 196 blocks, 4870 calls, 177322 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 실제 사슬 `1d588`→`1d58e`·`1d592`→`1d59c`(두 C 값), Clear만 `1ed78`→`1ed80`·`1fa3c`→`1fa44`.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, C2 시험): 빌드 경고 0, 실행 종료 0, runtime error 0.
- [F] V1 pc2(작업자 1회, `--workers 3`, scratch `work/v1_pc2`): fixture 1,743개(block 821, chain 12, node 16, natural 14, reinstall 11, callee 36, error 815, failpc 8, negative 10) failed 0, 방문 시작 195/196(`1d1d6` 제외, `GATED_CONSUMERS`), 빠진 후속 0, 도달 못한 분기 결과 0, 뒤 단위 gate 4개(`(1d1d6, 1d1da)` `(1d1d6, 1d1f2)` `(1ed80, 1ed84)` `(1fa44, 1fa90)`), carry oracle Unknown/Clear/Set = 806/102/10.
- [F] V1 회귀(작업자): pc1 1,264/1,264, se1 2,102/2,102, fr1 1,631/1,631(모두 failed 0). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`, `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·BSET/BCLR, WORD→LONG, 복귀 PC, carry tag, mask)를 적용해 만든 것 + 손으로 고른 helper·block 변이 + dispatcher carry 목록 14개·범위 1개, 631개): 1회째 `killed 591 of 631`. 살아남은 40개 중 비동치 빈틈 2개 — `1cad4-noext`(`LEA (A0,D7.W)`의 부호 확장 생략)와 `1cad4-index-noext`(`MOVE.L (A0,D7.W)`의 부호 확장 생략): work RAM 표에서는 64 KiB 거울이 차이를 감춘다 — 를 고정 ROM 합성 표에서 음수 색인을 쓰는 규칙 2개로 메웠다(재실행 `killed 2 of 3`). 나머지 38개는 동치다(`mut/equivalents.txt`): `MOVEQ #0` 바로 뒤의 `MOVE.B`(상수 ^1·BYTE→LONG) 16, 색인·값이 ff(또는 1fe) 이하라 mask가 무의미 7, `pc2_put`이 BYTE로 자름 2, WORD에 OR(상위 불변) 4, `1cad4`의 D7은 뒤의 `MOVE.L`이 덮음 2, `1d22a`의 `9c` 이중 쓰기·`9d` 뒤에서 지움 2, `1e006` 동점(두 길 모두 D1 = 0) 2, `1f244`의 D2 := 0은 `SUB.L`이 덮음 1, bit 번호 이중 mod 8 2. 최종 593/631(동치 38). 전체 재실행은 결정적 runner가 한다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`), `real_pc2.py`(C1 harness에 C2 world·소비자·통과 진입·선언 정지 21곳; `JMP (A1)` `1aa38` 착지를 FR9 JMP·옛 표 JMP와 함께 trace 전체에서 분류)): 작업자 300건 3회 — seed 1 `mismatches 0`(`covered starts 175 of 196`), seed 7 `mismatches 0`(172/196), seed 8 `FOLLOW_ANIM=1` `mismatches 0`(184/196). 분류된 차이: `1aa38`이 C2 내부 PC `1ce0e`에 착지 → checked PC 오류 각 1건(결정 2), `2986` 실패 경로의 caller X(FR9의 문서화된 차이) 1·0·3건. 정지하지 않은 native(약 7%)는 건너뜀.
- [F] `dleft.py`(`MS5_REOBS`, routing `003b4d86…`): 실행된 routing 밖 PC C **659** / E **12** / D 0, 예측 일치 frame **169,144**, 첫 정지 영역 C 14. 계획 §4.2 예측과 같다(C −98, +0 frame).

## block 목록

[F] scratch `starts_C2.txt`(SHA256 `c8e7313e2d71813c55be336edb79969d6c3ebc81d82b6abc012861026ef005a3`)와 같다.

- **`1a9e8..1aa3a`(8)**: `1a9e8 1a9f2 1a9fe 1aa0c 1aa16 1aa20 1aa2a 1aa2c`
- **`1c1e2` `1cab6..1cb1a`(10)**: `1c1e2 1cab6 1cabe 1cac2 1cad2 1cad4 1caea 1caf0 1cb08 1cb18`
- **`1cd12..1cd94`(13)**: `1cd12 1cd1a 1cd1c 1cd28 1cd2a 1cd4e 1cd50 1cd56 1cd58 1cd6a 1cd70 1cd78 1cd7c`
- **`1cd98..1cefa`(26)**: `1cd98 1cda6 1cdb0 1cdba 1cdc8 1cdd2 1cdd8 1cdea 1cdfe 1ce08 1ce1a 1ce26 1ce2a 1ce34 1ce48 1ce4c 1ce50 1ce5a 1ce5e 1ce62 1ce6a 1ce6e 1ce80 1cea8 1cec0 1cef8`
- **`1d0c2..1d1f4`(14)**: `1d0c2 1d0ca 1d0e0 1d0f6 1d10a 1d15a 1d160 1d16c 1d170 1d1d0 1d1d6 1d1da 1d1e2 1d1f2`
- **`1d222..1d468`(24)**: `1d222 1d22a 1d2d4 1d2de 1d2e6 1d2f0 1d2f2 1d2fa 1d2fc 1d304 1d306 1d30c 1d310 1d314 1d31e 1d326 1d32e 1d344 1d352 1d364 1d380 1d390 1d45a 1d466`
- **`1d582..1d5ac` `1dbd8..1dbf0`(11)**: `1d582 1d588 1d58e 1d592 1d59c 1d5a0 1d5aa 1dbd8 1dbde 1dbe8 1dbee`
- **`1ddd0..1de3c`(9)**: `1ddd0 1ddd4 1ddfc 1de00 1de06 1de0a 1de28 1de30 1de38`
- **`1dfe6..1e01a`(6)**: `1dfe6 1dff0 1dff6 1e006 1e014 1e016`
- **`1ed34..1eeea`(25)**: `1ed34 1ed3c 1ed3e 1ed48 1ed4a 1ed54 1ed5a 1ed68 1ed6a 1ed78 1ed80 1ed84 1ed8e 1ed96 1edb0 1edb4 1edbe 1edc6 1edd0 1edd8 1ede2 1ede6 1edee 1edf6 1eee0`
- **`1f1d8..1f2a4`(21)**: `1f1d8 1f1e8 1f1f4 1f1f8 1f1fc 1f224 1f228 1f230 1f23a 1f244 1f254 1f25a 1f268 1f26e 1f278 1f280 1f286 1f290 1f296 1f29a 1f2a0`
- **`1f7a4..1f810`(11)**: `1f7a4 1f7ac 1f7da 1f7de 1f7e2 1f7ec 1f7f2 1f7fc 1f802 1f806 1f80c`
- **`1fa3c..1fafc`(18)**: `1fa3c 1fa44 1fa48 1fa50 1fa58 1fa90 1fa94 1faa0 1faaa 1fab0 1faba 1fac0 1fac4 1fac8 1face 1fad2 1fae0 1fae8`

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j4 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK. C2 시험 `animation machine player pc2: 999 fixtures (715 single-block, 219 path, 18 producer chain, 16 declared C, 31 checked error (11 with a later failing PC), 99 kept C), 196 blocks, 4870 calls, 177322 checks`.
- [F] `ubsan`: build/run 종료 0, runtime errors 0.
- [F] `mutation`: total 631, killed 593, equivalent 38, surviving 0.
  - `MOVEQ #0`가 `MOVE.B` 바로 앞: 16개.
  - index 또는 값이 `ff` 또는 `1fe`보다 크지 않고 음수가 아님: 7개.
  - byte 쓰기가 이미 마스킹됨: 2개.
  - low WORD에 OR: 4개.
  - 뒤따르는 `MOVE.L`이 D7를 덮어씀: 2개.
  - 중복 reset 쓰기: 2개.
  - `1e006` tie: 두 경로 모두 D1 = 0: 2개.
  - `1f244` 상수가 `SUB.L`에 의해 덮어써짐: 1개.
  - bit number가 mod 8로 두 번 마스킹됨: 2개.
  - 이 실행 전에 메운 시험 빈틈: `1cad4-noext`와 `1cad4-index-noext` — 64 KiB work-RAM 미러가 부호 확장이 빠진 것을 숨겼고, 합성 ROM 테이블에 음수 index를 쓰는 규칙 두 개.
- [F] real-ROM: batches `f4`, `f5`, `s1`, `s2`, `s3` 종료 0, mismatches `0,0,0,0,0`; covered `196`, `194`, `193`, `195`, `195`(합집합 196/196).
- [F] V1: A/B 각각 fixtures 1743, failed 0, runs 2, identical true(digest `b379327ca53f2194`); regression specs 35개 모두 failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 종료 0. `objects_g1` 판정은 C1과 같다.
- [F] frames: `d1` 54400/54400, mismatches 0; `controller_game` 54400/54400, mismatches 0; `irq` 54400/54400, mismatches 0; `demo` 45684/45684, mismatches 0.
- [F] IO: matched_total 166744, baseline 166744, delta 0, mismatches 0, cpp_errors 0, runs 2, identical true; per_config `P0` 81600, `P1` 76128, `P1b` 7560, `boot-demo-0` 381, `boot-title-idle` 600, `boot-title-start` 192, `fx-bios-call` 3, `fx-c-input-read` 3, `fx-n-input-read` 3, `fx-queue-short` 1, `fx-start-c79a` 273.
  - 수락 항목 중 실패한 항목은 `frontiers_confirmed`다. 15개 C/E 실행이 TB 안에 숨은 4e8e6(C4)에서 멈추므로 frontier를 확인할 수 없고, C2 코드는 48350(C3)과 4e8e6(C4) 이후에만 실행되므로 계획이 말한 대로 C2만으로는 IO 이득이 없다.
  - 첫 전체 실행은 frame driver 수정 전 E1 base에서 했고, 두 입력 fixture에서 guard-bad였다. E1 수정을 병합한 뒤 IO를 재실행했다.
- [F] 남은 실행 PC: C 757 → 659, E 12, 예상 frame 변화 없음. 일치 frame 166,744.
- 검증 방법: deterministic runner(LLM 없음). IO는 E1 frame driver 수정 병합 후 재실행 값이다. 이 기록 초안은 local Qwen이 썼고 메인이 검토·수정했다.

## 뒤 단위 변경 기록: player C11(2026-10-27, 작업자 Claude Opus 5.5 / high)

C11 계약(`animation-machine-player-c11-contract.md`) 결정 5에 따른 기록이다. C2 실행부·시험은 바뀌지 않았다.

- [F] `1de34 BNE`의 대상 `1e8de`(이전 routing 밖, 뒤 단위 정지)는 C11 block 시작이다. C2 시험은 `1e8de`를 정지 PC로만 쓰므로 그대로 통과한다(정지 검사가 dispatch보다 먼저). V1 spec `pc2.py`의 `ROUTED_LATER`에 `1e8de`를 더했다(C2 run은 그 PC에서 계속 멈춘다). V1 pc2 1,743 그대로.
