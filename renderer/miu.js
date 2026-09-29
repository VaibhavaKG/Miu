// miu.js — Pixel cat that follows the cursor, with speech bubble for Pomodoro timer.

(function miu() {
  const CAT_NAME = "Miu";

  const catEl = document.getElementById("miu-cat");
  const bubbleEl = document.getElementById("miu-bubble");
  const bubbleText = document.getElementById("miu-bubble-text");

  let catPosX = 100;
  let catPosY = 100;
  let mousePosX = 0;
  let mousePosY = 0;

  let frameCount = 0;
  let idleTime = 0;
  let idleAnimation = null;
  let idleAnimationFrame = 0;

  let catIsVisible = false;
  let timerRunning = false;
  let bubbleTimeout = null;

  const catSpeed = 10;

  // Sprite offsets (32×32 grid positions in the sprite sheet)
  const spriteSets = {
    idle: [[-3, -3]],
    alert: [[-7, -3]],
    scratchSelf: [
      [-5, 0],
      [-6, 0],
      [-7, 0],
    ],
    scratchWallN: [
      [0, 0],
      [0, -1],
    ],
    scratchWallS: [
      [-7, -1],
      [-6, -2],
    ],
    scratchWallE: [
      [-2, -2],
      [-2, -3],
    ],
    scratchWallW: [
      [-4, 0],
      [-4, -1],
    ],
    tired: [[-3, -2]],
    sleeping: [
      [-2, 0],
      [-2, -1],
    ],
    N: [
      [-1, -2],
      [-1, -3],
    ],
    NE: [
      [0, -2],
      [0, -3],
    ],
    E: [
      [-3, 0],
      [-3, -1],
    ],
    SE: [
      [-5, -1],
      [-5, -2],
    ],
    S: [
      [-6, -3],
      [-7, -2],
    ],
    SW: [
      [-5, -3],
      [-6, -1],
    ],
    W: [
      [-4, -2],
      [-4, -3],
    ],
    NW: [
      [-1, 0],
      [-1, -1],
    ],
  };

  // --- Sprite helpers ---
  function setSprite(name, frame) {
    const sprite = spriteSets[name][frame % spriteSets[name].length];
    catEl.style.backgroundPosition = `${sprite[0] * 32}px ${sprite[1] * 32}px`;
  }

  function resetIdleAnimation() {
    idleAnimation = null;
    idleAnimationFrame = 0;
  }

  // --- Idle behaviour ---
  function idle() {
    idleTime += 1;

    if (
      idleTime > 10 &&
      Math.floor(Math.random() * 200) === 0 &&
      idleAnimation == null
    ) {
      let available = ["sleeping", "scratchSelf"];
      if (catPosX < 32) available.push("scratchWallW");
      if (catPosY < 32) available.push("scratchWallN");
      if (catPosX > window.innerWidth - 32) available.push("scratchWallE");
      if (catPosY > window.innerHeight - 32) available.push("scratchWallS");
      idleAnimation = available[Math.floor(Math.random() * available.length)];
    }

    switch (idleAnimation) {
      case "sleeping":
        if (idleAnimationFrame < 8) {
          setSprite("tired", 0);
          break;
        }
        setSprite("sleeping", Math.floor(idleAnimationFrame / 4));
        if (idleAnimationFrame > 192) resetIdleAnimation();
        break;
      case "scratchWallN":
      case "scratchWallS":
      case "scratchWallE":
      case "scratchWallW":
      case "scratchSelf":
        setSprite(idleAnimation, idleAnimationFrame);
        if (idleAnimationFrame > 9) resetIdleAnimation();
        break;
      default:
        setSprite("idle", 0);
        return;
    }
    idleAnimationFrame += 1;
  }

  // --- Main frame logic ---
  function frame() {
    frameCount += 1;
    const diffX = catPosX - mousePosX;
    const diffY = catPosY - mousePosY;
    const distance = Math.sqrt(diffX ** 2 + diffY ** 2);

    if (distance < catSpeed || distance < 48) {
      idle();
      return;
    }

    idleAnimation = null;
    idleAnimationFrame = 0;

    if (idleTime > 1) {
      setSprite("alert", 0);
      idleTime = Math.min(idleTime, 7);
      idleTime -= 1;
      return;
    }

    let direction = "";
    direction += diffY / distance > 0.5 ? "N" : "";
    direction += diffY / distance < -0.5 ? "S" : "";
    direction += diffX / distance > 0.5 ? "W" : "";
    direction += diffX / distance < -0.5 ? "E" : "";
    setSprite(direction, frameCount);

    catPosX -= (diffX / distance) * catSpeed;
    catPosY -= (diffY / distance) * catSpeed;

    catPosX = Math.min(Math.max(16, catPosX), window.innerWidth - 16);
    catPosY = Math.min(Math.max(16, catPosY), window.innerHeight - 16);

    catEl.style.left = `${catPosX - 16}px`;
    catEl.style.top = `${catPosY - 16}px`;
  }

  // --- Bubble positioning ---
  function updateBubblePosition() {
    if (bubbleEl.style.display === "none") return;
    // Position bubble above the cat, centered
    const bw = bubbleEl.offsetWidth || 50;
    const bx = catPosX - 16 + 16 - bw / 2; // center over cat
    const by = catPosY - 16 - 28;           // above cat
    bubbleEl.style.left = `${Math.max(0, bx)}px`;
    bubbleEl.style.top = `${Math.max(0, by)}px`;
  }

  function showBubble(text, durationMs) {
    bubbleText.textContent = text;
    bubbleEl.classList.remove("fading");
    bubbleEl.style.display = "block";
    updateBubblePosition();

    if (bubbleTimeout) clearTimeout(bubbleTimeout);
    if (durationMs && durationMs > 0) {
      bubbleTimeout = setTimeout(() => {
        bubbleEl.classList.add("fading");
        setTimeout(() => {
          bubbleEl.style.display = "none";
          bubbleEl.classList.remove("fading");
        }, 500);
      }, durationMs);
    }
  }

  function hideBubble() {
    if (bubbleTimeout) clearTimeout(bubbleTimeout);
    bubbleEl.style.display = "none";
    bubbleEl.classList.remove("fading");
  }

  function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  // --- Animation loop ---
  let lastFrameTimestamp = null;

  function onAnimationFrame(timestamp) {
    if (!lastFrameTimestamp) lastFrameTimestamp = timestamp;
    if (timestamp - lastFrameTimestamp > 100) {
      lastFrameTimestamp = timestamp;
      if (catIsVisible) {
        frame();
        updateBubblePosition();
      }
    }
    window.requestAnimationFrame(onAnimationFrame);
  }

  // Start the animation loop immediately (but cat is hidden)
  window.requestAnimationFrame(onAnimationFrame);

  // --- Timer-end animation ---
  function playTimerEndAnimation() {
    // Quick alert → scratchSelf sequence
    let animFrame = 0;
    const endAnim = setInterval(() => {
      if (animFrame < 3) {
        setSprite("alert", 0);
      } else if (animFrame < 12) {
        setSprite("scratchSelf", animFrame - 3);
      } else {
        clearInterval(endAnim);
        setSprite("idle", 0);
      }
      animFrame++;
    }, 150);
  }

  // --- IPC event handlers ---
  const api = window.miuAPI;

  // Cursor updates from main process
  api.onCursorMove((x, y) => {
    mousePosX = x;
    mousePosY = y;
  });

  // Show cat
  api.onShow(() => {
    catIsVisible = true;
    catEl.style.display = "block";
    setSprite("alert", 0);
    idleTime = 0;
  });

  // Hide cat
  api.onHide(() => {
    catIsVisible = false;
    catEl.style.display = "none";
    if (!timerRunning) hideBubble();
  });

  // Greeting
  api.onGreeting(() => {
    showBubble("mew!", 2000);
  });

  // Timer start
  api.onTimerStart((type, secs) => {
    timerRunning = true;
    showBubble(formatTime(secs));
  });

  // Timer tick
  api.onTimerTick((secs) => {
    if (timerRunning && catIsVisible) {
      showBubble(formatTime(secs));
    }
  });

  // Timer end
  api.onTimerEnd((type) => {
    timerRunning = false;
    showBubble("Time's up! 🐾", 8000);
    playTimerEndAnimation();
  });

  // Timer stop
  api.onTimerStop(() => {
    timerRunning = false;
    hideBubble();
  });

  // Temporary bubble (e.g. --status)
  api.onBubble((text, duration) => {
    showBubble(text, duration);
  });
})();
