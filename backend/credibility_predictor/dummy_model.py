import os

class DummyModel:
    def __init__(self):
        # classes_ order should match how app expects ['High','Low','Medium']
        self.classes_ = ['High', 'Low', 'Medium']

    def _get_row(self, X):
        try:
            row = X.iloc[0].to_dict()
        except Exception:
            try:
                row = X[0]
            except Exception:
                row = {}
        return row

    def predict_proba(self, X):
        row = self._get_row(X)
        followers = float(row.get('followers', 0) or 0)
        past_fake = float(row.get('past_fake', 0) or 0)
        domain_age = float(row.get('domain_age_years', 0) or 0)

        cred_base = min(0.95, followers / (followers + 1_000_000) + domain_age * 0.02)
        cred_base -= min(0.6, past_fake * 0.01)
        cred_base = max(0.0, min(0.99, cred_base))

        high = cred_base
        low = max(0.0, 0.6 - high)
        medium = max(0.0, 1.0 - high - low)

        s = high + medium + low
        high, medium, low = high/s, medium/s, low/s
        return [[high, low, medium]]

    def predict(self, X):
        probs = self.predict_proba(X)[0]
        idx = int(max(range(len(probs)), key=lambda i: probs[i]))
        return [self.classes_[idx]]

class DummyEncoder:
    def __init__(self):
        self.mapping = {
            'tamil': 0,
            'ta': 0,
            'sinhala': 1,
            'si': 1,
            'english': 2,
            'en': 2
        }

    def transform(self, values):
        try:
            return [self.mapping.get(str(v).lower(), 2) for v in values]
        except Exception:
            return [self.mapping.get(str(values).lower(), 2)]
