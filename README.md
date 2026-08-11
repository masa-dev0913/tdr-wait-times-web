# TDR待ち時間トラッカー

東京ディズニーランド／ディズニーシーのアトラクション・レストランの待ち時間を15分おきに自動記録し、当日・過去7日間などで振り返れるWebアプリです。

- **データ取得元**: 非公式サイト [tokyodisneyresort.info](https://tokyodisneyresort.info/) （公式はAPIを提供していないため）
- **記録**: 標準のLinux `cron` が `scraper/run.py` を15分おきに実行し、`data/waittimes.db`（SQLite）に追記
- **閲覧**: `app.py`（Streamlit）を常時プロセスとして稼働し、ブラウザで参照

## 構成

```
scraper/fetch.py   HTML取得
scraper/parse.py   HTML→レコード変換
scraper/run.py     4ページ(ランド/シー × アトラクション/レストラン)を取得しDBへ保存。cronから15分毎に起動
common/db.py        SQLiteスキーマ定義・接続
app.py               Streamlit閲覧アプリ
deploy/              サーバー設置用の crontab・systemd unit の例
```

## ローカルでの動作確認

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# .venv/bin/pip install -r requirements.txt         # macOS/Linux

.venv/Scripts/python -m scraper.run                 # 1回スクレイプしてDBに保存
.venv/Scripts/python -m streamlit run app.py         # ブラウザで確認 (http://localhost:8501)
```

## サーバーへのデプロイ（Ubuntu/Debian想定）

15分おきの確実な定期実行のため、GitHub Actionsのような外部cronではなく、**常時起動している1台のLinuxサーバー**（無料枠の常時稼働VMや格安VPSなど）上で、標準の`cron`とデータ記録スクリプト、Streamlitアプリを同居させる構成にしています。

1. サーバーにPython 3.10以上をインストール
2. このリポジトリをサーバーに配置（例: `/opt/tdr-wait-times`）
   ```bash
   git clone <このリポジトリのURL> /opt/tdr-wait-times
   cd /opt/tdr-wait-times
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   mkdir -p data logs
   ```
3. `crontab -e` で [deploy/crontab.txt](deploy/crontab.txt) の内容を登録（パスは実際の配置場所に合わせて書き換え）
4. [deploy/tdr-viewer.service](deploy/tdr-viewer.service) を `User=` とパスを実環境に合わせて編集し、`/etc/systemd/system/tdr-viewer.service` に配置
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now tdr-viewer
   ```
5. サーバーのファイアウォール／クラウドのセキュリティグループでポート8501（`--server.port`で変更可）を開放
6. `http://<サーバーのIPまたはドメイン>:8501` にアクセスして確認

### 動作確認コマンド

```bash
sudo systemctl status tdr-viewer     # Webアプリが起動しているか
tail -f logs/scrape.log               # cronによるスクレイプが15分毎に成功しているか
crontab -l                            # cron登録内容の確認
```

### 発展（任意）

- 独自ドメイン＋HTTPS化: nginxでリバースプロキシし、Let's Encrypt（certbot）で証明書を取得
- サーバー再起動後もcronは自動的に有効なままですが、`crontab -l` で登録が消えていないか初回は確認してください

## データ取得についての注意

`tokyodisneyresort.info` は非公式の有志運営サイトです。15分に1回・1リクエストずつという低頻度アクセスに留め、専用のUser-Agent（`scraper/fetch.py`）を設定しています。サイト構造が変わった場合は `scraper/parse.py` の修正が必要になることがあります。
