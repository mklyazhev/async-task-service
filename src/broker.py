from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from src.common.config import get_settings

TASKS_EXCHANGE = RabbitExchange(
    "tasks.exchange", type=ExchangeType.DIRECT, durable=True
)
TASKS_QUEUE = RabbitQueue(
    "tasks.queue",
    durable=True,
    routing_key="tasks.execute",
    arguments={"x-max-priority": 3},
)
broker = RabbitBroker(get_settings().rabbitmq_url)
