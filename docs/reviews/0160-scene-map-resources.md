# 장면 경로·맵 리소스 C++ 소비 리뷰

Baseline `a4ad8ae`. 직전 사용자 응답은 화면 실행 가능 여부를 설명한 상태 보고로 no progress였다. 이번에는 실제 작업 파일과 보고서를 재확인하고 미통합 변경의 리뷰·검증·기록을 완료했다. Canonical decrypted source SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다.

## 계약과 구현 리뷰

기존 MS5D v1을 사용하며 새로운 container format을 만들지 않았다. Kind1 path72개는 고정 CPU=ROM, kind2 primary root/lookup/map79개는 bank3 CPU+100000=ROM 관계를 보존한다. 총151개,765048 payload bytes다. 원본 게임 데이터는 ignored extracted 디렉터리에만 둔다.

메인이 packer, typed decoder/accessor, 두 CLI, 합성 unit과 독립 비교 도구를 읽었다. Map extent 계산은 uint64로 승격한 뒤 4+4*width*height를 검사한다. Cell offset은 bank window에 들어가는 확정 span 안에서 column-major로 계산하며 두 BE16 word와 CPU/ROM 주소를 반환한다. Raw header와 cache dimensions 불일치도 거부한다. 출력은 성공 후에만 게시한다.

Path decoder는8 opcode의 operand bytes를 보존하고 negative WORD가 정확히 마지막에 있어야 한다. Branch pointer는 원시 주소로 유지하며 실행하거나 도달성을 판단하지 않는다. Packer는 canonical의 연속 경로만 지원하고 cycle·불연속 경로를 거부한다. 이 제약을 전체 interpreter의 지원 범위로 바꾸지 않는다.

리뷰에서 빈 payload 허용, 중복 root/파일 이름에 의한 덮어쓰기 가능성, 참조 metadata와 raw operand의 불충분한 대조를 발견했다. 빈 payload 거부, root uniqueness 및 nonzero reference 집합 일치, 파일명/ID 중복 거부, raw >HI selector/pointer 및 각 path reference 목록 대조로 수정했다. 추가 합성 테스트를 확인했다. 재생성 후 manifest와 모든 resource hash는 변경되지 않았다.

## 검증

- 전체 빌드 로그 `artifacts/scene_map_resources_build_test.log`: 당시 Python152, C++103 실행, 경고0. C++ 변경은 그 뒤 없다.
- Packer 보강 후 `.venv/bin/python -m unittest discover -s tools/tests`: Python154, exit0. 로그 `artifacts/scene_map_resources_python_tests.log`.
- `.venv/bin/python tools/verify_scene_map_resources.py`:151 container의 header/CRC/주소/전체 payload 원본 일치. Typed C++ 소비 대상은 path72+map77의149개이며 root/lookup2개는 Python에서 연결 관계를 검사한다.
- Path218행(positive146/terminal72)과 map190707셀을 C++ 출력으로 재조합해 원본 전체 bytes와 비교했다. 오류39조건 통과. Read-only CLI의 입력 보존과 C++ unit의 API 결과 보존을 구분한다.
- Report SHA256 `7d799705deddddfc37482d63fdc9aa8ee4b903594f8064bf89d048e3df3ed6ec`, manifest `8312156694a7cf20a6782ad6834285965734c579cb532e09d82f40839080411e`. 메인이 보고서와 현재 두 binary,151 container hash를 다시 대조했다.

## 남은 작업

183c6의 clipping/VRAM/cache 쓰기, bank2 secondary 데이터,19e64 handler 실행,1afda 전체 register 승계, 일반1a5a4와47a94 이후 실행 연결이 남아 있다. 현재는 native resource의 실제 C++ 소비까지이며 스테이지 화면·자연 시간축·조작 가능한 게임이 아니다. 알려진 참조가 없는8개 map을 미사용으로 확정하지 않는다. 전체 목표는 active이며 완료로 표시하지 않는다.
