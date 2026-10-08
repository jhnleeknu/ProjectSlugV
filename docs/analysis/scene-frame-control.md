# 장면 프레임 제어

## 근거와 상태

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 여기의 코드 CPU 주소는 fixed 첫 1 MiB에서 ROM offset과 같다. `dxxx`는 RAM `100000..10ffff` 안의 offset이다. 메인이 원본 명령, 기존 script command/일반 초기화 구현을 대조했다. 조건·사각형·기간·설정·흔들림과 단일 배치의 C++ 구현 및 비교 결과는 아래에 기록한다. 전체1a73c와 외부47642 연결은 후속 분석 계약이다.

## 진행 조건 1a2b4

A1=LONG RAMd422. Null이면 바로 carry1을 반환하고 1a29e를 호출하지 않는다. 비영이면 D0.low=WORD(A1)+를 읽어 selector 0/4/8의 handler로 분기한다. Handler carry0이면 그대로 반환한다. Carry1이면 1a29e로 조건과 기간을 재설정한 뒤 carry1을 반환한다.

RAMd422는 scene command **0x2c의 시작 CPU+8**, 즉 기존 scene-script MS5D에 포함된 inline_data를 가리킨다. 15개의 setup dependency와 구분한다. Canonical inline 길이·selector·참조 주소를 별도로 목록화한다. 선택자 밖의 jump를 임의의 handler로 추측하지 않는다.

- Selector0 / 1a2e0: WORD(A1)+를 RAMd43e에 먼저 쓴다. D0.low=RAMd418을 RAMd41e와 unsigned 비교하고 CMP의 C를 EORI1로 뒤집는다. 따라서 phase>=limit이면 carry1이다. 조건이 거짓이어도 d43e 쓰기는 남는다. 조건이 참이면 뒤의 1a29e가 d43e를 다시0으로 만든다.
- Selector4 / 1a334: BYTEd68e가0이면 carry0. 아니면 A0=100cb8의 1a34c가 carry1일 때만 A0=100da8도 검사하고 그 결과를 반환한다. 두 오브젝트의 검사가 같은 A1 사각형을 사용한다.
- Selector8 / 1a2f2: BYTEd68e가0이면 carry0. 첫 사각형에서 첫 오브젝트와 둘째 오브젝트가 모두 carry1이면 반환한다. 하나라도 carry0이면 A1+=8로 두 번째 사각형을 선택하고 같은 순서로 검사한다. 단락 평가에 따라 최종 A0/D0/D1/D4/D5가 달라지므로 boolean 결과만 복원하면 안 된다.

## 사각형 검사 1a34c

원본 289e는 LONG(A0)가270e이면 carry0, 아니면 carry1이다. 1a34c는 이 결과가0일 때 사각형을 읽지 않고 carry1을 반환한다. 비영 결과일 때에는 object+15 bit7이 설정되지 않았으면 carry0이다.

검사가 필요한 경우 D4=LONG(A1), D5=LONG(A1+4), **ADD.L D4,D5**를 한다. 두 축을 독립적으로 더하는 연산으로 바꾸지 않는다. Low WORD의 carry가 high WORD에 전달되는 32비트 덧셈이다. D0.low=WORD(object+42), D1.low=WORD(object+46)에서 camera d3a2/d3a6을 각각 WORD로 뺀다.

먼저 signed16 D4.low<=D1.low<D5.low를 검사한다. 통과해야만 D4/D5 전체를 SWAP하고 signed16 D4.low<=D0.low<D5.low를 검사한다. 내부는 carry1, 그 외 carry0이다. 조기 반환은 아직 실행하지 않은 register 변경을 만들지 않는다. 사각형 끝은 exclusive이며 A1은 이 helper 안에서 변하지 않는다.

## 기간 재설정 1a29e

RAMd422 LONG=0, JSR197da, WORDd41e/d420=D7.low, WORDd43e=0 순서다. 기존 일반 장면 초기화의 duration helper가 같은 연산을 구현한다. 197da는 RAMd3b4를 A1에 읽고 null이면 D7.low=7fff다. 비영이면 10바이트 record를 terminal까지 이동하고 D7.low=terminal의 시간-1이다. 상위 D7은 보존한다. 전체 프레임 통합 시 원본 쓰기 순서와 읽기 창·임시 한도를 유지해야 한다.

## 설정 합성 1a526

D0.low=d41e, D1.low=d420을 각각 WORDd440/d442와 unsigned 최소값으로 만든다. D2.low에는 마지막 d442가 남는다. D0/D1을 d3ee/d3f0에 쓴다.

D0.low=d444, D1.low=d448을 읽는다. D0.low가8000일 때 두 값을 d426/d42a로 바꾸고 d3d6/d3da에 쓴다. Y도 d446/d44a, fallback d428/d42c, 출력 d3d8/d3dc 순서다. Fallback 판정은 D0만 검사한다.

D0.low=unsigned max(d43e,d44c)를 d3fa에 쓴다. 모든 MOVE.W는 입력 register 상위 WORD를 보존한다.

## 흔들림 1a3d6

D0=LONGd408, D1=D0를 ASR.L4한다. D0=-D0+D1을 32비트 wrap으로 RAMd408에 저장한다. D0+=8000 후 SWAP한다. D0.low를 signed16 [-8,8]로 제한하되 범위 밖이면 MOVEQ로 D0 전체를8 또는fffffff8로 바꾼다. WORDd404를 d406에 복사한 뒤 D0.low를 d404에 쓴다.

## 배치 한 번 실행 1a442

A0=LONGd40e. Null이면 반환한다. D7.low=WORD(A0)가 정확히ffff이면 반환한다. unsigned D7.low>WORDd418이면 대기한다. 그 외 1a470을 **한 번만** 호출하고 A0를 RAMd40e에 쓴다. 기존 1a414는 실행 가능한 모든 record를 반복하므로 그대로 대체할 수 없다.

## 전체 프레임 1a73c

RAM10 WORD=1과 bank 제어(2ffff2=2000,2ffff0=0) 뒤 1a2b4를 실행한다. Carry1일 때만 기존 script runner1a26a를 실행한다. 이후 1a526,19b96,19d08 순서다. D0/D1=LONGd3bc/d3c0에서 19802로 시간을 얻고 SWAP D7한다. unsigned D7.low>=WORDd418이면 phase를 갱신한다. 1a3d6, 전체 update1a7a8, 단일 placement1a442를 실행한 뒤 RAM10 WORD=0, bank 제어(2ffff2=1000,2ffff0=0)로 끝낸다.

이 원본 순서와 live RAM·전체 register·ordered port 출력을 유지해 연결해야 한다. 직접 플레이 화면, 전체 stage callback과 게임 복원은 별도 남은 목표다.

### 전체 프레임 연결 시 리소스·상태 계약

후속 compositor는 기존 `SceneMapTransferState`의 D0-D7/A0-A4를 사용하고 placement에 보존된 A6를 전달한다. 12레지스터 helper를 호출할 때 A3를 지우면 안 된다. 각 helper의 결과를 다음 helper의 입력으로 전달하며 RAM·레지스터·ordered ports 전체를 성공 시에만 게시한다. Helper별 독립 실행에서 검증한 상태를 프레임 중간에 다시 주입하지 않는다.

조건은 기존 script MS5D의 inline 주소 또는 live RAM을 읽는다. 조건 성공 뒤 script가 motion cursor와 path·설정을 바꿀 수 있으므로 프레임 시작 시 한 번 선택한 motion 리소스를 계속 사용하지 않는다. 각 motion 호출 직전 현재 RAMd3b4를 다시 읽고 해당 주소를 유일하게 포함하는 기존 exact motion 리소스를 선택한다. Script는 실제 phase gate가 열린 경우에만 decode한다. Null 또는 대기 중이면 사용하지 않는 script와 dependency를 선행 검사하지 않는다. 이 정책은 기존 일반 초기화의 resource 선택과 같다.

기존 `update_scene`은 coordinate prefix, 전체 debug, 네 path 실행을 포함한다. 여기서 생성되는 ports를 앞선 script 출력과 뒤의 bank reset 사이에 순서대로 붙여야 한다. 단일 placement는 마지막에 최대 한 record만 실행한다. Full frame 검증에는 bank2/3 읽기와 video/watchdog 출력 관찰이 필요하며, 현재 2 MiB flat-memory Musashi wrapper만으로 검증됐다고 주장할 수 없다. 이 항목은 후속 구현·검증 설계이며 아직 전체 프레임 실행 일치를 뜻하지 않는다.

### 외부 caller의 조건 입력 갱신 47642

메인이 fixed CPU/ROM `47642..47672`를 직접 대조했다. `480bc`는 `1a73c` 직전에 `47642`를 호출한다. 이 helper는 BYTE RAMd68e를0으로 지우고 A0=100cb8/D0=0, 이어 A0=100da8/D0=1로 같은 `47656`을 실행한다. `289e`의 callback 비교에서 carry0이면 건너뛴다. Carry1이면 object+61의 bit7을 검사하고, 이 bit가0일 때에만 RAMd68e의 D0번 bit를 설정한다. 최종 A0=100da8, D0=1이며 나머지 공개 일반 레지스터는 보존된다.

따라서 d68e는 두 오브젝트의 callback과 +61 상태에서 만든 비트 집합이다. 사각형 helper가 추가로 검사하는 object+15의 bit7과 혼동하지 않는다. 전체 `480bc`를 복원하기 전까지 1a2b4의 standalone fixture가 d68e를 설정하는 것은 명시적인 외부 입력이다. 이 후속 helper는 아직 C++ 구현·원본 실행 비교를 완료하지 않았다.

## Canonical 조건 데이터 목록

`tools/inventory_scene_conditions.py`가 41개 source-verified script의 814개 명령을 확인했다. Opcode2c는 3개 script 안의 9개다. Selector4의 8개는 각각 10바이트, selector8의 1개는 18바이트로 정의한 구조 크기와 정확히 맞는다. 총 98바이트이며 selector0, 빈 inline, 미확인 selector는 이 목록에 없다. 이 사실을 미사용 영역 전체에 확대하지 않는다.

| Script CPU/ROM | Inline CPU/ROM | Selector | Bytes |
| --- | --- | ---: | ---: |
| 0d9edc | 0d9f74 | 8 | 18 |
| 0d9edc | 0d9faa | 4 | 10 |
| 0d9edc | 0d9fd8 | 4 | 10 |
| 0d9edc | 0da002 | 4 | 10 |
| 0da02a | 0da0d0 | 4 | 10 |
| 0da02a | 0da106 | 4 | 10 |
| 0da02a | 0da13c | 4 | 10 |
| 0da02a | 0da172 | 4 | 10 |
| 0dbfca | 0dc06a | 4 | 10 |

목록 SHA256 `b9f0a24ba4df0a5788aa9e70a69fb7d45fb0787852e3af2dd21f414b5a37a56c`. Scene-script manifest SHA256 `9bf33a996fedc298a189fd456eddaa0e9f64f90aa3358277f8f9007ec20f09d8`. 메인이 도구의 catalog 참조 폐쇄, 원본 바이트·컨테이너·manifest 대조와 inline 소유 범위를 리뷰했다. 조건 실행 검증에서는 이 기존 데이터와 합성 RAM 자료를 구분한다.

## C++ API와 지원 범위

`step_scene_frame_control(ram, entry, windows, state, carry, error)`는1a2b4/1a34c/1a29e/1a526/1a3d6을 지원한다. 64 KiB RAM, D0-D7/A0/A1/A2/A4와 carry를 성공 시에만 게시한다. 조건·사각형은 원본 반환 C, 나머지 세 진입은 마지막 MOVE/CLR에 따라 C0이다. 전체 CCR과 포트는 노출하지 않는다.

기존 MS5D v1 kind1과 live RAM을 읽는다. WORD/LONG은 정렬된 완전한 span, BYTE는 홀수 주소도 허용한다. Fixed 읽기는 요청 범위를 유일하게 포함하는 창이 필요하며 겹치는 창·창을 가로지르는 읽기를 거절한다. 사용하지 않는 주소는 미리 역참조하지 않는다. API의 fixed 창 메타데이터와 CLI의 파일 형식 검사는 구분되며 CLI는 제공된 모든 파일을 먼저 검증한다.

기간 스캔은 typed motion decoder를 호출하지 않는다. 정확한 ffff terminal을 찾는 raw10-byte 스캔이며 알려지지 않은 type 값과 terminal-only 입력도 원본대로 처리한다. 읽기 실패·지원하지 않는 selector·주소 범위/덧셈 초과는 transaction 오류다. 방어적1,048,576-record cap은 현재 합법 주소 창에서 읽기 실패가 먼저 발생하므로 소진 검증을 주장하지 않는다. 전체1a73c 지원으로 확대하지 않는다.

```text
make -j4 all test
build/step_scene_frame_control ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 INPUT_RAM OUTPUT_RAM [MS5D_OR_DIRECTORY ...]
.venv/bin/python tools/inventory_scene_frame_control.py
.venv/bin/python tools/observe_scene_frame_control.py
.venv/bin/python tools/verify_scene_frame_control.py
.venv/bin/python tools/verify_scene_placement_single.py
.venv/bin/python tools/verify_scene_placement_execution.py
.venv/bin/python tools/verify_scene_general_initialization.py
```

CLI 출력은 RAM 파일과12register/boolean carry JSON이다. 입력·출력·리소스의 동일 경로, symlink/hardlink 별칭을 거절한다. 리소스 디렉터리 호출도 실제 canonical 조건의 원본 결과와 대조했다.

## 원본 실행 비교

다섯 helper의 **2,235조건/오류133조건**을 통과했다. 고정 revision Musashi에서 원본을 호출해 전체 RAM·12register·실제 CCR.C·RTS/A7+4를 비교했다. 호출 중 CPU context 재설정, 원본 수정, callee 대체가 없고 RAM/stack 밖 쓰기는 거절한다. Native의 설정·기간·흔들림 쓰기 순서를 관찰하고 C++ source 순서 및 alias 결과를 대조했다. C++의 모든 중간 쓰기를 별도 계측한 것은 아니다.

- Canonical9 inline의108조건과108 motion cursor의216조건, selector0 unsigned phase/force250조건을 포함한다. 조건 성공 뒤 비영 canonical/RAM duration과 조건 실패 시 잘못된 duration 주소를 읽지 않는 경로를 별도로 검사했다.
- 사각형 signed 경계·camera wrap864조건, packed Y carry가 X 판정에 영향을 주는 조건, Y 조기 탈락 시 SWAP 전 레지스터 보존을 확인했다. 네 signed rejection 분기 모두 양쪽 목적지를 관찰했다. Selector8은2/3/4회의 실제 사각형 호출과 오브젝트/사각형 주소 순서를 확인했다.
- 설정200조건은 unsigned min/max와 양축 기본값 선택을 포함한다. X/Y fallback은 각각100회다. 메인 리뷰에서 fixture가 d444 등을0444에 쓰던 오류를 발견해 주소를 수정했고, 명시 입력 위치 assertion과 실제 분기 양쪽 검사를 추가한 뒤 전체 corpus를 다시 생성·대조했다.
- 흔들림 standalone454조건과 연속 호출을 포함한다. 네 CLI sequence는5-helper 두 개와16-shake 두 개이며42호출 중38호출이 직전 실제 CLI RAM·12register를 외부 재작성 없이 소비한다. 호출 경계의 entry/stack/SR 설정은 남으며 자연 프레임 실행은 아니다.
- 선택299조건은 실행 중 SR을 읽지 않는 Unicorn과도 RAM·12register가 일치했다. Unicorn의 raw SR.C 일치를 주장하지 않는다. API unit은 late failure에서 입력 carry0/1과 전체 상태 보존도 검사한다.

최종 native SHA256 `8bff6c9466994aff28d0c338acfd5ed7630349cc6e2cb583b0e586aae3eb810f`, verification `fbe67ae4b00712c0579f6cb991dfdfcfbfaca3d46c6fea22ba3192312f61c2b2`, CLI `f1aab899f94c2afcb007d00de387720910fed339b3066cecb8da80958b66e2a4`.

명시된5코드 창159행, branch/call operand41개, literal 명령34개를 보존했다. 미해독/창 안 gap은0이다. Selector table은 실제 세 BRA.W 명령이고 indexed JSR의 최종 목적지를 자동으로 추측하지 않는다. JSON `df920909a4f2d1ed51c1beeae5a48fded6e6f68dc3d5586fba0fe1ca2c7b69f7`, ASM `b1a1aa2fb5248e0bcc3ba005f406586be355c8b76e182aa028f8c704dd7c4eed`. 목록화만으로 실행 분석 완료를 주장하지 않는다.

## 단일 배치와 회귀

기존 `execute_scene_placement`에1a442를 추가했다. 조건을 만족하면 기존 record 처리 후 cursor를 게시하고 즉시 반환한다. 기존1a414/1a470 의미는 유지한다. 원본1a442 **814조건/오류19조건**에서 전체 RAM·12register와 보존 A6가 일치했다. Canonical18root/24record/18terminal/37motion 입력 집합을 manifest와 대조했다.744조건은 record를 정확히 한 번,70조건은0번 호출했고 allocator fallback272조건을 포함한다.

동일한 두 eligible record 입력에서 원본1a442는 한 번,1a414는 두 번 호출한다. RAM10fff0의 record 직후110000 페이지를 실제로 unmapped로 두어도1a442는 해당 주소를 읽지 않고 다음 cursor로 게시한다. 세 CLI 연속 호출 중 두 후속 호출은 이전 RAM·13register를 외부 재작성 없이 사용한다. Callback 실행·반환 CCR·자연 scheduling은 검증 범위 밖이다.

Single verification `e09fa63f51a0a804fa299889b0304d53e0df6e95c1c4e6c9213fbe3843fed633`, CLI `81082e23d829f9dc379733709e4ff6d5597bde04c7a777d2902bc2a7062b93a4`. 기존 배치1,625/오류113 회귀는 `be49935388ce9b015539035950822119136f2fd7780999fd7b9f61a45271a569`, 일반 초기화221/오류111/3,176,113 ordered ports 회귀는 `0a0e19dd0626d5f4880c983afe07cf8f2959ab4723803eebdaa859d71e95022a`다. 기존 verifier의 invalid entry1a442는 새 지원 진입과 충돌하므로1a443으로 교체했고 오류 검사 수는 유지했다.

전체 make Python182/C++117/경고0이다. 메인이 원본·구현·검증 도구·최종 저장 결과와 현재 hash를 리뷰했다. 다음은 이 함수와 기존 camera/bounds/update/script를 전체1a73c 순서로 연결하는 작업이다. 직접 플레이와 전체 게임 복원은 미완료다.
