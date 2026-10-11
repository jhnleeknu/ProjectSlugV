# 카드 메뉴 중첩 복귀(`a698`..`a706`) 실행부 검증 기록

대상: 커밋 `afe13a1`의 `engine/src/animation_machine_card_menu_nested.cpp`. 검증기 `tools/verify_animation_machine_card_menu_nested.py`, 보고서 `artifacts/animation_machine_card_menu_nested_execution/verification.json`(Git 제외). 이 기록은 검증 결과이며 게임 전체 동등성 보고가 아니다.

## 입력(고정 해시)

| 항목 | SHA256 |
| --- | --- |
| 계약 `animation-machine-card-menu-nested-contract.md` | `1688616ba2f0ea744c0e37505c208bd2d9f0b8ba1ad066b21d1e65384fdbd27f` |
| 원본 관측 `artifacts/animation_machine_card_menu_nested_native/observation.json` | `7b40f4de2da0d11dba79fd098993b3dcc6f3a958be254d2642b456dd874c9959` |
| 관측 도구 `observe_animation_machine_card_menu_nested.py` | `fb7524ab620f2fbc730844a92293518cdf9016e6340fedc3e38c9a7a417746c8` |
| ROM(canonical BE) | `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f` (변경 없음, 전후 해시·mtime 확인) |

앞단 관측(fade/child/push/open/input/close/save)도 해시로 고정해 명령 표(source.json)와 연쇄 접두에 사용한다.

## 방법(사실)

- 64KiB RAM, 16 레지스터, PC, 라이브 A7, PVC(ff8/ff9 제외 마스크 비교), 뱅크, 순서 있는 포트 바이트, 외부 읽기 수, status를 분할 단계마다 비교한다. 재개는 이전 실제 C++ 출력과 기록된 host change(RAM/PC/A7 add/단계 경계 레지스터)만 사용하며 각 변경의 `pc_before`/`a7_before`를 단계 시작 상태와 대조하고 결과를 원본 RAM·레지스터와 대조한다. 기대 레지스터 주입은 없다.
- 시작: 실제 C++로 재실행한 fade/card 연쇄의 `c00468` 출력. 접두 단계 0..36은 관측기가 분할하지 않았으므로(관측기 인덱스 111/37이 저장되지 않은 접두) open 관측(단계 0..30, 445 phase)과 save 관측(단계 31..36, 359 phase)의 분할 phase를 같은 방식으로 C++에서 재실행하고 각 단계 끝 RAM·레지스터가 해당 관측과 같음을 확인한 뒤 중첩 연쇄(단계 37..109, 2615 phase, 73 연속 제어)로 이어 간다. `c00468`/`c0046e`(BIOS 카드)는 stop 경계로만 사용하며 실행하지 않는다.
- 연속 대 분할: 모든 단계의 연속 제어를 C++로 따로 실행해 분할 이어붙임 끝 상태와 같음을 확인하고, 원본 쪽에서는 분할 연결 트레이스·체크포인트 스냅샷이 연속 제어와 같음을 확인한다.
- 나머지 조건(61행)은 실제 C++ 연쇄 단계 출력에서 시작한다(RAM 해시 + fixture가 명시한 소스 단계 번호 + 레지스터 일치). 선언된 초기 레지스터는 `a2`/`a7`뿐이며 26행이 사용하고 값은 보고서에 기록된다. fresh 행 673 phase는 연쇄의 같은 원본 출력과 C++ 출력이 일치한다.
- 프레임 모델: 연쇄·각 행의 235 프레임에서 f2/ee/e5/e6, 두 레코드 높이·16바이트 레코드, child 콜백·7e/80, 효과음 큐 12바이트, 순서 포트 해시·개수, 프레임 RAM 변경 범위가 원본 기록과 C++ 출력에서 같다.
- 원본 읽기 감사: 고정/뱅크 ROM 읽기 바이트와 PVC 뱅크 재구성을 모든 phase에서 확인한다. 관측 산출물 115420개를 스트리밍하며 해시 검증했다.

## 결과(사실, 첫 실행 보고서 기준)

- 실제 C++ 비교: 64행(접두 2 + 중첩 관측 62행 중 정상 57 + 가드 5), 분할 12293 phase, 연속 제어 272 단계, 포트 12451, 외부 읽기 0, 스냅샷 12021. 중첩 관측 62행만: 분할 11489, 제어 235(관측 11494/240에서 가드 5행의 마지막 phase 5개 제외).
- 선언된 host change: RAM 252, PC 270, A7 add 5, 레지스터 3. 레지스터 3건은 관측기가 선언한 `A6=0x102000`(부모 재진입, `nested-f073` / `nosave-nested-f073` 단계 시작)과 정확히 같다.
- 가드 5건: 홀수 A2(a698)·홀수 A7(a698/a6da/a6b2)은 `program bus requires even WORD/LONG address`, 지원 안 되는 콜백은 `unsupported animation machine PC`. 전부 API 출력(RAM/PVC/레지스터/뱅크/포트 마커)이 보존된다. 원본 CPU 예외 롤백 동등성은 주장하지 않는다.
- 부정 실험(정확한 문자열 고정): 중첩 범위 내부 PC 20개 직접 진입(`a6b4` `a6b8` `a6ee` 등 묶음 분기 포함)은 `unsupported animation card menu nested PC`. 범위 바깥 `a696`은 close 코어(`unsupported animation card menu close PC`), `a70c`는 input 코어(`unsupported animation card menu input PC`), `c00468`/`c0046e`는 `unsupported animation machine PC`. 선언 스택을 둔 a698/a6da/a6b2 직접 진입을 도달 불가 stop으로 실행하면 2ac2 이후 디스패처가 `animation fade card odd JSR target`으로 실패하고 전체 롤백된다. 총 32개(부정 7 + 내부 20 + 가드 5).
- zero-step: 11개 block 시작 PC x carry 3종 = 33건 모두 입력 상태·RAM·PVC·뱅크 보존, 포트·읽기 없음. BIOS stop PC(`c00468`/`c0046e`)에서 stop==entry도 정상 반환(관찰 사항).
- Carry: C++ carry는 원본 opcode 걸음(ORI/ANDI CCR만 Known, 흐름 전용 보존, 그 밖 Unknown)과 모든 phase에서 일치한다(Unknown 10597, Clear 1626, Set 70). 중첩 단일 block 시작 10곳을 carry 1/2로 재실행(520회)한 결과 보존되는 곳은 `a6ce` `a6f8` `a706`뿐이며 정적 걸음과 계약 목록이 같다. `a6fc`는 단독 phase로 관측되지 않았고 정적으로 비보존이다(미관측).

## 발견 사항

1. (검증기 규칙) cleanup 코어의 `CMP.W $10(A0|A6),D0`(`2886`, `2a12`)는 C++가 비교 결과로 C를 Known으로 만든다(`2a00` 제거 경로, 중첩 코드가 아닌 기존 cleanup 코어). 기존 `classify_carry`는 Unknown으로 보아 불일치했으므로, 같은 phase 안의 소비 분기(BCS/BCC)의 실행 경로(BCS 취함 = C=1)를 근거로 기대값을 정하는 규칙을 검증기에 추가했다. 소비 분기가 없는 phase는 실패로 처리한다. C++ 불일치는 아니다.
2. (관측기 기록) fresh 행 `fresh-nested-parent-cleanup-480ac`와 `connected-bios3-stop-to-no-save-nested`의 마지막 프레임 기록 `child_7e/child_80`은 child가 아니라 부모 객체(A6=102000)의 7e/80(25008/182)이다. 연쇄 행 기록은 child(0/255)를 읽는다. 세 행 모두 C++ RAM과 원본 RAM이 같으므로 필드 이름 문제일 뿐이며 검증기는 두 행에 한해 부모 오프셋으로 비교하고 보고서에 기록한다.
3. C++ 불일치는 발견되지 않았다.

## 오래된 검증기 부정 실험의 경계 이동 필요 목록(적용하지 않음)

`a698`과 `a6da`가 실행되므로 다음이 영향을 받는다.
- close 검증기(`metalslug-v237/tools/verify_animation_machine_card_menu_close.py`): `boundary_direct_entry_00a698`(기대 `unsupported animation machine PC`)은 이제 실행되므로 제거하거나 다음 비실행 PC로 이동. `outside_range_entry_00a69a`는 중첩 범위 내부 PC라 `unsupported animation card menu nested PC`로, `outside_range_entry_00a6da`는 block 시작이라 실행되므로 제거. `a698_reached_via_*_with_stop_*`(다른 stop으로 a698 도달 시 `unsupported animation machine PC` 전체 롤백)은 a698 이후가 실행되어 문자열·결과가 바뀐다(2ac2 이후 `odd JSR target` 계열 또는 성공). stop=a698 양성 대조와 `zero_boundary_a698`은 stop 확인이 먼저라 유지 가능. 한계 문구 "a698 is a stop boundary only"와 `boundary_stop_pcs == (A698,)` 단언도 갱신 필요.
- open 검증기(`tools/verify_animation_machine_card_menu_open.py`): `BOUNDARY_PCS`의 `0xa6da`: `boundary_direct_entry_0006da`(기대 `unsupported animation machine PC`), 도달 stop 롤백 실험, `unobserved`의 `a3ac/a3b4`(BSR a6da 이후) 단언과 한계 문구. a6da는 실행되므로 다음 비실행 PC로 이동하거나 제거(`zero_boundary_0006da`는 유지 가능). 이 검증기의 다른 경계(`a2be a406 a662 a70a a71a bd26 9e94 9f36 c2c8`)는 이미 다른 단위에서 실행된다는 점도 같은 정리 대상이다.
- push 검증기(`tools/verify_animation_machine_card_menu.py`)와 input·save 검증기: a698/a6da 참조 없음(영향 없음).

## 미확인·범위 밖

BIOS 카드 처리 내부, 자연 scheduler·IRQ/타이밍, 일반 CCR(native SR 미측정), video port 화면 의미, `2a00` 이후 다음 객체·장면, 직접 플레이·전체 Goal. 접두 단계 0..36은 중첩 관측기가 아니라 open/save 관측의 분할 phase를 재사용했다. 비교는 통제된 fixture(프레임 재진입 PC, BIOS 재개, 입력 바이트, cleanup fixture, 부모 A6) 위에서만 성립한다.
