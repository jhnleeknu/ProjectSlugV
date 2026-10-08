# 상위 stage 활성화의 공유 stack 실행 검증

후속 readiness의 공유 stack·실제 carry 분기 연결은 `animation-machine-readiness-execution.md`를 따른다. `93b5b40` 이후47d20→47d3e→4847c→47d42를 연결했다. 아래 수치와 지원 경계는 각 이전 단위의 기록이며 최신 구현 상태와 구분한다.

Baseline `6c90612`. [확정 계약](animation-machine-activation-contract.md)에 따라 원본 `16ea4`, `16ed2`와 실제 `47cae` 진입부터 `47d20` 경계까지를 공개 animation-machine API와 대조했다. 입력은 통제된 합성 fixture이며 자연 scheduler에서의 도달을 입증하지 않는다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 이 문서의 fixed CPU 주소는 같은 파일 offset이다. 원본 파일의 내용과 수정 시각은 실행 전후 보존됐다. C++ harness는 원본 파일을 직접 읽지 않고 기존 MS5D v1 kind3 여덟 개를 실제 loader와 program bus로 읽는다.

## 실제 실행 범위

상위 경로는 좌표와 sprite WORD를 쓰는 `47cae`에서 시작해 `47cc0→16ed2`, `47cc6→47672`, `47ce6→16ea4`의 실제 JSR/RTS와 기존 `47cec` 이후 initializer `49f8c` 및 animation `49fc6`을 실행한다. Return LONG은 공유 work RAM에 쓰며 RTS는 그 시점 live RAM에서 읽는다. `16ea4` 끝의 `16ecc→cd58`은 JMP이므로 wrapper return을 추가하지 않는다.

`16ea4`는 A5를 `108000`, D3를 0으로 만들고 object flag BYTE를 D2.low에 읽는다. 두 SWAP/WORD ADD 뒤 각각 LSR.B가 만든 원래 bit0/bit1을 SUBX.W에서 사용한다. D0 WORD 계산은 modulo65536이다. D2.high24, D5.high16와 D7 보존은 `cd58` 진입 전 wrapper prefix의 계약이다. 이후 callee는 D7과 다른 register를 합법적으로 바꿀 수 있으며, callee를 포함한 최종 전체 register 결과는 원본과 대조했다. Callback은 clip 판단보다 먼저 실행된다. `16ed2`는 live 두 WORD를 signed16으로 비교하고 object+15 bit2를 변경하며, flag나 source/return이 alias하는 fixture도 포함한다.

`47cca`는 live object+7e BYTE를 D0에 넣고 ADD.W 두 번으로 4배한 뒤 `[48a12,48e12)`에서 LONG을 읽는다. 이는 raw 조회 가능 span이며 논리적인 256항목 table이라는 판정은 아니다. 이번 원본 관측은 서로 다른 source high BYTE 여덟 개의 조회를 확인했고 전체 BYTE domain의 자연 유효성을 주장하지 않는다.

## 관측과 C++ 대조

동결된 native 관측은 sprite wrapper 25조건, signed flag helper 11조건, 상위 chain 16조건으로 총 52조건·74단계다. 각 조건을 fresh CPU 두 번으로 실행했고, 검증기는 다시 전 조건·전 단계를 원본으로 재실행해 저장된 16register/PC, RAM/PVC 전후, trace와 ordered ports 여섯 payload를 대조했다. 원본 코드 patch, stub, 실행 시작 후 register 주입과 SR 읽기는 없다.

실제 C++ 대조는 52조건·74단계, ordered PVC write 636개, external status read 0회이며 모두 일치했다. 22회 재개는 직전 **실제 C++** RAM/16register/PC/carry/PVC/bank 출력에 native 기록의 host RAM 변경만 적용했다. Native incoming state는 assertion이며 다음 C++ 입력으로 대입하지 않는다. Device PVC와 bank는 원본 ordered write를 독립 모델로 fold해 비교한다.

대기에는 object·queue·saved stack을 바꾼 hold/release와 같은 CPU의 sound high→low→wrapper sprite wait→animation sprite wait 연결이 포함된다. 마지막 mixed 조건은 9단계 후 실제 `47d20`에 도달한다. 이미 끝난 wrapper의 좌표 계산이나 callback을 대기 재개 때 반복 실행하지 않는지도 trace와 전체 상태로 확인했다. Native에는 carry oracle이 없으므로 일반 완료 carry의 하드웨어 일치를 주장하지 않는다. 실제 C++ carry는 재개 때 전달하며 API wait의 Unknown만 별도로 확인한다. Harness 출력은 기존 strict 22-key 형식이다.

9개 checked failure는 wrapper prefix 뒤 odd WORD, 첫 signed read 뒤 지원 밖 둘째 read, bank ROM으로의 늦은 flag write, MOVEM 셋째 LONG의 경계 분할 write, live unsupported callback, 두 helper의 늦은 잘못된 RTS return, 상위 chain의 지원 경계 밖 실행, 실제 raw source 조회 span만 누락한 리소스를 검사한다. 각각 RAM/register/PC/carry/PVC/bank/ports/read count/status 전체 API 출력 보존을 확인했다. 누락 리소스 검사는 다른 원본 fixed bytes를 보존한 kind3 두 조각을 사용하며 원본 데이터나 pointer를 성공시키기 위해 바꾸지 않는다. 이 rollback은 공개 API의 checked failure 계약이며 원본 CPU exception의 rollback이나 OS 파일 저장의 원자성을 뜻하지 않는다.

## 동결 근거와 재현

| 파일 | SHA256 |
| --- | --- |
| `tools/observe_animation_machine_activation.py` | `a188f9d8823c6fd19fa6b5cdea4ca0c55016f38d644b25b6fe9b8778954b828c` |
| `artifacts/animation_machine_activation_native/observation.json` | `9244bfafbf4fe921ccbb8d293e5b713fa16f4fdc35b38246d851c7726fac8e61` |
| `tools/verify_animation_machine_activation.py` | `330f630634cc9111561779e37b7b8d60ca03d43ee8775d01c6a730b964593795` |
| `artifacts/animation_machine_activation_execution/verification.json` | `de726ac51b78c06d33925d287298c71162984f7f334aa8579893b3bdc283433b` |

Native 보고서의 65 input·445 artifact 참조를 검사했고 새 검증 보고서는 56 input·1023 artifact 문자열 참조, 절대 경로 정규화 후 1036개 고유 파일을 기록한다. Python/local import, C++ translation unit/재귀 header, unit source, compiler/runtime, 여덟 리소스와 manifest, native source/보고서/산출물 및 생성 harness/binary를 pin한다. 검증 중 입력 변경과 ROM 변경은 거부한다. Observer와 verifier는 시작 시 이전 성공 보고서를 지워 실패한 재실행이 낡은 성공 보고서를 남기지 않는다.

저장소 root에서 실행한다. 원본 및 기존 리소스가 준비돼 있어야 한다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_activation.py
.venv/bin/python tools/verify_animation_machine_activation.py
.venv/bin/python tools/verify_animation_machine.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_carry.py
make -j4 all test
```

검증기는 자기 artifact 폴더에서 C++11 `-O2 -Wall -Wextra -pedantic` harness를 빌드하며 compile warning은 0개였다. 메인의 전체 `make all test`는 Python 257개·C++ 153개, 경고 0개로 종료했다. 로그는 `/tmp/ms5-animation-activation-make.log`이다. 새 activation unit은 6672 API invocation을 포함하며 담당 작업자의 isolated normal/UBSan 실행이 통과했다. 기존 세 verifier도 source 변경 없이 순서대로 재실행해 통과했다.

| 현재 core 회귀 | 대조 수와 실패 검사 | 최종 보고서 SHA256 |
| --- | --- | --- |
| 기존 machine | base 8조건·연쇄 2단계, extended 85조건·121단계, 실패 9개 | `2a0851f7a88595e16d7f85df46483851ef6e9451033873dd97d1b716f4ea8cba` |
| 기존 callers | 59조건·91단계, 실제 출력 재개 32회, 실패 6개 | `5f8638bc3cf76ac8197f957753926a03e34b3024b802a50672e6db5f97f7894f` |
| 기존 carry | 60조건·160단계, 실제 출력 재개 100회, 실패 10개 | `a7182575f26b86101befee13b515bc32f2f634154854cf2a0e20e75ceee799f5` |

새 보고서와 기존 세 보고서의 고유 파일 1036/1707/1233/3042개 해시를 각각 현재 파일과 재검사했다. `/tmp/ms5-activation-final-reference-audit.json`에 결과를 기록했다. 독립 native 재실행은 33조건·55단계와 전체 22회 재개를 확인했다. 메인의 native 510개 참조 및 새 verifier 1036개 고유 파일 해시 검사도 통과했다. 독립 작업자의 source/core 리뷰와 1036개 파일 해시 검사에는 추가 발견 사항이 없으며, 근거는 `/tmp/ms5-activation-core-verifier-review.txt`(SHA256 `51c98c0c9e0ca2f73a1e7eba9f8aaaa4b75346ad8eaedc16aec0f7996cc38c63`)이다. 임시 로그·리뷰 파일은 로컬 확인용이고 동결 보고서의 provenance는 보고서 자체 `inputs`/`artifacts`에 남는다.

## 남은 범위

원본 관측기의 장치 지도는 bank2, 16개 coherent work-RAM mirror 및 제한된 PVC write/외부 status read를 사용한다. 임의 callback, 다른 bank의 원본 실행, IRQ/timing과 일반 CCR는 이 관측으로 확정하지 않는다. `47c6c` 조건/HUD/BCD와 `47d20` 이후 readiness/frame, 전체 stage scheduler 및 자연 게임 진행은 이번 완료 범위에 포함하지 않는다. 기존 standalone API와 전체 게임 목표의 나머지 작업도 그대로 남는다.
