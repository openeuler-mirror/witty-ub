#include "urma_1207_urma_check_ctx_invalid_return_status_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1207UrmaCheckCtxInvalidReturnStatusFunctionFailure> g_urma("urma_1207");

bool Urma1207UrmaCheckCtxInvalidReturnStatusFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1208"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1207UrmaCheckCtxInvalidReturnStatusFunctionFailure::GetName() const
{
    return "URMA_CHECK_CTX_INVALID_RETURN_STATUS 函数故障";
}

std::string Urma1207UrmaCheckCtxInvalidReturnStatusFunctionFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma1207UrmaCheckCtxInvalidReturnStatusFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1207UrmaCheckCtxInvalidReturnStatusFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1207UrmaCheckCtxInvalidReturnStatusFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1207UrmaCheckCtxInvalidReturnStatusFunctionFailure::GetId() const
{
    return "urma_1207";
}
} // namespace diag
