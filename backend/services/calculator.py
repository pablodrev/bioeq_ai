"""
Sample size and design parameter calculations.
"""
import math
from typing import Dict, Tuple, Optional

class BioeEquivalenceCalculator:
    """
    Calculates bioequivalence study design parameters.
    Based on Russian and EMA guidelines for generic drugs.
    """
    
    @staticmethod
    def calculate_sample_size(
        cv_intra: float,
        power: float = 0.80,
        alpha: float = 0.05,
        theta0: float = 0.95,
        theta1: float = 0.80,
        theta2: float = 1.25
    ) -> Tuple[int, str]:
        """
        Calculate sample size for 2x2 crossover bioequivalence study.
        
        Args:
            cv_intra: Intra-individual coefficient of variation (%)
            power: Statistical power (default 0.80 = 80%)
            alpha: Significance level (default 0.05 = 5%)
            theta0: True ratio (usually 0.95)
            theta1: Lower bioequivalence limit (usually 0.80)
            theta2: Upper bioequivalence limit (usually 1.25)
        
        Returns:
            Tuple of (sample_size, design_type)
        """
        
        # Convert CV to decimal
        cv_decimal = cv_intra / 100
        
        # Convert CV to variance on log scale
        # var_log = ln(CV^2 + 1)
        var_log = math.log(cv_decimal ** 2 + 1)
        
        # Standard error squared
        se_sq = var_log / 2  # For 2x2 crossover
        
        # Critical value from t-distribution (approximated as normal for large N)
        # For 2-sided test at alpha=0.05: z = 1.96
        # For non-inferiority: z_beta/z_alpha
        z_alpha = 1.96
        z_beta = 0.84  # For 80% power
        
        # For equivalence test: can use more accurate formula
        # n = 2 * ((z_alpha + z_beta) / log(theta2/theta1))^2 * se_sq
        
        # Simplified formula for 2x2 crossover
        log_theta = math.log(theta2 / theta1)  # Usually log(1.25/0.80) = log(1.5625) ≈ 0.447
        
        n_unrounded = 2 * ((z_alpha + z_beta) / log_theta) ** 2 * se_sq
        
        # Round up to nearest even number (pairs in crossover)
        n = int(math.ceil(n_unrounded / 2)) * 2
        
        # Minimum sample size is 12 (6 per period in crossover)
        n = max(n, 12)
        
        return n, "2x2 crossover"

    @staticmethod
    def calculate_sample_size_for_design(
        cv_intra: float,
        design_type: str,
        power: float = 0.80,
        alpha: float = 0.05,
        theta1: float = 0.80,
        theta2: float = 1.25
    ) -> Tuple[int, str]:
        """
        Generalized sample size calculation that adapts the variance term
        for different study designs. This is an approximation intended for
        planning and UI / reporting purposes.
        """
        # Map design type to an effective within-subject factor
        # (smaller factor -> smaller variance on comparison)
        design = design_type.lower()
        if "2x2" in design or "crossover" in design:
            se_factor = 1 / 2.0
        elif "3-way" in design or ("3" in design and "replicate" in design):
            se_factor = 1 / 3.0
        elif "4-way" in design or ("4" in design and "replicate" in design):
            se_factor = 1 / 4.0
        elif "параллел" in design or "parallel" in design:
            # Parallel designs typically have larger variance (between-subject)
            se_factor = 1.0
        else:
            # Default to crossover behaviour
            se_factor = 1 / 2.0

        # Use same core math as for calculate_sample_size but adapt se_sq
        cv_decimal = cv_intra / 100.0
        var_log = math.log(cv_decimal ** 2 + 1)
        se_sq = var_log * se_factor

        z_alpha = 1.96
        z_beta = 0.84 if power == 0.80 else 0.84  # keep simple for now

        log_theta = math.log(theta2 / theta1)
        n_unrounded = 2 * ((z_alpha + z_beta) / log_theta) ** 2 * se_sq

        if se_factor == 1.0:
            # Parallel: result represents total subjects (split between groups)
            n = int(math.ceil(n_unrounded))
        else:
            # For crossover and replicate designs ensure even subject counts
            n = int(math.ceil(n_unrounded / 2.0)) * 2

        n = max(n, 12)
        return n, design_type

    @staticmethod
    def choose_design_type(cv_intra: float, t_half: Optional[float]) -> str:
        """
        Choose a study design based on half-life and CV following rules:
        - If t_half is very long (weeks/months) -> Parallel
        - Else: CV <=30% -> 2x2 crossover
                CV 30-50% -> 3-way replicate
                CV >50% -> 4-way replicate
        """
        # Consider 'very long' half-life as >= 2 weeks (336 hours)
        if t_half is not None:
            try:
                if float(t_half) >= 24.0 * 7.0 * 2.0:
                    return "Параллельный"
            except Exception:
                pass

        # Fallback to CV-based rules
        if cv_intra <= 30.0:
            return "2x2 crossover"
        if 30.0 < cv_intra <= 50.0:
            return "3-way replicate"
        return "4-way replicate"

    @staticmethod
    def design_explanation(cv_intra: float, t_half: Optional[float], design_type: str) -> str:
        """
        Return a templated explanation (in Russian) why a particular design
        was chosen based on the simple rules.
        """
        # Check very long half-life rule
        try:
            if t_half is not None and float(t_half) >= 24.0 * 7.0 * 2.0:
                return (
                    f"Полувыведение ({t_half} часов) очень длинное; для таких веществ "
                    "рекомендуется параллельный дизайн (избегается период отмывания)."
                )
        except Exception:
            pass

        # CV-based explanations
        if cv_intra <= 30.0:
            return (
                f"CV_intra = {cv_intra}%. При CV ≤ 30% достаточно 2×2 кроссовера — "
                "эффективный дизайн с наименьшим числом участников."
            )
        if 30.0 < cv_intra <= 50.0:
            return (
                f"CV_intra = {cv_intra}%. При CV между 30% и 50% рекомендуется 3-way replicate — "
                "репликатный дизайн для более точной оценки вариабельности."
            )
        return (
            f"CV_intra = {cv_intra}%. При CV > 50% рекомендуется 4-way replicate — "
            "репликатный дизайн с большим числом периодов для контроля высокой внутрисубъектной вариабельности."
        )
    
    @staticmethod
    def estimate_washout_period(t_half: float) -> float:
        """
        Estimate washout period for crossover study.
        Rule: at least 5-7 half-lives to ensure < 5% residual concentration.
        
        Args:
            t_half: Terminal half-life in hours
        
        Returns:
            Recommended washout period in hours
        """
        # 5 half-lives for 97% elimination, 7 for 99%
        washout_hours = t_half * 7
        
        # Round up to nearest day
        washout_days = math.ceil(washout_hours / 24)
        
        return washout_days
    
    @staticmethod
    def estimate_blood_sampling(tmax: float, t_half: float) -> Dict[str, float]:
        """
        Estimate optimal blood sampling times for PK study.
        
        Args:
            tmax: Time to Cmax in hours
            t_half: Half-life in hours
        
        Returns:
            Dict with sampling times
        """
        return {
            "predose": 0.0,
            "post_dose_early": tmax * 0.25,
            "post_dose_peak": tmax,
            "post_dose_late_1": tmax + t_half,
            "post_dose_late_2": tmax + t_half * 3,
            "post_dose_late_3": tmax + t_half * 5,
        }
    
    @staticmethod
    def calculate_recruitment_sample_size(
        sample_size: int,
        dropout_rate: float = 0.0,
        screen_fail_rate: float = 0.0
    ) -> int:
        """
        Adjust sample size for dropout and screen failure rates.
        
        Args:
            sample_size: Required evaluable sample size
            dropout_rate: Expected dropout rate as percentage (0-100)
            screen_fail_rate: Expected screen failure rate as percentage (0-100)
        
        Returns:
            Adjusted recruitment sample size
        """
        if dropout_rate < 0 or dropout_rate > 100:
            raise ValueError("dropout_rate must be between 0 and 100")
        if screen_fail_rate < 0 or screen_fail_rate > 100:
            raise ValueError("screen_fail_rate must be between 0 and 100")
        
        # Convert percentages to decimals
        dropout_decimal = dropout_rate / 100
        screen_fail_decimal = screen_fail_rate / 100
        
        # Calculate adjustment factor
        # recruitment_needed = evaluable / ((1 - dropout) * (1 - screen_fail))
        adjustment_factor = (1 - dropout_decimal) * (1 - screen_fail_decimal)
        
        if adjustment_factor <= 0:
            raise ValueError("dropout_rate + screen_fail_rate cannot equal or exceed 100%")
        
        # Calculate recruitment size (round up)
        recruitment_size = int(math.ceil(sample_size / adjustment_factor))
        
        return recruitment_size

