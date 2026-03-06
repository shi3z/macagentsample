# Mac Agent Sample

ローカルで動作するエージェンティックAI。Ollamaを使用し、Web検索、ファイル操作、コード実行、画像生成が可能。

## 機能

- **チャット**: Ollama (gpt-oss:20b-long) によるストリーミング応答
- **Web検索**: DuckDuckGo News APIで最新ニュースを検索
- **ファイル操作**: ローカルファイルの読み書き
- **コード実行**: Pythonコードの実行
- **画像生成**: FLUX (mflux) によるApple Silicon対応画像生成
- **RAG**: ChromaDBによるドキュメント検索
- **音声入出力**: Web Speech API対応

## 必要条件

- macOS (Apple Silicon推奨)
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai/) with `gpt-oss:20b-long` model
- Conda環境 `mlx312` with mflux (画像生成用)

## セットアップ

### 1. Ollamaモデルのダウンロード

```bash
ollama pull gpt-oss:20b-long
```

### 2. バックエンドのセットアップ

```bash
cd backend
pip install -r requirements.txt
```

### 3. フロントエンドのセットアップ

```bash
cd frontend
npm install
```

### 4. 画像生成環境のセットアップ (オプション)

```bash
conda create -n mlx312 python=3.12
conda activate mlx312
pip install mflux
```

`backend/agent/tools.py` の `mflux_path` を環境に合わせて修正:
```python
mflux_path = "/path/to/your/conda/envs/mlx312/bin/mflux-generate"
```

## 起動

### バックエンド

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### フロントエンド

```bash
cd frontend
npm run dev
```

または一括起動:

```bash
./start.sh
```

## アクセス

- フロントエンド: http://localhost:5173
- バックエンドAPI: http://localhost:8000
- VPN経由: http://<your-tailscale-ip>:5173

## 使用例

- 「今日のニュースを教えて」→ Web検索
- 「猫の画像を生成して」→ FLUX画像生成
- 「このコードを実行して: print('Hello')」→ コード実行
- 「~/project/file.txt を読んで」→ ファイル読み取り

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/health` | GET | ヘルスチェック |
| `/api/chat` | POST | チャット (SSE) |
| `/api/documents/upload` | POST | ドキュメントアップロード |
| `/api/documents/count` | GET | ドキュメント数取得 |
| `/api/documents/search` | POST | ドキュメント検索 |
| `/api/images/{filename}` | GET | 生成画像取得 |

## ライセンス

MIT
