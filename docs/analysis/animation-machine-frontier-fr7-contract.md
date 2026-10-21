# frontier 단위 FR7(C 뒤에만 IO에 나타나는 영역 D: 충돌 판정 `4ad6c`/`4abc0` 묶음과 객체 `d2f90`·`cdd2e`·`3ad48`·`cde42` 등) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. FR2..FR6 계약(`animation-machine-frontier-fr6-contract.md`)의 구조·공통 규칙을 따르고 다른 점만 적는다. 메인 지시: `area-d-completion-plan.md`(맨 위 메인 결정) §4와 FR6 계약에 따라 FR7 = 다음 C 뒤 영역 D root(IO run에서 첫 C 정지 뒤에만 실행되는 D 코드; FR6 뒤 `dleft.py` 262 PC). 현재 routing으로 다시 재서 native 실행 수가 큰 C 뒤 D root를 자연스러운 closure로 약 220 block 이하까지 고른다. C 뒤 코드라 IO 비교의 사슬로는 닿지 않으므로 단위 시험·V1은 선언 상태와 IO state pack의 자연 node 상태(그 코드가 C 정지 뒤 native로 실행된 frame)로 선다. 계산 표는 모두 전사하고 TRAP 자리는 checked 경계다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기 `200094` `2000b4`는 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `ba9bb6b`(branch `claude/fr7-core` = `main`, FR1..FR6 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `989b7951f8613fcb3643603292b94b3a61fbb97b5ca16ad7e66cc31bef1adcfe`(= FR6 IO 재실행의 routing), `animation_machine_internal.h` `cef94f5cbabb5b89a0cdaf27c53f86cec9bf32abeaecedf6fdde8f3778b284c1`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; run 기록의 `unr_pcs`/`unr_new`, state pack `states/<config>/<case>.pack.gz`). FR6 IO 재실행의 예측·실측 일치 frame **165,714**, D 첫 정지 0.
- [F] 정적 디코드: capstone M68000, FR4..FR6과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, `MOVE.L #imm,(A6)` 설치 값 중 범위 안의 것, 범위 밖에서 들어오는 실제 분기 대상, 연속 Bcc 묶음은 한 block). routing된 PC, `RTS`, `TRAP`, 계산 점프에서 멈춘다. `28ae` 자식 값은 기록만 한다. 진입 = 아래 root들이 IO run에서 실제로 실행한 routing 밖 PC(다른 진입의 closure 안에 이미 든 것은 뺌). 설치 값은 native가 실행한 것만 따라간다(FR3 결정 2).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr7/`
  - `tools/`: FR6 scratch 도구의 경로만 새 배치(`metalslug-fr7`, `ms5-scratch/fr7`)로 바꾼 사본(`fclos.py` `hroute.py` `dstate.py` `dleft.py` `refidx.py` `cread.py` …), 새 `fr7roots.py`(현재 routing에서 C 뒤 D root별 실행 수·closure 크기), `fr7set.py`(합집합 closure의 누적 block 수와 예측), `unit_fr7.py`(이 단위 정의; 묶음은 환경 변수 `FRG`), `inrefs7.py`(범위 밖에서 범위 안으로 들어오는 분기·상수 전수), `probe_scan_fr7.py`, `fr7dis.py`.
  - `starts_fr7.txt`(시작 205개) SHA256 `19883209598827a63fae8aecdb92d60a4e5caca3db36df5eb3b0789d536015b3`; `ranges_fr7.txt`, `unit_fr7.out`(block별·범위 전체 디코드), `inrefs7.out`, `probe_fr7.out`.
  - 재현: `cd /Users/start/Workspce/metalslug-fr7 && FRG='4ad6c=4ad6c 4ab88;e8b6e=e8b6e;cdexx=cded2 cde6e cde42;3611x=36126 3611e 36118;d23b2=d23b2;cdd2e=cdd2e cc958 cc5e8;3ad48=3add4 3ad48 4356e' .venv/bin/python /Users/start/Workspce/ms5-scratch/fr7/tools/unit_fr7.py B D`(시작 204개를 쓴다; `e8b80`은 아래 "참조"의 결정 3으로 더한다).
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정**(`dleft.py`, routing `989b7951…`): 실행된 routing 밖 PC는 C 620 / D 262 / E 220, D 중 C 무관 0 / **C 뒤 262**, 예측 일치 frame 165,714, 첫 정지 영역 C·E 15 / C 1(D 0). FR6 기록과 같다.
- [F] **root 고르기**(`fr7roots.py`: C 뒤 D root별 실행 PC·실행 수·closure; `fr7set.py`: 합집합). native 실행 수 순서: `4ad6c`(3,670회, 14 run, closure 57 block; routing된 `4ab88`의 뒤 `4abc0..`와 같은 closure) `d23b2`(1,532, 1 run, 30) `42e68`(1,362, 계산 점프 `42f9e`) `4ab88`(1,348) `3add4`(864) `cded2`(351, 9 run) `42d9c`(152, 계산 점프 `42f9e`) `e8b6e`(98, 14 run, 40) `cdd2e`(85, 41) `af8f2`(78, `af990` 객체의 상태; 그 객체는 계산 점프 7개) `cc958`(77) `afd7c` `aff30` `d383c`(50; `d3500` 객체) `3ad48`(48) `4356e` `cde6e` `cc5e8` `d3554` `cde42` `36118`/`3611e`/`36126`(13 run) ….
- [F] **선택**: 계산 점프가 있는 `42d9c`/`42e68`(`42f9e` 표; 계획 FR8)과 `af990` 계열(`af9c4` 외 6; 계획 FR9)은 남긴다. 그 밖에서 실행 수가 큰 root를 객체 단위로 묶어(한 객체의 상태를 나누지 않음) 넣는다: 여러 run의 root(`4ad6c`/`4ab88` 14 run, `e8b6e` 14, `cde42`/`cde6e`/`cded2` 9, `36118`.. 13) 다음 1 run root의 실행 수 순서(`d23b2`, `cdd2e`+`cc958`+`cc5e8`, `3add4`+`3ad48`+`4356e`). 다음 후보 `cdc24`(+24 = 228)와 `af8f2`·`d383c`(FR9 객체의 일부)는 넣지 않는다.
- [F] **합계**(`unit_fr7.py`): **205 block 시작**(closure 204 + 범위 밖 분기 대상 `e8b80`), 13 범위, 명령 575, 짝수 PC 1,112(내부 907), 이어 붙인 바이트 2,224, SHA256 `b48ab88ad0856eeab751305fd94419b2383a294263f4f4fa2c234681d3748265`. 덮는 실행 PC 138개(실행 8,240회, run 14: P1 12(`068..071` `094` `095` `100` `101` `106` `107` `110` `111`), `boot-demo-0`, `boot-title-start`), 모두 영역 D·C 뒤. 기존 routing과 겹침 0, 연속 Bcc 묶음 0. TB 시작이지만 block 시작이 아닌 실행 PC 6개(`d2fe6` `d2fee` `d2ff6` `d2ff8` `d2ffa` `d3000`, 모두 `d2fd6`/`d2ff4` block 안의 Unicorn TB 경계)는 진입으로 쓰지 않는다(계획 §7).
- [F] **예측**(`fr7set.py`): IO 일치 frame **165,714 그대로**(C 뒤라 사슬이 닿지 않음; 계획 메인 결정 "FR7~FR9의 IO 확인은 C·E 연결 뒤"), D 남은 실행 PC **262 → 124**(C 무관 0, C 뒤 124), 첫 정지 영역 변화 없음(C·E 15, C 1).
- [F] **F4 범위 문서와의 겹침**(`animation-machine-object-callbacks-f4-scope.md` 범위 식 전부와 교차): U38 행 `4b8e4..4c38c`와 `4c0f0..4c1de`(27 시작). U38은 아직 구현되지 않았으므로 착수할 때 이 범위를 빼야 한다(결정 7). U32 `4ae4a..4b4fa`와 고분류 꼬리 행(`2b418..4dbd6`, 서술)은 겹치지 않거나 범위 행이 아니다.

| 묶음(진입) | block | 명령 | 실행 PC / 실행 수 / run | 범위 |
| --- | --- | --- | --- | --- |
| 충돌 판정 `4ad6c`(N08 `4ae4a`의 64 후보 block이 `BSR`; 뒤 `4abc0..` 피해 적용, `BRA 4abc0`) + 지면 탐색 `4c0f0` | 57 + 27 | 194 + 63 | 49 / 5,018 / 14 | `4abc0..4ae4a` `4c0f0..4c1de` |
| `e8b7e`/`e8b80`(C helper `e8b5a`의 꼬리; `e8b6e`가 root) | 14 | 41 | 7 / 98 / 14 | `e8b7e..e8c0e` |
| 객체 `cde42`(`cddee`의 `28ae` 자식; + 설치 `cded2`) | 13 | 26 | 11 / 405 / 9 | `cde42..cde6e` `cde96..cdeea` |
| 표 handler `36118`(LONG 표 `4a55c`) | 5 | 13 | 3 / 39 / 13 | `36118..3614a` |
| 객체 `d2776` `d2782` `d278e` `d279a`(LONG 표 `bbf1a..`의 callback, 공용 꼬리 `d2f90`; + 설치 `d3062`) | 24 | 70 | 28 / 1,532 / 1 | `d2776..d27a6` `d2f90..d309a` |
| 객체 `cdd2e`(`ccbb8` 외 9곳의 설치·`BRA` 대상; helper `cc5e8` `cc958`) | 41 | 82 | 19 / 195 / 1 | `cc5e2..cc600` `cc958..cca44` `cdd2e..cdd86` |
| 객체 `3ad48`(B2E `3ac2c`의 `2986` 자식; + 설치 `3add4`) + 소리 helper `4356e` | 21 + 3 | 78 + 8 | 21 / 953 / 1 | `3ad48..3ae84` `4356e..4358c` |
| 합 | **205** | 575 | 138 / 8,240 / 14 | 13 범위 |

## 요약

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `36118..3614a` | 50 | `fb86e8af64a6d64c81bb31ba63c579ee313f7c56b5c79a0dbfd03f2fab64f2ae` | 5 | 25 |
| `3ad48..3ae84` | 316 | `0f31e06a3dbdb389aab16d468279b811a502940dd12caac742ce8e2412706e48` | 21 | 158 |
| `4356e..4358c` | 30 | `abefc72c261de64c1d338fc21b2d40538b30a6ed2c1a91bbe51bdc8c90fd43f7` | 3 | 15 |
| `4abc0..4ae4a` | 650 | `74992dc68fa9a10bf07b59097a8184d2172d418ae41d707c8c4c8ac416433ee8` | 57 | 325 |
| `4c0f0..4c1de` | 238 | `81e7a4ee1279ac337f527f8dd924663eaa3e13aafb76f1ac0880aa6fe8374f5e` | 27 | 119 |
| `cc5e2..cc600` | 30 | `9b9d3cbad4b5d16f86753b5101570fc179fcbdbda761e578a836130ec78abd94` | 4 | 15 |
| `cc958..cca44` | 236 | `45eb1a9dbe90b328acdac72da1e80695c24e29f0b912cefc3408075e87d88ade` | 22 | 118 |
| `cdd2e..cdd86` | 88 | `083e53291be25ed9f3126e403e03a22d9ccd199be074cdb7f06da0cf960606c3` | 15 | 44 |
| `cde42..cde6e` | 44 | `b6ea28705514292bf481c28e93f2a2d028b222ea25809e7f0d5864186ed02128` | 2 | 22 |
| `cde96..cdeea` | 84 | `31ca3ace6b8004f89f6b0a0076468db41e01aece10916a6ecdaef9a81e2dd41b` | 11 | 42 |
| `d2776..d27a6` | 48 | `71c0a41badc4ce3d1b5e939d103ee8ed7faf6f7ff864cfa607a9dc2f7c98f207` | 4 | 24 |
| `d2f90..d309a` | 266 | `befcc9dc114e9bd5fea308bb0d85b07540b6273b5c379375f1280d2842f5ac7e` | 20 | 133 |
| `e8b7e..e8c0e` | 144 | `f3aa65320a6e17de90aa99a6ca00bbeaea37f89004a084f7da9bfd382a6e55fa` | 14 | 72 |
| 합계 FR7 | 2224 | 이어 붙인 바이트 `b48ab88ad0856eeab751305fd94419b2383a294263f4f4fa2c234681d3748265` | **205** | 1112(내부 907) |

- [F] closure가 13 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 범위 사이는 자료(`cc5d8..cc5e2`, `3614a..` `28ae` 자식 값, `d27a6..d2f90` 실행되지 않은 같은 꼴 stub 약 150개와 자료), routing된 코드(`3ad46` `4abbe` `4c0ee` `cc600` 앞뒤의 routing 경계: `3acd6..3ad48` B2b, `4aa88..4abc0` U7·`4ab88..4abc0`, `4c0ea..4c0f0` N33, `cc600..cc696` FR4), 또는 routing 밖 형제 코드(`e8b5a..e8b7e` C helper, `cdd86..cde42`, `cdc24..cdd2e` 계획 FR8)다.
- [F] **명령 종류**(575개; `unit_fr7.out` 집계): `MULS.W (An,D4.W),Dn` 4(`3ae18`; ROM WORD 표 `4411e`/`4419e`), `MULU.W D3,D2` 1(`4ac36`), `ASR.L` 10, `ASR.W #1` 6, `LSR.L` 3, `LSR.W` 3, `LSL.W #2` 1, `NEG.L` 9, `NEG.W` 5, `SWAP` 22, `EXT.W` 2, `SMI.B D4` 2, `SNE.B 78(A6)` 1, `ADD.L`/`SUB.L` 22(RMW 포함), `MOVEM.L` 9(메모리↔레지스터 4: `3adba` `3ae62` `cca1c` `cca2c`; 스택 5: `3ae04` `4ac82` `4acd6` `4ad4a` `4ad66`), `CMPA.L #0` 1·`CMPA.W #0` 2, `MOVEA.W #0` 2, `ADDA.W` 1, `SUBQ.W #6,A7` 1·`ADDQ.W #6,A7` 2, `TST.W (A7)+` 1, `CLR.L` 3·`CLR.W` 2, `ANDI.B #fe,CCR`/`ORI.B #1,CCR` 1씩, `BTST` 20(레지스터 `D0` `D1` `D6` 3)·`BSET` 4·`BCLR` 1, `CMP.L (A7),D6` 2, `CMPI.L` 1. **계산 점프·`JSR (An)`·TRAP·DIVU/DIVS·ABCD·ADDX/SUBX 없음**, I/O port·bank 쓰기 없음.
- [F] **나가는 곳**(각 실행부의 `case` block 시작으로 routing됨; 29개 모두 `case 0x…:` 확인): callee `28ae` `8ebe` `1a988` `1aa3a` `1ab80` `3af8` `43e08` `43e34` `43e38` `43ea4` `43eb8` `443d2` `44602` `46d72` `497a6` `49a58` `49a84` `49f8c` `49fc6` `4bb52` `4bce0` `4be2c` `4be34` `4be50` `4bfa4` `4c0b0` `d3c2a` `e625e`, 출구 `JMP 2a00`(`3adfe` `3ae7c` `cc5e2` `cdd40` `cdd78` `cdee2` `d3094`). routing 밖으로 나가는 곳은 없다. 다른 실행부 block의 **중간**으로 들어가는 분기·점프는 없다(FR6 `4fce0` 교훈: 출구 29개가 모두 block 시작).
- [F] **참조**(ROM `<100000` 짝수 오프셋 전수 디코드 + LONG 상수, scratch `inrefs7.py` 236줄, `LONG` 검색): 범위 밖에서 들어오는 실제 진입:
  - `4ad6c`: routing된 N08 `4afe0..4b4d6`의 `BSR.W` 64곳(`MOVEA.L d(A4),A2; MOVEQ #k,D4; BSR.W 4ad6c`).
  - `d2f90`: 밖 stub `d2772..d2e7a`의 `BRA.W` 약 150곳(같은 꼴 `MOVE.W #167,D0; LEA dxxxx(PC),A0`), `d2fd2`: 밖 `d2f8c BRA.W`. stub `d2776` `d2782` `d278e` `d279a`는 LONG 표 `bbf1a..bbf46`의 값이다(자료).
  - `cdd2e`: 밖 `ccbb8` `ccc80` `ccd6c` `cd0f6` `cd368` `cd506` `cd6a4` `cd77c` `cdc14` `cdd24`의 `MOVE.L #cdd2e,(A6)`와 `ccf4a` `cd94a` `cdb04` `cdd2a`의 `BRA.W`.
  - `cde42`: 밖 `cddee MOVEA.L #cde42,A0`(`28ae` 자식), `cde96`: 밖 `cde3e BRA.W`.
  - `3ad48`: routing된 B2E `3ac2e MOVEA.L #3ad48,A0`(`2986` 자식). `4356e`: 밖 `42da0 BSR.W`. `36118`: LONG 표 `4a55c`. `4c0f0`: 범위 안 `e8bfa`만. `e8b80`: **밖 `e8b7a BEQ.W e8b80`**(routing 밖 C helper `e8b5a`, 실제 명령) — 결정 3.
  - 그 밖의 범위 안 대상은 자료 디코드 잔재다: `360a8 BRA.B 36128`·`360b2 BRA.B 36132`(`36090..36118`은 자료), `46a6a DBcc`·`e3764`·`e381c`(홀수 대상), `4c0c4 BLT.B 4c138`(`4c0c0 JSR 46d72.l`의 operand 안; `4c138`은 `4c136 BCC.W`의 operand).
- [I] 의미(이름은 확정하지 않는다): 각 묶음 절의 [I] 줄.

## 공통 규칙·native 검증 계획

FR2..FR6 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr7.cpp`, 함수 `animation_objects_fr7_block`. 오류 문자열은 `unsupported animation objects fr7 PC`(범위 안 내부 PC 직접 진입), `objects fr7 caller requires known carry`(C 소비 block에 Unknown C; 소비자 8개). 그 밖의 오류는 공용 bus/스택 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(13 범위, FR6 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 8개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 설치 값 `3add4`(`3adc6`) `cded2`(`cdec0`) `d3062`(`d3046`)는 모두 바로 다음 PC라 그 block으로 들어간다(FR4 결정 4). 쓰기만 하는 설치는 없다. `28ae` 자식 값 `3614a`(`36128`)는 A0로 넘기기만 한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. 다른 단위·다음 단위가 routing할 코드(`e8b5a` `42d9c` `cdc24` `cdd86..` 등)는 rollback 탐침으로 쓰지 않는다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): FR2와 같다. 행의 run stop은 실패 block 바로 뒤 PC다.
- **자료 읽기**(live bus, 상한 검사 없음): bank 창 LONG `2000b4`(`3ad4e`, LONG `22(A6)`에 저장만), `200094`(`cde4c` `d2fac`: LONG `22(A6)`에 저장, `cde5c`: RAM에서 다시 읽어 그 주소 + `40`의 LONG을 A1로; `d2fbe`: 다시 읽어 그 주소 + sext(4·WORD D0)의 LONG을 A1로), ROM LONG 표 `3cd26`(`3ad6a`, 색인 sext(4·WORD D0), D0 = `49a84`의 결과), ROM WORD 표 `4411e`/`4419e`(`3ae3e..3ae50`, 색인 2·BYTE ≤ `1fe`), ROM LONG 쌍 `d2652` `d265a` `d2662` `d266a`(`d2f9a`의 꺼낸 A0: LONG `92(A6)` := `(A0)+`, D0 := `(A0)`), ROM BCD 표 `48a3a`(`4ad4a`의 A0 = `48a3a` + sext(2·WORD D0); `e6284`가 `-(A0)`로 A0+1, A0을 읽음), RAM: node field(A6), 표적 객체(A2) field, 공격 기록(A0) field·사각형 목록(`12(A0)..`, WORD `8000`이 끝), 판정 기록 LONG `56(A2)`(그 `8` `a` `10` `11` `c` 필드와 사각형 목록 `12..`), 배율 표 LONG `c(A1)`(색인 sext(2·WORD D0)), LONG `3e(A6)`(`4c1be`의 A0), LONG `92(A6)`(`d3084`의 A0), LONG `5e26(A5)`(`e8ba0` `e8bd6`의 A4: BYTE `5` `6` `7`), A5 field(아래 각 절), 스택. callee에게 주소만 넘기는 값: `3b73e`(`1ab80`의 A0), `3614a`(`28ae` 자식), A1 = A5 + `538e`(`cca1c`). 단위 시험은 합성 typed physical byte를 자료 영역에만 둔다(ROM 자료가 아니다; 이 단위 코드 바이트와 겹치지 않음): bank 창 LONG `200094` `2000b4`와 그 대상(`200094` → bank 표 `2a3000..`), 표 `3cd26..3cd36`(LONG 4개), WORD 표 `4411e..4431f` `4419e..4439f`, BCD 표 `48a3a` 앞뒤, LONG 쌍 `d2652..d2672`. V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** JSR/BSR 복귀 LONG. `36128`: `MOVE.L A0,-(A7)` → `3613a`: `MOVEA.L (A7)+,A1`. `d2f90`: `MOVE.L A0,-(A7)` → `d2f9a`: `MOVEA.L (A7)+,A0`. `3add4`: `MOVE.L 3a(A6),-(A7); MOVE.L 36(A6),-(A7)` → `3ae04`: `MOVEM.L (A7)+,D2-D3`(D2 = 넣은 `36`, D3 = 넣은 `3a`; `3adfe JMP 2a00`은 두 LONG을 남긴 채 나감). `4ac56`: `MOVEM.L D0-D2/D6-D7/A0,-(A7)`(24 BYTE, 낮은 주소부터 D0 D1 D2 D6 D7 A0) → `4acb4`: `MOVEM.L (A7)+,…`. `4ad4a`: `MOVEM.L D1-D7/A0-A4,-(A7)`(48 BYTE) → `4ad66`: 꺼냄. `4c0f0`: `SUBQ.W #6,A7`(A7 −= 6, 32 bit), WORD `4(A7)` := 4, LONG `(A7)` := swap(D0)의 하위 WORD를 0으로 한 값; `4c102..4c1d6`은 이 6 BYTE 틀(LONG `(A7)`, WORD `4(A7)`) 위에서 돌고 `4c1b6`/`4c1d6`의 `ADDQ.W #6,A7`이 푼다. `e8b6e`(밖)의 `MOVE.W D0,-(A7)` → `e8ba0`: `TST.W (A7)+`(WORD를 읽고 A7 += 2). 홀수 A7은 checked 오류다. 직접 진입 world는 이 값들을 복귀 LONG 아래에 선언한다(V1 spec `STACK`).
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B` `ADD.W` `ADDI.W` `SUB.W` `SUBI.B` `ADD.B` `ASR.W` `LSR.W` `LSL.W` `ANDI.W/.B` `OR.B` `NEG.W` `EXT.W` `SMI.B Dn` `SUBQ.B Dn`). `MOVEQ`·`MOVE.L`·`SWAP`·`NEG.L`·`ASR.L`·`LSR.L`·`ANDI.L`·`ADD/SUB.L`·`MULS.W`/`MULU.W`(32 bit 곱)·`MOVEA`·`LEA`는 LONG 전체. `MOVEA.W #0,A0`·`CMPA.W #0,A1`은 부호 확장한 WORD(= 0)와 32 bit 비교·대입. `ADDA.W D3,A0`는 부호 확장한 WORD를 32 bit에 더한다. 색인 `(An,Dn.W)` = An + sext(Dn.W). `ASR.L #n`은 부호 bit 복제(C++에서 부호 있는 shift를 쓰지 않음), `MULS.W`는 두 WORD의 부호 있는 곱(|곱| ≤ 2^30, 32 bit 안), `MULU.W`는 두 WORD의 무부호 곱(< 2^32). 비교(같은 block 안에서 만들고 소비): `CMP.W m,D1` + `BCS`(무부호 D1.W < m), `CMP.B m,D3` + `BLS`(무부호 ≤), `CMP.W m,D3` + `BCS`/`BHI`, `SUB.W D2,D3` + `BHI`(무부호 WORD 54 > D2.W), `CMP.W D3,D2` + `BCC`(무부호 ≥), `CMPI.W #8000,Dn` + `BNE`, `CMPI.W #20`/`#120,42(A6)` + `BMI`/`BPL`(차의 bit 15), `CMP.L (A7),D6` + `BCC`(무부호 LONG), `SUBQ.W #1,4(A7)` + `BCC`(빌림 = 원래 WORD가 0), `ADDI.W #c,D7` + `BCS`(WORD 더하기의 올림), `ADDI.W #20,D0; CMPI.W #180,D0` + `BCC`, `CMPI.W #e0,46(A6)` + `BCS`, `CMPI.W #fb,3a(A6)` + `BLE`(부호 WORD), `CMPI.L #fffff000,8e(A6)` + `BLE`(부호 LONG), `SUBQ.B #1,b6(A6)` + `BPL`(새 BYTE의 bit 7), `SUB.W; NEG.W` + `BMI`, `ASR.W #1` + `BCC`(밀려난 bit 0), `AND.W` + `BEQ`, `TST.B/W` + `BEQ`/`BNE`/`BMI`, `BTST` + `BEQ`/`BNE`, `MOVE.B`/`MOVE.W (An,Dn.W)` + `BEQ`, `CMPA` + `BEQ`. flag는 같은 block 안에서 만들고 소비한다(예외: "carry").

## carry

- [F] **소비 block 8개**(Clear 쪽 / Set 쪽):
  - `1ab80`: `3ae78 BCC.W 3ae82`(`3ae82` / `3ae7c`), `d308e BCS.W d3094`(`d3092` / `d3094`).
  - `46d72`(U12): `4c128 BCC.W 4c14a`(`4c14a` / `4c12c`), `4c182 BCC.W 4c1a4`(`4c1a4` / `4c186`).
  - `49fc6`: `cdd3c BCC.W cdd46`(`cdd46` / `cdd40`), `cdede BCC.W cdee8`(`cdee8` / `cdee2`), `d3080 BCS.W d3094`(`d3084` / `d3094`).
  - `497a6`(U20): `cde9c BCS.W cdeb2`(`cdea0` / `cdeb2`).
- [F] **known C 생산 block(자기 block 안에서 C를 정하고 끝남)**: `4c1b6`(`ADDQ.W #6,A7; ANDI.B #fe,CCR; RTS` → Clear), `4c1d6`(`ADDQ.W #6,A7; ORI.B #1,CCR; RTS` → Set). 읽는 곳: `4c0f0`의 유일한 호출자 `e8bfa`의 복귀 `e8c00 MOVE.W #b,D7`은 C를 읽지 않는다(그래서 carry 보존 목록에 넣지 않는다; 정지가 복귀 PC일 때만 그 tag가 보인다).
- [F] **C를 넘기는 `RTS`: 없다.** 이 단위의 subroutine(`4ad6c` `4abc0` `4c0f0` `cc5e8` `cc958` `4356e` `36118` `d2f90` `e8b7e` `e8b80`)의 모든 직접 호출자는 복귀 뒤 C를 읽지 않는다(scratch `cread.py`: `4ad6c` 64곳 0, `4c0f0` `cc5e8` `cc958` `4356e` 1곳씩 0, 나머지 0).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 8개다: `3ae78` `4c128` `4c182` `cdd3c` `cde9c` `cdede` `d3080` `d308e`. Unknown C로 소비자에 들어오면 checked 오류다. block 경계를 건너 다시 계산하는 flag와 X는 없다.

## 충돌 판정 `4ad6c`, 피해 적용 `4abc0`

- **`4ad6c`**(N08의 후보 block이 A2 := 표적 객체, D4 := 후보 번호로 `BSR`): A1 := A2 + `5a`, BYTE `5744(A5)` bit 7 = 1 → `4ad7c`, 아니면 `4ad78`: A1 += 1. **`4ad7c`**: BYTE `(A1)` ≠ D4.B → `4ae48 RTS`, 아니면 `4ad82`: A1 := LONG `56(A2)`, A1 = 0 → `4ae48`, 아니면 `4ad8e`: A3 := A0 + `12`, D0 := LONG `(A3)+`.
- **`4ad94`**: D1 := LONG `(A3)+`, BYTE `15(A6)` bit 1 = 0 → `4ada4`, 아니면 `4ada0`: D0.W := −(D0.W + D1.W). **`4ada4`**: D0.W += WORD `46(A6)`, SWAP D0, SWAP D1, BYTE `15(A6)` bit 0 = 0 → `4adba`, 아니면 `4adb6`: D0.W := −(D0.W + D1.W). **`4adba`**: D0.W += WORD `42(A6)`, A1 += `12`, D2 := LONG `(A1)+`.
- **`4adc4`**: D3 := LONG `(A1)+`, SWAP D2, SWAP D3, BYTE `15(A2)` bit 0 = 0 → `4add8`, 아니면 `4add4`: D2.W := −(D2.W + D3.W). **`4add8`**: D2.W += WORD `4a(A2)`, D2.W += D3.W, D2.W −= D0.W, D3.W += D1.W, (무부호) D2.W ≥ D3.W → `4ae32`, 아니면 `4ade8`: SWAP D0..D3, BYTE `15(A2)` bit 1 = 0 → `4adfe`, 아니면 `4adfa`: D2.W := −(D2.W + D3.W). **`4adfe`**: `4add8`과 같은 꼴(WORD `4e(A2)`), ≥ → `4ae2e`, 아니면 **`4ae0e`**(겹침): D2.W := LSR.W(ASR.W(D2.W, 1) + D0.W, 1), BYTE `5d(A2)` := D2.B, SWAP D0..D3, 같은 식으로 BYTE `5c(A2)`, `BRA 4abc0`.
- **`4ae2e`**: SWAP D0, SWAP D1(fall-through `4ae32`). **`4ae32`**: D2 := LONG `(A1)+`, D2.W ≠ `8000` → `4adc4`, 아니면 `4ae3a`: A1 := LONG `56(A2)`, D0 := LONG `(A3)+`, D0.W ≠ `8000` → `4ad94`, 아니면 `4ae48`.
- **`4abc0`**: A0 = 0 → `4ad6a RTS`, 아니면 `4abca`: D0.W := WORD `(A0)`, A1 := LONG `56(A2)`, D1.W := WORD `8(A1)`, BYTE `11(A1)` ≠ 1 → `4abe6`, 아니면 `4abde`: BYTE `5e(A2)` ≠ 0 → `4ad6a`, 아니면 `4abe6`.
- **`4abe6`**: D2 := 0, D3.W := WORD `a(A1)`, 그 bit 0을 밀어내며 ASR.W #1: 밀려난 bit = 0 → `4abf6`, 아니면 `4abf2`: D2.W += WORD `4(A0)`. **`4abf6`**/**`4ac00`**: 같은 꼴로 `4abfc`(+ WORD `6(A0)`)·`4ac06`(+ WORD `8(A0)`). **`4ac0a`**: D2.W = 0 → `4ac1e`, 아니면 `4ac10`: BYTE `10(A1)` = 0 → `4ac1e`, 아니면 `4ac18`: D2 := BYTE `10(A1)`(MOVEQ #0 + MOVE.B).
- **`4ac1e`**: A1 := LONG `c(A1)`, A1 = 0 → `4ac3a`, 아니면 `4ac2a`: D3.W := WORD `(A1 + sext(2·D0.W))`, = 0 → `4ad6a`, 아니면 `4ac36`: D2 := (D2.W × D3.W, 무부호 32 bit) ASR.L 8.
- **`4ac3a`**: (무부호) D1.W < WORD `5af2(A5)` → `4ac4a`, 아니면 `4ac42`: WORD `5af2` := D1.W, LONG `5af4` := A2. **`4ac4a`**: D3.B := BYTE `2(A0)`, (무부호) D3.B ≤ BYTE `5e(A2)` → `4acda`, 아니면 `4ac56`.
- **`4ac56`**: BYTE `5e(A2)` := D3.B, BYTE `17(A2)` ∨= 6, D4 := 0, D3.W := WORD `42(A2)` − WORD `4a(A6)`, D4.B := (bit 15 ? `ff` : 0), D4.W += D4.W, D3.W := WORD `46(A2)` − WORD `4e(A6)`, D4.B := (bit 15 ? `ff` : 0), D4.W := ASR.W(D4.W, 1) ∧ `c0`, BYTE `5f(A2)` := D4.B, 6 LONG 넣기, D0 := LONG `42(A6)` − LONG `4a(A6)` − LONG `42(A2)` + LONG `4a(A2)`, D1 := 같은 꼴(`46` `4e`), D0 += D0, D1 += D1, SWAP D0, SWAP D1, `JSR 44602`(복귀 `4acb4`).
- **`4acb4`**: D0 := LSR.L(D0, 4), D0.W ∧= `f`, BYTE `5f(A2)` ∨= D0.B, D0.B := BYTE `60(A6)` ∧ 3, D0.W := D0.W << 2, D1.B := BYTE `60(A2)` ∧ `f3`, D0.B ∨= D1.B, BYTE `60(A2)` := D0.B, 6 LONG 꺼내기(D0 D1 D2 D6 D7 A0).
- **`4acda`**: BYTE `61(A2)` bit 7 = 1 → `4ad6a`, **`4ace4`**: bit 6 = 1 → `4ad6a`. **`4acee`**: D3.W := WORD `54(A2)`, (무부호) < WORD `5b7c(A5)` → `4ad02`, 아니면 `4acfa`: WORD `5b7c` := D3.W, LONG `5b78` := A2. **`4ad02`**: (무부호) D3.W > WORD `5b82(A5)` → `4ad12`, 아니면 `4ad0a`: WORD `5b82` := D3.W, LONG `5b7e` := A2. **`4ad12`**: D2.W = 0 → `4ad6a`.
- **`4ad18`**: D3.W := WORD `54(A2)` − D2.W, (무부호) WORD `54` > D2.W → `4ad38`, 아니면 `4ad22`: BYTE `61(A2)` bit 7 := 1, BYTE `3(A0)` bit 0 = 1 → `4ad36`, 아니면 `4ad32`: `BSR 4bb52`(복귀 `4ad36`). **`4ad36`**: D3 := 0. **`4ad38`**: WORD `54(A2)` := D3.W, D1.B = 0 → `4ad6a`, **`4ad42`**: BYTE `60(A2)` bit 7 = 1 → `4ad6a`.
- **`4ad4a`**: 12 LONG 넣기(D1..D7, A0..A4), A0 := `48a3a` + sext(2·D0.W), D1.W := D0.W, D0.B := BYTE `60(A6)`, `JSR e625e`(FR6; 복귀 `4ad66`). **`4ad66`**: 12 LONG 꺼내기. **`4ad6a`**: `RTS`.
- [I] `4ad6c`는 N08 격자의 후보 표적 A2와 공격 객체 A6(사각형 목록 A0)의 겹침 판정, `4abc0`은 겹침의 피해 적용(공격 기록 A0의 피해 WORD `4/6/8`을 표적 판정 기록의 형태 bit `a`로 고르고 배율 표 `c`로 곱한 뒤 체력 WORD `54`에서 뺌, 0 이하면 `61` bit 7과 `4bb52`(파괴) [I], 점수 `48a3a` BCD를 `e625e`로 더함), `5af2` `5b7c` `5b82`는 가장 큰/작은 값 기록이다.

## 지면 탐색 `4c0f0`

- **`4c0f0`**: A7 −= 6, WORD `4(A7)` := 4, SWAP D0, D0.W := 0, LONG `(A7)` := D0, `JSR 4bce0`(복귀 `4c102`). **`4c102`**: `JSR 43e34`(복귀 `4c108`).
- **`4c108`**: WORD `42(A6)` − `20`의 bit 15 = 1 → `4c156`, 아니면 `4c112`: D0 := LONG `42(A6)`, D1 := LONG `46(A6)`, D3 := −LONG `(A7)`, A0 := 0, `JSR 46d72`(복귀 `4c128`). **`4c128`**(소비자): Clear → `4c14a`, Set → `4c12c`: (무부호) D6 ≥ LONG `(A7)` → `4c146`, 아니면 `4c132`: WORD `4(A7)` −= 1, 원래 WORD ≠ 0 → `4c146`, 아니면 `4c13a`: D0.W := WORD `42(A6)` + `a`, `BRA 4c1be`. **`4c146`**: `BRA 4c150`. **`4c14a`**: WORD `4(A7)` := 4. **`4c150`**: WORD `42(A6)` −= 5, `BRA 4c108`.
- **`4c156`**: `JSR 43e34`(복귀 `4c15c`). **`4c15c`**: WORD `4(A7)` := 4. **`4c162`**: WORD `42(A6)` − `120`의 bit 15 = 0 → `4c1b0`, 아니면 `4c16c`: `4c112`와 같음(복귀 `4c182`). **`4c182`**(소비자): Clear → `4c1a4`, Set → `4c186`: `4c12c`와 같은 꼴(`4c1a0` / `4c18c`), **`4c18c`**: `4c132`와 같은 꼴(`4c1a0` / `4c194`), **`4c194`**: D0.W := WORD `42(A6)` − `a`, `BRA 4c1be`. **`4c1a0`**: `BRA 4c1aa`. **`4c1a4`**: WORD `4(A7)` := 4. **`4c1aa`**: WORD `42(A6)` += 5, `BRA 4c162`.
- **`4c1b0`**: `JSR 43e34`(복귀 `4c1b6`). **`4c1b6`**: A7 += 6, C := 0, `RTS`.
- **`4c1be`**: A0 := LONG `3e(A6)`, D0.W −= WORD `(A0)`, SWAP D0, D0.W := 0, LONG `2e(A6)` := D0, `JSR 43e34`(복귀 `4c1d2`). **`4c1d2`**: `JSR 4c0b0`(N33/U12 쪽; 복귀 `4c1d6`). **`4c1d6`**: A7 += 6, C := 1, `RTS`.
- [I] `4c0f0`은 x(`42`)를 5씩 옮기며 지형 탐침 `46d72`로 높이 D6를 재는 지면 찾기다: 4번 연속 실패하면 그 x ± `a`에 내려놓고(`4c1be`, Set) 끝까지 못 찾으면 Clear.

## `e8b7e`/`e8b80`(C helper `e8b5a`의 꼬리)

- **`e8b7e`**: D2.W −= WORD `(A1)`(fall-through `e8b80`). **`e8b80`**: BYTE `4(A4)` bit 0 = 0 → `e8b92`, 아니면 `e8b8a`: D3.W += `100`, D3.W −= WORD `4(A1)`. **`e8b92`**: D0.W := D2.W, D1.W := D3.W, A0 := A6 + `2e`, `JSR 43e08`(복귀 `e8ba0`).
- **`e8ba0`**: A4 := LONG `5e26(A5)`, D0 := sext8(BYTE `5(A4)`)의 WORD를 상위로(MOVEQ #0; MOVE.B; EXT.W; SWAP; 하위 WORD 0), D1 := 같은 꼴(BYTE `6(A4)`), WORD `(A7)+` 꺼내기, = 0 → `e8bc2`, 아니면 `e8bbe`: D0 := −D0, D1 := −D1. **`e8bc2`**: LONG `36` := D0, LONG `3a` := D1, `JSR 4be34`(복귀 `e8bd0`). **`e8bd0`**: `JSR 43e38`(복귀 `e8bd6`).
- **`e8bd6`**: A4 := LONG `5e26(A5)`, D7 := BYTE `7(A4)`, D6 := 0, D7.B ≠ `b` → `e8c04`, 아니면 `e8bea`: `JSR 1a988`(FR6; 복귀 `e8bf0`). **`e8bf0`**: D0.W := −(D0.W − WORD `46(A6)`), bit 15 = 1 → `e8c00`, 아니면 `e8bfa`: `JSR 4c0f0`(복귀 `e8c00`). **`e8c00`**: D7.W := `b`. **`e8c04`**: LONG `36` := 0, LONG `3a` := 0, `RTS`.
- [F] `e8b80`은 밖 `e8b7a BEQ.W e8b80`의 대상이라 block 시작이다(결정 3). `e8b7e`는 `e8b7a`의 fall-through(관측된 TB 시작)이고 `e8b80`으로 이어진다.
- [I] 플레이어 슬롯(`5e26(A5)`)의 상대 위치에 객체를 두고 속도를 주는 C helper의 꼬리(`1d318`이 호출, 재분류 C)다.

## 객체 `cde42`(`cddee`의 `28ae` 자식), 표 handler `36118`

- **`cde42`**: A0 := A6 + `26`, WORD `20` := `e2`, LONG `22` := bank 창 LONG `200094`, D0.W := `100`, A0 := A6 + `26`, A1 := LONG `22`(다시 읽음), A1 := LONG `40(A1)`, `JSR 49f8c`(복귀 `cde6a`). **`cde6a`**: `BRA cde96`.
- **`cde96`**: `JSR 497a6`(복귀 `cde9c`). **`cde9c`**(소비자): Clear → `cdea0`: D0.W := `37a`, D1.B := 0, `JSR 8ebe`(복귀 `cdeae`), **`cdeae`**: `BRA cdec0`. Set → **`cdeb2`**: D0.W := `3ba`, D1.B := 0, `JSR 8ebe`(복귀 `cdec0`). **`cdec0`**: WORD `68` := `e0ed`, WORD `1e` := `e0ed`, LONG `(A6)` := `cded2`(들어감).
- **`cded2`**(설치 값): `JSR 43e34`(복귀 `cded8`). **`cded8`**: `JSR 49fc6`(복귀 `cdede`). **`cdede`**(소비자): Clear → `cdee8 RTS`, Set → `cdee2 JMP 2a00`.
- **`36118`**: `JSR 1aa3a`(U08; 복귀 `3611e`). **`3611e`**: D0 bit 2 = 0 → `36126 RTS`, 아니면 `36128`: A0 넣기, A0 := `3614a`, D0.W := `1e`, `JSR 28ae`(복귀 `3613a`). **`3613a`**: A1 := 꺼낸 LONG, WORD `2e(A0)` := WORD `(A1)+`, WORD `32(A0)` := WORD `(A1)+`, WORD `68(A0)` := WORD `(A1)+`, `RTS`(A0 = `28ae`가 돌려준 새 node).
- [I] `cde42`는 `497a6`(BYTE `10fd92`)로 두 anim(`37a`/`3ba`) 중 하나를 고르는 효과 객체, `36118`은 표 `4a55c`의 handler로 `1aa3a`의 결과 bit 2가 서면 자식 `3614a`를 만들고 위치·`68`을 넘긴다.

## 객체 `d2776..`(공용 꼬리 `d2f90`)

- **`d2776` `d2782` `d278e` `d279a`**: D0.W := `167`, A0 := `d2652` / `d265a` / `d2662` / `d266a`, `BRA d2f90`.
- **`d2f90`**: A0 넣기, D1 := 0, `JSR 8ebe`(복귀 `d2f9a`). **`d2f9a`**: A0 := 꺼낸 LONG, LONG `92` := LONG `(A0)+`, D0 := LONG `(A0)`, A0 := A6 + `26`, WORD `20` := `e2`, LONG `22` := bank 창 LONG `200094`, A0 := A6 + `26`, D1.W := 4·D0.W(WORD 안), A1 := bank 창 LONG `200094`(다시 읽음), A1 := LONG `(A1 + sext(D1.W))`, D0.W := `100`, `JSR 49f8c`(복귀 `d2fd2`). **`d2fd2`**: `JSR d3c2a`(복귀 `d2fd6`).
- **`d2fd6`**: LONG `3a` := `80000`, LONG `8e` := `ffffbbbc`, LONG `36` := `20000`, `JSR 49a58`(복귀 `d2ff4`). **`d2ff4`**: D1 := D0, D0 := LSR.L(SWAP D0, 1) ∧ `38000`, D1 bit 0 = 1 → `d300a`, 아니면 `d3008`: D0 := −D0. **`d300a`**: LONG `36` := D0, `JSR 49a58`(복귀 `d3014`). **`d3014`**: D0 := LSR.L(SWAP D0, 1) ∧ `78000`, LONG `3a` −= D0, (부호) WORD `3a` ≤ `fb` → `d3032`, 아니면 `d302c`: WORD `3a` := `fb`. **`d3032`**: (부호) LONG `8e` ≤ `fffff000` → `d3046`, 아니면 `d303e`: LONG `8e` := `fffff000`. **`d3046`**: BYTE `15` bit 3 := 1, LONG `56` := 0, BYTE `12` := `ff`, BYTE `13` := `ff`, LONG `(A6)` := `d3062`(들어감).
- **`d3062`**(설치 값): `JSR 4be34`(복귀 `d3068`). **`d3068`**: BYTE `15` bit 7 = 1 → `d3094`, 아니면 `d3072`: LONG `3a` += LONG `8e`, `JSR 49fc6`(복귀 `d3080`). **`d3080`**(소비자): Clear → `d3084`: A0 := LONG `92`, `JSR 1ab80`(복귀 `d308e`), Set → `d3094`. **`d308e`**(소비자): Clear → `d3092 RTS`, Set → `d3094 JMP 2a00`.
- [F] **ROM 자료**(원본 바이트): `d2652..d2672` = LONG 쌍 `000d261a 00000022`(`d2776`), `000d261a 00000023`(`d2782`), `000d261a 00000024`(`d278e`), `000d2622 00000025`(`d279a`): LONG `92(A6)` := 앞 LONG(`d3084`에서 `1ab80`의 A0), D0 := 뒤 LONG(bank 표 `200094`의 색인 WORD `22..25`). bank 표 읽기는 live bus다.
- [I] 파편 객체(표 `bbf1a`의 callback 중 하나): 소리 `167`, 색인별 anim, 난수 속도, 중력 `8e`; 화면 밖(`49fc6`)이나 착지(`1ab80` with LONG `92`)면 삭제.

## 객체 `cdd2e`(helper `cc5e8` `cc958`)

- **`cdd2e`**: `BSR cc5e8`(복귀 `cdd32`). **`cdd32`**: `BSR cc958`(복귀 `cdd36`). **`cdd36`**: `JSR 49fc6`(복귀 `cdd3c`). **`cdd3c`**(소비자): Clear → `cdd46`, Set → `cdd40 JMP 2a00`.
- **`cdd46`**: BYTE `61` bit 3 = 1 → `cdd70`, 아니면 `cdd50`: D0.B := BYTE `79`, = 0 → `cdd6c`, 아니면 `cdd58`: D0.B −= 1, ≠ 0 → `cdd68`, 아니면 `cdd5e`: BYTE `61` bit 3 := 1, D0.B := `1e`. **`cdd68`**: BYTE `79` := D0.B. **`cdd6c`**: `BRA cdd84`. **`cdd70`**: D0.B := BYTE `79`, ≠ 0 → `cdd7e`, 아니면 `cdd78 JMP 2a00`. **`cdd7e`**: D0.B −= 1, BYTE `79` := D0.B. **`cdd84`**: `RTS`.
- **`cc5e8`**: D0.W := WORD `42` + `20`, (무부호) ≥ `180` → `cc5e2 JMP 2a00`, 아니면 `cc5f6`: (무부호) WORD `46` < `e0` → `cc5e2`, 아니면 `cc5fe RTS`.
- **`cc958`**: BYTE `15` bit 7 = 0 → `cc9bc`, 아니면 `cc962`: LONG `64` += ASR.L(LONG `7e` − LONG `64`, 2), `JSR 4bfa4`(복귀 `cc976`). **`cc976`**: D5.W := `20` ∧ D6.W, = 0 → `cc986`, 아니면 `cc980`: BYTE `7a` := `ff`. **`cc986`**: D5.W := `100` ∧ D6.W, = 0 → `cc996`, 아니면 `cc990`: BYTE `7a` := `ff`. **`cc996`**: BYTE `15` bit 4 = 0 → `cc9b8`, 아니면 `cc9a0`: D0.B := BYTE `6e`, ≠ 5 → `cc9b8`, 아니면 `cc9ac`: BYTE `15` bit 7 := 0, BYTE `7c` := `ff`. **`cc9b8`**: `BRA cca38`.
- **`cc9bc`**: LONG `3a` += ASR.L(`fff40000` − LONG `3a`, 5), LONG `36` += ASR.L(LONG `7e` − LONG `36`, 5), LONG `64` := LONG `36`, BYTE `7c` ≠ 0 → `cca1c`, 아니면 `cc9e8`: BYTE `15` bit 4 = 0 → `cca04`, 아니면 `cc9f2`: BYTE `7a` = 0 → `cca04`, 아니면 `cc9fa`: `JSR 4be50`(복귀 `cca00`), **`cca00`**: `BRA cca0a`. **`cca04`**: `JSR 4be34`(복귀 `cca0a`). **`cca0a`**: D6 bit 5 = 0 → `cca18`, 아니면 `cca12`: BYTE `15` bit 4 := 1. **`cca18`**: `BRA cca38`.
- **`cca1c`**: A1 := A5 + `538e`, D0..D3 := LONG `2e` `32` `36` `3a`, A0 := LONG `3e`, `JSR 43eb8`(복귀 `cca2c`). **`cca2c`**: LONG `2e` `32` `36` `3a` `3e` := D0 D1 D2 D3 A1, `JSR 43ea4`(복귀 `cca38`). **`cca38`**: BYTE `78` := (BYTE `15` bit 7 ? `ff` : 0), `RTS`.
- [I] 목표 x(`7e`)로 다가가는 날아다니는 객체(화면 밖이면 삭제, 지형 bit `d6`로 착지 표시 `7a`·`15` bit 4).

## 객체 `3ad48`(B2E `3ac2c`의 `2986` 자식), 소리 helper `4356e`

- **`3ad48`**: WORD `20` := `122`, LONG `22` := bank 창 LONG `2000b4`, D0.W := 3, `JSR 49a84`(복귀 `3ad60`). **`3ad60`**: A1 := LONG `(3cd26 + sext(4·D0.W))`, D0.W := `100`, `JSR 49f8c`(복귀 `3ad78`). **`3ad78`**: D0.W := `db5`, D1.B := 0, `JSR 8ebe`(복귀 `3ad86`). **`3ad86`**: WORD `68` := `1001`, WORD `1e` := `1001`, `JSR 49a58`(복귀 `3ad98`). **`3ad98`**: D0.W := (D0.W ∧ `1f`) + `50`, D1.W := D0.W, D0 := `60000`, `JSR 443d2`(복귀 `3adae`). **`3adae`**: BYTE `15` bit 0 = 0 → `3adba`, 아니면 `3adb8`: D0 := −D0. **`3adba`**: LONG `36` := D0, LONG `3a` := D1, `JSR 49a58`(복귀 `3adc6`). **`3adc6`**: D0.B ∧= 2, BYTE `b6` := D0.B, LONG `(A6)` := `3add4`(들어감).
- **`3add4`**(설치 값): D0 := ASR.L(LONG `36`, 4), LONG `36` −= D0, LONG `3a` 넣기, LONG `36`(새 값) 넣기, `JSR 4be2c`(복귀 `3adec`). **`3adec`**: BYTE `15` bit 7 = 0 → `3ae04`, 아니면 `3adf6`: BYTE `b6` −= 1, 새 BYTE bit 7 = 0 → `3ae04`, 아니면 `3adfe JMP 2a00`.
- **`3ae04`**: D2, D3 := 꺼낸 LONG 둘, BYTE `15` bit 5 = 0 → `3ae68`, 아니면 `3ae12`: `JSR 49a58`(복귀 `3ae18`). **`3ae18`**(회전): D0.B := (D0.B ∧ `1c`) − `c`, D4.W := D4.W >> 8, D4.B += D0.B, D2 := ASR.L(D2, 1), D3 := ASR.L(D3, 1), A0 := `4411e`, A1 := `4419e`, D4.W += D4.W, D0 := D2, D1 := D3, D2 := ASR.L(D2, 8), D3 := ASR.L(D3, 8), D2 := S·D2.W, D3 := C·D3.W(S = sext WORD `(4411e + sext(D4.W))`, C = sext WORD `(4419e + sext(D4.W))`, 부호 있는 곱), D2 := ASR.L(D2 − D3, 8), D3 := D2, D2 := S·D2.W, D3 := −(C·D3.W), D0 := −(D0 − D2) + D2, D1 := −(D1 − D3) + D3, LONG `36` := D0, LONG `3a` := D1(fall-through `3ae68`).
- **`3ae68`**: `JSR 49fc6`(복귀 `3ae6e`). **`3ae6e`**: A0 := `3b73e`, `JSR 1ab80`(복귀 `3ae78`). **`3ae78`**(소비자): Clear → `3ae82 RTS`, Set → `3ae7c JMP 2a00`.
- **`4356e`**: D6.W := WORD `-7ff2(A5)`(= `10000e`), D7.W := WORD `5492(A5)` − D6.W + `c`, 더하기의 올림 = 1 → `4358a RTS`, 아니면 `43580`: WORD `5492` := D6.W, `JSR 3af8`(D0 = 호출자의 소리 번호; 복귀 `4358a`).
- [F] **ROM 자료**(원본 바이트): 표 `3cd26` = LONG `0003cd32 0003cd9c 0003ce06`(색인 0..2; [I] `49a84 #3`의 결과 범위), 그 뒤 `3cd32..`은 anim 자료다. `3b73e` = `fff80000 00100010 …`(`1ab80`의 A0, 화면 여유 사각형 [I]). WORD 표 `4411e` = `0000 0006 000d …`(sine [I]), `4419e` = `0100 0100 0100 00ff …`(cosine [I]). BCD 표 `48a3a` = `0100 0100 0500 0500 0100 …`. 표 밖 색인도 live bus로 읽는다(점프가 아니라 자료 읽기라 전사 대상이 아니다; 결정 2).
- [I] `3ad48`은 파편(난수 anim·속도, 감속 `36` −= `36`/16, 회전 bit 5면 sine 표로 속도 벡터 회전, 화면 밖이면 삭제), `4356e`는 같은 소리를 12 frame 안에 다시 내지 않는 throttle이다(frame 수 WORD `10000e`).

## 경계·routing 밖 출구

- [F] 이 단위 안에는 live 대상 호출·계산 점프·TRAP이 없다. 설치 쓰기는 모두 다음 PC로 들어간다.
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 14개: `36126` `3613a` `3ae82` `4358a` `4ad6a` `4ae48` `4c1b6` `4c1d6` `cc5fe` `cca38` `cdd84` `cdee8` `d3092` `e8c04`(그중 `3613a` `cca38` `e8c04` `4c1b6` `4c1d6`는 다른 명령 뒤의 RTS, `4c1b6`/`4c1d6`는 `ANDI`/`ORI CCR` 뒤).
- [F] **native 정지 규칙 주의**(V1): FR6 spec의 `first_unrouted`(`8c16 < pc <= 8ca6`, `16ed2 < pc <= 16eee` 내부, 정지 `2a00` `2a24`, 홀수 live 정지 PC 버림)를 그대로 쓴다. `JMP 2a00`는 routing된 출구다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR6 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0..A4 := 자연 node, LONG `56(A2)` `c(56(A2))` `3e(A6)` `92(A6)` `5e26(A5)` := 자연 node 또는 선언 RAM 기록, A5 field, 스택 WORD/LONG, PC).
- **IO pack 자연 node 상태(새 family `natural`)**: C 뒤 코드가 native로 실행된 IO run의 frame 시작 상태(`artifacts/animation_machine_io_native/states/<config>/<case>.pack.gz`, `observe_animation_machine_io.read_pack`)에서 callback LONG이 이 단위의 진입인 node를 찾아(work RAM 짝수 주소 전수 검색, 상수 목록으로 고정) 그 RAM·PVC·bank를 그대로 쓰고, 레지스터만 선언한다(D0..D4·A0..A4 = 그 frame 시작 값, A5 := `108000`, A6 := 그 node, A7 := `10ef00`(복귀 LONG = sentinel), PC := callback). 찾은 자연 node(scratch 검색 결과): `cded2`(P1/094 frame 393, node `102280`), `cdd2e`(boot-demo-0 frame 435, `1011a8`), `d3062`(boot-demo-0 frame 478..527, `101ad8` `101c60` `101de8` `101eac` `102034`), `3ad48`(538 `10126c`, 544 `101eac`, 552 `101d24`, …), `3add4`(539.. `10126c` 외). [I] 이 상태는 그 frame 첫 시점의 자연 node field·전역(A5)·RAM 기록이고, 실제 dispatcher가 그 node에 들어갈 때의 레지스터와 같은 frame 안의 앞선 node 변경은 반영하지 않는다(선언 레지스터). 같은 상태를 native와 C++가 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `1ab80` → `3ae78`(`3ae6e`)·`d308e`(`d3084`), `46d72` → `4c128`(`4c112`)·`4c182`(`4c16c`), `49fc6` → `cdd3c`(`cdd36`)·`cdede`(`cded8`)·`d3080`(`d3072`), `497a6` → `cde9c`(`cde96`). 두 C 값이 다 나오도록 hint를 둔다: `1ab80`(LONG `42`/`46`/`4a`/`4e`, BYTE `15`: 화면 안 Clear / 밖 Set — FR4/FR5와 같음), `49fc6`(LONG `26(A6)` = 0 → Set), `497a6`(BYTE `10fd92` = 0 → Set), `46d72`(WORD `42`/`46`: 지형 [U]). 단위 시험은 RAM·합성 자료만 읽고 PVC port를 쓰지 않는 생산자만 실제 사슬로 넣고(생성기가 두 C 값을 모두 만들어 낸 것), 나머지는 선언 C 행만 둔다(V1·실제 ROM 차분이 실제 사슬).
- node fixture: callback·설치 값(`3ad48` `3add4` `cde42` `cded2` `cdd2e` `d2776` `d2782` `d278e` `d279a` `d3062`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `4ad6c` `4abc0` `4c0f0` `cc5e8` `cc958` `4356e` `36118` `d2f90` `e8b7e` `e8b80`을 subroutine으로(복귀 LONG = sentinel, 스택 선언값 포함) 들어간다.
- 단위 시험(Unicorn 생성기, FR6 꼴): 시작 205개 × 들어오는 C 3가지, zero-step, 내부 PC 907개 정확한 오류, 경계 stop(출구 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), 그리고 빈틈 종류별 hint:
  - 부호·영 확장: `e8ba0` `EXT.W`(BYTE `7f`/`80`/`ff`, MOVEQ #0 뒤의 상위 쓰레기 없음 확인), `4ac18` `MOVEQ #0; MOVE.B`(D2 상위 쓰레기), `MOVEA.W #0,A0`(A0 상위 쓰레기), `ADDA.W D3,A0`(D0.W = `8000`·`ffff`·`4000`: 음수·WORD 넘침), `d2f9a` 색인 4·WORD(`ffff` → −4, `4001` → +4).
  - 음수 색인: `4ac2a`의 2·D0.W(D0.W = `ffff`/`8000`/`7fff`), `3ad60`의 4·D0.W(D0 상위 쓰레기, `ffff`), `d2f9a`의 4·D0.W.
  - MULU 상위 WORD: `4ac36`(D2·D3 상위 WORD 쓰레기, `ffff × ffff`, 곱의 bit 31 뒤 ASR.L 8), MULS: `3ae18`(D2/D3 = `7fff`/`8000`/−1 근처, 표 값 부호 경계).
  - 꺼낸 레지스터: `3ae04` D2/D3(넣은 값과 다른 값), `4acb4` 6 LONG·`4ad66` 12 LONG(꺼낸 A0가 다시 쓰이는 `4acda..4ad4a`), `3613a` A1, `d2f9a` A0, `e8ba0` WORD(0 / ≠ 0 / `8000`).
  - RAM 거울: node A6 = `1fe000`(거울 `10e000`), A2 = 거울 주소, A5 = `1f8000`.
  - bit 조합: `15(A6)` bit 0·1 4가지(`4ad94..4adb6`), `15(A2)` bit 0·1, `5744(A5)` bit 7, `a(A1)` 하위 3 bit 8가지, `61(A2)` bit 6·7, `3(A0)` bit 0, D6 bit 5·`20`·`100`(`cc976..cca0a`), BYTE `15` bit 4·7(`cc958`), `61` bit 3(`cdd46`), `15` bit 5·7(`3adec` `3ae04`).
  - 동점(같은 값): `4ac3a` BCS(D1.W = WORD `5af2`: 쓰기 block stop으로 구별), `4ac4a` BLS(같으면 `4acda`), `4acee` BCS·`4ad02` BHI(같으면 쓰기), `4ad18` BHI(WORD `54` = D2.W → `4ad22`), `4add8`/`4adfe` BCC(D2.W = D3.W → 안 겹침), `4c12c`/`4c186` BCC(D6 = LONG `(A7)`), `4c132`/`4c18c`(WORD 0 / 1), `4c108`/`4c162`(WORD `42` = `20`/`1f`/`120`/`11f`/`8020`), `cc5e8`(합 = `180`/`17f`, WORD 넘침 `ffe0`), `cc5f6`(`e0`/`df`), `d3014`(WORD `3a` = `fb`/`fc`/`8000`), `d3032`(LONG = `fffff000`/`fffff001`/`7fffffff`), `4356e`(D7 + `c`의 올림 경계 `fff4`/`fff3`), `3adf6`(BYTE `b6` = 0 → `ff`, `80`, 1), `cdd58`/`cdd7e` SUBQ.B(1 → 0, 0 → `ff`).
  - TST.W 대 TST.L 읽기 범위: `4ac0a TST.W D2`·`4ad12 TST.W D2`(D2 = `00010000`: TST.L이면 다르다), `4ad38 TST.B D1`(D1 = `100`), `4ac10 TST.B 10(A1)`·`cc9e0 TST.B 7c(A6)`·`d3068 BTST`·`e8bb8 TST.W (A7)+`를 bank 창 앞(A6 = `1fff8x` 등)에서 — 읽기 범위가 다르면 결과(성공/오류)가 달라진다(규칙, 정확한 오류 문자열).
  - 상위 레지스터 bit: `MOVE.W #imm,D0/D1`(`3ad48` `3ad60` `3ad78` `cdea0` `cdeb2` `d2776..` `d2fc8`), `MOVE.B #0,D1`, `ANDI.W #1f`/`ADDI.W #50`(`3ad98`), `ANDI.B #1c`/`SUBI.B #c`/`LSR.W #8`/`ADD.B`(`3ae18`), `SMI.B`/`ADD.W`/`ASR.W`/`ANDI.W #c0`(`4ac56`), `LSR.L #4`/`ANDI.W #f`/`LSL.W #2`/`OR.B`(`4acb4`), `SWAP`/`NEG.W`/`ADD.W`(`4ad94..4ae2e`), `SUB.W`/`ADDI.W`(`e8b7e` `e8b8a`), `MOVE.W #b,D7`, `SUBQ.B #1,D0`, `MOVE.B #1e,D0`.
  - 큰 값: `ASR.L` 부호(`3add4` LONG `36` = `80000000`/`7fffffff`/−1), `cc962`/`cc9bc` 차의 넘침(`7fffffff` − `80000000`), `d3072` LONG 더하기 넘침, `d3014` SUB.L 빌림, `4ac56`의 LONG 합 넘침, `4ae0e` ASR/ADD/LSR 경계.

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `tools/probe_scan_fr7.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_fr7.out` 444줄; 6자리 `0x0…` 꼴 0줄)으로 확인한 결과:
  - **옮길 것(이 단위가 옮김, 결정 5)**: `engine/tests/animation_machine_buffer_cue_test.cpp`의 "Unreached stop" 행(복귀 LONG `4abc0`, 옛 기대 `unsupported animation machine PC`) → work RAM `10fea0`; `engine/tests/animation_machine_screen_test.cpp`의 `state(0x4abc0)` 거부(옛 기대 `unsupported animation machine PC`) → work RAM `10fea2`. `animation_machine_fade_card_test.cpp`의 주석("4abc0 follows the U7 4aa88 range (no executor)")은 사실이 바뀌었으므로 고친다(검사 목록에는 `4abc0`이 없다).
  - **정렬할 표준 Python 검증기**: `tools/verify_animation_machine_buffer_cue.py`의 outside 탐침 `0x4abc0`(이제 FR7 시작: 실행됨 — input의 49c38과 같은 API-only control로 관찰된 결과만 받음)과 `0x4abc2`(이제 FR7 내부: `unsupported animation objects fr7 PC`). 각 항목에 옛 기대(`unsupported animation machine PC`)와 대체 단위 FR7을 적고, 거부 control은 work RAM PC로 둔다(이미 `10fe00` `10fefe`가 있음). 작업자 규칙의 실행 검증기 목록(`stage_entry` `area_clear` `stage_event` `stage_event_ops` `frame_helpers` `card_menu_close` `input` `scene_core` `scheduler` `objects_g1`)은 이 단위의 PC를 탐침으로 쓰지 않는다(검색 0줄).
  - 그대로 참인 것: 자기 범위 끝·밖 확인만 하는 것(`buffer_cue_test` ranges `4abc0`, `n33_test` RANGES 끝 `4c0f0`, `b2b_test` `ends[]`의 `3ad48`(`!in_ranges`만), `b2b.py` 범위 끝 `3ad48`, `observe_animation_machine_buffer_cue.py`·`verify_animation_machine_buffer_cue.py` `U7_RANGES`·routing 식, `inventory_stage_buffer_frame.py` WINDOWS), stop으로만 쓰는 것(N08 시험의 `4ad6c` 정지 203행 — 정지 검사가 routing보다 먼저다), 값·주석(B2E `3ad48` 자식 값, `u20_test`·`fr3`·`fr4`·`fr5`·`b4b` spec·생성기의 레지스터 값 `4c123` `4abcd` …, `b2c.py` 주석).
- [I] V1 spec 중 native 사슬이 이 단위의 PC(`4ad6c` `3ad48` `4abc0` 등)를 첫 routing 밖 PC로 멈추던 것(N08 계열·B2E `3ac2c`의 자식 등)은 더 진행한다(정지는 routing에서 계산되므로 spec 수정은 필요 없을 것으로 본다; 검증 작업자가 회귀로 확인하고 개수 변화를 적는다).
- [F] stage_event / stage_event_ops 검증기의 `CPP_PINS`(`animation_machine.cpp` `989b7951…`, `animation_machine_internal.h` `cef94f5c…`)는 이 단위의 공유 수정으로 맞지 않게 된다(FR1..FR6 관례대로 검증 단계에서 새 값으로 갱신; 메인 결정, 새 값은 "구현·검증 기록").

## 결정

1. **범위.** FR7 = 205 block(13 범위): 충돌 판정 `4ad6c`/`4abc0`(+ 지면 탐색 `4c0f0`), `e8b7e`/`e8b80`, 객체 `cde42`/`cded2`, handler `36118`, 객체 `d2776..`/`d2f90`/`d3062`, 객체 `cdd2e`(+ `cc5e8` `cc958`), 객체 `3ad48`/`3add4`(+ `4356e`). 계산 점프가 있는 `42d9c`/`42e68`과 `af990` 계열, `cdc24`, `d3500` 계열은 FR8·FR9에 남긴다.
2. **계산 점프·표.** 이 단위에 계산 점프가 없다(전사할 점프 표 0). 자료 표 `3cd26` `4411e` `4419e` `48a3a` `d2652..`와 bank 창 표는 live bus 읽기이고 표 밖 색인도 원본대로 읽는다. TRAP 자리 없음.
3. **범위 밖 분기 대상 `e8b80`.** routing 밖 C helper `e8b5a`의 `e8b7a BEQ.W e8b80`이 `e8b7e` block 중간으로 들어오므로 `e8b80`을 block 시작으로 둔다(`e8b7e`: `SUB.W (A1),D2` → fall-through `e8b80`). C helper가 routing될 때 그 실행부가 `e8b7e`/`e8b80` 두 진입을 쓴다(FR6 `4fce0`와 같은 문제를 미리 막음).
4. **carry 보존 목록.** 소비자 8개. `4c1b6`(Clear)·`4c1d6`(Set)은 자기 C를 정하고 RTS하며 읽는 곳이 없다. C를 넘기는 `RTS` 없음.
5. **숨은 탐침 이전.** `buffer_cue_test`의 복귀 LONG `4abc0` → `10fea0`, `screen_test`의 `4abc0` → `10fea2`(F4 단위 시험 경계 규칙), `fade_card_test` 주석 정정, `verify_animation_machine_buffer_cue.py`의 `4abc0`/`4abc2` 정렬(옛 기대 기록 + FR7 + work RAM control). stage_event / stage_event_ops `CPP_PINS` 갱신은 메인이 검증 단계에서 정한다.
6. **C 뒤 root의 검증.** 선언 상태(seed world + 선언 편집)에 더해 IO pack의 자연 node 상태(선언 레지스터)를 V1 family `natural`로 둔다(위 "seed·fixture"). IO 비교의 확인은 C·E 연결 뒤(계획 메인 결정).
7. **F4 범위 문서.** U38(`4b8e4..4c38c`)은 이 단위의 `4c0f0..4c1de`를 빼야 한다.
8. **정적으로 불가능한 분기.** 없을 것으로 본다(생성기·V1이 빠진 후속을 보고하면 그때 근거와 함께 `STATIC_IMPOSSIBLE`에 적는다).
9. **다음.** 이 단위 뒤 D 남은 실행 PC 124(모두 C 뒤): FR8(`42d9c`/`42e68` + 계산 점프 `42f9e`, `cdc24`, `cde..`, `4fcb8`(이미 FR6) 등)·FR9(`af990` 계열 계산 점프 7개, `d3500` 계열, `38e92`, `aea38` …).

## 미확인

- [U] node field 의미(`12` `13` `15` `1e` `20` `22` `26` `2e..3e` `42..4e` `54..61` `64` `68` `6e` `78` `79` `7a` `7c` `7e` `8e` `92` `b6`), A5 field(`538e` `5492` `5744` `5af2` `5af4` `5b78..5b82` `5e26`, `-7ff2`)의 뜻, 표 `3cd26` `4411e` `4419e` `48a3a` `d2652..`과 판정 기록(`56(A2)`)·공격 기록(A0)의 형식.
- [U] `46d72`(지형 탐침)의 C가 정해지는 조건과 `4c0f0`의 자연 실행(IO 관측에서 `4c0f0`은 실행되지 않았다: `e8bea`의 `5e26(A5)` BYTE `7` = `b`가 필요).
- [U] IO pack 자연 node 상태의 레지스터(선언)와 실제 dispatcher 진입 레지스터의 차이(결정 6의 [I]).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr7.cpp`(case label 205 = scratch `starts_fr7.txt`와 집합 일치; 공용 함수 `ofr7_btst`(BTST.B + BEQ), `ofr7_carry`, `ofr7_asr`(ASR.L), `ofr7_asr_word1`(ASR.W #1), `ofr7_muls`, `ofr7_le_long`(부호 LONG ≤), `ofr7_negadd`, `ofr7_mid`(`4ae0e`), `ofr7_span`(`4add8`/`4adfe`), `ofr7_shift_test`/`ofr7_add_damage`(`4abe6..4ac06`), `ofr7_probe`/`ofr7_height`/`ofr7_count`/`ofr7_reset`/`ofr7_step_x`/`ofr7_land`/`ofr7_frame_return`(`4c0f0` 틀), `ofr7_stub`(`d2776..`)), `engine/tests/animation_machine_objects_fr7_test.cpp`(생성 구역 + 수작성 규칙: `4356e` ADDI.W 올림 경계·WORD 레지스터, `4ac36` MULU·ASR.L 부호, `4ac3a`/`4ac4a`/`4acee`/`4ad02`/`4ad18`/`4add8` 동점(LONG A2 쓰기나 쓰기 block 정지로 구별), `4ac56` SMI/ADD.W/ASR.W/ANDI.W 네 조합과 6 LONG 넣기, `4ae0e` 중점(LSR.W 대 ASR.W를 D2 상위 WORD로 구별), `4ad4a` ADDA.W(`ffff` → `48a38`, `8000` → WORD 넘침)·12 LONG 넣기, `4c0f0` 틀, `4c108`/`4c162` BMI/BPL 경계, `4c12c` 무부호 동점, `4c132` 빌림, `4c194` SUBI.W, `4c150` SUBQ.W 넘침, `4c1b6`/`4c1d6` A7 += 6과 C, `4c1be`, `cc5e8`/`cc5f6` 무부호 경계와 WORD 넘침, `cca38` SNE, `d2ff4` SWAP/LSR/ANDI.L/NEG.L, `d3014` 부호 WORD BLE·SUB.L, `d3032` 부호 LONG BLE, `3adf6` BPL 넘침, `3ae04` MOVEM 순서, `3add4` ASR.L·넣는 순서, `e8ba0` EXT.W/SWAP/NEG.L과 꺼낸 WORD, `e8bf0`, `3613a`, `d2f9a` 색인(음수 포함), `3ad60` 색인(음수 포함)), `tools/generate_animation_machine_objects_fr7_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀, `atk`/`hit`/`pad`/`a2off`/`a2_mirror` hint 추가; 두 번 실행해 시험 파일 바이트 단위 같음 SHA256 `67e3d9cd459757de44c95984d317c3de124dd7d62806e2ec8586e39d4e418ddc`, 약 100초), `tools/unit_fixture_specs/fr7.py`(V1 spec; FR6 spec의 공용 부분(routing 해석, `first_unrouted`의 `8c16`/`16ed2` 내부 규칙, `block_next`, carry oracle, callee family) 그대로, 단위 부분 교체: 선언 기록 ATK `10fb00`·HIT `10fc00`·MULT `10fc80`·PAD `10fd80`·DREC `10fd40`(사각형 목록은 낮은 WORD `8000` LONG으로 끝), LONG `56(A2)` `5e26(A5)` `3e(A6)` `92(A6)`, 스택 선언(`4c0f0` 6 BYTE 틀, `4acb4` 6 LONG, `4ad66` 12 LONG, `3ae04`/`3adec`/`3adf6` 2 LONG, `3613a`/`d2f9a` 포인터, `e8b7e..e8ba0` WORD), 기하 hint `geo()`(겹침·맞닿음·뒤집기 bit), 사슬 8개, 오류 행 6 + 실행 뒤 실패 5, 새 family `natural`(IO pack 10 frame, 결정 6)). 공유 수정은 "공통 규칙"의 다섯 곳과 이전(결정 5)뿐이다.
- [F] 정적 spec 검사(scratch `spec_static.py`): `load_routing` 규칙 뒤 시작 205개와 내부 907개가 모두 `animation_objects_fr7_block`, sentinel은 routing 밖, routing 밖 정적 후속 0, 사슬 8개의 소비자가 진입에서 닿음, block 명령 합 575. 합성 기반 상태와 가짜 tracer로 world·hint·error·chain/node/callee/natural 생성 함수를 실행(scratch `spec_dry.py`): Python 오류 0, world 780, 오류 fixture 932개(내부 907 + 홀수 1 + Unknown C 8 + 홀수 node/stack/기록/틀 6 + 실행 뒤 실패 5 + failpc 짝 5) 이름 중복 0. `natural` family를 실제 native tracer로만 실행(scratch `spec_natural.py`, C++ 비교 아님): IO pack 10 frame에서 자연 node 26개(`3add4` 13, `d3062` 10, `cded2` `cdd2e` `3ad48` 1씩)가 모두 sentinel까지 정상 정지, 단위 시작 44개를 지남.
- [F] 단위 시험 world: A7 = `10ef00`, 합성 typed physical byte(ROM 자료 아님, 자료 영역만): bank 창 LONG `200094` → `2a3000`(그 표 `2a2ffc..2a30a4`, 색인 −1..40), `2000b4` → `2a5000`, LONG 표 `3cd22..3cd36`, WORD 표 `4411e..443a0`(난수 WORD 321개), `3b73e`(사각형 4 WORD), BCD 표 `48a38..48a48`, BYTE `e625c..e625d` = `01 23`, 기록 `d2652..d2672`. 생성기가 실제 생산자 사슬을 두 C 값 모두로 만들어 남긴 것 3개: `1ab80` → `3ae78`(`3ae6e`)·`d308e`(`d3084`), `497a6` → `cde9c`(`cde96`). `49fc6` → `cdd3c`·`cdede`·`d3080`은 PVC bank port를 써서, `46d72` → `4c128`·`4c182`는 합성 바이트 밖 ROM(지형)을 읽어 버려졌고 선언 C 행만 있다(V1·실제 ROM 차분이 실제 사슬). 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 출구 29개 + sentinel 모두 어떤 행의 stop.
- [F] `make -j3 all test`(작업자, scratch `make_all1.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 280개(FR6 279 + 1), Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR7 시험 줄: `animation machine objects fr7: 915 fixtures (696 single-block, 166 path, 18 producer chain, 16 declared C, 19 checked error (5 with a later failing PC), 36 kept C), 205 blocks, 4659 calls, 259107 checks`. 이전한 시험(buffer_cue `PASS 63 fixtures 71 phases 8 waits 831 API invocations`, screen `PASS 66`, fade_card `PASS 319`)은 개수 그대로다.
- [F] `dleft.py`(이 worktree routing `298c64da…`): 실행된 routing 밖 PC D 124 / E 220 / C 620, D 중 C 무관 0 / C 뒤 124, 예측 일치 165,714(변화 없음), 첫 정지 영역 C·E 15 / C 1.
- [F] buffer_cue 검증기 정렬의 근거(scratch `bufcue/probe4abc0.py`: 검증기 모듈의 API 기반 상태로 C++ harness만 실행): `4abc0` → A0 = 0이라 `4ad6a RTS` 뒤 기반 상태의 복귀 LONG으로 이어져 `animation machine external read queue empty`, `4abc2` → `unsupported animation objects fr7 PC`. 검증기 전체는 실행하지 않았다(검증 단계).
- [F] 검증 작업자 준비물(scratch, 결정적 실행기 `ms5-scratch/tools/verify_unit.py`용): `mut/run_mut.py`·`mut/mutants.py`(변이 292개; `--check`: 패턴 유일·문법 검사 통과(`patterns ok 292`), 2개 시험 실행 `killed 2 of 2` 뒤 산출물 삭제), `realrom/build.sh`·`realrom/run_all.sh`·`realrom/real_fr7.py`(FR6 harness에 FR7 world·소비자·진입; 선언 정지 FR4 BRA.W 표 항목 `cc7ac + 4k`/`cc82e + 4k`, `16ed6..16eee`/`8c16` 내부, `3c0000` MOVEM.W 쌍 병합; 시험 1회 40건 `mismatches 0` 뒤 산출물 삭제).
- [F] stage_event / stage_event_ops `CPP_PINS` 새 값(메인이 검증 단계에서 갱신): `animation_machine.cpp` `298c64da5f6ab9483acc7b1e39c0b733ea0908cb685c058621faa500ffbec51f`, `animation_machine_internal.h` `69b45dcd7444ae6411e238106b33c3f2f5098d10525e0ed93f78f21f237813fd`.

## block 목록

[F] scratch `starts_fr7.txt`(SHA256 `19883209598827a63fae8aecdb92d60a4e5caca3db36df5eb3b0789d536015b3`)와 같다.

- **`36118..3614a`(5)**: `36118 3611e 36126 36128 3613a`
- **`3ad48..3ae84`(21)**: `3ad48 3ad60 3ad78 3ad86 3ad98 3adae 3adb8 3adba 3adc6 3add4 3adec 3adf6 3adfe 3ae04 3ae12 3ae18 3ae68 3ae6e 3ae78 3ae7c 3ae82`
- **`4356e..4358c`(3)**: `4356e 43580 4358a`
- **`4abc0..4ae4a`(57)**: `4abc0 4abca 4abde 4abe6 4abf2 4abf6 4abfc 4ac00 4ac06 4ac0a 4ac10 4ac18 4ac1e 4ac2a 4ac36 4ac3a 4ac42 4ac4a 4ac56 4acb4 4acda 4ace4 4acee 4acfa 4ad02 4ad0a 4ad12 4ad18 4ad22 4ad32 4ad36 4ad38 4ad42 4ad4a 4ad66 4ad6a 4ad6c 4ad78 4ad7c 4ad82 4ad8e 4ad94 4ada0 4ada4 4adb6 4adba 4adc4 4add4 4add8 4ade8 4adfa 4adfe 4ae0e 4ae2e 4ae32 4ae3a 4ae48`
- **`4c0f0..4c1de`(27)**: `4c0f0 4c102 4c108 4c112 4c128 4c12c 4c132 4c13a 4c146 4c14a 4c150 4c156 4c15c 4c162 4c16c 4c182 4c186 4c18c 4c194 4c1a0 4c1a4 4c1aa 4c1b0 4c1b6 4c1be 4c1d2 4c1d6`
- **`cc5e2..cc600`(4)**: `cc5e2 cc5e8 cc5f6 cc5fe`
- **`cc958..cca44`(22)**: `cc958 cc962 cc976 cc980 cc986 cc990 cc996 cc9a0 cc9ac cc9b8 cc9bc cc9e8 cc9f2 cc9fa cca00 cca04 cca0a cca12 cca18 cca1c cca2c cca38`
- **`cdd2e..cdd86`(15)**: `cdd2e cdd32 cdd36 cdd3c cdd40 cdd46 cdd50 cdd58 cdd5e cdd68 cdd6c cdd70 cdd78 cdd7e cdd84`
- **`cde42..cde6e`(2)**: `cde42 cde6a`
- **`cde96..cdeea`(11)**: `cde96 cde9c cdea0 cdeae cdeb2 cdec0 cded2 cded8 cdede cdee2 cdee8`
- **`d2776..d27a6`(4)**: `d2776 d2782 d278e d279a`
- **`d2f90..d309a`(20)**: `d2f90 d2f9a d2fd2 d2fd6 d2ff4 d3008 d300a d3014 d302c d3032 d303e d3046 d3062 d3068 d3072 d3080 d3084 d308e d3092 d3094`
- **`e8b7e..e8c0e`(14)**: `e8b7e e8b80 e8b8a e8b92 e8ba0 e8bbe e8bc2 e8bd0 e8bd6 e8bea e8bf0 e8bfa e8c00 e8c04`

## 검증 기록(검증 실행: 결정적 runner + 메인 검토)

- [F] `make`: 종료 0, 경고 0, Assert 0, Python 310 OK. FR7 시험 `924 fixtures (705 single-block, 166 path, 18 producer chain, ...), 205 blocks`.
- [F] `ubsan`: 종료 0, runtime errors 0.
- [F] `mutation`: total 292, first run killed 283, hints 후 killed 286, equivalent 6.
  - `3adf6-bpl-word`: 1-byte store와 bit-7 test에서 BYTE store 앞의 WORD/BYTE mask는 관측되지 않는다.
  - `3ae18-d3-asr`: `ASR.L`/`LSR.L` `#8`은 bits `24..31`에서만 다르고, 뒤따르는 `MULS.W`는 low WORD만 읽고 `D3`를 덮어쓴다.
  - `3ae18-diff-logical`: 위와 같고, `(D2-D3)>>8`이 `MULS.W`에 입력되는 경우에도 동일하다.
  - `4ac56-asr-logical`: shift 전 `D4` low WORD는 최대 `01ff`이고 bit `15`가 0이므로 `ASR.W #1`과 `LSR.W #1`이 같다.
  - `4acb4-asr`: `LSR.L`/`ASR.L` `#4`는 `D0` upper bits에서만 다르고, low byte만 store되며 block 종료 전 `D0`가 popped(overwritten)된다.
  - `d2ff4-asr`: `SWAP` 후 `LSR.L #1`과 `ASR.L #1`은 bit `31`에서만 다르고, `ANDI #38000`에 의해 제거된다.
  - fixed gaps:
    - `4ac2a-unsigned`: hint `A1 = 44200`을 synthetic `4411e..4439e` window 안에서 `D0.W` `ffff`/`ffc0`/`ff90`으로 제공; work RAM에서는 64 KiB mirror가 zero-extended index를 숨긴다.
    - `4acb4-and3`: hint `BYTE 60(A6)=4/7`을 `BYTE 60(A2)` bit `4`가 clear된 상태로 제공; 뒤따르는 `OR` `f3`/`ff`가 차이를 숨겼다.
    - `4c108-signed-lt`: hint `WORD 42(A6)=8000/801f` 제공; `CMPI` 후 `BMI`는 overflow 시 signed compare와 다르다.
- [F] real-ROM: batches `s1`, `s2`, `s3`, `f4`, `f5` 각각 1500 cases, mismatches `0,0,0,0,0`, covered starts `205/205` in every batch.
- [F] V1: FR7 fixtures 1815, failed 0, runs 2, identical true; regression specs 30, all failed 0.
- [F] legacy verifiers: `stage_entry`, `area_clear`, `stage_event`, `stage_event_ops`, `frame_helpers`, `card_menu_close`, `input`, `scene_core`, `scheduler`, `objects_g1` 모두 pass.
- [F] frames: `d1` 54400/54400, mismatches 0; `controller_game` 54400/54400, 0; `irq` 54400/54400, 0; `demo` 45684/45684, 0.
- [F] IO: matched_total 165714, baseline 165714, delta 0, mismatches 0, cpp_errors 0, runs 2, identical true; per_config `P0` 81600, `P1` 75304, `P1b` 7424, `boot-demo-0` 381, `boot-title-idle` 600, `boot-title-start` 122; frontier `4e68e` `C` 15, `1d1f4` `C` 1. `FR7` 코드는 첫 `C` stop 이후에만 실행되므로 IO matched frames는 변하지 않는다.
- [F] area-D remaining PCs: before 262, after 124, all `C`-gated true.
- 검증 방법: deterministic runner `ms5-scratch/tools/verify_unit.py` (no LLM); mutant-gap drafting에 local Qwen을 사용했고 Claude가 검토했다.
