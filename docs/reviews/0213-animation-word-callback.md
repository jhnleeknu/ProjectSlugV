# Animation WORD callback3c 리뷰

대상은 baseline `cc5750b` 이후 `codex/animation-word-callback`의 C++3c 경로,14의 실제 RTS callback, 원본 관측·selector 목록·MS5D 패커·비교 도구다. 원격 없는 로컬 리뷰이며 PR이 아니다. canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`; 고정 CPU 명령 주소와 ROM 오프셋은 같고 벡터 영역은 별도 caveat를 둔다.

## 변경과 원본 판단

3c는 두 WORD selector의 wrap/signed 인덱스와 두 lookup을 수행하고, operand LONG을 D0/A0에 넣어 실제 target을 호출한다. 기존2b3e8/2b3fa/47672와 실제4e75인3679e만 연결했다. 이 RTS를 근거로14 selector03도 지원한다. 다른callback을 no-op으로 간주하지 않는다. 사운드 대기는 phase2, 복귀는 bank/PVC·MOVEM.W signed16→32·A0/A1 LONG·D6/pointer 저장을 재사용한다. state/API/CLI 형식은 유지했다.

메인이 원본4a30c..4a382와3679e,2b3e8..2b40c를 읽고 구현을 검토했다. 원본 관측은 callback 진입 D0/D1/D7/A0/A1과 실제 stack, 대기 후 live source/terminal 접근을 확인한다. 전체3c와14의 다른callback은 미완료다.

## 발견한 문제와 수정

1. **A0/A2 register 오류**: 첫 구현은4a326의 LEA4a76c,A0를 A2에 옮겼고 단위 검사도 같은 잘못된 기대값을 사용했다. 메인이 raw41f90004a76c와 diff를 대조해 발견했다. A0로 수정하고 nonzero A2 보존 검사를 추가했다. 다른 새 register 기대값도 원본으로 재검토하고 normal/UBSan·전체 검사·원본 비교를 다시 수행했다.
2. **prefix 크기 산술**: [42500,4276c)는624가 아니라620BYTE/155 LONG 슬롯이다. 목록 작업자와 패커 작업자가 독립 계산으로 발견했다. 계약과 문서를 교정했다. 주소 범위 자체는 바뀌지 않았다.
3. **중복 lookup 리소스**: control_04276c가4411e sound lookup도 포함한다. 성공 실행에 narrowlookup까지 제공하면 동일 주소가 모호해지므로 기존 widewindow만 사용한다. reader의 중복 거부를 완화하지 않았다.

## 작업자와 검토

Sol6.1/medium이 core/unit, inventory/공식검증기, RTS 관측/독립 리뷰·원본 감사를 분담했다. Sonnet5.5/medium은 패커·합성검사, Opus5.5/high는 나머지 세callback의 독립 원본 관측을 맡았다. 메인은 원본 의미·계약·수정 판단·실제 diff와 결과의 수용을 담당했다. 최대 작업자5/내부3을 유지했다.

CLI에 Claude model/effort를 명시했고 반환 modelUsage의 실제 모델이 Sonnet5.5/Opus5.5와 일치했다. 적용 effort는 반환 필드가 없어 요청값 이외의 독립 증거는 없다. Sol의 독립 core 리뷰·UBSan과 Opus 원본 전체 재실행 감사에 추가 결함은 없었다. 독립 감사는 같은 Unicorn 인프라를 사용한다.

## 검증 범위

- 수정 후 `make all test`: Python241/C++145 통과, 경고0. 이후 패커의 두 경계 operand 리소스와 검사가 추가되어 최종 Python discover243개 통과. C++ 소스는 그 사이 바뀌지 않았다. normal/UBSan 단위 검사도 통과했다.
- 전체 두 WORD selector 입력131072개 주소 계산과 실제 table raw값 목록·재생성 일치. 지원target3679e/2b3e8/2b3fa/47672는 각각 하나의 slot과4alias만 존재한다. raw값 목록을 지원가능한 모든함수 목록으로 취급하지 않는다.
- RTS 원본438조건/438단계와 다른세callback122조건/138단계, 총576성공단계를 재실행했다. 기존지원범위 밖5target은 prefix 뒤 중지, oddtarget1개는 미실행으로 구분했다. 총4488PVC/3external reads. 대기연쇄6개/16재개.
- 공식 C++ 대조는 sound CLI576단계 및 non-sound ordinary CLI515단계다. 전체RAM15R/state/carry/PVC/외부읽기 일치, 직전실제C++출력으로16재개,10개pending호출은리소스없이성공한다. 합성MS5A padding유무2조건의결과도일치한다. 이는실제고정script도달성증거가아니다.
- 오류·파일 보존383조건을 확인했다. 실제prefix155slot의원본target거부, prefix제공/누락구분,필수두lookup missing/partial/overlap,callbackoperand,latephase2실패,두CLI의실제unsupported5target거부와alias/FIFO검사를포함한다. API rollback은C++단위검사로확인하고 CLI파일보존과구분한다.
- 기존 execution/control/sound/indexed/field/direct-sound6회귀 모두통과. 메인이보고서의현재소스/CLI/산출물해시를재확인했다. 최종새보고서해시는STATUS와실행문서에기록한다.

## 리소스·남은 범위

MS5D v1 kind1의620BYTE prefix와각1024BYTE boundaryoperand2개를추가했다. 실제ROMbytes/CRC/header를검사하고C++loader로소비한다. 기존control/6431aoperand는재사용한다. [0,80)는canonicalcartridgeROMview이며BIOS/cartvector선택검증이아니다. 이fixture창안에서는주소wrap이없으므로임의32bitpointer에24bitmask를지원한다는증거도아니다.

미완료: 다른14/3c callback,40과실제bank상태의대기보존,자연script/groupbinding,자연IRQ/Z80,wholeCCR/cycle,직접플레이와전체Goal. bankshadow와physicalbank의차이및PVCoverlay경계문제는별도설계문서에남겼다. 현재14개의전체명령과14/3c의부분callback지원상태를구분한다.
