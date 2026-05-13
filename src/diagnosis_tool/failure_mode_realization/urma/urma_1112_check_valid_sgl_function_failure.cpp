#include "urma_1112_check_valid_sgl_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1112CheckValidSglFunctionFailure> g_urma("urma_1112");

bool Urma1112CheckValidSglFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1113"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1112CheckValidSglFunctionFailure::GetName() const
{
    return "check_valid_sgl 函数故障";
}

std::string Urma1112CheckValidSglFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1112CheckValidSglFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1112CheckValidSglFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1112CheckValidSglFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1112CheckValidSglFunctionFailure::GetId() const
{
    return "urma_1112";
}
} // namespace diag
