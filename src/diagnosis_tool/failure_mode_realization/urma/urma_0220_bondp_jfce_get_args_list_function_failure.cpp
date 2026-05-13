#include "urma_0220_bondp_jfce_get_args_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0220BondpJfceGetArgsListFunctionFailure> g_urma("urma_0220");

bool Urma0220BondpJfceGetArgsListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0221"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0220BondpJfceGetArgsListFunctionFailure::GetName() const
{
    return "bondp_jfce_get_args_list 函数故障";
}

std::string Urma0220BondpJfceGetArgsListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0220BondpJfceGetArgsListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0220BondpJfceGetArgsListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0220BondpJfceGetArgsListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0220BondpJfceGetArgsListFunctionFailure::GetId() const
{
    return "urma_0220";
}
} // namespace diag
