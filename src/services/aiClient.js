/**
 * Client kết nối và giao tiếp bất đồng bộ với Python AI Core Service (Transkun).
 */

import { logger } from "../utils/logger.js";

const AI_CORE_URL = process.env.AI_CORE_URL || "http://127.0.0.1:5000";

export class AiClient {
  /**
   * Kiểm tra trạng thái hoạt động của Python AI Core.
   */
  static async checkHealth() {
    try {
      const resp = await fetch(`${AI_CORE_URL}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      if (resp.ok) {
        return await resp.json();
      }
      return null;
    } catch (err) {
      logger.debug("Không thể kết nối tới AI Core Service:", err.message);
      return null;
    }
  }

  /**
   * Lấy metadata nhanh (thời lượng, hàng đợi) để tính ETA — KHÔNG tải âm thanh.
   * Trả về null nếu thất bại (không bao giờ ném lỗi, ETA chỉ là tính năng phụ).
   */
  static async estimateUrl(url) {
    try {
      const resp = await fetch(`${AI_CORE_URL}/estimate?url=${encodeURIComponent(url)}`, {
        signal: AbortSignal.timeout(30000),
      });
      if (!resp.ok) return null;
      const data = await resp.json();
      if (!data || !data.success) return null;
      return data;
    } catch (err) {
      logger.debug("Không lấy được ETA từ AI Core /estimate:", err.message);
      return null;
    }
  }

  /**
   * Yêu cầu AI Core tải và chuyển đổi âm thanh từ URL trực tuyến.
   */
  static async transcribeFromUrl(url) {
    logger.info(`Gửi yêu cầu AI transcribe từ URL tới ${AI_CORE_URL}/transcribe: ${url}`);
    const timeoutMs = (parseInt(process.env.TRANSCRIPTION_TIMEOUT_SECONDS, 10) || 600) * 1000;

    const resp = await fetch(`${AI_CORE_URL}/transcribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      signal: AbortSignal.timeout(timeoutMs),
    });

    const data = await resp.json();
    if (!resp.ok || !data.success) {
      throw new Error(data.error || `AI Core trả về lỗi HTTP ${resp.status}`);
    }

    const midiBuffer = Buffer.from(data.midi_base64, "base64");
    return {
      midiBuffer,
      filename: data.filename || `${data.title || "transcription"}.mid`,
      title: data.title || "Piano Piece",
      audioDurationSec: data.audio_duration_sec,
      midiSizeBytes: data.midi_size_bytes || midiBuffer.length,
      elapsedTimeSec: data.elapsed_time_sec || 0,
      deviceDisplay: data.device_display || "AI Core",
      sourceType: data.source_type || "Trực tuyến",
    };
  }

  /**
   * Yêu cầu AI Core chuyển đổi tệp âm thanh tải lên (Buffer).
   */
  static async transcribeFromFile(fileBuffer, filename) {
    logger.info(`Gửi tệp đính kèm (${fileBuffer.length} bytes) tới ${AI_CORE_URL}/transcribe`);
    const timeoutMs = (parseInt(process.env.TRANSCRIPTION_TIMEOUT_SECONDS, 10) || 600) * 1000;

    const formData = new FormData();
    const blob = new Blob([fileBuffer]);
    formData.append("file", blob, filename);

    const resp = await fetch(`${AI_CORE_URL}/transcribe`, {
      method: "POST",
      body: formData,
      signal: AbortSignal.timeout(timeoutMs),
    });

    const data = await resp.json();
    if (!resp.ok || !data.success) {
      throw new Error(data.error || `AI Core trả về lỗi HTTP ${resp.status}`);
    }

    const midiBuffer = Buffer.from(data.midi_base64, "base64");
    return {
      midiBuffer,
      filename: data.filename || `${data.title || "transcription"}.mid`,
      title: data.title || filename,
      audioDurationSec: data.audio_duration_sec,
      midiSizeBytes: data.midi_size_bytes || midiBuffer.length,
      elapsedTimeSec: data.elapsed_time_sec || 0,
      deviceDisplay: data.device_display || "AI Core",
      sourceType: "Tệp tải lên",
    };
  }
}
