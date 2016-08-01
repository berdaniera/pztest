##############################
# PZ test analysis
# Aaron Berdanier
# aaron.berdanier@gmail.com
# 1 August 2016

from datetime import datetime, timedelta
import pandas as pa
import numpy as np
from matplotlib import pyplot as plt
import seaborn
import os
import re

def getpredictors(da):
    # ACTIVITY METRICS
    # Number of days with account record
    ndays = (max(da.date)-min(da.date)).days
    # Average daily balance, filling non-transaction days
    avbal = da.balance.resample('D').last().ffill().mean()
    # Transactions per day
    ntran = len(da)/ndays*1.
    # Expenses covered by deposits
    deposits = sum(da.amount[da.text.str.contains("Deposit of Funds")])
    condition = (da.text.str.contains("Pay Bill to") | da.text.str.contains("Merchant Payment") | da.text.str.contains("Customer Withdrawal"))
    withdraw = -sum(da.amount[condition])
    expen = (deposits - withdraw)/ndays*1.
    # Average deposit per day
    depos = deposits/ndays*1.
    # Average airtime purchase amount
    airti = sum(da.amount[da.text.str.contains("Airtime Purchase")])/ndays*1.
    # M-Shwari savings account usage
    savin = 1 if len(da[da.text.str.contains("M-Shwari")]) > 0 else 0
    #
    # NETWORK METRICS
    # Number of unique people interactions - scaled by n days
    transactions = da.text[(da.text.str.contains('Customer Transfer to')|da.text.str.contains('Funds received from'))]
    peopl = 1.*len(set([x.split("-")[1].lower() for x in transactions.tolist()]))/ndays
    # Frequency of giving transfers
    givin = 1.*len(da[da.text.str.contains('Customer Transfer to')])#/ndays
    # Frequency of receiving transfers
    recei = 1.*len(da[da.text.str.contains('Funds received from')])#/ndays
    # Giving-receiving index: higher = giving more than receiving in their network
    givrec = (givin - recei)/ndays
    # Unique external lenders
    lende = len(set(da.text[da.text.str.contains('Business Payment from')]))
    # Average loan amount per day
    loans = 1.*sum(da.amount[da.text.str.contains('Business Payment')])/ndays
    return np.array([ndays, avbal, ntran, expen, airti, savin, peopl, givrec, lende, loans])

ff = os.listdir(d + "data/")

# initialize data
X = []
y = []
for i in xrange(len(ff)):
    fi = ff[i]
    da = pa.read_csv(d+'data/'+ff[i],header=None,names=["id","date","text","status","amount","balance"])
    da.date = pa.to_datetime(da.date)
    da = da.set_index(da.date)
    #X[i] = getpredictors(da)
    ld = da[da.text.str.contains("M-Shwari Loan")] # [['date','text','amount','balance']]
    if(len(ld)>0 and any(ld.text.str.contains("Disburse"))): # get risk only if they have an M-Shwari loan record
        ##### Get training data
        ldr = ld.sort_index() # sort ascending
        # start with first loan disbursement
        firstloan = next((i for i, v in enumerate(ldr.text.tolist()) if "Disburse" in v), None)
        ldr = ldr[firstloan:]
        ldr = ldr[ldr['date'] <= da.date[0]-timedelta(days=30)]
        delinquentdates = []
        loandates = ldr.date[ldr.text.str.contains("Disburse")]
        for di in loandates: # loop through loans
            debt = ldr.ix[di].amount*1.075 # add the loan amount
            ldr = ldr.drop(di) # pop it off
            # find all payments within 30 days of loan
            s = (ldr['date'] <= di+timedelta(days=30)) & (ldr['text'] == "M-Shwari Loan Repayment")
            ld2 = ldr[s]
            for payi in xrange(len(ld2)):
                debt += ld2.amount[payi] # pay down the debt
                ldr = ldr.drop(ld2.date[payi]) # remove the payment
                if(debt < 0): # paid it off
                    break
            if(debt > 0): # delinquent loan...
                delinquentdates.append(di)
        # get the last delinquent loan
        if(len(delinquentdates) > 0):
            preds = getpredictors(da[da.date < delinquentdates[-1]])
            X.append(preds)# all of the data before the delinquent loan
            y.append(0)
        else:
            preds = getpredictors(da)
            X.append(preds)
            y.append(1) #


# Fit model
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.metrics import confusion_matrix, accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.grid_search import GridSearchCV

pipe = Pipeline([('scl',StandardScaler()),
    ('pca',PCA(n_components=2)),
    ('clf',LogisticRegression(class_weight='balanced'))])
pipe.fit(X, y)
preds = pipe.predict(X)
accuracy_score(y,preds)
confusion_matrix(y,preds)



#### Get components and important variables
column_labels = ['PCA 1','PCA 2']
row_labels = ['ndays','avgbal','ntrans','deposit-expense','airtime','savings','npeople','giving-receiving','lendern','loanamt']
data = pipe.named_steps['pca'].components_.transpose() * pipe.named_steps['clf'].coef_ * 100
fig, ax = plt.subplots()
heatmap = ax.pcolor(data, cmap=plt.cm.coolwarm_r)
ax.set_xticks(np.arange(data.shape[1])+0.5, minor=False)
ax.set_yticks(np.arange(data.shape[0])+0.5, minor=False)
ax.invert_yaxis()
ax.xaxis.tick_top()
ax.set_yticklabels(row_labels, minor=False)
ax.set_xticklabels(column_labels, minor=False)
#plt.savefig('/home/aaron/Desktop/PZ1.pdf')
plt.show()



######## PREDICT SCORES FOR ALL PEOPLE

xl = pa.read_excel(d+"PZborrowers.xlsx",skiprows=1,names=['name','id','date'])

XX = []
order = [0]*len(ff) # order for sorting the predicted scores
for i in xrange(len(ff)):
    fi = ff[i]
    order[i] = np.where(xl.id==int(fi.split(".")[0]))[0][0]
    da = pa.read_csv(d+'data/'+ff[i],header=None,names=["id","date","text","status","amount","balance"])
    da.date = pa.to_datetime(da.date)
    da = da.set_index(da.date)
    XX.append(getpredictors(da))

predprob = np.array([x[1] for x in pipe.predict_proba(XX)])
Scores = [int(x) for x in predprob*100]
Scores = [x if x!= 0 else 1 for x in Scores] # zero scores get 1

# HISTOGRAM OF PREDICTED SCORES
plt.hist(Scores,bins=10,range=(0,100))
#plt.show()
plt.savefig('/home/aaron/Desktop/PZ2.pdf')

# Add scores to sheet
xl['score'] = [x[1] for x in sorted(zip(order, Scores))]

xl.to_excel(d+"Berdanier_PZresults.xlsx",header=["Name","ID Number","Date","Predicted Score"],index=False)

##############################

pa.DataFrame(StandardScaler().fit_transform(XX)).to_excel('/home/aaron/Desktop/pzs.xlsx',header=row_labels,index=False)
