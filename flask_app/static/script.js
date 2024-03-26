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
  console.log('Selected crime for filtering:', selectedCrime);
  window.location.href = `/crimes/${selectedCrime}`; // Redirect to the route for the selected crime

}

