# Spreadsheet import (2026-10-16)

Source: `Global_Scientific_Grants_and_Accelerators_TRL4-9.xlsx` (100 rows). Script: `apps/api/scripts/import_sheet.py`.

- **Added to the corpus:** 75 programmes, all `verified: false, confidence: low`.
- **Already in the corpus (not added again):** 25.
- **Skipped:** 0.
- **Crawler watch list:** 72 new URLs added to `data/curate/sites.yaml` (140 total).
- **Rows with something to check:** 26 (below).

Nothing from the sheet was checked against the funders' sites (the build sandbox cannot reach them).
Amounts, TRL bands and descriptions are the sheet's own; treat them as leads until someone opens each link.

## Rows to check

- **1. NSF SBIR Phase I**: The sheet links to NIH's SBIR page; NSF's programme is at seedfund.nsf.gov. US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **2. NSF SBIR Phase II**: The sheet links to NIH's SBIR page; the URL was replaced with NSF's seedfund.nsf.gov. US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **3. NIH SBIR Phase I (R43)**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **4. NIH SBIR Phase II (R44)**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **5. DOE SBIR Phase I**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **6. DOE SBIR Phase II**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **8. NASA SBIR Phase I**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **9. NASA SBIR Phase II**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **10. DARPA SBIR / STTR**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **11. USDA SBIR Phase I**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **12. USDA SBIR Phase II**: US SBIR/STTR is only for US small businesses majority-owned by US citizens or permanent residents. The programmes' authority lapsed on 1 Oct 2025; we could not verify whether it has been renewed since. Check before relying on it.
- **13. AFWERX / DIU Commercialization Fund**: AFWERX (US Air Force) and DIU are separate organisations; check which programme is meant.
- **22. Cyclotron Road (LBNL)**: Check whether cyclotronroad.lbl.gov is still a separate programme page.
- **40. Bied ForLab / EXIST Program**: 'Bied ForLab' is not a programme name we can identify; EXIST itself is real. Check the name.
- **50. Innovate UK Smart Grants**: We believe Innovate UK paused Smart grants in 2025 and could not confirm the current status. Check before showing it as open.
- **55. KIAT Industrial Technology R&D**: The amount range in the sheet is inverted (₩200,000,000 - ₩2,000,000), so the amount was left out.
- **64. SGInnovate Summiteer / Deep Tech Mentorship**: 'Summiteer' is not a programme name we can confirm for SGInnovate.
- **66. GAD (Global Applied DeepTech) Accelerator**: Check the programme name ('Global Applied DeepTech') against start2 Group's site.
- **67. BEP (Badan Ekonomi Kreatif) / BRIN Grants**: The sheet says 'TRN' (read as TRL), and the name mixes BEKRAF/creative-economy and BRIN; check which programme is meant.
- **70. NIAID International R&D Partnerships**: 'International R&D Partnerships' is not a programme name we can confirm at NIAID.
- **72. Temasek Foundation grants**: Temasek Foundation mainly funds community and social programmes; check that it funds company R&D at all.
- **75. INSEAD Venture Competition / SEA Hubs**: INSEAD Venture Competition is, as far as we know, for INSEAD students and alumni. Check eligibility.
- **81. NXPO Policy & Strategic Science Grants**: NXPO is a policy office; most research money flows through TSRI and the PMUs. Check that it runs open calls.
- **84. NSTDA STEP (Science Technology Park) Incubation**: 'STEP' is Chiang Mai University's science park name; NSTDA runs Thailand Science Park. Check the name.
- **85. BCC (Bangkok Business Challenge) / CU Enterprise**: Bangkok Business Challenge is run by Sasin School of Management; the sheet's link is a Chula sustainability page. Check the link.
- **93. KXG (KASIKORN X-Change)**: Check the name 'KASIKORN X-Change'; KBank's venture builder is known as KASIKORN X (KX).

## Already in the corpus

- 1. NSF SBIR Phase I → NSF SBIR/STTR Phase I (America's Seed Fund)
- 3. NIH SBIR Phase I (R43) → NIH SBIR/STTR
- 4. NIH SBIR Phase II (R44) → NIH SBIR/STTR
- 7. ARPA-E OPEN Program → ARPA-E OPEN and Program Funding Opportunities
- 17. Y Combinator → Y Combinator
- 18. Techstars Global Accelerator → Techstars Accelerator
- 19. SOSV / IndieBio → SOSV IndieBio (biotech)
- 21. Activate Global Fellowship → Activate Fellowship
- 22. Cyclotron Road (LBNL) → Activate Fellowship (likely: Cyclotron Road is the Berkeley Lab programme Activate grew out of)
- 26. EIC Pathfinder Open → EIC Pathfinder Open
- 28. EIC Transition → EIC Transition
- 29. EIC Accelerator Open → EIC Accelerator
- 43. Horizon Europe Marie Skłodowska-Curie Actions (MSCA) → MSCA Postdoctoral Fellowships (the sheet row is MSCA in general)
- 45. CDL (Creative Destruction Lab) Oxford / Paris → Creative Destruction Lab
- 59. Enterprise Singapore Startup SG Tech (PoC) → Startup SG Tech (Proof of Concept / Proof of Value)
- 60. Enterprise Singapore Startup SG Tech (PoV) → Startup SG Tech (Proof of Concept / Proof of Value)
- 69. MRANTI Tech Accelerator → MRANTI Technology Commercialisation Programmes (likely)
- 73. Antler Southeast Asia → Antler Residency (Southeast Asia)
- 74. Iterative VC Accelerator → Iterative Accelerator
- 76. NIA Startup Thailand Innovation Grant (NIA STARTUP) → NIA Open Innovation Grant (likely: same 1.5M THB cap)
- 77. NIA Innovation for Economy (FIRST S-CURVE / NEW S-CURVE) → NIA Thematic Innovation Program (likely)
- 78. NIA Social Innovation Project → NIA Social Innovation Grant
- 80. TSRI (Thailand Science Research and Innovation) Fundamental Fund → TSRI Fundamental Fund (FF)
- 82. DEPA Digital Startup Fund (dFund) → depa Digital Startup Fund
- 100. NXPO Thailand Science, Research and Innovation Fund (TSRI) → TSRI Fundamental Fund (FF) (the sheet lists it twice; this row links to NXPO, TSRI's site is tsri.or.th)

## Added

- 2. NSF SBIR Phase II (`nsf`)
- 5. DOE SBIR Phase I (`doe_sbir`)
- 6. DOE SBIR Phase II (`doe_sbir`)
- 8. NASA SBIR Phase I (`nasa_sbir`)
- 9. NASA SBIR Phase II (`nasa_sbir`)
- 10. DARPA SBIR / STTR (`darpa`)
- 11. USDA SBIR Phase I (`usda_nifa`)
- 12. USDA SBIR Phase II (`usda_nifa`)
- 13. AFWERX / DIU Commercialization Fund (`diu`)
- 14. BARDA DRIVe (`barda`)
- 15. NIST Manufacturing Extension Partnership (MEP) (`nist_mep`)
- 16. MassChallenge USA (`masschallenge`)
- 20. Plug and Play Tech Center (`pnp`)
- 23. Chain Reaction Innovations (ANL) (`anl_cri`)
- 24. Innovation Crossroads (ORNL) (`ornl_ic`)
- 25. Wells Fargo IN2 Incubator (`in2`)
- 27. EIC Pathfinder Challenges (`eic`)
- 30. EIC Accelerator Challenges (`eic`)
- 31. EIC STEP Scale-Up (`eic`)
- 32. Eurostars 3 (`eureka`)
- 33. Eureka Network Projects (`eureka`)
- 34. EIT InnoEnergy Call (`eit_innoenergy`)
- 35. EIT RawMaterials Accelerator (`eit_rawmaterials`)
- 36. EIT Health Headstart (`eit_health`)
- 37. EIT Digital Venture Program (`eit_digital`)
- 38. Innosuisse Innovation Projects (`innosuisse`)
- 39. FFG Bridge Program (`ffg`)
- 40. Bied ForLab / EXIST Program (`exist`)
- 41. Bpifrance Deeptech Plan (`bpifrance`)
- 42. CDTI R&D Projects (`cdti`)
- 44. Prime Movers Lab (`pml`)
- 46. EIT Food Accelerator Network (`eit_food`)
- 47. EIT Urban Mobility Accelerator (`eit_um`)
- 48. Deep Science Ventures (`dsv`)
- 49. Cancer Research UK Ventures (`cruk`)
- 50. Innovate UK Smart Grants (`innovate_uk`)
- 51. JST A-STEP (Adaptable and Seamless Technology transfer Program) (`jst`)
- 52. NEDO Technology Commercialization Program (`nedo`)
- 53. JETRO Startup Accelerator Programs (`jetro`)
- 54. KISED TIPS Program (Tech Incubator Program for Startup) (`kised`)
- 55. KIAT Industrial Technology R&D (`kiat`)
- 56. KIST Open Innovation Lab (`kist`)
- 57. NSTC Science & Technology Innovation Grant (`nstc_tw`)
- 58. TTA (Taiwan Tech Arena) Acceleration (`tta`)
- 61. Enterprise SG Startup SG Equity (Deep Tech) (`esg`)
- 62. A*STAR T-Up Programme (`astar`)
- 63. NRF Competitive Research Programme (CRP) (`nrf_sg`)
- 64. SGInnovate Summiteer / Deep Tech Mentorship (`sginnovate`)
- 65. A*CCELERATE Technologies (`astar`)
- 66. GAD (Global Applied DeepTech) Accelerator (`start2`)
- 67. BEP (Badan Ekonomi Kreatif) / BRIN Grants (`brin`)
- 68. MDEC GAIN / Kre8tif Accelerator (`mdec`)
- 70. NIAID International R&D Partnerships (`niaid`)
- 71. ADB Ventures (Asian Development Bank) (`adbv`)
- 72. Temasek Foundation grants (`temasek_fdn`)
- 75. INSEAD Venture Competition / SEA Hubs (`insead`)
- 79. NIA City and Community Innovation Challenge (`nia`)
- 81. NXPO Policy & Strategic Science Grants (`nxpo`)
- 83. NSTDA Research Chair / Industrial Joint Research (`nstda`)
- 84. NSTDA STEP (Science Technology Park) Incubation (`nstda`)
- 85. BCC (Bangkok Business Challenge) / CU Enterprise (`chula`)
- 86. True Incube (`true_incube`)
- 87. AIS The StartUp (`ais`)
- 88. Banpu Champions for Change (BCFC) (`banpu`)
- 89. InnoSpace (Thailand) (`innospace`)
- 90. Krungsri Finnovate (`krungsri_finnovate`)
- 91. Beacon Venture Capital (Kasikornbank) (`beacon_vc`)
- 92. SCB 10X (`scb10x`)
- 93. KXG (KASIKORN X-Change) (`kx`)
- 94. CU Innovation Hub (Chulalongkorn) (`chula`)
- 95. Thammasat University Science Park (`tu`)
- 96. Chiang Mai University Science Park (`cmu_step`)
- 97. Khon Kaen University Science Park (`kku_sp`)
- 98. Prince of Songkla University Science Park (`psu_sp`)
- 99. Thai-German Institute (TGI) (`tgi`)
