# 스프라이트 제출 cd58 재구성

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 대상 cd58..ce02는 fixed 영역이므로 CPU 주소=ROM 오프셋이다. RAM은 CPU100000..10ffff, A5=108000이다. 상세 원본 명령 계약은 stage-cue-frame.md의 cd58절에 기록했다.

## API와 지원 범위

`execute_sprite_submit(ram,state,status,error)`는 `SpriteSubmitExecutionState`의13개 일반 register와 waiting을 받는다. waiting=false이면 cd58부터 시작하고 LONG RAM9152의 callback을 먼저 실행한다. 현재 지원하는 callback은 원본에서RTS인cd50뿐이다. 다른 callback은 clip될 좌표라도 오류다. A6는 사용하지 않으며 CLI에서 보존해 반환한다. 기존 메모리 결과 중심 `submit_sprite` API는 변경하지 않는다.

waiting=true이면 cda4의 비교부터 재개한다. 최초 실행이 캡처한 D4.low와 live WORD8d34가 같아져야 진행한다. 기다리는 동안 RAM 쓰기는 없고 캡처 register를 유지한다. Callback, clipping, producer cursor와 prepared cursor를 재조회하지 않는다. Caller는 waiting 결과의 전체 register를 다음 호출에 전달해야 한다. 이 API가 임의로 만든 waiting 상태의 과거 실행 이력을 인증하지는 않는다.

클리핑 두 분기와 full 반환에도 원본 register 변화가 남는다. Normal/deferred 모두 원본 순서대로 RAM을 읽고 쓴다. 특히 deferred count의 증가가 source offset 읽기보다 먼저다. 최종 MOVEM은 D0/D1/D7의세LONG을순서대로쓴다. WORD/BYTE 연산은상위bit를보존하고signedWORD주소연산은명시적unsignedwrap으로구현한다.

새 API는기존typedqueue의cursor0..510/record12배수검증을추가하지않는다. 원본이계산한주소가정렬된완전한64KiB RAM범위이면지원하며그밖접근은오류다. 에러시RAM/register/waiting/status모두보존한다. 이는원본잘못된주소실행의부분변경/하드웨어fault를재현한다는뜻이아니다. 전체CCR,임의callback,호출중인터럽트스케줄러는이번범위밖이다.

단위검증의D6=061a수동waiting case는합성direct-resume상태다. 보통cd58에서D6은01fe로마스킹되므로이case를자연경로도달증거로쓰지않는다. 실제원본대기검증은cd58에서cda4에도달한상태를그대로이어받아수행해야한다.

## 검증 진행

Core/header/unit/CLI와 원본 관측·비교 도구 전체를 메인이 읽고 원본 계약과 대조했다. 독립 읽기 전용 리뷰에서도 구현 문제를 발견하지 않았다. 원본 write 순서의 관측과 alias에 민감한 최종 RAM 대조를 구분한다. C++ API에는 write-event 출력이 없으므로 독립된 두 write trace의 완전 동일을 주장하지 않는다.

원본 Musashi616조건/736단계에서 전체64KiB RAM·14register·waiting/status가 실제 CLI와 일치했다. Accepted512, clipped88, full16, waiting120단계이며 조건분기6개 모두 양쪽 실제 목적지를 확인했다. 대기60사례는 원본cd58에서cda4까지 실행한 후 같은 CPU를 reset 없이 이어 쓴다. 중간 hold는 실제 CMP/BNE2명령을 실행하고 다시cda4에 도달한다. CLI도 직전 출력 RAM/register를120회 이어 쓴다.

외부 변경은 callback pointer, prepared/producer cursor 및 마지막 consumer target에 한정해 정확히 기록한다. Callback을 지원하지 않는 주소로 바꾼 상태에서도 재개는 callback을 다시 호출하지 않는다. 캡처D4/D6를 유지하는지와 원본 write 순서를 확인한다. 이는 자연 scheduler/IRQ timing 전체를 재현했다는 뜻이 아니다.

오류31조건에서 입력과 기존 CLI출력을 보존했다. 별도의 direct API6조건에서 늦은 queue 변경 뒤 오류에도 RAM/13register/waiting/status가 보존됨을 확인했다. 잘못된 원본 주소나 callback은 native에서 실행하지 않았다.

메인이736개 저장RAM·입력승계·외부변경·PC/A7·register 결과·branch 집계와 현재 source/oracle/CLI/tool provenance를 직접 대조했다. 독립 CLI 검증 재실행에서도 같은 보고서 hash를 확인했다. 전체make Python182/C++123/경고0, 로그 `artifacts/sprite_submit_execution_build_test.log`.

재현 명령:

```sh
make -j2 all test
.venv/bin/python tools/observe_sprite_submit_execution.py
.venv/bin/python tools/verify_sprite_submit_execution.py
```

CLI: `build/execute_sprite_submit D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 WAITING STATUS INPUT_RAM OUTPUT_RAM`. WAITING은0/1, STATUS는0accepted/1clipped/2full/3waiting이다. 숫자는십진또는0x표기를지원한다. 기존출력과입력의동일경로·inode를거부한다.

- Native SHA256: `e5ed5e1e0119a1684f40318f708e920553dc1a071a09b9fedb19b4506d651b39`
- Verification SHA256: `06ee2a59080d2c5d984a35d5bc2f06a7807ad44c8cff441d391f66e58800844e`
- CLI SHA256: `78eb3a1ffcc79634c963d076d8e94f8d6cdca51f115b73bd0b2ebc0ee559266d`

## 이후 e8a48 연결 설계

스테이지 cue frame에서 sprite 대기가 발생하면 그 앞의 오브젝트 할당·좌표설정·cue 선택을 다시 실행하지 않아야 한다. Frame 상태에도 sprite 대기 여부와13register를 보존하고, 재개 호출은 cd58의cda4부터 처리한 뒤 e8b58로 반환하는 경로만 이어야 한다. 바깥 frame의 transaction은 helper와 sprite의 중첩 transaction까지 포함해야 한다.

할당 경로의 index는 BYTE(A0+7)-1c 결과의하위BYTE가20미만인경우0..31이다. e8a0c+4*index에서두WORD를읽으므로 필요한 raw 조회 창은128byte다. 첫16byte만 명백한별도DATA이며 그뒤원본코드도주소계산상읽힐수있다. 후속packer는이128byte를source조회창으로명시하고32개논리데이터레코드라고단정하지않아야한다. 현재catalog42개cue prefix는각8byte로별도목록화돼있지만아직이frame용runtime리소스로패키징하지않았다.

Scene script의현재알려진opcode10 간접참조 e6e9e의LONG은0이었다. 따라서그참조의실제설정은기본e89ec stream으로귀결된다. 이관측을모든가능한stream이기본하나라는증명으로확대하지않는다. Caller가RAM stream을제공하는경로와다른호출원은별도지원·검증대상이다.
