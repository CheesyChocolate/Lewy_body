"""Stage 6: nested-cross-validation classifier.

Demircioglu 2021/2024 (docs/preliminary_research/, docs/todo.md) found that feature
selection or class-balancing performed outside a per-fold nested CV loop inflates
reported AUC-ROC by up to 0.15 / accuracy by up to 0.17, an effect that grows with a
high feature-to-subject ratio and class imbalance -- both apply here (hundreds of
pyradiomics features per ROI, 126 SAA-positive vs. ~400 SAA-negative). So SelectKBest
feature selection and SMOTE oversampling are both refit independently inside every
training fold, never on the full dataset up front.

Model choice (L1-regularized logistic regression + SelectKBest pre-filter): simple,
interpretable, and its embedded L1 sparsity suits a high-feature/low-subject regime
better than an unregularized model (user decision, 2026-08-26; no specific classifier is
mandated by the literature review, only that it be nested). See docs/DECISIONS.md.
"""

from __future__ import annotations

import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler


def build_pipeline(random_state: int = 0) -> ImbPipeline:
    """Impute -> scale -> SelectKBest -> SMOTE -> L1 logistic regression.

    A single fold's worth of preprocessing + model, meant to be re-fit independently
    inside every outer-fold training split by nested_cv (never on the full dataset).
    """
    return ImbPipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("select", SelectKBest(score_func=f_classif)),
            ("smote", SMOTE(random_state=random_state)),
            (
                "clf",
                LogisticRegression(
                    penalty="l1",
                    solver="liblinear",
                    max_iter=5000,
                    random_state=random_state,
                ),
            ),
        ]
    )


def nested_cv(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    outer_folds: int = 5,
    inner_folds: int = 5,
    k_features_grid: tuple[int, ...] = (20, 50, 100),
    c_grid: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0),
    random_state: int = 0,
) -> pd.DataFrame:
    """Nested CV: outer loop reports generalization performance, inner loop (GridSearchCV)
    tunes k_features/C. Returns one row per outer fold, not a single point estimate --
    a low-hundreds-subject cohort gives inherently unstable single-split estimates
    (docs/preliminary_research), so the fold-level distribution is the actual result.
    """
    outer_cv = StratifiedKFold(
        n_splits=outer_folds, shuffle=True, random_state=random_state
    )
    param_grid = {"select__k": k_features_grid, "clf__C": c_grid}

    results = []
    for fold_i, (train_idx, test_idx) in enumerate(outer_cv.split(X, y)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        inner_cv = StratifiedKFold(
            n_splits=inner_folds, shuffle=True, random_state=random_state
        )
        search = GridSearchCV(
            build_pipeline(random_state=random_state),
            param_grid,
            cv=inner_cv,
            scoring="roc_auc",
            n_jobs=-1,
        )
        search.fit(X_train, y_train)

        best_model = search.best_estimator_
        y_prob = best_model.predict_proba(X_test)[:, 1]
        y_pred = best_model.predict(X_test)

        results.append(
            {
                "fold": fold_i,
                "best_params": search.best_params_,
                "auc_roc": roc_auc_score(y_test, y_prob),
                "accuracy": accuracy_score(y_test, y_pred),
                "n_test": len(test_idx),
                "n_positive_test": int(y_test.sum()),
            }
        )

    return pd.DataFrame(results)
