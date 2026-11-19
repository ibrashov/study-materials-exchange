# Error Analysis — Selected Production Model

- **Selected model:** `model_d_hybrid` (`hybrid_char_tfidf_logreg`, v1.0.0)
- **Validation-tuned threshold:** `0.8350` (uncertain band lower bound: `0.7150`)

## 1. Held-out Test Split Errors (`test.csv`)
- False Positives: **5**
- False Negatives: **737**

### Sample False Positives (Test)
| Filename | Language | Category | Normalized | Confidence |
| --- | --- | --- | --- | --- |
| `shift.pdf` | en | hard_negative | `shift` | 0.9195 |
| `Shift.pdf` | en | hard_negative | `shift` | 0.9222 |
| `Shift.xlsx` | en | hard_negative | `shift` | 0.9222 |
| `TOOLKIT.PDF` | en | clean_academic | `toolkit` | 0.8868 |
| `toolkit.pdf` | en | clean_academic | `toolkit` | 0.8671 |

### Sample False Negatives (Test)
| Filename | Language | Augmentation | Normalized | Confidence |
| --- | --- | --- | --- | --- |
| `пидорас.docx` | ru | none | `пидорас` | 0.8102 |
| `CL!t0r15.pdf` | en | multi_transform | `clitoris` | 0.6648 |
| `INCEST.pdf` | en | none | `incest` | 0.2644 |
| `Cialis.pdf` | en | none | `cialis` | 0.4625 |
| `PONYPLAY` | en | none | `ponyplay` | 0.4876 |
| `splooge.pdf` | en | none | `splooge` | 0.2559 |
| `ponyplay` | en | none | `ponyplay` | 0.4421 |
| `шлюх4.pdf` | ru | leetspeak | `шлюх4` | 0.3242 |
| `q u i m.pdf` | en | spaced_chars | `quim` | 0.6610 |
| `q*u*i*m.xlsx` | en | punct_separated | `quim` | 0.6822 |
| `DOGGYSTYLE.pdf` | en | none | `doggystyle` | 0.7791 |
| `Lab 10 spnk.pdf` | en | char_deletion | `lab 10 spnk` | 0.7074 |
| `nimphmania.docx` | en | char_deletion | `nimphmania` | 0.5461 |
| `Homework.13.ｐｉｓｓｉｎｇ.txt` | en | unicode_confusables | `homework 13 pissing` | 0.8070 |
| `пидорас.pdf` | ru | none | `пидорас` | 0.8102 |

## 2. Independent Challenge Test Set Errors (`challenge_test.csv`)
- False Positives: **0**
- False Negatives: **2**

### False Negatives (Challenge)
- `f*ck_this_course.pdf` (en, special_char_sub) -> norm `fck this course`, conf=0.6376
- `sh*t_exam.pdf` (en, special_char_sub) -> norm `sht exam`, conf=0.3929

## 3. Ambiguous Evaluation Cases (`ambiguous_eval.csv`)
| Filename | Expected | Predicted | Confidence | Policy Zone | Normalized |
| --- | --- | --- | --- | --- | --- |
| `pASS.pdf` | ALLOWED | ALLOWED | 0.0932 | allowed_confident | `pass` |
| `Ass_12.pdf` | ALLOWED | BLOCKED | 0.9675 | blocked_confident | `ass 12` |
| `Ass_1_Math.pdf` | ALLOWED | BLOCKED | 0.9279 | blocked_confident | `ass 1 math` |
| `Dickens_Novel_Analysis.pdf` | ALLOWED | ALLOWED | 0.0732 | allowed_confident | `dickens novel analysis` |
| `Hellman_Protocol.pdf` | ALLOWED | ALLOWED | 0.0849 | allowed_confident | `hellman protocol` |
| `Scunthorpe_Problem_NLP.pdf` | ALLOWED | ALLOWED | 0.1970 | allowed_confident | `scunthorpe problem nlp` |
| `Bitch_Index_Not_Real.pdf` | BLOCKED | BLOCKED | 0.9849 | blocked_confident | `bitch index not real` |
| `Pass_or_Fail_2026.pdf` | ALLOWED | ALLOWED | 0.0085 | allowed_confident | `pass or fail 2026` |
| `Sub_Matrix_Algebra.pdf` | ALLOWED | ALLOWED | 0.3974 | allowed_confident | `sub matrix algebra` |
| `Сексуальная_эволюция_дарвин.pdf` | ALLOWED | ALLOWED | 0.2108 | allowed_confident | `сексуальная эволюция дарвин` |
