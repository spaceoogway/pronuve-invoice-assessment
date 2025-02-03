## Reference Evapotranspiration (Penman–Monteith Equation)

$$
ET_0 = \frac{0.408\, \Delta\, R_n + \gamma\, \frac{900}{T_K}\, \text{wind}\,(e_s - e_a)}{\Delta + \gamma\, \left(1 + 0.34\, \text{wind}\right)}
$$

**Where:**

- $ET_0$: Reference evapotranspiration (mm/day)
- $\Delta$: Slope of the saturation vapor pressure curve (kPa/°C)
- $R_n$: Net (shortwave) radiation (MJ/m²/day)
- $\gamma$: Psychrometric constant (kPa/°C)
- $T_K$: Temperature in Kelvin, where $T_K = T + 273.15$
- $\text{wind}$: Wind speed at 10 m height (m/s)
- $e_s$: Saturation vapor pressure (kPa)
- $e_a$: Actual vapor pressure (kPa)

---

## Crop Evapotranspiration

$$
ET_c = ET_0\, K_c
$$

**Where:**

- $ET_c$: Crop evapotranspiration (mm/day)
- $ET_0$: Reference evapotranspiration (mm/day)
- $K_c$: Crop coefficient (dimensionless)

---

## Water Requirement

$$
\text{Water need} = \frac{ET_c \times A}{1000}
$$

**Where:**

- $\text{Water need}$: Water requirement (m³/day)
- $ET_c$: Crop evapotranspiration (mm/day)
- $A$: Area of the park (m²)