#include "urma_1230_urma_getenv_log_level_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1230UrmaGetenvLogLevelFunctionFailure> g_urma("urma_1230");

bool Urma1230UrmaGetenvLogLevelFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1231"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1230UrmaGetenvLogLevelFunctionFailure::GetName() const
{
    return "urma_getenv_log_level 函数故障";
}

std::string Urma1230UrmaGetenvLogLevelFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1230UrmaGetenvLogLevelFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1230UrmaGetenvLogLevelFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1230UrmaGetenvLogLevelFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1230UrmaGetenvLogLevelFunctionFailure::GetId() const
{
    return "urma_1230";
}
} // namespace diag
