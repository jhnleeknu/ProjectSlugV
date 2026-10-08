# Stage spatial frame 4701e 구현과 검증

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 명령은 fixed 첫1MiB CPU=ROM offset. RAM CPU100000..10ffff,A5=108000. 메인이4701e..4706c와46f52..4701e를 직접 읽었다. 아래 범위의 구현과 원본 실행 비교를 완료했다. spatial은 편의 이름이며 모든 소비자의 의미를 확정하지 않았다.

## 4701e

A0=10d646,D0=0. LONG(A0)+를9회0으로 써 d646..d669를 지운다. WORDd67c=7;A0=10d61a. 각 반복에서 D0.low=WORD(A0+2a); 비영이면 lowWORD에서1빼고 같은위치에쓴후43e38을호출한다(기존 step_scene_node 재사용 후보, A3 보존 필요). 이후 WORD(A0+26)의 부호bit가0일때46f52를호출한다. A0-=2c; WORDd67c를1줄이고 borrow가없으면반복한다. 카운터를 별도로 바꾸지 않는 경로는8개node이며 마지막카운터ffff. 함수진입A6와A3는직접바꾸지않는다. 비트 쓰기가 loop RAM카운터를 바꾸는 경우도 live값을 사용한다.

## 46f52

A1=LONG(A0+26); D0.low=WORD(A0+1c),D1.low=WORD(A0+20),D2.low=WORD(A0+14),D3.low=WORD(A0+18). signed D0.low>D2.low이면 EXG LONG D0/D2, signed D1.low>D3.low이면 EXG LONG D1/D3. 상위WORD까지교환한다.

MOVEM.W(A1)+,D4-D7은4WORD를 각각32bit signextend하고A1을8증가시킨다. D7.low+=1; D4..7 lowWORD를각각3bit왼쪽shift. D6.low+=D4.low,D7.low+=D5.low. D0.low+=D4.low,D1.low+=D5.low,D2.low+=D6.low,D3.low+=D7.low.

D7.low=WORDd67c; D6 LONG=0; D6.byte=BYTE(A1); ROL.B D6,2;D6.byte&=3; D6.low-=3. borrow없으면category쓰기를skip. borrow있으면NOT.W D6; A1=10d669;BSET.B D7,-(A1); DBRA D6 반복. 입력byte상위2bit가0/1/2/3이면 각각3/2/1/0byte(d668부터역방향)에bit(D7&7)를설정한다. NativeD6의highWORD는0이며최종low값도비교해야한다.

D4.low=ffa0(-96),D5.low=1ff(511). signed D0.low>511이면반환. D2.low-=D4.low 뒤 BLT면반환. D0.low-=D4.low 뒤 BGE가아니면D0 LONG=0. **46fcc는D2가아닌D1과D5를비교**하고signedD1.low>511이면D1.low=D5.low로쓴다. 원본의이피연산자를임의수정하지않는다.

D4.low=80(128),D5.low=1ff. signedD1.low>511이면반환. D3.low-=D4.low 뒤BLT면반환. D1.low-=D4.low 뒤BGE가아니면D1 LONG=0. signedD3.low>511이면D3.low=D5.low.

SUB뒤BLT/BGE는N xor V에따른조건이다. 단순히wrap된결과의부호만검사하면overflow경계에서틀린다. 입력signedoperand비교로조건을재현하되결과WORD는wrap해서남긴다.

D0.low>>=5;D2.low>>=5;D2.low-=D0.low. D1.low>>=5;D3.low>>=5;D3.low-=D1.low. A1=10d646+signextend(D0.low); BSET.B D7,(A1)+; DBRA D2 반복. A1=10d656+signextend(D1.low); BSET.B D7,(A1)+; DBRA D3 반복. DBRA는lowWORD감소/ffff종료이고highWORD보존. 연산순서와실제read/write범위를유지할필요가있다. 큰 범위에서도 실제 RAM 접근을 수행하고 범위를 벗어나면 전체 호출을 되돌린다.

## 원본 확인 항목

- 43e38 전체 반환register adapter와A0/A3보존을 검증했다.
- 기존 MS5D의 원본 검증된9byte probe를 fixed/bank2/bank3에서 소비했다.
- 전체4701e 및 직접46f52 경계/overflow/비트필드/DBRA상태를 whole-original로 비교했다.
- 범위검사나 데이터분류를추정으로엔진에추가하지않는다. 이 단위는 자연스테이지의 콜리전 전체 완료 증거가 아니다.


## 확정 API·루프 지원 계약

`step_stage_spatial_frame(ram,entry,windows,SceneMapTransferState&,bank,error)`는4701e/46f52를 지원한다. A6는사용하지않으므로CLI만입력/출력보존한다. bank2/3는fixed/matchingbank MS5D읽기에사용하고본함수는전환하지않는다. CLI는ENTRY D0..D7 A0..A4 A6 BANK INPUT_RAM OUTPUT_RAM [MS5D_OR_DIRECTORY...]와JSON13regs+a6+bank를사용한다.

원본loop를8회로하드코딩하지않는다. 4701e의SUBQ.W RAMd67c는그시점의liveWORD에서1을뺀다. 이전값0일때borrow로종료한다. 46f52의범위밖논리index가RAM내다른주소(카운터포함)를바꿀수있으므로순차접근그대로구현한다. A0는매번2c감소하며43e38/46f52가A0를보존하므로RAM접근범위를벗어나면실패하고전체호출을되돌린다. 임의반복횟수제한이나논리16bin제한은추가하지않는다. DBRA는원본lowWORD감소/ffff종료로실행한다.

모든read/write는실제align/CPU주소/전체RAM또는MS5Dspan을검사한다. category와bin은BYTE BSET이므로대상read후bit설정해write한다. 지원주소폭은현재다른API와같이24bit이하이며CPU상위byte주소alias는지원하지않는다. 실패는RAM·13register모두보존한다.

43e38은기존step_scene_node에12register를명시적으로복사/반환하고A3를보존한다. Fullframe은timer가비영일때만helper호출하고0일때좌표함수를임의호출하지않는다. 초기9LONGclear와그후timer/node순서를유지한다. 46f52직접entry는타이머/초기clear를하지않는다.

리소스probe는9byte(4WORD+categoryBYTE)가필요하다. 기존458개MS5D중source검증한fixed/bank2/bank3각1개를재사용한다. 실제source바이트와주소를목록도구에서기록하되자연적인논리record나사용성으로분류하지않는다.


## 재현과 증거

```sh
make -j2 all test
.venv/bin/python tools/inventory_stage_spatial_frame.py
.venv/bin/python tools/verify_stage_spatial_frame.py
```

원본429조건의 전체64KiB RAM·14register·bank가 실제CLI와 일치했다. 427조건은 pinned Musashi, banked source2조건은 immutable 실제bank mapping을 사용하는 Unicorn2.1.4다. 이전에 검증한 region Observer의 CPU/메모리 hook만 재사용한다. 원본 진입부터 RTS까지 callee를 바꾸지 않고 실행하며 별도 API carry는 비교에서 제외한다. 실행중 SR을 읽지 않는다.

20개 조건/DBRA 분기 중19개는 양쪽을 관측했다. 46fde는 앞선46fcc..46fd2가D1을511이하로 제한하여 참쪽으로 갈 수 없다. 부호 있는 SUB의 overflow, 전체LONG EXG, MOVEM.W sign extension,category 상위2bit,두bin DBRA,43e38 parent/stamp 경로를 비교했다. Native RAM쓰기10,626건을 초기RAM에서 순서대로 재생해 모든snapshot과도 일치한다.

원본 그대로의 넓은X범위를 계산해 논리16bin밖 RAM을 쓰는 경우를 포함한다. 별도의 인위적 fullframe 조건에서는 마지막8번째node의 쓰기가 d67c 카운터를0101로 바꾸고 추가257개 skip-node를 처리하여 총265회 반복한다. 실제원본과C++의PC호출횟수/최종A0/counterffff가 일치한다. 이는 자연적인 게임데이터 사용을 주장하는 fixture가 아니다.

네 번의 전체frame 호출 중3회는 호스트 RAM/register 변경 없이 이전 실제CLI 출력을 소비한다. CLI 오류8조건(잘못된entry/bank/source 및각rawprobe의누락category), 직접API 단위검증5오류조건과 signedoverflow 성공조건도 통과했다. 늦은 실패는 초기clear와앞선bitmap쓰기까지 되돌린다. 입력검증 오류의파일보존과API원자성을검증했으며파일저장중I/O실패원자성을보장하지않는다.

Fixed/bank2/bank3 각9byte probe와각directory loader를검증했다. 정확한파일/CPU주소/ROMoffset/rawbytes는 inventory의resource_read_fixtures에기록했다. 별도리소스를생성하지않았다. 분기와후속실행이읽는원본데이터를loader로소비했지만논리record경계/자연사용여부는여전히미확인이다.

전체make Python182/C++127/경고0. CLI SHA256 `125378e29e8f4796b2f302cc600b21ed7d17dbe620a07e29e9fb514c2768f726`.
Verification SHA256 `d715be1cfffdc1367dc16054807825a6d21170b9fddadef5ac0210f29230bb48`.
Inventory SHA256 `f3ddcdc81f73553b722d83e2dd807563f983971506a47a9adebbd7707da7ac9d`.

리뷰0186을따른다. 전체CCR/IRQ timing/자연scheduler/전체480bc/직접플레이는후속이며전체goal은active다.
