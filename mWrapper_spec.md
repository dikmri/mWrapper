# mWrapper 仕様書

MMAudio / NSFW_MMaudio を使って動画へ音声を付与する、初心者向けGUIアプリケーションの詳細仕様書。

- アプリ名: **mWrapper**
- 開発言語: **Python**
- GUI: **PySide6**
- 推奨OS: Windows 10/11 64bit
- 想定ユーザー: ComfyUIやPython環境構築に不慣れなユーザー
- 主用途: 合法・同意済みの成人向け動画に対し、MMAudio系モデルで音声を生成して付与する

---

## 1. 背景と目的

### 1.1 背景

MMAudio / NSFW_MMaudio を ComfyUI 経由で利用すると、以下のような課題がある。

- 動画を投げて即生成するまでの操作が多い
- 生成結果を確認し、気に入らなければ即再生成する流れが面倒
- 出力ファイルの命名・保存先管理が弱い
- 初心者にとって ComfyUI、モデル配置、依存関係の理解が難しい
- 成人向け動画の音付けという特定用途に最適化されていない

### 1.2 目的

mWrapper は、MMAudio / NSFW_MMaudio を使った音付け作業を、以下のような単純なワークフローで完結させる。

```text
動画をD&D
  ↓
日本語プロンプト入力
  ↓
英語プロンプトへ翻訳
  ↓
生成
  ↓
その場でプレビュー
  ↓
気に入らなければ再生成
  ↓
気に入ったら保存
```

### 1.3 非目的

v1.0 では以下を目的としない。

- 動画編集ソフトとしての高度なタイムライン編集
- ComfyUIワークフローの完全互換
- モデル学習・ファインチューニング
- 複数モデルの高度な比較UI
- クラウドサービス化
- モデル重みの同梱配布
- 成人向けサンプル素材の同梱

---

## 2. 基本方針

### 2.1 技術方針

- アプリ全体を Python で構築する
- GUI は PySide6 を使う
- MMAudio は Python から直接呼び出す
- 初期実装では MMAudio の CLI 実行をラップしてよい
- 安定後、ライブラリ呼び出しに切り替え可能な構造にする
- モデルや外部バイナリは原則としてアプリに同梱しない
- 初回セットアップウィザードで必要なものを自動導入する

### 2.2 配布方針

- GitHub で公開する
- アプリ本体は MIT License とする
- モデル、MMAudio、PyTorch、PySide6、FFmpeg 等の第三者コンポーネントはそれぞれのライセンスに従う
- リポジトリにはモデル重みや成人向けサンプル素材を含めない
- README と ThirdPartyNotices.md に依存関係とライセンス注意を明記する

### 2.3 ユーザー体験方針

初心者が以下だけ理解すれば使えることを目標にする。

1. アプリを起動する
2. 初回セットアップを実行する
3. 動画をドラッグ&ドロップする
4. 日本語で音の説明を書く
5. 生成ボタンを押す
6. プレビューする
7. 保存する

---

## 3. 参照情報

実装時に参照すべき主要な外部情報。

### 3.1 MMAudio

MMAudio は video and/or text inputs から同期した音声を生成するモデルである。公式READMEでは、CLI例として以下の形式が示されている。

```bash
python demo.py --duration=8 --video=<path to video> --prompt "your prompt"
```

出力は `./output` に `.flac` と `.mp4` として保存される。デフォルトの生成・学習 duration は 8 秒で、極端に長い/短い duration は品質低下の可能性がある。

- 公式リポジトリ: https://github.com/hkchengrex/MMAudio
- Hugging Face Space README: https://huggingface.co/spaces/hkchengrex/MMAudio/blob/b7f72e170fa7b7e2f41bd062d812cee9009a29b5/README.md

### 3.2 NSFW_MMaudio

- Hugging Face: https://huggingface.co/phazei/NSFW_MMaudio
- Hugging Face上の表示ライセンス: MIT
- 注意: モデル重みはアプリに同梱しない。ユーザーが初回セットアップで取得する。

### 3.3 PySide6

PySide6 は Qt for Python の公式バインディング。PyPIから導入可能。

- PyPI: https://pypi.org/project/PySide6/
- Qt for Python: https://doc.qt.io/qtforpython-6/

### 3.4 Hugging Face Hub

モデル取得には `huggingface_hub` を利用する。

- `hf_hub_download()` は単一ファイル取得
- `snapshot_download()` はリポジトリ全体の取得

参照:
- https://huggingface.co/docs/huggingface_hub/en/guides/download

### 3.5 Google Cloud Translation API

日本語プロンプトの英語翻訳には Google Cloud Translation API を利用する。

- Cloud Translation: https://cloud.google.com/translate
- REST API Reference: https://docs.cloud.google.com/translate/docs/reference/rest

### 3.6 PyTorch

GPU利用には PyTorch + CUDA 対応環境が必要。WindowsではGPU、CUDA、ドライバ、PyTorchビルドの組み合わせに注意する。

- https://pytorch.org/get-started/locally/

### 3.7 FFmpeg

動画情報取得、音声mux、再エンコード補助に FFmpeg / ffprobe を使う。

- https://ffmpeg.org/
- https://github.com/ffmpeg/ffmpeg

---

## 4. 対象ユーザー

### 4.1 想定ユーザー

- ComfyUIのノード構成が面倒だと感じているユーザー
- PythonやAIモデルの細かい導入に詳しくないユーザー
- 動画に対して手早くAI音声を付けたいユーザー
- 日本語でプロンプトを書きたいユーザー
- 生成結果を何度も試しながら選びたいユーザー

### 4.2 想定しないユーザー

- 違法・非同意素材を扱うユーザー
- 未成年に関する性的素材を扱うユーザー
- 実在人物への無断性的加工を行うユーザー
- モデル学習や高度な研究用途を主目的とするユーザー

---

## 5. 法務・安全・コンテンツ方針

### 5.1 アプリ内禁止事項

README、初回起動時の利用確認、About画面に以下を明記する。

mWrapper は以下の用途で使用してはならない。

- 未成年を含む、または未成年に見える性的素材
- 非同意、盗撮、リベンジポルノ、流出動画
- 実在人物への無断性的加工
- 違法に取得・配布された素材
- 各国・地域の法律に違反する用途
- 他者の権利・プライバシーを侵害する用途

### 5.2 初回起動時の確認

初回起動時、以下の確認画面を表示する。

```text
mWrapper は、合法かつ同意済みの成人向け素材に対して音声を生成するためのツールです。

以下の用途は禁止されています。
- 未成年または未成年に見える人物を含む性的素材
- 非同意・盗撮・リベンジポルノ・流出素材
- 実在人物への無断性的加工
- 違法素材または権利侵害素材

上記を理解し、合法・同意済みの素材にのみ使用します。
```

同意チェックボックスをオンにしないと次へ進めない。

### 5.3 GitHub公開時の注意

リポジトリには以下を含めない。

- 成人向けサンプル動画
- 成人向けサンプル画像
- 成人向けサンプル音声
- モデル重み
- Google APIキー
- Hugging Face token
- 生成済み成人向けコンテンツ

---

## 6. ライセンス方針

### 6.1 アプリ本体

mWrapper の独自コードは MIT License とする。

`LICENSE` ファイルに標準MITライセンス文を配置する。

### 6.2 依存コンポーネント

`ThirdPartyNotices.md` を作成し、以下を記載する。

| コンポーネント | 用途 | ライセンス/注意 |
|---|---|---|
| MMAudio | 音声生成 | 公式コードはMIT。モデル重みは別ライセンスの可能性あり |
| NSFW_MMaudio | 成人向け音声生成モデル | Hugging Face上はMIT表示。重みは同梱しない |
| PySide6 | GUI | LGPLv3/GPL/商用ライセンス体系 |
| PyTorch | 推論基盤 | PyTorchライセンスに従う |
| huggingface_hub | モデル取得 | Apache-2.0系 |
| Google Cloud Translation API | 翻訳 | Google Cloud利用規約に従う |
| FFmpeg | 動画処理 | LGPL/GPL構成に注意 |
| PyInstaller | exe化 | 生成物の配布は任意ライセンス可。ただし依存ライセンスに従う |

### 6.3 README上のライセンス注意文

READMEに以下の趣旨を記載する。

```text
mWrapper itself is licensed under the MIT License.

This repository does not include MMAudio model weights, NSFW_MMaudio model weights, FFmpeg binaries, or third-party model files. These components are downloaded or configured separately by the user and are governed by their respective licenses.

Users are responsible for ensuring that their use of third-party models and tools complies with all applicable licenses and laws.
```

---

## 7. システム構成

### 7.1 全体構成

```text
mWrapper
  ├─ PySide6 GUI
  │   ├─ MainWindow
  │   ├─ SetupWizard
  │   ├─ SettingsDialog
  │   ├─ PreviewPlayer
  │   └─ JobHistoryView
  │
  ├─ Application Core
  │   ├─ ConfigManager
  │   ├─ JobManager
  │   ├─ PromptManager
  │   ├─ TranslationService
  │   ├─ ModelManager
  │   ├─ VideoService
  │   ├─ MMAudioRunner
  │   └─ OutputManager
  │
  ├─ External Tools
  │   ├─ Python
  │   ├─ PyTorch
  │   ├─ MMAudio
  │   ├─ NSFW_MMaudio
  │   ├─ FFmpeg / ffprobe
  │   └─ Google Cloud Translation API
  │
  └─ User Data
      ├─ config.json
      ├─ models/
      ├─ temp/
      ├─ outputs/
      └─ history.jsonl
```

### 7.2 推奨ディレクトリ構成

```text
mwrapper/
  README.md
  LICENSE
  ThirdPartyNotices.md
  pyproject.toml
  requirements.txt
  scripts/
    setup_dev.ps1
    build_windows.ps1
    clean_temp.py
  mwrapper/
    __init__.py
    main.py
    app.py
    constants.py
    ui/
      main_window.py
      setup_wizard.py
      settings_dialog.py
      preview_player.py
      widgets/
        drop_area.py
        log_view.py
        progress_panel.py
    core/
      config.py
      jobs.py
      history.py
      prompts.py
      paths.py
    services/
      translator.py
      google_translate.py
      model_manager.py
      mmaudio_runner.py
      video_service.py
      output_manager.py
      ffmpeg.py
      safety.py
    workers/
      setup_worker.py
      generate_worker.py
      translate_worker.py
    resources/
      icons/
      styles/
        app.qss
  tests/
    test_config.py
    test_output_naming.py
    test_prompt_translation.py
    test_video_service.py
    test_safety.py
```

---

## 8. 主要画面仕様

## 8.1 初回セットアップウィザード

### 8.1.1 画面一覧

1. ようこそ
2. 利用条件確認
3. 動作環境チェック
4. 保存先フォルダ設定
5. Google翻訳設定
6. モデル設定
7. FFmpeg設定
8. セットアップ実行
9. テスト生成
10. 完了

### 8.1.2 ようこそ画面

表示内容:

- mWrapperの概要
- 初回セットアップで行うこと
- モデル等は外部から取得すること
- 成人・合法・同意済み素材のみ使用可能であること

### 8.1.3 利用条件確認画面

必須チェック:

- 合法かつ同意済みの成人向け素材にのみ使用する
- 未成年または未成年に見える性的素材には使用しない
- 非同意・盗撮・流出・リベンジポルノ素材には使用しない
- 実在人物への無断性的加工には使用しない
- モデル・ツールのライセンスは自分で確認する

### 8.1.4 動作環境チェック画面

チェック項目:

- OS
- Pythonバージョン
- GPU有無
- CUDA利用可否
- PyTorch利用可否
- 空き容量
- インターネット接続
- FFmpeg / ffprobe 有無
- 書き込み可能な作業ディレクトリ

表示形式:

| 項目 | 結果 | 詳細 |
|---|---|---|
| OS | OK/Warning/Error | Windows 11 64bit |
| GPU | OK/Warning/Error | NVIDIA GeForce ... |
| CUDA | OK/Warning/Error | torch.cuda.is_available() |
| FFmpeg | OK/Warning/Error | path/to/ffmpeg.exe |

### 8.1.5 保存先フォルダ設定

設定項目:

- デフォルト保存先フォルダ
- 一時ファイルフォルダ
- モデル保存フォルダ

デフォルト例:

```text
%USERPROFILE%\Videos\mWrapper\outputs
%LOCALAPPDATA%\mWrapper\temp
%LOCALAPPDATA%\mWrapper\models
```

### 8.1.6 Google翻訳設定

設定項目:

- Google翻訳を使う/使わない
- APIキー入力
- テスト翻訳ボタン
- APIキー保存方式

APIキーは平文保存を避ける。最低限、設定ファイルには保存せず、OSの資格情報ストア利用を検討する。

v1.0で難しい場合は以下を採用する。

- config.jsonには保存しない
- 起動時に環境変数 `MWRAPPER_GOOGLE_API_KEY` を読む
- GUIから入力したAPIキーはメモリ上のみ保持
- 将来的にkeyring対応

### 8.1.7 モデル設定

選択肢:

- NSFW_MMaudioを自動ダウンロード
- 既存のモデルパスを指定
- 後で設定する

モデル取得には `huggingface_hub.snapshot_download()` を使用する。

設定項目:

- Hugging Face repo id
- revision
- local_dir
- allow_patterns
- ignore_patterns

初期値例:

```text
repo_id: phazei/NSFW_MMaudio
local_dir: <models_dir>/NSFW_MMaudio
```

注意:

- モデルのファイル構成は実装時に実リポジトリを確認する
- ファイル名を決め打ちしすぎない
- ダウンロード後、必要ファイルが揃っているか検証する

### 8.1.8 FFmpeg設定

選択肢:

- PATH上のffmpegを使用
- ユーザーがffmpeg.exeを指定
- 自動導入
- 後で設定

推奨:

- v1.0ではPATH検出 + 手動指定を優先
- 自動導入はv1.1以降でも可
- FFmpegバイナリを同梱する場合はライセンス表示を厳密に行う

### 8.1.9 セットアップ実行

実行内容:

- 必要ディレクトリ作成
- config.json作成
- モデル取得
- MMAudio取得または配置確認
- 依存パッケージ確認
- FFmpeg確認
- テスト用短時間生成の準備

### 8.1.10 テスト生成

テスト内容:

- 付属の非成人・短尺・無害なテスト動画を使う、またはユーザーに動画選択させる
- 1〜2秒程度で最小生成
- 結果ファイルが生成されるか確認
- プレビュー可能か確認

リポジトリにテスト動画を含める場合は、完全に無害な素材に限定する。

---

## 8.2 メイン画面

### 8.2.1 レイアウト

```text
┌──────────────────────────────────────────────┐
│ mWrapper                                      │
├──────────────────────────────────────────────┤
│ [動画D&Dエリア]                              │
│ ここに動画ファイルをドロップ                  │
├───────────────────────┬──────────────────────┤
│ 入力動画情報           │ プレビュー             │
│ - ファイル名            │ [動画プレイヤー]        │
│ - 長さ                  │                      │
│ - 解像度                │                      │
│ - FPS                   │                      │
│ - 音声有無              │                      │
├───────────────────────┴──────────────────────┤
│ 日本語プロンプト                              │
│ [                                             ]│
│ [翻訳]                                        │
│ 英語プロンプト                                │
│ [                                             ]│
├──────────────────────────────────────────────┤
│ 設定: seed / duration / steps / cfg / model    │
├──────────────────────────────────────────────┤
│ [生成] [再生成] [停止] [保存]                  │
│ 進捗バー / ログ                               │
└──────────────────────────────────────────────┘
```

### 8.2.2 動画D&Dエリア

対応形式:

- mp4
- mov
- mkv
- webm
- avi

受け入れ条件:

- ファイルが存在する
- ffprobeで動画として認識できる
- 長さが取得できる
- 読み込み可能

エラー例:

- 対応していない形式です
- 動画情報を取得できません
- ファイルにアクセスできません
- ファイル名に使用できない文字があります

### 8.2.3 入力動画情報

表示項目:

- ファイル名
- フルパス
- 長さ
- 解像度
- FPS
- コーデック
- 音声トラック有無
- ファイルサイズ

### 8.2.4 プロンプト欄

日本語プロンプト:

- ユーザーが自然な日本語で入力
- 空でも可。ただし生成時に警告
- 例: 「ベッドのきしみ、荒い息、肌が擦れる音、室内の反響」

英語プロンプト:

- Google翻訳結果を表示
- 手動編集可能
- 最終的にMMAudioへ渡すのは英語プロンプト

翻訳ボタン:

- 日本語プロンプトが空なら無効
- Google APIキー未設定なら警告
- 翻訳失敗時は手動入力を促す

### 8.2.5 生成設定

基本設定:

| 項目 | 初期値 | 説明 |
|---|---:|---|
| seed | random | 生成乱数 |
| duration | auto / 8 | 生成秒数 |
| steps | MMAudio既定値 | 推論ステップ |
| cfg | MMAudio既定値 | prompt反映度 |
| model | NSFW_MMaudio | 使用モデル |
| output mode | video+audio | 音付きmp4出力 |

v1.0ではMMAudio CLIで対応できる項目のみUI表示する。未対応項目は内部予約に留める。

### 8.2.6 ボタン

#### 生成

条件:

- 動画が選択済み
- 英語プロンプトが入力済み
- モデルが利用可能
- FFmpegが利用可能
- 実行中ジョブがない

動作:

1. 一時フォルダにジョブディレクトリ作成
2. 入力動画情報を保存
3. 英語プロンプトを保存
4. MMAudio生成開始
5. ログをGUIへ流す
6. 完成後、プレビューを更新

#### 再生成

条件:

- 直前の生成ジョブが存在する
- 動画とプロンプトが残っている
- 実行中ジョブがない

動作:

- seedを変更して再生成
- 設定で「同じseedで再生成」も選べる
- 前回結果は履歴に残す
- プレビューは最新結果に更新

#### 停止

条件:

- 生成中ジョブがある

動作:

- subprocess実行中ならterminate
- 一定時間後も終了しなければkill
- 一時ファイルは残す/消すを設定可能

#### 保存

条件:

- 生成済みmp4が存在する

保存ファイル名:

```text
<元ファイル名>_mmaudio.mp4
```

同名ファイルが存在する場合:

```text
<元ファイル名>_mmaudio_001.mp4
<元ファイル名>_mmaudio_002.mp4
```

保存後:

- 保存先パスを表示
- 「フォルダを開く」ボタンを表示

---

## 9. 生成フロー

### 9.1 単発生成

```text
User drops video
  ↓
VideoService probes video
  ↓
User enters Japanese prompt
  ↓
TranslationService translates to English
  ↓
GenerateWorker starts
  ↓
MMAudioRunner prepares command
  ↓
MMAudio runs
  ↓
OutputManager detects generated mp4
  ↓
PreviewPlayer loads result
  ↓
History records job
```

### 9.2 MMAudio実行方式

v1.0ではCLIラップ方式を採用する。

例:

```bash
python demo.py --duration=8 --video="<input_video>" --prompt "<english_prompt>"
```

実装時にはMMAudioの最新CLI引数を確認し、以下の抽象メソッドに閉じ込める。

```python
class MMAudioRunner:
    def build_command(self, job: GenerateJob) -> list[str]:
        ...

    def run(self, job: GenerateJob, on_log: Callable[[str], None]) -> GenerateResult:
        ...
```

将来的にライブラリ呼び出しへ切り替える場合も、GUI側は変更しない。

### 9.3 出力検出

MMAudioの出力フォルダを監視し、生成されたmp4を特定する。

推奨:

- ジョブごとに専用 output_dir を渡せるなら渡す
- 渡せない場合は実行前後のファイル差分で検出
- 生成日時が最新のmp4を採用
- flacも履歴に記録する

### 9.4 長尺動画

v1.0では単純処理を基本とする。

- 動画長が8秒以下: そのまま生成
- 8秒超: 警告表示
- 8秒超でもユーザーが希望すれば生成可能
- 自動分割はv1.1以降

警告文例:

```text
MMAudioは8秒前後の生成を基本としています。
長尺動画では品質が不安定になる可能性があります。
v1.0では自動分割は行いません。
```

v1.1以降の長尺対応:

```text
動画を8秒ごとに分割
  ↓
各チャンクに同一または派生promptで生成
  ↓
音声をクロスフェード
  ↓
元動画にmux
```

---

## 10. 翻訳機能

### 10.1 基本仕様

- 日本語から英語への翻訳
- Google Cloud Translation APIを使用
- 翻訳結果は英語プロンプト欄に表示
- ユーザーは翻訳結果を手動編集可能
- 最終的に使用するのは英語プロンプト欄の内容

### 10.2 APIキー

優先順位:

1. GUIで一時入力されたAPIキー
2. 環境変数 `MWRAPPER_GOOGLE_API_KEY`
3. configの外部参照設定
4. 未設定

未設定時:

- 翻訳ボタンを押した場合に設定案内を表示
- 英語プロンプト手入力なら生成可能

### 10.3 Google Translation実装

抽象インターフェース:

```python
class TranslationService:
    def translate_ja_to_en(self, text: str) -> str:
        ...
```

Google実装:

```python
class GoogleTranslationService(TranslationService):
    def __init__(self, api_key: str):
        ...

    def translate_ja_to_en(self, text: str) -> str:
        ...
```

### 10.4 翻訳プロンプトの扱い

Google翻訳は自然言語翻訳として使う。LLMによる過剰なプロンプト最適化はv1.0では行わない。

ただし、将来の拡張用にPromptManagerを用意する。

```python
class PromptManager:
    def normalize_japanese_prompt(self, text: str) -> str:
        ...

    def postprocess_english_prompt(self, text: str) -> str:
        ...
```

v1.0では基本的にtrim程度でよい。

---

## 11. モデル管理

### 11.1 モデル保存先

デフォルト:

```text
%LOCALAPPDATA%\mWrapper\models
```

構成例:

```text
models/
  mmaudio/
    repo/
  NSFW_MMaudio/
    ...
```

### 11.2 モデル取得

`huggingface_hub.snapshot_download()` を使う。

擬似コード:

```python
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="phazei/NSFW_MMaudio",
    local_dir=model_dir,
    local_dir_use_symlinks=False,
)
```

### 11.3 モデル検証

ダウンロード後に以下を確認する。

- ディレクトリが存在する
- 必要な重みファイルが存在する
- ファイルサイズが0ではない
- MMAudio実行時に読み込める

注意:

- 必要ファイル名は実装時に実際のモデル構成を確認して決定する
- ファイル名を仕様書上で固定しない

### 11.4 MMAudio本体管理

方針は2案。

#### 案A: pip / git cloneで取得

初回セットアップ時にMMAudio本体を取得する。

メリット:

- 最新に追従しやすい
- リポジトリが軽い

デメリット:

- 初回セットアップにネット接続が必要
- upstream変更で壊れる可能性

#### 案B: mWrapper側にサブモジュール/特定revision固定

メリット:

- 再現性が高い

デメリット:

- ライセンス表記・更新管理が必要
- リポジトリ構成が重い

推奨:

- v1.0では特定commit/revisionを指定して取得
- configまたは定数にrevisionを保持
- READMEに動作確認済みrevisionを記載

---

## 12. 動画処理

### 12.1 ffprobe

動画情報取得に使用する。

取得項目:

- duration
- width
- height
- fps
- video codec
- audio codec
- audio stream count
- bitrate

### 12.2 ffmpeg

用途:

- 出力動画の確認
- 音声mux補助
- 将来の分割処理
- 将来のクロスフェード
- 将来の再エンコード

### 12.3 プレビュー

PySide6の動画再生機能を使用する。

候補:

- `QMediaPlayer`
- `QVideoWidget`
- `QAudioOutput`

プレビュー対象:

- 入力動画
- 生成済み動画

UI:

- 再生/停止
- シークバー
- 音量
- 現在時間/総時間

---

## 13. ジョブ管理

### 13.1 GenerateJob

```python
@dataclass
class GenerateJob:
    job_id: str
    input_video_path: Path
    japanese_prompt: str
    english_prompt: str
    seed: int | None
    duration: float | None
    model_id: str
    output_dir: Path
    created_at: datetime
```

### 13.2 GenerateResult

```python
@dataclass
class GenerateResult:
    job_id: str
    success: bool
    output_video_path: Path | None
    output_audio_path: Path | None
    log_path: Path
    error_message: str | None
    started_at: datetime
    finished_at: datetime
```

### 13.3 JobManager

責務:

- ジョブ作成
- 実行中ジョブ管理
- キャンセル
- 履歴保存
- 再生成用の前回設定保持

### 13.4 履歴

`history.jsonl` に1ジョブ1行で保存。

保存項目:

- job_id
- input_video_path
- japanese_prompt
- english_prompt
- seed
- duration
- model_id
- output_video_path
- success
- error_message
- created_at
- finished_at

---

## 14. 設定ファイル

### 14.1 config.json

保存先:

```text
%APPDATA%\mWrapper\config.json
```

例:

```json
{
  "version": 1,
  "paths": {
    "output_dir": "C:/Users/<User>/Videos/mWrapper/outputs",
    "temp_dir": "C:/Users/<User>/AppData/Local/mWrapper/temp",
    "models_dir": "C:/Users/<User>/AppData/Local/mWrapper/models",
    "ffmpeg_path": "",
    "ffprobe_path": ""
  },
  "translation": {
    "provider": "google",
    "api_key_env": "MWRAPPER_GOOGLE_API_KEY"
  },
  "model": {
    "default_model": "NSFW_MMaudio",
    "models": {
      "NSFW_MMaudio": {
        "repo_id": "phazei/NSFW_MMaudio",
        "local_dir": ""
      }
    }
  },
  "generation": {
    "default_duration": 8,
    "default_seed_mode": "random",
    "keep_temp_files": false
  },
  "safety": {
    "accepted_terms": false,
    "accepted_terms_at": null
  }
}
```

### 14.2 APIキー保存方針

v1.0ではAPIキーをconfig.jsonに直接保存しない。

対応:

- 環境変数
- GUIで起動中のみ保持
- 将来keyring対応

---

## 15. エラーハンドリング

### 15.1 エラー分類

| 種別 | 例 | ユーザー表示 |
|---|---|---|
| 入力エラー | 動画未選択 | 動画を選択してください |
| 翻訳エラー | APIキー不正 | Google翻訳に失敗しました |
| モデルエラー | モデル未導入 | モデルセットアップを実行してください |
| 実行エラー | MMAudio失敗 | 生成に失敗しました。ログを確認してください |
| FFmpegエラー | ffmpegなし | FFmpegを設定してください |
| 保存エラー | 権限なし | 保存先に書き込めません |
| キャンセル | ユーザー停止 | 生成を停止しました |

### 15.2 ログ

ログ保存先:

```text
%LOCALAPPDATA%\mWrapper\logs
```

ログ内容:

- アプリ起動
- 設定読み込み
- セットアップ進捗
- MMAudio実行コマンド
- 標準出力
- 標準エラー
- 例外スタックトレース
- 生成結果パス

注意:

- APIキー、Hugging Face token、個人情報をログに出さない
- プロンプトは履歴に保存するが、設定で無効化可能にする

---

## 16. セキュリティ・プライバシー

### 16.1 外部通信

外部通信が発生する箇所:

- Hugging Faceからモデル取得
- Google Cloud Translation API
- MMAudio取得時のGitHubアクセス

ユーザーに明示する。

### 16.2 ローカル処理

動画ファイル自体は外部送信しない。

ただし:

- Google翻訳を使う場合、日本語プロンプトはGoogle APIへ送信される
- モデル取得時にHugging Faceへアクセスする

### 16.3 シークレット管理

以下はログ・履歴に保存しない。

- Google APIキー
- Hugging Face token
- OSユーザー名を含む不要な詳細
- 認証情報

---

## 17. ビルド・配布

### 17.1 開発環境

推奨:

- Python 3.10 or 3.11
- Windows 10/11
- NVIDIA GPU
- CUDA対応PyTorch
- Git
- FFmpeg

### 17.2 requirements.txt

初期案:

```text
PySide6
torch
torchvision
torchaudio
huggingface_hub
requests
pydantic
python-dotenv
```

MMAudio本体が要求する依存は、MMAudio側のrequirementsに従う。

### 17.3 PyInstaller

Windows向け配布に PyInstaller を使用する。

方針:

- mWrapper本体をexe化
- モデルは同梱しない
- 初回起動時にモデル取得
- PyTorch同梱版は非常に重くなるため、初期は開発者向けと初心者向けを分ける

配布形態案:

#### 案A: 開発者向け

```text
git clone
python -m venv .venv
pip install -r requirements.txt
python -m mwrapper
```

#### 案B: 初心者向け

```text
mWrapper_Setup.exe
  ↓
アプリインストール
  ↓
初回起動ウィザードで依存・モデル導入
```

v1.0では案Aを完成させた後、案Bへ進む。

---

## 18. 実装マイルストーン

### 18.1 v0.1 MVP

目的:

英語プロンプト手入力で、単発生成・プレビュー・保存できる。

実装:

- PySide6メイン画面
- 動画D&D
- ffprobeで動画情報表示
- 英語プロンプト入力
- MMAudio CLIラップ
- 生成ログ表示
- 出力mp4検出
- プレビュー
- 保存ボタン
- `<元ファイル名>_mmaudio.mp4` 保存

受け入れ条件:

- mp4をD&Dできる
- 英語プロンプトで生成できる
- 生成結果をプレビューできる
- 保存ボタンで指定フォルダに保存できる
- 同名時に連番保存できる

### 18.2 v0.2 翻訳・設定

目的:

日本語プロンプトから英語プロンプトへ翻訳できる。

実装:

- Google翻訳API連携
- APIキー設定
- 英語プロンプト手動編集
- config.json
- 設定画面
- 保存先設定
- seed設定
- 再生成ボタン

受け入れ条件:

- 日本語を英語に翻訳できる
- APIキー未設定でも英語手入力で生成できる
- 再生成できる
- 設定が再起動後も保持される

### 18.3 v0.3 初回セットアップ

目的:

初心者向けに必要環境を確認・導入できる。

実装:

- 初回起動ウィザード
- 利用条件確認
- GPU/CUDA/PyTorchチェック
- FFmpegチェック
- モデルダウンロード
- MMAudio取得/確認
- テスト生成

受け入れ条件:

- 初回起動時にセットアップが開始される
- モデル未導入なら案内される
- セットアップ結果が明確に表示される
- エラー時に次に何をすればよいか表示される

### 18.4 v0.4 履歴・ログ強化

目的:

生成結果の再現性を高める。

実装:

- history.jsonl
- ジョブ履歴画面
- 過去設定から再生成
- ログビューア
- temp自動削除
- エラー詳細表示

受け入れ条件:

- 過去ジョブを確認できる
- 過去prompt/seedで再生成できる
- ログから失敗原因を追える

### 18.5 v1.0 安定版

目的:

GitHub公開可能な品質にする。

実装:

- README
- LICENSE
- ThirdPartyNotices.md
- 利用条件確認
- 安全方針
- Windows動作確認
- 主要エラーハンドリング
- テスト整備
- リリース手順

受け入れ条件:

- README手順でセットアップできる
- 初心者がメイン機能を使える
- ライセンス注意が明記されている
- モデルや成人向け素材がリポジトリに含まれていない

### 18.6 v1.1以降

候補:

- 長尺動画の自動分割・結合
- クロスフェード
- バッチ処理
- 複数候補同時生成
- プリセット
- ネガティブプロンプト
- ローカル翻訳
- keyring対応
- PyInstaller/インストーラ配布

---

## 19. テスト仕様

### 19.1 単体テスト

対象:

- config読み書き
- 出力ファイル名生成
- 同名時連番
- 動画拡張子判定
- ffprobe結果パース
- 翻訳サービスのモック
- MMAudioRunnerのコマンド生成
- 履歴保存

### 19.2 結合テスト

対象:

- 動画D&Dから情報表示
- 翻訳から生成
- 生成完了からプレビュー
- 保存
- 再生成
- キャンセル
- モデル未設定時のエラー
- ffmpeg未設定時のエラー

### 19.3 手動テスト

ケース:

1. 初回起動
2. 利用条件未同意で進めない
3. モデル未導入状態
4. Google APIキー未設定状態
5. 英語プロンプト手入力生成
6. Google翻訳生成
7. 8秒以下動画
8. 8秒超動画
9. 同名保存
10. 生成中キャンセル
11. 保存先権限なし
12. アプリ再起動後の設定保持

---

## 20. UI文言案

### 20.1 生成前警告

```text
この動画は8秒を超えています。
MMAudioは8秒前後の生成を基本としているため、長尺動画では品質が不安定になる可能性があります。
このまま生成しますか？
```

### 20.2 Google APIキー未設定

```text
Google翻訳APIキーが設定されていません。
翻訳機能を使うにはAPIキーを設定してください。
英語プロンプトを手動入力すれば、翻訳なしで生成できます。
```

### 20.3 モデル未導入

```text
モデルがまだ導入されていません。
初回セットアップを実行するか、設定画面からモデルフォルダを指定してください。
```

### 20.4 生成完了

```text
生成が完了しました。
プレビューで確認し、問題なければ保存してください。
```

### 20.5 保存完了

```text
保存しました。
<保存先パス>
```

---

## 21. README構成案

```text
# mWrapper

mWrapper is a beginner-friendly GUI wrapper for MMAudio-based video-to-audio generation.

## Features

- Drag & drop video input
- Japanese prompt input
- Google Translation API support
- MMAudio / NSFW_MMaudio generation
- Preview generated video
- Regenerate instantly
- Save as <original_filename>_mmaudio.mp4
- Setup wizard for models and dependencies

## Important Safety Notice

Use only with legal, consenting adult content.

Prohibited uses:
- minors or minor-looking sexual content
- non-consensual material
- voyeuristic or leaked material
- revenge pornography
- unauthorized sexual manipulation of real people
- illegal or rights-infringing content

## Installation

...

## Model Setup

...

## Google Translation Setup

...

## License

mWrapper is licensed under the MIT License.
Third-party models and tools are governed by their own licenses.
```

---

## 22. Codex向け実装指示

### 22.1 最初に実装すること

まず v0.1 MVP を実装する。

優先順位:

1. PySide6アプリの起動
2. メイン画面作成
3. 動画D&D
4. ffprobe連携
5. 英語プロンプト入力
6. MMAudioRunnerのCLIラップ
7. 生成ログ表示
8. 出力mp4検出
9. プレビュー
10. 保存処理

### 22.2 実装ルール

- GUIスレッドで重い処理をしない
- 生成処理はQThreadまたはQRunnableで実行する
- subprocessのstdout/stderrをGUIログへ流す
- APIキーやトークンをログ出力しない
- パスはpathlib.Pathで扱う
- Windowsパスの空白に注意する
- 外部コマンドはshell=Trueを避ける
- 例外は握りつぶさず、ユーザー向けメッセージと詳細ログに分ける
- モデルやMMAudioのファイル名はできるだけ設定化する
- テスト可能な処理はGUIから分離する

### 22.3 最初のPRの完成条件

- `python -m mwrapper` で起動する
- mp4をD&Dできる
- 動画情報が表示される
- 英語プロンプトを入力できる
- GenerateボタンでMMAudio CLIを呼べる
- stdout/stderrが画面に出る
- 生成結果mp4を検出できる
- プレビューできる
- Saveボタンで `<元ファイル名>_mmaudio.mp4` として保存できる

---

## 23. オープン課題

実装前または実装中に確認すること。

1. NSFW_MMaudioの実際のファイル構成
2. MMAudio CLIの最新引数
3. MMAudioに外部モデルパスを渡す方法
4. WindowsでのMMAudio動作可否
5. PyTorch CUDA版の自動導入方法
6. FFmpeg自動導入を行うか
7. Google APIキーの安全な保存方法
8. PyInstaller化時のPySide6/torch同梱サイズ
9. GitHub公開時のREADME表現
10. ThirdPartyNotices.mdの正確なライセンス一覧

---

## 24. まとめ

mWrapper は、MMAudio / NSFW_MMaudio による動画音付け作業を、ComfyUIよりも単純で反復しやすいGUI体験にするための専用アプリである。

v1.0では以下を最重要ゴールとする。

- Python + PySide6で完結
- D&D → prompt → generate → preview → regenerate → save の流れを実現
- 日本語プロンプトをGoogle翻訳で英語化
- モデルや依存関係は初回セットアップで導入
- アプリ本体はMIT LicenseでGitHub公開
- モデルや成人向け素材はリポジトリに含めない
- 安全・合法・同意済み素材のみを対象とする方針を明記する
