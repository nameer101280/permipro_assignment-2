"""API views for the question-answering endpoint."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .logic import answer_question


class HealthAPIView(APIView):
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "message": "Question-Answering Agent API",
                "endpoints": {"ask": "/api/ask/"},
            }
        )


class AskAPIView(APIView):
    def post(self, request):
        question = request.data.get("question") or request.data.get("q")
        if not isinstance(question, str) or not question.strip():
            return Response(
                {"error": "question is required", "source": "unknown"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = answer_question(question.strip())
        except Exception:
            return Response(
                {"error": "failed to process question", "source": "unknown"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"answer": result.answer, "source": result.source})
