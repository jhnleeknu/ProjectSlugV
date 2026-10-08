# ca9e/caf0 전체 레지스터 후속 계약

메인이 canonical BE 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`의ca9e..cb62,35a2..35ee를 확인했다. 모든 주소는 고정 CPU 주소이자 동일 ROM 오프셋이다. `artifacts/screen_reset_full_static.json`에 ca9e..cb62 및35a2..35ee의 완전한 명령 범위를 보존했다. 현재는 정적 계약이며 full15register API나 native 비교 완료가 아니다.

ca9e는A4=3c0000을설정하고D0=0→75000000, D7.low=2ff로시작해768개LONG video writes를수행한다. DBRA는D7.low만감소시키므로 최종D7은입력상위WORD와ffff다. 이어D1전체0,D0최종7580ff02와5개video writes를남긴다. 총773ports, RAM변경없음. D2..D6/A0..A3/A5/A6는불변이다.

caf0은ca9e전체를호출한뒤35a2를5회실행한다. rectangle순서는(7021,00ff,38,30),(701f,7000,40,1),(7000,7000,40,1),(7000,7000,1,32),(74e0,7000,1,32)다. 각호출은watchdog BYTE, column-major LONGvideo writes, WORD3c0004=0,LONG3c0000=82000000을낸다. 기존reset_game_screen의ports생성은이순서를반영한다.

최종caf0은D0=75807500,D1=00007000,D2=0,D3=32,D6=입력상위WORD|0000,D7=75007000,A4=3c0000이다. D4/D5/A0..A3/A5/A6는보존한다. 끝의CLR.B는A5+signedWORD8966(A5-769a)에쓰므로 A5=108000일때100966이다. 기존부분API의고정RAM966쓰기를임의A5지원으로확대하지않는다. 새전체API는A5를108000으로제한하거나실제checkedRAM목적지를명시적으로지원해야한다. ca9e자체는A5를역참조하지않는다.

35a2가매rectangle에서D6.low를height로설정하고0까지감소시키며D6상위WORD를보존한다. D7은MOVE.W D0→SWAP→MOVE.W D1로packing되므로초기D7상위WORD는사라진다. D0는각column끝에WORD32를더하고D2는WORD단위감소하지만caf0의후반MOVEQ1가D2전체를초기화한다. 기존API가반환하지않는D2/D6/D7/A4를정확히전달해야47af0후속을전체레지스터로연결할수있다.

새API는원본stageframe의경계와별개로ca9e/caf0전체를검증한다. 실제ROM실행에서fullRAM15regs/모든orderedports를비교하고상위WORDprofiles,임의입력A5정책,invalidspanrollback을확인해야한다. A7/stack/CCR/물리mirror동등성은별도범위다.
