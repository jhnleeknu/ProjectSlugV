# 47570 전체 초기화와 475a4 후속 구간

원본 프로그램은 `extracted/program/maincpu.decrypted.be.bin`이며 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 이 문서의 ROM CPU 주소는 고정 매핑에서 파일 오프셋과 같다. RAM 주소 표기는 CPU `100000`을 뺀 offset이며, 예를 들어 RAM `d694`는 CPU `10d694`다. 구현은 A5=`108000`인 원본 호출 조건을 따른다.

메인이 해석한 호출 순서와 필드 효과를 C++11로 구현하고, 불변 원본 코드의 Unicorn 실행과 전체 64KiB RAM 및 전체 D0/D1/D3를 비교했다. 자동 호출 목록 자체를 의미 확인으로 취급하지 않는다. 이전 접두부의 별도 IRQ 검증은 [game-prelude.md](game-prelude.md), c52a/c560에서 c584까지는 [game-startup.md](game-startup.md)에 기록돼 있다. 이번 범위는 47570 전체 함수와 475a4 suffix다. 자연 부팅의 호출자·스케줄러 전체를 완성했다는 뜻은 아니다.

## 전체 실행과 대기 상태

`initialize_game`은 먼저 `prepare_game_prelude`로 47570 접두부를 실행한다. RAM d683/d694/d69c byte, 000e/089e word, de14/de1c long, d680/d681 byte를 지운다. de26에 ROM 포인터 `e89e4`를 저장하고 de2e=`ff`, de2f=0을 쓴다. 포인터는 이 함수에서 역참조하지 않는다.

word 사운드 명령 `0720`을 enqueue한 뒤 RAM 4d7e.byte를 지우고 byte 명령 `08`, `20`을 순서대로 보낸다. word overflow 및 두 byte 전송은 각각 producer 대기 PC `3aea`에서 멈출 수 있다. `GamePreludeState` phase는 0=최초 47570, 1=word overflow, 2=byte08, 3=byte20, 4=접두부 완료 475a4다. word pending 내부 phase 1/2는 high/low byte를 구분한다. captured tail/next와 전체 레지스터를 함께 승계하며, 재개는 접두부나 외부 상태 읽기를 반복하지 않는다.

접두부 D3 전체와 D1 상위 word는 보존된다. D1.low는 대기 또는 완료 byte의 captured next다. D0는 word 대기에서 `0700 | command`, byte08에서 `0708`, byte20 및 접두부 완료에서 `0720`이다. RAM12=1, fd82!=0, fe80=0 조건에서만 external status byte를 CPU `d00046`에서 읽으며 `external_reads`로 호출당 읽기 여부를 반환한다. 이 함수 전체에 MMIO 쓰기는 없다.

접두부가 완료되면 같은 API 호출에서 suffix를 실행한다. `returned=true`이면 원본 47640 RTS까지 완료했고 D0/D1/D3는 최종 반환값이다. 이때 JSON의 next_pc=`475a4`, phase=4는 마지막 내부 경계 표시이며 실제 호출자 반환 PC가 아니다. 이미 returned인 상태를 재호출하면 거부한다. suffix에서 실패하면 그 호출의 접두부 변경까지 포함해 RAM/state/external_reads 전체를 보존한다. 대기 중 C++ API는 레코드 리소스를 사용하지 않지만 CLI는 리소스 파일을 먼저 로드한다.

## 475a4 suffix의 순서

`finish_game_initialization`은 사운드 접두부 없이 suffix만 실행한다. 구현은 다음 순서를 보존한다.

1. RAM d686.word=0; b7a20, 4d126, 1bcfe를 호출한다.
2. D0=0/D1=0으로 481de를 호출해 레코드0을 d694에 설정한다. D0=1/D1=0으로 같은 레코드를 d69c에 설정한다.
3. d682.byte=0; 1bd12를 다시 호출한다. de2a.long에 원본 포인터 `e89ec`를 저장한다. 이 포인터도 역참조하지 않는다.
4. 3d42는 RTS이며, 3dce는 4d91.bit4를 지우고 CPU RAM `100006`/`10000a` callback long을 `3dcc`로 설정한다.
5. 49a8e, 4aa30, b4a24, 2ef90, 46f2e, 4d13c, 4ddb6을 순서대로 호출한다. 2ef90과 46f2e 사이 6f1c2는 RTS다. 각 고정 리셋의 필드 범위는 [game-prelude.md](game-prelude.md)의 리셋 표와 `game_reset.cpp`가 정의한다.
6. dc8c/dc8d byte=0, d690.word=`00a0`, d692.word=`0180`, d68e.byte=0, d688/d68a/d68c word=0으로 한다. 인접 byte d68f는 보존한다.

4aa30에서 전체 D0/D1/D3를 0으로 하고 후속 리셋을 거쳐 최종 D0/D1/D3는 모두 0이다. 이 결과는 개별 레코드 helper의 register 보존 규칙과 구분한다.

## 고정 오브젝트와 selector의 두 기준

`reset_game_objects`는 1bcfe 또는 1bd12만 지원한다. 대상은 CPU `100cb8`, `100da8`이며 callback long이 `270e`일 때만 inactive다. callback=0도 active다. 모든 호출에서 D0 상위 word를 보존한다. D1/D3는 원본에서 보존되며 이 API는 두 레지스터를 인자로 받지 않는다.

1bcfe는 두 오브젝트 각각에 1bd2e를 실행한 뒤 1bd12로 fallthrough한다. active 1bd2e는 +9e/+a0/+9f/+a1 byte를 지우고 +78.word를 D0.low로 읽는다. selector가 0이면 d450, 그 외에는 d460을 선택해 CPU 포인터를 object+8c.long에 저장한다. 선택 구조체의 +6=1, +7=10, +4/+5=0, +c.word=ffff, +3=ff를 쓴다.

이어 1be84는 D0.low를 `&1`로 마스킹한다. **구조체 선택은 zero/nonzero, byte0/word8 지우기는 parity 기준이다.** selector=2이면 저장된 포인터와 초기화 구조체는 d460이지만 byte0 및 word8은 d450에서 지운다. selector를 0/1로 제한하거나 두 기준을 합쳐서는 안 된다.

1bd2e는 1bd90으로도 fallthrough한다. active 1bd90은 callback=`1d1f4`, +15=0, +61=80, +a8.bit4=1, +81/+82=0으로 한다. +78.word를 다시 읽어 D0.low에 넣고 zero면 d487, nonzero면 d48f byte를 지운다. **live** object+8c 포인터를 다시 읽어 그 구조체 +2/+1 byte와 +a.word를 지운다. 마지막 active 오브젝트의 raw selector가 최종 D0.low다.

1bd12는 d478.word/d474.long을 지운 뒤 두 오브젝트에 1bd90을 다시 실행한다. 단독 1bd12 API는 임의의 live 포인터를 그대로 사용하며, CPU RAM의 짝수 주소에서 12-byte 범위가 필요하다. 두 번째 오브젝트의 잘못된 포인터가 뒤늦게 발견돼도 앞선 변경과 D0를 모두 rollback한다.

## 20×16-byte 레코드

`tools/pack_game_records.py`는 CPU/ROM `4cf64..4d0a4`의 320byte를 MS5D v1 kind1으로 보존한다. 20개 레코드의 모든 byte를 저장하며 각 레코드와 원본 명령 근거의 해시를 manifest에 기록한다. 32byte header를 포함한 파일은 352byte다.

- payload SHA256: `9b1c4db78844053dff88ac7c863b15852c1ad1b9e500a831ed5a01fa9eff923c`
- `extracted/runtime/game_records.ms5d` SHA256: `959b4a00c3412fb7efb01bbc696b0f7acea4787cf521ac128e951d999b97979a`

packer는 원본 프로그램 해시, 481de/4d81c 명령 byte 및 payload 해시를 확인한다. C++ loader는 MS5D 형식을 검증하고 `configure_game_record`는 주소/320byte 크기/unsigned index를 검증한다. C++ helper 자체가 immutable payload 해시를 강제하지는 않는다. 실제 원본 리소스는 native verifier가 byte 대조한다.

481de wrapper는 입력 D0.low.bit0에 따라 목적지를 d694/d69c로 선택한다. 4d81c는 **마스킹 전에** unsigned D1.word<20을 검사한다. 레코드 주소는 `4cf64 + index*16`이다. 반환 D0는 상위 word 보존/하위 index, D1은 MULU 때문에 상위 word=0/하위 record+c.word, D3는 상위 word 보존/하위 record+a.word다.

| 목적지 offset | 값 |
| --- | --- |
| byte0 | index |
| byte1 | record byte2 |
| byte2 | record byte1 |
| byte3 | record word+c의 low byte |
| word4 | record word+a |
| word6 | record word+e |

필드의 게임상 의미나 레코드 이름은 확정하지 않았다. direct 4d81c 독립 API는 제공하지 않는다. index>=20은 C++ 오류로 거부하며 원본 TRAP #15 처리 전체를 구현한 것은 아니다.

## CLI와 재현

```sh
build/reset_game_objects ENTRY D0 INPUT_RAM OUTPUT_RAM
build/configure_game_record D0 D1 D3 INPUT_RAM OUTPUT_RAM RECORDS.ms5d
build/finish_game D0 D1 D3 INPUT_RAM OUTPUT_RAM RECORDS.ms5d
build/initialize_game --state PC D0 D1 D3 PHASE \
  [--word PHASE LOW CURSOR COMMAND TAIL NEXT] \
  [--byte COMMAND TAIL NEXT] [--returned 0|1] \
  EXTERNAL INPUT_RAM OUTPUT_RAM RECORDS.ms5d
```

숫자는 unsigned decimal/0x hex이고 RAM은 정확히 65536byte다. input/output/resource alias를 거부하고 API 검증 실패 시 기존 출력 파일을 보존한다. reset JSON은 d0, record/finish JSON은 d0/d1/d3다. initialize JSON은 접두부 상태와 external_reads, word/byte pending 및 returned를 포함한다.

```sh
python3 tools/pack_game_records.py
python3 -m unittest tools.tests.test_game_records
make build/reset_game_objects build/configure_game_record build/finish_game build/initialize_game \
  build/game_objects_test build/game_records_test build/game_initialization_test
./build/game_objects_test
./build/game_records_test
./build/game_initialization_test
python3 tools/verify_game_objects.py
python3 tools/verify_game_records.py
python3 tools/verify_game_initialization.py
```

## 검증 결과와 한계

Unicorn 2.1.4에서 원본 코드는 수정하지 않았다. 다음 수치는 해당 `artifacts/game_*/verification.json`에서 확인했다.

| 검증 | 원본/C++ 비교 | 오류 출력 보존 | 추가 관측 |
| --- | ---: | ---: | --- |
| game_objects | 149 | 24 | 전체 RAM/D0; 8개×2호출 CLI 승계; 원본 D1/D3 보존; MMIO 쓰기0 |
| game_records | 168 | 32 | 전체 RAM/D0/D1/D3; 2개×4호출 CLI 승계; MMIO 쓰기0 |
| game_initialization | 562 | 31 | 전체 RAM/D0/D1/D3; external read4회; MMIO 쓰기0 |

전체 초기화 비교는 direct suffix 256회, 전체47570 오브젝트 조합256회, 조건부 상태/필터32회, 승계 호출18회다. 최종 returned 548회와 실제 대기14회(phase1=6, phase2=4, phase3=4)를 비교했다. 원본 중첩 함수를 생략하거나 stub으로 바꾸지 않고 RTS 또는 실제 producer wait까지 실행했다. pending은 native stack의 반환주소로 독립 분류했다. 레코드 packer synthetic 테스트는7개이며 C++ 세 단위 테스트도 통과했다.

초기화 승계4시퀀스(5/3/5/5호출)는 실제 CLI의 RAM·전체 레지스터·pending을 유지하고 원본 CPU context/stack을 이어 실행했다. **이번 whole-function 검증은 호스트가 sound head RAM4d74.word를 명시적으로 바꿔 대기를 해제한다.** head 변경은 각각 1→2→12, 2→3, 1→2→12, 2→3→13이다. 이는 bounded fixture이며 IRQ나 스케줄러 동등성 근거가 아니다. 접두부의 별도 실제 IRQ 승계 결과를 전체 suffix 검증의 속성으로 확대하지 않는다.

레코드 승계도 다음 selector/index를 호스트가 제공한다. 오류 index에서 원본 TRAP은 실행하지 않았다. 다른 CPU 레지스터, CCR, stack 동등성, 자연 호출자 실행, 렌더링·전투 및 하드웨어 시간축은 이 검증 범위 밖이다. 저장한 e89e4/e89ec 포인터의 후속 데이터 소비도 미확인이다.

최종 보고서 SHA256 (실제 parsed CLI JSON을 다음 입력으로 전달한 재검증도 동일한 결과다):

- game_objects: `c239a5619c6e929f2cee2ca6f65ccf93635e6f7f35e61d751bedee361d9b75f9`
- game_records: `aa251956b6b4456c5787ab7bfed501160a7a1e72acfcadfaddc9c52d5615cb1b`
- game_initialization: `ba538ea67e01041c8b199c889d8f2a225f18b203bf55e6a281da5464af12a3b2`
