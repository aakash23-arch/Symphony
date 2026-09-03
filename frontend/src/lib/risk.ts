export function scoreDisclaimer(_topic?: string): string {
  return "Composite risk is an uncalibrated scalar (0.00 to 1.00) conditioned by transaction context, not a calibrated probability.";
}

export const expertNames: Record<string, string> = {
  E1: "Spectral Continuity (E1)",
  E2: "Phase Anomaly (E2)",
  E3: "Temporal Jitter (E3)",
  E4: "Biometric Variance (E4)",
  E5: "Prosodic Inconsistency (E5)",
  E6: "Synthetic Artifacts (E6)",
};

export function formatScore(score?: number | null): string {
  if (score == null || isNaN(score)) return "—";
  return score.toFixed(2);
}

export function formatUnit(val?: number | null, unit = ""): string {
  if (val == null || isNaN(val)) return "—";
  const formatted = val.toFixed(2);
  return unit ? `${formatted} ${unit}` : formatted;
}

export function scoreToBand(score?: number | null): string {
  if (score == null || isNaN(score)) return "LOW";
  if (score >= 0.75) return "CRITICAL";
  if (score >= 0.60) return "HIGH";
  if (score >= 0.35) return "UNCERTAIN";
  return "LOW";
}

export function bandLabel(band?: string | null, score?: number | null): string {
  const b = (band || (score != null ? scoreToBand(score) : "LOW")).toUpperCase();
  if (b.includes("CRITICAL") || b.includes("SYNTHETIC_HIGH")) return "CRITICAL THREAT";
  if (b.includes("HIGH") || b.includes("SYNTHETIC")) return "HIGH RISK";
  if (b.includes("UNCERTAIN") || b.includes("STEP_UP")) return "UNCERTAIN / STEP-UP";
  if (b.includes("SUSPICIOUS") || b.includes("MEDIUM") || b.includes("ELEVATED")) return "SUSPICIOUS / ELEVATED";
  if (b.includes("GENUINE") || b.includes("LOW")) return "NOMINAL / LOW RISK";
  return "EVALUATING";
}

export function getBandToken(band?: string | null) {
  const b = (band || "LOW").toUpperCase();
  if (b.includes("HIGH") || b.includes("CRITICAL") || b.includes("SYNTHETIC")) {
    return {
      bg: "bg-red-500/10",
      text: "text-red-600",
      border: "border-red-500/30",
      surface: "bg-red-500/5",
      tone: "critical",
      label: b.includes("CRITICAL") ? "CRITICAL THREAT" : "HIGH RISK",
      headline: "High Synthetic Risk Detected",
      meaning: "Elevated probability of voice manipulation or deepfake synthesis.",
      accent: "border-red-500",
    };
  }
  if (b.includes("UNCERTAIN")) {
    return {
      bg: "bg-purple-500/10",
      text: "text-purple-600",
      border: "border-purple-500/30",
      surface: "bg-purple-500/5",
      tone: "uncertain",
      label: "UNCERTAIN / STEP-UP",
      headline: "Uncertain Acoustic Evaluation",
      meaning: "Acoustic evaluation degraded by noise or channel artifacts requiring step-up verification.",
      accent: "border-purple-500",
    };
  }
  if (b.includes("MEDIUM") || b.includes("ELEVATED") || b.includes("SUSPICIOUS")) {
    return {
      bg: "bg-amber-500/10",
      text: "text-amber-600",
      border: "border-amber-500/30",
      surface: "bg-amber-500/5",
      tone: "warning",
      label: "ELEVATED RISK",
      headline: "Elevated Risk Context",
      meaning: "Potential acoustic anomaly or transaction sensitivity requirement.",
      accent: "border-amber-500",
    };
  }
  return {
    bg: "bg-emerald-500/10",
    text: "text-emerald-600",
    border: "border-emerald-500/30",
    surface: "bg-emerald-500/5",
    tone: "success",
    label: "LOW RISK",
    headline: "Low Risk Nominal Call",
    meaning: "Acoustic signature nominal with clean biometric continuity.",
    accent: "border-emerald-500",
  };
}

export const bandTokens: Record<string, ReturnType<typeof getBandToken>> = new Proxy(
  {},
  {
    get(_target, prop: string) {
      return getBandToken(prop);
    },
  }
);

export function getActionToken(action?: string | null) {
  const a = (action || "ALLOW").toUpperCase();
  if (a.includes("REJECT") || a.includes("BLOCK") || a.includes("TERMINATE")) {
    return {
      bg: "bg-red-500/10",
      text: "text-red-400",
      border: "border-red-500/30",
      surface: "bg-red-500/5",
      tone: "critical",
      label: a,
      headline: "Transaction Terminated / Blocked",
      accent: "border-red-500",
    };
  }
  if (a.includes("HOLD") || a.includes("FLAG") || a.includes("VERIFY") || a.includes("CHALLENGE")) {
    return {
      bg: "bg-amber-500/10",
      text: "text-amber-400",
      border: "border-amber-500/30",
      surface: "bg-amber-500/5",
      tone: "warning",
      label: a,
      headline: "Transaction Flagged for Out-of-Band Verification",
      accent: "border-amber-500",
    };
  }
  return {
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
    surface: "bg-emerald-500/5",
    tone: "success",
    label: a,
    headline: "Transaction Allowed to Proceed",
    accent: "border-emerald-500",
  };
}

export const actionTokens: Record<string, ReturnType<typeof getActionToken>> = new Proxy(
  {},
  {
    get(_target, prop: string) {
      return getActionToken(prop);
    },
  }
);

export function severityTone(severity?: string | null): string {
  const s = (severity || "INFO").toUpperCase();
  if (s === "CRITICAL" || s === "HIGH" || s === "ERROR") return "text-red-400";
  if (s === "WARNING" || s === "MEDIUM") return "text-amber-400";
  return "text-slate-400";
}

export function expertStatusTone(status?: string | null): string {
  const st = (status || "OK").toUpperCase();
  if (st === "NOMINAL" || st === "OK" || st === "ACTIVE") return "text-emerald-400";
  if (st === "DEGRADED" || st === "WARNING") return "text-amber-400";
  return "text-red-400";
}
