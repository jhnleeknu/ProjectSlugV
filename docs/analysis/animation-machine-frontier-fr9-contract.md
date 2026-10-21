# frontier 단위 FR9(C 뒤에만 IO에 나타나는 영역 D의 마지막 묶음: `af990` 객체 계열, 계산 점프 7개) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. FR8 계약(`animation-machine-frontier-fr8-contract.md`)의 "FR9 명세" 절을 범위·block·표의 기준으로 삼고, 구조·공통 규칙은 FR8 계약을 따르며 다른 점만 적는다. 메인 지시: FR8 뒤 남은 C 뒤 영역 D 51 PC(모두 `af990` 계열)를 FR9 하나로 연결해 D 남은 실행 PC를 **0**으로 만든다. 계산 표는 모두 전사하고, C 뒤 코드라 단위 시험·V1은 선언 상태와 IO state pack의 자연 node 상태(family `natural`)로 선다. 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 이 단위의 코드·고정 자료는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. 이 단위는 bank 창을 읽지 않는다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `aabf96e`(branch `claude/fr9-core` = FR8 커밋, FR1..FR8 routing). routing 기준 `engine/src/animation_machine.cpp` SHA256 `9592e227f3a4cfe478dafa4fcf3842dae50072fd7adbb828fd5108f0fe4a270b`(= FR8 검증의 routing), `animation_machine_internal.h` `a7d92b011f252b522dc8ac0e7f2c0b9bb3c0f72e2bb1a97bd9803f0e0deb400d`.
- [F] 관측 입력: native IO 관측 `artifacts/animation_machine_io_native`(읽기 전용; state pack `states/boot-demo-0/boot.pack.gz`). FR8 IO 예측 일치 frame **165,714**.
- [F] 정적 디코드: capstone M68000, FR8과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, 범위 안 설치 값, 범위 밖에서 들어오는 실제 분기 대상, PC 상대 계산 점프 `JMP d(PC,D0.W)` 뒤 `BRA.W` 표의 모든 항목). routing된 PC, `RTS`, `TRAP`에서 멈춘다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr9/`
  - `tools/`: FR8 scratch 도구의 경로만 `metalslug-fr9`, `ms5-scratch/fr9`로 바꾼 사본(`unit_fr8.py` `fr8tab.py` `fclos.py` `hroute.py` `dstate.py` `dleft.py` `cscan.py` `cread.py` `inrefs9.py` `probe_scan_fr7.py`)과 새 `natsearch.py`(IO pack에서 이 단위의 callback을 가진 자연 node 검색).
  - 재현: `cd /Users/start/Workspce/metalslug-fr9 && FRG='af990=af8cc af8f2 af910 af990 afcda afd7c aff00 aff30 b051a' .venv/bin/python /Users/start/Workspce/ms5-scratch/fr9/tools/unit_fr8.py B D` → `starts_fr9.txt`(시작 220개) SHA256 `f2ba650fc7e314c55521b70677110119844e5feac9715bab04e634879b070dff`(FR8 명세와 같음), `unit_fr9.new`(block별·범위 전체 디코드), `inrefs9.out`, `probe_fr9.out`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **재측정**(`dleft.py`, routing `9592e227…`): 실행된 routing 밖 PC는 C 620 / D 51 / E 220, D 중 C 무관 0 / **C 뒤 51**, 예측 일치 frame 165,714, 첫 정지 영역 C·E 15 / C 1(D 0). FR8 기록과 같다.
- [F] **정적 재디코드**(작업자 자체 실행): 진입 `af8cc` `af990`, **220 block 시작**, 6 범위, 명령 381, 짝수 PC 838(내부 618), 이어 붙인 바이트 1,676, SHA256 `9c3cc2bd6869c9c20db81bb8f0efce6735f7784f8a52ca2dd1584ccbaac7959e`. 덮는 실행 PC 51개 = D 남은 51개 전부(TB 잔재 0, 연속 Bcc 묶음 0). 계산 점프 7개, TRAP 0, `JSR (An)` 0. 기존 routing과 겹침 0(각 범위 앞뒤: `af92c` `afc16` `b005e` `b057e`은 N09, `af8ca` `afb3c` `afcf0` `afed8` `afefe` `b0518`은 routing 밖). FR8 명세의 모든 수치와 같다.
- [F] **예측**: FR9 뒤 D 남은 실행 PC **51 → 0**, IO 일치 frame 165,714 그대로(C 뒤라 사슬이 닿지 않음), 첫 정지 영역 변화 없음(C·E 15, C 1). 구현 뒤 `dleft.py`로 확인한다.
- [F] **F4 범위 문서와의 겹침**: R09 행 `af3fe..b05bc`가 FR9 6 범위를 모두 포함한다. R09는 FR9 범위를 빼야 한다(결정 6; `area-d-completion-plan.md`에 메모).

## 요약

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `af8cc..af92c` | 96 | `a60f98c063c0352b9da09ed2959c1a3241eec6cb085ca52a9f2a7027b59b353a` | 10 | 48 |
| `af990..afb3c` | 428 | `4650167caf11fc20b0c10a1b810f212756e33afd99b54bfbd6f4a0843f0ca4b6` | 91 | 214 |
| `afb3e..afc16` | 216 | `9e3cf192c4f7d19771f68e82fdeb628564b0698dafc93db50f5ce4c48fd71192` | 28 | 108 |
| `afcf2..afed8` | 486 | `31c8ba040ab51d8d7df7044ecbc2b44fb1c61235a9e9c69b903518d1372e2b62` | 47 | 243 |
| `aff00..b005e` | 350 | `9b3e2ab9fbcaf2f1b19413a3dbbfa0593bea2c4c2bcbdb9c201353bcdd812a27` | 38 | 175 |
| `b051a..b057e` | 100 | `bbbf26334f12987385169dfa60392e5dd3a38da69084c94d10bfee235ad13766` | 6 | 50 |
| 합계 FR9 | 1676 | 이어 붙인 바이트 `9c3cc2bd6869c9c20db81bb8f0efce6735f7784f8a52ca2dd1584ccbaac7959e` | **220** | 838(내부 618) |

- [F] closure가 6 범위를 빈틈없이 덮는다. 범위 사이: `af92c..af990` N09, `afb3c` 2바이트 `4e75`(도달하지 않는 `RTS`; routing 밖), `afc16..afcbe` N09, `afcbe..afcf2` routing 밖 형제 코드(설치 `afcda`의 몸통; 이 단위가 들어가지 않음), `afed8..aff00` routing 밖(쓰기만 하는 설치 값 `afed8`의 몸통), `b005e..b051a` N09·U15·routing 밖(`b04cc..b051a`), `b057e..` N09.
- [F] **명령 종류**(381개): `BRA.W` 109(표 항목 95 + 14), `JSR` 58(그중 `JSR d(PC)` 7: `b051a` 6곳·`b0468` 1곳), `JMP` 10(계산 점프 7 + `JMP 2a00` 3), `MOVE.W` 40, `MOVE.L` 21, `ADD.W` 16, `MOVEA.L` 15, `ANDI.W` 14, `MOVE.B` 7, `Bcc` 21(`BCC` 8·`BPL` 6·`BEQ` 5·`BNE` 2·`BMI` 2), `ADDI.B` 5, `ANDI.B` 4, `TST.B` 4·`TST.W` 3, `CMPI.B` 4·`CMPI.W` 1, `BTST` 4·`BSET` 4·`BCLR` 4·`BCHG` 1, `SUBQ.B` 3·`SUBQ.W` 2, `SUB.L` 3·`SUB.W` 2·`SUBI.B` 1, `EXT.L` 3, `LSL.L #8` 3, `ASR.L #2/#6` 3, `ADDI.W` 3, `ADDI.L` 2, `SF.B` 2·`ST.B` 1, `CLR.B` 1, `MOVEQ` 1, `MOVEM.W (A7)+,D0-D6` 1, `LEA` 1, `ORI.B #1,CCR` 1, `RTS` 1. **TRAP·DIVU/DIVS·MULU/MULS·ABCD·ADDX/SUBX·SWAP·`JSR (An)`·bank 창 읽기·I/O port 쓰기 없음.**
- [F] **나가는 곳**(모두 다른 실행부의 `case` block 시작으로 routing됨; 21개 확인): callee `2986`(buffer_cue) `3af8`(sound) `8ff4`(cleanup) `43e34`(cleanup) `43ea4`(U04) `443d2`(U02) `490ba`(U12) `49214`(N05) `49274`(U08) `49a58`(stage_area) `49f8c` `49fc6`(interpreter) `4be06`(U11) `4be34`(U08b) `e9112`(FR1b) `b0468`(N09), 분기 출구 `af92c` `af96a` `afc16` `b005e`(N09), `JMP 2a00`. routing 밖으로 나가는 곳은 없다. 이 단위의 분기·점프가 다른 실행부 block의 **중간**으로 들어가는 곳은 없다(출구 21개가 모두 block 시작).
- [F] **참조**(ROM `<100000` 짝수 오프셋 전수 디코드 + LONG 상수, scratch `inrefs9.out`): 범위 밖에서 들어오는 실제 진입은 N09 `af768 MOVE.L #af8cc,(A6)`, `af97e MOVE.L #af990,(A6)`, `af626 MOVE.L #afbbe,(A6)`(모두 routing된 N09), routing 밖 `af3da BRA.W afe30`, `afefc BRA.W aff24`, `afee2 JSR b051a(PC)`(모두 이 단위의 block 시작). 그 밖의 일치(`33670`/`3db10 MOVE.L #b0000,36(A0)`)는 속도 상수다. 다른 실행부가 이 단위 block의 중간으로 들어가는 곳은 없다.

## 공통 규칙·native 검증 계획

FR2..FR8 계약의 같은 절을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr9.cpp`, 함수 `animation_objects_fr9_block`. 오류 문자열은 `unsupported animation objects fr9 PC`(범위 안 내부 PC 직접 진입·계산 착지), `objects fr9 caller requires known carry`(C 소비 block에 Unknown C; 소비자 5개). 그 밖의 오류는 공용 bus/스택 오류와 `2986`의 기존 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(6 범위, FR8 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 5개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`, stage_event / stage_event_ops `CPP_PINS`(옛 값은 주석).
- **경계.** 설치 값 `af8f2`(`af8ec`) `afd7c`(`afd76`) `aff30`(`aff2a`) `afe40`(`afe3a`) `b001a`(`b0014`)는 바로 다음 PC라 그 block으로 들어가고, `af92c`(`af926`) `afc16`(`afc10`)은 바로 다음 PC이지만 N09 시작이라 N09로 들어간다. **쓰기만 하는 설치**: `af910`(`af906`, 뒤는 `BRA.W af96a`), `aff00`(`afe7a`, 뒤는 `afe80`), `afed8`(`afe8e`, 뒤는 `BRA.W b005e`; range 밖·routing 밖). `af910` `aff00`은 다른 경로의 block 시작이기도 하다. `2986` 자식 값 `b3dbc`와 `490ba`의 A0 `caba0`, `49f8c`의 A1 `b0e94` `b10f0` `b12ac` `b0fe8` `b13ee` `b1076`, `2986`의 A1 `100bf4`는 넘기기만 한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): FR2와 같다. 행의 run stop은 실패 block 바로 뒤 PC다.
- **자료 읽기**(live bus, 상한 검사 없음): RAM의 node field(A6), 부모 node LONG `c(A6)`의 BYTE `62`(읽고 씀), 자식 A0의 WORD `76..7e`(쓰기), 스택. 이 단위는 ROM 자료·bank 창을 읽지 않는다(callee에게 주소만 넘김). 그래서 단위 시험은 합성 physical byte를 두지 않는다(빈 physical ROM). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** JSR 복귀 LONG. `b0524`: `MOVE.W #0,-(A7)` ×3, `MOVE.W 94(A6),-(A7)`, `MOVE.W 92(A6),-(A7)`, `MOVE.W #10,-(A7)`, `MOVE.W #0,-(A7)`(WORD 7개, A7 −= 14) → `2986` → `b0556`: `MOVEM.W (A7)+,D0-D6`(낮은 주소부터 D0..D6, 각 WORD를 LONG으로 부호 확장, A7 += 14; flag를 바꾸지 않음). 홀수 A7은 checked 오류다. 직접 진입 world는 `b0556`의 WORD 7개를 복귀 LONG 아래에 선언한다(V1 spec `STACK`).
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B` `ADD.W` `SUB.W` `ADDI.W` `ANDI.W` `ANDI.B` `ADDI.B` `SUBI.B` `SUBQ.W/.B`). `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`EXT.L`·`LSL.L`·`ASR.L`·`MOVEM.W`(부호 확장)은 LONG 전체. `EXT.L D0` = WORD의 부호 확장(위 `ANDI.W`/`ADDI.W` 뒤라 항상 양수). `LSL.L #8`은 LONG 안에서 밀어냄. `ASR.L #6`/`#2`는 부호 유지 오른쪽 이동. `ADDI.L #ffffb000`/`#ffff8000`은 LONG 덧셈(mod 2^32). 계산 점프 색인 = `ANDI.W` 뒤 WORD 안에서 두 번 `ADD.W`(4배), PC := 표 + sext(D0.W). 비교(같은 block 안에서 만들고 소비): `SUBQ.W #1,D0` + `BMI`(새 WORD의 bit 15; `8000` → `7fff`은 넘침이지만 N = 0이라 거짓), `SUBQ.W #1,96(A6)` + `BPL`(새 WORD bit 15 = 0), `CMPI.B #1b,D0` + `BCC`(BYTE 무부호 ≥), `TST.B 5f(A6)` + `BPL`(BYTE bit 7), `TST.W D0` + `BPL`/`BMI`(WORD bit 15; LONG·BYTE와 다름), `TST.B 9b(A6)` + `BEQ`, `CMPI.B #b,5e(A6)` + `BNE`, `CMPI.W #0,92(A6)` + `BEQ`, `BTST` + `BEQ`/`BNE`.

## 계산 점프 7개와 표(결정 2)

모두 `ANDI.W #m,D0; ADD.W D0,D0; ADD.W D0,D0; JMP t(PC,D0.W)`(block 시작 = `ANDI.W`). PC := t + sext(4·(D0.W ∧ m)의 WORD)로 routing을 거친다(FR8 `42f9a`와 같음). D0 상위 WORD는 유지된다. 표 항목은 모두 `BRA.W`이고 이 단위의 block 시작이며 대상도 이 단위 안이다(원본 바이트에서 전사).

- [F] **`af9bc`**(m = `ff`, t = `af9c8`; 앞 block `af9b0`: D0.B := BYTE `5e`, `CMPI.B #1b,D0; BCC.W afb3e`) 27칸 `af9c8..afa30`: 색인 0 1 → `afb3e`, 2 3 → `afb58`, 4 → `afb3e`, 5 → `afb72`, 6 → `afb3e`, 7 → `afbbe`, 8 → `afb3e`, 9 → `afb72`, `a` → `aff52`, `b` → `aff86`, `c` `d` → `afb72`, `e` → `afb3e`, `f` → `afb72`, `10`..`1a` → `afb3e`.
- [F] **`afa40`**(m = `ff`, t = `afa4c`; 앞 block `afa34`: 같은 꼴, `BCC.W afba4`) 27칸 `afa4c..afab4`: `a` → `aff52`, `b` → `aff86`, 나머지 → `afba4`.
- [F] **`afac4`**(m = `ff`, t = `afad0`; 앞 block `afab8`: 같은 꼴, `BCC.W aff00`) 27칸 `afad0..afb38`: `a` → `aff52`, `b` → `aff86`, 나머지 → `aff00`.
- [F] **`afb44`**(m = 1, t = `afb50`; 앞 block `afb3e JSR 49a58`): 0 → `afbbe`, 1 → `afe98`. **`afb5e`**(m = 1, t = `afb6a`; `afb58`): 0 → `afcf2`, 1 → `afe98`. **`afb78`**(m = 7, t = `afb84`; `afb72`): 0 1 → `afbbe`, 2 → `afe98`, 3 4 → `afcf2`, 5 6 → `afda6`, 7 → `aff00`. **`afbaa`**(m = 1, t = `afbb6`; `afba4`): 0 → `aff00`, 1 → `afe0a`.
- [F] 표 항목 합 95(27·3 + 2 + 2 + 8 + 2). m = 1/7인 4개는 같은 block의 `ANDI.W`가 색인을 표 안으로 묶으므로 어떤 D0로 직접 들어와도 표 밖에 떨어지지 않는다. m = `ff`인 3개는 앞 block의 `CMPI.B #1b` + `BCC`가 정상 경로의 색인을 0..`1a`로 묶는다. **직접 진입한 D0.B ≥ `1b`**는 원본대로 표 뒤(t + 4·k, k ≤ `ff`)로 떨어지고 그 PC를 routing이 판정한다(FR1 결정 3): 이 단위의 시작이면 실행(예: `af9bc` k = `1b` → `afa34`, `afa40` k = `1b` → `afab8`), 이 단위의 내부면 `unsupported animation objects fr9 PC`(예: `af9bc` k = `1c` → `afa38`, `afac4` k = `1c` → `afb40`), N09 범위면 N09의 판정, routing 밖이면 `unsupported animation machine PC`(예: `afac4` k = `1b` → `afb3c`). 최대 착지 PC는 `afdc4`/`afe48`/`afecc`.

## carry

- [F] **소비 block 5개**(Clear 쪽 / Set 쪽): `afd90 BCC.W afda2`(`49fc6`; `afda2` / `afd94`), `aff3c BCC.W aff4e`(`49fc6`; `aff4e` / `aff40`), `b0048 BCC.W b005a`(`49fc6`; `b005a` / `b004c`), `afe6a BCC.W afe84`(`b0468` N09; `afe84` / `afe6e`), `b0556 MOVEM.W (A7)+,D0-D6; BCC.W b057c`(`2986`; `b057c` / `b055e`; `MOVEM.W`는 flag를 바꾸지 않는다). 생산자는 모두 routing된 실행부이고 known C를 돌려준다(`49fc6`: LONG `26(A6)` = 0이면 Set, interpreter 끝은 그 실행부의 C; N09 `b0468`: WORD `3a` ≥ 0이면 Clear, 아니면 `4ae4a` 결과로 Clear/Set; `2986`: 성공 Set, 실패는 아래).
- [F] **known C 생산 block**: `b0578`(`ORI.B #1,CCR` → Set, fall-through `b057c RTS`). `b057c`는 소비자가 아니라 C를 Unknown으로 바꾼다(아래).
- [F] **C를 넘기는 `RTS`: 없다.** `b051a`의 직접 호출자 6곳(`afcfc` `afea2` `aff0a` `aff52` `aff86`, routing 밖 `afee2`)은 복귀 뒤 C를 읽지 않는다(scratch `cread.py`: 0곳). 원본에서는 `b057c RTS`가 C(`b051a`의 `CMPI.W #0` Clear, `b0556` Clear, `b0578` Set)를 넘기지만 읽는 곳이 없다. 다른 진입은 node callback이다.
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 5개다: `afd90` `aff3c` `b0048` `afe6a` `b0556`. Unknown C로 소비자에 들어오면 checked 오류다. block 경계를 건너 다시 계산하는 flag와 X는 없다(`cscan.py`: 위 5개와 `b0578` ORI, `b057c` RTS 외에 경계를 건너 flag를 읽는 block 0; `afdd2` `afece`는 flag를 넘기지만 다음 block이 읽지 않는다).
- [F] **`2986`의 실패 경로**(`b0524`): `2986`(buffer_cue)의 실패 경로는 호출자의 X가 필요하다(`cue wrapper failure requires known caller X`, 2986 caller-X 제한; 기존의 의도된 checked 오류). 이 단위는 X를 만들지 않으므로 실패 경로는 그 오류로 끝난다. 실제 ROM 차분은 이 경우를 그 오류로 분류해 센다. 그래서 `b0556`의 Clear 쪽은 선언 C(단위 시험·V1 오류 행 외)로만 들어간다.

## 객체 `af8cc`(N09 `af768`의 설치 값)

- **`af8cc`**: A0 := `caba0`, `JSR 490ba`(U12; 복귀 `af8d8`). **`af8d8`**: D0.W −= 1, 새 WORD bit 15 = 1 → `af910`, 아니면 `af8de`: WORD `96` := D0.W, WORD `2c` := `80`, BYTE `9d` := 0(`SF.B`), LONG `(A6)` := `af8f2`(들어감).
- **`af8f2`**(설치 값): `JSR 4be06`(복귀 `af8f8`). **`af8f8`**: `JSR 49fc6`(C는 읽지 않음; 복귀 `af8fe`). **`af8fe`**: WORD `96` −= 1, 새 bit 15 = 0 → `af90c`, 아니면 `af906`: LONG `(A6)` := `af910`(쓰기만). **`af90c`**: `BRA af96a`(N09).
- **`af910`**(설치 값·분기 대상): WORD `20` := `163`, A1 := `b0e94`, D0.W := `100`, `JSR 49f8c`(복귀 `af926`). **`af926`**: LONG `(A6)` := `af92c`, N09 `af92c`로.
- [I] 등장 대기: `490ba`가 돌려준 D0.W(대기 frame 수 [I])만큼 `af8f2`에서 anim을 돌린 뒤 `af910`에서 다음 anim(`b0e94`)으로 바꾸고 N09 `af92c`로 넘어간다.

## 객체 `af990`(N09 `af97e`의 설치 값): 피격 반응 선택

- **`af990`**: `JSR 8ff4`(복귀 `af996`). **`af996`**: `JSR e9112`(복귀 `af99c`). **`af99c`**: BYTE `61` bit 1 = 1 → `afa34`, 아니면 `af9a6`: BYTE `15` bit 7 = 0 → `afab8`, 아니면 `af9b0`.
- **`af9b0`** / **`afa34`** / **`afab8`**: D0.B := BYTE `5e`, (무부호) ≥ `1b` → `afb3e` / `afba4` / `aff00`, 아니면 계산 점프 `af9bc` / `afa40` / `afac4`(위 절).
- **`afb3e`** / **`afb58`** / **`afb72`** / **`afba4`**: `JSR 49a58`(난수; 복귀 `afb44` / `afb5e` / `afb78` / `afbaa`) 뒤 계산 점프(위 절).
- [I] BYTE `5e` = 맞은 무기 종류 [I], BYTE `61` bit 1 / BYTE `15` bit 7로 세 표 중 하나를 고르고, 난수로 반응 anim(`afbbe` 낙하, `afcf2`/`afe98` 튀어오름, `afda6`/`afe0a` 날아감, `aff00` 쓰러짐, `aff52`/`aff86` 특수 무기 `a`/`b`)을 고른다.

## 반응 `afbbe`(N09 `af626`의 설치 값)

- **`afbbe`**: BYTE `61` bit 7 = 0 → `afbe2`, 아니면 `afbc8`: WORD `20` := `163`, A1 := `b10f0`, D0.W := `100`, `JSR 49f8c`(복귀 `afbde`: `BRA afbf8`). **`afbe2`**: 같은 꼴(A1 := `b12ac`; 복귀 `afbf8`). **`afbf8`**: `JSR 49a58`(복귀 `afbfe`). **`afbfe`**: D0.W ∧= `7f`, WORD `2c` += D0.W, WORD `96` := 0, BYTE `63` := 0, LONG `(A6)` := `afc16`, N09 `afc16`으로.

## 반응 `afcf2` / `afe98` / `aff00` 공통 머리와 `b051a`

- **`afcf2`** / **`afe98`** / **`aff00`** / **`b000a`**: D0.W := `187f`, `JSR 3af8`(소리; 복귀 `afcfc` / `afea2` / `aff0a` / `b0014`).
- **`afcfc`** / **`afea2`** / **`aff0a`** / **`aff52`** / **`aff86`**: `JSR b051a(PC)`(복귀 `afd00` / `afea6` / `aff0e` / `aff56` / `aff8a`).
- **`b051a`**(subroutine): WORD `92` = 0 → `b057c RTS`, 아니면 `b0524`: WORD 7개 넣기(위 "스택"), A0 := `b3dbc`, D0.W := `14`, A1 := `100bf4`, `JSR 2986`(자식; 복귀 `b0556`). **`b0556`**(소비자): D0..D6 := 꺼낸 WORD의 부호 확장(D0 = 0, D1 = `10`, D2 = sext(WORD `92`), D3 = sext(WORD `94`), D4..D6 = 0이 정상 경로), Clear → `b057c`, Set → `b055e`: WORD `76(A0)` := D2.W, `78(A0)` := D3.W, `7a(A0)` := D4.W, `7c(A0)` := D5.W, `7e(A0)` := D6.W, `JSR 49214`(복귀 `b0578`). **`b0578`**: C := 1(fall-through `b057c`). **`b057c`**: `RTS`.
- [I] WORD `92`/`94`(효과 위치 [I])가 0이 아니면 자식 `b3dbc`(피격 효과 [I])를 그 위치 기록과 함께 만든다.

## 반응 `afcf2`(튀어오름)

- **`afd00`**: WORD `20` := `163`, A1 := `b0fe8`, D0.W := `100`, `JSR 49f8c`(복귀 `afd16`). **`afd16`**: `JSR 49a58`(복귀 `afd1c`). **`afd1c`**: D1.B := D0.B ∧ `1f`(D1 상위 유지), BYTE `5f` bit 7 = 0 → `afd38`, 아니면 `afd2a`: D1.B += `48`, BYTE `15` bit 0 := 1, `BRA afd42`. **`afd38`**: D1.B += `18`, BYTE `15` bit 0 := 0(fall-through `afd42`).
- **`afd42`**: `JSR 49a58`(복귀 `afd48`). **`afd48`**: D0.W := (D0.W ∧ `3ff`) + `200`, D0 := sext(D0.W) << 8(LONG), `JSR 443d2`(속도; 복귀 `afd5a`). **`afd5a`**: LONG `36` := D0, LONG `3a` := D1, `JSR 49a58`(복귀 `afd68`). **`afd68`**: D0.W ∧= `7f`, WORD `2c` −= D0.W, `JSR 49274`(복귀 `afd76`). **`afd76`**: LONG `(A6)` := `afd7c`(들어감).
- **`afd7c`**(설치 값): LONG `3a` += `ffffb000`, `JSR 43ea4`(복귀 `afd8a`). **`afd8a`**: `JSR 49fc6`(복귀 `afd90`). **`afd90`**(소비자): Clear → `afda2`: `BRA b005e`(N09); Set → `afd94`: A0 := LONG `c(A6)`, BYTE `62(A0)` −= 1, `JMP 2a00`.

## 반응 `afda6` / `afe0a` / `afe30` 상태(날아감·착지)

- **`afda6`**: WORD `20` := `163`, A1 := `b13ee`, D0.W := `100`, `JSR 49f8c`(복귀 `afdbc`). **`afdbc`**: `JSR 49a58`(복귀 `afdc2`). **`afdc2`**: D1.B := (D0.B ∧ `3f`) + `20`, D0.W bit 15 = 0 → `afdd8`, 아니면 `afdd2`: BYTE `15` bit 0 반전(fall-through `afdd8`). **`afdd8`**: `JSR 49a58`(복귀 `afdde`). **`afdde`**: D0.W := (D0.W ∧ `7ff`) + `300`, D0 := sext(D0.W) << 8, `JSR 443d2`(복귀 `afdf0`). **`afdf0`**: LONG `36` := D0, LONG `3a` := D1, `JSR 49a58`(복귀 `afdfe`). **`afdfe`**: D0.W ∧= `7f`, WORD `2c` += D0.W, `BRA afe30`.
- **`afe0a`**: WORD `20` := `163`, A1 := `b13ee`, D0.W := `100`, `JSR 49f8c`(복귀 `afe20`). **`afe20`**: D0 := 0, LONG `36` := 0, LONG `3a` := 0, BYTE `15` bit 1 := 0(fall-through `afe30`).
- **`afe30`**(밖 `af3da`의 분기 대상): BYTE `15` bit 3 := 1, BYTE `9b` := `ff`(`ST.B`), LONG `(A6)` := `afe40`(들어감). **`afe40`**(설치 값): LONG `3a` += `ffff8000`, `JSR 4be34`(복귀 `afe4e`). **`afe4e`**: `JSR 49fc6`(C는 읽지 않음; 복귀 `afe54`). **`afe54`**: D0 := LONG `36`, D0 := ASR.L(D0, 6), LONG `36` −= D0, BYTE `9b` = 0 → `afe84`, 아니면 `afe66`: `JSR b0468(PC)`(N09; 복귀 `afe6a`). **`afe6a`**(소비자): Clear → `afe84`, Set → `afe6e`: `JSR 49a58`(복귀 `afe74`). **`afe74`**: D0.W bit 15 = 0 → `afe80`, 아니면 `afe7a`: LONG `(A6)` := `aff00`(쓰기만; fall-through `afe80`). **`afe80`**: BYTE `9b` := 0(fall-through `afe84`). **`afe84`**: BYTE `15` bit 7 = 0 → `afe94`, 아니면 `afe8e`: LONG `(A6)` := `afed8`(쓰기만; fall-through `afe94`). **`afe94`**: `BRA b005e`.

## 반응 `afe98`(작은 튀어오름)

- **`afea6`**: WORD `20` := `163`, A1 := `b0fe8`, D0.W := `100`, `JSR 49f8c`(복귀 `afebc`). **`afebc`**: BYTE `5f` bit 7 = 0 → `afece`, 아니면 `afec4`: BYTE `15` bit 0 := 1, `BRA afed4`. **`afece`**: BYTE `15` bit 0 := 0(fall-through `afed4`). **`afed4`**: `BRA aff24`.

## 반응 `aff00`(쓰러짐)과 `aff52` / `aff86`(무기 `a` / `b`), 착지 `b001a`

- **`aff0e`**: WORD `20` := `163`, A1 := `b1076`, D0.W := `100`, `JSR 49f8c`(복귀 `aff24`). **`aff24`**(밖 `afefc`의 분기 대상): `JSR 49274`(복귀 `aff2a`). **`aff2a`**: LONG `(A6)` := `aff30`(들어감). **`aff30`**(설치 값): `JSR 43e34`(복귀 `aff36`). **`aff36`**: `JSR 49fc6`(복귀 `aff3c`). **`aff3c`**(소비자): Clear → `aff4e`: `BRA b005e`; Set → `aff40`: A0 := LONG `c(A6)`, BYTE `62(A0)` −= 1, `JMP 2a00`.
- **`aff56`**: `JSR 49a58`(복귀 `aff5c`). **`aff5c`**: D1.B := D0.B ∧ `3f`, BYTE `5f` bit 7 = 0 → `aff78`, 아니면 `aff6a`: D1.B += `50`, BYTE `15` bit 0 := 1, `BRA aff82`. **`aff78`**: D1.B −= `f`(BYTE 순환), BYTE `15` bit 0 := 0(fall-through `aff82`). **`aff82`**: `BRA aff9a`.
- **`aff8a`**: `JSR 49a58`(복귀 `aff90`). **`aff90`**: D1.B := (D0.B ∧ `3f`) + `20`(fall-through `aff9a`).
- **`aff9a`**: `JSR 49a58`(복귀 `affa0`). **`affa0`**: D0.W := (D0.W ∧ `7ff`) + `a00`, D0 := sext(D0.W) << 8, `JSR 443d2`(복귀 `affb2`). **`affb2`**: LONG `36` := D0, LONG `3a` := D1, `JSR 49a58`(복귀 `affc0`). **`affc0`**: D0.W bit 15 = 1 → `affe0`, 아니면 `affc6`: A1 := `b0fe8`(WORD `20` := `163`, D0.W := `100`, `JSR 49f8c`; 복귀 `affdc`: `BRA afff6`). **`affe0`**: 같은 꼴(A1 := `b13ee`; 복귀 `afff6`). **`afff6`**: `JSR 49a58`(복귀 `afffc`). **`afffc`**: D0.W ∧= `7f`, WORD `2c` −= D0.W, `JSR 49274`(복귀 `b000a`). **`b000a`**: D0.W := `187f`, `JSR 3af8`(복귀 `b0014`). **`b0014`**: LONG `(A6)` := `b001a`(들어감).
- **`b001a`**(설치 값): BYTE `5e` ≠ `b` → `b0032`, 아니면 `b0024`: D0 := LONG `36`, D0 := ASR.L(D0, 2), LONG `36` −= D0, `BRA b003c`. **`b0032`**: 같은 꼴(LONG `3a`; fall-through `b003c`). **`b003c`**: `JSR 43ea4`(복귀 `b0042`). **`b0042`**: `JSR 49fc6`(복귀 `b0048`). **`b0048`**(소비자): Clear → `b005a`: `BRA b005e`; Set → `b004c`: A0 := LONG `c(A6)`, BYTE `62(A0)` −= 1, `JMP 2a00`.
- [I] `5e` = `b`이면 가로 속도(`36`), 아니면 세로 속도(`3a`)를 매 frame 1/4씩 줄인다. anim이 끝나면(`49fc6` Set) 부모의 BYTE `62`(자식 수 [I])를 줄이고 사라진다.

## 경계·routing 밖 출구

- [F] 이 단위 안에는 live 대상 호출(`JSR (An)`)·TRAP이 없다. 계산 점프 7개의 표 95칸은 모두 이 단위의 block 시작이다.
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 1개(`b057c`).
- [F] **native 정지 규칙**(V1): FR8 spec의 `first_unrouted`(`8c16 < pc <= 8ca6`, `16ed2 < pc <= 16eee` 내부, 정지 `2a00` `2a24`, 홀수 live 정지 PC 버림)를 그대로 쓴다. `JMP 2a00`는 routing된 출구다. 실제 ROM 차분의 선언 정지는 FR8과 같다(FR4 표 항목 `cc7ac + 4k`(`cc7b4` 제외) / `cc82e + 4k`). 계산 착지 분류(실제 ROM 차분)에 이 단위의 `JMP` 7곳(`af9c4` `afa48` `afacc` `afb4c` `afb66` `afb80` `afbb2`)을 더한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1..FR8 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0..A4 := 자연 node, LONG `c(A6)` := 자연 node, A5 field, 스택 WORD, PC).
- **IO pack 자연 node 상태(family `natural`)**: FR7/FR8과 같다. `boot-demo-0`의 frame 시작 상태에서 callback LONG이 이 단위의 진입(`af8cc` `af8f2` `af910` `af990` `afbbe` `afd7c` `afe40` `aff00` `aff30` `b001a`)인 node를 찾아(work RAM `100800..104c00` 짝수 주소) 그 RAM·PVC·bank를 쓰고 레지스터만 선언한다(A5 := `108000`, A6 := 그 node, A7 := `10ef00`(복귀 LONG = sentinel), PC := callback). 찾은 자연 node(scratch `natsearch.py`): `af8cc`(410 `1017c8`, 519 `101704`), `af8f2`(411..419 `1017c8`, 520..528 `101704`), `af910`(420 `1017c8`, 529 `101704`), `af990`(434 `1017c8`, 495 `101640`), `afd7c`(435..452 `1017c8`), `aff30`(496..509 `101640`). 쓰는 frame: 410 411 419 420 434 435 444 452 495 496 509 519 528 529. [I] 이 상태는 그 frame 첫 시점의 상태이고 dispatcher 진입 레지스터와 같은 frame 안의 앞선 node 변경은 반영하지 않는다(선언 레지스터). 같은 상태를 native와 C++가 받으므로 V1 비교는 유효하다.
- 사슬(chain) fixture(자연 사슬 world `NATURAL_CHAINS` 포함: 아래 기록): 소비자를 실제 생산자로 들어간다 — `49fc6` → `afd90`(`afd8a`)·`aff3c`(`aff36`)·`b0048`(`b0042`), `b0468` → `afe6a`(`afe66`), `2986` → `b0556`(`b0524`). hint: `49fc6`(LONG `26(A6)` = 0 → Set, 자연 anim이면 interpreter 끝의 C), `b0468`(WORD `3a` ≥ 0 → Clear; < 0이면 `4ae4a` 판정), `2986`(WORD `104ca0` 개수: 남으면 성공 Set, 0이면 실패 → caller-X 오류이므로 V1은 성공 쪽만 사슬로 둔다). 단위 시험은 RAM만 읽고 PVC port를 쓰지 않는 생산자만 실제 사슬로 넣는다(`49fc6`은 bank port를 쓰므로 버리고, `b0468`의 Set 쪽은 ROM 표 `b067e`를 읽으므로 버린다; `2986` 실패는 caller-X 오류라 버린다). 생성기가 두 C 값을 다 만든 사슬만 남기고 나머지는 선언 C 행만 둔다(V1·실제 ROM 차분이 실제 사슬).
- node fixture: callback·설치 값(`af8cc` `af8f2` `af910` `af990` `afbbe` `afd7c` `afe40` `aff00` `aff30` `b001a`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `b051a`를 subroutine으로(복귀 LONG = sentinel) 들어간다.
- 단위 시험(Unicorn 생성기, FR8 꼴): 시작 220개 × 들어오는 C 3가지, zero-step, 내부 PC 618개 정확한 오류, 경계 stop(출구 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), 계산 점프 7개의 표 색인 전부(표 항목 정지와 항목의 대상)와 표 밖 색인(`af9bc` `1b` → `afa34` 시작, `1c` → `afa38` 내부 오류; `afa40` `1b` → `afab8`; `afac4` `1b` → `afb3c` routing 밖 오류, `1c` → `afb40` 내부 오류), 그리고 빈틈 종류별 hint:
  - 부호·영 확장: `af9b0`/`afa34`/`afab8`의 MOVE.B + `ANDI.W #ff`(D0 bit 8..15 쓰레기, 상위 WORD 유지), `EXT.L`(`afd48` `afdde` `affa0`: D0 상위 쓰레기가 사라짐), `MOVEM.W`의 부호 확장(`b0556`: WORD `8000` `ffff` `7fff`), D1.B만 바꾸는 `MOVE.B D0,D1`(D1 상위 유지).
  - 음수 색인: 이 단위의 계산 점프는 항상 0 이상(`ANDI.W` 뒤 4배 ≤ `3fc`)이라 음수 색인이 없다. 64 KiB RAM 거울은 node A6 = `1fe000`(`10e000`), 부모 LONG `c(A6)`의 거울 주소로 확인한다.
  - 꺼낸 레지스터: `b0556` WORD 7개(D0..D6 전부 다른 값, 상위 bit 덮어씀).
  - bit 조합과 뒤따르는 mask: BYTE `15` bit 0·1·3·7(`afd2a`/`afd38` BSET/BCLR, `afdd2` BCHG, `afe20` BCLR #1, `afe30` BSET #3, `afec4`/`afece`, `aff6a`/`aff78`; 다른 bit 유지), BYTE `61` bit 1·7, BYTE `5f` bit 7(`TST.B`: `80` `7f` `ff` `0`), `ANDI.B #1f`/`#3f` 뒤 `ADDI.B`/`SUBI.B`(`aff78` 순환: 0 − `f` = `f1`), `ANDI.W #3ff`/`#7ff` 뒤 `ADDI.W`, `ANDI.W #7f` 뒤 `ADD.W`/`SUB.W 2c`(WORD 순환).
  - BMI 대 BLT·넘침: `af8d8` SUBQ.W + BMI(D0.W = 0 → `ffff` 참, `8000` → `7fff` 거짓(BLT이면 참), 1 → 0 거짓), `af8fe` SUBQ.W + BPL(WORD `96` = 0 → 거짓, `8000` → 참(넘침), 1 → 참).
  - 동점(같은 값): `af9b0`/`afa34`/`afab8` CMPI.B #1b(`1a`/`1b`/`ff`/`80`), `b001a` CMPI.B #b(`a`/`b`/`c`/`10b` 상위 쓰레기 없음: 메모리 BYTE), `b051a` CMPI.W #0(WORD `92` = 0 / `100` / `1` / `8000`).
  - TST.W 대 TST.L·TST.B: `afdc2` `afe74` `affc0`의 `TST.W D0`(D0 = `8000`·`80`·`80000000`·`10000`), `afe54`의 `TST.B 9b`(WORD 상위 BYTE만 0 아님은 무관: BYTE), `afd1c` `afebc` `aff5c`의 `TST.B 5f`(이웃 BYTE `5e`/`60`과 무관).
  - ASR 대 LSR: `afe54` `b0024` `b0032`의 `ASR.L`(LONG `36`/`3a` = `80000000` `ffffffc0` `ffffffff` `3f` `7fffffff`).
  - 상위 레지스터 bit: `MOVE.W #imm,D0`(`af910` `afbc8` `afbe2` `afcf2` `afd00` `afda6` `afe0a` `afe98` `afea6` `aff00` `aff0e` `affc6` `affe0` `b000a` `b0524`), `MOVEQ #0,D0`(`afe20`), `ANDI.W`(계산 점프 7개, `afbfe` `afd68` `afdfe` `afffc`), `SUBQ.W #1,D0`(`af8d8`), `MOVE.W D0,96(A6)`(`af8de`).
  - 정지 PC 확인: 실패한 block 바로 뒤를 run stop으로 두고 실패 PC를 확인한다(오류 fixture).

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `tools/probe_scan_fr7.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_fr9.out` 25줄)과 FR9 진입 PC 문자열 검색으로 확인한 결과:
  - **옮길 것: 없다.** 이 단위의 PC를 "routing 밖" 탐침이나 rollback 기대값으로 쓰는 시험·검증기는 없다. N09 시험의 rollback 탐침은 이미 `10fe00..10fefe`이고, N09 `RANGES`의 `af990`은 범위 끝값이다. 나머지 일치는 자료 값(`b0000` `b0010` `affff` 등 좌표·레지스터 값)과 문서 문자열이다.
  - 표준 Python 검증기(`tools/verify_*.py` 전부)는 이 단위의 PC를 탐침으로 쓰지 않는다(검색 0줄).
- [I] native 사슬이 이 단위의 PC(`af8cc` `af990` `afbbe` `aff24` 등)를 첫 routing 밖 PC로 멈추던 V1 spec(N09 계열 사슬)은 더 진행한다(정지는 routing에서 계산되므로 spec 수정은 필요 없을 것으로 본다; 검증 단계 회귀로 확인).
- [F] stage_event / stage_event_ops 검증기의 `CPP_PINS`(`animation_machine.cpp` `9592e227…`, `animation_machine_internal.h` `a7d92b01…`)는 이 단위의 공유 수정으로 맞지 않게 된다. 작업자가 새 값으로 바꾸고 옛 값을 주석(`# FR9 refresh: … was …`)으로 남긴다.

## 결정

1. **범위.** FR9 = `af990` 계열 220 block(6 범위), FR8 명세 그대로. FR9 뒤 D 남은 실행 PC 0이 목표다.
2. **계산 점프·표.** 7개 모두 PC := 표 + sext(4·(D0.W ∧ m)의 WORD)로 routing을 거친다. 표 95칸(모두 `BRA.W`)은 이 단위의 block 시작이고 그 대상도 이 단위 안이다(전사 완료). m = `ff`인 3개의 표 밖 착지는 routing이 판정한다(FR1 결정 3). TRAP 자리 없음.
3. **carry 보존 목록.** 소비자 5개. `b0578`(ORI)는 자기 C를 Set으로 정하고 `b057c RTS`에서 Unknown이 된다(호출자가 읽지 않음). C를 넘기는 `RTS` 없음.
4. **숨은 탐침 이전.** 없음(위 "영향받는" 절). stage_event / stage_event_ops `CPP_PINS`는 작업자가 새 값으로 바꾸고 옛 값을 주석으로 남긴다.
5. **C 뒤 root의 검증.** 선언 상태에 더해 IO pack(`boot-demo-0`)의 자연 node 상태(선언 레지스터)를 V1 family `natural`로 둔다. IO 비교의 확인은 C·E 연결 뒤(계획 메인 결정).
6. **F4 범위 문서.** R09(`af3fe..b05bc`)는 FR9 6 범위를 빼야 한다(`area-d-completion-plan.md`에 메모).
7. **2986 실패 경로.** `b0524`의 `2986` 실패는 기존 caller-X checked 오류로 끝난다(이 단위가 X를 만들지 않음). 단위 시험·V1의 `b0556` Clear 쪽은 선언 C 행이다.
8. **정적으로 불가능한 분기.** 없을 것으로 본다(생성기·V1이 빠진 후속을 보고하면 그때 근거와 함께 `STATIC_IMPOSSIBLE`에 적거나 미확인으로 남긴다).
9. **다음.** 영역 D 연결 완료. 그 뒤 C(플레이어 `4e68e`·`1d1f4`).

## 미확인

- [U] node field 의미(`15` `20` `2c` `36` `3a` `5e` `5f` `61` `62` `63` `92` `94` `96` `9b` `9d`), 부모 BYTE `62`의 뜻, anim 기록 `b0e94` `b10f0` `b12ac` `b0fe8` `b13ee` `b1076`, 자식 `b3dbc`.
- [U] native IO 관측에서 실행되지 않은 이 단위의 block(표 항목 대부분, `afbbe`..`afc16`, `afda6`..`afe98`, `aff52`..`b005a`)은 closure로 들어왔다(V1 선언 상태·실제 ROM 차분으로만 확인).
- [U] IO pack 자연 node 상태의 레지스터(선언)와 실제 dispatcher 진입 레지스터의 차이(결정 5의 [I]).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr9.cpp`(case label 220 = scratch `starts_fr9.txt`와 집합 일치; 공용 함수 `ofr9_bit`(BSET/BCLR/BCHG.B), `ofr9_btst`, `ofr9_carry`, `ofr9_add_word`, `ofr9_asr`(ASR.L, 부호 채움을 명시 연산으로), `ofr9_anim`(`MOVE.W #163,20(A6)`; A1; `JSR 49f8c`), `ofr9_sound`, `ofr9_kind`(`CMPI.B #1b` + `BCC`), `ofr9_table`(계산 점프), `ofr9_speed`(`ANDI.W`/`ADDI.W`/`EXT.L`/`LSL.L #8`), `ofr9_store_speed`, `ofr9_spread`, `ofr9_release`(부모 BYTE `62`), `ofr9_decay`(`ASR.L` + `SUB.L`), `ofr9_fall`(`ADDI.L`), `ofr9_side`(`TST.B 5f` + `BPL`)), `engine/tests/animation_machine_objects_fr9_test.cpp`(생성 구역 + 수작성 규칙: 계산 점프 7개의 모든 색인과 표 항목의 대상, `CMPI.B #1b` 경계를 지나는 색인, 표 밖 색인 `1b`/`1c`/`80`/`40`, `af8d8` BMI(`8000`), `af8fe` BPL, 설치 값, `afbfe` `afd68` `afdfe`의 WORD `2c`, D1 spread와 BYTE `15` bit, 속도 3가지, `ADDI.L`, `ASR.L #6`/`#2`, `TST.W D0`, `TST.B 9b`, 부모 BYTE `62`, `b001a`, `b051a`, `b0524` WORD 넣기, `b0556` `MOVEM.W` 부호 확장, `b055e`, `b0578` Set / `b057c` Unknown), `tools/generate_animation_machine_objects_fr9_test_table.py`(생성기; V1 spec의 `hint_worlds`를 절대 주소로 바꿔 씀; 두 번 실행해 시험 파일 바이트 단위 같음 SHA256 `29fa9a3976c0360a03ffa4d6bc9bbc3e7c00af81d1d1d94a38f877c60f629834`, 약 80초), `tools/unit_fixture_specs/fr9.py`(V1 spec; FR8 spec의 공용 부분(routing 해석, `first_unrouted`, `block_next`, carry oracle, chain/node/natural/callee family) 그대로, 단위 부분 교체; `block_instrs`는 단위 범위 끝에서도 멈춘다(`afbfe`/`af926`이 N09 시작으로 넘어감); `TABLE_JUMPS` 7개, 사슬 5개, 2986 실패는 FR4/B4 spec과 같은 `cue_failure` 분류(오류 행 + `298e`까지 일치 행), 자연 사슬 world `NATURAL_CHAINS`(아래), 오류 행(내부 618 + 홀수 1 + Unknown C 5 + 홀수 node/stack 5 + 계산 착지 3 + 실행 뒤 실패 4), family `natural`(boot-demo-0 14 frame)). 공유 수정은 "공통 규칙"의 다섯 곳, stage_event / stage_event_ops `CPP_PINS`(옛 값 주석), `area-d-completion-plan.md` 메모뿐이다.
- [F] `dleft.py`(이 worktree routing `7233eefc…`): 실행된 routing 밖 PC D **0** / E 220 / C 620, 예측 일치 165,714(변화 없음), 첫 정지 영역 C·E 15 / C 1.
- [F] `make -j3 all test`(작업자, scratch `make3.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 282개(FR8 281 + 1), Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR9 시험 줄: `animation machine objects fr9: 683 fixtures (547 single-block, 106 path, 0 producer chain, 10 declared C, 20 checked error (9 with a later failing PC), 11 kept C), 220 blocks, 4079 calls, 19910 checks`. 생성기 보고: 단일 행 없는 시작 0, 후속이 빠진 분기 block 0, 표 항목 95칸 모두 자기 점프 block 단일 행의 stop, 출구 21개 + sentinel + `afb3c` 모두 어떤 행의 stop. 실제 생산자 사슬은 단위 시험에 0개(`49fc6`은 bank port를 씀, `b0468` Set 쪽은 ROM `b067e`를 읽음(생성기 시도: Clear 3 / Set 0), `2986` 실패는 caller-X 오류) — 소비자 5개는 선언 C 행(양쪽)만 있고 실제 사슬은 V1·실제 ROM 차분이 맡는다.
- [F] UBSan(작업자, `-fsanitize=undefined -fno-sanitize-recover=undefined`): 빌드 경고 0, 실행 종료 0, runtime error 0.
- [F] V1 fr9(작업자 2회째, scratch `v1_try2`): fixture 1,415개(block 720, chain 10, node 14, natural 14, callee 4, error 636, failpc 7, negative 10) failed 0, 방문 시작 220/220, 빠진 후속 0, 도달 못한 분기 결과 0, carry oracle Unknown/Clear/Set = 741/21/6. 1회째는 `afe6a`의 Set 쪽(`afe6e`)이 빠졌다(선언 world에서 `b0468` → `4ae4a`가 후보를 찾지 못함). **자연 사슬 world**: IO pack `boot-demo-0` frame 517(node `1017c8`, WORD `3a` := `8000`, PC := `afe66`)에서 `4ae4a`가 자연 격자의 후보를 찾아 C Set(`afe6e`), frame 434는 Clear(`afe84`)(scratch `exp/hit468n.py`: frame 400..577 × node 3 × `3a` 3 = 1,602 world 중 288이 Set).
- [F] 변이(scratch `mut/run_mut.py`, `mut/mutants.py`): 1회째 254개 중 247 kill. 살아남은 7개 중 4개는 동치(BYTE 쓰기 mask `1ff`, 부호 bit 자신을 다시 채우는 ASR, `EXT.L`이 상위를 덮는 속도 `ANDI.W` LONG화와 항상 양수인 속도 WORD의 0 확장)라 목록에서 빼고 비동치 변이 2개(`put-mask-word`, `asr-fill-one`)로 바꿨다. 나머지 3개(`af9bc-mask` `afac4-mask`: 직접 진입 D0.B ≥ `80`/`40`의 표 밖 착지, `afe54-word`: `TST.B 9b` 대 `9a`)는 시험 규칙을 더해 kill(`af9bc` `80` → `afbc8`, `afac4` `40` → `afbd0`, BYTE `9a` = `ff`에서 홀수 A7로 `JSR b0468`이 없음을 확인). 현재 목록 252개(`--check`: `patterns ok 252`); 바꾼 5개 재실행 `killed 5 of 5`. 전체 재실행은 결정적 runner가 한다.
- [F] 실제 ROM 차분 준비(scratch `realrom/`): `build.sh` `run_all.sh`(5 × 1,500: s1 s2 s3, f4 f5 `FOLLOW_ANIM=1`; 로그 `run_s1..run_f5.log`에 `mismatches N`·`covered starts X of Y`), `real_fr9.py`(FR8 harness에 FR9 world·소비자·진입; 선언 정지 FR8과 같음; 계산 착지 분류에 FR9 `JMP` 7곳을 더하고, 40-PC trace 창을 벗어난 착지도 잡도록 case마다 "FR9 `JMP` 직후 FR9 시작이 아닌 PC"를 기록해 분류). 시험 실행(작업자): 200건 seed 1 `mismatches 0`(계산 착지 3건 분류, caller-X 34건 분류, 실제 생산자 뒤 소비자 도달 `afd90` 14 `afe6a` 19 `aff3c` 9 `b0048` 9 `b0556` 34), 200건 seed 4 `FOLLOW_ANIM=1` `mismatches 0`(`covered starts 195 of 220`). 산출물(`in_*.bin` `out_*.txt`)은 지웠다.
- [F] stage_event / stage_event_ops `CPP_PINS` 새 값(작업자가 갱신, 옛 값은 `# FR9 refresh:` 주석): `animation_machine.cpp` `7233eefce1281ff3fdda6f44f97948290b350786f895b2734fa6b2a18d7a534d`, `animation_machine_internal.h` `b870dcc5f415fc18b92fa0b2e7c97b469c2302ee3d5d2bf61d773643b44ed25e`.
- [F] 숨은 탐침 이전: 없음(위 "영향받는" 절, scratch `probe_fr9.out`). 다른 실행부 block의 중간으로 들어가는 FR9 분기·점프 0(출구 21개 모두 그 PC를 routing하는 실행부의 `case` label), 범위 밖에서 FR9 block 중간으로 들어오는 분기 0(`inrefs9.out`).

## block 목록

[F] scratch `starts_fr9.txt`(SHA256 `f2ba650fc7e314c55521b70677110119844e5feac9715bab04e634879b070dff`)와 같다.

- **`af8cc..af92c`(10)**: `af8cc af8d8 af8de af8f2 af8f8 af8fe af906 af90c af910 af926`
- **`af990..afb3c`(91)**: `af990 af996 af99c af9a6 af9b0 af9bc` + 표 `af9c8..afa30`(27) + `afa34 afa40` + 표 `afa4c..afab4`(27) + `afab8 afac4` + 표 `afad0..afb38`(27)
- **`afb3e..afc16`(28)**: `afb3e afb44 afb50 afb54 afb58 afb5e afb6a afb6e afb72 afb78 afb84 afb88 afb8c afb90 afb94 afb98 afb9c afba0 afba4 afbaa afbb6 afbba afbbe afbc8 afbde afbe2 afbf8 afbfe`
- **`afcf2..afed8`(47)**: `afcf2 afcfc afd00 afd16 afd1c afd2a afd38 afd42 afd48 afd5a afd68 afd76 afd7c afd8a afd90 afd94 afda2 afda6 afdbc afdc2 afdd2 afdd8 afdde afdf0 afdfe afe0a afe20 afe30 afe40 afe4e afe54 afe66 afe6a afe6e afe74 afe7a afe80 afe84 afe8e afe94 afe98 afea2 afea6 afebc afec4 afece afed4`
- **`aff00..b005e`(38)**: `aff00 aff0a aff0e aff24 aff2a aff30 aff36 aff3c aff40 aff4e aff52 aff56 aff5c aff6a aff78 aff82 aff86 aff8a aff90 aff9a affa0 affb2 affc0 affc6 affdc affe0 afff6 afffc b000a b0014 b001a b0024 b0032 b003c b0042 b0048 b004c b005a`
- **`b051a..b057e`(6)**: `b051a b0524 b0556 b055e b0578 b057c`
