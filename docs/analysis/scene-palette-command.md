# Scene opcode04의 palette binding 의존성

이 문서는 `c96d141`의19-handler/12-register milestone 기록이다. 아래 report hash·수치는 당시 결과이며 같은 경로는 후속검증에서 덮어쓸 수 있다. 현행20-handler의장면표시설정과최종검증은 `scene-setup.md`를참조한다.

## Source와 bank mapping

Baseline은 `9c20d50`다. Canonical decrypted8MiB 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. Opcode04 handler1a192는 첫1MiB 고정 ROM의 같은 파일 offset이다. 아래 palette root·lookup·bindings는 메인이 원본에서 확인한 bank2MiB 전환 뒤 CPU200000 영역의 조회를 canonical ROM offset200000부터 대응시킨다. 이를 모든 임의 bank mapping의 검증으로 확대하지 않는다.

원본1a192는 CPU20000c의 root BE32=2003d0를 읽는다. Operand selector를 word 폭으로 왼쪽2 shift한 `(selector<<2)&ffff`를 signed16 offset으로 사용해 root+offset의4바이트 pointer를 읽는다. Selector 자체에 단순 상한을 새로 만들지 않는다. 예를 들어ffff는 shift 후fffc, signed offset-4이고4000은 shift 후0이다. 실제 조회 주소·span은 bank `[200000,2ffff0)`에 포함되어야 한다. Overlay/register 영역2ffff0 이후는 원시 palette data 추출에 포함하지 않는다.

## 기존 MS5D 리소스

`tools/pack_scene_scripts.py`는 기존32-byte header를 유지한 MS5D v1 kind2 banked window를 새 palette dependencies에 사용한다. 첫1MiB 고정 resource는 기존kind1을 유지한다. 기존 script·node·motion·indirect/path resource를 유지하고 아래 dependencies를 추가한다. Stable ID는 source 주소 기반이다. 원본 ROM과 생성한 추출 게임 데이터는 Git에 추가하지 않는다.

| File | Stable ID prefix | Raw span |
| --- | --- | --- |
| palette_root.ms5d | scene-palette-root | CPU=ROM20000c,4 bytes |
| palette_lookup_%06x.ms5d | scene-palette-lookup | root+signed shifted selector의4 bytes |
| palette_bindings_%06x.ms5d | scene-palette-bindings | binding pointer의6-byte records와first-word ffff terminal2 bytes |

Binding 일반 record의 첫 BE16 word는 slot0..255이고 offset2 BE16 source word,offset4 flags byte,offset5 sixth byte는 모두 보존한다. 첫word가ffff면 그2바이트에서 끝난다. Source word가ffff인 일반 record를 terminal로 오인하지 않는다. 각 일반 record는 완전6바이트여야 한다. 정지 조건은 bank data end와 시작+65536바이트 scan bound이며 논리 record 수의 증명이 아니다. Slot 범위·alignment·truncation·missing terminal은 API 추출 오류다. Empty binding의 첫ffff terminal도 원시2바이트로 보존할 수 있다.

Canonical opcode04는75 occurrence이며 selector·lookup72개와binding pointer72개를 사용한다. Lookup와binding 주소를 각각 dedup한다. 실제binding의 일반 record 합계1132,최대94개이며 모든 terminal까지의 원시 span을 보존했다. Palette 새 dependency는 root1+lookup72+bindings72=145파일,7228 payload bytes다. 기존39 dependency를 포함한 manifest 전체는184파일/8476 payload bytes다. 색상 데이터 전송·원본palette 계산·자연게임 사용 완료를 이 추출 결과로 주장하지 않는다.

Root container36바이트 SHA256은 `2a144b272fc7e6db7c5ec3c66d20020f82b8787e99b03c543d08dc80f58d8403`, payload4바이트 SHA256은 `d1da8268e014e1bd2c193f5597ded8156d699de2aea5fee60c6ac258292e1f4e`다. 각 lookup/bindings의 source CPU/ROM offset·end·container/payload size·SHA·bank source200000와 references는 manifest dependencies에 있다. Lookup references에는 raw selector/shifted word/signed offset/조회주소/binding주소가 포함된다. Bindings에는6-byte raw record와 terminal주소를 기록한다.

## 재생성과 검사

```text
.venv/bin/python tools/pack_scene_scripts.py
.venv/bin/python -m unittest tools.tests.test_scene_script_pack -v
```

Packer 재생성 exit0,합성 시험12개가 통과했다. 이번palette 시험3개는kind2 header를 포함해 shift16 wrap·signed negative offset,bank boundary/alignment,첫word slot과둘째 sourceffff 구분,sixth byte 보존,정확한2-byte terminal/CRC,truncated record·slot256·bank overlay end 거부를 확인한다. 기존motion time/type 구분과script 시험도 유지한다. 생성184 dependency container의 header/CRC/hash와canonical raw bytes를 별도 직접 roundtrip으로 확인했다. 모든 source span을 검증한 뒤 파일을 publish한다.

최종 `extracted/runtime/scene_scripts/manifest.json` SHA256은 `c9df39f855b267c0b547e2392be4a334a4e698ea48d6a1593e571e72018b4dc1`다. Manifest 변경은 palette dependency 추가이며 기존 binary payload는 유지한다. Source hash·bank mapping·원시 필드와handler 실행 검증을 구분한다.

## 현행19-handler/12-register API

`SceneCommandState`는 D0..D7/A0/A1/A2/A4의 full12 register를 입력·출력한다. `execute_scene_command`는 기존18 handler에04를 추가해19개를 지원하며08만 미지원이다. Raw script를 다시 decode한 A1 exact opcode,11-register 이전 계약,borrowed optional dependencies와 RAM/state/ordered ports transaction을 유지한다.04 이외 handler는 A4를 보존한다. CCR·나머지 address registers·CPU stack은 API 출력이 아니다.

04는 operand selector를 D0.lowword에 읽고 RAM0010.word를0으로 저장한 뒤 port size2/address2ffff2/value1000, size2/address2ffff0/value0을 순서대로 남긴다. D0.lowword를16비트 shift2한 signed offset으로 root lookup을 읽어 binding resource를 찾는다. 이 scene 경로의 bank dependency는 CPU=ROM 주소의bank2MiB raw span만 받는다. Root/lookup은 exact4바이트이고 binding은 전체 terminated window다. Generic banked loader가 지원하는 다른 aligned bank mapping까지 이 caller가 지원한다고 주장하지 않는다.

### Generic binding helper와 반환값

`main_startup.h/.cpp`의 `PaletteBindingState`와 `bind_palette_resource`는 원본8da2의 terminated binding window를 처리한다. Fixed 또는 aligned banked window의 source mapping·slot0..255·exact6-byte records+ffff terminal을 검증한다. 이 helper는 binding resource의 A0 CPU주소를 사용하고 입력 D0.lowbyte로watchdog size1/address300001을 먼저 쓴다. Scene04에서는 앞의 shift 결과 lowbyte가 watchdog값이다.

각 record는 slot<<4 word offset,source.lowbyte×16+4 bucket을 구한다. D0.lowword=offset,D1.lowword=source,D4.lowword=bucket을 남기고 A1=104d92,A2=104d92+offset,A4=104d92+bucket을 설정한다. 해당 bucket의 이미 첫 node이면 relink를 건너뛰며 D2/D3는 그 단계에서 보존한다. Relink할 때 D2.lowword=old previous,D3.lowword=old bucket head를 남기고 ring을 unlink한 뒤 bucket앞에 삽입한다. Word 결과는 각register 상위16비트를 보존한다.

Slot node+8 word=ffff,+a/+c word=source를 저장하고 sourceffff이면+f byte=2,그 외에는 rawflags|80을 저장한다. Sixth byte는 리소스에 보존하지만 이 helper가 소비하지 않는다. Terminator 뒤에는 D0.lowword=ffff,A0=exclusive end다. Scene caller의 A1은 handler 완료 뒤 다음 opcode 주소로 복구되며 D5/D6는 보존되고 D7에는 dispatchopcode04가 남는다. D3의 최종 lowword는 마지막 실제 relink에 따라 달라져 단순 마지막record 값으로 치환하지 않는다.

Ring/binding resource 오류를 만나면 앞선 RAM0010과bank ports를 포함해 전체candidate를 취소한다. 실제 palette 색상 transfer를 수행하지 않으며 ports는04의2 bank writes+1watchdog,총3개다. Palette RAM registration과 bank selection을 물리 VRAM/color 전송 완료로 해석하지 않는다.

## 현행 CLI와 loader

```text
build/step_scene_command D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS SCRIPT_MS5D NODE_POINTERS_MS5D [DEPENDENCIES_DIR]
```

JSON은 full12 register와writes를 반환한다.04는DEPENDENCIES_DIR에서 palette_root→computedpalette_lookup→pointedpalette_bindings 순으로3파일을 `load_banked_data_resource`로 읽는다. 다른 dependency는 기존fixed loader를 사용한다. Loader는kind2 CRC/header/exact length와 CPU/ROM bankmapping 조건을 확인한다. Input/output/resource 및실제로선택한dependency path/inode alias를 거부한다. File로더검사와 API내binding/ring검사를구분한다. Port파일은기존sizebyte+addressBE32+valueBE32의9byte records다.

## 최종 native 검증과 회귀

`artifacts/scene_command/verification.json`의 최종 SHA256은 `308312679576dba7914c1bf16662b0443fb6136ce415346d789f700e327e4b51`이다. Session12359은 exit0으로4,330 native/99 negative/19,875 ordered ports를 통과했다. Full RAM/D0..D7/A0/A1/A2/A4와port순서가 일치하며 A7 RTS endpoint도 확인했다. Binary SHA256 `24b8ee0a96d4107132a11e628fb035713d6fabd9bd964a6890775cd9db41778d`와fixed1MiB 원본은 시작·끝에 같았다.

Canonical41 script/814 command의 지원18종773 occurrence에는04의75개가 포함되고,미지원08은41개다. 지원19종 중4c는canonical에없어native실행완료를주장하지않는다. 실제 CLI가184 dependency의 CPU/ROM/raw/CRC를 확인했다. 그중145 palette파일은kind2이고 기존39파일은kind1이다. 각palette binding의 generichelper효과와04bankports를 원본과 비교했다. Physical200000..2fffef는원본ROM2MiB source mapping으로불변을 확인하며PVC registertail은ROMimmutable검사에서제외한다.

Nativefixture는random workRAM에원본3ef2 palette initialization을실제실행해validring을 만든다.3ef2는비교command의자연caller가아니라start-only fixture다. Canonicaloperand를바꾸지않으며random RAM/high registers/slot boundary는명시적fixture다. Syntheticoperand와invalidresource검사는C++조건이며원본ROM을patch하거나해당오류조건을native실행하지않는다.

Actual CLI carry는42개구간/781호출이다. 모두길이2이상이므로이번결과에서는전체carrycall수와길이2이상구간내call수가같다. 그중40개adjacent-supported구간은771호출,별도2개palette already-head/rebinding구간은각5회로총10호출이다. Full12register와RAM/A1/A2/A4를승계하고미지원opcode또는negative terminator에서멈춘다. 각standalone callcontext는명시적으로재설정하므로전체scene scheduler나자연frame실행은검증하지않는다.

99negative에는missing/malformed bankroot·lookup·binding,kind1/kind2loader조건,잘못된mappedwindow와requireddependency/alias·ring rollback검사가포함된다. 실패시RAM/state/orderedports·CLIoutputs를보존했다. Packer시험12개와kind2window/header검사는원시추출·container조건의근거이며nativehandlercomparison과구분한다.

전체`make -j3 all test` session24446은exit0,Python137/C++99/warning0으로통과했다. 로그는 `artifacts/scene_command_build_test.log`다. Shared palettebinding helper 변경뒤stagepreparation 회귀도101native/37negative/441ports를통과했고reportSHA256은 `800662368857e8ab8f11c8c72ab179ca9dbbf65d7fe6a14ed9814c29238c88fd`다. Mainstartup 공유binding 회귀session96709도exit0으로209native/32negative/418watchdog/2preparation integration을통과했다. 실제 `artifacts/main_startup/verification.json` SHA256은 `2bf5387682dae840040749fb882917080a43ecedb22a1dd13766ca123cccea7a`로이전값과같고로그는 `artifacts/scene_command_main_startup_regression.log`다.

현재지원은단일19handler와bankedpalette등록까지다.08·전체scene scheduler·자연게임도달·후속색상전송·CCR/그밖addressregister·hardwaretiming은미완료다.
