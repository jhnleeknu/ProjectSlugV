# 두 번째 IRQ29c의 콜백과 VRAM 복구

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU29c..2d6은 같은 ROM 오프셋이다. 구현은 `irq_envelope.h/.cpp`의 `begin_raster_irq`와 `finish_raster_irq`다.

## 활성·비활성 분기

29c는 RAM10fd80.byte를 검사한다. 음수가 아니면 콜백 없이3c000c.word에2를 쓰고2d6의RTE 직전에 멈춘다. RAM·레지스터·외부 스택은 그대로다.20c의 비활성 분기와 달리 BIOS로 넘어가지 않는다.

음수이면 원래 A5.long, RAM104d8e의VRAM 주소.word를 차례로 push하고 A5에RAM10000a.long을 읽는다. JSR(A5)의 복귀 주소2b6을 push한 뒤 콜백 경계를 반환한다. 진입 A7을S라 하면 사용한 스택은 아래와 같다.

| 주소 | 내용 |
|---|---|
| S−10 | callback return2b6, long |
| S−6 | VRAM 주소, word |
| S−4 | 원래 A5, long |

이 시점 A5는 콜백 주소이며20c 경로처럼108000을 유지하는 것이 아니다. 활성 진입에서는 아직 interrupt acknowledge를 쓰지 않는다.

## 콜백 반환 뒤2b6

`finish_raster_irq` 입력 A7은 콜백 RTS 이후 S−6이다. 먼저3c000c.word에2를 쓰고, 스택의VRAM word를RAM104d8e와3c0000.word에 복구한다. 그word와 다음A5.long을 소비하고2cc의RTE 직전에 멈춘다. A7은 입력+6이고 스택 쓰기는 없다.

이 IRQ는 **A5만 저장·복원**한다. 콜백이 바꾼 D0..D7/A0..A4/A6은 종료 뒤에도 남는다.20c의 전체 레지스터 복구를 재사용하지 않는다. 콜백이 스택의VRAM/A5 내용을 바꿨다면 변경된 바이트를 복구 입력으로 사용한다.

## API 경계

외부 stack base/길이는 기존 IRQ envelope 규격이다. 활성 begin은A7=11000a..fffffe 짝수와 `[A7−10,A7)`를 요구한다. finish는A7=110000..fffff8 짝수와 `[A7,A7+6)`를 요구한다. 비활성 begin API는 사용하지 않는 스택을 검사하지 않지만 CLI는 파일 규격을 검사한다.

성공 결과의 next_pc는 콜백 주소 또는2d6/2cc이며 bios_handoff는false다. 실패는 RAM·스택·레지스터·결과·포트를 보존한다. 원본 SR/CCR·RTE·예외 프레임과 장치 시간축은 아직 출력 계약에 포함하지 않는다. 기본 콜백3dcc는 기존 `return_default_irq_callback`으로 처리할 수 있다.

```sh
build/step_irq_envelope raster-begin INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE
build/step_irq_envelope raster-finish INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE
```

## 원본 비교

`.venv/bin/python tools/verify_raster_irq.py`: 386조건(begin279/finish91/기본RTS16), 오류/별칭23조건 통과. 전체 RAM·명시적 스택·16개 레지스터, 순서 있는 MMIO314개 및 실제 스택 쓰기441개를 비교했다. 모든256개fd80, VRAM/A5 경계값, 최소/최대 스택과 최소 buffer,16개 begin→실제3dcc RTS→호스트 레지스터 변경→finish 승계를 포함한다. RTE 직전은 명시적 code hook으로 중단한다.

보고서 `artifacts/raster_irq/verification.json`, SHA256 `80591506798ab679b7a31376b4d5e41b40e69326a92498d7d0b9b2e5547ee91d`. 원본 ROM은 불변이다. 임의의 콜백 본문과 RTE/예외 프레임·장치 시간축은 아직 검증하지 않았다.
