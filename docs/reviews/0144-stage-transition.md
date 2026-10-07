# 스테이지 전환 분기 리뷰

Baseline `2faca66`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 첫1MiB에서 아래 CPU 주소와 ROM 파일 offset은 같다. 메인이 원본 제어 흐름과 레지스터 계약을 해석하고 sol에 구현/검증/목록화/문서를 분담했다.

## 해석한 계약

478c4/478f0/4791c는 palette8c16에 각각 -31/0tick, -31/16tick, +31/30tick을 준다. duration0은1이 된다. RAM 팔레트만 일치시키지 않고 signed DIVS의 나머지 상위word와 몫 하위word까지 반환해야 한다. 모든 delta가0인 early return에서는 MOVEQ가 만든 D0-D2 상위word 및 D3 상위word를 보존한다. 변경 경로에서는 D3를 duration으로 전체 초기화한다.

478f0과4791c는 callback4790a 설치 직후 첫 countdown 감소까지 같은 호출에서 실행한다. old counter0의 SUBQ borrow만 ca8a→479b0으로 진행한다. 478de의72f0은 RAM7ded.byte에서80을 빼므로 old값80..ff에서 반복한다. API는 한 번 관찰한 뒤 같은 PC를 반환하고 원본 scheduler의 시간 진행을 만들어내지 않는다.

ca8a는 ca9e와 별개다. 40×32 고정 타일과 watchdog 및 제어 포트까지1283개를 순서대로 출력하며 D0.low=7500,D1.low=7000,D2.low=0,D3=20이다. 4791c의 caf0은 기존2072포트 구현을 사용한다.

47934/4794c/47964의 allocation은 callback4fcb8/4fd0a/4ff4c를 저장한다. 성공하면 parent62를 지우고4798e를 설치한다. 마지막 종류만 LIVE RAMd690/d692를 새 노드76/78에 순서대로 복사한다. 정상 allocation 실패는478c4로 이어진다. 4798e는 flag가 설정되면 fade를 시작하고 다음 callback479b0을 설치한 뒤480bc 경계로 간다.

## 범위와 다음 본문

API는480bc 또는479b0 본문 직전에서 멈춘다. CCR, 다른 A레지스터, 자연 scheduler 전체를 복원한 것으로 주장하지 않는다. 앞 stage entry API는 D2를 반환하지 않으므로 두 API 연결만으로 모든 CPU 레지스터 승계를 증명할 수 없다.

별도 body 목록화는479b0..47af0에 인코딩된24직접호출/18대상 각각128바이트를 보존한다. 이는 실행 가능한 모든 호출이나 코드/데이터 분류 완료가 아니다. 메인 관찰:477c2는 removal2a0a/2a84, palette8bbc, sound3dce를 연결한다. e8a1c는 A0=0이면e89e4로 대체하고 de26/de2e/de2f를 설정한다. 48180은4d7a6의 복수 레지스터 반환값을 두 플레이어 기록 중 하나에 저장한다. e905c는 정적 오브젝트 재시작 뒤 입력 포인터를 D7으로 pop한 MOVE.L의 Z를 검사하므로 분기 기준을 D0으로 오해하면 안 된다. e7c36은 기존e7bf4 후 추가 고정 팔레트 등록e7bda를 호출한다. 해당26바이트는 슬롯b/c/d/e에 source025f/0065/0067/006a, 각flags02를 등록하고ffff로 끝난다. 이 추가 테이블의 런타임 리소스 패키징 및 본문 연결은 다음 작업이다. 이 본문들은 아직 구현/동작 검증 완료가 아니다.

## 최종 검증

메인은 core/CLI/unit/Makefile을 검토했다. candidate 내부에서 timer를 먼저 쓰고 palette 현재값을 읽는 순서 및 child 좌표의 순차 LIVE 읽기를 확인했다. 전체 make -j3 all test는 Python95/C++91 통과, 경고0이다. 독립 verifier를 검토하면서4791c의 all-delta-zero 보조 assertion이 caf0 이후 D3 상위word 초기화를 반영해야 함을 지적했다. 원본/C++ 비교와 별개인 검증 조건을 수정하도록 했다. 수정 후 최종 원본1249조건/오류49조건/618179포트 및 실제CLI callback 승계6시퀀스가 통과했다. A6+7a가 palette 현재값7dc2에 겹치는36조건과 child 첫 좌표 쓰기가 두 번째 source에 겹치는 조건도 원본과 일치했다. 전체RAM/D0-D3/A6/포트 순서를 비교했고 실행 파일과 ROM이 불변이었다. 보고서 SHA256 `fa20a6699046a1429b21094909462a5f7cd9be89688f6016ae195ff7756f97d3`. 승계 시 callback 스케줄링과 gate/child flag 변경은 host fixture이며 실제480bc scheduler 또는 IRQ 진행을 검증한 것은 아니다.
