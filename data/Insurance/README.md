# Household insurance module (PIns_01)

The annual model uses Tanaka's `PIns_01_current_coverage` specification:

- Stable insurance-efficacy, affordability, and provider-trust values are sampled jointly from questionnaire respondents in the matching household group.
- For every household and every simulated year, current flood-insurance coverage is drawn from the PIns_01 Bernoulli-logit probability.
- The probability uses the household's current persistent TP value. Insurance is updated after the annual flood/TP process, so a flood-induced TP increase affects coverage in the same year.
- Initial households and households created through marriage, independence, or in-migration use the same PIns_01 equation. There is no separate fixed entry probability.
- The PIns_02 annual new-uptake rule, PIns_04 five-year renewal rule, and five-year contract expiry are not used in this version.
- Annual transitions are recorded as `joined_PIns01`, `retained_PIns01`, `lapsed_PIns01`, or `remained_uninsured_PIns01`. New households are labeled separately.

For household group \(g\), the annual probability is

\[
p_{h,t}=\operatorname{logit}^{-1}(\alpha_g+\beta_{TP,g}TP_{h,t}+\beta_{E,g}E_h+\beta_{A,g}A_h+\beta_{T,g}T_h).
\]

The annual coverage state is then sampled as

\[
I_{h,t}\sim\operatorname{Bernoulli}(p_{h,t}).
\]

Annual `Household_TP_<year>_seed.txt` files contain insurance status, the three insurance perceptions, predicted probability, decision result, and initialization origin. `Insurance_Expire_Year` remains in the output schema for compatibility but is empty under PIns_01.
