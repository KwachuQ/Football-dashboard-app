from decimal import Decimal
from sqlalchemy import Column, Integer, String, BigInteger, Numeric
from src.models.base import Base


class TeamDiscipline(Base):
    __tablename__ = "mart_team_discipline"
    
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)
    season_id = Column(Integer, primary_key=True)
    season_name = Column(String)
    season_year = Column(String)
    matches_played = Column(BigInteger)
    total_yellow_cards = Column(Numeric)
    yellow_cards_per_game = Column(Numeric)
    total_red_cards = Column(Numeric)
    total_fouls = Column(Numeric)
    fouls_per_game = Column(Numeric)
    total_offsides = Column(Numeric)
    offsides_per_game = Column(Numeric)
    total_free_kicks = Column(Numeric)
    free_kicks_per_game = Column(Numeric)