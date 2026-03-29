import type { PremiumData } from '../types/a2a';

export function PremiumTable({ data }: { data: PremiumData }) {
  return (
    <div className="bg-bg-card rounded-lg p-4 border border-border space-y-3">
      <h3 className="text-text font-semibold">保費試算</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-text-muted border-b border-border">
            <th className="text-left py-1">商品</th>
            <th className="text-right py-1">月繳</th>
            <th className="text-right py-1">年繳</th>
          </tr>
        </thead>
        <tbody>
          {data.results.map((r) => (
            <tr key={r.product_id} className="border-b border-border/30">
              <td className="py-1.5 text-text">{r.product_name}</td>
              <td className="py-1.5 text-right text-text">${r.monthly_premium.toLocaleString()}</td>
              <td className="py-1.5 text-right text-text-muted">${r.annual_premium.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="font-semibold">
            <td className="pt-2 text-text">合計</td>
            <td className="pt-2 text-right text-primary">${data.total_monthly.toLocaleString()}</td>
            <td className="pt-2 text-right text-text-muted">${data.total_annual.toLocaleString()}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
