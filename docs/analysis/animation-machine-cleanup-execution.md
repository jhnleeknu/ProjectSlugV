# Cleanup/helper와 후속 caller의 실제 stack 검증

Baseline `54a69c4`. 원본 `299c`의 palette/coordinate/reset nested 호출, `2a0a/2a28/2a48/2a60/2a84`, `477c2/47fe4`에서 `47fe8`의 LEA 전 경계를 실제 공유 RAM/A7 실행으로 대조했다. 원본 관측과 새 core를 동결한 뒤 공식 대조를 수행했다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 낮은 fixed CPU 주소는 같은 ROM 파일 offset이다. 실제 여덟 MS5D v1 kind3를 C++ loader/bus로 공급하며 원본을 수정하지 않는다.

Strict 22-key test harness로 full64KiB RAM/16R/PC와 PVC/bank/ordered ports/read count/status를 비교한다. 재개는 실제 이전 C++ 출력과 선언된 host RAM 변경만 사용한다. Native SR을 읽지 않으며 C는 실행된 원본 branch successor로만 검증한다. 실제 cleanup 계약과 recursive Python/C++ 의존성·unit·compiler/runtime·원본·리소스·harness/binary를 첫 실행 전에 pin하고 종료 시 다시 검사한다. 시작 시 과거 성공 보고서를 삭제한다.

`299c`의 watchdog 쓰기와 `2782→8ff4/c3fa`, `271c→8eb6/43dcc/c3dc` reset 호출은 실제 A7 return을 사용한다. palette count는 BYTE 전체를 소비하며 임의 4개 clamp를 두지 않는다. palette 중복 index와 reference 감소/해제, coordinate 부모/stamp alias, 목록 splice/free-list/count의 read-before-write 순서를 원본 RAM 전체 결과로 확인한다.

`29c4`의 BCS는 Clear→`29c8`, Set→`29fe`이고 `2a16`의 BCC는 Clear→`2a1e`, Set→`2a1a`다. 원본 raw WORDs `6500 0038`·`6400 0006`과 실제 successor를 검사한다. 반복 PC는 `{index, pc, successor, carry}`의 실행 순서 목록으로 기록하며 PC별 최종 C로 축약하지 않는다. split endpoint는 global flattened trace 위치의 branch occurrence와 대응시킨다. `287e`의 return을 `29c4`로 둔 직접 fixture는 통제 adapter이며 자연 caller 도달성 증거가 아니다.

`2a28`의 A6/A1/A0 LONG push와 `2a48/2a60/2a84`의 A6 push, 각 live pop과 RTS를 유지한다. `47fe4`의 BSR은 `477c2`를 거쳐 `47fe8`로 돌아오며 LEA48108 실행 전에서 멈춘다. 이번 지원 확대로 이전 screen verifier의 명시적 unsupported 경계 검사만 `47fe4`에서 `47fe8`로 이동했다. 기존 native 관측과 그 당시 stop 경계는 변경하지 않는다.

## 공식 대조 결과

정상 69조건의 split 121단계와 fresh continuous 69단계, guard 3조건의 split/control 각각 3단계를 원본으로 재실행했다. C++ 정상 69조건·121단계는 full RAM/16R/PC와 장치·포트·상태가 일치했고 실제 이전 출력 재개는 52회다. 대기와 외부 읽기는 0회, watchdog BYTE 포트는 63개이며 video/PVC 출력은 없다. 원본 branch로 확인한 C endpoint는 29회다. 원본 정상 trace의 실제 branch occurrence는 `29c4` Clear22/Set4, `2a16` Clear16/Set14이며 일곱 조건에서 같은 chain의 `2a16` Clear·Set이 모두 나타났다. `29c4`의 두 방향은 서로 다른 조건들에서 확인했다.

palette count 0/1/2/4/5, reference 0/1/2/ffff, 중복 index와 mirror object, coordinate 0..7·부모/stamp alias, WORD unsigned depth 비교, linked removal/traversal, wrapper·whole `477c2/47fe4`를 포함한다. 별도 좌표 사례는 local X/Y carry 네 조합과 self/global stamp alias를 소비한다. 전체 BYTE count 지원 계약이 모든 256개 count의 native 열거 검증을 뜻하지는 않는다.

실제 stack-overlap guard는 coordinate BYTE 쓰기가 BSR return `000029ac`를 `ff0029ac`로 바꿔 `278e` RTS가 읽는 경우다. 다른 guard는 coordinate index8의 `46f06` TRAP과 object type 비영의 `2a52` TRAP이다. Native fault의 부분 효과와 checked API 전체 rollback을 구분한다. 정상 saved-A6 alias는 `2a28`에서 원본 reset이 저장 slot을 바꿔 `ffff3400`을 live pop하며 `2a46` RTS 전에 멈춘다. 함께 바뀐 outer return을 성공적으로 실행했다고 주장하지 않는다.

14개 focused checked-error 검사는 Unknown `29c4/2a16`, object/parent type과 coordinate TRAP, 아홉 LONG clear 뒤 경계 밖 WORD, object BYTE/WORD clear 뒤 경계 밖 LONG, 두 stack LONG push 뒤 fixed-bank push, clear 뒤 bad RTS, callback publication이 live return을 덮는 경우, 미지원 `47fe8` 및 전체 cleanup 후 이 경계를 실행하려는 경우를 포함한다. Native guard 3개와 합쳐 17개에서 RAM/state/carry/PVC/bank/ports/read count/status를 보존했다. 열한 PC와 유효 carry 세 값의 zero-step 33개도 입력을 보존했다.

| 파일 | SHA256 |
| --- | --- |
| `tools/observe_animation_machine_cleanup.py` | `d1e5051a482423c0078b53e958b59ac403cdd294b1d7494befd18de2abd032be` |
| `artifacts/animation_machine_cleanup_native/observation.json` | `12b825b02281f215bc554605dffc30c8d1e28d9921ac3a49cc40081df0e7553a` |
| `tools/verify_animation_machine_cleanup.py` | `4f0cd7fc20b71b1af8a7200e64c640b03d00cd68aea984939ee6e7f9cb6cf215` |
| `tools/verify_animation_machine.py`의 SOURCES 추가 후 | `de5ceb71288f061bbe6958e22fb9ccf7f042bfc51f097ef5cc0329656f5add04` |
| `artifacts/animation_machine_cleanup_execution/verification.json` | `5f547e6405afd24dff36bbf5f2eb1ae7b61e1b605c6c3b02bd55c838c2ac5988` |

Native 73 input·1385 artifact의 1458개 고유 경로와 C++ 보고서의 74 input·2497 artifact 문자열 참조, 정규화한 2520개 고유 경로의 현재 hash가 일치했다. 독립 native 검토는 57조건·split109/continuous57단계와 모든 1458개 참조를 확인했다. 새 verifier 독립 source/2520개 참조 감사도 추가 결함이 없었다. Core unit은 최종 normal/UBSan 223 API 호출을 통과했고 C 보존 block은 62개다. 메인의 `/tmp/ms5-cleanup-main-make-final.log`는 exit 0, Python 257개·C++ executable 실행 159회·경고 0개를 기록한다. 첫 공식 시도는 core의 `2a42` checkpoint 누락으로 실패하여 성공 보고서를 남기지 않았다. pop과 RTS 경계를 포함한 수정 및 도달성 감사를 마친 뒤 위 최종 보고서를 생성했다.

## 재현

저장소 root에서 준비된 원본을 사용한다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_cleanup.py
.venv/bin/python tools/verify_animation_machine_cleanup.py
.venv/bin/python tools/verify_animation_machine.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_carry.py
.venv/bin/python tools/verify_animation_machine_activation.py
.venv/bin/python tools/verify_animation_machine_readiness.py
.venv/bin/python tools/verify_animation_machine_hud.py
.venv/bin/python tools/verify_animation_machine_transition.py
.venv/bin/python tools/verify_animation_machine_exit.py
.venv/bin/python tools/verify_animation_machine_screen.py
make -j4 all test
```

기존 아홉 verifier도 새 core/common source 목록으로 공식 재실행해 모두 exit 0을 확인했다. 새 cleanup을 포함한 열 보고서의 현재 input/artifact hash가 모두 일치하며 정규화한 합집합은 28,143개 고유 경로다. 감사 기록은 `/tmp/ms5-cleanup-final-reference-audit.json`이다. 최종 report hash·회귀 수치와 메인 통합 결과는 [리뷰 0228](../reviews/0228-animation-machine-cleanup.md)에 기록한다.

## 남은 범위

Native fault의 부분 효과와 checked API 전체 rollback을 구분한다. 일반 CCR/XNZV·IRQ/timing, 자연 scheduler/게임플레이·전체 stage·전체 게임 완료는 미검증이다.
