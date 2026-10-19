# Demo Catalogs

`demo_products.json` contains the synthetic product records used by the software simulator and regression flows, plus the current live Vision demo products.

The **current physical three-SKU Vision contract** is:

```text
COPY-001       -> copy
OLIVE-OIL-001  -> olive_oil
BOTTLE-001     -> bottle
```

The older synthetic entries remain in the demo catalog because backend tests and simulator examples exercise generic product behavior independent of the current physical shelf objects.

For presentations and live Vision work, treat `copy`, `olive_oil`, and `bottle` as the active controlled SKU set.
