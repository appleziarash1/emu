// Procedural audio. No external audio files are required; every sound is
// synthesised with WebAudio so the build stays self-contained.
//
// Mobile browsers require a user gesture before audio can start, so `unlock()`
// must be called from a real input handler.

export class Audio {
  constructor(options) {
    this.options = options || { music: true, sfx: true };
    this.ctx = null;
    this.master = null;
    this.musicGain = null;
    this.sfxGain = null;
    this.musicTimer = null;
    this.currentTrack = null;
    this.step = 0;
  }

  unlock() {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') this.ctx.resume();
      return;
    }
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    this.ctx = new Ctx();
    this.master = this.ctx.createGain();
    this.master.gain.value = 0.9;
    this.master.connect(this.ctx.destination);

    this.musicGain = this.ctx.createGain();
    this.musicGain.gain.value = this.options.music ? 0.28 : 0;
    this.musicGain.connect(this.master);

    this.sfxGain = this.ctx.createGain();
    this.sfxGain.gain.value = this.options.sfx ? 0.5 : 0;
    this.sfxGain.connect(this.master);
  }

  setOptions(opts) {
    this.options = opts;
    if (!this.ctx) return;
    this.musicGain.gain.value = opts.music ? 0.28 : 0;
    this.sfxGain.gain.value = opts.sfx ? 0.5 : 0;
    if (!opts.music) this.stopMusic();
    else if (this.currentTrack) this.playMusic(this.currentTrack);
  }

  tone({ freq = 440, dur = 0.12, type = 'sine', gain = 0.3, slide = 0, delay = 0, dest = null }) {
    if (!this.ctx || !this.options.sfx) return;
    const t0 = this.ctx.currentTime + delay;
    const osc = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t0 + dur);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(gain, t0 + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(g);
    g.connect(dest || this.sfxGain);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  noise({ dur = 0.14, gain = 0.3, filter = 1200, delay = 0, q = 1 }) {
    if (!this.ctx || !this.options.sfx) return;
    const t0 = this.ctx.currentTime + delay;
    const len = Math.max(1, Math.floor(this.ctx.sampleRate * dur));
    const buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len);
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    const bp = this.ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = filter;
    bp.Q.value = q;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(gain, t0);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    src.connect(bp); bp.connect(g); g.connect(this.sfxGain);
    src.start(t0);
  }

  // --- named SFX -------------------------------------------------------
  swing(kind) {
    if (kind === 'heavy') { this.noise({ dur: 0.22, gain: 0.26, filter: 700 }); this.tone({ freq: 150, dur: 0.16, type: 'sawtooth', gain: 0.12, slide: -70 }); }
    else if (kind === 'ranged') { this.tone({ freq: 720, dur: 0.1, type: 'triangle', gain: 0.18, slide: -320 }); }
    else { this.noise({ dur: 0.12, gain: 0.2, filter: 1600 }); }
  }
  hit() { this.noise({ dur: 0.08, gain: 0.24, filter: 900 }); this.tone({ freq: 220, dur: 0.07, type: 'square', gain: 0.12, slide: -90 }); }
  crit() { this.tone({ freq: 900, dur: 0.1, type: 'square', gain: 0.16, slide: -400 }); this.noise({ dur: 0.1, gain: 0.2, filter: 2400 }); }
  kill() { this.tone({ freq: 330, dur: 0.18, type: 'triangle', gain: 0.16, slide: -180 }); this.noise({ dur: 0.16, gain: 0.14, filter: 600 }); }
  hurt() { this.tone({ freq: 180, dur: 0.2, type: 'sawtooth', gain: 0.2, slide: -110 }); this.noise({ dur: 0.14, gain: 0.18, filter: 400 }); }
  dash() { this.noise({ dur: 0.18, gain: 0.2, filter: 2600, q: 0.6 }); this.tone({ freq: 520, dur: 0.14, type: 'sine', gain: 0.1, slide: 260 }); }
  special() {
    this.tone({ freq: 200, dur: 0.4, type: 'sawtooth', gain: 0.16, slide: 420 });
    this.noise({ dur: 0.35, gain: 0.2, filter: 1800, q: 0.7 });
  }
  pickup() { this.tone({ freq: 880, dur: 0.09, type: 'triangle', gain: 0.16 }); this.tone({ freq: 1320, dur: 0.11, type: 'triangle', gain: 0.12, delay: 0.06 }); }
  boon() { [523, 659, 784, 1046].forEach((f, i) => this.tone({ freq: f, dur: 0.3, type: 'triangle', gain: 0.14, delay: i * 0.07 })); }
  ui() { this.tone({ freq: 620, dur: 0.06, type: 'square', gain: 0.1 }); }
  door() { this.tone({ freq: 120, dur: 0.5, type: 'sine', gain: 0.2, slide: 60 }); this.noise({ dur: 0.4, gain: 0.14, filter: 300 }); }
  bossRoar() {
    this.tone({ freq: 90, dur: 0.9, type: 'sawtooth', gain: 0.26, slide: -30 });
    this.noise({ dur: 0.8, gain: 0.22, filter: 260, q: 0.5 });
  }
  death() { [330, 262, 196, 147].forEach((f, i) => this.tone({ freq: f, dur: 0.6, type: 'sine', gain: 0.2, delay: i * 0.16 })); }
  victory() { [523, 659, 784, 1046, 1318].forEach((f, i) => this.tone({ freq: f, dur: 0.5, type: 'triangle', gain: 0.16, delay: i * 0.12 })); }

  // --- music -----------------------------------------------------------
  // Each track is a small loop of chord tones plus a bass pulse.
  playMusic(track) {
    this.currentTrack = track;
    if (!this.ctx || !this.options.music) return;
    this.stopMusic(true);
    const tracks = {
      hub: { root: 130.81, chords: [[261.6, 329.6, 392.0], [220.0, 277.2, 329.6], [246.9, 311.1, 370.0], [196.0, 246.9, 293.7]], bpm: 62 },
      combat: { root: 110.0, chords: [[220, 261.6, 329.6], [196, 246.9, 293.7], [174.6, 220, 261.6], [164.8, 207.7, 246.9]], bpm: 96 },
      boss: { root: 82.4, chords: [[164.8, 207.7, 246.9], [155.6, 196, 233.1], [146.8, 185, 220], [138.6, 174.6, 207.7]], bpm: 118 },
      tension: { root: 98.0, chords: [[196, 233.1, 293.7], [185, 220, 277.2], [174.6, 207.7, 261.6], [164.8, 196, 246.9]], bpm: 80 },
    };
    const cfg = tracks[track] || tracks.combat;
    const beat = 60 / cfg.bpm;
    this.step = 0;
    const play = () => {
      if (!this.ctx || !this.options.music || this.currentTrack !== track) return;
      const chord = cfg.chords[this.step % cfg.chords.length];
      // pad
      chord.forEach((f, i) => {
        this.tone({ freq: f, dur: beat * 1.8, type: 'sine', gain: 0.06, delay: i * 0.02, dest: this.musicGain });
      });
      // bass
      this.tone({ freq: cfg.root, dur: beat * 0.9, type: 'triangle', gain: 0.09, dest: this.musicGain });
      if (track === 'boss' || track === 'combat') {
        // percussion pulse on offbeats
        this.tone({ freq: 70, dur: 0.1, type: 'square', gain: 0.07, delay: beat * 0.5, dest: this.musicGain });
      }
      this.step++;
      this.musicTimer = setTimeout(play, beat * 1000);
    };
    play();
  }

  stopMusic(keepTrack) {
    if (this.musicTimer) { clearTimeout(this.musicTimer); this.musicTimer = null; }
    if (!keepTrack) this.currentTrack = null;
  }
}

export const audio = new Audio();
