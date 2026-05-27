from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import get_agent
import json
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://opscale-roan.vercel.app", "http://localhost:3000"],
       allow_methods=["POST", "GET", "OPTIONS"],
       allow_headers=["*"],
       allow_credentials=True,
)

class QueryRequest(BaseModel):
    message: str
    # pass org_id from Next.js so agent only queries that organization's data
    org_id: str  
@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/health")
def health():
    return {"status": "ok"}

system_prompt_template = """
You are a helpful assistant for a business's internal use. You have access to the following tools to assist you in answering questions:
1. get_overdue_customers(days: int, org_id: str) - Get customers with overdue invoices for the provided organization.
2. get_top_selling_products(limit: int, org_id: str | None) - Get top selling products by quantity, limited to an organization.
3. get_revenue_summary(period: str, org_id: str) - Get a summary of revenue for a given period, scoped to an organization.

When answering questions, use the tools above to get the most accurate and relevant information.
Always use the `org_id` provided in the request (organization id = {org_id}) to ensure you are only accessing data for that organization.
Return concise, factual answers and include any tool outputs verbatim in JSON when appropriate.
"""
@app.post("/api/chat")
async def chat(request: QueryRequest):
    
    # validate org_id
    if not request.org_id:
        return JSONResponse({"error": "org_id required"}, status_code=400)

    system_prompt = system_prompt_template.format(org_id=request.org_id)

    async def event_stream():
        try:
            async for event in get_agent().astream_events(
                {"messages": [{"system": system_prompt, "role": "user", "content": request.message}]},
                version="v2",
            ):
                if event.get("event") == "on_chat_model_stream" and event.get("data", {}).get("chunk", {}).get("content"):
                    yield f"data: {json.dumps({'text': event['data']['chunk'].content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")