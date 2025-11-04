const recycleValue = document.querySelector("#recycle_value");
const recycleCriteria = document.querySelector("#recycle_criteria");
const recycleAction = document.querySelector("#recycle_action");
const minBackups = document.querySelector("#min_backups")

function toggleOptions()
{
	// Disable recycle value field if no recycle criteria set
	const noRecycleCriteria = recycleCriteria.value == "none";
	recycleValue.disabled = noRecycleCriteria;
	recycleAction.disabled = noRecycleCriteria;

	// Disable min backups field if recycle criteria is not age
	minBackups.disabled = recycleCriteria.value != "age";
}

recycleCriteria.addEventListener("change", toggleOptions);

toggleOptions();
