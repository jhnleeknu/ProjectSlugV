# `480bc` U6 입력(`49b0c`·입력 callback) C++ 실행부 검증 기록

대상: `engine/src/animation_machine_input.cpp`(작업 트리 커밋 `2f65d65`), 계약 `animation-machine-input-u6-contract.md`(SHA256 `99ba39b26d652b48189f1ab55251c6a099bad4faa21abb2d5a387522636c98dc`), 원본 ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(`extracted/program/maincpu.decrypted.be.bin`, CPU 주소=file offset). 검증기 `tools/verify_animation_machine_input.py`, 보고서 `artifacts/animation_machine_input_execution/verification.json`(저장소 밖 산출물, Git 제외). [F]=이 검증에서 확인한 사실, [I]=추론, [U]=미확인.

## 입력(고정)

- 네이티브 관측 `artifacts/animation_machine_input_native/observation.json` SHA256 `311fb438bae1ff7aa013bf4e175302a7ba249cff5ef78eb45caa258308ec78b4`, 도구 `tools/observe_animation_machine_input.py` SHA256 `de302e9213e6946a2157fe7146d48561c053aed51eb9b4984a464e2a1f7f240a`. 관측 파일 121,001개를 모두 읽어 해시를 확인했고(`VERIFIED_ARTIFACTS == artifacts`), 136개 입력 파일 해시와 Unicorn 라이브러리 해시가 일치한다.
- 관측기 module은 검증기에서 라이브러리로만 import한다(main 미실행). 고정 fixture 생성기(`Items`·stage input loop corpus·rng 시드)와 Unicorn `probe`·Python 모델만 쓴다. 재구성한 fixture는 저장된 행의 RAM/PVC SHA·레지스터·host write와 대조한다.

## 비교 계층과 결과

1. **저장 조건 658 + guard 27**: native split phase마다 전체 64 KiB RAM, 16 레지스터, PC, A7, PVC, bank, ordered port(0개), external read(0), status를 실제 C++ 출력과 비교했다. 재개는 이전 실제 C++ 출력과 native step의 선언 host RAM write로만 한다. `28a8`/`28ac`는 기존 원자 실행부 `289e` 내부라 병합(506 phase)했다. 결과: split 11,408 phase(병합 후), continuous 656(`49e36` 대상 변종 2행 제외), 재개 10,750, 선언 host write 2,820. 연속 실행의 최종 상태는 split chain 끝과 일치한다. 시작 상태: 비자연 479행은 관측기 fixture를 재구성해 SHA 고정, 자연 206행은 native 산출물(SHA 고정) 선언 상태.
2. **정상 조건 7,527 end-to-end**: 자연 206은 저장 행(1번)으로, 나머지 7,321은 같은 고정 관측기 함수로 재구성해 Unicorn으로 다시 실행한 native 최종 상태와 비교했다. 비교 항목은 최종 64 KiB RAM, 16 레지스터, PC, PVC, bank, port 없음, external read, status, 분류한 carry, Python 독립 모델의 최종 레지스터·RAM·bank(7,317건)다. 관측에 기록된 census 필드(진입·stop·최종 PC, 명령 수, A7 증감, leader별 횟수, slot 전후, JSR 대상, fixed read)를 재실행 native와 대조하고(전부 일치) C++ 실행 후 slot 값도 기록값과 비교했다. 저장 행 450건은 재실행 native가 저장 산출물(RAM·PC 열·최종 레지스터)과 같음을 확인했다. **관측에는 census 조건의 RAM/레지스터가 저장되어 있지 않다**(저장된 필드는 위 census 필드뿐). 그래서 비저장 6,869건의 native 쪽 최종 상태는 기록값이 아니라 재실행값이다.
3. **carry**: C++ carry는 원본 opcode 분류(ORI #1,CCR Set / ANDI #fe,CCR Clear / `289e` known / flow-only 보존 / 그 밖 Unknown)와 모든 phase에서 일치한다. 생산자 `4836e`·`48378`(Clear)·`4837e`(Set)를 포함한다. 소비자 4곳(`49b28` `49b7e` `4d7c6` `1d5b2`)은 328개 phase 시작에서 실제 native 다음 PC가 분류한 C의 BCC/BCS 결과와 같고, 반대 C를 주면 반대 목적지로 가며 다른 것은 바뀌지 않는다. 소비자 4곳 모두 Clear/Set 진입이 관측되었다. census 3,768회 소비자 통과에서도 native 다음 PC와 분류 C가 같다. 진입 C 1/2 probe: 저장 phase 22,160회, census 916회. 150개 실행 block 시작 전부에서 보존 여부를 실제 C++로 관측했고(62개 보존 + 소비자 4개 flip = 계약 66개와 같음; `49bb0`·`49ad6`은 native에서 단일 block phase가 없어 다음 block 시작까지의 sub-step probe 2,577회로 native 레지스터와 대조) 계약의 보존 집합과 정확히 일치했다. C++ `carry_preserving_pc` 표에서 U6 범위 항목은 계약 66개의 상위집합이 아니라 정확히 같다(누락·초과 없음). native SR은 읽지 않았다.
4. **guard 27행**: 정확한 checked 오류와 전체 보존(RAM·레지스터·PC·carry·PVC·bank·ports marker·external read sentinel·status=1)을 확인했다. 진입 C Set과 Unknown 모두 같은 오류다.

| guard | C++ 오류(정확 문자열) |
| --- | --- |
| 홀수 JSR (A1) 대상 `49e35`, 상위 BYTE `80000049`(홀수) | `unaligned animation machine PC` |
| 상위 BYTE 비영 `01049e34` `ff049e34`, RAM `106000`, ROM `4aa88` | `unsupported animation machine PC` |
| `49b30`(입력 범위 안 명령 시작 아님) | `unsupported animation input PC` |
| 홀수 A5/A7/A0/A6/A1 읽기·push | `program bus requires even WORD/LONG address` |
| A7=`1100`(ROM) push | `program bus write requires RAM mirror units` |
| ROM 쓰기(`49bb4` A1=4000, `49c20` A5=8000) | `unsupported animation machine write device` |
| `49c20` 홀수 slot 쓰기 | `invalid animation machine write size/alignment` |
| 잘못된 stop 2건(`49b2e`·`4d7f0`, null 경로)과 stop 없는 TRAP | `unsupported animation machine PC`(480cc 이후 U1 코드를 거쳐 실행부 없는 `4aa88`에서 종료) |

## 의도된 차이(불일치로 세지 않음)

- [F] `JSR (A1)` 대상의 상위 BYTE가 비영이면 native Musashi 프로브는 하위 24-bit(`049e34` callback)를 실행하지만 C++는 위 표처럼 checked 오류로 거부하고 전체 상태를 보존한다(결정 2).
- [F] 대상 `49e36`(block 중간 RTS) 변종 2행은 native가 실행하지만 C++는 해당 phase와 연속 실행 모두 `unsupported animation input PC`로 거부·보존한다.

## API 전용 negative와 경계

- [F] 명령 중간 직접 진입 217개(접힌 54개 `49dd4` `49e8a` `49f4a` 포함)와 피연산자 WORD 직접 진입 276개는 모두 `unsupported animation input PC`다. 범위 밖 21곳(자료 `49ab0`, setter 틈 등)은 `unsupported animation machine PC`, 홀수 PC 7곳은 `unaligned animation machine PC`다.
- [F] `4d7f0`(TRAP #15)은 stop 전용 경계다. 직접 진입은 `unsupported animation machine PC`, stop=PC 제로 스텝은 carry 3종 모두 상태 불변 성공, native TRAP 경계 372조건과 일치한다.
- [F] 제로 스텝: 실행 block 시작 150개 x carry 3종 = 450회 전부 입력 상태 불변·성공. 경계 PC 5곳(`4d7f0` `480cc` `49b0c` `49b2e` `49b84`) x 3종도 같다.
- [F] 소비자 4곳에 Unknown carry로 직접 진입하면 `input caller requires known carry`와 전체 보존, 알려진 C는 소비·보존한다. 생산자 `48378`/`4837e`는 진입 C와 무관하게 Clear/Set을 반환한다.
- [F] stop을 못 만나는 경우(`49b0e` `49b2e` `4d7f0` `49e34`)는 `unsupported animation machine PC`와 전체 보존이다.
- [F] C++ `case` 라벨 150개는 계약의 실행 block 시작 150개(= 151 - `4d7f0`)와 같다. 계약 block 시작 151·접힘 54·보존 66 목록은 원본 opcode 분석(leader 도출·접힌 분기·FLOW_ONLY block)과 일치한다.

## 보고할 사항(적용 안 함)

- 계약 범위 표의 "명령 수" 열이 4개 행에서 디코드 결과와 다르다(`49de6..49e34` 22/23, `49f66..49f8c` 8/9, `49d88..49de6` 31/29, `49e38..49f66` 83/85). 합은 366 대 368이며 바이트와 단위 합계는 일치한다. 문서 오타 수준이다.
- 이전 검증기/시험에서 `49b0c`를 "실행부 없음" 경계로 쓰는 곳: `tools/verify_animation_machine_frame_helpers.py` 36·548·554·687행(`natural_480bc_with_stop_49b0c`가 `unsupported animation machine PC`를 기대, API 전용 stop 대조군 설명), 문서 주석 9행. `tools/verify_stage_frame.py` 22행의 `CALLEES`는 stop 목록이라 무관하다. `engine/tests/animation_machine_frame_helpers_test.cpp` 69·238행은 이미 U6 실행 후 기대값(`49b0c`→`480cc` 실행)으로 갱신되어 있다. 위 검증기의 해당 negative는 stop `49b0c`가 이제 U6 block 시작이라 오류 기대가 달라질 수 있다. [U] 실제 결과는 다른 검증기를 실행하지 않아 확인하지 않았다.

## 한계

- 통제된 fixture이며 자연 scheduler·IRQ·플레이 도달성을 증명하지 않는다. 자연 206건은 native 선언 진입 상태(SHA 고정)에서 `480cc`까지만 비교한다.
- `289e`는 전체 결과로만 비교한다. checked 실패는 API 출력 보존이며 원본 CPU 예외 rollback과의 동등을 주장하지 않는다. 변종 2행·상위 BYTE 비영·내부 PC 직접 진입은 native 대응이 없는 의도된 거부다.
- U6c callback 6종은 ROM 설치 경로가 없어 선언 slot 값으로만 관측한다(계약 [I]). TRAP #15 처리기와 필드 의미는 [U]다.

## 재현

- 검증기를 두 번 실행해 보고서 SHA256이 같았다(`f74a5d8ee46aeb38bc90f3f40973f523f473d4a01be2dd110a4779a98a9486a9`). 검증기 SHA256은 `509dd1d0455969f7137816e4bc5ba08ac972328e1302900452fdb08765dc4acf`.
- 실행: `.venv/bin/python tools/verify_animation_machine_input.py`. 보고서 위치 `artifacts/animation_machine_input_execution/`. C++ harness는 clang++ `-std=c++11 -Wall -Wextra -pedantic` 무경고 컴파일이다.
