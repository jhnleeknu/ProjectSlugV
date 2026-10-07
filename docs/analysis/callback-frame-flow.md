# 콜백 이후의 팔레트 처리와 다음 입력 대기

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU f46/f4c/f12와5728은 같은 복호화 ROM 오프셋이다.

메인 콜백에서 반환하면 f44가 원래 오브젝트A6를 복구한다. f46은5728을 한 번 호출한다. 팔레트 처리가 끝난 뒤 f4c는 RAM100016.byte를 검사하고0이면 f4c로 돌아가며,0이 아니면 f52에서 f12로 분기한다.

기존 ef2 대기는 RAM16>=RAM17을 요구하고 비디오 상태를 읽어RAM18을 갱신한다. **f4c는 RAM16!=0만 요구하며 RAM17을 읽거나 비디오를 읽지 않는다.** 특히 RAM17=0이어도 신호0은 계속 기다리고, RAM17=255여도 신호1로 진행한다. RAM18은 이 대기 구간에서 유지된다.

`poll_callback_input_control`은 f4c를 한 번 관찰한다. 기다리면 next_pc=f4c, 입력style 그대로, 입력읽기0과 빈포트를 반환하고RAM을 유지한다. 이때 쓰이지 않는 오브젝트·리소스는 API에서 검사하지 않는다. 신호가 있으면 기존 `step_input_control`로 f12 입력 소비와 callback/controller 분기를 수행한다. RAM16은 RAM1a에 옮긴 뒤0으로 소비된다. 오류 시 모든 API 출력은 보존된다.

호출자는 f46에서 `step_palette_frame`을 한 번 실행하고 반환D1의 하위16비트를 다음 poll의 style로 전달한다. 대기 중에는 팔레트 함수를 다시 실행하지 않는다. 신호 생성은 IRQ 서비스의 책임이며 poll이 신호를 만들거나 바쁜 루프로 기다리지 않는다. 이 구분으로 프레임 대기마다 효과 타이머가 잘못 감소하는 것을 방지한다.

```sh
build/step_input_control --callback-poll INPUT_RAM STREAMS_MS5D STATUS_TABLE_MS5D MENU_MS5D PAUSE_MS5D PALETTES_MS5P OUTPUT_RAM OUTPUT_PORTS OBJECT_ADDRESS STYLE LINE ENTRY_STACK SYSTEM P1_RAW P2_RAW P1_GAME P2_GAME [FONT_MS5D [STAGES_DIRECTORY]]
```

결과style은 기존 계약대로 입력 처리 경계의D1.word다. 뒤이어 controller가 실행된 경우의 최종 모든CPU레지스터를 뜻하지 않는다. CLI는 API와 달리 먼저 지정 리소스 파일을 로드한다.

SR/RTE/BIOS·장치 시간축과 자연 인터럽트 전달, ec4 앞부분 및 임의 콜백 본문 실행은 아직 미완료다.

## 검증 결과

`.venv/bin/python tools/verify_callback_frame_flow.py`: 원본537조건(메인poll524,IRQ5,팔레트5,스택단계3), 포트286개 및 오류5조건 통과. 모든256 신호값과 임계값0/255를 조합한512조건에서RAM18 유지와 비디오읽기0을 확인했다. 이 행렬의 신호는 명시적 초기 fixture다.

네 가지 팔레트 경로(복사/보정/혼합/혼합후보정)에서 실제 f46 JSR5728을 실행하고 반환D1을 대기와 다음입력에 전달했다. A5/A6/A7 보존도 확인했다. 이어 실제c8c 서비스가 신호를 생성하며 기다리던 메인 CPU 문맥은 호스트가 명시적으로 복구한다. 연속 사례에서는 신호를 호스트가 덮어쓰지 않는다.

별도 한 주기는 f12 입력→f3c 실제 스택 호출→원본3dcc RTS→f44 복구→f46 팔레트→f4c 대기→IRQ→다음 입력을 연결했다. 각 C++ 단계와 전체RAM/관련레지스터/스택/포트가 일치한다. 전체 CPU 명령을 재구성한 에뮬레이터나 자연 인터럽트 시간축을 검증한 것은 아니다. 일반 controller 경로의 추가 팔레트 호출은 대기 반복과 구분한다.

보고서: `artifacts/callback_frame_flow/verification.json`.
SHA256: `cc6c268073de463fd30f29c40171d8d021268274622735763c9333994950852d`.
