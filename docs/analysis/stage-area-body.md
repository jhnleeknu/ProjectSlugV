# Stage area body의 명령 근거와 다음 경계

## 원본과 재현 가능한 목록

Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 명령/고정 데이터 CPU 주소는 첫1MiB의 고정 ROM이며 파일 오프셋과 같다. RAM/MMIO와 banked 주소는 분리한다. 주소·상수는16진수이고 바이트·명령·호출 개수는10진수다.

`.venv/bin/python tools/inventory_stage_area_body.py`는 `artifacts/stage_area_body/report.json`과 `inventory.asm`을 만든다. Caller 창은479d0..47af0이며 end exclusive다. 직접 호출21개·unique15대상에 대한 bounded 후보와49c20을 포함한16개 callee 창을 보존한다. 전체558행은 후보 명령과 undecoded word의 합계이며 실행이나 분석 완료 수치가 아니다.4e666..4e68e는 명시40-byte 창이고 다른 callee는 명시128-byte 창이다. 첫RTS 이후도 남기고 지정 끝을 넘어가는 decode는 `dc.w`로 기록한다.

보고서 SHA256은 `a3996a4d2d3afefcd0a366b167160544bd8ac4d8193eff697aeb6d5f5e5f0f11`, ASM SHA256은 `b69c4e7ecaa21bb7acf70f5a86fc38fb078eb4b5ebfd81c8129385ca75ce053d`다. Reports의 engine/docs address text 참조는 기존 API 재사용 후보일 뿐 같은 RAM 효과·레지스터 계약을 확인한 결과가 아니다. 겹치는 callee 창은 의도적인 bounded 목록이며 코드/데이터 경계나 함수 소유권을 자동 확정하지 않는다.

## Caller 직접 호출 목록

479d0..47af0 안의 직접 대상은47594,4e666,48180,475ca,d760a,49c32,3af8,3d58,4814e,3d44,3c84,1a5a4,e8a1c,48398,e905c다. 정확한 callsite/raw bytes와 branch target은 보고서 및 ASM에 있다. 각128-byte callee 창에 보이는 추가 call/ROM operand도 후보로 기록하지만 재귀 분석 완료나 자연 reachability를 주장하지 않는다.

원본479d0은 object+7d.byte에 따라 분기한다. 앞서 구현된479ee의 두 player snapshot→475ca reset 경로와 다른47594 준비 경로가 이후479fe에서 합류한다. 기존 준비/캡처 대응은 [stage-preparation.md](stage-preparation.md)와 [player-record-capture.md](player-record-capture.md)에 있으며 이 목록의 새로운 동등성 결과와 합치지 않는다.47594의 독립 검증 보고서는 추후 확정 시 별도로 반영한다.

## 메인이 확정한4e666 selector 동작

A5=108000 문맥에서4e666은 RAM10dd2a, 이어10dd2b selector를 처리한다. 각 selector의 bit7가 켜져 있으면 branch로 건너뛴다. Bit7가 꺼져 있으면4e4d2를 base로 **signed D0.word** index에 있는 byte를 읽어 RAM10dd1e의 해당 bit를 BCLR.B하고 selector를ff로 만든다. 메모리 byte bit index는mod8 동작이다.

4e672/4e676/4e680의 D0 조작은 byte다. 따라서 bits8..15를 비롯한 상위24bit를 무조건 지우지 않는다. Low selector byte만으로 항상4e4d2..4e552 안을 읽는다고 일반화하지 않는다. 실제 앞선47594 suffix는 D0 전체0을 반환한다는 메인 계약과 별도로, standalone helper의 일반 register 입력은 구분해야 한다.

`4e4d2..4e552` 원시128바이트를 report의 raw_hex와 ASM에 보존했다. SHA256은 `aab36d4692c572b94b43fb395e58d13c8b39e8ed0448a91b8a06e52a919cbf86`다. 이것은 명시적 evidence 창이며 논리128-entry table의 전체 의미나 모든 signed index 안전성을 입증하지 않는다. 현재는 별도 MS5D 리소스나 C++ lookup 계약이 완료됐다고 주장하지 않는다.

## d760a와49c20/49c32의 명령 사실

메인이 확인한 d760a 첫 entry는 RAM10ddec.word=1, +2.word=0108, +4.word=01a0을 쓴다. 두 번째 entry RAM10ddf2.word=0, +2=0108, +4=01a0이며 RAM10ddf8.word=0096을 기록한다. D0는 MOVE.W0으로 lowword만 지워 highword를 보존하고 A0=d764a로28ae 할당을 호출한다. 같은128-byte 창에서d764a 이후 명령이 보이지만 이 callback body 실행 완료를 목록만으로 주장하지 않는다.

49c20은 ANDI.W1/LSL.W2로 D0.lowword를 계산하고 RAM10d734를 기준으로 indexed long 저장을 한다. Byte 계산으로 대체하지 않는다.49c32는 A0=0을 설정하고49c20으로 BRA한다.479fe→47a1c의 두 helper 호출에서는 마지막 MOVEQ1 뒤49c32를 호출하므로 원본 경계의 D0 전체는4라는 메인 확인을 기록한다. 다른 레지스터·CCR 효과는 이 명령 목록만으로 일반 계약을 확정하지 않는다.

## 미확정 후속 범위

47a1c 이후는 레코드word10과 RAM10d686의 비교 및 사운드 선택으로 이어진다.47a94에서는 record+2의 scene script 포인터를1a5a4에 전달하며 nonzero 경로는 미완료다. 현재 null-script 초기화 계약을 이 일반 scene script에 그대로 적용하지 않는다. e8a1c/48398/e905c 등의 전체 nested behavior와 register/port 계약은 메인의 추가 제어 흐름·자료구조 해석 대상이다.

이 문서의 완료 범위는 source 불변 확인, 지정 전체 decode 창, 원시 주소/호출 관계·lookup evidence와 메인의 위 정적 확인이다. Native47594 결과나 전체479d0 body 구현·자연 scheduler·스테이지 gameplay 동등성은 아직 확정하지 않는다.
