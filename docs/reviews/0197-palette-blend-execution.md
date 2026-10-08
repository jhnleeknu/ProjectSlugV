# Palette blend 8cda 전체 레지스터 리뷰

Baseline `e48fc44`, branch `codex/palette-blend-execution`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, 원본 비교를 분담했고 메인이 원본 계약·실제 diff·보고서 및 현재 입력 해시를 확인했다.

`execute_palette_blend`는 기존 `set_palette_blend`의 RAM 처리를 재사용하고 ObjectRestartState의 전체15레지스터를 반환한다. RAM 크기를 먼저 검사하고 원본 node+8 참조WORD를 읽어둔다. D0.low는입력lowBYTE×16으로바뀌며상위WORD를보존한다. A1=104d92,A2=선택slot주소다. 참조WORD가비영이고D2.byte>=32인경우에만MOVEQ처럼D2전체를32로바꾼다. 비활성node에서는D2를clamp하지않고,나머지레지스터와임의A5는보존한다. set_palette_blend는크기검사후실패/할당경로가없으므로RAM을쓴뒤실패하여state만불일치하는경로는없다.

단위검사는slot양끝과highWORD,D2.byte31/32/33의MOVEQ효과,참조0/비영,dirty설정/보존과전체legacyRAM동등성,잘못된RAM의상태보존을확인한다. runtime게임데이터가추가로필요없는RAM/register작업이다. CLI는기존palette effect CLI의파일보호를유지하며정확히15숫자와두경로,15키JSON을사용한다. FIFO/입출력inode별칭/기존출력보존/새출력생성을실제호출로검증했다.

`.venv/bin/python tools/verify_palette_blend_execution.py`가pinnedMusashi 원본480조건의전체RAM64KiB/15register와실제CLI의일치를확인했다. 원본쓰기600건의PC순서/재생,다섯조건분기양쪽,실제RTS/A7와source불변을감사했다. 참조0 160조건,활성320조건,D2전체MOVEQ192조건/보존288조건이며,초기dirty/clean 각각240조건은base-ID비교와독립적으로조합되어있다. 잘못된입력107조건이통과했다. 메인은현재입력10개,native입력6개,native산출물961개해시를재확인했다.

- Verification SHA256: `63125a881e5dac28dbb7562f8adbb9678ba138af48783fe13b2932c0e1eff07f`
- CLI SHA256: `729c4defc5ecaf5f66f79aa0d4668a3391af96a4b1117167021a149c33aae255`
- Native SHA256: `aaddf6efc6fd19e61d5d2af783db3f3a5cc159a6a7cb339ac886e15dbe298222`
- `make -j4 all test`: Python189/C++138/경고0,exit0. 격리UBSan단위검증도통과했다.
- Build/test log: `artifacts/palette_blend_execution_build_test.log`.

이단위를수용한다. 전체4e286 HUD출력과sound대기재개,47c6c callback연결은아직미완료다. A7/CCR/cycle/물리mirror/화면동등성은이15레지스터API의검증범위밖이다. 다음원본HUD관찰을별도로준비중이며그결과를C++전체HUD완료로계산하지않는다.

후속4e286 원본관찰도구를검토했고메인이128조건을별도CPU로재실행했다. 저장된전체RAM/15regs/ports/trace/metadata가일치했다. 실제8cda104회/35f0216회/3af8 6회,ports1,112개이며sound는모두1ac3 enqueue후비대기반환했다. 모든16개lookup WORD주소와코드바이트index10..15를실제읽는것을확인했다. 관찰SHA `2afe1658360f5c3a41fde648544d95cccc6ac645d341b962a83b0caad9291227`. 이증거는nonwaiting범위이며HUD의C++구현/대기재개완료는아니다.
