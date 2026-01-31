"""
Workflow State Manager

워크플로우 상태 관리 및 체크포인트 시스템
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger("state_manager")


class Checkpoint(BaseModel):
    """체크포인트 데이터"""
    checkpoint_id: str
    session_id: str
    timestamp: datetime
    phase: str
    state: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default={})


class StateManager:
    """
    워크플로우 상태 관리자

    - 상태 저장 및 복원
    - 체크포인트 생성 및 관리
    - 상태 히스토리 추적
    """

    def __init__(self, storage_dir: str = ".caas/checkpoints"):
        """
        Args:
            storage_dir: 체크포인트 저장 디렉토리
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

        # In-memory 캐시
        self.active_states: Dict[str, Dict[str, Any]] = {}

    def save_checkpoint(
        self,
        session_id: str,
        phase: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        체크포인트 저장

        Args:
            session_id: 세션 ID
            phase: 현재 Phase
            state: 저장할 상태
            metadata: 추가 메타데이터

        Returns:
            str: 체크포인트 ID
        """
        checkpoint_id = f"{session_id}_{phase}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            timestamp=datetime.utcnow(),
            phase=phase,
            state=state,
            metadata=metadata or {},
        )

        # 파일로 저장
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.model_dump(mode="json"), f, indent=2, default=str)

        self.logger.info(f"Checkpoint saved: {checkpoint_id}")
        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        체크포인트 로드

        Args:
            checkpoint_id: 체크포인트 ID

        Returns:
            Optional[Checkpoint]: 체크포인트 데이터
        """
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            self.logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return None

        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        checkpoint = Checkpoint(**data)
        self.logger.info(f"Checkpoint loaded: {checkpoint_id}")
        return checkpoint

    def list_checkpoints(self, session_id: Optional[str] = None) -> List[Checkpoint]:
        """
        체크포인트 목록 조회

        Args:
            session_id: 특정 세션의 체크포인트만 조회 (None이면 전체)

        Returns:
            List[Checkpoint]: 체크포인트 목록
        """
        checkpoints = []

        for checkpoint_file in self.storage_dir.glob("*.json"):
            try:
                with open(checkpoint_file, "r") as f:
                    data = json.load(f)
                checkpoint = Checkpoint(**data)

                if session_id is None or checkpoint.session_id == session_id:
                    checkpoints.append(checkpoint)
            except Exception as e:
                self.logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")

        # 시간 역순 정렬
        checkpoints.sort(key=lambda c: c.timestamp, reverse=True)
        return checkpoints

    def get_latest_checkpoint(self, session_id: str) -> Optional[Checkpoint]:
        """최신 체크포인트 조회"""
        checkpoints = self.list_checkpoints(session_id)
        return checkpoints[0] if checkpoints else None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """체크포인트 삭제"""
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            self.logger.info(f"Checkpoint deleted: {checkpoint_id}")
            return True
        else:
            self.logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return False

    def cleanup_old_checkpoints(self, days: int = 7):
        """오래된 체크포인트 정리"""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = 0

        for checkpoint in self.list_checkpoints():
            if checkpoint.timestamp < cutoff_date:
                self.delete_checkpoint(checkpoint.checkpoint_id)
                deleted_count += 1

        self.logger.info(f"Cleaned up {deleted_count} old checkpoints")
        return deleted_count

    # ========== In-Memory State Management ==========

    def set_state(self, session_id: str, state: Dict[str, Any]):
        """메모리에 상태 저장"""
        self.active_states[session_id] = state

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """메모리에서 상태 조회"""
        return self.active_states.get(session_id)

    def update_state(self, session_id: str, updates: Dict[str, Any]):
        """메모리 상태 업데이트"""
        if session_id in self.active_states:
            self.active_states[session_id].update(updates)
        else:
            self.active_states[session_id] = updates

    def clear_state(self, session_id: str):
        """메모리에서 상태 제거"""
        if session_id in self.active_states:
            del self.active_states[session_id]
            self.logger.info(f"State cleared: {session_id}")


class StateHistory:
    """
    상태 히스토리 추적기

    상태 변화를 추적하고 히스토리를 관리합니다.
    """

    def __init__(self, max_history: int = 100):
        """
        Args:
            max_history: 최대 히스토리 저장 개수
        """
        self.max_history = max_history
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = logger

    def record(self, session_id: str, state: Dict[str, Any], event: str = "update"):
        """상태 변화 기록"""
        if session_id not in self.history:
            self.history[session_id] = []

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "state_snapshot": state.copy(),
        }

        self.history[session_id].append(entry)

        # 최대 개수 초과시 오래된 것 제거
        if len(self.history[session_id]) > self.max_history:
            self.history[session_id] = self.history[session_id][-self.max_history:]

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """히스토리 조회"""
        return self.history.get(session_id, [])

    def get_state_at(self, session_id: str, index: int) -> Optional[Dict[str, Any]]:
        """특정 시점의 상태 조회"""
        history = self.history.get(session_id, [])
        if 0 <= index < len(history):
            return history[index]["state_snapshot"]
        return None

    def clear_history(self, session_id: str):
        """히스토리 삭제"""
        if session_id in self.history:
            del self.history[session_id]


class StateDiff:
    """
    상태 비교 도구

    두 상태 간의 차이를 계산합니다.
    """

    @staticmethod
    def compute_diff(
        state1: Dict[str, Any],
        state2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        두 상태의 차이 계산

        Returns:
            Dict[str, Any]: 변경사항
                - added: 추가된 키
                - removed: 제거된 키
                - modified: 변경된 키와 값
        """
        keys1 = set(state1.keys())
        keys2 = set(state2.keys())

        diff = {
            "added": {k: state2[k] for k in keys2 - keys1},
            "removed": {k: state1[k] for k in keys1 - keys2},
            "modified": {},
        }

        # 공통 키 중 값이 변경된 것 찾기
        common_keys = keys1 & keys2
        for key in common_keys:
            if state1[key] != state2[key]:
                diff["modified"][key] = {
                    "old": state1[key],
                    "new": state2[key],
                }

        return diff

    @staticmethod
    def has_changes(diff: Dict[str, Any]) -> bool:
        """변경사항 존재 여부"""
        return bool(diff["added"] or diff["removed"] or diff["modified"])


# ========== Global State Manager Instance ==========

_global_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """전역 State Manager 인스턴스 반환"""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = StateManager()
    return _global_state_manager
