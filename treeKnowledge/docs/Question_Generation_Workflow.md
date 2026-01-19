# Question Generation Workflow - Kỹ Năng Số (Digital Skills)

**Last Updated:** 2025-12-14 22:26:00 (GMT+7)

## Overview
This document outlines the automated process used to generate the question bank for the "Kỹ năng số" course. The goal was to convert raw GIFT format questions into a structured CSV format compatible with the system's import requirements, mapping each question to specific sub-skills (Nodes).

## 1. Project Structure

### Inputs
- **Source Directory:** `d:\MY_CODE\treeKnowledge\knowledge\Kỹ năng số\`
- **Files (GIFT Format):**
  - `MD1-120 câu_updated_gift.txt` (Module 1)
  - `MD2-120 câu_updated_gift.txt` (Module 2)
  - `MD3-120 câu_updated_gift.txt` (Module 3)
  - `MD4-120 câu_updated_gift.txt` (Module 4)
  - `MD5-120 câu_updated_gift.txt` (Module 5)
  - `MD6-120 câu_updated_gift.txt` (Module 6)

### Outputs
- **Destination File:** `d:\MY_CODE\treeKnowledge\import_templates\questions_KNS.csv`
- **Structure File:** `d:\MY_CODE\treeKnowledge\import_templates\structure_KNS.csv`

## 2. Processing Scripts
We developed separate Python scripts for each module to handle specific keyword analysis and classification logic.

| Module | Script | Key Classifications (Sub-modules) |
| :--- | :--- | :--- |
| **Module 1** | `process_gift_m1.py` | Information & Data (KNS.1.1 - KNS.1.4) |
| **Module 2** | `process_m2_glob.py` | Communication & Collaboration (KNS.2.1 - KNS.2.4) |
| **Module 3** | `process_m3.py` | Digital Content Creation (KNS.3.1 - KNS.3.4) |
| **Module 4** | `process_m4.py` | Security & Safety (KNS.4.1 - KNS.4.4) |
| **Module 5** | `process_m5.py` | Problem Solving (KNS.5.1 - KNS.5.4) |
| **Module 6** | `process_m6.py` | AI & Future Skills (KNS.6.1 - KNS.6.4) |

## 3. Workflow Steps

1.  **Parsing:** The scripts read the `.txt` files in standard GIFT format, extracting:
    - Question Title
    - Question Content
    - Options (A, B, C, D)
    - Correct Answer

2.  **Classification:** Each script contains a `classify_mX` function that maps a question to a `Node_ID` (e.g., KNS.3.2) based on keyword matching in the question text.
    - *Example (Module 4):* "malware", "virus" -> `KNS.4.1`

3.  **Formatting:** Questions are formatted into a dictionary matching the CSV columns: `Question_ID`, `Skill_ID_List`, `Content`, `Options`, `Answer`, `Difficulty`, `Explanation`.
    - `Question_ID` is auto-generated sequentially (e.g., Q1.001, Q4.120).

4.  **Appending:** The processed rows are appended to the main `questions_KNS.csv` file.

## 4. Current Status
As of **2025-12-14**, the `questions_KNS.csv` file contains **720 questions** (120 per module), fully mapped to the structure defined in `structure_KNS.csv`.

## 5. Execution
To re-run or update a module, execute the corresponding script:
```bash
python process_m4.py
```
*Note: Ensure the source GIFT files are present in the `knowledge` directory.*
