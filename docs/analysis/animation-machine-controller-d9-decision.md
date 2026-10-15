# controller D9: D1 frame 구동기에서 controller를 실행하는 선언 상태 결정

**상태: 구현 전 계약 초안 — 메인 결정 전.** 선택지·탐침 근거·권고와 frame 구동기 변경 계약이다. 구현·검증 기록이 아니다.

범위 근거: F5 범위 문서(`animation-machine-frame-head-f5-scope.md`, SHA256 `973d45957731ff17ccf49537024307cf7fd20fe9270c9d9bb44a2bc553280fb0`)의 결정 D9("C1/C2의 선언 상태(demo `c66a` + `104cd4` = 1 대 game `c7fc` + `10fdaf` = 2)는 H 단위가 끝난 뒤 별도로 정한다")와 D10, D1 frame 구동기(`engine/include/ms5/animation_machine_frame.h` SHA256 `79c82c5607a9f67a544c0b50edbcd1fd7e1c45ac40d493d58a451ae53ecfa9f6`, `engine/src/animation_machine_frame.cpp` SHA256 `4ab110fda0c499e1966eb7d37b4c0ddf3d64ed4dbc60023f7c50bdebfe03acbb`, 기록 `animation-machine-frame-driver-d1.md`). 단위 계약은 `animation-machine-controller-c1-contract.md` `-c2-contract.md` `-c3-contract.md`다.

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 작성했다. ROM SHA256 `29112a94…c886c860f`(작업 전후 같음), 작업 트리 `/home/user/ProjectSlugV` HEAD `c49bcd2`. 표기 [F]/[I]/[U]는 다른 계약과 같다. 탐침은 선언 모델이다. BIOS·자연 IRQ·자연 scheduler를 주장하지 않는다.

## 요약

- [F] **기록 상태(controller `c52a`)를 그대로 실행해도 게임이 해체되지 않는다.** 자연 137 seed × 400 frame에서 `c52a`는 frame 1에 한 번 boot fill을 하고 callback `c560`을 설치한다. 이후 `c560`은 WORD `107dea`(= `2000`)를 읽고 RTS하는 대기를 매 frame 반복한다. 136 seed가 400 frame을 완주했고, case 141은 선언 생략 때와 같은 frame 0 `odd-pc`에서 멈췄다. 표본 6 seed에서는 node 순서가 선언 생략과 400 frame 내내 같았다.
  - `107dea`를 줄이는 것은 IRQ `c8c`뿐이다. 범위 문서 §2.4·D9 (iii)의 "첫 frame에 해체"는 `1008e4` := `c66a` 선언의 결과다.
- [F] **(ii) 게임 mode 선언(LONG `1008e4` := `c7fc`, BYTE `10fdaf` := 2)도 136/136 seed가 400 frame을 완주했다.**
  - 매 frame 경로는 `c7fc` → 꼬리 `c988`이다(30,996 frame).
  - stage controller node `100b30`이 idle이 되는 frame(1·221·241·245)에는 `c76a` 전환(해체 → 자식 `b300`)이 일어난다. 이후 매 frame 경로는 `c79a` 대기다(23,132 frame).
  - 새 미routing code는 controller, 자식 `b300`/`b344`, 그리고 `b300`이 여는 menu의 항목 handler(`a856` `a876` `a896` `a8bc` + `a75a`, 25 leader)뿐이다(§3.3).
- [F] **(i) demo 선언(LONG `1008e4` := `c66a`, BYTE `104cd4` := 1)은 136 seed 모두 BIOS `c00444`(`c6c8`)에서 끝난다**(frame 108/328/348/352).
  - seed의 replay 포인터 LONG `104cc4`가 0이다. 그래서 H의 입력 replay는 ROM 주소 0부터 읽는다.
  - 자식 `e66aa` 계열(미routing, TRAP 2개)이 전환 뒤 N을 차지한다.
- **권고(작업자):**
  1. frame 구동기에 controller 실행 option(`Execute`)을 더한다. 기본은 지금의 선언 생략(`Skip`)이다.
  2. D9는 **선택 B(ii) 게임 mode**를 목표 상태로 정한다.
  3. 구현 순서상 **무선언 구성 (iii)**을 먼저 쓴다. 이 구성은 C3a 9 block만으로 자연 136 seed의 선언 생략을 없앤다.
  4. (i) demo는 쓰지 않는다.

## 1. 선택지

| 기호 | 구성 | 선언(frame 1의 H 시작 전 host 쓰기) |
| --- | --- | --- |
| S | D1 현행: controller 선언 생략(PC := `2ac2`, A7 += 4) | 생략 자체가 선언 |
| (iii) R | 기록 그대로 실행(`c52a`) | 없음 |
| (ii) G | 게임 mode | LONG `1008e4` := `c7fc`, BYTE `10fdaf` := 2 |
| (i) D | demo | LONG `1008e4` := `c66a`, BYTE `104cd4` := 1 |
| (참고) | `c66a`만 | LONG `1008e4` := `c66a`(범위 문서 실험 E 1행) |

- [F] 선언 시점: frame 0은 seed의 N만 실행하므로 첫 H는 frame 1이다. 관측기의 `cfg['writes']`(H 시작 전 host 쓰기)로 frame 1에만 적용했다. (ii)는 `b68`이 frame 1의 H에서 BYTE `100012` := `10fdaf` = 2를 복사하므로 H·controller·N이 같은 frame부터 게임 mode를 본다.
- [F] seed 상태: controller node `1008e4`의 `+62`와 `+74..+83`은 0이다. LONG `100b30`(stage controller node callback) = `47af0`, `104cd4`/`104cc4`/`104cc8` = 0, `107dea` = 0, `10fdae` = `10fdaf` = `100012` = 0(case 0·94·135 확인, 범위 문서 §2.1의 142 seed 값과 같다).

## 2. 탐침 방법

- [F] scratch `ana_c/cprobe.py`: `observe_animation_machine_frame_head.HeadRun`(D1 protocol)을 in-process로 상속한다. `run_head`가 controller 진입(H stop)에서 돌아오면 같은 CPU로 controller를 Unicorn에서 실행한다.
  - stop: code hook `2ac2`에서 A7 = SPd(`1ff000`)일 때, 곧 controller RTS가 dispatcher로 돌아온 순간이다.
  - 대기 해제: 기존 선언 해제(sound `3aea`, sprite `cda4`, gate)를 쓴다.
  - BIOS fetch(`c00000..`)는 경계로 멈춘다(`c310` 카드는 option, 이번 구성에서는 닿지 않음).
  - 복귀 뒤 A7을 SPd − 4로 되돌린다. 그러면 관측기의 선언 생략 코드(PC := `2ac2`, A7 += 4)가 controller 실행 결과 상태를 그대로 N에 넘긴다.
- [F] seed: `verify_animation_machine_frame_driver.declared_rebase()`의 Linux 재생성 `stage_entry_body`(observation SHA256 `f74048bbeaa83a80e93473038e1867b07b14d0c4693ab5a05d4f73b3beeab04a`)와 `R.prepared(case)` RNG 준비다. 자연 137 seed, 400 frame, continuous 실행이다. 입력 `ff`, raster 0은 D1과 같다.
- [F] 도구: `p2.py`(경로 상세), `p3.py`(S 대비 node 순서·RAM 첫 차이, 6 seed), `p4.py`(전 seed 집계), `p5.py`(전 seed, 실행된 모든 TB 범위의 routing bitmap 검사). routing bitmap은 현재 `engine/src/animation_machine.cpp`(SHA256 `c7318132…caad2`)를 `observe_animation_machine_scheduler_rng.build_routing`으로 읽었다.
- 저장소 도구·ROM·추출 자료는 고치지 않았다.

## 3. 탐침 결과

### 3.1 전 seed 집계(`p4.py`, 자연 137 seed × 400 frame)

| 구성 | 완주 400 | 멈춤 | controller 경로(frame 수) | 실행된 controller leader | 전환 첫 frame |
| --- | --- | --- | --- | --- | --- |
| (iii) R | 136 | case 141 frame 0 `odd-pc`(S와 같음) | `c52a`→`c560` 136, `c560`→`c560` 54,128 | 9(C3a 전부) | 1(boot 1회) |
| (ii) G | 136 | case 141 같음 | `c7fc`→`c7fc` 30,996, `c7fc`→`c79a` 136, `c79a`→`c79a` 23,132 | 43(C1 24, C2 19) | 1: 8, 221: 4, 241: 35, 245: 89 |
| (i) D | 0 | 136 seed가 BIOS `c00444`(`c6c8`), frame 108(8)/328(4)/348(35)/352(89). case 141 같음 | `c66a`→`c66a` 30,996, `c66a`→`c6c0` 136, `c6c0`→`c6c0` 14,416, `c6c0`→BIOS 136 | 64(C1 49, C2 15) | (ii)와 같음 |

- [F] N의 선언 대기는 세 구성 모두 card resume 130회(130 seed × 1)다. D1 기록과 같다. controller 안의 대기는 0회다.
- [F] controller port 합계:
  - (iii): PVC `2ffff2`/`2ffff0` 각 272건(seed당 frame 1에 2쌍).
  - (ii): 전환 frame에서만 `3c0000/4` 280,432, `300001/1` 1,496, `3c0004/2` 680건. `caf0` 화면 초기화와 해체 watchdog이고, 전환 136회 × 2,062 + 11 + 5다.
  - (i): 위 전환 몫 + 표시 frame `3c0000/4`·`3c0000/2`.
- [F] 전환 뒤 N의 미routing node callback:
  - (ii): `b300` 136, `b344` 23,132.
  - (i): `e66aa` 136, `e66ee` 4,624, `e673e` 9,792, `e6932` 12,376, `e6916` 2,040, `e68c6` 136.
  - (iii): 없음.

### 3.2 S 대비(`p3.py`, case 0·1·2·94·100·135)

- [F] (iii): 6 seed 모두 400 frame 동안 node 순서(pass별 callback 열 digest)가 S와 같다. RAM은 frame 1부터 다르다. `c52a`의 효과(controller node 필드, `107def` := `ff`, `107dea` := `2000`, `100010`, palette fill)가 남기 때문이다.
- [F] (ii): node 순서는 전환 frame(245 또는 1) 전까지 S와 같다. RAM은 frame 1부터 다르다(꼬리의 controller 필드, BYTE `100012` = 2).
- [F] (i): node 순서는 전환 frame 전까지 같다. 끝은 BIOS다.

### 3.3 routing 밖 실행 code(`p5.py`)

- [F] 방법: 실행된 모든 TB(Unicorn block hook)의 바이트 범위 안 짝수 PC를 현재 routing bitmap으로 검사했다. 기준은 같은 방법으로 돌린 S(선언 생략) 136 seed다.
- [F] S 기준선: routing 밖 PC가 53개다. 모두 기존 실행부 block의 내부 PC(예: `8c18`, `8e4c`, `2a04`)다. D1 C++ 검증(54,400 frame 일치)이 이미 덮는다.
- [F] (iii): 기준선과 controller closure를 빼면 새 PC가 0개다. H·N은 S와 같은 code만 실행한다.
- [F] (ii): 기준선, controller closure, `b300..b360`을 빼면 새 PC가 18개다(모두 N, 136 seed 전부).
  - `a856..a8ce` 15개: menu 항목 handler. 첫 실행은 전환 4 frame 뒤다.
  - `3900` `e7c32` `e84d2`: 기존 실행부 block `38fe` `e7c30` `e84d0`의 명령 내부·끝 PC다.
  - 정적 closure로 보면 handler는 leader 25개(`a75a` 포함)이고 callee는 모두 routing돼 있다(C2 결정 2).
- [F] 두 구성 모두 `skip_bad` = 0이다. controller 복귀 때 A6 = `1008e4`, A7 = SPd다.

### 3.4 정정

- [F] 범위 문서 요약·§2.4·D9 (iii)의 "`c52a`부터 실행하면 … BIOS `c00444`"·"(iii) 기록 그대로: 첫 frame에 해체"는 IRQ로 `107dea`가 풀린다는 가정의 결과다. D2(IRQ 미실행)에서는 `c560` 대기가 끝나지 않는다. "해체"는 `c66a` 선언(실험 E 1행)의 결과다.
- [F] 범위 문서 §2.4 "stage 비활성 frame의 전환에서 생기는 자식(`b300` `e66aa` 등)은 미routing 경계"는 맞다. 다만 (ii)에서 필요한 것은 `b300`(11 leader)과 그 menu handler(25 leader)이고, callee는 모두 이미 routing돼 있다(C2 결정 2).

## 4. 권고

1. **구동기 option `Execute` 추가(§5).** 기본은 `Skip`이므로 D1의 검증 결과·시험·도구가 바뀌지 않는다.
2. **D9 = 선택 B(ii) 게임 mode.** 근거:
   - [I] stage seed의 상태(`100b30` = stage controller callback, `104cd4` = 0 실시간 입력)와 맞는 controller 상태는 게임 진행 중의 `c7fc`뿐이다. `c7fc`는 `c7f6`이 `100b30`을 `477e4`로 재시작한 뒤 설치하는 상태다.
   - [F] 136 seed가 400 frame을 완주한다. 새 미routing 경계는 자식 `b300`과 그 menu handler(합 36 block)로 줄어든다.
   - [I] IRQ(F6)를 넣은 뒤에도 일관된다. 게임 mode의 IRQ는 BIOS `10fd80` bit 7 쪽 경로이며, 범위 문서 §2.5를 근거로 본다.
   - 선언은 host 쓰기 2건이다. frame 1 H 시작 전에 하고, 관측·검증 기록의 `declared` 목록에 남긴다.
3. **무선언 구성 (iii)을 먼저 쓰고, 나중에는 회귀 구성으로 둔다.**
   - [F] C3a 9 block만 있으면 자연 136 seed × 400 frame의 controller가 실제 실행이 된다. 선언 생략도, 선언 상태도 없다.
   - [I] (iii)은 IRQ가 없을 때만 일관된다. F6 뒤에는 `107dea`가 풀려 `c56e` → `47570` → `10fdae` = 0 → `c00444`로 끝날 것으로 본다. 따라서 장기 목표 구성은 아니다.
4. **(i) demo는 쓰지 않는다.** [F] seed의 replay 포인터가 0이라 replay 입력이 ROM 벡터 영역이다. 모든 seed가 BIOS 종단으로 끝나고, 미routing 자식 `e66aa` 계열(72 leader, TRAP)이 필요하다. demo는 영역 E(부팅·타이틀·데모)에서 boot 경로(C3b)부터 자연 상태를 만들어 다룬다.
5. **D10 정정:** C3a는 (iii)에서 자연 실행되고, C3b는 fixture 전용이다(C3 결정 1·2).

## 5. frame 구동기 변경 계약(`Execute`)

### 5.1 API(public header `ms5/animation_machine_frame.h` 변경, 메인 승인 필요)

- `enum AnimationFrameSegment`에 `AnimationFrameController=2`를 더한다. 대기 기록 `AnimationFrameWait.segment`가 이 값을 쓴다.
- `AnimationFrameOptions`에 다음을 더한다. 기본 생성 값은 지금 동작과 같다.
  - `bool execute_controller`: 기본 false, 곧 Skip.
  - `bool credit_resume`: 기본 false.
  - `std::uint32_t credit_answer`: 기본 `01010000`.
- `AnimationFrameResult`에 다음을 더한다.
  - `std::vector<VideoPortWrite> controller_ports`
  - `std::uint32_t controller_external_reads`
  - `std::uint32_t controller_exit_pc`: C 끝의 LONG `(1008e4)`, Skip이면 0.
  - 기존 `controller_pc`는 H stop PC(= C 진입 PC) 그대로다.
- `run_animation_machine_pass`(frame 0 N)는 바꾸지 않는다.

### 5.2 `step_animation_machine_frame` 순서(Execute)

1. H: 지금과 같다(stop LONG `(1008e4)`, 경계 검사 동일).
2. **C**: `run_segment(stop = 2ac2, segment = AnimationFrameController)`. 시작 C는 Unknown이고 대기 해제 표·한도(구간당 16)는 H/N과 같다.
   - [F] controller 안 첫 flag 소비는 모두 같은 block 또는 callee가 만든 flag를 읽으므로 진입 C는 쓰이지 않는다.
   - 끝 검사: PC = `2ac2`, A7 = SPd(`1ff000`), A6 = `1008e4`, A5 = `108000`, LONG `(100820)`이 H 시작의 head callback(`e4a`/`e74`)과 같음.
   - 어긋나면 `animation frame controller boundary mismatch`(checked, frame 전체 보존)다.
   - [F] 탐침(`p5.py`)에서 (iii)·(ii)의 controller 복귀는 모두 A6 = `1008e4`, A7 = SPd였다(관측기 `skip_bad` 0, 136 seed × 400 frame). A5와 head LONG은 따로 기록하지 않았다 [I: controller는 A5를 `108000`으로만 쓰고 `100820`을 쓰지 않는다].
3. N: 지금과 같다. 진입 조건(PC `2ac2`, A6 `1008e4`, A7 SPd)이 C의 끝 조건과 같다.

- stop을 `2ac2`로 둘 수 있는 이유:
  - [F] dispatcher `2ac2 MOVEA.L 8(A6),A6`은 fade_card 실행부의 block 시작이다.
  - [F] controller closure 안에는 `2ac2`로 가는 분기가 없다. 정적 closure 291 block에서 확인했다.
  - [F] self delete `2a00`(→ `2ac2`)은 자식 `b344`만 쓴다. 자식은 N에서 실행되므로 C segment와 무관하다.
  - 따라서 C segment에서 처음 닿는 `2ac2`는 controller RTS다.

### 5.3 BIOS 경계(C segment에서만; H·N은 지금과 같음)

`run_animation_machine` 실패 시 지금의 card 재실행 방식을 일반화한다. 같은 입력에서 stop을 BIOS PC로 바꿔 다시 실행한다. [I] 실행은 결정적이므로 BIOS fetch 앞까지의 경로가 같다. 아래 순서로 시도하고, 처음 그 PC에 Returned로 닿는 것을 쓴다. 없으면 원래 오류를 돌려준다.

| BIOS PC | 조건(LONG (A7) = 복귀) | 처리 | 기록 |
| --- | --- | --- | --- |
| `c00468`(카드) | `c37c` 또는 **`c316`**(C2 `c310`) | 지금의 `card_resume`과 같음(BYTE `10fdc6` := `card_answer`, PC := 복귀, A7 += 4, C Unknown) | `AnimationFrameWait{pc c00468, address 10fdc6}` |
| `c00450`(credit, `credit_resume`일 때) | `4a992`(C1 `4a98c`) | LONG `10fdb0` := `credit_answer`, PC := `4a992`, A7 += 4, C Unknown | `AnimationFrameWait{pc c00450, address 10fdb0, size 4}` |
| `c00444`(SYSTEM_RETURN) | 조건 없음(JMP) | **종단**: frame 실패 `animation frame controller system return`(checked, RAM·상태·device·result 보존) | 없음 |

- [F] (i) 구성에서 136 seed가 `c00444`에 닿았다. 구동기는 그 frame을 checked 실패로 끝내고, 호출자는 직전 frame 상태를 가진다.
- [I] 대안: 성공으로 끝내고 PC `c00444`의 상태를 result에 담는다. 그러면 "다음 H 시작이 유효함"이라는 불변식이 깨지므로 비권고다.
- [F] (ii)·(iii) 자연 구성에서는 BIOS에 닿지 않는다. 카드 `c310`은 `c890` 경로, credit `c00450`은 BYTE `10fd82` ≠ 0에서만 닿는다.

### 5.4 불변식·시험

- Skip(기본)은 지금 구동기와 바이트 단위로 같아야 한다. 기존 `animation_machine_frame_test.cpp`와 `verify_animation_machine_frame_driver.py`를 무변경으로 통과해야 한다.
- 실패 시 어느 segment에서든 RAM·state·device·result를 바꾸지 않는다(지금 규약).
- C segment는 H stop 직후에만 시작한다. 따라서 `step_animation_machine_frame`의 입력 조건(H 시작)은 바뀌지 않는다.
- 단위 시험(`animation_machine_frame_test.cpp` 확장 또는 새 시험), C3a·C1·C2 구현 뒤:
  - (iii) 1 frame: C 경로 `c52a`→`c560`, port 4, `controller_exit_pc` = `c560`.
  - 다음 frame `c560`(port 0).
  - (ii) `c7fc` frame.
  - 경계 오류 3종: A6 변경, A7 불일치, head LONG 변경.
  - BIOS 3종: card `c316`, credit 선언, `c00444` 종단 보존.
  - 대기 한도.
  - Skip/Execute 동등 행: controller가 `c560`이고 RAM 영향이 stack뿐인 frame에서 Skip과 Execute의 N 결과 비교.

## 6. 단위 순서·의존

| 순서 | 단위 | block | 필요 | 효과 |
| --- | --- | --- | --- | --- |
| 1 | 구동기 `Execute` + C3a | 9 | H1~H4·H8(완료), area_clear, H3 `4718` | (iii) 자연 136 × 400 실제 실행, 선언 생략 0 |
| 2 | C1 | 116 | 1 | (ii) 매 frame(전환 전) 자연 실행 |
| 3 | C2 + `b300` + menu handler | 128 + 36 | C1 | (ii) 전환·`c79a` 대기, 136 × 400 완주 |
| 4 | C3b | 38 | C1·C2 | fixture 전용(boot 뒤·demo 도입·title) |

- [I] 2와 3은 C1의 꼬리·Z 규약(C1 결정 3)을 공유한다. C2를 먼저 하면 전환 frame에서 C1 PC(`c988`)를 지나므로 시험할 수 없다.
- 무효화 탐침(구현 시 정리):
  - `animation_machine_scheduler_test.cpp` `pass-controller`, `tools/verify_animation_machine_scheduler.py` `pass-head-ring-unchecked-step-limit`: 1에서 바뀐다(C3 결정 8).
  - 그 밖의 `c52a`/`c66a` 사용은 stop·Skip 기대라 유효하다.

## 7. native 검증 계획

- **관측:** 새 도구 `tools/observe_animation_machine_controller.py` 또는 frame head 관측기에 protocol option을 더한다. 기존 관측기는 in-process import만 하고 SHA를 고정한다.
  - D1 protocol의 controller 생략 자리에서 controller를 native로 실행한다. 이 문서 §2와 같은 stop(`2ac2` & A7 = SPd)과 BIOS 경계를 쓴다.
  - 구성 (iii)·(ii) × 자연 137 seed × 400 frame.
  - frame별로 H/C/N 각 구간의 시작·끝 전체 상태 SHA, 순서 있는 port, 대기, external read, controller 경로(leader hit)를 기록한다.
  - fixture 구성:
    - (ii) 전환 frame 직전 상태 + `c79a` 분기 선언(`10fdb6` = 1, `62` = 2/3)
    - (iii) + WORD `107dea` := 0 + `10fdae` ∈ {0, 2, 3}
    - `10fd82` = 1(credit·`d00034`)
    - card `c890` 경로
  - 조건마다 fresh-CPU split과 continuous를 두 번씩 실행해 같은지 본다(기존 관례).
- **C++ 대 native:** `verify_animation_machine_frame_driver.py`의 frame별 비교를 Execute 모드로 확장한 별도 검증기를 둔다. 기존 검증기는 Skip 기준으로 그대로 둔다.
  - 비교 항목: RAM 64 KiB, 레지스터·PC, PVC, segment별 순서 있는 port, 대기, external read 수, `controller_pc`/`controller_exit_pc`.
  - C++ 단독 연쇄 400 frame을 두 번 실행한다.
  - 부정 검사: controller 경로의 RAM 1바이트, 선언 누락(`10fdaf` 쓰기 빠짐), 종단 위조.
  - (ii)에서 `b300` 구현 전 기대: 전환 frame에서 C++ checked 실패(`unsupported animation machine PC`, N의 `b300`).
- **단위 차분:** 각 단위 계약의 V1 fixture 검증기(`tools/verify_animation_machine_unit_fixtures.py`) spec. V1의 `card` 해제는 `c37c`만 받으므로 `c316`·`c00450`·`c00444` 처리를 더해야 한다(검증기 확장 작업).

## 8. 위험·미확인

- [I] (ii)의 `10fdaf` = 2 선언은 H·N의 `100012` 소비자를 바꾼다(입력 `49b3a`, sound `3b2a` 등, 범위 문서 실험 D). node 순서는 전환 전까지 S와 같지만 객체 상태는 다르다. 이는 의도한 차이(게임 mode)이고 native 비교로만 판정한다.
- [U] `b344`(`a370`)가 0이 아닌 값을 돌려주는 조건. 400 frame 안에서는 없었다. 일어나면 `62` := 3 → `c79a`에서 `c7c0 JMP c00444`(종단)다.
- [U] seed가 실제 게임의 어느 mode에서 왔는지(host API 산출물, 범위 문서 §2.1). (ii)는 가장 가까운 일관 상태라는 추론이다.
- [U] IRQ(F6) 뒤 각 구성의 동작. (iii)은 boot가 진행될 것으로 본다 [I].
- 위험: public header 변경(§5.1)은 다른 도구(SHA pin)에 영향이 있다. 기존 구동기처럼 핵심 실행부 `animation_machine.cpp/.h`는 바꾸지 않고, frame 구동기 header·source만 바꾼다.

## 메인 결정 (Claude Opus 5.5, 2026-10-15)

- **D9:** frame 구동기에 controller 실행 모드(`Execute`)를 추가하고 기본값은 `Skip`으로 둔다. `Skip`에서는 D1 결과·시험·검증기가 바이트 단위로 같아야 한다.
  - 목표 상태는 (ii) 게임 모드다.
  - 먼저 (iii) 기록 상태(`c52a`→`c560` 대기, C3a 9 block)로 선언 없이 선언 생략을 없앤다. (iii)은 IRQ(F6) 실행 전까지만 의미가 있다(`107dea` 감소는 IRQ만 한다 [F]).
- **RTS를 건너는 Z 플래그**(`4a974`의 `TST.B (A0)`): 승인한다.
  - 소비 block에서 BYTE (A0)를 다시 읽어 Z를 계산한다.
  - A0가 확인된 work RAM 4바이트 중 하나가 아니면 checked error다.
  - TST와 소비 사이에 그 바이트에 쓰기가 없음을 계약 근거와 원본 비교로 확인한다.
- **BIOS:**
  - card `c00468`의 반환 주소로 `c37c`와 `c316`을 모두 받는다.
  - `c00450`은 옵션으로 켜는 선언 resume이다.
  - `c00444`는 상태를 보존하는 checked error("animation frame controller system return")이며 resume은 없다.
- **fixture 전용 경로:** `d00034` 백업 RAM 읽기는 checked error. `SBCD`는 68000 의미 그대로 구현하고 512 입력을 모두 시험한다. `JSR (A1)`는 실제 대상을 따라간다.
- **무효가 되는 시험:**
  - `engine/tests/animation_machine_scheduler_test.cpp`의 `pass-controller`는 탐침 값만 work RAM PC로 바꾼다.
  - pin된 `tools/verify_animation_machine_scheduler.py`의 `pass-head-ring-unchecked-step-limit`는 수정하지 않고 무효 목록에 기록한다.
- **단위 배정**(이번 10개 묶음):

  | 번호 | 단위 |
  | --- | --- |
  | #6 | D9 = 구동기 `Execute` + C3a + `Execute` 모드 native 관측·C++ 비교 |
  | #3 | C1(116) |
  | #4 | C2(128 + `b300` 메뉴 자식 36) |
  | #5 | C3 = C3a + C3b(38) |

  C1~C2를 완료하면 (ii)로 400 frame 원본 비교를 한다.
