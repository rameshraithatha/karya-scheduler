from fastapi import APIRouter, HTTPException
from db.models import Action
from db.schemas import ActionSchema, ActionUpdateSchema
from db.session import SessionLocal

router = APIRouter()


@router.post("/actions")
def create_action(action: ActionSchema):
    db = SessionLocal()
    if db.query(Action).filter(Action.name == action.name).first():
        raise HTTPException(status_code=409, detail="Action already exists")
    db.add(Action(name=action.name, type=action.type, config=action.config))
    db.commit()
    return {"message": f"Action '{action.name}' created"}


@router.put("/actions/{name}")
def update_action(name: str, update: ActionUpdateSchema):
    db = SessionLocal()
    action = db.query(Action).filter(Action.name == name).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    action.type = update.type
    action.config = update.config
    db.commit()
    return {"message": f"Action '{name}' updated"}


@router.get("/actions/{name}", response_model=ActionSchema)
def get_action(name: str):
    db = SessionLocal()
    action = db.query(Action).filter(Action.name == name).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.put("/actions/{name}")
def update_action(name: str, update: ActionSchema):
    db = SessionLocal()
    action = db.query(Action).filter(Action.name == name).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    action.type = update.type
    action.config = update.config
    db.commit()
    return {"message": f"Action '{name}' updated"}


@router.delete("/actions/{name}")
def delete_action(name: str):
    db = SessionLocal()
    action = db.query(Action).filter(Action.name == name).first()
    if action:
        db.delete(action)
        db.commit()
        return {"message": f"Action '{name}' deleted"}
    raise HTTPException(status_code=404, detail="Action not found")


@router.get("/actions")
def list_actions():
    db = SessionLocal()
    return db.query(Action).all()
