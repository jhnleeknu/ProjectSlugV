# 맵 사각형 전송 C++ 리뷰

Baseline `6eae314`. 메인이원본183c6..185fa를분석해계약을제공하고sol이C++기계적구현/CLI/unit과독립원본관찰/비교를담당했다. 메인이최종source,unit,CLI,원본harness,비교도구와실제보고서를확인했다. ROMSHA는scene-map-transfer.md의canonical과같다.

## 구현과 리뷰 수정

Unsigned clipping과WORD/BYTE wrap,primary column-major데이터의VRAM LONG쓰기,secondary self-relativeWORD offset과RAM ring쓰기를원본순서로구현한다. MS5D source창을직접읽으며primary는bank3,secondary는bank2물리주소로구별한다. Header치수를대신쓰지않고descriptor를LIVE조회한다. API는13register와copied,ports,RAM을transaction으로게시한다.

메인은184bc ADD.B를초안의ADD.W로처리한오류를확인해lowbyte만갱신하도록수정했다. Y clipping의목적지ADD와X clipping의SUB차이를문서에도반영했다. 잘못된odd resource창은주소조회대상에서제외하고미지원읽기로오류처리한다. Ambiguous/cross-window읽기와late secondary실패도외부결과를변경하지않는다.

초안의zero loop count거부를원본SUBQ.W/BNE의65536반복으로바꾸었다. Primary/secondary각1048576cell의임시실행한계는명시API오류로남겼으며완전원본지원으로포장하지않는다. API내실패시rollback과CLI의두파일I/O atomicity는별개다. CLI는manifest가아닌정렬된MS5D파일을미리로드한다.

원본183c6에서184d2zero-write블록으로가는경로를추가하지않았다. Sentinel ffffffff branch는코드대로구현하고C++합성unit으로검사했지만canonical원본관찰에는해당pointer가없으므로native동등성범위밖으로표시했다.

## 실제 대조

원본492조건이모두RTS로복귀했다. 이중4개는RAMdescriptor높이가bankshadow에의해바뀌는alias조건이다. 원본코드/physicalbankbytes는수정하지않고호출내context연속성을유지했다. 독립호출시작baseline복원은내부실행을쪼개는것과구분한다.

C++전체RAM/13register/copied/ordered16620ports가일치했다. Copied는원본185f2/185f8실행경로로판단하며rawSR은별도관찰값이다. 복사420/거부72이다. CLInegative29조건과unit의latefailure결과보존을구분했다. 메인이negative10ff00node와10fff8descriptor가일부조건에서합법일수있음을지적해반드시범위밖read가되는주소로수정했다.

Observation SHA256 `242bdc3703c6c57ea771c94439d3c094b83a7c52f62bdbc3a37d2b33204bef56`,비교report `ba687e364602ab08a4074d3aa09f5b17ae8396576132a30c75d5ae99f611acef`,binary `80a3fd5811521e0389ca646fbd9acd3511b2efaa9a4f839a86d284f8dbd64660`. 메인이현재파일해시와보고서수치를재확인했다. 전체make Python162/C++104/경고0. 공유기존코어는수정하지않았다.

## 남은 범위

다회호출승계/자연frame은이번대조범위밖이다. 초기bank조건은fixed/RAMdescriptor fixture에서만상쇄되며임의bank진입지원이아니다. 다음은18702 wrapping caller,16f0e column control,1861a/18656 refresh와19e64 handler연결이다. 이후1afda register승계와일반1a5a4/47a94진입이필요하다. 영상쓰기복원은직접플레이가능화면완료가아니며전체goal은계속active다.
