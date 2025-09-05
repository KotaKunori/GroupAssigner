from pydantic import BaseModel
from typing import Optional, List, Dict

from ..value_objects.session_id import SessionId
from ..first_class_collections.participants import Participants
from ..entities.participant import PositionType

class Session(BaseModel):
    """
    Domain object of Session.
    """

    id: SessionId
    group_num: int
    min: int
    max: int
    participants: Participants
    # 任意: 入力で指定された職位配分（各グループのターゲット数）
    # 例: [{"Faculty":1, "Doctoral":1, "Master":1, "Bachelor":1}, ...] を group_num 件
    position_targets: Optional[List[Dict[str, int]]] = None

    @staticmethod
    def of(id: SessionId, group_num: int, min: int, max: int, participants: Participants, position_targets: Optional[List[Dict[str, int]]] = None) -> 'Session':
        return Session(id=id, group_num=group_num, min=min, max=max, participants=participants, position_targets=position_targets)
    
    @staticmethod
    def create(group_num: int, min: int, max: int, participants: Participants, position_targets: Optional[List[Dict[str, int]]] = None) -> 'Session':
        return Session(id=SessionId.generate(), group_num=group_num, min=min, max=max, participants=participants, position_targets=position_targets)

    def get_id(self) -> SessionId:
        return self.id
    
    def get_participants(self) -> Participants:
        return self.participants
    
    def get_group_num(self) -> int:
        return self.group_num

    def get_min(self) -> int:
        return self.min
    
    def get_max(self) -> int:
        return self.max
    
    def get_max_group_range(self) -> range:
        # Use the configured number of groups as the group index range
        return range(self.group_num)
    
    def convert_to_json(self) -> dict:
        return {
            "id": self.id.as_str(),
            "participants": self.participants.convert_to_json(),
        }

    # 追加: 入力由来の職位配分アクセス
    def has_position_targets(self) -> bool:
        return self.position_targets is not None

    def get_position_targets(self) -> Optional[List[Dict[str, int]]]:
        return self.position_targets

    def get_position_targets_as_enum(self) -> Optional[List[Dict[PositionType, int]]]:
        if self.position_targets is None:
            return None
        converted: List[Dict[PositionType, int]] = []
        for per_group in self.position_targets:
            group_map: Dict[PositionType, int] = {
                PositionType.FACULTY: 0,
                PositionType.DOCTORAL: 0,
                PositionType.MASTER: 0,
                PositionType.BACHELOR: 0,
            }
            # 不足キーは0で補完、未知キーは無視
            for k, v in per_group.items():
                key_norm = k.strip().lower()
                if key_norm == "faculty":
                    group_map[PositionType.FACULTY] = int(v)
                elif key_norm == "doctoral":
                    group_map[PositionType.DOCTORAL] = int(v)
                elif key_norm == "master":
                    group_map[PositionType.MASTER] = int(v)
                elif key_norm == "bachelor":
                    group_map[PositionType.BACHELOR] = int(v)
            converted.append(group_map)
        return converted