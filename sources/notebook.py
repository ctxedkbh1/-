import json
import os
from pathlib import Path

import requests

from core.references.domain import ReferenceRecord, ReferenceSource
from core.references.importers import import_csl_json, import_text


class LocalDocumentImporter:
    def import_file(self, path: str) -> ReferenceRecord:
        file_path = os.path.abspath(path)
        if not os.path.isfile(file_path):
            raise LocalImportError(f"文件不存在: {file_path}")
        suffix = Path(file_path).suffix.lower()
        if suffix in {".txt", ".md"}:
            content = _read_text(file_path)
            return _local_record(file_path, content)
        if suffix == ".docx":
            from docx import Document

            document = Document(file_path)
            content = "\n".join(paragraph.text for paragraph in document.paragraphs)
            return _local_record(file_path, content)
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:
                raise LocalImportError("未安装 pypdf，无法读取 PDF") from exc
            reader = PdfReader(file_path)
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
            return _local_record(file_path, content)
        if suffix in {".ris", ".bib"}:
            records = import_text(_read_text(file_path))
            if not records:
                raise LocalImportError("未从文献文件中解析到记录")
            return records[0]
        if suffix == ".json":
            records = import_csl_json(_read_text(file_path))
            if not records:
                raise LocalImportError("未从 CSL JSON 中解析到记录")
            return records[0]
        raise LocalImportError(f"不支持的本地文件类型: {suffix}")


class NotebookEnterpriseClient:
    def __init__(self, project_number: str, location: str, notebook_id: str,
                 access_token: str, endpoint: str = ""):
        self.project_number = project_number
        self.location = location
        self.notebook_id = notebook_id
        self.access_token = access_token
        self.endpoint = endpoint.rstrip("/") or f"https://{location}-discoveryengine.googleapis.com"

    def add_text(self, source_name: str, content: str) -> dict:
        payload = {
            "userContents": [{
                "textContent": {"sourceName": source_name, "content": content},
            }]
        }
        return self._post("sources:batchCreate", payload)

    def add_web_source(self, source_name: str, url: str) -> dict:
        payload = {
            "userContents": [{
                "webContent": {"sourceName": source_name, "url": url},
            }]
        }
        return self._post("sources:batchCreate", payload)

    def _post(self, action: str, payload: dict) -> dict:
        resource = (
            f"v1alpha/projects/{self.project_number}/locations/{self.location}/"
            f"notebooks/{self.notebook_id}/{action}"
        )
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                f"{self.endpoint}/{resource}", headers=headers, json=payload, timeout=60
            )
        except requests.RequestException as exc:
            raise NotebookError(f"Notebook Enterprise 网络错误: {exc}") from exc
        if response.status_code != 200:
            raise NotebookError(f"Notebook Enterprise HTTP {response.status_code}: {response.text[:300]}")
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise NotebookError("Notebook Enterprise 响应不是有效 JSON") from exc
        return data if isinstance(data, dict) else {}


class NotebookError(RuntimeError):
    pass


class LocalImportError(ValueError):
    pass


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _local_record(path: str, content: str) -> ReferenceRecord:
    return ReferenceRecord.from_dict({
        "title": Path(path).stem,
        "abstract": content.strip(),
        "source": ReferenceSource.LOCAL_FILE.value,
        "source_path": path,
        "attachment_path": path,
        "verified": True,
    })

# 版本: v2.0.1 (2026-08-17) 更新: Notebook Enterprise 与合法本地文件导入
