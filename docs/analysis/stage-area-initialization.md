# Stage area 초기화의 selector 리소스와 실행 경계

## 원본과 selector 조회 창

Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 source CPU 주소는 첫1MiB 고정 ROM이며 canonical 파일의 같은 오프셋이다. RAM/MMIO와 banked 주소는 별도로 기록한다. 주소·상수는16진수이며 바이트·반복·검증 개수는10진수다.

`tools/pack_stage_selector_lookup.py`는 `[4e4d2,4e552)` 원시128바이트를 보존한다. 메인이 확인한4e666은 RAM10dd2a/10dd2b selector bit7가 꺼졌을 때4e4d2+signed D0.word의 byte를 읽고 RAM10dd1e의 해당 bit(mod8)를 지운 뒤 selector를ff로 만든다. D0는 byte 연산이어서 bits8..15를 자동으로 지우지 않는다. 이 창은0..127 byte offset에 필요한 addressable 원시 범위이며 **논리128-entry 테이블이라는 주장은 하지 않는다.** Bits8..15가 비영이면 더 넓은 signed-index 창이 필요할 수 있다. 실제 caller의 앞선47594 suffix는 D0 전체0을 반환하므로 이 경로의 selector byte0..127은 보존 창에 포함된다. 임의 D0.word의 signed index가 이 창에 포함되거나 자연 실행에 사용된다고 일반화하지 않는다.

Lookup 명령 evidence는4e666..4e68e를 verified source와 bounded decoder로 확인하고 pin한다. 첫 selector BSR와 둘째 selector fallthrough, byte read·BCLR·ff 저장·RTS를 manifest에 원시 명령으로 기록한다. 이 추출 자체를 전체479d0 body 실행 분석이나 natural selector reachability의 증거로 취급하지 않는다.

## MS5D와 재생성

기존 MS5D v1 kind1을 사용하며 stable ID는 `stage-selector-lookup:0004e4d2`다. 출력은 `extracted/runtime/stage_selector_lookup.ms5d`와 `stage_selector_lookup.manifest.json`이다. Header32바이트와 payload128바이트를 합친 container는160바이트다. Metadata는 source CPU/ROM 주소·exclusive end·source/payload/container SHA·조회 표현과 명령 evidence·미확인 범위를 포함한다. 새 schema나 이미지 리소스를 만들지 않는다.

Payload SHA256은 `aab36d4692c572b94b43fb395e58d13c8b39e8ed0448a91b8a06e52a919cbf86`, container SHA256은 `59541b176a2819fd0f7aefbaa481d309c9e06e1fb4b722df52fe28e3285d6046`다. 실제 packer는 전체8MiB 길이·canonical SHA·instruction evidence·raw payload SHA를 확인하고 MS5D header/CRC/payload roundtrip을 검사했다. 원본과 추출 게임 데이터는 Git에 추가하지 않는다.

```text
.venv/bin/python tools/pack_stage_selector_lookup.py
.venv/bin/python -m unittest tools.tests.test_stage_selector_lookup_resource -v
```

합성 테스트7개가 source/evidence truncation, raw payload·source hash 변경, header schema·CRC·정확한 길이, CRC를 다시 맞춘 payload 변경, 주변 byte가 payload에 포함되지 않는 조건을 확인했고 모두 통과했다. Tracked 테스트는 ROM 창을 포함하지 않고 합성 bytes로 pin을 대체한다. 소비는 기존 `FixedDataResource`/`load_fixed_data_resource` 포맷을 사용하며 실제 CLI 로더는 아래 native 비교에서 세 MS5D를 읽었으며 selector container hash가 위 값과 일치했다. API는 사용되는 리소스만 검증하지만 CLI는 세 파일을 항상 로드한다.

## API와 continuation 계약

`engine/include/ms5/stage_area_initialization.h`와 `engine/src/stage_area_initialization.cpp`의 `step_stage_area_initialization`은 RAM64KiB, game records·player lookup·selector lookup, 외부 status byte, `StageAreaInitializationState`, external read count를 받는다. 상태는 `next_pc`, full D0/D1/D3/A6, phase와 내부 `GameInitializationState`를 보존한다. A6는 짝수 CPU RAM 주소이며 전체c4바이트 object span이 RAM에 포함되어야 한다. CCR·다른 data/address registers·CPU stack은 공개 API 결과가 아니다.

Fresh phase0의 PC는479d0이고 내부 initialization은 기본 idle 상태여야 한다. LIVE A6+7d area byte가0이면47594에서 `initialize_game`을 시작한다. 이 직접 진입은47570 prefix를 반복하지 않으며 초기 D0 상위16비트를 prelude의 word/byte 동작에 전달한다. Sound queue가 대기하면 outer phase1/PC3aea로 full D0/D1/D3와 nested pending 상태를 반환한다. Phase1은 내부 PC·phase·레지스터의 일치를 검증하고 저장된 initialization만 재개한다. 따라서 대기 중 host가 area byte를 바꾸어도 처음 선택한 branch를 다시 읽지 않는다.

Area가 비영이면479ee의 `resume_stage_area`로 현재 player 상태를 RAM에 snapshot한 뒤475ca 공통 reset을 실행한다. 이는 과거 상태 복구가 아니다. First-area initialization이 끝났을 때 LIVE RAMd684가0이면4e666 selector release를 실행한다. 이어 양쪽 branch 공통으로 LIVE d684가0이면 d760a의 고정 word 저장과28ae object 할당을 실행한다. ddec/ddee/ddf0에는1/0108/01a0, ddf2/ddf4/ddf6에는0/0108/01a0, ddf8에는0096을 저장하고 callback d764a를 할당 대상에 설치한다. 여기서 callback 본문을 실행하지 않는다. d684 gate는 할당 전에 읽으므로 allocator가 RAM alias를 통해 이후 값을 바꾸더라도 같은 호출에서 gate를 재평가하지 않는다.

마지막49c32/49c20 호출 두 번은 RAMd734/d738을0으로 만들고 D0 전체4를 남긴다. 완료 상태는 phase2/PC47a1c, D0=4/D1=0/D3=0이며 A6는 보존된다. Phase2를 다시 호출하면 오류다. 이 PC는 후속 body 실행 전 경계이고 native caller RTS가 아니다. 모든 성공 경로에서 MMIO write는 없으며 external status의 조건부 read 수만 반환한다.

함수는 candidate RAM/state/read count로 진행한다. 잘못된 RAM 크기·A6 span·continuation, 필요한 리소스 오류 또는 앞선 reset 이후의 늦은 selector/allocation 오류도 호출 전 RAM/state/external read count를 보존한다. 리소스 사용 조건은 first/nonfirst branch, active player source, selector bit7에 따라 달라진다. CLI는 별도로 모든 MS5D를 항상 읽고 path·inode alias와 parser 오류를 출력 저장 전에 거부한다.

## CLI와 검증

```text
build/step_stage_area_initialization --state PC D0 D1 D3 A6 PHASE [--init PC INNER_PHASE] [--word PHASE LOW CURSOR COMMAND TAIL NEXT] [--byte COMMAND TAIL NEXT] EXTERNAL INPUT_RAM OUTPUT_RAM RECORDS_MS5D PLAYER_LOOKUP_MS5D SELECTOR_LOOKUP_MS5D
.venv/bin/python tools/verify_stage_area_initialization.py
```

옵션은 positional 입력보다 앞에 두며 중복·누락 값을 거부한다. JSON은 `next_pc`, `phase`, `d0`, `d1`, `d3`, `a6`, `external_reads`, nested `initialization.returned/prelude`와 word/byte pending 상태를 반환한다. Phase1 재개 시 JSON의 RAM·full registers·pending을 다음 CLI 입력으로 전달한다. 파일 output에는 RAM만 저장하고 port 파일은 만들지 않는다.

최종 `artifacts/stage_area_initialization/verification.json` SHA256은 `76e22c1c64acba38eecb095c5d2e989b17079dd58be3685a4e5d0bf6b4712778`다. 검증 session15903은 exit0으로453 native 비교와47 negative 검사를 통과했다. 전체 RAM/full D0/D1/D3/A6/pending이 일치했으며 MMIO write0, 조건부 external read16이었다. 원본 first1MiB 코드와 binary SHA256 `20027b3dae7563a3ecea431f866c99b02035427e0e1783e8ada3e148299ecf07`는 시작·끝에 같았다.

Selector byte256개를 검사했고 bit7 clear인 실제 lookup 주소0..127을 원본4e67c에서 모두 관측했다. Bit7 set은 lookup을 건너뛰었다. 이는 raw 창의 해당 주소 접근 검증이며 자연 selector 사용이나 논리128개 항목의 증명이 아니다. Snapshot/475ca nested callee, allocator 성공·빈 free-list 실패, A6와 heap alias 접근 순서 및 늦은 오류 rollback을 비교했다. Controlled free node10d682의 callback 저장이 gate를 읽은 뒤 d684를0에서76으로 바꾸는 case는 접근 순서 근거이며, 아래 suspended LIVE gate 변경과 구분한다.

실제 CLI 결과를 승계한16개 wait sequence는 네 `(prelude phase, word phase)` 종류 `(1,1)/(1,2)/(2,0)/(3,0)`을 모두 확인했다. 대기 중 host가 area를1로 바꾸어도 first initialization을 계속하고, 별도로 d684를0/1로 바꾼 결과는 suffix 후 LIVE gate에 반영됐다. Host가 sound head RAM4d74.word를 명시적으로 바꾸어 대기를 해제했다. 자연 IRQ 일정·hardware timing 검증이라고 주장하지 않는다. 추가2개는 실제479ba player CLI 결과를 같은 native CPU context에서479d0에 전달했고 A5/A7/SR/stack을 다시 초기화하지 않았다. 공개 API 밖의 registers는 native context fixture이며 C++ 반환값으로 주장하지 않는다.

`artifacts/stage_area_initialization_build_test.log`의 전체 `make -j3 all test`는 exit0, Python125/C++95, warning0으로 완료됐다. Native fixture의2790/3ef2/49a1a 설정·controlled source record와 valid stored pointer 조건은 report scope에 남긴다.

## Scene script 후속 근거와 남은 범위

`tools/inventory_scene_scripts.py`는 canonical stage catalog19그룹의59 record+2 long을 목록화했다. 고유 pointer42개 중0은4 record에서 사용하고, 나머지41개는 짝수 first1MiB 주소다. 이41개를 최대64KiB/32768 row로 구문 후보 decode했을 때 모두 negative word terminator에 도달했다. 총855 row와 op2c opaque inline block9개를 보존했다. Skip 크기는18 한 번과10 여덟 번으로 모두 양수 짝수였으며, 일반 입력의 음수 또는 홀수 skip은 각각 unsupported 상태로 종료한다. 홀수 skip은 다음 opcode word 주소를 홀수로 만드는 address-error 경계이므로 정상 구문으로 진행하지 않는다.

최종 `artifacts/scene_scripts/report.json` SHA256은 `21b526531039763241fb8a01bc240df657ce0a357e240d21fab50ec8a42dd1a6`, `inventory.asm` SHA256은 `23d4a57f0438acf043250e7cdbf36307210b28ccd8b3916ac49f8b4dfbd14137`다. 원본1a0b6 dispatcher, 1a0bc..1a26a handler 후보 창과1a26a..1a29c terminator/phase gate 창을 별도로 보존한다. Operand 길이는 메인이 확인한20개 opcode 계약을 사용하며 실행·도달 가능성·handler 부작용은 미증명이다. Inline block 자체는 opaque bytes다.

47a1c 이후 사운드 선택과47a94의 scene script 포인터 전달, 일반 nonzero script 경로·자연 callback/scheduler·stage gameplay는 아직 미완료다. 이 milestone은479d0→47a1c의 두 branch와 저장된 대기 재개 경계까지다.
