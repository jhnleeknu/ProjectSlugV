# 배경 좌표 준비와 callback 후보 조사 리뷰

Baseline `80514f0`. 메인 에이전트가 원본1879c..187d6/1ae56..1aeb2/e74 호출 순서, C++/CLI/단위 검사 diff와 세 Python 도구를 검토했다.
프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. fixed영역 CPU주소=파일오프셋; 그 이후 inventory의 source는 ROMoffset만 사용한다.

## 의미·구현

1879c는14/18.word에서25.byte의bit0/1을 각각 빼며16비트로 순환한다. LSR.B가 각 SUBX.W의 X를 새로 설정함을 확인했다. cache7c/7e와 다르면 해당word와flag7a.bit7만 수정한다. active bit0과 무관하게 준비하며 D0/D1highword보존, D3=0이다. 1ae56의 네 객체순서와bank1→0/MMIO순서를 구현했다. 단일 API는 모든검사뒤 실패없는변경을 수행하며, scene API는 후보상태로 예외/오류시출력을 보존한다.

## 후보 조사와 판단

main_callback_refs1,101개는 모든 even-start 해석 후보다. A6+76의 여러 사용과 데이터 해석 오탐이 있어callback 실행확정이 아니다. root가 e40의A5상대쓰기가 메인100820의+76/+7a와 일치함을 확인했지만 자연호출은 미관측이다. task_queue_banked_refs는7MiB에서absoluteJSR/JMP0개와rawBE32값8개를 기록했다. 상대분기의 가상매핑과 거리제약을 실제bankmapping과 분리했다. 이를 미사용증명으로 취급하지 않았다. 확실한 e74→1ae56을 다음 구현으로 선택했다.

Inventory SHA256: main `16c26f88be0da9218f9f160c5b455261491d7a6870a5c3848b02f9c42b409e17`; banked task `c8e459517c4a99a27eada7e9e9248e1883bc40e06250e3ba004076cd0dd9dfac`.

## 검증·수정

`make -j3 all test`: session37246 exit0, Python73개/C++전체통과, 경고없음. 로그 `artifacts/column_prepare_build_test.log`.

검증스크립트의 조건별diff생성에서 동일파일을65536번읽는 반복I/O를 메인리뷰로 발견했다. 진행중session31000을명시적중단(exit130)하고 한번읽은RAM/포트를 재사용하도록 고쳤다. 실패진단도 불일치일때만계산한다. 의미/기대값은바꾸지않았다.

수정후 `tools/verify_column_prepare.py` session5402 exit0. 준비1,482조건+refresh연결4조건, 포트1,312개/오류29조건. 전체64KiBRAM/fullD0/D1/D3/포트비교, 모든cache변경조합, flag/selector256byte와word순환,4개CLI승계시퀀스,원본불변통과. refresh연결은dirtybit를소비해4+64×changed-record개포트를내는것을확인한다. 이단계의D1/D3는기존API가반환하지않아비교주장하지않는다.
보고서 SHA256 `1ee49b44a787cf2b279b99252ec8639b9183b2139b37450386bce9a8b38d6069`.

## 남은 범위

e74전체프레임준비순서, sound대기중재개, sprite준비동시성, 자연callback/IRQ작업본문, 실제픽셀/사운드시간축은추가연결과검증이필요하다. 전체목표완료가아니다.
