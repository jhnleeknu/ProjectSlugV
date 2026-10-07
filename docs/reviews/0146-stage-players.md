# 스테이지 플레이어 설정 리뷰

Baseline `5e896cd`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. ROM CPU 주소는 고정 첫1MiB에서 파일offset과 같다. 메인은476dc/47742/479ba와289e/2a48/2a28/1bd2e/49a58의 조합·정수폭·순서를 해석했다. 구현·추출·검증·문서는 sol에 분담하고 실제 변경을 메인이 검토했다.

## 선택과 원본 폭

47742는D0.word=0이면100cb8, 그 외는100da8을 선택한다. D1.word의 부호가 음수이면2a48의 static 제거를 수행한다. 비음수는 inactive callback270e일 때만2a28로1d1f4를 설치하고 저장했던D0.word를 object78에 넣은 뒤1bd2e로 초기화한다. callback0도 active여서 이 준비를 건너뛴다. 선택값D1.word는stack에서D0.word로 복원하므로 D1 자체를 원래 값으로 되돌리지 않는다. 선택값4이상은 unsigned 비교 후49a58 난수lowword&3을 사용한다. 활성 경로의D0.high는 남지만 재시작 경로에서는 helper가D0를전체0으로 만든다.

1bd2e의 기존 first/second 구현을 공용 API로 노출했다. selector!=0에 따른 record 선택과 selector&1에 따른 다른 필드 선택을 통합하거나 정규화하지 않았다. 기존reset_game_objects 동작은 변경하지 않았다. 음수제거 경로의 A6는 내부target을 가리키더라도 원래 caller 값을 돌려준다.

## 리소스와 두 gate

476dc는 stage6..8에 따라476bc/476c4/476cc를 선택하고 다른stage는첫pointer로 돌린다. area byte×4에서 두word를 순서대로 읽는다. 고정1009a8/100a6c 각각이inactive일 때만 해당player helper를 호출한다. 두 번째D1.word를 읽을 때 첫helper에서 반환된D1.high를 유지한다.

MS5D v1 kind1 `[476bc,47acc)`의1040바이트는 모든8bit area의 주소가능 창이다. 다섯선두pair와 세pointer 뒤의 원본명령도 포함한다. 전체를 논리테이블 또는256개 실제사용area로 간주하지 않는다. stage6 areas0/1, stage7 areas0/1, stage8 area0만 서로 분리된 다섯선두pair이며 다른조합에는 다른table/pointer/code 겹침이 있다. container1072바이트 SHA256 `9248616256431f9e81b27ab938bf2d6cc8e108006b7f032929babfa8c1c604e9`.

479ba caller는먼저RAMd681=ff를 쓰고D0.byte=RAMd684&3으로 바꾼다.0이면helper를 건너뛰며 미사용A6/table 검증도API에서는 하지 않는다. 비영이면476dc를 호출하고479d0직전에끝난다. A6+7d가d681에겹치는 경우ff쓰기후area조회순서를보존한다. 오류는첫player의재시작까지포함해RAM/레지스터/포트전체를rollback한다. CLI는모든경로에서MS5D파일을로드한다.

## 리뷰와 검증

메인은core/CLI/unit/Makefile및추출기를검토했다. 전체make는Python111/C++93통과,경고0이다. 공용game_objects 원본회귀149조건/오류24조건도통과했고 보고서SHA256 `c239a5619c6e929f2cee2ca6f65ccf93635e6f7f35e61d751bedee361d9b75f9`다.

메인은독립verifier의context_restore 이후SR/stack등을다시초기화하던코드가 '같은native context연속실행' 주장에맞지않음을지적했다. 연결검증에서는초기화를생략하고필요한A5/A7만assert하도록수정시켰다. 또area0..4전체를canonical pair라고부른label을선두5pair와overlap controlled fixture로구분하도록수정시켰다. 수정후최종session5270은1899원본조건/42오류조건/380포트/6CLI RNG승계와실제stage preparation→caller연결2조건을통과했다. 전체64KiBRAM/D0/D1/D3/A6와A7종료위치를비교했고ROM과실행파일은불변이었다. 최종보고서SHA256 `7d82d2427746eff1edea0e1f3659807d1f84db2e6a6327210dae4ef4e7235e77`. 선두5pair실행80조건과overlap실행160조건을분리했다. 모든stage256조건및area256×3조건은gate로helper를막아원본읽기주소를독립검증한다. RNG승계는후속D1.word=4를host가명시적으로요청한다.

## 남은 범위

479d0이후area별레코드복원,일반scene script,player callback1d1f4의전체게임플레이와자연scheduler는남아있다. 부팅부터플레이어조작가능한전체게임으로완료를확대하지않는다.
