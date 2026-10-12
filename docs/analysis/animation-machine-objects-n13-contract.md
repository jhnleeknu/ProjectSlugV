# 객체 callback F4 N13(옛 U25): `59ea2` 노드 callback(설치 `59ed6`, 공용 `5a802`·설치 `5a880` `5a8dc` `5a9ae`, 공용 꼬리 `5a9c2`), helper `5aa3a`·`5ab5a`, interpreter 명령 callback `5ab16` `5ab1c` `5ab22` `5ab3a`, `28ae` 자식 `5b220`(설치 `5b2ae`, ADDX·DIVU), `28ae` 자식 `d3580`(설치 `d35ce`)·helper `d3ab8` `d3ae8` `d3b1a`, 노드 callback `dbfac` 계약 초안

**상태: 계약 초안(작업자 Claude Opus 5.5 / high). 메인 결정 전이다. 아래 "작업자 검증 기록"은 이 초안대로 구현한 scratch 기록이다(커밋하지 않음).**

범위 근거는 재범위 문서 `animation-machine-object-callbacks-f4-rescope.md`(SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 메인 결정 1~5와 N13 행(155 block, `59ea2..59f1a` `5a7c8..5ab6c` `5b220..5b4c6` `d3580..d3614` `d3ab8..d3b70` `dbfac..dbfb8`, callback `59ea2` `59ed6` `5b220` `5b2ae` `d3580` `d35ce` `dbfac`, 경계 callee `482fa` `d3802`, X `5b356 ADDX.B`, `5b442`/`5b454 DIVU.W`, bank 1, 새 seed RNG 16 17 / base 16 17, 미실행 설치 8(+89), 옛 U25 155)이다. 재범위 scratch `final.out`의 N13 함수 진입은 `59ea2` `59ed6` `5a7c8` `5a9ae` `5aa3a` `5ab16` `5ab1c` `5ab5a` `5b220` `5b2ae` `d3580` `d35ce` `d3ab8` `d3ae8` `d3b1a` `dbfac`(16개)다. 단위 형식과 규약은 N11 계약(SHA256 `213f96a02e5b52f62aa4dcbc2787ec2cf1d4aad582c76da9e031d9f8c065d797`), N09 계약(SHA256 `0ff994e110ef3146cdafaea6aa59be074a024cf487cc43542dbc2e4a5ecee140`; 범위 안 설치 사슬 포함, DIVU overflow), N05 계약(SHA256 `403b0b6ba157097695918182b971b2411e645072f39802a51b5ca5e728104cf3`; 유일 선행 N 재계산 `bddb4`)과 N04 계약(SHA256 `3a87155a37c93679aae5f849b1deac3ec766a32f2142a5a1e21743ad6ef6c813`; 선행이 여럿인 Bcc는 각 선행에 묶음)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 JSR/BSR 대상, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback, 범위 안의 `MOVEA.L #imm,A0`+`JSR 28ae` 자식, interpreter 명령 callback 표 값)로 정한다. Unicorn TB 분할은 쓰지 않는다. 묶을 연속 Bcc는 없다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC는 경계다. 범위 안의 참조되지 않는 코드는 routing하지 않는다(`5a9bc JMP 2a24.L`, `d3ace..d3ae8` helper; 아래 결정 2).
- 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`NOT`/`SWAP` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만인 block, callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. block 사이 flag 재계산은 predecessor가 하나일 때만 쓴다(N05 `bddb4` 선례; N13은 `5b326` 하나). 선행이 여럿이면 각 선행에 묶는다(N04 `ab1a6`/N09 `af7b0` 선례; N13에는 없다). SUBX/ADDX의 X는 같은 block 안에서 만들어져야 한다(N13 `5b356`은 같은 block의 `ASR.B`가 만든다). 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N13의 코드와 고정 자료는 모두 `<100000`이라 CPU 주소와 file offset이 같다. banked window 자료는 LONG `200190` 하나다(`5aa40` `5b226`; "자료"). 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n13`(HEAD `43a137f` = N11까지 통합 + interpreter callback live routing, `engine/src/animation_machine.cpp` SHA256 `9876c3a3355aef40e160696ee3f72f27196d07bb166c8d5256133adf74984056`, routing 규칙 68개; `engine/src/animation_machine_interpreter.cpp` SHA256 `3b91b9fae2a93a820c6de9b276bbb9b2cbe9b6bb859d607e7f977cc02095e540`)을 참조했다. N13 routing 범위의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N12(`52e4a..532a0` `539e4..53ee0`, 작업 트리 `metalslug-n12`)와 겹치지 않고, N13은 그 PC를 부르지 않는다(두 단위가 모두 `482fa` `d3802`를 경계로 부른다). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n13/n13blocks.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N13 = 175 block**(재범위 N13 행 155 + 20, 결정 1), 코드 8 범위 2,042바이트, 457명령이다. 진입 18개: 노드 callback `59ea2`(LONG `e9044`), `dbfac`(LONG `dbfc4`); 범위 안 `MOVE.L #imm,(A6)` 설치 callback `59ed6`(`59ed0`) `5a880`(`5a87a`) `5a8dc`(`5a8d2`) `5a9ae`(`5a9a8`) `5b2ae`(`5b2a8`) `d35ce`(`d35c8`); 범위 밖 설치 `5a7c8`(`5a7c2`, 재범위 함수 진입); 범위 안 `28ae` 자식 `5b220`(`5aaa6`) `d3580`(`d3aec`); 범위 안 JSR/BSR 대상 `5aa3a` `5ab5a` `d3ab8` `d3ae8` `d3b1a`; interpreter 명령 callback 표 `4a5e0`의 값 `5ab16` `5ab1c` `5ab22` `5ab3a`.
- [F] 묶인 Bcc 0개. 계산 PC(JMP/JSR 표, 레지스터 간접)·TRAP·I/O port 쓰기·bank 변경은 없다. X/나눗셈: `5b356 ADDX.B D1,D0`(X는 같은 block `5b34e`의 `ASR.B #3,D0`이 만든다), `5b442 DIVU.W 82(A6),D0`·`5b454 DIVU.W D1,D0`(같은 block `5b442`). 그 밖 산술: `ASR.L #3`(`5a886`), `LSL.W #8`(`5b2f0`), `LSR.W`(`5b480` `d3596` `d35a4`), `SWAP`, `EXT.W`, `NEG.W`, `NOT.B`, `EOR.W`, `Scc`(`ST` `SPL` `SEQ`), `MOVEM.L D0-D5`(`d3ae8`/`d3afc`).
- [F] **경계 callee(실행부 없음)**: `482fa`(`5a802`), `d3802`(`5a82e` `5a8e8` `5a90e` `5a91e` `5a934` `5ab22`), `1a3ac`(`5a8dc`, 재범위 행에 없음; 결정 6). 범위 밖 설치 값 `5a376`(`59f0c` `5a7f4`) `5a5ca`(`5a9fe`) `d3614`(`d35de`) `d3646`(`d35ec`) `d3678`(`d35fc` `d360c`)과 범위 밖 `28ae` 자식 `5ab6c`(`5a8fe`) `5ab82`(`5ab3a`) `5b4c6`(`5b3c0`)은 node LONG/A0에 쓰는 값일 뿐 이 단위는 그 PC로 가지 않는다.
- [F] **flag**:
  - callee C 소비 block **6개**(모두 단독 Bcc, FLOW_ONLY): `5a8be`(`BCC`, `5ab5a`가 RTS로 돌려주는 `49fc6`의 C), `5aa2c`(`BCC`, U01 `4b54e`), `5b2b4`(`BCC`, `288c`), `5b3d0`(`BCC`, `28ae`), `5b48c`(`BCC`, N04 `4a46c`), `d3608`(`BCS`, `288c`). Unknown C로 들어오면 `objects n13 caller requires known carry`.
  - known carry 생산 block 없음(N13 안의 RTS 중 소비자가 C를 읽는 것은 `5ab6a`(FLOW, `49fc6`의 C를 그대로)뿐이다).
  - N 재계산 block **1개**: `5b326 SPL.B 7d(A6)`(유일 선행 `5b316 CMPI.W #8000,D1; BNE.W 5b326`의 N; 결정 4).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n13reach.py`): RNG·base 두 기록 모두 seed 16 17만 N13 PC를 실행한다. TB 시작 77개는 모두 block 시작이다. 정적 재생 예측: RNG complete +16 17, base complete +16 17(재범위 행과 같다). 자연 미도달 시작 98개(`5a7c8` 계열, `5a802` 계열, `5a8dc` 사슬, `5a9ae`, `5ab22` `5ab3a`, `5b220`의 ADDX·DIVU 경로 등)는 typed fixture와 실제 ROM 차분으로 덮는다.

## 메인 결정 (초안 권고)

1. **block 수 175(재범위 155와 +20).**
   - +1 `5a880`: `5a87a MOVE.L #5a880,(A6)`의 설치 진입이다. fall-through로 이어져 재범위 함수 본문에 이미 있지만 재범위 디코드는 설치 대상을 block 시작으로 세지 않았다. 이 계약은 N11(`aef18` 등) 관례대로 block 시작으로 둔다.
   - +14 `5a8dc` 사슬(`5a8dc..5a9a8`): `5a8d2 MOVE.L #5a8dc,(A6)`의 범위 안 설치 callback 본문이다(재범위 결정 2, N09 선례). 재범위는 별도 함수("미실행 설치")로 셌다. 이 사슬은 `5a9a8`에서 `5a9ae`(재범위 함수 진입)를 설치한다. [F] 사슬의 첫 호출 `JSR 1a3ac`가 경계라 현재 routing에서 `5a8dc`는 그 앞에서 멈춘다(결정 6).
   - +5 interpreter 명령 callback `5ab22`(2 block) `5ab3a`(3 block): 표 `4a5e0`(`5ab16` `5ab1c` `5ab22` `5ab3a`; interpreter `4a352`/`4a43c JSR (A1)`, base `4a500` + 4×명령)의 셋째·넷째 값이다. 재범위 함수 진입에는 자연 실행된 `5ab16` `5ab1c`만 있고, 행 범위 `5a7c8..5ab6c` 안에 있다. 권고: 같은 표의 형제라 함께 넣는다. 넣지 않으면 N13 범위 안에 미연결 조각 `5ab22..5ab5a`가 남는다.
2. **routing 범위는 코드만(8 범위).** `59ea2..59f1a` `5a7c8..5a9bc` `5a9c2..5ab6c` `5b220..5b4c6` `d3580..d3614` `d3ab8..d3ace` `d3ae8..d3b70` `dbfac..dbfb8`(짝수 PC 1,021개, block 시작 175, 내부 846).
   - 범위 안 미연결(routing 안 함): `5a9bc..5a9c2`(`JMP 2a24.L`; 어떤 분기·LONG도 가리키지 않는다), `d3ace..d3ae8`(helper `d3ace` = `d3ab8`에 `ST.B a3(A0)`를 더한 형; 참조 없음. `d3a80 JSR d3ae8`의 함수 `d3a7c`는 범위 밖).
   - 이웃: `59ea2` 앞 `59ea0 RTS`(미연결 함수 꼬리), `59f1a..5a7c8`(같은 상태기계의 미실행 상태들 `59f1a` `59f38` … `5a376` `5a5ca`, 설치 `5a7c2`; 미연결), `5ab6c..`(`28ae` 자식 `5ab6c` `5ab82`, 미연결), `5b200..5b220`(미연결 helper 꼬리, `5b21e RTS`), `5b4c6..`(`28ae` 자식 `5b4c6`, 미연결), `d3570..d3580`(미연결), `d3614..d3ab8`(설치 대상 `d3614` `d3646` `d3678`과 `d3a7c` 등, 미연결), `d3b70..`(미연결 `d3b70`), `dbf9a..dbfac`(N11 `dbf80` 자료 뒤 자료, LONG `dbfa6`), `dbfb8..`(자료). 겹침 없음.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n13.cpp`의 `animation_objects_n13_block`. 오류는 `unsupported animation objects n13 PC`(내부 PC), `objects n13 caller requires known carry`(소비 6 block), `objects n13 DIVU zero divisor`(`5b442`의 두 `DIVU.W` 제수가 0일 때; 결정 5).
4. **`5b326` N 재계산(유일 선행).** [F] `5b326`은 `5b31a BNE.W 5b326`(block `5b316 CMPI.W #8000,D1; BNE.W 5b326`)의 분기 대상이고 다른 참조(분기·LONG)가 없다(`5b322 BRA.W`는 `5b32a`로 간다). `CMPI.W`와 `BNE` 사이 `D1`은 그대로라 N = bit 15 of (`D1.W` − `8000`) = NOT bit 15 of `D1.W`로 정확히 재계산한다. `SPL.B 7d(A6)`는 N = 0(곧 `D1.W` bit 15 = 1)이면 BYTE `ff`, 아니면 `00`을 쓴다. CCR은 바꾸지 않는다(FLOW_ONLY). Unicorn typed fixture에서 `5b326`을 직접 진입할 때는 SR N을 이 식과 같게 둔다(N05 `bddb4` 선례).
5. **DIVU 두 곳(`5b442` block).** 68000 `DIVU.W <ea>,Dn`: 제수 = `<ea>`의 WORD(무부호). 제수 0이면 원본은 0 나누기 예외(vector 5, 처리기 LONG `00000014` = `202`)로 가는데 이 단위는 예외 처리를 모형화하지 않으므로 checked 오류 `objects n13 DIVU zero divisor`로 멈추고 상태를 보존한다(원본에 제수 검사가 없다). 몫 = `Dn`(32비트 무부호) / 제수가 `ffff`를 넘으면 overflow: V = 1, `Dn`은 바뀌지 않는다(N/Z는 뒤 `ANDI.L`/`TST.W`가 덮어 무관). 아니면 `Dn` = (나머지 << 16) | 몫. C는 항상 0이고 X는 바뀌지 않는다.
   - [F] `5b442 DIVU.W 82(A6),D0`: 앞 block `5b428`이 `MOVEQ #0,D0; MOVE.W 84(A6),D0; … SUB.W D1,D0`(그리고 `5b440 NEG.W D0`)이라 자연 경로에서는 `D0` ≤ `ffff`이므로 overflow가 없다. 직접 진입은 `D0` 상위 WORD가 임의라 overflow가 가능하다(그대로 구현). 제수 `82(A6)`는 `5b302`가 `0400`으로 쓰는 WORD다. [I] 정상 흐름에서 `84 ≠ 80`이면 이미 한 번 `0400`이 쓰였으므로 0이 아니다. 블록 안에 보호가 없으므로 0은 checked 오류다.
   - [F] `5b454 DIVU.W D1,D0`: `ANDI.L #ffff,D0`(첫 DIVU의 몫만), `MOVEQ #0,D1; MOVE.B 7b(A6),D1; ADDQ.B #1,D1` → 제수 = (`7b(A6)` + 1) & `ff`. `7b(A6)` = `ff`이면 제수 0 → checked 오류. [I] 자연 경로에서는 `5b420 SUBQ.B #1,7b(A6); BEQ`를 지난 값(1..`fe`)이라 0이 아니다. 피제수 ≤ `ffff`, 제수 ≥ 1이라 overflow는 없다(그래도 규칙대로 구현).
6. **경계 `1a3ac`(재범위 행에 없음).** [F] `5a8dc` 사슬의 `JSR 1a3ac.L` 대상 `1a3ac MOVEQ #4,D0`(2바이트)는 N05 범위 `1a3ae..1a3c8`로 fall-through하는 별도 진입이다(형제 `1a3a6 MOVEQ #8,D0; BRA.W 1a3ae`). 어느 단위 범위에도 없다. 이 계약은 경계(`unsupported animation machine PC`)로 둔다. 권고: 한 명령짜리라 다음 정리 단위(또는 N05 보강)에서 routing한다. `5a8dc` 사슬은 400 frame 안에 자연 실행되지 않는다.
7. **무효화 탐침: 없다.** `engine/tests`와 `tools`에서 N13 짝수 PC를 경계·rollback 탐침으로 쓰는 곳은 없다(검색: N13 진입·범위 상수). 경계 `d3802`를 stop으로 쓰는 U16·N07 test는 그대로 유효하다(N13은 `d3802`를 routing하지 않는다).
8. **interpreter callback.** `animation_machine_interpreter.cpp`는 바꾸지 않는다. [F] `43a137f`의 interpreter는 명령 callback 대상을 live routing으로 보낸다(허용 목록 없음). `5ab16` `5ab1c`(자연 실행)와 `5ab22` `5ab3a`는 N13 routing으로 실행된다. [F] interpreter 복귀점 `4a354`/`4a43e`는 `MOVE.W (A7)+,-7ff0(A5)`라 callback의 C를 읽지 않는다.

## 원본 바이트 근거

[F] 코드 8 범위 합계 2,042바이트. 범위 순서로 이어 붙인 SHA256 `0f0b7d9bbb08e0143b037bf91fa8f6e42b47760fb7f63e03b063ca390917c1ff`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `59ea2..59f1a` | 120 | `00d6d2e6c0b5b84ac358518ea85fd932de0899d19967bcc8aa0109897e94a462` | `59ea2`(초기화, 설치 `59ed6`) |
| `5a7c8..5a9bc` | 500 | `7fa503735dc0a920fdd04f9d6d75a84abd6664db07ca52ee505cf35d84e06e6f` | `5a7c8`, 공용 `5a802`(설치 `5a880`), 설치 `5a8dc` 사슬, `5a9ae` |
| `5a9c2..5ab6c` | 426 | `952df50f9887a8d1cc6829d9c6545b4c7302afe518eb1619f6e4f737cf08bc4f` | 공용 꼬리 `5a9c2`, helper `5aa3a`, interpreter callback 4개, helper `5ab5a` |
| `5b220..5b4c6` | 678 | `f1d9c5b97178f57e986641724951b952d2020ff938f7c34d2f40acbf4ec966d9` | `28ae` 자식 `5b220`(설치 `5b2ae`) |
| `d3580..d3614` | 148 | `e955cff5222c82e01e45c17609a1ff786650637dd8de77b5ecd8378b6800aa68` | `28ae` 자식 `d3580`(설치 `d35ce`) |
| `d3ab8..d3ace` | 22 | `091cb098eee964f6cf8825ace84236281e4c0ad462c0b9e5f90ab0e2a441ad1d` | helper `d3ab8` |
| `d3ae8..d3b70` | 136 | `d985eeba6b9973d2cd571b026acfa6835437f68ca1e71ceefb37cb1a5a81e643` | helper `d3ae8`(`28ae` 자식 `d3580` 생성), `d3b1a` |
| `dbfac..dbfb8` | 12 | `35619d9116b22efe34b6e6bb8dca76643d188d08ce5585c2de531a72bab2a128` | `dbfac`(`5c8d(A5)` = `ff` 후 `JMP 2a00`) |

- [F] 참조(raw LONG 검색 scratch `n13raw.py`; JSR/BSR/Bcc 검색 `n13refs.py`): `59ea2` ← LONG `e9044`([I] N11의 `e8eb4`·`e8f78`와 같은 stage event 표 영역). `dbfac` ← LONG `dbfc4`. `5a7c8` ← `5a7c2 MOVE.L #`(범위 밖). `5b220` ← `5aaa6 MOVEA.L #`(`28ae` 자식). `d3580` ← `d3aec MOVEA.L #`. `5ab16` `5ab1c` `5ab22` `5ab3a` ← LONG `4a5e0` `4a5e4` `4a5e8` `4a5ec`(interpreter 명령 callback 표, base `4a500`). `5aa3a` ← `59eba JSR d16(PC)`만. `5ab5a` ← N13 `59f12` `5a7fa` `5a8ba` `5a9b4`와 미연결 `59f48` `59fc2` `5a02a` `5a068` `5a0d2` `5a110` `5a168` `5a19c` `5a218` `5a254` `5a2b4` `5a2f0` `5a3f4` `5a44a` `5a49c` `5a4fe` `5a53c` `5a584` `5a68c` `5a712` `5a780`(모두 `BSR.W`). `5a802` ← N13 `59edc` `5a7ce`와 미연결 20곳(`BNE.W`). `5a9c2` ← N13 `59f16` `5a7fe`와 미연결 22곳(`BRA.W`/`BCS.W`). `d3ab8` ← `5ab0a`(N13)와 미연결 `56b52`(`JSR .L`). `d3ae8` ← `d3abc`(N13)와 미연결 `d3a80`. `d3b1a` ← `d35ce`(N13)와 미연결 `d364c`. `d35f2` ← 미연결 `d3644` `d3674`(`BRA`; 미연결 상태 `d3614`/`d3646`이 이 공용 꼬리로 들어온다).
- [F] 미연결 호출자가 N13 helper의 C를 읽는 곳: `5ab5a`의 미연결 호출자 중 `59f48` `5a068` `5a3f4` `5a49c` `5a53c` `5a68c` `5a780`은 다음이 `BCC.W`다(`49fc6`의 C). 그 호출자들은 N13 밖이라 이 단위의 FLOW `5ab6a RTS`가 C를 그대로 돌려주는 것으로 충분하다.

## block 목록과 실행 의미

[F] 175 block. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.W` 연산은 하위 WORD만, `.B`는 하위 BYTE만 바꾼다. `MOVEQ`는 LONG 전체를 부호확장 값으로 쓴다. `MOVEA.L`/`LEA`는 주소 레지스터 32비트 전체를 바꾸고 CCR을 바꾸지 않는다. `JSR`/`BSR`은 복귀 LONG을 쌓고 대상으로 간다. `JMP 2a00.L`은 PC = `2a00`. "FLOW"는 C 보존 block, "C 소비"는 callee C 소비 block이다(표시 없는 block은 Unknown).

**노드 callback `59ea2`(설치 `59ed6`) 12**
- `59ea2`: `MOVE.W #100,2e(a6); MOVE.W #80,32(a6); JSR 4c0ac.l` (→`59eb4`)
- `59eb4`: `MOVE.W 32(a6),86(a6); JSR 5aa3a(pc)` (→`59ebe`)
- `59ebe`: `BRA.W 59ec2` — FLOW
- `59ec2`: `MOVE.W #280,2e(a6); MOVE.L #fffe0000,36(a6); MOVE.L #59ed6,(a6)` (→`59ed6`)
- `59ed6`: `BTST.B #0,80(a6); BNE.W 5a802` (→`59ee0`) — FLOW
- `59ee0`: `JSR 43ea4.l` (→`59ee6`) — FLOW
- `59ee6`: `MOVE.L #1780000,d0; CMP.L 2e(a6),d0; BLE.W 59f12` (→`59ef4`)
- `59ef4`: `MOVE.L d0,2e(a6); MOVE.W #743,d0; JSR 3af8.l` (→`59f02`)
- `59f02`: `MOVE.W #19d4,d0; JSR 3af8.l` (→`59f0c`)
- `59f0c`: `MOVE.L #5a376,(a6)` (→`59f12`)
- `59f12`: `BSR.W 5ab5a` (→`59f16`) — FLOW
- `59f16`: `BRA.W 5a9c2` — FLOW

**설치 callback `5a7c8`(범위 밖 `5a7c2` 설치) 7**
- `5a7c8`: `BTST.B #0,80(a6); BNE.W 5a802` (→`5a7d2`) — FLOW
- `5a7d2`: `JSR 43ea4.l` (→`5a7d8`) — FLOW
- `5a7d8`: `MOVE.L #1780000,d0; CMP.L 2e(a6),d0; BGE.W 5a7fa` (→`5a7e6`)
- `5a7e6`: `MOVE.W #743,d0; JSR 3af8.l` (→`5a7f0`)
- `5a7f0`: `MOVE.L d0,2e(a6); MOVE.L #5a376,(a6)` (→`5a7fa`)
- `5a7fa`: `BSR.W 5ab5a` (→`5a7fe`) — FLOW
- `5a7fe`: `BRA.W 5a9c2` — FLOW

**공용 `5a802`(`80(A6)` bit 0 분기; 설치 `5a880`) 19**
- `5a802`: `ST.B 5d44(a5); JSR 482fa.l` (→`5a80c`) — FLOW
- `5a80c`: `BSET.B #4,80(a6); MOVE.W #20,7a(a6); JSR 4b6ec.l` (→`5a81e`)
- `5a81e`: `MOVE.W #743,d0; JSR 3af8.l` (→`5a828`)
- `5a828`: `JSR 46ef4.l` (→`5a82e`) — FLOW
- `5a82e`: `LEA.L 5b5e6(pc),a1; JSR d3802.l` (→`5a838`) — FLOW
- `5a838`: `MOVE.W #e0ed,68(a0); MOVE.W #e0ed,1e(a0); MOVEA.L #5c40e,a1; MOVE.W #100,d0; JSR 49f8c.l` (→`5a854`)
- `5a854`: `JSR 496c2.l` (→`5a85a`) — FLOW
- `5a85a`: `MOVE.L #80000,36(a6); MOVEQ #0,d0; MOVE.W 86(a6),d0; SWAP d0; CMP.L 32(a6),d0; BEQ.W 5a87a` (→`5a872`)
- `5a872`: `MOVE.L #40000,3a(a6)` (→`5a87a`)
- `5a87a`: `MOVE.L #5a880,(a6)` (→`5a880`)
- `5a880`: `JSR 43ea4.l` (→`5a886`) — FLOW
- `5a886`: `MOVE.L 36(a6),d0; ASR.L #3,d0; SUB.L d0,36(a6); TST.L 3a(a6); BEQ.W 5a8ba` (→`5a898`)
- `5a898`: `ADDI.L #ffffb0fe,3a(a6); MOVEQ #0,d0; MOVE.W 86(a6),d0; SWAP d0; MOVE.L 32(a6),d1; CMP.L d1,d0; BLE.W 5a8ba` (→`5a8b2`)
- `5a8b2`: `MOVE.L d0,32(a6); CLR.L 3a(a6)` (→`5a8ba`)
- `5a8ba`: `BSR.W 5ab5a` (→`5a8be`) — FLOW
- `5a8be`: `BCC.W 5a8d8` (→`5a8c2`) — C 소비
- `5a8c2`: `MOVEQ #0,d0; MOVE.W 86(a6),d0; SWAP d0; CMP.L 32(a6),d0; BNE.W 5a8d8` (→`5a8d2`)
- `5a8d2`: `MOVE.L #5a8dc,(a6)` (→`5a8d8`)
- `5a8d8`: `BRA.W 5aa34` — FLOW

**설치 callback `5a8dc` 14**
- `5a8dc`: `BSET.B #3,80(a6); JSR 1a3ac.l` (→`5a8e8`) — FLOW
- `5a8e8`: `LEA.L 5b5d4(pc),a1; JSR d3802.l` (→`5a8f2`) — FLOW
- `5a8f2`: `MOVE.W #e0ed,68(a0); MOVE.W #e0ed,1e(a0); MOVEA.L #5ab6c,a0; MOVE.W #0,d0; JSR 28ae.l` (→`5a90e`)
- `5a90e`: `MOVE.W #3c,76(a0); LEA.L 5b60a(pc),a1; JSR d3802.l` (→`5a91e`)
- `5a91e`: `MOVE.W #e0ea,68(a0); MOVE.W #e0ea,1e(a0); LEA.L 5b5f8(pc),a1; JSR d3802.l` (→`5a934`)
- `5a934`: `MOVE.W #e0ed,68(a0); MOVE.W #e0ed,1e(a0); LEA.L 5b5e6(pc),a1; JSR d3802.l` (→`5a94a`)
- `5a94a`: `MOVE.W #e0ec,68(a0); MOVE.W #e0ec,1e(a0); JSR 8ff4.l` (→`5a95c`)
- `5a95c`: `MOVE.W #d3e,d0; MOVE.B #0,d1; JSR 8ebe.l` (→`5a96a`)
- `5a96a`: `MOVE.W #d3f,d0; MOVE.B #0,d1; JSR 8ebe.l` (→`5a978`)
- `5a978`: `MOVE.W #d40,d0; MOVE.B #0,d1; JSR 8ebe.l` (→`5a986`)
- `5a986`: `MOVE.B 19(a6),14(a6); MOVEA.L #5cef4,a1; MOVE.W #100,d0; JSR 49f8c.l` (→`5a99c`)
- `5a99c`: `JSR 496c2.l` (→`5a9a2`) — FLOW
- `5a9a2`: `JSR 4b6ec.l` (→`5a9a8`) — FLOW
- `5a9a8`: `MOVE.L #5a9ae,(a6)` (→`5a9ae`)

**설치 callback `5a9ae` 3**
- `5a9ae`: `JSR 43ea4.l` (→`5a9b4`) — FLOW
- `5a9b4`: `BSR.W 5ab5a` (→`5a9b8`) — FLOW
- `5a9b8`: `BRA.W 5aa34` — FLOW

**공용 꼬리 `5a9c2` 12**
- `5a9c2`: `TST.L 7c(a6); BEQ.W 5a9e4` (→`5a9ca`)
- `5a9ca`: `MOVEA.L 7c(a6),a0; MOVEQ #0,d0; MOVEQ #0,d1; MOVE.B 88(a6),d0; MOVE.B 89(a6),d1; EXT.W d0; EXT.W d1; JSR 47070.l` (→`5a9e4`)
- `5a9e4`: `MOVE.W 54(a6),d0; CMP.W 82(a6),d0; BCC.W 5aa04` (→`5a9f0`)
- `5a9f0`: `BSET.B #1,80(a6); BNE.W 5aa04` (→`5a9fa`) — FLOW
- `5a9fa`: `ST.B 81(a6); MOVE.L #5a5ca,(a6)` (→`5aa04`)
- `5aa04`: `BTST.B #0,80(a6); BNE.W 5aa34` (→`5aa0e`) — FLOW
- `5aa0e`: `BTST.B #7,61(a6); BEQ.W 5aa26` (→`5aa18`) — FLOW
- `5aa18`: `MOVE.L #0,56(a6); BSET.B #0,80(a6)` (→`5aa26`)
- `5aa26`: `JSR 4b54e.l` (→`5aa2c`) — FLOW
- `5aa2c`: `BCC.W 5aa34` (→`5aa30`) — C 소비
- `5aa30`: `CLR.B 5e(a6)` (→`5aa34`)
- `5aa34`: `CLR.B 5e(a6); RTS`

**helper `5aa3a`(`28ae` 자식 `5b220`) 11**
- `5aa3a`: `MOVE.W #183,20(a6); MOVE.L 200190.l,22(a6); JSR 8ff4.l` (→`5aa4e`)
- `5aa4e`: `MOVE.W #d3c,d0; MOVE.B #0,d1; JSR 8ebe.l` (→`5aa5c`)
- `5aa5c`: `MOVE.W #d3d,d0; MOVE.B #0,d1; JSR 8ebe.l` (→`5aa6a`)
- `5aa6a`: `MOVE.B 19(a6),14(a6); MOVE.W #922,d0; JSR 4a496.l` (→`5aa7a`)
- `5aa7a`: `BSET.B #6,15(a6); MOVE.W #0,68(a6); MOVE.W #0,1e(a6); MOVE.W #734,d0; JSR 3af8.l` (→`5aa96`)
- `5aa96`: `MOVEA.L #5b9d2,a1; MOVE.W #100,d0; JSR 49f8c.l` (→`5aaa6`)
- `5aaa6`: `MOVEA.L #5b220,a0; MOVE.W #a,d0; JSR 28ae.l` (→`5aab6`)
- `5aab6`: `LEA.L 76(a6),a1; MOVE.L a1,76(a0); LEA.L 5dcaa.l,a0; JSR 490ba.l` (→`5aaca`)
- `5aaca`: `MOVE.W d0,54(a6); LEA.L 5dcf4.l,a0; JSR 490ba.l` (→`5aada`)
- `5aada`: `MOVE.W d0,82(a6); CLR.B 81(a6); MOVE.L #0,98(a6); MOVE.L #5dc5e,56(a6); MOVE.L #5d85e,7c(a6); MOVE.W #8,d0; MOVE.W #10,d1; MOVE.W #2f,d2; MOVE.W #3f,d3; JSR d3ab8.l` (→`5ab10`)
- `5ab10`: `CLR.B 9d(a6); RTS`

**interpreter 명령 callback `5ab16` `5ab1c` `5ab22` `5ab3a` 7**
- `5ab16`: `MOVE.W (a0),76(a6); RTS`
- `5ab1c`: `MOVE.W (a0),88(a6); RTS`
- `5ab22`: `LEA.L 5b61c(pc),a1; JSR d3802.l` (→`5ab2c`) — FLOW
- `5ab2c`: `MOVE.W #e0ec,68(a0); MOVE.W #e0ec,1e(a0); RTS`
- `5ab3a`: `MOVEA.L #5ab82,a0; MOVE.W #14,d0; JSR 28ae.l` (→`5ab4a`)
- `5ab4a`: `MOVE.W #ffe8,d0; MOVE.W #72,d1; JSR 49214.l` (→`5ab58`)
- `5ab58`: `RTS` — FLOW

**helper `5ab5a`(`49fc6` C 반환) 3**
- `5ab5a`: `MOVE.W 1e(a6),d0; JSR ce02.l` (→`5ab64`)
- `5ab64`: `JSR 49fc6.l` (→`5ab6a`) — FLOW
- `5ab6a`: `RTS` — FLOW

**`28ae` 자식 `5b220`(설치 `5b2ae`) 55**
- `5b220`: `MOVE.W #183,20(a6); MOVE.L 200190.l,22(a6); MOVEA.L c(a6),a0; LEA.L 2e(a0),a1; MOVEA.L 76(a6),a0; MOVE.B (a0),d0; MOVE.B 1(a0),d1; CLR.B 2(a0); EXT.W d0; EXT.W d1; JSR 43e04.l` (→`5b24e`)
- `5b24e`: `MOVE.W #2000,d0; MOVE.W d0,80(a6); MOVE.W d0,84(a6); MOVEA.L 76(a6),a0; MOVE.W #ffff,4(a0); MOVE.W #d3a,d0; MOVE.B #0,d1; JSR 8ebe.l` (→`5b272`)
- `5b272`: `MOVE.W #d45,d0; MOVE.B #0,d1; JSR 8ebe.l` (→`5b280`)
- `5b280`: `MOVE.B 19(a6),14(a6); BSET.B #6,15(a6); MOVE.W #1,68(a6); MOVE.W #1,1e(a6); MOVEA.L #5cff4,a1; MOVE.W #100,d0; JSR 49f8c.l` (→`5b2a8`)
- `5b2a8`: `MOVE.L #5b2ae,(a6)` (→`5b2ae`)
- `5b2ae`: `JSR 288c.l` (→`5b2b4`) — FLOW
- `5b2b4`: `BCC.W 5b4c0` (→`5b2b8`) — C 소비
- `5b2b8`: `BTST.B #3,80(a0); BNE.W 5b4c0` (→`5b2c2`) — FLOW
- `5b2c2`: `BTST.B #4,80(a0); BEQ.W 5b2de` (→`5b2cc`) — FLOW
- `5b2cc`: `BCLR.B #4,80(a0); MOVE.W 80(a6),d0; MOVE.W d0,84(a6); CLR.B 7b(a6)` (→`5b2de`)
- `5b2de`: `MOVEQ #0,d0; MOVE.W 84(a6),d1; MOVEA.L 76(a6),a0; MOVE.W 4(a0),d0; BMI.W 5b2f4` (→`5b2f0`)
- `5b2f0`: `LSL.W #8,d0; MOVE.W d0,d1` (→`5b2f4`)
- `5b2f4`: `MOVE.W 84(a6),d2; MOVE.W d1,84(a6); CMP.W d2,d1; BEQ.W 5b308` (→`5b302`)
- `5b302`: `MOVE.W #400,82(a6)` (→`5b308`)
- `5b308`: `MOVE.W 82(a6),d7; MOVE.W 80(a6),d2; SUB.W d2,d1; BEQ.W 5b348` (→`5b316`)
- `5b316`: `CMPI.W #8000,d1; BNE.W 5b326` (→`5b31e`)
- `5b31e`: `NOT.B 7d(a6); BRA.W 5b32a`
- `5b326`: `SPL.B 7d(a6)` (→`5b32a`) — FLOW
- `5b32a`: `TST.B 7d(a6); BEQ.W 5b334` (→`5b332`)
- `5b332`: `NEG.W d7` (→`5b334`)
- `5b334`: `ADD.W d7,d2; SUB.W d7,d1; EOR.W d1,d7; BPL.W 5b340` (→`5b33e`)
- `5b33e`: `ADD.W d1,d2` (→`5b340`)
- `5b340`: `MOVE.W d2,80(a6); BRA.W 5b34e`
- `5b348`: `MOVE.W #ffff,4(a0)` (→`5b34e`)
- `5b34e`: `MOVEQ #0,d1; MOVE.B 80(a6),d0; ASR.B #3,d0; ADDX.B d1,d0; ANDI.B #1f,d0; MOVE.B d0,86(a6); MOVEA.L 76(a6),a0; MOVE.B (a0)+,d0; MOVE.B (a0),d1; EXT.W d0; EXT.W d1; MOVE.W d0,2e(a6); MOVE.W d1,32(a6); JSR 43e34.l` (→`5b37a`)
- `5b37a`: `MOVEA.L 76(a6),a0; MOVE.B 7b(a6),d0; MOVE.B 3(a0),d1; CLR.B 3(a0); ADD.B d1,7b(a6); TST.B 7b(a6); BNE.W 5b3a0` (→`5b396`)
- `5b396`: `MOVE.B #0,7c(a6); BRA.W 5b472`
- `5b3a0`: `MOVE.B #1,7c(a6); CLR.B d7; TST.B d0; BNE.W 5b3b4` (→`5b3ae`)
- `5b3ae`: `ST.B d7; BRA.W 5b3ba` — FLOW
- `5b3b4`: `SUBQ.B #1,7a(a6); SEQ.B d7` (→`5b3ba`)
- `5b3ba`: `TST.B d7; BEQ.W 5b472` (→`5b3c0`)
- `5b3c0`: `MOVEA.L #5b4c6,a0; MOVE.W #a,d0; JSR 28ae.l` (→`5b3d0`)
- `5b3d0`: `BCC.W 5b420` (→`5b3d4`) — C 소비
- `5b3d4`: `MOVEQ #0,d2; MOVE.B 80(a6),d1; CMP.B 7f(a6),d1; BNE.W 5b3f4` (→`5b3e2`)
- `5b3e2`: `MOVE.B 7e(a6),d2; ADDQ.B #1,d2; ANDI.W #3,d2; MOVE.B d2,7e(a6); SUBQ.B #1,d2; ADD.W d2,d2` (→`5b3f4`)
- `5b3f4`: `MOVE.B d1,7f(a6); ADD.B d2,d1; MOVE.B d1,76(a0); SUB.B d2,d1; MOVE.L #2c0000,d0; MOVE.L a0,-(a7); JSR 443d2.l` (→`5b40e`)
- `5b40e`: `MOVEA.L (a7)+,a0; SWAP d0; SWAP d1; JSR 49214.l` (→`5b41a`)
- `5b41a`: `MOVE.L c(a6),c(a0)` (→`5b420`)
- `5b420`: `SUBQ.B #1,7b(a6); BEQ.W 5b46c` (→`5b428`)
- `5b428`: `MOVEQ #0,d0; MOVE.W 84(a6),d0; MOVE.W 80(a6),d1; SUB.W d1,d0; BEQ.W 5b466` (→`5b438`)
- `5b438`: `TST.B 7d(a6); BEQ.W 5b442` (→`5b440`)
- `5b440`: `NEG.W d0` (→`5b442`)
- `5b442`: `DIVU.W 82(a6),d0; ANDI.L #ffff,d0; MOVEQ #0,d1; MOVE.B 7b(a6),d1; ADDQ.B #1,d1; DIVU.W d1,d0; TST.W d0; BNE.W 5b45e` (→`5b45c`)
- `5b45c`: `ADDQ.W #1,d0` (→`5b45e`)
- `5b45e`: `MOVE.B d0,7a(a6); BRA.W 5b46c`
- `5b466`: `MOVE.B #6,7a(a6)` (→`5b46c`)
- `5b46c`: `MOVE.W #180,8a(a6)` (→`5b472`)
- `5b472`: `MOVE.W 8a(a6),d0; ADD.W d0,88(a6); ANDI.B #3,88(a6); LSR.W #4,d0; SUB.W d0,8a(a6); JSR 4a46c.l` (→`5b48c`)
- `5b48c`: `BCC.W 5b496` (→`5b490`) — C 소비
- `5b490`: `MOVE.B 1a(a6),14(a6)` (→`5b496`)
- `5b496`: `MOVE.B #ff,17(a6); JSR 49fc6.l` (→`5b4a2`)
- `5b4a2`: `MOVE.B 19(a6),14(a6); MOVEA.L 76(a6),a0; TST.B 2(a0); BEQ.W 5b4be` (→`5b4b4`)
- `5b4b4`: `CLR.B 2(a0); MOVE.B 1a(a6),14(a6)` (→`5b4be`)
- `5b4be`: `RTS` — FLOW
- `5b4c0`: `JMP 2a00.l` — FLOW

**`28ae` 자식 `d3580`(설치 `d35ce`) 19**
- `d3580`: `MOVE.W 76(a6),d0; MOVE.W 78(a6),d1; JSR 49290.l` (→`d358e`)
- `d358e`: `MOVEA.L c(a6),a0; MOVE.W 54(a0),d0; LSR.W #1,d0; TST.W 7e(a6); BNE.W d35a4` (→`d35a0`)
- `d35a0`: `MOVE.W d0,7e(a6)` (→`d35a4`)
- `d35a4`: `LSR.W #1,d0; TST.W 80(a6); BNE.W d35b2` (→`d35ae`)
- `d35ae`: `MOVE.W d0,80(a6)` (→`d35b2`)
- `d35b2`: `MOVEA.L #d418c,a1; MOVE.W #100,d0; JSR 49f8c.l` (→`d35c2`)
- `d35c2`: `JSR 49fc6.l` (→`d35c8`) — FLOW
- `d35c8`: `MOVE.L #d35ce,(a6)` (→`d35ce`)
- `d35ce`: `JSR d3b1a(pc)` (→`d35d2`) — FLOW
- `d35d2`: `MOVE.W 54(a6),d0; CMP.W 7e(a6),d0; BGT.W d35e4` (→`d35de`)
- `d35de`: `MOVE.L #d3614,(a6)` (→`d35e4`)
- `d35e4`: `CMP.W 80(a6),d0; BGT.W d35f2` (→`d35ec`)
- `d35ec`: `MOVE.L #d3646,(a6)` (→`d35f2`)
- `d35f2`: `BTST.B #7,61(a6); BEQ.W d3602` (→`d35fc`) — FLOW
- `d35fc`: `MOVE.L #d3678,(a6)` (→`d3602`)
- `d3602`: `JSR 288c.l` (→`d3608`) — FLOW
- `d3608`: `BCS.W d3612` (→`d360c`) — C 소비
- `d360c`: `MOVE.L #d3678,(a6)` (→`d3612`)
- `d3612`: `RTS` — FLOW

**helper `d3ab8`·`d3ae8`(`28ae` 자식 `d3580`) 4**
- `d3ab8`: `MOVEQ #0,d4; MOVEQ #0,d5; JSR d3ae8(pc)` (→`d3ac0`)
- `d3ac0`: `MOVE.W #1001,68(a0); MOVE.W #1001,1e(a0); RTS`
- `d3ae8`: `MOVEM.L d0-d5,-(a7); MOVEA.L #d3580,a0; MOVE.W #a,d0; JSR 28ae.l` (→`d3afc`)
- `d3afc`: `MOVEM.L (a7)+,d0-d5; MOVE.W d0,76(a0); MOVE.W d1,78(a0); MOVE.W d2,7a(a0); MOVE.W d3,7c(a0); MOVE.W d4,7e(a0); MOVE.W d5,80(a0); RTS`

**helper `d3b1a` 8**
- `d3b1a`: `JSR 43e34.l` (→`d3b20`) — FLOW
- `d3b20`: `MOVEA.L c(a6),a0; MOVE.B 12(a0),12(a6); MOVE.B 13(a0),13(a6); BTST.B #0,15(a0); BNE.W d3b44` (→`d3b3a`)
- `d3b3a`: `BCLR.B #0,15(a6); BRA.W d3b4a` — FLOW
- `d3b44`: `BSET.B #0,15(a6)` (→`d3b4a`) — FLOW
- `d3b4a`: `BCLR.B #7,61(a6); TST.B a3(a6); BNE.W d3b68` (→`d3b58`)
- `d3b58`: `BTST.B #7,61(a0); BEQ.W d3b68` (→`d3b62`) — FLOW
- `d3b62`: `BSET.B #7,61(a6)` (→`d3b68`) — FLOW
- `d3b68`: `MOVE.W 54(a0),54(a6); RTS`

**노드 callback `dbfac` 1**
- `dbfac`: `MOVE.B #ff,5c8d(a5); JMP 2a00.l`

수: `59ea2` 12 + `5a7c8` 7 + `5a802` 19 + `5a8dc` 14 + `5a9ae` 3 + `5a9c2` 12 + `5aa3a` 11 + interpreter callback 7 + `5ab5a` 3 + `5b220` 55 + `d3580` 19 + `d3ab8`/`d3ae8` 4 + `d3b1a` 8 + `dbfac` 1 = 175(`starts.txt`와 같다). 분류 합계: FLOW_ONLY 54(소비자 6 포함) + 생산 0 + Unknown 121 = 175.

### 의미 세부

- 비교·분기(모두 같은 block 안의 flag):
  - `59ee6 BLE`: `D0` = `01780000`, LONG `D0` − `2e(A6)`가 Z 또는 N≠V면 `59f12`. `5a7d8 BGE`: 같은 뺄셈의 N = V면 `5a7fa`. `5a898 BLE`: `D0` − `D1`(LONG). `d35d2`/`d35e4 BGT`: WORD `D0` − `7e(A6)`/`80(A6)`가 !Z ∧ N = V면 분기. V는 (a^b)&(a^res)의 부호 bit로 명시 계산한다.
  - `5a9e4 BCC`: WORD `54(A6)` − `82(A6)`의 무부호 borrow가 없으면(`54` ≥ `82`) `5aa04`.
  - `5a9f0 BSET.B #1,80(A6); BNE`: 설정 전 bit가 1이면 `5aa04`(Z = 원래 bit의 반전). `59ed6`/`5a7c8`/`5aa04 BTST.B #0,80(A6)`, `5aa0e BTST.B #7,61(A6)`, `5b2b8`/`5b2c2 BTST.B #3/#4,80(A0)`, `d35f2 BTST.B #7,61(A6)`, `d3b20 BTST.B #0,15(A0)`, `d3b58 BTST.B #7,61(A0)`는 Z만 쓴다.
  - `5b2de BMI`: `MOVE.W 4(A0),D0`의 WORD bit 15. `5b334 BPL`: `EOR.W D1,D7` 결과 bit 15. `5b392`/`5b3aa`/`5b3bc`/`d3b50 TST.B` + Bcc, `5b4ac TST.B 2(A0)`, `5a9c2 TST.L`, `5a886 TST.L 3a(A6)`, `d358e`/`d35a4 TST.W`, `5b458 TST.W D0`.
  - `5b3b4 SUBQ.B #1,7a(A6); SEQ.B D7`: 뺀 BYTE가 0이면 `D7.B` = `ff`, 아니면 `00`. `5b3ae ST.B D7`, `5a802 ST.B 5d44(A5)`, `5a9fa ST.B 81(A6)`는 `ff`를 쓴다(CCR 불변).
- 산술:
  - `5a85a`/`5a898`/`5a8c2`: `MOVEQ #0,D0; MOVE.W 86(A6),D0; SWAP D0` = `86(A6)` << 16.
  - `5a886`: `D0` = `36(A6)` ASR 3(부호 bit 채움, LONG), `36(A6)` −= `D0`(LONG). `5a898`: `3a(A6)` += `ffffb0fe`(LONG).
  - `5a9ca`: `D0` = sext8(BYTE `88(A6)`) & `ffff`, `D1` = sext8(BYTE `89(A6)`) & `ffff`(`MOVEQ #0` 뒤 `MOVE.B`+`EXT.W`; 상위 WORD 0).
  - `5b220`: `D0`/`D1` 하위 WORD = sext8(BYTE `(A0)`/`1(A0)`), A1 = 부모 node + `2e`, A0 = `76(A6)` 기록 포인터.
  - `5b2f0 LSL.W #8,D0; MOVE.W D0,D1`.
  - `5b308`~`5b340`(방향 추적): `D7.W` = `82(A6)`(속도), `D2.W` = `80(A6)`(현재), `D1.W` = 목표 − 현재(WORD). 0이면 `5b348`(`4(A0)` = `ffff`). `D1.W` = `8000`이면 `NOT.B 7d(A6)`(방향 뒤집기), 아니면 `SPL.B 7d(A6)`(결정 4). `7d` ≠ 0이면 `NEG.W D7`. `D2` += `D7`, `D1` −= `D7`, `D7` ^= `D1`(WORD); 결과 bit 15가 1이면(지나침) `D2` += `D1`(= 목표). `80(A6)` = `D2.W`.
  - `5b34e`(ADDX): `MOVEQ #0,D1`; `D0.B` = BYTE `80(A6)`; `ASR.B #3,D0`(BYTE 산술 shift 3번, X = C = 마지막으로 밀려난 bit = 원래 BYTE의 bit 2); `ADDX.B D1,D0` → `D0.B` = (`D0.B` + 0 + X) & `ff`; `ANDI.B #1f`; `86(A6)` = 그 BYTE. 이어 `D0`/`D1` = sext8 BYTE `(A0)`/`1(A0)`(`(A0)+`로 A0 += 1), `2e(A6)` = `D0.W`, `32(A6)` = `D1.W`, `JSR 43e34`. ADDX의 Z(0이 아니면 지움, 0이면 유지)·X·C는 뒤 `ANDI.B`가 덮거나 쓰이지 않는다. X는 block 밖으로 전하지 않는다.
  - `5b37a`: `D0.B` = 이전 `7b(A6)`; `D1.B` = BYTE `3(A0)`; `3(A0)` = 0; `7b(A6)` += `D1.B`(BYTE).
  - `5b3e2`: `D2.B` = `7e(A6)` + 1(BYTE); `ANDI.W #3,D2`(WORD); `7e(A6)` = `D2.B`; `SUBQ.B #1,D2`(BYTE; `D2.B` = 0이면 `ff`, 상위 BYTE는 그대로); `ADD.W D2,D2`(WORD).
  - `5b3f4`: `7f(A6)` = `D1.B`; `D1.B` += `D2.B`; BYTE `76(A0)` = `D1.B`; `D1.B` −= `D2.B`; `D0` = `002c0000`; `MOVE.L A0,-(A7)`; `JSR 443d2`. `5b40e`: `MOVEA.L (A7)+,A0; SWAP D0; SWAP D1; JSR 49214`.
  - `5b428`: `MOVEQ #0,D0; MOVE.W 84(A6),D0; MOVE.W 80(A6),D1; SUB.W D1,D0`(WORD; 상위 WORD 0). `5b440 NEG.W D0`.
  - `5b442`: 결정 5. 이어 `TST.W D0`이 0이면 `5b45c ADDQ.W #1,D0`. `5b45e`: `7a(A6)` = `D0.B`.
  - `5b472`: `D0.W` = `8a(A6)`; `88(A6)` += `D0.W`(WORD); `ANDI.B #3,88(A6)`(주소 `88(A6)`의 BYTE = WORD `88`의 상위 BYTE); `LSR.W #4,D0`; `8a(A6)` −= `D0.W`(WORD); `JSR 4a46c`.
  - `d358e`: `D0.W` = WORD `54(부모)` LSR 1; `7e(A6)` = 0이면 그 값. `d35a4`: 다시 LSR 1, `80(A6)` = 0이면 그 값.
  - `d3ae8`: `MOVEM.L D0-D5,-(A7)`(24바이트, `D0`이 낮은 주소); `A0` = `d3580`; `D0.W` = `a`; `JSR 28ae`. `d3afc`: `MOVEM.L (A7)+,D0-D5`(CCR 불변); 새 node(A0) WORD `76` `78` `7a` `7c` `7e` `80` = `D0`~`D5` 하위 WORD; `RTS`. `28ae`가 반환한 C는 읽지 않는다.
  - `d3b20`: BYTE `12`/`13(A6)` = 부모 BYTE `12`/`13`; 부모 `15` bit 0을 `15(A6)` bit 0으로 복사(`BCLR`/`BSET`). `d3b4a`: `BCLR.B #7,61(A6)`; `a3(A6)` = 0이고 부모 `61` bit 7이면 `61(A6)` bit 7 설정. `d3b68`: `54(A6)` = 부모 WORD `54`.
- 호출·설치: `5a9fa`/`59f0c`/`5a7f0`/`d35de`/`d35ec`/`d35fc`/`d360c`의 범위 밖 설치 값은 node LONG `(A6)` 쓰기다. `5a8f2`/`5ab3a`/`5b3c0`의 범위 밖 `28ae` 자식은 `A0` 값이다.

## 구현 범위와 규약

- routing 8 범위(결정 2). 짝수 PC 1,021개 중 block 시작 175, 내부 846. 내부 PC 직접 진입은 `unsupported animation objects n13 PC`다. 범위 이웃은 기존 실행부 또는 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. `NEG`/`SUB`/`ADD`/`CMP`/`ADDX`/`DIVU`는 원래 폭의 무부호 산술로 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다(`ASR`는 부호 bit 채움을 명시, `DIVU`는 `uint32_t` 나눗셈, 제수 0은 먼저 검사). flag는 같은 block 안의 Bcc/Scc만 쓴다. 예외: `5b326`(결정 4).
- **FLOW_ONLY 54개**(C 보존): `59ebe` `59ed6` `59ee0` `59f12` `59f16` `5a7c8` `5a7d2` `5a7fa` `5a7fe` `5a802` `5a828` `5a82e` `5a854` `5a880` `5a8ba` `5a8be` `5a8d8` `5a8dc` `5a8e8` `5a99c` `5a9a2` `5a9ae` `5a9b4` `5a9b8` `5a9f0` `5aa04` `5aa0e` `5aa26` `5aa2c` `5ab22` `5ab58` `5ab64` `5ab6a` `5b2ae` `5b2b4` `5b2b8` `5b2c2` `5b326` `5b3ae` `5b3d0` `5b48c` `5b4be` `5b4c0` `d35c2` `d35ce` `d35f2` `d3602` `d3608` `d3612` `d3b1a` `d3b3a` `d3b44` `d3b58` `d3b62`.
- **소비자 6개**(FLOW_ONLY 안): `5a8be` `5aa2c` `5b2b4` `5b3d0` `5b48c`(BCC: Clear면 분기) `d3608`(BCS: Set이면 분기). Unknown C면 `objects n13 caller requires known carry`(상태 보존).
- **known carry 생산 0개.** 그 밖 121 block(`MOVE`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`CLR`/`NOT`/`NEG`/`ADD`/`ADDI`/`ADDQ`/`SUB`/`SUBQ`/`AND`/`ANDI`/`EOR`/`ASR`/`LSR`/`LSL`/`EXT`/`SWAP`/`ADDX`/`DIVU` block, `MOVE.L #imm,(A6)` 설치 block, `MOVE`+`JSR` block, banked animation block `5aa3a` `5b220`)은 Unknown이다. (`5aa34 CLR.B; RTS`, `5ab10 CLR.B; RTS`, `5ab16`/`5ab1c`/`5ab2c MOVE.W; RTS`, `d3ac0` `d3afc` `d3b68`은 C를 0으로 만들지만 소비자가 없다: 노드 dispatcher, `59ebe BRA`, interpreter 복귀점, `5ab10`, `d35d2 MOVE.W`. 따라서 Unknown으로 둔다.)
- 제어 이동은 모두 정적이다. 스택: `JSR`/`BSR` 복귀 LONG, `5b3f4`/`5b40e`의 A0 LONG, `d3ae8`/`d3afc`의 `MOVEM.L` 24바이트.
- I/O port 쓰기 없음. bank 변경 없음. work RAM 밖 쓰기, 미해결·홀수 읽기는 기존 checked 오류다(예: A6/A0/부모 node 홀수, `76(A6)` 기록 포인터 홀수일 때의 `4(A0)` WORD).

## 자료

- [F] banked window LONG `200190`(`5aa40` `5b226`; bank base 기준 live bus). 그 값을 `22(A6)`에 쓰기만 한다(animation 자료 포인터; 이 단위는 그 내용을 읽지 않는다). C++는 주소를 고정하지 않고 현재 bank base로 읽는다(PVC bank 모델).
- [F] 이 단위가 직접 읽지 않고 주소만 넘기는 fixed ROM 자료: animation 목록 `5c40e` `5cef4` `5b9d2` `5cff4` `d418c`(`49f8c`), 표 `5dcaa` `5dcf4`(`490ba`), 자식 배치 기록 `5b5d4` `5b5e6` `5b5f8` `5b60a` `5b61c`(`d3802`). node LONG에 쓰는 상수: `5dc5e`(`56(A6)`), `5d85e`(`7c(A6)`).
- [F] work RAM: node(A6) WORD `1e` `20` `2e` `32` `54` `68` `7a` `7e` `80` `82` `84` `86` `88` `8a`, LONG `(A6)` `c` `22` `2e` `32` `36` `3a` `56` `76` `7c` `98`, BYTE `14` `15` `17` `19` `1a` `5e` `61` `7a` `7b` `7c` `7d` `7e` `7f` `80` `81` `88` `89` `9d` `a3`; 부모 node(`c(A6)`) WORD `54`, BYTE `12` `13` `15` `61`, 바이트 주소 `2e`(A1로 넘김); 기록(`76(A6)`) BYTE `0` `1` `2` `3`, WORD `4`; 새 자식 node(A0) WORD `68` `1e` `76` `78` `7a` `7c` `7e` `80`, LONG `76` `c`, BYTE `76`(`5b3fa`); `28ae`/`288c`가 돌려준 A0 BYTE `80`; A5 BYTE `5d44` `5c8d`.
- [I] `59ea2`는 큰 상태기계(`59f1a..5a7c8`의 여러 상태가 `5a802`·`5a9c2`·`5ab5a`를 공유)의 초기 상태로 보인다. `5aa3a`가 animation(`183`, bank `200190`)·효과음·`28ae` 자식 `5b220`(기록 `76(A6)` 공유)을 만들고, `5b220`은 `76(A6)` 기록의 목표 방향(`4(A0)`)으로 `80(A6)`을 속도 `82(A6)`로 돌리며 `86(A6)` = 방향/8(반올림, 32단계)을 만든다. `7b`/`7a`는 자식 `5b4c6` 생성 간격이다. `d3580`은 부모를 따라가는 부속 객체이고 부모 `54`(체력으로 보임)의 1/2·1/4에서 상태 `d3614`/`d3646`, `61` bit 7에서 `d3678`로 바뀐다. `dbfac`는 `5c8d(A5)` = `ff` 표시 후 끝난다. 게임 의미는 미확인이다.

## 의존·경계

- [F] N13 → 기존(모두 routing됨): U12 `4c0ac`(`59ea2`)·`490ba`(`5aab6` `5aaca`), U04 `43ea4`(`59ee0` `5a7d2` `5a880` `5a9ae`)·`ce02`(`5ab5a`), sound `3af8`(`59ef4` `59f02` `5a7e6` `5a81e` `5aa7a`), area_clear `4b6ec`(`5a80c` `5a9a2`), cleanup `46ef4`·`8ff4`(`5a828`; `5a94a` `5aa3a`)·`43e04`(`5b220`)·`43e34`(`5b34e` `d3b1a`), interpreter `49f8c`(`5a838` `5a986` `5aa96` `5b280` `d35b2`)·`49fc6`(`5ab64` `5b496` `d35c2`; C 반환), U11 `496c2`(`5a854` `5a99c`), U09 `47070`(`5a9ca`), U01 `4b54e`(`5aa26`; C 반환), U14 `4a496`(`5aa6a`), fade_card `28ae`(`5a8f2` `5aaa6` `5ab3a` `5b3c0` `d3ae8`; C 반환)·`2a00`(`5b4c0` `dbfac` JMP), stage_event_ops `288c`(`5b2ae` `d3602`; C와 A0 반환), U02 `8ebe`(`5a95c` `5a96a` `5a978` `5aa4e` `5aa5c` `5b24e` `5b272`)·`443d2`(`5b3f4`), N05 `49214`(`5ab4a` `5b40e`), N04 `4a46c`(`5b472`; C 반환), U08 `49290`(`d3580`). 이 callee들은 대기(waiting)를 돌려줄 수 있다(기존 동작).
- [F] 실행부 없는 경계: `482fa`(`5a802`), `d3802`(6곳), `1a3ac`(`5a8dc`; 결정 6). 셋 다 다른 단위 몫이라 시험은 그 PC의 stop 성립만 확인한다(F4 시험 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N13: stage event 표(`59ea2`), `dbfc4` 표(`dbfac`), interpreter 명령 callback(`5ab16` `5ab1c` `5ab22` `5ab3a`), `28ae` dispatch(`5b220` `d3580`), 미연결 `59f1a..5a7c8` 상태들(`5a802` `5a9c2` `5ab5a`), 미연결 `56b52`(`d3ab8`), `d3a80`(`d3ae8`), `d364c`(`d3b1a`), `d3644`/`d3674`(`d35f2`).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 175 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), 소비자 6개의 Unknown C checked 오류(상태 보존), zero-step, 내부 846 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 경계 `482fa` `d3802` `1a3ac`와 다른 단위 callee는 stop만. `5b326`은 선행 `5b316`의 N과 같은 SR로 Unicorn fixture를 만든다. ADDX(`80(A6)` BYTE 전 범위의 bit 2 경계), DIVU(정상 몫, overflow, 제수 0 두 곳 checked 오류) fixture. bank LONG `200190`은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 실제 생산자(`28ae` `288c` `4a46c` `4b54e` `49fc6`)를 지나는 Unicorn fixture로 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(모든 진입, 실제 callee 생산 C를 거친 소비자 분기).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0, base complete +16 17 기대. RNG 초기화 400 frame 차분: 불일치 0, complete +16 17 기대.

## 작업자 검증 기록 (scratch)

- [F] 공유 수정(브리프 허용 범위): `animation_machine.cpp` routing `else if` 1개(N11 뒤, 8 범위)와 carry 보존 case 묶음 1개(`// BTST/BEQ changes only Z` 앞, 54개), `animation_machine_internal.h` 선언 1줄, `Makefile`(source 목록·test target·실행 줄, Codex 공용 object 구조 유지), `tools/verify_animation_machine.py` SOURCES. `animation_machine_interpreter.cpp`는 바꾸지 않았다.
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0(기존 test 모두 통과). 새 test: `animation machine objects n13: 504 fixtures (20 checked errors, 70 known C), 175 blocks, 2431 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen_n13.py`): 175 시작 모두 native fixture로 덮임. 소비자 6개 Unknown C 오류, 시작마다 3 carry 한 block 후계·carry 분류, zero-step, 내부 846 PC, 홀수 PC 16개, RAM rollback 탐침(`10fe50` `10fe60` `10fe70`, RTS 끝 12 fixture의 복귀 LONG `10fe80`), 경계·다른 단위 callee stop 27종(`482fa` `d3802` `1a3ac` 포함). 실제 producer를 따라간 행: `28ae`(`5a8f2` `5aada` `5b3c0` `d3ab8`; `2908` Set / `290e` Clear), `288c`(`5b2ae` `d3602`; `2898`/`28a8` Set, `289e` 같음 Clear), `4a46c`(`5b472`; `4a48a` Set / `4a490` Clear), `4b54e`(`5aa26`; `4b6be` Clear / `4b6de` Set). 소비자 6개 모두 C Clear·Set 양쪽에서 native 분기가 계약 carry와 같았다(30건). DIVU 0 제수 checked 오류 4건(`82(A6)` = 0, `7b(A6)` = `ff`, `5b428` 경로, `5b420`에서 `7b` = 0 → `ff`; 마지막은 Unicorn에서 vector 5 예외 `5b454`로 확인). 경계값: ADDX `80` BYTE 17개(`03`/`04`, `7b`/`7c`, `80`/`84`, `fb`/`fc`/`ff`), DIVU 11개(정상, 첫 DIVU overflow `10000`/`12345678`/`ffffffff`/`7fff0000`, 몫 0 → 1), SPL 6개(`D1.W` bit 15 양쪽), 방향 추적 14개(`8000` 차이의 `NOT.B`, 지나침 clamp), LONG/WORD 부호 비교(`59ee6` `5a7d8` `5a898` `d35d2`: `7fffffff`/`80000000`/`7fff`/`8000`). 돌연변이 10개 중 9개가 test에서 실패했다(ADDX X 누락, SPL N 반전, DIVU overflow 무시, 둘째 제수 +1 누락, BLE 무부호, BGT 무부호, `SUBQ.B`를 WORD로, `MOVEM` pop 순서, `ASR.L`을 `LSR.L`로). 살아남은 1개(`ASR.B` 부호 채움 누락)는 뒤 `ANDI.B #1f`가 위 3 bit를 지워 결과가 같은 동치 돌연변이다.
- [F] 실제 ROM 차분(`realrom/real_n13.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, seed 1·2·3 각 1,500건; native stop은 STOP, `2a00`, sprite 대기 `cd58`, 이 트리 routing 밖 PC(경계 `482fa` `d3802` `1a3ac` 포함), 실제 소비자 `59f4c` 분기 뒤): 불일치 0/0/0, carry 불일치 0(`5ab5a`/`5ab64`/`5ab6a` 진입의 복귀 LONG을 미연결 실제 소비자 `59f4c BCC.W`로 둔 native 분기 37/30/38건, C Clear·Set 양쪽), 비교된 사례만으로 175 시작 모두 도달(seed마다 175/175). native port 쓰기(2,846/2,878/2,688건)도 순서까지 같다. native DIVU 0 제수 예외(vector 5) 47/46/40건은 C++ `objects n13 DIVU zero divisor`와 일치(의도된 차이, `5b442` 77·`5b454` 56). native가 6,000,000 명령 안에 멈추지 않은 68/68/56건은 제외했다. harness는 기존 실행부 block 내부 PC(재범위 15개 + exit `3d50` + cleanup `46ef4`/`46f08` block 내부)를 routing된 것으로 본다.
- [F] 기준(`43a137f` 사본 `ms5-scratch/n13/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 13,208·node 108,064, 불일치 0, 자연 완주 121. N13 뒤: pass 13,448·node 110,160, 불일치 0, 자연 완주 123(+16 17), 회귀 0, 변화는 seed 16 17뿐(첫 미연결 `dbfac` → 완주).
- [F] RNG 초기화 400 frame 차분: 기준 일치 pass 44,800·node 332,425, complete 112. N13 뒤 pass 45,600·node 337,881, 불일치 0, `other` 없음, complete 114(+16 17), 회귀 0(seed별 기록 차이는 router SHA 필드뿐, 그 밖은 seed 16 17). 응답 `00` 변형 6 seed: complete 6 → 6, 불일치 0. 정적 재생 예측과 같다.
- [F] ROM SHA256·mtime 작업 전후 같음.

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] `59f1a..5a7c8`의 미연결 상태들(`59f1a` `59f38` … `5a376` `5a5ca`, 설치 `5a7c2`)과 범위 밖 설치 `d3614` `d3646` `d3678`, `28ae` 자식 `5ab6c` `5ab82` `5b4c6`은 이 단위 밖이다(재범위 "미실행 설치 8(+89)"). 400 frame 자연 기록에서 실행되지 않는다. 실행되면 다음 frame dispatch에서 `unsupported animation machine PC`가 된다.
3. [U] 경계 `1a3ac`(결정 6)의 귀속.
4. [U] DIVU 0 제수 예외(vector 5 처리기 `202`) 이후 원본 동작은 모형화하지 않는다(checked 오류).

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n13/`(`n13blocks.py` block·범위 계산, `cls13.py` 분류, `fmt13.py` 목록, `n13refs.py`/`n13raw.py` 참조, `n13reach.py` 자연 도달·기대 완주, `n13route.py` routing 확인, `gen/` fixture 생성, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스 차분, `mut/` 돌연변이; 저장소 밖).
