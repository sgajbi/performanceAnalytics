# engine/mwr.py
from typing import List, Dict

def calculate_money_weighted_return(
    beginning_mv: float,
    ending_mv: float,
    cash_flows: List[Dict]
) -> float:
    """
    Calculates the money-weighted return using a simplified Modified Dietz formula.
    """
    net_cash_flow = sum(cf['amount'] for cf in cash_flows)

    denominator = beginning_mv + net_cash_flow

    if denominator == 0:
        return 0.0

    numerator = ending_mv - beginning_mv - net_cash_flow
    
    return (numerator / denominator) * 100