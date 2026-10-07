# 장면 좌표→경로 시간 조회 리뷰

Baseline `6144449`. 직전goal turn은18placement리소스추출·로더검증을완료한progress다. 메인은19802/18efa/1972a와196de/196ac의원본순서를확인하고구현계약을제공했다. Sol은공유helper/API/CLI/unit,독립원본관찰/비교와기존회귀를분담했다.

## 메인 코드 리뷰

기존선택블록은validate_motion/select_motion으로이동했으며19938의최종cursor게시/interpolation은그대로다. 메인이diff전체를대조했다. 19802는full D0/D1 저장·복원,projection4그룹의WORD/LONG폭과reversefractionborrow를보존한다. Backwardhelper가cursor를먼저게시하는반면forward는외부비교뒤게시하는차이가핵심이다.

Unit은forward→reverse→backward 재계산과backward-only 조기게시를구분하며단순히최종좌표만검사하지않는다. 이전record가없는오류는base/scratch변경후발생하지만호출전체RAM/state를보존한다. 기존선택bound와신규1,048,576외부반복한계는지원범위제약으로명시했다.

CLI는기존12register숫자/RAM/주소alias검사를재사용하고resource생략을허용한다. Nullcursor에서생략은정상,activecursor에서생략은오류다. 명시한파일은null경로라도미리읽는CLI와lazy API의차이를문서화했다.

## 검증·보강

신규원본2,664조건/오류69조건/MMIO0,wholeRAM/12register/RTS/A7+4 일치. Canonical/null1,584와RAMrelocated합성1,080을구분한다. 74sequences290호출중216호출은실제직전CLI출력을승계한다. Backward-only 조기게시569조건을개별callcount로확인했다. Sourcecodepatch/callee대체/호출중contextreset은없다.

메인이observer/verifier를읽고37resource·manifest hash의시작/끝동일성과positive입력RAM불변검사를추가하도록요청했다. 현재fixture/전체개수/순서/endpoint guard와함께최종C++2,664조건을다시실행했다. 원본관찰은동일한완료자료를사용했으며새원본실행으로표현하지않는다.

- Native SHA256 `16327326456cb75c7ff95f5b63ef5f615a73781f80f2befe106918998491b72f`.
- Verification SHA256 `1759ae535202062c79b78cfa9e760d09449dfd14ed3505fdc8e07a679eceebb6`.
- Binary SHA256 `3dd7bc65683296ab71b582ad1416ac35ca621cc5b871eca289d2b1704bce3193`.
- 전체make Python175/C++109/경고0. 기존19938 회귀12,170조건/오류69조건/MMIO0/미복귀0도통과했다. Report SHA256 `ab2460c368136e41266e0cf982f99628c3a5d64b46a83818c22588b22942a2f9`,binary SHA256 `8e2a9567a004d4c48f0e2aff092478e8af40dfc1d542a3de5cc325bb93694c35`.

## 다음 실행

기존placement raw422bytes를소비하는1a470 bounds/28aeallocation/43e08position/inlinecopy,1a414 gate와일반1a5a4가남았다. 본helper복원을전체스테이지진입·자연frame·전체게임완료로간주하지않는다. Goal은active다.
