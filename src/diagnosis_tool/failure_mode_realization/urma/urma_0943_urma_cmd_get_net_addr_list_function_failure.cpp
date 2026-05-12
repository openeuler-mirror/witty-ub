#include "urma_0943_urma_cmd_get_net_addr_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0943UrmaCmdGetNetAddrListFunctionFailure> g_urma("urma_0943");

bool Urma0943UrmaCmdGetNetAddrListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0944"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0943UrmaCmdGetNetAddrListFunctionFailure::GetName() const
{
    return "urma_cmd_get_net_addr_list 函数故障";
}

std::string Urma0943UrmaCmdGetNetAddrListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0943UrmaCmdGetNetAddrListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0943UrmaCmdGetNetAddrListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0943UrmaCmdGetNetAddrListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0943UrmaCmdGetNetAddrListFunctionFailure::GetId() const
{
    return "urma_0943";
}
} // namespace diag
