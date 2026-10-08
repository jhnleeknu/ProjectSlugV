# 장면 프레임 제어·단일 배치 리뷰

Baseline `ee0118d`, branch `codex/scene-frame-control`. 메인이 원본1a29e/1a2b4/1a34c/1a526/1a3d6과 helper289e/197da, 단일 배치1a442를 직접 읽고 기존 계약을 확인했다. 구현·비교 도구·목록화는 기존 gpt-6.1-sol / medium 에이전트3개에 서로 다른 파일로 위임했다. 이 리뷰는 해당 baseline 이후 본 변경 단위를 대상으로 한다.

## 구현

새 frame-control header/core/CLI/unit 전체와 Makefile 변경을 읽었다. API는 전체64KiB RAM·12register·carry를 후보 상태에서 처리하고 성공 시 게시한다. 조건의 true 반환만 duration을 호출하며 null 조건은 duration을 건너뛴다. 사각형의 callback/flag 조기 반환, Y 먼저 검사, packed LONG 덧셈과 전체 SWAP을 보존한다. 원본 WORD 상위 보존·unsigned min/max·signed 비교·ASR/NEG wrap·MOVEQ 전체 덮어쓰기를 확인했다. C++ signed overflow에 의존하지 않는다.

Fixed 창과 live RAM 읽기, BYTE 홀수 허용, WORD/LONG 정렬, 중복/부분 창, 계산 주소 초과와 raw duration 스캔을 검토했다. Terminal-only 및 미확인 type을 허용하는 raw 스캔과 기존 typed motion decoder를 구분한다. 방어적1,048,576-record cap은 합법 주소 범위에서 읽기 실패가 먼저 일어나므로 소진 검사로 표현하지 않는다. CLI 경로/동일 inode 보호와 디렉터리 로더, 출력 JSON도 확인했다.

메인 초기 리뷰에서 packed rectangle unit의 기대값 오류를 발견했다. Base(10,-2)에 extent(1,4)를 LONG으로 더하면 X upper는12이고 점(11,-1)은 내부다. Unit을 carry1과 SWAP 이후 값으로 수정했다. Core에서 D0를 읽은 직후 cameraX를 빼던 순서는 원본처럼 D0/D1을 먼저 읽고 각각 빼도록 맞췄다. Read-only인 이 경우 최종 결과는 같지만 원본 순서를 유지한다. API late failure의 입력 carry0/1, 잘못된 entry/RAM 크기 보존도 unit에 추가했다.

기존 placement 변경은 허용 entry1a442와 record/cursor 처리 직후 조건부 break가 핵심이다. 1a414 loop와1a470 direct record의 기존 동작은 그대로다. Header/CLI/unit diff를 읽고 두 eligible record, invalid 또는 존재하지 않는 다음 record를 읽지 않는 검사와 null/terminal/wait를 확인했다.

## 검증 도구 리뷰와 수정

Observer/verifier와 inventory 전체를 읽었다. Source SHA, 기존 MS5D manifest/container 원본 대조, RAM/stack write guard, 호출 중 context reset 부재, CPU별 register/carry 범위와 실제 출력 승계 여부를 확인했다.

메인 검토에서 설정 fixture의 `int(key[1:],16)` 오류를 발견했다. `d444`를0444에 쓰므로 의도한 fallback이 전혀 실행되지 않았다. `int(key,16)`으로 고치고 실제 RAM 필드값 assertion 및 unsigned min/max/fallback 분기의 양쪽 목적지 검사를 추가했다. 전체 native corpus를 재생성하고 C++와 다시 비교한 최종 결과만 수용했다. X/Y fallback 각각100회를 확인했다.

조건 true에서 비영 canonical/RAM duration으로 들어가는 경우, false에서 잘못된 duration 주소를 읽지 않는 경우를 보강했다. Shake는 이전 결과를 그대로 받는16회 연속 실행을 두 seed에서 검사한다. Duration/setting/shake의 native 쓰기 순서와 selector8의 object/rectangle 주소 순서 assertion도 확인했다. 이것은 native 쓰기 관찰과 C++ source/alias 검증이며 C++ 모든 중간 쓰기의 별도 trace equality는 아니다.

Single placement verifier에서 초기에는 resumed 호출도 cursor/phase/A0/A6를 다시 설정했다. 메인 리뷰 후 후속 두 호출은 이전 RAM·13register를 그대로 전달하게 고쳤다. Canonical root/record/terminal/motion 개수도 상수를 기록하는 데 그치지 않고 실제 검사한 주소 집합을 검증된 manifest와 대조한다. 기존 verifier의 invalid entry1a442는1a443으로 교체했으며 오류 검사 수는 유지했다.

## 최종 증거

- Frame-control2,235/오류133, 전체 RAM·12register·Musashi 실제 C 일치. 선택299조건은 실행 중 SR-read가 없는 Unicorn RAM·12register와도 일치했다. 네 signed rectangle rejection 분기와 설정 다섯 분기 모두 양쪽 목적지를 관찰했다. 네 CLI sequence42호출 중38이 직전 실제 출력 승계다.
- Single placement814/오류19, 전체 RAM·12register/A6 일치.744조건은 record 한 번,70조건은0번, allocator fallback272조건이다. 실제 unmapped110000 페이지를 다음 cursor로 반환하되 읽지 않는다. 동일 입력의 원본 loop는 두 번, single은 한 번 실행한다. 한 CLI sequence3호출 중2회는 외부 재작성 없이 이전 결과를 소비한다.
- 기존 placement1,625/오류113, 일반 초기화221/오류111/3,176,113 ordered ports 회귀가 통과했다. 전체 make Python182/C++117/경고0이며 로그는 `artifacts/scene_frame_control_build_test.log`다. Python 구문과 git diff 검사도 통과했다.
- Inventory5창159행/branch-call41/literal34, 미해독/창 내 gap0. Selector table의 실제 BRA.W와 indexed JSR를 구분했다. Single1a442의 원본 창은 기존 scene-frame inventory에도 보존되어 있다.

메인이 최종2,235개 native 저장 RAM·입력 fixture·register·branch/assertion과 C++ 결과 행을 재대조했다.814개 single 결과의 실제 호출 수/fixture와 canonical 주소 집합, 모든 현재 원본/리소스/oracle/CLI/core hash, 기존 회귀의 현재 binary/resource hash도 확인했다. JSON에 저장된 tuple/list 차이는 JSON 정규화 뒤 비교했다.

| 결과 | SHA256 |
| --- | --- |
| Frame native | `8bff6c9466994aff28d0c338acfd5ed7630349cc6e2cb583b0e586aae3eb810f` |
| Frame verification | `fbe67ae4b00712c0579f6cb991dfdfcfbfaca3d46c6fea22ba3192312f61c2b2` |
| Frame CLI | `f1aab899f94c2afcb007d00de387720910fed339b3066cecb8da80958b66e2a4` |
| Single verification | `e09fa63f51a0a804fa299889b0304d53e0df6e95c1c4e6c9213fbe3843fed633` |
| Placement CLI | `81082e23d829f9dc379733709e4ff6d5597bde04c7a777d2902bc2a7062b93a4` |
| Placement regression | `be49935388ce9b015539035950822119136f2fd7780999fd7b9f61a45271a569` |
| General initializer regression | `0a0e19dd0626d5f4880c983afe07cf8f2959ab4723803eebdaa859d71e95022a` |

이 단위의 통합을 수용한다. 원격 없는 로컬 branch/commit/review이며 ROM·추출 데이터는 Git에 넣지 않는다. 다음은 전체1a73c의 순서대로 기존 script/camera/bounds/update와 이번 함수를 연결하고 원본의 bank/video 출력을 대조하는 작업이다. 외부47642의 d68e 생성도 원본을 읽어 후속 계약에 추가했다. 전체480bc/stage callback·직접 플레이·전체게임 goal은 계속 미완료이며 active다.
