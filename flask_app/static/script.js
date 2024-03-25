document.addEventListener('DOMContentLoaded', function() {
    fetchCrimes();
});

function fetchCrimes() {
    fetch('/data')
    .then(response => response.json())
    .then(crimeData => {
        populateFilter(crimeData);
    })
    .catch(error => console.error('Error fetching crime data:', error));
}

function populateFilter(crimeData) {
    const filter = document.getElementById('crimeFilter');
    crimeData.forEach(crime => {
        let option = document.createElement('option');
        option.value = crime;
        option.textContent = crime;
        filter.appendChild(option);
    });
}

function filterCrimes() {
    const selectedCrime = document.getElementById('crimeFilter').value;
    // Now you can use `selectedCrime` to filter your data or make another fetch request
    // For demonstration, let's just log it to the console
    console.log('Selected crime for filtering:', selectedCrime);

    // Here you'd typically have logic to filter your dataset based on the selected crime
    // For now, as a placeholder, we're just logging the selected crime to the console
}
