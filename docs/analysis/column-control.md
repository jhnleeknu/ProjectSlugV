# 인터럽트의 열 위치 제어 갱신

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU 주소와 ROM 오프셋은 같다. 단일 구조체 갱신은187d8..18be8, 네 구조체 호출자는1adf8..1ae56이다. c8c는 팔레트72fa 이후1adf8, 그 뒤 일반 스프라이트16cfa를 호출한다.

## 구조체와 분기

입력은A0의128바이트 구조체다. +7a.byte의bit0이0이면 아무것도 하지 않는다.1이면bit7을 지우고 이전bit7이0일 때 반환한다. 갱신 요청이 있었어도 +26.word가 음수이면bit7을 지운 상태로 반환한다. 이 세 경로는D0를 보존한다.

그 외에는32개 열에 대해3c0000으로 두 번씩 long 쓰기를 실행한다. +26은 시작 슬롯, +7c와+7e는 두 제어 좌표, +3a..+78의32개word는 열별 보정값이다. 이름은 쓰기 대상에 따른 위치 제어 해석이며 이 함수 자체가 타일 이미지를 읽지는 않는다.

각long의 상위word는 비디오 주소, 하위word는 값이다. 첫 주소는 `(slot+8401)&ffff`, 둘째는 `(slot+8201)&ffff`이며 각 열마다1 증가한다. 첫 값x는 `(word(+7c)<<7)&ffff`, 기본 둘째 값y는 `(word(+7e)<<7)&ffff`다. 열마다x를800씩 word 단위로 증가한다.

각 열의 둘째 값은 unsigned `(x+400)&ffff < a000`인 경우에만 해당 보정word를y에 더한다. 같으면 보정을 적용하지 않는다. x의 랩어라운드 이후 비교 결과가 바뀔 수 있으므로 signed 좌표 비교나 단순 범위 clamp로 바꾸지 않는다. D0.word는기본y로 설정되며 상위word는 보존된다.

## 호출자와 API

`refresh_column_controls`는 한 구조체를 처리한다.64KiB RAM과 정렬된100000..10ff80 주소를 요구하며 오류 시 RAM/D0/포트 목록을 보존한다. 성공 시 포트 목록을 교체한다.

`refresh_scene_columns`는1adf8을 구현한다. RAM0010.word를1로 설정하고2ffff2.word=2000,2ffff0.word=0을 쓴 다음109156/10b1d6/10d256/10d2d6 순서로 호출한다. 마지막에는 RAM0010을0으로 만들고2ffff2=1000/2ffff0=0을 쓴다. 비활성 구조체만 있어도 네 PVC 쓰기는 발생한다. D0는 마지막으로 실제 갱신한 구조체의y를 반영하거나 모두 건너뛰면 입력값을 유지한다.

```sh
build/refresh_column_controls INPUT_RAM OUTPUT_RAM OUTPUT_PORTS OBJECT D0
build/refresh_column_controls --scene INPUT_RAM OUTPUT_RAM OUTPUT_PORTS D0
.venv/bin/python tools/verify_column_control.py
```

포트 파일은 검증용9바이트(size/address/value) 기록이다. 원본long 쓰기를size4로 보관하며 실제16비트 장치 버스의 시간 순서를 구현했다는 뜻은 아니다. 이 함수는 RAM의 원본 word 데이터를 사용하므로 PNG 변환에는 의존하지 않는다.

전체 CPU 레지스터/CCR 출력, 구조체를 채우는 상위 맵·타일 처리와 실제 장치 시간축은 남아 있다. 기존 팔레트/스프라이트 처리와 함께c8c에 연결할 때 각 함수의 레지스터 전달 및 작업 복구를 추가로 검증해야 한다.

## 검증 결과

원본1,441조건(독립1,409개, scene/승계32개)의 전체64KiB RAM, 전체D0와78,272개 순서 있는 포트 기록이 일치했다. 전체256개 flag와각 축512개 유효 좌표, 부호 있는slot, 주소/좌표 순환, A000 비교 경계와 네 구조체의16개 활성 조합을 확인했다.11개 주소/크기/별칭 오류에서 출력 보존을 확인했다. 원본 ROM은 수정하지 않았다.

보고서: `artifacts/column_control/verification.json`, SHA256 `f7a40f0435d4b77bae44a31486bcd2da4c9a3bbed9c03cd58db54ff0c9e754fd`.
