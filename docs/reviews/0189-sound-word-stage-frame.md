# Sound word와 stage sound frame 리뷰

Baseline88b79c2, branch codex/sound-word-execution. 사용자 병렬 규칙 변경은 b9b3939에 별도 저장했다. 이 단위는 full3af8과 상위2efa6, CLI/단위검증/원본비교 및 문서다.

Sol6.1/medium 세 작업자에 core+unit, 원본비교, CLI+Makefile+문서를 분리했다. 먼저 끝난 작업자는2efa6 core/CLI/verifier와 전체480bc fixture 설계로 재배정했다. 메인은 원본계약, 전체core/CLI/verifier/단위검증diff, RAM alias/정수폭/대기stack 계약을 검토하고 최종통합했다. 같은 파일은 완료 보고 후에만 재배정했다.

Opus claude-opus-5-5/high 읽기전용 독립리뷰는 3af8의 구현상 오류를 찾지 못했다. 실제 modelUsage도 claude-opus-5-5, effort는 CLI high 요청이며 결과별 확인 필드는 없다. 178.224초, 보고비용$0.6426818, output15040 tokens(thinking11365), input20/cachecreation37613/cacheread204489. 로그 artifacts/sound_word_opus_review.json. Opus는 테스트를 실행하지 않았다.

리뷰가 지적한 테스트 누락 중 highbyte3 성공 후 lowbyte 실패로 특수flag/queue를 원복하는 조건과 phase1/2 재개 주소오류4조건을 추가했다. 메인은 해당diff와 전체make 재실행을 확인했다. 나머지 gate/초기index8 alias는 실제 원본비교에 포함되어 있다. A5고정/A7추상화는 API 계약이며 원본은 별도stack(1feffc)을 사용해 저장byte/WORD와return주소/A7을 검사한다. 게임RAM64KiB와 stack 영역을 구분한다. 실제 원본 stack을 옮기거나 ROM을 패치하지 않는다.

3af8 원본2560단계/CLI거부98조건,22조건분기 양쪽,8sameCPU체인,Musashi12대표교차확인 통과. unsignedgates, conditionallyread d00046, duplicate source-before-dest, livehead/tail, signedinitialindex, overflowzero/byte3/postincrement, high/low pending이 일치한다. loop에 쓰기가 없어 repeatedindex 검출의 비종료 판정은 타당하다.

2efa6 원본2441단계/CLI거부112조건,상위3조건분기 양쪽,5pending상태,19sameCPU체인 통과. 초기D1.byte와D0.byte/WORD 폭, helper이전d491게시, 재개시 flag/gate/queue 비재샘플을 확인했다. 메인 요청으로 fixture순서를 정렬하고 모든 host byte/WORD변경을 report에 명시했다. 고정명령에서 불가능한 helper분기를 전체coverage라고 주장하지 않는다.

전체make -j3 all test 최종exit0 Python182/C++131/경고0. API 오류는 전체RAM/상태/외부readcount 보존, CLI오류는 입력 및 기존출력 보존이다. Sol UBSan 단위실행 통과; ASan결합실행은 완료되지 않아 통과로 취급하지 않는다. 현재소스/CLI가 양쪽원본보고서provenance와 일치함을 메인이 확인했다.

WORD reportSHA e8d035a20eaf7a24500ded9945be71a97d8ae59c8e5507622cf0d24319eda0bd, CLI2117feccf6966a51fafbd086a95c9f3bd93c53f103251634780f8ec951db7a17. Stage reportSHA5d1d8ecfa01264218f0f367221f25d9375717c2594f302da5a327c0fbe60f2df, CLI0faa5ff242e15db78946008eed26a355a689f59d940b07c4436f49c804b0502e.

통합을 수용한다. 전체480bc 원본smoke fixture는 별도후속설계이며 C++통합검증이 아니다. 자연scheduler/IRQ/전체CCR/오디오재생/직접플레이/전체게임은 미완료다. 원격없는로컬통합이며 Goal은 active다.
