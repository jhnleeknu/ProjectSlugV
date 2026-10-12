# 객체 callback F4 N16: `7839a` 계열 객체(옛 R13/R14 일부) — stage event callback `7839a`, 초기화 `77556`, 설치 callback `77596` `77d38` `77d70` `78de6`, 공용 꼬리 `78c22`, helper `79054`~`796cc` 계약 초안(N16a: N17 seed가 쓰는 부분)

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N16 행(217 block, `77556..7768e` `77d38..77d8e` `7839a..78660` `789ac..789d6` `78c22..78dec` `79054..7930a` `79566..796e6`, callback `77596` `77d38` `77d70` `7839a` `78de6`, 경계 `494c0` `4954e` `787d2` `79222`~`79722`(11) `cc778`, bank 1, 미실행 설치 20(+298), 새 seed 없음, 옛 R13 171·R14 52)과 메인 결정 1·2(이름 `objects-n16`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 단위 형식과 규약은 N14 계약(SHA256 `77bb85f8a3c1b1ddb60daec7f0bc5af62a2cede53ce78e4d7018c95f01423c04`)을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 각 선행에 접어 넣음).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 진입은 넣는다.
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. DIV 0 제수는 단위 checked 오류(N16에는 DIV가 없다).
- 범위 안 설치 뒤 220 block을 넘으면 나누고, N17 seed(76 77 98 99 104 105)가 쓰는 부분을 먼저 구현한다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback과 `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다. 묶인 연속 Bcc는 없다. Unicorn TB 분할은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다(이번에는 아래 결정 1의 분할이 예외). 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다. 범위 안 자료는 없다.
- U01~N14 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`EOR`/`ADDQ`/`SUBQ`/`ANDI` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`JMP`/`BRA`/`RTS`/Bcc)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`/`BCHG`만인 block, callee C를 소비하는 Bcc block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N16 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`2000d4`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n16`(HEAD `3e4b0b3` = N14 + interpreter `49f96`까지 통합, `engine/src/animation_machine.cpp` SHA256 `743f3798894bed30d1763e8e2907963d20e8d06653fb03e291d24426269c72ec`, routing 규칙 71개, `engine/src/animation_machine_interpreter.cpp` SHA256 `bd2bffb36ccf99cc18fe141949335e6ef1e07f7255cb1f137e387d0451ebac05`)을 참조했다. N16 routing 범위의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N15(`493bc..493fc` `7028e..702cc` `7054c..70606` `708a6..708ba` `71032..7120e` `71a80..71e8c`(N04 부분 제외) `72d66..72dd2` `76d18..76ff2`)와 범위가 겹치지 않는다. N16은 N15의 `493bc`를 부른다(경계, 아래). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n16/n16.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **재범위 N16 행 7 범위의 정적 도달 전체는 270 block**(진입 `77596` `77d38` `77d70` `7839a` `78de6`, 범위 안 설치 callback 17개 포함, 아래 결정 2의 `7957a` 포함)이다. 220을 넘으므로 메인 지시대로 나눈다(결정 1).
  - **N16(이 계약, "N16a") = 163 block**, 코드 16 범위 1,236바이트, 277명령이다. routing 짝수 PC 618개 중 내부 PC 455개다.
  - **N16b(뒤 단위) = 107 block**: `7839a`/`783c0` 상태 분기의 `783ea`(`88 ≠ 0`)·`785f2`(`9b` bit 2) 상태 사슬(범위 안 설치 `7840c` `78444` `78462` `78496` `784bc` `784fa` `7855a` `785b4` `785f2` `78628`), 꼬리 `78cc4`(설치 `78d0a` `78d3a`), helper `7919a` `79222` `7962a`. 목록은 "N16b" 절.
  - 재범위 행 217과 차이: 재범위는 실행 TB 함수 본문만 셌고, 이 계약은 범위 안 정적 도달 전부와 범위 안 설치 callback을 센다.
- [F] 범위 안 미도달·미참조 코드는 routing하지 않는다(결정 3): `783ae..783c0`, `78c58..78c5c`, `78cc0..78cc4`, `78d5a..78de6`, `789ac..789d6`, `790a6..790be`, `790fc..79114`, `79130..7919a`, `795b8..7960a`, `79654..7967e`, `79698..796cc`. 이 가운데 `790a6` `790fc` `79130` `795b8` `79698` `789ac`는 범위 밖 미연결 코드(JSR·설치 LONG)가 부르는 별도 함수이고, 나머지는 참조가 없다.
- [F] 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/MULx/DIVx·I/O port 쓰기·bank 변경·스택 직접 조작은 없다(`79164 MULS.W`는 N16b 쪽 미도달 `79130..7919a` 안이다).
- [F] 진입:
  - stage event callback `7839a`(고정 ROM LONG 표 `e8da4`; 같은 표의 이웃 `e8d9c` `773ee`, `e8da0` `78386`은 범위 밖 다른 진입). 범위 밖 `5417e JMP 7839a.l`도 같은 진입으로 온다.
  - 범위 안 설치 callback(결정 2 관례): `77596`(`77590`, fall-through), `77d38`(`77684`), `77d70`(`77d6a`, fall-through), `78de6`(`78c6e`).
  - 범위 안 분기 대상이자 범위 밖 참조가 있는 진입: `77556`(`783d2 BNE.W`, 범위 밖 `774cc BEQ.W`, `77908 BCS.W`, 설치 LONG 10곳 이상), `783c0`(범위 밖 `78382` `78396 BRA.W`), `78c22`(`7768a` `77d8a BRA.W`, 범위 밖 `BRA.W` 12곳 이상).
  - helper(JSR 대상): `79054`(`783c6`, 범위 밖 `774a2` `774ea` `78a20`), `79064`(`79054 BGT`, 범위 밖 `7747e JSR`), `79114`(`7839a`, 범위 밖 `78372` `78386`), `791ea` `791fa` `79292` `792b8` `79566` `796cc`(범위 밖 미연결 호출 다수), `79256` `7960a` `7967e`, 그리고 **두 번째 진입 `7957a`**(범위 밖 `77b0e JSR 7957a(pc)`, 결정 2).
- [F] **경계 callee(실행부 없음)**: `493bc`(N15 범위, 동시 진행; `775b2` `7967e`), `494c0`(`79584` `79592` `79614`), `4954e`(`795a0`), `79400`(`79256`), `79454`(`775f2`), `79478`(`79268` `792d8`), `7949c`(`7761c`), `794e2`(`7762a`), `79722`(`792ee`), `7942e`(`792f6`), `787d2`(`783e6 BRA.W`), `cc778`(`78c9a JMP`), 그리고 N16b 시작 `783ea`(`783ca BNE.W`) `785f2`(`783dc BNE.W`). 모두 `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **범위 밖 설치 값(고아 설치, 노드 LONG에 저장만)**: `776da` `7777a` `7783e` `778fa` `77a70` `77af4` `77c68` `77de8`(`77596` 계열), `77d8e`(`77d84`). `28ae` 자식 대상 `78e0e`(`78c76`)는 자식 노드 LONG에 저장되는 자료다(범위 밖, 미연결).
- [F] **carry**(아래 "carry" 절):
  - 소비 block **25개**: BCC/BCS 23개와 `EORI.B #1,CCR` 2개(`792ac` `7961e`, 결정 4).
  - known 생산 block **11개**: Set `79212` `792fe` `795ac` `78c96`, Clear `7921c` `792b2` `79304` `795b2` `79624`, 반전 `792ac` `7961e`.
  - FLOW_ONLY 93개(BCC/BCS 소비 23 포함), Unknown 59개. 93 + 11 + 59 = 163.
- [F] 스택: JSR 복귀 LONG만 쓴다(`JSR (PC)` 22곳 포함).
- [F] 자료(모두 live bus): banked LONG `2000d4`(`77562` `77d38` → 노드 `22(A6)`; `78c9a` → A1). 그 LONG이 가리키는 기록의 LONG `c0`(`77562`) `20`(`77d38`)을 A1(애니메이션 목록)로 읽는다. 고정 ROM 자료는 주소만 넘긴다(`798ca` `798aa` `798b2` `798c2` `cb3e4` `cdef8` `78e0e`). work RAM은 "자료" 절.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n16reach.py` `n16seen.py`): RNG 400 frame 기록에서 seed 76 77 98 99 104 105만 N16 PC를 실행한다(TB 시작 72개, 모두 이 계약의 163 시작 안). 각 seed에서 callback `7839a` 1회, `77596` 5회, `77d38` 1회, `77d70` 13회, `78de6` 1회다. base 120 frame 기록에서는 0이다. 자연 경로는 `7839a`→`79114`→`783c0`→`783d2`(`9b` bit 5)→`77556`→`77596`→…→`791fa` Set→`77d38`→`77d70`→`78c22` 꼬리→`1ab02` Set→`78de6`이고, 경계 중 `493bc`(N15)만 실행한다(`7967e`). 자연 미도달 시작 91개는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] **새 완주 seed 없음(재범위 행과 같음).** 이 작업 트리 base `3e4b0b3`에서 seed 76 77 98 99 104 105는 frame 0 N15 callback `708a6`에서 먼저 멈춘다(RNG 기록 `checked-current-first-unrouted-PC`). N16은 N15·N17과 함께일 때 이 seed를 푼다(재범위 N17 행 "N03 N04 N05 N08 N14~N17").

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **분할: N16 = 163 block("N16a"), N16b = 107 block.** [F] 재범위 7 범위의 정적 도달 전체(범위 안 설치 포함)는 270 block이라 220을 넘는다. N17 seed 6개의 자연 경로(위 요약)는 `7839a`의 `783ca`(`88 = 0`)→`783d2`(`9b` bit 5 set)→`77556` 갈래만 쓴다. 그래서 `7839a`/`783c0` 상태 분기의 나머지 두 갈래 `783ea`(`TST.W 88(A6); BNE.W`)와 `785f2`(`783dc BTST.B #2,9b(A6); BNE.W`)를 경계로 두고, 그 갈래만 쓰는 상태 사슬·꼬리 `78cc4`·helper `7919a` `79222` `7962a`를 N16b로 미룬다. `783dc`/`783e6`(분기 block 자체)은 N16에 넣는다(`787d2`는 원래 경계). 자를 곳을 함수 경계가 아니라 분기 대상으로 정한 이유: `7839a` 함수 본문(`783c0..78660`)이 혼자 107+ block이고, 그 진입이 N17 seed의 자연 진입이다. [I] 다른 분할(예: `77556`/`77596` 함수를 N16b로)은 N17 seed가 쓰는 시작을 빼게 된다. N16b는 `783ea` `785f2` 두 PC를 시작으로 routing만 더하면 되고 N16 실행부 block을 다시 나누지 않는다(`783ca`/`783dc`의 분기 대상이 이미 block 시작이다).
2. **두 번째 진입 `7957a` 포함(+1 block).** [F] 범위 밖 미연결 코드 `77b0e JSR 7957a(pc)`(고아 설치 `77af4` 사슬)가 `79566` helper의 `MOVE.B #1e,96(A6)` 뒤 `JSR 4945e.l`로 바로 들어온다. 고정 ROM 전수 참조 검사(scratch `n16xref.py`)에서 N16 block 안을 가리키는 참조는 이것뿐이다(그 밖 `790ea` = 자료 `ea55c` `0004 0007 90ea` 반복의 우연 일치, `78c60` = 미도달 `78c58 BRA.W`의 대상). 나중 단위가 N16 block 안으로 다시 routing할 수 없으므로(관례) 지금 시작으로 나눈다. `79574`(`MOVE.B #1e,96(A6)`, Unknown) → `7957a`(`JSR 4945e.l`, FLOW)다. 빼면 162 block이고 `7957a`는 내부 PC다.
3. **routing 구멍.** [F] 범위 안 미도달 코드(요약 목록)는 routing하지 않는다(`unsupported animation machine PC`). N03(`c644a` 미참조)·N11·N12·N13 선례와 같다. routing 범위는 도달 명령의 연속 구간 16개다("원본 바이트 근거" 표). `78c58 BRA.W 78c60`(`78c54 BRA.W` 뒤 도달 불가 명령)과 `78cc0`/`78cc2 RTS`도 구멍이다.
4. **`EORI.B #1,CCR; RTS` 2 block(`792ac` `7961e`)은 소비자이자 반전 생산자.** [F] `792ac`는 `4945e`(N08: `494a6`/`494ac` Clear, `494b4` Set)의 C를, `7961e`는 `494c0`(경계)의 C를 뒤집어 반환한다. 들어오는 C가 known이면 반대 값을 known으로 두고, Unknown이면 `objects n16 caller requires known carry`(상태 보존)다. 두 PC는 carry 보존 목록에 넣는다(들어오는 C를 받아야 하므로). [I] Unknown을 그대로 넘기는 대안은 오류 위치만 뒤 소비자(`792bc`, `77604`)로 옮긴다.
5. **known C 생산 11 block과 확인 방법.** [F] RTS 앞 `ORI.B #1,CCR` / `ANDI.B #fe,CCR`(Set 4: `79212` `792fe` `795ac` `78c96`; Clear 5: `7921c` `792b2` `79304` `795b2` `79624`)은 원본에서 항상 그 C를 만든다. 실제 ROM 소비자(복귀 주소)는 모두 N16 안이다: `791fa` → `77680` `77d80`; `79292` → `792bc`; `792b8` → `77672`; `79566` → `77612` `77652` `77664`; `7960a` → `77604`. typed fixture와 실제 ROM 차분이 helper를 따라 그 소비자의 native 분기로 C를 확인한다(Unicorn SR은 쓰지 않는다). `78c96`(`28ae` Set 뒤 `4970a` 다음)은 바로 뒤 `78c9a MOVE.B`가 C를 덮어 소비자가 없지만 같은 명령이라 Set으로 둔다(N14 결정 2 선례).
6. **`79256`의 반환 C는 Unknown.** [F] `79282 CLR.W D0; RTS`, `79286 MOVE.W #1,D0; RTS`, `7928c MOVE.W #2,D0; RTS`는 원본에서 C = 0이지만, 유일한 N16 호출자 `775ce` 뒤 `775d2 CMPI.W #1,D0`이 C를 덮는다. 범위 밖 호출자는 없다(고정 ROM `JSR 79256(pc)` 1곳). 소비자가 없으므로 관례대로 Unknown이다. `791e8`/`791f8`/`79696`/`790a4`/`795aa`/`796d6`/`796de RTS`는 FLOW(C 보존)다.
7. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n16.cpp`의 `animation_objects_n16_block`. 오류는 `unsupported animation objects n16 PC`(내부 PC), `objects n16 caller requires known carry`(소비 25 block). 메인 지시와 같다.
8. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`에서 N16 270 block 범위(N16b 포함)의 PC를 쓰는 곳은 없다(`u11` test의 `0x78641`은 레지스터 값). 새 경계 PC를 기대하는 기존 test도 없다.
9. **interpreter·다른 실행부의 두 번째 진입 누락 없음.** [F] N16이 부르는 다른 단위 진입(`49f8c` `49fc6` `4be06` `4be2c` `4c0ac` `496c2` `4d7a6` `49a58` `4945e` `4950e` `4970a` `4b54e` `1ab02` `28ae` `2a00` `490ba` `c6a96` `ea5f0`)은 모두 기존 실행부의 case로 시작한다(scratch routing 검사, interpreter `49f8c`/`49fc6` case 확인). 패치 파일은 없다.

## 원본 바이트 근거

[F] 코드 16 범위 합계 1,236바이트. 범위 순서로 이어 붙인 SHA256 `d5f4038dfd581eea06d8b5c77eab469d689b67c5534b875ca8eea13703cc8296`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `77556..7768e` | 312 | `1e6d65cdf399901e761a5337638254a9835ff5869c17939577720397bb7eb0a8` | 49 |
| `77d38..77d8e` | 86 | `96164625f6e68e4c2e25296c67c39deb595dafb1755acac1933159188ffc14e2` | 8 |
| `7839a..783ae` | 20 | `7f2296d6bfa5454e36095c133d59c4224b1db59b5ea9b00ac0c3830b9160129e` | 2 |
| `783c0..783ea` | 42 | `c7e90739b659f0531d9da6a6093b28b6c1e4bd7709b810a1ec6b5fa2ea40cfe0` | 6 |
| `78c22..78c58` | 54 | `498362677ae01d854b2b08c0339b1b7bc0c0ed1e7e3263d06e2b7dada79f262e` | 8 |
| `78c5c..78cc0` | 100 | `374676fbcd9f08e223d44fe9640afaa281bb69b6ad4c576f34f23aa7799c0edc` | 9 |
| `78de6..78dec` | 6 | `2738adf81304c5fbbc9eedf6248d6b2d7cfa132bc35dfb5e458d0bbd9e12d3f9` | 1 |
| `79054..790a6` | 82 | `21321e098062805a8be0df29b108bc22068b27091fe08c00726f19679ab91fef` | 7 |
| `790be..790fc` | 62 | `7c32500ca339ac3d1c2f828d8b3060a0957b634a12c30c7b76a711fd201bb4de` | 4 |
| `79114..79130` | 28 | `8ce11482bbb1b4597e9136bc646ee8937079d24630b7a58dc33acf220909bc48` | 2 |
| `791c0..79222` | 98 | `6a16bc60cef3ec8c5adec53d1facaaa2a42cc80ed7072c1da6d17607012e31c0` | 14 |
| `79256..7930a` | 180 | `0dcdcfd640999c4e0ca453b9a832a361211564095cec39b2a3654fb9eee34b43` | 29 |
| `79566..795b8` | 82 | `2da374120ecc5bcc8d1ce09b60d6af8b522e3ed8300244cdb9d61444d9e0cdb4` | 12 |
| `7960a..7962a` | 32 | `7fd9226a2e92703e15c330a5ca7e67e293a64d7c7a2f584aee5cd6500031495d` | 4 |
| `7967e..79698` | 26 | `5471e4e5ef6167346b04af05c5bb734b18d5a7230d8d04edc348ab303b1e0faa` | 5 |
| `796cc..796e6` | 26 | `b2382253d781d1a73a1c322f81ce740ece093c7dd2fb6b10183ba9fa85ba2659` | 3 |

- [F] 범위 밖 이웃(모두 미연결, `unsupported animation machine PC`): `77554`(앞 함수 끝), `7768e..`(고아 설치 `776da` 사슬), `77d36`, `77d8e..`(고아 설치 `77d8e`/`77de8` 사슬), `78398`(다른 함수 `78372`/`78386` 끝), 구멍 `783ae..783c0`(미참조 진입 `783ae` `783bc`), `783ea..78660`(N16b), `78660..78c22`(고아 설치 `78660` `78716` 등과 경계 `787d2`), 구멍 `78c58..78c5c`, `78cc0..78de6`(미도달 `RTS` 2개, N16b 꼬리 `78cc4..78d5a`, 미참조 `78d5e..78de6`), `78dec..`(`28ae` 자식 `78e0e` 자료·코드), `79052`, 구멍 `790a6..790be`(범위 밖 `JSR 790a6` 7곳의 helper), `790fc..79114`(미참조 `783ae`/`783bc`만 부르는 helper), `79130..791c0`(범위 밖 `78a16 JSR 79130`의 helper, `79164 MULS.W` 포함; `7919a..791c0`은 N16b), `79222..79256`(N16b `79222`), `7930a..79566`(경계 `7930a` `79400` `7942e` `79454` `79478` `7949c` `794e2`), `795b8..7960a`(범위 밖 `777d8 JSR 795b8`의 helper), `7962a..7967e`(N16b `7962a`, 미참조 `79654`), `79698..796cc`(범위 밖 `JSR 79698` 9곳의 helper), `796e6..`(경계 `796e6` `7970e` `79722`, 자료 `798aa..798da`).
- [F] 범위 밖 → N16 참조(scratch `n16xref.py`, 고정 ROM 전수: LONG 값, Bcc/BRA/BSR 변위, `JSR`/`JMP`/`LEA (PC)`): `77556`(`774cc BEQ.W`, `77908 BCS.W`, 설치 LONG 10곳 이상), `77d38`(설치 LONG 11곳 이상), `7839a`(`e8da4` 표, `5417e JMP.L`), `783c0`(`78382` `78396 BRA.W`), `78c22`(`BRA.W` 12곳 이상), `79054`(`774a2` `774ea` `78a20`), `79064`(`7747e`), `79114`(`78372` `78386`), `7957a`(`77b0e`, 결정 2), `791ea`(`JSR (PC)` 12곳 이상), `791fa`(12곳 이상), `79292`(`78b30` `79314` `7932a` `793c6`), `792b8`(`77970`), `79566`(`7773e` `777f4` `778b0` `7797e`), `796cc`(7곳), `7967e`(`78cc4` `78d5e`). 모두 block 시작으로 간다. 내부 PC와 같은 값은 자료 우연 일치(`790ea`)와 미도달 명령의 대상(`78c60`)뿐이다.
- [F] 범위 안 고정 ROM 자료는 없다. `LEA x(PC),A0`가 넘기는 사각형 `798ca`(`ffe0 fff8 0040 0020`, `1ab02`), `798aa`(`fe00 fff0 0200 0040`) `798b2`(`0000 fff0 0080 0040`) `798c2`(`ffec fff0 0028 0040`)(`494c0`, 경계)는 범위 밖이다.

## block 목록과 실행 의미

[F] 163 block. 각 줄은 block 안 명령 전체다(capstone 표기, 즉치·주소 16진). "(→x)"는 fall-through다. 태그: "C 소비"(Unknown이면 checked 오류), "Set/Clear 생산", "C 소비·반전 생산"(`EORI.B #1,CCR`), "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVE.W #x,D0`·`CLR.W D0`·`EOR.W D0,D0`·`ANDI.W #1,D0`은 하위 WORD만, `MOVE.B #0,D2`는 하위 BYTE만). `ASR.L #1`은 부호 bit 채움 산술 shift다. `ADDQ.B`/`SUBQ.B`/`SUBQ.W`는 원래 폭의 2의 보수다. 비교 분기: `BGT`/`BLT`(부호 있는 비교; `CMPI.W #a0,42(A6); BGT`는 signed `42.W > a0`, `CMPI.B #6,97(A6); BLT`는 증가 뒤 signed `97.B < 6`), `BPL`/`BMI`(결과·피연산자 최상위 bit; `SUBQ.W #1,84(A6); BPL`은 감소 결과, `TST.W 3a(A6); BMI`는 WORD bit 15), `BEQ`/`BNE`(0 여부; `ANDI.W #1,D0; BEQ`는 결과 0), `BCC`(C = 0), `BCS`(C = 1). `BCHG`/`BSET`/`BCLR`는 대상 BYTE bit만 바꾸고 Z만 쓴다. `MOVE.L 2000d4.l,22(A6)`은 bank window LONG을 live bus로 읽는다.

**초기화 `77556`(설치 `77596`) 3**
- `77556`: `CLR.L 36(a6); CLR.L 3a(a6); JSR 796cc(pc)`
- `77562`: `BCHG.B #0, 9b(a6); LEA.L 26(a6), a0; MOVE.W #b, 20(a6); MOVE.L 2000d4.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L c0(a1), a1; JSR 49f8c.l`
- `77590`: `MOVE.L #77596, (a6)` (→`77596`)

**callback `77596`(기본 상태; 범위 밖 설치 8개) 46**
- `77596`: `JSR 791ea(pc)` — FLOW
- `7759a`: `JSR 49fc6.l` — FLOW
- `775a0`: `BTST.B #4, 9b(a6); BEQ.W 77660` (→`775aa`) — FLOW
- `775aa`: `TST.B 99(a6); BNE.W 7764a` (→`775b2`)
- `775b2`: `MOVEA.L 76(a6), a0; JSR 493bc.l` — FLOW
- `775bc`: `BCC.W 7763c` (→`775c0`) — C 소비
- `775c0`: `JSR 4d7a6.l` — FLOW
- `775c6`: `CMPI.B #4, d0; BEQ.W 775f2` (→`775ce`)
- `775ce`: `JSR 79256(pc)` — FLOW
- `775d2`: `CMPI.W #1, d0; BNE.W 775e4` (→`775da`)
- `775da`: `MOVE.L #7777a, (a6); BRA.W 775f2`
- `775e4`: `CMPI.W #2, d0; BNE.W 775f2` (→`775ec`)
- `775ec`: `MOVE.L #7783e, (a6)` (→`775f2`)
- `775f2`: `JSR 79454(pc)` — FLOW
- `775f6`: `BCC.W 77600` (→`775fa`) — C 소비
- `775fa`: `MOVE.L #776da, (a6)` (→`77600`)
- `77600`: `JSR 7960a(pc)` — FLOW
- `77604`: `BCC.W 7760e` (→`77608`) — C 소비
- `77608`: `MOVE.L #77a70, (a6)` (→`7760e`)
- `7760e`: `JSR 79566(pc)` — FLOW
- `77612`: `BCC.W 7761c` (→`77616`) — C 소비
- `77616`: `MOVE.L #77c68, (a6)` (→`7761c`)
- `7761c`: `JSR 7949c(pc)` — FLOW
- `77620`: `BCC.W 7762a` (→`77624`) — C 소비
- `77624`: `MOVE.L #778fa, (a6)` (→`7762a`)
- `7762a`: `JSR 794e2(pc)` — FLOW
- `7762e`: `BCC.W 77638` (→`77632`) — C 소비
- `77632`: `MOVE.L #77af4, (a6)` (→`77638`)
- `77638`: `BRA.W 77646` — FLOW
- `7763c`: `JSR 4950e.l` — FLOW
- `77642`: `MOVE.L a0, 76(a6)` (→`77646`)
- `77646`: `BRA.W 7765c` — FLOW
- `7764a`: `SUBQ.B #1, 99(a6); JSR 79566(pc)`
- `77652`: `BCC.W 7765c` (→`77656`) — C 소비
- `77656`: `MOVE.L #77c68, (a6)` (→`7765c`)
- `7765c`: `BRA.W 7766e` — FLOW
- `77660`: `JSR 79566(pc)` — FLOW
- `77664`: `BCC.W 7766e` (→`77668`) — C 소비
- `77668`: `MOVE.L #77c68, (a6)` (→`7766e`)
- `7766e`: `JSR 792b8(pc)` — FLOW
- `77672`: `BCC.W 7767c` (→`77676`) — C 소비
- `77676`: `MOVE.L #77de8, (a6)` (→`7767c`)
- `7767c`: `JSR 791fa(pc)` — FLOW
- `77680`: `BCC.W 7768a` (→`77684`) — C 소비
- `77684`: `MOVE.L #77d38, (a6)` (→`7768a`)
- `7768a`: `BRA.W 78c22` — FLOW

**callback `77d38`(설치 `77d70`) 2**
- `77d38`: `MOVE.L 36(a6), d0; ASR.L #1, d0; MOVE.L d0, 36(a6); LEA.L 26(a6), a0; MOVE.W #b, 20(a6); MOVE.L 2000d4.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 20(a1), a1; JSR 49f8c.l`
- `77d6a`: `MOVE.L #77d70, (a6)` (→`77d70`)

**callback `77d70` 6**
- `77d70`: `JSR 4be2c.l` — FLOW
- `77d76`: `JSR 49fc6.l` — FLOW
- `77d7c`: `JSR 791fa(pc)` — FLOW
- `77d80`: `BCS.W 77d8a` (→`77d84`) — C 소비
- `77d84`: `MOVE.L #77d8e, (a6)` (→`77d8a`)
- `77d8a`: `BRA.W 78c22` — FLOW

**stage event callback `7839a`와 상태 분기 `783c0` 8**
- `7839a`: `JSR 79114(pc)` — FLOW
- `7839e`: `MOVE.B #f0, 94(a6); MOVE.B #8, 93(a6); BRA.W 783c0`
- `783c0`: `JSR 4c0ac.l` — FLOW
- `783c6`: `JSR 79054(pc)` — FLOW
- `783ca`: `TST.W 88(a6); BNE.W 783ea` (→`783d2`)
- `783d2`: `BTST.B #5, 9b(a6); BNE.W 77556` (→`783dc`) — FLOW
- `783dc`: `BTST.B #2, 9b(a6); BNE.W 785f2` (→`783e6`) — FLOW
- `783e6`: `BRA.W 787d2` — FLOW

**공용 꼬리 `78c22`(`1ab02` 화면 밖 판정, 파괴 `78c76`) 17**
- `78c22`: `JSR 7967e(pc)` — FLOW
- `78c26`: `SUBQ.W #1, 84(a6); BPL.W 78c34` (→`78c2e`)
- `78c2e`: `MOVE.W #0, 84(a6)` (→`78c34`)
- `78c34`: `BTST.B #0, 61(a6); BEQ.W 78c44` (→`78c3e`) — FLOW
- `78c3e`: `MOVE.B #1e, 99(a6)` (→`78c44`)
- `78c44`: `JSR 4b54e.l` — FLOW
- `78c4a`: `BTST.B #7, 61(a6); BEQ.W 78c5c` (→`78c54`) — FLOW
- `78c54`: `BRA.W 78c76` — FLOW
- `78c5c`: `CLR.B 5e(a6); LEA.L 798ca(pc), a0; JSR 1ab02.l`
- `78c6a`: `BCC.W 78c74` (→`78c6e`) — C 소비
- `78c6e`: `MOVE.L #78de6, (a6)` (→`78c74`)
- `78c74`: `RTS` — FLOW
- `78c76`: `MOVEA.L #78e0e, a0; MOVE.W #14, d0; JSR 28ae.l`
- `78c86`: `BCC.W 78c9a` (→`78c8a`) — C 소비
- `78c8a`: `CLR.W d0; MOVE.W #18, d1; JSR 4970a.l`
- `78c96`: `ORI.B #1, ccr` (→`78c9a`) — Set 생산
- `78c9a`: `MOVE.B 5f(a6), 5f(a0); MOVE.B #ff, 17(a6); LEA.L cdef8.l, a0; MOVEA.L 2000d4.l, a1; MOVE.W #b, d1; MOVE.W #1, d2; JMP cc778.l`

**삭제 callback `78de6` 1**
- `78de6`: `JMP 2a00.l` — FLOW

**helper `79054`(초기 외형·소리·표) 7**
- `79054`: `CMPI.W #a0, 42(a6); BGT.W 79064` (→`7905e`)
- `7905e`: `BCHG.B #0, 15(a6)` (→`79064`) — FLOW
- `79064`: `JSR 496c2.l` — FLOW
- `7906a`: `MOVE.W #8820, 68(a6); MOVE.W #8820, 1e(a6); MOVE.W #34, d0; MOVE.W #1, d1; MOVE.B #0, d2; JSR c6a96.l`
- `79088`: `MOVE.W #1, 54(a6); LEA.L cb3e4.l, a0; JSR 490ba.l`
- `7909a`: `MOVE.W d0, 84(a6); JSR ea5f0.l`
- `790a4`: `RTS` — FLOW

**helper `790be`/`790d4`/`79114`(자식 연결 초기화) 6**
- `790be`: `BSET.B #7, 9b(a6); MOVE.W 78(a6), d0; MOVE.W 7a(a6), d1; MOVE.B d0, 8d(a6); MOVE.B d1, 8c(a6)` (→`790d4`)
- `790d4`: `EOR.W d0, d0; MOVE.W d0, 76(a6); MOVE.W d0, 78(a6); MOVE.W d0, 7a(a6); MOVE.W d0, 7c(a6); MOVE.W d0, 7e(a6); MOVE.W d0, 80(a6); JSR 4945e.l`
- `790f4`: `MOVE.L a0, 76(a6); RTS`
- `790fa`: `BRA.B 790d4` — FLOW
- `79114`: `BTST.B #7, 9b(a6); BNE.B 790fa` (→`7911c`) — FLOW
- `7911c`: `BSET.B #5, 9b(a6); BCLR.B #4, 9b(a6); MOVE.W 76(a6), 88(a6); BRA.B 790be`

**helper `791c0`/`791ea`(이동·낙하) 9**
- `791c0`: `TST.W 3a(a6); BMI.W 791d0` (→`791c8`)
- `791c8`: `MOVE.L #ffff0000, 3a(a6)` (→`791d0`)
- `791d0`: `JSR 4be2c.l` — FLOW
- `791d6`: `BTST.B #7, 15(a6); BEQ.W 791e8` (→`791e0`) — FLOW
- `791e0`: `CLR.L 36(a6); CLR.L 3a(a6)` (→`791e8`)
- `791e8`: `RTS` — FLOW
- `791ea`: `JSR 4be06.l` — FLOW
- `791f0`: `BTST.B #7, 15(a6); BEQ.B 791c0` (→`791f8`) — FLOW
- `791f8`: `RTS` — FLOW

**helper `791fa`(C 반환: `97` 계수) 5**
- `791fa`: `BTST.B #7, 15(a6); BNE.W 79218` (→`79204`) — FLOW
- `79204`: `ADDQ.B #1, 97(a6); CMPI.B #6, 97(a6); BLT.W 7921c` (→`79212`)
- `79212`: `ORI.B #1, ccr; RTS` — Set 생산
- `79218`: `CLR.B 97(a6)` (→`7921c`)
- `7921c`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**helper `79256`(D0 = 0/1/2 선택) 11**
- `79256`: `JSR 79400(pc)` — FLOW
- `7925a`: `BCS.W 79282` (→`7925e`) — C 소비
- `7925e`: `CMPI.B #c0, 94(a6); BEQ.W 79286` (→`79268`)
- `79268`: `JSR 79478(pc)` — FLOW
- `7926c`: `BCC.W 79286` (→`79270`) — C 소비
- `79270`: `JSR 49a58.l` — FLOW
- `79276`: `ANDI.W #1, d0; BEQ.W 79286` (→`7927e`)
- `7927e`: `BRA.W 7928c` — FLOW
- `79282`: `CLR.W d0; RTS`
- `79286`: `MOVE.W #1, d0; RTS`
- `7928c`: `MOVE.W #2, d0; RTS`

**helper `79292`(C 반환: `42` 범위 + `4945e`) 5**
- `79292`: `MOVE.W 42(a6), d0; CMPI.W #18, d0; BLT.W 792b2` (→`7929e`)
- `7929e`: `CMPI.W #128, d0; BGT.W 792b2` (→`792a6`)
- `792a6`: `JSR 4945e.l` — FLOW
- `792ac`: `EORI.B #1, ccr; RTS` — C 소비·반전 생산
- `792b2`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**helper `792b8`(C 반환) 13**
- `792b8`: `JSR 79292(pc)` — FLOW
- `792bc`: `BCC.W 79304` (→`792c0`) — C 소비
- `792c0`: `MOVEA.L 76(a6), a0; CMPI.B #5, 95(a6); BGT.W 792e4` (→`792ce`)
- `792ce`: `CMPI.W #0, 84(a6); BGT.W 79304` (→`792d8`)
- `792d8`: `CLR.W 84(a6); JSR 79478(pc)`
- `792e0`: `BCC.W 79304` (→`792e4`) — C 소비
- `792e4`: `BTST.B #4, 9b(a6); BEQ.W 792fe` (→`792ee`) — FLOW
- `792ee`: `JSR 79722(pc)` — FLOW
- `792f2`: `BCC.W 792fe` (→`792f6`) — C 소비
- `792f6`: `JSR 7942e(pc)` — FLOW
- `792fa`: `BCC.W 79304` (→`792fe`) — C 소비
- `792fe`: `ORI.B #1, ccr; RTS` — Set 생산
- `79304`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**helper `79566`(C 반환: `96` 계수, `494c0` 두 사각형; 두 번째 진입 `7957a`) 12**
- `79566`: `ADDQ.B #1, 96(a6); CMPI.B #1e, 96(a6); BLT.W 795b2` (→`79574`)
- `79574`: `MOVE.B #1e, 96(a6)` (→`7957a`)
- `7957a`: `JSR 4945e.l` — FLOW
- `79580`: `BCS.W 795b2` (→`79584`) — C 소비
- `79584`: `LEA.L 798aa(pc), a0; JSR 494c0.l` — FLOW
- `7958e`: `BCC.W 795b2` (→`79592`) — C 소비
- `79592`: `LEA.L 798b2(pc), a0; JSR 494c0.l` — FLOW
- `7959c`: `BCC.W 795ac` (→`795a0`) — C 소비
- `795a0`: `MOVEA.L 76(a6), a0; JSR 4954e.l` — FLOW
- `795aa`: `RTS` — FLOW
- `795ac`: `ORI.B #1, ccr; RTS` — Set 생산
- `795b2`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**helper `7960a`(C 반환: `9b` bit 3, `494c0`) 4**
- `7960a`: `BTST.B #3, 9b(a6); BEQ.W 79624` (→`79614`) — FLOW
- `79614`: `LEA.L 798c2(pc), a0; JSR 494c0.l` — FLOW
- `7961e`: `EORI.B #1, ccr; RTS` — C 소비·반전 생산
- `79624`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**helper `7967e`(`493bc`/`4950e` 대상 갱신) 5**
- `7967e`: `MOVEA.L 76(a6), a0; JSR 493bc.l` — FLOW
- `79688`: `BCS.W 79696` (→`7968c`) — C 소비
- `7968c`: `JSR 4950e.l` — FLOW
- `79692`: `MOVE.L a0, 76(a6)` (→`79696`)
- `79696`: `RTS` — FLOW

**helper `796cc`(`15` bit 0 → `9b` bit 0 반전 복사) 3**
- `796cc`: `BTST.B #0, 15(a6); BEQ.W 796de` (→`796d6`) — FLOW
- `796d6`: `BCLR.B #0, 9b(a6); RTS` — FLOW
- `796de`: `BSET.B #0, 9b(a6); RTS` — FLOW


## N16b(뒤 단위로 미루는 107 block, 결정 1)

[F] 재범위 N16 행 범위의 정적 도달 가운데 이 계약에 넣지 않는 시작(scratch `starts_full.txt` − `starts.txt`): `783ea 783f2 783fe 78404 78408 7840c 7843e 78444 7844a 78450 78454 78458 7845e 78462 78468 78490 78496 7849a 784a0 784a4 784aa 784ae 784b2 784b8 784bc 784c0 784cc 784f4 784fa 784fe 78504 78510 7851a 78522 78528 7852c 78534 7853a 7853e 78542 78548 7854c 78550 78556 7855a 78564 7856e 785ae 785b4 785ba 785c4 785d0 785d6 785dc 785e0 785e8 785ee 785f2 78622 78628 7862c 78632 78636 7863a 78640 78644 78648 7864e 78652 78656 7865c 78cc4 78cc8 78cd0 78cd6 78cdc 78ce6 78cf0 78cf4 78cfe 78d02 78d08 78d0a 78d1a 78d1e 78d2a 78d2e 78d3a 7919a 791a0 791aa 791b0 791b8 791be 79222 7922c 79240 7924c 79250 7962a 79630 79634 79638 7963c 79640 79648 7964e`. routing 범위는 `783ea..78660` `78cc4..78d5a` `7919a..791c0` `79222..79256` `7962a..79654`다. 경계: 이 계약의 경계에 더해 `4929e` `4be34` `4bfa4`(routing됨), `7930a` `796e6` `7970e`(미연결), `cc8b4`. [F] 400 frame 두 기록 모두 N16b 시작을 실행하지 않는다. [I] `49fc6`(interpreter) 반환 C를 소비하는 BCC 3곳(`784a0` `785dc`, 범위 밖 `789b6`)과 `MULS.W`(미도달 `79164`)는 N16b에서 다시 본다.

## carry

- [F] **소비 25 block.** Unknown C로 들어오면 `objects n16 caller requires known carry`(상태 보존)다.
  - BCC/BCS 23개(한 명령 block, FLOW_ONLY):
    - `775bc BCC.W 7763c`, `79688 BCS.W 79696`: `493bc`(N15, 경계)의 C.
    - `775f6`(`79454`), `77620`(`7949c`), `7762e`(`794e2`), `7925a BCS`(`79400`), `7926c`(`79478`), `792e0`(`79478`), `792f2`(`79722`), `792fa`(`7942e`), `7958e` `7959c`(`494c0`): 경계 helper의 C. 이 단위에서는 typed 입력 C로만 들어온다.
    - `77604`(`7960a`), `77612` `77652` `77664`(`79566`), `77672`(`792b8`), `77680` `77d80 BCS`(`791fa`), `792bc`(`79292`): N16 helper의 known C(결정 5).
    - `79580 BCS.W 795b2`: N08 `4945e`의 C(`494a6`/`494ac` Clear, `494b4` Set).
    - `78c6a BCC.W 78c74`: U05 `1ab02`(사각형 화면 판정)의 C. Clear → RTS, Set → `78de6` 설치.
    - `78c86 BCC.W 78c9a`: fade_card `28ae`의 C. Clear → `78c9a`, Set → `4970a` 뒤 `ORI.B #1,CCR`.
    - Clear면 분기 대상(BCS는 fall-through), Set이면 반대.
  - `EORI.B #1,CCR; RTS` 2개(결정 4): `792ac`(`4945e`의 C), `7961e`(`494c0`의 C). known이면 뒤집은 known C로 RTS.
- [F] **known 생산 11 block**: Set `79212` `792fe` `795ac`(`ORI.B #1,CCR; RTS`), `78c96`(`ORI.B #1,CCR`, 결정 5); Clear `7921c` `792b2` `79304` `795b2` `79624`(`ANDI.B #fe,CCR; RTS`); 반전 `792ac` `7961e`.
- [F] **FLOW_ONLY 93 block**(C 보존): JSR/JMP/BRA/RTS block, `LEA`/`MOVEA`+`JSR`(`775b2` `79584` `79592` `795a0` `79614` `7967e`), BTST/BSET/BCLR/BCHG(Z만)+Bcc block, BCC/BCS 소비 23개. 목록: `77596 7759a 775a0 775b2 775bc 775c0 775ce 775f2 775f6 77600 77604 7760e 77612 7761c 77620 7762a 7762e 77638 7763c 77646 77652 7765c 77660 77664 7766e 77672 7767c 77680 7768a 77d70 77d76 77d7c 77d80 77d8a 7839a 783c0 783c6 783d2 783dc 783e6 78c22 78c34 78c44 78c4a 78c54 78c6a 78c74 78c86 78de6 7905e 79064 790a4 790fa 79114 791d0 791d6 791e8 791ea 791f0 791f8 791fa 79256 7925a 79268 7926c 79270 7927e 792a6 792b8 792bc 792e0 792e4 792ee 792f2 792f6 792fa 7957a 79580 79584 7958e 79592 7959c 795a0 795aa 7960a 79614 7967e 79688 7968c 79696 796cc 796d6 796de`.
- [F] **carry 보존 목록 95 PC** = FLOW_ONLY 93 + `792ac` `7961e`(결정 4).
- [F] **Unknown 59 block**: 그 밖 `MOVE`/`CLR`/`TST`/`CMPI`/`ADDQ`/`SUBQ`/`EOR`/`ANDI.W`/`ASR` 포함 block, `MOVE.L #imm,(A6)` 설치 block, `MOVEA.L #imm,A0`+`MOVE.W`+`JSR 28ae` 자식 block, 애니메이션 block(`MOVE.L 2000d4.l,22(A6)`), `79282` `79286` `7928c`(결정 6).
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 flag 읽기로 시작하는 곳은 위 C 소비 25곳뿐이다).

## 구현 범위와 규약

- routing 16 범위(위 표). 짝수 PC 618개 중 block 시작 163, 내부 455. 내부 PC 직접 진입은 `unsupported animation objects n16 PC`다. 범위 이웃과 구멍은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술은 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 95 PC를 넣는다. 생산 block은 실행 뒤 known C를 둔다.
- 제어 이동은 모두 정적이다. 설치 값(`MOVE.L #imm,(A6)`)은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `28ae` 자식 대상(A0 = `78e0e`)도 자료다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다.
- 스택: JSR 복귀 LONG만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `2000d4` → 노드 `22(A6)`(`77562` `77d38`), 이어서 `22(A6)` 기록의 LONG `c0`(`77562`) / `20`(`77d38`)을 A1(애니메이션 목록)로 읽어 `49f8c`(D0.W = `100`, A0 = A6 + `26`)로 넘긴다. `78c9a`는 LONG `2000d4`를 A1로 읽어 `cc778`(경계)로 넘긴다.
- [F] 주소만 넘기는 고정 ROM 자료: 사각형 `798ca`(A0, `1ab02`), `798aa` `798b2` `798c2`(A0, `494c0`), 표 `cb3e4`(A0, `490ba`), `cdef8`(A0, `cc778`), `28ae` 자식 대상 `78e0e`(A0, D0.W = `14`).
- [F] work RAM(노드 A6): BYTE `15`(bit 0: `7905e BCHG`, `796cc` 읽기; bit 7: `791d6` `791f0` `791fa` 읽기), `17`(= `ff`), `5e`(CLR), `5f`(→ A0 + `5f`), `61`(bit 0·7 읽기), `8c`/`8d`(= `7a`/`78` 하위 BYTE), `93`(= 8), `94`(= `f0`, `79256` 비교 `c0`), `95`(signed > 5), `96`(1씩 증가, signed < `1e`면 그대로, 아니면 `1e`), `97`(1씩 증가, signed < 6이면 Clear, 아니면 Set; `15` bit 7이면 0), `99`(TST, SUBQ, = `1e`), `9b`(bit 0: `77562 BCHG`, `796cc` 복사; bit 2·3·4·5·7 읽기, bit 4 지움·bit 5·7 세움); WORD `1e`/`68`(= `8820`), `20`(= `b`), `42`(signed > `a0`, `18` ≤ x ≤ `128`), `54`(= 1), `76`~`80`(0으로 지움, `76` → `88`), `84`(`490ba` 반환 D0.W, 감소·0 하한, CLR, signed > 0 비교), `88`(TST), `3a`(TST.W 부호); LONG `(A6)`(설치), `22`, `36`(CLR, `ASR.L #1`), `3a`(CLR, = `ffff0000`), `76`(대상 노드 포인터: `4950e`/`4945e` 반환 A0, `493bc`/`4954e` 인자 A0).
- [F] 상수 인자: `c6a96` D0.W/D1.W/D2.B = `34`/1/0, `490ba` A0 = `cb3e4`, `4970a` D0.W/D1.W = 0/`18`, `cc778` A0/A1/D1.W/D2.W = `cdef8`/bank LONG/`b`/1.
- [F] `79292`: `42.W`가 signed `18` 미만 또는 `128` 초과면 Clear, 아니면 `4945e`의 C를 뒤집어 반환한다(`4945e`가 Clear — BYTE `A5+568e` ≠ 0 — 이면 Set).
- [I] 게임 의미: `7839a`는 stage event로 나타나는 적 객체로 보인다. `79114`/`790be`가 대상 정보(`76`~`80`)를 지우고 `4945e`로 가장 가까운 player 노드를 `76`에 둔다. `77596`은 대기 상태로, player 거리·화면 위치(`494c0` 사각형)·계수(`96` `97`)에 따라 다른 상태(범위 밖 설치 8개)를 고르고, `791fa`가 `15` bit 7(착지)이 없는 frame을 6번 세면 `77d38`(낙하)로 바꾼다. `78c22`는 `61` bit 7(파괴)이면 폭발 자식 `78e0e`를 만들고 `cc778` 파편 루틴으로 넘기며, 아니면 `1ab02`로 화면 밖이면 `78de6`(`2a00` 삭제)를 설치한다. 확인하지 않았다.

## 의존·경계

- [F] N16 → 기존(모두 routing됨, 진입 case 있음): interpreter `49f8c` `49fc6`, U11 `4be06` `496c2`, U18 `4be2c`, U12 `4c0ac` `490ba`, input `4d7a6`, stage_area `49a58`, N08 `4945e`(C 반환), U15 `4950e`, N14 `4970a`, U01 `4b54e`, U05 `1ab02`(C 반환) `c6a96`, fade_card `28ae`(C 반환) `2a00`(JMP), U13 `ea5f0`.
- [F] 실행부 없는 경계: `493bc`(N15) `494c0` `4954e` `79400` `7942e` `79454` `79478` `7949c` `794e2` `79722` `787d2` `cc778`, N16b 시작 `783ea` `785f2`. 단위 test는 그 PC에서 stop만 확인한다(F4 test 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N16: stage event 표 `e8da4`, `5417e JMP 7839a`, 범위 밖 미연결 코드의 `JSR`/`BRA`/설치(요약). N15가 병합되면 `493bc`가 이어진다.
- [F] N15와 경계·범위가 겹치지 않는다. N17(`7a388..` 등)과도 겹치지 않는다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 163 시작 모두 typed fixture로 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 11개, 그 밖 Unknown), zero-step, 내부 455 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 소비 25곳의 Unknown carry 오류, 경계 stop. bank LONG과 `1ab02` 사각형은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 실제 생산자(`1ab02`, `28ae`, `4945e`, N16 helper)를 따라 들어간 fixture로 native 분기를 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(callback, 설치 상태, 실제 bank LONG·기록, 소비자 native 분기).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, 회귀 0, complete 변화 없음(N15 전).

## 작업자 검증 기록 (scratch)

- [F] 변경 파일: 새 `engine/src/animation_machine_objects_n16.cpp`(SHA256 `8aa45dae5a86f3a63a99c9f620e954c61826d5bf7a57e79a53a1f977edd908c2`), 새 `engine/tests/animation_machine_objects_n16_test.cpp`(SHA256 `3d64cd26d6d1c22ddb93c745188243efd1807f795f14b36085c28229e2070328`), 공유 최소 수정 `engine/src/animation_machine.cpp`(routing `else if` 1개 16 범위, carry 보존 case group 1개 95 PC; SHA256 `547f242b80b3629daef775c9af522d577e47437c59a06d216132324d812a0715`), `engine/src/animation_machine_internal.h`(선언 1줄; SHA256 `800b2398168c1776efe1cbb360669f7c6bc571dbcc0ce5ba8ce42d765d967045`), `Makefile`(source list·test target·run line; SHA256 `c55ad9463db22a41e623082cddfe774760ba2bc55eb09181e67b65e06d54b2fe`), `tools/verify_animation_machine.py`(SOURCES; SHA256 `30d1d67b6df3ddc0afe140104c8885fddd5f00fc3415cf0caeb72091939d42c7`). `animation_machine_interpreter.cpp`와 다른 단위 실행부는 고치지 않았다. 패치 파일 없음(결정 9).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0. 새 test: `animation machine objects n16: 561 fixtures (32 checked errors, 285 kept C), 163 blocks, 2041 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen.py`, Unicorn + 합성 물리 바이트 `798ca`(사각형) `2000d4`(bank LONG → work RAM 기록 `10e600`), 표 SHA256 `d6233e20dac6b446c88a9fe38da7dcd46d85644b9b07026c75a324132309d743`): 163 시작 모두 fixture 진입 또는 경로로 덮임. 실제 생산자 추종 fixture: `1ab02`(`78c5c`, 안/밖 4방향·반전 → 소비자 `78c6a`), `28ae`(`78c76`, 성공/실패; `4970a`→`49214`→`43e38`까지 따라가 `78c96` ORI 뒤 `78c9a`→`cc778`), `4945e`(`568e` = 0/1/2/3, `790d4` `79292` `792b8` `79566` `7957a` `7760e` `7766e` `7839a` → 소비자 `79580`과 반전 `792ac`), N16 helper의 ORI/ANDI/EORI 결과 → 실제 소비자 `77604` `77612` `77652` `77664` `77672` `77680` `77d80` `792bc`. block 표는 시작마다 incoming C clear/set의 native 후계·digest와 계약 C 분류, Unknown C는 소비 25곳에서 정확한 오류, zero-step 163×3, 내부 455 PC 정확한 오류, 홀수 PC(범위마다 양 끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`과 RTS 복귀 `10fe40`(9 fixture), routing 구멍의 도달 불가 명령 `78c58` `78cc0` `78cc2`는 routing 밖, 경계 stop 21곳(`493bc` `494c0` `4954e` `79400` `7942e` `79454` `79478` `7949c` `794e2` `79722` `787d2` `cc778` `783ea` `785f2` 및 다른 단위 진입). checked 오류 fixture 7개(홀수 노드 읽기·쓰기, 홀수 대상 쓰기, ROM 노드 읽기, 장치 쓰기, 스택 장치, RTS 장치). 돌연변이 8개(signed `97`/`96` 비교, `42` BGT, `78c96` ORI, `ASR.L`, `796cc` bit, EORI 반전, `77d80` BCS 방향)가 모두 test를 실패시켰다(scratch `mut/mut.out`).
- [F] 실제 ROM 차분(`realrom/real16.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, 무작위 work RAM, seed 1·2·3 각 1,500건): 불일치 0/0/0, 시작 도달 162/161/163(합집합 163). native stop은 STOP과 경계(`493bc` `494c0` `783ea` `787d2` `79400` `79454` `79478` `7949c` `794e2` `79722` `cc778`)·`2a00`. 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `77604` 26, `77612` 40, `77652` 17, `77664` 67, `77672` 160, `77680` 198, `77d80` 83, `78c6a` 66, `78c86` 58, `792ac` 136, `792bc` 235, `79580` 115건. native가 깨끗이 멈추지 않은 입력(무작위 기록으로 interpreter·이동 helper가 낮은 PC로 감)은 건너뛰고 셌다(89/67/72건).
- [F] 자연 상태 차분(scratch `natural/natural16.py` `compare16.py`): RNG 초기화+응답 `80` 400 frame 선언 모델을 seed 76 77 98 99 104 105로 다시 돌려(pass 끝 digest가 native seed 파일과 모두 같음) N16 callback 진입 상태 126개(seed마다 `7839a` 1, `77596` 5, `77d38` 1, `77d70` 13, `78de6` 1)를 잡았다. 선언 host 변경(복귀 LONG = STOP) 뒤 native와 C++ 결과가 126/126 같다. `78de6`은 `2a00`, 나머지는 모두 `78c22`→`7967e`의 N15 경계 `493bc`에서 멈춘다(결과 SHA256 `9a8154b440d32284fde4cac9eebf777d2ef1c5a97e221608d405bd8b118eba8b`).
- [F] 기준(`3e4b0b3` `git archive` 사본 `ms5-scratch/n16/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 13,928·node 115,196, 불일치 0, 자연 완주 127. N16 뒤(이 작업 트리): 같은 값, 불일치 0, 회귀 0, 바뀐 seed 0(결과 `diff_results.json` SHA256 `5c9e2de678d9a7cbc1a7a31cc341f6a6f8064d26794fe29c2ca2511172e8714b`, 기준과 바이트까지 같음).
- [F] RNG 초기화 400 frame 차분: 기준 complete 118, 일치 pass 47,200·node 349,637, 불일치 0(verification.json SHA256 `d3f6656cbf2f2348ea2eefd14dc1923fbb63d9c45107336f00a06faad37604d1`). N16 뒤: complete 118, 같은 pass·node, 불일치 0, 회귀 0, `other` 0, 도구 종료 0(SHA256 `d2c3f48b0a4e03c354cbeec8bc64a7b90260bdf53cf5c7209e67a46cb843ac5b`). seed 기록 차이는 18 seed의 `current_router_sha256` 값뿐이다. seed 76 77 98 99 104 105는 기준과 같이 frame 0 N15 `708a6`에서 멈춘다(요약).
- [F] ROM SHA256·mtime 작업 전후 같음(`29112a94…`, `1791291625`).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] N15(`493bc`)가 병합된 뒤 N16 자연 경로의 `493bc` 이후(`7968c`/`79692` 또는 `79696`)와 N17 seed의 완주는 N15·N17 통합에서 확인한다.
3. [U] N16b(107 block)와 범위 밖 고아 설치 `776da` `7777a` `7783e` `778fa` `77a70` `77af4` `77c68` `77d8e` `77de8`, 자식 `78e0e`, 경계 helper `79400`~`79722` `494c0` `4954e` `787d2` `cc778`의 동작은 해당 단위에서 정한다.
4. [U] 미참조 진입 `783ae` `783bc`(앞 `BRA.W` 뒤, 참조 없음)의 목적.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n16/`(`n16.py` block·범위 계산(`N16STOPS`로 분할 경계), `n16cls.py` carry 분류, `n16fmt.py` block 목록, `n16stat.py` 범위 SHA·짝수 PC, `n16xref.py` 범위 밖 참조, `n16reach.py` `n16seen.py` 자연 도달, `unitdef.py`, `gen/` typed fixture 생성·test 조립, `mut/` 돌연변이, `realrom/` 실제 ROM 차분, `natural/` 자연 상태 차분, `fp/` 프레임 패스·RNG 차분; 저장소 밖).
