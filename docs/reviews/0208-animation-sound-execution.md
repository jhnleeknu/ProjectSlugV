# Animation 14/1f 중첩 sound 연결 리뷰

Baseline `6f0ec55`, branch `codex/animation-sound-execution`. 이전 턴은0c/14의 구현과 원본 비교를 커밋한 진전이었다. Sol6.1/medium 세 작업자가 core/unit, 새CLI/Make/문서, 원본 비교를 분담했다. 메인은 원본 alias 증거를 보강하고 상태/API 경계를 정한 뒤 실제 diff와 검증기를 검토했다.

## 구현과 근거

외부 상태 BYTE와 invocation별 uint32 읽기 횟수를 받는 overload에14/1f→47672를 연결했다. 기존 overload/CLI에는 외부 입력과 중첩 상태 전달이 없으므로 이전 지원 범위를 유지하고1f/phase2를 명시적으로 거부한다. 새CLI가25숫자와26JSON key로 전체상태를 전달한다.

phase2는 outer interpreter A0/A1/bank와 inner source A0/sound phase/saved low/waiting을 분리한다.13R는 여전히 sprite.registers 한 곳에 있고 local ObjectSoundLookupState로 callee에 전달한다. 대기 중에는14/table/operand/callee prefix를 다시 실행하지 않는다. callee 완료 후 live source/lookup, outer bank/PVC/MOVEM.W 복원, pointer 저장 및 다음명령을 실행한다. 해당호출의 늦은실패는 RAM/state/carry/ports/external_reads 전부를 보존한다.

메인은 원본 observer에3alias 조건을 추가했다. A6=ffffe에서476b6의BYTE100010=05 뒤4a43e의WORD100010=0000 복원이 실제 발생한다. signed queue write3bcc가 source10095c에1ac0을 쓴 뒤47690/47694는 현재BYTE1a/WORD1ac0을 읽는다. low_hold에는 전체상태와pending stack 동일성 검사를 보강했다.

원본 고정CPU주소=ROM파일오프셋이며 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`는 불변이다. alias 보강 후22조건/30단계 native SHA는 `5f8b3d3a71532bd3c99d930ad4e61d9c490cc90036669cd872f9169294043108`이며 이전87a075... 보고서를 대체한다. 독립Sol이 세sameCPU연쇄와alias세조건 총14단계를메모리에서재실행하고 입력6/산출물120개hash를확인했다.

## 검증

- 실제 새CLI22조건/30단계의 전체64KiB RAM/15regs/중첩metadata/carry/PVC176회/외부읽기3회가 원본과 일치했다.8회 재개는 직전 실제 C++ 출력과 명시된 host 변경만 사용했다.5개hold/high→low 호출은 MS5D를 생략했다. 완료22개의carry는false, 대기8개는null이다.
- 오류72조건은 invalid metadata, actual sound의canonicalA5 제약, late inner lookup/source/object, outer 복원 후 next fetch 실패, loader·FIFO·alias·출력예약보존을 검증했다. 합성단위는 입력carry양쪽, 외부읽기횟수rollback/여러callback합산, 대기중미사용A6, 사용하지않는operand, bankalias를 포함한다.
- normal/UBSan 단위빌드·실행통과. 전체 `make all test` exit0, Python225/C++145/경고0이다. 기존4opcode90/98단계·15추가·157오류와 control178·혼합2·48오류도 통과했다.
- 새검증SHA `baf581cbb12606b3af6ec8bc344793d3ffaf61ec7b53231305396601700d3ae0`, 입력28/산출물247개항목, 중복제외274경로해시일치. 새CLI SHA `b3adeb071ae3080c527d5c5886596c88d8f67ae7761ac8ed594ed8580a14576b`.
- 기존회귀SHA `be59ad90077a495574387fff762a851fb9b7919e44b46c38edab710f604b8694`(현재699참조), control SHA `9150fea35c22643b418821fe01c75ae629463b78c9433bcebb85b0f75fd36714`(현재1484참조). 메인이 세보고서의모든현재해시를대조했다.

검토에서 수정할 코드문제는 발견하지 못했다. 재현과 제한은 `animation-sound-execution.md`에 기록한다. 원본코드를패치하지않은합성RAMscript 증거이며 자연게임도달성·전체callback·전체alias조합·물리IRQ/cycle을 주장하지 않는다. 다음10 indexed draw, 나머지opcode, 상위활성화callback, 자연scheduler/IRQ, 직접플레이 및 전체Goal은 미완료다.
