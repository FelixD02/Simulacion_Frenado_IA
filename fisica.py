import os
import joblib
import numpy as np

# --- 1. CONSTANTES FÍSICAS Y DEL SISTEMA ---
g = 9.81
F_MECANICA_MAX = 150000  # Límite discos/pastillas tractocamión (150 kN).
DT = 0.04                # Diferencial de tiempo de integración (40 ms)

# Carga el modelo entrenado (si existe). Si no existe, usa la fórmula manual.
_ruta = os.path.join(os.path.dirname(__file__), "modelo_ia.joblib")
MODELO_IA = joblib.load(_ruta) if os.path.exists(_ruta) else None

# --- 2. MOTOR FÍSICO DE INTEGRACIÓN NUMÉRICA ---
def simular_tiempo_real(escenario, v0_kmh, theta_deg, mu_s_real, m, L_via):
    v = v0_kmh / 3.6
    theta = np.radians(theta_deg)
    x = 0.0
    t = 0.0
    
    # Física Base
    N = m * g * np.cos(theta)
    Wx = m * g * np.sin(theta)
    F_ideal_verdadera = mu_s_real * N
    F_agarre_cinetico = (0.85 * mu_s_real) * N
    
    # 1. INCERTIDUMBRE Y MODELO DE IA
    mu_sensor = np.random.normal(mu_s_real, 0.15 * mu_s_real)
    
    if MODELO_IA is not None:
        # La IA entrenada predice el valor prudente
        mu_prudente_ia = float(MODELO_IA.predict([[mu_sensor, v0_kmh, theta_deg, m]])[0])
    else:
        # Fórmula de contingencia (Z-score 10%)
        mu_prudente_ia = mu_sensor - (1.28 * 0.15 * mu_sensor)
        
    F_calculada_IA = mu_prudente_ia * N
    F_ia_aplicada = min(F_MECANICA_MAX, max(0, F_calculada_IA))
    
    historial = {
        'x': [0], 'v': [v], 't': [0], 'estado': ["Inicio"],
        'F_ideal': F_ideal_verdadera, 'F_ia_ap': F_ia_aplicada, 'mu_leido': mu_sensor
    }
    
    choca = False
    hubo_bloqueo = False
    resultado_final = ""
    
    while v > 0 and t < 60:
        # DECISIÓN DEL CONTROLADOR
        if escenario == '1. Conductor Humano (Sin ABS)':
            if t < 1.5:
                F_aplicado, estado_actual = 0, "Reacción (1.5s)"
            else:
                F_aplicado, estado_actual = F_MECANICA_MAX, "Frenando a fondo"
        else:
            F_aplicado, estado_actual = F_ia_aplicada, "IA: Frenado Prudente"
            
        # EVALUACIÓN DE CONTACTO
        if F_aplicado > F_ideal_verdadera:
            hubo_bloqueo = True
            estado_actual = "¡Bloqueo de ruedas!"
            F_friccion_real = F_agarre_cinetico
        else:
            F_friccion_real = F_aplicado
            
        if mu_s_real < np.tan(theta) and F_aplicado > 0:
            estado_actual = "Pendiente supera agarre"
            
        # CÁLCULO CINEMÁTICO
        F_neta = Wx - F_friccion_real
        a = F_neta / m
        
        t_paro_exacto = t + abs(v / a) if a < 0 else float('inf')
        x_paro_exacto = x + v * (t_paro_exacto - t) + 0.5 * a * (t_paro_exacto - t)**2 if a < 0 else float('inf')
        
        v_new = v + a * DT
        x_new = x + v * DT + 0.5 * a * DT**2
        
        # CONDICIÓN DE CHOQUE
        if x_new >= L_via or (a < 0 and x_paro_exacto >= L_via and x_new >= L_via):
            x_new = L_via
            v_imp = np.sqrt(max(0, v**2 + 2 * a * (L_via - x))) if a != 0 else v
            choca = True
            resultado_final = "Choque"
            historial['x'].append(x_new); historial['v'].append(v_imp); historial['t'].append(t + DT)
            historial['estado'].append(resultado_final)
            break
            
        # CONDICIÓN DE DETENCIÓN
        if v_new <= 0:
            v_new = 0
            x_new = x_paro_exacto
            resultado_final = "Detenido con Bloqueo" if hubo_bloqueo else "Detenido Seguro"
            historial['x'].append(x_new); historial['v'].append(0); historial['t'].append(t_paro_exacto)
            historial['estado'].append(resultado_final)
            break
            
        x, v, t = x_new, v_new, t + DT
        historial['x'].append(x); historial['v'].append(v); historial['t'].append(t)
        historial['estado'].append(estado_actual)
        
    if v > 0 and t >= 60:
        resultado_final = "No se detuvo"
        historial['estado'].append(resultado_final)
        
    return historial, choca, hubo_bloqueo, resultado_final