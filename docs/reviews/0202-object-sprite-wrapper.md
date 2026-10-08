# Object sprite wrapper 16ea4 리뷰

Baseline `297bc1c`, branch `codex/object-sprite-wrapper`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, 원본 비교를 분담했다. 메인은 원본16ea4..16ecc, 새 core·unit·CLI·검증기와 기존 sprite callee를 읽었다. 별도 Sol의 독립 core 리뷰에서도 조치할 문제는 없었다.

Fresh 호출은 A5=108000/D3=0, object flag와 두 WORD 좌표, D1 LONG 및 D5.low를 원본 순서로 읽고 cd58을 호출한다. SWAP과 WORD wrapping을 명시적으로 유지한다. SUBX의 X는 바로 앞 LSR에서 나오므로 ADD carry를 재사용하지 않는다. D2 상위24bit와 D5 상위WORD를 보존한다. 기다리는 호출은 캡처된 A5를 검사하고 object/A6를 읽거나 좌표 전처리를 반복하지 않는다. 기본callback cd50 제한을 clip 앞에서 그대로 검사한다.

외부 transaction은 fresh 전처리와 기존 callee 전체를 감싼다. 늦은 queue/record 실패에서도 RAM/15registers/waiting/status를 보존한다. 실제 접근 주소만 검사하며 fresh object base 자체에 추가 제약을 만들지 않는다. A6=fffee/10ffac 경계도 허용된다. API 단위는 callback-before-clip, 잘못된 pending A5, poison된 wait/hold/release, 늦은 실패 rollback과 변환 overflow를 검증한다.

- `tools/verify_object_sprite_wrapper.py`: 원본96조건/112단계의 전체 RAM/15registers/status/waiting과 actual CLI 일치. 모든112단계를 원본 CPU에서 재실행했다.
- 8개 연속대기 연쇄의16회 재개는 직전 실제 C++ 출력 RAM/register/waiting에 기록된 외부 RAM 변화만 적용한다. 기대 native 상태를 다음 C++ 입력으로 주입하지 않는다.
- 별도 public snapshot에서 A6=0/ffffffff로 바꾼 hold/ready4단계도 원본과 C++가 일치했다. 원래96조건의 변경 없는 이력과 구분한다.
- 정상6개 callee 조건분기 양쪽, 원본 RAM쓰기204회 관측. 오류·파일 보존139조건 및 실제case alias/FIFO 검사 통과.
- 전체 `make -j4 all test` exit0, Python196/C++143/경고0. 로그 `artifacts/object_sprite_wrapper_build_test.log`. core의 격리 C++11 normal/UBSan 실행도 통과했다.
- Native SHA `49b4e745f9243d6c6b044e81327c7cbaa5122c2d051d8bdfe9734793ea95c525`.
- Verification SHA `41f926ba31a51a813b5e9c965767e94c1b1e8d2f6a58e758689d9aab5d9b97a5`.
- CLI SHA `4f1f25f01dd46f2b624f1f0c40f68fbae5b033ec79301e635f32ae89a1152906`.
- 메인이 source.json과 C++ 단계별 RAM을 포함한256개 현재 참조파일 hash를 직접 대조했다.

이번 wrapper는 새 ROM 리소스를 읽지 않는다. 임의callback, 자연IRQ/scheduler, 전체CCR/cycles/물리mirror/전체stage를 지원한다고 주장하지 않는다. 실제 상위 callback과 전체게임은 계속 미완료다.

## 다음 사운드 lookup 원본 준비

47672의 실제원본277조건/291단계/6같은CPU 대기연쇄를 확보했다. 원본 프로그램을 바꾸지 않고 ca70/3af8/47672를 실행했으며 saved A0와 high/low phase를 실제 stack에서 읽었다. raw WORD 주소4411e..4421c의128개 전부를 관찰했다. wrapper 조건분기 세 개는 양쪽 경로를 관찰했다. 전체sound gate coverage라는 뜻은 아니다.

메인은 observer와 직접 disassembly를 읽고7개 입력/873개 단계 파일 해시를 확인했다. object destination이source+1일 때 BYTE 쓰기 후 live WORD를 읽는 순서, signed queue index bbda의 sound 쓰기가 source를1ac0으로 바꾼 뒤 wrapper가 다시 읽는 순서를 보존해야 한다. 원본 SHA `42f093ee7d31dbd3e70b986dd7d7edd7fc409eeb543892ff5c3c6d4494e99f5d`. 실제256byte lookup의 runtime packer/C++ loader 연결과 wrapper 구현은 다음 단위다.

## 전체 animation 복원의 확인점

메인이49fc6..4a468의 제어흐름을 읽고 draw/sound/callback의 보관 상태와 bank 출력 경계를 분석했다. 특히 MOVEM.W 복원은 D0/D7 상위WORD를 보존하지 않고 부호 확장한다. 원본 세instruction을 합성 stack으로75조건 실행하여 이를 확인했다. 재현도구와 제한은 `docs/analysis/animation-full-register-boundaries.md`에 기록했다. 이것은 전체49fc6 실행·pending 검증이 아니다.

별도 Sol은47672의 전체RAM쓰기606개를 재생하고 대표20조건/34단계를 원본CPU로 다시 실행했다. 여섯대기 연쇄와 source-low/shiftedA5/queue alias가 일치했다. 대기14단계(high8/low6)의 saved_low는 실제 stack/D0에서55로 관측되므로 호출자가 요청한 명령1ac0의lowBYTE라고 가정하지 않는다. native observer의 mutate는 외부상태를255로 바꾸지만 phase host_changes는 RAM만 기록한다. 소스해시로 재현되고 재개 중 외부읽기는 없지만 후속 verifier에서 이255를 명시한다.
