# Animation opcode30 직접 sound와 continuation 계약

Baseline `51bdf61`. canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래fixed CPU주소는ROM파일offset과같다. 메인이4a2da..2f0과3af8..3c06을원본명령으로검토했다. 구현·원본대조완료는후속실행문서에기록한다.

30은4a2da에서A1+1을계산하여padding을읽지않고,4a2de에서D0전체0,4a2e0에서WORD(A1)+→D0.low를수행한다.4a2e2 MOVEM.L A0/A1,-(A7),4a2e6 JSR3af8. callee는기존full SoundWordExecutionState로재사용한다. 정상복귀4a2ec는A0/A1 LONG만복원하며D0/D7 WORD부호확장이나bank/PVC복원은없다.4a2f0→4a276에서D6=A1,LONG(A0)=D6를쓴후49ffe dispatch한다.

새로운외부입력overload나opcode별CLI를만들지않는다. 현재external-input overload와soundCLI에30을추가하고기존두overload/일반CLI는30/phase4를checked거부한다. 직접soundcallee는기존fixedRAM모델을재사용하므로새30의실제call/resume에서A5=108000을요구한다. 이는callee의3b98이후A5-relativequeue와관련한현재지원제한이며모든원본earlyfilter에A5검사가있다는주장이아니다. 대기중A6/script/원래command를미리다시검사하지않는다.

## Stack과 복귀의 정적 도출

S는whole49fc6진입A7다.30의MOVEM.L은S-8에A0,S-4에A1을저장하고JSR는S-12에return4a2ec를둔다. highBYTEwait에는추가savedlow용2BYTE(S-14)와return3c00(S-18)이있어A7=S-18이다. lowBYTEwait는BRA3ac8tailcall이라A7=S-12/top4a2ec이다. high→low변환은원래capturedlow를쓰며scriptWORD재읽기를하지않는다. 이 스택과 captured low 재사용은 후속 native207조건/255단계 관측에서 확인했다. 상세 범위와 해시는 animation-direct-sound-execution.md를 따른다.

## State/API/CLI 결정

- phase4=30 직접sound pending. sprite.waiting=false, callback_waiting=true, callback_sound_phase=1또는2, callback_saved_low는soundword의캡처값이다. 기존callback_*이름의세필드는phase2/4에서공유하는soundmetadata로사용한다.
- phase4에서saved_a0/saved_a1은30의MOVEM.L외부값,saved_bank=0,saved_list_end=0,callback_saved_a0=0이다. 새persistentfield는없다. phase0/1/2/3의기존규칙은유지한다.
- phase4재개는SoundWordExecutionState를현재canonical13R/phase/savedlow/waiting으로구성해callee만실행한다. hold는RAM/state/carry를그대로유지하며external_reads=0/PVC없음이다. high→low에서계속대기할수있다.
- 완료하면A0/A1을복원하고모든directsound metadata를0으로clear한뒤D6/상태pointer를쓰고다음명령을실행한다. draw_return/callback_return을사용하면가짜bank/PVC와D0/D7부호확장이생기므로전용복귀를쓴다.
- 기존uint32 external_reads에callee의uint8읽기를더한다. 여러30/기존1f가한invocation에서실행되면합산한다. 늦은실패는RAM/state/carry/ports/읽기횟수모두rollback한다.
- 일반CLI의21숫자/22JSON은유지하며phase0/1/3만허용한다. soundCLI의26숫자/27JSON도유지하되phase0..4,callback_waiting=(phase2또는4),sprite.waiting=(phase1또는3),carry는phase!=0에서null이다. 기존callbackmetadata의이름변경은하지않고phase별의미를문서화한다.

이미지원한opcode는계속회귀검증한다.30은고정lookup리소스를추가로요구하지않는다. commandWORD는MS5A 또는 liveRAM이며실제사운드재생/자연IRQ소비·모든script와group연결·3c/40및다른14callback·전체Goal은미완료다.
