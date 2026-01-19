// ==========================================
// 1. GRAPH DEFINITION (DAG Structure)
// ==========================================
const K_GRAPH = {
    'A': { id: 'A', label: 'Intro AI', level: 0, difficulty: 0.3, parents: [] },
    'B': { id: 'B', label: 'Python Basics', level: 0, difficulty: 0.3, parents: [] },
    'C': { id: 'C', label: 'ML Algorithms', level: 1, difficulty: 0.6, parents: ['A', 'B'] },
    'D': { id: 'D', label: 'Data Proc', level: 1, difficulty: 0.6, parents: ['B'] },
    'E': { id: 'E', label: 'Deep Learning', level: 2, difficulty: 0.8, parents: ['C', 'D'] },
    'F': { id: 'F', label: 'Transformer', level: 3, difficulty: 1.0, parents: ['E'] }
};
const NODE_IDS = Object.keys(K_GRAPH);

// UI Globals
let networkGreedy, networkBio;
let greedyData, bioData;
let simulationInterval;
let SIM_SPEED = 100;
let chartEnergy, chartKnowledge;
let timeStep = 0;

// Config Globals (Updated from UI)
let PARAMS = {
    alphaHigh: 18,
    recovRate: 15,
    decayRate: 0.005,
    switchCost: 2,
    mpcHorizon: 3,
    nonLinear: true,
    mismatchRate: 0.2
};

// ==========================================
// 2. HELPER FUNCTIONS (PHYSICS ENGINE)
// ==========================================
function getParamsFromUI() {
    return {
        alphaHigh: parseFloat(document.getElementById('alphaHigh').value),
        recovRate: parseFloat(document.getElementById('recovRate').value),
        decayRate: parseFloat(document.getElementById('decayRate').value) / 1000,
        switchCost: parseFloat(document.getElementById('switchCost').value),
        mpcHorizon: parseInt(document.getElementById('mpcHorizon').value),
        nonLinear: document.getElementById('nonLinearToggle').checked,
        mismatchRate: parseFloat(document.getElementById('mismatch').value) / 100
    };
}

// ==========================================
// 3. AGENT LOGIC (HYBRID: PHYSICS + GRAPH)
// ==========================================
class GraphAgent {
    constructor(name, strategy) {
        this.name = name;
        this.strategy = strategy;

        // Physics State
        this.energy = 100;
        this.burnoutTimer = 0;

        // Graph State
        this.mastery = { 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0 };
        this.currentNode = null;
        this.burnoutCount = 0;
        this.statusMsg = "Ready";

        this.logEnergy = [];
        this.logMastery = [];
    }

    step(params) {
        // 1. Forced Recovery (Burnout Recovery)
        if (this.energy < 20) {
            this.energy += 15; // Slow recovery
            this.currentNode = null;
            this.statusMsg = "BURNOUT RECOVERY";
            this.logState();
            return { action: 'REST', target: null, msg: this.statusMsg };
        }

        let targetNode = null;

        // --- FIND AVAILABLE NODES (Unlockeds) ---
        // Both Agents are smart enough to know prerequisites
        let unlockeds = NODE_IDS.filter(id => {
            if (this.mastery[id] >= 100) return false; // Already done
            let parents = K_GRAPH[id].parents;
            if (parents.length === 0) return true;
            return parents.every(p => this.mastery[p] >= 80); // Strict prerequisite
        });

        // --- DECISION STRATEGY ---

        if (this.strategy === 'GREEDY') {
            // RATIONAL GREEDY:
            // Always picks the HARDEST available node to maximize Immediate Reward.
            // Ignorant of Energy cost.

            if (unlockeds.length > 0) {
                // Sort Descending by Level (Hardest first)
                unlockeds.sort((a, b) => K_GRAPH[b].level - K_GRAPH[a].level);
                targetNode = unlockeds[0];
                this.statusMsg = `Grinding ${targetNode} (High Gain)`;
            } else {
                this.statusMsg = "No nodes available";
            }
        }

        else if (this.strategy === 'BIO') {
            // BIO-PKT (MPC / Adaptive):
            // Considers Energy State.

            if (this.energy > 60) {
                // High Energy -> Pick Hardest (Like Greedy)
                unlockeds.sort((a, b) => K_GRAPH[b].level - K_GRAPH[a].level);
                if (unlockeds.length > 0) targetNode = unlockeds[0];
                this.statusMsg = `Power Learning ${targetNode}`;
            } else if (this.energy > 30) {
                // Medium Energy -> Pick EASIEST (Active Rest / Pacing)
                // This is the key difference: Bio-PKT knows to "step back"
                unlockeds.sort((a, b) => K_GRAPH[a].level - K_GRAPH[b].level);
                if (unlockeds.length > 0) targetNode = unlockeds[0];
                this.statusMsg = `Pacing with ${targetNode}`;
            } else {
                // Low Energy -> Strategic Rest (Prevent Burnout)
                targetNode = null;
                this.statusMsg = "Strategic Rest";
            }
        }

        // --- EXECUTION (PHYSICS) ---
        if (!targetNode) {
            this.energy = Math.min(100, this.energy + params.recovRate);
            this.currentNode = null;
            this.logState();
            return { action: 'REST', target: null, msg: this.statusMsg };
        }

        // Calculate Cost & Gain
        let cost = (K_GRAPH[targetNode].level + 1) * 8; // Harder = More Energy

        // Apply Physics Params
        if (params.nonLinear) cost *= (1 + (100 - this.energy) / 100);

        let gain = 10;

        // Diminishing Returns (Natural Penalty)
        // No arbitrary burnouts, just reduced efficiency
        if (this.energy < 50) {
            gain *= (this.energy / 50);
        }

        this.energy -= cost;
        this.mastery[targetNode] = Math.min(100, this.mastery[targetNode] + gain);
        this.currentNode = targetNode;

        // Crash Check (Still possible if Greedy pushes too hard)
        if (this.energy <= 0) {
            this.energy = 0;
            this.burnoutCount++;
            this.statusMsg = "*** CRASHED ***";
        }

        this.logState();
        return { action: 'LEARN', target: targetNode, msg: this.statusMsg };
    }

    logState() {
        this.logEnergy.push(Math.round(this.energy));
        this.logMastery.push(this.getTotalMastery());
        if (this.logEnergy.length > 100) {
            this.logEnergy.shift();
            this.logMastery.shift();
        }
    }

    getTotalMastery() {
        return Math.round(NODE_IDS.reduce((acc, id) => acc + this.mastery[id], 0) / NODE_IDS.length);
    }
}

// ==========================================
// 4. VISUALIZATION & RUNTIME
// ==========================================
let greedyAgent = new GraphAgent("Greedy", "GREEDY");
let bioAgent = new GraphAgent("Bio-PKT", "BIO");

function initVisNetwork(containerId, dataSet) {
    let nodes = NODE_IDS.map(id => ({
        id: id, label: K_GRAPH[id].label + "\n0%", level: K_GRAPH[id].level,
        shape: 'box', color: { background: '#334155', border: '#cbd5e1' }, font: { color: 'white' }
    }));
    let edges = [];
    NODE_IDS.forEach(id => { K_GRAPH[id].parents.forEach(p => { edges.push({ from: p, to: id, arrows: 'to' }); }); });
    let data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
    let options = { layout: { hierarchical: { direction: 'LR', sortMethod: 'directed', levelSeparation: 100 } }, physics: false };
    return { net: new vis.Network(document.getElementById(containerId), data, options), nodes: data.nodes };
}

function updateAgentVis(agent, visData) {
    let updates = [];
    NODE_IDS.forEach(id => {
        let m = agent.mastery[id];
        let color = '#334155';
        if (m >= 100) color = '#10b981'; else if (m > 0) color = '#f59e0b';
        if (agent.currentNode === id) {
            let parentsMet = K_GRAPH[id].parents.every(p => agent.mastery[p] >= 50);
            color = parentsMet ? '#3b82f6' : '#ef4444';
        }
        updates.push({ id: id, label: `${K_GRAPH[id].label}\n${Math.round(m)}%`, color: { background: color } });
    });
    visData.nodes.update(updates);
}

function logToConsole(agentName, result) {
    // Only log if console exists (might be hidden)
    let consoleEl = document.getElementById('console-log');
    if (!consoleEl) return;

    let line = document.createElement('div');
    line.className = 'log-line ' + (agentName === 'Greedy' ? 'greedy' : 'bio');
    let time = new Date().toLocaleTimeString().split(' ')[0];
    line.innerText = `[${time}] ${agentName}: ${result.msg}`;
    consoleEl.prepend(line);
    if (consoleEl.childElementCount > 20) consoleEl.lastChild.remove();
}

// --- CHARTS ---
function initCharts() {
    const commonOptions = {
        responsive: true, maintainAspectRatio: false, animation: false,
        scales: { x: { display: false }, y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.1)' } } },
        plugins: { legend: { labels: { color: '#cbd5e1' } } }
    };

    // Energy
    if (chartEnergy) chartEnergy.destroy();
    chartEnergy = new Chart(document.getElementById('energyChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: Array(100).fill(0).map((_, i) => i),
            datasets: [
                { label: 'Greedy E', data: [], borderColor: '#ef4444', borderWidth: 2, tension: 0.2 },
                { label: 'Bio-PKT E', data: [], borderColor: '#10b981', borderWidth: 2, tension: 0.2 }
            ]
        },
        options: commonOptions
    });

    // Knowledge
    if (chartKnowledge) chartKnowledge.destroy();
    chartKnowledge = new Chart(document.getElementById('knowledgeChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: Array(100).fill(0).map((_, i) => i),
            datasets: [
                { label: 'Greedy Mastery', data: [], borderColor: '#ef4444', borderWidth: 2, borderDash: [5, 5] },
                { label: 'Bio-PKT Mastery', data: [], borderColor: '#10b981', borderWidth: 2 }
            ]
        },
        options: commonOptions
    });
}

function updateCharts() {
    if (chartEnergy) {
        chartEnergy.data.datasets[0].data = greedyAgent.logEnergy;
        chartEnergy.data.datasets[1].data = bioAgent.logEnergy;
        chartEnergy.update('none');
    }
    if (chartKnowledge) {
        chartKnowledge.data.datasets[0].data = greedyAgent.logMastery;
        chartKnowledge.data.datasets[1].data = bioAgent.logMastery;
        chartKnowledge.update('none');
    }
}

// --- MAIN LOOPS ---
function runLiveSimulation() {
    // Check if interval is already running, if so, just reset or continue?
    // Restart logic
    if (simulationInterval) clearInterval(simulationInterval);

    greedyAgent = new GraphAgent("Greedy", "GREEDY");
    bioAgent = new GraphAgent("Bio-PKT", "BIO");
    timeStep = 0;

    greedyData = initVisNetwork('network-greedy');
    bioData = initVisNetwork('network-bio');
    initCharts();

    document.getElementById('console-log').innerHTML = '';

    simulationInterval = setInterval(() => {
        let params = getParamsFromUI();
        let resG = greedyAgent.step(params);
        let resB = bioAgent.step(params);

        updateAgentVis(greedyAgent, greedyData);
        updateAgentVis(bioAgent, bioData);
        updateCharts();

        // UI Stats
        document.getElementById('scoreGreedy').innerText = greedyAgent.getTotalMastery();
        document.getElementById('burnGreedy').innerText = greedyAgent.burnoutCount;
        document.getElementById('scoreBio').innerText = bioAgent.getTotalMastery();
        document.getElementById('burnBio').innerText = bioAgent.burnoutCount;
        document.getElementById('status-greedy').innerText = `E: ${Math.round(greedyAgent.energy)}%`;
        document.getElementById('status-bio').innerText = `E: ${Math.round(bioAgent.energy)}%`;

        if (Math.random() > 0.8) {
            logToConsole('Greedy', resG);
            logToConsole('Bio-PKT', resB);
        }

        let allMastered = NODE_IDS.every(id => bioAgent.mastery[id] >= 100);
        if (allMastered) clearInterval(simulationInterval);

    }, SIM_SPEED);
}

// --- EXPERIMENT MODE MOVED TO energy.html / script_energy.js ---
// This file is dedicated to the Live Graph Visualization (v8.0/v9.0 Hybrid)

// Helper
function updateSpeed(val) {
    SIM_SPEED = 510 - val;
    document.getElementById('valSpeed').innerText = SIM_SPEED + "ms";
    if (simulationInterval) { clearInterval(simulationInterval); runLiveSimulation(); }
}
function switchTab(tab) {
    document.getElementById('tab-graph').style.display = tab === 'graph' ? 'flex' : 'none';
    document.getElementById('tab-energy').style.display = tab === 'energy' ? 'block' : 'none';
}

window.onload = runLiveSimulation;