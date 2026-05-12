#include "urma_0622_urma_alloc_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0622UrmaAllocJfrFunctionFailure> g_urma("urma_0622");

bool Urma0622UrmaAllocJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0623", "urma_0624", "urma_0625"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0622UrmaAllocJfrFunctionFailure::GetName() const
{
    return "urma_alloc_jfr 函数故障";
}

std::string Urma0622UrmaAllocJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0622UrmaAllocJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0622UrmaAllocJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0622UrmaAllocJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0622UrmaAllocJfrFunctionFailure::GetId() const
{
    return "urma_0622";
}
} // namespace diag
