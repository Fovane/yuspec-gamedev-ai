# Public Release Checklist

Use this before pushing `yuspec-gamedev-ai` to GitHub.

## Repository

- [x] Rename repository to `yuspec-gamedev-ai`.
- [x] Keep code under MIT with `LICENSE`.
- [x] Publish selected model weights through Git LFS.
- [x] Keep private/local corpora out of git.
- [x] Confirm public release files do not include private MMORPG project scripts.

## Data

- [x] Review public release datasets for synthetic or permissive-source content.
- [x] Do not publish Epic/Unreal documentation corpora unless terms allow it.
- [x] Do not publish private MMORPG project scripts.
- [x] For GitHub issue benchmarks, keep source repo and issue URLs.

## Models

- [x] Publish selected model weights via Git LFS.
- [x] Add model card to the release.
- [x] Include training-data source list.
- [x] Clearly distinguish Yuspec native weights from Qwen LoRA adapters.

## Product

- [ ] Rate-limit the public endpoint.
- [ ] Log failures without storing private user code by default.
- [x] Add visible disclaimer: answers can be wrong and patches must be tested.
