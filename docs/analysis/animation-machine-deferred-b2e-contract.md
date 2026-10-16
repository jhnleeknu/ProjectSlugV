# 스크립트 callback 무리 B2c-b·demo 끝 자식 `e66aa` 구현 계약 B2e

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안, 메인 확인 전.** 이 문서를 먼저 쓰고 그대로 구현한다. 아래 수치와 목록은 작업자가 정적 디코드로 독립 계산했다. 결정 항목(끝)은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 이 문서의 코드 주소는 모두 고정 영역(`<100000`)이라 CPU 주소와 파일 오프셋이 같다. banked 읽기(`200098`)는 live bus(bank base `200000`일 때 물리 오프셋 = CPU 주소)다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `04d5c2f`(`origin/main` + B2d + B2c-a). routing 기준 `engine/src/animation_machine.cpp` SHA256 `9884a39912c7084e3b7f1e0f1f2ae0346850590dba468c5cdf94479363aeb6d3`(dispatch 규칙 111개).
- [F] 정적 디코드: capstone 5.0.6 M68000. block 시작 규칙은 B1 계약 "기준 입력"·B2c 계약과 같다(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, DBRA 대상과 fall-through, `MOVE.L #imm,(A6)` 설치, `MOVEA.L #imm,A0` + `JSR 28ae` 자식; routing된 PC에서 멈춤; TRAP은 경계이며 block 수에 넣지 않는다).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/b2e/`
  - `route.py`(routing 해석, SHA256 `06a5cff9…`), `closure.py`(정적 closure·block 시작, `0c969705…`), `refs.py`(LONG·PC 상대 참조, `4f9cfd74…`), `unit_b2e.py`(단위 정의·겹침·개수·SHA 확인, `72a85d1a…`), `lindis.py`(선형 디코드, `4f94f471…`), `scan_refs.py`(시험·도구의 범위 안 상수 탐색).
  - `starts.txt`(B2e block 시작 109개) SHA256 `7cca0538a55c84d08d698518aad6ecc268257335d74f65da4ca50ce6f27e6d37`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 요약

- [F] **범위와 block 수**(정적, routing·TRAP에서 멈춤):

| 항목 | block | routing 범위 | 바이트 | SHA256 | 진입을 만드는 곳(참조) |
| --- | --- | --- | --- | --- | --- |
| `3abee` 스크립트 callback | 19 | `3abee..3acd6` | 232 | `fe8d9ff41e3007a91ecf6b4f5c693aa88fb39a87e9330f0b6fe5f8ace0992282` | callback 표 `4a500` index `0x23`(LONG `4a58c`) |
| `3b458` 스크립트 callback | 2 | `3b458..3b48c` | 52 | `91e5d126bda0f8f87be4c1f613e3b1aec8fef2d2ec085b62f9a0669e91680d83` | index `0x25`(LONG `4a594`) |
| `3b62a` `3b648` `3b656` 스크립트 callback | 4 + 1 + 5 | `3b62a..3b68a` | 96 | `3295213b734d86fcc82766dcce5d1746a00d82dca9b43f280515311b48454768` | index `0x27` `0x26` `0x24`(LONG `4a59c` `4a598` `4a590`) |
| `44602` 공용 leaf(각도) | 6 | `44602..4464a` | 72 | `85c15db72f248b81c721a16e16f0515bf10589b3c04d0afdb2e9676fb045159b` | `3b466` 외 43곳(B2a `6066a`, N34 `4c746`, N19 `b1ff6`, N25 `5ecbc` 등) |
| `4db18` 자식 생성 helper | 2 | `4db18..4db42` | 42 | `3f27d03f1a52f1c27309d061896b231d9b2461d45df61252d1e5bb1483dd2e5e` | N28 `2c826`, B1c `30c36`, N30 `33796`, B2b `3a1b2`, 범위 밖 `3da60` |
| `4dbdc` `28ae` 자식 | 16 | `4dbdc..4dc66` | 138 | `2f9230faba9adeb45195d095d47ad02331869150aa821622f1310876f4f7b59c` | `4db24 MOVEA.L #4dbdc,A0; JSR 28ae` |
| 소계 B2c-b | **55** | 짝수 PC 316(내부 261) | 632 | 이어 붙인 바이트 `fa8cc09d1def7e1b22b82fd1693ee1413e63df5ca59cf181cfaf2bdf0cb3dd9d` | |
| `e66aa` demo 끝 자식 | 34 | `e66aa..e6836` | 396 | `8b3a17634e2d1103e59f1c53a331045bd5ebfc647483a4a11caf6ce677394f2b` | C2 `c6a6`·`c926` `MOVEA.L #e66aa,A0; JSR 28ae` |
| 순위 계산 꼬리 | 8 | `e6854..e6896` | 66 | `36c3c562ab9753d9f50c9d43b7ca84ee281b2470681c273e841e4f1b913b26f8` | 범위 안 `e6832 BLT` |
| 제목 출력·`e68c6` 자식 | 11 | `e6898..e693a` | 162 | `256fa745826dbebfc46cf7da032b0f30fe9dc8c6ef45f3d74479661c25e0a42d` | `e66f6 JSR (PC)`, `e66ae` `28ae` 자식 |
| `e89da` 공용 leaf | 1 | `e89da..e89e4` | 10 | `3cb29ba9f68bade0ef22140d9947cb72d852d599770d798182fa75067b304984` | `e68a4` `e68b2` `e68c0` 외 6곳(`970c` `9752` `975c` `cb72` `4fc26` `ddfee`) |
| 소계 `e66aa` | **54** | 짝수 PC 317(내부 263) | 634 | 이어 붙인 바이트 `bbdb0f89f36c16984eb947969cf62b63b9229b5bc5009c559764b9ca3032289b` | |
| 합계 B2e | **109** | 10 범위, 짝수 PC 633(내부 524) | 1,266 | | |

- [F] B2c 계약 "B2c-b" 표의 55 block과 집합이 같다(같은 디코더, `4db18`에 `28ae` 자식 `4dbdc`를 따라감).
- [F] **D9 문서의 "72 leader"와의 차이.** D9 탐침은 Unicorn TB 경계(실행 trace의 block hook)를 셌다. 정적 규칙으로는 `e66aa`의 closure가 `e68c6` 자식을 포함해 55 시작이고, 그중 `e6836`은 `TRAP #f` 자체라 경계로 빼서 **54**다. [I] TB 수는 `JSR` 복귀·`DBRA` 반복마다 새 TB가 생겨 정적 시작보다 크다.
- [F] 합계 109 block은 상한(약 220) 안이라 **두 항목을 한 단위로 구현한다**(결정 1).
- [F] **현재 routing과의 관계**: 10개 범위의 모든 짝수 PC가 현재 routing 밖이다(겹침 0, `unit_b2e.py`가 짝수 PC 전수 확인). 이웃: `3acd6`(B2b)·`3b48c`(B2c)·`3b628`(B2c 끝)·`4db42..4dbdc`(N23)·`4dbda`(N23)은 routing돼 있다. `3abec` `3b68a` `44600` `4464a` `4db16` `4dc66` `e66a8` `e6836` `e6838..e6854`(문자열) `e6896` `e693a` `e89d8` `e89e4`는 routing 밖이다.
- [F] **나가는 곳은 모두 routing됨**: callee `2986` `28ae` `288c` `3b288` `3b48c` `4970a` `43e34` `49290` `49f8c` `49fc6` `4d900` `8ebe` `8e82` `e7c36` `1a5a4` `47570` `8c16` `e84c8` `3670` `49260` `49a58` `3918`, 출구 `4c2fa`(B2b) `2a00`. 경계는 TRAP 두 곳(`e6836` `e6896`)과 live target(`4dc44 JSR (A1)`, interpreter의 `JSR (A1)`)뿐이다.
- [F] **도달성**: B2c-b는 스크립트 interpreter callback(`4a352`/`4a43c` `JSR (A1)`, A1 = LONG `4a500 + 4·index`)과 routing된 호출자에서 들어온다. 자연 400 frame(D1 54,400/54,400)은 어느 진입도 실행하지 않았다(실행했다면 미연결 PC 오류로 불일치가 났다). `e66aa`는 D9 demo 선언 (i)(LONG `1008e4` := `c66a`, BYTE `104cd4` := 1)에서 136 seed 모두 실행한다(D9 §3.1: `e66aa` 136, `e66ee` 4,624, `e673e` 9,792, `e6932` 12,376, `e6916` 2,040, `e68c6` 136). 기준 `04d5c2f`의 controller `Execute` demo 비교는 이 자리에서 C++ 오류로 136 seed가 갈라진다(아래 "frame 검증").

## 공통 규칙

B1 계약 "공통 규칙"과 B2c·B2d 계약을 그대로 따른다. 다른 점과 이 단위 값만 적는다.

1. **실행부·이름.** `engine/src/animation_machine_objects_b2e.cpp`, 함수 `animation_objects_b2e_block`. 오류 문자열은 `unsupported animation objects b2e PC`(범위 안 내부 PC 직접 진입)와 `objects b2e caller requires known carry`(C 소비 block에 Unknown C)다.
2. **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(10개 범위), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비 block 5개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES`, test 목록, 시험 target·실행 줄; Codex의 object 재사용 구조 유지), `tools/verify_animation_machine.py` `SOURCES`.
3. **경계.** TRAP `e6836`·`e6896`은 routing하지 않는다(F4 관례: checked 경계). 그 PC로 가면 stop이면 멈추고, 아니면 `unsupported animation machine PC`(전체 rollback)다. 단위 시험은 그 PC에서 stop만 확인한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다.
4. **known C**(아래 "carry"). B2c 관례대로 소비 block만 carry 보존 목록에 넣는다(B2d 결정 3의 FLOW 전체 등록은 쓰지 않는다: 이 단위의 소비 block은 모두 callee RTS 직후의 단일 Bcc block이라 결과가 같다).
5. **간접 분기**(원본에 거르기가 없음, live target; B2 `3a5c8`·B2c `3ab7e`와 같다): `4dc44 JSR (A1)`, A1 = LONG `7a(A6)`. 대상이 routing 밖이면 `unsupported animation machine PC`, 홀수면 `unaligned animation machine PC`다(dispatcher가 판정).
6. **계산 표**(F1 결정 3: 상한 검사 없이 live bus로 읽는다):
   - `4462a`: BYTE `44502 + D0.W`(D0.W ∈ `0..ff`, 앞 `AND.W #ff`), BYTE `44502 + D1.W`(같음), BYTE `44482 + sext(D1.W − D0.W)`. 정적으로 `44383..44681`에 한정된다.
   - `e678c`: LONG `e637a + sext(4·(D0.W − 1))`. `e682e`를 거쳐 오면 D0.W ∈ `1..11`(11 entry, `1ST`..`11TH` 문자열 포인터)이다. 직접 진입은 원본 산술 그대로다. 이어 그 포인터에서 BYTE 4개((A0)+)를 읽는다.
   - `e68cc`: LONG `e63e4 + 4·(D0 & 1)`(2 entry, 정적으로 한정).
   - `e67d0`·`e67fe`·`e6854`: work RAM 순위 기록 `10f02e + 8·k`(`MULU.W #8`, `LEA (A1,D0.W)`/`ADDA.W`는 WORD 부호 확장).
7. **banked 읽기.** `4dbe2 MOVE.L 200098.l,22(A6)`는 live bus로 읽는다.
8. **정수 연산.** `3acb8 DIVU.W #3,D0`(D0 = BYTE `a8` ∈ `0..ff`: 몫 ≤ `55`, 0 나누기·overflow 없음), `3acc0 MULS.W D7,D0`(16×16 부호 곱), `3b45e ASR.L #8`·`ASR.L #1`·`ASR.L #4`, `3b474 ASR.B #3`, `3b480 LSR.B #3`, `44602 ASR.W #1`·`SMI`·`EOR.B`·`SUB.B`, `3b638 NEG.L`, `3ac98 NEG.B`·`NEG.W`, `3b64a NOT.W`, `e679c`·`e67d2` 등 `MULU.W #2/#8`, `e6872 CMP.L`(무부호 BCC), `e682e CMPI.W`/`BLT`·`e688a CMPI.W`/`BLE`(부호), `e6826 DBRA`, `e6916 ADDI.B` 자리올림은 68000 폭 그대로 명시 구현한다. 부호 있는 shift는 부호 bit를 명시적으로 채운다(미정의 동작 없음). X를 쓰는 명령·I/O port 쓰기·bank 변경은 이 단위 block에 없다.
9. **`2986` 호출**(`3ac3e` `3ac70`). `2986` caller-X 제한(buffer_cue 결정 1)은 그대로다. 할당 실패(`28ae` 실패, D0.W ≥ WORD `104ca0`)면 `298e`가 `cue wrapper failure requires known caller X`(checked)를 낸다. 성공이면 C Set이 돌아온다(`298e`가 보존하는 SR).
10. **interpreter callback의 진입 상태**([F] `4a408`/`4a30c`): A0 = 스크립트의 LONG 인자, A6 = 객체 node, D0 = index·4(좁은 꼴) 또는 A0(넓은 꼴), D1 = WORD `4a76c[…]`(넓은 꼴). 복귀 `4a354`/`4a43e`는 C를 읽지 않는다(`MOVE.W (A7)+,…`). 그래서 callback이 돌려주는 C(`3b678 ORI.B #1,CCR` 뒤 `3b67c MOVE.W`가 Clear로 덮음)는 소비자가 없고 Unknown으로 둔다.

## 공통 native 검증 계획

B1 계약 "공통 native 검증 계획"과 B2c·B2d 계약의 가족을 따른다. V1 `tools/verify_animation_machine_unit_fixtures.py`에 새 spec `tools/unit_fixture_specs/b2e.py`를 둔다.

- **macOS seed.** 이 컴퓨터에는 `artifacts/linux_rebase/stage_entry_body`가 없다. 자연 seed가 필요한 V1·frame 실행은 B2c/B2d와 같은 scratch wrapper가 `D.SEED_DIR`만 역사 관측 `artifacts/stage_entry_body`(SHA256 `1f65100f…` = D1 검증기의 `HISTORIC_SEED_SHA`)로 바꾼다. 도구 파일은 고치지 않는다.
- **기반 world.** D1 seed 116/117 frame 2의 자연 N pass node(B2c spec과 같은 `NODE_INDEX`)에 선언 편집(레지스터, node field, 부모 `c(A6)`, PC)을 더한다.
- **block 직접 진입.** 모든 block 시작(소비 block 5개와 `e6890` 제외)을 직접 진입 fixture로 덮는다. stop은 단위 밖 첫 PC(routed callee, sentinel 복귀, TRAP)다. 조건분기 양쪽은 coverage fixture로 채운다.
- **callback 사슬.** interpreter `4a408`(좁은 꼴)·`4a30c`(넓은 꼴)에서 work RAM 스크립트(index `0x23..0x27`, LONG 인자 → work RAM 자료)로 들어가 callback을 실제 `JSR (A1)`로 실행하고 복귀점 `4a43e`/`4a354`에서 멈춘다(routed callee `2986` `28ae` `3b48c` `4970a` `4c2fa` `3b288` `44602` 통과).
- **C 사슬.** 소비 5개를 실제 생산자로 들어간다: `2986` → `3ac76`(`3ac58` 진입), `28ae` → `3b666`(`3b656` 진입), `49fc6` → `4dc34`(`4dc28` 진입), live `JSR (A1)` → `4dc46`(`7a(A6)` := `288c`, routing된 known C 생산자), `288c` → `4dc50`(`4dc4a` 진입). native는 실제 flag로, C++는 known C로 분기한다.
- **자연 호출자.** `4db18`은 routing된 호출자(N28 `2c818`, B1c `30c1c`, N30 `33788`, B2b `3a1b2`)에서 들어가 `28ae` 할당·`4db34` 복귀까지, `44602`는 `3b458`·B2a `6064a`·N34 `4c742`에서 들어가 실제 복귀점까지 실행한다.
- **demo 자연 경로.** 자연 controller 진입 상태(D1 H 끝, A6 = `1008e4`, PC = LONG `(1008e4)`)에 D9 demo 선언(LONG `1008e4` := `c66a`, BYTE `104cd4` := 0 → C1 `c674` 비replay → C2 `c686`)을 두고 `c66a`부터 native로 실행한다. 해체(`c4cc`) → `caf0` → `ca76` → `c6a6` 자식 `e66aa` 할당 → `c6c0` → 꼬리 → RTS `2ac2` → dispatcher가 `e66aa` node → `e6756` 화면 준비 → `28ae` 자식 `e68c6` → `e66cc` 설치 → 자식 `e68c6` node → `e6938`에서 멈춘다. 이어지는 frame(`e66ee` 표시, `e673e` timer, `e6748` → controller `62` → `c6c8 JMP c00444`)은 frame 검증이 덮는다.
- **오류 fixture.** 내부 짝수 PC 전수(524) → `unsupported animation objects b2e PC`. Unknown C 소비 5개 → `objects b2e caller requires known carry`. 범위 밖 이웃·TRAP(stop 없이) → `unsupported animation machine PC`. 홀수 PC. `4dc44` live target이 work RAM·홀수. `e6890 MOVE.W #1,1.w` → `invalid animation machine write size/alignment`. `2986` 할당 실패 → `cue wrapper failure requires known caller X`. 상태 보존 확인.
- **음성 검사.** C++ 입력 RAM 1 bit·레지스터 1 bit·stop·queue 차이가 검출되는지 본다.
- **단위 시험** `engine/tests/animation_machine_objects_b2e_test.cpp`: B2c 시험과 같은 꼴이다(`run_animation_machine`만 사용). 생성기 `tools/generate_animation_machine_objects_b2e_test_table.py`(Unicorn M68000, 원본 BE ROM 위에 같은 합성 byte를 겹침)가 만든 행으로 모든 시작 × 들어오는 C 3가지, zero-step, 내부 PC 전수 정확한 오류, TRAP·경계 stop, RAM 탐침 rollback, Unknown C 소비자, 저장 뒤 실패 rollback을 확인한다. 합성 typed physical byte(ROM 자료가 아님): `44380..44700`(각도 표 자리), `e637a..e63a6` LONG 11개 + 문자열 자리, `e63e4..e63ec`, banked `200000..200100`.
- **frame 검증(회귀).** D1 driver 400 frame(54,400/54,400), controller `Execute` `--declare game`(54,400/54,400), IRQ(54,400/54,400)는 출력만 scratch로 옮겨 그대로 돌린다. 새 routing은 자연 경로(Skip·게임 모드)에 없는 PC만 더하므로 바뀌지 않아야 한다([I]). **controller `Execute` `--declare demo`** 는 기준 `04d5c2f`와 변경 뒤를 같은 wrapper로 돌려 비교한다(기준: 136 seed가 `e66aa` frame에서 갈라짐, 완료 frame 45,684 중 일치 31,128).

## B2c-b: 스크립트 callback 무리(37)·`4db18`/`4dbdc`(18)

### `3abee`(19, callback index `0x23`)

- [F] `3abee`: `TST.B a6(A6)`; ≠ 0 → `3ac12`. `3abf6`: `BTST.B #4,9d(A6)`; 0 → `3ac12`. `3ac00`: `9d` `9e` bit 4 지움, BYTE `a6` := 5. `3ac12`: BYTE `a6` = 0 → `3ac1a RTS`.
- [F] `3ac1c`: BYTE `a6` −= 1, D7.B := BYTE `a8` & 3; ≠ 0 → `3ac58`. `3ac2c`: A0(스크립트 인자) push, `2986` 자식 `3ad48`(D0.W = `1e`, A1 = `100bf4`), `3ac44`: `JSR 3b48c`(B2c), `3ac48`: D0.W = `fff0`, D1.W += `20`, `JSR 4970a`, `3ac56`: A0 pop.
- [F] `3ac58`: BYTE `a3` := 6, A0 push, `2986` 자식 `42d9c`(D0.W = `a`). `3ac76`: `MOVEA.L (A7)+,A1`(스크립트 인자), **`BCC 3acd4`**(`2986`의 C: 실패면 RTS — 실제로는 위 9의 checked 오류가 먼저 난다).
- [F] `3ac7c`: BYTE `a8` += 1, D7.W/D2.W/D3.W := WORD `(A1)+` 3개, `BSR 3b48c`. `3ac8a`: D2.W += D0.W, D3.W += D1.W; BYTE `15` bit 0이면 `3ac98`: `NEG.B D7`, D7.B += `80`, `NEG.W D2`. `3aca0`: 새 자식 BYTE `76(A0)` := D7.B, D7 := 2, (BYTE `76(A0)` & `3f`) ≠ 0 → `3acc6`. `3acb2`: D0 := BYTE `a8`, `DIVU.W #3`, `SWAP`, D0.W −= 1(나머지 − 1), `MULS.W D7,D0`, BYTE `76(A0)` += D0.B. `3acc6`: BYTE `60(A0)` := BYTE `60(A6)`, D0 := 2, `JMP 4c2fa`(B2b).
- [I] partner 객체의 발사(자식 `3ad48` 섬광, `42d9c` 탄) 스크립트 callback이다. 세 번 중 한 번 각도를 ±2 흔든다.

### `3b458`(2, index `0x25`)·`44602`(6)

- [F] `3b458`: `MOVEM.L 36(A6),D0-D1`, D0 `ASR.L #8` `ASR.L #1`, D1 `ASR.L #8` `ASR.L #4`, `JSR 44602`. `3b46c`: D0.B &= `7f`, D0.B −= BYTE `a1`, `ASR.B #3`, D1.B := BYTE `a1` + D0.B, BYTE `a1` := D1.B, `LSR.B #3,D1`, BYTE `98` `a2` := D1.B, RTS.
- [F] `44602`: D0.W `ASR #1`, D2.B := `SMI`, D0.B := (D0.B ^ D2.B) − D2.B; D1/D3도 같다. D1.W &= `ff`; 0 → `4461c`(`MOVEQ #0,D0`). D0.W &= `ff`; 0 → `44626`(`MOVEQ #40,D0`). `4462a`: 위 "계산 표". `4463c`: D3.B ^= D2.B, D0.B := (D0.B ^ D3.B) − D3.B, D2.B &= `80`, D0.B += D2.B, RTS.
- [I] `44602`는 (dx, dy) → 8비트 각도(`atan2` 표)다. `3b458`은 partner 이동 속도 방향을 BYTE `a1`(1/8 보간)로 따라가게 한다.
- RTS C는 소비자가 없다(호출자 44곳 중 이 단위는 `3b46c` 하나). Unknown으로 둔다.

### `3b62a`(4, index `0x27`)·`3b648`(1, index `0x26`)·`3b656`(5, index `0x24`)

- [F] `3b62a`: D0 := LONG `(A0)`, `CLR.W D0`; BYTE `15` bit 0이면 `3b638 NEG.L D0`. `3b63a`: LONG `64` := D0, `JSR 3b288`(N33). `3b642`: LONG `64` := 0, RTS.
- [F] `3b648`: D0.W := `NOT` WORD `(A0)`, BYTE `9d` `9e` &= D0.B, RTS.
- [F] `3b656`: `28ae` 자식 `d3c9e`(D0.W = `1e`; 자식 값은 자료, 실행 PC 아님). `3b666`: **`BCC 3b67c`**(`28ae`의 C: Set = 할당 성공). `3b66a`: D0.W = D1.W = 0, `JSR 4970a`. `3b678`: `ORI.B #1,CCR` → `3b67c`: WORD `68(A0)` `1e(A0)` := `1001`, RTS. [F] 실패(C Clear)면 A0 = `28ae`가 돌려준 대체 node(A5 − `7168`)에 쓴다(원본 그대로).

### `4db18`(2)·`4dbdc`(16)

- [F] `4db18`: A0 := 0, LONG push, `MOVEM.W D0-D1,-(A7)`(낮은 주소에 D0.W), `28ae` 자식 `4dbdc`(D0.W = `a`). `4db34`: WORD `76(A0)` := 원래 D0.W, `78(A0)` := 원래 D1.W, LONG `7a(A0)` := 0, RTS. `28ae` 실패면 대체 node에 쓴다.
- [F] `4dbdc`: WORD `20` := `ea`, LONG `22` := banked LONG `200098`, A1 = `4dd1a`, D0.W = `100`, `JSR 49f8c`. `4dbfa`: 소리 `3b0`(`8ebe`). `4dc08`: WORD `68` `1e` := `fff1`, D0.W/D1.W := WORD `76`/`78`, `JSR 49290`. `4dc22`: 설치 `4dc28`.
- [F] `4dc28`(재진입): `JSR 43e34`, `JSR 49fc6`, **`4dc34 BCS 4dc60`**. `4dc38`: LONG `7a` = 0 → `4dc4a`. `4dc40`: `JSR (A1)`(A1 = LONG `7a`, live), **`4dc46 BCS 4dc60`**. `4dc4a`: `JSR 288c`, **`4dc50 BCC 4dc60`**(부모 없음·부모 callback ≠ `270e`이면 Set, 아래 B2d 관례). `4dc54`: `JSR 4d900`. `4dc58`: `TST.B D0`; 음수면 `4dc60`. `4dc5e`: RTS. `4dc60`: `JMP 2a00`(자기 삭제).
- [F] `4db18`의 모든 호출자는 `4db18`로 들어가 LONG `7a` := 0을 쓴다(`4db1e` 이후 진입 참조 0건). [I] 자연 경로에서는 `4dc40`의 `JSR (A1)`이 실행되지 않는다. 다른 code가 `7a`를 쓰는지는 [U]다.
- [I] 위치(D0, D1)에 효과 자식을 만드는 공용 helper다(N28·N30·B1c·B2b 호출자).

## `e66aa` demo 끝 자식(54)

- **진입**([F]): C2 `c6a6`(demo 끝 `c69a` 해체 뒤)·`c926`(카드 경로)이 `MOVEA.L #e66aa,A0; MOVE.W #0,D0; JSR 28ae`로 controller node(`1008e4`) 뒤에 자식 node를 만든다. 범위 안 설치 `e66ee`(`e66e8`)·`e673e`(`e6738`), 자식 `e68c6`(`e66b8`, D0.W = `14`), 그 설치 `e6916`(`e6910`)·`e6932`(`e692c`).
- **의미**([F] 바이트, [I] 해석): demo 끝의 **순위 화면**("BEST TANK BUSTERS", `e63d2` 문자열)이다.
  - `e66aa`: `JSR e6756`(화면 준비: `8e82`, `e7c36`, `1a5a4`(A0 = `e631a` 기본 순위 자료, D0 = 0), `47570`, `8c16`(D0..D2 = 0, D3 = 8)). `e66ae`: 자식 `e68c6`. `e66be`: `49260`(D0.W = `a0`, D1.W = `80`). `e66cc`: WORD `76` := `5a`, `7e` `78` `7a` := 0, BYTE `80` := 0, WORD `7c` := 1, 설치 `e66ee`.
  - `e66ee`(재진입): BYTE `80` = 0이면 `e6746 RTS`. 아니면 `JSR e6898`(제목 3줄: `e89da` → `3918` 문자 출력, D1.W = `441`, 위치 `7085` `71a5` `72c5`). `e66fa`: WORD `7c` −= 1, 빌림 없으면 `e6746`. `e6702`: `7c` := 0, `7a` += 1, `7a` ≤ 1(무부호)이면 `e6726`. `e6714`: `78` = 9가 아니면 `e671e`: `78` += 1. `e6722`: `7a` := 0. `e6726`: D0.W := `78`, `JSR e6784`(순위 한 줄). `e672e`: `78` = 9이면 `e6738`: 설치 `e673e`.
  - `e673e`(재진입): WORD `76` −= 1, 0이면 `e6748`: A0 = LONG `c(A6)`(부모 = controller node), **BYTE `62(A0)` := `ff`**, `JMP 2a00`(자기 삭제). 그 뒤 controller `c6c0`이 `62` ≠ 0을 보고 `c6c8 JMP c00444`(BIOS SYSTEM_RETURN, frame 구동기의 checked 종단)로 간다.
  - `e6784`(순위 줄 k = D0.W): WORD push, D7.W := k, `JSR e682e`(순위 계산) → D0. `e678c`: 순위 문자열 포인터 LONG `e637a[D0 − 1]`, 문자 4개를 `e84c8`(D0.W = `70a8 + 2k`, D1.W = `441`, 뒤 3개는 D1.W = 3, D0.W += 1). `e67d0`: 점수 LONG `10f02e + 8k`를 `3670`(D4 = 8, A1 = `e84c8`, D3 = 0, D0.W = `7168 + 2k`). `e67fe`: 이름 3문자 `10f032 + 8k`를 `DBRA D7` 반복(`e681e` `e6826`)으로 `e84c8`(D0.W = `73a8 + 2k`). `e682a`: WORD pop, RTS.
  - `e682e`: D7.W < `a`(부호)면 `e6854`, 아니면 **`TRAP #f`(`e6836`, 뒤 문자열 `"RANK_IN Record Number Error"`)**. `e6854`: A0 = `10f02e + sext(8·D7.W)`, D7 += 1, A1 = `10f02e`, D0 = D1 = 1, D3 = LONG `(A0)`. `e6870`: D4 = LONG `(A1)`, D3 ≥ D4(무부호)면 `e687c`, 아니면 `e6878`: D0.W := D1.W + 1. `e687c`: D1.W = D7.W이면 `e6882 RTS`. `e6884`: A1 += 8, D1.W += 1, D1.W ≤ `a`(부호)면 `e6870`, 아니면 **`e6890 MOVE.W #1,1.w`** 다음 **`TRAP #f`(`e6896`)**.
  - `e68c6`(자식): `JSR 49a58`(난수), `e68cc`: A1 = LONG `e63e4[D0 & 1]`, WORD `20` := `152`, D0.W = `100`, `JSR 49f8c`. `e68ec`: 소리 `e95`. `e68fa`: WORD `68` `1e` := 0, BYTE `12` := 0, `JSR 43e34`, 설치 `e6916`. `e6916`(재진입): BYTE `12` += `10`, 자리올림 없으면 `e6932`. `e6920`: BYTE `12` := `ff`, 부모 BYTE `80(A0)` := `ff`(표시 시작), 설치 `e6932`. `e6932`: `JSR 49fc6`(C 버림), `e6938 RTS`.
- [F] **`e6890`의 홀수 WORD 쓰기**: 68000에서는 주소 오류 예외가 난다([I] 디버그 정지). C++는 `am_write`의 정렬 검사로 `invalid animation machine write size/alignment`(checked, 전체 rollback)다. Unicorn은 주소 오류를 흉내 내지 않으므로 native 비교는 하지 않는다(오류 fixture만, 의도적 차이 1).
- [F] **`e89da`**(1 block): `LEA e84c8(PC),A1; JMP 3918`. 9곳이 부르는 공용 leaf다(결정 3).
- **known C**: 생산·소비 없음(모든 flag는 block 안에서 소비; `e6932`의 `49fc6` C는 버림).
- **경계**: TRAP `e6836` `e6896`. 그 밖 callee는 모두 routing됨.

## carry

- [F] **소비 block 5개**(callee가 돌려준 C를 읽음):
  - `3ac76`: `MOVEA.L (A7)+,A1; BCC.W 3acd4` — `2986`(`298e`가 복원한 SR: 성공 Set).
  - `3b666`: `BCC.W 3b67c` — `28ae`(`290c` Set / `2916` Clear).
  - `4dc34`: `BCS.W 4dc60` — `49fc6`(interpreter).
  - `4dc46`: `BCS.W 4dc60` — live target `JSR (A1)`이 돌려준 C(그 callee의 마지막 block이 known C를 남겨야 한다).
  - `4dc50`: `BCC.W 4dc60` — `288c`(readiness).
- [F] 이 5개만 `carry_preserving_pc`에 넣는다. Unknown이면 checked 오류다. 이 단위에는 다른 block이 소비하는 known C 생산자가 없다. 그 밖의 모든 block은 진입 때 Unknown이 된다.

## 영향받는 기존 시험·검증기

[F] `scan_refs.py`로 새 routing 범위 안 상수를 전수 검색했다. 새 routing 대상 PC를 "미연결" 기대로 쓰는 곳과 바꾸는 값(값만 바꿈, work RAM 탐침):

| 파일 | 위치 | 지금 | 바꾸는 값 |
| --- | --- | --- | --- |
| `engine/tests/animation_machine_objects_b2a_test.cpp` | 597행 `unrouted[]`의 `0x44602` | 미연결 기대 | `0x10fe08` |
| 같은 파일 | 603행 `world(…,0x6064a,…)` stop 없이 `44602`에서 오류 기대 | 미연결 기대 | `0x10fe0a` |
| `engine/tests/animation_machine_objects_b2b_test.cpp` | 590행 `world(…,0x3a1b2,…)` stop 없이 `4db18`에서 오류 기대 | 미연결 기대 | `0x10fe06` |
| 같은 파일 | 620행 `unrouted[]`의 `0x4db18`, `0x3b458` | 미연결 기대 | `0x10fe08`, `0x10fe0a` |
| `engine/tests/animation_machine_objects_b2c_test.cpp` | 660행 `neighbours[]`의 `0x3abee`, `0x3b458`, `0x3b62a` | 미연결 기대 | `0x10fe02`, `0x10fe04`, `0x10fe06` |
| `engine/tests/animation_machine_objects_u03_test.cpp` | 400행 `outside[]`의 `0xe89da` | 미연결 기대 | `0x10fe0c` |
| `tools/unit_fixture_specs/b2a.py` | `UNROUTED_NEIGHBOURS`의 `0x44602`, `error-boundary-44602`(PC `6064a`) | 미연결 기대 | `0x10fe08`, PC `0x10fe0a`(이름 `error-probe-10fe0a`) |
| `tools/unit_fixture_specs/b2b.py` | `UNROUTED_NEIGHBOURS`의 `0x4db18`, `error-boundary-4db18`(PC `3a1b2`) | 미연결 기대 | `0x10fe08`, PC `0x10fe06`(이름 `error-probe-10fe06`) |
| `tools/unit_fixture_specs/b2c.py` | `UNROUTED_NEIGHBOURS`의 `0x3abee 0x3b458 0x3b62a 0x3b648 0x3b656 0x4db18 0x44602` | 미연결 기대 | `0x10fe02 0x10fe04 0x10fe06 0x10fe08 0x10fe0a 0x10fe0c 0x10fe0e` |

- stop만 확인하는 곳(그대로 통과): b2a 시험 141·478행(`44602` stop), b2b 시험 163행(`4db18` stop), b1c 시험 653·763행, n19 1082행, n25 1486행, n28 830행, n30 821행, n34 774·822행(모두 fixture stop = 그 PC), `tools/unit_fixture_specs/b1c.py` `BOUNDARY`(trace stop), `c2.py` `CHILDREN`(chain stop; controller는 자식을 설치만 함).
- 데이터 값으로만 나오는 곳(무관): C2 시험 176·259행(A0 = `e66aa` 값), `game_ready_test.cpp` 50행·`tools/verify_game_ready.py`(저장 값, native 별도 검증), N23 시험 852행(범위 끝 `4dbdc`, 배타), `tools/verify_fixed_text.py`(native 전용).
- frame 검증기: controller `Execute` `--declare demo`의 C++ 결과가 바뀐다(의도한 변화; 기준·변경 뒤를 모두 기록). D1·게임 모드·IRQ는 바뀌지 않아야 한다.

## 결정 필요 (MAIN DECISION NEEDED)

1. **범위.** B2c-b 55 + `e66aa` 54 = 109 block을 B2e 하나로 구현한다(작업자 권고·채택).
2. **TRAP·`e6890`.** TRAP `e6836` `e6896`은 routing하지 않는 checked 경계로 두고, `e6890`의 홀수 WORD 쓰기는 C++ 정렬 오류(checked)로 둔다(native 비교 없음, 의도적 차이). 대안: `e6890`을 routing하지 않고 경계로 두기(그러면 `e6884` 뒤가 미연결 오류).
3. **공용 leaf `44602`·`e89da`.** `44602`(44곳)·`e89da`(9곳)는 이 단위 호출 그래프가 처음 실행하는 leaf라 이 단위가 routing한다(B2c 결정 3 `1bf80` `1d198` 관례). 다른 호출자는 그대로 이 실행부를 쓰게 된다. 대안: 경계(stop만)로 두면 `3b458`·`e6898`을 끝까지 실행할 수 없고 demo frame 비교가 그 자리에서 갈라진다.
4. **`3b4e0`·`4b6f4`.** B2c 결정 2·B2 결정 4 그대로 routing하지 않는다.
5. **`4dc44 JSR (A1)`.** 허용 목록 없이 live target(B2 `3a5c8` 관례). 자연 호출자는 모두 `7a` := 0이라 [I] 실행되지 않는다.
6. **carry 등록.** 소비 block 5개만 등록(B2c 꼴). 대안: B2d처럼 FLOW 전체 등록(결과 같음).

## 미확인

- [U] callback index `0x23..0x27`을 쓰는 스크립트(partner `3c88c..` 계열로 추정)와 화면상 동작 이름.
- [U] `4dc40` live target이 실제로 생기는 경로(LONG `7a`를 0이 아닌 값으로 쓰는 code).
- [U] `e6890`/TRAP 경로가 실제로 생기는지(순위 기록 `10f02e`가 정렬돼 있지 않거나 D7 ≥ `a`). 자연 demo에서는 [I] 생기지 않는다.
- [U] 하드웨어에서 순위 화면 timer(`76` = `5a`)·`80` 시작 시점과 BIOS 복귀 뒤 동작(BIOS 효과는 주장하지 않는다).
- [U] 400 frame 밖·응답 `00`·controller 생략 해제 시 B2c-b의 자연 도달.

## block 목록

[F] scratch `starts.txt`(SHA256 `7cca0538a55c84d08d698518aad6ecc268257335d74f65da4ca50ce6f27e6d37`)와 같다.

- **`3abee`(19)**: `3abee 3abf6 3ac00 3ac12 3ac1a 3ac1c 3ac2c 3ac44 3ac48 3ac56 3ac58 3ac76 3ac7c 3ac8a 3ac98 3aca0 3acb2 3acc6 3acd4`
- **`3b458`(2)**: `3b458 3b46c`
- **`3b62a` `3b648` `3b656`(10)**: `3b62a 3b638 3b63a 3b642 3b648 3b656 3b666 3b66a 3b678 3b67c`
- **`44602`(6)**: `44602 4461c 44620 44626 4462a 4463c`
- **`4db18`·`4dbdc`(18)**: `4db18 4db34 4dbdc 4dbfa 4dc08 4dc22 4dc28 4dc2e 4dc34 4dc38 4dc40 4dc46 4dc4a 4dc50 4dc54 4dc58 4dc5e 4dc60`
- **`e66aa`(54)**: `e66aa e66ae e66be e66cc e66ee e66f6 e66fa e6702 e6714 e671e e6722 e6726 e672e e6738 e673e e6746 e6748 e6756 e675c e6762 e676e e6774 e6782 e6784 e678c e67b0 e67c0 e67c8 e67d0 e67fe e681e e6826 e682a e682e e6854 e6870 e6878 e687c e6882 e6884 e6890 e6898 e68aa e68b8 e68c6 e68cc e68ec e68fa e6910 e6916 e6920 e6932 e6938 e89da`
- 경계(block 아님): TRAP `e6836` `e6896`, 문자열 `e6838..e6854`.

## 구현·검증 기록(작업자, 메인 리뷰 전)

- 실행부 `engine/src/animation_machine_objects_b2e.cpp`(case label 109 = block 시작 109, `starts.txt`와 집합 일치). routing `else if` 1개(10 범위), carry 보존 목록에 `3ac76 3b666 4dc34 4dc46 4dc50`, 선언 1줄, Makefile(SOURCES·시험 target·실행 줄), `tools/verify_animation_machine.py` SOURCES.
- 단위 시험 `engine/tests/animation_machine_objects_b2e_test.cpp`(run_animation_machine만): 생성 행 196개(`tools/generate_animation_machine_objects_b2e_test_table.py`, native Unicorn + 합성 표 바이트), 비소비 block × C 3종, 소비 block × C 2종, zero-step 109 × 3, 내부 짝수 PC 524개 정확한 오류, 범위 양끝 홀수 PC, work RAM 탐침 rollback, 이웃·TRAP, live target RAM·홀수, `e6890` 홀수 쓰기, TRAP stop(`e682e` → `e6836`), 저장 뒤 실패 rollback(`3ac58` → `2986` 실패), 홀수 install, Unknown C 소비자.
- 기존 시험·spec의 탐침 이전은 위 "영향받는 기존 시험·검증기" 표 그대로다(값과 해당 주석·이름만 바꿈).
- 검증 결과는 작업자 보고에 둔다(scratch `/Users/start/Workspce/ms5-scratch/b2e/`). [F] `capstone`은 `e89da`의 `LEA d16(PC),A1`(`43fa faec`)을 디코드하지 못한다. spec은 길이 4를 고정 값으로 둔다.
- [F] 원 `half-abs-sign` 변이(`ASR.W #1` 결과의 bit 14 검사)는 동치 변이다(ASR 뒤 bit 15 = bit 14). 대체 변이 2개(`ASR` 부호 채움 제거, `SMI` 반전)로 바꿔 확인했다.
