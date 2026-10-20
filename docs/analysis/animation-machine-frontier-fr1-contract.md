# 첫 frontier 단위 FR1(IO frontier 순위 1–14) 구현 계약 — FR1a 구현, FR1b·FR1c 명세

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. 범위는 IO 비교(`animation-machine-io-execution.md` §5.3, `frontier.json`)의 후보 단위 순위 1–14, 즉 확정 frontier PC 14개 전부다. 다시 잰 closure가 약 230 block을 넘으므로 자연 경계에서 나눈다(결정 1): 이 작업자는 **FR1a**(214 block)를 구현하고, 나머지 **FR1b**(199)·**FR1c**(148)는 끝 절에 정확히 명세한다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 코드와 고정 표는 모두 `<100000`이라 CPU 주소와 파일 오프셋이 같다. bank 창 읽기 `2001c0` `2001d0`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `5c30b72`(branch `claude/frontier-units`, PR #6 head). routing 기준 `engine/src/animation_machine.cpp` SHA256 `8ce8eb93c21465dd5e9355d4518ab1ca853df4549305fec98c7854caa1a82db6`(= `frontier.json`의 `routing_file_sha256`).
- [F] frontier 입력: IO 검증기 출력 `/Users/start/Workspce/ms5-scratch/io2fix/vA/frontier.json`(확정 실행 68, 미확정 0, frontier PC 14개).
- [F] 정적 디코드: capstone M68000. block 시작 규칙은 B4·B4b 계약과 같다(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, 변위 없는 `MOVE.L #imm,(A6)` 설치 값, 전사한 PC 상대 점프 표의 항목). routing된 PC, `RTS`, `TRAP`(경계, 단위에 넣지 않음), `JMP (An)`(live 대상)에서 멈춘다. `28ae`/`2986` 자식 값(`JSR` 앞 `MOVEA.L #imm,A0`)은 기록만 하고 따라가지 않는다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr1/`
  - `hroute.py` `closure2.py` `b3adis.py` `refs.py` `xref.py` `probe_scan.py`(B4b scratch 복사, 경로만 바꿈), `fclos.py`(위 규칙의 closure; 점프 표 전사 `TABLES`), `unit_fr1.py`(단위 정의·분류, `FR1PART=b`/`c`로 FR1b·FR1c), `tbl_b3dbc.py`(`b3484`/`b3894` 표 전사), `data_a.py`(자료 표).
  - `starts_a.txt`(FR1a 시작 214개) SHA256 `b3fa4194da6fd2afdaf760e74decc00f98430d9b674444c0c1db47e279225b9a`; `starts_b.txt`(199) `f396240016f4a67f8c433e8d4d39e4970692f5bb8be6bef1150bbdaa9857f000`; `starts_c.txt`(148) `8b4ce0695c74311baf724817e25bd955f1773a190bfc206aa1decd56a904dcc0`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 크기 재산정과 분할

[F] frontier PC 14개에서 위 규칙으로 closure를 다시 쟀다(scratch `fclos.py`, routing된 PC 제외). IO 표(§5.3)의 값은 "포인터를 따라가지 않는 직접 closure, root = PC 이하 `0x1000` 안 가장 가까운 call 대상"이라 설치 사슬·점프 표가 빠졌고, root 둘은 frontier PC와 다른 코드다.

| IO 순위 | frontier PC(IO root) | 실행 수 | IO leader | 다시 잰 block | 명령 | 범위 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `de660`(root 6개) | 14 | 54 | 56 | 136 | `ca42..ca48` `4e146..4e166` `de660..de8bc` |
| 2 | `e5324`(root `e4ffc`) | 12 | 3 | 82 | 210 | `4e0de..4e0f6` `e5292..e5580` `e56c0..e5724` |
| 3 | `b3dbc` | 12 | 1 | 39 | 97 | `b3dbc..b3dfc` `b3ea2..b3eac` `b3ec4..b3f40` `b3f4c..b3f8c` `b3fa4..b402a` |
| 4 | `b30f6`(root 32개) | 3 | 46 | 86 | 180 | `b30ba..b336a` `b3460..b3484` `e9112..e9148` |
| 5 | `4b6f4` | 3 | 3 | 3 | 4 | `4b6f4..4b702` |
| 6 | `d131a`(root `d0fec`) | 3 | 7 | 3 | 9 | `d131a..d1348` |
| 7 | `eb9ba` | 3 | 14 | 14 | 31 | `eb9ba..eba3e` |
| 8 | `51602` | 3 | 6 | 6 | 13 | `515e0..515fc` `51602..51608` |
| 9 | `b7742` | 3 | 1 | 1 | 1 | `b7742..b7748` |
| 10 | `5a376` | 3 | 16 | 40 | 73 | `5a376..5a460` `5a54e..5a5ba` |
| 11 | `b975e` | 3 | 9 | 10 | 19 | `b975e..b97c0` |
| 12 | `bc08c` | 3 | 4 | 148 | 348 | `bc08c..bc404` `bc47c..bc7d6` |
| 13 | `de376` | 2 | 17 | 18 | 40 | `ddfdc..de00c` `de376..de3e6` |
| 14 | `de024` | 1 | 29 | 67 | 190 | `ddfdc..de00c` `de024..de260` `de2b6..de31e` `de3ae..de3e6` |
| 합 | 14 | 68 | | **562**(`de376`·`de024` 겹침 18 제외) | 1,325 | |

- [F] **`e4ffc` → `e5324`.** `e4ffc..e5086`은 ASCII 문자열 자료다(`\p\cA OVER…`, `CONTINUE`, `CAPTURED PRISONER`, `SCORE` 등; capstone이 가짜 명령으로 디코드). 확정 frontier PC는 `e5324`(node callback LONG(A6) = `e5324`, 호출자 복귀 `2ac2`)이고 IO의 root `e4ffc`는 `0x1000` 규칙의 부산물이다. `e5324`는 U02의 `28ae` 자식 값이다(`e51f0` `e5202 MOVEA.L #e5324,A0`).
- [F] **`d0fec` → `d131a`.** 확정 frontier PC는 `d131a`(복귀 `4a43e`, 즉 `4a43c JSR (A1)`의 live 호출)다. `d0fec..d1028`은 다른 계산 helper(호출자 `39e0a` `7710e` `ae058`)이고 `d131a`의 closure에 없다. FR1에 넣지 않는다.
- [F] **`b3dbc` 1 → 39 block과 B2 표의 "31 block" 대조.** IO 표의 1 block은 `b3dc8 JMP b3dcc(PC,D0.W)`에서 멈춘 값이다. 이 계약은 점프 표 두 개(`b3dcc` 4 항목, `b3fce` 2 항목)를 전사해 39 block이다(표 `b3dcc`만 전사하면 26, 둘 다 빼면 1). B2 계약(`deferred-b2-contract.md` 94·235행)의 31은 B2 기준 routing에서 낸 추정이며 이 규칙으로는 재현되지 않는다 [I](당시 표 처리·routing 차이). 사실로 쓰는 값은 39다. 또 IO 관측으로 `b3dbc`는 node callback으로 실제 실행되는 PC임이 확인됐다(B1 결정 5의 [U] "실행 PC인지"는 `b3dbc`에 한해 [F]: P1 case 0 1 127..135, frame 99, LONG(A6) = `b3dbc`, 복귀 `2ac2`).
- [F] `b3dbc`의 두 `JMP (A0)`(`b3f3e` `b3fc4`)는 표 `b3484`(10 byte 기록 104개)의 LONG `6`이 대상이다. 표가 가리키는 처리기는 서로 다른 101곳(`bfb5a..c1b98`, `d8f78..d8f9e`, 모두 routing 밖)이라 전부 넣으면 단위가 수천 block이 된다. 그래서 `JMP (An)`는 live 대상 routing으로 두고(F4 관례) 처리기는 다음 frontier로 남긴다(결정 4).
- [F] **분할(결정 1).** 합 562 > 약 230이다. frontier 실행 수가 가장 많은 root(14·12·12)를 FR1a에 두고, 실행 수 3인 root 9개 중 작은 객체 6개(`4b6f4` `d131a` `eb9ba` `51602` `b7742` `b975e`, 합 37)를 함께 넣는다. 실행 수 3인 큰 객체 셋과 E 영역 title/demo 둘은 나눈다.
  - **FR1a** = `de660` + `e5324` + `b3dbc` + `4b6f4` `d131a` `eb9ba` `51602` `b7742` `b975e` = **214 block**, 18 범위. frontier 실행 68개 중 56개(14 + 12 + 12 + 3 × 6)의 첫 정지 PC를 연결한다.
  - **FR1b** = `b30f6` + `5a376` + `de376` + `de024` = **199 block**, 9 범위(끝 절). 실행 9개.
  - **FR1c** = `bc08c` = **148 block**, 2 범위(끝 절). 실행 3개.
  - [I] FR1b·FR1c는 FR1a와 범위·callee를 공유하지 않는다(겹침 0, 서로의 block 시작을 부르지 않음). 순서는 FR1a → FR1b → FR1c를 권고한다.

## 요약(FR1a)

- [F] **범위·block 수**(18 범위, 합 214):

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `ca42..ca48` | 6 | `8f0c49538e19307cb4467697c7bc4b1872803ec29acf130db4981098c3f4c483` | 1 | 3 |
| `4b6f4..4b702` | 14 | `e4c8ad6f5265776398cd30ddedfba947a49756e74a03160be849c1d70f4facaf` | 3 | 7 |
| `4e0de..4e0f6` | 24 | `568c1f81697a8d049fa6c4842b344618c84018c571c25da55448563839bee84e` | 1 | 12 |
| `4e146..4e166` | 32 | `8b73df383b45213867ff6b9d174a9490741067913820d4744ea8304f8f7e409e` | 5 | 16 |
| `515e0..515fc` | 28 | `4aab7ee099018ed8eba7d4e654aa2d2bdd95456d2284f0e02a87315e2486b313` | 5 | 14 |
| `51602..51608` | 6 | `72595c559b0cea7143b33f2950bf2cea2560e4bcd208f5ddbed22fd0d2e29ec2` | 1 | 3 |
| `b3dbc..b3dfc` | 64 | `2be0e79bcda44b2f160988ba00b03f61180edf61fb4dd02988d9d301f4667608` | 9 | 32 |
| `b3ea2..b3eac` | 10 | `bec17b064124805c35d7a28e0087fc3d9c486e3207a861714f6f19f8da0e341b` | 1 | 5 |
| `b3ec4..b3f40` | 124 | `c37c72c9565dff62d0dc55b065e16a716a6bf85cbceb769fc42a70033760a6b4` | 11 | 62 |
| `b3f4c..b3f8c` | 64 | `1c8a3d7b451a4e51128ba9d50c4ecb6feac5a6d4c1d8f85d1b29b583396c7ac7` | 4 | 32 |
| `b3fa4..b402a` | 134 | `8e6d8180953de64ab59812bcef1da24cb8dca7d94ee1535efcc64eb17f76da9b` | 14 | 67 |
| `b7742..b7748` | 6 | `2738adf81304c5fbbc9eedf6248d6b2d7cfa132bc35dfb5e458d0bbd9e12d3f9` | 1 | 3 |
| `b975e..b97c0` | 98 | `34a01667a0cd95d0638e3c78a4849e575b98142f52af6a0bfb76cff05563dfec` | 10 | 49 |
| `d131a..d1348` | 46 | `529906a9a890bb3823243029e31a1be741c98c20a22747c3bbf93af49414bb9e` | 3 | 23 |
| `de660..de8bc` | 604 | `219a7ebc7219cce411f551ca1a9a9735e1eb07308ca912a099233bed81c18ff0` | 50 | 302 |
| `e5292..e5580` | 750 | `e259ff3925bd17d1404c38b01742520bead83707b4c79c42333a9579dffc1b35` | 76 | 375 |
| `e56c0..e5724` | 100 | `ea0cc655a083dc1d693d1db1a66443182f941245e459a68060a117cccfd3ff7b` | 5 | 50 |
| `eb9ba..eba3e` | 132 | `e3674e1969b8ae55ce78947457cdab8ea8f664749a5d9160eb6f13f7b38f6211` | 14 | 66 |
| 합계 FR1a | 2242 | 이어 붙인 바이트 `3eaab87a6c06630b30b85933139e6cff5e8b699bfb68e31eb973c85863113db9` | **214** | 1121(내부 907) |

- [F] 명령 520개, closure가 18 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 연속 Bcc 묶음 없음, X 소비(ADDX/SUBX/ROX)·I/O port·bank 변경 없음. DIVU 4곳(`e56c0` helper, 결정 6). `TRAP #15` 1곳(`b3eac`, 경계, 범위 밖). 계산 점프 4곳(`b3dc8` `b3fca` 표 점프, `b3f3e` `b3fc4` `JMP (A0)`, 결정 3·4).
- [F] **현재 routing과의 관계**: 18 범위의 짝수 PC는 모두 routing 밖이다(겹침 0). 경계 이웃: `ca40`(routing 밖 `RTS`)·`ca48`(F1b block), `4b6f2`(F1b `RTS`)·`4b702`(routing된 다른 helper), `4e0dc`(routing 밖 `RTS`)·`4e0f6`(routing 밖 형제 함수), `4e144`(routing 밖 `RTS`)·`4e166`(readiness block), `515de`(routing 밖 `RTS`)·`515fc`(routing 밖 형제 진입 `LEA 5160e(PC),A0; BRA 515e0`), `51600`(그 형제의 `BRA.B`)·`51608`(형제 진입 `LEA 51626(PC),A0`), `b3dba`(자료)·`b3dfc`(routing 밖 형제 함수 `b3dfc`), `b3eac`(`TRAP #15`, 뒤는 문자열 `ITEM KIND ERROR`)·`b3ec2`(문자열 뒤의 도달하지 않는 `MOVE.W #0,76(A6)` 중간), `b3f40`(정적 참조 없는 형제 진입 `MOVE.W D0,8a(A6); JSR b3f4c; JMP b3f68`)·`b3f4a`(그 `JMP` 중간), `b3f8c`(LONG 표 `b3f8c..b3fa4`), `b3fa2`(표 끝)·`b402a`(routing 밖 형제 `MOVE.L A0,76(A6); RTS`), `b7740`(U18 `RTS`)·`b7748`(routing 밖 `RTS`), `b975c`(U05 `RTS`)·`b97c0`(routing 밖 형제 함수), `d1318`(routing 밖 `RTS`)·`d1348`(형제 `d1348 MOVEA.L #d13b4,A0 …`), `de65e`(자료)·`de8bc`(routing 밖 다른 함수 `JSR 43e34; JSR 49fc6; RTS`), `e5290`(U02 `JMP`)·`e5580`(`28ae` 자식 값, routing 밖), `e56be`(routing된 `RTS`)·`e5724`(routing된 block), `eb9b8`(U06 `RTS`)·`eba3e`(U06 block).
- [F] **나가는 곳은 모두 routing돼 있다**: callee `28ae` `2986` `3670`(`JMP`/`JSR`) `36ba` `3a70`(`JMP`) `3af8` `3c44` `8c16` `8cda` `8ebe` `8ff4` `ca48` `ca56` `ca8a` `caf0` `1a5a4` `1ab02` `43e34` `49214` `49a58` `49a84` `49f8c` `49fc6` `eba3e`(`JSR (PC)`), 출구 `JMP 2a00`(삭제) 3곳(`b3ed8` `b7742` `e5572`), `JMP 2a24` 2곳(`de8ac` `b97b8`), `JMP 491b6`(`d1342`), `JMP 3670` 2곳(`e5400` `e54c0`), `JMP 3a70` 4곳(`e52a2` `e52ca` `e52ea` `e5318`). routing 밖으로 나가는 실행 PC는 `TRAP` `b3eac`와 계산 점프의 live 대상뿐이다(결정 3·4).
- [F] **참조**(ROM 전체 직접 분기·LONG 상수 검색, scratch `refs.py` `xref.py`): 범위 밖에서 들어오는 실제 분기는 모두 block 시작이다 — `ca42`(`4e848` `4e8b2 JSR`), `4b6f4`(`5ef66` `5f5e0` `5f73e`(B2a, routing됨) 외 `51ce4`~`ef974` `JSR` 17곳), `515e0`(형제 `51600`(이 범위 밖, routing 밖) `5160c BRA.B`), `51602`(`50d9c`(U14) `5145a BSR.W`), `b3ea2`(형제 `b3e18` `b3e70 BRA.W`), `b3f4c`(`b3e9c` `b3f44 JSR`), `b3f68`(`b3f48 JMP`), `eb9ba`(`eb84a` `eb85e`, U06), `eb9e4`(`eb878` `eb892`, U06). LONG 값: `de660` = `c8d2 MOVEA.L #de660,A0`(C2 `28ae` 자식), `e5324` = `e51f0` `e5202`(U02 `28ae` 자식), `b3dbc` = `2986` 자식 값 20곳 이상(`60812` `608b6`(B2a) `37cd4` `543cc` `73f0a` …), `b7742` = `b6fea` `b70f6` `b773a` `b7804` `b789c` `b78b0 MOVE.L #b7742,(A6)`, `b975e` = `b9736`(U05 설치), `d131a`는 호출 표 LONG(정적 위치 [U], 실행 근거는 `4a43c JSR (A1)`).
- [F] 범위 안 내부 PC로 보이는 분기(`e0a3e..e0b0a`의 `e52b9` `e52cb` `e5403` … 11곳)는 모두 이름 문자열 자료(`Hyades Hygieia …`)의 가짜 디코드다. 내부 PC 착지 0으로 본다.
- [I] 의미: `de660`은 캐릭터 선택 뒤 새 게임 준비 객체(C2 `c8ce`가 만듦; `8c16` 화면 색, `1a5a4` 배치, `28ae` 자식 `de97e` `de8ca`×2 `deba4`×4, 대기 뒤 자식 `deb1a`×4 `de9e8`×2, `ca42`/`36ba` 표시, `4e146`(BYTE `9c` = 1인 플레이어 수)이 0이면 진행, 소리 `3af8`·`3c44`, 끝에 부모 BYTE `62` := `ff`), `e5324`는 결과(점수·포로) 표시 객체(`3a70`/`3670` 문자열·숫자 그리기, `e56c0` = 16 bit 값의 10진 BCD 변환), `b3dbc`는 아이템 객체(종류 WORD `76` < `6e`, 기록 `b3894`·`b3484`의 처리기로 `JMP (A0)`), `4b6f4`는 BYTE `5b86(A5)` ≠ 0을 C로 돌려주는 판정, `d131a`는 list `100bf4`에 `2986` 자식 `d13b4`를 넣는 처리기, `eb9ba`/`eb9e4`는 U06 메뉴의 선택 index 순환(`eb9ba`: WORD `7e` ∈ [0, WORD `7a`), `eb9e4`: WORD `7c` ∈ [0, WORD `78`)와 표 `eba9e` 기록·소리), `51602`는 (D0, D1) WORD 쌍 목록을 D2와 함께 `8cda`(HUD)에 넘기는 반복, `b7742`는 설치되는 "자기 삭제" callback, `b975e`는 U05 객체의 끝 상태(애니메이션 시작, `49fc6`, `1ab02` 화면 판정). 이름은 확정하지 않는다.

## 공통 규칙·native 검증 계획

B1 계약 "공통 규칙"과 "공통 native 검증 계획", B2 계약 "자식(`28ae`) 진입 fixture", B2c~B4b 계약의 공유 파일·macOS seed 관례를 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr1.cpp`, 함수 `animation_objects_fr1_block`. 오류 문자열은 `unsupported animation objects fr1 PC`(범위 안 내부 PC 직접 진입), `objects fr1 caller requires known carry`(C 소비 block에 Unknown C; 소비자 3개가 있으므로 둔다), `objects fr1 DIVU zero divisor`(`DIVU.W D2,D0`에서 D2.W = 0; 원본은 vector 5 예외, 모델링하지 않음 — N13 관례, 결정 6)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(18 범위, B4b 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(결정 5의 4개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, test 목록 실행 줄, 시험 target; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** routing 밖 실행 PC는 `TRAP` `b3eac`(BCS 실패 쪽, `unsupported animation machine PC`)와 계산 점프의 live 대상이다. 기존 시험이 stop으로만 보던 PC(`4b6f4`(B2a), `51602`(U14), `eb9ba` `eb9e4`(U06), `b975e`(U05), `de660`(C2 레지스터 값))는 stop 판정이 routing보다 먼저라 그대로 통과한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다(F4 관례).
- **오류 fixture의 실패 PC**(리뷰 0264 L-1). 기대 오류 fixture마다 실패 PC를 적는다. 실패 PC가 진입 PC와 다르면 같은 상태를 stop = 실패 PC로 실행해 정확히 그 PC에서 멈추는지(성공) 함께 확인한다(홀수 실패 PC는 계산 점프 대상뿐이며 식으로 확인).
- **자료 읽기**(live bus, F1 결정 3): 모든 표 읽기는 원본 주소 계산 그대로 live bus로 읽는다. 상한 검사는 원본에 없으므로 두지 않는다. 대상: LONG `2001c0` `2001d0`(bank 창)과 LONG `c(LONG 22(A6))`(`b3fd6`)·`48(LONG 22(A6))`(`b975e`), BYTE `(b3894 + sext(WORD(12·D0.W)))`·WORD `2(…)`(`b3f50` `b3f68` `b3fb2`), BYTE/WORD/LONG `(b3484 + sext(WORD(10·k)))` + `0`/`2`/`4`/`6`, LONG `(b3f8c + sext(D0.W))`(`b3f68`), WORD 목록 `(A0)+`(`515e2` `515ec`, `51602`는 `51620`), LONG/WORD `(eba9e + sext(WORD(8·WORD 7c)))` + `0`/`4`/`6`(`eba08`). RAM 읽기: BYTE `5b86(A5)`(`4b6f4`), WORD `(5d22(A5) + D0.W)`·`(5d26(A5) + D0.W)`(`4e0de`), BYTE `9c(1009a8)`·`9c(100a6c)`(`4e146`), BYTE `(10fdb6 + sext(D0.W))`(`e5324`), BYTE `-8000(A5)`(`e52f6`), WORD `(A7)`(`515ec`). 단위 시험은 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `515e0 MOVE.W D2,-(A7)`(WORD), `515e8 ADDQ.W #2,A7`(A7 += 2, flag 없음) 뒤 `RTS`, `515ec MOVE.W (A7),D2`(pop 아님)·`MOVE.L A0,-(A7)`, `515f8 MOVEA.L (A7)+,A0`. `BSR`/`JSR (PC)` 복귀: `4e14e`(→ `4e152`), `b3f02`(→ `b3f22`), `b3f22`(→ `b3f26`), `b3f4c`(→ `b3f50`), `b3faa`(→ `b3fb2`), `e5350`(→ `e5358`), `e536e` `e542e` `e54f8`, `e53e8`/`e54a8`(→ `e53ec`/`e54ac`), `eba08`(→ `eba28`). 모두 `am_push`/`am_pop`(홀수 A7은 checked 오류).
- **정수 연산.** `MOVEQ`(LONG, 부호 확장: `#e1` → `ffffffe1`), `MOVE.B`/`MOVE.W` → Dn(상위 유지), `MOVEA.L`, `LEA d16(An)`·`LEA abs`·`LEA d16(PC)`(절대 주소), `ADDA.W D0,An`(An += sext(D0.W), 32 bit), `MULU.W #c`/`#a`(무부호 16 × 16 → D0 32 bit 전체), `DIVU.W D2,D0`(결정 6), `SWAP`, `ANDI.W`/`ANDI.L #ffff`/`ANDI.B #3`(해당 폭), `EOR.B D2,15(A6)`, `OR.W`, `LSL.W #3/#4/#8`(WORD만), `ADD.W Dn,Dn`(WORD wrap), `SUBQ.W #1` 메모리, `ADDQ.W #1` 메모리, `ADDQ.B #1,62(A0)`, `ADDQ.W #1,D0`, `CLR.W`/`CLR.B` 메모리. 비교·분기: `SUBQ.W #1,d(A6)` + `BEQ`(결과 WORD = 0), `CMPI.B #4`/`#1`/`#3` + `BEQ`/`BNE`, `CMPI.W #19cf` + `BGE`(부호 WORD ≥), `CMPI.W #6e` + `BCS`(무부호 <), `CMPI.W #3e7` + `BLS`(무부호 ≤), `CMP.W 7a(A6),D1`/`CMP.W 78(A6),D1` + `BLT`(부호 D1.W < WORD), `MOVE.W` + `BPL`/`BNE`/`BEQ`(N/Z of WORD), `TST.B`/`TST.W` + `BEQ`/`BNE`, `ANDI.W #7` + `BNE`, `ANDI.L #ffff` + `BEQ`, `BTST` + `BNE`. 모두 같은 block 안에서 만들고 소비한다(예외: 결정 5의 C). 68000 폭 그대로 명시 구현한다.
- **macOS seed.** 자연 seed가 필요한 V1·D1 실행은 B3a~B4b와 같은 scratch wrapper가 `D.SEED_DIR`만 역사 관측 `artifacts/stage_entry_body`(SHA256 `1f65100f…`)로 바꾼다(도구 파일은 고치지 않음).

## carry

- [F] **소비 block 3개**(callee가 돌려준 C를 읽음; 각 block은 `BCC.W` 하나):
  - `b401e BCC.W b4028` / `b9798 BCC.W b97a8`: `49fc6`(interpreter known C). Clear → 분기 대상, Set → `b4022`(설치 `b3fa4`) / `b979c`(WORD `76` := 1, 설치 `b970e`).
  - `b97b4 BCC.W b97be`: `1ab02`(화면 판정: 밖이면 `1aafc` Set, 안이면 `1ab7a ANDI.B #fe,CCR` Clear). Clear → `b97be RTS`, Set → `b97b8 JMP 2a24`.
- [F] **known C 생산**(결정 5): `4b6f4`의 `TST.B 5b86(A5)`는 C를 지운다 — BYTE = 0이면 `BEQ 4b700`(C Clear), 아니면 `4b6fc`(`ORI.B #1,CCR`, C Set) → `4b700 RTS`. 호출자 20곳이 모두 복귀 직후 `BCC`/`BCS`로 이 C를 읽는다(`5ef6c` `5f5e6` `5f744`는 B2a가 routing한 소비자, 나머지 17곳 `51cea`~`ef97a`는 routing 밖). 그래서 실행부는 `4b6f4` block 끝에서 C Clear(두 갈래 모두), `4b6fc` 끝에서 C Set을 남기고, `4b700`(`RTS`)은 들어온 C를 그대로 보존한다(통과 block, 결정 5).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 소비자 3개(`b401e` `b9798` `b97b4`)와 통과 `RTS` `4b700`, 합 4개다. Unknown C로 소비자에 들어오면 checked 오류다. `4b700`은 C를 읽지 않으므로 Unknown도 그대로 통과한다(오류 아님). 그 밖의 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다(`4b6f4` `4b6fc` 제외).
- [F] C를 읽지 않는 호출: `2986`(`d132a` → `d1330 MOVE.W`), `28ae`(`de69a`…`de802` → `MOVE.W #k,7a(A0)` / `MOVE.L` 설치, `e554c` → `e5552 MOVE.W`), `49a58`(`b3f26` → `ANDI.W`), `1a5a4`(→ `MOVEA.L`), `4e146`(→ `TST.B D0`), `4e0de`(→ `MOVE.W`), `e56c0`(→ `MOVE.W D0,76(A6)`), `8cda`(`515f2` → `MOVEA.L (A7)+`), `8ebe` `8ff4` `3af8` `3c44` `8c16` `ca48` `ca56` `ca8a` `caf0` `ca42` `36ba` `43e34` `49214` `49f8c` `49a84` `3670` `eba3e`(다음 명령은 모두 MOVE/LEA/JSR/RTS/TST). 범위 밖 호출자의 반환 C 사용(`ca42` `4e146` `4e0de` `51602` `eb9ba` `eb9e4` `d131a`)도 확인했다: `4e84e TST.W`, `4e8b8 CMPI.B`, `de81a MOVE.W`, `de832 TST.B`, `e53da`/`e549a MOVE.W`, `50da0`/`5145e MOVEQ`, `eb84e`/`eb862`/`eb87c`/`eb896 BRA`, `4a43e MOVE.W`. 소비자 없는 carry 보존은 만들지 않는다.
- [F] block 경계를 건너 다시 계산하는 flag는 없다.

## 객체 `de660` `de660..de8bc`(50) + helper `ca42..ca48`(1) `4e146..4e166`(5)

- **`de660`**(node callback): D0 D1 D2 := `ffffffe1`(MOVEQ #e1), D3 := `f`, `JSR 8c16`(복귀 `de66e`). **`de66e`**: `JSR ca48`(복귀 `de674`). **`de674`**: `JSR ca8a`(복귀 `de67a`).
- **`de67a`**: WORD `76` := 4, 설치 `de686`(fall-through).
- **`de686`**(설치 값)·**`de754`**·**`de84c`**: WORD `76` −= 1(SUBQ.W), 결과 0 → `de690`/`de75e`/`de856`, 아니면 `de68e`/`de75c`/`de854 RTS`.
- **`de690`**: A0 := `de526`(자료, `1a5a4` 인자), `JSR 1a5a4`(복귀 `de69a`).
- **`de69a`**: A0 := `de97e`, D0.W := `1e`, `JSR 28ae`(복귀 `de6aa`). **`de6aa`**: A0 := `de8ca`, D0.W := `1e`, `JSR 28ae`(복귀 `de6ba`).
- **`de6ba`** `de6d0` `de6e6` `de6fc` `de712`: WORD `7a(A0)` := 0 / 1 / 0 / 1 / 2(A0는 `28ae`가 준 자식 또는 더미 `100e98`), 다음 자식 A0 := `de8ca` / `deba4` / `deba4` / `deba4` / `deba4`, D0.W := `1e`, `JSR 28ae`(복귀 다음 block).
- **`de728`**: WORD `7a(A0)` := 3, D0.W := `19da`, `JSR 3af8`(복귀 `de738`). **`de738`**: D0.W := `73c`, `JSR 3af8`(복귀 `de742`).
- **`de742`**: BYTE `62` := 0, WORD `76` := 4, 설치 `de754`.
- **`de75e`**: `JSR caf0`(복귀 `de764`). **`de764`**: D0 D1 D2 := 0, D3 := 8, `JSR 8c16`(복귀 `de772`). **`de772`**: 설치 `de778`.
- **`de778`**(설치 값): BYTE `62` = 4 → `de784`, 아니면 `de782 RTS`.
- **`de784`**: `JSR ca56`(복귀 `de78a`). **`de78a`**: A0 := `deb1a`, D0.W := `1e`, `JSR 28ae`(복귀 `de79a`).
- **`de79a`** `de7b0` `de7c6` `de7dc` `de7f2`: WORD `7a(A0)` := 0 / 1 / 2 / 3 / 0, 다음 A0 := `deb1a` / `deb1a` / `deb1a` / `de9e8` / `de9e8`, D0.W := `1e`, `JSR 28ae`.
- **`de808`**: WORD `7a(A0)` := 1, 설치 `de814`.
- **`de814`**(설치 값): `JSR ca42`(복귀 `de81a`). **`de81a`**: D0.W := `727b`, D1.W := 3, D3 := 0, D4 := 2, `JSR 36ba`(복귀 `de82c`). **`de82c`**: `JSR 4e146`(복귀 `de832`).
- **`de832`**: D0.B = 0 → `de83a`, 아니면 `de838 RTS`.
- **`de83a`**: `JSR ca48`(복귀 `de840`). **`de840`**: WORD `76` := `4b`, 설치 `de84c`.
- **`de856`**: D0 D1 D2 := `ffffffe1`, D3 := `f`, `JSR 8c16`(복귀 `de864`). **`de864`**: WORD `76` := `14`, D0.W := `73c`, `JSR 3c44`(복귀 `de874`). **`de874`**: WORD `82` := `19c0`, 설치 `de880`.
- **`de880`**(설치 값): 부호 WORD `82` ≥ `19cf` → `de898`, 아니면 `de88a`: WORD `82` += 1, D0.W := WORD `82`, `JSR 3af8`(복귀 `de898`).
- **`de898`**: WORD `76` −= 1, 0 → `de8a2`, 아니면 `de8a0 RTS`.
- **`de8a2`**: D0.W := `19c0`, `JSR 3af8`(복귀 `de8ac`). **`de8ac`**: A0 := LONG `c`, BYTE `62(A0)` := `ff`, `JMP 2a24`.
- **`ca42`**: A0 := A5 − `76a2`(LEA), `RTS`.
- **`4e146`**: D0 := 0(MOVEQ), A0 := `1009a8`, `BSR.W 4e158`(복귀 `4e152`). **`4e152`**: A0 := `100a6c`(fall-through `4e158`).
- **`4e158`**: BYTE `9c(A0)` = 1 → `4e162`, 아니면 `4e164`. **`4e162`**: D0.W += 1(fall-through). **`4e164`**: `RTS`.

## 객체 `e5324` `e5292..e5580`(76) + helper `4e0de..4e0f6`(1) `e56c0..e5724`(5)

- **`e5292`**: D0.W := `706d`, WORD `7c` = 0 → `e52a2`, 아니면 `e529e`: D0.W := `72ad`. **`e52a2`**: A0 := `e503c`, A1 := `e84c8`, `JMP 3a70`.
- **`e52b2`**: D0.W := `706a`, A0 := `e5014`, WORD `7c` = 0 → `e52ca`, 아니면 `e52c2`: D0.W := `72aa`, A0 := `e5028`. **`e52ca`**: A1 := `e84c8`, `JMP 3a70`.
- **`e52d6`**: D0.W := `7074`, A0 := `e507a`, WORD `7c` = 0 → `e52ea`, 아니면 `e52e6`: D0.W := `72b4`. **`e52ea`**: A1 := `e84c8`, `JMP 3a70`.
- **`e52f6`**: A0 := `e504c`, BYTE `-8000(A5)` = 3 → `e5308`, 아니면 `e5304`: A0 := `e505e`. **`e5308`**: D0.W := `7070`, WORD `7c` = 0 → `e5318`, 아니면 `e5314`: D0.W := `72b0`. **`e5318`**: A1 := `e84c8`, `JMP 3a70`.
- **`e5324`**(node callback): A0 := `10fdb6`, D0.W := WORD `7c` & 1, BYTE `(A0 + sext(D0.W))` ≠ 1 → `e5572`, 아니면 `e533c`.
- **`e533c`**: A0 := LONG `c`, D0.W := WORD `82(A0)`, WORD `7c` = 0 → `e5350`, 아니면 `e534c`: D0.W := WORD `84(A0)`.
- **`e5350`**: WORD `80` := D0.W, `BSR.W e52b2`(복귀 `e5358`). **`e5358`**: WORD `7a` := `f`, 설치 `e5364`.
- **`e5364`** `e537e` `e5424` `e543e` `e54e4` `e5538`(설치 값): WORD `7a` −= 1, 0 → `e536e`/`e5388`/`e542e`/`e5448`/`e54ee`/`e5542`, 아니면 `e536c`/`e5386`/`e542c`/`e5446`/`e54ec`/`e5540 RTS`.
- **`e536e`**: `BSR.W e5292`(복귀 `e5372`). **`e5372`**: WORD `7a` := 8, 설치 `e537e`.
- **`e5388`** `e5448`: D0.W := `1ac4`, `JSR 3af8`(복귀 `e5392`/`e5452`). **`e5392`** `e5452`: WORD `7a` := `1e`, 설치 `e539e`/`e545e`.
- **`e539e`** `e545e`(설치 값): WORD `7a` −= 1, 0 → `e53ca`/`e548a`, 아니면 `e53a6`/`e5466`: D0.W := WORD `7a` & 7, ≠ 0 → `e53bc`/`e547c`, 아니면 `e53b2`/`e5472`: D0.W := `1ac4`, `JSR 3af8`(복귀 `e53bc`/`e547c`).
- **`e53bc`** `e547c`: D0.W := `3e8`, `JSR 49a84`(복귀 `e53c6`/`e5486`). **`e53c6`** `e5486`: `BRA.W e53e8`/`e54a8`.
- **`e53ca`** `e548a`: LONG `(A6)` := `e5418`/`e54d8`(설치만), D0.W := WORD `7c`, `JSR 4e0de`(복귀 `e53da`/`e549a`).
- **`e53da`** `e549a`: D0.W := D1.W / D2.W, 무부호 D0.W ≤ `3e7` → `e53e8`/`e54a8`, 아니면 `e53e4`/`e54a4`: D0.W := `3e7`.
- **`e53e8`** `e54a8`: `BSR.W e56c0`(복귀 `e53ec`/`e54ac`).
- **`e53ec`** `e54ac`: WORD `76` := D0.W, D0.W := `71ed`/`71f0`, WORD `7c` = 0 → `e5400`/`e54c0`, 아니면 `e53fc`/`e54bc`: D0.W := `742d`/`7430`.
- **`e5400`** `e54c0`: A0 := A6 + `76`, A1 := `e84c8`, D3 := 0, D4 := 3, D1.W := `461`, `JMP 3670`.
- **`e5418`**(설치 값): WORD `7a` := `f`, 설치 `e5424`. **`e542e`**: `BSR.W e52f6`(복귀 `e5432`). **`e5432`**: WORD `7a` := 8, 설치 `e543e`.
- **`e54d8`**(설치 값): WORD `7a` := `f`, 설치 `e54e4`. **`e54ee`**: D0.W := `1acf`, `JSR 3af8`(복귀 `e54f8`). **`e54f8`**: `BSR.W e52d6`(복귀 `e54fc`).
- **`e54fc`**: A0 := `10de14`, D0.W := `7154`, WORD `7c` = 0 → `e5518`, 아니면 `e550e`: A0 := `10de1c`, D0.W := `7394`. **`e5518`**: A1 := `e84c8`, D3 := 0, D4 := 8, D1.W := `461`, `JSR 3670`(복귀 `e552c`).
- **`e552c`**: WORD `7a` := `1e`, 설치 `e5538`.
- **`e5542`**: A0 := `e5580`, D0.W := 0, `JSR 28ae`(복귀 `e5552`). **`e5552`**: WORD `7c(A0)` := WORD `7c`, WORD `80(A0)` := WORD `80`, BYTE `62` := 0, 설치 `e5568`.
- **`e5568`**(설치 값): BYTE `62` ≠ 0 → `e5572`, 아니면 `e5570 RTS`.
- **`e5572`**: A0 := LONG `c`, BYTE `62(A0)` += 1, `JMP 2a00`.
- **`4e0de`**: D0.W &= 1, D0.W += D0.W, A0 := A5 + `5d22`, D1.W := WORD `(A0 + sext(D0.W))`, A0 := A5 + `5d26`, D2.W := WORD `(A0 + sext(D0.W))`, `RTS`.
- **`e56c0`**: D3 := 0, D2.W := `a`, D0 &= `ffff`, 0 → `e5720`, 아니면 `e56d0`.
- **`e56d0`**: `DIVU.W D2,D0`, `SWAP`, D0.W &= `f`, D3.W := D0.W, `SWAP`, D0 &= `ffff`, 0 → `e5720`, 아니면 `e56e6`.
- **`e56e6`**: `DIVU.W D2,D0`, `SWAP`, D0.W &= `f`, D0.W <<= 4, D3.W |= D0.W, `SWAP`, D0 &= `ffff`, 0 → `e5720`, 아니면 `e56fe`.
- **`e56fe`**: `DIVU.W D2,D0`, `SWAP`, D0.W &= `f`, D0.W <<= 8, D3.W |= D0.W, `SWAP`, D0 &= `ffff`, `DIVU.W D2,D0`, `SWAP`, D0.W &= `f`, D0.W <<= 8, D0.W <<= 4, D3.W |= D0.W(fall-through).
- **`e5720`**: D0.W := D3.W, `RTS`.

## 아이템 객체 `b3dbc` `b3dbc..b3dfc`(9) `b3ea2..b3eac`(1) `b3ec4..b3f40`(11) `b3f4c..b3f8c`(4) `b3fa4..b402a`(14)

- **`b3dbc`**(node callback, `2986` 자식 값): D0.W := WORD `7e`, WORD `7e` := 0, D0.W := 4·D0.W(ADD.W 두 번, WORD wrap), `JMP b3dcc(PC,D0.W)`: PC := `b3dcc` + sext(D0.W)(결정 3).
- **`b3dcc`** `b3dd0` `b3dd4` `b3dd8`(표 항목 0..3): `BRA.W b3ddc`/`b3de4`/`b3dec`/`b3df4`.
- **`b3ddc`** `b3de4` `b3dec` `b3df4`: A0 := `b41be`/`b4036`/`b42a2`/`b403e`(LEA (PC); 뒤에 LONG `76` `7a`로 저장될 동작 포인터, 이 단위는 실행하지 않음), `BRA.W b3ea2`.
- **`b3ea2`**: 무부호 WORD `76` < `6e` → `b3ec4`, 아니면 `b3eac`(`TRAP #15` 경계, routing 밖).
- **`b3ec4`**: WORD `68` := `8838`, WORD `1e` := `8838`, D0.W := WORD `76`, ≠ 0 → `b3ede`, 아니면 `b3ed8 JMP 2a00`.
- **`b3ede`**: D1.W := WORD `78`, ≠ 0 → `b3eea`, 아니면 `b3ee6`: D1.W := `258`.
- **`b3eea`**: D2.W := WORD `7a`, D3.W := WORD `7c`, BYTE `95` bit 2 ≠ 0 → `b3f02`, 아니면 `b3efc`: BYTE `94` := 5.
- **`b3f02`**: LONG `76` := A0, LONG `7a` := A0, WORD `8c` := D1.W, BYTE `95` := D2.B, D2.B &= 3, BYTE `15` ^= D2.B, WORD `8a` := D0.W, `JSR b3f4c(PC)`(복귀 `b3f22`).
- **`b3f22`**: `JSR b3f68(PC)`(복귀 `b3f26`). **`b3f26`**: `JSR 49a58`(복귀 `b3f2c`).
- **`b3f2c`**: D0.W &= `8000`, WORD `98` := D0.W, D3.W ≠ 0 → `b3fc6`, 아니면 `b3f3a`.
- **`b3f3a`**: A0 := LONG `6(A1)`, `JMP (A0)`(결정 4).
- **`b3f4c`**: `JSR b3f5c(PC)`(복귀 `b3f50`). **`b3f50`**: D0.B := BYTE `(A0)`, D0.W &= `ff`, WORD `90` := D0.W, `RTS`.
- **`b3f5c`**: D0 := D0.W × `c`(MULU.W, 32 bit), A0 := `b3894` + sext(D0.W)(ADDA.W), `RTS`.
- **`b3f68`**: D0.W := WORD `2(A0)`, D0 := D0.W × `a`(MULU.W), A1 := `b3484` + sext(D0.W), WORD `8e` := WORD `2(A1)`, BYTE `97` := BYTE `(A1)`, D0.W := WORD `4(A1)`, LONG `7e` := LONG `(b3f8c + sext(D0.W))`, `RTS`.
- **`b3fa4`**(설치 값·표 대상): `JSR 8ff4`(복귀 `b3faa`). **`b3faa`**: D0.W := WORD `8a`, `JSR b3f5c(PC)`(복귀 `b3fb2`).
- **`b3fb2`**: D0.W := WORD `2(A0)`, D0 := D0.W × `a`, A0 := `b3484` + sext(D0.W), A0 := LONG `6(A0)`, `JMP (A0)`(결정 4).
- **`b3fc6`**: D3.W := 4·D3.W(WORD wrap), `JMP b3fce(PC,D3.W)`: PC := `b3fce` + sext(D3.W)(결정 3).
- **`b3fce`** `b3fd2`(표 항목 0·1): `BRA.W b3fa4`/`b3fd6`.
- **`b3fd6`**: A0 := A6 + `26`, WORD `20` := `1e3`, LONG `22` := LONG `2001c0`, D0.W := `100`, A0 := A6 + `26`, A1 := LONG `22`, A1 := LONG `c(A1)`(bank 창), `JSR 49f8c`(복귀 `b3ffe`).
- **`b3ffe`**: D0.W := `380`, D1.B := 0, `JSR 8ebe`(복귀 `b400c`). **`b400c`**: 설치 `b4012`.
- **`b4012`**(설치 값): `JSR 43e34`(복귀 `b4018`). **`b4018`**: `JSR 49fc6`(복귀 `b401e`). **`b401e`**(소비자): Clear → `b4028 RTS`, Set → `b4022`: LONG `(A6)` := `b3fa4`(설치만, `b4028`로 이어짐).

## helper `4b6f4..4b702`(3)

- **`4b6f4`**: BYTE `5b86(A5)` = 0 → `4b700`(C Clear), 아니면 `4b6fc`(C Clear). **`4b6fc`**: `ORI.B #1,CCR`(C Set, fall-through). **`4b700`**: `RTS`(C 보존).

## 처리기 `d131a` `d131a..d1348`(3)

- **`d131a`**: A0 := `d13b4`, D0.W := `14`, A1 := `100bf4`, `JSR 2986`(복귀 `d1330`). **`d1330`**: WORD `76(A0)` := 0, D0 := 0(MOVEQ), D1.W := `20`, `JSR 49214`(복귀 `d1342`). **`d1342`**: `JMP 491b6`.
- [F] `2986` caller-X 제한(buffer_cue 결정 1)은 그대로다. 할당 실패면 `298e`가 기존 checked 오류를 낸다(이 단위의 문제가 아님).

## U06 이웃 `eb9ba..eba3e`(14)

- **`eb9ba`**: D3 := 0(MOVEQ), D1.W := WORD `7e`, bit 15 = 0 → `eb9ce`, 아니면 `eb9c4`: WORD `7e` := WORD `7a`, `BRA.W eb9dc`.
- **`eb9ce`**: 부호 D1.W < WORD `7a` → `eb9dc`, 아니면 `eb9d6`: WORD `7e` := 0(fall-through).
- **`eb9dc`**: D3.W ≠ 0 → `eb9e4`, 아니면 `eb9e2 RTS`. (`eb9ba`에서 오면 D3 = 0이라 항상 `eb9e2`; `eb9e4`는 U06 `eb878` `eb892`가 직접 부르는 진입이다.)
- **`eb9e4`**: D1.W := WORD `7c`, bit 15 = 0 → `eb9fa`, 아니면 `eb9ec`: WORD `7c` := WORD `78`, WORD `7c` −= 1, `BRA.W eba08`.
- **`eb9fa`**: 부호 D1.W < WORD `78` → `eba08`, 아니면 `eba02`: WORD `7c` := 0(fall-through).
- **`eba08`**: A0 := `eba9e`, D0.W := WORD `7c` << 3(LSL.W), LONG `80` := LONG `(A0 + sext(D0.W))`, WORD `84` := WORD `(A0 + sext(D0.W) + 4)`, WORD `86` := WORD `(… + 6)`, `JSR eba3e(PC)`(복귀 `eba28`, U06).
- **`eba28`**: `JSR 8ff4`(복귀 `eba2e`). **`eba2e`**: D0.W := WORD `84`, D1.B := 0, `JSR 8ebe`(복귀 `eba3c`). **`eba3c`**: `RTS`.

## HUD 목록 `515e0..515fc`(5) `51602..51608`(1)

- **`51602`**: A0 := `51620`, `BRA.B 515e0`.
- **`515e0`**: push WORD D2(fall-through `515e2`).
- **`515e2`**: D0.W := WORD `(A0)`, A0 += 2, bit 15 = 0 → `515ec`, 아니면 `515e8`: A7 += 2(ADDQ.W, A 전체), `RTS`.
- **`515ec`**: D1.W := WORD `(A0)`, A0 += 2, D2.W := WORD `(A7)`, push LONG A0, `JSR 8cda`(복귀 `515f8`). **`515f8`**: A0 := pop LONG, `BRA.B 515e2`.

## 자기 삭제 callback `b7742..b7748`(1)

- **`b7742`**(설치 값): `JMP 2a00`.

## U05 끝 상태 `b975e..b97c0`(10)

- **`b975e`**(설치 값, U05 `b9736`): A0 := A6 + `26`, WORD `20` := `203`, LONG `22` := LONG `2001d0`, D0.W := `100`, A0 := A6 + `26`, A1 := LONG `22`, A1 := LONG `48(A1)`(bank 창), `JSR 49f8c`(복귀 `b9786`). **`b9786`**: 설치 `b978c`.
- **`b978c`**(설치 값): `JSR 43e34`(복귀 `b9792`). **`b9792`**: `JSR 49fc6`(복귀 `b9798`). **`b9798`**(소비자): Clear → `b97a8`, Set → `b979c`: WORD `76` := 1, LONG `(A6)` := `b970e`(설치만, U05 block; `b97a8`로 이어짐).
- **`b97a8`**: A0 := `ba3d6`, `JSR 1ab02`(복귀 `b97b4`). **`b97b4`**(소비자): Clear → `b97be RTS`, Set → `b97b8 JMP 2a24`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다(scratch `data_a.py`, `tbl_b3dbc.py`). index 범위는 원본에 상한 검사가 없어 [I]로 적는다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다.

| 표 | 범위 | 읽는 곳 | 내용 |
| --- | --- | --- | --- |
| bank LONG | CPU `2001c0` `2001d0`(bank 창) | `b3fd6`, `b975e` | 물리 `200000` bank: `002cdeaa`(LONG `c` = `002cdfea`), `002d450e`(LONG `48` = `002d4798`). 물리 `300000` bank: `00028260`, `01868260`([I] 이 bank에서는 이 객체가 쓰이지 않는다) |
| 점프 표 | `b3dcc..b3ddc` | `b3dc8`(계산 대상) | `6000 000e` `6000 0012` `6000 0016` `6000 001a`(`BRA.W b3ddc b3de4 b3dec b3df4`) |
| 점프 표 | `b3fce..b3fd6` | `b3fca` | `6000 ffd4`(`BRA.W b3fa4`) `6000 0002`(`BRA.W b3fd6`) |
| 아이템 기록 | `b3894..b3dbc`(12 byte × 110, SHA256 `e55d358c5f83da281bca84ee20b85dda8d3fb6422b09aae229646e30f72a4d27`) | `b3f50`(BYTE 0), `b3f68` `b3fb2`(WORD 2 = 종류 index) | index = WORD `76`/`8a`(< `6e`는 `b3ea2`만 확인) |
| 종류 기록 | `b3484..b3894`(10 byte × 104, SHA256 `3f473be99dba878a90675d336bbfa133ab8160cdd9d4b82623562758c4fbb648`) | `b3f68`(BYTE 0 → `97`, WORD 2 → `8e`, WORD 4 → 표 `b3f8c` offset), `b3f3a` `b3fb2`(LONG 6 = 처리기) | 처리기 101곳: `bfb5a..c0022`(8 byte 간격 75곳 포함), `c06de` `c06e6` `c06ee` `c0986` `c098c` `c0a58` `c0ace` `c0ba8` `c0c1e` `c0c42` `c0d68` `c0e2a` `c0ea0` `c1036` `c13c0` `c1560` `c16f6` `c188c` `c191a` `c1af6` `c1b98`, `d8f78` `d8f7e` `d8f88` `d8f8e` `d8f98` `d8f9e`, 전부 routing 밖(scratch `tbl_b3dbc.py`가 전부 출력) |
| LONG 표 | `b3f8c..b3fa4`(SHA256 `2facdee2fb880a2a861a13991de6f88c80fce8ac831d57917bf2b844625a81bf`) | `b3f68`(offset WORD 4 = 0, 4, …, `14`) | `00000000 ffffc000 ffffa000 ffff8000 ffff6000 ffff4000` |
| HUD 목록 | `51620..51626`(SHA256 `94304c45f114161d991e6f300c458517d9ae5619f9e59490a4af3eecdf9f8909`) | `515e2` `515ec`(A0 = `51620`) | `0085 0201`, 끝 `ffff`. 형제: `5160e` = `0081 0201 0082 0201 0083 0201 0084 0201 ffff`, `51626` = `00ff 0200 ffff` |
| 메뉴 기록 | `eba9e..`(8 byte: LONG, WORD, WORD) | `eba08`(index WORD `7c` ∈ [0, WORD `78`) [I]) | 처음 12개: `(00000002,0c00,0009) (0000000a,0c0a,000a) (00000012,0c15,0007) (0000001a,0c1d,000a) (00000022,0c9d,0000) (0000002a,0c9e,0001) (00000032,0ca0,0002) (0000003a,0ca3,0003) (00000042,0ca7,0001) (0000004a,0ca9,0004) (00000052,0cae,0001) (0000005a,0cb0,0001)` |

- [F] **callee에게 넘기기만 하는 자료**(이 단위는 읽지 않음): `1a5a4`의 A0 = `de526`; `3a70`의 A0 = `e503c` `e5014` `e5028` `e507a` `e504c` `e505e`(문자열), A1 = `e84c8`; `3670`의 A0 = A6 + `76` / `10de14` / `10de1c`, A1 = `e84c8`, D1 = `461`, D3 D4; `1ab02`의 A0 = `ba3d6`(사각형 `ffd0ff00 00600200`); `36ba`의 D0..D4; `28ae`/`2986`의 자식 값 `de97e` `de8ca` `deba4` `deb1a` `de9e8` `e5580` `d13b4`(다음 frontier, 결정 7); `8c16`의 D0..D3; 소리·효과 `3af8`(`19da` `73c` `19c0..19cf` `1ac4` `1acf`) `3c44`(`73c`) `8ebe`(`380`, WORD `84`) `49a84`(`3e8`) `49214`(0, `20`); 저장만 하는 포인터: LONG `76`/`7a` := `b41be`/`b4036`/`b42a2`/`b403e`(`b3f02`).
- [I] index가 [I] 범위 밖이면 원본은 다음 코드·표 바이트를 자료로 읽는다. C++도 같은 주소를 live bus로 읽는다(단위 시험에서는 합성 바이트 밖이라 bus checked 오류).

## 경계·routing 밖 출구

- [F] routing 밖 실행 PC: `b3eac`(`TRAP #15`), 계산 점프의 live 대상(`b3dc8` `b3fca` 표 밖 index, `b3f3e` `b3fc4`의 처리기 LONG). 그 밖은 위 자료뿐이다.
- [F] routing된 출구·callee: 위 "요약"의 목록. `RTS`로 끝나는 block 26개: `ca42` `4b700` `4e0de` `4e164` `515e8` `b3f50` `b3f5c` `b3f68` `b4028` `b97be` `de68e` `de75c` `de782` `de838` `de854` `de8a0` `e536c` `e5386` `e542c` `e5446` `e54ec` `e5540` `e5570` `e5720` `eb9e2` `eba3c`.
- [F] 공유 진입: `ca42`는 범위 밖 `4e848` `4e8b2`가, `4b6f4`는 20곳이, `515e0`은 형제 `515fc` `51608`가, `b3ea2`는 형제 `b3e18` `b3e70`이, `b3f4c`·`b3f68`은 형제 `b3e9c` `b3f40` `b3f44` `b3f48`이 쓴다. 이후 그 코드를 넣는 단위는 이 단위의 block 시작으로 끝나야 한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, B3a~B4b spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 자연 node·0·RAM 목록, LONG `c(A6)` := 자연 node, LONG `22(A6)` := 실제 bank 포인터, 아이템 index WORD `76`/`8a` < `6e`, 표 index WORD `7c`/`7e`, `515xx` 스택 WORD/LONG, PC).
- [I] **IO 관측 상태도 node seed로 좋다**: `artifacts/animation_machine_io_native`의 frame 시작 상태(`states/*.pack.gz`)에서 확정 frontier frame(예: P1 case 94 frame 2 `de660`, case 0 frame 99 `b3dbc`, case 90 frame 100 `e5324`, case 32 frame 181 `4b6f4`)을 frontier PC까지 실행한 상태가 이 단위의 실제 진입 상태다. V1 spec에는 이 출처를 주석으로 적고, IO 비교 재실행(검증 작업자)이 자연 경로를 직접 확인한다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`1ab02` → `b97b4`(`b97a8` 진입), `49fc6` → `b401e`(`b4018`) `b9798`(`b9792`); `49fc6`는 단위 시험에서 선언 C, V1·실제 ROM 차분에서 실제 사슬). `4b6f4`의 C는 실제 소비자 `5f5e6`(B2a, 복귀 LONG)을 거쳐 native 분기로 확인한다(Unicorn SR은 읽지 않는다).
- node fixture: callback 진입(`de660` `e5324` `b3dbc` `b975e` `b7742`)과 설치 값(`de686` `de754` `de778` `de814` `de84c` `de880` `e5364` `e537e` `e539e` `e5418` `e5424` `e543e` `e545e` `e54d8` `e54e4` `e5538` `e5568` `b3fa4` `b4012` `b978c`)을 node callback으로 들어가 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `4b6f4` `ca42` `4e146` `4e0de` `e56c0` `51602` `515e0` `eb9ba` `eb9e4` `d131a` `e5292` `e52b2` `e52d6` `e52f6` `b3f4c` `b3f5c` `b3f68`을 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, B4b 꼴): 시작 214개 × 들어오는 C 3가지, zero-step, 내부 PC 907개 정확한 오류, 경계 stop(`TRAP` `b3eac` 포함), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC, BYTE·WORD 부호 경계(BYTE ≥ `80`, WORD ≥ `8000`, `MULU` 뒤 sext 경계 `12·k`/`10·k` ≥ `8000`)를 고르는 hint, 계산 점프 대상 전부(표 항목, 다음 block 시작 `b3ddc`/`b3fd6`, 내부, 홀수, 범위 밖), `DIVU` 0 제수·몫 넘침.

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `probe_scan.py`: 18 범위 안 값, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`):
  - **U06 시험 `boundaries()`**: `eb818-up`(stop `eb9ba`)·`eb81e-next`(stop `eb9e4`) 행을 stop 없이 다시 돌려 `unsupported animation machine PC`를 기대한다 → 이 단위가 routing하므로 stop-only로 옮긴다(결정 8). `e742c-clear-busy`(`3ed2`) 행은 그대로다.
  - **area_clear 검증기**(`tools/verify_animation_machine_area_clear.py` 883행 `unrouted_neighbour_04b6f4`, 기대 `unsupported animation machine PC`): B2 결정 4가 미뤄 둔 항목이다. 이 단위가 `4b6f4`를 routing하므로 기존 방식(`SUPERSEDED_NEIGHBOURS` 분류 + `SUPERSEDED_NEIGHBOUR_ERRORS`의 새 오류, 행에 `former_expected_API_error` 기록)으로 옮긴다(결정 9). 두 결과를 모두 허용하지 않는다.
  - 그대로 참인 것: U02 `rom_outside[]`(`e5324` `e5292` `e56c0` `e5722`), U05 `rom_outside[]`(`b975e` `b9760`), U06 `rom_outside[]`(`eb9ba` `eb9e4` `eba3c`), area_clear 시험 `rom_outside[]`(`ca46`), B2a·B2b `ends[]`(`4b6f4`)는 "자기 범위 밖"만 본다. B2a `boundary-stop-4b6f4`·`5f5da` 설치 확인, U14 `boundaries()` `want[]`(`51602`), U06·U14·U02 생성 표의 stop 행, C2 시험 `de660`(레지스터 값)은 stop-only라 그대로 통과한다.
  - Python 관측기·검증기의 `F1B_RANGES`(`4b6e4..4b6f4`), `observe_animation_machine_objects_g1.py`·`_g2.py`의 BOUNDARY 표, `observe_animation_machine_pvc_banks.py` `U06_RANGES`는 고정 관측 도구다(pin된 역사 기록; 고치지 않음). [I] 그 관측을 다시 돌리면 경계가 달라질 수 있다(재실행 대상 아님).
  - V1 spec `b2a.py`의 `c4b6f4` 계열(native는 `4b6f4`에서, C++는 소비자에서 시작)은 그대로 성립한다. [I] `b2a.py` 사슬 fixture의 첫 routing 밖 정지가 `4b6f4`였던 행은 이제 더 진행한다(V1은 매번 다시 만든다: 검증 작업자가 b2a·u06 계열 회귀로 확인).
- [I] 계산 PC로 이 범위에 착지하는 숨은 탐침(예: 다른 단위의 node 사슬이 `4b6f4` `eb9ba` `51602` `b975e`를 지나 rollback을 기대하는 행)은 구현 뒤 `make test`로 찾는다. 찾으면 결정 8대로 옮기고 이 절에 더한다.
- [I] frame 회귀: `4b6f4` `eb9ba` `51602` `b975e` `b7742`는 기존 자연 frame(D1·controller·IRQ·demo)에서도 닿을 수 있다. 그 frame이 지금까지 이 PC에서 `unsupported animation machine PC`로 끝났다면 더 진행한다(이득). 자연 불일치는 결함이다(검증 작업자).

## 결정

1. **범위·분할.** 562 block을 FR1a 214 / FR1b 199 / FR1c 148로 나눈다. FR1a는 frontier 실행 수 14·12·12의 root와 실행 수 3인 작은 객체 6개다. 실행 수 3인 큰 객체(`b30f6` 86, `5a376` 40, `bc08c` 148)와 E title/demo(`de376` `de024`, 겹침 포함 73)는 FR1b·FR1c로 미룬다.
2. **`e4ffc`·`d0fec` root.** IO root 규칙의 부산물로 보고 확정 frontier PC `e5324`·`d131a`로 바꾼다. `e4ffc..e5086`(문자열)·`d0fec`(다른 helper)는 넣지 않는다.
3. **표 점프 `b3dc8 JMP b3dcc(PC,D0.W)`·`b3fca JMP b3fce(PC,D3.W)`.** PC := 표 시작 + sext(index.W)(32 bit)로 옮긴 뒤 대상 검사는 routing에 맡긴다(B4b 결정 3의 `e74fc`와 같은 꼴): 표 항목이면 그 block, 표 바로 뒤 block 시작(`b3ddc` = index 4, `b3fd6` = index 2)이면 그 block(원본과 같이 실행), 이 단위의 다른 짝수 PC면 그 block 또는 `unsupported animation objects fr1 PC`, 홀수면 `unaligned animation machine PC`(index.W가 4의 배수라 이 경우는 없음), 그 밖은 그 PC의 routing(routing 밖이면 `unsupported animation machine PC`). 원본 표는 정적으로 4·2 항목이다. F1 결정 3대로 표 밖 착지는 원본 그대로 따라가거나 checked 오류다.
4. **`JMP (A0)` `b3f3e`·`b3fc4`.** PC := A0(32 bit, live 대상 routing). 처리기 101곳(표 `b3484` LONG 6)은 이 단위에 넣지 않고 다음 frontier로 둔다(전사는 위 표). 홀수 A0는 `unaligned animation machine PC`.
5. **carry 보존 목록.** 소비자 3개(`b401e` `b9798` `b97b4`)와 통과 `RTS` `4b700`만 넣는다. `4b6f4`(TST → C Clear)·`4b6fc`(ORI → C Set)는 자기 block에서 known C를 남긴다(호출자 20곳이 읽음). 브리프의 "소비자만" 원칙에서 `4b700`은 C를 호출자 소비자에게 전달하는 유일한 경로라 포함한다(메인 확인 필요).
6. **`DIVU.W D2,D0`(`e56d0` `e56e6` `e56fe` 둘).** D2.W = 0이면 `objects fr1 DIVU zero divisor`(checked, N13 관례), 몫 > `ffff`면 D0 그대로(V만 서고 C++는 V를 모델링하지 않음), 아니면 D0 := 나머지 << 16 | 몫. 단위 안 경로(`e56c0`가 D2.W := `a`, D0 &= `ffff`)에서는 둘 다 생기지 않는다; 직접 진입에서만 생긴다.
7. **자식 값.** `28ae` 자식 `de97e` `de8ca` `deba4` `deb1a` `de9e8`(`de660`), `e5580`(`e5324`), `2986` 자식 `d13b4`(`d131a`)와 `b3dbc` 처리기는 따라가지 않는다(다음 frontier 후보, FR2).
8. **숨은 탐침 이전.** 기존 시험이 이 범위의 PC를 routing 밖 rollback으로 기대하면 RAM `10fexx` 탐침이나 stop-only 확인으로 옮기고, 옮긴 곳은 "영향받는 기존 시험"과 "구현·검증 기록"에 대응을 적는다.
9. **area_clear 이웃 `4b6f4`.** 예전 기대(`unsupported animation machine PC`)는 `former_expected_API_error`로 남기고 분류 `superseded_by_FR1_routes_4b6f4`, 새 오류는 이 단위 뒤 C++가 실제로 내는 정확한 문자열 하나로 고정한다(구현 뒤 측정, "구현·검증 기록"). 검증기 SHA는 바뀐다(manifest 0267의 pin은 역사 기록).
10. **`TRAP #15` `b3eac`.** 단위 범위에 넣지 않는다(`b3ea2..b3eac`). WORD `76` ≥ `6e`이면 `b3ea2`가 PC := `b3eac`로 끝나고 다음 dispatch가 `unsupported animation machine PC`(전체 rollback)를 낸다.

## FR1b 명세(다음 단위)

[F] scratch `FR1PART=b unit_fr1.py`로 같은 규칙에서 낸 값이다. `starts_b.txt`(199) SHA256 `f396240016f4a67f8c433e8d4d39e4970692f5bb8be6bef1150bbdaa9857f000`, 이어 붙인 바이트 1956, SHA256 `f20d14ba254b85323f1cd9ec2fe2c708fb48c0b9b5e1ade3801aaf87c0f29b7e`, 짝수 PC 978(내부 779), 명령 456.

| 범위 | 바이트 | SHA256 | block |
| --- | --- | --- | --- |
| `5a376..5a460` | 234 | `b40fa049cc1c974e2a276361354243ad4ee97df6b4ee62c3a793e41ce0bff9b0` | 26 |
| `5a54e..5a5ba` | 108 | `4313e82d039afeb3dca3614ddbff02213a0751309cb78121821ea5a40f18bfbe` | 14 |
| `b30ba..b336a` | 688 | `4529700726f10b63315513626c39865f35249a4c23060d1521c638b940ecc124` | 75 |
| `b3460..b3484` | 36 | `ccde97acb2265a2e6f4222673dfff69bc90b05aeac24045d81e61525d9a89beb` | 5 |
| `ddfdc..de00c` | 48 | `73e414c2d10bac8c79fc157c1cf8f13bc7a274933a2359c22f2567cad3a10987` | 5 |
| `de024..de260` | 572 | `e8e052b8c97eb59cfb5c8bd531ab44477338d98554f8dffca1886b76fda4958a` | 46 |
| `de2b6..de31e` | 104 | `c6d3ec1014779552fca1710f812445bb238caf93c1b4351f199bf9a17290766f` | 9 |
| `de376..de3e6` | 112 | `43a25ea90142baf79b660683a20948c44298f76fdae6f799470d07e322c7bd22` | 13 |
| `e9112..e9148` | 54 | `beb10bb2eb9acfd8952b07e3fbf061b6588bcfdf59abf52d207c2e460590b945` | 6 |

- 진입: `b30f6`(node callback; 설치 `b31dc` `b3246`, 사슬은 `b3242 BRA b30ba`로 `b30ba..b30f6`를 지남), `5a376`(설치 `5a3c6` `5a3e4` `5a41e` `5a43a` `5a54e` `5a574`), `de376`(설치 `de3c2`), `de024`(설치 `de054` `de0d8` `de0ee` `de112` `de15c` `de1a8` `de1b4` `de204` `de210` `de2b6` `de2cc`). 공유 helper `ddfdc..de00c`(두 E 진입이 `BSR`), `de3ae..de3e6`는 `de376` 범위 안.
- 출구(모두 routing됨): `101c` `28ae` `2a00` `35f0` `3af8` `8c16` `8da2` `caf0` `cd58` `16fac` `16ff8` `17012` `1861a` `1ab02` `43ea4` `43ffc` `490ba` `491b6` `49214` `493bc` `4945e` `496c2` `4970a` `49a58` `49f8c` `49fc6` `4ae4a` `4b54e` `4be2c` `5a802` `5a9c2` `5ab5a` `c6a96` `e7c16` `e89da` `e932c`. 자식 `b336a` `b33d8` `d1d08` `d1d38`.
- carry 소비자 [F]: `b30ea` `b335e`(BCC, `1ab02`), `b31f4`(BCC, `b3460`), `b3470`(BCC, `493bc`), `b32d8` `b330a` `b333c`(BCC, `28ae`), `5a3f8`(BCC, `5ab5a`), `5a58e`(BCS, `4945e`). known C 생산: `b3474`(ORI, Set)·`b347e`(ANDI, Clear) → `b3460`의 `RTS`(같은 block 끝), `b32ea` `b331c` `b334e`(ORI, 읽는 곳은 각자 확인: `b3358 JSR 1ab02`가 덮음, `b3352 JMP 2a00`).
- 표: `5a59c MOVEA.L 5a5ba(PC,D0.W),A0`(index = (`49a58` & 3)·4; LONG 표 `5a5ba..5a5ca` = `5a0ae 5a1c4 5a376 5a460`)의 값은 `5a5b4 MOVE.L A0,(A6)`로 설치된다. [I] 이 표 설치 값(`5a0ae` `5a1c4` `5a460`, 셋 다 routing 밖)은 같은 객체의 다른 상태다. 따라가면 `59f1a..5a376` `5a460..5a5ba`까지 172 block이 더해진다. FR1b에서 "표 설치 값을 진입으로 넣을지" 결정해야 한다(권고: 넣지 않고 다음 frontier로; 넣으면 FR1b를 둘로 나눈다).
- 주의: `de05e`는 `MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l`(PVC port 쓰기, `am_zero_bank`와 같은 꼴)과 `MOVEA.L 20000c.l,A0`(bank 창)·`(A0,D0.W)` 표 읽기를 한다. `de2cc` `de2fe` `de3c6`은 ROM 표 `de34e` `de3e6`를 `(A0)+`로 읽는다. `e9112..e9148`은 `BRA.W e932c`로 끝나는 공유 helper(`e910e`도 같은 코드로 들어옴)다.
- 영향받는 기존 시험: 이 계약 범위 밖이라 측정하지 않았다(FR1b 작업자가 `probe_scan.py`를 `FR1PART=b`로 다시 돌린다).

## FR1c 명세(다음 단위)

[F] `starts_c.txt`(148) SHA256 `8b4ce0695c74311baf724817e25bd955f1773a190bfc206aa1decd56a904dcc0`, 이어 붙인 바이트 1746, SHA256 `b57fa00163a69a553fa1e4eef56d85daf9e6aa7b90de62437c04d69ba15d7e34`, 짝수 PC 873(내부 725), 명령 348.

| 범위 | 바이트 | SHA256 | block |
| --- | --- | --- | --- |
| `bc08c..bc404` | 888 | `a608a6c9262f83fba0183695ecaf88c95e49f3efbfb4e3325599da09d8fed2bd` | 66 |
| `bc47c..bc7d6` | 858 | `d1f36ff57653cc45f0bd7db243e1649ab4352c46f7a17d59bc1c7f530a46cf6c` | 82 |

- 진입: `bc08c`(node callback)와 설치 값 34곳(`bc0b2` `bc0c2` `bc132` `bc1b8` `bc1ea` `bc202` `bc246` `bc290` `bc2be` `bc2fe` `bc32c` `bc344` `bc388` `bc47c` `bc4b0` `bc4cc` `bc504` `bc520` `bc566` `bc584` `bc5ca` `bc5e8` `bc624` `bc640` `bc696` `bc6ae` `bc6d2` `bc6ea` `bc6fa` `bc716` `bc742` `bc75a` …; scratch `unit_c.out`가 전부 출력).
- 출구(모두 routing됨): `28ae` `8ebe` `8ff4` `43e34` `49214` `49290` `4970a` `49f8c` `49fc6` `4be06` `4be2c` `4be34` `4bfa4` `c6a96`. 자식 `bc404` `bc7d6` `bc844` `d6c78`. bank 창 LONG `200140`(LONG `1c` `8c` `c` `10` `14`…).
- carry: `bc1f6` `bc338` …(BCC, `49fc6`) 등 소비자는 FR1c 작업자가 같은 규칙으로 센다. `bc0b2 SUBQ.W #1,76(A6); BCC`는 같은 block 안 C다.

## 미확인

- [U] BYTE `62` `94` `95` `97`, WORD `76` `78` `7a` `7c` `7e` `80` `82` `84` `86` `8a` `8c` `8e` `90` `98`, LONG `76` `7a` `7e` `80`의 의미(객체마다 다름); `1ab02`·`49fc6` C의 정확한 의미.
- [U] 화면상 이름(캐릭터 선택·결과·아이템 종류), `e5324`의 `10fdb6`·`10de14`·`10de1c` 의미, `4b6f4`의 BYTE `5b86(A5)` 의미.
- [U] 물리 `300000` bank에서 `2001c0` `2001d0`의 쓰임.
- [U] `d131a`를 담은 호출 표의 위치(실행 근거는 `4a43c JSR (A1)`뿐).
- [U] 자연 frame에서 이 단위 뒤 다음 첫 미routing PC(IO 비교 재실행으로 확인; [I] 예상: `de660` 계열은 자식 `de97e` `de8ca` `deba4` `deb1a` `de9e8`, `e5324`는 자식 `e5580`, `b3dbc`는 표 `b3484` 처리기, `d131a`는 `d13b4`, 나머지는 FR1b·FR1c root나 다른 미routing 코드).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr1.cpp`(case label 214 = scratch `starts_a.txt`와 집합 일치), `engine/tests/animation_machine_objects_fr1_test.cpp`(생성 구역 + 수작성 규칙: `51602`/`515e0`의 스택 순서(WORD D2, LONG A0, 복귀 LONG `515f8`), `515f8`/`515e8`의 pop, 표 점프 `b3dbc`(WORD `7e` = 0..4, `2000` → `abdcc` 부호 확장)·`b3fc6`(D3.W = 0..2, `2000` → `abfce`), `4b6f4`의 C(BYTE 0 → Clear, 아니면 Set)와 `4b700`의 C 보존(Unknown 포함), `e56d0` DIVU 몫 넘침(D0 그대로), `e56c0` BCD(`3e7` → `999`), `b3ea2` → `TRAP` `b3eac` stop-only, 자료·TRAP PC 5개(`b3dba` `b3eac` `b3f8c` `b3fa2` `de65e`)의 dispatcher 오류), `tools/generate_animation_machine_objects_fr1_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음, SHA256 `0cbda5adcdd45815…`, 약 70초), `tools/unit_fixture_specs/fr1.py`(V1 spec; 정적 검사만 함 — `load_routing` 규칙 119개 뒤 시작 214개가 모두 `animation_objects_fr1_block`, 내부 907개도 모두 같은 실행부, `b3eac`·sentinel은 routing 밖, 정적 후속은 시작이거나 범위 밖; `first_unrouted`는 B4b spec의 capstone 길이 디코드판). 공유 수정은 "공통 규칙"의 다섯 곳뿐이다.
- [F] 단위 시험 world: A7 = `10ef00`; `515e2` `515e8` `515ec`는 A7 아래 선언 WORD, `515f8`은 LONG(목록) + WORD를 둔다. 합성 typed physical byte(ROM 자료 아님): bank `2001c0`(→ `2a0000`) `2001d0`(→ `2a0100`), `2a000c` `2a0148`, 종류·아이템 기록 `b3484..b3dbc`(종류 기록 0/1/2의 처리기 = `b3fa5`(홀수) `b3fa6`(단위 안) `10fe40`(RAM); 아이템 기록 `6d`의 종류 index `ccd`, 종류 기록 103의 offset `8000`으로 MULU·ADDA.W/표 offset의 부호 확장을 확인), LONG 표 `b3f8c..b3fa4`, 목록 `51620..51626`, 메뉴 기록 `eba9e..ebb1e`, `1ab02` 사각형 `ba3d6..ba3de`, 부호 확장 대상 `ab486` `abf8c` `e3a9e`. native 실행 중 단위 안 비시작 PC에 계산 착지하면(또는 홀수 PC) 그 run은 버리고 오류 행이 대신한다.
- [F] `make -j3 all test`(작업자): 종료 0, 경고 0, Assert 줄 0, 시험 실행 271개, Python 310개 통과. FR1 시험 줄: `727 fixtures (518 single-block, 159 path, 11 producer chain, 6 declared C, 33 checked error (17 with a later failing PC), 27 kept C), 214 blocks, 3929 calls, 44272 checks`. 실제 생산자 사슬: `1ab02`(`b97a8` → `b97b4`) C Clear/Set 둘 다, `4b6f4` → `4b700` → B2a `5f5e6`(→ `5f5f0` Clear / `5f5ea` Set) 둘 다. 단일 block 표에서 모든 조건 분기의 두 쪽을 들어갔다(누락 0). 기준(`5c30b72`, scratch `make_io_final.log`) 대비 다른 시험 줄의 변화는 U06 `1550 → 1548 calls`(아래 1)뿐이다.
- [F] 무효가 된 기존 탐침과 이전(결정 8·9):
  1. U06 시험 `boundaries()`의 `eb818-up`(stop `eb9ba`)·`eb81e-next`(stop `eb9e4`) rollback(`unsupported animation machine PC` 기대) → stop-only(`final_of(...).s.pc`)로 바꿨다. 첫 `make test`에서 `eb818`이 FR1a를 지나 다른 checked 오류(`unsupported sprite callback target`)에 닿아 실패한 것으로 찾았다. `e742c-clear-busy`(`3ed2`)는 그대로다. U06 줄은 fixture 수가 같고 호출 수만 2 줄었다.
  2. area_clear 검증기 `unrouted_neighbour_04b6f4`: 예전 기대 `unsupported animation machine PC`를 `former_expected_API_error`로 남기고(`reject_one`이 `SUPERSEDED_NEIGHBOURS` 행에 기록), 분류 `superseded_by_FR1_routes_4b6f4`, 새 기대 `program bus write requires RAM mirror units` 하나로 고정했다. 이 값은 검증기 자신의 one-shot harness(`common.HARNESS`, 이 작업 트리 객체에 링크)로 natural-000 기준 상태·carry 2·stop `ff000`에서 측정했다(scratch `ac_probe.py`). 같은 방법으로 잰 대조 이웃 `1c5ea`(기존 기록과 같은 `program bus write requires RAM mirror units`), `1bef8` `ca50`(`unsupported animation machine PC`)가 기존 기대와 같아 측정 방법을 확인했다. [I] `4b6f4` → `4b700 RTS`가 기준 상태의 복귀 LONG으로 돌아가 frame 코드가 ROM 미러가 아닌 곳에 쓰다 멈춘다(B2 결정 4에서 예상한 대로 기대가 바뀜). 검증기 전체 실행은 하지 않았다(검증 작업자 몫; 이 검증기는 공유 `artifacts/` 아래 자기 출력 폴더를 지우고 다시 쓰므로 scratch에서 OUT을 바꿔 실행해야 한다).
  - 그 밖의 시험·Python 시험 변화 없음(B2a `boundary-stop-4b6f4`, U14 `51602`, U05·U02 `rom_outside[]` 등은 그대로 통과).
- [F] **검증 기록(검증 작업자, Sonnet 5.5 / medium, `MS5_SEED_DIR=artifacts/stage_entry_body`)**:
  - `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310개 OK, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. U06 줄 `154 fixtures ... 1548 calls`. 변이 생존자 정리 뒤 FR1 줄: `animation machine objects fr1: 747 fixtures (538 single-block, 159 path, 11 producer chain, 6 declared C, 33 checked error (17 with a later failing PC), 27 kept C), 214 blocks, 4009 calls, 45463 checks`(생성기 두 번 실행, 시험 파일 SHA256 `a3f820e94c566939...` 동일). 다른 시험 줄은 기준 로그와 같다.
  - UBSan(`build_ubsan.sh`, 생존자 정리 전후 두 번): 종료 0, `runtime error` 0, 같은 FR1 줄.
  - 변이 144개: 140개 즉시 죽음, 생존 4개를 분석했다. `de81a-d3-word`(`MOVEQ #0,D3`이 D3 전체를 지움: 생성기 hint `d3` = `12345678` `ffffffff` `80000001` 추가), `e5552-no-62`(BYTE `62(A6)` 비영 값 hint 추가), `eba2e-84`(WORD `84(A6)` != `86(A6)` hint 추가)는 hint로 죽였다. `clamp-lt`(`e53da` `e549a`의 `BLS` 경계를 `<`로 바꿈)는 **상태 동치로 증명**: D0.W == `3e7`일 때 원본은 `e53e8`로, 변이는 `e53e4`(`MOVE.W #3e7,D0`, D0.W가 이미 `3e7`이라 아무 변화 없음)를 거쳐 `e53e8`에 닿는다. 레지스터·RAM·포트·carry가 같고 중간 PC만 다르며 시험은 stop `e53e8`의 상태를 본다. hint(`3e6` `3e7` `3e8` `103e7` `ffff` `8000`)를 넣은 뒤에도 같은 변이가 남는 것으로 확인했다. 최종 `killed 143 of 144`, 1개 동치(위 증명).
  - 실제 ROM 차분(5 × 1,500, Unicorn 대 C++): 불일치 0. 첫 실행은 harness 세계 문제로 48..56건이 났다: native가 `8c16`(C++는 `animation_exit`에서 한 번에 처리하는 routed 잎)의 내부 분기 목표 `8c2a`에서 멈추던 것. harness(scratch)에서 `8c16 < pc <= 8ca6`를 내부로 취급해 해결. 남은 14건(5개 batch 합)은 모두 계산 표 점프 `b3dc8`·`b3fca`가 시작이 아닌 PC에 착지해 C++가 checked `unsupported animation objects fr1|u01|u19|n06 PC` 오류를 내는 것으로(결정 3의 문서화된 차이) harness가 분류로 센다. covered starts 212/213/214/214/214/213(batch별; 미착수 `de690`, `b3ed8`은 무작위 추첨 문제), 실제 소비자 비교 `b401e` `b9798` `b97b4` `5f5e6` 모두 batch마다 19..102회. DIVU 0 제수 native skip은 harness가 `no clean stop`으로 센다.
  - V1 `fr1` 두 번: 1,631 fixtures 모두 ok, 두 실행의 `[(name,digest)]` 같음, visited 214/214. 첫 실행의 실패 6건을 고쳤다(FR1 spec만): ① `first_unrouted`가 `8c16`의 분기 목표 `8c2a`에서 멈추던 것 → `8c16 < pc <= 8ca6`는 내부(`node-de660-0`, `node-de84c-1`), ② negative `negative-ram-block-b3f02-*`가 `7c(A6)`가 block에서 덮이는 RAM 비트 flip을 써서 차이가 안 났음 → RAM 오프셋 `f9f0` flip. 회귀 `b4` 1,830 / `b4b` 1,723 / `b3a` 1,468 모두 ok. U06 C++ 시험은 `make test`에 포함되어 통과.
  - **해결(메인, 2026-10-19): 기존 `b2a` V1 spec 회귀 4행** `spawn-5eed2-from-5ee20/5ee4e-s32/s33-n18`. 원인은 `spawn_fixtures`의 native `trace()` 정지 조건이 미연결 PC에만 멈추던 것이다. FR1a가 `4b6f4`를 연결하자 native가 `8e4a` 내부 PC `8e4c`까지 진행했고, C++는 그 PC에 멈출 수 없어 external read에서 끝났다. C++는 `8e4a`까지 native와 같았다(C++ 결함 아님). 정지 조건에 `4b6f4`(stop-only 경계)를 더해 고쳤다. b2a 1,386/1,386, fr1 1,631/1,631(`tools/unit_fixture_specs/b2a.py` `c57fe4e1…`). 같은 수정으로 `5f504` spawn 8행도 기준과 같은 `4b6f4` 정지로 돌아갔다.
  - area_clear 검증기(scratch `run_area_clear.py`): 통과, 종료 0, sha256 `07a70148...`, 행 `unrouted_neighbour_04b6f4`: 분류 `superseded_by_FR1_routes_4b6f4`, 오류 `program bus write requires RAM mirror units`, `former_expected_API_error` = `unsupported animation machine PC`.
  - frame 회귀: D1 · controller `--declare game` · IRQ 각 54,400/54,400, `--declare demo` 45,684/45,684(137 seeds), 자연 불일치 0, 기준(B4b) 로그와 시각을 뺀 줄이 같고(변한 frame 없음; report SHA만 `elapsed_seconds` 때문에 다름) 완료 frame 수 증가도 없다.
  - IO 비교 재실행(`verify_animation_machine_io.py`, scratch `ioA`): 불일치 0, 예상 밖 C++ 오류 0, 모든 acceptance true, 173,966 비교 중 첫 실패 전 일치 140,861 -> **146,957(+6,096)**. 구성별: P0 81,600 -> 81,600 (+0); P1 56,469 -> 60,968 (+4,499; frontier 실행 52 -> 46); P1b 2,511 -> 4,108 (+1,597; 13 -> 10); boot-demo-0 / boot-title-idle / boot-title-start 각 2 -> 2; fixtures 변화 없음. frontier 실행 69 -> 60. frontier.json SHA256 `ad4e7325d613863431df7122b8db1f523bd0fbb3b8acae22eb56f6090e033ea2`(scratch `ioA/frontier.json`). 새 frontier(실행 수 순, 모두 11개): `4e68e` 14, `c0ace` 12(`b3dbc` 처리기 표 `b3484`), `e5580` 12(`e5324` 자식), `515fc` 3(HUD 목록 형제), `5a376` 3, `b30f6` 3, `b97c0` 3(`b975e` 다음 block), `bc08c` 3, `d13b4` 3(`d131a` 자식), `de376` 2, `de024` 1(뒤 5개 중 `5a376` `b30f6` `bc08c` `de376` `de024`는 FR1b·FR1c 계획대로 유지). [I] `de660`의 `28ae` 자식 `de97e..`는 frontier에 나타나지 않고 `4e68e`가 그 자리를 차지한다(14 실행, 첫 frame 2..222).
- [U] 미확인은 위 "미확인" 절 그대로다.

## block 목록

[F] scratch `starts_a.txt`(SHA256 `b3fa4194da6fd2afdaf760e74decc00f98430d9b674444c0c1db47e279225b9a`)와 같다.

- **`ca42..ca48`(1)**: `ca42`
- **`4b6f4..4b702`(3)**: `4b6f4 4b6fc 4b700`
- **`4e0de..4e0f6`(1)**: `4e0de`
- **`4e146..4e166`(5)**: `4e146 4e152 4e158 4e162 4e164`
- **`515e0..515fc`(5)**: `515e0 515e2 515e8 515ec 515f8`
- **`51602..51608`(1)**: `51602`
- **`b3dbc..b3dfc`(9)**: `b3dbc b3dcc b3dd0 b3dd4 b3dd8 b3ddc b3de4 b3dec b3df4`
- **`b3ea2..b3eac`(1)**: `b3ea2`
- **`b3ec4..b3f40`(11)**: `b3ec4 b3ed8 b3ede b3ee6 b3eea b3efc b3f02 b3f22 b3f26 b3f2c b3f3a`
- **`b3f4c..b3f8c`(4)**: `b3f4c b3f50 b3f5c b3f68`
- **`b3fa4..b402a`(14)**: `b3fa4 b3faa b3fb2 b3fc6 b3fce b3fd2 b3fd6 b3ffe b400c b4012 b4018 b401e b4022 b4028`
- **`b7742..b7748`(1)**: `b7742`
- **`b975e..b97c0`(10)**: `b975e b9786 b978c b9792 b9798 b979c b97a8 b97b4 b97b8 b97be`
- **`d131a..d1348`(3)**: `d131a d1330 d1342`
- **`de660..de8bc`(50)**: `de660 de66e de674 de67a de686 de68e de690 de69a de6aa de6ba de6d0 de6e6 de6fc de712 de728 de738 de742 de754 de75c de75e de764 de772 de778 de782 de784 de78a de79a de7b0 de7c6 de7dc de7f2 de808 de814 de81a de82c de832 de838 de83a de840 de84c de854 de856 de864 de874 de880 de88a de898 de8a0 de8a2 de8ac`
- **`e5292..e5580`(76)**: `e5292 e529e e52a2 e52b2 e52c2 e52ca e52d6 e52e6 e52ea e52f6 e5304 e5308 e5314 e5318 e5324 e533c e534c e5350 e5358 e5364 e536c e536e e5372 e537e e5386 e5388 e5392 e539e e53a6 e53b2 e53bc e53c6 e53ca e53da e53e4 e53e8 e53ec e53fc e5400 e5418 e5424 e542c e542e e5432 e543e e5446 e5448 e5452 e545e e5466 e5472 e547c e5486 e548a e549a e54a4 e54a8 e54ac e54bc e54c0 e54d8 e54e4 e54ec e54ee e54f8 e54fc e550e e5518 e552c e5538 e5540 e5542 e5552 e5568 e5570 e5572`
- **`e56c0..e5724`(5)**: `e56c0 e56d0 e56e6 e56fe e5720`
- **`eb9ba..eba3e`(14)**: `eb9ba eb9c4 eb9ce eb9d6 eb9dc eb9e2 eb9e4 eb9ec eb9fa eba02 eba08 eba28 eba2e eba3c`
