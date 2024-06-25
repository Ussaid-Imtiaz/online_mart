import asyncio
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import  Session, select, Session
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List
from typing import Annotated
from app.db import create_tables, get_session
from app.models import Order
from app.schemas import OrderRead, OrderCreate
from app.kafka_utils import consume_login_user_event, verify_logged_in_user
from app import settings
from app.kafka_utils import get_kafka_producer
from aiokafka import AIOKafkaProducer
from app import order_placed_pb2

# Step-7: Create contex manager for app lifespan
@asynccontextmanager   # Allows you to run setup code before the application starts and teardown code after the application shuts down. 
async def lifespan(app:FastAPI) -> AsyncGenerator[None,None]:   # indicates that the lifespan function is an async generator(type hint is used to indicate that a function returns an asynchronous generator) that doesn't produce any values (the first None) and doesn't accept any values sent to it (the second None)
    # asyncio.create_task(consume_message("orders", settings.BOOTSTRAP_SERVER))
    print("Creating Tables")
    create_tables()
    print("Tables Created")
    loop = asyncio.get_event_loop()
    task = loop.create_task(consume_login_user_event())
    yield     # Control is given back to FastAPI, app starts here. code before yield will run before the startup and code after the yield statement runs after the application shuts down
    task.cancel()
    await task
    print("App is shutting down")

# Create instance of FastAPI class 
app : FastAPI = FastAPI(
    lifespan=lifespan, # lifespan tells FastAPI to use the lifespan function to manage the application's lifespan events
    title="My Orders", 
    version="1.0",
    servers=[
        {
            "url": "http://127.0.0.1:8013",
            "description": "Development Server"
        }
    ]
) 
    
# Step-9: Create all endpoints of order app
@app.get("/")
async def root():
    return {"Hello" : "This is Order Service."}

@app.get("/orders", response_model=List[OrderRead])
async def get_all(session:Annotated[Session, Depends(get_session)]
                  ) -> List[OrderRead]:
    
    statement = select(Order)
    orders = session.exec(statement).all()
    if orders:
        return orders
    else:
        raise HTTPException(status_code=404, detail="No order Found")

@app.get("/orders/{id}", response_model=OrderRead )
async def get_one(id: int ,
                  session:Annotated[Session, Depends(get_session)]
                  ) -> OrderRead:
    # SQLModel queries: Select order of given id and execute first result
    order = session.exec(select(Order).where(Order.id == id)).first()

    if order:
        return order
    else:
        raise HTTPException(status_code=404, detail="No order Found")
    
# Post endpoint
@app.post("/orders/", response_model=OrderRead)
async def create_order(
    order: OrderCreate, 
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)],
    username : Annotated[str, Depends(verify_logged_in_user)]
    )-> OrderRead:

    new_order = Order(user_name=order.user_name, product_name=order.product_name, quantity=order.quantity)
    # Add order to the database
    session.add(new_order)
    session.commit()
    session.refresh(new_order)

    order_placed_event = order_placed_pb2.OrderPlaced(user_name=new_order.user_name, 
                                                    product_name=new_order.product_name, 
                                                    quantity=new_order.quantity,)
    serialized_order = order_placed_event.SerializeToString()
    await producer.send_and_wait(settings.KAFKA_ORDER_TOPIC, serialized_order)

    return new_order
   

@app.put("/orders/{order_id}", response_model=OrderRead)
async def edit_one(
    order_id: int, 
    order_update: OrderCreate, 
    session:Annotated[Session, Depends(get_session)],
    username : Annotated[str, Depends(verify_logged_in_user)]
    ) -> OrderRead:

    # Fetch the order from the database
    db_order = session.exec(select(Order).where(Order.id == order_id)).first()
        
    if db_order:
        for key, value in order_update.dict().items():
            setattr(db_order, key, value)

        session.add(db_order)
        session.commit()
        session.refresh(db_order) 
        return db_order
    else:
        raise HTTPException(status_code=404, detail="No order Found")

    
@app.delete("/orders/{order_id}")
async def delete_order(
    order_id: int,
    session: Annotated[Session, Depends(get_session)],
    username : Annotated[str, Depends(verify_logged_in_user)]
):
    # Fetch the order from the database
    db_order = session.exec(select(Order).where(Order.id == order_id)).first()

    if db_order:
        session.delete(db_order)
        session.commit()
        return {"message": "order Deleted Successfully"}
    else:
        raise HTTPException(status_code=404, detail="No order Found")



# # Creating Access Token to give to user for authorisation 
# ALGORITHM: str = "HS256"  # Defining the algorithm used for JWT encoding
# SECRET_KEY: str = "A Secret Key"  # Defining the secret key for encoding and decoding JWTs

# def create_access_token(subject: str, expires_delta: timedelta):  # Function to create a JWT access token
#     expire = datetime.utcnow() + expires_delta  # Setting the token expiry time
#     to_encode = {"exp": expire, "sub": str(subject)}  # Creating the payload with expiry time and subject
#     encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # Encoding the payload to create JWT
#     return encode_jwt  # Returning the generated JWT

# @app.get("/get-token")  # Defining a GET endpoint to generate an access token
# async def get_access_token(name: str):  # Asynchronous function to handle the token generation request
#     token_expiry = timedelta(minutes=1)  # Setting the token expiry time to 1 minute
#     print("Access Token Expiry Time", token_expiry)  # Printing the token expiry time to the console
#     generated_token = create_access_token(subject=name, expires_delta=token_expiry)  # Creating the access token
#     return {"Access Token": generated_token}  # Returning the generated token in a JSON response

# def decode_access_token(token: str):  # Function to decode a JWT access token
#     decoded_jwt = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # Decoding the JWT using the secret key and algorithm
#     return decoded_jwt  # Returning the decoded JWT payload

# @app.get("/decode-token")  # Defining a GET endpoint to decode an access token
# async def decode_token(token: str):  # Asynchronous function to handle the token decoding request
#     try:  # Trying to decode the token
#         decoded_data = decode_access_token(token)  # Decoding the access token
#         return decoded_data  # Returning the decoded data in a JSON response
#     except JWTError as e:  # Handling JWT errors
#         return {"error": str(e)}  # Returning the error message in a JSON response


# fake_users_db: dict[str, dict[str, str]] = {
#     "ameenalam": {
#         "username": "ameenalam",
#         "full_name": "Ameen Alam",
#         "email": "ameenalam@example.com",
#         "password": "ameenalamsecret",
#     },
#     "mjunaid": {
#         "username": "mjunaid",
#         "full_name": "Muhammad Junaid",
#         "email": "mjunaid@example.com",
#         "password": "mjunaidsecret",
#     },
# }

# @app.post("/login")  # Defining a POST endpoint for user login
# async def login_request(data_from_user: Annotated[OAuth2PasswordRequestForm, Depends(OAuth2PasswordRequestForm)]):  # Asynchronous function to handle the login request, using OAuth2PasswordRequestForm for user credentials
    
#     # Step 1 : Validate user credentials from DB
#     user_in_db = fake_users_db.get(data_from_user.username)  # Checking if the username exists in the fake database
#     if user_in_db is None:  # If username is not found
#         raise HTTPException(status_code=400, detail="Incorrect username")  # Raise an HTTP exception with status code 400 and error message

#     # Step 2 : Validate password from DB
#     if user_in_db["password"] != data_from_user.password:  # Checking if the provided password matches the stored password
#         raise HTTPException(status_code=400, detail="Incorrect password")  # Raise an HTTP exception with status code 400 and error message
    
#     # Step 3 : Create access token
#     token_expiry = timedelta(minutes=1)  # Setting the token expiry time to 1 minute
#     generated_token = create_access_token(subject=data_from_user.username, expires_delta=token_expiry)  # Creating the access token using the provided username and expiry time

#     return {"username": data_from_user.username, "access_token": generated_token}  # Returning the username and generated access token in a JSON response


# # Authentication using OAuth2PasswordBearer
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # Defining the OAuth2PasswordBearer scheme with the token URL pointing to the login endpoint

# @app.get("/special-item")  # Defining a GET endpoint to access a special item
# async def special_item(token: Annotated[str, Depends(oauth2_scheme)]):  # Asynchronous function to handle the request, extracting the token using the OAuth2PasswordBearer scheme
#     decoded_data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # Decoding the JWT token to retrieve the payload using the secret key and algorithm
#     return {"username": token, "decoded data": decoded_data}  # Returning the token and the decoded data in a JSON response


