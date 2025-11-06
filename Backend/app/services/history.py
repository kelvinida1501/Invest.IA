from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

import yfinance as yf
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Asset, AssetPrice


def _upsert_price_row(
    db: Session,
    asset_id: int,
    target_date: date,
    close_value: float,
) -> AssetPrice:
    row = (
        db.query(AssetPrice)
        .filter(and_(AssetPrice.asset_id == asset_id, AssetPrice.date == target_date))
        .first()
    )
    if row:
        row.close = close_value
        return row

    row = AssetPrice(asset_id=asset_id, date=target_date, close=close_value)
    db.add(row)
    return row


def ensure_price_history(
    db: Session,
    asset: Asset,
    start_date: date,
    end_date: date,
) -> None:
    """
    Garante que existam cotações diárias para o ativo no intervalo solicitado.
    Faz um backfill usando o yfinance quando houver lacunas.
    """
    if start_date > end_date:
        return

    # Já existe histórico suficiente?
    missing_dates: set[date] = set()
    existing_rows = (
        db.query(AssetPrice.date)
        .filter(
            AssetPrice.asset_id == asset.id,
            AssetPrice.date >= start_date,
            AssetPrice.date <= end_date,
        )
        .all()
    )
    existing_dates = {row.date for row in existing_rows}

    current = start_date
    while current <= end_date:
        if current not in existing_dates:
            missing_dates.add(current)
        current += timedelta(days=1)

    if not missing_dates:
        return

    history = yf.Ticker(asset.symbol).history(
        start=start_date.strftime("%Y-%m-%d"),
        end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=False,
    )

    if history.empty:
        return

    for idx, row in history.iterrows():
        dt = idx.to_pydatetime().date()
        if dt < start_date or dt > end_date:
            continue
        close_val = row.get("Close")
        if close_val is None:
            continue
        try:
            close = float(close_val)
        except (TypeError, ValueError):
            continue
        _upsert_price_row(db, asset.id, dt, close)


def ensure_history_for_assets(
    db: Session,
    assets: Iterable[Asset],
    start_date: date,
    end_date: date,
) -> None:
    for asset in assets:
        ensure_price_history(db, asset, start_date, end_date)
