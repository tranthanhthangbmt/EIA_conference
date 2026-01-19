// Dữ liệu mô phỏng kết quả cuối cùng (End-state Data)
// Trong thực tế, bạn có thể truyền biến từ index.html sang đây
const finalData = {
    efa: {
        mastery: 890,
        sustain: 4.2, // Mastery / Stress
        burnouts: 4,
        happiness: -150,
        efficiency: 0.65,
        stability: 0.3
    },
    bio: {
        mastery: 945,
        sustain: 15.8, // Cao hơn nhiều
        burnouts: 0,
        happiness: 320,
        efficiency: 0.98,
        stability: 0.9
    }
};

// Hàm khởi tạo báo cáo
function initDashboard() {
    renderKPIs();
    renderRadarChart();
}

function renderKPIs() {
    // 1. Mastery
    document.getElementById('kpi-mastery').innerHTML =
        `<span style="color:#44cc44">${finalData.bio.mastery}</span> <span style="font-size:0.5em; color:#666">vs ${finalData.efa.mastery}</span>`;
    let diffMastery = finalData.bio.mastery - finalData.efa.mastery;
    document.getElementById('delta-mastery').innerHTML =
        `<span class="delta-positive">▲ +${diffMastery} pts (+${((diffMastery / finalData.efa.mastery) * 100).toFixed(1)}%)</span>`;

    // 2. Sustainability Index (ROI)
    document.getElementById('kpi-sustain').innerHTML = finalData.bio.sustain.toFixed(1);
    document.getElementById('delta-sustain').innerHTML =
        `<span class="delta-positive">▲ 3.7x Higher Efficiency</span>`;

    // 3. Burnout
    document.getElementById('kpi-burnout').innerHTML = finalData.bio.burnouts;
    document.getElementById('delta-burnout').innerHTML =
        `<span class="delta-positive">▼ Eliminated (${finalData.efa.burnouts} in Baseline)</span>`;

    // 4. Happiness
    document.getElementById('kpi-happy').innerHTML = finalData.bio.happiness;
    document.getElementById('delta-happy').innerHTML =
        `<span class="delta-positive">▲ Huge Improvement</span>`;
}

function renderRadarChart() {
    const ctx = document.getElementById('finalRadarChart').getContext('2d');
    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Total Mastery', 'Energy Efficiency', 'Emotional Stability', 'Sustainability', 'Burnout Resistance'],
            datasets: [{
                label: 'Bio-PKT (Proposed)',
                data: [95, 98, 90, 100, 100], // Normalized scores (0-100)
                backgroundColor: 'rgba(68, 204, 68, 0.4)',
                borderColor: '#44cc44',
                pointBackgroundColor: '#44cc44'
            }, {
                label: 'EFA (Baseline)',
                data: [89, 65, 30, 40, 20], // EFA yếu ở các chỉ số bền vững
                backgroundColor: 'rgba(255, 68, 68, 0.4)',
                borderColor: '#ff4444',
                pointBackgroundColor: '#ff4444'
            }]
        },
        options: {
            scales: {
                r: {
                    angleLines: { color: '#444' },
                    grid: { color: '#444' },
                    pointLabels: { color: '#ccc', font: { size: 12 } },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            },
            plugins: {
                legend: { labels: { color: '#fff' } }
            }
        }
    });
}

// Chạy khi load trang
window.onload = initDashboard;
