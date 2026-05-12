#include "urma_0326_deepcopy_jfs_wr_node_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0326DeepcopyJfsWrNodeFunctionFailure> g_urma("urma_0326");

bool Urma0326DeepcopyJfsWrNodeFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0327", "urma_0328", "urma_0329", "urma_0330",
                                                    "urma_0331", "urma_0332", "urma_0333"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0326DeepcopyJfsWrNodeFunctionFailure::GetName() const
{
    return "deepcopy_jfs_wr_node 函数故障";
}

std::string Urma0326DeepcopyJfsWrNodeFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0326DeepcopyJfsWrNodeFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0326DeepcopyJfsWrNodeFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0326DeepcopyJfsWrNodeFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0326DeepcopyJfsWrNodeFunctionFailure::GetId() const
{
    return "urma_0326";
}
} // namespace diag
