# 팔레트 전송 wrapper 리뷰

기준c0e8ce8 이후. 메인이72fa 일반경로의gate, slot0 mask와장치선택을해석했다. gpt-6.1-sol medium이API/CLI를구현했고메인이diff와원본연속검증을검토했다.

- pending은bit7만지우며없을때staging을변경하지않는다.
- slot0 첫word의별도AND8000을기존upload커널앞에적용한다.
- 최종display bank는7dec byte의zero/nonzero다.
-54회전송과24회연속효과프레임 RAM/palette/bank비교통과. make all test통과.
- 특수채우기·bank1내용·IRQ/장치타이밍은미완료다. 출력은일반경로만지원한다고명시한다.
