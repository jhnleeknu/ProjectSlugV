# frontier 단위 FR2a(IO frontier `c0ace` `e5580` `b33d8` `a8ee`) 구현 계약과 FR2b 이후 명세

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. 범위는 FR1c 뒤 IO frontier(`4e68e` 14, `c0ace` 12, `e5580` 12, `50dae` `5ab82` `b33d8` `bc844` 각 3, `a8ee` 1, `1d1f4` 1)다. 전체 closure가 약 220 block을 크게 넘으므로(결정 1) 이 단위 FR2a는 바로 들어갈 수 있는 root를 실행 수 순으로 담고, 나머지는 끝 절 "FR2b 이후 명세"로 정확히 정한다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 코드와 고정 표는 모두 `<100000`이라 CPU 주소와 파일 오프셋이 같다. bank 창 읽기 `2001c4` `20017c`는 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `11be2b6`(branch `claude/frontier-units-2`, PR #7 head, FR1a/b/c routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `00ff3a1b8bfb89d7682bb48506ef39809ddd9062853335707385457b2cbd9fb4`(= FR1c IO 재실행 `frontier.json`의 `routing_file_sha256`).
- [F] frontier 입력: FR1c 뒤 IO 재실행 `/Users/start/Workspce/ms5-scratch/fr1c/ioA/frontier.json`(SHA256 `5042cf640a0bd53e699111093e3fcf607570ec8d6367dd08380add2bf306552d`; 첫 실패 전 일치 150,472, frontier run 53). 확정 frontier(모두 phase N, A7 = `1feffc`, 호출자 복귀 `2ac2`, `a8ee`만 A7 = `1feff0`·복귀 `a3c8`):
  - `c0ace`: P1 11 + P1b 1, frame 99, A6 = `1020f8`, LONG(A6) = `b3dbc`, A0 = `c0ace`(FR1a `b3dbc`의 `JMP (A0)` live 대상: 종류 기록 `b3484`의 처리기).
  - `e5580`: P1 11 + P1b 1, frame 245, A6 = `1013f4`/`10157c`, LONG(A6) = `e5580`(FR1a `e5324`의 `28ae` 자식 값 `e5542 MOVEA.L #e5580,A0`).
  - `b33d8`: P1 2 + P1b 1, frame 120, A6 = `101f70`, LONG(A6) = `b33d8`(FR1b `b31c0 MOVEA.L #b33d8,A0`의 자식).
  - `a8ee`: boot-title-start 1(+ fixture fx-start-c79a), frame 113, A6 = `100f5c`, LONG(A6) = `b344`, 복귀 LONG `a3c8`(card menu 표의 LONG `a900`/`a95a` = `a8ee`, routing된 메뉴 코드의 `JSR (An)` live 대상).
  - `4e68e` 14(frame 2·222), `50dae` 3, `5ab82` 3, `bc844` 3, `1d1f4` 1: FR2b 이후(끝 절).
- [F] IO 관측의 frame 시작 상태(`artifacts/animation_machine_io_native/states/P1/000.pack.gz`, 읽기 전용, scratch `io/node_at.py`)로 확인한 `c0ace` node `1020f8`: frame 99 LONG(A6) = `b3dbc`, WORD `76` = `32`; frame 100..159 LONG(A6) = `c0b52`(이 단위의 설치 값), WORD `8a` = `32`(아이템 기록 index), WORD `90` = `8`(표 `b433c`의 index 2 = `b437a`), 이후 node가 해제(`270e`)된다. 아이템 기록 `32`(`b3894 + 12·32` = `08000032 000b445e 00002000`)의 처리기 LONG 4는 `b445e`다. 같은 run의 RAM 목록 `10dd48`/`10dd50` WORD는 `8000`, `10dd5c..` 목록은 비었다(frame 99..160).
- [F] 정적 디코드: capstone M68000, FR1·FR1c 계약과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, DBcc 대상, `MOVE.L #imm,(A6)` 설치 값, 범위 밖에서 들어오는 실제 JSR/BSR/JMP/BRA 대상). routing된 PC, `RTS`, `TRAP`, `JMP`/`JSR (An)`(live 대상)에서 멈춘다. `28ae`/`2986` 자식 값은 기록만 한다. 연속 Bcc는 한 block으로 묶는다(`e6534`).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr2/`
  - `tools/`: FR1c scratch의 `hroute.py` `fclos.py` `unit_fr1.py` `refs.py` `xref.py` `longref.py` `callers.py` `leafscan.py` `disr.py`를 경로만 바꿔 복사(`unit_fr1.py`는 환경 변수 `FR2G`로 묶음 지정, `hroute.py`는 `EXTRA_ROUTED`로 가상 routing 범위 추가, `fclos.py`는 설치 값 추적 끄기 옵션), 새 `overlap.py`(root closure 겹침), `cread.py`(호출 뒤 C를 읽는 호출 지점 전수), `split4e.py`(`4e68e` 분할), `specs.py`(FR2b 이후 명세), `player.py`(`1d1f4` 요약), `io/node_at.py` `io/ram_at.py`(IO 상태 읽기).
  - `starts_a.txt`(FR2a 시작 218개) SHA256 `1407bd08e2148fce51fa1dba8b962fa7b3da2747214d6e9a8ae10215d334fe99`; `unit_a.out`(block별·범위 전체 디코드), `xref_a.out` `longref_a.out` `callers_a.out`, `starts_fr2b.txt` … `starts_fr2h.txt`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **frontier closure 크기(현재 routing, 같은 규칙):** `4e68e` 512(설치 값 7개 포함), `c0ace` 134, `e5580` 45(묶음 1), `50dae` 211, `5ab82` 202, `b33d8` 12, `bc844` 66, `a8ee` 12(+ 결정 8의 `a772` = 13), `1d1f4` 1,614(점프 표 미전사) — 합 약 2,800으로 한 단위(약 220)를 크게 넘는다. 겹침은 `4e68e`∩`e5580` 28 block(`e63ec..e65dc` 순위 표 helper)뿐이다(scratch `overlap.py`). IO 표의 root `c01a8`·`e4ffc`·`b3246`·`5ab6c`·`a75a`는 "PC 아래 가장 가까운 호출 대상" 규칙의 값이고, 실제 진입은 위 확정 frontier PC다([F] `e4ffc`는 FR1 계약대로 ASCII 자료, `b3246` `a75a`는 이미 routing된 PC).
- [F] **FR2a(결정 1)** = 실행 수가 큰 root 중 한 단위에 들어가는 것: `c0ace` 묶음 148 + `e5580` 45 + `b33d8` 12 + `a8ee` 13 = **218 block**, 27 범위, 명령 588, 짝수 PC 1,062(내부 844), 이어 붙인 바이트 2,124, SHA256 `a52ec2aeee7bda535ca3bfe3a8126efab98212b4d1c600fee29ad136a4eff648`. 겹침 0. frontier run 53 중 28(12 + 12 + 3 + 1)의 첫 정지 PC를 연결한다.
  - `c0ace` 묶음 = `c0ace` closure 134(`b4958` 공용 아이템 갱신·`1c8a4`·`e62a8` 점수 BCD 덧셈·`e991c`/`e9b5a` 점수 표시 자식 생성 포함) + 표 `b433c`의 처리기 `b4354` `b437a` 13(`b4aca` 공유, 결정 2) + 아이템 기록 처리기 `b445e` 1(결정 2).
  - `4e68e`(14 run)는 FR2a 뒤에도 484 block이라 세 단위(FR2b 157 / FR2c 167 / FR2d 160)로 나눈다. 각 단위만으로는 IO 진척이 없고 셋이 모두 들어가야 14 run이 frame 2·222를 넘는다(끝 절, 결정 1).

| root(진입) | block | 명령 | 범위 |
| --- | --- | --- | --- |
| `c0ace`(+ `b4354` `b437a` `b445e`) | 148 | 398 | `1c1f4..1c238` `1c8a4..1c8f0` `b4334..b433c` `b4354..b43de` `b442e..b4464` `b4664..b466c` `b4680..b46be` `b46c0..b46f6` `b4760..b4806` `b489e..b4a24` `b4ab0..b4ab6` `b4aca..b4ad4` `c0ace..c0ba8` `c1d2e..c1d34` `e62a8..e62ec` `e991c..e995c` `e9b5a..e9b8a` |
| `e5580` | 45 | 103 | `e5580..e5614` `e63ec..e63fa` `e6516..e6570` `e6582..e65dc` `e693a..e6952` |
| `b33d8` | 12 | 28 | `b33d8..b3460` |
| `a8ee`(+ `a772`) | 13 | 59 | `9ee6..9ef2` `9ef8..9f24` `a770..a7e0` `a8ee..a8f8` |
| 합 | **218** | 588 | 27 범위 |

## 요약

- [F] **범위·block 수**(27 범위, 합 218):

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `9ee6..9ef2` | 12 | `7fa4e7d37e5f95a33e1c512b3ab1864f435491064ef078f435e22b83087a1b6a` | 1 | 6 |
| `9ef8..9f24` | 44 | `43f682bfdc484a82d608551e2020f7e4d7dcbf8986553c06a0cbdbfe91baa432` | 2 | 22 |
| `a770..a7e0` | 112 | `db53770434868bedca14a3619f61c715ad38a7531f094af6ff2156fb448d6e20` | 9 | 56 |
| `a8ee..a8f8` | 10 | `83e63a9c50b841607abcef65b0d241a06b3830c549211a9aaef66bd1e1e42463` | 1 | 5 |
| `1c1f4..1c238` | 68 | `ede514518f3115e79a229f3c2f494e85caaab09d7a41e0a0b3f8d2d8199ea32d` | 3 | 34 |
| `1c8a4..1c8f0` | 76 | `c30ca2bbd8d809dc3a3dcf6bf0d4c755413135090d7590a02c7a34242725c174` | 8 | 38 |
| `b33d8..b3460` | 136 | `69de968382feeabc5f35d790cb9d8fca0100f459656683dde8f3be7a1827f70f` | 12 | 68 |
| `b4334..b433c` | 8 | `b87a6a8c7aa8ed158e8635feaae215bced53e80327c2f4a6918c17303af82356` | 2 | 4 |
| `b4354..b43de` | 138 | `c3218b4c2ea2c85b1ceec6d3d22fe33c19070e707f554f0a408c2349eab7ac58` | 13 | 69 |
| `b442e..b4464` | 54 | `8cb6f4a38693530dda826286546066391b59c1f091cd995fe4e1f072950bcec0` | 8 | 27 |
| `b4664..b466c` | 8 | `f0619b0a961787f19aff9d8f9bfdd766152651f03b3669cf2f1f60f6e91ed941` | 1 | 4 |
| `b4680..b46be` | 62 | `19603ebfc6e9f71e164422ffac008e94d755455ca3858de81dd5439e74f7c0e3` | 7 | 31 |
| `b46c0..b46f6` | 54 | `49eefbf38193a1c60d2c902118865df11f1defa65de1fd03c8b6d15b46d66fe7` | 3 | 27 |
| `b4760..b4806` | 166 | `ce08fe3663000781f6ee7ef6552e2c8449e42eed800be00d2a934305caa638d5` | 23 | 83 |
| `b489e..b4a24` | 390 | `e66b69f75904ff2599a0bfafc9de94a0d6802457d88c2c39ec4ee0613bf69384` | 42 | 195 |
| `b4ab0..b4ab6` | 6 | `ab21bab99f032078f0fb20a9f0a4003e903a58b307047697d96242d2f1a95d9e` | 1 | 3 |
| `b4aca..b4ad4` | 10 | `b78ab0f27ba457bee107fc12df3f97cedb3dc2d0ba7851feb5592846425ff694` | 1 | 5 |
| `c0ace..c0ba8` | 218 | `a084f7e5d1db37a08729de9232338a8d44e964419c84aa741b8e6a00686a804b` | 18 | 109 |
| `c1d2e..c1d34` | 6 | `2738adf81304c5fbbc9eedf6248d6b2d7cfa132bc35dfb5e458d0bbd9e12d3f9` | 1 | 3 |
| `e5580..e5614` | 148 | `b11b8ca6589f314769a6ea76cd95bef8f14fbbc54686e611b2220fc990241f95` | 16 | 74 |
| `e62a8..e62ec` | 68 | `424366e0a0b56156a72a373ce7a8a7dfabecc39f9c69eb71f6a593b53212b6d4` | 8 | 34 |
| `e63ec..e63fa` | 14 | `59c4b30fdfa8de48a685980213acc3dbb1fcd703fdbbb0060daed67fcb356747` | 3 | 7 |
| `e6516..e6570` | 90 | `d69e9e3c10d15ea40ff486bcffea8ce56dcf278875822691f595ff54505961ed` | 12 | 45 |
| `e6582..e65dc` | 90 | `99736a7a097d9036e5cf0fa06709ddbee9a7fdfaa38b340af5a8c54f5213e9f3` | 12 | 45 |
| `e693a..e6952` | 24 | `2d77b6de35ca920c902b36337ac01438f3613424ed79af8232ecff497b0cb92d` | 2 | 12 |
| `e991c..e995c` | 64 | `74959b3dd8b93da1b7c894879727767cbacd1d54b85747e6e95a9e8e785cbca0` | 7 | 32 |
| `e9b5a..e9b8a` | 48 | `2ae9e00c74824e91c297c70159b2a680c62f325fe0d38d18f9468d5151695973` | 2 | 24 |
| 합계 FR2a | 2124 | 이어 붙인 바이트 `a52ec2aeee7bda535ca3bfe3a8126efab98212b4d1c600fee29ad136a4eff648` | **218** | 1062(내부 844) |

- [F] closure가 27 범위를 빈틈없이 덮는다(도달하지 않는 명령 0; `b46be..b46c0` `b4ab6..b4aca` 등 범위 사이 바이트는 자료·다른 함수). 연속 Bcc 묶음 1(`e652e BHI.W e6552; BCS.W e6540`). DBcc 2(`e63f4` `e9952`). X 소비는 `e62ce`의 `ABCD` 4개뿐(X는 같은 block의 `ADDI.B #0,D0`가 0으로 만듦, 결정 3). `DIVU.W` 1(`a7ac`, 결정 7). `MULU.W` 7(`1c1f4` 두 번, `b4680`, `e659a`, `e65c2`; 모두 무부호 16 × 16 → 32 bit). `Scc` 3(`9ee6 SEQ`, `b496c`/`b498a SCS`). 계산 점프(`JMP (d,PC,Dn)`)는 없다. live 대상 `JSR (A1)` 5곳(결정 2). `TRAP #15` 경계 2곳(`b466c` `e6570`, 범위 밖, 결정 6). I/O port·bank 쓰기 없음.
- [F] **현재 routing과의 관계**: 27 범위의 짝수 PC는 모두 routing 밖이다(겹침 0). 경계 이웃 중 routing된 것: `9ee4`(앞 단위 `RTS`), `a76e`(card menu `RTS`), `b4806`(routing된 다른 block), `b4a24`, `b4aae`, `e557e`(FR1 `e5292..e5580` 끝)·`e5614`, `e62ec`(routing된 `e62ec`), `e6938`. 그 밖은 routing 밖 자료·형제 코드(`b433c..b4354` LONG 표, `b4ad4..b4aec` LONG 표, `b46f6..b4706` WORD 표, `1c1c0..1c1f4` BYTE 표, `1c238..` BYTE 표, `b466c` `e6570` TRAP 문자열).
- [F] **나가는 곳은 모두 routing돼 있다**(각 실행부의 `case` block 시작): callee `288c` `289e` `28ae` `2986` `3af8` `1aa3a` `43e34` `43ea4` `49290` `49a58` `49f8c` `49fc6` `c6a96`, 출구 `JMP 2a00`(`b3448` `b3458` `b4a06` `b4a1c` `c1d2e` `e5606`), `JMP 1aa7e`(`b4764`), `JMP 49260`(`b46dc`), `JMP cd58`(`a7c2`). `scratch leafscan.py`: 이 출구들 안에서 routing 밖 분기 대상은 없다. live 대상(결정 2)과 TRAP 2곳(결정 6)만 routing 밖이다.
- [F] **참조**(ROM 전체 직접 분기·LONG 상수, scratch `xref_a.out` `longref_a.out` `callers_a.out`): 범위 밖에서 들어오는 실제 분기·설치·LONG은 모두 block 시작이다 — `a770`(`a8f4` `aa70` `abf8` `aeb2` `afa2` `b244`… `BRA.W`), `a772`(`aca4 BRA.W`, 결정 8), `9f12`(`973a JSR`), `1c1f4`(`1c458` `1cefe BSR`, `1c91e`… `JMP`), `b4334`(`bfcf2`… 38곳 `JSR`), `b4388`(`b43f0` `b4408 JSR`), `b442e`(`b4428` `b44a2 JSR`), `b4958` `b4ab0`(각 34곳 `JSR`), `b4aca`(`b4080 JSR`), `c1d2e`(`c00a0`… `BNE.W`), `e62a8`(`e3de2` `e492a` `e9902` `e9b04 JSR`), `e63ec`(`e6442` `e6488` `e6992` `e6b74 JSR`), `e6556`(`4edec JSR`), `e9b5a`(`e995e` `e9aa6 JSR`), `e9b72`(`e9b56 BRA.W`); 설치·LONG: `c0ace`(종류 기록 `b367c` LONG 6), `b4354`/`b437a`(표 `b433c`), `b445e`(아이템 기록 LONG 4, 81곳), `a8ee`(`a900` `a95a`), `b33d8`(FR1b `b31c0`), `e5580`(FR1a `e5542`), `1c8a4`(`b469a`). 내부 PC로 보이는 분기·LONG(`1c21c` ← `1c1b8`, `c0b50` ← `c0bb8`, `e55e8` ← `e55ac`, `e6526` ← `e14b2`, 홀수 대상들, LONG `b343c` `b4800` `c0b00`과 1 MiB 밖의 값)은 명령 중간·ASCII 자료의 우연한 바이트다 [F](각 위치 디코드: `1c1b6 BRA.W 2291a`의 확장 word, `c0bb4 JSR c6a96.l` 안, `e55a8 JSR e693a.l` 안, `e14a0..` 문자열, `6f85e MOVE.W #b,D1; MOVE.W #343c…`).
- [I] 의미: `c0ace`는 FR1a 아이템 객체 `b3dbc`의 종류 처리기 하나다 — 난수(`49a58`)로 LONG `36`/`3a` 초기 속도, 소리 `1836`, `c6a96`, bank 창 `2001c4` 애니메이션, 설치 `c0b52`(이동 `43ea4`, LONG 속도 감쇠 `ASR.L #4`, 공용 아이템 갱신 `b4958`, 시간 초과·화면 밖이면 삭제). `b4958`은 아이템 공용 루틴(깜빡임 BYTE `12`/`13`, 플레이어와의 접촉 판정 `b489e`(RAM 목록 `5d5c(A5)`/`5d98(A5)`, `289e`, 표 `b433c`의 판정기)·`b476a`(플레이어 기록 `10dd48`/`10dd50`), 접촉 시 아이템 기록 `b3894`의 처리기 호출 → `b442e` 점수 BCD 가산 `e62a8`(`10de18`/`10de20`)·점수 표시 자식 `e9b8a`(`2986`)·`b46c0`(`49260`)·소리 `1acf`, 수명 WORD `8c`, 화면 판정 `1aa7e`). `e5580`은 결과 화면(`e5324`)의 순위 입력 객체다 — WORD `80` < `a`이면 `28ae` 자식 `e6952`(이름 입력) 생성, 점수(`10de14`/`10de1c`)를 순위 표 `10f02e`(8 byte × 10)에 끼워 넣는 `e6556`(`e6516` 순위 찾기, `e65b0` 아래로 밀기, `e63ec` byte 복사). `b33d8`은 FR1b `b30f6` 계열의 연출 자식(bank 창 `20017c` 애니메이션, 부모 BYTE `61` bit 7·`288c`로 삭제). `a8ee`는 card menu 항목의 그리기 처리기(D7 = `d22b`로 `a770` 공용 그리기, `9ee6` `9f12` `9ef8`로 메뉴 기록 `-ee(A5)`의 좌표·크기, `DIVU`로 비율, `cd58` sprite). 이름은 확정하지 않는다.

## 공통 규칙·native 검증 계획

FR1 계약 "공통 규칙·native 검증 계획"과 FR1c 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr2.cpp`, 함수 `animation_objects_fr2_block`. 오류 문자열은 `unsupported animation objects fr2 PC`(범위 안 내부 PC 직접 진입), `objects fr2 caller requires known carry`(C 소비 block에 Unknown C; 소비자 7개), `objects fr2 DIVU zero divisor`(`a7ac`, 결정 7)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(27 범위, FR1c 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(9개, 결정 5), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, test 목록 실행 줄, 시험 target; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** routing 밖 실행 PC는 live 대상(결정 2)과 TRAP 2곳(결정 6)뿐이다. 기존 시험이 stop으로만 보던 PC(`c0ace`(FR1a 처리기 값), `e5580`(FR1a 자식 값), `b33d8`(FR1b 자식 값))는 stop 판정이 routing보다 먼저라 그대로 통과한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다(F4 관례). dispatcher 오류 확인에 쓰는 범위 옆 PC는 자료·TRAP PC(`b433c` `b4ad4` `b46f6` `1c238` `b466c` `e6570`)뿐이다; 다른 단위·다음 frontier가 routing할 코드(`bc844` `e6952` `e9b8a` `b44ac` …)는 탐침으로 쓰지 않는다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1, FR1c 교훈): 기대 오류 fixture마다 실패 PC를 적고, 진입 PC와 다르면 같은 상태를 stop = 실패 PC로 실행해 정확히 그 PC에서 멈추는지 확인한다. 행의 run stop은 실패 block 바로 뒤 PC로 둬서(행마다 `stop` 지정) 실패를 건너뛴 변이가 같은 오류를 내지 못하게 한다.
- **자료 읽기**(live bus, F1 결정 3, 상한 검사 없음): BYTE `(1c1c4 + sext(D1.W))` `(1c1c0 + sext(D1.W))` `(1c238 + sext(D0.W))`(`1c1f4`), 아이템 기록 BYTE `1(b3894 + sext(WORD(12·D1.W)))`·LONG `4(…)`(`b4680` `b46a2`)·LONG `8(…)` 이하 BCD BYTE(`b442e` `b4440` `e62ce`), LONG `(b433c + sext(WORD 90(A6)))`(`b4780` `b47a4` `b48ec`), LONG `(b4ad4 + sext(WORD 90(A6)))`(`b4aca`), WORD `(b46f6 + sext(2·(D1.W & 7)))`(`b46c0`), bank 창 LONG `2001c4`·`14(…)`(`c0b24`), `20017c`·`8(…)`(`b3400`), 판정기 `b4354`/`b4388`의 `(A0)+`·`(A1)+`(RAM 목록 또는 `b4ad4`가 가리키는 기록). RAM 읽기: node field(A6), 부모 LONG `c(A6)`의 BYTE `61`/`62`, 플레이어 기록 `100cb8`/`100da8`(`1c8ba` `b46c0`), `-ee(A5)` `-f2(A5)`(= `107f12` `107f0e`, 메뉴 기록 포인터), `-7ff2(A5)`(= WORD `10000e`), `5d48(A5)` `5d50(A5)` `5d5c(A5)` `5d98(A5)` `5dd4(A5)` `538e(A5)` `5e4a(A5)`, `10dd48`/`10dd50`, `10de14..10de24`, 순위 표 `10f02e..10f07e`. 단위 시험은 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다, 코드 바이트와 겹치지 않는 자료 영역만). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `MOVE.W Dn,-(A7)`/`(A7)+`(`1c8a4`/`1c8ac` `b4436`/`b4440` `b489e`/`b494c`/`b4950` `e693a`/`e694c` `e9b5a`/`e9b72` `a788`/`a7c2`), `MOVE.L` push/pop(`a772`/`a788` `a788` `a796`/`a7c2` `b437a`/`b4380` `b48ec`/`b491a` `e6556`/`e655c` `e991c`/`e9922`), `MOVEM.L d0/a0`(`b4694`/`b469e` `b46a2`/`b46ac`: `(A7)` = D0, `4(A7)` = A0), `MOVEM.L a1/a6`(`b4922`/`b4936`: `(A7)` = A1, `4(A7)` = A6), `MOVEM.L d0-d1/a0`(`e6584`/`e658c`: `(A7)` = D0, `4` = D1, `8` = A0), `MOVEM.L (a7)+,a1`(`b491a`), JSR/BSR 복귀 LONG. 모두 `am_push`/`am_pop`(홀수 A7은 checked 오류). `a7c2`는 `a788`이 넣은 LONG D0을 WORD 두 번(상위 → 하위)으로, WORD D1을 마지막에 꺼낸다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B` `ADD.W/.B` `SUB.W` `NEG.W` `ADDQ.W/.B` `SUBQ.W/.B` `ANDI.W/.B` `ORI.W/.B` `EOR` 없음, `LSL.W #3` `LSR.B #6` `LSL.B #3`). `MOVEQ`는 LONG 전체(부호 확장). `ADDI.L` `ADD.L`/`NEG.L` 메모리 LONG, `ASR.L #4`(32 bit 산술: 부호 bit 복제, 명시 구현), `LSL.L #8`, `ROL.L #4`, `SWAP`, `ANDI.L #ffff`, `MULU.W`(무부호 16 × 16 → 32 bit 대상 전체), `DIVU.W`(결정 7), `ADDA.W`/`SUBA.W`(원본 WORD의 부호 확장 뒤 32 bit 더하기), `ADDQ.W #4,A0`(주소 레지스터 32 bit), `ABCD`(결정 3), `ADD.B` + `SCS.B`(같은 block의 BYTE 올림 C), `BSET.B #3,61(A6)` + `BEQ`(옛 bit의 Z), `TST.B`/`TST.W`/`TST.L` + `BNE`/`BEQ`/`BPL`, `CMPI.W #a/#6e/#80/#780`·`CMPI.B #3/#ff`·`CMPI.L #20000/#50000`·`CMP.W`/`CMP.L`/`CMP.B`/`CMPA.L`(무부호 `BCS`/`BCC`/`BLS`/`BHI`, 부호 `BLE`/`BGE`, `BEQ`/`BNE`), `SUBQ.B #1,D6` + `BGE`(옛 BYTE 부호값 ≥ 1), `SUBQ.W #1,D1` + `BPL`(새 WORD N), `SUBQ.W #1,D0` + `BCS`(옛 WORD = 0), `SUBQ.W #1,7a(A6)` + `BEQ`, `DBRA`(하위 WORD −1, `ffff`가 아니면 반복), `BTST #n,Dn`(Dn: LONG bit n mod 32), `BTST.B #n,d(An)`. 같은 block 안에서 만들고 소비한다(예외: 결정 4의 재계산, 결정 5의 C).

## carry

- [F] **소비 block 7개**(callee가 돌려준 C):
  - `b3454 BCS.W b345e`: `288c`(stage_event_ops `2898 ORI` Set, `289e`(readiness) `28a8 ORI` Set / `28ac` Clear). Set → `b345e RTS`, Clear → `b3458 JMP 2a00`.
  - `b46ac MOVEM.L (A7)+,D0/A0; BCS.W b46bc`: 아이템 기록 LONG 4의 처리기(`JSR (A1)` live 대상; 이 단위 `b445e ANDI` Clear, 다른 처리기는 FR2h). Set → `b46bc`, Clear → `b46b4`.
  - `b478e BCC.W b4796` / `b47b2 BCC.W b47ba` / `b491a MOVEM.L (A7)+,A1; BCC.W b4942`: 표 `b433c`의 판정기(`JSR (A1)`; 이 단위 `b4374`/`b43d2 ORI` Set, `b43d8 ANDI` Clear). Clear → `b4796`/`b47ba`/`b4942`, Set → `b4792`/`b47b6`/`b4922`.
  - `b48e8 BCC.W b4942`: `289e`(readiness). Clear → `b4942`, Set → `b48ec`.
  - `b4a18 BCC.W b4a22`: `b4760`(`JSR b4aca; JMP 1aa7e`)가 꼬리 호출한 U01 `1aa7e`(`1aaf6 ANDI` Clear, `1aafc ORI` Set). Clear → `b4a22 RTS`, Set → `b4a1c JMP 2a00`.
- [F] **C를 넘기는 `RTS` 2개**(결정 5):
  - `b433a RTS`: `b4334 JSR 49fc6`의 interpreter known C를 그대로 돌려준다. [F] `b4334`의 호출자 38곳 중 11곳이 복귀 직후 `BCC.W`로 읽는다(`c00a4` `c01c2` `c08fe` `c0cce` `c0df6` `c1c06` `c1c7c` `c1ce0` `d906a` `d90ae` `d9416`, 모두 routing 밖의 다른 아이템 처리기; scratch `cread.py`). FR1a `4b700` 관례.
  - `1c230 RTS`: `1c1f4`의 `CMP.B D0,D1; BNE.W 1c232`가 떨어진 쪽(같음)이라 C = 0(빌림 없음)이다. `1c1f4`가 그 C(Clear)를 known으로 남기고 `1c230`이 돌려준다. [F] `1c1f4`의 호출자 중 `1cefe BSR.W 1c1f4; BCC.W`(routing 밖, `1d1f4` 플레이어 closure)가 읽는다.
- [F] **known C 생산**: `1c1f4`(CMP.B의 빌림 = 무부호 D1.B < D0.B; 같으면 Clear), `1c232` `b4374` `b43d2` `b4458`(`ORI.B #1,CCR; RTS` Set), `b43d8` `b445e`(`ANDI.B #fe,CCR; RTS` Clear). 그 밖의 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다.
- [F] **읽는 곳이 없는 known C**(carry 보존 목록에 넣지 않음, FR1c 결정 5 관례): `b4434 RTS`(`TST.L` Clear) `b46bc` `b494c`/`b4950`(`MOVE`가 지움) `b47ea`/`b47f8`/`b47fe` `1c8b8`/`1c8ee` `b4a22` `e62ea` `e654c` `e6552` — 각 함수의 직접 호출자(ROM 전체)가 복귀 뒤 C를 읽지 않는다(`cread.py`: `b442e` `b4958` `b4ab0` `b476a` `b489e` `1c8a4` `e62a8` `e6516` `e6556` 호출자 C 읽기 0).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 9개다: 소비자 `b3454` `b46ac` `b478e` `b47b2` `b48e8` `b491a` `b4a18`, 통과 `RTS` `b433a` `1c230`. Unknown C로 소비자에 들어오면 checked 오류다(통과 `RTS`는 Unknown을 그대로 돌려준다).
- [F] **flag 재계산(결정 4)**: `b47f4 BCC.W b47fe`는 유일 선행 `b47de`(`CMP.W D0,D1; BNE.W b47f4`)의 C를 쓴다 → C = 무부호 D1.W < D0.W(레지스터 그대로). `b48ba BEQ.W b494c`는 선행 둘(`b48b8 TST.W (A1)` fall-through, `b4942 ADDA.W #a,A1; TST.W (A1); BRA.W b48ba`)이 모두 같은 A1로 `TST.W (A1)`를 했으므로 Z = (WORD `(A1)` = 0)을 RAM에서 다시 읽어 계산한다. 그 밖에 block 경계를 건너 다시 계산하는 flag는 없다.

## 객체 `c0ace`와 아이템 공용 루틴

공통 꼴 "bank 애니메이션 `anim(n, w, d)`" = `LEA 26(A6),A0; MOVE.W #n,20(A6); MOVE.L w.l,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1; JSR 49f8c.l`.

- **`c0ace`**(종류 처리기, `b3dbc`의 `JMP (A0)`): D0 := 0, `JSR 49a58`(복귀 `c0ad6`). **`c0ad6`** `c0aec`: D0.W &= `7fff`, D0 += `10000`(LONG), LONG `36`/`3a` := D0; `c0ad6`은 D0 := 0, `JSR 49a58`(복귀 `c0aec`), `c0aec`은 D0.W := `1836`, `JSR 3af8`(복귀 `c0b04`).
- **`c0b04`**: BYTE `15` bit 0 ≠ 0 → `c0b12`, 아니면 `c0b0e`: LONG `36` := −LONG `36`(fall-through `c0b12`).
- **`c0b12`**: D0.W := `70`, D1.W := 5, D2.B := 0, `JSR c6a96`(복귀 `c0b24`). **`c0b24`**: anim(`1eb`, `2001c4`, `14`)(복귀 `c0b4c`). **`c0b4c`**: 설치 `c0b52`.
- **`c0b52`**(설치 값): `JSR 43ea4`(복귀 `c0b58`). **`c0b58`**: 부호 LONG `3a` ≥ `20000` → `c0b6e`, 아니면 `c0b64`: LONG `3a` += LONG `3a` ASR 4(fall-through `c0b6e`).
- **`c0b6e`**: D0 := LONG `36` + `28000`, 무부호 D0 ≥ `50000` → `c0b8c`, 아니면 `c0b82`: D0 := LONG `36`, LONG `36` += D0 ASR 4(D0 = 그 값, fall-through `c0b8c`).
- **`c0b8c`**: `JSR b4958`(복귀 `c0b92`). **`c0b92`**: `JSR b4ab0`(복귀 `c0b98`). **`c0b98`**: D0 bit 2 ≠ 0 → `c1d2e`(`JMP 2a00`), 아니면 `c0ba0`: `JSR b4334`(복귀 `c0ba6 RTS`).
- **`b4334`**: `JSR 49fc6`(복귀 `b433a`). **`b433a`**: `RTS`(C 통과, 결정 5). **`b4ab0`**: D0.B := BYTE `96`, `RTS`. **`b4aca`**: D0.W := WORD `90`, A0 := LONG `(b4ad4 + sext(D0.W))`, `RTS`.
- **`b4958`**: BYTE `95` bit 3 ≠ 0 → `b499e`, 아니면 `b4962`: BYTE `12` = `ff` → `b4980`, 아니면 `b496c`: D0.B := (BYTE `12` LSR 6) + 1, D0.B := D0.B LSL 3, BYTE `12` += D0.B(C = BYTE 올림), D0.B := C ? `ff` : 0, BYTE `12` |= D0.B(fall-through `b4980`). **`b4980`** **`b498a`**: BYTE `13`에 같은 일(→ `b499e`).
- **`b499e`**: BYTE `96` bit 2 ≠ 0 → `b49e4`, 아니면 `b49a8`: BYTE `94` = 0 → `b49b8`, 아니면 `b49b0`: BYTE `94` −= 1, `BRA b49e4`.
- **`b49b8`**: D7 := 0, `JSR b489e`(복귀 `b49be`). **`b49be`**: `JSR b476a`(복귀 `b49c2`). **`b49c2`**: D7.B = 0 → `b49e4`, 아니면 `b49c8`: D7.B |= 4, BYTE `96` |= D7.B, D0.B := D7.B, D0.W &= 3, 0 → `b49e4`, 아니면 `b49da`: D0.W −= 1, D1.W := WORD `8a`, `BRA b4664`.
- **`b49e4`**: D0.W := WORD `8c`, 0 → `b4a14`, 아니면 `b49ec`: D0.W −= 1, ≠ 0 → `b4a10`, 아니면 `b49f2`: BYTE `95` bit 4 ≠ 0 → `b4a10`, 아니면 `b49fc`: BYTE `61` bit 3 := 1, 옛 bit 0 → `b4a0c`(D0.W := `24`, fall-through `b4a10`), 아니면 `b4a06 JMP 2a00`. **`b4a10`**: WORD `8c` := D0.W(fall-through `b4a14`).
- **`b4a14`**: `JSR b4760`(복귀 `b4a18`). **`b4a18`**(소비자): Clear → `b4a22 RTS`, Set → `b4a1c JMP 2a00`. **`b4760`**: `JSR b4aca`(복귀 `b4764`). **`b4764`**: `JMP 1aa7e`.
- **`b4664`**: 무부호 D1.W < `6e` → `b4680`, 아니면 `b466c`(TRAP #15 경계, 결정 6). **`b4680`**: D1 := D1.W × `c`, A0 := `b3894` + sext(D1.W), BYTE `1(A0)` bit 0 = 0 → `b46a2`, 아니면 `b4694`: push A0, push D0(`MOVEM.L d0/a0,-(a7)`), `JSR 1c8a4`(복귀 `b469e`). **`b469e`**: pop D0, pop A0(fall-through `b46a2`).
- **`b46a2`**: A1 := LONG `4(A0)`, push A0, push D0, `JSR (A1)`(복귀 `b46ac`, live 대상). **`b46ac`**(소비자): pop D0, pop A0; Set → `b46bc RTS`, Clear → `b46b4`: A0 += 8, `JSR b442e`(복귀 `b46bc`).
- **`b442e`**: LONG `(A0)`의 N = 0 → `b4436`, 아니면 `b4434 RTS`. **`b4436`**: push WORD D0, D0.W += 1, `JSR e62a8`(복귀 `b4440`). **`b4440`**: D0.W := pop WORD, D1 := LONG `(A0)`, `JSR e991c`(복귀 `b444a`). **`b444a`**: `JSR b46c0`(복귀 `b444e`). **`b444e`**: D0.W := `1acf`, `JSR 3af8`(복귀 `b4458`). **`b4458`**: C Set, `RTS`. **`b445e`**: C Clear, `RTS`.
- **`b46c0`**: D1.W &= 7, D1.W += D1.W, D1.W := WORD `(b46f6 + sext(D1.W))`, A1 := `100cb8`, D0.B = 0 → `b46dc`, 아니면 `b46d6`: A1 := `100da8`(fall-through `b46dc`). **`b46dc`**: D0.W := WORD `42(A1)`, D1.W += WORD `46(A1)`, A1 := A5 + `538e`, D0.W −= WORD `1c(A1)`, D1.W −= WORD `20(A1)`, `JMP 49260`.
- **`b476a`**: D7 bit 2 ≠ 0 → `b4804 RTS`, 아니면 `b4772`: A0 := `10dd48`, WORD `(A0)` = `8000` → `b4796`, 아니면 `b4780`: A1 := LONG `(b433c + sext(WORD 90))`(D0.W := WORD `90`), `JSR (A1)`(복귀 `b478e`). **`b478e`**(소비자): Clear → `b4796`, Set → `b4792`: D7.B |= 1(fall-through `b4796`).
- **`b4796`** `b47a4` **`b47b2`**(소비자) `b47b6`: `10dd50`과 D7.B |= 2로 같은 꼴(→ `b47ba`). **`b47ba`**: D7.B ≠ 3 → `b4804`, 아니면 `b47c2`: D0.W := WORD `5d48(A5)` − WORD `42`, N = 0 → `b47d0`, 아니면 `b47ce`: D0.W := −D0.W. **`b47d0`** `b47dc`: D1.W := |WORD `5d50(A5)` − WORD `42`|(같은 꼴). **`b47de`**: D1.W ≠ D0.W → `b47f4`, 아니면 `b47e4`: `JSR 49a58`(복귀 `b47ea`: D0.B := (D0.B & 1) + 1, D7.B := D0.B, `RTS`).
- **`b47f4`**(결정 4): 무부호 D1.W < D0.W → `b47f8`(D7.B := 2, `RTS`), 아니면 `b47fe`(D7.B := 1, `RTS`).
- **`b489e`**: push WORD D7, D0.W := WORD `10000e`(= `-7ff2(A5)`) & 1, ≠ 0 → `b48b4`(A1 := A5 + `5d5c`), 아니면 `b48ac`(A1 := A5 + `5d98`, `BRA b48b8`). **`b48b8`**: WORD `(A1)` 읽기(TST)(fall-through `b48ba`). **`b48ba`**(결정 4): WORD `(A1)` = 0 → `b494c`, 아니면 `b48be`: D0.W := WORD `10000e` & 1, ≠ 0 → `b48d2`(A2 := A5 + `5d98`), 아니면 `b48ca`(A2 := A5 + `5dd4`, `BRA b48d6`).
- **`b48d6`**: A1 = A2(LONG) → `b494c`, 아니면 `b48dc`: D7 := (A6 & `ffff0000`) | WORD `(A1)`, A0 := D7, `JSR 289e`(복귀 `b48e8`). **`b48e8`**(소비자): Clear → `b4942`, Set → `b48ec`.
- **`b48ec`**: push A1, A2 := A0, A0 := A5 + `5dd4`, A3 := LONG `2(A1)`, LONG `(A0)` := LONG `(A3)`, LONG `4(A0)` := LONG `4(A3)`(A3 += 8), WORD `(A0)` += WORD `42(A2)`, WORD `2(A0)` += WORD `46(A2)`(D0.W/D1.W = 그 값), D0.W := WORD `90`, A1 := LONG `(b433c + sext(D0.W))`, `JSR (A1)`(복귀 `b491a`). **`b491a`**(소비자): A1 := pop; Clear → `b4942`, Set → `b4922`.
- **`b4922`**: push A6, push A1(`MOVEM.L a1/a6`), D0.W := WORD `8a`, A6 := (A6 & `ffff0000`) | WORD `(A1)`(D7 = 그 값), A1 := LONG `6(A1)`, `JSR (A1)`(복귀 `b4936`, live 대상). **`b4936`**: A1 := pop, A6 := pop, D0.W ≠ WORD `8a(A6)` → `b4950`, 아니면 `b4942`.
- **`b4942`**: A1 += `a`, WORD `(A1)` 읽기, `BRA b48ba`. **`b494c`**: D7.W := pop WORD, `RTS`. **`b4950`**: D7.W := pop WORD, D7.B |= 4, `RTS`.
- **`b4354`**(표 `b433c` 판정기, `JSR (A1)` 진입): D0.W := WORD `(A0)+`, D1 := LONG `(A0)+`, D0.W += D1.W, D0.W −= WORD `4a`, 무부호 D0.W ≥ D1.W → `b43d8`, 아니면 `b4364`: SWAP D1, D0.W := WORD `(A0)+`, D1.W += D0.W, D1.W −= WORD `4a`, 무부호 D1.W ≥ D0.W → `b43d8`, 아니면 `b4374`(C Set, `RTS`). [F] 두 번째 축도 WORD `4a(A6)`를 쓴다(원본 바이트 `926e004a`).
- **`b437a`**(같은 표, `JSR (A1)` 진입): push A0, `JSR b4aca`(복귀 `b4380`). **`b4380`**: A1 := A0, A0 := pop, `BRA b4388`. **`b4388`**: D0.W := WORD `(A1)+`, D1 := LONG `(A1)+`, BYTE `15` bit 0 = 0 → `b439a`, 아니면 `b4396`: D0.W := −(D0.W + D1.W)(fall-through `b439a`).
- **`b439a`**: D0.W += D1.W + WORD `4a` − WORD `(A0)`, D1.W += WORD `4(A0)`, 무부호 D0.W ≥ D1.W → `b43d8`, 아니면 `b43ac`: SWAP D1, D0.W := WORD `(A1)+`, BYTE `15` bit 1 = 0 → `b43be`, 아니면 `b43ba`: D1.W := −(D1.W + D0.W). **`b43be`**: D1.W += D0.W + WORD `4e` − WORD `2(A0)`, D0.W += WORD `6(A0)`, 무부호 D1.W ≥ D0.W → `b43d8`, 아니면 `b43d2`(C Set, `RTS`). **`b43d8`**: C Clear, `RTS`.
- **`1c8a4`**: push WORD D0, `JSR 1aa3a`(복귀 `1c8ac`). **`1c8ac`**: D1.W := D0.W, D0.W := pop WORD, D1 bit 5 = 0 → `1c8b8 RTS`, 아니면 `1c8ba`: A0 := `100cb8`, D0.W &= 1, 0 → `1c8ce`, 아니면 `1c8c8`: A0 := `100da8`. **`1c8ce`**: BYTE `a7(A0)` bit 4 := 1, A4 := LONG `8c(A0)`, WORD `8(A4)` += `1f0`, 무부호 WORD `8(A4)` < `780` → `1c8ee RTS`, 아니면 `1c8e8`: D0 := 1, `BSR 1c1f4`(복귀 `1c8ee`).
- **`1c1f4`**: A4 := LONG `8c(A0)`, D1 := BYTE `4(A4)`(D1 상위 0), D1.B := BYTE `(1c1c4 + D1.W)`, D0 := D0.W × 3, D0.W += D1.W, D1.B := BYTE `9e(A0)`, D1.B := BYTE `(1c1c0 + D1.W)`, D0 := D0.W × 4, D0.W += D1.W, D0.B := BYTE `(1c238 + sext(D0.W))`, D1.B := BYTE `9f(A0)`, BYTE `a0(A0)` := D0.B; C := 무부호 D1.B < D0.B; D1.B ≠ D0.B → `1c232`(C Set, `RTS`), 같으면 `1c230`(C Clear를 돌려주는 `RTS`).
- **`e62a8`**: D0 bit 0 = 0 → `e62ba`, 아니면 `e62b0`: A1 := `10de18`, `BSR e62ce`(복귀 `e62ba`). **`e62ba`**: D0 bit 1 = 0 → `e62cc RTS`, 아니면 `e62c2`: A1 := `10de20`, `BSR e62ce`(복귀 `e62cc`).
- **`e62ce`**: A0 += 4, X := 0(`ADDI.B #0,D0`, D0 그대로), BYTE 네 번 `ABCD -(A0),-(A1)`(결정 3; 올림 X 전달), 마지막 C = 0 → `e62ea RTS`, 아니면 `e62e0`: WORD `(A1)` := `9999`, BYTE `2(A1)` := `99`(fall-through `e62ea`).
- **`e991c`**: push D1, `JSR e9b5a`(복귀 `e9922`). **`e9b5a`**: push WORD D0, A0 := `e9b8a`, D0.W := `a`, A1 := `100bf4`, `JSR 2986`(복귀 `e9b72`). **`e9b72`**: D0.W := pop WORD, WORD `88(A0)` := D0.W, A1 := A5 + `5e4a` + 2·sext(D0.W)(ADDA.W 두 번), D1.W := WORD `(A1)`, WORD `8a(A0)` := D1.W, WORD `(A1)` += 1, `RTS`.
- **`e9922`**: D3 := pop LONG, A1 := A0 + `76`, D7 := 0, D4 := 7, D6.B := 7(fall-through `e9930`). **`e9930`**: D3 := D3 ROL 4, D5.B := D3.B & `f`, ≠ 0 → `e9942`, 아니면 `e993c`: D6.B −= 1, 옛 부호 BYTE D6 ≥ 1 → `e9952`, 아니면 `e9942`. **`e9942`**: D6.B := D5.B, D5.B := 3·D5.B(BYTE), BYTE `(A1 + sext(D7.W))` := D5.B, D7.W += 1, D6.B := 0. **`e9952`**: `DBRA D4,e9930`(→ `e9956`). **`e9956`**: BYTE `8f(A0)` := D7.B, `RTS`.

## 객체 `e5580`(결과 화면 순위 입력)

- **`e5580`**(`28ae` 자식 값): 무부호 WORD `80` < `a` → `e55a4`, 아니면 `e558a`: WORD `7a` := `3c`, 설치 `e5596`. **`e5596`**(설치 값): WORD `7a` −= 1, 결과 0 → `e55a0`(`BRA e5606`), 아니면 `e559e RTS`.
- **`e55a4`**: D0.W := WORD `80`, `JSR e693a`(복귀 `e55ae`). **`e55ae`**: WORD `76(A0)` := WORD `7c`, 0 → `e55b8`(D0.W := `70d8`, A1 := `10de18`, `BRA e55d0`), 아니면 `e55c6`(D0.W := `7318`, A1 := `10de20`). **`e55d0`**: WORD `78(A0)` := D0.W, LONG `7a(A0)` := A1, BYTE `62` := 0, 설치 `e55e2`.
- **`e55e2`**(설치 값): BYTE `62` = 0 → `e55ea RTS`, 아니면 `e55ec`: A0 := `10de14`, WORD `7c` = 0 → `e5600`, 아니면 `e55fa`: A0 := `10de1c`. **`e5600`**: `JSR e6556`(복귀 `e5606`). **`e5606`**: A0 := LONG `c`, BYTE `62(A0)` := `ff`, `JMP 2a00`.
- **`e693a`**: push WORD D0, A0 := `e6952`, D0.W := `14`, `JSR 28ae`(복귀 `e694c`). **`e694c`**: WORD `7e(A0)` := pop WORD, `RTS`.
- **`e6556`**: push A0, `JSR e6516`(복귀 `e655c`). **`e655c`**: A0 := pop, 무부호 D0.W ≤ `a` → `e6568`, 아니면 `e6566 RTS`. **`e6568`**: 부호 D0.W ≤ `a` → `e6582`, 아니면 `e6570`(TRAP #15 경계; `e655c`에서는 일어나지 않음, 결정 6).
- **`e6516`**: A1 := `10f02e`, D0 := 1, D1 := 1, D3 := LONG `(A0)`(fall-through `e6522`). **`e6522`**: D4 := LONG `(A1)`, 무부호 D3 ≥ D4 → `e652e`, 아니면 `e652a`: D0.W := D1.W + 1. **`e652e`**: D3 > D4 → `e6552`(D1.W −= 1, `RTS`), D3 < D4 → `e6540`, 같으면 `e6538`: D1.W = `a` → `e654c`, 아니면 `e6540`. **`e6540`**: A1 += 8, D1.W += 1, 부호 D1.W ≤ `a` → `e6522`, 아니면 `e654c`: D0 := D1 := `ffffffff`, `RTS`.
- **`e6582`**: D1 := `a`(fall-through `e6584`). **`e6584`**: push A0, D1, D0(`MOVEM.L d0-d1/a0`), `JSR e65b0`(복귀 `e658c`). **`e658c`**: pop D0, D1, A0; D1.W = D0.W → `e659a`, 아니면 `e6596`: D1.W −= 1, `BRA e6584`. **`e659a`**: D0.W −= 1, D0 := D0.W × 8, A1 := `10f02e` + sext(D0.W), D0 := 8, `JSR e63ec`(복귀 `e65ae RTS`).
- **`e65b0`**: 부호 D1.W ≤ `a` → `e65ba`, 아니면 `e65b8 RTS`. **`e65ba`**: D1.W −= 1, N = 0 → `e65c2`, 아니면 `e65c0 RTS`. **`e65c2`**: D1 := D1.W × 8, A1 := `10f02e` + sext(D1.W), A0 := A1 − 8, D0 := 8, `JSR e63ec`(복귀 `e65da RTS`).
- **`e63ec`**: 옛 D0.W = 0 → `e63f8 RTS`(D0.W := `ffff`), 아니면 `e63f2`(D0.W −= 1). **`e63f2`**: BYTE `(A1)+` := BYTE `(A0)+`, `DBRA D0,e63f2`(→ `e63f8`).

## 객체 `b33d8`, card menu 그리기 `a8ee`

- **`b33d8`**(FR1b `28ae` 자식 값): D0 := 0, D1 := 0, `JSR 49290`(복귀 `b33e2`). **`b33e2`**: WORD `68` `1e` := `e0ed`, D0.W := `5e`, D1.W := 2, D2.B := 0, `JSR c6a96`(복귀 `b3400`). **`b3400`**: anim(`15b`, `20017c`, `8`)(복귀 `b3428`). **`b3428`**: 설치 `b342e`.
- **`b342e`**(설치 값): `JSR 43e34`(복귀 `b3434`). **`b3434`**: `JSR 49fc6`(복귀 `b343a`). **`b343a`**: A0 := LONG `c`, BYTE `61(A0)` bit 7 = 0 → `b344e`, 아니면 `b3448 JMP 2a00`. **`b344e`**: `JSR 288c`(복귀 `b3454`). **`b3454`**(소비자): Set → `b345e RTS`, Clear → `b3458 JMP 2a00`.
- **`a8ee`**(메뉴 기록 LONG, `JSR (An)` 진입): D7 := `d22b`, `BRA a770`. **`a770`**: D0 := 0(fall-through `a772`). **`a772`**(결정 8): push D7, `JSR 9ee6`(복귀 `a77a`). **`a77a`**: D1.W := `fd00`, D7.B ≠ 0 → `a788`, 아니면 `a784`: D1.W := `fe00`.
- **`a788`**: D7 := pop LONG, push WORD D1, push D0, push D7, `JSR 9f12`(복귀 `a796`). **`a796`**: D0.W := (D0.W LSL 3) + 8, D1.W := D1.W LSL 3, SWAP D0, D0.W := `1f8` − D1.W, push D0, `JSR 9ef8`(복귀 `a7ac`).
- **`a7ac`**: D1 := (D1 & `ffff`) LSL 8, `DIVU.W D2,D1`(결정 7), 무부호 D1.W < `80` → `a7c2`, 아니면 `a7c0`: D1.W −= 1. **`a7c2`**: D1.W |= `ff00`, D5.W := `ffff`, D0 := pop LONG, D7 := pop LONG, D0 상위 WORD += pop WORD, D0.W += pop WORD, SWAP D1, D1.W := pop WORD, `JMP cd58`.
- **`9ee6`**: A2 := LONG `-ee(A5)`, D7.B := (A2 = LONG `-f2(A5)`) ? `ff` : 0, `RTS`. **`9ef8`**: A2 := LONG `-ee(A5)`, D0 := BYTE `b(A2)`, D1 := BYTE `4(A2)`(상위 0), D2.W := D0.W, D3 := 0, D2.B := BYTE `c(A2)`, `RTS`. **`9f12`**: A2 := LONG `-ee(A5)`, D0 := BYTE `9(A2)`, D1 := BYTE `a(A2)`(상위 0), `RTS`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다. index 범위는 원본에 상한 검사가 없어 [I]로 적는다.

| 표 | 범위 | 읽는 곳 | 내용 |
| --- | --- | --- | --- |
| 판정기 LONG | `b433c..b4354`(6 LONG, SHA256 `6ec1d6ed9b369ccb346d3943fbf4f8fe5624b07272a12c5930fee4739da1956e`) | `b4780` `b47a4` `b48ec`(index WORD `90(A6)`, byte offset) | `b4354` `b437a` `b437a` `b437a` `b437a` `b437a` |
| 판정 상자 포인터 LONG | `b4ad4..b4aec`(6 LONG, `3b77c3bad204524484b0a1bad6f4cb7efe3cca9a286e1f6bc5431f5f922cb9e1`) | `b4aca`(index WORD `90(A6)`) | `b4c56` `b4c56` `b4c5e` `b4c66` `b4c6e` `b4c76`(각 8 byte: WORD, LONG, WORD; `b437a`·U01 `1aa7e`가 읽음) |
| WORD 표 | `b46f6..b4706`(8 WORD, `8946ca72d1806619f743909b0a94220bf0c2d13e31dcb9499f00df5688c5c8df`) | `b46c0`(index 2·(D1.W & 7)) | `0000 000c 0018 0024 0006 0012 001e 002a` |
| 아이템 기록 | `b3894..b3dbc`(12 byte × 110, `e55d358c5f83da281bca84ee20b85dda8d3fb6422b09aae229646e30f72a4d27`, FR1 계약과 같은 표) | `b4680`(BYTE 1 bit 0), `b46a2`(LONG 4 = 처리기), `b442e` `b4440` `e62ce`(LONG 8 = BCD 점수) | 처리기 29곳: `b445e` 81 기록, `b44ac` 2, `b44b2..b45f0` 각 1(FR2h); BYTE 1 bit 0이 선 기록 26 |
| BYTE 표 | `1c1c0..1c1c4` `00010203`, `1c1c4..1c1f4`(48 byte, `6b7fcdcd…`), `1c238..`(`00030507 01030608 …`, `28bb5485…` = 첫 40 byte) | `1c1f4` | index는 BYTE `9e(A0)`, BYTE `4(A4)`, (3·D0.W + t1)·4 + t2 |
| bank LONG | CPU `2001c4` `20017c` | `c0b24`(LONG `14(…)`), `b3400`(LONG `8(…)`) | 물리 `200000` bank 값은 V1·실제 ROM 차분이 원본 bank 바이트로 읽는다(단위 시험은 합성). [U] 물리 `300000` bank에서의 쓰임 |

- [F] **callee에게 넘기기만 하는 자료**: `49f8c`의 A1(bank 창이 가리키는 값), `28ae` 자식 `e6952`(`e693a`), `2986` 자식 `e9b8a`(`e9b5a`, list `100bf4`), `c6a96` `49290` `3af8` `49260` `cd58`의 D0..D7.

## 경계·routing 밖 출구

- [F] live 대상(결정 2): `b46aa JSR (A1)`(아이템 기록 LONG 4), `b478c` `b47b0` `b4918 JSR (A1)`(표 `b433c`), `b4934 JSR (A1)`(RAM 목록 기록의 LONG 6). 복귀 LONG을 넣고 PC := A1이다. routing 밖·홀수 대상은 dispatcher가 `unsupported animation machine PC`/`unaligned animation machine PC`로 전체 rollback한다.
- [F] TRAP #15 경계(결정 6): `b466c`(`b4664`, 무부호 D1.W ≥ `6e`, 뒤 문자열 `ITEM RESULT ERROR`), `e6570`(`e6568`, 부호 D0.W > `a`, 뒤 문자열 `RANK IN trapped`). PC := TRAP 위치로 끝나고 dispatcher가 `unsupported animation machine PC`를 낸다.
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 41개: `9ee6` `9ef8` `9f12` `1c230` `1c232` `1c8b8` `1c8ee` `b345e` `b433a` `b4374` `b43d2` `b43d8` `b4434` `b4458` `b445e` `b46bc` `b47ea` `b47f8` `b47fe` `b4804` `b494c` `b4950` `b4a22` `b4ab0` `b4aca` `c0ba6` `e559e` `e55ea` `e62cc` `e62ea` `e63f8` `e654c` `e6552` `e6566` `e65ae` `e65b8` `e65c0` `e65da` `e694c` `e9956` `e9b72`.
- [F] **native 정지 규칙 주의**(V1·실제 ROM 차분): FR1b의 `first_unrouted` 수정판(`8c16 < pc <= 8ca6` 내부, 정지 `2a00` `2a24`)을 그대로 쓴다. 이 단위의 출구 중 C++가 한 block으로 처리하는 잎(`8c16` 꼴)은 없다(`leafscan.py`).

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1·FR1c spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 자연 node·플레이어 기록, A1 := RAM 상자, A5 기준 RAM(`5d48` `5d50` `5d5c` `5d98` `5dd4` `538e` `5e4a` `-ee` `-f2` `-7ff2`), `10dd48`/`10dd50`, `10de14..`, `10f02e..` 순위 표, LONG `c(A6)` := 자연 node, 스택 LONG/WORD, PC).
- [I] IO 관측 상태가 이 단위의 실제 진입 상태다(`fr1c/ioA/frontier.json`의 확정 frontier). V1 spec에는 이 출처를 주석으로 적고, IO 비교 재실행(검증 작업자)이 자연 경로를 직접 확인한다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `288c` → `b3454`(`b344e`), `289e` → `b48e8`(`b48dc`), `b4760`(`b4aca`, U01 `1aa7e`) → `b4a18`(`b4a14`), 이 단위 판정기 `b4354`/`b437a` → `b478e`(`b4780`) `b47b2`(`b47a4`) `b491a`(`b48ec`), 아이템 처리기 `b445e` → `b46ac`(`b46a2`). `49fc6` → `b433a`는 단위 시험에서 선언 C, V1·실제 ROM 차분에서 실제 사슬(`b4334`). `1c1f4` → `1c230`은 단위 안 사슬(Clear).
- node fixture: 진입(`c0ace` `e5580` `b33d8`)과 설치 값(`c0b52` `e5596` `e55e2` `b342e`)을 node callback으로, `a8ee`는 메뉴 처리기 진입(복귀 LONG = sentinel)으로 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `b4958` `b4334` `b4ab0` `b4aca` `1c8a4` `1c1f4` `e62a8` `e991c` `e6556` `e63ec` `b4354` `b437a` `b445e` `9ee6` `9ef8` `9f12` `a770` `a772`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, FR1c 꼴): 시작 218개 × 들어오는 C 3가지, zero-step, 내부 PC 844개 정확한 오류, 경계 stop(출구 전부, live 대상은 RAM 탐침), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), BYTE·WORD·LONG 부호 경계(`b496c`의 BYTE 올림, `c0b58` LONG `20000`/`1ffff`/`80000000`, `c0b6e` `28000` 경계, `e6540`/`e65b0` WORD `a`/`b`/`8000`, `e993c` BYTE `80`/`1`/`0`, `ASR.L` 부호 bit, `MULU` 입력 `ffff`, `ADDA.W` sext 경계 `8000`, `DIVU` 0/넘침), `b47f4` 직접 진입은 SR C = (D1.W < D0.W), `b48ba` 직접 진입은 SR Z = (WORD `(A1)` = 0)(결정 4). `ABCD`는 BCD·비 BCD 숫자를 모두 넣어 원본 CPU(Unicorn) 결과와 비교한다(결정 3).

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `probe_scan2.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_a.out` 26줄)과 `make test`로 확인한 결과:
  - 그대로 참인 것(stop-only·레지스터 값·자기 범위 끝): FR1a 시험의 `e5580`(`e5542` 행의 A0 값, `RANGES` 끝), FR1b 시험 `b31c0` 행의 A0 = `b33d8`, C2 시험 `RANGES` 끝 `a770`, B2e 시험·spec `e693a`(자기 범위 끝·`ends[]` 범위 밖 확인), U02 시험 `rom_outside[]`(`e5612`, 자기 범위 밖 확인만), B3a·motion_walk·stage_area·stage_counter 시험의 같은 값(레지스터·RAM 값), 관측기 `observe_*`의 고정 범위 표(pin된 역사 기록).
  - **옮긴 것(결정 9, 이전 기대값 기록):**
    - `engine/tests/animation_machine_objects_fr1b_test.cpp` `rules()`의 범위 옆 자료 PC 목록: `b345e`(FR2a `RTS` block)를 RAM `10fe5e`로 바꿨다(이전 기대: `unsupported animation machine PC`).
    - `engine/tests/animation_machine_stage_event_test.cpp` `computed()`: `e97d8 JMP e97e4(PC,D1.W)`가 D0.W = `ce..dd`이면 FR2a 범위 `e991c..e995c`에 떨어진다(16 대상). FR2a 시작 `e991c` `e9930` `e993c`는 stop-only 확인, 나머지 13개는 `unsupported animation objects fr2 PC`로 기대를 바꿨다(이전 기대: 모두 `unsupported animation machine PC`). 결과 줄 `73/162 computed targets run/rejected` → `76/159`.
    - `tools/verify_animation_machine_frame_helpers.py`(outside 탐침 `b4ab0`)·`tools/verify_animation_machine_card_menu_close.py`(outside 탐침 `9ee6`): FR2a block 시작이 됐으므로 RAM `10fe46`으로 바꾸고 `SUPERSEDED_RECORDS`에 이전 기대(`unsupported animation machine PC`)를 남겼다. 이 두 검증기는 실행하지 않았다(검증 작업자, 공유 `artifacts/` OUT 주의).
  - [F] stage_event / stage_event_ops 검증기의 `CPP_PINS`(`animation_machine.cpp` `00ff3a1b…`, `animation_machine_internal.h` `caad91c1…`)는 이 단위의 공유 수정으로 맞지 않게 된다(FR1 뒤 `2f74353` 관례대로 새 값 `eadc97b0…`/`522199f9…`로 갱신 필요; 메인 결정).
- [I] V1 spec 중 native 사슬이 `c0ace` `e5580` `b33d8` `a8ee`(또는 `b4958` `b4334` `e62a8` 등 공유 진입)를 첫 routing 밖 PC로 멈추던 것은 더 진행한다. spec 정지 조건이 바뀌면(FR1c b2a 관례) stop-only 경계를 더한다.
- [I] frame 회귀: card menu `a8ee`, 결과 화면 `e5580`은 기존 자연 frame에서도 닿을 수 있다. 그 frame이 이 PC에서 `unsupported animation machine PC`로 끝났다면 더 진행한다(이득). 자연 불일치는 결함이다(검증 작업자).

## 결정

1. **범위.** FR2a = `c0ace` 묶음 148 + `e5580` 45 + `b33d8` 12 + `a8ee` 13 = 218 block. 실행 수 1위 `4e68e`(14)는 FR2a 뒤에도 484 block이라 한 단위가 될 수 없고, 나머지 3 run root(`50dae` 211, `5ab82` 202, `bc844` 66)를 더하면 약 220을 넘는다. 그래서 12 run 두 root를 먼저, 작은 `b33d8`(3)·`a8ee`(1)를 더했다(`bc844`를 넣으면 284). 메인이 `bc844`를 FR2a에 넣고 `a8ee`를 미루거나, `4e68e`를 먼저 하도록 바꾸면 끝 절 명세를 다시 잰다.
2. **계산 호출 `JSR (A1)`.** 5곳 모두 live 대상 routing(F4 관례). 표 `b433c`(6 항목, 대상 2곳)는 작아서 그 판정기 `b4354` `b437a`(13 block)를 넣는다. 아이템 기록 처리기 29곳(192 block) 중 frontier 경로의 것(IO 상태: node `1020f8`의 아이템 `32` → `b445e`, 기록 110개 중 81개가 같은 처리기)만 넣고 나머지 28곳은 FR2h로 미룬다. RAM 목록 기록의 LONG 6(`b4934`)은 정적 대상이 없다.
3. **`ABCD` 의미.** `ABCD -(A0),-(A1)`는 이 프로젝트의 원본 CPU oracle(Unicorn M68000) 규칙을 그대로 구현한다: t = src + `66`; s = t + dst + X; c = s XOR (t XOR dst); 결과 = (s − (((NOT c) & `110`) >> 2 | ((NOT c) & `110`) >> 3)) & `ff`, X = C = bit 8. [F] 이 식은 Unicorn M68000(`UC_CPU_M68K_M68000`)의 `ABCD` 결과·X·C와 256 × 256 × 2 = 131,072 입력 전부에서 같다(scratch `probe/abcd_check.py`, 불일치 0). 두 바이트가 모두 BCD(각 숫자 0..9, 100 × 100 × 2 = 20,000 입력)이면 68000 정의(하위 숫자 > 9면 +6, 합 > `99`면 C)와도 같다(차이 0). [U] 숫자가 `a..f`인 입력에서 실제 68000과 같은지는 확인하지 않았다(알려진 실기 측정 규칙과는 74,688/131,072 입력, Musashi 규칙과는 75,012 입력이 다르다; 예 `8f + 05`(X = 0) = `9a`, C = 0(oracle) / `fa`, C = 1(Musashi)). 원본 자료(아이템 기록 LONG 8, 점수 `10de18..`)는 BCD다 [I]. Z·V·N은 쓰지 않는다(소비자 없음). 메인 확인 필요.
4. **flag 재계산.** `b47f4`: C = 무부호 D1.W < D0.W(유일 선행 `b47de`의 `CMP.W D0,D1`, 레지스터 그대로). `b48ba`: Z = (WORD `(A1)` = 0)(선행 둘 `b48b8` `b4942`가 모두 같은 A1로 `TST.W (A1)`; RAM WORD를 다시 읽는다 — 원본에 없는 bus 읽기 1회이지만 대상은 work RAM 목록이다 [I]). 단위 시험의 Unicorn 직접 진입은 SR C/Z를 그 값과 같게 둔다. V1 native는 SR = `2000`(C = Z = 0)으로 시작하므로 V1 spec의 `b47f4` 직접 진입은 D1.W ≥ D0.W, `b48ba` 직접 진입은 WORD `(A1)` ≠ 0인 world만 쓰고, 다른 쪽은 선행 block 진입으로 덮는다.
5. **carry 보존 목록.** 소비자 7개(`b3454` `b46ac` `b478e` `b47b2` `b48e8` `b491a` `b4a18`)와 C를 넘기는 `RTS` 2개(`b433a`: 49fc6 C를 routing 밖 11곳의 `BCC`로, `1c230`: `1c1f4`의 Clear를 `1cefe`로). 읽는 곳이 없는 known C(위 "carry")는 넣지 않는다. `ORI`/`ANDI; RTS` block(`1c232` `b4374` `b43d2` `b43d8` `b4458` `b445e`)은 자기 block에서 C를 정하고 돌아간다.
6. **TRAP #15 경계.** `b466c`(아이템 index ≥ `6e`)·`e6570`은 단위 범위에 넣지 않는다(FR1 결정 10 관례). [F] `e6568`의 유일 선행 `e655c`는 무부호 D0.W ≤ `a`일 때만 `e6568`로 가므로 부호 D0.W ≤ `a`가 항상 참이라 자연 경로에서 `e6568 → e6570`은 일어나지 않는다. 원본대로 구현하고, `e6568` 직접 진입(선언 D0.W > `a`)은 `e6570`에 닿으므로 단위 시험·V1 spec의 "빠진 후속" 점검에서 빼지 않는다(stop-only 행·오류 행으로 확인).
7. **`DIVU.W D2,D1`(`a7ac`).** 0 나누기는 checked 오류 `objects fr2 DIVU zero divisor`(원본은 vector 5 예외, 모형화하지 않음; FR1a `e56d0` 관례), 몫 > `ffff`이면 V만 서고 D1 그대로, 아니면 D1 = 나머지:몫. 바로 다음 `TST.B D1`이 flag를 덮어 DIVU의 flag는 읽지 않는다. [F] 자연 경로(`a796 → 9ef8 → a7ac`)는 D1 = BYTE `4(A2)` ≤ `ff`라 D1 LSL 8 ≤ `ff00`이고 넘침이 없다. 0 나누기는 BYTE `c(A2)` = 0일 때 일어난다 [U](메뉴 기록 값).
8. **`a772` 시작.** 범위 밖 `aca4 MOVE.L #80000,D0; BRA.W a772`(routing 밖 메뉴 항목)가 `a770 MOVEQ #0,D0` 다음으로 들어오므로 `a772`를 block 시작으로 둔다(`a770`은 한 명령 block, fall-through `a772`).
9. **숨은 탐침 이전.** 기존 시험이 이 범위의 PC를 routing 밖 rollback으로 기대하면 RAM `10fexx` 탐침이나 stop-only 확인으로 옮기고 이전 기대값을 남긴다. 실제로 옮긴 것: FR1b 시험 `b345e`, stage_event 시험의 `e97d8` 계산 대상 16개, frame_helpers 검증기 `b4ab0`, card_menu_close 검증기 `9ee6`("영향받는 기존 시험"). stage_event / stage_event_ops 검증기의 `CPP_PINS` 갱신은 메인이 정한다.
10. **자식 값.** `28ae` 자식 `e6952`(`e693a`), `2986` 자식 `e9b8a`(`e9b5a`)는 따라가지 않는다(다음 frontier 후보; FR2e/FR2h).

## 미확인

- [U] node field 의미(BYTE `12` `13` `61` `62` `94` `95` `96`, WORD `7a` `7c` `7e` `80` `88` `8a` `8c` `90`, LONG `36` `3a`), 표 `1c1c0`/`1c1c4`/`1c238`·`b46f6`의 의미, RAM `5d48(A5)` `5d5c(A5)`·`5d98(A5)`·`5dd4(A5)` 목록 기록, `5e4a(A5)` 계수기, `-ee(A5)` 메뉴 기록의 정체.
- [U] 비 BCD 숫자에서 `ABCD`의 실제 68000 결과(결정 3), `a7ac` 0 나누기가 실제로 일어나는지(결정 7).
- [U] 물리 `300000` bank에서 bank 창 LONG의 쓰임.
- [U] 자연 frame에서 이 단위 뒤 다음 첫 미routing PC(IO 비교 재실행으로 확인; [I] 예상: `c0ace` run은 아이템을 먹으면 `2986` 자식 `e9b8a`, 다른 처리기면 그 처리기; `e5580` run은 `28ae` 자식 `e6952`; `b33d8`은 완주; `a8ee`는 메뉴의 다른 처리기).

## FR2b 이후 명세

[F] 각 단위는 앞 단위가 모두 routing된 상태를 가정해 같은 규칙으로 잰 값이다(scratch `specs.py`, `EXTRA_ROUTED` = 앞 단위 범위; 실제 착수 때 그 시점의 routing으로 다시 잰다). 진입(root)과 정지 집합이 정의이고, block 수·시작 목록 SHA256(`starts_<name>.txt`, 첫 16자)은 확인값이다.

| 단위 | 진입 | 추가 정지 | block | 명령 | 시작 목록 SHA256 | 범위 요약 | 비고 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FR2b | `4e68e` 본체가 부르는 helper 19곳: `b0c 371e 3786 ca3a ca50 ca5c ca64 ca6a 1be3a 1bf94 1c052 1c086 4a90e 4d86e 4e0f6 4e112 b7a28 e6496 e8c3a` | — | 157 | 405 | `7159ccb85c7d82f9` | `b0c..b58` `371e..37e2` `ca3a..ca70` `1a988..1a996` `1be3a..1c0d2` `4a90e..4a944` `4c0f0..4c1de` `4d86e..4da2a` `4e0f6..4e122` `b7a28..b7a2e` `e6496..e6516` `e8b6e..e8cc0` | 계산 점프 `3772` `37d8`(표 전사 필요), `28ae` 자식 `b3dfc` |
| FR2c | `4e68e` | `4e94e` `4ebe2`(설치 값) | 167 | 370 | `f2613ca8d1a84a02` | `4e4da..4e5e8` `4e68e..4e69a` `4e69c..4e94e` `4eb58..4ebe2` `4ed3c..4ee7a` `4f22c..4f2ba` | TRAP #15 `4e69a`(WORD `76` ≥ 2), 자식 `4f2e0` `e695a` |
| FR2d | `4e94e` `4ebe2` | — | 160 | 398 | `b60a8687da34872c` | `4e94e..4eb58` `4ebe2..4ed3c` `4ee7a..4eea2` `4eef4..4f08a` `4f118..4f184` `4f1ac..4f22c` | FR2b·c·d가 모두 들어가야 `4e68e` 14 run이 진행 |
| FR2e | `bc844` `e6952` | — | 195 | 453 | `7e7333a8e4d0e017` | `bc844..bcb22` `e6952..e6e06`(여러 조각) `e63fa..e6448` `3144..314c` | `bc844` 3 run(FR1c `bc08c`의 `28ae` 자식); `e6952`는 FR2a `e693a`의 자식([I] `e5580` 12 run의 다음 frontier); TRAP `e6d92` `e6dd0` |
| FR2f | `50dae` | — | 211 | 451 | `0512008d3c01f310` | `50cf6..5160e` `482ea..4833e` `491fe..49214` `1a3a6..1a3ac` | 3 run; 자식 `5146c` `5193c` `51c36` |
| FR2g | `5ab82` | — | 202 | 631 | `e7c303bb25793763` | `5ab82..5b220` `4464a..44666` `d1028..d10d8` | 3 run; TRAP `5ae0e`, 자식 `5ad98` `d1d08` |
| FR2h | 아이템 처리기 28곳 `b44ac b44b2 … b45f0` + `e9b8a` | — | 201 | 481 | `aacb65f64fd5ce90` | `b44ac..b4760`(조각) `1c012..1c922`(조각) `4d55e..4d6b4` `e9b8a..e9c72` | FR2a의 live 대상·자식; TRAP `b470e` `b4730`, 계산 `e9c6e` |

- [F] **`1d1f4` 플레이어 closure(FR2 범위 밖, 다음 플레이어 단위 연속)**: FR2a..FR2h가 모두 routing된 뒤에도 1,521 block(명령 3,248, 70 조각, 16,676 byte), 점프 표 3개(`2031c` 9 항목, `20792` 4 항목, `207ba` `1b` 항목)를 전사하면 1,775 block(명령 3,838)이다. 설치 값 104, `28ae`/`2986` 자식 12, 아직 전사하지 않은 계산 점프 `20378` `203ac` `2094e` `209d6`, live `JMP (A1)` `1aa38`·`JSR (A4)` `201a6`. block 분포: `1c000..` 96, `1d000..` 377, `1e000..` 426, `1f000..` 396, `20000..` 284, `21000..` 80, `22000..` 15, `48000..`/`49000..`/`4c000..`/`4d000..`/`4e000..` 89, 기타 3. [I] 설치 값 단위로 나누면 약 220 block 단위 8–9개가 필요하다(진입 `1d1f4`; `1d20c` 등 설치 상태별로 순서를 정함). IO frontier 실행은 boot-demo-0 1개(frame 381)뿐이다.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr2.cpp`(case label 218 = scratch `starts_a.txt`와 집합 일치, scratch 검사), `engine/tests/animation_machine_objects_fr2_test.cpp`(생성 구역 + 수작성 규칙: `ABCD` 십진·비십진(`8f + 05` = `9a`, C = 0)·`999999` 고정, `DIVU` 몫·넘침(D1 그대로)·나머지, `b47f4` C·`b48ba` Z 재계산(들어오는 C 3가지), `1c1f4` → `1c230`(Clear)/`1c232`(Set)의 C, `b433a`의 C 통과(Unknown 포함), `MOVEM.L` 순서 `b4694` `b4922` `e6584`, `a7c2`의 LONG·WORD pop, `e659a`의 `ADDA.W` 부호 확장(`10f026`), `e993c` 부호 BYTE `BGE`, `e9930 ROL.L`, `b496c` BYTE 올림, `c0b58` 부호 LONG·`ASR.L #4`, `9ee6 SEQ`, `e6568` 부호 WORD(`8000` → `e6582`, `b` → `e6570`), `b4354` 두 축의 WORD `4a`, 범위 옆 자료·TRAP PC 7개(`b433c` `b4ad4` `b46f6` `1c238` `1c1c0` `b466c` `e6570`)의 dispatcher 오류, `1c8ba`의 플레이어 기록), `tools/generate_animation_machine_objects_fr2_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음, SHA256 `7c2a41f6ddffc088…`, 약 12분), `tools/unit_fixture_specs/fr2.py`(V1 spec; 정적 검사만 함 — `load_routing` 규칙 122개 뒤 시작 218개와 내부 844개가 모두 `animation_objects_fr2_block`, sentinel·TRAP `b466c` `e6570`은 routing 밖, 정적 후속은 시작이거나 routing된 출구, 사슬 7개와 통과 사슬 3개의 소비자가 진입에서 닿음; 합성 기반 상태와 가짜 tracer로 world·hint·error·chain/node/callee 생성 함수를 native 없이 실행해 Python 오류 0, 오류 fixture 863개 이름 중복 0, `b47f4` 직접 진입 world는 모두 D1.W ≥ D0.W, `b48ba`는 WORD `(A1)` ≠ 0). 공유 수정은 "공통 규칙"의 다섯 곳과 "영향받는 기존 시험"의 이전 네 곳뿐이다.
- [F] 단위 시험 world: A7 = `10ef00`, 합성 typed physical byte(ROM 자료 아님, 자료 영역만): `1c1c0..1c1f4`(값 0..3) `1c238..1c278`, 아이템 기록 `b3894..b3dbc`(처리기 = `b445e`/`b4374`/`b43d8`/RAM `10fe40`, 기록 `32` = `b445e`, LONG 8 = BCD(가끔 비십진·부호 bit)), LONG 표 `b433c..b4354`(`b4354` `b437a` `10fe40` `b437a` `b4354` `b437a`), `b4ad4..b4aec`(→ RAM 상자 `10e600..10e630`), WORD 표 `b46f6..b4706`, bank 창 `2001c4`(→ `2a0700`) `20017c`(→ `2a0800`)와 `2a0714` `2a0808`. 실제 생산자 사슬은 RAM만 읽는 `288c`(LONG `c(A6)`·`(부모)` = `270e`), `289e`(목록 WORD → node LONG `270e`), U01 `1aa7e`(`b4aca`의 상자, 화면 한계 `53f2..53f8(A5)`), 이 단위 판정기·처리기로 두 C 값을 모두 만든다. work RAM은 native에서 실행할 수 없으므로(fetch 보호) RAM live 대상은 C++ 전용 오류 행으로만 확인한다. `1c1f4`의 기대 C는 생성기의 독립 Python 모델(native 끝 D0.B·D1.B의 무부호 빌림)이고 Unicorn SR은 읽지 않는다.
- [F] `make -j3 all test`(작업자, scratch `make_all3.log`; `make_all2.log`와 시험 줄 동일): 종료 0, 경고 0, Assert 줄 0, 시험 실행 274개, Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR2 시험 줄: `animation machine objects fr2: 930 fixtures (652 single-block, 180 path, 48 producer chain, 18 declared C, 32 checked error (12 with a later failing PC), 98 kept C, 13 data C), 218 blocks, 4520 calls, 282298 checks`. 기준(scratch `make_base.log`, `11be2b6`) 대비 다른 시험 줄 변화는 stage_event의 `73/162` → `76/159`(위 이전)뿐이다. 단일 block 표에서 모든 조건 분기의 두 쪽을 들어갔다(예외 `e63f2 DBRA`의 자기 반복: 같은 PC가 stop이면 zero-step이라 path 행으로 덮음), 출구 17개 + STOP + TRAP 2곳이 모두 어떤 행의 stop이다.
- [F] 검증 작업자 준비물(scratch, 실행하지 않음): `build_ubsan.sh`, `mut/run_mut.py`(변이 151개; 패턴 유일성 확인, `--check`는 문법 검사까지), `realrom/real_fr2.py`(FR1c harness에 FR2a world·소비자·진입·`b47f4` SR C·`b48ba` SR Z; `py_compile`만), `runwrap.py` `run_frames.sh` `run_area_clear.py` `run_stage_entry.py` `run_regs.sh`(경로만 바꿈). 실행 순서와 기대값은 scratch `HANDOFF.md`.

## 검증 기록(검증 작업자 Sonnet 5.5 / medium, macOS, `MS5_SEED_DIR=artifacts/stage_entry_body`)

[F] 모든 출력은 scratch `/Users/start/Workspce/ms5-scratch/fr2/`에만 썼다(공유 `artifacts/`는 읽기 전용; frame_helpers·card_menu_close·stage_event·stage_event_ops는 `legacy/mkroot.py`로 만든 git clone + 작업 트리 변경 + 공유 artifacts 심볼릭 링크 + 자기 출력 폴더만 실제 디렉터리인 scratch 루트에서 실행). ROM SHA256 `29112a94…c860f`, mtime `1791291625` 변동 없음.

| 단계 | 명령 / 방법 | 결과 |
| --- | --- | --- |
| 빌드·시험 | `make -j3 all test`(최종 `-j2` 재실행 포함) | 종료 0, 경고 0, Assert 0, 시험 274개, Python 310개 OK; fr2 줄 `930 fixtures …, 218 blocks, 4528 calls, 282307 checks`(수작성 규칙 추가 후; 이전 4520 / 282298) |
| UBSan | `build_ubsan.sh`(`-fsanitize=undefined -fno-sanitize-recover`), 규칙 추가 전·후 2회 | 종료 0, `runtime error` 0 |
| 변이 | `mut/run_mut.py` 151개 | 처음 145 / 151 사망; 생존 6개(`table-no-sext` `1c1f4-mulu4-word` `b4680-zext` `b4936-no-a6` `b4aca-zext` `e9942-index-zext`)에 수작성 규칙을 더한 뒤 전체 재실행 **151 / 151 사망**(동치 판정 0) |
| 실제 ROM 차분 | Unicorn ↔ C++, 8개 `program_rom_*.ms5d`, bank `200000`/`300000`, 5 × 1,500(s1 s2 s3 plain, f4 f5 FOLLOW_ANIM) | 불일치 **0**(5 배치), 시작 218 / 218 모두 덮음, 소비자 7개가 실제 생산자 뒤에서 native 분기와 비교됨(예 s1: `b3454` 68 `b46ac` 40 `b478e` 32 `b47b2` 46 `b48e8` 56 `b491a` 43 `b4a18` 231); harness 수정 없음 |
| V1 fr2 | `unit_fixtures --spec fr2.py --workers 1` 2회 | 1,592 fixture 모두 ok, 두 실행의 `[(name,digest)]` 동일, `visited 218/218`, carry oracle ok(Unknown/Clear/Set 630/62/30), 오류 860 · 일치 722 · 선언 불일치 10 |
| V1 회귀 | fr1 fr1b fr1c b2a b4 b4b | 1,631 / 1,441 / 1,755 / 1,386 / 1,830 / 1,723, 실패 0(기준과 같음); 나머지 17개 spec(b1a b1b b1c b2b b2c b2d b2e b3a b3b b3c c1 c2 c3b d9 f6a f6b f6c)도 종료 0 |
| 이전된 검증기 | frame_helpers(scratch 루트) | PASS: cases 199, split 3,683, negatives 180, preserving 38 |
| | card_menu_close(scratch 루트) | PASS: cases 82, split 7,886, negatives 85, prefix 12,175 |
| | stage_entry(`run_stage_entry.py`) | PASS: cases 335, split 23,761, negatives 2,757, carry 21,829/100/1,832(기준과 같음) |
| | area_clear(`run_area_clear.py`) | PASS: conditions 256, frames 37,418, split 117,537, continuous 37,444, negatives 181, guards 26(기준과 같음) |
| | stage_event_ops(핀 갱신 뒤) | PASS |
| | stage_event(핀 갱신 + 아래 이전) | PASS: typed 560, phases 22,870, guards 117, natural nodes 9,613, negatives 1,020 |
| frame | D1 / controller game / IRQ / controller demo | 54,400 / 54,400, 54,400 / 54,400, 54,400 / 54,400, 45,684 / 45,684, 자연 불일치 0; FR1c 보고서와 비교해 입력 해시 외 바뀐 frame·필드 없음 |
| IO | `verify_animation_machine_io.py` 2회(`--workers 1`) | `verification.json` `frontier.json` 두 실행 바이트 동일(SHA256 `2e39bf7e…` `4a8077c7…`), 불일치 0, C++ 오류 0 |

**IO 변화**(FR1c `ioA` 대비 첫 실패 전 일치 프레임): P0 81,600 → 81,600(+0), P1 62,586 → 63,840(+1,254), P1b 4,917 → 5,031(+114), boot-demo-0 381 → 381, boot-title-idle 600 → 600, boot-title-start 113 → 117(+4), fixture fx-start-c79a 265 → 269, fx 나머지 변동 없음. 합계 **150,472 → 151,848(+1,376)**, 비교 173,966 프레임, 불일치 0, frontier run 53(확정 52 + fixture 1) 그대로, `routing_file_sha256` `eadc97b0…`. `c0ace`(12) `e5580`(12) `b33d8`(3) `a8ee`(1) root는 frontier에서 사라졌다(28 run이 더 진행).
새 frontier(PC: run 수, 설정, frame, 부모 callback → 복귀): `4e68e` 14(P1 12 + P1b 2, frame 2·222) 변동 없음; **`48256` 12**(P1 11 + P1b 1, frame 325, node callback `e525a` → `e528c`; `e5580` run의 다음 root); **`76852` 12**(P1 11 + P1b 1, frame 133, callback `76852` → `2ac2`; `c0ace` run의 다음 root, [I] 계약이 예상한 `e9b8a`가 아니다); `50dae` 3(frame 271); `5ab82` 3(frame 141); **`b336a` 3**(P1 2 + P1b 1, frame 120; `b33d8` run의 다음 root); `bc844` 3(frame 217); **`a92a` 1**(boot-title-start, frame 117, callback `b344` → `9e14`; `a8ee` 다음); `1d1f4` 1(boot-demo-0, frame 381). 새 root 4개(`48256` `76852` `b336a` `a92a`)는 FR2b 이후 명세에 없는 다음 frontier 후보다. 경로: `/Users/start/Workspce/ms5-scratch/fr2/ioA/frontier.json`.

**검증 작업 중 고친 것(전부 승인된 범위)**
- `tools/unit_fixture_specs/fr2.py`: (1) `trace()`가 홀수 live `JSR (A1)` 목표를 정지 PC로 돌려주면 `invalid animation machine RAM/PVC/stop PC`(`block-b4922-0` `block-b4922-1` `callee-b476a-3`)였으므로 그런 trace를 버린다(홀수 목표 오류 행은 `error_fixtures`에 있음). (2) 스택 선언 추가: `b48d6`(WORD) `b4936`(LONG LONG WORD). (3) 도달 못한 분기 결과 덮기 위한 hint: `b442e` 음수 LONG, `e62ce`/`e62e0` 올림 있는 BCD, `288c` Clear(부모 LONG `270e`), 표 판정기 직사각형(`b4780` `b47a4` `b48ec` Set = 겹침). 처음 1,562 → 1,592 fixture, 실패 3 → 0. 남은 `unreachable outcomes`: `b46ac → b46bc`(Set)만 — 아이템 처리기 중 C Set을 돌려주는 것은 FR2h 범위라 V1에서 닿지 않는다(단위 시험은 합성 처리기로 덮음).
- `engine/tests/animation_machine_objects_fr2_test.cpp` 수작성 규칙 추가(생성 구역·생성기 불변): 음수 WORD 인덱스 `b4680`(D1.W × c = 8004) `b4780`(WORD 90 = fff8) `b4aca`(fff8)를 별도 합성 ROM 위치로, `1c1f4`의 `MULU.W` 상위 WORD, `e9942` 음수 인덱스(A1 = 100000, D7.W = ffff → 쓰기 장치 오류), `b4936`의 pop한 A6.
- `tools/verify_animation_machine_stage_event.py`(계약 결정 9의 후속; 핀은 `CPP_PINS` `animation_machine.cpp` `eadc97b0…`, `animation_machine_internal.h` `522199f9…`로 갱신, 이전 값은 주석에 있음. stage_event_ops도 같은 핀 갱신): `e97d8` 계산 대상 16개(D0.W = ce..dd → e991c..e9958)의 이전 기대는 모두 `unsupported animation machine PC`였다. FR2a 뒤 FR2a 시작 3개(`e991c` `e9930` `e993c`)는 native가 계산 점프 *앞*(`e97e0`)에서 거부한 guard phase 앞의 phase까지만 비교하고 target까지 stop으로 도달하는 `superseded_FR2a_routing_boundary` 행으로, 나머지 13개는 FR2a의 `unsupported animation objects fr2 PC`로 바꿨다(C++ 단위 시험과 같은 분류; native 불일치 아님, 같은 접근을 거부하는 같은 종류의 검사). 결과 560 조건·guard 117은 그대로.
- 실행부(`engine/src`)는 수정하지 않았다.

## block 목록

[F] scratch `starts_a.txt`(SHA256 `1407bd08e2148fce51fa1dba8b962fa7b3da2747214d6e9a8ae10215d334fe99`)와 같다.

- **`9ee6..9ef2`(1)**: `9ee6`
- **`9ef8..9f24`(2)**: `9ef8 9f12`
- **`a770..a7e0`(9)**: `a770 a772 a77a a784 a788 a796 a7ac a7c0 a7c2`
- **`a8ee..a8f8`(1)**: `a8ee`
- **`1c1f4..1c238`(3)**: `1c1f4 1c230 1c232`
- **`1c8a4..1c8f0`(8)**: `1c8a4 1c8ac 1c8b8 1c8ba 1c8c8 1c8ce 1c8e8 1c8ee`
- **`b33d8..b3460`(12)**: `b33d8 b33e2 b3400 b3428 b342e b3434 b343a b3448 b344e b3454 b3458 b345e`
- **`b4334..b433c`(2)**: `b4334 b433a`
- **`b4354..b43de`(13)**: `b4354 b4364 b4374 b437a b4380 b4388 b4396 b439a b43ac b43ba b43be b43d2 b43d8`
- **`b442e..b4464`(8)**: `b442e b4434 b4436 b4440 b444a b444e b4458 b445e`
- **`b4664..b466c`(1)**: `b4664`
- **`b4680..b46be`(7)**: `b4680 b4694 b469e b46a2 b46ac b46b4 b46bc`
- **`b46c0..b46f6`(3)**: `b46c0 b46d6 b46dc`
- **`b4760..b4806`(23)**: `b4760 b4764 b476a b4772 b4780 b478e b4792 b4796 b47a4 b47b2 b47b6 b47ba b47c2 b47ce b47d0 b47dc b47de b47e4 b47ea b47f4 b47f8 b47fe b4804`
- **`b489e..b4a24`(42)**: `b489e b48ac b48b4 b48b8 b48ba b48be b48ca b48d2 b48d6 b48dc b48e8 b48ec b491a b4922 b4936 b4942 b494c b4950 b4958 b4962 b496c b4980 b498a b499e b49a8 b49b0 b49b8 b49be b49c2 b49c8 b49da b49e4 b49ec b49f2 b49fc b4a06 b4a0c b4a10 b4a14 b4a18 b4a1c b4a22`
- **`b4ab0..b4ab6`(1)**: `b4ab0`
- **`b4aca..b4ad4`(1)**: `b4aca`
- **`c0ace..c0ba8`(18)**: `c0ace c0ad6 c0aec c0b04 c0b0e c0b12 c0b24 c0b4c c0b52 c0b58 c0b64 c0b6e c0b82 c0b8c c0b92 c0b98 c0ba0 c0ba6`
- **`c1d2e..c1d34`(1)**: `c1d2e`
- **`e5580..e5614`(16)**: `e5580 e558a e5596 e559e e55a0 e55a4 e55ae e55b8 e55c6 e55d0 e55e2 e55ea e55ec e55fa e5600 e5606`
- **`e62a8..e62ec`(8)**: `e62a8 e62b0 e62ba e62c2 e62cc e62ce e62e0 e62ea`
- **`e63ec..e63fa`(3)**: `e63ec e63f2 e63f8`
- **`e6516..e6570`(12)**: `e6516 e6522 e652a e652e e6538 e6540 e654c e6552 e6556 e655c e6566 e6568`
- **`e6582..e65dc`(12)**: `e6582 e6584 e658c e6596 e659a e65ae e65b0 e65b8 e65ba e65c0 e65c2 e65da`
- **`e693a..e6952`(2)**: `e693a e694c`
- **`e991c..e995c`(7)**: `e991c e9922 e9930 e993c e9942 e9952 e9956`
- **`e9b5a..e9b8a`(2)**: `e9b5a e9b72`
