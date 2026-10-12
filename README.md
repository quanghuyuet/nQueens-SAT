# N-Queens

Project giải bài toán N-Queens bằng SAT, lập trình ràng buộc (CP)
và lập trình tuyến tính nguyên (ILP/MIP).

## Cấu trúc

Solver được nhóm theo **phương pháp giải**. Chương trình đo hiệu năng
và kết quả thực nghiệm nằm riêng ở thư mục gốc.

```text
nQueens-SAT-main/
├── solvers/                   # Triển khai thuật toán giải
│   ├── sat/                   # Các encoding SAT, dùng Glucose3
│   │   ├── binary.py
│   │   ├── binomial.py
│   │   ├── commander.py
│   │   ├── product.py
│   │   └── sequential.py
│   ├── cp/                    # Constraint programming
│   │   ├── cp_sat.py          # OR-Tools CP-SAT
│   │   └── cplex_cp.py        # IBM CP Optimizer qua DOcplex CP
│   └── mip/                   # Integer linear programming
│       ├── gurobi.py          # Gurobi, biến nhị phân
│       └── cplex_mip.py       # CPLEX MIP, biến nhị phân
├── benchmark/                 # Chương trình đo hiệu năng
│   ├── benchmark_sat.py        # So sánh encoding SAT bằng Glucose3
│   ├── benchmark_solvers.py    # So sánh 5 phương pháp giải
│   └── common.py               # Process, timeout, đo thời gian, in bảng
├── results/                   # Kết quả thực nghiệm
│   ├── .gitkeep               # Giữ thư mục trong Git
│   └── sat_encoding_selection.txt
├── playground.py              # Thử nghiệm thủ công
├── README.md                  # Hướng dẫn sử dụng
└── .gitignore
```

`solvers/`, các thư mục con của `solvers/` và `benchmark/` đều có
`__init__.py` để import dưới dạng Python package.

Dữ liệu và báo cáo thực nghiệm lưu tại `results/`.

## Cài thư viện

Dùng `python -m pip` để cài vào đúng Python đang chạy code.
Phần benchmark cần thêm `psutil` để dừng worker và tiến trình solver con
khi hết timeout, dùng chung cho Windows và các hệ điều hành khác:

```powershell
python -m pip install psutil
```

Chỉ cần cài thư viện solver cho phương pháp muốn sử dụng:

| Phương pháp | Lệnh cài |
| --- | --- |
| SAT | `python -m pip install python-sat` |
| CP-SAT | `python -m pip install ortools` |
| CPLEX CP | `python -m pip install docplex` và runtime CP Optimizer |
| Gurobi MIP | `python -m pip install gurobipy` |
| CPLEX MIP | `python -m pip install cplex` |

CPLEX Community Edition giới hạn 1.000 biến và 1.000 ràng buộc
([thông tin IBM](https://www.ibm.com/products/ilog-cplex-optimization-studio/pricing)).
Mô hình CPLEX MIP này có `n²` biến và `6n − 2` ràng buộc, nên bản Community
chạy được N ≤ 31. Từ N=32 cần bản CPLEX không giới hạn kích thước;
nếu vượt giới hạn, solver báo lỗi 1016 thay vì trả về `None`.

CPLEX CP cần executable `cpoptimizer` trên `PATH`. Nếu runtime được cài
ở nơi khác, đặt biến môi trường `DOCPLEX_CP_EXECUTABLE` tới đường dẫn đầy đủ
của `cpoptimizer.exe`. Thư viện DOcplex là lớp mô hình hóa, không thay thế
runtime CP Optimizer.

Ví dụ cấu hình đường dẫn runtime trong PowerShell:

```powershell
$env:DOCPLEX_CP_EXECUTABLE = 'C:\duong-dan\cpoptimizer.exe'
python -m solvers.cp.cplex_cp
```

Chi tiết về runtime và cấu hình: [tài liệu DOcplex CP của IBM](https://ibmdecisionoptimization.github.io/docplex-doc/cp/creating_model.html).

## Chạy chương trình

Chạy các lệnh từ thư mục gốc của project.

```powershell
# Giải N=8 bằng từng phương pháp
python -m solvers.sat.binary
python -m solvers.cp.cp_sat
python -m solvers.cp.cplex_cp
python -m solvers.mip.gurobi
python -m solvers.mip.cplex_mip

# Benchmark tất cả encoding SAT với N=4 và N=8
python -m benchmark.benchmark_sat --sizes 4 8 --timeout 120

# Benchmark một encoding
python -m benchmark.benchmark_sat --encodings binary --sizes 8 16

# So sánh SAT + Glucose3, CP-SAT, Gurobi, CPLEX MIP, CPLEX CP
python -m benchmark.benchmark_solvers --sizes 8 16 32 64

# Chọn encoding SAT đại diện hoặc chỉ chạy một số solver
python -m benchmark.benchmark_solvers --sizes 8 16 --sat-encoding commander
python -m benchmark.benchmark_solvers --sizes 8 16 --solvers sat cp_sat cplex_cp
```

Benchmark cũng hỗ trợ chạy trực tiếp:

```powershell
python benchmark/benchmark_sat.py --sizes 4 8
python benchmark/benchmark_solvers.py --sizes 4 8
```

Chạy thử nghiệm thủ công bằng `python playground.py`. File này hiện dùng
encoding product với các kích thước từ N=4 đến N=512.

## Quy ước benchmark

Hai benchmark mặc định chạy N=8, 16, 32, 64, 128, 256, 512. Trong benchmark
solver, mọi phương pháp nhận cùng danh sách N. Mỗi test chạy trong một process
riêng với giới hạn **120 giây tổng thời gian**, kể cả khởi động, import và tạo
mô hình. Có thể đổi bằng `--timeout`.

| Cột | Ý nghĩa |
| --- | --- |
| Build | Tạo biến, ràng buộc, objective hoặc CNF; Gurobi bao gồm `model.update()` |
| Solve | Thời gian gọi API solve/optimize, bao gồm presolve |
| Total | Từ lúc khởi động process tới khi nhận kết quả hoặc hết deadline |
| Status | `SAT`, `UNSAT`, `TIMEOUT` hoặc `ERROR` |
| Vars / Clauses | Chỉ có trong benchmark SAT, tính cả biến phụ |

Tất cả thời gian tính bằng giây. `Total` còn bao gồm import, thiết lập solver,
license, khởi tạo môi trường/container MIP, nạp CNF và truyền kết quả;
vì vậy có thể lớn hơn `Build + Solve`. Với CP Optimizer, thời gian Solve
bao gồm chuyển mô hình sang CPO, khởi động runtime và lấy kết quả.
Benchmark chỉ lấy trạng thái, không đo chuyển nghiệm thành ma trận hay in bàn cờ.

`--` nghĩa là chưa tới hoặc chưa hoàn tất giai đoạn đo. Nếu một giai đoạn lỗi,
thời gian đã chạy trong giai đoạn đó vẫn được ghi. Thiếu thư viện, lỗi license
hoặc runtime được báo `ERROR` kèm nguyên nhân; các test còn lại tiếp tục chạy.
Khi timeout, worker và các process native con được dừng. Bảng chỉ in ra terminal,
chưa xuất CSV.

### Encoding SAT đại diện

`benchmark_sat.py` đề xuất encoding có tổng `Build + Solve` thấp nhất trong
những encoding hoàn tất mọi N của lần chạy. Không xếp hạng encoding có
`TIMEOUT` hoặc `ERROR`. Chi phí khởi động process và đếm biến không nằm trong
tiêu chí chọn này.

Mặc định `benchmark_solvers.py` dùng **commander**, được chọn từ một lần đo
N=8, 16, 32, 64 trên máy hiện tại. Kết quả lưu tại
[`results/sat_encoding_selection.txt`](results/sat_encoding_selection.txt):

| Encoding | Tổng Build + Solve (giây, xấp xỉ) | Kết quả |
| --- | --- | --- |
| commander | 0.4635 | Hoàn tất cả 4 N |
| binomial | 0.8182 | Hoàn tất cả 4 N |
| binary | 1.2556 | Hoàn tất cả 4 N |
| product | — | TIMEOUT tại N=32 |
| sequential | — | TIMEOUT tại N=64 |

Đây là lựa chọn theo mẫu đo, không phải khẳng định tốt nhất cho mọi N hoặc
mọi máy. Chạy lại benchmark SAT cho bộ N cần nghiên cứu rồi truyền encoding
được đề xuất bằng `--sat-encoding`. Lần chạy SAT mới không tự thay đổi mặc định
trong code.

## Giao diện solver

Mỗi solver cung cấp `solve_n_queens(n)`:

- `n` là số nguyên dương.
- Kết quả là ma trận `n × n` gồm `0/1`; ô có hậu mang giá trị `1`.
- Trả về `None` nếu bài toán vô nghiệm.
- Lỗi thư viện, giấy phép hoặc solver được báo bằng exception.

```python
from solvers.sat.binary import solve_n_queens

board = solve_n_queens(8)
```

Để dùng phương pháp khác, import hàm từ `solvers.cp.cp_sat`, `solvers.cp.cplex_cp`
hoặc `solvers.mip.gurobi`, `solvers.mip.cplex_mip`.
