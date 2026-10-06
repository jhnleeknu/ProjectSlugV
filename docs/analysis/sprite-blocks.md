# 여러 직사각형의 연속 표시

대상 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.

## 원본 근거

고정 ROM/CPU0xced0은 payload의 첫 word를 읽고0100을 뺀다. 남은 값을 swap하여 D7 상위 word에 보관하고0xcede부터 dx,dy,폭/높이를 읽는다. 한 직사각형의 열 처리가 끝나면0xd240에서 D7에01000000을 빼고 carry가 없으면0xcedc로 돌아간다. 따라서 헤더 상위 byte는 블록 수이고, 다음 블록은 별도0100 헤더 없이6byte 좌표/치수로 시작한다.

정방향 refresh의0xf626→0xf2a0, 역방향 일반0x11b6e→0x1180c에서도 같은 블록 반복을 확인했다. 나머지 H/V 및 방향 조합은 이전에 해석한 분기 주소로 직접 실행하여 비교했다. 각 블록은 같은 입력 U/V 및 style을 쓰지만 dx/dy와 치수가 독립적이다. 할당 슬롯은 앞 블록의 결과를 이어받는다.

하위 header byte가0이 아닌 payload도 ROM에 존재한다. 후속 조사에서 표시 소비기에 영향이 없음을 확인하여 kind2에서 원본 그대로 허용했다. 다른 호출자에서의 의미는 미확인이다(docs/analysis/sprite-header.md). 포인터처럼 보이는 연속 값은 테이블 경계나 게임 내 사용 증거로 간주하지 않는다.

## 실제 리소스

모두 bank400000을 CPU200000에 매핑한다. 아래 offset은 복호화된 프로그램 파일 기준이다.

| packed ID | ROM offset | CPU address | 블록 수 |
|---|---|---|---|
| 02382a | 470c9c | 270c9c | 2 |
| 02402a | 470cbe | 270cbe | 3 |
| 02482a | 470cee | 270cee | 2 |
| 000122 | 4bcade | 2bcade | 3 |

`pack_composition_blocks.py`는 원본 group/item 포인터를 따라 이들을 MS5C v1 kind2로 저장한다. payload 바이트는 그대로 보존한다. 실제 게임 호출부와 팔레트가 확인되지 않아 manifest의 use_status는 unclassified다. 원본 소비기를 직접 호출할 수 있다는 사실을 자연스러운 게임 도달 가능성과 혼동하지 않는다.

## C++ 통합과 검증

`emit_sprite_blocks`는 각 블록을 기존 variant emitter에 전달하고 순서 있는 출력과 다음 슬롯을 누적한다. 모든 블록을 검사한 후 호출자 출력을 교체하므로 뒤쪽 손상이나 trailing data가 부분 결과를 남기지 않는다. kind1은 이전과 동일한 단일 블록 검증을 유지한다. kind2 역시 CRC, 실제 파일 길이, 원본 ROM 범위 및 각 블록 경계를 확인한다.

- `verify_sprite_blocks.py --cpp`: 실제 네 리소스, 네 H/V 조합, 양방향, 준비/갱신, 좌표 wrap, 빈/1/380 슬롯, 캐시 경계의2880조건. 다음 슬롯과 모든 비디오 쓰기의 순서/값이 원본과 일치.
- `verify_sprite_pipeline.py --blocks --flips`: 원본 초기화/슬롯 설정/생성기/정렬/준비/갱신과 MS5C C++ 경로를 연속 비교.124제출·32단계에서64KiB RAM과 비디오 쓰기 전체 일치.
- 같은 pipeline에 `--disabled-pool` 적용한124제출·32단계도 일치.
- 기존 kind1 반전 pipeline124제출·32단계 회귀 통과.
- `make all test`: 로더의 잘못된 개수·치수·경계·CRC·후행 byte·255블록, emitter의 다음 블록 좌표와 슬롯 소진 후 오류 원자성 검사 포함.

픽셀 출력, 스케줄링/IRQ, 전체 리소스 목록, 실제 오브젝트 애니메이션과 게임 호출부는 별도 검증이 필요하다.
