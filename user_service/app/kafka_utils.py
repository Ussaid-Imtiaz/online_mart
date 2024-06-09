from aiokafka import AIOKafkaProducer, AIOKafkaConsumer 
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from app import settings

async def create_topic():
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await admin_client.start()
    topic_list = [NewTopic(name=settings.KAFKA_USER_TOPIC, num_partitions=2, replication_factor=1)]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only=False)
        print(f"Topic '{settings.KAFKA_USER_TOPIC}' created successfully")
    except Exception as e:
        print(f"Failed to create topic '{settings.KAFKA_USER_TOPIC}': {e}")
    finally:
        await admin_client.close()


# Kafka Producer as a dependency
async def kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

# async def consume_message(topic, bootstrap_servers):
#     # create a consumer instance
#     consumer = AIOKafkaConsumer(
#         topic, 
#         bootstrap_servers = bootstrap_servers,
#         group_id = "my-group",
#         auto_offset_reset = 'earliest'
#     )

#     # Start the consumer
#     await consumer.start()
#     try:
#         # Continuasly listen to message
#         async for message in consumer:
#             print(f'Received message: {message.value} on topic {message.topic}')
#             new_product = product_pb2.Product()
#             new_product.ParseFromString(message.value)
#             print(f'\n\m Consumer Deserialized Data : {new_product}')
#         # Add code to process messages

#     finally:
#         await consumer.stop()