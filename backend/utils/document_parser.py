"""
文档解析工具
参考开发思路文档：第4.3节 — 数据复盘的数据源

支持：
- 图片：通过多模态模型识别数字
- CSV/TSV：pandas 读取结构化数据
- 后续可扩展：Excel、PDF

设计原则：不依赖平台API，用户自己上传截图/导出文件。
"""

import csv
import io
import logging
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class ParsedData:
    """解析后的数据结构"""
    numbers: dict = None           # 从截图/CSV提取的数据
    raw_text: str = ""            # 原始文本（调试用）
    source_type: str = ""         # "image" or "csv" or "unknown"
    errors: list = None           # 解析过程中的错误

    def __post_init__(self):
        if self.numbers is None:
            self.numbers = {}
        if self.errors is None:
            self.errors = []


def is_image_file(filename: str) -> bool:
    """判断是否为支持的图片文件"""
    ext = Path(filename).suffix.lower()
    return ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def is_csv_file(filename: str) -> bool:
    """判断是否为 CSV/TSV 文件"""
    ext = Path(filename).suffix.lower()
    return ext in {".csv", ".tsv"}


def parse_csv_content(content: str, delimiter: str = ",") -> dict:
    """
    解析 CSV 字符串内容

    将 CSV 数据转换为 flat 字典：
    - 如果 CSV 是 key-value 格式（两列），直接映射
    - 否则返回所有数值型字段

    Args:
        content: CSV 文本内容
        delimiter: 分隔符

    Returns:
        提取的数据字典 {"指标名": 数值}
    """
    result = {}
    try:
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            return result

        # 尝试 key-value 格式（2列）
        if len(rows[0]) == 2 and all(len(r) == 2 for r in rows):
            # 跳过表头：若首行 value 不是数值，视为表头行（如「指标,数值」）
            start = 0
            try:
                float(rows[0][1])
            except (ValueError, TypeError):
                start = 1
            for key, val in rows[start:]:
                key = key.strip()
                try:
                    result[key] = float(val)
                except ValueError:
                    result[key] = val
        else:
            # 多列格式：提取所有数值型字段
            header = [h.strip() for h in rows[0]]
            for row in rows[1:]:
                for i, val in enumerate(row):
                    if i < len(header):
                        try:
                            result[header[i]] = float(val.strip())
                        except (ValueError, IndexError):
                            continue

    except Exception as e:
        logger.error("CSV parse error: %s", e)

    return result


def parse_csv_file(file_path: str) -> ParsedData:
    """
    解析 CSV 文件

    Args:
        file_path: CSV 文件路径

    Returns:
        ParsedData 对象
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8-sig")
        numbers = parse_csv_content(content)
        return ParsedData(
            numbers=numbers,
            raw_text=content,
            source_type="csv",
        )
    except Exception as e:
        err = f"CSV 文件解析失败: {e}"
        logger.error(err)
        return ParsedData(source_type="csv", errors=[err])


def merge_parsed_data(*datasets: ParsedData) -> dict:
    """
    合并多个数据源（截图 + CSV）的数据

    如果同一个指标在多个来源中出现，保留先出现的值。

    Returns:
        合并后的数据字典
    """
    merged = {}
    for ds in datasets:
        if ds.numbers:
            for key, val in ds.numbers.items():
                if key not in merged:
                    merged[key] = val
    return merged
