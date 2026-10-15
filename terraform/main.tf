# CrediScore · scoring-api
# Infra base: provider Kubernetes + backend remoto (S3) + namespace.
# Alineado con k8s/namespace.yaml y ADR 0003 (AWS como proveedor tentativo).

terraform {
  required_version = ">= 1.10.0" # use_lockfile (lock nativo en S3) requiere >= 1.10

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.31"
    }
  }

  # Backend remoto en S3. Los bloques backend no aceptan variables, por eso los
  # valores van fijos aquí o se inyectan en el init:
  #   terraform init \
  #     -backend-config="bucket=<tu-bucket>" \
  #     -backend-config="region=<tu-region>"
  # El bucket debe existir antes (versionado + cifrado activados).
  backend "s3" {
    bucket       = "crediscore-tfstate-CHANGE_ME"
    key          = "crediscore/scoring-api/terraform.tfstate"
    region       = "sa-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
variable "kubeconfig_path" {
  description = "Ruta al kubeconfig del clúster destino"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Contexto del kubeconfig (null = el actual)"
  type        = string
  default     = null
}

variable "namespace" {
  description = "Namespace de la aplicación"
  type        = string
  default     = "crediscore"
}

# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------
provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

# ---------------------------------------------------------------------------
# Namespace (mismos labels que k8s/namespace.yaml)
# ---------------------------------------------------------------------------
resource "kubernetes_namespace_v1" "crediscore" {
  metadata {
    name = var.namespace

    labels = {
      "app.kubernetes.io/part-of" = "crediscore"
      iniciativa                  = "crediscore"
      equipo                      = "los-papus"
    }
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
output "namespace" {
  value = kubernetes_namespace_v1.crediscore.metadata[0].name
}
