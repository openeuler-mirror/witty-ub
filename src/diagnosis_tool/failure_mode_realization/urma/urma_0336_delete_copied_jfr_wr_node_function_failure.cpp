#include "urma_0336_delete_copied_jfr_wr_node_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0336DeleteCopiedJfrWrNodeFunctionFailure> g_urma("urma_0336");

bool Urma0336DeleteCopiedJfrWrNodeFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0337"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0336DeleteCopiedJfrWrNodeFunctionFailure::GetName() const
{
    return "delete_copied_jfr_wr_node 函数故障";
}

std::string Urma0336DeleteCopiedJfrWrNodeFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0336DeleteCopiedJfrWrNodeFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0336DeleteCopiedJfrWrNodeFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0336DeleteCopiedJfrWrNodeFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0336DeleteCopiedJfrWrNodeFunctionFailure::GetId() const
{
    return "urma_0336";
}
} // namespace diag
