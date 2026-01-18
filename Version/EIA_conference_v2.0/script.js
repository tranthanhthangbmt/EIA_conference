// CONFIGURATION GLOBALS
const DAYS = 7;
const HOURS_PER_DAY = 10;
const TOTAL_STEPS = DAYS * HOURS_PER_DAY;
const E_MAX = 100;
const E_CRITICAL = 20;
const GAIN_HIGH = 10;
const GAIN_LOW = 4;

let chartEnergy, chartKnowledge;

// --- PHYSICS ENGINE (Mô phỏng vật lý của người học) ---
// Tách biệt vật lý ra khỏi Agent để MPC có thể dùng nó để dự báo
function simulateStep(currentState, action, params) {
    let nextState = { ...currentState }; // Clone state

    // 1. Burnout Recovery Logic
    if (nextState.burnoutTimer > 0) {
        nextState.energy = Math.min(E_MAX, nextState.energy + params.recovRate);
        nextState.burnoutTimer--;

        // Memory Decay accelerated during Burnout (3x)
        nextState.knowledge *= (1 - params.decayRate * 3);

        return { state: nextState, reward: 0 };
    }

    // 2. Action Costs & Gains
    let cost = 0;
    let gain = 0;

    if (action === 'HIGH') { cost = params.alphaHigh; gain = GAIN_HIGH; }
    else if (action === 'LOW') { cost = params.alphaLow; gain = GAIN_LOW; }
    else { cost = -params.recovRate; gain = 0; } // REST

    // Non-linear Fatigue: Pin yếu xả nhanh
    if (params.nonLinear && nextState.energy < 50 && cost > 0) {
        let fatigueFactor = 1 + (50 - nextState.energy) / 50;
        cost *= fatigueFactor;
    }

    // Switching Cost: Đổi món tốn pin
    if (nextState.lastAction && nextState.lastAction !== action && action !== 'REST') {
        nextState.energy -= params.switchCost;
    }

    // Update Energy
    nextState.energy -= cost;
    nextState.energy = Math.max(0, Math.min(E_MAX, nextState.energy));

    // 3. Knowledge Update (Gain + Decay)
    // Stochastic Noise (Removed for MPC Prediction to keep it "Expected Value")
    // But kept for real simulation step later

    // Standard Decay
    nextState.knowledge *= (1 - params.decayRate);
    nextState.knowledge += gain;

    // 4. Check Burnout (Constraint Violation)
    let penalty = 0;
    if (nextState.energy < E_CRITICAL && action !== 'REST') {
        nextState.burnoutTimer = 2; // Lockout
        nextState.knowledge -= gain; // Mất kiến thức vừa học
        penalty = 1000; // Phạt cực nặng cho hàm mục tiêu MPC
    }

    nextState.lastAction = action;

    // Reward for MPC = Gain - Penalty
    // Ta muốn tối đa hóa Gain và tránh Penalty
    let reward = gain - penalty;

    return { state: nextState, reward: reward };
}


// --- AGENT CLASS ---
class VirtualLearner {
    constructor(strategy) {
        this.strategy = strategy;
        this.state = {
            energy: E_MAX,
            knowledge: 0,
            burnoutTimer: 0,
            lastAction: null
        };

        this.logEnergy = [];
        this.logKnowledge = [];
    }

    step(stepIndex, params) {
        let action = 'REST';

        // --- STRATEGY LOGIC ---
        if (this.strategy === 'GREEDY') {
            action = (this.state.energy > 0) ? 'HIGH' : 'REST';
        }
        else if (this.strategy === 'FIXED') {
            let cycle = stepIndex % 6;
            if (cycle < 2) action = 'HIGH';
            else if (cycle === 2) action = 'REST';
            else if (cycle < 5) action = 'LOW';
            else action = 'REST';
        }
        else if (this.strategy === 'BIO') {
            // REAL MPC ALGORITHM (LOOK-AHEAD)
            action = this.runMPC(params);
        }

        // --- EXECUTE ACTION (REALITY) ---
        // Apply stochastic noise only in reality, not inside MPC prediction
        let result = simulateStep(this.state, action, params);

        // Add noise to reality
        if (action !== 'REST' && result.state.burnoutTimer === 0) {
            let noise = (Math.random() - 0.5) * 2.0; // Fixed noise factor for simplicity
            result.state.knowledge += noise;
        }

        this.state = result.state;
        this.logState();
    }

    // --- MPC CORE: RECURSIVE SEARCH ---
    runMPC(params) {
        // Optimization Horizon
        const horizon = parseInt(params.mpcHorizon);
        const actions = ['HIGH', 'LOW', 'REST'];

        let bestScore = -Infinity;
        let bestAction = 'REST';

        // Helper function for DFS
        const search = (currentState, depth, accumulatedScore) => {
            if (depth === 0) return accumulatedScore;

            let maxScore = -Infinity;

            for (let act of actions) {
                // Simulate 1 step forward
                let simResult = simulateStep(currentState, act, params);

                // Recursive call
                let score = search(simResult.state, depth - 1, accumulatedScore + simResult.reward);

                if (score > maxScore) maxScore = score;
            }
            return maxScore;
        };

        // Root level search (Find first action)
        for (let act of actions) {
            let simResult = simulateStep(this.state, act, params);
            // Calculate potential score of this path
            let pathScore = search(simResult.state, horizon - 1, simResult.reward);

            if (pathScore > bestScore) {
                bestScore = pathScore;
                bestAction = act;
            }
        }

        return bestAction;
    }

    logState() {
        this.logEnergy.push(this.state.energy);
        this.logKnowledge.push(this.state.knowledge);
    }
}

// --- MAIN LOOP ---
function runSimulation() {
    // Get params
    const params = {
        alphaHigh: parseFloat(document.getElementById('alphaHigh').value),
        alphaLow: 3, // Fixed relative to High
        recovRate: parseFloat(document.getElementById('recovRate').value),
        decayRate: parseFloat(document.getElementById('decayRate').value) / 1000,
        switchCost: parseFloat(document.getElementById('switchCost').value),
        mpcHorizon: document.getElementById('mpcHorizon').value,
        nonLinear: document.getElementById('nonLinearToggle').checked
    };

    const greedy = new VirtualLearner('GREEDY');
    const fixed = new VirtualLearner('FIXED');
    const bio = new VirtualLearner('BIO');

    for (let t = 0; t < TOTAL_STEPS; t++) {
        // Daily Reset
        if (t > 0 && t % HOURS_PER_DAY === 0) {
            [greedy, fixed, bio].forEach(agent => {
                agent.state.energy = E_MAX;
                agent.state.lastAction = null;
            });
        }
        greedy.step(t, params);
        fixed.step(t, params);
        bio.step(t, params);
    }

    updateCharts(greedy, fixed, bio);
    updateStats(greedy, fixed, bio);
}

// --- VISUALIZATION (Chart.js) ---
function updateStats(g, f, b) {
    document.getElementById('scoreGreedy').innerText = Math.round(g.state.knowledge);
    document.getElementById('burnGreedy').innerText = g.state.burnoutCount || 0;

    document.getElementById('scoreFixed').innerText = Math.round(f.state.knowledge);
    document.getElementById('scoreBio').innerText = Math.round(b.state.knowledge);

    let improv = ((b.state.knowledge - f.state.knowledge) / f.state.knowledge) * 100;
    document.getElementById('improvementVal').innerText = (improv > 0 ? "+" : "") + improv.toFixed(1) + "%";
}

function updateCharts(g, f, b) {
    const labels = Array.from({ length: TOTAL_STEPS }, (_, i) => i);

    const commonOptions = {
        responsive: true, maintainAspectRatio: false,
        elements: { point: { radius: 0 } },
        interaction: { mode: 'index', intersect: false },
        animation: false, // Global disable animation for perf
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
            y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } }
        }
    };

    // 1. Energy Chart
    // Check if chart exists. If NO, create it. If YES, update data.
    if (!chartEnergy) {
        const ctxE = document.getElementById('energyChart').getContext('2d');
        chartEnergy = new Chart(ctxE, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Greedy', data: g.logEnergy, borderColor: '#ef4444', borderWidth: 2 },
                    { label: 'Fixed', data: f.logEnergy, borderColor: '#f59e0b', borderWidth: 2, borderDash: [5, 5] },
                    { label: 'Bio-PKT (MPC)', data: b.logEnergy, borderColor: '#10b981', borderWidth: 2.5 }
                ]
            },
            options: {
                ...commonOptions,
                plugins: { annotation: { annotations: { line1: { type: 'line', yMin: 20, yMax: 20, borderColor: 'red', borderDash: [2, 2] } } } },
                scales: { ...commonOptions.scales, y: { min: 0, max: 100 } }
            }
        });
    } else {
        // FAST UPDATE PATH
        chartEnergy.data.datasets[0].data = g.logEnergy;
        chartEnergy.data.datasets[1].data = f.logEnergy;
        chartEnergy.data.datasets[2].data = b.logEnergy;
        chartEnergy.update('none'); // 'none' = No animation
    }

    // 2. Knowledge Chart
    if (!chartKnowledge) {
        const ctxK = document.getElementById('knowledgeChart').getContext('2d');
        chartKnowledge = new Chart(ctxK, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Greedy', data: g.logKnowledge, borderColor: '#ef4444', borderWidth: 2 },
                    { label: 'Fixed', data: f.logKnowledge, borderColor: '#f59e0b', borderWidth: 2, borderDash: [5, 5] },
                    { label: 'Bio-PKT (MPC)', data: b.logKnowledge, borderColor: '#10b981', borderWidth: 3 }
                ]
            },
            options: commonOptions
        });
    } else {
        // FAST UPDATE PATH
        chartKnowledge.data.datasets[0].data = g.logKnowledge;
        chartKnowledge.data.datasets[1].data = f.logKnowledge;
        chartKnowledge.data.datasets[2].data = b.logKnowledge;
        chartKnowledge.update('none');
    }
}

window.onload = runSimulation;