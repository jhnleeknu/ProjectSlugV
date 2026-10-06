# 문자열 측정과 공통 해석 리뷰

기준303f059이후. 메인이38e8과기존386e해석을대조하고 gpt-6.1-sol medium에공통해석기/측정API/CLI구현을위임했다. 메인이diff검토·원본388조건·기존trace회귀를수행했다.

- 기존제어명령규칙과bytecarry손실,wordwrap을유지했다. 측정은글꼴에무관하게nonzero반환byte를세며trace지원범위는확대하지않았다.
- count는uint16로wrap한다. style/line/consumed를성공시에만교체한다.
- CLI는MS5D로더를사용하며주소/숫자범위를검사한다. 홀수문자열주소를허용한다.
- 원본388조건및거부7조건통과. make all test와출력보존/count폭unit검사통과.
- 기존경고문560개포트쓰기및ASCII127조건회귀가원본과일치했다.
- 메뉴크기계산기반이며메뉴초기화·표시완료를의미하지않는다.
