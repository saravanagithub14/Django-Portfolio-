// ===== Background Particle Effect =====
(function initParticles() {
    const canvas = document.getElementById('particle-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H;

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    const particles = [];
    const COUNT = 35; // Reduced from 60 — lighter on CPU

    for (let i = 0; i < COUNT; i++) {
        particles.push({
            x: Math.random() * W,
            y: Math.random() * H,
            r: Math.random() * 1.2 + 0.3,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            alpha: Math.random() * 0.3 + 0.05
        });
    }

    function draw() {
        ctx.clearRect(0, 0, W, H);
        for (const p of particles) {
            p.x += p.vx;
            p.y += p.vy;
            if (p.x < 0) p.x = W;
            if (p.x > W) p.x = 0;
            if (p.y < 0) p.y = H;
            if (p.y > H) p.y = 0;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255,255,255,${p.alpha})`;
            ctx.fill();
        }
        requestAnimationFrame(draw);
    }
    // Delay particle start so D3 render gets full CPU priority on first frame
    setTimeout(draw, 500);
})();

// ===== Graph Setup =====
const container = document.getElementById('graph-container');
let width = container.clientWidth;
let height = container.clientHeight;

// Create SVG
const svg = d3.select('#graph-container').append('svg')
    .attr('width', width)
    .attr('height', height);

// ===== Glass Orb SVG Defs =====
const defs = svg.append('defs');

// --- Outer glow blur filter (wide soft halo) ---
const glowFilter = defs.append('filter').attr('id', 'glass-glow')
    .attr('x', '-100%').attr('y', '-100%').attr('width', '300%').attr('height', '300%');
glowFilter.append('feGaussianBlur').attr('in', 'SourceGraphic').attr('stdDeviation', '5');

// --- Orb body gradient: dark navy edges, blue-purple inner lit zone ---
// Mimics the reference: dark outer shell, glow from within, deep translucent glass
const orbBody = defs.append('radialGradient').attr('id', 'glass-0')
    .attr('cx', '42%').attr('cy', '38%').attr('r', '58%')
    .attr('fx', '36%').attr('fy', '32%');
orbBody.append('stop').attr('offset', '0%')
    .attr('stop-color', '#b8b4e8').attr('stop-opacity', 0.55);    // bright specular top-left
orbBody.append('stop').attr('offset', '22%')
    .attr('stop-color', '#7b6fc4').attr('stop-opacity', 0.35);    // mid purple
orbBody.append('stop').attr('offset', '55%')
    .attr('stop-color', '#3d2f8f').attr('stop-opacity', 0.55);    // deep purple body
orbBody.append('stop').attr('offset', '80%')
    .attr('stop-color', '#1a1048').attr('stop-opacity', 0.75);    // near-black edge
orbBody.append('stop').attr('offset', '100%')
    .attr('stop-color', '#0a0620').attr('stop-opacity', 0.85);    // dark rim

// Depth-1 variant (slightly smaller/dimmer)
const orb1 = defs.append('radialGradient').attr('id', 'glass-1')
    .attr('cx', '42%').attr('cy', '38%').attr('r', '58%').attr('fx', '36%').attr('fy', '32%');
orb1.append('stop').attr('offset', '0%').attr('stop-color', '#a09cdc').attr('stop-opacity', 0.5);
orb1.append('stop').attr('offset', '25%').attr('stop-color', '#6358b0').attr('stop-opacity', 0.3);
orb1.append('stop').attr('offset', '60%').attr('stop-color', '#2e2270').attr('stop-opacity', 0.5);
orb1.append('stop').attr('offset', '100%').attr('stop-color', '#080418').attr('stop-opacity', 0.8);

// Depth-2
const orb2 = defs.append('radialGradient').attr('id', 'glass-2')
    .attr('cx', '42%').attr('cy', '38%').attr('r', '58%').attr('fx', '36%').attr('fy', '32%');
orb2.append('stop').attr('offset', '0%').attr('stop-color', '#8880cc').attr('stop-opacity', 0.45);
orb2.append('stop').attr('offset', '30%').attr('stop-color', '#4d4298').attr('stop-opacity', 0.28);
orb2.append('stop').attr('offset', '70%').attr('stop-color', '#1e1555').attr('stop-opacity', 0.45);
orb2.append('stop').attr('offset', '100%').attr('stop-color', '#050310').attr('stop-opacity', 0.75);

// Depth-3
const orb3 = defs.append('radialGradient').attr('id', 'glass-3')
    .attr('cx', '42%').attr('cy', '38%').attr('r', '58%').attr('fx', '36%').attr('fy', '32%');
orb3.append('stop').attr('offset', '0%').attr('stop-color', '#6c68b8').attr('stop-opacity', 0.4);
orb3.append('stop').attr('offset', '35%').attr('stop-color', '#382f7a').attr('stop-opacity', 0.22);
orb3.append('stop').attr('offset', '100%').attr('stop-color', '#030210').attr('stop-opacity', 0.7);

// --- Inner luminous glow (the purple light from within) ---
const innerGlow = defs.append('radialGradient').attr('id', 'glass-inner')
    .attr('cx', '50%').attr('cy', '50%').attr('r', '50%');
innerGlow.append('stop').attr('offset', '0%').attr('stop-color', '#9080ff').attr('stop-opacity', 0.18);
innerGlow.append('stop').attr('offset', '40%').attr('stop-color', '#6040cc').attr('stop-opacity', 0.12);
innerGlow.append('stop').attr('offset', '75%').attr('stop-color', '#4020aa').attr('stop-opacity', 0.08);
innerGlow.append('stop').attr('offset', '100%').attr('stop-color', '#200880').attr('stop-opacity', 0.0);

// --- Halo gradient (outer soft purple glow) ---
const haloGrad = defs.append('radialGradient').attr('id', 'glass-halo')
    .attr('cx', '50%').attr('cy', '50%').attr('r', '50%');
haloGrad.append('stop').attr('offset', '0%').attr('stop-color', '#7755ff').attr('stop-opacity', 0.25);
haloGrad.append('stop').attr('offset', '60%').attr('stop-color', '#4422cc').attr('stop-opacity', 0.1);
haloGrad.append('stop').attr('offset', '100%').attr('stop-color', '#220088').attr('stop-opacity', 0);

// --- Specular highlight: tiny blue-white crescent ---
const specGrad = defs.append('radialGradient').attr('id', 'glass-shine')
    .attr('cx', '50%').attr('cy', '50%').attr('r', '50%');
specGrad.append('stop').attr('offset', '0%').attr('stop-color', '#dde8ff').attr('stop-opacity', 0.8);
specGrad.append('stop').attr('offset', '100%').attr('stop-color', '#9090ff').attr('stop-opacity', 0);



// Zoom layer
const zoomLayer = svg.append('g');

svg.call(d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
        zoomLayer.attr('transform', event.transform);
    })
);

const g = zoomLayer.append('g');

// ===== Build Hierarchy =====
let rootNode = d3.hierarchy(resumeData);

// Since all nodes are collapsed:false, all children are already available.
// Assign unique IDs
let idCounter = 0;
rootNode.descendants().forEach(d => {
    d.id = d.data.id || d.data.name || `node_${idCounter++}`;
});

// ===== Force Simulation =====
// Force multipliers (driven by sliders)
let forceParams = {
    centerStrength: 0.5,
    repelMultiplier: 0.9,
    linkStrength: 0.8,
    linkDistMultiplier: 0.9,
    animSpeed: 0.5
};

function linkDistFn(d) {
    const base = d.source.depth === 0 ? 120 : d.source.depth === 1 ? 80 : d.source.depth === 2 ? 55 : 40;
    return base * (0.3 + forceParams.linkDistMultiplier * 1.7);
}

function chargeFn(d) {
    const base = d.depth === 0 ? -600 : d.depth === 1 ? -250 : -120;
    return base * (0.1 + forceParams.repelMultiplier * 1.8);
}

const simulation = d3.forceSimulation()
    .velocityDecay(0.45)
    .alphaDecay(0.04)             // Was 0.015 — now settles ~3x faster
    .force('link', d3.forceLink().id(d => d.id).distance(linkDistFn).strength(forceParams.linkStrength))
    .force('charge', d3.forceManyBody().strength(chargeFn))
    .force('center', d3.forceCenter(width / 2, height / 2).strength(forceParams.centerStrength))
    .force('collide', d3.forceCollide().radius(d => {
        if (d.depth === 0) return 60;
        if (d.depth === 1) return 40;
        if (d.depth === 2) return 25;
        return 16;
    }))
    .stop(); // Start stopped — we'll kick it off after the loader

// ===== Rendering =====
function getRadius(depth) {
    if (depth === 0) return 22;
    if (depth === 1) return 12;
    if (depth === 2) return 7;
    return 4;
}

function render() {
    const allNodes = rootNode.descendants();
    const allLinks = rootNode.links();

    // --- Links ---
    const link = g.selectAll('.link')
        .data(allLinks, d => `${d.source.id}-${d.target.id}`);

    link.exit().transition().duration(300).attr('stroke-opacity', 0).remove();

    const linkEnter = link.enter().append('line')
        .attr('class', 'link')
        .attr('stroke-opacity', 0);

    const linkMerge = linkEnter.merge(link);

    // Fade links in
    linkMerge.transition().duration(800).attr('stroke-opacity', 1);

    // --- Nodes ---
    const node = g.selectAll('.node')
        .data(allNodes, d => d.id);

    node.exit().transition().duration(300).attr('opacity', 0).remove();

    const nodeEnter = node.enter().append('g')
        .attr('class', d => {
            let cls = `node depth-${d.depth}`;
            if (d.data.navigateTo) cls += ' navigable';
            return cls;
        })
        .attr('opacity', 0)
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // Cascade timing: each depth level starts after the previous fully appears
    // depth-0: 0ms, depth-1: 800ms, depth-2: 1600ms, depth-3: 2200ms
    function cascadeDelay(d) {
        const depthStart = [0, 800, 1600, 2200];
        const base = depthStart[Math.min(d.depth, 3)];
        // stagger siblings slightly so they ripple out (not all at once)
        const siblingIndex = d.parent ? d.parent.children.indexOf(d) : 0;
        return base + siblingIndex * 80;
    }

    // --- Solid mask behind the glass to hide link lines ---
    nodeEnter.append('circle')
        .attr('class', 'orb-mask')
        .attr('r', 0)
        .attr('fill', '#000000')
        .attr('pointer-events', 'none')
        .transition()
        .delay(d => cascadeDelay(d))
        .duration(700)
        .ease(d3.easeElasticOut.amplitude(0.8).period(0.5))
        .attr('r', d => getRadius(d.depth));

    // --- Glass orb base circle with gradient fill ---
    nodeEnter.append('circle')
        .attr('class', 'orb-base')
        .attr('r', 0)
        .attr('fill', d => `url(#glass-${Math.min(d.depth, 3)})`)
        .transition()
        .delay(d => cascadeDelay(d))
        .duration(700)
        .ease(d3.easeElasticOut.amplitude(0.8).period(0.5))
        .attr('r', d => getRadius(d.depth));

    // --- Inner glow rim-light (second layer) ---
    nodeEnter.append('circle')
        .attr('class', 'orb-inner')
        .attr('r', 0)
        .attr('fill', 'url(#glass-inner)')
        .attr('pointer-events', 'none')
        .transition()
        .delay(d => cascadeDelay(d) + 60)
        .duration(700)
        .ease(d3.easeElasticOut.amplitude(0.8).period(0.5))
        .attr('r', d => getRadius(d.depth));

    // --- Purple outer halo ---
    nodeEnter.each(function (d) {
        const r = getRadius(d.depth);
        d3.select(this).insert('circle', ':first-child')
            .attr('class', 'orb-glow')
            .attr('r', 0)
            .attr('fill', 'url(#glass-halo)')
            .attr('filter', 'url(#glass-glow)')
            .attr('pointer-events', 'none')
            .transition()
            .delay(cascadeDelay(d))
            .duration(700)
            .ease(d3.easeElasticOut.amplitude(0.8).period(0.5))
            .attr('r', r * 2.2);
    });

    // --- Spinning specular highlight (small bright ellipse that orbits) ---
    nodeEnter.each(function (d) {
        const r = getRadius(d.depth);
        const highlight = d3.select(this).append('ellipse')
            .attr('class', 'orb-shine')
            .attr('cx', -r * 0.25)
            .attr('cy', -r * 0.3)
            .attr('rx', r * 0.35)
            .attr('ry', r * 0.18)
            .attr('fill', 'url(#glass-shine)')
            .attr('opacity', 0)
            .attr('pointer-events', 'none');

        highlight.transition()
            .delay(cascadeDelay(d) + 500)
            .duration(400)
            .attr('opacity', d.depth === 0 ? 0.9 : d.depth === 1 ? 0.7 : 0.5);
    });

    // --- Labels ---
    nodeEnter.append('text')
        .attr('dy', d => d.depth === 0 ? 35 : 22)
        .attr('text-anchor', 'middle')
        .text(d => d.data.name)
        .style('font-size', d => {
            if (d.depth === 0) return '16px';
            if (d.depth === 1) return '13px';
            if (d.depth === 2) return '11px';
            return '10px';
        })
        .style('opacity', 0)
        .style('display', d => d.depth > 2 ? 'none' : 'block');

    // Cascade label fade in
    nodeEnter.select('text')
        .transition()
        .delay(d => cascadeDelay(d) + 400)
        .duration(500)
        .style('opacity', d => d.depth <= 1 ? 1 : 0.7);

    // Node group fade in (cascade)
    nodeEnter.transition()
        .delay(d => cascadeDelay(d))
        .duration(400)
        .attr('opacity', 1);

    // --- Hover: show deep labels ---
    nodeEnter.on('mouseover', function (event, d) {
        d3.select(this).select('text')
            .style('display', 'block')
            .transition().duration(200)
            .style('opacity', 1);

        // Highlight connected links
        linkMerge.attr('stroke-opacity', l => {
            return (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.08;
        }).attr('stroke', l => {
            return (l.source.id === d.id || l.target.id === d.id)
                ? 'rgba(180,140,255,0.85)' : 'rgba(120,80,220,0.1)';
        });

        // Info panel
        if (d.data.description) {
            const panel = document.getElementById('info-panel');
            document.getElementById('panel-title').innerText = d.data.name;
            document.getElementById('panel-content').innerHTML = `
                <p>${d.data.description}</p>
                ${d.data.link ? `<a href="${d.data.link}" target="_blank" style="color: rgba(255,255,255,0.6); text-decoration: underline;">Visit →</a>` : ''}
            `;
            panel.style.display = 'block';
            panel.style.opacity = '1';
        }
    });

    nodeEnter.on('mouseout', function (event, d) {
        if (d.depth > 2) {
            d3.select(this).select('text')
                .transition().duration(300)
                .style('opacity', 0)
                .on('end', function () { d3.select(this).style('display', 'none'); });
        }

        // Reset link highlights
        linkMerge.attr('stroke-opacity', 1).attr('stroke', 'rgba(140,100,255,0.25)');
    });

    // --- Click: navigate or toggle ---
    nodeEnter.on('click', (event, d) => {
        event.stopPropagation();

        // If this node has a navigation target, go there
        if (d.data.navigateTo) {
            window.location.href = d.data.navigateTo;
            return;
        }

        // Otherwise toggle expand/collapse
        if (d.children || d._children) {
            if (d.children) {
                d._children = d.children;
                d.children = null;
            } else {
                d.children = d._children;
                d._children = null;
            }
            render();
            simulation.alpha(0.4).restart();
        }
    });

    const nodeMerge = nodeEnter.merge(node);

    // ===== Simulation Tick =====
    simulation.nodes(allNodes).on('tick', () => {
        linkMerge
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        nodeMerge
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    simulation.force('link').links(allLinks);
    simulation.alpha(1).restart();
}

// ===== Drag handlers =====
function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// ===== Handle resize =====
window.addEventListener('resize', () => {
    width = container.clientWidth;
    height = container.clientHeight;
    svg.attr('width', width).attr('height', height);
    simulation.force('center', d3.forceCenter(width / 2, height / 2));
    simulation.alpha(0.3).restart();
});

// ===== Initial Render + Loader dismiss =====
// Pre-warm the simulation silently (no tick callbacks yet) to pre-compute positions
simulation.nodes(rootNode.descendants());
simulation.force('link').links(rootNode.links());
// Run ~30 ticks silently so nodes start in reasonable positions
for (let i = 0; i < 30; i++) simulation.tick();

// Now render with pre-computed positions, then kick off live simulation
render();
simulation.restart();

// Dismiss loader
setTimeout(() => {
    const loader = document.getElementById('loader');
    if (loader) {
        loader.classList.add('fade-out');
        setTimeout(() => loader.remove(), 800);
    }
}, 400); // Faster dismiss — graph is already rendered


