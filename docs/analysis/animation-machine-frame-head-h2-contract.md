# F5 frame head H2: 입력 sampler `31d6`와 pause/menu 요청 `9136` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 F5 범위 문서(`animation-machine-frame-head-f5-scope.md`, 작업 트리 사본 SHA256 `973d45957731ff17ccf49537024307cf7fd20fe9270c9d9bb44a2bc553280fb0`)의 §4 H2 행이다: `31d6..35a0` `9086..932e` `313c` `3902..3916`, 151 block, 자연 실행 19, 위험 external read 큐·replay stream·card menu callee. §1.1 단계 10·12(`f12`→`31d6`, `f54 JSR 9136`, head 안 pause 루프 `fb4 BRA ec4`)와 "관측 결과에 따른 정정" 4(입력 recorder `349c..3520` 도달 불가)가 근거다. 메인 결정 D1~D10(범위 문서 머리)이 구속한다. H1 계약(`animation-machine-frame-head-h1-contract.md`, SHA256 `6f709815fda022dfe6c6e6d3595293f04a3ac963423e2e7c4357aefe585a93cd`)의 external-read queue 절(공개 API `AnimationMachineDevice::reads`, 단일 순서 queue, 빈 queue `animation machine external read queue empty`, 불일치 `animation machine external read queue mismatch`, 성공 commit 때만 소비)을 그대로 쓴다. native 관측은 `animation-machine-frame-head-observation.md`(SHA256 `98677e44862b7ae7304992fd7d2c7d1f1ac0616252aa6937fac9a6fe32ce16f2`)와 산출 `artifacts/animation_machine_frame_head_native/observation.json`(SHA256 `4fe4f796879af90df1c1fd4c753485a9bf0a04d2667b14b8c00dbab23879b16b`, 읽기 전용)이다. 단위 형식과 규약은 H1·H3·H4 계약과 F4 단위 관례를 따른다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. H2 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-h2`(base `9643372` = F4 N01~N33 + F5 H1·H3·H4 + external-read queue API, `engine/src/animation_machine.cpp` SHA256 `c67801e35678c8a92a72e3e035800a8e86f1908bf596dd71a0c9a9a6bc5ea89b`, routing 규칙 94개, `engine/include/ms5/animation_machine.h` SHA256 `0e9ed25b4ae745d9fab7bd8c01795d00096a526404c222abf1bf59ed77b738e2`)을 참조했다. H2 범위의 짝수 PC는 기존 routing에 없다. [F]=원본 바이트, 기록 산출물 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/h2/h2dec.py`(정적 디코드, H1 `h1dec.py`와 같은 leader 규칙, `starts.txt`)가 원본 opcode에서 독립 계산했다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, flag 공유 Bcc 묶음, 범위 안 설치 callback)로 정한다. Unicorn TB 분할은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다. 범위 밖 callee는 그 실행부로 간다(이미 routing된 callee는 기존 실행부, 미routing callee는 경계).
- U01~N33·H1 수용 관례: CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`BRA`/`JMP`/`RTS`/Bcc/`DBRA`)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만인 block은 FLOW_ONLY다. 그 밖의 block은 Unknown이다.

## 요약

- [F] **정적 leader 151개 = 범위 문서 §4 H2의 151과 같다.** 진입 7개(`31d6` `9136`과 범위 안 호출 대상 `9086` `313c` `3902` `349c` `352a`)에서 분기·fall-through를 끝까지 따라간 closure가 hull `313c..3144` `31d6..35a2` `3902..3918` `9086..9332`의 명령 413개를 모두 덮는다(미도달 0). 흐름 공유 Bcc 묶음은 `350e`(`34f4`의 `BCC.W 3522` 뒤 `DBRA`) 하나이고, `350e`는 `34f0 BCC.W 350e`의 대상이라 따로 시작이기도 하다.
- [F] **추가 3 block(메인 결정 1): menu renderer `9332`.** `92ec LEA 9332(PC),A0; JSR a2b8`이 전역 renderer LONG `107f16`(`-ea(A5)`)에 `9332`를 설치하고, card menu 실행부(`a008` tail-call, `a624`의 `JSR (A1)` 경로)가 그 LONG을 live 대상으로 부른다. `9332`는 어느 단위 범위에도 없고 기존 routing에도 없다. H2 범위에 넣으면 시작 `9332` `933a` `933e` 3개가 더해져 **154 block**이다.
- [F] 진입·호출자(scratch `h2xref.py`, fixed ROM 전체의 분기·JSR·LONG·PC 상대 참조): `31d6`은 H1 `f24 JSR`만, `9136`은 H1 `f54 JSR`만 부른다. `313c`는 범위 밖 `3110 BSR`(F5 C2 `3162` 쪽)도 부르고 복귀 `3114 LEA; CLR.L`은 C를 읽지 않는다. `9086`은 범위 밖 `9430 JSR d(PC)`도 부르고 복귀 `9434 BTST`는 C를 읽지 않는다. `3902`는 범위 밖 14곳(`8f4a` `ab9c` `b6dc` `ba86` `bab6` `c184` `c6fe` `4a8e2` `4e9c6` `4e9d4` `4e9f4` `4eaca` `4eb14` `ebe36`)이 부른다. 이 가운데 routing된 것은 `8f4a`(objects U02)뿐이고 복귀 `8f4e MOVEA`→`8f50 MOVEQ`가 C를 지운다. 나머지 LONG 일치(`322e` `3400` `343c` `344c`)와 `907a`의 `6c12`는 자료 우연 일치다.
- [F] **경계(H2가 실행하지 않는 곳):** 호출된 기존 실행부 `386e`(card_menu, `3904 BSR`) `3650`(card_menu_open, `3912 BSR`) `3918`(card_menu_open, `928e JSR`) `ca9e`(screen, `92ce JSR`) `a29c` `a2b8`(card_menu, `92d4`/`92ec JSR`) `a370`(card_menu_open, `92fc JSR`) `e84c8`(card_menu_open, `933e JMP`), 그리고 각 함수의 호출자 복귀(RTS). menu callback `931a JSR (A0)`(LONG `107df6` ≠ 0)은 D8 guard(checked 오류)다.
- [F] **carry:** 소비 block 0, known 생산 0(모델로 두지 않음), FLOW_ONLY 46, guard 1(`931a`), Unknown 107. 46 + 1 + 107 = 154.
- [F] **external read(D4):** 입력 BYTE `380000`/`300000`/`340000`은 `AnimationMachineDevice::reads` 단일 순서 queue에서 원본 읽기 순서대로 꺼낸다. 읽기 block은 `31d6`(`380000`, `300000` 순서로 2건) `3242`(`340000`) `329c`(`300000`) `32f4`(`340000`) `349c`(`300000`, `340000` 순서로 2건)다. 입력 mode BYTE `104cd4` 0이면 H당 `380000 300000 340000 300000 340000`(5건, native 관측의 자연 H 패턴 뒤 5건과 같다), 1이면 replay(`352a`, 장치 읽기 0건) 또는 recorder(`349c`, 2건) 뒤 0건, 2 이상이면 앞 3건뿐이다.
- [F] **live bus 읽기:** `3358 TST.W 0180.w`(ROM WORD `000180` = `0000`), replay stream BYTE(`353c` `3568` `3572`, A0 = LONG `104cc4`; mode 1 선택 `3162`가 표 `f0dfe`의 LONG(`f01fe` `f07fe` …)을 넣는다), RAM 필드.
- [F] **자연 H에서 H2가 닿는 곳**(관측 자연 상태: `104cd4`=0, `100012`=0, `107df0`=`107df1`=`107def`=0, `10f000`=0, `10f002`=0): `31d6`→(`3216`/`3226`→`323e`/`322e`)→`3242`→…→`3292`→`329c`→…→`32f4`→…→`334c` RTS, `9136`→`913e`→`9154`→`9160`→`9168`→`9086`→`910e`→`9134` RTS→`916c`→`9196` RTS(D0 = 1, pause 아님). [I] 따라서 H1+H2+H3+H4로 자연 H는 controller 진입 LONG `(1008e4)`까지 간다(아래 검증 기록에서 확인).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 154 block(151 + renderer `9332` 3).** routing은 `313c..3144` `31d6..35a2` `3902..3918` `9086..9344`(4 범위, 짝수 PC 852개, 시작 154, 내부 698)다. [F] `9332..9344`(`CMPI.B #3,D1; BNE.W 933e` / `MOVE.B #6b,D1` / `JMP e84c8.l`)는 `92ec`가 설치하는 pause menu renderer이고 `docs/analysis/menu-frame.md`(§"실제 메뉴 렌더러9332")가 host 수준에서 이미 같은 의미를 기록했다. 넣지 않으면 pause menu frame(`92fc JSR a370`)은 card menu 실행부가 renderer를 부르는 순간 `unsupported animation machine PC`로 rollback된다. 메인이 151로 제한하면 `9086..9332`로 줄이고 `9332`를 stop-only 경계로 둔다(실행부의 해당 case 3개를 빼는 것 외 변경 없음).
2. **입력 recorder `349c..3522`(`3360`/`3364` 경유)를 routing한다.** [F] 원본 ROM file offset `0x180..0x181` = `00 00`(fixed 영역, CPU 주소 `000180` = file offset)이라 canonical ROM에서는 `3358 TST.W 0180.w; BEQ.W 3368`이 항상 replay(`352a`)로 간다. 그러나 `0180`은 live bus 읽기이고, block 시작 규약(정적 closure 전체 routing)과 직접 진입 시험을 지키기 위해 recorder 12 block(`3360` `3364` `349c` `34d6` `34e4` `34e6` `34ec` `34ee` `34f4` `350e` `3512` `3522`; `3358` 포함 시 13)을 일반 경로로 구현한다. 시험은 직접 진입과 합성 physical 창(`0180` ≠ 0)으로 덮는다. 메인이 경계로 두기를 원하면 `3360` 이후를 `unsupported animation frame head input recorder` checked 오류로 바꿀 수 있다(근거: 위 ROM 바이트).
3. **pause 루프 모델(한 반복 = run 하나).** [F] pause는 `9136`이 `D0.B` = 0을 돌려줄 때다. H1 `f5a`가 BYTE `84(A6)` := 0으로 두고 `f66`/`f84`(`1→0` 전환이면 `3db2` `3d7e` `8bbc` `8bc8` `8c16`) 뒤 `fae JSR 5728` → `fb4 BRA ec4`로 head 안을 돈다. 각 반복은 `ec4` → `ef2`(vblank 대기, D2) → `efc` raster → `f12` → `31d6` → `b68` → `f30` → `f54 JSR 9136` 순서를 다시 지난다.
   - 규약: **pause 루프의 반복 경계는 D2 vblank Waiting(`ef2`)이다.** 선언 BYTE `100017` ≥ 1이면 각 반복이 `ef2`에서 Waiting으로 끝나고(성공 commit), host가 선언 해제 BYTE `100016` := BYTE `100017`을 쓴 뒤 같은 PC에서 다음 run을 시작한다. 따라서 run 하나 = 원본 vblank 한 번 = pause 루프 한 반복이다(D1 A의 H stop LONG `(1008e4)`는 그대로, pause가 풀리는 반복에서 그 stop에 닿는다).
   - [F] 선언 `100017` = 0(관측 자연 seed)이면 원본 code에 반복 경계가 없다(`ef2`가 기다리지 않는다). 이때 run은 선언 queue가 허락하는 만큼 반복하고(반복마다 raster 2건 + 입력 3~5건), queue가 비면 `animation machine external read queue empty` checked 오류로 run 전체가 rollback된다. 실행부는 반복 수를 세거나 끊지 않는다(원본에 없는 경계를 만들지 않는다). 1,000,000 block 상한은 기존 run 규약 그대로다.
   - 이 규약은 H2 실행부의 새 코드 없이 H1의 `ef2`·`fb4`와 queue 규약만으로 성립한다. 시험은 (a) `100017` = 1에서 pause 진입 → `ef2` Waiting → 해제 → 다음 반복 Waiting, (b) `100017` = 0에서 두 반복 뒤 start edge로 pause가 풀려 같은 run 안에서 controller stop에 닿는 경우, (c) `100017` = 0에서 queue가 한 반복분만 있을 때 둘째 반복의 `3c0006` 읽기에서 queue empty와 rollback을 확인한다.
4. **menu callback guard(D8).** [F] `9308`은 BYTE `-212(A5)` := 0, A0 := LONG `-20a(A5)`(= `107df6`), `CMPA.W #0,A0`(부호 확장 0과 32 bit 비교)로 0이면 `931c`, 아니면 `931a JSR (A0)`이다. `931a`는 실행하지 않고 `unsupported animation frame head menu callback`(상태 보존)이다. [F] `107df6`의 정적 writer는 `919a MOVE.L #0,107df6.l`뿐이다(범위 문서 1.1). `9308` 자체는 일반 block이다(쓰기 뒤 `931a`로 PC를 옮기고, 다음 block의 guard 오류로 run 전체가 rollback된다).
5. **실행부 파일·오류 문자열.** `engine/src/animation_machine_frame_head_h2.cpp`의 `animation_frame_head_h2_block`. 오류: `unsupported animation frame head h2 PC`(내부 PC), `unsupported animation frame head menu callback`(guard), queue 오류 2개는 `am_read`가 낸다(H1 queue 절). carry 소비자가 없으므로 carry 오류 문자열은 없다.
6. **무효화 탐침(값만 교체).** [F] 기존 test가 H2 PC를 "routing 밖"으로 쓴 곳은 세 곳이다(구현 뒤 `make all test`로 확인).
   - `engine/tests/animation_machine_objects_u02_test.cpp`의 outside 목록 `3902` → work RAM PC `10fe12`(같은 test의 `10fe10`과 겹치지 않음; 주석 포함, 논리 변경 없음).
   - `engine/tests/animation_machine_card_menu_open_test.cpp`의 outside 목록 `3916` → `10fe14`(같은 test의 `10fe20`과 겹치지 않음).
   - `engine/tests/animation_machine_objects_u02_test.cpp` `boundaries()`의 `8ebe-over-debug`: stop을 `STOP`으로 바꾼 rollback 기대가 `3902`에서 `unsupported animation machine PC`였다. `8f48 JSR 3902.l`의 대상은 코드에 고정이라 RAM PC로 옮길 수 없다. 이제 `3902`→`3904 BSR 386e`(card menu 실행부)가 문자열 `8f6c`를 live bus로 읽고 이 test의 합성 physical ROM이 그 바이트를 덮지 않으므로 `missing or ambiguous physical program bus ROM byte`로 run 전체가 rollback된다. 같은 의미(rollback)로 기대 문자열만 바꾸고 그 행을 따로 검사한다.
   - 같은 test의 `3902` stop 행(`8ebe-over-debug`의 성공 행, 후속 `8f34`→`3902`)과 H1 test의 `31d6`/`9136` 경계 행은 stop이라 그대로 유효하다. [F] Python 검증기 `tools/verify_animation_machine_card_menu.py`(`outside_range_entry_003902`)는 수정하지 않고 무효화 목록으로 보고한다.

## 원본 바이트 근거

[F] H2 코드 5 범위 1,704바이트(짝수 PC 852개, 시작 154, 내부 698).

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `313c..3144` | 8 | `a62a962d93137af7fb53282670a898a7293f1927c94aaca5f14e41b868b5e670` | 1 |
| `31d6..35a2` | 972 | `489f2339710630044a8c74fdc3ccff7d08e8f6497772fe6548105eeb67eb8361` | 70 |
| `3902..3918` | 22 | `2ee827eb3be5c9293e5b793e1834ccc4917c1e83daa2846f3b1d98ca42cb39fd` | 6 |
| `9086..9332` | 684 | `9b40a84d48486127e5fc46671c545e861fe50f3a222f8a454b419e9093e71f85` | 74 |
| `9332..9344` | 18 | `bfca5a08788474fe8c1411a7fad01bac8607496180d63af5c9fd431a11c59bb7` | 3 |

- [F] 앞 4 범위(범위 문서 hull) 연결 1,686바이트 SHA256 `117b5f4f913fb31846663d6dad10b7b8af4fc64d088e506929212a054547941c`.
- [F] 범위 이웃: `313a`(`3130..313c` 다른 함수의 RTS) `3144`(`MOVE.W D0,104cd2.l`, 참조 별도) `31d4`(`3162` 함수의 RTS, F5 C2) `3900`(card_menu 뒤 RTS) `9084`(자료) `9344`(`MOVE.B #18,D0`, `9344..` 별도 함수)는 routing 밖이다. `35a2`(transition) `3918`(card_menu_open)은 다른 실행부다.
- [F] 자료: ROM WORD `000180` = `0000`. pause 문자열 `9068..9086` = `\l\x12\x1a\p\0\c\x03PAUSE\0\0\l\x12\x1a\c\x03     \0`(`9238` A0 = `9079`, `924c` A0 = `9068`, `928e` A0 = `9079`; H2는 읽지 않고 `3902`/`3918`이 부르는 card menu 실행부가 읽는다). `92d4`의 A0 = `93e0`(menu 표, `a29c`가 읽음). replay 표 `f0dfe` = LONG `000f01fe` `000f07fe` …, recorder 표 `f1a06` = LONG `000f0e06` `000f1406` …(둘 다 `3162`가 읽으며 H2 범위 밖).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "FLOW"(C 보존), "guard", "입력 …"(queue 읽기 순서). 태그 없는 block은 Unknown이다. d16(An)·`(An,Dn.W)`는 부호 확장한다.

**입력 repeat 설정 `313c`(`91a4 JSR`, 범위 밖 `3110 BSR`) 1**
- `313c`: `MOVE.W #1002, -332e(a5); RTS`

**입력 sampler `31d6`(`f24 JSR`) 49**
- `31d6`: `MOVE.B 380000.l, d0; NOT.B d0; ANDI.B #f, d0; MOVE.B -334c(a5), d1; MOVE.B d0, -334c(a5); EOR.B d0, d1; AND.B d0, d1; MOVE.B d1, -334b(a5); MOVE.B 300000.l, d0; NOT.B d0; LEA.L -334a(a5), a0; MOVE.B 2(a0), d1; MOVE.B d1, 1(a0); MOVE.B d0, 2(a0); EOR.B d0, d1; AND.B d0, d1; MOVE.B d1, 3(a0); BEQ.W 3226` (→`3216`) — 입력 `380000` `300000`
- `3216`: `MOVE.B d1, 4(a0); MOVE.B 104cd2.l, 5(a0); BRA.W 3242`
- `3226`: `SUBQ.B #1, 5(a0); BNE.W 323e` (→`322e`)
- `322e`: `MOVE.B d0, 4(a0); MOVE.B 104cd3.l, 5(a0); BRA.W 3242`
- `323e`: `CLR.B 4(a0)` (→`3242`)
- `3242`: `MOVE.B 340000.l, d0; NOT.B d0; LEA.L -3344(a5), a0;` 이하 `31fe..3212`와 같은 6명령`; BEQ.W 3276` (→`3266`) — 입력 `340000`
- `3266` / `3276` / `327e` / `328e`: `3216` / `3226` / `322e` / `323e`와 같은 형태(대상 `3292`, `3276`의 BNE 대상 `328e`)
- `3292`: `CMPI.B #0, -332c(a5); BNE.W 334e` (→`329c`)
- `329c`: `MOVE.B 10fd94.l, -3358(a5); MOVE.B 300000.l, d0; NOT.B d0; LEA.L -3358(a5), a0;` 같은 6명령`; BEQ.W 32d8` (→`32c8`) — 입력 `300000`
- `32c8` / `32d8` / `32e0` / `32f0`: 같은 형태(대상 `32f4`)
- `32f4`: `MOVE.B 10fd9a.l, -3352(a5); MOVE.B 340000.l, d0; NOT.B d0; LEA.L -3352(a5), a0;` 같은 6명령`; BEQ.W 3330` (→`3320`) — 입력 `340000`
- `3320` / `3330` / `3338` / `3348`: 같은 형태(대상 `334c`)
- `334c`: `RTS` — FLOW
- `334e`: `CMPI.B #1, -332c(a5); BNE.W 3406` (→`3358`)
- `3358`: `TST.W 180.w; BEQ.W 3368` (→`3360`)
- `3360`: `BSR.W 349c` — FLOW
- `3364`: `BRA.W 336c` — FLOW
- `3368`: `BSR.W 352a` — FLOW
- `336c`: `MOVE.B -333e(a5), d0; LEA.L -3358(a5), a0;` 같은 6명령`; BEQ.W 339c` (→`338c`)
- `338c` / `339c` / `33a4` / `33b4`: 같은 형태(대상 `33b8`)
- `33b8`: `MOVE.B -333d(a5), d0; LEA.L -3352(a5), a0;` 같은 6명령`; BEQ.W 33e8` (→`33d8`)
- `33d8` / `33e8` / `33f0` / `3400`: 같은 형태(대상 `3404`)
- `3404`: `RTS` — FLOW
- `3406`: `CLR.B d0; LEA.L -3358(a5), a0;` 같은 6명령`; BEQ.W 3434` (→`3424`)
- `3424` / `3434` / `343c` / `344c`: 같은 형태(대상 `3450`)
- `3450`: `CLR.B d0; LEA.L -3352(a5), a0;` 같은 6명령`; BEQ.W 347e` (→`346e`)
- `346e` / `347e` / `3486` / `3496`: 같은 형태(대상 `349a`)
- `349a`: `RTS` — FLOW

**입력 recorder `349c`(`3360 BSR`) 10**
- `349c`: `MOVE.B 300000.l, d0; NOT.B d0; LSL.W #8, d0; MOVE.B 340000.l, d0; NOT.B d0; MOVE.W -333e(a5), d1; MOVE.W d0, -333e(a5); EOR.W d1, d0; MOVEA.L -3338(a5), a0; MOVE.B -3330(a5), d5; MOVE.W -3332(a5), d6; MOVE.W -3334(a5), d7; CMP.W d6, d7; SNE.B d1; ORI.B #f, d1; CMP.B d5, d1; BNE.W 34e6` (→`34d6`) — 입력 `300000` `340000`
- `34d6`: `MOVE.B d5, (a0, d6.w); ADDQ.W #1, d6; CMPI.W #600, d6; BCC.W 3522` (→`34e4`)
- `34e4`: `CLR.B d5` (→`34e6`)
- `34e6`: `TST.W d0; BEQ.W 3512` (→`34ec`)
- `34ec`: `MOVEQ #f, d1` (→`34ee`)
- `34ee`: `LSL.W #1, d0; BCC.W 350e` (→`34f4`)
- `34f4`: `MOVE.B d5, (a0, d6.w); CLR.W d5; ADDQ.W #1, d6; MOVE.B d1, d2; LSL.B #4, d2; OR.B d2, (a0, d7.w); MOVE.W d6, d7; CMPI.W #600, d6; BCC.W 3522; DBRA d1, 34ee` (→`3512`) — `BCC`·`DBRA` 묶음
- `350e`: `DBRA d1, 34ee` (→`3512`) — FLOW
- `3512`: `MOVE.W d6, -3332(a5); MOVE.W d7, -3334(a5); ADDQ.B #1, d5; MOVE.B d5, -3330(a5); RTS`
- `3522`: `MOVE.B #2, -332c(a5); RTS`

**입력 replay `352a`(`3368 BSR`) 11**
- `352a`: `MOVEA.L 104cc4.l, a0; MOVE.W -3332(a5), d7` (→`3534`)
- `3534`: `CMPI.W #600, d7; BCC.W 359a` (→`353c`)
- `353c`: `MOVE.B (a0, d7.w), d0; MOVE.B #ff, d1; CMP.W -3334(a5), d7; BNE.W 3552` (→`354c`)
- `354c`: `MOVE.B #f, d1; AND.B d1, d0` (→`3552`)
- `3552`: `CMP.B -3330(a5), d0; BNE.W 3590` (→`355a`)
- `355a`: `MOVE.B #0, -3330(a5); ADDQ.W #1, d7; CMP.B d1, d0; BNE.W 3572` (→`3568`)
- `3568`: `TST.B (a0, d7.w); BNE.W 3590` (→`3570`)
- `3570`: `ADDQ.W #1, d7` (→`3572`)
- `3572`: `MOVE.W -3334(a5), d0; MOVE.W d7, -3334(a5); MOVE.B (a0, d0.w), d0; LSR.B #4, d0; MOVE.W 104cc2.l, d1; BCHG.B d0, d1; MOVE.W d1, 104cc2.l; BRA.B 3534`
- `3590`: `MOVE.W d7, -3332(a5); ADDQ.B #1, -3330(a5); RTS`
- `359a`: `MOVE.B #2, -332c(a5); RTS`

**문자열 출력 `3902`(`9250 JSR`) 6**
- `3902`: `MOVE.W d0, d3` (→`3904`)
- `3904`: `BSR.W 386e` — FLOW
- `3908`: `CMPI.B #0, d2; BNE.W 3912` (→`3910`)
- `3910`: `RTS` — FLOW
- `3912`: `BSR.W 3650` — FLOW
- `3916`: `BRA.B 3904` — FLOW

**start 판정 `9086`(`9168` `91cc BSR`, 범위 밖 `9430`) 24**
- `9086`: `MOVEQ #0, d0; CMPI.B #2, -7fee(a5); BNE.W 910e` (→`9092`)
- `9092`: `TST.B 7d82(a5); BNE.W 90a2` (→`909a`)
- `909a`: `MOVE.B -334b(a5), d0; BRA.W 90d2`
- `90a2`: `TST.B 7002(a5); BEQ.W 90d2` (→`90aa`)
- `90aa`: `MOVEQ #0, d0; BTST.B #7, -3347(a5); BEQ.W 90ba` (→`90b6`)
- `90b6`: `BSET.B #1, d0` (→`90ba`) — FLOW
- `90ba`: `BTST.B #7, -3341(a5); BEQ.W 90c8` (→`90c4`) — FLOW
- `90c4`: `BSET.B #3, d0` (→`90c8`) — FLOW
- `90c8`: `MOVE.B -334c(a5), d1; ANDI.B #a, d1; AND.B d1, d0` (→`90d2`)
- `90d2`: `CMPI.B #0, 7db6(a5); BNE.W 90e0` (→`90dc`)
- `90dc`: `BCLR.B #1, d0` (→`90e0`) — FLOW
- `90e0`: `CMPI.B #3, 7db6(a5); BNE.W 90ee` (→`90ea`)
- `90ea`: `BCLR.B #1, d0` (→`90ee`) — FLOW
- `90ee`: `CMPI.B #0, 7db7(a5); BNE.W 90fc` (→`90f8`)
- `90f8`: `BCLR.B #3, d0` (→`90fc`) — FLOW
- `90fc`: `CMPI.B #3, 7db7(a5); BNE.W 910a` (→`9106`)
- `9106`: `BCLR.B #3, d0` (→`910a`) — FLOW
- `910a`: `BRA.W 9134` — FLOW
- `910e`: `TST.B 7002(a5); BEQ.W 9134` (→`9116`)
- `9116`: `MOVEQ #0, d0; BTST.B #7, -3347(a5); BEQ.W 9126` (→`9122`)
- `9122`: `BSET.B #1, d0` (→`9126`) — FLOW
- `9126`: `BTST.B #7, -3341(a5); BEQ.W 9134` (→`9130`) — FLOW
- `9130`: `BSET.B #3, d0` (→`9134`) — FLOW
- `9134`: `RTS` — FLOW

**pause/menu 요청 `9136`(`f54 JSR`) 50**
- `9136`: `TST.B -210(a5); BNE.W 91c2` (→`913e`)
- `913e`: `MOVE.B -20f(a5), d0; BEQ.W 9154` (→`9146`)
- `9146`: `MOVE.B d0, -210(a5); MOVE.B #0, -20f(a5); BRA.W 919a`
- `9154`: `BTST.B #1, 10f000.l; BNE.W 9168` (→`9160`) — FLOW
- `9160`: `TST.B -211(a5); BNE.W 9196` (→`9168`)
- `9168`: `BSR.W 9086` — FLOW
- `916c`: `TST.B d0; BEQ.W 9196` (→`9172`)
- `9172`: `BTST.B #1, d0; BEQ.W 9184` (→`917a`) — FLOW
- `917a`: `ORI.B #1, -210(a5); BRA.W 919a`
- `9184`: `BTST.B #3, d0; BEQ.W 9196` (→`918c`) — FLOW
- `918c`: `ORI.B #2, -210(a5); BRA.W 919a`
- `9196`: `MOVEQ #1, d0; RTS`
- `919a`: `MOVE.L #0, 107df6.l; JSR 313c.l`
- `91aa`: `MOVE.B #0, -20d(a5); MOVE.B -3356(a5), -204(a5); MOVE.B -3350(a5), -203(a5); MOVEQ #0, d0; BRA.W 92a8`
- `91c2`: `TST.B 107dee.l; BNE.W 92fc` (→`91cc`)
- `91cc`: `BSR.W 9086` — FLOW
- `91d0`: `BTST.B #0, -210(a5); BEQ.W 91fe` (→`91da`) — FLOW
- `91da`: `BTST.B #1, d0; BNE.W 928a` (→`91e2`) — FLOW
- `91e2`: `TST.B 7002(a5); BEQ.W 91fe` (→`91ea`)
- `91ea`: `BTST.B #0, -334b(a5); BNE.W 925e` (→`91f4`) — FLOW
- `91f4`: `BTST.B #0, -334c(a5); BNE.W 926c` (→`91fe`) — FLOW
- `91fe`: `BTST.B #1, -210(a5); BEQ.W 922c` (→`9208`) — FLOW
- `9208`: `BTST.B #3, d0; BNE.W 928a` (→`9210`) — FLOW
- `9210`: `TST.B 7002(a5); BEQ.W 922c` (→`9218`)
- `9218`: `BTST.B #2, -334b(a5); BNE.W 925e` (→`9222`) — FLOW
- `9222`: `BTST.B #2, -334c(a5); BNE.W 926c` (→`922c`) — FLOW
- `922c`: `BTST.B #6, 10f001.l; BNE.W 9256` (→`9238`) — FLOW
- `9238`: `LEA.L 9079(pc), a0; SUBQ.B #1, -20d(a5); MOVE.B -20d(a5), d7; ANDI.B #30, d7; BEQ.W 9250` (→`924c`)
- `924c`: `LEA.L 9068(pc), a0` (→`9250`) — FLOW
- `9250`: `JSR 3902.l` — FLOW
- `9256`: `MOVE.W #0, d0; BRA.W 92a8`
- `925e`: `MOVE.B #f, -20e(a5); MOVE.W #2, d0; BRA.W 92a8`
- `926c`: `SUBQ.B #1, -20e(a5); BCC.W 9282` (→`9274`)
- `9274`: `MOVE.B #1, -20e(a5); MOVE.W #2, d0; BRA.W 92a8`
- `9282`: `MOVE.W #0, d0; BRA.W 92a8`
- `928a`: `BRA.W 92ce` — FLOW
- `928e`: `LEA.L e84c8.l, a1; LEA.L 9079(pc), a0; JSR 3918.l` — FLOW
- `929e`: `CLR.B -212(a5); CLR.B -210(a5); MOVEQ #1, d0` (→`92a8`)
- `92a8`: `MOVE.B -3356(a5), d6; MOVE.B -204(a5), d7; EOR.B d6, d7; AND.B d6, d7; OR.B d7, -3355(a5); MOVE.B -3350(a5), d6; MOVE.B -203(a5), d7; EOR.B d6, d7; AND.B d6, d7; OR.B d7, -334f(a5); SUBQ.B #1, -20d(a5); RTS`
- `92ce`: `JSR ca9e.l` — FLOW
- `92d4`: `MOVE.B #ff, -212(a5); LEA.L 93e0(pc), a0; MOVE.W #4, d0; MOVE.W #8, d1; JSR a29c.l`
- `92ec`: `LEA.L 9332(pc), a0; JSR a2b8.l` — FLOW
- `92f6`: `MOVE.W #0, -206(a5)` (→`92fc`)
- `92fc`: `JSR a370.l` — FLOW
- `9302`: `TST.B d0; BEQ.W 932a` (→`9308`)
- `9308`: `MOVE.B #0, -212(a5); MOVEA.L -20a(a5), a0; CMPA.W #0, a0; BEQ.W 931c` (→`931a`)
- `931a`: `JSR (a0)` — guard
- `931c`: `CMPI.W #1, -206(a5); BEQ.W 928e` (→`9326`)
- `9326`: `BRA.W 92a8` — FLOW
- `932a`: `MOVE.W #0, d0; BRA.W 92a8`

**pause menu renderer `9332`(결정 1, `92ec`가 설치) 3**
- `9332`: `CMPI.B #3, d1; BNE.W 933e` (→`933a`)
- `933a`: `MOVE.B #6b, d1` (→`933e`)
- `933e`: `JMP e84c8.l` — FLOW

- [F] 실행 의미 보충(명령 순서대로 읽기·쓰기; `.W`/`.B`는 나머지 bit 보존; 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow·shift에 기대지 않는다; 메모리 RMW(`SUBQ.B` `ADDQ.B` `ORI.B` `OR.B`)는 읽은 뒤 쓴다; `CLR.B`/`CLR.W` 메모리는 쓰기만 모델한다):
  - **latch 6명령**(`31fe..3212` 형태, 블록 끝 BEQ 포함): `D1.B` = BYTE `2(A0)`(이전 현재값), BYTE `1(A0)` = `D1.B`, BYTE `2(A0)` = `D0.B`, `D1.B` = (`D1.B` ^ `D0.B`) & `D0.B`(새로 눌림), BYTE `3(A0)` = `D1.B`; `D1.B` = 0이면 repeat 경로(`…26`/`…76` 형태), 아니면 edge 경로. **edge**(`3216` 형태): BYTE `4(A0)` = `D1.B`, BYTE `5(A0)` = BYTE `104cd2`. **repeat**(`3226` 형태): BYTE `5(A0)` −= 1; ≠ 0이면 clear(`323e` 형태: BYTE `4(A0)` = 0), = 0이면 expire(`322e` 형태: BYTE `4(A0)` = `D0.B`, BYTE `5(A0)` = BYTE `104cd3`). A0 = A5 + sext(disp)(블록 = `104cb6` P1 장치, `104cbc` P2 장치, `104ca8` P1 논리, `104cae` P2 논리; A5 = `108000` 기준).
  - `31d6`: `D0.B` = ~queue(`380000`) & `f`; `D1.B` = BYTE `-334c(A5)`; BYTE `-334c(A5)` = `D0.B`; `D1.B` = (`D1.B` ^ `D0.B`) & `D0.B`; BYTE `-334b(A5)` = `D1.B`; `D0.B` = ~queue(`300000`); A0 = A5 − `334a`; latch. `3242`: `D0.B` = ~queue(`340000`), A0 = A5 − `3344`, latch. `3292`: BYTE `-332c(A5)` ≠ 0이면 `334e`. `329c`: BYTE `-3358(A5)` = BYTE `10fd94`(읽고 쓰기), `D0.B` = ~queue(`300000`), A0 = A5 − `3358`, latch. `32f4`: BYTE `-3352(A5)` = BYTE `10fd9a`, `D0.B` = ~queue(`340000`), A0 = A5 − `3352`, latch.
  - `334e`: BYTE `-332c(A5)` ≠ 1이면 `3406`. `3358`: WORD(`000180`, live bus) = 0이면 `3368`, 아니면 `3360`. `3360`: `BSR 349c`(복귀 `3364`). `3364`: `BRA 336c`. `3368`: `BSR 352a`(복귀 `336c`). `336c`: `D0.B` = BYTE `-333e(A5)`, A0 = A5 − `3358`, latch. `33b8`: `D0.B` = BYTE `-333d(A5)`, A0 = A5 − `3352`, latch. `3406`/`3450`: `D0.B` = 0, A0 = A5 − `3358`/A5 − `3352`, latch(새로 눌림은 항상 0이라 edge `3424`/`346e`는 직접 진입으로만 닿는다).
  - `349c`: `D0.B` = ~queue(`300000`); `D0.W` = (`D0.W` << 8) & `ffff`; `D0.B` = ~queue(`340000`); `D1.W` = WORD `-333e(A5)`; WORD `-333e(A5)` = `D0.W`; `D0.W` ^= `D1.W`; A0 = LONG `-3338(A5)`; `D5.B` = BYTE `-3330(A5)`; `D6.W` = WORD `-3332(A5)`; `D7.W` = WORD `-3334(A5)`; `D1.B` = (`D7.W` ≠ `D6.W`) ? `ff` : 0; `D1.B` |= `f`; `D1.B` ≠ `D5.B`이면 `34e6`. `34d6`: BYTE(A0 + sext(`D6.W`)) = `D5.B`; `D6.W` += 1; `D6.W` ≥ `600`(부호 없는)이면 `3522`. `34e4`: `D5.B` = 0. `34e6`: `D0.W` = 0이면 `3512`. `34ec`: `D1` = `f`(LONG). `34ee`: c = bit 15 of `D0.W`; `D0.W` = (`D0.W` << 1) & `ffff`; c = 0이면 `350e`. `34f4`: BYTE(A0 + sext(`D6.W`)) = `D5.B`; `D5.W` = 0; `D6.W` += 1; `D2.B` = (`D1.B` << 4) & `ff`; BYTE(A0 + sext(`D7.W`)) |= `D2.B`; `D7.W` = `D6.W`; `D6.W` ≥ `600`이면 `3522`; 아니면 `DBRA D1`(`D1.W` −= 1; ≠ `ffff`이면 `34ee`, 아니면 `3512`). `350e`: `DBRA D1`. `3512`: WORD `-3332(A5)` = `D6.W`, WORD `-3334(A5)` = `D7.W`, `D5.B` += 1, BYTE `-3330(A5)` = `D5.B`, RTS. `3522`: BYTE `-332c(A5)` = 2, RTS.
  - `352a`: A0 = LONG `104cc4`(절대 주소), `D7.W` = WORD `-3332(A5)`. `3534`: `D7.W` ≥ `600`(부호 없는)이면 `359a`. `353c`: `D0.B` = BYTE(A0 + sext(`D7.W`))(live bus), `D1.B` = `ff`; `D7.W` ≠ WORD `-3334(A5)`이면 `3552`. `354c`: `D1.B` = `f`, `D0.B` &= `f`. `3552`: `D0.B` ≠ BYTE `-3330(A5)`이면 `3590`. `355a`: BYTE `-3330(A5)` = 0, `D7.W` += 1; `D0.B` ≠ `D1.B`이면 `3572`. `3568`: BYTE(A0 + sext(`D7.W`)) ≠ 0이면 `3590`. `3570`: `D7.W` += 1. `3572`: `D0.W` = WORD `-3334(A5)`; WORD `-3334(A5)` = `D7.W`; `D0.B` = BYTE(A0 + sext(`D0.W`)); `D0.B` >>= 4; `D1.W` = WORD `104cc2`(절대); `D1` bit (`D0` & 31)(레지스터 대상 BCHG는 LONG, bit 번호 mod 32) 반전; WORD `104cc2` = `D1.W`; `BRA 3534`. `3590`: WORD `-3332(A5)` = `D7.W`, BYTE `-3330(A5)` += 1, RTS. `359a`: BYTE `-332c(A5)` = 2, RTS. [F] 루프 한 번이 `3572` block 실행 한 번이고, 매 반복 `D7.W`가 1 이상 늘어 `600`에서 끝난다.
  - `3902`: `D3.W` = `D0.W`. `3904`: `BSR 386e`(복귀 `3908`). `3908`: `D2.B` ≠ 0이면 `3912`. `3910`: RTS. `3912`: `BSR 3650`(복귀 `3916`). `3916`: `BRA 3904`.
  - `9086`: `D0` = 0; BYTE `-7fee(A5)`(`100012`) ≠ 2이면 `910e`. `9092`: BYTE `7d82(A5)`(`10fd82`) ≠ 0이면 `90a2`. `909a`: `D0.B` = BYTE `-334b(A5)`, `BRA 90d2`. `90a2`/`910e`: BYTE `7002(A5)`(`10f002`) = 0이면 `90d2`/`9134`. `90aa`/`9116`: `D0` = 0; BYTE `-3347(A5)` bit 7 = 0이면 `90ba`/`9126`. `90b6`/`9122`: `D0` bit 1 set. `90ba`/`9126`: BYTE `-3341(A5)` bit 7 = 0이면 `90c8`/`9134`. `90c4`/`9130`: `D0` bit 3 set. `90c8`: `D1.B` = BYTE `-334c(A5)` & `a`; `D0.B` &= `D1.B`. `90d2`/`90e0`: BYTE `7db6(A5)` ≠ 0/≠ 3이면 다음 비교, 같으면 `90dc`/`90ea`(`D0` bit 1 clear). `90ee`/`90fc`: BYTE `7db7(A5)`로 같은 일(`90f8`/`9106`: bit 3 clear). `910a`: `BRA 9134`. `9134`: RTS. 레지스터 대상 `BSET`/`BCLR`은 LONG(bit 1, 3).
  - `9136`: BYTE `-210(A5)`(`107df0`) ≠ 0이면 `91c2`. `913e`: `D0.B` = BYTE `-20f(A5)`; = 0이면 `9154`. `9146`: BYTE `-210(A5)` = `D0.B`, BYTE `-20f(A5)` = 0, `BRA 919a`. `9154`: BYTE `10f000` bit 1 ≠ 0이면 `9168`. `9160`: BYTE `-211(A5)` ≠ 0이면 `9196`. `9168`: `BSR 9086`(복귀 `916c`). `916c`: `D0.B` = 0이면 `9196`. `9172`/`9184`: `D0` bit 1/3(레지스터 BTST, bit mod 32) = 0이면 `9184`/`9196`. `917a`/`918c`: BYTE `-210(A5)` |= 1/2, `BRA 919a`. `9196`: `D0` = 1, RTS. `919a`: LONG `107df6` = 0, `JSR 313c`(복귀 `91aa`). `91aa`: BYTE `-20d(A5)` = 0, BYTE `-204(A5)` = BYTE `-3356(A5)`, BYTE `-203(A5)` = BYTE `-3350(A5)`, `D0` = 0, `BRA 92a8`.
  - `91c2`: BYTE `107dee` ≠ 0이면 `92fc`. `91cc`: `BSR 9086`(복귀 `91d0`). `91d0`: BYTE `-210(A5)` bit 0 = 0이면 `91fe`. `91da`: `D0` bit 1 ≠ 0이면 `928a`. `91e2`/`9210`: BYTE `7002(A5)` = 0이면 `91fe`/`922c`. `91ea`/`9218`: BYTE `-334b(A5)` bit 0/2 ≠ 0이면 `925e`. `91f4`/`9222`: BYTE `-334c(A5)` bit 0/2 ≠ 0이면 `926c`. `91fe`: BYTE `-210(A5)` bit 1 = 0이면 `922c`. `9208`: `D0` bit 3 ≠ 0이면 `928a`. `922c`: BYTE `10f001` bit 6 ≠ 0이면 `9256`. `9238`: A0 = `9079`; BYTE `-20d(A5)` −= 1; `D7.B` = 그 BYTE & `30`; = 0이면 `9250`. `924c`: A0 = `9068`. `9250`: `JSR 3902`(복귀 `9256`). `9256`/`9282`/`932a`: `D0.W` = 0, `BRA 92a8`. `925e`: BYTE `-20e(A5)` = `f`, `D0.W` = 2, `BRA 92a8`. `926c`: BYTE `-20e(A5)` −= 1; 빌림 없음(이전 ≠ 0)이면 `9282`. `9274`: BYTE `-20e(A5)` = 1, `D0.W` = 2. `928a`: `BRA 92ce`. `928e`: A1 = `e84c8`, A0 = `9079`, `JSR 3918`(복귀 `929e`). `929e`: BYTE `-212(A5)` = 0, BYTE `-210(A5)` = 0, `D0` = 1.
  - `92a8`: `D6.B` = BYTE `-3356(A5)`; `D7.B` = BYTE `-204(A5)`; `D7.B` = (`D7.B` ^ `D6.B`) & `D6.B`; BYTE `-3355(A5)` |= `D7.B`; 같은 일을 `-3350`/`-203`/`-334f`로; BYTE `-20d(A5)` −= 1; RTS.
  - `92ce`: `JSR ca9e`(복귀 `92d4`). `92d4`: BYTE `-212(A5)` = `ff`, A0 = `93e0`, `D0.W` = 4, `D1.W` = 8, `JSR a29c`(복귀 `92ec`). `92ec`: A0 = `9332`, `JSR a2b8`(복귀 `92f6`). `92f6`: WORD `-206(A5)` = 0. `92fc`: `JSR a370`(복귀 `9302`). `9302`: `D0.B` = 0이면 `932a`. `9308`: 결정 4. `931c`: WORD `-206(A5)` = 1이면 `928e`. `9326`: `BRA 92a8`.
  - `9332`: `D1.B` ≠ 3이면 `933e`. `933a`: `D1.B` = `6b`. `933e`: PC = `e84c8`(JMP, 복귀 LONG 없음).

## carry

- [F] **소비 0, known 생산 0.** H2 안의 모든 Bcc·`DBRA`는 같은 block에서 만든 flag나 레지스터만 읽는다(`34ee`의 `BCC`는 같은 block의 `LSL.W`, `34f4`·`34d6`의 `BCC`는 같은 block의 `CMPI.W`, `926c`의 `BCC`는 같은 block의 `SUBQ.B`). BSR/JSR 복귀점 block(`3364` `336c` `3908` `3916` `916c` `91aa` `91d0` `9256` `929e` `92d4` `92ec` `92f6` `9302`)은 C를 읽기 전에 새 flag를 만들거나 C를 읽지 않는다. 범위 밖 호출자 복귀점(`f2a` FLOW → `b68` Unknown, `f5a` `MOVE`/`BNE`, `3114` `CLR`, `9434` `BTST`, `3902` 호출자 중 routing된 `8f4e`→`8f50 MOVEQ`)도 H2 RTS 앞 C를 읽지 않는다. `3910 RTS`의 C는 원본에서 항상 0(`3908 CMPI.B #0`)이지만 소비자가 없어 known 생산으로 모델하지 않는다(관례: 소비자 없는 known carry는 두지 않는다). 따라서 carry 오류 문자열은 두지 않는다.
- [F] **FLOW_ONLY 46 block**(C 보존): `334c` `3360` `3364` `3368` `3404` `349a` `350e` `3904` `3910` `3912` `3916` `90b6` `90ba` `90c4` `90dc` `90ea` `90f8` `9106` `910a` `9122` `9126` `9130` `9134` `9154` `9168` `9172` `9184` `91cc` `91d0` `91da` `91ea` `91f4` `91fe` `9208` `9218` `9222` `922c` `924c` `9250` `928a` `928e` `92ce` `92ec` `92fc` `9326` `933e`. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석 붙은 case group 하나)에 46 PC를 넣는다.
- [F] **guard 1 block**(`931a`): 실행하지 않으므로 C 분류가 없다(보존 목록에 넣지 않는다).
- [F] **Unknown 107 block**: 나머지(`MOVE`/`MOVEQ`/`CLR`/`NOT`/`EOR`/`AND`/`ANDI`/`OR`/`ORI`/`CMP`/`CMPI`/`CMPA`/`TST`/`ADDQ`/`SUBQ`/`LSL`/`LSR`/`SNE`/`BCHG`가 든 block; queue 읽기 block 5개 포함).

## 경계와 external read·pause 모델

- [F] **stop-only 경계(H2가 실행하지 않음):** 위 요약의 callee 8개와 호출자 복귀. 단위 시험은 이 PC들을 stop으로만 쓰고 "routing 밖" rollback 탐침으로 쓰지 않는다(F4 시험 경계 관례). rollback 탐침은 work RAM PC `10fe00..10fefe`를 쓴다.
- [F] **external read(D4):** 결정 사항 없음(H1 queue 절 그대로). 실행부는 `am_read(c, 380000/300000/340000, 1, v)`만 부르고, queue 머리 검사·소비·rollback은 공통 `am_read`/`run_animation_machine`이 한다. 한 block이 두 건을 읽을 때(`31d6` `349c`) 둘째 읽기가 실패하면 block 전체가 실패하고 run 전체가 입력 그대로 남는다(첫 소비도 되돌아간다).
- [F] **replay stream:** `352a..3590`의 BYTE 읽기는 live bus(work RAM 또는 physical ROM 창)다. 자연 replay 표 값은 fixed ROM `f01fe..`이다(`3162` 선택, C2 범위). 실행부는 주소를 해석하지 않는다.
- [F] **pause 루프:** 결정 3.
- [F] **스택:** BSR/JSR 복귀 LONG(`3360` `3368` `3904` `3912` `9168` `91cc` `919a` `9250` `928e` `92ce` `92d4` `92ec` `92fc`)과 RTS pop. `933e`는 JMP라 스택을 바꾸지 않는다. work RAM 밖 스택은 기존 checked 오류다.

## 구현 범위와 규약

- routing 4 범위(결정 1). 짝수 PC 852개 중 block 시작 154, 내부 698. 내부 PC 직접 진입은 `unsupported animation frame head h2 PC`다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVEA`·`LEA`는 LONG 전체). 레지스터 대상 `BSET`/`BCLR`/`BCHG`/`BTST`는 LONG bit(번호 mod 32), 메모리 대상은 BYTE bit(번호 mod 8)다. 반복 block(`3534`..`3572`, `34ee`/`34f4`/`350e`, `3904`..`3916`)은 원본처럼 block 실행 한 번이 한 반복이다.
- 기존 실행부는 고치지 않는다. 공유 최소 수정: `animation_machine.cpp` routing `else if` 하나와 carry 보존 case group 하나, `animation_machine_internal.h` 선언 하나, `Makefile`(source 목록·test target·실행 줄), `tools/verify_animation_machine.py` SOURCES. 결정 6의 test 기대 교체 3곳(두 test 파일).

## 자료

- [F] fixed ROM(live bus): WORD `000180`. replay stream(LONG `104cc4`가 가리키는 곳).
- [F] work RAM(A5 = `108000` 기준 자연 주소): `100012`(`-7fee`), `104ca8..104cb1`(`-3358..-334f`, P1/P2 논리 블록), `104cb4` `104cb5`(`-334c` `-334b`, system), `104cb6..104cbb`(`-334a`, P1 장치 블록), `104cb9`(`-3347`), `104cbc..104cc1`(`-3344`, P2 장치 블록), `104cbf`(`-3341`), `104cc2`(WORD replay 입력, 절대), `104cc4`(LONG replay pointer, 절대), `104cc8`(`-3338`, LONG recorder buffer), `104ccc` `104cce` `104cd0`(`-3334` `-3332` `-3330`), `104cd2` `104cd3`(repeat 지연·간격, 절대; `-332e` WORD), `104cd4`(`-332c`, 입력 mode), `107dee`(`-212`, 절대 읽기) `107def` `107df0` `107df1` `107df2` `107df3`(`-211..-20d`), `107df6`(`-20a`, LONG menu callback; `919a`는 절대 주소로 씀), `107dfa`(`-206`), `107dfc` `107dfd`(`-204` `-203`), `10f000` `10f001`(절대), `10f002`(`7002`), `10fd82`(`7d82`), `10fd94` `10fd9a`(절대), `10fdb6` `10fdb7`(`7db6` `7db7`).
- [F] device: 읽기 `380000` `300000` `340000`(결정 없음, H1 queue 절).

## 시험 계획

- 단위 시험(`engine/tests/animation_machine_frame_head_h2_test.cpp`, `run_animation_machine`만): Unicorn 생성 fixture(scratch 생성기, 원본 ROM + 합성 physical 바이트 `0180..0182`·replay stream 창; 입력은 선언 queue), 154 시작 전부, block 표(시작 × 들어오는 C Unknown/clear/set: native 후속·digest·queue 소비 수·C 분류), zero-step(154 × C 3), 내부 PC 698 전수(정확한 오류), 범위 양끝 홀수 PC, guard `931a`(C 3가지), queue 오류(빈 queue·주소/크기 불일치, 두 번째 읽기 실패 시 첫 소비 rollback), 경계 stop(`386e` `3650` `3918` `ca9e` `a29c` `a2b8` `a370` `e84c8`, 호출자 복귀), RAM rollback 탐침 `10fexx`, H1과 이어지는 행(`f12`→`31d6`→`f2a`, `f54`→`9136`→`f5a`)과 pause 루프 행(결정 3의 a·b·c).
- 실제 ROM 차분(Unicorn vs C++ + 8 `program_rom_*.ms5d`, queue 포함), native F5 관측의 자연 H 시작 상태에서 H1+H2+H3+H4 전체 차분(H가 어디서 멈추는지 보고)과 관측 입력 변종(`input-rand` `input-all` `input-start`, 가능하면 `vblank1` `vblank2` `combo`), 돌연변이 검사, UBSan, base frame pass·RNG 400 무변화.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다. 작업 트리 `metalslug-h2`(base `9643372`), scratch `ms5-scratch/h2/`.
- [F] 실행부 case 집합 = scratch `starts.txt`(154 = 정적 151 + renderer 3). 공유 최소 수정: routing `else if` 하나(4 범위), carry 보존 case group 하나(46 PC), internal.h 선언 하나, Makefile(source·test target·실행 줄), `tools/verify_animation_machine.py` SOURCES. 결정 6의 test 기대 교체 3곳. public header는 바꾸지 않았다.
- [F] `make -j3 all test`: exit 0, 경고 0, `Assert` 줄 0, `tools/tests` unittest 257 OK. H2 test 출력: `animation machine frame head h2: 715 fixtures (17 checked errors, 2 waiting, 3 resumed, 18 kept C), 153 blocks, 2840 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover`) 통과.
- [F] 단위 test(run_animation_machine만; scratch `gen/gen_h2.py` Unicorn 생성, 두 번 생성해 표 SHA256 동일): 715 fixture(성공 698, checked 오류 17: queue empty 7·mismatch 5·menu guard 5), release 3(pause 루프), block 표 153(× 들어오는 C 3, FLOW 46 보존·나머지 Unknown), zero-step 154 × 3, 내부 PC 698 전수(정확한 오류), 범위 양끝 홀수 8, guard `931a` × 3, queue 읽기 block 5개 × C 3 × (빈 queue, 한 건 부족, 크기 불일치, 주소 불일치, 상위 bit) 모두 상태·queue 보존, RTS가 RAM PC `10fe40`으로 가는 rollback, 경계 stop(`386e` `3650` `3918` `ca9e` `a29c` `a2b8` `a370` `e84c8` STOP `b68` `f5a` `c52a`), split = continuous 5쌍, mode 0 sampler 독립 model 400 상태(edge·clear·expire 모두 발생). pause 루프(결정 3): `100017`=1에서 반복마다 `ef2` Waiting(읽기 6건), 해제 뒤 다음 반복, frame step edge에서 controller stop; `100017`=0에서 세 반복(읽기 18건) 뒤 같은 run에서 `c52a`; queue 한 반복분이면 둘째 raster 읽기에서 queue empty와 전체 rollback; pause 진입(`84` 1→0, `3db2` `3d7e` `8bbc` `8bc8` `8c16` `5728`) 뒤 `ef2` Waiting.
- [F] 돌연변이 검사(scratch `mut/mut_h2.py`, scratch 사본만 변형, 109개 + identity): 108/109를 test가 잡았다. 남은 `916c-byte`(`TST.B D0`→`TST.W`)는 등가 돌연변이다: 하위 BYTE가 0이면 뒤의 `BTST #1`/`#3`도 0이라 두 경로 모두 `9196`(D0 = 1)로 간다. 첫 실행의 생존 3개 중 `ix-sign`(`(An,Dn.W)` 부호 확장)·`919a-cb`(LONG 쓰기)는 fixture `3572-rom-ff80`/`-fff0`(합성 ROM 창으로 부호 확장이 보임)·`9136-cb-long`을 더해 잡혔다.
- [F] 실제 ROM 차분(scratch `realrom/real_h2.py`, Unicorn PvcMachine vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, 입력은 native가 요청할 때 seed 난수로 공급하고 순서 기록 → C++에는 그 순서 + 여분 2건): 3 seed × 1,500 case 불일치 0/0/0, 154 시작 전부 진입. 기대 checked 오류(menu guard) 21/29/37, C++ stop C(Unknown/Clear/Set) seed 1 1,438/21/20, 여분 queue 2건은 모든 성공 행에서 남음. native가 무작위 A0로 매핑 밖 접근을 해 깨끗이 멈추지 않은 case는 건너뜀(109/122/93).
- [F] native F5 관측 차분(scratch `realrom/nat_h2.py`, `observation.json` SHA256 `4fe4f796…`, 읽기 전용; 관측기의 순서 있는 `h.ext` 기록을 단일 queue로 사용): 자연 seed 136개의 H 4,975개에서 (a) 시작 digest 4,975/4,975, (b) 전체 H native 재실행이 기록 `h.end`·port digest·대기 목록을 재현(queue 남김 0) 4,975/4,975, (c) H1+H2+H3+H4 native vs C++ 불일치 0. **자연 H 4,975개 전부가 controller 진입 LONG `(1008e4)` = `c52a`에서 멈춘다**(남은 F5 경계 없음). 구간 안 `16bd0` 선언 해제 1,543회, C++ stop C 모두 Unknown, H2 leader 28개 실행. 관측 변종 8종(`combo` `input-all` `input-rand` `input-start` `raster-hi` `raster-mixed` `vblank1` `vblank2`, 6 seed × 122 H = 976)도 재현 976/976·불일치 0·전부 `c52a`(`ef2` 해제 366, `16bd0` 632); 입력 변종이 edge 경로 `3216` `3266` `32c8` `3320`을 더한다.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본): 기준 `9643372` pass 14,648·node 126,694, 불일치 0 → H2 뒤 `diff_results.json` 바이트 동일. RNG 400 frame(`…_rng_f4.py` 사본): 기준 complete 134·pass 53,600·node 403,683·불일치 0 → H2 뒤 `totals` 동일. 새 완주 0, 잃은 seed 0(frame head는 여전히 F2 pass의 stop이다).
- [F] 무효화 목록(수정하지 않음): `tools/verify_animation_machine_card_menu.py` `outside_range_entry_003902`.
- [U] 남은 미확인: recorder(`349c..3522`)는 canonical ROM에서 도달 불가이며 합성 `0180` 창으로만 검증했다. `107df6` menu callback·aux callback의 실제 사용은 미확인(guard). pause menu 전체(`92ce` 이후 `a370` frame과 `9332` renderer)의 card menu 실행부 경로는 경계 stop과 실제 ROM 차분(무작위 상태)으로만 덮었고 자연 관측에는 없다.
