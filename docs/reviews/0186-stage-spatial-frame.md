# Spatial bitmap frame 리뷰

Baseline `123b595`, branch `codex/stage-spatial-frame`. 신규core/header/CLI/unit,Makefile,목록/원본비교도구와문서가대상이다.

메인이 원본46f52/4701e/43e38 전체를직접읽었다. 에이전트사용량실패후남은core/header를검토해fullWORD교환/부호확장/signedSUB조건과wrap/DBRA감소/A3adapter보존을확인하고나머지파일을작성했다. 기존검증된region CLI loader를복사하되인자위치/entry/API출력을검토했다. 실제RAM범위에기반한오류transaction을유지한다.

초기426조건을통과한뒤branch부족을확인하여minX<-96/maxX>=-96 및maxYclamp를보강했다. maxX32767의SUB overflow후논리16bin밖쓰기도추가했다. 8회하드코딩을막기위해8번째node가카운터를0101로바꾸고추가257skip-node를처리하는fixture를만들었다. 원본도실제265회반복하여최종A0/counterffff/RAM/register가일치한다. 이것은자연데이터가아닌명시적경계fixture다.

최종429조건전체RAM/14register/bank일치. pinnedMusashi427,actualbankedUnicorn2이며ROM/stub변경/SRhook읽기가없다.20조건/DBRA분기중19양쪽;46fde는직전D1clamp때문에한쪽만가능하다. 원본write10626건의순서재생이snapshot과일치한다.4frame중3prioroutput승계,CLI거부8조건과API원자성5오류조건통과. API늦은오류는초기clear/앞선bitmap까지보존한다.

리소스목록은128명령/0undecoded와원본source검증된기존458MS5D에서선택한9byte probe3개를보존한다. rawprobe는자연record의미를확정하지않는다. 각probe의누락category거부와directory loader도확인했다. 전체make Python182/C++127/경고0 (`artifacts/stage_spatial_frame_build_test.log`).

Verification SHA256 `d715be1cfffdc1367dc16054807825a6d21170b9fddadef5ac0210f29230bb48`; CLI `125378e29e8f4796b2f302cc600b21ed7d17dbe620a07e29e9fb514c2768f726`; inventory `f3ddcdc81f73553b722d83e2dd807563f983971506a47a9adebbd7707da7ac9d`.

이단위통합을수용한다. 전체CCR/IRQ timing/자연scheduler/전체480bc/직접플레이는미완료이며전체goal은active다. 원격없는로컬통합이다.
