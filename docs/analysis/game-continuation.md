# c58a 이후 제어 흐름

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 고정 ROM CPU 주소와 파일 오프셋이 같으며 RAM 표기는 CPU 절대 주소다. 메인이 원본 명령을 읽어 확인한 정적 분기 해석이다. 아직 C++ 실행 연결이나 자연 부팅 관측을 완료하지 않았다.

## 초기 분기

47570은 c584의 JSR에서 호출되고 c58a로 돌아온다. c58a의 MOVE.B는 RAM10fdae를 D0.low byte에 넣고 나머지24bit를 유지한다. 이후 byte값0 또는1은 BIOS c00444로 JMP한다. 이 주소는 게임 프로그램 파일의 오프셋이 아니며 BIOS의 동작을 임의의 RTS로 대체하면 안 된다.

값3은 c6da로 분기한다. 그 외 값은 ROM180.word를 검사한다. 제공된 canonical 이미지의 값은0이므로 c5be 경로로 이어진다. 이 관측은 다른 ROM/매핑의 값까지0이라고 가정하는 근거가 아니다. c5be는 ca7e와4fb1a를 호출하고 오브젝트 callback을 c5ce로 설정한 뒤 즉시 그 본문을 실행한다. ca7e는 A5=108000 조건에서 RAM100965.byte를0으로 만든다. ca76은 같은 byte를ff로 만든다. 이 byte의 게임상 이름은 아직 확정하지 않는다.

## 후속 경계

c5ce는 A6+62.byte를 검사한다.0이면c73e, 그 외에는ca76과28ae를 실행한다.28ae 입력은 A0=de024와 D0.low=0이며 그 뒤에+62를0으로 만들고 callback c5f4로 진행한다.28ae의 실행 효과를 아직 이 문서에서 확정하지 않는다.

c5f4는+62가0이면c724로, 그 외에는+76.word=150과 callback c608을 설정하고 같은 호출에서 카운터를 한 번 감소시킨다. c608에서 감소 후0이 아니면c724,0이면c610이다. 따라서 callback 전환 뒤 즉시 fallthrough하는 동작을 별도 프레임 지연으로 바꾸면 안 된다.

c610은 RAM10f02a.word=1, 난수초기화49a1a, c4cc, caf0,47570을 실행한다.이 호출 순서와47570의대기·재개를 `game-restart.md`의C++통합으로연결했다. 이어10f02a의bit0을 보존하고6을 더해4823a를 호출하고, 다시10f02a로3162를 호출한다. callback을c654로 바꾸고c652에서RTS한다.

c654는 고정 오브젝트100b30과 ROM477e4를2a28에 전달한다. callback c66a에서289e와314c의 carry를 사용한다. 원본289e는 대상callback!=270e이면carry1, 같으면carry0이고314c는RAM104cd4.byte==1일때만carry1이다. 따라서 대상이활성이고입력mode1이면c724로,둘중하나가아니면c686으로진행한다. 이판정의호출자C++연결은아직남아있다. 이 경로는c686에서ROM180을 다시 검사하며 nonzero이면 그 위치를clear하는 명령도 존재한다. 단순 RAM이나 정상 ROM 쓰기라고 추측하지 않으며 실제 하드웨어 매핑/진입조건 확인이 필요하다.

값3 경로 c6da는 ca76,28ae(A0=de376,D0.low=0)를 호출하고 callback c6f4를 설정한다. c6f4는c6ce 데이터 주소를3902에 전달하고10fdda를36ba에 전달한다.10fdda.byte가0이면c73e, 아니면c724다. c724/c73e는RAM100012.byte가2이면c74c로 간다. 그 외c724만A6+81.byte에 따라c49c를 호출할 수 있고 둘 다c988로 이어진다.

## 재생성 가능한 목록과 한계

`python3 tools/inventory_game_continuation.py`는94명령 후보,22직접호출,23분기/JMP를 기록한다. 결과 `artifacts/game_continuation/report.json` SHA256 `9cb1f79cf80ce9a25c68294e23b13d5e16efab49cc063a3a8faeee77d511b9de`. 텍스트 참조 목록은 문서가 늘어나면 바뀔 수 있다.

c6ce..c6da는c6f8 LEA가 참조하는12byte 구간으로 코드 디코딩에서 제외했다. c6da는 명시적 분기 대상이므로 거기서 다시 시작한다. c700은c6fc의6byte JSR 중간이므로 경계로 자르지 않았다. 메인의 임시 Capstone 직접 호출은c78e JSR의 마지막2byte가 없는 창에서 가짜 aaaaaaaa 피연산자를 출력했다. 실제6byte는4eb9000028ae이며 대상은28ae다. 기존 `disassemble_range`의 패딩과 실길이 검사로 확인했고 가짜 주소를 분석 결과에 사용하지 않는다.

4fb1a·28ae·c4cc·caf0의하위구현과c610통합은완료했다. 남은초기분기및c654후속구현에서는BIOS경계와callback반환/대기를명시하고이함수들을실제순서로연결해야한다. 호출을 무시한 채 PC만 옮기는 구현은 해당 경로 복원으로 인정하지 않는다. 전체 게임 목표는 계속 진행 중이다.


## c654와 다음 스테이지 콜백

c654는기존정적오브젝트재시작2a28로RAM100b30에callback477e4를설정한뒤현재A6의callback을c66a로바꾸고같은호출에서판정에들어간다. c610이설정한inputmode1과새callback477e4조건에서는c724로이어진다. 이는정적명령해석이며scheduler가자연스럽게실행한관측은아니다.

callback477e4는배경초기화1a5a4,stage/area조회474e2/47540,stage+area byte복사및추가reset들을실행한다. area조회포인터가0이면area를0으로바꿔다시조회한다. 478a8의indexedJMP는478ac..478c4에있는6개BRA명령을사용한다. 앞의검사는unsignedD0.word<24이지만D0값은byte에서읽고추가4배연산이없다. 유효selector를자동으로0..5로가정해서는안되며리소스의실제값과분기주소대응을확인해야한다.

재현도구 `tools/inventory_game_ready.py`는144명령후보/콜백직접호출21개와19개callee후보를기록했다. 보고서SHA256 `5d29ef19a566184c2f7ceb1b6b72fac55fb887cffb59453470fd7e0a889b6c77`. callback범위는479b0exclusive에서멈추며전체콜백이나모든스테이지가분석완료된것은아니다. 자동주소참조는의미확정과구분한다.
