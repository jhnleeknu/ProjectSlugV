# 직사각형 스프라이트 반전

대상 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
아래 주소는 고정 프로그램 영역 CPU 주소이며 이 영역에서는 ROM 파일 오프셋과 같다.

| 할당/단계 | 일반 | 좌우 | 상하 | 양쪽 |
|---|---|---|---|---|
| 정방향 준비 | ce82 | d250 | d620 | d9f2 |
| 역방향 준비 | 117b2 | 11b7e | 11f4c | 1231c |
| 정방향 갱신 | f246 | f636 | fa28 | fe26 |
| 역방향 갱신 | 13b66 | 13f52 | 14340 | 1473a |

style bit0는 좌우, bit1은 상하 반전이다. 큐 dispatcher는 bit2로 슬롯 영역을 고른 뒤 그 비트를 제거한다. 반전은 원본 소스 데이터 순서를 바꾸지 않고 출력 좌표와 목적지 타일 주소를 바꾼다.

column과 row는 0부터 시작한다. 모든 최종 word는 하위16bit를 쓴다.

- 일반 X: `(u+dx)*64 + column*1024`.
- 좌우 X: `(u-dx)*64 - (column+1)*1024`.
- 일반 Y 기준값: `v-dy`.
- 상하 Y 기준값: `v+dy-1+height*16`. 원본의 NEG/NOT 연산 때문에 `-1`이 필요하다.
- 갱신 Y word: `((기준값*128)&65535)|height`.
- 일반 목적지 row: `row`, 상하 반전 목적지 row: `height-1-row`.
- 속성 word: `((원본속성+(style&0xff00))&65535)^(style&255)`.

슬롯 상한 확인, 화면 밖 열 생략, 역방향 선감소, 캐시된 열의 Y 전용 갱신 순서는 기존 분기와 같다. C++는 unsigned32 연산으로 감산과 곱셈의 wrap을 보존한다.

## 런타임 연결

`emit_sprite_rectangle_variant`가 네 가지 변환을 선택한다. 기존 네 개 고정 분기 API는 속성 bit와 무관하게 기존 배치 의미를 유지한다. 따라서 원본의 특정 분기 주소를 직접 실행한 검증과 dispatcher가 style에 따라 분기를 선택한 검증을 구별할 수 있다.

준비·갱신 dispatcher와 `emit_sprite_resource`는 새 API를 사용한다. 실제 입력은 기존 MS5C 바이너리와 C++ 로더이며 이미지 변환이나 새 리소스 형식은 필요하지 않다. style 하위 byte 0..7만 큐에서 지원한다. 그 밖의 분기나 다중 블록은 여전히 거부한다.

## 재현

```sh
make all test
.venv/bin/python tools/verify_sprite_flips.py --cpp
.venv/bin/python tools/verify_sprite_pipeline.py --flips
.venv/bin/python tools/verify_sprite_pipeline.py --flips --disabled-pool
```

원본 두 리소스 ID 2152/2952의16개 분기, 좌표 wrap, 빈/1/380 슬롯 용량, 캐시 경계를 포함한1440조건에서 다음 슬롯과 순서 있는 비디오 쓰기 전체가 일치했다. 리소스 payload는 ROM4cce60/4cd3e8에 있고 bank400000 매핑에서 CPU2cce60/2cd3e8로 접근한다.

연속 검증은 네 가지 반전을 프레임/레코드마다 섞고 원본 생성기부터 준비·갱신까지 실행한다. 두 영역 활성과 한 영역 비활성 각각124제출·32단계에서 전체64KiB RAM과 비디오 쓰기를 비교한다. 실제 IRQ 타이밍, 픽셀 rasterizer, 다른 리소스 레이아웃, 전체 게임의 동등성을 증명하는 검증은 아니다.
