import structlog
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from ...dependencies import get_quiz_repository, get_video_job_repository
from ..schemas import QuizResponse, QuizSubmission
from ....core.exceptions import JobNotFoundError
from ....services.quiz_evaluator import QuizEvaluator
from ....config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()

@router.get("", response_model=Dict[str, Any])
async def get_video_quiz(
    video_id: int,
    quiz_repo = Depends(get_quiz_repository),
    video_repo = Depends(get_video_job_repository)
) -> Dict[str, Any]:
    try:
        job = video_repo.get(video_id)
        if not job:
            raise JobNotFoundError(video_id)

        if job.status != "completed":
            raise HTTPException(
                status_code=409,
                detail=f"Quiz not available. Job status: {job.status}"
            )

        questions = quiz_repo.get_questions_by_job_id(video_id)
        if not questions:
            raise HTTPException(
                status_code=404,
                detail="No quiz questions found for this video"
            )

        # Hide correct answers - only return question data needed for taking quiz
        quiz_questions = []
        for q in questions:
            question_data = {
                "question_id": q.question_id,
                "question": q.question,
                "type": q.type,
                "max_score": q.max_score
            }

            # Add options for MCQ questions only
            if q.type == "multiple_choice" and "options" in q.answer_config:
                question_data["options"] = q.answer_config["options"]

            # Add context if available
            if q.context:
                question_data["context"] = q.context

            quiz_questions.append(question_data)

        total_score = quiz_repo.get_total_score_by_job_id(video_id)

        return {
            "questions": quiz_questions,
            "total_questions": len(questions),
            "max_score": total_score
        }

    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get quiz questions", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve quiz questions")


@router.post("", response_model=Dict[str, Any])
async def submit_video_quiz(
    video_id: int,
    submission: QuizSubmission,
    quiz_repo = Depends(get_quiz_repository),
    video_repo = Depends(get_video_job_repository)
) -> Dict[str, Any]:
    try:
        job = video_repo.get(video_id)
        if not job:
            raise JobNotFoundError(video_id)

        questions = quiz_repo.get_questions_by_job_id(video_id)
        if not questions:
            raise HTTPException(
                status_code=404,
                detail="No quiz questions found for this video"
            )

        questions_data = [
            {
                "question_id": q.question_id,
                "question": q.question,
                "type": q.type,
                "answer_config": q.answer_config,
                "context": q.context,
                "max_score": q.max_score
            }
            for q in questions
        ]

        user_answers = [
            {
                "question_id": question_id,
                "user_answer": user_answer
            }
            for question_id, user_answer in submission.answers.items()
        ]

        evaluator = QuizEvaluator(None)
        evaluation_result = await evaluator.evaluate_quiz_submission(questions_data, user_answers)

        return {
            "total_score": evaluation_result["total_score"],
            "max_possible_score": evaluation_result["max_possible_score"],
            "evaluated_at": evaluation_result["evaluated_at"],
            "results": evaluation_result["question_results"]
        }

    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit quiz", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to evaluate quiz submission")


