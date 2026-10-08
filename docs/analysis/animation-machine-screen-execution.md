# 화면 초기화와 timer 후속 흐름의 실제 stack 검증

Baseline `c776ed8`. 이번 단위는 원본 `ca9e/caf0`과 실제 공유 A7, `47fca`의 JSR부터 `47fdc` timer 경로를 기존 machine API에 연결한다. `480bc` body 또는 `47fe4`의 BSR 실행 전 경계에서 멈추며 자연 scheduler나 다음 frame을 host PC 변경으로 재현했다고 주장하지 않는다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 낮은 fixed CPU 주소는 같은 ROM 파일 offset이다. 실제 MS5D v1 kind3 여덟 개를 C++ loader/bus로 제공한다. 원본은 수정하지 않는다.

검증기는 strict 22-key harness로 full64KiB RAM/16register/PC/PVC/bank/status/ordered ports/read count를 비교한다. 실제 대기의 재개는 직전 C++ 출력과 명시된 host RAM 변경만 사용하며 native incoming을 주입하지 않는다. Native SR을 읽거나 unobserved carry를 추정하지 않는다. 포트는 원본 명령 접근 단위의 `>BII`9byte 기록이며 VRAM/pixel·물리 bus cycle 수의 검증이 아니다.

## 원본 동작과 비교 경계

`ca9e`는 A4를 `3c0000`으로 설정하고 정상 진입에서 768회 loop와 다섯 tail LONG, 총 773개 video 포트를 쓴다. 직접 `cab0`의 D7.low=`ffff`는 65,536회 loop를 실제로 수행하며 tail을 합쳐 65,541개 출력이다. 직접 `cab8`은 DBRA-only이므로 입력 C를 보존한다. D7 상위 WORD 및 D0의 32bit wrap을 원본 전체 register 결과와 대조한다. 임의 A4는 실제 RAM/PVC 또는 checked device 접근이며 별도 video 주소로 강제하지 않는다.

`caf0`는 실제 A7에 `caf2`를 push해 `ca9e`를 호출한 뒤 35a2 rectangle 다섯 개를 호출한다. 정상 출력은 2072개(워치독 5·비디오 2067)다. 각 rectangle의 최종 `3c0004` WORD와 `3c0000` LONG을 순서대로 유지한다. 마지막 BYTE(A5-769a) clear와 live RTS도 실제 RAM을 사용한다. 원본 fixture의 return LONG `000ff000` 일부를 clear하여 `0000f000`으로 돌아가는 경우를 별도 성공 경로로 대조한다.

`47fca` JSR의 실제 return `47fd0`에서 timer WORD=32와 callback LONG=`47fdc`를 순서대로 쓰고 즉시 timer를 31로 감소시켜 `480bc`로 간다. 직접 `47fdc`는 timer 0/1/2/ffff를 비교하며 1만 `47fe4`로 간다. `47fe4`와 `480bc`는 stop 경계이며 body는 실행하지 않는다. Z만 소비하는 직접 `47fe0` 임의 진입은 지원하지 않는다.

## 검증 결과와 재현

원본 matrix 34조건 가운데 정상 31조건의 split 128단계와 fresh continuous 37단계를 재실행했다. Guard 3조건의 split 10단계와 continuous 3단계도 따로 재실행했다. C++은 정상 31조건·128단계의 full RAM/16R/PC와 장치·포트·상태를 일치시켰다. 실제 이전 출력 재개는 97회이며 대기 6단계, ordered 포트 92,222개(비디오 92,167·워치독 55), PVC 출력과 외부 읽기는 각각 0개다. 이번 native C 태그는 모두 미관측이며 native와의 C 동등성 검사는 0개다. 대기에서는 API Unknown을 확인한다.

11개 focused checked-error 검사는 DBRA LONG의 odd/wrong-device A4, 2072개 포트 이후 잘못된 final BYTE clear, ca9e 출력 뒤 bad/odd live RTS와 odd A7 pop, timer WORD 쓰기 뒤 잘못된 object LONG, odd timer read, flag-only `47fe0`·지원 밖 `47fe4`, 전체 `47fca` 실행 뒤 `480bc` body 거부를 포함한다. Native guard 3개와 합쳐 14개다. Guard는 `cb5e`의 bank write `200000`, shared stack을 덮은 뒤 `caee`가 읽은 raw return `7580ff02`, `47fd6`의 fixed LONG write `0ffffe`다. 원본 fault의 이미 일어난 부분 효과를 API rollback과 같다고 주장하지 않는다. API 오류에서는 RAM/state/carry/PVC/bank/포트/read count/status 입력 전부를 보존한다. 여덟 PC와 유효 carry 세 값의 zero-step 24개도 입력을 보존했다.

| 파일 | SHA256 |
| --- | --- |
| `tools/observe_animation_machine_screen.py` | `3df8c3aa322d1ac96d3edeeb03dc672929ec25c405e96cee752a2d5707ae40ec` |
| `artifacts/animation_machine_screen_native/observation.json` | `89e5f3867d416ac611565f46b0f4c0590ee1bb53d7be28a65572c0f018614d9a` |
| `tools/verify_animation_machine_screen.py` | `c154e119718375f2c834360032a9f59c8ee625366837c577c5af6e6c78cc219f` |
| `tools/verify_animation_machine.py`의 SOURCES 추가 후 | `35478315b63f3528b4393984b49c7e6255dd715c3d208eec44d820f073691c27` |
| `artifacts/animation_machine_screen_execution/verification.json` | `7fbbe6ec7902e064cca0c8e9471fab787981a8e00f668fb3388781e5c9b5d15d` |

Native 72 input·1461 artifact의 1533개 고유 경로와 C++ 보고서의 73 input·2542 artifact 문자열 참조, 정규화 후 2565개 고유 경로의 현재 hash를 확인했다. 실제 새 screen 계약·기존 full screen/HUD 계약, recursive Python/C++ 의존성·unit·compiler/runtime·리소스·원본·harness/binary를 pin하고 시작/종료 hash와 원본 stat을 검사한다. 시작 시 이전 성공 보고서를 지워 stale success를 방지한다.

저장소 root에서 준비된 원본을 사용한다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_screen.py
.venv/bin/python tools/verify_animation_machine_screen.py
.venv/bin/python tools/verify_animation_machine.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_carry.py
.venv/bin/python tools/verify_animation_machine_activation.py
.venv/bin/python tools/verify_animation_machine_readiness.py
.venv/bin/python tools/verify_animation_machine_hud.py
.venv/bin/python tools/verify_animation_machine_transition.py
.venv/bin/python tools/verify_animation_machine_exit.py
make -j4 all test
```

새 screen unit은 normal/UBSan에서 66 API invocation을 통과했고 최대 DBRA 65,541개 출력을 포함했다. 메인의 `/tmp/ms5-screen-main-make.log`는 exit 0, Python 257개·C++ 실행 158회·경고 0개를 기록한다. 독립 검토는 원본 대표 21조건과 전체 native 1533개·verifier 2565개 현재 참조를 확인했고 추가 결함이 없었다. 기존 여덟 verifier도 새 core/common source 목록으로 공식 재실행해 모두 exit 0을 확인했다. 새 screen을 포함한 아홉 보고서의 현재 input/artifact hash가 전부 일치하며 정규화한 합집합은 25,717개 고유 경로다. 감사 기록은 `/tmp/ms5-screen-final-reference-audit.json`이다. 아홉 보고서의 최종 hash·회귀 수치와 메인 통합 결과는 [리뷰 0227](../reviews/0227-animation-machine-screen.md)에 기록한다.

## 남은 범위

Native fault의 부분 효과와 checked API 전체 출력 rollback을 구분한다. OS 저장 원자성, 일반 CCR/XNZV·IRQ/timing, 임의 device/callback, video/VRAM/pixel, 자연 gameplay와 전체 stage·게임 완료는 미검증이다.
