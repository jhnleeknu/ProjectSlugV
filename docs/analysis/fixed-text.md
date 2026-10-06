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

## 문자열 길이 측정과 공통 제어 해석

38e8은같은386e해석기를사용하지만글꼴타일을그리지않고반환된nonzero byte수를word로센다. 따라서ASCII뿐아니라80..ff도한글자씩세며65536개면0으로wrap한다. 제어명령의인자0은문자열종료가아니지만반환된문자0(알수없는escape뒤0포함)은종료다.

`measure_fixed_text`와기존`trace_fixed_text`가제어해석을공유하도록정리했다. 측정결과는glyph_count/style/line/consumed_bytes이며오류시이전결과를보존한다. trace의font61/ASCII지원범위는그대로다. 비ASCII측정가능을비ASCII렌더링지원으로간주하지않는다.

CLI `measure_fixed_text INPUT_MS5D CPU_ADDRESS STYLE LINE`은MS5D데이터창의주소에서읽고glyph_count/style/line/end_cpu_address를JSON으로출력한다. 문자열주소는홀수도허용한다. 기존control_menu.ms5d의7문자열을실제로읽어검증했다.

```
make all test
.venv/bin/python tools/verify_text_measure.py
.venv/bin/python tools/verify_fixed_text.py
```

원본38e8과388조건의글자수·style·line·종료주소가일치했다. 메뉴7문자열,모든nonzero byte255종,위치명령120조건,개행경계4조건,escape종료및65536글자wrap을포함한다. 잘림/누락/원본trap에대응하는입력7개는명시적으로거부했다. 오류출력보존unit검사도통과했다. 이구현은메뉴크기계산에필요한문자측정이며메뉴초기화/표시전체구현은남아있다.

## 기본 1타일 문자 출력 3650

메뉴초기화는기본문자callback을3650으로설정한다. 공통3918/386e루프에서3650으로들어오는glyph는1바이트다. 원본SWAP/MOVE.W/LSL.B/LSL.W/MOVE.B를따르면타일word는`((style&0f00)<<4)|((style&000f)<<8)|glyph`이다. ASCII제한이없고각byte를한타일로쓴다. 이것은다중바이트Unicode해석을의미하지않는다. 원본문자제어코드가고르는font/page와glyph번호를그대로사용한다.

매글자마다3c0000에 `(cursor<<16)|tile`을long으로쓴뒤cursor word에20을더하고,같은포트에8200을word로쓴다. 후자의VRAM주소설정을생략하지않는다. C++ `VideoPortWrite`는address/value/size를갖는공통하드웨어쓰기표현이며 `trace_direct_fixed_text`가이순서를출력한다. 기존2타일font61 trace와측정API의지원범위는유지한다.

```
make all test
build/trace_direct_text INPUT_MS5D CPU_ADDRESS CURSOR STYLE OUTPUT_WRITES
.venv/bin/python tools/verify_direct_text.py
```

CLI의비교파일은각이벤트를size byte+BE32포트주소+BE32값의9바이트로기록한다. 이는비교출력이며새로운게임리소스포맷이아니다. 입력은기존MS5D원본문자열이다. API는성공시목록을교체하고제어명령오류/100000글자상한에서이전목록을보존한다.

원본3918/3650과291스트림의포트주소·쓰기폭·값·순서가일치했다. 실제메뉴7문자열×4style,255nonzero glyph×256style조합65,280개,주소word wrap과제어명령을포함한다. Unicorn callback이word값을부호확장해서보고하는경우실제쓰기폭16비트로마스크해버스값을비교한다. 전체기존검사와출력보존/상한unit검사가통과했다.

이결과는기본문자렌더링의원본포트명령검증이다. 메뉴항목배치/선택표시/가림callback 및최종팔레트·픽셀화면검증은아직남았다.
