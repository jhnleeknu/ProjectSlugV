# Stage activation prefix C++ 연결 리뷰

Baseline `4707ac3`, branch `codex/stage-activation-prefix`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, native 비교를 분담했다. 메인은 원본 계약·실제 diff·검증 결과를 검토했고 비교 담당 Sol이 core/CLI를 독립 검토했다.

`initialize_stage_activation_prefix`는 원본47c04에서47c6c 명령 실행 직전까지의 상태를 반환한다. 원본이 여기서RTS한다고 주장하지 않는다. 실제반환된RAM/15regs/ports를 후속콜백에 연결할 수 있으며 callback47c6c 게시도 원본순서로 수행한다. 전체stage활성화와직접플레이는별도미완료다.

원본9060/4e254 초기화, bit4/bit2 게시, 조건부477a2 호출, ca76/ca56와signedBYTE c3c0, 부모BYTE/WORD/LONG 쓰기를 실제순서로 연결한다. 각flag와parent필드는candidateRAM에서다시읽어helper/parent alias효과를보존한다. A5를고정하지않고uint32 base+signed displacement를int64로계산한뒤실제RAMspan을검사한다. WORD/LONG에만짝수정렬을적용한다. 최종LONG쓰기실패나블록리소스실패도candidateRAM/15regs/ports를폐기하여입력을보존한다.

기존execute_stage_block_draw와MS5D C++loader를재사용한다. 새리소스형식이나중복표는추가하지않았다. 조건부블록출력이없는경로는리소스없이동작하며미사용core window를검사하지않는다. CLI에서명시한파일은모두loader로검증한다. CLI는15개숫자,세경로,선택적MS5D를받고정확히15개키의JSON을출력한다. 입력/리소스/출력별칭과FIFO,신규placeholder정리를검증했다. 실제write/close실패의파일원자성은보장하지않는다.

리뷰중단위fixture가RAM밖에flag를설정하려는문제를발견했다. 작업자가flag는범위안이고후속helper만범위밖인A5=10a600으로바꾸고fixture주소검사assert를추가했다. 제품코드의checked주소검사는정상이다. 수정후격리단위/UBSan검증이통과했다. ASan은작업자실행이멈춰성공증거로기록하지않았다.

`.venv/bin/python tools/verify_stage_activation_prefix.py`는고정원본104조건,추가원본A5=108001/108002 두조건,리소스없는분기5회로총111회실제CLI비교를수행했다. 전체64KiBRAM/15regs/6,576orderedports가일치했다. 149개오류조건과latehelper/WORD실패의출력보존,FIFO4종,casealias를검증했다. 원본STOP/A7와branch/write replay,helperclear후parent재독출근거도감사한다. 메인은보고서의현재입력15개,native입력7개,산출물425개해시를재확인했다.

- Verification SHA256: `8d201ba3822457b69673b5ebab5ea663fadeb81889c5aa59d1ff5730617e56ae`
- CLI SHA256: `75cc4b6cb7bbcfc9b35f88fb5a46cddfec927f7feca62a59730f37d55a599e4d`
- 전체 `make -j4 all test`: Python189/C++137/경고0, exit0.
- Build/test log: `artifacts/stage_activation_prefix_build_test.log`.

이구간구현을수용한다. 원본에없는callback반환,CCR/cycle/stack/물리mirror/화면동등성을주장하지않는다. 다음8cda전체상태native관찰480조건도준비했다. 메인은observer를읽고기존dirty bit가base-ID equality와항상같이변하는fixture상관을제거해다시실행했다. 깨끗한flag·같은base·weight변화20조건에서도flag쓰기없음을확인했다. 최종관찰SHA `aaddf6efc6fd19e61d5d2af783db3f3a5cc159a6a7cb339ac886e15dbe298222`; 이는C++비교완료가아니다. `stage-hud-counter-contract.md`에후속4e286의sound대기와비BCD lookup범위를기록했다.
