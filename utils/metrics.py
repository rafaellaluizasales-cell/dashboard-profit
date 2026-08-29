import pandas as pd

def calculate_metrics(df):
    if df.empty:
        return {
            'total_pnl': 0.0, 'gross_profit': 0.0, 'gross_loss': 0.0,
            'num_trades': 0, 'win_rate': 0.0, 'profit_factor': 0.0,
            'avg_pnl': 0.0, 'avg_win': 0.0, 'avg_loss': 0.0, 'payoff': 0.0,
            'max_win': 0.0, 'max_loss': 0.0, 'max_dd': 0.0,
            'max_w_streak': 0, 'max_l_streak': 0
        }

    total_pnl = df['Res_Numeric'].sum()
    gross_profit = df[df['Res_Numeric'] > 0]['Res_Numeric'].sum()
    gross_loss = df[df['Res_Numeric'] < 0]['Res_Numeric'].sum()
    num_trades = len(df)
    
    wins = df[df['Res_Numeric'] > 0]
    losses = df[df['Res_Numeric'] < 0]
    
    win_rate = (len(wins) / num_trades * 100) if num_trades > 0 else 0
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else (99.99 if gross_profit > 0 else 0)
    
    avg_pnl = df['Res_Numeric'].mean() if num_trades > 0 else 0
    avg_win = wins['Res_Numeric'].mean() if len(wins) > 0 else 0
    avg_loss = losses['Res_Numeric'].mean() if len(losses) > 0 else 0
    payoff = (avg_win / abs(avg_loss)) if avg_loss != 0 else 0
    
    max_win = df['Res_Numeric'].max() if num_trades > 0 else 0
    max_loss = df['Res_Numeric'].min() if num_trades > 0 else 0
    
    # Streaks
    mw, ml, cw, cl = 0, 0, 0, 0
    vals = df['Res_Numeric'].values
    for v in vals:
        if v > 0:
            cw += 1
            cl = 0
            mw = max(mw, cw)
        elif v < 0:
            cl += 1
            cw = 0
            ml = max(ml, cl)
        else:
            cw, cl = 0, 0
    max_w_streak, max_l_streak = mw, ml
    
    # Drawdown
    if not df.empty:
        cum = df['Res_Numeric'].cumsum()
        max_dd = (cum - cum.cummax()).min()
    else:
        max_dd = 0.0
    
    # Anti-Fading Discipline Streak
    # Definition: Success is NOT (Operated=TR AND Real=BTC)
    discipline_streak = 0
    if 'Group_Operado' in df.columns and 'Group_Real' in df.columns:
        # Sort by date to ensure streak is chronological
        df_sorted = df.sort_values('Abertura_Dt')
        for _, row in df_sorted.iterrows():
            is_fading_error = (row['Group_Operado'] == 'TR (Lateral)') and (row['Group_Real'] == 'BTC (Momentum)')
            if not is_fading_error:
                discipline_streak += 1
            else:
                discipline_streak = 0 # Reset on error
    
    # Violinada no BE Analysis
    # Definition: TeriaPagado == 'Sim' AND (Res_Numeric is near zero or negative)
    # We consider "near zero" as being between -30 and 30 (covering spread/commissions)
    if 'TeriaPagado' in df.columns:
        violinadas_df = df[
            (df['TeriaPagado'].astype(str).str.upper().str.contains('SIM')) & 
            (df['Res_Numeric'] <= 30)
        ]
    else:
        violinadas_df = pd.DataFrame()
    num_violinadas = len(violinadas_df)
    
    # Financial impact: If each violinada had paid a 2:1 target (assuming R$ 160 per contract)
    # Total potential lost = (Qtd * 160) - Res_Numeric
    if 'Qtd_Clean' in violinadas_df.columns and not violinadas_df.empty:
        potencial_perdido = ((violinadas_df['Qtd_Clean'] * 160) - violinadas_df['Res_Numeric']).sum()
    else:
        potencial_perdido = num_violinadas * 2000 # Fallback

    return {
        'total_pnl': total_pnl,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'num_trades': num_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_pnl': avg_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'payoff': payoff,
        'max_win': max_win,
        'max_loss': max_loss,
        'max_dd': max_dd,
        'max_w_streak': max_w_streak,
        'max_l_streak': max_l_streak,
        'discipline_streak': discipline_streak,
        'num_violinadas': num_violinadas,
        'potencial_perdido': potencial_perdido
    }
