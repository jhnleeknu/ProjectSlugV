# 정적 오브젝트 재시작의 전체 레지스터 계약

## 근거와 범위

원본 `maincpu.decrypted.be.bin` SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 코드 주소는 fixed 첫 1 MiB에 있으며 CPU 주소와 ROM 파일 오프셋이 같다. `100000..10ffff`는 별도 작업 RAM, `300001`은 watchdog 포트다.

진입 `002a28`은 A0의 정적 오브젝트를 정리하고 입력 A1의 callback LONG을 저장한다. Callback 자체를 실행하지 않는다. 스테이지 후반 `0e905c`는 A0=`100bf4`, A1=`0e9150`으로 이 함수를 호출한다. 기존 `restart_static_object`의 선택적 D1/D3 출력만으로는 이 caller에 필요한 전체 레지스터를 전달할 수 없다.

새 계약은 D0-D7/A0-A6 15개 레지스터와 전체 64 KiB RAM, 순서 있는 포트 명령이다. A7/CCR/버스 타이밍은 공개 상태에 포함하지 않는다. 원본 비교에서는 정상 RTS와 A7 복귀를 별도로 검사한다. 주소 계산은 32비트이며 WORD 인덱스는 부호 확장한다. 지원 RAM 밖 접근은 오류로 반환한다.

## 호출 순서

`2a28`은 먼저 WORD(A0+10)가 0인지 검사하고 아니면 TRAP15에 도달한다. A6, A1, A0를 스택에 저장한 뒤 A6=A0으로 `299c`를 호출한다. 반환 후 A0를 복원하고 저장했던 callback을 LONG(A0)에 쓴 뒤 A6를 복원한다. **A1 레지스터 자체는 복원하지 않는다.** Callback은 저장만 하므로 원본은 even/fixed-ROM 여부를 검사하지 않는다.

`299c`는 A5=`108000`으로 놓고 입력 D0.byte를 `300001`에 쓴다. `2782`를 통해 팔레트 해제 `8ff4`, 좌표 연결 해제 `c3fa → 46ef4`를 순서대로 실행한다. 이어 LONG(A6)=`270e`를 쓴 후 WORD(A6+10)를 LIVE로 읽는다. 최초 검사 당시 0이었다고 이 후반 분기를 생략하면 안 된다.

## 팔레트 해제와 레지스터

`8ff4`는 D7=MOVEQ0, D7.byte=BYTE(A6+1d), SUBQ.W 1이다. Borrow가 나면 바로 BYTE(A6+1d)=0으로 끝낸다. 아니라면 A1=`104d92`로 설정하고 D7.low를 감소시키며 다음을 반복한다.

- D0=MOVEQ0 뒤 BYTE(A6+19+sign16(D7))를 D0.byte로 읽고 LSL.W 4를 적용한다.
- A2=A1+sign16(D0), D1.low=WORD(A2+8)이다. D1 상위 WORD는 보존한다.
- 참조 수가 0 또는 ffff면 쓰지 않는다. 그 외에는 RAM의 참조 수를 1 감소시키고 결과가 0일 때만 `8e4a`로 연결을 변경한다. D1에는 감소 전 값이 남는다.
- 각 반복 후 SUBQ.W 1을 수행한다. 최종 D7은 `0000ffff`이며 BYTE(A6+1d)=0으로 끝낸다.

개수는 원본에서 BYTE 그대로 읽는다. 일반 팔레트 할당기의 네 슬롯 제한을 이 해제 함수의 명령에 없는 검사로 적용하지 않는다. 높은 개수와 비정상 연결은 정상 게임 상태라는 뜻이 아니며 합성 입력으로 구분한다.

`8e4a`의 쓰기 순서는 다음과 같다. 모든 WORD 대입은 레지스터 상위 WORD를 보존하고 모든 RAM 읽기는 앞선 쓰기를 반영한다.

```text
D2.low = WORD(A2)
D3.low = WORD(A2+2)
WORD(A1+sign16(D3)) = D2.low
WORD(A1+sign16(D2)+2) = D3.low
D2.low = 1000
D3.low = WORD(A1+sign16(D2))
WORD(A2+2) = D2.low
WORD(A2) = D3.low
WORD(A1+sign16(D3)+2) = D0.low
WORD(A1+sign16(D2)) = D0.low
WORD(A2+a) = ffff
WORD(A2+c) = ffff
BYTE(A2+f) = 2
```

## 좌표 연결 해제

`c3fa`는 `46ef4`를 호출하며 레지스터를 저장하지 않는다. D0=MOVEQ0 뒤 D0.byte=BYTE(A6+6c)로 읽는다. Bit7이 설정되어 있으면 반환한다. 나머지는 D0.low<8이어야 하며 아니면 TRAP15다.

유효 index는 MULU.W `2c`로 D0 전체를 갱신하고 A0=`10d4e6`+sign16(D0)로 만든다. WORD(A0+26)=ffff, WORD(A0+2a)=2, BYTE(A6+6c)=ff를 이 순서대로 쓰고 `43e38`을 호출한다. 기존 전체 레지스터 좌표 API의 D0-D7/A0/A1/A2/A4 결과를 그대로 승계하며 A3/A5/A6는 보존한다. 부모/자기 참조와 stamp 분기도 기존 API의 LIVE 읽기 규칙을 따른다.

## 필드 초기화와 연결 오브젝트 경로

정리 후 WORD(A6+10)가 0이면 A0=A6으로 `271c`를 실행한다. `8eb6`, `43dcc → 43dda`, `c3dc → 4aa06/e90ca/46eec`와 후반 필드 쓰기는 기존 `reset_object_fields`의 RAM 결과와 대응한다. 이 경로의 최종 레지스터 변화는 D0=0, D1=ffffffff이고 A0는 해당 오브젝트 주소로 돌아온다. 나머지 레지스터는 보존한다.

팔레트나 좌표 쓰기가 WORD(A6+10)를 바꾸면 `29c0`의 연결 경로로 들어간다. `287e`는 A0=LONG(A6+8), D0.low=WORD(A6+10)으로 읽고 WORD(A0+10)와 unsigned 비교한다. D0가 작으면 바로 반환한다. 그렇지 않으면 현재 A6를 `271c`로 초기화한 후 다음을 순서대로 수행한다.

```text
A0 = LONG(A6+4)
A1 = LONG(A6+8)
LONG(A1+4) = A0
LONG(A0+8) = A1
LONG(A6+8) = LONG(104c9c)
LONG(104c9c) = A6
WORD(104ca0) += 1
A6 = A0
```

새 A6의 callback이 `270e`이고 WORD(A6+10)가 비영일 때만 `29c0`으로 반복한다. 0 종류의 이전 오브젝트까지 추가 초기화하지 않는다. 바깥 `2a28`의 최종 A0/A6 복원과 입력 callback 저장은 이 경로에서도 동일하다.

합성 확인 예: 오브젝트 `106000`의 초기 종류는 0이고 팔레트 슬롯은 0, 참조 수는 1로 둔다. 슬롯 0의 이전/다음 WORD를 `1000/127e`로 두면 `8e4a`의 첫 쓰기가 `104d92+127e=106010`에 `1000`을 써서 종류가 바뀐다. 이 입력은 실제 게임의 정상 연결 구조로 주장하지 않지만 원본의 후반 분기를 검사할 수 있다.

## 검증 상태

`restart_object_full` C++ API와동명CLI에서597조건의전체64KiB RAM·15레지스터·597개 ordered watchdog 출력이원본과일치했다. 원본은2a28부터RTS까지중간callee대체나contextreset없이실행했다. 각호출의정상복귀와A7+4,MMIO읽기0,코드불변도확인했다. Native최대실행은6,977명령이며관찰한도200,000명령이내다.

Corpus는count0..4/ref0·1·2·ffff/상위WORD·callback경계160개,중복슬롯18개,count5·8·32·128·255의20개,coordinate/parent/self/overlap/stamp360개,object주소경계/겹침16개,부호있는palette link3개,종류변경후단일분기4개와연속정리/이전static종료4개,실제CLI승계12호출이다. 원본3ef2가palette초기상태를준비하며나머지는통제된합성fixture다. Callbackodd/RAM/ffffffff는저장값검사이고실행가능성검사가아니다.

팔레트freehelper8e4a는1,251회,좌표43e38은288회,연결분기29c0은10회,연결정리29c8은8회실행됐다. 메인리뷰에서연속정리검증누락을보완하여한호출에29c0/29c8각2회와freecount/head결과를필수검사했다. 이전callback270e이더라도종류0이면추가초기화하지않는분기도포함한다.

4승계sequence의12호출중8호출은직전CLI출력RAM·레지스터를소비한다. Host는A0 object/A1 callback만다시설정한다. 오류136조건은입력및기존출력을보존했다. 후반palette link/coordinate parent/연결pointer오류와65,536회self-cycle한도도포함한다. 전체make Python175/C++112/경고0이다.

- Native SHA256 `ac50d120ef409636185808d039c4a1c0425d20f526f6f74fd83afb3aa86b670c`.
- Verification SHA256 `6a196fae937d7d558b8d885ec5c237a02236bc216683a0740e820dc4037483d6`.
- CLI SHA256 `93f1781648fe7fbe74b56bc7ee1ffae9428a83a80f431000e426715929f69731`.
- 명시원본15창/169행/미해독0의inventory SHA256 `d38ea9affe3c58d9a4634d1f2ecd9f892c9d5a814c5c2cc595660b4589a702a1`.

메인은core/CLI/unit/observer/verifier전체와현재ROM/binary/report·597저장RAM/ports를대조했다. 기존부분레지스터API는변경하지않았다. 전체스테이지callback,자연프레임,직접플레이화면은별도미완료범위다.

```text
make -j3 all test
.venv/bin/python tools/inventory_object_restart_full.py
.venv/bin/python tools/observe_object_restart_full.py
.venv/bin/python tools/verify_object_restart_full.py
.venv/bin/python tools/inventory_stage_event_contexts.py
build/restart_object_full D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS
```

API는실패시RAM/state/ports를그대로보존한다. CLI의계산검증오류도출력을쓰기전에반환한다. C++실행은원본ROM이나PNG/오디오preview를읽지않는다. 이번함수는RAM의관리상태만소비하므로추가런타임리소스가없다.
