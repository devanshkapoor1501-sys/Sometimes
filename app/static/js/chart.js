(function renderPriceChart() {
  const chartData = window.chartData;
  const canvas = document.getElementById('priceChart');
  if (!chartData || !canvas || !chartData.values?.length) return;

  new Chart(canvas, {
    type: 'line',
    data: {
      labels: chartData.labels,
      datasets: [
        {
          label: 'Close Price',
          data: chartData.values,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.16)',
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.25,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
      },
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { ticks: { maxTicksLimit: 10 } },
      },
    },
  });
})();
