# `480bc` U3 motion walk: C++ 실행 검증 기록

[F]=실행·해시로 확인, [I]=추론, [U]=미확인. 대상: `engine/src/animation_machine_motion_walk.cpp`(선택 F, block 시작 370). 기준: `animation-machine-motion-walk-u3-contract.md`(SHA256 `fe5db3bd8d160296e71a82e5ddace169b9dd61b6dd15c0e61fd0b96f0fc6793d`), 원본 Unicorn 관측 `artifacts/animation_machine_motion_walk_native/observation.json`(SHA256 `411f3444d365d487dc2e5e8fca861c2117dd9aa21733af7f8537e514e9708968`, 관측 도구 SHA256 `c3112b04fbbeb54f76a77e8063099bdbe9231ce3cd2f2a95267368c922ae2d0b`), ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 검증기 `tools/verify_animation_machine_motion_walk.py` -> `artifacts/animation_machine_motion_walk_execution/verification.json`. 검증 대상 커밋은 워크트리 a0b3df5(미커밋 검증기 추가).

## 결과 [F]
검증기 2회 실행 보고서 SHA256 동일: `6ede75393848e017452f60dbedd596b01325de705cca7b2799ea2244c70167c2`. `make -j4 all test` 통과(`animation_machine_motion_walk_test PASS 3865 API invocations`). `git diff --check` 깨끗.

- 비교: 1359 case(일반 1333-4 + guard 30), split 45,408 phase(재개는 직전 실제 C++ 출력 + 기록된 host 변경만, 44,097회), continuous 대조 1,304. 매 phase 전체 64KiB RAM/16R/PC/A7/PVC/bank/순서 port/external read/status 일치. native 459,257 산출물 전부 읽고 해시 검증.
- 시작 상태: scene_frame 116, stage_frame 64, 선언 unit fixture 907(scene case 182 입력 + 선언 stack write로 재구성, 기록 SHA와 일치)은 재구성·일치 확인. stage_entry_body 120과 캡처 재진입 152는 native 산출물 SHA 고정 선언 상태(재구성 불가; 레지스터·A7·stack bytes는 기록과 일치 확인, 캡처는 부모 scene case 입력을 재구성해 SHA 일치 확인).
- Carry: 원본 opcode 분류만 사용(SR 미사용). U3 규칙: TST.W `19710`/`1971c`, AND.W `1938e`/`19596`(블록 `19710 1971c 19372 1957a`)만 known Clear. 해당 phase 각 176/224개에서 C++ 결과 일치. 분포 Unknown 41,964 / Clear 1,408 / Set 2,036. carry 입력 1/2 probe 88,876회; 소비 block 9개 전부 flip 검사(U3 소비 block flip 총 965회, 각 소비자 5회 이상). FLOW_ONLY 211: 200은 단일 block probe, 9는 소비자 flip, 나머지 2(`1973a`,`19756`)는 다중 block phase 안에서 phase 단위 분류로만 확인. 비보존 159 중 156 단일 probe, 3(`1973c`,`1982a`,`19850`)은 phase 단위로만.
- 정적: block 시작 370 = 옵코드 유도 = 계약 = 관측기 목록, 묶인 분기 14, 소비 9, 생산자(ORI Set 6/ANDI Clear 1/계산 Clear 4), FLOW_ONLY 211, C++ case 라벨·표 PC가 370과 정확히 일치, C++ carry 보존 목록 U3 부분 211과 일치, 라우팅 범위가 계약 범위 병합과 일치, 180 slot 표 대상 전부 ROM BRA.W 디코드와 일치. 370 block 전부 실제 phase에서 실행·phase 첫 PC로도 실행.
- zero-step 370 block x carry 3 = 1,110 전부 통과. U2 경계 `1a0b6 1a470 1a7a8`와 이전 경계 `19812 19844 19910` zero-step 통과.
- 음수(정확한 문자열, 전체 보존): 내부 PC 787, 피연산자 word PC 421 -> `unsupported animation motion walk PC`; 범위 밖 9(`18c04 19768 19772 197d8 19938 1993c 19944 1996e 19976`) -> `unsupported animation machine PC`; Unknown carry 소비 9 -> `motion walk caller requires known carry`; 계산된 비-block-start 짝수 PC 이어 실행 36(도착 PC에 따라 위 두 문자열); 도달 안 하는 stop 7(`ff000 1a0b6 1a470 19758 1a73e 1a2c2 18c9a`) -> `unsupported animation machine PC`; 소비자 known carry 양방향 제어 18, 전체 경로 stop 제어 7. native guard 30 전부(각 phase/whole-step): odd A1/A7/A5 -> `program bus requires even WORD/LONG address`, ROM write A5 -> `unsupported animation machine write device`, A7 -> `program bus write requires RAM mirror units`, bad-stop 6 -> `unsupported animation machine PC`, oor 6 -> 계산 PC에 따라 `unaligned animation machine PC` / walk / machine 오류. 모두 출력 보존 확인.
- 홀수 계산 PC(oor 25 row): API가 홀수 stop을 `invalid animation machine RAM/PVC/stop PC`로 거부하고, stop 없이 이어 실행하면 `unaligned animation machine PC`. 두 경우 모두 정확 문자열+보존 확인. 단 dispatcher JMP 직후 부분 효과(D4.W)는 API로 관측 불가이므로 native와 비교하지 않았다.

## 범위 밖 19938..19978 [F]
관측기가 계약 밖 선언 범위로 `19938..19978`(`flow-19938` 4 row)을 관측했다. C++는 이 범위를 라우팅하지 않는다(`unsupported animation machine PC`). 검증기는 이 4 row를 비교에서 제외하고, 선언 진입에서 정확한 오류와 출력 보존만 확인한다(expected-unsupported). `19768`/`19772`(U5 호출자)도 같은 오류.

## 구 verifier 영향 (적용하지 않음) [F]
`tools/verify_animation_machine_scene_core.py`에서 `19812/19844/19910`을 unsupported로 기대하는 부분:
- 783-784행 `boundary_direct_entry_*`: BOUNDARY_PCS의 `19812 19844 19910`은 이제 실행되는 block 시작.
- 785-789행 `outside` 목록: `19820 198ec 19920`은 U3 내부 PC(`unsupported animation motion walk PC`), `19830 19850`은 U3 block 시작(오류 아님)으로 바뀐다.
- 71-72행 GUARD_ERRORS 중 `guard-bad-stop-1a7a8-on-19844-seed`(이제 U3를 거쳐 `1a7a8`에 도달해 오류가 아님), `guard-bad-stop-19812-on-19844-seed`(`19812` 도달 시 오류 아님) 기대값 재검토 필요.
- 813-814행 `full_path_start_with_stop_{19812,19844,19910}`: 기준 seed case 36은 motion LONG=0이라 세 PC 미도달, 기존 기대 유지 예상([I], 미실행).
- 8행·939행 docstring/limits 문구.
그 밖(`BOUNDARY_PCS` 실행 금지 assert, source.json 부재 assert, boundary zero-step)은 영향 없음 예상([I]).

## 한계·미확인 [U]
- 통제된 fixture 검증이며 자연 scheduler/IRQ 도달성은 아니다. 캡처·stage_entry 상태는 native 산출물 고정(재구성 불가).
- native 오류 rollback과 C++ 검사 오류의 동등성은 주장하지 않는다(출력 보존만).
- `1a0b6 1a470 1a7a8` 이후 본문(U4/U5)은 미검증. 홀수 계산 PC의 dispatcher 부분 효과 미비교. 무한 루프 경로의 step 상한 문구 미관측.
- 관측기 `contract_discrepancies` 1건(계약의 자연 도달 목록에 `18d32`,`18ece` 포함 vs type 80 미실행)은 계약 서술 문제이며 C++ 불일치가 아니다.

## 재현
`cd tools && ../.venv/bin/python verify_animation_machine_motion_walk.py` (약 1시간, 부하에 따라 가변). C++ 불일치는 발견되지 않았다.
