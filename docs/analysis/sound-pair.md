# 3d58/3d64 사운드 pair producer

원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 CPU 주소 `0x3d58`, `0x3d64`, `0x3d6e`, `0x3aea`, `0x3af6`은 고정 ROM의 파일 오프셋과 같다. RAM 주소는 CPU `0x100000`에 매핑된 64 KiB의 오프셋으로 표기한다. 원본 ROM을 수정하지 않는다.

## 확정된 실행 계약

`enqueue_sound_pair`는 `3d58`의 prefix `0a` 또는 `3d64`의 prefix `0b`를 byte 큐에 먼저 넣고, 입력 D0의 저장한 하위 byte에서 두 번째 명령을 만든다. D0의 상위 24 bit와 전체 D3를 보존한다. D1의 상위 word는 보존하며 byte producer가 계산한 captured next를 하위 word에 반환한다.

첫 명령이 완료되면 저장한 byte에 `20`을 8 bit 폭으로 더한다. 원본 `SCS.B`는 덧셈 carry를 D1의 하위 byte `ff` 또는 `00`으로 만들고, 이어지는 `OR.W D1,D0`가 두 번째 명령을 결정한다. 저장한 byte가 `e0` 이상이면 두 번째 명령은 `ff`다. 그 밖에는 저장한 byte+`20`이다. 이때 첫 producer의 next가 0..127이므로 D1 하위 word의 상위 byte는 0이다.

`SoundPairState`는 entry, next_pc, 전체 D0/D1/D3, phase, saved와 `SoundBytePending`을 담는다. phase0은 최초 진입이며 saved와 byte pending은 모두 기본값이어야 한다. phase1은 prefix 대기, phase2는 두 번째 byte 대기, phase3은 완료다. phase1/2의 PC는 공통 `3aea`이므로 phase를 별도로 승계한다. 재개는 captured tail/next를 사용하며 live tail을 다시 읽어 대체하지 않는다. 첫 대기를 재개한 호출이 첫 명령을 출판한 뒤 곧바로 두 번째 대기에 멈출 수 있다.

완료한 phase3은 saved를 유지하고 byte pending을 모두 기본값으로 지운다. next_pc `3af6`은 마지막 native RTS 명령의 경계 표시다. 실제 caller의 return PC를 실행하거나 복원한 것으로 해석하지 않는다. 완료 상태를 다시 호출하면 오류다.

## API와 오류 보존

RAM은 정확히 65536 byte다. 지원 entry, PC/phase, prefix 또는 saved로부터 결정한 command, waiting 상태, tail 0..127, next wrap, D0.byte와 D1.low의 일치를 검사한다. 잘못된 상태나 큐 head/tail, 메모리 할당 실패는 RAM과 전체 state를 보존한다. 정상 대기 호출은 성공을 반환한다. 이 producer 자체는 MMIO 쓰기나 읽기를 수행하지 않는다. 소비자 IRQ가 큐 head를 움직이는 동작은 별도 interrupt API의 범위다.

## CLI와 재현

```
build/step_sound_pair ENTRY D0 D1 D3 PHASE SAVED COMMAND TAIL NEXT INPUT_RAM OUTPUT_RAM
make -j2 build/step_sound_pair build/sound_pair_test
build/sound_pair_test
.venv/bin/python tools/verify_sound_pair.py
```

CLI는 decimal 또는 `0x` 정수를 엄격히 파싱하며 입력/출력의 canonical path, symlink, hardlink 중복을 거부한다. PC와 byte.waiting은 phase에서 구성한다. JSON은 `entry,next_pc,d0,d1,d3,phase,saved,byte`를 반환하며 byte 객체의 키는 `waiting,command,tail,next`다. API 검증이 끝나기 전에 출력 파일을 열지 않는다.

단위 시험은 두 대기의 반복, 첫 완료 후 두 번째 대기, captured tail 유지, carry `ff`, 링 wrap, 전체 레지스터 폭과 오류 rollback을 검증했다. targeted build와 단위 시험이 통과했고 컴파일 경고가 없었다. 독립 원본 실행 최종 검증은 2180 native boundary, 67 음성 사례와 40 actual CLI carry sequence를 통과했다. 저장한 byte 0..255, 양쪽 entry, wrap, prefix/suffix 대기에서 전체 RAM/D0/D1/D3/pending을 비교했다. Carry 중 32개는 host head/tail 변경을 사용하는 범위 시험이며, 8개는 실제 IRQ consumer만으로 대기를 풀었다. 이 8개를 포함한 IRQ 실행은 28회, 별도 IRQ 포트 쓰기는 48개다. Producer 자체 MMIO 쓰기는 0이고 원본 코드 수정은 없다. 보고서 `artifacts/sound_pair/verification.json` SHA256은 `77798809d958068d210e268b21306a3000b3a84a1d3e3ddc63af02e11e0034eb`다. 전체 빌드는 stage entry 통합 뒤에 별도로 수행할 예정이다.
