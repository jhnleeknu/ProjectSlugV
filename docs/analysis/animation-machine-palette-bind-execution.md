# 팔레트 연결과 노드 준비의 실제 공유 스택 검증

Baseline `5cb6256`. 확정 계약 `animation-machine-palette-bind-contract.md`의 `47ff2→48042` 경계까지 실제 palette release/binding·bank2 lookup·node 준비를 검증한다. 기존3R/9R API의 local/prevalidated-resource 실행으로 실제16R/A7·live stream/list 접근을 대신하지 않는다. 동결된 원본 관측과 실제 C++ 공식 비교를 완료했다. 원본 guard의 부분효과와 API의 전체 rollback은 별도로 검사한다.

Canonical BE ROM은 `extracted/program/maincpu.decrypted.be.bin`,8MiB,SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. Fixed CPU 주소는 동일 file offset이며 bank read는 당시 actualorderedPVC에서 독립 계산한 physical offset으로 대조한다. 실제 여덟 MS5D v1 kind3를 C++ loader/bus에 공급하고 원본을 수정하지 않는다. Initial palette preparer 실행은 controlled fixture provenance로 구분한다.

Strict22-key test harness에서 full64KiB RAM/16R/PC/A7·devicePVC/bank·orderedports/read count/status를 비교한다. 재개는 직전 실제 C++ 출력과 선언된 hostRAM변경만 사용한다. Fresh original split/continuous 재실행과 저장 payload를 감사한다. Raw nativePVC와 masked device storage는 구분하고 actualorderedwrites로 독립 fold한다. Native C는 별도 실제 proof 없으면 미관측이며 SR을 읽지 않는다.

입력·recursive Python/C++ source/header·newunit·compiler/runtime·resource·native/source/report·harness/binary를 실행 전 pin하고 종료 시 current hashes와 ROM stat/hash를 검사한다. 시작 시 이전 성공 보고서를 지운다. Checked API rollback과 원본 fault의 부분효과는 별개다.

```sh
.venv/bin/python tools/pack_physical_program.py
.venv/bin/python tools/observe_animation_machine_palette_bind.py
.venv/bin/python tools/verify_animation_machine_palette_bind.py
```

`48042`의 JSR1861a는 실행하지 않는다. 전달되는 `480f2` header 주소와 실제 header payload 읽기를 구분한다. 일반 map update·rendering·scheduler/gameplay·BIOS/IRQ/timing·일반 CCR·전체 게임 완료는 미검증이다.

동결 원본 도구 SHA256은 `74cabb1c2fa0acc922a8f3d5ff2a1a56cb979b6ea4d0e6b99f695d1d11b3b90a`, 보고서 `artifacts/animation_machine_palette_bind_native/observation.json` SHA256은 `0ce478765207df8625a9a8065fb0f75ce68604b6df7a822bd8ac0d0ec5648afb`이다. 정상58조건의 split140단계/freshcontinuous58단계/재개82회와 별도5guard를 저장했다. 정상 actualorderedports77개는 watchdog69/PVC8이고 video·wait·외부status읽기는 없다. 실제 upper4조건에서 각6회씩 총24 bank read를 기록했다.

원본에서 CPU20000c→physical20000c의LONG, CPU2004c0→physical2004c0의LONG, CPU201ec0의 binding WORD/WORD/BYTE/terminalWORD를 읽는다. 각 upper조건은 합계15byte를 읽는다. 두LONG 창 각4byte와 binding raw창8byte의 합계16byte 중 binding의 sixthbyte는 읽지 않으므로, 세 raw창 전체를 소비했다고 주장하지 않는다. `480f2` header는 주소 전달과 payload소비를 구분한다. Live flags alias는 변경된 adjacentterminal을 소비하기 전 `8e36`에서 멈추는 부분 증거이고, 별도 정상 조건이 fullRTS를 검증한다. LiveRTS binding alias의 실제 변경된 반환주소 `0004f080`은 관측된 경계이며 임의 정상 게임 continuation으로 확장하지 않는다.

Core unit65 API호출 normal/UBSan이 경고0으로 통과했고, 별도 선택적인 actualkind3 uppercaller 검사는66번째 호출로 통과했다. 메인 `make -j4 all test`가 exit0으로 Python257개/C++161개 실행, 경고0을 기록했다. 기존 회귀의 최종 기록은 리뷰0230에 저장한다.

공식 보고서 `artifacts/animation_machine_palette_bind_execution/verification.json` SHA256은 `fda00cf15928f1b1f34598aabe6b1f036ef3a46b4f4b5950066a9b39489cf5d0`, 검증 도구 SHA256은 `d7a3856837d7a402408255c887bb0b2346be93e1889c23462a828e8cf890a959`이다. 정상58조건·140단계·직전 실제 C++ 출력 재개82회가 fullRAM/16R/PC/A7/PVC/bank/ports/status/read count와 일치했다. 원본 정상·guard 전체를 fresh split145단계/continuous63단계로 재실행하고 저장 payload와 대조했다. 독립 읽기 감사는 정상 fixed680건/bank24건과 PVC쓰기8건을 확인했다.

실패21건은 nativeguard5건과 API전용16건이다. 홀수 binding WORD·미지원 장치 읽기·signed list offset/late link 쓰기·reference/ID 이후 live flag읽기·node의 늦은 쓰기/변경된RTS·누락된 실제bank lookup과 `48042` 이후본문·Z-only4진입을 검사했다. 모두 API의 fullstate/carry/RAM/device/bank/ports/read count/status 보존을 확인했고 원본 fault rollback과 동일하다고 주장하지 않는다. Zero-step33건은 valid carry0/1/2 입력 전 상태 보존을 검사했다. 79inputs/2831artifact keys는 정규화2855개 고유 파일이며 전후/current SHA검사를 통과했다.

기존11개 공식 machine 회귀도 모두 통과했다. 메인은 새 검증을 포함한12개 보고서의 현재 고유 참조35106개를 직접 해시 대조했다. 독립 검토·경계 검사 수정·최종 회귀별SHA는 리뷰0230에 기록한다. 전체 게임 완료나 자연 stage/frame 도달성으로 확대하지 않는다.
