# MiniGPT — 自己的 Qwen / Ollama + Vercel

回答由你 Mac 上已下載的 Ollama 模型生成。這份程式沒有 OpenAI API、ChatGPT 或其他雲端聊天模型呼叫。Vercel 只負責網頁與轉送；Mac、Ollama、橋接服務與 tunnel 都要保持開啟。模型權重留在 Mac，不必上传 GitHub。

## 1. 確認你的模型

Mac 終端機執行：

```bash
ollama list
```

記下 NAME 欄的完整名稱。本文以 `qwen2.5:0.5b` 示範；請換成你已下載的名稱，例如 `qwen2.5:7b`。不會自動下載或替換模型。

先執行：

```bash
ollama run qwen2.5:0.5b
```

回答正常後輸入 `/bye` 離開聊天。若顯示無法連線，先開啟 Ollama App；或在另一個終端機執行 `ollama serve`。已在執行時不必再啟動第二個服務。

## 2. 啟動 Mac 橋接服務

解壓縮到桌面，執行：

```bash
cd ~/Desktop/MiniGPT-ollama-vercel/mac-gateway
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

最後一行會生成隨機密碼。用文字編輯器打開 `mac-gateway/.env`，填入：

```dotenv
OLLAMA_GATEWAY_TOKEN=剛才產生的隨機密碼
OLLAMA_MODEL=qwen2.5:0.5b
```

模型名稱必須等於 `ollama list` 中你要用的名稱。啟動：

```bash
python -m uvicorn gateway:app --host 127.0.0.1 --port 8001
```

這個終端機保持開啟。橋接只提供有密碼保護的 `/api/chat`，不提供下載、刪除或管理模型的介面。不要直接公開 Ollama 的 11434 連接埠。

## 3. 建立外部連線

如果已安裝 Homebrew，可安裝 Cloudflare tunnel：

```bash
brew install cloudflared
```

測試用：另開終端機執行

```bash
cloudflared tunnel --url http://127.0.0.1:8001
```

記下輸出的 `https://…trycloudflare.com` 網址，填入下一步的 `OLLAMA_GATEWAY_URL`。不要加 `/api/chat`。不能使用 localhost 或 Mac 的區域網路 IP 作為 Vercel 連線位址。

Quick Tunnel 是暫時測試服務，重啟可能換網址，也沒有上線保證。它不支援 SSE；Mac 橋接這段使用 Ollama 原生 NDJSON，Vercel 到瀏覽器才轉成 SSE。若 tunnel 中間層緩衝回應，可能會一次收到整段答案。正式使用建議在 Cloudflare 建立固定 Tunnel，把自有網域如 `minigpt-api.stevexlab.com` 對應到 `http://127.0.0.1:8001`。不使用 Quick Tunnel 的互動式 email 驗證，因為 Vercel 後端不能完成瀏覽器登入；此程式以橋接 token 驗證。

## 4. 部署 Vercel

1. 建立 GitHub repository，上傳這個資料夾內的內容至 repository 根目錄，包含隱藏的 `.python-version`、`.gitignore`、`.vercelignore`。不要上傳 `.env`、`.venv` 或模型權重。
2. Vercel → Add New → Project → 匯入 repository。
3. Framework 選 FastAPI，Root Directory 選包含 app.py 的資料夾。Build / Install / Output 保持預設。
4. 加入下面環境變數（Production；預覽部署也需 Preview）。

| 名稱 | 值 |
| --- | --- |
| `OLLAMA_GATEWAY_URL` | 第 3 步得到的 HTTPS 網址，沒有 `/api/chat` |
| `OLLAMA_GATEWAY_TOKEN` | 與 Mac `.env` 的橋接密碼完全相同 |
| `OLLAMA_MODEL` | 與 Mac `.env`、ollama list 完全相同的模型名稱 |
| `MINIGPT_ACCESS_TOKEN` | 另外設定一組長隨機密碼，作為網站登入密碼 |
| `BRAVE_API_KEY` | 選填；只有勾選網路搜尋才會呼叫 Brave，與聊天模型無關 |

5. Deploy，開網站 →「設定」→ 輸入 `MINIGPT_ACCESS_TOKEN` →「保存並測試連線」。這個按鈕確認 Vercel 設定；第一次發送聊天才會實際測試 Mac 的模型。
6. 更改任何環境變數後重新部署。Quick Tunnel 網址換掉也需要更新與重新部署。

## 下次啟動

開啟 Ollama App，另開終端機：

```bash
cd ~/Desktop/MiniGPT-ollama-vercel/mac-gateway
source .venv/bin/activate
python -m uvicorn gateway:app --host 127.0.0.1 --port 8001
```

再開 tunnel。固定 Tunnel 使用其設定的啟動方式；Quick Tunnel 用第 3 步命令，網址更改須更新 Vercel。Mac 休眠／關機或任一服務停止，網站聊天就會無法生成；對話仍留在瀏覽器。

## 本機測試網頁（選用）

根目錄建立自己的 `.env`，依 `.env.example` 填入 HTTPS tunnel、兩種密碼與模型名稱，再執行：

```bash
cd ~/Desktop/MiniGPT-ollama-vercel
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

打開 http://127.0.0.1:8000。

## 功能與限制

- 聊天串流、六種助理模式、停止與重新生成、個人記憶、文字檔附加、對話 JSON 匯入匯出、SymPy 數學工具與可選 Brave 搜尋。
- 對話保存在瀏覽器 localStorage，不會自動跨裝置同步；可匯入原版本單一對話 JSON。
- 每次最多送 40 則／24,000 字元歷史；Ollama 使用 8,192 tokens 上下文，超出模型有效容量時可能截短。回答最多 2,048 tokens，Vercel 生成總時間上限 50 秒。
- 第一次載入較大模型可能逾時。可先在 Mac 用 `ollama run 模型名稱` 問一句話預熱，再使用網站。長回答可送出「請繼續」。
- 這個部署包未移植原版 LoRA 訓練、圖片／語音／OCR／RAG／資料分析；原版本仍可在 Mac 使用。這版使用原先下載的模型，沒有聲稱載入你的 LoRA 權重。
- 個人密碼模式，沒有多人帳號、跨裝置資料庫或每人用量限制。不要分享兩組密碼。
- 「停止」會關閉瀏覽器請求；中間代理與 Ollama 可能延遲結束運算。

## 問題排查

- 網站 401：檢查 `MINIGPT_ACCESS_TOKEN`。
- 模型服務 401：Mac 與 Vercel 的 `OLLAMA_GATEWAY_TOKEN` 不相同。
- 模型服務 400：兩側 `OLLAMA_MODEL` 不一致。
- Ollama 回報錯誤：Mac 上執行 `ollama list`，確認模型已下載且服務開啟；模型不存在通常回報 404。
- 無法連接模型：檢查 tunnel 網址、橋接终端機、Ollama 與 Mac 睡眠狀態。
- 生成逾時：預熱模型、缩短問題、使用你已下載且適合 Mac 記憶體的較小模型。

## 驗證與來源

`python tests/check.py` 使用模擬 Ollama NDJSON，驗證串流轉換、權限、錯誤處理與真實 SymPy 計算。未在你的 Mac 上測試模型，也未替你實際部署到 Vercel。

- Ollama API: https://docs.ollama.com/api/chat
- Vercel FastAPI: https://vercel.com/docs/frameworks/backend/fastapi
- Cloudflare Quick Tunnel: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
