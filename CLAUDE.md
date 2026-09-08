# Claude Code向け

共通ルールは [AGENTS.md](AGENTS.md)、分担と検証方針は [開発手順](docs/DEVELOPMENT_WORKFLOW.md) を読んでください。

現在の実装指示は [W05：採光条件・日時比較](docs/tasks/W05-daylight.md) です。W04-v3（642aeec）は受入済みです。作業場所は `build/worktrees/visual-twin`、ブランチは `feature/visual-twin-foundation`。着手時HEADをBASEとして記録してください。

GPTが仕様・レビュー、Claude Codeが実装を担当します。完成速度を優先し、検証は仕様の代表的な正常系と簡単な異常系に絞ります。W05は一括で実装し、内部工程ごとのレビュー待ちは不要です。W06には着手しません。
