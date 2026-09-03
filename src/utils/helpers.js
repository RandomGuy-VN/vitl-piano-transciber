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
