# 장면 이동 평가 리뷰

Baseline `9db7c98`. 이전 goal turn은1a26a 실행 루프 구현·원본비교·문서·커밋을완료한progress다. 이번에는일반1a5a4에서호출하는19938과1972a/196ac/196de/18caa/18fd2/18c06을메인이직접분석하고확정계약구현·목록화·검증을sol에분담했다. 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 코드와canonical경로주소는첫1MiB CPU=ROMoffset이다.

## 계약과 구현 검토

D7의16.16 입력으로구간을앞뒤로선택하고d3b8/d3ba 기준word를이동방향에따라갱신한다. 원본1972a의BPL/BMI는N만검사하여V를무시하므로 signed relational comparison을사용하지않았다. 시작0과terminal에서D7을자르는동작,구간을넘을때+6offset을더하거나빼는순서,최종cursor의d3b4저장을보존했다.

36종jump target의WORD delta와LONG 좌표계산을직접대조했다. NEG는ASR보다먼저이며unsigned연산으로16/32비트wrap과signfill을구현한다. WORD연산의register상위부분을보존하되MOVEQ0인보조축은전체clear한다. 19938마지막+8offset은type<58이면Y에더하고모든type에서X에도더한다. D0/D1결과를RAMd3bc/d3c0에저장하는caller동작은이함수에추가하지않았다.

API는기존MS5Dkind1을읽고내부cursor와정확record경계를지원한다. Nullpath는리소스검사없이원본대로반환하며CLI는항상파일로드한다. 후보RAM/state로전체transaction을만들어뒤늦은이전span이탈도입력을보존한다. Type/shape/주소범위검사는지원입력계약이며원본임의메모리실행을대신지원한다고주장하지않는다. 반복bound2N+1은순환입력거부정책이다.

메인이core/CLI/unit/Makefile/목록도구/독립verifier를직접읽었다. Unit의reverseY ASR사례를NEG-before-ASR라고표시한주석만정정했으며실행코드는변경하지않았다. 공유기존scene_command/scene_script_run코어는수정하지않았다.

## 검증

원본19938부터RTS까지12,170조건/오류69조건을통과했다. Strict주소5,466=canonical record경계/fraction/highprofile5,168+실제CLI양방향carry290+null8이다. 합성6,704=36type다양한offset/fraction6,480+N-only overflow224이다. 실제37path108records는11type을포함하며합성은36type모두원본18fd2방문을확인했다. 미복귀/한도초과0,MMIO0이다.

합성원본path는RAM106000에놓고C++는동일rawpayload의fixed60000 MS5D를읽는다. 양쪽RAMscratchbytes는같고원본출력A1과d3b4만주소정규화한다. Canonical에는정규화가없다. 이relocation과호출간A5base/A3A6/stackSR fixture를명시하며ROM을patch하지않는다. 74sequence290호출에서RAM/full12register를승계하고D7만명시적으로host갱신한다. 자연scheduler나프레임진행의증거는아니다.

Report `artifacts/scene_motion/verification.json` SHA256 `a9926535334bf76d820277ac25b3da2448e8346599d11f372c4f7fa8755522a9`. Native session22829 exit0후합성payloadhex/SHA metadata를추가했고실행비교를불필요하게반복하지않았다. Binary SHA256 `13843937cdd4fd721d463d904de0f5ab3ccf552dab77628af423e23a8cffe32a`. 메인이실제보고서수치/해시/실행파일을확인했다.

전체make exit0 Python139/C++101/경고0. `artifacts/scene_motion_build_test.log`에서101개C++실행과warning0을별도로확인했다. 기존기능을수정하지않는추가API이며전체단위회귀가통과했다. 원시37path39참조/108record/37terminal·644decode행·36entry×3dispatch의재생성도구와한계를기록했다.

## 남은 작업

다음은일반1a5a4의1a7a8장면node갱신과후속helper를연결하고이동평가/스크립트루프를같은호출로검증하는것이다. 현재1a5a4전체·47a94이후연결·자연시간축·실제스테이지화면과게임전체는미완료이며목표는계속활성이다.
