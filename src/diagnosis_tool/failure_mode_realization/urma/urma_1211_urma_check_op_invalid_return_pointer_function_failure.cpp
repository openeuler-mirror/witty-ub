#include "urma_1211_urma_check_op_invalid_return_pointer_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1211UrmaCheckOpInvalidReturnPointerFunctionFailure> g_urma("urma_1211");

bool Urma1211UrmaCheckOpInvalidReturnPointerFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1212"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1211UrmaCheckOpInvalidReturnPointerFunctionFailure::GetName() const
{
    return "URMA_CHECK_OP_INVALID_RETURN_POINTER 函数故障";
}

std::string Urma1211UrmaCheckOpInvalidReturnPointerFunctionFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma1211UrmaCheckOpInvalidReturnPointerFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1211UrmaCheckOpInvalidReturnPointerFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1211UrmaCheckOpInvalidReturnPointerFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1211UrmaCheckOpInvalidReturnPointerFunctionFailure::GetId() const
{
    return "urma_1211";
}
} // namespace diag
