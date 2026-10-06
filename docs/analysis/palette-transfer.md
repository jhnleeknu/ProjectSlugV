# 일반 팔레트 전송 wrapper와 연속 효과 실행

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 원본 고정ROM CPU/파일 entry72fa, 일반전송72fa..8738. RAM주소는100000 기준이다.

7dea word가0이면 일반전송이다.7ded bit7을지우고 이전값이1일때만 staging을전송한다. 이때먼저bank0 선택장치3a000f에쓰고 staging 첫slot 첫word를8000으로AND한다. 즉이첫word는dirty표시만남기고나머지bits를지운다. 이어서기존256블록 dirty upload를실행한다. pending이없으면staging에손대지않는다.

끝에서는watchdog300001에쓰고7dec byte가0이면3a000f(bank0), nonzero이면3a001f(bank1)를선택한다. `transfer_palette_frame`은전체RAM, 논리적인palette0 8192바이트와최종display_bank를반영한다. MMIO쓰기순서와실제표시타이밍·bank1내용은이API계약밖이다.

7dea가nonzero인873a 분기는별도채우기모드다. 이함수는명시적오류와전체입출력보존으로처리하며일반전송으로잘못실행하지않는다.

```
make all test
.venv/bin/python tools/verify_palette_transfer.py
```

원본과C++의54회전송에서RAM·palette0·최종뱅크가일치했다.32개경계fixture는pending0/1/128/255, 표시뱅크0/1, 첫stagingword0/1234/9234/ffff와다양한나머지dirty값을포함한다.

추가로실제MS5P source203/39d/3d3에효과설정→프레임진행→전송을24회연속실행했다.(-4,-4,-4,기간4)와(31,-31,0,기간5) 두시퀀스이며각각한프레임의전송을늦춰pending gate도관찰했다. 각호출뒤전체RAM과palette byte를비교했다. 이는제어된호출일정이며실제IRQ나전체게임루프도달성검증은아니다.

추가단위검사는특수모드에서RAM/palette/bank출력보존, pending없을때첫word보존, pending있을때첫word특별처리와표시뱅크반영을확인한다. 전체기존검사통과.
