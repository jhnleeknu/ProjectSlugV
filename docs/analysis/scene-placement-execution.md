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

명시 창은 1a414..1a442, 1a470..1a526, 43e08..43e22의 3개·81행이다. Inventory SHA256 `ef0725af2a3ec142f2ce3366c4dc7f815d395bdbff45547e439711328731284a`. Decode 성공만으로 전체 배치 실행 검증을 주장하지 않는다. 1a414/1a470 통합 검증은 아래 후속 결과에 기록한다. 일반1a5a4 초기화, 자연 프레임과 플레이 화면은 남아 있다.

## 43e08 검증 결과

원본과 C++의 전체64KiB RAM·12register·RTS/A7+4가 2,020조건에서 일치했다. 오류72조건은 입력 RAM·기존 출력 보존을 확인했다. 8개 node 주소와 5개 parent 조건, XY WORD 경계25조합, scratch register2조합의2,000조건에 실제CLI 승계20호출을 더했다. 4sequence 중16호출은 이전출력을 소비한다. 부모/self/overlap/globalstamp alias, 최소/최대 유효span과100ec6도 포함한다. 이 주소 입력은 합성fixture이며 실제 allocation 호출의 통합 검증은 아니다.

신규 report SHA256 `69cc9998a64b73427ac99aa46579e4c6032dbce91862391f6accd33b588598b6`, CLI SHA256 `0848f156847974de3ba9622c24c59fe0a6b03ca770251c4a8f0506ef53058a9a`. 원본code는 수정하지 않았고 MMIO0, 입력 RAM과 binary hash의 전후 보존을 확인했다.

기존좌표회귀5,248조건(leaf1,132/prefix4,116), 오류135조건도 통과했다. Report SHA256 `ca8a3b769e504965d2c2e2ad0f2d531433576cef5861bced5212be35d2ac7066`, prefix CLI SHA256 `ae63ee760a03336acf18b5016ef06fa2b85f6a0f3d0ac45ec3aad85ebcd7bed4`. 전체make Python175/C++109/경고0이다.

## 배치 실행 API와 지원 경계

`execute_scene_placement(ram, entry, windows, state, parent_a6, error)`는1a414/1a442/1a470을지원한다. 1a442는 eligible record를 최대 한 번만 실행하고 다음 record를 읽지 않는다. `SceneCommandState`의12register와별도A6입력을사용하며A6는원본에서도보존된다. 전체호출이성공한경우에만RAM/state를게시한다. Stream중뒤record가실패해도앞record의할당·좌표·payload와cursor쓰기를모두되돌린다.

리소스는기존MS5D fixed CPU=ROM창을빌려읽는다. Record/bounds/payload는LIVE RAM에서도읽을수있고겹치는복사는WORD별로원본순서대로처리한다. ROM읽기는완전히포함하는유일한창이필요하며부분창·중복창을거부한다. Motion은기존19802가요구하는완전한fixed motion리소스를사용한다. RAM에배치한motion자체는현재지원하지않는다. Native가읽지않는bounds나allocation parent를미리검사하지않는다.

Stream은임시1,048,576record한도이며초과시명시오류다. Inline길이는기존decoder와같이짝수이고8000미만이어야한다. 이제약밖원본동작의완전복원을주장하지않는다. Callback은주소를저장하는데까지이며실행하지않는다. MMIO를생성하는함수는아니다.

```text
build/execute_scene_placement ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 A6 INPUT_RAM OUTPUT_RAM [RESOURCE_FILE_OR_DIR ...]
.venv/bin/python tools/inventory_scene_placement_contexts.py
.venv/bin/python tools/observe_scene_placement_execution.py
.venv/bin/python tools/verify_scene_placement_execution.py
```

CLI JSON에는entry와13개입출력register가있다. RAM과resource의동일경로·symlink·hardlink출력alias를거부한다. Directory인자를사용하면그안의모든.ms5d를로드하므로다른종류의container가섞인경우필요한파일을명시한다. 검증은18placement와37motion의55파일을명시한다.

Contextinventory는41script/814command의18개opcode0c참조를재생성한다. 16개는같은script에앞선opcode00의motion참조가있고2개는없어unknown이다. 앞선참조는현재실행상태나도달성의증거가아니다. Inventory SHA256 `bc4ae71160e6851305d5829c7bdd56ee32869889e92dbb8205e1de169336b65d`.

## 전체 배치 실행 비교 결과

1a414/1a470에서RTS까지원본callee를그대로실행하여전체64KiB RAM과D0-D7/A0/A1/A2/A4/A6를1,625조건에서대조했다. MMIO0,RTS/A7+4를확인했다. 분리observer결과와verifier의새원본실행결과도fixture/input/output hash와register별로일치했다. 원본코드patch나callee대체/호출중contextreset은없다.

Canonical24record 경계조합1,152조건,18root의phase2종36조건,terminal18조건,CLI승계90호출,37motion의entry/phase조합296조건,할당12조건,bounds12조건,RAMalias5조건,fffe gate2조건,호출중phase변경1조건,null1조건이다. Bounds네제외분기의실제PC edge,할당거절의100ec6위치쓰기,474→476 WORD복사의이전쓰기전파,동일호출중phase가1로바뀌어두번째record까지실행되는경우를개별assert한다.

18CLIsequence의90호출중72호출은직전CLI RAM·register결과를사용한다. Host는phase를갱신하고A0/A6를명시적으로다시제공한다. 1a414는RAMcursor에서A0를다시읽는다. 이승계를모든register의무수정전달이나자연scheduler로표현하지않는다.

오류113조건은input과기존output보존을검사한다. Bounds분기를건너뛰는음성fixture와RAM끝을넘지않던복사fixture를메인리뷰/실행에서발견하여수정했다. Alias로length가a50c가되는원본동작은지원밖오류검사로보존하고,지원길이의양성alias는상속byte0으로별도실행했다. 최종corpus전체를다시실행했으며이전부분통과를최종결과로합산하지않았다.

- Native observation SHA256 `716b54add2b2733cbd04b7274e6d6fe852e7762cc8558f32056720da457b2820`.
- Verification SHA256 `341085cfa6992a09e44fefc3d23cfe18b3f409c88e5d1d65abf6102ae994996b`.
- CLI SHA256 `636c4b0769d9aaceee8ddb1c270bdbff48cd100825905c0c478fcd0d303eab43`.

55resource와두manifest,contextinventory의hash를실행전후확인했고메인도현재hash를재확인했다. 전체make Python175/C++110/경고0. 일반1a5a4초기화·자연frame·플레이화면·전체게임복원은미완료다.

## 후속1a442 단일 실행

프레임 제어 단위에서1a442를 추가하고814조건/오류19조건을 대조했다. 동일한 두 eligible record에서1a442는 한 번,1a414는 두 번 실행하며 다음 unmapped 페이지를 읽지 않는 동작도 확인했다. 기존1a414/1a470의1,625/오류113과 이미 구현된 일반1a5a4의221/오류111 회귀를 재검증했다. 최종 hash·재현 명령·상태 승계와 지원 한계는 [scene-frame-control.md](scene-frame-control.md)의 단일 배치와 회귀 절에 기록한다. 위 최초 구현 시점의 hash와 구분한다.
