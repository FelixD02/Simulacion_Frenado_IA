import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons, Button
import matplotlib.patches as patches
import matplotlib.transforms as mtransforms
from matplotlib.animation import FuncAnimation

# Importamos el motor físico y las constantes desde el nuevo archivo fisica.py
from fisica import simular_tiempo_real, F_MECANICA_MAX

# --- CONSTANTES DE INTERFAZ GRÁFICA ---
PRESETS_FRICCION = {
    'Asfalto Seco (~0.8)': 0.8,
    'Concreto Seco (~0.7)': 0.7,
    'Asfalto Mojado (~0.5)': 0.5,
    'Afirmado/Barro (~0.2)': 0.2
}

COLORES_ESTADO = {
    "Inicio": ('royalblue', 'slategray'),
    "Reacción (1.5s)": ('royalblue', 'slategray'),
    "Frenando a fondo": ('forestgreen', 'slategray'),
    "IA: Frenado Prudente": ('forestgreen', 'slategray'),
    "¡Bloqueo de ruedas!": ('darkorange', 'slategray'),
    "Pendiente supera agarre": ('gold', 'slategray'),
    "Choque": ('firebrick', 'darkred'),
    "Detenido Seguro": ('forestgreen', 'slategray'),
    "Detenido con Bloqueo": ('darkorange', 'slategray'),
    "No se detuvo": ('purple', 'indigo')
}

# --- CONFIGURACIÓN DE LA INTERFAZ GRÁFICA ---
fig, ax = plt.subplots(figsize=(12, 7))
plt.subplots_adjust(left=0.05, bottom=0.45, right=0.75, top=0.9)
ax.set_title("Frenado Tradicional vs IA: Incertidumbre y Regresión Cuantil", fontsize=14, fontweight='bold')
ax.set_xlabel("Distancia horizontal (m)")
ax.set_ylabel("Altura (m)")
ax.grid(True, linestyle=':', alpha=0.7)
ax.set_aspect('equal', adjustable='datalim')

axcolor = 'whitesmoke'
slider_L = Slider(plt.axes([0.2, 0.35, 0.45, 0.03], facecolor=axcolor), 'L. Vía (m)', 20.0, 500.0, valinit=300.0)
slider_v0 = Slider(plt.axes([0.2, 0.30, 0.45, 0.03], facecolor=axcolor), 'Velocidad (km/h)', 10.0, 100.0, valinit=60.0)
slider_theta = Slider(plt.axes([0.2, 0.25, 0.45, 0.03], facecolor=axcolor), 'Ángulo (°)', 0.0, 10.0, valinit=5.0) 
slider_m = Slider(plt.axes([0.2, 0.20, 0.45, 0.03], facecolor=axcolor), 'Masa (kg)', 4000.0, 52000.0, valinit=30000.0)

ax_radio_modo = plt.axes([0.77, 0.72, 0.2, 0.12], facecolor='lightgray')
radio_modo = RadioButtons(ax_radio_modo, ('1. Conductor Humano (Sin ABS)', '2. Sistema IA (Autónomo)'))

ax_radio_fric = plt.axes([0.77, 0.52, 0.2, 0.18], facecolor='lightgray')
radio_fric = RadioButtons(ax_radio_fric, tuple(PRESETS_FRICCION.keys()))

ax_boton = plt.axes([0.77, 0.42, 0.2, 0.08])
boton_play = Button(ax_boton, '▶ SIMULAR', color='lightblue', hovercolor='0.975')

txt_resultado = plt.figtext(0.77, 0.10, "Ajuste parámetros y presione SIMULAR...", fontsize=10, weight='bold', wrap=True)

# HUD Display en el gráfico anclado a la esquina superior derecha
hud_text = ax.text(0.95, 0.95, "", transform=ax.transAxes, fontsize=12, 
                   verticalalignment='top', horizontalalignment='right', 
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# --- CREACIÓN DEL CAMIÓN Y ESCENA ---
partes_camion = []
trailer = patches.Rectangle((-10.0, 0.8), 6.5, 3.2, edgecolor='black', zorder=3)
cabina = patches.Polygon([(-3.2, 0.8), (-0.2, 0.8), (-0.2, 1.7), (-0.8, 3.0), (-3.2, 3.0)], edgecolor='black', zorder=3)
ventana = patches.Polygon([(-1.5, 1.8), (-0.6, 1.8), (-1.1, 2.7), (-1.5, 2.7)], color='cyan', edgecolor='black', zorder=4)
chasis = patches.Rectangle((-10.0, 0.7), 9.5, 0.2, color='black', zorder=2)
ruedas = [patches.Circle((x, 0.6), 0.6, color='black', zorder=5) for x in [-8.5, -6.5, -2.0]]

partes_camion.extend([trailer, cabina, ventana, chasis] + ruedas)
for parte in partes_camion: ax.add_patch(parte)
linea_via, = ax.plot([], [], color='dimgray', linewidth=5, zorder=1)
poste_fin, = ax.plot([], [], color='red', linewidth=3, linestyle='--', zorder=2)

# --- ACTUALIZACIÓN ESTÁTICA EN TIEMPO REAL ---
def actualizar_escena_estatica(val=None):
    theta_rad = np.radians(slider_theta.val)
    L_via = slider_L.val
    
    # Dibujar vía y poste
    linea_via.set_data([-20 * np.cos(theta_rad), L_via * np.cos(theta_rad)], [20 * np.sin(theta_rad), -L_via * np.sin(theta_rad)])
    poste_fin.set_data([L_via * np.cos(theta_rad), L_via * np.cos(theta_rad)], [-L_via * np.sin(theta_rad), -L_via * np.sin(theta_rad) + 10])
    
    # Reiniciar camión a inicio
    transform = mtransforms.Affine2D().rotate(-theta_rad) + ax.transData
    cabina.set_facecolor(COLORES_ESTADO["Inicio"][0]); trailer.set_facecolor(COLORES_ESTADO["Inicio"][1])
    for p in partes_camion: p.set_transform(transform)
    
    ax.set_xlim(-20, L_via + 20)
    ax.set_ylim(-L_via * np.sin(theta_rad) - 10, 25)
    hud_text.set_text("Posición Inicial")
    fig.canvas.draw_idle()

for s in [slider_L, slider_v0, slider_theta, slider_m]: s.on_changed(actualizar_escena_estatica)

# --- MOTOR DE ANIMACIÓN ---
anim_obj = None

def animar(event):
    global anim_obj
    if anim_obj is not None: anim_obj.event_source.stop()
        
    escenario = radio_modo.value_selected
    mu_real = PRESETS_FRICCION[radio_fric.value_selected]
    
    # Llama a la función que ahora vive en fisica.py
    hist, choca, hubo_bloqueo, res_final = simular_tiempo_real(
        escenario, slider_v0.val, slider_theta.val, mu_real, slider_m.val, slider_L.val
    )
    
    d_final = hist['x'][-1]
    t_final = hist['t'][-1]
    
    F_ideal_kN = hist['F_ideal'] / 1000
    val_txt = f"RESULTADO: {res_final}\n"
    if choca: val_txt += f"Impacto a {hist['v'][-1] * 3.6:.1f} km/h en {t_final:.1f}s.\n"
    else: val_txt += f"Se detuvo en {d_final:.1f} m ({t_final:.1f}s).\n"
        
    val_txt += f"\n--- DATOS DE VALIDACIÓN ---\n"
    val_txt += f"Fuerza Ideal (F*): {F_ideal_kN:.1f} kN\n"
    
    if 'IA' in escenario:
        val_txt += f"Sensor IA (con ruido \u03C3=15%): {hist['mu_leido']:.2f}\n"
        val_txt += f"Fuerza Prudente Aplicada (IA): {hist['F_ia_ap']/1000:.1f} kN\n"
        val_txt += "-> IA usa Regresión Cuantil (10%) para evitar bloqueo."
    else:
        val_txt += f"Fuerza Humano (Pánico): {F_MECANICA_MAX/1000:.1f} kN\n"
        if hubo_bloqueo: val_txt += "-> Superó F*. Llantas bloqueadas y pérdida direccional."
    
    txt_resultado.set_text(val_txt)
    
    frames_totales = len(hist['x'])
    salto = max(1, frames_totales // 90)
    indices_anim = list(range(0, frames_totales, salto))
    if indices_anim[-1] != frames_totales - 1: indices_anim.append(frames_totales - 1)
    indices_anim.extend([frames_totales - 1] * 15) # Pausa final
    
    theta_rad = np.radians(slider_theta.val)
    
    def update(idx_visual):
        frame = indices_anim[idx_visual]
        x_val = hist['x'][frame]
        v_val = hist['v'][frame] * 3.6
        t_val = hist['t'][frame]
        estado = hist['estado'][frame]
        
        # HUD Update
        hud_text.set_text(f"Tiempo: {t_val:.1f} s\nVelocidad: {v_val:.1f} km/h\nDistancia: {x_val:.1f} m\nEstado: {estado}")
        
        # Colores
        c_cab, c_trail = COLORES_ESTADO.get(estado, ('royalblue', 'slategray'))
        cabina.set_facecolor(c_cab); trailer.set_facecolor(c_trail)

        # Geometría
        x_coord, y_coord = x_val * np.cos(theta_rad), -x_val * np.sin(theta_rad)
        transformacion = mtransforms.Affine2D().rotate(-theta_rad).translate(x_coord, y_coord) + ax.transData
        for parte in partes_camion: parte.set_transform(transformacion)
        
        ax.set_xlim(x_coord - 20, x_coord + 40)
        ax.set_ylim(y_coord - 25, y_coord + 25)
        return partes_camion + [hud_text]

    anim_obj = FuncAnimation(fig, update, frames=len(indices_anim), interval=20, blit=False, repeat=False)
    fig.canvas.draw()

boton_play.on_clicked(animar)
actualizar_escena_estatica()
plt.show()