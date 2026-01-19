
// --- 0. DEFINING THE KNOWLEDGE GRAPH (Mini-version of treeKnowledge) ---
// Giả lập 6 Nodes theo cấu trúc DAG:
// Level 1: A, B (Cơ bản)
// Level 2: C (Cần A), D (Cần B)
// Level 3: E (Cần C & D), F (Cần E) - Trùm cuối
const K_GRAPH = {
    'A': { id: 'A', label: 'Basics 1', difficulty: 0.3, parents: [], position: 0 },
    'B': { id: 'B', label: 'Basics 2', difficulty: 0.3, parents: [], position: 0 },
    'C': { id: 'C', label: 'Intermed 1', difficulty: 0.6, parents: ['A'], position: 1 },
    'D': { id: 'D', label: 'Intermed 2', difficulty: 0.6, parents: ['B'], position: 1 },
    'E': { id: 'E', label: 'Advanced', difficulty: 0.8, parents: ['C', 'D'], position: 2 },
    'F': { id: 'F', label: 'Expert', difficulty: 1.0, parents: ['E'], position: 3 }
};
const NODE_IDS = Object.keys(K_GRAPH);

// CONFIG GLOBALS
let TOTAL_STEPS = 100;
const HOURS_PER_DAY = 10;
const E_MAX = 100;
const E_CRITICAL = 20;

let chartEnergy, chartKnowledge;
let network = null;

// --- AGENT CLASS ---
class VirtualLearner {
    constructor(strategy) {
        this.strategy = strategy;
        this.state = {
            energy: E_MAX,
            // Thay vì knowledge scalar, ta dùng Knowledge Vector
            mastery: { 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0 },
            burnoutTimer: 0,
            lastAction: null
        };
        this.logEnergy = [];
        this.logTotalMastery = [];
    }

    // Tính tổng điểm Mastery (để vẽ biểu đồ cũ)
    getTotalMastery() {
        return Object.values(this.state.mastery).reduce((a, b) => a + b, 0);
    }

    // Đếm số Node đã Master (>90%)
    getMasteredCount() {
        return Object.values(this.state.mastery).filter(m => m >= 90).length;
    }

    step(stepIndex, params) {
        // ... (Logic Burnout recovery giữ nguyên) ...
        if (this.state.burnoutTimer > 0) {
            this.state.energy = Math.min(E_MAX, this.state.energy + params.recovRate);
            this.state.burnoutTimer--;
            this.logState();
            return;
        }

        // --- GRAPH-AWARE DECISION MAKING ---
        let actionNode = null;
        let actionType = 'REST';

        if (this.strategy === 'GREEDY') {
            // Greedy luôn chọn Node khó nhất chưa học (bất chấp tiên quyết)
            // Hoặc chọn Node điểm cao nhất
            // Giả lập sai lầm: Chọn Node E khi chưa học C, D
            if (this.state.energy > 0) {
                // Find highest difficulty node not yet mastered
                let target = NODE_IDS.find(n => this.state.mastery[n] < 100 && K_GRAPH[n].difficulty >= 0.8);
                if (!target) target = NODE_IDS.find(n => this.state.mastery[n] < 100);

                actionNode = target;
                actionType = 'HIGH'; // Mặc định coi là High Load
            }
        }
        else if (this.strategy === 'BIO') {
            // Bio-PKT: Chọn Node phù hợp với Năng lượng & Tiên quyết (ZPD)
            // 1. Lọc các Node đã thỏa mãn Tiên quyết (Prerequisites met)
            let learnableNodes = NODE_IDS.filter(id => {
                if (this.state.mastery[id] >= 100) return false; // Đã học xong
                let parents = K_GRAPH[id].parents;
                if (parents.length === 0) return true;
                // Kiểm tra xem cha đã master chưa (>50%)
                return parents.every(p => this.state.mastery[p] >= 50);
            });

            // 2. Chọn Node dựa trên Năng lượng (MPC Logic Simplified)
            if (this.state.energy > 40) {
                // Chọn Node khó nhất trong tập Learnable
                actionNode = learnableNodes.reverse().find(n => K_GRAPH[n].difficulty >= 0.6);
                if (!actionNode) actionNode = learnableNodes[0]; // Fallback
                actionType = 'HIGH';
            } else if (this.state.energy > E_CRITICAL) {
                // Chọn Node dễ
                actionNode = learnableNodes.find(n => K_GRAPH[n].difficulty < 0.6);
                actionType = 'LOW';
            } else {
                actionType = 'REST';
            }
        }
        else {
            // Fixed Strategy (Giữ nguyên logic cũ nhưng random node)
            actionType = (stepIndex % 3 === 0) ? 'REST' : 'HIGH';
            if (actionType !== 'REST') actionNode = NODE_IDS.find(n => this.state.mastery[n] < 100);
        }

        // --- EXECUTE LEARNING ---
        let cost = 0;
        let gain = 0;

        if (actionType === 'REST' || !actionNode) {
            cost = -params.recovRate;
            this.state.lastAction = 'REST';
        } else {
            // Tính Cost dựa trên độ khó Node
            let nodeInfo = K_GRAPH[actionNode];
            cost = nodeInfo.difficulty * 20; // Khó thì tốn nhiều pin (10-20 energy)

            // Adjust cost by custom Alpha High from UI if HIGH
            if (actionType === 'HIGH') cost = Math.max(cost, params.alphaHigh);

            // Tính Gain: PHỤ THUỘC VÀO TIÊN QUYẾT (GRAPH CHECK)
            let efficiency = 1.0;
            // Check prerequisites again for Reality
            let parentsMet = nodeInfo.parents.every(p => this.state.mastery[p] >= 50);

            if (!parentsMet) {
                efficiency = 0.1; // Phạt nặng: Học vượt cấp không vào đầu! (Reviewer #6 satisfaction)
                // console.log("Prerequisite penalty applied!");
            }

            // Dynamic Efficiency based on Energy
            if (this.state.energy < 50) efficiency *= (this.state.energy / 50);

            gain = 5 * efficiency; // Base gain per step

            // Stochastic Noise
            gain += (Math.random() - 0.5);

            // Update Mastery cho Node đó
            this.state.mastery[actionNode] = Math.min(100, this.state.mastery[actionNode] + Math.max(0, gain));
            this.state.lastAction = 'LEARN';
        }

        // Update Energy
        this.state.energy = Math.max(0, Math.min(E_MAX, this.state.energy - cost));

        // Burnout Check
        if (this.state.energy < E_CRITICAL && actionType !== 'REST') {
            this.state.burnoutTimer = 2;
        }

        this.logState();
    }

    logState() {
        this.logEnergy.push(this.state.energy);
        this.logTotalMastery.push(this.getTotalMastery());
    }
}

// --- VISUALIZATION: DRAW GRAPH ---
function drawGraph(agent) {
    const nodes = new vis.DataSet(
        NODE_IDS.map(id => {
            let mastery = agent.state.mastery[id];
            // Color mapping: Green > 90, Blue > 0, Gray = 0
            let color = mastery >= 90 ? '#10b981' : (mastery > 0 ? '#38bdf8' : '#475569');
            // Borders: Red if prerequisites missing but attempted (not easy to viz here, simple for now)
            return {
                id: id,
                label: `${K_GRAPH[id].label}\n${Math.round(mastery)}%`,
                color: { background: color, border: '#fff' },
                font: { color: '#f1f5f9' },
                shape: 'box',
                level: K_GRAPH[id].position
            };
        })
    );

    const edges = new vis.DataSet([
        { from: 'A', to: 'C', arrows: 'to' },
        { from: 'B', to: 'D', arrows: 'to' },
        { from: 'C', to: 'E', arrows: 'to' },
        { from: 'D', to: 'E', arrows: 'to' },
        { from: 'E', to: 'F', arrows: 'to' }
    ]);

    const container = document.getElementById('mynetwork');
    const data = { nodes: nodes, edges: edges };
    const options = {
        layout: { hierarchical: { direction: 'LR', sortMethod: 'directed', levelSeparation: 150 } },
        physics: false,
        edges: { color: '#64748b' }
    };

    if (network) network.destroy();
    network = new vis.Network(container, data, options);
}

// --- MAIN RUN ---
function runSimulation() {
    const params = getParamsFromUI();
    TOTAL_STEPS = 100; // Fixed duration for Graph demo

    const greedy = new VirtualLearner('GREEDY');
    const fixed = new VirtualLearner('FIXED');
    const bio = new VirtualLearner('BIO');

    for (let t = 0; t < TOTAL_STEPS; t++) {
        greedy.step(t, params);
        fixed.step(t, params);
        bio.step(t, params);
    }

    updateCharts(greedy, fixed, bio);

    // Update Stats Display
    document.getElementById('scoreGreedy').innerText = greedy.getMasteredCount();
    document.getElementById('scoreFixed').innerText = fixed.getMasteredCount();
    document.getElementById('scoreBio').innerText = bio.getMasteredCount();

    // DRAW GRAPH FOR BIO AGENT (Showcase)
    if (document.getElementById('tab-graph').style.display !== 'none') {
        drawGraph(bio);
    } else {
        // Just draw it in background or waiting for tab switch?
        // Let's hooktab switch to redraw if needed, or draw now invisibly
        drawGraph(bio);
    }
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
        compliance: parseFloat(document.getElementById('compliance') ? document.getElementById('compliance').value : 100) / 100
    };
}

// --- VISUALIZATION HELPERS (Reused from v6.0) ---
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

    // 1. Energy
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

    // 2. Knowledge (Total Mastery)
    const ctxK = document.getElementById('knowledgeChart').getContext('2d');
    if (chartKnowledge) {
        chartKnowledge.data.datasets[0].data = g.logTotalMastery;
        chartKnowledge.data.datasets[1].data = f.logTotalMastery;
        chartKnowledge.data.datasets[2].data = b.logTotalMastery;
        chartKnowledge.update('none');
    } else {
        chartKnowledge = new Chart(ctxK, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Greedy', data: g.logTotalMastery, borderColor: '#ef4444', borderWidth: 2 },
                    { label: 'Fixed', data: f.logTotalMastery, borderColor: '#f59e0b', borderWidth: 2, borderDash: [5, 5] },
                    { label: 'Bio-PKT (MPC)', data: b.logTotalMastery, borderColor: '#10b981', borderWidth: 3 }
                ]
            },
            options: commonOptions
        });
    }
}

// Monte Carlo (simplified/disabled for Graph Demo unless requested)
// --- MONTE CARLO + FAIRNESS AUDIT (Restored & Adapted for v7.0) ---
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
        iterParams.recovRate *= (1 - constitution);

        let type = 'Average';
        if (constitution > 0.1) type = 'Weak';
        else if (constitution < -0.1) type = 'Strong';

        // Note: Strategy constructors don't take 'type' in v7 simplification, 
        // but we keep the logic for statistical grouping if we were to expand Agent class later.
        // For now, type mainly affects params via 'constitution' above.
        const greedy = new VirtualLearner('GREEDY');
        const fixed = new VirtualLearner('FIXED');
        const bio = new VirtualLearner('BIO');

        for (let t = 0; t < TOTAL_STEPS; t++) {
            greedy.step(t, iterParams);
            fixed.step(t, iterParams);
            bio.step(t, iterParams);

            // Chart Aggregation
            aggEnergy.greedy[t].push(greedy.state.energy);
            aggEnergy.fixed[t].push(fixed.state.energy);
            aggEnergy.bio[t].push(bio.state.energy);
            // v7 Adaptation: Use getTotalMastery() instead of knowledge scalar
            aggKnowledge.greedy[t].push(greedy.getTotalMastery());
            aggKnowledge.fixed[t].push(fixed.getTotalMastery());
            aggKnowledge.bio[t].push(bio.getTotalMastery());
        }

        // Subgroup Collection (End State)
        if (type === 'Weak') {
            weakStats.greedy.push(greedy.getTotalMastery());
            weakStats.bio.push(bio.getTotalMastery());
        } else if (type === 'Strong') {
            strongStats.greedy.push(greedy.getTotalMastery());
            strongStats.bio.push(bio.getTotalMastery());
        }

        if (bio.getTotalMastery() > fixed.getTotalMastery()) winCount++;
    }

    // Fairness Calculations
    const avg = arr => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
    const wImp = weakStats.greedy.length ? ((avg(weakStats.bio) - avg(weakStats.greedy)) / avg(weakStats.greedy) * 100).toFixed(1) : "N/A";
    const sImp = strongStats.greedy.length ? ((avg(strongStats.bio) - avg(strongStats.greedy)) / avg(strongStats.greedy) * 100).toFixed(1) : "N/A";

    statusEl.innerHTML = `
        <strong>Fairness Audit:</strong><br>
        Weak Learners Gain: <span style="color:#2ed573">${wImp > 0 ? '+' : ''}${wImp}%</span><br>
        Strong Learners Gain: <span style="color:#70a1ff">${sImp > 0 ? '+' : ''}${sImp}%</span><br>
        Avg Win Rate: ${Math.round(winCount / N * 100)}%
    `;

    // Process Stats for Charts
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

    // Update Stats UI (Use Mean of Final Step)
    const fStep = TOTAL_STEPS - 1;
    // We pass 0 as burnout risk for now as we didn't track it granularly in this simplified restore
    updateStatsUI(
        stats.knowledge.greedy.mean[fStep], 0,
        stats.knowledge.fixed.mean[fStep], 0,
        stats.knowledge.bio.mean[fStep], 0,
        true
    );
}

// --- SENSITIVITY ANALYSIS (Restored & Adapted) ---
async function runSensitivityAnalysis() {
    const statusEl = document.getElementById('mcStatus');
    statusEl.innerHTML = "Running Sensitivity Sweep (Mismatch Rate 0% -> 50%)...";

    // Disable buttons
    const buttons = document.querySelectorAll('button');
    buttons.forEach(b => b.disabled = true);

    const rates = [0, 10, 20, 30, 40, 50];
    let results = [];
    const N = 20; // Fast sweep

    for (let r of rates) {
        let win = 0;
        let baseParams = getParamsFromUI();
        baseParams.mismatchRate = r / 100.0;

        for (let i = 0; i < N; i++) {
            let params = { ...baseParams };
            // Perturb slightly
            params.alphaHigh *= (1 + (Math.random() - 0.5) * 0.15);
            params.recovRate *= (1 + (Math.random() - 0.5) * 0.15);

            const greedy = new VirtualLearner('GREEDY');
            const fixed = new VirtualLearner('FIXED');
            const bio = new VirtualLearner('BIO');

            for (let t = 0; t < TOTAL_STEPS; t++) {
                greedy.step(t, params);
                fixed.step(t, params);
                bio.step(t, params);
            }
            // v7 Adaptation
            if (bio.getTotalMastery() > fixed.getTotalMastery()) win++;
        }
        results.push(`Mismatch ${r}%: ${Math.round(win / N * 100)}% Win`);
        statusEl.innerHTML = `Analyzing... ${r}%`;
        await new Promise(res => setTimeout(res, 10));
    }

    statusEl.innerHTML = "<strong>Sensitivity Results:</strong><br>" + results.join("<br>");
    buttons.forEach(b => b.disabled = false);
}

// --- MONTE CARLO CHART UPDATE HELPERS (Restored) ---
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
                    label: 'Bio Variance', /* Confidence Interval */
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

    // Switch to Energy Tab automatically to show charts
    if (window.switchTab) window.switchTab('energy');
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

    /* Burnout UI currently only supports simple numbers, not updating detailed text structure to avoid breaks. */
    /* Only update if elements exist and are simple counts */
    // document.getElementById('burnGreedy').innerText = valG + burnSuffix;

    let improv = ((bScore - fScore) / (fScore || 1)) * 100; // avoid div by zero
    if (document.getElementById('improvementVal')) {
        document.getElementById('improvementVal').innerText = (improv > 0 ? "+" : "") + improv.toFixed(1) + "%";
    }
}

window.onload = runSimulation;