"""W08-G ゲスト試用版ランチャー。

既存のCLI（refresh-visual-study.py / launch-unreal-walkthrough.py /
save-study-scenario.py / compare-unreal-studies.py / build-web-data.mjs …）と
UEエディタ機能を、施主がパスやコマンドを毎回入力せずに操作できる薄い入口に
まとめる。状態schema・部屋/面/器具ID・単位・正本の契約は複製せず、既存の
共通関数（refresh_inputs / source_changes / multi_room_state / validate_* …）
をそのまま呼ぶ。

- paths      … ワークツリー基準のパス解決とローカル設定ディレクトリ
- config     … git除外のローカル設定（エンジン/Blender/cache/選択モデル）
- models     … 生成済みguestプロジェクトの検出・検証・登録・現行選択
- furniture  … Three.js書出しfurniture.jsonの読込・差分・検証・正本反映
- scenarios  … 保存済み案の一覧と「現在の保存を案にする」
- update     … 既存refreshを工程表示付きで実行し、成功時のみ現行モデルを切替
- comparison … 仕上げA/Bの記録と共有用コピー
- runner     … 引数配列でのサブプロセス実行とログ取得
- app        … tkinter GUI（既定の入口）
"""
