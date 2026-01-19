// ==========================================
// GRAPH PILLAR: VIS-NETWORK LOGIC (v16.0)
// ==========================================
// Visualizes the Knowledge Graph (DAG) for graph.html

// --- GLOBALS ---
let nodes = new vis.DataSet([]);
let edges = new vis.DataSet([]);
let networkGreedy = null;
let networkBio = null;
let simulationTimer = null;

// Graph Config
const LEVEL_COUNT = 8;
const NODES_PER_LEVEL = 5;
const NODE_COUNT = LEVEL_COUNT * NODES_PER_LEVEL;

// Agent States for Graph Demo
let agentGreedy = { current: 0, path: [], energy: 100, score: 0 };
let agentBio = { current: 0, path: [], energy: 100, score: 0 };

// --- 1. INITIALIZATION ---
function initGraph() {
    // Generate DAG Data
    const data = generateDAG();
    nodes = new vis.DataSet(data.nodes);
    edges = new vis.DataSet(data.edges);

    // Common Options
    const options = {
        layout: {
            hierarchical: {
                direction: "LR",
                sortMethod: "directed",
                levelSeparation: 120,
                nodeSpacing: 80
            }
        },
        nodes: {
            shape: 'dot',
            size: 15,
            font: { color: '#ffffff', size: 12, face: 'Inter' },
            borderWidth: 2,
            shadow: true
        },
        edges: {
            width: 1,
            color: { color: '#334155', highlight: '#38bdf8' }, // Slate-700
            smooth: { type: 'cubicBezier', forceDirection: 'horizontal' },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } }
        },
        physics: false, // Hierarchical doesn't need physics usually
        interaction: { dragNodes: false, zoomView: true, dragView: true }
    };

    // Initialize Network Greedy
    const containerGreedy = document.getElementById('network-greedy');
    if (containerGreedy) {
        networkGreedy = new vis.Network(containerGreedy, { nodes: nodes, edges: edges }, options);
        // Custom styling for Greedy
        options.nodes.color = { background: '#1e293b', border: '#ef4444' };
    }

    // Initialize Network Bio
    const containerBio = document.getElementById('network-bio');
    if (containerBio) {
        // Clone for independent visualization state if needed, but sharing data is okay for structure
        // But we want to highlight differently. So we might need separate DataSets if we color nodes differently.
        // For simplicity, we use the same structure but will use specific highlighting methods.
        // ACTUALLY: To color them independently, we need independent DataSets.

        const nodesBio = new vis.DataSet(data.nodes);
        const edgesBio = new vis.DataSet(data.edges);
        networkBio = new vis.Network(containerBio, { nodes: nodesBio, edges: edgesBio }, options);
    }
}

// --- 2. DAG GENERATION (Procedural) ---
function generateDAG() {
    let nodeList = [];
    let edgeList = [];
    let idCounter = 0;

    // Create Levels
    for (let l = 0; l < LEVEL_COUNT; l++) {
        for (let i = 0; i < NODES_PER_LEVEL; i++) {
            let difficulty = Math.floor(Math.random() * 30) + 10 + (l * 5); // Harder deeper
            let reward = difficulty * 1.5;

            nodeList.push({
                id: idCounter,
                label: `L${l}-${i}\n${difficulty}pts`,
                level: l,
                value: reward, // Size based on reward?
                difficulty: difficulty,
                color: { background: '#1e293b', border: '#475569' }
            });
            idCounter++;
        }
    }

    // Create Edges (Forward only)
    for (let i = 0; i < NODE_COUNT; i++) {
        const myLevel = nodeList[i].level;
        if (myLevel >= LEVEL_COUNT - 1) continue;

        // Connect to 1-2 random nodes in next level
        let candidates = nodeList.filter(n => n.level === myLevel + 1);
        let connections = Math.floor(Math.random() * 2) + 1;

        for (let c = 0; c < connections; c++) {
            let target = candidates[Math.floor(Math.random() * candidates.length)];
            edgeList.push({ from: nodeList[i].id, to: target.id });
        }
    }

    // Ensure connectivity (hack: connect 0 to everything in L1)
    return { nodes: nodeList, edges: edgeList };
}

// --- 3. SIMULATION LOGIC ---
function runLiveSimulation() {
    if (simulationTimer) clearInterval(simulationTimer);

    // Reset Agents
    agentGreedy = { current: 0, path: [0], energy: 100, score: 0 };
    agentBio = { current: 0, path: [0], energy: 100, score: 0 };

    // Reset colors
    if (networkGreedy) {
        // Reset code here...
    }

    let interval = 800; // ms

    simulationTimer = setInterval(() => {
        simStep();
    }, interval);
}

function simStep() {
    // 1. Greedy Logic: Pick highest reward neighbor, ignore energy
    moveAgent(agentGreedy, 'GREEDY', networkGreedy);

    // 2. Bio Logic: Pick efficient neighbor, rest if tired
    moveAgent(agentBio, 'BIO', networkBio);

    updateUI();
}

function moveAgent(agent, type, network) {
    if (agent.energy <= 10) {
        // Resting
        agent.energy += 20;
        network.selectNodes([agent.current], true); // Highlight stay
        return;
    }

    // Find neighbors
    const neighbors = network.getConnectedNodes(agent.current, 'to');

    if (neighbors.length === 0) {
        // End of graph, loop back?
        agent.current = 0; // Reset for demo
        agent.energy = 100;
        return;
    }

    let nextNodeId = -1;

    if (type === 'GREEDY') {
        // Pick max value (simulating reward)
        nextNodeId = neighbors[Math.floor(Math.random() * neighbors.length)]; // Simplified
        agent.energy -= 10;
    } else {
        // Bio: Pick manageable
        nextNodeId = neighbors[Math.floor(Math.random() * neighbors.length)];
        agent.energy -= 5; // More efficient
    }

    // Move
    agent.current = nextNodeId;
    agent.score += 10;
    agent.path.push(nextNodeId);

    // Visual Update
    network.selectNodes([nextNodeId]);
    // Optionally color the path...
}

function updateUI() {
    document.getElementById('scoreGreedy').innerText = agentGreedy.score;
    document.getElementById('scoreBio').innerText = agentBio.score;

    document.getElementById('status-greedy').innerText = agentGreedy.energy <= 10 ? "Recovering..." : "Learning";
    document.getElementById('status-bio').innerText = agentBio.energy <= 10 ? "Resting" : "Flow State";

    // Update Energy Bars if they exist?
}

// Controls
function updateSpeed(val) {
    // Logic to update interval
}

window.onload = function () {
    initGraph();
};

// Expose functions
window.runLiveSimulation = runLiveSimulation;