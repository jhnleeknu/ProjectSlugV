# 장면 이동 구간 선택과 좌표 평가

Baseline `9db7c98`. Canonical 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소와 상수는16진수이며 고정 첫1MiB 코드는 CPU주소=ROMoffset이다. RAM주소는별도다. 메인이 원본 명령을 직접 decode하여 분석한 계약이며 구현·원본비교 최종 결과는 후속 검증 절에 기록한다.

## 진입과 구간 선택

19938은 RAM10d3b4의 cursor를 A1에 읽는다. Null이면 D0/D1을 각각 RAMd3b8/d3ba word를 상위16비트에 둔 값으로 만들고 반환한다. 비영이면1972a로 구간을 선택하고 A1을 RAMd3b4에 저장한 뒤18fd2를 평가한다. D7은 상위16비트가 시간 정수부인32비트 입력이다.

1972a는 D7을 한번 SWAP한 채 반복한다. 현재 정수부에서 record+0을 WORD로 뺀 결과의 N비트가1이면 뒤로 이동한다. 여기서 BPL/BMI는 V를 함께 판단하는 BGE/BLT와 다르다. 따라서 일반적인 signed less 비교로 치환하지 않는다. 시작 time이0이면 D7전체=start<<16으로 잘라 반환한다. 그렇지 않으면196de를 수행하고 다시 비교한다.

현재 시작보다 앞이 아니면 next record time(+a)과 같은 N비트 비교를 한다. 아직 다음 시작보다 앞이면 D7을 다시 SWAP해 반환한다. 다음 시작 이상이고 next type(+c)이 음수면 D7전체=(nexttime<<16)-1로 잘라 반환한다. 그렇지 않으면196ac를 실행해 다음 구간으로 이동한다. 지원 raw span 밖의 이전 구간은 읽을 수 없으며 API 오류다. 잘못된 경로가 만든 비종료는 지원 동작으로 일반화하지 않는다.

196ac는 현재 구간의18caa WORD delta를 RAMd3b8/d3ba에 더하고 A1을10바이트 전진한다. 새 type을D4.low에 읽고 새+6을D0.low에 읽는다. Type<58이면d3ba에, 아니면d3b8에 그word를 더한다. 196de는 현재+6을 같은축에서 먼저 빼고 A1을10바이트 후퇴한다. 이전 구간의18caa delta를 두 기준word에서 뺀 뒤 d3b4에 A1을 저장한다. 모든 기준좌표 연산은16비트 wrap이다.

## 36종 산술

Type은0..8c의4배수이며 index=type/4다. 18c06은 type<58일때 carry를 세우며 그외는 지운다. D4.low에는type이 남는다. 18caa의 주축 delta는 index0..10 및22..28에서 nexttime-starttime, index11..21 및29..35에서 starttime-nexttime이다. Index<22는 주축X, 그외는 주축Y다.

보조축은 주축delta에 다음 순서의 변환을 적용한다. NEG는 shift보다 먼저 수행한다.

| index | 보조축 변환 순서 |
|---|---|
| 0..10 | LSL1, 그대로, ASR1, ASR2, ASR3, 0, NEG→ASR3, NEG→ASR2, NEG→ASR1, NEG, NEG→LSL1 |
| 11..21 | NEG→LSL1, NEG, NEG→ASR1, NEG→ASR2, NEG→ASR3, 0, ASR3, ASR2, ASR1, 그대로, LSL1 |
| 22..28 | 그대로, ASR1, ASR2, 0, NEG→ASR2, NEG→ASR1, NEG |
| 29..35 | NEG, NEG→ASR1, NEG→ASR2, 0, ASR2, ASR1, 그대로 |

18caa는 D0/D1의 lowword만 수정하지만 보조축0은 MOVEQ이므로 해당 레지스터 전체가0이다. WORD NEG/LSL은16비트로 wrap하며 ASR은 sign fill한다. 나머지 상위word를 임의로 지우지 않는다.

18fd2는 같은36종 변환을 LONG으로 계산한다. 정방향 주축delta는 D7-(start<<16), 역방향은 (start<<16)-D7다. 32비트 wrap과 ASR sign fill을 보존한다. 이후192b2는 D0/D1을 SWAP하고 RAMd3b8/d3ba를 WORD로 더한 뒤 다시 SWAP한다. 즉 분수 lowword를 보존하면서 각각의 상위word에 기준좌표를 더한다.

19938의 마지막199962..199974는 D2=word(record+8)<<16으로 만들고18c06으로축을선택한다. Type<58이면D1+=D2를실행하고 **모든 type에서 D0+=D2도 실행**한다. 이를 한축만 더하는 코드로 정리하면 원본과 달라진다. RAMd3bc/d3c0에 결과를 저장하는 것은 이 함수 밖의 caller 책임이다. +4필드는 이번 함수들에서 사용하지 않으며 다른helper의 의미를 추측하지 않는다.

## API와 재생성

`evaluate_scene_motion(ram, path, state, error)`는64KiB RAM과 기존12register `SceneCommandState`를 사용한다. Borrowed `FixedDataResource`는 기존 MS5D kind1 raw10-byte records+4-byte terminal이다. Current cursor가 내부record일수있으므로 리소스시작주소와 같도록 강제하지 않는다. CPU=ROM fixed첫1MiB, 최대65536bytes, 정확terminal과 모든type을 검사한다. Null은 path를 검사하지 않지만 CLI는 파일을 항상 로드한다.

전체 RAM과 state를 candidate에 계산하고 성공시에만 교체한다. 앞쪽span을 벗어나는 후퇴나 malformedresource는 error로 반환한다. 선택반복2N+1회 초과는지원밖순환입력으로거부하며 원본무한실행과같다고주장하지않는다. CCR은공개출력계약에없다. MMIO효과는없다.

```text
make -j3 all test
.venv/bin/python tools/inventory_scene_motion.py
.venv/bin/python tools/verify_scene_motion.py
build/evaluate_scene_motion D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 INPUT_RAM OUTPUT_RAM MOTION_MS5D
```

CLI는12register JSON과64KiB RAM출력을저장한다. 실제경로리소스는 `extracted/runtime/scene_scripts/motion_*.ms5d`이며 기존 `tools/pack_scene_scripts.py`로재생성한다. Host가D7을바꾸는검증입력은자연프레임진행과구분한다.

## 검증 결과

원본 differential12,170조건과오류69조건을통과했다. 실제canonical경로는주소정규화없이비교하고,36type합성은원본ROM을수정하지않도록RAM에경로를배치한다. 합성에서는native106000과C++resource60000의A1/d3b4주소만정규화하고그외RAM/레지스터를비교한다. 이함수의재구성은일반1a5a4연결에필요한부분이며자연프레임진행·화면렌더링이나전체스테이지실행완료를뜻하지않는다.


실제주소비교5,466조건은108record의시작/다음time±1·fraction·highregister 조합5,168,37경로양방향74sequence의실제CLI carry290호출, null8이다. 합성6,704조건은36type·overflow·ASR·fraction6,480과N16방향경계224다. Canonical관찰type11종과합성36종을따로기록한다. Native미복귀/한도초과는0이며 RAM전체·12register·RTS/A7·MMIO0·fixedROM불변을확인했다. 개별합성payloadhex/SHA를보고서에기록하며이는실제게임데이터발견으로취급하지않는다.

최종 `artifacts/scene_motion/verification.json` SHA256 `a9926535334bf76d820277ac25b3da2448e8346599d11f372c4f7fa8755522a9`. Binary SHA256 `13843937cdd4fd721d463d904de0f5ab3ccf552dab77628af423e23a8cffe32a`. 전체make exit0 Python139/C++101/경고0,로그 `artifacts/scene_motion_build_test.log`. C++unit은null,분수/ASR/offset,terminalclip,N-onlyclip,앞뒤승계와candidate변경후span실패rollback을검사한다.

원시목록 `inventory.json` SHA256 `b899218545a490e533ce5bfebe58a61771830b6f5a004372e19643c58219eac4`,명시창 `disassembly.json` SHA256 `55e66de8a6dc4d2889c6a38dafe0e1dab95887fe7e8d4b82aafa8a11597ea7ef`,36entry×3분기표 `dispatch.json` SHA256 `3014408a53b88bcd8b20d0b813667174c43ff9cb71c9bd1c8a081a13331fd406`. 자동decode만으로의미확정을주장하지않으며메인이원본제어흐름·산술과C++코드를대조했다.
