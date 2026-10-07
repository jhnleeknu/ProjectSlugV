# 인터럽트의 크레딧 요청 처리

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
CPU 고정 주소와 ROM 오프셋이 같다. 대상은bbe..bee와 그 안에서 호출하는a74/a2c/a4e이다. BIOS 호출은 없다.

`process_credit_request`는64KiB RAM과 전체D0를 받아 원본bbe의 RAM/D0 결과를 만든다. 다른 레지스터와 CCR 출력은 현재 API에 포함하지 않는다. 크레딧이라는 이름은 두 바이트의 가용성 확인과 BCD 차감 역할에 따른 해석이다.

fd82가0이 아니면 RAM과D0를 그대로 반환한다.0이면 RAM0014 요청을D0.byte로 읽고, 요청이0이 아니면fdb4에 OR한 뒤a74를 실행한다. 마지막에D0.byte를~fdb4로 바꾸고 RAM0014에 AND하여 처리된 비트를 지운다.

## a74의 도달 가능한 분기

bbe 경로에서는 fd82가 항상0이다. fdaf가1이면 fdb4&f004를 검사한다. 결과가0이 아니면 fdb4를0으로 만들고 fdaf를2로 바꾼다. 이 경우 요청은0014에 남으며 아직 크레딧을 차감하지 않는다. fdaf가1/2 이외이면 fdb4만0으로 만든다.

fdaf가2이면a2c로 fdb4의 하위 요청 두 비트와 RAM0004/0005의 가용성을 처리한다. 각 반복은D0.byte를 우측으로1비트 이동하고, 빠져나간 bit0이1이면서 해당 크레딧이0이 아니면bit1을 세운다. 두 번 반복하므로 원래 요청의 상위 비트도 이동하여 남을 수 있다. 이 결과에f004와f007을 AND하여f006에 OR하고fdb4에 저장한다. 원본에서D1에~f006을 만들지만 이 값을D0 마스크에 사용하지 않는다. 임의로 기존f006 비트를 제외하지 않는다.

a4e는D0.word를 두 번 우측 이동하며 빠져나간bit0에 해당하는 크레딧을 차감한다.0인 크레딧은 차감하지 않는다. SUB.W D6,D6가X를 지운 뒤 SBCD로1을 빼므로 하위 nibble이0이면7을, 아니면1을 빼는 byte 연산으로 RAM 결과를 표현한다. 실제 원본 실행에서 유효·비정상 BCD byte 전체를 비교한다.

## 정수 폭과 연결 계약

a2c는byte 이동이고a4e는word 이동이다. 따라서 호출 당시D0.word의 상위 byte가a4e 이후 달라진다. 마지막bbe의D0.byte 덮어쓰기는 그 위의 바이트를 보존한다. 예를 들어D0=abcdab00, 요청3과 두 크레딧이 유효하고 모든 mask가 허용되면 결과D0=abcd2afc이다. 상태를 bool이나 하위 byte만으로 반환하면 이 차이가 사라진다.

정확히64KiB RAM이 아니면 실패하며 RAM/D0를 보존한다. standalone a74의 fd82!=0 경로는 이 API의 대상이 아니다. 후속c8c의 사운드 호출 전 포트 쓰기에D0가 전달되므로, 이번 구현은 그 레지스터 의존성을 연결하는 기반이다. 전체 IRQ 레지스터 저장·복구와 장치 시간축은 별도 작업이다.

```sh
build/process_credit_request INPUT_RAM OUTPUT_RAM D0
.venv/bin/python tools/verify_credit_request.py
```

원본1,326조건(독립1,294조건+승계32회)의 전체RAM과 전체D0가 일치했다. 모든256개 크레딧 byte와 요청 byte, 모드/마스크/즉시 반환 조건을 비교했고 실제a74/a2c/a4e/SBCD 도달을 확인했다.7개 크기/파일 별칭 오류는 출력을 보존했다. 원본 ROM은 수정하지 않았다.

보고서: `artifacts/credit_request/verification.json`, SHA256 `b18bdf7fa6e789a49e761fddfeb48a127f574e51f7a84f4c08de8d625af5e53b`.
