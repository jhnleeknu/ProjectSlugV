# Scene command의 부분 실행 계약

이 문서는 `e495c44`의15-handler/10-register milestone 기록이다. 아래 report hash·수치는 당시 결과이며 같은 report 경로는 후속 검증에서 덮어쓸 수 있다. 현행18-handler/11-register API와 의존성·최종 검증은 `scene-command-dependencies.md`를 참조한다.

## 원본과 resource 범위

Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. Script·handler·pointer table 주소는 첫1MiB 고정 ROM이며 같은 파일 offset이다. RAM pointer는 CPU RAM 주소로 따로 기록한다. 주소·opcode·상수는16진수, 개수는10진수다.

앞선 resource milestone은 stage catalog59 record의41개 비영 script를 기존 MS5D v1 kind1로 보존하고20종 opcode의 typed syntax를 decode했다. Resource 추출·dispatch-only 검증은 `scene-script-resources.md`의 범위이며 이번 command handler 실행 검증과 구분한다. 원본과 추출 게임 데이터는 Git에 추가하지 않는다.

이번 실행 지원은15 opcode `0c/14/18/1c/20/28/2c/30/34/38/3c/40/44/48/4c`다. `00/04/08/10/24`는 syntax decoder가 읽을 수 있어도 실행 API에서 미지원이다. Script 전체의 순차 실행,1a26a phase gate,일반 scene 초기화·자연 scheduler 또는 미지원 handler의 부작용까지 완료했다고 주장하지 않는다.

## Node pointer 원시 리소스

`tools/pack_scene_scripts.py`는 `[1a08e,1a09e)`의16바이트4 BE32 RAM pointer를 `extracted/runtime/scene_scripts/node_pointers.ms5d`에 추가한다. 기존 MS5D v1 kind1이며 stable ID는 `scene-node-pointers:0001a08e`다. Manifest의 `node_pointers`는 source CPU/ROM 주소·payload 길이와 container SHA를 기록하며 실제 payload는4 pointer를 그대로 보존한다. 새로운 별도 포맷을 만들지 않는다.

```text
.venv/bin/python tools/pack_scene_scripts.py
make runtime-resources
```

Pointer resource는 handler가 원본 고정 table을 읽는 효과를 제공하기 위한 것이며16바이트라는 raw span을 node 구조의 논리 크기로 해석하지 않는다. Payload pointer는109156/10b1d6/10d256/10d2d6다. Container48바이트의 SHA256은 `85b32c4d7aff4ba30dc4053a22e695d93cc97006854dfdb321c0a59365b2ee9c`, payload16바이트 SHA256은 `e92ddd0369fbf6b8eefa393b9220f497f28f49395f3ea935577683e8f68847e9`다. 실제 생성 파일을 읽어 확인했다.

## 단일 command API

`engine/include/ms5/scene_command.h`와 `engine/src/scene_command.cpp`의 `execute_scene_command(ram,script,node_pointers,state,ports,error)`는 exact64KiB RAM과 `SceneCommandState`의 full D0/D1/D2/D3/D4/D5/D6/D7/A0/A1을 입력·출력한다. A1은 opcode 시작 CPU 주소다. API는 script.source의 원시 resource를 다시 decode하고 그 주소와 일치하는 command만 사용한다. 외부에서 수정한 typed commands 목록을 실행 근거로 사용하지 않는다. Terminator·operand 내부 주소·미지원 opcode는 오류다.

원본1a0b6 dispatch의 MOVE.W로 D7.lowword에 opcode를 넣고 상위16비트를 보존한 뒤 각 handler를 실행한다. 성공 A1은 command.next_cpu_address이며 op2c의 opaque inline span도 건너뛴다. Handler RTS까지의 지원 효과만 제공하며 caller 실행이나 다음 opcode의 자동 실행은 하지 않는다. Opcode14의 node helper는 기존 scene node RAM 효과에 더해 원본 scratch register 결과까지 연결한다. 다른 address registers·CCR·CPU stack은 노출하지 않는다.

| Opcode | 지원 효과와 노출 결과 |
| --- | --- |
| 0c | Operand long을 A0와 RAMd40e에 저장 |
| 14 | Node selector 뒤2 word를 각각 상위 word로 올려 RAMd38e/d392 long에 modulo32 덧셈. D0/D1과 선택 A0로16fee를 실행. D2=old node+14 long,D3=old node+18 long,D4.lowbyte=0/D5.lowbyte=RAMd494(나머지24bit 보존),D6보존,D7전체0 |
| 18 | 선택 node+28/+2a word에 operand 저장 |
| 1c | Operand word 비영이면 node+7a byte에81 OR.0 경로는 bit0 clear 후1701a..1724a로 이어 node+26 signed word를 D7.lowword로 읽음.음수면 즉시 반환,비음수면 watchdog1회와VRAM long64회 및 D5/D6/D7 결과를 반환 |
| 20 | RAMd40c byte에 `(old & operand byte0) | operand byte1`. D7.lowbyte에 결과 |
| 28 | RAMd416 word 저장 |
| 2c | 첫 word 음수면7fff,아니면 원래 값을 D0.lowword/d416/d41e에 저장. 둘째 word를 modulo16 빼 d420에 저장. 셋째 skip word를 D0.lowword에 남기고 d422 long에 inline 시작 주소 저장 |
| 30 | RAMd426/d428/d42a/d42c에4 word 저장 |
| 34 | Operand word rotate-left1 후&3을 D0.lowword에 저장. RAMd3cc byte의 기존fc bits와 OR한 결과를 D1.lowbyte와 RAM에 저장 |
| 38 | RAMd3fc/d400에2 long 저장 |
| 3c | RAMd432 word 저장 |
| 40 | D0.lowword에 operand-1. Operand0이면 RAM4d90.byte0과4d91.bit3 set,비영이면 감소값 lowbyte와 bit3 clear. RAM4d90 word를 MMIO3c0006 word로1회 저장 |
| 44 | RAMd42e/d430에2 word 저장 |
| 48 | RAMd43c word 저장 |
| 4c | RAMd434 long 저장 |

Word/byte 결과는 해당 register의 나머지 상위 bits를 보존한다. Node opcode14/18/1c는 selector0/4/8/12만 지원하고 원본1a08e CPU=ROM offset/16-byte pointer resource를 요구한다. 선택 pointer는 짝수 RAM CPU 주소이며14는2e바이트,18은2c바이트,1c는7b바이트 전체 span이 RAM 안에 있어야 한다. API는 다른 opcode에서 node resource를 검증하지 않는다. 일반 signed-index lookup이나 다른 ROM table 범위는 지원하지 않는다.

성공은 RAM/state와 해당 command의 ordered port 결과를 교체한다. 40은 size2/address3c0006/valueRAM4d90.word의1 write다.1c의0 operand와 비음수 node slot 경로는 watchdog size1/address300001/valueD0.lowbyte를 먼저 쓰고32 slot마다2 long3c0000을 순서대로 쓴다. 따라서 총65 writes다. 음수 slot이면 추가 ports가 없다. 원본1701a..1724a에 따라 D6.lowword=slot+8001,D7.lowword=slot+8201(각16비트 wrap) 뒤 두 register의 halves를 SWAP하고 D6.lowword=0fff/D7.lowword=8000으로 만든다. D5 전체10000으로32회 반복하며 매회 D7 write→D7+=10000→D6 write→D6+=10000 순서다. 모든 long 덧셈은32비트 modulo다. 음수 slot return은 D7.lowword만 slot으로 바꾸고 D5/D6를 보존한다. 오류는 호출 전 RAM/state/ports 전체를 보존한다. 부분 node update나 output port 변경을 commit하지 않는다.

## CLI

```text
build/step_scene_command D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS SCRIPT_MS5D NODE_POINTERS_MS5D
```

모든 정수는32비트 unsigned decimal 또는0x hex다. CLI는 exact RAM, 각 input/output/resource의 canonical path·inode alias와 parser를 검사하고 `load_scene_script` 및 기존 `load_fixed_data_resource`를 항상 호출한다. API가 node resource를 사용하지 않는 opcode여도 CLI의 file loading은 필요하다. 성공 JSON은 full `d0/d1/d2/d3/d4/d5/d6/d7/a0/a1`과 `writes`를 반환한다. Port 파일은 기존 각9바이트 `size byte + address BE32 + value BE32` 형식이다.

## 최종 검증

최종 `artifacts/scene_command/verification.json` SHA256은 `ea129b9adc8158c195cd1bd92ee4488d24aae78ca87e6327a3a0dad5ffe9e65d`다. Session36147은 exit0으로3,385 native case/65 negative/18,720 ordered ports를 통과했다. 전체64KiB RAM과 full D0..D7/A0/A1, port 순서가 일치했으며 원본 A7 RTS endpoint도 확인했다. Binary SHA256 `7424ae5fd62e55d4180579da798c2d3354e86853181cf6c1729f8cd90c04a253`와 fixed1MiB 원본 code는 시작·끝에 같았다.

Canonical41 script의814 command 중 지원14종586 occurrence를4 RAM/high-register profile로 비교해2,344 case를 만들었다. 추가로1c false-clear52 occurrence×5 slot boundary=260과40 video39 occurrence×5 shadow profile=195를 검사했다. Actual CLI adjacent-supported run118개에서586 call의 실제 output RAM/full returned registers/A1을 다음 command에 전달했다. 미지원 opcode 또는 negative terminator에서 run을 중단하며 다음 run은 명시된 standalone call boundary에서 시작한다. CPU standalone call context를 다시 설정하므로 전체 interpreter/scheduler의 자연적인 연속 실행을 검증한 것이 아니다.

원본 비교는 canonical operand만 사용하며 random RAM/register와 slot boundary는 명시된 fixture다. 지원15종 중4c는 canonical occurrence0이어서 C++ 합성 unit으로만 확인했다. 합성 operand·node alias/history 역시 C++ unit 범위이며 native 포함으로 주장하지 않는다. Mutated resource의 invalid selector negative는 C++ validation만 실행했고 원본 ROM에 쓰거나 native 실행하지 않았다.

초기 원본 비교는1c false-clear의1701a watchdog+64 long/D7 효과 누락과14의 D5 scratch 누락을 발견했다. 이를 수정하고 D0..D7/A0/A1의10 register API로 확장한 뒤 전체를 재실행해 통과했다. 이 검증 기록은 RAM만 같아도 register/port 계약이 같다고 가정할 수 없다는 실제 회귀 근거다.

`artifacts/scene_command_build_test.log`의 전체 `make -j3 all test`는 exit0, Python131/C++99와 warning0으로 완료됐다. 자연게임 도달·전체 script·미지원5 handler·1a26a phase gate·외부 map/path·CPU CCR/다른 address registers·hardware timing은 범위 밖이다.

## 미지원 command의 다음 의존성 목록

메인이 canonical syntax inventory로 확인한 미지원228개는08:41,00:39,04:75,24:72,10:1이다. 근거 목록은 `artifacts/scene_command/remaining_commands.json`에 보존한다. Canonical10의 opcode 주소는e6f34, operand pointer는e6e9e이며 그 ROM long 값은0이다. 이 값·빈도는 구문/원시 참조 사실이고 handler 실행·외부 target 소유·자연 도달 검증이 아니다. 다음 구현 의존성 분석 대상으로 남긴다.
