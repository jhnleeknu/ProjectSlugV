# frontier 단위 FR4(FR3 뒤 D 영역 IO frontier `72f8a` `878dc`와 그 자연 후속) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. FR2 계약(`animation-machine-frontier-fr2-contract.md`)·FR2b 계약·FR3 계약(`animation-machine-frontier-fr3-contract.md`)의 구조·공통 규칙을 따르고 다른 점만 적는다. 메인 지시: `area-d-completion-plan.md` §4의 FR4(`7343a` 묶음 + `878aa` + bc 꼬리, 계산 점프 `cc7a8` `cc82a`, 약 201 block, 예측 IO 163,350)를 현재 routing으로 다시 재고, FR3 뒤 IO frontier `72f8a`(12 run, frame 496)와 `878dc`(3 run, frame 309)의 자연 후속을 모두 덮으며, 계산 점프 표는 전부 전사한다. 약 220을 넘으면 나눈다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 코드·고정 표는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기 `2000d0` `2000d4` `200080` `200140`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `2ae9502`(branch `claude/frontier-units-3`, FR3 커밋). routing 기준 `engine/src/animation_machine.cpp` SHA256 `869a9dc12b14ba47ed65642ab937cb1bbaa5a49775241e3a325ce47fc1d1a446`(= FR3 IO 재실행 `frontier.json`의 `routing_file_sha256`), `animation_machine_internal.h` `f7953e9a0a117d13b4f4b8966df5402838e579a4a4efb36c325affd18daf1f3b`.
- [F] frontier 입력: FR3 뒤 IO 재실행 `/Users/start/Workspce/ms5-scratch/fr3/ioA/frontier.json`(첫 실패 전 일치 **161,229**, frontier run 39 = 확정 37 + guard fixture 2). 이 단위의 확정 frontier(모두 phase N, 복귀 `2ac2`):
  - `72f8a`: P1 11 + P1b 1, frame 496(FR3의 `c5370` run이 252 → 496으로 진행한 뒤). [F] `72f8a`는 FR2b·N15 계열 routing 코드 `70d6a` `7102a` `71206`이 `MOVE.L #72f8a,(A6)`로 쓰는 설치 값이다(이 단위 안 `732f6`, 범위 밖 형제 `73210` `73456`도 씀).
  - `878dc`: P1 2 + P1b 1, frame 309(FR3의 `bc93c` run이 276 → 309로 진행한 뒤). [F] `878dc`는 ROM LONG 표 `4a6a0..`의 한 항목(`4a6b0`; 이웃 `703f6` `76f1e` `7ef84` `87b3c` …)이다. 표를 읽는 생성 경로는 이미 routing돼 있다 [I].
  - 나머지 D frontier `5ab82`(3, frame 141)·`50dae`(3, frame 271)는 FR5·FR6이다.
- [F] **자연 후속 확인**(scratch `tools/dstate.py` `tools/fr4next.py` `tools/fr4pcs.py`, IO 관측 읽기 전용): `artifacts/animation_machine_io_native/runs/*/*.json.gz`의 frame별 `unr_new`를 현재 routing으로 다시 걸렀다. `P1/000`(c5370 run): frame 496 `72f8a` `72f90` … `7345e` `734a6` `735a4` → 497 `730a6` `730fa` → 499 `730d2` `730e0` `73304` `7338c` `733b6` → 500 `73392` → 532 `7346c` → 541 `734be` → 542 `73520` → 563 `73326`, 그 뒤 600 frame 끝까지 routing 밖 PC 없음. `P1/022`(bc844 run): 309 `878dc` `8790c` `87986` … `87a94` → 310 `87982` → 317 `879f4` → 318 `87a78` → 331 `87a0c` → 332 `87a3e` `87a56` → 333 `87a50` → 347 `bca2c`(FR3 `bc9d8`의 설치 값) `bca6e` → 348 `bca62` → 352 `87a64` → 451 `bca7a` → 459 `bca82` → 593 `bc7d6`(FR1c `bc716`의 `28ae` 자식) → 594 `bc836`, 그 뒤 600 frame 끝까지 없음.
- [F] 정적 디코드: capstone M68000, FR3 계약과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, `MOVE.L #imm,(A6)` 설치 값 중 범위 안의 것, 범위 밖에서 들어오는 실제 분기 대상, 연속 Bcc 묶음은 한 block). routing된 PC, `RTS`, `TRAP`, 계산 점프에서 멈춘다. `28ae` 자식 값은 기록만 한다. 진입 = 위 run들이 실제로 실행한 routing 밖 PC 121개(다른 진입의 closure 안에 이미 든 것은 뺌: `878dc` `8790c` `bca2c` `72f8a` `bc7d6`). 설치 값은 native가 실행한 것만 따라간다(FR3 결정 2). TB 시작이지만 block 시작이 아닌 PC `72fe0` `72fe6` `72fee` `72ff2` `72ff6` `72ffa` `72ffe`(`72fdc` anim block 안의 bank 창 읽기 뒤 TB 경계)는 진입이 아니다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr4/`
  - `tools/`: FR3 scratch 도구의 경로만 바꾼 사본(`fclos.py` `hroute.py` `dstate.py` `dleft.py` `refidx.py` `cread.py` …), 새 `unit_fr4.py`(이 단위 정의), `fr4probe.py` `fr4tab.py`(계산 점프 표를 전사했을 때의 closure), `fr4next.py`(단위 뒤 run별 다음 정지), `fr4pcs.py`, `fr4tail.py`(`JMP cc778` 꼬리 호출 지점의 둘레 진입), `fr4dis.py`, `probe_scan_fr4.py`.
  - `starts_fr4.txt`(시작 192개) SHA256 `3652aa0ce2eb34078244a1ab10912976a3cc498a8f6aab6b43efdac695c8c22e`; `unit_fr4.out`(block별·범위 전체 디코드), `probe_fr4.out`.
  - 재현: `cd /Users/start/Workspce/metalslug-fu3 && .venv/bin/python /Users/start/Workspce/ms5-scratch/fr4/tools/unit_fr4.py B D`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **계획값 재측정**(현재 routing `869a9dc1…`, `area-d-completion-plan.md` §4 규칙): FR4 root(`72f8a` `730a6` `73296` `73392` `7343a` `878aa` `bca2c` `bca62` `bc7d6` `bc836`)의 실행 PC 121개(실행 54,414회, 16 run) closure는 계산 점프 `cc7a8` `cc82a`를 경계로 둘 때 **192 block 시작**(계획 도구 셈 201 = 시작 192 + 연속 Bcc 묶음 2 + JSR 복귀 등 계획 도구의 leader 셈 차이), 명령 499. 예측 일치 frame **163,350**(+2,121)로 계획과 같다(`fr4next.py`: `72f8a` 12 run 496 → 600 끝, `878dc` 3 run 309 → 600 끝; 12 × 104 + 3 × 291 = 2,121). D 남은 실행 PC 640 → 502(C 무관 273 → 155, C 뒤 367 → 347: `cc600` `cc778` `cca76` `cdc1c` 계열의 C 뒤 PC 20개도 이 단위에 든다), D 첫 정지 run 21 → 6(`5ab82` 3 + `50dae` 3).
- [F] **계산 점프 표 전사의 크기**(`fr4tab.py`): `cc7a8 JMP cc7ac(PC,D0.W)`와 `cc82a JMP cc82e(PC,D0.W)`는 정적으로 27 항목씩이다(index = `CMPI.B #1b,D0; BCC` 뒤 `ANDI.W #ff,D0`이라 0..`1a`; 항목은 모두 `BRA.W`, 아래 "자료 표"에 전부 적음). 항목 54개를 block으로 넣으면 246(시작) / 계획 셈 255, 항목의 대상 처리기(`ccaf8` `ccc88` `ccd74` `ccf4e` `cd0fe` `cd370` `cd7c6` `cd94e` `cdb08`; `cdc1c`는 이미 단위 안)까지 따라가면 **597 block**(명령 1,363)이다. 약 220의 한 단위가 될 수 없다.
- [F] **IO에서의 실행**: 두 표 점프는 관측 집합 296 run 어디서도 실행되지 않았다. `cc778` 계열은 boot-demo-0(C 뒤, frame 433)에서만 실행되며 그때도 `cc798`의 `BCC.W cdc1c`(index ≥ `1b`)를 탔다(`cc7a0` 미실행). 즉 표 항목과 처리기는 IO 진척에 기여하지 않는다.
- [F] **고른 것(결정 1)**: FR4 = 위 closure **192 block**, 15 범위, 명령 499, 짝수 PC 1,100(내부 908), 이어 붙인 바이트 2,200, SHA256 `4abcf701beff2217cd36ffd39c974be75b6105f2777f50265ccb761db48892d8`. 두 계산 점프는 이 단위 안 block(`cc7a0` `cc822`)으로 구현하고 PC := 표 시작 + sext(index.W)로 옮긴 뒤 대상은 routing에 맡긴다(FR1 결정 3과 같은 꼴, F1 결정 3). 표 항목 54개와 처리기 closure(약 342 block)는 FR4b·FR4c(C 뒤 D, 약 200 block 두 단위)로 미룬다. 기존 routing과 겹침 0, 연속 Bcc 묶음 2(`cc62a BEQ.W cc650; BPL.W cc646`, `cc66e BEQ.W cc694; BPL.W cc68a`).
- [F] **F4 범위 문서와의 겹침**(scratch 확인, `animation-machine-object-callbacks-f4-scope.md`의 범위 식 전부와 교차): U27 `cc778..cc822`(254행)가 이 단위의 `cc778..cc7ac` `cc818..cc82e`와 겹친다. U27/U28/U30/R07/R12/R13 행의 "간접 `cc7a8` `cc82a`"가 이 단위의 두 계산 점프다. 범위 문서는 계획이고 아직 구현된 단위가 아니므로 겹침은 그 단위들이 착수할 때 이 범위를 빼야 한다는 뜻이다(결정 5).
- [I] **예상 진척**(상한 추정, IO 비교 재실행이 실제 측정값): 161,229 → **163,350**(+2,121). 나머지 frontier(`4e68e` 15, `5ab82` 3, `50dae` 3, `1d1f4` 1, fixture `2634` 2)는 그대로이고 frontier run 수는 39 − 15 = 24(새 D 정지 없음).

| 묶음(진입) | block | 명령 | 범위 |
| --- | --- | --- | --- |
| `72f8a`(+ 설치 `730a6` `73296` `73392`, 공용 꼬리 `7345e`, 쓰기만 `72f8a` `71a80` `72d42` `733d0`) | 95 | 273 | `72f8a..73132` `73218..733d0` `7345e..7357c` `73582..735a2` `735a4..735a8` |
| `cc778`(`7355c`/`73582`의 `JMP` 대상, helper `cca76` `cc600`, 정지 설치 `cdc24`) | 31 | 83 | `cc600..cc696` `cc778..cc7ac` `cc818..cc82e` `cca76..ccade` `cdc1c..cdc24` |
| `878dc`(+ `28ae` 자식 `8790c`, 설치 `87982` `87a50`, 쓰기만 `87a3e`, helper `87a6c`) | 47 | 96 | `878dc..87a3c` `87a3e..87a8c` `87a94..87aaa` |
| `bca2c`(FR3 정지 설치 값; + 설치 `bca62`, 쓰기만 `bc93c` `bcaa0`) | 11 | 25 | `bca2c..bcaa0` |
| `bc7d6`(FR1c `bc716`의 `28ae` 자식; + 설치 `bc836`) | 8 | 22 | `bc7d6..bc844` |
| 합 | **192** | 499 | 15 범위 |

## 요약

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `72f8a..73132` | 424 | `768eae2446365eb60d964fad1f504dc10f38d3a2a1b170c71e5a3481e3168e3f` | 33 | 212 |
| `73218..733d0` | 440 | `e0e6c5a55e80c46adbf1dc3344f2c5f75eb671a1e57a4be62eac0fce32386387` | 33 | 220 |
| `7345e..7357c` | 286 | `e25c1100a389ba2c105ea5c62989670c72fae3c7f880115b1d5f4381abb27c8d` | 27 | 143 |
| `73582..735a2` | 32 | `7c94b3a824d2c8df78c9bc01df5e8710abd094472b08289b9ac6e37f36e4a310` | 1 | 16 |
| `735a4..735a8` | 4 | `273dde22b9dc010cd8622bcc9289b3a18db22b27032717788a851aed37fbcdbc` | 1 | 2 |
| `878dc..87a3c` | 352 | `357d0aec1220288ddf93bad41c27fd432710fc795ece7846e7a24c1044470e5d` | 32 | 176 |
| `87a3e..87a8c` | 78 | `e31660f49398d7568ed16ff2812b6a301762cdad11991531ca7c0367e7ddb48c` | 11 | 39 |
| `87a94..87aaa` | 22 | `326bd67ede5f7080788d0d0f4c3f70937e1672b4fb47ba30e15ffe7fc41e3acc` | 4 | 11 |
| `bc7d6..bc844` | 110 | `5982046558ecc975c07d71dff2dc89f36553dffff03af1ba7df18b5bf2f736d0` | 8 | 55 |
| `bca2c..bcaa0` | 116 | `d40cb0a12a94dbb32abc193ecfbf7ea9e06c0c0aea865191b5532d28f911048d` | 11 | 58 |
| `cc600..cc696` | 150 | `bbbe3ea6c08fbcaa003d13f780e1bf8cb7409211cffb8e5938575b5d21b0d356` | 17 | 75 |
| `cc778..cc7ac` | 52 | `74d7ea532dc4e5ab0bf97e8ecace83b3fe281bf09658501d42a08e220b21d861` | 5 | 26 |
| `cc818..cc82e` | 22 | `66bbb9b13240449dfdeb368ea6abdb728d9ebe52d7a408806da761a0cac14a15` | 3 | 11 |
| `cca76..ccade` | 104 | `52e1d6af4b60f5d18bb8b1c4061ab0da306952d941459f13136efdbf717b8aad` | 5 | 52 |
| `cdc1c..cdc24` | 8 | `4d2d7d9bbf1c4879b49da73677e107ecee5d88a8d6ce3dc1fe5cbec382cb1cf9` | 1 | 4 |
| 합계 FR4 | 2200 | 이어 붙인 바이트 `4abcf701beff2217cd36ffd39c974be75b6105f2777f50265ccb761db48892d8` | **192** | 1100(내부 908) |

- [F] closure가 15 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 범위 사이: `73132..73218`(`73132` 형제 상태, 실행 안 됨), `733d0..7345e`(정지 설치 값 `733d0`의 코드와 `7343a` 형제 상태: `7343a`는 범위 밖 `73434`의 설치 값이고 IO에서 실행되지 않음), `7357c..73582`(`RTS; BRA.W 735a4`, 닿지 않는 조각), `735a2`(`RTS`, 닿지 않음), `87a3c`(`RTS`, 닿지 않음), `87a8c..87a94`(상자 자료), `cc696..cc778`(다른 helper), `cc7ac..cc818`(점프 표 1), `cc82e..cca76`(점프 표 2와 `cc89c` `cc8b4` 다른 함수), `ccade..cdc1c`(처리기 본문), `cdc24..`(정지 설치 값 `cdc24`의 코드).
- [F] X 소비 없음(`ADDX`/`SUBX`/`ROX` 없음). `JSR (An)` 없음. `TRAP` 없음. I/O port·bank 쓰기 없음. `DIVU`/`MULS`/`MULU` 없음. 계산 점프 2곳(`cc7a8` `cc82a`, 결정 2). `BVS` 1곳(`73534`, 같은 block의 `ADD.L`의 V). `MOVEM.W` 스택(`73102` 넣기, `7310c` 꺼내며 부호 확장). `ASR.L #5/#6/#8`, `ASR.W #1`, `LSL.L #1/#3/#6`, `LSL.W #2`, `LSR.W #1`, `SWAP`, `NEG.L`/`NEG.W`(메모리 LONG 포함), `EOR.L`/`EOR.W`, `SNE.B`, `ST.B`.
- [F] **경계 이웃**: routing된 것 `bc7d4`(FR1c) `bc844`(FR2b) `bca2a`(FR3). 그 밖은 routing 밖 형제 코드·자료(위 목록, 그리고 `72f88` `73216` `7345c` `878da` `cc5fe` `cc776` `cca74` `cdc1a` 앞쪽 다른 함수의 끝).
- [F] **나가는 곳**(각 실행부의 `case` block 시작으로 routing됨): callee `28ae` `8ebe` `8ff4` `1ab02` `1ab80` `43e34` `48502` `491c4` `49290` `4970a` `497a6` `49a58` `49f8c` `49fc6` `4ae4a` `4b54e` `4bc04` `4be34` `4bfa4` `70036`(`BSR.W`) `7054c`(`BSR.W`) `c6a96` `e9112`, 출구 `JMP 2a00`(`7346c` `87a64` `87aa2`), `BEQ.W 71a80`(`730d8`), `BRA.W 70054`(`735a4`). routing 밖으로 나가는 곳은 계산 점프의 대상(표 항목 `cc7ac..cc814` `cc82e..cc896`, 결정 2)뿐이다.
- [F] **참조**(ROM 전체 LONG 상수와 정적 발견 색인, scratch `refidx.py`): 범위 밖에서 들어오는 실제 진입은 모두 block 시작이다 — `72f8a`(`70d6a` `7102a` `71206` `73210` `73456` 설치, `72f62` `72f86` `BRA`), `878dc`(LONG 표 `4a6b0`), `bca2c`(FR3 `bc9d8` 설치), `bc7d6`(FR1c `bc716` `MOVEA.L #`, `28ae` 자식), `cc778`(`JMP`: routing된 `72e0c` `72e32` N15 `76f0e` N16 `78cba` N17 `7a4d6` N18 `86342` N20 `73644`, 밖 `747b6` `8032a`, `BSR`: `cdb00`), `cca76`(밖 `cc8bc`), `cdc1c`(표 항목과 처리기 `cdb10`). 범위 안 다른 PC로 들어오는 밖의 분기는 없다.
- [I] 의미(이름은 확정하지 않는다): `72f8a`는 N15/FR2b 계열 보병형 적의 이동 상태(난수 `49a58`으로 LONG `92`(속도 보정)·LONG `64`(가속 ±`40000..4ffff`)·WORD `2c`를 정하고 bank `2000d0`/`2000d4`(WORD `9c`로 선택) LONG `4`의 애니메이션). `730a6`: BYTE `15` bit 7(화면 안 [I]) = 0이면 `73304` 낙하/점프 상태, BYTE `61` bit 0이면 `73218` 방향 전환. `730ba`: 목표 x(LONG `8e`)까지의 거리 부호와 진행 방향 비교, `49a58` 난수로 `71a80` 이탈. 지형 `4bc04`(위치 WORD `42`±`40`, `46`) → `70036` → `4bfa4` → `49fc6` → `7054c`(Set이면 `71a80` 설치). `7345e` 공용 꼬리: 피격 판정 `1ab80`(상자 `72d5e`; Set이면 부모 BYTE `62` := `ff` 뒤 `2a00` 삭제), BYTE `62`(피격 종류 [I])가 있으면 방향 BYTE `15` bit 0을 정하고 이전 callback을 LONG `9e`에 두고 `72d42` 설치, `48502`(플레이어 위치 [I]) 기반 sine 형 진동 계산으로 LONG `92` `8e` 갱신(`BVS`면 `8e` 그대로), `4b54e` 접촉, BYTE `61` bit 7이면 부모 BYTE `62` := `ff`, BYTE `17` := `ff`, 처리기 인자(A0 = 표 `cdeea`/`cdef8`, A1 = bank 창 LONG, D1.W = 3/`b`, D2.W = 0/1)로 `cc778`. `cc778`: BYTE `5e`(피격 원인 index [I])가 0이면 `RTS`, 아니면 `cca76`(처음 한 번 BYTE `61` bit 6을 세우고 BYTE `76` `7b`, LONG `82` `86`, WORD `8a` `8c`에 인자 저장; `cc600` 소리(LONG 표 `cdf3e`, WORD `8c` index, `497a6` = BYTE `10fd92` 기반 선택); `e9112`; BYTE `78` := BYTE `15` bit 7 ? `ff` : 0, 나머지 field 정리), BYTE `5e` := 0, BYTE `15` bit 7로 표 `cc7ac`/`cc82e`(index BYTE `5e` < `1b`) 또는 `cdc1c`(`cdc24` 설치). `878dc`는 LONG 표 `4a6b0`의 객체: `28ae` 자식 `8790c`(파편 [I]: 속도 LONG `36` = ±`80000`, `c6a96`(1f, 13), bank `200080` LONG `4c` anim, 설치 `87982`: `87a6c`(WORD `3a` 하강 속도로 frame 번호 `13..17`) → anim 다시, x 속도 LONG `36`을 0쪽으로 ±`2000` 감속, WORD `76` 동안 대기 뒤 LONG `3a` −= `4900`(중력), `4be34`, 화면 밖·지형 BYTE `61` bit 0이면 `87a3e` 쓰기, `49fc6`, LONG `72`(지형 표) ≠ 0이면 `4ae4a`, `1ab02` 화면 판정(상자 `87a8c`)). `87a3e`: BYTE `61` bit 3, WORD `76` := `14`, 설치 `87a50`: `43e34` `49fc6` 뒤 WORD `76` 세다 0이면 `2a00`. `bca2c`는 FR3 `bc93c` 계열의 셋째 단계(bank `200140` LONG `90` anim, 부모 BYTE `62`/`63`이 있으면 WORD `76` 세기 → `bc93c`/`bcaa0` 쓰기). `bc7d6`은 FR1c `bc716`의 효과 자식(`49290` `491c4` 위치, `c6a96`(4f, 37), bank `200140` LONG `dc`).

## 공통 규칙·native 검증 계획

FR2·FR2b·FR3 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr4.cpp`, 함수 `animation_objects_fr4_block`. 오류 문자열은 `unsupported animation objects fr4 PC`(범위 안 내부 PC 직접 진입·계산 착지), `objects fr4 caller requires known carry`(C 소비 block에 Unknown C; 소비자 7개). 그 밖의 오류는 공용 bus/스택 오류다(`28ae` 실패 경로의 caller-X 제한 등 기존 checked 오류 그대로).
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(15 범위, FR3 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 7개, "carry"), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 정지 설치 값 `733d0` `bcaa0` `cdc24`, 범위 안이지만 다음 PC가 아닌 설치 쓰기 `72f8a`(`732f4`) `87a3e`(`87a0c` `87a1c`), 범위 밖 routing된 값 `71a80`(`73128`) `72d42`(`7349c`) `bc93c`(`bca82`)는 `MOVE.L ...,(A6)`로 쓰기만 하고 실행하지 않는다(FR3 결정 2). 기존 시험이 stop으로만 보던 PC(`cc778`: N04 `72dd8` 계열·N15 `76ef4`·N16 `78c76`..·N17 `7a48e` `7a4aa`·N18 `8625a`..·N20 `73620` `7362a`, `bc7d6`: FR1c `bc716`)는 stop 판정이 routing보다 먼저라 그대로 통과한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. 다른 단위·다음 단위가 routing할 코드(표 항목 `cc7ac..` `cc82e..`, 처리기 `ccaf8` … `cdb08`, `cdc24`, `733d0`, `7343a`, `73132`, `bcaa0`, `cc8b4`)는 rollback 탐침으로 쓰지 않는다(계산 점프 대상은 stop-only로 확인, 결정 2). dispatcher 오류 확인에 쓰는 범위 옆 PC는 자료 PC `87a8c`(상자)·`72d5e`(상자)뿐이다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): FR2와 같다. 행의 run stop은 실패 block 바로 뒤 PC다.
- **자료 읽기**(live bus, 상한 검사 없음): LONG `(cdf3e + sext(4·WORD 8c))`와 그 LONG이 가리키는 WORD `+0`/`+2`(`cc610` `cc654` `cc63c` `cc642` `cc680` `cc686`), bank 창 LONG `2000d0` `2000d4`(LONG `4` `c` `28`, `7355c`/`73582`는 LONG 자체를 A1로) `200080`(LONG `4c`, 그리고 `87986`의 `(LONG 200080 + sext(4·D0.W))`) `200140`(LONG `90` `dc`)와 그 LONG `d(…)`. RAM 읽기: node field(A6), 부모 LONG `c(A6)`의 BYTE `62` `63`(`bca6e` `bca88`; `7346c` `7354c`는 BYTE `62` 쓰기), WORD `53a2(A5)`(`734ee`), 그리고 callee가 돌려준 레지스터. 단위 시험은 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다, 자료 영역 `cdf3e..cdf86`과 bank `200000` 창 LONG과 그 뒤 LONG만; 코드 바이트와 겹치지 않음). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `MOVEM.W D0-D1,-(A7)`(`73102`: 낮은 주소 D0.W)과 `MOVEM.W (A7)+,D2-D3`(`7310c`: D2 := sext(낮은 주소 WORD = 넣은 D0.W), D3 := sext(넣은 D1.W), `4bc04` 호출 너머); JSR/BSR 복귀 LONG. 홀수 A7은 checked 오류다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B`, `ADDI.W` `ADD.W` `SUB.W` `SUBQ.W` `ANDI.W` `ANDI.B` `NEG.W` `LSL.W` `LSR.W` `ASR.W` `EOR.W` `CLR.W` `CLR.B` `ST.B` `SNE.B`, `BSET`/`BCLR`/`BCHG`). `MOVEQ`는 LONG 전체. `MOVEA.L`. `ANDI.L #ff`/`#ffff`, `SUBI.L #80`, `ADDI.L #40000`, `ADDI.L #2000`/`SUBI.L #2000`/`SUBI.L #4900`(메모리 LONG). `LSL.L #6` 뒤 `SWAP`(`7308e`), `LSL.L #3`(`730ba`), `LSL.L #1`(`73520`), `LSL.W #2`(`73296`). `ASR.L #5`(`73392`), `ASR.L #6`/`#8`(`734be` `734da` `734ee` `73506` `73520`), `ASR.W #1`(`734ac` `734be`: WORD만, 부호 bit 복제), `LSR.W #1`(`87a78`). `ADDI.W #8000` 뒤 `SWAP; ASR.L #8`(WORD를 LONG 상위로 옮겨 산술 이동). `CLR.W D0` 뒤 `ASR.L #6`(`734ee`). `NEG.L 64(A6)`·`NEG.L 36(A6)`(메모리 LONG). 비교: `CMPI.W #180,46(A6)` + `BCS`(무부호 WORD < `180`), `CMPI.B #1b,D0` + `BCC`(무부호 BYTE ≥ `1b`), `CMPI.W #4,D1` + `BLE`(부호 WORD ≤ 4), `SUBQ.W #1,76(A6)` + `BCC`(옛 WORD ≠ 0), `TST.B`/`TST.W`/`TST.L` + `BEQ`/`BNE`/`BPL`/`BMI`, `MOVE.B` + `BEQ`(`7347a` `cc778`), `MOVE.L` + `BEQ`/`BMI`(`87a28` `73506`), `MOVE.W` + `BPL`(`87a6c`), `MOVE.W (A0,D0.W),D0` + `BEQ`/`BPL` 묶음(`cc610` `cc654`), `SUB.W` + `BPL`(`734b4` `734d0`), `ASR.W` + `BPL`(`734ac` `734be`), `EOR.L`/`EOR.W` + `BPL`(`730ba` `732ac`), `SUBQ.W; ANDI.W #1` + `BNE`(`73482`), `ANDI.B #7` + `BEQ`(`730d8`), `ADD.L` + `BVS`(`73520`: 부호 있는 32 bit 넘침), `BSET.B #6` + `BNE`(Z = 옛 bit), `BTST` + `BEQ`/`BNE`, `BTST` + `SNE`(`ccab6`). flag는 같은 block 안에서 만들고 소비한다(예외: "carry"의 callee C).

## carry

- [F] **소비 block 7개**(callee가 돌려준 C; Clear 쪽 / Set 쪽):
  - N15 `7054c`(FR2b 소비자 `70cf8`과 같은 생산자, known C): `73124 BCC.W 7312e`(`7312e` / `73128`).
  - U12 `1ab80`: `73468 BCC.W 7347a`(`7347a` / `7346c`).
  - `28ae`(Set = 생성 성공): `878ec BCC.W 8790a`(`8790a` / `878f0`).
  - `1ab02`: `87a9e BCC.W 87aa8`(`87aa8` / `87aa2`).
  - U20 `497a6`(`TST.B 10fd92`: 0이면 `ORI` Set, 아니면 Clear; FR2b 소비자 `7686e`와 같은 생산자): `cc60c BCS.W cc654`(Clear `cc610` / Set `cc654`), `cc638 BCS.W cc642`(`cc63c` / `cc642`), `cc67c BCS.W cc686`(`cc680` / `cc686`).
- [F] **C를 넘기는 `RTS`: 없음.** 이 단위의 subroutine `cc600` `cca76` `87a6c`와 진입 `cc778`의 직접 호출자는 복귀 뒤 C를 읽지 않는다(scratch `cread.py`: `cc778` 호출 1곳 `cdb00`, `cca76` 3곳, `cc600` 3곳, `87a6c` 1곳, C 읽는 곳 0). `cc778`로 `JMP`하는 꼬리 호출 지점 11곳(`72e0c` `72e32` `73576` `7359c` `73644` `747b6` `76f0e` `78cba` `7a4d6` `8032a` `86342`)의 둘레 진입은 모두 `MOVE.L #…,(A6)` 설치 상수로만 참조된다(scratch `fr4tail.py`: `72d42` `72d56` `72d5e` `733d0` `7343a` `735a8` `7476c` `76e90` `78a10` `7a48e` `80074` `86252` …) [F]; 그래서 그 상태들은 node callback이고 복귀는 dispatcher `2ac2`다 [I].
- [F] **known C 생산 block 없음**(이 단위에 `ORI`/`ANDI` CCR 없음). 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다(`SUBQ`+`BCC`, `CMPI`+`BCC`/`BCS`는 같은 block 안에서 소비).
- [F] **읽는 곳이 없는 C**(carry 보존 목록에 넣지 않음): node callback의 `RTS`(`8790a` `87a6a` `87aa8` `bc842` `bca9e`, `cc818` `cdc1c`: `MOVE`가 정한 Clear지만 dispatcher가 읽지 않음), helper `RTS`(`87a8a` `cc694` `ccab6`).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 7개다: `73124` `73468` `878ec` `87a9e` `cc60c` `cc638` `cc67c`. Unknown C로 소비자에 들어오면 checked 오류다.
- [F] flag 재계산(block 경계를 건너 다시 계산하는 flag)은 없다.

## 객체 `72f8a`(+ `730a6` `73296` `73392`)

- **`72f8a`**(설치 값): `JSR 49a58`(복귀 `72f90`). **`72f90`**: D0 := (D0 ∧ `ff`) − `80`(LONG), LONG `92` := D0, BYTE `83` = 0 → `73008`, 아니면 `72fa8`.
- **`72fa8`** / **`73008`**: WORD `9c` ≠ 0 → `72fdc` / `7303c`, 아니면 `72fb0` / `73010`. **`72fb0`** `73010`: anim(3, `2000d0`, 4)(복귀 `72fd8` / `73038`; FR2 "공통 꼴": LEA 26(A6),A0; WORD `20` := n; LONG `22` := LONG(창); D0.W := `100`; A0 := A6 + `26`; A1 := LONG(LONG `22` + d); `JSR 49f8c`). **`72fdc`** `7303c`: anim(`b`, `2000d4`, 4)(복귀 `73004` / `73064`). **`72fd8`**: `BRA.W 73004`. **`73004`** **`73038`**: `BRA.W 73064`.
- **`73064`**: `JSR 49a58`(복귀 `7306a`). **`7306a`**: D0 := (D0 ∧ `ffff`) + `40000`(LONG), BYTE `15` bit 0 ≠ 0 → `73082`, 아니면 `73080`: D0 := −D0(LONG). **`73082`**: LONG `64` := D0, D0의 N = 0 → `7308e`, 아니면 `7308c`: D0 := −D0. **`7308e`**: D0 := SWAP(D0 << 6)(LONG), D0.W += `80`, WORD `2c` := D0.W, LONG `8e` := LONG `42`, 설치 `730a6`(다음 PC라 들어감).
- **`730a6`**(설치 값): BYTE `15` bit 7 = 0 → `73304`, 아니면 `730b0`: BYTE `61` bit 0 ≠ 0 → `73218`, 아니면 `730ba`.
- **`730ba`**: D0 := LONG `8e` − LONG `42`, D1 := LONG `64`, D2 := D1 << 3, D0 := (D0 + D2) ⊕ D1(LONG), N = 0 → `730ea`, 아니면 `730d2`: `JSR 49a58`(복귀 `730d8`). **`730d8`**: D0.B ∧= 7, 0 → `71a80`(routing된 출구), 아니면 `730e0`: LONG `64` := −LONG `64`, BYTE `15` bit 0 반전(fall-through `730ea`).
- **`730ea`**: D0.W := `40`, BYTE `15` bit 0 ≠ 0 → `730fa`, 아니면 `730f8`: D0.W := −D0.W. **`730fa`**: D0.W += WORD `42`, D1.W := WORD `46`, WORD D0, D1 넣기(`MOVEM.W`, 낮은 주소 D0.W), `JSR 4bc04`(복귀 `7310c`). **`7310c`**: D2 := sext(꺼낸 WORD), D3 := sext(꺼낸 WORD), `BSR.W 70036`(복귀 `73114`). **`73114`**: `JSR 4bfa4`(복귀 `7311a`). **`7311a`**: `JSR 49fc6`(복귀 `73120`; C는 읽지 않음). **`73120`**: `BSR.W 7054c`(복귀 `73124`). **`73124`**(소비자): Clear → `7312e`, Set → `73128`: LONG `(A6)` := `71a80`(쓰기만; fall-through `7312e`). **`7312e`**: `BRA.W 7345e`.
- **`73218`**: WORD `9c` ≠ 0 → `7324c`, 아니면 `73220`: anim(3, `2000d0`, `c`)(복귀 `73248`: `BRA.W 73274`). **`7324c`**: anim(`b`, `2000d4`, `c`)(복귀 `73274`). **`73274`**: D0 := `10000`, BYTE `15` bit 0 ≠ 0 → `73286`, 아니면 `73284`: D0 := −D0. **`73286`**: LONG `64` := D0, LONG `8e` := LONG `42`, 설치 `73296`(다음 PC라 들어감).
- **`73296`**(설치 값): D2.W := (WORD `64` << 2) + WORD `42`(WORD; WORD `64`는 LONG `64`의 상위 WORD), D3.W := WORD `46`, D0.W := `ff`, `BSR.W 70036`(복귀 `732ac`). **`732ac`**: D0.W := (WORD `8e` − WORD `42`) ⊕ WORD `64`, D1.W := WORD `64`, N = 0 → `732c2`, 아니면 `732be`: LONG `64` := −LONG `64`. **`732c2`**: BYTE `15` bit 7 = 0 → `73304`, 아니면 `732cc`: `JSR 4bfa4`(복귀 `732d2`). **`732d2`**: BYTE `61` bit 0 ≠ 0 → `732fa`, 아니면 `732dc`: WORD `64`의 N = 0 → `732ee`(BYTE `15` bit 0 := 1), 아니면 `732e4`(bit 0 := 0, `BRA.W 732f4`). **`732f4`**: LONG `(A6)` := `72f8a`(쓰기만). **`732fa`**: `JSR 49fc6`(복귀 `73300`: `BRA.W 7345e`).
- **`73304`**: 무부호 WORD `46` < `180` → `73316`, 아니면 `7330e`: LONG `3a` := `8a000`. **`73316`**: D0 := `28000`, BYTE `15` bit 0 ≠ 0 → `73328`, 아니면 `73326`: D0 := −D0. **`73328`**: LONG `64` := D0, LONG `36` := D0, WORD `9c` ≠ 0 → `73364`, 아니면 `73338`: anim(3, `2000d0`, `28`)(복귀 `73360`: `BRA.W 7338c`). **`73364`**: anim(`b`, `2000d4`, `28`)(복귀 `7338c`). **`7338c`**: 설치 `73392`(다음 PC라 들어감).
- **`73392`**(설치 값): LONG `36` += ASR.L(LONG `64` − LONG `36`, 5), LONG `3a` += ASR.L(`fff00000` − LONG `3a`, 5)(D0 = 마지막 더한 값), `JSR 4be34`(복귀 `733b6`). **`733b6`**: `JSR 49fc6`(복귀 `733bc`). **`733bc`**: BYTE `15` bit 7 = 0 → `733cc`, 아니면 `733c6`: LONG `(A6)` := `733d0`(쓰기만; fall-through `733cc`). **`733cc`**: `BRA.W 7345e`.

## 공용 꼬리 `7345e`

- **`7345e`**: A0 := `72d5e`(상자), `JSR 1ab80`(복귀 `73468`). **`73468`**(소비자): Clear → `7347a`, Set → `7346c`: A0 := LONG `c`, BYTE `62(A0)` := `ff`, `JMP 2a00`.
- **`7347a`**: D0.B := BYTE `62`, 0 → `734a6`, 아니면 `73482`: D0.W := (D0.W − 1) ∧ 1, ≠ 0 → `73496`(BYTE `15` bit 0 := 0), 아니면 `7348c`(bit 0 := 1, `BRA.W 7349c`). **`7349c`**: LONG `9e` := LONG `(A6)`, LONG `(A6)` := `72d42`(쓰기만; fall-through `734a6`).
- **`734a6`**: `JSR 48502`(복귀 `734ac`). **`734ac`**: D1.W := ASR.W(D1.W, 1), N = 0 → `734b4`, 아니면 `734b2`: D1.W := −D1.W. **`734b4`**: D0.W −= WORD `8e`, N = 0 → `734be`, 아니면 `734bc`: D1.W := −D1.W. **`734be`**: D0.W := D0.W + D1.W + `8000`, D0 := ASR.L(SWAP(D0), 8), D3.W := ASR.W(D3.W, 1), N = 0 → `734d0`, 아니면 `734ce`: D3.W := −D3.W. **`734d0`**: D2.W −= WORD `8e`, N = 0 → `734da`, 아니면 `734d8`: D3.W := −D3.W. **`734da`**: D2.W := D2.W + D3.W + `8000`, D2 := ASR.L(SWAP(D2), 8) + D0, WORD `9a` = 0 → `73506`, 아니면 `734ee`: D0.W := WORD `96` + WORD `53a2(A5)` − WORD `42` + `8000`, D0 := ASR.L(SWAP(D0) ∧ `ffff0000`, 6)(`SWAP; CLR.W; ASR.L #6`), D2 += D0(fall-through `73506`).
- **`73506`**: D2 := ASR.L(D2, 6), D0 := WORD `8c` + `77`(무부호 WORD를 LONG에: `MOVEQ #0` 뒤 `MOVE.W`, `ADDI.W`로 WORD 안에서 넘침), WORD `8c` := D0.W, D1 := LONG `92`, N = 1 → `73520`, 아니면 `7351e`: D0 := −D0(LONG). **`73520`**: D0 <<= 1(LONG), D1 := ASR.L(D1, 6), D1.W += D0.W, D2 := D2 − D1 + LONG `92`(LONG), LONG `92` := D2, D2 += LONG `8e`, 부호 있는 넘침(V) → `7353c`, 아니면 `73538`: LONG `8e` := D2. **`7353c`**: `JSR 4b54e`(복귀 `73542`). **`73542`**: BYTE `61` bit 7 = 0 → `735a4`(`BRA.W 70054`), 아니면 `7354c`: A0 := LONG `c`, BYTE `62(A0)` := `ff`, WORD `9c` ≠ 0 → `73582`, 아니면 `7355c`.
- **`7355c`** / **`73582`**: BYTE `17` := `ff`, A0 := `cdeea` / `cdef8`, A1 := LONG `2000d0` / `2000d4`(bank 창 LONG), D1.W := 3 / `b`, D2.W := 0 / 1, `JMP cc778`(이 단위 안).

## 처리기 입구 `cc778`(+ `cca76` `cc600` `cdc1c`)

- **`cc778`**: D0.B := BYTE `5e`, 0 → `cc818 RTS`, 아니면 `cc780`: `JSR cca76`(복귀 `cc784`). **`cc784`**: D0.B := BYTE `5e`, BYTE `5e` := 0, BYTE `15` bit 7 = 0 → `cc81a`, 아니면 `cc798`.
- **`cc798`** / **`cc81a`**: 무부호 D0.B ≥ `1b` → `cdc1c`, 아니면 `cc7a0` / `cc822`. **`cc7a0`** / **`cc822`**: D0.W := 4·(D0.W ∧ `ff`)(WORD 안), `JMP cc7ac(PC,D0.W)` / `JMP cc82e(PC,D0.W)`: PC := `cc7ac` / `cc82e` + sext(D0.W)(결정 2).
- **`cdc1c`**: LONG `(A6)` := `cdc24`(쓰기만), `RTS`.
- **`cca76`**: BYTE `61` bit 6 := 1, 옛 bit = 1 → `cca9c`, 아니면 `cca80`: BYTE `76` := 0, BYTE `7b` := `ff`, LONG `82` := A0, LONG `86` := A1, WORD `8a` := D1.W, WORD `8c` := D2.W(fall-through `cca9c`). **`cca9c`**: LONG `56` := 0, `BSR.W cc600`(복귀 `ccaa8`). **`ccaa8`**: LONG `56` := 0, `JSR e9112`(복귀 `ccab6`). **`ccab6`**: BYTE `78` := (BYTE `15` bit 7 ≠ 0) ? `ff` : 0(`BTST; SNE`), BYTE `7a` := 0, LONG `7e` := 0, LONG `64` := 0, BYTE `79` `7d` `77` `7c` := 0, `RTS`.
- **`cc600`**: `JSR 8ff4`(복귀 `cc606`). **`cc606`**: `JSR 497a6`(복귀 `cc60c`). **`cc60c`**(소비자): Clear → `cc610`, Set → `cc654`.
- **`cc610`** / **`cc654`**: A0 := LONG `(cdf3e + sext(4·WORD 8c))`(`ADD.W D0,D0` 두 번: WORD 안에서 넘침), D0.W := 0 / 2(`MOVE.W #0/#1; ADD.W`), D0.W := WORD `(A0 + sext(D0.W))`, 0 → `cc650` / `cc694`, N = 0 → `cc646` / `cc68a`, 아니면(음수) `cc632` / `cc676`: `JSR 497a6`(복귀 `cc638` / `cc67c`). **`cc638`** / **`cc67c`**(소비자): Clear → `cc63c` / `cc680`(D0.W := WORD `(A0)`, `BRA.W cc646` / `cc68a`), Set → `cc642` / `cc686`(D0.W := WORD `2(A0)`). **`cc646`** / **`cc68a`**: D1.B := 0, `JSR 8ebe`(복귀 `cc650` / `cc694`). **`cc650`**: `BRA.W cc694`. **`cc694`**: `RTS`. (A0는 `cc610`/`cc654`가 정한 값이 block 경계와 `497a6` 호출을 넘어 쓰인다: `497a6`은 A0·D0를 바꾸지 않는다 [F] `497a6..497b4`.)

## 객체 `878dc`(+ `8790c` `87982` `87a3e` `87a50` `87a6c`)

- **`878dc`**(LONG 표 `4a6b0` 값): A0 := `8790c`, D0.W := `a`, `JSR 28ae`(복귀 `878ec`). **`878ec`**(소비자): Clear → `8790a RTS`, Set → `878f0`: D0.W := `ffe8`, BYTE `15` bit 0 = 0 → `87900`, 아니면 `878fe`: D0.W := −D0.W. **`87900`**: D1.W := `20`, `JSR 4970a`(복귀 `8790a`). **`8790a`**: `RTS`.
- **`8790c`**(`28ae` 자식 값): `JSR 491c4`(복귀 `87912`). **`87912`**: LONG `36` := `80000`, LONG `3a` := 0, WORD `76` := 8, BYTE `15` bit 0 ≠ 0 → `87936`, 아니면 `87932`: LONG `36` := −LONG `36`. **`87936`**: WORD `68` `1e` := `e0ef`, D0.W := `1f`, D1.W := `13`, D2.B := 0, `JSR c6a96`(복귀 `87954`). **`87954`**: anim(`ba`, `200080`, `4c`)(복귀 `8797c`). **`8797c`**: 설치 `87982`(다음 PC라 들어감).
- **`87982`**(설치 값): `JSR 87a6c`(복귀 `87986`). **`87986`**: A0 := A6 + `26`, WORD `20` := `ba`, LONG `22` := LONG `200080`, D1.W := 4·D0.W(WORD 안), A1 := LONG `(LONG 200080 + sext(D1.W))`, D0.W := `100`, `JSR 49f8c`(복귀 `879b6`).
- **`879b6`**: BYTE `15` bit 0 ≠ 0 → `879d4`, 아니면 `879c0`: LONG `36`의 N = 0 → `879d0`, 아니면 `879c8`: LONG `36` += `2000`. **`879d0`**: `BRA.W 879e4`. **`879d4`**: LONG `36`의 N = 1 → `879e4`, 아니면 `879dc`: LONG `36` −= `2000`. **`879e4`**: WORD `76` = 0 → `879f4`(LONG `3a` −= `4900`), 아니면 `879ec`(WORD `76` −= 1, `BRA.W 879fc`). **`879fc`**: `JSR 4be34`(복귀 `87a02`).
- **`87a02`**: BYTE `15` bit 7 = 0 → `87a12`, 아니면 `87a0c`: LONG `(A6)` := `87a3e`(쓰기만). **`87a12`**: BYTE `61` bit 0 = 0 → `87a22`, 아니면 `87a1c`: LONG `(A6)` := `87a3e`(쓰기만). **`87a22`**: `JSR 49fc6`(복귀 `87a28`; C는 읽지 않음). **`87a28`**: D0 := LONG `72`, 0 → `87a38`, 아니면 `87a30`: A0 := D0, `JSR 4ae4a`(복귀 `87a38`). **`87a38`**: `BRA.W 87a94`. **`87a94`**: A0 := `87a8c`(상자), `JSR 1ab02`(복귀 `87a9e`). **`87a9e`**(소비자): Clear → `87aa8 RTS`, Set → `87aa2 JMP 2a00`.
- **`87a3e`**(설치 값; 이 단위는 쓰기만 하며 다음 frame의 dispatcher가 들어감): BYTE `61` bit 3 := 1, WORD `76` := `14`, 설치 `87a50`(다음 PC라 들어감). **`87a50`**: `JSR 43e34`(복귀 `87a56`). **`87a56`**: `JSR 49fc6`(복귀 `87a5c`). **`87a5c`**: WORD `76` −= 1, 옛 WORD ≠ 0 → `87a6a RTS`, 아니면 `87a64 JMP 2a00`.
- **`87a6c`**: D0.W := `13`, D1.W := WORD `3a`(LONG `3a`의 상위 WORD), N = 0 → `87a8a RTS`, 아니면 `87a78`: D1.W := (−D1.W) >> 1(무부호 WORD 이동), (부호) D1.W ≤ 4 → `87a88`, 아니면 `87a84`: D1.W := 4. **`87a88`**: D0.W += D1.W. **`87a8a`**: `RTS`.

## 객체 `bca2c`(+ `bca62`), `bc7d6`(+ `bc836`)

- **`bca2c`**(FR3 `bc9d8`가 쓰는 설치 값): D0.W := 8, WORD `76` := D0.W, anim(`e3`, `200140`, `90`)(복귀 `bca5c`). **`bca5c`**: 설치 `bca62`. **`bca62`**: `JSR 43e34`(복귀 `bca68`). **`bca68`**: `JSR 49fc6`(복귀 `bca6e`; C는 읽지 않음). **`bca6e`**: A0 := LONG `c`, BYTE `62(A0)` = 0 → `bca88`, 아니면 `bca7a`: WORD `76` −= 1, 옛 WORD ≠ 0 → `bca88`, 아니면 `bca82`: LONG `(A6)` := `bc93c`(쓰기만). **`bca88`**: BYTE `63(A0)` = 0 → `bca9e RTS`, 아니면 `bca90`: WORD `76` −= 1, 옛 WORD ≠ 0 → `bca9e`, 아니면 `bca98`: LONG `(A6)` := `bcaa0`(쓰기만; fall-through `bca9e`). A0는 `bca6e`가 정한 값이 block 경계를 넘어 쓰인다.
- **`bc7d6`**(FR1c `bc716`의 `28ae` 자식 값): D0.W := 0, D1.W := 0(`MOVE.W`: 상위 WORD 유지), `JSR 49290`(복귀 `bc7e4`). **`bc7e4`**: `JSR 491c4`(복귀 `bc7ea`). **`bc7ea`**: D0.W := `4f`, D1.W := `37`, D2.B := 0, `JSR c6a96`(복귀 `bc7fc`). **`bc7fc`**: anim(`e3`, `200140`, `dc`)(복귀 `bc824`). **`bc824`**: WORD `68` `1e` := `8838`, 설치 `bc836`. **`bc836`**: `JSR 43e34`(복귀 `bc83c`). **`bc83c`**: `JSR 49fc6`(복귀 `bc842`). **`bc842`**: `RTS`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다(점프 표는 routing으로 간다).

| 표 | 범위 | 읽는 곳 | 내용 |
| --- | --- | --- | --- |
| 점프 표 1 | `cc7ac..cc818`(27 × `BRA.W`) | `cc7a0`(계산 대상) | index `0`..`1a` → 대상: 0 `cdc1c`, 1 `cdc1c`, 2 `cdc1c`, 3 `cd0fe`, 4 `cd370`, 5 `cd7c6`, 6 `cd94e`, 7 `ccc88`, 8 `cdc1c`, 9 `cd7c6`, a `ccf4e`, b `ccd74`, c `cdb08`, d `cdb08`, e..`1a` `cdc1c`. 바이트 `6000146e 6000146a 60001466 60000944 60000bb2 60001004 60001188 600004be 6000144e 60000ff4 60000778 6000059a 6000132a 60001326 60001436 60001432 6000142e 6000142a 60001426 60001422 6000141e 6000141a 60001416 60001412 6000140e 6000140a 60001406` |
| 점프 표 2 | `cc82e..cc89a`(27 × `BRA.W`) | `cc822`(계산 대상) | 0 `cdc1c`, 1 `cdc1c`, 2 `cdc1c`, 3 `cd0fe`, 4 `cdc1c`, 5 `cd7c6`, 6 `ccaf8`, 7 `ccc88`, 8 `cdc1c`, 9 `cdc1c`, a `ccf4e`, b `ccd74`, c..`1a` `cdc1c`. 바이트 `600013ec 600013e8 600013e4 600008c2 600013dc 60000f82 600002b0 6000043c 600013cc 600013c8 600006f6 60000518 600013bc 600013b8 600013b4 600013b0 600013ac 600013a8 600013a4 600013a0 6000139c 60001398 60001394 60001390 6000138c 60001388 60001384` |
| 소리 LONG | `cdf3e..cdf56`(6 LONG) | `cc610` `cc654`(index 4·WORD `8c`, sext) | `000cdf56 000cdf5e 000cdf66 000cdf6e 000cdf76 000cdf7e`; 기록 WORD 4개씩: `0c49 0c4d 0c4a ffff` / `0c4e 0c54 0c4f ffff` / `0c55 0c5a 0c56 0c59` / `0c5b 0c5e 0c5c ffff` / `0000 0000 0c60 0000` / `0c87 0c8b 0c8a 0c89`(이 단위는 `+0` `+2`만 읽음) |
| 처리기 인자 | `cdeea..cdf06`, `cdef8..` | `7355c` `73582`(A0, `cca80`이 LONG `82`에 저장) | 이 단위는 주소만 넘긴다 |
| 상자 | `72d5e..72d66`(`fff8 fff0 0010 0050`), `87a8c..87a94`(`fff0 fff8 0020 0010`) | callee `1ab80` / `1ab02`의 A0 | 이 단위는 주소만 넘긴다 |
| bank LONG | CPU `2000d0` `2000d4` `200080` `200140` | anim 꼴(`LONG d(…)`), `7355c`/`73582`(LONG 자체), `87986`(색인) | 물리 `200000` bank 값은 V1·실제 ROM 차분이 원본으로 읽는다(단위 시험은 합성). [U] 물리 `300000` bank에서의 쓰임 |

- [F] **callee에게 넘기기만 하는 자료**: `28ae` 자식 `8790c`(`878dc`), `c6a96` `49290` `491c4` `4970a` `70036` `4bc04` `8ebe` `4ae4a`(A0 = LONG `72`) `e9112`의 D0..D3/A0.

## 경계·routing 밖 출구

- [F] 이 단위 안에는 live 대상 호출·TRAP이 없다. 설치 쓰기의 정지 값(FR3 결정 2)은 실행하지 않는다.
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 11개: `8790a` `87a6a` `87a8a` `87aa8` `bc842` `bca9e` `cc694` `cc818` `ccab6` `cdc1c`(설치 쓰기 뒤) — node callback의 복귀와 helper의 복귀.
- [F] **계산 점프 대상**(결정 2): `cc7a0`/`cc822`가 정한 PC는 routing으로 간다. 자연 경로(`cc798`/`cc81a`를 거침)의 대상은 표 항목 27개 중 하나이고 이 단위에서는 routing 밖이라 `unsupported animation machine PC`다(FR4b가 routing하면 그 block). 직접 진입에서 D0.B ≥ `1b`이면 대상은 `cc7ac..cdba8` / `cc82e..cdc2a`: 이 단위의 block 시작(`cc818` `cc81a` `cc822` `cca76` `cca80` `cca9c` `ccaa8` `ccab6` `cdc1c`)이면 그 block(원본과 같이 실행), 이 단위의 다른 짝수 PC면 `unsupported animation objects fr4 PC`(F1 결정 3: 명령 중간 착지는 checked 오류), 그 밖은 그 PC의 routing. index.W가 4의 배수라 홀수 대상은 없다.
- [F] **native 정지 규칙 주의**(V1): FR2 spec의 `first_unrouted`(`8c16 < pc <= 8ca6` 내부, 정지 `2a00` `2a24`, 홀수 live 정지 PC 버림)를 그대로 쓴다. `BEQ.W 71a80`·`BRA.W 70054`·`JMP 2a00`은 routing된 출구다. 계산 점프 대상은 routing 밖 첫 PC로 멈춘다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1·FR2·FR2b·FR3 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 자연 node, LONG `c(A6)` := 자연 node, 스택 WORD, PC).
- [I] IO 관측 상태가 이 단위의 실제 진입 상태다(`fr3/ioA/frontier.json`의 확정 frontier와 위 "자연 후속 확인"). V1 spec에는 이 출처를 주석으로 적고, IO 비교 재실행(검증 작업자)이 자연 경로를 직접 확인한다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `7054c` → `73124`(`73120`), `1ab80` → `73468`(`7345e`), `28ae` → `878ec`(`878dc`), `1ab02` → `87a9e`(`87a94`), `497a6` → `cc60c`(`cc606`)·`cc638`(`cc632`)·`cc67c`(`cc676`). seed world에서 두 C 값이 다 나오도록 hint를 둔다: `7054c`(BYTE `61` bit 5, BYTE `82` bit 4 조합), `497a6`(BYTE `10fd92` = 0 / ≠ 0), `28ae`(빈 node 목록 있음 / 없음 [I]), `1ab80`/`1ab02`(위치 WORD `42` `46`을 화면 안 / 밖). 단위 시험은 RAM·합성 자료만 읽는 생산자만 실제 사슬로 넣고(생성기가 두 C 값을 모두 만들어 낸 것), 나머지는 선언 C 행만 둔다(V1·실제 ROM 차분이 실제 사슬).
- node fixture: callback·설치 값(`72f8a` `730a6` `73296` `73392` `878dc` `8790c` `87982` `87a3e` `87a50` `bca2c` `bca62` `bc7d6` `bc836`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. `cc778`은 `JMP` 진입(node 문맥: 복귀 LONG = dispatcher)으로 실행한다.
- callee fixture: `cc600` `cca76` `87a6c`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, FR3 꼴): 시작 192개 × 들어오는 C 3가지, zero-step, 내부 PC 908개 정확한 오류, 경계 stop(출구 전부), 계산 점프 대상 전부(표 index `0..1a`의 stop-only 확인, D0.B ≥ `1b` 직접 진입의 단위 안 시작·내부 착지), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), 그리고 빈틈 종류별 hint:
  - 부호·영 확장: `7310c` `MOVEM.W` 부호 확장(넣은 WORD `8000`/`7fff`), `cc610`/`cc654` 표 index의 sext(WORD `8c` = `2000`/`e000`: 4배가 WORD `8000`) — 합성 ROM 위치로, `87986` D1.W = 4·D0.W의 sext(D0.W = `2000`), `73506` `MOVEQ #0; MOVE.W` 영 확장(WORD `8c` = `ff89..ffff`: `ADDI.W #77`이 WORD 안에서 넘침).
  - 음수 색인: 위 `cc610`/`cc654`/`87986`.
  - 꺼낸 레지스터: `7310c`의 D2/D3(넣은 순서와 부호 확장).
  - RAM 거울: `734ee`의 WORD `53a2(A5)`를 A5 = `1f8000`에서(거울 `10d3a2`), node A6를 거울 위쪽(`1fe000`)에서 몇 행.
  - bit 조합: `730e0` BCHG, `7348c`/`73496` BSET/BCLR #0, `732e4`/`732ee`, `87a3e` BSET #3, `cca76` BSET #6(옛 bit 0/1), `ccab6` SNE(BYTE `15` = `00` `7f` `80` `ff`), `730a6`/`732c2`/`733bc`/`87a02` BTST #7, `730b0`/`732d2`/`87a12` BTST #0(BYTE `61`), `73542` BTST #7(BYTE `61`).
  - 상위 레지스터 bit: `MOVE.W #imm,D0/D1/D2`(`bc7d6` `7355c` `73582` `87a6c` `878f0`), `MOVE.B #0,D1`(`cc646`), `ANDI.B #7,D0`(`730d8`), `ANDI.W #1`(`73482`), `ASR.W`/`NEG.W`/`ADD.W`/`SUB.W`(`734ac`..`734da`의 D0..D3 상위 WORD), `ADD.W D1,D0`(`87a88`), `LSL.W #2`(`73296`).
  - 동점(같은 값): `73304` WORD `46` = `17f`/`180`/`181`, `87a78` D1.W = 4/5/8/`a`(−D1.W >> 1 = 4), `cc798`/`cc81a` D0.B = `1a`/`1b`/`ff`, `730d8` D0.B ∧ 7 = 0, `73520` `BVS` 경계(LONG `8e` + D2 = `7fffffff`/`80000000`), `bca7a`/`bca90`/`87a5c` WORD `76` = 0/1, `732dc` WORD `64` = `7fff`/`8000`.
  - 큰 값: `72f90` D0 ∧ `ff` − `80`(D0 = `ffffff7f`/`80`/`7f`), `7306a` D0 ∧ `ffff` + `40000`, `7308e` LSL.L #6 넘침 bit, `73392` ASR.L #5의 음수.

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `tools/probe_scan_fr4.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_fr4.out` 155줄; 생성 표의 무작위 레지스터 값은 진입·stop 열만 걸러 봄)으로 확인한 결과:
  - 그대로 참인 것(stop-only·자기 범위 끝·주석): N04(`72dd8` `72df2` `72e18` `72de2` 행 stop `cc778`, `at_pc[]`·`want[]` `cc778`), N15(`76ef4` 행 stop `cc778`, `at_pc[]`), N16(`78c76`..`78c9a` 행 stop `cc778`, `at_pc[]`), N17(`7a48e` `7a4aa` 행 stop `cc778`, `at_pc[]`), N18(`8625a`..`86324` 행 stop `cc778`, `at_pc[]`), N20(`73620` `7362a` 행 stop `cc778`, `at_pc[]`), FR1c(`bc716` 행 stop `28ae`, `RANGES` 끝 `bc7d6`), FR3(`RANGES` 끝 `bca2c`), spec `fr1c.py`·`fr3.py`(`RANGES` 끝).
  - 옮길 것: 정적 검색에서는 없다. [I] `make -j3 all test`에서 깨지는 숨은 탐침이 나오면 결정 6대로 옮기고 이 절에 더한다.
- [I] V1 spec 중 native 사슬이 `cc778` `72f8a` `878dc` `bca2c` `bc7d6`를 첫 routing 밖 PC로 멈추던 것은 더 진행한다(정지는 routing에서 계산되므로 spec 수정은 필요 없을 것으로 본다; 검증 작업자가 회귀로 확인). 특히 N04/N15/N16/N17/N18/N20 spec의 `cc778` 정지 행은 이제 `cc778` 안으로 들어가 `cca76` `cc600` `497a6` `8ebe` `e9112`를 거쳐 표 점프 항목(routing 밖)이나 `cdc1c`·`cc818` 복귀까지 간다.
- [F] stage_event / stage_event_ops 검증기의 `CPP_PINS`(`animation_machine.cpp` `869a9dc1…`, `animation_machine_internal.h` `f7953e9a…`)는 이 단위의 공유 수정으로 맞지 않게 된다(FR1..FR3 관례대로 새 값으로 갱신 필요; 메인 결정, 새 값은 "구현·검증 기록").

## 결정

1. **범위.** FR4 = 계획 §4의 root 묶음 closure **192 block**(15 범위; `72f8a` 95, `cc778` 처리기 입구 31, `878dc` 47, `bca2c` 11, `bc7d6` 8). 두 IO frontier(`72f8a` 12 run, `878dc` 3 run)의 자연 후속을 600 frame 끝까지 모두 덮는다. 정지 설치 값 `733d0` `bcaa0` `cdc24`.
2. **계산 점프 `cc7a8`/`cc82a`.** 두 표(27 항목씩)는 이 계약에 전부 전사한다(대상 10종). 실행부는 PC := 표 시작 + sext(4·(D0.W ∧ `ff`))로 옮기고 대상 검사는 routing에 맡긴다(FR1 결정 3과 같은 꼴). 표 항목 54개 block과 처리기 closure(계획 셈으로 597 − 201 = 약 396 block, 그중 항목 54)는 이 단위에 넣지 않는다: 한 단위(약 220)를 넘고 IO 관측에서 실행되지 않으며(C 뒤 boot-demo-0도 `cdc1c` 쪽) 모두 C 뒤 D다. **제안**: FR4b = 표 항목 54 + 처리기 `cdc24`(`cdc1c`의 설치 값, closure 약 66) `ccaf8` `ccc88` 묶음, FR4c = `ccd74` `ccf4e` `cd0fe` `cd370` `cd7c6` `cd94e` `cdb08` 나머지(재측정 필요; `cd94e`는 다시 `cc778`로 돌아오는 큰 closure). 메인이 FR7..FR9(C 뒤 D)와 묶어 순서를 정한다. 그 전에는 자연 경로에서 index < `1b`인 피격 처리가 `unsupported animation machine PC`(표 항목)로 멈춘다 — IO 관측에는 그런 실행이 없다.
3. **carry 보존 목록.** 소비자 7개(`73124` `73468` `878ec` `87a9e` `cc60c` `cc638` `cc67c`). C를 넘기는 `RTS` 없음, known C 생산 block 없음.
4. **설치 값.** `MOVE.L #v,(A6)`은 v가 바로 다음 PC일 때만 그 block으로 들어간다(`730a6` `73296` `73392` `87982` `87a50` `bc836` `bca62`). 나머지(`72f8a` `87a3e` `71a80` `72d42` `bc93c` `733d0` `bcaa0` `cdc24`)는 LONG 쓰기뿐이다.
5. **F4 범위 문서 U27과의 겹침.** U27 `cc778..cc822`와 겹치는 `cc778..cc7ac` `cc818..cc82e`(그리고 U27 "외 2"·U28/U30의 간접 `cc7a8` `cc82a`)는 FR4가 routing한다. 그 단위들은 착수할 때 이 범위를 빼고 다시 잰다.
6. **숨은 탐침 이전.** 정적 검색에서 이전 대상 없음. stage_event / stage_event_ops `CPP_PINS` 갱신은 메인이 정한다.
7. **TB 시작 PC.** IO 관측의 TB 시작 `72fe0` `72fe6` `72fee` `72ff2` `72ff6` `72ffa` `72ffe`는 block 시작이 아니다(내부 PC 오류).
8. **다음.** 이 단위 뒤 D 첫 정지: `5ab82`(FR5, 3 run), `50dae`(FR6, 3 run). FR4의 run 15개는 600 frame 끝까지 간다 [I].

## 미확인

- [U] node field 의미(BYTE `15` `17` `5e` `61` `62` `63` `76` `77` `78` `79` `7a` `7b` `7c` `7d` `83`, WORD `1e` `20` `2c` `42` `46` `68` `76` `8a` `8c` `96` `9a` `9c`, LONG `36` `3a` `56` `64` `72` `7e` `82` `86` `8e` `92` `9e`), BYTE `10fd92`, WORD `53a2(A5)`, 표 `cdf3e`·`cdeea`·`cdef8` 값의 의미.
- [U] `cc610`/`cc654`의 WORD `8c`가 항상 0..5인지, `87986`의 D0.W(= `87a6c`의 `13..17`)가 bank 표 범위 안인지(원본에 상한 검사 없음).
- [U] 물리 `300000` bank에서 bank 창 LONG의 쓰임.
- [U] 표 항목·처리기(`ccaf8` … `cdb08`)의 의미와 정확한 closure(FR4b/FR4c 착수 때 그 시점 routing으로 다시 잼).
- [U] 자연 frame에서 이 단위 뒤 run별 다음 첫 미routing PC(IO 비교 재실행으로 확인; [I] 예상은 결정 8).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr4.cpp`(case label 192 = scratch `starts_fr4.txt`와 집합 일치), `engine/tests/animation_machine_objects_fr4_test.cpp`(생성 구역 + 수작성 규칙: 두 계산 점프의 index `0..1a` 54개 stop-only와 WORD index, `cc784`를 거친 표 선택(BYTE `15` bit 7)과 BYTE `5e` 지움, index ≥ `1b`의 `cdc1c`, 직접 진입 착지 `1b` → `cc818`(RTS)·`92` → `cca76`·`ff` → `ccba8`(stop-only), `7310c` MOVEM.W 부호 확장, `730fa` push 순서, `73520` BVS 양쪽 부호와 LSL.L / ASR.L / ADD.W / SUB.L, `73506` MOVEQ / MOVE.W 영 확장과 ADDI.W 넘침, `734be` / `734ac` ASR.W / SWAP / ASR.L, `7308e` LSL.L / SWAP / ADDI.W, `72f90` ANDI.L / SUBI.L, `73392` ASR.L #5, `87a78` / `87a6c` NEG.W / LSR.W / 부호 BLE, `87986`·`cc610`의 음수 WORD 색인(합성 위치 `29d000`·`c5f3e`; 영 확장이면 비매핑), `cc654` 기록 +2, `cca80` / `ccab6` BYTE 쓰기와 이웃, SNE, `cca76` BSET 옛 bit, `7347a` SUBQ.W / ANDI.W와 BSET / BCLR, LONG `9e`, `73304` / `cc798` 무부호 비교, `730d8` ANDI.B, `73296` / `732ac` WORD 연산, `730ba` LONG 연산, 범위 옆 자료 PC `87a8c` `72d5e`의 dispatcher 오류), `tools/generate_animation_machine_objects_fr4_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; 두 번 실행해 시험 파일 바이트 단위 같음 SHA256 `d586e25d52ab6b61…`, 약 65초), `tools/unit_fixture_specs/fr4.py`(V1 spec; FR3 spec의 공용 부분 그대로, 단위 부분 교체: 연속 Bcc 묶음 `cc62e` `cc672`, 소리 index WORD `8c`, BYTE `10fd92`, WORD `53a2(A5)`, 계산 착지 오류 행 `cc81c` `cca7a`). 공유 수정은 "공통 규칙"의 다섯 곳뿐이다(기존 시험·spec의 이전 없음).
- [F] 정적 spec 검사(scratch `spec_static.py`): `load_routing` 규칙 125개 뒤 시작 192개와 내부 908개가 모두 `animation_objects_fr4_block`, sentinel·자료 PC(`87a8c` `72d5e`)는 routing 밖, 정적 후속은 시작이거나 routing된 출구(routing 밖 출구 0; 계산 점프는 정적 후속 없음), 사슬 7개의 소비자가 진입에서 닿음, block 명령 합 499. 합성 기반 상태와 가짜 tracer로 world·hint·error·chain/node/callee 생성 함수를 native 없이 실행(scratch `spec_dry.py`): Python 오류 0, world 619, 오류 fixture 931개(내부 908 + 홀수 1 + Unknown C 7 + 홀수 node/stack 3 + 계산 착지 2 + 실행 뒤 실패 4 + failpc 짝 6) 이름 중복 0.
- [F] 단위 시험 world: A7 = `10ef00`, 합성 typed physical byte(ROM 자료 아님, 자료 영역만): 소리 표 `cdf3e..cdf56`(RAM 기록 `10fe40 + 8k`를 가리킴), 상자 `72d5e..72d66` `87a8c..87a94`, bank 창 `2000d0`(→ `2a1000`, LONG `4` `c` `28`) `2000d4`(→ `2a2000`) `200080`(→ `2a5000`, LONG `4c..5c`) `200140`(→ `2a6000`, LONG `90` `dc`). 생성기가 실제 생산자 사슬을 두 C 값 모두로 만들어 남긴 것: `7054c` → `73124`, `1ab80` → `73468`, `1ab02` → `87a9e`, `497a6` → `cc60c`·`cc638`·`cc67c`. `28ae` → `878ec`는 Clear만 나와(빈 node 목록 없음) 선언 C 행만 있다(V1·실제 ROM 차분이 실제 사슬). 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0.
- [F] `make -j3 all test`(작업자, scratch `make_all1.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 277개, Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR4 시험 줄: `animation machine objects fr4: 722 fixtures (532 single-block, 121 path, 36 producer chain, 14 declared C, 19 checked error (7 with a later failing PC), 50 kept C), 192 blocks, 4004 calls, 102829 checks`. FR3 최종 기준(scratch `fr3/make_all4.log`) 대비 다른 시험 줄 변화는 없다(stop-only로 `cc778`을 보던 N04/N15/N16/N17/N18/N20 시험 그대로 통과; 이전이 필요한 기존 시험 없음).
- [F] `dleft.py`(이 worktree routing `31a1b033…`): 실행된 routing 밖 PC D 502 / E 220 / C 620, D 중 C 무관 155 / C 뒤 347, 예측 일치 **163,350**, 첫 정지 영역 D 6 / C·E 15 / C·D 1.
- [F] 검증 작업자 준비물(scratch, 실행하지 않음): `build_ubsan.sh`, `mut/run_mut.py`·`mut/mutants.py`(변이 288개; 패턴 유일성 확인, `--check`는 문법 검사까지 통과), `realrom/real_fr4.py`(FR3 harness에 FR4 world·소비자·진입, 계산 점프 `cc7a8` `cc82a` 착지 분류; `py_compile`만), `runwrap.py` `run_frames.sh` `run_area_clear.py` `run_stage_entry.py` `run_regs.sh`(회귀 목록에 `fr3` 추가) `v1_all.sh` `v1_one.sh` `io_ab.sh` `io_delta.py`(FR3 재실행 `fr3/ioA` 대비) `legacy/`(경로만 바꿈). 실행 순서와 기대값은 scratch `HANDOFF.md`.
- [F] stage_event / stage_event_ops `CPP_PINS` 새 값(메인이 갱신): `animation_machine.cpp` `31a1b033911fd15cfed40998c1072f32db29a85d7605848e1049b1bbf86735c8`, `animation_machine_internal.h` `8570d1e86121aa5ad8432c716d2787cdc69ef5cb26bbc9cb3a78742edd7625e0`.

### 검증 기록(검증 작업자, Sonnet 5.5 / medium)

- [F] 환경: ROM SHA256 `29112a94…` 불변, 모든 명령 `MS5_SEED_DIR=artifacts/stage_entry_body`. 결과물은 scratch `ms5-scratch/fr4/`.
- [F] `make -j3 all test`(재실행 `make_all3.log`): 종료 0, 경고 0, Assert 0, Python 310개 OK. FR4 시험 줄: 722 fixtures, 192 blocks, **4006 calls, 102831 checks**(변이 생존자 보강 뒤).
- [F] UBSan(`build_ubsan.sh`, 시험 수정 뒤 재실행 `ubsan2.log`): 종료 0, `runtime error` 0.
- [F] 변이 288개: 284 killed + 시험 보강 뒤 2 killed(`87a78-lt`, `732dc-long`) + 동등 2개. 생존자와 처리: `87a78-lt`(BLE → BLT)는 동점 4에서 `87a84`(`MOVE.W #4,D1`)를 거쳐도 D1.W = 4로 같아서 `87a88` stop만으로는 구분되지 않았다 → 시험에 "`87a84`를 stop으로 두면 진입하지 않음" 규칙 추가. `732dc-long`(`TST.W` → `TST.L`)은 부호 비트가 같아 읽기 범위 경계에서만 다르다 → A6 = `1fff9a`(WORD `1ffffe`, LONG은 bank 창으로 넘어가 오류) 규칙 추가. `sw-unsigned`·`87a78-unsigned`는 동등: `87a78`의 `LSR.W #1` 결과는 항상 `<= 7fff`라 부호 확장과 무부호 값이 같다.
- [F] real ROM 차분(Unicorn 대 C++, 5 × 1,500, `realrom/`): harness 수정 뒤 5배치 모두 mismatches 0, 시작 192/192 덮음(s2만 `73010` 빠짐, 다른 배치가 덮음), 소비자 7개 모두 실제 생산자 뒤 비교됨. 첫 실행은 25 mismatch였고 원인은 harness 분류: 계산 점프 표 항목(`cc7ac+4k`, `cc82e+4k`, 계약 결정 2에서 stop 전용)을 선언된 stop으로 두지 않아 native만 항목을 지나갔다 — 표 항목 54 PC를 `UNR`(선언된 stop)로 넣고 같은 seed로 재실행(C++ 변경 없음).
- [F] V1 `fr4` 2회: 1,629 fixtures 모두 ok(match 694, error 925, 의도한 negative 대조 mismatch 10), `report.json` 행별 digest 동일. 첫 실행 spec 수정 3건(spec만): ① 노드 world `bc7d6`/`bc836`이 `49290`→`8ebe`→TRAP #15(`8ec8`)로 가서 추적 불가 → 노드 hint에 BYTE `1d` = 0..3(FR1c와 같은 꼴), ② 묶음 `BEQ.W/BPL.W` block(`cc610` `cc654`)에서 BEQ가 잡히면 후속이 `pcs[n-1]`이라 `block_next()`로 계산(그전엔 후속 `cc650`/`cc694`가 빠진 것으로 보임), ③ `87a28`의 LONG `72` != 0 hint 추가(후속 `87a30`). 최종: carry oracle ok, visited 192/192, missing successors / unreachable outcomes = `878ec -> 8790a` 하나. 이유: `28ae`의 Clear 반환은 실패 경로(`2986`)이고 caller의 X가 필요한 기존 checked 오류(FR1/FR3 문서화 차이)라 V1에서 성공 successor로는 만들 수 없다 [I]. 회귀 26 spec 모두 ok, 개수는 FR3 기준과 같고 `b1a`만 2,807 → 2,801(전부 ok): 사슬 `78408`·`7853e`가 이전에는 `cc778`에서 멈췄고 이제 FR4를 지나 더 멀리 가서 fixture 6개(`chain-78408-2/3`, `chain-7853e-2`, `chainexit-*`)가 같은 stop으로 합쳐졌다.
- [F] frame: D1 / controller game / IRQ 54,400/54,400, demo 45,684/45,684, natural mismatch 0. FR3 `verification.json`과 비교하면 바뀐 frame 없음(차이는 입력 파일 목록의 `animation_machine_objects_fr4.cpp` 한 줄뿐; `report_sha256`은 routing 파일 해시 때문에 다름).
- [F] 기존 검증기: `stage_entry` cases 335 / split 23,761 / negatives 2,757 / carry 21,829·100·1,832, `area_clear` conditions 256 / frames 37,418 / split 117,537 / continuous 37,444 / negatives 181 / guards 26, `stage_event`(pin 새 값) typed 560 / phases 22,870 / negatives 1,020, `stage_event_ops` typed 284 / phases 5,081 / negatives 894, `frame_helpers` 199 / 3,683 / 180, `card_menu_close` 82 / 7,886 / 85, `objects_g1` 4,752행(execution-equal 4,689, checked-boundary 54, native-step-limit 8, invalid-declared-flag-precondition 1) rc 0 — 모두 기대와 같음.
- [F] IO(`verify_animation_machine_io`, `--workers 1`, 2회): `verification.json` SHA `73c0138b…`, `frontier.json` `480abb51…` 두 번 동일, `diff -rq`(harness_stderr·run_info.json 제외) 깨끗. mismatches 0, unexpected C++ errors 0, P0 81,600 불변. 일치 frame **161,229 → 163,350 (+2,121 = 예측 일치)**: P1 +1,726, P1b +395, 나머지 불변. frontier run 39 → **24**; 제거된 첫 정지 `72f8a` 12, `878dc` 3. 남은 첫 정지: `4e68e` 15, `5ab82` 3, `50dae` 3, `1d1f4` 1, fixture `2634` 2. `dleft.py`: D 640 → **502**(C 무관 155, C 뒤 347), 예측 163,350.
- [F] 이 검증으로 바뀐 파일: `engine/tests/animation_machine_objects_fr4_test.cpp`(수작성 규칙 2개 추가; 생성기를 다시 돌려도 같음), `tools/unit_fixture_specs/fr4.py`(위 spec 수정 3건), stage_event / stage_event_ops `CPP_PINS`(`31a1b033…` / `8570d1e8…`, 이전 값은 주석에 보존), `area-d-completion-plan.md` §4 메모. 실행부(`animation_machine_objects_fr4.cpp`)는 바꾸지 않았다.

## block 목록

[F] scratch `starts_fr4.txt`(SHA256 `3652aa0ce2eb34078244a1ab10912976a3cc498a8f6aab6b43efdac695c8c22e`)와 같다.

- **`72f8a..73132`(33)**: `72f8a 72f90 72fa8 72fb0 72fd8 72fdc 73004 73008 73010 73038 7303c 73064 7306a 73080 73082 7308c 7308e 730a6 730b0 730ba 730d2 730d8 730e0 730ea 730f8 730fa 7310c 73114 7311a 73120 73124 73128 7312e`
- **`73218..733d0`(33)**: `73218 73220 73248 7324c 73274 73284 73286 73296 732ac 732be 732c2 732cc 732d2 732dc 732e4 732ee 732f4 732fa 73300 73304 7330e 73316 73326 73328 73338 73360 73364 7338c 73392 733b6 733bc 733c6 733cc`
- **`7345e..7357c`(27)**: `7345e 73468 7346c 7347a 73482 7348c 73496 7349c 734a6 734ac 734b2 734b4 734bc 734be 734ce 734d0 734d8 734da 734ee 73506 7351e 73520 73538 7353c 73542 7354c 7355c`
- **`73582..735a2`(1)**: `73582`
- **`735a4..735a8`(1)**: `735a4`
- **`878dc..87a3c`(32)**: `878dc 878ec 878f0 878fe 87900 8790a 8790c 87912 87932 87936 87954 8797c 87982 87986 879b6 879c0 879c8 879d0 879d4 879dc 879e4 879ec 879f4 879fc 87a02 87a0c 87a12 87a1c 87a22 87a28 87a30 87a38`
- **`87a3e..87a8c`(11)**: `87a3e 87a50 87a56 87a5c 87a64 87a6a 87a6c 87a78 87a84 87a88 87a8a`
- **`87a94..87aaa`(4)**: `87a94 87a9e 87aa2 87aa8`
- **`bc7d6..bc844`(8)**: `bc7d6 bc7e4 bc7ea bc7fc bc824 bc836 bc83c bc842`
- **`bca2c..bcaa0`(11)**: `bca2c bca5c bca62 bca68 bca6e bca7a bca82 bca88 bca90 bca98 bca9e`
- **`cc600..cc696`(17)**: `cc600 cc606 cc60c cc610 cc632 cc638 cc63c cc642 cc646 cc650 cc654 cc676 cc67c cc680 cc686 cc68a cc694`
- **`cc778..cc7ac`(5)**: `cc778 cc780 cc784 cc798 cc7a0`
- **`cc818..cc82e`(3)**: `cc818 cc81a cc822`
- **`cca76..ccade`(5)**: `cca76 cca80 cca9c ccaa8 ccab6`
- **`cdc1c..cdc24`(1)**: `cdc1c`
