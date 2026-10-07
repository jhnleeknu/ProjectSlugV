# 장면 경로 실행 19e64

Canonical decrypted source SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 코드주소는고정첫1MiB의CPU주소=ROM offset이다. 근거는 `artifacts/scene_paths/disassembly.json`의19e64..1a07a와16ff8..17012 원본창이며메인이직접명령순서를분석했다. 구문목록/리소스추출과handler실행검증을구분한다.

## 실행 상태와 시작

A0는scene node,A1은RAM metadata,A2는명령cursor다. Metadata는+0 LONG cursor,+4/+6 WORD기준좌표,+8/+a WORD추가이동,+c WORD flags를담는다. Flags는OR.W로갱신하는경로와+c의BYTE만BCLR/대입하는경로가함께있다. 따라서+c BYTEbit4는WORD1000에대응하며+c+1의byte를임의로지우면안된다.

19e64는A2=LONG(A1)을읽고0이면즉시복귀한다. 비영이면A1/A2만LONG으로저장하고18656이동분갱신을호출한뒤복원한다. 이후WORD(A2)+를D7.low에읽고음수이면RTS한다. Terminator를소비한A2는다음주소지만metadata cursor를자동전진시키지는않는다. 일반opcode는00..1c의4배수8종이다.

## 좌표·플래그 명령

00은metadata+c BYTE를10으로설정하고두operand WORD를+4/+6에쓴후+8/+a WORD를0으로만든다. +c+1 byte는그대로다. 1c는두WORD를차례로D0.low에읽어metadata+4/+6에ADD.W한다. 18은첫WORD를D0.low에읽어metadata+c에OR.W하고두WORD를+8/+a에쓴다. 세명령모두원시stream은전진하지만metadata cursor는게시하지않는다.

## 04 descriptor 교체

Operand 시작A2는12byte descriptor다. A3=node+2e를읽고nonnull일때만metadata+c BYTEbit1/3을각BCLR한다. 이전bit1이켜졌으면old descriptor width를metadataX에더하고bit3이켜졌으면old height를metadataY에서뺀다. Old descriptor가NULL이면두bit는여기서지우지않는다.

이어서bit0/2를각BCLR하고이전bit가켜져있을때new width를X에서빼거나new height를Y에더한다. Delta+8/+a를각X/Y에더한다. Node7a byte를D7.byte에읽어&e7로wrapbits3/4를비운다. Metadata+c bit5/6을각BCLR하여이전bit에따라nodebits3/4를설정한뒤node7a에쓴다. 읽기/쓰기는원본순서이며각BCLR의판단은지우기전bit다.

D0/D1.low에metadataX/Y를읽고streamA2/metadataA1을저장한다. A1=descriptor,A2=descriptor+8 LONG column pointer로16ff8을호출한다. 16ff8은node2e=A1,node36=A2를먼저쓴뒤D0/D1을각LSL.W4→ASR.W4하여signed12bit로만들고node32/34에쓴다. 상위WORD는유지된다.

그뒤metadataA1을되찾아+c bit4를BCLR한다. 이전bit가1이면1861a전체갱신,0이면18656이동분갱신을호출한다. MetadataA1와저장된descriptor operandA2를복원한뒤A2+=12,metadataLONGcursor=A2로게시하고dispatch를계속한다. Helper scratch D/Aregister와port효과를임의로지우지않는다.

## 조건 명령 08/0c/10/14

첫offsetWORD를D7.low로읽는다. 아래연산은모두WORD wrap이다. 08/14의첫BPL와각최종BPL/BMI는N만검사하며overflow V를참조하는signed관계비교로대체하지않는다. 0c/10은첫차이뒤TST.W가있어BLE가0또는N=1을뜻한다.

| Opcode | 먼저 통과해야 하는 조건 | 이후 D0 계산 | 분기 조건 |
| --- | --- | --- | --- |
| 08 | oldX-currentX의N=1 | currentX+((node32+offset)<<4)-ffa0 | N=0 |
| 0c | oldX-currentX의WORD가signed positive | currentX+((node32+oldWidth+offset)<<4)-01a1 | N=1 |
| 10 | oldY-currentY의WORD가signed positive | currentY+((node34+offset)<<4)-0270 | N=1 |
| 14 | oldY-currentY의N=1 | currentY+((node34-oldHeight+offset)<<4)-0071 | N=0 |

OldX/Y는node1c/20,currentX/Y는node14/18이다. 0c/14에서필요할때A3=node2e를읽어old width/height를참조한다. Early false에는이읽기가없다. D0/D1/D7의highWORD는각MOVE.W/산술로보존한다.

True이면flagsWORD를D0.low로읽어metadata+c에OR.W하고dx/dy WORD를+8/+a에쓴다. 다음LONG을새A2로읽고metadataLONGcursor에도게시한다. False이면첫offsetWORD소비후A2+=10하여다음명령으로가며metadata cursor는그대로다. Branch대상이현재리소스창밖이라도다른제공된창이나RAM으로이어질수있으며해석기가실제로다음읽기범위를검사해야한다.

## 구문·동작 범위

Canonical72경로는00/04와18두개,negative terminator로구성된다. 다른조건opcode와1c의의미는위원본코드에서확인한것이며canonical사용·자연도달을주장하지않는다. 그경로는ROMpatch가아닌합성RAM stream으로별도관찰한다. Runtime은MS5D의원시bytes와원본주소를읽으며PNG나JSON구문목록을실행데이터로대체하지않는다.

전체1a7a8과1afda register승계,일반1a5a4/47a94 이후진입및자연frame/직접플레이화면은아직별도미완료작업이다.

## C++ API와 재현

`configure_scene_map_descriptor`와 `execute_scene_path`는기존13register SceneMapTransferState,64KiB RAM,borrowed FixedDataResource창목록을사용한다. 진입bank2/A5=108000과정렬된A0 RAM주소를전제로각접근범위를검사한다. Metadata와stream은LIVE RAM에서도읽으며고정ROM/은행창은기존주소규칙으로조회한다. Unknown opcode/없는창/잘못된접근은명시API오류다. Negative opcode는정상종료다.

호출전체RAM/register/orderedports는성공시에만게시한다. Initial moved refresh와명령내full/moved refresh의port목록은순서대로이어진다. 복원대상인A1/A2와그외helper scratch를구분한다. Source bytes를직접해석하므로inspection용ScenePath의캐시된명령배열에의존하지않는다.

임시명령실행한계1048576개를넘으면전체호출을오류로되돌린다. 하위column search/cell전송의한계도남아있다. 이한계밖원본실행과fullCCR/stack/자연frame의완전지원은완료로주장하지않는다.

```text
make -j3 all test
.venv/bin/python tools/observe_scene_path_execution.py
.venv/bin/python tools/verify_scene_path_execution.py
build/execute_scene_path ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS extracted/runtime/scene_maps extracted/runtime/scene_secondary
```

ENTRY는0x16ff8 또는0x19e64이다. CLI는unsigned decimal/0xhex숫자,정확65536byte입력RAM을받고기존9byte orderedport레코드와RAM,stdout JSON(entry/13regs/writes)을쓴다. 모든MS5D파일을먼저로딩하며manifest JSON은파싱하지않는다. 입력·출력·resource별path/symlink/hardlink alias는거부한다. API transaction과두출력파일의filesystem-wide atomicity를혼동하지않는다. 이명령은스테이지화면실행기가아니다.


## 최종 원본 비교

원본 2,958조건(19e64 2,888 / 16ff8 70)이 모두 RTS로 복귀했다. C++ CLI의 전체64KiB RAM, 13register, 순서 있는130,388개 port쓰기가 일치했고 오류36조건은 입력과 기존 출력파일을 보존했다. 호출 내부 context reset은 없다.

Canonical218cursor×oldmap유무×2profile×정지/이동 1,744조건, 전체72경로×2profile 144조건, null2, signed12bit설정70, 합성RAM조건분기480, 기타metadata명령6, canonical04의256 highflag×oldmap유무512조건이다. 조건명령은각opcode의true/false를모두관찰했지만canonical자연도달은아니다. 추가512조건은lowflag a5와bit7보존,oldmap null일때bit1/3보존을포함한다.

- 원본관찰 SHA256 `29facad109b2bcac22b1b0a114cac5dc5fa41d317b1e0cd1a1a183c840b082a0`.
- 전체비교 SHA256 `9f4d41d3bd8c55215a56f060f138603e0e972f8c59293715e4db85dd8a8ff687`.
- CLI binary SHA256 `c2d6651bc3c6c25711c813f5d22118f93e1d080a4038c175221b225c82c12420`.

전체 make Python170/C++106/경고0. 기존refresh 회귀1,744조건/오류35/23,636ports도통과했다. 전체CCR·자연frame·CLI다회호출승계·일반scene초기화·실제스테이지화면은이검증의범위밖이다.
