# Contributing to open-tabletop-gm

Thanks for your interest in contributing — pull requests are welcome. A few practical notes below.

## License of contributions

By submitting a pull request, you agree that your contribution is licensed under the [GNU Affero General Public License v3.0 or later](LICENSE), the same license as the rest of the project.

You retain copyright on your own contributions. AGPL-3.0-or-later applies forward from your contribution onward; the combined work remains licensed under AGPL-3.0-or-later.

## What's most useful to contribute

- **New system modules** under `systems/<system>/` — see [SYSTEM-PORTING.md](SYSTEM-PORTING.md) for the contract and conventions. New game-system support is the highest-value contribution to this project
- **Bug fixes** on routing, display companion, scripts, or LLM-probe tooling
- **LLM probe results** for models not currently covered in [docs/LLM-GUIDE.md](docs/LLM-GUIDE.md) — especially local / open-weight models on common hardware tiers
- **Local-model compatibility improvements** — anything that helps smaller / local models work better with the agent loop

## Process

1. For new system modules, open an issue first to discuss scope and the system's specifics before implementation
2. Bug fixes and small improvements can go straight to a PR
3. Write a clear PR description that covers the *why* and a brief note about what you tested
4. There's no CI; the maintainer reviews PRs manually
5. The maintainer may apply minor hardening on top of merged PRs — these land as separate follow-up commits in the same release, never as edits to your work

## Questions

Open an issue or comment on an existing PR. The maintainer reads everything.
