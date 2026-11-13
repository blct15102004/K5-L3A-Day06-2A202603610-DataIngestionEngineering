# Báo cáo cá nhân — Day 6: Data Ingestion Engineering

**Họ và tên:** Bùi Lê Công Tuấn  
**MSSV:** 2A202603610  
**Lớp:** K5-L3A  
**Ngày nộp:** 13/11/2026

---

## 1. Dữ liệu và Pipeline

### 1.1 Corpus

| Thuộc tính | Giá trị |
|---|---|
| Tên tài liệu | Modyn: Data-Centric Machine Learning Pipeline Orchestration |
| Tên file | `bother2025modyn.pdf` |
| Tác giả | Maximilian Böther, Ties Robroek, Viktor Gsteiger, Robin Holzinger, Xianzhe Ma, Pınar Tözün, Ana Klimovic (ETH Zurich, ITU Copenhagen, TU Munich) |
| Xuất bản / Venue | ACM SIGMOD 2025 (Berlin, Germany) |
| Quyền sử dụng | Tài liệu nghiên cứu khoa học mở (ACM Open Access / Pre-print), phục vụ mục đích nghiên cứu và giáo dục |
| Số trang | 30 trang |
| Quy tắc tính trang | Mỗi trang PDF = 1 đơn vị, đánh số 1–30 theo thứ tự xuất hiện |
| Tổng ký tự trích xuất | ~116,139 ký tự (100% trang có text trích xuất được bằng PyPDF, không có trang scan) |
| Nội dung | Bài báo hệ thống về nền tảng điều phối huấn luyện liên tục (continuous ML pipeline), bao gồm kiến trúc hệ thống, formalization toán học, chính sách chọn mẫu (data selection), phát hiện drift và kích hoạt (triggering), tầng lưu trữ song song và benchmark thực nghiệm |

### 1.2 Chuẩn hóa văn bản

Hàm `normalize_text()` trong `src/ingestion.py` thực hiện:
1. **Khử null bytes (`\x00`):** Loại bỏ các ký tự null sinh ra từ bộ giải mã font của PDF để tránh lỗi encoding `0x00` trong PostgreSQL UTF-8.
2. **Chuẩn hóa Unicode NFC:** `unicodedata.normalize("NFC", text)` đảm bảo sự nhất quán cho mọi ký tự.
3. **Chuẩn hóa khoảng trắng & ngắt dòng:** Thay thế `\u00a0` (non-breaking space) thành space thường, thu gọn chuỗi khoảng trắng và tab thừa, giữ lại tối đa 2 dấu xuống dòng giữa các đoạn văn để bảo toàn cấu trúc ngữ nghĩa.
4. **Bảo toàn ranh giới câu & đoạn:** Thuật toán chunking theo đoạn (`by_paragraph`) dựa trên cấu trúc xuống dòng đôi để phân tách chính xác các mục nội dung.

**Lỗi và giới hạn trích xuất:**
- Một số công thức toán học (ví dụ: các biểu thức ký hiệu tập hợp $D_r^{tot}$ hay $\pi(S_t)$ ở trang 5–6) khi trích xuất qua PyPDF bị mất một số ký hiệu đặc biệt.
- Các bảng benchmark (ví dụ: bảng Throughput ở trang 22–24) khi trích xuất dạng văn bản thuần có thứ tự text đan xen, cần chunking theo paragraph để gom cụm nội dung mô tả thay vì chỉ phụ thuộc vào số liệu rời rạc.

### 1.3 Metadata

Hàm `determine_metadata()` suy diễn metadata từ vị trí trang và từ khóa nội dung:

| Trường | Nguồn giá trị | Mô tả |
|---|---|---|
| `document_id` | Định danh cố định | `modyn_bother2025` |
| `source` | Tên file | `bother2025modyn.pdf` |
| `page` | Số trang PDF (1-based) | 1 → 30 |
| `section` | Suy diễn theo khoảng trang | `introduction` (tr.1–4), `system_design` (tr.5–15), `evaluation` (tr.16–24), `references` (tr.25–30) |
| `topic` | Cố định | `ml_pipeline` |
| `component` | Từ khóa văn bản | `triggering` / `data_selection` / `storage` / `trainer` / `evaluation` / `general` |

**Lý do chọn `section` làm trường lọc metadata:**
- Bài báo khoa học có cấu trúc phân chia phần rất rõ ràng giữa lý thuyết/kiến trúc (`system_design`), đánh giá thực nghiệm (`evaluation`) và tài liệu tham khảo (`references`).
- Khi người dùng hỏi về kiến trúc hay thiết kế của hệ thống, việc lọc `section: system_design` giúp loại bỏ toàn bộ các kết quả trùng lặp hoặc nhiễu từ phần đo đạc thực nghiệm hay danh mục tài liệu trích dẫn.

### 1.4 Embedding Model & Vector Store

| Thành phần | Chi tiết |
|---|---|
| Embedding model | `models/gemini-embedding-001` (Google Generative AI) |
| Provider | Google AI Studio |
| Số chiều (dimensions) | 768 (cấu hình `outputDimensionality=768`) |
| Metric khoảng cách | Cosine distance (`1 - (embedding <=> query_vec)`) |
| Vector store | PostgreSQL 16 + pgvector 0.8.7 (chạy trên Docker Compose) |
| Port & DB | `127.0.0.1:55433`, database: `day6_lab` |
| DB driver | `pg8000>=1.31.0` (thay thế cho `psycopg[binary]` do Windows App Control Policy chặn DLL) |
| Chi phí | **\$0** (Sử dụng Google AI Studio Free Tier) |
| Cơ chế Cache | Disk cache tại `starter/.cache/embeddings/` (lưu SHA-256 hash theo nội dung văn bản) |

---

## 2. Cấu hình Chiến lược và Benchmark

### 2.1 Ba chiến lược thử nghiệm

| Tham số | Strategy A (Fixed) | Strategy B (Paragraph) | Strategy C (Para + Metadata Filter) |
|---|---|---|---|
| Phương pháp | Fixed-size sliding window | Structure-aware by paragraph | Structure-aware by paragraph + Filter |
| Cỡ chunk | 500 ký tự | Tối đa 500 ký tự / đoạn | Tối đa 500 ký tự / đoạn |
| Overlap | 50 ký tự | 0 (ranh giới tự nhiên) | 0 (ranh giới tự nhiên) |
| Lọc truy vấn | Không | Không | JSONB filter (`metadata @> :filter_json`) |
| Số chunks | 265 | 283 | 283 (dùng chung index với B) |
| Thời gian index | 3.75s (cache hit) | 4.31s (cache hit) | Không tốn thời gian index riêng |
| **Khác biệt duy nhất B→C** | — | — | **Chỉ áp dụng metadata filter lúc truy vấn**; toàn bộ vector và index kế thừa từ B |

### 2.2 Benchmark Dataset

- **Tổng số câu:** 20 câu (q01 đến q20)
- **Phân chia split (cố định trước khi chạy benchmark):**
  - **Dev set:** 15 câu (q01 – q15) dùng để quan sát và lựa chọn chiến lược
  - **Test set:** 5 câu (q16 – q20) chỉ đánh giá 1 lần để kiểm chứng tính tổng quát
- **Số câu có filter:** 7 câu (q03, q05, q08, q12 ở dev; q16, q17, q19 ở test)
- **Kiểm chứng Evidence:** Mỗi câu hỏi đều được gán `gold_page` và `evidence_quote` trích xuất trực tiếp từ văn bản trang PDF tương ứng. Tiêu chí xác định "hit" yêu cầu chunk tìm được phải thuộc đúng trang `gold_page` và chứa chuỗi `evidence_quote` (hoặc tối thiểu 80% tập từ khóa của trích dẫn).

**Tiêu chí chọn chiến lược trước khi xem Test:**
> Chọn chiến lược có **Hit@1 và Hit@3 trên Dev set cao nhất**, đồng thời đạt **100% Filter compliance**. Strategy B và C vượt trội hơn A ở Dev Hit@1 (53.33% vs 33.33%) và Dev Hit@3 (66.67% vs 60.0%). Strategy C được chọn chính thức vì kế thừa chất lượng retrieval của B và bổ sung khả năng lọc chính xác 100% phạm vi ngữ cảnh.

---

## 3. Kết quả Thực nghiệm

### 3.1 Bảng kết quả định lượng (Quantitative Benchmark)

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian index | Chi phí |
|---|---|---|---|---|---|---|
| **A (Fixed 500/50)** | Dev | 5/15 (33.33%) | 9/15 (60.00%) | 265 | 3.75s | \$0 |
| **A (Fixed 500/50)** | Test | 1/5 (20.00%) | 3/5 (60.00%) | 265 | — | \$0 |
| **B (Paragraph max 500)** | Dev | **8/15 (53.33%)** | **10/15 (66.67%)** | 283 | 4.31s | \$0 |
| **B (Paragraph max 500)** | Test | 1/5 (20.00%) | 3/5 (60.00%) | 283 | — | \$0 |
| **C (Para + Filter)** | Dev | **8/15 (53.33%)** | **10/15 (66.67%)** | 283 | — | \$0 |
| **C (Para + Filter)** | Test | 1/5 (20.00%) | 3/5 (60.00%) | 283 | — | \$0 |

*Ghi chú:*
- Filter compliance trên Dev: Strategy A đạt 3/4 (75.0%), Strategy B đạt 3/4 (75.0%), còn **Strategy C đạt 4/4 (100.0%)**.
- Filter compliance trên Test: Cả 3 chiến lược đều đạt 3/3 (100.0%).
- Filter compliance Overall (toàn bộ 7 câu có filter): Strategy A và B đạt 6/7 (85.71%), trong khi **Strategy C đạt tuyệt đối 7/7 (100.0%)**, chứng minh hiệu quả loại trừ triệt để của cơ chế lọc metadata JSONB.

### 3.2 Bảng đánh giá thủ công 5 khía cạnh

| Strategy | Coherence trung bình /2 (10 mẫu) | Metadata đủ và đúng (15 hits) | Filter tuân thủ (3 câu test) | Grounding: Số câu đạt 0 / 1 / 2 | Grounding trung bình /2 |
|---|---|---|---|---|---|
| **Strategy A (Fixed)** | 1.20 / 2.0 | 15/15 (100%) | 3/3 (100%) | 6 / 5 / 4 | 0.87 / 2.0 |
| **Strategy B (Paragraph)** | **2.00 / 2.0** | 15/15 (100%) | 3/3 (100%) | 5 / 5 / 5 | 1.00 / 2.0 |
| **Strategy C (Para + Filter)** | **2.00 / 2.0** | 15/15 (100%) | 3/3 (100%) | **3 / 4 / 8** | **1.33 / 2.0** |

**Chi tiết nguồn minh chứng & đường dẫn:**
- Traces chi tiết: `starter/results/traces_strategy_a.json`, `traces_strategy_b.json`, `traces_strategy_c.json`
- Đánh giá độ mạch lạc: `artifacts/coherence_evaluation.json` (10 vị trí trang: 1, 3, 5, 8, 10, 12, 14, 17, 20, 24)
- Kiểm tra metadata: `artifacts/metadata_check.json` (kiểm tra đầy đủ 5 trường `source, page, section, topic, component`)
- Đánh giá Grounding: `artifacts/grounding_evaluation.json` (chấm điểm top-3 hits của 5 câu test q16–q20)

---

## 4. Phân tích và Kết luận

### 4.1 So sánh Chiến lược A – B và B – C

1. **So sánh A (Fixed) và B (Paragraph):**
   - **Độ chính xác truy xuất:** B vượt trội rõ rệt trên Dev set: Hit@1 tăng từ 33.33% lên **53.33%** (+20%), Hit@3 tăng từ 60.0% lên **66.67%**.
   - **Tính mạch lạc (Coherence):** B đạt điểm tuyệt đối **2.00/2.0**, trong khi A chỉ đạt **1.20/2.0**. Strategy A với cửa sổ trượt 500 ký tự cố định thường xuyên cắt ngang câu giữa chừng hoặc cắt rời rạc các bảng/hình ảnh, dẫn đến việc mất ngữ cảnh hoàn chỉnh. Ngược lại, Strategy B bảo toàn nguyên vẹn đoạn văn (paragraph) theo cấu trúc ngữ nghĩa tự nhiên của bài báo.
   - **Số lượng chunk:** B tạo ra 283 chunks so với 265 chunks của A (+6.8%), đây là mức tăng kích thước lưu trữ không đáng kể so với lợi ích thu được về độ chính xác và tính mạch lạc.

2. **So sánh B (Paragraph) và C (Para + Filter):**
   - Mặc dù Hit@1 và Hit@3 trên tập test bằng nhau (do tập test chỉ có 5 câu), nhưng chất lượng Grounding của Strategy C vượt trội rõ rệt: **1.33/2.0** so với **1.00/2.0** của Strategy B.
   - Strategy C có **8/15 hits đạt điểm 2 tuyệt đối** (đầy đủ bằng chứng và traceable), trong khi B chỉ có 5 hits. Việc áp dụng metadata filter `section: system_design` giúp loại bỏ hoàn toàn các đoạn văn nhắc đến tên thuật toán ở phần đánh giá thực nghiệm (Section 7) mà tập trung chính xác vào phần định nghĩa lý thuyết và thiết kế kiến trúc (Section 4 & 5).

### 4.2 Hai ví dụ sai điển hình

- **Ví dụ 1 — Câu q04 (Dev): "What triggering policy types does Modyn support according to the experiments on yearbook?"**
  - *Nguồn gold:* Trang 20, Figure 12 legend (Time, Drift, Amount, Performance).
  - *Kết quả sai của Strategy A:* Top-1 và Top-2 trả về các chunk ở trang 9 và trang 10 (phần mô tả lý thuyết của Triggering Policies) thay vì trang 20 (phần thực nghiệm trên yearbook). Nguyên nhân là do từ khóa "triggering policies" xuất hiện với mật độ rất cao ở phần lý thuyết, khiến vector tương đồng ngữ nghĩa thiên về các trang giới thiệu tổng quát.
  - *Khắc phục:* Bổ sung metadata cấp con `experiment_dataset: yearbook` để lọc chính xác ngữ cảnh thực nghiệm.

- **Ví dụ 2 — Câu q19 (Test): "What models does Modyn ship with out of the box?"**
  - *Nguồn gold:* Trang 15, Section 5.4.1 (Trainer Server): "Modyn comes with some models (e.g., ResNets, DLRM, and transformers)".
  - *Kết quả ở Strategy A:* Hit top-1 rơi vào trang 16 (Section 7 - Evaluation setup: ResNet50, DLRM) nhưng thiếu mất model `transformers`.
  - *Kết quả ở Strategy C:* Nhờ có filter `section: system_design`, kết quả loại bỏ trang 16 và trả về chính xác đoạn văn ở Section 5.4.1 trên trang 15, bao gồm đầy đủ cả ResNets, DLRM và transformers.

### 4.3 Chiến lược được chọn và đánh đổi

- **Chiến lược được chọn:** **Strategy C (Paragraph Chunking + Metadata Filter)**.
- **Đánh đổi:**
  - *Ưu điểm:* Độ mạch lạc cao nhất (2.0/2.0), Hit@1 cao nhất (53.33%), Grounding cao nhất (1.33/2.0), đảm bảo 100% kết quả tuân thủ phạm vi bài báo.
  - *Nhược điểm / Chi phí:* Cần bước tiền xử lý để trích xuất và gán nhãn metadata phân vùng tài liệu (`section`). Nếu câu truy vấn không xác định được metadata filter, hệ thống sẽ fallback về Strategy B.
- **Điều kiện áp dụng:** Rất phù hợp với các tài liệu kỹ thuật dài, bài báo khoa học, hồ sơ thiết kế kiến trúc hệ thống — nơi thông tin được chia tách rành mạch theo các phân đoạn nội dung.

### 4.4 Hạn chế và Hướng cải tiến

1. **Hạn chế:**
   - Tập câu hỏi test gồm 5 câu là tương đối nhỏ; chỉ số Hit@1/Hit@3 trên test nhạy cảm với từng câu riêng lẻ.
   - Việc trích xuất bảng biểu bằng PyPDF chưa giữ được cấu trúc 2 chiều hoàn hảo, các số liệu trong bảng Throughput (trang 22) bị xếp thành các dòng liên tiếp.
2. **Hướng cải tiến nếu làm lại hoặc mở rộng:**
   - Ứng dụng thư viện chuyên dụng như `pdfplumber` hoặc `marker` để trích xuất bảng biểu thành định dạng Markdown table.
   - Thử nghiệm mô hình reranker (Cross-Encoder) đối với top-10 candidates trước khi trả về top-3 để tăng thêm Hit@1.
   - Bổ sung trích xuất tự động các phần mục lục (TOC / Headings) để phân cấp metadata tự động ở mức độ chi tiết hơn (tiểu mục 5.1, 5.2, 5.3,...).

---

## 5. Hướng dẫn Tái hiện Kết quả (Reproduction Steps)

```powershell
# 1. Clone repo và vào thư mục starter
cd starter

# 2. Khởi động PostgreSQL + pgvector qua Docker
docker compose -p day6_student_starter up -d --wait

# 3. Kích hoạt môi trường và kiểm tra kết nối
.venv\Scripts\Activate.ps1
python scripts\check_setup.py

# 4. Chạy toàn bộ pipeline ingestion, chunking, embedding và benchmark
python -m src.run

# 5. Sinh các file đánh giá thủ công
python scripts\generate_manual_evaluations.py
```
