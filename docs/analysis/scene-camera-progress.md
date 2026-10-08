# 장면 좌표 진행

## 근거와 상태

원본 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 코드 CPU 주소는 fixed 첫 1 MiB에 있어 ROM 파일 오프셋과 같다. `d3xx`는 RAM `100000..10ffff` 안의 오프셋이며 A5=`108000`이다. 근거 목록은 `tools/inventory_scene_frame.py`가 생성하는 `artifacts/scene_frame_disassembly.asm`이다.

메인이 원본 명령과 제어 흐름을 해석하고 C++ API·CLI로 연결했다. 기존 motion MS5D를 사용하며 아래 원본 비교를 통과했다. 경계값 검증을 실제 게임의 자연 도달성 주장으로 확대하지 않는다.

## 축별 요청량: 19a40 / 19ac8

두 함수는 각각 X/Y의 요청량을 D7에 반환한다. WORD 연산은 16비트, LONG 연산은 32비트로 감싼다. MOVE.W는 레지스터 상위 WORD를 유지하고 MOVEQ는 전체 LONG을 덮어쓴다.

| 입력/상수 | X (19a40) | Y (19ac8) |
| --- | --- | --- |
| D0.low / D1.low | d3ce / d3d2 | d3d0 / d3d4 |
| 중심값 | d3d6 | d3d8 |
| 여유값 D5.low | d3da | d3dc |
| D0에서 빼는 값 | 002c | 0018 |
| D1에서 빼는 값 | 0114 | 00b8 |
| 속도 제한 LONG | d3e6 | d3ea |
| 이전/출력 요청량 LONG | d3de | d3e2 |

공통 앞부분은 D7=0에서 시작한다. D7.low=D0.low+D1.low, ASR.W 1, 중심값 차감, D6.low=D7.low 순서다. D6.low에 D5.low를 더한 결과 N이 0이면 D6 전체를 0으로 만든다. D7.low에서 D5.low를 뺀 결과 N이 1이면 D7 전체를 0으로 만든다. 이어 ADD.W D6,D7을 한다. 여기서는 오버플로를 고려한 signed 비교가 아니라 N만 검사한다.

D0.low에서 축 상수를 빼고 N이 1이면 D0=0이다. signed16 D7.low>D0.low이면 D7.low=D0.low다. D1.low에서 축 상수를 빼고 N이 0이면 D1=0이다. signed16 D7.low<D1.low이면 D7.low=D1.low다.

SWAP D7 후 N32가 0이면 7을 더하고 ASR.L 3을 한다. D0=속도 제한 LONG을 읽고 signed32 D7>D0이면 D7=D0로 제한한다. ADD.L D7,D0 후 **BGE는 N xor V를 검사**한다. 분기하지 않으면 SUB.L D0,D7이다. 이를 단순히 감싼 결과의 부호 검사로 바꾸면 안 된다.

X는 D7에서 기존 RAMd3de를 빼고, N32가 0이면 1을 더하고 ASR.L 1을 한 뒤 기존 RAMd3de를 더한다. 결과를 RAMd3de에 저장한다.

Y는 **19b38에서 먼저 D7을 RAMd3e2에 저장**하고 19b3c에서 같은 값을 뺀다. 따라서 차이는 0이며 1을 더하고 ASR.L 1하면 다시 0이다. RAMd3e2를 더해 원래 값을 반환한다. X와 같은 평활화로 고치지 않는다. Y의 이 저장/재조회 순서와 X/Y 레지스터 결과를 함께 검증해야 한다.

## 전체 진행: 19b96

1. D4.low=WORDd3bc, D5.low=WORDd3c0에 camera WORDd3a2/d3a6을 더한다. D4.low를 d3ce/d3d2에서, D5.low를 d3d0/d3d4에서 뺀다. 모두 WORD 연산이다.
2. WORDd3fa가 비영이면 D0/D1=LONGd3bc/d3c0으로 19802를 호출한다. D6=D7을 보존하고 D7=zero-extended WORDd3fa << 8에 D6를 더한다. 이 경로는 제안 좌표 생성과 19832를 건너뛰고 전진 제한 19c28로 간다. d3fa는 부호 확장하지 않는다.
3. 일반 경로는 BYTEd3cc bit0이 설정되면 19a40, 아니면 LONGd3fc를 D7과 RAMd3de에 쓴다. D7+=LONGd3bc를 RAMd3c4에 쓴다. bit1도 같은 방식으로 19ac8 또는 LONGd400을 사용해 d3e2/d3c8을 갱신한다.
4. 19832로 현재/제안 좌표의 D6/D7과 구간을 결정한다. CMP.L D6,D7의 **unsigned carry**로 제한 방향을 고른다. 앞선 19832 내부 N-only 방향 판정과 구분한다.
5. 전진 제한은 D5=WORDd3ee << 16이다. unsigned D7>=D5일 때 D6>=D5이면 D5=D6로 바꾸고 D7=D5다. 후진 제한은 D5=WORDd3f0 << 16이며 D7<D5일 때 D6<D5이면 D5=D6로 바꾸고 D7=D5다. 이후 19978을 호출한다.
6. d3fa 비영이면 좌표를 바로 확정한다. 일반 경로는 설정된 축 bit에 대해서만 아래 검사를 진행한다. 거절은 d3de/d3e2를 0으로 만들고 현재 좌표는 유지한다. 제안 좌표와 경로의 앞선 변경을 되돌리지는 않는다.
7. 확정은 LONGd3c4/c8을 d3bc/c0에 복사한다. 확정/거절 모두 마지막에는 WORDd3ce/d3d0=7fff, d3d2/d3d4=8000으로 초기화한다.

### 확정 전 경계 검사

X는 D1.low=WORDd3c4-WORDd3bc이며 0이면 Y로 진행한다. N이 0이면 D0.low=d3ce-002c, 결과 N이 1이면 거절한다. N이 1이면 D0.low=d3d2-0114 후 **ADD.W D1,D0**를 하고 N이 0이면 거절한다.

Y는 D1.low=WORDd3c8-WORDd3c0이며 0이면 확정한다. N이 0이면 D0.low=d3d0-0018, 결과 N이 1이면 거절한다. N이 1이면 D0.low=d3d4-00b8 후 N이 0이면 거절한다. **Y의 후진 검사에는 X의 ADD.W D1,D0가 없다.** 이 비대칭과 모든 N-only 분기를 유지한다.

## 검증

2,773조건에서 pinned Musashi로 실행한 원본 전체 RAM·12레지스터가 C++와 일치했다. 축별 요청 1,152 / canonical 1,080 / 합성 주소 정규화 465 / null 전체 진행 76이다. Canonical은 37리소스의 108record를 모두 사용하고 합성에서는 36type을 실제 원본 실행에서 관찰했다. Native 합성 자료는 RAM106000, C++는 MS5D60000을 사용하며 출력 A1/RAMd3b4만 정규화한다.

ADD.L의 V=1 관찰은 X385/Y382회로 N xor V 분기와 다음 PC를 검사했다. 그중 standalone axis 335조건은 SR을 실행 중 읽지 않는 Unicorn과도 전체 상태가 일치했다. Y 선행 저장·재조회 후 차이0, unsigned 제한의 다섯 분기 각각 양쪽 목적지, 이전 시간으로의 fallback을 확인했다.

강제 속도 경계에서 D6=fffe0000에 ffff<<8을 더하면 D7=00fdff00으로 감싸지만 원본은 여전히 전진 제한으로 간다. 이 원본 분기와 이후 전체 결과를 확인했다. 전체 진행의 확정 1,164회/거절 457회 중 128회는 거절 전에 실제 cursor가 바뀌었다. 거절 뒤 제안 XY·cursor는 유지하고 현재 XY를 보존하며 두 요청량을0으로 만드는 동작을 검사했다.

오류 102조건에서 입력/기존 출력이 보존된다. 8개의 실제 CLI sequence는 24호출이며 16호출이 직전 RAM·register를 소비한다. 다만 매 호출 bounds·center·margin·speed·old velocity·시간 제한·force·fixed delta·flags·camera WORD를 host가 다시 쓴다. 자연 frame이나 속도 연속 갱신을 검증했다고 주장하지 않는다.

Verification SHA256 `6e98c13f63080f3859d99446d618990d615e2e1c2fb756a818be46b74f0b86c2`, native `94e5b900cb10941cccca10dbf08392218beefb4fda498b6ad8ba72eb61736e65`, CLI `8371c0c02165583693691ae20e33ef0b974b4e97ddc033957cb7243f15445944`. 상세 리뷰는0175다.

## 재현과 범위

```sh
make
.venv/bin/python tools/inventory_scene_camera.py
.venv/bin/python tools/observe_scene_camera.py
.venv/bin/python tools/verify_scene_camera.py
```

원본·runtime motion 자료와 기존 pinned Musashi build가 필요하다. 새 환경의 oracle 생성은 `tools/build_musashi_oracle.py`를 사용한다. API는 RAM·register transaction이며 원본 code patch, callee 중간 reset이나 결과 보정은 없다. 19b96은 필요한 시점에 기존 motion API의 exact resource 검사와 한도를 사용한다. RAM motion·범위 밖 record는 명시 지원 밖 오류다. CCR·cycle timing과 전체 1a73c frame, 직접 플레이 화면은 이번 완료 범위가 아니다.
