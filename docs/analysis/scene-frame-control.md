# 장면 프레임 제어: 후속 구현 계약

## 근거와 상태

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 여기의 코드 CPU 주소는 fixed 첫 1 MiB에서 ROM offset과 같다. `dxxx`는 RAM `100000..10ffff` 안의 offset이다. 메인이 원본 명령, 기존 script command/일반 초기화 구현을 대조한 계약이며 아직 아래 프레임 제어의 구현·실행 일치를 주장하지 않는다.

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

목록 SHA256 `b9f0a24ba4df0a5788aa9e70a69fb7d45fb0787852e3af2dd21f414b5a37a56c`. Scene-script manifest SHA256 `9bf33a996fedc298a189fd456eddaa0e9f64f90aa3358277f8f9007ec20f09d8`. 메인이 도구의 catalog 참조 폐쇄, 원본 바이트·컨테이너·manifest 대조와 inline 소유 범위를 리뷰했다. 실제 조건 평가 및 모든 selector 동작 검증은 후속 작업이다.
