# 맵 전송과 반복 경계의 실제 공유 스택 검증

Baseline `6212b39`. 확정 계약 `animation-machine-map-transfer-contract.md`의 `48042→4804e` 경계와 column/clip/refresh/wrap helpers를 실제16R/A7/bus로 검증한다. 기존13R map API의 local saved array로 MOVEM.W의 실제 공유 RAM push/pop을 대신하지 않는다. 동결된 원본과 실제 C++의 공식 비교가 완료되었다.

Canonical BE ROM은 `extracted/program/maincpu.decrypted.be.bin`,8MiB,SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. Fixed CPU 주소는 같은 file offset이며 banked read는 당시 실제 orderedPVC를 독립 fold한 bank/physicaloffset/원본bytes로 대조한다. 실제 여덟 MS5D v1 kind3를 C++ loader/bus로 공급하고 원본을 수정하지 않는다. 초기 scene/palette 준비는 fixture provenance와 관측 구간을 구분한다.

Strict22-key harness는 full64KiB RAM/16R/PC/liveA7/devicePVC-bank/orderedports/externalreads/status를 비교한다. 재개 입력은 직전 실제 C++ 출력과 선언된 hostRAM변경뿐이다. 원본 fresh split/continuous 및 저장payload를 재실행·감사한다. Raw nativePVC와 masked device storage는 구분한다. Native SR은 읽지 않으며 알려진 source C writer와 실제 분기로 관측된 C를 구분한다.

새 계약·unit·recursive Python/C++ source/header·compiler/runtime·native/report/resources·harness/binary를 실행 전 pin하고 종료 시 currenthashes/ROMstat를 재검사한다. 시작 시 stale 성공보고서를 지운다. Native fault의 부분효과와 checked API의 전체 rollback을 별개로 기록한다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_map_transfer.py
.venv/bin/python tools/verify_animation_machine_map_transfer.py
```

`4804e` 이후 timer/8c16은 실행하지 않는다. 별도caller가 확인되지 않은 `184d2..1852e` video zero-fill과185fa/18656 wrappers는 이번 범위에 포함하지 않는다. Instruction-unit video ports와 실제buscycles/VRAM표시를 구분한다. 일반CCR/XNZV·BIOS/IRQ/timing·자연scheduler/직접플레이·전체게임 완료는 미검증이다.

전역 실행 예산은 유한100만 machine block이다. 정상적인 D2.low=0의65536 column 반복을 과거10만 cap으로 잘라내지 않도록 확정된 변경이며, 원본 instruction 수와 C++ block 수는 서로 다르다. 원본 정상 완료와 별도 API 예산 초과 rollback을 각각 검사한다. 원본 D2.low=0 조건은 65536회 반복을 완료했고 continuous trace는 327689개 PC를 기록했다(split에는 중복 checkpoint 한 개가 더 있다). 같은 정상 조건의 실제 C++ 완료와 별도 유한 예산 초과 실패에서 전체 API 출력 보존을 확인했다.

`185ee`의 원본 `003c00014e75`(ORI CCR1/RTS)와 `185f4`의 `023c00fe4e75`(ANDI CCRfe/RTS)는 source-classified Set/Clear 검사로 구분한다. Native는 이 범위의 SR이나 C를 읽지 않으며 이 검사를 측정된 native carry라고 표현하지 않는다.


동결된 원본 보고서는 50개 정상 조건의 131 split 단계와 50 fresh continuous 단계, 별도 guard 5개를 기록한다. 정상 구간의 ordered port 11666개는 video 9212, watchdog 2292, PVC 162개다. 실제 bank 데이터 read 2787개와 fixed read 280개는 소비 당시 bank와 physical offset을 대조한다. 원본 도구 SHA256은 `5c3e49d5f3b74f275e2efc7d5c670b462be3f2e6a1b9e4c651a9d4816dbaf5e8`, 원본 보고서 SHA256은 `3cbf2b1b6b49c675f116c8298f09d36feb817ae76173fcab4d03a71b1428abf8`이다. 이 원본 집계 자체를 C++ 일치나 자연 플레이의 증거로 대체하지 않는다.

공식 `artifacts/animation_machine_map_transfer_execution/verification.json`은 정상 50조건/131단계와 직전 실제 C++ 출력 재개 81회를 대조했다. Full64KiB/16R/PC/A7/PVC-device/bank/ordered ports/status/외부 read count가 일치했고, 원본 split/continuous의 정상 50단계와 guard continuous 5단계를 모두 재실행했다. 실제 ordered port는 11666개, wait와 외부 read는 0개다. 이번 범위의 native carry 관측은 0개이며 source-classified Set/Clear 6검사를 별도로 기록했다.

실패 검사는 custom13개와 원본 guard5개를 합한18개이고, zero-step은11경계×carry3값=33개다. DIVU zero/odd record read/늦은 bank write/공유 column write가 바꾼 live RTS raw218742는 원본 fault와 checked rollback을 분리해 검사한다. 추가 검사는 실제 MOVEM의 앞선 push/pop, secondary LONG publication 뒤 실패, live BYTE 재읽기 실패, bank3 전환 뒤 missing ROM, 마지막 flag write 뒤 잘못된 RTS, 유한100만 block budget을 넘은 반복 clear 후 전체 출력 보존을 포함한다.

검증기 SHA256은 `75ffc969bee9f16ed916aad7abe9d96207268b8d321380f2150aef84129bb8c4`, 공식 보고서는 `78f2dfb30e4a8710a4044f6be7985f8220632213190af5eff4a28f8beb854844`다. 81 input key와2690 artifact key를 정규화한2715개 파일의 현재 SHA256을 검사했다. 새 core/unit은 normal·UBSan에서103 API 호출과 경고0으로 통과했다. 독립 core 검토는 원본298명령 raw bytes와39개 C-preserver, 동결된 native의14개 incoming checkpoint를 대조했으며, 독립 native 감사는27조건/73split/27continuous/guard5개와1549개 hash 참조를 확인했다.

메인의 최종 `make all test`는 Python257개/C++실행162개, 경고0으로 통과했다(`/tmp/ms5-map-transfer-main-make-final.log`). 확대된 유한 예산으로 기존 transition fill의 약196k block 정상 완료가 가능해졌으므로, 과거 budget 실패 기대를 실제 완료와 정확한3 port 기대값으로 정정했다. 이는 새 runtime 결함이나 무제한 실행의 허용이 아니다. 배정된 screen/cleanup/scene/palette binding 회귀도 공식 재실행과 현재 hash 감사에 통과했다. 다른 기존 회귀와 전체 보고서 union의 최종 집계는 메인의 통합 리뷰에 기록한다.

배정된 기존 회귀는 각각 screen31/128단계·실패14·zero24,cleanup69/121·실패17·zero33,scene79/225·실패20·zero30,palette binding58/140·실패21·zero33을 유지했다. 이들 재실행은 신규 맵 관측50조건에 더해진 자연 플레이 증거가 아니라 이전 API/실행 범위의 회귀 증거다.

최종 기존12개 공식 machine 회귀가 모두 통과했다. 메인이 새 map을 포함한13개 보고서의 현재 고유 참조37744개 SHA를 직접 확인했다. 회귀별 최종SHA·검토·수정 근거는 리뷰0231에 기록한다. 이 단계 통합 뒤 사용자의 요청에 따라 Goal을 일시중지하며 전체 게임 완료로 취급하지 않는다.
