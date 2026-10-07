# 난수 초기화와 상태 진행

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 ROM CPU 주소와 파일 오프셋이 같다. 메인이49a1a..49a8c를 직접 해석했다. c574의MOVEQ0 및c576의JSR49a1a는 실제 호출 근거지만 자연 부팅의 실행 관측은 아니다.

## 원본 연산

49a1a는55개 word를 RAMd6b4..d720에 생성하고 CPU포인터10d720을 RAMd722에 저장한다. D0.low가0이면 RAMf02c를 그대로 둔다. 비영이면 RAMf02c.word를1 증가시킨 하위word를 D0.low에 넣는다. 따라서 호출 D0.low의 비영 값 자체를 seed로 쓰지 않는다. D1.low를 D0.low로 바꾼 뒤 다음을55회 수행한다.

1. D1.low에7925와D0.low를 더하고16비트로 제한한다.
2. 그 unsigned word를 제곱하여32비트 D1에 넣고8비트 오른쪽으로 민다.
3. D0와D1 전체32비트를 교환한 뒤 D0.low를 다음 버퍼word에 쓴다.

49a58은 현재 cursor의word를 D0.low에 읽어 기존 상위word를 보존한다. cursor를 한word 진행하고55word 원형 버퍼로 감싼다. 진행한 cursor에서23word 뒤의 위치에도 같은 감싸기를 적용하고 그word에서 반환할word를16비트 뺄셈한다. 반환값은 변경 전 cursor에서 읽은 값이다.

49a84는 진입 D0.low를 배율로 보관하고49a58을 실행한다. 얻은 unsigned word와 배율을 곱한32비트 결과에SWAP을 적용한다. 최종 lowword는 product>>16이고 highword는 product의 하위word다. 전체 D0를 단순 범위 제한 결과로 치환하면 상위word가 원본과 달라진다.

## C++ 계약

random_state의 seed_random/next_random/scale_random은64KiB RAM과 전체 레지스터를 받는다. seed는D0/D1을 반환하고 next/scale은D0만 변경한다. next/scale은 cursor가10d6b4..10d720 범위의 짝수 주소인지 검사한다. 입력 오류 시 RAM과 레지스터를 보존한다. A5/다른 scratch register/CCR 및 시간축은 이 API의 반환 계약이 아니다.

CLI는 `build/step_random seed|next|scale D0 D1 INPUT_RAM OUTPUT_RAM`이며 결과 JSON은 d0/d1이다. next/scale에서는 입력D1을 그대로 반환한다. 모든 계산은 명시적인 unsigned 비트폭으로 구현한다. 런타임 난수 상태는 RAM이며 별도 이미지나 오디오 리소스를 사용하지 않는다.

## 검증

`.venv/bin/python tools/verify_random_state.py`는 원본1,690호출(seed110/next460/scale1120)의 전체 RAM과 전체D0/D1 일치를 확인했다. 모든55 cursor 위치, seed counter wrap, oldword 경계와 scale limit0/1/ffff를 포함한다. 실제 CLI RAM/D0/D1을 승계하는480호출(next240/scale240)과 별도의 고정 limitffff 220호출을 실행했다. 후자는 lowlimit만 호스트가 공급하고 RAM/D1/D0.high는 실제 반환을 전달하며, 네 바퀴를 돌고220회 모두 비영 결과였다. 입력 오류26조건의 출력 보존도 통과했다.

보고서 SHA256 `886e457b96b4ea5c9655c432d208eeca198e840a42c29a6a119d92d6c57308ff`. 원본 코드 불변과 MMIO 쓰기 없음도 확인했다. 난수의 통계 품질이나 모든 자연 호출 경로를 검증한 것은 아니다. c56e 이후의 초기화·게임 로직 연결은 남아 있다.
