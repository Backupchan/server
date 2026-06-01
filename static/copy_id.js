// navigator.clipboard.writeText doesn't work on non-secure connections
function copyText(text) {
	const textArea = document.createElement('textarea');
	textArea.value = text;
		  
	textArea.style.position = 'fixed';
	textArea.style.left = '-999999px';
		  
	document.body.appendChild(textArea);
	textArea.focus();
	textArea.select();

	try {
		document.execCommand('copy');
	} catch (err) {
		console.error(`failed to copy text: ${err}`);
	}

	document.body.removeChild(textArea);
}


document.querySelector("#copy-id-link").addEventListener("click", ev => {
	copyText(ev.target.dataset.targetId);
	ev.target.innerText = "Copied!";
});
