# 카드 메뉴 닫기 실행부 C++ 검증 기록

대상: `engine/src/animation_machine_card_menu_close.cpp` (커밋 92108ac). 검증기 `tools/verify_animation_machine_card_menu_close.py`, 보고서 `artifacts/animation_machine_card_menu_close_execution/verification.json`(Git 제외). ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(CPU 주소=파일 오프셋). 구현·원본 동등성 완료 보고가 아니다.

## 입력(고정)
- 계약 `animation-machine-card-menu-close-contract.md` SHA256 `925c44c1...4c38`, 원본 관측 `observation.json` `b5bd2164...39dd`, 관측 도구 `f38219e8...e8dc`(31 블록 시작, 경계 `a698`).
- 접두 체인은 입력 관측(`49c1ba52...9ce9b46`, 도구 `cbd6fdf1...6104`)의 chain 행 step 0..330을 실제 C++로 재실행한다(시작은 실제 C++ BIOS 정지 출력). 단계마다 전체 64KiB RAM/16R/PC/PVC/뱅크/순서 포트/외부 읽기/상태를 비교하고, 닫기 관측의 교차검증 4건(a29c step24, a370 step25, open step30, 입력 최종 step330의 RAM SHA 및 PC)과 일치함을 단언한다.

## 사실(검증 결과)
- 82행(71 정상+11 가드): split 7886 단계·control 246 단계 모두 같은 방식(이전 실제 C++ 출력에서만 재개, 선언된 호스트 변경 PC/RAM/레지스터 적용 후 비교) 일치. 연속 대 분할 동등, chain 대 fresh/connected 812 단계 C++끼리 일치.
- 선언 호스트 변경: PC 253, RAM 245(정리 fixture 1d/6c/104ca4 71건, 0x299c 경로가 있는 단계에서만 허용, 104ca4 값은 프레임 진입 A7과 일치), 레지스터 13건(`A6=부모 102000`, 단계 경계, 기록된 13건 목록과 정확히 일치, 실제로 값이 바뀜).
- 프레임 27개의 순서 포트 SHA·개수, 레코드 107efe의 WORD4 전후, -f2/-ee/-e5, 프레임 A6의 콜백/7e, 나가는 PC/A6/A7이 관측 close_frames와 일치.
- 캐리: C++ 결과 = 원본 opcode 기반 분류(ORI/ANDI CCR 알려짐, 흐름 전용 보존, 그 외 Unknown). 계약의 보존 목록 `9ee4 a320 a324 a672 a67a c2f8`은 소스 opcode 유도·C++ case 목록과 일치하고 `a344`는 Unknown. 알려진 C 프로브 14102회, 단일 블록 관측은 보존 블록만 보존. `a324`는 단독 진입 시 C가 입력을 소비(Clear→`a328`, Set→`a332`, 보존), Unknown이면 `card menu caller requires known carry` 오류와 전체 보존.
- 가드 11건: 정확한 오류 문자열과 전 출력(RAM/PVC/16R/PC/뱅크/포트/읽기/상태) 보존. 홀수 접근은 `program bus requires even WORD/LONG address`, ROM/뱅크 쓰기는 `unsupported animation machine write device`, a698/a6da는 `unsupported animation machine PC`, 정리 fixture 없음은 `animation cleanup original TRAP15: coordinate index`.
- 음성: 내부 PC 65개 -> `unsupported animation card menu close PC`; 범위 밖 `9ee6 a69a a6da c2fa c2fc`와 `a698` 직접 진입 -> `unsupported animation machine PC`; a698에 닿는 중첩 단계 시작점에서 다른 stop(ff000, 2ac2, c2c0)은 전체 rollback, stop=a698은 성공(양성 대조). 총 98건(음성 87 + 가드 11). 제로 스텝: 31 블록 x 3 캐리 = 93건 전부 입력 보존.
- 읽기 감사: 고정 ROM 읽기 243, 뱅크 읽기 0, PVC 쓰기 0.

## 추론 / 검증기 허용 규칙
- 기존 cleanup 실행부는 `CMP.W`(`2886`, `2a12`) 뒤 C를 알려진 값으로 모델링한다. 원본 opcode 분류만으로는 Unknown이라 불일치했으므로 검증기는 CMP 뒤 BCS/BCC 경로로 C를 도출한다(경로가 없으면 Clear/Set 중 하나). 닫기 실행부 변경이 아니라 `2a00` 경로의 기존 동작이다.
- `a018` 호출자 BCS 블록(`9ba6`... `a00c`, `a324`)은 시작 PC일 때 입력 C에 의존하므로 프로브에서 제외한다.

## 미확인 / 범위 밖
`a698` 중첩 메뉴 복귀와 `a6da`, `bd26` 저장, 부모/자식 제거 뒤 장면, 자연 스케줄러·IRQ·타이밍, 네이티브 SR(관측하지 않음), 원본 CPU 예외 rollback 동등성(API 보존만 확인).

## 기존 검증기에서 경계 이동이 필요한 음성(적용하지 않음)
`a662`/`a2be`/`9e94`/`c2c8`이 이제 실행되므로 아래 "실행부 없음" 음성은 `a698`(또는 `a406`/`bd26`/`a6da` 등 여전히 미실행 PC)로 옮겨야 한다.
- `verify_animation_machine_card_child.py`: `9e94_pc_has_no_executor`, `c2c8_pc_has_no_executor`(직접 진입, 오류표 575-576행 포함), 머리말의 "남은 경계" 문구.
- `verify_animation_machine_card_menu.py`: `BOUNDARY_PCS`의 `B9E94`, `C2C8`(boundary_direct_entry 및 boundary_zero_step), 범위 밖 진입 목록의 `0xa2be`.
- `verify_animation_machine_card_menu_open.py`(워킹트리 미커밋본): `BOUNDARY_PCS`/`STOP_BOUNDARIES`의 `9e94 a2be a662`와 `{C2C8}`(boundary_direct_entry, boundary_zero_step), `BOUNDARY_ROWS`의 `9e94/a2be/a662/c2c8` 행에 대한 "다른 stop에서 rollback" 음성(이제 닫기 코드를 실행), 해당 stop 쌍의 `others` 목록, 양성 대조는 stop 경계로 유지 가능, `never_executed` 감사는 네이티브 추적이 변하지 않아 유지. `a406 a70a bd26 e84d6 a63c a6da`는 유지.
- 입력 단위 검증기(메인 트리 미확인): 같은 4개 PC를 경계 음성으로 쓰고 있으면 동일하게 이동.
