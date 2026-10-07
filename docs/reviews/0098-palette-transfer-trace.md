# 팔레트 전송 D0와 포트 순서 리뷰

대상 기준 커밋: `f917c57`.

메인이72fa와873a의 명령 및 기존 최종상태 구현을 확인했다. 기존API를 재사용하여 데이터 변환을 중복 구현하지 않고, 원본dirty marker와 최종palette 상태로 순서 있는long/word/byte 기록과D0를 생성하는 추가API를 작성했다. gpt-6.1-sol / medium에 CLI와 원본 비교를 분리 위임하고 실제 산출물을 검토했다.

일반 pending이0이어도watchdog과최종bank 쓰기를 수행한다. marker가 있는 마지막블록의 첫long이D0가 되며 첫slot 마스크를 적용한 값을 사용한다. 전체채우기는패턴D0를 유지하고 역순long쓰기를 기록하며 최종zero word뒤watchdog 없이bank 선택한다. API는기존지원counter0/2000과동일하고 실패 시 모든 출력보존을 유지한다.

원본680조건의 전체RAM/두bank/D0/표시bank와190,792포트가 일치했다. 검증기는실제bank선택에따라물리palette창을전환하며두논리bank를별도보관한다.36개specialfill의2,048long 내림차순과마지막zero word,watchdog부재를직접assert했다.14개오류/별칭에서기존출력을보존했다. 원본ROM불변확인.

`make all test`: Python73개및C++전체통과. 로그: `artifacts/palette_transfer_trace_build_test.log`. `git diff --check` 통과. 보고서 SHA256: `54adcdc1bc20abc8203bff065516a4ea869b33915e99a2838ca5bf6c535794be`.

이 결과는명령수준포트순서이며실제장치시간축은아니다. 전체CPU레지스터/CCR,나머지스프라이트반환값과작업복구를c8c에연결하는작업이남았다. 전체목표는active다.
