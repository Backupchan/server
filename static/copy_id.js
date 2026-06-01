document.querySelector("#copy-id-link").addEventListener("click", ev => {
	navigator.clipboard.writeText(ev.target.dataset.targetId);
	ev.target.innerText = "Copied!";
});
