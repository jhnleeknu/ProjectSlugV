# 배치용 WORD 좌표 초기화 리뷰

Baseline `7abf3ce`. 직전 goal turn은19802통합커밋과검증기록을완료한progress다. 이번에는메인이원본43e08과1a414/1a470을직접읽어계약을확정하고sol에구현,독립실행비교,원본목록과기존회귀를분담했다.

## 구현과 메인 검토

`step_scene_node`에43e08을추가했다. SWAP/CLR.W의결과를unsigned32bit leftshift16으로표현하고기존43e22공통prefix와position(false)를사용한다. 최소26byte span, parent쓰기→좌표쓰기→stamp WORD clear→LIVEposition읽기순서를보존한다. 메인이header/core/unit 전체diff를대조했다. 신규unit은43e22와의입력폭차이,전체scratch/history결과,쓰기이후invalidparent의RAM/12register rollback을검사한다.

할당거절주소100e98+2e는유효한성공fixture다. 원본1a470은carry검사없이43e08을실행하므로이주소를거부하면안된다. 메인이verifier담당에게이구분을명확히전달했다.

## 검증 검토

메인은신규verifier전체를읽었다. 원본43e08부터RTS까지callee대체없이연속실행하며standalone호출경계에서만context를복원한다. 정확2020case와순서검사,전체RAM/12register/stack,입력불변,원본fixedROM불변,실행파일hash불변을확인한다. HostXY/parent입력변경을자연프레임으로표현하지않는다. 실제CLI승계20호출중16호출이직전출력을사용한다. 신규2,020/오류72/MMIO0과기존좌표회귀5,248/오류135/MMIO0이각1회완료됐다.

- 신규report SHA256 `69cc9998a64b73427ac99aa46579e4c6032dbce91862391f6accd33b588598b6`.
- 회귀report SHA256 `ca8a3b769e504965d2c2e2ad0f2d531433576cef5861bced5212be35d2ac7066`.
- registerCLI SHA256 `0848f156847974de3ba9622c24c59fe0a6b03ca770251c4a8f0506ef53058a9a`.
- prefixCLI SHA256 `ae63ee760a03336acf18b5016ef06fa2b85f6a0f3d0ac45ec3aad85ebcd7bed4`.

전체make Python175/C++109/경고0. 메인이현재report/binary/inventory hash를다시확인했다. 원본창3개81행은의미분석의근거이며자동decode결과를통합실행검증으로취급하지않는다.

## 남은 작업

1a414 gate와1a470시간/bounds/할당/좌표/payload를단일transaction으로연결하고원본전체호출과비교해야한다. 이어일반1a5a4와47a94진입을연결한다. 현재helper복원을스테이지화면이나전체게임완료로취급하지않으며goal은active다.
