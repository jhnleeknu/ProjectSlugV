# 제어 메뉴의 원본 데이터와 C++ 해석

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. CPU/파일 주소는 고정ROM에서동일하다.

92da는A0=93e0,D0=4,D1=8로설정하고92e6에서a29c를호출한다. a29c는메뉴상태를초기화하고a0a0으로진입한다. a0a0은16바이트크기의RAM항목을아래방향으로할당하고문자열길이·항목수를읽어크기를설정한다. 완전한할당·표시실행기는아직복원하지않았다.

## 데이터 구조

93e0 헤더는16바이트다: +0 BE32제목주소, +4 최소너비byte, +5 최소높이byte, +6 BE32callback주소, +10 BE32callback주소, +14 BE16flags. +6 callback은a430..a440에서, +10 callback은a3b8..a3c6에서사용한다. 두callback의공식명칭은알수없어필드명을offset으로유지한다.

헤더뒤항목은10바이트씩이어진다. +0 BE32문자열주소, +4 BE32처리함수주소, +8 BE16인자다. 문자열주소ffffffff가4바이트종료표시다. 0과fffffffe는종료표시가아니며초기크기계산에서문자열측정을건너뛴다. 9b26은object+8선택byte에10을곱해항목을찾고9b3e는해당callback으로점프하면서인자를D1하위word에넣는다.

확인한93e0에는6항목이있고9430직전에종료한다. 제목과항목문자열은937e..93df에있다. 원본38e8실행으로7문자열의소비끝주소가추출범위내임을확인했다. 문자byte는386e제어명령과하드웨어문자코드를포함하므로임의Unicode변환을하지않았다.

## 게임용 리소스와 검증

`pack_control_menu.py`는937e..942f를기존MS5D v1으로보존한다. `extracted/runtime/control_menu.ms5d`는210바이트이며 manifest의stable ID는`menu:000093e0`이다. 기존데이터창형식을재사용하며PNG나화면캡처에의존하지않는다.

C++ `decode_menu_descriptor`는MS5D창과주소를받아구조체를만든다. 끝잘림·범위·정렬을검사하고오류시출력구조체를보존한다. API는byte항목수에맞춰255항목까지허용하며원본의과다항목count wrap을지원한다고주장하지않는다. 문자열/callback주소는다른리소스에도있을수있으므로이창안으로억지제한하지않는다. 실제callback코드를C++함수포인터로실행하지않는다.

```
.venv/bin/python tools/pack_control_menu.py
make all test
.venv/bin/python tools/verify_control_menu.py
```

C++출력전체필드가원본과일치했다. 원본9b26의6선택주소,9b3e의24호출(각항목event0/3/7/ffff),7문자열범위를확인했다. callback진입점에서멈췄으므로callback내용·메뉴화면·자연도달성검증과구분한다. 경계·종료표시·255/256개·출력보존검사와전체기존검사가통과했다.

다음연결대상은a0a0의메뉴초기화,386e문자열측정, a370메뉴프레임과항목callback이다. 이한메뉴추출을전체메뉴카탈로그로간주하지않는다.

## a29c 초기화의 C++ 연결

`initialize_menu`는a29c의메뉴스택reset과첫할당을구현한다. 이진입점은head7f0e를107f0e로초기화하므로a0a0의중첩메뉴표시경로를거치지않고107efe에첫슬롯을만든다. 일반a0a0 push나중첩메뉴지원과구분한다.

MS5D descriptor의제목과항목문자열을`measure_fixed_text`로읽는다. 제목0은생략하고항목0/fffffffe도측정을생략한다. style은입력Y word로시작하고line은명시적인initial_line으로받으며문자열간에이어진다. 최대글자수는16비트unsigned 비교다. flags&0e가0이면padding4,아니면2를더한결과의하위byte와최소너비중큰값을쓴다. 높이는(항목수+2)의하위byte와최소높이중큰값이다. 호스트의일반정수크기로계산해wrap을없애지않는다.

새슬롯+0에는원본descriptor주소를보존한다. +4를0으로쓰지만+5는기존값을유지한다. +6은항목수,+7/+8은0,+9/+a는X/Y하위byte,+b/+c는폭/높이,+d는3,+e는ff,+f는0이다. 전역7f16은기본문자callback3650,7f1a는0,7f1b는1이다. current pointer7f12는원본의push/pop효과대로보존된다.

CLI:

```
build/init_menu INPUT_RAM INPUT_MS5D OUTPUT_RAM ADDRESS X Y LINE
.venv/bin/python tools/verify_menu_init.py
```

실제93e0리소스16조건과합성경계362조건,총378조건의전체RAM이원본a29c와일치했다. 254/255항목에서높이byte wrap,255주변문자열폭,65535글자word wrap,문자열간line전달을포함한다. 잘못된리소스/측정trap/짧은RAM은상태변경없이거부한다. 전체기존검사통과. 이단계는메뉴초기화이며프레임애니메이션·중첩메뉴·실제화면은후속작업이다.
