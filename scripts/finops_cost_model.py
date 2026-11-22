"""FinOps · Modelo de costo mensual de CrediScore (S18). Reproducible y con supuestos a la vista.

  python scripts/finops_cost_model.py     # escribe docs/finops/evidencia/cost-model.json

Precios: lista on-demand de AWS us-east-1 (referencia pública). sa-east-1 (São Paulo, la
región del backend de Terraform) es más cara: se aplica REGION_FACTOR como supuesto y se debe
reemplazar por la cifra del AWS Pricing Calculator antes de presupuestar en serio.

Dos estados para la palanca 2 (capacidad):
  antes   · manifiestos de la S07: requests 100m/128Mi, HPA 3..20, staging igual a prod 24x7
            (dev corre en kind local: USD 0)
  después · requests 250m/128Mi (el tier mínimo de Fargate que igual se paga), HPA 3..8 por la
            capacidad medida en el game day (E0), staging con 1 réplica y apagado fuera de horario
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "finops" / "evidencia" / "cost-model.json"
HOURS = 730
REGION_FACTOR = 1.5  # SUPUESTO sa-east-1 vs us-east-1; verificar en calculator.aws

PRICE = {  # USD, us-east-1, on-demand
    "eks_cluster_h": 0.10,
    "fargate_vcpu_h": 0.04048,
    "fargate_gb_h": 0.004445,
    "aurora_acu_h": 0.12,
    "aurora_storage_gb_mo": 0.10,
    "msk_serverless_cluster_h": 0.75,
    "msk_partition_h": 0.0015,
    "nat_gw_h": 0.045,
    "alb_h": 0.0225,
    "api_gw_per_million": 3.50,
    "cw_logs_gb": 0.50,
    "secret_mo": 0.40,
}


def fargate_tier(cpu_m: int, mem_mi: int) -> tuple[float, float]:
    """EKS Fargate suma 256 MiB al request de memoria y redondea a la configuración válida
    siguiente. Combinaciones mínimas: 0,25 vCPU con 0,5 / 1 / 2 GB; 0,5 vCPU con 1–4 GB."""
    vcpu = max(0.25, math.ceil(cpu_m / 250) * 0.25)
    gb = (mem_mi + 256) / 1024
    gb = 0.5 if gb <= 0.5 else math.ceil(gb)
    if vcpu >= 0.5:
        gb = max(gb, 1.0)
    return vcpu, gb


def pod_month(cpu_m: int, mem_mi: int, hours: float) -> float:
    vcpu, gb = fargate_tier(cpu_m, mem_mi)
    return (vcpu * PRICE["fargate_vcpu_h"] + gb * PRICE["fargate_gb_h"]) * hours


def env_cost(
    name: str,
    *,
    services: int,
    replicas: float,
    cpu_m: int,
    mem_mi: int,
    hours: float,
    aurora_instances: int,
    aurora_min_acu: float,
    aurora_hours: float,
    monthly_requests: int,
    logs_gb: float,
) -> dict:
    lines = {
        "EKS plano de control": PRICE["eks_cluster_h"] * HOURS,
        f"Fargate ({services} servicios x {replicas:g} pods)": services * replicas * pod_month(cpu_m, mem_mi, hours),
        "Aurora Serverless v2 (cómputo mínimo)": aurora_instances
        * aurora_min_acu
        * PRICE["aurora_acu_h"]
        * aurora_hours,
        "Aurora almacenamiento 20 GB": 20 * PRICE["aurora_storage_gb_mo"],
        "MSK Serverless (clúster + 30 particiones)": (PRICE["msk_serverless_cluster_h"] + 30 * PRICE["msk_partition_h"])
        * HOURS,
        "NAT Gateway (1)": PRICE["nat_gw_h"] * HOURS,
        "ALB del Ingress": PRICE["alb_h"] * HOURS,
        "API Gateway": monthly_requests / 1e6 * PRICE["api_gw_per_million"],
        "CloudWatch Logs": logs_gb * PRICE["cw_logs_gb"],
        "Secrets Manager (5)": 5 * PRICE["secret_mo"],
    }
    lines = {k: round(v * REGION_FACTOR, 2) for k, v in lines.items()}
    return {"env": name, "lines": lines, "total": round(sum(lines.values()), 2)}


def scenario(
    label: str,
    *,
    cpu_m: int,
    hpa_max: int,
    stg_replicas: float,
    stg_hours: float,
    stg_aurora_instances: int,
    stg_aurora_hours: float,
) -> dict:
    prod = env_cost(
        "prod",
        services=3,
        replicas=3,
        cpu_m=cpu_m,
        mem_mi=128,
        hours=HOURS,
        aurora_instances=2,
        aurora_min_acu=0.5,
        aurora_hours=HOURS,
        monthly_requests=300_000,
        logs_gb=10,
    )
    stg = env_cost(
        "staging",
        services=3,
        replicas=stg_replicas,
        cpu_m=cpu_m,
        mem_mi=128,
        hours=stg_hours,
        aurora_instances=stg_aurora_instances,
        aurora_min_acu=0.5,
        aurora_hours=stg_aurora_hours,
        monthly_requests=50_000,
        logs_gb=3,
    )
    # Techo: prod con todos los servicios en hpa_max todo el mes (un cliente desbocado, un DoS)
    ceiling_extra = 3 * (hpa_max - 3) * pod_month(cpu_m, 128, HOURS) * REGION_FACTOR
    return {
        "label": label,
        "fargate_tier_per_pod": fargate_tier(cpu_m, 128),
        "hpa_max": hpa_max,
        "prod": prod,
        "staging": stg,
        "total_expected": round(prod["total"] + stg["total"], 2),
        "total_ceiling": round(prod["total"] + stg["total"] + ceiling_extra, 2),
    }


def main() -> int:
    office_hours = 12 * 22  # 12 h x 22 días hábiles
    before = scenario(
        "antes", cpu_m=100, hpa_max=20, stg_replicas=3, stg_hours=HOURS, stg_aurora_instances=2, stg_aurora_hours=HOURS
    )
    after = scenario(
        "despues",
        cpu_m=250,
        hpa_max=8,
        stg_replicas=1,
        stg_hours=office_hours,
        stg_aurora_instances=1,
        stg_aurora_hours=office_hours,
    )  # Aurora v2 con auto-pausa (0 ACU)
    out = {
        "prices_reference": "AWS us-east-1 on-demand (lista pública)",
        "region_factor_assumed": REGION_FACTOR,
        "prices": PRICE,
        "before": before,
        "after": after,
        "saving_expected_usd": round(before["total_expected"] - after["total_expected"], 2),
        "saving_expected_pct": round(1 - after["total_expected"] / before["total_expected"], 4),
        "saving_ceiling_usd": round(before["total_ceiling"] - after["total_ceiling"], 2),
        "msk_share_of_after": round(
            (
                after["prod"]["lines"]["MSK Serverless (clúster + 30 particiones)"]
                + after["staging"]["lines"]["MSK Serverless (clúster + 30 particiones)"]
            )
            / after["total_expected"],
            4,
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    for s in (before, after):
        print(f"{s['label']}: esperado {s['total_expected']} USD/mes · techo {s['total_ceiling']} USD/mes")
        for env in ("prod", "staging"):
            print(f"  {env}: {s[env]['total']}  {s[env]['lines']}")
    print(
        f"Ahorro esperado: {out['saving_expected_usd']} USD/mes ({out['saving_expected_pct']:.1%}); "
        f"techo: {out['saving_ceiling_usd']} USD/mes; MSK = {out['msk_share_of_after']:.0%} del costo después"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
