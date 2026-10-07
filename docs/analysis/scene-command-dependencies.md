# Scene command의 motion·간접 참조 리소스

이 문서는 `9c20d50`의18-handler/11-register milestone 기록이다. 수치·report hash는 당시 결과이고 같은 report 경로는 후속 검증에서 덮어쓸 수 있다. 현행19-handler/12-register API와 palette banked 의존성은 `scene-palette-command.md`를 참조한다.

## Source와 지원 경계

Baseline은 `e495c44`다. Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 전체8MiB 크기·해시를 packer에서 확인한다. 이 문서의 script/table/path CPU 주소는 첫1MiB 고정 ROM이며 같은 파일 offset이다. Table payload의 RAM pointer는 별도 CPU RAM 주소다. 주소·상수는16진수, 개수는10진수다.

이번 작업은 기존 `tools/pack_scene_scripts.py`에 원시 의존성 추출을 추가한다. 기존41 script/5486 payload byte와1a08e node pointer16바이트의 형식·주소·내용은 그대로 유지한다. 기존 MS5D v1 kind1을 쓰고 새 schema를 만들지 않는다. ROM/추출 게임 데이터는 Git에 추가하지 않는다.

## Path node table

`path_nodes.ms5d`는 `[1a0a6,1a0b6)`의16바이트를 그대로 담는다. Stable ID는 `scene-path-nodes:0001a0a6`이다.4 BE32 RAM pointer10d356/10d364/10d372/10d380의 원시 lookup table이며 node 구조의 크기나 일반 signed selector index 지원을 뜻하지 않는다.

Container48바이트 SHA256은 `f9aa6725468e8d223c04538ee29edc5902f0f1d7f08359a636cfaca6c0e01797`, payload SHA256은 `4b36e8780369efa2801aed19c9583fd210a6f76cfb56a731655c299ac2fb6f93`이다.

## Opcode00의 motion span

Canonical41 script의 opcode00 operand 마지막 BE32(A2)에 있는 비영 pointer를 중복 제거한다.39 occurrence가37개의 서로 다른 motion pointer를 참조한다. 각 pointer는 비영 짝수 fixed-ROM 주소여야 한다.

`motion_%06x.ms5d`는 pointer부터10바이트 일반 record를 따라가다가 record+2 BE16이ffff인 종결 record를 만나면 그 record의 처음4바이트까지만 포함한다. 일반 record는 전체10바이트가 있어야 한다. Source 첫1MiB 경계와 시작+65536바이트 scan bound를 동시에 적용한다. 첫 record는 종결이면 오류이고 offset0 word는 time,offset2 word는 type다. Type word는8c 이하이면서4의 배수여야 한다. 이는 메인이 확인한18c06 jump dispatch의 첫 진입 조건이다. **후속 type와 motion 효과는 원시 보존만 하며 미해석이다.** Terminator type word 자체를 opcode로 해석하지 않는다.

실제37 path 모두 첫 record는 nonterminal이며 첫 type은14/64/80이다.108개 일반 record와37개4-byte terminal prefix, 총1228 payload byte를 보존했다. Stable ID는 `scene-motion:%08x`이며 각 span의 종결 주소·첫 type·일반 record 수를 metadata에 기록한다. Logical motion 전체 동작이나 path의 자연 도달 완료를 주장하지 않는다.

## Opcode10의 간접 long

각 canonical opcode10 operand pointer에서4바이트 raw BE32를 `indirect_%06x.ms5d`로 추출한다. 비영 짝수 fixed-ROM pointer와 전체4바이트 span을 요구한다. Stable ID는 `scene-indirect:%08x`다. Canonical opcode 주소e6f34의 operand e6e9e는 long0을 담는다.

`indirect_0e6e9e.ms5d`의 container36바이트 SHA256은 `263726ab232c6e211da116feb2db645b0d8ffcc8013558211afa1b4ac89d7884`, payload4바이트 SHA256은 `df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119`이다. 그 값이 가리키는 추가 target을 추출하거나 handler 효과를 실행한 것은 아니다.

## Manifest와 재생성

출력 경로는 `extracted/runtime/scene_scripts/`다. 기존 manifest의 `dependencies`에 path table1개·motion37개·indirect1개, 총39개를 추가한다. 새 payload 합계1248바이트다. 각 entry는 file/id/source CPU·ROM offset/exclusive end/container·payload size와 SHA, script/command 주소·opcode·operand pointer references를 포함한다. Motion 뒤의 값·실행 의미는 scope에 미해석으로 남긴다. Table의 references는 empty이며 source 주소 자체가 확정 근거다.

```text
.venv/bin/python tools/pack_scene_scripts.py
.venv/bin/python -m unittest tools.tests.test_scene_script_pack -v
```

수정 후 재생성은 exit0, 기존 script 시험6개와 신규 motion 시험3개,총9개가 통과했다. 별도 직접 검사는 기존 script41개와 새 dependency39개의 MS5D header/CRC/source raw bytes·SHA roundtrip을 확인했다. 회귀 시험은 time1/type14 허용,timeffff/type64 및time3/type80 허용,time0/type90와unaligned type 거부,첫 terminal 거부,terminal4byte만 포함,후속type dead 원시 보존,missing terminal/truncation 거부를 확인했다. 첫 검사에서 time을 type로 오인한 오류를 메인 리뷰가 발견했고 offset2 type 검사로 수정했다. 모든 span을 준비·검증한 뒤 리소스 파일을 publish하므로 잘못된 source span에서 기존 script를 먼저 쓰지 않는다.

최종 manifest SHA256은 `9b6dcb8156fdd8a6cd368b8afe79f86b2b6908d0efc85d3f0d53b1d79c6dafed`이다. Packer 결과와 원시 검사는 추출 계약의 근거이며 실제 C++ CLI 로더와 handler native 비교는 아래 최종 결과로 확인했다. 이번 milestone은00/10의 data 의존성 보존이며 후속 motion interpreter·전체 scene script·자연 scheduler는 미완료다.


## 현행18-handler/11-register API

`SceneCommandState`는 full D0..D7/A0/A1/A2의11 register를 입력·출력한다. `execute_scene_command`의 마지막 optional argument는 borrowed `const std::vector<FixedDataResource>* dependencies=NULL`이며 호출 중에만 사용한다. 기존15 handler에00/10/24를 추가해18개를 지원한다.04/08은 미지원이다. 기존 raw script re-decode·A1 exact opcode·RAM64KiB·ordered ports와 전체 state transaction은 유지한다. A2도 opcode00/24에서 원본 operand pointer를 반환하며 다른 handler에서는 보존한다. CCR·나머지 address register/CPU stack은 API 밖이다.

### Opcode00

첫2 operand word를 RAMd3b8/d3ba에 쓰고 각각 상위 word로 올린 값을 D0/D1 전체 및 RAMd3bc/d3c0에 저장한다. 마지막 operand long은 A2와 RAMd3b4에 저장한다. A2=0이면 motion dependency를 사용하지 않으며 duration=7fff다.

비영 A2는 같은 CPU=ROM 주소의 motion raw resource를 요구한다. 첫1MiB span·65536-byte bound와10-byte 일반 record/4-byte terminal prefix의 정확한 끝을 검증한다. 첫 type은 offset2 word이며8c 이하/4배수다. 첫 record를18c06 dispatch에 전달하는 효과만 지원하며 후속 운동 실행은 하지 않는다. Type을 D4.lowword로 읽고 첫 record+6/+8 word를 D0/D1.lowword로 읽는다. Type<58이면 d3ba.word와d3c0.long의 상위 word,아니면 d3b8.word와d3bc.long의 상위 word에 해당 word를 modulo16 더한다. ADD.W가 해당 주소의 word를 수정하며 long의 하위 word를 수정하는 것이 아니다. 후속 record는 terminal 탐색을 위한 원시 span이며 그 type를 실행하지 않는다. Terminal offset0 time word-1(modulo16)을 duration으로 사용한다.

그 다음 D0=0-RAMd3bc.long,D1=01000000-RAMd3c0.long(modulo32),A0=10d38e,D2=RAMd3a2.long으로43e22 node helper를 실행한다. 공개 D0/D1/D3는 helper 결과, D4.lowbyte=0,D5.lowbyte=RAMd494(그 외24bits 보존),D7 전체=duration을 반환하며 RAMd41e/d420에도 duration을 쓴다. 이 초기 coordinate·첫 motion 적용 계약을 이후 frame의 일반 motion interpreter 구현으로 확대하지 않는다.

### Opcode10과24

10은 operand pointer의 exact4-byte dependency를 읽어 A0에 저장한다. 값0이면 A0=e89ec fallback으로 바꾸고 RAMde2a.long에 저장한다. Canonical e6e9e raw0에 해당하는 경로다. 추가 callback 본문을 실행하지 않는다.

24는 첫 operand word selector를 D7.lowword로,뒤 operand long을 A2로 읽는다. Exact1a0a6/16-byte path node resource에서 selector0/4/8/12의 RAM pointer를 읽고 그 주소에 A2.long을 저장한다. 선택 주소는 짝수 CPU RAM이며 전체4-byte span을 요구한다. A0는 보존한다. 이 long을 대상으로 path 본문을 실행하거나 일반 signed selector를 지원하지 않는다.

Dependencies는 해당 command에서 필요할 때만 검증한다. Missing/malformed motion·간접 window·path table·잘못된 selector/span은 앞서 수행한 RAM update를 포함해 RAM/state/ports 모두 호출 전 값으로 보존한다. 성공 A1은 기존 command.next_cpu_address다.00/10/24 자체는 MMIO port를 추가하지 않는다.

## 현행 CLI

```text
build/step_scene_command D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS SCRIPT_MS5D NODE_POINTERS_MS5D [DEPENDENCIES_DIR]
```

JSON은11 register 키 `d0/d1/d2/d3/d4/d5/d6/d7/a0/a1/a2`와 `writes`를 반환한다. 기존 unsigned parser·exact RAM·resource/input/output alias 검사와9-byte port record 형식을 유지한다. Script와 node table 파일은 항상 로드한다. Dependencies dir은 실행할 command에 motion/indirect/path 파일이 필요할 때만 필수다. 실제 A1 command의 operand를 사용해 motion_%06x/indirect_%06x 또는path_nodes.ms5d 한 파일만 로드하고 기존 input/output/resource와 path·inode alias를 확인한다. Dependency를 쓰지 않는 handler와00의 A2=0 경로는 dir 없이 실행할 수 있다.

## 현행 최종 native 검증

`artifacts/scene_command/verification.json`의 최종 SHA256은 `a69e2b5b136e4db0c14245b7602c36ec0ccd03b5868ed864b894eb5b3cc0f6fb`다. 실제 보고서를 읽어3,945 native/83 negative/18,720 ordered ports/79 actual CLI adjacent-supported run을 확인했다. Full RAM과D0..D7/A0/A1/A2,ordered ports가 일치했고 A7 RTS endpoint를 확인했다. Binary SHA256 `5c690cca7abc017ed999574b95d57caffe45c3f44a067e3938ee68a3563c6982`와 fixed1MiB 원본은 시작·끝에 같았다.

Canonical41 script/814 command 중 현행 지원은17종698 occurrence,미지원04/08은116 occurrence다. 지원18종 중4c는 canonical에 없어서 C++ 합성 unit만 수행하며 native claim은 하지 않는다.00/10/24의 기존 canonical operand와39 dependency 파일을 실제 CLI가 로드해 원본과 비교했고 모든 dependency raw span은 canonical ROM과 같았다. Random RAM/high registers와 slot boundary는 명시적 fixture이며 synthetic operand·node alias/history는 C++ unit 범위로 구분한다. 이전15-handler/10-register3,385 case 결과와 이번 결과는 같은 보고서 경로의 서로 다른 milestone이다.

79 carry run은 actual CLI output RAM/full11 registers/A1/A2를 인접 지원 command에 전달한다. 미지원 opcode 또는 negative terminator에서 멈추며 다음 run은 명시된 standalone call context로 시작한다. 자연적인 전체 script scheduler나 frame-time motion 실행을 검증한 것이 아니다.

최종83 negative는 기존70과 마지막 dependency negative13개를 포함한다. Required directory 누락,파일 부재·malformed container·CRC-valid wrong CPU window,dependency와output의 같은 path alias를 검사했다. API/CLI 오류는 output을 보존했다. 이13개는 native rerun 이후 검증을 추가한 C++ validation이며 원본 ROM을 수정하거나 invalid dependency를 native 실행하지 않았다. Packer source hash·table/record span과 C++ loader의 schema/CRC/사용 window 조건을 각각 구분한다.

`artifacts/scene_command_build_test.log`의 전체 `make -j3 all test`는 exit0, Python134/C++99와 warning0으로 통과했다. 이번 추가 지원은 최초 motion record 적용·terminal duration·간접 long·path pointer 저장까지다.04/08,후속 motion interpreter·전체 script·자연게임 도달·scheduler·CCR/다른address registers·hardware timing은 미완료다.
