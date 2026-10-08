# HUD·BCD와 상위 활성화의 실제 stack 실행 검증

Baseline `24d13ff`. [확정 계약](animation-machine-hud-contract.md)에 따라 `4e286`, `4843c`, `8cda`, `35f0`와 상위 `47c6c`의 원본 실행을 공개 animation-machine API에 연결했다. 입력은 통제된 합성 fixture이며 자연 scheduler에서의 도달, 실제 플레이나 전체 stage 완료를 뜻하지 않는다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 이 문서의 fixed CPU 주소는 같은 ROM 파일 offset이다. C++ harness는 원본 파일을 직접 읽지 않고 실제 MS5D v1 kind3 여덟 개를 기존 loader/bus로 읽는다. ROM hash와 수정 시각은 실행 전후 보존됐다.

## 실제 관측 범위

HUD gate, `99ff/9a00` 경계, raw nibble 0..15, counter BYTE와 sound wait, 팔레트 reference/target/weight/dirty, BCD source0 대표 입력, rectangle의 WORD/BYTE wrap과 상위 register bits를 관측했다. 전체 `[4e272,4e292)`의 16 WORD 읽기 주소가 실제 trace에 나타났다. 이 32byte의 SHA256은 `095633d24bf3730eff7bc16f1f39975b01599421b749480b2ad6b8e30859bdda`다. 일부 WORD는 코드 bytes이며 16개의 논리적인 digit이라고 판정하지 않는다. BCD의 이전 exhaustive 검증·외부 hardware reference는 별도 pin된 근거이고, 이번 대표 입력 관측이 모든 65536쌍 재검증을 대신하지 않는다.

Sound와 palette 호출 전 WORD D0 저장, 실제 JSR의 LONG return 저장, live WORD pop, 첫 rectangle 뒤 WORD pop과 두 번째 rectangle tail JMP를 공유 RAM A7로 실행했다. 사운드 대기 중 host가 저장 WORD를 `0f01`로 바꾸면 원본이 실제 복원하는 값도 바뀐다. 임시 별도 stack이나 RAM diff mask를 사용하지 않는다. 상위 흐름은 HUD 후 counter를 다시 읽고 BSR `4843c`, JSR `ca70`, live source/status 조회를 순서대로 거쳐 `47eac/47d24` 또는 기존 활성화·readiness로 간다.

정상 native는 HUD 64조건, BCD 30조건, palette 12조건, rectangle 6조건, upper 12조건으로 124조건이다. 정상 split 277단계와 fresh continuous control 138단계, 별도 guard 3조건의 split/control 각 3단계를 기록했다. 조건마다 split 두 번과 control 두 번으로 fresh CPU 508회·단계 실행 842회다. 검증기는 127조건의 split/control 전 단계를 원본으로 다시 실행해 전체 16register/PC, RAM/PVC 전후, trace, ordered ports 및 checkpoint snapshot payload를 대조했다. 중간 checkpoint에서 멈춘 실행과 연속 실행의 전체 PC/event/host-change 순서 및 RAM/PVC/register snapshot이 일치한다.

원본에 ROM patch·stub·실행 시작 후 register 주입이나 SR 읽기는 없다. Carry는 일반적으로 관측하지 않는다. Readiness까지 간 upper 조건은 실제 `47d42:6400002e` BCC의 successor `47d72`(Clear)/`47d46`(Set)에서만 역으로 판정한다. 중간 반환 경계의 tag도 뒤이은 실제 분기 결과를 근거로 삼으며 host SR이나 C++ 출력을 oracle로 사용하지 않는다.

## C++ 대조와 실패 검사

실제 C++은 정상 124조건·277단계를 모두 일치시켰다. 직전 실제 출력으로 이어간 재개 153회, 대기 14단계, known carry 비교 12단계, ordered port 756개(video 732개·PVC 24개), external status read 0회다. 재개 입력은 직전 C++ RAM/16register/PC/carry/PVC/bank 출력과 기록된 host RAM 변경만 사용한다. Native incoming 값은 assertion이며 다음 입력으로 주입하지 않는다. API wait의 Unknown carry도 확인했다. 기존 strict 22-key harness 형식은 유지한다.

새 로컬 fold helper는 native event 순서대로 video write와 독립 PVC fold의 결과를 합친다. 기존 공통 `fold_device`는 변경하지 않았다. Video `3c0000`의 LONG은 size4 한 건, 최종 WORD는 size2 한 건이며 `>BII` 9byte 레코드로 기록한다. PVC는 기존 WORD 단위 모델을 유지한다. 이는 원본 명령의 접근 단위이며 16bit 물리 bus cycle 수나 VRAM/pixel 결과의 검증을 뜻하지 않는다.

Native guard 3개는 정상 완료와 분리한다. A7=`104e62`의 palette alias에서 target WORD write가 실제 JSR return `0004e2f0`을 `00040a0d`로 바꾸고 native는 지원 밖 odd target에서 멈춘다. C++은 같은 초기 fixture를 `unaligned animation machine PC`로 거부하고 palette·stack을 포함한 전체 API 출력을 보존했다. 나머지는 원본 rectangle TRAP 경계와 upper odd WORD 접근이다. Native의 부분 변경은 관측 근거로 보존하며 CPU fault rollback과 API rollback의 동등성을 주장하지 않는다.

추가 checked failure 12개는 gate device, counter write 뒤 odd WORD push, palette write 뒤 잘못된 live RTS, 첫 video write 뒤 TRAP, zero height의 실제 WORD 감소 후 TRAP, rectangle ports 뒤 잘못된 RTS, 지원 밖 live A4, BCD 두 BYTE write 뒤 잘못된 RTS, odd saved WORD pop, Unknown readiness branch, palette와 첫 rectangle 뒤 두 번째 digit WORD 누락, 전체 upper prefix 뒤 지원 밖 stop을 검사한다. RAM/register/PC/carry/PVC/bank/ports/read count/status 보존을 확인했다. 누락 lookup은 `[4e276,4e278)`만 비우고 다른 원본 bytes를 보존한 기존 kind3 조각을 사용한다. 원본 데이터나 pointer를 성공시키기 위해 바꾸지 않는다. 세 checkpoint `4e2f0/4e312/47c80`에서 각 valid carry enum의 zero-step 9개도 입력 보존을 확인했다. 이 증거는 OS 저장의 원자성을 뜻하지 않는다.

## 동결 근거와 재현

| 파일 | SHA256 |
| --- | --- |
| `tools/observe_animation_machine_hud.py` | `715b9631674bf3a5cafa13b9254d45398448de6ac67f891376fac63d3a1619fe` |
| `artifacts/animation_machine_hud_native/observation.json` | `41408a8aa9f6f47468632aca987db6f8fb773660ae2e78b4990a0545ff536a72` |
| `tools/verify_animation_machine_hud.py` | `715e52b014bab1af7bc4bf723a020ffc161e682c559eeb3b4c9a294c27085282` |
| `tools/verify_animation_machine.py`의 SOURCES 추가 후 | `c77866127c68924f785251c4123d115142e6ff2e4339e2fa1b3ddb52e3850a2b` |
| `artifacts/animation_machine_hud_execution/verification.json` | `ddfa3e768c229bee082c7321579236670fbef75e14a7da4b846226210c269d91` |

Native 71 input·3083 artifact의 3154개 참조를 검사했다. 새 보고서는 62 input·4975 artifact 문자열 참조, 정규화 후 4990개 고유 경로를 기록한다. 실행 전에 Python/local imports, C++ translation units/재귀 headers, unit source, compiler/runtime, 실제 리소스·manifest, native 관측 및 생성 harness/binary를 pin하고 종료 시 다시 검사한다. Observer와 verifier는 시작 시 이전 성공 보고서를 지운다.

저장소 root에서 원본과 기존 runtime 리소스를 준비해 실행한다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_hud.py
.venv/bin/python tools/verify_animation_machine_hud.py
.venv/bin/python tools/verify_animation_machine.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_carry.py
.venv/bin/python tools/verify_animation_machine_activation.py
.venv/bin/python tools/verify_animation_machine_readiness.py
make -j4 all test
```

새 harness는 자기 artifact 폴더에서 C++11 `-O2 -Wall -Wextra -pedantic`로 경고 없이 빌드됐다. 메인의 `/tmp/ms5-machine-hud-make.log`는 `make all test` exit 0, Python 257개·C++ 155개·경고 0개를 기록한다. 새 HUD unit은 담당 작업자의 isolated normal/UBSan에서 1283 API invocation을 통과했다. Native 독립 감사는 60조건·split 132단계·continuous 74단계와 전체 대기 14단계·guard 3개를 재현했다(`/tmp/ms5-hud-native-independent-review.txt`). Source/core 및 새 verifier의 독립 리뷰와 4990개 현재 참조 해시 감사에는 추가 결함이 없었다. 근거는 `/tmp/ms5-hud-core-independent-review.txt`, SHA256 `9da356037989e3c3ce425fc8e68945fd7ddd53f73428fa677532c5b48577fc6f`이다.

기존 다섯 verifier도 새 core와 common source 목록으로 한 번씩 재실행해 모두 exit 0을 확인했다. Native 관측 파일은 변경하지 않았다.

| 회귀 보고서 (`artifacts/*_execution/verification.json`) | 실제 대조·실패 검사 | SHA256 | 고유 참조 경로 |
| --- | --- | --- | --- |
| `animation_machine` | base 8조건·chain 2단계, extended 85조건·121단계, negative 9개 | `ec26d29e69a54bb93121af0f3c651ee628a1838c77f012996421a88fd1b0558c` | 1709 |
| `animation_machine_callers` | 59조건·91단계·32재개, negative 6개 | `b673a46a7b88c4bb31563062afa80b6493fb8107605cfa3136a313f4bf408573` | 1235 |
| `animation_machine_carry` | 60조건·160단계·100재개, negative 10개·zero-step 3개 | `ba24cf0e425d2fa506fef9f2a6e00d667ebe475a8dd11bf43274962916837dec` | 3044 |
| `animation_machine_activation` | 52조건·74단계·22재개, negative 9개 | `e3d59b40f4cfd5188f44b2fd4e27620b7c1e7c1aacf8bf9d6f680f3b36151f38` | 1038 |
| `animation_machine_readiness` | 68조건·154단계·86재개, negative 14개·zero-step 3개 | `8c334f1bdd20338a9f5657b021ceea3196d8f12995142159a9ffd5adc2838f6f` | 2977 |

새 HUD 보고서와 위 다섯 보고서의 모든 input/artifact 참조를 현재 파일로 다시 hash 검사해 일치시켰다. 표의 고유 경로 수는 각 보고서 안의 상대·절대 경로를 정규화한 수이며 보고서 사이에는 공통 입력이 있으므로 합산한 고유 파일 수를 뜻하지 않는다. 감사 기록은 `/tmp/ms5-hud-final-reference-audit.json`이다.

## 남은 범위

Native 지도는 bank2, 16개 coherent RAM mirror와 제한된 PVC/video/external 접근을 사용하고 범위 밖 접근을 guard한다. 다른 bank의 원본 실행, 임의 callback/device, video readback·VRAM 상태·pixel, IRQ/timing, 일반 CCR/XNZV, `47eac/47d24/47d46/47d72` 이후 명령과 자연 scheduler·전체 stage 복원은 이번 완료 범위에 포함하지 않는다.
