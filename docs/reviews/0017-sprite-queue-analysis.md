# 스프라이트 큐 분석 리뷰

기준b73a968. 메인 에이전트가 원본 producer/consumer를 직접 추론하고48개 경계 입력을원본CPU로검증했다.64KiB 전체 memory effect일치. 출력자료는artifacts/sprite_queue에만보관한다.

소스ID0x2152/0x2952를즉시값으로쓰는원본호출부를확인했고bank/group/item 두단계참조로ROM0x4cce60/0x4cd3e8에연결했다. 첫data폭/높이 해석은코드와인접pointer 차이로지지되지만 전체format완료로기록하지않는다.

큐충만wait,정렬소비,하드웨어쓰기전체는아직미검증이다. 분석검증기는재구성C++와의차등검증이아니며그범위를문서에명시했다.
