# 오브젝트 제거와 화면 초기화 리뷰

Baseline `cd1721a`. canonical 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이299c/2a0a/2a84/c4cc 및ca9e/caf0/35a2의원본을해석했다. sol3개에제거구현,제거원본비교,화면초기화구현·비교와기존회귀를분담했다. 메인이최종코드·CLI·단위검사·nativeverifier·실제보고서를검토했다.

## 핵심 판단

callback270e의제거요청과free-list회수를분리했다. depth가더큰다음노드가있으면hold하고마지막자식제거후이전inactive노드를연쇄회수한다. 연쇄회수는watchdog과palette/coordinatecleanup을반복하지않는다. 2a0a는299c가반환한A6를매번읽으며2a84는입력A6를복원한다. c4cc는보관한현재노드의live next로순회한다.

palette release에optionalD1을추가하여각slot의감산전reference와상위word보존을반영했다. 좌표cleanup은oldworldY를D3에읽고갱신된worldX/Y를D0/D1에반영한다. 그뒤depth비교는D0.low만바꾸며reset271c까지갔을때만D0=0/D1=ffffffff가된다. 사용객체span/잘못된포인터/원본TRAP와순환budget제약을명시하고RAM/state/ports를transaction으로보존한다.

화면초기화는773포트의ca9e와5개고정rectangle을포함한2072포트의caf0를복원했다. 포트순서·폭·주소·값과D0상위word SWAP결과를반영한다. 임의35a2입력을노출하지않고원본고정호출범위만지원한다. 기존메뉴의ca9e동작은이번에수정하지않았다.

## 검토와 검증

최초제거검증193조건은palette/coordinate종료후271c가D0/D1을덮는leaf경로가중심이었다. 메인리뷰에서이것만으로신규반환값을증명할수없음을확인해,271c미호출의deferred150조건을추가하도록요청했다. 최종session17025 exit0:343조건/오류50조건,watchdog382개순서일치. 세hold→childcascade와실제allocator28ae→299c의CLI출력승계를포함한다. 보고서SHA256 `4422458b5cfcf56ddb232cc46c1a5f21b2a92df94f16c0eb7b49d01f33fcca3f`.

기존staticrestart회귀session62561 exit0:506원본조건/오류5조건,보고서SHA256 `05862a1870c440e1ab16e914f038db0dcfce6f1b52c83201f1b8172e15ad4dad`로기존과같다. optionalD1의count0/상위word/실패보존은추가단위검사로확인했다.

화면최종session81276 exit0:104조건/오류23조건,147940포트일치. 실제caf0→ca9e및5회35a2호출을관측하며callee대체/ROM패치는없다. SHA256 `328476653aa7648ceb08c18ea78a72b77425e09dc2591ef520c38d46e9a0227a`.

전체 `make -j3 all test` session11433 exit0. Python88개와C++전체통과,경고없음. 로그 `artifacts/object_removal_screen_build_test.log`. 이후C++변경은없다.

## 범위

controlled list/명시한호출경계검증이며자연스케줄러와callback본문실행은포함하지않는다. malformedloop원본실행은제외했다. 기타CPU레지스터·CCR·stack동등성·물리시간과화면픽셀은미검증이다. 다음c610은seed→제거→화면초기화→47570사운드대기→stage/input선택을원본순서로연결해야한다. 기존input초기화의레지스터계약과대기중A6/호출단계보존을추가확인해야한다. 전체게임복원목표는진행중이다.
