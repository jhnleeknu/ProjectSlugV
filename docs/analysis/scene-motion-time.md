# 좌표에서 장면 경로 시간 조회 19802

Canonical decrypted SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 본코드주소는고정첫1MiB CPU주소=ROMoffset이다. 배치처리1a470이현재좌표와motion경로를대조할때호출하는19802를분석한다. 기존19938의시간→좌표평가와구분한다.

## 진입과 반복 순서

19802는RAM10d3b4를A1에읽는다. Null이면D7=MOVEQ0,19810 RTS이며D0/D1을포함한나머지register와RAM은그대로다. 비영이면19812에서D0와D1을LONG으로stack에저장하고18efa,1972a를차례로호출한다. 그뒤D1/D0를LONG으로복원한다.

19822는현재A1과LIVE RAM10d3b4를비교한다. 같으면19830 RTS한다. 다르면1982a에서A1을RAM10d3b4에쓰고19812로돌아간다. 반복중A1을진입처럼다시load하지않는다. 구간선택전후에무조건cursor를게시하면이비교의의미가바뀐다.

196de backward helper는이전구간으로이동하고base좌표를뺀뒤1970a에서RAM10d3b4=A1을쓴다. 반면196ac forward helper는다음구간/base를갱신하지만이함수안에서cursor를게시하지않는다. 따라서19802의재계산여부는단순히구간index가변했는지만으로정할수없다. 기존원본의비대칭을그대로보존한다.

## 18efa의 네 투영

WORD(A1+2)를D4.low에읽고36종type을4묶음으로dispatch한다. 상위WORD는유지된다. 모든아래산술은원본의WORD/LONG폭으로wrap한다.

| Type | 입력축 | 시간계산 |
| --- | --- | --- |
| 00..28,4간격 | D0 | forwardX |
| 2c..54,4간격 | D0 | reverseX |
| 58..70,4간격 | D1 | forwardY |
| 74..8c,4간격 | D1 | reverseY |

Forward는D7=입력LONG,SWAP D7,SUB.W base,ADD.W recordstart,SWAP D7다. Base는X일때RAM10d3b8,Y일때10d3ba다. 입력fraction을그대로보존한다. Reverse는D7=MOVEQ0,MOVE.W base,SWAP,SUB.L 입력,LONG결과를SWAP,ADD.W recordstart,SWAP이다. Fraction subtraction의borrow가정수부에반영되므로WORD좌표끼리만빼면안된다.

배치caller1a470의선행MOVE.W는D0/D1상위WORD를보존한뒤SWAP하므로19802 입력fraction을임의로0으로고정해서는안된다. 19802는내부selector가D0/D1을scratch로사용하더라도출력D0/D1을입력LONG과같게되돌린다.

## 구간 선택 1972a

기존19938과같은선택루틴이다. D7을처음에SWAP하고WORD차이의N만으로start이전/end이전을검사한다. Signed관계비교N xor V로바꾸지않는다. 이전구간이없으면start<<16으로clamp하고다음구간이terminal이면(end<<16)-1로clamp한다. Backward는현재record+6의offset을base에서먼저빼고이전구간delta를뺀다. Forward는현재구간delta를더한뒤다음record+6의offset을더한다. 원시10byte record와4byte terminal은기존MS5D motion리소스를소비한다.

## 재현 근거와 상태

`tools/inventory_scene_motion_time.py`는18efa..18fd2,196ac..19768,19802..19832 세창140행을보존한다. SHA256 `c3ca8323b73fda3e3b84cac04d76fe945561e4fdcf9d2424c922514444cad49a`. Decode성공만으로실행완료를판정하지않는다.

## C++ 계약과 검증

`resolve_scene_motion_time`는기존SceneCommandState12register와64KiB RAM을사용한다. `evaluate_scene_motion`과resource검사/1972a 선택helper를공유하지만19802의외부cursor비교전에는무조건게시하지않는다. 입력D0/D1은매재계산뒤LONG그대로복원하며RAM·전체state는성공시에만게시한다.

기존선택한계2*record_count+1에더해19802 외부재계산은임시1048576회한계를둔다. 이한계밖실행은명시지원밖오류다. Null cursor는path를검사하지않고A1=0/D7=0을반환한다. CLI에서resource를생략할수있으며nonnull cursor에서생략하면오류다. 명시resource파일을넘긴경우CLI는null cursor라도파일을먼저로드한다.

```text
make -j3 all test
.venv/bin/python tools/inventory_scene_motion_time.py
.venv/bin/python tools/observe_scene_motion_time.py
.venv/bin/python tools/verify_scene_motion_time.py
build/resolve_scene_motion_time D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 INPUT_RAM OUTPUT_RAM [MOTION_MS5D]
```

원본2,664조건의전체RAM/12register/RTS/A7+4를대조했고MMIO는0이다. 주소그대로비교한1,584조건은canonical경계1,292+74carrysequence의290호출+null2다. 별도합성1,080조건은36type×3cursor×10target이며원본RAM106000의자료를C++fixed60000리소스로비교한다. 이경우출력A1과RAMd3b4만주소정규화한다. Canonical에는정규화가없다.

Carry290호출중216호출이직전실제CLI RAM/12register를사용한다. 입력XY변경은명시host fixture이며자연이동시간축이아니다. 원본에서19812 재계산682조건,backward792조건을관찰했고569조건은backwardpublication뒤한번의projection으로끝났다. D0/D1LONG보존을모든조건에assert한다.

CLI오류69조건과resource생략null 양성1조건을추가확인했다. Verifier는현재전체case순서/fixture/개수와endpoint를대조해smoke/잘린자료를거부한다. 37motion파일,scriptmanifest,binary가비교전후동일함과positive입력RAM불변을확인했다. Resource/input검사를추가한뒤C++전체를다시비교했으며원본관찰은이미완료한동일자료를사용했다.

- Native SHA256 `16327326456cb75c7ff95f5b63ef5f615a73781f80f2befe106918998491b72f`.
- Verification SHA256 `1759ae535202062c79b78cfa9e760d09449dfd14ed3505fdc8e07a679eceebb6`.
- CLI SHA256 `3dd7bc65683296ab71b582ad1416ac35ca621cc5b871eca289d2b1704bce3193`.

전체make Python175/C++109/경고0. 기존19938 회귀12,170조건/오류69조건/MMIO0/미복귀0도통과했다. Report SHA256 `ab2460c368136e41266e0cf982f99628c3a5d64b46a83818c22588b22942a2f9`,binary SHA256 `8e2a9567a004d4c48f0e2aff092478e8af40dfc1d542a3de5cc325bb93694c35`. 일반1a414 placement실행과1a5a4초기화·자연frame/게임화면은별도미완료범위다.
