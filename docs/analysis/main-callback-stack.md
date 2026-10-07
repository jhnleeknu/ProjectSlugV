# 메인 콜백의 실제 스택과 오브젝트 복구

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU 주소 f30..f52는 같은 복호화 프로그램 ROM 오프셋이다.

## 호출과 복귀

f30이 오브젝트 A6+76.long을 A0에 읽고 0 여부를 검사한다. 새 `enter_main_callback`은 f3c부터 시작하므로 이 슬롯을 다시 읽지 않고 **입력 A0**를 호출 대상으로 사용한다. 원래 A6.long을 push하고 A6+7a.long을 새 A6 문맥으로 읽은 뒤 JSR의 복귀 주소 f44.long을 push한다. 입력 A7을 S라 하면 S−8에는 f44, S−4에는 원래 A6가 저장된다. 출력 A7은 S−8이고 next_pc는 입력 A0다. D0..D7/A0..A5는 보존된다.

콜백 RTS가 f44를 소비한 뒤 `restore_main_callback`을 호출한다. 입력 스택의 현재 long을 A6로 복구하고 A7에4를 더한 뒤 **f46의 팔레트 호출 직전**에서 멈춘다. 콜백이 저장된 A6를 바꿨다면 바뀐 값을 사용한다. 다른 레지스터는 콜백이 남긴 값 그대로 유지한다. 두 경계 모두 RAM 변경과 MMIO는 없다.

공유 `irq_envelope.h/.cpp`의 실제 스택·결과 규격을 사용한다. main-call은 64KiB RAM, 짝수 오브젝트100000..10ff82, 짝수SP110008..fffffe와 외부 스택 `[SP−8,SP)`를 요구한다. RAM과 스택 벡터는 별개여야 한다. main-return은 짝수SP110000..fffffa와 `[SP,SP+4)`를 요구한다. 성공 시 bios_handoff=false, 실패 시 입력과 결과·포트를 보존한다. SR/CCR은 계약에 포함하지 않는다.

```sh
build/step_irq_envelope main-call INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE
build/step_irq_envelope main-return INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE
.venv/bin/python tools/verify_main_callback_stack.py
```

## 검증

원본352조건(독립304, 연결48)과 실패/별칭21조건 통과. 전체 RAM·스택·16개 레지스터 및 시간순 스택 쓰기가 일치하고 MMIO는 없다. 호출48조건에서 입력A0와 오브젝트+76을 의도적으로 다르게 했으며 오브젝트/스택 경계를 확인했다. 복귀256조건에서 저장 A6 패턴과 word 정렬을 확인했다.

16개 연결 사례는 main-call 출력 스택을 실제3dcc RTS와 main-return에 전달한다. 레지스터 변경은 호스트가 명시적으로 주입했으며 임의 콜백 본문을 복원했다고 주장하지 않는다. 원본 코드 불변과 code hook 중단을 확인했다. C++ 단위 검사에는 실제 저장 A6의 변경 및 오류 시 결과·포트 보존도 포함했다.

보고서: `artifacts/main_callback_stack/verification.json`.
SHA256: `0af33d3f984a79ca47cb2ea1a562d43de1f2e8e72a3dbf6b03777c011efad4e9`.

## 다음 연결의 남은 조건

f46은5728 팔레트 처리를 호출한 뒤 f4c에서RAM100016.byte가 0이 아닌지 기다리고 f12로 돌아간다. 이 대기는 ef2와 달리 RAM17 임계값을 비교하거나 비디오3c0006을 읽지 않는다.

기존 `step_palette_frame`은 RAM과 장치 쓰기를 복원하지만 최종D1을 반환하지 않는다. 원본5728 및7196 아래 색 변환 helper들은 경로에 따라 D1을 바꿀 수 있다. 따라서 콜백의 D1을 그대로 다음 입력 style로 넘기는 연결은 아직 정당화되지 않는다. 팔레트 최종D1과 f4c 대기, ec4 앞부분 및 실제 콜백 본문을 계속 분석해야 한다. 전체 메인 루프·부팅·SR/RTE/BIOS·장치 시간축은 미완료다.
