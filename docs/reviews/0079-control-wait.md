# 활성 대기와 반복 입력 리뷰

대상:`5c6f9ca` 이후 변경.

메인은91c2..92ce의 분기순서·byte연산·표시조건을 원본에서 해석하고 C++대기실행기 및 오류/경계 단위검사를 구현했다. 확정된 MS5D팩커/CLI/원본반복비교는 gpt-6.1-sol / medium 에이전트3개에파일별로위임했다. 메인이최종코드와검증경로를검토했다.

플레이어별로메뉴요청→새진행→누름유지를검사하므로1P의진행이2P의메뉴요청보다우선한다. repeat0의감소borrow후1재설정,표시시blink2회감소/억제시1회감소를보존했다. native30byte창을원래MS5D로추출하며제어인자0과중간padding을별도로검사한다.

초기원본비교는case75에서RAM/10ports/D3는같지만D0가03200000인문제를발견했다. 메인은3650이swap뒤tile을D0상위word에남기고9256이MOVE.W0만한다는원본명령을확인했다. 결과status를정규화하지않고signedD0전체를반환하도록수정했다. 상위bit가켜진tile도signedoverflow/unsigned-to-signed범위외변환에의존하지않도록signedword를구한뒤65536을곱한다. 호출자상태는lowbyte0/2라는API계약을문서화했다.

수정후1,416조건이전체RAM/orderedports/signedD0/D3에서일치했다. 실제분기idle776/step135/held205/menu300,3902의PAUSE484/clear144회와238180ports를확인했다. verifier는CPU의실제분기와scriptA0를hook으로확인하고전체원본매핑불변도검사한다. 누름유지20회×2플레이어,점멸40회×표시/억제의출력RAM연속시퀀스도통과했다.

reportSHA256:`c1dbe1c087a5f8098877c1966db03f43266e72ac4055f6949f7cb9cf0424a4e8`. make all test는Python61개/C++전체통과. 새단위검사는player1vsplayer2우선순위,repeatborrow,clear의기존palette,PAUSE의palette0,점멸wrap,늦은텍스트실패의RAM/result/전체port보존을검사한다. CLI는3입력/2출력의별칭과숫자범위를검사한다.

입력상태는메뉴가열리지않은활성대기다. 이미열린메뉴의종료callback/928e글자지우기,물리입력·스케줄링/실제게임한프레임진행,전체CPU상태,픽셀·하드웨어타이밍·전체게임부팅은미완료다. 전체목표는active다.
