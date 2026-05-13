#include "urma_0920_get_dev_ctx_name_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0920GetDevCtxNameFunctionFailure> g_urma("urma_0920");

bool Urma0920GetDevCtxNameFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0921", "urma_0922", "urma_0923"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0920GetDevCtxNameFunctionFailure::GetName() const
{
    return "get_dev_and_ctx_by_name 函数故障";
}

std::string Urma0920GetDevCtxNameFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0920GetDevCtxNameFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0920GetDevCtxNameFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0920GetDevCtxNameFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0920GetDevCtxNameFunctionFailure::GetId() const
{
    return "urma_0920";
}
} // namespace diag
