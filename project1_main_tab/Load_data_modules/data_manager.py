"""
DataManager: Quản lý dữ liệu lớn (hàng trăm triệu dòng) qua DuckDB + Parquet.
"""
import duckdb
import pandas as pd
from pathlib import Path


class DataManager:
    def __init__(self, parquet_dir: Path):
        self.parquet_dir = Path(parquet_dir)
        self.conn = duckdb.connect()
        self._columns: list[str] = []
        self._date_min = None
        self._date_max = None
        self._parquet_files: list[str] = []
        self._refresh_file_list()
        self._init_metadata()

    def _refresh_file_list(self):
        """Cập nhật danh sách file Parquet thực tế trên disk."""
        self._parquet_files = [
            str(f).replace("\\", "/")
            for f in sorted(self.parquet_dir.glob("*.parquet"))
        ]

    def _read_expr(self) -> str:
        """
        Tạo biểu thức đọc Parquet dùng list file cụ thể thay vì glob.
        Tránh lỗi glob trên Windows với path có dấu cách.
        """
        if not self._parquet_files:
            raise ValueError("Không có file Parquet nào.")
        # DuckDB nhận list: read_parquet(['file1.parquet', 'file2.parquet'])
        files_str = ", ".join(f"'{f}'" for f in self._parquet_files)
        return f"read_parquet([{files_str}])"

    def _init_metadata(self):
        try:
            expr = self._read_expr()

            # Schema (tên cột) — không scan data rows
            schema_df = self.conn.execute(
                f"DESCRIBE SELECT * FROM {expr} LIMIT 0"
            ).df()
            self._columns = schema_df["column_name"].tolist()

            # Date range — đọc từ Parquet statistics
            row = self.conn.execute(
                f"SELECT MIN(Datetime), MAX(Datetime) FROM {expr}"
            ).fetchone()
            self._date_min = row[0]
            self._date_max = row[1]

        except Exception as e:
            print(f"[DataManager] Lỗi khởi tạo metadata: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_columns(self) -> list[str]:
        return self._columns

    def get_date_range(self):
        return self._date_min, self._date_max

    def query(
        self,
        start=None,
        end=None,
        columns: list[str] | None = None,
        max_rows: int | None = None,
    ) -> pd.DataFrame:
        """
        Query dữ liệu theo time range và column selection.
        Chỉ đọc đúng phần cần thiết từ Parquet (predicate + column pushdown).
        """
        try:
            expr = self._read_expr()
        except ValueError as e:
            print(f"[DataManager] {e}")
            return pd.DataFrame()

        # Column selection — luôn include Datetime
        if columns:
            cols = list(dict.fromkeys(["Datetime"] + list(columns)))
            col_expr = ", ".join(f'"{c}"' for c in cols)
        else:
            col_expr = "*"

        # Datetime params — dùng Python datetime thuần (tz-naive) cho an toàn
        conditions = []
        params = []
        if start is not None:
            ts = pd.Timestamp(start)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
            conditions.append("Datetime >= ?")
            params.append(ts.to_pydatetime())
        if end is not None:
            ts = pd.Timestamp(end)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
            conditions.append("Datetime <= ?")
            params.append(ts.to_pydatetime())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit = f"LIMIT {max_rows}" if max_rows else ""

        sql = f"""
            SELECT {col_expr}
            FROM {expr}
            {where}
            ORDER BY Datetime
            {limit}
        """

        try:
            return self.conn.execute(sql, params if params else None).df()
        except Exception as e:
            print(f"[DataManager] Lỗi query: {e}")
            print(f"  SQL: {sql[:200]}")
            return pd.DataFrame()

    def get_sample(self, n: int = 2000) -> pd.DataFrame:
        """Lấy n dòng đầu để preview."""
        try:
            expr = self._read_expr()
            return self.conn.execute(
                f"SELECT * FROM {expr} ORDER BY Datetime LIMIT {n}"
            ).df()
        except Exception as e:
            print(f"[DataManager] Lỗi get_sample: {e}")
            return pd.DataFrame()

    def count_rows(self) -> int:
        try:
            expr = self._read_expr()
            result = self.conn.execute(
                f"SELECT COUNT(*) FROM {expr}"
            ).fetchone()
            return result[0] if result else 0
        except:
            return 0

    def is_valid(self) -> bool:
        self._refresh_file_list()
        return len(self._parquet_files) > 0

    def close(self):
        try:
            self.conn.close()
        except:
            pass
