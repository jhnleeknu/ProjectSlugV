# 477e4/477ee stage entry와 사운드 재개

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 고정 ROM CPU 주소는 같은 파일 오프셋이다. RAM은 CPU `100000..10ffff`에 매핑된다. `artifacts/stage_entry/inventory.asm`은 명령 목록 근거이며 의미 계약은 메인의 원본 제어 흐름 검토와 독립 실행 비교로 확정한다. 원본 코드 수정이나 callback/BIOS stub을 사용하지 않는다.

## 지원하는 실행 경계

`step_stage_entry`는 실제 `477e4`에서 시작하는 초기화 포함 호출과, 초기화가 끝난 실제 `477ee`에서 시작하는 호출을 구분한다. `477e4`는 null-script scene initializer를 먼저 실행한다. `477ee` 진입은 이 접두부를 실행하지 않는다. 일반 nonzero-script 초기화나 dispatch 이후 stage body는 이 API 범위가 아니다.

phase0에서 객체+7c/+7d에 LIVE RAMd680/d681의 stage/area byte를 복사하고 stage catalog를 조회한다. Stage byte가 19 이상이면 조회 group0으로 clamp되지만 객체에 저장한 원래 stage byte는 유지한다. Area가 범위를 벗어나면 객체 area를0으로 돌려 재조회한다. 성공하면 record payload의 원본 CPU 주소를 객체+76에 저장하고 group header의 상위 byte를 RAMd684에 반영한다.

원본에는 59개의 record와 비어 있는 7개 group이 있다. Empty group은 area0으로 되돌아가도 pointer가0이라 반복하는 native 경로다. 지원 API는 조회를 256회로 제한하여 오류로 반환한다. 이는 native TRAP을 재현한 것이 아니라 끝나지 않는 경로에 대한 API 오류다.

뒤이어 원본 순서로 객체 active flag, RAM0965/0967/dd1f/7def/d683 등을 변경한다. Callback이 `270e`가 아닌 객체는 callback0도 active로 취급한다. LIVE 객체 record pointer에서 music word(+10)를 읽어 RAMd686.word와 비교하고, 다르면 `19c1`은 pair saved `38`, 그 밖에는 `80`을 `3d58` producer에 전달한다.

## Pending과 LIVE 재조회

`StageEntryState`는 next_pc, 전체 D0/D1/D3/A6, phase와 `SoundPairState`를 담는다. Phase1은 next_pc `3aea`의 사운드 대기이며 원본 saved byte와 captured queue tail/next를 모두 승계한다. 재개는 sound producer만 실행한다. Scene 초기화, stage/area 선택과 prefix의 RAM 변경을 반복하지 않는다. 반복 대기는 포트0개이며 RAM/state가 그대로다.

사운드가 완료되면 RAMd68c.word를1로 하고 screen `ca9e`를 실행한다. 이 screen 구간의 ordered ports는 773개다. 전체 `477e4` 호출에는 별도 scene initializer 포트도 앞서 포함될 수 있다. 이후 객체+76의 record pointer를 **LIVE 값으로 다시** 읽어 selector를 얻는다. 따라서 대기 사이 pointer 변경은 후반 selector 조회에 반영되며 초기 stage query를 반복한 결과로 대체하지 않는다.

Selector는 0,4,8,0c,10,14를 지원하며 각각 `478c4,478f0,4791c,47934,4794c,47964`로 dispatch한다. Canonical 59 records에서 도달하는 selector는 이 중 네 종류다. 나머지 두 target의 존재와 synthetic D0에 의한 분기 관측을 실제 canonical resource 경로 도달로 해석하지 않는다. Phase2는 해당 target의 첫 명령 이전에서 끝나며 body나 RTS를 실행하지 않는다.

## Transaction과 CLI

RAM은 정확히65536 byte, A6는 짝수 RAM CPU 주소이며 c4-byte 객체 span이 필요하다. Phase0은 idle sound, phase1은 일치하는 전체 Dregs와 유효한 sound pending을 요구한다. 완료 phase2를 다시 호출하면 오류다. Catalog validation, late LIVE pointer 조회 또는 selector 검증이 실패해도 RAM, state와 기존 포트 vector 모두 보존한다. CLI 역시 API가 성공하기 전에 출력 파일을 열지 않고 입력/출력 및 실제 catalog resource 경로의 canonical/symlink/hardlink alias를 거부한다.

```
build/step_stage_entry PC PHASE D0 D1 D3 A6 PAIR_PHASE SAVED COMMAND TAIL NEXT \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS CATALOG_DIR TABLES_MS5D
make -j2 build/step_stage_entry build/stage_entry_test
build/stage_entry_test
.venv/bin/python tools/verify_stage_initialization.py
```

JSON은 next_pc,phase,d0,d1,d3,a6,writes와 전체 sound pending 객체를 반환한다. 포트 파일은 size8/addressBE32/valueBE32의 9-byte ordered record다. 전체 RAM과 JSON state를 함께 승계해야 한다. D2/D4-D7, 다른 Aregs, CCR, native stack, scheduler와 timing은 반환 계약 밖이다.

## 검증 기록

Targeted build와 단위 시험이 통과했다. `make -j3 all test`는 exit0이며 Python95개와 C++90개 실행을 통과했고 컴파일 경고0개다. 로그는 `artifacts/stage_entry_build_test.log`다. 독립 native verifier 최종 실행은 526 native boundary, 81 오류 입력 사례, 401942 ordered port 쓰기와 8 actual CLI carry sequence를 통과했다. 59 canonical records 전체와 실제 `477e4` initializer 포함 호출 8개, 대기 중 LIVE record pointer 변경, A6=`10d608`의 객체 필드 overlap을 비교했다. 전체 RAM/D0/D1/D3/A6/sound pending/포트 순서가 일치했고 MMIO 읽기는0개다.

Canonical records의 도달 target은 `478c4,478f0,47934,47964` 네 개다. `4791c`와 `4794c`는 selector8/10의 synthetic register fixture로 indexed BRA map만 검증했으며 canonical catalog 도달로 계산하지 않았다. 비어 있는7개 group도 bounded native 반복 관측과 API 오류 검증으로 따로 기록했다.

최종 보고서 `artifacts/stage_initialization/verification.json` SHA256은 `6ba246a33c26b91b841443ed3f26a023eb5abd150dd4f16e2b7626d775bd31fa`다. 실행 파일 SHA256 `82b2d08457372d9ce3f8a29e960fa58b1c5686edb917d3232f5197d7ae7c8234`는 검증 시작과 종료에 동일했다. 원본 코드 수정은 없었다. Carry sequence의 head release와 일부 LIVE pointer 변경은 host 입력으로 주어진 범위이며, 이를 scheduler나 실제 IRQ에 의한 소비자 실행의 검증으로 확대하지 않는다.
