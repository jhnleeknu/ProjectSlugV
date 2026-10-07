# 장면 좌표 노드의 개별 helper 계약

후속 진행: `scene-coordinates.md`에서기존API의D0..D7/A0/A1/A2/A4승계를확장하고카메라·네노드좌표prefix를연결했다. 아래5register제약은당시검증범위이며기존CLI호환은유지한다.

## 원본과 범위

프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 진입 주소는 고정 ROM CPU 주소이며 canonical decrypted 파일의 같은 오프셋에 대응한다. RAM 주소와 CPU 레지스터 값은 ROM 오프셋과 구분한다. 주소·offset·명령 상수는 별도 표기가 없으면16진수다. 바이트 개수8192/38과 반복 횟수2048은10진수다. 노드·local·world 등의 이름은 분석용 이름이며 원본 소스의 자료형 이름을 복원한 것은 아니다.

메인이 확정한 개별 진입 `43dda`, `16fac`, `43e22`, `16fee`, `43e38`, `43ea8`, `1728c`, `1724c`, `1726c`, `17292`를 `engine/include/ms5/scene_node.h`와 `engine/src/scene_node.cpp`의 `step_scene_node`로 연결한다. `SceneNodeState`에는 전체32bit D0/D1/D3/A0/A1을 둔다. 전체64KiB RAM과 이 다섯 레지스터가 성공 시 출력이며 오류 시 모두 보존한다. 다른 scratch 레지스터·CCR·stack 동등성·자연 호출자 및 하드웨어 시점은 이 API의 계약에 포함하지 않는다.

코어 작성본은 기존 `update_position`의 RAM 효과를 사용한다. 원본 해석 근거는 메인의 확인과 [position-state.md](position-state.md), 추가 명령 창은 [stage-startup.md](stage-startup.md) 및 `artifacts/stage_startup/inventory.asm`에 있다. `477e4`/`1a5a4`/`1a7a8` 전체 연결이나 표시 완료를 개별 helper 구현의 완료로 대신하지 않는다.

## 진입별 저장과 레지스터 출력

A0은 모든 지원 진입에서 보존한다. 아래 범위는 A0을 기준으로 한 offset이며, 원본의 BE word/long 크기를 유지한다.

| 진입 | RAM 효과 | D0/D1/D3/A1 출력 |
|---|---|---|
| `43dda` | `[A0,A0+26)`의38바이트를 지운다. | D0 전체0; D1/D3/A1 보존. |
| `16fac` |43dda 뒤 +2c/+2d.byte, +2e.long, +32/+34.word를0으로 한다. +36.long=ffffffff, +28/+2a.word=0100, +7a.byte=6. 나머지는 이 초기화에서 보존한다. | D0 전체0; D1/D3/A1 보존. |
| `43e22` | 입력 A1을 +10.long에, 입력 D0/D1을 +0/+4.long에 저장한다. +24.word를0으로 만든 뒤43e38 갱신을 수행한다. | D0/D1은 갱신된 +14/+18.long; D3은 갱신 전 +18.long; A1은 저장된 parent 주소. |
| `16fee` | +2c.word를0으로 한 뒤43e22 경로. |43e22와 같은 출력 계약. |
| `43e38` | local/parent로 result·flags·이전 좌표·stamp를 갱신한다. | D0/D1=result +14/+18.long; D3=이전 result Y(+18.long); A1=parent +10.long. |
| `43ea8`, `1728c` | +8/+c.long을 +0/+4.long에 각각 더한 뒤43e38 경로. |43e38과 같은 출력 계약.1728c는43ea8 tail JMP다. |
| `1724c` | D0의 축별 계산 결과를 +8.long에 저장하고 +2c.byte 잔여값을 갱신한다. | D0=결과 전체32bit; D1/D3/A1 보존. |
| `1726c` | D1의 축별 계산 결과를 +c.long에 저장하고 +2d.byte 잔여값을 갱신한다. | D1=결과 전체32bit; D0/D3/A1 보존. |
| `17292` | `[A0+80,A0+2080)`의8192바이트를 지운다.앞80바이트는 보존한다. | D0 전체0; D1/D3 보존; A1=A0+2080. |

Parent는0 또는 유효 RAM 노드다. 기존 position API는 parent result를 local에 더하며 low16 덧셈의 두 carry와 parent flag를 OR한다. stamp0/변경/동일에 따른 previous 저장 순서와 self-parent는 기존 명령 순서를 따른다. parent를 재귀 갱신하지 않는다. 길이·주소 유효성 검사는 host API 계약이며 원본 address exception의 재현은 아니다.

`43e22`/`16fee`는 parent/local 저장을 한 뒤 old world Y를 캡처하므로 alias/overlap에서도 앞선 저장 순서를 건너뛰어서는 안 된다. D3을 임의 입력값으로 유지하거나 lowword만 반환하면 전체 레지스터 계약과 다르다. 메인의 원본 해석에 따른 계약이며 독립 native 검증 결과는 아래 상태 절에서 확정한다.

## 1724c/1726c의 정수 폭

입력 전체값을 V라 하고 factor F는 X 경로의 +28.word 또는 Y 경로의 +2a.word다. 잔여 byte는 각각 +2c/+2d다. 원본 연산은 lowword와 highword를 다르게 취급한다.

1. `P = unsigned16(V.low) * unsigned16(F)`를32bit로 계산한다.
2. P의 lowbyte를 기존 잔여 byte에 더해 byte로 저장하고, 이 byte 덧셈의 carry를 따로 유지한다.
3. P를 signed32 비트 패턴으로 보아8bit arithmetic right shift한다. unsigned multiply에서 얻은 P라도 bit31이1이면 sign extension이 필요하다.
4. `signed16(V.high) * signed16(F)`를 구하고 그 결과를32bit 비트 패턴으로8bit 왼쪽 이동한다.
5. 두 결과와 byte carry를32bit modulo 덧셈해 해당 long 증분과 D0 또는 D1 전체에 기록한다.

이것은 일반적인 실수 곱셈으로 치환한 식이 아니다. lowword unsigned 곱, ASR32 sign extension, 잔여 byte carry, highword signed 곱을 분리해야 한다. C++는 unsigned32 wrap과 명시적인 signed16 변환을 사용하며 signed overflow·음수 왼쪽 shift의 미정의 동작에 의존하지 않는다. factor의 물리 단위와 실제 스테이지별 사용 주기는 이 계약에서 확정하지 않는다.

## 주소·오류와 CLI

RAM은 CPU `[100000,110000)`에 대응하는 정확히65536바이트여야 한다. A0은 짝수 CPU RAM 주소이며 진입별 전체 span을 포함해야 한다: 일반 좌표 진입0x26바이트,16fac는0x7b바이트,16fee/1724c/1726c는0x2e바이트,17292는0x2080바이트다. 사용되는 parent도 짝수 RAM 주소의0x26바이트 span을 요구한다.17292의 최종 A1은 쓰기 뒤의 경계 주소이며 마지막 저장 위치와 구분한다.

오류는 전체 RAM과 `SceneNodeState`를 보존한다. 지원하지 않는 entry, 잘린 RAM, 홀수/범위 밖 A0, 잘못된 parent를 성공처럼 처리하지 않는다. 성공 경로에서 MMIO를 내보내는 API는 아니며 임의 ROM 읽기나 resource loading도 하지 않는다. 이 범위 밖의 원본 CPU fault를 자동으로 emulation했다고 주장하지 않는다.

CLI는 `build/step_scene_node ENTRY D0 D1 D3 A0 A1 INPUT_RAM OUTPUT_RAM`이고 JSON에 `d0,d1,d3,a0,a1`을 반환한다. 숫자는 unsigned32 decimal/hex이며 input/output 경로 alias를 거부한다. CLI 전달값은 이 API의 레지스터 계약만 포함하며 전체 M68000 register bank의 출력이 아니다.

## 검증 상태와 한계

`.venv/bin/python tools/verify_scene_node.py`의 최종 보고서 `artifacts/scene_node/verification.json`을 확인했다. 원본1904조건과 오류94조건이 통과했으며 전체64KiB RAM과 D0/D1/D3/A0/A1이 일치한다. MMIO 쓰기는0회이고 원본 코드는 수정하지 않았다. 보고서 SHA256은 `c900dfc01d94c31633856b8ffae34478ce9ad281366b9322e23ccebd85a0c1c6`이다.

원본 진입부터 실제 RTS까지 비교하며 초기화, parent/overlap/stamp 및 lowword carry, unsigned 첫 곱·ASR32·signed 둘째 곱과 fractional byte carry, 주소 span 경계와17292의8192바이트 clear를 포함한다.8개의 승계 시퀀스는 각각6호출이며 실제 CLI의 RAM과 레지스터 출력을 다음 호출에 사용했다. set 경계의 위치와 parent 입력은 명시적인 host fixture다. 이48호출은1904조건에 포함되며 추가로 더한 수치가 아니다. 잘못된 pointer의 원본 fault는 실행하지 않고 host API/CLI 오류 보존을 확인했다.

전체 `make -j3 all test`는 메인에서 exit0으로 완료했다. `artifacts/scene_node_build_test.log`에는 Python88검사와 C++87개 test executable의 통과가 기록되어 있고 warning/error는0개다. 메인 리뷰는 [0141-scene-node.md](../reviews/0141-scene-node.md)에 기록한다. 이 결과는 개별 scene-node C++ primitives의 비교이며 [stage-startup.md](stage-startup.md)에 기록한 원본1a5a4의16개 제한된 probe와 구분한다. 그 probe는 C++ 동등성 검사가 아니다.

원시 바이트 검사는 이미 재현 가능하다. `inventory_stage_startup.py`는17292 prefix `43e800807000`, `[17298,18298)`의 `22c0`2048회 반복,18298의 RTS `4e75`를 assert한다. 이것은 명령과 저장 span의 증거이며 개별 primitive의 C++ native 동등성 비교와 구분한다. 이 API가 완성되어도 banked 배경 데이터, debug VRAM 경로, 다른 초기화 callee, 전체 `1a5a4`/`477e4` 호출자는 여전히 별도 작업이다.
