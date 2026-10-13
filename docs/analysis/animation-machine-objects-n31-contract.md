# 객체 callback F4 N31: `38ba0` 계열 객체 — callback `38ba0`·설치 `38bac`·`38c36`·`38c8e` 사슬, code pointer `38d44`, 공유 꼬리 `3a34c`/`3a350`/`3a41c`, `JMP 2a00` 꼬리 `3a2f4`, `28ae` 자식 `3a2fa`, N30a live target `34750` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N31 행(48 block, 누적 4,667, `34750..34752` `38ba0..38d56` `3a2f4..3a4a4`, 진입 `38ba0` `38bac` `38c36`, 경계 callee 9, 미실행 설치 2(+70), 옛 U43 48 + U44 22 + U45 15; seed 116 117 사슬)이다. 단위 형식과 규약은 N30 계약(`animation-machine-objects-n30-contract.md`, SHA256 `dbbb15d8768f53f7cee0cbdedd4cdb5c189ed7cfd11db83ec7744475af894139`)을 따른다. 메인 작업 지시:
- block 시작은 `MOVE.L #imm,(A6)` 설치 callback, DBRA 대상, JSR 복귀점을 포함한 정적 디코드로 정하고 재범위 수치와 다르면 보고한다(결정 2).
- 재범위 표에서 N31 `3a2f4..3a4a4`가 N32 `3a34c..3a4a4`·N33 `3a41c..3a4a4`와 겹친다. 정적 디코드(공유 꼬리, 함수 범위)로 실제 소유를 정하고 N31 몫만 routing하며 N32·N33이 따를 분할을 정확히 적는다(결정 1).
- `34750`은 N30a `3489a JMP (A1)`의 live target이고 N30a가 경계로 둔다.
- 약 230 block을 넘으면 a/b 분할을 제안한다(N31은 96 block이라 나누지 않는다).
- 범위 안 PC를 "routing 밖" 탐침으로 쓰는 기존 test·fixture는 RAM `10fe00..10fefe`로 옮긴다(해당 없음, 결정 7).
- 다른 단위 실행부의 두 번째 진입이 필요하면 고치지 않고 scratch patch와 결정으로 보고한다(해당 없음, 결정 1).

- 결정 관례(N30과 같음): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치, 범위 밖에서 참조하는 범위 안 진입(설치 값·`28ae` 자식 값·BRA 대상), `LEA x(PC),A0`로 넘기는 code pointer)로 정한다. Unicorn TB 분할은 시작이 아니다. 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N30 수용 관례: `MOVE.x`/`MOVEQ`/`CLR`/`TST`/`CMPI`/`ADDQ`/`SUBQ`/`AND`/`ANDI`/`OR`/`NEG` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`BSET`/`BCLR`/`SNE`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. `ORI` CCR은 known Set 생산이다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N31 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. N31은 banked window를 읽지 않는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n31`(HEAD `d5d85ed` = N01~N26, N28(두 번째 진입 `30fa0` 포함), N29a, N30a 통합, `engine/src/animation_machine.cpp` SHA256 `378aaf570b5de75e9e1c4172098a0f688bc67cbf2f3ad5bf808b9d12e45db2ea`, routing 규칙 86개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`, `engine/src/animation_machine_objects_n30.cpp` SHA256 `aeed39270b8f25b4a62a08458d45249eea9260270b2dbaa2804bb6438142f115`, `engine/src/animation_machine_objects_n23.cpp` SHA256 `c5a148eb271bc3defc3ea62b4d52d4104c8ed2da16d29be61a9f542fbacefa00`)을 참조했다. 재범위 N31 행 3 범위의 짝수 PC는 모두 기존 routing에 없다. 범위 양끝 이웃 `3474e`(N30a `3474c BRA.W`의 내부 PC) `34752` `38b9e` `38d56` `3a2f2` `3a4a4` 중 `3474e`만 routing(N30a)이고 나머지는 routing 밖이다. N27 범위(`5fd24..60506` `dcf56..dcf6a`)와 겹치지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n31/n31.py`(정적 디코드, SHA256 `ad8163145a4121ee410b79d9af7780aca0fc94816bb669c53ca22fd15acee291`; `starts.txt` SHA256 `c9b9cdc537c598d91b674f55e4bd8cfcbd15b23e598d6c863d023ff88f34da98`)와 `cls31.py`(분류)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N31 = 96 block**(재범위 행 3 범위 전체, 코드 872바이트, 185 명령 전부 도달, 자료 없음, 짝수 PC 436, 내부 340). 진입 9개(`38ba0` `38bac` `38c36` `34750`, code pointer `38d44`, 범위 밖 참조 진입 `3a2fa` `3a34c` `3a350` `3a41c`)에서 분기·fall-through·범위 안 설치(`38bac` `38c36` `38c8e` `38cc0` `38cfa` `38d18` `3a334`)를 끝까지 따라갔다. ~230 미만이라 나누지 않는다.
- [F] 진입:
  - callback `38ba0`(LONG `bbed2` `c453c` `e8ce0` `e8ce4`의 객체 표 값; U16 `bbec4`가 `2986` 자식 값으로 넘김): `JSR 3b542`(N33), 설치 `38bac`, RTS.
  - 설치 callback `38bac`(`38ba4`, `38d32`, N32 `38e68`): `4b82e`, `3b302`(A0 = `3b8a0`), `3a5d2`, `3b22a`, `4da50`(A0 = code pointer `38d44`), `496c2`, 설치 `38c36`(fall-through).
  - 설치 callback `38c36`: `1aa7e`(사각형 `3b736`; Set → `3a2f4`), `3b26a`, `4d2d4`(사각형 `3b74e`), `3a4a4`, `4d508`, 설치 `38d56`(범위 밖 값), `3b334`, `BRA 3a34c`.
  - 설치 callback `38c8e`(공유 꼬리 `3a388`): BYTE `9f` ≥ `11`이면 `38cfa`; 아니면 `3af8`, `3b302`(`3b8d6`), `3a5d2`, 설치 `38cc0`(fall-through): `3a5be`(A0 = LONG `82`), `1aa7e`, `3b26a`, `3b334`(Set → 설치 `38cfa`), `BRA 3a34c`. `38cfa`(설치 값·BCC 대상): BYTE `9f` = `11`, `3b302`(`3b8ac`), `3a5d2`, 설치 `38d18`(fall-through): `1aa7e`, `3b26a`, `3b334`(Set → 설치 `38bac`), `BRA 3a34c`.
  - code pointer `38d44`(`38c14 LEA 38d44(PC),A0; JSR 4da50`; N23 `4dbac JSR (A1)`이 부름): 부모 BYTE `b3` = 0이면 C = 0, 아니면 C = 1, RTS.
  - `3a2f4 JMP 2a00`: N31 `38c40` `38cd8` `38d22 BCS`, N32 `3a044 BRA`, N32 `39e44 MOVE.L #3a2f4,(A6)` 설치, N33 `3b5a0 BCC`, 범위 밖 `38b4e BCC`가 쓰는 공유 꼬리.
  - `28ae` 자식 callback `3a2fa`(N33 `3a2d4`, 범위 밖 `3a02a`의 `MOVEA.L #3a2fa,A0; MOVE.W #1e,D0; JSR 28ae`): `3af8`(`18de`), `8ebe`(`363`, 0), `49f8c`(`6f536`), 설치 `3a334`(fall-through): `4be06`, `49fc6`(Set → `JMP 2a00`), RTS.
  - 공유 꼬리 `3a34c`(N31 `38c8a` `38cee` `38d38`, N32 `38e76 BRA.W`) → `BRA 3a3e8`; `3a350`(N32 `39cda` 본문 20곳 이상과 범위 밖 `38d98` `38dd0 BRA.W`): BYTE `15` bit 7, 포화 증가 BYTE `ab`, `3a4a4`(Clear → 설치 `38c8e`), `4d7a6`, `4d734`, `4d9ba`, `3b2ee`, `3af8`; `3a3e8`: `4b54e`, `4ae4a`(`3b7ec`), BYTE `61` bit 7 → 설치 `3a0dc`(범위 밖 값); `3a41c`(N32 `39eae` `39f98`, N33 `3a23e BRA.W`): `8a.W` 타이머, `4d766`, `3b2b8`, BYTE `94` `9e` `a3` `b2`, RTS.
  - N30a live target `34750`(`34748 LEA 34750(PC),A1` → `3489a JMP (A1)`): `RTS`.
- [F] **경계(실행부 없음, 현재 routing 밖) callee 12개**: `3a4a4`(어느 단위에도 없음, 결정 3) `3a5be` `3a5d2` `3b22a` `3b26a` `3b2b8` `3b2ee` `3b302` `3b334` `3b542`(N33 범위 또는 그 이웃) `4d734` `4d9ba`. `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **다른 실행부로 가는 callee·출구**: `2a00`(fade_card), `3af8`(sound), `8ebe`(U02), `1aa7e` `4b54e`(U01), `496c2`(U11), `49f8c` `49fc6`(interpreter), `4ae4a`, `4b82e`, `4be06`, `4d2d4` `4d508` `4d766` `4d7a6` `4da50`(N23).
- [F] **범위 밖 설치 값(실행 PC가 아님)**: `38d56`(`38c80`; 함수 `38d56..38dd4`, 결정 4), `3a0dc`(`3a412`; 결정 4). 주소만 넘기는 자료: 사각형 `3b736`(`1aa7e`) `3b74e`(`4d2d4`), `3b302` 인자 `3b8a0` `3b8d6` `3b8ac`, `4ae4a` 인자 `3b7ec`, 애니메이션 `6f536`(`49f8c`).
- [F] **carry**(아래 "carry" 절): 소비 10 block(모두 FLOW), known 생산 2개(`38d44` TST Clear, `38d50` ORI Set; 소비자 N23 `4dbb2 BCS`), FLOW_ONLY 47개(소비 10 포함), Unknown 47개. 47 + 2 + 47 = 96.
- [F] X·DIVx/MULx·TRAP·I/O port 쓰기·bank 변경·bank 읽기·계산 점프 표·레지스터 간접 제어 이동이 없다. N/Z 재계산이 없다(flag를 읽는 Bcc·`SCS`·`SNE`는 모두 같은 block 안의 생산자를 읽는다). 스택은 JSR 복귀 LONG뿐이다.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`build.pkl` `DYN`, TB 시작 기준): seed 116 117만 N31 PC를 실행한다: `34750`, `38ba0` `38ba4`, `38bac..38c24`의 8개, `38c36..38c8a`의 7개, `38d44` `38d54`, 공유 꼬리 `3a34c` `3a3e8` `3a3ee` `3a406` `3a418` `3a434` `3a43a` `3a444` `3a460` `3a478` `3a496` `3a4a2`. `38c8e` 사슬, `3a2fa` 함수, `3a350..3a3e8`, `3a41c` 진입은 자연 400 frame에서 실행되지 않는다.
- [F] 기준(`d5d85ed`)에서 seed 116 117은 frame 0 `38ba0`에서 멈춘다. [I] N31 뒤에는 frame 0 `38ba0 JSR 3b542`(N33)에서 멈춘다. 새 완주 seed는 없다(재범위 N31 행과 같음).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **겹친 범위의 소유: N31이 `3a2f4..3a4a4` 전체를 갖는다.** [F] 정적 디코드:
   - `3a2f4..3a2fa`는 `JMP 2a00` 한 명령(공유 꼬리, 설치 값)이다. N33 함수 `3a1e0`은 `3a2ee JMP 2a00`에서 끝나 `3a2f4`를 포함하지 않는다.
   - `3a2fa..3a34c`는 `28ae` 자식 callback 함수 하나(9 block, 설치 `3a334`)다. 부모는 N33 `3a2d4`와 범위 밖 `3a02a`다.
   - `3a34c..3a4a4`는 하나의 공유 꼬리 함수(`3a4a2 RTS`에서 끝남)다. 바깥 진입은 `3a34c`(N31 3곳, N32 `38e76`), `3a350`(N32 `39cda` 본문, 범위 밖 `38d98` `38dd0`), `3a41c`(N32 `39eae` `39f98`, N33 `3a23e`) 셋뿐이다(scratch `xref31.py`). 꼬리의 `3a388 MOVE.L #38c8e,(A6)`은 N31 범위 `38ba0..38d56` 안의 `38c8e` 사슬을 설치한다.
   - **권고(구현함)**: N31 = 재범위 3 범위의 코드 전부(96 block). 공유 꼬리 진입 `3a34c` `3a350` `3a41c`, `3a2f4`, `3a2fa`가 모두 N31 block 시작이다. 따라서 N32·N33은 N31 실행부의 두 번째 진입을 요구하지 않는다(scratch patch 없음).
   - **N32가 따를 분할**: N32 범위에서 `3a34c..3a4a4`를 뺀다(재범위의 "신규 310"은 이미 N31의 21 block을 뺀 수다. `3a350..3a3e8` 15 block과 `3a41c` 1 block도 이제 N31이므로 N32 `39cda` 본문의 신규는 [I] 294다). N32의 `BRA.W 3a34c`/`3a350`/`3a41c`, `MOVE.L #3a2f4,(A6)`, `BRA.W 3a2f4`는 N31 실행부로 간다.
   - **N33이 따를 분할**: N33 범위 `3a1e0..3a2fa`를 `3a1e0..3a2f4`로, `3a41c..3a4a4`는 뺀다. `3a23e BRA.W 3a41c`, `3b5a0 BCC.W 3a2f4`, `3a2d4`의 `28ae` 자식 값 `3a2fa`는 N31 시작이다.
   - 대안: N31 = 재범위 48 + `3a41c` 시작(49)만 두고 `3a350..3a3e8`·`38c8e` 사슬·`3a2fa`를 N32·N33에 둔다. `38c8e` 사슬은 N31 함수 범위 `38ba0..38d56` 안이라 N32가 그 범위 안을 routing해야 하고, N31 block `3a418`(현재 `3a41c`까지 이어짐)에 두 번째 진입 patch가 생기므로 권하지 않는다.
2. **재범위 수치와 다른 점.** [F] 재범위 N31 행 48 block(함수 5개 `34750` `38ba0` `38bac` `38c36` `38d44`; scratch `rescope/units.pkl`·`build.pkl`)은 이 계약의 96 block 중 48개와 집합까지 같다. 이 계약에만 있는 시작 48개: `3a2fa` 함수 9(`3a2fa` `3a304` `3a312` `3a32e` `3a334` `3a33a` `3a340` `3a344` `3a34a`), `38c8e` 사슬 23(`38c8e..38d38`), `3a350` 경로 15(`3a350` `3a35a` `3a376` `3a380` `3a384` `3a388` `3a392` `3a39c` `3a3a4` `3a3ac` `3a3b6` `3a3c4` `3a3cc` `3a3d6` `3a3de`), 바깥 진입 `3a41c` 1. 재범위는 함수 본문을 실행된 진입에서 설치를 따르지 않고 셌다.
   - **경계 callee**: 재범위 9(`3a4a4` `3a5d2` `3b22a` `3b26a` `3b2b8` `3b302` `3b334` `3b542` `4d508`) 중 `4d508`은 N23이 routing했다. 추가된 경로가 부르는 `3a5be` `3b2ee` `4d734` `4d9ba`가 늘어 12다.
   - **미실행 설치 "2(+70)"**: 범위 밖 설치 값 `38d56`·`3a0dc` 둘로 본다([I]; 본문 block 수 70은 이 계약에서 다시 세지 않았다, [U]).
   - **새 완주 seed**: 재범위와 같이 없다(아래 검증 기록).
3. **`3a4a4..3a5d2` 틈(어느 단위에도 없음).** [F] `3a4a4`(`D0.W` = `86.W`, `D2` = ±2(BYTE `15` bit 0), `D3` = `1e`, `JMP 4d418`) `3a4be`(BYTE push + `4d8d8` + `JMP 4d4b4`) `3a4da`(`4d6b4`, `28ae` 자식 `3ae84` `2d57a`/`2d3ae`, `4c2fa`, ORI/ANDI C) `3a5be`(`JSR (A0)`)는 재범위 어느 단위 범위에도 없다(N32·N33 경계 목록에만 있음). N31은 `3a4a4`(`38c56` `3a380`)와 `3a5be`(`38cc0`)를 부르고 `3a4a4`의 C(= 경계 `4d418`의 C)를 `38c5e` `3a384`가 소비한다. routing하지 않는다. [I] `4d418`을 맡는 단위 또는 N32b·고아 정리 단계에 붙이는 것을 권한다.
4. **범위 밖 설치 값 `38d56`·`3a0dc`.** [F] `38c80 MOVE.L #38d56,(A6)`의 `38d56..38dd4`(설치 `38d80` `38db6`, `28ae` 자식 `3af86`, `SCC.B 62(A6)`, `4972c`, 설치 `39366`(N32), `BRA.W 3a350`)는 N31 범위 끝 바로 뒤, N32 범위 `38dd4` 바로 앞의 틈이다. `3a412 MOVE.L #3a0dc,(A6)`의 `3a0dc`도 재범위 어느 단위에도 없다(본문이 N32 `39cda`와 공유 꼬리를 공유). 둘 다 자연 400 frame에서 실행되지 않는다. routing하지 않는다(N30 결정 7의 `3383c`와 같은 꼴). [I] 고아 정리 단계 또는 N32 쪽 몫이다.
5. **code pointer `38d44`의 known C.** [F] N22 `3d3de`·N28 `2b692`와 같은 꼴이다. `38d44 MOVEA.L c(A6),A0; TST.B b3(A0); BEQ.W 38d54`의 `TST`가 C = 0을 두고, `38d50 ORI.B #1,CCR`이 C = 1을 둔다. `38d54 RTS`는 FLOW다. 소비자는 N23 `4dbb2 BCS.W 4dbd6`(`4dbac JSR (A1)`의 복귀점)다. 생산 2개(`38d44` Clear, `38d50` Set)로 둔다. 실제 소비자 `4dbb2`를 복귀 LONG으로 둔 native 분기로 확인한다(Unicorn SR을 쓰지 않음).
6. **경계 callee C 소비.** [F] `38c5e BCC.W 38c86`·`3a384 BCS.W 3a392`는 경계 `3a4a4`(→ `4d418`)의 C, `38ce4 BCC.W 38cee`·`38d2e BCC.W 38d38`은 경계 `3b334`(N33)의 C를 읽는다. 실행부가 없으므로 N31 안에서는 typed fixture(진입 C 선언)로만 실행하고 Unknown C면 `objects n31 caller requires known carry`다. [U] 생산은 그 단위가 정한다. `38c40` `38cd8` `38d22`(U01 `1aa7e`), `38c52`(N23 `4d2d4`), `3a43a`(N23 `4d766`)는 실제 생산자를 native로 따라가 확인한다. `3a340`(interpreter `49fc6`)은 typed fixture로 확인한다(N26 `5f394` 관례).
7. **무효화 탐침 없음(탐침 이동 없음).** [F] `engine/tests`·`engine/src`·`tools/*.py`의 16진 토큰 중 N31 3 범위의 값은 N30a 실행부·test의 live target/stop `34750`(stop만, routing 뒤에도 그 PC에서 멈춤), routing 규칙 주석, U16 `bbec4`의 `2986` 자식 값 `0x38ba0`(자료)뿐이다. "routing 밖" 탐침이나 rollback 기대로 쓰는 곳은 없다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n31.cpp`의 `animation_objects_n31_block`. 오류는 `unsupported animation objects n31 PC`(내부 PC), `objects n31 caller requires known carry`(소비 10 block).
9. **`2986` caller-X 제한 해당 없음.** [F] N31은 `2986`을 부르지 않는다.

## 원본 바이트 근거

[F] N31 코드 3 범위 합계 872바이트(짝수 PC 436개, 시작 96, 내부 340). 범위 순서로 이어 붙인 SHA256 `86128a6ba1dfa8336de0d538c2a5574cef17f90d8978a0813dbf245308c0026a`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `34750..34752` | 2 | `1ceeabf0c6a5a30bad12cdac0e3ab015a7188a42e6aebb556aad00bb9cd693ad` | 1 |
| `38ba0..38d56` | 438 | `d35e9f8795a8aedb6658b10a63d5bf92386452244957e62b2419c86c94690b61` | 48 |
| `3a2f4..3a4a4` | 432 | `8b0b8e121e2cd32da1f32b158a7f73d43718f38740f38be43a7f1fbc8f3efbec` | 47 |

- [F] 범위 이웃: `34748..34750`(N30a), `34752..34874`(범위 밖 `34752` `34792` 등; N30a LONG 표 `348a2` 대상), `38b90..38ba0`(범위 밖, 설치 `38e86`), `38d56..38dd4`(결정 4), `38dd4..`(N32), `3a1e0..3a2f4`(N33 함수 `3a1e0`), `3a4a4..3a5d2`(결정 3).
- [F] 우연 일치(실행 진입 아님): 위 진입 외에 N31 범위로 들어오는 LONG·분기·PC 상대 참조는 없다(scratch `xref31.py`: `38bac` LONG 3곳은 설치, `38ba0` LONG 4곳은 객체 표 값, `3a2f4` LONG `39e46`은 `39e44` 설치의 확장어, `3a2fa` LONG 2곳은 `28ae` 자식 값).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "Clear 생산", "Set 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. 비교·`TST`·`BTST`·산술과 그 Bcc는 같은 block 안에 있다.

**N30a live target `34750` 1**
- `34750`: `RTS` — FLOW

**callback `38ba0`(객체 표 값) 2**
- `38ba0`: `JSR 3b542(pc)` — FLOW
- `38ba4`: `MOVE.L #38bac, (a6); RTS`

**설치 callback `38bac`(`38ba4` `38d32`, N32 `38e68`; `4b82e`, `3b302`(`3b8a0`), `3a5d2`, `3b22a`, `4da50`(code pointer `38d44`), `496c2`, 설치 `38c36`) 9**
- `38bac`: `MOVE.W #8810, 68(a6); MOVE.W #8810, 1e(a6); LEA.L 0.w, a0; JSR 4b82e.l`
- `38bc2`: `MOVE.W #0, 88(a6); MOVEA.L #3b8a0, a0; JSR 3b302(pc)`
- `38bd2`: `JSR 3a5d2(pc)` — FLOW
- `38bd6`: `CLR.B a4(a6); CLR.B 9c(a6); MOVE.B #40, a1(a6); BCLR.B #3, 15(a6); JSR 3b22a(pc)`
- `38bee`: `MOVE.B 1b(a6), 14(a6); MOVE.L #0, 7e(a6); MOVE.L #0, 56(a6); MOVEQ #2, d0; MOVEQ #24, d1; BTST.B #0, 15(a6); BEQ.W 38c14` (→`38c12`)
- `38c12`: `NEG.W d0` (→`38c14`)
- `38c14`: `LEA.L 38d44(pc), a0; JSR 4da50.l` — FLOW
- `38c1e`: `JSR 496c2.l` — FLOW
- `38c24`: `MOVE.B #0, 78(a6); MOVE.B #0, b5(a6); MOVE.L #38c36, (a6)` (→`38c36`)

**설치 callback `38c36`(`1aa7e`(`3b736`), `3b26a`, `4d2d4`(`3b74e`), `3a4a4`, `4d508`, 설치 `38d56`(범위 밖 값), `3b334`, 끝 `BRA 3a34c`) 12**
- `38c36`: `LEA.L 3b736(pc), a0; JSR 1aa7e.l` — FLOW
- `38c40`: `BCS.W 3a2f4` (→`38c44`) — C 소비, FLOW
- `38c44`: `JSR 3b26a(pc)` — FLOW
- `38c48`: `LEA.L 3b74e(pc), a0; JSR 4d2d4.l` — FLOW
- `38c52`: `BCC.W 38c86` (→`38c56`) — C 소비, FLOW
- `38c56`: `MOVE.W d0, 86(a6); JSR 3a4a4(pc)`
- `38c5e`: `BCC.W 38c86` (→`38c62`) — C 소비, FLOW
- `38c62`: `MOVE.W d0, 88(a6); MOVE.W 86(a6), d0; MOVE.B #11, d1; MOVE.B ad(a6), d2; MOVE.B ae(a6), d3; MOVE.W 54(a6), d4; JSR 4d508.l`
- `38c80`: `MOVE.L #38d56, (a6)` (→`38c86`)
- `38c86`: `JSR 3b334(pc)` — FLOW
- `38c8a`: `BRA.W 3a34c` — FLOW

**설치 callback `38c8e`(공유 꼬리 `3a388`; 설치 `38cc0` `38cfa` `38d18` `38bac`) 23**
- `38c8e`: `CMPI.B #11, 9f(a6); BCC.W 38cfa` (→`38c98`)
- `38c98`: `MOVE.W #1a5f, d0; JSR 3af8.l`
- `38ca2`: `MOVEA.L #3b8d6, a0; JSR 3b302(pc)` — FLOW
- `38cac`: `JSR 3a5d2(pc)` — FLOW
- `38cb0`: `MOVE.B #4, 95(a6); CLR.L 64(a6); MOVE.L #38cc0, (a6)` (→`38cc0`)
- `38cc0`: `BSET.B #3, 94(a6); MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `38cce`: `LEA.L 3b736(pc), a0; JSR 1aa7e.l` — FLOW
- `38cd8`: `BCS.W 3a2f4` (→`38cdc`) — C 소비, FLOW
- `38cdc`: `JSR 3b26a(pc)` — FLOW
- `38ce0`: `JSR 3b334(pc)` — FLOW
- `38ce4`: `BCC.W 38cee` (→`38ce8`) — C 소비, FLOW
- `38ce8`: `MOVE.L #38cfa, (a6)` (→`38cee`)
- `38cee`: `MOVE.L #0, 56(a6); BRA.W 3a34c`
- `38cfa`: `MOVE.B #11, 9f(a6); MOVEA.L #3b8ac, a0; JSR 3b302(pc)`
- `38d0a`: `JSR 3a5d2(pc)` — FLOW
- `38d0e`: `CLR.L 64(a6); MOVE.L #38d18, (a6)` (→`38d18`)
- `38d18`: `LEA.L 3b736(pc), a0; JSR 1aa7e.l` — FLOW
- `38d22`: `BCS.W 3a2f4` (→`38d26`) — C 소비, FLOW
- `38d26`: `JSR 3b26a(pc)` — FLOW
- `38d2a`: `JSR 3b334(pc)` — FLOW
- `38d2e`: `BCC.W 38d38` (→`38d32`) — C 소비, FLOW
- `38d32`: `MOVE.L #38bac, (a6)` (→`38d38`)
- `38d38`: `MOVE.L #0, 56(a6); BRA.W 3a34c`

**code pointer `38d44`(N23 `4dbac JSR (A1)`) 3**
- `38d44`: `MOVEA.L c(a6), a0; TST.B b3(a0); BEQ.W 38d54` (→`38d50`) — Clear 생산
- `38d50`: `ORI.B #1, ccr` (→`38d54`) — Set 생산
- `38d54`: `RTS` — FLOW

**공유 꼬리 `3a2f4` 1**
- `3a2f4`: `JMP 2a00.l` — FLOW

**`28ae` 자식 callback `3a2fa`(설치 `3a334`) 9**
- `3a2fa`: `MOVE.W #18de, d0; JSR 3af8.l`
- `3a304`: `MOVE.W #363, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `3a312`: `MOVE.W #1001, 68(a6); MOVE.W #1001, 1e(a6); MOVEA.L #6f536, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3a32e`: `MOVE.L #3a334, (a6)` (→`3a334`)
- `3a334`: `JSR 4be06.l` — FLOW
- `3a33a`: `JSR 49fc6.l` — FLOW
- `3a340`: `BCC.W 3a34a` (→`3a344`) — C 소비, FLOW
- `3a344`: `JMP 2a00.l` — FLOW
- `3a34a`: `RTS` — FLOW

**공유 꼬리 `3a34c` / `3a350` / `3a3e8` / `3a41c` 37**
- `3a34c`: `BRA.W 3a3e8` — FLOW
- `3a350`: `BTST.B #7, 15(a6); BEQ.W 3a376` (→`3a35a`) — FLOW
- `3a35a`: `MOVEQ #0, d0; MOVE.B d0, a4(a6); MOVE.B #1, 9c(a6); MOVE.B #40, a1(a6); BCLR.B #3, 15(a6); BRA.W 3a380`
- `3a376`: `ADDQ.B #1, ab(a6); SCS.B d0; OR.B d0, ab(a6)` (→`3a380`)
- `3a380`: `JSR 3a4a4(pc)` — FLOW
- `3a384`: `BCS.W 3a392` (→`3a388`) — C 소비, FLOW
- `3a388`: `MOVE.L #38c8e, (a6); BRA.W 3a3e8`
- `3a392`: `MOVE.W 86(a6), d0; JSR 4d7a6.l`
- `3a39c`: `CMPI.B #11, d0; BNE.W 3a3ac` (→`3a3a4`)
- `3a3a4`: `MOVE.B d1, ad(a6); MOVE.B d2, ae(a6)` (→`3a3ac`)
- `3a3ac`: `MOVE.W 86(a6), d0; JSR 4d734.l`
- `3a3b6`: `MOVE.W 86(a6), d0; MOVEA.L 56(a6), a1; JSR 4d9ba.l`
- `3a3c4`: `TST.B 5e(a6); BEQ.W 3a3e8` (→`3a3cc`)
- `3a3cc`: `BTST.B #6, 61(a6); BNE.W 3a3e8` (→`3a3d6`) — FLOW
- `3a3d6`: `MOVE.W #1e, d0; JSR 3b2ee(pc)`
- `3a3de`: `MOVE.W #1a59, d0; JSR 3af8.l`
- `3a3e8`: `JSR 4b54e.l` — FLOW
- `3a3ee`: `BTST.B #7, 15(a6); TST.W 64(a6); BEQ.W 3a406` (→`3a3fc`)
- `3a3fc`: `LEA.L 3b7ec(pc), a0; JSR 4ae4a.l` — FLOW
- `3a406`: `BTST.B #7, 61(a6); SNE.B d0; BEQ.W 3a418` (→`3a412`) — FLOW
- `3a412`: `MOVE.L #3a0dc, (a6)` (→`3a418`)
- `3a418`: `AND.B d0, 5e(a6)` (→`3a41c`)
- `3a41c`: `BCLR.B #6, 61(a6); TST.W 8a(a6); BEQ.W 3a434` (→`3a42a`)
- `3a42a`: `SUBQ.W #1, 8a(a6); BSET.B #6, 61(a6)` (→`3a434`)
- `3a434`: `JSR 4d766.l` — FLOW
- `3a43a`: `BCC.W 3a444` (→`3a43e`) — C 소비, FLOW
- `3a43e`: `BSET.B #6, 61(a6)` (→`3a444`) — FLOW
- `3a444`: `TST.L 7e(a6); BEQ.W 3a460` (→`3a44c`)
- `3a44c`: `MOVE.B 1a(a6), 14(a6); JSR 3b2b8(pc)`
- `3a456`: `BSET.B #6, 61(a6); BRA.W 3a478` — FLOW
- `3a460`: `MOVE.B 1b(a6), 14(a6); MOVE.W 8a(a6), d0; ANDI.W #1, d0; BEQ.W 3a478` (→`3a472`)
- `3a472`: `MOVE.B 19(a6), 14(a6)` (→`3a478`)
- `3a478`: `BCLR.B #3, 94(a6); BCLR.B #2, 94(a6); MOVE.B #ff, 9e(a6); TST.B a3(a6); BEQ.W 3a496` (→`3a492`)
- `3a492`: `SUBQ.B #1, a3(a6)` (→`3a496`)
- `3a496`: `TST.B b2(a6); BEQ.W 3a4a2` (→`3a49e`)
- `3a49e`: `SUBQ.B #1, b2(a6)` (→`3a4a2`)
- `3a4a2`: `RTS` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다):
  - `38ba0`: `JSR 3b542`. `38ba4`: `(A6)` = `38bac`, RTS.
  - `38bac`: `68.W` = `1e.W` = `8810`, A0 = 0(`LEA 0.w`), `JSR 4b82e`. `38bc2`: `88.W` = 0, A0 = `3b8a0`, `JSR 3b302`. `38bd2`: `JSR 3a5d2`. `38bd6`: BYTE `a4` = BYTE `9c` = 0, BYTE `a1` = `40`, BYTE `15` bit 3 = 0, `JSR 3b22a`. `38bee`: BYTE `14` = BYTE `1b`, LONG `7e` = LONG `56` = 0, `D0` = 2, `D1` = `24`(`MOVEQ`); BYTE `15` bit 0 = 0이면 `38c14`, 아니면 `38c12`: `D0.W` = (0 − `D0.W`) & `ffff`. `38c14`: A0 = `38d44`, `JSR 4da50`. `38c1e`: `JSR 496c2`. `38c24`: BYTE `78` = BYTE `b5` = 0, `(A6)` = `38c36`, fall-through.
  - `38c36`: A0 = `3b736`, `JSR 1aa7e`. `38c40`: Set이면 `3a2f4`. `38c44`: `JSR 3b26a`. `38c48`: A0 = `3b74e`, `JSR 4d2d4`. `38c52`: Clear면 `38c86`. `38c56`: `86.W` = `D0.W`, `JSR 3a4a4`. `38c5e`: Clear면 `38c86`. `38c62`: `88.W` = `D0.W`, `D0.W` = `86.W`, `D1.B` = `11`, `D2.B` = BYTE `ad`, `D3.B` = BYTE `ae`, `D4.W` = `54.W`, `JSR 4d508`. `38c80`: `(A6)` = `38d56`(범위 밖 값). `38c86`: `JSR 3b334`. `38c8a`: `BRA 3a34c`.
  - `38c8e`: 무부호 BYTE `9f` ≥ `11`이면 `38cfa`. `38c98`: `D0.W` = `1a5f`, `JSR 3af8`. `38ca2`: A0 = `3b8d6`, `JSR 3b302`. `38cac`: `JSR 3a5d2`. `38cb0`: BYTE `95` = 4, LONG `64` = 0, `(A6)` = `38cc0`, fall-through. `38cc0`: BYTE `94` bit 3 = 1, A0 = LONG `82`, `JSR 3a5be`. `38cce`: A0 = `3b736`, `JSR 1aa7e`. `38cd8`: Set이면 `3a2f4`. `38cdc`: `JSR 3b26a`. `38ce0`: `JSR 3b334`. `38ce4`: Clear면 `38cee`. `38ce8`: `(A6)` = `38cfa`. `38cee`: LONG `56` = 0, `BRA 3a34c`. `38cfa`: BYTE `9f` = `11`, A0 = `3b8ac`, `JSR 3b302`. `38d0a`: `JSR 3a5d2`. `38d0e`: LONG `64` = 0, `(A6)` = `38d18`, fall-through. `38d18`: A0 = `3b736`, `JSR 1aa7e`. `38d22`: Set이면 `3a2f4`. `38d26`: `JSR 3b26a`. `38d2a`: `JSR 3b334`. `38d2e`: Clear면 `38d38`. `38d32`: `(A6)` = `38bac`. `38d38`: LONG `56` = 0, `BRA 3a34c`.
  - `38d44`: A0 = LONG `c`(부모), C = 0; BYTE `b3(A0)` = 0이면 `38d54`, 아니면 `38d50`: C = 1. `38d54`: RTS.
  - `3a2f4` `3a344`: `JMP 2a00`.
  - `3a2fa`: `D0.W` = `18de`, `JSR 3af8`. `3a304`: `D0.W` = `363`, `D1.B` = 0, `JSR 8ebe`. `3a312`: `68.W` = `1e.W` = `1001`, A1 = `6f536`, `D0.W` = `100`, `JSR 49f8c`. `3a32e`: `(A6)` = `3a334`, fall-through. `3a334`: `JSR 4be06`. `3a33a`: `JSR 49fc6`. `3a340`: Clear면 `3a34a`(RTS), Set이면 `3a344`.
  - `3a34c`: `BRA 3a3e8`. `3a350`: BYTE `15` bit 7 = 0이면 `3a376`. `3a35a`: `D0` = 0, BYTE `a4` = 0(`D0.B`), BYTE `9c` = 1, BYTE `a1` = `40`, BYTE `15` bit 3 = 0, `BRA 3a380`. `3a376`: BYTE `ab` += 1(8 bit); 올림이면(이전 값 `ff`) `D0.B` = `ff`, 아니면 0(`SCS`); BYTE `ab` |= `D0.B`(BYTE를 다시 읽어 OR; 결과적으로 `ff`에서 포화). `3a380`: `JSR 3a4a4`. `3a384`: Set이면 `3a392`. `3a388`: `(A6)` = `38c8e`, `BRA 3a3e8`. `3a392`: `D0.W` = `86.W`, `JSR 4d7a6`. `3a39c`: `D0.B` ≠ `11`이면 `3a3ac`. `3a3a4`: BYTE `ad` = `D1.B`, BYTE `ae` = `D2.B`. `3a3ac`: `D0.W` = `86.W`, `JSR 4d734`. `3a3b6`: `D0.W` = `86.W`, A1 = LONG `56`, `JSR 4d9ba`. `3a3c4`: BYTE `5e` = 0이면 `3a3e8`. `3a3cc`: BYTE `61` bit 6 = 1이면 `3a3e8`. `3a3d6`: `D0.W` = `1e`, `JSR 3b2ee`. `3a3de`: `D0.W` = `1a59`, `JSR 3af8`.
  - `3a3e8`: `JSR 4b54e`. `3a3ee`: BYTE `15`를 읽고(`BTST`, 결과는 다음 `TST`가 덮음), `64.W` = 0이면 `3a406`. `3a3fc`: A0 = `3b7ec`, `JSR 4ae4a`. `3a406`: `D0.B` = (BYTE `61` bit 7 = 1) ? `ff` : 0(`SNE`); bit 7 = 0이면 `3a418`. `3a412`: `(A6)` = `3a0dc`(범위 밖 값). `3a418`: BYTE `5e` &= `D0.B`. `3a41c`: BYTE `61` bit 6 = 0; `8a.W` = 0이면 `3a434`. `3a42a`: `8a.W` −= 1(16 bit), BYTE `61` bit 6 = 1. `3a434`: `JSR 4d766`. `3a43a`: Set이면 `3a43e`: BYTE `61` bit 6 = 1. `3a444`: LONG `7e` = 0이면 `3a460`. `3a44c`: BYTE `14` = BYTE `1a`, `JSR 3b2b8`. `3a456`: BYTE `61` bit 6 = 1, `BRA 3a478`. `3a460`: BYTE `14` = BYTE `1b`, `D0.W` = `8a.W` & 1; 0이면 `3a478`. `3a472`: BYTE `14` = BYTE `19`. `3a478`: BYTE `94` bit 3 = 0, bit 2 = 0(읽기·쓰기 두 번), BYTE `9e` = `ff`; BYTE `a3` = 0이면 `3a496`, 아니면 `3a492`: BYTE `a3` −= 1. `3a496`: BYTE `b2` = 0이면 `3a4a2`, 아니면 `3a49e`: BYTE `b2` −= 1. `3a4a2`: RTS.

## carry

- [F] **소비 10 block**(모두 FLOW). Unknown C로 들어오면 `objects n31 caller requires known carry`(상태 보존)다.
  - `38c40 BCS.W 3a2f4`, `38cd8 BCS.W 3a2f4`, `38d22 BCS.W 3a2f4`: U01 `1aa7e`(`1aaf6 ANDI` Clear, `1aafc ORI` Set).
  - `38c52 BCC.W 38c86`: N23 `4d2d4`(N30 `33200`과 같은 소비).
  - `38c5e BCC.W 38c86`, `3a384 BCS.W 3a392`: 경계 `3a4a4`(→ `4d418`, 결정 6).
  - `38ce4 BCC.W 38cee`, `38d2e BCC.W 38d38`: 경계 `3b334`(N33, 결정 6).
  - `3a340 BCC.W 3a34a`: interpreter `49fc6`.
  - `3a43a BCC.W 3a444`: N23 `4d766`(`4d77a ADD.B D1,D1` 계산 C; N30 `33ac2`와 같은 소비).
- [F] **known 생산 2 block**: Clear(`TST.B`) `38d44`, Set(`ORI`) `38d50`. RTS `38d54`(FLOW)로 N23 `4dbb2 BCS.W`에 넘어간다(결정 5).
- [F] **FLOW_ONLY 47 block**(C 보존): JSR/JMP/BRA/RTS block, `LEA`+`JSR`(`38c14` `38c36` `38c48` `38cce` `38d18` `3a3fc`), `MOVEA`+`JSR`(`38ca2`), `BSET`+`MOVEA`+`JSR`(`38cc0`), `BTST`+Bcc(`3a350` `3a3cc`), `BTST`+`SNE`+`BEQ`(`3a406`), `BSET`(`3a43e`, `3a456`+`BRA`), 소비 10개. 목록: `34750` `38ba0` `38bd2` `38c14` `38c1e` `38c36` `38c40` `38c44` `38c48` `38c52` `38c5e` `38c86` `38c8a` `38ca2` `38cac` `38cc0` `38cce` `38cd8` `38cdc` `38ce0` `38ce4` `38d0a` `38d18` `38d22` `38d26` `38d2a` `38d2e` `38d54` `3a2f4` `3a334` `3a33a` `3a340` `3a344` `3a34a` `3a34c` `3a350` `3a380` `3a384` `3a3cc` `3a3e8` `3a3fc` `3a406` `3a434` `3a43a` `3a43e` `3a456` `3a4a2`.
- [F] **carry 보존 목록 47 PC** = FLOW_ONLY 47. 생산 2 block은 보존 목록에 넣지 않고 block 안에서 C를 정한다.
- [F] **Unknown 47 block**: 나머지(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMPI`/`ADDQ`/`SUBQ`/`AND`/`ANDI`/`OR`/`NEG` 포함 block, 설치 block).
- [F] RTS로 돌려주는 C가 쓰이는 N31 함수는 code pointer `38d44`(N23 `4dbb2`)뿐이다. `38ba4` `3a34a` `3a4a2`(callback 끝, scheduler 복귀)와 `34750`(N30a callback `34748`의 끝)의 C는 쓰이지 않는다.

## 구현 범위와 규약

- routing 3 범위(위 표). 짝수 PC 436개 중 block 시작 96, 내부 340. 내부 PC 직접 진입은 `unsupported animation objects n31 PC`다. 범위 이웃(결정 3·4의 틈, N30a, N32, N33 범위)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)이거나 그 단위 실행부다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVEA`·`LEA`는 LONG 전체). 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow에 기대지 않는다(`NEG.W`, `ADDQ.B`, `SUBQ.W`, `SUBQ.B`). 결과 flag는 같은 block 안의 Bcc·`SCS`·`SNE`만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다). `CLR`은 쓰기로 둔다(기존 단위와 같음).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 47 PC를 넣는다.
- 제어 이동은 모두 정적이다. `3a2f4` `3a344 JMP 2a00`은 복귀 LONG을 push하지 않는다. 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`38c24`→`38c36`, `38cb0`→`38cc0`, `38d0e`→`38d18`, `3a32e`→`3a334`). `38c12`→`38c14`, `38c80`→`38c86`, `38ce8`→`38cee`, `38d32`→`38d38`, `38d50`→`38d54`, `3a376`→`3a380`, `3a3a4`→`3a3ac`, `3a412`→`3a418`→`3a41c`, `3a42a`→`3a434`, `3a43e`→`3a444`, `3a472`→`3a478`, `3a492`→`3a496`, `3a49e`→`3a4a2`도 이어진다.
- 스택: JSR 복귀 LONG만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경·bank 읽기 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] N31 자신은 고정 ROM·banked 자료를 읽지 않는다. 주소만 넘기는 자료: 사각형 `3b736`(`1aa7e`) `3b74e`(`4d2d4`), `3b302` 인자 `3b8a0` `3b8d6` `3b8ac`, `4ae4a` 인자 `3b7ec`, 애니메이션 `6f536`(`49f8c`), code pointer `38d44`(`4da50`).
- [F] work RAM:
  - 노드 A6: BYTE `14` `15` `19` `1a` `1b` `5e` `61` `78` `94` `95` `9c` `9e` `9f` `a1` `a3` `a4` `ab` `ad` `ae` `b2` `b5`; WORD `1e` `54` `64`(`TST.W`) `68` `86` `88` `8a`; LONG `(A6)`(설치) `c`(부모) `56` `64` `7e` `82`.
  - 부모 `c(A6)`: BYTE `b3`(`38d44`).
- [F] 상수 인자: `3af8` `D0.W` = `1a5f`(`38c98`) `18de`(`3a2fa`) `1a59`(`3a3de`); `8ebe` `D0.W`/`D1.B` = `363`/0; `49f8c` A1/`D0.W` = `6f536`/`100`; `4da50` `D0`/`D1` = ±2/`24`, A0 = `38d44`; `4d508` `D1.B` = `11`; `3b2ee` `D0.W` = `1e`; `4b82e` A0 = 0.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_objects_n31.cpp` `887e18348061b56e`, `engine/tests/animation_machine_objects_n31_test.cpp` `0547ff5a342a108e`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나(3 범위), carry 보존 case group 하나(47 PC); `b1e9e44e0fd8d3d9`), `engine/src/animation_machine_internal.h`(선언 하나; `f358ac69c1316f9b`), `Makefile`(source 목록·test target·실행 줄; `4adba68a8dc0fcdf`), `tools/verify_animation_machine.py` SOURCES(`b01532e531c90cd9`). `animation_machine_interpreter.cpp`와 다른 단위 실행부는 바꾸지 않았다. 다른 단위의 두 번째 진입 patch는 필요 없다(결정 1).
- [F] 실행부 case 집합 = scratch `starts.txt`(96). 내부 PC 340개는 모두 `unsupported animation objects n31 PC`, 소비 10 block은 Unknown C에서 `objects n31 caller requires known carry`(상태 보존)다.
- [F] `make -j3 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`). N31 test 출력: `animation machine objects n31: 260 fixtures (21 checked errors, 58 kept C), 96 blocks, 1195 calls`. N29·N30 test는 그대로 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N31 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen31.py` Unicorn 생성(SHA256 앞 16자리 `8435cf2098cd69a8`, 표 `4cdc95331290e3c2`), `gen/assemble31.py` 조립): 260 fixture(성공 239, checked 오류 21), 96 시작 모두 Unicorn fixture로 덮음, block 표(96 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 10은 Unknown에서 거부), zero-step 96 × 3, 내부 PC 340 전수, 홀수 PC(범위 양끝 6), RAM rollback 탐침 `10fe60` `10fe70` `10fe80` `10fea0` `10feb0`·RTS 복귀 `10fe90`(8 fixture), 경계·다른 단위 진입 stop 28개(stop만). "real" 행은 `1aa7e`(사각형 `3b736`, 12 배치 × `38c36` `38cce` `38d18`; Set 6, Clear 30), N23 `4d2d4`(N22 `1bf02`, 사각형 `3b74e` → `38c52`; Set 1, Clear 7), N23 `4d766`(N22 `1bfb4` → `3a43a`; Set 5, Clear 1)를 native로 따라가 실제 소비자 분기와 비교했다. code pointer `38d44`는 복귀 LONG을 실제 소비자 `4dbb2`로 둔 native 분기로 확인했다(부모 `b3` = 0 → `4dbb6`(Clear), 1·`80` → `4dbd6`(Set)). 합성 물리 바이트(ROM 자료 아님): `1bef8..1bf02`, `3b736..3b73e`, `3b74e..3b756`.
- [F] 돌연변이 검사(scratch `mut/mut31.py` SHA256 앞 16자리 `7a91f08d94a034d9`, 실행부 한 곳씩 32개): 32/32를 test가 잡았다(`mut/mut.log`). 처음에 살아남은 `m26`(`3a3ee`의 `BTST.B #7,15(A6)` 읽기 삭제)은 읽기 순서 checked 오류 fixture(`error-3a3ee-btst-read`, A6 = `fffa0`)를 더해 잡았다.
- [F] 실제 ROM 차분(scratch `realrom/real31.py` SHA256 앞 16자리 `e7df89308d58d89b`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM; native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC(N31 경계 12개, 범위 밖 설치 값 `38d56` `3a0dc`; 나중 단위가 routing해도 선언 stop으로 유지)·interpreter `49f8c`/`49f96`(선언 stop)에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0, 시작 96/96(세 seed 모두). 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `38c40` 115 `38c52` 63 `38cd8` 43 `38d22` 24 `3a340` 87 `3a43a` 316, `38d44` → N23 `4dbb2` 47. interpreter 따라가기(`FOLLOW_ANIM`, seed 4) 1,000 case 불일치 0. 의도한 차이: `38d54`에 Unknown C로 직접 들어가 N23 `4dbb2`가 `objects n23 caller requires known carry`로 거부한 1~2건(seed별). native 홀수 주소·`2986` 0건. clean stop이 없는 native case는 건너뜀(seed별 43/41/51).
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `d5d85ed` 일치 pass 14,408·node 122,462, 불일치 0 → N31 뒤 같음(`diff_results.json` SHA256 앞 16자리 `a6c41695e17a74bd`, 기준과 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` `5986aaef…`) → N31 뒤 같은 수치·불일치 0(`76308d74…`). 차이는 기록된 `animation_machine.cpp` SHA, 새 원본 목록, seed 116 117의 `current_first_missing_PC` `38ba0` → `3b542`뿐이다. **새 완주 seed 없음**(재범위 예상과 같음), 잃은 seed 0. seed 116 117은 frame 0 `38ba0 JSR 3b542`의 `3b542`(N33)에서 멈춘다.
- [F] 탐침 이동: 없음(결정 7). 이 test의 새 RAM 탐침은 `10fe60` `10fe70` `10fe80` `10fe90` `10fea0` `10feb0`이다.
- [U] 남은 미확인: N31 범위의 자연 frame pass 비교는 116 117이 `3b542`에서 먼저 멈춰 아직 없다(실제 ROM 차분·fixture로만 덮음). 경계 `3a4a4`(→ `4d418`)와 `3b334`의 C 생산(소비 `38c5e` `3a384` `38ce4` `38d2e`)은 그 단위가 정한다. 결정 3의 `3a4a4..3a5d2`, 결정 4의 `38d56..38dd4`·`3a0dc`는 routing하지 않았다. 재범위 "미실행 설치 2(+70)"의 block 수 70은 다시 세지 않았다.
