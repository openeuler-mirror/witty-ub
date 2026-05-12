#include "urma_1017_urma_cmd_alloc_token_id_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1017UrmaCmdAllocTokenIdFunctionFailure> g_urma("urma_1017");

bool Urma1017UrmaCmdAllocTokenIdFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1018", "urma_1019"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1017UrmaCmdAllocTokenIdFunctionFailure::GetName() const
{
    return "urma_cmd_alloc_token_id 函数故障";
}

std::string Urma1017UrmaCmdAllocTokenIdFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1017UrmaCmdAllocTokenIdFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1017UrmaCmdAllocTokenIdFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1017UrmaCmdAllocTokenIdFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1017UrmaCmdAllocTokenIdFunctionFailure::GetId() const
{
    return "urma_1017";
}
} // namespace diag
