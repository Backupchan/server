from dataclasses import dataclass
from backupchan_server import models

@dataclass
class SearchQuery:
    name: str | None
    target_type: models.BackupType | None
    recycle_criteria: models.BackupRecycleCriteria | None
    recycle_action: models.BackupRecycleAction | None
    location: str | None
    name_template: str | None
    deduplicate: bool | None
    alias: str | None
    tags: list[str] | None

    def sql(self) -> tuple[str, list[any]]:
        conditions = []
        values = []

        if self.name:
            conditions.append("name LIKE %s")
            values.append(f"%{self.name}%")

        if self.target_type:
            conditions.append("type = %s")
            values.append(self.target_type)

        if self.recycle_criteria:
            conditions.append("recycle_criteria = %s")
            values.append(self.recycle_criteria)

        if self.recycle_action:
            conditions.append("recycle_action = %s")
            values.append(self.recycle_action)

        if self.location:
            conditions.append("location LIKE %s")
            values.append(f"%{self.location}%")

        if self.name_template:
            conditions.append("name_template LIKE %s")
            values.append(f"%{self.name_template}%")

        if self.deduplicate is not None:
            conditions.append("deduplicate = %s")
            values.append(int(self.deduplicate))

        if self.alias:
            conditions.append("alias LIKE %s")
            values.append(f"%{self.alias}%")

        tags = [] if not self.tags else list(set(tag.strip() for tag in self.tags if tag.strip()))
        if tags:
            placeholders = ",".join(["%s"] * len(tags))
            filter_string = ("AND " + " AND ".join(["tar." + condition for condition in conditions])) if conditions else ""
            return f"SELECT tar.* FROM targets tar JOIN target_tags tt ON tar.id = tt.target_id JOIN tags t ON t.id = tt.tag_id WHERE t.name IN ({placeholders}) {filter_string} GROUP BY tar.id HAVING COUNT(DISTINCT t.name) >= %s", tags + values + [len(tags)]

        filter_string = " AND ".join(conditions)
        return f"SELECT * FROM targets WHERE {filter_string}", values
