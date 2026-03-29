import type { ProductData } from '../types/a2a';

const PROVIDER_LABEL: Record<string, string> = { cathay: '國泰', fubon: '富邦' };

export function ProductCard({ products }: { products: ProductData[] }) {
  return (
    <div className="bg-bg-card rounded-lg p-4 border border-border space-y-3">
      <h3 className="text-text font-semibold">商品推薦（{products.length} 項）</h3>
      <div className="grid gap-2">
        {products.map((p) => (
          <div key={p.product_id} className="bg-bg rounded-lg p-3 border border-border/50 flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-1.5 py-0.5 rounded bg-cta/20 text-cta">{PROVIDER_LABEL[p.provider] || p.provider}</span>
                <span className="text-sm font-medium text-text">{p.name}</span>
              </div>
              <div className="text-xs text-text-muted mt-1">{p.category} · {p.highlights.join(' · ')}</div>
            </div>
            <div className="text-right shrink-0">
              <div className="text-primary font-semibold">${p.base_premium_monthly.toLocaleString()}/月</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
