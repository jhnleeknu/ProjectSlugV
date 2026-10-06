# 메뉴 문자 배치 C++ 리뷰

기준e269260이후. 메인이확정한원본288조건사양을gpt-6.1-sol medium 두에이전트에분리위임했다. 한쪽은공통glyph가림,다른쪽은배치/CLI를구현했다. 메인이diff와기존원본oracle통합을검토했다.

- 공통문자해석기와MS5D를재사용한다. 숨김글자는cursor를진행하지않고화살표는진행한다.
- signed byte제목정렬과항목index갱신을원본대로구현한다.
- 확인한event5 no-op만처리하고미지원callback을명시적으로거부한다. 오류시RAM/목록은불변이다.
- 원본288조건전체RAM/포트쓰기일치. glyph가림·미지원flags/callback·height0경계unit검사통과.
- make all test 및기존직접문자291스트림/65,280조합회귀통과.
- 전체메뉴상태전환/다른event/화면픽셀완료를주장하지않는다.
