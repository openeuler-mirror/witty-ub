#include "urma_1209_urma_check_op_invalid_return_neg_status_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1209UrmaCheckOpInvalidReturnNegStatusFunctionFailure> g_urma("urma_1209");

bool Urma1209UrmaCheckOpInvalidReturnNegStatusFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1210"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1209UrmaCheckOpInvalidReturnNegStatusFunctionFailure::GetName() const
{
    return "URMA_CHECK_OP_INVALID_RETURN_NEG_STATUS 函数故障";
}

std::string Urma1209UrmaCheckOpInvalidReturnNegStatusFunctionFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma1209UrmaCheckOpInvalidReturnNegStatusFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1209UrmaCheckOpInvalidReturnNegStatusFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1209UrmaCheckOpInvalidReturnNegStatusFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1209UrmaCheckOpInvalidReturnNegStatusFunctionFailure::GetId() const
{
    return "urma_1209";
}
} // namespace diag
