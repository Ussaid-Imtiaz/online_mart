from fastapi import HTTPException
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer 
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from app import settings
from app import user_login_pb2



async def create_topic():
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await admin_client.start()
    topic_list = [NewTopic(name=settings.KAFKA_ORDER_TOPIC, num_partitions=2, replication_factor=1)]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only=False)
        print(f"Topic '{settings.KAFKA_ORDER_TOPIC}' created successfully")
    except Exception as e:
        print(f"Failed to create topic '{settings.KAFKA_ORDER_TOPIC}': {e}")
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


logged_in_users = set()  # Set to keep track of logged-in users

async def consume_login_user_event():
    # create a consumer instance
    consumer = AIOKafkaConsumer(
        'user_logged_in',
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_ORDER_GROUP_ID,
        auto_offset_reset = 'earliest'
    )

    # Start the consumer
    await consumer.start()
    try:
        # Continuasly listen to message
        async for message in consumer:
            print(f'Received message: {message.value} on topic {message.topic}')
            user_logged_in_event = user_login_pb2.UserLoggedIn()
            user_logged_in_event.ParseFromString(message.value)
            username = user_logged_in_event.username
            if username:
                logged_in_users.add(username)
                print(f"User logged in: {username}")
    finally:
        await consumer.stop()

def verify_logged_in_user(username: str):
    if username not in logged_in_users:
        raise HTTPException(status_code=401, detail="Please log in first")