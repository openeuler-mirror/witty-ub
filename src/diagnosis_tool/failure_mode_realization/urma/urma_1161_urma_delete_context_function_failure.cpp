#include "urma_1161_urma_delete_context_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1161UrmaDeleteContextFunctionFailure> g_urma("urma_1161");

bool Urma1161UrmaDeleteContextFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1162"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1161UrmaDeleteContextFunctionFailure::GetName() const
{
    return "urma_delete_context 函数故障";
}

std::string Urma1161UrmaDeleteContextFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1161UrmaDeleteContextFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1161UrmaDeleteContextFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1161UrmaDeleteContextFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1161UrmaDeleteContextFunctionFailure::GetId() const
{
    return "urma_1161";
}
} // namespace diag
