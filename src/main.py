import typer
import boto3
import json
import logging
from pathlib import Path
from typing import Optional

from src.core.vpc_manager import VPCManager
from src.core.security_manager import SecurityManager
from src.workloads.api_workload import APIWorkload
from src.workloads.database_workload import DatabaseWorkload
from src.workloads.workflow_workload import WorkflowWorkload

app = typer.Typer()

@app.command()
def setup_environment(
    env: str = typer.Option(..., help="Environment to setup (dev/prod)"),
    region: str = typer.Option("us-east-1", help="AWS region"),
    ami_id: str = typer.Option(..., help="AMI ID to use for instances"),
    config_path: Optional[Path] = typer.Option(None, help="Path to config file")
):
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Load configuration
    if config_path is None:
        config_path = Path(__file__).parent / "config" / f"{env}_config.json"
    
    with open(config_path) as f:
        config = json.load(f)

    # Initialize AWS clients
    ec2_client = boto3.client('ec2', region_name=region)

    # Initialize managers
    vpc_manager = VPCManager(ec2_client, region)
    security_manager = SecurityManager(ec2_client)

    try:
        # Create VPC and networking
        vpc_info = vpc_manager.create_vpc(
            config['vpc']['cidr'],
            config['vpc']['public_subnets'],
            config['vpc']['private_subnets']
        )

        # Create security groups
        security_groups = security_manager.create_security_groups(vpc_info['vpc_id'])

        # Initialize workload managers
        workloads = {
            'api': APIWorkload(
                ec2_client, 
                region,
                config['workloads']['api']['instance_type'],
                config['workloads']['api']['spot']
            ),
            'database': DatabaseWorkload(
                ec2_client,
                region,
                config['workloads']['database']['instance_type'],
                config['workloads']['database']['spot']
            ),
            'workflow': WorkflowWorkload(
                ec2_client,
                region,
                config['workloads']['workflow']['instance_type'],
                config['workloads']['workflow']['spot']
            )
        }

        # Launch instances for each workload
        for workload_type, workload in workloads.items():
            subnet_ids = vpc_info['public_subnets'] if workload_type == 'api' else vpc_info['private_subnets']
            instance_ids = workload.create_instance(
                subnet_ids[0],
                security_groups[workload_type],
                ami_id
            )
            logger.info(f"Created {workload_type} instances: {instance_ids}")

    except Exception as e:
        logger.error(f"Error setting up environment: {str(e)}")
        raise

if __name__ == "__main__":
    app()