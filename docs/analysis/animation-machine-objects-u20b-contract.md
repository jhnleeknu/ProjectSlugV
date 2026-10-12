# 객체 callback F4 U20b(재범위 N02): 객체 `858d8` 계열(설치 callback `859b2` `85aa4` `85af8` `85b6c` `85b9e` `85bcc` `85c04` `85c48`)과 공유 꼬리 `849f4` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 U20 계약(`animation-machine-objects-u20-contract.md`, SHA256 `c4000688b7a02546b6ff0202d872af61c5c52632678390fef8ff794be1594cb0`)의 "U20b 제안"과 메인 결정(분할 수용, U20a는 `aa35e83`에 병합), 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N02 행이다. 범위 문서는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U20 행이다. 단위 형식과 규약은 U18·U20 계약과 U05 계약(SHA256 `77fd4062f3935d0e8b2989ad65bed395f43fa7bd37f33309c7a29fa9f512dafc`, `1ab02` 반환 C)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기·DBcc fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee, 다른 단위의 PC, 범위 밖 callback은 실행부 없는 경계다.
- U01~U20a 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BTST`/`BSET`/`BCLR`/`BCHG`)만인 block과 callee C를 소비하는 block은 FLOW_ONLY다. `SUBQ` block은 Unknown이다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U20b 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 자료(`2000e0`)는 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u20b`(HEAD `aa35e83` = U20a·U19까지 통합, `engine/src/animation_machine.cpp` SHA256 `ae8b975237c3c98331c8d09d501f4bb882345d0e187a9dcb7db28af2de9ac3b3`, routing 규칙 57개)을 참조했다. 동시에 진행하는 N01(`5208a..` `e5bb0..e5fbe`, 작업 트리 `metalslug-n01`)의 PC는 U20b에서 나오지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/u20b/u20b.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U20b는 **block 시작 92개**다. 코드 3 범위(`849f4..84a14` 4, `858d8..8597c` 11, `85980..85c6c` 77), 944바이트, 186명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx·I/O port 쓰기·bank 변경은 없다. routing 짝수 PC는 472개, 내부 PC는 380개다.
  - `8597c`(`BRA.W 85984`, 4바이트)는 `85978 BRA.W 85984` 바로 뒤의 도달 불가 명령이다(분기 대상도 아니다). 범위에 넣지 않는다(routing 밖, `unsupported animation machine PC`).
  - 재범위 문서 N02 행의 77과 다르다. 이 계약의 92는 정적 디코드(설치 callback 8개 진입, `849f4` 공유 꼬리 4 포함)다. [U] 77의 산정 차이(재범위 scratch 함수 본문 규칙)는 확인하지 않았다.
  - 함수: 노드 callback `858d8`(stage event 표 LONG `e8dec`가 가리킴), `MOVE.L #imm,(A6)`로 설치되는 callback 8개, 18곳(fixed ROM `BRA.W 849f4`, 이 단위 안 5곳 포함)이 공유하는 꼬리 `849f4`.
- [F] **경계 callee(실행부 없음)**: 없음. 나가는 호출은 모두 routing되어 있다: U05 `1ab02`(C 반환), fade_card `28ae`(자식 생성, C 반환은 소비하지 않음)·`2a00`(`JMP`, 자기 삭제), U04 `43ea4`, interpreter `49f8c` `49fc6`(C 반환), U18 `4be2c`, U11 `4be06`, U17 `4bfa4`, U02 `8ebe`, U20a `492d0` `497a6`(C 반환).
- [F] **범위 밖 자식 callback(쓰기만 함)**: `85c6c`(`85968 MOVEA.L #85c6c,A0` → `28ae`). 범위 문서 어느 단위에도 없다. [F] F4 범위 재생(base·RNG+`80` 400 frame)에서 seed 36·37은 `85c6c`를 실행하지 않는다(`78(A6)`≠0 경로).
- [F] **flag**:
  - 블록 경계를 건너는 C 소비 block **3개**: `849fe BCC.W 84a12`(`1ab02` 반환: U05 `1ab7a` Clear / U01 `1aafc` Set), `8592c BCC.W 85936`(`497a6` 반환: U20a `497a6` Clear / `497b0` Set), `85bec BCC.W 85c00`(`49fc6` 반환, U17 `bc054`·U18 `b76ae`와 같은 소비).
  - known carry 생산 block: 없음(callback 반환 C는 scheduler가 쓰지 않고, `849f4`로 들어오는 18곳은 모두 `BRA.W` 꼬리 호출이다).
  - block 안에서 만들고 쓰는 flag: `CMPI.W #a0,42(A6); BGE`(부호 있는 WORD ≥ `a0`: `858d8` `85aa4`), `TST.W ...; BNE`(`858fe` `8594e`), `MOVE.L 84/88(A6),D0; CMPI.L #0,D0; BGE`(D0 부호 bit 0: `859b2` `85a1c`), `CMPI.L #k,36/3a(A6); BLE/BGE`(부호 있는 LONG: `859c0` `859f0` `85a2a` `85a5a` `85b02` `85b1a`), `CMP.W 7c/7e/80/82(A6),D0; BCC/BCS`(무부호 WORD: `859dc` `85a0c` `85a46` `85a76`), `CMPI.W #0,36(A6); BGE`(LONG `36`의 상위 WORD 부호: `85af8`), `SUBQ.W #1,76(A6); BNE`(`85a92` `85b8c`), BTST 뒤 Bcc(Z: `85b6c` `85bcc` `85c2c` `85c48`).
- [F] 읽는 자료:
  - bank window LONG `2000e0`(`85984` `85ac2` `85b3e` `85b9e` `85c04`의 `MOVE.L 2000e0.L,22(A6)`)와 그 값 + `5c`/`c`/`c`/`18`/`4`의 LONG(`MOVEA.L 22(A6),A1; MOVEA.L d(A1),A1`). live bus로 읽는다(PVC bank 상태 의존). [F] bank `200000`이면 `2000e0`=`002b3388`(이어지는 LONG도 bank window 안), bank `300000`이면 `0029f3c8`, bank `400000`이면 `0022351c`.
  - fixed ROM WORD 표 `84976+2·7a(A6)`(`85936`; 값 `0c5f 0c62 0c63 0c64 0c65 0c67`, index 상한은 원본이 검사하지 않으므로 live bus가 정한다).
  - 주소만 넘기는 상수: `84982`(→`1ab02` A0, 그 안에서 LONG 2개 `ffe0fff0 00400040`을 읽음), `85c6c`(→`28ae` A0).
  - work RAM: node WORD `42` `46` `76` `78` `7a` `7c` `7e` `80` `82`, LONG `36` `3a` `84` `88`, BYTE `15`.
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base와 RNG 초기화+응답 `80` 변형 모두 seed 36·37만 닿는다. TB 시작 39개(`849f4` 4, `858d8` `858f2` `85926` `8592c` `85930` `8594e` `85980`, `85b3e`~`85c68`). `85984`~`85b3a`(`78(A6)`=0 경로: 자식 `85c6c` 생성과 설치 callback `859b2` `85aa4` `85af8`)는 자연 미도달이며 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] seed 36·37의 기준 첫 미연결 callback은 `858d8`(frame 0)이다. F4 범위 재생에서 두 seed가 실행하는 routing 밖 TB는 U20b 범위 밖에는 기존 묶인 분기 내부 12개(`8c2a`…`47fe0`, 범위 문서 측정 방법의 제외 목록)뿐이다. [I] U20b로 두 seed가 base·RNG 모두 완주할 것으로 본다(검증에서 확인).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 92(재범위 N02 행 77과 차이).** 정적 디코드 결과를 따른다. `8597c`는 도달 불가라 넣지 않는다.
2. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u20b.cpp`의 `animation_objects_u20b_block`. 오류는 `unsupported animation objects u20b PC`(내부 PC), `objects u20b caller requires known carry`(소비 3 block). 메인 지시와 같다.
3. **C 소비 3 block의 생산자.** `849fe`: U05 `1ab02`(U05 `b9752`와 같다). `8592c`: U20a `497a6`/`497b0`(U05 `c6ad6`과 같다). `85bec`: interpreter `49fc6`(U18 `b76ae`와 같다). Unknown이면 `objects u20b caller requires known carry`(상태 보존).
4. **bank 자료.** `2000e0`과 이어지는 LONG은 live bus로 읽는다(U18 결정 6과 같음). test는 합성 bank 바이트를 쓴다(ROM 자료를 test에 넣지 않음). fixed 표 `84976`도 test에서는 합성 바이트로 둔다.
5. **무효화 탐침.** [F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U20b 범위 PC를 rollback·outside 탐침으로 쓰는 곳은 없다(scratch `probes.py`). 범위 이웃 `8597c`, `84a14`, `85c6c`는 routing 밖으로 남는다.

## 원본 바이트 근거

[F] 코드 3 범위 합계 944바이트. 범위 순서로 이어 붙인 SHA256 `fe0e7e83f2c53270dfed54d37011a924517d470a33bf762a2fc1bf2db2bc15b7`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `849f4..84a14` | 32 | `5403446589afc00dfae39ccbfb531ad55839566c9ad9f18ae84117f35d4d44aa` | 공유 꼬리 `849f4` |
| `858d8..8597c` | 164 | `b1ea127bca7af2e73f41c069d25625bbd5dfadd05fe604ef029db27662cf8c7e` | callback `858d8` |
| `85980..85c6c` | 748 | `965fb8c077d0895b24effa58737f9c83fc3b0288326200c74e051a7cb758afe3` | 상태 본문, 설치 callback 8개 |

- [F] 범위 밖 이웃: `84976..849f4`(자료: WORD 표 `84976`, 사각형 `84982`, 그 뒤 다른 함수), `84a14..`(다른 함수 `84a14`, `858d8`과 같은 꼴의 다른 객체), `858c0..858d8`(자료), `8597c`(도달 불가 `BRA.W`), `85c6c..`(자식 callback `85c6c`).
- [F] 참조: `858d8`은 stage event 표 LONG `e8dec`. `849f4`는 `BRA.W` 18곳(`84d28` `84e5e` `84f26` `84fe0` `8506a` `850d6` `85168` `851da` `85298` `85300` `853a2` `85414` `85488`과 U20b 안 `85aa0` `85b3a` `85b9a` `85c00` `85c68`). 설치 callback 8개는 U20b 안 `MOVE.L #imm,(A6)`(`859ac` `85a9a` `85af2` `85b66` `85b94` `85bc6` `85bfa` `85c42`)만 설치한다.

## block 목록과 실행 의미

[F] 92 block. 각 줄은 block 안 명령 전체다. "(→x)"는 fall-through다. d16(An)은 부호확장한다. `.W` 연산은 나머지 bit를 보존한다. `NEG.L`은 0-값(32bit wrap)이다. `CMPI.W #0,36(A6)`은 LONG `36`의 상위 WORD를 비교한다.

**공유 꼬리 `849f4` 4**
- `849f4`: `LEA 84982(PC),A0; JSR 1ab02.L` (U05)
- `849fe`: `BCC.W 84a12` (carry 소비)
- `84a02`: `BSET.B #7,61(A6); CLR.W 54(A6); JMP 2a00.L` (fade_card 자기 삭제)
- `84a12`: `RTS`

**callback `858d8` 11**
- `858d8`: `CMPI.W #a0,42(A6); BGE.W 858f2`
- `858e2`: `MOVE.W #40,7e(A6); MOVE.W #ffc0,7c(A6); BRA.W 858fe`
- `858f2`: `MOVE.W #100,7c(A6); MOVE.W #100,7e(A6)` (→`858fe`)
- `858fe`: `MOVE.W 46(A6),D0; MOVE.W D0,80(A6); MOVE.W 46(A6),D0; MOVE.W D0,82(A6); MOVE.L #ffff8000,84(A6); MOVE.L #ffff8000,88(A6); TST.W 7a(A6); BNE.W 85936`
- `85926`: `JSR 497a6.L` (U20a)
- `8592c`: `BCC.W 85936` (carry 소비)
- `85930`: `MOVE.W #5,7a(A6)` (→`85936`)
- `85936`: `MOVE.W 7a(A6),D0; LEA 84976(PC),A0; ADD.W D0,D0; MOVE.W (A0,D0.W),D0; MOVE.B #0,D1; JSR 8ebe.L` (fixed 표; U02)
- `8594e`: `BSET.B #6,15(A6); MOVE.W #8800,68(A6); MOVE.W #8800,1e(A6); TST.W 78(A6); BNE.W 85980`
- `85968`: `MOVEA.L #85c6c,A0; MOVE.W #14,D0; JSR 28ae.L` (자식 생성)
- `85978`: `BRA.W 85984`

**상태 본문 77**
- `85980`: `BRA.W 85b3e`
- `85984`: `LEA 26(A6),A0; MOVE.W #23,20(A6); MOVE.L 2000e0.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 5c(A1),A1; JSR 49f8c.L` (bank 자료)
- `859ac`: `MOVE.L #859b2,(A6)` (→`859b2`)
- `859b2`: `MOVE.L 84(A6),D0; CMPI.L #0,D0; BGE.W 859f0`
- `859c0`: `CMPI.L #fffc0000,36(A6); BLE.W 859d4` / `859cc`: `ADD.L D0,36(A6); BRA.W 859dc` / `859d4`: `MOVE.L #fffc0000,36(A6)` (→`859dc`)
- `859dc`: `MOVE.W 42(A6),D0; CMP.W 7c(A6),D0; BCC.W 859ec` / `859e8`: `NEG.L 84(A6)` (→`859ec`) / `859ec`: `BRA.W 85a1c`
- `859f0`: `CMPI.L #40000,36(A6); BGE.W 85a04` / `859fc`: `ADD.L D0,36(A6); BRA.W 85a0c` / `85a04`: `MOVE.L #40000,36(A6)` (→`85a0c`)
- `85a0c`: `MOVE.W 42(A6),D0; CMP.W 7e(A6),D0; BCS.W 85a1c` / `85a18`: `NEG.L 84(A6)` (→`85a1c`)
- `85a1c`: `MOVE.L 88(A6),D0; CMPI.L #0,D0; BGE.W 85a5a`
- `85a2a`: `CMPI.L #ffff0000,3a(A6); BLE.W 85a3e` / `85a36`: `ADD.L D0,3a(A6); BRA.W 85a46` / `85a3e`: `MOVE.L #ffff0000,3a(A6)` (→`85a46`)
- `85a46`: `MOVE.W 46(A6),D0; CMP.W 82(A6),D0; BCC.W 85a56` / `85a52`: `NEG.L 88(A6)` (→`85a56`) / `85a56`: `BRA.W 85a86`
- `85a5a`: `CMPI.L #10000,3a(A6); BGE.W 85a6e` / `85a66`: `ADD.L D0,3a(A6); BRA.W 85a76` / `85a6e`: `MOVE.L #10000,3a(A6)` (→`85a76`)
- `85a76`: `MOVE.W 46(A6),D0; CMP.W 80(A6),D0; BCS.W 85a86` / `85a82`: `NEG.L 88(A6)` (→`85a86`)
- `85a86`: `JSR 43ea4.L` (U04) / `85a8c`: `JSR 49fc6.L`
- `85a92`: `SUBQ.W #1,76(A6); BNE.W 85aa0` / `85a9a`: `MOVE.L #85aa4,(A6)` (→`85aa0`) / `85aa0`: `BRA.W 849f4`
- `85aa4`: `CMPI.W #a0,42(A6); BGE.W 85aba` / `85aae`: `MOVE.L #ffffc000,36(A6); BRA.W 85ac2` / `85aba`: `MOVE.L #4000,36(A6)` (→`85ac2`)
- `85ac2`: `MOVE.L #0,3a(A6); LEA 26(A6),A0; MOVE.W #23,20(A6); MOVE.L 2000e0.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L c(A1),A1; JSR 49f8c.L`
- `85af2`: `MOVE.L #85af8,(A6)` (→`85af8`)
- `85af8`: `CMPI.W #0,36(A6); BGE.W 85b1a`
- `85b02`: `CMPI.L #fffc0000,36(A6); BLE.W 85b16` / `85b0e`: `SUBI.L #8000,36(A6)` (→`85b16`) / `85b16`: `BRA.W 85b2e`
- `85b1a`: `CMPI.L #40000,36(A6); BGE.W 85b2e` / `85b26`: `ADDI.L #8000,36(A6)` (→`85b2e`)
- `85b2e`: `JSR 43ea4.L` / `85b34`: `JSR 49fc6.L` / `85b3a`: `BRA.W 849f4`
- `85b3e`: `85ac2`의 뒤 7명령과 같고 `MOVEA.L c(A1),A1` (bank 자료) / `85b66`: `MOVE.L #85b6c,(A6)` (→`85b6c`)
- `85b6c`: `BTST.B #7,15(A6); BNE.W 85b80` / `85b76`: `JSR 4be2c.L` (U18) / `85b7c`: `BRA.W 85b86` / `85b80`: `JSR 4be06.L` (U11) / `85b86`: `JSR 49fc6.L`
- `85b8c`: `SUBQ.W #1,76(A6); BNE.W 85b9a` / `85b94`: `MOVE.L #85b9e,(A6)` (→`85b9a`) / `85b9a`: `BRA.W 849f4`
- `85b9e`: `85b3e`와 같고 `MOVEA.L 18(A1),A1` / `85bc6`: `MOVE.L #85bcc,(A6)` (→`85bcc`)
- `85bcc`: `BTST.B #7,15(A6); BNE.W 85be0` / `85bd6`: `JSR 4be2c.L` / `85bdc`: `BRA.W 85be6` / `85be0`: `JSR 4be06.L` / `85be6`: `JSR 49fc6.L`
- `85bec`: `BCC.W 85c00` (carry 소비) / `85bf0`: `LEA 26(A6),A0; JSR 492d0.L` (U20a) / `85bfa`: `MOVE.L #85c04,(A6)` (→`85c00`) / `85c00`: `BRA.W 849f4`
- `85c04`: `85b3e`와 같고 `MOVEA.L 4(A1),A1`
- `85c2c`: `MOVE.L #fffc0000,64(A6); BTST.B #0,15(A6); BEQ.W 85c42` / `85c3e`: `NEG.L 64(A6)` (→`85c42`) / `85c42`: `MOVE.L #85c48,(A6)` (→`85c48`)
- `85c48`: `BTST.B #7,15(A6); BNE.W 85c5c` / `85c52`: `JSR 4be2c.L` / `85c58`: `BRA.W 85c62` / `85c5c`: `JSR 4bfa4.L` (U17) / `85c62`: `JSR 49fc6.L` / `85c68`: `BRA.W 849f4`

(수: 4 + 11 + 77 = 92.)

## 구현 범위와 규약

- routing 3 범위: `849f4..84a14`, `858d8..8597c`, `85980..85c6c`. 짝수 PC 472개 중 block 시작 92, 내부 380. 내부 PC 직접 진입은 `unsupported animation objects u20b PC`다.
- **FLOW_ONLY 36개**(C 보존): `849f4` `849fe` `84a12` `85926` `8592c` `85978` `85980` `859ec` `85a56` `85a86` `85a8c` `85aa0` `85b16` `85b2e` `85b34` `85b3a` `85b6c` `85b76` `85b7c` `85b80` `85b86` `85b9a` `85bcc` `85bd6` `85bdc` `85be0` `85be6` `85bec` `85bf0` `85c00` `85c48` `85c52` `85c58` `85c5c` `85c62` `85c68`.
- **known carry 생산**: 없음. 그 밖 56개는 Unknown(`84a02`의 `CLR.W`, `MOVE.L #imm,(A6)` block, `SUBQ`/`NEG`/`ADD`/`ADDI`/`SUBI`/`CMP`/`CMPI`/`TST`/`MOVE` block).
- **소비자 3개**(결정 3). Unknown이면 `objects u20b caller requires known carry`(상태 보존).
- 스택: JSR 복귀 LONG만. I/O port 쓰기·bank 변경 없음. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM/bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U20b → 기존: U05 `1ab02`, fade_card `28ae` `2a00`, U04 `43ea4`, interpreter `49f8c` `49fc6`, U18 `4be2c`, U11 `4be06`, U17 `4bfa4`, U02 `8ebe`, U20a `492d0` `497a6`.
- [F] U20b → 경계: 없음. 자식 callback `85c6c`는 쓰기만 한다.
- [F] 다른 단위 → U20b: stage event 표 `e8dec`(`858d8`), `849f4`로 가는 범위 밖 `BRA.W` 13곳(`84d28`~`85488`, 다른 객체 callback).

## 자연 시작 상태(읽기 전용 기록)

- [F] 기준 C++ 차분(이 작업 트리 `aa35e83`, 현재 `tools/verify_animation_machine_scheduler_f4.py`·`_rng_f4.py`를 scratch 출력으로 실행): base 일치 pass 11,938·node 93,222, 불일치 0, 자연 완주 109 seed(seed 36·37의 첫 미연결 callback `858d8`, frame 0). RNG 초기화 400 frame: 불일치 0, complete 84, 일치 pass 33,604·node 243,049.

- [F] 작업자 scratch 측정(구현 후, 같은 도구): base 일치 pass 12,178·node 94,840, 불일치 0, 자연 완주 111(새 완주 36 37, 회귀 0). RNG 초기화 400 frame: 일치 pass 34,404·node 248,027, 불일치 0, complete 86(새 complete 36 37, 잃은 것 0).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 92 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류, zero-step, 내부 380 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 소비자 3개 Unknown 오류, 소비자 C는 실제 생산자(`1ab02` `497a6` `49fc6`)를 지나는 fixture의 native 분기로 확인. 자연에 없는 길은 typed fixture(Unicorn, work RAM 입력과 합성 bank·표 바이트)로 비교한다.
- 실제 ROM 차분: `858d8`과 설치 callback 8개, `849f4`를 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다(bank `200000`/`300000`).
- 차분(F2 프레임 패스, 142 seed): 불일치 0, 회귀 0, seed 36·37 완주. RNG 초기화 400 frame 차분: 불일치 0, seed 36·37 complete.

## 미확인·범위 밖

1. [I] `858d8`은 화면 x(`42`) 기준 좌우 한계(`7c`/`7e`)와 y(`46`) 기준 상하 한계(`80`/`82`)를 정하고, `78(A6)`이 0이면 자식 `85c6c`를 만들어 가속도 `84`/`88`로 흔들리는 이동(`859b2`), 아니면 `85b3e` 이후의 직선 이동·대기 상태로 간다. 게임 의미는 미확인이다.
2. [U] `85c6c` 자식 callback과 `849f4`로 오는 범위 밖 13개 객체의 본문은 U20b 밖이다.
3. [U] 재범위 N02 77 block의 산정 차이.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/u20b/`(`u20b.py` block·범위·SHA 계산, `need.py` seed 36·37 필요 집합, `hroute.py` `owner.py` `u20dis.py` `refs.py` `nextins.py` `probes.py` `dynreach.py`; 저장소 밖).
