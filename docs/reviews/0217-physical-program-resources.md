# 0217 — 전체 physical program 리소스와 C++ 소비

Baseline `48465d6`, branch `codex/physical-program-resources`. 기존 kind2가 담지 못하던 bank1..7의 마지막16BYTE씩112BYTE를 포함해 canonical 프로그램8MiB 전체를 보존한다. 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 전체 코드의 의미 분석이나 게임 복원 완료를 뜻하지 않는다.

## 변경과 검토

- MS5D v1 kind3, CPU sentinel ffffffff, physical offset/size/CRC를 사용한다. 별도 `PhysicalRomResource`와 typed loader를 추가하며 기존 kind1/2 loader 계약은 유지한다. 크기·범위·길이·CRC 오류는 기존 리소스를 보존한다.
- 패커는 인접한1MiB 파일8개와 metadata를 생성한다. 총 payload8,388,608BYTE, container8,388,864BYTE다. Manifest SHA `798d042a6c6bcf8f5f880608b1fdb5f02b7694d3dada9e0c7832d6b3b1824482`. 원본·추출물은 Git에서 제외한다.
- C++ bus는 kind3의 각 physical BYTE가 유일하게 포함되는지 확인한다. 홀수 physical bank base의 WORD가 두 파일에 걸쳐도 읽는다. 빈틈·중복·legacy와 겹치는 unit은 거부한다. 기존 legacy WORD의 완전한 단일 창 요구는 유지한다. Vector/PVC는 명시적인 장치 view가 필요하다.
- CLI는 header kind로 loader를 선택하며 kind3 vector의 수명은 실행 동안 유지한다. 기존 positional ABI와13개 register JSON은 그대로다. 기존 검증기의 잘못된 kind3 오류 입력은 이제 지원하지 않는 kind99로 변경했다.
- 메인이 core/loader/CLI/검증기의 실제 source와 diff를 검토했다. Sol 작업자들은 서로 다른 구현·패커·검증기·원본 관측을 교차 검토했다. 확정된 C++ 결함은 발견되지 않았다. 검증기에는 provenance 입력과 partial WORD/cross-chunk 오류 검사를 보강했다.

## 검증

- `make all test` exit0: Python257, C++ test 실행147, 경고0. Core/loader의 별도 normal/UBSan도 통과했다. 이 단위는 기존 full49fc6 실행기를 변경하지 않으며 기존 일곱 full49fc6 비교기를 모두 재실행했다는 뜻은 아니다.
- 독립 패커 감사: 두 번 재생성한 파일·manifest가 실제 산출물과 일치했다. C++ typed loader로 전체8MiB를 원본과 비교했고 기존 loader16회 거절/기존값 보존을 확인했다. Python 신규14개 검사도 통과했다.
- 새 C++ harness는 runtime kind3 파일8개만 읽어 public bus로8,388,608BYTE를 반환했다. Python이 원본과 모든 bytes를 비교했다. 경계 읽기241건, 홀수 physical WORD/LONG39건, 거절15건, 장치 view 우선3건을 확인했다. 첫1MiB 경계는 fixed ROM→RAM이므로 연속 ROM으로 가장하지 않는다.
- 기존 원본95조건을 재실행하고 kind3만 사용하는 실제 CLI73조건의13register/전체64KiB RAM을 비교했다. 기존 guard19건과 추가 오류11건은 출력 보존을 확인했다. 기존 high32 guard3건은 원래95보고서 안에서 계속 미비교로 남긴다.
- Legacy kind1/2 경로도73일치/19거절/3보류 및 추가22오류를 재검증했다. 현재 report SHA `c8f53f1f729fbd34f3aa007fbbd18c58b587917bee319c1607cb6f44c3d0ba67`.

## 별도 높은 주소 관측

새 `observe_animation_high_address.py`는 기존 high32 입력3개에만 명시적인 host24비트 bus adapter를 적용한다. 원본 handler CPU/ROM4a382..4a3ac와 입력은 그대로 실행하고4a276 전에 중단한다. logical01000000은 실제 cart program[0:1000]의 읽기 전용 alias이고 레지스터·hook의 raw32 주소는 보존한다. logicalfffffff0은 busfffff0의 미지원 장치로 읽기 전에 중단한다.

2완료/1guard, 각 fresh CPU2회와12payload를 확인했다. 전체RAM15register/A7·접근 순서·쓰기 전 bytes·원래 관측의 prefix가 일치한다. 독립 Sol도3조건을 재실행하고404고유 참조 해시를 확인했다. Source SHA `7fe7e967fb8893ffcd1b3d7c2b388ffa70a37dc4d4b3451f6121407fd22b281e`, native report SHA `0350a9da19b7b7e13b5ec82bb84dede2092b54d44b2aa6153d083e55df29bac9`.

이는 제한된 cart-vector 선택 가정 아래 host 매핑 관측이다. Unicorn의 자동 mask, 실제 기판 측정, 일반 MMIO/BIOS vector 선택, CCR, whole40 또는 자연 script 도달성의 근거로 확대하지 않는다.

최종 C++ 검증기는 이3조건을 별도 그룹으로 다시 실행했다. 2완료의13register/전체RAM이 실제 C++와 일치하고1masked-device 오류는 출력 파일을 보존했다. 기존95의3보류와 혼합하지 않는다. 최종 verifier source SHA `a6ec8f2579e1073e217e259e8eea8b79037ee15ffc797d511acf33427d6d6d37`, report SHA `e87f9980061f929187d2d1e6fae3402087fd66c97292f924fd1a8baa9ee4b401`. 메인이 입력25/산출물783참조의 고유803파일 해시를 현재 파일과 확인했다. 이전636b86a6 보고서는 이 별도 그룹 추가 전 결과다.

## 재현과 다음 작업

```sh
.venv/bin/python tools/pack_physical_program.py
make all test
.venv/bin/python tools/observe_animation_high_address.py
.venv/bin/python tools/verify_animation_banked_lookup.py
.venv/bin/python tools/verify_physical_program.py
```

다음은 whole49fc6의 caller A7와 frame memory 효과다. push로 남는 bytes와 pop 시점의 실제 RAM 읽기를 보존해야 하며 metadata에 저장한 값만 복원하거나 stack RAM 차이를 mask해서는 alias 의미가 보장되지 않는다. 명령 완료 수는17중14종과14/3c 일부로 유지한다. 전체 Goal의 범위·완료 기준과 누적 진행을 유지한다.
