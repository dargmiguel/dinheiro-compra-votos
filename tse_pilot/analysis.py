from __future__ import annotations

import csv
import json
import math
import sqlite3
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .pipeline import _centavos

ELECTION_DATE = date(2022, 10, 2)
MISSING_VALUES = {"", "#NULO", "#NE"}


def _missing(value: Any) -> bool:
    return value is None or str(value).strip().upper() in MISSING_VALUES


def _age_at_election(value: str | None) -> int | None:
    if _missing(value):
        return None
    try:
        born = datetime.strptime(str(value).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None
    return ELECTION_DATE.year - born.year - ((ELECTION_DATE.month, ELECTION_DATE.day) < (born.month, born.day))


def _pt_int(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def _pt_decimal(value: float, places: int = 2) -> str:
    formatted = f"{float(value):,.{places}f}"
    return formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _pt_brl_centavos(value: int) -> str:
    return _pt_decimal(value / 100)


def _pt_bool(value: bool | None) -> str:
    return "sim" if value is True else "não" if value is False else "não verificado"


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_validation(path: Path) -> dict[str, Any]:
    validation = json.loads(path.read_text(encoding="utf-8"))
    if validation.get("status") != "approved":
        raise ValueError("análise exige validação do pipeline com status approved")
    denominator = validation.get("vote_denominator")
    if not denominator or denominator.get("uf_count") != 27:
        raise ValueError("validação não comprova denominador oficial reconciliado para as 27 UFs")
    fatal_counts = validation.get("fatal_counts")
    if not isinstance(fatal_counts, dict) or not fatal_counts or any(int(value) != 0 for value in fatal_counts.values()):
        raise ValueError("análise exige todas as contagens fatais da validação iguais a zero")
    return validation


def _expense_totals(connection: sqlite3.Connection, deduplicated: bool) -> dict[str, int]:
    if deduplicated:
        query = """
            SELECT e.sq_candidate, SUM(e.amount_centavos) AS amount_centavos
            FROM expenses e
            JOIN expense_occurrences o
              ON o._source_member = e.source_member AND o._source_row = e.source_row
            JOIN candidates c ON c.sq_candidate = e.sq_candidate
            WHERE c.candidate_status_code = '12'
              AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
              AND o.TP_PRESTACAO_CONTAS = 'Final'
            GROUP BY e.sq_candidate
        """
        return {row[0]: int(row[1]) for row in connection.execute(query)}

    totals: dict[str, int] = {}
    query = """
        SELECT o.SQ_CANDIDATO, o.VR_DESPESA_CONTRATADA
        FROM expense_occurrences o
        JOIN candidates c ON c.sq_candidate = o.SQ_CANDIDATO
        WHERE c.candidate_status_code = '12'
          AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
          AND o.TP_PRESTACAO_CONTAS = 'Final'
        ORDER BY o._source_member, o._source_row
    """
    for candidate_id, amount in connection.execute(query):
        totals[candidate_id] = totals.get(candidate_id, 0) + _centavos(amount)
    return totals


def _expense_survey_by_type(
    connection: sqlite3.Connection,
    status_code: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = {
        row[0]
        for row in connection.execute(
            "SELECT sq_candidate FROM candidates WHERE candidate_status_code = ? AND election_year = 2022 AND turn = 1 AND cargo_code = '6'",
            (status_code,),
        )
    }
    raw_types: dict[str, dict[str, Any]] = {}
    per_candidate_type: dict[tuple[str, str], int] = {}
    raw_query = """
        SELECT o.SQ_CANDIDATO, o.TP_PRESTACAO_CONTAS, o.VR_DESPESA_CONTRATADA
        FROM expense_occurrences o
        JOIN candidates c ON c.sq_candidate = o.SQ_CANDIDATO
        WHERE c.candidate_status_code = ?
          AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
        ORDER BY o._source_member, o._source_row
    """
    for candidate_id, raw_type, raw_amount in connection.execute(raw_query, (status_code,)):
        submission_type = "(não informado)" if _missing(raw_type) else str(raw_type).strip()
        amount = _centavos(raw_amount)
        summary = raw_types.setdefault(
            submission_type,
            {"candidates": set(), "rows": 0, "zero_rows": 0, "amount_centavos": 0},
        )
        summary["candidates"].add(candidate_id)
        summary["rows"] += 1
        summary["zero_rows"] += int(amount == 0)
        summary["amount_centavos"] += amount
        key = (candidate_id, submission_type)
        per_candidate_type[key] = per_candidate_type.get(key, 0) + amount

    deduplicated_types: dict[str, dict[str, Any]] = {}
    excluded_candidates_by_type: dict[str, set[str]] = {}
    excluded_rows_by_type: dict[str, int] = {}
    exclusion_query = """
        SELECT o.SQ_CANDIDATO, o.TP_PRESTACAO_CONTAS
        FROM expense_dedup_exclusions x
        JOIN expense_occurrences o
          ON o._source_archive = x.source_archive
         AND o._source_member = x.source_member
         AND o._source_row = x.source_row
        JOIN candidates c ON c.sq_candidate = o.SQ_CANDIDATO
        WHERE c.candidate_status_code = ?
          AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
    """
    for candidate_id, raw_type in connection.execute(exclusion_query, (status_code,)):
        submission_type = "(não informado)" if _missing(raw_type) else str(raw_type).strip()
        excluded_candidates_by_type.setdefault(submission_type, set()).add(candidate_id)
        excluded_rows_by_type[submission_type] = excluded_rows_by_type.get(submission_type, 0) + 1
    deduplicated_query = """
        SELECT e.sq_candidate, o.TP_PRESTACAO_CONTAS, e.amount_centavos
        FROM expenses e
        JOIN expense_occurrences o
          ON o._source_member = e.source_member AND o._source_row = e.source_row
        JOIN candidates c ON c.sq_candidate = e.sq_candidate
        WHERE c.candidate_status_code = ?
          AND c.election_year = 2022 AND c.turn = 1 AND c.cargo_code = '6'
        ORDER BY e.source_member, e.source_row
    """
    for candidate_id, raw_type, amount in connection.execute(deduplicated_query, (status_code,)):
        submission_type = "(não informado)" if _missing(raw_type) else str(raw_type).strip()
        summary = deduplicated_types.setdefault(submission_type, {"candidates": set(), "rows": 0, "amount_centavos": 0})
        summary["candidates"].add(candidate_id)
        summary["rows"] += 1
        summary["amount_centavos"] += int(amount)

    rows: list[dict[str, Any]] = []
    for submission_type in sorted(set(raw_types) | set(deduplicated_types)):
        raw = raw_types.get(submission_type, {"candidates": set(), "rows": 0, "zero_rows": 0, "amount_centavos": 0})
        deduplicated = deduplicated_types.get(submission_type, {"candidates": set(), "rows": 0, "amount_centavos": 0})
        zero_candidates = sum(
            amount == 0
            for (candidate, kind), amount in per_candidate_type.items()
            if kind == submission_type
        )
        excluded_count = excluded_rows_by_type.get(submission_type, 0)
        if excluded_count != raw["rows"] - deduplicated["rows"]:
            raise ValueError(f"exclusões não reconciliam para status {status_code}, prestação {submission_type}")
        rows.append({
            "tp_prestacao_contas": submission_type,
            "candidate_status_code": status_code,
            "candidate_count": len(candidates),
            "candidates_with_rows": len(raw["candidates"]),
            "candidates_without_rows": len(candidates) - len(raw["candidates"]),
            "candidates_with_zero_total": zero_candidates,
            "all_lines_occurrence_rows": raw["rows"],
            "all_lines_zero_amount_rows": raw["zero_rows"],
            "all_lines_declared_expense_centavos": raw["amount_centavos"],
            "deduplicated_occurrence_rows": deduplicated["rows"],
            "deduplicated_candidates_with_rows": len(deduplicated["candidates"]),
            "deduplicated_declared_expense_centavos": deduplicated["amount_centavos"],
            "excluded_occurrence_rows": excluded_count,
            "excluded_affected_candidates": len(excluded_candidates_by_type.get(submission_type, set())),
            "excluded_amount_centavos": raw["amount_centavos"] - deduplicated["amount_centavos"],
        })
    any_rows = {candidate for candidate, _ in per_candidate_type}
    return rows, {
        "candidate_count": len(candidates),
        "candidates_with_any_expense_rows": len(any_rows),
        "candidates_without_any_expense_rows": len(candidates - any_rows),
        "expense_occurrence_rows": sum(row["all_lines_occurrence_rows"] for row in rows),
        "deduplicated_occurrence_rows": sum(row["deduplicated_occurrence_rows"] for row in rows),
        "all_lines_declared_expense_centavos": sum(row["all_lines_declared_expense_centavos"] for row in rows),
        "deduplicated_declared_expense_centavos": sum(row["deduplicated_declared_expense_centavos"] for row in rows),
    }


def _design_matrix(
    frame: pd.DataFrame,
    include_demographics: bool,
    interaction: bool,
    include_age: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    design = pd.DataFrame(index=frame.index)
    design["intercept"] = 1.0
    design["log1p_expense_brl"] = frame["log1p_expense_brl"].astype(float)
    if include_age:
        design["age_at_election"] = frame["age_at_election"].astype(float)
    categorical = ["uf", "party_code"]
    if include_demographics:
        categorical += ["gender", "race", "schooling"]
    if interaction:
        categorical.remove("gender")
    for column in categorical:
        values = frame[column].astype(str)
        dummies = pd.get_dummies(values, prefix=column, drop_first=True, dtype=float)
        design = pd.concat([design, dummies], axis=1)
    if interaction:
        design["female"] = (frame["gender"] == "FEMININO").astype(float)
        design["expense_x_female"] = design["log1p_expense_brl"] * design["female"]
    return design, categorical


def _fit_model(
    name: str,
    frame: pd.DataFrame,
    include_demographics: bool,
    interaction: bool,
    include_age: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]], Any, pd.DataFrame]:
    model_frame = frame
    if interaction:
        model_frame = frame[frame["gender"].isin(["FEMININO", "MASCULINO"])].copy()
    design, categorical = _design_matrix(model_frame, include_demographics, interaction, include_age)
    required_controls = ["uf", "party_code"]
    if include_age:
        required_controls.append("age_at_election")
    if include_demographics:
        required_controls.extend(["gender", "race", "schooling"])
    missing_columns = [column for column in required_controls if model_frame[column].isna().any()]
    if missing_columns:
        raise ValueError(f"amostra do modelo contém controles ausentes: {', '.join(missing_columns)}")
    if np.linalg.matrix_rank(design.to_numpy()) != design.shape[1]:
        raise ValueError(f"matriz do modelo {name} tem colinearidade exata; estimativa não foi publicada")
    fitted = sm.GLM(model_frame["vote_share"], design, family=sm.families.Binomial()).fit(maxiter=100, cov_type="HC1")
    if not fitted.converged:
        raise ValueError(f"modelo {name} não convergiu")
    conf = fitted.conf_int()
    coefficient_rows = []
    for term, estimate in fitted.params.items():
        coefficient_rows.append({
            "model": name,
            "term": term,
            "coefficient": float(estimate),
            "robust_se_hc1": float(fitted.bse[term]),
            "ci95_low": float(conf.loc[term, 0]),
            "ci95_high": float(conf.loc[term, 1]),
            "p_value": float(fitted.pvalues[term]),
        })
    controls = ["UF", "partido"]
    if include_age:
        controls.append("idade na data da eleição")
    if include_demographics:
        controls.extend(["sexo", "raça", "escolaridade"])
    return {
        "name": name,
        "n": int(fitted.nobs),
        "converged": bool(fitted.converged),
        "covariance": "HC1 robusta",
        "family": "logit fracionário (GLM Binomial)",
        "controls": controls,
        "interaction": interaction,
        "deviance": float(fitted.deviance),
        "aic": float(fitted.aic),
        "categorical_controls": categorical,
    }, coefficient_rows, fitted, model_frame


def _fit_ols_sensitivity(name: str, frame: pd.DataFrame, response: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    design, categorical = _design_matrix(frame, include_demographics=True, interaction=False)
    if np.linalg.matrix_rank(design.to_numpy()) != design.shape[1]:
        raise ValueError(f"matriz do modelo {name} tem colinearidade exata; estimativa não foi publicada")
    fitted = sm.OLS(frame[response], design).fit(cov_type="HC1")
    conf = fitted.conf_int()
    coefficients = [
        {
            "model": name,
            "term": term,
            "coefficient": float(estimate),
            "robust_se_hc1": float(fitted.bse[term]),
            "ci95_low": float(conf.loc[term, 0]),
            "ci95_high": float(conf.loc[term, 1]),
            "p_value": float(fitted.pvalues[term]),
        }
        for term, estimate in fitted.params.items()
    ]
    return {
        "name": name,
        "n": int(fitted.nobs),
        "converged": True,
        "covariance": "HC1 robusta",
        "family": "OLS de sensibilidade",
        "outcome": response,
        "controls": ["UF", "partido", "idade na data da eleição", "sexo", "raça", "escolaridade"],
        "interaction": False,
        "r_squared": float(fitted.rsquared),
        "rmse": float(math.sqrt(fitted.mse_resid)),
        "categorical_controls": categorical,
    }, coefficients

def _marginal_prediction(
    fitted: Any,
    standardization_frame: pd.DataFrame,
    expense_centavos: float,
    *,
    interaction: bool = False,
    gender: str | None = None,
) -> dict[str, float]:
    prediction_frame = standardization_frame.copy()
    prediction_frame["log1p_expense_brl"] = math.log1p(float(expense_centavos) / 100)
    if gender is not None:
        prediction_frame["gender"] = gender
    design, _ = _design_matrix(
        prediction_frame,
        include_demographics=True,
        interaction=interaction,
        include_age=True,
    )
    design = design.reindex(columns=fitted.model.exog_names, fill_value=0.0)
    matrix = design.to_numpy(dtype=float)
    linear_predictor = matrix @ fitted.params.to_numpy(dtype=float)
    probability = 1 / (1 + np.exp(-np.clip(linear_predictor, -40, 40)))
    mean_prediction = float(probability.mean())
    gradient = (matrix * (probability * (1 - probability))[:, None]).mean(axis=0)
    covariance = np.asarray(fitted.cov_params(), dtype=float)
    variance = max(0.0, float(gradient @ covariance @ gradient))
    standard_error = math.sqrt(variance)
    margin = 1.959963984540054 * standard_error
    return {
        "prediction": mean_prediction,
        "ci95_lower": max(0.0, mean_prediction - margin),
        "ci95_upper": min(1.0, mean_prediction + margin),
        "standard_error": standard_error,
    }


def _fit_diagnostics(fitted: Any, frame: pd.DataFrame) -> dict[str, Any]:
    observed = frame["vote_share"].to_numpy(dtype=float)
    predicted = np.asarray(fitted.fittedvalues, dtype=float)
    residual = observed - predicted
    calibration_frame = pd.DataFrame(
        {"observed": observed, "predicted": predicted},
        index=frame.index,
    )
    calibration_frame["decile"] = pd.qcut(
        calibration_frame["predicted"],
        q=10,
        labels=False,
        duplicates="drop",
    )
    calibration_deciles = []
    for decile, group in calibration_frame.groupby("decile", observed=True):
        mean_observed = float(group["observed"].mean())
        mean_predicted = float(group["predicted"].mean())
        calibration_deciles.append({
            "decile": int(decile) + 1,
            "n": int(len(group)),
            "mean_observed_vote_share": mean_observed,
            "mean_predicted_vote_share": mean_predicted,
            "calibration_gap": mean_observed - mean_predicted,
        })
    return {
        "n": int(len(frame)),
        "mean_observed_vote_share": float(observed.mean()),
        "mean_predicted_vote_share": float(predicted.mean()),
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "mae": float(np.mean(np.abs(residual))),
        "max_absolute_decile_calibration_gap": max(abs(row["calibration_gap"]) for row in calibration_deciles),
        "calibration_deciles": calibration_deciles,
        "evaluation": "calibração na própria amostra; não é validação externa",
    }


def _influence_diagnostics(
    fitted: Any,
    frame: pd.DataFrame,
    expense_column: str,
) -> dict[str, Any]:
    influence = fitted.get_influence(observed=True)
    cooks_distance = np.asarray(influence.cooks_distance[0], dtype=float)
    leverage = np.asarray(influence.hat_matrix_diag, dtype=float)
    fitted_values = np.asarray(fitted.fittedvalues, dtype=float)
    expense_index = fitted.model.exog_names.index("log1p_expense_brl")
    expense_dfbetas = np.asarray(influence.dfbetas[:, expense_index], dtype=float)
    n = len(frame)
    threshold = 4 / n
    finite_cooks = np.isfinite(cooks_distance)
    finite_dfbeta = np.isfinite(expense_dfbetas)
    top_indices = np.argsort(np.where(finite_cooks, cooks_distance, -np.inf))[::-1][:10]
    max_cook = float(np.max(cooks_distance[finite_cooks])) if finite_cooks.any() else None
    max_abs_dfbeta = float(np.max(np.abs(expense_dfbetas[finite_dfbeta]))) if finite_dfbeta.any() else None
    top_candidates = []
    for rank, position in enumerate(top_indices, start=1):
        candidate = frame.iloc[int(position)]
        top_candidates.append({
            "rank": rank,
            "sq_candidate": candidate["sq_candidate"],
            "expense_brl": float(candidate[expense_column]) / 100,
            "observed_vote_share": float(candidate["vote_share"]),
            "fitted_vote_share": float(fitted_values[int(position)]),
            "cooks_distance": float(cooks_distance[position]) if finite_cooks[position] else None,
            "leverage": float(leverage[position]),
            "dfbeta_log1p_expense": float(expense_dfbetas[position]) if finite_dfbeta[position] else None,
        })
    return {
        "n": n,
        "screening_rule": "Distância de Cook > 4/N; triagem heurística, sem exclusão automática de candidaturas",
        "cook_distance_screen_threshold": threshold,
        "candidates_above_cook_screen": int(np.count_nonzero(cooks_distance > threshold)),
        "maximum_cook_distance": max_cook,
        "maximum_leverage": float(leverage.max()),
        "maximum_absolute_expense_dfbeta": max_abs_dfbeta,
        "top_influential_candidates": top_candidates,
    }


def _build_prediction_and_diagnostic_tables(
    fitted_models: dict[str, tuple[Any, pd.DataFrame, str]],
    complete_case_frame: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    spending_quantiles = (("Q25", 0.25), ("Mediana", 0.5), ("Q75", 0.75))
    spending_values = [
        int(np.quantile(
            complete_case_frame["expense_deduplicated_centavos"].to_numpy(dtype=float),
            quantile,
            method="nearest",
        ))
        for _, quantile in spending_quantiles
    ]
    scenario_comparison = []
    for (label, quantile), expense_centavos in zip(spending_quantiles, spending_values):
        dedup_fit, dedup_frame, _ = fitted_models["deduplicado_completo"]
        all_rows_fit, all_rows_frame, _ = fitted_models["todas_as_linhas_completo"]
        dedup_prediction = _marginal_prediction(dedup_fit, dedup_frame, expense_centavos)
        all_rows_prediction = _marginal_prediction(all_rows_fit, all_rows_frame, expense_centavos)
        scenario_comparison.append({
            "expense_level": label,
            "expense_quantile": quantile,
            "expense_brl": expense_centavos / 100,
            "deduplicated_prediction": dedup_prediction["prediction"],
            "deduplicated_ci95_lower": dedup_prediction["ci95_lower"],
            "deduplicated_ci95_upper": dedup_prediction["ci95_upper"],
            "all_rows_prediction": all_rows_prediction["prediction"],
            "all_rows_ci95_lower": all_rows_prediction["ci95_lower"],
            "all_rows_ci95_upper": all_rows_prediction["ci95_upper"],
            "difference_percentage_points": (
                all_rows_prediction["prediction"] - dedup_prediction["prediction"]
            ) * 100,
            "standardization_n": len(dedup_frame),
        })

    interaction_fit, interaction_frame, _ = fitted_models["deduplicado_interacao_sexo"]
    female_expenses = interaction_frame.loc[
        interaction_frame["gender"] == "FEMININO", "expense_deduplicated_centavos"
    ].to_numpy(dtype=float)
    male_expenses = interaction_frame.loc[
        interaction_frame["gender"] == "MASCULINO", "expense_deduplicated_centavos"
    ].to_numpy(dtype=float)
    female_lower, female_upper = np.quantile(female_expenses, (0.05, 0.95), method="nearest")
    male_lower, male_upper = np.quantile(male_expenses, (0.05, 0.95), method="nearest")
    common_lower = max(float(female_lower), float(male_lower))
    common_upper = min(float(female_upper), float(male_upper))
    if common_lower >= common_upper:
        raise ValueError("faixa central de despesas de mulheres e homens não tem suporte comum")
    curve_expenses = np.unique(np.rint(np.linspace(common_lower, common_upper, 21)).astype(int))
    sex_curve_points = []
    for expense_centavos in curve_expenses:
        male_prediction = _marginal_prediction(
            interaction_fit,
            interaction_frame,
            int(expense_centavos),
            interaction=True,
            gender="MASCULINO",
        )
        female_prediction = _marginal_prediction(
            interaction_fit,
            interaction_frame,
            int(expense_centavos),
            interaction=True,
            gender="FEMININO",
        )
        sex_curve_points.append({
            "expense_brl": int(expense_centavos) / 100,
            "male_prediction": male_prediction["prediction"],
            "male_ci95_lower": male_prediction["ci95_lower"],
            "male_ci95_upper": male_prediction["ci95_upper"],
            "female_prediction": female_prediction["prediction"],
            "female_ci95_lower": female_prediction["ci95_lower"],
            "female_ci95_upper": female_prediction["ci95_upper"],
            "female_minus_male_percentage_points": (
                female_prediction["prediction"] - male_prediction["prediction"]
            ) * 100,
        })
    prediction_tables = {
        "scenario_comparison": scenario_comparison,
        "sex_interaction_curve": {
            "support_definition": "interseção dos intervalos P5–P95 das despesas Final deduplicadas de mulheres e homens",
            "common_support": {
                "female_p05_brl": float(female_lower) / 100,
                "female_p95_brl": float(female_upper) / 100,
                "male_p05_brl": float(male_lower) / 100,
                "male_p95_brl": float(male_upper) / 100,
                "lower_brl": common_lower / 100,
                "upper_brl": common_upper / 100,
            },
            "standardization_n": len(interaction_frame),
            "points": sex_curve_points,
        },
        "standardization": "média de previsões na escala de participação sobre a mesma distribuição de controles completos; fixa-se a despesa e, nas curvas de interação, o sexo",
        "uncertainty_method": "ICs pontuais de 95% pelo método delta para médias padronizadas, usando a covariância sanduíche HC1 do modelo; não são intervalos individuais. Diferenças entre cenários são estimativas pontuais sem IC próprio.",
    }

    model_diagnostics: dict[str, Any] = {}
    calibration_rows = []
    influence_rows = []
    for model_name in ("deduplicado_completo", "todas_as_linhas_completo"):
        fitted, fitted_frame, expense_column = fitted_models[model_name]
        fit = _fit_diagnostics(fitted, fitted_frame)
        influence = _influence_diagnostics(fitted, fitted_frame, expense_column)
        model_diagnostics[model_name] = {"fit": fit, "influence": influence}
        calibration_rows.extend(
            {"model": model_name, **row}
            for row in fit["calibration_deciles"]
        )
        influence_rows.extend(
            {"model": model_name, **row}
            for row in influence["top_influential_candidates"]
        )

    cutoff_centavos = float(np.quantile(
        complete_case_frame["expense_deduplicated_centavos"].to_numpy(dtype=float),
        0.99,
        method="nearest",
    ))
    tail_frame = complete_case_frame.loc[
        complete_case_frame["expense_deduplicated_centavos"] <= cutoff_centavos
    ].copy()
    excluded_tail_count = len(complete_case_frame) - len(tail_frame)
    tail_sensitivity = []
    for scenario, source_model, expense_column in (
        ("deduplicado", "deduplicado_completo", "expense_deduplicated_centavos"),
        ("todas_as_linhas", "todas_as_linhas_completo", "expense_all_lines_centavos"),
    ):
        full_fitted = fitted_models[source_model][0]
        trimmed_frame = tail_frame.copy()
        trimmed_frame["log1p_expense_brl"] = (
            trimmed_frame[expense_column].astype(float).div(100).map(math.log1p)
        )
        _, _, trimmed_fit, _ = _fit_model(
            f"{source_model}_sem_top_1pct",
            trimmed_frame,
            include_demographics=True,
            interaction=False,
            include_age=True,
        )
        full_interval = full_fitted.conf_int().loc["log1p_expense_brl"]
        trimmed_interval = trimmed_fit.conf_int().loc["log1p_expense_brl"]
        tail_sensitivity.append({
            "scenario": scenario,
            "cutoff_rule": "1% superior da distribuição de despesas deduplicadas (P99; candidaturas acima do limite removidas apenas neste diagnóstico)",
            "cutoff_brl": cutoff_centavos / 100,
            "excluded_candidates": excluded_tail_count,
            "n_after_exclusion": int(trimmed_fit.nobs),
            "full_coefficient": float(full_fitted.params["log1p_expense_brl"]),
            "trimmed_coefficient": float(trimmed_fit.params["log1p_expense_brl"]),
            "trimmed_ci95_lower": float(trimmed_interval.iloc[0]),
            "trimmed_ci95_upper": float(trimmed_interval.iloc[1]),
            "coefficient_change": float(
                trimmed_fit.params["log1p_expense_brl"] - full_fitted.params["log1p_expense_brl"]
            ),
            "full_ci95_lower": float(full_interval.iloc[0]),
            "full_ci95_upper": float(full_interval.iloc[1]),
        })
    model_diagnostics["top_one_percent_expense_sensitivity"] = tail_sensitivity
    return prediction_tables, model_diagnostics, calibration_rows, influence_rows




def run_financial_analysis(database_path: Path, validation_path: Path, output_dir: Path) -> dict[str, Any]:
    validation = _read_validation(Path(validation_path))
    validation_path = Path(validation_path)
    data_root = validation_path.parent.parent.parent
    manifest_path = data_root / "manifests" / f"manifest-{validation.get('manifest_id')}.json"
    source_resource: dict[str, Any] = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_resource = next(
            (resource for resource in manifest.get("resources", []) if resource.get("resource_key") == "vote_totals_2022"),
            {},
        )
    source_metadata = {
        "manifest_file": str(manifest_path) if manifest_path.is_file() else None,
        "official_source_url": source_resource.get("url"),
        "frozen_zip": source_resource.get("local_path"),
        "sha256": source_resource.get("file", {}).get("sha256"),
        "size_bytes": source_resource.get("file", {}).get("size_bytes"),
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        table_names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        payment_tables = sorted(name for name in table_names if "pag" in name.casefold() or "paid" in name.casefold())
        required = {"candidates", "votes", "vote_denominators", "expense_occurrences", "expenses"}
        if missing := required - table_names:
            raise ValueError(f"base derivada sem tabelas exigidas: {', '.join(sorted(missing))}")
        candidates = [dict(row) for row in connection.execute(
            """
            SELECT sq_candidate, uf, party_code, birth_date, gender, race, schooling,
                   candidate_status_code, election_year, turn, cargo_code
            FROM candidates
            WHERE election_year = 2022 AND turn = 1 AND cargo_code = '6'
            ORDER BY sq_candidate
            """
        )]
        apto = [candidate for candidate in candidates if candidate["candidate_status_code"] == "12"]
        inapto = [candidate for candidate in candidates if candidate["candidate_status_code"] == "3"]
        vote_totals = {
            row[0]: int(row[1])
            for row in connection.execute("SELECT sq_candidate, SUM(valid_votes) FROM votes GROUP BY sq_candidate")
        }
        denominators = {row[0]: int(row[1]) for row in connection.execute("SELECT uf, valid_votes_total FROM vote_denominators")}
        vote_denominator_rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT uf, election_year, turn, cargo_code, cargo, valid_nominal_votes,
                       valid_legend_votes, valid_votes_total, source_row_count,
                       source_archive, source_member
                FROM vote_denominators ORDER BY uf
                """
            )
        ]
        if len(vote_denominator_rows) != 27 or any(
            row["valid_nominal_votes"] + row["valid_legend_votes"] != row["valid_votes_total"]
            for row in vote_denominator_rows
        ):
            raise ValueError("denominadores da base não cobrem 27 UFs com totais nominais + legenda reconciliados")
        deduplicated_expenses = _expense_totals(connection, deduplicated=True)
        all_expenses = _expense_totals(connection, deduplicated=False)
        apto_rows, apto_expense_summary = _expense_survey_by_type(connection, "12")
        inapto_rows, inapto_summary = _expense_survey_by_type(connection, "3")
        candidate_rows: list[dict[str, Any]] = []
        for candidate in apto:
            candidate_id = candidate["sq_candidate"]
            denominator = denominators.get(candidate["uf"])
            votes = vote_totals.get(candidate_id)
            if denominator is None or denominator <= 0 or votes is None or votes < 0 or votes > denominator:
                continue
            age = _age_at_election(candidate["birth_date"])
            candidate_rows.append({
                "sq_candidate": candidate_id,
                "uf": candidate["uf"],
                "party_code": None if _missing(candidate["party_code"]) else str(candidate["party_code"]),
                "age_at_election": age,
                "gender": None if _missing(candidate["gender"]) else str(candidate["gender"]).strip().upper(),
                "race": None if _missing(candidate["race"]) else str(candidate["race"]).strip().upper(),
                "schooling": None if _missing(candidate["schooling"]) else str(candidate["schooling"]).strip().upper(),
                "valid_nominal_votes": votes,
                "official_valid_votes": denominator,
                "vote_share": votes / denominator,
                "expense_deduplicated_centavos": deduplicated_expenses.get(candidate_id),
                "expense_all_lines_centavos": all_expenses.get(candidate_id),
            })
        frame = pd.DataFrame(candidate_rows)
        if frame.empty:
            raise ValueError("nenhuma candidatura APTO tem denominador e votos nominais válidos observados")
        complete_mask = frame[["expense_deduplicated_centavos", "expense_all_lines_centavos", "uf", "party_code", "age_at_election", "gender", "race", "schooling"]].notna().all(axis=1)
        model_frame = frame.loc[complete_mask].copy()
        missing_final_expense = frame["expense_deduplicated_centavos"].isna()
        control_columns = ["uf", "party_code", "age_at_election", "gender", "race", "schooling"]
        missing_controls = frame[control_columns].isna().any(axis=1)
        missing_controls_by_field = {column: int(frame[column].isna().sum()) for column in control_columns}
        exclusion_overlap = int((missing_final_expense & missing_controls).sum())
        zero_nominal_votes_apto = int(frame["valid_nominal_votes"].eq(0).sum())
        if model_frame.empty:
            raise ValueError("nenhuma candidatura completa para os modelos definidos no protocolo")
        coefficients: list[dict[str, Any]] = []
        models: list[dict[str, Any]] = []
        fitted_models: dict[str, tuple[Any, pd.DataFrame, str]] = {}
        model_specs = (
            ("deduplicado_completo", "expense_deduplicated_centavos", True, False, True),
            ("todas_as_linhas_completo", "expense_all_lines_centavos", True, False, True),
            ("deduplicado_uf_partido", "expense_deduplicated_centavos", False, False, False),
            ("deduplicado_interacao_sexo", "expense_deduplicated_centavos", True, True, True),
            ("todas_as_linhas_interacao_sexo", "expense_all_lines_centavos", True, True, True),
        )
        for name, expense_column, full_controls, interaction, include_age in model_specs:
            required_columns = [expense_column, "uf", "party_code"]
            if include_age:
                required_columns.append("age_at_election")
            if full_controls:
                required_columns.extend(["gender", "race", "schooling"])
            selected = frame.loc[frame[required_columns].notna().all(axis=1)].copy()
            selected["log1p_expense_brl"] = selected[expense_column].astype(float).div(100).map(math.log1p)
            model, estimates, fitted, fitted_frame = _fit_model(name, selected, full_controls, interaction, include_age)
            model["expense_scenario"] = "deduplicado" if "deduplicado" in name else "todas as linhas"
            models.append(model)
            coefficients.extend(estimates)
            fitted_models[name] = (fitted, fitted_frame, expense_column)
        ols_frame = model_frame.copy()
        ols_frame["log1p_expense_brl"] = ols_frame["expense_deduplicated_centavos"].astype(float).div(100).map(math.log1p)
        ols_frame["log1p_nominal_votes"] = ols_frame["valid_nominal_votes"].astype(float).map(math.log1p)
        for name, response in (
            ("deduplicado_ols_participacao", "vote_share"),
            ("deduplicado_votos_brutos_log1p", "log1p_nominal_votes"),
        ):
            model, estimates = _fit_ols_sensitivity(name, ols_frame, response)
            model["expense_scenario"] = "deduplicado"
            models.append(model)
            coefficients.extend(estimates)
        prediction_tables, model_diagnostics, calibration_rows, influence_rows = (
            _build_prediction_and_diagnostic_tables(fitted_models, model_frame)
        )
        interaction_model = next(model for model in models if model["name"] == "deduplicado_interacao_sexo")
        gender_counts = model_frame["gender"].value_counts(dropna=False).to_dict()
        gender_analysis_n = int(model_frame["gender"].isin(["FEMININO", "MASCULINO"]).sum())
        expense_scenarios = {}
        for label, column in (("deduplicado", "expense_deduplicated_centavos"), ("todas_as_linhas", "expense_all_lines_centavos")):
            observed = [candidate.get(column) for candidate in candidate_rows if candidate.get(column) is not None]
            expense_scenarios[label] = {
                "total_centavos": int(sum(observed)),
                "candidates_with_final_expenses": len(observed),
                "observed_zero_candidates": sum(value == 0 for value in observed),
                "absent_candidates": len(apto) - len(observed),
            }
        expense_sensitivity_difference_centavos = (
            expense_scenarios["todas_as_linhas"]["total_centavos"]
            - expense_scenarios["deduplicado"]["total_centavos"]
        )
        payment_source = validation.get("source_details", {}).get("accounts_2022", {})
        paid_members = {
            member
            for member in payment_source.get("selected_members", []) + payment_source.get("excluded_aggregate_or_document_members", [])
            if "despesas_pagas" in member.casefold()
        }
        payment_archive_checked = False
        payment_archive_path = payment_source.get("archive")
        if payment_archive_path and Path(payment_archive_path).is_file():
            try:
                with zipfile.ZipFile(payment_archive_path) as archive:
                    paid_members = {name for name in archive.namelist() if "despesas_pagas" in name.casefold()}
                payment_archive_checked = True
            except zipfile.BadZipFile:
                payment_archive_checked = False
        paid_members = sorted(paid_members)
        vote_observed = sum(candidate["sq_candidate"] in vote_totals for candidate in apto)
        payments_integrated = bool(payment_tables)
        reconciliation = validation.get("reconciliation", {})
        nominal_by_uf = reconciliation.get("nominal_votes_by_uf", {})
        fatal_counts = validation.get("fatal_counts", {})
        pipeline_validation = {
            "status": validation.get("status"),
            "fatal_counts": fatal_counts,
            "fatal_count_total": sum(int(value) for value in fatal_counts.values()),
            "warnings": validation.get("warnings", {}),
            "expense_rows_reconciled": None
            if not reconciliation.get("expense_rows_source_vs_aggregate")
            else reconciliation["expense_rows_source_vs_aggregate"][0] == reconciliation["expense_rows_source_vs_aggregate"][1],
            "expense_amount_reconciled": None
            if not reconciliation.get("expense_centavos_source_vs_aggregate")
            else reconciliation["expense_centavos_source_vs_aggregate"][0] == reconciliation["expense_centavos_source_vs_aggregate"][1],
            "vote_rows_reconciled": None
            if not reconciliation.get("vote_rows_source_vs_aggregate")
            else reconciliation["vote_rows_source_vs_aggregate"][0] == reconciliation["vote_rows_source_vs_aggregate"][1],
            "vote_totals_reconciled": None
            if not reconciliation.get("vote_valid_votes_source_vs_aggregate")
            else reconciliation["vote_valid_votes_source_vs_aggregate"][0] == reconciliation["vote_valid_votes_source_vs_aggregate"][1],
            "nominal_votes_reconciled_by_uf": bool(nominal_by_uf)
            and all(row["party_source"] == row["candidate_source"] for row in nominal_by_uf.values()),
            "nominal_uf_count": len(nominal_by_uf),
        }
        result: dict[str, Any] = {
            "manifest_id": validation.get("manifest_id"),
            "source_metadata": source_metadata,
            "pipeline_validation": pipeline_validation,
            "population": {
                "apto_candidates": len(apto),
                "inapto_candidates": len(inapto),
                "apto_with_official_denominator_and_observed_votes": len(candidate_rows),
                "apto_without_official_denominator_or_observed_votes": len(apto) - len(candidate_rows),
                "apto_zero_nominal_votes": zero_nominal_votes_apto,
            },
            "outcome": "votos nominais válidos do candidato / total oficial de votos válidos por UF (nominais + legenda)",
            "vote_denominator_uf_count": len(vote_denominator_rows),
            "official_nominal_votes_national_total": sum(row["valid_nominal_votes"] for row in vote_denominator_rows),
            "official_legend_votes_national_total": sum(row["valid_legend_votes"] for row in vote_denominator_rows),
            "official_valid_votes_national_total": sum(row["valid_votes_total"] for row in vote_denominator_rows),
            "vote_denominators_by_uf": vote_denominator_rows,
            "expense_measure": "VR_DESPESA_CONTRATADA em prestações Final, BRL, transformação log(1 + despesa); zeros observados preservados; ausência excluída da regressão",
            "expense_scenarios": expense_scenarios,
            "expense_sensitivity_difference_centavos": expense_sensitivity_difference_centavos,
            "model_complete_case_n": len(model_frame),
            "model_complete_case_exclusions": len(apto) - len(model_frame),
            "model_exclusion_reasons": {
                "apto_without_final_expense": int(missing_final_expense.sum()),
                "apto_with_missing_controls": int(missing_controls.sum()),
                "overlap": exclusion_overlap,
            },
            "missing_controls_by_field": missing_controls_by_field,
            "gender_comparison": {
                "women_and_men_n": gender_analysis_n,
                "other_or_missing_gender_excluded_from_interaction": len(model_frame) - gender_analysis_n,
                "counts_in_main_complete_case": {str(key): int(value) for key, value in gender_counts.items()},
                "interaction_model": interaction_model["name"],
                "interpretation": "associação não causal; a inclinação pode variar entre mulheres e homens",
            },
            "prediction_tables": prediction_tables,
            "model_diagnostics": model_diagnostics,
            "calibration_deciles": calibration_rows,
            "influence_top_candidates": influence_rows,
            "models": models,
            "coefficients": coefficients,
            "apto_expenses_by_type": apto_rows,
            "apto_expense_survey": apto_expense_summary,
            "inapto_expenses_by_type": inapto_rows,
            "inapto_expense_survey": inapto_summary,
            "payment_integration": {
                "integrated_in_analysis_database": payments_integrated,
                "payment_related_tables": payment_tables,
                "frozen_archive_checked": payment_archive_checked,
                "frozen_archive_payment_members": paid_members,
                "status": (
                    "integrado"
                    if payments_integrated
                    else (
                        f"não integrado: {len(paid_members)} membros de despesas pagas estão no ZIP congelado; não há tabela de pagamentos na base derivada, e essa integração complementar não bloqueia a análise contratada"
                        if paid_members
                        else "não integrado; não foi identificado membro de despesas pagas no ZIP congelado; a integração complementar não bloqueia a análise contratada"
                    )
                ),
            },
            "vote_observations_for_apto": vote_observed,
            "limitations": [
                "A situação APTO é a registrada no snapshot; não prova elegibilidade jurídica na data da eleição.",
                "Despesas são valores declarados contratados, não pagamentos efetivos.",
                "Deduplicar igualdade integral nas 53 colunas originais é uma escolha metodológica; não confirma identidade econômica das repetições.",
                "Todas as linhas permanecem como sensibilidade. Diferença não significa desperdício ou irregularidade.",
                "Modelos observacionais não estimam efeito causal; qualidade do candidato, incumbência, apoio, geografia e competitividade podem confundir a associação.",
                "Votos por UF são agregados eleitorais; os resultados não descrevem decisões individuais de eleitores.",
            ],
        }
    finally:
        connection.close()

    _write_csv(
        output_dir / "tse-2022-vote-denominator-by-uf.csv",
        result["vote_denominators_by_uf"],
        ["uf", "election_year", "turn", "cargo_code", "cargo", "valid_nominal_votes", "valid_legend_votes", "valid_votes_total", "source_row_count", "source_archive", "source_member"],
    )
    _write_csv(
        output_dir / "tse-2022-financial-model-estimates.csv",
        result["coefficients"],
        ["model", "term", "coefficient", "robust_se_hc1", "ci95_low", "ci95_high", "p_value"],
    )
    _write_csv(
        output_dir / "tse-2022-predicted-expense-scenarios.csv",
        result["prediction_tables"]["scenario_comparison"],
        ["expense_level", "expense_quantile", "expense_brl", "deduplicated_prediction", "deduplicated_ci95_lower", "deduplicated_ci95_upper", "all_rows_prediction", "all_rows_ci95_lower", "all_rows_ci95_upper", "difference_percentage_points", "standardization_n"],
    )
    _write_csv(
        output_dir / "tse-2022-sex-interaction-curve.csv",
        result["prediction_tables"]["sex_interaction_curve"]["points"],
        ["expense_brl", "male_prediction", "male_ci95_lower", "male_ci95_upper", "female_prediction", "female_ci95_lower", "female_ci95_upper", "female_minus_male_percentage_points"],
    )
    _write_csv(
        output_dir / "tse-2022-model-calibration-deciles.csv",
        result["calibration_deciles"],
        ["model", "decile", "n", "mean_observed_vote_share", "mean_predicted_vote_share", "calibration_gap"],
    )
    _write_csv(
        output_dir / "tse-2022-model-influence-top-candidates.csv",
        result["influence_top_candidates"],
        ["model", "rank", "sq_candidate", "expense_brl", "observed_vote_share", "fitted_vote_share", "cooks_distance", "leverage", "dfbeta_log1p_expense"],
    )
    _write_csv(
        output_dir / "tse-2022-top-one-percent-expense-sensitivity.csv",
        result["model_diagnostics"]["top_one_percent_expense_sensitivity"],
        ["scenario", "cutoff_rule", "cutoff_brl", "excluded_candidates", "n_after_exclusion", "full_coefficient", "trimmed_coefficient", "trimmed_ci95_lower", "trimmed_ci95_upper", "coefficient_change", "full_ci95_lower", "full_ci95_upper"],
    )
    submission_fields = [
        "tp_prestacao_contas", "candidate_status_code", "candidate_count",
        "candidates_with_rows", "candidates_without_rows", "candidates_with_zero_total",
        "all_lines_occurrence_rows", "all_lines_zero_amount_rows",
        "all_lines_declared_expense_centavos", "deduplicated_occurrence_rows",
        "deduplicated_candidates_with_rows", "deduplicated_declared_expense_centavos",
        "excluded_occurrence_rows", "excluded_amount_centavos",
        "excluded_affected_candidates",
    ]
    _write_csv(output_dir / "tse-2022-apto-expenses-by-type.csv", apto_rows, submission_fields)
    _write_csv(output_dir / "tse-2022-inapto-expenses-by-type.csv", inapto_rows, submission_fields)
    (output_dir / "tse-2022-financial-analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    main_expense_estimate = next(
        estimate for estimate in result["coefficients"]
        if estimate["model"] == "deduplicado_completo" and estimate["term"] == "log1p_expense_brl"
    )
    all_rows_expense_estimate = next(
        estimate for estimate in result["coefficients"]
        if estimate["model"] == "todas_as_linhas_completo" and estimate["term"] == "log1p_expense_brl"
    )
    reduced_expense_estimate = next(
        estimate for estimate in result["coefficients"]
        if estimate["model"] == "deduplicado_uf_partido" and estimate["term"] == "log1p_expense_brl"
    )
    reduced_model_n = next(model["n"] for model in models if model["name"] == "deduplicado_uf_partido")
    female_slope_difference = next(
        estimate for estimate in result["coefficients"]
        if estimate["model"] == "deduplicado_interacao_sexo" and estimate["term"] == "expense_x_female"
    )
    missing_control_summary = ", ".join(
        f"{column}={_pt_int(count)}"
        for column, count in missing_controls_by_field.items()
        if count
    ) or "nenhum"
    report_lines = [
        "# Análise financeira TSE 2022 — deputado federal, 1º turno",
        "",
        f"Versão de dados: `{result['manifest_id']}`.",
        "",
        "## Escopo e método",
        "",
        f"População: {_pt_int(len(apto))} candidaturas APTO no snapshot; {_pt_int(len(inapto))} candidaturas INAPTO levantadas separadamente. A situação do snapshot não é uma conclusão jurídica sobre a data da eleição.",
        f"Desfecho: {result['outcome']}. O denominador oficial foi reconciliado antes dos filtros de situação e tipo de prestação.",
        f"Exposição: {result['expense_measure']}. Principal: despesas deduplicadas; sensibilidade: todas as linhas. A regra compara os 53 campos TSE no mesmo snapshot e membro, excluindo auditoria; não prova identidade econômica.",
        f"Denominador oficial: {_pt_int(result['official_valid_votes_national_total'])} votos válidos — {_pt_int(result['official_nominal_votes_national_total'])} nominais + {_pt_int(result['official_legend_votes_national_total'])} de legenda — nas 27 UFs. Origem congelada: `{result['source_metadata']['official_source_url'] or 'fonte registrada no manifesto'}`, ZIP `{result['source_metadata']['frozen_zip'] or 'manifesto'}`, SHA-256 `{result['source_metadata']['sha256'] or 'manifesto'}`, {_pt_int(result['source_metadata']['size_bytes']) if result['source_metadata']['size_bytes'] else 'tamanho registrado no manifesto'} bytes.",
        "Escopo da fonte: deputado federal, primeiro turno de 2022; votos nominais e de legenda incluídos.",
        f"Cobertura de votos em APTO: {_pt_int(result['population']['apto_with_official_denominator_and_observed_votes'])}/{_pt_int(result['population']['apto_candidates'])} com denominador e votos observados; {_pt_int(result['population']['apto_without_official_denominator_or_observed_votes'])} sem cobertura; {_pt_int(result['population']['apto_zero_nominal_votes'])} com zero voto nominal.",
        f"Validação do pipeline: {result['pipeline_validation']['status']}; {_pt_int(result['pipeline_validation']['fatal_count_total'])} contagens fatais. Reconciliações de linhas/valores de despesas e votos: {'/'.join(_pt_bool(result['pipeline_validation'][key]) for key in ('expense_rows_reconciled', 'expense_amount_reconciled', 'vote_rows_reconciled', 'vote_totals_reconciled'))}; votos nominais coincidem por UF: {_pt_bool(result['pipeline_validation']['nominal_votes_reconciled_by_uf'])} ({_pt_int(result['pipeline_validation']['nominal_uf_count'])} UFs).",
        "Modelo principal: GLM binomial/logit para participação fracionária, com erros-padrão robustos HC1. Modelo completo ajusta UF, partido, idade, sexo, raça e escolaridade; comparação reduzida ajusta UF e partido. Não se combina partido e federação.",
        "A análise é associação, não causalidade; confundimento por qualidade do candidato, incumbência, apoio partidário, geografia e competitividade permanece possível. Sexo não feminino/masculino e ausência de sexo ficam fora apenas da interação; o modelo completo mantém categorias informadas.",
        "",
        "## Cobertura, zeros e totais de despesas Final entre APTO",
        "",
        "| Cenário | Total declarado (R$) | Candidatos com despesa Final | Total observado zero | Sem linha Final |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, key in (("Deduplicado (principal)", "deduplicado"), ("Todas as linhas (sensibilidade)", "todas_as_linhas")):
        value = expense_scenarios[key]
        report_lines.append(
            f"| {label} | {_pt_brl_centavos(value['total_centavos'])} | {_pt_int(value['candidates_with_final_expenses'])} | {_pt_int(value['observed_zero_candidates'])} | {_pt_int(value['absent_candidates'])} |"
        )
    report_lines.extend([
        "",
        "## Demais tipos de prestação entre APTO",
        "",
        "Os outros tipos são apresentados separados de `Final`; o critério não infere qual entrega foi recebida por último.",
        "",
        "| Tipo | Candidatos com linha | Sem linha | Linhas todas | Total todas (R$) | Linhas deduplicadas | Total deduplicado (R$) | Linhas excluídas | Candidatos afetados |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in apto_rows:
        report_lines.append(
            f"| {row['tp_prestacao_contas']} | {_pt_int(row['candidates_with_rows'])} | {_pt_int(row['candidates_without_rows'])} | {_pt_int(row['all_lines_occurrence_rows'])} | {_pt_brl_centavos(row['all_lines_declared_expense_centavos'])} | {_pt_int(row['deduplicated_occurrence_rows'])} | {_pt_brl_centavos(row['deduplicated_declared_expense_centavos'])} | {_pt_int(row['excluded_occurrence_rows'])} | {_pt_int(row['excluded_affected_candidates'])} |"
        )
    report_lines.extend([
        "",
        f"Modelos completos, interações e sensibilidades OLS usam {_pt_int(len(model_frame))} candidaturas com despesas Final, votos e controles completos; {_pt_int(len(apto) - len(model_frame))} APTO ficam fora desses modelos: {_pt_int(int(missing_final_expense.sum()))} sem linha Final, {_pt_int(int(missing_controls.sum()))} com algum controle ausente (sobreposição {_pt_int(exclusion_overlap)}; campos: {missing_control_summary}). Zero de despesa e {_pt_int(zero_nominal_votes_apto)} votos nominais iguais a zero são mantidos; ausência de linha não vira zero.",
        f"O modelo de comparação com ajuste apenas por UF/partido, sem idade, usa N={_pt_int(next(model['n'] for model in models if model['name'] == 'deduplicado_uf_partido'))}.",
        f"Entre APTO, preservar todas as ocorrências soma R$ {_pt_brl_centavos(expense_scenarios['todas_as_linhas']['total_centavos'])}; a base principal deduplicada soma R$ {_pt_brl_centavos(expense_scenarios['deduplicado']['total_centavos'])}. Diferença: R$ {_pt_brl_centavos(expense_sensitivity_difference_centavos)}; não é classificação de gasto indevido.",
        "",
        "## Modelos estimados",
        "",
        "| Modelo | N | Família | Desfecho | Controles |",
        "|---|---:|---|---|---|",
    ])
    for model in models:
        report_lines.append(f"| {model['name']} | {_pt_int(model['n'])} | {model['family']} | {model.get('outcome', 'participação de votos fracionária')} | {', '.join(model['controls'])}{'; interação despesa×mulher' if model['interaction'] else ''} |")
    report_lines.append(
        f"Diagnósticos: {_pt_int(sum(bool(model['converged']) for model in models))}/{_pt_int(len(models))} convergiram e todas as matrizes passaram a verificação de posto. Adequação, calibração e influência estão detalhadas abaixo; não há validação externa."
    )
    report_lines.extend([
        "",
        f"Na amostra completa, {_pt_int(gender_analysis_n)} candidaturas com sexo informado como feminino/masculino entram na interação; {_pt_int(len(model_frame) - gender_analysis_n)} com outra categoria/ausente ficam fora apenas dessa comparação.",
        f"No GLM completo, o coeficiente de `log1p(despesa)` foi {_pt_decimal(main_expense_estimate['coefficient'], 3)} (IC 95% HC1 {_pt_decimal(main_expense_estimate['ci95_low'], 3)} a {_pt_decimal(main_expense_estimate['ci95_high'], 3)}) no cenário deduplicado e {_pt_decimal(all_rows_expense_estimate['coefficient'], 3)} ({_pt_decimal(all_rows_expense_estimate['ci95_low'], 3)} a {_pt_decimal(all_rows_expense_estimate['ci95_high'], 3)}) com todas as linhas. Ambos indicam associação positiva ajustada na escala logit; isso não demonstra que mais despesa cause mais votos.",
        f"Com ajuste somente por UF/partido, sem idade (N={_pt_int(reduced_model_n)}), o coeficiente de `log1p(despesa)` foi {_pt_decimal(reduced_expense_estimate['coefficient'], 3)} (IC 95% HC1 {_pt_decimal(reduced_expense_estimate['ci95_low'], 3)} a {_pt_decimal(reduced_expense_estimate['ci95_high'], 3)}).",
        f"Na interação planejada, a diferença de inclinação mulheres–homens foi {_pt_decimal(female_slope_difference['coefficient'], 3)} na escala logit (IC 95% HC1 {_pt_decimal(female_slope_difference['ci95_low'], 3)} a {_pt_decimal(female_slope_difference['ci95_high'], 3)}). É uma diferença associativa, não causal.",
        "Consulte `tse-2022-financial-model-estimates.csv` para todos os coeficientes e valores-p. GLM está em escala logit; OLS está em escala linear do desfecho informado. As estimativas são associativas, não causais.",
        "",
    ])
    report_lines.extend([
        "",
        "## Participação prevista em níveis comparáveis de despesa",
        "",
        "As previsões são médias padronizadas: fixa-se a despesa no nível indicado e calcula-se a participação de votos prevista para cada candidatura da distribuição comum de controles completos, depois se tira a média. São associações ajustadas, não previsões causais nem resultados eleitorais individuais. ICs de 95% pontuais pelo método delta, usando a covariância sanduíche HC1; não são intervalos para candidaturas individuais. A diferença entre cenários é apresentada em pontos percentuais como diferença de estimativas pontuais, sem IC próprio.",
        "",
        "| Despesa contratada | Deduplicado: participação prevista (IC 95%) | Todas as linhas: participação prevista (IC 95%) | Diferença todas − deduplicado (p.p.) |",
        "|---|---:|---:|---:|",
    ])
    for row in prediction_tables["scenario_comparison"]:
        expense = f"R$ {_pt_decimal(row['expense_brl'], 2)} ({row['expense_level']})"
        dedup = f"{_pt_decimal(row['deduplicated_prediction'] * 100, 4)}% ({_pt_decimal(row['deduplicated_ci95_lower'] * 100, 4)}–{_pt_decimal(row['deduplicated_ci95_upper'] * 100, 4)}%)"
        all_lines = f"{_pt_decimal(row['all_rows_prediction'] * 100, 4)}% ({_pt_decimal(row['all_rows_ci95_lower'] * 100, 4)}–{_pt_decimal(row['all_rows_ci95_upper'] * 100, 4)}%)"
        report_lines.append(
            f"| {expense} | {dedup} | {all_lines} | {_pt_decimal(row['difference_percentage_points'], 5)} |"
        )
    curve = prediction_tables["sex_interaction_curve"]
    support = curve["common_support"]
    report_lines.extend([
        "",
        "## Comparação mulheres–homens dentro do suporte comum",
        "",
        f"A curva usa apenas despesas dentro da interseção das faixas P5–P95 dos dois grupos: R$ {_pt_decimal(support['lower_brl'], 2)} a R$ {_pt_decimal(support['upper_brl'], 2)}. Em cada nível, fixa-se a despesa e alterna-se o sexo na mesma distribuição de controles; os ICs de 95% são pontuais e pelo método delta/HC1.",
        "Na codificação, homens são a referência (indicador `female=0`); `log1p(despesa)` é a inclinação associativa masculina e `expense_x_female` acrescenta a diferença de inclinação para mulheres na escala logit. A inclinação feminina é a soma dos dois coeficientes. Como o logit inverso é não linear, o coeficiente de interação não equivale a uma porcentagem de gasto necessária; compare as curvas previstas.",
        "",
        "| Despesa (R$) | Homens: participação prevista (IC 95%) | Mulheres: participação prevista (IC 95%) | Diferença mulheres − homens (p.p.) |",
        "|---:|---:|---:|---:|",
    ])
    for row in curve["points"]:
        male = f"{_pt_decimal(row['male_prediction'] * 100, 2)}% ({_pt_decimal(row['male_ci95_lower'] * 100, 2)}–{_pt_decimal(row['male_ci95_upper'] * 100, 2)}%)"
        female = f"{_pt_decimal(row['female_prediction'] * 100, 2)}% ({_pt_decimal(row['female_ci95_lower'] * 100, 2)}–{_pt_decimal(row['female_ci95_upper'] * 100, 2)}%)"
        report_lines.append(
            f"| {_pt_decimal(row['expense_brl'], 2)} | {male} | {female} | {_pt_decimal(row['female_minus_male_percentage_points'], 2)} |"
        )
    report_lines.extend([
        "",
        "## Adequação do ajuste e influência",
        "",
        "RMSE e MAE medem o erro médio entre participação observada e ajustada, em pontos percentuais; a calibração agrupa as previsões em decis e compara médias observadas e previstas. São verificações dentro da própria amostra, não validação fora da amostra. Influência: distância de Cook, alavancagem e DFBETA do coeficiente de despesa. O limite Cook > 4/N é apenas uma triagem heurística; nenhum caso foi excluído automaticamente.",
        "",
        "| Cenário | RMSE (p.p.) | MAE (p.p.) | Maior diferença de calibração por decil (p.p.) | Cook > 4/N | Maior Cook | Maior alavancagem | Maior valor absoluto de DFBETA da despesa |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for model_name in ("deduplicado_completo", "todas_as_linhas_completo"):
        diagnostic = model_diagnostics[model_name]
        fit = diagnostic["fit"]
        influence = diagnostic["influence"]
        max_dfbeta = influence["maximum_absolute_expense_dfbeta"]
        report_lines.append(
            f"| {model_name} | {_pt_decimal(fit['rmse'] * 100, 2)} | {_pt_decimal(fit['mae'] * 100, 2)} | {_pt_decimal(fit['max_absolute_decile_calibration_gap'] * 100, 2)} | {_pt_int(influence['candidates_above_cook_screen'])} (limite {_pt_decimal(influence['cook_distance_screen_threshold'], 4)}) | {_pt_decimal(influence['maximum_cook_distance'], 4)} | {_pt_decimal(influence['maximum_leverage'], 4)} | {_pt_decimal(max_dfbeta, 4)} |"
        )
    report_lines.extend([
        "",
        "A sensibilidade abaixo remove somente candidaturas acima do P99 da despesa deduplicada, para verificar a estabilidade da inclinação de despesa. A amostra principal permanece intacta; a regra não identifica erro nem gasto indevido. As listas de calibração por decil e os 10 casos de maior Cook por cenário estão nos CSVs de diagnóstico.",
        "",
        "| Cenário | Corte P99 (R$) | Excluídos na sensibilidade | N após corte | Coeficiente principal | Coeficiente sem cauda (IC 95% HC1) | Mudança |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in model_diagnostics["top_one_percent_expense_sensitivity"]:
        trimmed_ci = f"{_pt_decimal(row['trimmed_coefficient'], 3)} ({_pt_decimal(row['trimmed_ci95_lower'], 3)}–{_pt_decimal(row['trimmed_ci95_upper'], 3)})"
        report_lines.append(
            f"| {row['scenario']} | {_pt_decimal(row['cutoff_brl'], 2)} | {_pt_int(row['excluded_candidates'])} | {_pt_int(row['n_after_exclusion'])} | {_pt_decimal(row['full_coefficient'], 3)} | {trimmed_ci} | {_pt_decimal(row['coefficient_change'], 3)} |"
        )
    report_lines.extend([
        "",
        "Arquivos: `tse-2022-predicted-expense-scenarios.csv`, `tse-2022-sex-interaction-curve.csv`, `tse-2022-model-calibration-deciles.csv`, `tse-2022-model-influence-top-candidates.csv` e `tse-2022-top-one-percent-expense-sensitivity.csv`. As curvas mostram médias previstas ajustadas; toda interpretação é associativa.",
        "",
    ])
    report_lines.extend([
        "## INAPTO — levantamento separado por tipo de prestação",
        "",
        f"Entre {_pt_int(inapto_summary['candidate_count'])} candidaturas INAPTO, {_pt_int(inapto_summary['candidates_with_any_expense_rows'])} têm ao menos uma ocorrência e {_pt_int(inapto_summary['candidates_without_any_expense_rows'])} não têm linha de despesa na base. A tabela usa ocorrências intactas e também mostra o cenário deduplicado; não mistura INAPTO à regressão APTO.",
        "",
        "| Tipo | Candidatos com linha | Sem linha | Linhas todas | Linhas zero | Total todas (R$) | Linhas deduplicadas | Total deduplicado (R$) | Linhas excluídas | Candidatos afetados |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in inapto_rows:
        report_lines.append(
            f"| {row['tp_prestacao_contas']} | {_pt_int(row['candidates_with_rows'])} | {_pt_int(row['candidates_without_rows'])} | {_pt_int(row['all_lines_occurrence_rows'])} | {_pt_int(row['all_lines_zero_amount_rows'])} | {_pt_brl_centavos(row['all_lines_declared_expense_centavos'])} | {_pt_int(row['deduplicated_occurrence_rows'])} | {_pt_brl_centavos(row['deduplicated_declared_expense_centavos'])} | {_pt_int(row['excluded_occurrence_rows'])} | {_pt_int(row['excluded_affected_candidates'])} |"
        )
    report_lines.extend([
        "",
        "## Pagamentos e limitações",
        "",
        result["payment_integration"]["status"] + ".",
    ])
    report_lines.extend(f"- {limitation}" for limitation in result["limitations"])
    report_lines.extend([
        "",
        "## Reprodução",
        "",
        "```sh",
        "python -m tse_pilot analyze --database data/derived/2022/pilot.sqlite --validation data/derived/2022/validation.json --output reports",
        "```",
        "",
        "A saída JSON registra contagens, modelos, metadados de execução e limitações; os coeficientes e o levantamento INAPTO também são arquivos CSV.",
        "",
    ])
    (output_dir / "tse-2022-financial-analysis.md").write_text("\n".join(report_lines), encoding="utf-8")
    return result
