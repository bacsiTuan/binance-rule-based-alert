# Group 02 project submission

**Project:** Rule-Based Alerting on Binance Market Data  
**Course:** Python for Engineers  
**Class:** FA26HN MSA42HN  
**Lecturer:** Bùi Trung Hiếu  
**Date:** 15 October 2026

## Submission files

- `Group_02_Project_Report.docx`: editable English report, 23 pages, revised on 16 October 2026.
- `Group_02_Project_Report.pdf`: report for consistent reading and submission.
- `Group_02_Presentation.pptx`: editable English presentation, 18 slides with speaker notes.
- `Group_02_Presentation.pdf`: slides for consistent reading and submission.
- `Group_02_Project_Report.md`: editable plain-text report source.
- `SOURCE_SNAPSHOT.zip` and `SOURCE_MANIFEST.json`: working source snapshot and SHA-256 inventory.
- `evidence/`: actual application screenshots.
- `appendices/`: six-question live AI dataset, rubric, raw answers, scores, numerical checks, test output, five-symbol checks and controlled Telegram acceptance evidence.

## Required content coverage

| Requirement | Report pages | Slides |
| --- | --- | --- |
| Background and user needs | 4 | 2 |
| General and measurable objectives | 5 | 3 |
| Individual task allocation and contribution | 6 | 4 |
| Completed features and boundaries | 7 | 5 |
| Technologies and integration | 8–10 | 6–7 |
| Core code and logic explanation | 11–14 | 7–11 |
| Screenshots and execution results | 15–18 | 12–15 |
| AI dataset, criteria, scale and results | 19–20 | 16–17 |
| Conclusion and future work | 21 | 18 |

Report page 3 contains the contents with linked page references. Pages 22–23 contain references, source information and reproduction commands. The report revision adds the proposed architecture from the team document, updates objective statuses and extends Đào Công Tuấn’s responsibilities to application containerization and documentation. Existing evaluation evidence is dated 15 October 2026. The presentation is unchanged in this report-only revision.

## Team review before submission

Each of the four confirmed members has a 25 percent contribution share. The responsibility descriptions are editable and should be reviewed by the team. No student identifiers were supplied, so the report does not invent them. Add identifiers if the lecturer requires them.

The report describes the actual inspected implementation. It identifies three delivered indicator families, the separate WebSocket prototype, the limits of supported Telegram rules and the small exploratory AI evaluation. It does not claim that the entire original plan is complete.

The source snapshot includes baseline commit `62b5622` and local WebSocket prototype/supporting changes. The repository link may therefore omit the prototype until the team commits it. The included archive is the reproducible source for this report. Earlier repository planning and README status statements may predate the acceptance evidence in this submission.

## Source code link

https://github.com/bacsiTuan/binance-rule-based-alert

English-response change: https://github.com/bacsiTuan/binance-rule-based-alert/pull/11

## Local startup

Extract `SOURCE_SNAPSHOT.zip` into a new directory. See `HUONG_DAN_CHAY.md`, `AI_ASSISTANT.md`, and `BE/README.md` for full configuration. With Docker Desktop running, use PowerShell at the source root:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build --wait
```

In another terminal:

```powershell
cd FE
npm ci
npm run dev
```

Open http://127.0.0.1:5173 and http://127.0.0.1:8000/docs. Configure real provider credentials only in the backend `.env`. The archive contains examples, not working keys. AI calls require the operator's provider account and may incur charges. Telegram sending is opt-in. Run only one scheduler-enabled API process.

## Email draft

**Subject:** `[FA26HN-MSA42HN]_[Nhom_02]_[Rule-Based Alerting on Binance Market Data]`

Dear Mr. Bùi Trung Hiếu,

We are Group 02 from class FA26HN MSA42HN. Please find our project submission for “Rule-Based Alerting on Binance Market Data” attached.

The submission includes our English project report, presentation slides, source snapshot and supporting appendices. The appendices provide application screenshots, test results and a six-question live AI evaluation with its dataset and scoring rubric.

Source code: https://github.com/bacsiTuan/binance-rule-based-alert

Our team members are Phương Hữu Thành Nam, Bùi Quý Đăng, Nguyễn Anh Vũ and Đào Công Tuấn.

Thank you for reviewing our project.

Best regards,  
Group 02  
FA26HN MSA42HN

This is a prepared draft. No email has been sent, and no Git changes have been pushed as part of preparing these submission files.
