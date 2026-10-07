# 메인 준비 대기와 실제 IRQ 소비 연결 리뷰

Baseline `e1c4ceb`. 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 기존 C++ 준비/IRQ API를 공유 RAM으로 연결했으며 런타임 코드 수정 없이 소비자가 대기를 해제하는 것을 검증했다.

## 구성과 검토

메인이 sound byte/word 큐와 sprite의 이전 준비 구간·새 정렬 구간의 관계를 검토했다. 초기 fixture 이후 sound head와 sprite read cursor는 IRQ 서비스만 변경한다. 준비 대기 중에도 main pending과 전체 D1/D3를 보존하고, 실제 CLI 반환 RAM을 다음 서비스에 전달한다. 서브에이전트에 C++ 통합 검사와 원본 비교 harness를 분담하고 메인이 코드와 결과를 검토했다.

C++ 검사는 sound busy의 무진행, 반복 byte 소비 후 재개, command3 우선 전송, 이전 sprite 소비 후 반대 방향의 새 준비, 다음 IRQ의 새 sprite 소비와 팔레트 전송을 확인한다. 잘못된 팔레트 상태에서는 RAM/bank/display/result/ports와 main pending이 보존된다. Makefile은 새 검사를 test의 직접 의존성과 실행 목록에 포함한다.

원본 harness는 실제 MS5P 및 단일/다중 블록 MS5C를 사용한다. PVC 쓰기에 따라 원본 bank window를 바꾸며 두 palette bank와 모든 순서 있는 MMIO를 비교한다. IRQ는 c8c에서 실행하고 main의 저장 context로 돌아간다. IRQ가 완료되기 전 main을 재개하지 않는다. main의 전체 RAM/D1/D3/pending 및 palette bank/display를 C++와 비교한다.

첫 80시퀀스 통과 뒤 메인이 IRQ timer16의 실제 word 명령 추가를 요구했다. 추가한 2시퀀스는 timer가0이 되고 RAM4d84=19c0, word tail2→4가 되는 것을 확인한다. main은 그 새 명령까지 소비한다. 이전 검증의 호스트 tail 수정과 달리 이 추가는 원본 IRQ 생산 경로에서 발생한다.

## 최종 검증

`make -j3 all test`: session30397 exit0. Python73개와 C++ 전체 검사 통과, 경고 없음. 로그 `artifacts/main_prelude_irq_build_test.log`.

`.venv/bin/python tools/verify_main_prelude_irq.py`: 최종 session74127 exit0. 82시퀀스, main292경계(sound대기82/sprite대기128/ec4완료82), 완료 IRQ187회 통과. main 포트58,248개와 IRQ 포트66,636개, 총124,884개가 일치한다. main 영상 읽기82회와 IRQ sound status 읽기187회도 일치한다. IRQ에 의한 sound head 진행41회, sprite read 진행146회, palette bank 변경82회다.

보고서 `artifacts/main_prelude_irq/verification.json` SHA256 `6d930aea7824a4dc5ba7bebc5b1a451c903da8aadaaf9fe3584c5b83ca054ad4`. 메인이 최종 집계와 해시를 확인했다. 이 harness에 별도 CLI 오류 조건 수를 주장하지 않으며, 실패 보존은 C++ 검사와 기존 준비 검증에 있다.

## 한계와 다음 단계

IRQ 진입의 scratch register는 명시적인 fixture이며 main CPU context의 보존·복원은 호스트가 수행한다. task queue는 비어 있다. 자연 발생 IRQ, BIOS/SR/RTE, 물리 시간 및 IRQ 최종 scratch register 전체를 검증한 것은 아니다. 준비/소비 연결 검증은 전체 게임 실행 완료를 의미하지 않는다.

다음 e4a 초기화의 직접 호출과 e7b58의 고정 팔레트 등록17레코드를 `docs/analysis/main-startup.md`에 기록했다. sourceffff는 비활성 슬롯 표시이므로 팔레트 데이터로 추출하지 않아야 한다. 이 초기화는 아직 구현하지 않았다.
