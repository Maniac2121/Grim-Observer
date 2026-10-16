/* Reference loader for Claude; not an automatic patch to the APK.
   Serve /audio under WebViewAssetLoader (recommended), not an untested file:// fetch.
   Initialize AudioContext/resume inside the game's existing user-gesture path. */
class GrimAudioPack {
  constructor(context, baseURL, destination = context.destination) {
    this.ctx = context;
    this.baseURL = baseURL.endsWith('/') ? baseURL : baseURL + '/';
    this.manifest = null;
    this.byId = new Map();
    this.buffers = new Map();
    this.pending = new Map();
    this.lastVariant = new Map();
    this.active = new Set();
    this.loops = new Map();
    this.lastPlay = new Map();
    this.maxVoices = 24;
    this.bus = context.createGain();
    this.bus.gain.value = 0.45;
    this.compressor = context.createDynamicsCompressor();
    this.compressor.threshold.value = -14;
    this.compressor.knee.value = 8;
    this.compressor.ratio.value = 8;
    this.compressor.attack.value = 0.003;
    this.compressor.release.value = 0.15;
    this.bus.connect(this.compressor);
    this.compressor.connect(destination);
  }
  async init() {
    const response = await fetch(this.baseURL + 'audio_manifest.json');
    if (!response.ok) throw new Error('Audio manifest: ' + response.status);
    this.manifest = await response.json();
    for (const item of this.manifest.sound_effects) {
      if (!this.byId.has(item.id)) this.byId.set(item.id, []);
      this.byId.get(item.id).push(item);
    }
    return this;
  }
  async decode(item) {
    if (this.buffers.has(item.path)) return this.buffers.get(item.path);
    if (this.pending.has(item.path)) return this.pending.get(item.path);
    const promise = (async () => {
      const r = await fetch(this.baseURL + item.path);
      if (!r.ok) throw new Error('Audio ' + item.path + ': ' + r.status);
      const buffer = await this.ctx.decodeAudioData(await r.arrayBuffer());
      this.buffers.set(item.path, buffer);
      return buffer;
    })();
    this.pending.set(item.path, promise);
    try { return await promise; } finally { this.pending.delete(item.path); }
  }
  async preload(ids) {
    // Bounded concurrency: don't decode the entire 303-file pack on battle start.
    const queue = ids.flatMap(id => this.byId.get(id) || []);
    let index = 0;
    const worker = async () => { while (index < queue.length) await this.decode(queue[index++]); };
    await Promise.all([worker(), worker(), worker()]);
  }
  choose(id) {
    const list = (this.byId.get(id) || []).filter(x => this.buffers.has(x.path));
    if (!list.length) return null;
    let eligible = list.filter(x => x.path !== this.lastVariant.get(id));
    if (!eligible.length) eligible = list;
    const item = eligible[Math.floor(Math.random() * eligible.length)];
    this.lastVariant.set(id, item.path);
    return item;
  }
  play(id, {gain = 0.4, pan = 0, pitch = 1, cooldown = 0.04} = {}) {
    if (this.ctx.state !== 'running' || this.active.size >= this.maxVoices) return null;
    const now = this.ctx.currentTime;
    if (now - (this.lastPlay.get(id) ?? -Infinity) < cooldown) return null;
    const item = this.choose(id);
    if (!item || item.loop) return null;
    const source = this.ctx.createBufferSource();
    source.buffer = this.buffers.get(item.path);
    source.playbackRate.value = Math.max(0.8, Math.min(1.2, pitch));
    const volume = this.ctx.createGain(); volume.gain.value = Math.max(0, Math.min(1, gain));
    const panner = this.ctx.createStereoPanner(); panner.pan.value = Math.max(-1, Math.min(1, pan));
    source.connect(volume); volume.connect(panner); panner.connect(this.bus);
    this.active.add(source); this.lastPlay.set(id, now);
    source.onended = () => { this.active.delete(source); source.disconnect(); volume.disconnect(); panner.disconnect(); };
    source.start(); return source;
  }
  startLoop(emitterId, id, gain = 0.12) {
    if (this.loops.has(emitterId)) return this.loops.get(emitterId);
    if (this.loops.size >= 8) return null;
    const item = this.choose(id);
    if (!item || !item.loop) return null;
    const source = this.ctx.createBufferSource();
    source.buffer = this.buffers.get(item.path); source.loop = true;
    source.loopStart = item.loop_start_frame / item.sample_rate;
    source.loopEnd = item.loop_end_frame_exclusive / item.sample_rate;
    const volume = this.ctx.createGain(); volume.gain.setValueAtTime(0, this.ctx.currentTime);
    volume.gain.linearRampToValueAtTime(gain, this.ctx.currentTime + 0.2);
    source.connect(volume); volume.connect(this.bus); source.start();
    const state = {source, volume}; this.loops.set(emitterId, state); return state;
  }
  stopLoop(emitterId) {
    const state = this.loops.get(emitterId); if (!state) return;
    this.loops.delete(emitterId);
    const now = this.ctx.currentTime;
    state.volume.gain.cancelScheduledValues(now);
    state.volume.gain.setTargetAtTime(0, now, 0.06);
    state.source.onended = () => { state.source.disconnect(); state.volume.disconnect(); };
    state.source.stop(now + 0.3);
  }
  stopAll() {
    for (const source of this.active) { try { source.stop(); } catch (_) {} }
    for (const id of [...this.loops.keys()]) this.stopLoop(id);
  }
}
