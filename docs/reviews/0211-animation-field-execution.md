# Animation 필드 변경·상대 분기와 실제 script 연결 리뷰

Baseline `b5ded33`, branch `codex/animation-field-execution`. 메인은 원본4a27e..2d8,4a2f2..308,4a3de..404의7명령과공통4a276복귀를읽고계약을확정했다. Sol6.1/medium 세작업자가core/unit,원본/검증기,실제resource/문서를병렬로구현했다. 메인은전체diff·빌드·보고서해시를확인했으며구현작업자는검증기/native를,리소스작업자는core를독립리뷰했다.

## 구현 검토

18의D0high24/D1high16보존과WORDselector두배wrap,1c/20의D1쓰기폭,24의memoryBYTE감소와D0offset보존,34/38의padding미읽기와D0변경차이를원본raw에대조했다. 2c는fieldWORD상위BYTE를남기고WORD두배한뒤unsigned비교한다. 선택되는경우script WORD를읽어signed변위를더하고그결과에signedlength를더한다. 기존script/data reader를구분하고각실제접근만검사한다.

일곱명령후D6=A1,LONG(A0)=D6를쓴다. target/statepointer와live다음script의alias도원본순서대로처리한다. 기존state/API/CLI/포맷을유지하며candidate transaction이늦은오류에서도모든공개상태를보존한다. 복귀나선택결과를편의상정규화하지않았다.

unit리뷰에서RAM안의odd주소를범위밖이라고설명한오류를찾아실제aligned LONG10fffe..110001경계초과로교정했다. 검증기초안은2c의없는selector0 fixture를찾아StopIteration이발생했으며실제존재하는2c fixture와그table주소를사용하도록수정했다. 둘다검증코드/설명의문제였고runtime불일치는발견되지않았다.

## 원본·리소스·검증 근거

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`는불변이다. 아래주소는fixed CPU=ROMoffset이다.

- 원본818조건/PVC3272개에서whole49fc6의64KiB RAM15regs/carry/읽기·쓰기·PC·stacktrace를보존했다. 요청991중173은odd/outspan또는제어fixture조건으로제외했고정상실행성공으로세지않았다. nativeSHA `8ce1f6051cd06310e7e3e321f8ad9bbb879714ceee4381e8662883b936f3e508`. 독립56조건재실행·8입력3272파일해시감사통과.
- 실제verifier가818원본조건을모두재실행후실제CLI출력RAM15regs/metadata/carry/PVC와비교했다. 34/38은리소스없이실행했다. 길이1/index0의선택WORD0000과후속00의겹침은primaryfixture에서제외되지만합법적이므로별도원본실행+C++추가1조건/PVC4개로검증했다. 선언length보다읽기폭이큰경로를묵시적으로빼지않았다.
- 원본caller3d2e2 raw와script[3e808,3e854)의분기·점프경계를검토했다. 76BYTE/15명령이두loop를닫으며0c의selector2f는object+a0,18의selector34는object+b0다. 이후3e854script는미포함이다. sourcehash/callerraw/명령경계/operand제약/payload·containerpin을검증하는packer가stableID·메타데이터를포함한기존MS5A108BYTE를만든다.9합성test와메인의실제재생성byte대조가통과했다.
- fixedscript12조건에서새MS5A와기존wideMS5D를C++loader로읽고원본과전체RAM15regs/carry/PVC96개가일치했다. 제어groupf2는실제groupbinding이나자연게임도달성으로주장하지않는다.
- 오류64조건은다섯table명령의누락/partial조회,actualodd/outspan쓰기,여섯필드쓰기후nextfetch실패와2c의늦은fetch,source정렬,metadata·resource·FIFO·alias·두출력예약실패시보존을검증한다. APIunit에서실제도달한scriptwindow의빈padding허용,liveRAM수정후fetch,상태pointer중간쓰기와rollback도검증한다.
- 새reportSHA `d7f3685c55b9401359b84eff53d10e2e26d3ada6222c2d49e5b885ad2dab6592`. 메인과독립Sol이입력33/산출물6644항목의고유6676현재경로해시와최종오류문구/trace를확인했다.
- 기존execution90/98+15추가164오류,control178+2혼합48오류,sound22/30 73오류,indexed846/854+fixed30+signed6+soundCLI12 60오류도현재binary로통과했다. 현재SHA와전체재현명령은STATUS와animation-field-execution.md에기록한다.
- `make all test` exit0 Python234/C++145/경고0;단위normal/UBSan통과. ROM/추출data/artifacts는Git추가하지않았다.

남은actionable결함을발견하지못했다. 이번엔7명령추가로13명령과14일부경로를지원하며30/3c/40·다른callback은미완료다. 모든selector/relative조합,전체CCR/physicalmirror/cycle,자연scheduler/IRQ,직접플레이및전체Goal이완료된것은아니다.
