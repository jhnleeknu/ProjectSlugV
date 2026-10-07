# 메인 e4a 초기화의 직접 호출 근거

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 CPU 주소는 고정 ROM의 파일 오프셋과 같다. 메인이 원본 명령과 테이블을 직접 확인했다. 이 문서는 e74 준비 이전에 남은 작업을 기록하며 e4a 전체가 구현되었다는 뜻이 아니다.

## 호출 순서

- e4a는 e7bf4를 호출한다. e7bf4는8e82로 고정 참조 슬롯을 해제하고 A0=e7b58을8da2에 전달한 뒤, D0.word=6/D1.word=1/D2.word=12로8cda에 tail-call한다.
- e50의 MOVEQ0 뒤 RAM000e.word=0, A6+7e.word=0, A6+84.byte=1, A6+76.long=0을 쓴다.
- e68은903a를 호출한다. 903a→9056은 RAM7def.byte=ff, 이어7dee/7df0/7df1.byte=0을 쓴다. 9546은7dfe.byte 및7dff..7e06의8바이트를0으로 만든다. 이 마지막 루프의 MOVEQ는 D0 전체를0으로 만든다.
- e6e는 A6의 선두 long을e74로 바꾼 뒤 준비 구간으로 이어진다. 기존 e74 준비 API와 분리하여 초기화를 먼저 복원해야 한다.

8e82는256개 노드 중 참조word가ffff인 노드만0으로 만들고8e4a로 free ring에 이동한다. 일반 참조 노드는 보존한다. 8da2는6바이트 고정 등록 레코드를 순회하며 source ID 하위byte의 bucket으로 노드를 옮긴다. 참조word=ffff로 고정하고, source ID가ffff이면 두 ID=ffff와 flags=2를 쓴다. 그렇지 않으면 두 ID와 flags|80을 쓴다. 테이블 종결은 목적 슬롯ffff이며 source IDffff와 다르다. 이 특수 source ID를 실제 팔레트 데이터로 추출하면 안 된다.

## e7b58 등록 테이블

| 슬롯 | source ID | flags |
| ---: | ---: | ---: |
| 0 | 0062 | 02 |
| 1 | 0069 | 02 |
| 2 | 006b | 02 |
| 3 | 006c | 02 |
| 4 | 0063 | 02 |
| 5 | 01b8 | 02 |
| 6 | 0062 | 02 |
| 7 | 0001 | 00 |
| 8 | 0b03 | 00 |
| 9 | 0b04 | 00 |
| 10 | 0b05 | 00 |
| 15 | 0b06 | 00 |
| 11 | ffff | 02 |
| 12 | ffff | 02 |
| 13 | ffff | 02 |
| 14 | ffff | 02 |
| 255 | 0001 | 00 |

모든 레코드의6번째 byte는0이다. e7bbe의wordffff가 종결자다. 총17레코드, 유효 source ID11종이며 고정 등록 뒤 slot6의 혼합 목표를source1/weight12로 설정한다.

## 후속 구현 조건

기존 palette_state의3ef2 초기화와 palette_control의8cda setter는 있으나8e82/8da2 고정 슬롯 재배치의 C++ API는 아직 없다. 연결 리스트의 unlink/insert를 기존 free/bucket 불변식에 맞춰 복원하고, watchdog 쓰기 및 main에 남는 D1/D3를 원본과 비교해야 한다. e7b58 레코드는 버전 있는 런타임 데이터로 추출하고 유효 source ID만 MS5P에 포함한다. 현재 pack_palettes의 단순 BINDING_TABLES 추가만으로는 sourceffff를 실제 데이터로 취급하므로 충분하지 않다.

이 직접 호출 체인은 정적 e4a 진입의 근거다. e4a가 실제 부팅에서 스케줄되는 전체 경로나 BIOS 전후 동작이 관측되었다는 주장은 하지 않는다.
