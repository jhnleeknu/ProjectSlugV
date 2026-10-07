# 인터럽트용 팔레트 전송 기록과 D0

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU 주소와 ROM 오프셋이 같다. 대상은72fa 일반 전송과873a 전체 채우기 경로다.

`transfer_palette_banks_traced`는 기존 `transfer_palette_banks`와 동일한 RAM/두 bank/표시bank 결과를 내면서 포트 기록과 전체D0를 반환한다. 기존 데이터 전송 함수를 재사용하고 trace 생성까지 성공한 뒤 모든 출력을 교체한다. 오류 시 RAM/두bank/표시bank/D0/포트 목록을 보존한다. 지원 counter는 기존처럼0과2000이다. 다른 counter의 창 밖 주소 접근은 아직 지원하지 않는다.

## 일반 전송

RAM7ded.bit7을 지우고 이전 값이1이면3a000f.byte에 입력D0의 하위 byte를 쓴다. 첫 staging word를8000으로 마스킹한다. 각32바이트 블록의 첫byte bit7을 지우고 이전 값이1인 블록에 대해8개long을 낮은 주소에서 높은 주소 순으로400000+block offset에 쓴다. 각 전송의D0는 marker 제거 후 블록 첫long이다. 따라서 반환D0는 마지막 dirty 블록의 첫long이며 전송 블록이 없으면 입력D0 그대로다.

pending 여부와 관계없이 일반 경로는300001.byte에 최종D0 하위byte를 쓴다. 이후 RAM7dec가0이면3a000f, 아니면3a001f에 같은 하위byte를 써 표시bank를 선택한다. 최초bank 선택, 실제 팔레트 쓰기, watchdog, 최종bank 선택의 순서를 기록한다.

## 전체 채우기

counter2000 경로는3a001f에 입력D0 하위byte를 쓰고 RAM7da2..7dc1의32바이트를D0..D7으로 읽는다.256개의 MOVEM predecrement는 각 블록에서D7부터D0까지 높은 주소에서 낮은 주소로long을 쓴다. 첫 주소는401ffc, 마지막long 주소는400000이다. 그 뒤400000.word에0을 쓴다.

D0는 패턴의 첫long이며 마지막0 쓰기로 변하지 않는다. 이 경로는watchdog을 건너뛰고 최종bank 선택만 수행한다. 따라서 총2,051개 기록(선택1+long2,048+word1+선택1)을 낸다.

```sh
build/trace_palette_transfer INPUT_RAM INPUT_BANKS OUTPUT_RAM OUTPUT_BANKS OUTPUT_PORTS D0
.venv/bin/python tools/verify_palette_transfer_trace.py
```

BANKS는 검증용 상태 스냅샷으로 bank0/1 각8192바이트를 연결한다. 포트 파일은 size byte/address BE32/value BE32의9바이트 실행 기록이다. 실제 게임 리소스는 기존 MS5P 바이너리를 계속 사용한다. 이 추가 API는 변환 이미지나 오디오 파일을 런타임 입력으로 사용하지 않는다.

원본 명령 수준의 long/word 쓰기 순서를 보존하지만 실제16비트 버스의 시간 간격, 화면 스캔, 전체CPU 레지스터와CCR은 아직 재현하지 않는다. 후속c8c의 포트 쓰기에 영향을 주는D0를 연결하기 위한 API다.

## 검증 결과

원본680조건의 전체64KiB RAM, 두8192바이트bank, 표시bank, 전체D0와190,792개 순서 있는 포트 기록이 일치했다.256개 개별dirty블록, pending/혼합/전체/빈 조합,36개 독립 패턴 채우기와 이어지는 일반 전송을 포함한다.14개 잘못된 크기/counter/별칭 조건에서 출력을 보존했다. 원본 ROM은 변경하지 않았다.

보고서: `artifacts/palette_transfer_trace/verification.json`, SHA256 `54adcdc1bc20abc8203bff065516a4ea869b33915e99a2838ca5bf6c535794be`.
