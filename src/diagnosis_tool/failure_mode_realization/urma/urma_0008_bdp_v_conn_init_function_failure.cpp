#include "urma_0008_bdp_v_conn_init_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0008BdpVConnInitFunctionFailure> g_urma("urma_0008");

bool Urma0008BdpVConnInitFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0009", "urma_0010"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0008BdpVConnInitFunctionFailure::GetName() const
{
    return "bdp_v_conn_init 函数故障";
}

std::string Urma0008BdpVConnInitFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0008BdpVConnInitFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0008BdpVConnInitFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0008BdpVConnInitFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0008BdpVConnInitFunctionFailure::GetId() const
{
    return "urma_0008";
}
} // namespace diag
