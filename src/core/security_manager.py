from typing import Dict, List
import boto3
import logging

class SecurityManager:
    def __init__(self, ec2_client):
        self.ec2 = ec2_client
        self.logger = logging.getLogger(__name__)

    def create_security_groups(self, vpc_id: str) -> Dict[str, str]:
        """Create security groups for different components"""
        try:
            security_groups = {}
            
            # Create API Security Group
            security_groups['api'] = self._create_api_security_group(vpc_id)
            
            # Create Database Security Group
            security_groups['database'] = self._create_database_security_group(vpc_id, security_groups['api'])
            
            # Create Workflow Security Group
            security_groups['workflow'] = self._create_workflow_security_group(vpc_id, security_groups['api'])
            
            return security_groups
            
        except Exception as e:
            self.logger.error(f"Error creating security groups: {str(e)}")
            raise

    def _create_api_security_group(self, vpc_id: str) -> str:
        """Create security group for API servers"""
        try:
            api_sg = self.ec2.create_security_group(
                GroupName='api-servers',
                Description='Security group for API servers',
                VpcId=vpc_id
            )
            
            # Add inbound rules
            self.ec2.authorize_security_group_ingress(
                GroupId=api_sg['GroupId'],
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '10.0.0.0/16'}]
                    }
                ]
            )
            
            return api_sg['GroupId']
            
        except Exception as e:
            self.logger.error(f"Error creating API security group: {str(e)}")
            raise

    def _create_database_security_group(self, vpc_id: str, api_sg_id: str) -> str:
        """Create security group for database servers"""
        try:
            db_sg = self.ec2.create_security_group(
                GroupName='database-servers',
                Description='Security group for database servers',
                VpcId=vpc_id
            )
            
            # Add inbound rules
            self.ec2.authorize_security_group_ingress(
                GroupId=db_sg['GroupId'],
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'UserIdGroupPairs': [{'GroupId': api_sg_id}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '10.0.0.0/16'}]
                    }
                ]
            )
            
            return db_sg['GroupId']
            
        except Exception as e:
            self.logger.error(f"Error creating database security group: {str(e)}")
            raise

    def _create_workflow_security_group(self, vpc_id: str, api_sg_id: str) -> str:
        """Create security group for workflow servers"""
        try:
            workflow_sg = self.ec2.create_security_group(
                GroupName='workflow-servers',
                Description='Security group for workflow servers',
                VpcId=vpc_id
            )
            
            # Add inbound rules
            self.ec2.authorize_security_group_ingress(
                GroupId=workflow_sg['GroupId'],
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 8080,
                        'ToPort': 8080,
                        'UserIdGroupPairs': [{'GroupId': api_sg_id}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '10.0.0.0/16'}]
                    }
                ]
            )
            
            return workflow_sg['GroupId']
            
        except Exception as e:
            self.logger.error(f"Error creating workflow security group: {str(e)}")
            raise
