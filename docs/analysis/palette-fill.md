# 특수 팔레트 채우기와 별도 주소 계산

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정ROM CPU/파일주소873a는특수채우기,8b64는설정이다.

72fa는RAM107dea word가nonzero이면873a로분기한다. bank1을선택한뒤A0=400000+signed16(counter), A1=107da2를설정한다.8752..8b52는동일 MOVEM.L d0-d7,-(a0) 256개다. 따라서32바이트패턴을총8192바이트,높은주소에서낮은주소로반복기록한다. counter에서2000을word단위로빼고결과0이면최종A0의첫word를0으로쓴다. 그후일반wrapper의8720으로분기해RAM107dec가선택하는표시bank로돌아간다. 일반준비pending107ded와staging105da2는변경하지않는다.

확인한설정8b64는counter를2000으로만든다. 이값으로실행하면bank1 전체8192바이트가32바이트패턴의256회반복이되며첫word만0이다. 원본32fixture(패턴16종×최종bank선택2종)에서전체RAM·논리bank1·bank선택순서가일치했다. 다른counter에서장치주소미러링까지지원한다고주장하지않는다.

## 중요한 소스 주소 차이

8b64는D0를16비트로마스크하고32배하지만, 최종LEA는 **D0.W signed인덱스**를쓴다. 소스주소는다음과같다.

```
base = ROM[200004] = 22bd12
source = base + signed16((input_id * 32) & ffff)
```

일반7196의source base+unsigned_ID*32와다르다. 설정입력은2048마다alias되고1024..2047의나머지는음수offset이다. 예를들어입력0897은일반palette0897이아니라base+12e0(일반0097위치)를읽는다. MS5P일반카탈로그ID를그대로연결하면잘못된색이될수있다.

설정은원본4718변환을pattern의word1..15에쓰고word0은보존한다. bank shadowRAM0010을0으로하고counter2000을설정한다. 입력0/1/15/1023/1024/2047/2048/0897/ffff의9조건에서전체RAM이독립주소모델과일치했다.

```
.venv/bin/python tools/analyze_palette_fill.py
```

현재결과는원본분석과검증도구다. C++의두뱅크전송API와이설정함수의리소스주소연결은후속작업이며기존일반전송API는특수모드를명시적으로거부한다. 실제호출자의입력범위, 장치타이밍과표시화면은미확인이다.
