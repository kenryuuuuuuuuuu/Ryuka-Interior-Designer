# Claude Code向け

AGENTS.md、docs/DEVELOPMENT_WORKFLOW.mdを読んでください。

2026-09-11：ゲストG1〜G3・W08-Gは受入済みです。施主指示で開発ブランチをmainへ統合し、プロジェクトのトップを日常作業場所にしました。旧 `build/worktrees/visual-twin` はGit worktreeとして解除済みです。再作成しないでください。[日常利用](docs/DAILY_USE.md)、[残課題](docs/BACKLOG.md)、[移行記録](docs/tasks/daily-use-consolidation.md)を参照します。

当面はゲストの家具編集→UE反映→見え方確認と作り込みを優先します。自宅H1〜H4・W08-Fは未着手で、施主の指示なく開始しません。GPTが仕様/レビュー、Claudeが実装という分担を継続し、代表正常系と簡単な異常系で確認します。新しい仕組み変更はブランチで行い、worktreeが必要なら日常版の外に置きます。開始時HEADをBASEとして固定し、保存案・モデル・ローカル設定を消さないでください。
