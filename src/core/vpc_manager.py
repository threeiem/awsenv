from typing import Dict, List
import boto3
import logging
import time

class VPCManager:
    def __init__(self, ec2_client, region: str):
        self.ec2 = ec2_client
        self.region = region
        self.logger = logging.getLogger(__name__)

    def create_vpc(self, vpc_cidr: str, public_cidrs: List[str], private_cidrs: List[str]) -> Dict:
        """Create VPC with public and private subnets"""
        try:
            # Create VPC
            vpc = self.ec2.create_vpc(
                CidrBlock=vpc_cidr,
                EnableDnsHostnames=True,
                EnableDnsSupport=True
            )
            vpc_id = vpc['Vpc']['VpcId']
            
            # Wait for VPC to be available
            waiter = self.ec2.get_waiter('vpc_available')
            waiter.wait(VpcIds=[vpc_id])
            
            # Create and attach internet gateway
            igw = self.ec2.create_internet_gateway()
            igw_id = igw['InternetGateway']['InternetGatewayId']
            self.ec2.attach_internet_gateway(VpcId=vpc_id, InternetGatewayId=igw_id)
            
            # Create NAT Gateway for private subnets
            public_subnet_id = self._create_public_subnets(vpc_id, public_cidrs, igw_id)[0]
            nat_gateway_id = self._create_nat_gateway(public_subnet_id)
            
            # Create private subnets
            private_subnet_ids = self._create_private_subnets(vpc_id, private_cidrs, nat_gateway_id)
            
            self.logger.info(f"VPC {vpc_id} created successfully with all components")
            
            return {
                'vpc_id': vpc_id,
                'public_subnets': self._get_public_subnet_ids(vpc_id),
                'private_subnets': private_subnet_ids,
                'internet_gateway_id': igw_id,
                'nat_gateway_id': nat_gateway_id
            }
            
        except Exception as e:
            self.logger.error(f"Error creating VPC: {str(e)}")
            raise

    def _create_public_subnets(self, vpc_id: str, cidrs: List[str], igw_id: str) -> List[str]:
        """Create public subnets with route to internet gateway"""
        subnet_ids = []
        try:
            # Create route table for public subnets
            public_route_table = self.ec2.create_route_table(VpcId=vpc_id)
            public_rt_id = public_route_table['RouteTable']['RouteTableId']
            
            # Add route to internet gateway
            self.ec2.create_route(
                RouteTableId=public_rt_id,
                DestinationCidrBlock='0.0.0.0/0',
                GatewayId=igw_id
            )
            
            # Create public subnets
            for i, cidr in enumerate(cidrs):
                subnet = self.ec2.create_subnet(
                    VpcId=vpc_id,
                    CidrBlock=cidr,
                    AvailabilityZone=f'{self.region}{"abcd"[i]}',
                    MapPublicIpOnLaunch=True
                )
                subnet_id = subnet['Subnet']['SubnetId']
                subnet_ids.append(subnet_id)
                
                # Associate subnet with public route table
                self.ec2.associate_route_table(
                    RouteTableId=public_rt_id,
                    SubnetId=subnet_id
                )
                
                # Tag subnet as public
                self.ec2.create_tags(
                    Resources=[subnet_id],
                    Tags=[{'Key': 'Type', 'Value': 'Public'}]
                )
                
            return subnet_ids
            
        except Exception as e:
            self.logger.error(f"Error creating public subnets: {str(e)}")
            raise

    def _create_private_subnets(self, vpc_id: str, cidrs: List[str], nat_gateway_id: str) -> List[str]:
        """Create private subnets with route to NAT gateway"""
        subnet_ids = []
        try:
            # Create route table for private subnets
            private_route_table = self.ec2.create_route_table(VpcId=vpc_id)
            private_rt_id = private_route_table['RouteTable']['RouteTableId']
            
            # Add route to NAT gateway
            self.ec2.create_route(
                RouteTableId=private_rt_id,
                DestinationCidrBlock='0.0.0.0/0',
                NatGatewayId=nat_gateway_id
            )
            
            # Create private subnets
            for i, cidr in enumerate(cidrs):
                subnet = self.ec2.create_subnet(
                    VpcId=vpc_id,
                    CidrBlock=cidr,
                    AvailabilityZone=f'{self.region}{"abcd"[i]}'
                )
                subnet_id = subnet['Subnet']['SubnetId']
                subnet_ids.append(subnet_id)
                
                # Associate subnet with private route table
                self.ec2.associate_route_table(
                    RouteTableId=private_rt_id,
                    SubnetId=subnet_id
                )
                
                # Tag subnet as private
                self.ec2.create_tags(
                    Resources=[subnet_id],
                    Tags=[{'Key': 'Type', 'Value': 'Private'}]
                )
                
            return subnet_ids
            
        except Exception as e:
            self.logger.error(f"Error creating private subnets: {str(e)}")
            raise

    def _create_nat_gateway(self, public_subnet_id: str) -> str:
        """Create NAT Gateway in the public subnet"""
        try:
            # Allocate Elastic IP for NAT Gateway
            eip = self.ec2.allocate_address(Domain='vpc')
            
            # Create NAT Gateway
            nat_gateway = self.ec2.create_nat_gateway(
                SubnetId=public_subnet_id,
                AllocationId=eip['AllocationId']
            )
            
            # Wait for NAT Gateway to be available
            waiter = self.ec2.get_waiter('nat_gateway_available')
            waiter.wait(NatGatewayIds=[nat_gateway['NatGateway']['NatGatewayId']])
            
            return nat_gateway['NatGateway']['NatGatewayId']
            
        except Exception as e:
            self.logger.error(f"Error creating NAT Gateway: {str(e)}")
            raise

    def _get_public_subnet_ids(self, vpc_id: str) -> List[str]:
        """Get all public subnet IDs in the VPC"""
        try:
            subnets = self.ec2.describe_subnets(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'tag:Type', 'Values': ['Public']}
                ]
            )
            return [subnet['SubnetId'] for subnet in subnets['Subnets']]
            
        except Exception as e:
            self.logger.error(f"Error getting public subnet IDs: {str(e)}")
            raise
