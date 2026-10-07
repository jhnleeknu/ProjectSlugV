# Scene motion 원시 record 목록

## Source와 resource 검증

Canonical decrypted8MiB 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. Motion resource는first1MiB 고정ROM 주소와같은파일offset이며CPU/ROMmapping을확인한다. RAM에쓰는효과·운동의미는이번목록작업에서해석하지않는다. 주소/type/상수는16진수,개수는10진수다.

`tools/inventory_scene_motion.py`는기존scene script manifest의motion_%06x.ms5d37개를읽는다. MS5Dversion1/kind1/reserved0·정확한header/payload길이·CRC·manifestcontainer/payloadSHA·CPU/ROM주소와canonical rawbytes를모두대조한다. 기존 `motion_span`으로정확한종결span도확인한다. 추출규격·리소스내용·packer는바꾸지않는다.

## 원시 record와 참조

각10-byte일반record는offset0 timeword,offset2 typeword,offset4/6/8의BE16원시word를보존한다. 마지막record는4-byte(timeword/typeffff)이며전체10-byte로늘리지않는다. Field 이름은time/type과word_at_4/6/8만사용한다. Type별운동function·좌표/속도·duration의미는추측하지않는다.

고유37경로에일반record108개·terminal37개가있다. Script command39개가이경로를참조한다. 각path는CPU/ROM/resourceoffset·원시recordhex·hash·terminaltime·script/command주소를기록하며,참조script와연결된stage catalog group/area/record주소도남긴다. 같은script를여러stage record가참조하는조건은39command참조와별도다.

| Type word | 고유경로를각1회센 record 수 |
| --- | ---: |
| 0004 | 9 |
| 0008 | 4 |
| 000c | 1 |
| 0010 | 1 |
| 0014 | 58 |
| 0020 | 3 |
| 0024 | 3 |
| 0040 | 9 |
| 0048 | 1 |
| 0064 | 14 |
| 0080 | 5 |

Script command참조수로가중한별도통계는type0014가60개이며다른type는위와같다. 이것은구문참조빈도이지실제frame실행횟수나자연게임도달빈도가아니다. Packer가검증하는첫recordtype와달리이목록은모든후속recordtype도그대로수집한다.

## 시간값의 원시 단조성

Timeword를unsigned BE16정수로만비교한다. 일반recordtime은0..1590,terminaltime은0001..2001범위다.37경로모두일반time이엄격히증가하며terminal을포함해도nondecreasing이다. 일반record가1개인경로의strict조건은비교쌍이없어참으로분류한다. Report는각인접쌍의increase/equal/decrease와terminal여부를보존한다.

이원시단조성은frameclock·시간단위·wrap·terminalduration·실제interpreter동작을확정하지않는다. Signed해석이나timewordffff 특수효과의일반규칙도추론하지않는다.

## 재생성과 결과

```text
.venv/bin/python tools/inventory_scene_motion.py
```

실행exit0으로37경로/39command참조/108일반record/37terminal과모든MS5D/canonical대조를확인했다. 결과는 `artifacts/scene_motion/inventory.json`이며최종SHA256은 `b899218545a490e533ce5bfebe58a61771830b6f5a004372e19643c58219eac4`다. Report는입력manifestSHA도남겨재생성시snapshot을구분한다. 원본ROM과추출게임데이터를Git에추가하지않는다.

이번완료는원시목록과통계다. Motion type별의미·후속record실행·scene/frame scheduler·자연도달은메인이분석할미완료범위다.


## 명시 원본 명령 창 재생성

같은명령은 `artifacts/scene_motion/disassembly.json`도생성한다. 창은 `[18c06,18efa)`, `[18fd2,192c4)`, `[196ac,19768)`, `[19938,19978)`다. 각창의source/start CPU·ROM/end exclusive/raw SHA와 `disassemble_range` instruction 후보를저장한다. 첫RTS에서멈추지않으며범위를넘는불완전/invalid명령은helper의dc.w로보존한다. Endpoint를전체함수끝이나code/data소유권완료로가정하지않는다.

총644row이며disassembly SHA256은 `55e66de8a6dc4d2889c6a38dafe0e1dab95887fe7e8d4b82aafa8a11597ea7ef`다. 기존inventory SHA는변하지않았다. 이명령목록은native실행·motion의미해석완료가아니며메인의계약검토용원시근거다.
