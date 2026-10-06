# RAM으로 복사·변환되는 코드

## 확인된 변환
고정 ROM 0x1046..0x1065는 ROM 0x1342부터 word를 읽고 ROR.W #3 뒤 RAM 0x100000에 순서대로 쓴다. D0 시작값 0x8ea에 DBRA가 적용되어 총 0x8eb(2283) word, 4566바이트다. 소스 범위는 [0x1342,0x2518), RAM 범위는 [0x100000,0x1011d6)이다.

Python ROR16 변환과 원본 루프를 Unicorn M68000에서 실행한 결과를 전체 비교했고 일치했다. 0x300001 watchdog 쓰기는 메모리로만 수용했으며 장치 동작은 모델링하지 않았다. 0x1066의 JSR 직전에 실행을 멈췄다.

출력 extracted/program/ram100000.decoded.be.bin SHA256:
af7c7aa3f59eb7790ae0710521020c413408759fa8f27b433e0da78e3ca895d8.

```sh
.venv/bin/python tools/extract_ram_code.py
```

artifacts/disassembly/ram100000.json 및 .asm에는 RAM CPU 주소를 붙인다. ROM 오프셋 대응은 source_rom_offset + (CPU address - 0x100000)이며 바이트마다 ROR16 변환 전후 관계가 있다. 이는 원래 ROM을 단순 복사한 코드가 아니다.

## 초기 관찰
변환 결과 0x100000은 A5=0x108000 설정으로 시작한다. 0x100016에서 사운드 명령 주소 0x320000에 3을 쓰고, 0x10003e/0x10005a에서 RAM의 두 레코드에 각각 0x10008c/0x100162 함수 주소를 넣는다. 이 경로의 UI/게임상 역할은 미확인이다.

변환 루프 출력만 검증했다. 변환된 프로그램 자체를 실행하지 않았고, 선형 역어셈블의 모든 바이트가 코드라고 확정하지 않는다. 런타임 C++에 원본 RAM 코드를 실행하는 방식으로 우회 구현하지 않고 의미를 분석할 자료로 보존한다.
