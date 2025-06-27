#!/usr/bin/env python3
"""
장치 매핑 모듈
장치 좌표와 이름 간의 매핑을 관리합니다.
"""
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

class DeviceMapper:
    """
    장치 매퍼 클래스
    장치 좌표, 이름, 비트 위치 간의 매핑을 처리합니다.
    """
    def __init__(self):
        # 장치 매핑 테이블 초기화 (좌표 -> 장치명)
        # 이미지에 기반하여 정확한 위치로 업데이트
        self.device_map = {
            # 1학년 (1행 1-4열)
            (0, 0): "1-1", (0, 1): "1-2", (0, 2): "1-3", (0, 3): "1-4",
            # 2학년 (1행 8-11열)
            (0, 8): "2-1", (0, 9): "2-2", (0, 10): "2-3", (0, 11): "2-4",
            # 3학년 (2행 1-4열)
            (1, 0): "3-1", (1, 1): "3-2", (1, 2): "3-3", (1, 3): "3-4",
            # 특수실 (3행) - 이미지에 표시된 명칭으로 수정
            (2, 0): "교무열", (2, 1): "교사연2", (2, 2): "맵실", (2, 3): "보건실부",
            (2, 4): "과무E-12", (2, 5): "과학준비", (2, 6): "정의루비", (2, 7): "남여휴게",
            # 특수실 (4행) - 이미지에 표시된 명칭으로 수정
            (3, 0): "교무실", (3, 1): "방사성작", (3, 2): "위클루의", (3, 3): "표1-12",
            (3, 4): "교무지", (3, 5): "진로연구", (3, 6): "모듈2", (3, 7): "정의교자",
            # 특수실 (5행) - 이미지에 표시된 명칭으로 수정
            (4, 0): "B1공통훈", (4, 1): "A1공통훈", (4, 2): "B2공통훈", (4, 3): "A2공통훈",
            (4, 4): "A3공통훈", (4, 5): "강당", (4, 6): "방송실", (4, 7): "별박1-1",
            (4, 8): "별박1-2", (4, 9): "별박1-3", (4, 10): "별박2-1", (4, 11): "별박2-2",
            (4, 12): "운동장", (4, 13): "옥외"
        }
        
        # 역방향 매핑 생성 (장치명 -> 좌표)
        self.device_to_coord = {v: k for k, v in self.device_map.items()}
        
        # 장치 ID -> 장치명 매핑 생성
        self.id_to_device = {}
        for device_name in self.device_to_coord:
            device_id = self._get_device_id(device_name)
            if device_id:
                self.id_to_device[device_id] = device_name
        
        # 상태 코드 매핑 테이블
        self.STATE_CODES = {
            frozenset([]): 0x00,                # 모두 꺼짐
            frozenset([301]): 0x03,             # 3학년 1반만 켜짐
            frozenset([301, 302]): 0x01,        # 3학년 1,2반 모두 켜짐
            # 추가 상태 코드는 더 많은 테스트를 통해 확장 가능
        }
        
        # 상태 코드 역매핑 (서버 응답 해석용)
        self.REVERSE_STATE_CODES = {
            0x00: frozenset([]),                # 모두 꺼짐
            0x03: frozenset([301]),             # 3학년 1반만 켜짐
            0x01: frozenset([301, 302]),        # 3학년 1,2반 모두 켜짐
            # 추가 상태 코드는 더 많은 테스트를 통해 확장 가능
        }
        
        # 그룹 장치 정의
        self.device_groups = {
            # 학년별 그룹
            "1학년전체": ["1-1", "1-2", "1-3", "1-4"],
            "2학년전체": ["2-1", "2-2", "2-3", "2-4"],
            "3학년전체": ["3-1", "3-2", "3-3", "3-4"],
            # 전체 학년
            "전체교실": ["1-1", "1-2", "1-3", "1-4", "2-1", "2-2", "2-3", "2-4", "3-1", "3-2", "3-3", "3-4"],
            # 특수실 그룹
            "교무군": ["교무열", "교무실", "교무지", "교사연2"],
            "특별실": ["맵실", "과무E-12", "위클루의", "모듈2", "진로연구"],
            "공통훈련실": ["B1공통훈", "A1공통훈", "B2공통훈", "A2공통훈", "A3공통훈"],
            "별관": ["별박1-1", "별박1-2", "별박1-3", "별박2-1", "별박2-2"],
            # 모든 장치
            "전체장치": list(self.device_map.values())
        }
    
    def get_device_name(self, row, col):
        """좌표로 장치명 찾기"""
        return self.device_map.get((row, col), "알 수 없음")
    
    def get_device_coords(self, device_name):
        """장치명으로 좌표 찾기"""
        return self.device_to_coord.get(device_name, None)
    
    def get_device_by_id(self, device_id):
        """
        장치 ID로 장치명 찾기
        
        Parameters:
        -----------
        device_id : int
            장치 ID
            
        Returns:
        --------
        str or None
            장치명 또는 없으면 None
        """
        return self.id_to_device.get(device_id)
    
    def get_all_device_ids(self):
        """
        모든 장치의 ID 매핑 정보 반환
        
        Returns:
        --------
        dict
            장치명 -> 장치 ID 매핑 딕셔너리
        """
        device_ids = {}
        for device_name in self.device_to_coord:
            device_id = self._get_device_id(device_name)
            if device_id:
                device_ids[device_name] = device_id
        return device_ids
    
    def get_group_devices(self, group_name):
        """
        그룹명으로 소속 장치 목록 반환
        
        Parameters:
        -----------
        group_name : str
            장치 그룹명 (예: "1학년전체", "전체장치")
            
        Returns:
        --------
        list or None
            그룹에 속한 장치명 목록 또는 그룹이 없으면 None
        """
        return self.device_groups.get(group_name)
    
    def get_all_groups(self):
        """
        모든 장치 그룹 정보 반환
        
        Returns:
        --------
        dict
            그룹명 -> 장치 목록 매핑 딕셔너리
        """
        return self.device_groups
    
    def get_byte_bit_position(self, row, col):
        """좌표에 따른 바이트 위치와 비트 위치 계산"""
        # 기본 비트 위치는 항상 col % 8
        bit_pos = col % 8
        
        # 행과 열에 기반한 바이트 위치 계산 (패턴 사용)
        # 1행(row=0): 10/11, 2행(row=1): 14/15, 3행(row=2): 18/19
        # 즉, 행이 증가할 때마다 바이트 위치는 4씩 증가
        base_byte = 10 + (row * 4)
        
        # 열 그룹에 따른 오프셋 추가 (0-7열은 +0, 8-15열은 +1)
        byte_pos = base_byte + (1 if col >= 8 else 0)
        
        # 디버깅 정보 출력
        logger.debug(f"좌표 매핑: ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
        
        return byte_pos, bit_pos
    
    def get_state_code(self, active_rooms):
        """
        현재 활성화된 반 목록에 따른 상태 코드를 반환합니다.
        
        Parameters:
        -----------
        active_rooms : set
            활성화된 방 ID 집합
            
        Returns:
        --------
        int
            상태 코드 값
        """
        frozen_set = frozenset(active_rooms)
        if frozen_set in self.STATE_CODES:
            return self.STATE_CODES[frozen_set]
        else:
            logger.warning(f"매핑되지 않은 상태 조합: {active_rooms}")
            return 0x00  # 기본값
    
    def get_rooms_from_state_code(self, state_code):
        """
        상태 코드로부터 활성화된 방 목록을 반환합니다.
        
        Parameters:
        -----------
        state_code : int
            서버에서 받은 상태 코드
            
        Returns:
        --------
        set
            활성화된 방 ID 집합
        """
        if state_code in self.REVERSE_STATE_CODES:
            return set(self.REVERSE_STATE_CODES[state_code])
        else:
            logger.warning(f"알 수 없는 상태 코드: 0x{state_code:02X}")
            return set()

    def broadcast_to_device(self, device_id, status=1):
        """
        장치 ID를 직접 사용하여 신호를 전송합니다.
        
        Parameters:
        -----------
        device_id : int
            신호를 보낼 장치 ID
        status : int
            설정할 장치 상태 (1: 켜짐, 0: 꺼짐)
        
        Returns:
        --------
        bool
            전송 성공 여부
        """
        # 필요한 모듈 임포트
        from ..services.packet_builder import packet_builder
        from ..services.network import network_manager
        
        # 장치 ID로 장치명 찾기
        device_name = self.get_device_by_id(device_id)
        if not device_name:
            logger.error(f"장치 ID에 해당하는 장치를 찾을 수 없음: {device_id}")
            return False
        
        # 장치명으로 좌표 찾기
        coords = self.get_device_coords(device_name)
        if not coords:
            logger.error(f"장치명에 해당하는 좌표를 찾을 수 없음: {device_name}")
            return False
        
        row, col = coords
        byte_pos, bit_pos = self.get_byte_bit_position(row, col)
        
        logger.info(f"장치 {device_name}(ID: {device_id})에 상태 {status} 신호 전송 중")
        logger.debug(f"좌표: ({row}, {col}), 바이트 위치: {byte_pos}, 비트 위치: {bit_pos}")
        
        # 패킷 생성 및 전송
        payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, status)
        if payload is None:
            logger.error("패킷 생성 실패")
            return False
        
        success, _ = network_manager.send_payload(payload)
        return success

    def broadcast_to_devices(self, device_ids, status=1):
        """
        여러 장치 ID에 동시에 신호를 전송합니다.
        
        Parameters:
        -----------
        device_ids : list
            신호를 보낼 장치 ID 목록
        status : int
            설정할 장치 상태 (1: 켜짐, 0: 꺼짐)
        
        Returns:
        --------
        dict
            각 장치별 전송 결과
        """
        results = {}
        for device_id in device_ids:
            results[device_id] = self.broadcast_to_device(device_id, status)
        return results
        
    def broadcast_to_group(self, group_name, status=1):
        """
        그룹에 포함된 모든 장치에 신호를 전송합니다.
        
        Parameters:
        -----------
        group_name : str
            장치 그룹명 (예: "1학년전체", "전체장치")
        status : int
            설정할 장치 상태 (1: 켜짐, 0: 꺼짐)
            
        Returns:
        --------
        dict
            결과 정보 (성공한 장치 수, 실패한 장치 수, 결과 목록)
        """
        # 필요한 모듈 임포트
        from ..services.packet_builder import packet_builder
        from ..services.network import network_manager
        
        # 그룹에 포함된 장치 목록 가져오기
        devices = self.get_group_devices(group_name)
        if not devices:
            logger.error(f"그룹명에 해당하는 장치 그룹을 찾을 수 없음: {group_name}")
            return {"success": False, "reason": "Unknown group"}
        
        # 결과 저장용 변수
        results = {"devices": {}, "success_count": 0, "fail_count": 0}
        
        # 각 장치별로 신호 전송
        for device_name in devices:
            # 장치명으로 좌표 찾기
            coords = self.get_device_coords(device_name)
            if not coords:
                logger.warning(f"장치명에 해당하는 좌표를 찾을 수 없음: {device_name}")
                results["devices"][device_name] = False
                results["fail_count"] += 1
                continue
            
            row, col = coords
            byte_pos, bit_pos = self.get_byte_bit_position(row, col)
            
            # 패킷 생성 및 전송
            payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, status)
            if payload is None:
                logger.error(f"패킷 생성 실패: {device_name}")
                results["devices"][device_name] = False
                results["fail_count"] += 1
                continue
            
            # 패킷 전송
            success, _ = network_manager.send_payload(payload)
            results["devices"][device_name] = success
            
            if success:
                results["success_count"] += 1
            else:
                results["fail_count"] += 1
        
        # 전체 결과 반환
        results["total"] = len(devices)
        results["group_name"] = group_name
        results["status"] = "success" if results["fail_count"] == 0 else "partial"
        
        return results

    def get_device_mapping_json(self):
        """
        장치 매핑 정보를 JSON 형식으로 반환
        
        Returns:
        --------
        dict
            장치 매핑 정보를 포함하는 딕셔너리
        """
        # 행/열 기반 그리드 정보
        max_row = max([pos[0] for pos in self.device_map.keys()]) + 1
        max_col = max([pos[1] for pos in self.device_map.keys()]) + 1
        
        # 그리드 구성
        grid = []
        for row in range(max_row):
            grid_row = []
            for col in range(max_col):
                device_name = self.device_map.get((row, col), "")
                grid_row.append({
                    "position": [row, col],
                    "device_name": device_name,
                    "device_id": self._get_device_id(device_name) if device_name else None,
                    "type": self._get_device_type(device_name)
                })
            grid.append(grid_row)
        
        # 1차원 장치 목록
        devices = []
        for pos, device_name in self.device_map.items():
            device_id = self._get_device_id(device_name)
            devices.append({
                "position": list(pos),
                "row": pos[0],
                "col": pos[1],
                "device_name": device_name,
                "device_id": device_id,
                "type": self._get_device_type(device_name)
            })
        
        # 타입별 장치 그룹
        device_groups = {
            "classrooms": [],
            "special_rooms": [],
            "groups": {}
        }
        
        for device in devices:
            if device["type"] == "classroom":
                device_groups["classrooms"].append(device)
            else:
                device_groups["special_rooms"].append(device)
        
        # 그룹 장치 정보 추가
        for group_name, group_devices in self.device_groups.items():
            device_groups["groups"][group_name] = {
                "devices": group_devices,
                "count": len(group_devices)
            }
        
        return {
            "grid": grid,
            "devices": devices,
            "device_groups": device_groups,
            "dimensions": {
                "rows": max_row,
                "cols": max_col
            }
        }
    
    def _get_device_id(self, device_name):
        """
        장치명으로부터 ID 추출
        """
        if not device_name:
            return None
            
        # 학년-반 형식 (예: "1-1", "3-2")
        if '-' in device_name and device_name[0].isdigit():
            grade, class_num = device_name.split('-')
            try:
                grade = int(grade)
                class_num = int(class_num)
                return grade * 100 + class_num  # 예: 1학년 1반 -> 101
            except ValueError:
                pass
        
        # 이미지에 표시된 특수 공간 ID 매핑
        special_rooms = {
            # 새로운 특수 공간 이름들 (패킷 분석 결과 기반)
            "교행연회": 1031,
            "교사연구": 1032,
            "매점": 1033,
            "보건학부": 1034,
            "컴퓨터12": 1035,
            "과학준비": 1036,
            "창의준비": 1037,
            "남여휴게": 1038,
            "교무실": 1039,
            "학생식당": 1040,
            "위클회의": 1041,
            "프로그12": 1042,
            "전문교무": 1043,
            "진로상담": 1044,
            "모둠12": 1045,
            "창의공작": 1046,
            "본관1층": 1047,
            "융합관1층": 1048,
            "본관2층": 1049,
            "융합관2층": 1050,
            "융합관3층": 1051,
            "강당": 1052,
            "방송실": 1053,
            "별관1-1": 1054,
            "별관1-2": 1055,
            "별관1-3": 1056,
            "별관2-1": 1057,
            "별관2-2": 1058,
            "운동장": 1059,
            "옥외": 1060,
            
            # 기존 특수 공간 ID도 유지 (이전 코드와의 호환성)
            "교무실": 1001,
            "과학실": 1002,
            "정의교실": 1003,
            "남여휴게실": 1004,
            "교무실2": 1005,
            "학생식당": 1006,
            "위클래식": 1007,
            "프로그램실": 1008,
            "교무2처": 1009,
            "진로상담": 1010,
            "모듈1실": 1011,
            "정의교실2": 1012,
            "A1호실": 1013,
            "B2호실": 1014,
            "A2호실": 1015,
            "B3호실": 1016,
            "방송실-1": 1017,
            "방송실-2": 1018,
            "방송실-3": 1019,
            "별관1-1": 1020,
            "별관2-1": 1021,
            "별관2-2": 1022,
            "선생영역": 1025,
            "시청각실": 1026,
            "체육관": 1027,
            "보건실부": 1028,
            "교무실": 1029,
            "과학실비": 1030,
            "강당": 1031,
            "방송실": 1032
        }
        
        return special_rooms.get(device_name)
    
    def _get_device_type(self, device_name):
        """
        장치 타입 반환 (교실 또는 특수 공간)
        """
        if not device_name:
            return None
            
        # 학년-반 형식은 교실로 분류
        if '-' in device_name and device_name[0].isdigit():
            return "classroom"
        
        # 그 외는 특수 공간으로 분류
        return "special_room"

# 싱글톤 인스턴스 생성
device_mapper = DeviceMapper() 