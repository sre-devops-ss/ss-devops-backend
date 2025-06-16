import json
import logging
from datetime import datetime, timedelta

import boto3

from utils.cassandra_client import CassandraClient
from utils.cross_account import CrossAccountClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class BillingMonitoring:
    def __init__(self, cross_account_client):
        """
        Initialize BillingMonitoring with cross-account client
        
        Args:
            cross_account_client (CrossAccountClient): Client for cross-account operations
        """
        self.cross_account_client = cross_account_client
        self.ce_client=cross_account_client.get_client("ce")
        self.budget_client=cross_account_client.get_client("budget")
        self.cloudwatch_client=cross_account_client.get_client("cloudwatch")
        
        self.cassandra = CassandraClient()

    def setup_billing_monitoring(self, config=None):
        """Set up monitoring for AWS billing"""
        try:
            # Default configuration
            default_config = {
                'monthly_budget': 1000,  # USD
                'anomaly_threshold': 20,  # percentage
                'bandwidth_threshold': 100,  # USD
                'evaluation_periods': 2,
                'period': 300,
                'alarm_actions': [
                    f"arn:aws:sns:{self.cross_account_client.region}:{self.cross_account_client.account_id}:monitoring-alerts"
                ]
            }
            
            # Merge with user config
            if config:
                default_config.update(config)
            
     
            # Set up budget monitoring
            self._setup_budget_monitoring(self.budget_client, default_config)
            
            # Set up cost anomaly detection
            self._setup_anomaly_detection(self.ce_client, default_config)
            
            # Set up bandwidth cost monitoring
            self._setup_bandwidth_monitoring(self.cloudwatch_client, default_config)
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'Billing monitoring enabled successfully',
                    'monitoring_configured': [
                        'budget',
                        'cost_anomaly',
                        'bandwidth_cost'
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error setting up billing monitoring: {str(e)}")
            return {
                'statusCode': 500,
                'body': {
                    'error': 'Internal Server Error',
                    'message': str(e)
                }
            }

    def _setup_budget_monitoring(self, budgets_client, config):
        """Set up AWS Budgets monitoring"""
        try:
            # Create monthly budget
            budgets_client.create_budget(
                AccountId=self.cross_account_client.account_id,
                Budget={
                    'BudgetName': 'Monthly-Budget',
                    'BudgetLimit': {
                        'Amount': str(config['monthly_budget']),
                        'Unit': 'USD'
                    },
                    'BudgetType': 'COST',
                    'TimeUnit': 'MONTHLY'
                },
                NotificationsWithSubscribers=[
                    {
                        'NotificationType': 'ACTUAL',
                        'ComparisonOperator': 'GREATER_THAN',
                        'Threshold': 80,
                        'ThresholdType': 'PERCENTAGE',
                        'NotificationState': 'ALARM',
                        'Subscribers': [
                            {
                                'SubscriptionType': 'EMAIL',
                                'Address': config.get('notification_email', '')
                            }
                        ]
                    }
                ]
            )
            
            # Store budget info in Cassandra
            self.cross_account_client.store_monitoring_config(
                'billing',
                'budget',
                'Monthly-Budget',
                {
                    'metric_name': 'BudgetLimit',
                    'threshold': config['monthly_budget'],
                    'comparison_operator': 'GreaterThanThreshold',
                    'period': config['period']
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting up budget monitoring: {str(e)}")
            raise

    def _setup_anomaly_detection(self, ce_client, config):
        """Set up Cost Anomaly Detection"""
        try:
            # Create anomaly monitor
            ce_client.create_anomaly_monitor(
                AnomalyMonitor={
                    'MonitorType': 'DIMENSIONAL',
                    'DimensionalValueCount': 10
                },
                AnomalySubscription={
                    'Threshold': config['anomaly_threshold'],
                    'Frequency': 'DAILY',
                    'Subscribers': [
                        {
                            'Type': 'EMAIL',
                            'Address': config.get('notification_email', '')
                        }
                    ]
                }
            )
            
            # Store anomaly detection info in Cassandra
            self.cross_account_client.store_monitoring_config(
                'billing',
                'anomaly',
                'Cost-Anomaly-Detection',
                {
                    'metric_name': 'AnomalyThreshold',
                    'threshold': config['anomaly_threshold'],
                    'comparison_operator': 'GreaterThanThreshold',
                    'period': config['period']
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting up anomaly detection: {str(e)}")
            raise

    def _setup_bandwidth_monitoring(self, cloudwatch_client, config):
        """Set up bandwidth cost monitoring"""
        try:
            # Create CloudWatch alarm for bandwidth costs
            cloudwatch_client.put_metric_alarm(
                AlarmName='Bandwidth-Cost-Alarm',
                AlarmDescription='Alarm for bandwidth/data transfer costs',
                MetricName='EstimatedCharges',
                Namespace='AWS/Billing',
                Statistic='Maximum',
                Period=config['period'],
                EvaluationPeriods=config['evaluation_periods'],
                Threshold=config['bandwidth_threshold'],
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[
                    {
                        'Name': 'ServiceName',
                        'Value': 'Amazon CloudFront'
                    },
                    {
                        'Name': 'Currency',
                        'Value': 'USD'
                    }
                ],
                AlarmActions=config['alarm_actions']
            )
            
            # Store bandwidth monitoring info in Cassandra
            self.cross_account_client.store_monitoring_config(
                'billing',
                'bandwidth',
                'Bandwidth-Cost-Alarm',
                {
                    'metric_name': 'EstimatedCharges',
                    'threshold': config['bandwidth_threshold'],
                    'comparison_operator': 'GreaterThanThreshold',
                    'period': config['period']
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting up bandwidth monitoring: {str(e)}")
            raise

def lambda_handler(event, context):
    """Lambda handler for setting up monitoring"""
    try:
        # Get required parameters
        body = json.loads(event.get('body', '{}'))
        account_id = body.get('account_id')
        role_arn = body.get('role_arn')
        region = body.get('region', 'us-east-1')
        config = body.get('config')
        
        if not all([account_id, role_arn]):
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Missing required parameters',
                    'message': 'account_id and role_arn are required'
                }
            }
        
        # Initialize cross-account client
        cross_account_client = CrossAccountClient(account_id, role_arn, region)
        
        # Initialize monitoring
        monitor = BillingMonitoring(cross_account_client)
        
        # Set up monitoring
        return monitor.setup_billing_monitoring(config)
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal Server Error',
                'message': str(e)
            }
        } 