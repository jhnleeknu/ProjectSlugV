# frontier 단위 FR5(FR4 뒤 D 영역 IO frontier `5ab82`와 그 자연 후속) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. FR2·FR2b·FR3·FR4 계약(`animation-machine-frontier-fr4-contract.md`)의 구조·공통 규칙을 따르고 다른 점만 적는다. 메인 지시: `area-d-completion-plan.md` §4의 FR5(`5ab82`, root `5ab6c`, 3 run frame 141, TRAP `5ae0e`, 약 203 block)를 현재 routing으로 다시 재고, FR6 `50dae`(약 100–105 block, 3 run frame 271)가 작으므로 FR5 단독과 "FR5 = `5ab82` 핵심 + `50dae`" 나눔 중 약 220 이하에 더 맞는 것을 새 측정으로 정한다. 목표는 FR5+FR6 뒤 IO 집합의 D 첫 정지 0이다. 같은 run의 자연 후속은 들어가는 한 600 frame까지 따라간다. 계산 표는 모두 전사하고 TRAP 자리는 checked 경계다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기 `200190`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `db2ec06`(branch `claude/frontier-units-4`, PR #9 head; FR3·FR4 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `31a1b033911fd15cfed40998c1072f32db29a85d7605848e1049b1bbf86735c8`(= FR4 IO 재실행 `frontier.json`의 `routing_file_sha256`), `animation_machine_internal.h` `8570d1e86121aa5ad8432c716d2787cdc69ef5cb26bbc9cb3a78742edd7625e0`.
- [F] frontier 입력: FR4 뒤 IO 재실행 `/Users/start/Workspce/ms5-scratch/fr4/ioA/frontier.json`(첫 실패 전 일치 **163,350**, frontier run 24 = `4e68e` 15 + `5ab82` 3 + `50dae` 3 + `1d1f4` 1 + guard fixture `2634` 2). 이 단위의 확정 frontier: `5ab82` P1 2(`P1/016` `P1/017`) + P1b 1(`P1b/016`), frame 141, phase N, 복귀 `2ac2`. [F] `5ab82`는 routing된 N13 `5ab3a`(`MOVEA.L #5ab82,A0; MOVE.W #14,D0; JSR 28ae`)가 만드는 `28ae` 자식의 callback 값이다(N13 계약 "범위 밖 `28ae` 자식 `5ab6c` `5ab82` `5b4c6`").
- [F] **자연 후속 확인**(scratch `tools/dstate.py` `tools/fr5next.py` `tools/fr5pcs.py`, IO 관측 읽기 전용): `artifacts/animation_machine_io_native/runs/*/*.json.gz`의 frame별 `unr_new`를 현재 routing으로 다시 걸렀다. 세 run 모두 같다: frame 141 `5ab82` … `5ac68`(`4464a` `5b1f8` 나눗셈 `5aede..5b21e`, `5ae66` 곱셈 `5ae10..5ae92` 포함) → 142 `5ac84` `5ac9e` `5acac` … `5ad64`, `44656` `44660` → 146 `5ad1c` `5ad32`, `28ae` 자식 `5ad98` `5adac` … `5ae06` → 147 `5add8` → 163 `5ae08` → 185 `5acfe` → 186 `5ad66` `5ad70` `5ad80` `5ad84` `5ad8e`, 그 뒤 600 frame 끝까지 routing 밖 PC 없음(`fr5next.py`: 단위 뒤 세 run의 다음 정지 = 끝 600).
- [F] 정적 디코드: capstone M68000, FR4 계약과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, `MOVE.L #imm,(A6)` 설치 값 중 범위 안의 것, 범위 밖에서 들어오는 실제 분기 대상, 연속 Bcc 묶음은 한 block). routing된 PC, `RTS`, `TRAP`(경계, 단위에 넣지 않음), 계산 점프에서 멈춘다. `28ae` 자식 값은 기록만 한다. 진입 = 위 run들이 실제로 실행한 routing 밖 PC 131개(다른 진입의 closure 안에 이미 든 것은 뺌: `4464a` `5ab82` `5ad98`). 설치 값은 native가 실행한 것만 따라간다(FR3 결정 2; 이 단위의 설치 값 4개는 모두 범위 안이다). TB 시작이지만 block 시작이 아닌 PC `5afe8` `5afea` `5afec` `5afee` `5aff8` `5affa` `5affc` `5affe`(나눗셈 반복 block `5afe6` `5aff6` 안, 4 KiB 경계 `5b000` 앞의 Unicorn TB 경계)는 진입이 아니다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr5/`
  - `tools/`: FR4 scratch 도구의 경로만 바꾼 사본(`fclos.py` `hroute.py` `dstate.py` `dleft.py` `refidx.py` `cread.py` `fr4dis.py` …), 새 `unit_fr5.py`(이 단위 정의; 묶음은 환경 변수 `FRG`), `fr5next.py`(단위 뒤 run별 다음 정지), `fr5pred.py`(예측 일치 frame·D 남은 PC), `fr5pcs.py`(run별 실행 PC와 첫 frame), `inrefs.py`(범위 밖에서 범위 안으로 들어오는 분기·상수 전수), `longs.py`, `probe_scan_fr5.py`.
  - `starts_fr5.txt`(시작 195개) SHA256 `5ad39ca4bdb048ceaa1d7f2c5917b78a2a5dc0902599953894d219b36e4f9d64`; `unit_fr5.out`(block별·범위 전체 디코드), `probe_fr5.out`.
  - 재현: `cd /Users/start/Workspce/metalslug-fu4 && FRG='5ab6c=5ab6c;44602=44602' .venv/bin/python /Users/start/Workspce/ms5-scratch/fr5/tools/unit_fr5.py B D`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **계획값 재측정**(현재 routing `31a1b033…`, `area-d-completion-plan.md` §4 규칙): FR5 root `5ab6c`(실행 PC 125개) + `44602`(실행 PC 6개, 모두 `4464a..44666`; root `44602` 자체는 B2e가 routing함)의 실행 PC 131개(실행 6,342회, 3 run) closure = **195 block 시작**, 명령 584, 5 범위(계획 도구 셈 약 203은 JSR 복귀 등 leader 셈 차이; FR3 계약의 221은 FR3이 가져간 `d1028..d10d8` 18을 포함한 값). 예측 일치 frame **164,727**(+1,377 = 3 run × (600 − 141))로 계획과 같다. D 남은 실행 PC 502 → **371**(C 무관 155 → 24 = FR6 `50dae` 묶음의 실행 PC, C 뒤 347 그대로), D 첫 정지 run 6 → 3(`50dae` 3).
- [F] **FR6 측정**(같은 도구, FR5와 같은 규칙): `50dae` 묶음(`50dae` `50cf6` `50d08` `50dd2` `50e42` `51608`, 실행 PC 24개) closure = **105 block**(명령 227, 7 범위, 정지 설치 7개), 그 3 run(`P1/084` `P1/085` `P1b/084`)은 frame 271 → 600 끝(`fr5next.py`). 두 run 묶음은 겹치지 않는다(run도 다름).
- [F] **FR5 + FR6 한 단위**는 195 + 105 = **300 block**이라 약 220을 넘는다. 나누는 안 "`5ab82` 핵심 + `50dae`"가 220 안에 들려면 `5ab82` 쪽을 약 115 block 이하로 잘라야 하는데, 그러면 `5ab82` 3 run은 frame 141의 같은 첫 frame 안에서(나눗셈·곱셈 helper가 첫 frame에 모두 실행됨) 다시 멈추므로 IO 진척이 거의 없고, 남은 약 80 block을 FR6에 다시 넣어야 한다. 나눗셈 helper 하나(`5aede..5b1f6` 98 block)만으로 115에 가깝다.
- [F] **고른 것(결정 1)**: FR5 = `5ab82` 묶음 + `4464a` **195 block** 단독(5 범위, 명령 584, 짝수 PC 830(내부 635), 이어 붙인 바이트 1,660, SHA256 `39a6a3ef5e6a5f577e764f7390c35ce85b6eeec855b54d5f64396da259d482cb`). 그 3 run의 자연 후속을 600 frame 끝까지 모두 덮는다. FR6 = `50dae` 묶음 105(메인 결정대로 FR7 앞부분으로 약 220까지 채움; FR5 뒤 다시 잼). FR5 + FR6 뒤 D 첫 정지는 0이 된다(예측 165,714, 계획과 같음). 기존 routing과 겹침 0, 연속 Bcc 묶음 0.
- [F] **F4 범위 문서와의 겹침**: 없다. 재범위 문서 N13 행(`59ea2..59f1a` `5a7c8..5ab6c` `5b220..5b4c6` `d3580..d3614` `d3ab8..d3b70` `dbfac..dbfb8`, 범위 문서 U25의 같은 묶음)은 이 단위의 `5ab82..5b220`과 맞닿기만 한다(`5ab6c..5ab82`는 N13 밖 `28ae` 자식 `5ab6c`, `5b220`은 N13 시작). B2e의 `44602..4464a`도 `4464a`와 맞닿기만 한다.
- [I] **예상 진척**(상한 추정, IO 비교 재실행이 실제 측정값): 163,350 → **164,727**(+1,377). 나머지 frontier(`4e68e` 15, `50dae` 3, `1d1f4` 1, fixture `2634` 2)는 그대로이고 frontier run 수는 24 − 3 = 21(새 D 정지 없음).

| 묶음(진입) | block | 명령 | 범위 |
| --- | --- | --- | --- |
| `5ab82`(N13 `5ab3a`의 `28ae` 자식; + 설치 `5ac84` `5add8`, 범위 안 쓰기만 `5aca6` `5ad66`, `28ae` 자식 `5ad98`) | 55 | 145 | `5ab82..5ae0e` |
| 고정소수점 곱셈 `5ae66`(+ `5ae54` `5ae10`, 빠른 길 `5aebe`) | 26 | 62 | `5ae10..5ae3e` `5ae54..5ae98` `5aebe..5aede` |
| 고정소수점 나눗셈 `5b1f8`(+ `5aede`, 48회 펼친 반복) | 107 | 363 | `5aede..5b220` |
| 근사 거리 `4464a` | 7 | 14 | `4464a..44666` |
| 합 | **195** | 584 | 5 범위 |

## 요약

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `4464a..44666` | 28 | `6017af8dfd68c895fa7072d1d34844153332b07085eb46aa501821c35b1607f2` | 7 | 14 |
| `5ab82..5ae0e` | 652 | `632b72bb6699a8886f597e3951e49d20c902ded4013d973b4c43d94258f23a61` | 55 | 326 |
| `5ae10..5ae3e` | 46 | `8f126b527e1b10952ff8be7366a935e3f9e0e6bc3b49b3fbda44ba1a0761c336` | 5 | 23 |
| `5ae54..5ae98` | 68 | `467256be6364d61eccb675ec733027db0f4a79c380c4ba0c4879a1b7d5038438` | 14 | 34 |
| `5aebe..5b220` | 866 | `b01e629c82a49ea2e83d5e2dfd1afbec54bf81e13e0123985d64ffb85b087d8d` | 114 | 433 |
| 합계 FR5 | 1660 | 이어 붙인 바이트 `39a6a3ef5e6a5f577e764f7390c35ce85b6eeec855b54d5f64396da259d482cb` | **195** | 830(내부 635) |

- [F] closure가 5 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 범위 사이: `5ae0e`(`TRAP #15`, 결정 2), `5ae3e..5ae54`(정적 참조 없는 형제 진입 `5ae3e`: 부호 처리 뒤 `5ae54`로 떨어짐, 실행 안 됨), `5ae98..5aebe`(정적 참조 없는 형제 진입 `5ae98`: 범위 검사 `BHI 5ae0e` 뒤 `5aebe`로 떨어짐, 실행 안 됨).
- [F] **X 소비**: `ADDX.W D1,D1` / `ADDX.L D3,D3` 48쌍(나눗셈 반복; X는 같은 block의 `ADD.L D0,D0`가 정함), `NEGX.L D1`(`5ae62`; X는 같은 block의 `NEG.L D0`가 정함). block 경계를 건너는 X는 없다(결정 4). `MULU.W` 5(`5ae12` `5ae1c` `5ae2a` `5ae36` `5aeca`; 모두 무부호 16 × 16 → 32 bit, 피연산자 상위 WORD 무시). `DIVU`/`DIVS`/`MULS` 없음(나눗셈은 시프트·뺄셈 반복). 계산 점프·`JSR (An)` 없음. I/O port·bank 쓰기 없음. `ORI.B #1,CCR` 1곳(`5ad8e`, 읽는 곳 없음). `TRAP #15` 경계 1곳(`5ae0e`, 범위 밖). `MOVEM.W` 스택(`5ac02` 넣기, `5ac58` 꺼내며 부호 확장), WORD·LONG 스택 넣기/꺼내기(`5ac0c` `5ac14` `5ac1e` `5ac50` `5ae14` `5ae16` `5ae38` `5ae3a` `5b20e` `5b214`), 스택 메모리 연산 `ADD.L D2,2(A7)`·`ADDQ.W #1,(A7)`. `EXT.L`, `ASL.L #8`, `ASR.L #8`, `LSR.W #1`, `SWAP`, `NOT.B`, `NEG.L`/`NEG.W`, `SUB.W D0,D0`, `CLR.W`/`CLR.L`, `BSET.B`.
- [F] **경계 이웃**: routing된 것 `44648`(B2e `44602`의 `RTS`) `5b220`(N13). 그 밖은 routing 밖 형제 코드(`44666`: 다른 거리 함수, `5ab6c..5ab82`: `28ae` 자식 `5ab6c` 상태, `5ae3e` `5ae98`: 위 형제 진입).
- [F] **나가는 곳**(각 실행부의 `case` block 시작으로 routing됨): callee `28ae` `3af8` `8ebe` `8ff4` `1ab80` `43e34` `43ea4` `490ba` `49214` `4945e` `4970a` `49f8c` `49fc6` `4ae4a` `4b6f4` `d1028`(FR3), 출구 `JMP 2a00`(`5ad92` `5ae08`). routing 밖으로 나가는 곳은 `TRAP #15` `5ae0e`뿐이다(결정 2).
- [F] **참조**(ROM `<100000` 짝수 오프셋 전수 디코드 + LONG 상수, scratch `inrefs.py` `longs.py`): 범위 밖에서 들어오는 실제 진입은 모두 block 시작이다 — `5ab82`(N13 `5ab3a` `MOVEA.L #`), `4464a`(`JSR`: 이 단위 `5ac0e` `5acd8`, 밖 `29150` `8bd74` `9071a` `9088a`), `5ae54`(밖 형제 `5ae4c BPL.W` 및 `5ae52`의 fall-through). `5aebe`는 밖 형제 `5aeba`의 fall-through(정적 참조 없음). 범위 안 다른 PC로 들어오는 밖의 분기는 없다(`89d54`의 `#5b05b`는 홀수 자료 값).
- [I] 의미(이름은 확정하지 않는다): `5ab82`는 N13 적(`5a7c8` 계열)이 던지는 포물선 투사체다. 첫 frame에 bank `200190` anim, 소리 `1a21`(`3af8`), `8ff4` `8ebe`(`d42`), anim 자료 `5cf10`(`49f8c`), 가까운 플레이어(`4945e`; 없으면 자기 x − `60`)까지의 x 거리(왼쪽 ≥ `40`로 제한)와 y(`120` − WORD `46`)로 근사 거리(`4464a`: max + min/2)를 구하고, 고정소수점 나눗셈(`5b1f8`)·표 `5ddde`/`5de40`(`490ba`, 부모 BYTE `80` bit 1로 선택)·곱셈(`5ae66`)·`d1028`(FR3, 속도 분해 [I])로 LONG `36` `3a` `90` `94`(x·y 속도와 가속 [I])를 정한다. 다음 frame부터(`5ac84`): x 속도가 음이 아니면 x 속도·가속을 지우고, 아니면 가속을 더한다; `4b6f4`(BYTE `5b86(A5)`) Set 또는 부모 BYTE `61` bit 7이면 폭발 `5ad66`; y 속도 += 중력 LONG `94`; 이동 거리(`4464a`)를 WORD `8a`에 쌓아 `1200`마다 연기 자식 `5ad98`(`28ae`)과 `49214`; 이동 `43ea4`; 지면 WORD `86(부모)` ≤ y(LONG `32`)이면 착지(y 속도 0, y := 지면, 다음 frame 폭발 `5ad66` 설치); 그리기 `49fc6`; 충돌 `4ae4a`(상자 `5dc22`) ≠ 0이면 폭발; 화면 판정 `1ab80`(상자 `5dc1a`) Set이면 삭제 `2a00`. 폭발 `5ad66`: 소리 `1a21`, 폭발 자식 `d1d08`(`28ae`; FR3 범위), 성공하면 `4970a`(0, 0), 삭제. 연기 자식 `5ad98`: bank `200190` anim, `8ff4` `8ebe`, 자료 `5cf3e`, 속도 0, 그 뒤 매 frame 부모 WORD `84` −= 1을 자기 WORD `1e`(우선순위 [I])로, `43e34` `49fc6` `1ab80`로 삭제 판정.

## 공통 규칙·native 검증 계획

FR2·FR2b·FR3·FR4 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr5.cpp`, 함수 `animation_objects_fr5_block`. 오류 문자열은 `unsupported animation objects fr5 PC`(범위 안 내부 PC 직접 진입), `objects fr5 caller requires known carry`(C 소비 block에 Unknown C; 소비자 6개). 그 밖의 오류는 공용 bus/스택 오류다(`28ae` 실패 경로의 caller-X 제한 등 기존 checked 오류 그대로).
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(5 범위, FR4 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 6개, "carry"), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 범위 안이지만 다음 PC가 아닌 설치 쓰기 `5ac84`(`5ac7c`, 뒤는 `RTS`) `5ad66`(`5ad06`, 뒤는 `5ad0c`)는 `MOVE.L #v,(A6)`로 쓰기만 한다. `5ac94`의 `MOVE.L #5aca6,(A6)`도 쓰기만이고 같은 block의 `BRA.W 5aca6`가 `5aca6`로 간다. `5add2`의 `MOVE.L #5add8,(A6)`은 다음 PC라 들어간다(FR4 결정 4). 기존 시험이 stop으로만 보던 PC(`5ab82`: N13 `5ab3a` 행의 `28ae` 자식 값(stop은 `28ae`), `4464a`: B2e의 범위 끝 표시(`!in_ranges`만 확인))는 그대로 참이다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. 다른 단위·다음 단위가 routing할 코드(`5ab6c`, `5ae3e`, `5ae98`, `44666`, FR6 `50dae` 등)는 rollback 탐침으로 쓰지 않는다. dispatcher 오류 확인에 쓰는 범위 옆 PC는 TRAP `5ae0e`뿐이다(영원히 routing 밖).
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): FR2와 같다. 행의 run stop은 실패 block 바로 뒤 PC다.
- **자료 읽기**(live bus, 상한 검사 없음): bank 창 LONG `200190`(`5ab82` `5ad98`, LONG 자체를 WORD `22`에 저장; 따라가 읽지 않음). RAM 읽기: node field(A6), 부모 LONG `c(A6)`의 BYTE `61` `80`, WORD `84` `86`(`5acb0` `5ac1e` `5ace8` `5add8`), `4945e`가 돌려준 A0의 WORD `42`(`5abda`), 스택. callee에게 주소만 넘기는 ROM 자료: 상자 `5dc1a`(`1ab80`) `5dc22`(`4ae4a`), 표 `5ddde` `5de40`(`490ba`), anim 자료 `5cf10` `5cf3e`(`49f8c`의 A1), `28ae` 자식 `5ad98` `d1d08`. 단위 시험은 bank 창 `200190`과 상자 `5dc1a..5dc22`에만 합성 typed physical byte를 둔다(ROM 자료가 아니다; 코드 바이트와 겹치지 않음). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `5abfa`: `MOVEM.W D0-D1,-(A7)`(낮은 주소 D0.W) 뒤 `MOVE.L D2,-(A7)`(`1000000`), `JSR 4464a`; `5ac14`: `MOVE.L (A7)+,D1`; `5ac1e`: `MOVE.L D0,-(A7)`(몫); `5ac4a`: `MOVE.L (A7)+,D0`; `5ac56`: `MOVEM.W (A7)+,D0-D1`(D0 := sext(낮은 주소 WORD), D1 := sext(다음 WORD)). `5ae10`: `MOVE.L D2,-(A7)`, `CLR.L -(A7)`(64 bit 곱 누적, 높은 LONG이 낮은 주소), `ADD.L D2,2(A7)`(가운데 LONG), `ADDQ.W #1,(A7)`(넘침 올림), `ADD.L (A7)+,D1`, `MOVE.L (A7)+,D0`. `5b20e`: `MOVE.W D7,-(A7)` 뒤 `BSR.W 5aede`; `5b214`: `MOVE.W (A7)+,D7`(WORD만, 상위 유지). JSR/BSR 복귀 LONG. 홀수 A7은 checked 오류다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B`, `SUB.W` `SUBI.W` `ADD.W` `ADDQ.W` `ADDX.W` `LSR.W` `NEG.W` `CLR.W` `SUB.W D0,D0` `NOT.B`, `BSET`). `MOVEQ`는 LONG 전체. `MULU.W`는 두 하위 WORD의 무부호 곱 32 bit. `EXT.L`(WORD 부호 확장). `ASL.L #8`(LONG 왼쪽 이동, 결과는 LSL과 같음), `ASR.L #8`(부호 bit 복제). `NEG.L`(0 − x, X = C = (x ≠ 0)), `NEGX.L`(0 − x − X). `ADD.L D0,D0`(X = C = 옛 bit 31), `ADDX.W D1,D1`(WORD: 2·D1.W + X, X = 16 bit 올림), `ADDX.L D3,D3`(2·D3 + X, X = 32 bit 올림). 비교: `CMPI.W #ffc0,D0` + `BLE`(부호 WORD ≤ −`40`, 같으면 BLE), `CMP.W D0,D1` + `BLS`(무부호 WORD D1 ≤ D0, 같으면 BLS), `CMP.L D1,D0` + `BLE`(부호 LONG D0 ≤ D1), `CMPI.W #1200,8a(A6)` + `BLT`(부호 WORD < `1200`), `CMPI.W #0,D0` + `BNE`(WORD만), `CMP.L D3,D0/D1` + `BCC`(무부호 LONG ≥ `10000`), `CMP.L D3,D0/D1` + `BEQ`(= `10000`), `CMP.L D2,D3` + `BCS`(무부호 LONG D3 < D2), `ADD.L D2,2(A7)` + `BCC`(32 bit 올림), `TST.L`/`TST.W`/`TST.B` + `BPL`/`BMI`/`BEQ`, `BTST` + `BNE`. flag는 같은 block 안에서 만들고 소비한다(예외: "carry"의 callee C).

## carry

- [F] **소비 block 6개**(callee가 돌려준 C; Clear 쪽 / Set 쪽):
  - U11/N08 `4945e`(가까운 플레이어; `494a6`/`494ae` `ANDI` Clear, `494ba` `ORI` Set; FR1b 소비자 `5a58e`와 같은 생산자): `5abd6 BCS.W 5abe2`(`5abda` / `5abe2`).
  - B2a `4b6f4`(FR1a `4b700 RTS`가 넘기는 `TST.B 5b86(A5)`의 Clear / `ORI` Set): `5acac BCS.W 5ad66`(`5acb0` / `5ad66`).
  - U12 `1ab80`: `5ad60 BCS.W 5ad92`(`5ad64` / `5ad92`), `5ae02 BCS.W 5ae08`(`5ae06` / `5ae08`).
  - `28ae`(Set = 생성 성공): `5ad80 BCC.W 5ad92`(`5ad92` / `5ad84`).
  - `49fc6`: `5adf2 BCS.W 5ae08`(`5adf6` / `5ae08`).
- [F] **C를 넘기는 `RTS`: 없다.** 이 단위의 subroutine `4464a` `5ae10` `5ae54` `5ae66` `5aede` `5b1f8`의 모든 직접 호출자(ROM 전수: `4464a` 6곳, 나머지 1곳씩)는 복귀 뒤 C를 읽지 않는다(scratch `cread.py`; 단위 안 BSR 복귀 `5ae56 TST.L` `5ae92 MOVE.W` `5b214 MOVE.W`도 C를 읽지 않음).
- [F] **known C 생산 block**: `5ad8e ORI.B #1,CCR`(Set) 하나. 그 C는 `5ad92 JMP 2a00`이 받지만 `2a00`(삭제)은 C를 읽지 않는다(B4·FR3의 "ORI Set without a reader"와 같음). 그래서 carry 보존 목록에 넣지 않는다: `5ad8e`는 끝에서 Set이고 다음 block(`5ad92`)은 Unknown이 된다.
- [F] **읽는 곳이 없는 C**: node callback의 `RTS`(`5ac68` `5ad64` `5ae06`), helper `RTS`(`4465a` `44660` `5ae34` `5ae64` `5ae92` `5aed8` `5b1f6` `5b21e`).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 6개다: `5abd6` `5acac` `5ad60` `5ad80` `5adf2` `5ae02`. Unknown C로 소비자에 들어오면 checked 오류다.
- [F] flag 재계산(block 경계를 건너 다시 계산하는 flag)은 없다. X도 block 안에서 만들고 쓴다(결정 4).

## 객체 `5ab82`(첫 frame)

- **`5ab82`**(`28ae` 자식 값): WORD `20` := `183`, LONG `22` := LONG `200190`(bank 창), D0.W := `1a21`, `JSR 3af8`(복귀 `5ab9a`). **`5ab9a`**: `JSR 8ff4`(복귀 `5aba0`). **`5aba0`**: D0.W := `d42`, D1.B := 0, `JSR 8ebe`(복귀 `5abae`). **`5abae`**: A1 := `5cf10`, D0.W := `100`, `JSR 49f8c`(복귀 `5abbe`).
- **`5abbe`**: WORD `68` `1e` := `e0ef`, BYTE `15` bit 3 := 1, `JSR 4945e`(복귀 `5abd6`). **`5abd6`**(소비자): Clear → `5abda`, Set → `5abe2`. **`5abda`**: D0.W := WORD `42(A0)`(A0 = `4945e`가 돌려준 플레이어 기록), `BRA.W 5abea`. **`5abe2`**: D0.W := WORD `42` − `60`(WORD 안, fall-through `5abea`).
- **`5abea`**: D0.W −= WORD `42`, (부호) D0.W ≤ `ffc0` → `5abfa`, 아니면 `5abf6`: D0.W := `ffc0`.
- **`5abfa`**: D1.W := `120` − WORD `46`(WORD 안), WORD D0, D1 넣기(`MOVEM.W`, 낮은 주소 D0.W), D2 := `1000000`, LONG D2 넣기, `JSR 4464a`(복귀 `5ac14`).
- **`5ac14`**: D1 := 꺼낸 LONG(`1000000`), D0 := SWAP(D0) ∧ `ffff0000`(`SWAP; CLR.W`: 하위 WORD를 상위로), `JSR 5b1f8`(복귀 `5ac1e`).
- **`5ac1e`**: LONG D0 넣기, A0 := LONG `c`, BYTE `80(A0)` bit 1 ≠ 0 → `5ac3e`, 아니면 `5ac2e`: A0 := `5ddde`, `JSR 490ba`(복귀 `5ac3a`: `BRA.W 5ac4a`). **`5ac3e`**: A0 := `5de40`, `JSR 490ba`(복귀 `5ac4a`).
- **`5ac4a`**: D0 := sext(D0.W) << 8(`EXT.L; ASL.L #8`), D1 := D0, D0 := 꺼낸 LONG, `JSR 5ae66`(복귀 `5ac56`).
- **`5ac56`**: D2 := D0, D0 := sext(꺼낸 WORD), D1 := sext(꺼낸 WORD)(`MOVEM.W (A7)+,D0-D1`), D3.W := 0 뒤 D3.B := `70`(D3 상위 WORD 유지), `JSR d1028`(복귀 `5ac68`).
- **`5ac68`**: LONG `36` := D0, LONG `3a` := D1, LONG `90` := D2, LONG `94` := D3, WORD `8a` := 0, LONG `(A6)` := `5ac84`(쓰기만), `RTS`.

## 객체 `5ab82`(다음 frame부터: 설치 `5ac84`)

- **`5ac84`**(설치 값): LONG `36`의 N = 1 → `5ac9e`, 아니면 `5ac8c`: LONG `36` := 0, LONG `90` := 0, LONG `(A6)` := `5aca6`(쓰기만), `BRA.W 5aca6`. **`5ac9e`**: D0 := LONG `90`, LONG `36` += D0(fall-through `5aca6`).
- **`5aca6`**: `JSR 4b6f4`(복귀 `5acac`). **`5acac`**(소비자): Clear → `5acb0`, Set → `5ad66`. **`5acb0`**: A0 := LONG `c`, BYTE `61(A0)` bit 7 ≠ 0 → `5ad66`, 아니면 `5acbe`.
- **`5acbe`**: WORD `84` := WORD `1e`, D1 := LONG `94`, LONG `3a` += D1, D0 := ASR.L(LONG `36`, 8), D1 := ASR.L(LONG `3a`, 8), `JSR 4464a`(복귀 `5acde`). **`5acde`**: WORD `8a` += D0.W, `JSR 43ea4`(복귀 `5ace8`).
- **`5ace8`**: A0 := LONG `c`, D0 := WORD `86(A0)` << 16(`MOVEQ #0; MOVE.W; SWAP`), D1 := LONG `32`, (부호) D0 ≤ D1 → `5ad0c`, 아니면 `5acfe`: LONG `3a` := 0, LONG `32` := D0, LONG `(A6)` := `5ad66`(쓰기만; fall-through `5ad0c`).
- **`5ad0c`**: `JSR 49fc6`(복귀 `5ad12`; C는 읽지 않음). **`5ad12`**: (부호) WORD `8a` < `1200` → `5ad40`, 아니면 `5ad1c`: WORD `8a` −= `1200`, A0 := `5ad98`, D0.W := `1e`, `JSR 28ae`(복귀 `5ad32`; C는 읽지 않음). **`5ad32`**: D0.W := 0, D1.W := 0(`MOVE.W`: 상위 유지), `JSR 49214`(복귀 `5ad40`).
- **`5ad40`**: A0 := `5dc22`, `JSR 4ae4a`(복귀 `5ad4c`). **`5ad4c`**: D0.W ≠ 0 → `5ad66`, 아니면 `5ad54`: A0 := `5dc1a`, `JSR 1ab80`(복귀 `5ad60`). **`5ad60`**(소비자): Clear → `5ad64 RTS`, Set → `5ad92`.
- **`5ad66`**(폭발): D0.W := `1a21`, `JSR 3af8`(복귀 `5ad70`). **`5ad70`**: A0 := `d1d08`, D0.W := `1e`, `JSR 28ae`(복귀 `5ad80`). **`5ad80`**(소비자): Clear → `5ad92`, Set → `5ad84`: D0.W := 0, D1.W := 0(`CLR.W`), `JSR 4970a`(복귀 `5ad8e`). **`5ad8e`**: C := 1(`ORI.B #1,CCR`; fall-through `5ad92`). **`5ad92`**: `JMP 2a00`.

## 연기 자식 `5ad98`(+ 설치 `5add8`)

- **`5ad98`**(`28ae` 자식 값): WORD `20` := `183`, LONG `22` := LONG `200190`, `JSR 8ff4`(복귀 `5adac`). **`5adac`**: D0.W := `d42`, D1.B := 0, `JSR 8ebe`(복귀 `5adba`). **`5adba`**: A1 := `5cf3e`, D0.W := `100`, `JSR 49f8c`(복귀 `5adca`). **`5adca`**: LONG `36` := 0, LONG `3a` := 0, 설치 `5add8`(다음 PC라 들어감).
- **`5add8`**(설치 값): A0 := LONG `c`, WORD `84(A0)` −= 1, WORD `1e` := WORD `84(A0)`, `JSR 43e34`(복귀 `5adec`). **`5adec`**: `JSR 49fc6`(복귀 `5adf2`). **`5adf2`**(소비자): Clear → `5adf6`, Set → `5ae08`. **`5adf6`**: A0 := `5dc1a`, `JSR 1ab80`(복귀 `5ae02`). **`5ae02`**(소비자): Clear → `5ae06 RTS`, Set → `5ae08 JMP 2a00`.

## 근사 거리 `4464a`

- **`4464a`**: D0.W의 N = 0 → `44650`, 아니면 `4464e`: D0.W := −D0.W. **`44650`**: D1.W의 N = 0 → `44656`, 아니면 `44654`: D1.W := −D1.W. **`44656`**: (무부호) D1.W ≤ D0.W → `44660`, 아니면 `4465a`. **`4465a`**: D0.W := (D0.W >> 1) + D1.W(WORD 안), `RTS`. **`44660`**: D1.W := D1.W >> 1, D0.W += D1.W(WORD 안), `RTS`. (`NEG.W 8000` = `8000`이라 무부호 비교가 그 값을 가장 큰 값으로 본다; 상위 WORD는 그대로.)

## 고정소수점 곱셈 `5ae66`(+ `5ae54` `5ae10` `5aebe`)

- **`5ae66`**: D7 := 0, D3 := `10000`(`MOVEQ #1; SWAP`), D0의 N = 0 → `5ae76`, 아니면 `5ae72`: D0 := −D0, D7.B := ¬D7.B. **`5ae76`**: D1의 N = 0 → `5ae80`, 아니면 `5ae7c`: D1 := −D1, D7.B := ¬D7.B. **`5ae80`**: (무부호) D0 ≥ `10000` → `5ae90`, 아니면 `5ae86`: D1 ≥ `10000` → `5ae90`, 아니면 `5ae8c`: `BRA.W 5aebe`.
- **`5ae90`**: `BSR.B 5ae54`(복귀 `5ae92`). **`5ae92`**: D0.W := D1.W, D0 := SWAP(D0), `RTS`(D0 = 64 bit 곱의 가운데 32 bit).
- **`5ae54`**: `BSR.B 5ae10`(복귀 `5ae56`). **`5ae56`**: D1의 N = 1 → `5ae0e`(`TRAP #15` 경계, 결정 2), 아니면 `5ae5a`: D7.B = 0 → `5ae64 RTS`, 아니면 `5ae60`: D0 := −D0(X := D0 ≠ 0), D1 := 0 − D1 − X(`NEGX.L`; fall-through `5ae64`).
- **`5ae10`**(64 bit 무부호 곱 D1:D0 := D0 × D1): D2.W := D1.W, D2 := D2.W × D0.W(`MULU.W`), LONG D2 넣기, LONG 0 넣기, D2 := SWAP(D0) 뒤 D2 := D2.W × D1.W, LONG `2(A7)` += D2, 올림 없음 → `5ae26`, 있음 → `5ae24`: WORD `(A7)` += 1. **`5ae26`**: D1 := SWAP(D1), D2 := D0.W × D1.W, LONG `2(A7)` += D2, 올림 없음 → `5ae34`, 있음 → `5ae32`: WORD `(A7)` += 1. [F] 첫 올림(`5ae22` → `5ae24`)은 정적으로 불가능하다: 그때 LONG `2(A7)`은 `0000`:(lo × lo의 상위 WORD) ≤ `0000fffe`이고 더하는 값(hi × lo) ≤ `fffe0001`이라 합이 `ffffffff`를 넘지 않는다(`5ae24`는 직접 진입으로만 실행; V1 spec `STATIC_IMPOSSIBLE`). **`5ae34`**: D0 := SWAP(D0), D1 := D1.W × D0.W, D1 += 꺼낸 LONG, D0 := 꺼낸 LONG, `RTS`.
- **`5aebe`**(빠른 길; 자연 진입은 `5ae8c`에서만, 그때 D0, D1 < `10000`): D1 = `10000` → `5aed0`, 아니면 `5aec4`: D0 = `10000` → `5aeda`, 아니면 `5aeca`: D0 := D1.W × D0.W(`MULU.W`), D0.W := 0(`SUB.W D0,D0`), D0 := SWAP(D0)(fall-through `5aed0`). **`5aed0`**: D7.B = 0 → `5aed8 RTS`, 아니면 `5aed6`: D0 := −D0(fall-through `5aed8`). **`5aeda`**: D0 := D1, `BRA.B 5aed0`.

## 고정소수점 나눗셈 `5b1f8`(+ `5aede`)

- **`5b1f8`**: D7 := 0, D0의 N = 0 → `5b204`, 아니면 `5b200`: D0 := −D0, D7.B := ¬D7.B. **`5b204`**: D1의 N = 0 → `5b20e`, 아니면 `5b20a`: D1 := −D1, D7.B := ¬D7.B. **`5b20e`**: WORD D7 넣기, `BSR.W 5aede`(복귀 `5b214`). **`5b214`**: D7.W := 꺼낸 WORD, D7.B = 0 → `5b21e RTS`, 아니면 `5b21c`: D0 := −D0(fall-through `5b21e`).
- **`5aede`**: D0 = 0 → `5b1f6 RTS`(D0 = 0), 아니면 `5aee4`: D1 = 0 → `5ae0e`(`TRAP #15` 경계, 0 나누기), 아니면 `5aeea`.
- **`5aeea`**: D2 := D1(제수), D1 := SWAP(D0), D0 := SWAP(D0) ∧ `ffff0000`, D3 := 0, 그리고 반복 1회(아래 "반복").
- **반복**(48회 = `5aeea` 안 1회 + block `5af06 + 16·k`(k = 0..46) 47개): D0 := D0 + D0(X := 옛 bit 31), D1.W := D1.W + D1.W + X(X := 16 bit 올림; D1 상위 WORD 유지), D3 := D3 + D3 + X(32 bit), (무부호) D3 < D2 → 다음 반복 block(마지막은 `5b1f6`), 아니면 그 block의 `+12` block으로.
- **빼기 block** `5af02 + 16·k`(k = 0..47): D0.W += 1(WORD 안), D3 −= D2(LONG), fall-through 다음 반복 block(k = 47이면 `5b1f6`).
- **`5b1f6`**: `RTS`. [I] 결과: 48 bit 피제수 (|D0| << 16)를 |D1|로 나눈 몫의 하위 32 bit가 D0, 나머지가 D3(16.16 고정소수점 나눗셈).

## 경계·routing 밖 출구

- [F] 이 단위 안에는 live 대상 호출·계산 점프가 없다. 설치 쓰기의 범위 안 값(`5ac84` `5aca6` `5ad66`)은 다음 PC가 아니면 실행하지 않는다(`5aca6`는 같은 block의 `BRA.W`로 간다).
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 11개: `4465a` `44660` `5ac68` `5ad64` `5ae06` `5ae34` `5ae64` `5ae92` `5aed8` `5b1f6` `5b21e`.
- [F] **`TRAP #15` `5ae0e`**(결정 2): `5ae56`(곱이 부호 있는 범위를 넘음: D1의 N = 1)과 `5aee4`(0 나누기: D1 = 0)가 PC := `5ae0e`로 끝난다. `5ae0e`는 routing 밖이라 다음 dispatch가 `unsupported animation machine PC`(전체 rollback)를 낸다. 시험은 `5ae0e`를 stop으로만 확인한다(stop 판정이 routing보다 먼저).
- [F] **native 정지 규칙 주의**(V1): FR4 spec의 `first_unrouted`(`8c16 < pc <= 8ca6` 내부, 정지 `2a00` `2a24`, 홀수 live 정지 PC 버림)를 그대로 쓴다. `JMP 2a00`은 routing된 출구다. TRAP `5ae0e`은 routing 밖 첫 PC로 멈춘다(native가 TRAP을 실행하기 전).

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR4 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 자연 node, LONG `c(A6)` := 자연 node, 스택 WORD/LONG, PC).
- [I] IO 관측 상태가 이 단위의 실제 진입 상태다(`fr4/ioA/frontier.json`의 확정 frontier와 위 "자연 후속 확인"). V1 spec에는 이 출처를 주석으로 적고, IO 비교 재실행(검증 작업자)이 자연 경로를 직접 확인한다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `4945e` → `5abd6`(`5abbe`), `4b6f4` → `5acac`(`5aca6`), `1ab80` → `5ad60`(`5ad54`)·`5ae02`(`5adf6`), `28ae` → `5ad80`(`5ad70`), `49fc6` → `5adf2`(`5adec`). seed world에서 두 C 값이 다 나오도록 hint를 둔다: `4945e`(BYTE `568e(A5)` = 0 / ≠ 0), `4b6f4`(BYTE `5b86(A5)` = 0 / ≠ 0), `1ab80`(위치 WORD `42` `46`을 화면 안 / 밖), `28ae`(빈 node 목록 있음 / 없음 [I]), `49fc6`(LONG `26` = 0 / ≠ 0). 단위 시험은 RAM·합성 자료만 읽고 PVC port를 쓰지 않는 생산자만 실제 사슬로 넣고(생성기가 두 C 값을 모두 만들어 낸 것), 나머지는 선언 C 행만 둔다(V1·실제 ROM 차분이 실제 사슬).
- node fixture: callback·설치 값(`5ab82` `5ac84` `5ad98` `5add8`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `4464a` `5ae66` `5ae54` `5ae10` `5b1f8` `5aede`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, FR4 꼴): 시작 195개 × 들어오는 C 3가지, zero-step, 내부 PC 635개 정확한 오류, 경계 stop(출구 전부와 TRAP `5ae0e`), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), 그리고 빈틈 종류별 hint:
  - 부호·영 확장: `5ac4a` `EXT.L`(D0.W = `8000`/`7fff`, 상위 WORD 쓰레기), `5ac56` `MOVEM.W` 부호 확장(넣은 WORD `8000`/`7fff`), `5ace8` `MOVEQ #0; MOVE.W; SWAP`(WORD `86` = `8000`: 음의 LONG), `5b214` `MOVE.W (A7)+,D7`(상위 유지).
  - 음수 색인: 이 단위에는 색인 주소 지정이 없다(대신 음수 피연산자: `5ae66` `5b1f8`의 D0/D1 = `80000000` `ffffffff`, `4464a`의 `8000`).
  - `MULU` 상위 WORD: `5ae10` `5ae26` `5ae34` `5aeca`의 D0/D1 상위 WORD가 `0`이 아닌 값(곱에 쓰이지 않음), 최대 곱 `ffff × ffff`와 가운데 LONG 올림 두 번.
  - 꺼낸 레지스터: `5ac14` D1(LONG), `5ac4a` D0(LONG), `5ac56` D0/D1(WORD 부호 확장), `5ae34` D1/D0(LONG), `5b214` D7(WORD).
  - RAM 거울: node A6 = `1fe000`(거울 `10e000`), 부모 LONG `c` = 거울 주소, 스택 A7 거울 몇 행.
  - bit 조합: `5abbe` BSET #3(BYTE `15` = `00` `08` `f7` `ff`), `5ac1e` BTST #1(부모 BYTE `80` = `00` `02` `fd` `ff`), `5acb0` BTST #7(부모 BYTE `61` = `00` `7f` `80` `ff`).
  - 동점(같은 값): `5abea` BLE(D0.W − WORD `42` = `ffc0`/`ffc1`/`ffbf`, `7fff − ffff` = `8000`), `44656` BLS(D0.W = D1.W, ±1), `5ace8` BLE(D0 = D1, ±1, 부호 경계 `80000000`/`7fff0000`), `5ad12` BLT(WORD `8a` = `11ff`/`1200`/`1201`/`8000`), `5ae80` `5ae86` BCC(= `ffff`/`10000`/`10001`), `5aebe` `5aec4` BEQ(= `10000`), 나눗셈 반복 BCS(D3 = D2, D3 = D2 − 1), `5ae10` 올림(가운데 LONG 합 = `ffffffff`/`100000000`).
  - TST.W 대 TST.L 읽기 범위(bank 창 옆): `5ac84 TST.L 36(A6)`을 A6 = `1fffc8`(LONG `1ffffe..200001`이 bank 창으로 넘어감)에서 — 읽기 범위가 다르면 결과(성공/오류)가 달라진다(규칙, 정확한 오류 문자열). 레지스터 TST.W/TST.L(`4464a` `44650` `5ae56` `5ae66` `5ae76` `5aede` `5aee4` `5b1f8` `5b204`)은 상위 WORD와 하위 WORD의 부호·0이 다른 값(`00008000` `80000000` `00010000`).
  - 상위 레지스터 bit: `MOVE.W #imm,D0/D1`(`5ab82` `5aba0` `5ad1c` `5ad32` `5ad66` `5ad70` `5adac`), `MOVE.B #0,D1`(`5aba0` `5adac`), `CLR.W D3; MOVE.B #70,D3`(`5ac56`), `CLR.W D0/D1`(`5ad84`), `SUB.W D0,D0`(`5aeca`), `ADDQ.W #1,D0`(빼기 block: D0 = `xxxxffff`에서 WORD 안 넘침), `ADDX.W D1,D1`(D1 상위 유지), `LSR.W`/`ADD.W`(`4465a` `44660`), `NEG.W`(`4464e` `44654`), `MOVE.W D1,D0`(`5ae92`), `NOT.B D7`.
  - 큰 값: `5ac9e` `ADD.L` 넘침(LONG `36` = `7fffffff`), `5acbe` LONG `3a` + LONG `94` 넘침, ASR.L #8의 음수, `5acde` WORD `8a` 넘침, `5ad1c` `SUBI.W #1200` 넘침, `5add8` `SUBQ.W` 넘침(WORD `84` = 0), `5ae60` `NEG.L 0`(X = 0) 대 `NEG.L 1`(X = 1) 뒤 `NEGX.L`.

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `tools/probe_scan_fr5.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_fr5.out` 5줄)으로 확인한 결과:
  - 그대로 참인 것: B2e 시험(`RANGES` 끝 `4464a`, `ends[]`의 `4464a`는 `!in_ranges`(B2e 자기 범위 밖)만 확인), spec `b2e.py`(`RANGES` 끝; `unit_of(hi) != b2e` 확인은 FR5 뒤에도 참; 주석), N13 시험(`5ab3a` 행: `28ae` 자식 값 `5ab82`는 A0 값이고 stop은 `28ae`).
  - 옮길 것: 정적 검색에서는 없다. [I] `make -j3 all test`에서 깨지는 숨은 탐침이 나오면 결정 6대로 옮기고 이 절에 더한다.
- [I] V1 spec 중 native 사슬이 `4464a`(밖 호출자 `29150` `8bd74` `9071a` `9088a`가 routing된 단위에 있으면)나 `5ab82`를 첫 routing 밖 PC로 멈추던 것은 더 진행한다(정지는 routing에서 계산되므로 spec 수정은 필요 없을 것으로 본다; 검증 작업자가 회귀로 확인). `29150` `8bd74` `9071a` `9088a`는 현재 routing 밖이다 [F](scratch `inrefs.py`의 `routed_src=False`).
- [F] stage_event / stage_event_ops 검증기의 `CPP_PINS`(`animation_machine.cpp` `31a1b033…`, `animation_machine_internal.h` `8570d1e8…`)는 이 단위의 공유 수정으로 맞지 않게 된다(FR1..FR4 관례대로 검증 단계에서 새 값으로 갱신; 메인 결정, 새 값은 "구현·검증 기록").

## 결정

1. **범위.** FR5 = `5ab82` 묶음 + `4464a` **195 block** 단독(5 범위; 객체 55, 곱셈 26, 나눗셈 107, 거리 7). FR5 + FR6(`50dae` 105) = 300은 약 220을 넘고, `5ab82` 핵심을 잘라 `50dae`와 묶으면 `5ab82` run이 첫 frame 안에서 다시 멈춰 IO 진척이 거의 없다. FR6은 `50dae` 105 + FR7 앞부분(메인 결정)으로 한다. FR5의 3 run은 600 frame 끝까지 간다 [I].
2. **`TRAP #15` `5ae0e`.** 단위 범위에 넣지 않는다(`5ae0e..5ae10`). `5ae56`(곱 넘침)·`5aee4`(0 나누기)가 PC := `5ae0e`로 끝나고 다음 dispatch가 `unsupported animation machine PC`(전체 rollback)를 낸다. 형제 `5ae98`의 `BHI 5ae0e` 두 곳은 이 단위 밖이다. 계산 표는 이 단위에 없다(전사할 표 0).
3. **carry 보존 목록.** 소비자 6개(`5abd6` `5acac` `5ad60` `5ad80` `5adf2` `5ae02`). C를 넘기는 `RTS` 없음. `5ad8e`(ORI) Set은 읽는 곳 없음.
4. **X와 펼친 반복.** X는 block 밖으로 나가지 않는다(`ADD.L D0,D0`가 매 반복 block 첫 명령, `NEG.L`이 `NEGX.L` 바로 앞). 나눗셈 48회 반복은 원본 block 그대로 95 block(반복 47 + 빼기 48; 첫 반복은 `5aeea` 안)으로 두고 공용 함수 하나로 실행한다(block마다 원본 PC 그대로, 반복을 접지 않음).
5. **설치 값.** `MOVE.L #v,(A6)`은 v가 바로 다음 PC일 때만 그 block으로 들어간다(`5add8`). `5ac84`(뒤 `RTS`), `5ad66`(뒤 `5ad0c`), `5aca6`(뒤 `BRA.W 5aca6`)은 LONG 쓰기뿐이다.
6. **숨은 탐침 이전.** 정적 검색에서 이전 대상 없음. stage_event / stage_event_ops `CPP_PINS` 갱신은 메인이 검증 단계에서 정한다.
7. **TB 시작 PC.** IO 관측의 TB 시작 `5afe8` `5afea` `5afec` `5afee` `5aff8` `5affa` `5affc` `5affe`는 block 시작이 아니다(내부 PC 오류).
8. **다음.** 이 단위 뒤 D 첫 정지: `50dae`(FR6, 3 run, frame 271). 그 뒤 남은 첫 정지는 C/E `4e68e` 15와 C `1d1f4` 1뿐이다(예측 165,714).

## 미확인

- [U] node field 의미(BYTE `15` `61` `80`, WORD `1e` `20` `42` `46` `68` `84` `86` `8a`, LONG `22` `32` `36` `3a` `90` `94`), BYTE `568e(A5)` `5b86(A5)`, 표 `5ddde` `5de40` `5dc1a` `5dc22` `5cf10` `5cf3e` 값의 의미, `d1028`이 돌려주는 D0..D3의 뜻.
- [U] 물리 `300000` bank에서 bank 창 LONG `200190`의 쓰임.
- [U] `5ae3e` `5ae98` 형제 진입과 `5ab6c` 상태의 실행 조건(IO 관측에서 실행되지 않음).
- [U] 자연 frame에서 이 단위 뒤 run별 다음 첫 미routing PC(IO 비교 재실행으로 확인; [I] 예상은 결정 1·8).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr5.cpp`(case label 195 = scratch `starts_fr5.txt`와 집합 일치; 나눗셈 반복은 공용 함수 `ofr5_divide_step`, 빼기 block은 한 case 묶음), `engine/tests/animation_machine_objects_fr5_test.cpp`(생성 구역 + 수작성 규칙: `5ae10` 64 bit 곱(상위 WORD는 SWAP으로만), 부호 반전 `NEG.L`/`NEGX.L`(X 0/1), 곱 넘침과 0 나누기의 TRAP `5ae0e` stop-only, `5ae24` WORD 넘침, `5ae66` 느린 길·빠른 길·`10000` 입력, `5ae80`/`5ae86` 무부호 BCC와 동점, `5aebe`/`5aec4` BEQ 동점, `5aeca` MULU.W / SUB.W / SWAP, `5b1f8` 몫·나머지(1/3, −1/2, 5/3, `500000`/`1000000`), `5aede` D0 = 0, `5b214` WORD pop, 나눗셈 반복의 BCS 동점·ADD.L X·ADDX.W 올림, 빼기 block의 ADDQ.W WORD 넘침과 SUB.L 빌림, `4464a`의 `NEG.W 8000`·BLS 동점·LSR.W 무부호·TST.W 하위 WORD, `5abea` 부호 비교와 BLE 동점(동점에서 `5abf6`에 들어가지 않음), `5abe2` SUBI.W 넘침, `5abfa` 넣는 순서, `5ac14`/`5ac4a`/`5ac56` 꺼내기·EXT.L·ASL.L·MOVEM.W 부호 확장·CLR.W + MOVE.B, `5ac84` TST.L 읽기 범위(A6 = `1fffc6` 성공, `1fffc8` bank 창으로 넘어가 `missing or ambiguous physical program bus ROM byte`), `5ac9e` ADD.L 넘침, `5acbe` ASR.L, `5ace8` 영 확장·부호 BLE·동점·착지, `5ad12` 부호 BLT 동점, `5ad4c` WORD 비교, `5add8` SUBQ.W 넘침, `5ac1e` BTST #1, `5abbe` BSET, `5ab82` bank 창 LONG, TRAP PC `5ae0e`의 dispatcher 오류), `tools/generate_animation_machine_objects_fr5_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀, `mirror`(node `1fe000`)·`parent_mirror`(부모 `1feb00`) hint 추가; 두 번 실행해 시험 파일 바이트 단위 같음 SHA256 `0302f9c1397854778976e1939da1c1d3e580fc439b1e200fbccd4c9fc12c6697`, 약 65초), `tools/unit_fixture_specs/fr5.py`(V1 spec; FR4 spec의 공용 부분 그대로, 단위 부분 교체: 부모 field BYTE `61` `80`·WORD `84` `86`, BYTE `1d` < 4(`8ebe`/`8ff4`의 TRAP #15 `8ec8` 회피), BYTE `568e(A5)` `5b86(A5)`, `mirror`/`parent_mirror` hint, `STATIC_IMPOSSIBLE` `(5ae22, 5ae24)`, TRAP `5ae0e` 경계 오류 행). 공유 수정은 "공통 규칙"의 다섯 곳뿐이다(기존 시험·spec의 이전 없음).
- [F] 정적 spec 검사(scratch `spec_static.py`): `load_routing` 규칙 126개 뒤 시작 195개와 내부 635개가 모두 `animation_objects_fr5_block`, sentinel·TRAP `5ae0e`은 routing 밖, 정적 후속은 시작이거나 routing된 출구(routing 밖 출구는 `5ae0e`뿐), 사슬 6개의 소비자가 진입에서 닿음, block 명령 합 584. 합성 기반 상태와 가짜 tracer로 world·hint·error·chain/node/callee 생성 함수를 native 없이 실행(scratch `spec_dry.py`): Python 오류 0, world 1,002, 오류 fixture 657개(내부 635 + 홀수 1 + Unknown C 6 + 홀수 node/stack 3 + TRAP 경계 2 + 실행 뒤 실패 4 + failpc 짝 6) 이름 중복 0.
- [F] 단위 시험 world: A7 = `10ef00`, 합성 typed physical byte(ROM 자료 아님, 자료 영역만): bank 창 LONG `200190`(값 `2a7a5c`, 따라가지 않음), 상자 `5dc1a..5dc22`(`ffc0 ffe0 0080 0080`). 생성기가 실제 생산자 사슬을 두 C 값 모두로 만들어 남긴 것: `4945e` → `5abd6`, `4b6f4` → `5acac`, `1ab80` → `5ad60`·`5ae02`, `28ae` → `5ad80`(선언한 빈 node `10f400`, WORD `104ca0` ≤ `1e`이면 Clear). `49fc6` → `5adf2`는 `49fc6`이 PVC bank port를 써서 버려졌고 선언 C 행만 있다(V1·실제 ROM 차분이 실제 사슬). 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block `5ae10 → 5ae24` 하나(정적으로 불가능, 위 `5ae10` 절).
- [F] `make -j3 all test`(작업자, scratch `make_all1.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 278개, Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR5 시험 줄: `animation machine objects fr5: 1003 fixtures (849 single-block, 96 path, 30 producer chain, 12 declared C, 16 checked error (6 with a later failing PC), 43 kept C), 195 blocks, 4860 calls, 99474 checks`. FR4 최종 기준(scratch `fr4/make_all3.log`) 대비 다른 시험 줄 변화는 없다(이전이 필요한 기존 시험 없음).
- [F] `dleft.py`(이 worktree routing `7641c2d9…`): 실행된 routing 밖 PC D 371 / E 220 / C 620, D 중 C 무관 24 / C 뒤 347, 예측 일치 **164,727**, 첫 정지 영역 D 3(`50dae`) / C·E 15 / C·D 1.
- [F] 검증 작업자 준비물(scratch, 실행하지 않음): `build_ubsan.sh`, `mut/run_mut.py`·`mut/mutants.py`(변이 194개; 패턴 유일성 확인, `--check`는 문법 검사까지 통과), `realrom/real_fr5.py`(FR4 harness에 FR5 world·소비자·진입, TRAP `5ae0e`을 선언된 stop `UNR`로, FR4 표 항목은 `UNR_FR4`로 계속 선언; `py_compile`만), `runwrap.py` `run_frames.sh` `run_area_clear.py` `run_stage_entry.py` `run_regs.sh`(회귀 목록에 `fr4` 추가) `v1_all.sh` `v1_one.sh` `io_ab.sh` `io_delta.py`(FR4 재실행 `fr4/ioA` 대비) `legacy/`(경로만 바꿈). 실행 순서와 기대값은 scratch `HANDOFF.md`.
- [F] stage_event / stage_event_ops `CPP_PINS` 새 값(메인이 검증 단계에서 갱신): `animation_machine.cpp` `7641c2d9f54068ee2c4308c516bea495bc4392fd0107b3f85b584de5fedcf337`, `animation_machine_internal.h` `fcef64db27191d5aa06fd75a83d3cf1fd9a989aaeddcc9870ae9f803a223009f`.

## 검증 기록(검증 작업자, Sonnet 5.5 / medium)

모든 명령은 `MS5_SEED_DIR=artifacts/stage_entry_body`, 출력은 scratch `/Users/start/Workspce/ms5-scratch/fr5/`. ROM 불변.

- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310 OK, FR5 줄 `1003 fixtures ... 195 blocks, 4860 calls, 99474 checks`. UBSan(`build_ubsan.sh`): 종료 0, `runtime error` 0, 같은 FR5 줄.
- [F] **변이 194개**: 첫 실행 192 killed. 생존 2개: (a) `5b214-word-test`(TST.B를 TST.W로 바꿈) = 시험 틈. `5b214` hint 행의 D0가 `80000000`(자기 자신의 NEG.L)이라 `5b21c` 경유와 `5b21e` 직행이 D0로 구별되지 않았다. 수정: `tools/unit_fixture_specs/fr5.py` `hint_worlds()` `5b214` 행 D0 `80000000` -> `1`(생성기 재실행, 시험 파일 변경 10줄). 재실행에서 killed. (b) `5ae10-d2-long`(`MOVE.W D1,D2; MULU.W D0,D2` -> `MULU.W D0,D1`의 D2 := D1 x D0) = **동치**: `ofr5_mulu`가 두 피연산자를 WORD로 가르고 결과가 D2 전체를 덮으므로 D2 상위 WORD가 결과에 영향이 없다(`MULU.W`는 상위 무시, 곱 32 bit가 D2 전체를 대체). 수정 뒤 전체 재실행: **killed 193 of 194 + 동치 1 = 194**.
- [F] 수정 뒤 `make -j3 all test` 다시(종료 0, 경고 0, 같은 FR5 줄), UBSan 다시(종료 0, runtime error 0).
- [F] real-ROM 차분 5 x 1,500(s1 s2 s3 f4 f5): 각 mismatches 0, covered starts 195/195. harness 수정 없음.
- [F] V1 `fr5` 2회(수정 뒤): 각 1,656 fixture, ok 1,656, failed 0, `carry oracle ok`, `visited 195/195`, 누락 후속 [] / 닿지 않는 결과 [], 두 report의 [(name,digest)] 동일. 회귀 spec 27개(fr4 1,629 / fr3 1,458 / fr2b 1,761 / fr2 1,592 / fr1 1,631 / fr1b 1,441 / fr1c 1,755 / b2a 1,386 / b4 1,830 / b4b 1,723 / b1a 2,801 / b1b 1,892 / b1c 1,842 / b2b 1,419 / b2c 1,707 / b2d 1,485 / b2e 1,054 / b3a 1,468 / b3b 1,360 / b3c 625 / c1 1,741 / c2 1,607 / c3b 480 / d9 26 / f6a 320 / f6b 726 / f6c 1,538): 모두 failed 0, 개수가 FR4 기준과 같다.
- [F] 프레임: D1 54,400/54,400, controller game 54,400/54,400, IRQ 54,400/54,400, demo 45,684/45,684, natural mismatches 0(바뀐 frame 없음).
- [F] `CPP_PINS` 갱신(메인 결정): stage_event / stage_event_ops 두 검증기를 `animation_machine.cpp` `7641c2d9...` / `animation_machine_internal.h` `fcef64db...`로(옛 값 `31a1b033...` / `8570d1e8...`는 주석). 이후 stage_event 560 / 22,870 / 1,020, ops 284 / 5,081 / 894, frame_helpers 199 / 3,683 / 180, card_menu_close 82 / 7,886 / 85, objects_g1 4,752 행 rc 0, stage_entry 335 / 23,761 / 2,757 / carry 21,829/100/1,832, area_clear 256 / 37,418 / 117,537 / 181 / guards 26 모두 통과.
- [F] **IO 비교**(2회 동일: verification.json `fcc09ca6b2f43555`, frontier.json `6e8d4113b257a947`): compared 173,966, **matched 164,727**(FR4 163,350 + 1,377 = 예측과 정확히 같음), mismatched 0, cpp_errors 0, P0 81,600 그대로, P1 +918, P1b +459, 나머지 설정 변화 0. 정지(frontier) run 24 -> 21: `5ab82` 3 run이 사라지고 남은 것은 `4e68e` 15, `50dae` 3, `1d1f4` 1, fixture `2634` 2. `dleft.py`: D 502 -> **371**(C 무관 24, C 뒤 347), 첫 정지 D 3 / C·E 15 / C·D 1.
- 변경 파일: FR5 파일 + `tools/unit_fixture_specs/fr5.py`(위 hint 1줄) + 시험 파일 재생성 + stage_event / stage_event_ops 핀 두 줄.

## block 목록

[F] scratch `starts_fr5.txt`(SHA256 `5ad39ca4bdb048ceaa1d7f2c5917b78a2a5dc0902599953894d219b36e4f9d64`)와 같다.

- **`4464a..44666`(7)**: `4464a 4464e 44650 44654 44656 4465a 44660`
- **`5ab82..5ae0e`(55)**: `5ab82 5ab9a 5aba0 5abae 5abbe 5abd6 5abda 5abe2 5abea 5abf6 5abfa 5ac14 5ac1e 5ac2e 5ac3a 5ac3e 5ac4a 5ac56 5ac68 5ac84 5ac8c 5ac9e 5aca6 5acac 5acb0 5acbe 5acde 5ace8 5acfe 5ad0c 5ad12 5ad1c 5ad32 5ad40 5ad4c 5ad54 5ad60 5ad64 5ad66 5ad70 5ad80 5ad84 5ad8e 5ad92 5ad98 5adac 5adba 5adca 5add8 5adec 5adf2 5adf6 5ae02 5ae06 5ae08`
- **`5ae10..5ae3e`(5)**: `5ae10 5ae24 5ae26 5ae32 5ae34`
- **`5ae54..5ae98`(14)**: `5ae54 5ae56 5ae5a 5ae60 5ae64 5ae66 5ae72 5ae76 5ae7c 5ae80 5ae86 5ae8c 5ae90 5ae92`
- **`5aebe..5b220`(114)**: `5aebe 5aec4 5aeca 5aed0 5aed6 5aed8 5aeda 5aede 5aee4 5aeea`, 빼기 block `5af02 + 16·k`(k = 0..47: `5af02` … `5b1f2`), 반복 block `5af06 + 16·k`(k = 0..46: `5af06` … `5b1e6`), `5b1f6 5b1f8 5b200 5b204 5b20a 5b20e 5b214 5b21c 5b21e`
