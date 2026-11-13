# Day 06 · Data Ingestion Engineering

> **Học viên:** Bùi Lê Công Tuấn  
> **MSSV:** 2A202603610 | **Lớp:** K5-L3A  
> **Corpus:** Modyn: Data-Centric Machine Learning Pipeline Orchestration (30 trang, ACM SIGMOD 2025)  
> **Báo cáo chi tiết:** [report/individual/2A202603610_BuiLeCongTuan.md](report/individual/2A202603610_BuiLeCongTuan.md)

---

## Tóm tắt Kết quả Thực nghiệm

| Chiến lược | Dev Hit@1 (n/15) | Dev Hit@3 (n/15) | Test Hit@1 (n/5) | Test Hit@3 (n/5) | Coherence (/2) | Grounding (/2) | Tuân thủ Filter |
|---|---|---|---|---|---|---|---|
| **Strategy A (Fixed-size 500/50)** | 5/15 (33.3%) | 9/15 (60.0%) | 1/5 (20.0%) | 3/5 (60.0%) | 1.20 | 0.87 | 100% |
| **Strategy B (By Paragraph max 500)** | **8/15 (53.3%)** | **10/15 (66.7%)** | 1/5 (20.0%) | 3/5 (60.0%) | **2.00** | 1.00 | 100% |
| **Strategy C (Para + Metadata Filter)** | **8/15 (53.3%)** | **10/15 (66.7%)** | 1/5 (20.0%) | 3/5 (60.0%) | **2.00** | **1.33** | **100%** |

**Chiến lược tối ưu được chọn:** **Strategy C (Paragraph Chunking + Metadata Filter)** — Đạt độ mạch lạc tuyệt đối (2.0/2.0), chất lượng grounding cao nhất (1.33/2.0 với 8/15 hits đạt điểm 2), và 100% kết quả tuân thủ bộ lọc ngữ cảnh.

---

## Hướng dẫn Tái hiện Kết quả (Reproduction Steps)

```powershell
# 1. Khởi động PostgreSQL 16 + pgvector qua Docker
cd starter
docker compose -p day6_student_starter up -d --wait

# 2. Kiểm tra kết nối database
.venv\Scripts\python.exe scripts\check_setup.py

# 3. Chạy pipeline ingestion, chunking, embedding và benchmark
.venv\Scripts\python.exe -m src.run

# 4. Tạo các file đánh giá thủ công (Coherence, Metadata, Grounding)
.venv\Scripts\python.exe scripts\generate_manual_evaluations.py
```

---

## Cấu trúc Thư mục Nộp bài

```text
├── STUDENT.md                                      # Thông tin học viên và commit chốt bài
├── README.md                                       # Hướng dẫn setup, chạy, đường dẫn dữ liệu
├── data/
│   ├── bother2025modyn.pdf                         # Corpus 30 trang (SIGMOD 2025)
│   ├── manifest.json                               # Giấy phép, nguồn, cấu trúc section
│   └── benchmark.json                              # Bộ 20 câu hỏi (15 dev / 5 test)
├── benchmark/
│   └── benchmark.json                              # Bản sao benchmark dataset
├── starter/src/                                    # Toàn bộ mã nguồn pipeline hoàn chỉnh
│   ├── ingestion.py                                # Load PDF, khử null byte, chuẩn hóa NFC, metadata
│   ├── chunking.py                                 # Fixed-size và By-paragraph chunking
│   ├── embeddings.py                               # Gemini API (gemini-embedding-001) + disk cache
│   ├── store.py                                    # PgVectorStore (pg8000, JSONB filter, upsert)
│   ├── evaluation.py                               # Chấm điểm Hit@1, Hit@3, filter compliance
│   └── run.py                                      # Điều phối pipeline 5 bước
├── artifacts/
│   ├── experiment_log.csv                          # Nhật ký thí nghiệm 3 chiến lược
│   ├── benchmark_summary.json                      # Tóm tắt chỉ số định lượng
│   ├── coherence_evaluation.json                   # Đánh giá độ mạch lạc 10 trang mẫu (0-2)
│   ├── metadata_check.json                         # Kiểm tra metadata và filter 5 câu test
│   ├── grounding_evaluation.json                   # Đánh giá grounding 5 câu test x top-3 (0-2)
│   └── traces_strategy_{a,b,c}.json                # Traces chi tiết từng truy vấn
├── results/                                        # Thư mục kết quả đồng bộ
└── report/individual/
    └── 2A202603610_BuiLeCongTuan.md                # Báo cáo cá nhân đầy đủ 5 phần
```

---

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.
