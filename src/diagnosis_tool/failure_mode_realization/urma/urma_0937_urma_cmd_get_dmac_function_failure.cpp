#include "urma_0937_urma_cmd_get_dmac_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0937UrmaCmdGetDmacFunctionFailure> g_urma("urma_0937");

bool Urma0937UrmaCmdGetDmacFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0938"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0937UrmaCmdGetDmacFunctionFailure::GetName() const
{
    return "urma_cmd_get_dmac 函数故障";
}

std::string Urma0937UrmaCmdGetDmacFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0937UrmaCmdGetDmacFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0937UrmaCmdGetDmacFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0937UrmaCmdGetDmacFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0937UrmaCmdGetDmacFunctionFailure::GetId() const
{
    return "urma_0937";
}
} // namespace diag
