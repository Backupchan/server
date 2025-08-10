import mock_modules
import api
import serverapi
import serverconfig
import stats
import delayed_jobs
import pytest
import logging
import io
import datetime
import random
import string
from backupchan_server import models
from flask import Flask

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")

app = Flask(__name__)
app.config["TESTING"] = True
config = serverconfig.get_server_config(True) # loads default config
db = mock_modules.MockDatabase()
file_manager = mock_modules.MockFileManager(db)
server_api = serverapi.ServerAPI(db, file_manager)
stats = stats.Stats(db, file_manager)
job_manager = delayed_jobs.JobManager()
api = api.API(db, server_api, config, file_manager, stats, job_manager)
api.key = None

app.register_blueprint(api.blueprint, url_prefix="/api")

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def create_test_target() -> models.BackupTarget:
    name = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    target_type = random.choice(list(models.BackupType))
    recycle_criteria = random.choice(list(models.BackupRecycleCriteria))
    recycle_value = random.randint(0, 10)
    recycle_action = random.choice(list(models.BackupRecycleAction))
    location = "".join(random.choices(string.ascii_uppercase + string.digits, k=5)) + "/" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    name_template = "$I-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return db.add_target(name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, True, None)

def create_test_backup(target_id: str) -> models.Backup:
    return db.add_backup(target_id, False)

def test_list_targets(client):
    response = client.get("/api/target")
    assert response.status_code == 200

    data = response.get_json()
    assert "targets" in data

def test_new_target(client):
    response = client.post("/api/target", json={"name": "test", "backup_type": "single", "recycle_criteria": "none", "recycle_value": 0, "recycle_action": "recycle", "location": "/", "name_template": "test$I", "deduplicate": True, "alias": "test"})
    assert response.status_code == 201
    
    data = response.get_json()
    target = db.get_target(data["id"])
    assert target is not None

def test_new_target_bad(client):
    response = client.post("/api/target", json={})
    assert response.status_code == 400

def test_edit_target(client):
    db.reset()

    target_id = create_test_target()

    response = client.patch(f"/api/target/{target_id}", json={"name": "test23", "recycle_criteria": "count", "recycle_value": 10, "recycle_action": "delete", "location": "/var/backups/test", "name_template": "test$I-$D", "deduplicate": False, "alias": "test"})
    assert response.status_code == 200
    
    target = db.get_target(target_id)
    assert target.name == "test23"
    assert target.recycle_criteria == models.BackupRecycleCriteria.COUNT
    assert target.recycle_value == 10
    assert target.recycle_action == models.BackupRecycleAction.DELETE
    assert target.location == "/var/backups/test"
    assert target.name_template == "test$I-$D"
    assert target.alias == "test"

def test_delete_target(client):
    db.reset()
    
    target_id = create_test_target()
    
    response = client.delete(f"/api/target/{target_id}", json={"delete_files": True})
    assert response.status_code == 200
    
    target = db.get_target(target_id)
    assert target is None

def test_upload_backup(client):
    db.reset()
    
    target_id = create_test_target()
    
    response = client.post(f"/api/target/{target_id}/upload", data={"backup_file": (io.BytesIO(b"test lol"), "test.txt"), "manual": False}, content_type="multipart/form-data")
    assert response.status_code == 200
    
    backups = db.list_backups_target(target_id)
    assert len(backups) == 1

def test_delete_target_backups(client):
    db.reset()
    
    target_id = create_test_target()
    backup_id = create_test_backup(target_id)
    
    response = client.delete(f"/api/target/{target_id}/all", json={"delete_files": True})
    assert response.status_code == 200
    
    backup = db.get_backup(backup_id)
    assert backup is None

def test_delete_backup(client):
    db.reset()
    
    target_id = create_test_target()
    backup_id = create_test_backup(target_id)
    
    response = client.delete(f"/api/backup/{backup_id}", json={"delete_files": True})
    assert response.status_code == 200
    
    backup = db.get_backup(backup_id)
    assert backup is None

def test_recycle_backup(client):
    db.reset()
    
    target_id = create_test_target()
    backup_id = create_test_backup(target_id)
    
    response = client.patch(f"/api/backup/{backup_id}", json={"is_recycled": True})
    assert response.status_code == 200
    
    backup = db.get_backup(backup_id)
    assert backup.is_recycled
    
    # And now restoring it.
    
    response = client.patch(f"/api/backup/{backup_id}", json={"is_recycled": False})
    assert response.status_code == 200
    
    backup = db.get_backup(backup_id)
    assert not backup.is_recycled

def test_recycle_bin(client):
    db.reset()
    
    target_id = create_test_target()
    backup_id0 = create_test_backup(target_id)
    backup_id1 = create_test_backup(target_id)
    
    db.recycle_backup(backup_id0, True)
    db.recycle_backup(backup_id1, True)
    
    response = client.get("/api/recycle_bin")
    assert response.status_code == 200
    
    data = response.get_json()
    assert len(data["backups"]) == 2

def test_recycle_bin_clear(client):
    db.reset()

    target_id = create_test_target()
    backup_id0 = create_test_backup(target_id)
    backup_id1 = create_test_backup(target_id)
    
    db.recycle_backup(backup_id0, True)
    db.recycle_backup(backup_id1, True)
    
    response = client.delete("/api/recycle_bin", json={"delete_files": True})
    assert response.status_code == 200
    
    recycle_bin = db.list_recycled_backups()
    assert len(recycle_bin) == 0

def test_auth(client):
    db.reset()
    api.key = "kantai_collection"
    
    # With valid token
    response = client.get("/api/target", headers={"Authorization": "Bearer kantai_collection"})
    assert response.status_code == 200
    
    # With no token
    response = client.get("/api/target")
    assert response.status_code == 401
    
    # With invalid token
    response = client.get("/api/target", headers={"Authorization": "Bearer efijwefoij"})
    assert response.status_code == 403

    api.key = None

def test_stats(client):
    db.reset()

    response = client.get("/api/stats")
    assert response.status_code == 200

    data = response.get_json()
    assert "program_version" in data
    assert isinstance(data["program_version"], str)

    fields = ["total_target_size", "total_recycle_bin_size", "total_targets", "total_backups", "total_backups", "total_recycled_backups"]
    for field in fields:
        assert field in data
        assert isinstance(data[field], int)
