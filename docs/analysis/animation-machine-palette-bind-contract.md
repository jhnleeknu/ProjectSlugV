# 팔레트 연결과 맵 노드 준비의 실제 스택 계약

Baseline `5cb6256`. Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. fixed CPU 주소는 같은 ROM 파일 offset이며, banked CPU 주소는 아래에 별도로 physical offset을 명시한다. 메인이 원본 bytes·호출·분기·자료구조 쓰기 순서를 확인했다. 이 계약은 구현/원본 동등성 완료 보고가 아니다.

## 범위와 리소스

47ff2 JSR e7c36부터 팔레트 연결,bank2 lookup,16fac 노드 초기화,16ff8 descriptor 설정까지 실제 공유 RAM/A7으로 연결한다.48042 JSR1861a(맵 갱신)는 다음 실행 전 경계다. 일반 맵 갱신·화면 표시 완료를 주장하지 않는다.8e82/8da2와e7bf4/e7c36를 새 실행부로 구현하고 기존8e4a cleanup/8cda HUD/43dda clear의 실제 stack 실행을 재사용한다. 기존3R/9R API를 host register 저장·복구 adapter로 사용하지 않는다.

기존 여덟 MS5D v1 kind3와 C++ loader/bus를 사용한다. 별도kind1 창에 없다는 이유로 새로운 형식이나 사전 decode 결과를 만들지 않는다. 실제bank2에서 CPU20000c(physical20000c)의LONG=2003d0, CPU2004c0(physical2004c0)의LONG=201ec0이며, 그binding의8byte는 `0080 1436 0000 ffff`다. C++에서는 이 값을 상수로 대신하지 않고 원본 접근 시점에 bus를 읽는다. fixed480f2의8byteheader는 `003c 0000 0014 0010`이다. 이번 caller는480f2 주소만 전달하며 header payload를 읽었다고 주장하지 않는다.

## 8e82: 기존 고정 팔레트 해제

8e82 watchdog BYTE300001=D0.byte;8e88 A1=104d92,A2=A1,D0전체0,D7.low=00ff.8e96은 WORD(A2+8)==ffff인지 검사한다. 같으면8ea0 WORD(A2+8)=0,8ea6 BSR8e4a(return8ea8)를 실행한다. 그 외8ea8로 간다.8ea8 A2+=10;D0.low+=10;DBRA D7→8e96,종료8eb4 RTS.

D7 상위WORD는 유지되고 기본256entry를 처리한다.8e4a는 기존 실제 bus/list/stack helper다. free-list 및 reference 값을 미리 cache하거나 모든 ring을 선검사하지 않는다.8e4a의 list writes가 다음 entry/reference 또는 live return을 바꾸면 그 값을 이어서 읽는다. Nativefixture는 초기 palette ring을 어떻게 마련했는지 명시하고 원본 preparer 실행을 중간 register 주입으로 숨기지 않는다.

## 8da2: live binding과 이중 연결 목록

8da2 A5=108000;8da8 watchdog BYTE300001=D0.byte;8dae D0.low=WORD(A0). ffff이면8e44 A0+=2,8e48 RTS로 간다. 그 외8db8 A1=104d92 후8dbe로 간다.

8dbe D0.low<<=4(WORD wrap), A2=A1+signed D0.W.8dc4 D1.low=WORD(A0+2);D4.low=D1.low;D4.low&=ff;D4.low<<=4;D4.low+=4;A4=A1+signed D4.W. WORD(A4+2)==D0.low이면8dfe로 건너뛴다.

다르면8dde에서 D2.low=WORD(A2),D3.low=WORD(A2+2)를 읽고 다음 순서로 변경한다.
1. WORD(A1+signed D3.W)=D2.low.
2. WORD(A1+signed D2.W+2)=D3.low.
3. D3.low=WORD(A4+2)를 **앞선 쓰기 후 다시 읽는다**.
4. WORD(A1+signed D3.W)=D0.low.
5. WORD(A2+2)=D3.low.
6. WORD(A2)=D4.low.
7. WORD(A4+2)=D0.low.

8dfe WORD(A2+8)=ffff. D1.low==ffff이면 WORD(A2+a)=ffff,WORD(A2+c)=ffff,BYTE(A2+f)=2. 그 외 WORD(A2+a)=D1.low,WORD(A2+c)=D1.low, D0.byte=BYTE(A0+4),BSET7 D0,BYTE(A2+f)=D0.byte다. binding operand byte는 list/entry 쓰기 뒤 live로 읽으며 host로 미리 복사하지 않는다. BSET7은 해당bit만 바꾸고 다른 D0 비트를 보존한다.

8e36 A0+=6,D0.low=WORD(A0);ffff가아니면8dbe로 반복하며 A1을 다시 초기화하지 않는다. ffff이면8e44 A0+=2;8e48 live RTS. 원본은 index<256·완전한ring·exactwindow·forward선검사를 하지 않는다. signed index와 실제 read/write의 범위를 bus에서 검사하고 budget으로 비정상 반복을 제한한다. API 실패의 전체 rollback은 원본 fault의 부분 효과와 구분한다.

## e7bf4/e7c36의 실제 호출

e7bf4 JSR8e82(returne7bfa);e7bfa LEAe7b58,A0;e7bfe JSR8da2(returne7c04). e7c04 D0.low=6,D1.low=1,D2.low=c;e7c10 JMP8cda. tail JMP는 추가 stack return을 만들지 않는다.8cda의 원본 의미는 이미 HUD 실행부에 있으며 실제 A7 RTS를 사용한다.

e7c36 JSRe7bf4(returne7c3a);e7c3a LEAe7bda,A0;e7c3e JMP8da2. e7c16의다른wrapper는 이번 새caller범위로 암묵 추가하지 않는다.

## 47ff2부터48042까지

47ff2 JSRe7c36(return47ff8).47ff8 D0.low=003c;47ffc WORD(A5-7ff0)=0;48002 WORD2ffff2=1000;4800a WORD2ffff0=0.48012 A0=LONG20000c;48018 LSL.W2,D0;4801a A0=LONG(A0+signed D0.W);4801e JSR8da2(return48024). 각 실제 PVCwrite의 bank/model 변화와 live ROM 읽기를 보존한다.

48024 LEA10d256,A0;4802a JSR16fac(return48030).48030 LEA480f2,A1;48034 MOVEA.W#0,A2(전체0);48038 MOVEQ0,D0;4803a MOVEQ1f,D1;4803c JSR16ff8(return48042).48042의JSR1861a는 아직 실행하지 않는다. 앞선 scene에서 설정한 node+26 slot은16fac의clear범위밖이므로 그대로 유지된다.

16fac JSR43dda(return16fb2).43dda는 기존 실제9LONG/WORD clear와liveRTS다.16fb2 이후 BYTE(A0+2c)=0,BYTE(A0+2d)=0,LONG(A0+2e)=0,WORD(A0+32)=0,WORD(A0+34)=0,LONG(A0+36)=ffffffff,WORD(A0+28)=0100,WORD(A0+2a)=0100,BYTE(A0+7a)=6 순서로 쓰고16fec RTS한다. 원본이 하지 않는 node전체span 선검사는 추가하지 않는다.

16ff8 LONG(A0+2e)=A1,LONG(A0+36)=A2를 먼저 쓴다.그 뒤 LSL.W4/ASR.W4를 D0와D1에 각각 적용한다. low12bit를 signed12→WORD로 확장하며 상위WORD는 유지한다. C++의 음수 signed shift나 implementation-defined cast에 의존하지 않는다. WORD(A0+32)=D0.low,WORD(A0+34)=D1.low;17010 liveRTS. 앞선 두 LONG쓰기와 returnslot이 겹치면 바뀐 값을 pop한다.

## 실행·검증 경계

실제call/return, pop직후,loop와list쓰기의필요checkpoint를 구현 block과 맞춘다. 임의Z-only분기는 단독지원하지 않고 실제 CMP/MOVE/TST와 분기까지 함께 실행한다. 새knownC는 필수가 아니며 검증된flag-preserving명령만 입력C를 보존하고 나머지는Unknown이다. 원본 SR/context를 읽어carry를 추측하지 않는다.

Native는 immutablefixedROM,16coherent64KiB RAM mirrors,CPU가소유하는readonly bankbuffer,rawPVC와독립모델을 사용한다. 실제bankread마다당시bank·physicaloffset·원본bytes를 검사한다. fullRAM/16R/PC/actualA7·장치/bank·orderedports·reads/status를 비교하고 이전실제C++출력으로 재개한다. freshcontinuous와split의결과가 일치해야한다. 오래된partialAPI검증으로 이 근거를 대신하지 않는다.

직전 scene의unsupported47ff2검사는새경계48042로 이동하되 역사적정상stop과원본관측은그대로둔다. palettebinding/RAMalias/리소스읽기와맵갱신완료를구분한다. 자연scheduler·BIOS/IRQ/timing·일반CCR·전체스테이지·직접플레이·전체게임완료는 미검증이다.
