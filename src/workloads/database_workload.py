from typing import Dict, List, Optional
from src.core.base_instance import BaseInstance

class DatabaseWorkload(BaseInstance):
    def __init__(self, ec2_client, region: str, instance_type: str, spot: bool = False):
        super().__init__(ec2_client, region)
        self.instance_type = instance_type
        self.spot = spot

    def create_instance(self, subnet_id: str, security_group_id: str, ami_id: str) -> List[str]:
        # Always use on-demand for production databases
        return self._create_ondemand_instance(subnet_id, security_group_id, ami_id)

    def get_user_data(self) -> str:
        return """#!/bin/bash
                yum update -y
                amazon-linux-extras install postgresql12
                systemctl start postgresql
                """

    def _create_ondemand_instance(self, subnet_id: str, security_group_id: str, ami_id: str) -> List[str]:
        # [Database instance creation logic]
        pass