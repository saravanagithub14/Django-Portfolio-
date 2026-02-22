// ===== Snowfall Effect =====
// Drop this script into any page for a subtle snowfall layer.
(function () {
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

    const flakes = [];
    const COUNT = 55;

    for (let i = 0; i < COUNT; i++) {
        flakes.push({
            x: Math.random() * W,
            y: Math.random() * H,
            r: Math.random() * 2 + 0.5,
            speed: Math.random() * 0.6 + 0.2,
            drift: (Math.random() - 0.5) * 0.4,
            alpha: Math.random() * 0.4 + 0.1,
            wobble: Math.random() * Math.PI * 2,
            wobbleSpeed: Math.random() * 0.02 + 0.005
        });
    }

    function draw() {
        ctx.clearRect(0, 0, W, H);
        for (const f of flakes) {
            f.y += f.speed;
            f.wobble += f.wobbleSpeed;
            f.x += f.drift + Math.sin(f.wobble) * 0.3;

            if (f.y > H + 5) {
                f.y = -5;
                f.x = Math.random() * W;
            }
            if (f.x < -5) f.x = W + 5;
            if (f.x > W + 5) f.x = -5;

            ctx.beginPath();
            ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${f.alpha})`;
            ctx.fill();
        }
        requestAnimationFrame(draw);
    }
    draw();
})();
