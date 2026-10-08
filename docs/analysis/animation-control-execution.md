# Animation 조건 분기와 제한된 callback의 전체 상태 연결

## 현재 bank-state CLI schema

[실제 bank 상태 계약](animation-bank-state-contract.md)에 따라 공통 `SAVED_LIST_END` 바로 뒤 argv22에 unsigned32 `CURRENT_BANK_BASE`를 전달한다. 일반 CLI는22숫자/23JSON, RAM/output/ports argv23/24/25 및 resource26+이며, sound CLI는27숫자/28JSON, callback4개 argv23..26, EXTERNAL argv27, RAM/output/ports argv28/29/30 및 resource31+다. 두 출력 JSON은 숫자 `current_bank_base`를 항상 포함한다. 임의 uint32 bank 입력을 허용하며 saved_bank와 구분한다. 이전 schema 자동 추정이나 기본값 보충은 없다. 아래 원본 관측·검증 수치와 해시는 해당 단위 당시의 완료 기록이며, 이 schema 이행의 재검증 결과를 대신하지 않는다.


후속1f 지원은 별도 external-input overload와 [sound 실행 CLI](animation-sound-execution.md)에 추가되었다. 이 문서의 기존 overload/CLI는 이전 지원 범위를 유지한다. 아래 검증 해시는 당시 연결의 기록이다.

[전체 상태 확장 계약](animation-control-full-contract.md)과 [raw resource 범위](animation-control-resource-spans.md)를 따른다. canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 fixed CPU 주소는 ROM 파일 오프셋과 같다. 기존 전체 상태의00/04/08/28에0c와14(확인된1d/1e callback만)를 추가하는 단위이며, 전체17opcode와 임의callback 완료를 뜻하지 않는다. 기존 RAM/carry API나 기존 호출형을 제거하지 않는다.

```cpp
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows,
    AnimationExecutionState& state, bool& carry,
    std::vector<VideoPortWrite>& ports, std::string& error);
```

기존 overload는 빈 windows를 전달해 위 API를 호출한다. `AnimationExecutionState`의 sprite13register/A5/A6, phase, saved A0/A1/bank와 waiting은 변경하지 않는다. phase1은 기존 직접04의sprite 대기이며14의 임의callback 대기를 뜻하지 않는다. 정확히65536바이트 RAM, 실제 reached 정렬/span과 unique complete fixed read를 검사한다. 오류는 전체RAM·15레지스터·metadata·carry·기존ports를 보존하고 성공ports는 이번 호출분으로 교체한다. pending은 carry입력bool을 보존하며 CLI가null로 표시한다.

## CLI 호환성과 resource 식별

```text
build/step_animation_execution \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  PHASE SAVED_A0 SAVED_A1 SAVED_BANK SPRITE_WAITING SAVED_LIST_END CURRENT_BANK_BASE \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [RESOURCE_MS5A_OR_MS5D ...]
```

현재 숫자22개, 최소argc26, INPUT_RAM/OUTPUT_RAM/OUTPUT_PORTS는argv23/24/25, resource는argv26이후다. 레지스터와saved pointer는unsigned32bit, phase0/1/3(2거절),bank0..65535,waiting0..1,saved_list_end/current_bank_base uint32의 strict10진수/0x16진수 파서를 유지한다. 출력은 정확히23key다:15레지스터와 `phase`, `saved_a0`, `saved_a1`, `saved_bank`, `saved_list_end`, `current_bank_base`, `waiting` boolean, `carry`(pending null/완료boolean). ENTRY나carry입력은 없다. 출력포트의 ordered9바이트 `>BII` 형식도 동일하다.

각 resource의 **실제 첫4바이트**가MS5A이면 기존 `load_animation_resource`, MS5D이면 `load_fixed_data_resource`를 사용한다. 확장자나 인자 위치로종류를 추정하지 않는다.4바이트를 읽을 수 없거나 다른magic이면 실패한다. fixed kind1/version/CRC/length/reserved 검증은 각 기존loader를 따른다. 공급한 파일은 미사용경로에서도 검증하며, resource0개는 실제fixedfetch가 도달하지 않는 null/liveRAM/pending경로에서 허용한다. 이후fixed조회가 도달하면 필요한 창을 제공해야 한다.

same canonical path/inode resource alias는 종류에 관계없이 한 번만 로드한다. 서로 다른 파일로 공급된 overlap은 actualread에서unique/complete 정책을 따른다. MS5A는 명령fetch, MS5D는조회data이며 RAM주소는 항상 현재RAM에서읽는다. 같은raw주소를 가진 script와data의provenance를 임의로 섞지 않는다.

phase3의indexed sprite대기와saved_list_end는 [indexed 실행 문서](animation-indexed-execution.md)를따른다. phase0/1/2에서는saved_list_end=0이다. 현재일반CLI는외부sound상태를받지않으므로phase2를거절한다.

## 0c: WORD selector와 live branch

4a3b8은 desiredBYTE를D1.byte에읽고SNE.B로00/ff로만든다. D1상위24bit는보존한다. selectorWORD를D0.low에읽어ADD.W로두배하고 `4a76c+sign16((selector*2)&ffff)`의WORD를D0.low에읽는다. D0상위WORD를보존하며unsignedindex로바꾸지않는다. 전체WORDdomain은32768개의distinct signed-evenWORD주소를만들며selector와selector+8000은같은주소다.

branch targetLONG을D7에먼저읽은뒤A6+signed16(D0.low)의liveBYTE를검사한다. 조건불일치여도targetoperand읽기는생략하지않는다. SNE.B는D0.byte만00/ff로바꾸므로offset의bits8..15와상위WORD가남는다. 같으면A1=D7,다르면현재A1을유지한다. D6=A1전체를LONG(A0)에쓴뒤다음dispatch한다. 이쓰기와다음RAMscript가alias되면새live값을읽는다. 중간CMPcarry를최종반환carry로오인하지않는다.

## 14: 원본 callback frame과1d/1e

D0전체0후selectorBYTE×4로4a500의callbackLONG을D7에읽고operandLONG을A0에읽는다. 원래A0,operand뒤A1과livebankWORD를저장하고shadow0/PVC두WORD후실제지원callback효과를실행한다. 조회한target이있다는이유만으로임의함수를지원하거나no-op으로대체하지않는다.

1d→2b3e8,1e→2b3fa만지원한다. 각각object+7c/+7dBYTE를D0전체0뒤읽고WORD×4로operand주소의LONG을먼저읽은후object+78에쓴다. source가liveRAM이면현재값을읽고alias순서를유지한다. fixedsource면공급MS5D의유일한완전한LONG이필요하다. 이둘에는내부sound/wait가없으므로새pending종류를만들지않는다. canonicalA5를무조건요구하지않으며실제reachedA5-relativeRAMspan을검사한다.

복귀는liveA5-relativebankshadow복원,PVC재설정,MOVEM.W D0/D7의signed16→32복원,A1/A0LONG복원순이다. 일반MOVE.W의상위WORD보존으로대체하면안된다. 마지막D6=A1/LONG(A0)=D6뒤dispatch를계속한다.14/1f→47672의sound대기는기존phase1로표현하지않으며별도미구현경로다.

## 실제 보존 resource와 중복 창 주의

`tools/pack_animation_control.py`는기존MS5Dv1kind1두파일을제공한다. 원본CPU=ROM대응,source/tool/frozenresource계약provenance와rawrole/indexdomain을metadata에기록한다.

| 파일 | sourceCPU/ROM범위 | payload/container | container SHA256 |
| --- | --- | --- | --- |
| control_04276c.ms5d | [4276c,5276c) | 65536/65568바이트 | 0e110324fa9a7d039c91f3c9a44b11a9ea60e0bbd7a73376166f91983beef0c2 |
| operands_06431a.ms5d | [6431a,64836) | 1308/1340바이트 | 832681dcfe9f037a2e1fa069c8327b9c1d15a144e5132fbfced8ada668e773b2 |

첫창은full0cselector와14의BYTEdispatch창[4a500,4a900)을함께포함한다. 옛290바이트field창이나별도중복callback창을추가하지않는다. 둘째창은기존knownscript의8개operandbase각각fullBYTEindex의raw합집합이며하나의논리table나자연index사용범위를확정하지않는다. 기존65f56..662c2script는opcode10도포함하므로이번0c/14연결만으로script전체가새API에서지원된다고주장하지않는다.

## 파일 보호와 I/O 한계

RAM과모든MS5A/MS5D는열기전에stat/S_ISREG로일반파일을검사하여FIFO를거부한다. pathcanonical/inodealias검사와두출력의O_NONBLOCK예약을유지한다. core성공전에는output을열지않는다. 두fstat가일반파일이고서로다르며모든입력의저장identity/현재inode와도다른것을확인한뒤에만truncate/쓰기한다. 실제casealias도inode로거부한다. 예약/검사실패에는기존파일을보존하고새placeholder는현재lstatidentity가예약inode와같을때만제거한다. write/close를검사하지만실제I/O실패의두출력원자교체/rollback은보장하지않는다.

## 재현과 검증 상태

아래178건/control mixed2건및회귀해시는saved_list_end추가전20숫자/21key schema의완료기록이다. 현재21숫자/22key와phase3 연결의새검증은 [indexed 실행 문서](animation-indexed-execution.md)에따로기록한다. 기존resource형식은변경하지않았다.

```sh
.venv/bin/python tools/pack_animation_control.py
.venv/bin/python tools/pack_activation_animation.py
.venv/bin/python -m unittest tools.tests.test_animation_control_resource
make build/step_animation_execution build/animation_execution_test
./build/animation_execution_test
.venv/bin/python tools/observe_animation_control_commands.py
.venv/bin/python tools/verify_animation_control_execution.py
.venv/bin/python tools/observe_activation_animation_scripts.py
.venv/bin/python tools/verify_animation_execution.py
make -j4 all test
```

Makefile의기존CLI에fixed_data_resource.cpp를추가하고runtime-resources에controlpacker를등록했다. core/unit의link는animation_execution.cpp와sprite_submit_execution.cpp를유지한다. 위도구는별도audit-only인자없이실행한다. 관측·검증명령은ignored artifacts의보고서와fixture를재생성하며ROM은수정하지않는다.

`artifacts/animation_control_execution/verification.json`의SHA256은 `01bf8c488c626b1f80346ba97dbdc9175357a0b269747281b2760e9ee8ea11d8`이다. 원본관측 `artifacts/animation_control_commands/observation.json`의SHA256은 `0590de05828d8639340843f06a33417aa32e0370196512bf5a4d17e97165a885`다. primary178건은0c128건과14의1d/1e50건이며, immutable원본49fc6를재실행하여전체65536바이트RAM·15레지스터·RTS반환carry·순서있는PVC912건·비활성continuation metadata를실제CLI결과와비교했다. 반환carry는true80/false98건이다. 실제MS5Dcontainer를기존C++loader로소비한결과이며, native관측에서실행하지않은RAM밖field fixture2건은성공수에서제외하고CLI오류로검사했다.

별도mixed supplement2건은synthetic liveRAM prefix에서MS5D를읽은뒤원본MS5A48980 script로이어지는하나의전체원본호출을비교한다. 0c분기경로는PVC36건,14/1d operand조회후08경로는40건이며primary912건과별도다. 두종류의resource를한호출에서실제로로드·소비했지만, synthetic prefix의자연게임도달성을뜻하지않는다. 오류48건은누락·부분·중복/overlap data창,미지원callback selector(1f포함),정렬/span과callback완료후다음fetch의늦은오류등에서실패와기존파일보존을검사한다. 문서갱신시보고서의입력31개와native/C++artifact1447개해시를모두현재파일과대조했다.

기존00/04/08/28회귀의현재보고서 `artifacts/animation_execution/verification.json` SHA256은 `ee6d4284ca590eada918161a6944b2b110c875ddd86854dede1fa087e51d0ade`다. primary90case/98phase와이전실제C++출력을이용한재개8건,별도liveRAM원본코드15건,negative157건이통과했다. 이는이번primary178건에합산하지않는다. 전체 `make -j4 all test`는exit0이며 `artifacts/animation_control_execution/make-all-test.log`에서Python225개,C++test실행145개,컴파일경고0건을확인했다. core작업자의격리normal/UBSan unit검증도통과했다.

나머지opcode,1d/1e외callback/대기,bankeddata,전체CCR/A7stack/cycles,물리mirror,자연IRQ/scheduler,composition/palettebinding,직접플레이와전체GOAL완료는이번확장의증거범위밖이며목표에서제외하지않는다.

## saved_list_end 추가 후 현행 schema 회귀

현재21숫자/22key schema로 `tools/verify_animation_control_execution.py`를재실행한보고서 `artifacts/animation_control_execution/verification.json` SHA256은 `4d03a72e673cc3ca6967d40d4c96527745bac0769915db78a05048c53c1907f5`이다. primary178건,별도mixed2건,negative48건이통과했다. 입력37개와native/C++artifact1447개의현재hash를모두대조했다. 위01bf8c...는이전schema의완료기록이며이새해시가현행schema회귀기록이다. 새opcode10검증은별도로기록한다.
