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

CPU 스택 전체의 메모리 표현과 레지스터/플래그, 자연적인 인터럽트 재진입, Z80와 오디오 시간축은 구현 범위 밖이다. pending은 원본의 제어 상태를 표현하며 실제 장치 스케줄링은 별도 연결이 필요하다.

## 검증 결과

원본2,241조건의 전체64KiB RAM과 pending 모든 필드가 일치했다. 필터 조합2,048개, 원형 큐의 중복/추가/넘침과0건너뛰기, 명령3의 우선 처리, 실제 CPU 문맥/스택을 보존한 재개22회를 포함한다. 조건부 외부 읽기64회도 정확한 분기 조건으로 확인했다.25개 실패/파일 별칭 조건에서 출력을 보존했다. `make all test`의 Python73개와 C++ 전체가 통과했다.

보고서: `artifacts/sound_word/verification.json`, SHA256 `cd7e92af61c905924a06d6500e77d04464c59c707ff306bc1aac46cd1a88a59a`.
