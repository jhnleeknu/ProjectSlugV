# 전체 게임 초기화 함수 복원 리뷰

Baseline `36e638b`. 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이 원본의 오브젝트·레코드 처리와 suffix 호출 순서를 해석하고, sol에 구현·검증·리소스 추출을 분담했다. 메인이 C++ 코어, CLI, packer, 검증 코드 및 실제 보고서를 검토했다.

## 계약과 판단

`1bcfe`의 초기 포인터 선택은 zero/nonzero지만 `1be84`의 clear 대상은 parity다. selector2에서 서로 다른 구조체를 수정하는 원본 동작을 보존한다. `1bd2e`에서 `1bd90`, `1bcfe`에서 `1bd12`로 이어지는 fallthrough를 모두 구현한다. callback0은 활성이고270e만 비활성이다. 단독1bd12는 live pointer를 읽으며 늦게 발견된 잘못된 포인터도 전체 변경을 롤백한다.

481de는 4d81c의20개16byte 레코드를 사용한다. unsigned D1.low<20 검사가 마스킹보다 먼저며 MULU가 D1 상위word를 지운다. D0/D3 상위word 보존과 byte/word 필드 순서를 확인했다. 원시320byte 전체를 MS5D에 보존하고 C++ 로더로 읽는다. 게임상 의미가 불확실한 필드 이름은 확정하지 않았다.

475a4 suffix를 원본 순서대로 연결하고47570의 기존 사운드 대기 접두부와 통합했다. 반환 D0/D1/D3=0은 개별 helper의 결과를 생략하는 근거로 사용하지 않았다. returned=true가 완료 표시이며 next_pc475a4/phase4는 마지막 내부 경계다. 호출자 PC로 혼동하지 않도록 header와 문서에 명시한다. suffix 실패 시 접두부 변경까지 보존한다.

## 검증

전체 `make -j3 all test` session19295 exit0. Python88개와 전체 C++ 검사 통과, 경고 없음. 로그 `artifacts/game_initialization_build_test.log`. 이후 변경은 Python 검증과 문서이며 C++ 변경은 없다.

- 오브젝트: 원본149조건, 오류24조건. 전체RAM/D0 비교와 원본 D1/D3 보존 관측. 보고서 SHA256 `c239a5619c6e929f2cee2ca6f65ccf93635e6f7f35e61d751bedee361d9b75f9`.
- 레코드: 원본168조건, 오류32조건. 모든20 ID와 selector/상위word 조합, 실제CLI 승계 포함. SHA256 `aa251956b6b4456c5787ab7bfed501160a7a1e72acfcadfaddc9c52d5615cb1b`.
- 전체 초기화: 원본562조건, 오류31조건. suffix256회, whole47570 조합256회, 조건부32회, 승계18회. 전체RAM/D0/D1/D3와 독립 추출 pending 비교, 외부읽기4회, MMIO쓰기0. SHA256 `ba538ea67e01041c8b199c889d8f2a225f18b203bf55e6a281da5464af12a3b2`.

검토 중 다음 상태가 CLI JSON과 동등성을 확인한 native 객체에서 전달되는 점을 발견했다. 동일 값이지만 실제 CLI 승계를 명확하게 보장하도록 parsed CLI JSON을 다음 입력으로 전달하게 수정했다. 최종 verifier session39092 exit0으로562조건/오류31조건을 다시 통과했고 보고서 해시는 동일하다. 원본 코드나 호출을 패치/우회하지 않는다.

## 범위와 다음 작업

전체 함수의4개 대기 승계 시퀀스는 호스트가 RAM4d74.word를 수정해 해제한다. 이전 접두부 IRQ 검증을 전체 함수의 IRQ/스케줄러 검증으로 확대하지 않는다. 기타CPU레지스터·CCR·stack 동등성·자연 호출자·물리시간은 이 검증 범위 밖이다.

다음은 원본 호출자c58a부터 BIOS 경계와 후속 콜백을 연결하는 작업이다. ROM180.word는 canonical 이미지에서0이며 코드 사이c6ce..c6da는 데이터 참조 구간이다. 이를 코드로 자동 확정하지 않는다. 전체 부팅·플레이·전투·모든 스테이지 복원 목표는 진행 중이다.
