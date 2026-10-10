# `480bc` 프레임 helper 묶음 U7: buffer `4aa88`·cue `e8a48` 계약

**상태: 메인 리뷰를 거쳐 확정(아래 메인 결정). 구현·검증 기록이 아니다.** 메인이 원본과 대조해 리뷰한 뒤 확정한다. 범위 근거는 `animation-machine-480bc-scope.md`의 U7이다. 진입 경계는 확정된 U1 계약(`animation-machine-frame-helpers-u1-contract.md`)의 두 호출이다. `480cc` JSR `4aa88`은 복귀 LONG `480d2`, `480e4` JSR `e8a48`은 복귀 LONG `480ea`를 쓴다.

Claude Opus 5.5 / high 분석 작업자가 canonical BE ROM을 capstone M68000으로 디코드했다. ROM은 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB이며 fixed CPU 주소=file offset이다. banked window `200000+`는 bank `1000`이면 physical `200000`, `2000`이면 physical `300000`이다. 기존 관측 산출물은 읽기 전용으로 재생했다. U1~U6 실행부는 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `2f65d65`, WIP)의 `engine/src`를 읽기 전용으로 참조했다.

표기는 다음과 같다. [F]는 원본 바이트 또는 기록된 산출물에서 확인한 사실, [I]는 추론, [U]는 미확인이다. 명령 단위 정답은 원본 바이트 자체다.

같은 루틴의 typed host 재구성은 machine 실행부가 아니며 교차 확인 자료로만 쓴다. 해당 소스는 `engine/src/stage_buffer_frame*.cpp`, `stage_cue_*.cpp`, 문서는 `stage-buffer-frame.md`, `stage-cue-frame.md`, `sprite-submit-execution.md`다.

[I] U7은 `480bc` 묶음의 마지막 단위다. U1~U7을 모두 구현하면 `480bc`의 모든 JSR 대상에 실행부가 생긴다. 그러면 `480bc`→`480f0` RTS를 끝까지 실행할 수 있다(아래 "전체 `480bc` frame 통합"). 남는 정지점은 다음과 같다.
- 기존 실행부의 실제 대기: sprite `cda4`, sound `3aea` 등.
- checked 오류 경계: TRAP `4939c`/`4d7f0`, 계산 PC 범위 밖, `cd50`이 아닌 sprite callback, 미지원 쓰기 장치.

메인 결정(Claude Opus 5.5, 원본 대조 리뷰 후): (1) `2986`의 MOVE SR은 선택 A로 구현한다. push WORD는 system BYTE `20`과 CCR 이미지로 만들고, 실패 경로의 X는 복귀 LONG이 `e8a8a`인 `e8a48` 문맥에서만 계산한다(A5=`108000`, stack alias, pop WORD가 push 값과 같음을 guard). 그 밖의 호출자가 실패 경로에 오면 checked 오류다. 공용 machine 상태(X 추적)는 바꾸지 않으며, `2986`의 다른 호출 지점(전체 156곳)이 필요해지면 선택 B를 다시 검토한다. `298e`는 carry 보존·known carry 생산 block으로 둔다. (2) `e8ad0` stream walk는 종료 표식 없이 원본대로, 기존 block budget만 한계다(U5 결정 5 선례). (3) 디버그 경로(`10f001` bit7/0/1)는 모두 구현한다. (4) ROM 자료는 물리 `program_rom_000000.ms5d` window로만 읽는다(U6 결정 5 선례). (5) 대기·재개는 기존 `AnimationMachineWaiting`을 그대로 쓰고 새 metadata를 두지 않는다. (6) 새 실행부 파일은 `engine/src/animation_machine_buffer_cue.cpp`이며 routing 4 범위다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

### 1. `2986` MOVE SR 모델 (범위 문서 미확인 2, 가장 중요)

**원본 동작**
- [F] `2990` `MOVE SR,-(A7)`는 16-bit SR 전체(system byte + CCR)를 A7−2의 live stack에 쓴다. `2998` `MOVE (A7)+,SR`가 이를 다시 꺼낸다.
- [F] 쓰는 위치는 `2986`이 저장한 A6 LONG의 하위 WORD 위치다. `2986` 진입 A7을 S라 하면 `2986`은 S−4에 A6 LONG을 넣고, `298e`가 꺼낸 뒤 S−2에 SR WORD를 쓴다.
- [F] 이 WORD는 RTS 뒤 A7 아래에 stale bytes로 남는다. 이후 더 깊은 push가 덮지 않으면 frame 끝 RAM에 그대로 보인다.

**기록 증거**
- [F] stage_frame `active-cue-allocation`(verification.json results[42], `2986` 실패 경로) 기록 `stack_hex`의 STACK−16 WORD는 `2004`이다. STACK−18 WORD는 `0010`이고, 이는 저장된 A6 `00100820`의 상위 WORD다.
- [F] stage_frame은 stack을 64KiB RAM 밖의 별도 영역(`1feffc`)에 두었다. machine 관측기는 `1feffc`를 RAM mirror(`10effc`)로 쓴다. 따라서 machine 전체 RAM 비교에는 이 WORD(RAM offset `efec`)가 포함된다.

**WORD의 구성(정확한 유도)**
- [F] `2990` 시점 CCR은 `28ae` 종료 경로로 정해진다. 아래 표의 "D0.W"는 `298e` 시점 값이다. `28ae`와 `2986`은 실패 경로에서 D0을 바꾸지 않는다. 성공 경로에서는 `28e6` ADDQ 결과가 그대로 남는다.
- [F] 각 경로에서 해당 값이 마지막으로 쓰인 뒤 `2990`까지 RAM 쓰기가 없다. 성공 경로의 마지막 쓰기는 `2902`, 실패 경로는 쓰기 자체가 없다. stack push는 아래 대안 A의 별칭 검사로 따로 다룬다.

| `28ae` 종료 | C | V | Z/N | X |
| --- | --- | --- | --- | --- |
| 성공(`2908` ORI #1) | 1 | 0(`2902` MOVE.B) | `2902`가 쓴 BYTE = BYTE 6a(A0)의 값 | `28e6` ADDQ.W #1 carry = (D0.W==0) |
| 실패, `28ba` BCC(D0.W ≥ WORD `104ca0` 무부호) | 0 | CMP.W D0.W−M 결과(M=live WORD `104ca0`) | 같은 CMP 결과 | `2986` 진입 시점의 X(호출자 값) |
| 실패, `28c2` BEQ(입력 A0=0, D0.W < M) | 0 | 0 | Z=1, N=0 | `2986` 진입 시점의 X |

- [F] system byte(T/S/I2..I0)는 실행 문맥의 값이다. machine 관측기는 모두 SR=`2000`으로 시작한다. ROM은 `92c`·`974`·`1200`에서 `MOVE #$2000,SR`로 주 루프 SR을 둔다(fixed 1 MiB raw 검색; `46fc2000`). [U] 실제 게임이 `480bc` 실행 중 IPL을 무엇으로 두는지는 확인하지 않았다.
- [F] fixed 1 MiB에서 `40e7`(MOVE SR,-(A7))은 `2990` 하나, `46df`(MOVE (A7)+,SR)는 `2998` 하나뿐이다(raw 짝수 offset 검색).

**호출자 X(실패 경로)**
- [F] `e8a48` 문맥에서 실패 경로 X는 `e8af4`의 마지막 ADD.W carry다. flags BYTE 4(cue)의 bit0이면 `WORD 2(cue)+WORD 10d3c0`의 carry이고, bit0이 없고 bit1이면 `WORD (cue)+WORD 10d3bc`의 carry다. 둘 다 없으면 0이다.
- [F] 근거: `e8a5e` SUBI.W의 borrow는 할당 경로에서 항상 0이다. BYTE 7(cue)가 `1c` 미만이면 D0.B ≥ `e4`가 되어 `e8a66` BCC로 할당을 건너뛴다. 그 뒤 `2986` 진입까지는 MOVE/MOVEA/BTST/조건분기/BSR/JSR/RTS뿐이라 X를 바꾸지 않는다.

**scratch 확인**
- [F] scratch `u7/srprobe.py`는 Unicorn M68000 합성 조건 288개를 원본 `e8a48`부터 끝까지 실행했다. 조건은 성공/실패, 부모 +10 WORD `0`·`7fff`·`ffff`, BYTE 6a `0`·`1`·`80`, cue flags 0..3, 덧셈 carry 유무다.
- [F] stack RAM에 남은 WORD를 위 표와 시작 SR `2000`으로 만든 예측값과 비교해 불일치 0이었다. SR을 `2700`으로 시작하면 WORD 상위 BYTE가 `27`이 된다.
- 이 probe는 분석용이다. hook에서 SR을 읽은 것은 scratch 교차 확인에만 썼고, 검증 방법으로 제안하지 않는다.

**machine 상태와 선택지**
- [F] machine 상태에는 C만 있다(`AnimationCarryState`). X/N/Z/V와 system byte는 없다.
- [F] 실패 경로의 X는 `28ae` 실행부(fade_card, 다른 단위)를 건너 전달되어야 한다.
- [F] `2986` 호출 위치는 8 MiB raw 검색에서 156곳이다. `480bc` closure 안에서는 `e8a84` 하나뿐이다.

- **선택 A(작업자 권고, U7 한정 정확 모델)**: `298e` block 하나에서 다음 순서로 처리한다.
  1. A6를 pop한다.
  2. 이미지 W를 계산한다. 상위 BYTE는 선언 상수 `20`이다. 하위 BYTE는 위 표대로 계산하며, C는 machine carry로서 known이어야 한다.
  3. W를 A7−2에 WORD로 쓴다.
  4. BYTE 6a(A6)→6a(A0)를 복사한다.
  5. WORD를 live pop하고, machine carry를 그 WORD의 bit0으로 둔다.
  6. RTS한다.

  세부 규칙은 다음과 같다.
  - 실패 경로 X는 live stack의 복귀 LONG이 `e8a8a`일 때만 위 `e8a48` 문맥 규칙으로 계산한다. live 재읽기 대상은 LONG `10de26`, cue +0/+2/+4, WORD `10d3bc`/`10d3c0`이다. 재읽기 주소가 `e8af4` 이후 쓰인 stack 범위 [S−8, S+8)와 겹치면 checked 오류다. 복귀 LONG이 `e8a8a`가 아니면 checked 오류이며, 제안 문자열은 `cue wrapper failure requires known caller X`다.
  - A5-상대 주소 일치를 보장하도록 `e8a48` 진입 block에서 A5=`108000`을 요구한다(아니면 checked 오류). [I] `28ae`가 A5를 `108000`으로 덮으므로 `298e`에서는 원래 A5를 알 수 없다.
  - pop한 WORD가 push한 W와 다르면 checked 오류다. 이는 `2992` 쓰기가 stack WORD와 겹친 경우이며, S/IPL 변화는 machine이 표현하지 않는다.
  - 성공 경로는 호출자와 무관하게 정확하다.
  - 근거: 공용 상태를 바꾸지 않는다(U6 메인 결정 4가 Z 추가를 거절한 선례). closure 안 유일 호출자를 정확히 처리한다.
  - 비용: 호출자 특정 규칙이 생긴다. 다른 `2986` 호출자를 machine에 넣을 때 실패 경로를 다시 결정해야 한다.
- **선택 B(일반 모델)**: machine 상태에 X known/Unknown 분류를 추가한다. carry와 같은 방식이며, X 보존 PC 목록과 생산 block(`e8a50` SUBI, `e8b04`/`e8b12` ADD, `28e6` ADDQ)을 둔다. `298e` 실패 경로는 known X를 요구한다. fade_card의 `28ae`/`28b4`/`28be`/`290e`/`2916`이 X 보존 목록에 들어가야 한다. 156개 호출자로 일반화되지만, 공용 상태 구조와 모든 기존 회귀의 상태 비교가 바뀐다.
- **선택 C(비권고)**: 실패 경로 X를 0으로 선언하고 차이를 문서화한다. 원본과 다를 수 있으므로 전체 RAM 비교 원칙에 어긋난다.
- **선택 D(비권고)**: `298e`의 실패 경로를 모두 checked 오류로 둔다. stage_frame `active-cue-allocation` frame(실패, 이미지 `2004`)이 통합 비교에서 빠진다.
- 공통 하위 결정:
  - system byte 상수 `20`을 machine 선언 규약으로 둘지, fixture 선언 값으로 받을지 정한다. 작업자는 상수 `20`을 권고한다(모든 관측기와 ROM 주 루프 근거).
  - `298e`를 `carry_preserving_pc` 목록에 넣는다. 이 block은 known C 소비자이며 C 복원자다.

### 2. `e8ad0` stream 진행의 무한 가능성

- [F] `e8adc`는 D0.W=WORD `10d418`을 한 번만 읽는다. 그 뒤 `e8ae0`이 `CMP.W 12(A0),D0; BCS e8aee` 아니면 `ADDA.W #12,A0; BRA e8ae0`를 반복한다. 종료 표식이나 횟수 제한이 없다.
- [F] 기본 stream `e89ec`의 다음 gate는 `ffff`(`e89f8`)다. D0.W=`ffff`이면 코드 바이트를 gate로 읽으며 계속 진행한다.
- 선택 A(**작업자 권고**): 원본 그대로 둔다. 읽기 오류나 기존 machine block 상한(1,000,000)에서 checked 오류와 전체 rollback이 일어난다. U5 메인 결정 5(`1a514`)와 같다.
- 선택 B: 전용 guard(예: A0가 fixed ROM 창을 벗어나면 오류). 원본에 없는 판정을 추가하므로 비권고다.

### 3. 디버그 경로 구현 여부 (범위 문서 미확인 8)

- [F] U7 디버그 경로는 세 가지다.
  - `10f001` bit7: `4aa88` 16-slot loop와 `4b784` 두 sprite 제출. 대기할 수 있다.
  - `10f001` bit0: `4ab5a`/`4ab6e`, BYTE `10db84`=`ff`.
  - `10f001` bit1: `e8b18` 디버그 cue sprite, D7=`ba2b`, `cd58` 대기 가능.
- [F] stage_frame fixture가 bit7과 bit1 경로를 실행한다. typed 관측(`stage_buffer_frame`)은 bit0 경로 양쪽을 실행했다.
- 선택 A(**작업자 권고**): 모두 구현한다. 선택 B: guard(checked 오류). 이 경우 stage_frame의 buffer·cue·cue-debug-status 14 행(43~56)이 통합 비교에서 빠진다.

### 4. ROM 자료 창

- 선택 A(**작업자 권고**): physical `extracted/runtime/program_rom/program_rom_000000.ms5d`로만 읽는다. U6 메인 결정 5와 같다. 대상은 다음과 같다.
  - `e8a0c+4×index`(index 0..`1f`, `e8a0c..e8a8c`)
  - cue/stream 자료(`e89e4`, `e89ec`, catalog cue)
- [F] 기존 kind1 창(`extracted/runtime/stage_cue_control/default_cue.ms5d`·`default_stream.ms5d`, `stage_cue_frame`의 lookup 128B와 cue 42개)은 host API 전용으로 둔다. 작업 트리 `program_bus.cpp`는 kind1과 physical이 겹치면 `partial or ambiguous legacy/physical program bus ROM unit`으로 실패한다.

### 5. 대기·재개 규약 확인

- 선택 A(**작업자 권고**): 새 metadata 없이 기존 `AnimationMachineWaiting`을 그대로 쓴다.
  - 대기 시 상태(PC=`cda4`, 16 register, carry Unknown)와 RAM(live stack 포함)을 commit한다.
  - 재개는 같은 stop PC로 다시 호출한다.
  - typed API의 `buffer_phase`/`saved_*`는 재현하지 않는다. live stack이 그 상태다.
  - host가 대기 사이에 stack 영역을 바꾸면 원본 의미대로 live로 읽힌다(별도 보호 없음).
- 선택 B: 대기 phase를 machine 상태에 명시한다. 정보 중복이므로 비권고다.

### 6. 실행부 파일·라우팅

- [I] 새 실행부 파일은 `engine/src/animation_machine_buffer_cue.cpp`(함수 `animation_buffer_cue_block`)로 제안한다.
- [I] 라우팅 범위는 `4aa88..4abc0`, `4b784..4b82e`, `e8a48..e8b5a`, `2986..299c`(모두 `<`)다.
- [F] 작업 트리 라우팅과 겹치지 않는다. 가장 가까운 기존 범위는 다음과 같다.
  - fade_card `28ae..2916`
  - cleanup `299c..29fe`(시작 `>=299c`), `4aa06`/`4aa2e` 단일
  - interpreter `49f8c..4a46c`
  - script_placement `e89fa..e8a0c`
- [I] `e8a0c..e8a48`(자료와 closure 밖 `e8a1c`/`e8a3a`)와 `e8b5a..`는 라우팅하지 않는다.

## 원본 바이트 근거

[F] 아래 코드 범위는 합계 778바이트(219 명령, 미해독 0, 범위 안 빈틈 없음)이며 위 ROM에서 직접 추출했다(scratch `u7/leaders7.py`). 네 범위를 이어 붙인 SHA256은 `aa13f52b624d8da72825a6afb522510763c1bacaf6c75cb448cc523e8653c574`이다.

| CPU 범위 | 바이트 수 | SHA256 | 원본 바이트 |
| --- | --- | --- | --- |
| `4aa88..4abc0` | 312 | `81819232ea21f024…3f31bd83` | `083900070010f0016700006c2f0e49f90010daf87e002c54206c0004bcfc000067000044b0fc00006700003c1c2e006d0206000fbe066600002e2f0c3f0741e800042e3c0000122b4eba0cb23e1f285f3b7c0000801033fc1000002ffff233fc0000002ffff0524749ec0008b9fc0010db7865a22c5f7e00206d5c88e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8e2d8b1fc0010dc886500000641ed5b882b485c881b6d5b855b841b7c00005b851b6d5b875b861b7c00005b87083900000010f0016700001c103900104cab803900104cb102000080670000081b7c00ff5b8449ed574647ed5918086d0007574466000004c74c72ff426c01d0700072007400760078007a007c007e0049ec00d048e4ff0048e4ff0048e4ff0048e4ff0048e4ff0048e4ff0048e4f0004e75` |
| `4b784..4b82e` | 170 | `a55b440d6d7fcc5b…5f2fdc3e5d3389d2` | `223cffff0000082e0002001567000006323c00042018082e000000156700000c48404440484008c10000082e0001001567000008444008c100014840d06e00424840d06e00462f002f012f072f087aff4eb90000cd58205f2e1f221f201f341836180a410003082e00000015670000044442082e000100156700000444434840d0424840d0432f087aff4eb90000cd58205f3b7c0000801033fc1000002ffff233fc0000002ffff04e75` |
| `e8a48..e8b5a` | 274 | `8d885f6646762efa…325075fe` | `4a2d5e2f67000060422d5e2f206d5e267000102800070440001c0c000020640000463f00610000863f003f01207c000d5f16303c0000227c00100bf44eb90000298641e8002e43ed538e321f301f4eb900043e0841e80048301f43faff68e548d2c030d930d94a2d5e2e6600000e6100001843e800042b495e26083900010010f0016600004c4e75206d5e2ab0fc000067000018302d5418b068000c65000008d0fc000c60f22b485e2a4e7530103228000208280001000467000006d06d53bc08280000000467000006d26d53c04e7543f90010d38e206d5e26b0fc0000670000304ebaffc8d06d53a2d26d53a64840300172ff42410c4001e06500000608c100017aff2e3c0000ba2b4eb90000cd584e75` |
| `2986..299c` | 22 | `307b823886017a67…bdfec928c` | `2f0e2c496100ff222c5f40e7116e006a006a46df4e75` |

[F] U7이 부르는 기존 실행부 범위의 원본 SHA256(참고용, 바꾸지 않음):
- `28ae..2918` 106B `b00433a1c0ee3681572790b56a8ba968070bfa38bdc8aec80d83f00462a49610`
- `43e08..43ea4` 156B `de928a386ddf00b206611b5f44709f226fdf07394442b5a1419ec69dd54e8383`
- `cd50..ce02` 178B `253423692793c9dd104dc72a09d7d4f480251fa98872f89fd30827a440bdff1c`

[F] 자료 창 바이트(아래 "필요한 ROM·MS5D 자료 창"):
- `e8a0c..e8a8c` 128B, SHA256 `73399f8741816b3d759beb32ab5e344ed724806c60215a9f86e92f01169105ae`. 앞 16B는 `00000002000000010001000100020001`이다.
- `e89e4..e89ec` `0000000003000000`
- `e89ec..e89fa` `00000000006001000308000bffff`

## 실행 의미(A5=`108000` 기준 절대 주소)

[F] 모든 `d16(A5)` 접근은 live A5로 계산한다(U2~U6과 같음). A5=`108000`일 때 주소는 다음과 같다.
- buffer 쪽: `5c88`→`10dc88`, `5b88`→`10db88`, `5b84..5b87`→`10db84..10db87`, `5744`→`10d744`, `5746`→`10d746`, `5918`→`10d918`, `−7ff0`→`100010`
- cue 쪽: `5e26`→`10de26`, `5e2a`→`10de2a`, `5e2e`/`5e2f`→`10de2e`/`10de2f`, `538e`→`10d38e`, `5418`→`10d418`, `53bc`/`53c0`→`10d3bc`/`10d3c0`, `53a2`/`53a6`→`10d3a2`/`10d3a6`
- `cd58`: `1152`→`109152`

[F] 절대 주소 접근은 BYTE `10f001`, `104cab`, `104cb1`, LEA `10d38e`(`e8b18`), PVC `2ffff2`/`2ffff0`뿐이다.

[F] 공통 폭 규칙은 U2~U6과 같다.
- MOVE.W/ADD.W/NEG.W/EORI.W/SUBI.W/LSL.W의 Dn 목적지는 하위 WORD만, MOVE.B/OR.B/ANDI.B는 하위 BYTE만 바꾼다.
- MOVEQ·MOVE.L은 LONG 전체를 바꾼다. SWAP은 두 WORD를 교환한다. CLR.W는 하위 WORD만 지운다.
- CMPA.W #0은 부호확장 0과 An LONG 전체를 비교한다. CMPA.L은 무부호 LONG 비교(BCS)다. ADDA.W는 부호확장이다.
- BSET/BTST의 Dn 피연산자 bit 번호는 mod 32, 메모리 피연산자는 mod 8이다.

### `4aa88` 프레임 buffer

1. [F] `4aa88`: BTST.B #7,BYTE `10f001`(절대)이 0이면 `4aafe`로 간다.
2. [F] 디버그 slot loop(`4aa94..4aafc`):
   - `4aa94`: MOVE.L A6,-(A7)로 바깥 A6을 live stack에 둔다. A4=`10daf8`, MOVEQ #0,D7.
   - `4aa9e`: A6=LONG (A4), A0=LONG 4(A4). A6=0이면 `4aaee`로 간다.
   - `4aaac`: A0=0이면 `4aaee`로 간다.
   - `4aab4`: D6.B=BYTE 6d(A6) AND `0f`. CMP.B D6,D7이 다르면 `4aaee`로 간다.
   - `4aac2`: push LONG A4, push WORD D7, A0+=4(LEA), D7=`0000122b`(MOVE.L), JSR `4b784`(PC 상대, 복귀 `4aad4`).
   - `4aad4`: D7.W=pop WORD(하위 WORD만 복원, 상위 WORD는 `cd58`이 바꾼 값이 남을 수 있음), A4=pop LONG. 그다음 `am_zero_bank`와 같은 세 쓰기를 한다: WORD 0→A5−`7ff0`, WORD `1000`→`2ffff2`, WORD 0→`2ffff0`.
   - `4aaee`: ADDQ.W #1,D7, A4+=8. CMPA.L #`10db78`,A4가 무부호로 작으면(BCS) `4aa9e`로 간다(16 slot, index 0..15).
   - `4aafc`: A6=pop LONG(바깥 A6 복원)한 뒤 `4aafe`로 fall-through한다.
   - [I] slot 객체 A6은 `4b784`·`cd58` 동안 register로만 유지된다(`cd58`은 A6/A4를 바꾸지 않음). 바깥 A6·slot A4·slot D7.W는 live stack에 있다.
3. [F] 정상 경로 `4aafe`:
   - MOVEQ #0,D7. A0=LONG `10dc88`(ring cursor).
   - LSR.W (A0)+를 16회 한다. 각각 WORD 읽기, 논리 >>1, 같은 주소 WORD 쓰기, A0+=2 순서다. X/C=밀려난 bit0.
   - CMPA.L #`10dc88`,A0가 무부호로 작지 않으면 `4ab2e`에서 A0=`10db88`(LEA)로 되돌린다.
   - `4ab32`: LONG A0→`10dc88`.
   - [F] 순차 실행이 정답이다. cursor가 `10dc6a..10dc86`이면 LSR이 cursor LONG 자신(`10dc88..10dc8b`)을 먼저 바꾸고, 그 뒤 MOVE.L이 덮는다.
   - 홀수 cursor는 기존 홀수 접근 오류, RAM이 아닌 cursor는 기존 `unsupported animation machine write device`(checked 오류, 전체 rollback)다.
4. [F] `4ab36..4ab4c`: BYTE `10db85`→`10db84`, BYTE 0→`10db85`, BYTE `10db87`→`10db86`, BYTE 0→`10db87`.
5. [F] BTST.B #0,BYTE `10f001`가 0이면 `4ab74`로 간다.
   - `4ab5a`: D0.B=BYTE `104cab`, OR.B BYTE `104cb1`, ANDI.B #`80`. 0이면 `4ab74`로 간다.
   - `4ab6e`: BYTE `ff`→`10db84`.
6. [F] `4ab74`: A4=`10d746`, A3=`10d918`(LEA). BCHG.B #7,BYTE `10d744`: Z=(이전 bit7==0). BNE `4ab88`.
   - 이전 bit7이 0이면 `4ab86` EXG A3,A4가 실행되어 A4=`10d918`, A3=`10d746`이 된다.
7. [F] `4ab88`:
   - MOVEQ #−1,D1(곧 덮임), CLR.W `1d0`(A4), D0..D7 각 MOVEQ #0, A4+=`d0`(LEA).
   - MOVEM.L D0-D7,-(A4)를 6회, MOVEM.L D0-D3,-(A4)를 1회 해서 [A4, A4+`d0`)의 208바이트를 위에서 아래로 0으로 쓴다. RTS.
   - 결과: D0..D7=0, A4=선택된 buffer 시작, A3=다른 buffer 시작, A0=새 cursor, A6=바깥 A6. A1/A2는 slot 경로의 `cd58` 결과가 남는다(clip이 아니면 A1=`108b34`).
   - [I] 쓰는 값이 모두 0이므로 RAM 결과는 쓰기 순서와 무관하다. 순서 있는 RAM 쓰기 기록이 필요하면 원본 관측 순서를 따른다.

### `4b784` 두 sprite 제출(slot 객체 A6, A0=record+4, D7=`122b`)

8. [F] `4b784`: D1=`ffff0000`. BTST.B #2,BYTE 15(A6)이면 `4b794`에서 MOVE.W #4,D1(D1=`ffff0004`)한다.
   - `4b798`: D0=LONG (A0)+.
   - bit0이면 `4b7a4`: SWAP D0, NEG.W D0, SWAP D0, BSET #0,D1.
   - `4b7ae`: bit1이면 `4b7b8`: NEG.W D0, BSET #1,D1.
   - `4b7be`: SWAP D0, ADD.W WORD 42(A6),D0, SWAP D0, ADD.W WORD 46(A6),D0. push LONG D0, D1, D7, A0 순서. MOVEQ #−1,D5. JSR `cd58`(복귀 `4b7da`).
9. [F] `4b7da`: A0, D7, D1, D0를 pop한다. D2.W=WORD (A0)+, D3.W=WORD (A0)+(**재개 뒤 live 읽기**). EORI.W #3,D1.
   - bit0이면 `4b7f4` NEG.W D2. `4b7f6`: bit1이면 `4b800` NEG.W D3.
   - `4b802`: SWAP D0, ADD.W D2,D0, SWAP D0, ADD.W D3,D0. push LONG A0. MOVEQ #−1,D5. JSR `cd58`(복귀 `4b814`).
   - [F] D1 bit6은 이 경로에서 항상 0이다(D1 하위 BYTE는 0..7). 따라서 `cdb2`는 normal 쪽만 간다.
10. [F] `4b814`: A0=pop. bank 초기화 세 쓰기(위와 같음). RTS(`4aad4`로).

### `e8a48` cue

11. [F] `e8a48`: TST.B BYTE `10de2f`가 0이면 `e8aae`로 간다.
12. [F] `e8a50`: CLR.B `10de2f`(BYTE 쓰기 1회).
    - A0=LONG `10de26`(cue). MOVEQ #0,D0. D0.B=BYTE 7(A0). SUBI.W #`1c`,D0.
    - CMPI.B #`20`,D0가 무부호 ≥이면 `e8aae`로 간다. 할당 경로의 index는 0..`1f`이고, 이때 SUBI borrow는 0이다.
13. [F] `e8a6a`: push WORD D0(index). BSR `e8af4`(복귀 `e8a70`).
    - `e8af4`: D0.W=WORD (A0), D1.W=WORD 2(A0).
    - BTST #1,BYTE 4(A0)이면 `e8b04` ADD.W WORD `10d3bc`,D0.
    - `e8b08`: BTST #0이면 `e8b12` ADD.W WORD `10d3c0`,D1.
    - `e8b16` RTS. 상위 WORD와 다른 register는 보존된다.
14. [F] `e8a70`: push WORD D0(X), push WORD D1(Y). A0=`d5f16`(MOVEA.L, callback 주소로만 쓰임). MOVE.W #0,D0. A1=`100bf4`. JSR `2986`(복귀 `e8a8a`).
15. [F] `2986`: push LONG A6. A6=A1. BSR `28ae`(fade_card 기존 실행부, 복귀 `298e`).
    - 성공하면 A0=새 객체, C=1이다. 실패하면 A0=A5−`7168`=`100e98`, C=0이다.
    - `28ae`는 A5=`108000`을 둔다.
16. [F] `298e`(한 block): A6=pop LONG(원래 A6).
    - `2990` MOVE SR,-(A7): 결정 1의 WORD를 A7−2에 쓴다.
    - `2992` MOVE.B BYTE 6a(A6)→6a(A0)(live, 실패 시에도 실행, 실패 목적지 `100f02`).
    - `2998` MOVE (A7)+,SR: WORD live pop, CCR 복원(C=`28ae`의 C).
    - `299a` RTS.
17. [F] `e8a8a`: A0+=`2e`, A1=`10d38e`(LEA). D1.W=pop WORD, D0.W=pop WORD(하위 WORD만). JSR `43e08`(cleanup 기존 case, 복귀 `e8a9c`; `43e38`로 이어짐, A0 보존, A5=`108000`).
18. [F] `e8a9c`: A0+=`48`(=객체+`76`). D0.W=pop WORD(index). A1=`e8a0c`(LEA PC). LSL.W #2,D0. ADDA.W D0,A1(부호확장, 값 0..`7c`). MOVE.W (A1)+,(A0)+를 두 번 한 뒤 `e8aae`로 간다.
    - [F] 실패 경로에서는 위 쓰기가 모두 fallback 객체 `100e98`에 간다: `100f02`, `100ec6..100eeb`, `100f0e`/`100f10`. 기록 stage_frame results[42]의 RAM_writes와 일치한다.
19. [F] `e8aae`: TST.B BYTE `10de2e`가 0이 아니면 `e8ac2`로 간다.
    - `e8ab6`: BSR `e8ad0`(복귀 `e8aba`).
    - `e8aba`: A1=A0+4(LEA). LONG A1→`10de26`.
    - [F] `e8ad0`이 null A0를 반환해도 우회가 없다. 그 경우 `10de26`=`00000004`가 된다.
20. [F] `e8ad0`: A0=LONG `10de2a`. 0이면 `e8af2` RTS(D0 불변).
    - `e8adc`: D0.W=WORD `10d418`(1회).
    - `e8ae0`: CMP.W WORD 12(A0),D0가 무부호로 작으면(BCS) `e8aee`로 간다. 아니면 `e8ae8`에서 A0+=12(ADDA.W), BRA `e8ae0`(결정 2).
    - `e8aee`: LONG A0→`10de2a`. `e8af2` RTS.
21. [F] `e8ac2`: BTST.B #1,BYTE `10f001`(절대)이 0이 아니면 `e8b18`로 간다. 0이면 `e8ace` RTS(`480ea`로).
22. [F] 디버그 `e8b18`: A1=`10d38e`. A0=LONG `10de26`. 0이면 `e8b58` RTS로 간다.
    - `e8b2a`: JSR `e8af4`(복귀 `e8b2e`).
    - `e8b2e`: ADD.W WORD `10d3a2`,D0. ADD.W WORD `10d3a6`,D1. SWAP D0. MOVE.W D1,D0(D0=X:Y). MOVEQ #−1,D1. CLR.W D1. CMPI.W #`1e0`,D0가 무부호 ≥이면 `e8b46` BSET #1,D1.
    - `e8b4a`: MOVEQ #−1,D5. D7=`0000ba2b`. JSR `cd58`(복귀 `e8b58`).
    - `e8b58`: RTS.

### 공통

[F] U7 자체 쓰기는 다음뿐이다.
- RAM
- PVC: bank 초기화 1회당 `2ffff2`·`2ffff0` WORD 2개. slot 1개 호출이 완료되면 `4b816`과 `4aad8`에서 2회씩, 합계 4개다.
- `2990` stack WORD

[F] `cd58`(sprite), `28ae`(fade_card), `43e38`(cleanup)의 쓰기는 기존 실행부 소관이다. 읽기는 접근 시점의 live bus(현재 bank)이며, 홀수 WORD/LONG 접근은 기존 checked 오류와 전체 rollback이다.

[F] Stack 깊이는 `480bc` 진입 A7=U 기준이다.
- slot 경로 최대 U−42: `480d2` 4, 바깥 A6 4, A4 4, D7.W 2, `4aad4` 4, D0/D1/D7/A0 16, `4b7da` 4, `cd58`의 callback JSR 4.
- 할당 경로 최대 U−26: `28ae` 성공 경로 push A0까지.
- 디버그 cue 경로 최대 U−12.

## 구현 범위와 규약

- [F] U7이 부르는 기존 실행부는 그대로 쓰고 바꾸지 않는다. 작업 트리 소스에서 각 진입 case가 있음을 확인했다.
  - `cd58`(sprite, `animation_machine_sprite.cpp` 35행; callback LONG `109152`가 `cd50`이 아니면 `unsupported sprite callback target`, 대기는 `cda4` 55행)
  - `28ae`(fade_card, `animation_machine_fade_card.cpp` 55행; 2908/290e가 known C를 두고 `290c`/`2916` RTS가 보존 목록에 있음)
  - `43e08`(cleanup, `animation_machine_cleanup.cpp` 189행, U5 메인 결정 2)
- **Block 시작 PC (60개)**: 루틴 진입, 분기 대상, 조건분기 fall-through, 호출 복귀, 호출 진입을 모두 넣는다. 목록 밖 PC 직접 진입은 거부한다. scratch `u7/leaders7.py`가 원본 opcode에서 계산했다(U2 `19c7e`·U6 `49dd4` 같은 접기 예외 없음).
  - `4aa88` 묶음 17: `4aa88` `4aa94` `4aa9e` `4aaac` `4aab4` `4aac2` `4aad4` `4aaee` `4aafc` `4aafe` `4ab2e` `4ab32` `4ab5a` `4ab6e` `4ab74` `4ab86` `4ab88`
  - `4b784` 13: `4b784` `4b794` `4b798` `4b7a4` `4b7ae` `4b7b8` `4b7be` `4b7da` `4b7f4` `4b7f6` `4b800` `4b802` `4b814`
  - `e8a48` 묶음 28: `e8a48` `e8a50` `e8a6a` `e8a70` `e8a8a` `e8a9c` `e8aae` `e8ab6` `e8aba` `e8ac2` `e8ace` `e8ad0` `e8adc` `e8ae0` `e8ae8` `e8aee` `e8af2` `e8af4` `e8b04` `e8b08` `e8b12` `e8b16` `e8b18` `e8b2a` `e8b2e` `e8b46` `e8b4a` `e8b58`
  - `2986` 2: `2986` `298e`
- **묶인 분기 PC (24개, 직접 진입 거부)**: 모두 같은 block 안 생산자(BTST/BCHG/CMP/CMPA/CMPI/TST/ANDI/SUBI)의 flag를 소비한다.
  - `4aa90` `4aaa8` `4aab0` `4aabe` `4aafa` `4ab2a` `4ab56` `4ab6a` `4ab82` `4b790` `4b7a0` `4b7b4` `4b7f0` `4b7fc` `e8a4c` `e8a66` `e8ab2` `e8aca` `e8ad8` `e8ae4` `e8b00` `e8b0e` `e8b26` `e8b42`
  - 그 밖의 내부 PC도 거부한다. JSR이 있는 `4b7d4`·`4b80e`·`e8b52`·`e8a84`, `e8aec` BRA 등이 여기에 해당한다.
- **Carry 소비 block (1개)**: `298e`. C로 이미지 bit0을 만든다. 진입 C가 Unknown이면 checked 오류와 전체 rollback이다(제안 문자열 `cue wrapper requires known carry`). 그 밖의 U7 조건분기는 모두 block 안에서 flag를 만들고 소비한다.
- **Known carry 생산 block (1개)**: `298e`(MOVE (A7)+,SR로 C를 복원; 값은 pop한 WORD의 bit0, 결정 1). [F] U7 routine이 반환하는 C를 소비하는 호출자는 없다(`480d2` JSR, `480ea` JSR, `e8a8a` LEA, `e8a70` MOVE.W, `e8b2e` ADD.W, `e8aba` LEA).
- **Carry 보존(FLOW_ONLY) block (15개)**: 기존 규약대로 전 명령이 LEA/MOVEA/PEA/JSR/JMP/BSR/BRA/RTS/MOVEM/NOP/BTST/BSET/BCLR/BCHG/조건분기인 block이다.
  - `4aa88` `4aafc` `4ab2e` `4ab74` `4b7ae` `4b7f6` `e8ab6` `e8ac2` `e8ace` `e8af2` `e8b08` `e8b16` `e8b2a` `e8b46` `e8b58`
  - [I] `298e`는 소비·복원 block으로서 `carry_preserving_pc` 목록에 별도로 넣는다. 그래야 `290c`/`2916`에서 넘어온 known C가 block 실행 전에 Unknown으로 바뀌지 않는다(U1 `4765c` 선례).
  - EXG block `4ab86`과 ADDA block `e8ae8`은 기존 규약대로 Unknown이다. 그 밖도 Unknown이다.
- **경계·stop**:
  - [F] U7은 새 경계를 만들지 않는다.
  - U7 구현 후 U1의 `4aa88`·`e8a48` 경계는 일반 block 시작이 된다.
  - stop을 도달하는 block 시작 PC로 주면 그 PC 실행 직전 상태로 멈춘다.
  - U7 단독 검증 stop은 `480d2`(`4aa88`) 또는 `480ea`(`e8a48`)다. 둘 다 U1 block 시작이며, RTS 직후 상태(A7+4)로 멈춘다.
  - 도달하지 않는 stop은 실행부 없는 PC에서 `unsupported animation machine PC`와 전체 rollback이다(U1~U6과 같음).
- **`cd58` 대기(결정 5)**: 기존 sprite 실행부가 `cd5e`/`cda4`에서 `c.waiting=true`로 멈추고 `AnimationMachineWaiting`을 반환한다. 상태는 PC=`cda4`, D4=캡처한 WORD, carry Unknown이다.
  - 재개는 같은 stop으로 다시 호출하는 것이다. `cda4`는 live WORD `108d34`만 다시 읽는다. callback·clip·D6/D4 산출은 다시 실행하지 않는다.
  - [F] 대기 시 A7과 live stack 내용(`480bc` 진입 A7=U 기준)은 다음과 같다. stage_frame 기록 `final_a7`와 `stack_hex`가 같은 위치를 보인다.
    - 첫 sprite(`4b7d4`): A7=U−38. U−4 `480d2`, U−8 바깥 A6, U−12 slot A4, U−14 slot D7.W, U−18 `4aad4`, U−22 D0, U−26 D1, U−30 D7, U−34 A0, U−38 `4b7da`. register A6=slot 객체.
    - 둘째 sprite(`4b80e`): A7=U−26. U−22 A0, U−26 `4b814`, 그 위는 같다.
    - 디버그 cue(`e8b52`): A7=U−8. U−4 `480ea`, U−8 `e8b58`.
  - 재개 뒤 `4b7da`는 pop한 A0로 크기 WORD를 live로 읽는다. 첫 대기 동안 host가 record를 바꾸면 원본처럼 바뀐 값을 읽는다.
  - 둘째 `cd58`은 callback LONG `109152`를 다시 읽는다. stage_frame `buffer-first-release`가 이를 위해 `cd50`을 다시 쓴다.
- [F] 기존 회귀 중 U7 PC를 "실행부 없음"으로 기대하는 곳(작업 트리)은 U7 구현 시 다른 실행부 없는 PC로 옮겨야 한다.
  - `engine/tests/animation_machine_frame_helpers_test.cpp` 69행 edge `{0x480cc,0x4aa88,0x480d2}`·`{0x480e4,0xe8a48,0x480ea}`, 238~239행, 288행 outside 목록의 `0x4aa88`·`0xe8a48`
  - `animation_machine_fade_card_test.cpp` 135행
  - `animation_machine_screen_test.cpp` 69행
  - 주석: `animation_machine_input_test.cpp` 7행, `animation_machine_exit_test.cpp` 75행
- 폭·연산 규칙:
  - 메모리 LSR.W는 WORD 읽기·쓰기 1회씩이다.
  - BCHG 메모리 bit 번호는 mod 8이다.
  - EXG는 두 LONG을 교환한다.
  - MOVEM.L -(A4)는 LONG 단위로 A4를 먼저 줄인 뒤 쓴다.
  - MOVE.W Dn,-(A7)/(A7)+는 WORD live stack이다.
  - `(A0)+`·`(A1)+`는 WORD 2, LONG 4씩 증가한다.
  - CMPI.B·CMP.W·CMPI.W·CMPA.L 뒤 BCC/BCS는 무부호다.
  - LSL.W #2는 상위 WORD를 보존한다.
  - `2990` WORD 이미지는 결정 1을 따른다.
- 루프:
  - `4aa9e` 16회 고정(A4 비교)
  - `4aafe` 16회 직선 코드
  - `e8ae0` 무제한(결정 2)

## 시작 상태(관측 산출물 재생, 읽기 전용)

[F] 방법: scratch `u7/entry7.py`, `entry7b.py`, `cover7.py`가 기록된 PC 열을 `480bc`..`480f0` 구간별로 분류했다.
- `artifacts/stage_entry_body/native_*_begin.trace.json.gz`(142)
- `artifacts/stage_frame/verification.json`(SHA `47645dd39e0df8241cb504cd637a99cdc751544b4ac47c9e1227d8d5705f53b5`, 96 행)

[F] `u7/routed7.py`는 두 출처의 실행 PC 1,498개를 작업 트리 라우팅 식(소스 정규식 근사)과 제안 U7 범위에 대조했다. 전부 어느 한쪽 안에 있었고, 그중 190개는 U7 범위에만 있었다. [I] 따라서 U1~U7 구현 뒤 이 frame들의 명령은 모두 실행부가 있다. [U] 기존 실행부가 이 seed들의 내부 경로를 모두 받는지는 실행해 봐야 안다.

- stage_entry_body(첫 자연 frame 142):
  - [F] 142 frame 모두 같은 U7 경로를 탄다: `4aa88→4aafe→4ab32→4ab74→4ab86(EXG)→4ab88`과 `e8a48→e8aae→e8ac2→e8ace`.
  - [F] 즉 `10f001`=0(slot loop, `10db84` 강제, 디버그 cue 없음)이고, 할당 요청 `10de2f`=0, `10de2e`≠0이며, ring wrap이 없고, `10d744` bit7 이전 값이 0이다.
  - [F] 137 frame이 `480f0`에 도달한다. 5 frame(`native_0136..0140`)은 `2efa6` 뒤 기존 sound 대기 `3aea`에서 멈춘다.
  - [F] 이 trace들의 begin 상태는 `480bc` 진입 시점으로 저장되어 있지 않다(U1 관측기 주석). 따라서 경로 근거로만 쓰고 machine seed로는 쓰지 않는다.
- stage_frame(96 행 중 64 행이 `480bc`에서 시작하고, 나머지는 hold/release 이어 실행이다):
  - smoke·carried 40 행(results 0..39, `verify_stage_frame.smoke()` seed 0/4/25/34, bank 2/3, 출력 승계):
    - [F] U7 최소 경로다. smoke host write가 `10f001`=0, `10dc88`=`10db88`, `10de2e`=1, `10de2f`=0을 둔다.
    - [F] ring wrap `4ab2e`는 smoke frame 7·15(results 7, 15)에서 일어난다.
    - [F] EXG `4ab86`은 시작 행 64 중 42에서 실행된다. 이는 frame마다 `10d744` bit7이 토글되기 때문이다.
  - active 3 행(40 spatial, 41 region, 42 cue-allocation):
    - [F] 42에서만 할당 경로를 탄다: `e8a50→e8a6a→e8af4`(flags bit0/1 없음) `→e8a70→2986→28ae`.
    - [F] `28ae`는 `104ca0`=0이라 `28b4` BCC로 실패(`290e`)한다. 이어 `298e→e8a8a→43e08→e8a9c`(index 0, `0000`/`0002`를 `100f0e`에 씀) `→e8aae`(`10de2e`=1) `→e8ac2→e8ace`.
    - [F] cue는 RAM `106000`(host write)에 있다. 바깥 A6=`100820`이다. stack 이미지는 `2004`다(결정 1).
  - buffer chain 7 행(43~49):
    - [F] host write로 `10f001` bit7, slot 표 `10daf8`, callback `109152`=`cd50`, queue를 둔다. slot 0만 일치하고 1..15는 A6 null로 건너뛴다(`4aa9e→4aaee`).
    - [F] `buffer-first-start`(43)은 첫 sprite 대기 A7=U−38이다. hold(44)는 callback·`8d36`·`8d3a` 오염 후에도 같은 상태다. release(45)에서 둘째 sprite가 대기한다. release-second(46)에서 `480f0`까지 간다.
    - [F] `buffer-second-start`(47)은 첫 제출을 통과하고 둘째에서 대기(A7=U−26)한다. hold(48)과 release(49)가 이어진다.
  - cue chain 3 행(50~52)과 cue-debug-status 4 행(53~56):
    - [F] `10f001` bit1 디버그 cue sprite 경로다. 50은 `cda4` 대기(A7=U−8)이고, 53은 `e8b46` BSET(Y≥`1e0`, clip-Y)이며, 54/55/56은 clip-X/full/accepted다.
  - sound 37 행(57~93)과 external 2 행(94, 95):
    - [F] U7 최소 경로다. 대기는 기존 sound 실행부(`3aea`)다.
- [F] stage_frame이 실행한 U7 block 시작은 43/60이다.
  - 미실행 17개: `4ab5a` `4ab6e`(bit0 디버그), `4b794` `4b7a4` `4b7b8` `4b7f4` `4b800`(객체 flags bit2/0/1), `e8ab6` `e8aba` `e8ad0` `e8adc` `e8ae0` `e8ae8` `e8aee` `e8af2`(stream 진행, `10de2e`=0), `e8b04` `e8b12`(cue flags).
  - `28ae` 성공(`2908`) 경로도 `480bc` 문맥에서는 관측되지 않았다.
- [F] 선언 진입 자료(재사용 후보, typed host API 관측; 모두 stack을 RAM 밖 별도 영역에 두었으므로 machine 규약으로 다시 관측해야 함):
  - `artifacts/stage_buffer_frame/observation.json`(SHA `6b77299d0809fd21439effba2e1edf8a27cd32e7f2287ef25da009693320850c`, 659 조건): 14개 U7 조건분기 전부와 `cda0`/`cda8` 대기 양쪽을 관측했다. `4ab56`·`4ab6a` 양쪽, `4aab0`·`4aabe`의 skip 쪽도 포함한다.
  - `artifacts/stage_cue_frame/observation.json`(SHA `c4e44fc73bf700b34396d1f00d339bd37661f0aa0a193f26eb492067d108f63c`, 822 조건): `e8a48` 분기 10개 양쪽과 `28ba` 성공 87/실패 56을 관측했다. `e8b26` null 쪽은 1회다.
  - `artifacts/stage_cue_control/observation.json`(SHA `b820dff0be27fbc038c563473840fc6bb3652788c57bf200c7248d0c1a06da52`, 555 조건): `e8ad0`/`e8af4`/`2986` 직접 진입이다. `28c2` 실패 16이 포함되며, 이는 `e8a48` 밖 문맥이라 결정 1 선택 A에서는 오류 대상이다.
  - [I] 각 관측기의 `build_cases`/`fixture`(`tools/observe_stage_buffer_frame.py`, `observe_stage_cue_frame.py`, `observe_stage_cue_control.py`)를 machine 선언 진입에 재사용할 수 있다.

## 전체 `480bc` frame 통합(U1~U7)

[I] U7 구현 뒤 다음 경로가 처음으로 연결된다.
- `480bc → 47642 → 1a73c(U2~U5) → 49b0c(U6) → 4aa88(U7) → b4a2a → 6f1c2 → 4701e → e8a48(U7) → 2efa6 → 480f0` RTS
- 그 RTS 뒤 frame 진입 시 A7에 있던 복귀 LONG(U1 관측기 규약 `2ac2`)으로 간다.

[F] 정지 규약은 다음과 같다. stop은 그 복귀 PC다. 대기가 있으면 `AnimationMachineWaiting`을 받고 같은 stop으로 재개한다. 나머지는 checked 오류(전체 rollback)다.

## 검증 조건(최소)

- **전체 frame 통합(필수, U1~U7 결합)**: stage_frame 96 행을 machine 규약으로 다시 만든다(U1 관측기와 같이 A7=`1feffc` RAM mirror, 복귀 LONG `2ac2`, PVC page 선언).
  - seed에서 `480bc`로 진입해 `480f0` RTS 뒤 stop(`2ac2`)까지 원본과 비교한다. 대상은 다음과 같다.
    - smoke·carried chain: 앞 frame의 machine 출력을 host 변경 없이 다음 frame 입력으로 쓴다. ring wrap과 EXG 교대를 포함한다.
    - active 3 행: 42의 stack 이미지 WORD 포함.
    - buffer-first/second·cue chain: start→hold→release(→release-second)이며, 각 호출 사이에는 stage_frame과 같은 host write만 둔다.
    - cue-debug-status 4 행, sound chain 37 행, external 2 행.
  - native 기준은 같은 seed를 machine 관측 규약(stack이 RAM mirror에 쓰임)으로 다시 실행한 결과다.
  - [I] stage_frame 기록 RAM과는 stack 영역 밖에서만 같아야 한다. 교차 확인용이다.
  - split/continuous 둘 다 한다.
- 자연(U7 단독): 같은 seed를 원본으로 PC=`4aa88`/`e8a48`에서 캡처한 상태에서 시작해 `480d2`/`480ea` stop까지 비교한다. 대기 chain도 포함한다.
- 선언 진입(위 typed 관측 생성기, stack을 RAM mirror로 옮기고 실제 호출자 복귀 LONG `480d2`/`480ea`):
  - `4aa88`: 16 slot 조합(A6/A0 null, D6 불일치, D7.B 비교와 slot index 15), 객체 flags bit0/1/2 조합, 첫·둘째 대기 각각과 둘 다, 앞 slot의 port 4개를 게시한 뒤 다음 slot에서 대기, bank 3 진입(reset 뒤 bank 2), clip 반환.
  - cursor: `10db88`, `10dc68`(wrap), `10dc6a..10dc86`(cursor 자기 겹침), 범위 밖 RAM, 홀수(오류), ROM(쓰기 오류).
  - `10f001` bit0과 `104cab|104cb1` bit7 조합, `10d744` bit7 0/1.
  - `e8a48`: tag `1b`/`1c`/`3b`/`3c`/`ff`(skip 경계), index 0..`1f` 전부(`e8a0c+4i`, 코드 바이트 읽기 포함), cue flags 0..3, 덧셈 carry 유무, `28ae` 성공/실패, `10de2e` 0/비0, `10de2a` null/비null, gate 경계(같음/±1, `ffff`), `e8ad0` null 반환(`10de26`=4), 디버그 bit1과 cue null, Y=`1df`/`1e0`, `cd58` clip/full/accepted/대기.
- `2986` 이미지(결정 1):
  - 성공: 부모 +10 WORD=`ffff`(X=1), BYTE 6a `00`/`01`/`80`.
  - 실패(`104ca0`=0): cue flags bit0 carry, bit1 carry, 둘 다, 없음(X 0/1).
  - 선택 A에서는 `e8a8a`가 아닌 복귀 LONG으로 실패 경로에 직접 진입하면 오류여야 한다. `28c2` 경로, stage_cue_control 문맥이 여기에 해당한다.
  - 별칭 검사 오류: 재읽기 주소가 stack 범위와 겹치는 경우, `2992`가 stack WORD를 덮는 경우.
  - 이미지 WORD는 RAM 바이트로 비교한다. Unicorn hook에서 SR을 읽지 않는다.
- 경계·오류:
  - Unknown carry로 `298e`에 직접 진입하면 오류여야 한다.
  - 묶인 분기 24개와 내부 PC(`4b7d4`·`4b80e`·`e8b52`·`e8a84`·`e8aec` 등), 자료 PC(`e8a0c`)에 직접 진입하면 거부해야 한다.
  - 홀수 A0/A4/A6/A7 접근 오류와 비`cd50` callback 오류는 전체 rollback이어야 한다.
  - `e8ae0`이 step 상한에 걸린 오류는 전체 rollback이어야 한다.
  - zero-step과 비도달 stop rollback을 넣는다.
  - U1·fade_card·screen 회귀의 `4aa88`/`e8a48` 기대값을 갱신한다.
- 비교 항목은 기존과 같다: full 64KiB RAM(stack mirror 포함)/16R/PC/A7/carry 분류/PVC-device/bank/ordered ports/external reads/status, 입력·산출물 SHA, ROM stat 불변. C 판정은 원본 opcode 분류로 하고 Unicorn hook에서 SR을 읽지 않는다.

## 필요한 ROM·MS5D 자료 창

- [F] `e8a0c..e8a8c`(128B, SHA `73399f87…05ae`): `e8a9c`의 `(A1)+` WORD 두 개 읽기.
  - 논리 표는 앞 16B(index 0..3: `0000 0002`, `0000 0001`, `0001 0001`, `0002 0001`)다.
  - index 4..`1f`는 `e8a1c..` 코드 바이트를 자료로 읽는다(원본 그대로).
  - [I] 의미상 index는 tag−`1c`이며 기본 표 크기 밖 tag가 자연 발생하는지는 [U]다.
- [F] `e89e4..e89ec`(기본 cue 8B, `e8a1c` 문맥에서 `10de26`에 게시)와 `e89ec..e89fa`(기본 stream 12B+`ffff`, `e8a02`에서 `10de2a`에 게시): U7은 포인터가 가리킬 때만 읽는다. 포인터를 두는 `e8a1c`/`e8a02`는 U7 밖이다(`e8a02`는 U5).
- [F] catalog cue(`stage-cue-frame.md`의 42 nonnull root 첫 8B)는 fixed ROM에 있다. `4b784` sprite record(LONG 4(slot)+4)는 포인터 값에 따라 fixed/banked/RAM 중 하나다.
- [F] 주소만 싣고 읽지 않는 상수는 `d5f16`(새 객체 callback LONG; `cmpi.w #3,$76(a6)`로 시작하는 코드)과 `100bf4`(부모 객체 A1)다.
- [F] 위 fixed 창은 모두 physical `program_rom_000000.ms5d`(kind 3, canonical-physical-program manifest) 범위 안이다. 결정 4 선택 A면 machine은 physical 창으로만 읽는다.
- [I] machine 검증기는 physical ROM을 직접 읽으므로 kind1 창은 게임 런타임 납품 범위의 확인용이다.

## 미확인·범위 밖

1. 메인 결정 1~6.
2. [U] 실제 게임에서 `480bc` 실행 중 SR system byte(IPL)의 값과, 결정 1 상수 `20`이 자연 실행과 일치하는지.
3. [U] `10f001`(bit7/bit1/bit0 디버그 스위치로 추정, [I])의 생산자, slot 표 `10daf8..10db77` 설치 경로, `10db84..10db87`의 의미.
4. [U] ring `10db88..10dc87`(16 WORD/frame 감쇠로 추정, [I])과 double buffer `10d746`/`10d918`(각 `1d2`B 중 앞 `d0`B와 +`1d0` WORD만 지움)의 소비자와 의미.
5. [U] 할당 요청 `10de2f`의 생산자, `10de2e`의 의미(수동 cue 고정으로 추정, [I]), stream record 배치(+0 gate, +4 cue 8B, 12B 간격은 [I]), tag `1c..3b`의 게임 의미, 객체 +`76`/`78` WORD 두 개의 의미.
6. [U] 자연 플레이에서 `28ae`가 실패하는 빈도와 그때 `100e98` fallback 객체를 덮는 부작용의 영향(원본 그대로 구현, U5 메인 결정 4와 같음).
7. [U] 결정 1 선택 A의 caller 규칙은 `480bc` 밖 `2986` 호출자 155곳에 적용되지 않는다. 그 문맥들의 machine 통합은 범위 밖이다.
8. [I] `e8a1c`/`e8a3a`(cue 초기화·상태 조회)와 `e8c3c`(`e8ad0`의 다른 호출자), `47baa`(`e8af4`의 다른 호출자), `498a2`·`4b4f0`·`4b6b4`(`4b784`의 다른 호출자)의 machine 통합은 범위 밖이다. 같은 block이 쓰이므로 재사용될 수 있다.
9. [I] 자연 scheduler·IRQ/timing·일반 CCR(X/N/Z/V; 결정 1의 한 WORD 제외)·직접 플레이·전체 Goal은 범위 밖이다.

작업자 scratch: 세션 scratchpad `u7/`(저장소 밖). 파일은 `md7.py`, `leaders7.py`, `leaders7.json`, `entry7.py`, `entry7b.py`, `cover7.py`, `routed7.py`, `srscan.py`, `srprobe.py`, `refs7.py`다.
