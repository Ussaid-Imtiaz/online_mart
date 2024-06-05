from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import  Session, select, Session
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List
from typing import Annotated
from app.db import create_tables, get_session
from app.models import Product
from app.schemas import ProductRead, ProductCreate

# Step-7: Create contex manager for app lifespan
@asynccontextmanager   # Allows you to run setup code before the application starts and teardown code after the application shuts down. 
async def lifespan(app:FastAPI) -> AsyncGenerator[None,None]:   # indicates that the lifespan function is an async generator(type hint is used to indicate that a function returns an asynchronous generator) that doesn't produce any values (the first None) and doesn't accept any values sent to it (the second None)
    # asyncio.create_task(consume_message("products", settings.BOOTSTRAP_SERVER))
    print("Creating Tables")
    create_tables()
    print("Tables Created")
    yield     # Control is given back to FastAPI, app starts here. code before yield will run before the startup and code after the yield statement runs after the application shuts down
    print("App is shutting down")

# Create instance of FastAPI class 
app : FastAPI = FastAPI(
    lifespan=lifespan, # lifespan tells FastAPI to use the lifespan function to manage the application's lifespan events
    title="My Inventory", 
    version="1.0",
    servers=[
        {
            "url": "http://127.0.0.1:8000",
            "description": "Development Server"
        }
    ]
) 
    
# Step-9: Create all endpoints of Product app
@app.get("/")
async def root():
    return {"Hello" : "This is Inventory Service."}

@app.get("/products", response_model=List[ProductRead])
async def get_all(session:Annotated[Session, Depends(get_session)]
                  ) -> List[ProductRead]:
    
    statement = select(Product)
    products = session.exec(statement).all()
    if products:
        return products
    else:
        raise HTTPException(status_code=404, detail="No Product Found")

@app.get("/products/{id}", response_model=ProductRead )
async def get_one(id: int ,session:Annotated[Session, Depends(get_session)]) -> ProductRead:
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
    session: Annotated[Session, Depends(get_session)]
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





