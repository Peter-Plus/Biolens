from fastapi.testclient import TestClient
from biolens.api import app


def test_auth_and_project_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOLENS_TOKEN", "test-token")
    with TestClient(app) as client:
        assert client.get("/projects").status_code == 401
        headers = {"Authorization":"Bearer test-token"}
        created = client.post("/projects", headers=headers, json={"name":"Test", "path":str(tmp_path)})
        assert created.status_code == 200
        project = created.json()
        chat = client.post("/chats", headers=headers, json={"project_id":project["id"]}).json()
        detail = client.get("/chats/"+chat["id"], headers=headers).json()
        assert detail["messages"] == []
        assert client.get("/settings", headers=headers).json().get("api_key") is None


def test_invalid_project_path(monkeypatch, tmp_path):
    monkeypatch.setenv("BIOLENS_TOKEN", "")
    with TestClient(app) as client:
        result=client.post("/projects",json={"name":"missing","path":str(tmp_path/'missing')})
        assert result.status_code==400


def test_pdf_preview_and_page_bounds(monkeypatch, tmp_path):
    import pymupdf
    from biolens import api, store
    monkeypatch.setenv("BIOLENS_TOKEN", "")
    monkeypatch.setattr(api, "ARTIFACT_DIR", tmp_path)
    file=tmp_path/'report.pdf'
    doc=pymupdf.open()
    page=doc.new_page()
    page.insert_text((72,72),'BioLens report')
    doc.save(file)
    doc.close()
    with TestClient(app) as client:
        item=store.artifact('chat','run',file,'pdf')
        assert client.get('/artifacts/'+item['id']+'/preview').status_code==200
        image=client.get('/artifacts/'+item['id']+'/pages/0')
        assert image.status_code==200 and image.content.startswith(b'\x89PNG')
        assert client.get('/artifacts/'+item['id']+'/pages/1').status_code==404
