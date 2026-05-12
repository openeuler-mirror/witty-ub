#include "urma_0949_urma_get_dmac_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0949UrmaGetDmacFunctionFailure> g_urma("urma_0949");

bool Urma0949UrmaGetDmacFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0950"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0949UrmaGetDmacFunctionFailure::GetName() const
{
    return "urma_get_dmac 函数故障";
}

std::string Urma0949UrmaGetDmacFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0949UrmaGetDmacFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0949UrmaGetDmacFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0949UrmaGetDmacFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0949UrmaGetDmacFunctionFailure::GetId() const
{
    return "urma_0949";
}
} // namespace diag
