#include "urma_1020_urma_cmd_alloc_token_id_ex_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1020UrmaCmdAllocTokenIdExFunctionFailure> g_urma("urma_1020");

bool Urma1020UrmaCmdAllocTokenIdExFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1021", "urma_1022"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1020UrmaCmdAllocTokenIdExFunctionFailure::GetName() const
{
    return "urma_cmd_alloc_token_id_ex 函数故障";
}

std::string Urma1020UrmaCmdAllocTokenIdExFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1020UrmaCmdAllocTokenIdExFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1020UrmaCmdAllocTokenIdExFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1020UrmaCmdAllocTokenIdExFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1020UrmaCmdAllocTokenIdExFunctionFailure::GetId() const
{
    return "urma_1020";
}
} // namespace diag
