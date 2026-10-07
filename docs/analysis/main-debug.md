# 메인 진단 출력 ec4..ef2

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
이 문서의 CPU주소는 고정ROM 주소이며 같은 복호화 프로그램 오프셋이다.

## 정규 리소스

`tools/pack_main_debug.py`는d56..e3f의234바이트를 `extracted/runtime/main_debug.ms5d`로저장한다. MS5D v1헤더32바이트를포함한266바이트이며원본바이트를변환하지않는다. 기존C++ MS5D로더를사용한다.

- format: d56..def,154바이트. d58의NUL은`\p`제어피연산자이며def가최종종료다.
- 인자표: df0..e3f,20개의BE32 RAM주소. 전체포인터목록과원본위치는manifest에기록한다.
- e40부터의코드는포함하지않는다. 이전직접renderer검증fixture의d56..e49보다정확히10바이트짧다.
- 리소스SHA256: `b2d6bc8f2b4bacb5da6fe3cb32e448f3dd714c102ef0efe3abc2eb2c2ceb8c80`.
- manifest SHA256: `ff9038b0af9edab342bf4b25da046444ae3fd0b7e83e20b8262598564c9afee8`.

## 조건과 반환 경계

`step_main_debug`는ec4에서시작해ef2의대기직전에끝난다. RAM10f000.bit0이0이면오브젝트와리소스를사용하지않는다. bit0이1일때object+84.byte가0이어도출력을생략한다. byte접근뿐이므로이경계에서는홀수object주소도가능하다. 활성상태는cursor7066,formatd56,argumentsdf0,renderer3650으로3a70포맷터를실행한다.

성공시RAM·비디오포트와최종32비트D1을반환한다. D1상위16비트는보존되고하위word는포맷터종료시의style이다. 조건을통과하지않으면D1과RAM을유지하고포트는빈목록이다. 잘못된주소/리소스/포맷실패는입력및출력을보존한다. CLI는조건검사전에리소스파일을로드하므로비활성경로라도유효한MS5D파일이필요하다.

종료시style은RAM104cda.word와항상같다고가정하면안된다. 396e는저장style을D1에읽고마지막제어문자를해석한뒤NUL이면style을다시저장하지않고반환한다. 따라서`format_fixed_text`에선택적final_style출력을추가하여마지막파서결과를반환한다. 기존호출법은유지한다.

```sh
.venv/bin/python tools/pack_main_debug.py
build/step_main_debug INPUT_RAM DEBUG_MS5D OUTPUT_RAM OUTPUT_PORTS OBJECT_ADDRESS D1
```

JSON next_pc는ef2(3826)이고d1은최종unsigned32값이다. ef2대기/비디오읽기와다음입력은여기서실행하지않는다. 다른CPU scratch레지스터·SR/CCR·픽셀·물리장치시간축은계약에포함하지않는다.

## 검증

`.venv/bin/python tools/verify_main_debug.py`는원본ec4에서ef2직전까지790조건,시간순포트61,272개,오류11조건을확인했다. RAM64KiB전체와최종D1을비교했다. 모든256설정byte와오브젝트상태0/1/255,32비트D1상위값,홀수오브젝트주소및마지막상태byte경계를포함한다. 두출력생략경로에서는무관한유효MS5D창도사용하지않음을확인했다. 원본코드첫1MiB는불변이고font읽기는0이다.

보고서: `artifacts/main_debug/verification.json`.
SHA256: `bbe8deb1e9bd518172600538a3eb79a5295cff5edd8000fe9efb3bad0c5c38ee`.

## 줄 위치의 반환과 입력 연결

`format_fixed_text`는선택적final_line으로종료시D3.word도반환한다. `step_main_debug`의선택적line입출력은진단을생략하면유지되고활성출력시종료파서의값으로갱신된다. D3상위word는이계약에포함하지않는다. CLI에마지막선택인자LINE을주면JSON에도line을반환하며기존호출의JSON은유지한다.

```sh
build/step_main_debug INPUT_RAM DEBUG_MS5D OUTPUT_RAM OUTPUT_PORTS OBJECT_ADDRESS D1 LINE
```

단순`A\n`포맷에서는RAM104cd8.word가7000이어도반환line은7001이다. 실제진단문자열역시마지막줄바꿈뒤바로종료하므로저장된RAMline을읽어서다음입력의LINE으로쓰면일치하지않는다. 진단이끝나면반환D1.lowword와line을`poll_input_control`의style/initial_line에전달한다. 기다리는동안진단출력은다시실행하지않는다.

`.venv/bin/python tools/verify_debug_input_flow.py`는진단5회·IRQ서비스10회·메인poll14회총29경계와포트469개,잘못된LINE6조건을검증했다. 원본종료D3.word와저장RAMline의차이를직접확인하고CLI의D1/line출력을poll에전달했다. 진단전후A5/A6/A7보존,대기중재출력없음과실제c8c의신호생성을검사했다.

두번째프레임은원본CPU문맥을계속실행하지만,현재pollAPI는컨트롤러종료의모든scratch레지스터를출력하지않는다. 따라서다음debug의D1/D3입력은원본에서얻은외부검증조건이며완전히자립한C++연속CPU상태라고주장하지않는다. IRQ간문맥복구도호스트동작이다.

보고서: `artifacts/debug_input_flow/verification.json`.
SHA256: `f8554a23827ace276e07b389230258d3ec00a0ecaaf439d925b3d814d344fb12`.
