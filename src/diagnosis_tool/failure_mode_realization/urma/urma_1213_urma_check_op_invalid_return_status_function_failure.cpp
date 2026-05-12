#include "urma_1213_urma_check_op_invalid_return_status_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1213UrmaCheckOpInvalidReturnStatusFunctionFailure> g_urma("urma_1213");

bool Urma1213UrmaCheckOpInvalidReturnStatusFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1214"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1213UrmaCheckOpInvalidReturnStatusFunctionFailure::GetName() const
{
    return "URMA_CHECK_OP_INVALID_RETURN_STATUS 函数故障";
}

std::string Urma1213UrmaCheckOpInvalidReturnStatusFunctionFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma1213UrmaCheckOpInvalidReturnStatusFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1213UrmaCheckOpInvalidReturnStatusFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1213UrmaCheckOpInvalidReturnStatusFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1213UrmaCheckOpInvalidReturnStatusFunctionFailure::GetId() const
{
    return "urma_1213";
}
} // namespace diag
