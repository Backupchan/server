import mock_modules
import api
import serverapi
import serverconfig
import models
import pytest
import logging
import io
import datetime
from flask import Flask

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")

app = Flask(__name__)
app.config["TESTING"] = True
config = serverconfig.get_server_config(True)
db = mock_modules.MockDatabase()
file_manager = mock_modules.MockFileManager(db, "") # TODO no need for recycle bin path in mock
server_api = serverapi.ServerAPI(db, file_manager)
api = api.API(db, server_api, config, file_manager)

app.register_blueprint(api.blueprint, url_prefix="/api")

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_list_targets(client):
    response = client.get("/api/target")
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"]
    assert "targets" in data

def test_new_target(client):
    response = client.post("/api/target", json={"name": "test", "backup_type": "single", "recycle_criteria": "none", "recycle_value": 0, "recycle_action": "recycle", "location": "/", "name_template": "test$I"})
    assert response.status_code == 201
    
    data = response.get_json()
    assert data["success"]
    
    response = client.get(f"/api/target/{data['id']}")
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    assert "target" in data
    target = data["target"]
    assert target["name"] == "test"
    assert target["target_type"] == "single"
    assert target["recycle_criteria"] == "none"
    assert target["recycle_value"] == 0
    assert target["recycle_action"] == "recycle"
    assert target["location"] == "/"
    assert target["name_template"] == "test$I"

def test_new_target_bad(client):
    response = client.post("/api/target", json={})
    assert response.status_code == 400
    
    data = response.get_json()
    assert not data["success"]

def test_edit_target(client):
    db.reset()

    response = client.post("/api/target", json={"name": "test", "backup_type": "single", "recycle_criteria": "none", "recycle_value": 0, "recycle_action": "recycle", "location": "/", "name_template": "test$I"})
    assert response.status_code == 201
    
    data = response.get_json()
    assert data["success"]
    target_id = data["id"]

    response = client.patch(f"/api/target/{target_id}", json={"name": "test23", "recycle_criteria": "count", "recycle_value": 10, "recycle_action": "delete", "location": "/var/backups/test", "name_template": "test$I-$D"})
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    
    response = client.get(f"/api/target/{target_id}")
    assert response.status_code == 200
    
    data = response.get_json()
    assert "target" in data
    target = data["target"]
    assert target["name"] == "test23"
    assert target["recycle_criteria"] == "count"
    assert target["recycle_value"] == 10
    assert target["recycle_action"] == "delete"
    assert target["location"] == "/var/backups/test"
    assert target["name_template"] == "test$I-$D"

def test_delete_target(client):
    db.reset()
    
    response = client.post("/api/target", json={"name": "kasane testo", "backup_type": "multi", "recycle_criteria": "none", "recycle_value": 0, "recycle_action": "recycle", "location": "/a/a/a/a", "name_template": "$I$I$I$I"})
    assert response.status_code == 201
    
    data = response.get_json()
    assert data["success"]
    target_id = data["id"]
    
    response = client.delete(f"/api/target/{target_id}", json={"delete_files": True})
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    
    response = client.get(f"/api/target/{target_id}")
    assert response.status_code == 404

def test_upload_backup(client):
    db.reset()
    
    response = client.post("/api/target", json={"name": "kasane testo", "backup_type": "multi", "recycle_criteria": "none", "recycle_value": 0, "recycle_action": "recycle", "location": "/a/a/a/a", "name_template": "$I$I$I$I"})
    assert response.status_code == 201
    
    data = response.get_json()
    assert data["success"]
    target_id = data["id"]
    
    response = client.post(f"/api/target/{target_id}/upload", data={"backup_file": (io.BytesIO(b"test lol"), "test.txt"), "manual": False}, content_type="multipart/form-data")
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    
    response = client.get(f"/api/target/{target_id}")
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    assert "target" in data
    assert "backups" in data
    assert len(data["backups"]) != 0

def test_delete_target_backups(client):
    db.reset()
    
    # TODO use db directly for things other than the endpoint tested.
    #      This'll make it simpler and make all the testing focus on one thing
    #      instead of validating unrelated endpoints in every test.
    
    target_id = db.add_target("kasane testo", models.BackupType.SINGLE, models.BackupRecycleCriteria.COUNT, 10, models.BackupRecycleAction.RECYCLE, "/a/a/a/a", "test$I")
    backup_id = db.add_backup(target_id, datetime.datetime.now(), False)
    
    response = client.delete(f"/api/target/{target_id}/all", json={"delete_files": True})
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"] # TODO necessary?
    
    backup = db.get_backup(backup_id)
    assert backup is None

def test_delete_backup(client):
    db.reset()
    
    # TODO create method for making a testing target and backup
    target_id = db.add_target("kasane testo", models.BackupType.SINGLE, models.BackupRecycleCriteria.COUNT, 10, models.BackupRecycleAction.RECYCLE, "/a/a/a/a", "test$I")
    backup_id = db.add_backup(target_id, datetime.datetime.now(), False)
    
    response = client.delete(f"/api/backup/{backup_id}", json={"delete_files": True})
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    
    backup = db.get_backup(backup_id)
    assert backup is None

def test_recycle_backup(client):
    db.reset()
    
    target_id = db.add_target("kasane testo", models.BackupType.SINGLE, models.BackupRecycleCriteria.COUNT, 10, models.BackupRecycleAction.RECYCLE, "/a/a/a/a", "test$I")
    backup_id = db.add_backup(target_id, datetime.datetime.now(), False)
    
    response = client.patch(f"/api/backup/{backup_id}", json={"is_recycled": True})
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    
    backup = db.get_backup(backup_id)
    assert backup.is_recycled
    
    # And now restoring it.
    
    response = client.patch(f"/api/backup/{backup_id}", json={"is_recycled": False})
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    
    backup = db.get_backup(backup_id)
    assert not backup.is_recycled

def test_recycle_bin(client):
    db.reset()
    
    target_id = db.add_target("kasane testo", models.BackupType.SINGLE, models.BackupRecycleCriteria.COUNT, 10, models.BackupRecycleAction.RECYCLE, "/a/a/a/a", "test$I")
    backup_id0 = db.add_backup(target_id, datetime.datetime.now(), False)
    backup_id1 = db.add_backup(target_id, datetime.datetime.now(), False)
    
    db.recycle_backup(backup_id0, True)
    db.recycle_backup(backup_id1, True)
    
    response = client.get("/api/recycle_bin")
    assert response.status_code == 200
    
    data = response.get_json()
    assert len(data["backups"]) == 2

def test_recycle_bin_clear(client):
    db.reset()

    target_id = db.add_target("kasane testo", models.BackupType.SINGLE, models.BackupRecycleCriteria.COUNT, 10, models.BackupRecycleAction.RECYCLE, "/a/a/a/a", "test$I")
    backup_id0 = db.add_backup(target_id, datetime.datetime.now(), False)
    backup_id1 = db.add_backup(target_id, datetime.datetime.now(), False)
    
    db.recycle_backup(backup_id0, True)
    db.recycle_backup(backup_id1, True)
    
    response = client.delete("/api/recycle_bin", json={"delete_files": True})
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"]
    
    recycle_bin = db.list_backups_is_recycled(True)
    assert len(recycle_bin) == 0