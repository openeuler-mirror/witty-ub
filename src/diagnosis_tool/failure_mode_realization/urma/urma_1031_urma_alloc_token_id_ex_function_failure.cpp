#include "urma_1031_urma_alloc_token_id_ex_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1031UrmaAllocTokenIdExFunctionFailure> g_urma("urma_1031");

bool Urma1031UrmaAllocTokenIdExFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1032", "urma_1033"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1031UrmaAllocTokenIdExFunctionFailure::GetName() const
{
    return "urma_alloc_token_id_ex 函数故障";
}

std::string Urma1031UrmaAllocTokenIdExFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1031UrmaAllocTokenIdExFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1031UrmaAllocTokenIdExFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1031UrmaAllocTokenIdExFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1031UrmaAllocTokenIdExFunctionFailure::GetId() const
{
    return "urma_1031";
}
} // namespace diag
