# Animation 0c/14 C++ 연결 리뷰

Baseline `f074b49`, branch `codex/animation-control-execution`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, 원본 비교 도구를 맡았다. 메인은 확정 원본 계약과 실제 diff, 검증기, 혼합 리소스 경로 및 최종 해시를 검토했다. 이전 턴은 원본 관측·패커·계약을 커밋한 실제 진전이며 이번 단위가 그 C++ 연결이다.

기존 API를 유지하는 MS5D windows overload를 추가했다.0c의 signed WORD 두 배/조회와 D0/D1 부분 갱신,14의1d/1e 실제 target 검사와 live index/source LONG, bank/PVC/MOVEM.W/A0A1 복원을 연결했다. CLI는 실제 magic으로 MS5A/MS5D loader를 선택하고 모든 입력의 alias/FIFO 보호를 유지한다.1f와 다른 callback은 여전히 명시적 미지원이다.14 전체를 완료한 것으로 세지 않는다.

## 검증

- 원본178조건과 실제CLI의 전체64KiB RAM/15regs/carry/비활성 continuation/PVC912회가 일치했다.0c128개,14의1d/1e50개, carrytrue80/false98이다.
- 추가2조건은 합성 RAM0c/14 prefix에서 MS5D를 실제 조회한 뒤 원본48980 MS5A를 실행했다. 모든 상태와 orderedPVC36/40회가 일치하여 두 resource 종류의 동일 호출 내 소비를 확인했다.
- 오류48조건은 missing/partial/ambiguous windows, loader 손상, callback/source 오류, 실제callback완료 후 다음script fetch실패, FIFO/alias 및 신규출력예약 정리를 검증했다. 마지막 destination/pointer 쓰기는 앞선 주소검사를 통과했다면 이1d/1e 경로에서 독립적인 span 실패를 만들 수 없으므로, 더 이른 실패를 late write로 잘못 기록하지 않았다.
- API 합성 단위 검사는 positive/negative offset, source/index overlap, RAM pointer write→다음fetch, noncanonicalA5, callback destination=bank shadow alias, false/true carry rollback과 old overload를 포함한다. normal/UBSan 빌드·실행 모두 통과했다.
- 전체 `make all test` exit0, Python225/C++145/경고0. 기존4opcode 회귀90조건/98단계·이전실제C++출력기반8재개·추가15·오류157도 통과했다.
- Control report SHA256 `01bf8c488c626b1f80346ba97dbdc9175357a0b269747281b2760e9ee8ea11d8`, 입력31/산출물1447 참조해시 일치. 기존 회귀의 새 SHA는 `ee6d4284ca590eada918161a6944b2b110c875ddd86854dede1fa087e51d0ade`이며 입력23/산출물670개가 현재파일과 일치한다. 메인이 두 보고서의 총1478/693개 참조를 직접 확인했다.
- CLI SHA256 `c3ed67b1922f1d7292d88b819525c69cc580615c9d0c60626d354c13107e5f66`. 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f` 불변을 확인했다. 고정CPU주소=ROM파일오프셋이다.

## 다음1f의 원본 증거

메인이 `tools/observe_animation_sound_callback.py`를 작성해 수정 없는49fc6→14/1f→47672를19조건/27단계로 관측했다. 같은CPU 세대기연쇄, 재개8·대기8·완료19(carryfalse),PVC152회다. source/gate/bank/scriptoperand를 host에서 바꿔도 현재callback prefix는 재실행하지 않으며 완료부는 live source를 다시 읽는다. high/low의 실제nestedSP=STACK-28/-22, innerA0와outerA0/A1/bank를 직접 캡처했고 MOVEM.W 복원도 확인했다.

SHA256 `87a075a297e63924b0da880eaa22ea3c1b90e635a949880f8b0426c0320801a3`. 별도Sol의10단계 재실행과 다른Sol의 원본stack명령 리뷰, 메인의현재114개입력/산출물hash검사를 통과했다. 이것은 canonicalA5/A6와 합성RAMscript의 원본 증거이며1f C++지원·source/queuealias 전체조합·자연실행을 증명하지 않는다. 후속 phase2 구현의 기준으로 사용한다.

현재 변경에 남은 수정할 문제는 발견하지 못했다. 재현 명령과 현재 지원 범위는 `docs/analysis/animation-control-execution.md`에 있다. 나머지11opcode,14의다른callback,1f중첩sound,C++indexed draw,상위callback,자연scheduler/IRQ,직접플레이와전체게임Goal은 미완료다.
