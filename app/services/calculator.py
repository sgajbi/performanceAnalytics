import pandas as pd
from datetime import datetime, date
from decimal import Decimal, getcontext
import calendar
import numpy as np # Import numpy for NaT checks

# Set global precision for Decimal calculations
getcontext().prec = 28

class PortfolioPerformanceCalculator:
    def __init__(self, config):
        """
        Initializes the calculator with global configuration parameters.
        :param config: Dictionary containing 'performance_start_date', 'metric_basis', 'period_type',
                       'report_start_date', 'report_end_date'.
        Note: Dates in config (performance_start_date, report_start_date, report_end_date) are expected to be
        datetime.date objects due to Pydantic parsing in main.py, but this class defensively converts them.
        """
        self.performance_start_date = self._parse_date(config.get("performance_start_date"))
        self.metric_basis = config["metric_basis"] # "NET" or "GROSS"
        self.period_type = config.get("period_type", "Explicit") # "MTD", "QTD", "YTD", "Explicit"
        self.report_start_date = self._parse_date(config.get("report_start_date"))
        self.report_end_date = self._parse_date(config.get("report_end_date"))


    def _parse_date(self, date_val):
        """Helper to safely parse various date inputs (str, date, NaT) to datetime.date objects."""
        if isinstance(date_val, date):
            return date_val
        elif isinstance(date_val, str):
            try:
                return datetime.strptime(date_val, "%Y-%m-%d").date()
            except ValueError:
                return None # Or raise a more specific error if a date is mandatory
        elif pd.isna(date_val) if isinstance(date_val, (pd.Timestamp, float)) else False: # Handles NaT from pandas, and float for NaN
            return None
        return None # For None or any other unexpected type


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

        if (current_begin_mv + current_bod_cf + current_end_mv + current_eod_cf == 0) and \
           (current_eod_cf == self._get_sign(current_bod_cf)):
            return 1
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
        if current_day == 1:
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
        return self._get_sign(val_for_sign)


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
            return current_daily_ror
        elif current_sign == 1:
            if prev_day_calculated is not None:
                prev_long_cum_ror_final = self._parse_decimal(prev_day_calculated['Long Cum Ror %'])

                if current_daily_ror == 0:
                    return prev_long_cum_ror_final
                else:
                    calc_val = ((Decimal(1) + prev_long_cum_ror_final/100) * \
                                (Decimal(1) + current_daily_ror/100 * current_bmv_bcf_sign) - Decimal(1)) * 100
                    return calc_val
        return Decimal(0)


    def _calculate_temp_short_cum_ror(self, current_sign, current_daily_ror, current_perf_date, prev_day_calculated, current_bmv_bcf_sign, effective_period_start_date):
        """Calculates 'Temp short Cum RoR %' for the current row, resetting at effective_period_start_date."""

        if current_perf_date == effective_period_start_date:
            return current_daily_ror
        elif current_sign != 1: # Short positions logic
            if prev_day_calculated is not None:
                prev_short_cum_ror_final = self._parse_decimal(prev_day_calculated['Short Cum RoR %'])

                if current_daily_ror == 0:
                    return prev_short_cum_ror_final
                else:
                    calc_val = ((Decimal(1) + prev_short_cum_ror_final/100) * \
                                (Decimal(1) + current_daily_ror/100 * current_bmv_bcf_sign) - Decimal(1)) * 100
                    return calc_val
        return Decimal(0)

    def _calculate_nctrls(self, current_temp_long_cum_ror, current_temp_short_cum_ror,
                          current_bod_cf, current_eod_cf, current_perf_date, next_day_data, report_end_date):
        """Calculates NCTRL 1-3 for the current row."""
        next_bod_cf_val = self._parse_decimal(next_day_data.get('BOD Cashflow', 0)) if next_day_data is not None else Decimal(0)
        next_date_val_raw = next_day_data.get('Perf. Date') if next_day_data is not None else None

        next_date_beyond_period = False
        if next_date_val_raw is not None and report_end_date is not None:
            # Robustly convert next_date_val_raw to datetime.date object
            try:
                # Use errors='coerce' to turn unparseable dates into NaT
                next_date_val = pd.to_datetime(next_date_val_raw, errors='coerce').date()
            except Exception:
                # Fallback if pd.to_datetime itself fails or if it's already a date object
                if isinstance(next_date_val_raw, date):
                    next_date_val = next_date_val_raw
                else:
                    next_date_val = None # Set to None if it cannot be converted to a valid date

            if next_date_val is not None: # Only compare if next_date_val is a valid date
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

        next_nip_val = self._parse_decimal(next_day_data.get('NIP', 0)) if next_day_data is not None else Decimal(0)
        next_bod_cf_val = self._parse_decimal(next_day_data.get('BOD Cashflow', 0)) if next_day_data is not None else Decimal(0)


        lookahead_reset_cond = False
        if next_day_data is not None:
            if next_nip_val == 0 and next_bod_cf_val != 0 and \
               (current_temp_long_cum_ror <= Decimal(-100) or current_temp_short_cum_ror >= Decimal(100)):
                lookahead_reset_cond = True

        is_current_date_period_start = (current_perf_date == effective_period_start_date)

        if current_nip == 1:
            if is_current_date_period_start or lookahead_reset_cond:
                 return Decimal(0), Decimal(0)
            else:
                return prev_long_cum_ror_final, prev_short_cum_ror_final

        else:
            reset_if_prev_nip_active_and_no_cf = False
            if prev_day_calculated is not None:
                if prev_nip == 1 and current_bod_cf == 0 and \
                   (prev_long_cum_ror_final <= Decimal(-100) or prev_short_cum_ror_final >= Decimal(100)):
                    reset_if_prev_nip_active_and_no_cf = True

            if reset_if_prev_nip_active_and_no_cf:
                return Decimal(0), Decimal(0)
            elif is_current_date_period_start:
                return current_temp_long_cum_ror, current_temp_short_cum_ror
            else:
                return current_temp_long_cum_ror, current_temp_short_cum_ror


    def calculate_performance(self, daily_data_list, config):
        """
        Calculates portfolio performance based on daily data.
        :param daily_data_list: List of dictionaries, each representing a day's data.
        :param config: Dictionary containing additional configuration.

        :return: List of dictionaries with all calculated performance metrics.
        """
        df = pd.DataFrame(daily_data_list)
        # Convert to datetime.date objects, coercing errors to NaT
        df['Perf. Date'] = pd.to_datetime(df['Perf. Date'], errors='coerce').dt.date

        overall_effective_report_start_date = self.performance_start_date
        if self.report_start_date:
             overall_effective_report_start_date = max(self.performance_start_date, self.report_start_date)

        if self.report_end_date:
            # self.report_end_date is now guaranteed to be a datetime.date object or None due to _parse_date in __init__
            temp_report_end_date = self.report_end_date
            
            # --- DEBUGGING PRINTS ---
            print(f"DEBUG: Type of df['Perf. Date'] series elements before filter: {type(df['Perf. Date'].iloc[0]) if not df['Perf. Date'].empty else 'Empty Series'}")
            print(f"DEBUG: Value of df['Perf. Date'].iloc[0] (if not empty): {df['Perf. Date'].iloc[0] if not df['Perf. Date'].empty else 'N/A'}")
            print(f"DEBUG: Type of temp_report_end_date: {type(temp_report_end_date)}")
            print(f"DEBUG: Value of temp_report_end_date: {temp_report_end_date}")
            # --- END DEBUGGING PRINTS ---

            # Perform the filtering with guaranteed date types
            df = df[df['Perf. Date'] <= temp_report_end_date].copy()

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


        df['NIP'] = df.apply(self._calculate_nip, axis=1)

        for i, row in df.iterrows():
            current_day = self._parse_decimal(row['Day'])
            current_perf_date = row['Perf. Date'] # This is already a date object or NaT/None
            current_begin_mv = self._parse_decimal(row['Begin Market Value'])
            current_bod_cf = self._parse_decimal(row['BOD Cashflow'])
            current_eod_cf = self._parse_decimal(row['Eod Cashflow'])
            current_mgmt_fees = self._parse_decimal(row['Mgmt fees'])
            current_end_mv = self._parse_decimal(row['End Market Value'])
            current_nip = self._parse_decimal(row['NIP'])


            prev_day_calculated = df.loc[i-1] if i > 0 and (i-1) in df.index else None
            # next_day_data will have 'Perf. Date' as a date object or NaT/None
            next_day_data = df.iloc[i+1].to_dict() if i + 1 < len(df) else None

            effective_period_start_date = None
            if self.period_type == "MTD":
                effective_period_start_date = date(current_perf_date.year, current_perf_date.month, 1)
            elif self.period_type == "QTD":
                effective_period_start_date = self._get_start_of_quarter(current_perf_date)
            elif self.period_type == "YTD":
                effective_period_start_date = date(current_perf_date.year, 1, 1)
            elif self.period_type == "Explicit":
                effective_period_start_date = overall_effective_report_start_date
            else:
                effective_period_start_date = self.performance_start_date

            # If current_perf_date became NaT, skip calculations for this row
            if pd.isna(current_perf_date):
                # Optionally, set this row's calculated values to defaults/NaNs
                # For now, let's just continue
                continue

            effective_period_start_date = max(effective_period_start_date, self.performance_start_date)


            val_for_sign = current_begin_mv + current_bod_cf
            df.at[i, 'sign'] = self._calculate_sign(current_day, val_for_sign, prev_day_calculated)
            current_sign = df.at[i, 'sign']


            df.at[i, 'daily ror %'] = self._calculate_daily_ror(
                current_perf_date, current_begin_mv,
                current_bod_cf, current_end_mv, current_eod_cf, current_mgmt_fees,
                effective_period_start_date
            )
            current_daily_ror = df.at[i, 'daily ror %']

            # This comparison is now correctly between date objects
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
                continue

            df.at[i, 'Temp Long Cum Ror %'] = self._calculate_temp_long_cum_ror(
                current_sign, current_daily_ror, current_perf_date, prev_day_calculated, current_sign, effective_period_start_date
            )
            current_temp_long_cum_ror = df.at[i, 'Temp Long Cum Ror %']


            df.at[i, 'Temp short Cum RoR %'] = self._calculate_temp_short_cum_ror(
                current_sign, current_daily_ror, current_perf_date, prev_day_calculated, current_sign, effective_period_start_date
            )
            current_temp_short_cum_ror = df.at[i, 'Temp short Cum RoR %']


            nctrl1, nctrl2, nctrl3 = self._calculate_nctrls(
                current_temp_long_cum_ror, current_temp_short_cum_ror,
                current_bod_cf, current_eod_cf, current_perf_date, next_day_data, self.report_end_date
            )
            df.at[i, 'NCTRL 1'] = nctrl1
            df.at[i, 'NCTRL 2'] = nctrl2
            df.at[i, 'NCTRL 3'] = nctrl3

            cond_n4 = False
            if prev_day_calculated is not None:
                prev_temp_long_cum_ror_temp = self._parse_decimal(prev_day_calculated['Temp Long Cum Ror %'])
                prev_temp_short_cum_ror_temp = self._parse_decimal(prev_day_calculated['Temp short Cum RoR %'])
                prev_eod_cf_val = self._parse_decimal(prev_day_calculated['Eod Cashflow'])

                if (prev_temp_long_cum_ror_temp <= Decimal(-100) or prev_temp_short_cum_ror_temp >= Decimal(100)) and \
                   (current_bod_cf != 0 or prev_eod_cf_val != 0):
                    cond_n4 = True
            df.at[i, 'NCTRL 4'] = 1 if cond_n4 else 0
            current_nctrl4 = df.at[i, 'NCTRL 4']

            df.at[i, 'Perf Reset'] = self._calculate_perf_reset(nctrl1, nctrl2, nctrl3, current_nctrl4)
            current_perf_reset = df.at[i, 'Perf Reset']

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

            df.at[i, 'Long /Short'] = "S" if current_sign == -1 else "L"

            df.at[i, 'Final Cummulative ROR %'] = ((Decimal(1) + current_long_cum_ror_final/100) * \
                                                   (Decimal(1) + current_short_cum_ror_final/100) - Decimal(1)) * 100

        # Filter the final DataFrame by overall_effective_report_start_date
        # Both df['Perf. Date'] and overall_effective_report_start_date are date objects here.
        final_df = df[df['Perf. Date'] >= overall_effective_report_start_date].copy()


        # Convert Decimal columns to float for JSON serialization
        for col in final_df.columns:
            # Check if the column is of 'object' dtype (which Decimal columns often are)
            # and if it contains at least one Decimal instance.
            # This ensures we only convert Decimal objects, preserving other 'object' types like strings.
            if final_df[col].dtype == object and len(final_df) > 0 and any(isinstance(x, Decimal) for x in final_df[col]):
                final_df[col] = final_df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

        # Convert 'Perf. Date' column back to string format for JSON response
        final_df['Perf. Date'] = final_df['Perf. Date'].apply(lambda x: x.strftime("%Y-%m-%d") if isinstance(x, date) else x)

        return final_df.to_dict(orient='records')