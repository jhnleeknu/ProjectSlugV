# Readiness의 공유 stack·실제 caller carry 검증

Baseline `93b5b40`. [확정 계약](animation-machine-readiness-contract.md)에 따라 `4847c`와 하위 helper의 실제 JSR/RTS, 상위 caller `47d20/47d3e`, 원본 `47d42` BCC를 공개 animation-machine API로 연결했다. 통제된 합성 입력의 검증이며 자연 scheduler나 전체 stage 실행의 완료를 뜻하지 않는다.

원본은 canonical BE `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 아래 fixed CPU 주소는 같은 파일 offset이다. C++ harness는 원본 파일을 직접 읽지 않고 실제 MS5D v1 kind3 여덟 개와 explicit cartridge vector/PVC/RAM view를 기존 loader/bus로 읽는다. 원본 hash와 수정 시각은 실행 전후 보존됐다.

## 원본 실행과 carry 근거

`47d20`의 BRA는 `47d3e`로 간다. `47d3e:4eba073c`는 PC-relative JSR `4847c`이며 실제 공유 RAM에 return `47d42`를 쓴다. `47d42:6400002e` BCC는 Clear이면 `47d72`, Set이면 `47d46`으로 간다. 검증은 선택된 successor의 명령 실행 전에 멈춘다.

Readiness는 `1bdde→289e`의 marker 조회, live object flag, 조건부 `4dee2` record 조회, 두 player의 조기 반환, `A5+5684` flag와 조건부 `4e166` mask를 실제 순서대로 실행한다. `4e166` 반환 C는 Unknown이며 상위 `484a2`가 D0.byte의 TST 결과를 읽어 최종 ORI/ANDI writer로 간다. Mask 값으로 C를 대신 만들지 않는다. 직접 RTS block은 입력 C를 보존하고, Unknown인 채 C를 읽는 branch에 진입하면 checked 오류다.

Native는 SR을 읽지 않는다. 반환 경계의 carry tag는 **뒤이어 실제 실행한 원본 BCC 방향**에서 역으로 정하며, 검증기도 successor와 원본 branch bytes에서 독립적으로 Clear/Set을 계산한다. 각 split 실행은 fresh CPU의 중단 없는 control 실행과 반환 경계 RAM/PVC/register snapshot, 최종 분기, trace를 대조한다. Standalone `4847c/1bdde/289e/4dee2`의 return LONG을 `47d42`로 놓는 것은 명시적 branch-observation adapter이며 자연 호출 관계의 증거는 아니다.

## 실제 결과

동결 native는 68조건, split 154단계, fresh continuous control 86단계다. 조건마다 split 두 번과 control 두 번, 총 fresh CPU 272회·단계 실행 480회를 수행했다. 분기 결과는 Clear 40조건·Set 28조건이다. Native 전 조건·양쪽 실행의 모든 단계를 검증기에서 다시 실행해 저장된 전체 16register/PC, RAM/PVC, trace, ports와 선택적 return snapshot payload를 대조했다.

실제 C++ 대조는 68조건·154단계 모두 일치했다. 실제 출력 재개 86회, API Unknown 대기 18단계, return 경계와 원본 BCC 결과 각 68개, ordered PVC write 126개, external status read 0회다. 재개 입력은 직전 실제 C++ RAM/16register/PC/carry/PVC/bank 출력에 기록된 host RAM 변경만 적용한다. Native incoming state는 assertion으로 사용하며 기대값을 다음 C++ 입력으로 주입하지 않는다. Device PVC와 bank는 원본 ordered writes를 독립 모델로 fold해 비교한다. 기존 strict 22-key harness 형식은 유지했다.

조기 반환 profile, mask 0..3, shifted/mirrored A5, JSR return write와 marker/record의 live alias를 포함한다. 세 `47cae` 연결 조건에는 같은 CPU의 sound high→low, wrapper sprite wait와 animation sprite wait 뒤 readiness/BCC까지의 실행이 들어 있다. Legacy readiness observer는 fixture profile 입력만 제공하며 SR을 읽는 실행 경로는 호출하지 않는다.

14개 checked failure는 다섯 Unknown branch, nested JSR 뒤 odd marker, RAM/bank 경계의 return LONG write, pointer/D0 변경 뒤 odd record WORD, 첫 PVC BYTE 뒤 지원 밖 둘째 mask BYTE, live 잘못된 RTS, 첫 player 통과 뒤 두 번째 player의 실제 bank2 데이터 누락, 두 known branch의 지원 밖 successor, whole activation/readiness 뒤 지원 밖 successor를 검사한다. RAM/register/PC/carry/PVC/bank/ports/read count/status 전체 출력 보존을 확인했다. 세 valid enum의 zero-step 입력 보존도 확인했다.

Whole activation 실패 검사의 추가 **C++ 전용 positive control 한 개**는 native single-wrapper-wait 조건의 초기 fixture에서 consumer WORD `108d34`만 `0100`으로 바꾼다. 실제 `47cae→47d42`가 대기 없이 성공하고 RAM 변경·PVC write 42개를 만드는 것을 먼저 확인한 뒤, 같은 fresh 입력으로 stop을 지원 밖으로 바꿔 rollback을 확인했다. Control의 변경된 입력을 native와 같다고 주장하지 않으며, 실패 실행에 control의 변경된 출력을 재사용하지 않는다. Checked rollback은 원본 CPU fault의 rollback이나 OS 파일 저장의 원자성을 의미하지 않는다.

## 동결 근거와 재현

| 파일 | SHA256 |
| --- | --- |
| `tools/observe_animation_machine_readiness.py` | `2055e9c1a3c89a7b9378f8ebcfe259a176815d42ede2f03543e5118026b9fb3e` |
| `artifacts/animation_machine_readiness_native/observation.json` | `a93d54a8b9001073a469795b70e00541ab5c9f09dcee9af9c2aa7b7393157ada` |
| `tools/verify_animation_machine_readiness.py` | `8f5a10f93749e33b5093e559979396b2a3b5c5425fd98e635c583aa9f0be79d9` |
| `tools/verify_animation_machine_callers.py`의 metadata 수정 후 | `cfe92bdffa4c15583e6e420fa82664ed88f507b3de48cf74f75f43a276f00682` |
| `tools/verify_animation_machine.py`의 SOURCES 추가 후 | `80a9daf41efdb193832a9cada930560009a76723055f0a74053d7aeec1c7770d` |
| `artifacts/animation_machine_readiness_execution/verification.json` | `a26fde94977d049b482e83721589adce71f6dfd8c5188a8a413dd072dde477bc` |

Native 67 input·1849 artifact 참조를 검사했다. 새 C++ 보고서는 60 input·2961 artifact 문자열 참조, 절대 경로 정규화 후 2976개 고유 파일을 기록한다. Python/local imports, C++ translation units/재귀 headers, unit source, compiler/runtime, 실제 리소스·manifest, 원본 관측과 생성 harness/binary를 실행 전에 pin하고 실행 후 다시 검사한다. 두 도구는 시작 시 낡은 성공 보고서를 지워 실패한 재실행이 이전 성공을 남기지 않는다.

저장소 root에서 원본과 기존 runtime 리소스를 준비하고 실행한다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_readiness.py
.venv/bin/python tools/verify_animation_machine_readiness.py
.venv/bin/python tools/verify_animation_machine.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_carry.py
.venv/bin/python tools/verify_animation_machine_activation.py
make -j4 all test
```

새 검증기는 자기 artifact 폴더에서 C++11 `-O2 -Wall -Wextra -pedantic` harness를 경고 없이 빌드했다. 메인의 `/tmp/ms5-animation-readiness-make.log`는 `make all test` exit 0, Python 257개·C++ 154개·경고 0개를 기록한다. 담당 작업자의 새 readiness unit은 589 API invocation을 normal/UBSan으로 통과했다. 기존 네 verifier도 현재 core에서 순서대로 통과했다. `callers`의 실패 metadata는 `original_caller_return`으로 기록한다. `47d20`은 이제 지원되므로 해당 bad-stop 검사는 readiness를 거친 뒤 지원 밖 successor에서 거부된다. 원본 stop 경계와 기존 실패 assertion은 바꾸지 않았다.

| 회귀 | 실제 대조와 실패 검사 | 최종 보고서 SHA256 |
| --- | --- | --- |
| 기존 machine | base 8조건·연쇄 2단계, extended 85조건·121단계, 실패 9개 | `101cb4c586a32d64ed1960ca8e6fd2f40036fb72efcf31c988855a7bd949fc6c` |
| 기존 callers | 59조건·91단계, 실제 출력 재개 32회, 실패 6개 | `d4ee15f9267d762a9c9f92ac68f97b9c6579496d743a837d8bf8e43354f435b4` |
| 기존 carry | 60조건·160단계, 실제 출력 재개 100회, 실패 10개 | `125de83133bcaf29a3724eeb787d54841ae2a2203fb5730e923e726adf597802` |
| 기존 activation | 52조건·74단계, 실제 출력 재개 22회, 실패 9개 | `de0906f83e9c10aae190d875f279d2b86cb2619065645497a99b556297bd00a7` |

최종 새 보고서와 기존 네 보고서의 참조 해시를 현재 파일과 전부 재검사했다. 고유 경로 수는 readiness 2976, 기존 machine 1708, callers 1234, carry 3043, activation 1037이며 모두 일치했다. 결과는 `/tmp/ms5-readiness-final-reference-audit.json`에 기록했다. 초기 `f8489b...`와 metadata 수정 후 `9050a2...` 보고서는 위 `a26fde...` 보고서로 대체됐다. Native source의 blank line trailing whitespace 한 곳을 제거한 뒤 native와 새 verifier만 다시 실행했고, 실행 의미·조건·payload와 기존 네 회귀 보고서는 유지됐다. Source/core 및 whole-prefix control의 독립 리뷰에서는 추가 결함이 없었다. Metadata 수정 후 네 dependent 보고서의 현재 1234/3043/1037/2976개 고유 참조도 독립 검사에 통과했다. `/tmp/ms5-readiness-core-verifier-review.txt`(SHA256 `05919d25a26816eab7eefd6d37cca557a6b6103a5e4d0edc71dad7bf459a825e`)에 근거를 남겼다. 임시 파일은 로컬 확인용이고 재현 입력과 산출물의 pin은 각 동결 보고서에 남는다.

## 남은 범위

Native 장치 지도는 bank2, 16개 coherent RAM mirror와 제한된 PVC/external 장치를 사용하며 범위 밖 접근은 guard한다. 원본은 patch/stub/register injection 없이 실행했다. 다른 bank의 원본 실행, 임의 callback/device, IRQ/timing과 CCR의 XNZV는 이번 증거로 확정하지 않는다. `47d46/47d72` 이후 명령, 선행 HUD/BCD, 자연 scheduler와 전체 stage 완료는 별도 남은 작업이다.
