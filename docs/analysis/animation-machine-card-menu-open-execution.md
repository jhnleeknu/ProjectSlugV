# 카드 메뉴 열림 프레임(`a370`→`a5d2`/`a348`/`9b58`→`a5ea`, `c1c4`/`bf94`, `c2c0`)의 실제 C++ 검증

Baseline `34814b7`, branch `codex/animation-machine-card-menu-open`. 계약 `animation-machine-card-menu-open-contract.md`(SHA256 `1eb6c80ebcbef6a2f8c6488c23342ee4a85dae1c0acbf9037ad3ccb280549c4b`)의 202개 block 시작과 경계(`c2c8 9e94 9f36 a2be a406 a662 a6da a70a a71a bd26 e84d6 a63c`)를 동결된 native 관측과 공개 C++ API(`run_animation_machine`)로 비교하는 검증기 `tools/verify_animation_machine_card_menu_open.py`의 기록이다. 경계 PC는 stop으로만 허용되며 실행하지 않는다. 자연 scheduler·BIOS 동작의 증거가 아니다.

## 입력과 방법

- Native 관측 `artifacts/animation_machine_card_menu_open_native/observation.json` SHA256 `154b4ed588a1bf7c9615bc7c6c3710492e4c0a711aca710b20f6bd21a7390ab4`, 도구 `tools/observe_animation_machine_card_menu_open.py` SHA256 `17dea0a98c5a8ca3aa34ccf7524d132872877774ffcfd39970037fa0f7d04316`을 pin한다. 정상 79 + guard 9 조건. 관측은 해시·trace 일관성으로만 감사하며 재실행하지 않는다.
- 비교 항목: full 64KiB RAM, 16R, PC, live A7, PVC device/bank, ordered ports(video LONG/WORD 순서 포함), external reads, status. 단계 split마다 비교하고, 재개는 직전 실제 C++ 출력과 native 기록의 선언된 host 변경(RAM, PC, A7 가산)만 쓴다. continuous 제어와 split 최종 출력이 같음을 확인한다. 기대 레지스터를 주입하지 않는다.
- 시작 상태: BIOS 행은 fade/card chain의 `c00468` stop 출력, 나머지 78개 조건은 card child chain→push chain을 검증기가 C++로 다시 실행한 `a370` stop 출력(step 25, RAM SHA는 native 교차 기록 `268b5550...`과 같음, A7 `1feff8`)에서 시작한다. 선언된 초기 레지스터(callback 행 D0 3/3/0/0/5, `guard-odd-A7`의 A7)와 선언된 bank 상태(`bank-300000-same-address`)는 라벨별로 정확히 고정했다(선언 차이가 있는 행 7개).
- Carry는 native SR이 없으므로 native가 실행한 PC 열의 원본 opcode 분류(`ori #1,ccr`=Set, `andi #fe,ccr`=Clear, `FLOW_ONLY` 보존, 그 밖 Unknown)와 C++ carry를 대조한다. phase가 a018 호출자 BCS에서 시작하지 않는 한(입력 C를 소비하므로 경로가 바뀜) 입력 C=Clear/Set 탐침 26220회를 같은 입력으로 다시 실행해 분류와 같고 carry 외 출력이 같음을 확인했다(보존 4623회).
- 보존 block 68개는 원본 opcode(block 끝 = 제어 이동 또는 다음 block 시작)에서 독립 도출해 `animation_machine.cpp`의 열림 구역 `case` 목록과 정확히 일치함을 확인했다. 단일 block phase 관측(`a06c`/`a076`은 입력과 무관하게 Clear/Set)이 도출과 일치한다.
- Negative는 입력 RAM/PVC/16R/PC/carry/bank/ports(marker)/reads/status 전체 보존과 단일 정확 오류 문자열을 고정한다.

## 결과

`.venv/bin/python tools/verify_animation_machine_card_menu_open.py` 통과(2시간 33분).

- 88 조건(정상 79 + guard 9), split 14969(guard 직전까지), continuous 282, 재개 14881, ports 34605, native 외부 read 0. 원본 프로그램 읽기 감사: fixed 1841, bank 756, PVC write 12.
- 프레임 증거: chain 행 step 26..30과 connected 행 step 0..4의 프레임마다 C++ ordered ports SHA, video LONG/WORD/`8200` 개수, 4(A2) WORD 전후, 7/8/e 필드, 자식 7e/80, 출력 PC/A7이 native `open_frames`와 같다(ports 0/34/51/85/189). fresh `connected-a370-to-open` 345 phase는 chain의 C++ 출력과 같다. chain step 25 RAM이 push chain 출력과 같다.
- carry 분포: Unknown 11893, Clear 2997, Set 79.
- Negative 합계 365 = native guard 9(checked API 오류, 전체 출력 보존) + API 356. 묶인 분기 60개를 포함한 계약 범위 내부 PC 283개 직접 진입은 `unsupported animation card menu open PC`; 경계 PC(`9e94 9f36 a2be a406 a662 a6da a70a a71a bd26 e84d6 a63c c2c8`)와 범위 끝 밖 PC는 `unsupported animation machine PC`. 경계 도달 행의 마지막 단계를 다른 stop(`ff000`, `2ac2`, 다른 경계)으로 호출하는 rollback 음성과 같은 입력이 해당 경계를 stop으로 줄 때 성공하는 양성 대조를 둔다(10개 경계). a018 호출자 BCS 15개 PC에 Unknown carry로 진입하면 `card menu caller requires known carry`와 전체 rollback이다. 같은 PC에 Clear/Set 진입은 각각 Clear/Set 대상으로 분기(30건, 상태 보존). 제로 스텝 202 block × carry 3 = 606건은 입력 상태 전체가 보존된다. 경계 12곳의 stop==entry 제로 스텝은 성공(관측 사항).
- guard 오류: 홀수 A2/A3/A0/A7 5건은 `program bus requires even WORD/LONG address`, `e5=0`·`e5=3(c2c8)`·`a63c`·`e84d6` 4건은 `unsupported animation machine PC`.
- 보고서 `artifacts/animation_machine_card_menu_open_execution/verification.json` SHA256 `ee5010f1ac280ef533f700a2d426fd6c888a243f9076f997b3daf071b557f3c3`, 검증기 SHA256 `ecf5dea3cbb751cf6046b64ef43288126285a82a2cf311548c071b1683847973`.

## 기존 검증기 갱신

`a370`/`9b58`/`c2c0`이 실행되므로 두 검증기의 미지원 negative를 아직 실행부가 없는 PC로 옮겼다.

- `verify_animation_machine_card_menu.py`: 경계 직접 진입을 `38c8 38e2 a406 9e94 c2c8`로 바꾸고, `a370`을 다른 stop으로 만나는 호출은 이제 `a370`이 실행된 뒤 dispatcher가 다음 객체의 odd JSR 대상을 만나는 `animation fade card odd JSR target` rollback이다(라벨 `a370_runs_then_dispatcher_continues_with_stop_*`). `9b58`/`overflow a370`의 구 음성은 제거하고 `a370`/`9b58`/`c2c0` stop 성공 양성 대조로 대체했다. native guard `guard-stop-9b58-never-reached`(이제 `9b58` stop 성공)와 `guard-run-past-a370`(`c2c0` stop 성공)은 `native_guards_superseded_by_card_menu_open_core`에 기록하고 negative로 세지 않는다. `guard-stop-38c8-never-reached`는 `animation fade card odd JSR target`으로 바뀌었다. 재실행: 95 조건, split 2405, continuous 111, negative 123(guard 8 + API 115), zero-step 123, 보고서 SHA256 `89640e8b3031450e9e34464ad5af6cae36c9afc5fdf86de29758581b3896d2f4`, 검증기 SHA256 `423a08b4db4879bf8f041dcee7fc183a94e830f7b555c113dfe7c6eb49181a84`. 열림 검증기가 이 chain을 재사용하려고 `CARRY_PROBES` 플래그(기본 True)를 추가했다.
- `verify_animation_machine_card_child.py`: `a370_pc_has_no_executor`/`c2c0_pc_has_no_executor`를 `a406`/`9e94`/`c2c8` PC로 옮기고 `a29c` 호출 뒤 `a370`이 실행되는 두 rollback을 `a29c_call_then_open_frame_with_stop_{ff000,a406}_rolls_back`(`animation fade card odd JSR target`)으로 바꾸며 stop `2ac2` 양성 대조를 추가했다. `guard-run-past-a29c`(stop `2ac2` 성공)를 superseded에 추가했다(총 3개). 재실행: 32 조건, split 568, continuous 112, negative 16, zero-step 126, 보고서 SHA256 `eb734d58c0385791a2027fd9470b3f5eafb5b226e2c093b353841520987b0c94`, 검증기 SHA256 `c3d5afb4ee01275ecb5c70649dac44e658b2e5ad5e80c42e42785aa7aca451e1`.

## 기존 검증과의 관계

`verify_animation_machine{,_fade_card,_screen,_cleanup,_scene,_palette_bind,_map_transfer,_callers,_carry,_activation,_readiness,_hud,_transition,_exit}.py` 14개는 수정 없이 통과한다. `make -j4 all test`는 종료 코드 0이며 `animation_machine_card_menu_open_test` 2530, `animation_machine_card_menu_test` 494, `animation_machine_card_child_test` 347 API 호출이 통과한다(빌드는 이미 최신).

## 한계와 미확인

- 원본 ROM에 banked descriptor는 없다(탐색 0건). banked 영역은 문자열 포인터를 현재 bank로 읽는 경우만 검증했다.
- Carry는 원본 opcode 분류이며 native C 측정이 아니다.
- 경계(`9e94 a2be a406 a662 a70a bd26 e84d6 a63c c2c8`)와 hook 대상은 실행하지 않는다. hook 대상 `9000`은 다른 단위의 코드여서 native 행만 비교하고 rollback 음성에서 제외했다(`fff00`만 사용).
- native에서 관측되지 않은 block 시작 8개: `c1ee c1f4 c1fe c202 c208`(`bd26` 뒤), `a3ac a3b4`(`a2be`/`a6da` 뒤), `9b78`(BEQ/BNE 같은 플래그 뒤의 RTS로 구조적으로 도달 불가). 제로 스텝과 carry 도출로만 확인한다.
- 선언된 RAM/레지스터/bank fixture는 입력이지 원본 측정 준비가 아니다. 프레임 재진입은 선언된 PC 변경이다. 자연 scheduler·IRQ·timing·타일/팔레트 의미·직접플레이는 범위 밖이다.
- 묶인 분기·내부 PC 거부는 API 전용이며 검사된 실패는 API 출력 보존이지 원본 CPU fault rollback이 아니다.
