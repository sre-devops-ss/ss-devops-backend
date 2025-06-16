from cassandra.cluster import Cluster
from cqlshlib.aws_sigv4_auth import SigV4AuthProvider
import os
import logging
from .cassandra_schema import create_keyspace, create_tables
import threading

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class CassandraClient:
    """Utility class for handling Cassandra operations"""
    
    _cluster = None
    _session = None
    _lock = threading.Lock()

    def __init__(self, keyspace=None, region=None, host=None, port=None):
        """Initialize Cassandra client with environment variables"""
        self.keyspace = keyspace or os.environ.get('CASSANDRA_KEYSPACE', 'monitoring')
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        self.host = host or os.environ.get('CASSANDRA_HOST', f'cassandra.{self.region}.amazonaws.com')
        self.port = int(port or os.environ.get('CASSANDRA_PORT', 9142))
        self.ssl_opts = {
            'ca_certs': os.environ.get('CASSANDRA_CA_CERT', '/etc/ssl/certs/ca-bundle.crt'),
            'ssl_version': 2  # PROTOCOL_TLS
        }

        # Use a singleton session for efficiency
        with CassandraClient._lock:
            if CassandraClient._session is None:
                auth_provider = SigV4AuthProvider(region_name=self.region)
                CassandraClient._cluster = Cluster([self.host], port=self.port, auth_provider=auth_provider, ssl_options=self.ssl_opts)
                CassandraClient._session = CassandraClient._cluster.connect(self.keyspace)
        self.session = CassandraClient._session
    
    def connect(self):
        """Connect to Cassandra cluster"""
        try:
            # Create keyspace and tables if they don't exist
            create_keyspace(self.session)
            self.session.set_keyspace(self.keyspace)
            create_tables(self.session)
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Cassandra: {str(e)}")
            return False
    
    def close(self):
        """Close Cassandra connection"""
        with CassandraClient._lock:
            if CassandraClient._cluster:
                CassandraClient._cluster.shutdown()
                CassandraClient._cluster = None
                CassandraClient._session = None
    
    def execute(self, query, params=None):
        """Execute a CQL query"""
        try:
            if not self.session:
                if not self.connect():
                    raise Exception("Failed to connect to Cassandra")
            
            if params:
                return self.session.execute(query, params)
            return self.session.execute(query)
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            return None
    
    def get_metrics(self, account_id, region, namespace, metric_name, start_time=None, end_time=None):
        """Get metrics from Cassandra"""
        query = """
            SELECT * FROM metrics
            WHERE account_id = %s
            AND region = %s
            AND namespace = %s
            AND metric_name = %s
        """
        parameters = [account_id, region, namespace, metric_name]
        
        if start_time:
            query += " AND timestamp >= %s"
            parameters.append(start_time)
        if end_time:
            query += " AND timestamp <= %s"
            parameters.append(end_time)
        
        query += " ORDER BY timestamp DESC"
        
        return self.execute(query, parameters)
    
    def get_alarms(self, account_id, region):
        """Get alarms from Cassandra"""
        query = """
            SELECT * FROM alarms
            WHERE account_id = %s
            AND region = %s
        """
        return self.execute(query, [account_id, region])
    
    def get_resources(self, account_id, region, resource_type):
        """Get resources from Cassandra"""
        query = """
            SELECT * FROM resources
            WHERE account_id = %s
            AND region = %s
            AND resource_type = %s
        """
        return self.execute(query, [account_id, region, resource_type])
    
    def get_monitoring_config(self, account_id, resource_type):
        """Get monitoring configuration from Cassandra"""
        query = """
            SELECT * FROM monitoring_config
            WHERE account_id = %s
            AND resource_type = %s
        """
        return self.execute(query, [account_id, resource_type])
    
    def get_account(self, account_id):
        """Get account information from Cassandra"""
        query = """
            SELECT * FROM accounts
            WHERE account_id = %s
        """
        return self.execute(query, [account_id])

    def shutdown(self):
        with CassandraClient._lock:
            if CassandraClient._cluster:
                CassandraClient._cluster.shutdown()
                CassandraClient._cluster = None
                CassandraClient._session = None 