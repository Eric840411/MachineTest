"""
音頻檢測模組 - 透過 Web Audio API 監控遊戲音頻品質

檢測項目：
- 有無聲音（靜音檢測）
- 音量過小
- 爆音/失真（clipping）
- 單聲道/立體聲
- 底噪

原理：
1. 在頁面載入前注入 JS，攔截 AudioContext
2. 插入 AnalyserNode 採集音頻數據
3. 定期從 Python 端讀取分析結果
"""
import asyncio
import json
import logging
import math
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


# ─── 預設音頻配置 ───
DEFAULT_AUDIO_CONFIG = {
    "enabled": True,
    "duration": 5,
    "sample_interval": 0.2,
    "volume": {
        "min_db": -40,
        "max_db": -3,
        "silence_threshold_db": -60,
    },
    "clipping": {
        "enabled": True,
        "threshold": 0.95,
        "max_ratio": 0.01,
    },
    "stereo": {
        "require_stereo": True,
        "correlation_threshold": 0.95,
    },
    "noise_floor_db": -55,
}


# ─── 注入瀏覽器的 JavaScript（攔截 AudioContext）───
AUDIO_MONITOR_SCRIPT = """
(() => {
  // 避免重複注入
  if (window.__audioMonitorInjected) return;
  window.__audioMonitorInjected = true;

  // 儲存分析結果
  window.__audioMonitor = {
    active: false,
    contexts: [],
    samples: [],
    channelCount: 0,
    sampleRate: 0,
    error: null
  };

  const OrigAudioContext = window.AudioContext || window.webkitAudioContext;
  if (!OrigAudioContext) {
    window.__audioMonitor.error = 'AudioContext not supported';
    return;
  }

  // 保存原始 connect
  const origConnect = AudioNode.prototype.connect;

  // 包裝 AudioContext
  const PatchedAudioContext = function(...args) {
    const ctx = new OrigAudioContext(...args);
    const mon = window.__audioMonitor;

    mon.sampleRate = ctx.sampleRate;
    mon.channelCount = ctx.destination.channelCount;
    mon.active = true;

    // 建立分析鏈
    const analyserMain = ctx.createAnalyser();
    analyserMain.fftSize = 2048;
    analyserMain.smoothingTimeConstant = 0.3;

    // 左右聲道分離
    const splitter = ctx.createChannelSplitter(2);
    const analyserL = ctx.createAnalyser();
    const analyserR = ctx.createAnalyser();
    analyserL.fftSize = 2048;
    analyserR.fftSize = 2048;

    // 建立中繼節點
    const inputGain = ctx.createGain();
    inputGain.gain.value = 1.0;
    inputGain.connect(analyserMain);
    inputGain.connect(splitter);
    splitter.connect(analyserL, 0);
    splitter.connect(analyserR, 1);
    inputGain.connect(ctx.destination);

    // 攔截 connect：凡是連接到 destination 的，改連到 inputGain
    AudioNode.prototype.connect = function(dest, ...cArgs) {
      if (dest === ctx.destination) {
        return origConnect.call(this, inputGain, ...cArgs);
      }
      return origConnect.call(this, dest, ...cArgs);
    };

    // 儲存到 monitor
    mon.contexts.push({
      ctx,
      analyserMain,
      analyserL,
      analyserR,
      inputGain
    });

    // 定期採樣
    const bufLen = analyserMain.frequencyBinCount;
    const dataMain = new Float32Array(bufLen);
    const dataL = new Float32Array(bufLen);
    const dataR = new Float32Array(bufLen);

    const sampleFn = () => {
      if (ctx.state !== 'running') return;

      analyserMain.getFloatTimeDomainData(dataMain);
      analyserL.getFloatTimeDomainData(dataL);
      analyserR.getFloatTimeDomainData(dataR);

      // RMS 計算
      let sumSq = 0, peak = 0, clipCount = 0;
      let sumSqL = 0, sumSqR = 0, sumLR = 0;

      for (let i = 0; i < bufLen; i++) {
        const v = dataMain[i];
        sumSq += v * v;
        const absV = Math.abs(v);
        if (absV > peak) peak = absV;
        if (absV >= 0.95) clipCount++;

        const vL = dataL[i];
        const vR = dataR[i];
        sumSqL += vL * vL;
        sumSqR += vR * vR;
        sumLR  += vL * vR;
      }

      const rms = Math.sqrt(sumSq / bufLen);
      const rmsL = Math.sqrt(sumSqL / bufLen);
      const rmsR = Math.sqrt(sumSqR / bufLen);

      // 聲道相關性（1.0 = 完全相同 = 實質單聲道）
      const denominator = Math.sqrt(sumSqL * sumSqR);
      const correlation = denominator > 0 ? sumLR / denominator : 0;

      // 頻譜數據
      const freqData = new Float32Array(bufLen);
      analyserMain.getFloatFrequencyData(freqData);

      mon.samples.push({
        t: performance.now(),
        rms,
        rmsDb: rms > 0 ? 20 * Math.log10(rms) : -Infinity,
        peak,
        peakDb: peak > 0 ? 20 * Math.log10(peak) : -Infinity,
        clipCount,
        clipRatio: clipCount / bufLen,
        rmsL, rmsR,
        correlation,
        channelCount: ctx.destination.channelCount,
        state: ctx.state,
        // 取前 64 個頻率 bin 做頻譜摘要
        freqSummary: Array.from(freqData.slice(0, 64))
      });

      // 最多保留 200 筆
      if (mon.samples.length > 200) mon.samples.shift();
    };

    setInterval(sampleFn, 200);

    return ctx;
  };

  // 複製原型
  PatchedAudioContext.prototype = OrigAudioContext.prototype;

  window.AudioContext = PatchedAudioContext;
  if (window.webkitAudioContext) {
    window.webkitAudioContext = PatchedAudioContext;
  }
})();
"""


def deep_merge(base: dict, override: dict) -> dict:
    """深度合併字典，override 覆蓋 base"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_audio_config(profile_dir: Path, profiles_base_dir: Path = None) -> dict:
    """
    讀取音頻配置：先載入 _default，再用遊戲專屬覆蓋
    
    Args:
        profile_dir: 遊戲 profile 資料夾（如 machine_profiles/JJBX/）
        profiles_base_dir: machine_profiles/ 根目錄
    """
    config = DEFAULT_AUDIO_CONFIG.copy()

    # 嘗試載入 _default/audio_config.json
    if profiles_base_dir is None:
        profiles_base_dir = profile_dir.parent

    default_path = profiles_base_dir / "_default" / "audio_config.json"
    if default_path.exists():
        try:
            with default_path.open("r", encoding="utf-8") as f:
                default_data = json.load(f)
            config = deep_merge(config, default_data)
        except Exception as e:
            logging.warning(f"[AudioDetector] 讀取預設音頻配置失敗: {e}")

    # 載入遊戲專屬 audio_config.json 並覆蓋
    game_path = profile_dir / "audio_config.json"
    if game_path.exists():
        try:
            with game_path.open("r", encoding="utf-8") as f:
                game_data = json.load(f)
            config = deep_merge(config, game_data)
            logging.info(f"[AudioDetector] 載入遊戲專屬音頻配置: {profile_dir.name}")
        except Exception as e:
            logging.warning(f"[AudioDetector] 讀取遊戲音頻配置失敗: {e}")

    return config


@dataclass
class AudioAnalysisResult:
    """音頻分析結果"""
    has_audio: bool = False
    avg_volume_db: float = -100.0
    peak_volume_db: float = -100.0
    min_volume_db: float = -100.0
    clipping_detected: bool = False
    clipping_ratio: float = 0.0
    is_stereo: bool = False
    channel_correlation: float = 0.0
    noise_floor_db: float = -100.0
    sample_count: int = 0
    issues: list = field(default_factory=list)
    details: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return len(self.issues) == 0 and self.has_audio

    def to_dict(self) -> dict:
        return {
            "has_audio": self.has_audio,
            "avg_volume_db": round(self.avg_volume_db, 2),
            "peak_volume_db": round(self.peak_volume_db, 2),
            "min_volume_db": round(self.min_volume_db, 2),
            "clipping_detected": self.clipping_detected,
            "clipping_ratio": round(self.clipping_ratio, 4),
            "is_stereo": self.is_stereo,
            "channel_correlation": round(self.channel_correlation, 4),
            "noise_floor_db": round(self.noise_floor_db, 2),
            "sample_count": self.sample_count,
            "issues": self.issues,
            "passed": self.passed,
        }


class AudioDetector:
    """音頻品質檢測器"""

    @staticmethod
    async def inject_monitor(page) -> bool:
        """
        在頁面注入音頻監控腳本（需在頁面導航前呼叫）
        
        Args:
            page: Playwright Page 物件
            
        Returns:
            是否成功注入
        """
        try:
            await page.add_init_script(AUDIO_MONITOR_SCRIPT)
            logging.info("[AudioDetector] 音頻監控腳本已注入")
            return True
        except Exception as e:
            logging.error(f"[AudioDetector] 注入音頻監控失敗: {e}")
            return False

    @staticmethod
    async def collect_samples(page, duration: float = 5.0, interval: float = 0.2) -> list:
        """
        收集音頻樣本
        
        Args:
            page: Playwright Page
            duration: 採樣時長（秒）
            interval: 採樣間隔（秒）
        
        Returns:
            樣本列表
        """
        # 清除舊樣本
        await page.evaluate("window.__audioMonitor && (window.__audioMonitor.samples = [])")

        logging.info(f"[AudioDetector] 開始採樣 {duration}s (間隔 {interval}s)...")
        await asyncio.sleep(duration)

        # 讀取樣本
        samples = await page.evaluate("""
            () => {
                const mon = window.__audioMonitor;
                if (!mon) return { error: 'monitor not found', samples: [] };
                return {
                    active: mon.active,
                    sampleRate: mon.sampleRate,
                    channelCount: mon.channelCount,
                    error: mon.error,
                    contextCount: mon.contexts.length,
                    samples: mon.samples.map(s => ({
                        rms: s.rms,
                        rmsDb: s.rmsDb === -Infinity ? -100 : s.rmsDb,
                        peak: s.peak,
                        peakDb: s.peakDb === -Infinity ? -100 : s.peakDb,
                        clipCount: s.clipCount,
                        clipRatio: s.clipRatio,
                        rmsL: s.rmsL,
                        rmsR: s.rmsR,
                        correlation: s.correlation,
                        channelCount: s.channelCount,
                        state: s.state
                    }))
                };
            }
        """)

        if isinstance(samples, dict) and samples.get("error"):
            logging.warning(f"[AudioDetector] 採樣錯誤: {samples['error']}")

        return samples

    @staticmethod
    async def analyze(page, config: dict = None) -> AudioAnalysisResult:
        """
        執行完整音頻分析
        
        Args:
            page: Playwright Page
            config: 音頻配置（來自 audio_config.json）
            
        Returns:
            AudioAnalysisResult
        """
        if config is None:
            config = DEFAULT_AUDIO_CONFIG

        result = AudioAnalysisResult()
        duration = config.get("duration", 5)
        interval = config.get("sample_interval", 0.2)

        # 採集樣本
        raw = await AudioDetector.collect_samples(page, duration, interval)

        if not isinstance(raw, dict):
            result.issues.append("無法取得音頻數據")
            return result

        samples = raw.get("samples", [])
        result.sample_count = len(samples)
        result.details["sample_rate"] = raw.get("sampleRate", 0)
        result.details["context_count"] = raw.get("contextCount", 0)
        result.details["monitor_active"] = raw.get("active", False)

        if not raw.get("active", False):
            result.issues.append("未偵測到 AudioContext（遊戲可能沒有使用 Web Audio API）")
            return result

        if len(samples) == 0:
            result.issues.append("採樣數據為空（音頻可能未播放）")
            return result

        # ─── 分析音量 ───
        vol_cfg = config.get("volume", {})
        rms_dbs = [s["rmsDb"] for s in samples if s["rmsDb"] > -100]

        if rms_dbs:
            result.has_audio = True
            result.avg_volume_db = sum(rms_dbs) / len(rms_dbs)
            result.peak_volume_db = max(s["peakDb"] for s in samples if s["peakDb"] > -100)
            result.min_volume_db = min(rms_dbs)

            silence_threshold = vol_cfg.get("silence_threshold_db", -60)
            if result.avg_volume_db < silence_threshold:
                result.has_audio = False
                result.issues.append(
                    f"平均音量 {result.avg_volume_db:.1f} dB 低於靜音閾值 {silence_threshold} dB"
                )

            min_db = vol_cfg.get("min_db", -40)
            if result.has_audio and result.avg_volume_db < min_db:
                result.issues.append(
                    f"音量過小: 平均 {result.avg_volume_db:.1f} dB < 最低要求 {min_db} dB"
                )

            max_db = vol_cfg.get("max_db", -3)
            if result.peak_volume_db > max_db:
                result.issues.append(
                    f"音量過大: 峰值 {result.peak_volume_db:.1f} dB > 最大限制 {max_db} dB"
                )
        else:
            result.has_audio = False
            result.issues.append("完全無音頻輸出（靜音）")

        # ─── 分析爆音 ───
        clip_cfg = config.get("clipping", {})
        if clip_cfg.get("enabled", True) and samples:
            clip_ratios = [s["clipRatio"] for s in samples]
            max_clip_ratio = max(clip_ratios) if clip_ratios else 0
            avg_clip_ratio = sum(clip_ratios) / len(clip_ratios) if clip_ratios else 0
            result.clipping_ratio = avg_clip_ratio

            max_allowed = clip_cfg.get("max_ratio", 0.01)
            if avg_clip_ratio > max_allowed:
                result.clipping_detected = True
                result.issues.append(
                    f"爆音/失真: clipping 比率 {avg_clip_ratio:.4f} > 閾值 {max_allowed}"
                )

        # ─── 分析聲道 ───
        stereo_cfg = config.get("stereo", {})
        if samples:
            correlations = [s["correlation"] for s in samples if s["rms"] > 0.001]
            if correlations:
                avg_corr = sum(correlations) / len(correlations)
                result.channel_correlation = avg_corr

                corr_threshold = stereo_cfg.get("correlation_threshold", 0.95)
                result.is_stereo = avg_corr < corr_threshold

                if stereo_cfg.get("require_stereo", True) and not result.is_stereo:
                    result.issues.append(
                        f"疑似單聲道: 聲道相關性 {avg_corr:.4f} >= {corr_threshold} "
                        f"(1.0 = 完全相同 = 單聲道)"
                    )
            else:
                result.is_stereo = False

            # 聲道詳情
            channel_count = samples[0].get("channelCount", 0)
            result.details["channel_count"] = channel_count

        # ─── 底噪分析 ───
        noise_floor = config.get("noise_floor_db", -55)
        if rms_dbs:
            quietest = sorted(rms_dbs)[:max(1, len(rms_dbs) // 5)]
            result.noise_floor_db = sum(quietest) / len(quietest)

        logging.info(
            f"[AudioDetector] 分析完成: "
            f"音量={result.avg_volume_db:.1f}dB | "
            f"峰值={result.peak_volume_db:.1f}dB | "
            f"爆音={result.clipping_detected} | "
            f"立體聲={result.is_stereo} | "
            f"問題={len(result.issues)}個"
        )

        return result

    @staticmethod
    async def get_realtime_levels(page) -> Optional[dict]:
        """
        取得即時音量（用於測試工具即時顯示）
        
        Returns:
            {"rms_db": float, "peak_db": float, "rms_l": float, "rms_r": float, "correlation": float}
        """
        try:
            data = await page.evaluate("""
                () => {
                    const mon = window.__audioMonitor;
                    if (!mon || !mon.samples.length) return null;
                    const s = mon.samples[mon.samples.length - 1];
                    return {
                        rms_db: s.rmsDb === -Infinity ? -100 : s.rmsDb,
                        peak_db: s.peakDb === -Infinity ? -100 : s.peakDb,
                        rms_l: s.rmsL,
                        rms_r: s.rmsR,
                        correlation: s.correlation,
                        clip_ratio: s.clipRatio,
                        state: s.state
                    };
                }
            """)
            return data
        except Exception:
            return None

