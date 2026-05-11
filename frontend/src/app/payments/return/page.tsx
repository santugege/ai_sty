import Link from "next/link";
import { AppNav } from "@/components/app-nav";

type PaymentReturnPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function PaymentReturnPage({
  searchParams,
}: PaymentReturnPageProps) {
  const params = searchParams ? await searchParams : {};
  const orderNo = firstParam(params.out_trade_no) || firstParam(params.orderNo) || "";
  const tradeStatus = firstParam(params.trade_status) || "";

  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="grid min-h-screen xl:grid-cols-[10rem_minmax(0,1fr)]">
        <AppNav />

        <section className="grid min-h-screen place-items-center px-4 py-8">
          <div className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-soft">
            <p className="text-xs font-bold uppercase text-accent">Payment</p>
            <h1 className="mt-1 text-2xl font-black">支付结果</h1>
            <p className="mt-3 text-sm leading-6 text-ink-light">
              页面跳转只代表收银台流程结束，最终状态以后端回调为准。
            </p>

            <dl className="mt-5 grid gap-3 rounded-lg bg-surface-soft p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <dt className="text-ink-light">订单号</dt>
                <dd className="max-w-[14rem] truncate font-bold">
                  {orderNo || "等待回调"}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-ink-light">支付状态</dt>
                <dd className="font-bold">{tradeStatus || "处理中"}</dd>
              </div>
            </dl>

            <Link
              href="/"
              className="mt-5 inline-flex h-10 items-center rounded-md bg-ink px-4 text-sm font-black text-white transition-refined hover:bg-accent"
            >
              回到工作台
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}

