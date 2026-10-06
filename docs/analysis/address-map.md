# 68000 주소·뱅크와 역어셈블 범위

기준은 고정 MAME neogeo.cpp의 banked_vectors_r, 카트리지 설치 및 PVC overlay와 prot_pvc.cpp의 get_bank_base다.

- CPU 0x000000..0x7f: BIOS/카트리지 벡터 선택 상태에 의존한다.
- CPU 0x80..0xfffff: 고정 카트리지 ROM, 같은 영역 오프셋.
- CPU 0x100000..0x10ffff: 작업 RAM(미러 있음), ROM이 아니다.
- CPU 0x200000..0x2fdfff: 명시적 bank_base + (address - 0x200000).
- CPU 0x2fe000..0x2fffff: PVC RAM/protection overlay, ROM으로 읽으면 안 된다.
- BIOS, 팔레트 RAM, 비디오 레지스터 등은 이 ROM resolver의 대상이 아니다.

PVC: bank_base=((word_ff8>>8)|(word_ff9<<8))+0x100000. 계산 후 ff8=(ff8&0xfe00)|0x00a0, ff9&=0x7fff. 수식의 바이트 기준값을 1MiB로 반올림하지 않는다. 홀수 기준값도 수학적 오프셋으로 보존하지만 실제 홀수 뱅크 접근의 CPU/호스트 동작은 아직 실행 검증하지 않았다. 도구는 상태를 추측하거나 ROM 크기로 wrap하지 않는다.

## 역어셈블
Capstone 5.0.6을 .venv에 고정했다. 범위마다 ROM offset과 CPU base를 명시한다. 모든 줄은 자동 해석 후보이며 코드/데이터 확정과 별개다. 뱅크를 모르는 큰 영역을 0부터 선형 CPU 주소로 붙이지 않는다.

Capstone은 잘린 13fc/4ef9/0000 등의 명령을 가짜 aa 피연산자로 표시할 수 있다. 도구는 충분한 패딩으로 필요한 명령 길이를 구하고 실제 요청 바이트 내에 완전히 들어가는 명령만 수용한다. 잘린/해독 불가 word는 undecoded_word로 남긴다. 합성 회귀 테스트로 이 조건을 확인했다.

```sh
make setup-tools
.venv/bin/python tools/disassemble_program.py --offset 0x2aac --length 0x1c --cpu-base 0x2aac --output artifacts/disassembly/object_dispatch.json
```

아직 다른 디스어셈블러와 전체 결과를 교차 검증하거나 게임 실행 trace와 비교하지 않았다.
