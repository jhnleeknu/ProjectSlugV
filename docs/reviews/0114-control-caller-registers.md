# 컨트롤러 반환 이후 D1/D3 리뷰

대상 기준 커밋: `d508b02`.

메인이f5a..ff6,8be0/8c16..8cc8의원본명령과기존팔레트helper를확인했다. f5a의byte쓰기,효과시작MOVEQ,16비트차이와DIVS의나머지/몫packed결과,복구전middle byte읽기를구분했다. palette blend의최종D3.word도반환한다. signed quotient/remainder와고정폭변환은C++11정의된연산을사용한다.

- `make -j3 all test`:Python73개및C++전체검사통과,경고없음. 로그 `artifacts/control_caller_registers_build_test.log`.
- 추가단위검사후 `make build/control_caller_test && ./build/control_caller_test` 통과. status우회D1byte보존,변화없음D1ffff0000/D3zero,늦은리소스실패의모든출력롤백을확인했다.
- `.venv/bin/python tools/verify_control_caller_registers.py`:322조건/27,858포트/오류14조건통과. 전체RAM과32비트D1/D3를원본에서직접비교한다.
- 메인리뷰에서새register인자의파싱오류보존과네가지팔레트helper도달확인을보강했다. 합성return주소는Unicorn종료조건이hook보다먼저적용되므로helperhit필수목록에서제외하되종료PC는별도검사한다.
- 보고서SHA256 `8b636bf7b93621d7b7787618b630ad6c4fd8b189961da7ed9d26a31209511960`.

이번입력은9136직후레지스터다. 9136본체의반환값이나연속프레임의모든CPU문맥까지자동으로생성하지않으며다음작업에서연결한다. 임의콜백·전체부팅·SR/RTE/BIOS·물리시간축은미완료다.
