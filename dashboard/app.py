"""Dashboard local Boréal : streamlit run dashboard/app.py."""
import os
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from data_access import MEASURES,aggregate_sql,compare_previous_year,query,ratios,shapley,where
ROOT=HERE.parent
DB=Path(os.environ.get('BOREAL_DB',str(ROOT/'boreal.duckdb')))

st.set_page_config(page_title='Boréal · Pilotage',page_icon='◈',layout='wide')
START=time.perf_counter()
st.markdown('''<style>
.stApp{background:#f5f7fa}.block-container{padding-top:2rem;max-width:1450px}
[data-testid="stSidebar"]{background:#102d3b}[data-testid="stSidebar"] *{color:#edf5f6}
[data-testid="stMetric"]{background:white;border:1px solid #dce5e9;border-radius:12px;padding:18px 16px}
[data-testid="stMetricLabel"]{color:#547080}[data-testid="stMetricValue"]{color:#12384a;font-size:1.8rem}
h1,h2,h3{color:#12384a}.eyebrow{color:#168678;font-size:12px;font-weight:700;letter-spacing:2px}
</style>''',unsafe_allow_html=True)
px.defaults.color_discrete_sequence=['#168678','#183e58','#dc9e36','#8a779e','#6d9dac']

@st.cache_data(ttl=300,show_spinner=False)
def read(path,sql,params=(),stamp=0):
    return query(path,sql,params)

if not DB.is_file():
    st.error('Base absente. Lance python analyses/preparer_dashboard.py depuis le dossier du projet, puis redémarre cette page.')
    st.stop()
STAMP=DB.stat().st_mtime_ns

def q(sql,params=()):return read(str(DB),sql,tuple(params),STAMP)
def chart(fig):
    fig.update_layout(template='plotly_white',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font={'color':'#173b4c'},title_font_color='#173b4c',legend={'font':{'color':'#173b4c'}},margin={'l':10,'r':15,'t':45,'b':20},legend_title_text='')
    fig.update_xaxes(tickfont_color='#426170',title_font_color='#426170',gridcolor='#dbe4e9',zerolinecolor='#dbe4e9')
    fig.update_yaxes(tickfont_color='#426170',title_font_color='#426170',gridcolor='#dbe4e9',zerolinecolor='#dbe4e9')
    st.plotly_chart(fig,width='stretch',theme=None)
def euro(x):return '—' if pd.isna(x) else f'{x:,.0f} €'.replace(',',' ')
def pct(x):return '—' if pd.isna(x) else f'{100*x:.2f} %'.replace('.',',')
def number(x):return '—' if pd.isna(x) else f'{x:,.0f}'.replace(',',' ')
def download(frame,label,key):st.download_button(label,frame.to_csv(index=False).encode('utf-8-sig'),key+'.csv','text/csv',key=key)

required={'mart_portefeuille_mensuel','mart_contrat_mois','mart_cohortes_dashboard','mart_delais','mart_audits'}
present=set(q("SELECT table_name FROM information_schema.tables WHERE table_schema='marts'").table_name)
if not required.issubset(present):
    st.error('Préparation incomplète : lance python analyses/preparer_dashboard.py avant d’ouvrir le dashboard.')
    st.stop()
options=q('SELECT DISTINCT produit,region,canal_distribution FROM marts.mart_portefeuille_mensuel')
months=q('SELECT DISTINCT mois FROM marts.mart_portefeuille_mensuel ORDER BY 1').mois.dt.date.tolist()
with st.sidebar:
    st.markdown('## ◈ BORÉAL')
    st.caption('ASSURANCES · OBSERVATOIRE DATA')
    page=st.radio('Navigation',['Portefeuille','Technique et clients','Exploitation'])
    st.divider()
    period=st.select_slider('Période observée',options=months,value=(months[0],months[-1]),format_func=lambda d:d.strftime('%m/%Y'))
    products=st.multiselect('Produits',sorted(options.produit.dropna().unique()),default=sorted(options.produit.dropna().unique()))
    regions=st.multiselect('Régions',sorted(options.region.dropna().unique()),default=sorted(options.region.dropna().unique()))
    channels=st.multiselect('Canaux',sorted(options.canal_distribution.dropna().unique()),default=sorted(options.canal_distribution.dropna().unique()))
    threshold=st.number_input('Seuil orange du S/P (%)',min_value=1.0,max_value=100.0,value=70.0,step=1.0)/100
    st.caption('70 % : hypothèse de frais de 25–30 %. Rouge à 100 %.')
    if st.button('Actualiser les données'):st.cache_data.clear();st.rerun()
filters={'debut':period[0],'fin':period[1],'produits':products,'regions':regions,'canaux':channels}
condition,params=where(filters)

st.markdown('<div class="eyebrow">MARCHÉS AUTO & HABITATION · EXTRACTION AU 30 JUIN 2025</div>',unsafe_allow_html=True)
st.title({'Portefeuille':'Piloter le portefeuille','Technique et clients':'Comprendre les écarts et les clients','Exploitation':'Surveiller la chaîne et les délais'}[page])
st.caption(f'{period[0]:%m/%Y} → {period[1]:%m/%Y} · {len(products)} produit(s) · {len(regions)} région(s) · {len(channels)} canal(aux)')

with st.expander('Définitions des indicateurs et périmètres'):
    st.markdown('''**Exposition** : jours de couverture / 365,25 ; effet inclus, résiliation exclue. **Prime acquise** : prime annuelle × exposition.
**Fréquence** : sinistres retenus / années-polices. **Coût moyen** : charge retenue / sinistres retenus. **Prime moyenne** : primes acquises / exposition.
**Charge** : payé + réserve restante conventionnelle des dossiers ouverts. **S/P** : charge retenue / primes acquises ; sans suite et rejetés exclus, suivis séparément.
**Résiliation** : événement à sa date réelle ; taux = événements / exposition. **Contrats actifs** : stock à la fin du dernier mois sélectionné ; les stocks ne s'additionnent pas.
**Valeur client** : primes acquises moins paiements, hors frais et réserves. **Rétention** : présence au même produit à un anniversaire entièrement observable.
**Audits** : taux de confirmation parmi les seuls audités valides. **Clôture** : date absente ; dernier règlement des CLOTURE présenté uniquement comme approximation distincte.
Les profils clients sont ceux de juin 2025. 2025 est partielle, les sinistres récents moins développés. Les délais des seuls dossiers déjà réglés ne décrivent pas les dossiers encore en attente.''')

if page=='Portefeuille':
    monthly=q(aggregate_sql('mois',condition),params)
    if monthly.empty:st.info('Aucune donnée pour ces filtres.');st.stop()
    total=ratios(pd.DataFrame([monthly[MEASURES].sum()])).iloc[0]
    stock=q('SELECT coalesce(sum(contrats_actifs),0) stock FROM marts.mart_portefeuille_mensuel WHERE '+condition+' AND mois=?',params+[period[1]]).stock.iloc[0]
    row=st.columns(3)
    for box,label,value,helptext in [(row[0],'Primes acquises',euro(total.primes_acquises),'Primes proratisées à la durée couverte.'),(row[1],'Contrats actifs',number(stock),'Stock au dernier jour du dernier mois sélectionné.'),(row[2],'S/P technique',pct(total.ratio_sp),'Charge retenue évaluée au 30/06/2025 / primes acquises de la période.')]:box.metric(label,value,help=helptext)
    row=st.columns(3)
    row[0].metric('Fréquence / 100 années-polices',f'{100*total.frequence:.2f}'.replace('.',',') if pd.notna(total.frequence) else '—',help='Sinistres retenus / exposition × 100 ; les arrondis des cartes sont descriptifs.')
    row[1].metric('Coût moyen',euro(total.cout_moyen))
    row[2].metric('Taux de résiliation / année-police',pct(total.taux_resiliation))
    if pd.notna(total.ratio_sp):
        if total.ratio_sp>=1:st.error('S/P ≥ 100 % : examiner les segments contributeurs ; la charge atteint ou dépasse les primes.')
        elif total.ratio_sp>=threshold:st.warning('S/P au-dessus du seuil : analyser les gros sinistres et le mix des risques avant de décider.')
        else:st.success('S/P sous le seuil choisi. Vérifier les gros dossiers et l’incertitude avant toute conclusion sur la rentabilité.')
    history_filter=dict(filters,debut=pd.Timestamp(period[0]).date().replace(year=period[0].year-1),fin=pd.Timestamp(period[1]).date().replace(year=period[1].year-1))
    prev_cond,prev_params=where(history_filter)
    previous=q(aggregate_sql('mois',prev_cond),prev_params)
    compared=compare_previous_year(monthly,previous)
    a,b=st.columns(2)
    with a:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=compared.mois,y=compared.primes_acquises,name='Période',mode='lines',line={'color':'#168678','width':3},hovertemplate='%{x|%m/%Y}<br>Primes : %{y:,.0f} €<extra></extra>'))
        fig.add_trace(go.Scatter(x=compared.mois,y=compared.primes_n_1,name='Même mois N-1',mode='lines',line={'color':'#9baab2','dash':'dot'},hovertemplate='Mois aligné N-1<br>Primes : %{y:,.0f} €<extra></extra>'))
        fig.update_layout(title='Comparer les primes aux mêmes mois de N-1',yaxis_title='Primes acquises (€)');chart(fig)
    with b:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=compared.mois,y=100*compared.ratio_sp,name='S/P',mode='lines',line={'color':'#183e58','width':3},hovertemplate='%{x|%m/%Y}<br>S/P : %{y:.1f} %<extra></extra>'))
        fig.add_trace(go.Scatter(x=compared.mois,y=100*compared.sp_n_1,name='Même mois N-1',mode='lines',line={'color':'#9baab2','dash':'dot'}))
        fig.add_hline(y=threshold*100,line_dash='dot',line_color='#dc9e36')
        fig.update_layout(title='Repérer les mois de forte charge',yaxis_title='S/P (%)');chart(fig)
    st.caption('Le S/P est classé par survenance, avec les règlements connus au 30/06/2025. N-1 manquant reste vide. Les mois sans exposition ont un ratio inconnu.')
    st.dataframe(ratios(monthly),width='stretch',hide_index=True)
    download(ratios(monthly),'Télécharger les indicateurs filtrés','portefeuille')

elif page=='Technique et clients':
    technical,clienttab=st.tabs(['Technique','Clients'])
    with technical:
        axis=st.selectbox('Comparer les segments par',['zone_risque','formule','canal_distribution','tranche_age','produit'],format_func=lambda x:{'zone_risque':'Zone de risque','formule':'Formule','canal_distribution':'Canal','tranche_age':'Âge','produit':'Produit'}[x])
        segments=ratios(q(aggregate_sql(axis,condition),params))
        if segments.empty:st.info('Aucun segment pour ces filtres.')
        else:
            segments['S/P (%)']=100*segments.ratio_sp
            fig=px.bar(segments,x=axis,y='S/P (%)',color='S/P (%)',color_continuous_scale=['#4fa69b','#dc9e36','#c3635c'],hover_data=['exposition_annees','nb_sinistres_retenus','primes_acquises'],title='Prioriser les segments avec un S/P élevé et une exposition suffisante')
            fig.add_hline(y=threshold*100,line_dash='dot');chart(fig)
            st.dataframe(segments,width='stretch',hide_index=True)
            download(segments,'Télécharger les segments filtrés','segments')
        annual=ratios(q(aggregate_sql('annee',condition),params))
        st.subheader('Expliquer la variation du S/P')
        st.caption('Calcul sur les mois sélectionnés et les filtres courants. Comparer seulement des années couvrant les mêmes mois ; 2025 est partielle.')
        if len(annual)>1:
            changes=[]
            for i in range(1,len(annual)):
                old,new=annual.iloc[i-1],annual.iloc[i]
                effects=shapley([old.frequence,old.cout_moyen,old.prime_moyenne],[new.frequence,new.cout_moyen,new.prime_moyenne])
                for name,effect in zip(['Fréquence','Coût moyen','Prime moyenne'],effects):changes.append({'Comparaison':f'{int(old.annee)} → {int(new.annee)}','Facteur':name,'Points de S/P':100*effect})
            chart(px.bar(pd.DataFrame(changes),x='Comparaison',y='Points de S/P',color='Facteur',barmode='relative',title='Décomposer la variation : fréquence, coût et prime moyenne'))
        else:st.info('Sélectionne au moins deux années pour afficher une variation.')
        if 'mart_ic' in present:
            with st.expander('Incertitude et tests : résultats globaux non filtrés'):
                st.caption('Ces résultats couvrent tout le portefeuille 2020–juin 2025 ; les filtres ci-dessus ne leur sont pas appliqués.')
                st.dataframe(q("SELECT indicateur,estimation,ic_bas,ic_haut,methode FROM marts.mart_ic WHERE axe='global'"),hide_index=True,width='stretch')
                st.dataframe(q('SELECT comparaison,p_value,p_value_holm,interpretation FROM marts.mart_tests_statistiques'),hide_index=True,width='stretch')
    with clienttab:
        cohort_condition,cohort_params=where(filters,"date_trunc('month',date_entree)")
        group=st.selectbox('Détention au début du suivi',['Tous','Mono à entrée','Multi à entrée'])
        extra='' if group=='Tous' else ' AND detention_entree=?'
        retention=q('''SELECT cohorte,produit,anciennete,count(*) effectif,
            count(*) FILTER(WHERE retenu_anniversaire)::DOUBLE/count(*) taux
            FROM marts.mart_cohortes_dashboard WHERE '''+cohort_condition+' AND observable'+extra+' GROUP BY 1,2,3 ORDER BY 1,2,3',cohort_params+([] if group=='Tous' else [group]))
        st.caption('Rétention : filtre de période appliqué à la date d’entrée ; canal = canal de première souscription au produit. Les cases non entièrement observables restent vides. Détention mono/multi fixée à l’entrée.')
        for product in products:
            subset=retention[retention.produit==product]
            if subset.empty:continue
            matrix=subset.pivot(index='cohorte',columns='anciennete',values='taux')
            matrix=matrix.reindex(columns=range(0,6))
            fig=px.imshow(matrix*100,text_auto='.1f',color_continuous_scale=['#edf5f3','#168678'],zmin=0,zmax=100,aspect='auto',labels={'x':'Ancienneté (ans)','y':'Cohorte','color':'Retenus (%)'},title=f'{product} : suivre les cohortes sur les anniversaires observables')
            fig.update_xaxes(side='bottom');chart(fig)
        with st.expander('Comparer mono/multi à 1 an, à cohorte et produit fixés'):
            comparison=q("""SELECT cohorte,produit,detention_entree,count(*) effectif,
                count(*) FILTER(WHERE retenu_anniversaire)::DOUBLE/count(*) taux_retention
                FROM marts.mart_cohortes_dashboard WHERE """+cohort_condition+
                ' AND observable AND anciennete=1 GROUP BY 1,2,3 ORDER BY 1,2,3',cohort_params)
            st.dataframe(comparison,hide_index=True,width='stretch')
            st.caption('Comparaison descriptive : le groupe est fixé à l’entrée, sans interprétation causale.')
        values=q('''SELECT client_id_maitre,region,sum(primes_acquises) primes_acquises,
             sum(paiements_flux) sinistres_payes,sum(primes_acquises-paiements_flux) valeur_observee
             FROM marts.mart_contrat_mois WHERE '''+condition+' GROUP BY 1,2',params)
        if not values.empty:
            positive=values[values.valeur_observee>0].sort_values(['valeur_observee','client_id_maitre'],ascending=[False,True]).copy()
            a,b=st.columns(2)
            a.metric('Valeur observée de la sélection',euro(values.valeur_observee.sum()),help='Primes acquises moins paiements datés de la période ; contrats correspondant aux filtres.')
            b.metric('Valeurs clients négatives',euro(values.loc[values.valeur_observee<0,'valeur_observee'].sum()))
            if not positive.empty:
                positive['Clients à valeur positive (%)']=100*np.arange(1,len(positive)+1)/len(positive)
                positive['Valeur positive cumulée (%)']=100*positive.valeur_observee.cumsum()/positive.valeur_observee.sum()
                chart(px.line(positive.iloc[np.unique(np.linspace(0,len(positive)-1,min(500,len(positive))).astype(int))],x='Clients à valeur positive (%)',y='Valeur positive cumulée (%)',title='Mesurer la concentration des valeurs positives ; suivre les pertes séparément'))
            st.caption('Valeur limitée aux contrats et paiements correspondant aux filtres ; hors frais et réserves. Le Pareto exclut explicitement les valeurs négatives. Il ne mesure pas une valeur future.')
            st.dataframe(values.sort_values('valeur_observee').head(15),hide_index=True,width='stretch')
            download(values,'Télécharger les valeurs clients filtrées','valeur_clients')
        snapshot=q('''SELECT count(*) FILTER(WHERE nb_contrats_actifs>0) actifs,
             count(*) FILTER(WHERE multi_detenteur_actuel) multi FROM marts.mart_valeur_client''').iloc[0]
        st.info(f'Photo globale au 30/06/2025, non filtrée : {number(snapshot.multi)} multi-détenteurs sur {number(snapshot.actifs)} clients actifs ({pct(snapshot.multi/snapshot.actifs) if snapshot.actifs else "—"}).')

else:
    st.subheader('État de la chaîne · périmètre global')
    st.caption('Les filtres commerciaux ne s’appliquent pas aux journaux, à la qualité ni aux tests. Fraîcheur métier évaluée à la date d’extraction du 30/06/2025.')
    for name,label in [('exploitation_sources','Fraîcheur et dernier chargement par source'),('exploitation_tests','Résultats des tests'),('exploitation_qualite','Rejets et anomalies par règle')]:
        if name in present:
            frame=q('SELECT * FROM marts.'+name)
            with st.expander(label,expanded=name=='exploitation_sources'):
                st.dataframe(frame,width='stretch',hide_index=True)
    st.subheader('Délais et audits · sélection commerciale')
    delay_condition,delay_params=where(filters,"date_trunc('month',date_survenance)")
    delays=q('''SELECT garantie,count(*) nb_dossiers,
        count(delai_premier_reglement_jours) nb_premiers_reglements_observes,
        median(delai_declaration_jours) declaration_mediane,
        quantile_cont(delai_declaration_jours,.9) declaration_p90,
        median(delai_premier_reglement_jours) premier_reglement_mediane,
        quantile_cont(delai_premier_reglement_jours,.9) premier_reglement_p90,
        median(delai_dernier_reglement_clotures_jours) dernier_reglement_clotures_mediane
        FROM marts.mart_delais WHERE '''+delay_condition+' GROUP BY 1 ORDER BY 1',delay_params)
    if not delays.empty:
        chart(px.bar(delays,x='garantie',y='premier_reglement_p90',hover_data=['nb_dossiers','nb_premiers_reglements_observes'],title='Examiner les garanties aux délais de premier règlement les plus longs',labels={'premier_reglement_p90':'P90 observé (jours)'}))
        st.dataframe(delays,width='stretch',hide_index=True)
        download(delays,'Télécharger les délais filtrés','delais')
    st.warning('Date de clôture indisponible. Le dernier règlement des seuls dossiers CLOTURE est une approximation distincte. Les dossiers non réglés ont un délai inconnu, et les quantiles observés peuvent sous-estimer les délais futurs.')
    audit=q('''SELECT count(*) FILTER(WHERE audite) audits,
        count(*) FILTER(WHERE audite AND fraude_confirmee) confirmes,
        coalesce(sum(charge) FILTER(WHERE audite AND fraude_confirmee),0) charge_confirmee
        FROM marts.mart_delais WHERE '''+delay_condition,delay_params).iloc[0]
    row=st.columns(3)
    row[0].metric('Dossiers audités',number(audit.audits));row[1].metric('Confirmation parmi les audités',pct(audit.confirmes/audit.audits) if audit.audits else '—');row[2].metric('Charge des dossiers confirmés',euro(audit.charge_confirmee))
    st.caption('Audits sur la population sélectionnée par date de survenance. Le taux ne s’applique pas aux non-audités. Les montants concernés ne sont pas des économies démontrées.')

st.divider()
st.caption(f'Boréal Assurances · données pseudonymisées · affichage calculé en {time.perf_counter()-START:.2f} s · extraction au 30/06/2025')
