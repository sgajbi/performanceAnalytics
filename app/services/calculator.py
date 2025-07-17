import pandas as pd
from datetime import datetime, date
from decimal import Decimal, getcontext
import calendar

# Set global precision for Decimal calculations
getcontext().prec = 28

class PortfolioPerformanceCalculator:
    def __init__(self, config):
        """
        Initializes the calculator with global configuration parameters.
        :param config: Dictionary containing 'performance_start_date', 'metric_basis', 'period_type',
                       'report_start_date', 'report_end_date'.
        """
        self.performance_start_date = datetime.strptime(config["performance_start_date"], "%Y-%m-%d").date()
        self.metric_basis = config["metric_basis"] # "NET" or "GROSS"
        self.period_type = config.get("period_type", "Explicit") # "MTD", "QTD", "YTD", "Explicit"
        # report_start_date and report_end_date are now directly used from config,
        # and made optional by checking for their existence.
        self.report_start_date = datetime.strptime(config["report_start_date"], "%Y-%m-%d").date() if "report_start_date" in config and config["report_start_date"] else None
        self.report_end_date = datetime.strptime(config["report_end_date"], "%Y-%m-%d").date() if "report_end_date" in config and config["report_end_date"] else None

    def _get_sign(self, value):
        """Replicates Excel's SIGN function for Decimal values."""
        if value > 0:
            return Decimal(1)
        elif value < 0:
            return Decimal(-1)
        else:
            return Decimal(0)

    def _is_eomonth(self, date_obj):
        """Checks if a given date is the end of its month."""
        return date_obj.day == calendar.monthrange(date_obj.year, date_obj.month)[1]

    def _get_start_of_quarter(self, date_obj):
        """Returns the first day of the quarter for a given date."""
        quarter_month = (date_obj.month - 1) // 3 * 3 + 1
        return date(date_obj.year, quarter_month, 1)

    def _parse_decimal(self, value):
        """Helper to safely parse values to Decimal, handling potential non-numeric inputs."""
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return Decimal(0)

    def _calculate_nip(self, current_data):
        """Calculates NIP for a single row based on the corrected formula."""
        current_begin_mv = self._parse_decimal(current_data['Begin Market Value'])
        current_bod_cf = self._parse_decimal(current_data['BOD Cashflow'])
        current_eod_cf = self._parse_decimal(current_data['Eod Cashflow'])
        current_end_mv = self._parse_decimal(current_data['End Market Value'])

        # First condition: AND(cur_BMV+cur_BCF+curr_EMV+curr_ECF=0,curr_ECF=SIGN(cur_BCF))
        if (current_begin_mv + current_bod_cf + current_end_mv + current_eod_cf == 0) and \
           (current_eod_cf == self._get_sign(current_bod_cf)):
            return 1
        # Second condition (corrected): AND(curr_ECF+curr_EMV=0,curr_ECF<>0)
        elif (current_eod_cf + current_end_mv == 0) and current_eod_cf != 0:
            return 1
        else:
            return 0

    def _calculate_sign(self, current_day, val_for_sign, prev_day_calculated):
        """
        Calculates 'sign' for the current row.
        This function determines the initial sign and updates it based on certain conditions
        from the previous day, mimicking Excel's behavior.
        """
        if current_day == 1: # Represents the very first row of the entire input dataset
            return self._get_sign(val_for_sign)
        elif prev_day_calculated is not None:
            prev_sign = self._parse_decimal(prev_day_calculated['sign'])
            prev_eod_cf = self._parse_decimal(prev_day_calculated['Eod Cashflow'])
            prev_perf_reset = self._parse_decimal(prev_day_calculated['Perf Reset'])
            current_bod_cf_for_sign_check = self._parse_decimal(prev_day_calculated['BOD Cashflow'])

            current_sign_val = self._get_sign(val_for_sign)
            if current_sign_val != prev_sign:
                if current_bod_cf_for_sign_check != 0 or prev_eod_cf != 0 or prev_sign == 0 or prev_perf_reset == 1:
                    return current_sign_val
                else:
                    return prev_sign
            else:
                return prev_sign
        return self._get_sign(val_for_sign) # Fallback, should generally be covered by above


    def _calculate_daily_ror(self, current_perf_date, current_begin_mv,
                             current_bod_cf, current_end_mv, current_eod_cf, current_mgmt_fees,
                             effective_start_date):
        """
        Calculates 'daily ror %' for the current row.
        Returns 0 if the current performance date is before the effective start date of the period.
        """
        if current_perf_date < effective_start_date:
            return Decimal(0)
        elif (current_begin_mv + current_bod_cf) == 0:
            return Decimal(0)
        else:
            mgmt_fee_deduction = Decimal(0)
            if self.metric_basis == "NET":
                mgmt_fee_deduction = current_mgmt_fees

            numerator = current_end_mv - current_bod_cf - current_begin_mv - (current_eod_cf - mgmt_fee_deduction)
            denominator = abs(current_begin_mv + current_bod_cf)

            return (numerator / denominator * 100) if denominator != 0 else Decimal(0)

    def _calculate_temp_long_cum_ror(self, current_sign, current_daily_ror, current_perf_date, prev_day_calculated, current_bmv_bcf_sign, effective_period_start_date):
        """Calculates 'Temp Long Cum Ror %' for the current row, resetting at effective_period_start_date."""

        if current_perf_date == effective_period_start_date:
            # If it's the start of the effective period, the temp cum ROR starts with the daily ROR of that day
            return current_daily_ror
        elif current_sign == 1:
            if prev_day_calculated is not None:
                # Use the final Long Cum Ror from the previous day for compounding
                prev_long_cum_ror_final = self._parse_decimal(prev_day_calculated['Long Cum Ror %'])

                if current_daily_ror == 0:
                    return prev_long_cum_ror_final
                else:
                    # Compounding formula: (1 + R_prev) * (1 + R_daily) - 1
                    calc_val = ((Decimal(1) + prev_long_cum_ror_final/100) * \
                                (Decimal(1) + current_daily_ror/100 * current_bmv_bcf_sign) - Decimal(1)) * 100
                    return calc_val
        # If current_sign is not 1, or if it's not the effective start and no previous data, return 0
        return Decimal(0)


    def _calculate_temp_short_cum_ror(self, current_sign, current_daily_ror, current_perf_date, prev_day_calculated, current_bmv_bcf_sign, effective_period_start_date):
        """Calculates 'Temp short Cum RoR %' for the current row, resetting at effective_period_start_date."""

        if current_perf_date == effective_period_start_date:
            # If it's the start of the effective period, the temp cum ROR starts with the daily ROR of that day
            return current_daily_ror
        elif current_sign != 1: # Short positions logic
            if prev_day_calculated is not None:
                # Use the final Short Cum RoR from the previous day for compounding
                prev_short_cum_ror_final = self._parse_decimal(prev_day_calculated['Short Cum RoR %'])

                if current_daily_ror == 0:
                    return prev_short_cum_ror_final
                else:
                    # Compounding formula for short returns: (1 - R_prev) * (1 + R_daily) - 1.
                    # The Excel equivalent uses (1 - prev_short_cum_ror_final / 100)
                    # and (1 + current_daily_ror / 100 * current_bmv_bcf_sign).
                    term_inside = (Decimal(1) + prev_short_cum_ror_final / Decimal(-100)) * \
                                  (Decimal(1) + current_daily_ror / 100 * current_bmv_bcf_sign) - Decimal(1)
                    calc_val = (term_inside - Decimal(1)) * 100 # Additional -1 for short calculation based on Excel

                    return calc_val
        # If current_sign is 1, or if it's not the effective start and no previous data, return 0
        return Decimal(0)

    def _calculate_nctrls(self, current_temp_long_cum_ror, current_temp_short_cum_ror,
                          current_bod_cf, current_eod_cf, current_perf_date, next_day_data, report_end_date):
        """Calculates NCTRL 1-3 for the current row."""
        next_bod_cf_val = self._parse_decimal(next_day_data.get('BOD Cashflow', 0)) if next_day_data is not None else Decimal(0)
        next_date_val = next_day_data.get('Perf. Date') if next_day_data is not None else None

        next_date_beyond_period = False
        if next_date_val is not None and report_end_date is not None:
            next_date_beyond_period = next_date_val > report_end_date


        cond_nctrl_common = current_bod_cf != 0 or next_bod_cf_val != 0 or current_eod_cf != 0 or \
                            self._is_eomonth(current_perf_date) or next_date_beyond_period

        nctrl1 = 1 if (current_temp_long_cum_ror < -100 and cond_nctrl_common) else 0
        nctrl2 = 1 if (current_temp_short_cum_ror > 100 and cond_nctrl_common) else 0
        nctrl3 = 1 if (current_temp_short_cum_ror < -100 and current_temp_long_cum_ror != 0 and cond_nctrl_common) else 0

        return nctrl1, nctrl2, nctrl3

    def _calculate_perf_reset(self, nctrl1, nctrl2, nctrl3, nctrl4):
        """Calculates 'Perf Reset' for the current row."""
        return 1 if (nctrl1 == 1 or nctrl2 == 1 or nctrl3 == 1 or nctrl4 == 1) else 0

    def _calculate_long_short_cum_ror_final(self, current_nip, current_perf_reset,
                                             current_temp_long_cum_ror, current_temp_short_cum_ror,
                                             current_bod_cf,
                                             prev_day_calculated, next_day_data, effective_period_start_date, current_perf_date):
        """Calculates 'Long Cum Ror %' and 'Short Cum RoR %' for the current row."""
        prev_long_cum_ror_final = self._parse_decimal(prev_day_calculated['Long Cum Ror %']) if prev_day_calculated is not None else Decimal(0)
        prev_short_cum_ror_final = self._parse_decimal(prev_day_calculated['Short Cum RoR %']) if prev_day_calculated is not None else Decimal(0)
        prev_nip = self._parse_decimal(prev_day_calculated['NIP']) if prev_day_calculated is not None else Decimal(0)

        next_nip_val = self._parse_decimal(next_day_data['NIP']) if next_day_data is not None else Decimal(0)
        next_bod_cf_val = self._parse_decimal(next_day_data['BOD Cashflow']) if next_day_data is not None else Decimal(0)


        lookahead_reset_cond = False
        if next_day_data is not None:
            if next_nip_val == 0 and next_bod_cf_val != 0 and \
               (prev_long_cum_ror_final == -100 or prev_short_cum_ror_final == 100):
                lookahead_reset_cond = True

        # Check if the current date IS the effective period start date.
        is_current_date_period_start = (current_perf_date == effective_period_start_date)

        # IF cur_NIP = 1 branch
        if current_nip == 1:
            # If NIP is 1, it generally means a reset/special condition.
            # If it's also a period start or lookahead reset, then reset to 0.
            if is_current_date_period_start or lookahead_reset_cond:
                 return Decimal(0), Decimal(0)
            else: # If NIP=1 but not a period start or lookahead reset, retain previous day's final ROR
                return prev_long_cum_ror_final, prev_short_cum_ror_final
        else: # cur_NIP != 1 branch
            reset_if_prev_nip_active_and_no_cf = False
            if prev_day_calculated is not None:
                if prev_nip == 1 and current_bod_cf == 0 and \
                   (prev_long_cum_ror_final == -100 or prev_short_cum_ror_final == 100):
                    reset_if_prev_nip_active_and_no_cf = True

            if reset_if_prev_nip_active_and_no_cf:
                return Decimal(0), Decimal(0)
            elif is_current_date_period_start: # If not NIP=1 special reset, but it is a period start
                # When it's the effective start date, the cumulative ROR should just be the daily ROR for that day.
                # The temp cum ROR calculation already handles this initial value.
                return current_temp_long_cum_ror, current_temp_short_cum_ror
            else: # Normal accumulation (if not a reset point)
                return current_temp_long_cum_ror, current_temp_short_cum_ror

    def calculate_performance(self, daily_data_list, config):
        """
        Calculates portfolio performance based on daily data.
        :param daily_data_list: List of dictionaries, each representing a day's data.
        :param config: Dictionary containing additional configuration.
        :return: List of dictionaries with all calculated performance metrics.
        """
        df = pd.DataFrame(daily_data_list)
        df['Perf. Date'] = pd.to_datetime(df['Perf. Date']).dt.date

        # Determine the overall effective reporting start date based on performance_start_date
        # and report_start_date from config.
        # This will be the earliest date from which we consider data for reporting.
        overall_effective_report_start_date = self.performance_start_date
        if self.report_start_date: # If report_start_date is provided and valid
             overall_effective_report_start_date = max(self.performance_start_date, self.report_start_date)

        # Filter the DataFrame to include only dates within the relevant reporting window
        if self.report_end_date:
            df = df[df['Perf. Date'] <= self.report_end_date].copy()
        # No need to filter by overall_effective_report_start_date here, as individual
        # row calculations will handle returns prior to their effective period start.

        # Initialize columns
        cols_to_init = ['sign', 'daily ror %', 'Temp Long Cum Ror %', 'Temp short Cum RoR %',
                        'Long Cum Ror %', 'Short Cum RoR %', 'Final Cummulative ROR %']
        for col in cols_to_init:
            df[col] = Decimal(0)

        df['NCTRL 1'] = 0
        df['NCTRL 2'] = 0
        df['NCTRL 3'] = 0
        df['NCTRL 4'] = 0
        df['Perf Reset'] = 0
        df['NIP'] = 0
        df['Long /Short'] = ""


        # Pre-calculate NIP for all rows using the corrected formula
        df['NIP'] = df.apply(self._calculate_nip, axis=1)

        # Iterate row by row for cumulative calculations
        # Using iterrows() is fine for smaller DataFrames, for very large ones,
        # vectorized operations are preferred but complex for this logic.
        for i, row in df.iterrows():
            current_day = self._parse_decimal(row['Day'])
            current_perf_date = row['Perf. Date']
            current_begin_mv = self._parse_decimal(row['Begin Market Value'])
            current_bod_cf = self._parse_decimal(row['BOD Cashflow'])
            current_eod_cf = self._parse_decimal(row['Eod Cashflow'])
            current_mgmt_fees = self._parse_decimal(row['Mgmt fees'])
            current_end_mv = self._parse_decimal(row['End Market Value'])
            current_nip = self._parse_decimal(row['NIP'])

            # Safely get previous day's calculated data
            prev_day_calculated = df.loc[i-1] if i > 0 and (i-1) in df.index else None
            next_day_data = df.iloc[i+1] if i + 1 < len(df) else None

            # Determine the effective period start date for the *current row's period calculation*.
            # This is the crucial part for MTD/QTD/YTD/Explicit resetting.
            effective_period_start_date = None
            if self.period_type == "MTD":
                effective_period_start_date = date(current_perf_date.year, current_perf_date.month, 1)
            elif self.period_type == "QTD":
                effective_period_start_date = self._get_start_of_quarter(current_perf_date)
            elif self.period_type == "YTD":
                effective_period_start_date = date(current_perf_date.year, 1, 1)
            elif self.period_type == "Explicit":
                effective_period_start_date = overall_effective_report_start_date # For explicit, it's the max of performance_start_date and report_start_date
            else:
                effective_period_start_date = self.performance_start_date # Fallback, though period_type should be validated

            # Ensure the effective_period_start_date is never before the global performance_start_date
            effective_period_start_date = max(effective_period_start_date, self.performance_start_date)


            # Calculate 'sign' (this is generally not period-dependent but data-dependent)
            val_for_sign = current_begin_mv + current_bod_cf
            df.at[i, 'sign'] = self._calculate_sign(current_day, val_for_sign, prev_day_calculated)
            current_sign = df.at[i, 'sign']


            # Calculate 'daily ror %'
            # If current date is before the determined effective period start, its daily ROR for *this period* is 0.
            df.at[i, 'daily ror %'] = self._calculate_daily_ror(
                current_perf_date, current_begin_mv,
                current_bod_cf, current_end_mv, current_eod_cf, current_mgmt_fees,
                effective_period_start_date
            )
            current_daily_ror = df.at[i, 'daily ror %']

            # If the current date is *before* the overall effective reporting start date,
            # or before the effective period start for its type, then all RORs for this row should be zeroed out.
            # This is to ensure no values from "pre-period" dates show up in the output.
            if current_perf_date < overall_effective_report_start_date:
                df.at[i, 'Temp Long Cum Ror %'] = Decimal(0)
                df.at[i, 'Temp short Cum RoR %'] = Decimal(0)
                df.at[i, 'Long Cum Ror %'] = Decimal(0)
                df.at[i, 'Short Cum RoR %'] = Decimal(0)
                df.at[i, 'Final Cummulative ROR %'] = Decimal(0)
                df.at[i, 'NCTRL 1'] = 0
                df.at[i, 'NCTRL 2'] = 0
                df.at[i, 'NCTRL 3'] = 0
                df.at[i, 'NCTRL 4'] = 0
                df.at[i, 'Perf Reset'] = 0
                # NIP is already pre-calculated based on data, not period, so it remains.
                continue # Skip further calculations for this row as it's outside the reporting window

            # Calculate 'Temp Long Cum Ror %'
            df.at[i, 'Temp Long Cum Ror %'] = self._calculate_temp_long_cum_ror(
                current_sign, current_daily_ror, current_perf_date, prev_day_calculated, current_sign, effective_period_start_date
            )
            current_temp_long_cum_ror = df.at[i, 'Temp Long Cum Ror %']


            # Calculate 'Temp short Cum RoR %'
            df.at[i, 'Temp short Cum RoR %'] = self._calculate_temp_short_cum_ror(
                current_sign, current_daily_ror, current_perf_date, prev_day_calculated, current_sign, effective_period_start_date
            )
            current_temp_short_cum_ror = df.at[i, 'Temp short Cum RoR %']


            # Calculate NCTRL 1-3
            nctrl1, nctrl2, nctrl3 = self._calculate_nctrls(
                current_temp_long_cum_ror, current_temp_short_cum_ror,
                current_bod_cf, current_eod_cf, current_perf_date, next_day_data, self.report_end_date # Use self.report_end_date here
            )
            df.at[i, 'NCTRL 1'] = nctrl1
            df.at[i, 'NCTRL 2'] = nctrl2
            df.at[i, 'NCTRL 3'] = nctrl3

            # Calculate NCTRL 4 (still needs prev_day_calculated access)
            cond_n4 = False
            if prev_day_calculated is not None:
                prev_temp_long_cum_ror_temp = self._parse_decimal(prev_day_calculated['Temp Long Cum Ror %'])
                prev_temp_short_cum_ror_temp = self._parse_decimal(prev_day_calculated['Temp short Cum RoR %'])
                prev_eod_cf_val = self._parse_decimal(prev_day_calculated['Eod Cashflow'])

                if (prev_temp_long_cum_ror_temp == -100 or prev_temp_short_cum_ror_temp == 100) and \
                   (current_bod_cf != 0 or prev_eod_cf_val != 0):
                    cond_n4 = True
            df.at[i, 'NCTRL 4'] = 1 if cond_n4 else 0
            current_nctrl4 = df.at[i, 'NCTRL 4']

            # Calculate 'Perf Reset'
            df.at[i, 'Perf Reset'] = self._calculate_perf_reset(nctrl1, nctrl2, nctrl3, current_nctrl4)
            current_perf_reset = df.at[i, 'Perf Reset']

            # Calculate 'Long Cum Ror %' and 'Short Cum RoR %'
            long_cum_ror, short_cum_ror = self._calculate_long_short_cum_ror_final(
                current_nip, current_perf_reset,
                current_temp_long_cum_ror, current_temp_short_cum_ror,
                current_bod_cf,
                prev_day_calculated, next_day_data, effective_period_start_date, current_perf_date
            )
            df.at[i, 'Long Cum Ror %'] = long_cum_ror
            df.at[i, 'Short Cum RoR %'] = short_cum_ror
            current_long_cum_ror_final = df.at[i, 'Long Cum Ror %']
            current_short_cum_ror_final = df.at[i, 'Short Cum RoR %']

            # Calculate 'Long /Short'
            df.at[i, 'Long /Short'] = "S" if current_sign == -1 else "L"

            # Calculate 'Final Cummulative ROR %'
            df.at[i, 'Final Cummulative ROR %'] = ((Decimal(1) + current_long_cum_ror_final/100) * \
                                                  (Decimal(1) + current_short_cum_ror_final/100) - Decimal(1)) * 100

        # Final conversion of Decimal objects to float for JSON serialization.
        # This is done for the entire DataFrame at the end to ensure all Decimal values are converted.
        for col in df.columns:
            # Check if the column contains Decimal objects
            if df[col].dtype == object and len(df) > 0 and any(isinstance(x, Decimal) for x in df[col]):
                df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

        # Convert date objects in 'Perf. Date' back to string for JSON output
        df['Perf. Date'] = df['Perf. Date'].apply(lambda x: x.strftime("%Y-%m-%d") if isinstance(x, date) else x)

        # Convert to list of dictionaries for JSON output, only for rows within the overall reporting start date
        # (rows before this were zeroed out anyway).
        final_df = df[df['Perf. Date'] >= overall_effective_report_start_date.strftime("%Y-%m-%d")].copy()
        return final_df.to_dict(orient='records')