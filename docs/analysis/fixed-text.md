# 고정 타일 문자 경로

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.

0xcb64는 기존에 확인한 palette source ID0x897을 slot0에 등록하고, A0=0xcb80로 0xe89da에 점프한다. 후자는 A1=0xe84c8로 설정한 뒤 공통 문자 루프0x3918을 사용한다. 이 스트림은 경고문이며 [0xcb80,0xccd5)의341바이트다. style/palette/location 명령의 operand에0이 포함되므로 단순 NUL 검색으로 길이를 구하면 잘못된다. 원본 실행 종료 A0로 끝을 확인했다.

## 제어 바이트

0x386e는 byte를 읽는다. 0x5c 뒤에서 아래 명령을 처리하고 다시 byte를 읽는다. 알 수 없는 명령은 뒤의 byte를 문자로 반환한다. 반환 byte0은 문자열 종료다.

| 명령 | 원본 효과 |
|---|---|
| c + byte | D1의 하위byte를 글꼴 값으로 설정 |
| p + byte | D1 상위byte를 operand 하위4bit로 설정 |
| l + x,y | D3=0으로 시작해 x<<5, y를 ADD.B로 더하고0x7000을 ADD.W; D0=D3 |
| n | D3 word+1 후 D0=D3 |
| r | D0=D3 |

l의 ADD.B는 byte carry를 상위byte로 전달하지 않는다. l/n 이후 D3>=0x7500이면 trap15다. r은 검사하지 않는다.

## font0x61 경로

0xe84c8의 글꼴 분기 중0xe8576..0xe85a6을 복원했다. ASCII byte g에 대해 상단 타일 값은 `(palette<<12)|0xa00|(((g&0xf0)*2)&0xff)|(g&0xf)`다. CPU 포트0x3c0000에 `(cursor<<16)|tile` long을 쓰고0x10010을 더해 두 번째 long을 쓴다. 따라서 다음 행에는 tile+0x10이 간다. cursor는 다음 문자를 위해 word 단위0x20 증가한다.

pinned MAME neogeo_spr.cpp draw_fixed_layer는 VRAM0x7000+row+column×0x20을 읽어 하위12bit를 타일ID, 상위4bit를 팔레트로 사용한다. 이 경고문은 팔레트slot0과 50개 서로 다른 타일ID를 참조한다. fixed 소스 선택과 실제 화면 RGB 재현은 아직 별도 검증이 필요하다.

C++ `trace_fixed_text`는 이 ASCII/font61 경로를 구현한다. 다른 글꼴과 비ASCII는 명시적 실패이며, 원본 trap도 호스트 오류로 보고한다. 오류 시 기존 출력은 보존한다. 이는 원본 텍스트 엔진 전체의 구현이 아니다.

## 검증

```
make build/trace_fixed_text
.venv/bin/python tools/verify_fixed_text.py
```

원본0xcb64 실행에서 포트0x3c0000 쓰기를 기록했다. C++가 동일 추출 스트림으로 생성한560개 address/value 순서가 전체 일치한다. 원본0xe89da와 ASCII1..127을 각각 포함한127개 합성 스트림도 비교했다. 팔레트15, 위치 명령, 개행, 복귀, escape 처리를 함께 지나간다.

원본 스트림 SHA256 `c63119be00c1f26c13bcfc7c1c1def3eadcee76f62f86e0810d1a4496e2f18c4`.
경고문 쓰기 순서 SHA256 `5b7226162bf069a169c70096001c3dca4c3fffa621752366e2862afa373aa9a1`.

추출 스트림과 trace는 artifacts/fixed_text에 보관한다. 이 trace 파일은 분석·비교용이며 최종 게임이 스크린샷이나 기록된 명령을 재생하는 구조로 대체하지 않는다. 엔진은 복원한 제어 해석을 실행하며, 후속 단계에서 공통 리소스·fixed 타일·팔레트·렌더러를 연결한다.
