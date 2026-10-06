# 메뉴 초기화 리뷰

기준eebdbd5이후. 메인이a29c/a0a0의첫할당경로를해석하고 gpt-6.1-sol medium에확정된API/CLI를위임했다. 메인이소스·원본378조건·오류보존·전체회귀를검토했다.

- MS5D/descriptor/공통문자측정을재사용한다. 모든측정/범위검사후RAM에쓴다.
- 크기비교는원본byte폭이고최대문자수는word폭이다. 슬롯+5와current pointer는보존한다.
- 문자의style/line이각문자열로이어지는동작도일치했다.
- 실제메뉴16조건과합성362조건의전체RAM이원본과일치했다. make all test 통과.
- API는a29c reset/첫할당이다. 일반중첩push나활성메뉴표시를완료했다고주장하지않는다.
