// Dados para o gráfico de ranking de escolas
function initRankingCharts(escolasLabels, escolasData, alunosLabels, alunosData) {
    const ctx1 = document.getElementById('escolasChart').getContext('2d');
    const ctx2 = document.getElementById('alunosChart').getContext('2d');

    const chartConfig = {
        type: 'bar',
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    };

    const escolasChart = new Chart(ctx1, {
        ...chartConfig,
        data: {
            labels: escolasLabels,
            datasets: [{
                data: escolasData,
                backgroundColor: 'rgba(78, 115, 223, 0.8)',
                borderColor: 'rgba(78, 115, 223, 1)',
                borderWidth: 1
            }]
        }
    });

    const alunosChart = new Chart(ctx2, {
        ...chartConfig,
        data: {
            labels: alunosLabels,
            datasets: [{
                data: alunosData,
                backgroundColor: 'rgba(28, 200, 138, 0.8)',
                borderColor: 'rgba(28, 200, 138, 1)',
                borderWidth: 1
            }]
        }
    });
}
