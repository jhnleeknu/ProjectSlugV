# c654 ready gate와 c686의 후속 준비

원본 프로그램 `extracted/program/maincpu.decrypted.be.bin` SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 ROM CPU 주소는 고정 파일 오프셋과 같고 RAM offset은 CPU 주소에서100000을 뺀 값이다. `artifacts/game_ready/inventory.asm`의 bounded 원본 명령과 메인의 해석을 구현 근거로 사용했다. 목록의 선형 디코딩 자체는 실행 검증을 대신하지 않는다.

## 진입과 실제 종료 경계

`GameReadyState`는 next_pc 및 전체 D0/D1/D3/A6를 담는다. `step_game_ready`의 입력 PC는 c654/c66a/c686/c6c0이고 출력은 c724/c73e/c00444 중 실제 원본 도달 경계다. 이 경계의 body를 실행하거나 RTS 반환 PC를 만들지 않는다. A6는 절대 CPU RAM 주소이며 c4-byte 범위를 가진 짝수 오브젝트여야 한다. RAM은 정확히65536byte다.

c654는 고정 오브젝트100b30을 callback477e4로 정적 restart한다. 팔레트·coordinate cleanup과 field reset은 기존 `restart_static_object`를 사용한다. watchdog에는 입력 D0.byte를 쓰며 D1/D3는 해당 helper의 전체 반환값을 승계한다. 271c의 최종 D0=0도 반영한다. 고정 오브젝트의 depth.word가nonzero이면 지원하지 않는 원본TRAP 경로로 오류를 반환한다. 현재 A6의 callback을c66a로 쓰고 같은 호출에서 c66a gate로 진행한다.

c66a는 고정100b30 callback이270e가 아닌지 확인한다. callback=0도 active다. active이고 RAM4cd4.byte==1이면c724에서 멈춘다. inactive 또는 replay flag가1이 아닌 경우 c686으로 진행한다. c66a 자체는 D0/D1/D3를 바꾸지 않는다.

## c686 준비와 allocator의 정상 실패

c686은 원본ROM180.word를 검사한다. 이 API는 canonical ROM180.word=0만 지원한다. 다른 값에서 ROM을 지우고c610으로 돌아가는 경로는 명시적으로 제외하며 ROM을 수정하지 않는다.

0 경로는 c4cc 오브젝트 정리, caf0 screen reset, ca76의RAM965.byte=ff를 순서대로 실행한다. 제거에서 실제 반환된 A6와 D0/D1/D3를 승계하고 watchdog·VRAM 포트도 그 순서로 누적한다. caf0의2072개 port를 생략하거나 화면상 결과로 대체하지 않는다. 관련 계약은 [object-removal.md](object-removal.md) 및 [object-allocation.md](object-allocation.md)를 따른다.

이어 A0=e66aa, D0.low=0으로28ae allocator를 호출한다. D0 상위 word는 보존한다. API에 운반하지 않는 scratch A1 입력은0으로 두며 allocator의 실제 D0를 반환한다. D1/D3는 allocator가 바꾸지 않는다. 원본은 carry를 검사하지 않으므로 free count0의 정상 실패에서도 후속 처리를 계속한다. 잘못된 포인터 등의 **API 오류**는 정상 실패와 구분하며 전체 작업을 rollback한다.

현재 A6+62.byte=0, 현재 A6.callback=c6c0을 live로 쓴 뒤 같은 호출에서 c6c0을 실행한다. 따라서 이 경로는c73e에 도달한다. allocator가 저장한e66aa callback과 static restart의477e4 callback은 설치만 하며 실행하지 않는다.

c6c0 단독 진입은 live A6+62.byte가0이면c73e, nonzero면BIOS 경계c00444로 간다. 경계에서 멈추고 BIOS를 실행하지 않는다. 이 단독 진입은 RAM 및 반환 D0/D1/D3/A6를 그대로 유지하며 포트가 없다.

## 오류와 실행 계약

RAM/state/ordered ports는 하나의 transaction이다. c654의 정적 cleanup, c686의 연결 제거, caf0 포트 생성이 성공한 뒤 late allocation 오류가 생겨도 caller의 RAM/state/기존 ports를 보존한다. 성공 시 ports는 이번 호출의 새 목록으로 교체된다.

지원하는 포인터/링 범위와 제거 budget은 기존 helper 계약을 따른다. 임의 outside-RAM CPU 주소, 원본 TRAP 처리, 다른 레지스터/전체CCR/stack 동등성, callback bodies 및 scheduler는 이 API에 포함하지 않는다. ready라는 이름을 stage gameplay 완료의 의미로 확대하지 않는다.

## CLI와 재현

```sh
build/step_game_ready PC D0 D1 D3 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS
```

숫자는 unsigned32 decimal 또는0x hex다. 입력 RAM은 정확히65536byte며 세 파일의 canonical/hardlink/symlink alias를 거부한다. API 검증이 끝나기 전에 output을 열지 않는다. JSON은 next_pc/d0/d1/d3/a6/writes다. 포트 레코드는 size(byte)/address(BE32)/value(BE32) 각9byte다. 별도 runtime 리소스는 이 경계에 필요하지 않다.

```sh
make build/step_game_ready build/game_ready_test
./build/game_ready_test
python3 tools/verify_game_ready.py
```

C++11 targeted build와 단위 테스트가 통과했다. 테스트는 active callback0/inactive270e와 replay0/1/2의 gate, c654 같은 호출의 fallthrough, c686 cleanup/screen/allocation 순서, 정상 allocator 실패에서도callback/flag를 설치하는 원본 동작, c6c0의두실제경계, late cleanup/allocation 실패의 전체 port/RAM/state 보존을 검사한다.

## 원본 비교 상태

`artifacts/game_ready/verification.json` 최종 실행은 Unicorn2.1.4에서 원본246조건/오류39조건을 통과했다. 전체 RAM/D0/D1/D3/A6와 순서 있는 port274484개가 일치한다. 원본 코드와ROM180.word=0을 유지하며 실제 중첩 함수를c724/c73e 또는BIOS c00444까지 실행하고 **해당경계명령 실행전에** 멈춘다.

원본2790 runtime list와 실제 MS5I CLI 결과를 대조한 fixture를 사용하고, palette cleanup은 원본3ef2/8ebe로 구성한다. predicate144조건, c6c0 두경계20조건, 정상allocator실패 및 사용하지않는 invalid freehead6조건, coordinate64조건, palette6조건과승계6호출을 포함한다. malformed pointer/원본TRAP에 대한39오류조건은 원본실행없이출력보존을검사한다.

승계4시퀀스 중2개는 각각2호출의 실제CLI RAM/전체register를재진입에넘긴다. 호스트가 controller+62.byte를ff로 바꿔 두번째호출의BIOS경계를선택하는fixture이며e66aa를실행한결과로취급하지않는다. 나머지2개는 실제restart CLI와원본c610의동일RAM/전체D0D1D3A6를확인한뒤두caller의c654 explicit callback 진입에넘긴다. callback477e4/e66aa는저장만확인하고body를실행하지않는다. 자연scheduler 호출을검증했다고주장하지않는다.

BIOS 실행, 자연 호출자·IRQ·hardware timing, 다른 CPU register/전체CCR/stack 동등성 및 이후c724/c73e/callback body는 범위 밖이다. 최종보고서 SHA256은 `4f09a7ef5db74efe5b5ab29bf8a4646cf9cb49145dc5c05a2508e0dcffc1fe17`다.
