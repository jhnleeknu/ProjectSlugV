# 공식 verifier 4개 수정의 독립 delta 리뷰

2026-10-14. 인수 범위는 **수정된 공식 main 4개 전체 재실행 + 기존 24개 current-pin report + 기존 7개 reviewed-delta report**다. 적용된 네 파일의 AST·실제 source SHA, 31개 기존 report의 모든 input pin과 **공식 4개 전체 재실행의 종료 0 및 최종 report**를 독립 확인해 이 범위를 수용했다. 전체 35개를 새 source bytes로 다시 실행했다고 주장하지 않는다.

## Baseline·실제 적용 확인

원래 공식 35개 전체 실행은 **31 pass + 아래 4개 stale expectation 실패**로 종료했다. 실행 당시 517개 source pin은 모두 불변이었다. 원본 manifest SHA256 `267b6c50b2a43c48687382d107a2a4a7151925347065df8972ff84c32deabf47`, source-freeze SHA256 `87d755242e5e38b94d6746bdb07a8184e3d0d99693942ad6b595c5066e802677`를 보존한다. source-freeze는 시작 commit `409abfd`를 기록하며, 독립 비교 기준 commit `23779e0`의 네 tool bytes가 실제 freeze의 hash와 정확히 같음을 확인했다.

실제 적용 기록 `build/legacy_acceptance/delta-applied.json`과 commit **`668e142`**의 수정은 네 tool에만 있다. frozen 517개 파일 중 나머지 513개는 같은 bytes다. 원본 ROM, native 관측 및 C++ 엔진·공유 comparator는 수정하지 않았다. 각 파일의 whole-file SHA는 승인된 scratch proposal과 같고 다음 AST 범위만 바뀌었다.

| 도구 | 적용된 제한 AST delta | 적용 source SHA256 |
|---|---|---|
| card-menu | `compare_guards` + `overflow_guard_prefix` | `1dd4552147c45a34154bc6f48b2053d5a216f3bc065b6ad276ece0b51aa6dd37` |
| scene-core | `GUARD_ERRORS['guard-cond-index-negative-8000']` value 하나 | `f5c18f3518d0deae8c41fedff5c783b3ff5ffa20c860476e91c348511d9f7cd1` |
| script-placement | `negatives` + `h1_outside_prefix` | `d77b432ace5e053b75c982f2b25e72bc3571cadce89f99ead949abd8ae0eddd5` |
| stage-area | `reject_one` + `superseded_stage_area_neighbour_prefix` | `29df79b716136fa3453304d88529c939aaa11de2ea471945997aaa647f255fa9` |

나머지 기존 definition과 module top-level AST는 그대로다. scene-core는 dictionary의 key 및 나머지 value도 그대로다. 새 helper는 해당 수정 함수에서만 한 번 호출되며 decorator/default argument/annotation의 import-time 평가가 없다. 적용 후 직접 검사한 결과는 `build/g3_acceptance/four-applied-delta-review.json`에 기록했다.

## 네 기대 수정의 원본·검증 범위

### Card-menu

`guard-overflow-rts-unsupported-target`의 이전 unsupported 요구는 H1의 새 executor와 맞지 않는다. fixed ROM CPU 주소/파일 offset `0x1000` WORD `4e75 RTS`를 실행하면 기존 stop `0xa370`에 도달한다. 새 helper는 선언된 전체 guard의 `a0a0` 시작과 실제 직전 C++ 출력의 `a0c2` 시작을 각각 fresh native CPU로 실행한다. trace에 `1000`이 있고 final stop이 `a370`이며 16R/PC/전체 RAM/PVC/bank/순서 있는 ports/external read 수(0)가 C++와 같아야 한다. `a0c2`의 재실행 tuple은 원래 guard API의 실제 결과와도 정확히 같아야 한다. native SR는 읽지 않는다. 이전 native fault와 rollback의 동등성은 주장하지 않는다.

### Scene-core

`guard-cond-index-negative-8000`는 계속 checked rejection이다. target CPU/고정 ROM offset `0x122d4`는 H4 cell `0x120c0 + 532`의 내부(532 mod 18 = 10)다. 실제 fresh archived-phase probe의 오류는 `unsupported animation frame head h4 PC`이며 전체 public rollback을 확인했다. 해당 key의 generic 기대만 이 정확한 오류로 바꾸고 다른 guard 값·key·검사 함수를 유지했다.

### Script-placement

원본 fixed CPU/file offset `3db2..3dca`는 MOVEQ/BTST/BEQ/MOVE.B/ADDQ/RTS 사슬이다. H1의 `3db2` 진입은 기존 declared stop `ff000`에 정상 복귀하므로 이전 unsupported negative를 positive로 전환한다. `3db4`는 H1 block 내부 진입으로 정확한 H1 오류와 full rollback을 요구한다.

새 helper는 `3db2` bytes `70000839000300104d91670000044e75103900104d9052404e75`를 확인하고 actual input에서 fresh native 전체 복귀 사슬을 재생한다. final PC/16R/RAM/14개 순서 있는 PVC writes를 비교한다. 초기 PVC 8192바이트를 정확히 주입하며, raw native ff8/ff9 저장 차이를 감추지 않고 기존 Python device fold로 full 8192 PVC 및 bank를 비교한다. raw native는 ff8/ff9 밖의 동일성을 요구하고 각 write의 원본 PC/bytes를 기록한다. `3db2`는 `API_only_control=False`다. native CCR 값의 동등성은 주장하지 않는다.

AST-recursive local imports(PVC banks→scheduler→address_map/disassemble_program), Unicorn Python wrappers와 실제 native library를 첫 native import/실행 전후 고정한다. scratch 검증은 357 negative(340 interior), 264 zero와 former controls(659 API calls)를 통과했다. 검증 source SHA `da7a33941cf4f69c57171d04224136f89ccc88facfadd4e8fa6f88f75aeeb51f`와 최종 적용 bytes 사이의 차이는 함수 내부 comment 한 줄뿐이다. 그 comment를 되돌리면 이전 SHA가 정확히 재현되고 전체 AST가 같음을 확인했다. 이를 새 bytes의 scratch 재실행으로 주장하지 않는다.

### Stage-area

네 exact label/PC(`0b481e`, `0b4a2a`, `046f52`, `01bdde`)에서만 이전 generic 기대를 `animation machine external read queue empty`로 바꾼다. 이전 기대와 label의 PC를 검사하고 실제 실패의 전체 public rollback을 요구한다.

원본 native/C++ prefix를 H1 public block `ea4`까지 비교하고 첫 외부 WORD read가 CPU/file offset `eaa`, 주소 `3c0006`임을 확인한다. block bytes는 `08ed0007801b3039003c0006`다. 각 prefix의 16R/PC/RAM/PVC/bank/404 ordered ports/read-count 0이 같으며 이후 입력이나 완료 상태는 주입·비교하지 않는다. empty API queue는 native CPU fault가 아니다. 따라서 prefix 실행은 native 증거를 갖고, 실패의 rollback은 API-only claim이다(`API_only=False`, `boundary_rollback_API_only=True`).

immutable observer source, manifest/Unicorn wrappers/native library의 전후 SHA를 고정한다. local transitives는 outer report의 기존 dependency before/after audit에도 포함된다. scratch 719 negative, 10 consumer control, 462 zero 및 RNG/F3b controls의 검증 source SHA는 `137e6053d2c4c5cf56b80c266b3e19cff36012c51251e607609e79d6ce0ca946`다. 최종 적용은 return metadata만 `native_PC_hook_count=len(trace), stopped_PC_included=True`로 고쳤다. stop PC 방문을 실행된 instruction으로 세지 않는다. 이 두 field 변경을 되돌리면 이전 검증 SHA가 정확히 재현됨을 확인했고 새 bytes의 scratch 재실행으로 표현하지 않는다.

## 호출 경로와 source-as-data 영향

공식 35개 root의 recursive local imports, module/from-import aliases, attribute reference 및 callsite를 AST로 읽었다. 변경된 실행 함수/값을 호출하거나 쓰는 root는 해당 네 공식 tool뿐이다.

| 변경 대상 | 유일한 own 실행 경로(baseline line) | 다른 root가 실제로 사용하는 경로 |
|---|---|---|
| card-menu `compare_guards` | own `main`:627 | glyph prefix(card_child/input/close/open), audit/compare(open), start_of_row/apply_changes(open/save)와 상수. 이들은 변경되지 않음 |
| scene-core guard value | own `compare_guards`:757(value),770(keys); own `run`:941 | input/scene_update/script_placement의 carry/merge/check/PVC/scene-input APIs와 상수. dictionary 참조·alias 없음 |
| script-placement `negatives` | own `run`:975 | 다른 root에 module import·attribute/from-import alias 없음 |
| stage-area `reject_one` | own negatives/parallel 실행; own `run`:1264 | 다른 root에 module import·attribute/from-import alias 없음 |

보수적인 import graph와 실제 함수 실행은 구분했다. card-menu는 자신을 포함한 21개 root의 AST import closure에 나타나지만 대부분 실행되지 않는 card_child local import를 통해 포함된다. 이것을 guard 실행의 증거로 취급하지 않는다. 새 helper 정의는 import 시 native 실행이나 global mutation을 하지 않는다.

파일을 데이터로 읽는 경로도 별도 확인했다. area_clear/stage_area/stage_event/stage_event_ops/scheduler의 source inventory는 `MAIN_ROOT=/Users/start/Workspce/metalslug`의 원래 checkout을 읽는다. 실제 resolve가 이번 worktree와 다르고 그 checkout은 변경하지 않았다. remaining input verifier의 local source inventory는 `49b0c` matching line만 읽는다. 네 baseline·applied source 모두 해당 line이 없으므로 이 결과도 바뀌지 않는다. script-placement의 자체 local source inventory는 해당 공식 main의 재실행으로 새 metadata를 확보한다.

## 실제 historical report pin 영향

원래 성공한 31개 report의 파일 SHA가 original35 manifest 값과 같음을 확인했다. 모든 `inputs`를 실제 파일과 대조했다(282개 unique input, 미확인/누락 path 0). 정확한 분류는 다음과 같다.

- **24개:** 모든 current input pin이 원래 report와 같다.
- **7개:** 나머지 pin은 같고 아래 unused module delta의 whole-file pin만 이전 값이다. 원래 report와 pin을 유지한 행동 동등성 overlay 대상이다.
  - card-menu old pin: card_child, card_menu_open, card_menu_input, card_menu_close, card_menu_save.
  - scene-core old pin: input, scene_update.
- 원래 성공 report에는 script-placement/stage-area pin 차이가 없다.

`build/g3_acceptance/old31-report-pin-impact.json` SHA256 `556302befb254cd5e4d67f761e4fdaad7aad43a2bc3e697357c95baa14e6965a`에 각 report SHA, old/current module pin, `current_byte_identity=false` 및 전체 input 비교를 보존했다. 31개 모두 pin이 바뀐 것으로 표현하지 않는다. 7개는 현재 module bytes와 같지 않지만 검사되는 실행 경로는 동일하다. 과거 pin을 새 hash로 덮어쓰지 않는다.

## 공식 4개 재실행의 최종 확인

공식 4개 main 전체 재실행은 모두 **종료 0**이며 `failure=null`, `ROM_unchanged=true`다. 각 report 및 default/copy/log SHA, 실제 적용된 self-source pin, receipt의 before/after 입력 map 동일성을 확인했다. 네 report의 모든 input을 실제 파일과 다시 해시 비교했고, 새 helper의 native source/wrapper/library/manifest pin과 정확한 proof metadata도 확인했다.

| 공식 재실행 | report SHA256 | 현재 input pin 직접 확인 |
|---|---|---|
| card-menu | `94d0c7ed6bc0f1806f97fd53089b5ffc7d1d734235e0580098329acd08968f68` | 150 |
| scene-core | `143691f1bfec4f15db1375c7f7db997f599e156e5c968ec4e37d311aac795d49` | 157 |
| script-placement | `32c0e17f86e9d9417b87f80cfd36da203532b654c8d65a765c7c66ac4e96f1e3` | 159 |
| stage-area | `cce2ed244270f8ea0b054f698252fea4d17f131a5e8472fe5b5f86a1d1aa03b4` | 147 |

각 actual report는 `artifacts/animation_machine_{card_menu,scene_core,script_placement,stage_area}_execution/verification.json`, 보존 copy·실행 receipt는 `build/legacy_acceptance/reruns/`에 있다. card-menu의 actual 2개 native prefix 및 `1000 RTS→a370`, scene-core의 phase/whole_step 정확 H4 오류와 rollback, script-placement의 `3db2` full prefix·14 PVC writes·`3db4` 정확 오류, stage-area의 네 prefix `ea4` 및 first read `eaa/3c0006.W`와 API-only boundary rollback이 최종 report에 포함된 것을 확인했다.

독립 수용 artifact `build/g3_acceptance/official-four-independent-review.json` SHA256 **`0d31bf9b96e4c677675100e9f169f75a1f64e234b697b0a3486b2bcf9981f962`**는 `all_four_pass=true`, `pending=[]`, historical 31개 report hash 전부 보존, **24 current-pin + 7 reviewed-delta**를 기록한다. 마지막 확인에서도 기존 31개 report와 old pin은 수정되지 않았다. 최종 회귀 manifest는 이 evidence를 함께 연결한다.

수용 결론은 **4개 fresh full main + 24개 current-pin 기존 성공 + 7개 unused-source-delta 동등성을 독립 검토한 기존 성공**이다. 전체 게임 재구성 완료나 새 bytes로 수행한 35개 fresh run을 주장하지 않는다.
