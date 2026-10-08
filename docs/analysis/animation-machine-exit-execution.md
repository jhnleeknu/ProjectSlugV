# 카운터 종료·후속 callback의 공유 stack 실행 검증

Baseline `21d818c`. [확정 계약](animation-machine-exit-contract.md)의 `47eac..47fca`, `47c5a`, `1c63c`, `48398/30f4`, `3c84/3d44`, `4e24e/ca7e`와 기존 `8c16` leaf adapter를 공개 animation-machine API에 연결했다. 최종 경계는 `47fca:4eb90000caf0`의 **JSR caf0 실행 직전**이다. `480bc/47c6c`도 원본 실행의 지정 stop이며 다음 frame을 host가 만들어 자연 scheduler라고 주장하지 않는다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 낮은 fixed CPU 주소는 같은 ROM 파일 offset이다. C++ harness는 원본 파일을 직접 읽지 않고 기존 MS5D v1 kind3 여덟 개를 loader/bus로 소비한다.

## 실제 원본 관측

정상 native는 90조건·split 252단계·fresh continuous 112단계다. 별도 guard 3조건은 split 5단계·control 3단계이며, 전체 93조건마다 split/control을 두 번씩 실행해 fresh CPU 372회·단계 실행 744회를 기록했다. 정상 조건은 lookup 24, player helper 17, palette 13, countdown 8, clear 6, pipeline 6, whole exit 5, sound pair 4, late callback 4, prefix 3이다. 대기는 22단계, ordered PVC writes는 190개이며 external read는 0회다.

`47eac`은 실제 `48980` script와 원본 default sprite callback을 사용한다. 원본 prefix가 object 좌표를 다시 쓰므로 incoming queue/clip label만으로 최종 draw 결과를 단정하지 않는다. 실제 trace와 full register/RAM 효과를 기준으로 대조한다. `30f4`는 원본 `[30ec,30f4)`의 `6070809090909090`을 실제 kind3 bus로 읽고 D0 상위 WORD를 보존한다. 상수표·난수 함수나 별도 성공용 ROM script로 대체하지 않는다.

`47f74/47f82`의 MOVEM은 D0 전체 LONG을 live A7 RAM에 저장·복원한다. 마지막 `19dc` sound high wait 중 saved LONG을 `8123ab00` 또는 `89abcdef`로 바꾼 조건에서 원본이 상위 WORD까지 새 D0를 복원한다. 이후 실제 BYTE 비교가 palette 분기를 선택한다. Sound BYTE 쌍은 첫 BSR의 live return과 두 번째 tail BRA를 유지하며 추가 return을 만들지 않는다. `47f9c`의 timer 32는 같은 실행에서 31로 감소하고, fresh timer 0은 ffff로 wrap한다. 이 late callback 입력은 대기 재개와 구분한 fresh fixture다.

Carry는 host SR을 읽지 않고 원본 `1c648/1c664:6400000e` BCC의 바로 다음 PC로 판정한다. Clear successor는 각각 `1c658/1c674`, Set은 `1c64c/1c668`이다. 검증기는 원본 bytes와 실제 PC 쌍으로 독립 판정해 `branch_evidence`와 checkpoint tag를 확인한다. 나머지 native carry는 미관측이다. 실제 JSR return이 첫 player marker와 겹치는 조건도 관측하며 호출 전에 marker 값을 고정하지 않는다.

`8c16` adapter는 기존 full15R leaf에 같은 RAM과 8D/7A를 전달한 뒤 live A7의 LONG을 읽어 RTS한다. A5가 108000으로 바뀌고 palette write가 return slot과 겹치면 그 새 target을 사용한다. 원본의 positive alias는 palette write가 실제 return을 200으로 바꾸며 해당 PC에서 멈춘다. Leaf 내부 instruction checkpoint·IRQ·시간이나 일반 CCR을 구현했다는 뜻은 아니다.

원본 관측에는 ROM patch·stub, 시작 뒤 register 주입, SR 읽기, 별도 scratch stack이나 stack diff mask가 없다. Split과 fresh continuous의 전체 PC/event/host-change 순서와 RAM/PVC/16register checkpoint snapshot이 일치한다.

## C++ 대조와 checked 실패

최종 C++은 정상 90조건·252단계, 직전 실제 출력 재개 162회, 대기 22단계, 원본 branch로 판정한 known carry 44단계를 일치시켰다. Ordered PVC writes는 190개, external read는 0회다. Strict 22-key harness는 전체 16register/PC/RAM/PVC/bank/status/ordered ports/read count를 비교한다. 원본 ordered PVC writes의 독립 fold로 device/bank 상태를 판정하며 공통 fold 동작은 변경하지 않았다. 실제 sound/animation 대기의 다음 입력은 직전 실제 C++ 출력과 기록된 host RAM 변경만 사용하며 native incoming을 주입하지 않는다. Known carry는 원본 branch evidence가 있는 checkpoint만 비교하고 API wait carry는 Unknown이다.

Native guard 3개는 정상 완료와 분리한다. Lookup의 두 publication BYTE가 live RTS를 `60fff000`으로 바꿔 원본 `483a8`의 fetch에서 guard한다. Noncanonical A5의 initializer는 실제 `49fb6` TRAP 경계이며 C++ 오류에 `initializer TRAP15`가 포함되는지 검사한다. Prefix A6=`1fffe0`의 첫 BYTE write `20005e`는 보호된 bank ROM 접근이다. 같은 초기 입력의 checked C++ 실패에서 전체 API 출력을 보존하며 원본 fault의 부분 효과와 rollback의 동등성을 주장하지 않는다.

추가 실패 14개는 Unknown branch 두 곳, object BYTE 뒤 odd WORD 두 곳, D0 LONG push/pop, palette·lookup·clear 세 곳·sound pair 쓰기 뒤 잘못된 RTS, 실제 `30ec` BYTE 누락 및 전체 nonwaiting pipeline 뒤 지원 밖 successor를 포함한다. Native guard 3개와 합쳐 17개다. Missing lookup은 해당 BYTE만 제외한 나머지 원본 chunk0를 기존 kind3 컨테이너 두 개로 공급한다. 원본 bytes를 바꾸지 않는다. 유효 carry enum 세 값과 일곱 경계(`47eac/47f74/47f82/47c5a/1c648/1c664/47fca`)의 zero-step 21개는 입력 보존을 확인했다. API 실패 보존은 OS 저장 원자성을 뜻하지 않는다.

## 동결 근거와 재현

| 파일 | SHA256 |
| --- | --- |
| `tools/observe_animation_machine_exit.py` | `ed153a295259e691349b0cd5a13df48046a6c24b3eb6648f02702ca5c34967bc` |
| `artifacts/animation_machine_exit_native/observation.json` | `026585bc88057054d188978774aa8ce436ca7f97aaa6c2ffd459c5ca1a888bf3` |
| `tools/verify_animation_machine_exit.py` | `6a60a33bd3b53682f780467e9cd494f45201527bd6015717c652b9b9e8105d91` |
| `tools/verify_animation_machine.py`의 SOURCES 추가 후 | `ef495da24a3861f23aed71e57ffac9dbe23a2d5cf62dbbf5db0f1149e13df54b` |
| `artifacts/animation_machine_exit_execution/verification.json` | `12fae62c0c40ffd431435c5a550d935692f07192f05badab23ad1475f42be8e8` |

Native 73 input·2801 artifact의 2874개 현재 참조와 C++ 보고서의 70 input·4629 artifact 문자열 참조, 정규화 후 4650개 고유 경로를 hash 검사해 일치시켰다. 새 verifier는 실제 HUD·exit 계약과 recursive local imports/C++ palette headers/source, unit, compiler/runtime, 원본/resource/manifest, 생성 harness/binary를 pin한다. 입력 hash는 native 재실행·컴파일 전에 캡처하고 종료 시 다시 검사한다. 원본 hash/stat 보존을 확인하며 시작 시 이전 성공 보고서를 지워 stale success를 방지한다.

저장소 root에서 준비된 원본을 사용한다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_exit.py
.venv/bin/python tools/verify_animation_machine_exit.py
.venv/bin/python tools/verify_animation_machine.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_carry.py
.venv/bin/python tools/verify_animation_machine_activation.py
.venv/bin/python tools/verify_animation_machine_readiness.py
.venv/bin/python tools/verify_animation_machine_hud.py
.venv/bin/python tools/verify_animation_machine_transition.py
make -j4 all test
```

새 exit unit은 isolated normal/UBSan에서 419 API invocation을 통과했다. Native 독립 감사는 65조건·split 206단계·continuous 87단계와 전체 대기 22단계·guard 3개, 모든 2874개 참조를 확인했다. 기록 `/tmp/ms5-exit-audit.txt` SHA256은 `bc83eaef22550fe7a112414c8e61c74dd8679f120b8f88e9f911a7cdf193201f`다. 메인의 `/tmp/ms5-exit-main-make.log`는 `make all test` exit 0, Python 257개·C++ 실행 157회·경고 0개를 기록한다. 새 verifier의 독립 source/참조 감사에서도 실제 exit 계약 pin과 4650개 현재 고유 경로가 일치했고 추가 결함은 없었다. 기존 일곱 verifier도 source를 수정하지 않고 새 core/common source 목록으로 공식 재실행해 모두 exit 0을 확인했다. Native 관측 파일은 변경하지 않았다. 새 exit를 포함한 여덟 보고서의 모든 input/artifact hash가 현재 파일과 일치하며 정규화한 합집합은 23250개 고유 경로다. 자체 감사 기록은 `/tmp/ms5-exit-final-reference-audit.json`이다. 여덟 보고서의 최종 hash·회귀 수치와 메인 통합 감사는 [리뷰 0226](../reviews/0226-animation-machine-exit.md)에 기록한다.

## 남은 범위

통제된 fixture의 국소 실행 대조다. 일반 CCR/XNZV, IRQ/timing, 임의 callback/device, video/VRAM/pixel, 다른 bank의 원본 실행, 자연 scheduler·실제 플레이, `47fca`의 JSR 및 `caf0/480bc/47c6c` 후속 body·전체 stage·전체 게임 완료는 이번 범위가 아니다.
