import type { Cart } from "@synccart/shared-types";

function money(minor: number, currency: string) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 2 }).format(minor / 100);
}

export function CartList({ cart, onRemove, removing }: { cart: Cart; onRemove: (sku: string) => void; removing?: string | null }) {
  if (!cart.items.length) return <div className="empty-state"><div className="empty-orbit">◎</div><h3>Your cart is empty</h3><p>Scan your first item to begin.</p></div>;
  return (
    <div className="cart-list">
      {cart.items.map((item) => (
        <article className="cart-row" key={item.sku}>
          <div className="product-mark">{item.name.slice(0, 2).toUpperCase()}</div>
          <div className="cart-copy"><strong>{item.name}</strong><span>{item.sku}</span><small>{money(item.unit_price_minor, item.currency)} × {item.quantity}</small></div>
          <div className="cart-actions"><strong>{money(item.line_total_minor, item.currency)}</strong><button onClick={() => onRemove(item.sku)} disabled={removing === item.sku}>− Remove</button></div>
        </article>
      ))}
    </div>
  );
}

export function CartTotal({ cart }: { cart: Cart }) {
  const entries = Object.entries(cart.totals_by_currency);
  return <div className="cart-total"><span>{cart.total_quantity} item{cart.total_quantity === 1 ? "" : "s"}</span><strong>{entries.length ? entries.map(([currency, value]) => money(value, currency)).join(" + ") : "₹0.00"}</strong></div>;
}
