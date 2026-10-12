# MiniGPT · Vercel 版

從 MiniGPT v0.4 改寫的雲端版本。Python 3.12 + FastAPI + 原生 HTML/CSS/JavaScript，不需要 Gradio、Rust、PyTorch、tokenizers 或本機模型。這是可部署的原始碼；尚未替你建立 Vercel 專案或實際上線。

## 部署至 Vercel

1. 解壓縮 `MiniGPT-vercel.zip`。
2. 建立 GitHub repository，把 **MiniGPT-vercel 資料夾內的檔案**上傳到 repository 根目錄（要包含 `.python-version`、`.gitignore` 和 `vercel.json`）。不要上傳 `.env` 或 `.venv`。
3. Vercel → Add New → Project → Import 該 repository。
4. Framework Preset 選 **FastAPI**（通常自動辨識）。如果 repository 外面還包了一層 `MiniGPT-vercel`，Root Directory 設成該資料夾。
5. Build Command、Output Directory、Install Command 保持預設，不要設定 `npm run build`，也不要填 `public` 為輸出目錄。
6. Environment Variables 加入下表。正式部署使用 Production；預覽測試也需要勾選 Preview。
7. 按 Deploy。完成後開網址 → 設定 → 輸入你設定的存取密碼 → 保存並測試連線。
8. 後續修改環境變數，必須重新部署才會套用。

| 環境變數 | 值 / 用途 |
| --- | --- |
| `OPENAI_API_KEY` | 必填，模型服務的 API 金鑰，僅由後端使用 |
| `MINIGPT_ACCESS_TOKEN` | 必填，自己設定的長隨機密碼，用於網站 API 驗證 |
| `OPENAI_BASE_URL` | 預設 `https://api.openai.com/v1`；可使用支援 Chat Completions SSE 的 HTTPS API |
| `OPENAI_MODEL` | 預設 `gpt-4o-mini`；依你的 API 服務填寫模型 ID |
| `BRAVE_API_KEY` | 選填，Brave Search 金鑰；設定後可啟用網路搜尋 |

ChatGPT 訂閱與模型 API 是不同服務；此網站需要 API 金鑰。模型使用費由供應商計算。不可填 `localhost`、`127.0.0.1` 或你 Mac 的本機 Ollama 位址；Vercel 會連到雲端服務。不要把金鑰放進 index.html 或提交到 GitHub。

存取密碼只存於瀏覽器 sessionStorage，關閉分頁後通常會清除。這是個人共用密碼模式；所有知道密碼的人都能使用後端模型額度，沒有多人帳號與每人限額。若要讓多人長期使用，請先加上正式登入及持久化限流。

### CLI 部署（可選）

在專案資料夾執行：

```bash
npx vercel@latest
```

完成連結後，在 Vercel 專案設定加入上表環境變數，再執行：

```bash
npx vercel@latest --prod
```

## Mac 本機安裝與啟動

請先安裝 Python 3.12。假設解壓縮的資料夾放在桌面：

```bash
cd ~/Desktop/MiniGPT-vercel
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

使用文字編輯器修改 `.env`，填入 `OPENAI_API_KEY` 與 `MINIGPT_ACCESS_TOKEN`，再執行：

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

瀏覽器開啟 `http://127.0.0.1:8000`，到設定輸入 `.env` 中的存取密碼。停止服務按 Ctrl+C。下次啟動只需：

```bash
cd ~/Desktop/MiniGPT-vercel
source .venv/bin/activate
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

## 功能對照

| 功能 | Vercel 版 |
| --- | --- |
| 聊天、一般 / 學習 / 程式 / 數學 / 研究 / 創作模式 | 支援，雲端 API 串流 |
| 停止、重新生成 | 支援；停止會中止瀏覽器連線，不保證供應商立即停止計費 |
| 對話列表、刪除、JSON 匯入 / 匯出 | 支援，瀏覽器 localStorage；不會跨裝置自動同步 |
| 個人記憶 | 支援，本機瀏覽器保存，聊天時傳送 |
| 文字 / 程式檔附加 | 支援，總訊息最多 12,000 字元 |
| 算式、方程式、微積分、矩陣、統計 | 使用原版 SymPy 白名單工具，單次 5 秒上限 |
| 網路搜尋與來源 | 支援 Brave Search 摘要，需金鑰；未讀取網頁全文 |
| 原版 SQLite 對話 | 可先在原版匯出單一對話 JSON，再在雲端版匯入；不直接上傳資料庫 |
| LoRA / MLX / 本機模型 / 背景訓練 | 保留於原本本機版本，未移植到這個部署包 |
| 圖片生成 / 編輯 / 去背、語音、OCR、資料分析、RAG | 未移植到這個部署包，使用原本本機版本 |
| 原版校對、收藏分類、訊息分支 | 未移植到這個部署包 |

全部歷史仍保存在瀏覽器；每次只送最近最多 40 則、24,000 字元的連續上下文給模型。單則使用者訊息最多 12,000 字元，個人記憶最多 3,000 字元。這版取消原版超長自動續寫，單次輸出最多 2,048 tokens；後端生成總時間最多 50 秒，Vercel 函式設 60 秒。需更長回答時送出「請繼續」。此設定避免一般請求持續過久。

## 常見問題

- **503 / 請設定存取密碼**：缺少 `MINIGPT_ACCESS_TOKEN`，加入後重新部署。
- **401 / 存取密碼錯誤**：網站設定填入的值須等於 `MINIGPT_ACCESS_TOKEN`，不是模型 API 金鑰。
- **模型服務 HTTP 401 / 403**：確認 API 金鑰與服務位址。
- **HTTP 400 / 404**：檢查模型 ID、是否支援 `/chat/completions`、是否允許 `max_tokens` 與串流。
- **HTTP 429**：供應商額度或速率限制，請檢查 API 帳戶。
- **部署 404**：Root Directory 必須包含 app.py 和 requirements.txt；Framework Preset 使用 FastAPI。
- **對話消失**：清除瀏覽器資料或切換瀏覽器 / 網域會使本機歷史無法讀取；請定期匯出。
- **本機 Python 3.14 安裝問題**：使用 `python3.12` 建立新的 .venv，不要沿用舊版的環境。

## 驗證

`tests/check.py` 用模擬模型串流驗證 API，沒有呼叫付費模型；另包含真實 SymPy 工具測試。可執行 `python tests/check.py`。前端語法也經 Node 檢查。雲端 API 實際連線與 Vercel 上線需你填入環境變數後驗證。

## 部署依據

- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/docs/functions/runtimes/python
- https://vercel.com/docs/functions/limitations

使用 Vercel 官方支援的根目錄 app.py / app 入口與 maxDuration 設定。此包不向伺服器磁碟寫入歷史或設定，不需要常駐背景工作。
