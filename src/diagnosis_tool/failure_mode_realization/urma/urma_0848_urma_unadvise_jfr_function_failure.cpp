#include "urma_0848_urma_unadvise_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0848UrmaUnadviseJfrFunctionFailure> g_urma("urma_0848");

bool Urma0848UrmaUnadviseJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0849", "urma_0850"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0848UrmaUnadviseJfrFunctionFailure::GetName() const
{
    return "urma_unadvise_jfr 函数故障";
}

std::string Urma0848UrmaUnadviseJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0848UrmaUnadviseJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0848UrmaUnadviseJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0848UrmaUnadviseJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0848UrmaUnadviseJfrFunctionFailure::GetId() const
{
    return "urma_0848";
}
} // namespace diag
