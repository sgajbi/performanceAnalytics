# 📊 Portfolio Performance Analytics: A User Guide

Welcome to the **Performance Analytics Suite**.  
This platform provides a **comprehensive, transparent, and multi-faceted view** of your portfolio's performance.  

Whether you're:
- a **Portfolio Manager** evaluating strategy,  
- a **Client Advisor** explaining results, or  
- an **Investor** tracking returns,  

this guide will help you understand the key tools at your disposal and how to use them effectively.  

The suite is built to answer three **fundamental questions** about any investment portfolio:

1. **What was my performance?** (Measurement)  
2. **What drove my performance?** (Contribution)  
3. **Why did my performance differ from my benchmark?** (Attribution)  

---

## 1. Measuring Performance: TWR vs. MWR

The first step in any analysis is **measuring the top-line return**. The platform offers two industry-standard methods:

### ⏳ Time-Weighted Return (TWR): *The "Portfolio's Return"*

- **Definition:** Measures the compounded growth rate of a portfolio. Neutralizes the impact of **cash flows** (deposits & withdrawals).  
- **Purpose:** Industry standard for judging **investment manager skill**.  
- **Think of it as:** The growth of a single dollar invested on day one.  
- **When to Use:** Evaluate the **manager’s skill** independent of investor timing.  

**Key Configurations:**
- `frequencies`: Daily, monthly, quarterly, or yearly.  
- `metric_basis`: `"NET"` (after fees) or `"GROSS"` (before fees).  

---

### 💵 Money-Weighted Return (MWR): *The "Investor's Return"*

- **Definition:** Measures the actual return an **investor receives**, considering timing and size of cash flows.  
- **Purpose:** Captures the investor’s **real financial outcome**.  
- **Think of it as:** Similar to **IRR (Internal Rate of Return)**.  
- **When to Use:** Understand the **investor’s actual return** on invested capital.  

**Key Configurations:**
- Uses **XIRR**, the industry standard for handling irregular cash flows.  

---

### ⚖️ TWR vs. MWR: Which One to Use?

| **Question**                       | **Best Metric** | **Use Case** |
|------------------------------------|-----------------|--------------|
| How good is my portfolio manager?  | **TWR**         | Evaluate manager’s skill, independent of investor decisions. |
| What was my actual return?         | **MWR**         | Assess investor’s real return, including impact of timing. |
| How does my performance compare to an index? | **TWR** | Provides apples-to-apples benchmark comparison. |

---

## 2. Explaining Performance Drivers: Contribution Analysis

Once you know **total return (TWR)**, the next step is identifying **what drove it**.  

**Contribution Analysis** decomposes portfolio return into **each holding’s contribution**.  

- **What It Answers:** *“Which investments were winners and which were losers?”*  
- **How It Works:** Contributions are calculated so the **sum reconciles to total return**.  

**Key Configurations:**
- **Single-Level:** Flat list of all positions and their contributions.  
- **Multi-Level Drill-Down:** Break down by hierarchy (e.g., `["sector", "position_id"]`) to see both sector and position-level contributions.  

---

## 3. Understanding Active Performance: Attribution Analysis

For **actively managed portfolios**, attribution explains **why performance differs from the benchmark**.  

- **What It Answers:** *“Did I outperform because of sector choices or stock selection?”*  

### The Three Attribution Effects:
1. **Allocation Effect:** Value added/lost by overweighting or underweighting groups (e.g., sectors, regions).  
2. **Selection Effect:** Value added/lost from **picking securities** that outperformed within their group.  
3. **Interaction Effect:** Captures the **combined impact** of allocation & selection.  

---

## 4. The Multi-Currency Dimension

For **global portfolios**, returns come from:
1. **Local Asset Performance**  
2. **Currency Fluctuations**  

**Activating the Feature:**  
Set `"currency_mode": "BOTH"` in your request and provide FX rates.  

### Return Decomposition:
- **Local Return:** Asset’s return in native currency.  
- **FX Return:** Impact of currency exchange fluctuations.  
- **Base Return:** Final return in reporting currency.  

**Currency Attribution:** Explains whether active return was driven by **local asset selection** or **currency bets**.  
**Currency Hedging:** Models hedging strategies to show **true hedged performance**.  

---

## 5. Ensuring Trust: Reproducibility & Data Lineage

Every calculation is **transparent, auditable, and reproducible**.  

### 🔒 Calculation Hash
- Every response includes a **`calculation_hash`**.  
- This acts as a **verifiable fingerprint** ensuring results are reproducible.  

### 🧾 Data Lineage Drill-Down
- Using `calculation_id`, retrieve the full **lineage receipt** from `/performance/lineage/`.  
- Provides CSV downloads with:
  - Exact request sent  
  - Final response received  
  - Day-by-day breakdown of intermediate calculations  

This ensures **auditability** and **compliance**.  

---

# ✅ Summary

- **TWR** → Best for evaluating **manager skill** and **benchmark comparison**.  
- **MWR** → Best for measuring **investor’s actual experience**.  
- **Contribution** → Answers *“What drove my performance?”*  
- **Attribution** → Explains *“Why did my performance differ from benchmark?”*  
- **Multi-Currency** → Breaks down local vs FX impact, supports hedging.  
- **Reproducibility & Lineage** → Guarantees transparency and trust.  

---
