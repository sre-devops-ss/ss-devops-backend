import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class MetricsRetriever:
    def __init__(self, cassandra_client):
        self.cassandra = cassandra_client

    def get_metrics_for_plotting(self, account_id, resource_type, metric_name, start_time=None, end_time=None):
        """
        Get metrics data formatted for plotting
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=7)
            if not end_time:
                end_time = datetime.utcnow()

            # Query metrics from Cassandra
            query = """
                SELECT timestamp, value, unit
                FROM monitoring.metrics
                WHERE account_id = %s
                AND resource_type = %s
                AND metric_name = %s
                AND timestamp >= %s
                AND timestamp <= %s
                ALLOW FILTERING
            """
            params = (account_id, resource_type, metric_name, start_time, end_time)
            
            results = self.cassandra.execute(query, params)
            
            # Format data for plotting
            timestamps = []
            values = []
            unit = None
            
            for row in results:
                timestamps.append(row.timestamp)
                values.append(row.value)
                unit = row.unit
            
            return {
                'timestamps': [t.isoformat() for t in timestamps],
                'values': values,
                'unit': unit,
                'metric_name': metric_name,
                'resource_type': resource_type
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics for plotting: {str(e)}")
            raise

    def get_resource_metrics(self, account_id, resource_id, start_time=None, end_time=None):
        """
        Get all metrics for a specific resource
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=7)
            if not end_time:
                end_time = datetime.utcnow()

            # Query metrics from Cassandra
            query = """
                SELECT metric_name, timestamp, value, unit
                FROM monitoring.metrics
                WHERE account_id = %s
                AND resource_id = %s
                AND timestamp >= %s
                AND timestamp <= %s
                ALLOW FILTERING
            """
            params = (account_id, resource_id, start_time, end_time)
            
            results = self.cassandra.execute(query, params)
            
            # Group metrics by name
            metrics_data = {}
            for row in results:
                if row.metric_name not in metrics_data:
                    metrics_data[row.metric_name] = {
                        'timestamps': [],
                        'values': [],
                        'unit': row.unit
                    }
                metrics_data[row.metric_name]['timestamps'].append(row.timestamp)
                metrics_data[row.metric_name]['values'].append(row.value)
            
            # Sort timestamps and values
            for metric_name in metrics_data:
                sorted_data = sorted(zip(metrics_data[metric_name]['timestamps'], 
                                      metrics_data[metric_name]['values']))
                metrics_data[metric_name]['timestamps'] = [t for t, _ in sorted_data]
                metrics_data[metric_name]['values'] = [v for _, v in sorted_data]
                metrics_data[metric_name]['timestamps'] = [t.isoformat() for t in metrics_data[metric_name]['timestamps']]
            
            return metrics_data
            
        except Exception as e:
            logger.error(f"Error getting resource metrics: {str(e)}")
            raise

    def get_alarm_history_for_plotting(self, account_id, resource_id, start_time=None, end_time=None):
        """
        Get alarm history formatted for plotting
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=7)
            if not end_time:
                end_time = datetime.utcnow()

            # Query alarm history from Cassandra
            query = """
                SELECT timestamp, state, severity
                FROM monitoring.alarm_history
                WHERE account_id = %s
                AND resource_id = %s
                AND timestamp >= %s
                AND timestamp <= %s
                ALLOW FILTERING
            """
            params = (account_id, resource_id, start_time, end_time)
            
            results = self.cassandra.execute(query, params)
            
            # Format data for plotting
            timestamps = []
            states = []
            severities = []
            
            for row in results:
                timestamps.append(row.timestamp)
                states.append(row.state)
                severities.append(row.severity)
            
            # Sort by timestamp
            sorted_data = sorted(zip(timestamps, states, severities))
            timestamps = [t for t, _, _ in sorted_data]
            states = [s for _, s, _ in sorted_data]
            severities = [s for _, _, s in sorted_data]
            
            return {
                'timestamps': [t.isoformat() for t in timestamps],
                'states': states,
                'severities': severities
            }
            
        except Exception as e:
            logger.error(f"Error getting alarm history for plotting: {str(e)}")
            raise

    def get_metric_thresholds(self, account_id, resource_type, metric_name):
        """
        Get threshold values for a specific metric
        """
        try:
            query = """
                SELECT warning_threshold, critical_threshold
                FROM monitoring.metric_thresholds
                WHERE account_id = %s
                AND resource_type = %s
                AND metric_name = %s
                ALLOW FILTERING
            """
            params = (account_id, resource_type, metric_name)
            
            results = self.cassandra.execute(query, params)
            
            if results:
                row = results[0]
                return {
                    'warning_threshold': row.warning_threshold,
                    'critical_threshold': row.critical_threshold
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting metric thresholds: {str(e)}")
            raise 