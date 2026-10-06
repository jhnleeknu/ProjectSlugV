# 애니메이션 상태 실행기 리뷰

대상40d5fec 이후. 메인이 확인한사양을 gpt-6.1-sol/medium에 위임해실행기와CLI를 구현했다. 메인은core·fetch범위·CLI 실제코드를검토하고 원본검증·혼합pipeline·실패원자성테스트를작성했다.

- duration 상위byte 덧셈과old timer signed조건, word감소·포인터전환 순서를기존원본모델과대조했다.
- fetch는64bit cursor와차감전조건으로범위를검사한다. script주소는24bit공간에제한한다.
- 원본의기본콜백producer를사용한다. Waiting은재개하지않고오류로롤백하며지원계약에명시한다.
- 올바른draw뒤unsupported opcode로실패해도큐변경이남지않는다. 잘린operand·최대offset·스크립트주소범위·producer Waiting·10000명령한도도검사했다.
- 원본/C++ 대기2000조건, 혼합8시퀀스96호출·192준비/갱신단계에서RAM·carry·비디오출력이일치했다.
- make all test, 추가animation_step_test, git diff --check 통과.

출력파일두개의IO는파일시스템전체transaction이아니다. API RAM/carry원자성과구분한다. 자연ROM script·나머지명령·IRQ/실시간스케줄링은미완료다.
