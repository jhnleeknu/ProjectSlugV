# 영역 C 단위 C3(플레이어 객체 `1d1f4` 본체 뒷부분: `1ee00` 상태, 공통 꼬리 `201a2`, 둘째 callback 칸 `84(A6)` 상태들, 230 block) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 범위·block·출구는 `area-c-completion-plan.md` §4.2의 C3 행과 아래 "C3 상세 명세"(계획 §8과 같은 꼴, 이 계약에서 새로 씀)를 기준으로 삼고, 구조·공통 규칙은 C2 계약(`animation-machine-player-c2-contract.md`)·C1 계약·FR9 계약을 따르며 다른 점만 적는다. 단위 이름은 C3, 파일 접두어는 `player_c3`(C++) / `pc3`(V1 spec)다(계획 메인 결정 7). 결정 항목은 작업자 권고안으로 구현했으며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기는 `361ea MOVE.L 200098.l,22(A6)` 하나이고 CPU 주소다(물리 오프셋 `bank_base + 98`). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `5d686ac`(branch `claude/c3-core`; C1 `ff2e284`, E1 `6308f75`, C2 `5d686ac` routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `003b4d86868d11dce31dd6732b5c79f9c1d76e523a75110628d7d11f87c389f5`, `animation_machine_internal.h` `9bb14a08b8beafda059409ccf886f4ed1a83827b3144c6ff2234fb6fb5b92ec6`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/P1/068.pack.gz` `094.pack.gz` `106.pack.gz`, `boot-title-start/boot.pack.gz`, `boot-demo-0/boot.pack.gz`)와 계획의 보정 관측 `ms5-scratch/c1/reobs/`(실행 집합 측정용, 계획 메인 결정 1; 읽기만).
- [F] 시작 목록: 계획 scratch `ms5-scratch/c3/starts_C3.txt`(226개, SHA256 `6452d0d0f8a675c26f0f65201d929b12b86524edb772addb2bac6e737e83874d`, 계획 §6 표의 `6452d0d0f8a675c2`와 같음)에 결정 10의 4개(`1cde0` `1cdf0` `1cdfa` `202a0`)를 더한 **`ms5-scratch/c3/starts_C3_final.txt`(230개, SHA256 `3cbca2ea534fb5f0a98ee4620a5123f5e36545d2b1b7f46cb0b8ccd6d5126a92`)**. 실행부의 `case` label 230개, V1 spec `STARTS`와 집합이 같다(작업자 확인).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/c3/`
  - `remeasure/`(재측정: `keydump_old.py` `keys_old.json` `remeasure2.py` → `r3.json` `r3_C3.txt`), `plan/udetail_C3.txt` `plan/C3.dis.txt`(범위·출구·역어셈블), `work/callers_c3.py`(진입 호출자와 호출 뒤 명령), `work/writers_c3.py`(LONG `84(A6)`·BYTE `a0`/`9c`/`a9` 쓰기 명령 검색, 결과 `w84.txt` `wa0.txt`), `work/natsearch.py`(IO pack 자연 node 검색), `work/c3io.py`(IO run·frame), `work/firststops.py`(예측 첫 정지 PC), `work/mkroot.py` `work/ip_probe.py` `work/bc_probe.py`(검증기 새 기대값 관측), `work/hexsearch.py`(기존 파일의 C3 범위 상수 검색), `mut/`(변이), `realrom/`(실제 ROM 차분), `trial_logs/`(작업자 시험 실행 로그).
- 표기: [F] 원본 바이트·현재 소스·관측 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정 전**(`MS5_REOBS=…/c1/reobs dleft.py`, routing `003b4d86…` = C1+E1+C2): 실행된 routing 밖 PC C **659** / E **12** / D 0, 예측 일치 frame **169,144**, 첫 정지 영역 C 14. 계획 §4.2의 C2 뒤 값과 같다.
- [F] **closure 재측정(C1+E1+C2 routing 상태)**: C2 작업자 방식 그대로 계획 spec `plan/plan_final.json`과 계획 당시 routing(`7233eefc…`)의 단위 key(`remeasure/keys_old.json`)로 현재 routing에서 `cplan3`을 돌렸다(`remeasure2.py`). **C3 = 226 block, 457 명령, 1,938 byte, 시작 목록 SHA `6452d0d0…`(계획과 같음)**, 예측 169,482(+338), 남은 C 532 / E 12, 첫 정지 C 14. `r3_C3.txt`는 `starts_C3.txt`와 바이트 단위로 같다. C4~C8의 시작 목록 SHA도 계획 §6 표와 같다.
  - [F] 차이(기록): 같은 실행에서 C9 `798b4ef1…`(160 block), C10 `712bf006…`(41), C11 `afc56b24…`(139), C13 `ce1e1e7b…`(194)는 계획 표(196 / 197 / 196 / 196)와 다르고 전체 검사는 `starts_equal true, insns_equal false`다. [I] C2가 routing되어 closure가 C2 block을 지나가지 않으므로, C2 block에서만 닿는 미실행 subtree(C2의 미룬 입구 `1de3c` `1e21c` `1e8de` 뒤)가 "나머지 단위"에서 빠진 측정상의 차이다. C3~C8에는 영향이 없다. C9~C13은 계획 결정 3대로 착수 때 다시 잰다.
- [F] **정적 범위(계획 226 block)**: 29 범위, 1,938 byte(이어 붙인 SHA256 `34abd1c3c2f4d2721abb6943322733c8ec645f29eae85423d7ab5cb72b38745a`), 짝수 PC 969(내부 743). **결정 10 반영 뒤(구현)**: 31 범위, 1,974 byte(이어 붙인 SHA256 `0fc3d967b85bbd689727f7f0ae1974a3cdfeaf30bc9f4a6e0a2e8847ee8e4de3`), 짝수 PC 987(내부 757), 시작 230. 범위 안에 기존 routing된 PC는 없다(`make test`의 내부 PC 757개 검사가 모두 C3 오류로 거부됨).
- [F] **측정 결과**(`dleft.py`): 계획 226 block만 연결(routing `7aecd27a…`) C 659 → **532**(−127: 실행된 C3 PC 127개, 그중 block 시작 126개), 예측 169,482(+338). 결정 10의 4 block을 더한 최종(routing `0a8379ca…`) C **529**(보정 관측이 demo frame 431에 기록한 `1cde0` `1cdf0` 등 3개가 더 빠짐), E 12, 예측 일치 frame **169,482**(+338), 첫 정지 C 14. [I] 이 예측 모형은 결정 10의 TB 가림을 보지 못한다: 계획 226 block만으로는 실제 IO가 frame 192/408/312에서 `1cdf0`(C7)에 멈춰 +0이었을 것이다(결정 10).

## C3 상세 명세(계획 §8과 같은 꼴)

### 범위

- [F] **계획 226 block, 457 명령, 1,938 byte, 29 범위**(시작 목록 SHA256 `6452d0d0…`, 범위 이어 붙인 SHA256 `34abd1c3…`) **+ 결정 10의 4 block = 230 block, 1,974 byte, 31 범위**(시작 목록 SHA256 `3cbca2ea534fb5f0a98ee4620a5123f5e36545d2b1b7f46cb0b8ccd6d5126a92`, 범위 이어 붙인 SHA256 `0fc3d967b85bbd689727f7f0ae1974a3cdfeaf30bc9f4a6e0a2e8847ee8e4de3`). 아래 표는 구현 범위다.

| 범위(CPU = 파일 오프셋) | byte | SHA256(앞 16자) | 시작 | 내용 [I] |
| --- | --- | --- | --- | --- |
| `1cb40..1cb44` | 4 | `d0139efb8e594aaf` | 1 | `LEA 94(A6),A1`(→ C5 `1cb44`) |
| `1cde0..1cdea` | 10 | `d030c2843035354d` | 1 | 결정 10: C2 `1cdd8`의 fall-through, `BSET #4,61`; `BRA 1cdf0` |
| `1cdf0..1cdfe` | 14 | `e84e9b1000eefbaa` | 2 | 결정 10: C2 `1cdea`의 fall-through, `CMPI.B #2,1(A4)`, `ANDI.W #ffbf,D0`(→ C2 `1cdfe`) |
| `1ed22..1ed34` | 18 | `a03695e81d4abec4` | 5 | 기록 표 판정 `1ed22`: `1cb08`의 C, `49a58` 난수와 `D1` 비교 |
| `1ee00..1eee0` | 224 | `a0dc56da4ff71c44` | 34 | 상태 `1ee00`(C2 `1edf6`의 fall-through), 입력·기록 표 판정들, `201a2`로 |
| `1f126..1f1d8` | 178 | `0904697ddbce6da4` | 17 | 방향 전환 `1f126`, 설치 `1f166`, `1ed78` 쓰기 |
| `201a2..201bc` | 26 | `0a558452a5da98bc` | 4 | 공통 꼬리: `JSR (A4)` `201a6`(A4 = LONG `84(A6)`), `1a9e8`, `4d0a4` |
| `201d0..20240` | 112 | `ba0cacb199734a16` | 14 | `4de9c`, BYTE `a7` bit 6·7, `4b54e`, WORD `90` |
| `2024a..20268` | 30 | `108b76d20f05c263` | 4 | BYTE `a8` bit 6 깜빡임 |
| `20290..202ac` | 28 | `cf2f1928b8f005c4` | 2 | BYTE `61` bit 6/7, `5e` 지우기; 결정 10: `202a0`(`TST.W c(A4)`, → `202b6` / C5 `202ac`) |
| `202b6..20320` | 106 | `c1ac052a032e460b` | 12 | 기록 WORD `8(A4)` 세기, `49c38`, `1aa3a`, BRA.W 표 점프 `2031c` |
| `20516..20544` | 46 | `711d876b679b3a22` | 6 | BYTE `a4` 깜빡임(`1d15a` / `1d0c2`) |
| `20626..206cc` | 166 | `5ae50dfb17e19aed` | 16 | 높이 비교(`1a988`), 설치 쓰기 `20720` `20738`, `206a4`(LONG 표 `206d4`), BYTE `ab` `ac` |
| `206d2..206d4` | 2 | `1ceeabf0c6a5a30b` | 1 | `RTS` |
| `2156a..21622` | 184 | `7f2a8d88af07f7ce` | 15 | 이동 `2156a`(MOVEM.W, `49fca`), 목록 조회 `215e6`, 칸 상태 `21602`/`21610`, `JMP (A1)` `21620` |
| `21baa..21c12` | 104 | `03558027c2299333` | 11 | C를 돌려주는 판정 `21baa`(BYTE 표 `21ba6`) `21bc6` `21be6`(SUBX) |
| `21c1a..21c72` | 88 | `d1d8eb598c2c76c8` | 13 | `21c1c`, 목록 처리기 `21c22`, 칸 상태 `21c66` |
| `21c74..21ca4` | 48 | `0a7ddd81281806fb` | 8 | 입력 요약(`1cd98`) bit에 따른 분기, `2156a`로 |
| `21f30..21f4c` | 28 | `fbe700c919bccc2e` | 4 | `1cb40` / `1cabe` 뒤 `21f58`로 |
| `21f58..21f78` | 32 | `f946d44757eac919` | 2 | 칸 상태 `21f70`(목록 `21b26`) |
| `21ffc..22028` | 44 | `981cc292a37944c6` | 2 | 칸 상태 `21ffc`, `221ca`로 |
| `221ca..22238` | 110 | `1db377449f9fc58e` | 17 | 칸 상태 `221d2`(목록 `216c8`, `JMP (A1)` `221de`), 칸 값 쓰기 |
| `361e4..36292` | 174 | `36f4a831b5ca2408` | 16 | `28ae` 자식 `361e4`(C2 `1d1e2`), bank LONG `200098`, 설치 `36292`(FR6) |
| `48350..48368` | 24 | `4c7755f007ef4c08` | 3 | C1 `48346`의 Set 쪽 |
| `48384..4838c` `48392..48398` | 8 + 6 | `9a26697f815718a6` `bf91dcfae565e848` | 2 | C2 `1d1d0`이 부르는 C helper |
| `484ca..484d2` | 8 | `0e147622cc2e4d0e` | 1 | `D0 := BYTE 5682(A5)` |
| `4d0a4..4d0cc` `4d100..4d106` | 40 + 6 | `c5ad00945c32e238` `bf91dcfae565e848` | 6 | C helper: WORD `5cba/5ce6(A5)` 판정, `LSR.B` |
| `4de9c..4dee2` | 70 | `b15448eb12c43c48` | 9 | C helper: BYTE·WORD `5d12/5d18(A5)` 세기 |
| `e8b5a..e8b7e` | 36 | `0c170be8650930ec` | 2 | 기록 helper `e8b5a`(뒤 `e8b7e`/`e8b80`은 FR7) |
| 합계 C3 | 1974 | 이어 붙인 바이트 `0fc3d967…` | **230** | 짝수 PC 987(내부 757) |

- [F] **진입(실행된 PC를 줄인 closure 진입, `udetail.py C3`)**: `1ee00` `202b6` `2156a` `215e6` `21602` `21baa` `21bc6` `21be6` `21c1c` `21c22` `361e4` `48350` `48384` `e8b5a`. 실행된 시작 126개, 실행되지 않은 시작 100개.
- [F] **호출자**(ROM 전체 직접 분기 검색, `work/callers_c3.py`): `1ee00` ← C2 `1edf6` fall-through만(직접 분기 없음); `201a2` ← 상태 끝의 `BRA.W` 48곳(C2 `1f2a0` `1f80c` `1face`, C3 `1eedc` `1f1d4`, 나머지는 뒤 단위); `2156a` ← `BSR`/`BRA` 26곳(C3 `22216` `21ca0`; 부르는 쪽은 뒤에서 `TST.W D7`만 읽음); `215e6` ← `BSR` 28곳(모두 바로 뒤 `BCC`); `21baa` `21bc6` ← 각 4곳, `21be6` ← 2곳, `21c1c` ← 3곳(모두 바로 뒤 `BCS`); `1ed22` ← `1ee22` `1eea0` `1eebe`; `1cb40` ← 6곳; `48350` ← C1 `48346`; `48384` ← C2 `1d1d0`; `484ca` ← `1ee40`; `4d0a4` ← `201b2`; `4de9c` ← `201de`; `e8b5a` ← C2 `1d318`; `e8b6e` ← FR7 `e8cb8 JSR`; `1f126` ← `1ee04` `1efb4`(C11); `21602` ← `21682` `2246e`(뒤 단위). `361e4`는 C2 `1d1e2 MOVEA.L #361e4,A0; JSR 28ae`의 `28ae` 자식이다.
- [F] **설치 값**(MOVE.L `#v,(A6)`): 곧바로 들어감 `1f166`(`1f160`), `36292`(`3628c`, FR6 routed). **쓰기만**: `1ed78`(`1f1ce`, C2), `1fc38`(`201f2`), `20720`(`20648`), `20738`(`2066a`, C5).
- [F] **둘째 callback 칸 `84(A6)`**: `1f148` `21608` `21c5e` `21f68` `221ca` `221f6` `22208` `22220`이 LONG `84(A6)` := `21602` `21610` `21c66` `21f70` `221d2` `2210c` `21ffc` `22452`를 쓴다. `21602` `21610` `21c66` `21f70` `221d2`(쓰기 뒤 곧바로 그 값으로 들어감)와 `21ffc`는 C3 시작이고, `2210c`(C12 미룬 입구)와 `22452`는 뒤 단위다. IO run에서 node `100cb8`의 `84`는 frame 193~218 `21c66`, 347~392 `21f70`, 393~457 `21602`, demo 411~577 `21610`이다(`work/natsearch.py`).

### 계산 점프와 표(결정 2)

- [F] **`201a6 JSR (A4)`**(block `201a2`): A4 = LONG `84(A6)`. ROM 전체에서 LONG `84(A6)`에 즉시값을 쓰는 명령은 플레이어 코드 `1b000..24000`의 `MOVE.L #v,84(A6)` 34개 값뿐이다(`work/writers_c3.py 84`, 결과 `work/w84.txt`): `21602` `21610` `21664` `2173c` `21770` `217b2` `217e0` `217f6` `218b2` `2190e` `21960` `2199a` `219d8` `21a76` `21acc` `21c66` `21cd8` `21d2a` `21d92` `21e04` `21e6a` `21eb0` `21f02` `21f70` `21fc6` `21ffc` `2210c` `22128` `221d2` `22240` `2228e` `22360` `2241c` `22452`(C2 `1d22a` 초기화와 상태들의 `21602` 포함). 같은 구간의 다른 쓰기 `22ba6 MOVE.L 36(A6),84(A6)` `23aac CLR.L 84(A6)` `23b18 MOVE.L D0,84(A6)`는 다른 객체(callback `22b96` 등의 node)의 field다 [I]. 계획 §4.1의 "19개"는 closure가 닿은 값만 센 것이고, 이 목록은 ROM의 쓰기 명령 전체에서 셌다.
  - 허용 대상 = 이 34개 값. 그 밖의 LONG(0, 홀수, bit 24 이상이 선 값, 다른 routing된 PC 포함)은 `unsupported animation player c3 jump target`(checked, rollback, 복귀 LONG을 넣기 전). 허용 값 중 routing된 것(`21602` `21610` `21c66` `21f70` `21ffc` `221d2`)은 그대로 들어가고, 나머지 28개는 다음 dispatch가 `unsupported animation machine PC`(뒤 단위 정지)다.
- [F] **`2031c JMP 20320(PC,D0.W)`**(block `20318`): 표 `20320..20344`(파일 오프셋 = CPU 주소), BRA.W 9칸: `20320`→`2036c`, `20324`→`203a0`, `20328`→`203a0`, `2032c`→`2045c`, `20330`→`2049e`, `20334`→`20344`, `20338`→`20358`, `2033c`→`2036c`, `20340`→`203a0`. 색인은 BYTE `a0`(× 4, `2030a`의 `MOVEQ #0` + `MOVE.B` 뒤 `ADD.W` 두 번). [F] BYTE `a0`를 쓰는 ROM 명령은 `1bd40 MOVE.B #0,a0(A0)`과 `1c226 MOVE.B D0,a0(A0)`(D0 = BYTE 표 `1c238`의 값; 그 표의 첫 `3c` byte는 모두 0..8)뿐이다(`work/wa0.txt`). IO 관측에서 실행된 칸은 없다.
  - 결정(계획 결정 4, FR4 방식): **칸은 전사하지 않는다.** 실행부는 D0.W를 WORD 안에서 두 번 더한 변위가 `20` 이하일 때만 PC := `20320` + 변위로 옮기고(9칸 = 허용 대상, 모두 routing 밖이라 다음 dispatch의 `unsupported animation machine PC`가 선언 정지), 변위가 `20`을 넘으면 `unsupported animation player c3 jump target`이다. WORD 안의 계산이라 D0.W = `4000`+k는 원본처럼 k칸이 된다.
- [F] **`21620 JMP (A1)`**(block `21620`, `2161c BCC`의 Set 쪽): A1 = `215e6`이 목록 `21622`(`LEA 21622(PC),A0`)에서 key WORD = BYTE `9c`로 찾은 handler LONG. 목록 `21622..21662`([F] ROM 바이트): (`21c22`, 1) (`21d60`, 2) (`21e48`, 3) (`21e3a`, 4) (`21720`, 5) (`217e0`, 6) (`2178e`, 7) (`2175a`, 8) (`21950`, 9) (`219c8`, a), LONG 0.
  - 허용 대상 = 이 10개 handler. routing된 것은 `21c22`(C3)뿐이고 나머지 9개는 뒤 단위 정지다. 그 밖의 A1은 `unsupported animation player c3 jump target`.
- [F] **`221de JMP (A1)`**: 목록 `216c8`(`221d2 LEA 216c8(PC),A0`) = (`21602`, 0), LONG 0. 허용 대상 = `21602` 하나, 그 밖은 같은 checked 오류.
- [F] 같은 `215e6` 조회를 쓰는 다른 목록: `21aee`(`21c66`: (`21602`,0) (`21d60`,2) (`21e48`,3) (`21e3a`,4)), `21b26`(`21f70`: (`21602`,0) (`21e48`,3) (`21e3a`,4)), `21688`(C4·뒤). 그 `JMP (A1)`(`21c72` 등)은 뒤 단위다.
- [F] 읽는 고정 ROM 자료(live bus, 상한 검사 없음; 원본도 표 뒤의 바이트를 읽는다): LONG 표 `206d4 + 4 × BYTE a9`(`206a4`; [F] ROM 값 `0 48ec6 48ec6 48f3e 0 0`, BYTE `a9`의 ROM 쓰기는 0..5), BYTE 표 `21ba6 + sext(WORD 76)`(`21bb2`; `0b 0b 06 06`), 목록 `21622` `216c8` `21aee` `21b26`(`215ec`/`215f8`), A0로 넘기는 기록 WORD 표 `1b542` `1b55e` `1b57c` `1b598` `1b5b6` `1b5f2`(`1cb08`에 넘김) `1b798` `1b3c0` `1b83c`(`1cabe`) `1bc68`(`1cb40`) `1b188`(`1d0c2`), 그리고 bank LONG `200098`.

### 출구와 경계

- [F] **routing된 출구**(callee·분기 출구, 모두 다른 실행부의 block 시작): `8ebe` `ce02` `1a988` `1aa3a` `1c1f4` `36292` `482aa` `484e2` `49290` `49a58` `49c38` `49f8c` `49fc6` `49fca` `4ae4a` `4b54e` `4bfc0` `4c1de` `e8b7e` `e8b80`, 앞 단위 `1a9e8` `1cab6` `1cabe` `1cb08` `1cd98` `1cef8` `1d0c2` `1d15a` `1dfe6` `1ed34` `1ed78` `1eee0` `1f7a4` `1fa3c` `1fae8`(C2; 결정 10의 `1cdfa`·`1cdf0`이 닿는 `1cdfe` 포함) `48368` `49bca`(C1).
- [F] **뒤 단위 정지**(실행되지만 뒤 단위가 가짐, routing 밖; V1·실제 ROM 차분의 선언 정지 `EXIT_STOPS`):
  - C4: `21c72`(`21c6e` fall-through). C5: `1cb44`(`1cb40` fall-through) `20240`(`20238` fall-through) `20268`(`2022a BEQ`) `202ac`(`202a0` fall-through) `20544`(`2053c` fall-through) `21c12`(`21c06` fall-through) `21f4c`(`21c9c BCS`) `21f78`(`21f70 BSR`의 복귀 PC). C6: `206cc`(`206c6` fall-through) `21662`(`2161c BCC`) `4838c`(`48384` fall-through). C8: `1fa68`(`1f18e BNE`) `201bc`(`201b8` fall-through) `4d0cc`(`4d0b8 BNE`).
  - 미룬 입구(나머지 단위): `1fc96` `1fd50`(C11) `21ca4` `21d0e` `21fa6` `2210c`(C12) `223a0` `223d6`(C13).
  - 계산 점프의 routing 밖 허용 대상(위 "계산 점프"): JSR (A4) 28개, `21620` 9개, 표 칸 9개.
  - [I] 이 가운데 fall-through(직선 다음 PC)는 `1cb44` `20240` `202ac` `20544` `206cc` `21c12` `21c72` `4838c` `201bc`와 복귀 PC `21f78`이다. V1 `first_unrouted`는 직선 다음 routing 밖 PC를 다른 실행부 block의 내부로 보고 지나가므로 선언 정지가 필요하다(C1 결정 6과 같음). C3 run이 지나가는 C2 block의 정지(pc2 `EXIT_STOPS` 가운데 아직 routing 밖인 15개)도 pc3 `EXIT_STOPS`에 넣었다.
- [F] TRAP 없음. ROM·RAM 실행 없음. 특이 명령: `SUBX.W D0,D0`(`21bea`), `MOVEM.W` 2개(`2158e` 넣기, `215c8` 꺼내기).

### block 경계를 넘는 flag(결정 3·4)

scratch `cscan.py starts_C3.txt`와 호출자 검색으로 정했다. block 경계 너머의 Z를 읽는 block은 `1ee56` 하나다(다른 `BEQ`/`BNE`는 같은 block의 `BTST`/`BSET`/`BCLR`/`BCHG`/`TST`/`CMPI`/`AND`/`SUBQ` 뒤). N/V를 넘겨 읽는 block은 없다. X 소비는 `21be6`의 `SUBX`뿐이고 같은 block의 `ADDQ.B`가 X를 정한다.

- [F] **C 소비 block 22개**(Clear 쪽 / Set 쪽; Unknown C면 `player c3 caller requires known carry`):
  - `1cb08`(C2)의 C(`1cb18 RTS`로 돌아옴; `1cb08`은 Clear만, Set 쪽 `1cb1a`는 C5): `1ed26 BCC`(`1ed32` / `1ed2a`), `1ee32 BCS` `1ee86 BCS`(→ `1eee0`).
  - `1ed22`의 C: `1ee26` `1eea4` `1eec2 BCS`(→ `1eee0`).
  - `1ee04 BCS 1f126`: `1ee00 BSR 1ed34` 뒤. C2 `1ed34`는 들어온 C를 돌려주므로 `1ee00`에 들어온 C(C2 `1edf6`의 Clear)를 읽는다.
  - `1ee16 BCC`(`1dfe6`, C2 생산자), `1ee3c BCC`(`484e2`), `1ee7a BCS`(`4c1de`), `1f1ca BCC`(`49fc6`), `201b8 BCC`(`4d0a4`), `201e4 BCC`(`4de9c`), `202da BCS`(`49c38`), `2161c` `21c6e` `221da BCC`(`215e6`), `21c3a BCS`(`21bc6`), `21c42 BCS`(`21baa`), `21c48 BCS`(`21c1c`), `21c9c BCS`(`21be6`), `36282 BCC`(`482aa`).
- [F] **C 통과 block 4개**(들어온 C를 그대로 둠, `carry_preserving_pc`에 넣음): `1ee00`(`BSR`은 CCR을 바꾸지 않음), `1ed32 RTS`, `215f6 RTS`, `21c1a RTS`.
- [F] **C 생산 block**(자기 block에서 C를 정함): Clear `215ec`(`CMPA.W #0,A1`; `215f6` 쪽만 C가 살아남음) `21bc0` `21be0` `21bfa` `21c1c` `48392` `4d100` `4debc` `4ded4`(`ANDI.B #fe,CCR; RTS`), Set `215fc` `21bda` `48362` `4deca`(`ORI.B #1,CCR; RTS`), 자료 `1ed30`(`CMP.W D1,D0`: 무부호 D0.W < D1.W), `21bb2`(`CMP.B a1(A6),D0; RTS`: 무부호 D0.B < BYTE `a1`), `21c06`(`CMP.W D1,D0; BCC`: 같은 비교, Clear면 `21c1a`, Set이면 C5 `21c12`).
- [F] **앞 단위가 남긴 사항**(C2 계약): `1edf6`의 Clear → C3 `1ee00`(통과) → `1ed34` → `1ed3c RTS` → `1ee04`. C2 `1d1d6`은 `48384`의 C를 읽는다: `48392` Clear(이제 실제 사슬), Set 쪽 `4838c`는 C6. C1 `1d21c BCS`는 `48346`의 C를 읽는다: Set 쪽이 C3 `48350` → `48362`(이제 실제 사슬; `4835a`에서 BYTE `568e` ≠ 0이면 C1 `48368` Clear).

### IO 실행 run과 frame

- [F] 보정 관측(계획 당시 routing으로 셈, `work/c3io.py`): C3 PC를 실행하는 run 14개(P1 12, boot-title-start, boot-demo-0), 실행된 C3 PC 127개(시작 126), 실행 183,836회.
  - P1 94 95 100 101 106 107 110 111: 처음 실행 frame **192, 193, 195, 347**(각 13,283회). P1 68~71: **408, 409, 411, 563**(각 12,835회). boot-title-start: **312, 313, 315, 467**(13,283회). boot-demo-0: **381, 382, 386, 411**(12,949회, PC 114개).
  - [I] frame 192/408/312/381: C1 `48346` → C3 `48350`(Set) → C1 `1d21c BCS` → C2 `1d222` 초기화 → C3 `e8b5a`·`48384`(C2 `1d314` `1d1d0`) → C2 `1ed78` → … → `1edf6` → C3 `1ee00` → `201a2` → `JSR (A4)` = `21602`(C2 초기화 값) → `21610` → 목록 `21622` → … . frame 193~218(408~434, 313~338, 382~383)에는 node `100cb8`의 callback `1edb0`(C2)이 매 frame `1ee00`·`201a2`를 지나고 칸 `84` = `21c66`에서 `21c22` 계열을 실행한다.
- [F] **IO 예측(C1+E1+C2+C3 연결)**: 169,144 → **169,482**(+338 = A 8 run × 26 + B 4 run × 26 + title 26; demo 0). 예측 첫 정지(`work/firststops.py`): P1 94 계열 8 run frame **218**, P1 68 계열 4 run frame **434**, boot-title-start frame **338**(모두 C4 `371e` `3786` … = `4e94e` 본체·숫자 출력), boot-demo-0 frame **381**(C6 `1d398` `1d63a` … ). [I] 같은 frame 안의 실행 순서는 IO 비교가 확정한다(계획 §7 [U]).
- [F] D1 자연 seed 137개와 P0 run은 C3 코드를 실행하지 않는다.

## 공통 규칙·native 검증 계획

FR2..FR9, C1, C2 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_player_c3.cpp`, 함수 `animation_player_c3_block`. 오류 문자열은 `unsupported animation player c3 PC`(범위 안 내부 PC 직접 진입), `player c3 caller requires known carry`(C 소비 block에 Unknown C; 소비자 22개), `unsupported animation player c3 flag source`(결정 3의 Z 출처 guard), `unsupported animation player c3 jump target`(결정 2의 계산 점프 대상 guard) 네 개다. 그 밖의 오류는 공용 bus/스택/dispatcher 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(29 범위, C2 줄 뒤), `carry_preserving_pc`의 C2 묶음 뒤에 주석 달린 case 묶음 하나(소비자 22 + 통과 4), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 주석). 그 밖의 기존 시험·검증기 수정은 "영향받는" 절에 모았다.
- **설치 값.** `1f12a`(`MOVE.L #1f166,(A6)`)와 `3628c`(`MOVE.L #36292,(A6)`)는 쓰고 곧바로 그 값으로 들어간다. `1f1ce` `201f2` `20648` `2065e`는 LONG만 쓴다. 칸 `84`: `21602` `21c5a` `21f58` `221ca`는 쓰고 그 값으로 들어가고, `221f6` `22208` `22220`과 `1f12a`는 쓰기만 한다.
- **자료 읽기**(live bus): node field(A6), LONG `8c(A6)`(A4: WORD `8`), LONG `c(A6)`(부모: WORD `78`), A5 기준 BYTE `5683` `568e` `5684` `5682` `5c8d`, WORD `5cba`/`5ce6`(+ BYTE `22`), BYTE·WORD `5d12`/`5d18`(+ WORD `4`), LONG `5e26`(A4: WORD `0` `2`, BYTE `4`), BYTE `5e2e` `5e2f` 쓰기, 스택(`2158e`/`215c4`의 WORD 셋, `e8b6e`의 WORD 하나), 고정 ROM 표·목록과 bank LONG(위 "계산 점프와 표"). 단위 시험은 고정 ROM 자료 자리에 합성 physical byte만 둔다(원본 자료 아님, 모두 원본과 다름): 기록 WORD 표 `1b542` `1b55e` `1b57c` `1b598` `1b5b6` `1b5f2`(각 8 WORD), bank LONG `200098` = `0012fedc`, LONG 표 `206d4` = `10e900 0 10e940 0 110000 10e980`, 목록 `21622` = (`21d60`,1) (`21c22`,2) (`219c8`,`103`) 0, `216c8` = (`21602`,2) 0, `21aee` = (`21e48`,1) (`21602`,3) 0, `21b26` = (`21e3a`,1) 0, BYTE 표 `21ba4..21baa` = `77 33 05 0a 80 01`. V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾼다(`MOVE.W/.B`, `ADD.W`, `SUB.W`, `NEG.W`, `EXT.W`, `ANDI.W`, `AND.B`, `SUBQ.B`, `LSR.B`, `SUBX.W`). `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`SUB.L`은 LONG 전체. `MOVEM.W (A7)+,D0-D1`은 WORD를 부호 확장해 LONG 전체에 넣는다(`215c8`). `MOVEM.W D0-D1,-(A7)`은 D0을 낮은 주소에 둔다. 색인 `(d,PC,D0.W)`·`(A0,D7.W)`는 부호 확장 WORD. 비교: `CMP.W D1,D0` + `BCC`/borrow(무부호 WORD), `CMP.B a1(A6),D0`(무부호 BYTE), `CMP.B 9f(A6),D0` + `BEQ`(BYTE), `CMP.W (A0)+,D0`(WORD: BYTE `9c`와 key WORD `0103`은 같지 않음), `CMPI.B #k`(BYTE), `CMPA.W #0,An`(An 전체를 0과 비교), `SUB.L` + `BGT`(부호 LONG), `SUB.W` + `BLE`(부호 WORD), `TST.B 9d` + `BGT`/`BLT`(부호 BYTE, 한 block의 묶인 조건 분기), `TST.W 4(A4)` + `BPL`(WORD 부호), `SUBQ.W #1,8(A4)` + `BCC`(빌림 = 이전 WORD 0), `SUBQ.W #1,90(A6)` + `BNE`(결과 WORD). bit: `BTST/BSET/BCLR/BCHG #n,d(An)`(memory BYTE, n mod 8), `BTST #n,Dn`(LONG bit n), `BCHG #1,a7`·`BCHG #6,a8`(옛 bit로 분기). `21be6`: `ADDQ.B #1,a3`의 carry를 X로, `SUBX.W D0,D0` = 0 − 0 − X(D0.W = `ffff`/0, 상위 유지; 결과가 0이 아니면 Z를 지우고 0이면 그대로 두지만 다음 `OR.B`가 flag를 다시 정하므로 읽히지 않음), `OR.B D0,a3`(메모리를 다시 읽음, `ff`에서 포화).
- **스택.** `2158e`이 WORD 셋(D1, D0, 옛 WORD `1e`)을 넣고 `JSR 49fca`(복귀 `215c4`), `215c4`가 셋을 꺼낸다. `e8b6e`이 WORD D0을 넣는다(FR7 `e8ba0 TST.W (A7)+`가 꺼냄).

## carry와 Z(결정 3·4)

- [F] 소비자 22개·통과 4개·생산자는 위 명세와 같다. dispatcher는 `carry_preserving_pc`에 없는 PC로 갈 때 C를 Unknown으로 만든다. 따라서 이 단위의 C 의미는 (1) 소비자가 known C를 읽고 그대로 둔다, (2) 통과 block이 들어온 C를 그대로 둔다, (3) 생산자가 자기 block에서 C를 정한다, (4) 나머지 block 뒤 C는 Unknown이다.
- [F] **`1ee56 BNE.W 1eee0`의 Z**(결정 3): 유일한 선행은 `1ee4e LEA 1b5f2(PC),A0; BSR 1cb08`이다. `1cb08`은 `MOVEQ #0,D7; MOVE.B 9f(A6),D7; ADD.W D7,D7; MOVE.W (A0,D7.W),D7; BNE 1cb1a`이고 `1cb18 RTS`로 돌아올 때 Z = 1(옮긴 WORD = 0)이다. `1cb08`·`1cb18`은 A0와 BYTE `9f`를 바꾸지 않는다.
  - **player C5에서 넓힘**(C5 계약 결정 3): 이전 규칙은 위와 같이 WORD ≠ 0이면 checked flag-source 오류였다. C5가 `1cb1a`를 routing한 뒤에는 WORD W ≠ 0이면 C5 경로의 Z를 다시 계산한다: WORD W2 = (A0 + sext(W)), LONG L = (LONG `22(A6)` + sext((4 × W2) & ffff)); L = 0이면 `1cb30 RTS`(Z = 1) → `1ee5a`, 아니면 `1cb32 ORI.B #1,CCR; RTS`(Z = 0) → `1eee0`. 세 출처 주소 중 하나라도 24 bit로 `200000` 이상이면 checked flag-source 오류다. 실행부·시험·생성기·pc3 오류 fixture의 이전 / 새 기대값은 C5 계약 "영향받는" 절에 있다.

## 경계·routing 밖 출구

- [F] 이 단위의 간접 분기는 `201a6 JSR (A4)`, `2031c JMP (PC,D0.W)`, `21620 JMP (A1)`, `221de JMP (A1)` 네 곳이다(결정 2). `RTS`로 끝나는 block 21개.
- [F] **native 정지 규칙**(V1): C2 spec의 `first_unrouted`에 C3 뒤 단위·미룬 입구 23곳과 C2의 남은 정지 15곳(`EXIT_STOPS`)을 선언 정지로 더하고, 계산 점프 네 곳(`JUMP_PCS`) 직후 PC가 C3 시작이 아니면 그 PC에서 멈춘다(C++는 허용 목록 밖이면 checked 오류, 목록 안이면 다음 dispatch가 그 PC에서 정지/오류이므로 같은 stop에서 양쪽이 멈춘다). 실제 ROM 차분은 같은 정지를 `UNR`로 두고, 계산 점프 착지를 trace 전체에서 추적해 분류한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR9·C1·C2 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: 그 node(A6)에 선언 편집. ROM 쓰기 명령이 범위를 정한 값은 그 범위 안으로 둔다(결정 2): LONG `84(A6)` := C3 칸 상태 6개 또는 `2210c`, BYTE `a0` := 0..8, BYTE `a9` := 0..5, 직접 들어가는 `21620`/`221de`의 A1 := 목록 handler, `20318` 직접 진입의 D0.W := 0..8. LONG `5434(A5)` := 0(C2 결정 2의 ROM 값), LONG `5e26(A5)` := node.
- **IO pack 자연 node 상태(family `natural`)**: C2 spec과 같은 frame 14개(node `100cb8`의 callback `1edb0`; 결정 10의 `1cdf0`을 지나 같은 callback 안에서 C3 `1ee00`·`201a2`·칸 `21c66`을 거쳐 sentinel까지 간다, C3 block 82~91개), 레지스터만 선언(A5 := `108000`, A6 := `100cb8`, A7 := `10ef00`(복귀 LONG = sentinel), PC := `1edb0`).
- **재설치 world(family `reinstall`, 15개)**: `1f166`(P1 094 193, P1 068 409, boot-title-start 313, boot-demo-0 382 의 `100cb8`), `361e4`(같은 frame의 `28ae` 자식 node `101704`, 그 node는 `36292`를 들고 있음), `1edb0` + 칸 `84` := `21602` / `21610` / `21f70` / `221d2` / `21ffc`(P1 094 193), 칸이 자연 `21602`·`21f70`·`21610`인 frame(P1 094 393 / 347, boot-demo-0 411)의 `1edb0`. [I] 이미 진행된 node를 다시 시작하는 world이며 native와 C++가 같은 상태를 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`CHAINS` 22개 + Z 사슬 `1ee4e` → `1cb08` → `1cb18` → `1ee56`). V1에서 두 C가 다 나오는 것: `1ee36`(`484e2`), `1ee74`(`4c1de`), `1f1c4`(`49fc6`), `201da`(`4de9c`), `202d0`(`49c38`), `21610` `21c66` `221d2`(`215e6`), `21c34`(`21bc6`), `21c3e`(`21baa`), `36278`(`482aa`), `1ee12`(`1dfe6`). Clear만(뒤 단위 gate, `LATER_GATED`): `1edf6`→`1ee04`, `1ed22`→`1ed26`, `1ee1a`/`1ee98`/`1eeb6`→`1ee26`/`1eea4`/`1eec2`, `1ee2a`→`1ee32`, `1ee7e`→`1ee86`, `201ae`→`201b8`, `21c98`→`21c9c`, `1ee56`의 `1eee0` 쪽. `21c46`→`21c48`의 Set 쪽은 원본에서 불가능(`21c1c`는 늘 Clear, `STATIC_IMPOSSIBLE`).
- node fixture: `1f166` `361e4`를 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. callee fixture: `1cb40` `1ed22` `1f126` `201a2` `202b6` `206a4` `2156a` `215e6` `21602` `21610` `21baa` `21bc6` `21be6` `21c1c` `21c22` `21c66` `21f30` `21f40` `21f70` `21ffc` `221d2` `48350` `48384` `484ca` `4d0a4` `4de9c` `e8b5a`를 subroutine으로 들어간다.
- 단위 시험(Unicorn 생성기, C2 꼴): 시작 230개(소비자 22개 제외; `1ee56`은 native SR Z를 다시 계산한 Z와 같게 두는 행 `single 5`) × 들어오는 C 3가지, zero-step, 내부 PC 757개 정확한 오류, 경계 stop(출구·뒤 단위 정지·계산 점프 대상 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC. 손으로 계산한 규칙(`rules_a`..`rules_d`): 계산 점프 허용 목록 전부(34 + 10 + 1개 들어감, 목록 밖 값 거부, `20318` 변위의 WORD wrap·경계 `20`/`24`), `1ee56` Z 출처(0 / 0 아님 / `1ffffe` / `200000` 경계 / 24-bit), `1ed30`·`21bb2`·`21c06` borrow(동점 Clear, WORD/BYTE 폭, `21bb2` 음수 색인 `fffe` → `21ba4`), `21be6` ADDQ.B/SUBX/OR.B 포화, `2156a`~`215c4` EXT.W·NEG.W·MOVEM.W(넣는 순서, 꺼낼 때 부호 확장)·WORD 덧셈, `215e6` 조회(CMPA 32 bit, key WORD), `2062e` `20640` 부호 비교, `202b6` 빌림, `20238` 0/wrap, `206a4` 표(LONG `110000`의 하위 WORD 0, 색인 `40` → `207d4`), `1f12a`·`20226`·`20290`·`22004`·`361e4` ff node(쓴 field와 이웃 BYTE 유지), 칸 `84` LONG 쓰기, `4835a` BYTE 폭, `4d0a4`/`4de9c` 선택·`LSR.B` 논리 shift·세기, `e8b5a`/`e8b6e`.

## 영향받는 기존 시험·검증기(이전 기대값 → 새 기대값, 이유)

- [F] `tools/verify_animation_machine_stage_event.py` / `_stage_event_ops.py` `CPP_PINS`: `animation_machine.cpp` `003b4d86868d11dce31dd6732b5c79f9c1d76e523a75110628d7d11f87c389f5` → `0a8379cacc854d593b262cbb4989dc68a17dfacb3e58b06e0d3e833d87474b26`, `animation_machine_internal.h` `9bb14a08b8beafda059409ccf886f4ed1a83827b3144c6ff2234fb6fb5b92ec6` → `dee2f94720c4f7abd38131660b83a741fa36ada560a56357fafd8cb3f2a0e112`(이 단위의 공유 수정; 옛 값은 `# player C3 refresh:` 주석). 마지막 편집 뒤의 파일 SHA다.
- [F] `tools/unit_fixture_specs/pc1.py`: `EXIT_STOPS`의 `48350`이 C3 시작이 되어 `build()`의 "뒤 단위 정지는 routing 밖" 검사가 실패한다. 이전 `ROUTED_LATER = (0x1d222,)` → 새 `(0x1d222, 0x48350)`. `48350`은 C1 실행의 선언 정지로 그대로 둔다(C1 fixture 집합 불변). 이유: C2가 `1d222`에 쓴 방식과 같다.
- [F] `tools/unit_fixture_specs/pc2.py`:
  - `EXIT_STOPS`의 `1ee00` `201a2` `48384` `e8b5a` `1cde0` `1cdf0`(C3 시작; 뒤 둘은 결정 10)을 같은 방식으로 `ROUTED_LATER = (0x1ee00, 0x201a2, 0x48384, 0xe8b5a, 0x1cde0, 0x1cdf0)`로 허용한다(이전: 모두 routing 밖이어야 함).
  - 오류 fixture `error-1aa2c-jmp-201a2` `error-1aa2c-jmp-1ee00` `error-1a9e8-jmp-1ee00`(C2 `JMP (A1)` 대상이 routing 밖이면 `unsupported animation machine PC`)은 대상이 C3 시작이 되어 C++가 C3 코드를 실행하므로 더 이상 그 오류가 아니다. 대상을 C2 범위 사이의 ROM 자료 LONG `1ed70` / `1ed74`(코드가 아니어서 routing될 일이 없음)로 바꿔 `error-1aa2c-jmp-1ed70` `error-1aa2c-jmp-1ed74` `error-1a9e8-jmp-1ed70`이 되었다. 확인한 내용(C2 결정 2의 "routing 밖 대상은 다음 dispatch 오류")은 같다.
- [F] `tools/generate_animation_machine_player_c2_test_table.py` 오류 행 `jmp-1ee00` → `jmp-1ed70`(같은 이유). 생성기를 다시 돌려 생성 구역에서 그 한 행만 바뀐 것을 확인했다(`error-jmp-1ee00` → `error-jmp-1ed70`, 나머지 바이트 같음). `engine/tests/animation_machine_player_c2_test.cpp` 손 규칙 `s.a[1]=0x1ee00; reject(… "unsupported animation machine PC")` → `0x1ed70`(옛 값은 주석).
- [F] `tools/verify_animation_machine_input.py` 이웃 목록의 `48384`: `unsupported animation machine PC` 거부 → `SUPERSEDED_OUTSIDE`(`'area C C3 (player_c3)'`, `49bca`와 같은 API-only control). 기본 상태(natural-stage-frame-0000)에서 `ff000`까지 성공한다. 관측: scratch `work/ip_probe.py`(scratch clone root `roots/probe`): `48384 ok=True pc=0xff000`, 대조 `48386` → `unsupported animation player c3 PC`, `49bca` → ok.
- [F] `tools/verify_animation_machine_buffer_cue.py` "no executor" 탐침의 `e8b5a` `e8b5c`: 이전 둘 다 `unsupported animation machine PC`. 새 `SUPERSEDED_OUTSIDE`: `e8b5a` → `animation machine external read queue empty`(C3 시작에서 FR7 `e8b7e`/`e8b80`을 지나 선언 없는 입력 읽기까지 감; 분류 `superseded_by_player_C3_start_then_routed_continuation_unit_not_traced`, FR7의 `4abc0`와 같은 꼴), `e8b5c` → `unsupported animation player c3 PC`(분류 `superseded_by_player_C3_interior`). 관측: scratch `work/bc_probe.py`(검증기의 첫 결과 행 phase 0 상태, carry 2): `e8b5a`/`e8b5c` 위 값, 대조 `e8a46` → `unsupported animation machine PC`, `4abc0` → external read queue empty(기존 기대값과 같음).
- [F] 검색(`work/hexsearch.py`: `tools/*.py`, `tools/unit_fixture_specs/*.py`, `engine/tests/*.cpp`, `engine/src/*.cpp`의 16진 상수 중 C3 범위 안의 값): 위 곳 말고는 stop으로만 쓰는 값(C1 시험의 `48350` 행·출구 목록, C2 시험의 `1ee00` `201a2` `48384` `e8b5a` 행·출구 목록), 경계가 맞닿은 범위(`input_test` RANGES `4836e..48384`, `buffer_cue_test` `e8a48..e8b5a`, `n23_test` `484b4..484ca`), 주석, 다른 시험 자료 안의 우연한 값(`h4` `h8` `u12` `u15` `b1b` `n34` `fr2` `irq_f6a`의 레지스터·RAM 값, `game_records` 계열의 자료 끝 `4d0a4`)뿐이다. `make -j4 all test`가 통과했다(경고 0).
- [I] native 사슬이 이 단위의 PC(`1ee00` `201a2` `48350` `48384` `e8b5a` 등)를 첫 routing 밖 PC로 멈추던 V1 spec·검증기는 더 진행한다(정지는 routing에서 계산된다). pc1·pc2는 그 PC를 선언 정지로 두어 fixture 집합이 같다. 나머지는 메인 runner의 회귀·legacy 단계가 확인한다.

## 결정

1. **범위.** C3 = 계획 §4.2 그대로 226 block, 29 범위(C1+E1+C2 routing 상태에서 계획 key로 재측정해 같음)에 결정 10의 4 block을 더해 230 block, 31 범위. 계획 메인 결정 2·9(미룬 입구, `1ee00` 분할)를 따른다.
2. **계산 점프 네 곳(허용 대상은 ROM 자료 쓰기에서 정함; C2 결정 2의 선례).**
   - `201a6 JSR (A4)`: 허용 = ROM이 LONG `84(A6)`에 쓰는 즉시값 34개(위 목록). 목록 안이면 PC := A4(복귀 `201a8`을 넣음), routing 밖 값은 다음 dispatch의 `unsupported animation machine PC`(뒤 단위 정지). 목록 밖은 `unsupported animation player c3 jump target`.
   - `2031c JMP 20320(PC,D0.W)`: 실행된 칸이 없어 칸을 전사하지 않는다(계획 결정 4, FR4 방식). 변위(D0.W × 4, WORD 안) ≤ `20`이면 PC := `20320` + 변위(9칸, 모두 뒤 단위 정지), 넘으면 checked jump-target 오류. [F] BYTE `a0`의 ROM 쓰기는 0 또는 표 `1c238`의 0..8 값이다.
   - `21620 JMP (A1)`: 허용 = 목록 `21622`의 handler 10개. `221de JMP (A1)`: 허용 = 목록 `216c8`의 `21602`. 그 밖은 checked jump-target 오류.
   - [I] 68000은 주소 bit 24..31을 버리지만 C++는 32 bit로 비교하므로 상위 byte가 0이 아닌 값은 원본과 달리 checked 오류다(ROM 자료로는 생기지 않음). 실행 전체가 rollback된다.
3. **RTS를 넘는 Z(`1ee56`, C1 결정 3의 규약).** `1ee56`은 Z를 메모리에서 다시 계산한다: WORD (A0 + sext(2 × BYTE `9f(A6)`))(`1cb08`이 읽은 것과 같은 주소; A0와 BYTE `9f`는 `1cb08`/`1cb18`이 바꾸지 않음). 그 WORD가 0이면 Z = 1이고 `1ee5a`로 간다(routing된 유일한 복귀 경로 `1cb18`과 같음). 다음은 checked `unsupported animation player c3 flag source`(rollback): (a) 24-bit 주소가 `200000` 이상(고정 ROM `<100000`과 work RAM `100000..1fffff` 밖; bank·장치를 다시 읽으면 원본에 없는 두 번째 읽기), (b) WORD ≠ 0(그 Z는 C5 `1cb1a` 경로가 만든 것이고 C3는 그 경로를 모름). [I] C5가 `1cb1a`를 routing하면 `1cb30 RTS`(Z = 1, C Clear)와 `1cb32 ORI.B #1,CCR; RTS`(Z = 0, C Set)가 생기므로 C5가 (b)를 넓혀야 한다(그 두 경로에서는 Z = (C = Clear)이다).
   - (player C5, 2026-10-22) (b)를 넓혔다: W ≠ 0이면 오류 대신 C5 `1cb1a`의 `TST.L` 출처를 다시 읽어 Z를 정한다(위 "carry와 Z"의 넓힘 항목, C5 계약 결정 3). 출처가 `200000` 이상일 때만 checked 오류다.
4. **carry 보존 목록.** 소비자 22개와 통과 4개(`1ee00` `1ed32` `215f6` `21c1a`)만 넣는다. 생산자는 자기 block에서 C를 정하므로 넣지 않는다(FR 관례). `215ec`은 `CMPA.W #0,A1`의 Clear를 정하고 `215f6`(통과)이 그것을 돌려준다. `1ee56`은 C를 읽지 않으므로 넣지 않는다.
5. **표 읽기.** 고정 ROM 표·목록은 live bus로 읽고 상한을 검사하지 않는다(원본과 같음; 목록 조회는 원본대로 LONG 0까지 반복). 단위 시험은 합성 byte만 선언하므로 그 밖 색인은 `missing or ambiguous physical program bus ROM byte`로 확인하고, 원본 값은 V1·실제 ROM 차분이 비교한다.
6. **뒤 단위 정지.** C3 block이 직선·분기·호출·복귀로 닿는 뒤 단위 시작 15곳과 미룬 입구 8곳, 그리고 C3 run이 지나가는 C2 block의 남은 정지 15곳을 V1 `first_unrouted`와 실제 ROM 차분의 선언 정지로 둔다.
7. **앞 단위 spec의 선언 정지.** pc1·pc2의 `EXIT_STOPS` 가운데 C3가 routing한 PC는 `ROUTED_LATER`로 허용하고 선언 정지로 그대로 둔다(C2가 pc1에 쓴 방식). C2의 "routing 밖 JMP 대상" 오류 시험은 ROM 자료 LONG `1ed70`/`1ed74`로 옮긴다.
8. **실행부 파일·오류 문자열.** 위 "공통 규칙". 오류 문자열 4개.
9. **다음.** 계획 순서대로 C4(`4e94e` 본체·숫자 출력 `3650`, `JMP (A1)` `21c72`). C2+C3 연결로 IO +338(169,482)을 메인 runner가 확인한다.
10. **TB에 가려진 직선 연속 4 block을 C3에 넣는다(계획 226 → 230, 시작 목록 SHA `6452d0d0…` → `3cbca2ea…`).** [F] 보정 관측(`ms5-scratch/c1/reobs`)은 TB마다 "관측 당시 routing(`7233eefc`) 밖인 첫 명령"만 기록한다. C2 `1cdea BCLR.B #4,61(A6)`(6 byte) 다음의 `1cdf0`은 같은 TB의 직선 연속이라, TB 시작 `1cdea`가 기록될 때 가려진다(`1cde0`도 `1cdd8`의 fall-through로 같다). C3 `20290` 다음의 `202a0`도 같다. 그래서 계획은 `1cde0` `1cdf0`을 demo frame 431의 C7로, `202a0`을 C5로 나눴다(`work/c7check.py`: `1cdea`는 14 run frame 192/408/312, `1cdf0`은 demo 431 하나). [F] native 추적(`work/straightline.py`, V1 natural fixture와 같은 IO pack frame-start 상태)은 frame 193·194·200·218(P1 94), 409·410·434(P1 68), 193·205(P1 106), 313·314·338(title), 382·383(demo) 모두에서 callback `1edb0` → `1cd98` → `1cdea` → **`1cdf0`**을 실행한다. 계획 226 block만 연결하면 IO 비교는 이 PC에서 멈춘다(예측 +338 대신 +0) [I]. `straightline2.py`로 "정지 PC의 직선 block을 routing된 것으로 치고 다시 추적"을 되풀이하면 `1cdf0..1cdf6`, `202a0..202a8` 두 번 뒤 모든 world가 sentinel까지 간다. 그래서 `1cde0`(`BSET #4,61; BRA`), `1cdf0`(`CMPI.B #2,1(A4); BCS 1cdfe`), `1cdfa`(`ANDI.W #ffbf,D0`, C2 `1cdfe`로), `202a0`(`MOVEA.L 8c(A6),A4; TST.W c(A4); BNE 202b6`; `202ac`는 C5)를 C3에 넣었다. flag는 block 안에서만 쓴다. [I] C5·C7의 시작 목록은 이 4개를 빼고 다시 재야 한다(메인 판단). [U] 다른 node·frame에도 같은 가림이 있을 수 있다. IO 비교가 확정한다.

## 미확인

- [U] node field·전역 값의 의미(`84` 칸 상태, `9c` 목록 key, `9d` `a0` `a1` `a3` `a4` `a9` `aa` `ab` `ac`, `5683` `568e` `5684` `5682` `5c8d`, `5cba/5ce6`, `5d12/5d18`, `5e26`, 목록 `21622` `21aee` `21b26` `216c8`의 handler). 이름은 동작에서 붙인 [I]이다.
- [U] IO 관측에서 실행되지 않은 이 단위의 block 100개(`1f126..1f1d4` 대부분, `201e8`~, `2051e`~, `20648`~, `21baa`~ 일부, `21f30..21f70`, `21ffc..22236` 대부분, `3622c` 계열, `4dea8`~ 등)는 closure로 들어왔다(V1 선언 상태·실제 ROM 차분으로만 확인).
- [U] `22ba6` `23aac` `23b18`이 쓰는 LONG `84`가 플레이어 node의 칸이 아니라는 것(결정 2의 허용 목록 근거)은 callback 계열에서 본 추론이다 [I]. 플레이어 node에 그 값이 들어가면 checked 오류가 알린다.
- [U] 결정 3(b)의 범위는 C5 연결 때 다시 정한다. → C5 계약 결정 3에서 정했다(W ≠ 0이면 C5 경로의 Z를 다시 계산).
- [U] 같은 frame 안의 실행 순서(IO 첫 정지 PC). 예측은 C4 `371e`/`3786` 계열(13 run)과 C6 `1d398` 계열(demo)이다.
- [U] 재설치 world와 IO pack 자연 node 상태의 레지스터(선언)는 실제 dispatcher 진입 레지스터와 다를 수 있다(C1·C2와 같음).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_player_c3.cpp`(case label 230 = `starts_C3_final.txt`와 집합 일치; 공용 함수 `pc3_get` `pc3_put` `pc3_bit`(BTST/BSET/BCLR/BCHG memory BYTE, 옛 bit) `pc3_byte_is` `pc3_carry` `pc3_return_carry` `pc3_install` `pc3_slot84` `pc3_mask` `pc3_shape` `pc3_index_call` `pc3_add_word` `pc3_listed`, 허용 목록 `PC3_SLOT84`(34) `PC3_LIST_21622`(10)), `engine/tests/animation_machine_player_c3_test.cpp`(생성 구역 + 수작성 규칙 `rules_a`..`rules_d`), `tools/generate_animation_machine_player_c3_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; 약 90초; 다시 실행해 시험 파일 바이트 단위 같음), `tools/unit_fixture_specs/pc3.py`(V1 spec; C2 spec의 공용 부분 그대로, 단위 부분 교체, `EXIT_STOPS`, `PASS_SET`, `CLEAR_SET` `SET_SET` `DATA_SET`, `Z_READERS`, `LATER_GATED`, `STATIC_IMPOSSIBLE`, `JUMP_PCS`, `SLOT84` `LIST_21622`, 묶인 조건 분기 `BUNDLED = (21c30,)`, family `reinstall`(추가 쓰기 포함)). 공유 수정은 "공통 규칙"·"영향받는" 절의 곳뿐이다.
- [F] `make -j4 all test`(작업자, 최종): 종료 0, 경고 0, Python 310 OK. C3 시험 줄: `animation machine player pc3: 1282 fixtures (730 single-block, 39 Z reader, 289 path, 93 producer chain, 44 declared C, 87 checked error (23 with a later failing PC), 244 kept C), 230 blocks, 5415 calls, 114879 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block은 `1ee56`의 `1eee0` 쪽뿐(뒤 단위 gate), 실제 사슬 두 C 값 10개(`1ee12` `1ee36` `201da` `202d0` `21610` `21c34` `21c3e` `21c66` `221d2` `36278`), Clear만 10개와 Z 사슬.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, C3 시험): 빌드 경고 0, 실행 종료 0, runtime error 0.
- [F] V1 pc3(작업자 1회, `--workers 2`, scratch `work/v1_pc3`): fixture 1,831개(block 827, chain 35, node 5, natural 14, reinstall 15, callee 89, error 822, failpc 14, negative 10) failed 0, 방문 시작 230/230, 빠진 후속 0, 도달 못한 분기 결과 0, 뒤 단위 gate 10개, carry oracle Unknown/Clear/Set = 743/173/83. natural·reinstall 29개 가운데 24개가 sentinel까지(C3 block 82~108개) 간다.
- [F] V1 회귀(작업자): pc1 1,264/1,264, pc2 1,743/1,743, se1 2,102/2,102, fr1 1,631/1,631(모두 failed 0; pc1·pc2 fixture 수는 C2 기록과 같음). 나머지 spec은 결정적 runner가 돌린다.
- [F] 변이(scratch `mut/run_mut.py`; `mut/mutants.py`는 `mut/make_mutants.py`가 실행부 줄마다 연산자(분기 교환, 비교 반전·경계, field +1, 크기, bit 번호·BSET/BCLR/BCHG, WORD→LONG, 복귀 PC, carry tag·소비자 분기 교환, mask, 설치·칸 값) + 손으로 고른 helper·block 변이(허용 목록·`20318` 경계·`1ee56` 출처·MOVEM 순서·부호 확장·SUBX 등) + dispatcher carry 목록 26개·범위 1개를 적용해 만든 것, 735개): 1회째(226 block, 725개) `killed 691 of 725`, 빈틈 14개를 규칙과 합성 LONG `110000`으로 메움. 결정 10 뒤 2회째 `killed 713 of 735`, 빈틈 2개(`20238-mask` `48350-field`)를 규칙으로 메움(`killed 2 of 2`). 최종 715/735, 나머지 20개는 동치(`mut/equivalents.txt`: `MOVEQ #0` 바로 뒤의 `MOVE.B` 10, 값이 ff 이하라 mask가 무의미 5, `206a4` 첫 두 배가 WORD 안 1, BYTE 쓰기 helper가 자름 2, bit 번호 상수 1, WORD `90`의 0 판정 1). 64 KiB RAM 거울이 부호 확장 변이를 가리는 곳은 고정 ROM 합성 자료의 음수 색인(`21bb2` WORD 76 = `fffe` → `21ba4`)과 `1ee56`의 `1ffffe`/`200000` 경계 규칙으로 덮었다.
- [F] 실제 ROM 차분(scratch `realrom/`: `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`), `real_pc3.py`(C2 harness에 C3 world·소비자·통과·Z 진입·선언 정지; C3 계산 점프 네 곳의 착지를 허용 목록과 trace 전체에서 대조해 분류; `49fca`는 점프로 들어올 때만 정지)): 작업자 300건 — seed 1 `mismatches 0`(`covered starts 219 of 230`; 문서화된 분류 C3 jump-target 2건), seed 7 `FOLLOW_ANIM=1` `mismatches 0`(228/230; jump-target 4건, `1ee56` flag-source 1건), seed 8 `FOLLOW_ANIM=1` `mismatches 0`(219/230; jump-target 1건). 정지하지 않은 native(약 5~13%)는 건너뜀. 로그 `trial_logs/real_n300_*.log`.
- [F] `dleft.py`(`MS5_REOBS`): 이전(routing `003b4d86…`) C 659 / E 12, 예측 169,144, 첫 정지 C 14(`dleft_before.log`). 이후(routing `0a8379ca…`) C **529** / E 12, 예측 **169,482**, 첫 정지 C 14(`dleft_after.log`). 예측 첫 정지 PC(`work/firststops_after.txt`): P1 94 계열 8 run frame 218·P1 68 계열 4 run frame 434·boot-title-start frame 338에서 C4 `371e` `3722` `372a` … (`4e94e` 본체·숫자 출력), boot-demo-0 frame 381에서 C6 `1d398` `1d3a0` … `1d63a`.
- [F] 기존 검증기 새 기대값은 scratch clone root(`roots/probe`, `work/mkroot.py`: 작업 트리 clone + 변경 파일 복사 + 공유 자료 symlink, 출력 폴더만 실제)에서 관측했다(`ip_probe.py` `bc_probe.py`). 같은 root에서 stage_event / stage_event_ops `CPP_PINS`가 파일 SHA와 같음을 확인했다(4 / 9 pin, 불일치 0).

## block 목록

[F] scratch `starts_C3_final.txt`(SHA256 `3cbca2ea534fb5f0a98ee4620a5123f5e36545d2b1b7f46cb0b8ccd6d5126a92`) = 계획 `starts_C3.txt`(226) + 결정 10의 `1cde0` `1cdf0` `1cdfa` `202a0`.

- **`1cb40` `1cde0..1cdfe`(4)**: `1cb40 1cde0 1cdf0 1cdfa`
- **`1ed22..1eee0`(39)**: `1ed22 1ed26 1ed2a 1ed30 1ed32 1ee00 1ee04 1ee08 1ee12 1ee16 1ee1a 1ee26 1ee2a 1ee32 1ee36 1ee3c 1ee40 1ee46 1ee4e 1ee56 1ee5a 1ee64 1ee72 1ee74 1ee7a 1ee7e 1ee86 1ee8a 1ee90 1ee98 1eea4 1eea8 1eeae 1eeb6 1eec2 1eec6 1eecc 1eed6 1eedc`
- **`1f126..1f1d8`(17)**: `1f126 1f12a 1f166 1f16a 1f174 1f17c 1f186 1f18e 1f198 1f19c 1f1a4 1f1b4 1f1ba 1f1c4 1f1ca 1f1ce 1f1d4`
- **`201a2..20320`(36)**: `201a2 201a8 201ae 201b8 201d0 201da 201e4 201e8 201f2 201f8 201fc 20206 20210 20216 2021c 20226 2022a 20238 2024a 20254 2025e 20264 20290 202a0 202b6 202c2 202d0 202da 202de 202e6 202ec 202f4 202fc 20300 2030a 20318`
- **`20516..206d4`(23)**: `20516 2051e 2052c 20530 20534 2053c 20626 2062e 2063a 20640 20648 20654 2065e 20670 20674 20682 20686 2068e 2069c 206a4 206c0 206c6 206d2`
- **`2156a..21622`(15)**: `2156a 21580 21582 2158c 2158e 215c4 215e6 215ec 215f6 215f8 215fc 21602 21610 2161c 21620`
- **`21baa..21ca4`(32)**: `21baa 21bb2 21bc0 21bc6 21bd0 21bda 21be0 21be6 21bfa 21c00 21c06 21c1a 21c1c 21c22 21c34 21c3a 21c3e 21c42 21c46 21c48 21c4c 21c5a 21c66 21c6e 21c74 21c78 21c80 21c88 21c90 21c98 21c9c 21ca0`
- **`21f30..22238`(25)**: `21f30 21f3c 21f40 21f48 21f58 21f70 21ffc 22004 221ca 221d2 221da 221de 221e0 221e4 221ec 221f6 221fe 22208 22210 22216 2221a 22220 22228 22230 22236`
- **`361e4..36292`(16)**: `361e4 3620a 36218 36228 3622c 3623a 3624a 36256 3625c 36264 3626a 36272 36278 36282 36286 3628c`
- **`48350..484d2`(6)**: `48350 4835a 48362 48384 48392 484ca`
- **`4d0a4..4dee2`(15)**: `4d0a4 4d0ac 4d0b4 4d0b8 4d0be 4d100 4de9c 4dea8 4deac 4deb4 4deba 4debc 4dec2 4deca 4ded4`
- **`e8b5a..e8b7e`(2)**: `e8b5a e8b6e`
