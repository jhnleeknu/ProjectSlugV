# 두뱅크 전송 API 리뷰

기준cbfb3d0 이후. 메인이앞선원본채우기사양을제공하고 gpt-6.1-sol medium이API/CLI를구현했다. 메인이diff,원본양쪽경로비교와회귀검사를수행했다.

- 정상counter0은기존일반전송API로위임하고bank1은보존한다.
- 원본설정함수의counter2000만특수채우기로실행한다. 다른counter는임의clamp없이오류다.
- 특수채우기는bank0,pending,staging을보존한다. pattern반복뒤bank1첫word를0으로만든다.
- 32채우기 및32후속일반전송의전체RAM/두bank/최종선택이원본과일치했다.
- make all test 통과. vectoralias,비정상counter와출력보존검사추가.
- setup8b64의리소스주소연결과실제장치타이밍은남아있다.
