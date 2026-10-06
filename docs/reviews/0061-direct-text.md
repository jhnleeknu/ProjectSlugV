# 기본 문자 포트 출력 리뷰

기준3f5733a이후. 메인이3650/3918과메뉴기본문자callback을확인하고 gpt-6.1-sol medium에API/CLI구현을위임했다. 메인이코드리뷰,원본비교와검사수정을수행했다.

- glyph별long쓰기다음word8200 reset을보존한다. 공통VideoPortWrite는주소/값/폭을모두표현한다.
- 타일번호는원본byte/word shift에맞춰계산하며font/page상위의불필요한bit는버린다. 공통제어해석과MS5D를재사용한다.
- 원본291스트림,65,280glyph/style조합일치. 초기검증에서Unicorn의sign-extended word callback을확인해실제bus폭으로마스크했다. C++동작을잘못변경하지않았다.
- make all test 통과. 불완전스트림/상한오류에서출력보존을검사했다.
- 원본메뉴전체배치·가림·callback·픽셀비교완료로확대해석하지않는다.
