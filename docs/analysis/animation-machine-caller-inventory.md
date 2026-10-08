# Animation machine caller 정적 inventory

후속 readiness의 공유 stack·실제 carry 분기 연결은 `animation-machine-readiness-execution.md`를 따른다. `93b5b40` 이후47d20→47d3e→4847c→47d42를 연결했다. 아래 수치와 지원 경계는 각 이전 단위의 기록이며 최신 구현 상태와 구분한다.

현재 carry 확장은 `animation-machine-carry-execution.md`를 따른다. `ed42971` 이후 Unknown/Clear/Set 상태와 실제 BCC·BCS caller를 추가했다. 아래 이전 단위의 검증 수치·해시는 당시 기록이며, 최신 회귀 해시는 carry 문서에 별도로 기록한다.

기준 `ff25485` 이후 작업이다. 아래 구현 상태와 입력 pin은 이 baseline을 읽은 시점의 기록이며, 같은 단위에서 추가한 caller/initializer 연결은 `animation-machine-callers-execution.md`를 따른다. `AGENTS.md`/`docs/GOAL.md`를 읽고 canonical BE 프로그램을 `load_verified_program`으로 검증했다. 원본은 `extracted/program/maincpu.decrypted.be.bin`, 8,388,608바이트, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 이 문서에서 검토한 호출 명령은 모두 **fixed CPU 주소=ROM 파일 offset<100000**이다. 물리 ROM의 나머지 부분을 CPU 주소와 동일시하지 않는다. ROM·기존 source/artifact·runtime resource를 변경하거나 빌드하지 않았다.

## 확정된 지역 caller 근거

아래는 기존 stage activation 분석과 원본의 연속 명령 bytes를 대조한 정적 사실이다. 자연 scheduler에서 이 경로가 실행됐다는 새로운 동적 증거는 아니다.

| CPU=ROM | raw bytes | 명령과 지역적 의미 |
| --- | --- | --- |
| 47d0a | `227c000489c2` | A1=489c2 script |
| 47d10 | `303c0100` | D0.low=0100 |
| 47d14 | `4eb900049f8c` | JSR initializer49f8c; return47d1a |
| 47d1a | `4eb900049fc6` | JSR animation49fc6; 실제 caller return47d20 |
| 47d20 | `6000001c` | BRA47d3e, CCR 읽거나 변경하지 않음 |
| 47d3e | `4eba073c` | JSR4847c(PC-relative), return47d42 |
| 47d42 | `6400002e` | BCC47d72; 직전 readiness4847c의 carry를 읽음 |
| 47ed0 | `3d7c00ea0020` | object+20 WORD=00ea |
| 47ed6 | `227c00048980` | A1=48980 script |
| 47edc | `303c0100` | D0.low=0100 |
| 47ee0 | `4eb900049f8c` | JSR initializer49f8c |
| 47ee6 | `3d7c00a00042` | object+42 WORD=00a0 |
| 47eec | `3d7c01800046` | object+46 WORD=0180 |
| 47ef2 | `3d7c005a007a` | object+7a WORD=005a |
| 47ef8 | `4eb90001c63c` | JSR1c63c |
| 47efe | `2cbc00047f04` | LONG(A6)=47f04 callback address |
| 47f04 | `4eb900049fc6` | JSR animation49fc6; 실제 caller return47f0a |
| 47f0a | `4a6e007a` | TST.W object+7a: N/Z 설정, V/C clear; animation carry 소멸 |
| 47f0e | `6700000a` | BEQ47f1a, 위 TST의 Z를 읽음 |
| 47f12 | `536e007a` | nonzero 갈래에서 object+7a WORD 감소 |
| 47f16 | `60000026` | BRA47f3e |
| 47f3e | `6000017c` | BRA480bc frame body |
| 47f42 | `61000454` | zero/two player-marker 조건의 다른 갈래 BSR48398 |
| 47f46 | `6000fd12` | BRA47c5a |

**47d1a와47f04의 지역 continuation은 animation의 반환 carry를 소비하지 않는다.** 47d20의 BRA는 carry를 잠시 보존하지만 47d3e에서 readiness를 호출하므로47d42를 animation carry 소비라고 표시하면 안 된다. 또한47d24→4e216 뒤47d2a BCC,47d2e→bee 뒤47d34 BCS는47d20이 건너뛴 별도 경로이며 각각 해당 helper의 반환을 읽는다. 이 결론을 다른 caller까지 일반화하지 않는다.

49fc6 원본은 null pointer 경로49fe6 `003c0001`(ORI.B #1,CCR)와49fea `4e75`, 공통반환4a0e0 `e247`(ASR.W #1,D7) 및4a0e2 `4e75`를 가진다. 따라서 원본 반환 carry 자체는 존재한다. 현재 machine state가 CCR을 제공하지 않는 사실과 caller가 그것을 필요로 하는지는 별도로 판단해야 한다.

## Tail caller와 carry 사용 후보

단 하나의 aligned absolute JMP raw match는2b52c `4ef900049fc6`다. 연속 decode상2b520 `0c41f000`(CMP.W #f000,D1),2b524 `57c0`(SEQ D0.byte),2b526 `8e00`(OR.B D0,D7),2b528 `1d47007e`(object+7e=D7.byte) 뒤에 이어진다. 이 지역 명령열은 실제 JMP encoding이며 **새 return frame을 push하지 않고 기존 caller frame으로49fc6에 tail transfer**한다. 상위 caller·자연 실행은 여기서 확인하지 않았다.

전체 raw JSR 후보 중 직후 word가 BCC인 경우736개, BCS인 경우25개(합761개)다. BHI/BLS 직후 후보는0개다. 이 수는 정렬된 byte pattern 통계이며761개를 모두 검증된 함수 caller/실행 경로라고 뜻하지 않는다. 예를 들어1dc84 `4eb900049fc6` 직후1dc8a `64000040`은 BCC1dccc이고,1dc70 BSR1d182→1dc74 JSR4bfc0→1dc7a MOVE.W object+1e,D0→1dc7e JSRce02의 연속 명령으로 대조했다. 이 지역의 BCC는 중간 flag-writing 명령 없이 animation 반환 carry를 직접 읽는다. 일반 caller 연결에는 CCR/carry 문제가 남는다는 구체적인 정적 반례다. 해당 함수의 entry/reachability/전체 분기 의미는 미확인이다.

## 전체 aligned raw scan과 증거 수준

8MiB 모든 짝수 offset에서 `4eb9 00049fc6`/`4ef9 00049fc6`를 검색했다. 또한 fixed영역에서 JSR/JMP PC-relative(`4eba`/`4efa`, target=PC+2+signedWORD)와68000 BSR(`61xx`, short 또는WORD displacement)을 산술 검사했다. 결과는 **JSR.absL1621개+JMP.absL1개=1622개**, 모두fixed영역이며 PC-relative/BSR 직접 target match는0개다. absolute-short로49fc6를 표현할 수 없으며 indirect register/memory jump나상위 callback binding은 이 검색의 대상이 아니다. odd offset은68000 명령경계가 될 수 없어 제외했다.

아래 목록은 누락 없이 raw match를 보존하는 **후보 inventory**다. 각 offset의6바이트는 JSR이면`4eb900049fc6`, JMP이면`4ef900049fc6`다. 범위별 나열은 code classification이나 자연 도달성을 뜻하지 않는다. full-region 자동decode를 분석완료로 취급하지 않았고, 위 지역 명령열만 `disassemble_range`의 padded decode와 실제bytes를 대조했다. 다음 목록에서 `C`=직후BCC pattern, `S`=직후BCS pattern, `J`=JMP; 무표시는JSR이며 carry 미사용을 뜻하지 않는다(더 늦게 읽을 수 있음).

### Raw offset 10000..20000 (44개)

```text
01dc84C 01df4c 01dfb4 01e208C 01e292 01e2eeC 01e372C 01e3f2C 01e466 01e4c4C 01e572C 01e76e
01e810C 01e8be 01e962 01e9beC 01ea32 01ea7e 01eb06C 01eb68 01ec60C 01ed0eC 01eed6 01efcc
01f066 01f112C 01f1c4C 01f290C 01f32aC 01f3c4C 01f476C 01f524C 01f5beC 01f74cC 01f7fcC 01f8ce
01f976C 01f9c6C 01fabaC 01fb18 01fb94 01fc1e 01fe62 01ff3e
```

### Raw offset 20000..30000 (91개)

```text
0200a2C 02018eC 020b38 020c26 020cce 020db4 020e50C 020ee8C 020fa4C 021034C 0210aeS 021158C
021258C 0214acC 021516 022c5e 022ca8 022d26C 022f56 022fceC 02311e 0233e4C 0234c0C 0236ae
023762C 0237b8C 0238fc 02398aC 0239d2C 023bd2 023c44C 023cde 02516c 02544eC 026380C 026c54
026efaC 027a3aC 027c60 027d04C 027eae 027f38C 028152 0281d8C 028450 029012 02916c 0292c8C
02941a 02953aC 029b42 029ba8 029bfeC 029c90 029d8aC 029dfcC 029e70C 02a686C 02a786 02a80e
02a878C 02a8c8 02a924C 02a964 02a9fc 02aa6aC 02b52cJ 02cb6eC 02d0e2 02d10cC 02d4ca 02d568C
02d67e 02d7acC 02d858C 02d8a6C 02d9c0C 02daf4C 02dbc8C 02f102 02f130 02f168 02f196 02f21e
02f24c 02f280 02f296 02f2b4 02f3a6C 02f51a 02f5b0
```

### Raw offset 30000..40000 (85개)

```text
030dacC 030e82 030ebaC 0310d0 0312ca 03143aC 031490C 031526S 0315beC 031632C 031664 031ac2S
0331a2 0331dc 033288C 03332c 0333e2 033472 0334cc 033526C 0335d8 033816 03392eC 033fcaC
0340b8 034204C 0342aeC 03435cC 0343c6C 03445eC 03451e 0345b0C 03469c 0346b8 03486c 0361d2C
0362d2 03633eC 036394C 036506 0365e0 036796 036906 03698aC 036aa8 036ae0S 036b1aS 036b84C
036ebc 036f24C 036f78C 037074C 0370c6C 037182C 0371e6C 03739e 03740eC 03752a 037734 037884
037b5e 037d9eC 037de0 03a33aC 03ad36C 03ae68 03af0cC 03af5aC 03b020C 03b106C 03b1a0 03b218C
03b37a 03b386 03dba8C 03dcfc 03e23e 03e2e6S 03e3a4C 03e446 03e48cS 03e538C 03e5aa 03e63eC
03e678
```

### Raw offset 40000..50000 (18개)

```text
040758C 040956 040a26 0423e6 0425a0 042638C 042e98 043140C 043258C 043406 04348eC 043546C
047d1a 047f04 04daf0 04db9e 04dc2eS 04f49c
```

### Raw offset 50000..60000 (88개)

```text
05024a 050576 050584 05084a 050b34 050cea 050e5a 050f3e 0513fa 05159a 051798 051802C
051a48 051abcC 051cc8 051d0a 051d4c 051dc6 051ee8 051f5eC 051fb4C 05213c 052f66 053172
0531e2 05322cC 053284C 05336c 0533e2 053444 053518 053552 0535f2 0536f4 053742 053770
0538c2 0539ea 053ab8C 053c26C 053cf8C 053db2 053e08C 053e4aC 053f6aC 054022 0540d0C 054152
0543a0 054878C 056b64 056bb6 056dca 057682 0576d8C 057772C 0577d4C 0579e6 057b32C 057bd0
057c9c 057d66 057e14 057eee 05800e 0580e4 058200C 058354 058470C 0584dcC 058618C 05ab64
05ad0c 05adecS 05b49c 05b54e 05e7ea 05e8c0 05ee16C 05ef48 05efc0C 05f18aC 05f38eC 05f5c8
05f6b6 05f870C 05fcaeC 05ff78C
```

### Raw offset 60000..70000 (37개)

```text
06030e 06040e 0604fe 0607d0 0609d2 060aec 060e26C 060e66 060f00C 061116C 0611e6 061286
06145c 061714 06181e 06188e 0618fe 061964 06199cS 0619ca 0619fcC 061a76 061ad6 061b3c
061b78 061bd8S 061c4aS 061cceS 061cfcS 061d30 061d62S 06f800 06fa2c 06fab0 06fb66C 06fc8cC
06fd1cC
```

### Raw offset 70000..80000 (281개)

```text
070ae2C 070b74C 070bf8C 070c86 070e0cC 070f84C 07110e 07128cC 07133a 0713c4C 071454C 0714e4C
0716b6C 0717ce 071888 0718cc 071978 0719d8 071a68C 071b28 071d2e 071dc2C 071e72 071f18C
071fbc 0720fcC 07219aC 072238C 0722c6C 072376 072400C 0724bc 07252eC 0725c0C 07266e 072700C
072766C 0727ccC 072832C 072898C 0728feC 072964C 0729e8C 072bdcC 072cfeC 07311a 073204C 0732fa
0733b6 07344aC 0737c2 073832C 073886C 0738e2C 07392cC 073a84 073ae4 073b44 073be0C 073c52C
073cf0 073d72C 073e02 074006 07410c 074160C 0741de 074226 0742d4C 074350 0743fcC 074476C
074506C 074574C 0745e2C 074676C 074716C 07481eC 0748fe 0749ceC 074a38 074acaC 074b3cC 074bb6C
074c46C 074caeC 074d16C 074daaC 074e32 074e7a 074f04C 07506c 075222C 075c58 075d52C 075db4
075ec6 075fb2C 07600a 076086C 07619e 07620eC 07628aC 07635aC 0763d2 076410 07645eC 0764caC
076530 07659c 076640C 0766eaC 07676e 0767bc 0767f2 0768ee 0768fe 07699aC 076df2 076e44C
076eaaC 077044C 0771aa 07725eC 07752aC 07759a 0776d0 07771c 0777c4 07788e 07795c 077a56
077ada 077b56C 077bc4 077c46C 077d04C 077d76 077dc6C 077ee0C 077f8c 07807eS 07813a 0781f2C
078246C 0782c2C 078350C 07844a 07849aC 0784fe 0785d6C 07862c 0786c2C 078750C 0787b0C 07880c
0788c6C 078954C 0789b0C 078aa0 078af2C 078b92 078c0eC 078e7e 078eeeC 07900c 079dc2 079eb0
079eecC 079f48 079f78 07a00eC 07a072 07a106C 07a160C 07a1d8C 07a22eC 07a27eC 07a2faC 07a36aC
07a40eC 07a580 07a638C 07a680 07a6faC 07a754C 07a7aeC 07a826C 07a876C 07a8c6C 07a942C 07a9b2
07a9e2 07aa3cC 07ab44 07ac22 07ac7a 07ac9a 07ada8 07af06C 07af80C 07c8ac 07c9a6 07c9ecC
07ca5c 07ca9c 07cb44C 07cbb8 07cc56C 07ccc8 07cd46C 07cda6C 07ce06C 07ce8cC 07cf18C 07d024C
07d0b8C 07d148C 07d1d2 07d28cC 07d2e0C 07d380 07d434 07d4ee 07d57c 07d62cC 07d69a 07d73aC
07d7b2C 07d812C 07d878C 07d902C 07d98c 07da54C 07daa8C 07db00C 07db62 07dbeeC 07dc52C 07dcc4
07dd42C 07dda6C 07de40C 07def0 07df94C 07dfeeC 07e048C 07e0ceC 07e148 07e188 07e2e4 07e49aC
07f40aC 07f45cC 07f4beC 07f516C 07f5b4 07f63cC 07f66aC 07f6dc 07f730C 07f78aC 07f7f2 07f8c0
07f908C 07f96aC 07f9f4C 07fa46C 07faa2C 07fb00C 07fb7cC 07fc16 07fc64C 07fcd8C 07fd44C 07fdbeC
07fe5e 07fee6C 07ff14C 07ff66C 07ffc2C
```

### Raw offset 80000..90000 (238개)

```text
08001aC 08009c 0800f0C 080168 0801ccC 08026e 080300 080404 08047aC 080a54C 080ae0C 080b3cC
080bd4C 080c3aC 080d1a 080d6eC 080dc8C 080e1aC 080ec6 080f1aC 080f84 080fe6C 081038C 081158
0811a0C 081220C 081318C 0813d4 081454C 0814e0C 081568C 081608 0816d0 081836 0818acC 081a9e
081b9a 081c5a 081cf4C 081e50C 081fbe 082010 082064C 0820acC 082106 082168C 0821caC 082288
08253c 0825caC 082672 082786 082840C 0828d2C 082998C 082a3eC 082bcc 082c86C 082d18C 082ddeC
082e6eC 082f16 082fa4C 08303eC 0830d8 083176C 08327aC 08336eS 083466C 0835da 083be4 083c34C
083c98 083d46 083db8C 083e22 083e72C 083eeaC 083f78 084016S 0840c2C 084242 0842b4C 084384C
08445a 084c0e 084cf6 084e58 084f02C 084f90 085042C 0850b8C 085124C 0851b6C 085284 0852ea
085354C 0853eaC 085472 085492 085548 08566c 0857a6C 085a8c 085b34 085b86 085be6C 085c62
085ce8 085e6c 085eac 085f5cC 085fb8C 086048 08608cC 086156C 0861bc 086228 0863baC 086420
08648c 08674c 086858 08693eC 086a28 086b50 086bdaC 086cc8C 086da8 086eeeC 086fb0 08707a
087144 0871caC 0872e6C 08734aC 087472C 08750e 0875f4C 0876be 0877be 0878b0C 087a22 087a56
087b10C 087c52C 087f3c 0880e8 0882a8 0883e8 08845cC 088530C 0890e8 0891f2C 08926a 0892ba
089352C 08941e 089562 0895eeC 0896a2 0898da 0899e0 089a6cC 089ab8C 089b7c 089bc6C 089c6a
089df0 089f82 08a0c6C 08a1b8C 08a222C 08b44e 08b648 08b736 08b89c 08b9e2 08ba74 08bbe4
08bd62 08be48C 08bebeC 08bf80S 08c7bc 08c818 08c88cC 08c8ee 08c9ceC 08ca4aC 08cabc 08cb9cC
08cc00 08cca8C 08cd0cC 08cd58 08cdfcC 08ce54C 08cf18C 08cf86C 08d058C 08d0bcC 08d126 08d172C
08d23a 08d2faC 08d364C 08daf6C 08db6eC 08dc9c 08ddd6C 08de74 08df0cC 08e060C 08e216 08e35aC
08e3f8C 08ecec 08ed5a 08edaa 08ede4 08ee96 08ef00 08ef6e 08efb4 08f00c 08f086 08f0d0
08f1a8 08f5e8 08f846 08f950C 08fc1eS 08fd02 08fd8aC 08fe98 08ff4aC 08ffccC
```

### Raw offset 90000..a0000 (153개)

```text
0900ce 090af8 090b58 090b88 0917b4 0917e6 091892 09190c 091a38C 091ad4 091b04 091dba
091e8c 091f62 0920b2C 09215aC 0922b6S 09231cC 092416 09243c 0924de 09254c 09265cC 0926c0C
0928e4 092998C 092a88C 0935b2 093686 09376eC 093842C 09390eC 0939e4C 093a36C 093afaC 093b98C
093bf4C 093c8eC 093d60C 093eba 093fc2C 094b04 094d36 094e0c 094e90 095214 095362C 09593c
0959d8 095c2a 095ca0 095d8a 095dee 095eea 095f58 0967f6 09686e 09690c 096978C 0969e2C
096a2e 096ab8 096b26 096bb4C 096cf6 096d58 096dbc 096e50C 096f40C 096fecC 09704aC 0970ccC
09711cC 097182C 0971d2 097256 097314C 097434 099a18 099a88 099b08 099beeC 099cacC 099d98
099decC 099ef0C 09a018 09a17a 09a37a 09a432C 09ae22 09ae98 09af32C 09afb0C 09b11c 09b288C
09b3f0C 09b4d0 09b55a 09b5d0 09b660 09b74a 09b936 09bae0C 09bc4a 09bd38 09bdc0C 09bf62
09bffe 09d190C 09daea 09e296 09e2e2C 09e340 09e394C 09e426C 09e586 09e5e6C 09e62e 09e7f6
09e8d6 09e976 09ea88C 09eb1eC 09ebc0C 09ec7aC 09ecdaC 09ed2e 09eda8 09ee3e 09eebeC 09ef06C
09ef54C 09efb6C 09f02cC 09f0baC 09f102C 09f180C 09f1de 09f232C 09f6bc 09f750C 09f7cc 09f9c0
09fa8a 09fb9a 09fc40 09fcf4C 09fd70C 09fdf2C 09fe60C 09fed8C 09ffb0C
```

### Raw offset a0000..b0000 (236개)

```text
0a002cC 0a00a8C 0a0106 0a015aC 0a0c36C 0a12a8 0a1a08 0a1a66C 0a1aac 0a1bec 0a1c3e 0a1d1a
0a1d8c 0a1e0aC 0a1e50C 0a1e9cC 0a1efcC 0a1f68C 0a2020C 0a2066C 0a20b4 0a2108C 0a2f20 0a30b4
0a36c4 0a3722C 0a3760C 0a38d2 0a39e8 0a3a62 0a3abe 0a3b5eC 0a3be8 0a3ca4 0a3d4c 0a3df4
0a3ec6 0a3f54C 0a3f9aC 0a3ff0C 0a405c 0a40b0C 0a4448 0a4708 0a485e 0a4a26 0a4b66 0a4c60
0a4dce 0a4f38 0a5062 0a514a 0a51ae 0a51f6 0a531aC 0a5474 0a5704 0a586e 0a5974 0a5a96
0a5b60C 0a5bf4 0a5e26 0a6114 0a62c2 0a641c 0a6584 0a66aa 0a67b4C 0a68fc 0a6abc 0a6bc2C
0a6d1e 0a6ea0 0a6f42 0a702c 0a7096 0a71a6 0a7214 0a74f6 0a76ca 0a7812 0a791e 0a7a6e
0a7bda 0a7c60 0a7d4a 0a7db4 0a7ec4 0a7f32 0a81c6 0a8254C 0a82a6C 0a8346 0a83fc 0a847e
0a85c4C 0a87da 0a8870 0a88a2 0a88d4 0a88ea 0a89b4 0a8a3e 0a8ac4 0a8b5aC 0a8d34 0a8da2
0a8ea0 0a8f36 0a906a 0a91d0 0a9366 0a93e6C 0a9434C 0a952e 0a961c 0a9662 0a971a 0a97fc
0a987c 0a9900C 0a9b08C 0a9c16C 0a9c96C 0a9d94 0a9e06 0a9e78 0a9eea 0a9f28C 0aa10aC 0aa21aC
0aa29aC 0aa34a 0aa3ca 0aa428C 0aa4c2C 0aa6acC 0aa76a 0aa7ecC 0aa894C 0aa9f2 0aaac0 0aab62
0aabaeC 0aabf6C 0aac7a 0aacd0C 0aad54 0aadaaC 0aadf6 0aae4aC 0aaeaa 0aaef8C 0aaf82C 0ab018C
0ab1c6 0ab2a4 0ab3a6 0ab496 0ab616 0ab6c6 0ab750 0ab79cC 0ab7e4C 0ab868 0ab8beC 0ab942
0ab998C 0aba3aC 0aba88C 0abb20C 0abbf6 0abc4c 0abc9aC 0abd14C 0abddaC 0abe4aC 0abeaeC 0abfdc
0ac070C 0acbecC 0acdea 0ace9cC 0acf5aC 0acfc8C 0ad086C 0ad0dcC 0ad16cC 0ad242 0ad29a 0ad2e8C
0ad374 0ad3f4 0ad4e6C 0ad57eC 0ad5e0 0ad606 0ad65aC 0ad6ee 0ad758 0ad7d4 0ad88eC 0ad9aa
0ada76 0adb7a 0adc9eC 0add12 0add7c 0ade2eC 0aded8 0adf56C 0adff0C 0ae0ba 0ae180C 0ae2d8C
0ae352 0ae494 0aeb02 0aebda 0aed12 0aedfa 0af036C 0af1ea 0af324 0af59e 0af69eC 0af72e
0af8b4 0af8f8 0af932C 0afc8cC 0afce0C 0afd8aC 0afe4e 0aff36C
```

### Raw offset b0000..c0000 (215개)

```text
0b0042C 0b17e2C 0b19f8S 0b1a56 0b1af4 0b1e22 0b25de 0b2798C 0b27f4C 0b283cC 0b288eC 0b28d6
0b2984C 0b29ccC 0b2a32C 0b2aa2C 0b2aeaC 0b2b4cC 0b2b94C 0b2bfaC 0b2c52C 0b2c9aC 0b2d0a 0b2decC
0b2e62C 0b2eb4 0b2f46 0b2facC 0b3042C 0b3080 0b321e 0b329c 0b33c2 0b3434 0b4018C 0b4334
0b4c4e 0b51e0 0b527e 0b530c 0b537a 0b53d4C 0b5486C 0b5548 0b56f8 0b5cf0 0b5daa 0b5eb0C
0b5f78C 0b6000 0b640a 0b64acC 0b65f6 0b66be 0b6768 0b6874C 0b6a20 0b6ae4 0b6b80 0b6c76
0b6d6eC 0b6e54C 0b6fa8 0b6fd8 0b70b2 0b719aC 0b7264C 0b738cC 0b7482 0b7532C 0b75e8C 0b76a8C
0b77faC 0b787a 0b7a0cC 0b8190 0b820eC 0b829cC 0b82f6 0b8374C 0b83ecC 0b8418 0b849aC 0b85aa
0b85f8S 0b884c 0b88b2 0b892eC 0b8a12C 0b8accC 0b8c36 0b8ca2 0b8d54C 0b8de0 0b8e32C 0b8e78C
0b8f2aC 0b8f74C 0b8ffaC 0b9052C 0b90ca 0b9166 0b928e 0b933c 0b9456 0b94d0 0b95c4 0b9634
0b96aa 0b9720 0b9792C 0b97f4C 0b99c4 0b9b36 0b9c18 0b9cf2 0b9d8e 0b9f7a 0ba0aa 0ba1a0
0ba5a0 0ba61a 0ba6a6 0ba7e4 0ba8b8 0ba92e 0ba996 0ba9eaC 0baa2a 0baa70C 0bac80 0bae26
0baec6C 0baf50C 0bb056 0bb0a4C 0bb0ea 0bb128C 0bb16e 0bb20cC 0bb2beC 0bb338 0bb39aC 0bb40aC
0bb47aC 0bb52c 0bb64e 0bb7ca 0bb818 0bb86a 0bb9a0 0bba62 0bbd42 0bbe7a 0bc018 0bc04eC
0bc084 0bc1b0 0bc1f0C 0bc278 0bc2e6 0bc332C 0bc38eC 0bc46aC 0bc4b6 0bc50a 0bc57c 0bc5e0
0bc62a 0bc69cC 0bc6d8C 0bc700 0bc748C 0bc784C 0bc7ce 0bc83c 0bc8ea 0bc92aC 0bc978 0bca14C
0bca68 0bcad4C 0bcb1a 0bd450 0bd58c 0bd8a6 0bd94aC 0bdaf6 0bdbb6 0bdc36 0bdcae 0bdd44
0bde32 0bdea6 0bdf58 0be0a0 0be120 0be1c0 0be2dc 0beb72 0bec68 0bee06 0bee56C 0beea6C
0beefe 0bf02e 0bf09e 0bf106 0bf16e 0bf6de 0bf87a 0bf96c 0bf988 0bfa18 0bfd8eC
```

### Raw offset c0000..d0000 (56개)

```text
0c2cb6C 0c2e3cC 0c2f06 0c30f4 0c3140 0c31d4 0c3256C 0c3466C 0c3502C 0c3b64 0c3e04 0c3e82C
0c3eee 0c3f7a 0c4052 0c40ecC 0c4188 0c44a8 0c4618 0c469cC 0c4714 0c4798C 0c4804C 0c488aC
0c48eeC 0c496a 0c4a52 0c4aceC 0c4b7eC 0c4c08C 0c4caa 0c4d4eC 0c4dfeC 0c4e88C 0c4f2eC 0c4fc4C
0c505eC 0c50fc 0c51e2 0c5268 0c52f2 0c535eC 0c5406 0c5476C 0c5580C 0c5608C 0c5668 0c5706C
0c5a40 0c5b4aC 0c5caeC 0c5e24 0c5f52C 0c6376C 0cdd36C 0cded8C
```

### Raw offset d0000..e0000 (53개)

```text
0d14fe 0d166a 0d1724C 0d1774C 0d17e6C 0d1984 0d1b10 0d1bb0 0d1c16 0d1c76C 0d2012C 0d23b8S
0d307aS 0d34e4 0d35c2 0d37ceC 0d3c86C 0d3ce4C 0d3d6aC 0d3df6C 0d417aC 0d44d2 0d46d8C 0d481aC
0d4a74 0d4d04C 0d4d98C 0d4f4a 0d4fa8 0d4ffc 0d505a 0d50e8 0d5150 0d51a0 0d51ce 0d520e
0d52f8C 0d53be 0d545a 0d5812 0d5a86C 0d6eae 0d6f10C 0d77d4 0d82c4 0d83aeC 0d8654 0d86ecC
0de8c2 0dee2e 0def50 0def92 0defce
```

### Raw offset e0000..f0000 (27개)

```text
0e43ee 0e4988 0e4998 0e4a66 0e4b1a 0e4b3c 0e5834 0e5c0cC 0e5ce2 0e5e00C 0e6932 0e77dc
0e78c0 0e7910C 0e7a14 0ea8f6C 0ea9f8 0eaa34C 0eab30C 0ee77a 0eeaf8 0eeb02C 0ef296 0ef692
0ef7b0C 0ef9aa 0efda4C
```

## ff25485 시점 trace와 구현 재사용 경계

- `artifacts/stage_activation_static.json` / `stage_activation_remaining_static.json`은 instructions 목록을 가진 정적 자료다. 이를 실제 callback 실행 trace라고 부르지 않는다. 기존 `stage-activation-api-inventory.md` 및 `activation-animation-resource-spans.md`는47d1a/47f04와 setup의 정적 근거를 제공한다. 오래된 문서의 “부분 animation API만 있음”은 그 작성시점 상태이며 현재 machine을 부정하는 근거로 재사용하지 않는다.
- 현재 shared-stack native10 trace파일 중9개가49fc6를 포함하며, extended121 trace파일 중85개가49fc6를 포함한다. 나머지는 같은CPU의 대기 재개 단계다. 두 자료 모두47d1a/47f04 PC는0건이다. 즉 원본 whole49fc6 entry→caller sentinel 반환/대기 증거는 있지만 이 stage callback에서 실제 JSR한 증거로 바꾸어 주장하지 않는다. 기존 observation/trace는 읽기만 했다.
- `run_animation_machine` (`animation_machine.h/.cpp`)은16register/A7/PC, live sharedRAM stack, PVC/bank, external read, wait/return을 제공한다. caller가 return LONG을 이미 RAM[A7]에 제공하고 stop PC를 명시한다. 따라서47d1a/47f04의 callee 경계까지만 실행하려면 실제 return47d20/47f0a를 사용하고 caller가 JSR push를 책임져야 한다. machine은 이 두 caller PC나initializer49f8c를 dispatch하지 않으며 일반CCR/carry도 state에 없다. 기존 sentinel을 stage return이라고 바꾸는 것만으로 전체caller 구현이 되지는 않는다.
- `execute_stage_activation_helper(...entry49f8c...)`는15register/RAM/두PVCWORD output과 actual A5=108000 TRAP조건을 제공하므로 initializer 의미 재사용 후보이다. 그러나A7/JSR/RTS stack 및 devicePVC side effects를 통합하지 않고 carrybool도 이entry에서는 보존한다. machine과 결합할 때 adapter가 stack/ordereddeviceeffects를 명시해야 한다. 현재 자동연결 구현은 없다.
- `initialize_stage_activation_prefix`는47c04부터 **47c6c 직전**까지만 구현한다. `step_stage_entry_body`는47a94 initialization+480bc tail이며47af0 callback execution을 제외한다. 둘을47d1a/47f04가 이미 실행되는 API로 오인하면 안 된다.
- `execute_stage_readiness`는4847c 전체 chain의15register/carry와 conditionalRAM accesses를 제공한다.47d3e 직후BCC에는 이 API가 재사용 가능하다. 다만 이 API 역시 actualA7/stack/CCR전체를 제공하지 않으며 아직47c6c caller와 연결하지 않았다.

확정 사실은 두 stage continuation의 carry 비소비와 위 rawencoding/지역명령/현재API범위다. 전체1622후보의 code 판정, 각caller의 상위 binding·stage/object 자연 도달성, indirect calls, animation carry가 필요한 caller의 machine 확장 방식, initializer/caller 실제stack 통합은 미확인이다. 복잡한 caller 분기·CCR 설계는 메인 판단 대상으로 반환한다. 이 목록은 전체목표나모든caller복원의 완료 선언이 아니다.

## 재현 및 입력 pin

조사는 `.venv/bin/python`에서 `sys.path.insert(0,'tools')` 후 `load_verified_program(Path.cwd())`를 호출하고, 위에 명시한 opcode/displacement 식으로 짝수offset을 순회했다. 관련 지역bytes는 `disassemble_range(program,start,end-start,start)`로 대조했다. 조사중 `/tmp/ms5-animation-caller-scan.json`에후보와 bounded decode를 기록했다(공식 runtime format이나검증보고서가아님). 새도구/원본실행/build는추가하지않았다.

| 입력 | ff25485 조사 시점 SHA256 |
| --- | --- |
| `tools/disassemble_program.py` | `ea320976f41d937cdbe3dcabbe350c260ab82ec79abc5e2ed80bf325dc4204de` |
| `tools/inspect_activation_animation_scripts.py` | `78e8951512f3bf1af19d5a5caa759b444c4b4c9e85e15b56bd29570e3e6b755f` |
| `tools/trace_animation_references.py` | `361c821bbfe7f4fb239197d300c8f48d768bf7ebe3624641b2aecbc65af2f000` |
| `tools/observe_animation_shared_stack.py` | `3965fe15ec0852a454ed2005a3f0fd88bab34567d780336e5bfd1c44201af371` |
| `tools/observe_animation_machine_extended.py` | `336d4637f95cea6bcbf75d98627953ee51f2a52da4a641ea3db943f3433d2d36` |
| `engine/include/ms5/animation_machine.h` | `d291ceb34dc12fff843e6619846d6a1856f57718d3e80158a5b4ecea9abd00f8` |
| `engine/src/animation_machine.cpp` | `caaab5b639be0d1698b92a78e1d4613513bbc37142d4a20bbb4ce4703754bed1` |
| `engine/include/ms5/stage_activation_helpers.h` | `7c735c34044173dc1e7f7e9eaffc12b8c4c0fc2969b3f999686122e03781a97b` |
| `engine/include/ms5/stage_activation_prefix.h` | `81f22a14a0fab65c512035ebc4094d434221b4b08083772178e8b302ef604b74` |
| `engine/include/ms5/stage_entry_body.h` | `c85331e6bed4e140b419cead2e9db6190cc37b0d0e2f89c797283d93c70045de` |
| `engine/include/ms5/stage_readiness.h` | `9f4fcf6c482ee4cd78b26951b9282933cfe4587871027e71d9c495cbba7ec1e3` |
| `artifacts/animation_shared_stack_native/observation.json` | `43a6627828fa9047ba1b3a89becc0731c1f19e38aa2f1f2dd8f4f9e098cb94cc` |
| `artifacts/animation_machine_extended_native/observation.json` | `5ca26b65cb413860fab9fb5b488023665f2a5ec7dd27a729d6e71734c7262029` |
