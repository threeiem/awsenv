from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import boto3
import logging

class BaseInstance(ABC):
    def __init__(self, ec2_client, region: str):
        self.ec2 = ec2_client
        self.region = region
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def create_instance(self, subnet_id: str, security_group_id: str, ami_id: str) -> List[str]:
        pass

    @abstractmethod
    def get_user_data(self) -> str:
        pass

    def wait_for_instances(self, instance_ids: List[str]) -> None:
        waiter = self.ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)

    def tag_instances(self, instance_ids: List[str], tags: List[Dict]) -> None:
        self.ec2.create_tags(Resources=instance_ids, Tags=tags)