# 제어 요청 수락과 메뉴 진입 리뷰

대상: `38885a8` 이후 변경.

메인은9136..9332와ca9e..caee, a2b8을 원본에서 읽고 비활성 수락/실제92ce 진입의 지원 범위를 정했다. 활성 컨트롤러 전체와 종료 간접callback을 구현했다고 주장하지 않도록 API 경계를 명시했다. 메뉴 진입/첫 프레임/입력 tail 통합과 late-failure 단위검사는 메인이 구현했다. 확정된 수락 처리/원본 비교, CLI, 메뉴 진입 비교는 gpt-6.1-sol / medium 에이전트3개에 분리 위임했다.

비활성 수락은 pending byte를 그대로 복사하거나9086의bit1→bit3 우선순위를 적용한다. 입력을 저장한 직후 tail을 실행하므로 누적 byte가 변하지 않는다. 92ce 진입에서는 저장 입력을 덮어쓰지 않고 현재 값과 비교해 새로운 bit를 누적한다. 두 경로를 같은 입력 초기화로 합치지 않았다.

ca9e의773개 long writes 순서를 그대로 기록한다. 메뉴 초기화의 optional final_line을 첫a370 호출로 전달하며 실제진입A7은S−4다. 첫 frame은 높이0에서 열기 단계를 수행하므로 아직font를 읽지 않는다. 결과를 다음frame으로 전달하면9332가 실제 호출됨을 별도로 확인했다. 기존 current/head/renderer가 무효값이어도 원본초기화가 이를 덮어쓰는 순서를 따르며, firstframe 후current가root로바뀌는 효과를 포함한다.

메인이 verifier의 wholeRAM/ports/status/D3 비교, helper순서/A7 assertion, 입력 누적/소수 높이/countdown assertion과 시퀀스의 실제9332호출을 검토했다. 고립432진입 및3시퀀스15호출이 통과했으며 reportSHA256은 `11444536b70c74303ee6d332ff3db50dc332c98869d7443572c95ae784e4bee2`다.

요청 수락8,192조건은 전체RAM/반환byte 일치,수락8169/미진입23이다. ROM불변보고를 실제mapped1MiB 비교로 확인하도록 요구했고 최종verifier를 다시 실행했다. reportSHA256은 `38c1e1b0fb24010e88ec888153e0bcf7173d845df91277612c78a0961597569e`다. CLI 입력별칭/크기/이미활성오류에서 기존출력보존도 확인했다.

전체 make all test(Python55개와C++전체) 통과. 진입 단위검사는773쓰기를 준비하고 메뉴 초기화까지 진행한 뒤 미지원header가 실패하는 경우의 모든RAM/result/port출력 보존을 확인한다. 원본프로그램수정,PNG 의존성,새런타임리소스형식은 없다.

9136 활성대기/반복,종료간접callback/928e글자지우기,물리입력·스케줄링,전체CPU레지스터/외부스택,픽셀·타이밍·전체게임실행은 남아 있다. 전체목표는 active다.
