# Readiness의 실제 호출·carry 계약

Baseline `93b5b40`. Canonical BE 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 fixed CPU 주소는 같은 ROM 파일 offset이다. 메인이 원본4847c..484b4,1bdde..1be3a,289e..28ae,4dee2..4df1a,4e166..4e186과47d20..47d46을 직접 읽어 기존 collapsed readiness API와 대조했다. 이는 구현 계약이며 실제 대조 결과는 별도 execution 문서에 기록한다.

## 상위 호출과 실제 분기

47d20은 BRA47d3e,47d3e는 PC-relative JSR4847c(return47d42),47d42는 BCC47d72이다. Set이면 fallthrough47d46이다. 이 세 block은 C를 보존한다. Unknown인 채47d42에 진입하면 checked 오류다. 선택한 successor 명령을 실행하기 전 stop한다.

4847c는 MOVEQ0 D0 후4847e에서1bdde를 JSR하고48484에서 반환C를 읽는다. Clear이면484ae로, Set이면48488의 MOVEQ1 D0와4848a의 두 번째1bdde JSR를 거친다. 두 번째 return48490에서도 Clear이면484ae다. 양쪽 Set일 때만48494에서 live BYTE(A5+5684)를 읽고 비영이면484a8,0이면4849c의4e166 JSR(return484a2)로 간다.484a2는 D0.byte를 TST하고0이면484ae,비영이면484a8이다.

484a8 ORI CCR1은 C=Set,484ae ANDI CCRfe는 C=Clear로 만든 뒤 실제 RTS를 실행한다. 직접484ac/484b2 RTS 진입은 입력 C를 보존하며 앞선 writer가 실행됐다고 추측하지 않는다.

## 하위 helper와 stack alias

1bdde는 A0=A5−7348, D0.low&=1을 계산하고 선택1이면 A0=A5−7258로 바꾼다.1bdee JSR289e는1bdf4를 실제 RAM stack에 쓴다. 이 LONG 쓰기가 player marker와 겹치면289e는 **변경된 marker**를 읽어야 한다.

289e는 LONG(A0)와270e를 비교한다. 같으면 CMP의 C=Clear 상태로 RTS한다. 다르면28a8 ORI CCR1을 실제 거쳐 Set으로 RTS한다. 직접28a8은 Set을 만들고 직접28ac RTS는 입력 C만 보존한다.

1bdf4 BCC는 Clear이면1be2e로 간다. Set이면1bdf8에서 live BYTE(A0+a8) bit4를 읽어1이면1be2e,0이면1be02에서 live BYTE(A0+61) bit7을 읽는다. bit7=1이면1be34,0이면1be0c JSR4dee2(return1be12)다.1be12 BCC는 Clear이면1be2e,Set이면1be16의 D1.byte CMP3/4/5를 거친다. 셋 중 하나면1be34,그 외1be2e다.1be2e ORI는 Set,1be34 ANDI는 Clear로 반환한다.1be32/1be38 직접 RTS는 C를 보존한다. BTST와 그 조건부 분기는 Z만 바꾸므로1bdf8/1be02는 C를 보존한다.

4dee2는 A4=A5+5d12, D0.low&=1을 계산하고 선택1이면A4=A5+5d18로 바꾼다. live WORD(A4+4)가 음수이면4df0a ANDI에서 Clear로 반환한다. 그 외 live BYTE(A4)가1/2일 때만 BYTE(A4+2)를D1.byte에 읽고4df14 ORI에서 Set으로 반환한다. 다른 type은Clear다. D1의 상위24bit를 보존한다. 내부JSR가 없는 leaf 전체를 묶되 접근 순서와 실제RTS 읽기를 유지한다. 직접4df0a/4df10 writer block과4df0e/4df18 RTS도 구분한다.

4e166은 D0=0, live BYTE(A5−75bc)==2이면D0.low|=1, 이후 live BYTE(A5−74f8)==2이면D0.low|=2다. 실제RTS를 수행하며 block 반환C는 보수적으로 Unknown이다. 마지막 CMPI/조건부ORI의 C를 mask 값과 동일시하지 않는다. 상위484a2는 C를 읽지 않고 새 TST 결과를 사용한다. 직접4e184 RTS는 입력C를 보존한다.

## 실행 경계와 검증 기준

모든 JSR/RTS는 공유RAM A7을 사용한다. 새 read/write는 기존24bit bus와32bit register wrap 계약을 따르며 standalone API의 canonical RAM 제한을 임의로 이식하지 않는다. 확인된 entire block만 C를 보존하고 나머지는 Unknown으로 시작해 실제 writer에서만 known C를 설정한다. Unknown을 false로 소비하지 않는다.

원본 C 기대값은 실제47d42 BCC successor로 판정한다. Return 경계에서 멈춘 실행과 fresh CPU의 연속 실행을 비교하고, SR을 읽거나 expected register를 실행 중 주입하지 않는다. Standalone helper return을47d42로 놓는 조건은 명시적 통제 adapter이며 자연 호출 관계의 증거가 아니다. 대기와 연결되는47cae 경로도 같은 CPU/실제 이전 C++ 출력으로 재개한다.

원본 bytes·자원·스택 차이를 바꾸거나 가리지 않는다. 오류 시 전체 API 출력 보존과 native CPU exception은 별개다.47d46/47d72 이후 동작, 선행 HUD/BCD, 자연 scheduler·IRQ/timing·일반 CCR/XNZV·전체 stage 완료는 남은 범위다.
