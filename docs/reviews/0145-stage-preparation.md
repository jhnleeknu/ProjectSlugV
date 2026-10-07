# 스테이지 팔레트 등록과 오브젝트 정리 리뷰

Baseline `c718b76`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 ROM CPU 주소는 첫1MiB 고정 매핑에서 파일 offset과 같다. 메인은e7c36/8da2/477c2 제어 흐름·레지스터·순서를 해석했다. sol에 리소스 추출/구현/독립 검증/문서를 나눠 맡겼다.

## 추가 데이터와 등록

e7bda..e7bf4는4개6바이트 등록 레코드와ffff 종결word다. 슬롯b/c/d/e에source025f/0065/0067/006a를 연결하며flags02 및 여섯째byte0을 보존한다. 별도 형식을 만들지 않고 MS5D v1 kind1과 기존 C++ loader를 사용한다. 실제 색 데이터도 기존 MS5P sparse catalog에 추가한다. 전체 팔레트 데이터 추출 완료로 주장하지 않는다.

e7c36은 기존e7bf4를 실행한 뒤 위 테이블로8da2를 tail-call한다. 세 watchdog은 진입D0.byte/0/60이다. 추가 등록은source 하위byte에 해당하는 bucket 선두로 node를 옮긴다. 이미 선두면 relink를 생략하고 D3.low를 유지한다. 최종D0=0000ffff,D1.low=마지막source(실제006a),D1.high 및 D3.high는 보존한다. D3.low는 마지막 실제 relink의 이전 head다.

기존 main_startup.cpp의 등록loop를 내부함수로 공용화했다. 메인은 loop 순서/검증/변경 범위가 기존과 같음을 확인했다. 기존main API는 여전히D0=60,D1.low=1을 반환하며 stage API만 추가테이블의 마지막source를 반환한다. 원본main 회귀검증을 요구했다.

## 오브젝트와 이후 상태

477c2는 현재A6의 자손을2a0a로 제거한 뒤 고정100bf4의 자손과 본체를2a84로 정리한다. 각 helper의 실제 A6/D0/D1/D3 반환을 다음 호출에 전달한다. 이어D0를 전체0으로 만들고8bbc로RAM7dec.byte를0으로 설정한다. 마지막3dce는RAM4d91.bit4를 지우고 RAM6/a.long에3dcc를 쓴다. D1/D3를 임의 초기화하지 않는다.

479b0 준비 API는e7c36와477c2를 연결하고479ba의 후속명령 직전에서 멈춘다. late resource/list 오류는 앞서 수행한 palette나 removal까지 candidate 내부에서 취소해 RAM/레지스터/포트를 보존한다. 다른 레지스터·CCR·자연 scheduler와479ba 이후 스테이지 본문은 아직 계약 밖이다.

## 검증

전체 make -j3 all test는 Python104/C++92 통과, 경고0이다. 기존main startup 원본 회귀209조건/오류32조건/418포트와 준비 연결2조건도 통과했다. 보고서 SHA256 `2bf5387682dae840040749fb882917080a43ecedb22a1dd13766ca123cccea7a`가 이전 결과와 같다. 새 MS5D container는58바이트 SHA256 `de398dc6e5c917c83709a325dd72b557faa0b94a66b3a5d71b5c955fd7f3fdc6`, MS5P는33개ID/2276바이트 SHA256 `df097b579c1c544bb39f0eaa94b85767180f73acad33ace29b154da4a261a07c`다.

기존 palette resource verifier는 disabled sourceffff를 실제 색 ID로 조회하던 오류를 수정했다. 활성34bindings의 색 데이터 비교와 비활성4bindings의 제외 목록을 분리했다. 이 검증은 각 테이블을 독립 상태에서 실행하며 모든 자연 장면을 검증한 것이 아니다. 보고서 SHA256 `e7a7f4124229ccd54edcc5d4fb262d21588fab3ecd5194161cc89258019da32f`.

독립 새 준비 검증은101원본조건/37오류조건/441API포트와2CLI 승계시퀀스가 통과했다. 별도e7c36→7196→72fa는 신규4슬롯 각각32바이트가 MS5P와 일치했다. 최종 보고서 SHA256 `226820728af213cb3fc73808809723e951d4e8a00dbd39d644793f69d08a17ab`. 별도 palette 변환에서7196의 PVC1000/0 pair가 두 번 나오는4쓰기를 실제로 기록했다. 처음에는 한 pair만 예상한 검증 보조조건을 실제 trace에 맞춰 수정했고, 최종 실행에서 A7와 포트 기록을 함께 검증했다. mapped physicalbank의2ffff0 이후는 장치 register overlay이므로 ROM 불변 비교는200000..2fffef로 한정하고 고정 첫1MiB는 전체 비교한다. A7는 standalone RTS와479ba 경계에서 서로 다른 반환 위치를 확인한다.

## 다음 분석 근거

명시적476d0..477c2 범위를 artifacts/stage_preparation/next-player-setup.json 및 asm에 보존했다. 첫12바이트는476bc/476c4/476cc를 가리키는 세 pointer long으로476f6에서 읽으며 디코더가 표시한 ORI를 실행 코드로 취급하지 않는다. 476dc는 stage6..8을 세 pointer로 선택하고 그 외 stage는첫pointer로돌린 뒤 area*4의 두 word를 읽는다. 47742는 word부호에 따라 고정 플레이어를 제거하거나재시작하며 선택값4이상에 난수 helper49a58을 호출한다. 테이블의 정확한 주소가능범위·사용조건과 helper전체레지스터는 다음 작업에서 검증해야 한다.
