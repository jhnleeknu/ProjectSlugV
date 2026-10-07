# 인터럽트의 저장 작업 프레임 복구

원본 복호화 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
고정 CPU 주소와 ROM 오프셋은 같다. `restore_interrupt_task`는ce2에서시작해d28의RTS가작업으로넘어간직후, 또는빈큐의d36첫명령전에멈추는상태전이를표현한다. 작업본문을실행하지않는다.

## 프레임 형식과 순서

입력A5는108000이다. RAM10081c의long을A6에읽고unsigned로10081c이상이면빈큐경계d36으로넘긴다. 이때A6외레지스터와RAM은보존하고하드웨어/스택쓰기가없다.

작업이있으면입력D0의하위byte를300001에쓰고 RAM0010.word를0으로만든뒤 PVC2ffff2.word=1000/2ffff0.word=0을쓴다. 그다음프레임에서D0..D7/A0..A5의14개long을순서대로읽는다. 프레임+56은저장A6,+60은작업진입PC이며전체길이는64바이트다.

MOVEM후A6를프레임+64로만든뒤 **복원된A5-77e4** 위치에그값을쓴다. 아직A5를108000으로되돌리기전이다. 그후외부스택에복귀주소d2a를push하고프레임+60에서읽은PC를push하며프레임+56에서A6를읽는다. A5를108000으로만든뒤RTS로PC를소비한다. 최종A7은입력A7-4이고스택상단은d2a다. PC를push했던입력A7-8의메모리값도남는다.

큐포인터쓰기가저장A6/PC와겹치면새로쓴값을후속읽기에서보게된다. RAM0010과프레임이겹치는지원입력에서는bankword초기화가MOVEM보다앞선다. 이읽기/쓰기순서를구조체일괄복사나선행PC캡처로바꾸지않는다.

## API 경계

`InterruptRegisters`는D0..D7/A0..A7 전체32비트를보관한다. `InterruptTaskResult`는다음PC/복구여부와외부스택두long쓰기의주소·값을반환한다. 하드웨어쓰기벡터는watchdog/PVC만포함한다. 외부스택쓰기와최종A7을반영하는것은호출자의책임이다.

지원입력은64KiB RAM, 입력A5=108000, 작업이있을때100000..1007dc의word정렬프레임이다. 원본c64가생성하는32개정규프레임은10001c..1007dc의64바이트간격이다. 프레임이큐끝을넘거나RAM밖을읽는상태는지원하지않는다. 저장A5의포인터쓰기목적지는word정렬된100000..10fffc여야한다. 외부스택A7은word정렬된110008..fffffc를지원하여스택쓰기가작업RAM과겹치지않게한다. 빈큐는사용하지않는스택을검사하지않는다.

오류는RAM/레지스터/결과/포트목록을보존한다. CCR/SR은아직표현하지않는다. 작업함수실행,작업이RTS로d2a에돌아온뒤의반복, c64등록과c8c전체스케줄링은후속연결이다.

```sh
build/restore_interrupt_task INPUT_RAM INPUT_REGS OUTPUT_RAM OUTPUT_REGS OUTPUT_PORTS
.venv/bin/python tools/verify_interrupt_task.py
```

REGS파일은검증용으로D0..D7/A0..A7의16개BE32를연결한64바이트다. 게임리소스형식을변경하지않는다.

원본279조건의전체RAM/16개레지스터/포트/실제외부스택쓰기와메모리가일치했다.32개정규프레임과저장A5쓰기목적지가전역포인터/A6/PC/RAM0010인경우,word정렬경계,스택양끝과unsigned빈포인터를포함한다.25개잘못된입력/별칭에서출력을보존했다. 원본ROM은불변이다.

보고서: `artifacts/interrupt_task/verification.json`, SHA256 `1d7b1abce22d3efe70639ad1de9b8745a62ae0debeca56a5132618cf8c4216a6`.
