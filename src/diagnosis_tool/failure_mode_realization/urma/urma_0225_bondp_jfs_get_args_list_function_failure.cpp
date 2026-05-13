#include "urma_0225_bondp_jfs_get_args_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0225BondpJfsGetArgsListFunctionFailure> g_urma("urma_0225");

bool Urma0225BondpJfsGetArgsListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0226", "urma_0227"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0225BondpJfsGetArgsListFunctionFailure::GetName() const
{
    return "bondp_jfs_get_args_list 函数故障";
}

std::string Urma0225BondpJfsGetArgsListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0225BondpJfsGetArgsListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0225BondpJfsGetArgsListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0225BondpJfsGetArgsListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0225BondpJfsGetArgsListFunctionFailure::GetId() const
{
    return "urma_0225";
}
} // namespace diag
