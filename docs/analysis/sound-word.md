# 사운드 word 명령 큐

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU 주소와 ROM 오프셋이 같다. 생산자는3af8..3c08, 배출은3c08..3c42이며 byte 생산자는3ac8이다.

## 큐와 필터

RAM4d82의 네 big-endian word 슬롯을 사용한다. head4d8a와 tail4d8c는 바이트 인덱스0/2/4/6이다. 일반적으로 세 항목까지 보유하고, 네 번째 추가는 가장 오래된 항목을 byte 큐로 배출한다.

3af8은 unsigned word가2000 이상이거나 하위 byte가20 미만이면 무시한다. 상위 byte가01/02/03인 명령도 무시한다. RAM0012가1이면 상위 byte0, 또는 fd82!=0/fe80==0/외부d00046!=0의 조합, 또는 fd8d==0을 추가로 거른다. RAM4d7e가0이 아니면1000 이상을 거르고, f001.bit5가 켜져 있으면 상위 byte0을 거른다. API의 external_status는 조건부d00046 byte 입력값이며 실제 장치 구현은 아니다.

head에서 tail 직전까지 검색하다 같은 명령을 찾으면 바로 다음 항목과 한 번만 교환한다. 이미 마지막이면 아무것도 바꾸지 않는다. 없으면 tail에 쓴 뒤 tail을 `(tail+2)&6`으로 갱신한다. 새 tail이 head와 같아졌다면 head도2씩 전진시키고, 오래된 word가0이 아닌 경우 상위 byte 다음 하위 byte 순서로3ac8에 전달한다. head/tail 갱신은 byte 대기보다 먼저 일어난다.

## 배출과 재개

3c08은 처음 head를 로컬 cursor에 잡는다. 매 반복에서 live tail과 비교하며, word0은 건너뛴다. 나머지는 상위/하위 byte를 전달한 뒤 cursor를 전진시킨다. 실제 RAM head는 배출이 끝났을 때 한 번 저장한다. 대기 중 읽기 위치와 하위 byte는 원본 스택에 보관되어 있으므로 live head나 word 내용을 다시 읽어 복원하면 안 된다.

`SoundWordPending`은 kind(0완료/1생산 중 넘침/2배출), phase(0완료/1상위 byte 대기/2하위 byte 대기), low, cursor와 기존 SoundBytePending을 보관한다. 생산 kind1의 cursor는0이고 배출의 cursor는 원본 스택에 보관된 인덱스다. 완료 시 모든 필드는0이다. 재개는 byte 생산자의 캡처 상태부터 이어가고, 상위 byte가 완료되면 저장했던 하위 byte를 새로 전달한다. 각 byte는 명령3 우선 플래그 규칙도 그대로 적용한다.

API 실패는 해당 호출의 RAM과 pending 변경을 모두 취소한다. 지원 RAM 크기는64KiB이며 사용되는 word 인덱스는0/2/4/6이다. 필터로 거른 생산은 인덱스를 사용하지 않는다. 배출 재개는 live head를 다시 읽지 않고, byte 대기를 벗어나 반복으로 돌아올 때 live tail을 검사한다. 이 오류 처리 계약은 잘못된 인덱스로 원본이 읽는 큐 밖 메모리를 재현한다는 뜻은 아니다.

```sh
build/sound_word enqueue INPUT_RAM OUTPUT_RAM COMMAND EXTERNAL_BYTE
build/sound_word drain INPUT_RAM OUTPUT_RAM
build/sound_word resume INPUT_RAM OUTPUT_RAM KIND PHASE LOW CURSOR BYTE_COMMAND BYTE_TAIL BYTE_NEXT
```

기존 command 중심 API는 CPU 레지스터를 반환하지 않는다. 아래 신규 API는 full D0/D1만 추가로 반환한다. CPU 스택 전체의 메모리 표현과 그 밖의 registers/CCR, 자연적인 인터럽트 재진입, Z80와 오디오 시간축은 구현 범위 밖이다. pending은 원본의 제어 상태를 표현하며 실제 장치 스케줄링은 별도 연결이 필요하다.

## 기존 RAM/pending 검증 결과

원본2,241조건의 전체64KiB RAM과 pending 모든 필드가 일치했다. 필터 조합2,048개, 원형 큐의 중복/추가/넘침과0건너뛰기, 명령3의 우선 처리, 실제 CPU 문맥/스택을 보존한 재개22회를 포함한다. 조건부 외부 읽기64회도 정확한 분기 조건으로 확인했다.25개 실패/파일 별칭 조건에서 출력을 보존했다. `make all test`의 Python73개와 C++ 전체가 통과했다.

보고서: `artifacts/sound_word/verification.json`, SHA256 `cd7e92af61c905924a06d6500e77d04464c59c707ff306bc1aac46cd1a88a59a`.


## Full D0/D1 producer와 재개 API

`engine/include/ms5/sound_word.h`와 `engine/src/sound_word.cpp`는 기존 큐 알고리즘을 공유하는 `enqueue_sound_word_registers(ram,d0,d1,external_status,pending,external_reads,error)`와 `resume_sound_word_registers(ram,d0,d1,pending,error)`를 추가한다. 생산 command는 입력 D0.lowword다. 지원 RAM은 정확히64KiB이며 D0/D1은32비트 입력·출력이다. D3나 다른 CPU register는 이 primitive API에서 다루지 않는다.

원본3af8의 첫 unsigned word/lowbyte 필터에서 반환하면 D0/D1 모두 보존한다. 그 다음 high-byte mask를 D1.lowword에 넣는 경로는 D1 상위16비트를 보존한다. 큐 검색 cursor·추가 tail·넘침 head 갱신도 word 연산으로 D1.lowword에 반영한다. 따라서 무시된 command가 항상 같은 D1을 반환하는 것은 아니며 실제 반환 지점에 따라 달라진다. 중복 항목 교환과 정상 추가는 D0 전체를 보존한다.

넘침으로 oldest word를 byte 큐에 전달할 때 D0.lowbyte만 상위/하위 command로 바뀌고 D0의 나머지24비트는 보존한다. 일반 byte 생산자는 계산한 next index를 D1.lowword에 남기며 상위16비트를 보존한다. Command3의 우선 처리 경로는 그 D1 갱신을 하지 않는다. 최종 또는 대기 register 결과는 같은 RAM/pending 알고리즘의 각 명령 폭을 따라 publish한다.

신규 resume는 overflow kind1만 받는다. Kind2 drain의 full register 재개는 지원하지 않으며 기존 RAM/pending API로만 가능하다. Captured pending은 phase1/2, waiting=true, cursor0이어야 하고 phase2의 command는 저장한 low와 같아야 한다. 입력 D0.lowbyte는 captured byte command와, D1.lowword는 captured next index와 일치해야 한다. 재개는 저장한 high/low byte 상태부터 이어가므로 live RAM oldest word를 다시 읽지 않는다. 완료 시 pending 전체는 기본0 상태가 된다.

생산은 조건부 외부 byte d00046 read 수0/1을 반환한다. 신규 resume는 외부 status를 다시 읽지 않으며 CLI의 external_reads는0이다. 오류는 RAM·D0/D1·pending 및 생산의 external_reads를 호출 전 값으로 보존한다. 유효하지 않은 큐 index·captured register/state 조합을 원본의 잘못된 메모리 접근으로 실행하지 않고 API error로 거부한다.

```text
build/step_sound_word_registers enqueue INPUT_RAM OUTPUT_RAM D0 D1 EXTERNAL
build/step_sound_word_registers resume INPUT_RAM OUTPUT_RAM D0 D1 KIND PHASE LOW CURSOR COMMAND TAIL NEXT
```

정수 입력은 unsigned decimal 또는0x-prefixed hex를 받으며 음수·overflow·trailing text를 거부한다. CLI는 exact RAM 크기와 canonical path/inode alias를 확인하고 API 성공 후 output RAM을 저장한다. JSON은 full `d0/d1`, `external_reads`, `pending`의 kind/phase/low/cursor/waiting/command/tail/next를 반환한다. 다음 재개는 실제 output RAM과 JSON registers/pending을 승계한다. 새 drain CLI나 MMIO port output은 추가하지 않는다.

## 신규 full register 검증 결과

`artifacts/sound_word_registers/verification.json`의 SHA256은 `abc5c9deeec4e3bcc761389c2bdd1406fa8516fdf918a2ef867502bb188ec798`이며 최종 session90516은 exit0이었다. 원본3af8과 실제3aea continuation을 수정 없이 실행해2,525 native case의 전체 RAM/full D0/D1/pending을 비교했다. 조건부 external read64회, producer MMIO write0이며34 negative case에서 output을 보존했다. Binary SHA256 `be6cec06181582ab5440a45f68ac300acc9767d7cfc8d2a7d7cc0deb4a3e0ade`와 원본 fixed1MiB는 시작·끝에 같았다.

실제 CLI RAM/registers/pending carry28개 중24개는 host가 byte head를 명시적으로 바꾸어 대기를 해제하고 live tail53, word indicesffff, 이전 slot aabb 변경을 사용해 captured 상태와 live 읽기 구분을 검증했다. 추가4개는 high wait→low wait→RTS의 phase1/2/0을 승계했다. 원본 CPU context/stack을 보존했고 high wait A7=STACK-6, low wait A7=STACK, RTS A7=STACK+4 endpoint도 확인했다. Native D3 보존은 관측했지만 API에서 노출하지 않으므로 C++ 반환값으로 주장하지 않는다. CPU flags·다른 registers·자연 IRQ/concurrency·audio hardware timing은 범위 밖이다.

기존 RAM/pending verifier도 session57874 exit0으로2,241 case/25 negative와 기존 report SHA `cd7e92af61c905924a06d6500e77d04464c59c707ff306bc1aac46cd1a88a59a`를 유지했다. Full register 추가와 기존 command API 회귀를 구분한다. Stage47a1c의 여러 생산 호출과 caller 중간 상태 연결은 `stage-sound-initialization.md`에서 별도로 기록한다.
