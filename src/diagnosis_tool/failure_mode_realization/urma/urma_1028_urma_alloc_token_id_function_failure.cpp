#include "urma_1028_urma_alloc_token_id_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1028UrmaAllocTokenIdFunctionFailure> g_urma("urma_1028");

bool Urma1028UrmaAllocTokenIdFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1029", "urma_1030"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1028UrmaAllocTokenIdFunctionFailure::GetName() const
{
    return "urma_alloc_token_id 函数故障";
}

std::string Urma1028UrmaAllocTokenIdFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1028UrmaAllocTokenIdFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1028UrmaAllocTokenIdFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1028UrmaAllocTokenIdFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1028UrmaAllocTokenIdFunctionFailure::GetId() const
{
    return "urma_1028";
}
} // namespace diag
