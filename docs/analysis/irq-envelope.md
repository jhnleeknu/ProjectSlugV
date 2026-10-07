# IRQ 진입과 종료의 저장 프레임

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
CPU20c..23a 및248..29a는 고정 ROM의 같은 오프셋이다. `irq_envelope.h/.cpp`는 외부 콜백·BIOS 호출의 앞뒤에서 실행되는 게임 코드를 표현한다.

## 진입20c

`begin_irq_envelope`는 먼저3c000c.word에6을 쓴다. RAM10fd80.byte가 음수가 아니면 BIOS c00438로 넘기는 결과를 반환한다. 이 경로에서는 RAM·레지스터·스택을 변경하지 않으며 사용하지 않는 스택 주소도 API가 검사하지 않는다. SR/CCR은 별도 범위다.

음수이면 D0..D7/A0..A6을 MOVEM.L predecrement로 저장한다. 실제 쓰기 순서는 A6..A0,D7..D0이며 원래 A7보다60바이트 아래까지 사용한다. A5를108000으로 설정한 뒤 RAM104d8e의 VRAM 주소 word와 RAM100010의 bank word를 차례로 push한다. A0에 RAM100006.long을 읽고 JSR(A0)의 복귀 주소23c를 push한다. 결과 next_pc는 A0, A7은 진입 값−68이다. 콜백 본문은 실행하지 않는다.

진입 A7을S라 하면 저장 프레임은 다음과 같다.

| 주소 | 내용 |
|---|---|
| S−68 | 콜백의 복귀 주소23c, long |
| S−64 | bank, word |
| S−62 | VRAM 주소, word |
| S−60..S−1 | D0..D7/A0..A6, 15개 long |

## 종료248

`finish_irq_envelope`의 입력은 c0044a BIOS 호출이 돌아온248 경계다. A7은 위 프레임의S−64를 가리켜야 한다. 이 API가 콜백·c8c·BIOS를 대신 실행하거나 중간 RAM/레지스터를 추측하지 않는다.

3c0004.word를0으로 만들고 A5를108000으로 설정한다. 스택에서 bank를 읽어 RAM100010에 복구한 뒤, 현재 D7/D0의 하위 word를 predecrement로 임시 저장한다. 실제 주소는 입력A7과 입력A7−2다. 이미 읽은 bank 위치가 D7.low로 덮어써지는 것도 보존한다.

PVC2ffff2.word에 `((bank+1)<<12)&ffff`,2ffff0.word에0을 쓴다. 연산은16비트이며 bankffff도 허용한다. 원본은 임시 D0/D7을 MOVEM.W로 다시 읽지만 이후 최종 MOVEM.L에서 저장된 원래 레지스터로 덮어쓴다. 그 사이의 임시 확장은 결과 레지스터가 아니며 스택의 실제 word 쓰기는 결과에 남긴다.

다음 word를 VRAM 주소로 읽어 RAM104d8e와3c0000.word에 쓴다.3c0006.word의 bit3을 읽어 RAM100002.byte를ff 또는0으로 갱신한다. 마지막에15개 레지스터를 실제 입력 스택에서 복구하며 A7은 입력+64다. 반환 next_pc29a는 **RTE 실행 전**이다. 예외 프레임·SR·복귀PC 복원은 아직 포함하지 않는다.

## 외부 스택과 실패 계약

스택은 base 주소와 byte vector로 전달한다. base는110000 이상, fffffe 이하의 짝수이며 길이도 짝수다. 끝 주소는1000000 이하다. 작업 RAM과 겹치는 스택은 지원하지 않는다.

- 활성 진입은 A7=110044..fffffe의 짝수이며 `[A7−68,A7)` 범위가 필요하다.
- 종료는 A7=110002..ffffbe의 짝수이며 `[A7−2,A7+64)` 범위가 필요하다.
- BIOS 우회는 스택을 사용하지 않아 API가 범위를 검사하지 않는다. 진단 CLI는 파일 규격으로 base/길이를 항상 검사한다.

결과 `stack_writes`는 size/address/value 순서의 실제 스택 쓰기 기록이고 stack vector도 함께 갱신된다. MMIO는 별도 ports에 담는다. 지원하지 않는 주소나 크기로 실패하면 RAM·스택·레지스터·결과·포트를 모두 보존한다. 콜백이나 BIOS가 저장 프레임을 변경한 경우 종료 API는 변경된 입력 바이트를 읽는다. 진입 당시 별도 구조체 사본을 원본보다 우선하지 않는다.

```sh
build/step_irq_envelope begin INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE
build/step_irq_envelope finish INPUT_RAM INPUT_STACK INPUT_REGS OUTPUT_RAM OUTPUT_STACK OUTPUT_REGS OUTPUT_PORTS STACK_BASE VIDEO_STATUS
```

RAM64KiB, REGS16개BE32, STACK가변 byte span이며 MMIO 진단 파일은 기존9-byte 규격이다. 모든 입력·출력 파일 별칭은 거부한다.

현재 제공된 mslug5.zip의13개 항목에는 게임 P/C/M/V ROM만 있으며 BIOS가 없다. c00438/c0044a의 내부 동작을 원본 BIOS 비교로 확인한 것으로 기록하지 않는다. 다른 게임 코드 분석과 구현은 계속할 수 있다.

## 원본 비교 및 콜백 슬롯 근거

`.venv/bin/python tools/verify_irq_envelope.py`: 원본1,342조건(독립1,310 및16개 연속 진입/종료 쌍), 오류/별칭20조건 통과. 전체 RAM·스택 buffer·16개 레지스터·MMIO·시간 순서의 실제 스택 쓰기·비디오 읽기 횟수를 비교했다. 모든256개fd80, 비디오 하위byte256개와 네 상위byte, bankffff 순환, 스택 최솟값/최댓값과 BIOS의 미사용 스택을 포함한다. 원본은 변경하지 않았다. 보고서 SHA256 `3a0116a7b2da28ed49999cfbfd306291247b6c2720be9241dd781d35a5b7b06b`.

`tools/analyze_irq_callback_refs.py`의 정적 조사에서 RAM100006 참조는236/3dd8, RAM10000a 참조는2b0/3dde에 발견된다. 메인이 원본3dcc..3de4를 확인했다.3dce는RAM104d91.bit4를 지우고 A0=3dcc를 두 슬롯에 저장한다.3dcc는RTS다.3dce 직접 호출 후보는9e4/c4cc/475e6/477dc다.

이 결과는 로컬 명령·데이터 흐름 근거다. 모든 런타임 콜백이 항상3dcc라는 의미가 아니며, 동적 주소·간접 쓰기·뱅크 코드·변형 RAM 코드는 조사 밖이다. 원본 게임의 자연 실행 도달성은 별도 확인한다. 슬롯 보고서 SHA256 `82881d4f8233e31d372dc3036225f4c1080ce962811d28579c77f4d20fa72bbc` (`artifacts/irq_callback_refs/report.json`).
