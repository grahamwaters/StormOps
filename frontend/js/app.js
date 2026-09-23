(() => {
  "use strict";
  const MAX_FILE_BYTES = 12 * 1024 * 1024;
  const MAX_SIDE = 900;
  const canvas = document.querySelector("#cloud-canvas");
  const context = canvas.getContext("2d");
  const fileInput = document.querySelector("#image-file");
  const dropzone = document.querySelector("#dropzone");
  const simulateButton = document.querySelector("#simulate-button");
  const saveButton = document.querySelector("#save-button");
  const pauseButton = document.querySelector("#pause-button");
  const status = document.querySelector("#status");
  const fileName = document.querySelector("#file-name");
  const previewTitle = document.querySelector("#preview-title");
  const canvasState = document.querySelector("#canvas-state");
  const particleCount = document.querySelector("#particle-count");
  const emptyState = document.querySelector("#empty-state");
  const expandButton = document.querySelector("#expand-button");
  const particles = [];
  let selectedFile = null;
  let animationId = null;
  let paused = false;
  let points = [];
  let sourceObjectUrl = null;

  function setStatus(message) { status.textContent = message; }

  function resizeCanvas() {
    if (animationId !== null) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
    const box = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.floor(box.width * ratio));
    canvas.height = Math.max(1, Math.floor(box.height * ratio));
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw();
  }

  function draw() {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    context.clearRect(0, 0, width, height);
    for (const particle of particles) {
      particle.x += particle.vx;
      particle.y += particle.vy;
      if (particle.x < -particle.size) particle.x = width + particle.size;
      if (particle.x > width + particle.size) particle.x = -particle.size;
      if (particle.y < -particle.size) particle.y = height + particle.size;
      if (particle.y > height + particle.size) particle.y = -particle.size;
      const gradient = context.createRadialGradient(particle.x, particle.y, 0, particle.x, particle.y, particle.size);
      gradient.addColorStop(0, `rgba(${particle.color},${particle.opacity})`);
      gradient.addColorStop(1, `rgba(${particle.color},0)`);
      context.fillStyle = gradient;
      context.beginPath();
      context.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
      context.fill();
    }
    if (particles.length && !paused && !document.hidden && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      animationId = requestAnimationFrame(draw);
    } else animationId = null;
  }

  function clearSimulation() {
    if (animationId !== null) cancelAnimationFrame(animationId);
    animationId = null;
    particles.length = 0;
    points = [];
    expandButton.disabled = true;
    document.body.classList.remove("is-fullscreen");
    expandButton.textContent = "Expand canvas";
    saveButton.disabled = true;
    pauseButton.disabled = true;
    pauseButton.textContent = "Pause motion";
    paused = false;
    particleCount.textContent = "0 CLOUD PARTICLES";
    canvasState.textContent = "STANDBY";
    canvasState.classList.remove("ready");
    emptyState.hidden = false;
    draw();
  }

  function acceptFile(file) {
    if (!file) return;
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
      fileInput.value = "";
      selectedFile = null;
      simulateButton.disabled = true;
      clearSimulation();
      setStatus("Choose a PNG, JPEG, or WebP image.");
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      fileInput.value = "";
      selectedFile = null;
      simulateButton.disabled = true;
      clearSimulation();
      setStatus("That image is over 12 MB. Choose a smaller file.");
      return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    previewTitle.textContent = file.name;
    simulateButton.disabled = false;
    clearSimulation();
    setStatus("Image ready. Build a cloud field when you are set.");
  }

  function sampleImage(image) {
    const scale = Math.min(1, MAX_SIDE / image.width, MAX_SIDE / image.height);
    const width = Math.max(1, Math.round(image.width * scale));
    const height = Math.max(1, Math.round(image.height * scale));
    const buffer = document.createElement("canvas");
    buffer.width = width;
    buffer.height = height;
    const bufferContext = buffer.getContext("2d", { willReadFrequently: true });
    if (!bufferContext) throw new Error("Image processing is unavailable in this browser.");
    bufferContext.drawImage(image, 0, 0, width, height);
    const pixels = bufferContext.getImageData(0, 0, width, height).data;
    const found = [];
    const step = Math.max(2, Math.ceil(Math.sqrt((width * height) / 3000)));
    for (let y = 0; y < height; y += step) {
      for (let x = 0; x < width; x += step) {
        const offset = (y * width + x) * 4;
        const brightness = (pixels[offset] + pixels[offset + 1] + pixels[offset + 2]) / 3;
        if (pixels[offset + 3] < 24 || brightness < 174) continue;
        const overshoot = pixels[offset] > 246 && pixels[offset + 1] > 246 && pixels[offset + 2] > 246;
        const opacity = Math.min(0.72, Math.max(0.1, (brightness - 160) / 145));
        found.push({ x: x / width, y: y / height, color: overshoot ? "255,185,91" : "207,226,238", opacity });
      }
    }
    return { found, width, height };
  }

  function buildSimulation() {
    if (!selectedFile) return;
    simulateButton.disabled = true;
    saveButton.disabled = true;
    setStatus("Reading image locally…");
    const url = URL.createObjectURL(selectedFile);
    const image = new Image();
    image.onload = () => {
      try {
        const sampled = sampleImage(image);
        if (sourceObjectUrl) URL.revokeObjectURL(sourceObjectUrl);
        sourceObjectUrl = url;
        points = sampled.found;
        particles.length = 0;
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        const scale = Math.min(width / sampled.width, height / sampled.height);
        const drawWidth = sampled.width * scale;
        const drawHeight = sampled.height * scale;
        const offsetX = (width - drawWidth) / 2;
        const offsetY = (height - drawHeight) / 2;
        for (const point of sampled.found) {
          particles.push({
            x: offsetX + point.x * drawWidth,
            y: offsetY + point.y * drawHeight,
            size: 2 + Math.random() * 4.5,
            opacity: point.opacity,
            color: point.color,
            vx: (Math.random() - 0.5) * 0.2,
            vy: (Math.random() - 0.5) * 0.12,
          });
        }
        emptyState.hidden = true;
        particleCount.textContent = `${particles.length.toLocaleString()} CLOUD PARTICLES`;
        if (!particles.length) {
          canvasState.textContent = "NO CLOUDS";
          canvasState.classList.remove("ready");
          setStatus("No bright cloud regions were found. Try a visible satellite image or a brighter storm photo.");
        } else {
          canvasState.textContent = "SIMULATING";
          canvasState.classList.add("ready");
          saveButton.disabled = false;
          const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          setStatus(reducedMotion
            ? `${particles.length.toLocaleString()} bright image samples found. Motion is reduced by your system preference.`
            : `${particles.length.toLocaleString()} bright image samples are moving. You can export this simulation.`);
          pauseButton.disabled = reducedMotion;
          expandButton.disabled = false;
          draw();
        }
      } catch (error) {
        URL.revokeObjectURL(url);
        setStatus(error instanceof Error ? error.message : "Could not process this image.");
        clearSimulation();
      } finally {
        simulateButton.disabled = false;
      }
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      simulateButton.disabled = false;
      setStatus("The selected file could not be decoded as an image. Try another file.");
    };
    image.src = url;
  }

  function exportSimulation() {
    if (!points.length) return;
    const safeName = selectedFile.name.replace(/\.[^.]+$/, "").normalize("NFKD")
      .replace(/[^a-z0-9_-]+/gi, "_").slice(0, 60) || "stormops_cloud_field";
    const payload = JSON.stringify(points);
    const html = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>StormOps cloud field</title><style>*{box-sizing:border-box}body{margin:0;background:#08111c;color:#e9f2f8;font:14px system-ui;display:grid;place-items:center;min-height:100vh}.wrap{width:min(1000px,96vw)}h1{font-size:16px;font-weight:500}canvas{width:100%;height:min(70vh,600px);display:block;background:radial-gradient(ellipse,#102338,#08121d);border:1px solid #1d3142;border-radius:8px}</style><main class="wrap"><h1>StormOps · visual cloud field</h1><canvas id="field" aria-label="Animated cloud visualization"></canvas></main><script>const points=${payload};const c=document.querySelector('#field'),x=c.getContext('2d');let w,h,dpr;function size(){dpr=Math.min(devicePixelRatio||1,2);w=c.clientWidth;h=c.clientHeight;c.width=w*dpr;c.height=h*dpr;x.setTransform(dpr,0,0,dpr,0,0)}addEventListener('resize',size);size();function frame(){x.clearRect(0,0,w,h);for(const p of points){const px=p.x*w,py=p.y*h,g=x.createRadialGradient(px,py,0,px,py,4);g.addColorStop(0,'rgba('+p.color+','+p.opacity+')');g.addColorStop(1,'rgba('+p.color+',0)');x.fillStyle=g;x.fillRect(px-4,py-4,8,8)}requestAnimationFrame(frame)}frame()<\/script></html>`;
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${safeName}-stormops.html`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus("Standalone cloud visualization downloaded.");
  }

  fileInput.addEventListener("change", event => acceptFile(event.target.files[0]));
  simulateButton.addEventListener("click", buildSimulation);
  saveButton.addEventListener("click", exportSimulation);
  pauseButton.addEventListener("click", () => {
    paused = !paused;
    if (paused && animationId !== null) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
    pauseButton.textContent = paused ? "Resume motion" : "Pause motion";
    if (!paused && particles.length && animationId === null) animationId = requestAnimationFrame(draw);
  });
  dropzone.addEventListener("dragover", event => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", event => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
    acceptFile(event.dataTransfer.files[0]);
  });
  function toggleExpandedCanvas() {
    if (!points.length) return;
    document.body.classList.toggle("is-fullscreen");
    expandButton.textContent = document.body.classList.contains("is-fullscreen") ? "Exit expanded view" : "Expand canvas";
    resizeCanvas();
  }
  expandButton.addEventListener("click", toggleExpandedCanvas);
  document.querySelector("#canvas-wrap").addEventListener("dblclick", toggleExpandedCanvas);
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && document.body.classList.contains("is-fullscreen")) {
      document.body.classList.remove("is-fullscreen");
      expandButton.textContent = "Expand canvas";
      resizeCanvas();
    }
  });
  window.addEventListener("resize", resizeCanvas);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && animationId !== null) {
      cancelAnimationFrame(animationId);
      animationId = null;
    } else if (!document.hidden && !paused && particles.length && animationId === null) {
      animationId = requestAnimationFrame(draw);
    }
  });
  resizeCanvas();
})();
