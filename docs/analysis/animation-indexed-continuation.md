# Animation opcode10 indexed draw continuation

분석 기준은 commit `27cadc4301113b7940628d3089dd5feabf0771c9`와 canonical BE program SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 주소는 fixed CPU 주소이며 같은 파일 오프셋이다. 원본을 수정하지 않고 `load_verified_program`과 `disassemble_range`로 `49fc6..4a27c`의 관련 bytes를 확인하고, 기존 `animation_execution.{h,cpp}` 및 indexed/draw 분석을 대조했다. 이 문서는 정적 명령 해석, 이후 독립 감사한 whole49fc6 opcode10 native 관측과 API 계획을 구분한다. C++ 구현 완료를 주장하지 않는다.

## 확정된 제어 흐름과 레지스터 폭

Dispatch는 `4a01e JMP`와 `4a032 BRA 4a22c`다. handler에 진입할 때 별도 return address를 push하지 않는다. A0는 animation state pointer, A1은 opcode10 다음 selector BYTE를 가리킨다.

| 원본 주소 / bytes | 실제 효과 |
| --- | --- |
| `4a22c 7000`, `4a22e 1019`, `4a230 d040` | D0 전체0, selector BYTE 읽기와 A1 증가, D0.low WORD 두 배 |
| `4a232 45f90004a76c`, `4a238 30320000` | A2=4a76c, table WORD→D0.low; field offset은 signed WORD |
| `4a23c 3219` | length WORD→D1.low, D1.high 보존, A1은 list base |
| `4a23e 48711000` | **field BYTE를 읽기 전에** `list_base + signed16(D1.low)`를 LONG push |
| `4a242 10360000`, `4a246 e748` | object field BYTE→D0.byte만 교체, D0.low를3bit 왼쪽 shift하여16bit 절단 |
| `4a248 b041`, `4a24a 64000024` | unsigned WORD 비교 `offset >= length`이면4a270으로 skip |
| `4a24e 0c3100040000`, `4a254 67000012` | selected BYTE가04이면4a268; 다른 값이면4a258 TRAP15 |
| `4a268 43f10001` | A1=`list_base + signed16(offset) + 1`, 즉 selected draw operand |
| `4a26c 6100fe9e` | BSR4a10c, return address는4a270 |
| `4a270 225f`, `4a272 6000fd8a` | PEA의 list end→A1 LONG 복원, 바로49ffe dispatch |

`index_word=(table_word & ff00) | field_byte`, `offset=(index_word<<3)&ffff`다. table WORD의 상위 BYTE를 버리고 field BYTE만8배하면 원본과 다르다. unsigned 비교 후 실제 selected address 계산은 signed WORD이므로 high-bit offset의 역방향 접근도 별도다. length도 unsigned 비교값과 signed 주소 displacement라는 두 역할을 갖는다. length가8의 배수라는 검사는 원본에 없다.

Skip에서는 selected opcode/operand나 draw object 필드를 읽지 않는다. D0/D1/A2는 위 계산 결과, D7은 dispatch가 만든10, D6는 incoming 값이다. 이후 명령이 이 값을 바꿀 수 있으므로 이를 전체 호출 최종 상태라고 일반화하지 않는다. selected opcode가04인 경우에만 draw를 호출한다. invalid selected opcode는 checked unsupported/error로 대응할 대상이며 native 성공 oracle에 넣지 않는다.

## Draw의 조기 반환과 정상 반환

기존4a10c helper는 opcode04와 같은 operand7BYTE를 읽고 D0/D5/D6를 MOVEQ0으로 초기화한다. sentinel packed LONG `007ff800`, 음수 timer BYTE(A0+4), object flash 조건(object+61 bit3 및 live A5-7ff1 bit0)은 각각 실제 도달 순서대로 조기 RTS한다. 이때 sprite saved frame/PVC zero-bank를 만들지 않지만 indexed BSR return4a270과 PEA list end는 이미 stack에 있다. 따라서 sentinel/flash도 **A1=list end 복원 후 dispatch**한다. sentinel은 object+20/timer/flash 접근을 요구하지 않고, timer skip은 뒤 flash 접근을 요구하지 않는다.

정상 sprite 완료는4a200..4a22a의 기존 draw epilogue를 거친다. live A5 기준 bank shadow WORD 복원 및 PVC2회, D0/D7의 MOVEM.W signed16→32 복원, A0/A1 LONG 복원 뒤 RTS4a270이다. 그 A1은 selected record의 operand7BYTE 다음 주소다. 이어4a270이 별도의 list end로 A1을 다시 교체한다.

**4a276을 실행하지 않는다.** indexed 명령 자체는 LONG(A0)의 저장 pointer를 갱신하지 않으며, D6=A1을 강제하지 않는다. D6는 실제 draw/producer의 postdraw 값을 유지하다가 다음 명령의 효과를 받는다. 기존 callback_return을 재사용하면 잘못된 pointer write와 D6 변경이 생긴다. 기존 draw_return은 D6를 변경하지 않으므로 그 부분은 재사용 후보지만 indexed 외부 복귀를 추가해야 한다.

## 대기 stack: 원본 실행으로 확인한 제한된 범위

S를 whole49fc6 진입 시 A7로 정의한다. `(S)`에는 caller return sentinel이 있다. 실제 wait는 cd58의 polling loop cda4다. 아래 source 명령에서 도출한 frame은 이제 whole10 원본 실행의 normal/deferred × index0/4 네 체인에서 begin/hold의 실제 stack bytes로 확인했다.

| S 상대 주소 | 저장 값 / 생성 명령 |
| --- | --- |
| `S-4` LONG | list end;4a23e PEA |
| `S-8` LONG | indexed draw return4a270;4a26c BSR |
| `S-12` LONG | draw saved A1(selected record+8);4a1dc MOVEM.L |
| `S-16` LONG | draw saved A0;같은 MOVEM.L |
| `S-18` WORD | saved bank shadow;4a1e0 |
| `S-22` LONG | sprite return4a200;4a1fa JSR |

직접04 draw의 기존 pending frame보다4BYTE 더 깊다. 고정 observer는 wait에서 A7=S-22와 위 전체 frame을 캡처했고, ready에서 return4a200→4a22a→4a270→49ffe 순서를 기록했다. 독립 재실행에서도 일치했다. isolated oracle stack은 게임64KiB RAM 밖에 두며, physical RAM mirror/IRQ와 전체CCR 동등성을 의미하지 않는다. SR은 A7 설정 전에 쓰고 hook에서 읽지 않는 기존 규칙을 유지한다.

`draw saved A1`과 `list end`는 서로 다르다. 선택한 항목이 목록 마지막일 때 우연히 같을 수 있어, 중간 항목을 선택하는 native fixture가 필수다. 대기 중 list length/selector/field/selected operands를 바꿔도 현재 list end와 현재 draw prefix를 다시 계산하지 않는다. 완료 후 그 저장 list end의 다음 명령은 live RAM에서 읽는다. 다음 indexed/draw 명령은 변경된 object를 합법적으로 다시 읽을 수 있다.

## 고정 native 자료의 독립 감사

`tools/observe_animation_indexed_execution.py`와 `artifacts/animation_indexed_execution_native/observation.json`을 read-only 검토했다. 보고서 SHA256은 `db3247ceba5327719b84882b7d1abe006f0e30c87d28642ed7c2f9a9f75a6508`다. 전체 자료는846cases/854phases/3564ordered PVC, same-CPU wait4chains이며 input6개와 phase파일3416개의 현재 SHA를 모두 확인했다. source.json의255개 instruction row 및 fixed selector raw512BYTE도 canonical ROM bytes와 일치한다. 프로그램/trace에 stub나 ROM patch를 넣지 않고, 실제 original instruction으로 실행하며 RAM write replay와 allowed instruction/write/stack guards를 검사한다.

독립 재실행은90cases/98phases/496PVC를 메모리에서 수행했다. 모든 special family와 대표 BYTE index/timer를 포함하므로 length0/7/fff8/fff0, retained-high-BYTE selector91/92/96/97/a7/ac, 네 wait chain의 전체 begin/hold/ready가 포함된다. 각 phase의 전체64KiB RAM,15registers,carry,PVC bytes,read/write/PC/boundary/stack trace가 저장 자료와 정확히 일치했다. 파일이나 native report를 다시 쓰지 않았다.

네 chain의 wait/hold8snapshots 모두 A7=S-22, top return4a200, indexed return4a270과 saved frame이 일치한다. index0 두 chain의 saved_a1=10580c/list_end=10582c로 서로 다른 값을 실제 확인했다. index4 두 chain은 두 값 모두10582c다. hold는 PC cda4/cda8/cda4만 실행하며 RAM/PVC를 쓰지 않고 capture를 유지한다. ready는 poison된 selector/length/selected opcode/object 전처리를 다시 실행하지 않고 저장 list end에서 dispatch했다. 별도 trace 확인에서 네 ready 모두4a276이 없고 LONG(A0)의 pointer가 변하지 않으며, draw RTS 시 D6=2가 첫49ffe에서도2로 유지된다.

이 관측은 합성 liveRAM5record list와 실제 fixed selector raw table/defaultcd50의 제한된 fixture다. unsigned negative-length 중 index5/ff는 정상04 record 밖을 선택하므로 네 조합을 명시적으로 제외했다. selected opcode!=04 TRAP 성공, 모든 selector/length 결합, 각 draw branch 양쪽, 자연 게임 script 도달성, IRQ/physical mirror/전체CCR 또는 C++ 동등성은 주장하지 않는다. 감사에서 구체적인 자료 불일치나 oracle 합성 문제는 발견하지 못했다.

## 제안 상태와 API 선택

제안은 기존 canonical `AnimationExecutionState`에 `uint32_t saved_list_end`(constructor0)를 추가하고 phase3을 indexed sprite wait로 예약하는 것이다. saved_a0/saved_a1/saved_bank는 계속 **내부 draw frame**만 나타낸다. phase3에서 sprite.waiting=true, callback metadata는 모두0이다. phase0/1/2에서 saved_list_end=0을 요구한다. phase3에서는 list end0 자체를 metadata 불일치로 거절하지 않는다. 주소의 실제 접근 가능성은 sprite 완료 후 다음 fetch가 도달할 때 검사한다.

완료/조기 skip에는 local list-end 값을 보관하여4a270을 실행한다. sprite가 기다리면 local 값을 saved_list_end에 저장하고 phase3으로 반환한다. phase3 재개는 fresh prefix/selector/table/list/object preprocessing을 건너뛰고 execute_sprite_submit에 현재 canonical register snapshot을 넘긴다. 계속 기다리면 metadata와 carry를 보존하고, 완료하면 draw_return→A1=saved_list_end→saved_list_end0→직접 dispatch 순서로 진행한다. draw_return이 phase/saved fields를 지우므로 list end는 호출 전에 local로 보존해야 한다. 성공한 wait는 실제 prefix RAM/PVC 효과를 commit하고, 이후 실패는 기존 전체 invocation transaction으로 RAM/state/carry/ports/external_reads를 보존한다.

메인의 이번 분석 단위 결정은 **새 opcode별 CLI를 만들지 않고 기존 state/API/CLI를 확장**하는 것이다. 세 step_animation_execution overload 모두10과 phase3을 지원하도록 계획한다. indexed sprite 자체에는 external input이 필요하지 않으므로 구 overload에서도 이를 처리할 수 있다. 기존1f/phase2의 external-input overload 제한은 그대로다. 별도 API/CLI라면 기존 숫자 schema를 유지할 수 있지만 entrypoint가 늘어난다. 메인은 프로젝트 검증 CLI schema의 명시적 진화를 선택했다. 아직 구현된 동작이라는 뜻은 아니다.

기존 CLI는20→21numeric으로, SPRITE_WAITING 다음에 SAVED_LIST_END를 추가한다. INPUT/OUTPUT/PORTS는 argv22/23/24, resources25+이며 JSON21→22keys다. full sound CLI는25→26numeric으로, **공유 old21 뒤에** CALLBACK_SAVED_A0/CALLBACK_SOUND_PHASE/CALLBACK_SAVED_LOW/CALLBACK_WAITING/EXTERNAL을 둔다. INPUT/OUTPUT/PORTS는 argv27/28/29, resources30+이며 JSON26→27keys다. JSON의 추가 key는 saved_list_end다. 따라서 sound CLI에서 SAVED_LIST_END는 callback fields보다 앞이며, 기존25numeric 끝에 붙이는 형태가 아니다.

carry는 phase1/2/3 모두null, sprite.waiting은1/3만true, callback_waiting은2만true다. phase0 성공 시 모든 saved metadata0이다. 세 기존 verifier의 shared FIELDS/initial/parse 및 callback parser와 provenance를 새 schema로 함께 갱신하고 전체 기존회귀를 다시 실행해야 한다. 구 CLI 숫자 인자는 호환을 주장하지 않으며 문서에 변경을 명시한다. A5는 실제 sprite entry/resume에서만108000을 요구하고, sentinel/timer/flash/offset skip에 무조건 canonical A5를 요구하지 않는다. A6도 phase3 hold에서 prefix object span을 새로 검증하지 않는다.

## 재사용 가능한 부분과 남은 증거

현재 read_data는 MS5D lookup, read_script는 MS5A/fresh RAM script, draw는 full register/PVC sprite 호출, draw_return은 내부 epilogue를 제공한다. wide control resource `[4276c,5276c)`는4a76c selector table을 포함한다. 새 리소스 형식이나 임의 composition binding은 필요하지 않다. 기존 RAM-only step_animation_with_data의768조건은 선택/RAM/carry 근거지만 full15R/PVC/pending 증거를 대신하지 않는다.

구현 전/검증 시 확인할 항목은 다음과 같다.

- 아래 native 관측으로 확인한 stack과 같은 CPU hold/release를 C++ phase3 및 이전 실제 C++ 출력의 연속 재개와 비교한다.
- offset skip, selected sentinel, timer/flash skip, accepted/clipped/full/deferred/wait 및 list 다음 명령의 실제 register·RAM·PVC를 비교한다. draw status 자체를 새 animation 반환값으로 발명하지 않는다.
- 중간 record 선택, signed length/offset 경계, table high BYTE 유지, unsigned 비교, odd/unmapped 실제 도달 접근을 분리한다. 생략된 list 전체를 불필요하게 fetch하지 않는다.
- PEA 이전 table/length 읽기와 PEA 이후 live field 읽기 순서를 지키며, pending list end를 poison된 object/script에서 재계산하지 않는다.
- 현재 draw 종료 직후 다음 fetch110000 등의 late failure에서 public RAM/state/carry/ports가 보존되는지 확인한다. native 성공 사례로 합성 invalid metadata를 포장하지 않는다.

나머지 animation opcode, arbitrary callback, banked script, 자연 gameplay/IRQ 및 전체 GOAL 완료는 이 제안의 검증 범위 밖이며 이후 작업으로 남는다.
