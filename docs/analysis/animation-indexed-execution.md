# Opcode10 indexed draw의 전체 상태 연결

## 현재 bank-state CLI schema

[실제 bank 상태 계약](animation-bank-state-contract.md)에 따라 공통 `SAVED_LIST_END` 바로 뒤 argv22에 unsigned32 `CURRENT_BANK_BASE`를 전달한다. 일반 CLI는22숫자/23JSON, RAM/output/ports argv23/24/25 및 resource26+이며, sound CLI는27숫자/28JSON, callback4개 argv23..26, EXTERNAL argv27, RAM/output/ports argv28/29/30 및 resource31+다. 두 출력 JSON은 숫자 `current_bank_base`를 항상 포함한다. 임의 uint32 bank 입력을 허용하며 saved_bank와 구분한다. 이전 schema 자동 추정이나 기본값 보충은 없다. 아래 원본 관측·검증 수치와 해시는 해당 단위 당시의 완료 기록이며, 이 schema 이행의 재검증 결과를 대신하지 않는다.


[확정 계약](animation-indexed-full-contract.md),[resource 범위](animation-indexed-resource-spans.md),[중첩 draw frame](animation-indexed-continuation.md)을따른다. 기준분석commit은9169360이다. canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며fixed CPU주소는ROM파일offset과같다. 이번단위는기존전체상태API의opcode10과phase3을연결한다. 기존00/04/08/28/0c/14의지원과sound전용overload의1f범위를유지하며전체17opcode완료를뜻하지않는다.

## 상태와 현재 CLI

기존세 `step_animation_execution` overload의state에uint32 `saved_list_end`를추가한다. 기존sprite.registers의13레지스터와a5/a6가유일한canonical저장소다. phase0=fresh/완료,phase1=직접04 sprite대기,phase2=14/1f sound대기,phase3=indexed sprite대기다. phase3은sprite.waiting=true,callback metadata비활성이며saved_a0/saved_a1/saved_bank는내부draw frame,saved_list_end는별도outer list복귀주소다. phase0/1/2는saved_list_end=0이다. phase3에서list end0을metadata불일치로거절하지않고실제후속fetch에도달하면주소를검사한다.

```text
build/step_animation_execution \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  PHASE SAVED_A0 SAVED_A1 SAVED_BANK SPRITE_WAITING SAVED_LIST_END CURRENT_BANK_BASE \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [RESOURCE_MS5A_OR_MS5D ...]

build/step_animation_sound_execution \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  PHASE SAVED_A0 SAVED_A1 SAVED_BANK SPRITE_WAITING SAVED_LIST_END CURRENT_BANK_BASE \
  CALLBACK_SAVED_A0 CALLBACK_SOUND_PHASE CALLBACK_SAVED_LOW CALLBACK_WAITING EXTERNAL \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [RESOURCE_MS5A_OR_MS5D ...]
```

일반CLI는22숫자/최소argc26,RAM/output/ports argv23/24/25,resource26+다. phase0/1/3을받고2를거절한다. soundCLI는27숫자/최소argc31,RAM/output/ports argv28/29/30,resource31+이며phase0..4를받는다. 공통SAVED_LIST_END는argv21, CURRENT_BANK_BASE는argv22이고 sound callback4개/EXTERNAL은argv23..27이다. 새필드는uint32 strict10진수/0x16진수이며기존숫자의폭과range검사는유지한다.

stdout은일반23key,sound28key다. 숫자saved_list_end와current_bank_base를항상포함한다. waiting은sprite.waiting만표시하며phase1/3에서true,callback_waiting은phase2/4에서true다. carry는phase!=0에서null,완료에서boolean이며carry입력숫자는없다. orderedports9바이트 `>BII`와65536바이트RAM출력은유지한다. 이전20/25숫자명령에는 SPRITE_WAITING 뒤 SAVED_LIST_END를 삽입하고, 그 뒤 CURRENT_BANK_BASE도 명시해야 한다. 이전 직접04/sound pending은 saved_list_end=0이며 실제 장치 bank를 별도로 전달한다. positional schema 자동 추정이나 RAM shadow에서의 bank 추정은 하지 않는다.

## 원본 선택·복귀 순서

MOVEQ0뒤selectorBYTE×2로fixed4a76c의WORD를읽는다. lengthWORD는D1.low에읽고high16를보존한다. list base+signed16(length)를복귀주소로저장한뒤A6+signed16(tableWORD)의liveBYTE를읽는다. length0도field읽기를생략하지않는다. MOVE.B가남긴tableWORD의highBYTE를유지하고LSL.W3의16bit wrap을적용한다. unsigned offset>=length이면draw를생략한다.

선택되면list base+signed16(offset)의BYTE가04인지확인하고기존draw body로진입한다. 원본TRAP15경로를성공no-op로바꾸지않는다. index+8<=length나length8배수제한을추가하지않으며실제script opcode/operand span을검사한다. signedlength/offset은앞쪽주소를가리킬수있고계산범위밖은checked오류다. list end의메모리는계산때미리읽지않는다.

sentinel/음수timer/flash skip,완료draw와대기해제후모두원래list end를A1으로복원하여직접49ffe dispatch로간다. 4a276을경유하지않으므로pointer write나D6=A1을추가하지않는다. phase3은captured sprite만재개하고object/selector/table/list header와draw prefix를반복하지않는다. hold에는resource0개와검사되지않은현재A6도허용하지만reached sprite callee는기존canonical A5제한을유지한다. 완료후기존draw_return과별도list end복원을수행하고현재RAM의다음명령을읽는다.

오류는호출전RAM·15레지스터·모든metadata·carry·ports 및sound호출형의external_reads를보존한다. 성공pending은현재효과를commit하고carry입력bool을보존한다. pending해제뒤list end의fetch에서늦게실패해도동일transaction을따른다.

## Resource와 파일 보호

fullBYTEselector의raw창 `[4a76c,4a96c)`512바이트는기존control_04276c.ms5d `[4276c,5276c)`안에있다. 기존animation_065f56.ms5a는known8lists와0c/14/10script876바이트를보존한다. 앞선1d/1e callback의known8operandbasefullBYTE raw합집합은operands_06431a.ms5d `[6431a,64836)`에있으며10자체는이창을읽지않는다. MS5A/MS5D형식을바꾸거나새packer를추가하지않는다. 구체적인C++소비결과는최종보고서에서구분한다.

두CLI의실제magic loader선택,모든입력의regularfile검사/FIFO거절,canonical/inode resource중복제거와RAM/output비중복검사,두출력O_NONBLOCK예약/fstat후truncate순서는유지한다. suppliedresource는미사용경로에도검증한다. 기존파일을검사실패에서보존하고새placeholder는예약identity와일치할때만정리한다. 실제쓰기시작후두출력의원자교체/rollback은보장하지않는다.

## 재현과 검증 상태

다음은현재도구의재현명령이다. 공유build와최종verifier실행은메인이조정했다. 문서작성작업에서는보고서와현재입력·산출물해시를읽어확인했으며build/관측을중복실행하지않았다.

```sh
.venv/bin/python tools/pack_animation_control.py
.venv/bin/python tools/pack_animation_branch.py
.venv/bin/python tools/pack_activation_animation.py
make build/step_animation_execution build/step_animation_sound_execution build/animation_execution_test
./build/animation_execution_test
.venv/bin/python tools/observe_animation_indexed_execution.py
.venv/bin/python tools/observe_animation_indexed_fixed_scripts.py
.venv/bin/python tools/verify_animation_indexed_execution.py
.venv/bin/python tools/observe_activation_animation_scripts.py
.venv/bin/python tools/verify_animation_execution.py
.venv/bin/python tools/observe_animation_control_commands.py
.venv/bin/python tools/verify_animation_control_execution.py
.venv/bin/python tools/observe_animation_sound_callback.py
.venv/bin/python tools/verify_animation_sound_execution.py
make all test
```

원본근거는synthetic list846조건/854단계의 `db3247ceba5327719b84882b7d1abe006f0e30c87d28642ed7c2f9a9f75a6508`과fixed script30조건의 `7f50c9d4ddf4023e47dd22abc6849cbd6322bd4916f2e620a04a2ca78b61fd37`다. 최종검증기는이원본단계를모두재실행하고실제C++와비교했다. fixed matrix의실제indexed도달점은65f64/6605a두곳이며known8개전체실행으로일반화하지않는다.

최종 `artifacts/animation_indexed_execution/verification.json` SHA256은 `3f45b555bf6e5c391f1adfd97adf27e2b747e2307718883d42046086629a4e15`다. primary846case/854phase의전체65536바이트RAM·15레지스터·metadata·완료carry·orderedPVC3564건이일치했다. 일반CLI의8회재개는이전실제C++출력과명시된hostRAM변경만이어받았고phase3 hold는resource없이통과했다. knownfixedscript30건은기존MS5A/MS5D를실제loader로소비하고PVC300건까지원본과일치했다.

별도signed선택주소6건은selector92/a7/ac와field0/4에서unsigned비교통과후음수signedoffset으로목록앞의실제04를선택하는경로이며PVC48건이일치했다. 이는negative실패수가아니다. fixture는header를10e000에놓아선택주소와lengthfff8의복귀주소를지원RAM안에유지했다. 초기ac fixture의RAM밖선택주소와negative용selector91의실제양수offset을교정하여,후자는실제음수offset인96으로바꿨다. 이두교정은테스트fixture수정이며runtime버그발견으로기록하지않는다.

soundCLI도동일4대기연쇄의12phase와이전실제C++출력재개8회를비교하여PVC32건까지일치했다. 이indexed경로에서callbackmetadata와external_reads는0이며,phase3을sound phase2로표현하지않았다. primary/fixed/signed/sound수는서로다른집단으로구분하고합쳐새case수로표시하지않는다.

새negative60건은saved_list_end파싱·비활성/pending조합·누락/부분/분할/중복/overlap selector창·미지원선택opcode·정렬/실제RAMspan·늦은producer callback/복귀후다음fetch·공급한corruptresource·입출력alias/FIFO/casealias·예약cleanup등을검사했다. 오류를native성공으로세지않는다. 문서갱신시보고서의입력34개와artifact7174개entry를현재파일과전부대조했으며중복path를합치면7206개다.

현행schema의기존회귀보고서도통과했다. execution은90case/98phase·별도liveRAM15건·negative164건이며SHA256 `77a5ecbd0092e4dcb33d27976b1668d190ef76b15967f428773f978dfb1f9fc0`,control은178primary+2mixed·negative48건이며 `4d03a72e673cc3ca6967d40d4c96527745bac0769915db78a05048c53c1907f5`,sound는22case/30phase·negative73건이며 `645a5de6b056cd8571488f78968a9fbb4cd429a11f5dbd5628bfa1835937cdfe`다. 기존execution/control/sound문서에서는추가전의역사해시와이현행schema회귀해시를별도절로구분한다.

메인통합 `make all test`는exit0,Python225개/C++test실행145개/컴파일경고0건이다. core작업자의격리normal/UBSan unit검증도통과했다. 재현명령에는지원되지않는추가flag를붙이지않는다. 모든관측fixture는제어된RAM상태이며자연게임실행의증거로확대하지않는다.

나머지opcode/임의callback,bankedscript/data,전체CCR/A7stack/cycles,physicalmirror/IRQ/scheduler,composition/palette binding,자연게임도달성과직접플레이는별도미완료이며전체GOAL에서제외하지않는다.
