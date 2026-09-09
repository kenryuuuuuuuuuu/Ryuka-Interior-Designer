# Claude Code向け

共通ルールは [AGENTS.md](AGENTS.md)、分担と検証方針は [開発手順](docs/DEVELOPMENT_WORKFLOW.md) を読んでください。

現在の実装指示は [W06：電気設備と夜間照明比較](docs/tasks/W06-electrical-lighting.md) です。W05-v2（fcc99c2）は受入済みです。作業場所は `build/worktrees/visual-twin`、ブランチは `feature/visual-twin-foundation`。着手時HEADをBASEとして記録してください。

GPTが仕様・レビュー、Claude Codeが実装を担当します。完成速度を優先し、検証は仕様の代表的な正常系と簡単な異常系に絞ります。W06は一括で実装し、内部工程ごとのレビュー待ちは不要です。W07には着手しません。
