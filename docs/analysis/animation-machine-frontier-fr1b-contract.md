# frontier 단위 FR1b(IO frontier `b30f6` `5a376` `de376` `de024` + 인접 잎 `b97c0` `515fc`) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. 범위는 FR1 계약(`animation-machine-frontier-fr1-contract.md`) 끝 절 "FR1b 명세"의 root 4개와, FR1a 뒤 IO 재실행 frontier(`ioA/frontier.json`)에서 FR1b와 붙어 있는 작은 잎 2개(결정 2)다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 코드와 고정 표는 모두 `<100000`이라 CPU 주소와 파일 오프셋이 같다. bank 창 읽기 `20000c` `20017c` `2001d0`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `958d66a`(branch `claude/frontier-units`, FR1a 커밋). routing 기준 `engine/src/animation_machine.cpp`(FR1a routing 포함).
- [F] frontier 입력: FR1a 뒤 IO 재실행 `/Users/start/Workspce/ms5-scratch/fr1/ioA/frontier.json`(SHA256 `ad4e7325d613863431df7122b8db1f523bd0fbb3b8acae22eb56f6090e033ea2`, frontier PC 11개).
- [F] 정적 디코드: capstone M68000, FR1 계약과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, `MOVE.L #imm,(A6)` 설치 값, 범위 밖에서 들어오는 실제 JSR/BSR 대상). routing된 PC, `RTS`, `TRAP`, `JMP (An)`에서 멈춘다. `28ae` 자식 값은 기록만 한다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr1b/`
  - `tools/`: FR1 scratch의 `hroute.py` `fclos.py` `unit_fr1.py` `refs.py` `xref.py` `probe_scan.py`를 경로만 바꿔 복사(`unit_fr1.py`의 `FR1PART=b` 묶음에 `b97c0` `515fc` 진입과 `e9114` 진입을 더함), `longref.py`(범위 안 PC와 같은 LONG 상수 검색), `callers.py`(현재 routing된 코드 중 FR1b 시작을 참조하는 곳), `leafscan.py`(출구 callee 안의 routing 밖 분기 대상), `disgroup.py`(묶음 디코드).
  - `starts_b.txt`(시작 211개) SHA256 `3b1c05b3c069d9a1f4f3d255e45048f2ab6495e5509fe88cedabe157a8d55574`, `unit_b2.out`(block별 디코드·전체 디코드).
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] FR1a가 routing된 현재 기준으로 FR1 계약의 FR1b 규칙(root `b30f6` `5a376` `de376` `de024`)을 다시 돌렸다. 시작 199개, 범위 9개, 이어 붙인 바이트 1956, `starts_b.txt` SHA256 `f396240016f4a67f8c433e8d4d39e4970692f5bb8be6bef1150bbdaa9857f000`로 FR1 계약 값과 같다(FR1a와 겹침 0, FR1a가 FR1b 출구를 바꾸지 않음).
- [F] **`5a59c`의 LONG 표 `5a5ba`**(`5a0ae 5a1c4 5a376 5a460`)는 FR1 메인 결정대로 진입으로 넣지 않는다(결정 3). 값은 `MOVE.L A0,(A6)`로 설치만 된다.
- [F] **인접 잎 2개 추가(결정 2).** IO 재실행 frontier에서 실행 수 3인 PC 중 FR1b·FR1a 호출 그래프에 바로 붙은 작은 잎을 넣는다.
  - `b97c0`(node callback, U05 `b9740 MOVE.L #b97c0,(A6)`가 설치; FR1a `b975e`와 같은 꼴의 짝): 10 block, `b97c0..b9822`.
  - `515fc`(U14 `50da8 BSR.W`의 진입, FR1a `515e0` 목록 반복의 형제: `LEA 5160e(PC),A0; BRA.B 515e0`): 1 block, `515fc..51602`.
  - `d13b4`(FR1a `d131a`의 `2986` 자식)는 다시 잰 closure가 67 block(`4941e..4945e` `494c0..4950e` `d13b4..d159e` `d2206..d224c`)이라 넣으면 278 > 약 220이다. 넣지 않고 다음 frontier로 둔다. `4e68e`(14 실행, 1,243 명령) `c0ace`(b3dbc 처리기) `e5580`(46 block) `bc08c`(FR1c)도 같은 이유로 범위 밖이다.
- [F] **외부 진입 `e9114`(결정 4).** ROM 전체 분기 검색(`xref.py`)에서 `e9114`(`e9112 MOVEQ #ff,D0` 바로 뒤의 `LEA 5e30(A5),A1`)가 `d6664 JSR e9114.l`과 `e9106 JSR e9114(PC)`(둘 다 routing 밖)의 대상이다. 이후 그 호출자를 넣는 단위가 이 단위 내부 PC로 끝나지 않도록 `e9114`를 block 시작으로 둔다(`e9112`는 `MOVEQ #ff,D0` 한 명령 block, fall-through `e9114`).
- [F] 최종: **211 block**, 11 범위, 명령 477, 짝수 PC 1030(내부 819), 이어 붙인 바이트 2060, SHA256 `f3d0d8ed773006487f2833cb49e3e937c53320704ef163ee8f1a7cd7962d6b68`.

| root(진입) | block | 명령 | 범위 |
| --- | --- | --- | --- |
| `b30f6`(+ `e9114`) | 87 | 180 | `b30ba..b336a` `b3460..b3484` `e9112..e9148` |
| `5a376` | 40 | 73 | `5a376..5a460` `5a54e..5a5ba` |
| `de376` | 18 | 40 | `ddfdc..de00c` `de376..de3e6` |
| `de024` | 67 | 190 | `ddfdc..de00c` `de024..de260` `de2b6..de31e` `de3ae..de3e6` |
| `b97c0` | 10 | 19 | `b97c0..b9822` |
| `515fc` | 1 | 2 | `515fc..51602` |
| 합(`de376`·`de024` 겹침 12 제외) | **211** | 477 | 11 범위 |

`de376`·`de024` 겹침 12 block: `ddfdc ddfea ddfee ddff4 de00a de3ae de3b2 de3c2 de3c6 de3ce de3e0 de3e4`.

## 요약

- [F] **범위·block 수**(11 범위, 합 211):

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `515fc..51602` | 6 | `83533e46e5bc4f9b20e60ca8e3bcc793bbf37d17af3c1102ca3f9ce9dbfcf245` | 1 | 3 |
| `5a376..5a460` | 234 | `b40fa049cc1c974e2a276361354243ad4ee97df6b4ee62c3a793e41ce0bff9b0` | 26 | 117 |
| `5a54e..5a5ba` | 108 | `4313e82d039afeb3dca3614ddbff02213a0751309cb78121821ea5a40f18bfbe` | 14 | 54 |
| `b30ba..b336a` | 688 | `4529700726f10b63315513626c39865f35249a4c23060d1521c638b940ecc124` | 75 | 344 |
| `b3460..b3484` | 36 | `ccde97acb2265a2e6f4222673dfff69bc90b05aeac24045d81e61525d9a89beb` | 5 | 18 |
| `b97c0..b9822` | 98 | `ea9f1b986bb23be66fc28a2b797e74a686df25ad83c8c8f308b4f4c19c9efb5f` | 10 | 49 |
| `ddfdc..de00c` | 48 | `73e414c2d10bac8c79fc157c1cf8f13bc7a274933a2359c22f2567cad3a10987` | 5 | 24 |
| `de024..de260` | 572 | `e8e052b8c97eb59cfb5c8bd531ab44477338d98554f8dffca1886b76fda4958a` | 46 | 286 |
| `de2b6..de31e` | 104 | `c6d3ec1014779552fca1710f812445bb238caf93c1b4351f199bf9a17290766f` | 9 | 52 |
| `de376..de3e6` | 112 | `43a25ea90142baf79b660683a20948c44298f76fdae6f799470d07e322c7bd22` | 13 | 56 |
| `e9112..e9148` | 54 | `beb10bb2eb9acfd8952b07e3fbf061b6588bcfdf59abf52d207c2e460590b945` | 7 | 27 |
| 합계 FR1b | 2060 | 이어 붙인 바이트 `f3d0d8ed773006487f2833cb49e3e937c53320704ef163ee8f1a7cd7962d6b68` | **211** | 1030(내부 819) |

- [F] closure가 11 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 연속 Bcc 묶음 없음, X 소비(ADDX/SUBX/ROX) 없음, `TRAP` 없음, 계산 점프 없음(`5a59c`의 PC 상대 index는 자료 읽기). DBRA 없음(`5a596` 반복은 `SUBQ.W #1,D7; BEQ`). **PVC port 쓰기 2개**: `de05e`의 `MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l`(앞의 `MOVE.W #0,-7ff0(A5)`와 함께 공유 `am_zero_bank`와 같은 세 쓰기, 같은 순서; bank 결과 `200000`).
- [F] **현재 routing과의 관계**: 11 범위의 짝수 PC는 모두 routing 밖이다(겹침 0). 경계 이웃: `515fa`(FR1a `515f8` block의 `BRA.B`)·`51602`(FR1a block), `5a374`(자료)·`5a460`(표 `5a5ba`의 넷째 상태 `MOVE.L #5a460,98(A6)`, routing 밖), `5a54a`(`5a460` 상태의 `BRA.W 5a9c2`, routing 밖)·`5a5ba`(LONG 표), `b30b8`(사각형 자료 `b30aa..b30ba`)·`b336a`(`28ae` 자식 값, routing 밖 코드), `b345e`(routing 밖 `RTS`)·`b3484`(FR1a가 읽는 종류 기록 표), `b97be`(FR1a `RTS`)·`b9822`(사각형 자료), `ddfda`(HUD 표 끝 `ffff`)·`de00c`(`43ffc` 인자 자료), `de022`(자료)·`de260`(routing 밖 형제 `MOVE.W #0,78(A6); MOVE.L #de26c,(A6)`), `de2b4`(형제 코드 안)·`de31e`(LONG 자료), `de374`(자료 `ffff`)·`de3e6`(WORD/LONG 목록 자료), `e9110`(routing 밖 `e910e JSR e90f2(PC)`의 확장 word)·`e9148`(routing 밖 형제 `MOVEQ #0,D0; MOVE.B 5e3c(A5),D0; RTS`).
- [F] **나가는 곳은 모두 routing돼 있다**: callee `101c` `28ae` `35f0` `3af8` `8c16` `8da2` `caf0` `cd58` `16fac` `16ff8` `17012` `1861a` `1ab02` `43e34` `43ea4` `43ffc` `490ba` `491b6` `49214` `493bc` `4945e` `496c2` `4970a` `49a58` `49f8c` `49fc6` `4ae4a` `4b54e` `4be2c` `5ab5a` `c6a96` `e7c16` `e89da`, 출구 `JMP 2a00` 3곳(`b30ee` `b3352` `b3362`), `JMP 2a24`(`b981a`), `BRA.W 5a9c2` 3곳(`5a41a` `5a45c` `5a5b4`), `BNE.W 5a802` 3곳(`5a3e4` `5a43a` `5a574`), `BRA.W e932c`(`e9140`), `BRA.B 515e0`(`515fc`). 모두 block 시작이다(`5a9c2` `5a802` N13, `e932c` stage_event, `515e0` FR1a).
- [F] **참조**(ROM 전체 직접 분기·LONG 상수, scratch `xref.py` `refs.py` `longref.py` `callers.py`): 범위 밖에서 들어오는 실제 분기·설치·LONG은 모두 block 시작이다 — `515fc`(`50da8` U14, `51466` `BSR.W`), `5a376`(N13 `59f0c` `5a7f4 MOVE.L`, 표 `5a5c2`), `5a54e`(`5a070` `5a1b0` `5a2fc MOVE.L`, routing 밖 형제 상태), `b30f6`(LONG 표 `e8e90`, [I] 객체 종류 표), `b97c0`(U05 `b9740`), `de024`(C3 `c5da MOVEA.L`, `28ae` 자식), `de376`(C3 `c6de`), `de2b6`(routing 밖 형제 `de29c BMI.W`), `e9112`(N15 `76eee`, N23 `c3ba6`, U19 `d831e` 외 routing 밖 `JSR` 40곳 이상), `e9114`(`d6664` `e9106 JSR`). 내부 PC로 보이는 분기(`b331e` ← `b3386`, `ddff1` ← `ddf84`, `de04c` ← `de09e`, `de0aa` ← `de0b0`, `e9117` ← `e37a6`)는 모두 명령 중간이나 자료의 가짜 디코드다. 내부 PC와 같은 LONG 상수 `000b9800` `000de000`은 자료 상수다 [I](설치·분기 명령이 아님).
- [I] 의미: `b30f6`은 던져지는 물체 객체(WORD `7c` → 속도 LONG `82`, `c6a96` 등록, bank 창 `20017c` 애니메이션, `28ae` 자식 `b336a` `b33d8`, 상태 `b31dc`(대상 추적 `b3460`/`493bc`)·`b3246`(낙하 `e9112`, `4be2c`, 착지 뒤 `28ae` 자식 `d1d08` `d1d38`·`4970a` 효과), 화면 밖이면 삭제), `5a376`은 N13 객체 `59ea2`의 상태 하나(`490ba` 애니메이션 선택, 상태 `5a3e4` `5a41e` `5a43a` `5a54e` `5a574`, 표 `5a5ba`에서 다음 상태를 고름), `de024`는 demo/title E 영역 연출(화면 정리 `43ffc` `caf0` `e7c16`, 색 `8c16`, 배경 `8da2`·`16fac`·`16ff8`·`1861a`·`17012`, 스프라이트 `cd58` 이동 3단계, 로고 표 `de34e`), `de376`은 title 화면(`101c` 소리, `ddfdc` 문자열 `e89da`·`35f0`, 표 `de3e6` 스프라이트 반복, 부모 BYTE `62` := 1), `b97c0`은 U05 객체의 다른 끝 상태, `515fc`는 HUD 목록 `5160e`. 이름은 확정하지 않는다.

## 공통 규칙·native 검증 계획

FR1 계약 "공통 규칙·native 검증 계획"을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr1b.cpp`, 함수 `animation_objects_fr1b_block`. 오류 문자열은 `unsupported animation objects fr1b PC`(범위 안 내부 PC 직접 진입), `objects fr1b caller requires known carry`(C 소비 block에 Unknown C; 소비자 11개)다. DIVU·기타 단위 전용 오류는 없다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(11 범위, FR1a 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 11개, 결정 5), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, test 목록 실행 줄, 시험 target; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** routing 밖 실행 PC는 없다(모든 출구가 routing됨). 기존 시험이 stop으로만 보던 PC(`515fc`(U14), `e9112`(N15 N23 U19), `b97c0`(U05 설치 값), `de024` `de376`(C3 레지스터 값))는 stop 판정이 routing보다 먼저라 그대로 통과한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다(F4 관례).
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): 기대 오류 fixture마다 실패 PC를 적고, 진입 PC와 다르면 같은 상태를 stop = 실패 PC로 실행해 정확히 그 PC에서 멈추는지 함께 확인한다.
- **자료 읽기**(live bus, F1 결정 3, 상한 검사 없음): LONG `(5a5ba + sext(WORD(4·(D0 & 3))))`(`5a59c`), LONG `20017c`(bank 창)과 LONG `(LONG 20017c + sext(WORD(4·D0.W)))`(`b316e`), LONG `2001d0`과 LONG `50(LONG 22(A6))`(`b97c0`), LONG `20000c`(bank 쓰기 뒤)와 LONG `(LONG 20000c + ec)`(`de05e`), LONG `(de34e + sext(WORD(4·WORD 78)))`(`de2cc`), WORD/LONG 목록 `(A0)+`(`de2fe` `de306` `de3c6` `de3ce`, A0 = `de3e6`). RAM 읽기: node field(A6), WORD `46(A0)`(`b31f8`), BYTE `-7fff(A5)`(`ddfdc`), BYTE `(5e30(A5) + sext(D1.W / D0.W))`(`e9126` `e9132`, 읽고 씀), LONG `c(A6)`의 BYTE `62`(`de3b2`, 씀). 단위 시험은 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `de306`/`de3ce` `MOVE.L A0,-(A7)` 뒤 `JSR cd58`(복귀 `de318`/`de3e0`), `de318`/`de3e0` `MOVEA.L (A7)+,A0`. `BSR`/`JSR (PC)` 복귀: `5a3f4`(→ `5a3f8`) `5a44a`(→ `5a44e`) `5a584`(→ `5a588`) `b31ec`(→ `b31f4`) `de3ae`(→ `de3b2`). 모두 `am_push`/`am_pop`(홀수 A7은 checked 오류).
- **PVC port.** `de05e`는 `am_zero_bank`(WORD `-7ff0(A5)` := 0, WORD `2ffff2` := `1000`, WORD `2ffff0` := 0; port 기록 2개, bank `200000`)를 쓴다. 단위 시험은 port 기록(주소·크기·값, 순서)과 PVC page·bank를 native와 비교한다.
- **정수 연산.** `MOVEQ`(LONG 부호 확장: `#e1` → `ffffffe1`, `#ff` → `ffffffff`, `#1f`), `MOVEA.W #0,An`(→ 0), `MOVE.B`/`MOVE.W` → Dn(상위 유지; `MOVEQ #ff,D1; MOVE.W #w,D1` → `ffff0000 | w`), `MOVE.L`, `EXT.L`, `LSL.L #8`(32 bit), `LSL.W #2`(WORD), `ADD.W Dn,Dn`(WORD wrap), `NEG.L`/`NEG.W`, `ASR.L #2`(부호 유지 산술 이동, UB 없이 명시 구현), `SUBI.L #4000`, `SUB.L`, `SUB.W`, `SWAP`, `ANDI.W #3`/`#ff`, `AND.B`, `SNE.B`(Z 반대면 `ff`, 아니면 0; BYTE만), `BSET.B #n`(메모리 BYTE), `CLR.B`, `SUBQ.B #1`(메모리 BYTE wrap), `SUBQ.W`/`ADDQ.W` 메모리(WORD wrap), `ADDQ.B #1,(A1,D0.W)`. 비교·분기: `BTST.B` + `BNE`/`BEQ`, `TST.W`/`TST.B` + `BEQ`/`BNE`, `TST`(`MOVE.L` Z) `BEQ`, `MOVE.L` + `BMI`(LONG N), `MOVE.W (A0)+` + `BMI`(WORD N), `SUB.W` + `BPL`(WORD N), `CMP.W 7e(A6),D0` + `BGT`(부호 D0.W > WORD), `CMPI.W #0/#14/#a/#5` + `BEQ`/`BNE`, `CMPI.B #0,-7fff(A5)` + `BEQ`, `CMPI.B #c` + `BCC`(무부호 BYTE ≥ `c`), `CMPA.L 98(A6),A0` + `BEQ.B`, `SUBQ.W #1,D7` + `BEQ`, `SUBQ.W #1,d(A6)` + `BEQ`/`BNE`. 모두 같은 block 안에서 만들고 소비한다(예외: 결정 5의 C).

## carry

- [F] **소비 block 11개**(callee가 돌려준 C를 읽음; 각 block은 `BCC`/`BCS` 하나):
  - `5a3f8 BCC.W 5a402`: `5ab5a`(N13, `49fc6`의 C를 돌려줌). Clear → `5a402`, Set → `5a3fc`.
  - `5a58e BCS.W 5a9c2`: `4945e`. Set → `5a9c2`, Clear → `5a592`.
  - `b30ea BCC.W b30f4` / `b335e BCC.W b3368` / `b9816 BCC.W b9820`: `1ab02`(밖 Set, 안 `ANDI.B #fe,CCR` Clear). Set → `b30ee` / `b3362` / `b981a`.
  - `b31f4 BCC.W b3218`: `b3460`(이 단위; `b3474` Set / `b347e` Clear). Set → `b31f8`.
  - `b3470 BCC.W b347e`: `493bc`(N15). Clear → `b347e`, Set → `b3474`.
  - `b32d8 BCC.W b32ee` / `b330a BCC.W b3320` / `b333c BCC.W b3352`: `28ae`(할당 실패 Set). Set → `b32dc` / `b330e` / `b3340`.
  - `b97fa BCC.W b980a`: `49fc6`. Set → `b97fe`.
- [F] **known C 생산**(결정 5): `b3474`(`MOVEA.L 88(A6),A0; ORI.B #1,CCR; RTS`)는 C Set, `b347e`(`ANDI.B #fe,CCR; RTS`)는 C Clear를 남긴다(`RTS`가 같은 block 안이라 통과 block이 필요 없다; 호출자 `b31ec JSR b3460(PC)`의 복귀 `b31f4`가 읽음). `b32ea` `b331c` `b334e`(`ORI.B #1,CCR`)는 C Set을 남기지만 다음 block(`b32ee BRA` `b3320 BRA` `b3352 JMP 2a00`)이 carry 보존이 아니어서 읽는 곳이 없다(B4b `2b74a` 관례: 값은 남기고 보존 목록에는 넣지 않음).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 소비자 11개뿐이다. Unknown C로 소비자에 들어오면 checked 오류다. 그 밖의 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다(`b3474` `b347e` `b32ea` `b331c` `b334e` 제외).
- [F] 다른 단위 소비자에게 C를 전달하는 `RTS`는 없다: `b30f4` `b3368` `b9820` `de05c` `de0e0` `de0f6` `de11a` `de1a6` `de202` `de25e` `de31c` `de3e4`는 dispatcher(`2ac2`)로, `de00a`는 `de3b2 MOVEA.L`로 돌아가고, `e9140`은 `BRA e932c`다. 범위 밖 호출자의 반환 C 사용도 확인했다: `515fc`는 `BRA.B 515e0`(FR1a)로 끝나 C는 FR1a `515e8 RTS`가 정한다(이 단위가 아님; 복귀 U14 `50dac`는 `RTS`). `e9112`는 `BRA e932c`로 끝나고 호출 뒤 다음 명령 `76ef4 MOVE.B` `c3bac TST.W` `d8324 TST.W` `b324c BSET`(Z만)는 C를 읽지 않는다.
- [F] C를 읽지 않는 호출: `490ba`(→ `MOVE.B D0`), `496c2` `49f8c` `43ea4` `3af8` `c6a96` `49214` `491b6` `4b54e`(→ `BTST`) `43e34` `4be2c`(→ `BTST`) `4ae4a`(→ `CMPI.W`) `4970a`(→ `ORI`) `49fc6`(`b321e` → `MOVE.L`, `b329c` → `TST.W`) `49a58`(→ `ANDI.W`) `e9112`(→ `BSET`) `101c` `43ffc` `caf0` `e7c16` `8c16` `8da2` `16fac` `16ff8` `1861a` `17012` `cd58` `e89da` `35f0`(→ `RTS`, `de00a`는 dispatcher가 아니라 `de3b2`로 감).
- [F] block 경계를 건너 다시 계산하는 flag는 없다.

## 객체 `5a376` `5a376..5a460`(26) `5a54e..5a5ba`(14)

- **`5a376`**(node callback, N13 설치): LONG `98` := `5a376`, BYTE `80` bit 1 ≠ 0 → `5a39c`, 아니면 `5a388`.
- **`5a388`** `5a39c`: A0 := `5dd3e`/`5dd88`(LEA abs), `JSR 490ba`(복귀 `5a394`/`5a3a8`). **`5a394`**: BYTE `8c` := D0.B, `BRA 5a3ac`. **`5a3a8`**: BYTE `8c` := D0.B(fall-through `5a3ac`).
- **`5a3ac`** `5a568`: `JSR 496c2`(복귀 `5a3b2`/`5a56e`).
- **`5a3b2`** `5a3c6`(설치 값) `5a41e`(설치 값) `5a558`: A1 := `5b784`/`5b7ea`/`5b66e`/`5b66e`, D0.W := `100`, `JSR 49f8c`(복귀 `5a3c2`/`5a3d6`/`5a42e`/`5a568`).
- **`5a3c2`**: `BRA 5a3d6`.
- **`5a3d6`**: BYTE `9c` := 0, BYTE `8c` −= 1(wrap), 설치 `5a3e4`(fall-through).
- **`5a3e4`** `5a43a` `5a574`(설치 값): BYTE `80` bit 0 ≠ 0 → `5a802`, 아니면 `5a3ee`/`5a444`/`5a57e`.
- **`5a3ee`** `5a444` `5a57e`: `JSR 43ea4`(복귀 +6). **`5a3f4`** `5a44a` `5a584`: `BSR.W 5ab5a`(복귀 +4).
- **`5a3f8`**(소비자): Clear → `5a402`, Set → `5a3fc`: LONG `(A6)` := `5a41e`(설치만) → `5a402`.
- **`5a402`**: D0.B := (BYTE `8c` ≠ 0 ? `ff` : 0), D1.B := (BYTE `9c` ≠ 0 ? `ff` : 0), D1.B &= D0.B, 0 → `5a41a`, 아니면 `5a414`: LONG `(A6)` := `5a3c6`(설치만) → `5a41a`.
- **`5a41a`** `5a45c`: `BRA 5a9c2`.
- **`5a42e`**: WORD `84` := `10`, 설치 `5a43a`.
- **`5a44e`**: WORD `84` −= 1, ≠ 0 → `5a45c`, 아니면 `5a456`: LONG `(A6)` := `5a54e`(설치만) → `5a45c`.
- **`5a54e`**(설치 값): D0.W := `743`, `JSR 3af8`(복귀 `5a558`).
- **`5a56e`**: 설치 `5a574`.
- **`5a588`**: `JSR 4945e`(복귀 `5a58e`). **`5a58e`**(소비자): Set → `5a9c2`, Clear → `5a592`: D7.W := 5(fall-through `5a596`).
- **`5a596`**: `JSR 49a58`(복귀 `5a59c`).
- **`5a59c`**: D0.W &= 3, D0.W += D0.W 두 번, A0 := LONG `(5a5ba + sext(D0.W))`(live bus), D7.W −= 1, 0 → `5a5b4`, 아니면 `5a5ae`.
- **`5a5ae`**: A0 = LONG `98` → `5a596`, 아니면 `5a5b4`.
- **`5a5b4`**: LONG `(A6)` := A0(설치만), `BRA 5a9c2`.

## 객체 `b30f6` `b30ba..b336a`(75) `b3460..b3484`(5) + helper `e9112..e9148`(7)

- **`b30f6`**(node callback, 표 `e8e90`): D0 := sext(WORD `7c`) << 8(32 bit), LONG `82` := D0, WORD `78` ≠ 0 → `b3114`(LONG `36` := D0), 아니면 `b310c`(LONG `3a` := D0, `BRA b3118`).
- **`b3118`**: WORD `7a` = 0 → `b3130`, 아니면 `b3120`: BYTE `15` |= 1, LONG `36` := −LONG `36`(32 bit), D0 := 그 값(fall-through `b3130`).
- **`b3130`**: WORD `68` := `8800`, WORD `1e` := `8800`, D0.W := `5e`, D1.W := 1, D2.B := 0, `JSR c6a96`(복귀 `b314e`).
- **`b314e`**: WORD `76` ≠ 0 → `b3164`(WORD `54` := `64`, D0.W := 1), 아니면 `b3156`(WORD `54` := `c8`, D0.W := 4, `BRA b316e`).
- **`b316e`**: A0 := A6 + `26`, WORD `20` := `15b`, LONG `22` := LONG `20017c`, A0 := A6 + `26`, D1.W := D0.W, D1.W += D1.W 두 번, A1 := LONG `20017c`, A1 := LONG `(A1 + sext(D1.W))`, D0.W := `100`, `JSR 49f8c`(복귀 `b319e`).
- **`b319e`** `b31c0`: A0 := `b336a`/`b33d8`, D0.W := `a`, `JSR 28ae`(복귀 `b31ae`/`b31d0`).
- **`b31ae`**: D0 := 0, D1.W := 0, `JSR 49214`(복귀 `b31ba`). **`b31ba`** `b31d0`: `JSR 491b6`(복귀 `b31c0`/`b31d6`).
- **`b31d6`**: 설치 `b31dc`.
- **`b31dc`**(설치 값): WORD `76` = 0 → `b3218`, 아니면 `b31e4`: WORD `80` = 0 → `b3218`, 아니면 `b31ec`: WORD `80` −= 1, `JSR b3460(PC)`(복귀 `b31f4`).
- **`b31f4`**(소비자): Clear → `b3218`, Set → `b31f8`: D1 := LONG `82`, D0.W := WORD `46(A0)` − WORD `46`, N = 0 → `b320c`, 아니면 `b3208`: D1 := −D1, D0.W := −D0.W(fall-through `b320c`).
- **`b320c`**: 부호 D0.W > WORD `7e` → `b3218`, 아니면 `b3214`: LONG `3a` := D1(fall-through `b3218`).
- **`b3218`**: `JSR 43ea4`(복귀 `b321e`). **`b321e`**: `JSR 49fc6`(복귀 `b3224`).
- **`b3224`**: D0 := LONG `72`, 0 → `b3234`, 아니면 `b322c`: A0 := D0, `JSR 4ae4a`(복귀 `b3234`).
- **`b3234`**: D0.W = 0 → `b3242`, 아니면 `b323c`: LONG `(A6)` := `b3246`(설치만) → `b3242`.
- **`b3242`**: `BRA b30ba`. **`b30ba`**: `JSR 4b54e`(복귀 `b30c0`).
- **`b30c0`**: BYTE `61` bit 7 = 0 → `b30d0`, 아니면 `b30ca`: LONG `(A6)` := `b3246`(설치만) → `b30d0`.
- **`b30d0`** `b32a2`: WORD `76` ≠ 0 → `b30e0`/`b32b2`(A0 := `b30b2`), 아니면 `b30d8`/`b32aa`(A0 := `b30aa`, `BRA b30e4`/`b32b6`).
- **`b30e4`** `b3358`: `JSR 1ab02`(복귀 `b30ea`/`b335e`). **`b30ea`** `b335e`(소비자): Clear → `b30f4`/`b3368 RTS`, Set → `b30ee`/`b3362 JMP 2a00`.
- **`b3246`**(설치 값): `JSR e9112`(복귀 `b324c`).
- **`b324c`**: BYTE `61` |= 8, LONG `36` −= `4000`, LONG `82` := LONG `3a`, `JSR 4be2c`(복귀 `b3266`).
- **`b3266`**: BYTE `15` bit 7 = 0 → `b3284`, 아니면 `b3270`: D0 := −LONG `82`, LONG `3a` := D0, D0 := LONG `36` ASR 2, LONG `36` −= D0(fall-through `b3284`).
- **`b3284`**: WORD `76` ≠ 0 → `b3296`(WORD `86` := `14`), 아니면 `b328c`(WORD `86` := `1e`, `BRA b329c`).
- **`b329c`**: `JSR 49fc6`(복귀 `b32a2`).
- **`b32b6`**: D0.W := WORD `86`, 0 → `b3358`, 아니면 `b32be`: D0.W −= 1, D0.W ≠ `14` → `b32f2`, 아니면 `b32c8`.
- **`b32f2`**: D0.W ≠ `a` → `b3324`, 아니면 `b32fa`. **`b3324`**: D0.W ≠ 5 → `b3358`, 아니면 `b332c`.
- **`b32c8`** `b32fa` `b332c`: A0 := `d1d08`/`d1d08`/`d1d38`, D0.W := `1e`, `JSR 28ae`(복귀 `b32d8`/`b330a`/`b333c`).
- **`b32d8`** `b330a` `b333c`(소비자): Clear → `b32ee`/`b3320`/`b3352`, Set → `b32dc`/`b330e`/`b3340`: D0.W := `60`/`30`/0, D1.W := 0, `JSR 4970a`(복귀 `b32ea`/`b331c`/`b334e`).
- **`b32ea`** `b331c` `b334e`: C Set(fall-through `b32ee`/`b3320`/`b3352`). **`b32ee`** `b3320`: `BRA b3358`. **`b3352`**: `JMP 2a00`.
- **`b3460`**(`JSR (PC)` 대상): D0 := LONG `88`, N = 1 → `b347e`, 아니면 `b3468`: A0 := D0, `JSR 493bc`(복귀 `b3470`).
- **`b3470`**(소비자): Clear → `b347e`, Set → `b3474`: A0 := LONG `88`, C Set, `RTS`. **`b347e`**: C Clear, `RTS`.
- **`e9112`**: D0 := `ffffffff`(fall-through `e9114`).
- **`e9114`**(외부 `JSR` 진입): A1 := A5 + `5e30`, D1 := BYTE `6b`(상위 0), 무부호 D1.B ≥ `c` → `e912a`, 아니면 `e9126`: BYTE `(A1 + sext(D1.W))` −= 1(fall-through `e912a`).
- **`e912a`**: 무부호 D0.B ≥ `c` → `e913e`(D0 := `ffffffff`), 아니면 `e9132`: D0.W &= `ff`, BYTE `(A1 + sext(D0.W))` += 1, `BRA e9140`.
- **`e9140`**: BYTE `6b` := D0.B, `BRA e932c`.

## U05 끝 상태 `b97c0` `b97c0..b9822`(10)

- **`b97c0`**(설치 값, U05 `b9740`): A0 := A6 + `26`, WORD `20` := `203`, LONG `22` := LONG `2001d0`, D0.W := `100`, A0 := A6 + `26`, A1 := LONG `22`, A1 := LONG `50(A1)`(bank 창), `JSR 49f8c`(복귀 `b97e8`). **`b97e8`**: 설치 `b97ee`.
- **`b97ee`**(설치 값): `JSR 43e34`(복귀 `b97f4`). **`b97f4`**: `JSR 49fc6`(복귀 `b97fa`). **`b97fa`**(소비자): Clear → `b980a`, Set → `b97fe`: WORD `76` := 0, LONG `(A6)` := `b970e`(설치만, U05 block) → `b980a`.
- **`b980a`**: A0 := `ba3d6`, `JSR 1ab02`(복귀 `b9816`). **`b9816`**(소비자): Clear → `b9820 RTS`, Set → `b981a JMP 2a24`.

## HUD 목록 형제 `515fc..51602`(1)

- **`515fc`**: A0 := `5160e`, `BRA.B 515e0`(FR1a).

## E 영역 `ddfdc..de00c`(5) `de024..de260`(46) `de2b6..de31e`(9) `de376..de3e6`(13)

- **`ddfdc`**(`BSR` 대상): A0 := `ddf7c`, BYTE `-7fff(A5)` = 0 → `ddfee`, 아니면 `ddfea`: A0 := `ddf5e`(fall-through `ddfee`).
- **`ddfee`**: `JSR e89da`(복귀 `ddff4`). **`ddff4`**: D0.W := `717b`, D1.W := `e317`, D2.W := 1, D3.W := 1, `JSR 35f0`(복귀 `de00a`). **`de00a`**: `RTS`.
- **`de024`**(node callback, C3 `28ae` 자식) `de11c` `de380`: A0 := 0(MOVEA.W), `JSR 43ffc`(복귀 `de02e`/`de126`/`de38a`).
- **`de02e`** `de38a`: `JSR caf0`(복귀 `de034`/`de390`). **`de034`** `de126` `de390`: `JSR e7c16`(복귀 `de03a`/`de12c`/`de396`).
- **`de03a`** `de0be` `de0f8` `de136` `de3a0`: D0 D1 D2 := `ffffffe1`/0/`ffffffe1`/0/0, D3 := 0/8/8/0/0, `JSR 8c16`(복귀 `de048`/`de0cc`/`de106`/`de144`/`de3ae`).
- **`de048`** `de0cc` `de0e2` `de106`: WORD `76` := 2/`3c`/`3c`/`14`, 설치 `de054`/`de0d8`/`de0ee`/`de112`.
- **`de054`** `de0d8` `de0ee` `de112`(설치 값): WORD `76` −= 1, 0 → `de05e`/`de0e2`/`de0f8`/`de11c`, 아니면 `de05c`/`de0e0`/`de0f6`/`de11a RTS`.
- **`de05e`**: D0.W := `3b`, `am_zero_bank`(WORD `-7ff0(A5)` := 0, WORD `2ffff2` := `1000`, WORD `2ffff0` := 0), A0 := LONG `20000c`, D0.W <<= 2, A0 := LONG `(A0 + sext(D0.W))`, `JSR 8da2`(복귀 `de08a`).
- **`de08a`**: A0 := `de00c`, `JSR 43ffc`(복귀 `de094`). **`de094`**: A0 := `109156`, `JSR 16fac`(복귀 `de0a0`).
- **`de0a0`**: A1 := `de01c`, A2 := 0, D0 := 0, D1 := `1f`, `JSR 16ff8`(복귀 `de0b2`). **`de0b2`**: `JSR 1861a`(복귀 `de0b8`). **`de0b8`**: `JSR 17012`(복귀 `de0be`).
- **`de12c`** `de396`: A0 := `ddf08`, `JSR 8da2`(복귀 `de136`/`de3a0`).
- **`de144`**: WORD `7a` := 0, WORD `7c` := `1b8`, WORD `76` := `1e`, 설치 `de15c`.
- **`de15c`** `de1b4` `de210`(설치 값): D1 := `ffff1500`, D7 := `2152`, D0 := `a00180`, D5 := 0, `JSR cd58`(복귀 `de176`/`de1ce`/`de22a`).
- **`de176`** `de1ce` `de22a`: D1 := `ffff1600`, D7 := `2952`, D0 := WORD `7a` << 16 | WORD `7c`(MOVE.W, SWAP, MOVE.W), D5 := 0, `JSR cd58`(복귀 `de194`/`de1ec`/`de248`).
- **`de194`**: WORD `7a` += 8; **`de1ec`**: WORD `7a` −= 4, WORD `7c` −= 4; **`de248`**: WORD `7a` += 6, WORD `7c` += 6; 이어 WORD `76` −= 1, ≠ 0 → `de1a6`/`de202`/`de25e RTS`, 아니면 `de1a0`/`de1fc`/`de258`: LONG `(A6)` := `de1a8`/`de204`/`de2b6`(설치만) → `RTS` block.
- **`de1a8`** `de204`(설치 값): WORD `76` := `1e`/`14`, 설치 `de1b4`/`de210`.
- **`de2b6`**(설치 값): D0.W := `74b`, `JSR 3af8`(복귀 `de2c0`). **`de2c0`**: WORD `78` := 0, 설치 `de2cc`.
- **`de2cc`**(설치 값): A0 := `de34e`, D1 := `ffff1800`, D7.W := WORD `78`, D7.W += D7.W 두 번, D7 := LONG `(A0 + sext(D7.W))`, N = 1 → `de3ae`, 아니면 `de2e6`: D0 := `a00180`, D5.W := `1000`, `JSR cd58`(복귀 `de2f6`).
- **`de2f6`**: WORD `78` += 1, A0 := `de3e6`(fall-through `de2fe`).
- **`de2fe`** `de3c6`: D1 := `ffff0000` | WORD `(A0)`, A0 += 2, WORD bit 15 = 1 → `de31c`/`de3e4 RTS`, 아니면 `de306`/`de3ce`: D7 := LONG `(A0)`, A0 += 4, D0 := `a00180`, D5 := 0, push LONG A0, `JSR cd58`(복귀 `de318`/`de3e0`).
- **`de318`** `de3e0`: A0 := pop LONG, `BRA.B de2fe`/`de3c6`.
- **`de376`**(node callback, C3 `28ae` 자식): D0.B := 2, `JSR 101c`(복귀 `de380`).
- **`de3ae`**: `BSR.W ddfdc`(복귀 `de3b2`). **`de3b2`**: A0 := LONG `c`, BYTE `62(A0)` := 1, 설치 `de3c2`.
- **`de3c2`**(설치 값): A0 := `de3e6`(fall-through `de3c6`).

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다. index 범위는 원본에 상한 검사가 없어 [I]로 적는다.

| 표 | 범위 | 읽는 곳 | 내용 |
| --- | --- | --- | --- |
| 상태 LONG | `5a5ba..5a5ca` | `5a59c`(index = (`49a58` D0 & 3)·4) | `0005a0ae 0005a1c4 0005a376 0005a460`(설치 값; `5a376`만 이 단위, 결정 3) |
| bank LONG | CPU `20017c` `2001d0` `20000c` | `b316e`, `b97c0`, `de05e` | 물리 `200000` bank: `20017c` = `002c44f0`(LONG `+4` = `002c450c`, `+10` = `002c4610`), `2001d0` = `002d450e`(LONG `50` = `002d4808`), `20000c` = `002003d0`(LONG `+ec` = `00201eb8`). `de05e`는 읽기 전에 bank를 `200000`으로 바꾼다. 물리 `300000` bank의 `20017c` `2001d0`은 `01000000` `01868260`([I] 이 bank에서는 쓰이지 않음) |
| 로고 LONG | `de34e..de376` | `de2cc`(WORD `78` = 0..9 [I]) | `00012952 00014152 00015952 00017152 00018952 0001a152 0001b952 0001d152 0001e952 ffffffff`(끝 음수 → `de3ae`) |
| 스프라이트 목록 | `de3e6..de41a` | `de2fe` `de306` `de3c6` `de3ce` | (WORD, LONG) 6쌍 `1400 00001952` `1100 00000152` `1200 00000952` `1300 00001152` `0d00 00024952` `0d00 00025152`, 끝 `ffff` |
| 사각형 | `b30aa..b30ba`, `ba3d6..ba3de` | `1ab02` 인자(`b30d8` `b30e0` `b32aa` `b32b2`, `b980a`) | `ffc0ffd0 00800060`(둘 다), `ffd0ff00 00600200` |

- [F] **callee에게 넘기기만 하는 자료**(이 단위는 읽지 않음): `490ba`의 A0 = `5dd3e` `5dd88`; `49f8c`의 A1 = `5b784` `5b7ea` `5b66e`, bank 창 LONG; `e89da`의 A0 = `ddf7c` `ddf5e`(문자열 `SNK PLAYMORE 2003`); `8da2`의 A0 = `ddf08`·bank 창 LONG; `43ffc`의 A0 = 0 / `de00c`; `16fac`의 A0 = `109156`; `16ff8`의 A1 = `de01c`; `28ae` 자식 값 `b336a` `b33d8` `d1d08` `d1d38`(다음 frontier); `cd58`의 D0 D1 D5 D7; `35f0`의 D0..D3; `c6a96`의 D0..D2; `4970a`의 D0 D1; `3af8`의 `743` `74b`; `101c`의 D0.B = 2.

## 경계·routing 밖 출구

- [F] routing 밖 실행 PC: 없다. 단위 안 계산 착지도 없다(계산 점프 없음).
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 15개: `b30f4` `b3368` `b3474` `b347e` `b9820` `de00a` `de05c` `de0e0` `de0f6` `de11a` `de1a6` `de202` `de25e` `de31c` `de3e4`.
- [F] 공유 진입: `e9112`는 N15 N23 U19와 routing 밖 40곳 이상이, `e9114`는 `d6664` `e9106`이, `515fc`는 U14 `50da8`와 `51466`이, `ddfdc`는 `de3ae`가(이 단위), `de2b6`은 형제 `de29c`가 쓴다. 이후 그 코드를 넣는 단위는 이 단위의 block 시작으로 끝나야 한다.
- [F] **native 정지 규칙 주의**(V1·실제 ROM 차분): 출구 `8c16`은 C++가 한 block(`animation_exit`)으로 처리하는 잎이라 내부 분기 대상 `8c2a..8ca6`이 routing 밖으로 보인다(scratch `leafscan.py`: 출구 39개 중 이런 잎은 `8c16`뿐; `4ae4a` `5a802`가 보이는 routing 밖 대상은 그 executor의 block 경계). native "첫 routing 밖 PC" 정지 조건은 `8c16 < pc <= 8ca6`를 내부로 취급한다(FR1 spec 수정과 같음).

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 자연 node·RAM 기록, LONG `c(A6)` := 자연 node, LONG `88(A6)` := 자연 node 또는 음수, 표 index WORD `78`, BYTE `6b`, BYTE `-7fff(A5)`, `de306`/`de3ce`/`de318`/`de3e0`의 스택 LONG, PC).
- [I] IO 관측 상태가 이 단위의 실제 진입 상태다: `ioA/frontier.json`의 확정 frontier(P1 case frame 133 `5a376`, frame 120 `b30f6`, frame 249 `b97c0`, frame 143 `515fc`(복귀 `50dac`), boot-demo-0 frame 2 `de024`, boot-title-idle/start frame 2 `de376`). V1 spec에는 이 출처를 주석으로 적고, IO 비교 재실행(검증 작업자)이 자연 경로를 직접 확인한다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `1ab02` → `b30ea`(`b30e4` 진입) `b335e`(`b3358`) `b9816`(`b980a`), `493bc` → `b3470`(`b3468`), `b3460` → `b31f4`(`b31ec` 진입, 단위 안 생산자 `b3474`/`b347e`), `28ae` → `b32d8`(`b32c8`) `b330a`(`b32fa`) `b333c`(`b332c`). `49fc6` → `b97fa`(`b97f4`), `5ab5a` → `5a3f8`(`5a3f4`), `4945e` → `5a58e`(`5a588`)는 단위 시험에서 선언 C, V1·실제 ROM 차분에서 실제 사슬(Unicorn SR은 읽지 않는다).
- node fixture: callback 진입(`5a376` `b30f6` `de024` `de376` `b97c0`)과 설치 값(`5a3c6` `5a3e4` `5a41e` `5a43a` `5a54e` `5a574` `b31dc` `b3246` `b97ee` `de054` `de0d8` `de0ee` `de112` `de15c` `de1a8` `de1b4` `de204` `de210` `de2b6` `de2cc` `de3c2`)을 node callback으로 들어가 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `515fc` `b3460` `ddfdc` `e9112` `e9114`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, FR1a 꼴): 시작 211개 × 들어오는 C 3가지, zero-step, 내부 PC 819개 정확한 오류, 경계 stop(출구 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC, BYTE·WORD 부호 경계(BYTE ≥ `80`, WORD ≥ `8000`, index 뒤 sext 경계 `4·k` ≥ `8000`)를 고르는 hint, `de05e`의 port 기록 비교.

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `probe_scan.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`):
  - **stage_entry 검증기**(`tools/verify_animation_machine_stage_entry.py` `negatives()`의 `outside_entry_0ddfdc`, 기대 `unsupported animation machine PC`): 이 단위가 `ddfdc`를 routing하므로 기존 방식(`SUPERSEDED_OUTSIDE`에 새 오류, 행에 `former_expected_API_error` 기록)으로 옮긴다(결정 7). 새 오류는 구현 뒤 그 검증기 자신의 harness로 base 상태에서 측정한 정확한 문자열 하나로 고정한다("구현·검증 기록"). 두 결과를 모두 허용하지 않는다.
  - 그대로 참인 것(stop-only 또는 자기 범위 밖 확인): U14 `boundaries()` `want[]`(`515fc`), N15 N23 U19 `boundaries()`의 `e9112` stop, U05 `rom_outside[]`(`b97c0`)와 `b9726-end-b97c0`(설치 값 확인), C3 시험의 A0 = `de024`/`de376`(레지스터 값), stage_entry 시험의 A0 = `ddfdc`(표 끝 포인터 값), FR1a 시험 `RANGES`(자기 범위).
  - V1 spec: 현재 spec(`b1a`..`b4b` `c1` `c2` `c3b` `d9` `f6a`..`f6c` `fr1`)의 단위는 FR1b 시작을 호출·설치하지 않는다(scratch `callers.py`: FR1b 시작을 참조하는 routing된 코드는 C3 `c5da` `c6de`(`28ae` 자식 값), U14 `50da8`, N13 `59f0c` `5a7f4`, N15 `76eee`, U05 `b9740`, N23 `c3ba6`, U19 `d831e`뿐이고 이 중 V1 spec이 있는 것은 C3(`c3b.py`: 정지가 단위 밖 첫 PC = `28ae`)뿐). 그래서 b2a 꼴의 native 정지 조건 변화는 [I] 없다.
  - Python 관측기의 BOUNDARY 표(`observe_animation_machine_objects_g1.py` `b97c0`, `_g2.py` `e9112`), `observe_animation_machine_stage_entry.py` `DATA_ROWS`(`ddfa4..ddfdc`, 자료 끝)는 고정 관측 도구다(pin된 역사 기록; 고치지 않음).
- [I] 계산 PC로 이 범위에 착지하는 숨은 탐침은 구현 뒤 `make test`로 찾는다. 찾으면 결정 6대로 옮기고 이 절에 더한다.
- [I] frame 회귀: `e9112`(N15 N23 U19 호출), `515fc`(U14), `b97c0`(U05), `5a376`(N13)는 기존 자연 frame에서도 닿을 수 있다. 그 frame이 지금까지 이 PC에서 `unsupported animation machine PC`로 끝났다면 더 진행한다(이득). 자연 불일치는 결함이다(검증 작업자).

## 결정

1. **범위.** FR1 FR1b 명세 199 block에 결정 2·4의 12 block을 더해 211 block. FR1a와 겹침 0.
2. **인접 잎.** IO 재실행 frontier의 실행 수 3인 작은 잎 `b97c0`(10)·`515fc`(1)를 넣는다. `d13b4`(67, 합 278 > 약 220)·`4e68e`·`c0ace`·`e5580`·`bc08c`는 다음 frontier.
3. **`5a5ba` 표 설치 값.** `5a0ae` `5a1c4` `5a460`(같은 객체의 다른 상태, 172 block)은 진입으로 넣지 않는다(FR1 메인 결정). `5a59c`는 표 LONG을 live bus로 읽어 A0에, `5a5b4`가 `(A6)`에 저장만 한다.
4. **`e9114` 외부 진입.** `d6664` `e9106`의 `JSR` 대상이라 block 시작으로 둔다(`e9112`는 `MOVEQ #ff,D0` 한 명령 block).
5. **carry 보존 목록.** 소비자 11개(`5a3f8` `5a58e` `b30ea` `b31f4` `b3470` `b32d8` `b330a` `b333c` `b335e` `b97fa` `b9816`)만 넣는다. `b3474`(Set)·`b347e`(Clear)는 자기 block(`RTS` 포함)에서 known C를 남기고, `b32ea` `b331c` `b334e`(Set)는 읽는 곳이 없다. C를 다른 단위로 넘기는 통과 `RTS`는 없다.
6. **숨은 탐침 이전.** 기존 시험이 이 범위의 PC를 routing 밖 rollback으로 기대하면 RAM `10fexx` 탐침이나 stop-only 확인으로 옮기고, 옮긴 곳은 "영향받는 기존 시험"과 "구현·검증 기록"에 적는다.
7. **stage_entry `outside_entry_0ddfdc`.** 예전 기대(`unsupported animation machine PC`)는 `former_expected_API_error`로 남기고, 새 기대는 이 단위 뒤 C++가 실제로 내는 정확한 문자열 하나로 고정한다(측정, "구현·검증 기록"). `superseded_by` 값은 72fa/7300 행(F6b)과 구분해 `FR1b (ddfdc..de00c)`로 적는다. 검증기 SHA는 바뀐다.
8. **PVC port `de05e`.** 공유 `am_zero_bank`를 그대로 부른다(세 쓰기의 순서·폭이 원본과 같음). bank는 쓰기 뒤 live 값으로 `20000c`를 읽는다.

## 미확인

- [U] BYTE `15` `61` `62` `6b` `80` `8c` `9c`, WORD `46` `54` `68` `76` `78` `7a` `7c` `7e` `80` `84` `86`, LONG `36` `3a` `72` `82` `88` `98`의 의미(객체마다 다름).
- [U] `5a5ba` 표의 다른 상태(`5a0ae` `5a1c4` `5a460`)가 자연 frame에서 고르는 빈도, `49a58` 난수와의 관계.
- [U] 물리 `300000` bank에서 `20017c` `2001d0`의 쓰임.
- [U] `b30f6`을 담은 LONG 표 `e8e90`의 정체(객체 종류 표로 보임).
- [U] 자연 frame에서 이 단위 뒤 다음 첫 미routing PC(IO 비교 재실행으로 확인; [I] 예상: `28ae` 자식 `b336a` `b33d8` `d1d08` `d1d38`, 표 상태 `5a0ae` `5a1c4` `5a460`, `de024`·`de376`은 frame 진행 뒤 다른 E 코드).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr1b.cpp`(case label 211 = scratch `starts_b.txt`와 집합 일치), `engine/tests/animation_machine_objects_fr1b_test.cpp`(생성 구역 + 수작성 규칙: `de05e`의 port 순서·값·PVC page·bank와 쓰기 뒤 bank 창 LONG, `de306`의 스택 순서(LONG A0, 복귀 LONG `de318`)와 `de318` pop·`de2fe` 목록 끝, `e9114`의 `5e30(A5)` 계수기 증감과 BYTE `6b`, `e9112`가 BYTE `6b`만 씀, `b3270`의 `ASR.L #2`(음수), `b30f6`의 `EXT.L`/`LSL.L #8`, `5a59c`의 표 index(상위 WORD 유지), `5a402`의 `SNE`/`AND.B`(상위 24 bit 유지), 범위 옆 자료 PC 16개의 dispatcher 오류), `tools/generate_animation_machine_objects_fr1b_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음, SHA256 `0aa398746a738c18…`, 약 70초), `tools/unit_fixture_specs/fr1b.py`(V1 spec; 정적 검사만 함 — `load_routing` 규칙 120개 뒤 시작 211개가 모두 `animation_objects_fr1b_block`, 내부 819개도 모두 같은 실행부, sentinel과 `493c6`은 routing 밖, 정적 후속은 시작이거나 routing된 출구 39개, 사슬 11개의 소비자가 진입에서 닿음; `first_unrouted`는 FR1 spec의 수정판 그대로(`8c16 < pc <= 8ca6` 내부, 정지 `2a00`에 `2a24` 추가)). 공유 수정은 "공통 규칙"의 다섯 곳과 결정 7의 stage_entry 검증기뿐이다.
- [F] 단위 시험 world: A7 = `10ef00`; `de318`/`de3e0`는 A7에 선언 LONG(목록 포인터)을 둔다. 합성 typed physical byte(ROM 자료 아님): 상태 표 `5a5ba..5a5ca`(LONG 3 = RAM 탐침 `10fe40`, 설치만 됨), 사각형 `b30aa..b30ba` `ba3d6..ba3de`, 로고 표 `de34e..de376`(음수 LONG 포함)과 부호 확장 대상 `d634e`(WORD `78` = `2000`), 스프라이트 목록 `de3e6..de3fa`, bank 창 `20000c`(→ `2a0300`) `20017c`(→ `2a0200`) `2001d0`(→ `2a0100`)와 `2a03ec` `2a0200..2a0218` `2a0150`, 부호 확장 대상 `298200`(D0.W = `2000`). 실제 생산자 사슬은 RAM만 읽는 `1ab02`(3곳) `493bc`(`b3468`) `b3460`→`493bc`→`b3474`/`b347e`(`b31ec`) `28ae`(3곳, 빈 목록 WORD `104ca0`)로 두 C 값을 모두 만든다.
- [F] `make -j3 all test`(작업자, scratch `make_all1.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 272개, Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR1b 시험 줄: `animation machine objects fr1b: 667 fixtures (423 single-block, 145 path, 48 producer chain, 22 declared C, 29 checked error (6 with a later failing PC), 77 kept C, 5 with PVC ports), 211 blocks, 3460 calls, 59319 checks`. 단일 block 표에서 모든 조건 분기의 두 쪽을 들어갔다(누락 0), 출구 39개 + STOP이 모두 어떤 행의 stop이다. 기준(FR1a 검증 로그 `fr1/ver/make2.log`) 대비 다른 시험 줄 변화 없음(새 줄만 추가) — 숨은 탐침 0.
- [F] 무효가 된 기존 탐침과 이전(결정 6·7):
  1. stage_entry 검증기 `outside_entry_0ddfdc`: 예전 기대 `unsupported animation machine PC`를 `former_expected_API_error`로 남기고(`negatives()`가 `SUPERSEDED_OUTSIDE` 행에 기록), `superseded_by` = `FR1b (ddfdc..de00c)`(새 표 `SUPERSEDED_BY`; 72fa/7300 행 값은 그대로 `F6b (72f0..7326)`), 새 기대 `animation machine external read queue empty` 하나로 고정했다. 이 값은 검증기 자신의 `invoke()`와 `common.HARNESS`(이 작업 트리 객체에 링크)로 base 상태(`body-000-actual59-catalog-records` phase 0, carry 2, stop `ff000`)에서 측정했다(scratch `se_probe.py`). 같은 방법으로 잰 대조 `ddf98` `ddfa4` `ddf90` `10fe00`은 기존 기대 `unsupported animation machine PC`와 같았다. stop `e89da` `ddff4` `35f0` `de00a`로 나눠 돌리면 모두 성공한다: [I] `de00a RTS`가 base 상태의 자연 복귀 LONG으로 돌아가 그 frame 코드가 외부 장치를 읽다 멈춘다(빈 queue; 장치 근거 아님). 검증기 전체 실행은 하지 않았다(검증 작업자 몫, scratch `run_stage_entry.py`로 OUT을 바꿔 실행).
  - 그 밖의 시험·Python 시험·V1 spec 변화 없음(U14 `515fc`, N15 N23 U19 `e9112`, U05 `b97c0`, C3 `de024`/`de376` 등은 stop-only라 그대로 통과).
- [F] 검증 작업자(Sonnet 5.5 / medium) 실행 기록, 모두 `MS5_SEED_DIR=artifacts/stage_entry_body`, 출력은 scratch(`/Users/start/Workspce/ms5-scratch/fr1b/`)만:
  - `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310개 통과, FR1b 줄 위 그대로(667 fixtures, 211 blocks, 3460 calls, 59319 checks), 기준 로그 대비 새 줄 외 차이 없음. UBSan(`-fsanitize=undefined -fno-sanitize-recover`): 종료 0, `runtime error` 0, 같은 FR1b 줄.
  - 변이 143개: `killed 143 of 143`(생존 0, 동치 증명 불필요, 생성기 힌트 추가 없음).
  - 실제 ROM 차분(Unicorn 대 C++, 1,500 x 5 = s1 s2 s3 plain, f4 f5 FOLLOW_ANIM): 불일치 0 x 5, 시작 211/211(seed 2만 `5a3c2` 누락, 나머지 4 batch가 덮음), 11 소비자 모두 실제 생산자 뒤에서 native 분기와 비교됨, 알려진 분류(홀수 주소 레지스터, Unknown-C, interpreter dispatch, 2986) 모두 0건. harness 수정 없음.
  - V1 `fr1b` spec: 첫 실행에서 `visited 211/211`, 1,436 fixture 모두 ok였지만 정적 후속 4쌍과 도달 불가 결과 4개가 남았다(`5a58e -> 5a592`, `b31f4 -> b31f8`, `b3470 -> b3474`, `5a5ae -> 5a596`, `5a5b2 -> 5a596`). 원인은 spec 힌트 부족이었고(C++ 결함 아님) spec만 고쳤다: (1) 사슬 `b3468`/`b31ec`에 `A0/D0 := 100cb8`과 BYTE `568e(A5)` 0/1 교대(`493e8`의 Set), (2) `5a588` 사슬에 BYTE `568e(A5) != 0`(Clear), (3) `5a5ae`에 LONG `98(A6)` = A0 힌트, 커버리지 탐색은 `5a59c`를 첫 진입으로(그 앞 진입은 `49a58` callee에서 멈춤), `5a5ae` 커버리지에 표 상태값 4개 순환. 결과: `missing successors [], unreachable outcomes []`, **1,441 fixture 전부 ok**(error 838, match 593, mismatch 10), 두 번 실행(v1runA/B)의 `[(name,digest)]` 동일. 회귀(같은 wrapper): fr1 1,631/1,631, b2a 1,386/1,386, b4 1,830/1,830, b4b 1,723/1,723 모두 ok. 다른 spec/test 수정 없음.
  - stage_entry 검증기(wrapper): 통과, `outside_entry_0ddfdc` 행 = error `animation machine external read queue empty`, `former_expected_API_error` `unsupported animation machine PC`, `superseded_by` `FR1b (ddfdc..de00c)`, 72fa/7300 행 그대로; summary sha256 `24f6f157...`. area_clear 검증기(wrapper): 통과(conditions 256, frames 37,418, sha256 `cc05d3e1...`), `unrouted_neighbour_04b6f4` 행 FR1 그대로.
  - frame 회귀(scratch): D1 / controller game / IRQ 54,400/54,400 complete, natural 불일치 0, demo 45,684/45,684(137 seed), FR1a 기준 `fr1/frames`와 `verification.json`이 소스 pin(`animation_machine_internal.h` SHA)과 elapsed만 다르다(변한 frame 0, native 비교 불필요).
  - IO 비교 재실행(`ioA`, `ioB` 동일: verification.json sha256 `9e101480...`, frontier.json sha256 `063a5efc487bb1ae...`, routing_file_sha256 `271ce329...`): 비교 173,966 frame, **불일치 0**, C++ 오류 0, 모두 acceptance true. 첫 실패 전 일치 frame **149,506**(FR1a 146,957, +2,549), frontier run **56**(FR1a 60).

    | config | FR1a 첫 실패 전 일치 | FR1b | 증감 |
    | --- | ---: | ---: | ---: |
    | P0 | 81,600 | 81,600 | 0 |
    | P1 | 60,968 | 61,942 | +974 |
    | P1b | 4,108 | 4,595 | +487 |
    | boot-demo-0 | 2 | 381 | +379 |
    | boot-title-idle | 2 | 600 (frame-limit 완주) | +598 |
    | boot-title-start | 2 | 113 | +111 |
    | fx 5종 | 275 | 275 | 0 |

    새 frontier(첫 미routing PC, run 수 / config / frame): `4e68e` 14 (P1 12, P1b 2; 2..222), `c0ace` 12 (root `c01a8`, frame 99), `e5580` 12 (root `e4ffc`, frame 245), `50dae` 3 (frame 271; 이전 `515fc`의 호출 뒤), `5ab82` 3 (root `5ab6c`, frame 141; 이전 `5a376`), `b33d8` 3 (root `b3246`, frame 120; 이전 `b30f6`, `28ae` 자식), `bc08c` 3 (frame 167), `d13b4` 3 (frame 328), `a8ee` 1 (root `a75a`, boot-title-start frame 113; 이전 `de376`), `1d1f4` 1 (boot-demo-0 frame 381; 이전 `de024`). 이전 frontier `b97c0` 3 run(frame 249)은 목록에서 사라졌다(어느 새 PC로 옮겼는지는 [U], frontier.json의 root로는 `5ab82`/`b33d8` 등과 구분되지 않음). 합계 55 확정 run(+ fixture 1).

## block 목록

[F] scratch `starts_b.txt`(SHA256 `3b1c05b3c069d9a1f4f3d255e45048f2ab6495e5509fe88cedabe157a8d55574`)와 같다.

- **`515fc..51602`(1)**: `515fc`
- **`5a376..5a460`(26)**: `5a376 5a388 5a394 5a39c 5a3a8 5a3ac 5a3b2 5a3c2 5a3c6 5a3d6 5a3e4 5a3ee 5a3f4 5a3f8 5a3fc 5a402 5a414 5a41a 5a41e 5a42e 5a43a 5a444 5a44a 5a44e 5a456 5a45c`
- **`5a54e..5a5ba`(14)**: `5a54e 5a558 5a568 5a56e 5a574 5a57e 5a584 5a588 5a58e 5a592 5a596 5a59c 5a5ae 5a5b4`
- **`b30ba..b336a`(75)**: `b30ba b30c0 b30ca b30d0 b30d8 b30e0 b30e4 b30ea b30ee b30f4 b30f6 b310c b3114 b3118 b3120 b3130 b314e b3156 b3164 b316e b319e b31ae b31ba b31c0 b31d0 b31d6 b31dc b31e4 b31ec b31f4 b31f8 b3208 b320c b3214 b3218 b321e b3224 b322c b3234 b323c b3242 b3246 b324c b3266 b3270 b3284 b328c b3296 b329c b32a2 b32aa b32b2 b32b6 b32be b32c8 b32d8 b32dc b32ea b32ee b32f2 b32fa b330a b330e b331c b3320 b3324 b332c b333c b3340 b334e b3352 b3358 b335e b3362 b3368`
- **`b3460..b3484`(5)**: `b3460 b3468 b3470 b3474 b347e`
- **`b97c0..b9822`(10)**: `b97c0 b97e8 b97ee b97f4 b97fa b97fe b980a b9816 b981a b9820`
- **`ddfdc..de00c`(5)**: `ddfdc ddfea ddfee ddff4 de00a`
- **`de024..de260`(46)**: `de024 de02e de034 de03a de048 de054 de05c de05e de08a de094 de0a0 de0b2 de0b8 de0be de0cc de0d8 de0e0 de0e2 de0ee de0f6 de0f8 de106 de112 de11a de11c de126 de12c de136 de144 de15c de176 de194 de1a0 de1a6 de1a8 de1b4 de1ce de1ec de1fc de202 de204 de210 de22a de248 de258 de25e`
- **`de2b6..de31e`(9)**: `de2b6 de2c0 de2cc de2e6 de2f6 de2fe de306 de318 de31c`
- **`de376..de3e6`(13)**: `de376 de380 de38a de390 de396 de3a0 de3ae de3b2 de3c2 de3c6 de3ce de3e0 de3e4`
- **`e9112..e9148`(7)**: `e9112 e9114 e9126 e912a e9132 e913e e9140`
