from ssl import SSLContext, PROTOCOL_TLSv1_2 , CERT_REQUIRED

import boto3
from cassandra.cluster import Cluster
from cassandra_sigv4.auth import SigV4AuthProvider
from cassandra.auth import PlainTextAuthProvider

import os
import logging
from .cassandra_schema import create_keyspace, create_tables
import threading

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssl_context = SSLContext(PROTOCOL_TLSv1_2)
ssl_context.load_verify_locations('sf-class2-root.crt')
ssl_context.verify_mode = CERT_REQUIRED


class CassandraClient:
    """Utility class for handling Cassandra operations"""
    
    _cluster = None
    _session = None
    _lock = threading.Lock()
    
    

    def __init__(self, host=None, port=None):
        keyspace_name = os.environ.get('CASSANDRA_KEYSPACE', 'monitoring')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        if(os.environ.get('USE_AWS_KEYSPACE') == 'true'):
            
            boto_session = boto3.Session()
            auth_provider = SigV4AuthProvider(boto_session)
            self.port = int(port or os.environ.get('CASSANDRA_PORT', 9142))
            self.host = host or os.environ.get('CASSANDRA_HOST', f'cassandra.{self.region}.amazonaws.com')
            cluster = Cluster([self.host], ssl_context=ssl_context, auth_provider=auth_provider,port=9142)
            self.session = cluster.connect()
            logger.info("Using AWS CASSANDRA")
        else:
            userName=os.environ.get('CASSANDRA_USER','monitoringuser')
            password=os.environ.get('CASSANDRA_PASSWORD','pass')
            self.port = int(port or os.environ.get('CASSANDRA_PORT', 9042))
            host_env = os.environ.get('CASSANDRA_HOST', "192.168.0.1")
            hosts = [h.strip() for h in host_env.split(",") if h.strip()]
            
            
            auth_provider = PlainTextAuthProvider(username=userName, password=password)
            cluster = Cluster(hosts, port=self.port, auth_provider=auth_provider)
            self.session = cluster.connect()
            
            logger.info("Using Local CASSANDRA_KEYSPACE")
            
        """Initialize Cassandra client with environment variables"""

        try:
            query = "CREATE KEYSPACE IF NOT EXISTS "+keyspace_name+" WITH replication "+ "= {'class':'SimpleStrategy', 'replication_factor':1};";
            self.session.execute(query);
            self.session.set_keyspace(keyspace_name)
        except Exception as e:
            logger.warning(f"Could not create keyspace {keyspace_name}: {str(e)}")
            # Try to use existing keyspace
            try:
                self.session.set_keyspace(keyspace_name)
            except Exception as e2:
                logger.error(f"Could not set keyspace {keyspace_name}: {str(e2)}")
                raise

        
        
    
    def getSession(self):
  
        try:            
            return self.session
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