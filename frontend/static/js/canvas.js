// ================================================================
// canvas.js — DualStack Radar
// Animação de raios de luz no fundo + efeito parallax do mouse
// ================================================================

const canvas = document.getElementById('bg-canvas');
const ctx    = canvas.getContext('2d');
let W, H, rays = [];

/** Redimensiona o canvas ao tamanho da janela. */
function resize() {
  W = canvas.width  = window.innerWidth;
  H = canvas.height = window.innerHeight;
}
resize();
window.addEventListener('resize', resize);

/**
 * Cria um objeto "raio de luz" com atributos aleatórios.
 * @returns {{ x, y, angle, len, speed, width, alpha, color, life }}
 */
function mkRay() {
  return {
    x:     Math.random() * W * 1.5 - W * 0.25,
    y:     H + 50,
    angle: -Math.PI / 2 + (Math.random() - .5) * .8,
    len:   300 + Math.random() * 400,
    speed: .3  + Math.random() * .4,
    width: .5  + Math.random() * 2,
    alpha: .03 + Math.random() * .08,
    color: Math.random() > .5
             ? 'rgba(124,58,237,'
             : Math.random() > .5 ? 'rgba(168,85,247,' : 'rgba(59,130,246,',
    life: Math.random(),
  };
}

/* Inicializa 35 raios */
for (let i = 0; i < 35; i++) rays.push(mkRay());

/**
 * Loop de animação: desenha todos os raios com fade in/out
 * usando requestAnimationFrame.
 */
function drawRays() {
  ctx.clearRect(0, 0, W, H);

  rays.forEach(r => {
    r.life += r.speed * .003;
    /* Recria o raio ao fim do ciclo de vida */
    if (r.life > 1) { Object.assign(r, mkRay()); r.life = 0; }

    /* Opacidade em sino: max no meio da vida */
    const fade = Math.sin(r.life * Math.PI);
    const x2 = r.x + Math.cos(r.angle) * r.len;
    const y2 = r.y + Math.sin(r.angle) * r.len;

    /* Gradiente linear ao longo do raio */
    const g = ctx.createLinearGradient(r.x, r.y, x2, y2);
    g.addColorStop(0,   r.color + '0)');
    g.addColorStop(.3,  r.color + (r.alpha * fade) + ')');
    g.addColorStop(.7,  r.color + (r.alpha * fade * .5) + ')');
    g.addColorStop(1,   r.color + '0)');

    ctx.beginPath();
    ctx.moveTo(r.x, r.y);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = g;
    ctx.lineWidth   = r.width;
    ctx.stroke();
  });

  requestAnimationFrame(drawRays);
}
drawRays();

/* Efeito parallax suave do canvas em resposta ao mouse */
document.addEventListener('mousemove', e => {
  const mx = (e.clientX / window.innerWidth  - .5) * 20;
  const my = (e.clientY / window.innerHeight - .5) * 20;
  canvas.style.transform = `translate(${mx * .3}px, ${my * .3}px)`;
});
