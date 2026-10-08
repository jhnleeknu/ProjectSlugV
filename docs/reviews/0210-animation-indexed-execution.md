# Animation10 C++ 선택 그리기와 continuation 리뷰

Baseline `9169360`, branch `codex/animation-indexed-execution`. Sol6.1/medium 세 작업자가 core/unit, 두CLI/문서, 원본비교를 분담했다. 메인은 원본 의미·코드 diff·검증기·전체빌드와 최종 해시를 리뷰하고, 구현 작업자가 독립적으로 검증기와 보고서를 교차검토했다.

## 최종 동작

`AnimationExecutionState.saved_list_end`와phase3에 indexed draw의별도PEA복귀주소를보존한다. selector/tableWORD→length→signedend→livefield→WORDshift→unsignedcompare→조건부04호출의순서를유지했다. 7바이트선언길이의8BYTE실제읽기와negative signed선택/복귀를허용하고,실제도달한span만검사한다. selectedopcode!=04는원본TRAP15에대응하는checked실패다.

대기는기존spritecallee를재개하고draw_return뒤A1을listend로복원한다. callback_return을사용하지않으며D6나LONG(A0)를추가로쓰지않는다. phase3에서listend0자체는허용하고후속fetch에도달하면검사한다. 세API모두지원하며wholeinvocation오류는RAM/state/carry/PVC/external_reads를보존한다.

두CLI에SPRITE_WAITING뒤SAVED_LIST_END를추가했다. 일반21숫자/22JSON, sound26숫자/27JSON이며phase3carry는null이다. 기존숫자인자호환은명시적마이그레이션이필요하다. 파일보호코드의기존순서는유지한다. 기존MS5A/MS5D형식·packer는바꾸지않았다.

## 원본 근거와 검증

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`는불변이다. 분석문서의고정CPU주소는ROM파일offset과같다.

- 새verifier가원본846조건/854단계를다시실행하고실제CLI의전체64KiB RAM/15regs/metadata/carry/PVC3564개를비교했다. 이전실제C++출력으로8회재개하고hold에는리소스를생략했다.
- 기존fixedscript65f56..662c2의30조건/PVC300개가실제MS5A/MS5D소비에서일치했다. 도달list는65f64/6605a두곳이며known8전체라고주장하지않는다.
- 실제rawtable selector92/a7/ac와index0/4의negative signed선택6조건/PVC48개를별도원본실행으로확인했다. fullsoundCLI도네대기연쇄12단계/8실제출력재개/PVC32개가일치하며callback metadata와external_reads0을확인했다.
- 새오류60조건은partial/split/overlaptable,선택opcode,정렬/도달RAM,latecallee/복원/nextfetch,metadata,loader/FIFO/alias/출력파일보존을확인했다. APIunit은추가로모든상태필드·입력carry양쪽·외부읽기횟수rollback·미사용A6·listend0hold를검증한다.
- 검토중negative fieldfixture의selector91은실제WORD4a2d로양수임을발견하여96/8004로교정했다. selectorac의큰negative displacement가낮은scriptbase에서RAM밖을가리켜추가6fixture의header를10e000으로옮겼다. 합성입력구성오류였고원본자료·런타임을왜곡하여통과시키지않았다. 독립리뷰가교정후실제도달주소와오류문구를확인했다.
- report SHA `3f45b555bf6e5c391f1adfd97adf27e2b747e2307718883d42046086629a4e15`,입력34/산출물7174항목. 메인과독립Sol이고유7206현재참조hash일치를확인했다.
- 기존execution90/98+15추가164오류,control178+2혼합48오류,sound22/30 73오류도통과했다. 세현재reportSHA는STATUS와각실행문서에기록한다. 메인은각보고서모든참조해시도확인했다.
- `make all test` exit0,Python225/C++145/경고0. 확장unit normal 및`-fsanitize=undefined -fno-sanitize-recover=all` 격리실행통과.

재현은 `make all test` 후 `.venv/bin/python tools/verify_animation_indexed_execution.py`, `verify_animation_execution.py`, `verify_animation_control_execution.py`, `verify_animation_sound_execution.py` 순서다. 원본보고서재생성명령과전체CLI사용법은animation-indexed-execution.md에있다. 검증산출물과ROM은Git에포함하지않는다.

남은actionable결함은발견하지못했다. 모든selector/length결합·전체CCR/실제A7mirror/cycle·자연scheduler/IRQ·직접플레이는증명하지않는다. 전체17opcode중6종및14의일부경로가연결된상태이며나머지명령·callback·상위활성화와전체Goal은미완료다.
