# 장면 설정의 실제 공유 스택 검증

Baseline `8db0a9e`. 새 범위는 `47fe8/47fec→43ffc`와 실제 descriptor·reset/node/allocator/pool 호출을 `47ff2` JSR 전 경계까지 연결한다. 새 실행기는 공유 RAM에서 실제 A7 push/pop을 수행한다. 기존12R API의 local/vector로 이를 대신하지 않는다. 동결된 원본과 실제 C++ 공식 비교가 완료되었다. 원본 관측과 checked API 실패의 증거 범위는 아래에서 구분한다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 낮은 fixed CPU 주소는 같은 ROM 파일 offset이다. 실제 여덟 MS5D v1 kind3를 C++ loader/bus로 공급하며 ROM을 수정하지 않는다. `48108`의 원본12byte descriptor는 별도 새 format 없이 포함된다.

Strict22-key test harness로 full64KiB RAM/16R/PC/A7와 mutablePVC/device bank·ordered ports/read count/status를 비교한다. 실제 이전 C++ 출력과 선언된 host RAM 변경만 재개 입력으로 사용한다. 원본 bank data는 실제 PVC 쓰기 뒤 readonly backend를 갱신하며 rawPVC와 독립 장치 효과를 분리한다. 일반 CCR/Z를 공개했다고 주장하지 않으며 임의 `44074` Z-only 진입을 checked 거부한다.

실제 새 scene 계약과 recursive Python/C++ 의존성·unit·compiler/runtime·원본·리소스·harness/binary를 실행 전에 pin하고 종료 시 다시 검사한다. 시작 시 이전 성공 보고서를 지운다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_scene.py
.venv/bin/python tools/verify_animation_machine_scene.py
```

Native fault의 부분 효과와 checked API rollback을 구분한다. 일반 CCR/XNZV·IRQ/timing·banked code execution·자연 scheduler/게임플레이·전체 stage·전체 게임 완료는 미검증이다.

원본 관측 보고서 `artifacts/animation_machine_scene_native/observation.json` SHA256은 `46c0271dbfdc15f93e73bed69c08e62511a122c991e8c30c9e5b7979cd3b0ff3`, 도구 SHA256은 `4c5ae13f7599065008f52390636c2e8a97e3c91cbc9ccd670d642d277f24c9d9`이다. 정상79조건의 split225단계와 fresh continuous79단계, 별도8guard를 저장했다. 정상 단계는 실제 PVC196·video244815·watchdog54911 쓰기를 포함하고 wait·외부 status 읽기·관측된 carry는 없다.

고정 descriptor와 통제된 liveRAM descriptor를 구분한다. A0 LONG·PEA suffix pointer·D7 WORD(stride2)의 실제 push/pop, operand/stack alias, sign-extended MOVEM.W, allocator WORD wrap 및 순차 WORD clear를 원본에서 관측한다. 직접 `ccfc` D7.low=`ffff`는 실제65536 WORD 반복 후 `cd06`에서 멈추며 변경된 반환 주소를 소비하는 전체 RTS 성공을 뜻하지 않는다. 일부 alias 조건도 명시된 원본 경계에서 멈춘다.

이 scene closure의 실제 bank ROM data 읽기는0이다. 동적 backend가 PVC2→3→2 전환에 맞춰 readonly bytes를 갱신하는 별도 합성 확인 도구는 `tools/probe_scene_bank_backend.py`이며, 이 결과를 원본 scene의 bank3 읽기 증거로 합산하지 않는다. Raw nativePVC와 C++ 장치의 masked storage는 구분하고 실제 ordered writes로 장치 효과를 독립 계산한다.

Core unit139 API 호출 normal/UBSan이 통과했다. 전체 `make all test`는 Python257/C++160 실행, 경고0으로 완료했다(main의 전체 빌드 기록). 기존12R API는 별도 범위를 유지한다.

공식 검증 보고서 `artifacts/animation_machine_scene_execution/verification.json` SHA256은 `26c596cb95fd59aba2f5d19a43ab65cd6baebbc8cdfe9aab46e88b09b5a19556`, 검증 도구 SHA256은 `2681bdc3db82c0292db6750b0808937d1ad4ff7034f9638261314fa761409fcd`이다. 정상79조건·225단계·이전 실제 C++ 출력 재개146회가 fullRAM/16R/PC/A7/PVC/bank/ordered ports/status/read count와 일치했다. 총299922 ports는 PVC196·video244815·watchdog54911이다. 원본 split233단계와 fresh continuous87단계(별도8guard 포함)를 모두 메모리에서 다시 실행하고 저장 payload와 대조했다.

실패20건은 원본 guard8건과 API 전용12건으로 나눈다. 실제 reset 뒤 누락된 ROM descriptor, 순차 WORD/LONG 쓰기 뒤 접근 실패, A0/D7 live pop 뒤 잘못된 RTS, stack push 뒤 경계 실패, `44074` Z-only 진입과 `47ff2` 이후 미지원 본문을 검사한다. API 실패에서 full state/carry/RAM/device/bank/ports/read count/status 보존을 확인했으며, 원본 fault의 부분 효과와 동일하다고 주장하지 않는다. Zero-step30건은 세 carry 입력 각각의 전 상태 보존을 확인했다. 보고서77입력·4244 artifact key는 정규화4267개 고유 파일이며 전후/current SHA 검사를 통과했다.

기존 열 공식 회귀도 모두 통과했다. 메인은 새 scene을 포함한 열한 보고서의 현재 고유 파일 합집합32326개 SHA를 확인했다. 각 최종 보고서 SHA와 검토 근거는 리뷰0229에 기록했다.
