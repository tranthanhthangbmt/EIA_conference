// CONFIGURATION GLOBALS
const DAYS = 7;
const HOURS_PER_DAY = 10;
const TOTAL_STEPS = DAYS * HOURS_PER_DAY;
const E_MAX = 100;
const E_CRITICAL = 20; // Burnout threshold
const GAIN_HIGH = 10;
const GAIN_LOW = 4;
const RECOVERY_RATE = 15;

let chartEnergy, chartKnowledge;

// --- CORE AGENT CLASS ---
class VirtualLearner {
    constructor(strategy) {
        this.strategy = strategy; // 'GREEDY', 'FIXED', 'BIO'
        this.energy = E_MAX;
        this.knowledge = 0;
        this.burnoutTimer = 0;
        this.burnoutCount = 0;
        this.lastAction = null; // To track switching cost

        // Logs
        this.logEnergy = [];
        this.logKnowledge = [];
    }

    step(stepIndex, params) {
        // 1. Handle Burnout State
        if (this.burnoutTimer > 0) {
            this.energy = Math.min(E_MAX, this.energy + RECOVERY_RATE);
            this.burnoutTimer--;
            this.logState();
            this.lastAction = 'REST';
            return;
        }

        // 2. Determine Action based on Strategy
        let action = 'REST';

        if (this.strategy === 'GREEDY') {
            // "Straw man": Cứ học cho đến khi sập
            action = (this.energy > 0) ? 'HIGH' : 'REST';
        }
        else if (this.strategy === 'FIXED') {
            // "Pomodoro/Fixed": 2 High -> 1 Rest -> 2 Low -> 1 Rest (Loop)
            // Chu kỳ 6 giờ
            let cycle = stepIndex % 6;
            if (cycle < 2) action = 'HIGH';      // Hour 0, 1
            else if (cycle === 2) action = 'REST'; // Hour 2
            else if (cycle < 5) action = 'LOW';  // Hour 3, 4
            else action = 'REST';                // Hour 5
        }
        else if (this.strategy === 'BIO') {
            // "Bio-PKT": Sandwich Strategy
            // Nếu pin cao -> High. Pin vừa -> Low. Pin thấp (nhưng chưa sập) -> Rest chủ động
            // Safety Margin = 35%
            if (this.energy > 35) action = 'HIGH';
            else if (this.energy > E_CRITICAL + 5) action = 'LOW';
            else action = 'REST';
        }

        // 3. Calculate Costs & Gains
        let cost = 0;
        let gain = 0;

        if (action === 'HIGH') {
            cost = params.alphaHigh;
            gain = GAIN_HIGH;
        } else if (action === 'LOW') {
            cost = params.alphaLow;
            gain = GAIN_LOW;
        } else {
            cost = -RECOVERY_RATE; // Negative cost = Recovery
            gain = 0;
        }

        // --- REALISM FACTOR 1: NON-LINEAR FATIGUE ---
        // Nếu pin yếu (<50%), xả nhanh hơn (mô phỏng kiệt sức)
        if (params.nonLinear && this.energy < 50 && cost > 0) {
            let fatigueFactor = 1 + (50 - this.energy) / 50; // Max 2x drain at 0 energy
            cost *= fatigueFactor;
        }

        // --- REALISM FACTOR 2: SWITCHING COST ---
        // Nếu đổi hành động (VD: High -> Low), bị phạt năng lượng
        if (this.lastAction && this.lastAction !== action && action !== 'REST') {
            this.energy -= params.switchCost;
        }

        // --- REALISM FACTOR 3: STOCHASTIC NOISE ---
        // Điểm số dao động ngẫu nhiên
        if (gain > 0) {
            let noise = (Math.random() - 0.5) * params.noiseFactor;
            gain += noise;
        }

        // Update State
        this.energy -= cost;
        this.energy = Math.max(0, Math.min(E_MAX, this.energy)); // Clip [0, 100]
        this.knowledge += Math.max(0, gain); // Gain can't be negative
        this.lastAction = action;

        // 4. Burnout Check (Hard constraint)
        if (this.energy < E_CRITICAL && action !== 'REST') {
            this.burnoutCount++;
            this.burnoutTimer = 2; // Forced rest 2 hours
            // Penalty: Mất kiến thức của giờ vừa rồi do "sập nguồn"
            this.knowledge -= gain;
        }

        this.logState();
    }

    logState() {
        this.logEnergy.push(this.energy);
        this.logKnowledge.push(this.knowledge);
    }
}

// --- MAIN SIMULATION LOOP ---
function runSimulation() {
    // Get params from UI
    const params = {
        alphaHigh: parseFloat(document.getElementById('alphaHigh').value),
        alphaLow: parseFloat(document.getElementById('alphaLow').value),
        switchCost: parseFloat(document.getElementById('switchCost').value),
        noiseFactor: parseFloat(document.getElementById('noiseFactor').value),
        nonLinear: document.getElementById('nonLinearToggle').checked
    };

    const greedy = new VirtualLearner('GREEDY');
    const fixed = new VirtualLearner('FIXED');
    const bio = new VirtualLearner('BIO');

    for (let t = 0; t < TOTAL_STEPS; t++) {
        // Daily Reset (Sleep restores energy)
        if (t > 0 && t % HOURS_PER_DAY === 0) {
            greedy.energy = E_MAX;
            fixed.energy = E_MAX;
            bio.energy = E_MAX;
            // Reset lastAction prevents switching cost carry-over next day
            greedy.lastAction = null; fixed.lastAction = null; bio.lastAction = null;
        }

        greedy.step(t, params);
        fixed.step(t, params);
        bio.step(t, params);
    }

    updateCharts(greedy, fixed, bio);
    updateStats(greedy, fixed, bio);
}

// --- VISUALIZATION LOGIC ---
function updateStats(g, f, b) {
    document.getElementById('scoreGreedy').innerText = Math.round(g.knowledge);
    document.getElementById('burnGreedy').innerText = g.burnoutCount;

    document.getElementById('scoreFixed').innerText = Math.round(f.knowledge);
    document.getElementById('burnFixed').innerText = f.burnoutCount;

    document.getElementById('scoreBio').innerText = Math.round(b.knowledge);
    document.getElementById('burnBio').innerText = b.burnoutCount;

    // Calc Improvement vs Fixed (Strong Baseline)
    let improv = ((b.knowledge - f.knowledge) / f.knowledge) * 100;
    document.getElementById('improvementVal').innerText = (improv > 0 ? "+" : "") + improv.toFixed(1) + "%";
}

function updateCharts(g, f, b) {
    const labels = Array.from({ length: TOTAL_STEPS }, (_, i) => i);

    // --- 1. ENERGY CHART ---
    // If chart doesn't exist, create it. If it does, just update data.
    if (!chartEnergy) {
        const ctxE = document.getElementById('energyChart').getContext('2d');
        chartEnergy = new Chart(ctxE, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Greedy', data: g.logEnergy, borderColor: '#ef4444', borderWidth: 2, tension: 0.1, pointRadius: 0 },
                    { label: 'Fixed (Pomodoro)', data: f.logEnergy, borderColor: '#f59e0b', borderWidth: 2, borderDash: [5, 5], tension: 0.1, pointRadius: 0 },
                    { label: 'Bio-PKT (Ours)', data: b.logEnergy, borderColor: '#10b981', borderWidth: 2.5, tension: 0.3, pointRadius: 0 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false, // Disable animation for performance
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line', yMin: 20, yMax: 20, borderColor: 'rgba(239, 68, 68, 0.5)', borderWidth: 1, borderDash: [2, 2], label: { content: 'Burnout Threshold', enabled: true }
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
                    y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    } else {
        // Update existing chart
        chartEnergy.data.datasets[0].data = g.logEnergy;
        chartEnergy.data.datasets[1].data = f.logEnergy;
        chartEnergy.data.datasets[2].data = b.logEnergy;
        chartEnergy.update('none'); // 'none' mode prevents animation
    }

    // --- 2. KNOWLEDGE CHART ---
    if (!chartKnowledge) {
        const ctxK = document.getElementById('knowledgeChart').getContext('2d');
        chartKnowledge = new Chart(ctxK, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Greedy', data: g.logKnowledge, borderColor: '#ef4444', borderWidth: 2, pointRadius: 0 },
                    { label: 'Fixed', data: f.logKnowledge, borderColor: '#f59e0b', borderWidth: 2, borderDash: [5, 5], pointRadius: 0 },
                    { label: 'Bio-PKT', data: b.logKnowledge, borderColor: '#10b981', borderWidth: 3, pointRadius: 0 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { labels: { color: '#cbd5e1' } } },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
                    y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    } else {
        chartKnowledge.data.datasets[0].data = g.logKnowledge;
        chartKnowledge.data.datasets[1].data = f.logKnowledge;
        chartKnowledge.data.datasets[2].data = b.logKnowledge;
        chartKnowledge.update('none');
    }
}

function downloadCharts() {
    alert("Pro-tip for Reviewers: Use the browser's Screenshot tool to capture High-DPI images for your LaTeX document!");
}

// Initial Run
window.onload = runSimulation;