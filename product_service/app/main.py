import asyncio
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import  Session, select, Session
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List
from typing import Annotated
from app.db import create_tables, get_session
from app.models import Product
from app.schemas import ProductRead, ProductCreate
from app.kafka_utils import consume_login_user_event, verify_logged_in_user


# Step-7: Create contex manager for app lifespan
@asynccontextmanager   # Allows you to run setup code before the application starts and teardown code after the application shuts down. 
async def lifespan(app:FastAPI) -> AsyncGenerator[None,None]:   # indicates that the lifespan function is an async generator(type hint is used to indicate that a function returns an asynchronous generator) that doesn't produce any values (the first None) and doesn't accept any values sent to it (the second None)
    # asyncio.create_task(consume_message("products", settings.BOOTSTRAP_SERVER))
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
    title="My Products", 
    version="1.0",
    servers=[
        {
            "url": "http://127.0.0.1:8015",
            "description": "Development Server"
        }
    ]
) 
    


# Step-9: Create all endpoints of Product app
@app.get("/")
async def root():
    return {"Hello" : "This is Product Service."}

@app.get("/products", response_model=List[ProductRead])
async def get_all(session:Annotated[Session, Depends(get_session)],
                  username : Annotated[str, Depends(verify_logged_in_user)]
                  ) -> List[ProductRead]:
    
    statement = select(Product)
    products = session.exec(statement).all()
    if products:
        return products
    else:
        raise HTTPException(status_code=404, detail="No Product Found")

@app.get("/products/{id}", response_model=ProductRead )
async def get_one(id: int ,session:Annotated[Session, Depends(get_session)],
username : Annotated[str, Depends(verify_logged_in_user)]
) -> ProductRead:
    # SQLModel queries: Select Product of given id and execute first result
    product = session.exec(select(Product).where(Product.id == id)).first()

    if product:
        return product
    else:
        raise HTTPException(status_code=404, detail="No Product Found")
    
# Post endpoint
@app.post("/products/", response_model=ProductRead)
async def create_product(
    product: ProductCreate, 
    session: Annotated[Session, Depends(get_session)],
    
    )->ProductRead:

    new_product = Product(name=product.name, description=product.description, price=product.price, stock=product.stock)
    # Add product to the database
    session.add(new_product)
    session.commit()
    session.refresh(new_product)
    return new_product

@app.put("/products/{product_id}", response_model=ProductRead)
async def edit_one(
    product_id: int, 
    product_update: ProductCreate, 
    session:Annotated[Session, Depends(get_session)]
    ) -> ProductRead:

    # Fetch the product from the database
    db_product = session.exec(select(Product).where(Product.id == product_id)).first()
        
    if db_product:
        db_product.name = product_update.name
        db_product.description = product_update.description
        db_product.price = product_update.price
        db_product.stock = product_update.stock

        session.add(db_product)
        session.commit()
        session.refresh(db_product) 
        return db_product
    else:
        raise HTTPException(status_code=404, detail="No Product Found")

    
@app.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    session: Annotated[Session, Depends(get_session)]
):
    # Fetch the product from the database
    db_product = session.exec(select(Product).where(Product.id == product_id)).first()

    if db_product:
        session.delete(db_product)
        session.commit()
        return {"message": "Product Deleted Successfully"}
    else:
        raise HTTPException(status_code=404, detail="No Product Found")





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


