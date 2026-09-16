import React, { useState } from 'react';
import './RetailOperatorDashboard.css';

const RetailOperatorDashboard = () => {
  const [selectedBusiness, setSelectedBusiness] = useState(1);
  const [selectedAction, setSelectedAction] = useState(null);
  const [simulateMode, setSimulateMode] = useState(false);
  const [simulatedMetrics, setSimulatedMetrics] = useState(null);

  const businesses = [
    {
      id: 1,
      name: 'Downtown Bookstore',
      churn: 0.475,
      repeat: 0.975,
      margin: -0.81,
      revenue: 29386462,
      customers: 40,
      monthlyCustomersLost: Math.round(40 * 0.475),
      costOfChurnPerMonth: Math.round(29386462 * 0.475 / 12),
      problem: 'Bleeding customers + Selling at massive loss',
      crisis: true,
    },
    {
      id: 8,
      name: 'Main St Hardware',
      churn: 0.5,
      repeat: 0.95,
      margin: -0.86,
      revenue: 29812185,
      customers: 40,
      monthlyCustomersLost: Math.round(40 * 0.5),
      costOfChurnPerMonth: Math.round(29812185 * 0.5 / 12),
      problem: 'CRITICAL: Losing 50% of customers EVERY MONTH + -86% margin',
      crisis: true,
    },
    {
      id: 5,
      name: 'Omni Retail',
      churn: 0.175,
      repeat: 0.975,
      margin: -0.7,
      revenue: 29436036,
      customers: 40,
      monthlyCustomersLost: Math.round(40 * 0.175),
      costOfChurnPerMonth: Math.round(29436036 * 0.175 / 12),
      problem: 'Negative margin but good retention - Focus: Pricing strategy',
      crisis: false,
    },
  ];

  const actionPlans = {
    priceIncrease: {
      title: '🔥 RAISE PRICES IMMEDIATELY',
      description: 'Increase prices by 15-25% across all products',
      impact: {
        marginImprovement: 15,
        churnIncrease: 5,
        timeToImplement: '1 week',
        investmentNeeded: 5000,
      },
      risks: ['Could lose price-sensitive customers', 'Competitors may undercut'],
      benefits: [
        'Turn -86% margin into positive margin',
        'Revenue impact: +$3.7M annually',
        'Immediate cash flow improvement',
      ],
      approval: false,
    },
    discontinueProducts: {
      title: '🗑️ KILL LOSING PRODUCTS',
      description: 'Discontinue bottom 50% of products (by margin)',
      impact: {
        marginImprovement: 20,
        churnIncrease: 15,
        timeToImplement: '2 weeks',
        investmentNeeded: 10000,
      },
      risks: [
        'Might accelerate churn if discontinuing popular items',
        'Need clearance sale to move inventory',
      ],
      benefits: [
        'Focus on profitable products only',
        'Reduce inventory carrying costs',
        'Simpler operations = lower overhead',
      ],
      approval: false,
    },
    loyaltyProgram: {
      title: '💝 LAUNCH LOYALTY PROGRAM',
      description: 'Reward repeat customers with 10-15% loyalty discount',
      impact: {
        marginImprovement: -5,
        churnReduction: 20,
        timeToImplement: '3 weeks',
        investmentNeeded: 50000,
      },
      risks: ['High upfront cost', 'ROI takes 6 months to show'],
      benefits: [
        'Recover 8 lost customers/month (at Downtown Bookstore level)',
        'Increase repeat rate from 97.5% → 99%',
        'Build brand loyalty',
      ],
      approval: false,
    },
    hybrid: {
      title: '⚡ HYBRID EMERGENCY PLAN',
      description: 'Raise prices 10% + Cut bottom 30% products + Launch loyalty for top customers',
      impact: {
        marginImprovement: 25,
        churnReduction: 10,
        timeToImplement: '2 weeks',
        investmentNeeded: 35000,
      },
      risks: ['Complex to execute', 'Requires training staff'],
      benefits: [
        'Addresses BOTH margin AND churn',
        'Balanced approach = lower risk',
        '+$6.2M annual revenue impact',
        'Reaches profitability in 60 days',
      ],
      approval: false,
    },
    doNothing: {
      title: '❌ DO NOTHING (NOT RECOMMENDED)',
      description: 'Keep current strategy, hope things improve',
      impact: {
        marginImprovement: 0,
        churnReduction: 0,
        timeToImplement: 'Ongoing',
        investmentNeeded: 0,
      },
      risks: [
        'Business failure in 6-12 months',
        'Cumulative loss: -$14.7M',
        'Lost customers never return',
      ],
      benefits: ['None - this is why it\'s not recommended'],
      approval: false,
    },
  };

  const current = businesses.find(b => b.id === selectedBusiness);
  const action = selectedAction ? actionPlans[selectedAction] : null;

  const simulateAction = (actionKey) => {
    const actionImpact = actionPlans[actionKey];
    const newMargin = current.margin + (actionImpact.impact.marginImprovement / 100);
    const newChurn = Math.max(0, current.churn - (actionImpact.impact.churnReduction / 100));

    setSimulatedMetrics({
      actionKey,
      before: {
        margin: current.margin,
        churn: current.churn,
        monthlyLoss: current.costOfChurnPerMonth,
      },
      after: {
        margin: newMargin,
        churn: newChurn,
        monthlyLoss: Math.round(current.revenue * newChurn / 12),
      },
      annualSavings: (current.costOfChurnPerMonth * 12) - (Math.round(current.revenue * newChurn / 12) * 12),
    });
    setSimulateMode(true);
  };

  const formatCurrency = (num) => {
    if (num >= 1000000) return `$${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `$${(num / 1000).toFixed(0)}K`;
    return `$${num.toFixed(0)}`;
  };

  return (
    <div className="retail-dashboard">
      {current.crisis && (
        <div className="emergency-banner">
          <div className="emergency-content">
            <span className="emergency-icon">⚠️</span>
            <div>
              <h2>EMERGENCY: CRITICAL BUSINESS SITUATION</h2>
              <p>
                You are losing {current.monthlyCustomersLost} customers every month.
                That's {formatCurrency(current.costOfChurnPerMonth)} in revenue gone.
                Your margin is {(current.margin * 100).toFixed(0)}% (losing money on every sale).
              </p>
            </div>
          </div>
        </div>
      )}

      <header className="dashboard-header">
        <h1>Retail Operator Decision Dashboard</h1>
        <p>Make the critical decision your business needs RIGHT NOW</p>
      </header>

      <div className="business-selector">
        <h3>Select Your Business</h3>
        <div className="business-buttons">
          {businesses.map((b) => (
            <button
              key={b.id}
              className={`biz-btn ${selectedBusiness === b.id ? 'active' : ''} ${b.crisis ? 'crisis' : ''}`}
              onClick={() => {
                setSelectedBusiness(b.id);
                setSelectedAction(null);
                setSimulateMode(false);
                setSimulatedMetrics(null);
              }}
            >
              {b.crisis && '🔴'} {b.name}
            </button>
          ))}
        </div>
      </div>

      <main className="dashboard-main">
        <div className="container">
          <div className="problem-section">
            <h2 className="problem-title">YOUR PROBLEM</h2>
            <div className="problem-box">
              <p className="problem-statement">{current.problem}</p>
              <div className="problem-metrics">
                <div className="metric-danger">
                  <span className="label">Losing per month</span>
                  <span className="value">{current.monthlyCustomersLost} CUSTOMERS</span>
                  <span className="detail">{formatCurrency(current.costOfChurnPerMonth)} revenue</span>
                </div>
                <div className="metric-danger">
                  <span className="label">Your margin</span>
                  <span className="value">{(current.margin * 100).toFixed(0)}%</span>
                  <span className="detail">You lose ${Math.abs(current.margin).toFixed(2)} per $1 sold</span>
                </div>
                <div className="metric-danger">
                  <span className="label">Annual impact</span>
                  <span className="value">{formatCurrency(current.costOfChurnPerMonth * 12)}</span>
                  <span className="detail">Lost revenue + paying to stay open</span>
                </div>
              </div>
            </div>
          </div>

          <div className="actions-section">
            <h2>YOUR OPTIONS (Pick ONE)</h2>
            <div className="action-grid">
              {Object.entries(actionPlans).map(([key, plan]) => (
                <div
                  key={key}
                  className={`action-card ${selectedAction === key ? 'selected' : ''} ${key === 'doNothing' ? 'danger' : ''}`}
                  onClick={() => setSelectedAction(key)}
                >
                  <h3>{plan.title}</h3>
                  <p className="action-desc">{plan.description}</p>
                  <div className="impact-preview">
                    <div className="impact-item">
                      <span className="impact-label">Margin Improvement</span>
                      <span className={`impact-value ${plan.impact.marginImprovement >= 0 ? 'positive' : 'negative'}`}>
                        {plan.impact.marginImprovement >= 0 ? '+' : ''}{plan.impact.marginImprovement}%
                      </span>
                    </div>
                    <div className="impact-item">
                      <span className="impact-label">Churn Reduction</span>
                      <span className={`impact-value ${plan.impact.churnReduction >= 0 ? 'positive' : 'negative'}`}>
                        {plan.impact.churnReduction >= 0 ? '-' : '+'}{Math.abs(plan.impact.churnReduction)}%
                      </span>
                    </div>
                    <div className="impact-item">
                      <span className="impact-label">Investment</span>
                      <span className="impact-value">{formatCurrency(plan.impact.investmentNeeded)}</span>
                    </div>
                  </div>
                  <p className="timeline">⏱️ {plan.impact.timeToImplement} to implement</p>
                </div>
              ))}
            </div>
          </div>

          {action && !simulateMode && (
            <div className="action-details">
              <div className="details-header">
                <h2>{action.title}</h2>
                <button className="close-btn" onClick={() => setSelectedAction(null)}>×</button>
              </div>
              <div className="details-grid">
                <div className="details-box benefits">
                  <h3>✅ Benefits</h3>
                  <ul>
                    {action.benefits.map((b, idx) => (
                      <li key={idx}>{b}</li>
                    ))}
                  </ul>
                </div>
                <div className="details-box risks">
                  <h3>⚠️ Risks</h3>
                  <ul>
                    {action.risks.map((r, idx) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="action-buttons">
                <button className="btn-simulate" onClick={() => simulateAction(selectedAction)}>
                  📊 Simulate Impact
                </button>
                <button className="btn-approve" onClick={() => alert(`✅ Approved: ${action.title}\n\nNext: Implement in ${action.impact.timeToImplement}\n\nInvestment: ${formatCurrency(action.impact.investmentNeeded)}`)}>
                  ✅ Approve & Execute
                </button>
              </div>
            </div>
          )}

          {simulatedMetrics && simulateMode && (
            <div className="simulation-results">
              <div className="sim-header">
                <h2>📊 IMPACT SIMULATION</h2>
                <button className="close-btn" onClick={() => setSimulateMode(false)}>×</button>
              </div>
              <div className="before-after">
                <div className="before-column">
                  <h3>📍 BEFORE (Today)</h3>
                  <div className="metric-box">
                    <p className="metric-label">Margin</p>
                    <p className="metric-value danger">{(simulatedMetrics.before.margin * 100).toFixed(0)}%</p>
                  </div>
                  <div className="metric-box">
                    <p className="metric-label">Monthly Churn</p>
                    <p className="metric-value danger">{(simulatedMetrics.before.churn * 100).toFixed(1)}%</p>
                  </div>
                  <div className="metric-box">
                    <p className="metric-label">Monthly Revenue Loss</p>
                    <p className="metric-value danger">{formatCurrency(simulatedMetrics.before.monthlyLoss)}</p>
                  </div>
                </div>
                <div className="arrow">→</div>
                <div className="after-column">
                  <h3>🎯 AFTER (30 days)</h3>
                  <div className="metric-box">
                    <p className="metric-label">Margin</p>
                    <p className={`metric-value ${simulatedMetrics.after.margin >= 0 ? 'positive' : 'danger'}`}>
                      {(simulatedMetrics.after.margin * 100).toFixed(0)}%
                    </p>
                    <p className="change">{simulatedMetrics.after.margin >= 0 ? '✅ PROFITABLE' : '⚠️ Still negative'}</p>
                  </div>
                  <div className="metric-box">
                    <p className="metric-label">Monthly Churn</p>
                    <p className={`metric-value ${simulatedMetrics.after.churn < simulatedMetrics.before.churn ? 'positive' : 'danger'}`}>
                      {(simulatedMetrics.after.churn * 100).toFixed(1)}%
                    </p>
                    <p className="change">{((simulatedMetrics.before.churn - simulatedMetrics.after.churn) * 100).toFixed(0)}% reduction</p>
                  </div>
                  <div className="metric-box">
                    <p className="metric-label">Monthly Revenue Loss</p>
                    <p className="metric-value positive">{formatCurrency(simulatedMetrics.after.monthlyLoss)}</p>
                    <p className="change">Save {formatCurrency(simulatedMetrics.before.monthlyLoss - simulatedMetrics.after.monthlyLoss)}/mo</p>
                  </div>
                </div>
              </div>
              <div className="annual-impact">
                <h3>💰 ANNUAL IMPACT</h3>
                <div className="annual-box">
                  <p>If you act today, in 12 months you'll save:</p>
                  <p className="annual-value positive">{formatCurrency(simulatedMetrics.annualSavings)}</p>
                  <p className="annual-detail">That's the difference between business failure and business survival.</p>
                </div>
              </div>
              <div className="simulation-actions">
                <button className="btn-approve" onClick={() => alert(`✅ Decision Made!\n\nAction: ${actionPlans[simulatedMetrics.actionKey].title}\n\nExpected Annual Savings: ${formatCurrency(simulatedMetrics.annualSavings)}\n\nLet's proceed to implementation!`)}>
                  ✅ YES - Execute This Plan
                </button>
                <button className="btn-simulate" onClick={() => setSimulateMode(false)}>
                  ← Try Another Option
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="dashboard-footer">
        <p>💡 <strong>Insight:</strong> Doing nothing costs you {formatCurrency(current.costOfChurnPerMonth * 12)} per year. Most actions pay for themselves in 2-3 months.</p>
      </footer>
    </div>
  );
};

export default RetailOperatorDashboard;
