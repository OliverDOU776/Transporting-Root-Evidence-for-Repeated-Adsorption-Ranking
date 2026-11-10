'use strict';

// No remote services or analytics are used. Media are served with the project page.
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copy);
    const status = document.getElementById('copy-status');
    try {
      await navigator.clipboard.writeText(target.textContent);
      button.textContent = 'Copied';
      status.textContent = 'Copied to clipboard.';
      setTimeout(() => { button.textContent = 'Copy'; }, 1800);
    } catch (_) {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(target);
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = 'Text selected. Use your browser copy command.';
    }
  });
}

// Start the explanatory animation only after checking the visitor's motion preference.
// There is intentionally no autoplay attribute in HTML, avoiding an early autoplay
// before this deferred script can honor prefers-reduced-motion.
const valueHero = document.getElementById('value-hero-video');
const valueHeroToggle = document.getElementById('value-hero-toggle');
if (valueHero && valueHeroToggle) {
  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let userPaused = false;
  valueHero.muted = true;
  valueHero.loop = true;
  valueHero.playsInline = true;
  valueHero.controls = false;
  valueHeroToggle.hidden = false;

  const updateHeroControl = () => {
    const playing = !valueHero.paused && !valueHero.ended;
    valueHeroToggle.textContent = playing ? 'Pause animation' : 'Play animation';
    valueHeroToggle.setAttribute('aria-pressed', String(playing));
  };
  const playHero = async () => {
    valueHero.preload = 'auto';
    try {
      await valueHero.play();
    } catch (_) {
      // Autoplay can be blocked by the browser. Leave an explicit play choice.
      updateHeroControl();
    }
  };
  valueHero.addEventListener('play', updateHeroControl);
  valueHero.addEventListener('pause', updateHeroControl);
  valueHero.addEventListener('ended', updateHeroControl);
  valueHeroToggle.addEventListener('click', () => {
    if (valueHero.paused || valueHero.ended) {
      userPaused = false;
      playHero();
    } else {
      userPaused = true;
      valueHero.pause();
    }
  });
  const applyMotionPreference = () => {
    valueHero.autoplay = !motionPreference.matches;
    if (motionPreference.matches) {
      valueHero.pause();
      updateHeroControl();
    } else if (!userPaused) {
      playHero();
    }
  };
  motionPreference.addEventListener('change', applyMotionPreference);
  applyMotionPreference();
}
