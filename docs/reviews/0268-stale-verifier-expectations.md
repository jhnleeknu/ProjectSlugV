# 0268 단위별 runner가 돌리지 않던 검증기 4개의 낡은 기대값

메인 통합 sweep(`ms5-scratch/sweep/sweep.py`)에서 `verify_animation_machine_carry.py`, `_stage_catalog.py`, `_motion_walk.py`, `_objects_g3.py`가 실패했다. 단위별 runner(`verify_unit.py`)가 이 넷을 돌리지 않아, 뒤 단위가 바꾼 동작을 검증기가 따라가지 못했다. 이 문서는 원인, 분류, 바꾼 기대값과 검증 결과를 남긴다.

- 대상: branch `claude/verifier-fixes`, worktree `/Users/start/Workspce/metalslug-vfix`, 기준 `main` `7e18c48`(C1~C10 병합). 커밋은 메인이 한다.
- 작업자: Claude Opus 5.5 / high. `engine/src` 실행부와 C++ 시험은 바꾸지 않았다. ROM·`extracted/`·`artifacts/`는 읽기만 했다.
- 표기: [F] 사실(실행·ROM으로 확인), [I] 추론, [U] 미확인.
- 분류 결과: **넷 모두 뒤 단위의 의도된 변경 때문에 낡은 검증기 기대값이다. 실행부 회귀는 없다.**

## 1. carry: C6·C10이 stub 후속을 routing함

- [F] 실패: `b268e31`(C8 뒤)에서 `late-branch-0210b4-2`, FR12 tip에서 `late-branch-01dc8a-1`. `ac2ca0a`에서는 통과.
- [F] 검사 내용: interpreter stub `1dc8a BCC.W 1dccc` / `210b4 BCS.W 21564`를 known C로 실행하면, 고른 후속 PC에서 `unsupported animation machine PC`로 멈추고 API 출력이 모두 보존되어야 한다. 후속이 routing 밖이라는 전제다.
- [F] 원인:
  - C6이 `21564`(`JMP 2a00`)를 routing했다(C6 계약 표 `21564..2156a`). Set 쪽 run이 `21564 → 2a00 → 299c → 287e`까지 간다. `287e MOVEA.L 8(A6),A0; CMP.W 10(A0),D0`에서 A0 = fixture node `102000`의 LONG `8(A6)` = `a3592789`(홀수)라서 `program bus requires even WORD/LONG address`가 난다.
  - C10이 `1dccc`/`1dc8e`를 routing했다(C10 결정 5). 두 쪽 모두 `201a2 MOVEA.L 84(A6),A4; JSR (A4)`에 닿는다. LONG `84(A6)` = `81ec885b`는 ROM 목록 밖이라서 C3 검사가 `unsupported animation player c3 jump target`을 낸다.
  - C10 계약은 "carry 시험은 두 목표를 정지 PC로만 쓴다"고 C++ 시험만 확인했다. 이 Python 검증기는 확인 범위에 없었다.
- [F] 경로 확인: 같은 run에 앞쪽 stop을 두어 block 시작에 차례로 닿는지 봤다. `210b8`은 main과 FR14 tip 모두 routing 밖이라 `late-branch-0210b4-1`은 그대로다.
- 변경(`SUPERSEDED_LATE_BRANCH`). label은 유지하고, 이전 기대값은 행의 `former_expected_API_error`에 남긴다.

| label | 이전 | 이후 | 원인 단위 | 닿는 block 시작 |
| --- | --- | --- | --- | --- |
| `late-branch-01dc8a-1` | `unsupported animation machine PC` | `unsupported animation player c3 jump target` | C10 `1dccc` | `1dccc` `201a2` |
| `late-branch-01dc8a-2` | 같음 | 같음 | C10 `1dc8e` | `1dc8e` `1d1d0` `1dc92` `1dccc` `201a2` |
| `late-branch-0210b4-2` | 같음 | `program bus requires even WORD/LONG address` | C6 `21564` | `21564` `2a00` `299c` `287e` |
| `whole-caller-late-branch-01dc84` | 같음 | `unsupported animation player c3 jump target` | C10 | `1dc8a` `1dc8e` `1dccc` `201a2` |
| `whole-caller-late-branch-0210ae` | 같음 | `program bus requires even WORD/LONG address` | C6 | `210b4` `21564` `2a00` `287e` |

- 강화한 점: late-branch 3행은 stop을 고른 후속(`1dccc`/`1dc8e`/`21564`)에 두면 run이 거기서 끝나야 한다. 그때 상태는 입력과 같고 PC만 후속이어야 한다(16 레지스터, carry, RAM, PVC, bank, 포트 없음, 외부 읽기 0). 이것으로 분기 방향을 직접 확인한다. 이전 검사는 오류 문자열만 봤다. 전체 rollback 검사는 그대로다.

## 2. stage_catalog: C3이 `48350`을 routing함

- [F] 실패: `b268e31` 이후 `('boundary_entry_0479b0', 'animation machine external read queue empty', 'unsupported animation machine PC')`. `ac2ca0a`에서는 통과.
- [F] 원인(dispatch PC trace를 남기는 진단용 harness 사본, scratch 전용):
  - `479b0`은 F1c2부터 실행 가능한 block 시작이다(같은 파일 `SUPERSEDED_GUARDS`). 그래서 이 탐침은 "실행부 없음"이 아니라 run의 첫 routing 밖 PC에서 같은 문구로 멈춰 통과하고 있었다. `ac2ca0a`와 C2 병합 `24337ee`에서는 2,379 block 뒤 `48350`(C1 `48346`의 Set 쪽)에서 멈췄다.
  - C3 병합 `b5a702e`부터 `48350`이 C3 시작이다. run은 `48362 → C1 1d21c → …`로 4,293 block을 가서 `ea4 MOVE.W 3c0006.l,D0`(LSPC VCOUNT, queue 장치)에 닿는다. 이 API 호출에는 queue 값이 없어 검사된 오류가 나고, 전체 rollback된다.
  - `b5a702e`와 main의 trace는 같다(4,293 PC, 바이트 단위로 같음).
- 변경(`SUPERSEDED_BOUNDARY_ENTRIES`): `boundary_entry_0479b0`의 기대값을 `unsupported animation machine PC`에서 `animation machine external read queue empty`로 바꿨다(분류 `superseded_by_player_C3_routes_48350`). 같은 run에 stop `48350` / `1d21c` / `ea4`를 두면 각각 거기서 정상으로 끝나야 한다. `boundary_entry_0478a6`(TRAP)은 그대로다.

## 3. motion_walk: C9이 `20c00..20c30`을 routing함

- [F] 실패(FR12 tip; C9가 들어간 main도 같음): `computed_pc_run_on_oor-18c06-type7ffe`가 `unsupported animation player c9 PC`를 냈고, 기대값은 `unsupported animation machine PC`였다.
- [F] 원인: native 행의 계산 PC는 `18c0a JMP 18c0e(PC,D4.W)`와 type `7ffe`로 `20c0c`다. `20c0c`는 C9 block `20c00`(`20c00..20c0e`) 안의 `20c0a BMI.W 20c10` 변위 word다. C9 계약은 C++ 시험의 type만 `7ffe → 7ff0`으로 바꿨고(C10이 다시 `2562`로 바꿈), 이 검증기의 계산 PC 행은 확인하지 않았다. native 행의 type은 기록된 자료라서 바꾸지 않는다.
- 변경: `SUPERSEDED_COMPUTED['oor-18c06-type7ffe'] = 'unsupported animation player c9 PC'`, `SUPERSEDED_BY` = `player C9 interior 20c0c`. C5의 `oor-18efa-type7ffe`(`20f00`)와 같은 방식이다. 이전 기대값은 보고서의 `superseded_guard_errors`에 남는다.

## 4. objects_g3: FR7이 `4ad6c`를 routing해 G2 연속 검사의 빈틈이 드러남

- [F] 실패 시점: `92dbff7`, `2d68094`(FR8), `4627da8`(FR7 병합)에서 실패하고, `ba9bb6b`(frontier-units-4)에서는 통과한다(fixture 80개 제한 run, 나쁜 행 0 → 28). **영역 C보다 앞선 FR7에서 시작됐다.**
- [F] 나쁜 행: N08 `reach-entry-declared-*` 28개의 "through" 흐름. 각 행의 오류는 `('cont-run', 0, j, 'ok', None)`이고, 다른 검사는 모두 참이었다.
- [F] 원인:
  - through 흐름은 `4afe4 → 4ad6c → 4aff8 → 4ad6c → … → 4b26c → 4ad6c → guard`처럼 FR7의 충돌 판정 `4ad6c`를 매번 불렀다가 돌아온다.
  - FR7 전에는 `4ad6c`가 routing 밖이었다. 그래서 그 phase가 모두 black box로 막혔고(`phase_blocked` 15~16), G2 `run_cpp_flow`의 검사 (3)(성공 phase 2개 이상의 연속 run)이 한 번도 돌지 않았다.
  - FR7 뒤에는 사슬이 끊기지 않아 검사 (3)이 phase 0..j를 한 번에 돌리고 phase j의 끝 PC `4ad6c`에서 멈추게 한다. 그런데 C++ API는 stop PC에 **처음** 닿을 때 멈춘다(G2 `phase_groups` docstring의 규칙). 그래서 phase 0 끝의 첫 `4ad6c`에서 멈추고, chain 끝 상태와 달라 오류가 된다. 검사 자체의 문제다.
  - C++ 결과는 phase마다 native와 같았다. split 사슬은 phase별로 native 상태·포트·외부 읽기와 비교하고 그 비교가 모두 통과했다.
- 변경(G3만 바꿈; G2는 G3 docstring대로 수정하지 않음):
  - fixture 단계의 `run_cpp_flow` wrapper가 `('cont-run', i, j, 'ok', _)` 오류 가운데 **목표 PC가 phase i..j에서 이미 실행된 경우만** 다시 확인한다(`repeated_target_cont_run`).
    - (a) 같은 요청(stop = 반복 PC)은 첫 도착 phase의 native 끝 상태와 같아야 한다.
    - (b) i..j 가운데 앞에서 실행되지 않은 마지막 phase 끝(2 phase 이상)을 stop으로 둔 연속 run은 native 끝 상태, 포트, 외부 읽기, known C와 같아야 한다.
  - 둘 다 맞을 때만 오류를 지운다. 목표가 반복되지 않는 경우(G2 검사가 성립하는 경우)는 그대로 실패한다.
  - 새 check `fixtures_repeated_target_runs`를 두고, 행별 증거를 `repeated_target_cont_runs`, 개수를 `fixtures.repeated_target_cont_runs`에 남긴다. natural 단계는 바꾸지 않았다.
- [F] 결과: 28행 모두 (a)(b)가 일치한다. (b)의 stop은 `4b26c`, phase 범위는 `[0, j−1]`이다. 행 분류는 FR7 전과 같은 `guard-deliberate:native-unmasked-address`로 돌아왔다.

## 검증

| 검사 | main(`metalslug-vfix`) | FR14 tip(`a517aad` + 이 4파일) |
| --- | --- | --- |
| sweep `carry` | rc 0 | rc 0 |
| sweep `objects_g3` | rc 0 | rc 0 |
| sweep `stage_catalog` | rc 0 | rc 0 |
| sweep `motion_walk` | rc 0 | rc 0 |
| `make -j4 all test` | rc 0, 경고 0 | — |

- [F] FR11~FR14·E2는 이 네 검증기 파일을 바꾸지 않는다(`git diff 7e18c48 a517aad`는 `verify_animation_machine.py`의 SOURCES 한 줄뿐). 그래서 FR14 tip 확인은 detached worktree `metalslug-vfix-fr14test`(`a517aad`)에 이 4파일을 덮어 sweep으로 했다.
- scratch: `ms5-scratch/vfix/`(sweep 출력 `sweep-main/` `sweep-fr14/`, 탐침 helper `helpers/`, bisect 결과 `g3lim-*/` `sc-*/`).

## 남은 사항

- [U] carry·stage_catalog의 새 오류는 API 전용 대조다. native의 fault rollback과 같다는 주장은 하지 않는다(`native_exception_rollback_equivalence_claimed=False`, `API_only_control=True`). 이전에도 같은 제약이었다.
- [I] 단위별 runner가 이 넷(과 sweep 대상 전체)을 돌리지 않으면 같은 일이 되풀이된다. 단위 runner에 sweep 대상을 넣거나 단위마다 sweep을 돌리는 것을 메인이 정해야 한다.
