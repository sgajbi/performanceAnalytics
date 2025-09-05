# app/api/endpoints/contribution.py
from fastapi import APIRouter, HTTPException, status
import pandas as pd
from adapters.api_adapter import create_engine_config, create_engine_dataframe
from app.models.contribution_requests import ContributionRequest
from app.models.contribution_responses import ContributionResponse, PositionContribution
from engine.compute import run_calculations
from engine.contribution import calculate_position_contribution

router = APIRouter()


@router.post("/contribution", response_model=ContributionResponse, summary="Calculate Position Contribution")
async def calculate_contribution_endpoint(request: ContributionRequest):
    """
    Calculates the performance contribution for each position within a portfolio,
    using the Carino smoothing algorithm for multi-period returns.
    """
    try:
        # 1. Calculate portfolio-level performance to get returns and flags
        portfolio_config = create_engine_config(request.portfolio_data)
        portfolio_df = create_engine_dataframe(
            [item.model_dump(by_alias=True) for item in request.portfolio_data.daily_data]
        )
        portfolio_results = run_calculations(portfolio_df, portfolio_config)

        # 2. Calculate performance for each individual position
        position_results_map = {}
        for position in request.positions_data:
            position_config = create_engine_config(request.portfolio_data) # Use same config
            position_df = create_engine_dataframe(
                [item.model_dump(by_alias=True) for item in position.daily_data]
            )
            position_results_map[position.position_id] = run_calculations(position_df, position_config)
            
        # 3. Calculate the final contribution using all results
        contribution_results = calculate_position_contribution(portfolio_results, position_results_map)

        # 4. Format the response
        total_portfolio_return = (1 + portfolio_results[PortfolioColumns.DAILY_ROR] / 100).prod() - 1
        
        position_contributions = [
            PositionContribution(
                position_id=pos_id,
                total_contribution=data["total_contribution"],
                average_weight=data["average_weight"],
                total_return=data["total_return"],
            ) for pos_id, data in contribution_results.items()
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during contribution calculation: {str(e)}",
        )

    return ContributionResponse(
        calculation_id=request.calculation_id,
        portfolio_number=request.portfolio_number,
        report_start_date=request.portfolio_data.report_start_date,
        report_end_date=request.portfolio_data.report_end_date,
        total_portfolio_return=total_portfolio_return,
        total_contribution=sum(pc.total_contribution for pc in position_contributions),
        position_contributions=position_contributions,
    )