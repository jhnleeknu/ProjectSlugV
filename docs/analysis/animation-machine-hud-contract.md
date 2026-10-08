# HUD·BCD의 실제 호출 스택 연결 계약

Baseline `24d13ff`. Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 fixed CPU 주소이며 ROM 파일 offset과 같다. 메인은 원본 `47c6c..47cae`, `4843c..4847c`, `4e286..4e332`, `8cda..8d34`, `35f0..362a`의 bytes와 명령을 확인했다. 이 문서는 구현 계약이며 실행 대조 완료 여부는 별도 execution 문서에 기록한다.

## 상위 흐름

47c6c는 BYTE(A5+5684)가 비영이면 기존47d3e readiness 호출로 간다. 0이면 D0=0, D0.low=WORD(A5+567e), 실제 JSR4e286(return47c80)을 실행한다. 반환 후 같은 WORD를 다시 읽어 0이면47eac, 아니면 BSR4843c(return47c8c), JSRca70(return47c92)을 차례로 실행한다. ca70이 반환한 A0의 live WORD가0이면47d24다. 그 외 두 status BYTE(A5+7db6/+7db7)를 각각1과 비교한 ff/00을 D0/D1.byte에 넣고 OR.B 한다. 비영이면47d24,0이면 기존47cae 활성화 경로로 간다. 두 status는 short circuit하지 않는다.

47eac/47d24와 readiness 후47d46/47d72는 이번 단위의 실행 전 경계다. 중간 return 위치를 호스트 continuation 값으로 대체하지 않는다.

## HUD와 실제 WORD 저장

4e286의 gate·숫자·사운드·팔레트 의미는 `stage-hud-counter-contract.md`를 따른다. 새 실행기는 실제 A7과 공유 RAM을 사용한다. 사운드 호출 전 WORD D0를 push하고 JSR3af8은 LONG4e2ce를 push한다. 복귀 후 BYTE(A5+5d20)=1f를 먼저 쓰고 live WORD를 pop한다. 대기 중 원본 스택이 바뀌면 복원값도 바뀐다.

팔레트 호출은 WORD D0 저장, D0=12와 D1.low=0a0d, JSR8cda(return4e2f0), live WORD pop 순서다. 팔레트 slot12와 스택이 겹치면 실제 쓰기가 저장값과 복귀값에 영향을 줄 수 있다. 원본에 없는 스택 보호나 RAM diff mask를 사용하지 않는다.

통제 조건 A7=104e62에서는 saved WORD가 slot12+e/+f, JSR return LONG이 slot12+a..+d와 겹친다. reference가 비영이면 target+c에0a0d를 쓰면서 return0004e2f0가00040a0d로 바뀐다. 원본 관측은 pop4e2f0 이전에 잘못된 복귀 주소로 간다. 따라서 이를 정상 숫자 복원 사례로 분류하지 않는다. C++는 홀수 PC를 checked 오류로 거부하고 해당 호출의 모든 출력을 보존해야 한다. 원본 fault가 RAM 쓰기를 되돌린다는 뜻은 아니다.

첫 숫자 출력은 LSR.W8 후 WORD 저장, LSR.W4/ADD.W로 첫 index 계산, raw ROM4e272 lookup, SWAP, D0.low=7243/D2=D3=2, JSR35f0(return4e312)이다. 반환 시 live WORD를 pop해 low nibble index로 두 번째 lookup을 하고 D0.low=7283/D2=D3=2에서35f0으로 tail JMP한다. Tail JMP에는 가짜 return을 push하지 않는다. 99ff를 넘는 입력의 특수 출력도35f0으로 tail JMP한다.

표의 raw 읽기 span은[4e272,4e292)이다. 인덱스10..15는 코드 bytes를 읽을 수 있다. 새 machine은 기존 전체 프로그램 MS5D v1 kind3 리소스와 C++ bus/loader를 사용한다. 명목상10개 숫자로 자르거나 비BCD 입력을 정규화하지 않는다.

## BCD·팔레트와 출력

4843c의 raw source0 SBCD 규칙과 독립 기준은 `stage-counter-contract.md`를 따른다. SUBQ.B2의 borrow를 SBCD에 연결하며 underflow 때 D0/D1 전체32bit를 지운다. 그 외 상위24bit를 유지한다. high BYTE 다음 low BYTE를 쓰고 live RTS한다. 기존 standalone의 exhaustive 검증과 새 공유 스택 검증은 별개 증거다.

8cda는 D0.low를 ff로 mask하고4bit 좌측 이동해 A1=104d92, A2=A1+signed D0.low를 만든다. slot reference WORD+8이0이면 반환한다. 비영일 때 D2.byte>=20이면 MOVEQ20으로 전체 D2를 바꾼다. target WORD+c가 D1.low와 다르면 target, weight BYTE+e, dirty BYTE+f bit7을 순서대로 쓴다. 같으면 weight 차이를 검사해 필요 시 weight를 쓰고 source WORD+a가 D1.low와 다를 때만 dirty bit7을 세운다. BSET은 live BYTE read/modify/write다.

35f0은 A4=3c0000을 설정하고 D0.low/D1.low로 D7을 만들며 D6.low=D3.low를 유지한다. 셀마다 unsigned D7>=75000000이면 원본 TRAP15 경계에서 checked 오류다. 그 외 LONG D7 출력, D7+=10000, D7.byte+=10, D6.low--를 수행한다. 열 끝에 D1.byte++, D0.low+=20, D2.low--를 수행한다. 최종 WORD8200 출력 뒤 실제 RTS한다. 각 폭의 wrap과 상위 비트를 유지하고 반복은 machine block 예산 안에서 수행한다. 0인 폭·높이도 원본 WORD 감소 의미를 따르므로 TRAP/예산 오류가 날 수 있다.

비디오 출력은 기존 `VideoPortWrite`와 동일하게3c0000의 LONG 한 건(size4), 최종 WORD 한 건(size2)을 순서대로 기록한다. 이는 명령 접근 단위 trace이며16bit 물리 bus cycle 수를 주장하지 않는다. PVC는 기존 WORD 단위 trace와 독립 모델을 유지한다. 새 비디오 helper는 live A4의24bit 주소가3c0000일 때만 이 출력 형식을 사용한다. 다른 주소는 기존 RAM/PVC write 계약이나 checked unsupported 오류를 따른다. 비디오 readback·VRAM 장치 상태·IRQ/timing 구현을 뜻하지 않는다.

## Carry·검증 경계

새 block의 C는 보수적으로 Unknown이다. 확인한 JSR/BSR, 독립 RTS, LEA-only35f0 block만 입력 C를 보존한다. BCD 내부 borrow나 LSL.B3의 carry는 해당 분기의 실제 계산에 사용하되 일반 CCR을 지원했다고 주장하지 않는다. 기존 readiness의 실제 C writer와 BCC 계약은 유지한다.

원본 비교는 ROM patch·중간 예상 레지스터 주입·SR 읽기 없이16RAM mirror, 전체64KiB RAM,16레지스터/PC, ordered PVC/video events와 대기를 관측한다. 분할 실행은 fresh 연속 실행과 대조하며 C++ 재개는 직전 실제 출력으로 수행한다. API 실패의 전체 출력 보존은 원본 CPU fault rollback과 구분한다. 자연 scheduler 도달성·직접 플레이·전체 스테이지 복원은 이 단위의 완료 주장에 포함하지 않는다.
