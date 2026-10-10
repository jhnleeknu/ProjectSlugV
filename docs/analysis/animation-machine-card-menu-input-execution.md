# 카드 메뉴 입력 프레임(`a406`), 자동 선택 hook(`bf2c`), `a70a`/`a1ee`/`9fc4`/`9ff4`의 실제 C++ 검증

Baseline `70d12b6`(push+open+input C++ 핵심 WIP). 계약 `animation-machine-card-menu-input-contract.md`(SHA256 `78fe3d1a0c855e1e491d60c66afca710077585edaf8516076bb89386c72ca604`)의 `a406..a5d2`, `bf2c..bf94`, `9fc4..9fce`, `9ff4..9ffe`, `a1ee..a1fa`, `a70a..a71a`(block 시작 60개)를 동결된 native 관측과 공개 C++ API(`run_animation_machine`)로 비교하는 검증기 `tools/verify_animation_machine_card_menu_input.py`의 기록이다. `a662`(닫기), `bd26`(BIOS 카드 저장), `bf2c`가 아닌 hook 대상(`9000`/`c2c0`/`fff00` fixture)은 stop 경계일 뿐 실행하지 않는다.

## 입력과 방법

- Native 관측 `artifacts/animation_machine_card_menu_input_native/observation.json` SHA256 `49c1ba52f7ec11dc1929022f7dc6b455b434681d472e9a39631c69ea98ce9b46`, 도구 `tools/observe_animation_machine_card_menu_input.py` SHA256 `cbd6fdf19fcc4c5ccec8126be1ab9f98501df5a393dd9805da3f1b7802e66104`를 pin한다. 99 조건(정상 92 + guard 7). 359544개 native 산출물을 phase 단위로 스트리밍하며 보고서 해시와 대조하고(전수, 중복·누락 0), 목록의 manifest SHA256을 기록한다. 입력 92개(unicorn, ROM, 관측 도구)도 해시 대조한다. 계약 문서의 60개 block 목록은 문서 본문, 관측기 `input_block_starts`, 검증기 상수가 같음을 확인한다.
- 비교 항목: full 64KiB RAM, 16R, PC, live A7, PVC device/bank, ordered ports, external reads, status. 재개 입력은 직전 실제 C++ 출력과 native 단계 기록의 선언된 host 변경(RAM write, PC 변경, A7 가산)뿐이며 각 변경의 `pc_before`/`a7_before`가 단계 시작 상태와 같음을 확인한다. 기대 레지스터를 주입하지 않는다.
- 시작 상태(사실): chain 조건은 검토된 fade/card chain을 C++로 다시 실행한 `c00468` stop 출력에서 시작해 card child, push, open, 입력 300 프레임을 모두 C++로 재실행한다(split 12184 phase). 나머지 98 조건은 chain의 step 끝 C++ 출력을 native RAM SHA256+레지스터 동일성으로 골라 시작한다(open 끝 `2ac2`=step 30, 입력 프레임 N 끝=step 30+N). 예외: `guard-odd-A7-a43e`/`guard-odd-A7-2ac0`은 fixture가 선언한 홀수 A7(`1ff001`)을 선언 변경으로 기록한다. 이 외에 선언된 초기 레지스터 차이는 없다.
- 선행 증거와의 대조(사실): C++ chain의 step 24/25/30 출력이 child(`a29c`)·push(`a370`)·open(`2ac2`) native 관측의 해당 단계 RAM·레지스터와 같고, step 0..30 전부가 open native 관측의 단계 끝과 같다(31 단계).
- 연속 vs split: 모든 단계마다 native continuous control을 한 번에 C++로 재실행해 split 최종 출력과 같음을 확인한다(835 단계). native 쪽에서도 split 연결=continuous, checkpoint=snapshot을 단계별로 감사한다(snapshot 34944).
- 프레임별 기록 대조(사실): 803개 입력 프레임의 7e/80(A6), -e5/-e6(A5), 레코드 4(word)/7/8/d/e/f 필드와 stop PC/A7이 C++ RAM·레지스터와 같다. 300 프레임 7e 카운트다운(299→0)은 native와 301 프레임 모두 같고, chain 마지막은 `a662` stop이다.
- chain과 connected/fresh 프레임의 C++ 출력은 native 출력 동일성으로 12194 phase를 매칭해 같음을 확인했다(carry 포함 동일).
- Carry는 native SR이 없으므로 native가 실행한 PC 열의 원본 opcode 분류(ORI/ANDI CCR 확정, `FLOW_ONLY` 보존, 그 밖 Unknown; card child 검증기와 같은 분류기)와 C++ carry를 35779 phase 모두 대조한다. 추가로 입력 코어만 실행한 phase마다 입력 C=Clear/Set 탐침 42672회를 같은 입력으로 재실행해 분류와 같고 carry 외 출력이 동일함을 확인했다. 단일 block phase에서 C를 보존한 시작은 계약 13개(`a412 a41a a42a a442 a488 a562 a566 a570 a574 a57e a714 bf50 bf8e`)와 같고, 60개 block의 원본 opcode 정적 분석(분기/점프까지)도 같은 13개를 낸다. 단일 block phase로 관측되지 않은 시작은 `a46a a5c6 a70a`이며 이들은 정적 분석과 phase 단위 분류 대조로만 확인했다.
- Negative는 입력 RAM/PVC/16R/PC/carry/bank/ports(marker)/reads/status 전체 보존과 단일 정확 오류 문자열을 고정한다.

## 결과

`.venv/bin/python tools/verify_animation_machine_card_menu_input.py`가 통과했다.

- 99 조건, split 35779(guard phase 7 제외), continuous 835, 재개 35682, ports 6705, native 외부 read 0. 선언 host 변경: RAM 2141, PC 836, A7 1. 원본 프로그램 읽기 감사: fixed 2763, bank 648, PVC write 12. carry 분포: Unknown 35357, Clear 420, Set 2.
- Negative 합계 128 = native guard 7(checked API 오류, 전체 출력 보존) + API 121. 내부 PC 105개(block 시작·경계를 제외한 계약 범위의 모든 원본 명령 주소)는 `unsupported animation card menu input PC`, 경계 `a662 bd26 fff00` 직접 진입과 이 경계를 다른 stop(`2ac2`, 다른 경계, `c2c0`)으로 만나는 호출 12건은 `unsupported animation machine PC`와 전체 rollback이다. 같은 입력이 해당 경계를 stop으로 줄 때 성공하는 양성 대조 3건을 둔다. 홀수 hook 대상(`fff01`)은 `animation card menu input odd jump target`(API 전용, native guard 없음). 제로 스텝 60 block 시작 × carry 3 = 180건은 입력 상태 전체가 보존된다. 경계 3곳의 stop==entry 제로 스텝은 성공한다(관측 사항).
- guard 오류 문자열: 홀수 레코드/descriptor/A7(`guard-odd-ee-A2`, `-descriptor-A3-a42c`, `-A7-a43e`, `-A7-2ac0`)은 `program bus requires even WORD/LONG address`, hook 대상 `fff00`/`bd26`/`a662` stop 미도달은 `unsupported animation machine PC`.
- 보고서 `artifacts/animation_machine_card_menu_input_execution/verification.json`, 해시는 채팅 보고에 기록한다. `make -j4 all test` 종료 코드 0(`animation_machine_card_menu_test` 494, `..._open_test` 2519, `..._input_test` 1399 API 호출).

## 기존 검증기 영향(미적용, 보고)

`tools/verify_animation_machine_card_menu.py`·`..._card_child.py`에는 `a406/a70a/bf2c/9fc4/9ff4/a1ee`를 직접 쓰는 negative가 없다(`grep` 0건). 다만 `a370` 메뉴 프레임이 열림·입력 코어로 실행되므로 `a370`을 미지원 경계로 가정한 negative는 입력 코어가 생긴 뒤 의미가 바뀐다(임시 탐침 결과, 오류 문자열 변화는 `animation fade card odd JSR target`): card child의 `a370_after_a29c_call_with_stop_2ac2_rolls_back`은 성공으로 바뀌어 제거/이동이 필요하고, `a370_after_a29c_call_with_other_stop_rolls_back`은 프레임이 끝까지 돈 뒤 문자열이 바뀐다. push 검증기의 `a370_reached_with_stop_c2c0`/`9b58`류는 성공으로 바뀌고 나머지 stop은 문자열이 바뀐다. 경계를 `a662`/`bd26`로 옮기려면 -e5=2 또는 선택 상태 fixture(이 검증기의 guard 행 시작)가 필요하다. 이 탐침은 임시 실행이며 해당 검증기를 재실행한 결과가 아니다.

## 한계

- 입력 fixture(`104cba`/`104cc0`/`10fdb6`/`10fdb7`)와 프레임 재진입(PC=`2ab8`)은 선언 host 변경이며 원래 입력 루틴·BIOS·scheduler의 증거가 아니다.
- Carry는 원본 opcode 분류이지 native 측정이 아니다.
- `a662` 닫기 이후, `bd26` 카드 저장, 비 `bf2c` hook 대상, video port 의미는 범위 밖이며 미확인이다.
- 묶인 분기/내부 PC 거부와 홀수 hook 대상은 API 전용이다. 검사된 실패는 API 출력 보존이지 원본 CPU fault rollback이 아니다.
- Native 관측은 해시·trace 일관성으로만 감사하며 재실행하지 않는다. 검증기는 per-invocation 중간 파일을 지우고 negative/제로 스텝/guard 파일만 남긴다.
