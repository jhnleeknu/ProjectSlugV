# 오브젝트 정리와 실제 중첩 스택 계약

Baseline `54a69c4`. Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인은299c..2aaa,271c..278e,287e..288a,477c2..477e2와 아래 helper의 실제 명령 bytes를 확인했다. 주소는 fixed CPU 주소이자 같은 ROM 파일 offset이다. 기존 object_removal/object_restart_execution의 의미 분석을 참고하되 저장된 register나 return을 metadata로 복원하는 API로 실제 A7 실행을 대체하지 않는다.

## 299c와 목록 연결

299c는 A5=108000으로 설정하고 watchdog BYTE300001에 당시 D0.byte를 쓴 뒤 BSR2782(return29ac)를 실행한다.2782는 JSR8ff4(return2788),JSRc3fa(return278e),RTS다. 이 호출들이 변경한 live RAM/register를 그대로 다음 단계에 전달한다.29ac은 LONG(A6)=270e를 쓰고 WORD(A6+10)를 검사한다.0이면 A0=A6 후271c로 tail BRA하며 추가 return을 만들지 않는다.

비영이면29c0 BSR287e(return29c4),BCS를 실행한다.287e는 A0=LONG(A6+8),D0.low=WORD(A6+10),CMP.W WORD(A0+10),D0,RTS다. unsigned D0.low가 다음 WORD보다 작을 때 CSet,그 외 CClear다.29c4는 Set이면29fe RTS,Clear이면 A0=A6 후 BSR271c(return29ce)다. Unknown C 입력은 checked 오류이며 false로 처리하지 않는다.

29ce 이후 순서는 A0=LONG(A6+4),A1=LONG(A6+8),LONG(A1+4)=A0,LONG(A0+8)=A1,LONG(A6+8)=LONG(A5-3364),LONG(A5-3364)=A6,WORD(A5-3360)++다. 그 뒤 A6=A0로 바꾸고 LONG(A6)==270e 및 WORD(A6+10)!=0이면29c0로 돌아간다. 각 read/write는 앞선 쓰기가 반영된 live RAM에서 수행한다. 연결 전체를 미리 복사하거나 free-list/count 값을 캐시하지 않는다. 일반 구조체 유효성 규칙을 추가해 원본이 읽지 않은 필드를 선검사하지 않는다. 비정상 순환은 기존 machine block 예산으로 제한한다.

2a0a는 D0.low=WORD(A6+10),A6=LONG(A6+8) 후2a12 CMP.W WORD(A6+10),D0를 실행한다.2a16 BCC는 CClear이면2a1e의 A6=LONG(A6+4),RTS로 가고,CSet이면 BSR299c(return2a1c),BRA2a0a다. 비교는 unsigned WORD다. 이 실제 writer/branch 쌍도 known C로 표현하며 임의2a16 Unknown 입력은 거부한다.

## 271c의 실제 reset 호출

271c는 JSR8eb6(return2722),JSR43dcc(return2728),JSRc3dc(return272e)를 순서대로 실행한다.

- 8eb6은 BYTE(A0+1d)=0 후 RTS한다.
- 43dcc는 A0+=2e,BSR43dda(return43dd4),A0-=2e,RTS다.43dda는 D0 전체0 후 LONG offsets10,0,4,8,c,14,18,1c,20와 WORD24를 이 순서대로0으로 쓴다. 내부 BSR/RTS도 실제 A7이다.
- c3dc는 LONG(A0+64)=0,WORD(A0+6e)=40,JSR4aa06(returnc3ec),JSRe90ca(returnc3f2),JSR46eec(returnc3f8),RTS다.4aa06은 D0 전체0,WORD54=0,LONG56=0,BYTE5e=0,WORD5a=ffff,BYTE60=0,BYTE17=ff,BYTE6d=ff,LONG72=0 순서다. e90ca는 BYTE6a=0,6b=ff,46eec는 BYTE6c=ff다.

272e 이후 D0=0,D1=-1, BYTE(A0+15/61/62/63)=0, BYTE12/13=ff,WORD1e=ffff를 순서대로 쓴다. A0+=76 후 LONG0을 postincrement로19회,마지막 WORD0을 쓰고 A0-=c2 후 RTS한다. 원본의 A0 변화와 LONG 분할 bus 쓰기를 유지한다. object reset 결과가 stack slot과 겹칠 때 실제 pop 값이 달라질 수 있다.

## 팔레트 해제 8ff4/8e4a

8ff4는 D7 전체0 후 BYTE(A6+1d)를 읽고 low WORD를1감소시킨다. 감소 전0이면9030의 count BYTE=0,RTS로 간다. 그 외 A1=A5-326e, 각 반복에서 D0 전체0 후 BYTE(A6+19+signed D7.W)를 읽고 LSL.W4,A2=A1+signed D0.W로 설정한다. WORD(A2+8)를 D1.low에 읽어0/ffff이면 건너뛴다. 그 외 같은 WORD를 live 감소시키고 결과0일 때만 BSR8e4a(return902c)를 실행한다.902c의 D7.low 감소에서 borrow가 없으면9004로 반복한다. count를 임의4개로 제한하지 않으며 중복 palette index도 순서대로 처리한다.

8e4a는 D2.low=WORD(A2),D3.low=WORD(A2+2),WORD(A1+signed D3.W)=D2.low,WORD(A1+signed D2.W+2)=D3.low,D2.low=1000,D3.low=WORD(A1+signed D2.W)를 순서대로 수행한다. 이어 WORD(A2+2)=D2.low,WORD(A2)=D3.low,WORD(A1+signed D3.W+2)=D0.low,WORD(A1+signed D2.W)=D0.low,WORD(A2+a/c)=ffff,BYTE(A2+f)=2,live RTS다. index와 list link는 WORD의 부호 확장을 적용하며 read/write 순서를 바꾸지 않는다. 실제 BSR return과 palette list가 겹칠 수 있다.

## 좌표 해제와 43e38

c3fa는 JSR46ef4(returnc400),RTS다.46ef4는 D0 전체0 후 BYTE(A6+6c)를 읽는다. bit7이1이면 RTS한다. 나머지 값8이상은 원본46f06 TRAP 경계다.0..7이면 MULU.W2c, A0=A5+54e6+signed D0.W,WORD(A0+26)=ffff,WORD(A0+2a)=2,BYTE(A6+6c)=ff,JSR43e38(return46f2c),RTS다. coordinate 주소는 그 시점의 A5로 계산한다.

43e38은 내부 호출이 없는 연산 묶음이다. A5=108000,D2/D3=LONG(A0+14/18),A1=LONG(A0+10),D0/D1=LONG(A0/4),D7=0을 순서대로 수행한다. A1!=0이면 D4/D5=LONG(A1+14/18)를 읽는다. D6.low=D1.low+D5.low의 carry를 첫 ADDX.W D7,D7에 넣고, D6.low=D0.low+D4.low의 carry를 두 번째 ADDX에 넣는다. 그 결과 D7.low는2*carryY+carryX이며 D6 상위WORD는 유지된다. D0+=D4,D1+=D5는32bit wrap이고 마지막으로 BYTE(A1+25)를 D7.byte에 OR한다.

BYTE(A0+25)=D7.byte, LONG(A0+14)=D0,LONG(A0+18)=D1를 순서대로 쓴 **뒤** BYTE(A5+5494)를 D5.byte,BYTE(A0+24)를 D4.byte에 읽는다. D4.byte==0이면 BYTE(A0+24)=D5.byte,LONG(A0+1c/20)=D0/D1이다. 비영이고 두 BYTE가 다르면 stamp를 갱신하고 LONG(A0+1c/20)=D2/D3,같으면 추가 쓰기 없이 반환한다. MOVEM의 register/메모리 접근 순서와 alias를 보존한다. local X 의미는 실제 인접 WORD 합산에서만 계산하며 일반 XNZV나 임의 ADDX PC 진입을 지원했다고 주장하지 않는다.

## Wrapper와 스테이지 호출

2a28은 WORD(A0+10)==0을 확인하고 실제 LONG A6,A1,A0를 차례대로 push한다. A6=A0,JSR299c(return2a40),live pop A0,live pop LONG을(A0)에 쓰기,live pop A6,RTS다.2a48은 같은 type0 확인 뒤 A6만 push,A6=A0,BSR299c(return2a5c),live pop A6,RTS다.

2a60/2a84는 현재 A6의 WORD+10과 대상 A0의 WORD+10을 순서대로 검사하며 비영이면 각각 원본 TRAP 경계에서 거부한다. A6를 push하고 A6=A0 후2a0a를 실제 호출한다.2a84만 추가BSR299c(return2aa8)를 실행한다. 끝에서는 live pop A6,RTS다.2a00의 scheduler stack 전환과2a24는 이번 범위 밖이다.

477c2는 JSR2a0a(return477c8),A0=100bf4,JSR2a84(return477d4),D0=0,JSR8bbc(return477dc),JSR3dce(return477e2),RTS다.8bbc는 BYTE(A5-214)=D0.byte다.3dce는 BYTE(A5-326f)의 bit4를 clear하고 A0=3dcc,LONG100006=A0,LONG10000a=A0 후 RTS한다.47fe4 BSR477c2의 return은47fe8이며 이 **LEA48108 실행 전**이 새 상위 경계다.

MOVE.L register,-(A7)는 MOVEM과 달리 CCR에 영향을 주므로 C 보존 block으로 분류하지 않는다. 실제 JSR/BSR/RTS,LEA/MOVEA/ADDA/SUBA 및 확인한 BRA/BCC/BCS-only 조합만 C를 보존한다. 나머지는 보수적으로 Unknown이다. 기존 screen unit/verifier의 명시적 미지원 경계 검사는47fe4에서 아직 지원하지 않는47fe8로 옮기며 실패 출력 보존 검사는 유지한다.

## 증거와 한계

반복되는29c4/2a16의 carry 증거는 PC별 마지막 값이 아닌 실행 순서의 실제 branch occurrence로 기록한다. Split endpoint의 global trace 위치에서 바로 다음 원본 successor를 확인한다.287e의 return을29c4로 둔 fixture는 통제 adapter이며 자연 caller 도달성 증거로 부르지 않는다. SR 읽기·ROM patch·중간 register 주입·stack diff mask를 사용하지 않는다.

full64KiB RAM/16R/PC, ordered watchdog/PVC/video 접근, 외부읽기·장치/bank와 실제 C++ 출력 재개를 검증한다. 기존 MS5D v1 kind3와 C++ loader를 유지하며 원본·리소스 형식을 변경하지 않는다. 오류의 API 출력 보존과 native fault 부분 효과는 구분한다. 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체스테이지/적/보스·미사용 전체 의미는 미완료다.
