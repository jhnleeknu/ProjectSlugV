# 오브젝트 필드 초기화의 C++ 재구성

## 원본 근거
고정 프로그램 SHA256 29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f의 CPU 0x271c 루틴을 분석했다. 호출 경로는 0x8eb6, 0x43dcc→0x43dda, 0xc3dc→0x4aa06/0xe90ca/0x46eec이다. 모두 이 분석 범위에서는 고정 ROM 주소다.

엔진 API: ms5::reset_object_fields. 계약은 0xc4바이트 오브젝트의 메모리 효과이며 68000 레지스터·CCR·호출 스택 자체를 재현하는 API가 아니다.

| 초기화 | 오프셋 또는 범위(끝 제외) |
|---|---|
| 0 | 0x1d, [0x2e,0x54), [0x64,0x68), [0x54,0x5a), 0x5e, 0x60, [0x72,0x76), 0x6a, 0x15, [0x61,0x64), [0x76,0xc4) |
| 0xff | 0x17, 0x6b, 0x6c, 0x6d, 0x12, 0x13 |
| big-endian 0xffff | 0x5a, 0x1e |
| big-endian 0x0040 | 0x6e |

그 외 바이트는 그대로 보존한다. 전체 memset(0)로 바꾸면 원본과 다르다. 의미가 미확인인 필드에 임의로 좌표·HP 이름을 붙이지 않았다.

## 원본 CPU 실행과 비교
Unicorn 2.1.4, CPU 모델 M68000을 명시했다. 기본 모델을 사용한 초기 시도에서는 ADDA.W에서 예외가 발생했다. 모델 지정 후 원본 명령이 정상 복귀했다.

- 5가지 고정/순차 패턴 + 결정적 SHAKE256 패턴 256개 = 261개.
- 각 케이스 원본 ROM 0x271c를 helper 호출까지 실행했다.
- 실제 RTS 복귀 PC와 A0 복원을 확인했다.
- 오브젝트 양옆 16바이트 경계값이 유지되는지 확인했다.
- C++ 실행 결과와 196바이트 전체를 비교해 모두 일치했다.
- 비교 출력 SHA256: 4b38dc0ca9a1132f682c342ea31a5484aa11ce62bef2b3a3c1ea25d11d7d1283.

```sh
make setup-tools
make all
.venv/bin/python tools/verify_object_reset.py
make test
```

결과: artifacts/object_reset/verification.json. 원본 바이너리·비교 RAM 데이터는 Git에서 제외한다.

## 한계
이것은 실제 ROM 명령을 사용하는 CPU 단위 실행 비교다. 네오지오 BIOS·장치·게임 부팅 검증은 아니다. C++ 함수는 메모리 효과를 보존하며 원본 CPU 레지스터를 노출하지 않는다. 콜백 목록 초기화, 프레임 처리, 오브젝트의 실제 그래픽은 후속 작업이다.
