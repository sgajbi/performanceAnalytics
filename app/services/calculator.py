import calendar
import logging
from datetime import date, datetime
from decimal import Decimal, getcontext

import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.constants import (
    BEGIN_MARKET_VALUE_FIELD,
    BOD_CASHFLOW_FIELD,
    DAILY_ROR_PERCENT_FIELD,
    END_MARKET_VALUE_FIELD,
    EOD_CASHFLOW_FIELD,
    FINAL_CUMULATIVE_ROR_PERCENT_FIELD,
    LONG_CUM_ROR_PERCENT_FIELD,
    LONG_SHORT_FIELD,
    METRIC_BASIS_GROSS,
    METRIC_BASIS_NET,
    MGMT_FEES_FIELD,
    NCTRL_1_FIELD,
    NCTRL_2_FIELD,
    NCTRL_3_FIELD,
    NCTRL_4_FIELD,
    NIP_FIELD,
    PERF_DATE_FIELD,
    PERF_RESET_FIELD,
    PERIOD_TYPE_EXPLICIT,
    PERIOD_TYPE_MTD,
    PERIOD_TYPE_QTD,
    PERIOD_TYPE_YTD,
    SHORT_CUM_ROR_PERCENT_FIELD,
    TEMP_LONG_CUM_ROR_PERCENT_FIELD,
    TEMP_SHORT_CUM_ROR_PERCENT_FIELD,
)
from app.core.exceptions import CalculationLogicError, InvalidInputDataError, MissingConfigurationError

logger = logging.getLogger(__name__)


class PortfolioPerformanceCalculator:
    def __init__(self, config):
        logger.info("Initializing PortfolioPerformanceCalculator with config: %s", config)
        if not config:
            logger.error("Calculator configuration is empty.")
            raise MissingConfigurationError("Calculator configuration cannot be empty.")

        self.settings = get_settings()
        getcontext().prec = self.settings.decimal_precision
        logger.debug("Decimal precision set to: %s", getcontext().prec)

        self.performance_start_date = self._parse_date(config.get("performance_start_date"))
        if not self.performance_start_date:
            logger.error("'performance_start_date' is missing in calculator config.")
            raise MissingConfigurationError("'performance_start_date' is required in calculator config.")
        logger.info("Performance start date: %s", self.performance_start_date)

        self.metric_basis = config.get("metric_basis")
        if self.metric_basis not in [METRIC_BASIS_NET, METRIC_BASIS_GROSS]:
            logger.error("Invalid 'metric_basis': %s", self.metric_basis)
            raise InvalidInputDataError(
                f"Invalid 'metric_basis': {self.metric_basis}. Must be '{METRIC_BASIS_NET}' or '{METRIC_BASIS_GROSS}'."
            )
        logger.info("Metric basis: %s", self.metric_basis)

        self.period_type = config.get("period_type", PERIOD_TYPE_EXPLICIT)
        if self.period_type not in [PERIOD_TYPE_MTD, PERIOD_TYPE_QTD, PERIOD_TYPE_YTD, PERIOD_TYPE_EXPLICIT]:
            logger.error("Invalid 'period_type': %s", self.period_type)
            raise InvalidInputDataError(
                f"Invalid 'period_type': {self.period_type}. Must be '{PERIOD_TYPE_MTD}', '{PERIOD_TYPE_QTD}', '{PERIOD_TYPE_YTD}', or '{PERIOD_TYPE_EXPLICIT}'."
            )
        logger.info("Period type: %s", self.period_type)

        self.report_start_date = self._parse_date(config.get("report_start_date"))
        self.report_end_date = self._parse_date(config.get("report_end_date"))
        if not self.report_end_date:
            logger.error("'report_end_date' is missing in calculator config.")
            raise MissingConfigurationError("'report_end_date' is required in calculator config.")
        logger.info("Report start date: %s, Report end date: %s", self.report_start_date, self.report_end_date)

        if self.performance_start_date > self.report_end_date:
            logger.error(
                "'performance_start_date' (%s) cannot be after 'report_end_date' (%s).",
                self.performance_start_date,
                self.report_end_date,
            )
            raise InvalidInputDataError("'performance_start_date' must not be after 'report_end_date'.")

    def _parse_date(self, date_val):
        if isinstance(date_val, date):
            return date_val
        elif isinstance(date_val, str):
            try:
                parsed_date = datetime.strptime(date_val, "%Y-%m-%d").date()
                return parsed_date
            except ValueError:
                logger.warning("Could not parse date string: %s", date_val)
                return None
        elif pd.isna(date_val) if isinstance(date_val, (pd.Timestamp, float)) else False:
            return None
        return None

    def _get_sign(self, value):
        if value > 0:
            return Decimal(1)
        elif value < 0:
            return Decimal(-1)
        else:
            return Decimal(0)

    def _is_eomonth(self, date_obj):
        return date_obj.day == calendar.monthrange(date_obj.year, date_obj.month)[1]

    def _get_start_of_quarter(self, date_obj):
        quarter_month = (date_obj.month - 1) // 3 * 3 + 1
        return date(date_obj.year, quarter_month, 1)

    def _parse_decimal(self, value):
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, SystemError):
            logger.warning("Could not parse value to Decimal: %s", value)
            return Decimal(0)

    # Vectorized NIP calculation
    def _calculate_nip_vectorized(self, df):
        cond1 = (
            df[BEGIN_MARKET_VALUE_FIELD] + df[BOD_CASHFLOW_FIELD] + df[END_MARKET_VALUE_FIELD] + df[EOD_CASHFLOW_FIELD]
            == 0
        ) & (df[EOD_CASHFLOW_FIELD] == df[BOD_CASHFLOW_FIELD].apply(self._get_sign))

        cond2 = (df[EOD_CASHFLOW_FIELD] + df[END_MARKET_VALUE_FIELD] == 0) & (df[EOD_CASHFLOW_FIELD] != 0)

        return (cond1 | cond2).astype(int)

    def _calculate_daily_ror_vectorized(self, df, effective_start_date_series):
        """
        Vectorized calculation of 'daily ror %'.
        Returns 0 if the current performance date is before the effective start date of the period.
        """
        daily_ror = pd.Series([Decimal(0)] * len(df), index=df.index, dtype=object)

        condition = (df[PERF_DATE_FIELD] >= effective_start_date_series) & (
            df[BEGIN_MARKET_VALUE_FIELD] + df[BOD_CASHFLOW_FIELD] != 0
        )

        numerator = (
            df[END_MARKET_VALUE_FIELD] - df[BOD_CASHFLOW_FIELD] - df[BEGIN_MARKET_VALUE_FIELD] - df[EOD_CASHFLOW_FIELD]
        )
        if self.metric_basis == METRIC_BASIS_NET:
            numerator += df[MGMT_FEES_FIELD]

        denominator = abs(df[BEGIN_MARKET_VALUE_FIELD] + df[BOD_CASHFLOW_FIELD])

        ror_calc = (numerator / denominator * 100).where(denominator != 0, Decimal(0))

        daily_ror = daily_ror.mask(condition, ror_calc)

        return daily_ror

    def _calculate_sign(self, current_day, val_for_sign, prev_day_calculated):
        """
        Calculates 'sign' for the current row. This function determines the initial sign and updates it based on certain conditions
        from the previous day, mimicking Excel's behavior.
        """
        if current_day == 1:
            return self._get_sign(val_for_sign)
        elif prev_day_calculated is not None:
            prev_sign = self._parse_decimal(prev_day_calculated["sign"])
            prev_eod_cf = self._parse_decimal(prev_day_calculated[EOD_CASHFLOW_FIELD])
            prev_perf_reset = self._parse_decimal(prev_day_calculated[PERF_RESET_FIELD])
            current_bod_cf_for_sign_check = self._parse_decimal(prev_day_calculated[BOD_CASHFLOW_FIELD])

            current_sign_val = self._get_sign(val_for_sign)
            if current_sign_val != prev_sign:
                if current_bod_cf_for_sign_check != 0 or prev_eod_cf != 0 or prev_sign == 0 or prev_perf_reset == 1:
                    return current_sign_val
                else:
                    return prev_sign
            else:
                return prev_sign
        return self._get_sign(val_for_sign)

    def _calculate_temp_long_cum_ror(
        self,
        current_sign,
        current_daily_ror,
        current_perf_date,
        prev_day_calculated,
        current_bmv_bcf_sign,
        effective_period_start_date,
    ):
        """Calculates 'Temp Long Cum Ror %' for the current row, resetting at effective_period_start_date."""

        if current_perf_date == effective_period_start_date:
            return current_daily_ror
        elif current_sign == 1:
            if prev_day_calculated is not None:
                prev_long_cum_ror_final = self._parse_decimal(prev_day_calculated[LONG_CUM_ROR_PERCENT_FIELD])

                if current_daily_ror == 0:
                    return prev_long_cum_ror_final
                else:
                    calc_val = (
                        (Decimal(1) + prev_long_cum_ror_final / 100)
                        * (Decimal(1) + current_daily_ror / 100 * current_bmv_bcf_sign)
                        - Decimal(1)
                    ) * 100
                    return calc_val
        return Decimal(0)

    def _calculate_temp_short_cum_ror(
        self,
        current_sign,
        current_daily_ror,
        current_perf_date,
        prev_day_calculated,
        current_bmv_bcf_sign,
        effective_period_start_date,
    ):
        """Calculates 'Temp short Cum RoR %' for the current row, resetting at effective_period_start_date."""

        if current_perf_date == effective_period_start_date:
            return current_daily_ror
        elif current_sign != 1:  # Short positions logic
            if prev_day_calculated is not None:
                prev_short_cum_ror_final = self._parse_decimal(prev_day_calculated[SHORT_CUM_ROR_PERCENT_FIELD])

                if current_daily_ror == 0:
                    return prev_short_cum_ror_final
                else:
                    calc_val = (
                        (Decimal(1) + prev_short_cum_ror_final / 100)
                        * (Decimal(1) + current_daily_ror / 100 * current_bmv_bcf_sign)
                        - Decimal(1)
                    ) * 100
                    return calc_val
        return Decimal(0)

    def _calculate_nctrls(
        self,
        current_temp_long_cum_ror,
        current_temp_short_cum_ror,
        current_bod_cf,
        current_eod_cf,
        current_perf_date,
        next_day_data,
        report_end_date,
    ):
        """Calculates NCTRL 1-3 for the current row."""
        next_bod_cf_val = (
            self._parse_decimal(next_day_data.get(BOD_CASHFLOW_FIELD, 0)) if next_day_data is not None else Decimal(0)
        )
        next_date_val_raw = next_day_data.get(PERF_DATE_FIELD) if next_day_data is not None else None

        next_date_beyond_period = False
        if next_date_val_raw is not None and report_end_date is not None:
            try:
                next_date_val = pd.to_datetime(next_date_val_raw, errors="coerce").date()
            except Exception:
                if isinstance(next_date_val_raw, date):
                    next_date_val = next_date_val_raw
                else:
                    next_date_val = None

            if next_date_val is not None:
                next_date_beyond_period = next_date_val > report_end_date

        cond_nctrl_common = (
            current_bod_cf != 0
            or next_bod_cf_val != 0
            or current_eod_cf != 0
            or self._is_eomonth(current_perf_date)
            or next_date_beyond_period
        )

        nctrl1 = 1 if (current_temp_long_cum_ror < -100 and cond_nctrl_common) else 0
        nctrl2 = 1 if (current_temp_short_cum_ror > 100 and cond_nctrl_common) else 0
        nctrl3 = (
            1 if (current_temp_short_cum_ror < -100 and current_temp_long_cum_ror != 0 and cond_nctrl_common) else 0
        )

        return nctrl1, nctrl2, nctrl3

    def _calculate_perf_reset(self, nctrl1, nctrl2, nctrl3, nctrl4):
        """Calculates 'Perf Reset' for the current row."""
        return 1 if (nctrl1 == 1 or nctrl2 == 1 or nctrl3 == 1 or nctrl4 == 1) else 0

    def _calculate_long_short_cum_ror_final(
        self,
        current_nip,
        current_perf_reset,
        current_temp_long_cum_ror,
        current_temp_short_cum_ror,
        current_bod_cf,
        prev_day_calculated,
        next_day_data,
        effective_period_start_date,
        current_perf_date,
    ):
        """Calculates 'Long Cum Ror %' and 'Short Cum RoR %' for the current row."""
        prev_long_cum_ror_final = (
            self._parse_decimal(prev_day_calculated[LONG_CUM_ROR_PERCENT_FIELD])
            if prev_day_calculated is not None
            else Decimal(0)
        )
        prev_short_cum_ror_final = (
            self._parse_decimal(prev_day_calculated[SHORT_CUM_ROR_PERCENT_FIELD])
            if prev_day_calculated is not None
            else Decimal(0)
        )
        prev_nip = (
            self._parse_decimal(prev_day_calculated[NIP_FIELD]) if prev_day_calculated is not None else Decimal(0)
        )

        next_nip_val = self._parse_decimal(next_day_data.get(NIP_FIELD, 0)) if next_day_data is not None else Decimal(0)
        next_bod_cf_val = (
            self._parse_decimal(next_day_data.get(BOD_CASHFLOW_FIELD, 0)) if next_day_data is not None else Decimal(0)
        )

        lookahead_reset_cond = False
        if next_day_data is not None:
            if (
                next_nip_val == 0
                and next_bod_cf_val != 0
                and (current_temp_long_cum_ror <= Decimal(-100) or current_temp_short_cum_ror >= Decimal(100))
            ):
                lookahead_reset_cond = True

        is_current_date_period_start = current_perf_date == effective_period_start_date

        if current_nip == 1:
            if is_current_date_period_start or lookahead_reset_cond:
                return Decimal(0), Decimal(0)
            else:
                return prev_long_cum_ror_final, prev_short_cum_ror_final

        else:
            reset_if_prev_nip_active_and_no_cf = False
            if prev_day_calculated is not None:
                if (
                    prev_nip == 1
                    and current_bod_cf == 0
                    and (prev_long_cum_ror_final <= Decimal(-100) or prev_short_cum_ror_final >= Decimal(100))
                ):
                    reset_if_prev_nip_active_and_no_cf = True

            if reset_if_prev_nip_active_and_no_cf:
                return Decimal(0), Decimal(0)
            elif is_current_date_period_start:
                return current_temp_long_cum_ror, current_temp_short_cum_ror
            else:
                return current_temp_long_cum_ror, current_temp_short_cum_ror  # Corrected variable names here

    def calculate_performance(self, daily_data_list, config):
        """
        Calculates portfolio performance based on daily data.
        :param daily_data_list: List of dictionaries, each representing a day's data.
        :param config: Dictionary containing additional configuration.
        :return: List of dictionaries with all calculated performance metrics.
        """
        if not daily_data_list:
            raise InvalidInputDataError("Daily data list cannot be empty.")

        try:
            df = pd.DataFrame(daily_data_list)
        except Exception as e:
            raise InvalidInputDataError(f"Failed to create DataFrame from daily data: {e}")

        numeric_cols_to_parse = [
            "Day",
            BEGIN_MARKET_VALUE_FIELD,
            BOD_CASHFLOW_FIELD,
            EOD_CASHFLOW_FIELD,
            MGMT_FEES_FIELD,
            END_MARKET_VALUE_FIELD,
        ]
        for col in numeric_cols_to_parse:
            if col in df.columns:
                df[col] = df[col].apply(self._parse_decimal)

        df[PERF_DATE_FIELD] = pd.to_datetime(df[PERF_DATE_FIELD], errors="coerce").dt.date
        if df[PERF_DATE_FIELD].isnull().any():
            raise InvalidInputDataError("One or more 'Perf. Date' values are invalid or missing.")

        overall_effective_report_start_date = self.performance_start_date
        if self.report_start_date:
            overall_effective_report_start_date = max(self.performance_start_date, self.report_start_date)

        if self.report_end_date:
            temp_report_end_date = self.report_end_date
            df = df[df[PERF_DATE_FIELD] <= temp_report_end_date].copy()

        # Handle case where filtering by report_end_date results in an empty DataFrame
        if df.empty:
            return []

        cols_to_init = [
            "sign",
            DAILY_ROR_PERCENT_FIELD,
            TEMP_LONG_CUM_ROR_PERCENT_FIELD,
            TEMP_SHORT_CUM_ROR_PERCENT_FIELD,
            LONG_CUM_ROR_PERCENT_FIELD,
            SHORT_CUM_ROR_PERCENT_FIELD,
            FINAL_CUMULATIVE_ROR_PERCENT_FIELD,
        ]
        for col in cols_to_init:
            df[col] = Decimal(0)

        df[NCTRL_1_FIELD] = 0
        df[NCTRL_2_FIELD] = 0
        df[NCTRL_3_FIELD] = 0
        df[NCTRL_4_FIELD] = 0
        df[PERF_RESET_FIELD] = 0
        df[NIP_FIELD] = 0
        df[LONG_SHORT_FIELD] = ""

        # Vectorized NIP calculation
        df[NIP_FIELD] = self._calculate_nip_vectorized(df)

        # --- Vectorized Daily ROR Calculation --- #
        def get_effective_period_start_date_for_row(row_date, period_type, performance_start_date, report_start_date):
            if pd.isna(row_date):
                return pd.NaT

            effective_date = performance_start_date
            if period_type == PERIOD_TYPE_MTD:
                effective_date = date(row_date.year, row_date.month, 1)
            elif period_type == PERIOD_TYPE_QTD:
                quarter_month = (row_date.month - 1) // 3 * 3 + 1
                effective_date = date(row_date.year, quarter_month, 1)
            elif period_type == PERIOD_TYPE_YTD:
                effective_date = date(row_date.year, 1, 1)
            elif period_type == PERIOD_TYPE_EXPLICIT:
                effective_date = max(
                    performance_start_date, report_start_date if report_start_date else performance_start_date
                )
            else:
                effective_date = performance_start_date

            return max(effective_date, performance_start_date)

        df["effective_period_start_date"] = df[PERF_DATE_FIELD].apply(
            lambda x: get_effective_period_start_date_for_row(
                x, self.period_type, self.performance_start_date, self.report_start_date
            )
        )

        df[DAILY_ROR_PERCENT_FIELD] = self._calculate_daily_ror_vectorized(df, df["effective_period_start_date"])

        # --- Iterative Calculations (if strict row-by-row dependency remains) ---
        # The following calculations remain in a loop due to their complex dependencies on
        # previously calculated rows' *final* values, or lookahead conditions that are
        # challenging to vectorize directly without altering the Excel logic's behavior.
        # This approach provides significant performance gains where possible while
        # maintaining correctness for complex iterative logic.
        try:
            for i in range(len(df)):
                current_data = df.iloc[i]
                current_day = current_data["Day"]
                current_perf_date = current_data[PERF_DATE_FIELD]
                current_begin_mv = current_data[BEGIN_MARKET_VALUE_FIELD]
                current_bod_cf = current_data[BOD_CASHFLOW_FIELD]
                current_eod_cf = current_data[EOD_CASHFLOW_FIELD]
                current_mgmt_fees = current_data[MGMT_FEES_FIELD]
                current_end_mv = current_data[END_MARKET_VALUE_FIELD]
                current_nip = current_data[NIP_FIELD]

                prev_day_calculated = df.iloc[i - 1] if i > 0 else None
                next_day_data = df.iloc[i + 1].to_dict() if i + 1 < len(df) else None

                effective_period_start_date = current_data["effective_period_start_date"]

                if pd.isna(current_perf_date):
                    continue

                val_for_sign = current_begin_mv + current_bod_cf
                df.at[df.index[i], "sign"] = self._calculate_sign(current_day, val_for_sign, prev_day_calculated)
                current_sign = df.at[df.index[i], "sign"]

                current_daily_ror = df.at[df.index[i], DAILY_ROR_PERCENT_FIELD]

                if current_perf_date < overall_effective_report_start_date:
                    df.at[df.index[i], TEMP_LONG_CUM_ROR_PERCENT_FIELD] = Decimal(0)
                    df.at[df.index[i], TEMP_SHORT_CUM_ROR_PERCENT_FIELD] = Decimal(0)
                    df.at[df.index[i], LONG_CUM_ROR_PERCENT_FIELD] = Decimal(0)
                    df.at[df.index[i], SHORT_CUM_ROR_PERCENT_FIELD] = Decimal(0)
                    df.at[df.index[i], FINAL_CUMULATIVE_ROR_PERCENT_FIELD] = Decimal(0)
                    df.at[df.index[i], NCTRL_1_FIELD] = 0
                    df.at[df.index[i], NCTRL_2_FIELD] = 0
                    df.at[df.index[i], NCTRL_3_FIELD] = 0
                    df.at[df.index[i], NCTRL_4_FIELD] = 0
                    df.at[df.index[i], PERF_RESET_FIELD] = 0
                    continue

                df.at[df.index[i], TEMP_LONG_CUM_ROR_PERCENT_FIELD] = self._calculate_temp_long_cum_ror(
                    current_sign,
                    current_daily_ror,
                    current_perf_date,
                    prev_day_calculated,
                    current_sign,
                    effective_period_start_date,
                )
                current_temp_long_cum_ror = df.at[df.index[i], TEMP_LONG_CUM_ROR_PERCENT_FIELD]

                df.at[df.index[i], TEMP_SHORT_CUM_ROR_PERCENT_FIELD] = self._calculate_temp_short_cum_ror(
                    current_sign,
                    current_daily_ror,
                    current_perf_date,
                    prev_day_calculated,
                    current_sign,
                    effective_period_start_date,
                )
                current_temp_short_cum_ror = df.at[df.index[i], TEMP_SHORT_CUM_ROR_PERCENT_FIELD]

                nctrl1, nctrl2, nctrl3 = self._calculate_nctrls(
                    current_temp_long_cum_ror,
                    current_temp_short_cum_ror,
                    current_bod_cf,
                    current_eod_cf,
                    current_perf_date,
                    next_day_data,
                    self.report_end_date,
                )
                df.at[df.index[i], NCTRL_1_FIELD] = nctrl1
                df.at[df.index[i], NCTRL_2_FIELD] = nctrl2
                df.at[df.index[i], NCTRL_3_FIELD] = nctrl3

                cond_n4 = False
                if prev_day_calculated is not None:
                    prev_temp_long_cum_ror_temp = self._parse_decimal(
                        prev_day_calculated[TEMP_LONG_CUM_ROR_PERCENT_FIELD]
                    )
                    prev_temp_short_cum_ror_temp = self._parse_decimal(
                        prev_day_calculated[TEMP_SHORT_CUM_ROR_PERCENT_FIELD]
                    )
                    prev_eod_cf_val = self._parse_decimal(prev_day_calculated[EOD_CASHFLOW_FIELD])

                    if (
                        prev_temp_long_cum_ror_temp <= Decimal(-100) or prev_temp_short_cum_ror_temp >= Decimal(100)
                    ) and (current_bod_cf != 0 or prev_eod_cf_val != 0):
                        cond_n4 = True
                df.at[df.index[i], NCTRL_4_FIELD] = 1 if cond_n4 else 0
                current_nctrl4 = df.at[df.index[i], NCTRL_4_FIELD]

                df.at[df.index[i], PERF_RESET_FIELD] = self._calculate_perf_reset(
                    nctrl1, nctrl2, nctrl3, current_nctrl4
                )
                current_perf_reset = df.at[df.index[i], PERF_RESET_FIELD]

                long_cum_ror, short_cum_ror = self._calculate_long_short_cum_ror_final(
                    current_nip,
                    current_perf_reset,
                    current_temp_long_cum_ror,
                    current_temp_short_cum_ror,
                    current_bod_cf,
                    prev_day_calculated,
                    next_day_data,
                    effective_period_start_date,
                    current_perf_date,
                )
                df.at[df.index[i], LONG_CUM_ROR_PERCENT_FIELD] = long_cum_ror
                df.at[df.index[i], SHORT_CUM_ROR_PERCENT_FIELD] = short_cum_ror
                current_long_cum_ror_final = df.at[df.index[i], LONG_CUM_ROR_PERCENT_FIELD]
                current_short_cum_ror_final = df.at[df.index[i], SHORT_CUM_ROR_PERCENT_FIELD]

                df.at[df.index[i], LONG_SHORT_FIELD] = "S" if current_sign == -1 else "L"

                df.at[df.index[i], FINAL_CUMULATIVE_ROR_PERCENT_FIELD] = (
                    (Decimal(1) + current_long_cum_ror_final / 100) * (Decimal(1) + current_short_cum_ror_final / 100)
                    - Decimal(1)
                ) * 100
                logger.debug(
                    "Row %d: Final Cumulative ROR: %s", i, df.at[df.index[i], FINAL_CUMULATIVE_ROR_PERCENT_FIELD]
                )
        except Exception as e:
            logger.exception("Error during iterative calculation loop.")
            raise CalculationLogicError(f"Error during iterative calculation loop: {e}")

        # Remove the temporary column used for vectorized period start dates
        df.drop(columns=["effective_period_start_date"], inplace=True)

        final_df = df[df[PERF_DATE_FIELD] >= overall_effective_report_start_date].copy()

        # Convert Decimal columns to float for JSON serialization
        for col in final_df.columns:
            if (
                final_df[col].dtype == object
                and len(final_df) > 0
                and any(isinstance(x, Decimal) for x in final_df[col])
            ):
                final_df[col] = final_df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

        # Convert 'Perf. Date' column back to string format for JSON response
        final_df[PERF_DATE_FIELD] = final_df[PERF_DATE_FIELD].apply(
            lambda x: x.strftime("%Y-%m-%d") if isinstance(x, date) else x
        )
        logger.info("Performance calculation complete. Returning results.")
        return final_df.to_dict(orient="records")

    def get_summary_performance(self, calculated_results):
        if not calculated_results:
            return {
                "report_start_date": self.report_start_date.strftime("%Y-%m-%d") if self.report_start_date else None,
                "report_end_date": self.report_end_date.strftime("%Y-%m-%d"),
                BEGIN_MARKET_VALUE_FIELD: 0.0,
                BOD_CASHFLOW_FIELD: 0.0,
                EOD_CASHFLOW_FIELD: 0.0,
                MGMT_FEES_FIELD: 0.0,
                END_MARKET_VALUE_FIELD: 0.0,
                FINAL_CUMULATIVE_ROR_PERCENT_FIELD: 0.0,
                NCTRL_1_FIELD: 0,
                NCTRL_2_FIELD: 0,
                NCTRL_3_FIELD: 0,
                NCTRL_4_FIELD: 0,
                PERF_RESET_FIELD: 0,
                NIP_FIELD: 0,
            }

        try:
            first_day = next(
                (
                    day
                    for day in calculated_results
                    if date.fromisoformat(day[PERF_DATE_FIELD]) >= (self.report_start_date or date.min)
                ),
                None,
            )
            last_day = next(
                (
                    day
                    for day in reversed(calculated_results)
                    if date.fromisoformat(day[PERF_DATE_FIELD]) <= self.report_end_date
                ),
                None,
            )

            if not first_day or not last_day:
                raise ValueError("No data in report range.")

            summary = {
                "report_start_date": self.report_start_date.strftime("%Y-%m-%d") if self.report_start_date else None,
                "report_end_date": self.report_end_date.strftime("%Y-%m-%d"),
                BEGIN_MARKET_VALUE_FIELD: first_day.get(BEGIN_MARKET_VALUE_FIELD, 0.0),
                END_MARKET_VALUE_FIELD: last_day.get(END_MARKET_VALUE_FIELD, 0.0),
                BOD_CASHFLOW_FIELD: 0.0,
                EOD_CASHFLOW_FIELD: 0.0,
                MGMT_FEES_FIELD: 0.0,
                FINAL_CUMULATIVE_ROR_PERCENT_FIELD: last_day.get(FINAL_CUMULATIVE_ROR_PERCENT_FIELD, 0.0),
                NCTRL_1_FIELD: 0,
                NCTRL_2_FIELD: 0,
                NCTRL_3_FIELD: 0,
                NCTRL_4_FIELD: 0,
                PERF_RESET_FIELD: 0,
                NIP_FIELD: 0,
            }

            for day in calculated_results:
                d = date.fromisoformat(day[PERF_DATE_FIELD])
                if self.report_start_date and d < self.report_start_date:
                    continue
                if d > self.report_end_date:
                    continue

                summary[BOD_CASHFLOW_FIELD] += day.get(BOD_CASHFLOW_FIELD, 0.0)
                summary[EOD_CASHFLOW_FIELD] += day.get(EOD_CASHFLOW_FIELD, 0.0)
                summary[MGMT_FEES_FIELD] += day.get(MGMT_FEES_FIELD, 0.0)

                for ctrl_field in [
                    NCTRL_1_FIELD,
                    NCTRL_2_FIELD,
                    NCTRL_3_FIELD,
                    NCTRL_4_FIELD,
                    PERF_RESET_FIELD,
                    NIP_FIELD,
                ]:
                    if day.get(ctrl_field) == 1:
                        summary[ctrl_field] = 1

            return summary
        except Exception as e:
            logger.exception("Failed to calculate summary performance: %s", e)
            return {
                "report_start_date": self.report_start_date.strftime("%Y-%m-%d") if self.report_start_date else None,
                "report_end_date": self.report_end_date.strftime("%Y-%m-%d"),
                BEGIN_MARKET_VALUE_FIELD: 0.0,
                BOD_CASHFLOW_FIELD: 0.0,
                EOD_CASHFLOW_FIELD: 0.0,
                MGMT_FEES_FIELD: 0.0,
                END_MARKET_VALUE_FIELD: 0.0,
                FINAL_CUMULATIVE_ROR_PERCENT_FIELD: 0.0,
                NCTRL_1_FIELD: 0,
                NCTRL_2_FIELD: 0,
                NCTRL_3_FIELD: 0,
                NCTRL_4_FIELD: 0,
                PERF_RESET_FIELD: 0,
                NIP_FIELD: 0,
            }
