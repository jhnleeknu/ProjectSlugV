# frontier 단위 FR8(C 뒤에만 IO에 나타나는 영역 D: 객체 `42d9c`/`42e68`(계산 점프 `42f9e`), `d3500` 계열, `cdc24`, `38e92` 계열, `aea38`/`ae930` 계열, FR4 표 항목 `cc7b4`) 구현 계약과 FR9 명세

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. FR7 계약(`animation-machine-frontier-fr7-contract.md`)의 구조·공통 규칙을 따르고 다른 점만 적는다. 메인 지시: `area-d-completion-plan.md` §4와 FR7 계약에 따라 남은 C 뒤 영역 D(FR7 뒤 `dleft.py` 124 PC, 모두 C 뒤)를 FR8과 FR9로 나눈다. FR8 = native 실행 수가 가장 큰 root를 자연스러운 closure로 약 220 block까지, 나머지는 FR9로 이 문서에 범위·block·표까지 명세한다(FR8 + FR9 = 124 PC 전부). 계산 표는 모두 전사하고 TRAP 자리는 checked 경계다. C 뒤 코드라 단위 시험·V1은 선언 상태와 IO state pack의 자연 node 상태(family `natural`)로 선다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기 `200038` `200094` `200138`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `4627da8`(branch `claude/fr8-core` = `main`, FR1..FR7 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `298c64da5f6ab9483acc7b1e39c0b733ea0908cb685c058621faa500ffbec51f`(= FR7 검증의 routing), `animation_machine_internal.h` `69b45dcd7444ae6411e238106b33c3f2f5098d10525e0ed93f78f21f237813fd`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; run 기록의 `unr_pcs`/`unr_new`, state pack `states/<config>/<case>.pack.gz`). FR7 IO 재실행 일치 frame **165,714**, D 첫 정지 0.
- [F] 정적 디코드: capstone M68000, FR4..FR7과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, `MOVE.L #imm,(A6)` 설치 값 중 범위 안의 것, 범위 밖에서 들어오는 실제 분기 대상, 연속 Bcc 묶음은 한 block). routing된 PC, `RTS`, `TRAP`에서 멈춘다. **새 규칙(결정 2): PC 상대 계산 점프 `JMP d(PC,D0.W)` 뒤의 `BRA.W` 표는 경계식으로 항목 수를 정해 모든 항목을 block 시작으로 두고 그 `BRA.W` 대상을 일반 분기처럼 따라간다**(FR4 `cc7a8`/`cc82a`는 표 항목을 다음 단위로 미뤘다). `28ae`/`2986` 자식 값은 기록만 한다. 진입 = 아래 root들이 IO run에서 실제로 실행한 routing 밖 PC(다른 진입의 closure 안에 이미 든 것은 뺌). 설치 값은 native가 실행한 것만 따라간다(FR3 결정 2).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr8/`
  - `tools/`: FR7 scratch 도구의 경로만 새 배치(`metalslug-fr8`, `ms5-scratch/fr8`)로 바꾼 사본(`fclos.py` `hroute.py` `dstate.py` `dleft.py` `refidx.py` `cread.py` `fr7roots.py` …)과 새 `fr8tab.py`(계산 점프 표 8개의 경계·항목 전사), `fr8set.py`(표를 leader로 넣은 합집합 closure의 누적 block 수와 예측), `unit_fr8.py`(`unit_fr7.py` + 표 전사; 묶음은 환경 변수 `FRG`), `cscan.py`(block 경계를 건너 C를 읽는 block 전수), `inrefs7.py`/`inrefs9.py`(범위 밖에서 범위 안으로 들어오는 분기·상수 전수).
  - `starts_fr8.txt`(시작 229개) SHA256 `8a2f4e1a30776bb6f1f7de5c20c13492f00e2644fbea4b77bafe5553620a8e77`; `ranges_fr8.txt`, `unit_fr8.out`(block별·범위 전체 디코드), `inrefs8.out`, `probe_fr8.out`. FR9: `starts_fr9.txt`(220개) SHA256 `f2ba650fc7e314c55521b70677110119844e5feac9715bab04e634879b070dff`, `ranges_fr9.txt`, `unit_fr9.out`, `inrefs9.out`.
  - 재현: `cd /Users/start/Workspce/metalslug-fr8 && FRG='42d9c=42e68 42d9c;d3500=d383c d3554 d3802 d3500;cdc24=cdc24;38e92=38f0c 38e92 38eb4;aea38=aea68 aea54 aea4a aea38;cc7b4=cc778' .venv/bin/python /Users/start/Workspce/ms5-scratch/fr8/tools/unit_fr8.py B D`(FR9: `FRG='af990=af8cc af8f2 af910 af990 afcda afd7c aff00 aff30 b051a'`; 두 실행 모두 `starts_fr8.txt`에 쓰므로 FR9 실행 뒤에는 FR8 목록을 다시 만든다).
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정**(`dleft.py`, routing `298c64da…`): 실행된 routing 밖 PC는 C 620 / D 124 / E 220, D 중 C 무관 0 / **C 뒤 124**, 예측 일치 frame 165,714, 첫 정지 영역 C·E 15 / C 1(D 0). FR7 기록과 같다. 124 PC는 모두 `boot-demo-0` 한 run(frame 410..577)에서만 실행된다.
- [F] **root별 실행 수**(`fr7roots.py`, 같은 root의 실행 PC 합): `42e68` 1,362 · `42d9c` 152(같은 객체, 합 1,514) > `af990` 객체 계열(`af8f2` 78 `afd7c` 75 `aff30` 59 `af990` 20 `afcda` 10 `af8cc` 6 `aff00` 5 `b051a` 4 `af910` 4, 합 261) > `d3500` 계열(`d383c` 50 `d3554` 24 `d3802` 5 `d3500` 4, 합 83) > `38e92` 계열(`38f0c` 9 `38e92` 3 `38eb4` 1, 합 13) > `cdc24` 10 > `aea38` 계열(`aea38` `aea4a` `aea54` `aea68` 1씩, 합 4) > `cc778`(실행 PC `cc7b4` 1).
- [F] **closure 크기**(`fr8set.py`/`unit_fr8.py`, 표 전사 포함, 설치 값 중 범위 안 시작 포함): `42d9c` 객체 68, `af990` 객체 계열 **220**(계산 점프 7개의 표 항목 95 + 그 대상 handler), `d3500` 계열 36, `cdc24` 23, `38e92` 계열 41, `aea38` 계열 60(`ae930` 상태 기계와 `d39f6`/`d3a2e` helper), `cc7b4` 1. `af990` 계열은 표 항목 대상(`afb3e` `afbbe` `afba4` `afe98` `afe0a` `afda6` `aff52` `aff86`)까지 자연 closure라 더 쪼개면 한 객체의 상태를 나누게 된다.
- [F] **선택**: 실행 수 1위 `42d9c`(68)에 2위 `af990` 계열(220)을 더하면 288로 넘친다. 그래서 FR8 = `af990` 계열을 뺀 나머지 전부(**229 block**), FR9 = `af990` 계열(**220 block**)로 나눈다(결정 1). 다른 분할(`aea38` 계열 60을 FR9로)은 FR9가 280이 되어 둘 다 약 220을 지키지 못한다. FR8은 약 220보다 9 많다(4%; 메인이 바꾸면 `cc7b4` 1·`cdc24` 23을 FR9로 옮길 수 있으나 FR9가 그만큼 커진다).
- [F] **합계**(`unit_fr8.py`): **229 block 시작**, 12 범위, 명령 539, 짝수 PC 1,195(내부 966), 이어 붙인 바이트 2,390, SHA256 `8cb99aae4b2552cf59c0c47f7c1e8fd2a53180c5bd2d5aa6097937d19822014b`. 덮는 실행 PC **73개**(실행 1,625회, run 1: `boot-demo-0`), 모두 영역 D·C 뒤. 기존 routing과 겹침 0. 연속 Bcc 묶음 1(`cdcfe BEQ.W` + `cdd02 BPL.W`: `cdd02`는 시작이 아니다). TB 시작이지만 block 시작이 아닌 실행 PC 1개(`cdd02`, 묶음의 두 번째 Bcc)는 진입으로 쓰지 않는다(계획 §7).
- [F] **예측**(`fr8set.py`): IO 일치 frame **165,714 그대로**(C 뒤라 사슬이 닿지 않음), D 남은 실행 PC **124 → 51**(C 무관 0, C 뒤 51, 모두 FR9 `af990` 계열), 첫 정지 영역 변화 없음(C·E 15, C 1). FR9 뒤 0.
- [F] **F4 범위 문서와의 겹침**(`animation-machine-object-callbacks-f4-scope.md` 범위 식 전부와 교차): U27 행 `cc778..cc822`와 `cc7b4..cc7b8`(FR4가 이미 `cc778..cc7ac`·`cc818..cc82e`를 뺐다), U44 행 `38dd4..3a4a2`와 `38e92..38f0c` `38f14..38ff4`. 고분류 꼬리 행(`2b418..4dbd6`, 서술)은 범위 행이 아니다. FR9는 R09 행 `af3fe..b05bc`와 6 범위 전부 겹친다. 착수할 때 이 범위를 뺀다(결정 7).

| 묶음(진입) | block | 명령 | 실행 PC / 실행 수 | 범위 |
| --- | --- | --- | --- | --- |
| 객체 `42d9c`(B2e `3ac60 MOVEA.L #42d9c,A0; JSR 2986`의 자식; 설치 `42e68`; 계산 점프 `42f9a` + 표 9칸) + 자식 생성 꼬리 `430ba` | 65 + 3 | 185 | 20 / 1,514 | `42d9c..4309a` `430ba..430e6` |
| 객체 `d3500`(`d3802`의 `28ae` 자식; 설치 `d3554`) + 생성 helper `d3802`(밖 44곳의 `JSR`) + 위치 helper `d383c` | 8 + 7 + 21 | 79 | 25 / 83 | `d3500..d354c` `d354e..d3580` `d3802..d38e2` |
| 객체 `cdc24`(FR4 `cdc1c`·밖 `cd944`의 설치 값; 꼬리 `BRA cdd2e` FR7) | 23 | 58 | 10 / 10 | `cdc24..cdd2e` |
| 객체 `38e92`(N32/N32b `3906c` `3914c` `39722` `39d7c`의 설치 값; 설치 `38eb4` `38ece` `38ee2` `38f08`) | 15 + 26 | 82 | 13 / 13 | `38e92..38f0c` `38f14..38ff4` |
| 객체 `aea38`(LONG 표 `e8eac`의 값) + 상태 기계 `ae930`(설치 `aeab0` `aeb32`) + 자식 생성 helper `d39f6`/`d3a2e` | 51 + 1 + 8 | 134 | 4 / 4 | `ae930..aeb4c` `d39f6..d39fe` `d3a2e..d3a70` |
| FR4 계산 점프 `cc7a8`의 표 항목 `cc7b4`(결정 3) | 1 | 1 | 1 / 1 | `cc7b4..cc7b8` |
| 합 | **229** | 539 | 73 / 1,625 | 12 범위 |

## 요약

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `38e92..38f0c` | 122 | `633f979ddae54c525eec6e6dda08432a36861806a86e187f26cba5cb15b38234` | 15 | 61 |
| `38f14..38ff4` | 224 | `953e06174d31e7916266e891d7de3a7c9fab2a2c7bfa4b252c45ca2d135029d8` | 26 | 112 |
| `42d9c..4309a` | 766 | `bb55cdef4ffb17e2037c61ae6ee0911cf1d523558c319bbaea616e4d6f57b2d0` | 65 | 383 |
| `430ba..430e6` | 44 | `a90670c31a1f0a9a85cd8e4ae3fb0a91e3f5acc1cd00cc1bda046cf211a80d3d` | 3 | 22 |
| `ae930..aeb4c` | 540 | `141db722e4a52bd3cbba9de08086be3252837b0310e0c8267ad29823e4bf4ff9` | 51 | 270 |
| `cc7b4..cc7b8` | 4 | `74c77fdebd932fa3da7332d4a50098544711162de1803b3352c42df30ee526d3` | 1 | 2 |
| `cdc24..cdd2e` | 266 | `93415a9c2de65c413ce5b8af6048164a340952143398da16d494153c002e8ed5` | 23 | 133 |
| `d3500..d354c` | 76 | `b8a82a6ef25e64c5e67290b180127be7a4df446451db1c9cdf17d121e64f1991` | 8 | 38 |
| `d354e..d3580` | 50 | `8c23e342c760451679fd3badb3e1ae4962a033c6acee9bced3d9903d945f7367` | 7 | 25 |
| `d3802..d38e2` | 224 | `180e39ea1c04d9c8590dd35b66da8dbb11c548e9bbbe0eb3db878a7fe8c4cad6` | 21 | 112 |
| `d39f6..d39fe` | 8 | `cbbedd5c456cec8cf1a589a6a47d7a239259453e7fe135eca8f28efad9b51ae6` | 1 | 4 |
| `d3a2e..d3a70` | 66 | `625f3124269d581a7a39451570ffe9e51e10488032056dead1be515dccc6381b` | 8 | 33 |
| 합계 FR8 | 2390 | 이어 붙인 바이트 `8cb99aae4b2552cf59c0c47f7c1e8fd2a53180c5bd2d5aa6097937d19822014b` | **229** | 1195(내부 966) |

- [F] closure가 12 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 범위 사이는 자료(`38f0c..38f14` LONG 표, `4309a..430ba` 설치만 하는 값 `4309a`의 형제 코드, `d354c` 2 BYTE, `d3580..` N13, `d38e2..d39f6` 같은 꼴의 stub 약 25개, `d39fe..d3a2e` stub), routing된 코드(`38ff4..` N32, `cdc1c..cdc24` FR4, `cdd2e..` FR7, `d3580..` N13), 또는 routing 밖 형제 코드(`42a..42d9c` 자료, `430e6..` 자식 `430e6`의 몸통, `aeb4c..` 설치만 하는 `aeb4c`/`aec04`의 코드, `cc7ac..cc818` FR4 표의 나머지 항목)다.
- [F] **명령 종류**(539개; `unit_fr8.out` 집계): 계산 점프 `JMP 42fa2(PC,D0.W)` 1(표 `BRA.W` 9칸), `BRA.W` 표 항목 9 + `cc7b4` 1, `MOVEA.L (An,Dn.W),An` 5(`38eec` `42e6e` `aeaca` `cdce4` `d3898`; 자료 읽기), `MOVE.W (A0,D0.W),D0` 1(`cdce4`), `LSR.W #2/#3/#4/#8` 7, `LSL.W #8` 1, `ANDI.W`/`ANDI.B` 13, `ADDI.B`/`ADDQ.B` 6, `SUBQ.B` 2, `SUBQ.W` 6, `ADDQ.W #1,7e(A6)` 1, `NEG.W` 2, `CMPI.B` 9·`CMPI.W` 12·`CMP.W` 1, `TST.B` 5·`TST.W` 6, `BTST` 26(레지스터 `D0` 10)·`BSET` 7·`BCLR` 3·`BCHG` 1, `MOVEM.L (A7)+,D0` 2, `MOVE.L Dn/An,-(A7)` 4, `MOVE.W D0,-(A7)` 1, `MOVE.L (A7)+` 2, `MOVE.W (A7)+,D0` 1, `CLR.W Dn` 6·`CLR.B`/`CLR.W`/`CLR.L` 메모리 4, `MOVEQ` 6, `ORI.B #1,CCR` 2(`d3822` `d3a5a`), `JSR`/`BSR` 64. **TRAP·DIVU/DIVS·MULU/MULS·ABCD·ADDX/SUBX·EXT·SWAP·`JSR (An)` 없음**, I/O port·bank 쓰기 없음.
- [F] **나가는 곳**(각 실행부의 `case` block 시작으로 routing됨; 44개 모두 `case 0x…:` 확인): callee `28ae` `2986` `3af8` `8ebe` `1ab02` `3a4da` `3a5be` `3b288` `3b302` `3b334` `3b424` `4356e` `43e34` `443d2` `4706c` `49214` `49290` `4970a` `497a6` `49a58` `49a84` `49f8c` `49fc6` `4a496` `4ae4a` `4b54e` `4be06` `4be2c` `4be34` `4c0ac` `c6a96`, 분기 출구 `38ff4` `39076` `39156` `395dc` `395f8` `3976a` `398be` `39b72` `39db4`(N32/N32b) `3a350`(N31) `cdc1c`(FR4) `cdd2e`(FR7), `JMP 2a00`(`42eaa` `42ec0` `430e0` `aea26` `d3546` `d3578`). routing 밖으로 나가는 곳은 없다. 다른 실행부 block의 **중간**으로 들어가는 분기·점프는 없다(FR6 `4fce0` 교훈: 출구 44개가 모두 block 시작).
- [F] **참조**(ROM `<100000` 짝수 오프셋 전수 디코드 + LONG 상수, scratch `inrefs8.out` 95줄, LONG 검색): 범위 밖에서 들어오는 실제 진입:
  - `42d9c`: routing된 B2e `3ac60 MOVEA.L #42d9c,A0`(`2986` 자식). `42e68`: 범위 안 `42e5e`/`430b0`의 설치(`430b0`는 범위 밖 형제 `4309a` 코드 안: 설치 값 `4309a`는 실행되지 않아 쓰기만 한다).
  - `d3802`: 밖 44곳의 `JSR d3802.l`(`52ea6` … `ee71e`, 그중 routing된 것 N12 `52ea6` `52eee` `52f04`, N13 `5a832..5ab26`, N07 `bbd8a`, U16 `bbef6`). `d3500`: 범위 안 `d3804`(`28ae` 자식). `d3a2e`: 밖 stub `d38ea..d3a2a`의 `BRA.W` 30곳(같은 꼴 `LEA dxxxx(PC),A1`), `d39f6`: 밖 `aec62` `aecb2`의 `JSR`(그리고 범위 안 `ae9a2` `ae9f2`).
  - `cdc24`: routing된 FR4 `cdc1c`와 밖 `cd944`의 `MOVE.L #cdc24,(A6)`. `38e92`: routing된 N32 `3906c` `3914c` `39722`, N32b `39d7c`의 `MOVE.L #38e92,(A6)`. `aea38`: 밖 LONG 표 `e8eac`의 값(자료). `ae930`: 범위 안 `aeb28`/`aec00`(밖, `aec04` 형제 코드)의 `BRA.W`. `cc7b4`: FR4 `cc7a8`의 계산 점프(D0.B = 2).
  - 그 밖의 범위 안 대상은 자료·operand 디코드 잔재다: `42a4c..42c20`의 `BRA.W`/`BVC.W`(`42d9c` 앞 LONG 자료), `43104 BGT.B 430d8`(`43100 JSR 16ed2.l`의 operand), `ae646..ae686`(`ae6a8` 앞 자료).
- [I] 의미(이름은 확정하지 않는다): 각 묶음 절의 [I] 줄.

## 공통 규칙·native 검증 계획

FR2..FR7 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr8.cpp`, 함수 `animation_objects_fr8_block`. 오류 문자열은 `unsupported animation objects fr8 PC`(범위 안 내부 PC 직접 진입), `objects fr8 caller requires known carry`(C 소비 block에 Unknown C; 소비자 6개). 그 밖의 오류는 공용 bus/스택 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(12 범위, FR7 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 6개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 설치 값 `38eb4`(`38eae`) `38ece`(`38ec8`) `38ee2`(`38edc`) `38f08`(`38f02`) `aeab0`(`aeaaa`) `aeb32`(`aeb2c`) `d3554`(`d354e`)는 바로 다음 PC라 그 block으로 들어가고, `42e68`(`42e54`)은 바로 뒤 `BRA.W 42e68`로 들어간다(FR4 결정 4). **쓰기만 하는 설치**: `4313a`(`42f8a`, 뒤는 `RTS`), `4309a`(`43090`, 뒤는 `BRA.W 42e8e`), `aec04`(`aea12`, 뒤는 `aea18`), `aeb4c`(`aeb44`, 뒤는 `RTS`) — 모두 range 밖·routing 밖이고 native가 실행하지 않았다. `cdd24`의 `cdd2e`는 FR7 시작이고 `BRA.W cdd2e`로 들어간다. `28ae`/`2986` 자식 값 `d3500`(`d3802`, 범위 안이지만 이 단위가 들어가지 않고 A0로 넘기기만 함), `d309a`(`d3a38`), `d1d38`(`ae960` `ae9bc`), `430e6`(`43060` `430ba`)은 A0로 넘기기만 한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. FR9가 routing할 코드(`af8cc..b057e`)와 FR4b 표 항목(`cc7ac..cc818`의 `cc7b4` 밖)은 rollback 탐침으로 쓰지 않는다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): FR2와 같다. 행의 run stop은 실패 block 바로 뒤 PC다.
- **자료 읽기**(live bus, 상한 검사 없음): bank 창 LONG `200038`(`42da4`, LONG `22(A6)`에 저장만), `200094`(`42f62`, 저장만), `200138`(`aeaca`: 저장한 뒤 다시 읽어 그 주소 + sext(D1.W)의 LONG을 A1로; D1.W = 4·(2·WORD `7e` + 1)의 WORD); ROM LONG 표 `4376c`(`42e6e`, 색인 4·(BYTE `8c` ∧ `f`) ≤ `3c`), `38f0c`(`38eec`, 색인 4·BYTE `99` ≤ `3fc`, 무부호), `cdf3e`(`cdce4`, 색인 sext(4·WORD `8c`의 WORD))와 그 기록의 WORD `6`·`0`·`2`; RAM: node field(A6), LONG `96(A6)`의 기록(`d3500`: BYTE `0` `1`, WORD `2`; `d383c`/`d384a`/`d386c`/`d3880`: WORD `4` `6` `8` `a`, BYTE `d`, LONG `e`), LONG `e` 기록의 LONG 표(`d3898`, 색인 D0 ∧ `3c`), LONG `c(A6)`(`d38d0`: BYTE `12` `13`), 표적 A2(`42fd4`: BYTE `61`), 자식 A0(`ae986` `ae9d6` `aea68` `aea72` `d3830` `d3836` `d38ac` `d38bc` `d38d0` `d3a5e`: 쓰기), A5 field WORD `5418`(`aeb38`), 스택. callee에게 주소만 넘기는 값: `43942` `43bb0` `43b4a`(`49f8c`의 A1), `3b8b2` `3b8b8` `3b8be` 와 표 `38f0c`의 값(`3b302`의 A0), `3b756`(`4ae4a`의 A0), `4376c` 표의 값(`4ae4a`의 A0), `cdf86` `ce7c4` `cf870` `cf126` `d00e0` `d07f8`(`49f8c`의 A1), `ae6a8`(`1ab02`의 A0), `ae6b0` `ae728`(`4706c`의 A0), `d4046`(`d39f6`의 A1 → LONG `82(A0)`), `100bf4`(`2986`의 A1). 단위 시험은 합성 typed physical byte를 자료 영역에만 둔다(ROM 자료가 아니다; 이 단위 코드 바이트와 겹치지 않음): bank 창 LONG `200038` `200094` `200138`과 `200138`의 대상 표(음수 색인 포함), 표 `4376c..437ac`, 표 `38f0c` 주변(`38f0c..38f14`; 큰 색인은 코드 바이트를 읽으므로 단위 시험에서 버린다), 표 `cdf3a..cdf86`(음수 색인 −4 포함)와 그 기록. V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** JSR/BSR 복귀 LONG. `38f82`: `MOVE.L D0,-(A7)` → `38f8e`: `MOVEM.L (A7)+,D0`(flag를 바꾸지 않음; 그 앞의 `TST.W D0`가 `BNE`를 정함). `38fa2`: `MOVE.L D0,-(A7)` → `38fb4`: `MOVEM.L (A7)+,D0; BCS.W`(C는 `3a4da`의 것). `d3802`: `MOVE.L A1,-(A7)` → `d3836`: `MOVE.L (A7)+,96(A0)`. `d3a38`: `MOVE.W D0,-(A7); MOVE.L D1,-(A7)` → `d3a5e`: `MOVE.L (A7)+,D1; MOVE.W (A7)+,D0`(D0 상위 WORD 유지). 홀수 A7은 checked 오류다. 직접 진입 world는 이 값들을 복귀 LONG 아래에 선언한다(V1 spec `STACK`: `38f8e` `38fb4` LONG 1; `d3814` `d3818` `d3822` `d3826` `d3830` `d3836` LONG 1; `d3a4c` `d3a50` `d3a5a` `d3a5e` LONG 1 + WORD 1).
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B` `ADDI.B` `ADDQ.B` `SUBQ.B` `ADD.W` `ADDI.W` `SUBI.W` `SUBQ.W` `ADDQ.W` `ANDI.W/.B` `LSR.W` `LSL.W` `NEG.W` `CLR.W Dn` `MOVE.W (A7)+,D0`). `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`MOVEM.L`은 LONG 전체. 색인 `(An,Dn.W)` = An + sext(Dn.W). `LSR.W #n`은 WORD 무부호, `LSL.W #8`은 WORD 안에서 밀어냄. 비교(같은 block 안에서 만들고 소비): `CMPI.W #140,D0` + `BCS`(무부호 <), `SUBI.W #100,D0; CMPI.W #100,D0` + `BCS`, `CMPI.W #9,D0` + `BCC`(무부호 ≥), `CMPI.B #40,76(A6)` + `BMI`(차의 bit 7; 부호 비교가 아님), `SUBQ.B #1,8f(A6)` + `BLT`(N ≠ V: `80` → `7f`는 넘침이라 참), `CMPI.B #k,D0`/`#0,(A0)`/`#0,d(A1)`/`#ff,a0(A6)`/`#40,6f(A6)` + `BEQ`/`BNE`, `CMPI.W #k,D0`/`#4,7e(A6)`/`#0,9e(A6)` + `BEQ`/`BNE`, `CMP.W 7a(A6),D0` + `BLT`(부호 WORD, 넘침 포함), `SUBQ.W #1,D0; CMPI.W #0,D0` + `BGT`(부호 WORD > 0), `SUBQ.B #1,a0(A6)`/`SUBQ.W #1,9e(A6)` + `BNE`, `MOVE.W 8c(A6),D0` + `BNE`, `MOVE.W (A0,D0.W),D0` + `BEQ`/`BPL`(묶음), `TST.B`/`TST.W` + `BEQ`/`BNE`, `BTST` + `BEQ`/`BNE`, `TST.W D0; MOVEM.L (A7)+,D0` + `BNE`. flag는 같은 block 안에서 만들고 소비한다(예외: "carry").

## carry

- [F] **소비 block 6개**(Clear 쪽 / Set 쪽): `38fb4 BCS.W 39076`(`3a4da` B2b; `38fbc` / `39076`), `ae936 BCC.W ae93e`(`4b54e` U01; `ae93e` / `ae93a`), `aea22 BCC.W aea36`(`1ab02` U05; `aea36` / `aea26`), `cdd0c BCS.W cdd16`(`497a6` U20; `cdd10` / `cdd16`), `d3814 BCC.W d3826`(`28ae`; `d3826` / `d3818`), `d3a4c BCC.W d3a5e`(`28ae`; `d3a5e` / `d3a50`). 생산자는 모두 routing된 실행부이고 known C를 돌려준다(B2b `3a5b2`/`3a5b8` 등, U01 `4b546`/`4b54c`, U05, U20, `28ae`).
- [F] **known C 생산 block(자기 block 안에서 C를 정함)**: `d3822`(`ORI.B #1,CCR` → Set, fall-through `d3826`), `d3a5a`(`ORI.B #1,CCR` → Set, fall-through `d3a5e`). 읽는 곳이 없다: `d3826`(`BTST` + `BEQ`) 뒤 `d3836 MOVE.L ...; RTS`, `d3a5e`(`MOVE`·`SUBQ`·`CMPI`)가 C를 덮는다. 정지가 `d3826`/`d3a5e`일 때만 Set tag가 보인다(FR7 `4c1d6`와 같은 분류).
- [F] **C를 넘기는 `RTS`: 없다.** 이 단위의 subroutine(`d3802` 44곳, `d383c` 2곳, `d39f6` 4곳, `d3a2e`)의 모든 직접 호출자는 복귀 뒤 C를 읽지 않는다(scratch `cread.py`: 0곳). 다른 진입(`42d9c` `cdc24` `38e92` `aea38` `d3500` 등)은 node callback이다.
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 6개다: `38fb4` `ae936` `aea22` `cdd0c` `d3814` `d3a4c`. Unknown C로 소비자에 들어오면 checked 오류다. block 경계를 건너 다시 계산하는 flag와 X는 없다(`cscan.py`: 위 6개 외에 경계를 건너 C를 읽는 block 0; N/Z/V는 모두 같은 block 안).
- [F] **`2986`의 실패 경로**(`43060` `430ba`): `2986`(buffer_cue)의 실패 경로는 호출자의 X가 필요하다(`cue wrapper failure requires known caller X`, 2986 caller-X 제한; 기존의 의도된 checked 오류). 이 단위는 X를 만들지 않으므로 실패 경로는 그 오류로 끝난다. 실제 ROM 차분은 이 경우를 그 오류로 분류해 센다.

## 객체 `42d9c`/`42e68`(계산 점프 `42f9a`)

- **`42d9c`**: D0.W := `1a65`, `BSR 4356e`(FR7 소리 throttle; 복귀 `42da4`). **`42da4`**: LONG `7c` := `6f364`, LONG `78` := `100000`, WORD `20` := `2a`, LONG `22` := bank 창 LONG `200038`, A1 := `43942`, D0.W := `100`, `JSR 49f8c`(복귀 `42dd2`). **`42dd2`**: D0.W := `202`, D1.B := 0, `JSR 8ebe`(복귀 `42de0`). **`42de0`**: BYTE `8f` := 3, BYTE `15` bit 3 := 1, WORD `68` := `e000`, WORD `1e` := `e000`, BYTE `15` bit 0 := 0, D0 := LONG `78`, D1.B := BYTE `76`, `JSR 443d2`(복귀 `42e0c`).
- **`42e0c`**: LONG `36` := D0, LONG `3a` := D1, D0.B := BYTE `76`, D0 bit 5 = 0 → `42e24`, 아니면 `42e20`: D0.B += `f`. **`42e24`**: D0.W := LSR.W(D0.W, 4) ∧ `f`, BYTE `8c` := D0.B, D0.B := BYTE `76`, bit 5 = 0 → `42e3c`, 아니면 `42e3a`: D0.B += 7. **`42e3c`**: D0.W := LSR.W(D0.W, 3), D0.B ∧= `1f`(BYTE: bit 8..15 유지), BYTE `8d` := D0.B, D0.B := BYTE `76`, bit 5 = 0 → `42e54`, 아니면 `42e52`: D0.B += 3. **`42e54`**: D0.W := LSR.W(D0.W, 2) ∧ `3f`, BYTE `8e` := D0.B, LONG `(A6)` := `42e68`, `BRA 42e68`.
- **`42e68`**(설치 값): `JSR 4be34`(복귀 `42e6e`). **`42e6e`**: D0.B := BYTE `8c`, D0.W ∧= `f`, D0.W := 4·D0.W, A0 := LONG `(4376c + sext(D0.W))`, `JSR 4ae4a`(N08 격자 판정; 복귀 `42e88`). **`42e88`**: D0.B ≠ 0 → `42f92`, 아니면 `42e8e`.
- **`42e8e`**: BYTE `15` bit 5 = 1 → `42ec8`, 아니면 `42e98`: `JSR 49fc6`(C는 읽지 않음; 복귀 `42e9e`). **`42e9e`**: D0.W := WORD `42`, (무부호) < `140` → `42eb0`, 아니면 `42eaa JMP 2a00`. **`42eb0`**: D0.W := WORD `46` − `100`, (무부호) < `100` → `42ec6 RTS`, 아니면 `42ec0 JMP 2a00`.
- **`42ec8`**: BYTE `76` − `40`의 bit 7 = 1 → `42ed8`, 아니면 `42ed2`: BYTE `15` bit 0 := 1. **`42ed8`**: WORD `68` := `e0ed`, WORD `1e` := `e0ed`, BYTE `61` bit 0 = 0 → `42f08`, 아니면 `42eee`: `JSR 49a58`(난수; 복귀 `42ef4`). **`42ef4`**: D0.W := (D0.W ∧ `f`) − 7, WORD `32` += D0.W, A0 := `43bb0`, `BRA 42f62`. **`42f08`**: BYTE `61` bit 1 = 0 → `42f32`, 아니면 `42f12`: `JSR 49a58`(복귀 `42f18`). **`42f18`**: D0.W := (D0.W ∧ `f`) − 7, WORD `2e` += D0.W, BYTE `15` bit 1 := 1, A0 := `43b4a`, `BRA 42f62`. **`42f32`**: `JSR 49a58`(복귀 `42f38`). **`42f38`**: `42f18`의 앞 세 줄(WORD `2e`), BYTE `6f` = `40` → `42f5c`, 아니면 `42f4c`: `JSR 49a58`(복귀 `42f52`). **`42f52`**: `42ef4`의 앞 세 줄(WORD `32`; fall-through `42f5c`). **`42f5c`**: A0 := `43b4a`(fall-through `42f62`).
- **`42f62`**: WORD `20` := `e2`, LONG `22` := bank 창 LONG `200094`, A1 := A0, D0.W := `100`, `JSR 49f8c`(복귀 `42f7c`). **`42f7c`**: D0.W := `202`, D1.B := 0, `JSR 8ebe`(복귀 `42f8a`). **`42f8a`**: LONG `(A6)` := `4313a`(쓰기만), `RTS`.
- **`42f92`**: (무부호) D0.W ≥ 9 → `42fec`, 아니면 `42f9a`. **`42f9a`**(계산 점프, 결정 2): D0.W := 4·D0.W(WORD 안), PC := `42fa2` + sext(D0.W). 표(원본 바이트, 9칸 모두 `BRA.W`): `42fa2`→`42fec` `42fa6`→`42ff0` `42faa`→`42fc6` `42fae`→`42fd4` `42fb2`→`42fec` `42fb6`→`42fec` `42fba`→`42fd4` `42fbe`→`42fec` `42fc2`→`42fc6`. `42f92`의 경계로 정상 경로의 색인은 0..8이다. `42f9a`에 직접 들어온 다른 D0.W는 routing이 판정한다(표 밖의 범위 안 짝수 PC: 그 PC가 시작이면 실행, 아니면 `unsupported animation objects fr8 PC`; 범위 밖이면 그 PC의 routing; FR1 결정 3).
- **`42fc6`**: D0.W := `1a5d`, `JSR 3af8`(복귀 `42fd0`), **`42fd0`**: `BRA 430ba`. **`42fd4`**: BYTE `61(A2)` bit 7 = 1 → `42fe8`, 아니면 `42fde`: D0.W := `189d`, `JSR 3af8`(복귀 `42fe8`). **`42fe8`** **`42fec`**: `BRA 430ba`.
- **`42ff0`**: D0.W := `1a5e`, `JSR 3af8`(복귀 `42ffa`). **`42ffa`**: BYTE `8f` −= 1, 새 BYTE가 부호 있는 뺄셈으로 0보다 작음(N ≠ V) → `430ba`, 아니면 `43002`: `JSR 49a58`(복귀 `43008`). **`43008`**: D0.W := (D0.W ∧ `3fff`) − `1f80`, D1.B := BYTE `76`, D1.W := (D1.W << 8) + `8000`(WORD 안), D0.W += D1.W, D0.W := LSR.W(D0.W, 8), BYTE `76` := D0.B, D0 := LONG `78`, D1.B := BYTE `76`, `JSR 443d2`(복귀 `43030`). **`43030`** `43044` `43048` `4305e`: `42e0c`..`42e3a`와 같은 꼴(LONG `36`/`3a`, BYTE `8c`; `8d`는 다시 쓰지 않음; `43048`의 bit 5 → `43060` / `4305e` D0.B += 3). **`43060`**: D0.W := LSR.W(D0.W, 2) ∧ `3f`, BYTE `8e` := D0.B, A0 := `430e6`, D0.W := `1e`, A1 := `100bf4`, `JSR 2986`(자식; 복귀 `43080`). **`43080`**: LONG `7c(A0)` := LONG `7c(A6)`, D0 := 0, D1 := 0, `JSR 49214`(복귀 `43090`). **`43090`**: LONG `(A6)` := `4309a`(쓰기만), `BRA 42e8e`.
- **`430ba`**: `43060`의 뒤 네 줄(`JSR 2986`; 복귀 `430d0`). **`430d0`**: `43080`과 같음(복귀 `430e0`). **`430e0`**: `JMP 2a00`.
- [F] **ROM 자료**(원본 바이트): 표 `4376c` = LONG `0004358c 000435aa 000435c8 … 0004374e`(16칸, 간격 `1e`; `4ae4a`의 판정 기록 [I]). bank 창 `200038` `200094`는 live bus.
- [I] 각도 BYTE `76`(32방향: `8c` = 16방향 색인, `8d`/`8e`)으로 날아가는 탄(`443d2` 속도), `4ae4a`로 표적을 맞히면 결과 번호(0..8)로 소리(`1a5d`/`189d`/`1a5e`)를 내고 파편 자식(`430e6`)을 남긴 뒤 사라지거나(`430ba` → `2a00`) 튕겨 각도를 바꾼다(`42ff0`; `8f` 횟수). 화면 밖이면 삭제.

## 객체 `d3500`(`d3802`의 `28ae` 자식), helper `d3802` `d383c`

- **`d3802`**(subroutine): A1 넣기, A0 := `d3500`, D0.W := `14`, `JSR 28ae`(복귀 `d3814`). **`d3814`**(소비자): Clear → `d3826`, Set → `d3818`: D0.W := 0, D1.W := 0, `JSR 4970a`(복귀 `d3822`). **`d3822`**: C := 1(fall-through `d3826`). **`d3826`**: BYTE `15(A6)` bit 2 = 0 → `d3836`, 아니면 `d3830`: BYTE `15(A0)` bit 2 := 1. **`d3836`**: LONG `96(A0)` := 꺼낸 LONG, `RTS`.
- **`d3500`**(자식 callback): A0 := LONG `96`, BYTE `a0` := BYTE `1(A0)`, WORD `9e` := WORD `2(A0)`, BYTE `(A0)` = 0 → `d3522`, 아니면 `d3518`: D0.W := 0, D1.W := 0, `JSR 49290`(복귀 `d3522`). **`d3522`**: `JSR 43e34`(복귀 `d3528`). **`d3528`**: BYTE `a0` ≠ `ff` → `d354e`, 아니면 `d3532`: WORD `9e` = 0 → `d3546 JMP 2a00`, 아니면 `d353c`: `JSR d383c`(복귀 `d3540`). **`d3540`**: WORD `9e` −= 1, `BRA d3532`.
- **`d354e`**: LONG `(A6)` := `d3554`(들어감). **`d3554`**(설치 값): `JSR 43e34`(복귀 `d355a`). **`d355a`**: BYTE `a0` −= 1, ≠ 0 → `d3570`, 아니면 `d3562`: A0 := LONG `96`, BYTE `a0` := BYTE `1(A0)`, `JSR d383c`(복귀 `d3570`). **`d3570`**: WORD `9e` −= 1, ≠ 0 → `d357e RTS`, 아니면 `d3578 JMP 2a00`.
- **`d383c`**(subroutine): A1 := LONG `96`, D0.W := WORD `6(A1)`, `JSR 49a84`(난수 범위; 복귀 `d384a`). **`d384a`**: A1 := LONG `96`, D0.W += WORD `4(A1)`, BYTE `15` bit 0 = 0 → `d385e`, 아니면 `d385c`: D0.W := −D0.W. **`d385e`**: WORD `36` := D0.W, D0.W := WORD `a(A1)`, `JSR 49a84`(복귀 `d386c`). **`d386c`**: `d384a`와 같은 꼴(WORD `8(A1)`, bit 1, `d387e` NEG.W). **`d3880`**: WORD `3a` := D0.W, A0 := LONG `e(A1)`, BYTE `d(A1)` = 0 → `d38a0`, 아니면 `d3892`: `JSR 49a58`(복귀 `d3898`). **`d3898`**: D0.W ∧= `3c`, A0 := LONG `(A0 + sext(D0.W))`(fall-through `d38a0`). **`d38a0`**: D0.W := `1e`, `JSR 28ae`(자식 A0; C는 읽지 않음; 복귀 `d38ac`). **`d38ac`**: WORD `1e(A0)` := WORD `1e(A6)`, BYTE `15(A6)` bit 2 = 0 → `d38c2`, 아니면 `d38bc`: BYTE `15(A0)` bit 2 := 1. **`d38c2`**: D0.W := WORD `36`, D1.W := WORD `3a`, `JSR 49214`(복귀 `d38d0`). **`d38d0`**: A1 := LONG `c(A6)`, BYTE `12(A0)` := BYTE `12(A1)`, BYTE `13(A0)` := BYTE `13(A1)`, `RTS`.
- [I] `d3802`는 기록(A1 → LONG `96`)을 가진 생성기 자식 `d3500`을 만들고, `d3500`은 기록의 개수 WORD `2`만큼(간격 BYTE `1` frame마다) 기록의 자식(`e(A1)` 하나 또는 그 표에서 난수로 고름)을 위치 `4/6`·`8/a`(± 난수)에 만든다(파편·연기 방출기). BYTE `a0` = `ff`면 한 frame에 모두 만든다.

## 객체 `cdc24`

- **`cdc24`**: D0.W := WORD `8c`, ≠ 0 → `cdc46`, 아니면 `cdc2c`: WORD `20` := WORD `8a`, A1 := `cdf86`, D0.W := `100`, `JSR 49f8c`(복귀 `cdc42`), **`cdc42`**: `BRA cdce4`. **`cdc46`** `cdc68` `cdc8a` `cdcac`: D0.W ≠ 1 / 2 / 3 / 4 → 다음, 같으면 `cdc4e` `cdc70` `cdc92` `cdcb4`(A1 := `ce7c4` `cf870` `cf126` `d00e0`; 복귀 `cdc64` `cdc86` `cdca8` `cdcca`: `BRA cdce4`). **`cdcce`**: A1 := `d07f8`(복귀 `cdce4`).
- **`cdce4`**: A0 := LONG `(cdf3e + sext(4·WORD 8c))`, D0.W := WORD `6(A0)`(`MOVE.W #3,D0; ADD.W D0,D0`: D0 상위 유지), = 0 → `cdd24`, 부호 bit = 0 → `cdd1a`, 아니면 `cdd06`(BEQ/BPL 묶음, `cdd02`는 시작이 아님): `JSR 497a6`(복귀 `cdd0c`). **`cdd0c`**(소비자): Clear → `cdd10`: D0.W := WORD `(A0)`, `BRA cdd1a`; Set → `cdd16`: D0.W := WORD `2(A0)`. **`cdd1a`**: D1.B := 0, `JSR 8ebe`(복귀 `cdd24`). **`cdd24`**: LONG `(A6)` := `cdd2e`, `BRA cdd2e`(FR7).
- [F] **ROM 자료**: 표 `cdf3e` = LONG `000cdf56 000cdf5e 000cdf66 000cdf6e 000cdf76 000cdf7e`(색인 0..5), 기록 WORD `+6`: `ffff` `ffff` `0c59` `ffff` `0000` `0c89`.
- [I] `cdd2e` 비행 객체(FR7)의 시작: 종류 WORD `8c`(0..5)로 anim과 소리를 고른다(음수면 `497a6` BYTE `10fd92`로 두 소리 중 하나).

## 객체 `38e92`(N32/N32b의 설치 값)

- **`38e92`**: BYTE `95` := 0, LONG `64` := 0, BYTE `99` ≠ 0 → `38ed2`, 아니면 `38ea4`: A0 := `3b8b2`, `JSR 3b302`(N33; 복귀 `38eae`). **`38eae`**: LONG `(A6)` := `38eb4`(들어감). **`38eb4`**(설치 값): BYTE `99` ≠ 0 → `38e92`, 아니면 `38eba`: `BRA 38f14`.
- **`38ebe`**: A0 := `3b8b8`, `JSR 3b302`(복귀 `38ec8`). **`38ec8`**: LONG `(A6)` := `38ece`(들어감). **`38ece`**: `BRA 38f14`.
- **`38ed2`**: A0 := `3b8be`, `JSR 3b302`(복귀 `38edc`). **`38edc`**: LONG `(A6)` := `38ee2`(들어감). **`38ee2`**: BYTE `99` = 0 → `38e92`, 아니면 `38ee8`: `BRA 38f14`.
- **`38eec`**: A0 := LONG `(38f0c + 4·BYTE 99)`(MOVEQ #0; MOVE.B: D0 = BYTE의 4배, 무부호), `JSR 3b302`(복귀 `38f02`). **`38f02`**: LONG `(A6)` := `38f08`(들어감). **`38f08`**: `BRA 38f14`.
- **`38f14`**: BYTE `15` bit 7 = 0 → `398be`(N32), 아니면 `38f1e`: `JSR 3b424`(B2b; 복귀 `38f22`). **`38f22`**: D0 bit 7 = 1 → `39db4`, **`38f2a`**: D0 bit 1 = 0 → `38f3c`, 아니면 **`38f32`**: BYTE `15` bit 7 = 1 → `39156`. **`38f3c`**: D0 bit 1 = 1 → `38f56`, **`38f44`**: BYTE `9f` = 0 → `38f56`, **`38f4c`**: BYTE `15` bit 7 = 1 → `38ff4`. **`38f56`** `38f5e` `38f66`: D0 bit 5 / 2 / 3 = 1 → `3976a` / `395dc` / `395f8`. **`38f6e`**: BYTE `94` bit 2 = 1 → `38f98`, **`38f78`**: BYTE `9d` bit 4 = 0 → `38f98`, **`38f82`**: D0 넣기, A0 := `3b756`, `JSR 4ae4a`(복귀 `38f8e`). **`38f8e`**: Z := (D0.W = 0), D0 := 꺼낸 LONG, Z = 0 → `39b72`, 아니면 `38f98`.
- **`38f98`**: BYTE `9d` bit 6 = 0 → `38fbc`, 아니면 `38fa2`: D0 넣기, BYTE `9d` ∧= `bf`, BYTE `9e` ∧= `bf`, `JSR 3a4da`(B2b; 복귀 `38fb4`). **`38fb4`**(소비자): D0 := 꺼낸 LONG, Clear → `38fbc`, Set → `39076`. **`38fbc`**: A0 := LONG `82`, `JSR 3a5be`(복귀 `38fc4`). **`38fc4`** `38fd0` `38fd8` `38fe0`: D0.B := BYTE `97`(첫 block만), D0.B = 0 / 2 / 3 / 4 → `38eec` / `38ebe` / `38e92` / `38e92`, 아니면 다음. **`38fe8`**: `JSR 3b288`(복귀 `38fec`). **`38fec`**: `JSR 3b334`(복귀 `38ff0`). **`38ff0`**: `BRA 3a350`(N31).
- [F] **ROM 자료**: 표 `38f0c` = LONG `0003b8c4 0003b8ca`(색인 0..1), 그 뒤 `38f14..`는 코드다(BYTE `99` ≥ 2는 코드 바이트를 LONG으로 읽는다: 원본 그대로 live bus).
- [I] N32/N32b 탈것·동료 객체(`3a4da` 접근, `3b424` 입력)의 상태 선택부: BYTE `99`/`97`로 동작 anim(`3b302`)을 고르고 매 frame `38f14`의 판정 사슬을 돈다.

## 객체 `aea38`(LONG 표 `e8eac`), 상태 기계 `ae930`, helper `d39f6`/`d3a2e`

- **`aea38`**: D0.W := `4d`, D1.W := 1, D2.B := 0, `JSR c6a96`(복귀 `aea4a`). **`aea4a`**: D0.W := `c85`, `JSR 4a496`(복귀 `aea54`). **`aea54`**: WORD `68` := 0, WORD `1e` := 0, WORD `7a` ≠ 0 → `aea72`, 아니면 `aea68`: WORD `82(A0)` := 2, `BRA aea78`. **`aea72`**: WORD `82(A0)` := `d`. **`aea78`**: WORD `54` := `57`, WORD `7c` := 0, WORD `76` ≠ 0 → `aea92`, 아니면 `aea8c`: BYTE `15` bit 0 반전. **`aea92`**: WORD `7a` = 0 → `aea9e`, 아니면 `aea9a`: `BRA aeb2c`. **`aea9e`**: WORD `7e` := 0, `JSR 4c0ac`(복귀 `aeaaa`). **`aeaaa`**: LONG `(A6)` := `aeab0`(들어감).
- **`aeab0`**(설치 값): BYTE `15` bit 7 = 1 → `aeac4`: `JSR 4be06`, 아니면 `aeaba`: `JSR 4be2c`(복귀 `aeac0`: `BRA aeaca`). **`aeaca`**: D0.W := 2·WORD `7e` + 1, A0 := A6 + `26`, WORD `20` := `d3`, LONG `22` := bank 창 LONG `200138`, D1.W := 4·D0.W, A1 := LONG `(LONG 200138 + sext(D1.W))`, D0.W := `100`, `JSR 49f8c`(복귀 `aeb02`). **`aeb02`**: `JSR 49fc6`(복귀 `aeb08`; C는 읽지 않음). **`aeb08`**: BYTE `15` bit 0 = 1 → `aeb1c`: A0 := `ae728`, 아니면 `aeb12`: A0 := `ae6b0`, `BRA aeb22`. **`aeb22`**: `JSR 4706c`(복귀 `aeb28`). **`aeb28`**: `BRA ae930`.
- **`ae930`**: `JSR 4b54e`(U01 피격 판정; 복귀 `ae936`). **`ae936`**(소비자): Clear → `ae93e`, Set → `ae93a`: BYTE `5e` := 0. **`ae93e`**: BYTE `61` bit 7 = 0 → `aea18`, 아니면 `ae948`: WORD `7e` += 1, = 4 → `aea08`, 아니면 `ae956`: D0.W := `182f`, `JSR 3af8`(복귀 `ae960`). **`ae960`**: BYTE `61` bit 7 := 0, WORD `54` := `57`, A0 := `d1d38`, D0.W := `1e`, `JSR 28ae`(복귀 `ae97c`; C는 읽지 않음). **`ae97c`**: D0 := 0, D1 := 0, `JSR 49214`(복귀 `ae986`). **`ae986`**: WORD `68(A0)` := `e0ed`, WORD `1e(A0)` := `e0ed`, WORD `32` += `40`, `JSR 43e34`(복귀 `ae99e`). **`ae99e`**: D0.W := 2, `JSR d39f6`(복귀 `ae9a8`). **`ae9a8`**: WORD `32` −= `40`, `JSR 43e34`(복귀 `ae9b4`). **`ae9b4`**: WORD `7a` = 0 → `aea04`, 아니면 `ae9bc` `ae9cc` `ae9d6` `ae9ee` `ae9f8`: `ae960`..`ae9a8`과 같은 꼴(D1 := `60`, WORD `32` ± `80`). **`aea04`**: `BRA aea18`.
- **`aea08`**: D0.W := `1830`, `JSR 3af8`(복귀 `aea12`). **`aea12`**: LONG `(A6)` := `aec04`(쓰기만; fall-through `aea18`). **`aea18`**: A0 := `ae6a8`, `JSR 1ab02`(U05 화면 판정; 복귀 `aea22`). **`aea22`**(소비자): Clear → `aea36 RTS`, Set → `aea26`: BYTE `61` bit 7 := 1, WORD `54` := 0, `JMP 2a00`.
- **`aeb2c`**: LONG `(A6)` := `aeb32`(들어감). **`aeb32`**(설치 값): `JSR 43e34`(복귀 `aeb38`). **`aeb38`**: D0.W := WORD `5418(A5)`, (부호) D0.W < WORD `7a` → `aeb4a RTS`, 아니면 `aeb44`: LONG `(A6)` := `aeb4c`(쓰기만; fall-through `aeb4a`).
- **`d39f6`**: A1 := `d4046`, `BRA d3a2e`. **`d3a2e`**: D1 := A1, D0.W = 0 → `d3a36 RTS`, 아니면 `d3a38`: WORD D0 넣기, LONG D1 넣기, A0 := `d309a`, D0.W := `1e`, `JSR 28ae`(복귀 `d3a4c`). **`d3a4c`**(소비자): Clear → `d3a5e`, Set → `d3a50`: D0.W := 0, D1.W := 0, `JSR 4970a`(복귀 `d3a5a`). **`d3a5a`**: C := 1(fall-through `d3a5e`). **`d3a5e`**: D1 := 꺼낸 LONG, D0.W := 꺼낸 WORD, LONG `82(A0)` := D1, D0.W −= 1, (부호) D0.W > 0 → `d3a38`, 아니면 `d3a6e RTS`.
- [F] **ROM 자료**: `ae6a8` = WORD `ffd0 ffe0 0060 0090`(`1ab02`의 사각형 [I]). bank 창 `200138`과 그 표는 live bus.
- [I] 맞으면 4번까지 버티는(`7e`) 장애물·탱크류 [I]: 맞을 때마다 소리·자식 `d1d38`·파편 `d309a` 두 개(`d3a2e`, A1 = `d4046`)를 위치 `32` ± `40`/`80`에 만든다. `7a` ≠ 0이면 `5418(A5)`(진행 거리 [I])가 `7a`에 닿을 때까지 기다린다.

## FR4 표 항목 `cc7b4`

- **`cc7b4`**: `BRA.W cdc1c`(FR4; LONG `(A6)` := `cdc24`, `RTS`). FR4 `cc7a8`(BYTE `5e` = 2)가 native로 한 번 실행했다(frame 433).

## 경계·routing 밖 출구

- [F] 이 단위 안에는 live 대상 호출(`JSR (An)`)·TRAP이 없다. 계산 점프는 `42f9a` 하나이고 표는 9칸 전부 이 단위의 block 시작이다.
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 9개: `42ec6` `42f8a` `aea36` `aeb4a` `d357e` `d3836` `d38d0` `d3a36` `d3a6e`(그중 `42f8a` `d3836` `d38d0`는 다른 명령 뒤의 RTS).
- [F] **native 정지 규칙 주의**(V1): FR7 spec의 `first_unrouted`(`8c16 < pc <= 8ca6`, `16ed2 < pc <= 16eee` 내부, 정지 `2a00` `2a24`, 홀수 live 정지 PC 버림)를 그대로 쓴다. `JMP 2a00`는 routing된 출구다. 실제 ROM 차분의 선언 정지는 FR4 표 항목 `cc7ac + 4k`/`cc82e + 4k` 중 `cc7b4`를 뺀 53개다(`cc7b4`는 이제 routing됨).

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR7 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0..A4 := 자연 node 또는 선언 기록, LONG `96(A6)` := 선언 생성 기록 GREC, LONG `c(A6)` := 자연 node, A5 field, 스택 WORD/LONG, PC).
- **선언 기록(work RAM, 스택 page 밖)**: GREC `10fb00`(d3500/d383c의 기록: BYTE `0` `1`, WORD `2` `4` `6` `8` `a`, BYTE `d`, LONG `e` := 자식 값(`d1d38`·`d309a` 등 원본 자식 callback) 또는 GTAB), GTAB `10fb40`(LONG 16칸, `d3898`의 표), CREC `10fc00`(`cdce4`의 기록을 RAM에 둘 때는 쓰지 않음: `cdf3e`는 ROM이라 V1은 원본을 읽는다).
- **IO pack 자연 node 상태(family `natural`)**: FR7과 같다. `boot-demo-0`(`states/boot-demo-0/boot.pack.gz`)의 frame 시작 상태에서 callback LONG이 이 단위의 진입(node callback·설치 값: `42d9c` `42e68` `cdc24` `38e92` `38eb4` `38ece` `38ee2` `38f08` `d3500` `d3554` `aea38` `aeab0` `aeb32`)인 node를 찾아(work RAM `100800..104c00` 짝수 주소 전수 검색) 그 RAM·PVC·bank를 쓰고 레지스터만 선언한다(D0..D4·A0..A4 = frame 시작 값, A5 := `108000`, A6 := 그 node, A7 := `10ef00`(복귀 LONG = sentinel), PC := callback). 찾은 자연 node(scratch 검색): `cdc24`(frame 434, `1011a8`), `d3554`(478..481, `101a14`), `42d9c`(538 `101a14`, 540 `102034`, 544, 546, …, 576), `42e68`(539..577, 158개), `38e92`(541, `1017c8`). 쓰는 frame: 434 478 481 538 539 541 546 552 563 577. [I] 이 상태는 그 frame 첫 시점의 자연 node field·전역(A5)·RAM이고 dispatcher 진입 레지스터와 같은 frame 안의 앞선 node 변경은 반영하지 않는다(선언 레지스터). 같은 상태를 native와 C++가 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `3a4da` → `38fb4`(`38fa2`), `4b54e` → `ae936`(`ae930`), `1ab02` → `aea22`(`aea18`), `497a6` → `cdd0c`(`cdd06`), `28ae` → `d3814`(`d3802`)·`d3a4c`(`d3a38`). 두 C 값이 다 나오도록 hint를 둔다: `3a4da`(BYTE `b2(A6)` ≠ 0 → Clear; `b2` = 0이면 `4d6b4` 경로, BYTE `10f001` bit 2로 Set), `4b54e`(LONG `56(A6)` = 0 → `4b6be`, 판정 기록·BYTE `5744(A5)`·BYTE `5b84(A5)`), `1ab02`(LONG `42`/`46`/`4a`/`4e`, BYTE `15`: 화면 안 Clear / 밖 Set), `497a6`(BYTE `10fd92` = 0 → Set), `28ae`(WORD `104ca0` 개수: 0이면 실패 Clear, 남으면 성공 Set). 단위 시험은 RAM·합성 자료만 읽고 PVC port를 쓰지 않는 생산자만 실제 사슬로 넣고(생성기가 두 C 값을 모두 만든 것), 나머지는 선언 C 행만 둔다(V1·실제 ROM 차분이 실제 사슬).
- node fixture: callback·설치 값(`42d9c` `42e68` `cdc24` `38e92` `38eb4` `38ece` `38ee2` `38f08` `d3500` `d3554` `aea38` `aeab0` `aeb32`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `d3802` `d383c` `d39f6` `d3a2e`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, FR7 꼴): 시작 229개 × 들어오는 C 3가지, zero-step, 내부 PC 966개 정확한 오류, 경계 stop(출구 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), 계산 점프 `42f9a`의 색인 0..8 전부(표 항목 정지)와 표 밖 색인(9 → `42fc6`, `8000` → WORD 넘침으로 `42fa2`, `ffff` → `42f9e` 내부 오류, `fffe` → `42f9a` 다시 → `42f82` 내부 오류), 그리고 빈틈 종류별 hint:
  - 부호·영 확장: `38eec`의 MOVEQ #0 + MOVE.B(BYTE `99` = `80` `ff`: 무부호 색인; 합성 표 `38f0c..` 안에서는 0..1만 자료라 큰 값은 V1·실제 ROM), `cdce4`의 sext(4·WORD `8c`)(WORD `8c` = `ffff` → −4, `4000` → 0, `3fff` → `fffc`; 합성 표 `cdf3a..` 창 안), `aeaca`의 sext(D1.W)(WORD `7e` = `1fff` → D0 = `3fff` → D1 = `fffc`, `2000` → `4001`·`0004`; 합성 bank 표 창 안: 64 KiB work RAM 거울이 0 확장 색인을 숨기므로 표 기점은 합성 ROM 창 안에 둔다), `d3898`의 sext(D0.W ∧ `3c`)(항상 양수), `d3a5e`의 `MOVE.W (A7)+,D0`(D0 상위 유지), `CLR.W D0/D1`(상위 유지).
  - 음수 색인: `cdce4`(위), `aeaca`(위), `42f9a` 직접 진입의 D0.W = `ffff`/`fffe`/`8000`.
  - 꺼낸 레지스터: `38f8e`/`38fb4` LONG D0(넣은 값과 다른 값), `d3836` LONG(→ `96(A0)`), `d3a5e` LONG D1·WORD D0(`8000` `8001` `1` `0`).
  - RAM 거울: node A6 = `1fe000`(거울 `10e000`), LONG `96(A6)`의 기록 = 거울 주소, A5 = `1f8000`(`aeb38`).
  - bit 조합과 뒤따르는 mask: `15(A6)` bit 0·1·2·3·5·7(`42de0` BSET/BCLR 둘 다 같은 BYTE: 순서 확인, `42ec8`..`42f18`, `d3826` `d384a` `d386c` `d38ac` `aeab0` `aeb08` `aea8c` BCHG), `61(A6)` bit 0·1·7, `61(A2)` bit 7, `9d` bit 4·6(ANDI.B `bf` 뒤 다른 bit 유지), `9e`(ANDI.B), `94` bit 2, D0 bit 1·2·3·5·7(`38f22..38f66`), BYTE `76` bit 5(`42e0c` `42e24` `42e3c` `43030` `43048`; ADDI/ADDQ.B 뒤 LSR.W와 ANDI.W/ANDI.B — `42e3c`의 ANDI.B는 bit 8..15를 남긴다), `43008`의 ANDI.W `3fff`·SUBI.W·LSL.W #8·ADDI.W `8000`·LSR.W #8.
  - BMI 대 BLT·넘침: `42ec8` CMPI.B #40 + BMI(BYTE `76` = `80` `bf` `c0` `3f` `40` `7f`), `42ffa` SUBQ.B + BLT(BYTE `8f` = `80` `0` `1` `81`), `aeb38` CMP.W + BLT(WORD = `7fff`/`8000`, 같은 값), `d3a5e` SUBQ.W + CMPI #0 + BGT(D0.W = `8000` `8001` `1` `2` `0`).
  - 동점(같은 값): `42e9e`(`13f`/`140`), `42eb0`(`1ff`/`200`/`100`/`ff`), `42f92`(8/9/`ffff`), `ae948`(WORD `7e` = 3/4/`ffff`), `d3528`(`fe`/`ff`), `cdc46..cdcac`(0..5, `ffff`), `38fc4..38fe0`(0..5, `102` 상위 쓰레기).
  - TST.W 대 TST.L·TST.B 읽기 범위: `38f8e TST.W D0`(D0 = `10000`), `42e88 TST.B D0`(D0 = `100`), `d3a2e TST.W D0`(D0 = `10000`), `ae9b4`/`aea54`/`aea92 TST.W 7a(A6)`·`aea78 TST.W 76(A6)`(WORD 하위 BYTE만 0 아님), `38e92`/`38eb4`/`38ee2 TST.B 99`·`38f44 TST.B 9f`를 bank 창 앞(A6 = `1fff8x` 등)에서 — 읽기 범위가 다르면 결과(성공/오류)가 달라진다.
  - 상위 레지스터 bit: `MOVE.W #imm,D0`(`42d9c` `42da4` `42dd2` `42fc6` `42fde` `42ff0` `ae956` `ae99e` `aea08` `aea38` `aea4a` `d3802` `d38a0` `d3a38` `cdc2c..`), `MOVE.B #0,D1`·`MOVE.W #1,D1`·`MOVE.B #0,D2`, `ANDI.W #f; SUBQ.W #7`(`42ef4` `42f18` `42f38` `42f52`), `MOVE.B 76(A6),D1`(`42de0` `43008`), `D0.W := 3; ADD.W`(`cdce4`).
  - 정지 PC 확인: 실패한 block 바로 뒤를 run stop으로 두고 실패 PC를 확인한다(오류 fixture).

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `tools/probe_scan_fr7.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_fr8.out` 64줄)으로 확인한 결과:
  - **옮길 것: 없다.** 이 단위의 PC를 "routing 밖" 탐침이나 rollback 기대값으로 쓰는 시험·검증기는 없다.
  - 그대로 참인 것: 정지로만 쓰는 것(N07 `bbd86` → `d3802`, N12 `52ea2` `52ee4` `52ef4` → `d3802`, N13 `5a82e` … → `d3802`, U16 `bbef2` → `d3802`: 정지 검사가 routing보다 먼저다; 그 boundary 주석 "d3802 without an executor"는 사실이 바뀌지만 검사는 정지만 본다), FR4 시험 `TARGETS`(`cc7b4` 포함: stop 허용 목록과 정지 행 — 여전히 참), FR4 `RANGES`/spec 범위 끝 `cdc24`, 주석·값(N32 `38e92`, N32b `38e92`, U20의 레지스터 값 `42f81`, FR4 생성기 주석 `cdc24`).
  - 표준 Python 검증기(`tools/verify_*.py` 전부)는 이 단위의 PC를 탐침으로 쓰지 않는다(검색 0줄). 결정적 runner의 legacy 목록도 같다.
- [I] V1 spec 중 native 사슬이 이 단위의 PC(`d3802` `38e92` `cc7b4` 등)를 첫 routing 밖 PC로 멈추던 것(N07/N12/N13/U16의 `d3802` 호출, FR4의 `cc7a8` 표 항목 2, N32의 `38e92` 설치 뒤 dispatcher 경로)은 더 진행한다(정지는 routing에서 계산되므로 spec 수정은 필요 없을 것으로 본다; 검증 단계 회귀로 확인하고 개수 변화를 적는다).
- [F] stage_event / stage_event_ops 검증기의 `CPP_PINS`(`animation_machine.cpp` `298c64da…`, `animation_machine_internal.h` `69b45dcd…`)는 이 단위의 공유 수정으로 맞지 않게 된다. FR7과 달리 이번에는 메인 지시로 작업자가 새 값으로 바꾼다(옛 값은 주석에 남김; "구현·검증 기록").

## 결정

1. **범위.** FR8 = 229 block(12 범위): 객체 `42d9c`/`42e68`(+ 표 9칸, `430ba`), `d3500`/`d3554` + `d3802` `d383c`, `cdc24`, `38e92` 계열, `aea38` + `ae930` 상태 기계 + `d39f6`/`d3a2e`, FR4 표 항목 `cc7b4`. FR9 = `af990` 계열 220 block(아래 "FR9 명세"). 약 220 기준을 9 넘는다(위 "선택").
2. **계산 점프·표.** `42f9a JMP 42fa2(PC,D0.W)`: PC := `42fa2` + sext(4·D0.W의 WORD)로 routing을 거친다. 표 9칸(`42fa2..42fc2`, 모두 `BRA.W`)은 이 단위의 block 시작이고 그 대상(`42fec` `42ff0` `42fc6` `42fd4`)도 이 단위 안이다(전사 완료). `42f92`가 정상 경로의 색인을 0..8로 묶는다. 자료 표 `4376c` `38f0c` `cdf3e`, bank 창 표는 live bus 읽기이고 표 밖 색인도 원본대로 읽는다(점프가 아니라 전사 대상이 아니다). TRAP 자리 없음.
3. **FR4 표 항목 `cc7b4`.** IO에서 실행된 FR4 표 항목은 `cc7b4` 하나라 이 항목만 routing한다(`BRA.W cdc1c`, routing된 FR4 꼬리). 나머지 53칸(`cc7ac + 4k`, `cc82e + 4k`)과 그 handler(약 400 block)는 FR4b/FR4c로 남는다(D 완료에 필요 없음). 메인이 표 전체를 한 번에 옮기기를 원하면 FR4b에서 같은 방식으로 한다.
4. **carry 보존 목록.** 소비자 6개. `d3822`/`d3a5a`(ORI)는 자기 C를 Set으로 정하고 읽는 곳이 없다. C를 넘기는 `RTS` 없음.
5. **숨은 탐침 이전.** 없음(위 "영향받는" 절). FR4 시험의 `TARGETS`는 stop 목록이라 그대로 둔다. stage_event / stage_event_ops `CPP_PINS`는 작업자가 새 값으로 바꾸고 옛 값을 주석으로 남긴다.
6. **C 뒤 root의 검증.** 선언 상태에 더해 IO pack(`boot-demo-0`)의 자연 node 상태(선언 레지스터)를 V1 family `natural`로 둔다. IO 비교의 확인은 C·E 연결 뒤(계획 메인 결정).
7. **F4 범위 문서.** U27(`cc778..cc822`)은 `cc7b4..cc7b8`을, U44(`38dd4..3a4a2`)는 `38e92..38f0c` `38f14..38ff4`를 빼야 한다. FR9를 구현하면 R09(`af3fe..b05bc`)가 FR9 6 범위를 빼야 한다.
8. **정적으로 불가능한 분기.** 없을 것으로 본다(생성기·V1이 빠진 후속을 보고하면 그때 근거와 함께 `STATIC_IMPOSSIBLE`에 적는다).
9. **다음.** FR9(아래 명세), 그 뒤 C(플레이어 `4e68e`·`1d1f4`).

## FR9 명세(`af990` 계열, 220 block; 구현은 다음 단위)

- [F] **정의**(`unit_fr8.py`, `FRG='af990=af8cc af8f2 af910 af990 afcda afd7c aff00 aff30 b051a'`): 진입 `af8cc` `af990`(나머지 실행 PC는 이 둘의 closure 안), **220 block 시작**, 6 범위, 명령 381, 짝수 PC 838(내부 618), 이어 붙인 바이트 1,676, SHA256 `9c3cc2bd6869c9c20db81bb8f0efce6735f7784f8a52ca2dd1584ccbaac7959e`, 시작 목록 `starts_fr9.txt` SHA256 `f2ba650fc7e314c55521b70677110119844e5feac9715bab04e634879b070dff`. 덮는 실행 PC 51개(실행 261회, `boot-demo-0` frame 410..529). 연속 Bcc 묶음 0, TB 잔재 0. FR9 뒤 D 남은 실행 PC **0**.

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `af8cc..af92c` | 96 | `a60f98c063c0352b9da09ed2959c1a3241eec6cb085ca52a9f2a7027b59b353a` | 10 | 48 |
| `af990..afb3c` | 428 | `4650167caf11fc20b0c10a1b810f212756e33afd99b54bfbd6f4a0843f0ca4b6` | 91 | 214 |
| `afb3e..afc16` | 216 | `9e3cf192c4f7d19771f68e82fdeb628564b0698dafc93db50f5ce4c48fd71192` | 28 | 108 |
| `afcf2..afed8` | 486 | `31c8ba040ab51d8d7df7044ecbc2b44fb1c61235a9e9c69b903518d1372e2b62` | 47 | 243 |
| `aff00..b005e` | 350 | `9b3e2ab9fbcaf2f1b19413a3dbbfa0593bea2c4c2bcbdb9c201353bcdd812a27` | 38 | 175 |
| `b051a..b057e` | 100 | `bbbf26334f12987385169dfa60392e5dd3a38da69084c94d10bfee235ad13766` | 6 | 50 |

- [F] **계산 점프 7개와 표(원본 바이트, 전부 `BRA.W`, 모두 FR9 block 시작)**:
  - `af9bc`(`af9b0`: BYTE `5e` → D0.B, `CMPI.B #1b` + `BCC.W afb3e`; `ANDI.W #ff` 뒤 4배) `JMP af9c8(PC,D0.W)`, 27칸 `af9c8..afa30`: 0 1 → `afb3e`, 2 3 → `afb58`, 4 → `afb3e`, 5 → `afb72`, 6 → `afb3e`, 7 → `afbbe`, 8 → `afb3e`, 9 → `afb72`, a → `aff52`, b → `aff86`, c d → `afb72`, e → `afb3e`, f → `afb72`, 10..1a → `afb3e`.
  - `afa40`(`afa34`, 같은 꼴, `BCC.W afba4`) `JMP afa4c(PC,D0.W)`, 27칸 `afa4c..afab4`: a → `aff52`, b → `aff86`, 나머지 → `afba4`.
  - `afac4`(`afab8`, 같은 꼴, `BCC.W aff00`) `JMP afad0(PC,D0.W)`, 27칸 `afad0..afb38`: a → `aff52`, b → `aff86`, 나머지 → `aff00`.
  - `afb44`(`JSR 49a58` 뒤 `ANDI.W #1`) `JMP afb50(PC,D0.W)`: 0 → `afbbe`, 1 → `afe98`. `afb5e` `JMP afb6a`: 0 → `afcf2`, 1 → `afe98`. `afb78`(`ANDI.W #7`) `JMP afb84`: 0 1 → `afbbe`, 2 → `afe98`, 3 4 → `afcf2`, 5 6 → `afda6`, 7 → `aff00`. `afbaa` `JMP afbb6`: 0 → `aff00`, 1 → `afe0a`.
  - 표 항목 합 95(27·3 + 2 + 2 + 8 + 2). 각 점프는 FR8 `42f9a`처럼 PC := 표 + sext(색인)으로 routing을 거친다(직접 진입의 다른 D0는 routing 판정).
- [F] **carry**: 소비자 5개 — `afd90 BCC.W afda2`·`aff3c BCC.W aff4e`·`b0048 BCC.W b005a`(`49fc6`), `afe6a BCC.W afe84`(`b0468`, N09), `b0556 MOVEM.W (A7)+,D0-D6; BCC.W b057c`(`2986`; MOVEM.W는 flag를 바꾸지 않는다). known C 생산: `b0578 ORI.B #1,CCR`(fall-through `b057c RTS`). C를 넘기는 `RTS`: 없음(`b051a`의 호출자 6곳 `afcfc` `afea2` `aff0a` `aff52` `aff86` `afee2`는 복귀 뒤 C를 읽지 않음, `cread.py`). `2986` 실패 경로(`b0524`)는 caller-X checked 오류.
- [F] **나가는 곳**(모두 `case` block 시작): callee `2986` `3af8` `8ff4` `43e34` `43ea4` `443d2` `490ba` `49214` `49274` `49a58` `49f8c` `49fc6` `4be06` `4be34` `e9112` `b0468`, 분기 출구 `af92c` `af96a` `afc16` `b005e`(N09), `JMP 2a00`. 범위 밖에서 들어오는 실제 진입: N09 `af768 MOVE.L #af8cc`, `af97e MOVE.L #af990`(routing된 N09), `af626 MOVE.L #afbbe`(N09), routing 밖 `af3da BRA.W afe30`·`afefc BRA.W aff24`(`afe30` `aff24`는 FR9 시작), `afee2 JSR b051a`. 설치: `af8f2` `af910` `afd7c` `aff00` `aff30`(실행됨, 바로 다음 PC라 들어감), `afe40`(`afe30`의 다음 PC, 들어감), `b001a`(`b0014`의 다음 PC, 들어감), `afed8`(`afe8e`; 뒤는 `afe94 BRA.W b005e`라 쓰기만), `af92c` `afc16`(바로 다음 PC이지만 N09가 routing한 시작).
- [F] **자료**: `49f8c`의 A1 `b0e94` `b10f0` `b12ac` `b0fe8` `b13ee` `b1076`, `490ba`의 A0 `caba0`, `2986`의 자식 `b3dbc`(A1 `100bf4`, 스택 WORD 7개를 넣고 `b0556`에서 `MOVEM.W`로 7개를 부호 확장해 꺼냄).
- [F] **natural**: `boot-demo-0` frame 410..529의 node `1017c8` `101704` `101640`(callback `af8cc` `af8f2` `af910` `af990` `afd7c` `aff30`; scratch 검색).
- [F] **F4 범위**: R09 `af3fe..b05bc`가 FR9 6 범위를 뺀다.
- [I] 의미: `af990`은 N09 계열 객체(군중·포로 [I])의 피격 반응 상태 선택(BYTE `5e` = 맞은 무기 종류 0..1a, BYTE `61` bit 1, BYTE `15` bit 7로 표를 고름)과 그 반응 anim(`afbbe`..`b005e`, 낙하·튀어오름·도망)이다.
- 검증 계획: FR8과 같다(단위 시험 220 × 3 C, 내부 618, 표 95칸 각 색인, 소비자 5개 사슬, natural, 실제 ROM 5 × 1,500, 변이, V1).

## 미확인

- [U] node field 의미(`15` `1e` `20` `22` `2e` `32` `36` `3a` `42` `46` `54` `5e` `61` `68` `6f` `76..8f` `94..a0`), A5 field `5418`의 뜻, 표 `4376c` `38f0c` `cdf3e`의 기록 형식, GREC(LONG `96(A6)`) 기록의 실제 생산자 표.
- [U] `aea38` 계열은 native로 `aea38` `aea4a` `aea54` `aea68`만 실행됐다(frame 577, run 끝). `ae930` 상태 기계와 `d39f6`/`d3a2e`는 IO 관측에서 실행되지 않았고 closure로 들어왔다(V1 선언 상태·실제 ROM 차분으로만 확인).
- [U] IO pack 자연 node 상태의 레지스터(선언)와 실제 dispatcher 진입 레지스터의 차이(결정 6의 [I]).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr8.cpp`(case label 229 = scratch `starts_fr8.txt`와 집합 일치; 공용 함수 `ofr8_bit`(BSET/BCLR/BCHG.B), `ofr8_btst`(BTST.B + BEQ), `ofr8_dbit`(BTST #n,D0), `ofr8_carry`, `ofr8_add_word`, `ofr8_jitter`(`42ef4` 꼴), `ofr8_angle`/`ofr8_speed`/`ofr8_split16`/`ofr8_split64`(각도 분할), `ofr8_shard`/`ofr8_shard_link`(`2986` 자식 `430e6`), `ofr8_kind`(`cdc2c..`), `ofr8_child_d1d38`/`ofr8_child_place`(`ae960..`), `ofr8_offset`(`d384a`/`d386c`)), `engine/tests/animation_machine_objects_fr8_test.cpp`(생성 구역 + 수작성 규칙: `42f9a` 색인 0..8 전부와 표 항목의 대상, 표 밖 색인 9 / `8000` / `fffe`(두 번 돈 뒤 `42f82` 내부 오류), `42f92` 무부호, `42ec8` BMI, `42ffa` BLT 넘침, `43008` WORD 연산, `42e24`/`42e3c`/`42e54` 분할과 `42e20`/`42e3a`/`42e52` BYTE 올림, `42e6e` 색인, `42e9e`/`42eb0` 동점, `42de0` BSET/BCLR 순서, `42ef4`, `42fd4`, `aeb38` 부호 BLT, `ae948`, `d3a5e` 꺼냄·BGT, `aeaca`·`cdce4` 음수 색인, `38f8e` TST.W, `38eec` 색인, `38fa2` mask, `38fc4`/`38fd0`, `d3500`/`d384a` 기록, `d355a`/`d3570`/`d3540` 감소, `cc7b4`, `aea68`/`aea72`, `d3822` Set), `tools/generate_animation_machine_objects_fr8_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; 두 번 실행해 시험 파일 바이트 단위 같음 SHA256 `feb828b1a2c583f07a6a2a2faf24929f9219cd42b9c65df9ebe2b2f0cd3fcda6`, 약 80초; 진입과 같은 PC에서 멈추는 행(계산 점프가 자기 block으로 돌아옴)은 zero-step이라 버림), `tools/unit_fixture_specs/fr8.py`(V1 spec; FR7 spec의 공용 부분(routing 해석, `first_unrouted`, `block_next`, carry oracle, chain/node/natural/callee family) 그대로, 단위 부분 교체: 선언 기록 GREC `10fb00`·GTAB `10fb40`, ROM 생성 기록 5개, LONG `82(A6)` := 자연 N32 action routine(`3a60a` `3a7b6` `3a8d2` `3a9aa`; `3a5be`의 `JSR (A0)` 대상 — 다른 값은 native가 RAM fetch로 실패), 스택 선언, `BUNDLED = (cdd02,)`, `TABLE_JUMPS = {42f9a: 표 9칸}`, 사슬 6개, 오류 행(내부 966 + 홀수 1 + Unknown C 6 + 홀수 node/stack/기록 6 + 계산 착지 1 + 실행 뒤 실패 5), family `natural`(boot-demo-0 10 frame)). 공유 수정은 "공통 규칙"의 다섯 곳과 stage_event / stage_event_ops `CPP_PINS`(옛 값 주석)뿐이다.
- [F] `make -j3 all test`(작업자, scratch `make3.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 281개(FR7 280 + 1), Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR8 시험 줄: `animation machine objects fr8: 940 fixtures (724 single-block, 156 path, 30 producer chain, 12 declared C, 18 checked error (6 with a later failing PC), 44 kept C), 229 blocks, 4919 calls, 233391 checks`. 생성기가 실제 생산자 사슬을 두 C 값으로 만든 것 5개(`4b54e` → `ae936`, `1ab02` → `aea22`, `497a6` → `cdd0c`, `28ae` → `d3814`·`d3a4c`); `3a4da` → `38fb4`는 RAM 세계에서 Clear만 나와 선언 C 행만 있다(V1·실제 ROM 차분이 실제 사슬). 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 44개 + sentinel 모두 어떤 행의 stop.
- [F] UBSan(작업자, `-fsanitize=undefined -fno-sanitize-recover`): 빌드 경고 0, 실행 종료 0, runtime error 0.
- [F] V1 fr8(작업자 1회, scratch `v1_try`): fixture 1,931개(block 843, chain 12, node 33, natural 27, callee 15, error 985, failpc 6, negative 10) failed 0, 방문 시작 229/229, 빠진 후속 0, 도달 못한 분기 결과 0, carry oracle Unknown/Clear/Set = 917/13/6(known tag가 native C와 같음). 회귀 spec(작업자 확인용): fr4 1,629 · b2e · b2d · b2b · fr7 모두 failed 0(전체 회귀는 결정적 runner).
- [F] `dleft.py`(이 worktree routing `9592e227…`): 실행된 routing 밖 PC D 51 / E 220 / C 620, D 중 C 무관 0 / C 뒤 51(모두 FR9 `af990` 계열), 예측 일치 165,714(변화 없음), 첫 정지 영역 C·E 15 / C 1.
- [F] 결정적 runner 준비물(scratch `ms5-scratch/fr8/`): `mut/run_mut.py`·`mut/mutants.py`(변이 274개; `--check`: 패턴 유일·문법 검사 통과(`patterns ok 274`), 3개 시험 실행 `killed 3 of 3` 뒤 산출물 삭제), `realrom/build.sh`·`realrom/run_all.sh`·`realrom/real_fr8.py`(FR7 harness에 FR8 world·소비자·진입; 선언 정지 FR4 표 항목 `cc7ac + 4k`(`cc7b4` 제외)/`cc82e + 4k`, `16ed6..16eee`/`8c16` 내부, `3c0000` MOVEM.W 쌍 병합, 계산 착지 분류에 `42f9e` 추가; 시험 1회 60건 `mismatches 0` 뒤 산출물 삭제).
- [F] stage_event / stage_event_ops `CPP_PINS` 새 값(작업자가 갱신, 옛 값은 주석): `animation_machine.cpp` `9592e227f3a4cfe478dafa4fcf3842dae50072fd7adbb828fd5108f0fe4a270b`, `animation_machine_internal.h` `a7d92b011f252b522dc8ac0e7f2c0b9bb3c0f72e2bb1a97bd9803f0e0deb400d`.

## block 목록

[F] scratch `starts_fr8.txt`(SHA256 `8a2f4e1a30776bb6f1f7de5c20c13492f00e2644fbea4b77bafe5553620a8e77`)와 같다.

- **`38e92..38f0c`(15)**: `38e92 38ea4 38eae 38eb4 38eba 38ebe 38ec8 38ece 38ed2 38edc 38ee2 38ee8 38eec 38f02 38f08`
- **`38f14..38ff4`(26)**: `38f14 38f1e 38f22 38f2a 38f32 38f3c 38f44 38f4c 38f56 38f5e 38f66 38f6e 38f78 38f82 38f8e 38f98 38fa2 38fb4 38fbc 38fc4 38fd0 38fd8 38fe0 38fe8 38fec 38ff0`
- **`42d9c..4309a`(65)**: `42d9c 42da4 42dd2 42de0 42e0c 42e20 42e24 42e3a 42e3c 42e52 42e54 42e68 42e6e 42e88 42e8e 42e98 42e9e 42eaa 42eb0 42ec0 42ec6 42ec8 42ed2 42ed8 42eee 42ef4 42f08 42f12 42f18 42f32 42f38 42f4c 42f52 42f5c 42f62 42f7c 42f8a 42f92 42f9a 42fa2 42fa6 42faa 42fae 42fb2 42fb6 42fba 42fbe 42fc2 42fc6 42fd0 42fd4 42fde 42fe8 42fec 42ff0 42ffa 43002 43008 43030 43044 43048 4305e 43060 43080 43090`
- **`430ba..430e6`(3)**: `430ba 430d0 430e0`
- **`ae930..aeb4c`(51)**: `ae930 ae936 ae93a ae93e ae948 ae956 ae960 ae97c ae986 ae99e ae9a8 ae9b4 ae9bc ae9cc ae9d6 ae9ee ae9f8 aea04 aea08 aea12 aea18 aea22 aea26 aea36 aea38 aea4a aea54 aea68 aea72 aea78 aea8c aea92 aea9a aea9e aeaaa aeab0 aeaba aeac0 aeac4 aeaca aeb02 aeb08 aeb12 aeb1c aeb22 aeb28 aeb2c aeb32 aeb38 aeb44 aeb4a`
- **`cc7b4..cc7b8`(1)**: `cc7b4`
- **`cdc24..cdd2e`(23)**: `cdc24 cdc2c cdc42 cdc46 cdc4e cdc64 cdc68 cdc70 cdc86 cdc8a cdc92 cdca8 cdcac cdcb4 cdcca cdcce cdce4 cdd06 cdd0c cdd10 cdd16 cdd1a cdd24`
- **`d3500..d354c`(8)**: `d3500 d3518 d3522 d3528 d3532 d353c d3540 d3546`
- **`d354e..d3580`(7)**: `d354e d3554 d355a d3562 d3570 d3578 d357e`
- **`d3802..d38e2`(21)**: `d3802 d3814 d3818 d3822 d3826 d3830 d3836 d383c d384a d385c d385e d386c d387e d3880 d3892 d3898 d38a0 d38ac d38bc d38c2 d38d0`
- **`d39f6..d39fe`(1)**: `d39f6`
- **`d3a2e..d3a70`(8)**: `d3a2e d3a36 d3a38 d3a4c d3a50 d3a5a d3a5e d3a6e`

FR9 block 목록(`starts_fr9.txt`):

- **`af8cc..af92c`(10)**: `af8cc af8d8 af8de af8f2 af8f8 af8fe af906 af90c af910 af926`
- **`af990..afb3c`(91)**: `af990 af996 af99c af9a6 af9b0 af9bc` + 표 `af9c8..afa30`(27) + `afa34 afa40` + 표 `afa4c..afab4`(27) + `afab8 afac4` + 표 `afad0..afb38`(27)
- **`afb3e..afc16`(28)**: `afb3e afb44 afb50 afb54 afb58 afb5e afb6a afb6e afb72 afb78 afb84 afb88 afb8c afb90 afb94 afb98 afb9c afba0 afba4 afbaa afbb6 afbba afbbe afbc8 afbde afbe2 afbf8 afbfe`
- **`afcf2..afed8`(47)**: `afcf2 afcfc afd00 afd16 afd1c afd2a afd38 afd42 afd48 afd5a afd68 afd76 afd7c afd8a afd90 afd94 afda2 afda6 afdbc afdc2 afdd2 afdd8 afdde afdf0 afdfe afe0a afe20 afe30 afe40 afe4e afe54 afe66 afe6a afe6e afe74 afe7a afe80 afe84 afe8e afe94 afe98 afea2 afea6 afebc afec4 afece afed4`
- **`aff00..b005e`(38)**: `aff00 aff0a aff0e aff24 aff2a aff30 aff36 aff3c aff40 aff4e aff52 aff56 aff5c aff6a aff78 aff82 aff86 aff8a aff90 aff9a affa0 affb2 affc0 affc6 affdc affe0 afff6 afffc b000a b0014 b001a b0024 b0032 b003c b0042 b0048 b004c b005a`
- **`b051a..b057e`(6)**: `b051a b0524 b0556 b055e b0578 b057c`

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK. FR8 시험 `942 fixtures (726 single-block, 156 path, 30 producer chain, 12 declared C, 18 checked error (6 with a later failing PC), 44 kept C), 229 blocks, 4927 calls, 233983 checks`.
- [F] `ubsan`: build/run 종료 0, runtime errors 0.
- [F] `mutation`: total 274, 첫 실행 killed 268, hint 후 killed 269, equivalent 5(Qwen 판정을 메인이 코드로 확인).
  - `split16-long`: 크기 변경은 상위 bit만 바꾸고 결과는 이후 `&0xf`로 masking된다.
  - `43008-lsl-long`, `43008-lsl-byte`, `43008-asr`: 표 index 계산에서 low WORD만 사용되고 `D0`는 block 종료 전에 덮어써진다.
  - `d3570-word`: 해당 연산은 모든 입력에서 WORD 결과와 flag가 같다.
  - fixed gap:
    - `cdd10-2`(`MOVE.W (A0)` 대 `MOVE.W 2(A0)`): synthetic `cdf3a..cdf56` window 안의 hint `A0 = cdf3a/cdf3e`를 `tools/unit_fixture_specs/fr8.py`에 추가해 두 WORD가 다른 입력을 제공했고 killed.
- [F] real-ROM: batches `s1`, `s2`, `s3`, `f4`, `f5` 각 1500 cases, mismatches `0,0,0,0,0`; covered starts `229`, `228`, `229`, `229`, `229`(합집합 229/229). 계산 점프 `42f9a`가 다른 block의 non-start PC에 착지하는 경우는 checked PC error로 분류된다(FR4 결정 2, FR1 결정 3; `s3` 8건).
  - harness 수정: 분류 조건을 `objects` 계열에서 모든 `unsupported animation ... PC`로 넓혔고, 계산 점프 PC 검사를 마지막 40 PC가 아닌 전체 native trace 기준으로 바꿨다(이전 `s2` 1건, `s3` 2건은 이 분류 누락).
- [F] V1: FR8 fixtures 1933, failed 0, runs 2, identical true(digest `0415c8b66aa498e9`); regression specs 31, 모두 failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 종료 0. `objects_g1` verdict는 FR7과 같다(execution-equal 4689, checked-boundary 54, native-step-limit 8, invalid-declared-flag-precondition 1).
- [F] frames: `d1` 54400/54400, mismatches 0; `controller_game` 54400/54400, 0; `irq` 54400/54400, 0; `demo` 45684/45684, 0.
- [F] IO: matched_total 165714, baseline 165714, delta 0, mismatches 0, cpp_errors 0, runs 2, identical true; per_config `P0` 81600, `P1` 75304, `P1b` 7424, `boot-demo-0` 381, `boot-title-idle` 600, `boot-title-start` 122, `fx-*` 283; frontier `4e68e` `C` 15, `1d1f4` `C` 1. FR8 코드는 첫 `C` stop 이후에만 실행되므로 IO matched frames는 변하지 않는다.
- [F] area-D remaining PCs: before 124, after 51, 모두 `C`-gated.
- 검증 방법: deterministic runner `ms5-scratch/tools/verify_unit.py`(LLM 없음). 전체 실행은 `aabf96e`와 같은 내용의 작업 tree에서, hint 추가 후 make·ubsan·real-ROM·V1을 다시 실행했다. mutant 분석과 이 기록 초안에 local Qwen을 사용했고 메인이 검토·수정했다.
