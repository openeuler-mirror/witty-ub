#include "urma_1225_urma_read_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1225UrmaReadFunctionFailure> g_urma("urma_1225");

bool Urma1225UrmaReadFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1226"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1225UrmaReadFunctionFailure::GetName() const
{
    return "urma_read 函数故障";
}

std::string Urma1225UrmaReadFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1225UrmaReadFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1225UrmaReadFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1225UrmaReadFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1225UrmaReadFunctionFailure::GetId() const
{
    return "urma_1225";
}
} // namespace diag
