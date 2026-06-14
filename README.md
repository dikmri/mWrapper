# mWrapper

mWrapper は、MMAudio 系モデルを使って動画に音声を生成して付与するための Windows 向け GUI ラッパーです。

動画をウィンドウへドラッグアンドドロップし、ポジティブプロンプトと必要に応じてネガティブプロンプトを入力して生成できます。初回起動時にはセットアップ先フォルダを選ぶだけで、MMAudio、NSFW_MMaudio、専用 venv、CUDA 版 PyTorch の導入を自動で行います。

## 注意

このツールは、合法で同意済みの成人向け素材のみを対象にしてください。

次の用途には使用しないでください。

- 未成年、または未成年に見える人物を含む性的コンテンツ
- 非同意、盗撮、流出、リベンジポルノ
- 実在人物への無断の性的加工
- 違法、権利侵害、プライバシー侵害にあたる素材や用途

モデル、MMAudio、FFmpeg、PyTorch などの第三者コンポーネントは、それぞれのライセンスと利用条件に従ってください。

## インストール

Windows の PowerShell で次を実行してください。最新リリースの Windows 版 zip をダウンロードし、`%LOCALAPPDATA%\mWrapper\app` に展開して、スタートメニューとデスクトップにショートカットを作成します。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/dikmri/mWrapper/main/scripts/install.ps1 | iex"
```

インストール先を変えたい場合は、実行前に `MWRAPPER_INSTALL_DIR` を指定してください。

```powershell
$env:MWRAPPER_INSTALL_DIR = "D:\Apps\mWrapper"
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/dikmri/mWrapper/main/scripts/install.ps1 | iex"
```

デスクトップショートカットを作らない場合は `MWRAPPER_NO_DESKTOP_SHORTCUT=1` を指定できます。

```powershell
$env:MWRAPPER_NO_DESKTOP_SHORTCUT = "1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/dikmri/mWrapper/main/scripts/install.ps1 | iex"
```

手動で入れる場合は、GitHub Releases から `mWrapper-<version>-windows.zip` をダウンロードし、任意のフォルダに展開して `mWrapper.exe` を起動してください。

FFmpeg は別途必要です。`ffmpeg` と `ffprobe` が PATH から実行できる状態にしてください。

## 自動アップデート

リリース版の `mWrapper.exe` は、起動直後に GitHub Releases の最新版を確認します。

最新版がない場合はそのまま起動します。最新版がある場合は、ログに進捗を表示しながら Windows 版 zip をダウンロードし、mWrapper を終了して更新を適用したあと自動で再起動します。

自動アップデートを無効にしたい場合は、起動前に `MWRAPPER_DISABLE_AUTO_UPDATE=1` を指定してください。

```powershell
$env:MWRAPPER_DISABLE_AUTO_UPDATE = "1"
```

## 初回セットアップ

初回起動時、mWrapper はセットアップ先フォルダを選択します。

選択したフォルダには次のものを配置します。

- MMAudio 本体
- NSFW_MMaudio の重み
- MMAudio 専用 venv
- CUDA 版 PyTorch
- Hugging Face などの実行時キャッシュ

必要容量を見積もり、空き容量が足りないドライブは選択できないようにしています。環境にもよりますが、初回構築にはおおむね 20 GB 前後の空き容量が必要です。

セットアップ済みの環境は再利用されます。起動するたびに毎回インストールし直すことはありません。環境が壊れた場合や、別のドライブへ作り直したい場合だけ、画面上の `初期化` ボタンを押してください。

## 使い方

1. mWrapper を起動します。
2. 動画ファイルをウィンドウ内へドラッグアンドドロップします。
3. `MMAudio` または `NSFW_MMaudio` を選びます。
4. ポジティブプロンプトを入力します。
5. 必要ならネガティブプロンプトを入力します。
6. 毎回違う結果にしたい場合は `seed固定` をオフにします。
7. 同じ seed を再利用したい場合は `seed固定` をオンにします。
8. `生成` を押します。
9. プレビューで確認し、必要なら保存します。

プロンプトの内容は終了時に保存され、次回起動時に復元されます。

生成 duration はドラッグアンドドロップした動画の長さに合わせて自動調整されます。

## GPU / CUDA

NVIDIA GPU がある場合、初回セットアップ時に `nvidia-smi` でハードウェア情報を確認し、PyTorch の CUDA wheel を自動選択します。RTX 50 系など新しい GPU では古い CUDA 11.8 wheel が実行時に失敗することがあるため、mWrapper は CUDA 12.8 の PyTorch を優先します。

NVIDIA GPU がない場合は CPU 構成を選びます。ただし MMAudio の生成は重いため、実用上は CUDA 対応 GPU を推奨します。

## 出力

生成結果は MMAudio の出力から検出し、保存時に次の形式でコピーします。

```text
<元動画名>_mmaudio.mp4
```

同名ファイルがある場合は番号を付けて上書きを避けます。

## 開発

開発用にリポジトリを取得して動かす場合は次の通りです。

```powershell
git clone https://github.com/dikmri/mWrapper.git
cd mWrapper
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m mwrapper
```

テストは次で実行できます。

```powershell
python -m pytest
```

Windows exe zip は次で作成できます。

```powershell
.\scripts\build_exe.ps1
```

## リリース

`v*` タグを GitHub に push すると、GitHub Actions がテスト、Python package、Windows exe zip のビルド、GitHub Release の作成を行います。

```powershell
git tag v0.1.3
git push origin v0.1.3
```

Release には次のファイルが添付されます。

- `mWrapper-<version>-windows.zip`
- `mwrapper-<version>-py3-none-any.whl`
- `mwrapper-<version>.tar.gz`

## ライセンス

mWrapper 本体は MIT License です。

このリポジトリには MMAudio のモデル重み、NSFW_MMaudio のモデル重み、FFmpeg バイナリ、生成済みメディアは同梱していません。第三者コンポーネントの詳細は [ThirdPartyNotices.md](ThirdPartyNotices.md) を確認してください。
