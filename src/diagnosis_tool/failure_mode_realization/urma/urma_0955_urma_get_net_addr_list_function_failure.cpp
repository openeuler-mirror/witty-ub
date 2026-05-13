#include "urma_0955_urma_get_net_addr_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0955UrmaGetNetAddrListFunctionFailure> g_urma("urma_0955");

bool Urma0955UrmaGetNetAddrListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0956", "urma_0957", "urma_0958"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0955UrmaGetNetAddrListFunctionFailure::GetName() const
{
    return "urma_get_net_addr_list 函数故障";
}

std::string Urma0955UrmaGetNetAddrListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0955UrmaGetNetAddrListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0955UrmaGetNetAddrListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0955UrmaGetNetAddrListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0955UrmaGetNetAddrListFunctionFailure::GetId() const
{
    return "urma_0955";
}
} // namespace diag
