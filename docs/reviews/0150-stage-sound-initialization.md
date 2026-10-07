# 스테이지 사운드 초기화 리뷰

Baseline `4526288`. Canonical ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 명령주소는 고정 첫1MiB의 파일 오프셋과 같다. 메인은3af8 및47a1c..47a94의 분기·operand 폭·대기 복귀 위치를 해석하고 구현/CLI/단위검사/독립검증/목록을 검토했다.

## 공통 word producer

기존 sound_word 내부 큐 알고리즘에 optional register 결과를 연결했다. 초기 command>=2000 또는lowbyte<20은D1을 보존한다. 이후D1.low에 command highbyte를 놓고 필터·검색·중복 교환·enqueue·overflow의 실제 인덱스 변화를 반영한다. Overflow는D0.byte만 바꾸며 command3의 우선 처리에서는D1을 보존한다. 공유 resume_pending을 사용해 기존 RAM-only enqueue/drain/resume와 알고리즘이 갈라지지 않게 했다.

새 API는 전체D0/D1과 conditional external read count를 반환한다. Kind1의 captured pending만 재개하며 D0.byte/D1.low가 captured command/next와 일치해야 한다. 실패는RAM/레지스터/pending/read count를 보존한다.

## Caller 연결

47a1c에서만 LIVE A6+76의 레코드를 기존StageCatalog에서 찾는다. 레코드word10과RAMd686을 비교하고 새 값을d686에 먼저 저장한다. 동일/10fe/19c1은첫 명령을 건너뛰고,19c0은08/20,그외는word producer다. 이후1890/1891/1892를 보내고4d7e를 지운 뒤08/20을 보낸다. 초기 byte pair 전에4d7e를 지우지 않는 순서를 보존했다.

Phase1/4/5/6은word 대기,2/3은초기byte 대기,7/8은최종byte 대기다. Phase9는47a94 완료 경계다. 재개는record/이전d686을 다시 읽지 않는다. 반복 대기는 외부 읽기0이지만 해제 후 새 word 호출이 이어지면 같은 API호출에서 읽기가 추가될 수 있다. D3/A6와D0/D1의상위word를 보존한다.

## 검증 근거

- Primitive:원본2525/오류34,실제CLI승계28,외부읽기64,MMIO0. SHA256 `abc5c9deeec4e3bcc761389c2bdd1406fa8516fdf918a2ef867502bb188ec798`.
- 기존 sound_word 회귀:2241/25, SHA256 `cd7e92af61c905924a06d6500e77d04464c59c707ff306bc1aac46cd1a88a59a`.
- Caller:원본556/오류50,canonical59레코드,12대기하위단계,CLI승계8,구역초기화출력 연결2,외부읽기46/MMIO0. SHA256 `74d5eda9bdc667ff3590807b5ef1dd8e63a389abddec62a34b205335f9aa2b80`.
- 공유코어 prelude 회귀:235/50,기존IRQ37회/68포트 유지. 메인실행exit0. SHA256 `f9f3a9cc50175db1ca4c5c5111b7f954dafb8abb17eb811e0a52bcc13fabbe5e`.
- 전체make Python125/C++97/경고0. `artifacts/stage_sound_initialization_build_test.log`.

Caller는전체RAM/D0/D1/D3/A6/pending과stack 대기 깊이/완료A7을 비교한다. 실제 이전CLI 출력을 승계하며 native context 복원 뒤A5/A7/SR/stack을 다시 초기화하지 않는다. 원본 고정ROM과비교 바이너리는불변이다. 대기해제는host입력이며 자연IRQ/오디오시간축의 검증이 아니다. Canonical word10에는10fe가 없어 그 분기는 합성단위검사만 있고 원본도달 증거는없다.47a54는정상callreturn을가정한47a1c의내부CFG에서비도달이며 외부진입불가능을주장하지않는다.

최종 검증·문서 전달 중 sol 두 작업이 크레딧 소진으로 종료됐다. 메인이 생성된caller 보고서와현재binary를 대조하고 누락된prelude회귀 및최종문서를 마쳤다. 다음은47a94의 일반scene script 실행이며 전체복원은미완료다.
