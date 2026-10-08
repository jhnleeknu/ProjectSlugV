# 화면 초기화와 후속 timer의 공유 스택 계약

Baseline `c776ed8`. Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인은 ca9e..cb62와47fca..47fe4의 실제 명령 bytes를 확인했다. 아래 주소는 fixed CPU 주소이며 같은 ROM 파일 offset이다. 기존 screen-reset-full-contract의 register 의미를 공유 RAM/16R/PC/A7 실행기로 연결하며, 기존 부분 API 결과를 실제 stack 실행의 증거로 대체하지 않는다.

## ca9e와 DBRA

ca9e LEA는 A4=3c0000으로 설정한다. caa4부터 D0 전체0, D0.low=7500, SWAP D0, D7.low=02ff를 실행한다. D7 상위WORD는 유지한다. cab0은 LONG D0를 live(A4)에 쓰고 D0에10000을32bit wrap으로 더한 뒤 D7.low를1감소시킨다. 감소 결과ffff가 아니면 cab0으로 돌아간다. 정상 진입의 loop 출력은768개이며 D7은 초기 상위WORD|ffff가 된다.

직접 cab0 진입에서 D7.low=0이면1회,1이면2회,ffff이면65536회 출력한다. 음수로 해석해 미리 건너뛰지 않는다. 직접 cab8은 DBRA만 실행하므로 C를 보존하고 D7.low를 감소시킨 뒤 branch한다. cab0의 MOVE.L/ADDI.L/DBRA를 묶은 block은 CUnknown이다. DBRA는 Z를 소비하지 않는다. 모든 loop는 기존 semantic block 예산을 적용한다.

cabc는 D1 전체를0으로 만들고 D0.low=7500,SWAP,D0.low=0200을 실행한다. 이 순서의 결과 D0는75000200이다. cac8/cad0/cad8/cae0은 각각 live(A4)에 LONG을 쓰고 D0에200000을 더한다. cae8은 D0.low=ff02 후 마지막 LONG을 쓴다. 출력 값은75000200,75200200,75400200,75600200,7580ff02이고 최종 D0=7580ff02다. caee는 live RTS한다. 정상 ca9e는 총773개 LONG video 출력을 남긴다.

ca9e의 A4 초기화를 건너뛴 직접 loop/tail 진입에서는 임의 A4를 보존한다. 지원된 RAM/PVC 접근은 기존 am_write를 사용하며, RAM이 return slot과 겹치면 실제 쓴 값이 RTS target이다. 별도 scratch stack이나 return metadata로 바꾸지 않는다. helper는 video LONG3c0000만 제한적으로 포트 기록하며 일반 am_write의 MMIO 범위를 넓히지 않는다. 지원 밖 장치·주소는 checked 오류다.

## caf0의 실제 여섯 호출

caf0 BSR.B ca9e는 returncaf2를 실제 RAM/A7에 push한다. caf2 LEA A4=3c0000 뒤 다음 다섯 rectangle을 기존35a2로 JSR한다.

| JSR PC / return | D0.low | D1.low | D2 | D3 |
|---|---|---|---|---|
| cb08 / cb0e | 7021 | 00ff | WORD38 | WORD30 |
| cb1c / cb22 | 701f | 7000 | WORD40 | MOVEQ1 |
| cb30 / cb36 | 7000 | 7000 | WORD40 | MOVEQ1 |
| cb44 / cb4a | 7000 | 7000 | MOVEQ1 | WORD32 |
| cb58 / cb5e | 74e0 | 7000 | MOVEQ1 | WORD32 |

표의38/30/40/1/32는10진수이고 D0/D1 열은16진수다.

WORD 쓰기는 상위WORD를 보존하며 MOVEQ는32bit 전체를 바꾼다. 각35a2는 watchdog BYTE300001, column-major video LONG, 종료WORD3c0004=0과 LONG3c0000=82000000을 순서대로 기록한다. tile BYTE를 증가시키는35f0과 혼동하지 않는다.5회 rectangle cell은1140+40+40+32+32=1284개, 각3개 부가 포트를 합쳐1299개다. 따라서 ca9e773개와 합친 정상 caf0의 ordered instruction-access 출력은2072개(워치독5/비디오2067)다. 물리 bus cycle이나 렌더링 픽셀 수가 아니다.

cb5e는 BYTE(A5-769a)=0을 쓰고 cb62에서 live RTS한다. A5를108000으로 고정하지 않고 기존 bus의 RAM mirror를 지원한다. 해당 BYTE가 실제 return LONG을 덮을 수 있으며 이 순서를 보존한다. 최종 D0=75807500,D1=00007000,D2=0,D3=32,D6=초기상위WORD|0,D7=75007000,A4=3c0000이며 D4/D5/A0..A3/A5/A6은 보존한다. 실제 stack writes와 A7/PC는 별도로 남는다.

## 47fca 이후 연결과 검증

47fca JSRcaf0는 return47fd0를 push한다.47fd0은 WORD(A6+7a)=32, LONG(A6)=47fdc를 순서대로 쓰고47fdc로 이어진다.47fdc의 SUBQ.W1과 뒤 BNE를 묶는다. 결과 비영이면480bc,0이면47fe4다. 따라서 같은 호출에서32가31로 감소한다. fresh timer0은ffff로 wrap하고1만47fe4로 간다.47fe4의 BSR477c2와480bc body는 이번 범위에서 실행하지 않는다. 이전47fa8 timer1→palette/flag clear→caf0는 실제 연결해 검증한다. 다음 frame을 host PC 변경으로 만들지 않는다.

확인한 LEA-only, JSR/BSR, RTS, 직접 DBRA-only block만 C를 보존하며 다른 새 block은 Unknown이다. 일반 CCR/XNZV는 미구현이고 flag-only47fe0 임의 진입은 거부한다. zero-step은 기존 상태 보존 계약을 따른다.

검증은 실제 ROM의 full64KiB RAM/16R/PC와 ordered ports, 독립 PVC/bank 모델 및 C++ 실제 출력 재개를 대상으로 한다.8개 MS5D v1 kind3와 실제 C++ loader를 유지한다. SR 읽기·ROM patch·예상 register 주입·stack mask를 사용하지 않는다. API 실패 시 출력 보존과 native CPU fault의 부분 효과를 구분한다. 자연 scheduler·IRQ/timing·일반 video/VRAM·직접플레이·전체 게임 복원은 미완료이며 구체적인 실행 결과는 별도 execution 문서에 기록한다.
