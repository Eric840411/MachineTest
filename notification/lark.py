"""Lark 通知客戶端"""
import time
import logging
import requests
from typing import Optional, Dict, Any, List

try:
    from version import get_version_string
except ImportError:
    def get_version_string():
        return "unknown"


class LarkClient:
    """極簡 Lark 文本通知客戶端，內建重試機制與明確日誌"""

    def __init__(self, webhook: Optional[str]):
        self.webhook = (webhook or "").strip()
        self.enabled = bool(self.webhook)
        if not self.enabled:
            logging.warning("[Lark] LARK_WEBHOOK_URL 未設定，推播停用")
        else:
            logging.info(f"[Lark] Webhook 已載入（長度={len(self.webhook)}）")

    def send_text(self, text: str, retries: int = 2, timeout: float = 6.0):
        """發送文本訊息；未設定 webhook 則略過並記錄"""
        if not self.enabled:
            logging.debug("[Lark] 已停用，略過訊息：%s", text[:60])
            return False

        payload = {"msg_type": "text", "content": {"text": text}}
        last_err = None
        for i in range(retries + 1):
            try:
                r = requests.post(self.webhook, json=payload, timeout=timeout)
                if r.status_code >= 200 and r.status_code < 300:
                    logging.info("[Lark] 推播成功")
                    return True
                else:
                    logging.warning("[Lark] 非 2xx 回應：%s %s", r.status_code, r.text[:200])
            except Exception as e:
                last_err = e
                logging.warning("[Lark] 傳送失敗 (try %d/%d)：%s", i+1, retries+1, e)
            time.sleep(0.8 * (i + 1))  # backoff

        logging.error("[Lark] 最終失敗：%s", last_err)
        return False

    def send_test_report(self, report_data: Dict[str, Any]) -> bool:
        """
        發送結構化測試報告到Lark（可轉為Excel格式）
        
        report_data 格式：
        {
            "url": "...",
            "csv_data": "...",
            "entry_status": "success|failed",
            "console_errors": [...],
            "video_status": "normal|black|transparent|error",
            "video_message": "...",
            "button_tests": [...],
            "bet_results": [...]
        }
        """
        if not self.enabled:
            return False
        
        # 構建報告文本
        lines = [
            f"📊 **測試報告** ({get_version_string()})",
            "",
            f"**URL:** {report_data.get('url', 'N/A')}",
            f"**CSV資料:** {report_data.get('csv_data', 'N/A')}",
            "",
            "---",
            ""
        ]
        
        # 進入狀態
        entry_status = report_data.get('entry_status', 'unknown')
        status_emoji = "✅" if entry_status == "success" else "❌"
        lines.append(f"{status_emoji} **進入機器:** {entry_status}")
        
        # Console錯誤
        console_errors = report_data.get('console_errors', [])
        if console_errors:
            error_count = len(console_errors)
            lines.append(f"")
            lines.append(f"⚠️ **Console錯誤:** {error_count} 個")
            # 只顯示前5個錯誤
            for i, error in enumerate(console_errors[:5], 1):
                error_text = error.get('text', str(error))[:100]  # 限制長度
                error_type = error.get('type', 'unknown')
                lines.append(f"  {i}. [{error_type}] {error_text}")
            if error_count > 5:
                lines.append(f"  ... 還有 {error_count - 5} 個錯誤")
        else:
            lines.append(f"✅ **Console錯誤:** 無")
        
        # 視頻狀態
        video_status = report_data.get('video_status', 'unknown')
        video_message = report_data.get('video_message', '')
        if video_status == "normal":
            lines.append(f"✅ **視頻顯示:** 正常")
        else:
            lines.append(f"❌ **視頻顯示:** {video_status}")
            if video_message:
                lines.append(f"   詳情: {video_message}")
        
        # 按鈕測試
        button_tests = report_data.get('button_tests', [])
        if button_tests:
            lines.append(f"")
            lines.append(f"🔘 **按鈕測試:**")
            for test in button_tests:
                button_name = test.get('button', 'Unknown')
                status = test.get('status', 'unknown')
                emoji = "✅" if status == "success" else "❌"
                lines.append(f"  {emoji} {button_name}: {status}")
        else:
            lines.append(f"⚠️ **按鈕測試:** 未執行")
        
        # 下注結果
        bet_results = report_data.get('bet_results', [])
        if bet_results:
            lines.append(f"")
            lines.append(f"💰 **下注結果:**")
            for result in bet_results:
                success = result.get('success', False)
                emoji = "✅" if success else "❌"
                bet_amount = result.get('bet_amount', 'N/A')
                lines.append(f"  {emoji} 下注: {bet_amount} - {'成功' if success else '失敗'}")
        
        # 圖片比對結果
        image_comparisons = report_data.get('image_comparisons', [])
        if image_comparisons:
            lines.append(f"")
            lines.append(f"🖼️ **圖片比對結果:**")
            for comp in image_comparisons:
                stage = comp.get('stage', 'unknown')
                match = comp.get('match', False)
                emoji = "✅" if match else "❌"
                result_info = comp.get('result', {})
                if isinstance(result_info, dict):
                    matched = result_info.get('matched_images', 0)
                    total = result_info.get('total_images', 0)
                    lines.append(f"  {emoji} {stage}: {matched}/{total} 匹配")
                else:
                    lines.append(f"  {emoji} {stage}: {'匹配' if match else '不匹配'}")
        
        report_text = "\n".join(lines)
        return self.send_text(report_text)

