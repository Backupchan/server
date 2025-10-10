const recycleValue = document.querySelector("#recycle_value");
const recycleCriteria = document.querySelector("#recycle_criteria");
const recycleAction = document.querySelector("#recycle_action");

function toggleRecycleOptions()
{
	const noRecycleCriteria = recycleCriteria.value == "none";
	recycleValue.disabled = noRecycleCriteria;
	recycleAction.disabled = noRecycleCriteria;
}

recycleCriteria.addEventListener("change", toggleRecycleOptions);

toggleRecycleOptions();