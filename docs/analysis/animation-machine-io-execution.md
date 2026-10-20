# 입력·스테이지 진행(단위 IO-2) C++ 비교와 frontier 기록

**상태: 구현·검증 기록(IO-2). 커밋하지 않았다.** IO-1 관측기 기록은 `animation-machine-io-observation.md`, 범위·메인 결정은 `input-stage-progress-observation-scope.md`(이하 범위 문서)다. 이 문서는 범위 문서 §6(C++ 비교와 frontier)·§8(IO-2)의 구현 기록이다.

- 작성: Sonnet 5.5 / medium 작업자. 작업 트리 `metalslug-io`(브랜치 `claude/input-observation`, 기준 HEAD `a16719f`).
- 표기: [F] 이 도구가 실행해 확인한 사실, [I] 추론, [U] 미확인.
- 모든 비교는 선언 모델이다. BIOS 실행, 자연 IRQ 시점, 자연 scheduler를 주장하지 않는다. host 쓰기·장치 값·IRQ 전달·BIOS 반환은 관측(IO-1)의 선언이고, 이 도구는 그 기록을 그대로 쓴다.
- 원본 ROM과 추출 자료는 수정하지 않았고 Git에 넣지 않는다(시작·끝에 SHA256·mtime_ns 불변 assert). `engine/src`·`engine/include`는 바꾸지 않았다. 바꾼 것은 Makefile 4줄(§2)과 새 파일 3개뿐이다.

## 1. 요약

- [F] **Execute + IRQ + palette 조합의 첫 원본 비교다.** 관측 296개 실행(S `P0` 137, `P1` 137, `P1b` 14, B 3, fixture 5)의 native 완료 frame 173,966개를 native frame 시작 상태에서 C++ 한 packet(`step_animation_machine_frame` / `run_animation_machine_pass`, controller Execute, `irq_execution`, palette RAM)으로 실행해 비교했다. **불일치 0, 예기치 않은 C++ 오류 0**이다(§4).
- [F] **P0 대조(입력 없음) 136 seed × 600 frame = 81,600 frame이 전부 일치한다.** 신규 routing 없이 게임 mode `c7fc`→`c79a` 경로와 frame당 2회 IRQ가 원본과 같다.
- [F] **P1(선언 player start + `walkfire`)에서 52 seed가, P1b 14개 중 13개가, B 3구성이, `fx-start-c79a`가 C++ 미routing PC에서 실패한다.** 모두 `unsupported animation machine PC`이고, 첫 실패 frame의 PC를 `stop = P` 방식으로 확정했다(미확정 0, 후보 1개째에서 전부 확정). 고유 frontier PC는 비-fixture 14개이다(§5).
- [F] **순수 C++ 연쇄**(frame k는 C++ frame k-1의 출력 + 선언 host 쓰기 + native 소비 queue에서 시작)는 296개 실행 140,930 frame 전부 실제 호출로 실행했고(재사용 0), 첫 C++ 실패 frame까지 native 시작 digest와 모두 같다(발산 0). native가 멈춘 guard frame 9개 중 6개는 선언한 checked 오류 + 상태 보존으로 짝을 이룬다(나머지 3개는 그 frame에서 미routing PC가 먼저 나와 보류, §6).
- [F] 검증기를 서로 다른 출력 폴더에 두 번 실행해 `verification.json`·`frontier.json`의 SHA256이 같고 `diff -rq`(`harness_stderr`·`run_info.json` 제외)가 깨끗하다. `make -j4 all test` 종료 코드 0.
- 범위 문서와 다른 점은 §8.

## 2. 구현 파일

| 파일 | SHA256 앞 16자리 | 내용 |
| --- | --- | --- |
| `engine/tools/frame_io_acceptance.cpp` | `269b700773819553` | harness. `frame_irq_acceptance.cpp`에 controller Execute 옵션과 구간 단독 실행(mode 4)을 더한 packet |
| `tools/verify_animation_machine_io.py` | `c25f4a78aba7cfde` | 검증기와 frontier 보고 |
| `Makefile` | `9f12a36393c164f1` | `all: build/frame_io_acceptance`와 그 규칙(4줄 추가). `ANIMATION_MACHINE_SOURCES`·`ANIMATION_MACHINE_HEADERS`는 한 줄씩 그대로다 |

- **harness packet**(길이 접두 BE u32): mode 0 = `run_animation_machine_pass`, mode 1 = `step_animation_machine_frame`, mode 4 = 구간 하나(`run_animation_frame_segment`, palette·IRQ 포함, 구간 번호와 stop PC를 요청에 담음). 요청은 D0~D7/A0~A7, PC, carry, bank base, 상태 byte, 옵션(card 재개 `0x80`, controller Execute, `irq_execution`, palette), IRQ 값(Z80 0, video 0), palette 선택, RAM 64 KiB, PVC page, palette bank 2개, 선언 external-read queue를 담는다. 성공 응답은 최종 상태·구간별 port·대기·IRQ 기록·IRQ port·남은 queue이고, 실패 응답은 오류 문자열과 "RAM·상태·장치·palette가 그대로인가"이다. 형식 설명은 파일 머리 주석에 있다.
- **queue 공급:** C++가 queue를 자기 순서로 소비한다. 공급하는 것은 native가 H·C·N에서 소비한 기록(`q`)이고, 응답의 남은 queue가 비어야 일치다.
- 검증기 CLI: `.venv/bin/python tools/verify_animation_machine_io.py [--observation DIR/observation.json] [--out DIR] [--workers 3] [--no-build] [--configs ...] [--cases ...] [--max-frames N] [--reuse-chain] [--no-negatives] [--seed-dir PATH]`. `--out` 기본값은 `build/animation_machine_io_execution`이고 공유 `artifacts/` 아래는 거부한다. 빌드는 `make build/frame_io_acceptance`를 호출한다(`--no-build`로 생략).
- `--seed-dir`/`MS5_SEED_DIR`: 다른 frame 검증기와 같은 선택자다. 관측의 seed pin(`1f65100f…`, historic)과 SHA256이 다르면 오류이고, seed는 그 밖에는 읽지 않는다(frame 시작 상태는 관측의 상태 pack에 있다).

## 3. 입력 pin과 방법

- 입력: `artifacts/animation_machine_io_native`(관측기 run A의 읽기 전용 사본). `observation.json` 파일 SHA256 `66d30130d8a11a86…`(전체 `66d30130d8a11a86d9cd3dc723c61882602359702009acc37e85a563739c1fce`), `compared_sha256` `4bb6b93362747427…`을 둘 다 pin한다. 관측기 파일 SHA256이 `observation.json`의 `pins.observer`와 다르면 시작하지 않는다. 각 실행의 기록(`runs/*.json.gz`)과 상태 pack(`states/*.pack.gz`)은 `observation.json`의 SHA256(압축 전)과 대조하고, pack의 모든 frame 시작 상태 digest가 기록의 `start`와 같음을 assert한다.
- 이 도구는 native를 실행하지 않는다. native 쪽은 기록된 관측이다(frame 시작 상태, 소비 기록 `q`, 선언 host 쓰기, digest, port digest, IRQ 기록, 대기, guard).
- ROM 자원은 `common.resource_audit`(`verify_animation_machine.py`)로 `extracted/runtime/program_rom`의 8개 `.ms5d`를 ROM 바이트와 대조한다. 엔진 소스·헤더·harness 바이너리·라우팅 파일 SHA256을 `verification.json`의 `inputs`에 기록한다.

### 3.1 frame별 비교(native 시작 상태에서)

frame 0은 `run_animation_machine_pass`, frame k ≥ 1은 `step_animation_machine_frame`을 native frame 시작 상태(선언 host 쓰기 적용 후, §8-2)와 `q`로 실행한다. 일치의 정의(모두 같아야 한다):

- 최종 상태 digest(범위 문서 §5.5 정의: D0~D7/A0~A7, PC, bank base, ff8/ff9, 상태 byte, RAM 64 KiB, PVC page, palette bank 2개와 선택). 불일치 시 다음 frame의 기록 상태(host 쓰기를 되돌린 것)가 있으면 첫 차이(레지스터·PC·bank·RAM 주소·PVC·palette)를 기록한다.
- H·C·N 구간의 순서 있는 port(개수와 SHA256; `MOVE.L 3c0000` 분할 형태는 §8-5).
- IRQ 기록(구간, 대기 PC, 순번, 외부 읽기 수, BIOS 재개 수, RTE가 꺼낸 SR)과 IRQ마다의 port(개수·SHA256), IRQ port 총수.
- 대기(card `c00468`의 구간·PC·주소·답 `0x80`).
- 외부 읽기: 합 = `q` 길이 + native 상태 byte 읽기 수, queue 완전 소비.
- head PC / controller PC / controller 종료 callback / pass 정지 PC, carry Unknown.
- native가 끝나지 못한 frame(guard)은 §6의 표대로 C++가 checked 오류를 내고 상태를 보존해야 한다.

### 3.2 순수 C++ 연쇄

frame 0은 native 시작 상태에서, frame k ≥ 1은 C++ frame k-1의 출력에 선언 host 쓰기를 적용한 상태에서 시작한다. queue는 native 소비 기록이다. 각 연쇄 frame은 실제 harness 호출이다(`--reuse-chain`을 쓰지 않은 기본 실행; 140,930회). 연쇄 시작 digest를 native 시작 digest와 비교해 발산을 기록한다(0건). 연쇄는 첫 C++ 실패 frame에서 끝나고, native guard frame이면 그 실패가 선언한 오류인지 확인한다.

### 3.3 frontier 위치 확정(`check_fail_pc` 방식)

frame F에서 native는 끝났는데 C++가 `unsupported animation machine PC`로 실패하면, 후보 P를 native 기록에서 구한다: `unr_first`(실행 순서상 첫 미routing TB PC), 그다음 그 frame에 처음 나온 미routing PC(`unr_new`), 그다음(guard frame 등 key frame) 실행 TB 시작 주소. 확정 조건은 `check_fail_pc`와 같다: ① P가 짝수이고 dispatch chain 평가기(`verify_animation_machine_unit_fixtures.pc_routed`)로 routing 밖, ② 같은 frame을 H·C·N 구간별로 실행하고 P를 포함한 구간을 `stop = P`로 실행하면 성공하고 정확히 P에서 끝난다. 앞 구간이 실패하면 확정이 아니다. 확정 시 P 진입 시 LONG(A7)(호출자 복귀), A6와 LONG(A6)(node callback)를 기록한다. [I] 실패 PC 이전에 도달 가능한 미routing 후보는 실패 PC 하나뿐이므로(먼저 도달하면 그 PC에서 실패한다) 첫 확정 후보가 곧 frontier다.

## 4. 결과: 구성별 비교

"비교 frame"은 native가 완료한 frame이다. 일치는 첫 실패 전, "frontier"는 첫 실패(미routing)한 frame 수, "뒤 일치/뒤 미routing"은 첫 실패 뒤 frame을 native 시작 상태에서 따로 실행한 결과이다(C++가 성공하면 일치해야 한다; 불일치 0).

| 구성 | 실행 | 비교 frame | 일치(첫 실패 전) | frontier | 뒤 일치 | 뒤 미routing | 불일치 | 완주 실행 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P0` | 137 | 81,600 | 81,600 | 0 | 0 | 0 | 0 | 136 (+ case 141 frame 0 `odd-pc` guard) |
| `P1` | 137 | 81,600 | 56,469 | 52 | 6,657 | 18,422 | 0 | 84 (+ case 141 guard) |
| `P1b` | 14 | 8,400 | 2,511 | 13 | 2,010 | 3,866 | 0 | 1 |
| `boot-demo-0` | 1 | 577 | 2 | 1 | 2 | 572 | 0 | 0 (frame 577 `rom-write` guard 보류) |
| `boot-title-idle` | 1 | 600 | 2 | 1 | 0 | 597 | 0 | 0 |
| `boot-title-start` | 1 | 906 | 2 | 1 | 121 | 782 | 0 | 0 (frame 906 `system-return` guard 일치) |
| `fx-start-c79a` | 1 | 273 | 265 | 1 | 0 | 7 | 0 | 0 (frame 273 `system-return` guard 일치) |
| `fx-bios-call` | 1 | 3 | 3 | 0 | 0 | 0 | 0 | guard frame 3 일치 |
| `fx-queue-short` | 1 | 1 | 1 | 0 | 0 | 0 | 0 | guard frame 1 일치 |
| `fx-n-input-read` / `fx-c-input-read` | 2 | 6 | 6 | 0 | 0 | 0 | 0 | guard frame 3 보류(미routing `2634`) |
| 합계 | 296 | 173,966 | 140,861 | 69 | 8,790 | 24,246 | **0** | |

- [F] 모든 실패는 `unsupported animation machine PC`이고(24,315건), 다른 C++ 오류는 0건이다.
- [F] C++ 연쇄는 첫 실패 frame까지 140,861 frame을 일치시켰고 발산 0이다. 연쇄 종료 사유: 전체 완주 221(P0 136 + P1 84 + P1b 1), C++ 미routing 실패 69, native guard frame 도달 6(P0·P1 case 141 `odd-pc`, `fx-bios-call`, `fx-queue-short`, `fx-n/c-input-read`; 마지막 둘은 보류).
- [F] 첫 실패 frame과 native 첫 미routing frame은 비-fixture 68개 실행 모두 같다. fixture `fx-start-c79a`만 다르다(C++ 265, native 245): native 첫 미routing 245는 기준선 PC `3900`(P0에도 있고 C++가 처리)의 근사 효과이고, C++의 265는 `a8ee`(c79a menu의 start 처리 이후)이다.
- [F] P0 136 seed의 C++ 완주는 Execute + IRQ 조합의 첫 원본 비교로, 입력 소비 순서·IRQ(frame당 2회)·palette까지 일치한다.

## 5. frontier

`frontier.json`(`format ms5-io-frontier`)에 실행별 frontier, PC별 집계, root별, 영역별, 후보 단위가 있다. 영역은 주소 기준(C = `1b000..23fff`·`4e4c0..4f3ff`, E = `de000..df3ff`·`e6400..e6fff`·`c000..cbff`·`<1400`, 나머지 D) [I]이고, root는 call·포인터 대상 중 PC 이하 `0x1000` 이내 가장 가까운 것(IO-1 `an5.py` 규칙) [I]이다. 정적 closure는 분기 + JSR/BSR + fall-through이고 routing된 PC에서 멈춘다(포인터는 따라가지 않음).

### 5.1 확정 frontier PC(비-fixture)

| frontier PC | 구간 | frame | 실행 수 | 구성 (seed) | 영역 | 호출자 복귀 LONG(A7) | node callback LONG(A6) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `de660` | N | 2 | 9 | P1 94 95 100 101 106 107 110 111, P1b 94 | E | `2ac2` | `de660` |
| `de660` | N | 222 | 5 | P1 68 69 70 71, P1b 68 | E | `2ac2` | `de660` |
| `b3dbc` | N | 99 | 12 | P1 0 1 127..135, P1b 0 | D | `2ac2` | `b3dbc` |
| `e5324` (root `e4ffc`) | N | 100 | 12 | P1 90 91 118..126, P1b 90 | D | `2ac2` | `e5324` |
| `5a376` | N | 133 | 3 | P1 16 17, P1b 16 | D | `2ac2` | `5a376` |
| `bc08c` | N | 167 | 3 | P1 22 23, P1b 22 | D | `2ac2` | `bc08c` |
| `4b6f4` | N | 181 | 3 | P1 32 33, P1b 32 | D | `5f5e6` | `5f57c` |
| `b975e` | N | 120 | 3 | P1 44 45, P1b 44 | D | `2ac2` | `b975e` |
| `eb9ba` | N | 24 | 3 | P1 58 59, P1b 58 | D | `eb84e` | `eb81e` |
| `d131a` (root `d0fec`) | N | 327 | 3 | P1 60 61, P1b 60 | D | `4a43e` | `c6218` |
| `b30f6` | N | 120 | 3 | P1 72 73, P1b 72 | D | `2ac2` | `b30f6` |
| `b7742` | N | 273 | 3 | P1 80 81, P1b 80 | D | `2ac2` | `b7742` |
| `51602` | N | 143 | 3 | P1 84 85, P1b 84 | D | `50da0` | `50d6a` |
| `de024` | N | 2 | 1 | boot-demo-0 | E | `2ac2` | `de024` |
| `de376` | N | 2 | 2 | boot-title-idle, boot-title-start | E | `2ac2` | `de376` |

- [F] 비-fixture 68개 실행의 frontier는 모두 N 구간이고 후보 1개째에서 확정됐다. fixture: `fx-start-c79a` frame 265 N `a8ee`(start 이후 menu 처리, [I]), `fx-c-input-read`/`fx-n-input-read` frame 3 `2634`(합성 callback 자체가 미routing).
- [F] P1의 84 seed는 600 frame 완주(새 code 없음, P0와 같은 결과)이다. 새 code가 열리는 52 seed의 첫 PC는 위 표의 13종이고, 플레이어를 만드는 12 seed는 `de660` frame 2·222(새 게임 시작)에서 먼저 막힌다.
- [I] C 영역(플레이어)이 첫 frontier인 실행은 없다. 그 앞에서 E(`de660`, 캐릭터 선택 객체)·D 코드가 먼저 나오므로, 플레이어 root(`4e94e`, `1cd98` …)는 E 단위를 routing한 뒤에야 frontier가 된다.

### 5.2 영역별 root(상위, 정적 closure)

관측의 새 미routing PC(P0 기준선 제외)를 root로 묶은 값이다(frontier가 확정된 비-fixture 실행의 합). S 계열(P1·P1b)만 보면 root는 C 61 / D 226 / E 41로 IO-1 탐침(328개)과 같다. B 계열을 더한 전체는 C 81 / D 270 / E 56이다. "frontier"는 그 root가 첫 frontier인 실행 수, "실행"은 native 실행 횟수이다.

| 영역 | root | frontier | 실행 | 미routing PC | 실행(seed) 수 | closure leader / 명령 / 바이트 |
| --- | --- | --- | --- | --- | --- | --- |
| E | `de660` | 14 | 60 | 4 | 15 | 50 / 136 / 642 |
| E | `de376` | 2 | 18 | 8 | 3 | 17 / 40 / 160 |
| E | `de024` | 1 | 5 | 5 | 1 | 29 / 91 / 388 |
| E | `de8bc` | 0 | 79,773 | 3 | 15 | 3 / 3 / 14 |
| E | `df15e` | 0 | 48,563 | 17 | 15 | 30 / 77 / 318 |
| E | `dec8c` | 0 | 45,897 | 10 | 15 | 12 / 26 / 116 |
| D | `e4ffc` | 12 | 11,267 | 79 | 12 | 3 / 17 / 40 |
| D | `b3dbc` | 12 | 300 | 3 | 25 | 1 / 5 / 16 |
| D | `4b6f4` | 3 | 32,046 | 2 | 9 | 3 / 4 / 14 |
| D | `d0fec` | 3 | 1,785 | 50 | 27 | 7 / 23 / 60 |
| D | `b30f6` | 3 | 27 | 1 | 3 | 45 / 101 / 432 |
| D | `768b6` | 0 | 100,100 | 35 | 25 | 47 / 137 / 640 |
| D | `b4958` | 0 | 85,983 | 15 | 25 | 108 / 298 / 1,064 |
| D | `c01a8` | 0 | 53,760 | 17 | 25 | 138 / 375 / 1,386 |
| C | `4e94e` | 0 | 81,630 | 45 | 15 | 502 / 1,226 / 4,654 (포인터 31, 미해결 2) |
| C | `1cd98` | 0 | 58,472 | 22 | 14 | 45 / 106 / 428 |
| C | `21688` | 0 | 33,725 | 82 | 14 | 1 / 13 / 46 |
| C | `215e6` | 0 | 28,363 | 5 | 14 | 5 / 10 / 28 |
| C | `4e732` | 0 | 27,911 | 23 | 15 | 502 / 1,226 / 4,654 (`4e94e`와 같은 closure) |

(`runs`열의 15/25는 B 3구성을 포함한 실행 수이다.)

### 5.3 후보 단위

같은 영역에서 한 root의 직접 closure 안에 다른 root가 있으면 한 단위로 묶었다. 순위는 frontier 실행 수, 그다음 native 실행 수이다. 전체는 196개 단위(C 9, D 147, E 40)이고 상위는 다음과 같다. 단위 계약에서 다시 확인해야 하는 근사 [I]다.

| 순위 | 영역 | 대표 root | root 수 | frontier | 실행 | 실행 seed | union closure leader / 명령 / 바이트 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | E | `de660` | 6 (`ca42` `de660` `de686` `de754` `de778` `de814`) | 14 | 8,857 | 15 | 54 / 136 / 642 |
| 2 | D | `e4ffc` | 1 | 12 | 11,267 | 12 | 3 / 17 / 40 |
| 3 | D | `b3dbc` | 1 | 12 | 300 | 25 | 1 / 5 / 16 |
| 4 | D | `b30f6` | 32 | 3 | 57,732 | 3 | 46 / 101 / 432 |
| 5 | D | `4b6f4` | 1 | 3 | 32,046 | 9 | 3 / 4 / 14 |
| 6 | D | `d0fec` | 1 | 3 | 1,785 | 27 | 7 / 23 / 60 |
| 7–12 | D | `eb9ba` `51602` `b7742` `5a376` `b975e` `bc08c` | 각 1 | 3 | — | — | 각 6~16 leader |
| 13 | E | `de376` | 1 | 2 | 18 | 3 | 17 / 40 / 160 |
| 14 | E | `de024` | 1 | 1 | 5 | 1 | 29 / 91 / 388 |
| 16 | C | `4e94e` | 23 | 0 | 211,014 | 15 | 513 / 1,245 / 4,754 |
| 18 | C | `1cd98` | 42 | 0 | 134,245 | 16 | 1,494 / 3,363 / 14,302 |
| 15 | D | `b4958` | 8 | 0 | 247,288 | 25 | 138 / 375 / 1,386 |
| 17 | E | `de8bc` | 10 | 0 | 197,708 | 15 | 78 / 196 / 828 |
| 19 | D | `768b6` | 1 | 0 | 100,100 | 25 | 47 / 137 / 640 |

[I] 권고 순서: E의 `de660` 단위(frontier 14, 캐릭터 선택·새 게임 객체) → D의 `e4ffc`·`b3dbc`(자동 카메라 계열 stage event) → 그 뒤에 C의 플레이어(`4e94e` 단위, `1cd98` 단위)와 D의 공통 적(`b4958`, `768b6`, `c01a8`). 단위는 계약 문서에서 closure를 다시 확정한다.

## 6. native guard → C++ checked 오류 대응

`NATIVE_END_ERROR`(검증기 상수, 정확한 문자열)이다. guard frame은 native 시작 상태와 `q`로 C++를 실행해 오류가 같고 상태가 보존돼야 한다. 근거 열의 "native 짝"은 관측의 guard frame과 같은 frame에서 확인한 것, "C++ fixture"는 같은 완료 frame(P1 case 0 frame 5)의 RAM LONG 1개를 바꿔 만든 C++ 단독 확인이다.

| native guard | C++ 오류 | 확인 |
| --- | --- | --- |
| `system-return` (C의 BIOS `c00444`) | `animation frame controller system return` | native 짝: `boot-title-start` frame 906, `fx-start-c79a` frame 273 일치 |
| `external-read-queue-empty` (H) | `animation machine external read queue empty` | native 짝: `fx-queue-short` frame 1 일치 |
| `bios-boundary` (BIOS 창, 선언 밖) | `unsupported animation machine PC` | native 짝: `fx-bios-call` frame 3 일치 |
| `odd-pc` | `unaligned animation machine PC` | native 짝: P0·P1 case 141 frame 0 일치 |
| `rom-write` | `unsupported animation machine write device` | C++ fixture: LONG `10081c` := `100` → 오류 일치·상태 보존. native 짝(B demo frame 577)은 frame 2의 미routing(`de024`) 뒤라 보류 |
| `undeclared-device-read` (N 또는 C의 입력 port 직접 읽기) | `animation machine external read queue empty` | C++ fixture: N = LONG `100bf4` := `31d6`, C = LONG `1008e4` := `349c` → 오류 일치. native 짝(`fx-n/c-input-read` frame 3)은 합성 callback `2634` 자체가 미routing이라 보류 |
| `irq:bios-int1` | `animation irq bios int1 boundary` | C++ fixture: BYTE `10fd80` &= `7f` → 오류 일치. native 짝 없음 |
| `wait-not-released` / `irq:internal-wait` / `irq:regs-differ` / `irq:undeclared-read` / `fetch-unmapped` | `animation irq wait not released` / `animation irq internal wait` / `animation irq register restore mismatch` / `animation irq external read overrun` / `animation fade card odd JSR target` | 문자열은 엔진 소스·IRQ·D1 검증기에서 가져옴. 자연 실행·합성 fixture에서 한 번도 발생하지 않아 [U] 미확인 |

- [F] guard 6개(P0·P1 case 141 `odd-pc`, `fx-bios-call`, `fx-queue-short`, `fx-start-c79a`, `boot-title-start`)는 native 시작 상태 실행과 연쇄 모두 선언한 오류 + 상태 보존으로 일치했다. 보류 3개(`boot-demo-0` `rom-write`, `fx-n/c-input-read`)는 미routing PC가 먼저 걸려 `unsupported animation machine PC`가 나오며, 그 PC(`de024`, `2634`)는 frontier로 확정했다.
- 이 대응표는 기존 D1·controller·IRQ 검증기의 표에 `rom-write`·`undeclared-device-read`·`system-return`·`bios-boundary`·`irq:*`·`external-read-queue-empty`를 더한 것이다.

## 7. 반복성과 부정 검사

- **반복성:** 서로 다른 출력 폴더(`ms5-scratch/io3/runA`, `runB`)에 같은 명령을 두 번 실행. `verification.json` SHA256 `6abcb3ad62920d47…`와 `frontier.json` SHA256 `8b5493a55a2e7279…`가 같고 `diff -rq -x harness_stderr -x run_info.json`이 깨끗하다. 시간·경로·PID는 `run_info.json`(비교 제외)에만 있다. 한 번 실행에 약 4분(3 worker).
- **부정 검사 34건**(P1 case 0 frame 5, 전부 검출): RAM 1바이트, palette 1바이트, queue 값·순서(교환)·개수(부족·초과), IRQ 실행 끄기·Z80 값·video 값, palette 미부착, controller skip, 선언 host 쓰기 누락(연쇄 시작 digest가 native와 달라짐)과 선언 쓰기의 native 일치, 결과 위조 15종(RAM·레지스터·PC·PVC·palette 바이트/선택·IRQ 삭제/SR/port 값·node port 값·H/C port 삭제·대기 삭제·남은 queue·controller 종료 PC·carry), 기록 digest 불일치, 잘못된 요청(harness 비정상 종료)·잘못된 응답(거부), 위 guard C++ fixture 4개.
- **빌드·회귀:** `make -j4 all test` 종료 코드 0(로그 `ms5-scratch/io3/make_all_test.log`). harness는 `make all`에서 함께 빌드된다. 기존 frame 검증기(D1, controller, IRQ, head)와 0267 manifest 회귀는 이 작업이 `engine/src`·기존 도구를 바꾸지 않으므로 영향이 없다(재실행하지 않음) [I].

## 8. 범위 문서와 다른 점, 의도적 차이

1. **`compared_sha256` 재계산 불가 — 수정됨 [F].** 이전 관측(`3cc9adbb…`)은 메모리 객체(정수 키)를 정렬해 해시해, JSON 왕복 뒤(문자열 키, 사전식 정렬)의 재계산값 `dd9c5d50…`과 달랐다. 관측기는 이제 `compared_sha256`을 키를 뺀 객체의 JSON 왕복에 대해 계산하고(`recompute_compared_sha`), `--compare`와 이 검증기가 `observation.json`에서 재계산해 저장값과 같음을 요구한다. 새 관측(`ms5-scratch/io2fix/runA`=`--workers 3`, `runB`=`--workers 2`)은 `compared_sha256` `4bb6b933…`(재계산 일치), 파일 SHA256 `66d30130…`이고 `diff -rq -x platform.json`이 깨끗하다. 이전 관측과는 `compared_sha256` 값과 `pins.observer`(관측기 파일이 바뀜)만 다르다. 공유 `artifacts/animation_machine_io_native`는 새 run A로 교체했고 이전 것은 `artifacts/animation_machine_io_native.old_3cc9`에 남겼다.
2. **H에서 멈춘 guard frame의 시작 상태에는 선언 host 쓰기가 아직 없다.** 관측기는 H가 끝난 frame의 `start`를 쓰기 뒤에, H에서 멈춘 frame(`fx-bios-call` frame 3, `fx-queue-short` frame 1)은 쓰기 앞에 담는다. 검증기는 기록된 쓰기(RAM이 `old`이면 `new`로)를 적용한 시작 상태를 쓴다(`effective_start`; 쓰기가 이미 적용된 상태는 그대로). 같은 주소에 쓰기 여러 개(P1b의 `10f006`)는 처음 `old`·마지막 `new`로 합친다.
3. **구간별 digest·IRQ 전후 digest 비교 없음.** C++ packet은 frame 최종 상태와 기록(port·IRQ·대기)을 돌려주고 중간 상태는 주지 않는다. native `H.end`/`C.start`/`C.end`/`N.start`와 IRQ `pre`/`post` digest는 비교하지 않았다(최종 상태 digest, 구간별 port SHA256, IRQ 기록·port SHA256, 연쇄로 대신 덮는다). 구간 단독 실행(mode 4)은 frontier 확정에만 쓴다.
4. **외부 읽기는 합으로 비교.** native는 H·C·N 소비 목록을 이어 붙인 `q`만 남기므로 구간별 분할은 비교하지 않는다. 총 읽기 수 = `q` 길이 + native 상태 byte 읽기 수, queue 완전 소비, 순서는 C++의 front 일치 검사("mismatch"/"empty" 오류)가 보장한다.
5. **`MOVE.L 3c0000` port 분할.** native는 `4fcce`/`4fcda` 계열에서 이 쓰기를 WORD 쌍(`3c0000` hi, `3c0002` lo)으로 기록하고 그 밖에서는 LONG 하나로 기록한다. native에는 port 개수·SHA256만 있으므로, 검증기는 C++ port를 평문 / 전체 쌍 / 연속한 `3c0000` LONG 구간(길이는 개수 차이로 결정)을 쌍으로 바꾼 형태 중 digest가 같은 것을 찾는다(이전 frame의 구간 위치를 먼저 시도). 비교 frame 중 N 구간 전체 쌍 4,009회, 구간 쌍 93회가 이 형태였다. 구간 여러 개가 섞인 형태는 지원하지 않고 port 불일치로 보고한다(발생 0). [I] SHA256 일치이므로 잘못 일치할 가능성은 무시할 만하다.
6. **frontier 근사 범위.** 후보는 native 기록의 근사 routing bitmap(IO-1 정의)에서 나온다. `pc_routed`(정확한 dispatch chain)와 C++ `stop = P`로 확정하므로 순위 외의 영향은 없다. 비-fixture 68개 모두 후보 1개째(`unr_first`)가 확정 PC였다.
7. **fixture frontier.** `fx-*`는 frontier 집계(PC별·root별·단위)에서 제외하고 실행별 목록에만 표시한다.
8. **대응표 [U].** `irq:internal-wait`/`regs-differ`/`undeclared-read`/`wait-not-released`/`fetch-unmapped`의 C++ 오류 문자열은 발생 사례가 없다.

## 9. 미확인

- [U] B demo frame 577 `rom-write`와 N/C 입력 직접 읽기의 native 짝: 앞 단위(E의 `de024`, 합성 callback `2634` 계열)를 routing한 뒤에야 같은 frame에서 확인된다.
- [U] 구간별·IRQ 중간 digest 비교(§8-3), 구간별 읽기 분할(§8-4).
- [U] IRQ 장치 값(`320000` = 0, `3c0006` = 0), card 답 `0x80`, 선언 player start, 입력 스크립트의 실제 BIOS 대응(IO-1 §12와 같음).
- [U] 영역 C/D/E 분류와 root·단위 묶음은 주소·정적 closure 근사다.
- [U] `compared_sha256` 재계산 불일치 원인(§8-1).
- [U] 다른 플랫폼 재생성은 하지 않았다(macOS arm64, Unicorn은 이 도구가 쓰지 않는다).

## 10. 재현

작업 트리 루트에서(`.venv` 사용):

```sh
make build/frame_io_acceptance                      # 또는 make all
.venv/bin/python tools/verify_animation_machine_io.py \
  --observation artifacts/animation_machine_io_native/observation.json \
  --out /Users/start/Workspce/ms5-scratch/io3/runA --workers 3
# 두 번째 폴더에 같은 명령을 실행해 비교
diff -rq -x harness_stderr -x run_info.json /Users/start/Workspce/ms5-scratch/io3/runA /Users/start/Workspce/ms5-scratch/io3/runB
```

| 산출 | SHA256 앞 16자리 |
| --- | --- |
| `verification.json` (run A = run B) | `6abcb3ad62920d47` |
| `frontier.json` (run A = run B) | `8b5493a55a2e7279` |
| harness 바이너리 `build/frame_io_acceptance` | `4b85ac1cb2795db8` |

산출물(`verification.json`, `frontier.json`)은 Git 대상이 아니다. `engine/src/animation_machine.cpp`(routing) SHA256 `8ce8eb93…`, ROM SHA256 `29112a94…c886c860f`는 관측과 같다.
