# Monetization And Partner Channel Guide

Use this guide whenever the product may charge money, gate features by purchase, or let an outside person or company help sell it. Monetization infrastructure and partner distribution are separate decisions. A product may need either, both, or neither.

Do not select RevenueCat merely because a pricing page exists. First resolve the commercial model, purchase surfaces, entitlement owner, tax/compliance owner, and partner motion. Verify every named provider against current official documentation on the PRD date; do not freeze remembered pricing, platform support, or store-policy claims.

## Decision Gates

Record both gates in `PRD.md`, including an explicit `not_required — <reason>` result.

### Monetization Infrastructure Gate

1. Resolve the model: `none`, `one_time`, `subscription`, `usage_based`, `hybrid`, or `undecided`.
2. Record the offer: tiers, billing interval or unit, trial/discount rules, currency/region, upgrade/downgrade, cancellation, refund, grace/dunning, and the feature or quota each purchase unlocks.
3. Name every purchase surface: Apple App Store, Google Play, web checkout, invoice/sales-assisted, desktop license, marketplace, or another exact channel.
4. Decide the source of truth for products, purchases, subscription state, and entitlements. These may be one system or several joined by webhooks.
5. Decide who owns payment processing, tax/VAT/GST, invoices, fraud, refunds, chargebacks, customer billing support, and store compliance.
6. Mark subscription or purchase infrastructure `required`, `not_required`, or `blocked`. When required, compare only providers that fit the resolved surfaces and responsibilities.

### Partner Channel Gate

Resolve one model: `none`, `affiliate`, `referral`, `reseller`, `hybrid`, or `undecided`.

- **Affiliate:** a partner broadcasts a tracked link and earns a commission after a conversion. The customer buys from the product company or its merchant of record.
- **Referral:** a partner introduces a known lead. The sales team normally owns qualification and closing.
- **Reseller:** the partner owns more of the sale and may invoice the customer, receive a wholesale discount, provision licenses or seats, and handle onboarding or first-line support.
- **Hybrid:** name which motions coexist and how attribution conflicts are resolved.

For any non-`none` model, record eligibility/application, approval, attribution window and first/last-touch rule, lead/deal deduplication, commission basis and duration, refund/chargeback reversal, payout schedule and minimum, tax documentation, fraud controls, brand/creative rules, forbidden promotion, customer ownership, privacy/consent, termination, and audit/reporting. A reseller also records deal registration, territory, price authority, contract/invoice owner, provisioning/deprovisioning, delegated administration, support boundaries, renewal/upsell ownership, and channel conflict rules.

## Provider Shortlist

This is a shortlist, not a default or exhaustive catalog. Compare two to four options that actually fit the resolved product. Record official sources and retrieval date in `stack-decisions.md`.

Assign status per layer; one section may mix statuses. `Approved` means the human owner accepted a new choice directly or through an explicit recorded delegation. `Recommended` is a proposal awaiting that decision and is not executable. Authority is the cited source, not a status label. Record Selection, status, cited authority/evidence, fit, constraint, rejected alternatives, and revisit triggers using `output-contract.md`'s shared stack-decision shape.

### Purchases, Subscriptions, Paywalls, And Entitlements

| Option | Best fit | Watch-outs to resolve |
| --- | --- | --- |
| Native StoreKit / Google Play Billing | One or two native-store surfaces where the team can own receipt validation, subscription state, and entitlements | More backend and store-specific lifecycle work; verify current store rules and APIs |
| RevenueCat | Cross-platform app subscriptions, centralized entitlements, store purchase validation, paywalls/experiments, or combined mobile and web access | It does not remove store obligations; choose the web billing engine and merchant-of-record/tax owner separately |
| Qonversion | Mobile/web subscription management or observer-mode analytics with offerings, entitlements, experiments, integrations, and webhooks | Confirm the required mode and current SDK/platform coverage |
| Adapty | Mobile subscription apps prioritizing remotely managed paywalls, placements, experiments, and analytics | Confirm whether purchase/entitlement or web needs exceed its current supported surface |
| Superwall | Paywall, placement, audience, and experiment control; it may use its own subscription management or another purchase controller | Treat beta surfaces and the purchase-controller boundary explicitly |
| Stripe Billing + Entitlements | Web-first SaaS, recurring or usage-based billing, invoices, and feature entitlements | The product remains responsible for its legal/tax setup unless another Stripe or external service owns it; native digital-goods rules still apply |
| Paddle Billing | Web/SaaS or app-to-web billing when a merchant of record should own payment, tax, compliance, fraud, and billing operations | Confirm product eligibility, checkout/channel constraints, and how entitlements return to the app |
| Lemon Squeezy | Digital products or SaaS needing merchant-of-record billing, subscriptions, license keys, hosted checkout, and an integrated affiliate option | Confirm product approval, supported business model, and whether its entitlement/licensing model fits the app |

### Affiliate, Referral, And Reseller Operations

| Option | Best fit | Watch-outs to resolve |
| --- | --- | --- |
| PartnerStack | B2B programs that may combine affiliate, referral, lead, deal-registration, co-sell, and reseller motions | Broader CRM/billing integration and operating process are required |
| Rewardful | Straightforward affiliate/referral attribution and recurring commissions for Stripe- or Paddle-backed sales | It is not a full reseller or deal-registration system |
| FirstPromoter | Affiliate/referral programs needing recurring, limited-duration, or one-time commissions across supported billing providers | Unsupported billing systems require API work; reseller operations remain separate |
| Lemon Squeezy Affiliates | Products already sold through Lemon Squeezy that want application, link attribution, commissions, creatives, and payouts in the same platform | Affiliates apply through Lemon Squeezy; confirm that operating model fits partner recruitment |
| Custom partner service | Contract-specific reseller provisioning, wholesale pricing, territories, delegated admin, or channel rules no product supports cleanly | Highest implementation and operations burden; choose only from a documented gap |

## Selection Rules

- A pricing strategy makes the gates applicable; it does not make RevenueCat automatically required.
- Prefer native store commerce for a simple single-store app when cross-platform entitlement, remote paywall, or analytics needs do not justify another service.
- Prefer a subscription-management layer when multiple stores or web purchases must unlock one entitlement model, or when server-side receipt validation, paywall iteration, experiments, and lifecycle webhooks would otherwise be built in-house.
- Prefer Stripe Billing for web-first SaaS when the business wants to own the merchant relationship and operating stack. Consider Paddle or Lemon Squeezy when merchant-of-record responsibility is a primary requirement.
- Choose an affiliate tool for link attribution and commission payout. Choose a partnership platform or custom reseller workflow when partners register deals, invoice buyers, receive wholesale terms, provision access, or support customers.
- Billing and partner providers must join on stable customer, order/invoice, product/price, subscription, currency, net-revenue, refund, and chargeback identities. Define idempotent webhook handling and reconciliation before implementation.
- Never claim that an affiliate or reseller feature is free, globally available, store-compliant, or supported by a billing provider without current official evidence.
- Present two to four coherent commercial-infrastructure bundles that cover every applicable responsibility layer together. Recommend one, show operating cost and ownership tradeoffs, and obtain owner acceptance under the Stack Decision Checkpoint; do not ask the owner to combine unrelated provider menus blindly.
- Mark accepted new provider choices `Approved`, existing providers `Selected`, and hard constraints `Required`. `Recommended` and `Provisional` rows keep the checkpoint blocked and cannot enter delivery.

## Required Product And Delivery Outputs

`PRD.md` records both gate decisions, pricing and offer rules, purchase surfaces, entitlement behavior, partner motion, attribution and commission rules, customer/partner/admin UI, metrics, risks, and required `TEST-*` obligations.

`architecture.md` records the product/order/subscription/entitlement/partner/referral/deal/commission entities; payment and partner event flows; identity joins; webhook verification, idempotency, retries and reconciliation; refund/chargeback effects; provisioning/deprovisioning; environment separation; and external-console work.

`stack-decisions.md` records the approved billing/store, subscription/entitlement, paywall/checkout, merchant-of-record/tax, and partner-channel providers as separate layers with status, official evidence, fit, constraints, alternatives, revisit triggers, and the human Stack Decision Checkpoint.

For UI-bearing products, add or update every affected pricing, checkout, paywall, purchase restore/manage, affiliate application/dashboard, referral/deal registration, reseller administration, commission/payout, and error state in the PRD UI Surface Contract and `wireframes.html` before implementation.

Delivery separates independently verifiable billing/entitlement and partner-channel outcomes into different missions. Required tests cover sandbox/store purchase, entitlement grant/revoke/restore, renewal, upgrade/downgrade, cancellation, payment failure, refund/chargeback, webhook replay and out-of-order delivery, affiliate/referral attribution, commission reversal, duplicate/self-referral/fraud controls, payout records, and reseller provisioning/termination where applicable.

## Official Sources To Recheck

Retrieved for this guide on 2026-09-08. Recheck on each PRD date.

- RevenueCat documentation and web billing: https://www.revenuecat.com/docs and https://www.revenuecat.com/docs/web/overview
- Qonversion overview and subscription management: https://documentation.qonversion.io/docs/quickstart and https://documentation.qonversion.io/docs/subscription-management-mode
- Adapty paywalls and Web API: https://adapty.io/docs/create-paywall and https://adapty.io/docs/api-web
- Superwall documentation and subscription management: https://superwall.com/docs/ and https://superwall.com/docs/dashboard/subscription-management
- Stripe Billing subscriptions and entitlements: https://docs.stripe.com/billing/subscriptions/overview and https://docs.stripe.com/billing/entitlements
- Apple in-app purchase and App Review Guidelines: https://developer.apple.com/help/app-store-connect/configure-in-app-purchase-settings/overview-for-configuring-in-app-purchases and https://developer.apple.com/app-store/review/guidelines/
- Google Play Billing: https://developer.android.com/google/play/billing
- Paddle merchant-of-record billing: https://www.paddle.com/billing and https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf
- Lemon Squeezy billing and affiliates: https://docs.lemonsqueezy.com/guides/getting-started and https://docs.lemonsqueezy.com/help/affiliates-for-merchants/getting-referrals
- PartnerStack program models: https://docs.partnerstack.com/docs/plan-your-implementation
- Rewardful campaigns: https://help.rewardful.com/en/articles/2051885-create-your-first-campaign
- FirstPromoter commissions: https://help.firstpromoter.com/en/articles/8971339-recurring-commissions-and-monetary-rewards
