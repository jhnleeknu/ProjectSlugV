# Null-script 초기 장면과 원본 debug 표시

## 범위와 원본 근거

프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 명령 주소는 첫1MiB의 고정 ROM CPU 주소이며 canonical decrypted 파일의 같은 오프셋이다. RAM 및 MMIO 주소를 ROM 오프셋으로 취급하지 않는다. 아래 A5 상대 RAM 참조는 원본 호출 문맥 A5=`108000`을 사용한다. 주소·offset·상수는 별도 표기가 없으면16진수이며1280/512/8192 등의 바이트·반복 개수는10진수다.

`engine/include/ms5/scene_initialization.h`와 `engine/src/scene_initialization.cpp`에는 두 API를 둔다. `update_scene_debug`는 원본1afda의 일반 debug 분기, `initialize_stage_scene`은477e4의 D0=0/A0=0 준비와1a5a4 호출을477ee 반환 경계까지 연결하는 null-script 특수 경로다. 두 API는 전체64KiB RAM, 전체32bit D0/D1/D3와 순서 있는 `VideoPortWrite` 목록을 운반한다. 실패 시 RAM·레지스터·포트를 모두 보존한다. 다른 레지스터·CCR·stack·자연 하드웨어 시점은 계약 밖이다.

명령 근거는 `artifacts/stage_startup/inventory.asm`, [stage-startup.md](stage-startup.md)의 메인 정적 해석과 제한된 원본 probe다. 개별 좌표 helper 계약은 [scene-node.md](scene-node.md)에 있다.477ee 이후 stage/area 조회와 나머지477e4 본문은 이 API가 실행하지 않는다. 임의 nonzero script나19e64 traversal을 null-script 구현으로 대체하지 않는다.

## 1afda의 분기와 반복 읽기

원본은 RAM10f000의 bit3/4를 검사한다. 두 bit 모두0이면 RAM10d44e.byte를0으로 만든다. 이전 flag도0이면 D0/D1/D3와 포트를 보존한 채 반환한다. 이전 flag가 비영이면 `1b00e`의 tail JMP로 caf0 화면 초기화를 실행한다. 이때 caf0의2072개 watchdog/비디오 쓰기와 RAM100966.byte=0, 최종 D0=`75807500`, D1=`00007000`, D3=`00000020`이 연결된다. 자세한 caf0 근거는 기존 화면 reset API와 검증 기록을 따른다.

어느 bit라도 켜지면 `1b01c..1b030`은 RAM10d3a2/10d3a6,10916a/10916e,10b1ea/10b1ee의 여섯 long에 `fff80000` AND를 적용한다. 이어10d44e.byte를ff로 만든다. 이전 flag가0이면 바로 draw로 간다. 이전 flag가 비영이면 좌표 변화 판정을 수행한다.

변화 판정에는 원본의 반복 읽기를 보존한다. `1b042`가 A0=`109156`을 설정하고 +14/+18.long을 D0/D1에, +1c/+20.long을 D2/D3에 읽는다. `1b056`의 SUB.L과 `1b058`의 SUBX.L 뒤 BNE로 draw를 선택한다. 첫 판정이 같으면 `1b05e`는 두 번째 노드10b1d6을 **A1**에 LEA하지만, `1b062..1b06e`의 읽기는 계속 **A0** 기준이다. 두 번째 노드의 좌표를 대신 읽도록 고치지 않는다. 이는 원본 명령의 관측된 참조이며 게임 설계 의도를 추정한 최적화가 아니다.

SUBX의 Z는 sticky다. 첫 X 차이가 비영이면 Y 결과가0이어도 Z가0으로 유지되어 draw해야 한다. Y 차이는 X subtraction의 borrow를 포함해32bit wrap으로 계산한다. 따라서 단순히 Y 결과만0인지 검사하는 구현과 다르다. 비영 이전 flag에서 두 비교가 모두 같으면 D0/D1은 첫 노드의 현재 좌표 전체값, D3은0으로 반환하고 포트는 없다. 다른 노드만 변경된 경우도 원본의 첫 노드 반복 읽기를 따른다.

## Debug draw와 lookup

`1b07c`는 D2.word=0x27(열39), D3.word=0x1f(행31)로 시작한다. 내부 DBRA는 column39..0, 외부 DBRA는 row31..0 순서다. 따라서 한 row에서39번째 column부터0번째까지 쓴 뒤 다음 row로 내려간다.1280개 모두 주소3c0000의 long 쓰기이며 각 값의 highword는 `7000 + column*32 + row`, lowword는 lookup tile이다. 이 순서를 row/column 오름차순으로 바꾸지 않는다.

bit3이 켜지면109156 노드를 먼저 조회한다. 결과가0320이고 bit4도 켜지면10b1d6 노드를 조회한다. bit3이 꺼지고 bit4가 켜진 경우는 두 번째 노드를 바로 조회한다.0320의 표시 의미나 타일 내용은 별도 렌더링 분석 대상이며 이 값은 원본 비교·선택 조건으로만 사용한다.

`1b0e0`의 계산은 다음 명령상 폭을 유지한다. node+14.word를 column*8에서 빼고1f8로 mask해 X를 만든다. row*8에 node+18.word를 더해1f8로 mask한 뒤2bit logical right shift해 Y를 만든다. node lookup offset은 `(X<<4)+Y+80`이다. 노드의 그 BE16 tile을 읽고 lowbyte에58을 더한 뒤 byte로 wrap해 인덱스를 만든다. 인덱스*2로1af12 기준 BE16 값을 읽는다. 값이0320이 아니면 tile의c000 bits에서 계산한 offset0/2/4/6을1afd2에 더해 BE16 flag를 OR한다.

Lookup의 D0/D1 갱신은 word 연산이므로 draw 진입 시의 highword를 보존한다. 변화 판정 경로를 거치면 이미 D0/D1 전체가 현재 좌표로 덮였으므로 이때의 highword를 보존한다. D3도 draw 시작의 MOVE.W0x1f과 DBRA를 따라 highword를 보존하며, 완료 lowword는ffff다.1280개 포트의 highword 계산에 사용되는 scratch D2/D4 등을 일반 레지스터 반환 계약으로 확장하지 않는다.

## 원본 lookup 창의 MS5D 리소스

추출 명령은 `.venv/bin/python tools/pack_scene_debug.py`이며 `extracted/runtime/scene_debug.ms5d`와 `scene_debug.manifest.json`을 만든다. 기존 MS5D v1 kind1을 그대로 사용하고 새로운 포맷을 만들지 않는다. 안정 ID는 `scene-debug:0001af12`다. source CPU 주소와 ROM 파일 오프셋은1af12, end exclusive는1b112이며 payload512바이트·전체 파일544바이트다.

payload SHA256은 `44aae050bb5e0eb32e593dee5e8d81ea41b3c18dd0c6913c763d7ef446bb7583`, 컨테이너 SHA256은 `ca28489b53c66df310f32a2afca6312f56714f2e5af3fb65a2da17e3c2c4581f`다. C++ 로더는 기존 `engine/src/fixed_data_resource.cpp`의 `load_fixed_data_resource`이며 `FixedDataResource`를 scene API에 전달한다. API는 source CPU/ROM 주소와 정확한512바이트 길이를 검사한다. 변경된 raw bytes를 원본으로 간주하는 근거는 packer의 pinned hash와 소비 검증에서 별도로 확인한다.

창은 byte index 전체0..255가 주소로 접근할 수 있는256word 범위다. **원본 논리 테이블의 크기가512바이트라는 주장은 하지 않는다.** 그 안에1afd2의8바이트 flag와 명령 코드가 겹친다. unconsumed/미해석 바이트도 모두 보존한다. 자연 실행에서 모든 인덱스가 사용된다는 주장도 하지 않는다.

Packer는 canonical 전체 SHA와1b094/1b098의 base·flag LEA,1b102..1b126의 lookup 명령 바이트를 검증한다. synthetic 테스트 일곱 개가 payload·instruction evidence·전체 해시 변경, header schema, CRC와 길이 오류를 확인한다. ROM 바이트를 tracked 테스트 fixture로 넣지 않는다. Host API는 debug가 꺼진 분기에도 이 resource shape를 요구하므로, 이 요구를 원본의 추가 메모리 읽기 또는 native fault라고 표현하지 않는다.

## 477e4 prefix의 null-script 초기화

477e4는 MOVEQ0으로 D0 전체를0으로 만들고 A0=0을 설정한 뒤1a5a4를 호출한다. 이 특수 호출자에서 메인이 해석한 null-script 분기와 실제 원본 순서를 사용한다. 결과 상수만 쓰거나 debug 표시를 생략하는 방식으로 완료하지 않는다.

진입에서 RAM100010.word=1을 기록하고, PVC word 쓰기를 `2ffff2=2000`, `2ffff0=0` 순서로 기록한다.1a07a/19768 등의 null 입력 초기화, global word/long 저장, 좌표 node 초기화·parent 설정을 이어 수행한다.109156/10b1d6의 타일 조회 버퍼은17292를 통해 각각8192바이트를 지운다. 네 노드109156/10b1d6/10d256/10d2d6과 각 metadata를 원본 helper 순서에 맞춰 준비한다.

1a7a8의 scale enable은 RAM10d40c의 **byte**를 BTST.B한 뒤 BNE로 건너뛰는 원본 조건을 따른다. 즉 해당 bit가0일 때1724c 또는1726c를 호출한다. 이 initializer는 d40c를0으로 초기화하므로 네 노드 각각에서 두 scale helper를 실행하며, 합계 네 번의1724c와 네 번의1726c를 좌표 advance와 원본 순서로 연결한다. 입력과 결과가0일 수 있어도 같은 최종 RAM이라는 이유로 이 호출들을 생략하지 않는다. 조건을 word로 읽거나 bit가 켜진 경우를 호출 조건으로 뒤집는 구현은 계약과 다르다.

Null script 조건에서1a26a는 즉시 반환하고199d4는D7=0을 만든다는 메인의 해석이다. d418/d41c의 비교 때문에 preparation 반복은1회이며1a7a8 내부 좌표 갱신과1afda debug 분기를 연결한다. d41e=7fff와d41c=0의 비교는 추가1a29e를 건너뛰고, d40e=0의1a414 경로는 null-script 반환이다. 이 분기 특수화와 각 저장의 근거 주소는 [stage-startup.md](stage-startup.md)에 기록한다.

마지막 재설정 helper들을 마친 뒤 RAM100010.word=0, PVC `2ffff2=1000`, `2ffff0=0`을 순서대로 기록하고477ee 경계에 대응하는 반환 결과를 제공한다. 기본 flag0은 이 네 PVC 쓰기만이며 debug bit 경로는 그 사이에1280개의 VRAM 쓰기를 포함한다. 이 statement는 메인의 원본16조건 probe와 계약 근거이며 새로운 C++ 동등성 결과 수치와 구분한다. 일반 source bank 매핑은 원본 probe의2000/1000 PVC 모델과 별도 검증 대상이다.

## 검증 상태와 남은 범위

독립 검증 명령 `.venv/bin/python tools/verify_scene_initialization.py`의 최종 `artifacts/scene_initialization/verification.json`을 확인했다. 원본576조건(debug524/initializer52), 오류 보존24조건, 순서 있는 포트672744개가 통과했다. 전체64KiB RAM·전체 D0/D1/D3·포트 순서가 일치했고 MMIO read0, 원본 코드 변경0이다. 보고서 SHA256은 `451015b835b3a4e741bddf61b43e21cf5c8d72d1d4dc30ff4c4c5107f7554bb4`다.

실제 lookup 명령에서256개 index와4 upper flag 조합, 합계1024조합의 방문을 관측했다. 첫/둘째 노드 우선순위, 첫 노드 반복 history 판정, sticky SUBX Z, word high 보존과 descending draw 순서를 포함한다. 일곱 CLI 승계시퀀스는 실제 출력 RAM/D0/D1/D3를 다음 호출에 운반한다. history snapshot과 f000 bit 해제는 세 시퀀스의 명시적 host 입력이며 나머지 네 시퀀스에는 중간 host 입력이 없다. 잘못된 table window는 API 진입 시 거부되므로 initializer의 late rollback 관측이라고 주장하지 않는다.

검증 시작·종료의 실행 파일 해시는 동일한 `aab6915637f81851718c0951cfb83ea4099d132d36467848f690eb3f66e62f49`다. 전체 `make -j3 all test` 로그 `artifacts/scene_initialization_build_test.log`에서 Python95검사와 C++88 test executable 실행, warning/error0을 확인했고 메인이 terminal exit0을 확인했다. 메인 리뷰는 [0142-scene-initialization.md](../reviews/0142-scene-initialization.md)다.

원본 probe16조건 모두 RTS에 도달했다는 이전 결과는 `artifacts/stage_initialization/probe.json` SHA256 `18c241850f4c7e0adf715963cbe3bb98f653590cacb97e12715e9afd458c4e05`에 있다. 입력 A0=0/D0=0에 한정되고 C++ 동등성 검사가 아니다. 원본을 바꾸거나 helper를 fake return으로 교체하지 않는다.477ee 이후 stage query·callback dispatch, 임의 nonzero scene script,19e64 traversal, 자연 scheduler와 실제 픽셀·전체 스테이지게임플레이는 계속 별도 미완료 범위다.

## CLI 경계

기존 resource를 사용하는 CLI 형식은 다음과 같다.

```text
build/step_scene_initialization D0 D1 D3 INPUT OUTPUT PORTS TABLES
build/step_scene_initialization --debug D0 D1 D3 INPUT OUTPUT PORTS TABLES
```

기본 모드는477ee 경계까지 실행하고 JSON에 `next_pc=477ee`와 `d0/d1/d3/writes`를 출력한다. `--debug`는 원본1afda의 RTS에 대응하며 JSON은 `d0/d1/d3/writes`만 제공한다. Debug에 가상 caller PC를 만들어 붙이지 않는다. PORTS 파일은 기존 `VideoPortWrite`의 순서 있는 바이너리 출력이다.

## 다음 연결 과제

다음은477ee 이후 stage catalog와 사운드 two-byte queue 대기를 연결하는 작업이다. 메인이 원본4814e에서 RAM10d68c.word=1 저장과48154의RTS를 확인했다.3d58은 기존 D0.byte를 stack에 보존하고0a를 넣어3d6a의3ac8 호출로 보낸 뒤, 원래 byte를 복구해 ADD.B20, SCS.B D1, OR.W D1,D0을 거쳐3ac8로 BRA한다. 이는 두 queue 호출의 대기와 재개를 별도로 운반해야 한다는 다음 계약 근거이며 generic wrapper 구현 완료를 뜻하지 않는다. stage 앞 연결과477e4의 나머지 본문은 아직 미완료다.
