from fastapi import HTTPException
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer 
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from app import settings
from app import user_login_pb2



async def create_topic():
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await admin_client.start()
    topic_list = [NewTopic(name=settings.KAFKA_NOTIFICATION_TOPIC, num_partitions=2, replication_factor=1)]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only=False)
        print(f"Topic '{settings.KAFKA_NOTIFICATION_TOPIC}' created successfully")
    except Exception as e:
        print(f"Failed to create topic '{settings.KAFKA_NOTIFICATION_TOPIC}': {e}")
    finally:
        await admin_client.close()


# Kafka Producer as a dependency
async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()


order_placed = set()  # Set to keep track of logged-in users

async def consume_orders():
    # create a consumer instance
    consumer = AIOKafkaConsumer(
        'ORDER',
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_NOTIFICATION_GROUP_ID,
        auto_offset_reset = 'earliest'
    )

    # Start the consumer
    await consumer.start()
    try:
        # Continuasly listen to message
        async for message in consumer:
            print(f'Received message: {message.value} on topic {message.topic}')
            order_confirmation = user_login_pb2.OrderPlaced()
            order_confirmation.ParseFromString(message.value)
            username = order_confirmation.username
            if username:
                order_placed.add(username)
                print(f"User logged in: {username}")
    finally:
        await consumer.stop()

def verify_order_received(username: str):
    if username not in order_placed:
        raise HTTPException(status_code=401, detail="Order not placed")