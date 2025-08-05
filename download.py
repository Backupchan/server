import file_manager
import os
from backupchan_server import models
from werkzeug.utils import secure_filename

def get_download_path(backup: models.Backup, target: models.BackupTarget, recycle_bin_path: str, temp_save_path: str, fm: file_manager.FileManager) -> str:
    if target.target_type == models.BackupType.SINGLE:
        return file_manager.find_single_backup_file(file_manager.get_backup_fs_location(backup, target, recycle_bin_path))
    
    file_name = os.path.join(temp_save_path, secure_filename(f"{target.name}_{backup.id}.tar.xz"))
    fm.create_backup_archive(backup.id, file_name)
    return file_name
