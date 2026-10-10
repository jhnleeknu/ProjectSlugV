# 카드 메뉴 push(`a29c`→`a0a0`→`38e8`/`386e`)와 renderer 설정(`c2a8`→`a2b8`)의 실제 C++ 검증

Baseline `bfbfe60`, branch `codex/animation-machine-card-menu-push`. 계약 `animation-machine-card-menu-push-contract.md`(SHA256 `0a4d095f741e151f509364118663c6470e527ea7535c1058e8d93161398a81ea`)의 `a29c..a2be`, `a0a0..a1e2`, `386e..3902`, `c2a8..c2c0`을 동결된 native 관측과 공개 C++ API(`run_animation_machine`)로 비교하는 검증기 `tools/verify_animation_machine_card_menu.py`의 기록이다. `a370`(메뉴 프레임), `9b58`(중첩 push), `38c8`/`38e2`(TRAP #f)는 stop 경계일 뿐 실행하지 않으며 자연 scheduler·BIOS 동작의 증거가 아니다.

## 입력과 방법

- Native 관측 `artifacts/animation_machine_card_menu_native/observation.json` SHA256 `da76f4643efafafdc8929a9cd73a24a1e3a434e49275e5babcadd53e5c45bfbc`, 도구 `tools/observe_animation_machine_card_menu.py` SHA256 `adb3e9cb65175ebcb3c76347601755f951c033df673ada43533245b238951322`를 검증기가 pin한다. 정상 85 조건(split 2405 중 guard 앞 단계 포함, continuous 111), guard 10 조건. 관측 산출물은 해시·trace 일관성으로 감사하며 다시 실행하지 않는다. 경계 PC(`a370`/`9b58`/`38c8`/`38e2`)가 native trace에서 실행되지 않았음을 모든 phase에서 확인한다.
- 비교 항목: full 64KiB RAM, 16R, PC, live A7, PVC device/bank, ordered ports, external reads, status. 재개 입력은 직전 실제 C++ 출력과 native 단계 기록의 선언된 host 변경(RAM write, PC 변경, A7 가산)뿐이다. 각 변경 기록의 `pc_before`/`a7_before`가 단계 시작 상태와 같음을 검사한다. 기대 레지스터를 주입하지 않는다.
- 시작 상태: `a29c` stop 출력은 검토된 card child chain(`chain-full-bios-resume-to-a29c` step 24)을 검증기가 C++로 다시 실행해 얻은 실제 출력이다(RAM SHA `3e5d1fb0024c82b2fcde3cc368b1d99a4696572a22734e143ffa88f72f3e7d6e`, native 교차 기록과 동일). BIOS chain 행은 기존 fade/card chain의 `c00468` stop 출력에서 시작한다. 선언된 초기 레지스터(D0/D1/D3/D7/A0/A5/A7)와 선언된 bank 상태(`bank-300000-same-address`만, 장치 저장은 마스크된 ff8/ff9)는 native fixture 기록과 일치해야 하고 provenance에 `declared`가 있어야 한다. 선언 차이가 있는 행은 82개다.
- Carry는 native SR이 없으므로 native가 실행한 PC 열의 원본 opcode 분류(ORI/ANDI CCR 확정, `FLOW_ONLY` 보존, 그 밖 Unknown; card child 검증기와 같은 분류기)와 C++ carry를 대조한다. 추가로 카드 메뉴 core만 실행한 phase마다 입력 C=Clear/Set을 준 탐침 4612회를 같은 입력으로 다시 실행해 분류와 같고 carry 외 출력이 동일함을 확인했다(보존 762회). 단일 block phase에서 C를 보존한 block 시작은 `3878 38a4 a0c2 a158 a17e a2bc c2a8 c2ba`로 계약 목록과 일치한다. 이는 원본 opcode 분류이며 native C 측정이 아니다.
- Negative는 입력 RAM/PVC/16R/PC/carry/bank/ports(marker)/reads/status 전체 보존과 단일 정확 오류 문자열을 고정한다.

## 결과

`.venv/bin/python tools/verify_animation_machine_card_menu.py`가 통과했다.

- 95 조건(정상 85 + guard 10), split 2405, continuous 111, 재개(직전 C++ 출력에서 시작) 2312, ports 5050, native 외부 read 0. 원본 프로그램 읽기 감사: fixed 356, bank 713, PVC write 12.
- 연결 조건(`a29c` stop 출력에서 host 변경 없이 `a370` stop)은 BIOS chain 행의 같은 native 출력과 C++ 출력이 29 phase 모두 같다.
- Negative 합계 132 = native guard 10(checked API 오류, 전체 출력 보존) + API 122. 직접 진입 거부: 묶인 분기 PC 16개와 내부 PC 81개(블록 시작·묶인 분기·경계를 제외한 계약 범위의 모든 원본 명령 주소)는 `unsupported animation card menu PC`, 경계 PC `9b58 38c8 38e2 a370`과 범위 밖 PC(`a1e2 a2be 3902 c2c8 c2c0 a09e`)는 `unsupported animation machine PC`. `a370`/`9b58`/`38c8`/`38e2`를 다른 stop으로 만나는 호출 15건은 `unsupported animation machine PC`와 전체 rollback이며, 같은 입력이 해당 경계를 stop으로 줄 때 성공하는 양성 대조 4건을 둔다. 제로 스텝 41 block 시작 × carry 3 = 123건은 입력 상태 전체가 보존된다. 경계 4곳의 stop==entry 제로 스텝은 성공(관측 사항)한다.
- guard 오류 문자열: ROM/bank A5 write는 `unsupported animation machine write device`, 홀수 descriptor/A7은 `program bus requires even WORD/LONG address`, 홀수 A2 record 쓰기는 `invalid animation machine write size/alignment`, 나머지 6개(overflow RTS 대상 `1000`, `9b58`/`38c8`/`a370` stop 미도달, TRAP 미stop)는 `unsupported animation machine PC`.
- 보고서 `artifacts/animation_machine_card_menu_execution/verification.json` SHA256 `9f60e658eda41481720cf26184e4f4bc1468f8c07d9d2c783a11fb7be5aa2f37`, 검증기 SHA256 `d89134466824cd9a668bb9c196f7c65d7271d1f27710fb671270d74553c36afa`, core `engine/src/animation_machine_card_menu.cpp` SHA256 `d552b0ed10a261686d6d11492c0b86b08dcb95d47565acbd6c6fcc43890aa3f6`.
- 관측(C++ 불일치 후보, 거부 자체는 정상): block `38fe`의 RTS 주소 `3900` 직접 진입은 라우터 범위(`..38fe`)를 벗어나 카드 메뉴 core의 `unsupported animation card menu PC`가 아니라 `unsupported animation machine PC`로 거부된다. 검증기는 이 문자열을 그대로 고정했다.

## card child 검증기 갱신

`a29c`가 실행되므로 `tools/verify_animation_machine_card_child.py`의 `a29c` 미지원 negative를 정말 미지원인 경계로 옮겼다: `a370_pc_has_no_executor`(PC `a370`), `a370_after_a29c_call_with_other_stop_rolls_back`/`..._with_stop_2ac2_rolls_back`(7e=0으로 `a29c`를 호출한 뒤 메뉴가 `a370`에서 멈춤), `c2c0_pc_has_no_executor`(구 `a2b8`). 정상 `a29c` stop과 `mechanism_a29c_stop` 양성 대조는 유지한다. 동결 native guard 중 `guard-stop-c2a8-never-reached`(C++가 `c2a8`에서 ok)와 `guard-callback-a2b8`(`2ac2`에서 ok)는 이제 성공 입력이라 `native_guards_superseded_by_card_menu_core`로 기록한다. `guard-run-past-a29c`는 오류 문자열이 같지만 원인이 `a370`이다. 재실행 결과: 32 조건, split 568, continuous 112, negative 16(+superseded 2), zero-step 126, 보고서 SHA256 `ad205196bbae9fffffe7f87f10c05b141895e531557339b5fe0880bcdc82633b`, 검증기 SHA256 `d0e6a57417f8c0a67f30a049ba2188928b2ea1636d2b07dfcc049f719b4bfea9`.

## 기존 검증과의 관계

`verify_animation_machine{,_fade_card,_screen,_cleanup,_scene,_palette_bind,_map_transfer,_callers,_carry,_activation,_readiness,_hud,_transition,_exit}.py` 14개는 수정 없이 통과한다. `make -j4 all test`는 종료 코드 0이며 `animation_machine_card_menu_test` 495 API 호출, `animation_machine_card_child_test` 348 API 호출이 통과한다.

## 한계

- 원본 ROM에 banked descriptor는 없다(`200000`/`300000` bank의 모든 짝수 주소 탐색에서 종료 descriptor 0건). 따라서 banked 영역은 문자열 포인터(제목·항목)를 현재 bank로 읽는 경우만 검증했다.
- Carry는 원본 opcode 분류이지 native 측정이 아니다. ADDA/SUBA는 보수적으로 Unknown이다.
- `a370`(메뉴 프레임: 입력·커서·그리기 `9b58`/`9e1a`/`9d3a`/`a018`/`3918`/`3650`/`e84c8`)과 그 이후, callback `c1c4`/`bf94`, TRAP #f 처리, `c2c8` 이후는 범위 밖이며 미확인이다.
- 선언된 초기 레지스터·bank 상태·RAM fixture는 입력이지 원본 측정 준비가 아니다. 프레임 재진입은 선언된 PC 변경이다. 자연 scheduler·IRQ·timing·일반 CCR·직접플레이는 범위 밖이다.
- 묶인 분기·내부 PC 직접 진입 거부는 API 전용이다(native guard 없음). 검사된 실패는 API 출력 보존이며 원본 CPU fault rollback이 아니다.
- Native 관측은 해시·trace 일관성으로만 감사하고 이 검증기에서 재실행하지 않는다.
