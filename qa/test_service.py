"""測試服務客戶端 - 與外部測試服務串接"""
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class TestServiceClient:
    """與外部測試服務串接的客戶端"""
    
    def __init__(self, service_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化測試服務客戶端
        
        Args:
            service_url: 測試服務的URL（例如 "http://localhost:8080"）
            api_key: 可選的API密鑰
        """
        self.service_url = (service_url or "").strip()
        self.api_key = api_key
        self.enabled = bool(self.service_url)
        
        if self.enabled:
            self.session = requests.Session()
            if api_key:
                self.session.headers.update({"Authorization": f"Bearer {api_key}"})
            self.session.headers.update({"Content-Type": "application/json"})
            logging.info(f"[TestService] 已啟用，服務URL: {self.service_url}")
        else:
            logging.info("[TestService] 未啟用（未提供service_url）")
    
    def log_test_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        發送測試事件到外部服務
        
        Args:
            event_type: 事件類型，例如 "button_click", "bet_success", "bet_failed", "button_test"
            data: 包含測試詳情的字典
            
        Returns:
            是否發送成功
        """
        if not self.enabled:
            return False
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        try:
            response = self.session.post(
                f"{self.service_url}/api/test-events",
                json=payload,
                timeout=5.0
            )
            if response.status_code == 200:
                logging.debug(f"[TestService] 事件發送成功: {event_type}")
                return True
            else:
                logging.warning(f"[TestService] 事件發送失敗: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logging.error(f"[TestService] 發送事件失敗: {e}")
            return False
    
    def test_button_response(self, button_selector: str, page_url: str, button_name: str = "") -> bool:
        """
        測試按鈕是否有反應
        
        Args:
            button_selector: 按鈕選擇器
            page_url: 頁面URL
            button_name: 按鈕名稱（可選）
            
        Returns:
            是否發送成功
        """
        return self.log_test_event("button_test", {
            "button_selector": button_selector,
            "button_name": button_name,
            "page_url": page_url,
            "test_type": "response_check"
        })
    
    def log_bet_result(self, success: bool, bet_amount: Optional[float] = None, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        記錄下注結果
        
        Args:
            success: 下注是否成功
            bet_amount: 下注金額（可選）
            details: 其他詳情（可選）
            
        Returns:
            是否發送成功
        """
        event_data = {
            "success": success,
        }
        if bet_amount is not None:
            event_data["bet_amount"] = bet_amount
        if details:
            event_data.update(details)
        
        event_type = "bet_success" if success else "bet_failed"
        return self.log_test_event(event_type, event_data)
    
    def log_entry_status(self, url: str, status: str, error_message: Optional[str] = None) -> bool:
        """
        記錄進入機器的狀態
        
        Args:
            url: 機器URL
            status: 狀態（"success" 或 "failed"）
            error_message: 錯誤訊息（如果失敗）
            
        Returns:
            是否發送成功
        """
        data = {
            "url": url,
            "status": status
        }
        if error_message:
            data["error_message"] = error_message
        
        return self.log_test_event("entry_status", data)

