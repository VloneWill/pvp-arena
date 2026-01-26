#Imports fast API
from fastapi import FastAPI

#Creates a FastAPI instance
app = FastAPI(title="PvP Arena")

#Defines a health check endpoint
@app.get("/health")
#Returns a JSON response with a status of "ok"
def health():
    return {"status": "ok"}
