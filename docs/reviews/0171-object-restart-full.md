# 전체 레지스터 정적 오브젝트 재시작 리뷰

Baseline `ebf108d`, 작업 브랜치 `codex/object-restart-full`. 메인이 원본2a28/299c와팔레트·좌표·필드초기화callee의순서/레지스터변화를해석하고sol에게구현,독립원본비교,명시창및후속event목록을분담했다. 새 API는기존부분D1/D3재시작함수를바꾸지않는다.

## 코드 검토

메인이core/CLI/unit전체를읽었다. Callback은rawLONG저장만하며A1레지스터를복원하지않는다. A0/A6복원,A5=108000,watchdog입력D0.byte,팔레트카운트BYTE와D7 underflow,WORD상위보존·부호있는link주소,8e4a LIVE쓰기순서,좌표43e38의전체12register승계를확인했다.

정리중alias가종류를바꾸는299c후반경로를실제로지원한다. Unsignedorder비교,이전/다음pointer의LIVE조회,freehead/count변경,callback270e와비영종류의반복조건을원본과대조했다. reset_object_fields는같은RAM효과를제공하며이callee의D0=0/D1=ffffffff를반영한다. 모든외부게시가성공뒤이뤄지고65,536회한도와지원밖RAM접근은오류다. Callback실행·CCR·stackmemory전체노출은이번계약밖이다.

CLI의15unsigned인자,64KiB입력,파일경로/symlink/hardlink겹침검사와9byte출력을읽었다. Unit은rawcallback/highWORD,count255,freehead LIVE alias,좌표register,종류변경뒤연결정리,TRAP/범위rollback을포함한다. 전체make Python175/C++112/경고0,로그 `artifacts/object_restart_full_build_test.log`.

## 독립 원본 검증 검토

메인은observer/verifier를읽었다. 원본3ef2로palette를호출전준비하고2a28내부는중단·callee대체없이실행한다. ROM불변,MMIO읽기0,RTS와A7+4를검사한다. Fixture는정상게임경로로가정하지않고rawcount/link/부모/메모리겹침을합성해원본순서를시험한다. 모든15register를비교하며A5의비표준입력과A6 raw복원도포함한다.

첫corpus593조건에서연결경로가한번만실행되는검증공백을찾았다. 메인이연속정리및이전static종료조건을추가하도록요청했고최종native/C++597조건을비교했다. 29c0/29c8각2회,freecount6/head106200의guard가있다. 참조수1조건의8e4a실행과좌표조건의43e38실행도필수검사한다. 전체관찰은8e4a1,251회,43e38288회,29c010회,29c88회다.

최종597조건의전체RAM/15register/597ports가일치했다. 4CLIsequence12호출중8호출이직전실제CLI출력을소비하고host는A0/A1을명시입력한다. 오류135조건뒤메인이self-cycle한도검사를추가요청했다. 오류전체136조건을다시검사해반복한도실패에서도입력/기존출력보존을확인했다. Positive코드/fixture는변하지않아해당추가시positive를불필요하게재실행하지않았다.

메인은현재ROM/binary/native/verificationhash와각597행·저장RAM/porthash·register일치를직접확인했다. Native `ac50d120ef409636185808d039c4a1c0425d20f526f6f74fd83afb3aa86b670c`,verification `6a196fae937d7d558b8d885ec5c237a02236bc216683a0740e820dc4037483d6`,CLI `93f1781648fe7fbe74b56bc7ee1ffae9428a83a80f431000e426715929f69731`.

## 명시창 및 다음 입력

원본명시15창169행의inventory도읽고재생성hash동일성을확인했다. 30ec lookup8bytes는6070809090909090이며후속48398의추출대상이다. 별도stage event inventory는source-verified59record의간접포인터/target을읽고e905c의rawgate선택만적용한다. 고유47stream/612gate,52비영입력/7null을확인했다. Target0의header직후선택을별도처리하고opaque구간은event문법이나전체리소스범위로주장하지않는다. 메인이원본e905c와script전체를검토하고재생성hash `42dd9abc3b757545521fca62a14dab435b51b236c7f97434d515d6b383394372`를확인했다.

다음은e905c의리소스규격/실행연결과47a94후반이다. 480bc는다수callee를호출하므로이번결과를전체스테이지진입·직접플레이·전체goal완료로표현하지않는다. 원격은없으며로컬리뷰/커밋으로진행한다.
