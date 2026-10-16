# Deployment Plan: Banking Customer Segmentation

## Goal
Turn the analysis notebook into a live web dashboard that anyone can open with a link. It runs on free hosting (Streamlit Community Cloud), straight from this GitHub repo.

## Architecture

```
GitHub repo (code + data)
        │  auto-deploy on every push
        ▼
Streamlit Community Cloud
   app.py ─ loads data/High_Value_Customer_Identification_Final.xlsx
          ─ Customer Value Score (MinMaxScaler + weights)
          ─ K-Means segmentation (StandardScaler + KMeans)
          ─ Value-vs-Potential matrix + priority list
        ▼
Public URL  →  https://<your-app-name>.streamlit.app
```

## What the app shows
| Tab | Content |
|---|---|
| KPI row | Customers, number of clusters, top segment's spend share, low-value/high-potential count |
| Segments | Customers per segment, spend share, average profile per segment |
| Value vs Potential | Scatter plot of the four opportunity groups |
| Target list | Filter by High/Medium/Low priority and download as CSV |
| Customer lookup | Pick a customer ID to see their segment, scores and details |
| Sidebar | Upload a new workbook and change the number of clusters (2–8) |

## Phases

| Phase | Task | Done when |
|---|---|---|
| 1. Prepare | Notebook cleaned, `app.py` and `requirements.txt` added | App runs locally |
| 2. Test locally | `streamlit run app.py` on your laptop | Dashboard opens at http://localhost:8501 |
| 3. Version control | Push all files to GitHub | Files visible on the repo page |
| 4. Deploy | Streamlit Community Cloud → New app → choose repo, branch `main`, file `app.py` | Public URL works |
| 5. Verify | Open every tab, try the slider and the CSV download | No errors |
| 6. Share | Add the live link to the README, resume and LinkedIn | Recruiters can open it |

## Maintenance
- Every `git push` to `main` redeploys the app automatically.
- New data: replace the Excel file in `data/` and push, or upload a file through the sidebar.
- Apps on the free plan go to sleep after a few days without visitors. Opening the link wakes the app up in about 30 seconds.

## Future improvements
- Choose k with the elbow method and silhouette score
- Add a premium-eligibility classifier (Logistic Regression / Random Forest)
- Connect to a database instead of an Excel file
- Add login if the app ever uses real customer data
