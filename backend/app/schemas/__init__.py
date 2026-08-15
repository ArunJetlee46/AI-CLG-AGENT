"""Per-domain request/response schemas. Re-exports every schema so
`from app.schemas import X` works alongside the canonical submodules.
"""

from app.schemas.admin import (  # noqa: F401
    AnnouncementCreate,
    CopilotRequest,
    EvaluationRequest,
    GenerateRequest,
    IndustryPartnerCreate,
    ModelRegister,
    PredictionOut,
    ResearchProjectCreate,
    ResourceCreate,
    ResourceUpdate,
    ScenarioRequest,
    TimetableOptimizeRequest,
)
from app.schemas.approval import ApprovalDecision  # noqa: F401
from app.schemas.audit import AuditQuery, AuditRow  # noqa: F401
from app.schemas.auth import (  # noqa: F401
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.schemas.chat import ChatRequest, ChatResponse  # noqa: F401
from app.schemas.faculty import (  # noqa: F401
    AssignmentAssistRequest,
    AssignmentEvalRequest,
    CodeReviewRequest,
    InterviewRequest,
    InterviewScoreRequest,
    LabAssistantRequest,
    LessonPlanRequest,
    ProjectMentorRequest,
    ResumeRequest,
    SimilarityRequest,
    SimilaritySubmission,
    TeachingMaterialRequest,
)
from app.schemas.placement import (  # noqa: F401
    CompanyCreate,
    DriveCreate,
    JDAnalyzeRequest,
    JobDescriptionCreate,
    NotifyRequest,
    RoundCreate,
    SelectionCreate,
    ShortlistRequest,
)
from app.schemas.students import AdviseRequest, InterventionRequest  # noqa: F401
