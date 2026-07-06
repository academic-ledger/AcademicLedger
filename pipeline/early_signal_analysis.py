"""Multi-field early-signal analysis: do early citations predict eventual (10-year) within-cohort rank?

Runs on the QaL's own back-tested calibration cohorts (DB works.counts_by_year): the three
Decision-Sciences subfields (Management Science & OR, Information Systems & Management, General
Decision Sciences), publication years 2008-2015, cohorts >=200 papers (~302k papers total).
For each age 1..9 it aggregates (paper-weighted) Spearman rho, Kendall tau-b, AUC for the eventual
top decile, % uncited, share of eventual citations accrued, and % of the eventual top decile still
uncited. Feeds pipeline/make_fig_early_signal.py and docs/early_signal_result.md.

Run:  PYTHONPATH=pipeline .venv/bin/python pipeline/early_signal_analysis.py
"""

import _env; _env.load_env()
import os, psycopg, json, numpy as np

VINTAGES=range(2008,2016); H=10; MINN=200; AGES=list(range(1,10))
def cum(cby, v, age): return sum(val for y,val in cby.items() if int(y)<=v+age)

def spearman(a,b):
    ra=np.argsort(np.argsort(a,kind='stable')); rb=np.argsort(np.argsort(b,kind='stable'))
    # average ranks for ties
    ra=_avgrank(a); rb=_avgrank(b)
    return np.corrcoef(ra,rb)[0,1]
def _avgrank(x):
    x=np.asarray(x,float); order=np.argsort(x,kind='stable'); r=np.empty(len(x)); i=0
    while i<len(x):
        j=i
        while j+1<len(x) and x[order[j+1]]==x[order[i]]: j+=1
        r[order[i:j+1]]=(i+j)/2+1; i=j+1
    return r
def auc_top(pred, ev):  # AUC for eventual-top-10% (within cohort) from pred
    n=len(ev); thr=np.sort(ev)[int(0.9*n)]
    pos=(ev>=thr)&(ev>0)
    if pos.sum()==0 or pos.sum()==n: return None
    r=_avgrank(pred); s=r[pos].sum(); npos=pos.sum(); nneg=n-npos
    return (s-npos*(npos+1)/2)/(npos*nneg)
def taub(a,b,cap=1400,seed=0):
    a=np.asarray(a,float); b=np.asarray(b,float)
    if len(a)>cap:
        rng=np.random.default_rng(seed); idx=rng.choice(len(a),cap,replace=False); a=a[idx]; b=b[idx]
    da=np.sign(a[:,None]-a[None,:]); db=np.sign(b[:,None]-b[None,:])
    iu=np.triu_indices(len(a),1); sa=da[iu]; sb=db[iu]
    nc=np.sum((sa*sb)>0); nd=np.sum((sa*sb)<0)
    ta=np.sum((sa==0)&(sb!=0)); tb=np.sum((sb==0)&(sa!=0)); n0=len(sa)
    d=np.sqrt((n0-ta)*(n0-tb)); return (nc-nd)/d if d>0 else None

with psycopg.connect(os.environ["DATABASE_URL"]) as c, c.cursor() as cur:
    cur.execute("select primary_subfield, publication_year, counts_by_year from works where publication_year between 2008 and 2015 and counts_by_year is not null")
    rows=cur.fetchall()
print(f"pulled {len(rows)} works", flush=True)
coh={}
for sf,yr,cby in rows:
    if isinstance(cby,str): cby=json.loads(cby)
    coh.setdefault((sf,yr),[]).append(cby)
cohorts=[(k,v) for k,v in coh.items() if len(v)>=MINN]
npapers=sum(len(v) for _,v in cohorts)
print(f"{len(cohorts)} cohorts (>={MINN}), {npapers} papers", flush=True)

# accumulators (size-weighted by cohort n)
agg={a:{'rho':[],'auc':[],'w':[],'unc':0,'ncit_e':0,'ncit_a':0,'nstar':0,'star_unc':0,'ntot':0} for a in AGES}
taub_acc={a:[] for a in AGES}; taub_w={a:[] for a in AGES}
for (sf,yr),cbys in cohorts:
    ev=np.array([cum(cb,yr,H) for cb in cbys],float); n=len(ev)
    thr=np.sort(ev)[int(0.9*n)]; star=(ev>=thr)&(ev>0)
    for a in AGES:
        ca=np.array([cum(cb,yr,a) for cb in cbys],float)
        rho=spearman(ca,ev); au=auc_top(ca,ev)
        d=agg[a]
        if not np.isnan(rho): d['rho'].append(rho*n)
        if au is not None: d['auc'].append(au*n)
        d['w'].append(n)
        d['unc']+=int((ca==0).sum()); d['ntot']+=n
        d['ncit_e']+=ev.sum(); d['ncit_a']+=ca.sum()
        d['nstar']+=int(star.sum()); d['star_unc']+=int(((ca==0)&star).sum())
        if True:
            tb=taub(ca,ev)
            if tb is not None: taub_acc[a].append(tb*n); taub_w[a].append(n)

print("\nage  Spearman  Kendall-taub   AUC(top10%)  %uncited  cites-accrued  %stars-uncited")
res={}
for a in AGES:
    d=agg[a]; W=sum(d['w'])
    rho=sum(d['rho'])/W; auc=sum(d['auc'])/sum(d['w'][:len(d['auc'])]) if d['auc'] else float('nan')
    auc=sum(d['auc'])/W  # weights align (n each)
    unc=100*d['unc']/d['ntot']; accr=100*d['ncit_a']/d['ncit_e']; su=100*d['star_unc']/d['nstar']
    tb= (sum(taub_acc[a])/sum(taub_w[a])) if a in taub_acc and taub_acc[a] else None
    res[a]={'rho':round(rho,3),'taub':round(tb,3) if tb else None,'auc':round(auc,3),'unc':round(unc,1),'accr':round(accr,1),'star_unc':round(su,1)}
    print(f"{a:>3}  {rho:>7.3f}  {('%.3f'%tb) if tb else '   -  ':>10}   {auc:>9.3f}  {unc:>7.1f}  {accr:>11.1f}  {su:>11.1f}")
json.dump({'ncohorts':len(cohorts),'npapers':npapers,'by_age':res}, open("/private/tmp/claude-503/-Users-ulrich-Library-CloudStorage-GoogleDrive-ktulrich-gmail-com-My-Drive-00-AI-CoWorker-General-academicLedger/3025658f-2013-43e0-a540-cbc1a0198bac/scratchpad/early_signal_mf_result.json","w"), indent=2)
print("\nsaved result json")
