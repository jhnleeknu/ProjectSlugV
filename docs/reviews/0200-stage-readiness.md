# Stage readiness 4847c 리뷰

Baseline `f49e2da`, branch `codex/stage-readiness`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, 원본 비교를 분담했다. 메인이 실제 원본 계약·core·단위·검증 코드를 읽고 현재 보고서와 모든 입력 해시를 확인했다. 별도 Sol도 원본 listing에 대한 core의 독립 리뷰에서 조치가 필요한 문제를 발견하지 않았다.

`execute_stage_readiness`는 원본4847c의 두1bdde 호출,289e marker 검사,조건부4dee2,마지막4e166을 전체15레지스터/carry로 연결한다. 상위 두 MOVEQ가D0전체를초기화하고 각callee가D0.low/A0/A4/조건부D1.byte를남기는순서를보존한다. inactive marker270e,object+a8 bit4,object+61 bit7의우선순위가중요하다. record의signedWORD/type검사가통과할때만D1.byte를읽으며상위24bit를유지한다. status3/4/5와최종flag/mask에따른carry는원본호출자분기에직접사용할수있다.

실제도달한BYTE/WORD/LONG span만검사하며A5를108000으로고정하지않는다. WORD/LONG은2byte정렬이다. 첫player가종료하면두번째object·record·flag를미리읽거나검사하지않는다. 포인터덧셈은signed64중간값으로검사하고24bit mirror를모사하지않는다. RAM은const이며state와carry를임시변수에모아모든실패에서기존값을보존한다. 새리소스/ports/할당이필요없는RAM조회다.

검증기는 readiness 수식을복제하지않는다. 저장된214 native조건을원본CPU에서다시실행해전체RAM/15레지스터/RTS후carry/trace와비교한다. 모든JSR의복귀주소를원본명령길이에서읽고stack push/RTS순서를별도로재구성한다. actual RAM operand reads2,170개와stack writes1,121개,19조건분기양쪽을확인했다. 반환carry는true86/false128이며hook중SR을읽지않는다. 이전10개Musashi교차조건도그대로감사한다.

- `.venv/bin/python tools/verify_stage_readiness.py`:실제CLI214조건의전체64KiB RAM/15레지스터/carry/정확한16key JSON일치. 오류·파일보존120조건과새출력/실제case alias/FIFO검사통과.
- `make -j4 all test`:Python196/C++실행파일141/경고0,exit0. 로그 `artifacts/stage_readiness_build_test.log`. 격리normal/UBSan단위도통과했다.
- Native SHA256 `45ad59018ae534c4059d6348dc835e09d37d9d08dbc3554e2562c7cfe90a4844`.
- Verification SHA256 `36dd7de01cbd422685c75b54ac4885ba88970ffe1581968c85b6dd54bbeacd5f`.
- CLI SHA256 `592cd0a31e95f81aec80afb8e074a0023b5a44d91e272bbff5d4d2e0ebc198cf`.
- 메인이현재inputs9/native_inputs9/native_artifacts644의모든hash를대조했다. 계약의초기미완료안내를실행문서참조로수정한뒤검증기를재실행했으며앞선01054088...보고서는대체됐다.

홀수A5는진입후첫LONG읽기에서거부되므로이entry에서독립적으로도달하는늦은oddWORD오류가있다고주장하지않는다. stage callback전체·다른CCR bits/cycle/물리mirror/자연scheduler/직접플레이는미완료다. 이단위를수용하고다음활성화helper연결을계속한다.

## 후속 작은 helper 원본 관측

메인은4e216/bee/16ed2/49f8c의원본명령과 `observe_stage_activation_helpers.py`를읽었다.441조건(108/108/150/75)의전체RAM/15regs,앞두helper의carry,49f8c의orderedPVC150개를확보했다. 정상조건분기9개양쪽을관측했고49f8c의A5검사는정상반환만관측했다. TRAP처리를검증했다고주장하지않는다.

별도Sol은전체441조건의chronological RAM재생·source/trace/hash를감사하고대표20조건을메모리에서재실행했다. 메인도입력7개/조건별산출물1,764개hash를대조했다. signedWORD양극단,flagoperand alias,animation pointer와bank shadow overlap을포함한다. A6=fffea에서100010을clear한뒤A1 LONG이덮어쓰며포트는앞서기록한두WORD뿐인순서를유지한다. bee의A5fixture는실제0/ffffffff두값이며목록의108001까지실행했다고주장하지않는다.

관측SHA `ed26b6cc85ec93c777f211d1fa1d184eeb965659cbaec281116ed7bb4a28b0cf`. 이증거는native준비이며해당네helper의새C++완료나49fc6전체animation완료가아니다.
