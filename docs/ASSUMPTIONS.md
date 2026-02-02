# Assumptions and Limitations

Factual summary of modeling assumptions and known limitations. PRD: §13 Assumptions and Limitations, §11 MVP Scope.

---

## Fuel Load Estimation

- Fuel load is estimated with a **simplified linear model**.
- Fuel at start of lap *N* = `initial_fuel_kg - (N - 1) × fuel_per_lap_kg`, clamped to a minimum (e.g. 0 kg).
- Defaults: 110 kg at lap 1, 1.8 kg/lap consumption (configurable in `stint_features` and optimizer).
- **No refuelling**: pit stops do not add fuel (F1 2010+).
- Fuel is used only to correct lap time for car mass; no separate fuel strategy.

---

## Clean-Air Assumption

- **Lap times are treated as clean-air** in the MVP.
- The degradation model and optimizer assume that projected lap times are representative of a car running in free air.
- Traffic, following loss, and position-dependent pace are not modeled. Results can diverge when cars run in traffic or behind another car for long periods.

---

## Dry-Race-Only Scope

- **Only dry sessions are supported.** Wet races are rejected at load time (`load_race` raises if weather data reports Rainfall).
- Tire compounds are **slick only**: SOFT, MEDIUM, HARD. INTERMEDIATE and WET are not modeled.
- Validation and case studies use dry races only to reduce confounding from rain and mixed conditions.

---

## Excluded Features

The following are **out of scope** for the MVP and are not implemented:

| Area | Exclusion |
|------|-----------|
| **Safety car / VSC** | No safety car or virtual safety car modeling. Lap times and pit decisions under SC/VSC are not treated differently. The **VSC scenario** in the CLI and `vsc_recommendation` use a fixed pit-loss factor (e.g. 50%) for illustration only; there is no prediction of when VSC occurs. |
| **Traffic / multi-car** | Single-car optimization only. No traffic, undercut/overcut interaction, or position-dependent lap time. |
| **Driver-specific pace** | No driver-specific pace model beyond lap time trends in the data. Degradation is per track and compound, not per driver. |
| **Live integration** | No real-time or live-race integration. All inputs are from historical or cached session data. |
| **Wet / intermediate tires** | Wet and intermediate compounds are excluded. Only SOFT, MEDIUM, HARD are used. |

---

## Advisory Nature of Recommendations

- Strategy recommendations are **advisory**, not predictive.
- Outputs are based on a simplified model (linear degradation, fixed pit loss, clean-air, dry only). Real decisions depend on many factors not in the model.
- Results may diverge in races with unusual conditions (e.g. late rain, long safety car, heavy traffic). Assumptions should be revisited as the model evolves.
