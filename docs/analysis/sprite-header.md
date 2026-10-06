# 합성 리소스 헤더 하위 byte

프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.

이전 단계의 kind2 로더는 header 하위 byte를0으로 제한했다. 실제 bank400000의 group0에는0101과0103 리소스가 있다. ID029802는 ROM408b2c/CPU208b2c, ID070002는 ROM40a1c4/CPU20a1c4이며 둘 다 블록 수는1이다. 원본 포인터를 따라 추출했다. 자연 게임 호출부나 팔레트 연결을 확인한 것은 아니다.

## 해석 근거

고정 ROM/CPU0xced0은 header word를 읽어0100을 뺀 뒤swap한다. 블록 루프 마지막0xd240에서01000000을 빼고 carry로 반복한다. 하위 header byte는 D7의bit16..23에 남는다. 열/행 치수는 low word에서 갱신되고 블록 수는bit24..31에서 감소하므로 보존된 중간 byte가 반복 종료나 출력값에 영향을 주지 않는다. 나머지 방향·반전·준비/갱신 분기에도 같은 패턴이 있다.

0x16c30 및0x16d6a dispatcher는 큐 record+4의ffff 비교와 style low bits로 분기를 선택한다. 리소스 header 하위 byte를 분기 선택에 사용하지 않는다. 이것은 표시 경로에 대한 결론이며 다른 엔진 코드에서 이 byte를 읽는지까지 결론 내린 것은 아니다.

## 검증과 적용

`verify_sprite_header.py`는 원본 프로그램 파일을 변경하지 않고 에뮬레이터 메모리의 header 하위 byte만0..255로 교체한다. ID2152의 단일 블록과 ID2402a의3블록을16개 소비 분기에서 실행한8192조건에서 다음 슬롯과 순서 있는 모든 비디오 쓰기가 기존 모델과 일치했다. 합성 입력 검사와 실제 ROM 리소스 검사는 구분한다.

`verify_sprite_blocks.py --cpp`는 실제0101/0103 두 리소스를 추가하여 여섯 리소스의4320조건을 비교한다. MS5C kind2는 이제 하위 byte를 그대로 보존하고 emitter는 이 값을 출력에 사용하지 않는다. kind1은 기존0100 규격을 유지한다. 로더와 emitter의 단위 테스트도256개 byte 값을 검사한다.

포장 명령은 `tools/pack_composition_blocks.py`, metadata에는 opaque_header_byte가 추가된다. 전용 이미지 변환 없이 같은 C++ 런타임 경로에서 사용한다. 활성/비활성 pool의 연속 생성·준비·갱신 검증에는 여섯 리소스를 모두 포함한다.
