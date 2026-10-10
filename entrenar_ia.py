import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(42)
N = 8000
SUPERFICIES = np.array([0.8, 0.7, 0.5, 0.2]) # seco, concreto, mojado, barro

# 1) GENERAR DATOS SIMULADOS
mu_real = rng.choice(SUPERFICIES, N) * rng.uniform(0.9, 1.1, N)
# Sensor con error aleatorio del 15%
mu_sensor = rng.normal(mu_real, 0.15 * mu_real)

v0_kmh = rng.uniform(20, 100, N)
theta_deg = rng.uniform(0, 10, N)
masa_kg = rng.uniform(4000, 52000, N)

df = pd.DataFrame({"mu_sensor": mu_sensor, "v0_kmh": v0_kmh, "theta_deg": theta_deg, "masa_kg": masa_kg, "mu_real": mu_real})
df.to_csv("datos_entrenamiento.csv", index=False)

# 2) ENTRENAR (regresión cuantil 10%)
X = df[["mu_sensor", "v0_kmh", "theta_deg", "masa_kg"]].values
y = df["mu_real"].values

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=1)

modelo = GradientBoostingRegressor(loss="quantile", alpha=0.10, n_estimators=150, max_depth=3, random_state=1)
modelo.fit(X_tr, y_tr)

joblib.dump(modelo, "modelo_ia.joblib")

# 3) EVALUAR (Resultados para justificar en el informe)
pred = modelo.predict(X_te)
viejo = X_te[:, 0] - (1.28 * 0.15 * X_te[:, 0]) # Fórmula manual anterior

print("Probabilidad de bloqueo (\u03BC predicho > \u03BC real):")
print(f" Modelo entrenado: {np.mean(pred > y_te):.1%} (objetivo 10%)")
print(f" Fórmula manual: {np.mean(viejo > y_te):.1%}")

print("\nImportancia de cada entrada:")
print(dict(zip(["mu_sensor", "v0_kmh", "theta_deg", "masa_kg"], modelo.feature_importances_.round(3))))

plt.scatter(y_te, pred, s=4, alpha=0.4)
plt.plot([0, 1], [0, 1], "r--", label="predicho = real")
plt.xlabel("\u03BC real")
plt.ylabel("\u03BC prudente predicho por la IA")
plt.legend()
plt.title("Validación del modelo (datos de prueba)")
plt.savefig("validacion_ia.png", dpi=150)
plt.show()