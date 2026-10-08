# Object sound lookup 47672 리뷰

Baseline `ca809b3`, branch `codex/object-sound-lookup`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, runtime packer/tests를 분담했다. 메인은 원본 의미와 실제 core/unit/CLI/packer를 읽고 원본 비교 도구를 작성했다. 별도 Sol이 core와 검증기를 각각 독립 검토했다.

47672는 ca70의 A0=A5-76a4, source BYTE와 object+7e 비교, 조건부3af8 및 saved A0 복원을 연결한다. sound 대기는 실제 high/low 상태와 saved low BYTE를 그대로 보존한다. 관측된 pending low는55이며 요청명령1ac0의c0로 대체하면 안 된다. 재개는 prefix/외부gate 읽기를 반복하지 않고 실제 sound 완료 후 source BYTE를 다시 읽는다.

source BYTE→object+7e 쓰기 이후 live source WORD를 읽는다. 따라서 source+1 alias와 sound queue의 signed index bbda가 source를 덮는 순서를 보존한다. ADD.B의 signed overflow는 기존lowBYTE40..bf에서 발생하고 결과를80으로 바꾼다. WORD mask00fe 후 실제ROM WORD를 읽어1을 뺀다. 원본WORD0일 때만 D1전체를0으로 만들고 나머지는 상위WORD를 보존한다.

FixedDataResource는 실제 도달한 WORD를 완전히 포함하는 유일한 유효 창을 요구한다. 겹치는 일부창도 모호성으로 거부한다. raw window 시작이홀수여도 실제WORD가정렬되면허용한다. 아직sound에서대기하는단계에는조회리소스를요구하지않는다. 실제sound호출/재개만A5=108000제약을가지며no-sound는실제접근이유효한A5를허용한다. RAM/state/external_reads는전체transaction으로실패시보존한다.

## 실제 리소스 및 검증

- 기존 MS5D v1 kind1에 원본 `[4411e,4421e)`256byte를 포장하고 C++ loader로 읽었다. container288bytes, CRC32 `7344c719`, SHA `b8fb48ea03880f2285abf550e43cae731889b3545e1241b48074dcc05a3e6b7e`.
- payload SHA `eea1eddb352dfc10643395459d1afbd26ad22d1c5d3aa5c0fdf312052e458649`.128개ID는rawWORD위치이며논리적표의전체범위라는주장은하지않는다. 실제추출물은Git에서제외한다.
- `tools/verify_object_sound_lookup.py`:원본277조건/291단계를다시실행하고전체64KiB RAM/15레지스터/continuation/external_reads를actualCLI와비교했다. 모든128개raw주소/277조회가원본과일치한다.
- 6같은CPU 연쇄의14재개는직전실제C++출력에명시된RAM변화와EXTERNAL255만적용한다.14대기단계는리소스없이성공한다. native 기대register를다음C++입력으로주입하지않는다.
- CLI 오류·파일보존163조건. 독립검토에서 두WORD오류fixture가앞선noncanonical sound검사에걸리는것을발견했다. object비교BYTE를source와같게수정하여실제live BYTE쓰기후WORD정렬/끝경계오류에도달하게했다. 마지막outputBYTE범위실패도추가했다. 이것은제품코드오류가아닌검증입력보강이다.
- API합성단위는전체256lowBYTE,zeroD1clear,source/queuealias,high/low/연속wait,poison및늦은rollback,duplicate/partial/overlap창을검증했다. normal/UBSan격리실행통과.
- 전체 `make -j4 all test` exit0:Python205/C++144/경고0. 패커합성테스트9개포함. 로그 `artifacts/object_sound_lookup_build_test.log`.
- Native SHA `42f093ee7d31dbd3e70b986dd7d7edd7fc409eeb543892ff5c3c6d4494e99f5d`.
- Final verification SHA `785bc6249e24f89fc96fa69fabe5365d1cbe2871948a33b07f5e9d58eec2d0b5`. earlier e5d110/612550보고서는fixture/간접header해시보강으로대체했다. 현재입력18개/native및C++산출물1172개를대조했다.

상위callback,49fc6전체animation,자연scheduler/IRQ,직접플레이와전체게임복원은미완료다. 이번결과를전체sound gate/CCR/cycle/물리mirror 검증으로확대하지않는다.
