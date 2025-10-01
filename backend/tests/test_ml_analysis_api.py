import uuid
import pytest
from fastapi.testclient import TestClient
from main import app
import os
import hmac, hashlib, time


def test_create_list_ml_analysis_flow(client):
    # Create project
    proj_resp = client.post("/api/projects/", json={
        "name": "Test Project",
        "description": "Desc",
        "meta_group_id": "data-scientists"
    })
    assert proj_resp.status_code == 201, proj_resp.text
    project = proj_resp.json()

    # Upload image (simplified using text file as image placeholder)
    files = {
        'file': ('test.png', b'\x89PNG\r\n', 'image/png')
    }
    data = { 'metadata': '{}'}
    img_resp = client.post(f"/api/projects/{project['id']}/images", files=files, data=data)
    assert img_resp.status_code == 201, img_resp.text
    image = img_resp.json()

    # Create analysis
    analysis_payload = {
        "image_id": image['id'],
        "model_name": "resnet50_classifier",
        "model_version": "1.0.0",
        "parameters": {"topk": 3}
    }
    a_resp = client.post(f"/api/images/{image['id']}/analyses", json=analysis_payload)
    assert a_resp.status_code == 201, a_resp.text
    analysis = a_resp.json()
    assert analysis['model_name'] == 'resnet50_classifier'
    assert analysis['status'] == 'queued'

    # List analyses
    list_resp = client.get(f"/api/images/{image['id']}/analyses")
    assert list_resp.status_code == 200
    data_list = list_resp.json()
    assert data_list['total'] == 1
    assert data_list['analyses'][0]['id'] == analysis['id']

    # Get single analysis detail
    detail_resp = client.get(f"/api/analyses/{analysis['id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail['id'] == analysis['id']
    assert detail['annotations'] == []


def test_annotations_list_and_limit_and_status_flow(client):
    # Create project
    proj_resp = client.post("/api/projects/", json={
        "name": "P2",
        "description": "Desc",
        "meta_group_id": "data-scientists"
    })
    assert proj_resp.status_code == 201
    project = proj_resp.json()

    # Upload image
    files = {'file': ('test2.png', b'\x89PNG\r\n', 'image/png')}
    img_resp = client.post(f"/api/projects/{project['id']}/images", files=files, data={'metadata': '{}'})
    assert img_resp.status_code == 201
    image = img_resp.json()

    # Create up to limit
    limit = 3  # use a smaller temp limit via env? current default is 10, we'll just create 3
    for i in range(limit):
        payload = {
            "image_id": image['id'],
            "model_name": "resnet50_classifier",
            "model_version": f"1.0.{i}",
            "parameters": {"k": i}
        }
        r = client.post(f"/api/images/{image['id']}/analyses", json=payload)
        assert r.status_code == 201, r.text

    # List analyses (should be == limit)
    list_resp = client.get(f"/api/images/{image['id']}/analyses")
    assert list_resp.status_code == 200
    data_list = list_resp.json()
    assert data_list['total'] == limit

    analysis_id = data_list['analyses'][0]['id']

    # Status transitions: queued -> processing -> completed
    proc_resp = client.patch(f"/api/analyses/{analysis_id}/status", json={"status": "processing"})
    assert proc_resp.status_code == 200, proc_resp.text
    comp_resp = client.patch(f"/api/analyses/{analysis_id}/status", json={"status": "completed"})
    assert comp_resp.status_code == 200, comp_resp.text

    # Illegal transition (completed -> queued) should 409
    bad_resp = client.patch(f"/api/analyses/{analysis_id}/status", json={"status": "queued"})
    assert bad_resp.status_code == 409

    # Annotations list (empty)
    ann_list = client.get(f"/api/analyses/{analysis_id}/annotations")
    assert ann_list.status_code == 200
    ann_payload = ann_list.json()
    assert ann_payload['total'] == 0


def test_feature_flag_off_returns_404(client, monkeypatch):
    # Temporarily disable flag (monkeypatch environment & settings attr if possible)
    from core import config as cfg
    original = cfg.settings.ML_ANALYSIS_ENABLED
    cfg.settings.ML_ANALYSIS_ENABLED = False  # type: ignore
    try:
        # Attempt list (random UUID)
        resp = client.get(f"/api/images/{uuid.uuid4()}/analyses")
        assert resp.status_code == 404
    finally:
        cfg.settings.ML_ANALYSIS_ENABLED = original  # restore


def _hmac_headers(body: bytes, secret: str):
    ts = str(int(time.time()))
    mac = hmac.new(secret.encode('utf-8'), msg=(ts.encode('utf-8') + b'.' + body), digestmod=hashlib.sha256)
    return {
        'X-ML-Timestamp': ts,
        'X-ML-Signature': 'sha256=' + mac.hexdigest()
    }


def test_phase2_bulk_and_finalize_flow(client, monkeypatch):
    from core import config as cfg
    # Ensure secret is set on settings and environment (some code paths may re-read env on reload in future)
    cfg.settings.ML_CALLBACK_HMAC_SECRET = 'secret123'  # type: ignore
    os.environ['ML_CALLBACK_HMAC_SECRET'] = 'secret123'
    cfg.settings.ML_PIPELINE_REQUIRE_HMAC = True  # type: ignore

    # Create project & image & analysis
    proj = client.post('/api/projects/', json={"name":"P3","description":"d","meta_group_id":"data-scientists"}).json()
    img = client.post(f"/api/projects/{proj['id']}/images", files={'file': ('f.png', b'\x89PNG\r\n', 'image/png')}, data={'metadata':'{}'}).json()
    analysis = client.post(f"/api/images/{img['id']}/analyses", json={"image_id": img['id'], "model_name":"resnet50_classifier","model_version":"1","parameters":{}}).json()

    # Presign artifact
    presign_body = {"artifact_type":"heatmap","filename":"heat.png"}
    import json as _json
    headers = _hmac_headers(_json.dumps(presign_body).encode('utf-8'), cfg.settings.ML_CALLBACK_HMAC_SECRET)
    pre = client.post(f"/api/analyses/{analysis['id']}/artifacts/presign", json=presign_body, headers=headers)
    assert pre.status_code == 200, pre.text

    # Bulk annotations
    ann_body = {"annotations":[{"annotation_type":"classification","class_name":"cat","confidence":0.9,"data":{"score":0.9}}]}
    headers = _hmac_headers(_json.dumps(ann_body).encode('utf-8'), cfg.settings.ML_CALLBACK_HMAC_SECRET)
    bulk = client.post(f"/api/analyses/{analysis['id']}/annotations:bulk", json=ann_body, headers=headers)
    assert bulk.status_code == 200, bulk.text
    assert bulk.json()['total'] == 1

    # Finalize (completed)
    fin_body = {"status":"completed"}
    headers = _hmac_headers(_json.dumps(fin_body).encode('utf-8'), cfg.settings.ML_CALLBACK_HMAC_SECRET)
    fin = client.post(f"/api/analyses/{analysis['id']}/finalize", json=fin_body, headers=headers)
    assert fin.status_code == 200, fin.text
    assert fin.json()['status'] == 'completed'

    # Bad HMAC
    bad = client.post(f"/api/analyses/{analysis['id']}/annotations:bulk", json=ann_body, headers={'X-ML-Timestamp':'0','X-ML-Signature':'sha256=deadbeef'})
    assert bad.status_code in (401, 404)  # 404 if feature disabled, else 401
