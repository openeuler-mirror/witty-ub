#include "urma_1137_urma_cmd_free_token_id_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1137UrmaCmdFreeTokenIdFunctionFailure> g_urma("urma_1137");

bool Urma1137UrmaCmdFreeTokenIdFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1138", "urma_1139"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1137UrmaCmdFreeTokenIdFunctionFailure::GetName() const
{
    return "urma_cmd_free_token_id 函数故障";
}

std::string Urma1137UrmaCmdFreeTokenIdFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1137UrmaCmdFreeTokenIdFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1137UrmaCmdFreeTokenIdFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1137UrmaCmdFreeTokenIdFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1137UrmaCmdFreeTokenIdFunctionFailure::GetId() const
{
    return "urma_1137";
}
} // namespace diag
