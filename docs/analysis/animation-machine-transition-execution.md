# 상태·요청 분기와 화면 채우기의 공유 stack 실행 검증

Baseline `915a4c3`. [확정 계약](animation-machine-transition-contract.md)의 `4e216/bee`, `47d24..47da4`, `477ac/35a2`를 공개 animation-machine API에 연결했다. `477ee/47f4a/47da4/480bc/47eac`의 본문은 실행 전 경계다. 입력은 통제된 합성 fixture이며 자연 scheduler·실제 플레이·전체 stage 완료의 증거가 아니다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 낮은 fixed CPU 주소는 같은 ROM 파일 offset이다. C++ harness는 원본 파일을 직접 읽지 않고 MS5D v1 kind3 여덟 개를 기존 loader/bus로 소비한다.

## 원본 관측과 carry 근거

Native는 정상 107조건·split 224단계·fresh continuous 121단계, 별도 guard 3조건의 split/control 각 3단계를 기록했다. 조건마다 split 두 번과 control 두 번으로 fresh CPU 440회·단계 실행 702회다. 정상 분류는 gate 37, request 20, caller 10, fill 10, pending 9, signed flag 8, upper 8, negative flag 4, gate/stack alias 1이다. 대기는 14단계이며 정상 ordered writes는 watchdog 12개·video 685개·PVC 24개다.

Carry는 host SR을 읽지 않고 실제 원본 분기의 바로 다음 PC로 판정한다. `47d2a:64000012` BCC는 Clear `47d3e` / Set `47d2e`, `47d34:65000008` BCS는 Clear `47d38` / Set `47d3e`, `47d42:6400002e` BCC는 Clear `47d72` / Set `47d46`이다. 세 분기의 양쪽 결과가 관측됐다. 검증기는 원본 bytes와 실행 PC 쌍으로 별도 판정한 후 native의 `branch_evidence`와 checkpoint carry tag를 확인한다. Standalone `4e216/bee`의 fresh return을 해당 원본 분기 PC로 놓는 것은 명시된 통제 adapter다.

실제 `47d24` JSR가 incoming A7-4에 `00047d2a`를 쓰면서 A5-75bc의 초기 status 2가 0으로 바뀌는 alias를 관측했다. 뒤의 status 5를 읽어 Set이 되는 결과는 stack 쓰기 없는 helper 계산과 구분한다. Direct `bee`의 A7=`10f002`에서는 요청 BYTE `10f004`가 live return의 `7d`다. 복원 경로는 return을 유지하지만 소비 경로는 실제 RTS 값을 `00040034`로 바꾼다. 후자는 지원 밖 target guard이며 정상 완료에 포함하지 않는다.

Pending WORD 두 개의 쓰기와 실제 sound JSR return `47d98`를 공유 RAM A7로 실행한다. 대기 중 명시된 host RAM 변경은 saved low BYTE와 pending/timer/previous WORD에 적용되며, 재개는 동일 CPU의 실제 polling PC부터 계속한다. 이전 비교·쓰기·호출을 반복하지 않는다. 별도 임시 stack, RAM diff mask, 실행 시작 뒤 register 주입, ROM patch·stub·SR 읽기는 없다. Split과 fresh continuous의 전체 PC/event/host-change 순서 및 RAM/PVC/register checkpoint snapshot을 대조한다.

## C++ 대조와 checked 실패

최종 C++은 정상 107조건·224단계, 직전 실제 출력 재개 117회, 대기 14단계, original branch에서 독립 판정한 known carry 147단계를 일치시켰다. Ordered ports는 721개(watchdog 12·video 685·PVC 24), external read는 0회다. 기존 strict 22-key 형식과 전체 16register/PC/RAM/PVC/bank/status/read count를 대조하며 재개는 직전 실제 C++ 출력과 기록된 host RAM 변경만 전달한다. Native incoming은 assertion으로만 사용한다. API 대기 carry는 Unknown이다.

새 로컬 fold는 독립 PVC 모델과 watchdog BYTE `300001`, video WORD `3c0004`, LONG/WORD `3c0000`을 원본 event 순서대로 결합한다. `>BII` 9byte 레코드는 원본 명령의 접근 단위이며 물리 bus cycle 수나 watchdog 시간·VRAM/pixel 결과의 검증이 아니다. 기존 공통 `fold_device` 동작은 변경하지 않았다.

Fill의 WORD 폭·높이 0은 원본의 명시적 skip이며 `35f0`의 감소 후 wrap과 구분한다. 종료 WORD `3c0004=0` 뒤 LONG `(A4)=82000000` 순서를 보존한다. Direct `35bc` BEQ는 incoming Z를 공개 상태가 보유하지 않아 checked unsupported로 거부한다. 정상 fill은 실제 선행 MOVE.W/SUBQ.W가 만든 Z 조건을 같은 block 안에서 소비한다.

Native guard는 `bee`의 live RTS `40034`와 fill TRAP 두 조건이다. 첫 LONG 출력 뒤 TRAP도 실제 원본 trace로 남겼다. C++ checked failure는 같은 초기 입력의 RAM/register/PC/carry/PVC/bank/ports/read count/status 보존을 확인하며 원본 fault의 부분 효과와 API rollback의 동등성을 주장하지 않는다. 추가 checked 실패 12개는 Unknown branch 두 곳, direct `35bc`, fill의 늦은 TRAP·A4·RTS/odd RTS, helper의 조건부 두 번째 read, status clear 뒤 RTS, odd WORD, pending WORD 쓰기 뒤 sound JSR, 실제 누락 bank2 data를 포함한다. Native guard 3개와 합쳐 15개다. 여덟 경계(`47d24/47d2a/47d34/477ac/35a2/477ee/47da4/480bc`)와 유효 carry enum 세 값의 zero-step 24개는 입력 보존을 확인했다.

## 동결 근거와 재현

| 파일 | SHA256 |
| --- | --- |
| `tools/observe_animation_machine_transition.py` | `dff0b6e68dcb6b3364548028dfa99e83f5721742684e43fabbf2e8ea2f607d0e` |
| `artifacts/animation_machine_transition_native/observation.json` | `edf1f5e7248601d2a708cbc7ebfb8a89c62bfdb5dcef018cb94a2c5fa26aaba4` |
| `tools/verify_animation_machine_transition.py` | `80e7440a729ad7c55b55f61cc5b118514be027bcd35ad09065e9a674b4524110` |
| `tools/verify_animation_machine.py`의 SOURCES 추가 후 | `bdb514880e02354d394fad714e81d7824b2d53dd2680d4e99ccdec23d3e2480f` |
| `artifacts/animation_machine_transition_execution/verification.json` | `0da18b6f00f26a2a78a4be8ef256b50a361ff9ccf89d74ea5bd30d673f2a4f2b` |

Native 72 input·2519 artifact의 2591개 참조와 새 C++ 보고서의 65 input·4182 artifact 문자열 참조, 정규화 후 4199개 고유 경로를 현재 파일로 hash 검사해 일치시켰다. 새 verifier는 동결 source·실제 transition 계약과 upstream HUD 계약, recursive local imports/C++ headers·translation units, unit, compiler/runtime, 원본과 실제 resource/manifest, 생성 harness/binary를 기록한다. 입력 hash는 native 재실행과 컴파일 전에 잡고 종료 시 다시 검사한다. 원본 hash/stat 보존을 확인하며 시작 시 이전 성공 보고서를 지워 실패 뒤 stale success가 남지 않게 한다.

저장소 root에서 준비된 원본을 사용한다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_transition.py
.venv/bin/python tools/verify_animation_machine_transition.py
.venv/bin/python tools/verify_animation_machine.py
.venv/bin/python tools/verify_animation_machine_callers.py
.venv/bin/python tools/verify_animation_machine_carry.py
.venv/bin/python tools/verify_animation_machine_activation.py
.venv/bin/python tools/verify_animation_machine_readiness.py
.venv/bin/python tools/verify_animation_machine_hud.py
make -j4 all test
```

메인의 `/tmp/ms5-machine-transition-make.log`는 `make all test` exit 0, Python 257개·C++ 156개·경고 0개를 기록한다. 새 transition unit은 isolated normal/UBSan에서 500 API invocation을 통과했다. Native 독립 감사는 66조건·split 137단계·continuous 80단계와 전체 대기 14단계·guard 3개, 2591개 현재 hash 참조를 확인했다. 기록 `/tmp/ms5-transition-native-independent-review.txt` SHA256은 `2ee6a56de1792853b19a1bfb60061a777b221cdc0747ca1f3028bd3d3bf36005`다.

새 verifier/core의 독립 리뷰와 4199개 현재 참조 해시 감사에는 추가 결함이 없었다. 기록 `/tmp/ms5-transition-core-independent-review.txt` SHA256은 `24b0f5dbae8bdf588400800e5879a378150122c14e52aa5fc8059a030f841ca9`다.

기존 여섯 검증 경로는 공통 비교기의 SOURCES에 새 실행부만 추가한 상태로 재실행해 모두 exit 0을 확인했다. 각 경로의 검증 로직과 기존 native 관측 파일은 변경하지 않았다.

| 회귀 보고서 (`artifacts/*_execution/verification.json`) | 실제 대조·실패 검사 | SHA256 | 고유 참조 경로 |
| --- | --- | --- | --- |
| `animation_machine` | base 8조건·chain 2단계, extended 85조건·121단계, negative 9개 | `2c6bac72773d52692cd0a19113b51a728a94d9f20e6c30ba74b6c1922854cc9f` | 1710 |
| `animation_machine_callers` | 59조건·91단계·32재개, negative 6개 | `32cc2c866e5378f79d05716ca8b14871cf444e396e9ff108fa6ab795a011fac8` | 1236 |
| `animation_machine_carry` | 60조건·160단계·100재개, negative 10개·zero-step 3개 | `07e85b8bb4ce6c170ed6c919f90b2caba538eea39e639ea202e6b22ce91debc8` | 3045 |
| `animation_machine_activation` | 52조건·74단계·22재개, negative 9개 | `0f6633c300d7cb09f39efd32445707ff855be69a49bb0b729471353f68dba02f` | 1039 |
| `animation_machine_readiness` | 68조건·154단계·86재개, negative 14개·zero-step 3개 | `98d1a307ce3ef120c1800ab4aa79280c925aa9b22e57fa9f937f69621161da67` | 2978 |
| `animation_machine_hud` | 124조건·277단계·153재개, negative 15개·zero-step 9개 | `88fbed53e51772537226d54427aacf2ebbba951d5ae952766e863cb5114403ac` | 4991 |

새 보고서와 여섯 회귀 보고서의 모든 input/artifact hash를 현재 파일로 확인했다. 보고서별 상대·절대 경로를 정규화한 고유 수는 위 표와 같고, 일곱 보고서의 합집합은 18695개 고유 경로다. 감사 기록은 `/tmp/ms5-transition-final-reference-audit.json`이며 메인의 별도 `/tmp/ms5-transition-final-hash-audit.json`도 같은 합집합을 확인했다.


## 남은 범위

Native 지도는 bank2와 coherent 16개 RAM mirror, 제한된 PVC/video/watchdog/external 접근을 사용한다. 다른 bank의 원본 실행, 임의 device/callback, 일반 CCR/XNZV, IRQ/timing, VRAM/pixel, stop 경계 뒤 본문과 자연 scheduler·전체 stage·전체 게임 복원은 이번 완료 범위가 아니다. Tested API 실패 보존은 OS 파일 저장의 원자성을 뜻하지 않는다.
