export type DashboardData = {
  metrics: {
    open_hazards: number;
    open_actions: number;
    critical_hazards: number;
    average_risk_score: number;
  };
  risk_insights: string[];
  hazards_by_level: Record<string, number>;
};

export async function getDashboard(): Promise<DashboardData> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const token = process.env.NEXT_PUBLIC_DEMO_TOKEN;
  if (!token) {
    return {
      metrics: { open_hazards: 38, open_actions: 14, critical_hazards: 3, average_risk_score: 11.7 },
      risk_insights: [
        "Falls are trending upward across elevated work permits.",
        "Yard B has repeated vehicle-pedestrian interface observations.",
        "Three certification renewals are due before the next audit window."
      ],
      hazards_by_level: { low: 9, medium: 18, high: 8, critical: 3 }
    };
  }
  const response = await fetch(`${baseUrl}/api/v1/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
    next: { revalidate: 30 }
  });
  if (!response.ok) {
    throw new Error("Unable to load dashboard");
  }
  return response.json();
}
