# ResearchFlow User Onboarding Guide

**Welcome to ResearchFlow!** This guide will help you get started with the platform and make the most of its powerful research workflow features.

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [First Login](#first-login)
3. [Creating Your First Project](#creating-your-first-project)
4. [Understanding the 20-Stage Workflow](#understanding-the-20-stage-workflow)
5. [Working with Data](#working-with-data)
6. [AI-Powered Features](#ai-powered-features)
7. [Collaboration](#collaboration)
8. [Common Tasks](#common-tasks)
9. [Troubleshooting](#troubleshooting)
10. [Getting Help](#getting-help)

---

## Getting Started

### Prerequisites

- Modern web browser (Chrome, Firefox, Safari, or Edge)
- Active ResearchFlow account
- Basic understanding of research workflows
- (Optional) Institutional access for HIPAA-compliant features

### System Requirements

- **Minimum:** 4GB RAM, broadband internet connection
- **Recommended:** 8GB+ RAM, stable internet connection
- **Browser:** Latest version of Chrome, Firefox, Safari, or Edge

---

## First Login

### Step 1: Access the Platform

1. Navigate to your ResearchFlow instance URL (e.g., `https://researchflow.yourorg.com`)
2. You'll see the login page with options for:
   - Email/Password authentication
   - Single Sign-On (if configured)
   - Two-Factor Authentication (if enabled)

### Step 2: Complete Your Profile

After first login, you'll be prompted to complete your profile:

- **Basic Information:** Name, email, role
- **Organization:** Select or create your organization
- **Research Interests:** Add keywords for better collaboration
- **Notification Preferences:** Configure how you want to be notified

### Step 3: Tour the Dashboard

Your dashboard shows:
- **Active Projects:** Current research projects
- **Recent Activity:** Latest updates across your projects
- **Pending Approvals:** Governance gates requiring your attention
- **Quick Actions:** Start new project, upload data, view analytics

---

## Creating Your First Project

### Start a New Project

1. Click **"New Project"** from the dashboard
2. Fill in project details:
   - **Project Name:** Descriptive title for your research
   - **Description:** Brief overview of research objectives
   - **Governance Mode:** 
     - **DEMO:** For testing with synthetic data
     - **LIVE:** For real research with PHI protection
   - **Team Members:** Add collaborators and assign roles

### Project Roles

- **ADMIN:** Full control over project and settings
- **RESEARCHER:** Can execute workflows and analyze data
- **STEWARD:** Can approve governance gates and review PHI
- **VIEWER:** Read-only access to project and results

---

## Understanding the 20-Stage Workflow

ResearchFlow follows a structured 20-stage research pipeline:

### **Phase 1: Planning (Stages 1-4)**
1. **Topic Declaration:** Define research question using PICO framework
2. **Literature Search:** AI-powered literature review
3. **IRB Proposal:** Generate IRB application draft
4. **Planned Extraction:** Define variables and data requirements

### **Phase 2: Data Preparation (Stages 5-8)**
5. **PHI Scanning:** Detect and protect sensitive health information
6. **Schema Extraction:** Analyze dataset structure
7. **Data Scrubbing:** Clean and validate data quality
8. **Data Validation:** Ensure data meets research standards

### **Phase 3: Analysis (Stages 9-12)**
9. **Variable Selection:** Choose analysis variables
10. **Statistical Planning:** Define statistical approach
11. **Statistical Execution:** Run statistical analyses
12. **Supplementary Analysis:** Additional analyses and visualizations

### **Phase 4: Manuscript (Stages 13-16)**
13. **Manuscript Ideation:** Plan manuscript structure
14. **Introduction:** Generate introduction with literature integration
15. **Methods:** Document methodology
16. **Results:** Present findings with tables and figures

### **Phase 5: Review & Publication (Stages 17-20)**
17. **Discussion:** Interpret findings and limitations
18. **References:** Generate bibliography
19. **Journal Selection:** Identify target journals
20. **Conference Preparation:** Prepare presentations

---

## Working with Data

### Uploading Data

1. Navigate to your project
2. Click **"Upload Data"** in Stage 4 (Planned Extraction)
3. Supported formats:
   - CSV files
   - Excel files (.xlsx, .xls)
   - TSV files
   - Multiple file upload for merging

### Data Quality Checks

ResearchFlow automatically:
- Detects column types (numeric, categorical, date, etc.)
- Identifies missing values
- Flags outliers
- Calculates completeness scores
- Detects potential PHI

### PHI Protection (LIVE Mode)

In LIVE mode, all data goes through PHI scanning:
- **Automatic Detection:** Identifies names, SSNs, dates, addresses
- **Human Review:** Governance gate for steward approval
- **Deidentification:** Options for masking or removing PHI
- **Audit Trail:** Complete log of PHI handling

---

## AI-Powered Features

### AI Assistance Available

ResearchFlow uses AI for:
- **Literature Search:** Semantic search across medical literature
- **IRB Drafting:** Generate compliant IRB applications
- **Variable Recommendation:** Suggest relevant analysis variables
- **Statistical Guidance:** Recommend appropriate tests
- **Manuscript Generation:** Draft IMRaD sections
- **Citation Management:** Automatically format references

### Approving AI Requests

In LIVE mode, AI calls require approval:
1. Review the AI request details
2. Check estimated cost
3. Verify no PHI will be sent
4. Approve or deny the request
5. Monitor AI response quality

### AI Quality Controls

- **Cost Tracking:** See estimated and actual costs per AI call
- **Model Selection:** Choose appropriate AI models for tasks
- **Output Review:** All AI outputs flagged for human review
- **Feedback Loop:** Rate AI outputs to improve quality

---

## Collaboration

### Real-Time Collaboration

ResearchFlow supports real-time collaboration:
- **Live Editing:** Multiple users can edit simultaneously
- **Comments:** Add inline comments on any content
- **Version History:** Track all changes with timestamps
- **Presence Indicators:** See who's currently viewing

### Sharing & Permissions

Share projects with:
- **Internal Users:** Add team members from your organization
- **External Collaborators:** Invite via email (if enabled)
- **Read-Only Links:** Generate shareable links for viewing

### Notifications

Stay updated with:
- **Email Notifications:** For governance approvals and mentions
- **In-App Alerts:** Real-time updates on project activity
- **Digest Emails:** Daily or weekly summaries (configurable)

---

## Common Tasks

### Running Statistical Analysis

1. Navigate to Stage 11 (Statistical Execution)
2. Select your analysis type:
   - T-tests (independent, paired)
   - ANOVA (one-way, two-way)
   - Regression (linear, logistic)
   - Correlation analysis
   - Survival analysis
3. Configure analysis parameters
4. Review assumption checks
5. Execute analysis
6. Download results in multiple formats

### Generating Manuscript Sections

1. Complete prerequisite stages (data analysis)
2. Navigate to manuscript stages (13-17)
3. Click **"Generate with AI"** button
4. Review AI-generated content
5. Edit and refine as needed
6. Export to Word, PDF, or LaTeX

### Managing References

ResearchFlow automatically:
- Extracts citations from literature search
- Formats references in multiple styles (APA, MLA, Vancouver)
- Generates bibliography
- Checks for missing citations
- Exports to reference managers (Zotero, EndNote)

### Exporting Results

Export options:
- **Complete Bundle:** All artifacts, data, and documentation
- **Manuscript:** Word/PDF with embedded figures
- **Statistical Reports:** Formatted tables and results
- **Raw Data:** CSV exports with codebook
- **Audit Trail:** Complete governance log

---

## Troubleshooting

### Common Issues

**Issue: Can't upload data file**
- **Solution:** Check file size (<100MB), format (CSV/Excel), and permissions

**Issue: AI request stuck in pending**
- **Solution:** Contact your project steward to approve the request

**Issue: Statistical analysis failing**
- **Solution:** Check data quality, missing values, and variable selection

**Issue: Can't see project collaborators' changes**
- **Solution:** Refresh page, check internet connection, verify permissions

### Performance Tips

- Use Chrome or Firefox for best performance
- Close unnecessary browser tabs
- Clear browser cache if experiencing slowness
- Use "Export" feature for large datasets rather than viewing in-browser

### Data Recovery

If you lose work:
- Check **Version History** for previous saves
- Contact support for backup restoration
- Review **Audit Trail** for recent activity

---

## Getting Help

### Documentation

- **User Guides:** [docs/guides/](../guides/)
- **API Documentation:** [docs/api/](../api/)
- **Video Tutorials:** [platform.researchflow.com/tutorials]
- **FAQ:** [docs/FAQ.md](../FAQ.md)

### Support Channels

- **In-App Help:** Click "?" icon in top navigation
- **Email Support:** support@researchflow.com
- **Slack Community:** #researchflow-users
- **Office Hours:** Tuesdays 2-3pm ET

### Training Resources

- **Onboarding Webinar:** Weekly on Wednesdays
- **Advanced Workshops:** Monthly deep-dives on specific features
- **Video Library:** 50+ tutorial videos
- **Sample Projects:** Pre-loaded examples for learning

---

## Best Practices

### Data Management

✅ **DO:**
- Upload clean, well-structured data
- Document data sources and collection methods
- Use meaningful variable names
- Test with DEMO mode first

❌ **DON'T:**
- Upload data without proper permissions
- Share projects containing PHI without authorization
- Skip data quality checks
- Ignore governance gates

### AI Usage

✅ **DO:**
- Review all AI-generated content
- Provide feedback on AI outputs
- Use AI as a starting point, not final product
- Monitor AI costs

❌ **DON'T:**
- Blindly trust AI outputs
- Send PHI to AI without approval
- Use AI for clinical decision-making
- Ignore AI quality warnings

### Collaboration

✅ **DO:**
- Communicate with team via comments
- Document significant decisions
- Use version history to track changes
- Assign clear roles and responsibilities

❌ **DON'T:**
- Make major changes without discussion
- Work offline without syncing
- Override others' work without communication
- Ignore notifications from collaborators

---

## Next Steps

Now that you're familiar with the basics:

1. **Complete the Interactive Tutorial** (if available)
2. **Create a Test Project** in DEMO mode
3. **Join the Community** on Slack
4. **Attend a Training Webinar**
5. **Explore Advanced Features** as you get comfortable

**Welcome to ResearchFlow - Happy Researching! 🚀**

---

*Last Updated: February 4, 2026*  
*Version: 1.0.0*  
*Questions? Contact support@researchflow.com*