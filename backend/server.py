import json
import os
import time
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from database import init_db
from llm_manager import LLMManager
from models.corpus import Corpus
from models.corpus_entry import CorpusEntry
import logging
from config import settings
from models.error_range import ErrorRange
from models.training_error import TrainingError

logger = logging.getLogger(__name__)

# Initialize database connection
init_db()

app = FastAPI()

# Initialize LLMManager
llm_manager = LLMManager()


class ChatInput(BaseModel):
    history: List[Dict[str, Any]]


class LearnInput(BaseModel):
    chat: List[List[Dict[str, Any]]]
    knowledge: List[str]


class CorpusInput(BaseModel):
    name: str
    description: str = ""


class MessageInput(BaseModel):
    role: str = Field(
        ...,
        description="The role of the message sender (e.g., 'user', 'assistant', 'system')",
    )
    content: str = Field(..., description="The content of the message")


class CorpusEntryInput(BaseModel):
    corpus_name: str = Field(
        ..., description="The name of the corpus this entry belongs to"
    )
    entry_type: str = Field(
        ..., description="The type of the entry: 'chat' or 'knowledge'"
    )
    content: Optional[str] = Field(
        None, description="The content for 'knowledge' type entries"
    )
    messages: Optional[List[MessageInput]] = Field(
        None, description="The list of messages for 'chat' type entries"
    )

    class Config:
        schema_extra = {
            "example": {
                "corpus_name": "my_corpus",
                "entry_type": "chat",
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"},
                    {
                        "role": "assistant",
                        "content": "I'm doing well, thank you for asking. How can I assist you today?",
                    },
                ],
            }
        }


@app.post("/chat")
def chat(chat_input: ChatInput):
    try:
        response = llm_manager.chat(chat_input.history)
        return {"response": response}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/learn")
def learn(input: LearnInput):
    try:
        result = llm_manager.learn(input.chat, input.knowledge)
        return {"message": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save_model")
def save_model():
    try:
        result = llm_manager.save_model()
        return {"saved": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/corpus")
async def create_corpus(corpus_input: CorpusInput):
    try:
        corpus = Corpus(name=corpus_input.name, description=corpus_input.description)
        corpus.save()
        return {"message": "Corpus created successfully", "id": str(corpus.id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/corpus_entry")
async def create_corpus_entry(corpus_entry_input: CorpusEntryInput):
    try:
        corpus = Corpus.objects(name=corpus_entry_input.corpus_name).first()
        if not corpus:
            raise HTTPException(status_code=404, detail="Corpus not found")

        corpus_entry = CorpusEntry(
            entry_type=corpus_entry_input.entry_type,
            corpus=corpus,
        )

        if corpus_entry_input.entry_type == "chat":
            corpus_entry.messages = corpus_entry_input.messages
        else:
            corpus_entry.content = corpus_entry_input.content

        corpus_entry.save()
        corpus.update_timestamp()

        return {
            "message": "corpus_entry created successfully",
            "id": str(corpus_entry.id),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/corpus")
async def get_corpora():
    corpora = Corpus.objects().to_json()
    return {"corpora": corpora}


@app.get("/corpus_entries")
async def get_corpus_entries(
    corpus_id: str = Query(..., description="The ID of the corpus"),
    skip: int = Query(0, description="Number of entries to skip"),
    limit: int = Query(100, description="Maximum number of entries to return"),
):
    try:
        logger.info(f"Fetching corpus entries for corpus_id: {corpus_id}")
        corpus = Corpus.objects(id=corpus_id).first()
        if not corpus:
            logger.warning(f"Corpus not found for id: {corpus_id}")
            raise HTTPException(status_code=404, detail="Corpus not found")

        total_count = CorpusEntry.objects(corpus=corpus).count()
        entries = CorpusEntry.objects(corpus=corpus).skip(skip).limit(limit)

        logger.info(f"Retrieved {len(entries)} entries for corpus_id: {corpus_id}")
        return {
            "total": total_count,
            "entries": entries.to_json(),
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error fetching corpus entries: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.middleware("http")
async def log_responses(request: Request, call_next):
    print("---")
    print(f"start Endpoint: {request.url.path}")

    response = await call_next(request)

    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    # Reconstruct the response
    response = JSONResponse(
        content=json.loads(response_body),
        status_code=response.status_code,
        headers=dict(response.headers),
    )

    print(f"Endpoint: {request.url.path}")
    print(f"Response: {response_body.decode()}")
    print("---")

    return response


@app.get("/saved_models")
async def get_saved_models():
    try:
        # Get the list of saved models from the model directory
        model_dir = settings.model_dir
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
        saved_models = [
            f
            for f in os.listdir(model_dir)
            if os.path.isdir(os.path.join(model_dir, f))
        ]
        return {"models": saved_models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_training_session")
async def create_training_session():
    try:
        # Create a new directory for the training session
        session_name = f"training_session_{int(time.time())}"
        session_dir = os.path.join(settings.model_dir, session_name)
        os.makedirs(session_dir, exist_ok=True)

        # Initialize the model for the new session
        llm_manager.init_new_model(session_dir)

        return {"message": "New training session created", "session_name": session_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/load_model")
async def load_model(model_name: str):
    try:
        model_path = os.path.join(settings.model_dir, model_name)
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail="Model not found")

        # Load the specified model
        llm_manager.load_model(model_path)

        return {"message": f"Model {model_name} loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/error_distribution")
async def get_error_distribution(
    session: str = Query(..., description="Training session name")
):
    distribution = TrainingError.get_distribution(session)
    ranges = ErrorRange.objects.order_by("lower_bound")

    data = []
    range_index = 0
    for range in ranges:
        count = 0
        if (
            range_index < len(distribution)
            and distribution[range_index]["_id"] == range.id
        ):
            count = distribution[range_index]["count"]
            range_index += 1
        data.append(
            {
                "range": f"{range.lower_bound:.1f}-{range.upper_bound:.1f}",
                "count": count,
            }
        )

    return {"distribution": data}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=1127)

# how to run the server
# set port to 1127
# uvicorn backend.server:app --reload --port 1127
# uvicorn backend.server:app --port 1127
