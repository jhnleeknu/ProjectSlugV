# 장면 설정의 실제 스택 통합 계약

Baseline `8db0a9e`. Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 fixed CPU 주소이며 같은 ROM 파일 offset이다. 메인이 실제 원본 bytes와 기존 scene_setup의 제한을 확인해 정리했다. 이 문서는 구현·원본 동등성 완료 보고가 아니다. ROM patch, SR 읽기, 중간 register 예상값 주입을 금한다.

## 범위와 리소스

47fe8의 LEA48108과47fec JSR43ffc(return47ff2),43ffc..44094의 descriptor 처리,43f3e reset 및 실제 callees를 연결한다.47ff2 JSR e7c36은 다음 미지원 경계다. 기존 여덟 MS5D v1 kind3를 C++ loader/bus로 읽는다.48108의 실제12byte `0008 0002 0010 d256 0000 0003`는 type2 node10d256과 terminal이다. 기존 descriptor kind1 pack 목록과 이미 존재하는 전체 physical kind3의 포함 여부를 혼동하지 않는다.

기존 `setup_scene_resources`는12R와 vector에 저장한 suffix pointer를 사용하는 별도 API다. 이를 호출해서 실제 공유 RAM/A7 동작을 대신하지 않는다. 새 실행은 원본이 읽는 bus 주소를 그때 읽으며 descriptor를 미리 decode/copy하지 않는다. 원본의 signed stride, RAM/stack alias, 메모리 변경 후 pop을 보존한다. 원본이 하지 않는 exact descriptor/window/전체 node span 선검사를 추가하지 않는다. 기존 machine checked access와 operation budget을 사용한다.

## 43ffc의 descriptor 순서

43ffc A5=108000;44002 MOVE.L A0,-(A7);44004 BSR43f3e(return44008);44008 MOVEA.L(A7)+,A0.4400a CMPA.W#0,A0는 sign-extended immediate0와 full32 A0를 비교하며 low WORD 검사로 축약하지 않는다.0이면44086으로 간다.

44012 BYTE(A5+549a)=ff;D0.low=WORD(A0+2). type0이면44032로,3이면44086으로,나머지는4402c BSR43f5c(return44030) 후44012로 반복한다.44032는 ADDA.W(A0),A0, D7 전체0,BYTE(A5+549a)=0, MOVEM.W(A0),D0-D1이다. MOVEM.W는 두 register 전체에 각각 부호 확장한다.

44040 CMP.W#3,D1: equal→44072, unsigned lower→44066, greater→4404c TRAP.44066 MOVE.L A0,-(A7);D7.low++;A0+=signed D0.W;MOVEM.W(A0),D0-D1;BRA44040. 원본 수집기는 type0도 lower로 수집한다. 기존 API의 suffix0 선거부와 원본 처리시점은 다르므로 그대로 복사하지 않는다.

44072 TST.W D7;44074 BEQ44086. 비영이면44078 live pop A0;D7.low--;4407c MOVE.W D7,-(A7);4407e BSR43f5c(return44082).44082 MOVE.W(A7)+,D7;44084 BRA44074. 여기 BEQ가 소비하는 Z는 바로 앞 MOVE.W에서 온다. arbitrary44074 진입은 public state에 Z가 없으므로 거부한다.44072의 TST/분기와44082의 pop/BRA/분기를 각각 함께 처리하면 실제 호출 이후 saved WORD가 바뀐 경우도 보존할 수 있다. WORD stack stride는2이고 D7 상위WORD는 pop에서 유지된다.

44086 BSR4410c(return4408a);4408a MOVE.W#0,D0;4408e JSRcd1c(return44094);44094 live RTS. 각 BSR/JSR/PEA/MOVE push와 RTS/MOVEA/MOVE pop은 실제 RAM/A7이다. 원래 저장한 pointer/register를 host metadata로 복원하지 않는다.

## 레코드 43f5c와 slot 할당

43f5c MOVEM.W(A0),D0-D1;43f60 PEA(A0,signed D0.W). type1이면D0.low=WORD(A0+4),43f70 BSR440c8(return43f74),D0.low!=0이면43f7c TRAP.0이면43f92 MOVEQ1,D0;43f94 JSRcd1c(return43f9a);BRA43ff8.

Type2이면D0.low=20;43faa BSR440c8(return43fae);D0.low!=0이면43fb6 TRAP.0이면43fcc MOVE.W D1,-(A7),43fce A0=LONG(A0+4),43fd2 MOVE.W(A7)+,D0;43fd4 JSR16f9a(return43fda);BRA43ff8. Pushed WORD가 descriptor operand와 겹치면 뒤의 LONG read가 바뀐다. 다른 type은43fde TRAP.43ff8 live pop A0;43ffa live RTS.

440c8 BYTE(A5+549a)==0이면 아래 경계 할당: D1.low=WORD(A5+5496),D3.low=WORD(A5+5498),D2.low=(D1.low+D0.low) mod65536. unsigned D2.low>=D3.low이면D2.low=D3.low. WORD(A5+5496)=D2.low;D0.low=(D0.low-D2.low+D1.low) mod65536;RTS440ec.

BYTE비영이면 위 경계: D2.low=WORD(A5+5498),D3.low=WORD(A5+5496),D1.low=(D2.low-D0.low) mod65536;unsigned D1.low<D3.low이면D1.low=D3.low. WORD(A5+5498)=D1.low;D0.low=(D0.low-D2.low+D1.low) mod65536;RTS4410a. 중간 wrap을 생략한 넓은 정수 clamp로 바꾸지 않는다.

4410c D1.low=WORD(A5+5496),D2.low=WORD(A5+5498),WORD(A5+5496)=D2.low,D0.low=D2.low-D1.low;RTS4411c.

cd1c A4=A5+0d3e;D0.low!=0이면A4=A5+0d46. unsignedD1.low>=017c이면D1전체=ffffffff;그 뒤unsignedD1.low>=D2.low이면D2전체=ffffffff. SWAP D1;D1.low=D2.low;LONG(A4)=D1;LONG(A4+4)=D1;RTScd46. 두 쓰기는 순서대로 수행한다.

## Reset과 뱅크

43f3e JSRccd6(return43f44),JSR1ad9a(return43f4a),BSR43efa(return43f4c),WORD10d496=0,WORD10d498=017c,RTS43f5a.

ccd6 BSRcd48(returnccda).cd48 LONG(A5+1152)=cd50;RTScd50. ccda D0전체0,BYTE(A5+d3d)=0,LONG(A5+d34)=0,WORD(A5+d38/d3a/114e/1150)=0;A0=A5+b34;D7.low=ff. ccfc반복은 WORD(A0)=D0.low를 쓰고 A0를2증가하고 D0.low+=c,DBRA D7→ccfc. 종료 D0전체0,D1/D2전체ffffffff,JSRcd1c(returncd10);D0전체1,D1/D2전체ffffffff,JSRcd1c(returncd1a);RTS. 이 과정은 MOVE.W D0,(A0)+이며 메모리 값을 더하는 연산이 아니다.

1ad9a WORD(A5-7ff0)=1,WORD2ffff2=2000,WORD2ffff0=0, A0=109156,JSR1adf0(return1adba),A0=10b1d6,JSR1adf0(return1adc4),A0=10d256,JSR1adf0(return1adce),A0=10d2d6,JSR1adf0(return1add8). 마지막WORD(A5-7ff0)=0,WORD2ffff2=1000,WORD2ffff0=0;RTS1adee.1adf0 MOVEQ-1,D0;JMP16f9a는 tail call이다.

PVC raw storage와 장치 모델의 side effect를 구분한다. 각 실제 WORD write 뒤 독립 PVC 모델이 계산한 bank를 사용한다. Native 관측은 bank2 고정 backing을 유지한 채 bank3 읽기를 주장하지 않는다. 원본 fixed 코드와 bank data는 불변이며 backend의 장치 remapping을 ROM patch로 부르지 않는다. 실제 banked code 실행은 별도 검증 전까지 범위 밖이다.

43efa A4=3c0000;D7=82010000,D6=8401f000,D5=8001ffff,D4=00010000;D0.low=017b.43f1a반복 순서는 LONG(A4)=D7;D7+=D4;watchdog BYTE300001=D0.byte;LONG(A4)=D6;D6+=D4;watchdog;LONG(A4)=D5;D5+=D4;watchdog;DBRA D0. 기본380반복이며 최종lowffff. 실제 A4 bus대상을 유지하고 unsigned32 wrap을 사용한다. RTS43f3c.

## Node helper16f9a

16f9a WORD(A0+26)=D0.low;16f9e BSR1829a(return16fa2);16fa2 BSR1701a(return16fa6);16fa6 BSR182d0(return16faa);16faa RTS.

1829a D7.low=WORD(A0+26);negative WORD이면182ce RTS. 그 외A1=3c0000,D6.low=03ff,D7.low=(D7.low+1)<<6 mod65536,SWAP D7,CLR.W D7.182b4반복 LONG(A1)=D7;D7+=10000;LONG(A1)=D7;D7+=10000;DBRA D6. 종료watchdog BYTE300001=D0.byte;RTS182ce. 기본1024반복, 직접DBRA 초기ffff도65536반복인 원래 WORD 의미를 보존한다.

1701a BYTE(A0+7a)&=fe 후D7.low=WORD(A0+26);negative면1724a RTS.그 외watchdog BYTE300001=D0.byte,D6.low=D7.low,D7.low+=8201,D6.low+=8001,SWAP D7/D6,D6.low=0fff,D7.low=8000,D5=10000.1704a..17248은 정확히32개의 unrolled쌍:LONG3c0000=D7;D7+=D5;LONG3c0000=D6;D6+=D5.1724a RTS. 반복 횟수를 register에서 가져오지 않는다.

182d0 D0전체0,A1=A0+3a,D0.low=0;WORD(A1)=D0.low를32회 순차쓰기(매번 A1 postincrement2)하고1831a RTS. 원본은64바이트를 WORD접근으로 지운다. LONG/memset으로 바꿔 access·late-error·stack alias 의미를 지우지 않는다.

## 실행 경계와 증거

실제 call/return, pop 직후와 지원하는 loop 경계를 명시적으로 분리한다. 테스트 checkpoint가 해당 block을 실행한 다음 실제로 도달하는 PC인지 확인한다. 임의 Z-only분기 진입은 거부하며 실제 선행 writer와 합친다. 본 범위는 새 known-C공개를 요구하지 않는다. 명령으로 확인한 JSR/BSR/JMP/BRA/RTS/LEA/MOVEA/PEA/ADDA/DBRA-only block만 C를 보존하고 나머지는Unknown이다.

전체64KiB RAM/16R/PC·실제A7·orderedports·rawPVC/독립device/bank·reads/status를 비교한다. 이전 실제 C++ 출력으로 split재개하며 freshcontinuous 원본도 같은 checkpoint를 통과해야 한다. 기존12R API의 성공은 이 증거를 대신하지 않는다. Native fault부분효과와 checked API rollback을 구분한다. 이 계약은 전체 게임·스케줄러·IRQ/timing·일반CCR 완료를 주장하지 않는다.
