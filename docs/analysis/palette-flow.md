# 팔레트 준비·전송 경로

대상 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 ROM 주소는 파일 오프셋과 같다. 아래 bank 영역은 해당 경로가 설정한 base=0x200000에서 CPU 주소와 파일 오프셋이 같다.

## 원본에서 확인한 경로

0x7196 경로는 A5=0x108000일 때 A2=0x104d92(16바이트 단위 제어 레코드), A4=0x105da2(32바이트 단위 staging)를 설정한다. 0x71ac..0x71b4에서 PVC에 0x1000/0을 쓰고, CPU 0x200004의 long을 A6, 0x200008의 long을 A3에 읽는다. 실제 데이터는 각각 0x22bd12와 0x25cb52다.

0x71d8은 제어 레코드 +0xf bit7을 검사/해제한다. +0xa/+0xc word가 같으면 ID×32를 A6에 더하고 0x4718을 호출한다. 다르면 0x4c40으로 분기하며 이 혼합 경로는 아직 해석하지 않았다. 처리 후 staging 첫 word를 0x8000으로 설정한다. A2+=16, A4+=32로 반복하여 A4=0x107da2에서 끝나므로 256개 슬롯이다. 다른 조건에서 진입하는 0x7252 분기도 남아 있다.

0x4718은 source와 destination의 첫 word를 건너뛰고 15개 word를 처리한다. 각 source word를 두 배로 만든 결과의 하위16비트를 **부호 확장**하여 A3 상대 주소로 사용하고, 조회된 word를 destination에 저장한다. 단순 unsigned 배열 인덱싱으로 옮기면 다르다. A4는 복원하고 destination 첫 word는 보존한다. tools/analyze_palette_flow.py로 probe ID 0..15의 실제 원본 실행과 이 주소 계산 결과를 비교했다. 이는 ID들의 실제 게임 사용이나 테이블 전체 길이를 증명하지 않는다.

0x72fa의 wrapper는 A5-0x216과 A5-0x213에 따라 다른 경로로 분기한다. 정상 전송에서는 0x7316이 staging 첫 word를 0x8000으로 마스킹한 후, 0x7320에서 전송 커널을 시작한다. 이 전처리는 커널 API에 포함하지 않았다.

0x7320..0x871a는 256회 펼쳐진 bclr/beq/movem 시퀀스다. 각 32바이트 staging 블록의 첫 byte bit7을 지우고 이전 값이 1이었을 때만 32바이트를 CPU 0x400000+block×32에 복사한다. bit를 지운 뒤 복사하므로 표시 비트는 destination에 전달되지 않는다. pinned MAME neogeo.cpp의 메모리 맵은 0x400000..0x401fff를 paletteram으로 지정한다.

## C++ 재구성과 검증

`ms5::upload_dirty_palette_blocks`는 전송 커널의 staging/destination 메모리 효과만 구현한다. 두 버퍼는 서로 겹치지 않는 8192바이트 이상 영역이다. ROM 팔레트 리소스 전체 추출, wrapper, bank 선택, RGB 변환 및 장치 타이밍을 구현했다고 주장하지 않는다.

```
make build/upload_palette
.venv/bin/python tools/verify_palette_upload.py
.venv/bin/python tools/analyze_palette_flow.py
```

259개 입력(각 슬롯 단독 dirty 256종, 전부 clean, 전부 dirty, 교대 dirty)에 대해 원본 M68000 커널 실행과 staging+destination 16384바이트 전체가 일치했다. 원본 경계 guard도 확인했다. 결합 출력 SHA256: `68166404913b26b452b186a5cacad94e836a0549e17013394d9f6f2ae5ccb66b`.

다음 과제: ID 상한과 source 범위 검증, 제어 레코드 작성자 추적, 혼합/보정 함수 분석, 하드웨어 색상 인코딩 확인, 공통 팔레트 리소스 규격과 C++ 소비 경로 연결. 근거가 없는 길이로 ROM을 잘라 최종 팔레트 카탈로그라고 명명하지 않는다.
