# G3 N03–N16a 공개 C++ API 실행 검증

대상은 `engine/src/animation_machine_objects_{n03..n16}.cpp`와 공개 `run_animation_machine` API다. 검증 도구는 `tools/verify_animation_machine_objects_g3.py`이며 G2 검증기를 읽기 전용 라이브러리로 재사용한다. ROM 원본, 관측 도구와 계약은 수정하지 않는다. ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다.

## 입력과 재현

관측 `artifacts/animation_machine_objects_g3_native/observation.json` SHA256 `5bab5b216f7e3af4870544bf5f4467ec0507e836fe7def10bda1c957c816849f`, typed fixture SHA256 `37a7762b9ac9d6554851be6d9327c1bb73f6827e0dec371e8f250dbb45c6c437`를 고정한다. 관측 기록에 포함된 계약·도구 SHA도 검사한다. 모든 native 파일, 전체 C++ source/header, Makefile, import된 native 도구(전이 `disassemble_program.py` 포함), G2/G3 검증기, runtime program resource, decrypted program manifest를 해시로 묶고 실행 전후 동일성을 검사한다. 실제 재생성에 읽히는 scheduler/RNG 관측, stage_entry_body 관측과 142개 seed RAM, F3 계약도 전후 고정한다. 로드된 Python module 파일·Python 실행 파일과 실제 Unicorn/Capstone dylib 해시·버전을 고정한다. 원 관측에 Unicorn library SHA가 없으므로 원 관측 당시 바이너리와 같은 내용이라는 주장은 하지 않는다(version 2.1.4 일치와 현재 실행 전후 동일성만 확인). 생산·진단 바이너리와 생성한 harness source, 실제 clang++ 경로·해시·버전도 전후 검사한다. ROM은 해시와 stat을 전후 검사한다.

```sh
.venv/bin/python tools/verify_animation_machine_objects_g3.py --workers 3 \
  --out artifacts/animation_machine_objects_g3_execution_repeat \
  --scratch build/g3_acceptance_repeat
```

출력은 실제 로컬 디렉터리 `artifacts/animation_machine_objects_g3_execution`, 빌드·배치 임시 상태는 `build/g3_acceptance`다. 출력 경로에서 lexical `..`를 디렉터리 생성 전에 거부하고, 모든 경로 구성요소와 생성할 파일의 기존 symlink를 거부한다. 따라서 공유 관측·추출 경로로 쓰지 않는다. parent traversal·절대 외부 경로·디렉터리 symlink·파일 symlink 4개 부정 검증은 외부 파일/디렉터리를 만들지 않고 거부를 확인한다. `--cases`, `--fixture-limit`, `--stages`는 개발용이며 전체 인수를 만족하지 않으면 `complete_requested_matrix=false`, `accepted=false`다. 명령의 `_repeat` 출력·scratch는 재현용 새 경로 예시다. 이미 존재하는 `verification.json`을 덮어쓰지 않으므로 매 실행에서 사용하지 않은 `--out`을 지정한다. `--reuse-build`는 모든 입력과 바이너리 해시가 이전 build freeze와 같을 때만 허용한다.

## 비교 의미

[F] 자연 290 case의 30,632 node를 scheduler 원기록에서 다시 생성한다. entry/exit, frame·sequence·callback·depth·partial, 저장된 capture 상태, guard와 전체 case digest를 검사하고 각 native piece/phase를 공개 C++ API로 실행한다. 64KiB RAM, 16 registers(따라서 A7 포함), PC, bank base, 8KiB PVC 이미지와 ff8/ff9, 순서 있는 포트, external read 수, 대기·해제 목록을 비교한다. Known C는 native MOVE SR probe의 C 비트와 비교한다. typed 2,459 fixture는 저장된 시작 상태에서 native dump·final·ports를 재생성하고 reference/continuous/split 일치를 확인한다.

[F] 실제 실행 체인은 직전 C++ 출력만 사용한다. 생산 API가 아직 지원하지 않는 외부 callee를 checked 오류로 거부하면 다음 phase는 native 경계 상태에서 선언 재진입한다. `phase_real`과 `phase_declared`를 따로 센다. `match-partial`은 전체 node의 연속 실행 동등성 주장이 아니다. sound/sprite 대기 해제 쓰기도 선언 모델이다. BIOS, 자연 IRQ·scheduler를 주장하지 않는다.

[F] 주소 마스크 차이 경계를 제외한 checked 오류는 생산 API의 전체 public 출력 보존, 진단 복사본의 같은 오류 문자열, native가 진단 거부 PC에 실제 도달했다는 증거를 요구한다. 주소 마스크 차이 경계에서는 마지막 비교 가능한 block까지의 prefix만 비교하고 이후의 C++ checked 오류와 rollback을 별도 검증한다. native fault 이후의 진단 PC 도달은 주장하지 않는다. 진단 복사본은 dispatcher PC만 기록하며 생산 API가 판정 기준이다. 단일 block guard probe에서도 generic unsupported 오류를 자동 허용하지 않고 같은 증거와 분류를 요구한다. N13 DIVU zero는 native exception number 5를 별도로 확인한다. native 24bit 주소 마스크 부재는 실행 동등성으로 세지 않는다.

[F] 모든 계약 block 시작에서 C_in 0/1과 Unknown을 탐침한다. 소비자 fixture는 Unknown 오류 문자열과 진단 PC가 정확히 소비자 진입 PC인지 검사한다. API 부정 시험은 모든 interior PC×3 carry, 모든 홀수 PC×2 방식, 모든 block 시작×3 carry의 zero-step, 비라우팅 RAM PC×3 carry를 포함한다. 비교기의 오류 주입은 RAM, register, PC, PVC, bank, ordered ports, external reads, Known carry, waits 각각을 독립 변조해 모두 거부되는지 확인한다.

## 관측 discrepancy와 원본 근거

[F] immutable native 관측의 21 discrepancy를 그대로 보고한다. CFG leader 6, consumer parser/model 3, caller N 1, compressed block wording 8, outgoing call-site 2, producer/caller 범위 1이다. 자동 decoder/parser 차이 자체로 C++ 실행 불일치를 선언하거나 계약을 변경하지 않는다.

메인의 원본 확인(2026-10-14):

- CPU 주소 `0x710c6` / 복호화 P ROM 파일 offset `0x710c6`(고정 창, bank 없음): bytes `2d400064` = `MOVE.L D0,64(A6)`; `0x710ca` `4a80` = `TST.L D0`; `0x710cc` `6a000004` = `BPL 0x710d2`. N15 계약 상세와 C++는 일치한다. grouped `710a0`/`710c6` prose에서 observer parser가 `TST.W/BEQ`를 잘못 연결한 discrepancy다.
- CPU 주소 `0x494b4` / 파일 offset `0x494b4`(고정 창): `LEA 100cb8,A0`; `0x494ba` `003c0001` = `ORI #1,CCR`; RTS. 외부 caller `0x77604` / 파일 offset `0x77604` `64000008` = `BCC 0x7760e`가 carry를 소비한다. N08 계약은 유닛 내부 consumer가 없고 반환 C를 외부 caller가 읽는다고 명시한다. 관측의 expected `-`는 외부 consumer 추출 범위의 차이다.

[F] 실행 검증에서 추가로 확인한 관측·계약 경계:

- `71c86`은 N15 계약 결정 3대로 N04 내부 `71c98`의 TST/BNE를 함께 실행하므로 C++ phase와 block probe의 stop은 `71ca0` 또는 `71ccc`다. native piece의 유닛 경계 `71c98`은 독립 C++ block stop이 아니다. 실제 chain을 합쳐 비교한다.
- `792ac`/`7961e` EORI CCR는 RAM·register·PC가 같아도 출력 C를 뒤집는다. carry 자체의 의존성을 검증하고 Unknown 오류를 정확한 진입 PC에서 확인한다.
- 관측에서 consumer로 이름 붙인 `c637c` fixture 4개는 N03 계약 결정 3의 pass-through다(BCC 대상 `c6380` = fall-through). Unknown C로 `c6380`까지 성공하고 전체 상태·포트·read 수와 Unknown C 보존을 확인한다. 일반 consumer fixture 540개는 정확한 오류를 요구한다.
- pinned fixture **1278**(`5b326`, CCR N=0, D1.W=`3733`)와 **1281**(`bddb4`, CCR N=1, D2.W=`001a`)만 계약의 직접 진입 precondition을 어긴다. N13 계약 결정 4는 N=`NOT bit15(D1.W)`, N05 결정 4는 N=`bit15(D2.W)`를 요구한다. 원본 입력과 실제 diff를 보존하고 `excluded:contradictory-caller-N`, `no_execution_equivalence=true`로 표기한다. 올바른 동일 register/RAM counterpart **1279**/**1280**은 정상 실행 비교를 통과해야 한다. 입력을 수정해 원본 관측이 일치했다고 주장하지 않는다.
- 외부 callee 거부 `unsupported animation command or dispatch alignment`는 진단 PC `49ffe`, `unsupported sprite callback target`은 `cd58`일 때만 reviewed boundary로 허용한다. 외부 N19의 `objects n19 caller requires known carry`는 N19 계약 consumer **b1fdc BCS**에서만 허용한다. native의 도달, 같은 진단 오류, 전체 rollback에 더해 실제 C++ prefix를 `b1fdc`까지 다시 실행하여 전체 상태·포트·read 수를 비교하고 소비자 입력 C가 Unknown임을 기록한다. 이후는 checked callee에 따른 선언 재진입이며 whole-through 동등성이 아니다. N19 계약도 입력 SHA에 포함한다.

[U] 나머지 parser/CFG discrepancy는 pinned native 기록에서 유지된다. 성공한 executable differential만으로 문구의 분석 완료를 선언하지 않는다.

## 실행 결과

최초 전체 실행(`verification.failed.json`, SHA256 `f9bf6114488225fc1f6a125ee4c3670b8a1da78db91bd7af4b110edb63883c87`)은 fixture 53개와 probe 3개를 DIFF로 검출했다. 메인의 원본·계약 리뷰에 따라 위 비교 경계와 carry 의존성, 직접 진입 precondition을 수정했으며 C++ 실행부와 원본 관측 입력은 수정하지 않았다. 경로 보호 수정 전 전체 재실행은 35개 check 모두 true(SHA256 `07c296a96ac33b2a71296d2aef7aae4fb6b6db289fd54cddf7a569f05e0540a7`)였고, 최종 source identity는 경로 보호 수정 후 다시 전체 실행해 확인한다.

최종 전체 실행(2026-10-14)은 종료 **0**, `accepted=true`, **39개 check 전부 true**다. `verification.json` SHA256은 **`2c2ac4ae6438eb86dc5286a351fea146832e73a4f1cfe4ffedc2b997a3c42419`**, 검증기 SHA256은 `ab7bc23befbdd8855b612fa17e850a9f01f2369243aacd35afc9cae8d3e5ec6e`다. 실제 명령은 `.venv/bin/python tools/verify_animation_machine_objects_g3.py --workers 3`, 소요 315.52초, build/diagnostic compile 종료 0(생산 빌드 경고·출력 없음)이다. 최종 log는 `build/g3_acceptance/full-release.log`다. 실행 당시 입력 770개의 해시, generated harness, 바이너리, compiler·native oracle·decoder·ROM 전후 불변을 보고서에 기록했다.

| 항목 | 최종 결과 |
|---|---|
| 자연 matrix | 290 case / 30,632 node, 원기록 재생성 전부 일치. match **30,630**, 정확한 `stage area RNG pointer outside work RAM` guard **2**, DIFF **0** |
| 자연 unit pieces | **133,378/133,378** 검증. 전체 phase **262,522**, actual phase **262,522**, declared reentry **0**, blocked phase **0** |
| 자연 carry | Known C **112,306**, 불일치 **0**. Unknown **180,844**는 값의 동등성 주장 없음 |
| 자연 continuous/chain | continuous check **30,634**(guard·부분 연속 검사 포함), cont-vs-chain **30,632**, 불일치 **0** |
| typed | **2,459** 재생성 모두 일치, DIFF **0**. match **1,572**, match-partial **3**, contradictory N 입력 제외 **2**(실행 동등성 주장 없음), 나머지는 아래 checked guard/boundary |
| typed phase/carry | actual phase **15,592**, declared reentry **3**, blocked phase **5**. Known C **6,305**, 불일치 **0** |
| through | **312** 재생성 모두 일치. match-partial **256**, address-mask divergence **31**, checked guard/boundary **25**. whole-through match 주장 없음. **63** fixture에 N19 외부 carry 경계의 정확한 PC·prefix·입력 C 증거가 포함됨 |
| 모든 block probe | **2,203/2,203** 통과. 출력 carry class: preserve **822**, clear **36**, set **26**, unknown **1,315**, EORI invert **2**, native guard로 class 없음 **2**. carry 의존 probe **135**(Cout-only EORI 포함) |
| consumer fixture | 실제 consumer **540**는 exact Unknown 오류, pass-through c637c **4**는 Unknown 성공과 전체 상태·C 보존. 모두 통과 |
| API 부정 시험 | **56,108** 호출, 정확 오류·전체 rollback 또는 zero-step 성공, DIFF **0** |
| 오류 주입/출력 경로 | 상태·포트·read·carry·wait 독립 변조 **9개** 모두 거부, 출력 경로 변조 **4개** 모두 거부 |

Typed checked 분류(합계가 2,459이며 match/partial/제외와 구분): bank-read-outside-ROM **230**, odd-read **222**, odd-write **22**, rom-write **94**(write-device 45 + RNG pointer 49), DIVU exception 5→정확한 zero-divisor 오류 **20**, 기타 native CPU exception→unsupported machine **6**, read-unmapped **20**, write-unmapped **2**, checked-callee **46**, unknown-carry boundary **22**, interior landing **1**, native address-mask divergence **197**. 후자의 fault 이후 실행과 제외된 N fixture 2개는 실행 동등성으로 세지 않는다.

이 결과는 G3 N03–N16a matrix의 검증 결과다. 전체 게임 재구성의 완료나 진행률을 나타내지 않는다.
