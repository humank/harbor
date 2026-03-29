import type { Artifact, RiskData, ProductData, PremiumData } from '../types/a2a';
import { RiskCard } from './RiskCard';
import { ProductCard } from './ProductCard';
import { PremiumTable } from './PremiumTable';

export function ArtifactRenderer({ artifact }: { artifact: Artifact }) {
  const dataPart = artifact.parts.find((p) => p.data);
  if (!dataPart?.data) {
    const text = artifact.parts.map((p) => p.text).filter(Boolean).join('\n');
    return text ? <p className="text-sm text-text-muted">{text}</p> : null;
  }

  const d = dataPart.data as Record<string, unknown>;

  if ('score' in d && 'risk_class' in d) return <RiskCard data={d as unknown as RiskData} />;
  if ('products' in d) return <ProductCard products={(d.products as ProductData[]) || []} />;
  if ('total_monthly' in d) return <PremiumTable data={d as unknown as PremiumData} />;

  return (
    <pre className="bg-bg-card rounded-lg p-3 text-xs text-text-muted overflow-auto border border-border">
      {JSON.stringify(d, null, 2)}
    </pre>
  );
}
