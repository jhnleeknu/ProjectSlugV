# Stage cue frame e8a48 후속 계약

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. Fixed 첫1MiB CPU=ROM offset, RAM CPU100000..10ffff,A5=108000이다. 아래는 메인이 원본 명령을 읽은 후속 계약이다. 이번 문서만으로 구현·실행 비교 완료를 뜻하지 않는다.

## 초기 선택과 helper

- e89fa..e8a0c: A0가null이면 e89ec로 바꾸고 LONG RAMde2a=A0를 쓴다. 다른 일반 register는 그대로다.
- e8a1c..e8a3a: A0가null이면 e89e4로 바꾸고 LONG RAMde26=A0,BYTE de2e=ff,de2f=0을 쓴다. 기존 stage entry의 직접 cue 초기화다.
- e8ad0..e8af4: A0=LONG RAMde2a. Null이면 D0를 변경하지 않고 반환한다. 비영이면 D0.low=WORD RAMd418을 한 번 읽고 unsigned D0.low>=WORD(A0+12)이면 A0에12를 더해 반복한다. 처음으로 다음 gate보다 작아지면 LONG RAMde2a=A0를 쓰고 반환한다. Terminal 검사나 고정 반복 횟수를 새로 만들어 넣지 않는다. 범위 밖 또는 무한 진행에 대한 API 방어 계약은 구현 시 따로 정의해야 한다.
- e8af4..e8b18: D0.low=WORD(A0),D1.low=WORD(A0+2). BYTE(A0+4).bit1이 켜졌으면 WORD RAMd3bc를 D0.low에 더한다. 같은 byte.bit0이 켜졌으면 WORD RAMd3c0를 D1.low에 더한다. 상위 WORD와 다른 일반 register는 보존한다. 여기서 읽는 주소는 d3a2/d3a6가 아니다.

원본 e89e4..e89ec은8byte default cue다. e89ec..e89f8의12byte default record 다음 e89f8..e89fa에ffff WORD가 있다. e89fa부터는 코드다. e8a0c..e8a1c의16byte lookup 뒤 e8a1c부터도 코드다. 더 넓은 indexed raw 조회 창을 보존할 경우 이 경계를 논리 데이터 테이블 크기로 확대 해석하면 안 된다.

## e8a48 본체

BYTE RAMde2f가비영이면 먼저0으로 만든다. A0=LONGde26,D0=0,D0.byte=BYTE(A0+7),SUBI.W1c,D0 순서로 계산한다. Unsigned D0.byte>=20(hex)이면 할당을 건너뛴다. 그렇지 않으면 이 index WORD를 stack에 보존하고 e8af4를 호출해 XY WORD를 얻는다.

XY를 stack에 보존한 뒤 A0=d5f16,D0.low=0,A1=100bf4로2986을 호출한다. 반환 A0+2e를 A0로 만들고 A1=10d38e,XY를 D1/D0.low에 복원해43e08을 호출한다. 그 뒤 A0에48을 더하고 index를 D0.low에 복원한다. A1=e8a0c,D0.low<<=2,ADDA.W D0,A1 후 `(A1)+` WORD 두 개를 `(A0)+` WORD 두 개로 순서대로 복사한다. 2986의 실제 fallback/register 계약과43e08 전체 반환을 연결해야 한다.

그 다음 BYTEde2e가0이면 e8ad0을 실행하고 **반환 A0+4**를 A1에 넣어 LONGde26=A1을 쓴다. e8ad0의 null A0에 대해 별도 null 우회는 없다. 마지막 BYTE10f001.bit1이0이면 반환하고1이면 e8b18의 debug 경로로 이어진다.

Debug는 A1=10d38e,A0=LONGde26 후 A0null이면 반환한다. 비영이면 e8af4 다음 D0.low+=WORDd3a2,D1.low+=WORDd3a6를 수행하고 SWAP D0,MOVE.W D1,D0로 packed XY를 만든다. D1=ffffffff,CLR.W D1, unsigned D0.low>=01e0이면 D1.bit1을 켠다. D5=ffffffff,D7=0000ba2b로cd58을 호출하고e8b58에서 반환한다. 기존 sprite producer는 callback과 queue 대기 상태를 가진다. 이를 성공하는 no-op으로 대체하면 안 된다.

전체480bc 연결에는 위 helper 외에도 sprite producer의 전체 register/pending 계약, 원본 cue/stream 및 indexed raw lookup 리소스, 실제 allocator 호출을 검증해야 한다. 현재는 이 후속 분석 계약까지이며 직접 플레이 화면이나 전체 스테이지 프레임 완료를 주장하지 않는다.

## 2986 전체 wrapper 계약

2986은 입력 A6를 stack에 보존하고 A6=A1로28ae를 호출한다. 반환 후 원래 A6를 복원하고 SR을 보존한 채 **원래 A6+6a BYTE를 반환 A0+6a BYTE에 쓴다**. 이 복사는 할당 실패에도 실행된다. 따라서28ae의 실패 A0=100e98에서도 copy 목적지는100f02다.28ae의성공/실패carry를복원하며 나머지 일반register효과는기존allocate_object의D0/A0/A1이고A6는원래값이다. A6 source와A0 destination이liveRAM에서겹치면원본순서의읽기/쓰기를유지한다. BYTE접근은홀수주소도가능하다.

기존 allocate_object는28ae를이미검증했으므로이wrapper에서재사용한다. 실패를성공하는별도할당으로바꾸거나copy를성공시에만실행하면안된다.43e08은기존step_scene_node가전체12register를운반하므로frame연결에서는A3를별도로보존해재사용할수있다.

## cd58 전체 register와 대기 재개 후속 계약

메인이 inventory의 cd50..ce02 원본 명령을 다시 읽어 확인했다. 기존 `submit_sprite`는 메모리 결과와 status만 제공한다. 아래 register/pending 계약의 구현·원본 실행 검증은 아직 완료하지 않았다.

- cd52는 LONG RAM9152=A0만 쓴다. cd58은 이 LONG을 A0로 읽고 JSR(A0)를 **클리핑 전에** 실행한다. cd50은 RTS다. 지정된 raw 인코딩 검색에서 cd52 참조가0건인 것은 다른 callback이 불가능하다는 증명이 아니다. 후속 구현에서 default cd50만 지원할 경우 다른 callback은 오류로 명시해야 한다.
- 먼저 D0.low에서0040을 빼고 unsigned0280 이상이면 그대로 반환한다. 통과하면0040을 더해 복원하고 SWAP D0, D0.low+=0160을 수행한다. unsigned0400 이상이면 이 상태로 반환한다. 통과하면0160을 빼고 다시 SWAP한다. 따라서 clipped 반환에도 D0/A0 변화가 있다.
- A1=108b34; D6.low=WORD8d3a; D6.low=(D6.low+2)&01fe. D6.low!=WORD8d34이면 cdaa로 간다. 같으면 D4.low=WORD8d36을 읽는다. D4.low==WORD8d34이면 full 반환한다. 그렇지 않으면 cda4의 비교 반복에서 **캡처한 D4.low**와 live WORD8d34가 같아지기를 기다린다.
- 대기 재개는 callback·클리핑·D6/D4 산출을 다시 실행하는 새 제출과 다르다. 최초 대기 시점의 일반 register 및 재개 PC=cda4를 유지하고, consumer가 변경한 RAM에 대해 같은 D4와 비교해야 한다. 재개 시 callback pointer/8d36/8d3a가 바뀌어도 그것들을 다시 읽지 않는다. 기다리는 동안 생성 측의 RAM 쓰기는 아직 없다.
- cdaa에서 WORD8d3a=D6.low를 먼저 쓴다. D1.bit6을 지우되 이전 bit 값으로 normal/deferred를 선택한다. Normal은 D4.low=WORD8d38, D3.low=WORD(A1+signed(D6.low)), WORD(A1+signed(D4.low))=D3.low 순서다. D4.low=(D4.low+2)&01fe 후 WORD8d38=D4.low다.
- Deferred는 A0=108f4e,D4.low=WORD914e 후 **WORD914e+=2를 먼저 쓴다**. 이어 D3.low=WORD(A1+signed(D6.low)), WORD(A0+signed(D4.low))=D3.low다. 원본의 접근 순서는 alias에서 결과에 영향을 줄 수 있다.
- 합류하면 A0=107f34+signed(D3.low). SWAP D7; D0.low<<=7; D7.low|=D0.low; SWAP D7; D1.byte&=07; D0.low=D5.low; SWAP D0; D0.low<<=6; LONG(A0)=D0,LONG(A0+4)=D1,LONG(A0+8)=D7을 쓴다. D2/D5와 A2/A3/A4/A6는 default callback에서 보존된다. WORD/BYTE 연산은 나머지 상위 bit를 보존한다.

기존 typed queue API의 cursor/record invariant와 원본이 계산하는 signed-WORD 유효 RAM 주소를 구분해야 한다. 새로운 일반 register API가 지원할 범위는 문서에 명시하고, 지원 밖 접근을 정상 제출로 바꾸지 않는다. RAM/state/pending 실패 원자성, clip/full 양쪽의 실제 반환 상태, pending 후 consumer 변화에 대한 원본 대조가 필요하다.

## 구현 완료 범위와 재현

이번 단위는 e89fa/e8a1c/e8ad0/e8af4 및2986만 구현했다. `step_stage_cue_control`은13개의 변경 가능한 일반 register와 read-only A6를 운반하고,2986에서만 allocation_carry를 원본 C 결과로 갱신한다. 다른 네 entry에서는 이 별도 API값을 보존하며 전체 native CCR 동일을 주장하지 않는다. 오류는 RAM/state/carry를 모두 보존한다. Fixed kind1 MS5D 또는 live64KiB RAM의 완전한 접근만 지원한다. WORD/LONG은 정렬이 필요하고 BYTE는 홀수도 허용한다. 읽기가 필요한 곳에서 여러 fixed window가 겹치면 모호한 리소스로 거부한다.

기본 cue8byte, stream12byte+ffff WORD14byte를 `tools/pack_stage_cue_control.py`로 추출한다. 총22payload/86container bytes이며 원본 SHA, CPU=ROM 주소, CRC와 canonical header를 검증한다. `ffff`는 기본 데이터의 마지막 WORD 표기다. 원본 e8ad0에는 특별한 종료 분기가 없으므로 phaseffff에서 다음 창 밖 접근을 성공하는 종료로 바꾸지 않는다. C++ loader를 통해 실제 읽고, 해당 리소스를 사용하지 않는 경로는 파일 없이도 실행된다.

재현 명령:

```sh
.venv/bin/python tools/pack_stage_cue_control.py
.venv/bin/python tools/inventory_stage_cue_frame.py
make -j2 all test
.venv/bin/python tools/observe_stage_cue_control.py
.venv/bin/python tools/verify_stage_cue_control.py
```

원본 Musashi555조건의64KiB RAM·14register·allocation 결과를 실제 CLI와 대조했다.2986/28ae158호출은 성공69/실패89이며 originalA6 후속 복사는158회 모두 관찰했다. Allocator가 먼저 바꾼 source byte를 후속복사에서 읽은12조건의 입력값·live값·선행 write를 기록했다. 조건분기8개는 두 실제 목적지를 관찰했고,28d6의 null freehead 분기는 지원하는 정상 allocation graph에서 제외하고 C++ 오류조건으로 따로 검증했다. 입력/출력/리소스 보존 오류155조건도 통과했다.

세 sequence12호출 중9회는 직전 CLI 출력을 소비한다. Allocation sequence는 caller 입력A0/A1을 다시 지정하고, stream sequence는 phase WORD를 호스트에서 갱신한다. Cue sequence는 호스트 변경 없이 승계한다. 이를 자연 스테이지 실행 또는 모든 sequence의 무변경 승계라고 표현하지 않는다. Native 관측은 ROM patch/stub/호출중 reset/hook SR읽기를 사용하지 않는다.

메인이 core/header/CLI/unit, packer/inventory/관측/비교 도구를 읽고 verifier의 branch 집계 대조를 보완했다. 전체make Python182/C++122/경고0 (`artifacts/stage_cue_control_build_test.log`). 원본/추출물은 Git에서 제외한다.

- Native observation SHA256: `b820dff0be27fbc038c563473840fc6bb3652788c57bf200c7248d0c1a06da52`
- Verification SHA256: `3607ca69a390b0d133ece913f9ac5956ed99f221d1aa22e597d0bdd29c7d2e20`
- CLI SHA256: `04231d0f1ef04ed52a865e6e2bcc951e0ae82031d5f1e8ec01b06926cbdf4f5b`
- Default resource manifest SHA256: `aa5d59728cf10b841e314f2b838606f23ce44b6a15c83b62462349700de5450c`
- Inventory JSON SHA256: `d113549ead14d888670f8a41346c8e320fae9b2e1c0918647afc6070743129a7`

Inventory는5개 code창147명령/0gap, 별도DATA3영역, 기존catalog59record의LONG+6와42개nonnullroot의첫8byte만 기록한다. Raw cd52 참조0건으로 callback 폐쇄성을 추론하지 않는다. 전체e8a48과cd58 pending은 후속 작업이며 이 단위로 직접플레이나전체480bc 완료를 주장하지 않는다.
