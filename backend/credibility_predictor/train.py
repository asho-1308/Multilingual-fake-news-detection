import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib

# Load the dataset
filename = 'sample_dataset.csv'
df = pd.read_csv(filename)
print("Dataset loaded successfully.")

# Select Features and Target
features = ['past_fake', 'past_real', 'domain_age_years', 'followers', 'language']
target = 'credibility_label'

X = df[features].copy()
y = df[target]

# Preprocessing
lang_encoder = LabelEncoder()
X['language'] = lang_encoder.fit_transform(X['language'])

# Split into Training and Testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the Random Forest Model
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# Evaluate the Model
y_pred = rf_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\nModel Training Complete.")
print(f"Accuracy on Test Set: {accuracy * 100:.2f}%")
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# Save the model and the encoder
model_filename = 'credibility_rf_model.pkl'
encoder_filename = 'lang_encoder.pkl'

joblib.dump(rf_model, model_filename)
joblib.dump(lang_encoder, encoder_filename)

print(f"Model saved as '{model_filename}'")
print(f"Encoder saved as '{encoder_filename}'")