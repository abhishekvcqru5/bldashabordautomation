// script.js - Handle Gift Upload Form

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('giftForm');
  const resultDiv = document.getElementById('result');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const folderPath = form.folderPath.value.trim();
    const giftName = form.giftName.value.trim();
    const quantity = parseInt(form.quantity.value, 10);
    const description = form.description.value.trim();

    // Simple validation
    if (!folderPath) {
      showResult('Please provide a folder path.', false);
      return;
    }
    if (isNaN(quantity) || quantity < 1) {
      showResult('Quantity must be a positive number.', false);
      return;
    }

    // TODO: Integrate with backend API to actually upload files.
    // For now we just display a success message.
    const payload = {
      folderPath,
      giftName: giftName || undefined,
      quantity,
      description: description || undefined,
    };
    console.log('Gift upload payload:', payload);

    // Simulate async operation (e.g., fetch). Replace with real endpoint when available.
    try {
      // const response = await fetch('/api/upload-gifts', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(payload),
      // });
      // const data = await response.json();
      // if (!response.ok) throw new Error(data.message || 'Upload failed');
      // showResult(`Successfully uploaded ${quantity} gift(s).`, true);
      // Simulated success:
      await new Promise(r => setTimeout(r, 500));
      showResult(`Successfully prepared upload for ${quantity} gift(s) from "${folderPath}".`, true);
    } catch (err) {
      console.error(err);
      showResult(`Error: ${err.message}`, false);
    }
  });

  function showResult(message, success) {
    resultDiv.textContent = message;
    resultDiv.style.display = 'block';
    resultDiv.style.background = success ? 'rgba(0, 128, 0, 0.15)' : 'rgba(255, 0, 0, 0.15)';
    resultDiv.style.color = success ? '#b2ffb2' : '#ffb2b2';
  }
});
