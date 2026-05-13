#include "urma_0918_get_dev_ctx_eid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0918GetDevCtxEidFunctionFailure> g_urma("urma_0918");

bool Urma0918GetDevCtxEidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0919"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0918GetDevCtxEidFunctionFailure::GetName() const
{
    return "get_dev_and_ctx_by_eid 函数故障";
}

std::string Urma0918GetDevCtxEidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0918GetDevCtxEidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0918GetDevCtxEidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0918GetDevCtxEidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0918GetDevCtxEidFunctionFailure::GetId() const
{
    return "urma_0918";
}
} // namespace diag
