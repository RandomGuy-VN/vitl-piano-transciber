/**
 * Các hàm tiện ích hỗ trợ định dạng dung lượng, thời lượng, tên tệp tin và nhận diện URL.
 */

export function formatBytes(bytes) {
  if (!bytes || bytes < 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = Number(bytes);
  let unitIndex = 0;
  while (size >= 1024.0 && unitIndex < units.length - 1) {
    size /= 1024.0;
    unitIndex++;
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || seconds < 0) return "Không rõ";
  const totalSeconds = Math.round(Number(seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  const pad = (n) => String(n).padStart(2, "0");

  if (hours > 0) {
    return `${pad(hours)}:${pad(minutes)}:${pad(secs)}`;
  }
  return `${pad(minutes)}:${pad(secs)}`;
}

export function formatElapsedTime(seconds) {
  if (!seconds || seconds < 0) return "0.0s";
  const sec = Number(seconds);
  if (sec < 60) {
    return `${sec.toFixed(1)}s`;
  }
  const mins = Math.floor(sec / 60);
  const remSecs = (sec % 60).toFixed(1);
  return `${mins}m ${remSecs}s`;
}

/**
 * Định dạng ETA dạng "ước lượng": "~45s", "~1m 30s"...
 * Làm tròn lên bội của 5s để tránh cảm giác "quá chính xác".
 */
export function formatEta(seconds) {
  if (seconds === null || seconds === undefined || seconds <= 0) return null;
  const s = Math.max(5, Math.round(Number(seconds) / 5) * 5);
  if (s < 60) return `~${s}s`;
  const mins = Math.floor(s / 60);
  const rem = s % 60;
  return rem ? `~${mins}m ${rem}s` : `~${mins}m`;
}

/**
 * Ước tính thời gian TẢI VỀ âm thanh (giây) theo thời lượng.
 * Benchmark thực tế: ~6s phần cố định (metadata + normalize) + ~3% thời lượng audio.
 */
export function computeDownloadEta(durationSec) {
  if (!durationSec || durationSec <= 0) return null;
  return 6 + 0.03 * Number(durationSec);
}

/**
 * Ước tính thời gian XỬ LÝ AI (giây) theo thời lượng audio.
 * Benchmark CPU 2-thread đã đo: 60s audio ≈ 21s, 300s ≈ 95s
 * → hồi quy tuyến tính: ~8s cố định + 0.29 × thời lượng.
 */
export function computeProcessingEta(durationSec) {
  if (!durationSec || durationSec <= 0) return null;
  return 8 + 0.29 * Number(durationSec);
}

/**
 * Tổng ETA (giây) = tải về + xử lý AI (+ chờ hàng đợi nếu AI Core đang bận).
 * Trả về object chi tiết để embed hiển thị từng phần.
 */
export function buildEtaInfo({ durationSec, activeJobs = 0, maxConcurrentJobs = 1 } = {}) {
  const dlEta = computeDownloadEta(durationSec);
  const procEta = computeProcessingEta(durationSec);
  if (!dlEta || !procEta) return null;

  const queued = Number(activeJobs) >= Number(maxConcurrentJobs);
  const queueEta = queued ? 90 : 0; // ước lượng phẳng ~1m30s nếu phải chờ job khác
  const total = dlEta + procEta + queueEta;

  const parts = [`Tải về: ${formatEta(dlEta)}`, `Xử lý AI: ${formatEta(procEta)}`];
  if (queued) parts.push("Hàng đợi: ~1m 30s");

  return {
    totalSec: total,
    totalText: formatEta(total),
    detailText: parts.join(" • "),
    queued,
  };
}

export function sanitizeFilename(name, maxLength = 80) {
  if (!name) return "transcription";
  const cleaned = name
    .replace(/[\\/*?:"<>|]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return (cleaned || "transcription").slice(0, maxLength);
}

export function isSpotifyUrl(url) {
  if (!url) return false;
  const lower = url.toLowerCase();
  return lower.includes("spotify.com") || lower.includes("spotify.link") || lower.includes("spoti.fi");
}

export function isYoutubeUrl(url) {
  if (!url) return false;
  const lower = url.toLowerCase();
  return lower.includes("youtube.com") || lower.includes("youtu.be");
}

export function isSoundcloudUrl(url) {
  if (!url) return false;
  const lower = url.toLowerCase();
  return lower.includes("soundcloud.com") || lower.includes("on.soundcloud.com");
}

export function detectSourceName(url) {
  if (!url) return "Tệp tải lên";
  if (isYoutubeUrl(url)) return "YouTube";
  if (isSpotifyUrl(url)) return "Spotify";
  if (isSoundcloudUrl(url)) return "SoundCloud";
  if (url.includes("drive.google.com")) return "Google Drive";
  return "Đường dẫn trực tiếp";
}
