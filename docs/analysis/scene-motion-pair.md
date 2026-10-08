# 두 좌표의 경로 검사와 구간 선택

## 근거

Canonical program SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 코드CPU주소와ROMoffset은fixed첫1MiB에서같다. RAM100000..10ffff의d3xx는별도RAMoffset이다. Frame좌표갱신19b96은19832를호출해현재/제안좌표의시간과구간을결정한다. 19832가구간을넘을때192c4를사용한다.

## 192c4의 좌표 변환

입력A1은현재record를직접가리킨다. RAMd3b4로대체하지않는다. D0/D1은첫좌표,D2/D3은둘째좌표다. D4.low=record+2 type으로36way dispatch한다. Type14/40/64/80은평탄한축분기로좌표변환을생략한다.

첫22type은X기준차이를D0/D2에계산하고각각동일shift를적용한뒤Y를변환한다. Index%11이0..4이면D1-=D0,D3-=D2다. Index%11이6..10이면원본은**D1+=D0,D3+=D0**이다. D3에D2를사용하지않는다. Index5는변환없음이다. Shift는0/10=LSL1,1/9=없음,2/8=ASR1,3/7=ASR2,4/6=ASR3이다.

후반14type은Y기준차이를D1/D3에계산하고X를변환한다. (index-22)%7의0..2는D0-=D1,D2-=D3,4..6은D0+=D1,D2+=D3,3은변환없음이다. Shift는0/6=없음,1/5=ASR1,2/4=ASR2다. 모든LONG연산은32bitwrap이고ASR는부호비트를명시적으로채운다.

두번째Y좌표에도D0를더하는명령주소는1941a/19432/1944a/1945e/19476/19502/1951a/19532/19546/1955e다. 열개모두raw `d680`(`ADD.L D0,D3`)임을원본과대조했다. 이를수학적으로대칭적인공식으로교정하지않는다.

## 192c4의 범위와 carry

D4=D5=0으로놓고D4.low에첫22type은baseY(d3ba),후반14type은baseX(d3b8)를읽는다. D5.low=record+4를읽고ADD.WD4,D5한다. signed16 D4.low>D5.low이면전체LONG을교환한다. D4.low-=1,D5.low+=1은WORDwrap이며포화시키지않는다.

SWAPD4후두검사좌표가signed32로D4보다작은지를D6.byte/D7.byte에ff/0으로쓴다. EXT.W는lowBYTE를lowWORD로부호확장하고상위WORD를보존한다. 이어SWAPD5후두좌표가D5보다큰지를각lowBYTE에다시쓴다. 앞서EXT.W로만든bits8..15는그대로다. AND.WD6,D7후D7.low=0이면carry1,아니면carry0이다. 이과정은D6/D7상위WORD를보존한다.

## 19832의 진행

A1=RAMd3b4가null이면D6=D7=0,carry0으로반환한다. 비영이면D0/D1=d3bc/d3c0을18efa로시간조회하고D6에저장한다. D0/D1=d3c4/d3c8의제안좌표도같은현재구간에서시간조회하여D7로얻는다.

반복마다D5=D7,SWAPD5하고N(D7-D6)만으로후진/전진을고른다. signed비교N xor V로바꾸지않는다. 전진은N16(D5.low-nextStart)이1이면현재구간을게시하고끝낸다. 아니면다음type음수여부를검사한다. 마지막구간이면D7=(nextStart<<16)-1로제한하고끝낸다.

전진가능하면196ac로구간과base를앞으로옮긴다. 현재/제안좌표를D0-D3에다시읽고D6/D7을스택에보존한뒤192c4를호출한다. D6/D7을복원하되carry는보존한다. Carry1이면반복하며**시간을다시투영하지않는다**. Carry0이면196de로되돌린뒤현재end-1에제한한다.

후진은N16(D5.low-start)이0이면그대로끝낸다. Start0이면D7=start<<16으로제한한다. 그외196de로뒤로옮기고동일한192c4검사를한다. Carry1이면반복,carry0이면196ac로되돌린후현재start<<16에제한한다.

196ac는구간변경을RAMd3b4에즉시게시하지않는다. 196de는base를되돌린뒤즉시게시한다. 19832의비영cursor 정상경로는A1을RAMd3b4에쓴다. Null경로는이쓰기를생략한다. 두경로모두carry0으로반환한다. 좌표변환의D0-D5결과는버리지않으며D6/D7만스택값으로복원한다.

## 검증 상태

C++ API·CLI·unit과 독립 원본 비교를 통과했다. 총 4,232조건은 canonical 2,376, null 10, 합성 주소 정규화 1,846으로 구분한다. Canonical 37개 리소스의 모든 108개 record와 합성 36종 변환을 검사한다. 192c4는 null A1을 지원하지 않고 19832만 명시적인 null 경로가 있다. 이 함수만으로 19b96/전체 1a73c/자연 frame/직접 플레이 화면 완료를 주장하지 않는다.

전진/후진의 검사 통과와 거절, 구간 되돌림과 마지막/처음 제한, 여러 구간 이동을 관찰했다. N-only 비교에서 V=1인 관찰은 LONG 117회, 전진 WORD 4회, 후진 WORD 4회이며 실제 다음 PC와 비교한다. 원본의 비대칭 ADD 열 주소도 서로 다른 D0/D2로 검증했다. 8개의 실제 CLI 연속 호출에서 24회 중 16회가 직전 출력을 소비하며 현재/제안 XY 변경은 명시적인 host 입력이다.

전체 64 KiB RAM·12레지스터는 Musashi/Unicorn/C++가 일치한다. 반환 C는 Musashi와 C++가 일치하고, Unicorn의 반환 후 SR.C 불일치 1,326개는 진단값으로 남긴다. 오류 107조건은 입력/기존 출력을 보존한다. 원본 명령·callee 중간 상태 보정은 없다. 최종 report hash는 리뷰0174에 기록한다.

## CPU 플래그의 근거와 관찰 제약

반환 carry의 명령 의미는 [M68000 Family Programmer’s Reference Manual](https://www.nxp.com/docs/en/reference-manual/M68000PRM.pdf)의 AND/MOVE/MOVEQ 정의를 따른다. 특히 198a8의 `MOVE.L A1,53b4(A5)`는 메모리 목적지의 MOVE이며 MOVEA가 아니다. 정상 반환에서 C를 지운다. 192c4는 AND.W 뒤 결과가 0인 경로만 ORI로 C를 세운다.

Unicorn 2.1.4에서 외부 SR 조회와 실제 BCS가 다르며 실행 중 SR-read hook이 이후 분기를 바꾸는 사례를 발견했다. 메인의 별도 36조건 probe에서 no-hook/PC-only는 일치하고 SR-read만 차이를 보였다. 반환 C를 보정하거나 원본에 명령을 끼워 넣지 않는다. 별도 Musashi 실행기로 실제 반환 SR을 검사하고, Unicorn secondary에서는 실행 중 SR 읽기를 제거해 전체 RAM·12레지스터를 대조한다. 합성 probe는 원본 ROM을 바꾸지 않고 RAM에서 별도 명령을 실행한다.

## 재생성 명령

```sh
make
.venv/bin/python tools/inventory_scene_motion_pair.py
.venv/bin/python tools/build_musashi_oracle.py
.venv/bin/python tools/musashi_oracle.py
.venv/bin/python tools/probe_unicorn_m68k_flags.py
.venv/bin/python tools/probe_unicorn_pair_return.py
.venv/bin/python tools/observe_scene_motion_pair.py --unicorn
.venv/bin/python tools/observe_scene_motion_pair.py
.venv/bin/python tools/verify_scene_motion_pair.py
```

Musashi 빌더는 고정 revision/archive hash의 공식 소스를 받아 ignored `artifacts/dependencies`에서 빌드한다. C bridge는 도구용 외부 실행기 인터페이스이며 게임 엔진에는 연결하지 않는다. 원본 게임 실행의 instruction budget은 200,000이고, C++의 방어적 구간 반복 한도는 1,048,576이다. 정확한 불변 리소스 크기 제한 아래에서는 단조 cursor 이동이 끝/처음/창 밖에 먼저 닿으므로 이 C++ 반복 한도를 직접 소진하는 조건은 현재 공개 입력으로 만들 수 없다. 한도 검증을 했다고 주장하지 않으며 oversized resource 거절은 별도로 검사한다.
