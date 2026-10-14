# Migration independent review

Reviewer: gpt-6.1-sol / medium. Read-only review of publication changes against HEAD `20ea8a8`; only this ignored review output and the existing publication audit report are written by reviewer.

## Documents reviewed

`.gitignore`, `CLAUDE.md`, root `README.md`, `docs/WORKFLOW.md`, `docs/reviews/0260-cleanup-github-migration.md`.

- PASS: README exists at 0 bytes. `engine/README.md` preserved.
- PASS: `git check-ignore .venv extracted roms artifacts build` confirms all five root paths ignored, including current symlinks. Specific staging remains required by workflow.
- PASS: CLAUDE.md points to existing project rules and requires delegation without redefining historical acceptance.
- PASS: 0260 distinguishes in-progress cleanup/publication from complete game acceptance, states actual bytes must be preserved and historical pins/paths must not be overwritten. Completion claims and evidence custody must be filled in after execution.
- P2 finding (resolved after review): WORKFLOW says RNG/PVC observers accept `--routing-file` for machine-specific INPUT_TREE. Only `observe_animation_machine_scheduler_rng.py` supports that option. `observe_animation_machine_pvc_banks.py` accepts only `--out`/`--workers`; it reads fixed INPUT_TREE, INPUT_ROUTING, INPUT_BUS and U06 source paths (lines 42-44, 650, 655). Document RNG override separately and mark PVC path portability as an existing limitation/follow-up. Do not change pinned observer source simply to complete publication.
- Recheck: WORKFLOW now correctly separates RNG `--routing-file` from PVC fixed path limitations; `0260-publication-audit.json` records `review_correction` superseding earlier recommendation. No pinned observer source changed.
- Publication remote facts (empty refs/default main/authorization) are supplied by main and not independently network-verified by this reviewer.

## Final staged review

Independent reviewer rechecked 11 staged text files after actual cleanup; staged diff SHA256 `e45fdb627a6d968f589c3668efd6f7459672a5f5ad8ca83d0a73355e5f97dd93` was stable. README was 0 bytes; no data-root files, symlinks or secret-pattern findings. Actual archive and companion bytes/SHA matched the receipts; tool SHA matched the staged code; source initial/final/pre-delete census matched. Removed source directory was absent and its HEAD was an ancestor. No unresolved finding. Main separately verified remote publication and fresh clone in `0260-publication-receipt.json`.

## Evidence store code review (resolved)

Read `tools/preserve_evidence_store.py`; exercised disposable scratch fixture only. Actual evidence source files were not altered or deleted. Latest inspected source before trailing-tar fix: SHA256 `4f9b35d3db87e150117d7dae42efaa9360f16bab97431a69b000cd6c24bdef30` (author was adding manifest path checks concurrently).

- PASS: pack validates each regular-file source, including deduplicated files, against SHA256, size, mode and mtime; checks device/inode/mode/size/mtime/ctime before/after reads; reads via O_NOFOLLOW parent descriptors. Symlink targets and metadata are checked without following.
- PASS: expected unique object names, sizes and content hashes validated; ordinary extra/duplicate objects, symlink members and gzip CRC corruption rejected.
- PASS: restore second archive pass rechecks object naming, membership, size, content and input archive/manifest hashes; regular duplicate-content files receive distinct inodes; source symlink targets are preserved as links after regular files; recorded mode and mtime restored for fixture files/directories/links.
- PASS: duplicate manifest paths, traversal, non-directory ancestors and symlink ancestors rejected by current disk-backed manifest index.
- P2 finding: verify accepts a second tar archive appended after the first tar end marker inside a valid gzip stream. This defeats the exact-member claim (though produced pack archives do not intentionally include this). Current drain verifies gzip CRC but does not reject nonzero trailing tar data. Reported to author and main; verify and restore second pass require equivalent trailing-content checks including tarfile's buffered bytes.
- Fixture: `build/migration/audit-fixture-cs8jifwe/fixture-results.json`: 15 checks, 14 pass, trailing second tar rejection fails before fix.

Deletion eligibility remains main's separate full metadata/census and manifest comparison decision. This code review does not authorize deletion or assert all source entries are present in a user-supplied manifest. It verifies recorded metadata fields (type, mode, mtime_ns, size, link target, payload), not ownership, xattrs, birthtime or ACLs.

### Final independent recheck

Final tool SHA256: `694fff65f25f2cbbaf9a4d12446c7f0405aeb9285d03cb7f597ba914633b14ea`.

Author resolved P2 trailing tar finding with `finish_tar_stream`, called inside both verify and restore's second tar pass; it drains tarfile's internal stream buffer to EOF and rejects every nonzero tail while outer gzip EOF/CRC validation remains. Independent recheck passes 8/8: normal verification, normal restore, trailing second tar rejection in verify and restore, gzip CRC rejection, duplicate/extra/symlink object rejection. Results: `build/migration/audit-fixture-cs8jifwe/final-recheck.json`. Initial failed regression retained as historical review evidence.

No unresolved code-review finding remains within the assigned preservation contract. Actual large evidence-store pack, full source census, deletion eligibility and final publication checks remain main's responsibilities.
