import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class IntegrationHandler(BaseHTTPRequestHandler):
    notebook_auth = ""
    notebook_payload = {}

    def do_GET(self):
        if self.path == "/api/":
            self.send_response(200)
            self.send_header("Zotero-Server-ID", "local-server-1")
            self.send_header("Zotero-API-Version", "3")
            self.end_headers()
            return
        if self.path.startswith("/api/users/0/items"):
            body = json.dumps([{
                "key": "ZITEM1",
                "version": 12,
                "data": {
                    "itemType": "journalArticle",
                    "title": "Zotero Verified Item",
                    "creators": [{"firstName": "Li", "lastName": "Wang"}],
                    "date": "2024",
                    "publicationTitle": "Zotero Journal",
                    "DOI": "10.7777/zotero.1",
                    "url": "https://example.org/zotero",
                    "abstractNote": "Verified abstract",
                    "tags": [{"tag": "evidence"}],
                    "collections": ["COLL1"],
                },
            }]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Last-Modified-Version", "12")
            self.send_header("Zotero-Server-ID", "local-server-1")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        if not self.path.endswith("/sources:batchCreate"):
            self.send_error(404)
            return
        type(self).notebook_auth = self.headers.get("Authorization", "")
        length = int(self.headers.get("Content-Length", "0"))
        type(self).notebook_payload = json.loads(self.rfile.read(length).decode("utf-8"))
        body = json.dumps({"sources": [{"name": "source/1"}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), IntegrationHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    temp_dir = tempfile.mkdtemp(prefix="pa_integrations_")
    try:
        from core.references.domain import ReferenceSource
        from sources.notebook import LocalDocumentImporter, NotebookEnterpriseClient
        from sources.zotero import ZoteroClient

        base = f"http://127.0.0.1:{server.server_port}"
        zotero = ZoteroClient.local(base_url=base + "/api")
        connection = zotero.test_connection()
        assert connection.ok is True
        assert connection.server_id == "local-server-1"
        sync = zotero.sync_items(since=0)
        assert sync.version == 12
        assert sync.partition_id == "local:local-server-1"
        assert sync.references[0].zotero_item_key == "ZITEM1"
        assert sync.references[0].source is ReferenceSource.ZOTERO_LOCAL
        assert sync.references[0].doi == "10.7777/zotero.1"

        text_path = os.path.join(temp_dir, "notes.md")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("# Local evidence\n\nA verified local note.")
        local_record = LocalDocumentImporter().import_file(text_path)
        assert local_record.title == "notes"
        assert "verified local note" in local_record.abstract.lower()
        assert local_record.source is ReferenceSource.LOCAL_FILE

        notebook = NotebookEnterpriseClient(
            project_number="123",
            location="global",
            notebook_id="nb1",
            access_token="enterprise-token",
            endpoint=base,
        )
        response = notebook.add_text("Research note", "Grounded content")
        assert response["sources"][0]["name"] == "source/1"
        assert IntegrationHandler.notebook_auth == "Bearer enterprise-token"
        assert IntegrationHandler.notebook_payload["userContents"][0]["textContent"]["content"] == "Grounded content"
        print("INTEGRATIONS TEST OK")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

# 版本: v2.0.1 (2026-08-17) 更新: Zotero 与 Notebook 官方接入测试
