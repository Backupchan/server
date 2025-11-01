function getCheckboxesState(checkboxes)
{
	let sameState = true;
	checkboxes.forEach(box => {
		if (box.checked != checkboxes[0].checked) {
			sameState = false;
		}
	});
	if (sameState) {
		return checkboxes[0].checked;
	}
	return undefined; // some are checked some aren't
}

function toggleActionsBox(actionsBox, checkboxes) {
	const state = getCheckboxesState(checkboxes);
	actionsBox.style.display = state !== false ? "inline-block" : "none";
}

function updateSelectAllCheckbox(state, selectAllCheckbox) {
	if (state !== undefined) {
		selectAllCheckbox.indeterminate = false;
		selectAllCheckbox.checked = state;
	} else {
		selectAllCheckbox.indeterminate = true;
	}
}

function updateSelectedCount(selectedCount, checkboxes)
{
	let count = 0;

	checkboxes.forEach(box => {
		if (box.checked) {
			count++;
		}
	});

	if (count == 0) {
		selectedCount.innerText = "";
	} else if (count == 1) {
		selectedCount.innerText = "1 backup selected";
	} else {
		selectedCount.innerText = `${count} backups selected`;
	}
}

function updateEverything(checkboxes, selectAllCheckbox, actionsBox, selectedCount)
{
	const state = getCheckboxesState(checkboxes);
	updateSelectAllCheckbox(state, selectAllCheckbox);
	toggleActionsBox(actionsBox, checkboxes);
	updateSelectedCount(selectedCount, checkboxes);
}

function bulkEditInitialize(formId)
{
	const form = document.querySelector(`form#${formId}`);
	const checkboxes = form.querySelectorAll("td.bulk_edit_checkbox input")
	const selectAllCheckbox = form.querySelector("input.select_all_backups");
	const actionsBox = form.querySelector(".bulk_edit_actions");
	const selectedCount = actionsBox.querySelector("span.selected_count");

	selectAllCheckbox.addEventListener("change", () => {
		checkboxes.forEach(box => {
			box.checked = selectAllCheckbox.checked;
			updateEverything(checkboxes, selectAllCheckbox, actionsBox, selectedCount);
		});
	});

	checkboxes.forEach(box => {
		box.addEventListener("change", () => {
			updateEverything(checkboxes, selectAllCheckbox, actionsBox, selectedCount);
		});
	});

	// When reloading it doesn't set all checkboxes to disabled
	updateEverything(checkboxes, selectAllCheckbox, actionsBox, selectedCount);
}
