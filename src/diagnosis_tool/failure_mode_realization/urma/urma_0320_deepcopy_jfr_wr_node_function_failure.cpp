#include "urma_0320_deepcopy_jfr_wr_node_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0320DeepcopyJfrWrNodeFunctionFailure> g_urma("urma_0320");

bool Urma0320DeepcopyJfrWrNodeFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0321", "urma_0322"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0320DeepcopyJfrWrNodeFunctionFailure::GetName() const
{
    return "deepcopy_jfr_wr_node 函数故障";
}

std::string Urma0320DeepcopyJfrWrNodeFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0320DeepcopyJfrWrNodeFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0320DeepcopyJfrWrNodeFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0320DeepcopyJfrWrNodeFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0320DeepcopyJfrWrNodeFunctionFailure::GetId() const
{
    return "urma_0320";
}
} // namespace diag
