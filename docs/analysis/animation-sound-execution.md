# Animation14/1f sound callback의 전체 상태 CLI

[중첩 continuation 근거](animation-callback-continuation.md)와 기존 [control 실행 범위](animation-control-execution.md)를 따른다. canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 여기의 fixed CPU 주소는 ROM 파일 오프셋과 같다. 추가 범위는 opcode14의 selector1f 및 실제 dispatch target47672이며, 임의callback이나전체17opcode 지원을 뜻하지 않는다.

```cpp
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows,
    AnimationExecutionState& state, std::uint8_t external_status,
    std::uint32_t& external_reads, bool& carry,
    std::vector<VideoPortWrite>& ports, std::string& error);
```

15레지스터의저장은기존 `sprite.registers`의13개와a5/a6가유일한기준이다. 별도callee register배열을영속상태로추가하지않는다. phase0은fresh/완료,phase1은직접04 sprite대기,phase2는14/1f sound대기다. 기존outer saved_a0/saved_a1/saved_bank는interpreter A0·다음script A1·bank를보존한다. 추가callback_saved_a0는inner47672 source A0이며outer A0와다르다. callback_sound_phase는1=high/2=low,callback_saved_low는BYTE,callback_waiting은sound대기를나타낸다. phase2에서sprite.waiting은false다. 비활성metadata와phase별조합은core가검사한다.

## 새 CLI와 호환성

```text
build/step_animation_sound_execution \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  PHASE SAVED_A0 SAVED_A1 SAVED_BANK SPRITE_WAITING \
  CALLBACK_SAVED_A0 CALLBACK_SOUND_PHASE CALLBACK_SAVED_LOW CALLBACK_WAITING EXTERNAL \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [RESOURCE_MS5A_OR_MS5D ...]
```

숫자25개,최소argc29다. INPUT_RAM/OUTPUT_RAM/OUTPUT_PORTS는argv26/27/28,resource는argv29이후다. register와saved pointer는uint32,phase0..2,bank0..65535,sound phase0..2,low/external0..255,두waiting0..1을strict10진수/0x16진수로검사한다. carry입력숫자는없으며API초기bool은false다.

stdout은정확히26key다. 기존15레지스터와phase/saved_a0/saved_a1/saved_bank/waiting/carry에callback_saved_a0/callback_sound_phase/callback_saved_low/callback_waiting/external_reads를추가한다. waiting은sprite.waiting만표시하며callback_waiting과합치지않는다. 두waiting은boolean,carry는phase!=0이면null,완료면boolean이다. ports파일은이번호출의순서있는9바이트 `>BII` 기록이다. 오류에는JSON을출력하지않는다.

기존 `step_animation_execution` CLI의20숫자/21key schema는변경하지않는다. 기존API overload도기존범위를유지하며1f/phase2를거절한다. 새로운외부상태인자가있는호출형에서만이번범위를사용한다.

## 실행·재개와 실패 경계

14의selector BYTE→fixed dispatch LONG→operand LONG읽기순서를유지한다. operand A0를47672가곧덮더라도operand fetch를생략하지않는다. outer frame을저장하고bank shadow/PVC를쓴후실제object sound wrapper를호출한다. sound호출/재개에실제로도달한경로만기존callee 제약에따라A5=108000을요구한다. sound를건너뛴경로는실제A5-relative span을검사한다.

phase2 hold는captured inner/outer상태로sound대기만재개한다. selector/table/operand와callback prefix를다시읽지않고외부gate를다시평가하지않는다. 성공한대기는현재까지의RAM·15레지스터·metadata·ports를commit하고carry입력bool을보존한다. external_reads는이번호출의조건부외부상태읽기횟수다. hold에는resource0개도허용되지만공급한파일은항상loader검증을통과해야한다.

sound완료뒤inner saved A0를복원하고live source BYTE→object+7e쓰기→live source WORD→raw lookup→object+12쓰기를이어간다. 이후outer bank복원/PVC와MOVEM.W D0/D7의signed16→32복원,A1/A0복원,script pointer저장,다음live dispatch를실행한다. pending중A6를미리검사하지않으며완료후실제쓰기에서검사한다. 완료후lookup/outer복귀/다음fetch에서실패해도이번호출전체의RAM·state·carry·ports·external_reads를보존한다.

## Resource와 파일 보호

resource는실제4바이트magic MS5A/MS5D로기존loader를선택하며다른magic/잘린header를거절한다. 같은canonical path/inode는종류에관계없이한번만로드한다. distinct파일의부분/overlap창은실제read의unique complete규칙을따른다. MS5A는script,MS5D는fixed data,100000..10ffff는현재RAM이다. banked data는이번지원범위가아니다.

`tools/pack_animation_control.py`의control_04276c.ms5d `[4276c,5276c)`는0c/14 dispatch뿐아니라1f의raw WORD lookup `[4411e,4421e)`를포함한다. 기존작은object-sound lookup창을함께공급하여중복시키지않는다. operands_06431a.ms5d는1d/1e fixed operand가도달할때사용한다. resource없는hold가가능하다는사실을완료경로의fixed조회도불필요하다고확대하지않는다.

RAM은정확히65536바이트이며RAM과모든resource를ifstream전에stat/S_ISREG로검사하여FIFO를거절한다. 모든입력과출력의canonical/inode alias를검사한다. core성공후두출력을O_NONBLOCK으로truncate없이예약하고fstat로일반파일·서로다른inode·모든입력의저장/현재inode와의비중복을확인한뒤에만쓴다. 검사실패는기존파일을보존하고새placeholder는같은예약identity일때만제거한다. 실제case alias도inode로검출한다. write/close실패는검사하지만쓰기시작후두파일의원자교체/rollback은보장하지않는다.

## 재현과 검증 상태

```sh
.venv/bin/python tools/pack_animation_control.py
.venv/bin/python tools/pack_activation_animation.py
make build/step_animation_sound_execution build/step_animation_execution build/animation_execution_test
./build/animation_execution_test
.venv/bin/python tools/observe_animation_sound_callback.py
.venv/bin/python tools/verify_animation_sound_execution.py
.venv/bin/python tools/observe_activation_animation_scripts.py
.venv/bin/python tools/verify_animation_execution.py
.venv/bin/python tools/observe_animation_control_commands.py
.venv/bin/python tools/verify_animation_control_execution.py
make -j4 all test
```

corelink는animation_execution.cpp,sprite_submit_execution.cpp,object_sound_lookup.cpp,sound_word_execution.cpp,sound_byte_execution.cpp다. 기존animation CLI와unit도같은core 의존성합집합을사용한다. 새CLI에는animation_resource.cpp와fixed_data_resource.cpp를추가한다. Makefile all은새CLI를포함하며test는확장된기존animation_execution_test를유지한다.

최종원본관측 `artifacts/animation_sound_callback/observation.json`의SHA256은 `5f8b3d3a71532bd3c99d930ad4e61d9c490cc90036669cd872f9169294043108`이다. 기존19case/27phase에bank shadow와object destination이alias되는case19/20 및signed queue write가source와alias되는case21을추가하여22case/30phase다. 기존 `87a075...` 보고서는초기관측이며최종보고서로사용하지않는다. immutable원본49fc6와synthetic liveRAM14/1f script에서실제중첩stack과같은CPU의high/low hold·release를관측했다. callback stack이나expected register를hook에서주입하지않았다. A5는canonical이며A6는일반fixture와위bank alias조건을포함한다.

최종C++보고서 `artifacts/animation_sound_execution/verification.json`의SHA256은 `baf581cbb12606b3af6ec8bc344793d3ffaf61ec7b53231305396601700d3ae0`이다. 모든원본30phase를재실행하고22case의전체65536바이트RAM·15레지스터·outer/inner pending metadata·완료carry·순서있는PVC176건·external_reads합계3회를실제CLI와비교했다. 완료22phase의carry는false,대기8phase는JSON null이다. 재개8회는이전실제C++RAM·레지스터·metadata와명시된host RAM변경만사용한다. 원본native snapshot을다음C++입력으로대체하지않았다.

실제C++fixed loader가MS5Ddispatch/lookup창을소비했다. case16/17의hold와case18의hold/high_to_low/low_hold,총5phase는resource를공급하지않고통과했다. 이결과는대기중prefix·lookup의무재실행범위이며,ready이후fixed조회에는resource가필요하다. negative72건은숫자범위·비활성/pending metadata·조건부canonical A5·늦은inner lookup/source WORD/object destination·outer복귀후다음fetch오류·hold중공급한corrupt resource·RAM크기·alias/hardlink/symlink/FIFO·예약실패cleanup과실제case alias거절을검사한다. 오류를원본native 성공으로집계하지않았다. 문서갱신시입력28개와native/C++artifact247개entry를모두현재hash와대조했으며중복path를합치면274개다.

기존CLI/overload의회귀도통과했다. `artifacts/animation_execution/verification.json` SHA256 `be59ad90077a495574387fff762a851fb9b7919e44b46c38edab710f604b8694`는90case/98phase,이전실제C++출력재개8회,별도liveRAM15건,negative157건이다. `artifacts/animation_control_execution/verification.json` SHA256 `9150fea35c22643b418821fe01c75ae629463b78c9433bcebb85b0f75fd36714`는primary178건과별도mixed2건,negative48건이다. 이수를새1f의22case에합산하지않는다. 기존CLI에는external입력이없으므로1f/phase2를거절하는설계를유지한다.

전체 `make -j4 all test`는exit0이며 `artifacts/animation_sound_execution/make-all-test.log`에서Python225개,C++test실행145개,컴파일경고0건을확인했다. core작업자의격리normal/UBSan unit검증도통과했다. 재현도구에는추가audit-only같은인자를붙이지않는다. 관측·검증명령은ignored artifact를재생성하며ROM은수정하지않는다.

전체17opcode,다른callback,bankedscript/data,전체CCR/A7stack/cycles,물리mirror/IRQ/scheduler,composition group/palette binding,자연게임도달성과직접플레이는별도미완료범위다.
