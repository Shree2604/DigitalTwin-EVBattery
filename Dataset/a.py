# ============================================================
#   RUL PREDICTION — LSTM / BiLSTM / GRU / TCN COMPARISON
#   Timestamp handled, unwanted columns removed
# ============================================================

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, GRU, Bidirectional, Dense, Dropout
from tcn import TCN  # pip install keras-tcn

# ============================================================
# 1. LOAD DATA
# ============================================================
df = pd.read_csv("Dataset.csv")  # Change filename if needed

print("Original columns:", df.columns.tolist())

# ============================================================
# 2. REMOVE UNWANTED TARGET COLUMNS
# ============================================================
remove_cols = [
    "Failure_Probability",
    "TTF",
    "Component_Health_Score"
]

for col in remove_cols:
    if col in df.columns:
        df.drop(columns=[col], inplace=True)

print("Columns after removing FP, TTF, CHS:", df.columns.tolist())

# ============================================================
# 3. HANDLE TIMESTAMP
# ============================================================
if "Timestamp" in df.columns:
    # Convert to datetime safely
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%Y-%m-%d %H:%M:%S")

    # Convert to numeric time index (minutes from start)
    df["Timestamp"] = (df["Timestamp"] - df["Timestamp"].min()).dt.total_seconds() / 60.0

# ============================================================
# 4. PREPROCESSING
# ============================================================

# Encode Maintenance_Type if exists
if "Maintenance_Type" in df.columns:
    le = LabelEncoder()
    df["Maintenance_Type"] = le.fit_transform(df["Maintenance_Type"])

# Target variable
y = df["RUL"].values

# Input features X
X = df.drop("RUL", axis=1)

# Scaling inputs
scaler = RobustScaler()
X_scaled = scaler.fit_transform(X)

# ============================================================
# 5. CREATE TIME-SERIES SEQUENCES
# ============================================================

SEQ_LEN = 30  # 30 time steps

def make_sequences(data, labels, seq_len):
    Xs, ys = [], []
    for i in range(len(data) - seq_len):
        Xs.append(data[i:i+seq_len])
        ys.append(labels[i+seq_len])
    return np.array(Xs), np.array(ys)

X_seq, y_seq = make_sequences(X_scaled, y, SEQ_LEN)

print("Sequence shape:", X_seq.shape)

# Split (no shuffle for time-series)
X_train, X_test, y_train, y_test = train_test_split(
    X_seq, y_seq, test_size=0.2, shuffle=False
)

# ============================================================
# 6. MODEL DEFINITIONS
# ============================================================

input_shape = (X_train.shape[1], X_train.shape[2])

def build_lstm(input_shape):
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(64),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model

def build_bilstm(input_shape):
    model = Sequential([
        Bidirectional(LSTM(128, return_sequences=True)),
        Dropout(0.2),
        Bidirectional(LSTM(64)),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model

def build_gru(input_shape):
    model = Sequential([
        GRU(128, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        GRU(64),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model

def build_tcn(input_shape):
    model = Sequential([
        TCN(input_shape=input_shape, dropout_rate=0.2),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model

# ============================================================
# 7. TRAIN MODELS
# ============================================================

models = {
    "LSTM": build_lstm(input_shape),
    "BiLSTM": build_bilstm(input_shape),
    "GRU": build_gru(input_shape),
    "TCN": build_tcn(input_shape)
}

results = {}

for name, model in models.items():
    print(f"\n==============================")
    print(f" Training Model: {name}")
    print(f"==============================")

    model.fit(
        X_train, y_train,
        epochs=15,
        batch_size=64,
        validation_split=0.2,
        verbose=1
    )

    loss, mae = model.evaluate(X_test, y_test, verbose=0)
    results[name] = mae
    print(f"{name} Test MAE: {mae}")

# ============================================================
# 8. MODEL COMPARISON TABLE
# ============================================================

print("\n\n==============================")
print("   MODEL COMPARISON (MAE)")
print("==============================")
for name, mae in results.items():
    print(f"{name:10s} : {mae:.4f}")

best_model = min(results, key=results.get)
print("\nBEST MODEL FOR RUL PREDICTION:", best_model)
