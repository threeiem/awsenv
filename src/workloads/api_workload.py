from typing import Dict, List, Optional
from src.core.base_instance import BaseInstance
import time

class APIWorkload(BaseInstance):
    def __init__(self, ec2_client, region: str, instance_type: str, spot: bool = False):
        super().__init__(ec2_client, region)
        self.instance_type = instance_type
        self.spot = spot

    def create_instance(self, subnet_id: str, security_group_id: str, ami_id: str) -> List[str]:
        """Create API instances using either spot or on-demand"""
        try:
            if self.spot:
                return self._create_spot_instance(subnet_id, security_group_id, ami_id)
            return self._create_ondemand_instance(subnet_id, security_group_id, ami_id)
            
        except Exception as e:
            self.logger.error(f"Error creating API instance: {str(e)}")
            raise

    def get_user_data(self) -> str:
        """Return user data script for API servers"""
        return """#!/bin/bash
                yum update -y
                yum install -y docker
                systemctl start docker
                systemctl enable docker

                # Install Docker Compose
                curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
                chmod +x /usr/local/bin/docker-compose

                # Create app directory
                mkdir -p /app

                # Create Docker Compose file
                cat << EOF > /app/docker-compose.yml
                version: '3'
                services:
                    api:
                    image: nginx:latest
                    ports:
                        - "80:80"
                    restart: always
                EOF

                # Start services
                cd /app && docker-compose up -d
                """

    def _create_spot_instance(self, subnet_id: str, security_group_id: str, ami_id: str) -> List[str]:
        """Create spot instances for API servers"""
        try:
            spot_requests = self.ec2.request_spot_instances(
                InstanceCount=1,
                LaunchSpecification={
                    'ImageId': ami_id,
                    'InstanceType': self.instance_type,
                    'SubnetId': subnet_id,
                    'SecurityGroupIds': [security_group_id],
                    'UserData': self.get_user_data()
                }
            )
            
            # Wait for spot instances to be fulfilled
            request_ids = [req['SpotInstanceRequestId'] for req in spot_requests['SpotInstanceRequests']]
            
            # Wait for spot requests to be fulfilled
            waiter