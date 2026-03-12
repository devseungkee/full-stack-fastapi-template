from typing import Any
#from app.core.cache import get_cached_lmp_data, set_cached_lmp_data
from fastapi import APIRouter, HTTPException
from app.models import LMPSnapshotPublic, LMPSnapshotsPublic, LMPSnapshot
from app.api.deps import RedisDep, SessionDep
from pydantic import ValidationError
import gridstatus
from datetime import datetime
from sqlmodel import select
import pandas as pd

router = APIRouter(prefix="/grid", tags=["grid"])

@router.get("/lmp", response_model=LMPSnapshotsPublic)
def fetch_lmp_data(session: SessionDep, redis: RedisDep,  interval_start: str, market: str = "REAL_TIME_5_MIN", iso: str = "CAISO") -> Any:
    cached_data = redis.get_cached_lmp_data(redis, f"lmp:{iso}:{market}:{interval_start}")

    if cached_data is not None:
        try:
            cached_data = LMPSnapshotPublic.model_validate(cached_data, update={"cached": True})
            response = LMPSnapshotsPublic.model_validate(cached_data)
            return response
        except ValidationError as e:
            print(e.errors())

    record = session.exec(
        select(LMPSnapshot)
        .where(LMPSnapshot.interval_start == interval_start)
        .where(LMPSnapshot.iso == iso)
    ).all()

    if record is not None:
        try:
            response = LMPSnapshotsPublic.model_validate(record)
            return response
        except ValidationError as e:
            print(e.errors())

    caiso = gridstatus.CAISO()
    lmp_df = caiso.get_lmp(date="today", market=market, locations="ALL", sleep=1)

    lmp_snapshots = [LMPSnapshot(**row.to_dict()) for _, row in lmp_df.iterrows()]

    session.add_all(lmp_snapshots)
    session.commit()

    redis.set_cached_lmp_data(redis, f"lmp:{iso}:{market}:{interval_start}")

    response = LMPSnapshotsPublic.model_validate(lmp_snapshots)
    return response