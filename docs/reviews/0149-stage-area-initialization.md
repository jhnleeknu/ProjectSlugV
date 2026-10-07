# 구역 진입 분기 통합 리뷰

Baseline `363d4f9`. Canonical ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 명령과 데이터 CPU 주소는 첫1MiB 고정 ROM 오프셋과 같다. 메인은479d0..47a1c 및4e666/d760a/49c32를 직접 해석하고 core·CLI·unit·packer·native verifier의 변경을 검토했다. 구현/회귀, 원본 비교, 리소스/문서/구문 목록은 sol 세 작업에 맡겼다.

## 합류와 대기

처음에만 LIVE A6+7d.byte로 분기한다.0이면47594부터 전체 초기화를 실행하고, 그 외에는48180 두 snapshot과475ca를 실행한다. 첫 구역 초기화가3aea에서 멈추면 내부 GameInitializationState와 외부 레지스터를 함께 보존한다. 재개 시에는 구역 번호를 다시 읽지 않는다. 따라서 대기 중 구역 byte가 바뀌어도 이미 선택한 초기화 경로가 이어진다.

첫 구역 초기화가 끝난 뒤에는 LIVE RAMd684를 읽어0일 때4e666을 실행한다. 공통479fe에서도 LIVE d684가0일 때d760a를 실행한다. 재개 중 host가d684를 변경하는 실제 CLI 승계로 이 gate 동작을 비교했다. 새 API는47a1c 직전에서 끝나며 phase2 상태는 재호출하지 않는다. 오류는 전체RAM/state/external_reads를 보존한다.

## 리소스와 후속 쓰기

4e666은dd2a/dd2b를 순서대로 읽는다. Bit7가 켜진 selector는 보존하고, 그 외에는 원본4e4d2의byte를 읽어dd1e에서 해당bit(mod8)를 지운 뒤 selector를ff로 만든다. 조회 직전 D0 전체가0이라는 앞선 초기화의 계약 때문에 이 호출에서는0..127 주소 창으로 충분하다. 일반 standalone helper의 signed D0.word 전체 범위로 확대하지 않는다.

기존MS5D v1 kind1의 stage_selector_lookup.ms5d는128payload/160container이며 SHA256 `59541b176a2819fd0f7aefbaa481d309c9e06e1fb4b722df52fe28e3285d6046`이다. 원시 주소 창이며 논리128개 레코드라는 주장은 하지 않는다. API는 실제 사용 경로에서만 리소스 주소·크기를 검사하고 CLI는 세 리소스를 먼저 load한다.

d760a는ddec에(1,0108,01a0),ddf2에(0,0108,01a0),ddf8에0096을 저장한 후 기존28ae 할당으로 callback d764a를 설치한다. 빈 pool은 정상 실패이며 callback 본문은 실행하지 않는다. 끝의 두49c32 호출은d734/d738 long을0으로 하고 최종D0=4를 남긴다. D1/D3=0 및 A6 보존도 원본과 비교했다.

## 검증과 검토 결과

전체 `make -j3 all test`는 Python125/C++95, 경고0으로 완료됐다. 로그 `artifacts/stage_area_initialization_build_test.log`.

독립 원본453조건·오류 보존47조건·실제 CLI 승계16개·앞선479ba caller 연결2개를 통과했다. Lookup의0..127 실제 읽기 주소를 모두 관측했으며 selector bit7 skip도 비교했다. Full RAM/D0/D1/D3/A6와 pending, 대기 stack 깊이 및 끝의 A7을 확인했다. Native context 승계 후 SR/A7/stack 재초기화는 없다. MMIO쓰기0, 외부 읽기16이며 재개 읽기는0이다. 원본 고정 ROM과 실행 바이너리는 불변이다.

보고서 SHA256 `76e22c1c64acba38eecb095c5d2e989b17079dd58be3685a4e5d0bf6b4712778`. 대기 해제와 대기 중 구역/gate 변경은 명시적 host 입력이다. 별도의 controlled allocator node10d682는 callback 쓰기로d684를0에서76으로 바꾼다. 이는 gate를 읽은 뒤의 alias/쓰기 순서 검증이며 추가 gate 재조회 증거로 주장하지 않는다.

## 다음 장면 스크립트 근거

메인은1a0b6 dispatch와1a0bc..1a26a의20개 handler operand 길이,1a26a의 종료·진행 조건을 확인했다. inventory_scene_scripts.py는 stage catalog59개 레코드의+2 포인터를 중복 제거해42개를 기록한다. Null은4개 레코드가 공유하고,41개 비영 포인터는 모두 고정 ROM에 있다.855개 구문행이 negative-word 종료점까지 읽혔으며 opcode2c의9개 inline block은 opaque bytes로 보존한다. 음수/홀수 skip 또는 미지원 opcode를 정상 분석으로 간주하지 않는다.

목록 보고서 SHA256 `21b526531039763241fb8a01bc240df657ce0a357e240d21fab50ec8a42dd1a6`. 이 결과는 구문 목록이며41개 스크립트의 실행·의미·자연 도달을 검증한 결과가 아니다.47a1c 이후 사운드 선택, 일반 scene interpreter, callback/scheduler와 전체 게임플레이 복원이 남아 있다.
