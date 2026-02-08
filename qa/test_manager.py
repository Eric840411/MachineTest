"""測試任務管理器 - 共享的 CSV 機器號佇列（線程安全）"""
import logging
from typing import List, Optional, Dict
from threading import Lock


class TestTaskManager:
    """
    共享的 CSV 機器號佇列管理器
    
    所有 URL（GameRunner 線程）從同一個佇列中取機器號：
    - URL A 取 CSV[0], URL B 取 CSV[1]
    - A 跑完後取 CSV[2], B 跑完後取 CSV[3]
    - 以此類推，直到所有機器號處理完畢
    """
    
    def __init__(self, csv_data: List[str]):
        """
        初始化共享佇列
        
        Args:
            csv_data: CSV 機器號列表，例如 ["873-JJBX-0004", "873-JJBX-0005", ...]
        """
        self.csv_data = csv_data
        self._next_index = 0
        self._lock = Lock()
        # 追蹤每個 worker 完成的機器號
        self._worker_history: Dict[str, List[str]] = {}
        
        logging.info(f"[TaskManager] 初始化共享佇列: {len(csv_data)} 個機器號")
        for i, code in enumerate(csv_data):
            logging.info(f"[TaskManager]   [{i+1}] {code}")
    
    def get_next_csv(self, worker_id: str = "") -> Optional[str]:
        """
        從共享佇列中取得下一個機器號（線程安全）
        
        Args:
            worker_id: 呼叫者標識（用於日誌追蹤）
            
        Returns:
            下一個機器號，如果佇列已空則返回 None
        """
        with self._lock:
            if self._next_index >= len(self.csv_data):
                logging.info(f"[TaskManager] {worker_id or 'Worker'} 請求機器號 - 佇列已空")
                return None
            
            code = self.csv_data[self._next_index]
            self._next_index += 1
            
            # 記錄歷史
            if worker_id:
                if worker_id not in self._worker_history:
                    self._worker_history[worker_id] = []
                self._worker_history[worker_id].append(code)
            
            logging.info(
                f"[TaskManager] {worker_id or 'Worker'} 取得機器號 "
                f"[{self._next_index}/{len(self.csv_data)}]: {code}"
            )
            return code
    
    def get_remaining_count(self) -> int:
        """取得佇列中剩餘的機器號數量"""
        with self._lock:
            return max(0, len(self.csv_data) - self._next_index)
    
    def get_progress(self) -> str:
        """取得進度字串，例如 '3/10'"""
        with self._lock:
            return f"{self._next_index}/{len(self.csv_data)}"
    
    def get_worker_history(self) -> Dict[str, List[str]]:
        """取得每個 worker 的執行歷史"""
        with self._lock:
            return {k: list(v) for k, v in self._worker_history.items()}
    
    def is_all_done(self) -> bool:
        """是否所有機器號都已被取走"""
        with self._lock:
            return self._next_index >= len(self.csv_data)
