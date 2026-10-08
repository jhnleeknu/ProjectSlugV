# 카운터 종료·후속 콜백의 공유 스택 계약

Baseline `21d818c`. Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 fixed CPU 주소이며 같은 canonical ROM 파일 offset이다. 뱅크 창의 주소로 취급하지 않는다. 이 문서는 원본 의미에 대한 구현 계약이며 실행 검증 결과는 별도 execution 문서에 기록한다.

## 47eac 초기화와 실제 애니메이션 호출

47eac은 WORD(A6+1e)=ffff 후 JSR16ed2(return47eb8)를 실행한다. 이어 BYTE(A6+12)=ff, BYTE(A6+14)=4, WORD(A6+42)=a0, WORD(A6+46)=180, WORD(A6+20)=ea를 쓴다.47ed6 MOVEA.L은 A1=48980으로 설정하고 D0.low=100 후 JSR49f8c(return47ee6)를 실행한다. 실제 ROM48980을 읽으며 다른 script로 교체하지 않는다. WORD 좌표42/46을 다시 a0/180으로 쓰고 timer7a=5a, JSR1c63c(return47efe), LONG(A6)=47f04, 기존47f04 JSR49fc6(return47f0a)으로 이어진다.

47f0a의 TST.W(A6+7a)가0이면47f1a, 아니면 같은 WORD를 다시 읽고1감소시킨 후47f3e BRA480bc다. 시작값1은0으로 감소해도 이번 호출에서는 플레이어 flag를 읽지 않는다.0 경로는 D7 전체를0으로 만들고 A0=A5-7348과 A5-7258 순서로 각각 BYTE(A0+61)의 bit7을 읽는다. 두 SNE.B는 D0 상위24bit를 보존하며 OR.B 결과가 D7에 남는다. 두 읽기는 모두 실행된다. 비영이면480bc, 모두0이면47f42 BSR48398(return47f46), BRA47c5a다.47c5a는 BYTE(A6+7e)=ff, WORD(A6+20)=ea, LONG(A6)=47c6c를 순서대로 쓰고 기존47c6c로 간다.

1c63c는 absolute A0=100cb8, JSR289e(return1c648), 실제 BCC를 실행한다. Set일 때만 BYTE(A0+a8)에 bit1을 세우고 BYTE(A0+5e)=6을 쓴다. 이어 absolute A0=100da8에 같은 처리(return1c664)를 수행하고 live RTS한다.289e의 marker270e 비교와 실제 C writer를 재사용한다. JSR가 marker와 겹치면 새 return LONG이 marker를 바꾼다. 호출 전 marker를 미리 저장하거나 A5-relative 주소로 대체하지 않는다.

## 실제 lookup과 사운드 호출

48398은 JSR30f4(return4839e), BYTE(A5+567e)=D0.byte, BYTE(A5+567f)=ff, live RTS다.30f4는 absolute BYTE10fd8c를 D0.byte로 읽고 ANDI.W7을 수행한 뒤 PC-relative table30ec의 index D0.W에 해당하는 BYTE를 읽는다. D0 상위WORD는 보존하며 table8BYTE는 실제 MS5D kind3 program bus에서 읽는다. 난수 생성으로 추정하거나 별도 상수표로 바꾸지 않는다.

47f4a는 D0.low=1890/1891/1892를 차례대로 쓰고 각각 JSR3af8(return47f54/47f5e/47f68)를 실행한다. JSR3c84(return47f6e)는 BYTE(A5-3282)를0으로 쓴다. JSR3d44(return47f74)는 D0.byte=08 후 BSR3ac8(return3d4c), D0.byte=20 후 BRA3ac8로 tail 호출한다. 각 BYTE 쓰기는 그 시점의 상위24bit를 유지하며 기존 사운드 callee의 register 변경도 그대로 적용한다. tail BRA에 가짜 return을 추가하지 않는다.

47f74 MOVEM.L D0,-(A7)는 D0 전체32bit를 실제 RAM에 저장한다. D0.low=19dc 후 JSR3af8(return47f82)을 호출하고47f82 MOVEM.L (A7)+,D0는 live LONG 전체를 읽는다. 대기 중 saved LONG 변경은 상위WORD까지 다음 D0에 반영된다. metadata의 이전 D0를 복원하지 않는다.47f86의 실제 CMPI.B0과 BNE를 함께 처리해 D0.byte가0일 때만 D0=0,D1=D2=-31,D3=32 후 JSR8c16(return47f9c)을 실행한다.

47f9c는 WORD(A6+7a)=32와 LONG(A6)=47fa8을 순서대로 쓰고47fa8으로 진행한다. 따라서 같은 호출에서 timer32가31로 감소한다.47fa8은 SUBQ.W1과 BNE를 함께 처리한다. 결과 비영이면480bc,0이면 D0=D1=D2=-31,D3=32, JSR8c16(return47fbe), JSR4e24e(return47fc4), JSRca7e(return47fca)다.4e24e는 BYTE(A5+5d1f),ca7e는 BYTE(A5-769b)를 각각0으로 쓰고 live RTS한다. 시작 timer0은ffff로 wrap하여480bc로 간다.

최종 경계는 **47fca의 JSRcaf0를 실행하기 전**이다. caf0 body와 caller 후속 흐름은 이번 범위에 포함하지 않는다.480bc에서 PC를47fa8로 바꿔 자연적인 다음 frame이라고 주장하지 않는다. 늦은 callback 검사는 명시적인 fresh 초기 상태로 준비하고, 실제 sound/animation 대기 재개와 구분한다.

## 8c16 leaf와 live A7

기존 `execute_palette_effect`는8c16 전체 leaf의8D/7A와64KiB RAM 효과를 구현하며 내부 JSR가 없다. 새 adapter는 모든15register를 전달·회수하고 같은 RAM에 결과를 적용한 **뒤** 현재 A7의 LONG을 읽어 RTS한다. A7은 leaf 입력 구조에 숨겨서 복원하지 않으며 palette write가 return slot을 바꾸면 바뀐 값이 실제 return target이다.

8c16은 A5=108000으로 교체한다. D0..D2 signed WORD를±31로 제한하며 범위 밖 MOVEQ는 상위bit까지 바꾼다. 범위 안 값은 상위WORD를 보존한다. 각각 LSL.W8 후 WORD107dc8/dca/dcc에 쓰고 D3.low&=ff,2미만이면 D3.byte=1, BYTE107dd4에 duration을 쓴다. 각 WORD에서107dc2/dc4/dc6을 빼고 세 결과의 OR.W가0이면107dd4=0 후 반환한다. 아니면 D3 전체를 duration1..255로 만들고 각 signed WORD를 EXT.L/DIVS.W 처리해 quotient와 remainder를 원본 폭으로 묶고 low WORD를107dce/dd0/dd2에 쓴다. 이 전체 진입에는 divide-by-zero/quotient overflow가 없다. 일반 IRQ·시간·중간 instruction checkpoint는 이 leaf adapter의 범위가 아니다.

## 상태·검증 경계

실제 JSR/BSR/BRA/BCC/RTS, MOVEA/LEA-only, 두 MOVEM-only block만 C를 보존한다.1c648/1c664는 기존289e가 만든 known C를 소비하며 Unknown 입력은 실패한다. 다른 새 block과 전체8c16 adapter는 보수적으로 CUnknown이다. Z-only PC에 임의 진입을 지원하지 않는다. 해당 분기는 실제 비교·감소와 묶고 일반 CCR 지원으로 확대하지 않는다.

원본과 C++의 full64KiB RAM,16R/PC, ordered ports, external reads, 독립 PVC/bank 모델을 비교한다. 원본은 초기 설정 후 SR 읽기·ROM patch·중간 예상 register 주입·stack mask를 사용하지 않는다. C++ 재개는 직전 실제 출력과 명시한 RAM 변경을 사용한다. API 실패 시 전체 출력 보존은 원본 CPU fault rollback과 구분한다.8개 MS5D v1 kind3와 실제 C++ loader를 재사용하며 리소스 형식을 변경하지 않는다.

자연 scheduler·IRQ/timing·일반 CCR·caf0/477ee/47da4/480bc의 후속 body·직접 플레이·전체스테이지/적/보스·미사용자료 전체 의미는 미완료다. 이 국소 계약을 전체 게임 복원 완료로 취급하지 않는다.
