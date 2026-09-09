# Claude Code向け

AGENTS.md、docs/DEVELOPMENT_WORKFLOW.mdを読んでください。

現在の実装指示は [W07-G1：複数室の共通基盤](docs/tasks/W07-G1-multi-room-foundation.md)（READY）です。W06は3ceda9bまで受入済み。作業場所は `build/worktrees/visual-twin`、ブランチは `feature/visual-twin-foundation`。着手HEADの完全SHAをBASEに固定します。

施主承認済みの順序はゲストG1〜G3→W08-G→自宅H1〜H4→W08-Fです。今回はG1を一括実装し、G2以降には着手しません。内部工程ごとのレビュー待ちは不要です。GPTが仕様/レビュー、Claudeが実装。代表正常系と簡単な異常系を優先し過剰な検証はしません。
