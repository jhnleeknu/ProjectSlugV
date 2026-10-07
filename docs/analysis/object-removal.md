# 연결 오브젝트 제거의 후속 분석

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 ROM CPU 주소는 고정 파일 오프셋과 같다. RAM 절대 주소는100000..10ffff다. 메인이 원본 명령을 읽어 해석했다. 아래 앞부분은 구현 전 정적 분석 근거를 보존하며, 확인된 C++ 계약과 원본 비교는 후반에 별도로 기록한다.

## 299c와 보류된 제거

299c는A5=108000을 설정하고 입력D0.byte를 watchdog300001에 쓴다.2782는8ff4의 팔레트 해제 뒤c3fa를 호출하며,c3fa는46ef4를 호출한다. 기존 `restart_static_object`에 팔레트/좌표 정리와 필드 리셋 구현이 있지만 +10.word=0 정적 오브젝트만 지원한다.

정리 후299c는현재A6.callback=270e로 표시한다. +10.word가0이면A0=A6으로271c에 tail branch한다. nonzero이면287e에서 다음 노드의 +10.word와 현재 값을 unsigned 비교한다. 현재 depth가다음 depth보다 작으면29fe로 반환한다. 이때 노드가 리스트에 남아 있으므로 callback270e는 즉시 free를 의미하지 않는다. 다음 노드가 더 깊은 동안 반환을 보류하는 구조로 해석된다.

현재 depth>=다음 depth이면271c로 필드를 리셋하고, A0=현재.previous/A1=현재.next를 읽어 next.previous=previous와 previous.next=next를 쓴다. 현재.next에 freehead104c9c를 넣고 freehead를현재로 바꾸며 freecount104ca0.word를 증가시킨다. A6=previous로 이동한다. 이전 노드도 callback270e이고 depth!=0이면29c0부터 반복한다. 이 반복에서는 앞의 watchdog·팔레트/좌표 해제를 다시 실행하지 않는다. 그래서 제거 요청과 실제 free-list 복귀를 구분해야 한다.

## 하위 제거와 호출자

2a0a는현재 depth를D0.word에읽고 A6=next로 이동한다. 현재로부터 보관한 depth>=이동한노드.depth면 그 노드의previous로A6를돌리고RTS한다. 더 깊은 노드이면299c를호출하고2a0a부터반복한다.299c 자체가A6를 바꿀 수 있으므로 최초 부모 포인터나 최초depth를 매 반복마다 강제로 복원하면 원본과 달라질 수 있다.

2a84는입력A6와A0 모두depth0인지검사한다. 원본은위반시TRAP15다. A6를저장하고A6=A0로이동해2a0a와299c를순서대로실행한뒤입력A6를복원한다. c4cc는3dce→2a0a를실행하고 A6.next부터고정sentinel100820까지순회하며각노드에2a84를호출한다. 저장한현재노드의live next를호출후읽으므로사전에고정목록을만드는것과동일하다고가정하지않는다.

기존 API재사용 후보는 `reset_object_fields`, `release_palettes`, `update_position`, `restart_static_object`다. field reset은 +4/+8/+c/+10 링크·depth를 보존한다. linked path 구현 시 live read/write 순서, cascade, 비정상순환의오류처리, watchdog순서, 반환레지스터를추가검증해야한다. source의 정적분기분석만으로 실행동등성을 주장하지 않는다.

## 목록 재생성

`python3 tools/inventory_object_removal.py`는5개명시진입의59명령후보/22제어참조와5개helper후보를기록한다. 보고서 `artifacts/object_removal/report.json` SHA256 `3e904a609175dfe0121310ce69a8503d41b0d83dd758af4188c43c6bdb45ee69`. 선형RTS도달은모든분기/함수의동작완료증거가아니다. 문서/엔진텍스트참조는재사용후보이며동등성증거가아니다. 이 목록과 실제 실행 검증은 별개의 산출물이다.


## C++ 제거 API

`remove_objects(ram, entry, target, state, ports, error)`는 299c/2a0a/2a84/c4cc만 지원한다. `RemovalState`는 전체 D0/D1/D3/A6를 담는다. target은 2a84의 입력 A0 절대 CPU RAM 주소이며 다른 진입은 무시한다. RAM은 정확히 65536byte, 사용 오브젝트는 짝수 CPU RAM 주소에서 c4-byte 범위가 필요하다. RAM offset은 CPU 주소에서100000을 뺀 값이다. 사용하는 링크와 coordinate parent를 live로 검증한다. 2a84의 depth-zero 위반은 오류이며 원본 TRAP15 처리나 RAM 밖 쓰기는 구현하지 않는다.

루프는 호출당65536-operation budget을 공유한다. cleanup 진입, depth/cascade/children 및 c4cc traversal에 소모하며 budget 소진은 오류다. 잘못된 순환을 거부하기 위한 엔진 범위 제한이고 원본 시간·instruction count를 흉내내는 값이 아니다.

RAM/state/ordered ports는 하나의 transaction이다. late palette ring/coordinate parent/list pointer 오류나 budget 소진은 앞서 만든 watchdog과 RAM 변경까지 모두 보존한다. 성공 시 ports는 이번 호출의 새 목록으로 교체된다. free-list에 저장하는 head 값처럼 그 단계에서 역참조하지 않는 값은 임의로 새 구조체에 변환하지 않는다. pointer/link를 읽는 순서는 원본을 따르며, node를 미리 수집해 일괄 삭제하지 않는다.

## 정리와 반환 레지스터

299c는 cleanup 한 번마다 입력 D0의 low byte를 size1/address300001 watchdog으로 출력한다. cascade에서 이전 inactive node를 free하는 반복은 추가 watchdog·palette·coordinate 정리를 하지 않는다.

`release_palettes`는 기존 optional D3에 더해 마지막 optional D1 포인터를 받는다. 슬롯은 count를 감소시켜 역순으로 읽으며, 각 reference word를 **감산 전에** D1.low에 넣고 D1 상위 word를 보존한다. reference=0/ffff로 감산을 건너뛰는 슬롯도 D1에 읽은 값을 반영한다. count0이면 D1 전체를 보존한다. free ring으로 실제 이동한 노드만 D3.low를 old free tail로 바꾸고 상위 word를 보존한다. 실패 시 RAM/D1/D3를 모두 보존한다.

팔레트 해제 뒤 object+6c.byte를 live로 읽어 D0 **전체**를 unsigned index로 바꾼다. bit7이 있으면 coordinate 정리를 생략한다. 그렇지 않으면 index<8이 필요하며 d4e6+2c*index 구조체의 +26.word=ffff, +2a.word=2, object+6c=ff를 먼저 쓴다. 그 뒤 구조체의 old worldY(+18.long)를 D3 전체에 읽고 `update_position(false)`를 실행한다. 업데이트한 worldX(+14.long)/worldY(+18.long)를 D0/D1 전체에 반환한다. 따라서 palette D3.low 변경은 coordinate active 경로의 full D3 읽기로 덮일 수 있다.

callback을270e로 바꾼 후 depth0이면 `reset_object_fields`만 실행하고 D0=0/D1=ffffffff로 반환하며 A6를 유지한다. nonzero depth의 보류 반환은 D0.low만 depth로 바꾸므로 coordinate worldX의 상위 word를 유지한다. 실제 free 단계의 reset은 D0=0/D1=ffffffff이고 A6는 live previous로 이동한다. D3는 field reset으로 바뀌지 않는다. 2a0a도 매 반복의 실제 A6를 기준으로 D0.low를 갱신한다. 2a84는 성공 시 저장한 입력 A6를 복원하며 c4cc는 traversal 과정에서 반환된 A6를 그대로 사용한다.

이 계약은 D0/D1/D3/A6와 ordered watchdog 쓰기만 운반한다. 나머지 A/D 레지스터, 전체 CCR, callback 실행이나 scheduler 동작을 포함하지 않는다.

## CLI와 재현

```sh
build/remove_object ENTRY TARGET D0 D1 D3 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS
```

숫자는 unsigned32 decimal/0x hex다. RAM input/output/port output의 canonical 경로·hardlink·symlink alias를 거부한다. API 검증을 통과한 뒤에만 출력 파일을 연다. JSON은 d0/d1/d3/a6/writes다. 포트 파일은 각9byte인 size(byte), address(BE32), value(BE32) 레코드다.

```sh
make build/remove_object build/object_removal_test
./build/object_removal_test
python3 tools/verify_object_removal.py
```

단위 테스트는 cleanup 보류→후속 cascade, children의 반환 A6 승계, 2a84의 입력 A6 복원, c4cc의 live next traversal, coordinate oldY/world 출력 및 late rollback을 통과했다. optional palette D1의 count0/reference 읽기/high word 보존/실패 rollback도 포함한다. 기존 정적 restart API와의 회귀 비교는 별도 `verify_restart_registers.py`가 담당한다.

## 원본 대조와 제한

`artifacts/object_removal/verification.json`은 Unicorn2.1.4에서 원본343회와 C++를 비교해 전체 RAM/D0/D1/D3/A6 및 순서 있는 watchdog382개가 일치함을 기록한다. 오류50조건은 출력을 보존한다. 원본 프로그램은 불변이며 중첩 cleanup/helper를 실제 실행한다. coordinate8슬롯·stamp·parent 조합의 leaf144조건과 보류144조건, 실제 원본 palette 초기화/acquire로 만든 leaf6조건과 보류6조건을 포함한다. 보류 경로는271c 미호출 및 현재A6 유지도 확인했다.

승계4시퀀스 가운데3개는 실제 CLI RAM/레지스터를 두 번의 호출 사이에 넘겨 parent 보류→child 제거 cascade를 검사했다. 두 번째 호출의 target A6는 호스트가 명시적으로 선택한다. 나머지1개는 실제28ae allocator CLI의 RAM/D0/allocated A0를299c에 넘긴다. 이 연결의 D1/D3 등 나머지 입력은 explicit fixture이며 allocator의 전체 CPU context가 자연 승계됐다는 뜻은 아니다.

controlled lists의 보류/cascade/traversal은 자연 scheduler 실행과 구분한다. 오류·순환 입력에 대한 원본 실행은 제외한다. 최초 음성 fixture의2a0a self-next는 원본 계약상 정상 반환이므로 오류 가정을 제거하고, c4cc가 sentinel에 도달하지 않는 static cycle로 budget 거부를 검사했다. 원본 TRAP, callback bodies, 다른 CPU 레지스터/CCR/stack 동등성 및 하드웨어 시간축은 이 API 검증 범위 밖이다.

최종 보고서 SHA256은 `4422458b5cfcf56ddb232cc46c1a5f21b2a92df94f16c0eb7b49d01f33fcca3f`다.


optional palette D1 추가 후 기존 `verify_restart_registers.py` 회귀도 원본506조건/오류5조건을 다시 통과했다. 보고서 `artifacts/restart_registers/verification.json` SHA256은 이전과 같은 `05862a1870c440e1ab16e914f038db0dcfce6f1b52c83201f1b8172e15ad4dad`다. 기존 static restart 호출은 optional D1을 넘기지 않으므로 기존 반환 동작이 유지된다.
