# 상태를 갖는 메뉴 문자열 포맷터

프로그램 SHA256:`29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
명시한 코드 주소는 고정 ROM CPU 주소이며 복호화 파일 오프셋과 같다.

## 원본 구조

3a70은 A3=104cd6으로 설정하고3950 초기화 뒤396e를 carry가 설정될 때까지 호출한다. A0는 format, A1은 renderer(e84c8 또는3650), A2는 BE32 인자 포인터 배열이다. 각 인자는 문자열 또는 숫자 원시 byte를 가리킨다. C printf와는 다르다.

104cd6부터24바이트 RAM 상태:

| offset | 내용 |
| --- | --- |
| 0 | 현재 VRAM word cursor |
| 2 | 줄 시작 VRAM word |
| 4 | 글꼴/팔레트 style |
| 6 | format CPU pointer |
| 10 | renderer CPU pointer |
| 14 | 다음 인자 포인터 배열 CPU pointer |
| 18 | 현재 인자의 CPU pointer |
| 22 | 현재 삽입 항목의 출력 counter word |

초기화는+18의 기존값을 지우지 않는다. 포맷 문자열의 종료 byte는 읽지만, 그때 소비한 format pointer와 제어문자 변경은 상태에 저장하지 않는다. 일반 문자/%% 출력은 렌더러가 소비한 bytes까지 포함하여 format pointer를 저장한다.

## 폭과 삽입

383e는 십진 숫자 폭을 읽는다. 숫자가 없으면 word ffff, 숫자가 있으면 곱셈/덧셈의 하위16비트 결과를 사용한다. 폭0은 trap이다. 따라서65537은1로 순환한다. `%` 뒤의 첫 byte가0이면 숫자 zero padding을 활성화한다.

`%x`는37e2로 원시 byte의 nibble을 출력한다. 폭이 홀수면 첫 byte의 하위nibble, 짝수면 상위nibble부터 시작한다. 출력은 대문자 hex다. leading zero는 space로 바꾸되, zero padding이나 마지막 자리에서는0을 출력한다. 매 글리프마다 인자 시작부터 해당 자리까지 다시 조사하며 인자 포인터를 진행시키지 않는다.

`%s`는 인자에도386e 제어문자 파서를 적용한다. 제어문자/결합문자/@가 소비한 실제 pointer를 저장하고, 다음 byte가0이면 counter를 폭과 같게 만들어 다음 호출에서 삽입을 끝낸다. 폭에 도달해도 삽입을 끝낸다. 빈 문자열은 첫0을 glyph0으로 한 번 렌더링한 다음 다음 byte를 검사한다.

원본의 특이한 동작도 보존한다:

- 39b8의 SEQ.B D3가 줄 위치 하위byte를00 또는ff로 바꾼다. 3a24는 D3가 아닌 D2에 원래 줄 위치를 읽으므로 `%s` 파서가 변경된D3를 사용하고 이를 RAM에 저장한다. 줄 위치를 임의로 교정하지 않는다.
- 39e4는 counter word의 하위byte만 검사한다. 그래서 긴 삽입이256/512 등에 도달하면 다음 인자를 새로 읽는다. 한 문자열을 무제한으로 이어 읽는 동작으로 대체하지 않는다.
- `%x` 렌더러 lookahead A0는3650이다. 원본 첫byte48은 숫자/space glyph의 결합 처리를 유발하지 않는다. C++는 이 바이트를 명시적으로 사용하며 다른 코드 영역을 리소스에 요구하지 않는다.

## C++와 리소스 연결

`format_fixed_text`는 기존 MS5D 고정ROM 창 목록, 기존 글꼴 MS5D,64KiB 작업 RAM을 읽는다. 인자 pointer는 ROM이나 RAM 데이터를 가리킬 수 있다. 외부 스택에 있는 원본 포인터 배열은 주소와 raw byte 배열을 별도로 전달할 수 있다. 이는 새 리소스 포맷이 아니다. 현재 renderer는 e84c8의 지원되는 글꼴 경로만 구현한다.

`parse_fixed_text_glyph`와 `render_table_text_glyph`를 기존 문자열 코드에서 분리했다. 후자는 이미 파싱된 glyph0도 렌더링할 수 있어 포맷터의 빈 문자열 동작을 보존한다. 두 helper와 전체 포맷터는 오류 시 호출자 상태/출력을 보존한다. 전체 호출의 포트 쓰기는100000개, 실행 반복도100000회로 제한한다. 잘못된 접근, 겹치는 ROM창, 폭0과 미지원 변환은 명시적 오류다. 원본 trap/무한 실행을 정상 성공으로 처리하지 않는다.

## 검증

```
make all test
.venv/bin/python tools/verify_formatted_text.py
.venv/bin/python tools/verify_table_text.py
```

Unicorn에서 원본3a70 이하 명령을 변경 없이 실행하고289조건의 전체64KiB RAM 및 비디오 포트 쓰기 순서·폭·주소·값을 비교했다. 정상조건 모두 일치했다. 원본 포맷955e(`\c0%1x:%2x %s`),9781(`FOR %s `),59개 실제 스테이지 이름, %%/폭/zero padding, 홀짝hex폭1..8, 글꼴·팔레트·위치 제어, 빈문자열, 256/512 counter 경계와 폭 순환, RAM/ROM 인자를 포함한다. 진단 fixture는 원본 문자열을 안전한 고정ROM창60000으로 옮겼으며 실제 콜백 자체를 실행한 검사는 아니다.

C++ 단위검사는 상태변경·패딩뿐 아니라 외부 스택 인자, 데이터범위 초과, 잘못된 변환/폭, 미지원글꼴 및 오류 후 전체RAM/출력보존을 확인한다. 기존 glyph704스트림 회귀와 전체테스트도 통과했다.

진단CLI:

```
build/format_text INPUT_RAM OUTPUT_RAM MEMORY_MS5D FONT_MS5D FORMAT_CPU ARGUMENT_CPU CURSOR STYLE OUTPUT_PORTS
```

CLI는 하나의 MS5D 창과 RAM 인자 배열을 받는다. 라이브러리는 여러 창 및 별도 스택 배열을 지원한다. 출력 포트 파일은 기존 size byte + BE32 주소 + BE32 값의 진단 형식이다. 입력/출력 경로·inode 겹침을 거부한다.

## 남은 연결

9602/9802의 스테이지/구역 상태 변경, 이 포맷터가 남긴 RAM/레지스터와 일반행 다시그리기, 구분선 출력 및 전체a370 프레임 연결이 남았다. 주소0 이름 pointer 등 실제 콜백 경로는 필요한 ROM창을 확보하여 별도 검증해야 한다. 다른 renderer, CPU 전체 레지스터/flags, 원본의 스택 잔여값과 최종픽셀/실행 타이밍은 이번 동등성 주장에 포함하지 않는다.

## 직접 문자 렌더러3650

메인ec4의 진단 출력은e84c8이 아닌3650을 A1로 전달한다. `format_fixed_text`의 선택적 마지막 renderer 인자로3650/e84c8을 지정할 수 있다. 기본값은 기존e84c8이며 다른 주소는 지원 오류다. RAM104ce0.long에는 실제 선택 renderer 주소를 저장한다.

3650은D0의VRAM cursor와D1.style, D2.glyph로3c0000.long을 쓴다. style에byte단위4bit shift와word단위4bit shift를 차례로 적용하므로 출력하위word는 `((style & 0x0f00) << 4) | ((style & 0x000f) << 8) | glyph`다. 이후cursor에20을word로 더하고3c0000.word에8200을 쓴다. cursor는16비트로 순환한다.

이 경로는 글꼴 테이블, 다음문자, `@` 대체나두바이트glyph를 조회하지 않는다. API의font가 비어 있어도 가능하다. CLI는 기존자리를 유지하므로FONT_MS5D를 여전히 로드하지만3650렌더링에서는 사용하지 않는다. 포맷의%s/%x/%%와제어문자, RAM상태 및 오류롤백은 기존파서를 공유한다.

```sh
build/format_text --renderer 0x3650 INPUT_RAM OUTPUT_RAM MEMORY_MS5D FONT_MS5D FORMAT_CPU ARGUMENT_CPU CURSOR STYLE OUTPUT_PORTS
```

실제 진단format은CPUd56, 인자포인터20개는df0..e3f다. 문자열안에는NUL인제어문자피연산자가 있으므로 첫NUL까지를문자열전체로 간주하면 안 된다. 검증용원본창d56..e49에는 e40..e49의10바이트 코드도 포함되며 이를순수텍스트로분류하지 않는다. ec4조건과진단출력후레지스터전달의전체연결은후속작업이다.

3650 검증은 `.venv/bin/python tools/verify_formatted_direct.py`의487조건과포트10,426개, 오류13조건을통과했다. 합성format/인자는작업RAM108000..10bfff 등에두고원본첫1MiB의불변을확인했다. 원본d56/df0의진단출력4조건을포함한다. 253개literal byte와제어문자·폭·숫자·문자열·cursor경계에서전체RAM/포트가일치했고font영역읽기는0이었다. 보고서 `artifacts/formatted_direct/verification.json` SHA256: `172b71a08e5a0c40c557e18dd827ca13e54272c2229e1b8bc2e995bbd72e2b2e`.

기본e84c8 경로는기존 `verify_formatted_text.py`의289조건(실제스테이지이름59개포함)을재검증했다. 이기존검사는원본문자열을fixture창으로옮기는방식이며새3650검사의원본전체불변주장과구분한다.
