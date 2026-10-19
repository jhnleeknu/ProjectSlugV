# frontier 단위 FR3(FR2b 뒤 D 영역 IO frontier `c5370` `bc93c`와 그 자연 후속) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. FR2 계약(`animation-machine-frontier-fr2-contract.md`)과 FR2b 계약(`animation-machine-frontier-fr2b-contract.md`)의 구조·공통 규칙을 따르고 다른 점만 적는다. 메인 지시: FR2b 뒤 D 영역 frontier root `c5370`(12 run, frame 252), `5ab82`(root `5ab6c`, 3), `bc93c`(3), `50dae`(3) 중 영향이 큰 것을 약 220 block 안에 넣고, 넘치면 나눈다. D 영역 전체 계획은 `area-d-completion-plan.md`(같은 작업자)에 있다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 코드·고정 표는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기 `2000d0` `2000d4` `200090` `20003c` `200080` `200140`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `4bd282e`(branch `claude/frontier-units-3`, PR #8 head = FR2a/FR2b). routing 기준 `engine/src/animation_machine.cpp` SHA256 `4fc41a76a8ef697a93dd339af64a7deff8c62620c680d27015aad6bf2b2a3b40`(= FR2b IO 재실행 `frontier.json`의 `routing_file_sha256`), `animation_machine_internal.h` `142f253e7e8caa020620d97ea91eeac57907506c7323af4c9d006a8186c43d24`.
- [F] frontier 입력: FR2b 뒤 IO 재실행 `/Users/start/Workspce/ms5-scratch/fr2b/ioA/frontier.json`(SHA256 `2aeb3d7434511dad69bc08c26e9e4825139f457b4a0c738b77b862fe5a4b0bfd`; 첫 실패 전 일치 **158,202**, frontier run 39 = 확정 37 + guard fixture 2). 이 단위의 확정 frontier(모두 phase N, 복귀 `2ac2`):
  - `c5370`: P1 11 + P1b 1, frame 252, node callback LONG(A6) = `c5370`. [F] `c5370`은 ROM LONG 표 `e8fe0..`(`e9004`)의 한 항목이다(같은 표에 `c2e9a` `c3a58` `c528a` …; 표를 읽는 코드는 이미 routing된 객체 생성 경로 [I]).
  - `bc93c`: P1 2 + P1b 1, frame 276, LONG(A6) = `bc93c`(FR2b `bc934 MOVE.L #bc93c,(A6)`가 쓴 설치 값).
  - 나머지 D frontier `5ab82`(3, frame 141)·`50dae`(3, frame 271)는 이 단위 밖이다(결정 1).
- [F] **자연 후속 확인**(scratch `tools/dstate.py` `tools/dplan3.py` `tools/unit_fr3.py`, IO 관측 읽기 전용): `artifacts/animation_machine_io_native/runs/*/*.json.gz`의 frame별 `unr_new`(그 run에서 처음 실행된 routing 밖 TB 시작; 관측 당시 routing 기준)와 `N.cbs`를 현재 routing으로 다시 걸렀다. `P1/000`(c5370 run): frame 252 `c5370` → 253.. `c53ec`(설치 값) → 293 `76ff2` `7706a`(N15 `76f1e`·`76f3e` 계열의 `28ae` 자식, ROM LONG `76f30` `76f76`) → 294 `7703e` `77138` `77206` `ea69c` … → 374 `ea85a`(U18 `ea83a`의 설치 값, LONG `ea84e`) → 375 `ea8d2` → 419 `70d92`(FR2b `70d42`의 설치 값) → 420 `70dfc` → 496 `72f8a`(다음 frontier). `P1/022`(bc844 run): 276 `bc93c` → 277 `bc972` → 281 `bc9e0` → 282 `bca0e` → 301 `bc404`(FR1c `bc36c`의 `28ae` 자식, LONG `bc36e`) → 302 `bc464` → 309 `878dc`(다음 frontier).
- [F] 정적 디코드: capstone M68000, FR2b 계약과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, `MOVE.L #imm,(A6)` 설치 값 중 범위 안의 것, 범위 밖에서 들어오는 실제 분기 대상). routing된 PC, `RTS`, `TRAP`, `JMP`/`JSR (An)`에서 멈춘다. `28ae`/`2986` 자식 값은 기록만 한다. 진입 = 위 run들이 실제로 실행한 routing 밖 PC 150개(다른 진입의 closure 안에 이미 든 것은 뺌: `c5370` `76ff2` `7706a` `77206` `d1028` `ea85a` `70d92` `bc93c` `bc404`). 설치 값은 native가 실행한 것만 따라간다(결정 2). TB 시작이지만 block 시작이 아닌 PC `76ff8` `76ffe` `77002` `d0fee` `d0ff8`은 Unicorn TB 경계일 뿐 진입이 아니다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr3/`
  - `tools/`: FR2b scratch 도구의 경로만 바꾼 사본(`hroute.py` `fclos.py`(설치 값 추적 허용 집합 `install_ok` 추가) `dsm.py` `cread.py` `xref.py` …), 새 `dstate.py`(IO 관측 + 현재 routing), `dplan2.py` `dplan3.py`(D 계획), `unit_fr3.py`(이 단위 정의), `refidx.py`(정적 참조 색인), `probe_scan_fr3.py`(기존 시험의 범위 안 상수).
  - `starts_fr3.txt`(시작 197개) SHA256 `8497745968ea939dac031051aceb80f326dd5a4f50925c5d88a9f901b677a755`; `unit_fr3.out`(block별·범위 전체 디코드), `probe_fr3.out`.
  - 재현: `cd /Users/start/Workspce/metalslug-fu3 && .venv/bin/python /Users/start/Workspce/ms5-scratch/fr3/tools/unit_fr3.py B D`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **frontier root closure**(현재 routing, 같은 규칙, 실행된 설치 값만 따라감): `c5370` 33, `bc93c`(+ `bc972` `bc9e0` `bca0e`) 24, `5ab82`(+ `4464a`, `d1028..d10d8` 공유) 221, `50dae` 묶음(`50cf6` `50d08` `50dd2` `50e42` `51608`) 100. 네 root를 합치면 약 378이라 한 단위가 될 수 없다.
- [F] **고른 것(결정 1)**: 첫 정지 run 수가 가장 큰 `c5370`(12)과 그 run이 이어 실행하는 자연 후속 전부(frame 252 → 496: `76ff2` `7706a` `77206` 계열·`d0fec` 계산 helper·`ea69c`·`ea85a`·`70d92`), 그리고 `bc93c`(3)와 그 run의 자연 후속(276 → 309: `bc972` `bc9e0` `bca0e` `bc404` `bc464`). `d0fec`과 같은 helper 묶음인 `d1028..d10d8`(18 block, `5ab82` run에서만 실행)도 넣는다: FR5(`5ab82`)를 약 205 block으로 맞춘다.
- [F] **합 197 block**, 12 범위, 명령 480, 짝수 PC 1,012(내부 815), 이어 붙인 바이트 2,024, SHA256 `cf96af8aa55e33bb137759b1fe4a033348a8ffa24d5b95a7f9919e49dec5fb27`. 기존 routing과 겹침 0, 연속 Bcc 묶음 0, F4 범위 문서의 남은 단위 범위와 겹침 0(scratch 확인).
- [I] **예상 진척**(scratch `dplan3.py`, 상한 추정; IO 비교 재실행이 실제 측정값): `c5370` 12 run frame 252 → 496(`72f8a`, FR4), `bc93c` 3 run 276 → 309(`878dc`, FR4). 합 **+3,027 frame**(158,202 → 161,229). 나머지 frontier(`4e68e` 15, `5ab82` 3, `50dae` 3, `1d1f4` 1, fixture `2634` 2)는 그대로. 같은 예측 모형은 FR2b 기준 158,202를 정확히 재현한다.

| 묶음(진입) | block | 명령 | 범위 |
| --- | --- | --- | --- |
| `c5370`(+ 설치 `c53ec` `c564e`, `c561a`, 빈 helper `c579e`) | 33 | 67 | `c5370..c5432` `c561a..c5696` `c579e..c57a0` |
| `76ff2`(+ 설치 `7703e`) | 11 | 24 | `76ff2..7706a` |
| `7706a`(+ 설치 `77138`, `771e6`, helper `77284` `d0fec` `ea69c`) | 58 | 149 | `7706a..771de` `771e6..77206` `77284..772a0` `d0fec..d1028` `ea69c..ea6a2` `ea6b0..ea712` |
| `77206`(+ 설치 `77258`) | 12 | 25 | `77206..77284` |
| helper `d1028`(`d108a` `d10b4`) | 18 | 70 | `d1028..d10d8` |
| `ea85a`(+ 설치 `ea8d2`) | 19 | 41 | `ea85a..ea908` |
| `70d92`(+ 설치 `70dfc`) | 12 | 30 | `70d92..70e2a` |
| `bc93c`(+ 설치 `bc972` `bc9e0` `bca0e`) | 24 | 50 | `bc93c..bca2c` |
| `bc404`(+ 설치 `bc464`) | 10 | 24 | `bc404..bc47c` |
| 합 | **197** | 480 | 12 범위 |

## 요약

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `70d92..70e2a` | 152 | `8980bc978bcd6b1327aea41cf9047627fb46236e0d94d8c1fae53b03b93576a8` | 12 | 76 |
| `76ff2..771de` | 492 | `031ccd451a371b599a6c21b534624f7d590a3e09679f6176695132a9cddacc10` | 49 | 246 |
| `771e6..772a0` | 186 | `0f095bce88a311deab9c844427b53eedcbcf075458c827fd08b4c0fbc0301815` | 16 | 93 |
| `bc404..bc47c` | 120 | `ccefa772f148a9c936219f3fc22c5cb743f9beb5c99a4509d7899c3ea1a692a4` | 10 | 60 |
| `bc93c..bca2c` | 240 | `2f2d074cf5ef61fab390922a4ce12705d07bda6e64dcd413714878975774a5c4` | 24 | 120 |
| `c5370..c5432` | 194 | `9f94382b56a20f93cf8af3ac0c578bf5cedaa620eca29af36cd0e7c6ed95742c` | 18 | 97 |
| `c561a..c5696` | 124 | `3dbc0a1c584417298fdac6d978d549d80d5ca9b02fe0b7312990fa9a607e2bd7` | 14 | 62 |
| `c579e..c57a0` | 2 | `1ceeabf0c6a5a30bad12cdac0e3ab015a7188a42e6aebb556aad00bb9cd693ad` | 1 | 1 |
| `d0fec..d10d8` | 236 | `3f7d67f5e4dbaa2671a6cfde57c8a93aeff7766fb7d71738b7cb3402b6b1da83` | 25 | 118 |
| `ea69c..ea6a2` | 6 | `aaf131bd79bf2dc59e60c7e4bf326f3866b67fadce302c1092934b56c1e0f2a6` | 1 | 3 |
| `ea6b0..ea712` | 98 | `1b578f370298a37b50b15e6e21aa39715a453d1c7c20b4c2f0a03ff2bf172a98` | 8 | 49 |
| `ea85a..ea908` | 174 | `9de95e50bf3dfaf4efc0bc190868e24a0ef9a801a4ae734a85661b069f9fc1a8` | 19 | 87 |
| 합계 FR3 | 2024 | 이어 붙인 바이트 `cf96af8aa55e33bb137759b1fe4a033348a8ffa24d5b95a7f9919e49dec5fb27` | **197** | 1012(내부 815) |

- [F] closure가 12 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 범위 사이의 `771de..771e6`(`MOVE.L #771e6,(A6); RTS`, 분기로 닿지 않는 조각)과 `ea6a2..ea6b0`(형제 진입 `ea6a2` `ea6a8` `ea6ae`: `MOVEQ #1/#2/#3,D2; BRA.W ea6b0`, IO에서 실행되지 않음)은 범위 밖이다. X 소비 없음(`ADDX`/`SUBX` 없음). 계산 점프 없음. `JSR (An)` 없음. `TRAP` 없음. I/O port·bank 쓰기 없음. `DIVU.W` 3곳(`d1006` `d10c2` `d10cc`), `MULS.W` 5곳, `MULU.W` 2곳, `ASR.L #8`/`#4`/`#1`, `LSL.L #8`, `LSR.B #3`, `EXT.L`, `SWAP`, `MOVEM.W`/`MOVEM.L` 스택·메모리.
- [F] **경계 이웃**: routing된 것 `76ff0`(N15 끝) `bc402`(FR1c) `bc47c`(FR1c) `bc93a`(FR2b) `ea69a`(N35) `ea858`(U18) `ea908`(U18). 그 밖은 routing 밖 형제 코드·자료: `70e2a`(FR2b 정지 설치 값 `70e2a`의 코드), `771de`, `772a0..772de`(자료: `4ae4a` 표 `772a0`, 상자 `772be` `772c6`, `49f8c` 자료 `772ce`), `bca2c`(정지 설치 값), `c5432`(정지 설치 값), `c536e` `c5618` `c5696` `c579c` `c57a0`(다른 함수), `d0fea` `d10d8`(다른 함수), `ea6a2`, `ea712..`(LONG 표).
- [F] **나가는 곳은 모두 routing돼 있다**(각 실행부의 `case` block 시작): callee `28ae` `2986` `8ebe` `8ff4` `1ab02` `1ab80` `1abda` `43e08` `43e34` `43ea4` `443d2` `44602` `490ba` `491c4` `49290` `492d0` `496c2` `4970a` `49f8c` `49fc6` `4ae4a` `4b54e` `4be06` `4be2c` `4be34`(`77148 JSR`) `4bfa4` `4c0ac` `4c2cc` `76f98` `c6a96` `ea65a`(`ea6ca BSR.B`) `ea762`(`ea8de JSR`), 출구 `JMP 2a00`(`7704e` `77062` `7715c` `77186` `77268` `7727c` `bc474`), `JMP d1d08`(`771ec`), `BRA.W 72dd2`(`70e26`), `BEQ.W 71c90`(`70dfc`). 36곳(+ RTS 출구).
- [F] **참조**(ROM 전체 LONG 상수와 정적 발견 색인, scratch `refidx.py`): 범위 밖에서 들어오는 실제 진입은 모두 block 시작이다 — `c5370`(LONG 표 `e9004`), `76ff2` `7706a`(N15 `76f76` `76f30`의 `MOVEA.L #…,A0`), `77206`(이 단위 `771ba`), `d0fec`(N32b `39e0a JSR`, 이 단위 `7710e`), `d1028`(`5ac64 JSR`, 5ab82 함수), `ea69c`(이 단위 `7716a`, 밖 `2513a` `28fce` `75048` `78fe8` `7ad84` `7e2c0` `84436` `d44a6`), `ea85a`(U18 `ea84e` `eaa4e` 설치), `70d92`(FR2b `70d42` 설치), `bc93c`(FR2b `bc934`, 이 단위 `bca24` 쓰기), `bc404`(FR1c `bc36c`의 `28ae` 자식). 범위 안 다른 PC로 들어오는 밖의 분기는 없다.
- [I] 의미(이름은 확정하지 않는다): `c5370`은 객체 표 `e8fe0..`의 한 종류(`c6a96`(1f, 50), bank 창 `200080` LONG `140`의 애니메이션; WORD `76` ≠ 0이면 `c53a2` 이동형: LONG `86` = sext(WORD `76`) << 8, 위치 WORD `2e` > WORD `7a`이면 부호 반전, `c561a`에서 WORD `82` := WORD `7e`(수명)를 세며 `c564e` 갱신). 설치 `c53ec`/`c564e`: BYTE `15` bit 7로 `4be2c`/`4be06`, `49fc6`, `4b54e`(피격 판정 C) Set이면 BYTE `5e` := 0, 다음 상태 `c5432`/`c554c`(쓰기만). `7706a`는 N15 객체가 만드는 포물선 탄(`490ba`(표 `c88d4`)의 사거리 D0, `76f98`이 고른 목표 A0(Clear) 또는 자기(Set)와의 거리 WORD `42`/`46`, `d0fec`으로 초기 속도 LONG `36`/`3a` 계산, 가속 LONG `7e` = 0·`82` = `ffffac60`, 설치 `77138`: 속도 적분 → `4be34` → `1ab02`(상자 `772c6`) 화면 판정 → `ea69c`(착탄 효과 자식 `eaac0` 생성, `2986`) → `4ae4a`(지형 표 `772a0`) → `77284`(`44602` 각도) → BYTE `88` 회전 frame, BYTE `89` −= `38` 빌림마다 연기 자식 `77206`(`28ae`, `4970a`)). `76ff2`/`77206`은 효과 객체(bank 창 `200090`/`20003c`, `49fc6` 끝 → `2a00`, 상자 `772be` 화면 판정). `d0fec`은 (거리, 시간 D3, 중력 D2)로 속도를 푸는 고정소수점 계산, `d1028`은 `443d2`(삼각 표) 뒤 회전 행렬 곱과 `d108a`/`d10b4`(부호 처리 32/16 나눗셈). `ea85a`는 U18 객체의 설치 상태(`4c2cc` 지형 판정으로 표 `ea712`/`ea722`의 애니메이션 선택, 소리 `8ebe`(D0 = `1abda`의 D0/D1), `ea8d2`: BYTE `5e51(A5)`/`5e50(A5)` bit 7 소비 뒤 `49fc6` 끝이면 `ea908` 설치). `70d92`는 FR2b `70c0c` 계열의 착지 상태(bank `2000d0`/`2000d4` LONG `18`), `70dfc`: BYTE `15` bit 7 = 0이면 N15 `71c90`, 아니면 `4bfa4` `49fc6`, 끝이면 `492d0` 뒤 `70c0c` 설치. `bc93c`는 FR1c `bc08c`의 자식 `bc844`의 둘째 단계(부모 WORD `42`와 비교해 방향이 다르면 `bc9e0` 회전 애니메이션, 부모 BYTE `63`/`62`가 있으면 WORD `76` 세기 → `bcaa0`/`bca2c` 쓰기), `bc404`는 FR1c `bc36c`의 효과 자식(`49290` `491c4` 위치, bank `200080` LONG `38`).

## 공통 규칙·native 검증 계획

FR2 계약 "공통 규칙·native 검증 계획"과 FR2b 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr3.cpp`, 함수 `animation_objects_fr3_block`. 오류 문자열은 `unsupported animation objects fr3 PC`(범위 안 내부 PC 직접 진입), `objects fr3 caller requires known carry`(C 소비 block에 Unknown C; 소비자 17개), `objects fr3 DIVU zero divisor`(`DIVU.W`의 WORD 제수 0; 원본은 vector 5 예외를 타며 모형화하지 않음). 그 밖의 오류는 공용 bus/스택 오류다(`2986` 실패 경로의 caller-X 제한은 기존 checked 오류 그대로).
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(12 범위, FR2b 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(17개, "carry"), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** routing 밖 실행 PC는 없다(live 대상·TRAP 없음). 정지 설치 값 `bca2c` `bcaa0` `c5432` `c554c` `c5696`, 범위 안이지만 다음 PC가 아닌 설치 쓰기 `bc9e0`(`bc998` `bc9ac`) `bc93c`(`bca24`) `77138`(`77130`), 범위 밖 routing된 값 `70c0c`(`70e20`) `ea908`(`ea900`)은 `MOVE.L ...,(A6)`로 쓰기만 하고 실행하지 않는다(결정 2). 기존 시험이 stop으로만 보던 PC(`d0fec` `bc404` `bc93c` `7706a` `76ff2` `ea85a` `70d92`)는 stop 판정이 routing보다 먼저라 그대로 통과한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. dispatcher 오류 확인에 쓰는 범위 옆 PC는 자료 PC(`772a0` `ea712`)뿐이다; 다른 단위·다음 frontier가 routing할 코드(`70e2a` `771de` `bca2c` `c5432` `c5696` `d10d8` `ea6a2` `878dc` `72f8a` …)는 탐침으로 쓰지 않는다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): FR2와 같다. 행의 run stop은 실패 block 바로 뒤 PC다.
- **자료 읽기**(live bus, 상한 검사 없음): LONG `(ea712 + sext(4·WORD 76))`(`ea880`)·`(ea722 + sext(4·WORD 76))`(`ea8ae`), bank 창 LONG `2000d0` `2000d4`(LONG `18`) `200090`(`1c`) `20003c`(`14`) `200080`(`38` `140`) `200140`(`4` `8`)와 그 LONG `d(…)`. RAM 읽기: node field(A6), 부모 LONG `c(A6)`의 WORD `42`·BYTE `62` `63`(`bc97e..`), `76f98`이 돌려준 A0의 WORD `42` `46`(`770c2` `770f8`), BYTE `5e51(A5)` `5e50(A5)`(`ea8d2` `ea8e8`). 단위 시험은 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다, 자료 영역 `ea712..ea732`·`772be..772ce`와 bank `200000` 창 LONG과 그 뒤 LONG만; 코드 바이트와 겹치지 않음). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `MOVE.W D0,-(A7)`(`770b6`, `76f98` 호출 너머)와 `MOVE.W (A7)+,D2`(`770d6`); `MOVE.W D2,-(A7)`(`ea6b0`)과 `MOVE.W (A7)+,76(A0)`(`ea6fc`) / `ADDQ.W #2,A7`(`ea70a`); `MOVEM.L D0-D1/A0,-(A7)`(`ea6d0`: 낮은 주소부터 D0, D1, A0)과 `MOVEM.L (A7)+,D0-D1/A1`(`ea6ea`: **A1** := 넣은 A0); `MOVE.L D2,-(A7)`(`d0fec`)과 `MOVE.L (A7)+,D2`(`d101c`, N이 다음 `BPL`); `MOVEM.W D0-D1,-(A7)`(`d1028`: 낮은 주소 D0.W)와 `MOVEM.W (A7)+,D0-D1`(`d103a`: 두 WORD를 **부호 확장**해 LONG 전체에 씀); `MOVEM.L D2-D3,-(A7)`(`d1050`)과 `MOVEM.L (A7)+,D0-D1`(`d1080`: D0 := 넣은 D2, D1 := 넣은 D3); `MOVEM.L D0-D1,-(A7)`/`(A7)+,D0-D1`(`d108a`/`d10ae`); JSR/BSR 복귀 LONG. 홀수 A7은 checked 오류다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B`, `ADDQ.W` `SUBQ.W` `SUBI.B` `ADDI.W` `SUB.W` `NEG.W` `CLR.W` `CLR.B` `NOT.B` `LSR.B` `SMI.B` `SCS.B` `MOVE.B D3,D1`, `BCLR`/`BSET`/`BCHG`). `MOVEQ`는 LONG 전체(부호 확장). `MOVEA.W #0,A0`는 부호 확장(A0 = 0). `ADDQ.W #2,A7`은 A7 LONG 전체(+2). `LEA -2e(A0),A0`은 부호 확장 변위. `MOVEA.L (A1,D0.W),A1`은 sext 색인. `EXT.L`(WORD → LONG). `ASR.L #n`(32 bit 산술: 부호 bit 복제, 명시 구현), `LSL.L #8`(32 bit, 넘친 bit 버림), `LSR.B #3`(BYTE만). `MULS.W src,Dn`: 두 하위 WORD를 부호 확장해 곱한 32 bit(무부호 32 bit 산술로 계산, 곱은 32 bit 안). `MULU.W src,Dn`: 두 하위 WORD의 무부호 곱 32 bit(대상의 상위 WORD는 입력이 아니다). `DIVU.W src,Dn`: 제수 = src 하위 WORD(0이면 checked 오류), 몫 > `ffff`이면 V만 서고 Dn 그대로, 아니면 Dn = 나머지:몫. `SUB.L` `ADD.L` `NEG.L`(메모리 LONG 포함). 비교: `CMP.W`/`CMPI.W` + `BLE`/`BGE`(부호 있는 WORD), `CMPI.W #0` + `BNE`, `SUBQ.W #1` + `BCC`(옛 WORD ≠ 0), `SUBI.B #38` + `BCC`(무부호 옛 BYTE ≥ `38`), `TST.B`/`TST.W`/`TST.L` + `BEQ`/`BNE`/`BPL`, `MOVE.L` + `BEQ`/`BPL`(`7718c` `d0fec` `d101c`), `MOVE.W` + `BEQ`(`c538e`), `BCLR.B #7,d(A5)` + `BNE`(Z = 옛 bit). flag는 같은 block 안에서 만들고 소비한다(예외: "carry"의 callee C).

## carry

- [F] **소비 block 17개**(callee가 돌려준 C; Clear 쪽 / Set 쪽):
  - `49fc6`(interpreter known C): `70e12 BCC.W 70e26`(`70e26` / `70e16`), `7704a BCC.W 77054`(`77054` / `7704e`), `77264 BCC.W 7726e`(`7726e` / `77268`), `bc470 BCC.W bc47a`(`bc47a` / `bc474`), `bca1a BCC.W bca2a`(`bca2a` / `bca1e`), `ea8fc BCC.W ea906`(`ea906` / `ea900`; 진입 둘: `ea8f6 JSR 49fc6`의 복귀와 `ea8e8`의 `BNE.W ea8fc` — 그 경로의 C는 같은 block의 `ANDI.B #fe,CCR`이 정한 Clear이고 `BCLR`은 C를 바꾸지 않는다).
  - `1ab80`: `7705e BCC.W 77068`(`77068` / `77062`). `1ab02`: `77158 BCC.W 77162`(`77162` / `7715c`), `77278 BCC.W 77282`(`77282` / `7727c`).
  - N15 `76f98`(`76fc0`/`76fe6` ANDI Clear, `76fec JMP 4945e` → N08 known C): `770bc BCC.W 770c2`(`770c2` / `770c0`).
  - 이 단위 `ea69c`(`ea6fc` ORI Set / `ea70a` ANDI Clear): `77170 SCS.B 8a(A6)`(BYTE `8a` := `00` / `ff`, 다음 `77174`).
  - `28ae`(Set = 생성 성공): `771ca BCC.W 771dc`(`771dc` / `771ce`).
  - U18 `4b54e`: `c5412 BCC.W c5430`(`c5430` / `c5416`), `c5682 BCC.W c5694`(`c5694` / `c5686`).
  - U12 `1abda`(`1abea` CMPI 빌림 Set / `1abec` ANDI Clear): `ea6b8 BCC.W ea70a`(`ea70a` / `ea6bc`).
  - `ea65a`(routing된 U47/N35 쪽 known C): `ea6cc BCC.W ea70a`(`ea70a` / `ea6d0`).
  - FR2b `4c2cc`(`4c2ec` 통과 Clear / `4c2ee` Set): `ea86e BCC.W ea89e`(`ea89e` / `ea872`).
- [F] **C를 넘기는 `RTS`: 없음.** [F] 이 단위의 subroutine `d0fec` `d1028` `d108a` `d10b4` `77284` `c579e`의 직접 호출자는 복귀 뒤 C를 읽지 않는다(scratch `cread.py`: 0곳). `ea69c`의 호출자 9곳(이 단위 `7716a`, 밖 `2513a` `75048` `78fe8` `7ad84` `7e2c0` `84436` `d44a6`, 그리고 `28fce` LONG)은 `SCS`로 읽지만 C는 `ea6fc`/`ea70a`가 자기 block에서 정한다.
- [F] **known C 생산**: `ea6fc`(`…; ORI.B #1,CCR; RTS` Set), `ea70a`(`ADDQ.W #2,A7; ANDI.B #fe,CCR; RTS` Clear), `ea8e8`(`ANDI.B #fe,CCR; BCLR …; BNE`: 두 출구 모두 Clear), `771d8`(`ORI.B #1,CCR`, 다음 `771dc RTS`에서 Unknown이 됨: 읽는 곳 없음). 그 밖의 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다(`SUBI`/`SUBQ`+`BCC`는 같은 block 안에서 소비).
- [F] **읽는 곳이 없는 known C**(carry 보존 목록에 넣지 않음): `771d8`/`771dc`(node callback `77138`의 `RTS`: dispatcher 복귀 `2ac2`), `d1024`(`SUB.L; RTS`), `d10ba`(`TST.L` 뒤 `RTS`), `d1088`(`LSL.L` 뒤 `RTS`), node callback의 `RTS`(`77068` `77282` `bc47a` `bc9de` `bca2a` `c5430` `c5694` `ea906`).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 17개다: `70e12` `7704a` `7705e` `770bc` `77158` `77170` `771ca` `77264` `77278` `bc470` `bca1a` `c5412` `c5682` `ea6b8` `ea6cc` `ea86e` `ea8fc`. Unknown C로 소비자에 들어오면 checked 오류다.
- [F] flag 재계산(block 경계를 건너 다시 계산하는 flag)은 없다.

## 객체 `c5370`(+ `c53ec` `c561a` `c564e` `c579e`)

- **`c5370`**(표 `e9004` 값): WORD `54` := `64`, D0.W := `1f`, D1.W := `50`, D2.B := 0, `JSR c6a96`(복귀 `c5388`). **`c5388`**: `JSR 4c0ac`(복귀 `c538e`). **`c538e`**: WORD `68` `1e` := 0, D0.W := WORD `76`, 0 → `c53be`, 아니면 `c53a2`.
- **`c53a2`**: D0 := sext(D0.W) << 8(`EXT.L; LSL.L #8`), LONG `86` := D0, D0.W := WORD `2e`, (부호) D0.W ≤ WORD `7a` → `c53ba`, 아니면 `c53b6`: LONG `86` := −LONG `86`. **`c53ba`**: `BRA.W c561a`.
- **`c53be`** / **`c561a`**: (`c561a`만 먼저 WORD `82` := WORD `7e`) anim(`ba`, `200080`, `140`)(복귀 `c53e6` / `c5648`; FR2 "공통 꼴": LEA 26(A6),A0; WORD `20` := n; LONG `22` := LONG(창); D0.W := `100`; A1 := LONG(LONG `22` + d); `JSR 49f8c`). **`c53e6`** / **`c5648`**: 설치 `c53ec` / `c564e`(다음 PC라 들어감).
- **`c53ec`** / **`c564e`**(설치 값): BYTE `15` bit 7 ≠ 0 → `c5400` / `c5662`(`JSR 4be06`), 아니면 `c53f6` / `c5658`(`JSR 4be2c`, 복귀 `c53fc` / `c565e`: `BRA.W c5406` / `c5668`). 복귀 `c5406` / `c5668`: `JSR 49fc6`(복귀 `c540c` / `c566e`).
- **`c540c`**: `JSR 4b54e`(복귀 `c5412`). **`c5412`**(소비자): Clear → `c5430 RTS`, Set → `c5416`: BYTE `5e` := 0, LONG `(A6)` := `c5432`(쓰기만), BYTE `61` bit 7 = 0 → `c5430`, 아니면 `c542a`: LONG `(A6)` := `c554c`(쓰기만; fall-through `c5430`).
- **`c566e`**: WORD `82` −= 1, 옛 WORD ≠ 0 → `c567c`, 아니면 `c5676`: LONG `(A6)` := `c5696`(쓰기만; fall-through `c567c`). **`c567c`**: `JSR 4b54e`(복귀 `c5682`). **`c5682`**(소비자): Clear → `c5694 RTS`, Set → `c5686`: BYTE `5e` := 0, `BSR.W c579e`(복귀 `c568e`). **`c579e`**: `RTS`. **`c568e`**: LONG `(A6)` := `c554c`(쓰기만; fall-through `c5694 RTS`).

## 객체 `76ff2`, `7706a`(+ `77138` `77284` `d0fec` `ea69c`), `77206`

- **`76ff2`**(N15 `28ae` 자식 값): WORD `68` `1e` := `8820`, D0.W := `23`, D1.W := 7, D2.B := 0, `JSR c6a96`(복귀 `77010`). **`77010`**: anim(`da`, `200090`, `1c`)(복귀 `77038`). **`77038`**: 설치 `7703e`.
- **`7703e`**(설치 값): `JSR 43e34`(복귀 `77044`). **`77044`**: `JSR 49fc6`(복귀 `7704a`). **`7704a`**(소비자): Clear → `77054`, Set → `7704e JMP 2a00`. **`77054`**: A0 := `772be`, `JSR 1ab80`(복귀 `7705e`). **`7705e`**(소비자): Clear → `77068 RTS`, Set → `77062 JMP 2a00`.
- **`7706a`**(N15 `28ae` 자식 값): WORD `68` `1e` := `e0ef`, D0.W := `23`, D1.W := `35`, D2.B := 0, `JSR c6a96`(복귀 `77088`). **`77088`**: WORD `20` := `da`, A1 := `772ce`, D0.W := `100`, `JSR 49f8c`(복귀 `7709e`). **`7709e`**: BYTE `15` bit 3 := 1, `JSR 43e34`(복귀 `770aa`). **`770aa`**: A0 := `c88d4`, `JSR 490ba`(복귀 `770b6`). **`770b6`**: WORD D0 넣기(A7 −2), `JSR 76f98`(복귀 `770bc`). **`770bc`**(소비자): Clear → `770c2`, Set → `770c0`: A0 := A6.
- **`770c2`**: D0.W := WORD `42(A0)` − WORD `42(A6)`, BYTE `15` bit 0 ≠ 0 → `770d6`, 아니면 `770d4`: D0.W := −D0.W. **`770d6`**: D2.W := 꺼낸 WORD(A7 +2), (부호) D0.W ≤ D2.W → `770e0`, 아니면 `770de`: D0.W := D2.W. **`770e0`**: (부호) D0.W ≥ `40` → `770ec`, 아니면 `770e8`: D0.W := `40`. **`770ec`**: BYTE `15` bit 0 ≠ 0 → `770f8`, 아니면 `770f6`: D0.W := −D0.W.
- **`770f8`**: D1.W := WORD `46(A0)` + `10` − WORD `46(A6)`, D2 := `ffffac60`, D3.W := WORD `7a`, `JSR d0fec`(복귀 `77114`). **`77114`**: LONG `36` := D0, LONG `3a` := D1(`MOVEM.L`), LONG `7e` := 0, LONG `82` := D2, BYTE `89` := 0, BYTE `15` bit 0 := 0, LONG `(A6)` := `77138`(쓰기만), `RTS`.
- **`77138`**(설치 값): LONG `36` += LONG `7e`, LONG `3a` += LONG `82`(D0 = 마지막에 더한 값), `JSR 4be34`(복귀 `7714e`). **`7714e`**: A0 := `772c6`, `JSR 1ab02`(복귀 `77158`). **`77158`**(소비자): Clear → `77162`, Set → `7715c JMP 2a00`. **`77162`**: BYTE `8a` ≠ 0 → `77174`, 아니면 `7716a`: `JSR ea69c`(복귀 `77170`). **`77170`**(소비자): BYTE `8a` := C ? `ff` : `00`(fall-through `77174`).
- **`77174`**: BYTE `15` bit 5 = 0 → `7718c`, 아니면 `7717e`: BYTE `8a` = 0 → `771e6`, 아니면 `77186 JMP 2a00`. **`7718c`**: A0 := `772a0`, D0 := A0, D0 = 0 → `7719e`, 아니면 `77196`: A0 := D0, `JSR 4ae4a`(복귀 `7719e`). [F] `7718c`의 `BEQ`는 상수 A0 = `772a0` ≠ 0이라 정적으로 갈 수 없다(실행부는 일반 규칙대로 둔다). **`7719e`**: D0.W ≠ 0 → `771e6`, 아니면 `771a6`: `JSR 77284`(복귀 `771aa`). **`771aa`**: `JSR 49fc6`(복귀 `771b0`).
- **`771b0`**: BYTE `89` −= `38`, 무부호 옛 BYTE ≥ `38`(빌림 없음) → `771dc RTS`, 아니면 `771ba`: A0 := `77206`, D0.W := `14`, `JSR 28ae`(복귀 `771ca`). **`771ca`**(소비자): Clear → `771dc`, Set → `771ce`: D0.W := 0, D1.W := 0, `JSR 4970a`(복귀 `771d8`). **`771d8`**: C Set(fall-through `771dc`). **`771dc`**: `RTS`.
- **`771e6`**: `JSR 8ff4`(복귀 `771ec`). **`771ec`**: WORD `68` `1e` := `1001`, LONG `56` := 0, `JMP d1d08`.
- **`77284`**: D0 := LONG `36`, D1 := LONG `3a`(`MOVEM.L`), D0 := ASR.L 12 (= `ASR #8` 뒤 `ASR #4`), D1 := ASR.L 12, `JSR 44602`(복귀 `77298`). **`77298`**: D0.B := D0.B >> 3(무부호), BYTE `88` := D0.B, `RTS`.
- **`77206`**(`771ba`의 `28ae` 자식 값): `JSR 496c2`(복귀 `7720c`). **`7720c`**: WORD `68` `1e` := `1001`, D0.W := `e`, D1.W := 5, D2.B := 0, `JSR c6a96`(복귀 `7722a`). **`7722a`**: anim(`32`, `20003c`, `14`)(복귀 `77252`). **`77252`**: 설치 `77258`. **`77258`**: `JSR 43ea4`(복귀 `7725e`). **`7725e`**: `JSR 49fc6`(복귀 `77264`). **`77264`**(소비자): Clear → `7726e`, Set → `77268 JMP 2a00`. **`7726e`**: A0 := `772be`, `JSR 1ab02`(복귀 `77278`). **`77278`**(소비자): Clear → `77282 RTS`, Set → `7727c JMP 2a00`.
- **`ea69c`**: D2 := 0(`MOVEQ`), `BRA.W ea6b0`. **`ea6b0`**: WORD D2 넣기, `JSR 1abda`(복귀 `ea6b8`). **`ea6b8`**(소비자): Clear → `ea70a`, Set → `ea6bc`: D0 := LONG `42`, D1 := LONG `46`, A0 := 0(`MOVEA.W`), D7 := 2, `BSR.B ea65a`(복귀 `ea6cc`). **`ea6cc`**(소비자): Clear → `ea70a`, Set → `ea6d0`: D0, D1, A0 넣기(`MOVEM.L`), A0 := `eaac0`, D0.W := `1e`, A1 := `100bf4`, `JSR 2986`(복귀 `ea6ea`). **`ea6ea`**: D0, D1, **A1** := 꺼낸 LONG 세 개, SWAP D0, SWAP D1, A0 += `2e`, `JSR 43e08`(복귀 `ea6fc`). **`ea6fc`**: A0 −= `2e`(`LEA -2e(A0)`), WORD `76(A0)` := 꺼낸 WORD, C Set, `RTS`. **`ea70a`**: A7 += 2, C Clear, `RTS`.
- **`d0fec`**: LONG D2 넣기, D2의 N = 0 → `d0ff4`, 아니면 `d0ff2`: D2 := −D2. **`d0ff4`**: (부호) D3.W ≥ 2 → `d1000`, 아니면 `d0ffc`: D3.W := 2. **`d1000`**: D4 := `10000`, `DIVU.W D3,D4`, D0 := MULS(D4.W, D0.W), D1 := MULS(D4.W, D1.W), D5.W := D3.W, D3 := MULU(D2.W, D3.W), SWAP D2, D5 := MULU(D2.W, D5.W), SWAP D5, D5.W := 0, D3 += D5, D3 := ASR.L 1, D2 := 꺼낸 LONG, D2의 N = 0 → `d1024`, 아니면 `d1022`: D3 := −D3. **`d1024`**: D1 −= D3, `RTS`.
- **`d1028`**: WORD D1, WORD D0 넣기(`MOVEM.W D0-D1,-(A7)`), D0 := D2, D1.B := D3.B, `JSR 443d2`(복귀 `d1036`). **`d1036`**: D2 := D0, D3 := D1, D0 := sext(꺼낸 WORD), D1 := sext(꺼낸 WORD), D2 := ASR.L 8, D3 := ASR.L 8, D0.W ≠ 0 → `d104c`, 아니면 `d1048`: D0.W := 1. **`d104c`**: D2 := sext(D2.W), D3 := sext(D3.W), D3, D2 넣기(`MOVEM.L D2-D3,-(A7)`), D4 := MULS(D2.W, D2.W), D7 := D4, `BSR.W d108a`(복귀 `d105e`). **`d105e`**: D4 := −ASR.L(D7, 1), D5 := MULS(D1.W, D2.W), D7 := D5, `BSR.W d108a`(복귀 `d106e`). **`d106e`**: D5 := ASR.L(D7, 1) − D3, D5 := MULS(D2.W, D5.W), D7 := D5, `BSR.W d108a`(복귀 `d107c`). **`d107c`**: D2 := D4, D3 := D7, D0, D1 := 꺼낸 LONG 두 개, D0 <<= 8, D1 <<= 8(`LSL.L`), `RTS`.
- **`d108a`**: D1, D0 넣기, D1.B := (D0의 N) ? `ff` : 0(`SMI`), D0의 N = 0 → `d1098`, 아니면 `d1096`: D0 := −D0. **`d1098`**: D7의 N = 0 → `d10a2`, 아니면 `d109e`: D7 := −D7, D1.B := ~D1.B. **`d10a2`**: `BSR.W d10b4`(복귀 `d10a6`). **`d10a6`**: D1.B = 0 → `d10ae`, 아니면 `d10ac`: D7 := −D7. **`d10ae`**: D0, D1 := 꺼낸 LONG 두 개, `RTS`.
- **`d10b4`**: D0 ≠ 0(LONG) → `d10bc`, 아니면 `d10ba RTS`. **`d10bc`**: D6 := D7 >> 16(`CLR.W; SWAP`), `DIVU.W D0,D6`, SWAP D6, SWAP D7, D7.W := D6.W, SWAP D7, `DIVU.W D0,D7`, SWAP D6, SWAP D7, D7.W := D6.W, SWAP D7, `RTS`(D7 = 32 bit 몫, D6 상위 = 마지막 나머지 [I]; 제수는 D0의 **하위 WORD**: D0 ≠ 0이어도 D0.W = 0이면 checked 오류).

## 객체 `ea85a`(+ `ea8d2`), `70d92`(+ `70dfc`)

- **`ea85a`**(U18 설치 값): `JSR 8ff4`(복귀 `ea860`). **`ea860`**: WORD `32` += 1, D0.W := `ffe0`, `JSR 4c2cc`(복귀 `ea86e`). **`ea86e`**(소비자): Clear → `ea89e`, Set → `ea872`.
- **`ea872`** / **`ea89e`**: `JSR 1abda`(복귀 `ea878` / `ea8a4`). **`ea878`**: D1 := 0(`MOVEQ`), `JSR 8ebe`(복귀 `ea880`). **`ea8a4`**: D0.W := D1.W, D1 := 0, `JSR 8ebe`(복귀 `ea8ae`).
- **`ea880`** / **`ea8ae`**: A1 := LONG `(ea712 / ea722 + sext(4·WORD 76))`(`ADD.W D0,D0` 두 번: WORD 안에서 넘침), D0.W := `100`, `JSR 49f8c`(복귀 `ea89a` / `ea8c8`). **`ea89a`**: `BRA.W ea8c8`.
- **`ea8c8`**: WORD `32` −= 1, 설치 `ea8d2`(다음 PC라 들어감). **`ea8d2`**(설치 값): BYTE `5e51(A5)` bit 7 := 0, 옛 bit = 1 → `ea8e2`, 아니면 `ea8dc`: D7 := 8, `JSR ea762`(복귀 `ea8e2`). **`ea8e2`**: `JSR 43e34`(복귀 `ea8e8`). **`ea8e8`**: C Clear, BYTE `5e50(A5)` bit 7 := 0, 옛 bit = 1 → `ea8fc`(C Clear), 아니면 `ea8f6`: `JSR 49fc6`(복귀 `ea8fc`). **`ea8fc`**(소비자): Clear → `ea906 RTS`, Set → `ea900`: LONG `(A6)` := `ea908`(쓰기만; fall-through `ea906`).
- **`70d92`**(FR2b `70d42`의 설치 값): WORD `9c` ≠ 0 → `70dc6`, 아니면 `70d9a`. **`70d9a`** / **`70dc6`**: anim(3, `2000d0`, `18`) / anim(`b`, `2000d4`, `18`)(복귀 `70dc2` / `70dee`). **`70dc2`**: `BRA.W 70dee`. **`70dee`**: LONG `64` := 0, 설치 `70dfc`.
- **`70dfc`**(설치 값): BYTE `15` bit 7 = 0 → `71c90`(N15), 아니면 `70e06`: `JSR 4bfa4`(복귀 `70e0c`). **`70e0c`**: `JSR 49fc6`(복귀 `70e12`). **`70e12`**(소비자): Clear → `70e26`, Set → `70e16`: A0 := A6 + `26`, `JSR 492d0`(복귀 `70e20`). **`70e20`**: LONG `(A6)` := `70c0c`(쓰기만; fall-through `70e26`). **`70e26`**: `BRA.W 72dd2`.

## 객체 `bc93c`(+ `bc972` `bc9e0` `bca0e`), `bc404`(+ `bc464`)

- **`bc93c`**(FR2b `bc934`·이 단위 `bca24`가 쓰는 설치 값): D0.W := 8, WORD `76` := D0.W, anim(`e3`, `200140`, 4)(복귀 `bc96c`). **`bc96c`**: 설치 `bc972`.
- **`bc972`**(설치 값): `JSR 43e34`(복귀 `bc978`). **`bc978`**: `JSR 49fc6`(복귀 `bc97e`; C는 읽지 않음). **`bc97e`**: A0 := LONG `c`, D0.W := WORD `42(A0)`, (부호) D0.W ≥ WORD `42(A6)` → `bc9a2`, 아니면 `bc98e`.
- **`bc98e`**: BYTE `15` bit 0 = 0 → `bc99e`, 아니면 `bc998`: LONG `(A6)` := `bc9e0`(쓰기만; fall-through `bc99e`). **`bc99e`**: `BRA.W bc9b2`. **`bc9a2`**: BYTE `15` bit 0 ≠ 0 → `bc9b2`, 아니면 `bc9ac`: LONG `(A6)` := `bc9e0`(쓰기만; fall-through `bc9b2`).
- **`bc9b2`**: BYTE `63(A0)` = 0 → `bc9c8`, 아니면 `bc9ba`: WORD `76` −= 1, 옛 WORD ≠ 0 → `bc9c8`, 아니면 `bc9c2`: LONG `(A6)` := `bcaa0`(쓰기만). **`bc9c8`**: BYTE `62(A0)` ≠ 0 → `bc9de RTS`, 아니면 `bc9d0`: WORD `76` −= 1, 옛 WORD ≠ 0 → `bc9de`, 아니면 `bc9d8`: LONG `(A6)` := `bca2c`(쓰기만; fall-through `bc9de RTS`). A0는 `bc97e`가 정한 값이 block 경계를 넘어 쓰인다.
- **`bc9e0`**(설치 값): anim(`e3`, `200140`, 8)(복귀 `bca08`). **`bca08`**: 설치 `bca0e`. **`bca0e`**: `JSR 43e34`(복귀 `bca14`). **`bca14`**: `JSR 49fc6`(복귀 `bca1a`). **`bca1a`**(소비자): Clear → `bca2a RTS`, Set → `bca1e`: BYTE `15` bit 0 반전(`BCHG`), LONG `(A6)` := `bc93c`(쓰기만; fall-through `bca2a`).
- **`bc404`**(FR1c `bc36c`의 `28ae` 자식 값): D0.W := 0, D1.W := 0(`MOVE.W`: 상위 WORD 유지), `JSR 49290`(복귀 `bc412`). **`bc412`**: `JSR 491c4`(복귀 `bc418`). **`bc418`**: D0.W := `1f`, D1.W := `e`, D2.B := 0, `JSR c6a96`(복귀 `bc42a`). **`bc42a`**: anim(`ba`, `200080`, `38`)(복귀 `bc452`). **`bc452`**: WORD `68` `1e` := `e0ef`, 설치 `bc464`. **`bc464`**: `JSR 43e34`(복귀 `bc46a`). **`bc46a`**: `JSR 49fc6`(복귀 `bc470`). **`bc470`**(소비자): Clear → `bc47a RTS`, Set → `bc474 JMP 2a00`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다.

| 표 | 범위 | 읽는 곳 | 내용 |
| --- | --- | --- | --- |
| 애니메이션 LONG | `ea712..ea722`(4 LONG) | `ea880`(index 4·WORD `76`, sext) | `000eac64 000eaccc 000ead5c 000eae28` |
| 애니메이션 LONG | `ea722..ea732`(4 LONG) | `ea8ae` | `000eafb2 000eb040 000eaea2 000eb13e`(그 뒤 `ea732..`는 U18 `ea95a` 등의 표) |
| 지형·상자 자료 | `772a0..772de` | callee `4ae4a`(`772a0`), `1ab80`/`1ab02`(`772be`, `772c6`: LONG 둘), `49f8c`(`772ce`) | 이 단위는 주소만 넘긴다 |
| 사거리 표 | `c88d4..` | callee `490ba` | 이 단위는 주소만 넘긴다 |
| bank LONG | CPU `2000d0` `2000d4` `200090` `20003c` `200080` `200140` | anim 꼴(`LONG d(…)`) | 물리 `200000` bank 값은 V1·실제 ROM 차분이 원본으로 읽는다(단위 시험은 합성). [U] 물리 `300000` bank에서의 쓰임 |

- [F] **callee에게 넘기기만 하는 자료**: `49f8c`의 A1(`772ce`, bank 창 LONG), `28ae` 자식 `77206`(`771ba`), `2986` 자식 `eaac0`·부모 `100bf4`(`ea6d0`), `8ebe` `c6a96` `49290` `491c4` `443d2` `44602` `ea65a` `ea762` `4970a` `43e08` `492d0`의 D0..D7/A0.

## 경계·routing 밖 출구

- [F] 이 단위 안에는 live 대상 호출·TRAP·계산 점프가 없다. 설치 쓰기의 정지 값(결정 2)은 실행하지 않는다.
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 15개: `77068` `771dc` `77282` `bc47a` `bc9de` `bca2a` `c5430` `c5694` `c579e` `d1024` `d107c` `d10ae` `d10ba` `d10bc` `ea906`, 그리고 C를 정하고 끝나는 `ea6fc` `ea70a`(같은 block의 `RTS`)와 `77114`(설치 쓰기 뒤 `RTS`), `77298`.
- [F] **native 정지 규칙 주의**(V1): FR2 spec의 `first_unrouted`(`8c16 < pc <= 8ca6` 내부, 정지 `2a00` `2a24`, 홀수 live 정지 PC 버림)를 그대로 쓴다. `JMP d1d08`(`771ec`)·`BRA.W 72dd2`·`BEQ.W 71c90`은 routing된 출구다. `2986`이 실패하면 기존 caller-X checked 오류다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1·FR2·FR2b spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 자연 node, LONG `c(A6)` := 자연 node, 스택 WORD/LONG, PC).
- [I] IO 관측 상태가 이 단위의 실제 진입 상태다(`fr2b/ioA/frontier.json`의 확정 frontier와 위 "자연 후속 확인"). V1 spec에는 이 출처를 주석으로 적고, IO 비교 재실행(검증 작업자)이 자연 경로를 직접 확인한다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `49fc6` → `70e12`(`70e0c`)·`7704a`(`77044`)·`77264`(`7725e`)·`bc470`(`bc46a`)·`bca1a`(`bca14`)·`ea8fc`(`ea8f6`), `ea8e8` → `ea8fc`(같은 단위의 Clear), `1ab80` → `7705e`(`77054`), `1ab02` → `77158`(`7714e`)·`77278`(`7726e`), `76f98` → `770bc`(`770b6`), `ea69c` → `77170`(`7716a`), `28ae` → `771ca`(`771ba`), `4b54e` → `c5412`(`c540c`)·`c5682`(`c567c`), `1abda` → `ea6b8`(`ea6b0`), `ea65a` → `ea6cc`(`ea6bc`), `4c2cc` → `ea86e`(`ea860`). 단위 시험은 RAM·합성 자료만 읽는 생산자만 실제 사슬로 넣고(생성기가 두 C 값을 모두 만들어 낸 것), 나머지는 선언 C 행만 둔다(V1·실제 ROM 차분이 실제 사슬).
- node fixture: callback·설치 값(`c5370` `c53ec` `c564e` `76ff2` `7703e` `7706a` `77138` `77206` `77258` `ea85a` `ea8d2` `70d92` `70dfc` `bc93c` `bc972` `bc9e0` `bca0e` `bc404` `bc464`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `d0fec` `d1028` `d108a` `d10b4` `ea69c` `77284` `c579e`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, FR2b 꼴): 시작 197개 × 들어오는 C 3가지, zero-step, 내부 PC 815개 정확한 오류, 경계 stop(출구 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), 그리고 빈틈 종류별 hint:
  - 부호·영 확장: `c53a2` `EXT.L`(WORD `76` = `8000`/`7fff`/`ffff`), `770c2`/`770d6`/`770e0` 부호 WORD 비교(`8000` `7fff` `3f` `40`), `d0ff4` `CMPI.W #2`(`8000` `1` `2`), `d103a` `MOVEM.W` 부호 확장(`8000` `7fff`), `d104c` `EXT.L`, `ea6bc` `MOVEA.W #0`, `ea6fc` `LEA -2e(A0)`.
  - 음수 색인: `ea880`/`ea8ae` WORD `76` = `2000`/`e000`(4배가 WORD `8000`/`8000`) — 합성 ROM 위치로.
  - MULU 상위 WORD: `d1000` D2/D3/D5 상위 WORD가 0이 아닌 입력(`MULU`가 하위 WORD만 읽음), `MULS` 부호(`8000`·`ffff`), `DIVU` 몫 `8000`(D3.W = 2 → MULS의 부호 WORD).
  - 꺼낸 레지스터: `ea6ea`의 A1(넣은 A0), `d1036`의 D0/D1(넣은 WORD), `d107c`의 D0/D1(넣은 D2/D3), `d10ae`, `770d6`의 D2, `ea6fc`의 WORD.
  - RAM 거울: `ea8d2`/`ea8e8`의 `5e51(A5)`/`5e50(A5)`를 A5 = `1f8000`에서(거울 `10de51`), `ea6fc`의 A0를 거울 위쪽(`1ffff0` 근처: 영 확장 `ffd2`이면 RAM 밖).
  - BCHG/bit 조합: `bca1e` BYTE `15`(`00` `01` `fe` `ff`), `7709e` BSET #3, `77114` BCLR #0, `ea8d2`/`ea8e8` BCLR #7(옛 bit 0/1 × 다른 bit), `77174` BTST #5, `c53ec`/`c564e` BTST #7, `bc98e`/`bc9a2` BTST #0.
  - 상위 레지스터 bit: `MOVE.W #imm,D0/D1`(`bc404`), `MOVE.B D3,D1`(`d1028`), `CLR.W`(`771ce`), `LSR.B`(`77298`), `SMI.B`/`NOT.B`(`d108a`), `MOVE.W D6,D7`(`d10bc`), `MOVE.W D2,D0`(`770de`), `MOVE.W D1,D0`(`ea8a4`).
  - DIVU: `d1000` D3.W = 1(몫 `10000` 넘침: D4 그대로) / 0(오류 행), `d10bc` D0 = `10000`(D0.W = 0: 오류 행), 몫 경계.

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `tools/probe_scan_fr3.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_fr3.out` 46줄)으로 확인한 결과:
  - 그대로 참인 것(stop-only·레지스터 값·자기 범위 끝·`!in_ranges`만): N15(`76f1e`.. 행의 A0 = `7706a`/`76ff2`, `RANGES` 끝 `76ff2`), N32b(`39e02` 행 stop `d0fec`, `at_pc[]` `d0fec`), N35(`RANGES` 끝 `ea69c`), U18(`RANGES` 끝 `ea85a`, `ea83a` 행의 설치 값 `ea85a`), FR1c(`RANGES` 끝 `bc404`, `bc36c` 행), FR2b 시험(`RANGES` 끝 `bc93c`, 주석의 `70d92`), 관측기 `observe_animation_machine_objects_g2.py`의 고정 표(pin된 역사 기록).
  - **옮길 것(결정 6, 이전 기대값 기록):**
    - `tools/unit_fixture_specs/fr2b.py` `build()`의 "자료·정지 PC는 routing 밖" 확인 목록 `(0x702fa, 0x70d72, 0x76922, 0x71884, 0xbc93c)`: `bc93c`가 이 단위 시작이 되므로 빼고 정지 설치 값 `70e2a`(FR2b 정지 값, 여전히 routing 밖)로 바꾼다(이전 기대: `unit_of(bc93c) is None`).
  - [F] `make -j3 all test`는 첫 실행에 통과했다: 다른 C++ 시험의 탐침·계산 점프 guard 행 중 이 단위가 깨뜨린 것은 없다.
  - [I] V1 spec 중 native 사슬이 `c5370` `76ff2` `7706a` `d0fec` `ea85a` `70d92` `bc93c` `bc404`를 첫 routing 밖 PC로 멈추던 것은 더 진행한다(정지는 routing에서 계산되므로 spec 수정은 필요 없을 것으로 본다; 검증 작업자가 회귀로 확인).
- [F] stage_event / stage_event_ops 검증기의 `CPP_PINS`(`animation_machine.cpp` `4fc41a76…`, `animation_machine_internal.h` `142f253e…`)는 이 단위의 공유 수정으로 맞지 않게 된다(FR1·FR2a·FR2b 관례대로 새 값으로 갱신 필요; 메인 결정).

## 결정

1. **범위.** FR3 = `c5370`(12 run) 묶음 33 + 그 run의 자연 후속(`76ff2` 11, `7706a` 58, `77206` 12, `ea85a` 19, `70d92` 12) + `bc93c`(3 run) 묶음 24 + `bc404` 10 + `d0fec` helper 묶음의 나머지 `d1028..d10d8` 18 = **197**. 정지 설치 값 `bca2c` `bcaa0` `c5432` `c554c` `c5696`. `5ab82`(221)는 혼자 한 단위(FR5), `50dae`(100)는 FR6으로 미룬다(`area-d-completion-plan.md`). `d1028` 묶음은 FR3의 IO 진척에 기여하지 않는다(그 run은 `5ab82`에서 먼저 멈춤): 메인이 빼기로 하면 179 block이 된다.
2. **설치 값.** `MOVE.L #v,(A6)`은 v가 바로 다음 PC일 때만 그 block으로 들어간다(`ofr3_install`; `70dfc` `7703e` `77258` `bc464` `bc972` `bca0e` `c53ec` `c564e` `ea8d2`). 나머지는 LONG 쓰기뿐이다. closure는 native가 실행한 설치 값만 따라간다(실행되지 않은 값은 정지).
3. **carry 보존 목록.** 소비자 17개. C를 넘기는 `RTS`는 없다. `ea6fc` `ea70a` `ea8e8` `771d8`은 자기 block에서 C를 정한다.
4. **DIVU.** WORD 제수 0은 checked 오류 `objects fr3 DIVU zero divisor`(FR1·FR2a 관례). 몫 넘침은 원본대로 대상 그대로. 자연 경로는 `d0ff4`가 D3.W ≥ 2를, `d10b4`가 D0 ≠ 0을 보장하지만(D0.W = 0인 D0 ≠ 0은 막지 못함) 직접 진입은 모든 값을 받는다.
5. **TB 시작 PC.** IO 관측의 TB 시작 `76ff8` `76ffe` `77002` `d0fee` `d0ff8`은 block 시작이 아니다(내부 PC 오류).
6. **숨은 탐침 이전.** V1 spec `fr2b.py`의 `bc93c` routing 밖 확인 → `70e2a`. stage_event / stage_event_ops `CPP_PINS` 갱신은 메인이 정한다.
7. **다음.** 이 단위 뒤 자연 frontier: `72f8a`(c5370 run frame 496, FR4 `7343a` 묶음), `878dc`(bc844 run frame 309, FR4), `5ab82`(FR5), `50dae`(FR6), `4e68e`(C 영역).

## 미확인

- [U] node field 의미(BYTE `15` `5e` `61` `88` `89` `8a`, WORD `1e` `20` `2e` `32` `42` `46` `54` `68` `76` `7a` `7e` `82` `9c`, LONG `36` `3a` `56` `64` `7e` `82` `86`), 표 `ea712`/`ea722`·`772a0..`·`c88d4` 값의 의미, BYTE `5e50(A5)`/`5e51(A5)`의 정체.
- [U] `ea880`/`ea8ae`의 WORD `76`이 항상 0..3인지(원본에 상한 검사 없음).
- [U] `d10bc`의 결과 해석(32/16 나눗셈의 D6 상위 WORD 쓰임).
- [U] 물리 `300000` bank에서 bank 창 LONG의 쓰임.
- [U] 자연 frame에서 이 단위 뒤 다음 첫 미routing PC(IO 비교 재실행으로 확인; [I] 예상은 결정 7).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr3.cpp`(case label 197 = scratch `starts_fr3.txt`와 집합 일치, scratch 검사), `engine/tests/animation_machine_objects_fr3_test.cpp`(생성 구역 + 수작성 규칙: `d1000` DIVU 몫 `8000`의 MULS 부호·MULU 하위 WORD만·DIVU 넘침에서 D4 유지, `d1036` MOVEM.W 부호 확장, `d1028` push 순서·MOVE.B, `d107c` 꺼낸 LONG·LSL.L, `d108a`/`d10bc` 32/16 나눗셈과 부호 처리, `d10bc` D0.W = 0 오류, `ea6ea` 꺼낸 A1, `ea6fc` RAM 거울에서 `LEA -2e`, `ea70a` ADDQ·ANDI, `ea8d2` A5 = `1f8000` 거울 BCLR, `ea8e8` 두 출구 Clear, `ea880` 음수 WORD 색인(합성 위치 `e2712`; 영 확장이면 `f2712`라 오류), `ea8ae` 합성 표, `c53a2` EXT.L·부호 BLE·NEG.L, `bca1e` BCHG, `771b0` 무부호 빌림, `770d6` 부호 BLE, `77284` ASR.L, `77298` LSR.B, `bc404` MOVE.W 상위 유지, `770f8` WORD 연산, 범위 옆 자료 PC `772a0` `ea712`의 dispatcher 오류), `tools/generate_animation_machine_objects_fr3_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음 SHA256 `0450303908824dc6…`, 약 76초), `tools/unit_fixture_specs/fr3.py`(V1 spec; 정적 검사만 함 — `load_routing` 규칙 124개 뒤 시작 197개와 내부 815개가 모두 `animation_objects_fr3_block`, sentinel·자료 PC는 routing 밖, 정적 후속은 시작이거나 routing된 출구, 사슬 18개의 소비자가 진입에서 닿음; 합성 기반 상태와 가짜 tracer로 world·hint·error·chain/node/callee 생성 함수를 native 없이 실행해 Python 오류 0, 오류 fixture 848개 이름 중복 0). 공유 수정은 "공통 규칙"의 다섯 곳과 "영향받는 기존 시험"의 이전 한 곳(`fr2b.py`)뿐이다.
- [F] 단위 시험 world: A7 = `10ef00`, 합성 typed physical byte(ROM 자료 아님, 자료 영역만): 표 `ea712..ea732`(RAM 탐침 값 `10fe10..10fe2c`), 상자 `772be..772ce`, bank 창 `2000d0`(→ `2a1000`) `2000d4`(→ `2a2000`) `200090`(→ `2a3000`) `20003c`(→ `2a4000`) `200080`(→ `2a5000`) `200140`(→ `2a6000`)와 그 뒤 LONG. 생성기가 실제 생산자 사슬을 두 C 값 모두로 만들어 남긴 것: `1ab80` → `7705e`, `1ab02` → `77158`·`77278`, `1abda` → `ea6b8`. 한쪽 C만 나온 것(`76f98` Set만, `ea69c`/`28ae`/`4b54e`/`ea65a` Clear만)과 ROM 자료를 읽는 것(`49fc6` `4c2cc`)은 선언 C 행만 있다(V1·실제 ROM 차분이 실제 사슬). `ea8e8` → `ea8fc`는 단일·path 행이 모형 Clear로 확인한다. 생성기 보고 `branch blocks with a missing successor [7718c → 7719e]`(정적으로 갈 수 없는 쪽).
- [F] `make -j3 all test`(작업자, scratch `make_all1.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 276개, Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR3 시험 줄: `animation machine objects fr3: 603 fixtures (419 single-block, 93 path, 24 producer chain, 34 declared C, 33 checked error (6 with a later failing PC), 71 kept C), 197 blocks, 3352 calls, 65903 checks`. FR2b 최종 기준 대비 다른 시험 줄 변화는 없다(기존 C++ 시험 중 이전이 필요한 것은 없었다).
- [F] 검증 작업자 준비물(scratch, 실행하지 않음): `build_ubsan.sh`, `mut/run_mut.py`·`mut/mutants.py`(변이 229개; 패턴 유일성 확인, `--check`는 문법 검사까지 통과), `realrom/real_fr3.py`(FR2b harness에 FR3 world·소비자·진입; `py_compile`만), `runwrap.py` `run_frames.sh` `run_area_clear.py` `run_stage_entry.py` `run_regs.sh` `v1_all.sh` `v1_one.sh` `io_ab.sh` `io_delta.py` `legacy/`(경로만 바꿈, frame·V1 명령마다 `MS5_SEED_DIR=artifacts/stage_entry_body`). 실행 순서와 기대값은 scratch `HANDOFF.md`.
- [F] stage_event / stage_event_ops `CPP_PINS` 새 값(메인이 갱신): `animation_machine.cpp` `869a9dc12b14ba47ed65642ab937cb1bbaa5a49775241e3a325ce47fc1d1a446`, `animation_machine_internal.h` `f7953e9a0a117d13b4f4b8966df5402838e579a4a4efb36c325affd18daf1f3b`.

### 검증 기록 (Sonnet 5.5 / medium 검증 작업자, 2026-10-19 ~ 20)

모든 명령은 `MS5_SEED_DIR=artifacts/stage_entry_body`. ROM SHA256 `29112a94…c860f`, mtime `1791291625` 불변. 출력은 scratch `/Users/start/Workspce/ms5-scratch/fr3/`만 사용했다(공유 `artifacts/` 미사용).

- [F] **변경 3건**(결함이 아니라 시험 틈·spec 보고 정리, 이전 동작 기록): (1) 생성기 `hints()`에 `c5686` 행 추가(NODE+5e / 5f 모두 `ff`: `CLR.B 5e(A6)`가 이웃 5f를 건드리지 않음; 변이 `c5686-5e` 생존 때문), 시험 재생성 -> 시험 SHA `f386ce09…`(603 -> 604 fixture, 3356 calls, 66041 checks). (2) V1 spec `fr3.py`: 블록 행의 `missing successors`에서 정적으로 불가능한 `77192 -> 7719e`(STATIC_IMPOSSIBLE)와 소비자 후속(`ea8e8 -> ea8fc`, 사슬 fixture가 덮음)을 제외하고, 사슬 `ea8e8`은 항상 Clear라 `ea8fc -> ea900`(Set)을 요구하지 않음(그 Set은 `chain-ea8f6-to-ea8fc-0`가 덮음). 이전 동작: 이 4건이 `missing successors`에 추가로 찍혔다. fixture 수·digest 불변(1458). (3) `verify_animation_machine_stage_event.py` / `_ops.py` `CPP_PINS`를 `869a9dc12b14ba47…` / `f7953e9a0a117d13…`로 갱신(이전 값은 주석에 보존). 그 밖의 C++·다른 spec·다른 시험 변경 없음.
- [F] `make -j3 all test`: 종료 0, 경고 0. FR3 줄 `604 fixtures (420 single-block, 93 path, 24 producer chain, 34 declared C, 33 checked error (6 with a later failing PC), 71 kept C), 197 blocks, 3356 calls, 66041 checks`(수정 전 603 / 3352 / 65903). Python 310 OK. **UBSan**(`-fsanitize=undefined -fno-sanitize-recover`, 수정 전후 둘 다): 종료 0, `runtime error` 0.
- [F] **변이 229개**: 수정 전 222 killed / 7 survived, 수정 후(전체 재실행) **223 killed / 6 survived**(`c5686-5e`가 죽음). 남은 6개는 모두 동치로 증명한다(관측 가능한 최종 상태가 같다): `770d6-lt`(`BLE` -> `BLT`: 같을 때 `770de MOVE.W D2,D0`은 D0.W = D2.W라 무변화, 행은 `770e0`에서 멈춤), `770e0-gt`(같을 때 `770e8 MOVE.W #40,D0`이 D0.W = 40이라 무변화), `d0ff4-gt`(같을 때 `d0ffc MOVE.W #2,D3`이 D3.W = 2라 무변화), `d1000-d5-long`(D5는 곧 `MULU.W D2,D5`의 LONG 곱으로 전체 덮여 상위 WORD가 관측되지 않음), `d1036-tst-long`(D0는 `MOVEM.W` 부호 확장 값이라 WORD가 0이면 LONG도 0), `divu-no-overflow`(DIVU 넘침은 `d1000`에서 D3.W = 1일 때뿐이고 그때 `(나머지 0 << 16) | 몫 0x10000` = `0x10000`이 D4 유지값과 같고, `d10bc`의 두 나눗셈은 나머지 < 제수라 넘치지 않음).
- [F] **실제 ROM 차분**(5 x 1,500, seeds 1 2 3 + FOLLOW_ANIM 4 5): 5/5 `mismatches 0`, 합친 시작 **197/197**(seed 2 단독은 `70d9a` `bc96c` 빠짐, 다른 seed가 덮음), 하네스 수정 없음. 알려진 분류만(seed 4에서 `ea8a4` 계산된 dispatcher 1건).
- [F] **V1 fr3** 두 번(수정 후): 1458 fixture, failed 0(expect: match 605 / error 843 / mismatch 10), `[(name,digest)]` 동일, `carry oracle ok`(Unknown/Clear/Set 562/19/24), `visited 197/197`. 남은 `missing successors` / `unreachable outcomes`는 3건: `770bc -> 770c2`, `771ca -> 771dc`, `ea6cc -> ea6d0`(시드 세계에서 생산자 `76f98` / `28ae` / `ea65a`가 한쪽 C만 냄, [I]; 두 C 모두 C++ 선언 C 행이 덮고 실제 ROM 차분이 실제 사슬로 비교함).
- [F] **V1 회귀**(25 spec): 모두 failed 0, fixture 수가 FR2b 기준과 동일(fr2b 1,761 / fr2 1,592 / fr1 1,631 / fr1b 1,441 / fr1c 1,755 / b2a 1,386 / b4 1,830 / b4b 1,723 / b1a 2,807 / b1b 1,892 / b1c 1,842 / b2b 1,419 / b2c 1,707 / b2d 1,485 / b2e 1,054 / b3a 1,468 / b3b 1,360 / b3c 625 / c1 1,741 / c2 1,607 / c3b 480 / d9 26 / f6a 320 / f6b 726 / f6c 1,538). 이번에는 `b2a` 실패 없음.
- [F] **frame**: D1 / controller game / IRQ 54,400/54,400, demo 45,684/45,684, natural mismatches 0. FR2b `verification.json`과 `inputs`·`build`·시간 필드를 뺀 모든 값이 같다(바뀐 frame 없음, native 비교 필요 없음).
- [F] **legacy**(scratch git-clone 루트): stage_entry(cases 335, split 23,761, negatives 2,757, carry 21,829/100/1,832) PASS; area_clear(conditions 256, frames 37,418, split 117,537, continuous 37,444, negatives 181, guards 26) PASS; stage_event(핀 갱신 후; typed 560, phases 22,870, negatives 1,020) PASS; stage_event_ops(typed 284, phases 5,081, negatives 894) PASS; frame_helpers(cases 199, split 3,683, negatives 180) PASS; card_menu_close(cases 82, split 7,886, negatives 85) PASS; objects_g1(4,752 행: execution-equal 4,688 / checked-boundary 55 / native-step-limit 8 / invalid-declared-flag-precondition 1) 완료 rc 0.
- [F] **IO**(`verify_animation_machine_io.py --workers 1`) 두 번: `verification.json` SHA `014dd417…`, `frontier.json` SHA `245aacc2…` 둘 다 동일(`diff -rq` 동일, harness_stderr / run_info 제외). compared 173,966, **matched 161,229**(FR2b 158,202, **+3,027** = 예측 161,229와 정확히 같음), mismatches 0, cpp_errors 0, frontier run 39(unrouted 37 + guard fixture 2), P0 81,600 불변.

| 구성 | FR2b | FR3 | 증분 |
|---|---|---|---|
| P0 | 81,600 | 81,600 | 0 |
| P1 | 69,252 | 72,002 | +2,750 |
| P1b | 5,964 | 6,241 | +277 |
| boot-demo-0 / title-idle / title-start / fx-* | 변화 없음 | 변화 없음 | 0 |
| 합계 | 158,202 | 161,229 | +3,027 |

새 frontier(첫 unrouted PC: run 수, frame): `4e68e` 15 (2/122/222), **`72f8a` 12 (496; c5370 12 run, 252 -> 496)**, `5ab82` 3 (141), **`878dc` 3 (309; bc93c 3 run, 276 -> 309)**, `50dae` 3 (271), `2634` 2 (fixture), `1d1f4` 1 (381). 사라진 frontier: `c5370` 12, `bc93c` 3. `dleft.py`: 실행된 unrouted PC D 640 / E 220 / C 620 (FR2b D 790, -150), D 중 C 비의존 273, C 의존 367, 예측 matched 161,229.

## block 목록

[F] scratch `starts_fr3.txt`(SHA256 `8497745968ea939dac031051aceb80f326dd5a4f50925c5d88a9f901b677a755`)와 같다.

- **`70d92..70e2a`(12)**: `70d92 70d9a 70dc2 70dc6 70dee 70dfc 70e06 70e0c 70e12 70e16 70e20 70e26`
- **`76ff2..771de`(49)**: `76ff2 77010 77038 7703e 77044 7704a 7704e 77054 7705e 77062 77068 7706a 77088 7709e 770aa 770b6 770bc 770c0 770c2 770d4 770d6 770de 770e0 770e8 770ec 770f6 770f8 77114 77138 7714e 77158 7715c 77162 7716a 77170 77174 7717e 77186 7718c 77196 7719e 771a6 771aa 771b0 771ba 771ca 771ce 771d8 771dc`
- **`771e6..772a0`(16)**: `771e6 771ec 77206 7720c 7722a 77252 77258 7725e 77264 77268 7726e 77278 7727c 77282 77284 77298`
- **`bc404..bc47c`(10)**: `bc404 bc412 bc418 bc42a bc452 bc464 bc46a bc470 bc474 bc47a`
- **`bc93c..bca2c`(24)**: `bc93c bc96c bc972 bc978 bc97e bc98e bc998 bc99e bc9a2 bc9ac bc9b2 bc9ba bc9c2 bc9c8 bc9d0 bc9d8 bc9de bc9e0 bca08 bca0e bca14 bca1a bca1e bca2a`
- **`c5370..c5432`(18)**: `c5370 c5388 c538e c53a2 c53b6 c53ba c53be c53e6 c53ec c53f6 c53fc c5400 c5406 c540c c5412 c5416 c542a c5430`
- **`c561a..c5696`(14)**: `c561a c5648 c564e c5658 c565e c5662 c5668 c566e c5676 c567c c5682 c5686 c568e c5694`
- **`c579e..c57a0`(1)**: `c579e`
- **`d0fec..d10d8`(25)**: `d0fec d0ff2 d0ff4 d0ffc d1000 d1022 d1024 d1028 d1036 d1048 d104c d105e d106e d107c d108a d1096 d1098 d109e d10a2 d10a6 d10ac d10ae d10b4 d10ba d10bc`
- **`ea69c..ea6a2`(1)**: `ea69c`
- **`ea6b0..ea712`(8)**: `ea6b0 ea6b8 ea6bc ea6cc ea6d0 ea6ea ea6fc ea70a`
- **`ea85a..ea908`(19)**: `ea85a ea860 ea86e ea872 ea878 ea880 ea89a ea89e ea8a4 ea8ae ea8c8 ea8d2 ea8dc ea8e2 ea8e8 ea8f6 ea8fc ea900 ea906`
