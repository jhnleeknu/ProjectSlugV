# 슬롯 영역 설정과 비활성 상태

원본 프로그램 SHA256:29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f. 설정 함수의 고정 CPU 주소/파일 오프셋은0xcd1c..0xcd46이다.

D0 하위word가0이면 pool0(RAM0x108d3e), 그 외에는pool1(0x108d46)을 선택한다. D1 하위word가380 이상이면0xffff로 바꾼다. 바뀐 D1이 D2 하위word 이상이면 D2도0xffff로 바꾼다. 비교는 unsigned16이다. 선택한 영역에 BE word `[D1,D2,D1,D2]`를 저장하며 다른 영역은 변경하지 않는다.

상한을 항상380으로 clamp하는 함수가 아니다. 예를 들어 입력 하한1·상한0은 `[1,ffff,1,ffff]`가 된다. C++ configure_sprite_pool은 이 변환을 그대로 보존한다. 준비/갱신 dispatcher가 실제로 지원하는 상태는 범위0..380 안의 유효한 경계 또는 word4개 모두0xffff인 비활성 상태다. 혼합 sentinel/영역 밖 경계는 현재 계약에서 거부한다.

## 비활성 영역

0xccd6 초기화는 두 영역을 모두0xffff로 둔다. 원본 일반 emitter는 현재/한계값이 같아 명령을 내지 않으며 정리 루프도0회다. 이 상태는 잘못된 초기 RAM이 아니라 비활성 표현이다. 앞선 C++ dispatcher의 범위 검증은 이를 거부했으므로 수정했다.

C++는 비활성 영역의4word를 보존하고 명령을 내지 않는다. 해당 레코드의 marker/style/X와 리소스 ID/payload 검증은 유지한다. 유효한 payload를 쓰기 없는 emitter 호출로 검사하며 결과 slot0을 실제 비활성 cursor에 덮어쓰지 않는다. 전체 큐의 ready·방향·읽기 인덱스 갱신은 정상적으로 진행한다.

## 호출부 근거와 제한

고정 코드0x44086은0x4410c로 RAM0x10d496/0x10d498에서 D1/D2를 가져온 뒤 D0=0으로0xcd1c를 호출한다. 이는 한 영역만 설정하는 실제 호출 경로다. 단순 바이트 검색의 다른 후보를 모두 실행 코드라고 단정하지 않았다. 전체 초기화·화면 모드 호출 그래프와 슬롯 분배 함수들의 상위 의미는 아직 조사 중이다.

## 검증

- verify_sprite_pool.py: selector0/1/ffff×하한8×상한8=192조건, 원본0xcd1c와 C++의64KiB RAM 전체 일치.
- analyze_sprite_prepare_queue.py --cpp --disabled-pool:96조건 준비 및 후속 갱신 원본 일치.
- analyze_sprite_refresh_queue.py --cpp --disabled-pool:96조건 별도 갱신 원본 일치.
- verify_sprite_pipeline.py --disabled-pool 및 기본 실행: 각124제출·32준비/갱신 단계 일치. 슬롯 word를 직접 만드는 대신 원본/C++ 설정 함수를 호출한다. 설정 인자는 통제된 실험값이며 실제 게임의 모든 화면 모드에서 관찰한 값이라는 뜻은 아니다.
- C++ 테스트는 두 방향·두 영역·양 dispatcher의 비활성 유지, 잘못된 payload/혼합 sentinel의 오류·상태 보존을 검사한다.
