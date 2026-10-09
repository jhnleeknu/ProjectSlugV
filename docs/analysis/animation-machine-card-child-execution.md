# 카드 자식 callback c250의 실제 C++ 검증

Baseline `e25f276`, branch `codex/animation-machine-card-menu`. 계약 `animation-machine-card-child-contract.md`의 `c250..c2a2`, `de424..de48a`, `e7c16..e7c30`를 동결된 native 관측과 공개 C++ API(`run_animation_machine`)로 비교하는 검증기 `tools/verify_animation_machine_card_child.py`의 기록이다. BIOS(`c00468`)와 카드 메뉴(`a29c`)는 실행하지 않으며 자연 scheduler·BIOS 동작의 증거가 아니다.

## 입력과 방법

- Native 관측 `artifacts/animation_machine_card_child_native/observation.json` SHA256 `3e48b69e4827d5a25f7085aee1c81bf6bc0b41a64daa159a3232e690c16f3312`, 도구 `tools/observe_animation_machine_card_child.py` SHA256 `d9b229b7ecd79f1e412ccc55e78c2c57061e376bf32fbbed83237272cb03b7ae`를 검증기가 pin한다. 정상 26 조건(split 555, continuous 111), guard 6 조건. 관측 산출물은 해시·trace 일관성으로 감사하며 다시 실행하지 않는다.
- 비교 항목: full 64KiB RAM, 16R, PC, live A7, PVC device/bank, ordered ports, external reads, status. 재개 입력은 직전 실제 C++ 출력과 native 단계의 선언된 host 변경(RAM write, PC 변경, A7 가산)뿐이다. 기대 레지스터를 주입하지 않는다.
- BIOS 재개 행(연결·chain·변형)의 시작 상태는 기존 fade/card 검증기를 재실행해 얻은 실제 C++ `c00468` stop 출력(RAM SHA `b690c366...`)이다. 이후 행은 같은 보고서의 앞선 행의 실제 C++ 출력에서 시작하며, 선언된 초기 차이는 `guard-odd-A6-child`(A6), `guard-odd-A7-push-child`(A7+1), `boundary-7e-0000-fields-*`(D0/D1)뿐이다. PVC 1ff0..1ff3의 raw native 저장과 mask된 device 저장 차이는 기존 검증과 같이 제외한다.
- Carry는 native SR이 없으므로 native가 실행한 PC 열의 원본 opcode 분류(ORI/ANDI CCR 확정, flow-only 보존, 그 밖 Unknown)와 C++ carry를 대조한다. `c28a` BCS는 native 측에 C 증거가 없고 실행 PC 경로(`c28e` 대 `c290`)만 증거이다. 7e=8000은 borrow 없음(7fff, `c28e` RTS), 7e=0만 `c290`으로 간다.
- Negative는 입력 RAM/PVC/16R/PC/carry/bank/ports(marker)/reads/status 전체 보존과 단일 정확 오류 문자열을 고정한다. 자기 재귀 callback은 메커니즘을 단계별 stop으로 확인한다(재귀 push가 mirror RAM에서 `(A6)`를 `2ac2`로 덮고, `A6=8(A6)=2ac2`의 첫 LONG `2c6e0008`이 `JSR (A0)` 대상이 되어 실행부 없는 짝수 PC로 나간다). `a29c` stop의 positive 대조는 A7=entry-8, 스택 `[a7]=c2a8`, `[a7+4]=2ac2`.

## 결과

첫 실행에서 core가 `c27a..c280`과 `c290..c29e`를 한 block으로 묶어 native split checkpoint `c280`/`c296`/`c29a`/`c29e`에서 멈추지 못했다(조건 `chain-full-bios-resume-to-a29c` phase31). 의미 차이가 아니라 block 경계 문제이며, 메인이 각 명령을 별도 block으로 분리하고 unit의 내부 진입 목록을 고쳤다(unit 346 API 호출 통과).

실제 core에서 `.venv/bin/python tools/verify_animation_machine_card_child.py`가 통과했다: 32조건(정상26+guard6), split 568(정상555+guard 앞 단계13), continuous 112, negatives 18(native guard6+API12), zero-step 126, source 분류 carry Unknown549/Set19/Clear0. Fresh 조건은 연결 chain의 같은 단계와 C++ 출력이 같다. 7e=0만 `c290`→`a29c` stop(A7=entry-8, `[a7]=c2a8`, `[a7+4]=2ac2`)이다.

보고서 `artifacts/animation_machine_card_child_execution/verification.json` SHA256 `c22a93a33209745915f03606cdcd25dce8c33db5345a50e3b49d332d764c8f9f`, 검증기 SHA256 `281f2324d8b840d48c635ab51a5f9f16565729ecf3c1f0a35840e398cbce4822`, core SHA256 `3ff5b441d1870c2747e722443e455c59341a2bfc94fe719cd3817ec9f3a28adb`.

## 기존 검증과의 관계

14개 기존 검증기(최종 core 기준 재실행 결과는 리뷰0233; `verify_animation_machine{,_callers,_carry,_activation,_readiness,_hud,_transition,_exit,_screen,_cleanup,_scene,_palette_bind,_map_transfer,_fade_card}.py`)는 core 추가 후에도 수정 없이 모두 통과한다. `fade_card`의 `dispatcher_self_callback_stack_alias_then_unsupported_PC`는 단계별 stop으로 같은 메커니즘(`JSR 2c6e0008`)임을 다시 확인했으며 오류 문자열도 같아 변경하지 않았다.

## 한계

`c00468` BIOS 효과, `a29c/a0a0/a2b8/a370` 카드 메뉴, callback `c1c4`, 자연 scheduler·IRQ·timing·일반 CCR, 직접플레이는 범위 밖이며 미확인이다. 프레임 재진입은 선언된 PC 변경이다. `c28a` 직접 진입 거부는 API 전용(native guard 없음)이다.
