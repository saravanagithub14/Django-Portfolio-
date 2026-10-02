// ===== Background Particle Effect (2D Overlay) =====
(function initParticles() {
    try {
        const canvas = document.getElementById('particle-canvas');
        const host = document.getElementById('graph-container');
        if (!canvas || (host && host.dataset.mode === 'background')) return;
        const ctx = canvas.getContext('2d');
        let W, H;

        function resize() {
            W = canvas.width = window.innerWidth;
            H = canvas.height = window.innerHeight;
        }
        resize();
        window.addEventListener('resize', resize);

        const particles = [];
        const COUNT = 35;

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
            const color = getComputedStyle(document.documentElement).getPropertyValue('--text').trim();
            for (const p of particles) {
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < 0) p.x = W;
                if (p.x > W) p.x = 0;
                if (p.y < 0) p.y = H;
                if (p.y > H) p.y = 0;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.globalAlpha = p.alpha;
                ctx.fillStyle = color;
                ctx.fill();
            }
            requestAnimationFrame(draw);
        }
        setTimeout(draw, 500);
    } catch (e) { console.error("Particles init error:", e); }
})();

// ===== 3D Graph Implementation =====
console.log("Initializing 3D Graph...");

try {
    if (typeof resumeData === 'undefined') {
        throw new Error("resumeData is not defined. Check if data.js is loaded correctly.");
    }

    // 1. Transform hierarchical resumeData into nodes/links
    const nodes = [];
    const links = [];

    function flattenData(node, parent = null, depth = 0) {
        const id = node.id || node.name || `node_${nodes.length}`;

        // Detect if this node corresponds to the current page
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const targetPage = node.navigateTo || '';
        const isCurrentPage = (typeof activePage !== 'undefined' && activePage === id) ||
            (targetPage && targetPage.includes(currentPage));

        const depthColors = [
            '#EEF2F6', // Root
            '#B5E655', // Level 1 (lime)
            '#86AD3E', // Level 2
            '#56702A'  // Level 3
        ];

        // The current page uses the accent colour so it stands out from the lime tree
        const color = isCurrentPage ? '#7DD3FC' : depthColors[Math.min(depth, depthColors.length - 1)];

        const newNode = {
            id,
            name: node.name,
            description: node.description,
            // End nodes have no page of their own: open the nearest ancestor's page instead
            // (e.g. a project opens Projects). The current-page highlight above uses only the node's own link.
            navigateTo: node.navigateTo || (parent && parent.depth > 0 ? parent.navigateTo : undefined),
            link: node.link,
            depth: depth,
            color: color,
            isCurrentPage: isCurrentPage,
            parent: parent,
            val: isCurrentPage ? 35 : (depth === 0 ? 20 : depth === 1 ? 12 : depth === 2 ? 6 : 4),
            // Initialize all nodes near center for branching effect
            x: depth === 0 ? 0 : (Math.random() - 0.5) * 20,
            y: depth === 0 ? 0 : (Math.random() - 0.5) * 20,
            z: depth === 0 ? 0 : (Math.random() - 0.5) * 20
        };

        // Always keep central node at EXACT center
        if (depth === 0) {
            newNode.fx = 0;
            newNode.fy = 0;
            newNode.fz = 0;
        }

        nodes.push(newNode);
        if (parent) {
            links.push({ source: parent.id, target: id });
        }
        if (node.children) {
            node.children.forEach(child => flattenData(child, newNode, depth + 1));
        }
    }

    flattenData(resumeData);



    // 1.5 Generate background "ghost" clusters for Multiverse effect
    const ghostClusters = 8;
    for (let c = 0; c < ghostClusters; c++) {
        const clusterId = `ghost_${c}`;
        const clusterColor = `rgba(181, 230, 85, ${0.04 + Math.random() * 0.08})`;
        const center = {
            id: `${clusterId}_root`,
            name: '',
            val: 3,
            isGhost: true,
            color: clusterColor,
            // Place them far in the periphery
            fx: (Math.random() - 0.5) * 3000,
            fy: (Math.random() - 0.5) * 3000,
            fz: (Math.random() - 0.5) * 3000
        };
        nodes.push(center);

        for (let s = 0; s < 6; s++) {
            const satId = `${clusterId}_sat_${s}`;
            nodes.push({
                id: satId,
                name: '',
                val: 1.5,
                isGhost: true,
                color: clusterColor
            });
            links.push({
                source: center.id,
                target: satId,
                isGhost: true
            });
        }
    }

    console.log(`Flattened data: ${nodes.length} nodes (including ghosts), ${links.length} links`);

    const gData = { nodes, links };

    // The graph stays dark in both themes; --graph-bg only shifts its shade
    function graphBg() {
        return getComputedStyle(document.documentElement).getPropertyValue('--graph-bg').trim() || '#0A0C0F';
    }

    function initGraph() {
        console.log("Initializing 3D Graph sub-view...");
        const container = document.getElementById('graph-container');
        if (!container) {
            console.warn("graph-container not found on this page.");
            return;
        }
        // "background": a fixed, slowly orbiting, non-interactive backdrop behind the page
        // (components/graph_background.html). setExplore(true) makes it interactive.
        const isBackground = container.dataset.mode === 'background';
        const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
        let exploring = !isBackground;
        const labelSprites = [];
        const glowSprites = [];
        // Additive glows show up as white halos on a light page, so the light backdrop drops them
        const isLightPage = () => {
            const theme = document.documentElement.dataset.theme;
            return theme ? theme === 'light' : matchMedia('(prefers-color-scheme: light)').matches;
        };
        const updateGlows = () => {
            const show = exploring || !isLightPage();
            glowSprites.forEach(s => { s.visible = show; });
        };
        const TRANSPARENT = 'rgba(0,0,0,0)';

        const Graph = ForceGraph3D()(container)
            .graphData(gData)
            .backgroundColor(isBackground ? TRANSPARENT : graphBg())
            .showNavInfo(false)
            .nodeColor(node => node.color)
            .nodeLabel(node => `
            <div style="background: rgba(17, 20, 24, 0.92); padding: 8px 12px; border-radius: 6px; border: 1px solid #2B323B; backdrop-filter: blur(8px); pointer-events: none; color: #EEF2F6; font-family: 'Inter', sans-serif;">
                <div style="font-weight: 700; font-size: 14px; margin-bottom: 2px;">${node.name}</div>
                ${node.description ? `<div style="color: #95A0AC; font-size: 11px; max-width: 250px; line-height: 1.4;">${node.description}</div>` : ''}
                ${node.navigateTo && !node.isCurrentPage ? `<div style="color: #B5E655; font-size: 10px; margin-top: 4px; letter-spacing: 0.5px;">Click to open ↗</div>` : ''}
            </div>
        `)
            .nodeRelSize(4)
            .nodeVal(node => node.val)
            .nodeOpacity(0.9)
            .linkWidth(l => l.isGhost ? 0.3 : 1.2)
            .linkColor(l => l.isGhost ? 'rgba(181, 230, 85, 0.06)' : 'rgba(181, 230, 85, 0.35)')
            .linkDirectionalParticles(l => (l.isGhost || !exploring) ? 0 : 3)
            .linkDirectionalParticleSpeed(0.007)
            .linkDirectionalParticleWidth(1.5)
            .onNodeHover(node => {
                if (node && node.isGhost) return; // Ignore ghost nodes for interaction
                container.style.cursor = node ? 'pointer' : 'grab';



                // Highlight links on hover
                Graph.linkWidth(l => {
                    if (l.isGhost) return 0.3;
                    return (node && (l.source.id === node.id || l.target.id === node.id)) ? 2.5 : 1.2;
                });
                Graph.linkColor(l => {
                    if (l.isGhost) return 'rgba(181, 230, 85, 0.06)';
                    return (node && (l.source.id === node.id || l.target.id === node.id)) ? 'rgba(238, 242, 246, 0.85)' : 'rgba(181, 230, 85, 0.35)';
                });


            })
            .onNodeClick(node => {
                if (node && node.isGhost) return; // Ignore ghosts
                const distance = 120;
                const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
                Graph.cameraPosition(
                    { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                    node,
                    1500
                );

                if (node.navigateTo) {
                    // Links like "projects.html" are relative to the site root; resolving them against the
                    // current URL would turn /graph/ + projects.html into /graph/projects.html (a 404).
                    const target = node.navigateTo.startsWith('#')
                        ? node.navigateTo
                        : new URL(node.navigateTo, window.location.origin + '/').href;
                    setTimeout(() => {
                        const loader = document.getElementById('loader');
                        if (loader) {
                            loader.style.display = 'flex';
                            loader.classList.remove('fade-out');
                        }
                        window.location.href = target;
                    }, 800);
                }
            });

        document.addEventListener('themechange', () => {
            if (exploring) Graph.backgroundColor(graphBg());
            updateGlows();
        });

        // 3. Custom Rendering (Safe access to THREE)
        const THREE = window.THREE;
        if (THREE) {
            console.log("Three.js detected, applying custom materials & labels...");

            const scene = Graph.scene();
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
            scene.add(ambientLight);

            const spotLight = new THREE.PointLight(0xffffff, 1.8);
            spotLight.position.set(100, 100, 100);
            scene.add(spotLight);

            Graph.nodeThreeObject(node => {
                const group = new THREE.Group();
                const opacity = node.isGhost ? 0.2 : 0.85;

                // Sphere (Glass Orb)
                // 16 segments looks the same at this size; 64 made ~100 nodes cost ~800k triangles per frame
                const sphereGeom = new THREE.SphereGeometry(node.val * 0.8, 16, 16);
                const sphereMat = new THREE.MeshStandardMaterial({
                    color: node.color,
                    transparent: true,
                    opacity: opacity,
                    metalness: 0.3,
                    roughness: 0.05,
                    emissive: node.color,
                    emissiveIntensity: node.isCurrentPage ? 2.5 : (node.isGhost ? 0.2 : 0.5)
                });
                const sphere = new THREE.Mesh(sphereGeom, sphereMat);
                group.add(sphere);

                // Glow sprite
                if (!node.isGhost) {
                    const glowCanvas = document.createElement('canvas');
                    glowCanvas.width = 64;
                    glowCanvas.height = 64;
                    const glowCtx = glowCanvas.getContext('2d');
                    const gradient = glowCtx.createRadialGradient(32, 32, 0, 32, 32, 32);
                    gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
                    gradient.addColorStop(0.3, 'rgba(255, 255, 255, 0.4)');
                    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
                    glowCtx.fillStyle = gradient;
                    glowCtx.fillRect(0, 0, 64, 64);

                    const glowTexture = new THREE.CanvasTexture(glowCanvas);
                    const spriteMaterial = new THREE.SpriteMaterial({
                        map: glowTexture,
                        color: node.color,
                        transparent: true,
                        opacity: 0.7,
                        blending: THREE.AdditiveBlending
                    });
                    const sprite = new THREE.Sprite(spriteMaterial);
                    sprite.scale.set(node.val * 3.5, node.val * 3.5, 1.0);
                    glowSprites.push(sprite);
                    sprite.visible = exploring || !isLightPage();
                    group.add(sprite);

                    // Persistent Text Labels for important nodes (Depth 0, 1, or Current Page)
                    if (!node.isGhost && (node.depth <= 1 || node.isCurrentPage)) {
                        const labelCanvas = document.createElement('canvas');
                        const labelCtx = labelCanvas.getContext('2d');
                        const fontSize = node.depth === 0 ? 48 : (node.isCurrentPage ? 42 : 36);
                        labelCtx.font = `Bold ${fontSize}px 'Inter', sans-serif`;

                        const labelText = node.isCurrentPage ? `${node.name} (You are here)` : node.name;
                        const textWidth = labelCtx.measureText(labelText).width;

                        labelCanvas.width = textWidth + 40;
                        labelCanvas.height = fontSize + 40;

                        labelCtx.font = `Bold ${fontSize}px 'Inter', sans-serif`;
                        labelCtx.fillStyle = node.isCurrentPage ? '#7DD3FC' : '#EEF2F6';
                        labelCtx.shadowColor = node.isCurrentPage ? 'rgba(125, 211, 252, 0.7)' : 'rgba(0,0,0,0.8)';
                        labelCtx.shadowBlur = 12;
                        labelCtx.fillText(labelText, 20, fontSize + 20);

                        const labelTexture = new THREE.CanvasTexture(labelCanvas);
                        const labelMaterial = new THREE.SpriteMaterial({
                            map: labelTexture,
                            transparent: true,
                            opacity: 0.95
                        });
                        const labelSprite = new THREE.Sprite(labelMaterial);

                        const labelScale = (node.depth === 0 ? 15 : (node.isCurrentPage ? 20 : 10)) * (labelCanvas.width / labelCanvas.height);
                        labelSprite.scale.set(labelScale, node.depth === 0 ? 15 : (node.isCurrentPage ? 20 : 10), 1);
                        labelSprite.position.set(0, node.val + (node.isCurrentPage ? 14 : 8), 0);
                        // White labels would vanish on a light page, so the backdrop hides them
                        labelSprite.visible = exploring;
                        labelSprites.push(labelSprite);
                        group.add(labelSprite);
                    }
                }

                return group;
            });
        } else {
            console.warn("THREE not found on window. Falling back to default node rendering.");
        }

        // 4. Final adjustments
        Graph.d3Force('charge').strength(-250);
        Graph.d3Force('link').distance(node => node.source.depth === 0 ? 150 : 70);

        // Initial Camera: Start very close for dramatic "branching out" effect
        Graph.cameraPosition({ x: 0, y: 0, z: 80 });

        setTimeout(() => {
            // Pull back camera as nodes branch out
            Graph.cameraPosition({ z: 450 }, { x: 0, y: 0, z: 0 }, 3500);
        }, 1200);

        if (isBackground) {
            Graph.enableNavigationControls(false).enablePointerInteraction(false);
            const fit = () => Graph.width(container.clientWidth).height(container.clientHeight);
            fit();
            window.addEventListener('resize', fit);

            // Slow orbit around the centre; paused while exploring and for reduced motion
            let angle = 0, distance = 450, orbiting = false;
            setTimeout(() => { orbiting = true; }, 4800);  // after the opening zoom-out
            (function orbit() {
                if (orbiting && !exploring && !reduceMotion && !document.hidden) {
                    angle += 0.0009;
                    Graph.cameraPosition(
                        { x: distance * Math.sin(angle), y: Graph.camera().position.y, z: distance * Math.cos(angle) },
                        { x: 0, y: 0, z: 0 }
                    );
                }
                requestAnimationFrame(orbit);
            })();

            window.portfolioGraph = {
                setExplore(on) {
                    exploring = on;
                    Graph.enableNavigationControls(on)
                        .enablePointerInteraction(on)
                        .backgroundColor(on ? graphBg() : TRANSPARENT)
                        .linkDirectionalParticles(l => (l.isGhost || !on) ? 0 : 3);
                    labelSprites.forEach(s => { s.visible = on; });
                    updateGlows();
                    if (!on) {
                        // Resume the orbit from wherever the visitor left the camera
                        const c = Graph.camera().position;
                        angle = Math.atan2(c.x, c.z);
                        distance = Math.max(250, Math.min(700, Math.hypot(c.x, c.z)));
                    }
                }
            };
        }

        // Stop rendering while the graph is scrolled out of view (it keeps animating otherwise)
        if ('IntersectionObserver' in window) {
            new IntersectionObserver(entries => {
                for (const entry of entries) {
                    entry.isIntersecting ? Graph.resumeAnimation() : Graph.pauseAnimation();
                }
            }).observe(container);
        }

        // 5. Dismiss Loader
        console.log("Graph setup complete. Removing loader...");
        setTimeout(() => {
            const loader = document.getElementById('loader');
            if (loader) {
                loader.classList.add('fade-out');
                setTimeout(() => loader.remove(), 800);
            }
        }, 300);

    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGraph);
    } else {
        initGraph();
    }

} catch (err) {
    console.error("3D Graph Error:", err);
    // If it fails, at least dismiss the loader so user can see the content
    setTimeout(() => {
        const loader = document.getElementById('loader');
        if (loader) loader.remove();
    }, 2000);
}
