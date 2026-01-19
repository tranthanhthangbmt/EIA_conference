# Implementation Plan: Cognitive Load-Aware Difficulty Control

## Goal
Implement the "Cognitive Load-Aware Difficulty Control" mechanism described in the thesis (Paper 3). This aims to optimize the learning experience by dynamically selecting question difficulty based on the learner's current mastery level, avoiding frustration (too hard) or boredom (too easy).

## Current State Analysis
- **Database**: The `questions` table already has a `difficulty` column.
- **Engine**: Currently, `practice_engine.py` uses `qs.sample(1)` to pick a random question for a skill, ignoring difficulty.
- **Thesis Alignment**: Papers 1 (GAKT) and 2 (FASS) are implemented. Paper 3 (Difficulty Control) is the missing piece for a complete "Adaptive" system.

## User Review Required
> [!IMPORTANT]
> This change will alter how questions are selected. Instead of random questions, the system will favor questions that match the user's current proficiency.

## Proposed Changes

### Logic Overview
1.  **Define Difficulty Levels**: Ensure `difficulty` in DB maps to numerical values (e.g., 1=Easy, 2=Medium, 3=Hard).
2.  **Match Difficulty**:
    - If `User Mastery < 0.4` (Beginner): Prioritize **Easy** questions.
    - If `0.4 <= User Mastery < 0.7` (Intermediate): Prioritize **Medium** questions.
    - If `User Mastery >= 0.7` (Advanced/Review): Prioritize **Hard** questions.
3.  **Fallback**: If no questions of the target difficulty exist, fall back to adjacent difficulties.

### `practice_engine.py`
#### [MODIFY] [practice_engine.py](file:///d:/MY_CODE/treeKnowledge/practice_engine.py)
- Update `pick_question_for_skill` to accept `user_mastery_level`.
- Implement selection logic based on difficulty matching.

## Verification Plan

### Manual Verification
1.  **Setup**: Ensure questions for a topic have different difficulties in the DB.
2.  **Test Low Mastery**:
    - Set user mastery for a skill to 0.1 (via DB or Admin panel/hack).
    - Start Practice.
    - Verify questions served are "Easy".
3.  **Test High Mastery**:
    - Set user mastery to 0.8.
    - Start Practice.
    - Verify questions served are "Hard".
