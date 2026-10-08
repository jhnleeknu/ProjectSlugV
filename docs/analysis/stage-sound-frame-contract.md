# Stage sound frame 복원 계약 초안

원본 canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 CPU 주소는 고정 ROM의 같은 파일 오프셋이다. 재확인한 원본 목록은 `artifacts/sound_frame_source.json`에 저장했다. 이 문서는 정적 해석이며 구현/동적 검증 완료가 아니다.

## 0x2efa6

D1 하위 byte에 RAM `0x10d491`의 이전 값을 읽는다. RAM `0x10d490`이 비영이면 D0 하위 byte를 ff, 아니면 00으로 만들고 이를 d491에 게시한다. 현재가 비영/이전이 0이면 D0 하위 WORD를 1d28로 바꿔 3af8을 호출한다. 현재가 0/이전이 비영이면 같은 명령으로 3c44를 호출한다. 그 외는 반환한다. byte/WORD 갱신은 각 레지스터 상위 비트를 보존한다. 대기가 발생하면 선택된 helper를 재개하며 d490/d491을 다시 읽어 전이를 판정하지 않는다.

## 0x3c44

입력 D0 하위 WORD를 저장한다. A0=104d82, D1 하위 WORD=WORD104d8a로 시작한다. live tail WORD104d8c와 같아질 때까지 A1=A0+signextend(D1.low), D1.low=(D1.low+2)&6을 수행하고 WORD(A1)이 입력 명령과 같으면 0으로 지운다. A1은 마지막으로 검사한 주소다. 각 반복은 live tail을 다시 읽으므로 alias 쓰기가 tail을 바꿀 가능성도 고려해야 한다.

스캔 종료 후 D0 전체를 0x14로 설정해 3ac8을 호출한다. 반환하면 D0 하위 byte를 저장된 WORD의 상위 byte로 바꾸어 다시 3ac8을 호출한다. 반환하면 D0 하위 WORD를 저장한 원래 WORD로 복원하고 3ac8로 tail call한다. 따라서 세 번의 byte 제출 각각 독립적으로 대기할 수 있다. 첫 제출 이후 D0 상위 WORD는 0이다. 대기 상태에는 저장된 WORD, 어느 제출 단계인지, byte helper의 캡처된 레지스터가 필요하다. 스캔을 재실행하거나 입력 WORD를 현재 D0에서 다시 읽으면 안 된다.

## 0x3af8

D0.low가 unsigned 2000 이상이거나 D0.byte가20 미만이면 즉시 반환한다. 통과하면 D1.low=D0.low 후 D1.byte=0으로 만든다. D1.low가0100/0300/0200이면 반환한다.

RAM100012가1이면 D1.low==0에서 반환한다. 그 외에는 RAM10fd82 비영 및10fe80==0일 때만 외부 byte d00046을 읽고 비영이면 반환한다. 이어 RAM10fd8d==0이면 반환한다. 별도 gate로 RAM104d7e 비영이고 D0.low>=1000이면 반환한다. RAM10f001 bit5가 설정되고 D1.low==0이면 반환한다. 외부 읽기는 조건부이며 하드웨어 입력을 명시적으로 제공하는 설계가 필요하다.

A0=104d82, D1.low=WORD104d8a로 스캔한다. live tail과 다르면 A1=A0+signed D1.low를 캡처하고 D1.low=(D1.low+2)&6으로 갱신한다. WORD(A1)==D0.low일 때 다음 인덱스가 live tail과 다르면 다음 WORD를 A1로 복사하고 D0.low를 다음 WORD에 쓰며 반환한다. 같으면 쓰기 없이 반환한다. 불일치면 스캔을 계속한다.

tail 도달 시 WORD(A0+signed D1.low)=D0.low, D1.low=(D1.low+2)&6, tail=D1.low 순서로 게시한다. 새 인덱스가 live head와 다르면 반환한다. 같으면 A0+=signed D1.low, D1.low=(D1.low+2)&6, head=D1.low 순서로 실행한다. WORD(A0)==0이면 반환한다. 아니면 D0.byte=BYTE(A0) 후 A0++, 다음 BYTE(A0)를 저장한 후 A0++하고 3ac8을 호출한다. 반환 후 저장된 byte를 D0.byte에 복원하고 3ac8로 tail call한다. A0/A1 효과와 두 제출의 대기 상태를 보존해야 한다.

## 구현·검증 시 남은 판단

기존 sound_word API는 D0/D1 중심의 제한된 계약이다. 전체 frame에서는 byte helper와 일관된 전체 레지스터 계약을 별도로 연결해야 한다. 명령 스캔은 잘못된 tail로 무한 반복할 수 있으므로 안전한 중단과 정상 완료를 구분하고, 임의의 4회 제한으로 정상 결과를 만들지 않는다. signed 인덱스의 실제 RAM 접근, WORD 정렬, live alias, 중간 오류의 transaction을 검토한다.

동적 비교는 gate별 원본 분기, 큐 중복/이동/overflow/zero, 세 제출 단계 각각의 대기·재개, 외부 head 변경, 전체 RAM 및 레지스터를 포함해야 한다. 2efa6의 d491 게시가 helper 대기보다 먼저 일어나는지도 검증한다. 전체480bc와 자연 scheduler 연결, 직접 플레이는 이후이며 이 문서만으로 완료로 취급하지 않는다.
