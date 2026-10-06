# 스테이지 선택 목록과 상태

## 원본 근거

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
아래 CPU 주소는 고정 ROM 범위의 복호화 파일 오프셋과 같다.

`474e2`는 D0의 unsigned word가19 이상이면 0으로 보정하고, `474f4`의19개 BE32 포인터에서 그룹 주소를 얻는다. `48262`는 항목 수를 반환하고, `47540`은 선택 레코드의 payload 주소, `4827e`는 그 주소+18의 이름 스트림 주소를 반환한다. 범위를 벗어난 area는 record/name 주소0으로 반환한다. 그룹 번호를 표시 이름이나 최종 게임의 스테이지 순서로 치환하지 않는다.

| 그룹 | 원본 주소 | 레코드 수 |
|---:|---:|---:|
| 0 | dbadc | 11 |
| 1 | dcd14 | 6 |
| 2 | d99e2 | 14 |
| 3 | db6cc | 5 |
| 4 | dd382 | 9 |
| 5 | 472be | 3 |
| 6 | 47332 | 3 |
| 7 | 473a2 | 3 |
| 8 | 4741a | 2 |
| 9–15 | 4745c..47474, 4바이트 간격 | 각각0 |
| 16 | 47478 | 1 |
| 17 | 4749c | 1 |
| 18 | 474c0 | 1 |

합계19그룹·59레코드다. 이름 중 테스트를 가리키는 byte 문자열이 있다. 이것만으로 미사용 여부나 실행 가능성을 확정하지 않는다. 참조된 게임 코드와 맵/이벤트 동작은 별도 분석 대상이다.

## 원시 구조와 런타임 리소스

그룹은 보존 대상 BE16 header로 시작한다. 이어서 BE16 signed length와 length만큼의 payload가 반복되며 length0이 종료다. 다음 레코드로 이동할 때 length word 다음 주소에 signed length를 더한다. 실제 추출 그룹에서는 양의 짝수 길이만 발견됐다.

payload의 첫18바이트는 아직 불투명 header로 보존한다. 나머지 이름/제어문자/정렬 padding도 byte 그대로 유지한다. NUL 존재 검사는 구조 검사이며 모든 제어문자의 의미를 검증한 것은 아니다.

기존 MS5D v1을 사용한다. 큰 주소 간격을 포함한 새 포맷을 만들지 않고 index 및 각 그룹을 별도 창으로 저장한다.

- `extracted/runtime/stages/stage_index.ms5d`: CPU474f4, payload76바이트.
- `stage_group_00.ms5d`..`stage_group_18.ms5d`: 그룹 header부터 마지막 종료 word까지.
- `manifest.json`: 원본 해시, 안정적인 그룹/레코드 ID, CPU/ROM 주소, 레코드 크기, 원시 header 및 이름 bytes.

C++ `load_stage_catalog`는 index와19개 창의 주소 대응, 길이/종료/범위를 검사하고 `StageCatalog`에 원시 payload를 보관한다. `query_stage`는 동일한 보정과 count/record/name 조회를 제공한다. 카탈로그 실패와 조회 실패는 기존 출력 객체·값을 보존한다. 숫자 이름 변경이나 Unicode 변환은 하지 않는다.

## 선택 상태 변경

`set_stage_state`는 다음 원본 RAM 동작을 재구성했다.

- `4823a`: 입력 word<19이면 해당 byte를 RAMd680에 기록, 나머지는0. RAMd681은0으로 초기화.
- `48250`: 입력 하위 byte를 RAMd681에 기록.
- `48256`: RAM0bad의 byte에1을 더해 byte 순환 후 RAMd681에 기록. 이 경로는 입력 value를 사용하지 않는다.

RAM offsetd680/d681은 CPU10d680/10d681이다. 여기서는 선택값 기록만 수행하며 게임의 스테이지 전환 전체가 아니다. 메뉴9602/9802가 이 helper들과 count/name 조회를 사용한다. 해당 콜백의 포맷팅·동적 출력 통합은 다음 작업이다.

## 검증

`verify_stage_catalog.py`는 원본 명령을 바꾸지 않고19그룹·59payload·index·manifest 원시 바이트를 확인했다. C++와 원본 count/record/name을450조건에서 비교했다. 모든 실제 area와 빈 그룹, stage19이상 보정 및 큰 area를 포함한다.

선택 상태는 전체64KiB RAM을272조건에서 비교했다. stage/area word 경계16조건과 next-area source byte 전체256조건이 일치했다. C++ 단위 검사는 잘린/음수/홀수 레코드, 이름 NUL 누락, 종료 후 데이터, 마지막 그룹 로드 실패의 기존 카탈로그 보존, 변경된 source 주소 및 잘못된 상태 입력의 보존을 확인했다. `make all test` 통과.

```
.venv/bin/python tools/pack_stage_catalog.py
make all test
.venv/bin/python tools/verify_stage_catalog.py
build/query_stage extracted/runtime/stages STAGE AREA
build/stage_state INPUT_RAM OUTPUT_RAM ACTION VALUE
```

ACTION은0=그룹선택,1=구역값기록,2=RAM0bad 기반 다음구역이다. 아직 stage record header 의미, 참조 대상 데이터 전체, 자연스러운 실행 도달성 및 최종 화면·음향은 검증하지 않았다.
