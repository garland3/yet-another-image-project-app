import uuid
import pytest
from fastapi.testclient import TestClient
from main import app

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
