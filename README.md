# UNIVERSIDAD JOSÉ ANTONIO PÁEZ
## Facultad de Ingeniería - Escuela de Ingeniería en Computación
### Cátedra: Simulación de Sistemas | Parcial III - Trabajo Práctico

---

## 📌 1. Descripción General del Proyecto

Este proyecto contiene la solución integral para el **Parcial III de Simulación (Trabajo Práctico)**, desarrollado bajo el **Paradigma de Programación Orientada a Objetos (POO)** en Python. Cumple con la totalidad de los requerimientos de la evaluación:

1. **Problema 1: Simulación de Eventos Discretos** - Fábrica de Ensamblaje de Laptops con gestión de inventario crítico por umbral y paradas de línea (*Starvation*).
2. **Problema 2: Simulación Continua** - Clúster de Servidores de Alto Rendimiento modelado mediante una ecuación diferencial de balance térmico (Runge-Kutta 4) y *Thermal Throttling*.
3. **Consumo de API de Inteligencia Artificial (Google Gemini)** - Conexión automatizada a Google Gemini mediante la clave en `.env` para análisis de métricas, conclusiones y 3 recomendaciones de optimización cuantificadas.
4. **Animación Gráfica Interactiva en Pygame** - Interfaz gráfica interactiva con animación en tiempo real de la cola, estación de ensamble reactiva, indicador de stock de procesadores, termómetro térmico dinámico y gráfica continua en vivo.

---

## 📂 2. Estructura del Código

El proyecto reside de forma 100% independiente en la carpeta `parcial3_simulacion/`:

```
parcial3_simulacion/
├── main.py                     # Punto de entrada unificado (Menú interactivo / CLI / Pygame)
├── requirements.txt            # Dependencias requeridas
├── .env                        # Variables de entorno y API Keys
├── .env.example                # Plantilla de configuración
├── README.md                   # Esta documentación y guía de defensa oral
├── reporte_simulacion_parcial3.txt  # Reporte oficial generado con trazas y dictamen de IA
├── core/                       # Núcleo algorítmico y matemático
│   ├── models.py               # Entidades POO (LaptopOrder, ReplenishmentBatch, Trace, DataPoint)
│   ├── discrete_sim.py         # Motor de Eventos Discretos (DES) con PriorityQueue
│   └── continuous_sim.py       # Motor Continuo diferencial (RK4) y Thermal Throttling
├── services/                   # Capa de servicios auxiliares
│   ├── ai_service.py           # Cliente HTTP de Inteligencia Artificial (Gemini / OpenAI / Ollama)
│   └── reporter.py             # Generador de reportes en consola y archivo de texto
└── ui/                         # Interfaces de usuario
    ├── console_menu.py         # Menú interactivo en consola con validaciones
    └── pygame_app.py           # Bonus visualizador gráfico en Pygame con HUD y controles
```

---

## 📐 3. Fundamentos Matemáticos y Algorítmicos

### Problema 1: Simulación de Eventos Discretos (Fábrica de Laptops)
- **Proceso de Llegadas**: Proceso de Poisson con tasa $\lambda = 10 \text{ órdenes/hora}$. El intervalo entre arribos consecutivos es estocástico y sigue una distribución exponencial:
  $$\Delta t_{\text{arribo}} \sim \text{Exp}\left(\beta = \frac{1}{\lambda} = 6.0 \text{ minutos}\right)$$
- **Tiempo de Servicio de Ensamblaje**: Servidor único (estación de ensamblaje) con duración exponencial:
  $$t_{\text{ensamble}} \sim \text{Exp}\left(\mu_{\text{srv}} = 5.0 \text{ minutos/laptop}\right)$$
  Capacidad de servicio $\mu = 12.0 \text{ laptops/hora}$, intensidad teórica $\rho = \frac{\lambda}{\mu} = \frac{10}{12} \approx 0.8333$.
- **Política de Inventario y Reabastecimiento $(s, Q)$**:
  - Cada laptop requiere 1 procesador de gama alta.
  - Umbral de reorden: $s = 10 \text{ unidades}$. Cuando el stock cae por debajo de 10 unidades, se emite automáticamente una orden al proveedor.
  - Lote de pedido: $Q = 50 \text{ unidades}$.
  - Tiempo de entrega (*Lead Time*): $T_{\text{lead}} = 15 \text{ minutos}$.
  - **Parada de Línea (*Starvation*)**: Si el inventario llega a 0 y una orden necesita ensamblarse, la línea se detiene por falta de componentes. La orden se registra como "demorada por stock" y el sistema mide el tiempo total de paro hasta que arriba el nuevo lote (+50 procesadores), reanudando el ensamble de inmediato.

### Problema 2: Simulación Continua (Clúster Térmico de Servidores)
- **Tasa de Entrada de Tráfico**:
  $$\text{Traffic}(t) \sim \mathcal{N}(\mu = 3.0, \sigma = 1.0) \text{ Gbps}, \quad \text{acotado en } [1.0, 5.0] \text{ Gbps}$$
- **Ecuación Diferencial de Balance Térmico de Primer Orden**:
  $$\frac{dT}{dt} = \dot{Q}_{\text{gen}}(t) - \dot{Q}_{\text{dis}}(t)$$
  $$\dot{Q}_{\text{gen}}(t) = \alpha \cdot \text{Traffic}(t)$$
  $$\dot{Q}_{\text{dis}}(t) = k \cdot (T(t) - T_{\text{amb}})$$
  Con $T_{\text{amb}} = 25.0^\circ\text{C}$. Calibrado en equilibrio para que a tráfico nominal ($3.0 \text{ Gbps}$), la temperatura estacionaria sea exactamente $70.0^\circ\text{C}$ ($\alpha = 15.0 \cdot k$).
  La integración se realiza paso a paso mediante **Runge-Kutta de 4to Orden (RK4)**.
- **Thermal Throttling y Eficiencia**:
  - Si $T \le 70.0^\circ\text{C}$: Eficiencia nominal constante $\eta = 0.90$ ($90\%$).
  - Si $T > 70.0^\circ\text{C}$: Estrangulamiento térmico por protección del silicio:
    $$\eta(T) = \max\left(0.20, 0.90 - 0.035 \cdot (T - 70.0)\right)$$
  - Throughput instantáneo: $R(t) = \text{Traffic}(t) \cdot \eta(T) \text{ Gbps}$.
  - Acumulación de datos en Terabytes procesados ($1 \text{ TB} = 8000 \text{ Gbits}$):
    $$\Delta \text{TB} = \frac{R(t) \cdot \Delta t}{8000}$$

---

## 🚀 4. Guía de Ejecución

Asegúrate de estar en el entorno virtual de Python:

```bash
cd /home/cris/Documents/UJAP/Simuladores
source .venv/bin/activate
```

### Modo 1: Aplicación con Interfaz Gráfica Completa (Por Defecto)
Ejecuta la interfaz gráfica interactiva que integra Menú de Configuración, Simulación en Vivo y Visor de Reporte de IA:
```bash
python parcial3_simulacion/main.py
```
**Estructura de la Interfaz Gráfica**:
1. **Pantalla de Menú y Parámetros**: Ajusta con controles interactivos `[-]` y `[+]` las horas de simulación, tasas de Poisson y selección de proveedor de IA (`GEMINI`, `OPENAI`, `OLLAMA`, `LOCAL`).
2. **Pantalla de Simulación en Vivo**:
   - `[1] Fábrica Laptops`: Cola de laptops, estación de ensamble reactiva (Verde = Libre, Naranja = Ensamblando, Rojo = Detención de línea) y gauge de stock de procesadores con reorden a 15 min.
   - `[2] Clúster Térmico`: Nodo de servidor con racks y LEDs, termómetro dinámico a 70°C, alerta de Thermal Throttling y gráfica de temperatura/throughput en tiempo real.
   - `[✨ Consultar IA]`: Envía las métricas en segundo plano (sin congelar la animación) para obtener el análisis y recomendaciones de la IA.
   - `[🤖 Ver Reporte IA]`: Abre el visor de diagnóstico en pantalla con opción de exportar a `.txt`.
3. **Pantalla de Reporte de IA**:
   - Despliegue en pantalla de la conclusión cuantitativa y las 3 recomendaciones de optimización con scroll mediante rueda del ratón.
   - Botón `[💾 Exportar a Archivo .TXT]` para generar `reporte_simulacion_parcial3.txt`.

**Controles interactivos por Teclado y Ratón**:
- `Clic en Botones`: Navegar entre Menú, Problema 1, Problema 2 y Reporte IA.
- `[ESPACIO]`: Pausar / Reanudar la animación sin detener el cálculo lógico.
- `[1] / [2]`: Alternar entre Problema 1 y Problema 2.
- `[↑] / [↓]`: Modificar la velocidad de simulación ($0.5\times, 1\times, 2\times, 5\times, 10\times, 20\times$).
- `[R]`: Reiniciar la simulación a estado inicial.
- `[ESC]`: Regresar a la pantalla anterior / Menú.

### Modo 2: Menú por Consola / Headless CLI (Opcional)
Para terminales sin entorno gráfico o scripts de prueba automática:
- Menú de consola interactivo:
  ```bash
  python parcial3_simulacion/main.py --cli
  ```
- Ejecución directa headless:
  ```bash
  python parcial3_simulacion/main.py --cli --problem 1 --hours 8
  python parcial3_simulacion/main.py --cli --problem 2 --hours 4
  ```

---

## 🤖 5. Integración con Inteligencia Artificial (Google Gemini)

El módulo `services/ai_service.py` lee automáticamente las credenciales desde `parcial3_simulacion/.env` (`GEMINI_API_KEY` o `API_KEY`):

1. **Google Gemini**: Soporta modelos activos (`gemini-3.6-flash`, `gemini-flash-latest`, `gemini-2.5-flash`).
2. **Motor Analítico Local (Fallback)**: Si no hay conexión a internet durante la defensa presencial, se activa automáticamente un motor analítico local riguroso que evalúa los indicadores cuantitativos y emite conclusiones y 3 recomendaciones de optimización de nivel universitario sin fallar.

---

## 📋 6. Cumplimiento de Pautas de Evaluación

| # | Pauta de Evaluación | Implementación en el Proyecto |
|---|---|---|
| **1** | **Evaluación individual o en equipo** | Proyecto individual listo para entrega. |
| **2** | **Paradigma Orientado a Objetos (POO)** | Clases `LaptopOrder`, `ReplenishmentBatch`, `LaptopFactorySimulator`, `ThermalClusterSimulator`, `AISimulationService`, `SimulationReporter`, `PygameBonusVisualizer`. |
| **3** | **Consumir API de IA y archivo de texto** | Integración con Google Gemini y exportación garantizada a `reporte_simulacion_parcial3.txt`. |
| **4** | **Utilizar repositorios GitHub** | Código modular listo para commit y push. |
| **5** | **Código no duplicado** | Arquitectura original desarrollada específicamente para el examen. |
| **6** | **Entrega y defensa presencial** | Incluye argumentos teóricos y explicaciones paso a paso. |
| **7** | **Validaciones de datos de usuario** | Validadores `prompt_float` y `prompt_int` con límites de rango y captura de excepciones. |
| **8** | **Código comentado** | 100% de docstrings y comentarios explicativos en español. |
| **9** | **Datos por defecto para pruebas** | Valores por defecto integrados (Enter selecciona valor estándar del parcial). |
| **Bonus** | **Animación Pygame** | Visualización completa de colas, estados de ensamble, termómetro, throttling y HUD interactivo. |
# Parcial3_Simulacion
