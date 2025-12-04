from decimal import Decimal
from sqlalchemy import Column, Integer, String, BigInteger, Numeric
from src.models.base import Base


class TeamPossession(Base):
    __tablename__ = "mart_team_possession"
    
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)
    season_id = Column(Integer, primary_key=True)
    season_name = Column(String)
    season_year = Column(String)
    matches_played = Column(BigInteger)
    avg_possession_pct = Column(Numeric)
    total_accurate_passes = Column(Numeric)
    total_passes = Column(Numeric)
    accurate_passes_per_game = Column(Numeric)
    total_passes_per_game = Column(Numeric)
    pass_accuracy_pct = Column(Numeric)
    total_accurate_long_balls = Column(Numeric)
    accurate_long_balls_per_game = Column(Numeric)
    total_accurate_crosses = Column(Numeric)
    accurate_crosses_per_game = Column(Numeric)
    total_final_third_entries = Column(Numeric)
    final_third_entries_per_game = Column(Numeric)
    total_touches_in_box = Column(Numeric)
    touches_in_box_per_game = Column(Numeric)
    total_dispossessed = Column(Numeric)
    dispossessed_per_game = Column(Numeric)
    total_throw_ins = Column(Numeric)
    throw_ins_per_game = Column(Numeric)
    total_goal_kicks = Column(Numeric)
    goal_kicks_per_game = Column(Numeric)