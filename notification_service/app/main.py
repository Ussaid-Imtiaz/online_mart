from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer
from app import order_placed_pb2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from app import settings

app = FastAPI()

# Kafka consumer for receiving order confirmations
consumer = AIOKafkaConsumer(
    'ORDER',
    bootstrap_servers=settings.BOOTSTRAP_SERVER,
    value_deserializer=lambda m: order_placed_pb2.OrderPlaced().FromString(m)
)

# Email sending configuration
SMTP_SERVER = "smtp.gmail.com"   # Replace with your SMTP server
SMTP_PORT = 587  # Replace with your SMTP port
SMTP_USER = "imtiazussaid@example.com"  # Replace with your email
SMTP_PASSWORD = "Pakistan@1989"  # Replace with your email password

def send_email(to_address, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_address, msg.as_string())
        server.quit()
        print(f"Email sent to {to_address}")
    except Exception as e:
        print(f"Failed to send email to {to_address}: {e}")

@app.on_event("startup")
def on_startup():
    import threading
    threading.Thread(target=consume_order_confirmations, daemon=True).start()

def consume_order_confirmations():
    for message in consumer:
        order_confirmation = message.value
        handle_order_confirmation(order_confirmation)

def handle_order_confirmation(order_confirmation):
    # Replace with logic to get user's email based on order ID
    user_email = "ussaidimtiaz@yahoo.com"
    if order_confirmation.status == "confirmed":
        subject = "Order Confirmation"
        body = f"Your order {order_confirmation.order_id} has been confirmed."
    else:
        subject = "Order Failed"
        body = f"Your order {order_confirmation.order_id} has failed."
    send_email(user_email, subject, body)









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


