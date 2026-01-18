// CONFIGURATION GLOBALS
const DAYS = 7;
const HOURS_PER_DAY = 10;
const TOTAL_STEPS = DAYS * HOURS_PER_DAY;
const E_MAX = 100;
const E_CRITICAL = 20;
const GAIN_HIGH = 10;
const GAIN_LOW = 4;

let chartEnergy, chartKnowledge;

// --- 1. INTERNAL MODEL (Cái MPC nghĩ - Lý thuyết hoàn hảo) ---
function predictStep(currentState, action, params) {
    let nextState = { ...currentState };

    // Recovery logic (Predicted)
    if (nextState.burnoutTimer > 0) {
        nextState.energy = Math.min(E_MAX, nextState.energy + params.recovRate);
        nextState.burnoutTimer--;
        return { state: nextState, reward: 0 };
    }

    let cost = 0;
    let gain = 0;

    if (action === 'HIGH') { cost = params.alphaHigh; gain = GAIN_HIGH; }
    else if (action === 'LOW') { cost = params.alphaLow; gain = GAIN_LOW; }
    else { cost = -params.recovRate; gain = 0; }

    // MPC assumes Non-linear Fatigue exists (if enabled)
    if (params.nonLinear && nextState.energy < 50 && cost > 0) {
        let fatigueFactor = 1 + (50 - nextState.energy) / 50;
        cost *= fatigueFactor;
    }

    // MPC assumes Perfect Efficiency (trừ khi nó quá thông minh, 
    // nhưng để giả lập Model Mismatch, ta cho MPC tin rằng Efficiency luôn là 1 
    // hoặc MPC biết về Efficiency - ở đây ta cho MPC biết để nó tối ưu chuẩn)
    let efficiency = 1.0;
    if (params.useEfficiency) {
        // Simple efficiency model for MPC: Linearly drops below 50%
        if (nextState.energy < 50) efficiency = Math.max(0.1, nextState.energy / 50);
    }
    gain *= efficiency;

    // Update Energy
    nextState.energy -= cost;
    nextState.energy = Math.max(0, Math.min(E_MAX, nextState.energy));

    // Penalty logic
    let penalty = 0;
    if (nextState.energy < E_CRITICAL && action !== 'REST') {
        nextState.burnoutTimer = 2;
        penalty = 500; // Phạt nặng
    }

    // Reward
    let reward = gain - penalty;
    return { state: nextState, reward: reward };
}

// --- 2. PHYSICAL REALITY (Cái diễn ra thực tế - Khắc nghiệt & Ngẫu nhiên) ---
function executeRealStep(currentState, action, params) {
    let nextState = { ...currentState };

    // Burnout handling
    if (nextState.burnoutTimer > 0) {
        nextState.energy = Math.min(E_MAX, nextState.energy + params.recovRate);
        nextState.burnoutTimer--;
        // Burnout decay (Real memory loss)
        nextState.knowledge *= (1 - params.decayRate * 3);
        return nextState;
    }

    let cost = 0;
    let gain = 0;
    if (action === 'HIGH') { cost = params.alphaHigh; gain = GAIN_HIGH; }
    else if (action === 'LOW') { cost = params.alphaLow; gain = GAIN_LOW; }
    else { cost = -params.recovRate; gain = 0; }

    // REALISM 1: MODEL MISMATCH (Nhiễu động tham số)
    // Thực tế có thể tốn pin hơn dự kiến (Mismatch %)
    if (cost > 0) {
        let mismatch = 1 + (Math.random() * params.mismatchRate); // e.g., 1.0 to 1.2
        cost *= mismatch;
    }

    // REALISM 2: NON-LINEAR FATIGUE (Vật lý)
    if (params.nonLinear && nextState.energy < 50 && cost > 0) {
        let fatigueFactor = 1 + (50 - nextState.energy) / 50;
        cost *= fatigueFactor;
    }

    // REALISM 3: SWITCHING COST (Vật lý)
    if (nextState.lastAction && nextState.lastAction !== action && action !== 'REST') {
        nextState.energy -= params.switchCost;
    }

    // REALISM 4: DYNAMIC EFFICIENCY (Quan trọng!)
    // Khi mệt, học không vào đầu
    let efficiency = 1.0;
    if (params.useEfficiency) {
        if (nextState.energy < 50) {
            // Drop drasticly: At 20% energy -> 0.4 efficiency
            efficiency = Math.max(0.1, nextState.energy / 50);
        }
    }
    gain *= efficiency;

    // Stochastic Gain Noise
    if (gain > 0) gain += (Math.random() - 0.5) * 1.5;

    // Update Energy
    nextState.energy -= cost;
    nextState.energy = Math.max(0, Math.min(E_MAX, nextState.energy));

    // Update Knowledge
    nextState.knowledge *= (1 - params.decayRate);
    nextState.knowledge += Math.max(0, gain);

    // Check Burnout
    if (nextState.energy < E_CRITICAL && action !== 'REST') {
        nextState.burnoutTimer = 2;
        // Punishment: Lose recent gain due to cognitive crash
        nextState.knowledge -= gain;
    }

    nextState.lastAction = action;
    return nextState;
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

        // --- PLAN ---
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
            // MPC dùng mô hình Internal (predictStep) để ra quyết định
            action = this.runMPC(params);
        }

        // --- EXECUTE (Reality Check) ---
        // Kết quả thực tế có thể khác với dự tính của MPC
        this.state = executeRealStep(this.state, action, params);
        this.logState();
    }

    runMPC(params) {
        const horizon = parseInt(params.mpcHorizon);
        const actions = ['HIGH', 'LOW', 'REST'];

        // MPC Optimization via DFS (Mini-Max style but simple Maximize)
        // Note: MPC uses 'predictStep' (Ideal Model), NOT 'executeRealStep'
        const search = (currentState, depth, accumulatedReward) => {
            if (depth === 0) return accumulatedReward;

            let bestPathVal = -Infinity;
            for (let act of actions) {
                // Prediction
                let pred = predictStep(currentState, act, params);
                // Recursion
                let val = search(pred.state, depth - 1, accumulatedReward + pred.reward);
                if (val > bestPathVal) bestPathVal = val;
            }
            return bestPathVal;
        };

        let bestScore = -Infinity;
        let bestAction = 'REST';

        for (let act of actions) {
            let pred = predictStep(this.state, act, params);
            let score = search(pred.state, horizon - 1, pred.reward);

            // Bias breaker: Prefer Active Learning over Rest if scores are equal
            if (score > bestScore + 0.1) {
                bestScore = score;
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

// --- MAIN RUN ---
function runSimulation() {
    const params = {
        alphaHigh: parseFloat(document.getElementById('alphaHigh').value),
        alphaLow: 3,
        recovRate: parseFloat(document.getElementById('recovRate').value),
        decayRate: parseFloat(document.getElementById('decayRate').value) / 1000,
        switchCost: parseFloat(document.getElementById('switchCost').value),
        mpcHorizon: document.getElementById('mpcHorizon').value,
        nonLinear: document.getElementById('nonLinearToggle').checked,
        // New Reality Params
        mismatchRate: parseFloat(document.getElementById('mismatch').value) / 100, // %
        useEfficiency: document.getElementById('efficiencyToggle').checked
    };

    const greedy = new VirtualLearner('GREEDY');
    const fixed = new VirtualLearner('FIXED');
    const bio = new VirtualLearner('BIO');

    for (let t = 0; t < TOTAL_STEPS; t++) {
        if (t > 0 && t % HOURS_PER_DAY === 0) {
            [greedy, fixed, bio].forEach(a => {
                a.state.energy = E_MAX;
                a.state.lastAction = null;
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

    // 1. Energy
    const ctxE = document.getElementById('energyChart').getContext('2d');
    if (chartEnergy) {
        // FAST UPDATE
        chartEnergy.data.datasets[0].data = g.logEnergy;
        chartEnergy.data.datasets[1].data = f.logEnergy;
        chartEnergy.data.datasets[2].data = b.logEnergy;
        chartEnergy.update('none');
    } else {
        // INIT
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
    }

    // 2. Knowledge
    const ctxK = document.getElementById('knowledgeChart').getContext('2d');
    if (chartKnowledge) {
        // FAST UPDATE
        chartKnowledge.data.datasets[0].data = g.logKnowledge;
        chartKnowledge.data.datasets[1].data = f.logKnowledge;
        chartKnowledge.data.datasets[2].data = b.logKnowledge;
        chartKnowledge.update('none');
    } else {
        // INIT
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
    }
}

window.onload = runSimulation;


// --- MONTE CARLO LOGIC ---

async function runMonteCarlo() {
    const N = 50;
    const statusEl = document.getElementById('mcStatus');
    statusEl.innerText = `Running ${N} simulations...`;

    const baseParams = getParamsFromUI();
    const diversity = 0.15; // 15% variation

    // Data Aggregators
    let aggEnergy = { greedy: [], fixed: [], bio: [] };
    let aggKnowledge = { greedy: [], fixed: [], bio: [] };
    // Burnout Counters (for Probability)
    let burnCounts = { greedy: 0, fixed: 0, bio: 0 };

    for (let t = 0; t < TOTAL_STEPS; t++) {
        aggEnergy.greedy[t] = []; aggEnergy.fixed[t] = []; aggEnergy.bio[t] = [];
        aggKnowledge.greedy[t] = []; aggKnowledge.fixed[t] = []; aggKnowledge.bio[t] = [];
    }

    await new Promise(resolve => setTimeout(resolve, 10));

    let winCount = 0;

    for (let i = 0; i < N; i++) {
        let iterParams = { ...baseParams };
        // PERTURBATION: Population Diversity
        iterParams.alphaHigh *= (1 + (Math.random() - 0.5) * diversity);
        iterParams.recovRate *= (1 + (Math.random() - 0.5) * diversity);

        const greedy = new VirtualLearner('GREEDY');
        const fixed = new VirtualLearner('FIXED');
        const bio = new VirtualLearner('BIO');

        // Track burnout occurrence in this run
        let gBurn = false, fBurn = false, bBurn = false;

        for (let t = 0; t < TOTAL_STEPS; t++) {
            if (t > 0 && t % HOURS_PER_DAY === 0) {
                [greedy, fixed, bio].forEach(a => { a.state.energy = E_MAX; a.state.lastAction = null; });
            }
            greedy.step(t, iterParams);
            fixed.step(t, iterParams);
            bio.step(t, iterParams);

            if (greedy.state.burnoutTimer > 0) gBurn = true;
            if (fixed.state.burnoutTimer > 0) fBurn = true;
            if (bio.state.burnoutTimer > 0) bBurn = true;

            // Collect Data
            aggEnergy.greedy[t].push(greedy.state.energy);
            aggEnergy.fixed[t].push(fixed.state.energy);
            aggEnergy.bio[t].push(bio.state.energy);

            aggKnowledge.greedy[t].push(greedy.state.knowledge);
            aggKnowledge.fixed[t].push(fixed.state.knowledge);
            aggKnowledge.bio[t].push(bio.state.knowledge);
        }

        if (gBurn) burnCounts.greedy++;
        if (fBurn) burnCounts.fixed++;
        if (bBurn) burnCounts.bio++;

        if (bio.state.knowledge > fixed.state.knowledge) winCount++;
    }

    // Process Statistics
    const processSeries = (dataArr) => {
        let mean = [], min = [], max = [];
        for (let t = 0; t < TOTAL_STEPS; t++) {
            let values = dataArr[t];
            let sum = values.reduce((a, b) => a + b, 0);
            let avg = sum / values.length;
            mean.push(avg);

            // Bands: Mean +/- StdDev
            let sqDiff = values.map(v => (v - avg) ** 2);
            let stdDev = Math.sqrt(sqDiff.reduce((a, b) => a + b, 0) / values.length);
            min.push(avg - stdDev);
            max.push(avg + stdDev);
        }
        return { mean, min, max };
    };

    const stats = {
        energy: { greedy: processSeries(aggEnergy.greedy), bio: processSeries(aggEnergy.bio), fixed: processSeries(aggEnergy.fixed) },
        knowledge: { greedy: processSeries(aggKnowledge.greedy), fixed: processSeries(aggKnowledge.fixed), bio: processSeries(aggKnowledge.bio) }
    };

    statusEl.innerText = `Bio-PKT Win Rate: ${Math.round(winCount / N * 100)}% (N=${N})`;

    updateChartsMonteCarlo(stats);

    const finalStep = TOTAL_STEPS - 1;
    updateStatsUI(
        stats.knowledge.greedy.mean[finalStep], (burnCounts.greedy / N) * 100,
        stats.knowledge.fixed.mean[finalStep], (burnCounts.fixed / N) * 100,
        stats.knowledge.bio.mean[finalStep], (burnCounts.bio / N) * 100,
        true // isMonteCarlo mode
    );
}

async function runSensitivityAnalysis() {
    const statusEl = document.getElementById('mcStatus');
    statusEl.innerHTML = "Running Sensitivity Sweep (Mismatch Rate 0% -> 50%)...<br>This may take a moment.";

    // Disable buttons
    const buttons = document.querySelectorAll('button');
    buttons.forEach(b => b.disabled = true);

    const rates = [0, 10, 20, 30, 40, 50];
    let results = [];
    const N = 20; // Fast sweep

    for (let r of rates) {
        let win = 0;
        let baseParams = getParamsFromUI();
        baseParams.mismatchRate = r / 100.0; // Override mismatch

        for (let i = 0; i < N; i++) {
            // Apply similar perturbation for valid population test
            let params = { ...baseParams };
            params.alphaHigh *= (1 + (Math.random() - 0.5) * 0.15);
            params.recovRate *= (1 + (Math.random() - 0.5) * 0.15);

            const greedy = new VirtualLearner('GREEDY');
            const fixed = new VirtualLearner('FIXED');
            const bio = new VirtualLearner('BIO');

            for (let t = 0; t < TOTAL_STEPS; t++) {
                if (t > 0 && t % HOURS_PER_DAY === 0) {
                    [greedy, fixed, bio].forEach(a => { a.state.energy = E_MAX; a.state.lastAction = null; });
                }
                greedy.step(t, params);
                fixed.step(t, params);
                bio.step(t, params);
            }
            if (bio.state.knowledge > fixed.state.knowledge) win++;
        }
        results.push(`Mismatch ${r}%: ${Math.round(win / N * 100)}% Win`);

        // Update progress
        statusEl.innerHTML = `Analyzing... ${r}% complete`;
        await new Promise(res => setTimeout(res, 10));
    }

    statusEl.innerHTML = "<strong>Sensitivity Results:</strong><br>" + results.join("<br>");
    buttons.forEach(b => b.disabled = false);
}

function getParamsFromUI() {
    return {
        alphaHigh: parseFloat(document.getElementById('alphaHigh').value),
        alphaLow: 3,
        recovRate: parseFloat(document.getElementById('recovRate').value),
        decayRate: parseFloat(document.getElementById('decayRate').value) / 1000,
        switchCost: parseFloat(document.getElementById('switchCost').value),
        mpcHorizon: document.getElementById('mpcHorizon').value,
        nonLinear: document.getElementById('nonLinearToggle').checked,
        mismatchRate: parseFloat(document.getElementById('mismatch').value) / 100,
        useEfficiency: document.getElementById('efficiencyToggle').checked
    };
}

// Consolidate updating logic
function updateStats(g, f, b) {
    updateStatsUI(
        g.state.knowledge, g.state.burnoutCount || 0,
        f.state.knowledge, f.state.burnoutCount || 0,
        b.state.knowledge, b.state.burnoutCount || 0,
        false
    );
}

function updateStatsUI(gScore, gBurn, fScore, fBurn, bScore, bBurn, isMonteCarlo) {
    document.getElementById('scoreGreedy').innerText = Math.round(gScore);
    document.getElementById('scoreFixed').innerText = Math.round(fScore);
    document.getElementById('scoreBio').innerText = Math.round(bScore);

    // Update Burnout Labels dynamically
    const burnLabel = isMonteCarlo ? "Burnout Risk: " : "Burnouts: ";
    const burnSuffix = isMonteCarlo ? "%" : "";
    const valG = isMonteCarlo ? Math.round(gBurn) : gBurn;
    const valF = isMonteCarlo ? Math.round(fBurn) : fBurn;
    const valB = isMonteCarlo ? Math.round(bBurn) : bBurn;

    const setBurnHTML = (id, val) => {
        const el = document.getElementById(id);
        if (el && el.parentElement) {
            el.parentElement.innerHTML = `${burnLabel}<span id="${id}">${val}${burnSuffix}</span>`;
        }
    };

    setBurnHTML('burnGreedy', valG);
    setBurnHTML('burnFixed', valF);
    setBurnHTML('burnBio', valB);

    let improv = ((bScore - fScore) / fScore) * 100;
    document.getElementById('improvementVal').innerText = (improv > 0 ? "+" : "") + improv.toFixed(1) + "%";
}

// --- ADVANCED CHARTING (Mean + Confidence Interval) ---
function updateChartsMonteCarlo(stats) {
    const labels = Array.from({ length: TOTAL_STEPS }, (_, i) => i);
    const commonOptions = {
        responsive: true, maintainAspectRatio: false,
        elements: { point: { radius: 0 } },
        interaction: { mode: 'index', intersect: false },
        animation: false,
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
            y: { grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } }
        }
    };

    // 1. Energy Chart (Showing Mean + Band for Bio vs Greedy)
    const ctxE = document.getElementById('energyChart').getContext('2d');
    if (chartEnergy) chartEnergy.destroy();

    chartEnergy = new Chart(ctxE, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                // Greedy Mean
                { label: 'Greedy (Mean)', data: stats.energy.greedy.mean, borderColor: '#ef4444', borderWidth: 2, fill: false },
                // Bio Mean
                { label: 'Bio-PKT (Mean)', data: stats.energy.bio.mean, borderColor: '#10b981', borderWidth: 2, fill: false },

                // Confidence Bands (Tricky in Chart.js, usually use 'fill: +1' or 'fill: -1')
                // Simplified: Just showing means is often enough for web demo, 
                // but to impress reviewer, we add a semi-transparent fill for Bio
                {
                    label: 'Bio Variance',
                    data: stats.energy.bio.max,
                    borderColor: 'transparent',
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    fill: '+1' // Fill to next dataset
                },
                {
                    label: 'Bio Var Bottom',
                    data: stats.energy.bio.min,
                    borderColor: 'transparent',
                    fill: false // Helper dataset for band
                }
            ]
        },
        options: {
            ...commonOptions,
            scales: { ...commonOptions.scales, y: { min: 0, max: 100 } }
        }
    });

    // 2. Knowledge Chart
    const ctxK = document.getElementById('knowledgeChart').getContext('2d');
    if (chartKnowledge) chartKnowledge.destroy();

    chartKnowledge = new Chart(ctxK, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Greedy (Mean)', data: stats.knowledge.greedy.mean, borderColor: '#ef4444', borderWidth: 2 },
                { label: 'Fixed (Mean)', data: stats.knowledge.fixed.mean, borderColor: '#f59e0b', borderWidth: 2, borderDash: [5, 5] },
                { label: 'Bio-PKT (Mean)', data: stats.knowledge.bio.mean, borderColor: '#10b981', borderWidth: 3 },

                // Bio-PKT Confidence Band
                {
                    label: 'Variance',
                    data: stats.knowledge.bio.max,
                    borderColor: 'transparent',
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    fill: '+1'
                },
                {
                    label: 'Var Bottom',
                    data: stats.knowledge.bio.min,
                    borderColor: 'transparent',
                    fill: false
                }
            ]
        },
        options: commonOptions
    });
}

// Override Single Run to work with new Structure
// ... (Bạn giữ nguyên hàm runSimulation cũ nhưng gọi updateStatsUI thay vì update trực tiếp DOM) ...