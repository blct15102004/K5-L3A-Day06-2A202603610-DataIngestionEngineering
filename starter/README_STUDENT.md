# Starter · PostgreSQL + pgvector — Hướng dẫn thực tế (2A202603610)

> Đây là hướng dẫn chạy thực tế cho bài làm của **Bùi Lê Công Tuấn (2A202603610)**.
> File gốc README của đề bài: xem [../README.md](../README.md).

## Yêu cầu

- Docker Desktop (đang chạy)
- Python 3.11+ (có trong PATH, hoặc dùng đường dẫn đầy đủ `.venv\Scripts\python.exe`)
- Gemini API key (miễn phí tại https://aistudio.google.com)

## Cài đặt lần đầu

```powershell
# 1. Vào thư mục starter
cd c:\LAB-AI-THUCCHIEN\K5-L3A-Day06-2A202603610-DataIngestionEngineering\starter

# 2. Tạo virtual environment
python -m venv .venv

# 3. Cài thư viện (chạy với BypassSandbox nếu cần)
.venv\Scripts\pip install -r requirements.txt

# 4. Cấu hình API key
# Chỉnh file .env (đã tồn tại) — điền GEMINI_API_KEY của bạn

# 5. Khởi động PostgreSQL
docker compose -p day6_student_starter up -d --wait

# 6. Kiểm tra setup
.venv\Scripts\python.exe scripts\check_setup.py
# Kỳ vọng: Database: day6_lab | PostgreSQL: 16.x | pgvector: 0.8.7 | Setup OK
```

## Chạy pipeline đầy đủ

```powershell
cd c:\LAB-AI-THUCCHIEN\K5-L3A-Day06-2A202603610-DataIngestionEngineering\starter
.venv\Scripts\python.exe -m src.run
```

Pipeline sẽ thực hiện tuần tự:
1. **Load & normalize**: Đọc `data/giao_an_the_duc_thcs_51_trang.pdf` (51 trang)
2. **Strategy A**: Fixed-size chunking (500 chars, 50 overlap) → 218 chunks
3. **Strategy B**: Paragraph chunking (max 500 chars) → 238 chunks
4. **Strategy C**: Dùng lại index của B, áp dụng filter tại query time
5. **Embed**: Gọi Gemini API `models/gemini-embedding-001` (có disk cache)
6. **Store**: Upsert vào PostgreSQL pgvector (bảng `chunks`)
7. **Benchmark**: Chạy 20 câu hỏi từ `data/benchmark.json`
8. **Save results**: Traces → `results/traces_strategy_{a,b,c}.json`, summary → `results/benchmark_summary.json`

**Thời gian:** ~5–10 phút nếu dùng cache; ~20–30 phút nếu embed từ đầu.

## Tạo đánh giá thủ công

```powershell
.venv\Scripts\python.exe scripts\generate_manual_evaluations.py
```

Output: `artifacts/coherence_evaluation.json`, `artifacts/grounding_evaluation.json`, `artifacts/metadata_check.json`

## Lưu ý quan trọng

> **psycopg binary bị block bởi Windows App Control Policy** trên máy này.  
> `store.py` và `check_setup.py` dùng `pg8000` thay thế.  
> Nếu chạy trên máy khác không có App Control, có thể cài thêm `psycopg[binary]` và chỉnh lại import trong `store.py`.

## Cấu hình .env

```env
GEMINI_API_KEY=<your_key_here>
EMBEDDING_MODEL=models/gemini-embedding-001
DATABASE_URL=postgresql://student:studentpass@127.0.0.1:55433/day6_lab
```

## Corpus

| File | Mô tả |
|---|---|
| `data/bother2025modyn.pdf` | Corpus chính — 30 trang nghiên cứu SIGMOD 2025 "Modyn: Data-Centric Machine Learning Pipeline Orchestration" |
| `data/benchmark.json` | 20 câu hỏi benchmark (15 dev + 5 test) |
| `data/manifest.json` | Manifest nguồn dữ liệu |

## Kết quả benchmark (tóm tắt)

| Strategy | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 | Filter Compliance |
|---|---|---|---|---|---|
| A (Fixed) | 6.67% | 26.67% | 0% | 0% | 25% |
| B (Paragraph) | 0% | 26.67% | 0% | 0% | 0% |
| C (Para+Filter) | 6.67% | 33.33% | 0% | 20% | 100% |

**Chiến lược chọn: Strategy C** — Hit@3 cao nhất, filter compliance 100%.

Xem chi tiết: [report/individual/2A202603610_BuiLeCongTuan.md](../report/individual/2A202603610_BuiLeCongTuan.md)

