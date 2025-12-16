from datetime import date
from decimal import Decimal
from sqlalchemy import Column, Integer, String, BigInteger, Numeric, Date
from src.models.base import Base


class HeadToHead(Base):
    __tablename__ = "mart_head_to_head"
    
    team_id_1 = Column(Integer, primary_key=True)
    team_id_2 = Column(Integer, primary_key=True)
    team_1_name = Column(String)
    team_2_name = Column(String)
    total_matches = Column(BigInteger)
    team_1_wins = Column(BigInteger)
    draws = Column(BigInteger)
    team_2_wins = Column(BigInteger)
    team_1_goals = Column(BigInteger)
    team_2_goals = Column(BigInteger)
    team_1_avg_goals = Column(Numeric)
    team_2_avg_goals = Column(Numeric)
    over_15_pct = Column(Numeric)
    over_25_pct = Column(Numeric)
    over_35_pct = Column(Numeric)
    btts_pct = Column(Numeric)
    last_meeting_date = Column(Date)
    last_5_results = Column(String)