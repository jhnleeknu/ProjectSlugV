# F5 frame head H3: palette frame `5728`와 색 helper `4718`/`479e`/`4c40`/`504c` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 F5 범위 문서(`animation-machine-frame-head-f5-scope.md`, 작업 트리 사본 SHA256 `973d45957731ff17ccf49537024307cf7fd20fe9270c9d9bb44a2bc553280fb0`)의 §4 H3 행이다: `5728..72ee` `4718..5726`, 551 block(고유 39 + cell family 256×2), 자연 실행 318, 위험 unrolled 2,381명령 색 blend·watchdog 256회·PVC. 메인 결정(범위 문서 머리)이 구속한다. 특히 "반복 family(`5728` palette cell 등)는 PC를 매개변수로 받는 executor 하나로 구현해도 된다. 단위 상한은 고유 코드 기준으로 세되, 시험은 모든 진입 PC를 덮어야 한다"를 따른다. 형식·규약은 H1 계약(`animation-machine-frame-head-h1-contract.md`, SHA256 `16e7937e7bdc2a40f7e8f99601a806e046238a2f6f42bda181b5418c2495f3ec`)을 그대로 쓴다. native 관측은 `animation-machine-frame-head-observation.md`(SHA256 `98677e44862b7ae7304992fd7d2c7d1f1ac0616252aa6937fac9a6fe32ce16f2`)와 산출 `artifacts/animation_machine_frame_head_native/observation.json`(SHA256 `4fe4f796879af90df1c1fd4c753485a9bf0a04d2667b14b8c00dbab23879b16b`, 읽기 전용)이다.

메인 작업 지시(요약):
- 계약을 먼저 쓴다. block 목록은 정적 디코드로 정하고, cell family의 구조를 ROM 바이트로 증명한다(매개변수로 빼는 것 외에는 모든 cell이 바이트 단위로 같음).
- watchdog `300001` 등은 H1처럼 기록되는 port event다. PVC 쓰기는 `am_write`로 한다. raster·입력 읽기가 필요하면 H1처럼 `animation machine external read queue empty`에서 멈춘다(public header 변경 없음).
- 고유 코드가 ~230 block을 크게 넘으면 분할을 제안한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. H3 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-h3`(base `c5181b6` = F5 H1 + native F5 observer, `engine/src/animation_machine.cpp` SHA256 `4337007826e7d6dc41dd3381162124ca0ca028f7b7eb04fc85e4dc36454e94d3`, `engine/include/ms5/animation_machine.h` SHA256 `16092fb9479f1f72f883816e0c9f3e25914d1d56a071208ba800d0ed5b732734`)을 참조했다. H3 범위의 짝수 PC는 기존 routing에 없다. [F]=원본 바이트, 기록 산출물 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/h3/h3dec.py`(정적 디코드, `starts.txt` 551개 SHA256 `43ae5e72a75111d97f88ba46334a359cf114293bf41ac97681e29b4f240969f3`, 고유 `unique.txt` 39개 SHA256 `83b3c6028d6bcec31c1035d3941d39eeb60de16c90daf7d3633521c7b1cbef89`)가, 바이트 증명은 `h3proof.py`(`proof.log`, `cells.txt` SHA256 `a9d91a3ae417b00f1e4d673a30ab3e1bbadbae37439539ab003b592c2bb84077`)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **정적 leader 551개 = 고유 39 + cell family 512(256 cell × 2).** 진입 `5728` 하나에서 분기·fall-through·BSR을 끝까지 따라간 closure이고 범위 `4718..72f0`의 명령 3,191개를 모두 덮는다(미도달 0, 간접 분기 0, 연속 Bcc 묶음 0, 범위 밖 분기·호출 0). 범위 문서의 551(39 + 256×2)·3,191명령과 같다.
- [F] **분할 불필요.** 고유 block 39개는 상한(~230)보다 훨씬 작다. 큰 것은 unrolled helper 4개(명령 50/531/446/761)인데, 각 helper의 15회 반복 본문이 바이트 단위로 같으므로(아래 증명) C++에서는 같은 순서의 반복문으로 쓴다(H1 `166ca`/`16756` 관례).
- [F] **진입:** `5728`(H1의 `e98` `f44` `fae`가 `JSR 5728.l`로 부른다. 복귀점 `ea4` `f4c`(guard 경로) `fb4`). helper `4718`은 범위 밖 `8b94 BSR.W 4718`(controller 쪽 `8b64..8bb6`, F5 C2 범위)에서도 불린다(복귀 `8b98 MOVE.W #2000,-216(A5)`, C를 읽지 않음). fixed ROM 전체의 분기·JSR·LONG·PC 상대 참조 탐색(scratch `h3xref.py`)에서 그 밖의 진입은 우연 자료 일치뿐이다(`4f3ea`/`bbcc`/`2928`/`d3a6a`의 명령 바이트, writer 끝 LONG `00006400` 20곳 등; 모두 명령 중간·자료).
- [F] **경계:** H3는 다른 단위로 나가는 호출이 없다. 끝은 `7194`/`7232`/`72d0`의 RTS(호출자 복귀, 자연 H에서는 H1 `ea4`)뿐이다. 범위 이웃 `4716`은 routing 밖, `72f0`은 기존 실행부(F1 `47a94..` 계열 규칙의 `72f0..72fa`)다.
- [F] **carry:** 소비 block 0, known 생산 0. FLOW_ONLY 268(cell 257: `B_k` 256 + `L_255`; 고유 11), Unknown 283(cell `L_0..L_254` 255 + 고유 28). 268 + 283 = 551. carry 오류 문자열 없음.
- [F] **I/O:** watchdog `MOVE.B D0,300001.l` 256회(`5788`과 cell `L_0..L_254`; fade 단계 경로에서만), PVC `2ffff2`/`2ffff0` WORD 쓰기(`7196` `7232` `72d0`, bank `200000`), bank 창 읽기 LONG `200004`/`200008`과 그 포인터가 가리키는 palette 원본·색 변환 표, fixed ROM blend 표 `3f78+`. device 읽기(raster `3c0006`, 입력 `300000`/`340000`/`380000`)는 **없다**. 따라서 external read queue 오류도 없다.
- [F] **Waiting 없음.** H3 안에 대기 루프·신호 polling이 없다.
- [I] H3 routing 뒤 자연 H는 `5728`을 지나 H1 `ea4`(raster 읽기, 결정 2의 checked 오류)까지 간다. 역방향 writer 표(H4)에서 먼저 멈추는 segment는 그대로다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **routing 한 범위 `4718..72f0`, 단일 실행부.** [F] `4718..5728`과 `5728..72f0`이 이어져 있고 짝수 PC 5,612개가 모두 미routing이다(앞 이웃 `4716` 미routing, 뒤 이웃 `72f0` 기존 실행부). routing은 `(pc>=0x4718 && pc<0x72f0)` 하나다. 내부 PC(5,061개) 직접 진입은 `unsupported animation frame head h3 PC`(상태 보존)다.
2. **cell family는 PC 매개변수 실행부 하나(메인 결정 그대로).** [F] cell k(k = 0..255)는 `578c+26k`에서 시작하는 26바이트 `13c000300001 082a0001000f 66000008 08ea0007000f 45ea0010`(`MOVE.B D0,300001.l; BTST.B #1,f(A2); BNE.W +8; BSET.B #7,f(A2); LEA 10(A2),A2`)이고 256개가 모두 바이트 단위로 같다(`BNE.W`의 변위 `0008`도 상대값이라 같다). 매개변수는 PC에서 계산하는 k 하나뿐이다. block 시작은 `B_k = 579c+26k`(`BSET`, BNE 거짓 fall-through)와 `L_k = 57a2+26k`(`LEA`, BNE 대상)다. 실행부는 (pc − `578c`) mod 26 ∈ {16, 22}인 짝수 PC만 받고 나머지는 내부 PC 오류다.
3. **unrolled helper는 같은 순서의 반복문.** [F] `4718`(본문 8바이트 × 15), `479e`(78 × 15), `4c50`(66 × 15), `505c`(114 × 15)의 반복 본문이 모두 바이트 단위로 같다(증명 아래). 원본 block 하나(진입~RTS)를 C++ block 한 번으로 실행하고, 안에서 15회 반복을 원본 명령 순서대로 한다(읽기·쓰기 순서 보존).
4. **carry 보존 목록에 268 PC.** [F] `carry_preserving_pc`의 주석 붙은 case group 하나에 cell `B_k` 256개(`579c+26k`), `L_255`(`7188`, `LEA`만)와 고유 FLOW 11개를 넣는다. cell `B_k`는 `BSET` 하나뿐인 block이라 U01~N29 관례상 FLOW_ONLY다. [I] 소비자가 없어 Unknown으로 두어도 결과는 틀리지 않지만, 관례와 시험의 "kept C"를 맞추려고 넣는다. 다른 방식(범위 함수)은 공유 수정이 커지므로 택하지 않았다.
5. **watchdog은 port event, PVC는 `am_write`.** [F] `MOVE.B D0,300001.l` 한 번 = `VideoPortWrite{300001, 1, D0.B}` 한 건(기존 `palette_bind`·`cleanup`·`scene`과 같은 표현). `7196`/`7232`/`72d0`의 `MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.l; MOVE.W #0,2ffff0.l`은 기존 `am_zero_bank`와 같은 순서·값이다(PVC 기억, bank 공식, port 기록 2건).
6. **external read·Waiting 없음.** [F] H3 안에 raster·입력 읽기와 대기가 없어 public header나 queue API(병렬 작업)와 무관하다. 새 status·오류 어휘도 없다.
7. **무효화 탐침.** [F] 기존 test·verifier가 H3 범위 PC를 "routing 밖" 탐침이나 rollback 기대로 쓰는지는 구현 뒤 `make all test` 전체 실행과 Python verifier 목록으로 확인해 아래 검증 기록에 적는다. [I] H1 test는 `5728`을 stop-only 경계로만 쓰므로 그대로 통과할 것이다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_frame_head_h3.cpp`의 `animation_frame_head_h3_block`. 오류는 `unsupported animation frame head h3 PC`(내부 PC) 하나다. 나머지는 기존 공통 오류(정렬·RAM 밖 쓰기·bank 물리 범위·stack)다.

## 원본 바이트 근거

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `4718..5728` | 4,112 | `66830dccd305bc341d8ebe7652aa5423c13e9828be2d7d29bff902d6990a771f` | 8 |
| `5728..72f0` | 7,112 | `9438e0be887f8ecb36c1794d457113d5ce76b9345151f1e7ee7b4e3a0f7aa222` | 543(고유 31 + cell 512) |
| `4718..72f0`(연결) | 11,224 | `43249b159030445392103562097c2b26f283e77193a34ed41a3ba1f931f4e5ad` | 551 |

**cell family 증명(scratch `h3proof.py`, `proof.log`, `cells.txt`).**
- [F] `5788..578c` = `45edcd92`(`LEA -326e(A5),A2`), 그 뒤 cell 0이 `578c`에서 시작한다.
- [F] cell k(`578c+26k`, k = 0..255)의 26바이트는 256개 모두 `13c000300001082a0001000f6600000808ea0007000f45ea0010`과 같다(불일치 0). `cells.txt`에 k, cell 시작, `B_k`, `L_k`, cell 바이트 SHA256 앞 16자리를 256줄 기록했다.
- [F] 마지막 cell 255는 `7172..718c`이고 `578c+26×256 = 718c`가 `TST.B -213(A5)`(다음 고유 block)다. 따라서 `L_255 = 7188`의 `LEA` 뒤에는 cell 머리 대신 `718c`로 fall-through한다.
- [F] 정적 leader 중 `578c..718c` 안의 것은 정확히 `B_k`·`L_k` 512개다(그 밖의 leader 없음).

**helper unroll 증명.** 반복 본문을 (끝 − 앞 − prologue − epilogue) / 15로 나누어 15개 조각이 모두 같은지 비교했다.

| helper | prologue | 본문 바이트 × 15 | 본문 SHA256 앞 16 | epilogue | 끝 |
| --- | --- | --- | --- | --- | --- |
| `4718` | `2e0c 49ec0002 41e80002` | 8 | `48519991f40bb6c1` | `2847 4e75` | `479e` |
| `479e` | `7e1f 2c0c 49ec0002 41e80002` | 78 | `70ab172a4d214c25` | `2846 4e75` | `4c40` |
| `4c50` | `2c0c 2a0a 45faf322 ed48 d4c0 49ec0002 41e80002 43e90002` | 66 | `9d332e972d4eb36d` | `2445 2846 4e75` | `504c` |
| `505c` | `2c0c 2a0a 45faef16 ed48 d4c0 49ec0002 41e80002 43e90002` | 114 | `30913f542a18375b` | `2445 2846 4e75` | `5728` |

- [F] `4c40..4c50` = `4a40 6700fad4 c348 7e1f b047 6400faca`, `504c..505c` = `4a40 6700f74e c348 7e1f b047 6400f744`(대상만 `4718`/`479e`로 다르다).
- [F] `LEA 3f78(PC),A2`: `4c54`의 `45faf322`(4c56 − `0cde`)와 `5060`의 `45faef16`(5062 − `10ea`)이 모두 `3f78`이다.

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그 "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)·`(An,Dn.W)`는 부호 확장, `(An,Dn.L)`은 LONG 색인이다. A5 기준 자연 주소(A5 = `108000`): `-23e`=`107dc2`, `-23c`=`107dc4`, `-23a`=`107dc6`, `-238..-234`=`107dc8..107dcc`, `-232..-22e`=`107dce..107dd2`, `-22c`=`107dd4`, `-22b`=`107dd5`, `-213`=`107ded`, `-326e`=`104d92`, `-225e`=`105da2`, `-7ff0`=`100010`.

**fade 단계 `5728`(진입) 6**
- `5728`: `MOVE.B -22c(a5), d7; BEQ.W 718c` (→`5730`)
- `5730`: `MOVE.B -23e(a5), d0; MOVE.B -23c(a5), d1; MOVE.B -23a(a5), d2; SUBQ.B #1, d7; MOVE.B d7, -22c(a5); BNE.W 575c` (→`5746`)
- `5746`: `MOVE.W -238(a5), -23e(a5); MOVE.W -236(a5), -23c(a5); MOVE.W -234(a5), -23a(a5); BRA.W 5774`
- `575c`: `MOVE.W -232(a5), d7; ADD.W d7, -23e(a5); MOVE.W -230(a5), d7; ADD.W d7, -23c(a5); MOVE.W -22e(a5), d7; ADD.W d7, -23a(a5)` (→`5774`)
- `5774`: `SUB.B -23e(a5), d0; SUB.B -23c(a5), d1; SUB.B -23a(a5), d2; OR.B d1, d0; OR.B d2, d0; BEQ.W 718c` (→`5788`)
- `5788`: `LEA.L -326e(a5), a2; MOVE.B d0, 300001.l; BTST.B #1, f(a2); BNE.W 57a2` (→`579c`)

**dirty 표시 cell family 512(k = 0..255)**
- `B_k = 579c+26k`: `BSET.B #7, f(a2)` (→`L_k`) — FLOW
- `L_k = 57a2+26k`, k ≤ 254: `LEA.L 10(a2), a2; MOVE.B d0, 300001.l; BTST.B #1, f(a2); BNE.W L_(k+1)` (→`B_(k+1)`)
- `L_255 = 7188`: `LEA.L 10(a2), a2` (→`718c`) — FLOW

**palette 재구성 `718c` 25**
- `718c`: `TST.B -213(a5); BPL.W 7196` (→`7194`)
- `7194`: `RTS` — FLOW
- `7196`: `MOVE.B #0, -22b(a5); MOVE.L a6, -(a7); LEA.L -326e(a5), a2; LEA.L -225e(a5), a4; MOVE.W #0, -7ff0(a5); MOVE.W #1000, 2ffff2.l; MOVE.W #0, 2ffff0.l; MOVEA.L 200004.l, a6; MOVEA.L 200008.l, a3; MOVE.B -23e(a5), d0; OR.B -23c(a5), d0; OR.B -23a(a5), d0; BNE.W 7252` (→`71d8`)
- 무 fade 경로:
  - `71d8`: `BCLR.B #7, f(a2); BEQ.W 7222` (→`71e2`) — FLOW
  - `71e2`: `MOVEQ #0, d7; MOVEQ #0, d6; MOVE.W a(a2), d7; MOVE.W c(a2), d6; CMP.W d6, d7; BNE.W 7202` (→`71f4`)
  - `71f4`: `LSL.L #5, d7; LEA.L (a6, d7.l), a0; BSR.W 4718`
  - `71fe`: `BRA.W 7218` — FLOW
  - `7202`: `LSL.L #5, d6; LSL.L #5, d7; LEA.L (a6, d7.l), a0; LEA.L (a6, d6.l), a1; MOVEQ #0, d0; MOVE.B e(a2), d0; BSR.W 4c40`
  - `7218`: `MOVE.W #8000, (a4); MOVE.B #ff, -22b(a5)` (→`7222`)
  - `7222`: `LEA.L 20(a4), a4; LEA.L 10(a2), a2; CMPA.L #107da2, a4; BNE.B 71d8` (→`7232`)
  - `7232`: `MOVE.B -22b(a5), -213(a5); MOVEA.L (a7)+, a6; MOVE.W #0, -7ff0(a5); MOVE.W #1000, 2ffff2.l; MOVE.W #0, 2ffff0.l; RTS`
- fade 경로(`-23e|-23c|-23a` BYTE ≠ 0):
  - `7252`: `BCLR.B #7, f(a2); BEQ.W 72c0` (→`725c`) — FLOW
  - `725c`: `MOVEQ #0, d7; MOVEQ #0, d6; MOVE.W a(a2), d7; MOVE.W c(a2), d6; CMP.W d7, d6; BNE.W 728e` (→`726e`)
  - `726e`: `LSL.L #5, d7; LEA.L (a6, d7.l), a0; BTST.B #1, f(a2); BEQ.W 7286` (→`727e`)
  - `727e`: `BSR.W 4718` — FLOW
  - `7282`: `BRA.W 728a` — FLOW
  - `7286`: `BSR.W 479e` — FLOW
  - `728a`: `BRA.W 72b6` — FLOW
  - `728e`: `LSL.L #5, d6; LSL.L #5, d7; LEA.L (a6, d7.l), a0; LEA.L (a6, d6.l), a1; MOVEQ #0, d0; MOVE.B e(a2), d0; BTST.B #1, f(a2); BEQ.W 72b2` (→`72aa`)
  - `72aa`: `BSR.W 4c40` — FLOW
  - `72ae`: `BRA.W 72b6` — FLOW
  - `72b2`: `BSR.W 504c` — FLOW
  - `72b6`: `MOVE.W #8000, (a4); MOVE.B #ff, -22b(a5)` (→`72c0`)
  - `72c0`: `LEA.L 10(a2), a2; LEA.L 20(a4), a4; CMPA.L #107da2, a4; BNE.B 7252` (→`72d0`)
  - `72d0`: `7232`과 같은 6명령(끝 RTS)

**색 helper 8**
- `4718`: `MOVE.L a4, d7; LEA.L 2(a4), a4; LEA.L 2(a0), a0; (MOVE.W (a0)+, d0; ADD.W d0, d0; MOVE.W (a3, d0.w), (a4)+)` ×15`; MOVEA.L d7, a4; RTS` (명령 50)
- `479e`: `MOVEQ #1f, d7; MOVE.L a4, d6; LEA.L 2(a4), a4; LEA.L 2(a0), a0;` 본문(명령 35) ×15`; MOVEA.L d6, a4; RTS` (명령 531)
- `4c40`: `TST.W d0; BEQ.W 4718` (→`4c46`)
- `4c46`: `EXG.L a1, a0; MOVEQ #1f, d7; CMP.W d7, d0; BCC.W 4718` (→`4c50`)
- `4c50`: `MOVE.L a4, d6; MOVE.L a2, d5; LEA.L 3f78(pc), a2; LSL.W #6, d0; ADDA.W d0, a2; LEA.L 2(a4), a4; LEA.L 2(a0), a0; LEA.L 2(a1), a1;` 본문(명령 29) ×15`; MOVEA.L d5, a2; MOVEA.L d6, a4; RTS` (명령 446)
- `504c`: `TST.W d0; BEQ.W 479e` (→`5052`)
- `5052`: `EXG.L a1, a0; MOVEQ #1f, d7; CMP.W d7, d0; BCC.W 479e` (→`505c`)
- `505c`: `4c50`과 같은 prologue, 본문(명령 50) ×15, 같은 epilogue (명령 761)

**실행 의미 보충.** 명령 순서대로 읽고 쓴다. `.W`/`.B`는 나머지 bit를 보존한다(`MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`EXG`·`LSL.L`은 LONG 전체). 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow·shift에 기대지 않는다. 메모리 RMW(`ADD.W d7,-23e(a5)`, `BSET`/`BCLR`)는 읽은 뒤 쓴다. `MOVE.W (a3,d0.w),(a4)+`는 원본을 읽은 뒤 쓴다.
- `5728`: `D7.B` = BYTE `-22c(A5)`; 0이면 `718c`. `5730`: `D0.B`/`D1.B`/`D2.B` = BYTE `-23e`/`-23c`/`-23a(A5)`(이전 fade 정수부), `D7.B` −= 1, BYTE `-22c(A5)` = `D7.B`; 0이 아니면 `575c`, 0이면 `5746`. `5746`: WORD `-23e`/`-23c`/`-23a(A5)` = WORD `-238`/`-236`/`-234(A5)`(이 순서로 하나씩 읽고 씀), `5774`. `575c`: 세 채널에 대해 `D7.W` = WORD 증분(`-232`/`-230`/`-22e`), WORD 채널 += `D7.W`(16 bit). `5774`: `D0.B` −= BYTE `-23e`, `D1.B` −= BYTE `-23c`, `D2.B` −= BYTE `-23a`(새 정수부), `D0.B` |= `D1.B`, `D0.B` |= `D2.B`; 0이면 `718c`(정수부 변화 없음), 아니면 `5788`.
- `5788`: A2 = A5 − `326e`, watchdog(`D0.B`), BYTE `f(A2)` bit 1 = 1이면 `L_0`, 0이면 `B_0`. `B_k`: BYTE `f(A2)` bit 7 set. `L_k`: A2 += `10`; k ≤ 254이면 watchdog(`D0.B`), BYTE `f(A2)` bit 1로 `L_(k+1)`/`B_(k+1)`; k = 255이면 `718c`. [I] 256개 palette slot(`104d92+16k`) 중 bit 1(fade 제외)이 꺼진 slot에 dirty bit 7을 세우고 slot마다 watchdog을 친다.
- `718c`: BYTE `-213(A5)` bit 7 = 1이면 `7194 RTS`, 0이면 `7196`. `7196`: BYTE `-22b(A5)` = 0, LONG push A6, A2 = A5 − `326e`, A4 = A5 − `225e`, `am_zero_bank`과 같은 세 쓰기(WORD `-7ff0(A5)` = 0, PVC `2ffff2` = `1000`, `2ffff0` = 0), A6 = LONG `200004`, A3 = LONG `200008`(쓰기 뒤 bank의 live bus), `D0.B` = BYTE `-23e` | BYTE `-23c` | BYTE `-23a`; ≠ 0이면 `7252`, 아니면 `71d8`.
- `71d8`/`7252`: BYTE `f(A2)` bit 7 검사·clear; 원래 0이면 `7222`/`72c0`. `71e2`/`725c`: `D7` = WORD `a(A2)`(0 확장), `D6` = WORD `c(A2)`(0 확장); 같으면 `71f4`/`726e`, 다르면 `7202`/`728e`. `71f4`/`726e`: `D7` = (`D7` << 5) mod 2^32, A0 = A6 + `D7`. `726e`는 이어서 BYTE `f(A2)` bit 1 = 0이면 `7286`(BSR `479e`), 1이면 `727e`(BSR `4718`). `71f4`는 BSR `4718`(복귀 `71fe`). `7202`/`728e`: `D6`·`D7` << 5, A0 = A6 + `D7`, A1 = A6 + `D6`, `D0` = BYTE `e(A2)`(0 확장); `7202`는 BSR `4c40`(복귀 `7218`), `728e`는 bit 1 = 0이면 `72b2`(BSR `504c`), 1이면 `72aa`(BSR `4c40`). `7218`/`72b6`: WORD (A4) = `8000`, BYTE `-22b(A5)` = `ff`. `7222`/`72c0`: A4 += `20`, A2 += `10`(두 block에서 순서만 다르다); A4 ≠ `107da2`(고정 상수)이면 반복. `7232`/`72d0`: BYTE `-213(A5)` = BYTE `-22b(A5)`, A6 = LONG pop, `am_zero_bank`과 같은 세 쓰기, RTS.
- `4718`: `D7` = A4, A4 += 2, A0 += 2, 15회 { `D0.W` = WORD(A0), A0 += 2, `D0.W` = (`D0.W` × 2) & `ffff`, WORD(A4) = WORD(A3 + sext(`D0.W`)), A4 += 2 }, A4 = `D7`, RTS. [I] palette의 색 1..15를 변환 표로 옮긴다(색 0은 호출자가 `8000`으로 쓴다).
- `479e`: `D7` = `1f`, `D6` = A4, A4 += 2, A0 += 2, 15회 { `D0.W` = WORD(A0), A0 += 2; `D2.B` = `D0.B`, `D2.W` &= `1f`; `D0.W` >>= 5(논리); `D1.W` = `D0.W`, `D1.W` &= `1f`; `D0.W` >>= 5, `D0.W` &= `1f`; clamp(`D0`, BYTE `-23e`), clamp(`D1`, BYTE `-23c`), clamp(`D2`, BYTE `-23a`); `D0.W` <<= 5, `D0.B` |= `D1.B`, `D0.W` <<= 5, `D0.B` |= `D2.B`, `D0.W` ×= 2; WORD(A4) = WORD(A3 + sext(`D0.W`)), A4 += 2 }, A4 = `D6`, RTS.
  - clamp(X, v)(`ADD.B v,X; SPL D4; AND.B D4,X; CMP.B D7,X; SCC D4; OR.B D4,X; AND.B D7,X`): `X.B` = (`X.B` + v) & `ff`; `D4.B` = (`X.B` bit 7 = 0) ? `ff` : 0; `X.B` &= `D4.B`; `D4.B` = (`X.B` ≥ `1f`, 부호 없는 비교) ? `ff` : 0; `X.B` |= `D4.B`; `X.B` &= `1f`. [I] 채널 + fade를 0..31로 자른다.
- `4c40`/`504c`: `D0.W` = 0이면 `4718`/`479e`(A0 = 원본 a). `4c46`/`5052`: A0 ↔ A1 교환, `D7` = `1f`; `D0.W` ≥ `1f`(부호 없는 16 bit)이면 `4718`/`479e`(이제 A0 = 목표 c), 아니면 `4c50`/`505c`.
- `4c50`: `D6` = A4, `D5` = A2, A2 = `3f78`, `D0.W` <<= 6, A2 += sext(`D0.W`), A4 += 2, A0 += 2, A1 += 2, 15회 { `D0.W` = WORD(A1), A1 += 2; `D1.W` = WORD(A0), A0 += 2; 파랑: `D4.W` = `D0.W` & `1f`, `D3.W` = (`D1.W` & `1f`) − `D4.W`, `D3.B` = BYTE(A2 + sext(`D3.W`)), `D3.W` += `D4.W`; `D0.W` >>= 5, `D1.W` >>= 5; 초록: 같은 방식으로 `D4`·`D2`; `D0.W` >>= 5, `D1.W` >>= 5; 빨강: `D1.W` −= `D0.W`, `D1.B` = BYTE(A2 + sext(`D1.W`)), `D1.W` += `D0.W`; `D1.W` <<= 5, `D1.B` |= `D2.B`, `D1.W` <<= 5, `D1.B` |= `D3.B`, `D1.W` ×= 2; WORD(A4) = WORD(A3 + sext(`D1.W`)), A4 += 2 }, A2 = `D5`, A4 = `D6`, RTS. 빨강 채널은 `& 1f` 없이 `>> 10`이라 원본 WORD bit 15가 들어간다(색인 −63..63). [I] blend 표 `3f78 + 64×level`에서 (목표 − 원본) 차이를 비율로 줄여 원본에 더한다.
- `505c`: `4c50`과 같고, 세 채널 결과 뒤 compose 전에 clamp(`D1`, BYTE `-23e`), clamp(`D2`, BYTE `-23c`), clamp(`D3`, BYTE `-23a`)를 한다.

## carry

- [F] **소비 0, known 생산 0.** H3의 모든 Bcc는 같은 block에서 만든 flag를 읽는다(`4c46`/`5052`의 `BCC`도 같은 block의 `CMP.W`). BSR 복귀점(`71fe` `7218` `7282` `728a` `72ae` `72b6`)은 C를 읽지 않는다. 호출자 복귀점(`ea4` BSET+MOVE, `fb4` BRA → `ec4` BTST → `ef2`/`ed0`가 새 flag, `f4c` guard, `8b98` MOVE)도 H3 RTS 앞 C를 읽지 않는다. 따라서 carry 오류 문자열은 두지 않는다.
- [F] **FLOW_ONLY 268 block**(C 보존): cell `B_k` 256(`579c+26k`), `7188`(`L_255`, `LEA`만), `7194` `71d8` `71fe` `7252` `727e` `7282` `7286` `728a` `72aa` `72ae` `72b2`. `carry_preserving_pc`의 주석 붙은 case group 하나에 넣는다.
- [F] **Unknown 283 block**: 나머지(`MOVE`/`MOVEQ`/`TST`/`CMP`/`CMPA`/`ADD`/`SUB`/`SUBQ`/`OR`/`AND`/`LSL`/`LSR`/`EXG`+`CMP`, watchdog `MOVE.B` 포함 `L_0..L_254` 255, 고유 28).

## 경계·port·PVC·자료

- [F] **경계:** 호출자 복귀(RTS)뿐이다. 단위 시험은 반환 LONG = STOP으로 끝낸다. H1과 이어지는 행(`e98`/`fae` → `5728` → 복귀 `ea4`/`fb4`)으로 연결을 확인한다. rollback 탐침은 work RAM PC `10fe00..10fefe`를 쓴다(F4 시험 경계 관례).
- [F] **port(D7):** watchdog = `VideoPortWrite{300001,1,D0.B}` 1건(원본 쓰기 1건). PVC 쓰기는 `am_write`(PVC 기억·`pvc_effects`·port 기록). `7196`에서 bank가 `200000`(`2ffff2` = `1000`, `2ffff0` = 0)으로 바뀐 뒤 LONG `200004`/`200008`을 live bus로 읽는다.
- [F] **스택:** BSR 복귀 LONG, `7196`의 LONG push A6와 `7232`/`72d0` pop. work RAM 밖 스택은 기존 checked 오류다.
- [F] **work RAM:** `100010`(`-7ff0`), `104d92..105d92`(slot 표 16바이트 × 256: `+a` WORD 원본 번호, `+c` WORD 목표 번호, `+e` BYTE blend level, `+f` BYTE flag bit 7 dirty·bit 1 fade 제외), `105da2..107da2`(palette buffer 32바이트 × 256), `107dc2..107dd5`, `107ded`.
- [F] **ROM(live bus):** bank 창 LONG `200004`(palette 원본 표 기준 A6, 실제 ROM `0022bd12`)·`200008`(색 변환 표 A3, 실제 ROM `0025cb52`), 원본 palette A6 + (번호 << 5) + 2..30, 변환 표 A3 + sext(2 × 색), fixed blend 표 `3f78 + 64×level + (−63..63)`(level 1..30이므로 `3f79..4737`; level 30·빨강 차이 > 31이면 `4718..4737` code 바이트를 그대로 읽는다, 원본과 같음). [I] 번호가 크면 A6 + (번호 << 5)가 bank 창 끝을 넘을 수 있다. 그때는 기존 live bus 오류(`reached program bank physical span outside ROM` 등)다.

## 구현 범위와 규약

- routing 한 범위(결정 1). 짝수 PC 5,612개 중 block 시작 551, 내부 5,061. 내부 PC 직접 진입은 `unsupported animation frame head h3 PC`다.
- cell family는 PC 산술로 k와 종류(`B`/`L`)를 구한다(결정 2). helper는 반복문(결정 3).
- 기존 실행부는 고치지 않는다. 공유 최소 수정: `animation_machine.cpp` routing `else if` 하나와 carry 보존 case group 하나, `animation_machine_internal.h` 선언 하나, `Makefile`(source 목록·test target·실행 줄), `tools/verify_animation_machine.py` SOURCES.

## 시험 계획

- 단위 시험(`engine/tests/animation_machine_frame_head_h3_test.cpp`, `run_animation_machine`만): Unicorn 생성 fixture(scratch 생성기). 물리 ROM은 선언된 합성 바이트다(ROM 자료가 아니다): fixed `3f78..4738`과 bank `200000..240000`을 같은 공식(생성기·시험 공통)으로 채우고 LONG `200004` = `00201000`, `200008` = `00220000`을 둔다. 원본 번호·목표 번호는 합성 창 안을 가리키게 고른다.
  - 551 시작 전부를 block 표로 덮는다(시작 × 들어오는 C clear/set: native 후속·digest·port 수·C 분류). cell 512개 포함.
  - 전체 경로 fixture: timer 0 → `718c` RTS, 무 fade 재구성(같은 번호 `4718`, level 0/≥`1f`/중간 → `4c40`→`4718`(원본·목표)/`4c50`), fade 재구성(bit 1에 따라 `4718`/`479e`, `4c40`/`504c`의 세 갈래), timer > 1 단계·= 1 최종, 정수부 변화 0(`718c`)·≠ 0(cell 256, watchdog 256), clamp 양끝, 빨강 bit 15, 음수 `sext` 색인, H1 연결(`e98`→`ea4`, `fae`→`fb4`).
  - zero-step(551 × C 3), 내부 PC 5,061 전수(정확한 오류), 범위 홀수 양끝, RAM rollback 탐침, 공통 checked 오류(stack·정렬·bank 물리 범위).
- 돌연변이 검사(cell family 매개변수 포함), UBSan, 실제 ROM 차분(Unicorn vs C++ + 8 `program_rom_*.ms5d`), native F5 관측의 자연 H 구간 차분(H1+H3이 닿는 곳까지; 멈춤 위치 보고), base frame pass·RNG 400 무변화.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다. 작업 트리 `metalslug-h3`(base `c5181b6`), scratch `ms5-scratch/h3/`.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_frame_head_h3.cpp` `126b95efbd22c23d`, `engine/tests/animation_machine_frame_head_h3_test.cpp` `5fc4b0ff4df790be`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나(268 PC); `755bd30b9fc23c51`), `engine/src/animation_machine_internal.h`(선언 하나; `3e573e9a8ada8188`), `Makefile`(source 목록·test target·실행 줄; `a6f9bbbdd95b6b0a`), `tools/verify_animation_machine.py` SOURCES(`6c5dd2cbcc056994`). 결정 7 탐침 교체 1곳: `engine/tests/animation_machine_stage_entry_test.cpp`의 outside 탐침 `72ee`(이제 H3 내부 PC) → work RAM PC `10fe5c`(주석 포함, 논리 변경 없음; `00f719a438bb3cca`). public header는 바꾸지 않았다.
- [F] 실행부 case 집합 = scratch `starts.txt`(551). 고유 39는 `switch` case, cell 512는 PC 산술(`(pc − 578c) mod 26` ∈ {16, 22}). 내부 PC 5,061개(cell 내부 2,816 포함)는 모두 `unsupported animation frame head h3 PC`다.
- [F] `make -j3 all test`(작업 지시의 동시 3 process 상한): exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`), `tools/tests` unittest 257개 OK. H3 test 출력: `animation machine frame head h3: 127 fixtures (9 checked errors, 2 kept C, 6 splits), 551 blocks, 8509 calls`.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_test.sh ubsan`): H3 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만; scratch `gen/gen_h3.py` Unicorn 생성, 두 번 생성해 표 SHA256 `20911fe9ad385cab…` 동일): fixture 127(성공 118, checked 오류 9). 입력은 선언 LCG 채움 + 선언 slot 표 채움 + puts, 물리 바이트는 합성 창 두 개(`3f78..4718`, `200000..240000`, 공식 `syn_byte`)뿐(ROM 자료 아님). 551 시작 전부 block 표(× 들어오는 C Unknown/clear/set: native 후속·digest·port 수·C 분류; FLOW 268 C 보존, 나머지 Unknown; cell 후속 규칙 `B_k→L_k`, `L_k→B/L_(k+1)`, `L_255→718c`). zero-step 551 × 3, 내부 PC 5,061 전수, 홀수 PC 5(범위 양끝·cell 안), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`과 RTS가 RAM PC `10fe40`으로 가는 전체 경로 rollback. 전체 경로: idle, 무 fade/fade 재구성(256 slot, dirty 없음/전부), timer 단계·최종·정수부 불변, fade 제외 slot, helper 직접 진입(level 0/1/5/1c/1d/1f/20/8000/ffff, 32 bit 레지스터 상위 보존, 마지막 파랑 = `1f` SCC 경계), slot 모양 8 × fade 유무, H1 연결(`e98`→`ea4`, `fae`→`fb4`), 선언 중간 stop 6과 split = continuous 6쌍(포트 열 연결 포함). checked 오류 9: stack push 장치(`program bus write requires RAM mirror units`), 홀수 WORD 읽기·pop 3(`program bus requires even WORD/LONG address`), 합성 창 밖 원본·blend 표 끝 넘음 2(`missing or ambiguous physical program bus ROM byte`; level `1e`·빨강 차이 ≥ `20`은 실제 ROM에서는 `4718..4737` code 바이트를 읽는다), RAM 밖 쓰기 3(`unsupported animation machine write device`).
- [F] 돌연변이 검사(scratch `mut/mut_h3.py`, scratch 사본만 변형, 102개 + identity): 102/102를 test가 잡았다. cell family 매개변수(첫 PC·크기·수·`BSET`/`LEA` 위치·bit·BTST 변위·다음 cell·마지막 cell·watchdog 값·주소·누락) 15개 포함. 첫 실행에서 살아남은 2개 중 `clamp-scc`(SCC `≥`→`>`, `D4.B`만 다름)는 fixture `479e-blue-1f`로 잡혔고, `479e-d2-word`(`MOVE.B`+`AND.W`를 `MOVE.W`+`AND.W`로)는 결과가 같은 등가 돌연변이라 `AND.W`→`AND.B` 계열 3개(`479e-d2-andb` `479e-d1-andb` `blend-d4-byte`)로 바꾸고 wide 레지스터 fixture 6개를 더해 잡았다.
- [F] 실제 ROM 차분(scratch `realrom/real_h3.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, 초기 bank `200000`/`300000`, 무작위 work RAM + 구조 fade·slot 표, 실제 LONG `200004` = `0022bd12`·`200008` = `0025cb52`): 3 seed × 1,500 case 불일치 0/0/0, 551 시작 모두 진입, 모든 case가 STOP에서 끝남, watchdog event 149,206/153,405/152,347. native가 깨끗이 멈추지 않은 case(큰 palette 번호로 bank 창 밖 읽기, 무작위 RTS 대상)는 건너뜀 36/49/40. C++ stop C는 모두 Unknown.
- [F] native F5 관측 차분(scratch `realrom/nat_h3.py`, `artifacts/animation_machine_frame_head_native/observation.json` SHA256 `4fe4f796…`, 읽기 전용): 자연 seed 136개의 pass-end dump 4,975개에서 (a) 시작 digest = 기록 `h.start` 4,975/4,975, (b) 같은 선언 규약으로 H 전체를 native 재실행해 기록 `h.end`·port digest·대기 목록 재현 4,975/4,975, (c) H1+H3 구간 native vs C++ 불일치 0. **이제 H 구간이 멈추는 곳**: H1 `ea4`(raster 읽기, C++에서는 `animation machine external read queue empty`; 선언 stop) 3,332, 역방향 writer 표 `11792` 842 · `117a2` 651 · `11796` 107 · `117a6` 43(H4, 합 1,643). `5728` 진입 3,332회, 실행된 H3 leader 310(고유 21, cell 289; 명령 hook 기준). `16bd0` 선언 해제 1,543회. C++ stop C는 모두 Unknown.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `c5181b6` pass 14,648·node 126,688 일치, 불일치 0 → H3 뒤 `diff_results.json` 바이트 동일.
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 134·pass 53,600·node 403,677·불일치 0 → H3 뒤 같은 값. `verification.json` 차이는 `engine_source_sha256`의 `animation_machine.cpp`·새 파일 항목과 seed 2개 기록의 `current_router_sha256`뿐이다. 새 완주 0, 잃은 seed 0(frame head는 여전히 F2 pass의 stop이다).
- [F] 무효화 목록: `animation_machine_stage_entry_test.cpp` outside `72ee`(위에서 교체). Python verifier 중 H3 PC를 routing 밖 기대로 쓰는 것은 찾지 못했다(`verify_control_caller*.py`·`verify_callback_frame_flow.py` 등의 `5728`은 animation machine과 무관한 이전 원본 재생 도구다).
- [U] 남은 미확인: 자연 H의 다음 경계는 H1 `ea4` raster 읽기(queue API 병렬 작업)와 H4 writer 표다. palette 번호가 커서 A6 + (번호 << 5)가 bank 창을 넘는 경우의 원본 의미(자연 자료에서 일어나는지)는 확인하지 않았다(C++는 기존 live bus 오류). level `1e`에서 blend 표 행이 `4718` code 바이트로 이어지는 읽기가 자연에서 일어나는지도 확인하지 않았다(실제 ROM 차분은 같은 바이트를 읽어 일치).
