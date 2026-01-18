// CONFIGURATION GLOBALS
const DAYS = 7;
const HOURS_PER_DAY = 10;
const TOTAL_STEPS = DAYS * HOURS_PER_DAY;
const E_MAX = 100;
const E_CRITICAL = 20;
const GAIN_HIGH = 10;
const GAIN_LOW = 4;

let chartEnergy, chartKnowledge;

// --- 1. INTERNAL MODEL (MPC Logic) ---
function predictStep(currentState, action, params) {
    let nextState = { ...currentState };
    if (nextState.burnoutTimer > 0) {
        nextState.energy = Math.min(E_MAX, nextState.energy + params.recovRate);
        nextState.burnoutTimer--;
        return { state: nextState, reward: 0 };
    }
    let cost = 0, gain = 0;
    if (action === 'HIGH') { cost = params.alphaHigh; gain = GAIN_HIGH; }
    else if (action === 'LOW') { cost = params.alphaLow; gain = GAIN_LOW; }
    else { cost = -params.recovRate; gain = 0; }

    // Model Mismatch: MPC *thinks* it sees non-linearity if enabled
    if (params.nonLinear && nextState.energy < 50 && cost > 0) {
        let fatigueFactor = 1 + (50 - nextState.energy) / 50;
        cost *= fatigueFactor;
    }

    let efficiency = 1.0;
    if (params.useEfficiency && nextState.energy < 50) {
        efficiency = Math.max(0.1, nextState.energy / 50);
    }
    gain *= efficiency;

    // Penalty logic
    let penalty = 0;
    nextState.energy -= cost;
    nextState.energy = Math.max(0, Math.min(E_MAX, nextState.energy));

    if (nextState.energy < E_CRITICAL && action !== 'REST') {
        nextState.burnoutTimer = 2; // MPC expects 2 day penalty
        penalty = 500;
    }
    return { state: nextState, reward: gain - penalty };
}

// --- 2. PHYSICAL REALITY ---
function executeRealStep(currentState, action, params) {
    let nextState = { ...currentState };
    if (nextState.burnoutTimer > 0) {
        nextState.energy = Math.min(E_MAX, nextState.energy + params.recovRate);
        nextState.burnoutTimer--;
        nextState.knowledge *= (1 - params.decayRate * 3);
        return nextState;
    }

    // --- REALISM 5: HUMAN COMPLIANCE (Sự bất tuân) ---
    // Reviewer #5: Students have "Greedy Impulse".
    let finalAction = action;
    if (params.compliance < 1.0) {
        let roll = Math.random();
        if (roll > params.compliance) { // Non-compliance triggered!
            // Instinct: If Energy > 30, push HIGH. Else REST.
            if (currentState.energy > 30) finalAction = 'HIGH';
            else finalAction = 'REST';
        }
    }

    let cost = 0, gain = 0;
    if (finalAction === 'HIGH') { cost = params.alphaHigh; gain = GAIN_HIGH; }
    else if (finalAction === 'LOW') { cost = params.alphaLow; gain = GAIN_LOW; }
    else { cost = -params.recovRate; gain = 0; }

    // Realism 1: Model Mismatch
    if (cost > 0) cost *= (1 + (Math.random() * params.mismatchRate));

    // Realism 2: Non-Linear Fatigue
    if (params.nonLinear && nextState.energy < 50 && cost > 0) {
        cost *= (1 + (50 - nextState.energy) / 50);
    }

    // Realism 3: Switching Cost
    if (nextState.lastAction && nextState.lastAction !== finalAction && finalAction !== 'REST') {
        nextState.energy -= params.switchCost;
    }

    // Realism 4: Dynamic Efficiency
    let efficiency = 1.0;
    if (params.useEfficiency && nextState.energy < 50) {
        efficiency = Math.max(0.1, nextState.energy / 50);
    }
    gain *= efficiency;

    // Stochastic Noise
    if (gain > 0) gain += (Math.random() - 0.5) * 1.5;

    // Update Energy
    nextState.energy -= cost;
    nextState.energy = Math.max(0, Math.min(E_MAX, nextState.energy));

    // Update Knowledge
    nextState.knowledge *= (1 - params.decayRate);
    nextState.knowledge += Math.max(0, gain);

    // Check Burnout
    if (nextState.energy < E_CRITICAL && finalAction !== 'REST') {
        nextState.burnoutTimer = 2;
        nextState.knowledge -= gain; // Lose recent gain
    }

    nextState.lastAction = finalAction;
    return nextState;
}

// --- AGENT CLASS ---
class VirtualLearner {
    constructor(strategy, type = 'Average') {
        this.strategy = strategy;
        this.type = type; // 'Strong', 'Weak', 'Average'
        this.state = { energy: E_MAX, knowledge: 0, burnoutTimer: 0, lastAction: null };
        this.logEnergy = [];
        this.logKnowledge = [];
    }

    step(stepIndex, params) {
        let action = 'REST';
        // Plan
        if (this.strategy === 'GREEDY') action = (this.state.energy > 0) ? 'HIGH' : 'REST';
        else if (this.strategy === 'FIXED') {
            let cycle = stepIndex % 6;
            if (cycle < 2) action = 'HIGH'; else if (cycle === 2) action = 'REST';
            else if (cycle < 5) action = 'LOW'; else action = 'REST';
        }
        else if (this.strategy === 'BIO') action = this.runMPC(params);

        // Execute
        this.state = executeRealStep(this.state, action, params);
        this.logState();
    }

    runMPC(params) {
        const horizon = parseInt(params.mpcHorizon);
        const actions = ['HIGH', 'LOW', 'REST'];
        const search = (currentState, depth, accumulatedReward) => {
            if (depth === 0) return accumulatedReward;
            let bestPathVal = -Infinity;
            for (let act of actions) {
                let pred = predictStep(currentState, act, params);
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
            // Bias Breaker: Prefer Activity if equal
            if (score > bestScore + 0.1) { bestScore = score; bestAction = act; }
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
    const params = getParamsFromUI();
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

    updateCharts(greedy, fixed, bio);
    updateStats(greedy, fixed, bio);
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
        useEfficiency: document.getElementById('efficiencyToggle').checked,
        // NEW param from Reviewer #5
        compliance: parseFloat(document.getElementById('compliance') ? document.getElementById('compliance').value : 100) / 100
    };
}

// --- MONTE CARLO + FAIRNESS AUDIT ---
async function runMonteCarlo() {
    const N = 50;
    const statusEl = document.getElementById('mcStatus');
    statusEl.innerText = `Running Equity Analysis (N=${N})...`;

    const baseParams = getParamsFromUI();

    // Subgroup Stats
    let weakStats = { greedy: [], bio: [] };
    let strongStats = { greedy: [], bio: [] };

    // Aggregate for Charts
    let aggEnergy = { greedy: [], bio: [], fixed: [] };
    let aggKnowledge = { greedy: [], bio: [], fixed: [] };
    for (let t = 0; t < TOTAL_STEPS; t++) {
        aggEnergy.greedy[t] = []; aggEnergy.bio[t] = []; aggEnergy.fixed[t] = [];
        aggKnowledge.greedy[t] = []; aggKnowledge.bio[t] = []; aggKnowledge.fixed[t] = [];
    }

    await new Promise(resolve => setTimeout(resolve, 10));

    let winCount = 0;

    for (let i = 0; i < N; i++) {
        let iterParams = { ...baseParams };

        // Randomize Learner Constitution (Population Diversity)
        // alphaHigh base ~18 +/- 20%
        let constitution = (Math.random() - 0.5) * 0.40;
        iterParams.alphaHigh *= (1 + constitution);
        iterParams.recovRate *= (1 - constitution); // Weak learners recover slow too

        let type = 'Average';
        if (constitution > 0.1) type = 'Weak'; // Cost High, Recov Low
        else if (constitution < -0.1) type = 'Strong'; // Cost Low, Recov High

        const greedy = new VirtualLearner('GREEDY', type);
        const fixed = new VirtualLearner('FIXED', type);
        const bio = new VirtualLearner('BIO', type);

        for (let t = 0; t < TOTAL_STEPS; t++) {
            if (t > 0 && t % HOURS_PER_DAY === 0) {
                [greedy, fixed, bio].forEach(a => { a.state.energy = E_MAX; a.state.lastAction = null; });
            }
            greedy.step(t, iterParams);
            fixed.step(t, iterParams);
            bio.step(t, iterParams);

            // Chart Aggregation
            aggEnergy.greedy[t].push(greedy.state.energy);
            aggEnergy.fixed[t].push(fixed.state.energy);
            aggEnergy.bio[t].push(bio.state.energy);
            aggKnowledge.greedy[t].push(greedy.state.knowledge);
            aggKnowledge.fixed[t].push(fixed.state.knowledge);
            aggKnowledge.bio[t].push(bio.state.knowledge);
        }

        // Subgroup Collection
        if (type === 'Weak') {
            weakStats.greedy.push(greedy.state.knowledge);
            weakStats.bio.push(bio.state.knowledge);
        } else if (type === 'Strong') {
            strongStats.greedy.push(greedy.state.knowledge);
            strongStats.bio.push(bio.state.knowledge);
        }

        if (bio.state.knowledge > fixed.state.knowledge) winCount++;
    }

    // Fairness Calculations
    const avg = arr => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    // Check if we have data to avoid NaN
    const wImp = weakStats.greedy.length ? ((avg(weakStats.bio) - avg(weakStats.greedy)) / avg(weakStats.greedy) * 100).toFixed(1) : "N/A";
    const sImp = strongStats.greedy.length ? ((avg(strongStats.bio) - avg(strongStats.greedy)) / avg(strongStats.greedy) * 100).toFixed(1) : "N/A";

    statusEl.innerHTML = `
        <strong>Fairness Audit:</strong><br>
        Weak Learners Gain: <span style="color:#2ed573">${wImp > 0 ? '+' : ''}${wImp}%</span><br>
        Strong Learners Gain: <span style="color:#70a1ff">${sImp > 0 ? '+' : ''}${sImp}%</span><br>
        Avg Win Rate: ${Math.round(winCount / N * 100)}%
    `;

    // Update Charts (Standard Mean/Band)
    const processSeries = (dataArr) => {
        let mean = [], min = [], max = [];
        for (let t = 0; t < TOTAL_STEPS; t++) {
            let values = dataArr[t];
            let avg = values.reduce((a, b) => a + b, 0) / values.length;
            mean.push(avg);
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

    updateChartsMonteCarlo(stats);

    // Update Stats UI (Use Averages)
    const fStep = TOTAL_STEPS - 1;
    updateStatsUI(
        stats.knowledge.greedy.mean[fStep], 0,
        stats.knowledge.fixed.mean[fStep], 0,
        stats.knowledge.bio.mean[fStep], 0,
        true
    );
}

// --- SENSITIVITY ANALYSIS (v5.0 Feature - kept for robustness) ---
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
        statusEl.innerHTML = `Analyzing... ${r}% complete`;
        await new Promise(res => setTimeout(res, 10));
    }

    statusEl.innerHTML = "<strong>Sensitivity Results:</strong><br>" + results.join("<br>");
    buttons.forEach(b => b.disabled = false);
}

// --- VISUALIZATION HELPERS ---
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

function updateCharts(g, f, b) {
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

    const ctxE = document.getElementById('energyChart').getContext('2d');
    if (chartEnergy) {
        chartEnergy.data.datasets[0].data = g.logEnergy;
        chartEnergy.data.datasets[1].data = f.logEnergy;
        chartEnergy.data.datasets[2].data = b.logEnergy;
        chartEnergy.update('none');
    } else {
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

    const ctxK = document.getElementById('knowledgeChart').getContext('2d');
    if (chartKnowledge) {
        chartKnowledge.data.datasets[0].data = g.logKnowledge;
        chartKnowledge.data.datasets[1].data = f.logKnowledge;
        chartKnowledge.data.datasets[2].data = b.logKnowledge;
        chartKnowledge.update('none');
    } else {
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

    // 1. Energy
    const ctxE = document.getElementById('energyChart').getContext('2d');
    if (chartEnergy) chartEnergy.destroy();

    chartEnergy = new Chart(ctxE, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Greedy (Mean)', data: stats.energy.greedy.mean, borderColor: '#ef4444', borderWidth: 2, fill: false },
                { label: 'Bio-PKT (Mean)', data: stats.energy.bio.mean, borderColor: '#10b981', borderWidth: 2, fill: false },
                {
                    label: 'Bio Variance',
                    data: stats.energy.bio.max,
                    borderColor: 'transparent',
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    fill: '+1'
                },
                {
                    label: 'Bio Var Bottom',
                    data: stats.energy.bio.min,
                    borderColor: 'transparent',
                    fill: false
                }
            ]
        },
        options: {
            ...commonOptions,
            scales: { ...commonOptions.scales, y: { min: 0, max: 100 } }
        }
    });

    // 2. Knowledge
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

window.onload = runSimulation;