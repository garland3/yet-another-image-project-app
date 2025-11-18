import io
import uuid
import pytest
from PIL import Image


def _make_png_bytes(size=(10, 10), color=(0, 128, 255)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_create_and_list_user_annotations(client):
    # Create project
    pr = client.post("/api/projects/", json={"name": "P_annotations", "description": None, "meta_group_id": "g"})
    assert pr.status_code == 201
    pid = pr.json()["id"]

    # Upload image
    img_bytes = _make_png_bytes(size=(100, 100))
    files = {"file": ("test.png", img_bytes, "image/png")}
    ur = client.post(f"/api/projects/{pid}/images", files=files)
    assert ur.status_code == 201
    image_id = ur.json()["id"]

    # Create user annotation with bounding box
    annotation_data = {
        "annotation_type": "bounding_box",
        "label": "test object",
        "data": {
            "x_min": 10,
            "y_min": 20,
            "x_max": 50,
            "y_max": 60,
            "image_width": 100,
            "image_height": 100
        }
    }
    ar = client.post(f"/api/images/{image_id}/annotations", json=annotation_data)
    assert ar.status_code == 201, ar.text
    body = ar.json()
    assert body["image_id"] == image_id
    assert body["label"] == "test object"
    assert body["annotation_type"] == "bounding_box"
    assert body["created_by_id"] is not None
    assert body["data"]["x_min"] == 10
    annotation_id = body["id"]

    # List annotations for the image
    lr = client.get(f"/api/images/{image_id}/annotations")
    assert lr.status_code == 200
    list_body = lr.json()
    assert "annotations" in list_body
    assert list_body["total"] >= 1
    assert len(list_body["annotations"]) >= 1


def test_get_user_annotation(client):
    # Create project and image
    pr = client.post("/api/projects/", json={"name": "P_get_annotation", "description": None, "meta_group_id": "g"})
    assert pr.status_code == 201
    pid = pr.json()["id"]

    img_bytes = _make_png_bytes()
    files = {"file": ("test.png", img_bytes, "image/png")}
    ur = client.post(f"/api/projects/{pid}/images", files=files)
    assert ur.status_code == 201
    image_id = ur.json()["id"]

    # Create annotation
    annotation_data = {
        "annotation_type": "bounding_box",
        "label": "car",
        "data": {"x_min": 0, "y_min": 0, "x_max": 10, "y_max": 10, "image_width": 100, "image_height": 100}
    }
    ar = client.post(f"/api/images/{image_id}/annotations", json=annotation_data)
    assert ar.status_code == 201
    annotation_id = ar.json()["id"]

    # Get specific annotation
    gr = client.get(f"/api/annotations/{annotation_id}")
    assert gr.status_code == 200
    body = gr.json()
    assert body["id"] == annotation_id
    assert body["label"] == "car"


def test_update_user_annotation(client):
    # Create project and image
    pr = client.post("/api/projects/", json={"name": "P_update_annotation", "description": None, "meta_group_id": "g"})
    assert pr.status_code == 201
    pid = pr.json()["id"]

    img_bytes = _make_png_bytes()
    files = {"file": ("test.png", img_bytes, "image/png")}
    ur = client.post(f"/api/projects/{pid}/images", files=files)
    assert ur.status_code == 201
    image_id = ur.json()["id"]

    # Create annotation
    annotation_data = {
        "annotation_type": "bounding_box",
        "label": "old label",
        "data": {"x_min": 0, "y_min": 0, "x_max": 10, "y_max": 10, "image_width": 100, "image_height": 100}
    }
    ar = client.post(f"/api/images/{image_id}/annotations", json=annotation_data)
    assert ar.status_code == 201
    annotation_id = ar.json()["id"]

    # Update annotation
    update_data = {
        "label": "new label",
        "data": {"x_min": 5, "y_min": 5, "x_max": 15, "y_max": 15, "image_width": 100, "image_height": 100}
    }
    patch_r = client.patch(f"/api/annotations/{annotation_id}", json=update_data)
    assert patch_r.status_code == 200
    body = patch_r.json()
    assert body["label"] == "new label"
    assert body["data"]["x_min"] == 5


def test_delete_user_annotation(client):
    # Create project and image
    pr = client.post("/api/projects/", json={"name": "P_delete_annotation", "description": None, "meta_group_id": "g"})
    assert pr.status_code == 201
    pid = pr.json()["id"]

    img_bytes = _make_png_bytes()
    files = {"file": ("test.png", img_bytes, "image/png")}
    ur = client.post(f"/api/projects/{pid}/images", files=files)
    assert ur.status_code == 201
    image_id = ur.json()["id"]

    # Create annotation
    annotation_data = {
        "annotation_type": "bounding_box",
        "label": "to delete",
        "data": {"x_min": 0, "y_min": 0, "x_max": 10, "y_max": 10, "image_width": 100, "image_height": 100}
    }
    ar = client.post(f"/api/images/{image_id}/annotations", json=annotation_data)
    assert ar.status_code == 201
    annotation_id = ar.json()["id"]

    # Delete annotation
    dr = client.delete(f"/api/annotations/{annotation_id}")
    assert dr.status_code == 204

    # Verify it's deleted
    gr = client.get(f"/api/annotations/{annotation_id}")
    assert gr.status_code == 404


def test_annotation_without_label(client):
    # Create project and image
    pr = client.post("/api/projects/", json={"name": "P_no_label", "description": None, "meta_group_id": "g"})
    assert pr.status_code == 201
    pid = pr.json()["id"]

    img_bytes = _make_png_bytes()
    files = {"file": ("test.png", img_bytes, "image/png")}
    ur = client.post(f"/api/projects/{pid}/images", files=files)
    assert ur.status_code == 201
    image_id = ur.json()["id"]

    # Create annotation without label
    annotation_data = {
        "annotation_type": "bounding_box",
        "data": {"x_min": 0, "y_min": 0, "x_max": 10, "y_max": 10, "image_width": 100, "image_height": 100}
    }
    ar = client.post(f"/api/images/{image_id}/annotations", json=annotation_data)
    assert ar.status_code == 201
    body = ar.json()
    assert body["label"] is None
