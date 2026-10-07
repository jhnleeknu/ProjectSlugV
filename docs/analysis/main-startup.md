# 메인 e4a 초기화의 직접 호출 근거

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 CPU 주소는 고정 ROM의 파일 오프셋과 같다. 메인이 원본 명령과 테이블을 직접 확인했다. e4a→e74 초기화를 C++로 구현하고 원본 실행과 비교했다. 자연 부팅 전체를 구현했다는 뜻은 아니다.

## 호출 순서

- e4a는 e7bf4를 호출한다. e7bf4는8e82로 고정 참조 슬롯을 해제하고 A0=e7b58을8da2에 전달한 뒤, D0.word=6/D1.word=1/D2.word=12로8cda에 tail-call한다.
- e50의 MOVEQ0 뒤 RAM000e.word=0, A6+7e.word=0, A6+84.byte=1, A6+76.long=0을 쓴다.
- e68은903a를 호출한다. 903a→9056은 RAM7def.byte=ff, 이어7dee/7df0/7df1.byte=0을 쓴다. 9546은7dfe.byte 및7dff..7e06의8바이트를0으로 만든다. 이 마지막 루프의 MOVEQ는 D0 전체를0으로 만든다.
- e6e는 A6의 선두 long을e74로 바꾼 뒤 준비 구간으로 이어진다. 기존 e74 준비 API와 분리하여 초기화를 먼저 복원해야 한다.

8e82는256개 노드 중 참조word가ffff인 노드만0으로 만들고8e4a로 free ring에 이동한다. 일반 참조 노드는 보존한다. 8da2는6바이트 고정 등록 레코드를 순회하며 source ID 하위byte의 bucket 선두로 노드를 옮긴다. 8dd6은 sentinel+2의 next를 비교하며, 이미 선두이면 unlink/insert를 건너뛴다. 선두 이동 시 D3.low에는 이전 선두가 남고 D3.high는 보존된다. 참조word=ffff로 고정하고, source ID가ffff이면 두 ID=ffff와 flags=2를 쓴다. 그렇지 않으면 두 ID와 flags|80을 쓴다. 테이블 종결은 목적 슬롯ffff이며 source IDffff와 다르다. 이 특수 source ID를 실제 팔레트 데이터로 추출하면 안 된다.

## e7b58 등록 테이블

| 슬롯 | source ID | flags |
| ---: | ---: | ---: |
| 0 | 0062 | 02 |
| 1 | 0069 | 02 |
| 2 | 006b | 02 |
| 3 | 006c | 02 |
| 4 | 0063 | 02 |
| 5 | 01b8 | 02 |
| 6 | 0062 | 02 |
| 7 | 0001 | 00 |
| 8 | 0b03 | 00 |
| 9 | 0b04 | 00 |
| 10 | 0b05 | 00 |
| 15 | 0b06 | 00 |
| 11 | ffff | 02 |
| 12 | ffff | 02 |
| 13 | ffff | 02 |
| 14 | ffff | 02 |
| 255 | 0001 | 00 |

모든 레코드의6번째 byte는0이다. e7bbe의wordffff가 종결자다. 총17레코드, 유효 source ID11종이며 고정 등록 뒤 slot6의 혼합 목표를source1/weight12로 설정한다.

## 구현과 리소스

initialize_main_frame은 기존 palette_control의8cda setter와 고정 슬롯 해제·등록을 연결한다. 정확한64KiB RAM, 짝수 object RAM offset, e7b58의104바이트 MS5D를 받는다. 실패 시 RAM/전체D0D1D3/포트를 보존한다. 완료하면 object callback=e74, D0=0을 반환하며 e74 자체는 실행하지 않는다.

tools/pack_main_startup.py는 기존 MS5D v1 kind1로17레코드와 종결자를 보존한다. tools/pack_palettes.py는 disabled binding을 metadata에 보존하고 실제 sourceffff 추출을 제외한다. 추가7개 ID로 현재 sparse MS5P는29개 ID다. 전체 팔레트 카탈로그 완료를 의미하지 않는다.

이 직접 호출 체인은 정적 e4a 진입의 근거다. e4a가 실제 부팅에서 스케줄되는 전체 경로나 BIOS 전후 동작이 관측되었다는 주장은 하지 않는다.

8e82의 watchdog은 진입 D0의 하위byte를 쓰며, 루프 완료 D0=1000이므로 이어지는8da2 watchdog 값은0이다. e7c08의 MOVE.W로 최종 D1.low=1, D1.high는 보존된다. 최종 D3.low는 마지막 실제 목록 이동에서 읽은 값이며, 단순 상수로 치환하지 않는다. e50/9550 이후 D0 전체는0이다.

## 실행과 검증

```sh
.venv/bin/python tools/pack_main_startup.py
.venv/bin/python tools/pack_palettes.py
build/start_main D0 D1 D3 OBJECT_RAM_OFFSET INPUT_RAM OUTPUT_RAM OUTPUT_PORTS extracted/runtime/main_startup.ms5d
.venv/bin/python tools/verify_main_startup.py
```

CLI의 숫자는10진수 또는0x접두16진수다. JSON은 d0/d1/d3/next_pc/writes를 담는다. A5=108000은 암묵적인 진입 계약이며 A6는 object offset+100000이다. 출력RAM/D1/D3를 기존 prepare_main_frame에 next_pc=e74로 전달한다.

원본209조건에서 전체RAM/D0D1D3 및 watchdog418쓰기가 일치했다. 실제3ef2 초기화, e7bf4 기존 고정 등록,8ebe 일반 참조를 fixture로 사용했다. 다섯3회 시퀀스는 실제 CLI 출력을 승계한다. 오류32조건은 기존 출력 보존을 확인했다. 초기화→준비2조건은 원본 CPU context를 유지하고 CLI 상태를 전달하여 추가포트24개/영상읽기2회까지 일치했다. 보고서 SHA256 `2bf5387682dae840040749fb882917080a43ecedb22a1dd13766ca123cccea7a`.

다음 초기 노드1008e4의 callback c52a는9056→필드 초기화→8b64 palette fill 설정 뒤c560으로 바뀐다. c560은8bb6으로 fill counter를 읽어0이 될 때까지 반환한다. c56e 이후 같은e7bf4,49a1a 난수 초기화 및47570의 넓은 초기화 호출로 이어진다. 이 후속 callback은 아직 C++로 연결하지 않았다.
