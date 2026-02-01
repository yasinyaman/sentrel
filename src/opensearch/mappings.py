"""OpenSearch index mappings and policies for Sentry events."""

# Main index mapping for Sentry events
SENTRY_EVENTS_MAPPING = {
    "mappings": {
        "properties": {
            # Timestamps
            "@timestamp": {"type": "date"},
            "received_at": {"type": "date"},
            # Identifiers
            "event_id": {"type": "keyword"},
            "project_id": {"type": "integer"},
            # Core fields
            "level": {"type": "keyword"},
            "platform": {"type": "keyword"},
            "environment": {"type": "keyword"},
            "release": {"type": "keyword"},
            "transaction": {"type": "keyword"},
            "server_name": {"type": "keyword"},
            "logger": {"type": "keyword"},
            # Message & Exception
            "message": {
                "type": "text",
                "analyzer": "standard",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "exception_type": {"type": "keyword"},
            "exception_value": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "stacktrace": {"type": "text"},
            # User
            "user": {
                "properties": {
                    "id": {"type": "keyword"},
                    "email_hash": {"type": "keyword"},
                    "username": {"type": "keyword"},
                    "ip": {"type": "ip"},
                }
            },
            # GeoIP (enrichment)
            "geo": {
                "properties": {
                    "country_code": {"type": "keyword"},
                    "country_name": {"type": "keyword"},
                    "region_name": {"type": "keyword"},
                    "city": {"type": "keyword"},
                    "location": {"type": "geo_point"},
                }
            },
            # Browser & OS
            "browser": {
                "properties": {
                    "name": {"type": "keyword"},
                    "version": {"type": "keyword"},
                }
            },
            "os": {
                "properties": {
                    "name": {"type": "keyword"},
                    "version": {"type": "keyword"},
                }
            },
            "device": {
                "properties": {
                    "family": {"type": "keyword"},
                    "model": {"type": "keyword"},
                    "brand": {"type": "keyword"},
                }
            },
            # Runtime
            "runtime": {
                "properties": {
                    "name": {"type": "keyword"},
                    "version": {"type": "keyword"},
                }
            },
            # Request
            "request": {
                "properties": {
                    "url": {"type": "keyword"},
                    "method": {"type": "keyword"},
                }
            },
            # Tags (dynamic)
            "tags": {"type": "object", "dynamic": True},
            # SDK
            "sdk": {
                "properties": {
                    "name": {"type": "keyword"},
                    "version": {"type": "keyword"},
                }
            },
            # Fingerprint for grouping
            "fingerprint": {"type": "keyword"},
        }
    },
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "refresh_interval": "5s",
        "index.mapping.total_fields.limit": 2000,
    },
}

# Index template for automatic index creation
INDEX_TEMPLATE = {
    "index_patterns": ["sentry-events-*"],
    "template": SENTRY_EVENTS_MAPPING,
    "priority": 100,
    "composed_of": [],
    "_meta": {
        "description": "Template for Sentry event indices",
    },
}

# Index Lifecycle Management policy
ILM_POLICY = {
    "policy": {
        "phases": {
            "hot": {
                "min_age": "0ms",
                "actions": {
                    "rollover": {
                        "max_size": "50gb",
                        "max_age": "1d",
                    },
                    "set_priority": {
                        "priority": 100,
                    },
                },
            },
            "warm": {
                "min_age": "7d",
                "actions": {
                    "shrink": {"number_of_shards": 1},
                    "forcemerge": {"max_num_segments": 1},
                    "set_priority": {
                        "priority": 50,
                    },
                },
            },
            "cold": {
                "min_age": "30d",
                "actions": {
                    "set_priority": {
                        "priority": 0,
                    },
                },
            },
            "delete": {
                "min_age": "90d",
                "actions": {
                    "delete": {},
                },
            },
        }
    }
}

# ISM (Index State Management) policy for OpenSearch
# This is the OpenSearch equivalent of Elasticsearch ILM
ISM_POLICY = {
    "policy": {
        "description": "Sentry events lifecycle policy",
        "default_state": "hot",
        "states": [
            {
                "name": "hot",
                "actions": [
                    {
                        "rollover": {
                            "min_size": "50gb",
                            "min_index_age": "1d",
                        }
                    }
                ],
                "transitions": [
                    {
                        "state_name": "warm",
                        "conditions": {
                            "min_index_age": "7d",
                        },
                    }
                ],
            },
            {
                "name": "warm",
                "actions": [
                    {"force_merge": {"max_num_segments": 1}},
                ],
                "transitions": [
                    {
                        "state_name": "cold",
                        "conditions": {
                            "min_index_age": "30d",
                        },
                    }
                ],
            },
            {
                "name": "cold",
                "actions": [],
                "transitions": [
                    {
                        "state_name": "delete",
                        "conditions": {
                            "min_index_age": "90d",
                        },
                    }
                ],
            },
            {
                "name": "delete",
                "actions": [{"delete": {}}],
                "transitions": [],
            },
        ],
        "ism_template": {
            "index_patterns": ["sentry-events-*"],
            "priority": 100,
        },
    }
}
