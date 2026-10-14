# 정리·GitHub 이전 기록

## 범위와 기준

사용자가 2026-10-14 명시적으로 artifacts 정리 → 완료된 claude-integration 복사본 정리 → GitHub 게시를 승인했다. 기준 소스는 `20ea8a8`, 인수 기준은 `3d7d11a`, 엔진 기준은 `b8502bf`다. 이번 작업은 엔진 변경이나 전체 Goal 완료가 아니다. 루트 README는 0바이트이며 engine/README.md는 유지한다.

## 검토와 보존

- 내부 작업자 3개를 gpt-6.1-sol / medium으로 운영했다. 산출물 목록·공유 링크 검사, 완료 복사본·과거 근거 검사, 게시 이력·이동성 검사를 분담했다. 메인은 보존 방식, 삭제 범위, 실제 diff와 검증을 검토한다.
- claude-integration HEAD `9682aedb5efa198d71eadd331ef1d6125ed04776`은 기준 소스의 조상이다. 미반영 커밋·대상에만 있는 tracked 경로·tracked 수정은 없었다. 미추적 .venv/extracted는 공유 원본을 가리키는 링크다.
- 90개 등록 worktree와 937개 링크를 no-follow로 확인했으며 대상 복사본으로 들어오는 링크는 없었다. 공유 기본 작업 폴더·ROM·extracted·venv·현재 인수 산출물·다른 작업 복사본은 정리 대상에서 제외했다.
- 과거 0256 명시 근거 40개는 각 당시 pin과 일치한다. 현재 결과로 대체할 수 없으므로 실제 바이트를 보존한다. 현재 0258의 보고서·receipt·log 105개 해시도 원래 manifest와 일치함을 재확인했다. 역사적 pin과 경로는 덮어쓰지 않는다.
- 전체 파일을 각각 tar로 압축하는 첫 시도는 압축률 약81%로 공간 부족이 예상되어 중단했다. 원본 무변경을 확인하고 실패한 임시 출력 4개, 6,317,631,618바이트를 제거했다. 이 수치는 기존 프로젝트 산출물의 순수 절감량이 아니다.

## 보존 형식과 복원

`tools/preserve_evidence_store.py`는 원래 경로·타입·mode·mtime_ns·SHA256·symlink target을 gzip JSONL manifest에 보관하고, 동일 SHA의 파일 내용은 `objects/<sha>` tar member 하나로 보관한다. 복원 시 중복 파일도 독립 파일로 만들므로 한 파일의 수정이 다른 경로의 내용을 바꾸지 않는다. 원본 inode/ctime/atime·소유자·ACL·확장 속성 재현은 목적이 아니다. 도구는 POSIX 파일 descriptor/no-follow 기능을 사용하므로 macOS/Linux 환경에서 사용한다.

전체 원본은 regular 1,011,493개, directory 141개, symlink 513개, logical regular 25,416,756,662바이트다. 고유 내용은 30,730개 / 1,185,136,596바이트다. SHA manifest의 모든 regular file을 읽어 확인했고, 생성 전후 경로·타입·크기·mode·mtime·inode census가 같았다. 원본 JSONL manifest SHA256은 `9cce4e8a9f02cf53cb776ddb3ee88288f1f5cd50ae827a0491b6e25488ddd886`이다.

보존물은 Git 제외 대상이다. 실제 보존 경로는 다음과 같다.

- 압축 파일: `/Users/start/.codex/worktrees/f4-f5-acceptance/metalslug/artifacts/preserved/claude-integration-9682aed.objects.tar.gz` (636637075바이트), SHA256 `4008eefd6f9d27feca8c7a3635675f5a51fc09da77e839c3c1aaa7b21a32313b`
- Companion manifest: `/Users/start/.codex/worktrees/f4-f5-acceptance/metalslug/artifacts/preserved/claude-integration-9682aed.objects.tar.gz.manifest.jsonl.gz` (29546280바이트), SHA256 `9cce4e8a9f02cf53cb776ddb3ee88288f1f5cd50ae827a0491b6e25488ddd886`

처음 생성한 `.files.jsonl.gz`는 companion과 바이트가 같음을 확인하고 중복 사본만 제거했다. 원래 `/Users/start/.codex/worktrees/claude-integration/metalslug/` 뒤의 `artifacts/...` 및 `build/...` 경로는 companion manifest의 `path`와 일대일 대응한다. SHA로 실제 압축 객체에 연결된다.

 `verify --manifest <manifest> --archive <store>`로 모든 고유 내용·크기·추가/누락 객체·gzip CRC를 확인한다. `restore --manifest <manifest> --archive <store> --out <빈 새 폴더>`로 원래 artifacts/build 구조를 복원한다. 출력에는 원래 전체 파일 용량과 복원 중 고유 객체 staging 용량이 필요하다. 링크는 마지막에 원래 target 문자열로 생성하며, 링크가 참조하는 공유 원본은 별도다. 다른 컴퓨터에서 역사적 절대 경로를 그대로 사용할 수 있다고 가정하지 않는다. 실험·재실행은 보존본을 수정하지 말고 복원한 별도 폴더에서 한다.

도구 테스트는 `python3 -m unittest discover -s tools/tests -p test_preserve_evidence_store.py -v`로 9개 통과했다. 메인·독립 리뷰에서 발견한 두 번째 읽기 시 경로 재검증과 tar EOF 뒤 추가 데이터 거절을 보완했다. 독립 재검증 8개도 통과했다. `0260-preservation-independent.md`에 검토 근거를 남겼다. 이 시험은 전체 게임 회귀의 재실행이 아니다.

## 게시 내용 점검

기준 소스에서 도달 가능한 449 commits / 3,982 blobs / 1,964 역사 경로를 점검했다. 이력의 바이너리 payload·금지 데이터 경로·symlink/submodule·50MiB 이상 blob·검색 패턴에 해당하는 비밀정보는 발견하지 않았다. 가장 큰 blob은 792,661바이트다. 패턴 검사는 모든 비밀정보 부재를 증명하지 않으며, 최종 추가 변경도 별도로 검토한다. ROM·추출물·보존 파일은 Git에 넣지 않는다.

.gitignore에 루트 데이터/환경/산출물의 symlink도 제외하는 패턴을 추가했다. CLAUDE.md는 기존 AGENTS/GOAL/WORKFLOW/STATUS로 안내하며 Codex와 Claude 모두 심화 추론과 분산 코딩·검증을 나누고 서브에이전트를 사용하도록 명시한다.

## 실제 실행 결과

보존 검증 완료 후 삭제 직전 전체 source census가 동일함을 다시 확인했다. 대상의 물리 `artifacts`와 `build` 두 루트만 no-follow 방식으로 제거했다. 공유 primary의 artifacts/extracted/.venv는 동일 device/inode로 남았고, 다른 worktree는 삭제하지 않았다. 과거 worktree는 Codex `archive_worktree`로 정리했고 archived_worktree attachment·실제 경로 부재·Git worktree 등록 부재를 확인했다. `codex/claude-integration` 브랜치의 `9682aed`도 유지됐다.

보존 두 파일의 합은 666,183,355바이트다. 원래 logical payload 25,416,756,662바이트를 전부 복원 가능한 형태로 보관했다. 삭제 전후 관측 free는 17,669,640,192 → 44,379,947,008바이트이며, OS·다른 프로세스 영향이 있을 수 있어 정확한 독점 회수량으로 해석하지 않는다. 중복 manifest와 실패한 임시 압축 파일도 제거했다. 현재 인수 결과·최초 실패 자료는 유지했고 0258 report/receipt/log 105개 hash를 정리 후 다시 확인했다.

세부 기록은 `0260-cleanup-manifest.json`이다. GitHub 인증 후 dry-run push가 성공했고 origin은 지정 URL로 설정했다. 이 정리 커밋의 게시 완료 상태는 아래 후속 게시 기록 또는 `docs/STATUS.md`에서 확인한다.

## 새 컴퓨터에서 이어가기

`docs/WORKFLOW.md`의 clone → fetch → 기준 커밋 확인 → pull --ff-only → 독립 작업 브랜치 → 검증·상태 기록 → push 절차를 따른다. GitHub에는 소스와 도구·문서가 전달된다. ROM·런타임 리소스·과거 로컬 검증 근거는 별도 전달 또는 기록된 절차로 재생성해야 한다. 역사 근거를 재생성 결과로 조용히 교체하지 않는다. 기계별 관측기 경로 옵션과 ROM mtime pin 제약도 WORKFLOW에 기록했다.

## GitHub 게시 확인

정리 소스 체크포인트 `7dd25108e6f8d4569521118de11e413b6b27434c`를 origin의 `main`과 `codex/f4-f5-acceptance`에 atomic push했다. 두 원격 ref가 로컬 SHA와 같음을 확인했다. 별도 임시 폴더에서 GitHub main을 새로 clone하여 HEAD·tree 동일, 도달 가능한 450개 commit, root README 0바이트와 `git fsck --full` 성공을 확인한 뒤 임시 clone을 제거했다. 검증 receipt는 `0260-publication-receipt.json`이다. 이 확인 기록 자체는 체크포인트 다음 커밋으로 게시한다. 개발 브랜치 upstream은 `origin/codex/f4-f5-acceptance`다. 빈 저장소의 최초 게시이므로 PR이나 원격 병합을 수행하지 않았다.
