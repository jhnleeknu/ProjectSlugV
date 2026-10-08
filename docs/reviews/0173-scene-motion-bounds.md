# 장면 경로 폭·제한·경계 계산 리뷰

Baseline `7077531`, 브랜치 `codex/scene-motion-bounds`. 직전완료단위는event자료/초기화통합의progress다. 이번구현·목록화와독립검증은sol에분담했고메인이frame1a73c의의존관계와198ee/19978/19d98/19d08의전체register·flag·쓰기순서를분석했다. 검증도구가완료된현재상태를확인해진행중작업을재시작하지않고리뷰를이어갔다.

## 핵심 검토

Core변경전체,기존CLI와신규CLI차이,신규unit을읽었다. 기존19938에서bias전selected_position만분리하고기존bias방식을유지했다. 198ee는+4WORD축별폭을D2/D3에반환한다. Null경로와전체state보존을확인했다. 19978은N-only 32bit분기와LIVE좌표쓰기,19d98은signed16비교·전체LONG EXG·WORD min/max,19d08은두시간선택·WORD만스택복원·마지막ADD의signedoverflow만7fff로포화시키는순서를원본과대조했다. C++signedoverflow/implementation-defined변환에의존하지않는다.

새unit은36type,폭/bias분리,오버플로비교차이,양방향포화와앞선ADD만overflow인경우,후반bounds초기화후실패rollback을포함한다. CLI는기존exactMS5D loader와숫자/파일alias규칙을이어받는다. Resource지원범위/선택한도는기존motion함수와같고RAMmotion은별도미지원이다.

## 자료·검증 근거

메인이inventory도구를읽고10창548행및37resource108record의source/manifest/container대조를확인했다. 현재목록의+4WORD는전부0이고type은11종이다. 따라서nonzero폭과36type검증은원본RAM의합성자료와C++주소정규화MS5D로명확히구분했다. 원본code/파일은바꾸지않는다.

Observer/verifier를모두읽었다. 3,606조건은canonical880/null206/합성2,504/실제CLI승계16이며전체64KiBRAM·12register와RTS/A7를대조한다. 합성주소정규화는출력A1과RAMd3b4뿐이다. 모든네진입에서36type을관찰했고CMPoverflow40조건과포화6조건에는실제분기PC/register근거가있다. 경계갱신과비갱신모두관찰하며19d08의2회폭조회/1회시간조회와복원된시간을검사한다. 13조건의서로다른두시간과16개명시phase제한조건을포함한다.

오류117조건에서입력/기존출력을보존했다. 4실제CLIsequence16호출중12는직전출력을소비한다. D7/phase와19d08전cameraXY는명시host입력이다. MMIO쓰기0,callee중간reset/대체없음을확인했다. 메인이모든3,606행·저장RAMhash·register결과와37resource/manifest/원본hash를대조했다.

기존공유helper회귀는19938 12,170/오류69 및19802 2,664/오류69가통과했다. 전체make Python182/C++114/경고0,로그 `artifacts/scene_motion_bounds_build_test.log`. 코드의공백정리이후최종build도성공했고신규/기존두CLI의binaryhash가각검증report와같음을확인했다.

신규native `f32ba07b37962d31b86feb720d25c8c72754feef529eb7d9e82193a24077d528`,verification `d867cf922bba3631da01ee66a160ae9098e1d2af7677e521cf2209dd4acdc20f`,CLI `41b1481bf18b1aa132601e8c8b07a6835f42140049d537b233396c0aa71bba4f`. 기존19938 report `8df14e6b25f3bdfca1e072ab8891693a240db05130685587c84bfe2ed3faa2e7`,19802 report `6642a5916cfeed9c1a635f99bb633bd51579cb0bc46ec5825a123c877c1097bb`.

## 다음 의존성

전체frame1a73c에는19832/192c4의두좌표경로선택,19a40/19ac8/19b96의좌표진행,1a2b4조건등이남았다. 이번bounds를전체frame완료나직접플레이로표현하지않는다. 원격없는로컬리뷰/commit으로진행하며전체goal은active다.
