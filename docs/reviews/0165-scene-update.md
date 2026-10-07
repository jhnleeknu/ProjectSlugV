# 전체 장면 갱신 통합 리뷰

Baseline `70dc096`. 직전goal turn은원본계약분석,fullregister debug와composite구현,단위검사및기존회귀를진행한progress다. 이번turn에서최종원본대조와coverage보강·재검증을완료했다.

## 메인 분석·구현 리뷰

메인은1afda..1b128,ca9e..cb64,35a2..35f0,1a7a8..1a910의원본을읽었다. Debug의MOVEQ/부분폭저장,SUB/SUBX stickyZ,두번째node가아닌첫node반복검사,40×32 DBRA와마지막D2재설정,ADDI.B/ROL.W lookup scratch를확인했다. Reset tail caf0의D2/D6/D7/A4도callee를따라추론했다.

새API는기존SceneMapTransferState13register를사용한다. 좌표prefix의12register를명시적으로복사하며A3를보존한다. Debug의출력후원본에명시된네node/metadata쌍으로path를실행하고RAM·register·orderedports를호출전체transaction으로게시한다. 기존3register API는새core의wrapper로유지해중복구현을피했다. 기존coordinate/map/path core본문은변경없다.

CLI는명시MS5D파일또는디렉터리를받고정확1af12/512byte debug창을하나선택한다. root runtime디렉터리전체대신필요한파일과맵디렉터리만지정하는재현명령을사용한다. 단위검사의실제1280debug쓰기후네번째path오류는이미생성한ports와RAM/register를모두되돌리는것을확인한다.

## 검증 도구 리뷰 수정

초기native allowlist는caf0→35a2의3c0004 WORD쓰기를누락했다. 메인이발견해담당자에게수정을요청했고19번째case의실패자료를보존한후전체를재실행했다. 원본오류나엔진불일치로잘못분류하지않는다.

Canonicalpath를네node에임의배치하면smallnode3/4의0x80간격에secondarycache가겹칠수있다. 메인이opcode24 references의selector/4를사용하도록요청했다. 실제72참조는node0/1/2에만있고node3참조는없다. Script별동시reference군도관찰하되같은frame에실제로도달했다는claim은하지않는다. 초기slotffff corpus에추가로slot0 primaryvideo활성72조건을요청했다.

첫확장1,345조건은모두원본RTS로복귀했지만,메인이family별port합계를확인해slot0인72조건도모두0port임을발견했다. 다른canonicalpath조건의port도debug출력뿐이었다. 이는표시slot설정만으로실제map전송을검증할수없다는gap이다. Maskff/scroll0/parent0/velocity0와원시path의초기좌표에서유도한visible world좌표를별도fixture로추가하도록요청했다. 기존극단좌표case는보존하며실행중상태보정은하지않는다. 표시가능추가case마다debugoff 상태에서3c0000 쓰기가실제로있어야한다.

## 최종 검증 결과

- Full make: Python170/C++107/경고0. Binary `062b79fd12f7d16098ac7d845e07c0b7605bb28aa3d2a0a6a9c13de8e478e5c7`.
- 기존초기화회귀576/오류24/672744ports/7승계sequence. Report `bfa2403632a17fe814710ae03897243fab189646848ed6e7e5c61d2d7bbd2566`.
- 신규원본1,417조건(1afda263/1a7a8 1,154)/오류44/1,403,936 orderedports:전체RAM·13register일치,모든원본RTS/A7+4복귀. Visible72모두실제185f2/3c0000쓰기확인,해당family96,616ports.
- 실제CLI상태승계20호출/11sequences. Host의debugbits/history snapshot변경은명시fixture이며자연frame이아니다.
- Native SHA256 `a04fd624e808e1f58f3c22d1ba5ead5fbdb4cb411bde008b20e4c2c14157e030`.
- 전체비교 SHA256 `b9a0e96aa5e041411a578da4756e71cd716e8f96eb1452f5fe253ff1b87b58c5`.

메인이최종보고서와현재binary/201resource파일의hash를직접대조했다. Verifier가smoke나동일개수로잘린자료를완전한corpus로받지않도록현재build_cases의전체순서·fixture·개수와RTS/A7를검사하도록보강했다. 최종native/C++는이전positive결과재사용없이전체재실행했다. Main은수정된observer/verifier도읽어원본코드치환이나callee중간contextreset이없고actualCLI RAM/register가carry입력으로사용됨을확인했다. 재생성명령은scene-update.md에있다.

## 남은 전체 범위

전체1a7a8의검증과일반1a5a4는다르다. 일반초기화에는phase선택/반복,종료후1a414배치명령과object allocation/position/inlinepayload복사가더필요하다. Nullscript특수화를일반완료로취급하지않는다. 자연frame/입력/직접플레이화면과전체goal은미완료다.
