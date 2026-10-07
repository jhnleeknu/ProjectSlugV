# 장면 배치 스트림의 원시 리소스

원본 decrypted SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 모든본자료의CPU주소는고정첫1MiB이며ROM offset과같다. Scene command0c는operandLONG을RAM10d40e에저장한다. 이pointer의자료는기존script의operand만보존되어있었고pointedbytes는기존41script/199dependency에없었다.

## 레코드 경계의 원본 근거

1a414는A0=RAM10d40e를읽어null이면RTS한다. WORD(A0)가정확ffff일때종료한다. 다른음수WORD를모두종료로취급하지않는다. WORD(A0)와RAM10d418을CMP.W하여unsigned BLS일때1a470을호출한다. 복귀한A0를10d40e에게시하고다음record를반복한다.

| Record offset | 폭 | 현재 확인한 읽기 |
| --- | --- | --- |
| +0 | WORD | phase gate; ffff는2byte terminal |
| +2 | WORD | inline byte count |
| +4/+6 | WORD각1 | position계산에전달하는raw좌표 |
| +8 | LONG | optional pointer; 비영일때첫8bytes를D2/D3로읽음 |
| +c | LONG | 28ae에넘기는allocation callback pointer |
| +10 | count bytes | 새object에WORD단위로복사하는inlinebytes |

1a506은count를D0.word에읽고A0+=16한다. Count0이아니면WORD(A0)+를WORD(A1)+로복사하고D0.word-=2가0이될때종료한다. Skip경로1a51c는LEA16(A0,D0.W)로이동한다. 따라서odd count는copy loop의정상종료를보장하지않으며8000이상의count는signedskip주소와단순양수길이가다르다. 현재decoder는이둘을명시적으로지원하지않는다. Canonical자료에는이조건이없다.

## 목록 결과

원본명령참조18개/고유root18개에서일반record24개,terminal18개를확인했다. Error/shared/overlap후보0이며총422bytes다. dcea8은2records,e6f6c는6records,나머지16root는각1record다. dd7a0 record만inline2bytes이고나머지는0bytes다. Optional pointer는모두0,callbackpointer는24개모두고유하다. Callback을저장하는것과해당코드를실행하는것을구분한다.

도구 `inventory_scene_placements.py`는script manifest의payload를원본과대조한뒤0c 참조를읽는다. Stream별원시header/inline/terminal,주소와hash를기록하며guard밖자료를임의로고치지않는다. Inventory SHA256 `82c39694c35ecd59523f5ae73ed1eaae170915831af7c056e8e8576fc3c203d5`, disassembly SHA256 `0b1b8a849a442fead14e8635b08e128cbefa32405012fefdc979ca7778e6ca1b`.

## 실행 의미의 별도 미완료 범위

1a470은D0/D1.word 좌표를SWAP한뒤19802를통해motion구간과D7을조회한다. 19802는18efa→1972a를호출하고A1과RAMd3b4를비교하여필요하면다시계산한다. 18efa는36type을4묶음으로나눠X/Y 또는역방향X/Y의시간좌표를얻는다. 구간전후이동에서196de가RAMd3b4를바로쓰는반면196ac는그자리에서쓰지않는차이가있어단순한반복문으로동일시하면안된다.

1a488이후는phase와bounds를판단하고1a4da에서28ae allocation을호출한다. Carry를검사하지않고반환A0+2e를position으로사용하며43e08은WORD좌표를16.16으로만들어camera10d38e를parent로저장한다. 그뒤record inlinebytes를position+48(allocated object+76)에복사한다. 아직이전체실행·callback효과·일반1a5a4 완료를주장하지않는다.

## 바이너리·C++ 계약과 검증

기존MS5D v1kind1을사용하며파일은`placement_%06x.ms5d`,ID는`scene-placement:%08x`이다. Manifest는원본hash,CPU/ROM/end,CRC와payload/container SHA,참조명령및record별rawmetadata를보존한다. 현재canonical packer는bounds0만받으며nonzero를추측파일로대체하지않는다.

`decode_scene_placement`/`load_scene_placement`는sourcebytes의소유복사와각record·terminal주소를반환한다. 좌표·pointer는원시값이다. Generic C++decoder는접근불가능/odd pointer도그대로저장하며역참조하지않는다. Canonical packer의bounds0제약과구분한다. 후보결과를성공시에만교체하여실패시기존출력을보존한다.

```text
.venv/bin/python tools/pack_scene_scripts.py
.venv/bin/python tools/inventory_scene_placements.py
.venv/bin/python tools/pack_scene_placements.py
make -j3 all test
.venv/bin/python tools/verify_scene_placement_resources.py
build/inspect_scene_placement extracted/runtime/scene_placements/placement_0d9c0c.ms5d
```

기존canonical 복호화ROM과scene-script 선행자료가필요하다. `runtime-resources`에도scriptpack→placementinventory→placementpack 순서를추가했다. 관련세명령을다시실행해inventory/manifest/binary hash가동일함을확인했다.

18container/24records/18terminal의422bytes를C++JSON으로부터재조립하여원본slice와전수비교했다. 오류CLI26개,별도rawhighgate/opaquepointer 합성양성1개,Python합성5tests가통과했다. 전체make Python175/C++108/경고0. API출력보존은C++unit,CLI입력불변은verifier가검사한다.

- Manifest SHA256 `d958cd6ad42dfa84c6675f20c1e1a3251dab95ea71c184d70c4e2efe4fea3306`.
- Verification SHA256 `5e4c65d7bbdd46daa77a773f0ee0ba0328603174cdf56db92cb64529b9cb0e92`.
- CLI SHA256 `8848bbc7c193223edcac1b6abf54a9cf9b9e20fe42e99f31d98526d5bb78a20a`.

이검증은읽기전용구문/원시리소스검증이며실제placement handler/native실행동등성을포함하지않는다.


### 후속 구현을 위한 연산 폭과 순서

1a474/1a478의MOVE.W는입력D0/D1의상위WORD를보존한뒤SWAP하므로19802에넘기는LONG의하위16bits를임의로0으로만들면안된다. 19802는각18efa/1972a호출전후에D0/D1을LONG으로저장·복원한다. 18efa type00..28은forwardX,2c..54는reverseX,58..70은forwardY,74..8c는reverseY다. 역방향은baseWORD<<16에서입력LONG을SUB.L하여fraction borrow도반영한다.

1a488후D7.word가currentphase이상이면bounds를거치지않고allocation으로간다. 미만이면boundsLONG두개(또는0)를사용해signed BGT/BLT로제외한다. 원본1a4c4는X쪽계산에서도53a6(A5)를빼므로53a2로고치면안된다. 해석이름보다원본접근을우선한다. Allocation거부시에도carry분기없이반환A0의위치영역으로계속가므로거부를record의무효과skip으로대체할수없다.
