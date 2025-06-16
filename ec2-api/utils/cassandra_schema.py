from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model

class Account(Model):
    """Model for storing account information"""
    __keyspace__ = 'monitoring'
    __table_name__ = 'accounts'
    
    account_id = columns.Text(primary_key=True)
    account_name = columns.Text()
    role_arn = columns.Text()
    regions = columns.List(columns.Text())
    created_at = columns.DateTime()
    updated_at = columns.DateTime()

class Metric(Model):
    """Model for storing metric data"""
    __keyspace__ = 'monitoring'
    __table_name__ = 'metrics'
    
    account_id = columns.Text(partition_key=True)
    region = columns.Text(partition_key=True)
    namespace = columns.Text(partition_key=True)
    metric_name = columns.Text(partition_key=True)
    timestamp = columns.DateTime(clustering_order='DESC')
    value = columns.Float()
    unit = columns.Text()
    statistic = columns.Text()
    dimensions = columns.Map(columns.Text(), columns.Text())

class Alarm(Model):
    """Model for storing alarm information"""
    __keyspace__ = 'monitoring'
    __table_name__ = 'alarms'
    
    account_id = columns.Text(partition_key=True)
    region = columns.Text(partition_key=True)
    alarm_name = columns.Text(clustering_order='ASC')
    alarm_arn = columns.Text()
    metric_name = columns.Text()
    namespace = columns.Text()
    dimensions = columns.Text()  # JSON string
    threshold = columns.Float()
    comparison_operator = columns.Text()
    evaluation_periods = columns.Integer()
    period = columns.Integer()
    state_value = columns.Text()
    state_updated_timestamp = columns.DateTime()
    created_at = columns.DateTime()
    updated_at = columns.DateTime()

class Resource(Model):
    """Model for storing resource information"""
    __keyspace__ = 'monitoring'
    __table_name__ = 'resources'
    
    account_id = columns.Text(partition_key=True)
    region = columns.Text(partition_key=True)
    resource_type = columns.Text(partition_key=True)
    resource_id = columns.Text(clustering_order='ASC')
    resource_name = columns.Text()
    resource_arn = columns.Text()
    tags = columns.Map(columns.Text(), columns.Text())
    created_at = columns.DateTime()
    updated_at = columns.DateTime()

class MonitoringConfig(Model):
    """Model for storing monitoring configuration"""
    __keyspace__ = 'monitoring'
    __table_name__ = 'monitoring_config'
    
    account_id = columns.Text(partition_key=True)
    resource_type = columns.Text(partition_key=True)
    config = columns.Text()  # JSON string
    created_at = columns.DateTime()
    updated_at = columns.DateTime()

def create_keyspace(session):
    """Create the monitoring keyspace if it doesn't exist"""
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS monitoring
        WITH replication = {
            'class': 'SimpleStrategy',
            'replication_factor': 3
        }
    """)

def create_tables(session):
    """Create all required tables"""
    # Create accounts table
    session.execute("""
        CREATE TABLE IF NOT EXISTS monitoring.accounts (
            account_id text PRIMARY KEY,
            account_name text,
            role_arn text,
            regions list<text>,
            created_at timestamp,
            updated_at timestamp
        )
    """)
    
    # Create metrics table
    session.execute("""
        CREATE TABLE IF NOT EXISTS monitoring.metrics (
            account_id text,
            region text,
            namespace text,
            metric_name text,
            timestamp timestamp,
            value float,
            unit text,
            statistic text,
            dimensions map<text, text>,
            PRIMARY KEY ((account_id, region, namespace, metric_name), timestamp)
        ) WITH CLUSTERING ORDER BY (timestamp DESC)
    """)
    
    # Create alarms table
    session.execute("""
        CREATE TABLE IF NOT EXISTS monitoring.alarms (
            account_id text,
            region text,
            alarm_name text,
            alarm_arn text,
            metric_name text,
            namespace text,
            dimensions text,
            threshold float,
            comparison_operator text,
            evaluation_periods int,
            period int,
            state_value text,
            state_updated_timestamp timestamp,
            created_at timestamp,
            updated_at timestamp,
            PRIMARY KEY ((account_id, region), alarm_name)
        )
    """)
    
    # Create resources table
    session.execute("""
        CREATE TABLE IF NOT EXISTS monitoring.resources (
            account_id text,
            region text,
            resource_type text,
            resource_id text,
            resource_name text,
            resource_arn text,
            tags map<text, text>,
            created_at timestamp,
            updated_at timestamp,
            PRIMARY KEY ((account_id, region, resource_type), resource_id)
        )
    """)
    
    # Create monitoring_config table
    session.execute("""
        CREATE TABLE IF NOT EXISTS monitoring.monitoring_config (
            account_id text,
            resource_type text,
            config text,
            created_at timestamp,
            updated_at timestamp,
            PRIMARY KEY (account_id, resource_type)
        )
    """) 