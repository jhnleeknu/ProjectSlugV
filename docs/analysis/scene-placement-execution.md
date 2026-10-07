# 장면 배치 실행의 원본 계약

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 고정 ROM의 CPU 주소이며 같은 파일 오프셋이다. RAM은 `100000..10ffff`, A5는 `108000`이다. 메인이 원본 명령과 기존 C++ helper를 대조했다. 이 문서의 전체 배치 흐름은 분석 결과이며, 개별 helper의 구현·검증과 전체 호출의 실행 검증을 구분한다.

## 1a414 스트림 실행

RAMd40e의 LONG을 A0로 읽고 null이면 반환한다. 각 record의 첫 WORD를 D7.low로 읽어 정확히 ffff일 때 종료한다. 그 외에는 unsigned gate <= RAMd418.word일 때만 1a470을 호출하고, 돌아온 A0를 RAMd40e에 게시한 뒤 반복한다. Gate가 크면 현재 record를 소비하지 않는다. Terminal에서도 cursor를 별도로 전진시키지 않는다. 반복 중 phase와 record bytes를 다시 읽으므로 처음 복사한 조건으로 대체하지 않는다.

## 1a470의 시간과 bounds

D7=0 뒤 record gate를 WORD로 읽는다. Record+4/+6 WORD를 D0/D1.low에 읽고 각각 SWAP한 뒤 19802를 호출한다. 입력 레지스터의 원래 상위 WORD가 fraction이 되므로 19802 전에 버리면 안 된다. 반환 뒤 D0/D1/D7을 SWAP한다.

D7.low >= RAMd418.word이면 unsigned 비교로 바로 할당한다. 그렇지 않으면 D2/D3=0, A1=LONG(record+8)로 놓는다. Bounds pointer가 있으면 LONG 두 개를 순서대로 읽으며 A1을 8 증가시킨다. 다음 연산은 WORD 폭이며 BGT/BLT는 signed 비교다.

1. D2.low += D1.low, D2.low -= RAMd3a6.word. D2.low > RAMd3f8.word이면 skip.
2. D2.low += D3.low. D2.low < RAMd3f6.word이면 skip.
3. D2/D3를 SWAP. D2.low += D0.low, D2.low -= RAMd3a6.word. D2.low > RAMd3f4.word이면 skip.
4. D2.low += D3.low. D2.low < RAMd3f2.word이면 skip.

X 계산도 원본에서는 d3a6을 읽는다. d3a2로 변경하지 않는다. Bounds 자료는 현재 18개 canonical 배치 리소스에서 모두 null이지만, 비영 분기를 삭제할 근거는 아니다.

## 할당과 payload

원본은 record A0 LONG과 D0/D1 WORD를 저장한다. A0=record callback(+c), D0.low=0으로 28ae를 호출한다. 반환 carry를 검사하지 않고 D1/D0.low를 복원한다. A0 += 2e, A1=10d38e로 43e08을 호출한다. 따라서 할당 거절의 A0=100e98도 100ec6 위치 영역에 쓰기를 실행한다.

43e08 반환 뒤 A1=A0+48, A0=저장했던 record 주소다. D0.low=WORD(record+2), A0+=10(hex). 길이가 0이 아니면 WORD(A0)+를 WORD(A1)+로 복사하고 D0.low에서 2씩 빼며 0까지 반복한다. 최종 A0는 다음 record, A1은 실제 복사 끝을 가리킨다. Callback 주소는 할당 객체에 저장할 뿐 여기서 호출하지 않는다.

Skip은 D0.low=WORD(record+2), A0=record+10+sign16(D0)로 계산한다. 기존 리소스 decoder는 odd 또는 8000 이상 길이를 지원하지 않는다. 향후 실행 API도 이 제약을 명시해야 하며 이 범위의 native 동작을 복원했다고 주장할 수 없다. Native copy는 WORD 폭의 loop이므로 사전 복사한 payload와 일반 memcpy가 RAM alias에서 같은지 별도 검증해야 한다.

## 43e08 WORD 좌표 초기화

SWAP D0/D1 뒤 CLR.W를 수행하므로 원래 low WORD가 LONG 상위로 이동하고 fraction은 0이 된다. 원래 상위 WORD는 버린다. 이는 기존 43e22의 LONG 좌표 초기화와 다르다. A1을 node+10에 저장하고 D0/D1을 node+0/+4에 저장한 뒤 node+24 WORD를 0으로 쓰고 43e38로 분기한다.

C++ `step_scene_node`에 43e08을 추가하고 기존 position(false)를 사용했다. Node와 parent의 실제 쓰기·읽기 순서를 유지하며 입력 RAM과 12개 공개 레지스터는 실패 시 보존한다. 최소 node span은 26(hex)이며 대체 주소 100ec6도 유효하다. 이 helper에는 리소스 파일을 직접 읽는 동작이 없고, 배치 호출자가 추출한 좌표를 전달한다.

## 재생성

```sh
.venv/bin/python tools/inventory_scene_placement_execution.py
make -j3 all test
.venv/bin/python tools/verify_scene_node_word_position.py
.venv/bin/python tools/verify_scene_coordinates.py
```

명시 창은 1a414..1a442, 1a470..1a526, 43e08..43e22의 3개·81행이다. Inventory SHA256 `ef0725af2a3ec142f2ce3366c4dc7f815d395bdbff45547e439711328731284a`. Decode 성공만으로 전체 배치 실행 검증을 주장하지 않는다. 1a414/1a470 통합, 일반1a5a4 초기화, 자연 프레임과 플레이 화면은 남아 있다.

## 43e08 검증 결과

원본과 C++의 전체64KiB RAM·12register·RTS/A7+4가 2,020조건에서 일치했다. 오류72조건은 입력 RAM·기존 출력 보존을 확인했다. 8개 node 주소와 5개 parent 조건, XY WORD 경계25조합, scratch register2조합의2,000조건에 실제CLI 승계20호출을 더했다. 4sequence 중16호출은 이전출력을 소비한다. 부모/self/overlap/globalstamp alias, 최소/최대 유효span과100ec6도 포함한다. 이 주소 입력은 합성fixture이며 실제 allocation 호출의 통합 검증은 아니다.

신규 report SHA256 `69cc9998a64b73427ac99aa46579e4c6032dbce91862391f6accd33b588598b6`, CLI SHA256 `0848f156847974de3ba9622c24c59fe0a6b03ca770251c4a8f0506ef53058a9a`. 원본code는 수정하지 않았고 MMIO0, 입력 RAM과 binary hash의 전후 보존을 확인했다.

기존좌표회귀5,248조건(leaf1,132/prefix4,116), 오류135조건도 통과했다. Report SHA256 `ca8a3b769e504965d2c2e2ad0f2d531433576cef5861bced5212be35d2ac7066`, prefix CLI SHA256 `ae63ee760a03336acf18b5016ef06fa2b85f6a0f3d0ac45ec3aad85ebcd7bed4`. 전체make Python175/C++109/경고0이다.
