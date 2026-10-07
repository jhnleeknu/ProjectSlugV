# Secondary 맵 읽기 창 리뷰

Baseline `d215c6e`. 이전 goal turn은 path/primarymap 리소스와 C++ reader를 통합한 progress다. 이번 단위는 후속183c6 원본 분석과 bank2 secondary 접근 창 추출이다. 원본SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`는 고정했다.

메인이183c6..185fa raw instructions를 읽고 clipping unsigned borrow, y목적지ADD와x목적지SUB의차이, MOVEM.W sign-extension, primary bank3 영상쓰기, bank2 secondary 읽기를 구분했다. 분석 계약은 scene-map-transfer.md에 기록했다. 해당 함수의 C++ 실행 대조는 후속 단위이며 이 리뷰의 완료 근거가 아니다.

18568..185a0은 primary column당2개의 WORD offset을 소비한다. 각 offset은 자기 entry 주소에 sign16하여 더한다. 초기 source column은WORD로4배, source row도WORD로4배 후 sign16한다. Destination ring에서 일반복사mask007e와sentinel zero mask007c가다르다. Descriptor의width/height를쓰며primary map header를다시읽지않는다. 메인이이계약을제공하고sol이목록화/추출/반복검사를구현했다.

Canonical 비영 secondary descriptor40개/selector37개,root20204a. 모두구체pointer이며sentinel은없다. Full descriptor width/height,sourcecolumn/row0 기준으로8642column 후보/238982LONG읽기이며bounds오류0이다. 동일cellwindow를공유하는column7399개를보존했다. Canonical signedoffset은모두양수이므로합성테스트에음수offset과각entry기준alias를추가했다. 전체동적접근완전성이나collision의미로확대하지않는다.

Root/알려진lookup/offset WORD창/각cell창의union을기존MS5D v1kind2로보존한다. 겹침·인접만merge하며hole은추가하지않는다. 결과47파일/164960payloadbytes,origin8723개다. CPU=ROMbank2와bank3자료를혼동하지않도록ID는물리ROM시작을쓴다. 전체논리자료extent를추정하지않으며manifest에coverageorigins를남긴다. Inventory를원본에서재계산해일치한뒤파일을게시한다.

메인이 inventory/packer/test/verifier를직접읽었다. 독립endpoint sweep으로resource interval과읽기origin union의완전일치를검사하며header/CRC/전체sourcebytes/metadata와stableID도확인한다. Python-only검증으로명시하고없는C++대조를주장하지않는다. 합성8개포함전체Python162tests exit0. 추출자료와ROM은Git밖에있다.

- Inventory SHA256 `cbe8455db63a1b1570e95024b32e31be31bd93312639a8a4e7890cc454fdd98f`.
- Manifest SHA256 `c4bf74b00417e295d57e176d94cb2145d6f91ef37ef51ab85ccf83bb7d415170`.
- Resource report SHA256 `79f4678387ed1d40a8c1257dc992e0b7c622fc6e414ad65e4098f33bf75e597b`.

다음은동일리소스를소비하는183c6 C++루틴과원본실행의RAM/register/orderedports대조다. 자연스테이지화면과전체게임복원은미완료이며goal은active다.
