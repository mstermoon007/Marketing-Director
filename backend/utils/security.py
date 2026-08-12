"""安全工具：路径校验等。

用于防止任意文件读取（LFI）：客户端传入的文件路径必须解析后落在
允许的上传目录内，否则拒绝。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from backend.config.settings import PROJECT_ROOT


# 允许读取的文件根目录（上传文件落盘处）；其它路径一律拒绝
UPLOAD_ROOT = (PROJECT_ROOT / "data" / "uploads").resolve()


def assert_safe_upload_path(path: str) -> str:
    """校验文件路径落在上传目录内，返回解析后的绝对路径。

    拒绝空路径、绝对路径越界、以及使用 ``..`` 的目录穿越。
    允许的相对路径按上传根目录解析后再校验。

    Raises
    ------
    HTTPException
        路径为空或解析后不在 UPLOAD_ROOT 内时返回 400。
    """
    if not path:
        raise HTTPException(status_code=400, detail="文件路径不能为空")
    p = Path(path)
    resolved = p.resolve() if p.is_absolute() else (UPLOAD_ROOT / p).resolve()
    if resolved != UPLOAD_ROOT and UPLOAD_ROOT not in resolved.parents:
        raise HTTPException(
            status_code=400,
            detail="非法文件路径：超出允许的上传目录",
        )
    return str(resolved)


def assert_safe_file_list(files: list[str] | None) -> list[str]:
    """批量校验文件列表，返回解析后的安全路径列表。"""
    if not files:
        return []
    return [assert_safe_upload_path(f) for f in files]
