# MAANAKNETRA Parameter Matching & Comparison Rules (Step 7A & 7B)

> **HUMAN-LED ENGINEERING NOTICE**  
> These parameter comparison rules, unit normalization formulas, and compatibility evaluation boundaries were explicitly designed, reviewed, and audited by human standards engineers. They are deterministic algorithmic rules operating strictly on verified data in `data/standards.json`. At no point are these deterministic rules substituted by probabilistic or hallucinated LLM judgments.

---

## 1. Unit Normalization Rules

### Power Normalization
- **Rule**: All power ratings are converted to standard kilowatt ($kW$) for mathematical comparison while strictly preserving the original raw procurement text.
- **Conversion Factors**:
  - $1 \text{ kW} = 1000 \text{ W}$
  - $1 \text{ HP} (\text{metric/electrical}) = 0.7457 \text{ kW}$
  - $7.5 \text{ kW} \approx 10.05 \text{ HP}$ (in tender: `7.5 kW (10.0 HP)` dual-unit representation).
- **Rationale**: Procurement tenders often specify pump motors in both metric kilowatts ($kW$) and commercial horsepower ($HP$). Normalization ensures uniform evaluation against Indian Standard rating brackets.
- **Example**: A requirement for `10 HP` is evaluated as $7.457 \text{ kW}$.

### Voltage Normalization
- **Rule**: Standardized to Volts ($V$).
- **Conversion Factors**:
  - $1 \text{ kV} = 1000 \text{ V}$
- **Example**: `0.415 kV` $\rightarrow 415 \text{ V}$.

### Flow Rate (Discharge) Normalization
- **Rule**: Normalizes between Litres per second ($L/s$) and cubic meters per hour ($m^3/hr$).
- **Conversion Factor**:
  - $1 \text{ L/s} = 3.6 \text{ m}^3/\text{hr}$
  - $18.0 \text{ L/s} = 18.0 \times 3.6 = 64.8 \text{ m}^3/\text{hr}$.
- **Rationale**: Both $L/s$ and $m^3/hr$ are universally used in municipal and agricultural tenders. Dual-unit tenders (e.g. `18.0 Litres per Second (64.8 m³/hr)`) resolve to the exact same physical flow rate.

### Pressure Normalization
- **Rule**: Normalizes to bar ($bar$).
- **Conversion Factors**:
  - $1 \text{ bar} = 100 \text{ kPa} = 0.1 \text{ MPa} \approx 1.0197 \text{ kg/cm}^2 \approx 10.197 \text{ m water head}$.

---

## 2. Technical Parameter Comparison Rules

### Rule 1: Rated Supply Voltage (`VOLTAGE`)
- **Comparison Type**: Exact Equality / Categorical match.
- **Logic**: If tender specifies nominal $415\text{ V}$ 3-phase, matches standard clause for 3-phase AC supply ($415\text{ V}$).
- **Status**: `COMPLIANT`.
- **Conflict**: If tender specifies incompatible supply voltage (e.g. $230\text{ V}$ 3-phase or $600\text{ V}$), triggers `NON_COMPLIANT`.

### Rule 2: Voltage Variation Band (`VOLTAGE`)
- **Comparison Type**: Numeric Range Comparison.
- **Logic**:
  - Standard `IS 14220` Clause 6.2 specifies motor operation with supply voltage variation of $+6\%$ to $-15\%$ of rated $415\text{ V}$ ($352.75\text{ V}$ to $439.9\text{ V}$, nominally $352\text{ V}$ to $440\text{ V}$).
  - Tender specifies $350\text{ V}$ to $440\text{ V}$.
  - The $2\text{ V}$ lower margin ($350\text{ V}$ vs $352\text{ V}$) is flagged as `DEVIATING` with explicit numerical bounds preserved.

### Rule 3: Operating Temperature (`TEMPERATURE`)
- **Comparison Type**: Upper Bound / Maximum Threshold (`LESS_THAN_OR_EQUAL`).
- **Logic**:
  - `IS 14220` Scope explicitly covers *"handling clear, cold water up to 33°C"*.
  - Tender specifies *"ambient, not exceeding 33°C"*.
  - Evaluated as `COMPLIANT`.
  - If a tender demands operation at $45^\circ\text{C}$ or $50^\circ\text{C}$, the rule explicitly triggers `NON_COMPLIANT` (`CONFLICT`) because it exceeds the verified standard ceiling.

### Rule 4: Rated Power Output Ceiling (`POWER`)
- **Comparison Type**: Range Ceiling (`RANGE_CEILING`).
- **Logic**:
  - `IS 14220` Scope covers openwell submersible pumpsets *"up to 45 kW"*.
  - Tender specifies $7.5\text{ kW}$ ($10.0\text{ HP}$).
  - Since $7.5\text{ kW} \le 45\text{ kW}$, the requirement is evaluated as `COMPLIANT`.
  - If tender specifies $75\text{ kW}$, the rule triggers `NON_COMPLIANT`.

### Rule 5: Supply Frequency (`FREQUENCY`)
- **Comparison Type**: Exact Equality (`EXACT_EQUALITY`).
- **Logic**: Standard grid frequency is $50\text{ Hz} \pm 3\%$. Tender requirement of $50\text{ Hz}$ is evaluated as `COMPLIANT`. Conflicting frequency ($60\text{ Hz}$) triggers `NON_COMPLIANT`.

### Rule 6: Insulation Resistance & Megger Voltage (`TESTING`)
- **Comparison Type**: Lower Bound / Minimum Threshold (`GREATER_THAN_OR_EQUAL`).
- **Logic**:
  - Standard `IS 14220` Clause 14.3 requires minimum $5\text{ M}\Omega$ after immersion, measured with a $500\text{ V DC}$ megger.
  - Tender specifies $500\text{ V DC}$ megger and minimum $5\text{ Megaohms}$ after 24 hours immersion.
  - Both parameters are evaluated as `COMPLIANT`.
  - Insulation resistance requirement below $5\text{ M}\Omega$ (e.g. $2\text{ M}\Omega$) triggers `NON_COMPLIANT`.

---

## 3. Evidence Integrity Rules (Step 7B Corrections)

### Rule 7: Duty-Point Parameters (Head, Flow, Shut-Off Head, Submergence Depth)
- **Constraint**: **Do NOT treat existence of a table reference as proof of compliance.**
- **Parameters Affected**:
  - Rated Operating Head ($32.0\text{ m}$)
  - Discharge Rate ($18.0\text{ L/s} / 64.8\text{ m}^3/\text{hr}$)
  - Minimum Shut-off Head ($42.0\text{ m}$)
  - Maximum Submergence Depth ($15\text{ m}$)
- **Rule Action**:
  - In `IS 14220`, performance is indexed by continuous characteristic curves in Table 1 tested per `IS 11346`.
  - If the prototype dataset only states *"see Table 1"* but does not contain the actual numerical duty-point curves for $(H, Q)$ lookups, the engine **MUST return `NOT_SPECIFIED`**.
  - Marking compliance merely because "Table 1 exists" is strictly prohibited.

### Rule 8: Hydrostatic Test (Head vs. Discharge Pressure Distinction)
- **Constraint**: **Do NOT assume operating head == discharge pressure.**
- **Context**:
  - Tender: *"1.5 times the maximum operating head"*
  - Standard: *"1.5 times the maximum discharge pressure or 2.0 bar minimum"*
- **Rule Action**:
  - Head and discharge pressure are distinct physical quantities requiring system curve and density/gravity transformations not present in the structured prototype dataset.
  - Direct equivalence cannot be assumed.
  - Return `NOT_SPECIFIED` with note: *"Different physical quantities; direct equivalence not established."*

### Rule 9: Dynamic Efficiency Guardrail
- **Constraint**: **NEVER treat overall efficiency in `IS 14220` as a universal fixed scalar cutoff (such as 35%).**
- **Rule Action**:
  - Overall efficiency is dynamically determined by Table 1 curve lookup per `IS 11346`.
  - Return `NOT_SPECIFIED` and explain that duty-point curve table verification is required.

### Rule 10: Installation & Operating Environment Guardrail
- **Constraint**: **Never infer compliance from a general scope statement.**
- **Rule Action**:
  - Only return `COMPLIANT` when the standard structured data contains explicit evidence directly supporting that specific tender requirement.
  - General environment descriptions (e.g. rural sump wells) and installation preferences (e.g. vertical vs horizontal suspension) return `NOT_SPECIFIED` if explicit standard clauses are absent.

### Rule 11: Absence of Data vs. Conflict Rule
- **Constraint**: **Do NOT mark `NON_COMPLIANT` (`CONFLICT`) merely because a parameter is absent from the prototype standard dataset.**
- **Rule Action**:
  - Absence of structured data returns `NOT_SPECIFIED`.
  - `NOT_SPECIFIED` explicitly signifies *"Standard data does not contain enough information to compare"*. It does NOT mean non-compliant.
