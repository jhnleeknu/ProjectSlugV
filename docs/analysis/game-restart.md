# c610 restart 호출의 사운드 대기와 재개

프로그램 `extracted/program/maincpu.decrypted.be.bin` SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. ROM CPU 주소는 고정 매핑의 파일 오프셋과 같다. RAM offset은 CPU 주소에서100000을 뺀 값이며 A6는 절대 CPU RAM 주소다. 메인이 c610..c652 및 호출 함수들의 순서와 register 폭을 해석했다.

## 최초 실행

c610은 RAMf02a.word=1을 쓰고 D0 전체를0으로 만든 뒤49a1a 난수 초기화를 호출한다. 이어 c4cc 오브젝트 정리와 caf0 화면 reset을 수행하고47570 전체 게임 초기화를 호출한다. C++ `restart_game`은 기존 `seed_random`, `remove_objects`, `reset_game_screen`, `initialize_game`를 이 순서로 연결한다. 사전 수집한 목록이나 가상의 초기 상태로 대체하지 않는다. 제거가 반환한 실제 A6와 D0/D1/D3를 다음 단계에 넘긴다.

c4cc의 watchdog과 caf0의 VRAM/watchdog 쓰기를 호출 순서대로 누적한다. caf0의2072개 port는 최초 호출에만 생성한다. 이후47570의 word 또는 byte producer가3aea에서 대기하면 이미 수행한 seed·제거·화면 초기화 결과와 그 호출의 port를 반환한다. 사운드 접두부/후속 초기화 자체는 MMIO 쓰기가 없다. conditional external status 읽기는 기존47570 규칙을 따른다.

기존 helper 계약은 [object-removal.md](object-removal.md), [game-initialization.md](game-initialization.md), [game-prelude.md](game-prelude.md)에 분리돼 있다. screen reset의 단독 검증과 자연 화면/시간축 실행은 구분한다.

## 두 단계의 state

`GameRestartState`는 outer phase, A6, `GameInitializationState`를 담는다. D0/D1/D3는 initialization.prelude의 전체32bit 필드를 사용한다.

- outer phase0은 최초 실행이다. inner returned=false, phase0/next_pc47570 및 모든 pending이 기본 idle이어야 한다. 입력 D0/D1/D3 자체는 임의 값이 가능하다.
- outer phase1은 사운드 대기 재개다. inner returned=false, phase1..3/next_pc3aea가 필요하다. word/byte pending, captured next와 D0/D1의 일관성은 기존 initialization API가 검증한다.
- outer phase2는 c652 RTS까지 반환한 상태다. 이미 완료된 이 상태는 다시 호출할 수 없다.

phase1 재개에서는 **initialize_game만** 실행한다. f02a=1 쓰기, 난수 seed, 제거, screen reset을 반복하지 않는다. repeated wait는 RAM/pending을 그대로 두며 포트와 외부 읽기를 추가하지 않는다. 완료 후에는 아래 후속 처리를 이어 실행한다.

## 완료 직전의 live selector

47570이 반환하면 **live** RAMf02a.word를 읽어 bit0만 남기고 같은 word에 저장한다. D0.low=source+6으로SelectStage를 실행하므로 stage는6 또는7이다. D0 상위 word를 보존하는 명령 폭을 유지한다. 이후 f02a.word를 다시 읽어 D0.low에 넣고3162 input 초기화를 호출한다.

이 구현은 불변 원본 ROM180.word=0 조건의 기존 `initialize_input` API를 사용한다. selector0/1은 replay를 설정하며3162의 최종 D0.low는0이고 D1/D3는 보존된다. input API 자체는register 반환을 제공하지 않으므로 integration이 확인된 D0.low=0을 명시적으로 반영한다. 다른 ROM180 값에 대한 CPU 실행기로 확대하지 않는다.

현재 A6의 정렬/범위를 다시 확인하고 그 오브젝트 callback long에 c654를 쓴 뒤 outer phase2로 반환한다. **callbackc654는 설치만 하며 실행하지 않는다.** inner next_pc475a4/phase4는 마지막 내부 경계다. 이를 c652의 caller 반환 PC나 다음 실행 PC라고 표현하지 않는다. 반환 여부는 outer_phase=2 및 inner returned=true로 표시한다.

## 오류와 리소스

RAM은 정확히65536byte이며 입력/최종 A6는 짝수 CPU RAM 주소에서c4-byte 범위가 필요하다. 함수 전체는 candidate RAM/state/reads/ordered ports에서 실행한다. 최초 seed/제거/화면 작업이 성공한 뒤47570 또는 최종 input 리소스에서 오류가 발생해도 그 호출 전체의 RAM/state/read count/ports를 보존한다. 대기 재개에서 초기화가 완료된 뒤input 검증이 실패한 경우에도 입력 pending과 대기 state가 유지된다.

리소스는 실제 MS5D 파일 두 개다.

| 입력 | 원본 CPU/ROM 시작 | payload | 파일 SHA256 |
| --- | --- | ---: | --- |
| game_records.ms5d | 4cf64 | 320byte | 959b4a00c3412fb7efb01bbc696b0f7acea4787cf521ac128e951d999b97979a |
| input_streams.ms5d | f01fe | 1810hex byte | 5fd8e6f40f544d2c0c75d3559a885968d570277ca992076023e000ab0477ec0c |

C++는 사용하는 단계에서만 리소스를 검증하므로 사운드 대기 중엔 아직 필요하지 않은 리소스가 없어도 된다. CLI는 두 파일을 먼저 로드한다. ROM 데이터는 Git에 추가하지 않으며 원본 재생성 도구와 loader를 사용한다.

## CLI와 재현

```sh
build/restart_game --phase OUTER_PHASE --a6 A6 \
  --state PC D0 D1 D3 INNER_PHASE \
  [--word PHASE LOW CURSOR COMMAND TAIL NEXT] \
  [--byte COMMAND TAIL NEXT] \
  EXTERNAL INPUT_RAM OUTPUT_RAM OUTPUT_PORTS RECORDS.ms5d STREAMS.ms5d
```

필수 leading 옵션3개는 순서를 바꿀 수 있다. 중복 옵션은 거부한다. 최초 입력은 outer phase0, inner PC47570/phase0이고 대기 재개는 실제 반환된 full RAM/register/pending을 함께 전달한다. --returned 입력 옵션은 없다. 숫자는 unsigned decimal/0x hex이며 각 필드 폭을 검사한다.

JSON은 outer_phase/a6/writes와 기존 initialization의 next_pc/d0/d1/d3/phase/external_reads/word/byte/returned를 함께 담는다. 포트 파일은 size(byte)/address(BE32)/value(BE32)의9byte records다. RAM·port·resource의 모든 경로 alias를 canonical 경로 및inode로 확인한다. API 오류가 있으면 기존 output을 열지 않는다.

```sh
make build/restart_game build/game_restart_test
./build/game_restart_test
python3 tools/verify_game_restart.py
```

targeted build와 C++ 단위 테스트는 통과했다. 단위 테스트는 늦은 input 실패의 전체 rollback, 첫 대기의2072screen ports, repeated wait의 새 port 없음, 재개 시 seed/screen 재실행 없음, live f02a=0에서stage6/stream0 선택, 완료상태 및 malformed pending 거부를 검사한다.

## 원본 실행 비교

`artifacts/game_restart/verification.json`의 최종 실행은 Unicorn2.1.4에서 원본144경계/오류38조건을 통과했다. 전체 RAM/D0/D1/D3/A6/pending과 ordered ports166360개가 일치하고 conditional external read56회를 확인했다. 원본 코드는 수정하지 않았다. c610부터 실제c652 RTS 또는3aea 대기까지 중첩 원본 함수를 실행하며 ROM180.word=0도 유지한다.

실제2790 initializer와 MS5I CLI가 만든 runtime list를 사용하고 일부 fixture는 실제28ae로 child를 할당한다. palette cleanup 리소스는 원본3ef2 초기화로 만든다. 독립 최초 완료48조건과 승계32시퀀스×3호출96경계를 포함한다. 최초 완료는 A6=sentinel100820과 실제 controller1008e4를 모두 검사하며 child allocator의 parent도 해당 caller에 맞춘다. 대기 승계32시퀀스는 모두 실제 controller A6=1008e4를 사용한다. outer phase2 반환80회이며 대기64경계는 word high/low/byte08/byte20 각각16회다. 최초pending 종류를 원본 반환stack에서 독립적으로 확인한다. repeated wait와 완료 재개는 선행 seed/removal/screen port0개를 확인하여 prefix가 반복되지 않음을 검증한다.

승계 시 실제 parsed CLI 출력의 전체 RAM/register/pending을 다음 호출로 전달하고 원본 CPU context/stack도 유지한다. 호스트가 sound head를 release하고 f02a를0/1/2/ffff로 바꾸는 조건을 명시한다. 결과 stage6/7 및 실제input replay 포인터가 live bit0에 따라 달라짐을 확인한다. **sound head와f02a 변경은 bounded fixture이며 IRQ나 자연 시간축 동등성 근거가 아니다.** callbackc654, 다른 레지스터/전체CCR/stack 동등성 및 자연 scheduler 실행은 별도 범위다. malformed pending·returned 상태·late stream 실패·alias 등의 오류는 원본을 실행하지 않고 C++ 출력 보존을 검사한다.

최종 보고서 SHA256은 `eff31a72a6ac06645d6cb99f52b78a9103a10ff2a51810043073c468302fdd30`다. 선행33-error 및 sentinel만 사용한120-boundary 보고서는 실제 waitpending 음성과 controller A6 범위를 보완한 이144-boundary 최종본으로 대체한다. 전체 `make all test`도 성공했으며 Python88개와 전체 C++ 테스트가 통과했다.
