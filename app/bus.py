"""Accès à Kafka (Aiven for Apache Kafka en démo, Kafka local en dev)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

from app.config import ROOT, Topics, settings


def _security() -> dict[str, Any]:
    if not settings.kafka_ssl_dir:
        return {}
    certs = ROOT / settings.kafka_ssl_dir
    if settings.kafka_sasl_username:
        # Listener SASL d'Aiven : utilisateur / mot de passe + CA du projet
        return {
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "SCRAM-SHA-256",
            "sasl_plain_username": settings.kafka_sasl_username,
            "sasl_plain_password": settings.kafka_sasl_password,
            "ssl_cafile": str(certs / "ca.pem"),
        }
    return {
        "security_protocol": "SSL",
        "ssl_cafile": str(certs / "ca.pem"),
        "ssl_certfile": str(certs / "service.cert"),
        "ssl_keyfile": str(certs / "service.key"),
    }


def ensure_topics(partitions: int = 1) -> None:
    admin = KafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap, **_security())
    existing = set(admin.list_topics())
    missing = [t for t in Topics.ALL if t not in existing]
    if missing:
        try:
            admin.create_topics(
                [NewTopic(t, num_partitions=partitions, replication_factor=_replication()) for t in missing]
            )
        except TopicAlreadyExistsError:
            pass
    admin.close()


def _replication() -> int:
    # Aiven impose un facteur de réplication >= 2 ; en local un seul broker.
    return 2 if settings.kafka_ssl_dir else 1


def producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        value_serializer=lambda v: json.dumps(v, default=str).encode(),
        linger_ms=50,
        **_security(),
    )


def consumer(topics: Iterable[str], group_id: str) -> KafkaConsumer:
    return KafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=group_id,
        value_deserializer=lambda b: json.loads(b.decode()),
        auto_offset_reset="latest",
        enable_auto_commit=True,
        **_security(),
    )
