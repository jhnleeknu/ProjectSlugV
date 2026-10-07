# 장면 맵 사각형 전송 183c6 분석

원본 decrypted 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 코드 주소는 고정 첫1MiB CPU 주소=ROM offset이다. 근거는 `artifacts/scene_paths/disassembly.json`의183c6..185fa 창과 실제 원본 bytes다. 메인이 명령 순서를 직접 해석했다. 원본 실행 관찰 및 C++ 대조는 별도 결과로 기록한다.

## 입력과 clipping

A0는 RAM node, A1은12byte descriptor다. Descriptor +0/+2는 primary/secondary selector, +4/+6은 width/height이다. D0/D1은 source column/row, D2/D3은 전송 column/row count, D4/D5는 목적지 좌표의 WORD다. A5=108000을 전제로 bank shadow는 RAM100010이다. D0..D7와A2/A3/A4 scratch까지 결과를 보존해야 한다.

183c6..183f0은 x축,183f0..1841a는 y축을 자른다. 단순 signed rectangle 교집합으로 치환하지 않는다. 아래 연산은 WORD wrap이며 별도 설명 없으면 register 상위 WORD를 유지한다.

1. D7=descriptor dimension, count-=1, D7+=count, coordinate+=count.
2. unsigned coordinate>=D7이면185f4에서 CARRY만0으로 만들고 복귀한다. 앞에서 변경한 register는 남는다.
3. D7-=count; coordinate-=count. 두 번째 subtraction에 borrow가 있으면 x축은 destination-=coordinate, y축은 destination+=coordinate를 수행한다. 양쪽 모두 count+=coordinate 후 coordinate는 MOVEQ로 전체32bit0이 된다.
4. count+=1; D7-=coordinate; D7-=count. 마지막 subtraction에 borrow가 있으면 count+=D7.

통과하면 D4.low&=31, D5.low=(~D5.low)&31. D0..D5를 MOVEM.W로 저장하며18530에서 각각 sign-extended32bit로 복원한다. 특히 원래 high WORD 보존이 아니다. Early reject에는 이 복원이 없다. Count0과 비정상 dimension도 이 원본 연산 경로와 구분해야 한다.

## Primary 영상 쓰기

RAM100010=1, word port2ffff2=2000, word port2ffff0=0 순서로 bank3을 선택한다. 이때 CPU200000..2fffef=물리ROM300000..3fffef이며 PVC tail은 데이터로 읽지 않는다. CPU200004의 LONG root에서 `sign16((selector<<2)&ffff)` 변위의 LONG map pointer를 읽고4를 더한다. Map header는 이 루틴에서 읽지 않으며 descriptor의 height를 사용한다.

Node+26 WORD가 음수면 primary cell 읽기와 VRAM 쓰기만 건너뛴다. Root/lookup 읽기와 bank 전환은 이미 일어난다. 그렇지 않으면 첫 source cell은 map+4+4*(column*descriptorHeight+row)다. 다음 column으로는 `ADDA.W(height<<2)`를 사용하므로 이 변위는 WORD wrap 후 sign-extension이다.

영상 주소 구성에는 node+3a의64byte column control이 쓰인다. 목적지 column을2배하여 high control byte를 읽고 ASR.B3→ADD.B자기자신→ADD.B목적지row2배→AND.W003e를 수행한다. Slot은(node26+1)*2이며 slot과 목적지column2배를 더한 WORD를 LSL.W5하고 위 row offset을 더한다. 주소WORD를SWAP으로D7상위에 두고 각 source BE16을D7하위에 실어 LONG port3c0000으로 두 번 쓴다. 두 번째 쓰기 전 D7전체에10000을 더한다. Row 증가의 ADD.B/SUB.W 순서와 wrap도 유지한다.

184d2..1852e에는 별도 zero-write 코드가 있지만183c6 진입의 확인된 흐름은 이를 통과하지 않는다. 이 블록을 primary 음수 slot 처리로 잘못 연결하지 않는다. 다른 entry의 도달성은 별도 조사 대상이다.

## Secondary RAM 쓰기

18530 MOVEM.W 복원 후 RAM100010=0,2ffff2=1000,2ffff0=0으로 bank2를 선택한다. CPU와 물리ROM offset은200000..2fffef에서 수치상 같다. Descriptor+2가0이면 secondary 조회를 건너뛴다. 그렇지 않으면 CPU200010의root와같은signed WORD lookup 규칙으로 LONG pointer를 읽는다.

일반 pointer에서는 A2=pointer+sign16((sourceColumn<<2)&ffff). Source row offset은sign16((sourceRow<<2)&ffff)이다. 원래 clipped column count를WORD로2배하며 각 반복에서 다음을 수행한다.

- A4=offset entry 자체의 주소+sign16(BE16(entry))+signed row offset. A2는2bytes 전진한다. 상대 offset의 기준은 table 시작이 아니라 각 entry 주소다.
- Source A4부터 clipped row count개의 LONG을 순차로 읽어 node+80+column ring offset+(row offset&007e)에 쓴다. Row offset은4씩 증가한다.
- 목적지 column ring offset은 초기 D4<<8, 각 column 시작에&1f80, 각 종료에+80이다. Row offset 초기값은D5<<2다.
- Row loop 종료 시D6.low=0이며18598의 ADDA.W D6는0을 더한다. 따라서 원본1개 primary column은2개의 secondary offset entry를 소비한다.

Pointer ffffffff는 sentinel이다. 같은2배 column 수에 LONG0을 쓰지만 row mask는007c다. 일반 경로의007e와 같다고 가정하지 않는다. 이 경로의 존재와 canonical 참조에서 발견되는지는 별도로 기록한다.

마지막으로 bank2 shadow/port 쌍을 다시 쓰고 node+7a byte의bit7을 세운 뒤 CARRY=1로 복귀한다. Selector0이라도 마지막 bank2 port 쌍은 생략되지 않는다. Node/descriptor/column cache가 RAM에서 겹치면 앞선 쓰기 이후 LIVE 읽기 순서를 유지해야 한다.

## 리소스와 범위

Primary는 기존 scene_maps MS5D를 사용한다. Secondary는 알려진 descriptor의 full width/height,source column/row0을 기준으로 offset entry와각cell 읽기 창을 목록화한다. 동일 source span 공유와 overlap을 보존하고, 추출할 때 실제 읽기 창의 union만 기존MS5D kind2로 포장한다. 이 union은 전체 논리 자료의 길이나 전체 게임의 모든 동적 접근을 증명하지 않는다. Secondary 자료를 collision이라고 단정하지 않는다.

현재 전체1a7a8,19e64 handler,일반1a5a4와47a94 이후 자연 실행 연결 및 직접 조작 가능한 스테이지 화면은 미완료다.

## C++ API와 재현

`transfer_scene_map`은64KiB RAM, borrowed FixedDataResource 창 목록, D0..D7/A0..A4의13register 상태를 받아원본183c6의결과와copied bool,순서있는VideoPortWrite목록을반환한다. A5=108000과진입bank2를전제로한다. A0는정렬된RAM주소여야하며개별접근마다범위를검사한다. A1 descriptor는고정ROM이나RAM에서읽는다. 호출자RAM/상태/copied/ports는성공시만게시하며clipping reject는성공/copied=false다. 다른CCR flags와stack bytes는API결과에포함하지않는다.

Bank별source CPU/물리ROM관계를검사하고읽기범위가없거나둘이상겹치거나개별창경계를넘으면오류다. 인접창을자동결합하지않는다. CLI는디렉터리의정렬된 `.ms5d` 파일을기존로더로읽으며manifest JSON을파싱하지않는다. 모든리소스를먼저읽는CLI와필요한주소만조회하는API를구분한다. 동일입출력경로·symlink·hardlink alias를거부한다. API의transaction을파일두개의filesystem-wide atomic publication으로주장하지않는다.

```text
make -j3 all test
.venv/bin/python tools/observe_scene_map_transfer.py
.venv/bin/python tools/verify_scene_map_transfer.py
build/transfer_scene_map D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS extracted/runtime/scene_maps extracted/runtime/scene_secondary
```

Registers는unsigned decimal또는0xhex다. Output RAM은65536bytes,ports는각9bytes(size1+BE32address+BE32value),stdout은13regs/copied/writes JSON이다. 화면실행명령이아니다.

Zero WORD loop count는SUBQ.W/BNE와같이65536반복으로처리한다. 임시보호한계로primary/secondary각1048576cell초과는전체호출오류로되돌린다. 이한계밖의원본실행을지원한다고주장하지않으며전체목표의완료전에해결하거나실제도달조건을확인해야할항목이다.

## 검증 결과

원본492조건:72canonical descriptor×slot0/ffff×highregister2의288개,zero/nonzero secondary대표의경계좌표·1/2/32범위200개,RAMdescriptor10000a가bankshadow100010과겹치는4개다. 복사420/거부72,ordered ports16620건이다. 원본루틴내context reset은없으며각독립호출전에만baseline을복원한다. Fixture입력은자연게임도달상태가아니다.

동일fixture에서전체RAM/13register/copied/모든9byteport trace가C++와일치했다. CLI오류29조건의입력·기존출력파일보존도통과했다. 메인리뷰에서일부negative주소가합법일수있음을발견해실제로범위를넘는주소로수정했다. C++ unit은secondary ffffffff sentinel과late failure rollback,상대offset,bankshadow LIVE height,MOVEM.W sign-extension을별도로다룬다. Sentinel은canonical원본실행관찰에없으므로동등성검증범위밖이다. 다회CLI호출상태승계·자연streaming·전체frame검증도포함하지않는다.

- 원본관찰 SHA256 `242bdc3703c6c57ea771c94439d3c094b83a7c52f62bdbc3a37d2b33204bef56`.
- C++비교 SHA256 `ba687e364602ab08a4074d3aa09f5b17ae8396576132a30c75d5ae99f611acef`.
- C++binary SHA256 `80a3fd5811521e0389ca646fbd9acd3511b2efaa9a4f839a86d284f8dbd64660`.
- 전체make Python162/C++104/경고0. 로그 `artifacts/scene_map_transfer_build_test.log`.

관찰의초기window는bank3이고C++의암시진입bank는2이지만검증descriptor는fixed/RAM이며첫banked읽기전에명시bank3선택이있다. 이fixture의일치를임의진입bank동등성으로확대하지않는다. 현재확인한bank전환은정렬된2MiB/3MiB창이며일반PVC전동작의검증이아니다.

후속 refresh helper를같은번역단위에추가한뒤기존183c6 회귀492/오류29/16620ports를다시통과했다. 원본관찰은동일하고새binary SHA256은 `1250966f33a091e9bd01e64f37329b61df7354d5c6de29c2d7b03f60443088a0`,현재비교report SHA256은 `9ce11ab6a2fe4b75fbeeb91db32c02fad42f94f55bed9e9ae68681d7d1ce0404`다. 위최초구현검증해시와구분한다.
