# Stage catalog가 참조하는 scene script raw MS5D 리소스

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 CPU script 주소는 고정 ROM의 같은 파일 오프셋이다. 원본 ROM과 생성한 추출 데이터는 Git에 추가하지 않는다.

## 추출 범위와 형식

`tools/pack_scene_scripts.py`는 canonical stage catalog의59 record에서 payload+2의 script pointer를 읽는다. 서로 다른 비영 pointer마다 `scene_%06x.ms5d`를 생성한다. 현재41파일, raw payload 합계5486 byte이며 null pointer는 리소스를 생성하지 않는다. Manifest는 원본 해시,59참조와 각 리소스의 CPU/ROM 주소, exclusive end, container/payload 해시, command count와 terminator 주소를 기록한다.

형식은 기존 MS5D v1 kind1이다. Payload는 script 시작부터 처음 음수 BE16 opcode의2 byte까지 그대로 보존한다. Command operand와 opcode2c의 inline byte도 변경하지 않는다. Packer의65536-byte scan bound는 malformed source의 정지 제약이며 논리 script 길이의 증명이 아니다. Map/path 등 외부 pointer target은 이 bundle에 포함하지 않는다.

## C++ decoder 계약

`decode_scene_script(resource,script,error)`는 비영 짝수 fixed-ROM 주소, CPU=ROM offset과1MiB 이내 source span을 요구한다. 지원 opcode는00..4c의4단위20종이다. Operand byte 길이는 순서대로 `8,2,4,4,4,6,6,4,2,6,2,6,8,2,8,2,2,4,2,4`다.

Opcode2c는3 word operand 뒤에 세 번째 signed word가 지정한 opaque inline byte를 갖는다. 비음수 짝수 skip만 지원한다. Inline에 음수 opcode와 같은 byte가 있어도 명령으로 다시 읽지 않는다. Unknown opcode, truncation, 음수/홀수 skip, missing terminator와 terminator 뒤 추가 byte는 API 오류다.

`SceneScript.source`는 원래 FixedDataResource 전체를 보존한다. `commands`의 SceneCommand는 `source_cpu_address,opcode,operands,inline_data,next_cpu_address`를 갖는다. 음수 terminator는 commands에 포함하지 않고 `terminator_cpu_address,terminator_opcode`에 별도로 기록한다. 실패 시 source/commands/terminator 모두 보존한다. `load_scene_script(path,...)`는 기존 MS5D loader의 header/CRC 검사 뒤 같은 decoder를 호출한다. CLI도 ROM을 직접 읽지 않는다.

이는 typed syntax decoding이며 handler 실행이나 전체 interpreter 복원이 아니다. 독립 검증에서는1a0b6의 dispatch3명령만 실행한다. 제어 흐름, 외부 target의 소유 범위, 실제 게임에서의 자연 도달, RAM 효과와 timing은 이 결과로 확정하지 않는다.

## 재생성과 사용

```
.venv/bin/python tools/pack_scene_scripts.py
make runtime-resources
make -j2 build/inspect_scene_script build/scene_script_test
build/scene_script_test
build/inspect_scene_script extracted/runtime/scene_scripts/scene_0dc44c.ms5d
```

`inspect_scene_script SCRIPT_MS5D`는 JSON으로 source_cpu_address, commands 배열, terminator_address/opcode를 출력한다. Command 키는 `address,opcode,operandhex,inlinehex,next`다. Hex 문자열은 raw byte 순서이며 integer 주소/opcode는 decimal로 출력한다. 파일을 변경하지 않는다.

## 검증

C++ 단위 시험은 전체20 opcode, opaque inline block, 음수 terminator, 경계/truncation/unknown opcode/잘못된 skip과 기존 출력 rollback을 검사해 통과했다. Packer의 합성 Python 시험6개도 추가됐다. 전체 `make -j3 all test`는 exit0, Python131개와 C++98개 실행을 통과했고 컴파일 경고0개다. 로그는 `artifacts/scene_script_resources_build_test.log`다.

최종 `tools/verify_scene_script_resources.py`는41 script/5486 payload byte/814 command/9 opaque inline block와10음성 사례를 통과했다.59 record 참조를 원본과 대조하고 모든 C++ command의 raw 재조합이 원본 span과 같음을 확인했다. 각814명령에서 원본1a0b6의 MOVE.W/JMP/BRA만 실행하고 handler 첫 명령 전에 멈춰 A1+2, D7 상위 bit 보존과 target mapping을 검사했다. Handler 효과, 전체 scene 초기화, 외부 map/path 리소스, 자연 도달이나 실제 렌더링을 검증한 것은 아니다.

실제 보고서 `artifacts/scene_script_resources/verification.json` SHA256은 `624fdd85a3d34445a37421e5df4413b0a70d84dd94f027a90715ff6f907ec560`다. CLI binary SHA256은 `be3ccab6bcbf778172bfffe6ee45f329a482fcd9a6fbd30dd9e1b662a788bd89`다.
