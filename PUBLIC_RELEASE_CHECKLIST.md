# Public Release Checklist

Use this before pushing `yuspec-gamedev-ai` to GitHub.

## Repository

- [ ] Rename repository to `yuspec-gamedev-ai`.
- [ ] Keep code under MIT with `LICENSE`.
- [ ] Keep model weights out of git.
- [ ] Keep private/local corpora out of git.
- [ ] Confirm `git status --ignored` does not show sensitive files as tracked.

## Data

- [ ] Review every public dataset source.
- [ ] Do not publish Epic/Unreal documentation corpora unless terms allow it.
- [ ] Do not publish private MMORPG project scripts.
- [ ] For GitHub issue benchmarks, keep source repo and issue URLs.

## Models

- [ ] Publish model weights separately from source code.
- [ ] Add model card to each weight release.
- [ ] Include training-data source list.
- [ ] Clearly distinguish Yuspec native weights from Qwen LoRA adapters.

## Product

- [ ] Use retrieval for free web usage.
- [ ] Rate-limit the public endpoint.
- [ ] Log failures without storing private user code by default.
- [ ] Add visible disclaimer: answers can be wrong and patches must be tested.
