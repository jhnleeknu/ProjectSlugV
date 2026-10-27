# 영역 D 단위 FR15(세 번째 IO 관측의 첫 D 단위: 2986 callback `3ff14` → 설치 `3ff4c`(플레이어 node 선택, 부호 있는 WORD `2e` 비교, `40b60`의 C와 통과 RTS `40b7a`) → `4076a`/`40812`..`40872`(`4d766` C, script WORD 목록 `409e6`/`40a0a`), 28ae 자식 `40896` → `408c0`(`288c` C)과 보조 `40a5a`(소리 3개, 28ae 자식 `41fe6`/`40896`), script callback `40bc8` `6f282` `6f352`, `4c2c4`, 2986 자식 `b3dfc`, 원 그리기 `4fdfc`/`4fe50`(video port LONG `3c0000`)과 `4fea4`/`4fec6`, 28ae 자식 `4ff4c` → `4ff5c`, FR1 종류 처리기 `c13c0` → `c142a`/`c14d8`(MULU.W #8 구역, 묶인 BEQ `c1540`), 2986 자식 `e9b8a` → `e9b9a`(계산 점프 `e9c6e`의 칸 3 `e9c7e`) → `ea132` → `ea14c`(`ea2ca` C, BYTE `8f` 반복), 192 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §11.5 표의 D-1 행(제안 이름 FR15)을 기준으로 삼고, 구조·공통 규칙은 C11 계약(`animation-machine-player-c11-contract.md`; 세 번째 관측 방식, `MS5_IO_EXT2`, ext2 pack의 natural fixture)과 FR14 계약(영역 D 관례), FR12 계약(묶인 BEQ, `c1036` 형제 코드)을 따르며 다른 점만 적는다. 단위 이름은 FR15, 파일 접두어는 `objects_fr15`(C++) / `fr15`(V1 spec)다. 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다. BIOS 실행, 자연 scheduler, IRQ timing은 주장하지 않는다. stage 선택·continue 설정·PLAYER_START는 세 번째 관측의 선언 host 쓰기다(계획 §11.2).

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 LONG `2000b0`(`40896` `40a5a`)을 live bus로 읽는다. 장치 쓰기는 `4fe74 MOVE.L D3,3c0000.l` 하나다(video port LONG, ordered port로 기록). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 branch `claude/fr15-core` 시작 `9e82ba5`(`main` `eeae7b0` = C11 병합 + P2 frame 끝 carry 수정). routing 기준 `engine/src/animation_machine.cpp` SHA256 `4354bc8da2843db148b0fe64e2782469a26cbaa1774626f3d33a664710a67340`, `animation_machine_internal.h` `212ee22039dc709d3277956623cc87130a98fa0a7d752cc7a946ebf3cb6efd4e`(C11 계약의 새 값과 같음).
- [F] 관측 입력(읽기 전용): 세 번째 IO 관측 `artifacts/animation_machine_io_ext2`(`observation.json` SHA256 `bac35488287f2a5ac776fdcc1dccd3033d65b18181a4ee66850c9f7556c22657`, compared_sha256 `d30e68d6b8c7f69181be12b00f017c4eafccb705416af7e8beea02b6d9595673`, 검증기 pin 이름 `io-ext2`). 계획 §11.7 결정 1로 공유 artifacts에 옮겨졌다. V1 natural family는 이 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT2`, C11과 같은 위치 규칙)으로 읽는다.
- [F] 이 단위의 정확 bitmap 재관측 두 벌(scratch, 관측기 `tools/observe_animation_machine_io_ext2.py` 수정 없음): `reobs/fr15base`(현재 routing 그대로), `reobs/fr15v1`(계획 FR15 27 범위를 `--extra-routed`로 가상 routing). 결정 1.
- [F] 시작 목록: **`ms5-scratch/fr15/work/starts_plan.txt`(192개, 줄마다 하나, SHA256 `405ca3d95eb4eb5bcd8c1c8fc216a690acb3aef8f22a8865a5b6be6778fa08e7`)**. 계획 목록 `ms5-scratch/obs3/plan3/starts_D-1.txt`(공백 구분, SHA256 `4275083a110b197a614a2cd0283973882d3801a97c30b85dd16bb6c7f6c77135` = 계획 표의 `4275083a110b197a`)와 집합이 같다. 실행부의 `case` label 192개, V1 spec `STARTS`, 시험 생성기의 `STARTS`와 집합이 같다(작업자 확인: case 집합 = 시작 목록, V1 spec `build()`가 범위 안 짝수 PC 984개가 모두 `animation_objects_fr15_block`으로 routing됨을 확인, `make test`의 FR15 시험이 시작 192개를 셈).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr15/`
  - `reobs/run.sh`(재관측 + `dleft.py` `runstops.py` + digest chain), `reobs/fr15base` `fr15v1`(+ `.dleft` `.stops` `.chains` `.log`), `tools/xdetail.py`(계획 상세 → `plan/udetail_D-1_plan.txt` `plan/D-1.dis.txt`), `tools/static_fr15.py` → `work/static_plan.txt`(범위 안 정적 decode), `tools/refs_fr15.py` → `work/refs_plan.out`(ROM 전체 FR15 시작 참조), `tools/intargets.py` → `work/intargets_plan.out`(범위 안 비시작 PC로 오는 직접 분기), `tools/longrefs.py` → `work/longrefs_plan.out`(시작과 같은 ROM LONG), `tools/flagscan.py` → `work/flagscan_plan.txt`(block 경계를 넘는 flag), `tools/exitflags.py` → `work/exitflags_plan.txt`(출구 대상이 앞 코드의 flag를 읽는지), `tools/newvis_fr15.py` → `work/newvis_fr15v1.txt`(숨은 직선 PC), `tools/fr15exec.py` → `work/fr15exec_base.txt`(재관측의 FR15 실행 PC·run·frame), `tools/natscan_fr15.py` → `work/natscan_fr15.out` `work/natural_fr15.json`(V1 natural frame), `tools/fr15refs_repo.py` → `work/fr15refs_repo.out`(저장소의 FR15 범위 literal), `tools/v1dbg_fr15.py`(V1 world 진단), `work/v1_regs.sh`, `io_ext2_fr15/`(세 번째 관측 IO 비교), `mut/`(변이), `realrom/`(실제 ROM 차분), `qwen/`(local Qwen 초안과 대조), `trial_logs/`(작업자 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위(결정 1)

- [F] **재측정(현재 routing = `main` + C11 + P2 carry 수정)**: 정확 bitmap 재관측 `reobs/fr15base`(routing `4354bc8d`)의 예측 일치 frame은 **6,664**, 실행된 routing 밖 PC C 372 / D 1,954 / E 2다. 첫 정지는 `M1.5` 190 `4c2c4`, `M2.0` 215 `1d776`(C-2), `M3.1` 225 `4fdfc` 계열, `M4.0` 193 `40896` 계열, `D2` 553 `c13c0` 계열, `G1.94` 768 / `G1.68` 960 `ca5c` `b3dfc`이고 `D1` `P0` `P1` `X1`은 끝까지다. C11 계약의 가상 routing 재관측 `c11v1`과 `.stops`·digest chain이 같다(P2 carry 수정은 native 관측에 영향이 없다).
- [F] **정적 decode**(`work/static_plan.txt`): 27 범위의 명령 512개는 모두 범위 안에서 끝난다. 범위 안 leader는 계획 시작 192개 + `c1540` 하나다. `c1540`은 묶인 BEQ다(아래 "flag"; FR12 `c113a` `c11ec`와 같은 꼴): `c1532 BEQ.W c1540`(Z가 선 채)과 `c153c BEQ.W c1540`의 대상이자 `c153c`의 fall-through이므로 block 시작으로 두지 않는다. DBRA·TRAP는 없고, 계산 점프는 `e9c6e JMP e9c72(PC,D0.W)` 하나다.
- [F] **범위 밖에서 범위 안 비시작 PC로 오는 직접 분기**(`work/intargets_plan.out`): 실제 코드는 없다. `409c8 BRA.W 40a04`는 `409c4 ADDI.L #ffff6000,3a(A6)`의 즉치, `c1586 BPL.B c151e`는 `c1582 JSR c6a96.l`의 operand, `ea32e BGT.B ea2d4`는 `ea32a JSR 16ea4.l`의 operand를 명령으로 읽은 것이다. 나머지 둘(`c1532` `c153c` → `c1540`)은 범위 안의 묶인 BEQ다.
- [F] **정확 bitmap 재관측(FR15 가상 routing, 계획 27 범위)** `reobs/fr15v1`: 예측 일치 frame **6,824**(계획 표의 6,824와 같음, +160), 실행된 routing 밖 PC C 372 / D 1,782 / E 2. 첫 정지는 `M1.5` 213 `21a90`(C-2), `M2.0` 215 `1d776`(C-2), `M3.1` 248 `1db0a` 계열(C-2), `M4.0` 249 `4002c` 계열(뒤 단위), `D2` 611 `ea1ca`(D-2), `G1.94` 768 / `G1.68` 960 `ca5c`(E-1)이고 `D1` `P0` `P1` `X1`은 끝까지다. 모두 뒤 단위다. digest chain은 `fr15base`와 11 run 모두 같다.
  - [F] **숨은 직선 연속 검사**: `fr15base`에 없고 `fr15v1`에만 보이는 routing 밖 PC는 **없다**(`work/newvis_fr15v1.txt`: 11 run 모두 0). 실행되는 범위 끝(`3ffa0` `4076e` `4083c` `40884` `40890` `408da` `40978` `40a2e` `40b12` `40bce` `6f296` `6f360` `ea1ca` `ea1d8` `ea2c0`)은 기준 관측에도 이미 기록된 다른 진입이거나 뒤 단위 정지다(앞 명령이 BRA·JMP·RTS인 범위 끝은 직선 연속이 아니다).
  - [F] 범위 보정은 **없다**: 계획 27 범위·192 시작을 그대로 쓴다. 반복은 한 번으로 수렴했다.
- [F] **실행된 표 칸만 전사**: FR15 안의 계산 점프 `e9c6e`가 실행하는 칸은 `e9c7e`(BYTE `90` = 3) 하나다(아래 결정 2).
- [F] **IO 실행**(`reobs/fr15base`, `work/fr15exec_base.txt`): FR15 시작 가운데 기록된 것 171개, 실행 169,020회(TB 첫 routing 밖 PC 기록 수; 계획 표의 169,056은 closure 진입으로 줄인 실행 PC 단위의 셈), run 6개. 기록되지 않은 시작 21개(`3ff64` `40824` `4085e` `40868` `4095e` `409e6` `409f0` `409fa` `40a0a` `40a0e` `40af6` `4fee8` `4fef8` `4ff04` `b3e14` `c1502` `e9c16` `e9c2a` `e9c40` `e9c52` `ea332`)는 같은 TB 안의 직선 연속이거나 이 관측에서 실행되지 않는 분기 쪽이다(P2 node `100da8`의 `3ff64`, LONG `76` ≠ 0의 script 목록 `409e6`.. 등).
- [F] **계획 결정 5(E-1의 `c3ce`)**: `c3ce`의 호출자는 이미 routing된 D 코드 `42196`이고 FR15 block은 `c3ce`를 부르지도 거치지도 않는다(FR15 closure 밖). `fr15v1`에서 `c3ce`는 `M4.0` frame 250에 처음 실행되며, 이 run의 첫 정지는 그 앞 frame 249(`4ef08`·`4002c` 계열)다. 붙여도 예측이 바뀌지 않으므로 **`c3ce`는 붙이지 않고** E-1에 남긴다. `ca5c`도 FR15와 관계가 없어 E-1에 남긴다.

## FR15 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **192 block, 512 명령, 1,968 byte, 27 범위**(시작 목록 SHA256 `405ca3d9…`(줄 구분) / `4275083a…`(계획 공백 구분), 범위 byte를 이어 붙인 SHA256 `6f6033bfda897da21255a297b1fdd4edf718e060fb88b66ebfc273807ee59bdd`). 짝수 PC 984(내부 792; 묶인 BEQ `c1540` 포함). 기존 routing과 겹침 0(V1 spec `build()`와 시험 `interior()`가 범위 안 짝수 PC를 전수 확인).

| 범위(CPU = 파일 오프셋) | byte | 시작 | SHA256(앞 16자) | 내용 [I] |
| --- | --- | --- | --- | --- |
| `3ff14..3ffa0` | 140 | 14 | `0e57728ecaaaa22d` | 2986 callback `3ff14`(C11 `3fef4`가 씀): `49f8c` anim `40da0`, BYTE `92` := `ff`, BYTE `14` := BYTE `1b`, LONG `76` / `56` := 0, `496c2`, 설치 `3ff4c`(곧바로) → `40964`, `40a1c`, WORD `8a`로 플레이어 node(A5 − `7348` / A5 − `7258`), 부호 있는 WORD `2e` 비교(BLT), `40b60`의 C(BCC), `4d508`, `4002c`는 쓰기만 → BRA `4076a` |
| `4076a..4076e` | 4 | 1 | `794906625d777736` | BRA.W `40812` |
| `40812..4083c` | 42 | 4 | `b02e1cd02ed46535` | `4b54e`, BYTE `61` bit 7과 SNE.B D0, `405e2`는 쓰기만, AND.B D0를 BYTE `5e`에, BCLR #6,`61`(A6), WORD `84` = 0 → `40846`, 아니면 `4083c`(D-2) |
| `40846..40884` | 62 | 7 | `b584f1d6d817461d` | `4d766`의 C(BCC) → BSET #6,`61`; LONG `76` = 0 → BYTE `14` := BYTE `1b`, WORD `84` bit 0(1 → `40884`, D-2); 아니면 BYTE `14` := BYTE `1a`, JSR `409e6`, BSET #6,`61` |
| `4088e..40890` | 2 | 1 | `1ceeabf0c6a5a30b` | RTS |
| `40896..408da` | 68 | 7 | `df9006593cd4672c` | 28ae 자식 `40896`(`40af6`의): bank anim `11a` / bank 창 LONG `2000b0`, BYTE `92` := `ff`, WORD `8c` := `ffff`, `49290`, 설치 `408c0`(곧바로) → `288c`의 C(BCC `4095e`), `491c4`, TST.B `92`(A0)(BPL → `408da`, D-2) / RTS |
| `4095e..40978` | 26 | 3 | `a936935ddc60b29e` | JMP `2a00`; `40964`: CLR.B `9b`, BTST #7,`15`(0 → `40978`, D-3) / JMP `4bfb4` |
| `409e6..40a06` | 32 | 3 | `3a049c2deb88b250` | LONG `76`의 script WORD 목록: 음수 WORD → NEG, < 4 → BYTE `14` := BYTE `19`(A6,D1.W), LONG `76` := A0, RTS |
| `40a0a..40a2e` | 36 | 5 | `7f2d50e28b2390b7` | ADDA.W (A0),A0(>= 4) → LONG `76` := A0, D0.B := BYTE `14`, JMP `8d34`; `40a1c`: WORD `1e` → `ce02`, `49fc6`, RTS |
| `40a5a..40b12` | 184 | 11 | `d883654ba0821b7d` | `40a5a`(C11 `3fee2` BSR): bank anim `11a` / `2000b0`, 소리 `dad` `dac` `da6`(`8ebe`), WORD `68` / `1e` := `8810`, `4d81c` → BYTE `97` / `98`, WORD `54`, `496c2`, 28ae 자식 `41fe6`(C Set: 그 LONG `76` := A6 + `86`, BYTE `7a`..`7e`, ORI)와 28ae 자식 `40896`(C Clear → `40890`, D-3), BYTE `92` := `ff`, RTS |
| `40b60..40b7c` | 28 | 4 | `9f5c5ee060c779f5` | D0.W := WORD `8a`, D2 := 0, D3 := 8, `4d418`의 C(BCC) → WORD `8c` := D0.W, ORI(Set); RTS가 C를 넘김 |
| `40bc8..40bce` | 6 | 1 | `cbe0e44a1efd0fa1` | script callback(표 `4a500` + `bc`): WORD `86` := WORD (A0), RTS |
| `4c2c4..4c2cc` | 8 | 2 | `d6ea57ac9686c3ab` | JSR `4bce0`(PC); BRA.W `4c2d0` |
| `4fdfc..4fe8a` | 142 | 19 | `a7b54d916bef68d7` | fix 칸 D0.W / D1.W 둘레 반지름 D2.W의 중점 원(8 octant, BSR `4fe50`); `4fe50`: 열 0..`25`와 행 0..`1d` 검사(무부호), VRAM 주소 `7000` + 32 × 열 + 행, MOVE.L D3,`3c0000` |
| `4fea4..4ff12` | 110 | 12 | `6f4022f0d45a8c19` | ROM WORD 표 `4fe8a`의 칸 code로 반지름 D2 − 12 .. D2의 원 13개; `4fec6`: WORD `76` ASR 3, WORD `78` := (`1ff` − WORD `78`) ASR 3, (`14`, `10`)에서의 거리 → BYTE `7c` |
| `4ff4c..4ff96` | 74 | 7 | `325fb48b4122878f` | 28ae 자식 `4ff4c`(stage catalog `47964`): `4fec6`, BYTE `7a` := BYTE `7c`, 설치 `4ff5c`(곧바로): WORD `7a` = 0 → 부모 BYTE `62` := `ff`, JMP `2a00`; 아니면 SUBI.W #`200`(빌림 → 0), D2 := BYTE `7a`로 BRA `4fea4` |
| `6f282..6f296` | 20 | 1 | `dba43c77f186aa88` | script callback(표 `4a500` + `20`): D0.W := 6 × WORD (A0)+, ADD.B BYTE `7c`, BYTE `7f` := D0.B, RTS |
| `6f352..6f360` | 14 | 3 | `4a106dbbb15d7417` | script callback(표 `4a500` + `38`): `49a58` 난수, CMP.W (A0)+(BCS → `6f360`, D-3) / RTS |
| `b3dfc..b3e1c` | 32 | 4 | `303477680a844a09` | 2986 자식 `b3dfc`(C11 `e8c66`): WORD `7c` := 1, `1aa3a`, D0.B & `c0` → A0 := `b42a2` / `b403e`, BRA `b3ea2`(FR1) |
| `c13c0..c1560` | 416 | 36 | `59bb31ca5dabe1f6` | FR1 종류 처리기 `c13c0`(기록 `b35ce`, FR12 `c1036`의 형제): `49f8c` anim `c1ec0`, `c6a96`, `b4304`의 C(BCC `c1d06`), `49a58` 난수 각도(ROR / SMI / EOR), `c1cf2`; 설치 `c142a` / `c14d8`(`b4030`): steer, 각도, mirror, MULU.W #8 구역, 묶인 BEQ `c1540` → `c0944`, `b4958` / `b4ab0`(D0 bit 2 → `c1d2e`) / `b4334` |
| `e9b8a..e9b92` | 8 | 1 | `eb8eeaa91bf9f103` | 2986 자식 `e9b8a`(FR2 `e9b5c`): D0.W := 3, BRA `e9b9a` |
| `e9b9a..e9c72` | 216 | 17 | `b75ce5e7cffeb2b4` | BYTE `90` := D0.B, WORD `68` / `1e` := `ffff`, `ea2c6`, LONG `7e` := ROM LONG 표 `ea3c4`, ROM LONG 표 `ea3ac`(WORD `88`)의 소리 둘, BYTE `8f`개 칸의 폭 합, WORD `2e` / `32` 보정, `43e34`, `496c2`, JMP `e9c72`(PC,D0.W)(칸 3만) |
| `e9c7e..e9c82` | 4 | 1 | `8ab98729f252b0b0` | 표 칸 3: BRA.W `ea132` |
| `ea132..ea1ca` | 152 | 16 | `0355c5717c45f908` | WORD `a4` := 2, BYTE `92` := `ff`, WORD `8c` := WORD `a4`, 설치 `ea14c`(곧바로): `ea2ca`의 C(BCS `ea2c0`, D-2), `ea2e0`, `ea2fe` / `ea314` / `ea334`의 BYTE `8f` 반복(ROM WORD 표 `ea37c`, BYTE `93` / `92`에 BSET / BTST D1) → `ea1d0` / `ea1ca`(D-2) |
| `ea1d0..ea1d8` | 8 | 1 | `f4f0b1fcb99c3261` | ADDQ.W #1,`8c`(A6); BRA `ea2be` |
| `ea2be..ea2c0` | 2 | 1 | `1ceeabf0c6a5a30b` | RTS |
| `ea2c6..ea34a` | 132 | 10 | `393dfa734b535480` | 보조: `ea2c6` D0 := 0; `ea2ca` WORD `8a` + 4와 WORD `5e4a`(A5) + 2 × WORD `88`의 CMP.W(C); `ea2e0` `43e34`, BYTE `8e` += 1, BYTE `14` := BYTE `19`(A6, bit 0); `ea2fe` / `ea334` WORD `86` += 폭; `ea314` 기록의 LONG → `16ea4` |

- [F] **진입**(현재 routing 기준 호출자, `work/refs_plan.out` `work/longrefs_plan.out`):
  - 다른 실행부의 호출·분기: `40a5a` ← C11 `3fee2 BSR.W`(그리고 routing 밖 `3fd16` `3fe82` `3ff02`), `4c2c4` ← C11 `1e5e6 JSR`(그리고 routing 밖 `3338c` `335b0` `343f6`), `40964` `40a1c` `40b60` ← routing 밖 형제 callback `3fd..`/`3fe..`/`400..`의 BSR.W, `4076a` ← routing 밖 `3fe64` `3fe76` `40028`, `40812` ← routing 밖 `40798`, `ea2be` `ea2ca` `ea2e0` `ea2fe` `ea314` `ea334` ← routing 밖 형제 코드 `e9cea`..`ea2b0`, `ea132` ← 표 칸 0 `e9c72 BRA.W`(routing 밖), `4fea4` ← routing 밖 `4ff38 BCS.W`, `4fec6` ← routing 밖 `4ff12 BSR.B`.
  - 자식·설치 값(다른 실행부가 씀): `3ff14` ← C11 `3fef4 MOVE.L #3ff14,(A6)`(쓰기만; 그리고 routing 밖 `3ff06` `3ff0e`), `b3dfc` ← C11 `e8c66 MOVEA.L #b3dfc,A0`(2986 자식), `e9b8a` ← FR2 `e9b5c`(2986 자식), `4ff4c` ← stage catalog `47964`(28ae 자식), `40896` ← FR15 `40af6`(28ae 자식).
  - ROM LONG 표: `c13c0` ← FR1 종류 기록 표 `b3484..`의 기록 `b35ce`의 LONG 6(`b35d4`; FR14 `c0d68`과 같은 꼴), `6f282` `6f352` `40bc8` ← interpreter callback 표 `4a500`의 칸(`4a520` `4a538` `4a5bc`; interpreter `4a352`/`4a43c`의 JSR (A1), routing이 결정). 그 밖의 LONG 검색 적중(`c9e` `8726` `8e2c` `e7680` `f634a` `f99e6`)은 다른 명령의 operand나 자료가 우연히 같은 값이다.
- [F] **설치 값**(`MOVE.L #v,(A6)`): 곧바로 들어감 `3ff4c`(`3ff46`) `408c0`(`408ba`) `4ff5c`(`4ff56`) `c142a`(`c1424`) `c14d8`(`c14d2`) `ea14c`(`ea146`). 쓰고 다음 block으로 감 `4002c`(`3ff96`; routing 밖, 실행된 뒤 단위 callback) `405e2`(`40824`; routing 밖). LONG `a2` := `c141e`(`c1412`; `c1cf2`에 넘기는 값, FR12 `c106e`와 같음).
- [F] **자식**(`MOVEA.L #v,A0` 뒤 `JSR 28ae`): `41fe6`(`40ab8`; 이미 n22가 routing, FR15는 자식의 LONG `76`과 BYTE `7a`..`7e`만 씀), `40896`(`40af6`, FR15). `2986` 호출은 FR15 안에 없다.

### 계산 점프와 표(결정 2)

- [F] **`JMP e9c72(PC,D0.W)` `e9c6e`**(block `e9c64`): `MOVEQ #0,D0; MOVE.B 90(A6),D0; ADD.W D0,D0 ×2`라 D0.W = 4 × BYTE `90`(0..`3fc`)이고 대상은 `e9c72` + D0.W다. ROM 표 `e9c72..e9c86`은 BRA.W 다섯 칸(`ea132` `e9c86` `e9faa` `ea132` `ea2b4`)이다. BYTE `90`을 쓰는 원본은 `e9b9a MOVE.B D0,90(A6)` 하나이고, 그 D0를 정하는 진입은 `e9b8a`(D0 = 3, FR2 `e9b5c`가 만드는 2986 자식)와 `e9b92`(D0 = 4, routing 밖 `e9b40`의 2986 자식, 이 관측에서 실행 안 됨)다. **실행된 칸만 전사**(FR13 결정과 같은 규칙): 칸 3 `e9c7e`(BYTE `90` = 3)만 허용하고, 그 밖의 index는 checked `unsupported animation objects fr15 jump target`이다. 칸 0·1·2·4(`e9c72` `e9c76` `e9c7a` `e9c82`)는 routing 밖으로 남는다(V1 spec `build()`가 확인).
- [F] **읽는 고정 ROM 자료**(live bus, 상한 검사 없음; C3 결정 5와 같은 규칙. [F] 원본 값은 ROM 바이트):
  - bank 창 LONG `2000b0`(`40896` `40a5a`; FR14 bank anim과 같은 꼴), WORD 표 `4fe8a`(13 WORD, `4feb6`; A0가 `4fea4`에서 2씩 증가, 첨자 상한은 반복 수 13이 정함), LONG 표 `ea3c4`(`e9bae`; 첨자 = 4 × `ea2c6`의 D0 = 0이라 칸 0 = `ea3cc`), LONG 표 `ea3ac`(`e9bae`; 첨자 = 4 × WORD `88`(부호 확장); ROM의 의미 있는 칸은 3개(`ea3b8` `ea3bc` `ea3c0`, 소리 WORD 쌍)이고 WORD `88`을 쓰는 FR2 `e9b74`가 호출자 D0를 넣는다), LONG `7e`(A6)가 가리키는 기록(`ea3cc`; `e9bfa`의 WORD `4(A1,D2.W)`, `ea2fe`/`ea334`의 WORD `4(A0,D2.W)`, `ea314`의 LONG `(A0,D2.W)`; 첨자 = 2 × BYTE), WORD 표 `ea37c`(`ea182`; 첨자 = 2 × D6.W, `ea172`의 `CMPI.W #14,D6; BCC`가 D6 < `14`(무부호)를 보장 — 직접 진입이면 부호 확장 첨자), script 자료(LONG `76`이 가리키는 WORD 목록; `409e6` `40a0a`).
  - 넘기기만 하는 포인터(`MOVEA.L #` / `LEA d(PC)`): `40da0` `c1ec0`(49f8c anim), `b42a2` `b403e`(`b3e08`/`b3e14` → FR1 `b3ea2`), `c0924`(`c14c8` → FR12 `b402a`), `41fe6` `40896`(28ae 자식), `4fe8a`(`4fea4`).
- [F] FR15 안에는 TRAP·DIVU/DIVS·MULS·MOVEM·`JSR (An)`·`JMP (An)`가 없다. MULU 2(`c149c` `c1522`, `MULU.W #8,D0`).

### 정수 연산(결정 3)

- [F] WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W d(An),Dn`, `ADD.W`/`SUB.W`/`ADDQ.W`/`SUBQ.W`/`ADDI.W`/`SUBI.W`/`NEG.W`/`ANDI.W`, `LSR.W`/`LSL.W`/`ASR.W`, `MOVE.B`(레지스터 BYTE), `ADD.B`, `ANDI.B`, `SNE.B`/`SMI.B`, `EXT.W`, `MOVE.W #k,Dn`). `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`EXG.L`·`SWAP`·`EXT.L`·`LSL.L`/`ASR.L`·`MULU`는 LONG 전체. `ADDQ.W #2,A0`(`4febc`)와 `ADDA.W`(`40a0a` `ea172`)는 주소 레지스터 LONG 전체(ADDA.W는 부호 확장). 표 첨자 `(An,Dn.W)` / `(PC,Dn.W)`와 `d(A5)`(`-7348` `-7258`)는 부호 확장한다.
- [F] `MULU.W #8,D0; SWAP D0; MOVE.B D0,b6(A6)`: D0.L := 무부호 D0.W × 8, BYTE `b6` := D0.W의 위 3 bit(구역 0..7). C++는 `(D0 & ffff) * 8U`(넘침 없음).
- [F] `LSR.W b0(A6)`(`c145a`, 메모리 1 bit 이동): 새 WORD가 0이면 Z → `c14c2`.
- [F] `ASR.W #3` / `ASR.W #1` / `ASR.L #1` / `ASR.L #5`: 부호 bit로 채움(C++ `ofr15_asr_word` / `ofr15_asr`, 부호 있는 이동에 기대지 않음). `LSR.W #2,D6`(`4fdfc`), `LSR.W #1,D0`(`4ff04`)는 0으로 채움. `LSL.W #5,D7`(`4fe60`)은 WORD 안에서 넘침을 버림.
- [F] `ROR.W #8,D0; SMI.B D1`(`c13f8`): N은 회전 결과 bit 15(= 원래 bit 7). `EXT.W D1; EOR.W D1,D0; SUB.W D1,D0`: D1.W가 `ffff`면 D0.W := −D0.W(FR12 `c106e`와 같음).
- [F] `BTST D1,92(A6)` / `BSET D1,93(A6)`(`ea192` `ea182`, 메모리 operand): BYTE, bit = D1 mod 8. `BTST #2,D0`(레지스터)는 LONG의 bit 2.
- [F] `EXG.L D4,D5`(`4fe20` `4fe38`)와 `EXG.L D0,D1`(`4ff02`)은 32 bit 전체를 바꾼다.
- [F] 부호 있는 비교: `3ff68 CMP.W 2e(A6),D0; BLT`(WORD 부호 있는 미만). 무부호: `4fe04 CMP.W D4,D5; BCS`, `4fe50`/`4fe60 CMPI.W #26 / #1e,D7; BCC`, `409f0 CMPI.W #4,D1; BCC`, `4fef8 CMP.W D0,D1; BCC`, `ea172 CMPI.W #14,D6; BCC`, `e9bf2 CMP.B 8f(A6),D0; BCC`, `ea1b4 CMP.B 8f(A6),D1; BCS`, `6f358 CMP.W (A0)+,D0; BCS`, `4ff74 SUBI.W #200; BCC`(빌림 = WORD < `200`).

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작; `work/static_plan.txt`): `288c` `28ae` `2a00` `8d34` `8ebe` `ce02` `16ea4` `1aa3a` `43e34` `491c4` `49290` `496c2` `49a58` `49f8c` `49fc6` `4b54e` `4bce0` `4bfb4` `4c2d0` `4d418` `4d508` `4d766` `4d81c` `b3ea2` `b402a` `b4030` `b4304` `b4334` `b4958` `b4ab0` `c0944` `c1cf2` `c1d06` `c1d2e` `c6a96`(35개).
- [F] **뒤 단위 정지**(FR15 block이 분기·fall-through로 닿는 routing 밖 PC, 8개): `4083c` `40884` `408da` `ea1ca` `ea2c0`(D-2), `40890` `40978` `6f360`(D-3). 모두 계획 상세(`plan/udetail_D-1_plan.txt`)의 "later unit, executed" 목록과 같다. 출구 대상이 FR15가 남긴 flag를 읽는 곳은 없다(`work/exitflags_plan.txt`: 43 대상 모두 "-").
- [F] V1·실제 ROM 차분의 선언 정지는 위 8개, 쓰기만 하는 callback `4002c` `405e2`, C11의 남은 뒤 단위 정지 13개(`ca5c` `1d438` `1d776` `1d940` `1db0a` `1dbf0` `1e648` `1e71e` `1e96c` `2196c` `21a90` `21aa2` `4ebfc`)와 C1~C10의 남은 정지 9개(`1de3c` `1e21c` `1fc96` `1fd3c` `1fd50` `21ea0` `21fa6` `4e69a` `4ef08`)다(모두 32개). 계산 점프의 routing 밖 칸 `e9c72` `e9c76` `e9c7a` `e9c82`도 정지다.
- [F] TRAP 없음. ROM·RAM 실행 없음. 장치 쓰기: `4fe74 MOVE.L D3,3c0000.l` 하나(C++ `VideoPortWrite{3c0000, 4, D3}`; C4·U03과 같은 꼴). 장치 읽기 없음.

### block 경계·복귀를 넘는 flag(결정 4)

C11 방식대로 block 첫 명령부터 flag를 정하는 명령까지 훑었다(`work/flagscan_plan.txt`). 그리고 FR15 출구 대상과 FR15 RTS의 복귀 PC에서 FR15가 남긴 flag를 읽는 곳을 따로 훑었다(`work/exitflags_plan.txt`, 호출자 목록). X를 읽는 명령은 없다.

- [F] **C 소비 block 8개**(Clear 쪽 / Set 쪽; Unknown C면 `objects fr15 caller requires known carry`): `3ff78 BCC`(FR15 `40b60` → `4d418`; 아래 통과), `4084c BCC`(n23 `4d766`: `ST.B D1; ADD.B D1,D1`의 C), `408c6 BCC`(stage event ops `288c`: LONG `c(A6)` = 0이면 Set, 아니면 `289e`), `40ac8`·`40b06 BCC`(fade card `28ae`: 빈 node가 있으면 Set, `290e` 실패면 Clear), `40b6e BCC`(b2b `4d418`), `c13ee BCC`(FR12 `b4304`: LONG `76`이 `b4036`/`b403e`면 Clear, 아니면 Set), `ea150 BCS`(FR15 `ea2ca`).
- [F] **C를 만들거나 넘기는 FR15 block**: `ea2ca`(`CMP.W (A0,D1.W),D0; RTS`: C = 무부호 D0.W < WORD, 복귀 `ea150`가 읽음), `40b72`(`ORI.B #1,CCR` → Set, 다음 `40b7a`), **통과 RTS `40b7a`**(`40b6e`의 Clear 또는 `40b72`의 Set을 복귀 `3ff78`로 넘김; dispatcher `carry_preserving_pc`에 둠), `40acc`(`ORI.B #1,CCR` → Set, 다음 `40af6`이 `28ae`로 다시 정하므로 읽는 쪽 없음). 그 밖의 FR15 block 뒤는 Unknown이다.
- [F] 돌려주지만 읽는 쪽이 없는 flag: RTS `4088e` `408d8`(node callback 끝), `40a2c`(복귀 `3ff54 TST.W`), `409fa`(복귀 `40868 BSET`), `40b0a`(C11 `3feee`, flag를 읽지 않음), `40bc8` `6f282` `6f35e`(interpreter 복귀), `4fe4e`(복귀 `4febc ADDQ.W #2,A0` 뒤 `MOVE.W (A7)+`가 새로 정함), `4fe84` `4fe86`(복귀 `4fe0e`.. `NEG.W` / `EXG` / `TST.W`), `4fec4`, `4ff10`(복귀 `4ff50 MOVE.B`), `ea2be`, `ea2c6`(복귀 `e9bae ADD.W`), `ea2e6`(복귀 `ea158 CLR.B`), `ea2fe`/`ea334`의 RTS(복귀 `ea166 MOVE.W` / `ea1b4 ADDQ.W`), `ea332`(복귀 `ea1b0 JSR`), `c14c0` `c155e`.
- [F] **묶인 BEQ `c1540`**(FR12 `THREAD`와 같은 처리): `c1522 CMPI.B #0,b6(A6); BEQ.W c1540`의 taken 쪽은 Z가 선 채 `c1540 BEQ.W c0944`로 가므로 늘 `c0944`다. `c1536 CMPI.B #1,b6(A6); BEQ.W c1540; [c1540] BEQ.W c0944`도 Z로 `c0944` 또는 `c1544`다. C++는 `c1522`·`c1536`이 구역 0 / 1이면 `c0944`로 곧바로 간다. `c1540`은 block 시작이 아니며 직접 진입은 `unsupported animation objects fr15 PC`다.
- [F] Z / N이 경계를 넘는 곳은 없다. 그 밖의 Bcc는 같은 block 안의 명령이 정한 flag를 읽는다(`TST.W 8a`·`TST.L 76`·`TST.W 84`·`ANDI.W #1`·`TST.B 92(A0)`(BPL)·`MOVE.W (A0)+`(BPL)·`NEG.W`/`CMPI.W #4`(BCC)·`TST.W D6`(BMI)·`SUBQ.W #1,D4`(BNE)·`ADDQ.W #1,D2`(BMI)·`SUBI.W`(BPL/BMI)·`TST.W 7a`·`SUBI.W #200,7a`(BCC)·`ANDI.B #c0`·`BTST`(Z만)·`LSR.W b0`(BEQ)·`CMPI.B #0 / #1,b6`·`CMP.B 8f`·`SUB.W a4`/`MOVE.W D6,(A7)`(BMI)·`MOVE.W (A7)+,D6`(BMI)·`TST.B 93`·`MOVE.L (A0,D2.W),D7`(BEQ)).

### IO 실행 run과 frame

- [F] 실행 run 6개(`reobs/fr15base` 기준 FR15 PC가 처음 기록된 frame의 처음 ~ 마지막): `M1.5` 94 190(`4c2c4`), `M3.1` 94 225..261(`4ff4c` 원 그리기, `6f282`), `M4.0` 94 193..415(`40896` `3ff14` `3ff4c`), `D2` 94 553..607(`c13c0` `e9b8a` `ea14c`), `G1.94` 768..1,442, `G1.68` 960..1,698(`b3dfc`, `e9b8a`, `c13c0`). callback 수(`work/natscan_fr15.out`): `408c0` 521 frame(`M4.0`), `3ff4c` 54, `4ff5c` 21(`M3.1`), `c142a` 50 / `c14d8` 31 / `ea14c` 24(`D2`), `ea14c` 68 / 46(`G1.94` / `G1.68`).
- [F] **IO 예측(FR15 연결)**: 6,664 → **6,824**(+160; 재관측 `reobs/fr15v1`). P2 carry 수정이 들어간 기준이라 실측도 같은 값이 되어야 한다(아래 "검증 수치": 6,824).
- [F] 원래 IO 관측과 확장 관측은 FR15 코드를 실행하지 않는다(그 관측의 routing 밖 실행 PC에 FR15 시작이 없다). 일치 173,966과 14,500은 그대로여야 한다(작업자는 돌리지 않음; 메인 runner).

## 공통 규칙·native 검증 계획

FR2..FR14, C1~C11 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr15.cpp`, 함수 `animation_objects_fr15_block`. 오류 문자열은 `unsupported animation objects fr15 PC`(범위 안 내부 PC 직접 진입; 묶인 BEQ `c1540` 포함), `objects fr15 caller requires known carry`(C 소비 block 8개에 Unknown C), `unsupported animation objects fr15 jump target`(결정 2의 `e9c6e` 칸 밖) 세 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(27 범위, C11 줄 뒤; `)ok=animation_objects_fr15_block(c);`를 같은 줄에 둔다), `carry_preserving_pc`의 C11 묶음 뒤에 주석 달린 case 묶음 하나(소비자 8 + 통과 RTS `40b7a`), `animation_machine_internal.h`에 선언 하나(C11 뒤), `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄 끝에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 `# objects FR15 refresh:` 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** 곧바로 들어감 `3ff4c` `408c0` `4ff5c` `c142a` `c14d8` `ea14c`는 쓰고 그 값으로 들어가고, `4002c`(`3ff96`) `405e2`(`40824`)는 쓰고 다음 block으로 간다.
- **자료 읽기**(live bus): node field(A6), 부모 node(LONG `c(A6)`, `4ff64`), 플레이어 node(A5 − `7348` / − `7258`)의 WORD `2e`, A0 기록(`40bc8` `6f282` `6f358` `408d0`), script 목록(LONG `76`), A5 WORD 표 `5e4a`, 고정 ROM(위 "계산 점프와 표"). 단위 시험은 고정 ROM·bank 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): WORD 표 `4fe8a`(13), WORD 표 `ea37c`(20), LONG 표 `ea3ac`(3, RAM WORD 쌍) / `ea3c4`(2, RAM 기록), bank 창 LONG `2000b0` = `00fedcba`, 부호 확장 첨자 탐침 `e237c` `e23ac` `e23c4`(`ea37c` / `ea3ac` / `ea3c4`보다 `8000` 아래; 손 규칙 전용). V1·실제 ROM 차분은 원본 ROM을 읽는다.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `4354bc8da2843db148b0fe64e2782469a26cbaa1774626f3d33a664710a67340` → `f78d79200930f9284eb178c2aeed8cef3f8803b7095680a9c85d5e95846ac357`, `animation_machine_internal.h` `212ee22039dc709d3277956623cc87130a98fa0a7d752cc7a946ebf3cb6efd4e` → `92f9c7c743fe8e715ede53ab1042792aed39e4ac3edee6e7665ecb05622f1792`(옛 값은 `# objects FR15 refresh:` 주석).
- [F] **V1 spec**(C2~C11이 쓴 방식; 전수 검색: 모든 spec 모듈의 `EXIT_STOPS` `UNIT_EXITS` `BOUNDARY` `CHAIN_STOPS` `ROUTED_LATER` `OTHER_JUMP_PCS`에서 FR15 범위의 PC):
  - pc11: `EXIT_STOPS`(= C11 `UNIT_EXITS`)의 `40a5a` `4c2c4`(D-1 정지)는 이제 FR15 시작이다. `ROUTED_LATER` `()` → `(0x40a5a, 0x4c2c4)`: 그 run은 계속 그 PC에서 멈춘다(`build()`의 "later-unit stop must stay unrouted" 검사가 이 둘을 허용).
  - pc7 / pc9: 앞 V1 실행(`ms5-scratch/c11/v1_reg_pc7` `v1_reg_pc9`)에서 run이 처음 만난 routing 밖 PC `6f352`(script callback)에서 멈추던 fixture가 있다. `EXIT_STOPS`와 `ROUTED_LATER`에 `0x6f352`를 더했다(그 run은 이전처럼 그 PC에서 멈춘다).
  - b1c: `BOUNDARY`/`CHAIN_STOPS`의 `4c2c4`는 routing 여부와 관계없이 쓰는 정지 목록이라(`routed()` 검사 없음) 바꾸지 않았다.
  - 그 밖의 spec(pc1~pc6 pc8 pc10 se1 se2 fr9~fr14 등)에는 FR15 범위 PC가 없다. 앞 V1 실행 report의 fixture meta(`stop` `successor`)에서 FR15 범위 PC는 pc7·pc9(`6f352`)와 pc11(`40a5a` `4c2c4`)뿐이었다(scratch 전수 검색).
- [F] **C++ 시험**: 저장소의 FR15 범위 literal(`work/fr15refs_repo.out`)은 b1c(`4c2c4`, 정지) c11(`3ff14` `40a5a` `4c2c4` `b3dfc`, 정지·쓰기 값) fr12(`c13c0`, 범위 끝) fr1(`b3dfc`, 값) fr2(`e9b8a`, 범위 끝·쓰기 값) u15(`4c2c4`, 정지) stage_catalog / stage_transition(`4ff4c`, 자식 값) fr10 fr11 n34(범위 안 홀수·값)다. 모두 정지 PC이거나 자료 값이라, FR15 routing 뒤 작업자의 `make -j4 test`에서 C++ 시험이 모두 그대로 통과했다(기대값 변경 없음; `trial_logs/make_test1.log`).
- [F] **검증기**: `tools/verify_animation_machine_*.py`에 FR15 범위 PC를 기대값으로 쓰는 곳은 없다(`work/fr15refs_repo.out`: 관측기 `observe_animation_machine_hud.py` `_stage_area.py` `_stage_catalog.py`의 literal만). 메인 runner가 통합 sweep을 한다.
- [I] 원래 IO 관측과 frame 비교(d1·controller·irq·demo)는 FR15 코드를 실행하지 않으므로 결과가 같아야 한다. 메인 runner가 확인한다.

## 결정

1. **범위: 192 block, 27 범위(계획 그대로).** 정적 decode의 leader 193개 가운데 묶인 BEQ `c1540`은 block 시작이 아니다(결정 4). 숨은 직선 block은 없다(가상 routing 재관측에서 새로 보인 PC 0). 예측 6,824(+160). E-1 `c3ce` `ca5c`는 붙이지 않았다(FR15 closure 밖; `c3ce`는 `M4.0`의 첫 정지 뒤 frame에만 실행).
2. **계산 점프**: `JMP e9c72(PC,D0.W)` `e9c6e`는 실행된 칸 3 `e9c7e`(BYTE `90` = 3, 원본에서 `e9b8a`가 씀)만 허용하고, 그 밖의 index는 checked jump-target 오류다. 고정 ROM 표(`4fe8a` `ea3ac` `ea3c4` `ea37c`, LONG `7e`의 기록)와 bank 창 LONG `2000b0`은 live bus로 읽고 상한을 검사하지 않는다.
3. **정수 연산**: WORD/BYTE 대상은 하위만, 부호 확장 첨자, 산술/논리 이동은 C++에서 bit 연산으로 정의하고 부호 있는 이동·넘침에 기대지 않는다. `MULU.W #8`은 무부호.
4. **flag.** C 소비자 8개는 known C를 읽거나 checked 오류. `ea2ca`(CMP.W)와 `40b72`(ORI)가 C를 만들고, 통과 RTS `40b7a`가 넘긴다. `40acc`(ORI) Set은 읽는 곳이 없다. 묶인 BEQ `c1540`은 `c1522`/`c1536` 안에서 처리하고 Z / N 경계는 없다.
5. **V1 natural family.** 세 번째 관측의 state pack을 spec 안의 `io_pack`(`IO_EXT2`)이 읽는다(C11과 같은 위치 규칙과 compared_sha256 확인). frame 선택(`work/natural_fr15.json`): (a) node area `100800..104c00`의 node가 FR15 callback·설치(`3ff14` `3ff4c` `40896` `408c0` `4ff4c` `4ff5c` `b3dfc` `e9b8a` `ea14c` `c142a` `c14d8`)를 가진 frame(run·key마다 처음·가운데·마지막), (b) 정확 bitmap 재관측 `fr15base`가 FR15 시작을 그 frame에 처음 기록한 frame(그 frame의 pool node `1009a8` + `c4` k 가운데 routing된 callback을 가진 모든 node를 시도, frame마다 FR15 시작에 닿는 node 둘까지). 55 frame에서 36 fixture.
6. **앞 단위 spec.** pc11의 `40a5a` `4c2c4`, pc7·pc9의 `6f352`는 `ROUTED_LATER`(pc7·pc9는 `EXIT_STOPS`도)에 두어 그 run은 계속 그 PC에서 멈춘다.
7. **V1이 닿지 않는 결과**: 없다(`MODEL_GATED`·`LATER_GATED` 비어 있음; V1 fr15의 빠진 후속 0, 도달 못한 분기 결과 0).
8. **다음.** FR15 연결로 세 번째 관측 IO 6,664 → 6,824(+160)를 메인 runner가 확인한다. 계획 순서의 다음 단위는 E-1(`ca5c`, `c3ce`), C-2(C12; 첫 정지 `1d776` `1db0a` `21a90`), D-2(FR16; `ea1ca` `4083c` 등).

## 미확인

- [U] node field·전역 값의 의미(BYTE `92` `93` `8e` `8f` `90` `9b` `5e` `61` `7c` `7f` `b6`, WORD `8a` `84` `7a` `88` `8c` `a4` `b0` `b2` `b4` `86` `2e` `32`, LONG `76` `7e` `64` `a2`, A5 WORD 표 `5e4a`, ROM 표 `4fe8a` `ea3ac` `ea3c4` `ea37c`). 이름(원 그리기, 폭 합, steer, 구역, 소리)은 동작에서 붙인 [I]이다. `4fdfc`가 fix layer에 원을 그린다는 것은 VRAM 주소 `7000` + 32 × 열 + 행과 열 0..`25`·행 0..`1d`(40 × 30 칸 가운데 표시 영역)에서 추론했다.
- [U] `e9c72` 표의 칸 0·1·2·4 대상(`ea132` `e9c86` `e9faa` `ea2b4`)은 이 관측에서 실행되지 않는다. 칸 4는 `e9b92`(routing 밖 `e9b40`의 2986 자식)가 쓰는 index다.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 21개(위 "재확인과 범위")는 closure로 들어왔다(V1 선언 상태·natural·실제 ROM 차분·단위 시험으로만 확인).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC). 예: `M4.0` frame 249의 확인된 frontier는 `4ef08`(C1 미룬 입구)이고 재관측 `.stops`의 그 frame 목록 첫머리는 `4002c` 계열이다.
- [U] natural fixture의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1~C11과 같음). 'any' frame의 node 선택은 frame 시작 상태에서 각 node를 따로 시작한 것이다.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr15.cpp`(case label 192 = 시작 목록과 집합 일치; 공용 함수 `ofr15_get` `ofr15_put` `ofr15_bit` `ofr15_btst` `ofr15_bset61` `ofr15_carry` `ofr15_install` `ofr15_field_word` `ofr15_signed_word` `ofr15_asr` `ofr15_asr_word` `ofr15_add_word` `ofr15_half_sub` `ofr15_steer` `ofr15_angle` `ofr15_mirror` `ofr15_sector` `ofr15_sector_is` `ofr15_bit2` `ofr15_bank` `ofr15_sound` `ofr15_record` `ofr15_width` `ofr15_port` `ofr15_octant` `ofr15_exg45`), `engine/tests/animation_machine_objects_fr15_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_e`), `tools/generate_animation_machine_objects_fr15_test_table.py`(생성기; C11 생성기 꼴에 C4 생성기의 video port 기록(행마다 port 수와 FNV-1a digest)을 더함, 계산 점프 착지 검사 `JUMP_ALLOWED` = `{e9c6e: e9c7e}`, 묶인 BEQ `c1540` 착지 허용, `ea2ca`의 C는 그 run의 operand(D0.W, D1.W, A0, RAM)로 계산, V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; native가 `3c0000` LONG 밖의 장치 port를 쓰거나 선언 밖 ROM을 읽으면 그 run을 버림; 약 3분), `tools/unit_fixture_specs/fr15.py`(V1 spec; C11 spec의 공용 부분 + FR12의 `BUNDLED`/`THREAD` 처리, 단위 부분 교체, `EXIT_STOPS`(32), `CONSUMERS`(8), `TABLE_JUMPS`/`JUMP_PCS`/`JUMP_TABLE`(`e9c6e` → `e9c7e`), natural family는 세 번째 관측 pack). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- 검증 수치는 아래 "검증 수치" 절에 모았다.

## block 목록

[F] scratch `work/starts_plan.txt`(SHA256 `405ca3d9…`). 이 목록은 local Qwen이 범위별 JSON에서 초안을 썼고, 작업자가 스크립트로 만든 같은 목록과 줄 단위로 대조했다(27줄 모두 같음, `qwen/blocks_out.md`).

- **`3ff14..3ffa0`(14)**: `3ff14 3ff24 3ff46 3ff4c 3ff50 3ff54 3ff5c 3ff64 3ff68 3ff74 3ff78 3ff7c 3ff96 3ff9c`
- **`4076a..4076e`(1)**: `4076a`
- **`40812..4083c`(4)**: `40812 40818 40824 4082a`
- **`40846..40884`(7)**: `40846 4084c 40850 40856 4085e 40868 40872`
- **`4088e..40890`(1)**: `4088e`
- **`40896..408da`(7)**: `40896 408ba 408c0 408c6 408ca 408d0 408d8`
- **`4095e..40978`(3)**: `4095e 40964 40972`
- **`409e6..40a06`(3)**: `409e6 409f0 409fa`
- **`40a0a..40a2e`(5)**: `40a0a 40a0e 40a1c 40a26 40a2c`
- **`40a5a..40b12`(11)**: `40a5a 40a76 40a84 40a92 40aa6 40ab8 40ac8 40acc 40af6 40b06 40b0a`
- **`40b60..40b7c`(4)**: `40b60 40b6e 40b72 40b7a`
- **`40bc8..40bce`(1)**: `40bc8`
- **`4c2c4..4c2cc`(2)**: `4c2c4 4c2c8`
- **`4fdfc..4fe8a`(19)**: `4fdfc 4fe04 4fe0a 4fe0e 4fe14 4fe1a 4fe20 4fe26 4fe2c 4fe32 4fe38 4fe40 4fe48 4fe4c 4fe4e 4fe50 4fe60 4fe74 4fe86`
- **`4fea4..4ff12`(12)**: `4fea4 4feae 4feb6 4febc 4fec4 4fec6 4fee8 4feea 4fef6 4fef8 4ff02 4ff04`
- **`4ff4c..4ff96`(7)**: `4ff4c 4ff50 4ff5c 4ff64 4ff74 4ff7e 4ff84`
- **`6f282..6f296`(1)**: `6f282`
- **`6f352..6f360`(3)**: `6f352 6f358 6f35e`
- **`b3dfc..b3e1c`(4)**: `b3dfc b3e08 b3e14 b3e18`
- **`c13c0..c1560`(36)**: `c13c0 c13d6 c13e8 c13ee c13f2 c13f8 c141e c142a c1430 c143a c1450 c145a c1462 c146c c147c c1492 c149c c14ac c14b2 c14ba c14c0 c14c2 c14d2 c14d8 c14de c14e8 c14f2 c1502 c1518 c1522 c1536 c1544 c154a c1550 c1558 c155e`
- **`e9b8a..e9b92`(1)**: `e9b8a`
- **`e9b9a..e9c72`(17)**: `e9b9a e9bae e9bdc e9be6 e9bf2 e9bfa e9c0a e9c16 e9c1c e9c2a e9c30 e9c40 e9c46 e9c52 e9c58 e9c5e e9c64`
- **`e9c7e..e9c82`(1)**: `e9c7e`
- **`ea132..ea1ca`(16)**: `ea132 ea13c ea14c ea150 ea154 ea158 ea162 ea166 ea172 ea182 ea192 ea19e ea1b0 ea1b4 ea1bc ea1c2`
- **`ea1d0..ea1d8`(1)**: `ea1d0`
- **`ea2be..ea2c0`(1)**: `ea2be`
- **`ea2c6..ea34a`(10)**: `ea2c6 ea2ca ea2e0 ea2e6 ea2fe ea314 ea328 ea330 ea332 ea334`

## 검증 수치

작업자 실행(메인의 결정적 runner가 전체 검증을 다시 한다).

- [F] `make -j4 all test`(최종 실행부·시험): 종료 0, 경고 0, Assert 0, Python 310 OK(`trial_logs/make_final.log`). FR15 시험 줄: `animation machine objects fr15: 1182 fixtures (743 single-block, 327 path, 48 producer chain, 16 declared C, 48 checked error (7 with a later failing PC), 87 kept C, 33 port rows / 673 ports), 192 blocks, 5018 calls, 327768 checks`. 다른 C++ 시험은 바뀌지 않고 모두 통과한다.
- [F] 생성기: 다시 돌려 생성 결과가 identical(`trial_logs/gen_repro.log`, 3분). 행 1182. 단일 행이 없는 시작 0, 후속이 빠진 분기 block 0, 출구 중 stop이 아닌 것 0, 계산 점프 행이 표 칸 `e9c7e`에 멈춘다.
  - 실제 생산자 사슬 8개 유지: `3ff74`→`3ff78`, `40846`→`4084c`, `408c0`→`408c6`, `40ab8`→`40ac8`, `40af6`→`40b06`, `40b60`→`40b6e`, `c13e8`→`c13ee`, `ea14c`→`ea150`.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`): 빌드 종료 0, 경고 0, 실행 종료 0, runtime error 0.
- [F] V1 fr15(작업자, `--workers 3`): fixtures 1793(match 959, error 824, mismatches 10; natural 36) failed 0, `ok` true, 방문 시작 192/192, 빠진 후속 0, 도달 못한 분기 결과 0, carry oracle Unknown/Clear/Set = 923/17/19, 입력 파일 불변 확인 true, ports 9970(`trial_logs/v1_try7_fr15.log`). 앞선 `try1..try6`는 spec 보완 전이며, 이미 routing된 `41fe6`가 `EXIT_STOPS`에 들어 있었고, `4feb6` / `ea330`의 stack WORD hint가 빠졌고, `c13c0` node의 LONG `76`이 FR11 handler 목록 밖에 있었고, BYTE `1d(A6)`가 4 이상으로 `8ebe` TRAP에 도달했고, `e9b9a` 진입의 BYTE `90`이 3이 아니어서 계산 점프가 표 밖으로 갔다.
- [F] V1 regression specs(작업자, `--workers 3`; `trial_logs/v1_regs_r1.txt`): pc1 1264, pc2 1743, pc3 1829, pc4 1873, pc5 1755, pc6 1856, pc7 2077, pc8 986, pc9 2347, pc10 1334, pc11 1793, se1 2102, se2 1573, fr9 1415, fr10 2170, fr11 2170, fr12 2302, fr13 2122, fr14 1783(모두 failed 0, `ok` true; C11 기록과 같은 수).
- [F] 변이: 898개; 1회째 killed 861 of 898(`trial_logs/mut_first.log`). 생존 37개는 local Qwen이 먼저 분류했고(`qwen/mut_out.txt`) 작업자가 하나씩 확인했다. 시험 빈틈 15개는 규칙 `rules_e`로 메웠다(`trial_logs/mut_gaps.log`).
  - `rules_e`: `MOVE.W #k` / `ADD.W`가 윗 레지스터 비트를 남기는 경우 `3ff14` `e9b8a` `e9bfa`; `4fdfc`의 `LSR.W #2`; WORD 비교 / 계수기 `4fe04` `4feae` `4febc` `ea172` `e9bf2`; 부호 확장 WORD 첨자 `e9bae` `e9bfa` `ea182` `ea2ca`와 합성 probe `e237c` `e23ac` `e23c4`.
  - 남은 22개는 동치다(`mut/equivalents.txt`). 규칙을 더한 뒤 2회째 killed 876 of 898(`trial_logs/mut_second.log`), 남은 22개가 동치 목록과 같다. Qwen의 잘못된 분류 5건(`4fec6-sign`, `4ff74-le`, `ea19e-wordlong`은 동치인데 killable로 분류; `e9c64-iext` / `e9bfa-iext`는 라벨이 이유와 모순)과 killing input이 아닌 입력 2건(`e9bf2-mask`, `e9bfa-wordlong-2`)은 `ms5-scratch/tools/qwen_lessons.md`에 기록하고 `qwen_system.md`에 규칙을 더했다(`trial_logs/mut_first.log`, `mut_gaps.log`, `mut_second.log`, `mut/equivalents.txt`).
- [F] 실제 ROM 차분: 작업자 300건 seed 1 `mismatches 0`(covered starts 185 of 192, `trial_logs/real_t300.log`), 깨끗이 멈추지 않은 native 63건 건너뜀, 문서화된 분류: FR15 결정 2의 `e9c6e` 칸 밖 jump-target 오류 5건, 2986 실패 경로의 caller X 4건(C7 결정 6), 계산 점프가 다른 실행부 block의 비시작 PC에 닿음 1건(`c14de` 진입, C++ checked `unsupported animation irq f6a PC`), native oracle abort 0.
- [F] IO, 세 번째 IO 관측(io-ext2)(`tools/verify_animation_machine_io.py --observation artifacts/animation_machine_io_ext2/observation.json --workers 3`): run 11, native 비교 frame 18718 가운데 일치 6824(기준선 6664 → +160 = 예측 6824), mismatches 0, C++ 오류 11(`M1.5` 첫 정지 뒤 `cue wrapper failure requires known caller X`, 기준선과 같음), chain divergence 0(`trial_logs/io_ext2_fr15.log`; `verification.json` SHA256 `685287850307102190364383b4f6e93d41ca663c52547f0c20fc5002a6017fcc`, `frontier.json` `2a5d922345ddecf348f3ef6c06b4f8edb4673e9ab6a7002d537972920f16de21`).
  - run별 일치: `M1.5` 213, `M2.0` 215, `M3.1` 248, `M4.0` 249, `D2` 611, `G1.94` 768, `G1.68` 960, `P0` 600, `P1` 600, `D1` 1180, `X1` 1180.
  - 확인된 frontier: `ca5c`(E-1; `G1.94` 768, `G1.68` 960), `1d776`(C-2; `M2.0` 215), `1db0a`(C-2; `M3.1` 248), `21a90`(C-2; `M1.5` 213), `4ef08`(C1 미룬 입구; `M4.0` 249), `ea1ca`(D-2; `D2` 611).
  - 수용 키: 분기 없음·frontier 확인·전체 실행·guard가 frontier와 같거나 뒤·음성 검사 통과·다른 첫 실패 없음·검증기 오류 없음·mismatches 0은 true, 예상 밖 C++ 오류 없음은 false다.
- [F] 작업자가 돌리지 않은 검사: 원래 / 확장 IO 관측, frame, legacy 검증기는 결정적 runner가 돌린다.
- [F] `CPP_PINS`: stage_event / stage_event_ops의 두 pin이 최종 `animation_machine.cpp` / `animation_machine_internal.h` SHA와 같다.
- [F] 검증 방법: 이 절은 local Qwen이 JSON(`qwen/record_in.json`)에서 초안을 썼고 작업자가 확인했다.
