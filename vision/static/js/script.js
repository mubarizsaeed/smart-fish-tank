document.getElementById('analyze-tank').addEventListener('click', async () => {
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultDiv = document.getElementById('analysis-result');
    const button = document.getElementById('analyze-tank');
    
    loadingIndicator.style.display = 'block';
    resultDiv.innerHTML = '';
    button.disabled = true;
    button.style.opacity = '0.7';
    
    try {
        const response = await fetch('/analyze-tank');
        const data = await response.json();
        resultDiv.innerHTML = data.description;
    } catch (error) {
        resultDiv.innerHTML = 'Failed to analyze tank. Please try again.';
    } finally {
        loadingIndicator.style.display = 'none';
        button.disabled = false;
        button.style.opacity = '1';
    }
});