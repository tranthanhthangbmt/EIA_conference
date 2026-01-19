// ==========================================
// 1. GRAPH DEFINITION (DAG + SUBJECTS)
// ==========================================
const K_GRAPH = {
    'A': { id: 'A', label: 'Intro AI', level: 0, difficulty: 0.3, parents: [], subject: 'Theory', color: '#3b82f6' },
    'B': { id: 'B', label: 'Python Basics', level: 0, difficulty: 0.3, parents: [], subject: 'Theory', color: '#3b82f6' },
    'C': { id: 'C', label: 'ML Algos', level: 1, difficulty: 0.6, parents: ['A'], subject: 'Coding', color: '#f59e0b' },
    'D': { id: 'D', label: 'Data Proc', level: 1, difficulty: 0.6, parents: ['B'], subject: 'Coding', color: '#f59e0b' },
    'E': { id: 'E', label: 'Deep Learning', level: 2, difficulty: 0.8, parents: ['C', 'D'], subject: 'Math', color: '#ef4444' },
    'F': { id: 'F', label: 'Transformer', level: 3, difficulty: 1.0, parents: ['E'], subject: 'Math', color: '#ef4444' }
};
const NODE_IDS = Object.keys(K_GRAPH);

// GLOBALS
let greedyAgent, bioAgent;
let greedyData, bioData;
let simulationInterval;
let SIM_SPEED = 200; // Slower for cognitive inertia visibility
let chartEnergy, chartFlow, radarChart;

// PARAMS
const PARAMS = { recovRate: 15, nonLinear: true };

// ==========================================
// 2. PSYCHOMETRIC AGENT LOGIC (v10.0)
// ==========================================
class GraphAgent {
    constructor(name, strategy) {
        this.name = name;
        this.strategy = strategy;

        // Physical State
        this.energy = 100;
        this.mastery = { 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0 };

        // Context State
        this.currentNode = null;
        this.lastNode = null;
        this.burnoutCount = 0;

        // Psychological State (New for Q1 Paper)
        this.stress = 0;       // 0-100: Anxiety level
        this.focus = 100;      // 0-100: Attention span
        this.satisfaction = 50; // 0-100: Valence
        this.currentEmotion = "Neutral";
        this.statusMsg = "Ready";

        this.logEnergy = [];
    }

    step() {
        // --- 1. BIOLOGICAL UPDATE ---
        // Recover if resting
        if (this.currentNode === null) {
            this.energy = Math.min(100, this.energy + 10);
            this.stress = Math.max(0, this.stress - 15); // Rest reduces stress fast
            this.focus = Math.min(100, this.focus + 10);
        }

        // --- 2. DECISION MAKING (CONTROLLER) ---
        // Burnout Override
        if (this.energy < 15 || this.stress > 90) {
            this.currentNode = null;
            this.currentEmotion = "Burnout";
            this.statusMsg = "FORCE REST (Bio-Safety)";
            return { action: 'REST', reason: "Bio-Safety Triggered" };
        }

        let targetNode = null;
        let unlockeds = NODE_IDS.filter(id => {
            if (this.mastery[id] >= 100) return false;
            let parents = K_GRAPH[id].parents;
            if (parents.length === 0) return true;
            return parents.every(p => this.mastery[p] >= 80);
        });

        // STRATEGY LOGIC
        if (this.strategy === 'GREEDY') {
            // Ignorant of Stress/Switching Cost
            if (unlockeds.length > 0) {
                unlockeds.sort((a, b) => K_GRAPH[b].level - K_GRAPH[a].level);
                targetNode = unlockeds[0];
            }
        }
        else if (this.strategy === 'BIO') {
            // Context-Aware & Affective Computing
            let bestScore = -Infinity;

            unlockeds.forEach(nodeId => {
                let node = K_GRAPH[nodeId];
                let score = node.level * 10; // Base utility

                // Penalty for Switching Subject (Cognitive Load)
                if (this.lastNode && K_GRAPH[this.lastNode].subject !== node.subject) {
                    score -= 15; // Context Switch Penalty
                }

                // Penalty for Difficulty if Energy Low
                if (this.energy < 40 && node.difficulty > 0.6) {
                    score -= 50; // Avoid hard tasks when tired
                }

                if (score > bestScore) {
                    bestScore = score;
                    targetNode = nodeId;
                }
            });

            // If no good option, chose to Rest proactively
            if (bestScore < 0) targetNode = null;
        }

        // --- 3. EXECUTION & PSYCHOMETRICS ---
        if (!targetNode) {
            this.currentNode = null;
            this.currentEmotion = "Relieved";
            this.statusMsg = "Strategic Rest";
            return { action: 'REST', reason: "Strategic Recovery" };
        }

        // Context Switching Effect
        let isSwitch = this.lastNode && K_GRAPH[this.lastNode].subject !== K_GRAPH[targetNode].subject;
        if (isSwitch) {
            this.focus = Math.max(0, this.focus - 20); // Switching breaks focus
            this.stress = Math.min(100, this.stress + 10); // Switching adds cognitive load
        } else {
            this.focus = Math.min(100, this.focus + 5); // Continuity builds focus
        }

        // Learning Physics
        let difficulty = K_GRAPH[targetNode].difficulty;
        let cost = (difficulty * 10) + (isSwitch ? 5 : 0);

        // Stress Calculation (Yerkes-Dodson Law)
        // Strain = Difficulty vs Capacity (Energy + Focus)
        let strain = (difficulty * 100) - (this.energy * 0.5 + this.focus * 0.5);
        if (strain > 0) this.stress = Math.min(100, this.stress + strain * 0.2);
        else this.stress = Math.max(0, this.stress - 5); // Easy task relaxes

        // Update Energy
        this.energy = Math.max(0, this.energy - cost);

        // Gain depends on Focus (Flow state)
        let efficiency = this.focus / 100;
        if (this.stress > 80) efficiency *= 0.2; // High anxiety blocks learning

        let gain = 10 * efficiency;
        this.mastery[targetNode] = Math.min(100, this.mastery[targetNode] + gain);

        // Update Emotion Label
        if (this.stress > 80) this.currentEmotion = "Anxious";
        else if (this.focus > 80 && this.energy > 50) this.currentEmotion = "Flow";
        else if (this.energy < 30) this.currentEmotion = "Exhausted";
        else this.currentEmotion = "Focused";

        this.statusMsg = `Learning ${K_GRAPH[targetNode].label}`;
        this.lastNode = this.currentNode;
        this.currentNode = targetNode;

        return {
            action: 'LEARN',
            target: targetNode,
            switch: isSwitch,
            reason: `Learning ${K_GRAPH[targetNode].subject}`
        };
    }

    logHistory() {
        this.logEnergy.push(this.energy);
        if (this.logEnergy.length > 100) this.logEnergy.shift();
    }

    getAverageMastery() {
        return Math.round(NODE_IDS.reduce((a, b) => a + this.mastery[b], 0) / NODE_IDS.length);
    }
}

// ==========================================
// 3. VISUALIZATION
// ==========================================
function initVisNetwork(containerId) {
    let nodes = NODE_IDS.map(id => ({
        id: id,
        label: K_GRAPH[id].label + "\n0%",
        level: K_GRAPH[id].level,
        shape: 'box',
        font: { color: 'white' },
        color: { background: '#334155', border: K_GRAPH[id].color },
        borderWidth: 2
    }));

    let edges = [];
    NODE_IDS.forEach(id => {
        K_GRAPH[id].parents.forEach(p => edges.push({ from: p, to: id, arrows: 'to' }));
    });

    let data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
    let options = {
        layout: { hierarchical: { direction: 'LR', sortMethod: 'directed', levelSeparation: 120 } },
        physics: false,
        nodes: { borderWidthSelected: 4 }
    };

    return { net: new vis.Network(document.getElementById(containerId), data, options), nodes: data.nodes };
}

function updateAgentVis(agent, visData) {
    let updates = [];
    NODE_IDS.forEach(id => {
        let m = agent.mastery[id];
        let bg = '#334155';
        if (m >= 100) bg = '#10b981';
        else if (m > 0) bg = '#64748b';

        // Highlight Active
        let borderColor = K_GRAPH[id].color;
        if (agent.currentNode === id) {
            bg = K_GRAPH[id].color;
        }

        updates.push({
            id: id,
            label: `${K_GRAPH[id].label}\n${Math.round(m)}%`,
            color: { background: bg, border: borderColor }
        });
    });
    visData.nodes.update(updates);
}

function logToConsole(agentName, result) {
    let consoleEl = document.getElementById('console-log');
    let line = document.createElement('div');
    line.className = 'log-line ' + (agentName === 'Greedy' ? 'greedy' : 'bio');
    let time = new Date().toLocaleTimeString().split(' ')[0];

    let content = `[${time}] ${agentName}: ${result.reason}`;
    if (result.switch) content += " 🔄 (Switch)";

    line.innerText = content;
    consoleEl.prepend(line);

    if (consoleEl.childElementCount > 20) consoleEl.lastChild.remove();
}

// --- CHARTS (Including New Radar) ---
function initRadar() {
    const ctx = document.getElementById('radarChart').getContext('2d');
    if (radarChart) radarChart.destroy();

    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Energy', 'Focus', 'Low Stress', 'Satisfaction'],
            datasets: [
                {
                    label: 'Greedy',
                    data: [100, 100, 100, 50],
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    borderColor: '#ef4444',
                    borderWidth: 2
                },
                {
                    label: 'Bio-PKT',
                    data: [100, 100, 100, 50],
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderColor: '#10b981',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: 'rgba(255,255,255,0.1)' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    pointLabels: { color: '#cbd5e1', font: { size: 10 } },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            },
            plugins: { legend: { display: false } },
            animation: false
        }
    });
}

function updateRadar() {
    if (!radarChart) return;

    // Greedy Metrics
    radarChart.data.datasets[0].data = [
        greedyAgent.energy,
        greedyAgent.focus,
        100 - greedyAgent.stress, // Invert stress for radar (Out is good)
        greedyAgent.satisfaction
    ];

    // Bio Metrics
    radarChart.data.datasets[1].data = [
        bioAgent.energy,
        bioAgent.focus,
        100 - bioAgent.stress,
        bioAgent.satisfaction
    ];

    radarChart.update();
}

function initCharts() {
    const ctxE = document.getElementById('energyChart').getContext('2d');
    if (chartEnergy) chartEnergy.destroy();
    chartEnergy = new Chart(ctxE, {
        type: 'line',
        data: {
            labels: Array(100).fill(0).map((_, i) => i),
            datasets: [
                { label: 'Greedy E', data: [], borderColor: '#ef4444', borderWidth: 2, tension: 0.3 },
                { label: 'Bio-PKT E', data: [], borderColor: '#10b981', borderWidth: 2, tension: 0.3 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: { x: { display: false }, y: { min: 0, max: 100, grid: { color: '#334155' } } },
            plugins: { legend: { display: false } }
        }
    });

    const ctxF = document.getElementById('flowChart').getContext('2d');
    if (chartFlow) chartFlow.destroy();

    // Define Quadrant Boxes
    const boxAnnotations = {
        box1: { type: 'box', xMin: 0, xMax: 50, yMin: 1.5, yMax: 3.5, backgroundColor: 'rgba(239, 68, 68, 0.2)', borderWidth: 0, label: { content: 'ANXIETY 😨', display: true, color: '#f87171', font: { size: 14, weight: 'bold' } } },
        box2: { type: 'box', xMin: 50, xMax: 100, yMin: 1.5, yMax: 3.5, backgroundColor: 'rgba(16, 185, 129, 0.2)', borderWidth: 0, label: { content: 'FLOW 🤩', display: true, color: '#34d399', font: { size: 14, weight: 'bold' } } },
        box3: { type: 'box', xMin: 0, xMax: 50, yMin: 0, yMax: 1.5, backgroundColor: 'rgba(56, 189, 248, 0.2)', borderWidth: 0, label: { content: 'RECOVERY 😌', display: true, color: '#7dd3fc', font: { size: 14, weight: 'bold' } } },
        box4: { type: 'box', xMin: 50, xMax: 100, yMin: 0, yMax: 1.5, backgroundColor: 'rgba(251, 191, 36, 0.2)', borderWidth: 0, label: { content: 'BOREDOM 🥱', display: true, color: '#fcd34d', font: { size: 14, weight: 'bold' } } }
    };

    chartFlow = new Chart(ctxF, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Greedy Trail',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: '#ef4444',
                    borderWidth: 2,
                    showLine: true,
                    tension: 0.4,
                    pointRadius: 4
                },
                {
                    label: 'Bio-PKT Trail',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: '#10b981',
                    borderWidth: 2,
                    showLine: true,
                    tension: 0.4,
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: { duration: 0 },
            scales: {
                x: { min: 0, max: 100, title: { display: true, text: 'Energy (Resources)', color: '#94a3b8' }, grid: { color: '#334155' } },
                y: { min: 0, max: 3.5, title: { display: true, text: 'Difficulty (Challenge)', color: '#94a3b8' }, grid: { color: '#334155' } }
            },
            plugins: {
                legend: { labels: { color: '#e2e8f0' } },
                annotation: { annotations: boxAnnotations }
            }
        }
    });
}

function updateCharts() {
    if (chartEnergy) {
        chartEnergy.data.datasets[0].data = greedyAgent.logEnergy;
        chartEnergy.data.datasets[1].data = bioAgent.logEnergy;
        chartEnergy.update('none');
    }
    if (chartFlow) {
        let gY = greedyAgent.currentNode ? K_GRAPH[greedyAgent.currentNode].level : 0;
        let bY = bioAgent.currentNode ? K_GRAPH[bioAgent.currentNode].level : 0;

        if (Math.abs(greedyAgent.energy - bioAgent.energy) < 2 && gY === bY) {
            gY += 0.1;
        }

        let gData = chartFlow.data.datasets[0].data;
        let bData = chartFlow.data.datasets[1].data;

        gData.push({ x: greedyAgent.energy, y: gY });
        bData.push({ x: bioAgent.energy, y: bY });

        if (gData.length > 15) gData.shift();
        if (bData.length > 15) bData.shift();

        chartFlow.update('none');
    }
    updateRadar();
}

// --- MAIN LOOP ---
function runLiveSimulation() {
    if (simulationInterval) clearInterval(simulationInterval);

    greedyAgent = new GraphAgent("Greedy", "GREEDY");
    bioAgent = new GraphAgent("Bio-PKT", "BIO");

    greedyData = initVisNetwork('network-greedy');
    bioData = initVisNetwork('network-bio');
    initCharts();
    initRadar();

    document.getElementById('console-log').innerHTML = '';

    simulationInterval = setInterval(() => {
        let resG = greedyAgent.step();
        let resB = bioAgent.step();

        greedyAgent.logHistory();
        bioAgent.logHistory();

        updateAgentVis(greedyAgent, greedyData);
        updateAgentVis(bioAgent, bioData);
        updateCharts();

        // Update UI Stats
        updateUI(greedyAgent, 'Greedy');
        updateUI(bioAgent, 'Bio');

        // Log significant events
        if (Math.random() > 0.8 || resG.switch || resB.switch || resG.action === 'REST') {
            logToConsole('Greedy', resG);
            logToConsole('Bio-PKT', resB);
        }

        if (bioAgent.getAverageMastery() >= 100) clearInterval(simulationInterval);

    }, SIM_SPEED);
}

function updateUI(agent, prefix) {
    // New Psychometric UI
    document.getElementById(`score${prefix}`).innerText = agent.getAverageMastery() + "%";
    document.getElementById(`statusText${prefix}`).innerText = agent.statusMsg;

    document.getElementById(`stress${prefix}`).innerText = Math.round(agent.stress) + "%";
    document.getElementById(`flow${prefix}`).innerText = Math.round(agent.focus) + "%";

    let badge = document.getElementById(`badge${prefix}`);
    badge.innerText = agent.currentEmotion;

    // Color coding badge
    if (agent.currentEmotion === "Flow" || agent.currentEmotion === "Focused") badge.style.color = "#facc15";
    else if (agent.currentEmotion === "Anxious" || agent.currentEmotion === "Burnout") badge.style.color = "#ef4444";
    else badge.style.color = "#e2e8f0";

    // Overlay Text
    document.getElementById(`overlay-${prefix.toLowerCase()}`).innerText = `E: ${Math.round(agent.energy)}%`;
}

function updateSpeed(val) {
    SIM_SPEED = 510 - val;
    document.getElementById('valSpeed').innerText = SIM_SPEED + "ms";
    if (simulationInterval) { clearInterval(simulationInterval); runLiveSimulation(); }
}

function switchTab(tab) {
    document.getElementById('tab-graph').style.display = tab === 'graph' ? 'flex' : 'none';
    document.getElementById('tab-flow').style.display = tab === 'flow' ? 'flex' : 'none';
    document.getElementById('tab-energy').style.display = tab === 'energy' ? 'block' : 'none';

    if (tab === 'flow' && chartFlow) chartFlow.resize();
}

window.onload = runLiveSimulation;
