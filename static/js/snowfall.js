// ===== Unified Ambient Canvas (Snowfall + Particles — single RAF loop) =====
// On index.html (which has particle-canvas from script.js), this does nothing.
// On all sub-pages, this replaces the old separate snowfall + particle loops.
(function () {
    // Don't double-up on index.html
    if (document.getElementById('particle-canvas')) return;

    const canvas = document.createElement('canvas');
    canvas.id = 'snowfall-canvas';
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;pointer-events:none;';
    document.body.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    let W, H;

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    // Snow uses the text colour (white on dark, ink on light); the slow dots use the primary colour
    let snowColor, dotColor;
    function readColors() {
        const s = getComputedStyle(document.documentElement);
        snowColor = s.getPropertyValue('--text').trim();
        dotColor = s.getPropertyValue('--primary').trim();
    }
    readColors();
    document.addEventListener('themechange', readColors);

    // Combined 40 particles (was 55 snow + 50 bg = 105 total)
    const COUNT = 40;
    const flakes = [];
    for (let i = 0; i < COUNT; i++) {
        const isSnow = i < 20;
        flakes.push({
            x: Math.random() * (W || window.innerWidth),
            y: Math.random() * (H || window.innerHeight),
            r: isSnow ? (Math.random() * 1.8 + 0.4) : (Math.random() * 0.9 + 0.3),
            speed: isSnow ? (Math.random() * 0.5 + 0.15) : 0,
            vx: isSnow ? (Math.random() - 0.5) * 0.25 : (Math.random() - 0.5) * 0.2,
            vy: isSnow ? 0 : (Math.random() - 0.5) * 0.2,
            alpha: isSnow ? (Math.random() * 0.3 + 0.07) : (Math.random() * 0.1 + 0.02),
            wobble: Math.random() * Math.PI * 2,
            wobbleSpeed: Math.random() * 0.018 + 0.004,
            isSnow
        });
    }

    function draw() {
        ctx.clearRect(0, 0, W, H);
        for (const f of flakes) {
            if (f.isSnow) {
                f.y += f.speed;
                f.wobble += f.wobbleSpeed;
                f.x += f.vx + Math.sin(f.wobble) * 0.25;
                if (f.y > H + 5) { f.y = -5; f.x = Math.random() * W; }
                if (f.x < -5) f.x = W + 5;
                if (f.x > W + 5) f.x = -5;
                ctx.fillStyle = snowColor;
            } else {
                f.x += f.vx; f.y += f.vy;
                if (f.x < 0) f.x = W; if (f.x > W) f.x = 0;
                if (f.y < 0) f.y = H; if (f.y > H) f.y = 0;
                ctx.fillStyle = dotColor;
            }
            ctx.globalAlpha = f.alpha;
            ctx.beginPath();
            ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
            ctx.fill();
        }
        requestAnimationFrame(draw);
    }

    // Small delay so page paint isn't blocked on load
    setTimeout(draw, 150);
})();
