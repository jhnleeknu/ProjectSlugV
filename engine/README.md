# C++ 런타임 기반

현재 구현은 MS5T 타일 카탈로그 로더다. 플레이 가능한 게임이나 애니메이션 엔진은 아직 아니다.
C++11 기본 문법으로 작성하며, 리소스 규격은 ../docs/resource-format.md를 따른다.

저장소 루트에서:

```sh
make setup-tools
python3 tools/decode_tiles.py
python3 tools/verify_tiles_reference.py
python3 tools/pack_tiles.py
make
./build/check_tiles extracted/runtime/sprites.ms5t extracted/runtime/fixed.ms5t
make test
```

사전 입력은 검증된 extracted/media/ 데이터다. 이 입력을 만드는 단계는 docs/analysis/media-decryption.md에 있다.
런타임은 PNG 미리보기가 아닌 .ms5t 파일을 읽는다. 팔레트와 오브젝트 조합은 후속 작업이다.
check_tiles는 현재 파일 검증 CLI이며 렌더링 화면을 제공하지 않는다.
테스트 실행은 macOS/Linux POSIX 임시 파일 API를 사용하고 로더 자체는 표준 C++11이다.
